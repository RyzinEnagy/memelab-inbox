"""Phase 06: check the holdout seal without opening it.

Recomputes the sha256 and size of every file listed in sealed/SEAL.json (bytes only; nothing is decompressed or parsed), checks
the seal's own digest, and checks that the holdout label file's sha256 is the one recorded in PHASE_06_RESULTS.json and in
docs/predictive-intelligence/DECISIONS.md. Exit 0 when the seal holds, 1 otherwise.

    python -B check_seal.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PHASE = Path(__file__).resolve().parent.parent
REPO = PHASE.parents[2]
sys.path.insert(0, str(REPO))
from memelab.predictive import labels as L  # noqa: E402


def main() -> int:
    seal = json.loads((PHASE / "sealed" / "SEAL.json").read_text())
    probs = L.verify_seal(seal["files"], PHASE / "sealed")
    if L.sha(seal["files"]) != seal.get("seal_sha256"):
        probs.append("SEAL.json files block does not hash to seal_sha256")
    h = seal["files"]["holdout_labels.jsonl.gz"]["sha256"]
    res = PHASE / "PHASE_06_RESULTS.json"
    if res.exists() and h not in res.read_text():
        probs.append("holdout label sha256 not in PHASE_06_RESULTS.json")
    if h not in (REPO / "docs/predictive-intelligence/DECISIONS.md").read_text():
        probs.append("holdout label sha256 not in DECISIONS.md")
    print(json.dumps({"files": len(seal["files"]), "holdout_labels_sha256": h, "seal_sha256": seal.get("seal_sha256"),
                      "problems": probs}, indent=1))
    return 1 if probs else 0


if __name__ == "__main__":
    raise SystemExit(main())
