"""Reexecute inspected original audit scripts without changing their source bytes.

All scripts are taken from checksum-verified user-supplied ZIPs. Temporary
checkouts must be detached at the exact recorded application/optional refs.
Original Phase 04 probes are equivalent-expression tests, not package imports.
Original Phase 05 arithmetic is historical modeling, not current price advice.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

PIN = "698f73b854567ce60b56ce275b5ab6822a9d5f60"
OPTIONAL = "3f27fc788f9ab88286b8041355e5445fdfdf012c"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--optional", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    review = Path(__file__).resolve().parents[4]
    originals = review / "audits/social-intelligence/originals"
    guard = review / "audits/social-intelligence/evidence/independent_m00/network_guard"
    args.out.mkdir(parents=True, exist_ok=True)
    network = args.out.resolve() / "network-events.log"
    network.write_text("")
    for root, ref in [(args.baseline, PIN), (args.optional, OPTIONAL)]:
        assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip() == ref
        assert subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip() == ""
    checks = [
        ("phase00-baseline", args.baseline, [originals / "phase00/evidence/probes.py", args.baseline],
         originals / "phase00/evidence/probes-main.json", "json", 0),
        ("phase00-optional", args.optional, [originals / "phase00/evidence/probes.py", args.optional],
         originals / "phase00/evidence/probes-feature.json", "json", 0),
        ("phase01-functional", args.baseline, ["-m", "pytest", originals / "phase01/evidence/test_functional_audit.py",
                                               "-q", "-s", "-p", "no:cacheprovider"], None, "pytest", 1),
        ("phase04-microprobes", args.baseline, [originals / "phase04/evidence/04_microprobes.py"],
         originals / "phase04/evidence/04_microprobes_output.txt", "text", 0),
        ("phase05-cost-model", args.baseline, [originals / "phase05/evidence/phase05_cost_model.py"],
         originals / "phase05/evidence/phase05_cost_model.json", "json", 0),
    ]
    records = []
    raw_dir = Path(tempfile.mkdtemp(prefix="m00-original-script-raw-"))
    with tempfile.TemporaryDirectory(prefix="m00-original-probes-") as td:
        env = {"PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin", "HOME": td, "TMPDIR": td,
               "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
               "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "M00_NETWORK_LOG": str(network),
               "AUDIT_NETWORK_LOG": str(network), "MEMELAB_PRIVATE_DB": td + "/private.sqlite",
               "MEMELAB_LLM_CONFIG": td + "/missing-model.json"}
        for name, root, command, original, kind, expected_exit in checks:
            env["PYTHONPATH"] = os.pathsep.join([str(guard), str(root), str(root / "tests")])
            started = time.monotonic()
            result = subprocess.run([sys.executable, *map(str, command)], cwd=root, env=env,
                                    capture_output=True, text=True, timeout=180)
            raw = result.stdout + result.stderr
            (raw_dir / (name + ".log")).write_text(raw)
            public = raw.replace(str(review), "<REVIEW_ROOT>").replace(str(args.baseline), "<PINNED_CHECKOUT>").replace(str(args.optional), "<OPTIONAL_CHECKOUT>")
            public = re.sub(r"/(?:private/)?var/folders/[^\s\"'<>]+", "<TEMP_PATH>", public)
            (args.out / (name + ".log")).write_text(public)
            equivalent = None
            if original is not None:
                equivalent = (json.loads(result.stdout) == json.loads(original.read_text())) if kind == "json" else result.stdout == original.read_text()
            record = {"name": name, "exit_code": result.returncode, "expected_exit": expected_exit,
                      "seconds": round(time.monotonic() - started, 3), "archived_output_equal": equivalent,
                      "raw_output_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                      "published_output_sha256": hashlib.sha256(public.encode()).hexdigest()}
            if kind == "pytest":
                record["summary"] = next((s for s in reversed(result.stdout.splitlines()) if re.search(r"\d+ failed, \d+ passed", s)), None)
                record["failed_tests"] = re.findall(r"^FAILED .*?::(\w+)", result.stdout, re.M)
            records.append(record)
            (args.out / "execution.json").write_text(json.dumps({"checks": records, "network_events": len(network.read_text().splitlines()),
                "python": sys.version, "per_check_timeout_s": 180, "additional_memory_limit": "none"}, indent=2) + "\n")
            print(json.dumps(record), flush=True)
            assert result.returncode == expected_exit, record
            assert equivalent is not False, record
            if kind == "pytest":
                old = (originals / "phase01/evidence/independent-tests.log").read_text()
                archived_failures = re.findall(r"^FAILED .*?::(\w+)", old, re.M)
                assert sorted(record["failed_tests"]) == sorted(archived_failures)
                assert "5 failed, 17 passed" in record["summary"]
        for label, root in [("baseline", args.baseline), ("optional", args.optional)]:
            record = {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                      "status": subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True),
                      "database_sha256": hashlib.sha256((root / "data/memelab.sqlite").read_bytes()).hexdigest()}
            (args.out / (label + "-after.json")).write_text(json.dumps(record, indent=2) + "\n")
            assert record["status"] == ""
            assert record["database_sha256"] == "068287c0d7e454361eb42f54b2f90e49e4075ae3a962a3c57867165ab6a679ca"
        assert network.read_text() == ""


if __name__ == "__main__":
    main()
