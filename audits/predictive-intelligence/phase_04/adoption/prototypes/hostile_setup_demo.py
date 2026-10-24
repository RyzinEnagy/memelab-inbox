"""Phase 04 (P32): the lab's install route against a hostile package, in a throwaway venv, offline (`unshare -n`).

Builds, in a temporary directory, a source distribution `p04evil-1.0.tar.gz` whose setup.py writes a marker file when it runs
(stand-in for a destructive or exfiltrating install script; it does nothing else), and a harmless wheel `p04good-1.0`. Then:

  A. control: plain `pip install --no-index --find-links WH p04evil` builds the sdist and runs setup.py (marker written), which
     shows the threat is real;
  B. the lab route `pip install --require-hashes --only-binary=:all: --no-deps --no-index --find-links WH -r lock` with the
     sdist's correct sha256 in the lock: refused, setup.py never runs (marker absent);
  C. the lab route with a wheel whose hash differs from the lock: refused;
  D. runtime.check_lock and runtime.verify_artifact on the same files;
  E. the Phase 04 skeptic's counterexample (M1): the sdist's line with an environment marker and a trailing
     `--only-binary=:none:`. As a control, pip run directly with the lab's flags builds it and runs setup.py (the flags alone
     are not enough); the lab route, `runtime.install_argv`, refuses the lock before pip is started, and `check_lock` names
     the option. Same for a trailing `--hash=sha512:` that would admit a file whose sha256 is not locked.

    python hostile_setup_demo.py OUT.json
"""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))
from memelab.predictive import runtime as R  # noqa: E402

SETUPTOOLS_WHEEL_DIR = "/home/claude/pi_research/p04/wheels_setuptools"


def make_sdist(wh: Path, marker: Path) -> Path:
    setup = (f"from pathlib import Path\nPath({str(marker)!r}).write_text('setup.py ran')\n"
             "from setuptools import setup\nsetup(name='p04evil', version='1.0', py_modules=[])\n")
    p = wh / "p04evil-1.0.tar.gz"
    with tarfile.open(p, "w:gz") as t:
        for name, body in (("p04evil-1.0/setup.py", setup),
                           ("p04evil-1.0/PKG-INFO", "Metadata-Version: 2.1\nName: p04evil\nVersion: 1.0\n")):
            data = body.encode()
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            t.addfile(ti, io.BytesIO(data))
    return p


def make_wheel(wh: Path) -> Path:
    p = wh / "p04good-1.0-py3-none-any.whl"
    files = {"p04good.py": "VALUE = 1\n",
             "p04good-1.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: p04good\nVersion: 1.0\n",
             "p04good-1.0.dist-info/WHEEL": "Wheel-Version: 1.0\nGenerator: p04\nRoot-Is-Purelib: true\nTag: py3-none-any\n"}
    rec = []
    with zipfile.ZipFile(p, "w") as z:
        for n, body in files.items():
            z.writestr(n, body)
            import base64
            dg = base64.urlsafe_b64encode(hashlib.sha256(body.encode()).digest()).rstrip(b"=").decode()
            rec.append(f"{n},sha256={dg},{len(body.encode())}")
        rec.append("p04good-1.0.dist-info/RECORD,,")
        z.writestr("p04good-1.0.dist-info/RECORD", "\n".join(rec) + "\n")
    return p


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pip(venv_py: str, args: list[str]) -> dict:
    p = subprocess.run(["unshare", "-n", venv_py, "-m", "pip", "--disable-pip-version-check", "--no-input", *args],
                       capture_output=True, text=True, timeout=600)
    tail = (p.stdout + p.stderr).strip().splitlines()
    return {"exit": p.returncode, "tail": [ln[:160] for ln in tail[-3:]]}


