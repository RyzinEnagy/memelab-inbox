"""m15: entry and invalidation construction.

Builds up to four candidate entry styles from m13 (structure) and m14 (breakout) output:
ANTICIPATION, CONFIRMATION, PULLBACK, BREAKOUT_RETEST. An entry is only generated when the
structure supports it; omitted styles are explained in `omitted`.

Invalidation is always expressed as a CLOSE beyond a structural level on a named timeframe, never
as an arbitrary percentage. The stop is a separate level, placed a fraction of ATR beyond the
structural level to allow for wick noise.
"""
from __future__ import annotations

from . import m13_price_structure as m13
from . import m14_breakout_classifier as m14
from ._common import base_result, fmt_price, safe_get, to_float

STYLES = ("ANTICIPATION", "CONFIRMATION", "PULLBACK", "BREAKOUT_RETEST")


def _atr_abs(structure: dict, tf: str, price: float) -> float | None:
    a = safe_get(structure, "per_timeframe", tf, "volatility", "atr_pct")
    if a is None:
        a = safe_get(structure, "volatility", "headline", "atr_pct")
    return price * a / 100.0 if (a and price) else None


def _stop_below(level: float, atr_abs: float | None, stop_atr_frac: float, fallback_frac: float = 0.01) -> float:
    pad = atr_abs * stop_atr_frac if atr_abs else level * fallback_frac
    return level - pad


def _tf_label(tf: str | None) -> str:
    return {"day1": "daily", "hour1": "hourly", "minute15": "15-minute"}.get(tf or "", tf or "chart")


def _a_tf(tf: str | None) -> str:
    """'an hourly' / 'a daily' / 'a 15-minute' for use before 'close' or 'candle'."""
    lbl = _tf_label(tf)
    return ("an " if lbl == "hourly" else "a ") + lbl


def _exec_placeholder(zone_low: float, zone_high: float) -> str:
    return (f"to be filled by the depth module: check BUY impact for the intended size at {fmt_price(zone_low)}-{fmt_price(zone_high)}, "
            f"whether the quote route is single-pool, the slippage needed to fill, and the SELL impact at the same size (round-trip cost)")


def _structure_evidence(structure: dict, zone: dict | None) -> list[str]:
    ev = []
    if structure.get("structure"):
        ev.append(f"m13 combined structure {structure['structure']}: {structure.get('structure_summary', '')}".strip())
    if zone:
        ev.append(f"zone {fmt_price(zone['low'])}-{fmt_price(zone['high'])} ({zone.get('tf')}): {zone.get('why', '')}")
    return ev


