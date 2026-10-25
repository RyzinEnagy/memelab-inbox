"""Forward market-depth collector (D-BT-034; predictive PI-D-020, approved by Elving on 2026-10-25 as PI-D-044).

Research only. Read-only public endpoints, no key, no wallet, no transaction. For every lab decision (a thesis row first
visible in a `data/state/latest.json` export within the last 24 h) it records, once per hourly run until 25 h after the
export commit:
- the pool the export names (token row `primary_pool`, else `graduated_pool`; when neither, the vendor's top pool from
  the first successful lookup, flagged VENDOR_TOP_POOL, every lookup kept with its outcome): reserves in token units and
  USD and the mint's USD price, from GeckoTerminal's multi-pool endpoint (up to 30 pools of one network per call);
- on Solana, sell quotes for the mint into USDC at fixed USD sizes from Jupiter's keyless quote endpoint. The token
  amount sold is size / the mint's USD price from the pool read made earlier in the same run, and that price, its pool and
  its read time are stored with the quote. A quote whose implied price (proceeds before the router's stated price
  impact, per token) differs from that pool price by more than 10% is PRICE_DISAGREES, not OK. Other chains have no free quote source here: QUOTE_UNSUPPORTED_CHAIN.

These are observations made after the decision: the first one comes at the first hourly run after the export, up to
about an hour later, and the lag is stored on every row (since_export_s). Every row keeps captured_at (UTC epoch seconds
when the response arrived), the request URL, the HTTP status and the sha256 of the raw body (the body is kept by hash).
Anything not read in a run (cap, deadline, failed pool read) gets a row that says why. Rows are append-only; one run per
UTC hour (a second run in the same hour does nothing).
"""
from __future__ import annotations

import json
import math
import time
from collections import Counter
from pathlib import Path
from typing import Callable

from . import store
from .sources import gecko, labstate
from .timeguard import utc_ts

SIZES_USD = (100.0, 500.0, 2000.0)
WINDOW_S = 24 * 3600            # a decision enters when its export commit is at most this old
ACTIVE_S = 25 * 3600            # and is collected until this long after the export commit (the 24 h point plus one run)
GT_SPACING_S = 10.0             # GeckoTerminal: at most one call every 10 s
GT_WINDOW_S = 60.0              # and at most 6 calls in any 60 s, counting the refresh step's calls just before
GT_WINDOW_MAX = 6
GT_MAX_CALLS = 6
GT_MULTI_MAX = 30
JUP_QUOTE = "https://api.jup.ag/swap/v1/quote"
JUP_PROVIDER = "jupiter"
JUP_SPACING_S = 2.2             # keyless limit 0.5 requests a second (30 a minute); 2.2 s is 27 a minute
JUP_MAX_CALLS = 48              # 16 pools at three sizes, the size of a usual daily export
SLIPPAGE_BPS = 300              # same as the lab's own quote reads; it changes only otherAmountThreshold, not outAmount
DEADLINE_S = 115.0              # no call, first or retry, starts after this many seconds of the run
HTTP_TIMEOUT_S = 10.0           # so the run ends by DEADLINE_S + HTTP_TIMEOUT_S plus database work
RETRY_WAIT_S = 5.0              # one retry after a 429, a 5xx or no answer, if the cap and the deadline allow it
RETRY_STATUS = (0, 429, 500, 502, 503, 504)
PRICE_TOLERANCE = 0.10          # quote's implied price / pool price outside 0.9 to 1.1 gives PRICE_DISAGREES
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDC_DECIMALS = 6
NETWORK = {"solana": "solana", "bsc": "bsc", "base": "base", "ethereum": "eth"}   # lab chain -> GeckoTerminal network id
EXPORT_PATH = "data/state/latest.json"


def _same(chain: str, a: str | None, b: str | None) -> bool:
    """Exact identity on Solana (base58 is case sensitive); EVM addresses compare without case."""
    if a is None or b is None:
        return False
    return a == b if chain == "solana" else a.lower() == b.lower()


def row_sha256(row: dict) -> str:
    """Identity of an exact thesis row: sha256 of the row without `id` (the same rule as predictive PI-D-021)."""
    return store.sha256({k: v for k, v in row.items() if k != "id"})


def _hash_order(*parts) -> str:
    return store.sha256([str(p) for p in parts])


# ---------------------------------------------------------------- decisions from the lab's exports

