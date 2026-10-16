"""Record deliberately failing original-defect acceptance probes and archive mutations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--recovery", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent
    results = []
    network = a.out.resolve() / "acceptance-network-events.log"
    network.write_text("")
    with tempfile.TemporaryDirectory(prefix="m00-acceptance-") as tmp:
        env = {"PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin", "HOME": tmp, "TMPDIR": tmp,
               "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
               "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "M00_NETWORK_LOG": str(network)}
        def run(label, root, args):
            env["PYTHONPATH"] = str(here / "network_guard") + os.pathsep + str(root)
            log = a.out / (label + ".log")
            with log.open("w") as stream:
                proc = subprocess.run([sys.executable, *map(str, args)], cwd=root, env=env,
                                      stdout=stream, stderr=subprocess.STDOUT, timeout=180)
            results.append({"label": label, "exit_code": proc.returncode, "log": log.name})
            print(results[-1], flush=True)
        for label, root in [("baseline", a.baseline), ("recovery", a.recovery)]:
            run(label + "-independent-acceptance", root,
                ["-m", "pytest", str(here / "test_pinned_acceptance.py"), "-q", "-s", "-p", "no:cacheprovider"])
        source = a.recovery / "audits/social-intelligence"
        for label in ["byte-tamper", "missing-report"]:
            root = Path(tmp) / label
            dest = root / "audits/social-intelligence"
            shutil.copytree(source, dest)
            victim = dest / "recovered/00_BASELINE.md"
            if label == "byte-tamper":
                victim.write_bytes(victim.read_bytes() + b"x")
            else:
                victim.unlink()
            run(label, a.recovery, ["tools/check_audit_evidence.py", "--root", root, "--require-complete"])
    (a.out / "acceptance-execution.json").write_text(json.dumps({"checks": results,
        "network_events": len(network.read_text().splitlines()),
        "meaning": "Nine failing acceptance assertions reproduce open defects; positive control must pass. Mutation exit 1 is expected rejection."}, indent=2) + "\n")


if __name__ == "__main__":
    main()
