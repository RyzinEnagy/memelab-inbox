"""Phase 09: read-only adapter contract to the backtesting module's forward depth collector (research only, flag OFF, imported
by no existing module; standard library only).

The collector (D-BT-034/035 on `feature/backtesting`, approved by Elving on 2026-10-25 as PI-D-044) records, every hour until
25 h after each export commit, the decision pool's reserves (GeckoTerminal) and on Solana keyless sell quotes into USDC at fixed
sizes (Jupiter), in three append-only tables of its schema migration 2: `bt_depth_decisions`, `bt_depth_pool_lookups` and
`bt_depth_snapshots`. This module reads those tables and nothing else:
  - it never imports `memelab.backtest`, never fetches, never writes (the file is opened `mode=ro` and `query_only`), and is
    not a second loader: the expected columns come from the documented schema (`memelab/backtest/schema.py` at `12f278b`, the
    text kept as `tests/fixtures/predictive/bt_depth_schema_v2.sql`);
  - identity is chain plus exact mint (Solana byte for byte, EVM without case, the collector's own rule); a link to a predictive
    decision needs the same chain, mint and row sha256 and an export time equal to the decision time (both EXPORT_COMMIT);
  - every row is available at its `captured_at`; for its own decision it is after the decision (the first run comes up to an
    hour later), so it is never a feature of that decision (counterexample CX-09, `visible_at`); it may be a feature of a later
    decision of the same mint;
  - rows stay per pool (P02); `reserve_usd` is reported reserve, never exit capacity (P08); a quote has a proceeds number only
    in state OK; NO_ROUTE or NOT_TRADABLE is a lost route, never a favourable fill (P37); failed or skipped reads are censoring.
The proposed liquidity label (`proposed_liquidity_label`) is NOT a frozen target: it has no default parameter, labels whatever
observations it is given, and marks every result PROPOSED_NOT_FROZEN (PI-D-044, PI-D-054). Until the collector is deployed and
has rows, every result built here is TEST_ONLY.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
from pathlib import Path
from typing import Any, Sequence

from . import labels as L
from . import store as S

ADAPTER_VERSION = "depth-adapter-1"
SCHEMA_SOURCE = "memelab/backtest/schema.py migration 2 at 12f278b (origin/feature/backtesting)"
MIN_MIGRATION = 2
EXPECTED = {
    "bt_depth_decisions": ("id", "chain", "mint", "pool_address", "pool_source", "export_commit", "export_time", "export_path",
                           "created_at", "row_sha256", "status", "recorded_at", "content_hash"),
    "bt_depth_pool_lookups": ("id", "run_id", "decision_id", "chain", "mint", "attempt", "request_url", "captured_at", "http_status",
                              "raw_sha256", "raw_ref", "state", "pool_address", "value_json", "recorded_at", "content_hash"),
    "bt_depth_snapshots": ("id", "run_id", "decision_id", "chain", "mint", "pool_address", "kind", "provider", "size_usd",
                           "token_amount", "token_amount_raw", "decimals", "request_url", "captured_at", "http_status", "raw_sha256",
                           "raw_ref", "state", "since_export_s", "reserve_usd", "price_usd", "out_usd", "price_impact", "value_json",
                           "recorded_at", "content_hash"),
}
ROUTE_LOST = ("NO_ROUTE", "NOT_TRADABLE")
ANSWERED = ("OK",) + ROUTE_LOST
PROPOSED = "PROPOSED_NOT_FROZEN"
STATES = ("COLLECTOR_NOT_AVAILABLE", "SCHEMA_MISMATCH", "NO_ROWS", "OK")


class AdapterError(ValueError):
    pass


class DepthIdentityError(AdapterError):
    """A collector row of another chain, mint, row or export time was about to be linked to a decision (P01)."""


class DepthLeakageError(AdapterError):
    """A collector row captured after the time of use was about to be used as a feature (CX-09)."""


def same(chain: str, a: str | None, b: str | None) -> bool:
    if a is None or b is None:
        return False
    return a == b if chain == "solana" else a.lower() == b.lower()


def _refuse(path: Path) -> None:
    rp = path.resolve()
    if rp in S._forbidden_paths():
        raise AdapterError("the collector adapter never opens the tracked lab database (data/memelab.sqlite or MEMELAB_DB)")
    env = os.environ.get("MEMELAB_PREDICTIVE_STORE")
    if env and rp == Path(env).resolve():
        raise AdapterError("the collector adapter never opens the predictive store")
    L.refuse_sealed(str(path))


def connect_ro(path: str | Path) -> sqlite3.Connection:
    """Open a collector database read-only. A missing file is COLLECTOR_NOT_AVAILABLE (raised), never created."""
    p = Path(path)
    _refuse(p)
    if not p.is_file():
        raise FileNotFoundError(f"COLLECTOR_NOT_AVAILABLE: {p}")
    con = sqlite3.connect(f"file:{p.resolve()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    return con


def check_schema(con: sqlite3.Connection) -> list[str]:
    """Problems with the collector schema; empty when migration 2 or later is applied and every documented column exists."""
    out = []
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "bt_schema_migrations" not in tables:
        out.append("no bt_schema_migrations ledger")
    else:
        v = con.execute("SELECT MAX(version) FROM bt_schema_migrations").fetchone()[0]
        if v is None or int(v) < MIN_MIGRATION:
            out.append(f"migration {v} is below {MIN_MIGRATION}")
    for t, cols in EXPECTED.items():
        if t not in tables:
            out.append(f"table {t} missing")
            continue
        have = {r[1] for r in con.execute(f"PRAGMA table_info({t})")}
        miss = [c for c in cols if c not in have]
        if miss:
            out.append(f"{t}: columns {miss} missing")
    return out


def status(path: str | Path | None) -> dict:
    """COLLECTOR_NOT_AVAILABLE, SCHEMA_MISMATCH, NO_ROWS or OK, with counts. Never raises for a missing file."""
    if path is None or not Path(path).is_file():
        return {"state": "COLLECTOR_NOT_AVAILABLE", "path": str(path) if path else None, "adapter": ADAPTER_VERSION,
                "evidence_class": "TEST_ONLY"}
    con = connect_ro(path)
    try:
        probs = check_schema(con)
        if probs:
            return {"state": "SCHEMA_MISMATCH", "problems": probs, "adapter": ADAPTER_VERSION}
        n = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in EXPECTED}
        return {"state": "OK" if n["bt_depth_snapshots"] else "NO_ROWS", "rows": n, "adapter": ADAPTER_VERSION}
    finally:
        con.close()


def link(con: sqlite3.Connection, *, chain: str, mint: str, row_sha256: str, decision_time: float) -> dict | None:
    """The collector's decision row for one predictive decision, or None. Same chain, exact mint, same row sha256, and an export
    time equal to the decision time (both are the export commit time, PI-D-015); anything else raises."""
    rows = [dict(r) for r in con.execute("SELECT * FROM bt_depth_decisions WHERE chain=? AND row_sha256=?", (chain, row_sha256))]
    rows = [r for r in rows if same(chain, r["mint"], mint)]
    if not rows:
        return None
    if len(rows) > 1:
        raise DepthIdentityError("two collector decisions share one exact row")
    r = rows[0]
    if r["mint"] != mint and chain == "solana":
        raise DepthIdentityError("Solana mint differs in case (P01)")
    if abs(float(r["export_time"]) - float(decision_time)) > 1e-6:
        raise DepthIdentityError(f"export time {r['export_time']} is not the decision time {decision_time}: another export of the row")
    return r


def _jl(x: Any) -> Any:
    try:
        return json.loads(x) if isinstance(x, str) else x
    except ValueError:
        return None


def observations(con: sqlite3.Connection, *, chain: str, mint: str, decision_id: int | None = None) -> list[dict]:
    """Typed POOL and QUOTE rows of one exact (chain, mint), each available at its captured_at, grouped by pool by the caller.
    A row never read (captured_at NULL: cap, deadline, skipped) has no availability and no number."""
    q = "SELECT * FROM bt_depth_snapshots WHERE chain=?" + (" AND decision_id=?" if decision_id is not None else "")
    args = (chain, decision_id) if decision_id is not None else (chain,)
    out = []
    for r in con.execute(q + " ORDER BY captured_at, id", args):
        r = dict(r)
        if not same(chain, r["mint"], mint):
            continue
        cap = r["captured_at"]
        o = {"id": r["id"], "decision_id": r["decision_id"], "run_id": r["run_id"], "chain": r["chain"], "mint": r["mint"],
             "pool_address": r["pool_address"], "kind": r["kind"], "provider": r["provider"], "state": r["state"],
             "captured_at": float(cap) if cap is not None else None, "available_at": float(cap) if cap is not None else None,
             "since_export_s": r["since_export_s"], "size_usd": r["size_usd"], "http_status": r["http_status"],
             "raw_sha256": r["raw_sha256"], "reported_reserve_usd": r["reserve_usd"], "reserve_semantics": "REPORTED_RESERVE_NOT_EXIT_CAPACITY",
             "price_usd": r["price_usd"], "out_usd": None, "proceeds_ratio": None, "price_impact": None}
        if r["kind"] == "QUOTE" and r["state"] == "OK" and r["out_usd"] is not None and r["size_usd"]:
            o["out_usd"] = float(r["out_usd"])
            o["proceeds_ratio"] = float(r["out_usd"]) / float(r["size_usd"])
            o["price_impact"] = r["price_impact"]
        out.append(o)
    return out


def by_pool(obs: Sequence[dict]) -> dict[str, list[dict]]:
    """Per pool, never merged across venues of one mint (P02)."""
    g: dict[str, list[dict]] = {}
    for o in obs:
        g.setdefault(o["pool_address"], []).append(o)
    return g


def visible_at(obs: Sequence[dict], T: float) -> list[dict]:
    """Rows usable as inputs at time T: captured (read) at or before T. A collector row of the decision made at T is captured
    after T and is never returned (CX-09)."""
    return [o for o in obs if o["available_at"] is not None and o["available_at"] <= float(T)]


def assert_visible(rows: Sequence[dict], T: float) -> None:
    for o in rows:
        if o.get("available_at") is None or o["available_at"] > float(T):
            raise DepthLeakageError(f"collector row {o.get('id')} captured at {o.get('available_at')} is not available at {T} (CX-09)")


def proposed_liquidity_label(obs: Sequence[dict], *, decision_time: float, as_of: float, pool_address: str, size_usd: float,
                             drop: float, baseline_max_lag_s: float, horizon_s: float, horizon_tol_s: float) -> dict:
    """PROPOSED, not frozen (no default parameter): did the sell proceeds at `size_usd` on `pool_address` fall by `drop` or more
    between the first answered quote after the decision (within `baseline_max_lag_s`) and the answered quote nearest
    decision + `horizon_s` (within `horizon_tol_s`)? A lost route after an OK baseline is an event (ROUTE_LOST, P37); a route
    already lost at the baseline is EXIT_UNAVAILABLE_AT_BASELINE (not this target); unanswered reads are censored; a horizon not
    yet reachable at `as_of` is NOT_YET_MATURED (P05). Reported reserve is never read (P08)."""
    for name, v in (("size_usd", size_usd), ("drop", drop), ("baseline_max_lag_s", baseline_max_lag_s), ("horizon_s", horizon_s),
                    ("horizon_tol_s", horizon_tol_s)):
        if not (isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0):
            raise AdapterError(f"{name} must be a positive number")
    if not 0 < drop < 1:
        raise AdapterError("drop must be in (0, 1)")
    T = float(decision_time)
    base = {"status": PROPOSED, "pool_address": pool_address, "size_usd": size_usd,
            "params": {"drop": drop, "baseline_max_lag_s": baseline_max_lag_s, "horizon_s": horizon_s, "horizon_tol_s": horizon_tol_s}}
    if float(as_of) < T + horizon_s + horizon_tol_s:
        return dict(base, state="NOT_YET_MATURED", label=None)
    qs = [o for o in obs if o["kind"] == "QUOTE" and o["pool_address"] == pool_address and o["size_usd"] == size_usd
          and o["captured_at"] is not None and T <= o["captured_at"] <= float(as_of)]
    b = [o for o in qs if o["captured_at"] <= T + baseline_max_lag_s and o["state"] in ANSWERED]
    if not b:
        return dict(base, state="CENSORED_NO_BASELINE", label=None)
    b0 = b[0]
    if b0["state"] in ROUTE_LOST:
        return dict(base, state="EXIT_UNAVAILABLE_AT_BASELINE", label=None, baseline_id=b0["id"])
    h = [o for o in qs if abs(o["captured_at"] - (T + horizon_s)) <= horizon_tol_s and o["state"] in ANSWERED
         and o["captured_at"] > b0["captured_at"]]
    if not h:
        return dict(base, state="CENSORED_NO_HORIZON_READ", label=None, baseline_id=b0["id"])
    h0 = min(h, key=lambda o: (abs(o["captured_at"] - (T + horizon_s)), o["captured_at"]))
    if h0["state"] in ROUTE_LOST:
        return dict(base, state="ROUTE_LOST", label=1, baseline_id=b0["id"], horizon_id=h0["id"],
                    proceeds_ratio_0=b0["proceeds_ratio"], proceeds_ratio_h=None)
    ev = h0["proceeds_ratio"] <= b0["proceeds_ratio"] * (1.0 - drop)
    return dict(base, state="LABELED", label=int(ev), baseline_id=b0["id"], horizon_id=h0["id"],
                proceeds_ratio_0=b0["proceeds_ratio"], proceeds_ratio_h=h0["proceeds_ratio"])


def exit_context(obs: Sequence[dict], *, T: float, pool_address: str, size_usd: float) -> dict:
    """Size-specific exit context at time T (P44): the newest OK quote at this size on this pool captured at or before T, else
    EXECUTION_DATA_MISSING. A price forecast is never a profit claim without it."""
    vis = [o for o in visible_at(obs, T) if o["kind"] == "QUOTE" and o["pool_address"] == pool_address and o["size_usd"] == size_usd]
    ok = [o for o in vis if o["state"] == "OK"]
    if not ok:
        lost = [o for o in vis if o["state"] in ROUTE_LOST]
        return {"state": "ROUTE_LOST" if lost and (not ok) and lost[-1] is vis[-1] else "EXECUTION_DATA_MISSING", "size_usd": size_usd,
                "proceeds_ratio": None}
    q = ok[-1]
    return {"state": "OK", "size_usd": size_usd, "proceeds_ratio": q["proceeds_ratio"], "captured_at": q["captured_at"],
            "age_s": float(T) - q["captured_at"], "quote_id": q["id"]}