def export_decisions(repo: Path | str, ref: str = "refs/remotes/origin/main", now: float | None = None, window_s: float = WINDOW_S) -> dict:
    """Thesis rows first visible in an export commit of the last `window_s` (and not after `now`). The oldest export read
    is the baseline: its rows are known and never new (a shallow history cannot say when they first appeared). The
    decision time is the export commit time (PI-D-015); chain and pool come from the token row of that export (PI-D-021).
    A row that cannot be read is counted and skipped; it never makes the whole export unreadable."""
    now = time.time() if now is None else now
    versions = labstate.state_versions(Path(repo), ref)
    commits = []
    for c, ct, p in versions:
        if not commits or commits[-1][0] != c:
            commits.append((c, ct, []))
        commits[-1][2].append(p)
    out = {"status": "OK", "exports": len(commits), "baseline_commit": None, "latest_commit": None, "latest_time": None,
           "rows_unreadable": 0, "decisions": []}
    if len(commits) < 2:
        out["status"] = "NO_BASELINE" if commits else "NO_EXPORTS"
        return out
    out["baseline_commit"], out["latest_commit"], out["latest_time"] = commits[0][0], commits[-1][0], commits[-1][1]
    seen: set[tuple] = set()
    for i, (commit, ct, paths) in enumerate(commits):
        for path in sorted(paths, key=lambda p: p != EXPORT_PATH):
            t = labstate.load_version(Path(repo), commit, path)
            if t is None:
                continue
            toks = {k.get("mint"): k for k in t.get("tokens") or [] if isinstance(k, dict)}
            for row in t.get("theses") or []:
                try:
                    mint = row["mint"]
                    if not isinstance(mint, str) or not mint:
                        raise ValueError("mint")
                    created = utc_ts(row["created_at"])
                    ident = (mint, row_sha256(row))
                except Exception:
                    out["rows_unreadable"] += 1
                    continue
                if ident in seen:
                    continue
                seen.add(ident)
                if i == 0 or ct < now - window_s or ct > now:
                    continue
                tk = toks.get(mint) or {}
                pool, src = tk.get("primary_pool"), "EXPORT_PRIMARY_POOL"
                if not pool:
                    pool, src = tk.get("graduated_pool"), "EXPORT_GRADUATED_POOL"
                if not pool:
                    pool, src = None, "NONE_IN_EXPORT"
                out["decisions"].append({"chain": labstate.chain_of(mint, tk.get("chain")), "mint": mint, "pool_address": pool,
                                         "pool_source": src, "export_commit": commit, "export_time": ct, "export_path": path,
                                         "created_at": created, "row_sha256": ident[1], "status": row.get("status")})
    return out


def record_decision(con, d: dict, recorded_at: float) -> tuple[int | None, bool]:
    body = {k: d.get(k) for k in ("chain", "mint", "pool_address", "pool_source", "export_commit", "export_time", "created_at", "row_sha256", "status")}
    return store._insert(con, "bt_depth_decisions", dict(body, export_path=d.get("export_path"), recorded_at=recorded_at, content_hash=store.sha256(body)))


def _effective_pool(con, d: dict) -> tuple[str | None, str]:
    """The export's pool, else the pool of the first successful vendor lookup (fixed from then on)."""
    if d["pool_address"]:
        return d["pool_address"], d["pool_source"]
    r = con.execute("SELECT pool_address FROM bt_depth_pool_lookups WHERE decision_id=? AND state='OK' ORDER BY captured_at, id LIMIT 1", (d["id"],)).fetchone()
    return (r[0], "VENDOR_TOP_POOL") if r else (None, d["pool_source"])


def active_decisions(con, now: float, active_s: float = ACTIVE_S) -> list[dict]:
    return [dict(r) for r in con.execute("SELECT * FROM bt_depth_decisions WHERE export_time>=? AND export_time<=? ORDER BY export_time, id",
                                         (now - active_s, now)) if r["chain"] in NETWORK]


def active_pools(con, now: float, active_s: float = ACTIVE_S) -> list[dict]:
    """(chain, mint, pool) of decisions still inside their collection window, each with its newest decision."""
    best: dict[tuple, dict] = {}
    for d in active_decisions(con, now, active_s):
        pool, src = _effective_pool(con, d)
        if pool:
            best[(d["chain"], d["mint"], pool)] = dict(d, pool_address=pool, pool_source=src)
    return list(best.values())


def pending_lookups(con, now: float) -> list[dict]:
    return [d for d in active_decisions(con, now) if not d["pool_address"] and _effective_pool(con, d)[0] is None]


# ---------------------------------------------------------------- rows

