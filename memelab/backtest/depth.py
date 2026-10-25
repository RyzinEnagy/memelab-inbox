"""Forward market-depth collector (D-BT-034; predictive PI-D-020, approved by Elving on 2026-10-25 as PI-D-044).

Research only. Read-only public endpoints, no key, no wallet, no transaction. For every lab decision (a thesis row first
visible in a `data/state/latest.json` export within the last 24 h) it records, once per hourly run until 25 h after the
export commit:
- the pool the export names (token row `primary_pool`, else `graduated_pool`; when neither, the vendor's top pool at the
  first collect, flagged VENDOR_TOP_POOL): reserves in token units and USD, price, from GeckoTerminal's multi-pool
  endpoint (one call for up to 30 pools of one network, `include_composition=true`);
- on Solana, executable sell quotes for the mint at fixed USD sizes into USDC from Jupiter's keyless quote endpoint
  (api.jup.ag/swap/v1/quote, 0.5 requests per second without a key). The token amount sold is size / the pool's USD
  price from the same run, and is stored. Other chains have no free quote source here: QUOTE_UNSUPPORTED_CHAIN.

Every row keeps captured_at (UTC epoch seconds when the response arrived), the request URL, the HTTP status, the sha256
of the raw body (the body itself is kept by hash under the raw folder), and the time since the export commit. Rows are
append-only. A failed or missing read is a row with its state, never a made-up value.
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

SIZES_USD = (100.0, 500.0, 2000.0)
WINDOW_S = 24 * 3600            # a decision enters when its export commit is at most this old
ACTIVE_S = 25 * 3600            # and is collected until this long after the export commit (the 24 h point plus one run)
GT_SPACING_S = 10.0             # GeckoTerminal at most 6 calls a minute; the first call waits too (refresh ran just before)
GT_MAX_CALLS = 6
GT_MULTI_MAX = 30
JUP_QUOTE = "https://api.jup.ag/swap/v1/quote"
JUP_PROVIDER = "jupiter"
JUP_SPACING_S = 2.5             # keyless limit 0.5 requests per second
JUP_MAX_CALLS = 40
SLIPPAGE_BPS = 300              # same as the lab's own quote reads; it changes only otherAmountThreshold, not outAmount
DEADLINE_S = 100.0              # no new call starts after this many seconds of the run
HTTP_TIMEOUT_S = 10.0           # one slow answer cannot hold the step: worst case after the deadline is about 26 s
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


# ---------------------------------------------------------------- decisions from the lab's exports

def export_decisions(repo: Path | str, ref: str = "refs/remotes/origin/main", now: float | None = None, window_s: float = WINDOW_S) -> dict:
    """Thesis rows first visible in an export commit of the last `window_s`. The oldest export read is the baseline:
    its rows are known and never new (a shallow history cannot say when they first appeared). The decision time is the
    export commit time (PI-D-015); chain and pool come from the token row of that export (PI-D-021)."""
    now = time.time() if now is None else now
    versions = labstate.state_versions(Path(repo), ref)
    commits = []
    for c, ct, p in versions:
        if not commits or commits[-1][0] != c:
            commits.append((c, ct, []))
        commits[-1][2].append(p)
    out = {"status": "OK", "exports": len(commits), "baseline_commit": None, "latest_commit": None, "latest_time": None, "decisions": []}
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
            toks = {k["mint"]: k for k in t.get("tokens") or []}
            for row in t.get("theses") or []:
                ident = (row["mint"], row_sha256(row))
                if ident in seen:
                    continue
                seen.add(ident)
                if i == 0 or ct < now - window_s or ct > now:
                    continue
                tk = toks.get(row["mint"]) or {}
                pool, src = tk.get("primary_pool"), "EXPORT_PRIMARY_POOL"
                if not pool:
                    pool, src = tk.get("graduated_pool"), "EXPORT_GRADUATED_POOL"
                if not pool:
                    pool, src = None, None
                out["decisions"].append({"chain": labstate.chain_of(row["mint"], tk.get("chain")), "mint": row["mint"], "pool_address": pool,
                                         "pool_source": src, "export_commit": commit, "export_time": ct, "export_path": path,
                                         "created_at": float(row["created_at"]), "row_sha256": ident[1], "status": row.get("status")})
    return out


def record_decision(con, d: dict, recorded_at: float) -> tuple[int | None, bool]:
    body = {k: d.get(k) for k in ("chain", "mint", "pool_address", "pool_source", "export_commit", "export_time", "created_at", "row_sha256", "status")}
    return store._insert(con, "bt_depth_decisions", dict(body, export_path=d.get("export_path"), pool_resolved_at=d.get("pool_resolved_at"),
                                                         recorded_at=recorded_at, content_hash=store.sha256(body)))


def active_pools(con, now: float, active_s: float = ACTIVE_S) -> list[dict]:
    """(chain, mint, pool) of decisions still inside their collection window, each with its newest decision."""
    rows = con.execute("SELECT * FROM bt_depth_decisions WHERE pool_address IS NOT NULL AND export_time>=? AND export_time<=? "
                       "ORDER BY export_time, id", (now - active_s, now)).fetchall()
    best: dict[tuple, dict] = {}
    for r in rows:
        if r["chain"] in NETWORK:
            best[(r["chain"], r["mint"], r["pool_address"])] = dict(r)
    return list(best.values())


# ---------------------------------------------------------------- snapshots

def _snapshot(con, *, run_id: str, dec: dict, kind: str, provider: str, url: str | None, resp: dict | None, state: str,
              size_usd: float | None = None, token_amount: float | None = None, token_amount_raw: int | None = None, decimals: int | None = None,
              reserve_usd: float | None = None, price_usd: float | None = None, out_usd: float | None = None, price_impact: float | None = None,
              values: dict | None = None) -> None:
    captured = resp["t"] if resp else None
    body = dict(run_id=run_id, decision_id=dec["id"], chain=dec["chain"], mint=dec["mint"], pool_address=dec["pool_address"], kind=kind,
                provider=provider, size_usd=size_usd, token_amount=token_amount, token_amount_raw=str(token_amount_raw) if token_amount_raw is not None else None,
                decimals=decimals, request_url=url, captured_at=captured, http_status=resp["status"] if resp else None,
                raw_sha256=resp.get("sha") if resp else None, raw_ref=resp.get("raw_ref") if resp else None, state=state,
                since_export_s=(captured - dec["export_time"]) if captured is not None else None, reserve_usd=reserve_usd, price_usd=price_usd,
                out_usd=out_usd, price_impact=price_impact, value_json=values)
    store._insert(con, "bt_depth_snapshots", dict(body, recorded_at=time.time(), content_hash=store.sha256(body)))


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
    other = quote if side == "base" else base
    tok = included.get(base if side == "base" else quote) or {}
    v = {"side": side, "other_token": other.split("_", 1)[-1], "dex": (((rel.get("dex") or {}).get("data")) or {}).get("id"),
         "price_usd": _num(a.get(f"{side}_token_price_usd")), "reserve_usd": _num(a.get("reserve_in_usd")),
         "mint_balance": _num(a.get(f"{side}_token_balance")), "other_balance": _num(a.get(f"{'quote' if side == 'base' else 'base'}_token_balance")),
         "mint_liquidity_usd": _num(a.get(f"{side}_token_liquidity_usd")),
         "other_liquidity_usd": _num(a.get(f"{'quote' if side == 'base' else 'base'}_token_liquidity_usd")),
         "decimals": (tok.get("attributes") or {}).get("decimals"), "locked_liquidity_percentage": _num(a.get("locked_liquidity_percentage")),
         "volume_usd_h1": _num((a.get("volume_usd") or {}).get("h1")), "volume_usd_h24": _num((a.get("volume_usd") or {}).get("h24")),
         "transactions_h1": (a.get("transactions") or {}).get("h1")}
    if v["reserve_usd"] is None and v["mint_balance"] is None:
        return "NO_RESERVES", v
    return "OK", v


def _quote_state(resp: dict) -> str:
    if resp["status"] == 200:
        return "OK" if resp.get("json") and resp["json"].get("outAmount") not in (None, "") else "BAD_BODY"
    code = str((resp.get("json") or {}).get("errorCode") or "")
    if resp["status"] == 400 and code in ("COULD_NOT_FIND_ANY_ROUTE", "NO_ROUTES_FOUND"):
        return "NO_ROUTE"
    if resp["status"] == 400 and code == "TOKEN_NOT_TRADABLE":
        return "NOT_TRADABLE"
    return "SOURCE_BLOCKED" if resp["status"] == 0 else f"HTTP_{resp['status']}"


# ---------------------------------------------------------------- one run

class _Http:
    """Wraps an http_get so the time the response arrived, the status and the body are kept for the row."""

    def __init__(self, http_get: Callable[[str], tuple[int, bytes]], clock: Callable[[], float]):
        self.http_get, self.clock, self.last = http_get, clock, None

    def __call__(self, url: str) -> tuple[int, bytes]:
        status, body = self.http_get(url)
        self.last = {"t": self.clock(), "status": status, "body": body}
        return status, body


def _get(url: str, budget: gecko.Budget, http: _Http, provider: str) -> dict:
    status, d, raw_ref = gecko.get_json(url, budget, http, provider=provider)
    last = http.last or {"t": budget.clock(), "status": status, "body": b""}
    body = last["body"] or b""
    if raw_ref is None and body:
        raw_ref = store.save_raw(provider, body)    # error bodies are kept too (no route, rate limit); they name no secret
    resp = {"t": last["t"], "status": status, "raw_ref": raw_ref, "sha": raw_ref.rsplit("/", 1)[-1][:-5] if raw_ref else None, "json": d}
    if d is None and body:
        try:
            resp["json"] = json.loads(body)
        except ValueError:
            pass
    return resp


def collect(con, *, exports: dict | None, now: float | None = None, http_get=None, clock: Callable[[], float] = time.time, sleep=time.sleep,
            sizes=SIZES_USD, gt_max_calls: int = GT_MAX_CALLS, jup_max_calls: int = JUP_MAX_CALLS, gt_spacing_s: float = GT_SPACING_S,
            jup_spacing_s: float = JUP_SPACING_S, deadline_s: float = DEADLINE_S) -> dict:
    """One collector run. `exports` is export_decisions(...) or None (lab exports not reachable: collect for the
    decisions already stored). Commits after every call, so an interrupted run leaves whole rows only."""
    t0 = clock()
    now = t0 if now is None else now
    http_get = http_get or (lambda u: gecko.default_http_get(u, timeout=HTTP_TIMEOUT_S))
    run_id = "depth-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(now))
    gt = gecko.Budget(max_calls=gt_max_calls, min_spacing_s=gt_spacing_s, max_retries=1, sleep=sleep, clock=clock)
    gt._last = t0                                   # refresh made GeckoTerminal calls just before this step
    jup = gecko.Budget(max_calls=jup_max_calls, min_spacing_s=jup_spacing_s, max_retries=1, sleep=sleep, clock=clock)
    http = _Http(http_get, clock)
    summary = {"run_id": run_id, "exports": {k: v for k, v in (exports or {"status": "NOT_READ"}).items() if k != "decisions"},
               "decisions_new": 0, "unresolved_pools": 0, "deadline_hit": False, "pool_snapshots": Counter(), "quotes": Counter(), "not_attempted": Counter()}

    def time_left() -> bool:
        return clock() - t0 < deadline_s

    # 1. new decisions; a decision whose export names no pool waits for the vendor's top pool
    unresolved: dict[str, list[dict]] = {}
    for d in (exports or {}).get("decisions", []):
        if con.execute("SELECT 1 FROM bt_depth_decisions WHERE chain=? AND mint=? AND row_sha256=?", (d["chain"], d["mint"], d["row_sha256"])).fetchone():
            continue
        if d["chain"] not in NETWORK:
            summary["decisions_new"] += record_decision(con, dict(d, pool_source="UNSUPPORTED_CHAIN"), now)[1]
        elif d["pool_address"]:
            summary["decisions_new"] += record_decision(con, d, now)[1]
        else:
            unresolved.setdefault(d["chain"], []).append(d)
    con.commit()

    gt_tasks: list[tuple] = []
    for ch in sorted(NETWORK, key=lambda c: c != "solana"):       # Solana first: its quotes wait for its pool read
        lst = unresolved.get(ch) or []
        gt_tasks += [("resolve", ch, lst[i:i + GT_MULTI_MAX]) for i in range(0, len(lst), GT_MULTI_MAX)]
        gt_tasks.append(("pools", ch))
    pools_done: set[tuple] = set()
    quote_q: list[tuple] = []

    def run_gt(task) -> None:
        if task[0] == "resolve":
            _, chain, lst = task
            net = NETWORK[chain]
            url = f"{gecko.BASE}/networks/{net}/tokens/multi/{','.join(d['mint'] for d in lst)}?include=top_pools"
            resp = _get(url, gt, http, gecko.PROVIDER)
            if resp["status"] != 200 or resp["json"] is None:
                summary["unresolved_pools"] += len(lst)      # retried next run while the export is inside the window
                return
            found = {}
            for it in resp["json"].get("data") or []:
                tops = (((it.get("relationships") or {}).get("top_pools") or {}).get("data")) or []
                found[it.get("id") or ""] = tops[0]["id"].split("_", 1)[-1] if tops else None
            for d in lst:
                key = next((k for k in found if _same(chain, k, f"{net}_{d['mint']}")), None)
                pool = found.get(key) if key else None
                record_decision(con, dict(d, pool_address=pool, pool_source="VENDOR_TOP_POOL" if pool else "NO_POOL", pool_resolved_at=resp["t"]), now)
                summary["decisions_new"] += 1
            con.commit()
            return
        _, chain = task
        net = NETWORK[chain]
        todo = [p for p in active_pools(con, now) if p["chain"] == chain and (chain, p["mint"], p["pool_address"]) not in pools_done][:GT_MULTI_MAX]
        if not todo:
            return
        url = f"{gecko.BASE}/networks/{net}/pools/multi/{','.join(p['pool_address'] for p in todo)}?include=base_token,quote_token&include_composition=true"
        for p in todo:
            pools_done.add((chain, p["mint"], p["pool_address"]))
        if len(todo) == GT_MULTI_MAX:
            gt_tasks.insert(0, task)                        # more pools on this network than one call holds
        resp = _get(url, gt, http, gecko.PROVIDER)
        items, included = {}, {}
        if resp["status"] == 200 and resp["json"] is not None:
            for it in resp["json"].get("data") or []:
                items[((it.get("attributes") or {}).get("address")) or (it.get("id") or "").split("_", 1)[-1]] = it
            for it in resp["json"].get("included") or []:
                included[it.get("id")] = it
        for p in todo:
            it = next((v for k, v in items.items() if _same(chain, k, p["pool_address"])), None)
            if resp["status"] != 200 or resp["json"] is None:
                state, v = ("SOURCE_BLOCKED" if resp["status"] in (0, 429) else f"HTTP_{resp['status']}"), {}
            elif it is None:
                state, v = "NOT_IN_RESPONSE", {}
            else:
                state, v = pool_values(chain, net, p["mint"], it, included)
            _snapshot(con, run_id=run_id, dec=p, kind="POOL", provider=gecko.PROVIDER, url=url, resp=resp, state=state, decimals=v.get("decimals"),
                      reserve_usd=v.get("reserve_usd"), price_usd=v.get("price_usd"), values=v or None)
            summary["pool_snapshots"][state] += 1
            if chain != "solana":
                _snapshot(con, run_id=run_id, dec=p, kind="QUOTE", provider="none", url=None, resp=None, state="QUOTE_UNSUPPORTED_CHAIN")
                summary["quotes"]["QUOTE_UNSUPPORTED_CHAIN"] += 1
            elif state == "OK":
                quote_q.append((p, v))
        con.commit()
        # quotes: pools never quoted first, then the ones quoted longest ago
        def last_quote(p):
            r = con.execute("SELECT MAX(captured_at) FROM bt_depth_snapshots WHERE kind='QUOTE' AND state='OK' AND chain=? AND mint=? AND pool_address=?",
                            (p["chain"], p["mint"], p["pool_address"])).fetchone()[0]
            return -1.0 if r is None else r
        quote_q.sort(key=lambda x: last_quote(x[0]))

    def run_quote(p: dict, v: dict, size: float) -> None:
        price, dec = v.get("price_usd"), v.get("decimals")
        if not price or price <= 0 or dec is None:
            _snapshot(con, run_id=run_id, dec=p, kind="QUOTE", provider=JUP_PROVIDER, url=None, resp=None, state="NO_PRICE_OR_DECIMALS", size_usd=size)
            summary["quotes"]["NO_PRICE_OR_DECIMALS"] += 1
            return
        amount = size / price
        raw = int(math.floor(amount * 10 ** int(dec)))
        if raw <= 0:
            _snapshot(con, run_id=run_id, dec=p, kind="QUOTE", provider=JUP_PROVIDER, url=None, resp=None, state="AMOUNT_ZERO", size_usd=size)
            summary["quotes"]["AMOUNT_ZERO"] += 1
            return
        url = f"{JUP_QUOTE}?inputMint={p['mint']}&outputMint={USDC}&amount={raw}&slippageBps={SLIPPAGE_BPS}&swapMode=ExactIn"
        resp = _get(url, jup, http, JUP_PROVIDER)
        state = _quote_state(resp)
        j = resp.get("json") or {}
        vals, out_usd, impact = None, None, None
        if state == "OK":
            if j.get("inputMint") != p["mint"] or j.get("outputMint") != USDC or str(j.get("inAmount")) != str(raw):
                state = "IDENTITY_MISMATCH"
            out_usd = _num(j.get("outAmount"))
            out_usd = out_usd / 10 ** USDC_DECIMALS if out_usd is not None else None
            impact = _num(j.get("priceImpactPct"))
            vals = {"out_amount_raw": j.get("outAmount"), "other_amount_threshold": j.get("otherAmountThreshold"), "swap_usd_value": _num(j.get("swapUsdValue")),
                    "context_slot": j.get("contextSlot"), "route": [{"label": (s.get("swapInfo") or {}).get("label"), "amm": (s.get("swapInfo") or {}).get("ammKey"),
                                                                       "percent": s.get("percent")} for s in j.get("routePlan") or []],
                    "price_usd_used": price, "proceeds_ratio": (out_usd / size) if out_usd is not None else None}
        elif j:
            vals = {"error_code": j.get("errorCode"), "error": str(j.get("error") or "")[:200]}
        _snapshot(con, run_id=run_id, dec=p, kind="QUOTE", provider=JUP_PROVIDER, url=url, resp=resp, state=state, size_usd=size, token_amount=amount,
                  token_amount_raw=raw, decimals=int(dec), price_usd=price, out_usd=out_usd, price_impact=impact, values=vals)
        summary["quotes"][state] += 1
        con.commit()

    # 2. GeckoTerminal tasks in order; quotes fill the gaps between GeckoTerminal calls
    def pending(chain: str) -> bool:
        return any(p["chain"] == chain and (chain, p["mint"], p["pool_address"]) not in pools_done for p in active_pools(con, now))

    quotes: list[tuple] = []
    while True:
        while gt_tasks and gt_tasks[0][0] == "pools" and not pending(gt_tasks[0][1]):
            gt_tasks.pop(0)                                 # nothing to read on this network: no call
        if not (gt_tasks or quote_q or quotes) or not time_left():
            break
        if gt_tasks and gt.calls >= gt.max_calls:
            summary["not_attempted"]["geckoterminal_tasks"] += len([t for t in gt_tasks if t[0] == "resolve" or pending(t[1])])
            gt_tasks.clear()
            continue
        if gt_tasks and clock() - gt._last >= gt.min_spacing:
            run_gt(gt_tasks.pop(0))
            continue
        if not quotes and quote_q:
            p, v = quote_q.pop(0)
            quotes = [(p, v, s) for s in sizes]
        if quotes:
            if jup.calls >= jup.max_calls:
                summary["not_attempted"]["quotes"] += len(quotes) + len(quote_q) * len(sizes)
                quotes, quote_q = [], []
                continue
            run_quote(*quotes.pop(0))
            continue
        sleep(max(0.0, gt.min_spacing - (clock() - gt._last)))
    if gt_tasks or quote_q or quotes:
        summary["deadline_hit"] = not time_left()
        summary["not_attempted"]["geckoterminal_tasks"] += len([t for t in gt_tasks if t[0] == "resolve" or pending(t[1])])
        summary["not_attempted"]["quotes"] += len(quotes) + len(quote_q) * len(sizes)
    con.commit()
    q = summary["quotes"]
    blocked = sum(n for s, n in q.items() if s in ("SOURCE_BLOCKED", "HTTP_401", "HTTP_403", "HTTP_429"))
    summary["quote_source"] = ("NOT_USED" if not sum(n for s, n in q.items() if s != "QUOTE_UNSUPPORTED_CHAIN")
                               else "QUOTE_SOURCE_BLOCKED" if blocked and not q.get("OK") else "OK")
    summary.update(calls={"geckoterminal": gt.calls, "jupiter": jup.calls, "retries": gt.retries + jup.retries}, pools_active=len(active_pools(con, now)), wall_s=round(clock() - t0, 1))
    for k in ("pool_snapshots", "quotes", "not_attempted"):
        summary[k] = dict(summary[k])
    return summary


# ---------------------------------------------------------------- reading back

def status(con, now: float, hours: float = 48.0) -> dict:
    """Per decision: pool source, lag from the export commit to the first pool snapshot and first OK quote, and how
    many hours of the 0 to 24 h grid have a pool snapshot and an OK quote."""
    out = []
    for d in con.execute("SELECT * FROM bt_depth_decisions WHERE export_time>=? ORDER BY export_time, id", (now - hours * 3600,)):
        snaps = con.execute("SELECT kind, state, captured_at FROM bt_depth_snapshots WHERE chain=? AND mint=? AND pool_address IS ? AND captured_at>=? "
                            "AND captured_at<=? ORDER BY captured_at", (d["chain"], d["mint"], d["pool_address"], d["export_time"], d["export_time"] + ACTIVE_S)).fetchall()
        pool_ok = [s["captured_at"] for s in snaps if s["kind"] == "POOL" and s["state"] == "OK"]
        quote_ok = [s["captured_at"] for s in snaps if s["kind"] == "QUOTE" and s["state"] == "OK"]
        grid = lambda ts: len({int((t - d["export_time"]) // 3600) for t in ts if t - d["export_time"] < ACTIVE_S})
        out.append({"chain": d["chain"], "mint": d["mint"], "pool": d["pool_address"], "pool_source": d["pool_source"], "status": d["status"],
                    "export_time": d["export_time"], "first_pool_lag_s": round(pool_ok[0] - d["export_time"], 1) if pool_ok else None,
                    "first_quote_lag_s": round(quote_ok[0] - d["export_time"], 1) if quote_ok else None,
                    "pool_hours_of_25": grid(pool_ok), "quote_hours_of_25": grid(quote_ok),
                    "states": dict(Counter(f"{s['kind']}:{s['state']}" for s in snaps))})
    return {"decisions": len(out), "rows": out,
            "snapshots": dict(Counter(f"{r[0]}:{r[1]}" for r in con.execute("SELECT kind, state FROM bt_depth_snapshots")))}
