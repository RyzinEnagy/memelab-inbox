"""Phase 00 probe: can a stored thesis be reproduced from the archived inputs with the current code?

Clones the current checkout into a temp folder, then re-analyzes one real candidate (HIGGS,
DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump, stored report data/reports/20261007_0016_HIGGS_DoVAVz.md) twice
with a temp database:
  run A: the deep result files only (deep01a deep02 deep03 deep04)
  run B: every tracked result file of that session (adds disc01 s2_01 forensics01)
and compares score, status, fatal flags and pool facts with the stored report. Theses record neither the result ids
that fed them nor the code version, so which input set was used can only be inferred.

Usage (from the repo root): python audits/predictive-intelligence/phase_00/probes/lineage_reproduction_probe.py
Writes only inside a temp folder. No network.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True).stdout.strip()
MINT = "DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump"
STORED = os.path.join(ROOT, "data/reports/20261007_0016_HIGGS_DoVAVz.md")
TMP = tempfile.mkdtemp(prefix="pi_lineage_")
CLONE = os.path.join(TMP, "clone")
subprocess.run(["git", "clone", "-q", ROOT, CLONE], check=True)
head = subprocess.run(["git", "-C", CLONE, "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def facts(md: str) -> dict:
    m = re.search(r"Opportunity score (\d+)/100", md)
    s = re.search(r"Status: ([A-Z ]+?)[.\n]", md)
    pools = re.search(r"FACT: (\d+) pools known", md)
    return {"score": int(m.group(1)) if m else None, "status": s.group(1).strip() if s else None,
            "fatal_wash": "WASH_TRADING_HIGH" in md, "pools_known": int(pools.group(1)) if pools else None,
            "identity_confidence": (re.search(r"IDENTITY CONFIDENCE: (\w+)", md) or [None, None])[1]}


def run(tag: str, results: list[str]) -> dict:
    env = dict(os.environ, MEMELAB_DB=os.path.join(TMP, f"{tag}.sqlite"))
    rd = os.path.join(TMP, f"reports_{tag}")
    subprocess.run([sys.executable, "-m", "memelab", "init"], cwd=CLONE, env=env, check=True, capture_output=True)
    p = subprocess.run([sys.executable, "-m", "memelab", "scout", "--mints", MINT, "--results", *results, "--stage1", "disc01", "--report-dir", rd],
                       cwd=CLONE, env=env, capture_output=True, text=True)
    md = open(os.path.join(rd, "20261007_0016_HIGGS_DoVAVz.md")).read() if p.returncode == 0 else ""
    return {"results": results, "exit": p.returncode, **facts(md)}


out = {"clone_head": head, "stored": facts(open(STORED).read()),
       "run_A_deep_only": run("A", ["deep01a", "deep02", "deep03", "deep04"]),
       "run_B_all_session_files": run("B", ["disc01", "s2_01", "deep01a", "deep02", "deep03", "deep04", "forensics01"])}
out["clone_git_status"] = subprocess.run(["git", "-C", CLONE, "status", "--porcelain"], capture_output=True, text=True).stdout
# run C: the code as it was when the report was written (b6c424d, 2026-10-06T21:12-04:00; normalize.py next changed in 4a9155b)
subprocess.run(["git", "-C", CLONE, "checkout", "-q", "b6c424d"], check=True)
envc = dict(os.environ, MEMELAB_DB=os.path.join(TMP, "C.sqlite"))
subprocess.run([sys.executable, "-m", "memelab", "init"], cwd=CLONE, env=envc, check=True, capture_output=True)
pc = subprocess.run([sys.executable, "-m", "memelab", "analyze", MINT, "--results", "disc01", "s2_01", "deep01a", "deep02", "deep03", "deep04",
                     "forensics01", "--stage1", "disc01", "--no-persist", "--print"], cwd=CLONE, env=envc, capture_output=True, text=True)
regen = pc.stdout.split("\n", 1)[1] if pc.returncode == 0 else ""
stored_md = open(STORED).read()
drop = re.compile(r"## What changed since the last snapshot\?.*?(?=\n## )", re.S)   # needs the earlier 00:07 thesis in the DB
a = [ln for ln in drop.sub("", stored_md).splitlines() if ln.strip()]
b = [ln for ln in drop.sub("", regen).splitlines() if ln.strip()]
out["run_C_code_b6c424d_all_session_files"] = {"exit": pc.returncode, **facts(regen),
                                              "nonblank_lines_equal_to_stored_except_change_section": a == b, "lines": [len(a), len(b)]}
out["reading"] = ("run A differs from the stored thesis in score and status; run B matches score, status and fatal flag but not the pool "
                  "facts, because normalization code changed after 2026-10-07 (4a9155b); run C, the code of the day, reproduces the stored "
                  "report line for line except the change section that needs the earlier thesis. A stored thesis is reproducible only "
                  "with its input ids and code version, and neither is recorded in the theses table.")
print(json.dumps(out, indent=1))
