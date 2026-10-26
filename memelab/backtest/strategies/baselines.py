"""Baselines evaluated under the same universe, execution model and costs as every strategy."""
from __future__ import annotations

import hashlib

from . import features as F
from .base import Abstain, Exits, Signal, Strategy


class NoTrade(Strategy):
    """NO_TRADE: never enters. Its result is zero P&L and zero exposure; any strategy must beat it net of costs."""
    id, version, kind = "NO_TRADE", "1", "BASELINE"

    def evaluate(self, chain, mint, bars, decision_time, ctx=None):
        return None


class EnterAtDiscovery(Strategy):
    """ENTER_AT_DISCOVERY (buy and hold from discovery): enters at the first decision opportunity for each eligible
    token (the next open after the lab first observed it) and holds for `hold_bars` with a wide `stop_frac` stop.
    One attempt only: if that order cannot fill (no pool basis, no liquidity, impact cap), the token is not retried
    later, so the baseline never drifts into "enter whenever it became tradable". Shows what the discovery universe did."""
    id, version, kind = "ENTER_AT_DISCOVERY", "2", "BASELINE"
    default_params = {"hold_bars": 24, "stop_frac": 0.9}

    def evaluate(self, chain, mint, bars, decision_time, ctx=None):
        self._check(bars, decision_time)
        if not bars:
            return Abstain("INSUFFICIENT_HISTORY", "no closed bar at discovery")
        if (ctx or {}).get("attempts_so_far", (ctx or {}).get("entries_so_far", 0)) > 0:
            return None
        tf = bars[-1].end - bars[-1].start
        last = bars[-1]
        return Signal(self.id, self.version, chain, mint, candidate_time=decision_time, decision_time=decision_time, side="BUY",
                      exits=Exits(last.c * (1 - self.params["stop_frac"]), max_hold_s=self.params["hold_bars"] * tf), features={"close": last.c},
                      params_hash=self.phash, invalidation="time exit", latest_input_available_at=last.avail)


class RandomEntry(Strategy):
    """RANDOM_ENTRY: at each decision point enters with probability `p` decided by a seeded hash of (seed, mint,
    decision_time): deterministic, independent of prices. Same exits as the strategy it is compared with."""
    id, version, kind = "RANDOM_ENTRY", "1", "BASELINE"
    default_params = {"p": 0.05, "seed": 7, "stop_frac": 0.15, "tp_r": 2.0, "max_hold_bars": 48}

    def evaluate(self, chain, mint, bars, decision_time, ctx=None):
        self._check(bars, decision_time)
        if not bars:
            return Abstain("INSUFFICIENT_HISTORY", "")
        h = int(hashlib.sha256(f"{self.params['seed']}|{mint}|{decision_time}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        if h >= self.params["p"]:
            return None
        tf = bars[-1].end - bars[-1].start
        last = bars[-1]
        return Signal(self.id, self.version, chain, mint, candidate_time=last.end, decision_time=decision_time, side="BUY",
                      exits=Exits(last.c * (1 - self.params["stop_frac"]), take_profit_r=self.params["tp_r"], max_hold_s=self.params["max_hold_bars"] * tf),
                      features={"u": h}, params_hash=self.phash, invalidation="random baseline", latest_input_available_at=last.avail)


class MACross(Strategy):
    """MA_CROSS: transparent indicator baseline. Fast EMA crosses above slow EMA on the last closed bar. Stop at
    `stop_frac` below the close."""
    id, version, kind = "MA_CROSS", "1", "BASELINE"
    default_params = {"fast": 8, "slow": 24, "stop_frac": 0.15, "tp_r": 2.0, "max_hold_bars": 48}

    @property
    def warmup_bars(self):
        return self.params["slow"] + 2

    def evaluate(self, chain, mint, bars, decision_time, ctx=None):
        self._check(bars, decision_time)
        p = self.params
        if len(bars) < self.warmup_bars:
            return Abstain("INSUFFICIENT_HISTORY", "")
        c = [b.c for b in bars]
        f1, s1 = F.ema(c, p["fast"]), F.ema(c, p["slow"])
        f0, s0 = F.ema(c[:-1], p["fast"]), F.ema(c[:-1], p["slow"])
        if None in (f0, s0, f1, s1) or not (f0 <= s0 and f1 > s1):
            return None
        tf = bars[-1].end - bars[-1].start
        return Signal(self.id, self.version, chain, mint, candidate_time=bars[-1].end, decision_time=decision_time, side="BUY",
                      exits=Exits(bars[-1].c * (1 - p["stop_frac"]), take_profit_r=p["tp_r"], max_hold_s=p["max_hold_bars"] * tf),
                      features={"fast": f1, "slow": s1}, params_hash=self.phash, invalidation="stop", latest_input_available_at=bars[-1].avail)
