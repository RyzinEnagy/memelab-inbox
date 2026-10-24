"""GeckoTerminal public API adapter: pools and historical OHLCV, read-only, bounded, with provenance.

What it can and cannot give:
- Bars exist only for intervals with trades; an absent hour is "no trade or no data", never zero volume by default.
- Pool lists are today's lists. A pool enters history at its on-chain creation time (modeled availability,
  flagged POOL_LIST_PRESENT_DAY); the candidate set itself comes from today's list (disclosed, not hidden).
- No historical reserves, ticks or bins: those stay BLOCKED. Today's reserve_in_usd is stored as a present-day
  observation only and is never used for past fills.
"""
from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from typing import Callable

from .. import store
from ..timeguard import utc_ts

BASE = "https://api.geckoterminal.com/api/v2"
PROVIDER = "geckoterminal"
PROVIDER_LAG_S = 300.0          # heuristic publication lag for a closed bar (same value the social replay uses)
UA = "memelab-backtest/0.1 (research-only; read-only)"

# dex id -> pool type. Unknown ids stay UNKNOWN (never assumed constant product).
DEX_POOL_TYPE = {
    "pumpswap": "CPMM", "pump-fun-amm": "CPMM", "raydium": "CPMM", "raydium-cpmm": "CPMM", "meteora-damm": "CPMM",
    "meteora-damm-v2": "CLMM", "raydium-clmm": "CLMM", "orca": "CLMM", "meteora": "DLMM", "meteora-dlmm": "DLMM",
    "pump-fun": "BONDING_CURVE", "raydium-launchlab": "BONDING_CURVE", "meteora-dbc": "BONDING_CURVE",
}


class Budget:
    def __init__(self, max_calls: int, min_spacing_s: float = 3.0, max_retries: int = 4, sleep=time.sleep, clock=time.time):
        self.max_calls, self.min_spacing, self.max_retries = max_calls, min_spacing_s, max_retries
        self.calls, self.errors, self.retries, self._last = 0, 0, 0, 0.0
        self.sleep, self.clock = sleep, clock

    def wait(self):
        dt = self.clock() - self._last
        if dt < self.min_spacing:
            self.sleep(self.min_spacing - dt)
        self._last = self.clock()


class BudgetExhausted(RuntimeError):
    pass


def default_http_get(url: str, timeout: float = 30.0) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, b""


def get_json(url: str, budget: Budget, http_get: Callable[[str], tuple[int, bytes]] = default_http_get) -> tuple[int, dict | None, str | None]:
    """Bounded GET with exponential backoff on 429/5xx/network errors. Returns (status, json, raw_ref)."""
    for attempt in range(budget.max_retries + 1):
        if budget.calls >= budget.max_calls:
            raise BudgetExhausted(f"GeckoTerminal budget of {budget.max_calls} calls used")
        budget.wait()
        budget.calls += 1
        status, body = http_get(url)
        if status == 200:
            try:
                d = json.loads(body)
            except json.JSONDecodeError:
                budget.errors += 1
                return status, None, None
            return status, d, store.save_raw(PROVIDER, body)
        if status in (429, 500, 502, 503, 504, 0) and attempt < budget.max_retries:
            budget.retries += 1
            budget.sleep(min(60.0, 5.0 * (2 ** attempt)) + random.random())
            continue
        budget.errors += 1
        return status, None, None
    return 0, None, None


def fetch_pools(con, mint: str, budget: Budget, http_get=default_http_get, observed_at: float | None = None, chain: str = "solana") -> dict:
    url = f"{BASE}/networks/{chain}/tokens/{mint}/pools?page=1"
    status, d, raw = get_json(url, budget, http_get)
    observed_at = observed_at or time.time()
    if d is None:
        return {"mint": mint, "status": "SOURCE_BLOCKED" if status in (0, 429) else f"HTTP_{status}", "pools": []}
    out = []
    for p in d.get("data") or []:
        a = p.get("attributes") or {}
        rel = p.get("relationships") or {}
        dex = ((rel.get("dex") or {}).get("data") or {}).get("id")
        base_id = ((rel.get("base_token") or {}).get("data") or {}).get("id") or ""
        quote_id = ((rel.get("quote_token") or {}).get("data") or {}).get("id") or ""
        if not base_id.endswith(mint):
            continue  # pool where our mint is the quote side: price orientation differs; skipped and counted
        created = utc_ts(a["pool_created_at"]) if a.get("pool_created_at") else None
        ptype = DEX_POOL_TYPE.get(dex or "", "UNKNOWN")
        store.record_pool_version(con, chain=chain, pool_address=a["address"], mint=mint, pool_type=ptype, dex=dex,
                                  quote_mint=quote_id.split("_", 1)[-1] or None, pool_created_at=created, observed_at=observed_at,
                                  available_at=(created + PROVIDER_LAG_S) if created else observed_at, source=PROVIDER, raw_ref=raw)
        reserve = float(a["reserve_in_usd"]) if a.get("reserve_in_usd") not in (None, "") else None
        store.record_observation(con, kind="POOL_RESERVE_USD_PRESENT", provider=PROVIDER, payload={"pool": a["address"], "reserve_usd": reserve, "t": observed_at},
                                 chain=chain, mint=mint, pool_address=a["address"], event_time=observed_at, observed_at=observed_at,
                                 available_at=observed_at, value_num=reserve, raw_ref=raw)
        out.append({"pool": a["address"], "dex": dex, "pool_type": ptype, "created": created, "reserve_usd_now": reserve})
    return {"mint": mint, "status": "OK" if out else "NO_POOLS", "pools": out, "raw_ref": raw}


