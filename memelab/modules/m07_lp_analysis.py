"""07_LP_ANALYSIS: who controls liquidity, how removable it is, exit-door risk.

Sources: rugcheck markets[].lp (lpLockedPct, holders with owner/pct), lockers, pool types (launchpad-owned pools
such as pump.fun/PumpSwap and Meteora DBC graduation pools are protocol-controlled), DEX Screener pool list.
"""
from __future__ import annotations

from typing import Any

PROTOCOL_LP_OWNERS = {
    # known program / protocol authorities that custody graduated-pool LP (non-exhaustive, extend as observed)
    "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg": "pump.fun migration authority",
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA": "PumpSwap program",
    "dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN": "Meteora DBC program",
}
LOCKERS = {"Streamflow", "Jupiter Lock", "Bonk Lock", "Raydium Locker", "UNCX"}


def analyze(bundle: dict[str, Any]) -> dict[str, Any]:
    pools = bundle.get("pools") or []
    ident = bundle.get("identity") or {}
    facts, inferences, unknowns, heur = [], [], [], []
    per_pool = []
    total_liq = sum((p.get("reserve_usd") or 0) for p in pools)
    weighted_locked = 0.0; weighted_known = 0.0
    team_controlled_usd = 0.0; removable_usd = 0.0
    biggest_single_position_share = None
    for p in pools:
        lp = p.get("lp")
        res = p.get("reserve_usd") or 0
        row = {"pool": p.get("pool"), "dex": p.get("dex") or p.get("market_type"), "reserve_usd": res, "locked_pct": None, "control": "UNKNOWN", "notes": []}
        mt = (p.get("market_type") or "") + " " + (p.get("dex") or "")
        is_launchpad_pool = any(k in mt.lower() for k in ("pump", "dbc", "meteora_damm_v2", "damm", "dyn", "bonding", "raydium_launchlab", "launchlab")) or (p.get("pool") == ident.get("graduated_pool"))
        if lp:
            lk = lp.get("locked_pct")
            row["locked_pct"] = lk
            holders = lp.get("holders") or []
            top = holders[0] if holders else None
            if top:
                row["top_lp_holder"] = {"owner": top.get("owner"), "pct": top.get("pct")}
                if top.get("pct") is not None:
                    biggest_single_position_share = max(biggest_single_position_share or 0, top["pct"])
            # classify control
            if lk is not None and lk >= 95:
                row["control"] = "LOCKED_OR_BURNED"
                row["notes"].append(f"{lk:.0f}% of LP tokens locked/burned")
            elif top and top.get("owner") in PROTOCOL_LP_OWNERS:
                row["control"] = "PROTOCOL"
                row["notes"].append(f"LP held by {PROTOCOL_LP_OWNERS[top['owner']]}")
            elif is_launchpad_pool and (lk or 0) >= 50:
                row["control"] = "PROTOCOL_LIKELY"
                row["notes"].append("graduation pool; LP typically protocol-custodied")
            elif top and (top.get("pct") or 0) >= 50:
                row["control"] = "SINGLE_WALLET"
                row["notes"].append(f"one wallet {top['owner'][:8]}.. controls {top['pct']:.0f}% of LP tokens" + (" (flagged insider)" if top.get("insider") else ""))
                if top.get("owner") in (ident.get("creator"), ident.get("dev")):
                    row["control"] = "TEAM"
                    row["notes"].append("LP owner is the token creator/dev wallet")
            else:
                row["control"] = "DISPERSED" if len(holders) > 3 else "UNKNOWN"
            if lk is not None:
                weighted_locked += lk * res; weighted_known += res
                removable_usd += res * (1 - lk / 100) if row["control"] not in ("PROTOCOL", "PROTOCOL_LIKELY") else 0
            if row["control"] == "TEAM":
                team_controlled_usd += res
        else:
            if is_launchpad_pool:
                row["control"] = "PROTOCOL_LIKELY"; row["notes"].append("launchpad/graduation pool type; LP ownership not reported")
            else:
                row["notes"].append("LP token ownership not reported by any source")
            if p.get("labels") and any(l in ("CLMM", "DLMM", "DYN2") for l in p["labels"]):
                row["notes"].append("concentrated liquidity position(s); removable by position owner at any time")
                removable_usd += res
        per_pool.append(row)
    per_pool.sort(key=lambda r: r["reserve_usd"] or 0, reverse=True)
    locked_pct_weighted = (weighted_locked / weighted_known) if weighted_known else None
    for r in per_pool[:6]:
        facts.append(f"{r['dex']} {str(r['pool'])[:8]}..: ${r['reserve_usd']:,.0f}, control {r['control']}" + (f", LP locked {r['locked_pct']:.0f}%" if r['locked_pct'] is not None else "") + ("; " + "; ".join(r["notes"]) if r["notes"] else ""))
    if locked_pct_weighted is not None:
        facts.append(f"liquidity-weighted LP locked/burned share {locked_pct_weighted:.0f}% over ${weighted_known:,.0f} of pools with LP data")
    if total_liq:
        facts.append(f"estimated removable liquidity ${removable_usd:,.0f} of ${total_liq:,.0f} displayed ({removable_usd/total_liq:.0%})")
    main = per_pool[0] if per_pool else None
    one_venue = (main and total_liq and main["reserve_usd"] / total_liq > 0.8)
    # risk label
    risk = "MODERATE"; why = []
    if not per_pool:
        risk = "HIGH"; why.append("no pool data")
    else:
        crit = [r for r in per_pool if r["control"] in ("TEAM", "SINGLE_WALLET") and total_liq and r["reserve_usd"] / total_liq > 0.3]
        if crit:
            risk = "CRITICAL" if any(r["control"] == "TEAM" for r in crit) else "HIGH"
            why.append("a single wallet or the team controls the LP of a pool holding >30% of liquidity")
        elif total_liq and removable_usd / total_liq > 0.5 and not all(r["control"] in ("PROTOCOL", "PROTOCOL_LIKELY", "LOCKED_OR_BURNED") for r in per_pool if r["reserve_usd"] > 0.2 * total_liq):
            risk = "HIGH"; why.append(f"more than half of displayed liquidity ({removable_usd/total_liq:.0%}) is removable by position owners")
        elif all(r["control"] in ("PROTOCOL", "PROTOCOL_LIKELY", "LOCKED_OR_BURNED") for r in per_pool if r["reserve_usd"] > 0.2 * total_liq):
            risk = "LOW" if not one_venue else "MODERATE"
            why.append("main pools are protocol-custodied or locked" + ("; but liquidity sits in one venue" if one_venue else ""))
        else:
            why.append("mixed control; concentrated-liquidity positions can be withdrawn")
    if one_venue:
        inferences.append("liquidity depends on one venue; depth elsewhere is negligible")
    heur.append("'LP burned' is not a universal guarantee: protocol-owned pools can migrate, concentrated positions are not LP tokens, and a team can still hold the token supply")
    if any(r["control"] == "UNKNOWN" for r in per_pool):
        unknowns.append("LP ownership unknown for some pools (no RugCheck market entry)")
    # liquidity trend from jupiter stats
    mk = bundle.get("market") or {}
    for w in ("1h", "6h", "24h"):
        v = mk.get(f"liquidity_change_{w}")
        if v is not None:
            facts.append(f"liquidity change {w}: {v:+.1f}%")
            if v < -20:
                inferences.append(f"liquidity fell {abs(v):.0f}% in {w}: possible LP withdrawal, investigate")
    return {"per_pool": per_pool, "lp_risk": risk, "reason": "; ".join(why), "locked_pct": locked_pct_weighted, "removable_usd": removable_usd,
            "team_controlled_usd": team_controlled_usd, "total_liquidity_usd": total_liq, "single_venue": bool(one_venue),
            "biggest_single_lp_position_pct": biggest_single_position_share,
            "facts": facts, "inferences": inferences, "heuristics": heur, "unknowns": unknowns}
