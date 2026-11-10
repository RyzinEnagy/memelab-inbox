"""Strategies driven by the lab's own point-in-time evaluations (thesis rows in the frozen universe)."""
from __future__ import annotations

from .base import Abstain, Exits, Signal, Strategy

ACTIONABLE = ("ENTRY CONDITIONS MET", "NEAR ENTRY", "SETUP DEVELOPING", "WATCH")


class LabStatus(Strategy):
    """LAB_STATUS: when the lab records a thesis (decision time = the thesis created_at, which is when the lab's own
    analysis existed) with status in `statuses`, score >= `min_score` and NO fatal flag, enter at the next bar open.
    Stop: the thesis snapshot's nearest support when it is below the price, else `stop_frac` below the last close.
    Exits: stop, `tp_r` R, or `max_hold_bars`. This tests the lab's own ranking as a signal; it never overrides a
    fatal flag (fatal-flag rows can only be negative controls)."""
    id, version, kind = "LAB_STATUS", "1", "LAB"
    default_params = {"statuses": ["NEAR ENTRY", "ENTRY CONDITIONS MET", "SETUP DEVELOPING"], "min_score": 55, "stop_frac": 0.2,
                      "tp_r": 2.0, "max_hold_bars": 48}

    def evaluate(self, chain, mint, bars, decision_time, ctx=None):
        self._check(bars, decision_time)
        ev = (ctx or {}).get("thesis")
        if not ev:
            return None
        if ev["available_at"] > decision_time + 1e-9:
            from ..timeguard import LeakageError
            raise LeakageError("thesis used before it existed")
        if ev.get("fatal_flags"):
            return Abstain("RISK_FATAL_FLAW", ",".join(ev["fatal_flags"]))
        if ev.get("status") not in self.params["statuses"] or (ev.get("score") or 0) < self.params["min_score"]:
            return None
        if not bars:
            return Abstain("INSUFFICIENT_HISTORY", "no closed bar before the thesis")
        last = bars[-1]
        snap = ev.get("snapshot") or {}
        sup = snap.get("nearest_support")
        stop = sup if sup and sup < last.c else last.c * (1 - self.params["stop_frac"])
        tf = last.end - last.start
        return Signal(self.id, self.version, chain, mint, candidate_time=ev["available_at"], decision_time=decision_time, side="BUY",
                      exits=Exits(stop, take_profit_r=self.params["tp_r"], max_hold_s=self.params["max_hold_bars"] * tf),
                      features={"status": ev.get("status"), "score": ev.get("score"), "snapshot_liquidity": snap.get("liquidity"), "exit_cap_3pct": snap.get("exit_cap_3pct")},
                      params_hash=self.phash, invalidation=f"close below {stop:.6g}", latest_input_available_at=max(last.avail, ev["available_at"]))
