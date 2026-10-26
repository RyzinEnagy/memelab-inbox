"""Strategy contract. A strategy sees only closed bars and observations available at the decision time; it returns
a Signal (mechanical entry, structural invalidation, exits) or an Abstain with a reason. It never forecasts: every
signal carries claim = "SETUP" and the backtest decides what history says about such setups."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Sequence

from ..timeguard import LeakageError
from .features import B


class MalformedBars(ValueError):
    """Mixed timeframes, overlapping or unordered bars: the strategy refuses instead of guessing."""


@dataclass(frozen=True)
class Exits:
    stop_price: float | None                 # structural invalidation; gap-through fills at the open (engine)
    take_profit_r: float | None = None       # target = entry + R * (entry - stop)
    take_profit_pct: float | None = None
    max_hold_s: float | None = None
    trail_atr: float | None = None


@dataclass(frozen=True)
class Signal:
    strategy_id: str
    strategy_version: str
    chain: str
    mint: str
    candidate_time: float
    decision_time: float
    side: str
    exits: Exits
    features: dict
    params_hash: str
    invalidation: str
    based_on: tuple = ()
    claim: str = "SETUP"
    latest_input_available_at: float = 0.0

    def __post_init__(self):
        if self.latest_input_available_at > self.decision_time + 1e-9:
            raise LeakageError(f"{self.strategy_id}: an input available at {self.latest_input_available_at} was used at decision {self.decision_time}")
        if self.decision_time < self.candidate_time:
            raise ValueError("decision before candidate time")
        if self.side != "BUY":
            raise ValueError("long-only research signals")

    @property
    def signal_id(self) -> str:
        return hashlib.sha256(json.dumps([self.strategy_id, self.strategy_version, self.chain, self.mint, self.decision_time, self.params_hash]).encode()).hexdigest()[:24]

    def as_dict(self) -> dict:
        d = asdict(self)
        d["signal_id"] = self.signal_id
        return d


@dataclass(frozen=True)
class Abstain:
    reason: str
    detail: str = ""


def params_hash(params: dict) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]


class Strategy:
    id = "BASE"
    version = "0"
    kind = "TA"
    default_params: dict = {}

    def __init__(self, **params):
        unknown = set(params) - set(self.default_params)
        if unknown:
            raise ValueError(f"{self.id}: unknown params {sorted(unknown)}")
        self.params = {**self.default_params, **params}
        self.phash = params_hash(self.params)

    @property
    def warmup_bars(self) -> int:
        return 0

    def evaluate(self, chain: str, mint: str, bars: Sequence[B], decision_time: float, ctx: dict | None = None):
        raise NotImplementedError

    def _check(self, bars: Sequence[B], decision_time: float) -> None:
        if bars and bars[-1].avail > decision_time + 1e-9:
            raise LeakageError(f"{self.id}: bar available at {bars[-1].avail} passed to a decision at {decision_time}")
        if len(bars) > 1:
            tf = bars[0].end - bars[0].start
            for a, b in zip(bars, bars[1:]):
                # one timeframe, strictly increasing starts, no overlap (gaps are allowed: they are no-trade hours)
                if b.end - b.start != tf or b.start < a.end or b.start <= a.start:
                    raise MalformedBars(f"{self.id}: bars at {a.start} and {b.start} are not one clean series (tf {tf})")

    def describe(self) -> dict:
        return {"id": self.id, "version": self.version, "kind": self.kind, "params": self.params, "params_hash": self.phash, "warmup_bars": self.warmup_bars,
                "doc": (self.__doc__ or "").strip()}
