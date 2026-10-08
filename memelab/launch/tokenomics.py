"""TOKENOMICS_ANALYSIS: initial float, insider inventory, locked inventory, overhang, valuation and liquidity ratios.

Provenance on every number: MECHANISM (launchpad rule, chain-derived config), ON-CHAIN (holders read from chain indexes),
CLAIMED (project statement, never treated as verified), PROJECTED (expected value before trading). Locked tokens count as safe
only when the lock is a verified mechanism (launchpad vesting config, protocol locker); a claimed lock stays UNKNOWN.
"""
from __future__ import annotations

from typing import Any


def analyze(c: dict, holders: dict | None = None, claimed: dict | None = None, sol_price: float | None = None) -> dict[str, Any]:
    tk = dict(c.get("tokenomics") or {})
    claimed = claimed or {}
    exp = c.get("expected") or {}
    facts, inferences, unknowns, flags = [], [], [], []
    basis = tk.get("basis") or ("CLAIMED" if claimed else "UNKNOWN")
    total = tk.get("total_supply") or claimed.get("total_supply")
    curve = tk.get("curve_sale_pct")
    lp = tk.get("lp_reserved_pct") if tk.get("lp_reserved_pct") is not None else tk.get("pool_pct")
    locked = tk.get("locked_vesting_pct") if tk.get("locked_vesting_pct") is not None else tk.get("vault_pct")
    team_mech = tk.get("team_alloc_pct_mechanism")
    if total:
        facts.append(f"total supply {total:,.0f} ({basis})")
    if curve is not None:
        facts.append(f"{curve:.1f}% sold through the launch curve, {lp or 0:.1f}% reserved for the DEX pool ({basis})")
    elif lp is not None:
        facts.append(f"{lp:.1f}% of supply goes to the pool at deployment ({basis})")
    if locked:
        facts.append(f"{locked:.1f}% locked or vesting ({basis}; terms: {tk.get('vesting') or tk.get('vault_terms')})")
    # ---- observed holders (ON-CHAIN) ----
    h = holders or {}
    dev_pct = h.get("dev_pct")
    top10 = h.get("top10_ex_pool_pct")
    insider_net = h.get("insider_network_pct")
    cluster = h.get("cluster_pct")
    if dev_pct is not None:
        facts.append(f"creator wallet holds {dev_pct:.2f}% (ON-CHAIN)")
    if top10 is not None:
        facts.append(f"top-10 holders excluding pools/curve hold {top10:.1f}% (ON-CHAIN)")
    if insider_net:
        facts.append(f"RugCheck insider networks hold {insider_net:.1f}% (ON-CHAIN graph; inference by RugCheck)")
    # ---- derived ----
    insider_parts = [x for x in (dev_pct, insider_net, cluster) if x]
    insider = max(insider_parts) if insider_parts else (team_mech if team_mech is not None else claimed.get("team_pct"))
    insider_basis = "ON-CHAIN" if insider_parts else ("MECHANISM" if team_mech is not None else ("CLAIMED" if claimed.get("team_pct") is not None else None))
    if insider is None:
        unknowns.append("insider allocation")
    # initial float: what can trade right after launch. Curve-sold supply is liquid (held by buyers); LP inventory is liquid via the pool; vesting is not.
    init_float = None
    if curve is not None:
        init_float = curve + (lp or 0)
    elif lp is not None:
        init_float = lp + (tk.get("airdrop_pct") or 0)
    elif claimed.get("circulating_at_launch_pct") is not None:
        init_float = claimed["circulating_at_launch_pct"]; inferences.append("initial float is CLAIMED; verify against on-chain distribution at launch")
    if init_float is None:
        unknowns.append("initial float")
    overhang = (locked or 0) + (claimed.get("unlocking_30d_pct") or 0) if (locked is not None or claimed.get("unlocking_30d_pct") is not None) else None
    if overhang:
        inferences.append(f"future supply overhang about {overhang:.1f}% of supply as locks and vesting end")
    # valuation & liquidity
    mcap = (c.get("obs") or {}).get("mcap_usd")
    liq = (c.get("obs") or {}).get("liquidity_usd")
    exp_val = exp.get("grad_mcap_usd") or exp.get("start_mcap_usd") or claimed.get("launch_fdv_usd")
    exp_liq = exp.get("grad_liquidity_usd") or claimed.get("launch_liquidity_usd")
    trading = c.get("state") == "E"
    liq_ratio = (liq / mcap) if trading and liq and mcap else ((exp_liq / exp_val) if exp_liq and exp_val else None)
    liq_basis = "OBSERVED" if trading and liq and mcap else ("PROJECTED" if liq_ratio is not None else None)
    if liq_ratio is not None:
        facts.append(f"liquidity / market cap {liq_ratio:.2f} ({liq_basis})")
    if exp_val:
        facts.append(f"expected valuation at {'graduation' if 'grad_mcap_usd' in exp else 'launch'} ${exp_val:,.0f} (PROJECTED: {exp.get('basis') or 'claimed'})")
    # flags
    if insider is not None and insider > 30:
        flags.append(f"HIGH_INSIDER:{insider:.0f}%")
    if init_float is not None and init_float < 20:
        flags.append(f"LOW_FLOAT:{init_float:.0f}%")
    fee = tk.get("transfer_fee_bps")
    if fee:
        flags.append(f"TRANSFER_FEE:{fee}bps")
    if tk.get("transfer_hook"):
        flags.append("TRANSFER_HOOK")
    if locked and "CLAIMED" in basis:
        unknowns.append("lock contract, controller and unlock dates (claimed lock, not verified)")
    return {"basis": basis, "total_supply": total, "initial_float_pct": init_float, "initial_insider_pct": insider, "insider_basis": insider_basis,
            "locked_pct": locked, "overhang_pct": overhang, "liquidity_ratio": liq_ratio, "liquidity_basis": liq_basis, "expected_valuation_usd": exp_val,
            "expected_liquidity_usd": exp_liq, "flags": flags, "facts": facts, "inferences": inferences, "unknowns": unknowns}
