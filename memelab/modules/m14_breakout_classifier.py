"""m14: breakout classifier.

Classifies the most recent zone interaction as one of
NO_BREAKOUT / EARLY_BREAKOUT_ATTEMPT / CONFIRMED_BREAKOUT / BREAKOUT_RETEST / FAILED_BREAKOUT / RECLAIM.

Rules (all on CLOSES, never wicks):
  * breakout candle   = first close above zone.high after a close at or below it
  * acceptance        = `accept_n` consecutive closes above zone.high (default 3 on hourly)
  * volume expansion  = breakout-candle volume / trailing median volume
  * retest            = after the breakout, price traded back into the zone (low <= zone.high) and the
                        candle closed at or above zone.high (held)
  * failed            = after breaking, a close back below zone.low
  * reclaim           = price was above a zone (support), closed below zone.low, then closed back
                        above zone.high
  * wick-only pokes above a zone (high > zone.high, close <= zone.high) are EARLY_BREAKOUT_ATTEMPT
"""
from __future__ import annotations

import math

import numpy as np

from . import m13_price_structure as m13
from ._common import (
    base_result,
    fmt_price,
    normalize_candles,
    safe_get,
    to_float,
    ts_to_date,
)

CLASSES = ("NO_BREAKOUT", "EARLY_BREAKOUT_ATTEMPT", "CONFIRMED_BREAKOUT", "BREAKOUT_RETEST", "FAILED_BREAKOUT", "RECLAIM")


def _wick_body(c: np.ndarray, idxs: list[int]) -> dict | None:
    if not idxs:
        return None
    rows = c[idxs]
    o, h, l, cl = rows[:, 1], rows[:, 2], rows[:, 3], rows[:, 4]
    rng = np.where(h - l > 0, h - l, np.nan)
    body = np.abs(cl - o) / rng
    upper = (h - np.maximum(o, cl)) / rng
    lower = (np.minimum(o, cl) - l) / rng
    f = lambda a: (round(float(np.nanmean(a)), 3) if np.isfinite(np.nanmean(a)) else None)
    return {"n_candles": len(idxs), "body_frac": f(body), "upper_wick_frac": f(upper), "lower_wick_frac": f(lower),
            "all_bullish": bool((cl > o).all()), "candle_dates": [ts_to_date(c[i, 0], True) for i in idxs]}


def _trailing_median_vol(c: np.ndarray, i: int, lookback: int) -> float | None:
    seg = c[max(0, i - lookback):i, 5]
    seg = seg[seg > 0]
    if len(seg) < 3:
        return None
    return float(np.median(seg))


def _scan_zone(c: np.ndarray, z: dict, start: int, accept_n: int, vol_lookback: int, vol_min: float) -> dict | None:
    """Scan candles from `start` for the most recent breakout / failure / reclaim event on zone z.
    Returns an event dict or None if the zone was never crossed on a closing basis in the window."""
    closes, lows, highs = c[:, 4], c[:, 3], c[:, 2]
    n = len(c)
    zl, zh = z["low"], z["high"]
    events = []
    # state machine over closes. Side is remembered while inside the zone so that entering from
    # below and leaving below is a REJECTION (not a support loss) and entering from above and
    # leaving above is a HOLD (not a breakout).
    c0 = closes[start]
    state = "ABOVE" if c0 > zh else ("BELOW" if c0 < zl else "INSIDE_FROM_BELOW")
    breakout_i = None
    lost_i = None
    for i in range(start + 1, n):
        cl = closes[i]
        from_below = state in ("BELOW", "INSIDE_FROM_BELOW")
        if cl > zh:
            if from_below:
                kind = "RECLAIM" if lost_i is not None else "BREAKOUT"
                events.append({"type": kind, "i": i, "lost_i": lost_i})
                breakout_i = i
                lost_i = None
            state = "ABOVE"
        elif cl < zl:
            if not from_below:
                if breakout_i is not None:
                    events.append({"type": "FAILED", "i": i, "breakout_i": breakout_i})
                    breakout_i = None
                else:
                    events.append({"type": "LOST_SUPPORT", "i": i})
                lost_i = i
            elif state == "INSIDE_FROM_BELOW":
                events.append({"type": "REJECTION", "i": i})
            state = "BELOW"
        else:
            if state == "BELOW":
                state = "INSIDE_FROM_BELOW"
            elif state == "ABOVE":
                state = "INSIDE_FROM_ABOVE"
    if not events:
        return None
    last = events[-1]
    ev = {"zone": z, "events": events, "last": last}
    if last["type"] in ("BREAKOUT", "RECLAIM"):
        bi = last["i"]
        # acceptance: consecutive closes above zh starting at bi
        acc = 0
        for j in range(bi, n):
            if closes[j] > zh:
                acc += 1
            else:
                break
        still_above = closes[-1] > zh
        med = _trailing_median_vol(c, bi, vol_lookback)
        bvol = float(c[bi, 5])
        ratio = (bvol / med) if (med and med > 0) else None
        # also the max volume ratio over the first accept_n candles of the move
        seg = c[bi:min(n, bi + accept_n), 5]
        ratio_max = (float(seg.max()) / med) if (med and med > 0 and len(seg)) else None
        # retest: after acceptance window, any candle whose low dipped to/into the zone but closed >= zh
        retest_i = None
        for j in range(bi + 1, n):
            if lows[j] <= zh and closes[j] >= zh:
                retest_i = j
        # current state: did price close back inside the zone without closing below zl?
        inside_now = zl <= closes[-1] <= zh
        ev.update({"breakout_i": bi, "accept_count": acc, "still_above": still_above, "vol_ratio": ratio,
                   "vol_ratio_max": ratio_max, "retest_i": retest_i, "inside_now": inside_now,
                   "wick_only_before": None})
    return ev


