"""Phase 04: clean install, smoke and uninstall of the research lock in a throwaway venv, offline (`unshare -n`).

Steps: (1) new venv; record `pip freeze` and a manifest of every file under site-packages with its sha256; (2) install
docs/predictive-intelligence/locks/research-py313.txt with the lab's flags from a local wheelhouse (no index, no network);
(3) smoke: the bake-off approaches LR_SKLEARN, LGBM and COX_LIFELINES on the challenge, offline; (4) `pip uninstall -y` every
locked name; (5) the freeze and the manifest must equal step 1. Also records the system interpreter's `pip freeze` sha256,
which this phase never changes. The manifest lists directories as well as files (Phase 04 skeptic m8: pip leaves a namespace
directory such as `mpl_toolkits/` behind when it is empty, which a file-only manifest did not see); `rollback_clean` requires the
file manifest to match, and `rollback_clean_with_dirs` also requires no leftover directory. The documented rollback is deleting the
venv, which leaves nothing.

    python rollback_demo.py WHEELHOUSE OUT.json
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))
from memelab.predictive import runtime as R  # noqa: E402

LOCK = REPO / "docs/predictive-intelligence/locks/research-py313.txt"
BAKEOFF = Path(__file__).resolve().parent / "bakeoff.py"


def run(cmd, offline=True, **kw):
    if offline:
        cmd = ["unshare", "-n", *cmd]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=1800, **kw)


def manifest(venv: Path) -> dict:
    sp = next(venv.glob("lib/python3.*/site-packages"))
    files = sorted(p for p in sp.rglob("*") if p.is_file())
    dirs = sorted(str(p.relative_to(sp)) for p in sp.rglob("*") if p.is_dir() and "__pycache__" not in p.parts)
    h = hashlib.sha256()
    for p in files:
        h.update(str(p.relative_to(sp)).encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    return {"files": len(files), "sha256": h.hexdigest(), "dirs": len(dirs),
            "dirs_sha256": hashlib.sha256("\n".join(dirs).encode()).hexdigest(), "_dirs": dirs}


def main(wheelhouse: str, out: str) -> None:
    names = [m.group(1) for m in re.finditer(r"^([A-Za-z0-9._-]+)==", LOCK.read_text(), re.M)]
    sysfreeze = subprocess.run([sys.executable, "-m", "pip", "freeze", "--disable-pip-version-check"], capture_output=True, text=True).stdout
    res = {"lock": str(LOCK.relative_to(REPO)), "lock_sha256": hashlib.sha256(LOCK.read_bytes()).hexdigest(),
           "check_lock": R.check_lock(LOCK.read_text()), "packages": len(names),
           "system_pip_freeze_sha256": hashlib.sha256(sysfreeze.encode()).hexdigest()}
    with tempfile.TemporaryDirectory() as td:
        venv = Path(td) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        py = str(venv / "bin/python")
        res["pip_version"] = subprocess.run([py, "-m", "pip", "--version"], capture_output=True, text=True).stdout.split(" from ")[0]
        f0 = run([py, "-m", "pip", "freeze"]).stdout
        m0 = manifest(venv)
        inst = run([py, "-m", "pip", "install", "--disable-pip-version-check", *R.INSTALL_FLAGS, "--no-index", "--find-links", wheelhouse,
                    "-r", str(LOCK)])
        res["install"] = {"exit": inst.returncode, "tail": (inst.stdout + inst.stderr).strip().splitlines()[-1:]}
        f1 = run([py, "-m", "pip", "freeze"]).stdout
        res["installed_count"] = len([ln for ln in f1.splitlines() if "==" in ln])
        chk = run([py, "-m", "pip", "check"])
        res["pip_check"] = {"exit": chk.returncode, "lines": chk.stdout.strip().splitlines()[:5]}
        smoke = {}
        for a in ("LR_SKLEARN", "LGBM", "COX_LIFELINES", "LR_NUMPY"):
            p = run([py, "-I", "-B", str(BAKEOFF), "challenge", a], env={"PATH": "/usr/bin:/bin", "OMP_NUM_THREADS": "1"})
            try:
                o = json.loads(p.stdout.strip().splitlines()[-1])
                smoke[a] = {"exit": p.returncode, "brier": o.get("brier"), "predictions_sha256": o.get("predictions_sha256")}
            except (ValueError, IndexError):
                smoke[a] = {"exit": p.returncode, "stderr": p.stderr[-300:]}
        res["smoke_offline"] = smoke
        un = run([py, "-m", "pip", "uninstall", "-y", "--disable-pip-version-check", *names])
        res["uninstall"] = {"exit": un.returncode}
        f2 = run([py, "-m", "pip", "freeze"]).stdout
        m2 = manifest(venv)
        d0, d2 = m0.pop("_dirs"), m2.pop("_dirs")
        res["before"] = {"freeze_sha256": hashlib.sha256(f0.encode()).hexdigest(), "freeze_lines": len(f0.splitlines()), **m0}
        res["after_uninstall"] = {"freeze_sha256": hashlib.sha256(f2.encode()).hexdigest(), "freeze_lines": len(f2.splitlines()), **m2}
        same_files = (m0["files"], m0["sha256"]) == (m2["files"], m2["sha256"])
        if not same_files:
            sp = next(venv.glob("lib/python3.*/site-packages"))
            res["leftover_files"] = sorted(str(p.relative_to(sp)) for p in sp.rglob("*") if p.is_file())[:40]
        res["leftover_dirs"] = sorted(set(d2) - set(d0))
        res["missing_dirs"] = sorted(set(d0) - set(d2))
        res["rollback_clean"] = f0 == f2 and same_files
        res["rollback_clean_with_dirs"] = res["rollback_clean"] and not res["leftover_dirs"] and not res["missing_dirs"]
    print(json.dumps({k: res[k] for k in ("install", "installed_count", "smoke_offline", "uninstall", "rollback_clean",
                                          "rollback_clean_with_dirs", "leftover_dirs")}, indent=1))
    Path(out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
