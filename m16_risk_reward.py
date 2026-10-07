"""m16: risk / reward and scenario analysis per candidate entry.

For each entry from m15: distance to invalidation, supply zones above, four scenarios
(BEAR / BASE / BULL / EXTREME) with target, return %, R multiple and what must happen, R:R to
base and bull, and an expected-value RANGE in R from configurable probability bands.

R is rounded to 1 decimal. Probabilities are bands, not point estimates: we do not know the
distribution and the output says so.
"""
from __future__ import annotations

from . import m13_price_structure as m13
from . import m15_entry_invalidation as m15
from ._common import base_result, fmt_price, r1, safe_get, to_float

DEFAULT_BANDS = {"BEAR": (0.45, 0.65), "BASE": (0.20, 0.35), "BULL": (0.08, 0.20), "EXTREME": (0.02, 0.08)}


def _normalize(p: dict) -> dict:
    s = sum(p.values())
    return {k: v / s for k, v in p.items()} if s > 0 else p


def _ev(r: dict, probs: dict) -> float:
    return sum(probs[k] * r[k] for k in r if k in probs)


def _ev_range(r_by_scn: dict, bands: dict) -> tuple[float, float]:
    """EV low: bear at its upper band, upside scenarios at their lower bands, normalized.
    EV high: the reverse. Normalization keeps the band interpretation honest."""
    low = {k: (bands[k][1] if k == "BEAR" else bands[k][0]) for k in bands}
    high = {k: (bands[k][0] if k == "BEAR" else bands[k][1]) for k in bands}
    return _ev(r_by_scn, _normalize(low)), _ev(r_by_scn, _normalize(high))


