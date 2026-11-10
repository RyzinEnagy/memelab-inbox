"""Strategy registry: id -> class. Versions are part of every signal and experiment id."""
from __future__ import annotations

from .baselines import EnterAtDiscovery, MACross, NoTrade, RandomEntry
from .catalyst import CatalystVerified
from .labstatus import LabStatus
from .ta import AbsorptionBreak, BreakoutClose, BreakoutRetest, FailedBreakoutReclaim, MomentumExhaustion, TrendHHHL

REGISTRY = {c.id: c for c in (CatalystVerified, BreakoutClose, BreakoutRetest, FailedBreakoutReclaim, TrendHHHL, AbsorptionBreak, MomentumExhaustion, LabStatus,
                              NoTrade, EnterAtDiscovery, RandomEntry, MACross)}
BASELINES = ("NO_TRADE", "ENTER_AT_DISCOVERY", "RANDOM_ENTRY", "MA_CROSS")


def make(sid: str, **params):
    if sid not in REGISTRY:
        raise KeyError(f"unknown strategy {sid}")
    return REGISTRY[sid](**params)


def catalog() -> list[dict]:
    return [REGISTRY[k]().describe() for k in sorted(REGISTRY)]
