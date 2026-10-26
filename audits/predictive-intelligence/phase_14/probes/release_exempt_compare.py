"""Phase 14: release-audit findings with the old (git REF) and the current EXPLAINED list; everything outside the Phase 14 files must be equal.

    python -B release_exempt_compare.py REF
"""
import importlib.util, json, subprocess, sys, types
REPO = __import__("pathlib").Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
def load(src, name):
    spec = importlib.util.spec_from_loader(name, loader=None); m = importlib.util.module_from_spec(spec)
    m.__file__ = str(REPO / "tools/release_audit.py"); exec(compile(src, m.__file__, "exec"), m.__dict__); return m
new = load(open(str(REPO / "tools/release_audit.py")).read(), "rel_new")
old_src = subprocess.run(["git", "-C", str(REPO), "show", sys.argv[1] + ":tools/release_audit.py"], capture_output=True, text=True).stdout
old = load(old_src, "rel_old")
o_out, o_rev = old.scan_exec(); n_out, n_rev = new.scan_exec()
key = lambda h: (h["path"], h["line"], h["rule"])
newfiles = ("memelab/predictive/behavioral.py", "tests/test_predictive_behavioral.py", "audits/predictive-intelligence/phase_14/")
print(json.dumps({"old_unexplained": sorted(map(key, o_out)), "new_unexplained": sorted(map(key, n_out)),
  "old_reviewed_outside_phase14": len([h for h in o_rev if not h["path"].startswith(newfiles)]),
  "new_reviewed_outside_phase14": len([h for h in n_rev if not h["path"].startswith(newfiles)]),
  "reviewed_equal_outside_phase14": sorted(map(key,[h for h in o_rev if not h["path"].startswith(newfiles)])) == sorted(map(key,[h for h in n_rev if not h["path"].startswith(newfiles)])),
  "new_reviewed_phase14": sorted(map(key,[h for h in n_rev if h["path"].startswith(newfiles)]))}, indent=1))
