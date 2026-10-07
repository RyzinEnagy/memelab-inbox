"""05_POOL_DISCOVERY: every economically meaningful venue, liquidity concentration, pool age."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

QUOTE_NAMES = {"So11111111111111111111111111111111111111112": "SOL", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC", "Es9vMGANM1E2EjMA4c6kQX8m3KdMMw2sCkChfR4ZF9": "USDT"}


def analyze(bundle: dict[str, Any], min_reserve_usd: float = 1_000) -> dict[str, Any]:
    pools = [p for p in bundle.get("pools") or [] if p.get("pool")]
    facts, inferences, unknowns = [], [], []
    rows = []
    now = bundle.get("observed_at")
    for p in pools:
        res = p.get("reserve_usd") or p.get("gt_reserve_usd")
        created = p.get("created")
        age_h = None
        if created:
            try:
                age_h = (now - datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()) / 3600
            except ValueError:
                pass
        rows.append({"pool": p["pool"], "dex": p.get("dex") or p.get("market_type"), "quote": QUOTE_NAMES.get(p.get("quote"), p.get("quote_symbol") or (p.get("quote") or "")[:6]),
                     "reserve_usd": res, "base_reserve": p.get("base_reserve"), "quote_reserve": p.get("quote_reserve"), "vol_24h": p.get("vol_24h"),
                     "txns_h24": p.get("txns_h24") or p.get("txns_h24_gt"), "age_hours": age_h, "labels": p.get("labels"), "market_type": p.get("market_type"),
                     "lp_locked_pct": (p.get("lp") or {}).get("locked_pct") if p.get("lp") else None, "concentrated": bool(p.get("labels") and any(l in ("CLMM", "DLMM", "DYN2", "DAMM2") for l in p["labels"])) or (p.get("dex") or "") in ("meteora", "raydium-clmm", "orca")})
    rows.sort(key=lambda r: r["reserve_usd"] or 0, reverse=True)
    meaningful = [r for r in rows if (r["reserve_usd"] or 0) >= min_reserve_usd]
    total = sum(r["reserve_usd"] or 0 for r in rows)
    top_share = (meaningful[0]["reserve_usd"] / total) if meaningful and total else None
    facts.append(f"{len(rows)} pools known, {len(meaningful)} with >= ${min_reserve_usd:,.0f} displayed liquidity; total displayed ${total:,.0f}")
    for r in meaningful[:6]:
        facts.append(f"{r['dex']} {r['quote']} pool {r['pool'][:8]}..: ${r['reserve_usd'] or 0:,.0f} liquidity, 24h vol ${r['vol_24h'] or 0:,.0f}" + (f", age {r['age_hours']/24:.1f}d" if r['age_hours'] is not None else "") + (f", LP locked {r['lp_locked_pct']:.0f}%" if r['lp_locked_pct'] is not None else ""))
    if top_share is not None:
        facts.append(f"largest pool holds {top_share:.0%} of displayed liquidity")
        if top_share > 0.8:
            inferences.append("liquidity concentrated in a single venue; one LP decision can remove most depth")
    if any(r["concentrated"] for r in meaningful):
        inferences.append("concentrated-liquidity pools present (DLMM/CLMM/DAMM v2): displayed reserve overstates depth far from current price; rely on router quotes")
    quotes = {r["quote"] for r in meaningful}
    if quotes and quotes - {"SOL"}:
        facts.append("quote assets: " + ", ".join(sorted(quotes)))
    if not rows:
        unknowns.append("no pool data")
    return {"pools": rows, "meaningful": meaningful, "total_displayed_liquidity": total, "top_pool_share": top_share,
            "n_meaningful": len(meaningful), "facts": facts, "inferences": inferences,
            "heuristics": ["displayed liquidity is never an exit quote"], "unknowns": unknowns}
