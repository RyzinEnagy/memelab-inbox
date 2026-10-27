"""Phase 20: rerun every recorded counterexample at the frozen code and record whether it is still refused or caught.

    python -B cx_rerun.py OUTDIR       writes OUTDIR/COUNTEREXAMPLES.csv, OUTDIR/cx_rerun.json, OUTDIR/cx_raw/*.txt

Sources: each phase's evidence file names its own counterexample (CX-05 to CX-19, CX-10b-A, CX-10b-B, CX-16b) and the
orchestrator's skeptic counterexample (Phase 00, CX-S1 of Phase 01, Phase 02, Phase 03, Phase 04, CX-S06 to CX-SK19), with the
check that catches it. A counterexample with a pinned test is rerun through that test; one caught by a committed checker script
is rerun through that script; the Phase 00 counterexample (a lab clock as the decision time) has no test of its own and gets
an own check here (CX-00A, CX-00B). Network: none (pytest runs with the test files' socket hooks; the scripts read committed
files only). Nothing is written in the checkout.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
AUD = "audits/predictive-intelligence"
T = "tests/"

# id, phase, origin, what it is, catching tests (node ids) and/or commands [(argv, expected exit)]
CX = [
    ("CX-00A", "00", "skeptic", "theses.created_at taken as the decision or availability time (write lag hidden)", [], "own"),
    ("CX-00B", "00", "skeptic", "a stored thesis score used as an as-of feature at created_at", [], "own"),
    ("CX-S1", "01", "skeptic", "a row first exported later inherits its key's earlier decision time",
     [T + "test_predictive_decisions.py::test_cx_s1_a_row_first_exported_later_never_inherits_its_key_time"], None),
    ("CX-S02", "02", "skeptic", "a shortlisted repository under its pre-transfer path passes the candidate checker", [],
     [["python", "-B", f"{AUD}/phase_02/probes/check_candidates_negative.py", f"{AUD}/phase_02",
       f"{AUD}/phase_01/architecture/GAP_MATRIX.csv"], 0]),
    ("CX-S03", "03", "skeptic", "PurgedGroupKFold and CPCV credited as leak-free while training folds are empty or on later rows", [],
     [["python", "-B", f"{AUD}/phase_03/research/verify/check_scorecard_negative.py"], 0]),
    ("CX-03L", "03", "own", "a consistent author awards MAPIE C2 with a resolvable but false evidence line", [],
     [["python", "-B", f"{AUD}/phase_03/research/verify/counterexample_lead.py"], 0]),
    ("CX-04", "04", "own", "a walk-forward trained on rows before a midnight cutoff records the midnight as its training cutoff",
     [T + "test_predictive_stats.py::test_nan_maturity_on_leaking_rows_makes_the_audit_invalid",
      T + "test_predictive_stats.py::test_a_cutoff_after_the_test_start_is_invalid",
      T + "test_predictive_stats.py::test_lab_rule_is_valid_and_the_purge_mutation_is_refused"], None),
    ("CX-S04", "04", "skeptic", "a lock line with a per-line --only-binary=:none: option runs an sdist setup.py",
     [T + "test_predictive_runtime.py::test_p32_lock_guard_refuses_anything_but_hashed_exact_pins",
      T + "test_predictive_runtime.py::test_p32_install_argv_is_the_only_route_and_carries_the_flags"], None),
    ("CX-05", "05", "own", "a recorded vendor token that the URL did not send",
     [T + "test_predictive_asof_store.py::test_cx05_a_recorded_token_that_the_url_did_not_send_is_refused"], None),
    ("CX-06", "06", "own", "targets built from different reads of one decision",
     [T + "test_predictive_labels.py::test_cx06_targets_from_one_read_satisfy_the_cross_target_invariants",
      T + "test_predictive_labels.py::test_cx06_a_label_built_from_another_read_breaks_an_invariant"], None),
    ("CX-S06", "06", "skeptic", "a token=<mint> body that keeps the other token as base",
     [T + "test_predictive_labels.py::test_cx_s06_a_token_read_whose_body_keeps_the_other_token_as_base_gives_no_candle"], None),
    ("CX-07", "07", "own", "a join by mint with its latest snapshot",
     [T + "test_predictive_baselines.py::test_cx07_join_by_mint_with_its_latest_snapshot_is_refused"], None),
    ("CX-S07", "07", "skeptic", "one positive over five days earning a skill verdict",
     [T + "test_predictive_baselines.py::test_cx_s07_one_positive_over_five_days_never_earns_a_skill_verdict"], None),
    ("CX-08", "08", "own", "window-dependent opens, highs and lows changing a feature",
     [T + "test_predictive_technical.py::test_cx08_opens_highs_and_lows_never_change_a_feature",
      T + "test_predictive_technical.py::test_cx08_a_later_read_that_only_moves_opens_highs_and_lows_changes_nothing"], None),
    ("CX-S08", "08", "skeptic", "a number that depends on the other rows scored with it",
     [T + "test_predictive_technical.py::test_cx_s08_a_number_does_not_depend_on_the_other_rows_scored_with_it"], None),
    ("CX-09", "09", "own", "a post-decision collector read used as depth at the decision",
     [T + "test_predictive_onchain.py::test_cx09_a_post_decision_read_is_never_depth_at_the_decision"], None),
    ("CX-S09", "09", "skeptic", "a size cap from an old quote on another pool and a read after the decision",
     [T + "test_predictive_onchain.py::test_cx_s09_size_cap_uses_only_the_newest_visible_reads_of_the_decision_pool"],
     [["python", "-B", f"{AUD}/phase_09/probes/cx_s09_check.py", "{OUT}/cx_raw/CX-S09.json"], 0]),
    ("CX-10", "10", "own", "the newest export's token row used for an earlier decision",
     [T + "test_predictive_social.py::test_cx10_the_token_row_and_narrative_tables_come_from_the_decisions_own_export"], None),
    ("CX-10b-A", "10", "skeptic", "a VERIFIED catalyst available from first sighting, before its last condition held",
     [T + "test_predictive_social.py::test_cx10b_a_verified_availability_is_when_the_last_condition_held_and_follow_through_starts_at_the_decision"], None),
    ("CX-10b-B", "10", "skeptic", "a later suspension or untimed bot label applied at an earlier decision",
     [T + "test_predictive_social.py::test_cx10b_b_a_suspension_or_bot_label_recorded_after_t_is_not_applied_at_t"], None),
    ("CX-11", "11", "own", "a full-sample regime label used at an earlier decision",
     [T + "test_predictive_analog.py::test_regime_as_of_refuses_a_later_row_cx11",
      T + "test_predictive_analog.py::test_full_sample_regime_trap_is_caught_by_the_truncation_check_cx11"], None),
    ("CX-S11", "11", "skeptic", "one mint under two creator values counted as two analogs",
     [T + "test_predictive_analog.py::test_cx_s11_one_mint_under_two_creator_values_is_one_analog"], None),
    ("CX-12", "12", "own", "the best of 63 no-skill candidates looking good without correction",
     [T + "test_predictive_evaluation.py::test_cx12_the_best_of_63_no_skill_candidates_looks_good_uncorrected_but_not_after_max_t"], None),
    ("CX-S12", "12", "skeptic", "a correction that was never computed read as did-not-survive",
     [T + "test_predictive_evaluation.py::test_cx_s12_a_correction_that_was_not_computed_is_never_read_as_did_not_survive"], None),
    ("CX-13", "13", "own", "Platt fitted and checked on the spent holdout",
     [T + "test_predictive_calibration.py::test_cx13_platt_fitted_and_checked_on_the_spent_holdout_is_refused_at_every_step",
      T + "test_predictive_phase13_outputs.py::test_the_replay_was_rederived_exactly_and_the_cx13_traps_refused_real_holdout_rows"], None),
    ("CX-S13", "13", "skeptic", "flat evidence calibrating",
     [T + "test_predictive_abstention.py::test_rp2_m4_cx_s13_flat_evidence_never_calibrates_and_scores_outside_the_evidence_abstain"], None),
    ("CX-14", "14", "own", "agent agreement smuggled as a code or a nested fraction",
     [T + "test_predictive_behavioral.py::test_agreement_never_becomes_a_number"], None),
    ("CX-S14", "14", "skeptic", "a seed-reversed monitor under a stable label",
     [T + "test_predictive_behavioral.py::test_cx_s14_a_seed_reversed_monitor_is_unstable"], None),
    ("CX-15", "15", "own", "a planted catalyst's statements counted as hits and recall reported as accuracy",
     [T + "test_predictive_scenario_eval.py::test_permutation_flags_a_real_signal_and_not_an_outcome_independent_planted_half"], None),
    ("CX-S15", "15", "skeptic", "per-mint warnings fooling the decision-level permutation",
     [T + "test_predictive_scenario_eval.py::test_cx_s15_mint_planted_null_warnings_fool_the_decision_null_not_the_mint_block_null"], None),
    ("CX-16", "16", "own", "a positive T2 point on seven positives without calibration, and a forged champion level",
     [T + "test_predictive_registry.py::test_cx16_a_positive_t2_point_on_seven_positives_and_no_calibration_stays_abstain",
      T + "test_predictive_registry.py::test_cx16_a_forged_champion_level_is_refused_everywhere",
      T + "test_predictive_phase16_outputs.py::test_cx16_t2_b2_has_a_positive_point_but_stays_an_abstain_reference"], None),
    ("CX-16b", "16", "own", "forged facts with a recomputed id",
     [T + "test_predictive_registry.py::test_verify_facts_refuses_forged_facts_given_the_committed_records"], None),
    ("CX-S16", "16", "skeptic", "a forged-facts entry pinned and served through a caller-supplied check",
     [T + "test_predictive_registry.py::test_cx_s16_a_forged_facts_entry_is_never_pinned_or_served_whatever_the_caller_checks"], None),
    ("CX-17", "17", "own", "a rollback leaving an unchanged snapshot's withdrawn forecast in place",
     [T + "test_predictive_integration.py::test_cx17_a_rollback_makes_an_unchanged_snapshot_material_so_the_withdrawn_forecast_is_not_kept"], None),
    ("CX-S17", "17", "skeptic", "a refused target leaving its siblings' documents persisted",
     [T + "test_predictive_integration.py::test_rp2_m1_cx_s17_a_refused_target_leaves_nothing_of_its_event_and_the_next_pass_recovers"], None),
    ("CX-18", "18", "own", "a forged probability in a resealed state",
     [T + "test_predictive_reports.py::test_g7_cx18_a_forged_probability_in_a_resealed_state_is_refused_and_shows_no_number"], None),
    ("CX-SK18", "18", "skeptic", "run-together trading words in token text",
     [T + "test_predictive_reports.py::test_rp2_m4_cx_sk18_run_together_trade_words_in_token_text_are_withheld",
      T + "test_predictive_reports.py::test_rp2_m4_cx_sk18_the_report_and_the_alert_never_print_a_run_together_trade_word"], None),
    ("CX-19", "19", "own", "a backdated prediction added after its outcome",
     [T + "test_predictive_monitoring.py::test_cx19_a_backdated_prediction_after_its_outcome_is_refused_whatever_time_it_claims"], None),
    ("CX-SK19", "19", "skeptic", "a revision citing the read it revises",
     [T + "test_predictive_monitoring.py::test_cx_sk19_a_revision_citing_the_read_it_revises_or_no_read_is_refused",
      T + "test_predictive_monitoring.py::test_cx_sk19_a_pending_is_superseded_only_by_a_later_read_or_an_unread_gap_after_maturity"], None),
]


def own_cx00a() -> dict:
    """CX-00A: a decision time taken from theses.created_at is refused by the contract, the abstention layer and the store."""
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests" / "fixtures" / "predictive"))
    import copy
    import asof_helpers as H
    from memelab.predictive import abstention as AB, contract as C, store as S
    out = {}
    doc = json.loads((REPO / "tests/fixtures/predictive/forecast_examples_format_only.json").read_text())
    ex = doc[0] if isinstance(doc, list) else next(v for v in doc.values() if isinstance(v, dict) and "decision_time_basis" in v) \
        if any(isinstance(v, dict) and "decision_time_basis" in v for v in doc.values()) else None
    if ex is None:
        ex = next(x for v in doc.values() if isinstance(v, list) for x in v if isinstance(x, dict) and "decision_time_basis" in x)
    bad = dict(copy.deepcopy(ex), decision_time_basis="THESIS_CREATED_AT")
    out["contract_refuses_created_at_basis"] = any("PI-D-011" in e for e in C.validate(bad, backtest=C.backtest_status()))
    out["abstention_flags_created_at_basis"] = any("PI-D-011" in e for e in AB.disallowed_inputs(
        {"decision_time": 1.0, "decision_time_basis": "THESIS_CREATED_AT", "x": {}, "avail": {}}, []))
    con = S.connect(":memory:")
    row = H.thesis(H.MINT_A, 1_792_000_000.0)
    try:
        S.ingest_exports(con, [H.export("c1", 1_792_000_000.0 - 60.0, [row], [H.token(H.MINT_A, pool=H.POOL_A)])], now=1_792_100_000.0)
        out["store_refuses_decision_before_created_at"] = False
    except S.StoreError:
        out["store_refuses_decision_before_created_at"] = True
    out["caught"] = all(v for k, v in out.items() if k != "caught")
    return out


def own_cx00b() -> dict:
    """CX-00B: a thesis row's score is a feature only from the export commit that first carried it, never from created_at."""
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests" / "fixtures" / "predictive"))
    import asof_helpers as H
    from memelab.predictive import features as F, store as S
    con = S.connect(":memory:")
    ca = 1_792_000_000.0
    commit_t = ca + 3600.0                                       # the row reached the export an hour after created_at
    S.ingest_exports(con, [H.export("c1", commit_t, [H.thesis(H.MINT_A, ca, score=77)], [H.token(H.MINT_A, pool=H.POOL_A)])],
                     now=commit_t + 60)
    early = F.features_as_of(con, "solana", H.MINT_A, ca + 600.0, F.FEATURE_VERSION)
    later = F.features_as_of(con, "solana", H.MINT_A, commit_t + 1.0, F.FEATURE_VERSION)
    v_e = {v["feature_name"]: v for v in early["values"]}
    v_l = {v["feature_name"]: v for v in later["values"]}
    score_names = [k for k in v_l if "score" in k]
    out = {"score_features": score_names,
           "missing_before_the_commit": all(v_e.get(k, {}).get("value") is None for k in score_names),
           "present_after_the_commit": any(v_l[k]["value"] is not None for k in score_names),
           "availability_is_the_commit": all(v_l[k]["value"] is None or (v_l[k]["feature_available_at"] or 0) >= commit_t
                                             for k in score_names)}
    out["caught"] = bool(score_names) and out["missing_before_the_commit"] and out["present_after_the_commit"] and out["availability_is_the_commit"]
    return out


