"""Shared helpers for the structure / setup / sizing modules (m13-m18).

Dependency-light: stdlib + numpy only. Nothing here fetches data.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable

import numpy as np

# Candles per 24h for the timeframe keys used in the Bundle contract.
TF_CANDLES_PER_DAY = {"day1": 1.0, "hour1": 24.0, "minute15": 96.0, "minute5": 288.0, "minute1": 1440.0}
TF_SECONDS = {"day1": 86400, "hour1": 3600, "minute15": 900, "minute5": 300, "minute1": 60}
# Zone clustering tolerance (fraction of price) per timeframe.
TF_ZONE_TOL = {"day1": 0.06, "hour1": 0.03, "minute15": 0.015, "minute5": 0.01, "minute1": 0.0075}
# Ordering from highest to lowest timeframe.
TF_ORDER = ["day1", "hour1", "minute15", "minute5", "minute1"]


def base_result() -> dict:
    return {"facts": [], "inferences": [], "heuristics": [], "unknowns": []}


def is_num(x: Any) -> bool:
    if isinstance(x, bool):
        return False
    if isinstance(x, (int, float)):
        return not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))
    return False


def to_float(x: Any, default: float | None = None) -> float | None:
    """Best-effort float conversion that never raises."""
    if x is None or isinstance(x, bool):
        return default
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    if math.isnan(v) or math.isinf(v):
        return default
    return v


def safe_get(d: Any, *keys: Any, default: Any = None) -> Any:
    """Nested dict getter that tolerates None / non-dict intermediates."""
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def normalize_candles(raw: Any) -> np.ndarray:
    """Return an (n, 6) float array [ts, o, h, l, c, v], sorted ascending by ts, invalid rows dropped.

    Accepts the GeckoTerminal order (newest first) or any order. Returns an empty (0, 6) array
    for None / empty / malformed inputs.
    """
    if not raw or not isinstance(raw, (list, tuple)):
        return np.zeros((0, 6), dtype=float)
    rows = []
    for r in raw:
        if not isinstance(r, (list, tuple)) or len(r) < 5:
            continue
        vals = [to_float(x) for x in r[:6]]
        if len(vals) < 6:
            vals.append(0.0)
        if vals[5] is None:
            vals[5] = 0.0
        if any(v is None for v in vals[:5]):
            continue
        ts, o, h, l, c, v = vals
        if h <= 0 or l <= 0 or c <= 0 or o <= 0:
            continue
        if h < l:
            h, l = l, h
        h = max(h, o, c)
        l = min(l, o, c)
        rows.append([ts, o, h, l, c, max(v, 0.0)])
    if not rows:
        return np.zeros((0, 6), dtype=float)
    arr = np.array(rows, dtype=float)
    arr = arr[np.argsort(arr[:, 0], kind="stable")]
    # drop duplicate timestamps, keeping the last occurrence
    if len(arr) > 1:
        keep = np.ones(len(arr), dtype=bool)
        keep[:-1] = arr[1:, 0] != arr[:-1, 0]
        arr = arr[keep]
    return arr


def ts_to_date(ts: float | None, with_time: bool = False) -> str:
    if ts is None:
        return "unknown date"
    try:
        t = float(ts)
        if t > 1e12:  # milliseconds
            t /= 1000.0
        dt = datetime.fromtimestamp(t, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M" if with_time else "%Y-%m-%d")
    except (ValueError, OverflowError, OSError):
        return "unknown date"


def infer_candles_per_day(tf: str, candles: np.ndarray) -> float:
    if tf in TF_CANDLES_PER_DAY:
        return TF_CANDLES_PER_DAY[tf]
    if len(candles) >= 3:
        diffs = np.diff(candles[:, 0])
        diffs = diffs[diffs > 0]
        if len(diffs):
            med = float(np.median(diffs))
            if med > 1e7:  # ms
                med /= 1000.0
            if med > 0:
                return 86400.0 / med
    return 24.0


def pct(a: float | None, b: float | None) -> float | None:
    """(a - b) / b * 100, or None."""
    if a is None or b is None or b == 0:
        return None
    return (a - b) / b * 100.0


def r1(x: float | None, nd: int = 1) -> float | None:
    if x is None:
        return None
    return round(float(x), nd)


def fmt_price(p: float | None) -> str:
    if p is None:
        return "n/a"
    p = float(p)
    if p == 0:
        return "0"
    if p >= 1:
        return f"{p:,.4f}".rstrip("0").rstrip(".")
    # significant digits for sub-dollar memecoin prices
    digits = max(4, int(-math.floor(math.log10(abs(p)))) + 3)
    return f"{p:.{digits}f}"


def atr_pct(candles: np.ndarray, period: int = 14) -> float | None:
    """Average true range as % of close over the last `period` candles."""
    n = len(candles)
    if n < 2:
        return None
    h, l, c = candles[:, 2], candles[:, 3], candles[:, 4]
    prev_c = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    k = min(period, n - 1)
    seg = tr[-k:]
    ref = c[-k:]
    ref = np.where(ref > 0, ref, np.nan)
    vals = seg / ref * 100.0
    vals = vals[~np.isnan(vals)]
    if not len(vals):
        return None
    return float(np.mean(vals))


def realized_vol(candles: np.ndarray, candles_per_day: float) -> dict:
    """Std of log returns of closes: per candle and scaled to 24h (sqrt-time)."""
    c = candles[:, 4] if len(candles) else np.zeros(0)
    c = c[c > 0]
    if len(c) < 3:
        return {"per_candle_pct": None, "per_24h_pct": None, "n_returns": max(0, len(c) - 1)}
    lr = np.diff(np.log(c))
    sd = float(np.std(lr, ddof=1)) if len(lr) > 1 else float(np.std(lr))
    per_candle = sd * 100.0
    per_day = sd * math.sqrt(max(candles_per_day, 1e-9)) * 100.0
    return {"per_candle_pct": round(per_candle, 3), "per_24h_pct": round(per_day, 3), "n_returns": int(len(lr))}


# ----------------------------------------------------------------------------- quotes

def parse_quote_side(side: Any) -> list[tuple[float, float, dict]]:
    """Return sorted [(usd_size, impact_pct, raw)] for a BUY or SELL quote dict.

    Impact unit detection: Jupiter's priceImpactPct is a fraction (0.0123 == 1.23%) despite the
    name. If every impact is <= 1.0 we treat them as fractions and convert to percent; otherwise
    we take them as percent already. Callers should surface this in `heuristics`.
    """
    if not isinstance(side, dict) or not side:
        return []
    pts = []
    for k, v in side.items():
        size = to_float(k)
        if size is None and isinstance(v, dict):
            size = to_float(v.get("usd")) or to_float(v.get("in_usd"))
        if size is None or size <= 0:
            continue
        imp = None
        if isinstance(v, dict):
            status = str(v.get("status", "ok")).lower()
            if status not in ("ok", "success", "succeeded", "200", "none", ""):
                # failed quote = route cannot fill this size; treat as infinite impact
                pts.append((size, float("inf"), v))
                continue
            imp = to_float(v.get("impact"))
            if imp is None:
                imp = to_float(v.get("priceImpactPct"))
        else:
            imp = to_float(v)
        if imp is None:
            continue
        pts.append((size, abs(imp), v if isinstance(v, dict) else {}))
    if not pts:
        return []
    finite = [p[1] for p in pts if math.isfinite(p[1])]
    if finite and max(finite) <= 1.0:
        pts = [(s, (i * 100.0 if math.isfinite(i) else i), r) for s, i, r in pts]
    pts.sort(key=lambda t: t[0])
    return pts


def quote_unit_note(side: Any) -> str | None:
    if not isinstance(side, dict) or not side:
        return None
    imps = [to_float(v.get("impact")) if isinstance(v, dict) else to_float(v) for v in side.values()]
    imps = [i for i in imps if i is not None]
    if imps and max(abs(i) for i in imps) <= 1.0:
        return "quote impacts all <= 1.0: interpreted as fractions (Jupiter priceImpactPct style) and converted to percent"
    return None


def interp_impact(points: list[tuple[float, float, dict]], size: float) -> tuple[float | None, str]:
    """Log-linear interpolation of impact (percent) at `size`. Returns (impact_pct, flag).

    flag: "interpolated" | "exact" | "below_tested" | "beyond_tested_depth" | "no_quotes".
    Beyond the largest tested size we extrapolate conservatively: impact grows at least linearly
    with size (AMM impact is roughly linear for small trades, super-linear beyond), using the
    steeper of the last-segment log slope and a linear-in-size scaling.
    """
    if not points or size is None or size <= 0:
        return None, "no_quotes"
    sizes = [p[0] for p in points]
    imps = [p[1] for p in points]
    for s, i in zip(sizes, imps):
        if abs(s - size) / s < 1e-9:
            return i, "exact"
    if size < sizes[0]:
        # scale down linearly from the smallest tested point (conservative: no better than linear)
        i0 = imps[0]
        if not math.isfinite(i0):
            return float("inf"), "below_tested"
        return i0 * size / sizes[0], "below_tested"
    if size > sizes[-1]:
        # conservative extrapolation
        s1, i1 = sizes[-1], imps[-1]
        if not math.isfinite(i1):
            return float("inf"), "beyond_tested_depth"
        lin = i1 * size / s1
        if len(sizes) >= 2 and math.isfinite(imps[-2]) and imps[-2] > 0 and i1 > 0:
            s0, i0 = sizes[-2], imps[-2]
            slope = (math.log(i1) - math.log(i0)) / (math.log(s1) - math.log(s0)) if s1 != s0 else 1.0
            slope = max(slope, 1.0)
            loglin = math.exp(math.log(i1) + slope * (math.log(size) - math.log(s1)))
            return max(lin, loglin), "beyond_tested_depth"
        return lin, "beyond_tested_depth"
    # bracket
    for j in range(1, len(sizes)):
        if sizes[j - 1] <= size <= sizes[j]:
            s0, s1 = sizes[j - 1], sizes[j]
            i0, i1 = imps[j - 1], imps[j]
            if not math.isfinite(i1):
                return float("inf"), "interpolated"
            if i0 <= 0 or i1 <= 0:
                # linear fallback
                t = (size - s0) / (s1 - s0) if s1 != s0 else 0.0
                return i0 + t * (i1 - i0), "interpolated"
            t = (math.log(size) - math.log(s0)) / (math.log(s1) - math.log(s0)) if s1 != s0 else 0.0
            return math.exp(math.log(i0) + t * (math.log(i1) - math.log(i0))), "interpolated"
    return None, "no_quotes"


def max_size_for_impact(points: list[tuple[float, float, dict]], max_impact_pct: float) -> tuple[float | None, str]:
    """Largest size whose (interpolated) impact <= max_impact_pct.

    Returns (size, flag). flag: "interpolated" | "capped_at_largest_tested" | "below_smallest_tested" | "no_quotes".
    Interpolation is log-linear between the bracketing tested sizes. We never extrapolate above the
    largest tested size (that would claim depth that was not observed).
    """
    if not points:
        return None, "no_quotes"
    sizes = [p[0] for p in points]
    imps = [p[1] for p in points]
    if imps[0] > max_impact_pct:
        # even the smallest tested size exceeds the threshold: scale down linearly (conservative)
        if not math.isfinite(imps[0]) or imps[0] <= 0:
            return 0.0, "below_smallest_tested"
        return sizes[0] * max_impact_pct / imps[0], "below_smallest_tested"
    best = sizes[0]
    for j in range(1, len(sizes)):
        if imps[j] <= max_impact_pct:
            best = sizes[j]
            continue
        # bracket between j-1 (ok) and j (too much)
        s0, s1, i0, i1 = sizes[j - 1], sizes[j], imps[j - 1], imps[j]
        if not math.isfinite(i1):
            # failed quote at s1: stay at s0
            return s0, "interpolated"
        if i0 <= 0:
            t = (max_impact_pct - i0) / (i1 - i0) if i1 != i0 else 0.0
            return s0 + t * (s1 - s0), "interpolated"
        t = (math.log(max_impact_pct) - math.log(i0)) / (math.log(i1) - math.log(i0)) if i1 != i0 else 0.0
        return math.exp(math.log(s0) + t * (math.log(s1) - math.log(s0))), "interpolated"
    return best, "capped_at_largest_tested"


def route_pool_count(side: Any) -> int | None:
    """Max number of distinct pools / hops in any quote route on a side, or None if routes absent."""
    if not isinstance(side, dict):
        return None
    best = None
    for v in side.values():
        if not isinstance(v, dict):
            continue
        route = v.get("route")
        if isinstance(route, list) and route:
            n = len(route)
            best = n if best is None else max(best, n)
    return best


def dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out
