"""m17: position sizing under a risk constraint and a liquidity constraint.

RISK constraint:       size = max_loss_usd / (distance to invalidation as a fraction)
LIQUIDITY constraint:  largest BUY whose impact <= max_entry_impact_pct, and largest SELL whose
                       impact <= max_exit_impact_pct, applied to the FUTURE displayed value at each
                       exit multiple (a $5k position at 10x is a $50k sell, so the allowed initial
                       size for the 10x multiple is max exitable sell size / 10).
Impact is interpolated log-linearly between tested quote sizes and never extrapolated above the
largest tested size (unobserved depth is not claimed).

If account inputs are None we do not invent a dollar position: only the liquidity-implied
maximum is returned and needs_account_inputs is True.

Haircuts (recorded individually): 24h realized vol above threshold (-25%), transfer fee present,
route fragmentation (> 2 pools).
"""
from __future__ import annotations

import math

from . import m13_price_structure as m13
from ._common import (
    base_result,
    max_size_for_impact,
    parse_quote_side,
    quote_unit_note,
    route_pool_count,
    safe_get,
    to_float,
)


def _risk_constraint(entry: dict, max_loss_usd: float | None) -> tuple[float | None, dict]:
    zl, zh = to_float(entry.get("zone_low")), to_float(entry.get("zone_high"))
    inv = to_float(entry.get("invalidation_level"))
    stop = to_float(entry.get("stop_location"))
    info = {"distance_to_invalidation_pct": None, "distance_to_stop_pct": None, "sizing_level": None}
    if zl is None or zh is None:
        return None, info
    entry_px = (zl + zh) / 2.0
    # size on the STOP (where the loss is actually taken) if present, else on the invalidation level
    level = stop if (stop is not None and stop < entry_px) else inv
    if level is None or level >= entry_px:
        return None, info
    frac = (entry_px - level) / entry_px
    info["distance_to_invalidation_pct"] = round((entry_px - inv) / entry_px * 100.0, 2) if inv is not None and inv < entry_px else None
    info["distance_to_stop_pct"] = round((entry_px - stop) / entry_px * 100.0, 2) if stop is not None and stop < entry_px else None
    info["sizing_level"] = "stop_location" if level == stop else "invalidation_level"
    info["loss_fraction"] = round(frac, 4)
    if max_loss_usd is None:
        return None, info
    return max_loss_usd / frac, info


def _liquidity_constraint(quotes: dict, max_entry_impact_pct: float, max_exit_impact_pct: float,
                          exit_multiples: tuple, out: dict) -> dict:
    buy_pts = parse_quote_side(quotes.get("BUY"))
    sell_pts = parse_quote_side(quotes.get("SELL"))
    lc = {"entry_max": None, "exit_max_now": None, "exit_max_by_multiple": {}, "flags": {},
          "tested_buy_sizes": [p[0] for p in buy_pts], "tested_sell_sizes": [p[0] for p in sell_pts]}
    for side, pts in (("BUY", buy_pts), ("SELL", sell_pts)):
        note = quote_unit_note(quotes.get(side))
        if note:
            out["heuristics"].append(f"{side} {note}")
    if buy_pts:
        v, flag = max_size_for_impact(buy_pts, max_entry_impact_pct)
        lc["entry_max"], lc["flags"]["entry"] = v, flag
        out["facts"].append(f"BUY quotes at {len(buy_pts)} sizes (${buy_pts[0][0]:,.0f} to ${buy_pts[-1][0]:,.0f}); impact at largest tested {buy_pts[-1][1]:.2f}%" if math.isfinite(buy_pts[-1][1]) else f"BUY quotes at {len(buy_pts)} sizes; largest tested ${buy_pts[-1][0]:,.0f} failed to route")
        if flag == "capped_at_largest_tested":
            out["unknowns"].append(f"BUY impact at the largest tested size (${buy_pts[-1][0]:,.0f}) is still under {max_entry_impact_pct}%: true entry depth is at least this but untested beyond")
    else:
        out["unknowns"].append("no BUY quotes; entry depth unknown")
    if sell_pts:
        v, flag = max_size_for_impact(sell_pts, max_exit_impact_pct)
        lc["exit_max_now"], lc["flags"]["exit"] = v, flag
        out["facts"].append(f"SELL quotes at {len(sell_pts)} sizes (${sell_pts[0][0]:,.0f} to ${sell_pts[-1][0]:,.0f}); impact at largest tested {sell_pts[-1][1]:.2f}%" if math.isfinite(sell_pts[-1][1]) else f"SELL quotes at {len(sell_pts)} sizes; largest tested ${sell_pts[-1][0]:,.0f} failed to route")
        if flag == "capped_at_largest_tested":
            out["unknowns"].append(f"SELL impact at the largest tested size (${sell_pts[-1][0]:,.0f}) is still under {max_exit_impact_pct}%: exit depth beyond that is untested, so multiples are capped on tested depth")
        for m in exit_multiples:
            m = float(m)
            if m > 0 and v is not None:
                lc["exit_max_by_multiple"][int(m) if m.is_integer() else m] = v / m
    else:
        out["unknowns"].append("no SELL quotes; exit depth unknown (the constraint that matters most for a memecoin)")
    return lc