def _snapshot(con, *, run_id: str, dec: dict, kind: str, provider: str, url: str | None, resp: dict | None, state: str,
              size_usd: float | None = None, token_amount: float | None = None, token_amount_raw: int | None = None, decimals: int | None = None,
              reserve_usd: float | None = None, price_usd: float | None = None, out_usd: float | None = None, price_impact: float | None = None,
              values: dict | None = None) -> None:
    captured = resp.get("t") if resp else None
    if resp and resp.get("attempts"):
        values = dict(values or {}, attempts=resp["attempts"])
    body = dict(run_id=run_id, decision_id=dec["id"], chain=dec["chain"], mint=dec["mint"], pool_address=dec["pool_address"], kind=kind,
                provider=provider, size_usd=size_usd, token_amount=token_amount, token_amount_raw=str(token_amount_raw) if token_amount_raw is not None else None,
                decimals=decimals, request_url=url, captured_at=captured, http_status=resp.get("status") if resp else None,
                raw_sha256=resp.get("sha") if resp else None, raw_ref=resp.get("raw_ref") if resp else None, state=state,
                since_export_s=(captured - dec["export_time"]) if captured is not None else None, reserve_usd=reserve_usd, price_usd=price_usd,
                out_usd=out_usd, price_impact=price_impact, value_json=values)
    store._insert(con, "bt_depth_snapshots", dict(body, recorded_at=time.time(), content_hash=store.sha256(body)))


def _lookup_row(con, *, run_id: str, dec: dict, url: str | None, resp: dict | None, state: str, pool: str | None, attempt: int) -> None:
    body = dict(run_id=run_id, decision_id=dec["id"], chain=dec["chain"], mint=dec["mint"], attempt=attempt, request_url=url,
                captured_at=resp.get("t") if resp else None, http_status=resp.get("status") if resp else None,
                raw_sha256=resp.get("sha") if resp else None, raw_ref=resp.get("raw_ref") if resp else None, state=state, pool_address=pool,
                value_json={"attempts": resp["attempts"]} if resp and resp.get("attempts") else None)
    store._insert(con, "bt_depth_pool_lookups", dict(body, recorded_at=time.time(), content_hash=store.sha256(body)))


def _num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def pool_values(chain: str, network: str, mint: str, item: dict, included: dict) -> tuple[str, dict]:
    """State and values of one pool entry; the mint must be the base or the quote token of the pool (identity check)."""
    a = item.get("attributes") or {}
    rel = item.get("relationships") or {}
    base = (((rel.get("base_token") or {}).get("data")) or {}).get("id") or ""
    quote = (((rel.get("quote_token") or {}).get("data")) or {}).get("id") or ""
    want = f"{network}_{mint}"
    side = "base" if _same(chain, base, want) else "quote" if _same(chain, quote, want) else None
    if side is None:
        return "IDENTITY_MISMATCH", {"base_token": base, "quote_token": quote}
    other_side = "quote" if side == "base" else "base"
    other = quote if side == "base" else base
    tok = included.get(base if side == "base" else quote) or {}
    v = {"side": side, "other_token": other.split("_", 1)[-1], "dex": (((rel.get("dex") or {}).get("data")) or {}).get("id"),
         "price_usd": _num(a.get(f"{side}_token_price_usd")), "price_field": f"{side}_token_price_usd", "reserve_usd": _num(a.get("reserve_in_usd")),
         "mint_balance": _num(a.get(f"{side}_token_balance")), "other_balance": _num(a.get(f"{other_side}_token_balance")),
         "mint_liquidity_usd": _num(a.get(f"{side}_token_liquidity_usd")), "other_liquidity_usd": _num(a.get(f"{other_side}_token_liquidity_usd")),
         "decimals": (tok.get("attributes") or {}).get("decimals"), "locked_liquidity_percentage": _num(a.get("locked_liquidity_percentage")),
         "volume_usd_h1": _num((a.get("volume_usd") or {}).get("h1")), "volume_usd_h24": _num((a.get("volume_usd") or {}).get("h24")),
         "transactions_h1": (a.get("transactions") or {}).get("h1")}
    if v["reserve_usd"] is None and v["mint_balance"] is None:
        return "NO_RESERVES", v
    return "OK", v


