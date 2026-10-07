"""03_MARKET_DATA: consolidate price / volume / activity across providers, record discrepancies."""
from __future__ import annotations

from typing import Any


def analyze(bundle: dict[str, Any]) -> dict[str, Any]:
    mk = bundle.get("market") or {}
    facts, unknowns, inferences = [], [], []
    p = mk.get("price_usd")
    if p is None:
        unknowns.append("price unavailable")
    else:
        facts.append(f"price ${p:.8g} ({bundle['sources'].get('price_usd')})")
    liq = mk.get("liquidity_usd_total")
    if liq is not None:
        facts.append(f"total displayed liquidity ${liq:,.0f} ({bundle['sources'].get('liquidity_usd_total')})")
        if mk.get("ds_liquidity_total") is not None:
            facts.append(f"dexscreener pair liquidity sum ${mk['ds_liquidity_total']:,.0f}")
    v24 = (mk.get("vol") or {}).get("24h")
    v6 = (mk.get("vol") or {}).get("6h"); v1 = (mk.get("vol") or {}).get("1h")
    if v24:
        facts.append(f"24h volume ${v24:,.0f}" + (f"; 6h ${v6:,.0f}; 1h ${v1:,.0f}" if v6 is not None and v1 is not None else ""))
        if liq:
            facts.append(f"24h volume / liquidity = {v24/liq:.1f}x")
    pace6 = (v6 * 4 / v24) if v6 is not None and v24 else None
    pace1 = (v1 * 24 / v24) if v1 is not None and v24 else None
    if pace6 is not None:
        inferences.append(f"activity pace: last 6h running at {pace6:.2f}x and last 1h at {pace1:.2f}x the 24h average" if pace1 is not None else f"6h pace {pace6:.2f}x")
    mc, fdv = mk.get("market_cap"), mk.get("fdv")
    if mc is not None:
        facts.append(f"market cap ${mc:,.0f}; FDV ${fdv:,.0f}" if fdv is not None else f"market cap ${mc:,.0f}")
    if mk.get("holder_count") is not None:
        facts.append(f"holders {mk['holder_count']:,} (jupiter)")
    for d in bundle.get("discrepancies") or []:
        facts.append("DISCREPANCY " + d)
    liq_mc = (liq / mc) if liq and mc else None
    if liq_mc is not None:
        facts.append(f"liquidity / market cap = {liq_mc:.1%} (screening metric only, not an exit quote)")
    return {"price_usd": p, "liquidity_usd": liq, "vol_24h": v24, "vol_6h": v6, "vol_1h": v1, "pace_6h": pace6, "pace_1h": pace1,
            "market_cap": mc, "fdv": fdv, "liq_to_mcap": liq_mc, "age_hours": mk.get("age_hours"),
            "chg": mk.get("chg"), "facts": facts, "inferences": inferences,
            "heuristics": ["market cap is not money invested; FDV is not a future market cap"], "unknowns": unknowns}
