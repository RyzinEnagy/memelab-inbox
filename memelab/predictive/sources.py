"""Phase 05: read-only source adapters for the point-in-time store (research only, flag OFF, imported by no existing module).

  export_versions   every version of data/state/latest.json on a ref, read from git objects along the first-parent history,
                    oldest first, with commit time, blob id and body sha256 (the decision seam of PLANNED_SEAMS.md; the export
                    format is read by decisions.export_from_doc exactly as state.import_ reads it). Nothing is checked out.
  plan_backfill     which GeckoTerminal 5-minute series to read for which pool, and the holdout seal: only development-period
                    Solana decisions with a point-in-time pool (decision before the holdout start and the 6 h label maturity
                    at or before it); every request boundary at or before the pool's latest such decision and at least one
                    hour before the holdout start, so no request touches a holdout decision's window [decision - 3600 s, ...]
                    (ACCEPTANCE holdout_contacted rule). A pool claimed by two mints is refused (P01, P02).
  fetch_series      paged reads of one planned series through runtime.CallGuard (6 a minute, 1,200 a run, breaker after 5
                    consecutive failures, ACCEPTANCE api_limits), HTTP 429 back-off, every response handed to the caller for
                    store.ingest_gt_response. The network function is injected; tests pass a fake and never reach a socket.

No label, barrier or class is computed here (labels are Phase 06's).
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from . import contract as C
from . import decisions as D
from . import runtime as R
from . import store as S

EXPORT_PATH = "data/state/latest.json"
GT_BASE = "https://api.geckoterminal.com/api/v2/networks/{network}/pools/{pool}/ohlcv/{timeframe}"
LIMIT = 1000
PERIOD_S = 300
FEATURE_LOOKBACK_S = 86400          # the longest causal window of the feature set
WINDOW_MARGIN_S = 3600              # one more hour so a window's starting price has a candle at or before it
DEV_TARGET = "price_path_target_before_invalidation_6h"   # the shortest primary target: the widest development set
HOLDOUT_CONTACT_PAD_S = 3600        # ACCEPTANCE holdout_contacted counts any read covering [decision - 3600 s, maturity]


class SourceError(ValueError):
    pass


def _git(repo: str | Path, *a: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True).stdout


def export_versions(repo: str | Path, ref: str, path: str = EXPORT_PATH) -> list[dict]:
    """Every version of the export on `ref`'s first-parent history, oldest first. A version that does not parse is skipped and
    returned in the "skipped" list of the last element's metadata (counted, never silently)."""
    out, skipped = [], []
    for ln in _git(repo, "rev-list", "--reverse", "--first-parent", "--timestamp", ref, "--", path).decode().splitlines():
        if not ln.strip():
            continue
        t, commit = ln.split()
        raw = _git(repo, "show", f"{commit}:{path}")
        try:
            doc = json.loads(raw)
        except ValueError:
            skipped.append(commit)
            continue
        ex = D.export_from_doc(commit, int(t), doc)
        ex.update(blob=_git(repo, "rev-parse", f"{commit}:{path}").decode().strip(), body_sha256=hashlib.sha256(raw).hexdigest(),
                  body_bytes=len(raw), path=path)
        out.append(ex)
    if out:
        out[-1]["skipped_versions"] = skipped
    return out


def holdout_start() -> float:
    return C.parse_utc(C.ACCEPTANCE["holdout_window_utc"][0])


def development_period(decision_time: float) -> bool:
    h0 = holdout_start()
    return decision_time < h0 and C.label_matures_at(DEV_TARGET, decision_time) <= h0


def fetch_scope(dec: dict) -> str:
    """Why a decision's price window is or is not read in Phase 05 (a retrieval fact, recorded with every snapshot)."""
    if dec.get("chain") != "solana":
        return "OUT_OF_SCOPE_CHAIN"
    if not dec.get("pool_address"):
        return "NO_POOL_AT_DECISION"
    if not development_period(float(dec["decision_time"])):
        return "NOT_FETCHED_SEALED"
    return "DEVELOPMENT"


