"""m13: price structure.

Swing detection, HH/HL vs LH/LL sequencing, support/resistance zones with touch and volume
weighting, ATH/ATL, volatility, and a per-timeframe plus combined structure classification.

Pure function of the Bundle: never fetches, never raises on missing data.
"""
from __future__ import annotations

import math

import numpy as np

from ._common import (
    TF_ORDER,
    TF_ZONE_TOL,
    atr_pct,
    base_result,
    fmt_price,
    infer_candles_per_day,
    normalize_candles,
    pct,
    realized_vol,
    safe_get,
    to_float,
    ts_to_date,
)

STRUCTURES = ("UPTREND", "DOWNTREND", "RANGE", "TRANSITION", "PRICE_DISCOVERY")


# ----------------------------------------------------------------------------- swings

def find_swings(c: np.ndarray, left: int = 3, right: int = 3) -> tuple[list[dict], list[dict]]:
    """Fractal swing highs/lows. A swing high at i has h[i] > every high in the `left` bars before
    and >= every high in the `right` bars after (ties on the right are allowed so flat tops count)."""
    n = len(c)
    highs, lows = [], []
    if n < left + right + 1:
        return highs, lows
    h, l, v = c[:, 2], c[:, 3], c[:, 5]
    for i in range(left, n - right):
        hl, hr = h[i - left:i], h[i + 1:i + 1 + right]
        ll, lr = l[i - left:i], l[i + 1:i + 1 + right]
        if h[i] > hl.max() and h[i] >= hr.max():
            highs.append({"i": i, "ts": float(c[i, 0]), "price": float(h[i]), "vol": float(v[i]), "type": "high"})
        if l[i] < ll.min() and l[i] <= lr.min():
            lows.append({"i": i, "ts": float(c[i, 0]), "price": float(l[i]), "vol": float(v[i]), "type": "low"})
    return highs, lows


def label_sequence(highs: list[dict], lows: list[dict], tol: float) -> dict:
    """Label successive swing highs HH/LH/EQH and lows HL/LL/EQL (EQ = within tolerance)."""
    hi_labels, lo_labels = [], []
    for a, b in zip(highs, highs[1:]):
        d = (b["price"] - a["price"]) / a["price"] if a["price"] else 0.0
        hi_labels.append("EQH" if abs(d) <= tol / 2 else ("HH" if d > 0 else "LH"))
    for a, b in zip(lows, lows[1:]):
        d = (b["price"] - a["price"]) / a["price"] if a["price"] else 0.0
        lo_labels.append("EQL" if abs(d) <= tol / 2 else ("HL" if d > 0 else "LL"))
    return {"highs": hi_labels, "lows": lo_labels}


# ----------------------------------------------------------------------------- zones

def cluster_zones(points: list[dict], tol: float, candles: np.ndarray, tf: str, min_touches: int = 1) -> list[dict]:
    """Greedy single-linkage clustering of swing prices within `tol` (fraction of the cluster mean)."""
    if not points:
        return []
    pts = sorted(points, key=lambda p: p["price"])
    clusters: list[list[dict]] = []
    for p in pts:
        if clusters:
            cur = clusters[-1]
            mean = sum(q["price"] for q in cur) / len(cur)
            if abs(p["price"] - mean) / mean <= tol:
                cur.append(p)
                continue
        clusters.append([p])
    vols = candles[:, 5] if len(candles) else np.zeros(0)
    med_vol = float(np.median(vols[vols > 0])) if len(vols) and (vols > 0).any() else 0.0
    n = len(candles)
    ath_i = int(np.argmax(candles[:, 2])) if n else -1
    atl_i = int(np.argmin(candles[:, 3])) if n else -1
    zones = []
    for cl in clusters:
        if len(cl) < min_touches:
            continue
        prices = [q["price"] for q in cl]
        lo, hi = min(prices), max(prices)
        mid = sum(prices) / len(prices)
        # ensure a minimum width (half the tolerance) so single-touch zones are not zero-width
        min_half = mid * tol / 4
        if hi - lo < 2 * min_half:
            lo, hi = mid - min_half, mid + min_half
        n_high = sum(1 for q in cl if q["type"] == "high")
        n_low = sum(1 for q in cl if q["type"] == "low")
        vol_weight = 0.0
        hv_events = []
        for q in cl:
            if med_vol > 0 and q["vol"] > 0:
                ratio = q["vol"] / med_vol
                vol_weight += min(ratio, 5.0)
                if ratio >= 2.0:
                    hv_events.append((ratio, q))
        hv_events.sort(key=lambda t: -t[0])
        touches = len(cl)
        recency = max(q["i"] for q in cl) / max(n - 1, 1) if n else 0.0
        strength = touches + 0.5 * vol_weight + 1.0 * recency
        why = [f"{touches} touch{'es' if touches != 1 else ''} ({n_high} swing high{'s' if n_high != 1 else ''}, {n_low} swing low{'s' if n_low != 1 else ''}) on {tf}"]
        if hv_events:
            r, q = hv_events[0]
            kind = "rejection" if q["type"] == "high" else "absorption"
            why.append(f"high-volume {kind} ({r:.1f}x median volume) on {ts_to_date(q['ts'], tf != 'day1')}")
        idxs = {q["i"] for q in cl}
        if ath_i in idxs or (n and hi >= float(candles[ath_i, 2]) * (1 - 1e-9)):
            why.append("contains the in-data ATH")
        if atl_i in idxs or (n and lo <= float(candles[atl_i, 3]) * (1 + 1e-9)):
            why.append("contains the in-data ATL")
        if n_high and n_low:
            why.append("acted as both support and resistance (polarity flip)")
        last_touch = max(cl, key=lambda q: q["i"])
        why.append(f"last touched {ts_to_date(last_touch['ts'], tf != 'day1')}")
        zones.append({
            "tf": tf, "low": lo, "high": hi, "mid": mid, "touches": touches,
            "n_high": n_high, "n_low": n_low, "vol_weight": round(vol_weight, 2),
            "strength": round(strength, 2), "last_touch_ts": last_touch["ts"],
            "last_touch_i": last_touch["i"], "why": "; ".join(why),
        })
    return zones


