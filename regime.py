"""Layer 0: CRYPTO_REGIME_ENGINE.

Inputs (all from the ecosystem plan): CoinGecko daily charts for BTC/ETH/SOL/BNB, /global, DefiLlama stablecoin supply by chain,
Hyperliquid funding/OI, CoinGecko meme-token markets (breadth). Previous regime_snapshots supply the 7-day stablecoin change.
Output: RISK-ON / NEUTRAL / RISK-OFF / HIGH-VOLATILITY SPECULATION / CAPITAL FLIGHT with FACT / INFERENCE / CONFIDENCE lines.
"""
from __future__ import annotations

import json
import math
import statistics
import time
from typing import Any

from .. import db
from ._util import Component, clear_at, confidence_from_coverage, median, pct_change

COINS = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "binancecoin": "BNB"}


def _series(bodies: dict, cid: str) -> list[list[float]]:
    v = bodies.get(f"cg_chart:{cid}")
    return (v or {}).get("prices") or [] if isinstance(v, dict) else []


def trend_stats(prices: list[list[float]]) -> dict[str, Any]:
    px = [p[1] for p in prices if p and p[1]]
    if len(px) < 25:
        return {"trend": "UNKNOWN", "n": len(px)}
    last = px[-1]
    ma20 = sum(px[-20:]) / 20
    ma50 = sum(px[-50:]) / 50 if len(px) >= 50 else None
    hi90 = max(px[-90:])
    rets = [math.log(px[i] / px[i - 1]) for i in range(max(1, len(px) - 30), len(px)) if px[i - 1] > 0]
    vol30 = statistics.pstdev(rets) * math.sqrt(365) * 100 if len(rets) > 5 else None
    chg7 = pct_change(last, px[-8]) if len(px) >= 8 else None
    chg30 = pct_change(last, px[-31]) if len(px) >= 31 else None
    if ma50 is not None:
        trend = "UP" if last > ma20 > ma50 else "DOWN" if last < ma20 < ma50 else "MIXED"
    else:
        trend = "UP" if last > ma20 else "DOWN"
    return {"trend": trend, "last": last, "ma20": ma20, "ma50": ma50, "dd_90d": (last / hi90 - 1) * 100, "vol_30d": vol30, "chg_7d": chg7, "chg_30d": chg30, "n": len(px)}