def analyze(bundle: dict, entries: list | None = None, structure: dict | None = None,
            bands: dict | None = None, extreme_multiplier: float = 2.0, **kwargs) -> dict:
    out = base_result()
    out.update({"per_entry": [], "bands": None})
    bundle = bundle if isinstance(bundle, dict) else {}
    b = dict(DEFAULT_BANDS)
    if isinstance(bands, dict):
        for k, v in bands.items():
            if isinstance(v, (list, tuple)) and len(v) == 2:
                b[str(k).upper()] = (float(v[0]), float(v[1]))
    out["bands"] = {k: list(v) for k, v in b.items()}
    if not isinstance(structure, dict):
        structure = m13.analyze(bundle)
        out["heuristics"].append("structure= not supplied; ran m13 internally")
    if entries is None:
        entries = m15.analyze(bundle, structure=structure).get("entries", [])
        out["heuristics"].append("entries= not supplied; ran m15 internally")
    if isinstance(entries, dict) and "entries" in entries:
        entries = entries["entries"]
    if not entries:
        out["unknowns"].append("no candidate entries; nothing to evaluate")
        return out
    zones = [z for z in (structure.get("zones") or []) if isinstance(z, dict) and z.get("low") and z.get("high")]
    ath = to_float(structure.get("ath"))
    vol24 = safe_get(structure, "volatility", "headline", "per_24h_pct")

    for e in entries:
        if not isinstance(e, dict):
            continue
        zl, zh = to_float(e.get("zone_low")), to_float(e.get("zone_high"))
        inv = to_float(e.get("invalidation_level"))
        if zl is None or zh is None or inv is None:
            out["unknowns"].append(f"{e.get('style')}: entry zone or invalidation missing; skipped")
            continue
        entry_px = (zl + zh) / 2.0
        if entry_px <= inv:
            out["unknowns"].append(f"{e.get('style')}: invalidation {fmt_price(inv)} is not below entry {fmt_price(entry_px)}; skipped")
            continue
        dist_pct = (entry_px - inv) / entry_px * 100.0
        # R is measured on the STOP (where the loss is actually taken), falling back to the thesis level
        stop = to_float(e.get("stop_location"))
        if stop is not None and stop < entry_px:
            risk_abs = entry_px - stop
            r_basis = "stop_location"
        else:
            risk_abs = entry_px - inv
            r_basis = "invalidation_level"
        atr_pct_tf = safe_get(structure, "per_timeframe", e.get("tf") or "hour1", "volatility", "atr_pct") or safe_get(structure, "volatility", "headline", "atr_pct")
        noise_flag = None
        if atr_pct_tf and dist_pct < atr_pct_tf:
            noise_flag = f"invalidation is {dist_pct:.2f}% from entry, inside one ATR ({atr_pct_tf:.2f}%): a close through it can be noise; R multiples are large because the denominator is small, treat them with suspicion"
            out["heuristics"].append(f"{e.get('style')}: {noise_flag}")
        # supply zones above the entry zone, nearest first
        supply = sorted([z for z in zones if z["low"] > zh * 1.001], key=lambda z: z["low"])
        # merge near-duplicate zones across timeframes (within 3%)
        merged = []
        for z in supply:
            if merged and abs(z["low"] - merged[-1]["low"]) / merged[-1]["low"] < 0.03:
                merged[-1] = dict(merged[-1], high=max(merged[-1]["high"], z["high"]), touches=merged[-1].get("touches", 0) + z.get("touches", 0),
                                  why=merged[-1].get("why", "") + " | " + z.get("why", ""), tf=f"{merged[-1].get('tf')}+{z.get('tf')}")
            else:
                merged.append(dict(z))
        supply = merged
        notes = []
        scen = {}

        # BEAR
        scen["BEAR"] = {"target": entry_px - risk_abs, "return_pct": -risk_abs / entry_px * 100.0, "r": -1.0,
                        "what_must_happen": (e.get("invalidation_text") or f"close below {fmt_price(inv)}") + (f"; loss taken at the stop {fmt_price(stop)}" if r_basis == "stop_location" else ""),
                        "basis": f"loss taken at {r_basis.replace('_', ' ')}"}
        # BASE
        if supply:
            t = supply[0]["low"]
            scen["BASE"] = {"target": t, "basis": f"low of first supply zone {fmt_price(supply[0]['low'])}-{fmt_price(supply[0]['high'])} ({supply[0].get('tf')})",
                            "what_must_happen": f"price reaches the first resistance above entry: {supply[0].get('why', '')}; sellers who were trapped there get their exit, so expect a reaction"}
        elif ath and ath > entry_px * 1.02:
            t = ath
            scen["BASE"] = {"target": t, "basis": f"in-data ATH {fmt_price(ath)} (no swing-based supply zone above entry)",
                            "what_must_happen": "price returns to the prior high; no intermediate resistance identified in the candles"}
            notes.append("no supply zone between entry and ATH: targets rest on the ATH alone")
        else:
            # price discovery: no reference above; use a volatility-based measured move, flagged heuristic
            mv = (vol24 or 20.0) / 100.0 * 2.0
            t = entry_px * (1 + mv)
            scen["BASE"] = {"target": t, "basis": f"no resistance above (price discovery); heuristic target = entry + 2 x 24h realized vol ({mv*100:.0f}%)",
                            "what_must_happen": "price discovery continues for roughly two average days; there is no structural level to anchor this"}
            notes.append("BASE target is a volatility heuristic, not a structural level")
            out["heuristics"].append(f"{e.get('style')}: no supply above entry; BASE target derived from 24h realized volatility")
        # BULL
        if len(supply) >= 2:
            z2 = supply[1]
            scen["BULL"] = {"target": z2["low"], "basis": f"second supply zone {fmt_price(z2['low'])}-{fmt_price(z2['high'])} ({z2.get('tf')})",
                            "what_must_happen": f"first supply zone is absorbed (closes above {fmt_price(supply[0]['high'])}) and price travels to the next zone: {z2.get('why', '')}"}
        elif ath and ath > scen["BASE"]["target"] * 1.02:
            scen["BULL"] = {"target": ath, "basis": f"in-data ATH {fmt_price(ath)}",
                            "what_must_happen": "all intermediate supply is absorbed and price retests the prior high"}
        else:
            base_t = scen["BASE"]["target"]
            scen["BULL"] = {"target": entry_px + 2 * (base_t - entry_px), "basis": "2x the base move (no further structural reference)",
                            "what_must_happen": "price clears the base target and extends an equal distance; no structural anchor"}
            notes.append("BULL target is a projection, not a structural level")
        # EXTREME
        bull_t = scen["BULL"]["target"]
        ext_from_bull = entry_px + extreme_multiplier * (bull_t - entry_px)
        # The tail is capped: an ATH 10x away is not a planning target. Extreme = min(ATH, 3x the bull move), never more than +300% from entry.
        cap = entry_px * 4.0
        if ath and ath > bull_t * 1.02:
            ext = min(ath, max(ext_from_bull, entry_px + 3 * (bull_t - entry_px)), cap)
            basis = f"min(in-data ATH {fmt_price(ath)}, 3x bull move, +300%)"
            if ath > cap:
                notes.append(f"in-data ATH {fmt_price(ath)} is {(ath/entry_px - 1)*100:.0f}% above entry and was not used as the extreme target (capped at +300%)")
        else:
            ext = min(ext_from_bull, cap)
            basis = f"{extreme_multiplier:g}x the bull move (price discovery multiple), capped at +300%"
        scen["EXTREME"] = {"target": ext, "basis": basis,
                           "what_must_happen": "a price-discovery leg: new attention inflow, no supply overhead; this is the tail, not the plan"}
        # returns and R
        for k, s in scen.items():
            if k != "BEAR":
                s["return_pct"] = (s["target"] - entry_px) / entry_px * 100.0
                s["r"] = (s["target"] - entry_px) / risk_abs
            s["return_pct"] = round(s["return_pct"], 1)
            s["r"] = r1(s["r"])
            s["target"] = float(s["target"])
        r_by = {k: s["r"] for k, s in scen.items()}
        ev_lo, ev_hi = _ev_range(r_by, b)
        rr_base, rr_bull = scen["BASE"]["r"], scen["BULL"]["r"]
        verdict = ("R:R to base below 1: the first resistance is closer than the invalidation; the trade needs the bull case to pay" if rr_base is not None and rr_base < 1.0
                   else "acceptable R:R to the first target" if rr_base is not None and rr_base < 2.0 else "R:R to the first target is favourable")
        rec = {
            "style": e.get("style"), "entry_price": entry_px, "zone_low": zl, "zone_high": zh,
            "invalidation_level": inv, "distance_to_invalidation_pct": round(dist_pct, 2),
            "stop_location": e.get("stop_location"),
            "distance_to_stop_pct": round((entry_px - stop) / entry_px * 100.0, 2) if stop is not None and stop < entry_px else None,
            "r_basis": r_basis, "r_unit_pct": round(risk_abs / entry_px * 100.0, 2), "noise_flag": noise_flag,
            "first_supply_zone": ({k: supply[0].get(k) for k in ("tf", "low", "high", "touches", "strength", "why")} if supply else None),
            "subsequent_zones": [{k: z.get(k) for k in ("tf", "low", "high", "touches", "strength", "why")} for z in supply[1:5]],
            "scenarios": scen, "rr_base": rr_base, "rr_bull": rr_bull,
            "ev_r_low": r1(ev_lo), "ev_r_high": r1(ev_hi),
            "ev_positive_across_band": bool(ev_lo > 0),
            "verdict": verdict, "notes": notes,
            "uncertainty": ("EV is a RANGE from probability bands (bear {:.0f}-{:.0f}%, base {:.0f}-{:.0f}%, bull {:.0f}-{:.0f}%, extreme {:.0f}-{:.0f}%, normalized); "
                            "the bands are priors, not measured frequencies. Targets assume the zones react; nothing here is a forecast.").format(
                *(x * 100 for pair in (b["BEAR"], b["BASE"], b["BULL"], b["EXTREME"]) for x in pair)),
        }
        out["per_entry"].append(rec)
        out["inferences"].append(f"{rec['style']}: entry {fmt_price(entry_px)}, invalidation {fmt_price(inv)} ({dist_pct:.1f}% away); "
                                 f"base {fmt_price(scen['BASE']['target'])} = {rr_base}R, bull {fmt_price(bull_t)} = {rr_bull}R; EV {rec['ev_r_low']}R to {rec['ev_r_high']}R")
        if not supply:
            out["unknowns"].append(f"{rec['style']}: no supply zones above entry in the candle data")
    out["heuristics"].append("R = (target - entry) / (entry - stop); the stop, not the thesis level, is where the loss is taken; entry price = mid of the entry zone; R rounded to 1 decimal to avoid false precision")
    if vol24 is None:
        out["unknowns"].append("24h realized volatility unavailable; price-discovery targets would fall back to a 20% default")
    return out
