"""CP18-0 (PI-D-099): the change-control tests must fail on the frozen code 96c4445. Copies the tracked memelab and tests trees
plus the committed artifacts the tests read into a temporary folder, puts back 96c4445:memelab/predictive/reports.py, runs the
CP18-0 tests and writes which of them fail. The checkout is never edited.

    python -B cp18_0_old_code_check.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
OLD = "96c4445"
RPT = "memelab/predictive/reports.py"
TEST = "tests/test_predictive_reports.py"
A = "audits/predictive-intelligence"
EXTRA_DIRS = [f"{A}/phase_16/registry", f"{A}/phase_13/artifacts", f"{A}/phase_07/artifacts"]


def main(out: str) -> int:
    old = subprocess.run(["git", "show", f"{OLD}:{RPT}"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    res = {}
    with tempfile.TemporaryDirectory(prefix="p18_cp0_") as td:
        root = Path(td)
        for d in ("memelab", "tests"):
            shutil.copytree(REPO / d, root / d, ignore=shutil.ignore_patterns("__pycache__"))
        for d in EXTRA_DIRS:
            shutil.copytree(REPO / d, root / d)
        cmd = [sys.executable, "-B", "-m", "pytest", TEST, "-q", "-p", "no:cacheprovider", "-k", "cp18_0"]
        new = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        (root / RPT).write_text(old)
        prev = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        res = {"old_code": OLD, "tests": "-k cp18_0", "on_new_code": new.stdout.strip().splitlines()[-1],
               "on_old_code": prev.stdout.strip().splitlines()[-1],
               "failing_on_old_code": sorted(ln.split(" ")[1].split("::")[-1] for ln in prev.stdout.splitlines() if ln.startswith("FAILED"))}
    Path(out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
