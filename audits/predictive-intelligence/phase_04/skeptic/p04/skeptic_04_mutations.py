"""Skeptic 04: own mutations of memelab/predictive/runtime.py (temp copy; repository untouched). A mutation SURVIVES when
tests/test_predictive_runtime.py still passes. For P31 mutations the script also runs the pinned MiroFish clone through the
mutated gate (positive control the suite lacks).
    python -I -B skeptic_04_mutations.py REPO MIROFISH_CLONE OUT.json
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
repo, mf, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
M = [
 ("P31 normalization drift: lines lower-cased (fixture built case-sensitive)",
  'out.append(s)\n    return out', 'out.append(s.lower())\n    return out'),
 ("P31 shingle hash changed to sha1 prefix (fixture is sha256)",
  'return [hashlib.sha256("\\n".join(ls[i:i + SHINGLE_LINES]).encode()).hexdigest()[:HASH_HEX]',
  'return [hashlib.sha1("\\n".join(ls[i:i + SHINGLE_LINES]).encode()).hexdigest()[:HASH_HEX]'),
 ("P31 shingle length 4 -> 5", 'SHINGLE_LINES, WINNOW_WINDOW, HASH_HEX = 4, 12, 12', 'SHINGLE_LINES, WINNOW_WINDOW, HASH_HEX = 5, 12, 12'),
 ("breaker counts only network failures",
  'self.failures = 0 if st["state"] == AVAILABLE else self.failures + 1',
  'self.failures = self.failures + 1 if st["state"] == NETWORK_UNAVAILABLE else 0'),
 ("call and cost caps no longer abstain",
  'CALL_CAP_REACHED: "SOURCE_STALE", COST_CAP_REACHED: "SOURCE_STALE"', 'CALL_CAP_REACHED: None, COST_CAP_REACHED: None'),
 ("pace measured from the call start instead of its end (shorter waits after slow calls)",
  '        self.last = self.clock()\n        self.failures', '        self.failures'),
 ("ImportError becomes COMPONENT_ERROR",
  'return _state(name, DEPENDENCY_MISSING, type(e).__name__), None', 'return _state(name, COMPONENT_ERROR, type(e).__name__), None'),
 ("check_lock: banned options only at line start",
  'if any(low.startswith(o.strip()) or f" {o}" in f" {low}" for o in _BANNED_OPTIONS):',
  'if any(low.startswith(o.strip()) for o in _BANNED_OPTIONS):'),
 ("simulation: adapter run accepted when llm_actions key missing",
  'int(run.get("llm_actions") or 0) <= 0', 'int(run.get("llm_actions", 1) or 0) <= 0'),
 ("guarded swallows only Exception subclasses of ValueError/RuntimeError",
  '    except Exception as e:  # noqa: BLE001', '    except (ValueError, RuntimeError, MemoryError) as e:  # noqa: BLE001'),
]
def run(tmp):
    p = subprocess.run([sys.executable, "-B", "-m", "pytest", "tests/test_predictive_runtime.py", "-q", "-p", "no:cacheprovider", "-x"], cwd=tmp, capture_output=True, text=True, timeout=600)
    return p.returncode, (p.stdout.strip().splitlines() or [""])[-1]
def mf_hits(tmp):
    code = ("import sys,json;from pathlib import Path;sys.path.insert(0,'.');from memelab.predictive import runtime as R;"
            "fp=R.load_fingerprints('tests/fixtures/predictive/copyleft_fingerprints.json');"
            f"fs=[p for p in Path('{mf}').rglob('*') if p.is_file() and p.suffix in R.CODE_SUFFIXES and '.git' not in p.parts];"
            "print(len({x['path'] for x in R.copyleft_findings(fs,fp) if x['kind']=='fingerprint'}))")
    return subprocess.run([sys.executable, "-I", "-B", "-c", code], cwd=tmp, capture_output=True, text=True).stdout.strip()
res = []
with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    shutil.copytree(repo / "memelab", tmp / "memelab", ignore=shutil.ignore_patterns("__pycache__"))
    (tmp / "tests").mkdir()
    shutil.copy(repo / "tests/test_predictive_runtime.py", tmp / "tests/")
    shutil.copytree(repo / "tests/fixtures", tmp / "tests/fixtures")
    shutil.copytree(repo / "docs/predictive-intelligence/locks", tmp / "docs/predictive-intelligence/locks")
    for r in ("tools", "bridge", "skills"):
        if (repo / r).exists():
            shutil.copytree(repo / r, tmp / r, ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
    tgt = tmp / "memelab/predictive/runtime.py"; orig = tgt.read_text()
    res.append({"mutation": "baseline", "tests": run(tmp), "mirofish_files_flagged": mf_hits(tmp)})
    for name, a, b in M:
        assert orig.count(a) == 1, name
        tgt.write_text(orig.replace(a, b))
        code, line = run(tmp)
        r = {"mutation": name, "tests_exit": code, "result": line, "SURVIVED": code == 0}
        if name.startswith("P31"):
            r["mirofish_files_flagged_under_mutation"] = mf_hits(tmp)
        res.append(r)
    tgt.write_text(orig)
out.write_text(json.dumps(res, indent=1) + "\n")
for r in res: print(json.dumps(r))
