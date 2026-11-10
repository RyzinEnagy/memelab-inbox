"""Historical corpus builder: universe mints -> pools -> hourly OHLCV, bounded, resumable, with a coverage report.

Resumable: a mint whose pools were already fetched today (POOL_RESERVE_USD_PRESENT observation exists) is skipped
unless refresh=True. Every call goes through gecko.get_json (budget, backoff, raw shards).
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

from .. import store
from . import gecko

SOL_MINT = "So11111111111111111111111111111111111111112"
SOL_USDC_POOL = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"  # Raydium SOL/USDC; for SOL/USD denominators


def select_mints(con, universe_id: str, n_rejected_sample: int, seed: int = 20261023) -> list[str]:
    th = [r[0] for r in con.execute("SELECT DISTINCT mint FROM bt_universe_members WHERE universe_id=? AND chain='solana' AND basis='THESIS' ORDER BY mint", (universe_id,))]
    rj = [r[0] for r in con.execute("SELECT DISTINCT mint FROM bt_universe_members WHERE universe_id=? AND chain='solana' AND basis='REJECTION' ORDER BY mint", (universe_id,))]
    rj_only = [m for m in rj if m not in set(th)]
    rng = random.Random(seed)
    sample = rng.sample(rj_only, min(n_rejected_sample, len(rj_only)))
    return th + sorted(sample)


def already_fetched(con, mint: str) -> bool:
    """Done only when the mint's bar fetches completed (marker), or pools and bars are both stored (corpora built before
    the marker existed). A run stopped between the pool list and the bars is NOT done, so a resume fetches the bars."""
    if con.execute("SELECT 1 FROM bt_observations WHERE mint=? AND kind='CORPUS_MINT_DONE' LIMIT 1", (mint,)).fetchone():
        return True
    pools = con.execute("SELECT 1 FROM bt_observations WHERE mint=? AND kind='POOL_RESERVE_USD_PRESENT' LIMIT 1", (mint,)).fetchone()
    bars = con.execute("SELECT 1 FROM bt_market_bars WHERE mint=? LIMIT 1", (mint,)).fetchone()
    return bool(pools and bars)


def mark_done(con, mint: str, statuses: list[str], observed_at: float, chain: str = "solana") -> None:
    store.record_observation(con, kind="CORPUS_MINT_DONE", provider=gecko.PROVIDER, payload={"mint": mint, "statuses": statuses, "t": observed_at},
                             chain=chain, mint=mint, observed_at=observed_at, available_at=observed_at, value_text=",".join(statuses) or "NO_POOLS")


def build(con, mints: list[str], budget: gecko.Budget, lab_pools: dict | None = None, log_path: Path | None = None, refresh: bool = False,
          http_get=gecko.default_http_get, k_pools: int = 2) -> dict:
    lab_pools = lab_pools or {}
    log = open(log_path, "a") if log_path else None
    stats = {"mints": 0, "skipped_resume": 0, "no_pools": 0, "blocked": 0, "pools_fetched": 0, "bars_new": 0, "started": time.time()}
    try:
        for m in mints:
            if not refresh and already_fetched(con, m):
                stats["skipped_resume"] += 1
                continue
            res = gecko.fetch_pools(con, m, budget, http_get)
            con.commit()
            row = {"mint": m, "pools_status": res["status"], "n_pools": len(res["pools"]), "ohlcv": []}
            if res["status"] == "SOURCE_BLOCKED":
                stats["blocked"] += 1
            elif not res["pools"]:
                stats["no_pools"] += 1
            statuses = []
            for p in gecko.candidate_pools(res["pools"], lab_pools.get(m), k=k_pools):
                o = gecko.fetch_ohlcv(con, m, p["pool"], budget, http_get)
                con.commit()
                stats["pools_fetched"] += 1
                stats["bars_new"] += o.get("bars", 0)
                statuses.append(o["status"])
                row["ohlcv"].append({k: o.get(k) for k in ("pool", "status", "bars", "rows", "first", "last")} | {"dex": p["dex"], "pool_type": p["pool_type"]})
            if res["status"] in ("OK", "NO_POOLS") and "SOURCE_BLOCKED" not in statuses:
                mark_done(con, m, statuses, time.time())
                con.commit()
            stats["mints"] += 1
            if log:
                log.write(json.dumps(row) + "\n"); log.flush()
    except gecko.BudgetExhausted as e:
        stats["stopped"] = str(e)
    finally:
        if log:
            log.close()
    stats.update(calls=budget.calls, retries=budget.retries, errors=budget.errors, secs=round(time.time() - stats["started"], 1))
    return stats


def coverage(con, mints: list[str], tf: int = 3600) -> dict:
    """Per-mint coverage of stored bars (all pools), with missingness and gap statistics. Gaps are reported, never filled."""
    out = []
    for m in mints:
        pools = con.execute("SELECT DISTINCT pool_address, pool_type, dex FROM bt_pool_versions WHERE mint=?", (m,)).fetchall()
        bars = con.execute("SELECT pool_address, start, volume_usd, quality_flags FROM bt_market_bars WHERE mint=? AND timeframe_s=? ORDER BY pool_address, start", (m, tf)).fetchall()
        per_pool = {}
        for b in bars:
            per_pool.setdefault(b["pool_address"], []).append(b["start"])
        best = max(per_pool.items(), key=lambda kv: len(kv[1]), default=(None, []))
        starts = best[1]
        gaps = [int((b - a) / tf) - 1 for a, b in zip(starts, starts[1:]) if b - a > tf]
        span = int((starts[-1] - starts[0]) / tf) + 1 if starts else 0
        out.append({"mint": m, "pools_known": len(pools), "pools_with_bars": len(per_pool), "best_pool": best[0], "bars_best_pool": len(starts),
                    "first": starts[0] if starts else None, "last": starts[-1] if starts else None, "span_bars": span,
                    "missing_bars_in_span": (span - len(starts)) if starts else None, "max_gap_bars": max(gaps) if gaps else 0,
                    "pool_types": sorted({p["pool_type"] for p in pools})})
    return {"tokens": len(out), "with_bars": sum(1 for r in out if r["bars_best_pool"]), "rows": out}
