"""Point-in-time price features. Every function takes only CLOSED bars (oldest first) and looks backward.

Pivots are confirmed only after `right` further closed bars, and the confirmation time is returned, so a swing
low is never known before the bars that confirm it have closed (no repainting).
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class B:
    start: float
    end: float
    o: float
    h: float
    l: float
    c: float
    v: float
    avail: float

    @staticmethod
    def from_row(r: dict, provider_lag: float = 0.0) -> "B":
        end = r.get("end", r["start"] + r.get("tf", r.get("timeframe_s", 3600)))
        return B(float(r["start"]), float(end), float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"]),
                 float(r.get("v", r.get("volume_usd")) or 0.0), float(r.get("available_at", end + provider_lag)))


def prior_high(bars: Sequence[B], n: int) -> float | None:
    """Highest high of the n closed bars BEFORE the last one (the last bar is the one being tested)."""
    if len(bars) < n + 1:
        return None
    return max(b.h for b in bars[-n - 1:-1])


def prior_low(bars: Sequence[B], n: int) -> float | None:
    if len(bars) < n + 1:
        return None
    return min(b.l for b in bars[-n - 1:-1])


def atr(bars: Sequence[B], n: int = 14) -> float | None:
    if len(bars) < n + 1:
        return None
    trs = []
    for prev, b in zip(bars[-n - 1:-1], bars[-n:]):
        trs.append(max(b.h - b.l, abs(b.h - prev.c), abs(b.l - prev.c)))
    return sum(trs) / n


def median_volume(bars: Sequence[B], n: int) -> float | None:
    if len(bars) < n + 1:
        return None
    return statistics.median(b.v for b in bars[-n - 1:-1])


def ema(values: Sequence[float], n: int) -> float | None:
    if len(values) < n:
        return None
    k = 2 / (n + 1)
    e = sum(values[:n]) / n
    for v in values[n:]:
        e = v * k + e * (1 - k)
    return e


def confirmed_pivots(bars: Sequence[B], left: int = 3, right: int = 3) -> tuple[list[dict], list[dict]]:
    """Swing highs and lows. A pivot at index i is confirmed when bar i+right has closed; `known_at` is that bar's
    availability. Only pivots confirmed within the given bars are returned."""
    highs, lows = [], []
    for i in range(left, len(bars) - right):
        win = bars[i - left:i + right + 1]
        if bars[i].h == max(b.h for b in win) and all(bars[i].h > b.h for b in bars[i - left:i]):
            highs.append({"i": i, "price": bars[i].h, "t": bars[i].start, "known_at": bars[i + right].avail})
        if bars[i].l == min(b.l for b in win) and all(bars[i].l < b.l for b in bars[i - left:i]):
            lows.append({"i": i, "price": bars[i].l, "t": bars[i].start, "known_at": bars[i + right].avail})
    return highs, lows


def trend_state(bars: Sequence[B], left: int = 3, right: int = 3) -> dict:
    """HH/HL (UP), LH/LL (DOWN) from the last two confirmed pivots of each kind; otherwise RANGE/UNKNOWN."""
    hs, ls = confirmed_pivots(bars, left, right)
    if len(hs) < 2 or len(ls) < 2:
        return {"state": "UNKNOWN", "highs": hs[-2:], "lows": ls[-2:]}
    hh, hl = hs[-1]["price"] > hs[-2]["price"], ls[-1]["price"] > ls[-2]["price"]
    lh, ll = hs[-1]["price"] < hs[-2]["price"], ls[-1]["price"] < ls[-2]["price"]
    st = "UP" if hh and hl else ("DOWN" if lh and ll else "RANGE")
    return {"state": st, "last_high": hs[-1], "last_low": ls[-1], "prev_high": hs[-2], "prev_low": ls[-2]}


def down_bar_volume_slope(bars: Sequence[B], k: int) -> float | None:
    """Least-squares slope of volume on down bars (close < open) over the last k closed bars; negative = selling dries up.
    This is an OBSERVED feature; calling it absorption is an interpretation and is labeled as such by strategies."""
    if len(bars) < k:
        return None
    pts = [(i, b.v) for i, b in enumerate(bars[-k:]) if b.c < b.o]
    if len(pts) < 3:
        return None
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    den = sum((p[0] - mx) ** 2 for p in pts)
    return sum((p[0] - mx) * (p[1] - my) for p in pts) / den if den else None
