"""Phase 11 repair pass 2: the skeptic's counterexample CX-S11 (one mint under two creator values counted as two analogs) against
the first-pass module and the repaired one. Copies the tracked repository to a temporary folder, runs the CX-S11 tests of the
current test file with `memelab/predictive/analog.py` from the first-pass commit (0482a60, unchanged up to fcb76be) and from
HEAD, and writes the result. The first pass must fail, HEAD must pass.

    python -B cx_s11_check.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
FIRST_PASS = "0482a6017d62d32f35f86a2111f3f569096063b4"
TESTS = ["tests/test_predictive_analog.py::test_cx_s11_one_mint_under_two_creator_values_is_one_analog",
         "tests/test_predictive_analog.py::test_a_target_whose_mint_had_another_creator_excludes_that_deployers_other_mints_p14"]


def run(root: Path) -> dict:
    out = {}
    for t in TESTS:
        r = subprocess.run([sys.executable, "-B", "-m", "pytest", t, "-q", "-p", "no:cacheprovider"], cwd=root, capture_output=True, text=True)
        out[t.split("::")[1]] = {"exit": r.returncode, "last": r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""}
    return out


def main() -> int:
    files = subprocess.run(["git", "ls-files", "memelab", "tests"], cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    res = {}
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo"
        for f in files:
            (root / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / f, root / f)
        res["head"] = run(root)
        old = subprocess.run(["git", "show", f"{FIRST_PASS}:memelab/predictive/analog.py"], cwd=REPO, capture_output=True, check=True).stdout
        (root / "memelab/predictive/analog.py").write_bytes(old)
        res["first_pass_0482a60"] = run(root)
    res["pass"] = all(v["exit"] == 0 for v in res["head"].values()) and all(v["exit"] != 0 for v in res["first_pass_0482a60"].values())
    Path(sys.argv[1]).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
