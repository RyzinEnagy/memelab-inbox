"""Mechanical technical-analysis strategies on closed bars. Each docstring is the exact specification."""
from __future__ import annotations

from typing import Sequence

from . import features as F
from .base import Abstain, Exits, Signal, Strategy
from .features import B


def _sig(s: Strategy, chain, mint, bars: Sequence[B], decision_time, exits: Exits, feats: dict, invalidation: str) -> Signal:
    return Signal(s.id, s.version, chain, mint, candidate_time=bars[-1].end, decision_time=decision_time, side="BUY", exits=exits,
                  features=feats, params_hash=s.phash, invalidation=invalidation, based_on=(bars[0].start, bars[-1].start),
                  latest_input_available_at=bars[-1].avail)


class BreakoutClose(Strategy):
    """BREAKOUT_CLOSE: the last closed bar closes above the highest high of the previous `lookback` closed bars by at
    least `buffer`, with volume >= `vol_mult` x the median volume of those bars. A wick above the level that closes
    back below is NOT a breakout. Entry: next bar open after the bar is available (engine). Invalidation: a close back
    below the breakout level minus `stop_buffer` (stop placed there; gaps fill at the open). Exits: stop, take profit at
    `tp_r` R, or `max_hold_bars`. Abstains: fewer than lookback+1 closed bars (INSUFFICIENT_HISTORY), stale last bar."""
    id, version = "BREAKOUT_CLOSE", "1"
    default_params = {"lookback": 24, "buffer": 0.0, "vol_mult": 1.5, "stop_buffer": 0.03, "tp_r": 2.0, "max_hold_bars": 48, "max_staleness_bars": 1}

    @property
    def warmup_bars(self):
        return self.params["lookback"] + 1

    def evaluate(self, chain, mint, bars, decision_time, ctx=None):
        self._check(bars, decision_time)
        p = self.params
        if len(bars) < self.warmup_bars:
            return Abstain("INSUFFICIENT_HISTORY", f"{len(bars)} closed bars < {self.warmup_bars}")
        tf = bars[-1].end - bars[-1].start
        if decision_time - bars[-1].end > p["max_staleness_bars"] * tf + tf:
            return Abstain("STALE_DATA", "last closed bar too old")
        level = F.prior_high(bars, p["lookback"])
        mv = F.median_volume(bars, p["lookback"])
        last = bars[-1]
        if last.c <= level * (1 + p["buffer"]):
            return None
        if mv is not None and mv > 0 and last.v < p["vol_mult"] * mv:
            return None
        stop = level * (1 - p["stop_buffer"])
        return _sig(self, chain, mint, bars, decision_time, Exits(stop, take_profit_r=p["tp_r"], max_hold_s=p["max_hold_bars"] * tf),
                    {"level": level, "close": last.c, "volume": last.v, "median_volume": mv}, f"close below {stop:.6g} (breakout level {level:.6g} - {p['stop_buffer']:.0%})")


class BreakoutRetest(Strategy):
    """BREAKOUT_RETEST: a BREAKOUT_CLOSE happened within the last `within_bars` closed bars at level L; since then a
    closed bar's low came within `tol` of L (low <= L*(1+tol)) without closing below L*(1-tol); the last closed bar
    closes above L and above its own open (hold confirmed). A retest that closes below L*(1-tol) is a FAILED retest and
    cancels the setup. Entry next open. Stop below L*(1-stop_buffer)."""
    id, version = "BREAKOUT_RETEST", "1"
    default_params = {"lookback": 24, "within_bars": 12, "tol": 0.02, "stop_buffer": 0.04, "tp_r": 2.0, "max_hold_bars": 48, "vol_mult": 1.5}

    @property
    def warmup_bars(self):
        return self.params["lookback"] + 3

    def evaluate(self, chain, mint, bars, decision_time, ctx=None):
        self._check(bars, decision_time)
        p = self.params
        if len(bars) < self.warmup_bars:
            return Abstain("INSUFFICIENT_HISTORY", f"{len(bars)} closed bars < {self.warmup_bars}")
        tf = bars[-1].end - bars[-1].start
        n = len(bars)
        for k in range(n - 2, max(p["lookback"], n - 1 - p["within_bars"]) - 1, -1):     # breakout bar index k, retest after it
            lvl = F.prior_high(bars[:k + 1], p["lookback"])
            mv = F.median_volume(bars[:k + 1], p["lookback"])
            bk = bars[k]
            if lvl is None or bk.c <= lvl or (mv and bk.v < p["vol_mult"] * mv):
                continue
            after = bars[k + 1:]
            if any(b.c < lvl * (1 - p["tol"]) for b in after):
                return None                                   # failed retest: setup cancelled
            touched = any(b.l <= lvl * (1 + p["tol"]) for b in after)
            last = bars[-1]
            if touched and last.c > lvl and last.c > last.o:
                stop = lvl * (1 - p["stop_buffer"])
                return _sig(self, chain, mint, bars, decision_time, Exits(stop, take_profit_r=p["tp_r"], max_hold_s=p["max_hold_bars"] * tf),
                            {"level": lvl, "breakout_bar_start": bk.start, "retest_low": min(b.l for b in after)}, f"close below {stop:.6g} (retest level failed)")
            return None
        return None