def label_zones(zones: list[dict], price: float | None) -> None:
    for z in zones:
        if price is None:
            z["kind"] = "UNKNOWN"
            z["distance_pct"] = None
            continue
        if z["high"] < price:
            z["kind"] = "SUPPORT"
        elif z["low"] > price:
            z["kind"] = "RESISTANCE"
        else:
            z["kind"] = "AT_PRICE"
        z["distance_pct"] = round((z["mid"] - price) / price * 100.0, 2)
        z["edge_distance_pct"] = round(((z["high"] if z["kind"] == "SUPPORT" else z["low"]) - price) / price * 100.0, 2)


# ----------------------------------------------------------------------------- classification

def classify_tf(c: np.ndarray, highs: list[dict], lows: list[dict], labels: dict, tol: float,
                price: float, zones: list[dict], discovery_pct: float = 5.0, discovery_tail: float = 0.10) -> tuple[str, str, float]:
    """Return (structure, reason, confidence 0..1) for one timeframe."""
    n = len(c)
    if n < 5:
        return "TRANSITION", "too few candles to classify", 0.1
    ath = float(c[:, 2].max())
    ath_i = int(np.argmax(c[:, 2]))
    near_ath = price >= ath * (1 - discovery_pct / 100.0)
    ath_recent = ath_i >= math.floor((n - 1) * (1 - discovery_tail))
    if near_ath and ath_recent:
        return "PRICE_DISCOVERY", f"price within {discovery_pct:.0f}% of the in-data ATH and ATH printed in the last {int(discovery_tail*100)}% of candles", 0.8

    hl, ll = labels["highs"][-2:], labels["lows"][-2:]
    last_h = hl[-1] if hl else None
    last_l = ll[-1] if ll else None
    if last_h and last_l:
        up = last_h == "HH" and last_l in ("HL", "EQL")
        up2 = last_h in ("HH", "EQH") and last_l == "HL"
        down = last_h == "LH" and last_l in ("LL", "EQL")
        down2 = last_h in ("LH", "EQH") and last_l == "LL"
        if len(hl) >= 2 and len(ll) >= 2:
            # range check: recent swing highs within tol of each other and recent lows likewise
            rh = [q["price"] for q in highs[-3:]]
            rl = [q["price"] for q in lows[-3:]]
            flat_h = (max(rh) - min(rh)) / max(rh) <= 2 * tol
            flat_l = (max(rl) - min(rl)) / max(rl) <= 2 * tol
            if flat_h and flat_l and not (up and hl == ["HH", "HH"]) and not (down and ll == ["LL", "LL"]):
                return "RANGE", f"recent swing highs ({', '.join(fmt_price(x) for x in rh)}) and lows ({', '.join(fmt_price(x) for x in rl)}) each sit inside a {2*tol*100:.0f}% band", 0.7
        if up or up2:
            return "UPTREND", f"last swings: high {last_h}, low {last_l}", 0.7 if (up and up2) else 0.55
        if down or down2:
            return "DOWNTREND", f"last swings: high {last_h}, low {last_l}", 0.7 if (down and down2) else 0.55
        return "TRANSITION", f"mixed swings: high {last_h}, low {last_l} (no agreement between highs and lows)", 0.5

    # fallback: not enough swings, use net change and drawdown over the window
    closes = c[:, 4]
    chg = (closes[-1] - closes[0]) / closes[0] if closes[0] else 0.0
    if abs(chg) <= 2 * tol:
        return "RANGE", f"too few swings; net change over window {chg*100:+.1f}% is inside {2*tol*100:.0f}% band", 0.3
    return ("UPTREND" if chg > 0 else "DOWNTREND"), f"too few swings; net change over window {chg*100:+.1f}%", 0.3


