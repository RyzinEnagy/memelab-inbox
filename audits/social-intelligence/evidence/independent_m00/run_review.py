"""Run existing tests in disposable checkouts with exact statuses and offline guards.

Run with a disposable Python containing pytest==9.1.1 and numpy==2.4.2.
The checkouts must already be clean and detached at the two recorded commits.
No application code, assertions, clocks, or fixture results are changed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time

PIN = "698f73b854567ce60b56ce275b5ab6822a9d5f60"
RECOVERY = "3b434e1dcc59290d993a638ca615f61b929189bc"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--recovery", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent
    network = a.out / "network-events.log"
    network.write_text("")
    results = []
    env_info = {"python": sys.version, "platform": platform.platform(), "pytest": __import__("pytest").__version__,
                "numpy": __import__("numpy").__version__, "suite_timeout_s": 900,
                "memory_limit": "No additional address-space limit; host/sandbox limits apply",
                "network_guard": "Python audit hooks inherited by child Python; not OS packet capture"}
    with tempfile.TemporaryDirectory(prefix="m00-offline-") as tmp:
        env = {"PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ.get("M00_TOOL_PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
               "HOME": tmp, "TMPDIR": tmp, "LANG": "en_US.UTF-8", "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1",
               "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
               "MEMELAB_PRIVATE_DB": tmp + "/private.sqlite", "MEMELAB_LLM_CONFIG": tmp + "/missing-llm.json",
               "M00_NETWORK_LOG": str(network.resolve())}
        for label, root, sha in [("baseline", a.baseline, PIN), ("recovery", a.recovery, RECOVERY)]:
            assert git(root, "rev-parse", "HEAD") == sha
            assert not git(root, "status", "--porcelain"), "checkout must start clean"
            before = hashlib.sha256((root / "data/memelab.sqlite").read_bytes()).hexdigest()
            env["PYTHONPATH"] = str(here / "network_guard") + os.pathsep + str(root)
            checks = []
            if label == "recovery":
                checks += [("m00-tests", ["-m", "pytest", "tests/test_audit_evidence.py", "-q"]),
                           ("integrity", ["tools/check_audit_evidence.py"]),
                           ("strict-gate", ["tools/check_audit_evidence.py", "--require-complete"])]
            checks += [("full-suite", ["-m", "pytest", "tests", "-q"]),
                       ("content-guard", ["-m", "memelab", "social", "guard"]),
                       ("release-audit", ["tools/release_audit.py", "--main-ref", PIN,
                                          "--out", str(a.out.resolve() / (label + "-release.md")),
                                          "--json", str(a.out.resolve() / (label + "-release.json"))])]
            for name, args in checks:
                log = a.out / (label + "-" + name + ".log")
                start = time.monotonic()
                with log.open("w") as f:
                    proc = subprocess.Popen([sys.executable, *args], cwd=root, env=env, stdout=f, stderr=subprocess.STDOUT,
                                            start_new_session=True)
                    timed_out = False
                    try:
                        rc = proc.wait(timeout=900 if name == "full-suite" else 180)
                    except subprocess.TimeoutExpired:
                        import signal
                        timed_out = True
                        os.killpg(proc.pid, signal.SIGTERM)
                        rc = proc.wait()
                item = {"checkout": label, "sha": sha, "check": name, "command": "python " + " ".join(args),
                        "exit_code": rc, "shell_equivalent_exit": 128 - rc if rc < 0 else rc,
                        "timeout": timed_out, "seconds": round(time.monotonic() - start, 3), "log": log.name}
                results.append(item)
                (a.out / "execution.json").write_text(json.dumps({"environment": env_info, "checks": results}, indent=2) + "\n")
                print(json.dumps(item), flush=True)
            after = hashlib.sha256((root / "data/memelab.sqlite").read_bytes()).hexdigest()
            (a.out / (label + "-checkout.json")).write_text(json.dumps({"sha": sha, "database_before": before,
                "database_after": after, "tracked_diff": git(root, "diff", "--name-only", "HEAD"),
                "status_after": git(root, "status", "--porcelain")}, indent=2) + "\n")
        print("network_events=" + str(len(network.read_text().splitlines())), flush=True)


if __name__ == "__main__":
    main()
