"""23_TRADE_THESIS: assemble the complete thesis answering every question in the curriculum checklist,
plus the anti-confirmation-bias preamble (WHAT WOULD MAKE THIS TOKEN UNACCEPTABLE?)."""
from __future__ import annotations

from typing import Any


def unacceptable_conditions(bundle: dict[str, Any]) -> list[str]:
    """Written BEFORE deep research: falsification targets for this specific token."""
    mk = bundle.get("market") or {}
    ident = bundle.get("identity") or {}
    conds = [
        "an active mint or freeze authority, permanent delegate, or transfer hook of unknown program",
        "a transfer fee above 5% or a fee authority that can raise it",
        "the main pool's LP controlled by the team or a single wallet, or liquidity concentrated in one removable position",
        "inability to sell $5,000 within 5% impact, or no sell route at any tested size",
        "an unexplained single economic holder above 15% or cluster-adjusted ownership above 25%",
        "creator/dev or early wallets distributing while price rises (strength concealing distribution)",
        "24h volume more than 20x liquidity with near-zero organic share (manufactured activity)",
        "price more than 15% or 3 ATR above the nearest structural invalidation (chasing)",
        "lifecycle evidence pointing to DISTRIBUTION or BREAKDOWN with fading volume",
    ]
    if ident.get("launchpad"):
        conds.append(f"graduation pool for {ident['launchpad']} migrated or liquidity moved since graduation without explanation")
    if (mk.get("age_hours") or 1e9) < 24:
        conds.append("token younger than 24h: no retest history, sniper inventory unknown; default to WATCH unless depth is exceptional")
    return conds


def _first_line(d: dict | None, key: str, default="UNABLE TO DETERMINE"):
    if not d:
        return default
    v = d.get(key)
    return v if v not in (None, "", []) else default