def plan_backfill(decs: list[dict], *, lookback_s: float = FEATURE_LOOKBACK_S, margin_s: float = WINDOW_MARGIN_S) -> list[dict]:
    """One series per point-in-time pool of the development-period decisions. decs: rows of predictive_decisions."""
    h0 = holdout_start()
    by_pool: dict[str, list[dict]] = {}
    for d in decs:
        if fetch_scope(d) == "DEVELOPMENT":
            by_pool.setdefault(d["pool_address"], []).append(d)
    plan = []
    for pool, ds in sorted(by_pool.items()):
        mints = {d["mint"] for d in ds}
        if len(mints) != 1:
            raise SourceError(f"pool {pool} is the point-in-time pool of {len(mints)} mints: a pool has one mint (P01, P02)")
        mint = next(iter(mints))
        S.check_address("solana", mint)
        S.check_address("solana", pool, "pool")
        times = sorted(float(d["decision_time"]) for d in ds)
        boundary = int(math.floor(times[-1]))
        if boundary > h0 - HOLDOUT_CONTACT_PAD_S:
            raise SourceError(f"request boundary {boundary} reaches the holdout contact window (before {h0 - HOLDOUT_CONTACT_PAD_S})")
        plan.append({"series_id": f"{pool}@{boundary}", "chain": "solana", "mint": mint, "pool": pool, "boundary": boundary,
                     "need_from": times[0] - PERIOD_S - lookback_s - margin_s, "decisions": len(ds),
                     "first_decision": times[0], "last_decision": times[-1]})
    return plan


def check_plan(plan: list[dict]) -> None:
    """The seal, re-checked on any plan before a call is made."""
    h0 = holdout_start()
    owner: dict[str, str] = {}
    for p in plan:
        if p["boundary"] > h0 - HOLDOUT_CONTACT_PAD_S or p["boundary"] > p["last_decision"]:
            raise SourceError(f"series {p['series_id']}: boundary after the pool's last development decision or in the holdout window")
        if owner.setdefault(p["pool"], p["mint"]) != p["mint"]:
            raise SourceError(f"pool {p['pool']} planned for two mints")


def gt_url(pool: str, before: int, *, token: str | None, network: str = "solana", timeframe: str = "minute",
           aggregate: int = 5, limit: int = LIMIT) -> str:
    """`token=<mint>` makes the vendor price the mint even when it is the pool's quote token (the lab collector does the same,
    memelab/bridge/plan.py)."""
    return (GT_BASE.format(network=network, pool=pool, timeframe=timeframe)
            + f"?aggregate={aggregate}&limit={limit}&before_timestamp={int(before)}&currency=usd"
            + (f"&token={token}" if token else ""))


def curl_get(url: str, timeout_s: int = 60) -> tuple[int, bytes]:
    """The only network call in this package (used by the phase's backfill run, never by the tests)."""
    p = subprocess.run(["curl", "-sS", "-m", str(timeout_s), "-o", "-", "-w", "\n%{http_code}", "-H",
                        "Accept: application/json;version=20230302", url], capture_output=True, timeout=timeout_s + 30)
    body, _, code = p.stdout.rpartition(b"\n")
    try:
        return int(code or 0), body
    except ValueError:
        return 0, body


class HTTPStatusError(RuntimeError):
    """Raised inside the guarded call for a non-200 answer, so runtime.CallGuard counts it toward its breaker."""


