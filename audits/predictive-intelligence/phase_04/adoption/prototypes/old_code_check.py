"""Phase 04 repair: show that the new tests fail on the code the skeptic reviewed. Copies the working tree (without .git), puts back
`memelab/predictive/runtime.py`, `memelab/predictive/contract.py` and the prototype `core_numpy.py` as they were at the first-pass
commit, and runs the new tests against them. Every repaired finding must show up as a failing test id.

    python old_code_check.py OUT.json
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
OLD = "4a19d7135db809ed30f8bb5ce2390a800d1f92c3"
PROTO = "audits/predictive-intelligence/phase_04/adoption/prototypes/core_numpy.py"


# Names the new tests reference that the old module did not have. They reproduce the old behaviour (no guard before pip, no
# bake-off guard, no fixture check) so that the tests can be collected and each repaired finding shows up as its own failure.
SHIM = """

# ---- shim added by old_code_check.py (not part of the reviewed code) ----
BAD_RESPONSE = "BAD_RESPONSE"
NOT_CONTAINED = ()
FINGERPRINT_ALGO = "sha256"
NORMALIZATION = "whitespace collapsed, lines under 8 characters dropped (runtime.normalized_lines)"
BAKEOFF_ONLY = "BAKEOFF_ONLY"


class InstallRefused(ValueError):
    pass


def install_argv(lock_path, *, python="python", wheel_hashes=None):
    return [python, "-m", "pip", "install", *INSTALL_FLAGS, "-r", str(lock_path)]     # the old route: flags only


def lock_hashes(text):
    return {}


def fingerprint_spec():
    return {"shingle_lines": SHINGLE_LINES, "winnow_window": WINNOW_WINDOW, "hash": f"sha256 hex prefix {HASH_HEX}",
            "normalization": NORMALIZATION}


def refuse_bakeoff_labels(rows=(), path=None):
    return None
"""


def main(out: str) -> None:
    res = {"old_commit": OLD}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "repo"
        shutil.copytree(REPO, tmp, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.sqlite-shm", "*.sqlite-wal"))
        for f in ("memelab/predictive/runtime.py", "memelab/predictive/contract.py", PROTO):
            old = subprocess.run(["git", "-C", str(REPO), "show", f"{OLD}:{f}"], capture_output=True, text=True, check=True).stdout
            (tmp / f).write_text(old + (SHIM if f.endswith("runtime.py") else ""))
        for name, target in (("runtime_tests", "tests/test_predictive_runtime.py"), ("prototype_tests", PROTO.replace("core_numpy.py", "test_core_numpy.py"))):
            p = subprocess.run([sys.executable, "-B", "-m", "pytest", target, "-q", "-p", "no:cacheprovider", "-rf"], cwd=tmp,
                               capture_output=True, text=True, timeout=900)
            failed = sorted(set(re.findall(r"^FAILED (.+?)(?: - .*)?$", p.stdout, re.M)))
            res[name] = {"exit": p.returncode, "summary": (p.stdout.strip().splitlines() or [""])[-1], "failed_ids": failed}
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: (v if k == "old_commit" else {"exit": v["exit"], "summary": v["summary"], "n_failed": len(v["failed_ids"])})
                      for k, v in res.items()}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