def fetch_ohlcv(con, mint: str, pool: str, budget: Budget, http_get=default_http_get, tf: str = "hour", aggregate: int = 1,
                before: float | None = None, limit: int = 1000, observed_at: float | None = None, chain: str = "solana") -> dict:
    tf_s = {"minute": 60, "hour": 3600, "day": 86400}[tf] * aggregate
    url = f"{BASE}/networks/{chain}/pools/{pool}/ohlcv/{tf}?aggregate={aggregate}&limit={limit}&currency=usd&token={mint}"
    if before:
        url += f"&before_timestamp={int(before)}"
    status, d, raw = get_json(url, budget, http_get)
    observed_at = observed_at or time.time()
    if d is None:
        return {"pool": pool, "status": "SOURCE_BLOCKED" if status in (0, 429) else f"HTTP_{status}", "bars": 0}
    rows = ((d.get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
    # fetch evidence: the pool's bars are known up to this time even when nothing new traded (outcomes need it, Phase 17 M2)
    store.record_observation(con, kind="OHLCV_FETCHED", provider=PROVIDER, payload={"pool": pool, "rows": len(rows), "t": observed_at,
                             "last": max((float(r[0]) for r in rows if r), default=None)}, chain=chain, mint=mint, pool_address=pool,
                             event_time=observed_at, observed_at=observed_at, available_at=observed_at, value_num=float(len(rows)), raw_ref=raw)
    n, skipped_partial, bad = 0, 0, 0
    starts = [r[0] for r in rows if r]
    dup = {x for x in starts if starts.count(x) > 1}
    for r in rows:
        try:
            start, o, h, l, c, v = (float(x) for x in r[:6])
        except (TypeError, ValueError):
            bad += 1
            continue
        if min(o, h, l, c) <= 0 or h < max(o, c) or l > min(o, c):
            bad += 1
            continue
        if start + tf_s > observed_at:
            skipped_partial += 1   # the forming bar is never stored
            continue
        _, ins = store.record_bar(con, chain=chain, mint=mint, pool_address=pool, tf=tf_s, start=start, o=o, h=h, l=l, c=c, volume_usd=v,
                                  observed_at=observed_at, provider=PROVIDER, provider_lag_s=PROVIDER_LAG_S, raw_ref=raw,
                                  quality_flags="DUP_TS_IN_RESPONSE" if r[0] in dup else None)
        n += ins
    return {"pool": pool, "status": "OK" if rows else "EMPTY", "bars": n, "rows": len(rows), "partial_skipped": skipped_partial, "invalid": bad,
            "duplicate_starts": len(dup), "first": min((float(r[0]) for r in rows), default=None), "last": max((float(r[0]) for r in rows), default=None), "raw_ref": raw}


def candidate_pools(pools: list[dict], lab_pool: str | None = None, k: int = 2) -> list[dict]:
    """Present-day list -> candidate set: top-k by current reserve, the oldest pool, and the lab's own recorded pool.
    The set is disclosed as POOL_LIST_PRESENT_DAY; the choice among them at a decision time uses only bars
    available then (see pool_basis_at)."""
    by_res = sorted([p for p in pools if p.get("reserve_usd_now") is not None], key=lambda p: -p["reserve_usd_now"])[:k]
    oldest = sorted([p for p in pools if p.get("created")], key=lambda p: p["created"])[:1]
    lab = [p for p in pools if lab_pool and p["pool"] == lab_pool]
    seen, out = set(), []
    for p in by_res + oldest + lab:
        if p["pool"] not in seen:
            seen.add(p["pool"]); out.append(p)
    return out


def pool_basis_at(con, chain: str, mint: str, decision_time: float, tf: int = 3600, lookback_s: float = 86400.0) -> dict | None:
    """Point-in-time pool choice: among pools valid at decision_time, the one with the most volume in bars closed and
    available within the lookback window. Returns None when no pool has bars then (INSUFFICIENT_HISTORY)."""
    best = None
    for p in store.pools_valid_at(con, chain=chain, mint=mint, cutoff=decision_time):
        bars = store.bars_asof(con, chain=chain, mint=mint, pool_address=p["pool_address"], tf=tf, cutoff=decision_time)
        vol = sum((b["volume_usd"] or 0.0) for b in bars if b["end"] > decision_time - lookback_s)
        if bars and (best is None or vol > best["trailing_volume_usd"]):
            best = {"pool_address": p["pool_address"], "pool_type": p["pool_type"], "dex": p["dex"], "trailing_volume_usd": vol, "n_bars": len(bars)}
    return best
