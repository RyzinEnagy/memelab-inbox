"""Skeptic Phase 15: own mutations of scenario_eval.py (not in the phase's 45), run against both Phase 15 test files on a temp
copy (the clone is never edited). Usage: python -I p15_own_mutations.py REPO OUT.json"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
repo, outp = Path(sys.argv[1]), sys.argv[2]
MP = "memelab/predictive/scenario_eval.py"
MUT = [
    ("X1 event minimum 100 -> 99", "MIN_EVENTS = 100", "MIN_EVENTS = 99"),
    ("X2 blind check case sensitive", 'r"label_observed_at|event_observed)$", re.I)', 'r"label_observed_at|event_observed)$")'),
    ("X3 label_observed_at accepted", 'r"label_observed_at|event_observed)$"', 'r"event_observed)$"'),
    ("X4 SIMULATION_NOT_AVAILABLE codable", 'CODABLE_STATUSES = ("RULES_RAN", "SIMULATION_RAN")',
     'CODABLE_STATUSES = ("RULES_RAN", "SIMULATION_RAN", "SIMULATION_NOT_AVAILABLE")'),
    ("X5 warned minimum 20 -> 10", 'MIN_WARNED = C.ACCEPTANCE["min_bin_events"]', 'MIN_WARNED = 10'),
    ("X6 p_down uses >=", '"p_down": (1 + int(np.sum(null <= obs)))', '"p_down": (1 + int(np.sum(null >= obs)))'),
    ("X7 days gate <=", 'if days < a["min_effective_days"]:', 'if days <= a["min_effective_days"]:'),
    ("X8 lead time in minutes", 'float(r["lead_s"]) / 3600.0', 'float(r["lead_s"]) / 60.0'),
    ("X9 WORSE without sign", 'if lift is not None and lift < 0 and p_down_holm', 'if lift is not None and p_down_holm'),
    ("X10 shrink toward 0.5", 'c["p"] = (c["k"] + B.M_SHRINK * b0) / (c["n"] + B.M_SHRINK)',
     'c["p"] = (c["k"] + B.M_SHRINK * 0.5) / (c["n"] + B.M_SHRINK)'),
    ("X11 unseen stratum gets 0.5", 'else card["b0"]', 'else 0.5'),
    ("X12 correction at alpha passes", "if any(p >= ALPHA for p in known):", "if any(p > ALPHA for p in known):"),
    ("X13 NO_EVENT labels in per-label", 'if s["expect"] == "EVENT" and s["label"] not in', 'if s["label"] not in'),
    ("X14 rules beat B2 by 0.05 slack", "and b <= b2):", "and b <= b2 + 0.05):"),
]
src = (repo / MP).read_text()
res = []
with tempfile.TemporaryDirectory(prefix="sk15_mut_") as td:
    root = Path(td)
    for d in ("memelab", "tests"):
        shutil.copytree(repo / d, root / d, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(repo / "audits", root / "audits", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(repo / ".git", root / ".git")
    cmd = [sys.executable, "-B", "-m", "pytest", "tests/test_predictive_scenario_eval.py", "tests/test_predictive_phase15_outputs.py",
           "-q", "-x", "-p", "no:cacheprovider"]
    base = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    assert base.returncode == 0, base.stdout[-1500:]
    for name, a, b in MUT:
        if src.count(a) != 1:
            res.append({"mutation": name, "caught": None, "note": f"fragment count {src.count(a)}"}); continue
        (root / MP).write_text(src.replace(a, b))
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=900)
        failed = [ln.split(" ")[1] for ln in r.stdout.splitlines() if ln.startswith("FAILED")]
        res.append({"mutation": name, "caught": r.returncode != 0, "first_failure": failed[0] if failed else r.stdout.strip().splitlines()[-1]})
    (root / MP).write_text(src)
rep = {"mutations": len(res), "caught": sum(1 for r in res if r["caught"]), "survivors": [r["mutation"] for r in res if r["caught"] is False],
       "results": res}
Path(outp).write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps({k: rep[k] for k in ("mutations", "caught", "survivors")}, indent=1))
