"""20_MANIPULATION_DETECTION: organic vs manufactured momentum, with observed facts / interpretation / alternatives / confidence.

Signals available: turnover vs liquidity, two-sided wallets in trade window, organic share (jupiter), tx count vs unique
traders ratio, trade-size uniformity, holder growth vs trader growth, paid boosts, insider networks, synchronized trades.
"""
from __future__ import annotations

import statistics
from typing import Any


def analyze(bundle: dict[str, Any], orderflow: dict | None = None, clusters: dict | None = None, attention: dict | None = None) -> dict[str, Any]:
    mk = bundle.get("market") or {}
    trades = bundle.get("trades") or []
    of = orderflow or {}
    facts, interp, alts, unknowns = [], [], [], []
    score = 0.0; weight = 0.0
    def sig(name, value, severity, fact, interpretation, alternative):
        nonlocal score, weight
        facts.append(fact); interp.append(f"{name}: {interpretation}"); alts.append(f"{name}: {alternative}")
        score += severity; weight += 1
    liq, v24 = mk.get("liquidity_usd_total"), (mk.get("vol") or {}).get("24h")
    if liq and v24:
        turnover = v24 / liq
        if turnover > 20:
            sig("turnover", turnover, 0.8, f"24h volume is {turnover:.0f}x displayed liquidity", "volume far above what the pool depth can organically support; circular or wash-like trading likely", "very new tokens on launchpads legitimately turn over many times a day in the first 48h")
        elif turnover > 8:
            sig("turnover", turnover, 0.4, f"24h volume is {turnover:.1f}x displayed liquidity", "high turnover, partly bot-driven", "active memecoin trading with thin pools often shows 5-10x")
    org = of.get("organic_share")
    if org is not None:
        if org < 0.03:
            sig("organic_share", org, 0.7, f"organic volume share {org:.1%}", "provider classifies almost all flow as non-organic (bots/arb/wash)", "provider methodology may undercount organic flow routed through aggregators")
        elif org < 0.1:
            sig("organic_share", org, 0.35, f"organic volume share {org:.1%}", "most volume is bot/arbitrage-like", "normal for tokens with active MEV/arb and many small bots")
    ts = of.get("two_sided_wallet_share")
    if ts is not None and ts > 0.4:
        sig("two_sided", ts, 0.6, f"{ts:.0%} of recent window volume came from wallets that both bought and sold", "self-trading or bot cycling inflates volume", "market makers and arbitrage bots are two-sided by nature")
    tx = mk.get("txns") or {}
    t24 = tx.get("24h")
    if t24 and t24[2] and (t24[0] or 0) + (t24[1] or 0):
        per = ((t24[0] or 0) + (t24[1] or 0)) / t24[2]
        if per > 15:
            sig("tx_per_trader", per, 0.5, f"{per:.0f} transactions per unique trader in 24h", "a few wallets generate most transactions (bots or wash)", "sniper/arb bots are present on nearly every active Solana memecoin")
    if trades:
        usd = [t[4] or 0 for t in trades if t[4]]
        if len(usd) > 30:
            cv = statistics.pstdev(usd) / (statistics.mean(usd) or 1)
            if cv < 0.3:
                sig("size_uniformity", cv, 0.6, f"recent trade sizes are unusually uniform (cv {cv:.2f})", "scripted volume generation", "copy-trade bots with fixed sizes also produce uniform prints")
    hc = (mk.get("holder_change") or {}).get("24h")
    if hc is not None and mk.get("num_traders_24h") and mk.get("holder_count"):
        if hc > 20 and (mk["num_traders_24h"] / mk["holder_count"]) < 0.1:
            sig("holder_proliferation", hc, 0.5, f"holders +{hc:.0f}% in 24h while only {mk['num_traders_24h']/mk['holder_count']:.0%} of holders traded", "wallet splitting / airdrop-style holder inflation", "a viral airdrop or wide distribution event can look identical")
    if attention and attention.get("paid_boost"):
        sig("paid_boost", 1, 0.3, "active paid DEX Screener boost", "promotion is paid; trending position is partly bought", "many legitimate teams buy boosts; it is a cost of visibility, not proof of manipulation")
    if clusters and clusters.get("n_clusters"):
        hi = [c for c in clusters["clusters"] if c["confidence"] == "HIGH"]
        if hi:
            sig("clusters", len(hi), 0.6, f"{len(hi)} high-confidence wallet cluster(s) among top holders", "coordinated ownership can coordinate pumping and dumping", "funding from a shared CEX hot wallet produces false clusters")
    # social evidence we cannot see
    unknowns.append("bot-like posting, identical/synchronized posts, paid calls, follower jumps and fake engagement not measured (no social API); record browser observations with `memelab social-note` to include them")
    label = "MIXED / UNCERTAIN"
    if weight == 0:
        label = "MOSTLY ORGANIC" if (org is None or org >= 0.1) else "MIXED / UNCERTAIN"
        wash = "LOW"
    else:
        avg = score / weight
        strong = sum(1 for _ in interp)
        if avg >= 0.65 and strong >= 3:
            label = "SEVERELY MANIPULATED"; wash = "HIGH"
        elif avg >= 0.5 and strong >= 2:
            label = "LIKELY MANUFACTURED"; wash = "HIGH" if (liq and v24 and v24 / liq > 20) else "MODERATE"
        elif avg >= 0.35:
            label = "MIXED / UNCERTAIN"; wash = "MODERATE"
        else:
            label = "MOSTLY ORGANIC"; wash = "LOW"
    confidence = "LOW" if weight <= 1 else "MODERATE" if weight <= 3 else "HIGH"
    if label in ("SEVERELY MANIPULATED", "LIKELY MANUFACTURED") and confidence == "LOW":
        label = "MIXED / UNCERTAIN"  # do not accuse on one signal
    return {"label": label, "wash_trading": wash, "confidence": confidence, "n_signals": int(weight),
            "observed_facts": facts, "possible_interpretation": interp, "alternative_explanations": alts,
            "facts": facts, "inferences": interp, "heuristics": ["never accuse without evidence; every signal carries an innocent alternative"], "unknowns": unknowns}
