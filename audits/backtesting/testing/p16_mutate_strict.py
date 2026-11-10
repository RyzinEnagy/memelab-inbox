"""Phase 16 audit variant of mutate.py: same copy-and-mutate procedure, but it classifies HOW each mutation was caught.
ASSERTION = a test assertion failed (the behavior was checked); CRASH = the mutated code raised an unrelated error
(TypeError, NameError, SyntaxError ...), which proves less. Usage: python3 audits/backtesting/testing/p16_mutate_strict.py <set.json> [...]
Exit 0 always (it is a classifier, not a gate)."""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ENV = {**os.environ, "MEMELAB_HISTORY_REPO": str(ROOT)}
pat = shutil.ignore_patterns(".git", "__pycache__", "*.sqlite-shm", "*.sqlite-wal", "workplans")


def _ign(d, names):
    out = set(pat(d, names))
    if Path(d).resolve() == (ROOT / "data").resolve():
        out.add("backtest")
    return out


summary = {}
with tempfile.TemporaryDirectory() as td:
    base = Path(td) / "repo"
    shutil.copytree(ROOT, base, ignore=_ign)
    for setf in sys.argv[1:]:
        muts = json.load(open(setf))
        res = {"ASSERTION": [], "CRASH": [], "SURVIVED": [], "NOT_APPLICABLE": []}
        for m in muts:
            f = base / m["file"]; src = f.read_text()
            if m["old"] not in src:
                res["NOT_APPLICABLE"].append(m["id"]); continue
            f.write_text(src.replace(m["old"], m["new"], 1))
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "--tb=line", *m["tests"]], cwd=base, capture_output=True, text=True, env=ENV)
            f.write_text(src)
            if r.returncode == 0:
                res["SURVIVED"].append(m["id"]); continue
            out = r.stdout + r.stderr
            errs = re.findall(r"\b([A-Z][A-Za-z]*(?:Error|Exception))\b", out)
            kinds = set(errs) - {"AssertionError"}
            if "AssertionError" in errs or re.search(r"\bassert\b", out) or not kinds or any(k in ("LeakageError", "ClockError", "ArithmeticError", "OffAllowlist", "ScheduleNotApproved", "MalformedBars") for k in kinds):
                res["ASSERTION"].append(m["id"])
            else:
                res["CRASH"].append(f"{m['id']} ({','.join(sorted(kinds))})")
        summary[Path(setf).name] = {k: v for k, v in res.items()} | {"counts": {k: len(v) for k, v in res.items()}}
print(json.dumps(summary, indent=1))