def fetch_series(p: dict, *, http_get: Callable[[str], tuple[int, bytes]], guard: R.CallGuard,
                 clock: Callable[[], float] = time.time, sleep: Callable[[float], None] = time.sleep,
                 on_response: Callable[[dict], dict] | None = None, timeframe: str = "minute", aggregate: int = 5,
                 retries_429: int = 3, backoff_429_s: float = 60.0, token_param: bool = True) -> dict:
    """Read one planned series newest page first. Each response is passed to on_response (the caller ingests it and returns the
    ingest summary). Ends OK (vendor served nothing earlier, or the window start is reached), NO_DATA (no candle at all),
    READ_FAILED (an HTTP error after retries, or a network failure), BAD_BODY (a body that does not parse), CIRCUIT_OPEN or
    CALL_CAP_REACHED (the guard refused before calling). `retrieved_at` is the time the answer arrived."""
    check_plan([p])
    period = S.GT_PERIOD[(timeframe, int(aggregate))]
    before, page = int(p["boundary"]), 0
    keys, calls, status, detail, kept, last_end = [], 0, "OK", None, 0, None
    any_candle = False
    while True:
        url = gt_url(p["pool"], before, token=p["mint"] if token_param else None, timeframe=timeframe, aggregate=aggregate)
        tries = 0
        while True:
            last: dict[str, Any] = {}

            def call(u: str) -> tuple[int, bytes]:
                code, body = http_get(u)
                last["resp"] = (int(code), body)
                if int(code) != 200:
                    raise HTTPStatusError(f"HTTP {code}")
                return int(code), body

            requested = clock()
            st, val = guard.call("geckoterminal", call, url)
            if st["state"] in (R.CIRCUIT_OPEN, R.CALL_CAP_REACHED, R.COST_CAP_REACHED):
                status = "CIRCUIT_OPEN" if st["state"] == R.CIRCUIT_OPEN else "CALL_CAP_REACHED"
                detail = st["detail"]
                break
            calls += 1
            arrived = clock()
            if st["state"] == R.AVAILABLE:
                http, body = val
            elif "resp" in last:
                http, body = last["resp"]
            else:
                http, body = 0, b""
                detail = st["state"] + ":" + str(st["detail"])
            resp = {"url": url, "params": {"pool": p["pool"], "timeframe": timeframe, "aggregate": aggregate, "limit": LIMIT,
                                           "before_timestamp": before, "currency": "usd", "page": page,
                                           "series_id": p["series_id"], "requested_at": requested,
                                           "token": p["mint"] if token_param else None},
                    "retrieved_at": arrived, "http_status": http, "body": body, "boundary_at": before,
                    "timeframe": timeframe, "aggregate": aggregate}
            summary = on_response(resp) if on_response else {}
            if summary.get("response_key"):
                keys.append(summary["response_key"])
            if http == 429 and tries < retries_429:
                tries += 1
                sleep(backoff_429_s)
                continue
            break
        if status in ("CIRCUIT_OPEN", "CALL_CAP_REACHED"):
            break
        if http != 200:
            status, detail = "READ_FAILED", detail or f"HTTP {http}"
            break
        if summary.get("identity_check") and not str(summary["identity_check"]).startswith("OK"):
            status, detail = "IDENTITY_MISMATCH", summary["identity_check"]
            break
        try:
            rows = S.parse_gt_ohlcv(body)
        except (ValueError, S.StoreError) as e:
            status, detail = "BAD_BODY", str(e)[:200]
            break
        good = [r for r in rows if isinstance(r, list) and r and isinstance(r[0], (int, float)) and r[0] + period <= before]
        kept += len(good)
        if good:
            any_candle = True
            if last_end is None:
                last_end = max(float(r[0]) for r in good) + period
        if len(rows) < LIMIT or not rows:
            break
        earliest = int(min(float(r[0]) for r in rows))
        if earliest <= p["need_from"]:
            break
        if earliest >= before:
            status, detail = "BAD_BODY", "pagination did not move back"
            break
        before, page = earliest, page + 1
    if status == "OK" and not any_candle:
        status = "NO_DATA"
    return {"series_id": p["series_id"], "status": status, "detail": detail, "response_keys": keys, "calls": calls,
            "candles_kept": kept if status != "IDENTITY_MISMATCH" else 0, "last_end_at": last_end if status != "IDENTITY_MISMATCH"
            else None, "checked_at": clock(), "period_s": period}
