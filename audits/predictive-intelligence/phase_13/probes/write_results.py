"""Write PHASE_13_RESULTS.json from the committed Phase 13 files (artifact sha256 computed here).

    python -B write_results.py [--head-after SHA] [--post FILE.json] [--status NEEDS_REVIEW]
"""
import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PH = REPO / "audits/predictive-intelligence/phase_13"
SHORTS = ("T1_24h", "T1b_6h", "T2_24h")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--head-after", default=None)
    ap.add_argument("--post", default=None)
    ap.add_argument("--status", default="NEEDS_REVIEW")
    a = ap.parse_args()
    orc = json.loads((PH / "evidence/oracle_sklearn_statsmodels.json").read_text())["sklearn"]
    ova = json.loads((PH / "evidence/oracle_venn_abers.json").read_text())["venn_abers"]
    mut = json.loads((PH / "evidence/mutation_calibration_sr2.json").read_text())
    today = json.loads((PH / "calibration/TODAY_STATUS.json").read_text())
    log = json.loads((PH / "evidence/run_log.json").read_text())
    rerun = json.loads((PH / "evidence/frozen_code_rerun_sr2.json").read_text())
    cards = {s: json.loads((PH / f"artifacts/{s}/CALIBRATION_CARD.json").read_text()) for s in SHORTS}
    hold = json.loads((PH / "calibration/HOLDOUT_POST_OPENING.json").read_text())
    checks = [
        ("G1 package checksums", "sha256sum -c SHA256SUMS.txt", "41 OK, 0 failed", 0, True),
        ("G2 entry suite at 6f4f8ea", "python -m pytest tests -q -p no:cacheprovider", "1 failed, 1455 passed in 197.15s (known test_dedup_corroboration_resurface_denial only)", 1, True),
        ("G2 entry seal check", "python -B audits/predictive-intelligence/phase_06/probes/check_seal.py", "problems [] with the three pinned hashes", 0, True),
        ("G2 Phase 12 key tests", "python -m pytest tests/test_predictive_evaluation.py tests/test_predictive_phase12_outputs.py -q", "57 passed", 0, True),
        ("G3 pre-registration first", "git log", "0fdf698 (20:21:18Z) before the first code commit 5a3c582 (20:52:33Z)", None, True),
        ("G4 frozen code before the recorded run", "git log; evidence/run_log.json dirty_code", "recorded run at 5a3c582, repeated at 2e1488a; three earlier debug runs logged", None, True),
        ("G5 calibration set chronologically valid", "run_calibration.py REPLAY_CHECKS.json", "fold card sha equal (3, 5, 1 folds); OOS numbers equal to Phase 07 within its 6 decimals (5.0e-7); refusals tested", 0, True),
        ("G6 fit gate and method rule", "tests/test_predictive_calibration.py", "boundaries tested", 0, True),
        ("G7 Platt against scikit-learn _sigmoid_calibration within 1e-6", "oracle_calibration.py (p04_bundle)",
         f"FAILED as registered on {orc['g7_cases_over_1e-6']} (worst {orc['worst']['platt_param']:.2e}; lbfgs stops early); newton-cholesky {orc['worst']['platt_param_newton_cholesky']:.1e}; isotonic {orc['worst']['isotonic']:.1e}; Venn-Abers (ip200) {ova['worst']:.1e}",
         1, False),
        ("G8 frozen calibration tolerance", "tests", "stats.calibration_bins with ACCEPTANCE values, pinned", 0, True),
        ("G9 intervals widen with small support", "tests; BELOW_GATE_DESCRIPTIVE.json", "width non-increasing in support; 30-event confident set gives no calibrated card", 0, True),
        ("G10 abstention conditions", "tests/test_predictive_abstention.py", "28 conditions, each triggered alone with its contract reason; equal to the checklist's rule 12", 0, True),
        ("G11 P38 and invalid input", "tests", "NaN, inf, -0.1, 1.1 never publish; validator refuses injected values; NaN features are missing inputs", 0, True),
        ("G12 P11 and P10", "tests", "flat predictions flagged and fail calibration; always-negative rare event shows BSS <= 0 and worse log loss", 0, True),
        ("G13 overconfident rare class", "tests", "0.9 on a 2% class never calibrated", 0, True),
        ("G14 P23", "tests; SCORE_REPORT_DEV.json", "conflict flagged with both scores; T2 development rows show it", 0, True),
        ("G15 P27", "tests", "agreement 0.9 refused in scenarios, cohort, reference, simulation kind and source, behavioral input", 0, True),
        ("G16 P12", "tests", "token-history card on a new mint abstains; cross-sectional new-mint forecast needs its caveat", 0, True),
        ("G17 P39", "tests; DRIFT_DEV.json", "drift alarms only after the step; records append-only; no alarm on real development data (24, 44, 8 observations)", 0, True),
        ("G18 publication rule", "tests", "fixture FORECAST valid; every single condition gives ABSTAIN; tampered documents refused", 0, True),
        ("G19 schema", "tests; evidence/schema_jsonschema_check.json", "in-house checker and jsonschema 4.26.0: 0 errors on 299 written pairs; 12 mutations refused", 0, True),
        ("G20 real result", "run_calibration.py", "; ".join(f"{s} {cards[s]['calibration_set']['n']}/{cards[s]['calibration_set']['k']}/{cards[s]['calibration_set']['days']} {cards[s]['status']}" for s in SHORTS), 0, True),
        ("G21 holdout description only", "HOLDOUT_POST_OPENING.json; POST_OPENING_LOG.json", "; ".join(f"{s} {hold[s]['combined_state']}" for s in SHORTS) + "; no claim; sealed folder not read", 0, True),
        ("G22 today", "TODAY_STATUS.json", "; ".join(f"{s} {today['targets'][s]['prediction_status']} {sorted(today['targets'][s]['standing_reasons'])}" for s in SHORTS), 0, True),
        ("G23 search ledger", "evaluation.ledger_totals on experiments/SEARCH_LEDGER.csv", "3203 rows; candidates 87 and N_search 118 unchanged", 0, True),
        ("G24 determinism and isolation", "twin run; run_log.json", f"twin identical; socket events {len(log['socket_events'])}; stores unchanged; rerun at 2e1488a differs only in {rerun['differs']} (code commit line)", 0, True),
        ("G25 mutation probe", "probes/mutation_calibration.py", f"{mut['caught']} of {mut['mutations']} caught", 0, mut["caught"] == mut["mutations"]),
        ("G26 flag, imports, registry, contract", "tests; run_log.json", "flag OFF; no module imports calibration or abstention; contract and fingerprint 4b4aabce unchanged", 0, True),
    ]
    if a.post:
        for c in json.loads(Path(a.post).read_text()):
            checks.append(tuple(c))
    arts = sorted(p for p in PH.rglob("*") if p.is_file() and p.name != "PHASE_13_RESULTS.json" and "__pycache__" not in p.parts)
    arts += [REPO / "memelab/predictive/calibration.py", REPO / "memelab/predictive/abstention.py",
             REPO / "tests/test_predictive_calibration.py", REPO / "tests/test_predictive_abstention.py",
             REPO / "tests/test_predictive_phase13_outputs.py"]
    res = {"phase": "13", "status": a.status, "head_before": "6f4f8ea6254b6623cb66c627e6b61de3f9455fa8", "head_after": a.head_after,
           "commits": {"pre_registration": "0fdf698", "frozen_code": "5a3c582", "recorded_run_outputs": "9cd5288",
                       "self_review_pass_2_code": "2e1488a"},
           "result": {s: {"calibration_set": {k: cards[s]["calibration_set"][k] for k in ("n", "k", "days")},
                          "status": cards[s]["status"], "level": cards[s]["level"], "publishable": cards[s]["publishable"],
                          "card_sha256": cards[s]["card_sha"], "today": today["targets"][s]["prediction_status"],
                          "holdout_post_opening": hold[s]["combined_state"]} for s in SHORTS},
           "checks": [{"name": n, "command": c, "result": r, "exit_code": e, "pass": p} for n, c, r, e, p in checks],
           "artifacts": [{"path": p.relative_to(REPO).as_posix(), "sha256": sha(p)} for p in arts],
           "limitations": [
               "Publication path (FORECAST, SHADOW and VALIDATED_EXPERIMENTAL levels, admissible evidence) is TEST_ONLY: fixtures only; no real card is calibrated.",
               "G7 failed as registered on two descriptive below-gate fits (scikit-learn lbfgs stops early); a decision by the orchestrator or Elving is needed to close it (PI-D-069 item 6).",
               "The comparison with Phase 07's out-of-sample file is to its 6 decimals (fold cards equal by model sha).",
               "Exchangeability of the event rate is rejected across days (T1b, T2) and routes (T1, T1b): any calibration interval is conditional on an assumption the data contradict; no interval covers unmodelled risk.",
               "The published point cannot be recomputed from the document alone; Phase 17 keeps the raw number in its request record (PI-D-068).",
               "Development replay names CALIBRATION_EVIDENCE_PENDING at fold cutoffs that predate the prospective holdout, following the frozen evidence rule.",
               "The 10 prospective decisions have no stored features (Phase 05 store ends at the seal) and no price read: today's records add OOD and SOURCE_STALE.",
               "Every run read the opened holdout outcomes from committed Phase 12 files (POST_OPENING, logged); none fitted, selected or promoted.",
           ],
           "blockers": [],
           "approvals_needed": ["A decision on checklist item G7 (as PI-D-053 did for Phase 08 G16), by the orchestrator or Elving."],
           "next_eligible_phase": "14, once the orchestrator records Phase 13 PASS after the independent skeptic and repair pass"}
    (PH / "PHASE_13_RESULTS.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({"status": res["status"], "checks": len(res["checks"]), "failed": [c["name"] for c in res["checks"] if not c["pass"]],
                      "artifacts": len(res["artifacts"])}))


if __name__ == "__main__":
    main()
