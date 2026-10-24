"""Catalyst, wallet and social event-driven strategies with strict known-at semantics.

A catalyst record (built from the lab's catalyst tables, bt_observations or bt_capture_provenance) looks like:
  {"event_id", "chain", "mint", "origin_group", "claim_type", "published_at" (claim, untrusted), "first_seen_at",
   "available_at" (when the lab could act), "verified": bool, "denied": bool, "mint_verified": bool,
   "sentiment": +1 / -1, "historical_asof_proof": "NONE" | ...}
Rules enforced here:
- only records with available_at <= decision time exist for the strategy; published_at never makes one visible earlier;
- reposts from one origin_group count once (independent confirmation = distinct origins);
- a record without mint verification never links to a token;
- a token whose price already ran before the record became available is "late" (price first, attention later);
- verified on-chain selling (SWAP_SELL observations), not transfers, blocks entry; positive posts never override it;
- for historical studies, captures with historical_asof_proof NONE are usable only from their own first_seen_at.
"""
from __future__ import annotations

import random

from .base import Abstain, Exits, Signal, Strategy

# wallet observation kinds: only a verified swap sale is selling. A funding transfer, a move to custody or a program
# account, and an ownership inference are different facts and never count as a sale (G04).
WALLET_KINDS = ("SWAP_SELL", "SWAP_BUY", "WALLET_TRANSFER", "CUSTODY_MOVE", "PROGRAM_ACCOUNT", "OWNERSHIP_INFERENCE")


def visible(records: list[dict], t: float) -> list[dict]:
    return [r for r in records if r["available_at"] <= t]


def independent_origins(records: list[dict]) -> int:
    return len({r.get("origin_group") or r["event_id"] for r in records})


def placebo_shift(records: list[dict], seed: int, shift_s: float) -> list[dict]:
    """Control: move every record's times by a seeded uniform shift in [-shift_s, +shift_s] (same records, wrong times)."""
    rng = random.Random(seed)
    out = []
    for r in records:
        d = rng.uniform(-shift_s, shift_s)
        out.append({**r, "available_at": r["available_at"] + d, "first_seen_at": r.get("first_seen_at", r["available_at"]) + d,
                    "event_time": (r.get("event_time") or r["available_at"]) + d, "placebo": True})
    return out


class CatalystVerified(Strategy):
    """CATALYST_VERIFIED: when a catalyst record about this exact mint (mint_verified) becomes available, enter at the
    next open if: at least `min_origins` distinct origins report it (reposts of one origin count once), none is a
    denial, the claim is positive, the price did not already rise more than `max_prerun` between the first
    record's event time and the decision (price-first-attention-later guard), and no verified SWAP_SELL by tracked
    concentrated wallets in the last `sell_window_s`. Stop `stop_frac` below the last close; hold `hold_bars`."""
    id, version, kind = "CATALYST_VERIFIED", "1", "CATALYST"
    default_params = {"min_origins": 2, "max_prerun": 0.30, "sell_window_s": 6 * 3600, "stop_frac": 0.2, "hold_bars": 24, "tp_r": None,
                      "require_contemporaneous_proof": False}

    def evaluate(self, chain, mint, bars, decision_time, ctx=None):
        self._check(bars, decision_time)
        ctx = ctx or {}
        recs = [r for r in visible(ctx.get("catalysts", []), decision_time) if r.get("mint") == mint and r.get("chain") == chain]
        unverified = [r for r in visible(ctx.get("catalysts", []), decision_time) if r.get("mint") == mint and not r.get("mint_verified")]
        recs = [r for r in recs if r.get("mint_verified")]
        if not recs:
            return Abstain("UNVERIFIED_CATALYST", "no mint-verified record") if unverified else None
        if self.params["require_contemporaneous_proof"]:
            recs = [r for r in recs if r.get("historical_asof_proof", "NONE") != "NONE"]
            if not recs:
                return Abstain("UNKNOWN_AS_OF", "only late captures; no contemporaneous proof")
        if any(r.get("denied") for r in recs):
            return Abstain("CATALYST_DENIED", "a denial is visible")
        theses = [h for h in ctx.get("theses", []) if h["available_at"] <= decision_time]
        if theses and max(theses, key=lambda h: h["available_at"]).get("fatal_flags"):
            latest = max(theses, key=lambda h: h["available_at"])
            return Abstain("RISK_FATAL_FLAW", "lab fatal flag visible: " + ",".join(latest["fatal_flags"]))
        pos = [r for r in recs if (r.get("sentiment") or 0) > 0]
        if not pos:
            return None
        n_orig = independent_origins(pos)
        if n_orig < self.params["min_origins"]:
            return None
        sells = [w for w in ctx.get("wallet_events", []) if w["available_at"] <= decision_time and w.get("kind") == "SWAP_SELL"
                 and decision_time - w["available_at"] <= self.params["sell_window_s"]]
        if sells:
            return Abstain("VERIFIED_SELLING", f"{len(sells)} verified swap sells by tracked wallets")
        if not bars:
            return Abstain("INSUFFICIENT_HISTORY", "no closed bar")
        first_evt = min((r.get("event_time") or r["available_at"]) for r in pos)
        before = [b for b in bars if b.end <= first_evt]
        last = bars[-1]
        if before:
            prerun = last.c / before[-1].c - 1
            if prerun > self.params["max_prerun"]:
                return Abstain("LATE_ATTENTION", f"price already +{prerun:.0%} before the catalyst was knowable")
        else:
            prerun = None
        tf = last.end - last.start
        return Signal(self.id, self.version, chain, mint, candidate_time=max(r["available_at"] for r in pos), decision_time=decision_time, side="BUY",
                      exits=Exits(last.c * (1 - self.params["stop_frac"]), take_profit_r=self.params["tp_r"], max_hold_s=self.params["hold_bars"] * tf),
                      features={"origins": n_orig, "records": len(pos), "prerun": prerun, "claim_types": sorted({r.get("claim_type") for r in pos}),
                                "placebo": any(r.get("placebo") for r in pos)},
                      params_hash=self.phash, invalidation=f"close below {last.c * (1 - self.params['stop_frac']):.6g}",
                      latest_input_available_at=max([last.avail] + [r["available_at"] for r in pos]))
