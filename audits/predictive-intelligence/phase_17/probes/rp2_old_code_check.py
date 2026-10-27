"""CP17-1 (PI-D-096): every repair test must fail on the first-pass code at ea73cfb (the commit the skeptic reviewed). The old code
is exported into a temporary folder with the current test files (so an old-code write lands in the temporary copy, never in
the checkout).

    python -B rp2_old_code_check.py OUT.json
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
OLD = "ea73cfb"
FILES = ["tests/test_predictive_integration.py", "tests/test_predictive_registry.py"]
TESTS = {  # test: the skeptic finding it answers
    "tests/test_predictive_integration.py::test_rp2_m1_cx_s17_a_refused_target_leaves_nothing_of_its_event_and_the_next_pass_recovers": "M1",
    "tests/test_predictive_integration.py::test_rp2_m1_a_failure_after_the_targets_saves_no_document": "M1",
    "tests/test_predictive_integration.py::test_rp2_m1_an_attempted_event_short_of_its_three_documents_is_an_error": "M1",
    "tests/test_predictive_integration.py::test_rp2_m1_check_state_detects_a_document_without_an_attempted_request": "M1",
    "tests/test_predictive_integration.py::test_rp2_m1_m6_flag_off_never_imports_the_package_even_for_a_pathological_config": "m1 m6",
    "tests/test_predictive_integration.py::test_rp2_m2_flag_on_and_a_broken_package_says_so": "m2",
    "tests/test_predictive_integration.py::test_rp2_m3_an_identity_string_cannot_forge_a_line_a_number_or_a_trading_word": "m3",
    "tests/test_predictive_integration.py::test_rp2_m5_the_backtest_database_is_opened_read_only_by_its_uri": "m5 (bt_adapter default chain)",
    "tests/test_predictive_integration.py::test_rp2_m7_the_same_analysis_in_another_report_folder_is_the_same_snapshot": "m7",
    "tests/test_predictive_integration.py::test_rp2_m8_the_section_prints_no_local_path": "m8",
}
# The M2 tests pin calls that already exist at ea73cfb, and the m4 tests close gaps no module uses today: they pass there and
# are shown to fail when a call is removed (mutation_integration.py Y1, Y2) or a gap is used (rp2_isolation_mutations.py).
PASS_ON_OLD = [
    "tests/test_predictive_integration.py::test_rp2_m2_the_flow_refuses_a_forged_point_so_removing_verify_point_is_caught",
    "tests/test_predictive_integration.py::test_rp2_m2_the_flow_refuses_dropped_reasons_so_removing_check_document_is_caught",
    "tests/test_predictive_integration.py::test_rp2_m4_no_lab_module_names_the_cli_helpers_and_no_lab_import_loads_the_package",
    "tests/test_predictive_registry.py::test_the_registry_seam_names_only_the_integration_module",
]


def _run(root: Path, t: str) -> dict:
    r = subprocess.run([sys.executable, "-B", "-m", "pytest", t, "-q", "-p", "no:cacheprovider"], cwd=root, capture_output=True, text=True)
    return {"exit": r.returncode, "last_line": (r.stdout.strip().splitlines() or [""])[-1]}


def main(out: str) -> int:
    with tempfile.TemporaryDirectory(prefix="p17_rp2_") as td:
        root = Path(td)
        tar = subprocess.run(["git", "-C", str(REPO), "archive", OLD, "memelab", "tests", "audits/predictive-intelligence/phase_16/registry",
                              "audits/predictive-intelligence/phase_13/artifacts", "audits/predictive-intelligence/phase_07/artifacts"],
                             capture_output=True, check=True).stdout
        tarfile.open(fileobj=io.BytesIO(tar)).extractall(root, filter="data")
        (root / "data" / "state").mkdir(parents=True)
        (root / "inbox").mkdir()
        (root / "state").mkdir()
        for f in FILES:
            (root / f).write_text((REPO / f).read_text())
        res = {t: dict(_run(root, t), finding=f) for t, f in TESTS.items()}
        for v in res.values():
            v["failed_on_old_code"] = v["exit"] != 0
        old_pass = {t: _run(root, t) for t in PASS_ON_OLD}
    rep = {"old_code": OLD, "tests": res, "all_fail_on_old_code": all(v["failed_on_old_code"] for v in res.values()),
           "pinning_tests_pass_on_old_code": {t: v["exit"] == 0 for t, v in old_pass.items()},
           "pinning_note": "the M2 tests pin calls present at ea73cfb and fail when either call is removed (mutation_integration.py Y1, Y2); the m4 tests close isolation gaps no module used at ea73cfb and fail when one is used (rp2_isolation_mutations.py)"}
    Path(out).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"all_fail_on_old_code": rep["all_fail_on_old_code"], "pinning_pass_on_old": rep["pinning_tests_pass_on_old_code"]}))
    return 0 if rep["all_fail_on_old_code"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