def main(out: str) -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        wh = td / "wh"
        wh.mkdir()
        marker = td / "MARKER_SETUP_RAN"
        sd, whl = make_sdist(wh, marker), make_wheel(wh)
        for w in Path(SETUPTOOLS_WHEEL_DIR).glob("*.whl"):
            (wh / w.name).write_bytes(w.read_bytes())
        venv = td / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        py = str(venv / "bin/python")
        res = {"sdist_sha256": sha(sd), "wheel_sha256": sha(whl)}
        lock_sd = td / "lock_sdist.txt"
        lock_sd.write_text(f"p04evil==1.0 --hash=sha256:{sha(sd)}\n")
        lock_bad = td / "lock_badhash.txt"
        lock_bad.write_text("p04good==1.0 --hash=sha256:" + "0" * 64 + "\n")
        lock_good = td / "lock_good.txt"
        lock_good.write_text(f"p04good==1.0 --hash=sha256:{sha(whl)}\n")
        flags = list(R.INSTALL_FLAGS) + ["--no-index", "--find-links", str(wh)]
        res["B_lab_route_sdist_with_correct_hash"] = pip(py, ["install", *flags, "-r", str(lock_sd)])
        res["B_marker_written"] = marker.exists()
        res["C_lab_route_wheel_wrong_hash"] = pip(py, ["install", *flags, "-r", str(lock_bad)])
        res["C2_lab_route_wheel_right_hash"] = pip(py, ["install", *flags, "-r", str(lock_good)])
        res["A_control_plain_pip_builds_sdist"] = pip(py, ["install", "--no-index", "--find-links", str(wh), "p04evil"])
        res["A_marker_written"] = marker.exists()
        res["D_check_lock_sdist_lock"] = R.check_lock(lock_sd.read_text())
        res["D_verify_artifact_sdist"] = R.verify_artifact(sd, [sha(sd)])
        res["D_verify_artifact_wheel_wrong_hash"] = R.verify_artifact(whl, ["0" * 64])
        res["D_verify_artifact_wheel_right_hash"] = R.verify_artifact(whl, [sha(whl)])
        marker2 = td / "MARKER_SETUP_RAN_E"
        sd2 = wh / "p04evil2-1.0.tar.gz"
        setup2 = (f"from pathlib import Path\nPath({str(marker2)!r}).write_text('setup.py ran')\n"
                  "from setuptools import setup\nsetup(name='p04evil2', version='1.0', py_modules=[])\n")
        with tarfile.open(sd2, "w:gz") as t:
            for name, body in (("p04evil2-1.0/setup.py", setup2), ("p04evil2-1.0/PKG-INFO", "Metadata-Version: 2.1\nName: p04evil2\nVersion: 1.0\n")):
                data = body.encode()
                ti = tarfile.TarInfo(name)
                ti.size = len(data)
                t.addfile(ti, io.BytesIO(data))
        lock_e = td / "lock_marker_option.txt"
        lock_e.write_text(f'p04evil2==1.0 ; python_version >= "3" --hash=sha256:{sha(sd2)} --only-binary=:none:\n')
        lock_f = td / "lock_sha512.txt"
        lock_f.write_text(f'p04good==1.0 ; python_version >= "3" --hash=sha256:{"0" * 64} --hash=sha512:{"1" * 128}\n')
        res["E_check_lock_marker_option_line"] = R.check_lock(lock_e.read_text())
        res["E_check_lock_sha512_line"] = R.check_lock(lock_f.read_text())
        try:
            R.install_argv(lock_e)
            res["E_install_argv"] = "BUILT (bypass)"
        except R.InstallRefused as e:
            res["E_install_argv"] = "REFUSED: " + str(e)[:120]
        res["E_marker_after_install_argv"] = marker2.exists()
        res["E_control_pip_direct_with_lab_flags"] = pip(py, ["install", *flags, "-r", str(lock_e)])
        res["E_control_marker_written"] = marker2.exists()
        res["verdict"] = {
                          "skeptic_line_refused_by_check_lock": bool(res["E_check_lock_marker_option_line"]) and bool(res["E_check_lock_sha512_line"]),
                          "skeptic_line_refused_before_pip_by_install_argv": res["E_install_argv"].startswith("REFUSED") and not res["E_marker_after_install_argv"],
                          "flags_alone_do_not_stop_it_control": res["E_control_marker_written"],"lab_route_never_ran_setup_py": not res["B_marker_written"] and res["B_lab_route_sdist_with_correct_hash"]["exit"] != 0,
                          "wrong_hash_refused": res["C_lab_route_wheel_wrong_hash"]["exit"] != 0,
                          "right_hash_installs": res["C2_lab_route_wheel_right_hash"]["exit"] == 0,
                          "control_shows_the_threat": res["A_marker_written"]}
    Path(out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res["verdict"]))


if __name__ == "__main__":
    main(sys.argv[1])