def _wick_pokes(c: np.ndarray, z: dict, lookback: int) -> list[int]:
    n = len(c)
    out = []
    for i in range(max(0, n - lookback), n):
        if c[i, 2] > z["high"] and c[i, 4] <= z["high"]:
            out.append(i)
    return out


def analyze(bundle: dict, structure: dict | None = None, tf: str | None = None, accept_n: int = 3,
            vol_lookback: int = 20, vol_expansion_min: float = 1.5, lookback: int = 72,
            overextended_pct: float = 15.0, overextended_atr: float = 3.0, **kwargs) -> dict:
    out = base_result()
    out.update({"classification": "NO_BREAKOUT", "evidence": [], "chase_risk": None, "wick_vs_body": None,
                "volume_expansion_ratio": None, "breakout_zone": None, "tf": None, "overextended": False,
                "params": {"accept_n": accept_n, "vol_lookback": vol_lookback, "vol_expansion_min": vol_expansion_min,
                           "lookback": lookback, "overextended_pct": overextended_pct, "overextended_atr": overextended_atr}})
    bundle = bundle if isinstance(bundle, dict) else {}
    if not isinstance(structure, dict):
        structure = m13.analyze(bundle)
        out["heuristics"].append("structure= not supplied; ran m13 internally")
    ohlcv = bundle.get("ohlcv") if isinstance(bundle.get("ohlcv"), dict) else {}
    # pick timeframe: hour1 preferred, then minute15, then day1
    order = [tf] if tf else []
    order += [t for t in ("hour1", "minute15", "day1") if t not in order]
    c = np.zeros((0, 6))
    used_tf = None
    for t in order:
        cc = normalize_candles(ohlcv.get(t))
        if len(cc) >= accept_n + 5:
            c, used_tf = cc, t
            break
    if used_tf is None:
        out["unknowns"].append("no hourly/15m/daily candles with enough bars to classify a breakout")
        return out
    out["tf"] = used_tf
    if used_tf != "hour1":
        out["heuristics"].append(f"hour1 candles unavailable or too short; classifying on {used_tf} with accept_n={accept_n}")
    price = to_float(safe_get(bundle, "market", "price_usd")) or to_float(structure.get("price")) or float(c[-1, 4])
    n = len(c)
    start = max(0, n - lookback - 1)

    # candidate zones: this tf's zones plus the higher timeframe's (daily) zones, both from m13
    zones = []
    for z in structure.get("zones") or []:
        if not isinstance(z, dict) or z.get("low") is None or z.get("high") is None:
            continue
        if z.get("tf") in (used_tf, "day1", "hour1"):
            zones.append(z)
    if not zones:
        out["unknowns"].append("m13 produced no zones; nothing to break out of")
    atr_pct = safe_get(structure, "per_timeframe", used_tf, "volatility", "atr_pct")
    atr_abs = price * atr_pct / 100.0 if (atr_pct and price) else None

    events = []
    for z in zones:
        # ignore zones far from the recent price path (more than 60% away from the window's range)
        win_hi, win_lo = float(c[start:, 2].max()), float(c[start:, 3].min())
        if z["low"] > win_hi * 1.02 or z["high"] < win_lo * 0.98:
            continue
        ev = _scan_zone(c, z, start, accept_n, vol_lookback, vol_expansion_min)
        if ev:
            events.append(ev)
    classification = "NO_BREAKOUT"
    chosen = None
    if events:
        # decisive events (closes through a zone) outrank rejections (closes into a zone that did not
        # get through); within a tier the most recent event wins, then zone strength
        prio = {"BREAKOUT": 2, "RECLAIM": 2, "FAILED": 2, "LOST_SUPPORT": 1, "REJECTION": 0}
        events.sort(key=lambda e: (prio.get(e["last"]["type"], 0), e["last"]["i"], e["zone"].get("strength", 0)), reverse=True)
        chosen = events[0]
        z = chosen["zone"]
        last = chosen["last"]
        zdesc = f"{z.get('tf')} zone {fmt_price(z['low'])}-{fmt_price(z['high'])}"
        if last["type"] == "REJECTION":
            if last["i"] >= n - 2 * accept_n:
                classification = "EARLY_BREAKOUT_ATTEMPT"
                out["evidence"].append(f"{zdesc}: price closed into the zone from below then closed back under it at {ts_to_date(c[last['i'],0], True)}; an attempt, not a breakout")
            else:
                out["evidence"].append(f"{zdesc}: last attempt into the zone was rejected at {ts_to_date(c[last['i'],0], True)}; nothing since")
            chosen = None
        elif last["type"] == "FAILED":
            classification = "FAILED_BREAKOUT"
            out["evidence"].append(f"{zdesc}: broke out on a close at {ts_to_date(c[last['breakout_i'],0], True)} then closed back below zone low at {ts_to_date(c[last['i'],0], True)} ({fmt_price(c[last['i'],4])})")
        elif last["type"] == "LOST_SUPPORT":
            classification = "NO_BREAKOUT"
            out["evidence"].append(f"{zdesc}: support lost on a close at {ts_to_date(c[last['i'],0], True)}; no reclaim yet")
            out["inferences"].append("most recent structural event is a support loss, not a breakout")
        else:
            bi = chosen["breakout_i"]
            acc = chosen["accept_count"]
            ratio = chosen["vol_ratio"]
            ratio_max = chosen["vol_ratio_max"]
            out["volume_expansion_ratio"] = round(ratio, 2) if ratio is not None else None
            out["evidence"].append(f"{zdesc}: first close above zone high at {ts_to_date(c[bi,0], True)} (close {fmt_price(c[bi,4])})")
            if ratio is not None:
                out["evidence"].append(f"breakout candle volume {ratio:.1f}x trailing {vol_lookback}-candle median" + (f"; max {ratio_max:.1f}x within first {accept_n} candles" if ratio_max else ""))
            else:
                out["unknowns"].append("insufficient volume history to measure expansion on the breakout candle")
            vol_ok = (ratio is not None and ratio >= vol_expansion_min) or (ratio_max is not None and ratio_max >= vol_expansion_min)
            if not chosen["still_above"]:
                if chosen["inside_now"]:
                    classification = "EARLY_BREAKOUT_ATTEMPT"
                    out["evidence"].append(f"last close {fmt_price(c[-1,4])} is back inside the zone: breakout not holding yet (not failed either, zone low intact)")
                else:
                    classification = "FAILED_BREAKOUT"
            elif acc >= accept_n and (vol_ok or acc >= 2 * accept_n):
                classification = "RECLAIM" if last["type"] == "RECLAIM" else "CONFIRMED_BREAKOUT"
                out["evidence"].append(f"{acc} consecutive closes above zone high (acceptance threshold {accept_n})")
                if not vol_ok:
                    out["heuristics"].append(f"volume expansion below {vol_expansion_min}x but {acc} closes accepted (>= 2x threshold); treating as confirmed on time-acceptance")
                if chosen["retest_i"] is not None and chosen["retest_i"] > bi + 1 and last["type"] != "RECLAIM":
                    classification = "BREAKOUT_RETEST"
                    ri = chosen["retest_i"]
                    out["evidence"].append(f"retest at {ts_to_date(c[ri,0], True)}: low {fmt_price(c[ri,3])} dipped into the zone, close {fmt_price(c[ri,4])} held above zone high")
            else:
                classification = "EARLY_BREAKOUT_ATTEMPT"
                why = []
                if acc < accept_n:
                    why.append(f"only {acc} close(s) above zone high (need {accept_n})")
                if not vol_ok:
                    why.append(f"volume expansion {ratio:.1f}x < {vol_expansion_min}x" if ratio is not None else "volume expansion unmeasured")
                out["evidence"].append("not yet confirmed: " + "; ".join(why))
            if last["type"] == "RECLAIM" and classification in ("CONFIRMED_BREAKOUT", "EARLY_BREAKOUT_ATTEMPT"):
                out["evidence"].append(f"this was a reclaim: support lost on a close at {ts_to_date(c[last['lost_i'],0], True)} then closed back above the zone")
                if classification == "CONFIRMED_BREAKOUT":
                    classification = "RECLAIM"
            move_idxs = list(range(bi, min(n, bi + max(1, min(acc, accept_n)))))
            out["wick_vs_body"] = _wick_body(c, move_idxs)
            if out["wick_vs_body"] and out["wick_vs_body"]["upper_wick_frac"] is not None and out["wick_vs_body"]["upper_wick_frac"] > 0.5:
                out["inferences"].append("breakout candles are mostly upper wick: buyers were met with supply at the highs")
        out["breakout_zone"] = {k: z.get(k) for k in ("tf", "low", "high", "mid", "touches", "strength", "why")}
    # wick-only pokes at the nearest resistance (no close above yet)
    if classification == "NO_BREAKOUT":
        res = [z for z in zones if z.get("kind") == "RESISTANCE"]
        if res:
            nr = min(res, key=lambda z: z["low"])
            pokes = _wick_pokes(c, nr, min(lookback, 24))
            if pokes:
                classification = "EARLY_BREAKOUT_ATTEMPT"
                out["evidence"].append(f"{len(pokes)} wick(s) above resistance {fmt_price(nr['low'])}-{fmt_price(nr['high'])} without a close above (last {ts_to_date(c[pokes[-1],0], True)}); wicks are not breakouts")
                out["breakout_zone"] = {k: nr.get(k) for k in ("tf", "low", "high", "mid", "touches", "strength", "why")}
                out["wick_vs_body"] = _wick_body(c, pokes[-3:])
            else:
                out["evidence"].append(f"price below resistance {fmt_price(nr['low'])}-{fmt_price(nr['high'])}; no close or wick above it in the last {min(lookback,24)} candles")
        elif zones:
            out["evidence"].append("no resistance zone above price and no recent zone cross on a closing basis")
    out["classification"] = classification

    # chase risk: distance above the sensible invalidation (breakout zone low, else nearest support low)
    inv = None
    inv_src = None
    if out["breakout_zone"] and classification not in ("FAILED_BREAKOUT",) and out["breakout_zone"]["low"] < price:
        inv, inv_src = out["breakout_zone"]["low"], "breakout zone low"
    else:
        ns = structure.get("nearest_support")
        if isinstance(ns, dict) and ns.get("low"):
            inv, inv_src = ns["low"], f"nearest support low ({ns.get('tf')})"
    if inv and price:
        dist_pct = (price - inv) / inv * 100.0
        atr_mult = (price - inv) / atr_abs if atr_abs else None
        over = dist_pct > overextended_pct or (atr_mult is not None and atr_mult > overextended_atr)
        out["chase_risk"] = {"invalidation_level": inv, "invalidation_source": inv_src, "distance_pct": round(dist_pct, 2),
                             "distance_atr": round(atr_mult, 2) if atr_mult is not None else None, "atr_pct": atr_pct,
                             "overextended": bool(over), "thresholds": {"pct": overextended_pct, "atr": overextended_atr}}
        out["overextended"] = bool(over)
        out["inferences"].append(f"price is {dist_pct:.1f}% ({f'{atr_mult:.1f} ATR' if atr_mult is not None else 'ATR n/a'}) above {inv_src} {fmt_price(inv)}" + ("; OVEREXTENDED: entering here means a stop far from structure" if over else ""))
    else:
        out["unknowns"].append("no structural invalidation level below price; chase risk not computable")

    # order-flow context from market (supporting evidence only)
    mkt = bundle.get("market") if isinstance(bundle.get("market"), dict) else {}
    nb = safe_get(mkt, "net_buyers", "h1")
    tx = safe_get(mkt, "txns", "h1")
    if nb is not None:
        out["facts"].append(f"net buyers h1: {nb}")
        if classification in ("CONFIRMED_BREAKOUT", "EARLY_BREAKOUT_ATTEMPT", "RECLAIM", "BREAKOUT_RETEST"):
            out["inferences"].append("positive net buyers support the move" if to_float(nb, 0) > 0 else "net buyers not positive during the move: breakout lacks participation")
    if isinstance(tx, (list, tuple)) and len(tx) >= 2 and to_float(tx[0]) is not None and to_float(tx[1]):
        out["facts"].append(f"txns h1: {tx[0]} buys / {tx[1]} sells (ratio {to_float(tx[0])/to_float(tx[1]):.2f})")
    v1, v24 = to_float(safe_get(mkt, "vol", "h1")), to_float(safe_get(mkt, "vol", "h24"))
    if v1 is not None and v24:
        share = v1 / v24 * 100
        out["facts"].append(f"h1 volume is {share:.1f}% of h24 volume (even pace = 4.2%)")
    if not mkt:
        out["unknowns"].append("market block empty; no order-flow context for the breakout")
    out["heuristics"].append("breakouts are judged on closes only; acceptance = consecutive closes above the zone; volume expansion vs trailing median volume")
    return out