def _quote_state(resp: dict) -> str:
    st = resp.get("status")
    if st is None:
        return resp["skip"]
    if st == 200:
        return "OK" if resp.get("json") and resp["json"].get("outAmount") not in (None, "") else "BAD_BODY"
    code = str((resp.get("json") or {}).get("errorCode") or "")
    if st == 400 and code in ("COULD_NOT_FIND_ANY_ROUTE", "NO_ROUTES_FOUND"):
        return "NO_ROUTE"
    if st == 400 and code == "TOKEN_NOT_TRADABLE":
        return "NOT_TRADABLE"
    return "SOURCE_BLOCKED" if st == 0 else f"HTTP_{st}"


def _read_state(resp: dict) -> str:
    st = resp.get("status")
    if st is None:
        return resp["skip"]
    if st != 200 or resp.get("json") is None:
        return "SOURCE_BLOCKED" if st == 0 else f"HTTP_{st}"
    return "OK"


# ---------------------------------------------------------------- one run

class _Run:
    def __init__(self, con, now, http_get, clock, sleep, gt_max_calls, jup_max_calls, gt_spacing_s, jup_spacing_s, deadline_s,
                 gt_prior_calls, gt_prior_end):
        self.con, self.now, self.http_get, self.clock, self.sleep = con, now, http_get, clock, sleep
        self.t0 = clock()
        self.deadline = self.t0 + deadline_s
        self.gt = gecko.Budget(max_calls=gt_max_calls, min_spacing_s=gt_spacing_s, max_retries=1, sleep=sleep, clock=clock)
        self.jup = gecko.Budget(max_calls=jup_max_calls, min_spacing_s=jup_spacing_s, max_retries=1, sleep=sleep, clock=clock)
        self.gt._last = -1e18
        self.jup._last = -1e18
        # GeckoTerminal call times, the refresh step's included (all counted at its end, which is earlier than any of them)
        self.gt_stamps = [float(gt_prior_end)] * int(gt_prior_calls) if gt_prior_end is not None else []

    def time_left(self) -> bool:
        return self.clock() < self.deadline

    def gt_ready_at(self) -> float:
        t = self.gt._last + self.gt.min_spacing
        recent = sorted(self.gt_stamps)[-GT_WINDOW_MAX:]
        if len(recent) >= GT_WINDOW_MAX:
            t = max(t, recent[0] + GT_WINDOW_S + 0.5)
        return t

    def get(self, url: str, host: str) -> dict:
        """One read with at most one retry. Never raises on a cap, a deadline, a 429, a 5xx or a timeout: the answer says
        what happened (status None and `skip` when no call was made)."""
        budget = self.gt if host == "gt" else self.jup
        provider = gecko.PROVIDER if host == "gt" else JUP_PROVIDER
        attempts: list[dict] = []
        final, skip = None, None
        for k in range(2):
            if budget.calls >= budget.max_calls:
                skip = "NOT_ATTEMPTED_CAP" if not attempts else None
                break
            ready = min(self.gt_ready_at() if host == "gt" else budget._last + budget.min_spacing, self.deadline)
            if self.clock() < ready:
                self.sleep(ready - self.clock())
            if not self.time_left():
                skip = "NOT_ATTEMPTED_DEADLINE" if not attempts else None
                break
            budget.calls += 1
            budget._last = self.clock()
            if host == "gt":
                self.gt_stamps.append(budget._last)
            status, body = self.http_get(url)
            t = self.clock()
            raw_ref = store.save_raw(provider, body) if body else None
            final = {"t": t, "status": status, "raw_ref": raw_ref, "sha": raw_ref.rsplit("/", 1)[-1][:-5] if raw_ref else None, "body": body}
            attempts.append({"status": status, "captured_at": t, "raw_sha256": final["sha"]})
            if status in RETRY_STATUS and k == 0 and budget.calls < budget.max_calls and self.clock() + RETRY_WAIT_S < self.deadline:
                budget.retries += 1
                self.sleep(RETRY_WAIT_S)
                continue
            break
        if final is None:
            return {"status": None, "skip": skip or "NOT_ATTEMPTED_DEADLINE", "attempts": []}
        resp = dict(final, attempts=attempts if len(attempts) > 1 else [])
        resp.pop("body")
        try:
            resp["json"] = json.loads(final["body"]) if final["body"] else None
        except ValueError:
            resp["json"] = None
        if len(attempts) == 1 and attempts[0]["status"] in RETRY_STATUS:
            resp["retry_refused"] = "cap" if budget.calls >= budget.max_calls else "deadline"
        return resp