def analyze(bundle: dict, structure: dict | None = None, breakout: dict | None = None,
            stop_atr_frac: float = 0.5, max_anticipation_distance_pct: float = 35.0,
            min_zone_touches: int = 2, **kwargs) -> dict:
    out = base_result()
    out.update({"entries": [], "omitted": {}, "price": None})
    bundle = bundle if isinstance(bundle, dict) else {}
    if not isinstance(structure, dict):
        structure = m13.analyze(bundle)
        out["heuristics"].append("structure= not supplied; ran m13 internally")
    if not isinstance(breakout, dict):
        breakout = m14.analyze(bundle, structure=structure)
        out["heuristics"].append("breakout= not supplied; ran m14 internally")
    price = to_float(safe_get(bundle, "market", "price_usd")) or to_float(structure.get("price"))
    out["price"] = price
    if price is None:
        out["unknowns"].append("no current price; entries cannot be constructed")
        for s in STYLES:
            out["omitted"][s] = "no current price"
        return out
    zones = [z for z in (structure.get("zones") or []) if isinstance(z, dict) and z.get("low") and z.get("high")]
    if not zones:
        out["unknowns"].append("no zones from m13; no structural levels to build entries on")
        for s in STYLES:
            out["omitted"][s] = "no structural zones available"
        return out
    overall = structure.get("structure", "TRANSITION")
    cls = breakout.get("classification", "NO_BREAKOUT")
    bz = breakout.get("breakout_zone") if isinstance(breakout.get("breakout_zone"), dict) else None
    btf = breakout.get("tf") or "hour1"
    chase = breakout.get("chase_risk") if isinstance(breakout.get("chase_risk"), dict) else {}
    overextended = bool(breakout.get("overextended"))
    supports = sorted([z for z in zones if z.get("kind") == "SUPPORT"], key=lambda z: -z["high"])
    resistances = sorted([z for z in zones if z.get("kind") == "RESISTANCE"], key=lambda z: z["low"])
    nearest_res = resistances[0] if resistances else None

    # ------------------------------------------------------------------ ANTICIPATION
    style = "ANTICIPATION"
    cand = [z for z in supports if z.get("touches", 0) >= min_zone_touches and (price - z["high"]) / price * 100 <= max_anticipation_distance_pct]
    if overall == "DOWNTREND":
        out["omitted"][style] = "structure is DOWNTREND: bidding support ahead of confirmation is catching a falling knife; wait for a RECLAIM or base"
    elif not cand:
        out["omitted"][style] = (f"no support zone with >= {min_zone_touches} touches within {max_anticipation_distance_pct:.0f}% below price"
                                 if supports else "no support zone below price (price at lows or in discovery with no prior swing lows)")
    else:
        z = max(cand, key=lambda q: (q.get("strength", 0), q["high"]))
        tf = z.get("tf", "hour1")
        atr = _atr_abs(structure, tf, price)
        inv = z["low"]
        stop = _stop_below(inv, atr, stop_atr_frac)
        hl = safe_get(structure, "per_timeframe", tf, "last_higher_low")
        entry = {
            "style": style,
            "condition": f"resting bid inside {fmt_price(z['low'])}-{fmt_price(z['high'])} ({_tf_label(tf)} support, {z.get('touches')} touches) while price is above the zone; fill only if {_a_tf(tf)} candle trades into the zone without closing below {fmt_price(z['low'])}",
            "zone_low": z["low"], "zone_high": z["high"], "tf": tf,
            "thesis": f"the {fmt_price(z['low'])}-{fmt_price(z['high'])} zone holds as support and price rotates back toward {fmt_price(nearest_res['low']) if nearest_res else 'the prior highs'}",
            "why_exists": f"the zone has been defended {z.get('touches')} time(s) ({z.get('why', '')}); buying there puts invalidation {round((z['high']-inv)/z['high']*100, 1)}% below the fill instead of {round((price-inv)/price*100, 1)}% from current price",
            "evidence": _structure_evidence(structure, z) + ([f"last higher low on {_tf_label(tf)} at {fmt_price(hl)}"] if hl else []),
            "invalidation_level": inv,
            "invalidation_text": f"{_a_tf(tf)} close below {fmt_price(inv)} (zone low). That would mean the buyers who defended this level {z.get('touches')} time(s) have been absorbed and the level has flipped; the rotation thesis is wrong.",
            "stop_location": stop,
            "stop_text": f"stop {fmt_price(stop)}: zone low less {stop_atr_frac:g} ATR ({fmt_price(atr) if atr else 'ATR n/a, 1% pad'}) to absorb wick noise; the stop is not the thesis, the close is",
            "expected_execution": _exec_placeholder(z["low"], z["high"]),
            "advantages": ["best price and tightest structural invalidation of the four styles", "limit order: no chase, no slippage into a moving market", "if the zone is not reached nothing is lost"],
            "disadvantages": ["buying before confirmation: the zone may simply break (support tests happen because sellers are present)", "price may never return to the zone and the move leaves without you", "fills in a falling market are adverse-selected: you get filled when sellers are most aggressive"],
            "distance_from_price_pct": round((z["mid"] - price) / price * 100, 2),
        }
        if overall in ("TRANSITION",):
            entry["disadvantages"].append("structure is TRANSITION: no trend to lean on, the zone carries the whole thesis")
        out["entries"].append(entry)

    # ------------------------------------------------------------------ CONFIRMATION
    style = "CONFIRMATION"
    if cls in ("CONFIRMED_BREAKOUT", "RECLAIM") and bz and bz.get("low") and bz["low"] < price:
        if overextended:
            out["omitted"][style] = (f"breakout confirmed but price is {chase.get('distance_pct')}% / {chase.get('distance_atr')} ATR above the breakout zone low: OVEREXTENDED; "
                                     f"a confirmation entry here would carry an invalidation too far away. Wait for BREAKOUT_RETEST or PULLBACK.")
        else:
            atr = _atr_abs(structure, btf, price)
            inv = bz["low"]
            stop = _stop_below(inv, atr, stop_atr_frac)
            entry = {
                "style": style,
                "condition": f"buy at market/near {fmt_price(price)} now that {breakout.get('params', {}).get('accept_n', 3)} {_tf_label(btf)} closes have held above {fmt_price(bz['high'])} (zone high); do not buy if price has moved more than {chase.get('thresholds', {}).get('pct', 15)}% above {fmt_price(bz['low'])} by the time of execution",
                "zone_low": bz["high"], "zone_high": price, "tf": btf,
                "thesis": f"the break of {fmt_price(bz['low'])}-{fmt_price(bz['high'])} is accepted and the zone now acts as support; the path to {fmt_price(nearest_res['low']) if nearest_res else 'price discovery'} is open",
                "why_exists": f"m14 classified {cls}: " + "; ".join(breakout.get("evidence", [])[:3]),
                "evidence": _structure_evidence(structure, bz) + list(breakout.get("evidence", [])),
                "invalidation_level": inv,
                "invalidation_text": f"{_a_tf(btf)} close back below {fmt_price(inv)} (breakout zone low). That makes the breakout a FAILED_BREAKOUT: acceptance above the zone was false and the sellers who capped it are still there.",
                "stop_location": stop,
                "stop_text": f"stop {fmt_price(stop)}: breakout zone low less {stop_atr_frac:g} ATR to allow a wick through the zone without a close",
                "expected_execution": _exec_placeholder(bz["high"], price),
                "advantages": ["confirmation exists: closes, acceptance and (if present) volume expansion are observed, not hoped for", "momentum is in your favour at entry", "invalidation is unambiguous: the broken zone"],
                "disadvantages": [f"worst price of the four styles: {round((price - bz['low'])/bz['low']*100, 1)}% above the invalidation level", "late entries are where most of the chasing crowd is; a shakeout back into the zone is common", "if volume expansion was weak the breakout may be a liquidity grab"],
                "distance_from_price_pct": 0.0,
            }
            out["entries"].append(entry)
    elif cls == "EARLY_BREAKOUT_ATTEMPT":
        out["omitted"][style] = "breakout attempt not yet confirmed (insufficient closes above the zone and/or no volume expansion); confirmation entry waits for acceptance"
    elif cls == "FAILED_BREAKOUT":
        out["omitted"][style] = "most recent breakout FAILED (closed back below the zone); no confirmation to buy"
    elif cls == "BREAKOUT_RETEST":
        out["omitted"][style] = "breakout already retested; the retest entry is the better-priced version of this idea"
    else:
        out["omitted"][style] = "no confirmed breakout above a resistance zone"

    # ------------------------------------------------------------------ PULLBACK
    style = "PULLBACK"
    if overall not in ("UPTREND", "PRICE_DISCOVERY"):
        out["omitted"][style] = f"structure is {overall}: a pullback entry needs a higher-timeframe uptrend to lean on"
    else:
        # prefer the nearest support that is a prior breakout zone (polarity flip) or holds the last higher low
        cand = None
        for z in supports:
            if z.get("touches", 0) >= 1:
                cand = z
                break
        hl_tf = None
        hl = None
        for tf in ("hour1", "day1", "minute15"):
            v = safe_get(structure, "per_timeframe", tf, "last_higher_low")
            if v and v < price:
                hl, hl_tf = v, tf
                break
        if cand is None and hl is None:
            out["omitted"][style] = "uptrend but no support zone or higher low below price to pull back into (vertical move)"
        else:
            if cand is not None:
                tf = cand.get("tf", "hour1")
                zl, zh = cand["low"], cand["high"]
                if hl and hl < zl:
                    inv = hl
                    inv_desc = f"last higher low {fmt_price(hl)} on the {_tf_label(hl_tf)}"
                else:
                    inv = zl
                    inv_desc = f"zone low {fmt_price(zl)}"
            else:
                tf = hl_tf
                atr0 = _atr_abs(structure, tf, price) or price * 0.02
                zl, zh = hl, hl + atr0
                inv = hl
                inv_desc = f"last higher low {fmt_price(hl)} on the {_tf_label(hl_tf)}"
            atr = _atr_abs(structure, tf, price)
            stop = _stop_below(inv, atr, stop_atr_frac)
            entry = {
                "style": style,
                "condition": f"price pulls back into {fmt_price(zl)}-{fmt_price(zh)} ({_tf_label(tf)}) and prints {_a_tf(tf)} close back above {fmt_price(zh)}, or holds the zone on declining volume for 2+ candles; buy on that close, not on the first touch",
                "zone_low": zl, "zone_high": zh, "tf": tf,
                "thesis": f"the {overall.lower().replace('_', ' ')} continues; the pullback is a higher low above {inv_desc}",
                "why_exists": "trends advance in legs; buying the pullback into prior support keeps invalidation close while the higher-timeframe trend does the work" + (f". Zone: {cand.get('why', '')}" if cand else ""),
                "evidence": _structure_evidence(structure, cand) + ([f"last higher low {fmt_price(hl)} ({_tf_label(hl_tf)})"] if hl else []),
                "invalidation_level": inv,
                "invalidation_text": f"{_a_tf(tf)} close below {inv_desc}. A lower low ends the HH/HL sequence; the uptrend thesis is wrong regardless of what happens next.",
                "stop_location": stop,
                "stop_text": f"stop {fmt_price(stop)}: {stop_atr_frac:g} ATR below the structural level for wick noise",
                "expected_execution": _exec_placeholder(zl, zh),
                "advantages": ["trend alignment on the higher timeframe", "better price than confirmation with a defined structural level below", "waiting for the close back above the zone filters the pullbacks that keep falling"],
                "disadvantages": ["strong trends may not pull back to the zone at all", "the pullback can be the first leg of a reversal; only the close below the higher low tells you, after the fact", "requires monitoring: the condition is a close, so execution lags the touch"],
                "distance_from_price_pct": round(((zl + zh) / 2 - price) / price * 100, 2),
            }
            out["entries"].append(entry)

    # ------------------------------------------------------------------ BREAKOUT_RETEST
    style = "BREAKOUT_RETEST"
    if cls == "BREAKOUT_RETEST" and bz:
        atr = _atr_abs(structure, btf, price)
        inv = bz["low"]
        stop = _stop_below(inv, atr, stop_atr_frac)
        entry = {
            "style": style,
            "condition": f"price has retested {fmt_price(bz['low'])}-{fmt_price(bz['high'])} and closed back above {fmt_price(bz['high'])} on the {_tf_label(btf)}; buy at/near the zone high on that close (if price has already left the zone by more than 1 ATR, treat as missed)",
            "zone_low": bz["low"], "zone_high": bz["high"], "tf": btf,
            "thesis": f"the broken resistance has flipped to support and held on its first test; the breakout is validated",
            "why_exists": "m14: " + "; ".join(breakout.get("evidence", [])[:4]),
            "evidence": _structure_evidence(structure, bz) + list(breakout.get("evidence", [])),
            "invalidation_level": inv,
            "invalidation_text": f"{_a_tf(btf)} close below {fmt_price(inv)} (zone low). The retest failed: the zone did not hold as support, which is the whole thesis.",
            "stop_location": stop,
            "stop_text": f"stop {fmt_price(stop)}: zone low less {stop_atr_frac:g} ATR",
            "expected_execution": _exec_placeholder(bz["low"], bz["high"]),
            "advantages": ["highest-information entry: breakout, acceptance and a successful retest have all been observed", "tight invalidation relative to the confirmation entry", "the chasing crowd has been shaken out on the retest"],
            "disadvantages": ["not every breakout retests; this setup is often unavailable", "a second retest after a successful first one has a worse hit rate", "the retest can be a slow bleed rather than a sharp dip, making the 'held' judgment subjective"],
            "distance_from_price_pct": round((bz["high"] - price) / price * 100, 2),
        }
        out["entries"].append(entry)
    elif cls in ("CONFIRMED_BREAKOUT", "RECLAIM") and bz:
        atr = _atr_abs(structure, btf, price)
        inv = bz["low"]
        stop = _stop_below(inv, atr, stop_atr_frac)
        entry = {
            "style": style,
            "condition": f"WAIT: breakout above {fmt_price(bz['high'])} is confirmed but has not been retested. Entry condition = price returns to {fmt_price(bz['low'])}-{fmt_price(bz['high'])} and prints {_a_tf(btf)} close at or above {fmt_price(bz['high'])}. Not actionable until that happens.",
            "zone_low": bz["low"], "zone_high": bz["high"], "tf": btf,
            "thesis": "the broken resistance flips to support on its first retest and the breakout continues",
            "why_exists": "a confirmed breakout without a retest; the retest, if it comes, is the lower-risk version of the confirmation entry" + ("; the confirmation entry was omitted as overextended, so this is the remaining way in" if overextended else ""),
            "evidence": _structure_evidence(structure, bz) + list(breakout.get("evidence", [])),
            "invalidation_level": inv,
            "invalidation_text": f"{_a_tf(btf)} close below {fmt_price(inv)} (zone low): the retest failed and the breakout is a FAILED_BREAKOUT",
            "stop_location": stop,
            "stop_text": f"stop {fmt_price(stop)}: zone low less {stop_atr_frac:g} ATR",
            "expected_execution": _exec_placeholder(bz["low"], bz["high"]),
            "advantages": ["tight invalidation at a level that has already been tested from both sides", "lets the confirmation crowd get shaken out before you buy"],
            "disadvantages": ["conditional: the retest may never come", "if the retest arrives on heavy volume it may be a failure in progress rather than a hold"],
            "distance_from_price_pct": round((bz["high"] - price) / price * 100, 2),
            "pending": True,
        }
        out["entries"].append(entry)
    elif cls == "FAILED_BREAKOUT":
        out["omitted"][style] = "most recent breakout failed; the zone is resistance again, not a retest candidate"
    else:
        out["omitted"][style] = "no confirmed breakout to retest"

    for e in out["entries"]:
        e["invalidation_distance_pct"] = round((((e["zone_low"] + e["zone_high"]) / 2) - e["invalidation_level"]) / ((e["zone_low"] + e["zone_high"]) / 2) * 100, 2) if e.get("zone_low") and e.get("zone_high") else None
        out["inferences"].append(f"{e['style']}: {e['condition']}")
    for s, r in out["omitted"].items():
        out["inferences"].append(f"{s} omitted: {r}")
    if not out["entries"]:
        out["unknowns"].append("no entry style is supported by the current structure")
    out["heuristics"].append(f"invalidation is a close beyond a structural level on the entry's timeframe; stop = level less {stop_atr_frac:g} ATR; no fixed-percentage stops are used")
    return out