def compute(bodies: dict[str, Any], t: float | None = None, persist: bool = True) -> dict[str, Any]:
    t = t or time.time()
    facts, inferences, unknowns = [], [], []
    coins = {}
    for cid, sym in COINS.items():
        s = trend_stats(_series(bodies, cid))
        coins[sym] = s
        if s["trend"] == "UNKNOWN":
            unknowns.append(f"{sym} chart")
        else:
            facts.append(f"{sym} {s['trend']} (price {s['last']:,.2f}; 20d MA {s['ma20']:,.2f}" + (f", 50d MA {s['ma50']:,.2f}" if s.get("ma50") else "") + f"; 7d {s['chg_7d']:+.1f}%; 90d drawdown {s['dd_90d']:+.1f}%" + (f"; 30d realized vol {s['vol_30d']:.0f}% ann." if s.get("vol_30d") else "") + ")")
    g = bodies.get("cg_global") if isinstance(bodies.get("cg_global"), dict) else {}
    if g:
        facts.append(f"total crypto market cap ${g.get('total_mcap', 0) / 1e9:,.0f}B ({(g.get('mcap_chg_24h') or 0):+.1f}% 24h), BTC dominance {g.get('btc_dom')}%")
    else:
        unknowns.append("global market cap")
    st = bodies.get("llama_stables") if isinstance(bodies.get("llama_stables"), list) else []
    stable_total = sum(x[1] or 0 for x in st) if st else None
    stable_prev = None
    if persist:
        with db.connect() as con:
            row = con.execute("SELECT stable_mcap, observed_at FROM regime_snapshots WHERE observed_at <= ? AND stable_mcap IS NOT NULL ORDER BY observed_at DESC LIMIT 1", (t - 6 * 86400,)).fetchone()
            stable_prev = row["stable_mcap"] if row else None
    stable_chg = pct_change(stable_total, stable_prev)
    if stable_total:
        facts.append(f"stablecoin supply ${stable_total / 1e9:,.1f}B" + (f" ({stable_chg:+.2f}% vs ~7d ago)" if stable_chg is not None else " (7d change UNKNOWN: no snapshot older than 6 days yet)"))
    else:
        unknowns.append("stablecoin supply")
    hl = bodies.get("hl_meta") if isinstance(bodies.get("hl_meta"), dict) else {}
    fund = [hl[c]["funding"] for c in ("BTC", "ETH", "SOL") if c in hl and hl[c].get("funding") is not None]
    funding_ann = (sum(fund) / len(fund)) * 24 * 365 * 100 if fund else None  # hourly rate -> annualized %
    oi = sum((hl[c].get("oi") or 0) * (hl[c].get("mark") or 0) for c in hl) if hl else None
    if funding_ann is not None:
        facts.append(f"Hyperliquid funding BTC/ETH/SOL avg {funding_ann:+.1f}% annualized; perp OI (tracked coins) ${(oi or 0) / 1e9:,.2f}B")
    else:
        unknowns.append("funding / open interest")
    memes = bodies.get("cg_mkts:meme-token:1") if isinstance(bodies.get("cg_mkts:meme-token:1"), list) else []
    br7 = [m.get("p7d") for m in memes if m.get("p7d") is not None]
    br24 = [m.get("price_change_percentage_24h") for m in memes if m.get("price_change_percentage_24h") is not None]
    breadth7 = (sum(1 for x in br7 if x > 0) / len(br7) * 100) if br7 else None
    breadth24 = (sum(1 for x in br24 if x > 0) / len(br24) * 100) if br24 else None
    if breadth7 is not None:
        facts.append(f"meme breadth: {breadth7:.0f}% of the top {len(br7)} memes up on 7d, {breadth24:.0f}% up on 24h; median 7d {median(br7):+.1f}%")
    else:
        unknowns.append("meme breadth")

    # ---- decision ----
    ups = sum(1 for s in coins.values() if s["trend"] == "UP"); downs = sum(1 for s in coins.values() if s["trend"] == "DOWN")
    btc = coins["BTC"]; known = [s for s in coins.values() if s["trend"] != "UNKNOWN"]
    cov = Component("coverage", 1)
    cov.add(2, 1.0 if len(known) >= 3 else None, "major-coin charts"); cov.add(1, 1.0 if g else None, "global"); cov.add(1, 1.0 if stable_total else None, "stablecoins")
    cov.add(1, 1.0 if funding_ann is not None else None, "funding"); cov.add(1, 1.0 if breadth7 is not None else None, "breadth")
    regime = "UNKNOWN"
    if len(known) >= 2:
        hi_vol = (btc.get("vol_30d") or 0) > 60 or (funding_ann is not None and abs(funding_ann) > 40)
        if btc["trend"] == "DOWN" and (btc.get("dd_90d") or 0) < -20 and (stable_chg is not None and stable_chg < -1.0) and (breadth7 is None or breadth7 < 30):
            regime = "CAPITAL FLIGHT"
        elif downs >= max(2, len(known) - 1) or (breadth7 is not None and breadth7 < 30 and (btc.get("chg_7d") or 0) < -5):
            regime = "RISK-OFF"
        elif hi_vol and (breadth7 is None or breadth7 >= 40):
            regime = "HIGH-VOLATILITY SPECULATION"
        elif ups >= max(2, len(known) - 1) and (breadth7 is None or breadth7 >= 50):
            regime = "RISK-ON"
        else:
            regime = "NEUTRAL"
    conf = confidence_from_coverage(cov.coverage) if regime != "UNKNOWN" else "NONE"
    inferences.append({
        "RISK-ON": "majors trending up with broad meme participation: speculative capital is being deployed, size can run at the normal ceiling",
        "NEUTRAL": "mixed trends: selection matters more than exposure; keep sizes at or below normal and demand clean setups",
        "RISK-OFF": "majors trending down or memes broadly falling: new positions need stronger evidence; expect liquidity to thin on exits",
        "HIGH-VOLATILITY SPECULATION": "high realized volatility or extreme funding: fast rotations, stops get hit by noise; smaller size, wider invalidation, shorter holding",
        "CAPITAL FLIGHT": "stablecoins leaving while BTC breaks down: this is when exits fail; research only, no new entries",
        "UNKNOWN": "not enough market data to classify the regime; treat as RISK-OFF for sizing",
    }[regime])
    statement = f"FACT: {'; '.join(facts[:6])}. INFERENCE: {inferences[0]}. CONFIDENCE: {conf} ({len(unknowns)} input(s) unknown{': ' + ', '.join(unknowns) if unknowns else ''})."
    out = {"regime": regime, "confidence": conf, "statement": statement, "coins": coins, "global": g, "stable_mcap": stable_total, "stable_chg_7d_pct": stable_chg, "funding_ann_pct": funding_ann,
           "oi_usd": oi, "breadth_7d_pct": breadth7, "breadth_24h_pct": breadth24, "facts": facts, "inferences": inferences, "unknowns": unknowns, "observed_at": t,
           "size_multiplier": {"RISK-ON": 1.0, "NEUTRAL": 0.75, "HIGH-VOLATILITY SPECULATION": 0.5, "RISK-OFF": 0.5, "CAPITAL FLIGHT": 0.0, "UNKNOWN": 0.5}[regime]}
    if persist:
        with db.connect() as con:
            clear_at(con, t, {"regime_snapshots": "observed_at"})
            db.insert(con, "regime_snapshots", {"observed_at": t, "regime": regime, "confidence": conf, "statement": statement,
                      "btc_trend": coins["BTC"]["trend"], "eth_trend": coins["ETH"]["trend"], "sol_trend": coins["SOL"]["trend"], "bnb_trend": coins["BNB"]["trend"],
                      "btc_vol_30d": btc.get("vol_30d"), "btc_dd_90d": btc.get("dd_90d"), "breadth_pct": breadth7, "funding_avg": funding_ann, "oi_usd": oi,
                      "stable_mcap": stable_total, "stable_chg_7d_pct": stable_chg, "total_mcap": g.get("total_mcap"), "total_mcap_chg_24h": g.get("mcap_chg_24h"), "btc_dominance": g.get("btc_dom"),
                      "components_json": json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "n"} for k, v in coins.items()}), "unknown_json": json.dumps(unknowns)})
    return out