def assemble(bundle: dict[str, Any], mods: dict[str, dict]) -> dict[str, Any]:
    ident, mk = bundle.get("identity") or {}, bundle.get("market") or {}
    m = mods
    depth, lp, mech, hold, cl, early, of = m.get("depth") or {}, m.get("lp") or {}, m.get("mechanics") or {}, m.get("holders") or {}, m.get("clusters") or {}, m.get("early") or {}, m.get("orderflow") or {}
    st, bo, en, rr, sz, ex, att, man, lc, rs = (m.get(k) or {} for k in ("structure", "breakout", "entries", "rr", "sizing", "exit", "attention", "manipulation", "lifecycle", "rs"))
    q: dict[str, Any] = {}
    q["WHAT IS THE TOKEN?"] = f"{ident.get('name')} ({ident.get('symbol')}) on Solana, mint {bundle.get('mint')}, {mech.get('standard') or 'unknown standard'}, launched via {ident.get('launchpad') or 'unknown launchpad'}; age {mk.get('age_hours', 0)/24:.1f} days" if mk.get("age_hours") else f"{ident.get('name')} ({ident.get('symbol')}), mint {bundle.get('mint')}"
    q["WHY IS IT RECEIVING ATTENTION?"] = "; ".join((bundle.get("discovery_signals") or {}).get("why") or []) or "surfaced on request"
    q["WHAT LIFECYCLE STAGE IS IT IN?"] = f"{lc.get('stage')}{('/' + lc['sub_stage']) if lc.get('sub_stage') else ''} (confidence {lc.get('confidence')}); alternative {lc.get('alternative_stage')}"
    q["WHO OWNS THE SUPPLY?"] = f"adjusted top-10 {hold.get('adjusted_top10_pct', 0):.1f}% (raw {hold.get('raw_top10_pct', 0):.1f}%), pools {hold.get('pool_pct', 0):.1f}%, dev {hold.get('dev_holding_pct') if hold.get('dev_holding_pct') is not None else 'n/a'}%, largest unexplained holder {hold.get('largest_unexplained_pct') or 0:.2f}%" if hold else "UNABLE TO DETERMINE"
    q["WHAT ARE IMPORTANT CLUSTERS?"] = f"{cl.get('n_clusters', 0)} cluster signal(s); cluster-adjusted ownership {cl.get('cluster_adjusted_ownership_pct') if cl.get('cluster_adjusted_ownership_pct') is not None else 'n/a'}% at {cl.get('confidence')} confidence"
    q["WHAT ARE INSIDERS / EARLY HOLDERS DOING?"] = f"{early.get('large_holder_net_direction')} in the recent trade window; dev traded buy ${sum(d['buy_usd'] for d in early.get('dev', [])):,.0f} / sell ${sum(d['sell_usd'] for d in early.get('dev', [])):,.0f}"
    q["IS SUPPLY BEING ACCUMULATED OR DISTRIBUTED?"] = f"{early.get('absorption') or early.get('large_holder_net_direction') or 'UNABLE TO DETERMINE'}"
    q["WHAT LIQUIDITY ACTUALLY EXISTS?"] = f"displayed ${mk.get('liquidity_usd_total') or 0:,.0f}; exit capacity ~${depth.get('exit_capacity_usd_3pct') or 0:,.0f} at 3% impact, ~${depth.get('exit_capacity_usd_10pct') or 0:,.0f} at 10%"
    q["HOW MUCH CAN I REALISTICALLY ENTER?"] = f"~${depth.get('entry_capacity_usd_1_5pct') or 0:,.0f} within 1.5% impact"
    q["HOW MUCH CAN I REALISTICALLY EXIT?"] = q["WHAT LIQUIDITY ACTUALLY EXISTS?"]
    q["WHO CONTROLS THE LP?"] = f"LP risk {lp.get('lp_risk')}: {lp.get('reason')}"
    q["WHAT TOKEN-LEVEL RISKS EXIST?"] = ", ".join(mech.get("flags") or []) or "none observed among authorities/extensions" + ("" if mech.get("extensions") is not None else " (extensions not enumerated)")
    pfa = st.get("pct_from_ath")
    q["WHAT DOES PRICE STRUCTURE SAY?"] = (f"{st.get('structure')}; {st.get('structure_summary') or ''}" + (f"; {pfa:+.0f}% from ATH" if isinstance(pfa, (int, float)) else "")) if st and st.get("structure") else "UNABLE TO DETERMINE (no candles)"
    q["WHAT DOES ORDER FLOW SAY?"] = f"buy/sell vol ratio {of.get('buy_sell_vol_ratio') if of.get('buy_sell_vol_ratio') is None else round(of['buy_sell_vol_ratio'], 2)}, net buyers 24h {of.get('net_buyers_h24')}, organic share {of.get('organic_share') if of.get('organic_share') is None else f'{of['organic_share']:.0%}'}"
    q["WHAT DOES ATTENTION SAY?"] = f"{att.get('trend')}; holder change 24h {((att.get('holder_change') or {}).get('24h'))}%"
    q["IS THE MOMENTUM ORGANIC?"] = f"{man.get('label')} (confidence {man.get('confidence')}, wash-trading {man.get('wash_trading')})"
    q["WHAT WOULD MAKE AN ENTRY ATTRACTIVE?"] = "; ".join(e.get("condition", "") for e in en.get("entries") or []) or "no structurally supported entry at present"
    q["WHAT ENTRY STYLE FITS THE SETUP?"] = ", ".join(e.get("style", "") for e in en.get("entries") or []) or "none"
    q["WHAT INVALIDATES THE THESIS?"] = "; ".join(f"{e.get('style')}: {e.get('invalidation_text')}" for e in en.get("entries") or []) or "UNABLE TO DETERMINE (no entry defined)"
    q["WHERE IS LIKELY SUPPLY?"] = ", ".join(f"{z['low']:.6g}-{z['high']:.6g} ({z['tf']}, {z['touches']} touches)" for z in (st.get("zones") or []) if z.get("kind") == "RESISTANCE")[:400] or "UNABLE TO DETERMINE"
    pe = rr.get("per_entry") or []
    q["WHAT IS THE RISK/REWARD?"] = "; ".join(f"{p.get('style')}: {p.get('rr_base')}R to first supply, {p.get('rr_bull')}R bull, EV {p.get('ev_r_low')} to {p.get('ev_r_high')}R" for p in pe) or "UNABLE TO DETERMINE"
    q["WHAT POSITION SIZE IS ALLOWED BY RISK?"] = (f"${(sz.get('risk_constraint') or {}).get('size_usd'):,.0f}" if (sz.get("risk_constraint") or {}).get("size_usd") else "account-risk inputs not supplied; not computed")
    lq = sz.get("liquidity_constraint") or {}
    q["WHAT POSITION SIZE IS ALLOWED BY LIQUIDITY?"] = f"entry max ${lq.get('entry_max') or 0:,.0f}; exit-now max ${lq.get('exit_max_now') or 0:,.0f}; by future multiple {lq.get('exit_max_by_multiple')}"
    q["WHERE SHOULD PROFITS BE TAKEN?"] = "; ".join(f"{r.get('trigger')} -> {r.get('pct_of_position')}%" for r in ex.get("ladder") or []) or "UNABLE TO DETERMINE"
    q["WHAT WOULD IMPROVE THE SETUP?"] = "; ".join(lc.get("confirm_if") or []) if isinstance(lc.get("confirm_if"), list) else str(lc.get("confirm_if") or "")
    q["WHAT WOULD DETERIORATE IT?"] = "; ".join(lc.get("reject_if") or []) if isinstance(lc.get("reject_if"), list) else str(lc.get("reject_if") or "")
    return {"questions": q, "unacceptable_conditions": unacceptable_conditions(bundle)}
