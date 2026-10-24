"""Phase 05 regression of the lab's original CLI: the same commands in two fresh clones (before and after), temp databases,
no network, outputs compared byte for byte after masking the report file names' time stamp.

    python -B cli_regression.py REF_BEFORE REF_AFTER OUT.json

Commands (the Phase 00 baseline set): --help; init; analyze HIGGS with the deep results and --no-persist; analyze with the full
result set; scout into a report folder; catalyst fc-health. Each runs in its clone with MEMELAB_DB in a temp folder. The
network is cut with `unshare -n` when available.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MINT = "DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump"
CMDS = [
    ["--help"],
    ["init"],
    ["analyze", MINT, "--results", "deep01a", "deep02", "deep03", "deep04", "--stage1", "disc01", "--no-persist"],
    ["analyze", MINT, "--results", "disc01", "s2_01", "deep01a", "deep02", "deep03", "deep04", "forensics01", "--no-persist"],
    ["scout", "--mints", MINT, "--results", "deep01a", "deep02", "deep03", "deep04", "--stage1", "disc01", "--report-dir", "REPORTS"],
    ["catalyst", "fc-health"],
]


def run_side(ref: str, root: Path) -> dict:
    clone = root / "clone"
    subprocess.run(["git", "clone", "-q", "--no-local", str(REPO), str(clone)], check=True)
    subprocess.run(["git", "-C", str(clone), "checkout", "-q", ref], check=True)
    env = {k: v for k, v in os.environ.items() if not k.upper().endswith(("_KEY", "_TOKEN"))}
    env.update(MEMELAB_DB=str(root / "db" / "lab.sqlite"), PYTHONDONTWRITEBYTECODE="1")
    (root / "db").mkdir()
    reports = root / "reports"
    reports.mkdir()
    pre = ["unshare", "-n"] if shutil.which("unshare") and subprocess.run(["unshare", "-n", "true"]).returncode == 0 else []
    out = []
    for cmd in CMDS:
        c = [x if x != "REPORTS" else str(reports) for x in cmd]
        p = subprocess.run(pre + [sys.executable, "-m", "memelab", *c], cwd=clone, env=env, capture_output=True)
        text = p.stdout.decode(errors="replace").replace(str(root), "ROOT")
        text = re.sub(r"\d{8}_\d{4}_", "STAMP_", text)
        out.append({"cmd": " ".join(cmd), "exit": p.returncode, "stdout_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "stdout_head": text.splitlines()[:2]})
    files = {}
    for f in sorted(reports.iterdir()):
        body = re.sub(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?( ?UTC|Z)?", "TIME", f.read_text(errors="replace"))
        files[re.sub(r"^\d{8}_\d{4}_", "STAMP_", f.name)] = hashlib.sha256(body.encode()).hexdigest()
    status = subprocess.run(["git", "-C", str(clone), "status", "--porcelain"], capture_output=True, text=True).stdout
    return {"ref": ref, "head": subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True,
                                                text=True).stdout.strip(), "network_cut": bool(pre), "commands": out,
            "report_files": files, "clone_status_after": status.splitlines()}


def main(before: str, after: str, out: str) -> None:
    with tempfile.TemporaryDirectory() as d:
        a = run_side(before, Path(d) / "a")
        b = run_side(after, Path(d) / "b")
    same_cmd = [x["stdout_sha256"] == y["stdout_sha256"] and x["exit"] == y["exit"] for x, y in zip(a["commands"], b["commands"])]
    rep = {"before": a, "after": b, "commands_identical": all(same_cmd), "per_command": same_cmd,
           "reports_identical": a["report_files"] == b["report_files"] and bool(a["report_files"])}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("commands_identical", "per_command", "reports_identical")}
                     | {"exits": [c["exit"] for c in b["commands"]], "network_cut": b["network_cut"]}))


if __name__ == "__main__":
    main(*sys.argv[1:4])