class FailedBreakoutReclaim(Strategy):
    """RECLAIM: a breakout above L (close > L) within `within_bars`, then a close below L (failed breakout), then the last
    closed bar closes back above L. Entry next open. Stop below the lowest low since the failure."""
    id, version = "RECLAIM", "1"
    default_params = {"lookback": 24, "within_bars": 12, "tp_r": 2.0, "max_hold_bars": 48}

    @property
    def warmup_bars(self):
        return self.params["lookback"] + 3

    def evaluate(self, chain, mint, bars, decision_time, ctx=None):
        self._check(bars, decision_time)
        p = self.params
        if len(bars) < self.warmup_bars:
            return Abstain("INSUFFICIENT_HISTORY", "")
        tf = bars[-1].end - bars[-1].start
        n = len(bars)
        for k in range(n - 3, max(p["lookback"], n - 1 - p["within_bars"]) - 1, -1):
            lvl = F.prior_high(bars[:k + 1], p["lookback"])
            if lvl is None or bars[k].c <= lvl:
                continue
            mid = bars[k + 1:-1]
            if mid and any(b.c < lvl for b in mid) and bars[-1].c > lvl and bars[-2].c <= lvl:
                stop = min(b.l for b in mid)
                return _sig(self, chain, mint, bars, decision_time, Exits(stop, take_profit_r=p["tp_r"], max_hold_s=p["max_hold_bars"] * tf),
                            {"level": lvl, "failure_low": stop}, f"close below {stop:.6g} (reclaim low)")
            return None
        return None


class TrendHHHL(Strategy):
    """TREND_HHHL: the last two confirmed swing highs and lows are rising (HH and HL; pivots confirmed `right` bars
    later, never repainted) and the last closed bar closes above the last confirmed swing high. Not entered when price
    is more than `max_ext_atr` ATRs above the EMA(`ema_n`) (exhaustion filter). Stop below the last confirmed HL."""
    id, version = "TREND_HHHL", "1"
    default_params = {"left": 3, "right": 3, "ema_n": 20, "max_ext_atr": 4.0, "tp_r": 2.0, "max_hold_bars": 72}

    @property
    def warmup_bars(self):
        return max(self.params["ema_n"], 4 * (self.params["left"] + self.params["right"]))

    def evaluate(self, chain, mint, bars, decision_time, ctx=None):
        self._check(bars, decision_time)
        p = self.params
        if len(bars) < self.warmup_bars:
            return Abstain("INSUFFICIENT_HISTORY", "")
        tf = bars[-1].end - bars[-1].start
        st = F.trend_state(bars[:-1], p["left"], p["right"])     # pivots from bars before the trigger bar
        if st["state"] != "UP":
            return None
        last = bars[-1]
        if last.c <= st["last_high"]["price"] or bars[-2].c > st["last_high"]["price"]:
            return None
        e, a = F.ema([b.c for b in bars], p["ema_n"]), F.atr(bars, 14)
        if e is not None and a and (last.c - e) / a > p["max_ext_atr"]:
            return Abstain("OVEREXTENDED", f"{(last.c - e) / a:.1f} ATR above EMA")
        stop = st["last_low"]["price"]
        return _sig(self, chain, mint, bars, decision_time, Exits(stop, take_profit_r=p["tp_r"], max_hold_s=p["max_hold_bars"] * tf),
                    {"last_high": st["last_high"], "last_low": st["last_low"]}, f"close below last higher low {stop:.6g}")


