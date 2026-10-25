"""Phase 06: check the holdout seal without opening it.

Recomputes the sha256 and size of every file listed in sealed/SEAL.json (bytes only; nothing is decompressed or parsed), checks
the seal's own digest, and checks that three values are recorded OUTSIDE the seal, in docs/predictive-intelligence/DECISIONS.md
(and the holdout label hash also in PHASE_06_RESULTS.json): the holdout label file's sha256, the seal digest, and the sha256 of
SEAL.json itself, so a rewritten SEAL.json fails (Phase 06 skeptic m4, PI-D-045). It prints no count of sealed files (m8).
Exit 0 when the seal holds, 1 otherwise.

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
    dec = (REPO / "docs/predictive-intelligence/DECISIONS.md").read_text()
    own = L.file_sha256(PHASE / "sealed" / "SEAL.json")
    for name, v in (("holdout label sha256", h), ("seal digest", seal.get("seal_sha256")), ("SEAL.json sha256", own)):
        if not v or v not in dec:
            probs.append(f"{name} not recorded in DECISIONS.md")
    print(json.dumps({"holdout_labels_sha256": h, "seal_sha256": seal.get("seal_sha256"), "seal_json_sha256": own,
                      "problems": probs}, indent=1))
    return 1 if probs else 0


if __name__ == "__main__":
    raise SystemExit(main())
