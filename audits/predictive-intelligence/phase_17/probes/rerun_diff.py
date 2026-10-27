"""CP17-1 (PI-D-096): what changed in the recorded outputs between two commits' runs. Compares the committed smoke files at
OLD_REF with the files of a new run (a folder), JSON pointer by pointer; a difference under a key that holds a capture time,
pass id, latency, wall time or file hash is volatile, every other difference is listed for an explanation.

    python -B rerun_diff.py OLD_REF NEW_DIR OUT.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SMOKE = "audits/predictive-intelligence/phase_17/smoke"
FILES = ["REAL_PATH_SMOKE.json", "REAL_EXPORT_REPLAY.json", "TRACE_EXAMPLES.json", "FIXTURE_E2E.json", "REAL_SCOUT_SECTION.md"]
VOLATILE = ("capture", "pass_id", "pass_record", "latency", "wall", "file_sha", "state_files", "generated", "time_utc")


def _volatile(path: str) -> bool:
    k = path.split("/")[-1].split("[")[0]
    return any(v in k for v in VOLATILE) or k.endswith("_s") or k.endswith("_at")


def _walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            _walk(a.get(k, "<absent>"), b.get(k, "<absent>"), f"{path}/{k}", out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            _walk(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append(path)


def main(old: str, new: str, outp: str) -> int:
    rep = {"old_ref": old, "files": {}}
    for f in FILES:
        o = subprocess.run(["git", "-C", str(REPO), "show", f"{old}:{SMOKE}/{f}"], capture_output=True, text=True, check=True).stdout
        n = (Path(new) / f).read_text()
        if not f.endswith(".json"):
            ol, nl = o.splitlines(), n.splitlines()
            rep["files"][f] = {"byte_equal": o == n, "lines_old": len(ol), "lines_new": len(nl),
                               "removed": [x for x in ol if x not in nl], "added": [x for x in nl if x not in ol]}
            continue
        d = []
        _walk(json.loads(o), json.loads(n), "", d)
        vol = [p for p in d if _volatile(p)]
        rep["files"][f] = {"byte_equal": o == n, "volatile_differences": len(vol), "non_volatile_differences": [p for p in d if p not in vol]}
    Path(outp).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({f: (v["byte_equal"], len(v.get("non_volatile_differences", v.get("added", [])))) for f, v in rep["files"].items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