def collect(con, *, exports: dict | None, now: float | None = None, http_get=None, clock: Callable[[], float] = time.time, sleep=time.sleep,
            sizes=SIZES_USD, gt_max_calls: int = GT_MAX_CALLS, jup_max_calls: int = JUP_MAX_CALLS, gt_spacing_s: float = GT_SPACING_S,
            jup_spacing_s: float = JUP_SPACING_S, deadline_s: float = DEADLINE_S, gt_prior_calls: int = 0, gt_prior_end: float | None = None,
            price_tolerance: float = PRICE_TOLERANCE) -> dict:
    """One collector run. `exports` is export_decisions(...) or None (lab exports not reachable: collect for the
    decisions already stored). `gt_prior_calls` GeckoTerminal calls made by the refresh step that ended at `gt_prior_end`
    count against the 6-in-60-s window. Commits after every read, so an interrupted run leaves whole rows only."""
    R = _Run(con, None, http_get or (lambda u: gecko.default_http_get(u, timeout=HTTP_TIMEOUT_S)), clock, sleep, gt_max_calls, jup_max_calls,
             gt_spacing_s, jup_spacing_s, deadline_s, gt_prior_calls, gt_prior_end)
    now = R.t0 if now is None else now
    R.now = now
    run_id = "depth-" + time.strftime("%Y%m%dT%HZ", time.gmtime(now))
    summary = {"run_id": run_id, "status": "RAN", "exports": {k: v for k, v in (exports or {"status": "NOT_READ"}).items() if k != "decisions"},
               "decisions_new": 0, "deadline_hit": False, "lookups": Counter(), "pool_snapshots": Counter(), "quotes": Counter()}
    done_before = con.execute("SELECT 1 FROM bt_depth_snapshots WHERE run_id=? UNION SELECT 1 FROM bt_depth_pool_lookups WHERE run_id=? LIMIT 1",
                              (run_id, run_id)).fetchone()
    if done_before:
        summary.update(status="SKIPPED_SAME_HOUR", calls={"geckoterminal": 0, "jupiter": 0, "retries": 0}, quote_source="NOT_USED", wall_s=0.0)
        for k in ("lookups", "pool_snapshots", "quotes"):
            summary[k] = {}
        return summary

    # 1. every new decision is recorded at once, with or without a pool
    for d in (exports or {}).get("decisions", []):
        pool_source = "UNSUPPORTED_CHAIN" if d["chain"] not in NETWORK else d["pool_source"]
        summary["decisions_new"] += record_decision(con, dict(d, pool_source=pool_source), now)[1]
    con.commit()

    # 2. GeckoTerminal reads in order (per network: pool lookups, then pools), quotes in the gaps
    pools_read: dict[tuple, tuple[str, dict, dict]] = {}       # (chain, mint, pool) -> (state, values, resp)
    lookups_done: set[int] = set()
    gt_tasks: list[tuple] = []
    for ch in sorted(NETWORK, key=lambda c: c != "solana"):    # Solana first: its quotes wait for its pool read
        gt_tasks += [("lookup", ch), ("pools", ch)]
    quote_q: list[tuple] = []

    def lookup_todo(chain):
        return [d for d in pending_lookups(con, now) if d["chain"] == chain and d["id"] not in lookups_done][:GT_MULTI_MAX]

    def pools_todo(chain):
        return [p for p in active_pools(con, now) if p["chain"] == chain and (chain, p["mint"], p["pool_address"]) not in pools_read][:GT_MULTI_MAX]

    def run_lookup(chain):
        lst = lookup_todo(chain)
        net = NETWORK[chain]
        url = f"{gecko.BASE}/networks/{net}/tokens/multi/{','.join(d['mint'] for d in lst)}?include=top_pools"
        resp = R.get(url, "gt")
        state = _read_state(resp)
        found = {}
        if state == "OK":
            for it in resp["json"].get("data") or []:
                tops = (((it.get("relationships") or {}).get("top_pools") or {}).get("data")) or []
                found[it.get("id") or ""] = tops[0]["id"].split("_", 1)[-1] if tops else None
        for d in lst:
            lookups_done.add(d["id"])
            attempt = 1 + con.execute("SELECT COUNT(*) FROM bt_depth_pool_lookups WHERE decision_id=? AND state NOT LIKE 'NOT_ATTEMPTED%'", (d["id"],)).fetchone()[0]
            pool = None
            st = state
            if state == "OK":
                key = next((k for k in found if _same(chain, k, f"{net}_{d['mint']}")), None)
                pool = found.get(key) if key else None
                st = "OK" if pool else "NO_POOL"
            _lookup_row(con, run_id=run_id, dec=d, url=url if resp.get("status") is not None else None, resp=resp, state=st, pool=pool,
                        attempt=attempt if resp.get("status") is not None else attempt - 1)
            summary["lookups"][st] += 1
        con.commit()

    def quote_key(p):
        # runs in which the pool got an answered quote (any state), so a pool without a route cannot keep the front forever
        n = con.execute("SELECT COUNT(DISTINCT run_id) FROM bt_depth_snapshots WHERE kind='QUOTE' AND http_status IS NOT NULL AND chain=? AND mint=? "
                        "AND pool_address=? AND captured_at>=?", (p["chain"], p["mint"], p["pool_address"], p["export_time"])).fetchone()[0]
        last = con.execute("SELECT MAX(captured_at) FROM bt_depth_snapshots WHERE kind='QUOTE' AND http_status IS NOT NULL AND chain=? AND mint=? "
                           "AND pool_address=?", (p["chain"], p["mint"], p["pool_address"])).fetchone()[0]
        return (n, -1.0 if last is None else last, _hash_order(run_id, p["chain"], p["mint"], p["pool_address"]))

    def run_pools(chain):
        todo = pools_todo(chain)
        net = NETWORK[chain]
        url = f"{gecko.BASE}/networks/{net}/pools/multi/{','.join(p['pool_address'] for p in todo)}?include=base_token,quote_token&include_composition=true"
        if len(todo) == GT_MULTI_MAX:
            gt_tasks.insert(0, ("pools", chain))                    # more pools on this network than one call holds
        resp = R.get(url, "gt")
        state0 = _read_state(resp)
        items, included = {}, {}
        if state0 == "OK":
            for it in resp["json"].get("data") or []:
                items[((it.get("attributes") or {}).get("address")) or (it.get("id") or "").split("_", 1)[-1]] = it
            for it in resp["json"].get("included") or []:
                included[it.get("id")] = it
        for p in todo:
            it = next((v for k, v in items.items() if _same(chain, k, p["pool_address"])), None)
            if state0 != "OK":
                state, v = state0, {}
            elif it is None:
                state, v = "NOT_IN_RESPONSE", {}
            else:
                state, v = pool_values(chain, net, p["mint"], it, included)
            pools_read[(chain, p["mint"], p["pool_address"])] = (state, v, resp)
            _snapshot(con, run_id=run_id, dec=p, kind="POOL", provider=gecko.PROVIDER, url=url if resp.get("status") is not None else None, resp=resp,
                      state=state, decimals=v.get("decimals"), reserve_usd=v.get("reserve_usd"), price_usd=v.get("price_usd"), values=v or None)
            summary["pool_snapshots"][state] += 1
            if chain == "solana" and state == "OK":
                quote_q.append((p, v, resp))
        con.commit()
        quote_q.sort(key=lambda x: quote_key(x[0]))

    def run_quote(p: dict, v: dict, pool_resp: dict, size: float) -> None:
        price, dec = v.get("price_usd"), v.get("decimals")
        src = {"price_usd_used": price, "price_source": f"geckoterminal pool {p['pool_address']} {v.get('price_field')}",
               "price_captured_at": pool_resp.get("t"), "price_raw_sha256": pool_resp.get("sha")}
        if not price or price <= 0 or dec is None:
            _snapshot(con, run_id=run_id, dec=p, kind="QUOTE", provider=JUP_PROVIDER, url=None, resp=None, state="NO_PRICE_OR_DECIMALS", size_usd=size, values=src)
            summary["quotes"]["NO_PRICE_OR_DECIMALS"] += 1
            return
        amount = size / price
        raw = int(math.floor(amount * 10 ** int(dec)))
        if raw <= 0:
            _snapshot(con, run_id=run_id, dec=p, kind="QUOTE", provider=JUP_PROVIDER, url=None, resp=None, state="AMOUNT_ZERO", size_usd=size, values=src)
            summary["quotes"]["AMOUNT_ZERO"] += 1
            return
        url = f"{JUP_QUOTE}?inputMint={p['mint']}&outputMint={USDC}&amount={raw}&slippageBps={SLIPPAGE_BPS}&swapMode=ExactIn"
        resp = R.get(url, "jup")
        state = _quote_state(resp)
        j = resp.get("json") or {}
        vals, out_usd, impact = dict(src), None, None
        if state == "OK":
            if j.get("inputMint") != p["mint"] or j.get("outputMint") != USDC or str(j.get("inAmount")) != str(raw) or j.get("swapMode") not in (None, "ExactIn"):
                state = "IDENTITY_MISMATCH"
            out_usd = _num(j.get("outAmount"))
            out_usd = out_usd / 10 ** USDC_DECIMALS if out_usd is not None else None
            impact = _num(j.get("priceImpactPct"))
            swap_usd = _num(j.get("swapUsdValue"))
            # The router's own price for the mint: proceeds before its stated price impact, per token sold. A sale that
            # loses far more than the router's price impact was sized at a price the market does not pay (skeptic M4).
            # swapUsdValue is not used for this: it values the output, so it falls with real impact too.
            implied = (out_usd / ((1.0 - impact) * amount)) if out_usd and impact is not None and 0.0 <= impact < 1.0 and amount > 0 else None
            check = (implied / price) if implied is not None else None
            if state == "OK" and check is not None and abs(check - 1.0) > price_tolerance:
                state = "PRICE_DISAGREES"      # the pool's price and the router's price for the same tokens disagree
            vals.update(out_amount_raw=j.get("outAmount"), other_amount_threshold=j.get("otherAmountThreshold"), swap_usd_value=swap_usd,
                        implied_price_usd=implied, implied_over_pool_price=check,
                        price_check="NO_PRICE_IMPACT" if check is None else ("OK" if abs(check - 1.0) <= price_tolerance else "DISAGREES"),
                        context_slot=j.get("contextSlot"), slippage_bps=j.get("slippageBps"),
                        route=[{"label": (s.get("swapInfo") or {}).get("label"), "amm": (s.get("swapInfo") or {}).get("ammKey"), "percent": s.get("percent")}
                               for s in j.get("routePlan") or []],
                        proceeds_ratio=(out_usd / size) if out_usd is not None else None)
        elif j:
            vals.update(error_code=j.get("errorCode"), error=str(j.get("error") or j.get("message") or "")[:200])
        if resp.get("retry_refused"):
            vals["retry_refused"] = resp["retry_refused"]
        _snapshot(con, run_id=run_id, dec=p, kind="QUOTE", provider=JUP_PROVIDER, url=url if resp.get("status") is not None else None, resp=resp,
                  state=state, size_usd=size, token_amount=amount, token_amount_raw=raw, decimals=int(dec), price_usd=price, out_usd=out_usd,
                  price_impact=impact, values=vals)
        summary["quotes"][state] += 1
        con.commit()

    quotes: list[tuple] = []
    while True:
        while gt_tasks and not (lookup_todo(gt_tasks[0][1]) if gt_tasks[0][0] == "lookup" else pools_todo(gt_tasks[0][1])):
            gt_tasks.pop(0)                                         # nothing to read: no call
        if not (gt_tasks or quote_q or quotes) or not R.time_left():
            break
        if gt_tasks and R.gt.calls >= R.gt.max_calls:
            gt_tasks.clear()                                        # the pools left get NOT_ATTEMPTED_CAP rows below
            continue
        if gt_tasks and R.clock() >= R.gt_ready_at():
            kind, ch = gt_tasks.pop(0)
            (run_lookup if kind == "lookup" else run_pools)(ch)
            continue
        if not quotes and quote_q:
            p, v, presp = quote_q.pop(0)
            quotes = [(p, v, presp, s) for s in sizes]
        if quotes:
            if R.jup.calls >= R.jup.max_calls:
                quotes, quote_q = [], []                            # the quotes left get NOT_ATTEMPTED_CAP rows below
                continue
            run_quote(*quotes.pop(0))
            continue
        R.sleep(max(0.0, min(R.gt_ready_at(), R.deadline) - R.clock()))

    # 3. the record of what was not read in this run, and why
    why = lambda b: "NOT_ATTEMPTED_CAP" if b.calls >= b.max_calls else "NOT_ATTEMPTED_DEADLINE"
    summary["deadline_hit"] = not R.time_left()
    for d in pending_lookups(con, now):
        if d["id"] not in lookups_done:
            _lookup_row(con, run_id=run_id, dec=d, url=None, resp=None, state=why(R.gt), pool=None,
                        attempt=con.execute("SELECT COUNT(*) FROM bt_depth_pool_lookups WHERE decision_id=? AND state NOT LIKE 'NOT_ATTEMPTED%'", (d["id"],)).fetchone()[0])
            summary["lookups"][why(R.gt)] += 1
    for p in active_pools(con, now):
        key = (p["chain"], p["mint"], p["pool_address"])
        if key not in pools_read:
            _snapshot(con, run_id=run_id, dec=p, kind="POOL", provider=gecko.PROVIDER, url=None, resp=None, state=why(R.gt))
            summary["pool_snapshots"][why(R.gt)] += 1
            pstate = why(R.gt)
        else:
            pstate = pools_read[key][0]
        if p["chain"] != "solana":
            _snapshot(con, run_id=run_id, dec=p, kind="QUOTE", provider="none", url=None, resp=None, state="QUOTE_UNSUPPORTED_CHAIN")
            summary["quotes"]["QUOTE_UNSUPPORTED_CHAIN"] += 1
            continue
        have = {r[0] for r in con.execute("SELECT size_usd FROM bt_depth_snapshots WHERE run_id=? AND kind='QUOTE' AND chain=? AND mint=? AND pool_address=?",
                                          (run_id, *key))}
        for s in sizes:
            if s in have:
                continue
            state = why(R.jup) if pstate == "OK" else f"SKIPPED_POOL_{pstate}"
            _snapshot(con, run_id=run_id, dec=p, kind="QUOTE", provider=JUP_PROVIDER, url=None, resp=None, state=state, size_usd=s)
            summary["quotes"][state] += 1
    con.commit()
    q = summary["quotes"]
    called = {s: n for s, n in q.items() if not (s.startswith("NOT_ATTEMPTED") or s.startswith("SKIPPED_POOL") or s in ("QUOTE_UNSUPPORTED_CHAIN", "NO_PRICE_OR_DECIMALS", "AMOUNT_ZERO"))}
    blocked = sum(n for s, n in called.items() if s in ("SOURCE_BLOCKED", "HTTP_401", "HTTP_403", "HTTP_429"))
    summary["quote_source"] = ("NOT_USED" if not called else "QUOTE_SOURCE_BLOCKED" if blocked and not (q.get("OK") or q.get("PRICE_DISAGREES")) else "OK")
    summary.update(calls={"geckoterminal": R.gt.calls, "jupiter": R.jup.calls, "retries": R.gt.retries + R.jup.retries},
                   pools_active=len(active_pools(con, now)), wall_s=round(R.clock() - R.t0, 1))
    for k in ("lookups", "pool_snapshots", "quotes"):
        summary[k] = dict(summary[k])
    return summary


