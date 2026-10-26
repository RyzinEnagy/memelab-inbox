"""Phase 14 seed converter: one behavioral seed from a Phase 10 socialcat-1 snapshot (`socialcat.socialcat_as_of`) of one exact
decision. Kept outside `memelab/` because Phase 10's isolation test forbids any other lab module to name its code (Phase 17
decides where integration code lives). No side effect on import.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from memelab.predictive import behavioral as BH  # noqa: E402

SEED_NAMES = ("sc_attention_trend_ord", "sc_attention_suspect", "sc_organic_acceleration", "sc_attention_reversal",
              "sc_lifecycle_late", "sc_narrative_tagged", "sc_channels_n")


def seed_from_snapshot(snap: dict) -> dict:
    """The lab's attention readings available at the decision plus the catalyst and social table states. Missing readings are left
    out, never filled; a reading available after the decision raises."""
    if not snap.get("decision_key") or not snap.get("row_sha256"):
        raise BH.BehavioralError("snapshot without a decision: no seed")
    T = float(snap["decision_time"])
    ref = f"socialcat-1:{snap['socialcat_snapshot_sha']}"
    obs = []
    for n in SEED_NAMES:
        v = snap["values"][n]
        if v["value"] is None:
            continue
        if v["available_at"] is None or float(v["available_at"]) > T:
            raise BH.BehavioralError(f"{n} is not available at the decision")
        obs.append(BH.observation(BH.LAB_ATTENTION_PROXY, n, float(v["value"]), BH.iso(v["available_at"]), f"{ref}:{n}"))
    obs.append(BH.observation(BH.SOURCE_STATE, "catalyst_state", snap["catalyst_state"], BH.iso(T), f"{ref}:catalyst_state"))
    obs.append(BH.observation(BH.SOURCE_STATE, "social_state", snap["social_state"], BH.iso(T), f"{ref}:social_state"))
    return BH.build_seed(snap["chain"], snap["mint"], snap["row_sha256"], BH.iso(T), obs)
