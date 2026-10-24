"""Phase 01: verify every cell of architecture/GAP_MATRIX.csv independently of the script that wrote it.

Checks: the full facility x need grid is present once; status is one of the five allowed values; each anchor resolves:
  line   file exists, the line exists, and the keyword appears within 3 lines of it
  grep0  `git grep -i -E <pattern> -- memelab ':!memelab/predictive'` finds nothing
  nopath no tracked or untracked path matches the glob
  data   the dotted key exists in the probe summary JSON
Exit 0 when every cell holds, 1 otherwise. Read-only.

    python audits/predictive-intelligence/phase_01/probes/check_gap_anchors.py
"""
import csv
import glob
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CSV = ROOT / "audits/predictive-intelligence/phase_01/architecture/GAP_MATRIX.csv"
STATUSES = {"VERIFIED_PRESENT", "PARTIAL", "MISSING", "CONFLICT", "UNKNOWN"}


def main() -> int:
    rows = list(csv.DictReader(CSV.open()))
    facs = sorted({r["facility"] for r in rows})
    needs = sorted({r["need"] for r in rows})
    bad = []
    seen = {}
    for r in rows:
        k = (r["facility"], r["need"])
        seen[k] = seen.get(k, 0) + 1
    for f in facs:
        for n in needs:
            if seen.get((f, n)) != 1:
                bad.append(f"cell {f} x {n} appears {seen.get((f, n), 0)} times")
    for r in rows:
        tag = f"{r['facility']} x {r['need']}"
        if r["status"] not in STATUSES:
            bad.append(f"{tag}: status {r['status']!r}")
        kind, val, ev = r["check_kind"], r["check_value"], r["evidence"]
        if kind == "line":
            path, _, ln = ev.rpartition(":")
            p = ROOT / path
            if not p.exists():
                bad.append(f"{tag}: {path} missing")
                continue
            lines = p.read_text().splitlines()
            i = int(ln)
            if not (1 <= i <= len(lines)) or not any(val in lines[j] for j in range(max(0, i - 4), min(len(lines), i + 3))):
                bad.append(f"{tag}: keyword {val!r} not near {ev}")
        elif kind == "grep0":
            out = subprocess.run(["git", "grep", "-i", "-E", "-n", val, "--", "memelab", ":!memelab/predictive"], cwd=ROOT,
                                 capture_output=True, text=True)
            if out.stdout.strip():
                bad.append(f"{tag}: grep found {out.stdout.strip().splitlines()[0]}")
        elif kind == "nopath":
            if glob.glob(str(ROOT / val)):
                bad.append(f"{tag}: {val} exists")
        elif kind == "data":
            path, _, key = ev.partition("#")
            d = json.loads((ROOT / path).read_text())
            for part in key.split("."):
                if not isinstance(d, dict) or part not in d:
                    bad.append(f"{tag}: key {key} not in {path}")
                    break
                d = d[part]
        else:
            bad.append(f"{tag}: unknown check kind {kind!r}")
    print(f"cells {len(rows)}, facilities {len(facs)}, needs {len(needs)}, problems {len(bad)}")
    for b in bad:
        print("  " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
