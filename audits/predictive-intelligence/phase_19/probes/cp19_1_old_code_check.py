"""CP19-1 (PI-D-107): the repair tests run against the first-pass module `fce102e:memelab/predictive/monitoring.py` in a temporary
copy (the checkout is never edited). Expected: the tests that pin repaired behaviour fail on the old module.

    python -B cp19_1_old_code_check.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
A = "audits/predictive-intelligence"
TESTS = ["test_cx_sk19_a_revision_citing_the_read_it_revises_or_no_read_is_refused",
         "test_cx_sk19_a_pending_is_superseded_only_by_a_later_read_or_an_unread_gap_after_maturity",
         "test_k9_a_revision_without_a_reason_is_refused", "test_k3_k4_scorable_is_as_of_the_record_and_read_times_even_on_an_unchecked_index",
         "test_k8_a_later_read_that_changes_the_class_but_not_the_state_is_recorded_as_a_revision",
         "test_a_read_whose_boundary_stops_before_a_matured_window_is_a_visible_plan_gap",
         "test_k11_a_prediction_for_an_unknown_decision_or_another_mint_is_refused",
         "test_k15_a_prediction_set_reusing_a_decision_key_with_another_identity_is_refused",
         "test_k12_load_refuses_a_duplicated_entry_even_with_a_valid_chain", "test_k13_misses_mark_a_label_not_matured_at_the_evaluation_time",
         "test_k17_page_hinkley_orders_the_stream_by_time", "test_k7_m4_d6_alerts_above_the_share_of_final_reads_and_reports_retries_apart",
         "test_m3_d1_is_insufficient_when_a_column_cannot_be_measured_and_ok_only_when_every_column_is",
         "test_m5_a_pinned_champion_below_the_support_minimum_keeps_abstaining", "test_x4_a_revision_read_must_carry_the_token_of_its_mint",
         "test_x8_a_revision_to_a_state_without_a_label_still_cites_its_later_read"]


def main(out: Path) -> int:
    old = subprocess.run(["git", "-C", str(REPO), "show", "fce102e:memelab/predictive/monitoring.py"], check=True, capture_output=True,
                         text=True).stdout
    res = {}
    with tempfile.TemporaryDirectory(prefix="p19_old_") as td:
        root = Path(td)
        for d in ("memelab", "tests"):
            shutil.copytree(REPO / d, root / d, ignore=shutil.ignore_patterns("__pycache__"))
        for d in (f"{A}/phase_07/artifacts", f"{A}/phase_09/artifacts", f"{A}/phase_19/probes", f"{A}/phase_12/probes", f"{A}/phase_07/probes",
                  f"{A}/phase_10/probes", f"{A}/phase_11/probes", f"{A}/phase_17/probes"):
            shutil.copytree(REPO / d, root / d, ignore=shutil.ignore_patterns("__pycache__"))
        (root / "memelab/predictive/monitoring.py").write_text(old)
        for t in TESTS:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", f"tests/test_predictive_monitoring.py::{t}", "-q", "-p", "no:cacheprovider"],
                               cwd=root, capture_output=True, text=True)
            res[t] = "FAILS_ON_FCE102E" if r.returncode != 0 else "PASSES_ON_FCE102E"
    rep = {"module_at": "fce102e", "tests": len(TESTS), "fail_on_old": sum(v == "FAILS_ON_FCE102E" for v in res.values()), "results": res}
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("tests", "fail_on_old")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
