"""Builds alerts_day.json for the Phase 15 alert demo from the Phase 14 feed fixture (demo_day.json).

Adds, all invented: one allowlisted source so GOODCAT meets the convergence policy, one CORROBORATION flag on a LINKED
wallet for GOODCAT (recent), one on a LINKED wallet that is three days old (stale event), and the policy overrides the
demo uses. Run: python tests/fixtures/social/alerts/make_alerts.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "feed" / "demo_day.json"


def build() -> dict:
    spec = json.loads(BASE.read_text())
    spec["note"] = ("Invented accounts, tokens, posts, flags and market facts for the Phase 15 alert demo. Built by make_alerts.py "
                    "from the Phase 14 feed fixture.")
    spec["chrono_flags"] = list(spec["chrono_flags"]) + [
        {"at": "2026-10-13T08:05:00+00:00", "attribution": "LINKED", "bucket": "INFERENCE", "category": "CORROBORATION",
         "evidence": [{"kind": "post", "ref": "x:g1"}, {"kind": "tx", "ref": "invented-signature-2"}],
         "flag": "DISCLOSED_POSITION_CONSISTENT", "note": "invented: a linked wallet bought before the post that said it holds",
         "rule": "chrono.disclosed_position.v1", "source_id": "fx_trader_one", "token": "GOODCAT"},
        {"at": "2026-10-10T08:00:00+00:00", "attribution": "LINKED", "bucket": "INFERENCE", "category": "CORROBORATION",
         "evidence": [{"kind": "post", "ref": "x:g1"}, {"kind": "tx", "ref": "invented-signature-3"}],
         "flag": "DISCLOSED_POSITION_CONSISTENT_OLD", "note": "invented: an old linked-wallet event, past the age limit",
         "rule": "chrono.disclosed_position.v1", "source_id": "x:id:fx_bravo", "token": "GOODCAT"},
    ]
    spec["policy"] = {"reputable_sources": ["fx_bravo"]}
    return spec


if __name__ == "__main__":
    (HERE / "alerts_day.json").write_text(json.dumps(build(), indent=1, sort_keys=True) + "\n")
    print("wrote", HERE / "alerts_day.json")