def combine_structures(per_tf: dict) -> tuple[str, str]:
    """Combine per-timeframe classifications. Higher timeframes carry the trend; lower timeframes
    describe the state within it."""
    avail = [tf for tf in TF_ORDER if tf in per_tf and per_tf[tf].get("structure")]
    if not avail:
        return "TRANSITION", "no timeframe could be classified"
    # primary = highest timeframe with enough candles (>= 20), else the one with the most candles
    primary = next((tf for tf in avail if per_tf[tf].get("n_candles", 0) >= 20), None)
    if primary is None:
        primary = max(avail, key=lambda tf: per_tf[tf].get("n_candles", 0))
    p = per_tf[primary]["structure"]
    lower = [tf for tf in avail if TF_ORDER.index(tf) > TF_ORDER.index(primary)]
    lower_s = [per_tf[tf]["structure"] for tf in lower]
    if any(per_tf[tf]["structure"] == "PRICE_DISCOVERY" for tf in avail) and p in ("PRICE_DISCOVERY", "UPTREND"):
        return "PRICE_DISCOVERY", f"{primary}: {p}; a timeframe shows price discovery near the in-data ATH"
    if not lower_s:
        return p, f"{primary} only: {p}"
    opposite = {"UPTREND": "DOWNTREND", "DOWNTREND": "UPTREND"}
    if p in opposite and opposite[p] in lower_s:
        return "TRANSITION", f"{primary} {p} but {', '.join(f'{tf} {per_tf[tf]['structure']}' for tf in lower)} (lower timeframe opposes the higher one)"
    if all(s == p for s in lower_s):
        return p, f"all timeframes agree: {p}"
    detail = ", ".join(f"{tf} {per_tf[tf]['structure']}" for tf in lower)
    if p in ("UPTREND", "DOWNTREND") and all(s in ("RANGE", "TRANSITION", p) for s in lower_s):
        return p, f"{primary} {p}; consolidating on lower timeframes ({detail})"
    if p == "RANGE" and any(s in ("UPTREND", "DOWNTREND") for s in lower_s):
        return "TRANSITION", f"{primary} RANGE but lower timeframes trending ({detail}); possible range resolution"
    return p, f"{primary} {p}; lower timeframes: {detail}"


# ----------------------------------------------------------------------------- main

