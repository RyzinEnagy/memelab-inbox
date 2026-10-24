"""Phase 04 (P31): build the copyleft fingerprint set used by memelab/predictive/runtime.py copyleft_findings.

Reads the pinned AGPL sources outside the repository (MiroFish and black-it clones under /home/claude/pi_research/src at their
Phase 02/03 pins), takes 4-line shingles of normalized code lines with runtime.shingle_hashes and keeps the winnowed minimum of
every 12-shingle window (runtime.winnow). Only truncated sha256 hashes are written: no line of AGPL code enters the repository,
and the hashes cannot be turned back into code. Any copied run of at least 15 normalized lines shares a kept fingerprint.

    python build_copyleft_fingerprints.py OUT.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))
from memelab.predictive import runtime as R  # noqa: E402

SRC = Path("/home/claude/pi_research/src")
SOURCES = [
    {"repo": "666ghj/MiroFish", "dir": "666ghj__MiroFish", "pin": "7657031ac01184afe2cb220f5ee3545573b5e843", "license": "AGPL-3.0",
     "roots": ["backend", "frontend/src"]},
    {"repo": "bancaditalia/black-it", "dir": "bancaditalia__black-it", "pin": "6577b3cc12d26be0eff1924694dd58ede7a5ae6e",
     "license": "AGPL-3.0-or-later", "roots": ["black_it"]},
]


def main(out: str) -> None:
    fps: set[str] = set()
    meta = []
    for s in SOURCES:
        d = SRC / s["dir"]
        head = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        assert head == s["pin"], f"{s['repo']} clone is at {head}, not the pin"
        files = sorted(p for r in s["roots"] for p in (d / r).rglob("*") if p.suffix in R.CODE_SUFFIXES and p.is_file())
        kept = set()
        for p in files:
            kept |= R.winnow(R.shingle_hashes(p.read_text(errors="replace")))
        fps |= kept
        meta.append({"repo": s["repo"], "pin": s["pin"], "license": s["license"], "roots": s["roots"], "files": len(files),
                     "fingerprints": len(kept)})
    doc = {"version": 1, "purpose": "P31 copyleft gate: winnowed 4-line shingle hashes of pinned AGPL sources; hashes only",
           "normalization": "whitespace collapsed, lines under 8 characters dropped (runtime.normalized_lines)",
           "shingle_lines": R.SHINGLE_LINES, "winnow_window": R.WINNOW_WINDOW, "hash": f"sha256 hex prefix {R.HASH_HEX}",
           "sources": meta, "fingerprints": sorted(fps)}
    Path(out).write_text(json.dumps(doc, indent=0, sort_keys=True) + "\n")
    print(json.dumps({"fingerprints": len(fps), "sources": meta}))


if __name__ == "__main__":
    main(sys.argv[1])
