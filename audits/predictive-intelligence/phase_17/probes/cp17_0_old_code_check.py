"""CP17-0 (PI-D-094): the three new tests must fail on the frozen first-pass code 3d2089b. The old code is exported into a
temporary folder with the current test file (so an old-code write lands in the temporary copy, never in the checkout).

    python -B cp17_0_old_code_check.py OUT.json
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
OLD = "3d2089b"
TESTS = ["test_cp17_0_a_state_directory_inside_the_repository_but_outside_data_private_is_refused",
         "test_cp17_0_a_serve_state_change_within_the_hour_is_material",
         "test_cp17_0_any_failure_importing_the_package_leaves_the_scout_and_analyze_untouched"]


def main(out: str) -> int:
    with tempfile.TemporaryDirectory(prefix="p17_cp0_") as td:
        root = Path(td)
        tar = subprocess.run(["git", "-C", str(REPO), "archive", OLD, "memelab", "tests", "audits/predictive-intelligence/phase_16/registry",
                              "audits/predictive-intelligence/phase_13/artifacts", "audits/predictive-intelligence/phase_07/artifacts"],
                             capture_output=True, check=True).stdout
        tarfile.open(fileobj=io.BytesIO(tar)).extractall(root, filter="data")
        (root / "data" / "state").mkdir(parents=True)
        (root / "inbox").mkdir()
        (root / "state").mkdir()
        (root / "tests/test_predictive_integration.py").write_text((REPO / "tests/test_predictive_integration.py").read_text())
        res = {}
        for t in TESTS:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", f"tests/test_predictive_integration.py::{t}", "-q", "-p",
                                "no:cacheprovider"], cwd=root, capture_output=True, text=True)
            res[t] = {"exit": r.returncode, "failed_on_old_code": r.returncode != 0, "last_line": r.stdout.strip().splitlines()[-1]}
    rep = {"old_code": OLD, "tests": res, "all_fail_on_old_code": all(v["failed_on_old_code"] for v in res.values())}
    Path(out).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"all_fail_on_old_code": rep["all_fail_on_old_code"]}))
    return 0 if rep["all_fail_on_old_code"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
