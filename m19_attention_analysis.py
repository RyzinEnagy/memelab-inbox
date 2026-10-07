"""19_ATTENTION_ANALYSIS: attention as a market input, measured with the proxies available without a social API.

Proxies: holder growth (5m/1h/6h/24h), unique traders, net buyers, organic buyer count, DEX Screener paid boosts/profile
presence, GeckoTerminal social links and gt_score info component, Jupiter organic score, trader growth vs volume growth.
Optional `social_obs`: list of manual observations {metric, value, source, note} captured by the operator in the browser
(e.g. X search result counts, Telegram member count), stored in social_snapshots.
"""
from __future__ import annotations

from typing import Any


def analyze(bundle: dict[str, Any], social_obs: list[dict] | None = None) -> dict[str, Any]:
    mk = bundle.get("market") or {}
    so = bundle.get("social") or {}
    facts, inferences, unknowns, heur = [], [], [], []
    hc = mk.get("holder_change") or {}
    chg = mk.get("chg") or {}
    vol = mk.get("vol") or {}
    # holder growth series as attention proxy
    series = [(w, hc.get(w)) for w in ("5m", "1h", "6h", "24h") if hc.get(w) is not None]
    if series:
        facts.append("holder change: " + ", ".join(f"{w} {v:+.2f}%" for w, v in series))
    # acceleration: 1h holder growth annualized to 24h vs actual 24h
    trend = None
    h1, h6, h24 = hc.get("1h"), hc.get("6h"), hc.get("24h")
    if h6 is not None and h24 is not None:
        pace = (h6 * 4) - h24
        if h24 > 2 and pace > 1:
            trend = "ACCELERATION"
        elif h24 > 0.5 and abs(pace) <= 1:
            trend = "STABILITY"
        elif h24 <= 0 or (h6 is not None and h6 < 0 and h24 > 0):
            trend = "EXHAUSTION" if (h6 or 0) < 0 else "STABILITY"
        else:
            trend = "STABILITY" if h24 > 0 else "EXHAUSTION"
    if trend:
        inferences.append(f"attention trend by holder growth: {trend}")
    else:
        unknowns.append("holder change series unavailable")
    # participation breadth
    tr24 = mk.get("num_traders_24h"); ob24 = mk.get("num_organic_buyers_24h")
    if tr24:
        facts.append(f"unique traders 24h {tr24:,}" + (f", organic buyers {ob24}" if ob24 is not None else ""))
    # price vs attention divergence
    if h24 is not None and chg.get("24h") is not None:
        if chg["24h"] > 30 and h24 < 1:
            inferences.append("price up strongly while holder count barely grows: move driven by existing holders/bots, not new participants")
        if chg["24h"] < -20 and h24 > 3:
            inferences.append("holders still growing while price falls: new participants buying the dip (dip buyers can become supply)")
    # presence / channels
    channels = [k for k in ("website", "twitter", "telegram", "discord_url") if so.get(k)]
    facts.append("channels: " + ", ".join(channels) if channels else "no website/social links reported by providers")
    if so.get("gt_score") is not None:
        facts.append(f"geckoterminal gt_score {so['gt_score']:.0f} (info component {((so.get('gt_score_details') or {}).get('info'))})")
    if mk.get("organic_score") is not None:
        facts.append(f"jupiter organic score {mk['organic_score']:.0f} ({mk.get('organic_score_label')})")
    boost = None
    for c in (bundle.get("discovery_signals") or {}).get("feeds") or []:
        if c.startswith("ds:boost"):
            boost = True
    if boost:
        facts.append("token has an active paid DEX Screener boost")
    if social_obs:
        for o in social_obs:
            facts.append(f"{o.get('metric')}: {o.get('value')} ({o.get('source')})" + (f" - {o['note']}" if o.get("note") else ""))
    else:
        unknowns.append("mention velocity, unique posting accounts, engagement and search activity not measured (no social API); use browser observations via `memelab social-note`")
    # narrative strength proxy
    ns_parts = []
    if mk.get("organic_score") is not None: ns_parts.append(min(mk["organic_score"] / 100, 1))
    if h24 is not None: ns_parts.append(min(max(h24 / 10, 0), 1))
    if tr24: ns_parts.append(min(tr24 / 3000, 1))
    ns = sum(ns_parts) / len(ns_parts) if ns_parts else None
    organic = None
    if mk.get("organic_score") is not None:
        organic = mk["organic_score"] >= 40 and not boost
    heur.append("attention is an input, not value: compare it with price, volume, holder and liquidity growth to spot acceleration, stability or exhaustion")
    return {"trend": trend, "narrative_strength": ns, "organic": organic, "holder_change": hc, "channels": channels, "paid_boost": bool(boost),
            "facts": facts, "inferences": inferences, "heuristics": heur, "unknowns": unknowns}
