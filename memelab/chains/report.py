"""Ecosystem sections of the scout report (MARKET REGIME, CHAIN ROTATION, NARRATIVE ROTATION, LAUNCHPADS, EMERGING CHAINS,
CHAINS BEING DE-EMPHASIZED, WHAT WOULD CHANGE THE CURRENT ECOSYSTEM VIEW). Token sections come from the core scout renderer."""
from __future__ import annotations

import time
from typing import Any

from . import registry as R


def _m(x, d=1, suffix="%"):
    return "UNKNOWN" if x is None else f"{x:+.{d}f}{suffix}"


def _usd(x):
    if x is None:
        return "UNKNOWN"
    return f"${x / 1e9:,.2f}B" if abs(x) >= 1e9 else f"${x / 1e6:,.1f}M" if abs(x) >= 1e6 else f"${x:,.0f}"


def render(regime: dict, rotation: dict, narratives: dict, emerging: dict, launchpads: dict, baskets: dict, when: float | None = None) -> str:
    t = when or time.time()
    L = [f"# ECOSYSTEM VIEW, {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(t))}", ""]
    # ---- regime ----
    L += ["# MARKET REGIME", "", f"REGIME: {regime['regime']} (confidence {regime['confidence']}; position-size multiplier {regime.get('size_multiplier')})", ""]
    for f in regime.get("facts") or []:
        L.append(f"- FACT: {f}")
    for i in regime.get("inferences") or []:
        L.append(f"- INFERENCE: {i}")
    if regime.get("unknowns"):
        L.append(f"- UNKNOWN: {', '.join(regime['unknowns'])}")
    L.append("")
    # ---- chain rotation ----
    L += ["# CHAIN ROTATION", "", "| Chain | SOI | Trend | Research allocation | Major change |", "|---|---|---|---|---|"]
    for cid in rotation.get("ranked") or []:
        s = rotation["chains"][cid]; cfg = R.CHAINS[cid]
        comps = s["components"]
        big = max(comps.items(), key=lambda kv: kv[1]["points"] / kv[1]["max"])
        change = (f"{s['delta']:+.1f} vs last run" if s.get("delta") is not None else "first measurement") + f"; strongest {big[0].replace('_', ' ')} {big[1]['points']}/{big[1]['max']}"
        if s.get("status") == "LOW-PRIORITY MONITORING":
            change += "; LOW-PRIORITY MONITORING"
        L.append(f"| {cfg['name']} | {s['soi']} | {s['trend']} | {s['research_allocation']} | {change} |")
    L.append("")
    L.append("SOI components (max): DEX activity 20, meme activity 20, participation 15, capital flows 15, attention 15, opportunity quality 15. Unknown inputs earn zero; coverage is shown per chain.")
    L.append("")
    for cid in rotation.get("ranked") or []:
        s = rotation["chains"][cid]
        L.append(f"## {R.CHAINS[cid]['name']} (SOI {s['soi']}, coverage {s['coverage']:.0%})")
        L.append("")
        L.append(f"- {s['statement']}")
        for k, v in s["components"].items():
            parts = "; ".join(f"{p['label']}: {('%.2f' % p['v']) if p['v'] is not None else 'UNKNOWN'}" for p in v["parts"])
            L.append(f"- {k.replace('_', ' ')} {v['points']}/{v['max']}: {parts}")
        for f in s["components"].values():
            for fact in f["facts"]:
                L.append(f"- FACT: {fact}")
        L.append("")
    for st in rotation.get("statements") or []:
        if st.startswith("FACT:") and "rotation" in st.lower():
            L.append(f"- {st}")
    L.append("")
    # ---- narratives ----
    L += ["# NARRATIVE ROTATION", ""]
    cats = [n for n in narratives.get("narratives") or [] if n["source"] == "coingecko_category"]
    kws = [n for n in narratives.get("narratives") or [] if n["source"] == "keyword"]
    if cats:
        L += ["| Narrative | Lifecycle | Mcap | 24h | Volume 24h | Catalyst events 7d | Top tokens |", "|---|---|---|---|---|---|---|"]
        for n in cats[:18]:
            L.append(f"| {n['name']} | {n['lifecycle']} | {_usd(n.get('mcap'))} | {_m(n.get('mcap_chg_24h_pct'))} | {_usd(n.get('vol_24h'))} | {n['catalyst_events_7d'] if n['catalyst_events_7d'] is not None else 'n/a'} | {', '.join(n.get('top3') or [])[:60]} |")
        L.append("")
        for n in cats[:18]:
            if n["lifecycle"] not in ("UNKNOWN", "MATURE"):
                L.append(f"- {n['name']}: {n['lifecycle']} ({n['lifecycle_reason']})")
        L.append("")
    if kws:
        L.append("Keyword clusters across chains (a word shared by >= 3 distinct token names in trending pools and meme markets; a cluster is a candidate narrative, not a verified one):")
        L.append("")
        for n in kws:
            L.append(f"- {n['name']}: {n.get('token_count')} tokens on {', '.join(n.get('chains') or []) or 'n/a'}; catalyst events 7d {n['catalyst_events_7d']}; lifecycle {n['lifecycle']} ({n['lifecycle_reason']})")
        L.append("")
    L.append("Lifecycle labels need history; EMERGING/ACCELERATING/MANIA come from 24h change and volume/mcap, EXHAUSTING/DEAD from drawdown versus the 14- and 30-day highs of stored snapshots.")
    L.append("")
    # ---- benchmark ----
    L += ["# MEME BENCHMARK BASKET (CoinGecko meme-token top 100, by cap bucket)", ""]
    for name, b in (baskets.get("buckets") or {}).items():
        L.append(f"- {name}: n={b['n']}, median 24h {_m(b['median_chg_24h'])}, median 7d {_m(b['median_chg_7d'])}")
    L.append("")
    # ---- launchpads ----
    L += ["# LAUNCHPADS", ""]
    for r in launchpads.get("rows") or []:
        if not r["detectable"]:
            L.append(f"- {R.CHAINS[r['chain_id']]['name']} / {r['name']}: UNKNOWN (pools trade on a general DEX; not identifiable from pool data)")
        else:
            L.append(f"- {R.CHAINS[r['chain_id']]['name']} / {r['name']}: {r['new_pools_sample']} in newest-pools sample, {r['pools_in_trending']} in trending/top pools, sample vol 24h {_usd(r['sample_vol_24h'])}, sample liq {_usd(r['sample_liq'])}")
    L.append("")
    # ---- emerging ----
    L += ["# EMERGING CHAINS", ""]
    if not emerging.get("candidates"):
        L.append("- none detected this run (no network outside the registry with >= 2 cross-network trending pools or >= $200M TVL)")
    for c in emerging.get("candidates") or []:
        L.append(f"- {c['name']}: level {c['level']}; {'; '.join(c['signals'])}")
    L.append("")
    # ---- de-emphasized ----
    L += ["# CHAINS BEING DE-EMPHASIZED", ""]
    de = [cid for cid, s in rotation.get("chains", {}).items() if s.get("status") == "LOW-PRIORITY MONITORING" or s.get("research_allocation") == "WATCHLIST"]
    if not de:
        L.append("- none")
    for cid in de:
        s = rotation["chains"][cid]
        L.append(f"- {R.CHAINS[cid]['name']}: SOI {s['soi']}, allocation {s['research_allocation']}, status {s.get('status')}. Existing watchlist tokens keep refreshing; discovery is {'paused' if s.get('status') == 'LOW-PRIORITY MONITORING' else 'reduced'}.")
    L.append("")
    # ---- what would change ----
    L += ["# WHAT WOULD CHANGE THE CURRENT ECOSYSTEM VIEW", ""]
    top = (rotation.get("ranked") or [None])[0]
    L.append(f"- Regime flips if BTC closes below its 20d and 50d MAs with meme breadth under 30% (-> RISK-OFF) or if stablecoin supply falls >1% over a week while BTC breaks down (-> CAPITAL FLIGHT). Current: {regime['regime']}.")
    if top:
        L.append(f"- Chain leadership changes if another chain's SOI exceeds {R.CHAINS[top]['name']}'s ({rotation['chains'][top]['soi']}) on two consecutive runs; one run of divergence is noise.")
    L.append("- A narrative moves from ACCELERATING to MANIA at >= +25% category mcap in 24h or volume/mcap >= 1.0; MANIA to EXHAUSTING when mcap falls >20% from its 14-day high.")
    L.append("- A Tier-2 chain earns BUILD PARTIAL at SOI >= 60 with >= 60% data coverage; an unknown network earns MONITOR at 2 cross-network trending pools and BUILD PARTIAL at 6.")
    L.append("- Any input marked UNKNOWN above is a reason the view could be wrong; the next run with that input present can move the scores without any market change.")
    L.append("")
    return "\n".join(L)
