"""Bounded followups for a missing Git object and reported logging order failure."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--check", action="append", help="Run only named followups; existing records are retained")
    a = p.parse_args()
    here = Path(__file__).resolve().parent
    network = a.out.resolve() / "followup-network-events.log"
    network.touch(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="m00-followup-") as tmp:
        env = {"PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ.get("M00_TOOL_PATH", "/usr/bin:/bin"),
               "HOME": tmp, "TMPDIR": tmp, "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1",
               "OMP_NUM_THREADS": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "M00_NETWORK_LOG": str(network),
               "PYTHONPATH": str(here / "network_guard") + os.pathsep + str(a.root),
               "MEMELAB_PRIVATE_DB": tmp + "/private.sqlite", "MEMELAB_LLM_CONFIG": tmp + "/no-model.json"}
        logging = "tests/test_social_ingest.py::test_logs_never_carry_secrets_or_content"
        checks = [("logging-isolated", ["-m", "pytest", logging, "-q"]),
                  ("logging-order", ["-m", "pytest", "tests/test_social_ingest.py::test_cli_ingest_persists_verifiable_observation", logging, "-q"]),
                  ("logging-after-cli-setup", ["-c", "from memelab.social.cli import _setup_logging; _setup_logging(False); import pytest; raise SystemExit(pytest.main([" + repr(logging) + ", '-q']))"]),
                  ("release-audit-with-baseline", ["tools/release_audit.py", "--main-ref", "698f73b854567ce60b56ce275b5ab6822a9d5f60",
                       "--out", str(a.out.resolve() / "recovery-release-retry.md"), "--json", str(a.out.resolve() / "recovery-release-retry.json")]),
                  ("release-e2e", ["tools/release_e2e.py", "--out", str(a.out.resolve() / "recovery-e2e.md"),
                                   "--json", str(a.out.resolve() / "recovery-e2e.json")])]
        record = a.out / "followup-execution.json"
        results = json.loads(record.read_text()) if record.exists() else []
        for name, args in checks:
            if a.check and name not in a.check:
                continue
            with (a.out / (name + ".log")).open("w") as stream:
                r = subprocess.run([sys.executable, *args], cwd=a.root, env=env, stdout=stream,
                                   stderr=subprocess.STDOUT, timeout=180)
            results = [item for item in results if item["check"] != name]
            results.append({"check": name, "exit_code": r.returncode, "command": "python " + " ".join(args)})
            (a.out / "followup-execution.json").write_text(json.dumps(results, indent=2) + "\n")
            print(results[-1], flush=True)


if __name__ == "__main__":
    main()