def analyze(bundle: dict, entries: list | None = None, account_size: float | None = None,
            max_loss_usd: float | None = None, max_loss_pct: float | None = None,
            max_entry_impact_pct: float = 1.5, max_exit_impact_pct: float = 3.0,
            exit_multiples: tuple = (2, 5, 10), sizing_multiple: float | None = None,
            vol_haircut_threshold_pct: float = 25.0, structure: dict | None = None, **kwargs) -> dict:
    out = base_result()
    out.update({"risk_constraint": None, "liquidity_constraint": None, "allowed_size_usd": None,
                "binding_constraint": None, "haircuts": [], "needs_account_inputs": False, "per_entry": [],
                "params": {"max_entry_impact_pct": max_entry_impact_pct, "max_exit_impact_pct": max_exit_impact_pct,
                           "exit_multiples": list(exit_multiples), "vol_haircut_threshold_pct": vol_haircut_threshold_pct}})
    bundle = bundle if isinstance(bundle, dict) else {}
    quotes = bundle.get("quotes") if isinstance(bundle.get("quotes"), dict) else {}
    if isinstance(entries, dict) and "entries" in entries:
        entries = entries["entries"]
    entries = [e for e in (entries or []) if isinstance(e, dict)]

    # account inputs
    account_size = to_float(account_size)
    max_loss_usd = to_float(max_loss_usd)
    max_loss_pct = to_float(max_loss_pct)
    if max_loss_usd is None and account_size is not None and max_loss_pct is not None:
        max_loss_usd = account_size * max_loss_pct / 100.0
        out["facts"].append(f"max loss = {max_loss_pct:g}% of ${account_size:,.0f} = ${max_loss_usd:,.0f}")
    if max_loss_usd is None:
        out["needs_account_inputs"] = True
        out["unknowns"].append("account inputs missing (account_size + max_loss_pct, or max_loss_usd); only the liquidity-implied maximum is reported, no dollar position is proposed")

    # liquidity
    lc = _liquidity_constraint(quotes, max_entry_impact_pct, max_exit_impact_pct, exit_multiples, out)
    out["liquidity_constraint"] = lc
    # choose the multiple the liquidity constraint is applied at: default = the largest exit multiple
    # (plan for the position you hope to have), overridable
    mults = sorted(lc["exit_max_by_multiple"].keys(), key=float)
    chosen_mult = None
    if mults:
        if sizing_multiple is not None:
            chosen_mult = min(mults, key=lambda m: abs(float(m) - float(sizing_multiple)))
        else:
            chosen_mult = mults[-1]
    liq_cap_candidates = []
    if lc["entry_max"] is not None:
        liq_cap_candidates.append(("entry impact", lc["entry_max"]))
    if chosen_mult is not None:
        liq_cap_candidates.append((f"exit impact at {chosen_mult}x displayed value", lc["exit_max_by_multiple"][chosen_mult]))
    elif lc["exit_max_now"] is not None:
        liq_cap_candidates.append(("exit impact at current value", lc["exit_max_now"]))
    liq_cap = min(liq_cap_candidates, key=lambda t: t[1]) if liq_cap_candidates else None
    lc["binding_side"] = liq_cap[0] if liq_cap else None
    lc["liquidity_max_usd"] = liq_cap[1] if liq_cap else None
    lc["applied_multiple"] = chosen_mult
    if liq_cap:
        out["inferences"].append(f"liquidity-implied maximum ${liq_cap[1]:,.0f} (binding side: {liq_cap[0]})")
        if chosen_mult is not None and lc["exit_max_now"] is not None:
            out["inferences"].append(f"exit depth now ${lc['exit_max_now']:,.0f} at <= {max_exit_impact_pct}% impact; "
                                     + ", ".join(f"{m}x -> ${v:,.0f} initial" for m, v in sorted(lc['exit_max_by_multiple'].items(), key=lambda t: float(t[0]))))
    else:
        out["unknowns"].append("no usable quotes; liquidity constraint cannot be computed")

    # haircuts (multiplicative, applied to the final allowed size)
    haircuts = []
    if not isinstance(structure, dict):
        structure = m13.analyze(bundle) if bundle.get("ohlcv") else {}
    vol24 = safe_get(structure, "volatility", "headline", "per_24h_pct")
    if vol24 is not None:
        if vol24 > vol_haircut_threshold_pct:
            haircuts.append({"name": "volatility", "factor": 0.75, "reason": f"24h realized vol {vol24:.1f}% > {vol_haircut_threshold_pct:g}%: a structural stop is more likely to be hit by noise, so risk per unit is higher than the distance implies"})
    else:
        out["unknowns"].append("24h realized volatility unavailable; volatility haircut not evaluated")
    fee_bps = to_float(safe_get(bundle, "authorities", "transfer_fee_bps"))
    if fee_bps:
        f = max(0.5, 1.0 - min(fee_bps, 1000) / 10000.0 * 5)  # 1% fee -> 0.95 ... scaled, floor 0.5
        haircuts.append({"name": "transfer_fee", "factor": round(f, 3), "reason": f"token has a {fee_bps/100:.2f}% transfer fee: every round trip and every exit leg costs more than the quote shows"})
    elif safe_get(bundle, "authorities") is None:
        out["unknowns"].append("authorities block missing; transfer fee presence unknown")
    pools = None
    for side in ("SELL", "BUY"):
        n = route_pool_count(quotes.get(side))
        pools = n if (n is not None and (pools is None or n > pools)) else pools
    if pools is None and isinstance(bundle.get("pools"), list):
        pools = len(bundle["pools"]) if bundle["pools"] else None
    if pools is not None and pools > 2:
        haircuts.append({"name": "route_fragmentation", "factor": 0.8, "reason": f"quote route touches {pools} pools: depth is stitched across venues and can disappear independently"})
    elif pools is None:
        out["unknowns"].append("route / pool count unknown; fragmentation haircut not evaluated")
    out["haircuts"] = haircuts
    hc_factor = 1.0
    for h in haircuts:
        hc_factor *= h["factor"]

    # per entry risk constraint
    best = None
    for e in entries:
        risk_size, info = _risk_constraint(e, max_loss_usd)
        rec = {"style": e.get("style"), **info, "risk_constraint_usd": risk_size}
        if info.get("loss_fraction") is None:
            out["unknowns"].append(f"{e.get('style')}: entry zone / invalidation missing; risk constraint not computable")
        cands = []
        if risk_size is not None:
            cands.append(("risk", risk_size))
        if liq_cap:
            cands.append(("liquidity: " + liq_cap[0], liq_cap[1]))
        if cands and not out["needs_account_inputs"]:
            name, val = min(cands, key=lambda t: t[1])
            rec["binding_constraint"] = name
            rec["allowed_size_before_haircuts_usd"] = val
            rec["allowed_size_usd"] = val * hc_factor
            if risk_size is not None and max_loss_usd is not None:
                rec["loss_at_stop_usd"] = round(rec["allowed_size_usd"] * info["loss_fraction"], 2)
        else:
            rec["binding_constraint"] = ("liquidity: " + liq_cap[0]) if liq_cap else None
            rec["allowed_size_before_haircuts_usd"] = liq_cap[1] if liq_cap else None
            rec["allowed_size_usd"] = (liq_cap[1] * hc_factor) if liq_cap else None
            rec["liquidity_implied_max_only"] = True
        out["per_entry"].append(rec)
        if best is None or (rec.get("allowed_size_usd") or 0) > (best.get("allowed_size_usd") or 0):
            best = rec
    if not entries:
        out["unknowns"].append("no entries supplied; risk constraint not computable")
        if liq_cap:
            out["allowed_size_usd"] = liq_cap[1] * hc_factor if out["needs_account_inputs"] else liq_cap[1] * hc_factor
            out["binding_constraint"] = "liquidity: " + liq_cap[0]
    elif best is not None:
        out["risk_constraint"] = {"style": best.get("style"), "max_loss_usd": max_loss_usd,
                                  "distance_to_invalidation_pct": best.get("distance_to_invalidation_pct"),
                                  "distance_to_stop_pct": best.get("distance_to_stop_pct"),
                                  "sizing_level": best.get("sizing_level"), "size_usd": best.get("risk_constraint_usd")}
        out["allowed_size_usd"] = best.get("allowed_size_usd")
        out["binding_constraint"] = best.get("binding_constraint")
    if out["allowed_size_usd"] is not None:
        out["allowed_size_usd"] = round(out["allowed_size_usd"], 2)
        if haircuts:
            out["inferences"].append(f"haircuts applied: " + ", ".join(f"{h['name']} x{h['factor']}" for h in haircuts) + f" (combined x{hc_factor:.3f})")
        if out["needs_account_inputs"]:
            out["inferences"].append(f"liquidity-implied maximum ${out['allowed_size_usd']:,.0f}; this is a ceiling, not a recommendation; supply account inputs for a risk-based size")
        else:
            out["inferences"].append(f"allowed size ${out['allowed_size_usd']:,.0f}, binding constraint: {out['binding_constraint']}")
    if account_size is not None and out["allowed_size_usd"] is not None:
        out["facts"].append(f"allowed size is {out['allowed_size_usd']/account_size*100:.1f}% of account")
    out["heuristics"].append("liquidity constraint uses log-linear interpolation between tested quote sizes and never extrapolates above the largest tested size; exit depth is divided by the exit multiple so the future position can be sold")
    return out
