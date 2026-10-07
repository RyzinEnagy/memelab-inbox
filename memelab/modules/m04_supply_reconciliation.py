"""04_SUPPLY_RECONCILIATION: recompute valuation independently and build the supply-overhang view.

Sources: on-chain mint supply (rugcheck token.supply or RPC), jupiter circ/total supply, provider FDV/mcap.
Burned tokens on Solana are usually sent to incinerator addresses or the mint supply is reduced; locked / vesting
supply is inferred from classified holders (vesting contracts, lockers) when available.
"""
from __future__ import annotations

from typing import Any

BURN_ADDRESSES = {"1nc1nerator11111111111111111111111111111111", "11111111111111111111111111111111", "1111111111111111111111111111111111111111111"}


def analyze(bundle: dict[str, Any], holders_out: dict | None = None) -> dict[str, Any]:
    mk, a = bundle.get("market") or {}, bundle.get("authorities") or {}
    facts, inferences, unknowns, heur = [], [], [], []
    dec = a.get("decimals") if a.get("decimals") is not None else (bundle.get("identity") or {}).get("decimals")
    raw = a.get("supply_raw_rpc") or a.get("supply_raw")
    onchain_supply = None
    if raw is not None and dec is not None:
        try:
            onchain_supply = float(raw) / (10 ** int(dec))
            facts.append(f"on-chain mint supply {onchain_supply:,.0f} ({'rpc' if a.get('supply_raw_rpc') else 'rugcheck'})")
        except (TypeError, ValueError):
            pass
    circ, total = mk.get("circ_supply"), mk.get("total_supply")
    if circ is not None:
        facts.append(f"jupiter circulating {circ:,.0f}; total {total:,.0f}" if total is not None else f"jupiter circulating {circ:,.0f}")
    price = mk.get("price_usd")
    # independent recomputation
    recomputed = {}
    if price:
        if onchain_supply:
            recomputed["fdv_onchain_supply"] = price * onchain_supply
        if circ:
            recomputed["mcap_circ"] = price * circ
        if total:
            recomputed["fdv_total"] = price * total
    prov_fdv, prov_mc = mk.get("fdv"), mk.get("market_cap")
    denom = None
    if prov_fdv and recomputed:
        best = min(recomputed.items(), key=lambda kv: abs(kv[1] - prov_fdv) / prov_fdv)
        if abs(best[1] - prov_fdv) / prov_fdv < 0.05:
            denom = best[0]
            facts.append(f"provider FDV ${prov_fdv:,.0f} matches price x {denom.replace('fdv_', '').replace('mcap_', '')} supply (within 5%)")
        else:
            facts.append(f"provider FDV ${prov_fdv:,.0f} does not match any recomputed denominator: " + ", ".join(f"{k} ${v:,.0f}" for k, v in recomputed.items()))
            unknowns.append("FDV denominator used by provider")
    if prov_mc and prov_fdv and abs(prov_mc - prov_fdv) / prov_fdv > 0.02:
        facts.append(f"market cap ${prov_mc:,.0f} vs FDV ${prov_fdv:,.0f}: {1 - prov_mc/prov_fdv:.1%} of supply treated as non-circulating by provider")
    elif prov_mc and prov_fdv:
        facts.append("provider treats circulating = total supply (mcap = FDV)")
    # burned / locked / vesting from holders
    burned_pct = locked_pct = vesting_pct = None
    if holders_out:
        cls = holders_out.get("classified") or []
        burned_pct = sum(h["pct"] for h in cls if h.get("classification") == "BURN" and h.get("pct")) or 0.0
        locked_pct = sum(h["pct"] for h in cls if h.get("classification") in ("VESTING", "LOCKER") and h.get("pct")) or 0.0
        pool_pct = sum(h["pct"] for h in cls if h.get("classification") == "POOL" and h.get("pct")) or 0.0
        if burned_pct:
            facts.append(f"burn addresses hold {burned_pct:.2f}% of supply")
        if locked_pct:
            facts.append(f"vesting/locker contracts hold {locked_pct:.2f}% of supply (top holders only)")
        facts.append(f"liquidity pools hold {pool_pct:.2f}% of supply (top holders only)")
    # issuance risk
    mint_auth = a.get("mint_authority_rpc") if "mint_authority_rpc" in a else a.get("mint_authority")
    src_name = "rpc" if "mint_authority_rpc" in a else "rugcheck" if "mint_authority" in a else None
    if mint_auth:
        facts.append(f"MINT AUTHORITY ACTIVE: {mint_auth}; supply can be increased at will")
        inferences.append("uncontrolled future issuance is possible; FDV is not a ceiling")
    elif src_name:
        facts.append(f"mint authority revoked ({src_name})")
    elif a.get("mint_authority_disabled_jup") is True:
        facts.append("mint authority revoked (jupiter audit; rugcheck/rpc not available)")
    else:
        unknowns.append("mint authority not observed")
    # overhang estimate: supply not in pools/burn that sits with top holders, dev, insiders
    overhang = {}
    if holders_out:
        overhang["top_economic_pct"] = holders_out.get("adjusted_top10_pct")
        overhang["insider_pct"] = holders_out.get("insider_pct")
        overhang["dev_pct"] = holders_out.get("dev_holding_pct")
        parts = [v for v in (overhang.get("top_economic_pct"), overhang.get("insider_pct")) if v]
        if parts and price and (circ or onchain_supply):
            sup = circ or onchain_supply
            overhang["sellable_usd_top_economic"] = (overhang.get("top_economic_pct") or 0) / 100 * sup * price
            facts.append(f"top-10 economic holders control about ${overhang['sellable_usd_top_economic']:,.0f} of inventory at current price")
    heur.append("economically relevant overhang = inventory held by actors likely to sell into strength (early wallets, insiders, unlocked team supply), not total supply")
    if not holders_out:
        unknowns.append("holder classification not run; overhang by holder class unavailable")
    return {"onchain_supply": onchain_supply, "circ_supply": circ, "total_supply": total, "recomputed": recomputed,
            "provider_fdv_denominator": denom, "burned_pct": burned_pct, "locked_pct": locked_pct, "mint_authority_active": bool(mint_auth),
            "overhang": overhang, "facts": facts, "inferences": inferences, "heuristics": heur, "unknowns": unknowns}