# ---------------------------------------------------------------- reading back

def status(con, now: float, hours: float = 48.0) -> dict:
    """Per decision: pool and its source, pool lookups, lag from the export commit to the first pool snapshot and first OK
    quote, and how many hours of the 0 to 24 h grid have a pool snapshot and an OK quote."""
    out = []
    for r in con.execute("SELECT * FROM bt_depth_decisions WHERE export_time>=? ORDER BY export_time, id", (now - hours * 3600,)):
        d = dict(r)
        pool, src = _effective_pool(con, d)
        lk = con.execute("SELECT state, COUNT(*) n FROM bt_depth_pool_lookups WHERE decision_id=? GROUP BY state", (d["id"],)).fetchall()
        snaps = con.execute("SELECT kind, state, captured_at FROM bt_depth_snapshots WHERE chain=? AND mint=? AND pool_address IS ? AND captured_at>=? "
                            "AND captured_at<=? ORDER BY captured_at", (d["chain"], d["mint"], pool, d["export_time"], d["export_time"] + ACTIVE_S)).fetchall()
        pool_ok = [s["captured_at"] for s in snaps if s["kind"] == "POOL" and s["state"] == "OK"]
        quote_ok = [s["captured_at"] for s in snaps if s["kind"] == "QUOTE" and s["state"] == "OK"]
        grid = lambda ts: len({int((t - d["export_time"]) // 3600) for t in ts if t - d["export_time"] < ACTIVE_S})
        out.append({"chain": d["chain"], "mint": d["mint"], "pool": pool, "pool_source": src, "status": d["status"], "export_time": d["export_time"],
                    "lookups": {x["state"]: x["n"] for x in lk}, "first_pool_lag_s": round(pool_ok[0] - d["export_time"], 1) if pool_ok else None,
                    "first_quote_lag_s": round(quote_ok[0] - d["export_time"], 1) if quote_ok else None,
                    "pool_hours_of_25": grid(pool_ok), "quote_hours_of_25": grid(quote_ok),
                    "states": dict(Counter(f"{s['kind']}:{s['state']}" for s in snaps))})
    return {"decisions": len(out), "rows": out,
            "snapshots": dict(Counter(f"{r[0]}:{r[1]}" for r in con.execute("SELECT kind, state FROM bt_depth_snapshots")))}