class AbsorptionBreak(Strategy):
    """ABSORPTION_BREAK: over the last `k` closed bars the lows stay within `range_pct` of each other (price holds),
    down-bar volume has a negative slope (OBSERVED: selling volume shrinking), and the last closed bar closes above the
    range high. Calling this absorption is an INTERPRETATION recorded in the features; it is not proof of a future rise.
    Stop below the range low."""
    id, version = "ABSORPTION_BREAK", "1"
    default_params = {"k": 12, "range_pct": 0.12, "tp_r": 2.0, "max_hold_bars": 48}

    @property
    def warmup_bars(self):
        return self.params["k"] + 1

    def evaluate(self, chain, mint, bars, decision_time, ctx=None):
        self._check(bars, decision_time)
        p = self.params
        if len(bars) < self.warmup_bars:
            return Abstain("INSUFFICIENT_HISTORY", "")
        tf = bars[-1].end - bars[-1].start
        win = bars[-p["k"] - 1:-1]
        lo, hi = min(b.l for b in win), max(b.h for b in win)
        if hi / lo - 1 > p["range_pct"] * 2 or max(b.l for b in win) / lo - 1 > p["range_pct"]:
            return None
        slope = F.down_bar_volume_slope(win, len(win))
        if slope is None or slope >= 0:
            return None
        if bars[-1].c <= hi:
            return None
        return _sig(self, chain, mint, bars, decision_time, Exits(lo, take_profit_r=p["tp_r"], max_hold_s=p["max_hold_bars"] * tf),
                    {"range_low": lo, "range_high": hi, "down_volume_slope": slope, "observed": "down-bar volume falling while lows hold",
                     "interpretation": "absorption of sell pressure (inference, not a forecast)"}, f"close below range low {lo:.6g}")


class MomentumExhaustion(Strategy):
    """MOMENTUM: trend-following entry with an exhaustion guard and a liquidity filter, all on closed bars.
    Enter when: close > EMA(`fast`) > EMA(`slow`); the `roc_bars`-bar rate of change of the close is >= `min_roc`;
    volume regime is rising (median volume of the last `vol_short` bars >= `vol_regime` x the median of the
    `vol_long` bars before them). Abstain EXHAUSTION when the last bar's range is more than `blowoff_atr` ATRs and it
    closes in the lower half of that range, or when the close is more than `max_ext_atr` ATRs above EMA(`slow`).
    Abstain ILLIQUID when the median bar volume (USD) of the last `vol_short` bars is below `min_bar_volume_usd`.
    Stop: the lowest low of the last `stop_bars` closed bars. Exits: stop, `tp_r` R, `max_hold_bars`."""
    id, version = "MOMENTUM", "1"
    default_params = {"fast": 8, "slow": 24, "roc_bars": 6, "min_roc": 0.10, "vol_short": 6, "vol_long": 24, "vol_regime": 1.2,
                      "blowoff_atr": 3.0, "max_ext_atr": 5.0, "min_bar_volume_usd": 2_000.0, "stop_bars": 6, "tp_r": 2.0, "max_hold_bars": 48}

    @property
    def warmup_bars(self):
        p = self.params
        return max(p["slow"], p["vol_short"] + p["vol_long"], p["roc_bars"] + 1, 15)

    def evaluate(self, chain, mint, bars, decision_time, ctx=None):
        self._check(bars, decision_time)
        p = self.params
        if len(bars) < self.warmup_bars:
            return Abstain("INSUFFICIENT_HISTORY", f"{len(bars)} closed bars < {self.warmup_bars}")
        tf = bars[-1].end - bars[-1].start
        closes = [b.c for b in bars]
        last = bars[-1]
        short = sorted(b.v for b in bars[-p["vol_short"]:])[p["vol_short"] // 2]
        if short < p["min_bar_volume_usd"]:
            return Abstain("ILLIQUID", f"median bar volume {short:.0f} USD < {p['min_bar_volume_usd']:.0f}")
        ef, es, a = F.ema(closes, p["fast"]), F.ema(closes, p["slow"]), F.atr(bars, 14)
        if not (last.c > ef > es):
            return None
        roc = last.c / bars[-1 - p["roc_bars"]].c - 1
        if roc < p["min_roc"]:
            return None
        base = bars[-p["vol_short"] - p["vol_long"]:-p["vol_short"]]
        longm = sorted(b.v for b in base)[len(base) // 2]
        if longm > 0 and short < p["vol_regime"] * longm:
            return None
        if a:
            rng = last.h - last.l
            if rng > p["blowoff_atr"] * a and last.c < last.l + rng / 2:
                return Abstain("EXHAUSTION", f"blow-off bar {rng / a:.1f} ATR closing in its lower half")
            if (last.c - es) / a > p["max_ext_atr"]:
                return Abstain("EXHAUSTION", f"{(last.c - es) / a:.1f} ATR above EMA({p['slow']})")
        stop = min(b.l for b in bars[-p["stop_bars"]:])
        if stop >= last.c:
            return None
        return _sig(self, chain, mint, bars, decision_time, Exits(stop, take_profit_r=p["tp_r"], max_hold_s=p["max_hold_bars"] * tf),
                    {"ema_fast": ef, "ema_slow": es, "roc": roc, "vol_short_median": short, "vol_long_median": longm, "atr": a},
                    f"close below {stop:.6g} (lowest low of the last {p['stop_bars']} bars)")