def main(outdir: Path) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    raw = outdir / "cx_raw"
    raw.mkdir(exist_ok=True)
    t0 = time.time()
    nodes = sorted({n for _, _, _, _, ts, _ in CX for n in ts})
    junit = outdir / "cx_tests.xml"
    pt = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={junit}", *nodes], cwd=REPO,
                        capture_output=True, text=True, timeout=3600)
    (raw / "pytest.txt").write_text(pt.stdout[-20000:] + pt.stderr[-4000:])
    res: dict[str, str] = {}
    for tc in ET.parse(junit).getroot().iter("testcase"):
        key = f"tests/{tc.get('classname', '').split('.')[-1]}.py::{tc.get('name', '').split('[')[0]}"
        st = "failed" if any(c.tag in ("failure", "error") for c in tc) else ("skipped" if any(c.tag == "skipped" for c in tc) else "passed")
        res[key] = "failed" if "failed" in (res.get(key), st) else st
    rows = []
    for cid, ph, origin, what, tests, cmd in CX:
        outs = [res.get(n, "not_collected") for n in tests]
        cmd_res = None
        if cmd == "own":
            o = {"CX-00A": own_cx00a, "CX-00B": own_cx00b}[cid]()
            (raw / f"{cid}.json").write_text(json.dumps(o, indent=1, sort_keys=True, default=str))
            cmd_res = {"command": f"python -B {AUD}/phase_20/probes/cx_rerun.py (own check {cid})", "exit": 0 if o["caught"] else 1,
                       "expected": 0}
        elif cmd:
            argv, exp = cmd
            argv = [a.replace("{OUT}", str(outdir)) for a in argv]
            p = subprocess.run([sys.executable if a == "python" else a for a in argv], cwd=REPO, capture_output=True, text=True, timeout=1800)
            (raw / f"{cid}.txt").write_text(p.stdout[-20000:] + p.stderr[-4000:])
            argv = [a.replace(str(outdir), "OUTDIR") for a in argv]
            cmd_res = {"command": " ".join(argv), "exit": p.returncode, "expected": exp, "tail": p.stdout.strip().splitlines()[-1:] if p.stdout.strip() else []}
        caught = all(o == "passed" for o in outs) and (cmd_res is None or cmd_res["exit"] == cmd_res["expected"]) and (tests or cmd_res)
        rows.append({"id": cid, "phase": ph, "origin": origin, "counterexample": what, "tests": tests, "test_outcomes": outs,
                     "command": cmd_res, "result": "REFUSED_OR_CAUGHT" if caught else "NOT_CAUGHT"})
    with open(outdir / "COUNTEREXAMPLES.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "phase", "origin", "counterexample", "catching_tests", "test_outcomes", "command", "command_exit", "result"])
        for r in rows:
            w.writerow([r["id"], r["phase"], r["origin"], r["counterexample"], " ".join(r["tests"]), " ".join(r["test_outcomes"]),
                        (r["command"] or {}).get("command", ""), (r["command"] or {}).get("exit", ""), r["result"]])
    summary = {"counterexamples": len(rows), "caught": sum(r["result"] == "REFUSED_OR_CAUGHT" for r in rows),
               "not_caught": [r["id"] for r in rows if r["result"] != "REFUSED_OR_CAUGHT"], "pytest_exit": pt.returncode,
               "pytest_tail": pt.stdout.strip().splitlines()[-1] if pt.stdout.strip() else "", "wall_s": round(time.time() - t0, 1),
               "rows": rows}
    (outdir / "cx_rerun.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + "\n")
    print(json.dumps({k: summary[k] for k in ("counterexamples", "caught", "not_caught", "pytest_exit", "pytest_tail", "wall_s")}))
    return 0 if not summary["not_caught"] else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
