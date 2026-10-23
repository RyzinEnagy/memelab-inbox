"""Mutation harness: copy the repo to a temp dir, apply one textual mutation, run the given tests, expect FAILURE.
Usage: python audits/backtesting/testing/mutate.py <mutations.json>
Each mutation: {"id", "file", "old", "new", "tests"}. Exit 0 only if every mutation is caught (tests fail) and the
unmutated run passes."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
muts = json.load(open(sys.argv[1]))
ok = True
with tempfile.TemporaryDirectory() as td:
    base = Path(td) / "repo"
    pat = shutil.ignore_patterns(".git", "__pycache__", "*.sqlite-shm", "*.sqlite-wal", "workplans")   # audits are copied: some tests read committed evidence
    def _ign(d, names):
        out = set(pat(d, names))
        if Path(d).resolve() == (ROOT / "data").resolve():
            out.add("backtest")      # local research DB and raw shards (may be in use by a running fetch)
        return out
    shutil.copytree(ROOT, base, ignore=_ign)
    tests = sorted({t for m in muts for t in m["tests"]})
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests], cwd=base, capture_output=True, text=True)
    print(f"baseline (unmutated): exit {r.returncode} :: {r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]}")
    ok &= r.returncode == 0
    for m in muts:
        f = base / m["file"]; src = f.read_text()
        if m["old"] not in src:
            print(f"[{m['id']}] MUTATION NOT APPLICABLE (old text not found)"); ok = False; continue
        f.write_text(src.replace(m["old"], m["new"], 1))
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *m["tests"]], cwd=base, capture_output=True, text=True)
        caught = r.returncode != 0
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        print(f"[{m['id']}] {'CAUGHT' if caught else 'SURVIVED'} :: {last}")
        ok &= caught
        f.write_text(src)
print("RESULT:", "all mutations caught" if ok else "FAILURE")
sys.exit(0 if ok else 1)
