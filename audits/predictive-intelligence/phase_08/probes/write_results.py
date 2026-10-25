"""Write PHASE_08_RESULTS.json and the artifact table of PHASE_08_EVIDENCE.md from the files as they are.

    python -B write_results.py STATUS HEAD_AFTER [POSTCOMMIT_JSON]

Every file under audits/predictive-intelligence/phase_08/ except the results file and the evidence file (which hold the table)
is listed with its sha256, plus the phase's code and test files. POSTCOMMIT_JSON, when given, adds the post-commit checks.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
P8 = REPO / "audits/predictive-intelligence/phase_08"
START, END = "<!-- artifacts:start -->", "<!-- artifacts:end -->"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(status: str, head_after: str, post: str | None = None) -> None:
    skip = {"PHASE_08_RESULTS.json", "PHASE_08_EVIDENCE.md"}
    files = sorted(p for p in P8.rglob("*") if p.is_file() and p.name not in skip and "__pycache__" not in p.parts)
    arts = [{"path": str(p.relative_to(REPO)), "sha256": sha(p)} for p in files]
    for extra in ("memelab/predictive/technical.py", "tests/test_predictive_technical.py"):
        arts.append({"path": extra, "sha256": sha(REPO / extra)})
    m = {(r["target_short"], r["view"], r["model"], r["reference"]): r for r in csv.DictReader(open(P8 / "experiments/TECHNICAL_METRICS.csv"))}

    def line(t, mo, ref="B0"):
        r = m[(t, "ALL", mo, ref)]
        return {k: r.get(k) for k in ("n_with_number", "positives", "decision_days", "brier", "brier_ref", "bss_vs_ref", "bss_ci_day_lo",
                                      "bss_ci_day_hi", "bss_ci_mint_lo", "bss_ci_mint_hi", "governing", "p_holm", "abstain_reasons", "verdict")}

    smoke = json.loads((P8 / "evidence/serialization_smoke.json").read_text())
    traps = json.loads((P8 / "evidence/traps.json").read_text())
    xc = json.loads((P8 / "evidence/sklearn_crosscheck.json").read_text())
    diag = json.loads((P8 / "evidence/logit_solver_diagnosis.json").read_text())
    mut = json.loads((P8 / "evidence/mutation_technical.json").read_text())
    det = json.loads((P8 / "evidence/determinism.json").read_text())
    run = json.loads((P8 / "evidence/run_log.json").read_text())
    eq = json.loads((P8 / "evidence/phase07_equality.json").read_text())
    v2 = json.loads((P8 / "evidence/v2_consistency.json").read_text())
    ua = json.loads((P8 / "evidence/unavailable_candles.json").read_text())
    vt1 = json.loads((P8 / "evidence/trace/verify_trace.json").read_text())
    vt2 = json.loads((P8 / "evidence/trace/second/verify_trace.json").read_text())
    yp = json.loads((P8 / "evidence/young_pools.json").read_text())
    newton = max(r[s]["max_abs_coef_diff_to_numpy"] for r in diag["folds"].values() for s in ("newton-cholesky", "newton-cg"))
    checks = [
        {"name": "package checksums", "command": "sha256sum -c SHA256SUMS.txt", "exit_code": 0, "pass": True},
        {"name": "entry gate at 1139575", "command": "python -m pytest tests -q -p no:cacheprovider", "exit_code": 1,
         "result": "1 failed, 1179 passed in 165.18s (known failure only)", "pass": True},
        {"name": "seal check at entry", "command": "python -B audits/predictive-intelligence/phase_06/probes/check_seal.py", "exit_code": 0,
         "result": "problems []", "pass": True},
        {"name": "G3 pre-registration before any fit", "input": "8599318 at 2026-10-25T21:06:04Z holds checklist, registry and PI-D-050; technical.py absent at it; first real-label run after the code commit d290384 (21:22:26Z)",
         "result": "pass", "pass": True},
        {"name": "G4/G21 phase tests (repair pass 2)", "command": "python -m pytest tests/test_predictive_technical.py -q", "exit_code": 0, "result": "50 passed", "pass": True},
        {"name": "G21 mutation probe", "command": "python -B probes/mutation_technical.py evidence/mutation_technical.json", "exit_code": 0,
         "result": f"{mut['caught']} of {mut['mutations']} caught (the phase's 28 plus the skeptic's 11 non-equivalent survivors); "
                   f"equivalent: {[e['mutation'] for e in mut.get('equivalent_mutations', [])]}", "pass": mut["caught"] == mut["mutations"]},
        {"name": "CX-S08 score-time re-standardisation", "command": "pytest -k cx_s08 and the mutation 'S: CX-S08'", "exit_code": 0,
         "result": "the batch number equals the single-row number; the mutation is caught", "pass": any(r["mutation"].startswith("S: CX-S08") and r["caught"] for r in mut["results"])},
        {"name": "skeptic m3 runner stops on a failed trap", "input": "evidence/runner_exit_check.json",
         "result": "exit 1 with NC2T failed under the availability mutation", "pass": json.loads((P8 / "evidence/runner_exit_check.json").read_text())["exit_code"] == 1},
        {"name": "skeptic m1 young pools", "input": "evidence/young_pools.json",
         "result": f"{yp['pool_younger_than_window']} of {yp['censored_retrieval_decisions']} censored decisions are pools younger than the window; disclosed, label kept", "pass": True},
        {"name": "G16 preprocessing oracle (repair pass 2)", "command": "sklearn_crosscheck_tech.py", "exit_code": 1,
         "result": f"stats.Prep against SimpleImputer plus StandardScaler {xc['max_prep_design_diff']:.2g}; holdout-start designs {xc['holdout_start_designs_checked']}",
         "pass": xc["prep_shapes_equal"] and xc["max_prep_design_diff"] <= 1e-12},
        {"name": "G6 version 2 consistency", "input": "evidence/v2_consistency.json",
         "result": f"{v2['decisions_checked']} decisions, {len(v2['inconsistent'])} inconsistent", "pass": not v2["inconsistent"]},
        {"name": "G5 no input after T", "input": "evidence/unavailable_candles.json",
         "result": f"{ua['candles_started_before_T_not_available_total']} candles not yet available at T, {ua['inputs_used_after_T']} used; store candles ending after availability {ua['store_candles_with_end_after_availability']}",
         "pass": ua["inputs_used_after_T"] == 0 and ua["store_candles_with_end_after_availability"] == 0},
        {"name": "G7 same folds and B0/B2 numbers as Phase 07", "input": "evidence/phase07_equality.json",
         "result": json.dumps(eq, sort_keys=True), "pass": all(v["b0_b2_differences_at_6_decimals"] == 0 and v["split_fingerprint_equal"] for v in eq.values())},
        {"name": "G11 NC2-T future feature", "input": "evidence/traps.json NC2T", "result": json.dumps(traps["NC2T"], sort_keys=True), "pass": traps["NC2T"]["pass"]},
        {"name": "G11 P06-T moved cutoff", "input": "evidence/traps.json P06T", "result": json.dumps(traps["P06T"], sort_keys=True), "pass": traps["P06T"]["pass"]},
        {"name": "G11 P13-T later card", "input": "evidence/traps.json P13T", "result": "9 of 9 refused", "pass": traps["P13T"]["pass"]},
        {"name": "G14 artifacts", "input": "evidence/serialization_smoke.json",
         "result": "every card round-trips, tampering refused, runtime.verify_artifact passes, no pickle",
         "pass": all(v["roundtrip_identical"] and v["tamper_refused"] and not v["pickle_used"] for t in smoke.values() for k, v in t.items() if k != "contract")},
        {"name": "G15 contract", "input": "evidence/serialization_smoke.json contract",
         "result": "ABSTAIN valid, FORECAST refused for every target", "pass": all(t["contract"]["abstain_valid"] and t["contract"]["forecast_refused"] for t in smoke.values())},
        {"name": "G16 stumps oracle", "command": "sklearn_crosscheck_tech.py (research venv)", "exit_code": 1,
         "result": f"stumps max probability difference {xc['max_stump_prob_diff']:.2g}, same split every round", "pass": xc["max_stump_prob_diff"] <= 1e-9},
        {"name": "G16 logistic oracle, scikit-learn lbfgs (pre-registered tolerance 1e-6)", "command": "sklearn_crosscheck_tech.py (research venv)", "exit_code": 1,
         "result": f"max coefficient difference {xc['max_logit_coef_diff']:.3g} (fold 4 and holdout-start designs): above 1e-6, failed as registered", "pass": False},
        {"name": "G16 logistic, diagnosis added after the result", "command": "logit_solver_diagnosis.py (research venv)", "exit_code": 0,
         "result": f"lbfgs stops with gradients 1.0e-6 to 7.2e-6, numpy at most 3.3e-15; newton-cholesky and newton-cg agree with numpy within {newton:.2g}", "pass": newton <= 1e-6},
        {"name": "G17 determinism", "input": "evidence/determinism.json",
         "result": f"{det['files_compared']} files; differ only in {sorted(det.get('different_only_in', {}))} latency fields", "pass": det.get("identical_apart_from_timings", False)},
        {"name": "G17 isolation", "input": "evidence/run_log.json", "result": f"socket events {len(run['socket_events'])}, vendor calls 0, stores unchanged {run['stores']['unchanged']}",
         "pass": not run["socket_events"] and run["stores"]["unchanged"]},
        {"name": "G19 forecast traces", "command": "python -B probes/verify_trace.py evidence/trace/FORECAST_TRACE.json (and second/)", "exit_code": 0,
         "result": f"pre-registered: {vt1['differences'] or 'no difference'}; second: {vt2['differences'] or 'no difference'}; invalid inputs rejected",
         "pass": vt1["pass"] and vt2["pass"]},
        {"name": "G20 search ledger", "input": "experiments/SEARCH_LEDGER.csv", "result": f"registry rows missing {traps['registry_rows_missing_from_ledger']}",
         "pass": not traps["registry_rows_missing_from_ledger"]},
        {"name": "pre-commit full suite", "command": "python -m pytest tests -q -p no:cacheprovider", "exit_code": 1,
         "result": "1 failed, 1218 passed in 165.93s (known failure only; first pass, before the ledger test was added)", "pass": True},
    ]
    if post:
        checks += json.loads(Path(post).read_text())
    results = {s: {mo: line(s, mo) for mo in ("B2", "M1_T_LOGIT", "M2_T_LOGIT_B2", "M3_T_STUMPS")} for s in ("T1_24h", "T1b_6h", "T2_24h")}
    for s in results:
        results[s]["M2_T_LOGIT_B2_vs_B2"] = line(s, "M2_T_LOGIT_B2", "B2")
    out = {
        "phase": "08", "status": status, "provisional": "PROVISIONAL_PENDING_REVISION_REREAD (PI-D-046)",
        "status_reason": ("repair pass 2 folded in the independent skeptic (no material failure, 8 minor, CX-S08); every gate item holds "
                          "except checklist item G16 (logistic within 1e-6 of scikit-learn lbfgs), failed as registered (up to 2.08e-6) and "
                          "explained as lbfgs's stopping point (newton-cholesky within 9.0e-12); PASS needs the orchestrator or Elving to "
                          "record that the explanation closes G16 (PI-D-052 item 8)" if status == "NEEDS_REVIEW" else ""),
        "head_before": "1139575", "preregistration_commit": "8599318", "code_commit": "d290384", "runner_repair_commit": "d9b2a9c",
        "first_pass_head": "0656b7c", "repair2_code_commit": "e81ee46",
        "skeptic": {"review": "skeptic/PHASE_08_SKEPTIC.md", "material": 0, "minor": 8, "counterexample": "CX-S08 score-time re-standardisation",
                    "caught_by": ["tests/test_predictive_technical.py::test_cx_s08_a_number_does_not_depend_on_the_other_rows_scored_with_it",
                                  "tests/test_predictive_technical.py::test_scoring_uses_the_cards_training_mean_and_sd",
                                  "probes/mutation_technical.py mutation 'S: CX-S08'"]},
        "head_after": head_after, "registry_sha256": run["registry_sha"], "tech_feature_set_sha": run["tech_feature_set_sha"],
        "base_feature_set_sha": run["base_feature_set_sha"], "labels_version": run["labels_version"], "revision_check_claimed": False,
        "promotion": "MODEL_NOT_PROMOTED for every model", "results": results,
        "train_only_cards_at_holdout_start": {s: {mo: {k: v[k] for k in ("model_sha", "n_used", "k_used", "abstain")} for mo, v in t.items() if mo != "contract"}
                                              for s, t in smoke.items()},
        "checks": checks, "artifacts": arts,
        "limitations": [
            "PROVISIONAL until the Phase 06 48 h revision re-read is folded in; a changed development label means a rerun that supersedes these outputs (PI-D-046)",
            "development only, retrospective provider-mode reconstruction; cards are not as-of models for decisions before 2026-10-17",
            "technical inputs exist only on the PIT_RECORDED route with 24 h of fetched history: 154 of 240 labelled decisions",
            "T1 and T2 technical models never pass the training gate (INSUFFICIENT_HISTORY); T1b only in the last fold, scoring 6 rows with 0 positive on 1 day (INSUFFICIENT_DAYS)",
            "the T1b Brier skill on 6 negatives (M2 0.729) is not evidence of skill; no ranking or calibration can be checked without a positive",
            "one market regime (2026-W41 and W42); no per-cohort or regime statement",
            "pre-registered lbfgs tolerance exceeded (up to 2.08e-6, G16 failed as registered); newton-cholesky agrees within 9.0e-12 (diagnosis added after the result)",
            "both fitted T1b states sit exactly at 20 positives (fold 4 138 rows, holdout start 144): one changed development label from the 48 h re-read turns every fitted model into INSUFFICIENT_HISTORY",
            "12 of the 15 CENSORED_RETRIEVAL decisions are pools younger than the 24 h window (labelled by the frozen version 2 rule); tech-1 models cannot score pools under about 24 h 5 min old",
            "the P06-T rule was reinterpreted after recorded run 1 (late inputs refused, clock-only changes accepted)",
            "a second forecast trace was added after recorded run 1 because the pre-registered row's fold had no fitted technical model",
            "recorded run 1's P06-T probe was defective (counted a clock-only change); repaired and rerun; numbers unchanged",
            "the search-ledger test was added with the outputs (40 tests; 39 at the code commit); repair pass 2 added 10 (50)",
        ],
        "blockers": [],
        "open_dependency": "Phase 06 48 h revision re-read (not before 2026-10-26T13:49Z), run by the orchestrator",
        "approvals_needed": [],
        "next_eligible_phase": "09 once G16 is closed by a recorded decision (orchestrator or Elving); Phase 08 results PROVISIONAL under PI-D-046",
    }
    (P8 / "PHASE_08_RESULTS.json").write_text(json.dumps(out, indent=1, sort_keys=False) + "\n")
    ev = P8 / "PHASE_08_EVIDENCE.md"
    text = ev.read_text()
    table = "\n".join(["| Path | sha256 |", "|---|---|"] + [f"| `{a['path']}` | `{a['sha256']}` |" for a in arts])
    a, b = text.index(START), text.index(END)
    ev.write_text(text[:a + len(START)] + "\n" + table + "\n" + text[b:])
    print(json.dumps({"status": status, "checks": len(checks), "failed": [c["name"] for c in checks if not c["pass"]], "artifacts": len(arts)}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
