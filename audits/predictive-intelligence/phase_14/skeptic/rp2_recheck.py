"""Repair pass 2: run the skeptic's scripts against the first-pass code (git archive of c59c494 into a temporary folder) and the
repaired working tree, and record what each prints. Loopback only; the egress probe runs inside `unshare -n` with a lo alias.

    python -B rp2_recheck.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def run(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True, cwd="/tmp", timeout=600)
    keep = [ln[:240] for ln in p.stdout.splitlines() if ln.startswith(("ATTACK", "CX-S14", "E1", "E2", "E3", "E4", "{", "[")) or "forwarded=" in ln]
    return {"exit": p.returncode, "lines": keep}


def main(out: str) -> int:
    res = {}
    with tempfile.TemporaryDirectory(prefix="p14_fp_") as td:
        fp = Path(td)
        subprocess.run(f"git -C {REPO} archive c59c494 memelab tests audits/predictive-intelligence/phase_13/calibration/FORECAST_RESULTS_DEV.jsonl"
                       f" | tar -x -C {fp}", shell=True, check=True)
        Path("/tmp/claude-0/sk14").mkdir(parents=True, exist_ok=True)
        for name, tree in (("first_pass_c59c494", fp), ("repaired_working_tree", REPO)):
            res[name] = {
                "cx14_monitor_reversal": run([sys.executable, "-B", str(HERE / "cx14_monitor_reversal.py"), str(tree)]),
                "attacks_rp2": run([sys.executable, "-B", str(HERE / "p14_attacks_rp2.py"), str(tree)]),
                "meter": run([sys.executable, "-B", str(HERE / "p14_meter.py"), str(tree)]),
                "egress_in_netns": run(["/usr/bin/unshare", "-n", sys.executable, "-B", str(HERE / "p14_egress.py"), str(tree)]),
            }
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: {kk: vv["exit"] for kk, vv in v.items()} for k, v in res.items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