def analyze(bundle: dict, left: int = 3, right: int = 3, zone_tol: dict | None = None,
            min_touches: int = 1, max_zones_per_tf: int = 12, discovery_pct: float = 5.0,
            discovery_tail: float = 0.10, **kwargs) -> dict:
    out = base_result()
    out.update({
        "structure": "TRANSITION", "structure_summary": "", "per_timeframe": {}, "zones": [],
        "ath": None, "atl": None, "pct_from_ath": None, "pct_from_atl": None,
        "volatility": {}, "nearest_support": None, "nearest_resistance": None,
        "current_range": None, "price": None, "params": {"left": left, "right": right},
    })
    bundle = bundle if isinstance(bundle, dict) else {}
    ohlcv = bundle.get("ohlcv") if isinstance(bundle.get("ohlcv"), dict) else {}
    price = to_float(safe_get(bundle, "market", "price_usd"))
    tol_map = dict(TF_ZONE_TOL)
    if isinstance(zone_tol, dict):
        tol_map.update({k: float(v) for k, v in zone_tol.items() if to_float(v) is not None})

    candles_by_tf: dict[str, np.ndarray] = {}
    for tf, raw in (ohlcv or {}).items():
        c = normalize_candles(raw)
        if len(c) == 0:
            out["unknowns"].append(f"ohlcv.{tf}: no usable candles")
            continue
        candles_by_tf[tf] = c
    if not candles_by_tf:
        out["unknowns"].append("no OHLCV data in bundle; price structure cannot be assessed")
    if price is None:
        # fall back to the latest close of the lowest available timeframe
        for tf in reversed(TF_ORDER):
            if tf in candles_by_tf:
                price = float(candles_by_tf[tf][-1, 4])
                out["heuristics"].append(f"market.price_usd missing; using last {tf} close {fmt_price(price)} as current price")
                break
        if price is None:
            out["unknowns"].append("market.price_usd missing and no candles to infer it")
    out["price"] = price

    all_zones: list[dict] = []
    ath_candidates, atl_candidates = [], []
    for tf in sorted(candles_by_tf, key=lambda t: TF_ORDER.index(t) if t in TF_ORDER else 99):
        c = candles_by_tf[tf]
        tol = tol_map.get(tf, 0.03)
        n = len(c)
        highs, lows = find_swings(c, left, right)
        labels = label_sequence(highs, lows, tol)
        zones = cluster_zones(highs + lows, tol, c, tf, min_touches)
        label_zones(zones, price)
        zones.sort(key=lambda z: -z["strength"])
        zones = zones[:max_zones_per_tf]
        tf_ath = float(c[:, 2].max())
        tf_atl = float(c[:, 3].min())
        ath_i, atl_i = int(np.argmax(c[:, 2])), int(np.argmin(c[:, 3]))
        ath_candidates.append((tf_ath, float(c[ath_i, 0]), tf))
        atl_candidates.append((tf_atl, float(c[atl_i, 0]), tf))
        cpd = infer_candles_per_day(tf, c)
        vol = realized_vol(c, cpd)
        atrp = atr_pct(c)
        vol["atr_pct"] = round(atrp, 3) if atrp is not None else None
        vol["candles_per_24h"] = cpd
        structure, reason, conf = ("TRANSITION", "no price", 0.0)
        if price is not None:
            structure, reason, conf = classify_tf(c, highs, lows, labels, tol, price, zones, discovery_pct, discovery_tail)
        sup = [z for z in zones if z["kind"] == "SUPPORT"]
        res = [z for z in zones if z["kind"] == "RESISTANCE"]
        nearest_sup = max(sup, key=lambda z: z["high"]) if sup else None
        nearest_res = min(res, key=lambda z: z["low"]) if res else None
        rng = None
        if structure == "RANGE" and nearest_sup and nearest_res:
            rng = {"low": nearest_sup["low"], "high": nearest_res["high"],
                   "height_pct": round((nearest_res["high"] - nearest_sup["low"]) / nearest_sup["low"] * 100, 2),
                   "position_in_range_pct": round((price - nearest_sup["low"]) / (nearest_res["high"] - nearest_sup["low"]) * 100, 1) if nearest_res["high"] > nearest_sup["low"] else None}
        last_hl = None
        if labels["lows"]:
            for j in range(len(labels["lows"]) - 1, -1, -1):
                if labels["lows"][j] == "HL":
                    last_hl = lows[j + 1]["price"]
                    break
        last_lh = None
        if labels["highs"]:
            for j in range(len(labels["highs"]) - 1, -1, -1):
                if labels["highs"][j] == "LH":
                    last_lh = highs[j + 1]["price"]
                    break
        out["per_timeframe"][tf] = {
            "structure": structure, "reason": reason, "confidence": conf, "n_candles": n,
            "span_from": ts_to_date(c[0, 0], tf != "day1"), "span_to": ts_to_date(c[-1, 0], tf != "day1"),
            "swing_highs": [{"ts": q["ts"], "price": q["price"], "i": q["i"]} for q in highs[-8:]],
            "swing_lows": [{"ts": q["ts"], "price": q["price"], "i": q["i"]} for q in lows[-8:]],
            "sequence": {"highs": labels["highs"][-6:], "lows": labels["lows"][-6:]},
            "last_higher_low": last_hl, "last_lower_high": last_lh,
            "last_swing_low": lows[-1]["price"] if lows else None,
            "last_swing_high": highs[-1]["price"] if highs else None,
            "ath": tf_ath, "atl": tf_atl, "ath_date": ts_to_date(c[ath_i, 0], tf != "day1"),
            "pct_from_ath": round(pct(price, tf_ath), 2) if price is not None else None,
            "zone_tol": tol, "zones": zones, "nearest_support": nearest_sup, "nearest_resistance": nearest_res,
            "current_range": rng, "volatility": vol, "last_close": float(c[-1, 4]),
        }
        out["volatility"][tf] = vol
        all_zones.extend(zones)
        out["facts"].append(f"{tf}: {n} candles {out['per_timeframe'][tf]['span_from']} to {out['per_timeframe'][tf]['span_to']}; "
                            f"in-data high {fmt_price(tf_ath)}, low {fmt_price(tf_atl)}; {len(highs)} swing highs, {len(lows)} swing lows")
        if vol["per_24h_pct"] is not None:
            out["facts"].append(f"{tf}: realized vol {vol['per_candle_pct']:.2f}% per candle, {vol['per_24h_pct']:.1f}% per 24h; ATR {vol['atr_pct']:.2f}% of price" if vol["atr_pct"] is not None else f"{tf}: realized vol {vol['per_24h_pct']:.1f}% per 24h")
        out["inferences"].append(f"{tf} structure: {structure} ({reason})")
        if n < 20:
            out["unknowns"].append(f"{tf}: only {n} candles; classification confidence low")

    if ath_candidates:
        ath, ath_ts, ath_tf = max(ath_candidates, key=lambda t: t[0])
        atl, atl_ts, atl_tf = min(atl_candidates, key=lambda t: t[0])
        out["ath"] = ath
        out["atl"] = atl
        out["ath_date"] = ts_to_date(ath_ts, ath_tf != "day1")
        out["atl_date"] = ts_to_date(atl_ts, atl_tf != "day1")
        if price is not None:
            out["pct_from_ath"] = round(pct(price, ath), 2)
            out["pct_from_atl"] = round(pct(price, atl), 2)
            out["facts"].append(f"price {fmt_price(price)} is {out['pct_from_ath']:+.1f}% from in-data ATH {fmt_price(ath)} ({out['ath_date']}) and {out['pct_from_atl']:+.1f}% from in-data ATL {fmt_price(atl)}")
        out["unknowns"].append("ATH/ATL are from the candles in the bundle only; earlier price history may exist")

    # combined
    structure, summary = combine_structures(out["per_timeframe"])
    out["structure"] = structure
    out["structure_summary"] = summary
    if out["per_timeframe"]:
        out["inferences"].append(f"combined structure: {structure} ({summary})")

    # zones across timeframes, sorted by distance from price
    label_zones(all_zones, price)
    all_zones.sort(key=lambda z: (abs(z["distance_pct"]) if z.get("distance_pct") is not None else 1e9))
    out["zones"] = [{k: z[k] for k in ("tf", "kind", "low", "high", "mid", "touches", "strength", "distance_pct", "edge_distance_pct", "why", "last_touch_ts") if k in z} for z in all_zones]
    sup = [z for z in all_zones if z["kind"] == "SUPPORT"]
    res = [z for z in all_zones if z["kind"] == "RESISTANCE"]
    out["nearest_support"] = max(sup, key=lambda z: z["high"]) if sup else None
    out["nearest_resistance"] = min(res, key=lambda z: z["low"]) if res else None
    if out["nearest_support"]:
        z = out["nearest_support"]
        out["inferences"].append(f"nearest support {fmt_price(z['low'])}-{fmt_price(z['high'])} ({z['tf']}, {z['distance_pct']:+.1f}% from price): {z['why']}")
    elif candles_by_tf:
        out["unknowns"].append("no support zone below price in the available candles")
    if out["nearest_resistance"]:
        z = out["nearest_resistance"]
        out["inferences"].append(f"nearest resistance {fmt_price(z['low'])}-{fmt_price(z['high'])} ({z['tf']}, {z['distance_pct']:+.1f}% from price): {z['why']}")
    elif candles_by_tf:
        out["unknowns"].append("no resistance zone above price in the available candles (price at or above every prior swing high)")
    for tf in ("hour1", "day1", "minute15"):
        rng = safe_get(out, "per_timeframe", tf, "current_range")
        if rng:
            out["current_range"] = dict(rng, tf=tf)
            break
    # headline volatility: hourly if present, else whatever exists
    for tf in ("hour1", "minute15", "day1"):
        if tf in out["volatility"]:
            out["volatility"]["headline"] = dict(out["volatility"][tf], tf=tf)
            break
    out["heuristics"].append(f"swing detection is a {left}/{right}-bar fractal; zones cluster swing points within "
                             + ", ".join(f"{tf} {tol_map[tf]*100:.1f}%" for tf in candles_by_tf if tf in tol_map)
                             + "; zone strength = touches + 0.5*volume weight + recency")
    return out
