"""Phase 03 lead scoring inputs: which rubric items each repository earns, with the evidence for each point.

Every item not listed for a repository scores 0 (unanswered = 0). Items are all-or-nothing (RUBRIC_ITEMS.csv).
Evidence strings name files that check_scorecard.py resolves: REVIEWS/<repo>.md, SMOKES/<repo>/<file>,
verify/<file>, or pin:<owner__repo>/<path>:<line> (the pinned clone). Check ids refer to verify_reviews.py.
"""

R = "REVIEWS/%s.md"
S = "SMOKES/%s/%s"
P = "pin:%s/%s:%d"

def ev(*parts):
    return "; ".join(parts)

AW = {}
FLAGS = {}
ROUTE = {}
DECISION = {}
ZERO_NOTES = {}

# ---------------- scikit-learn ----------------
k = "scikit-learn__scikit-learn"
AW[k] = {
    "T1": (ev(S % (k, "smoke_output.txt") + " S1_splitters TimeSeriesSplit gap_0_rows", P % (k, "sklearn/model_selection/_split.py", 1104), "fold_audit:sklearn.TimeSeriesSplit"), "SK-1;SK-2;SK-7"),
    "O1": (ev(S % (k, "smoke_output.txt") + " S2_probability (527,2) finite in [0,1]", R % k + " s4 S2"), "SK-5"),
    "C1": (ev(P % (k, "sklearn/metrics/_classification.py", 3708), S % (k, "smoke_output.txt") + " brier and logloss fields"), "SK-6"),
    "C2": (ev(S % (k, "smoke_output.txt") + " S4_calibration frozen_sigmoid holdout brier 0.030943 (FrozenEstimator fit on train, sigmoid calibrated on the later val split)", R % k + " s4 S4"), "SK-4"),
    "F1": (ev(S % (k, "smoke_output.txt") + " S3_missing.HistGradientBoosting_native_nan proba_finite", R % k + " s4 S3"), ""),
    "D1": (ev(P % (k, "sklearn/calibration.py", 448)), "SK-6"),
    "Q1": (ev(S % (k, "repo_tests_subset.txt") + " 137 passed"), ""),
    "Q2": (ev(R % k + " s3 tests: test_calibration and test_split cover the role path"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-23; release 1.9.1 2026-09-10"), "PIN-ALL"),
    "Q4": (ev(R % k + " s1 built from the pin, imports"), ""),
    "Q5": (ev(R % k + " s4 no silent wrong output; isotonic hard 0 is the isotonic fit, flagged P38"), ""),
    "I1": (ev(S % (k, "smoke_output.txt") + " python 3.13.17"), ""),
    "I2": (ev("verify/closure_size.py: numpy 2.5.4, no pandas needed"), ""),
    "I3": (ev(R % k + " s8 estimator API"), ""),
    "I4": (ev(R % k + " s8 baseline and calibration layer; PLANNED_SEAMS models.py seam"), ""),
    "I5": (ev("verify/closure_size.py: declared closure 202.6 MB"), ""),
    "R1": (ev(S % (k, "smoke_output_run1.txt") + " equals smoke_output.txt S1, S2, S4"), "SK-3"),
    "R2": (ev(S % (k, "smoke_output.txt") + " S5_persistence pickle and joblib identical"), "SK-4"),
    "R5": (ev(S % (k, "smoke_output.txt") + " S5 version_stamp_in_state 1.10.dev0", P % (k, "sklearn/base.py", 517)), "SK-4;SK-6"),
    "K1": (ev(S % (k, "smoke_output.txt") + " network_attempts []"), ""),
    "K2": (ev(S % (k, "smoke_output.txt") + " S6_cost fit 0.19 s, single row 0.8 to 1.9 ms"), ""),
    "K3": (ev(S % (k, "smoke_output.txt") + " peak_rss_mb 143"), ""),
    "K4": (ev(R % k + " s4 S6: 1.9.1 cp313-win_amd64 on PyPI"), ""),
    "L1": (ev(R % k + " s2 COPYING BSD-3-Clause at the pin"), ""),
    "L2": (ev(R % k + " s2 vendored MIT and BSD only"), ""),
    "L3": (ev(R % k + " s2 no telemetry under sklearn/"), ""),
    "L4": (ev(R % k + " s1 meson build inspected; release wheel"), ""),
    "L5": (ev(R % k + " s2 no secrets, no service"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "PyPI release wheel (1.9.x), pickles only of files the lab wrote"
DECISION[k] = "INSTALL"
ZERO_NOTES[k] = {"T": "custom walk-forward iterables are caller code (not T1); TimeSeriesSplit purges by rows, not label time (T2 0); no availability concept (S1 trap passed)",
                 "O": "GroupKFold by mint ran but mint disjointness was not measured (O5 0); regression not run (O4 0)",
                 "C": "calibration_curve returns no bin counts (C5 0); no intervals or abstention"}

# ---------------- LightGBM ----------------
k = "lightgbm-org__LightGBM"
AW[k] = {
    "O1": (ev(S % (k, "smoke_output.txt") + " S2_probability (527,2)"), ""),
    "C1": (ev(P % (k, "src/metric/binary_metric.hpp", 134), S % (k, "smoke_output.txt") + " S1_cv final_valid_logloss_mean"), "LG-1"),
    "F1": (ev(S % (k, "smoke_output.txt") + " S3_missing finite with NaN"), "LG-4"),
    "D1": (ev("pin:%s/python-package/lightgbm/sklearn.py:1944 fit(sample_weight)" % k), "LG-3"),
    "Q1": (ev(S % (k, "repo_tests_subset.txt") + " 29 passed (pin tests on the 4.7.0 wheel)"), ""),
    "Q2": (ev(R % k + " s3 test_sklearn binary and predict_proba"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-23; 4.7.0 2026-07-18"), ""),
    "Q4": (ev(R % k + " s2 binary wheel imports"), ""),
    "Q5": (ev(R % k + " s4 none silent; imbalance switches inflate by design"), ""),
    "I1": (ev(S % (k, "smoke_output.txt") + " python 3.13.17"), ""),
    "I2": (ev("verify/closure_size.py venv: pandas 3.1.0, numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s3 sklearn API"), ""),
    "I4": (ev(R % k + " s8 Phase 08 comparator"), ""),
    "I5": (ev("verify/closure_size.py: closure 180.0 MB"), ""),
    "R1": (ev(S % (k, "smoke_output.txt") + " determinism trees identical", S % (k, "smoke_output_run1.txt") + " same text sha256"), "LG-2"),
    "R2": (ev(S % (k, "smoke_output.txt") + " S5 native_text identical max_abs_diff 0"), "LG-2"),
    "R3": (ev(S % (k, "smoke_output.txt") + " S5 native_text model (C++ parser, no code execution)"), "LG-2"),
    "K1": (ev(S % (k, "smoke_output.txt") + " network_attempts []"), "LG-4"),
    "K2": (ev(S % (k, "smoke_output.txt") + " S6 fit 0.075 s, single row 0.46 ms"), ""),
    "K3": (ev(S % (k, "smoke_output.txt") + " peak_rss_mb 182"), ""),
    "K4": (ev(R % k + " s4 S6 py3-none-win_amd64 wheel"), ""),
    "L1": (ev(R % k + " s2 MIT at the pin"), ""),
    "L2": (ev(R % k + " s2 Eigen MPL-2.0 parts only, unmodified; notices missing from the wheel recorded in the gate"), ""),
    "L3": (ev(R % k + " s2 none found"), ""),
    "L4": (ev(R % k + " s2 binary wheel, no install code"), ""),
    "L5": (ev(R % k + " s2 no secrets; dask sockets only for distributed training"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "PyPI wheel 4.7.x, native text model files, deterministic=True, research comparator"
DECISION[k] = "INSTALL"
ZERO_NOTES[k] = {"T": "accepts caller folds only; defaults shuffle (1,834 to 1,842 later rows per training fold)", "C": "raw probabilities 1 of 3 Wilson bins; no recalibration or intervals", "R": "text header carries no library version field shown (R5 0)"}

# ---------------- interpret ----------------
k = "interpretml__interpret"
AW[k] = {
    "T3": (ev(S % (k, "smoke_output_pin_cox.txt") + " cox_survival holdout_censored_before_24h 107 kept censored"), "IN-2"),
    "O1": (ev(S % (k, "smoke_output.txt") + " S2_probability (527,2)"), "IN-3"),
    "O2": (ev(S % (k, "smoke_output_pin_cox.txt") + " survival_cox fit with censoring, Harrell C 0.6749", "pin:%s/shared/libebm/compute/objectives/SurvivalCoxObjective.hpp:31" % k), "IN-1;IN-2"),
    "C5": (ev("verify/rerun_interpret_sd.out.txt has_standard_deviations_ true, n_sd_arrays 6 of 6 terms, all_finite true (per-term spread across outer bags)", P % (k, "python/interpret-core/interpret/glassbox/_ebm.py", 1639)), "IN-5"),
    "F1": (ev(S % (k, "smoke_output.txt") + " S3_missing native missing bin"), ""),
    "D1": (ev("pin:%s/python/interpret-core/interpret/glassbox/_ebm.py:475 sample_weight" % k), "IN-4"),
    "Q1": (ev(S % (k, "repo_tests_subset.txt") + " test_cox.py 26 passed"), ""),
    "Q2": (ev(R % k + " s3 Cox tests cover the survival path"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-18; 0.7.8 2026-03-17"), ""),
    "Q4": (ev(R % k + " s1 release and pin both import"), ""),
    "Q5": (ev(R % k + " s4 JSON load labelled untested, not silent"), ""),
    "I1": (ev(S % (k, "smoke_output.txt") + " python 3.13.17"), ""),
    "I2": (ev("verify/closure_size.py venv: pandas 3.1.0, numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s3 sklearn-style API"), ""),
    "I4": (ev(R % k + " s8 glassbox comparator"), ""),
    "I5": (ev("verify/closure_size.py: closure 318.0 MB"), ""),
    "R1": (ev(S % (k, "smoke_output.txt") + " determinism same_seed_identical_proba"), "IN-3"),
    "R2": (ev(S % (k, "smoke_output.txt") + " S5 pickle identical"), "IN-3"),
    "R3": (ev(S % (k, "smoke_output.txt") + " S5 json_export reloaded identically (private, beta path)"), "IN-1;IN-3"),
    "K1": (ev(S % (k, "smoke_output.txt") + " network_attempts []"), ""),
    "K2": (ev(S % (k, "smoke_output.txt") + " S6 fit 22.5 s default, single row 0.16 ms"), ""),
    "K3": (ev(R % k + " s4 peak RSS 250 MB"), ""),
    "K4": (ev(R % k + " s4 S6 pure wheel with bundled Windows DLL, 3.13 classifier"), ""),
    "L1": (ev(R % k + " s2 MIT at the pin"), ""),
    "L2": (ev(R % k + " s2 one Apache-2.0 file (permissive)"), ""),
    "L3": (ev(R % k + " s2 no telemetry; unpkg JS only for cloud-notebook visuals"), ""),
    "L4": (ev(R % k + " s1 build.sh inspected; wheel has no install code"), ""),
    "L5": (ev(R % k + " s2 no secrets; dashboard server not needed"), ""),
}
FLAGS[k] = "RESEARCH_ONLY (survival_cox, unreleased at the pin)"
ROUTE[k] = "PyPI wheel for classification; survival only from a later release"
DECISION[k] = "INSTALL (classification); ISOLATED_RESEARCH (survival)"
ZERO_NOTES[k] = {"T": "bags lets the caller choose validation rows (not T1); leak visible as top term but not refused", "C": "no recalibration, interval or abstention; Wilson bins inside on a logistic fixture earn nothing; C5 corrected in the repair pass (IN-5: the review probed the wrong attribute name)"}

# ---------------- TabPFN ----------------
k = "PriorLabs__TabPFN"
AW[k] = {
    "O1": (ev(S % (k, "smoke_output.txt") + " S2_probability (527,2)"), ""),
    "F1": (ev(S % (k, "smoke_output.txt") + " S3_missing native"), ""),
    "Q1": (ev(S % (k, "repo_tests_subset.txt") + " 72 passed"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-21; 9.2.0 2026-10-12"), ""),
    "Q4": (ev(R % k + " s1 installed from the pin, 91 files identical"), ""),
    "Q5": (ev(R % k + " s4 errors raised, none silent"), ""),
    "I1": (ev(S % (k, "smoke_output.txt") + " python 3.13.17"), ""),
    "I3": (ev(R % k + " s3 sklearn-style estimator"), ""),
    "I4": (ev(R % k + " s8 small-N comparator"), ""),
    "K1": (ev(S % (k, "smoke_output.txt") + " network_attempts_after_v2_fit_predict [] once v2 weights are cached"), "TP-4"),
    "K2": (ev(S % (k, "smoke_output.txt") + " S6 batch 62 ms per row, fit 0.96 s"), ""),
    "K3": (ev(S % (k, "smoke_output.txt") + " peak_rss_mb 996; v2 weights need no paid license"), "TP-2"),
    "K4": (ev(R % k + " s4 S6 pure wheel; torch cp313-win_amd64"), ""),
    "L1": (ev(R % k + " s2 code LICENSE Apache-2.0"), ""),
    "L4": (ev(R % k + " s2 setuptools build, no install scripts"), ""),
}
FLAGS[k] = "REJECT (default TabPFN-3.5 and 2.5/2.6/3 weights: non-commercial, outputs restricted); RESEARCH_ONLY (TabPFN-2 weights); NOT_REALTIME (CPU single row 17.5 s)"
ROUTE[k] = "TabPFN-2 weights only, pinned by sha256, separate venv, network blocked after the fetch"
DECISION[k] = "ISOLATED_RESEARCH"
ZERO_NOTES[k] = {"Q": "offline test subset did not cover the classifier path (Q2 0)", "I": "pandas version of the deleted venv not recorded (I2 0); 1.2 GB with torch (I5 0)",
                 "R": "reruns and reload differ by 6e-8, not bit-identical; fitted state is pickle", "L": "default weights non-commercial (L2 0); download counter call (L3 0); license token for default weights (L5 0)"}

# ---------------- statsmodels ----------------
k = "statsmodels__statsmodels"
AW[k] = {
    "T5": (ev("verify/rerun_statsmodels.out.txt filtered diff 0.0, smoothed diff 0.0186", S % (k, "smoke_output.txt") + " markov_regression.truncation_test"), "SM-2"),
    "O1": (ev(S % (k, "smoke_output.txt") + " S2_probability finite in [0,1], n 527"), ""),
    "C5": (ev(S % (k, "smoke_output.txt") + " S4_uncertainty holm, wilson_vs_lab 9e-6, GLM mean CI per row, standard errors"), "SM-3"),
    "F3": (ev(S % (k, "smoke_output.txt") + " markov_regression regime states (N07)"), "SM-2"),
    "D1": (ev(P % (k, "statsmodels/genmod/generalized_linear_model.py", 95) + " freq_weights, var_weights"), ""),
    "D3": (ev(S % (k, "smoke_output.txt") + " S4_uncertainty holm adjusted equal to hand computation"), "SM-3"),
    "Q1": (ev(S % (k, "repo_tests_subset.txt") + " 507 passed"), ""),
    "Q2": (ev(R % k + " s3 regime_switching and multitest tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-23; 0.15.0 2026-08-27"), ""),
    "Q4": (ev(R % k + " s1 built from the pin, imports"), ""),
    "Q5": (ev(R % k + " s4 default raises on NaN; out-of-sample predict raises (P42 recorded)"), "SM-1"),
    "I1": (ev(S % (k, "smoke_output.txt") + " python 3.13.17"), ""),
    "I2": (ev(R % k + " s1 pandas 3.1.0, numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s3 model API"), ""),
    "I4": (ev(R % k + " s8 B2 cross-check, Holm, Wilson"), ""),
    "I5": (ev("verify/closure_size.py: closure 260.5 MB"), ""),
    "R1": (ev("verify/repeat_runs.json statsmodels__statsmodels: reviewer script re-run by the lead, identical after normalization"), "REPEAT"),
    "R2": (ev(S % (k, "smoke_output.txt") + " S5_persistence identical"), "SM-3"),
    "K1": (ev(S % (k, "smoke_output.txt") + " network_attempts []"), ""),
    "K2": (ev(S % (k, "smoke_output.txt") + " S6 Logit 0.002 s, predict 0.005 ms"), ""),
    "K3": (ev(S % (k, "smoke_output.txt") + " peak_rss_mb 180"), ""),
    "K4": (ev(R % k + " s4 S6 0.15.0 cp313-win_amd64"), ""),
    "L1": (ev(R % k + " s2 LICENSE.txt BSD-3-Clause at the pin"), ""),
    "L2": (ev(R % k + " s2 nested BSD only"), ""),
    "L3": (ev(R % k + " s2 none found"), ""),
    "L4": (ev(R % k + " s2 meson build"), ""),
    "L5": (ev(R % k + " s2 no secrets"), ""),
}
FLAGS[k] = "LEAKAGE_FAIL (MarkovRegression defaults: smoothed probabilities, full-sample parameters); RESEARCH_ONLY (regime states)"
ROUTE[k] = "PyPI wheel; Logit, multipletests, proportion_confint in process; MarkovRegression only with train-window parameters and filter()"
DECISION[k] = "INSTALL (Logit, Holm, Wilson); ISOLATED_RESEARCH (MarkovRegression)"
ZERO_NOTES[k] = {"C": "no Brier or log loss function used (C1 0); GLM CI coverage not measured (C3 0)", "R": "pickle only (R3 0)"}

# ---------------- feast ----------------
k = "feast-dev__feast"
AW[k] = {
    "T4a": (ev(S % (k, "smoke_output.txt") + " S1_leak_trap.timestamp_field_is_availability_time rows_returning_own_future_value 0", "verify/rerun_feast_r1_script.out.txt"), "FE-1;FE-2"),
    "T6": (ev(S % (k, "smoke_output.txt") + " pit_semantics filter_by_created_timestamp_True exactly_at_second 2.0 (revision blocked)"), "FE-2"),
    "F2": (ev(S % (k, "smoke_output.txt") + " pit_semantics irregular per-entity times to the second"), "FE-2"),
    "F4": (ev(S % (k, "smoke_output.txt") + " pit_semantics other_mint_same_symbol 50.0"), "FE-2"),
    "F5": (ev(S % (k, "smoke_feast.py") + " typed FeatureViews `schema=[Field(name=` with `dtype=Float64`", S % (k, "smoke_output.txt") + " per_view_row_counts for 3 views"), ""),
    "Q1": (ev(S % (k, "repo_tests_subset.txt") + " 7 passed; one file needs the ibis extra"), ""),
    "Q2": (ev(R % k + " s3 dask offline store tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-19; 0.67.0 2026-10-13"), ""),
    "Q4": (ev(R % k + " s1 pure wheel imports"), ""),
    "I1": (ev(S % (k, "smoke_output.txt") + " python 3.13.17"), ""),
    "I3": (ev(R % k + " s4 local provider in process"), ""),
    "I5": (ev("verify/closure_size.py: closure 355.8 MB"), ""),
    "R1": (ev("verify/rerun_feast_r1_script.out.txt pit_semantics equal to the reviewer's run"), "FE-2"),
    "R3": (ev(S % (k, "smoke_output.txt") + " registry.db and online.db (sqlite, protobuf)", R % k + " s2"), ""),
    "K1": (ev(S % (k, "smoke_output.txt") + " network_attempts [] after import and apply"), "FE-2"),
    "K2": (ev(S % (k, "smoke_output.txt") + " S6 3,000 rows joined in 0.51 s"), ""),
    "K3": (ev(S % (k, "smoke_output.txt") + " peak_rss_mb 242"), ""),
    "K4": (ev(R % k + " s1 pure wheel"), ""),
    "L1": (ev(R % k + " s2 Apache-2.0 at the pin"), ""),
    "L2": (ev(R % k + " s2 MPL-2.0 only in unmodified dependencies"), ""),
    "L3": (ev(R % k + " s2 no usage module at the pin"), ""),
    "L4": (ev(R % k + " s2 pure wheel"), ""),
    "L5": (ev(R % k + " s2 auth code unused locally; no server started"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "not installed in the lab; 0.67.0 venv kept as an offline comparator"
DECISION[k] = "INSPIRED_IMPLEMENTATION"
ZERO_NOTES[k] = {"F": "rows silently dropped instead of nulled (F1 0)", "Q": "330 of 3,000 rows vanish silently, contradicting its docstring (Q5 0)",
                 "I": "requires pandas<3 (I2 0); duplicates the planned in-house as-of view (I4 0)", "R": "nothing to save or reload (R2 0)"}

# ---------------- MAPIE ----------------
k = "scikit-learn-contrib__MAPIE"
AW[k] = {
    "C3": (ev(S % (k, "raw_smoke_mapie.txt") + " lac conf=0.9 coverage 0.9184"), "MA-2"),
    "C4": (ev(S % (k, "raw_smoke_mapie.txt") + " `sizes: empty=29` at conf 0.9; risk controller `no valid threshold on 16 calibration positives`"), "MA-2"),
    "C5": (ev(S % (k, "raw_smoke_mapie.txt") + " ECE, Spiegelhalter p 0.6215, KS p 0.996"), ""),
    "D1": (ev(P % (k, "mapie/risk_control/risks.py", 277) + " BinaryRisk(risk_occurrence, risk_condition): custom per-row risk", P % (k, "mapie/risk_control/binary_classification.py", 182) + " consumed by BinaryClassificationController"), "MA-5"),
    "D2": (ev(S % (k, "raw_smoke_mapie.txt") + " `precision >= 0.1 at 90% confidence: no valid threshold` (Learn-then-Test controller abstains)"), "MA-2"),
    "Q1": (ev(S % (k, "raw_repo_tests_mapie.txt") + " 234 passed"), ""),
    "Q2": (ev(R % k + " s3 test_calibration and test_metrics"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-19; 1.6.0 2026-10-19"), ""),
    "Q4": (ev(R % k + " s2 numpy, scipy, scikit-learn only"), ""),
    "I1": (ev(S % (k, "raw_smoke_mapie.txt") + " python 3.13.17"), ""),
    "I2": (ev(S % (k, "raw_smoke_mapie.txt") + " pandas 3.1.0 numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s3 scikit-learn API"), ""),
    "I4": (ev(R % k + " s8 offline evaluation helper"), ""),
    "I5": (ev("verify/closure_size.py: closure 204.4 MB"), ""),
    "R1": (ev("verify/repeat_runs.json scikit-learn-contrib__MAPIE: reviewer script re-run by the lead, identical after normalization"), "REPEAT"),
    "R2": (ev(S % (k, "raw_smoke_mapie.txt") + " pickle reload identical sets and probabilities"), ""),
    "K1": (ev(S % (k, "raw_smoke_mapie.txt") + " unshare -n, exit 0"), ""),
    "K2": (ev(R % k + " s4 S6 fit 40 to 170 ms, predict microseconds"), ""),
    "K3": (ev(R % k + " s4 S6 166 MB"), ""),
    "K4": (ev(S % (k, "raw_pypi_files_r2.txt") + " py3-none-any"), ""),
    "L1": (ev(R % k + " s2 BSD-3-Clause sha256 92372faa"), ""),
    "L2": (ev(R % k + " s2 vendored MIT notices present"), ""),
    "L3": (ev(R % k + " s2 no network or telemetry code"), ""),
    "L4": (ev(R % k + " s2 setuptools, no setup.py"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "PyPI 1.6.0; offline evaluation only (split conformal sets, risk control, calibration diagnostics); never its Venn-Abers port, never a fitted Pipeline passed to VennAbersCalibrator(cv='prefit')"
DECISION[k] = "ADAPTER"
ZERO_NOTES[k] = {"O": "its only probability output is the Venn-Abers port that fails the definition (MA-1, MA-4): O1 0 by the verified-finding veto", "C": "no Brier or log loss function (C1 0); Venn-Abers port fails the definition above the calibration range (C2 0)", "Q": "Venn-Abers p1 defect, NaN score to a probability, prefit Pipeline refits the caller's transformers (MA-4) (Q5 0)", "D": "sample_weight passed through to the wrapped estimator does not count for D1 (pass-through rule); D1 rests on MAPIE's own BinaryRisk"}

# ---------------- crepes ----------------
k = "henrikbostrom__crepes"
AW[k] = {
    "T1": (ev(S % (k, "raw_smoke_crepes.txt") + " conformal test martingales over time-ordered scores: no alarm on train then val, `{'SimpleJumper': 619, 'SleeperStayer': 637` after the shift"), "CR-2"),
    "C3": (ev(S % (k, "raw_smoke_crepes.txt") + " marginal `coverage=0.9184`, class-conditional Mondrian `coverage=0.9336 positives_cov=0.9412`"), "CR-2"),
    "C4": (ev(S % (k, "raw_smoke_crepes.txt") + " class-conditional sets `{0,1}=406` at conf 0.9 (two-label no-decision sets)"), "CR-2"),
    "C5": (ev(S % (k, "raw_smoke_crepes.txt") + " `ks_test (uniformity of p-values) from evaluate`"), ""),
    "D4": (ev(S % (k, "raw_smoke_crepes.txt") + " martingale `alarm index (c=100, n means no alarm)` 619 to 637 after the shift"), "CR-2"),
    "Q3": (ev(R % k + " s1 commit 2026-07-08; 0.9.1 2026-06-12"), ""),
    "Q4": (ev(R % k + " s2 numpy, pandas, scipy"), ""),
    "Q5": (ev(R % k + " s4 none found; global RNG side effect recorded"), ""),
    "I1": (ev(S % (k, "raw_smoke_crepes.txt") + " python 3.13.17"), ""),
    "I2": (ev(R % k + " s1 pandas 3.1.0, numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s3 WrapClassifier and functions"), ""),
    "I4": (ev(R % k + " s8 drift monitor and abstention signal"), ""),
    "I5": (ev("verify/closure_size.py: closure 213.0 MB"), ""),
    "R1": (ev(S % (k, "raw_smoke_crepes.txt") + " two predict_p calls with the same seed equal"), "CR-2"),
    "R2": (ev(S % (k, "raw_smoke_crepes.txt") + " pickle reload identical p-values"), ""),
    "K1": (ev(S % (k, "raw_smoke_crepes.txt") + " unshare -n"), ""),
    "K2": (ev(R % k + " s4 S6 calibrate 2.9 ms, 0.1 ms per row"), ""),
    "K3": (ev(R % k + " s4 S6 241 MB"), ""),
    "K4": (ev(S % (k, "raw_pypi_files_r2.txt") + " py3-none-any"), ""),
    "L1": (ev(R % k + " s2 BSD-3-Clause sha256 3bed289f"), ""),
    "L2": (ev(R % k + " s2 no vendored code"), ""),
    "L3": (ev(R % k + " s2 no network code"), ""),
    "L4": (ev(R % k + " s2 plain setuptools"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "PyPI 0.9.1 pinned; offline monitoring on arrays from the as-of pipeline"
DECISION[k] = "ADAPTER"
ZERO_NOTES[k] = {"Q": "no test files at the pin (Q1 0, Q2 0)", "C": "no probability recalibration (C2 0)"}

# ---------------- venn-abers ----------------
k = "ip200__venn-abers"
AW[k] = {
    "O1": (ev(S % (k, "raw_smoke_venn_abers.txt") + " output shape (527, 2), `rows sum to 1: True`, `finite=True in[0,1]=True`"), ""),
    "C2": (ev(S % (k, "raw_smoke_venn_abers.txt") + " manual prefit path on the later window, `max |p1 - definition| = 0` on 530 probes"), "VA-1"),
    "C5": (ev(S % (k, "raw_smoke_venn_abers.txt") + " `interval p1-p0: median=0.0075` per-row interval width"), ""),
    "Q1": (ev(S % (k, "raw_repo_tests_venn_abers.txt") + " 18 passed"), ""),
    "Q2": (ev(R % k + " s3 all 4 test files"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-09-02; 1.5.4 2026-08-12"), ""),
    "Q4": (ev(R % k + " s1 builds and imports on 3.13"), ""),
    "I1": (ev(S % (k, "raw_smoke_venn_abers.txt") + " python 3.13.17"), ""),
    "I2": (ev(R % k + " s1 pandas 3.1.0, numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s3 manual mode on score arrays"), ""),
    "I4": (ev(R % k + " s8 test oracle and calibrator"), ""),
    "I5": (ev("verify/closure_size.py: closure 246.9 MB"), ""),
    "R1": (ev(S % (k, "raw_smoke_venn_abers.txt") + " manual mode equals the VennAbers class"), ""),
    "R2": (ev(S % (k, "raw_smoke_venn_abers.txt") + " pickle reload identical"), ""),
    "K1": (ev(S % (k, "raw_smoke_venn_abers.txt") + " unshare -n"), ""),
    "K2": (ev(R % k + " s4 S6 fit 8 to 11 ms, 0.23 us per row"), ""),
    "K3": (ev(R % k + " s4 S6 159 MB"), ""),
    "L1": (ev(R % k + " s2 MIT sha256 232ce5b4"), ""),
    "L2": (ev(R % k + " s2 no vendored code"), ""),
    "L3": (ev(R % k + " s2 no network code"), ""),
    "L4": (ev(R % k + " s2 setup.py inspected"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "pinned package kept in the research venv as a test oracle; numpy reimplementation in the lab"
DECISION[k] = "INSPIRED_IMPLEMENTATION"
ZERO_NOTES[k] = {"T": "estimator mode shuffles time by default (S4c)", "Q": "NaN score returns 0.625 silently (Q5 0)", "K": "sdist only on PyPI (K4 0)"}

# ---------------- model-diagnostics ----------------
k = "lorentzenchr__model-diagnostics"
AW[k] = {
    "C1": (ev(S % (k, "raw_smoke_model_diagnostics.txt") + " `SquaredError (Brier) decomposition` and `LogLoss decomposition` equal own Brier and log loss"), "MD-1"),
    "C5": (ev(S % (k, "raw_smoke_model_diagnostics.txt") + " `PAV blocks with counts` for the reliability curve and generalised bias with bias_stderr and p_value per bin"), ""),
    "F1": (ev(S % (k, "raw_smoke_model_diagnostics.txt") + " `rows with NaN liq_usd are reported as their own bin`"), "MD-1"),
    "D1": (ev(P % (k, "src/model_diagnostics/scoring/_scoring.py", 704) + " decompose(weights=)"), ""),
    "Q1": (ev(S % (k, "raw_repo_tests_model_diagnostics.txt") + " 294 passed, 4 need test-only pyarrow"), ""),
    "Q2": (ev(R % k + " s3 calibration and scoring tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-04-26; 1.5.0 2026-04-25"), ""),
    "I1": (ev(S % (k, "raw_smoke_model_diagnostics.txt") + " python 3.13.17"), ""),
    "I2": (ev(R % k + " s1 pandas 3.1.0, numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s3 stateless functions"), ""),
    "I4": (ev(R % k + " s8 offline oracle"), ""),
    "I5": (ev("verify/closure_size.py: closure 471.5 MB"), ""),
    "R1": (ev(S % (k, "raw_smoke_model_diagnostics.txt") + " repeated call identical"), ""),
    "K1": (ev(S % (k, "raw_smoke_model_diagnostics.txt") + " unshare -n"), ""),
    "K2": (ev(R % k + " s4 S6 decompose 1.5 ms"), ""),
    "K3": (ev(R % k + " s4 S6 242 MB"), ""),
    "K4": (ev(S % (k, "raw_pypi_files_r2.txt") + " py3-none-any"), ""),
    "L1": (ev(R % k + " s2 MIT sha256 45620685"), ""),
    "L2": (ev(R % k + " s2 no vendored code"), ""),
    "L3": (ev(R % k + " s2 no network code"), ""),
    "L4": (ev(R % k + " s2 hatchling"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "research venv only, as a cross-check for Phase 08 to 12 reports"
DECISION[k] = "INSPIRED_IMPLEMENTATION"
ZERO_NOTES[k] = {"Q": "pyarrow needed for pandas categorical inputs is undeclared (Q4 0); misleading zero-event p-values and silent NaN in bare scores (Q5 0)"}

# ---------------- arch ----------------
k = "bashtage__arch"
AW[k] = {
    "O4": (ev(S % (k, "raw_smoke_arch.txt") + " GARCH(1,1) estimates and volatility on 2016 returns"), ""),
    "C3": (ev(S % (k, "raw_smoke_arch.txt") + " Monte Carlo coverage IID 0.715, stationary 0.875"), "AR-1"),
    "F3": (ev(S % (k, "raw_smoke_arch.txt") + " GARCH(1,1) volatility state on 2016 returns, `12-step variance forecast last=0.2952` (degenerate on 60 returns)"), ""),
    "D3": (ev(S % (k, "raw_smoke_arch.txt") + " SPA p 0.306, MCS 90% set"), "AR-1"),
    "Q1": (ev(S % (k, "raw_repo_tests_arch.txt") + " 186 passed"), ""),
    "Q2": (ev(R % k + " s3 bootstrap and multiple comparison tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-22; 8.0.0 2025-10-21"), ""),
    "Q4": (ev(R % k + " s1 built from the pin"), ""),
    "I1": (ev(S % (k, "raw_smoke_arch.txt") + " python 3.13"), ""),
    "I2": (ev(R % k + " s1 pandas 3.1.0, numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s3 bootstrap objects"), ""),
    "I4": (ev(R % k + " s8 offline evaluation"), ""),
    "I5": (ev("verify/closure_size.py: closure 263.3 MB"), ""),
    "R1": (ev(S % (k, "raw_smoke_arch.txt") + " same seed twice identical"), "AR-1"),
    "R2": (ev(S % (k, "raw_smoke_arch.txt") + " pickled bootstrap identical interval"), ""),
    "K1": (ev(S % (k, "raw_smoke_arch.txt") + " unshare -n"), ""),
    "K2": (ev(R % k + " s4 S6 0.05 s per 2000 resamples"), ""),
    "K3": (ev(R % k + " s4 S6 174 MB"), ""),
    "K4": (ev(S % (k, "raw_pypi_files_r2.txt") + " 8.0.0 cp313 win_amd64"), ""),
    "L1": (ev("pin:%s/LICENSE.md:1 NCSA-style permissive" % k), "AR-2"),
    "L2": (ev(R % k + " s2 vendored pandas decorators (BSD-3)"), ""),
    "L3": (ev(R % k + " s2 no network code"), ""),
    "L4": (ev(R % k + " s2 meson build; research scripts not imported"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "PyPI release wheel, offline Phase 12 evaluation"
DECISION[k] = "ADAPTER"
ZERO_NOTES[k] = {"Q": "NaN gives a silent [nan, nan] interval; degenerate GARCH without warning (Q5 0)"}

# ---------------- mlfinpy ----------------
k = "baobach__mlfinpy"
AW[k] = {
    "D1": (ev(P % (k, "mlfinpy/sample_weights/attribution.py", 57) + " get_weights_by_return (sample weights by return attribution)"), ""),
    "Q1": (ev(S % (k, "raw_repo_tests_mlfinpy.txt") + " 17 passed"), ""),
    "I3": (ev(R % k + " s3 functions and splitters"), ""),
    "R1": (ev("verify/repeat_runs.json baobach__mlfinpy: reviewer script re-run by the lead, identical after normalization"), "REPEAT"),
    "R2": (ev(S % (k, "raw_smoke_mlfinpy.txt") + " pickled PurgedKFold identical folds"), ""),
    "K1": (ev(S % (k, "raw_smoke_mlfinpy.txt") + " unshare -n"), ""),
    "K2": (ev(R % k + " s4 1.9 ms per event"), ""),
    "K3": (ev(R % k + " s4 278 MB"), ""),
    "L1": (ev(R % k + " s2 LICENSE MIT at the pin"), ""),
    "L3": (ev(R % k + " s2 no network code"), ""),
    "L4": (ev(R % k + " s2 poetry-core, no scripts"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = "REJECT (unverified rights: BSD-3 mlfinlab code without its notice, snippet rights UNKNOWN); LEAKAGE_FAIL (PurgedKFold overlap, pending and same-bar labels); RESEARCH_ONLY (self-declared)"
ROUTE[k] = "none"
DECISION[k] = "REJECT"
ZERO_NOTES[k] = {"T": "PurgedKFold leaves overlapping windows (lead rerun: 3 of 3 expected)", "Q": "a test encodes the purge defect; no release in 18 months; sklearn undeclared"}

# ---------------- purgedcv ----------------
k = "eslazarev__purged-cross-validation"
AW[k] = {
    "T1": (ev(S % (k, "raw_smoke_purgedcv.txt") + " WalkForwardSplit 5 ordered folds", "fold_audit:purgedcv.WalkForwardSplit"), "PC-1;PC-3"),
    "T2": (ev("verify/rerun_purgedcv.out.txt WalkForwardSplit_leaks [0, 0, 0, 0, 0] and hand_case_kept [0, 1, 5] (lead interval-union checker)", "fold_audit:purgedcv.WalkForwardSplit"), "PC-1;PC-2;PC-3"),
    "T3": (ev("verify/fold_audit_purgedcv.out.txt WalkForwardSplit train_label_matures_after_first_test 0 in every fold", "fold_audit:purgedcv.WalkForwardSplit"), "PC-3"),
    "F2": (ev(S % (k, "raw_smoke_purgedcv.txt") + " irregular gaps 0 to 6,694 s purged by time"), "PC-1"),
    "D3": (ev(S % (k, "raw_smoke_purgedcv.txt") + " PBO 0.609 noise, 0.000 real drift"), ""),
    "Q1": (ev(S % (k, "raw_repo_tests_purgedcv.txt") + " 122 passed"), ""),
    "Q2": (ev(R % k + " s3 purge, embargo, walk-forward, CPCV and property tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-23; 0.1.11 2026-10-16"), ""),
    "Q4": (ev(R % k + " s2 numpy, pandas, scikit-learn, scipy; optuna lazy"), ""),
    "Q5": (ev(R % k + " s4 input validation raises on unordered times and NaT"), ""),
    "I1": (ev(S % (k, "raw_smoke_purgedcv.txt") + " python 3.13.17"), ""),
    "I2": (ev(S % (k, "raw_smoke_purgedcv.txt") + " pandas 3.1.0 numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s3 splitter interface and primitives"), ""),
    "I4": (ev(R % k + " s8 feeds the planned day walk-forward and LabelGate"), ""),
    "I5": (ev("verify/closure_size.py: closure 247.0 MB"), ""),
    "R1": (ev("verify/rerun_purgedcv.out.txt lead run reproduces the reviewer's per-fold counts"), "PC-1"),
    "R2": (ev(S % (k, "raw_smoke_purgedcv.txt") + " pickled splitter identical folds"), ""),
    "R4": (ev(S % (k, "raw_smoke_purgedcv.txt") + " audit_splitter rows removed by purge and embargo per fold"), ""),
    "K1": (ev(S % (k, "raw_smoke_purgedcv.txt") + " unshare -n"), ""),
    "K2": (ev(R % k + " s4 S6 folds in 17 to 153 ms"), ""),
    "K3": (ev(S % (k, "raw_smoke_purgedcv.txt") + " peak RSS 163 MB"), ""),
    "K4": (ev(S % (k, "raw_pypi_files_r2.txt") + " py3-none-any"), ""),
    "L1": (ev(R % k + " s2 MIT sha256 554e85fd"), ""),
    "L2": (ev(R % k + " s2 independent implementation, no vendored code"), ""),
    "L3": (ev(R % k + " s2 no network code"), ""),
    "L4": (ev(R % k + " s2 hatchling"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "PyPI 0.1.11 pinned; WalkForwardSplit for every model used in replay; PurgedKFold and CPCV only for labelled sensitivity or PBO, never for replay models; no PurgedGroupKFold on this data shape"
DECISION[k] = "ADAPTER"
ZERO_NOTES[k] = {"T": "no feature availability (S1 trap passed through walk-forward); PurgedKFold and CPCV train on up to 2,091 and 1,739 later rows (PC-3), so no temporal point rests on them", "O": "PurgedGroupKFold by mint leaves training folds of 0, 0, 45, 179 and 397 rows (PC-3): no usable group split (O5 0)"}

# ---------------- lifelines ----------------
k = "CamDavidsonPilon__lifelines"
AW[k] = {
    "T3": (ev(S % (k, "smoke_lifelines.result.json") + " concordance_holdout_all_incl_censored on 634 rows including 107 censored"), "LL-2"),
    "O1": (ev(S % (k, "smoke_lifelines.result.json") + " binary_24h_on_labeled_holdout shape [527] finite in [0,1]"), ""),
    "O2": (ev(S % (k, "smoke_lifelines.result.json") + " S2_S6_clean CoxPH and weibull_aft fitted on T and E with 107 censored kept"), "LL-2"),
    "C5": (ev(S % (k, "smoke_lifelines.out.txt") + " ICI 0.0087, E50 0.0061"), ""),
    "D1": (ev(P % (k, "lifelines/fitters/coxph_fitter.py", 175) + " weights_col"), ""),
    "Q1": (ev(S % (k, "repo_tests.out.txt") + " 16 passed (flaky installed: undeclared test dependency)"), ""),
    "Q2": (ev(R % k + " s3 concordance and Aalen-Johansen tests"), ""),
    "Q4": (ev(R % k + " s2 runtime dependencies complete"), ""),
    "Q5": (ev(R % k + " s4 NaN raises a clear error"), ""),
    "I1": (ev(S % (k, "smoke_lifelines.result.json") + " python 3.13.17"), ""),
    "I3": (ev(R % k + " s3 fitter API"), ""),
    "I4": (ev(R % k + " s8 survival baselines, nothing like it exists"), ""),
    "I5": (ev("verify/closure_size.py: closure 295.1 MB"), ""),
    "R1": (ev(S % (k, "smoke_lifelines_pandas3.result.json") + " identical metrics in a second run"), "LL-2"),
    "R2": (ev(S % (k, "smoke_lifelines.result.json") + " S5_persistence identical"), ""),
    "K1": (ev(S % (k, "smoke_lifelines.meta.json") + " unshare -n"), ""),
    "K2": (ev(S % (k, "smoke_lifelines.result.json") + " fit 0.12 s, 0.006 ms per row"), ""),
    "K3": (ev(R % k + " s4 194 MB"), ""),
    "K4": (ev(R % k + " s4 S6 py3-none-any wheel"), ""),
    "L1": (ev(R % k + " s2 MIT sha256 01ab0378"), ""),
    "L2": (ev(R % k + " s2 permissive dependencies"), ""),
    "L3": (ev(R % k + " s2 no network code"), ""),
    "L4": (ev(R % k + " s1 plain setup.py"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "PyPI wheel installed with --no-deps or a pandas override until pandas<3.0 is lifted"
DECISION[k] = "ADAPTER"
ZERO_NOTES[k] = {"Q": "last commit 2026-03-06, more than six months before review (Q3 0)", "I": "declares pandas<3.0 (I2 0)", "O": "competing risks marginal only (O3 0)", "F": "NaN refused (F1 0)"}

# ---------------- hazardous ----------------
k = "soda-inria__hazardous"
AW[k] = {
    "T3": (ev(S % (k, "smoke_hazardous.result.json") + " proba_shape [634, 3] and ibs_event1 on holdout_all (634 rows, 107 censored as event 0)", S % (k, "smoke_hazardous.py") + " `0 = censored`"), ""),
    "O1": (ev(S % (k, "smoke_hazardous.result.json") + " proba_shape [634,3] rows_sum_to_1"), "HZ-2"),
    "O2": (ev(S % (k, "smoke_hazardous.result.json") + " S2_S3_S6_clean SurvivalBoost fit_s 253.827 on event and duration with censored rows as event 0"), ""),
    "C1": (ev(S % (k, "smoke_hazardous.result.json") + " ibs_event1 and ibs_event2 (IPCW integrated Brier, censor-aware)"), ""),
    "C5": (ev(S % (k, "smoke_hazardous.result.json") + " S4_calibration aj_calibration_per_event_holdout and wilson95 in-the-large"), ""),
    "F1": (ev(S % (k, "smoke_hazardous.result.json") + " S3_nan 264 NaN accepted"), ""),
    "Q1": (ev(S % (k, "repo_tests.out.txt") + " 104 passed"), ""),
    "Q2": (ev(R % k + " s3 metrics and calibration tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-07-15; 0.2.0 2026-07-15"), ""),
    "Q4": (ev(R % k + " s2 declares lifelines and setuptools"), ""),
    "I1": (ev(S % (k, "smoke_hazardous.result.json") + " python 3.13.17"), ""),
    "I3": (ev(R % k + " s3 scikit-learn estimator"), ""),
    "I4": (ev(R % k + " s8 comparator for the T1 race"), ""),
    "I5": (ev("verify/closure_size.py: closure 330.9 MB"), ""),
    "R1": (ev(S % (k, "smoke_hazardous.result.json") + " refit_same_seed_identical_n_iter20"), "HZ-2"),
    "R2": (ev(S % (k, "smoke_hazardous.result.json") + " identical_after_reload"), ""),
    "K1": (ev(S % (k, "smoke_hazardous.meta.json") + " unshare -n"), ""),
    "K2": (ev("verify/rerun_hazardous_timing.out.txt fit 14.7 s at n_iter 10, 0.003 ms per row", R % k + " s4 S6"), "HZ-T"),
    "K3": (ev(R % k + " s4 182 MB"), ""),
    "L1": (ev(R % k + " s2 MIT sha256 cb492c05 at the pin"), ""),
    "L3": (ev(R % k + " s2 no network code"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = "REJECT (PyPI 0.2.0 wheel and sdist: SEER and METABRIC data of unknown rights, contents not in the source tree); pinned source eligible"
ROUTE[k] = "pinned source only (never the 0.2.0 artifacts); research comparator"
DECISION[k] = "ISOLATED_RESEARCH"
ZERO_NOTES[k] = {"O": "cumulative incidence decreases in time for 634 of 634 rows (HZ-2): the competing-risk race output fails its definition (O3 0 by the veto)", "C": "recalibrate_survival_function subtracts the absolute error and is unclipped (HZ-3: moves away from KM, leaves [0, 1]) (C2 0)", "Q": "cumulative incidence non-monotone for 634 of 634 rows (Q5 0)", "I": "pulls lifelines with pandas<3.0 (I2 0)", "K": "the only PyPI release is the rejected artifact (K4 0)", "L": "default PyPI route carries unknown-rights data and differs from the source tree (L2 0, L4 0)"}

# ---------------- river ----------------
k = "online-ml__river"
AW[k] = {
    "T1": (ev(S % (k, "smoke_river.result.json") + " progressive validation through simulate_qa in decision order"), "RV-1"),
    "T3": (ev("verify/rerun_river.out.txt answers_released_before_maturity 0 of 2,892 during the stream; 108 flushed at stream end are learned by progressive_val_score (RV-4), hence the scoped LEAKAGE_FAIL"), "RV-1;RV-2;RV-4"),
    "O1": (ev(S % (k, "smoke_river.result.json") + " S2_S6_online_delayed shape [527] finite"), ""),
    "F2": (ev(S % (k, "smoke_river.result.json") + " S2_S6_online_delayed: moment and delay on irregular decision times, nan_labels_skipped 107"), "RV-1"),
    "D1": (ev(P % (k, "river/linear_model/base.py", 183) + " learn_one(w=)"), ""),
    "D4": (ev(S % (k, "smoke_river.result.json") + " drift_feature_streams ADWIN and PageHinkley alarms in holdout (rows_into_holdout_before_first_detection 58 and 30), none in train"), ""),
    "Q1": (ev(S % (k, "repo_tests.out.txt") + " 161 passed"), ""),
    "Q2": (ev(R % k + " s3 drift and stream tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-23; 0.26.1 2026-08-21"), ""),
    "Q4": (ev(R % k + " s2 numpy, scipy, narwhals"), ""),
    "I1": (ev(S % (k, "smoke_river.result.json") + " python 3.13.17"), ""),
    "I2": (ev("verify/closure_size.py venv: numpy 2.5.4, pandas optional"), ""),
    "I3": (ev(R % k + " s3 dict API"), ""),
    "I4": (ev(R % k + " s8 drift monitoring (missing in the lab)"), ""),
    "I5": (ev("verify/closure_size.py: closure 175.6 MB"), ""),
    "R1": (ev("verify/repeat_runs.json online-ml__river: reviewer script re-run by the lead, identical after normalization"), "REPEAT"),
    "R2": (ev(S % (k, "smoke_river.result.json") + " S5_persistence pipeline identical, ADWIN state"), ""),
    "K1": (ev(S % (k, "smoke_river.meta.json") + " unshare -n"), ""),
    "K2": (ev(S % (k, "smoke_river.result.json") + " learn 12.9 us, predict 4.5 us per row"), ""),
    "K3": (ev(R % k + " s4 134 MB"), ""),
    "K4": (ev(R % k + " s4 S6 0.26.1 cp313 win_amd64"), ""),
    "L1": (ev(R % k + " s2 BSD-3 sha256 e87f2c8f"), ""),
    "L2": (ev("verify/river_crate_licenses.out.txt normal_closure_crates 34, normal_closure_non_permissive [] (MPL-2.0 colored is dev or bench only)", R % k + " s2 numpy, scipy, narwhals"), "RV-5"),
    "L3": (ev(R % k + " s2 no telemetry"), ""),
    "L4": (ev(R % k + " s2 wheel route; source build updates rustup (recorded in the gate)"), ""),
    "L5": (ev(R % k + " s2 network only in explicit dataset and stream helpers"), ""),
}
FLAGS[k] = "RESEARCH_ONLY (online learners on this data volume); LEAKAGE_FAIL (model state after a simulate_qa or progressive_val_score replay: the end-of-stream flush of unmatured answers is learned, qa.py:244, RV-4; drift detectors and in-stream predictions unaffected)"
ROUTE[k] = "PyPI wheel; river.drift behind a NaN-refusing wrapper; no model state is kept from a progressive_val_score replay"
DECISION[k] = "ADAPTER (drift); INSPIRED_IMPLEMENTATION (delayed progressive validation); ISOLATED_RESEARCH (online learners)"
ZERO_NOTES[k] = {"F": "NaN silently corrupts weights (F1 0, Q5 0)", "C": "no library metric used in the smoke (C1 0); miscalibrated"}

# ---------------- sktime ----------------
k = "sktime__sktime"
AW[k] = {
    "T1": (ev(S % (k, "smoke_sktime.result.json") + " A1_expanding_rows and A4_expanding_cutoff_timestamp ordered folds", "fold_audit:sktime.ExpandingWindowSplitter", "fold_audit:sktime.ExpandingCutoffSplitter"), "ST-2;ST-3"),
    "O5": (ev(S % (k, "smoke_sktime.result.json") + " C_panel_meta n_instances 289 (unequal length) fitted as one panel model by SklearnClassifierPipeline with a per-instance SummaryTransformer"), "ST-2;ST-4"),
    "F1": (ev(S % (k, "smoke_sktime.result.json") + " S3_nan_panel summary pipeline proba_finite"), "ST-2"),
    "F3": (ev(S % (k, "smoke_sktime.result.json") + " SummaryTransformer features on unequal windows"), ""),
    "Q1": (ev(S % (k, "repo_tests.out.txt") + " 1,417 passed; 2 failed on a data file the reviewer did not copy"), ""),
    "Q2": (ev(R % k + " s3 splitter tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-23; 1.2.0 2026-09-22"), ""),
    "Q4": (ev(R % k + " s1 core dependencies"), ""),
    "Q5": (ev(R % k + " s4 refusals raise; no silent output"), ""),
    "I1": (ev(S % (k, "smoke_sktime.result.json") + " python 3.13.17"), ""),
    "I2": (ev(S % (k, "smoke_sktime.result.json") + " pandas 3.0.5"), ""),
    "I3": (ev(R % k + " s3 estimator API"), ""),
    "I4": (ev(R % k + " s8 splitter designs"), ""),
    "I5": (ev("verify/closure_size.py: closure 259.6 MB"), ""),
    "R1": (ev("verify/repeat_runs.json sktime__sktime: reviewer script re-run by the lead, identical after normalization"), "REPEAT"),
    "R2": (ev(S % (k, "smoke_sktime.result.json") + " S5_persistence identical"), ""),
    "K1": (ev(S % (k, "smoke_sktime.meta.json") + " unshare -n"), ""),
    "K2": (ev(S % (k, "smoke_sktime.result.json") + " fit 0.73 s, 3.7 ms per instance"), ""),
    "K3": (ev(R % k + " s4 206 MB"), ""),
    "K4": (ev(R % k + " s4 S6 pure wheel"), ""),
    "L1": (ev(R % k + " s2 BSD-3 sha256 4f5bdd0f"), ""),
    "L2": (ev(R % k + " s2 GPL and source-available packages only behind optional wrappers"), ""),
    "L3": (ev(R % k + " s2 no telemetry"), ""),
    "L4": (ev(R % k + " s2 pure Python"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = "RESEARCH_ONLY (learners: forecasting fails on irregular series)"
ROUTE[k] = "not installed; splitter ideas reimplemented"
DECISION[k] = "INSPIRED_IMPLEMENTATION"
ZERO_NOTES[k] = {"O": "probabilities only from DummyClassifier(prior), one constant, and a wrapped scikit-learn LogisticRegression; its own panel classifiers raised on unequal series (ST-4): O1 0 by the wrapper rule; InstanceSplitter trains on later rows (ST-3), so O5 rests on the panel model", "T": "no purge or embargo (84 to 116 unmatured training labels per fold)", "F": "timedelta windows and forecasting fail on irregular timestamps (F2 0)", "R": "pickle only (R3 0)"}

# ---------------- tsfresh ----------------
k = "blue-yonder__tsfresh"
AW[k] = {
    "T5": (ev(S % (k, "smoke_tsfresh.out.txt") + " truncation invariance 127,428 of 127,428 cells"), "TS-2"),
    "F3": (ev(S % (k, "smoke_tsfresh.out.txt") + " 1,566 features per window"), ""),
    "D3": (ev(S % (k, "smoke_tsfresh.out.txt") + " P22_selection fdr_level 0.05: selected_under_5_permuted_labels all 0, selected_true_label 69"), ""),
    "Q1": (ev(S % (k, "repo_tests.out.txt") + " 36 passed"), ""),
    "Q2": (ev(R % k + " s3 dataframe_functions tests (roll_time_series)"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-07-06; 0.21.2 2026-05-31"), ""),
    "Q4": (ev(R % k + " s2 wheel imports"), ""),
    "I1": (ev(S % (k, "smoke_tsfresh.result.json") + " python 3.13.17"), ""),
    "I2": (ev(S % (k, "smoke_tsfresh.result.json") + " pandas 3.0.5"), ""),
    "I3": (ev(R % k + " s3 functions"), ""),
    "I4": (ev(R % k + " s8 feature catalogue"), ""),
    "R1": (ev(S % (k, "smoke_tsfresh.out.txt") + " from_columns re-extraction equals the first extraction"), ""),
    "R2": (ev(S % (k, "smoke_tsfresh.out.txt") + " pickled settings reused identically"), ""),
    "K1": (ev(S % (k, "smoke_tsfresh.meta.json") + " unshare -n"), ""),
    "K2": (ev(R % k + " s4 S6 Minimal 2.8 ms per window"), ""),
    "K3": (ev(R % k + " s4 335 MB"), ""),
    "K4": (ev(R % k + " s4 S6 pure wheel"), ""),
    "L1": (ev(R % k + " s2 MIT sha256 18042836"), ""),
    "L2": (ev(R % k + " s2 MPL-2.0 dependency files unmodified"), ""),
    "L3": (ev(R % k + " s2 requests only in examples"), ""),
    "L4": (ev(R % k + " s2 wheel needs no scripts"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = "RESEARCH_ONLY (feature generator)"
ROUTE[k] = "research venv; surviving calculators reimplemented in numpy"
DECISION[k] = "ISOLATED_RESEARCH"
ZERO_NOTES[k] = {"Q": "duplicate dict key drops two promised settings silently (Q5 0)", "I": "venv 503 MB (I5 0)", "F": "NaN refused (F1 0)"}

# ---------------- ruptures ----------------
k = "deepcharles__ruptures"
AW[k] = {
    "F3": (ev(S % (k, "smoke_ruptures.result.json") + " change points precision 0.632, recall 0.616"), ""),
    "Q1": (ev(S % (k, "repo_tests.out.txt") + " 130 passed"), ""),
    "Q2": (ev(R % k + " s3 costs, metrics, l1potts tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-05-26; 1.1.10 2025-09-10"), ""),
    "I1": (ev(S % (k, "smoke_ruptures.result.json") + " python 3.13.17"), ""),
    "I2": (ev("verify/closure_size.py venv: numpy 2.5.4, no pandas"), ""),
    "I3": (ev(R % k + " s3 fit and predict API"), ""),
    "I4": (ev(R % k + " s8 optional feature"), ""),
    "I5": (ev("verify/closure_size.py: closure 172.8 MB"), ""),
    "R1": (ev("verify/repeat_runs.json deepcharles__ruptures: reviewer script re-run by the lead, identical after normalization"), "REPEAT"),
    "R2": (ev(S % (k, "smoke_ruptures.result.json") + " pickle reload identical breakpoints"), ""),
    "K1": (ev(S % (k, "smoke_ruptures.meta.json") + " unshare -n"), ""),
    "K2": (ev(R % k + " s4 S6 KernelCPD 0.54 ms per refit"), ""),
    "K3": (ev(R % k + " s4 106 MB"), ""),
    "K4": (ev(R % k + " s4 S6 1.1.10 cp313 win_amd64"), ""),
    "L1": (ev(R % k + " s2 BSD-2-Clause sha256 f29c48be"), ""),
    "L2": (ev(R % k + " s2 numpy and scipy only"), ""),
    "L3": (ev(R % k + " s2 no network code"), ""),
    "L4": (ev(R % k + " s2 setup.py only cythonizes"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = "RESEARCH_ONLY (feature generator)"
ROUTE[k] = "research venv; a released wheel with a NaN check if a feature survives"
DECISION[k] = "ISOLATED_RESEARCH"
ZERO_NOTES[k] = {"T": "no causal mode; refit on a prefix is wrapper code; Window reads future samples", "Q": "typing_extensions undeclared (Q4 0); NaN gives silent breakpoints (Q5 0)"}

# ---------------- stumpy ----------------
k = "stumpy-dev__stumpy"
AW[k] = {
    "T5": (ev("verify/rerun_stumpy.out.txt stumpi left_P equals lead numpy past-only distance (1.4e-13)", S % (k, "smoke_stumpy.out.txt")), "SU-1"),
    "F1": (ev(S % (k, "smoke_stumpy.result.json") + " `subsequences containing NaN get distance inf`"), ""),
    "F3": (ev(S % (k, "smoke_stumpy.result.json") + " role_motif_match recovered_within_2 36 of 36 planted"), ""),
    "F4": (ev(S % (k, "smoke_stumpy.result.json") + " role_analog_query over 119 library_paths, candles_scanned 16634"), ""),
    "Q1": (ev(S % (k, "repo_tests.out.txt") + " 22 passed"), ""),
    "Q2": (ev(R % k + " s3 motif tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-16; 1.14.1 2026-02-08"), ""),
    "Q4": (ev(R % k + " s2 numpy, scipy, numba"), ""),
    "Q5": (ev(R % k + " s4 failures raise; none silent"), ""),
    "I1": (ev(S % (k, "smoke_stumpy.result.json") + " python 3.13.17"), ""),
    "I2": (ev("verify/closure_size.py venv: numpy 2.5.4, no pandas"), ""),
    "I3": (ev(R % k + " s3 functions"), ""),
    "I4": (ev(R % k + " s8 analog research"), ""),
    "I5": (ev("verify/closure_size.py: closure 364.0 MB"), ""),
    "R1": (ev("verify/rerun_stumpy.out.txt two code paths equal"), "SU-1"),
    "R3": (ev(S % (k, "smoke_stumpy.result.json") + " npz of float and int columns reloads equal"), ""),
    "K1": (ev(S % (k, "smoke_stumpy.meta.json") + " unshare -n"), ""),
    "K2": (ev(R % k + " s4 S6 cold 31 s, warm mass 0.9 ms"), ""),
    "K3": (ev(R % k + " s4 468 MB"), ""),
    "K4": (ev(R % k + " s4 S6 py3-none-any; numba cp313 win"), ""),
    "L1": (ev(R % k + " s2 BSD-3 sha256 36af1079"), ""),
    "L2": (ev(R % k + " s2 numba BSD, llvmlite BSD-2 and Apache-2.0"), ""),
    "L3": (ev(R % k + " s2 no network code"), ""),
    "L4": (ev(R % k + " s2 pure Python build"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = "RESEARCH_ONLY (no event probabilities); NOT_REALTIME as installed (31 s cold JIT)"
ROUTE[k] = "research venv for Phase 11 analog cohorts"
DECISION[k] = "ISOLATED_RESEARCH"
ZERO_NOTES[k] = {"R": "stumpi state cannot be pickled (R2 0)"}

# ---------------- evidently ----------------
k = "evidentlyai__evidently"
AW[k] = {
    "C1": (ev(S % (k, "smoke_evidently.out.txt") + " S2_probs LogLoss equals sklearn"), ""),
    "D4": (ev(S % (k, "smoke_evidently.out.txt") + " ROLE_drift flags liq_usd and ret_1h"), ""),
    "Q1": (ev(S % (k, "repo_tests_subset.out.txt") + " 78 passed"), ""),
    "Q2": (ev(R % k + " s3 stattests and drift tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-09-11; 0.7.23 2026-09-11"), ""),
    "Q5": (ev(R % k + " s4 invalid probabilities raise"), ""),
    "I1": (ev(S % (k, "smoke_evidently.meta.json") + " python 3.13.17 with pandas<3"), ""),
    "I3": (ev(R % k + " s3 Report API"), ""),
    "I4": (ev(R % k + " s8 drift reports without the UI service"), ""),
    "R2": (ev(S % (k, "smoke_evidently.out.txt") + " S5_persist roundtrip_dict_identical"), ""),
    "R3": (ev(S % (k, "smoke_evidently.out.txt") + " JSON snapshot, no pickle"), ""),
    "R4": (ev(S % (k, "telemetry_core_switch_on.out.txt") + " local Workspace add_run, runs 1"), ""),
    "K1": (ev(S % (k, "telemetry_core_switch_on.meta.json") + " core path 0 inet connects"), "EV-2"),
    "K2": (ev(S % (k, "smoke_evidently.out.txt") + " S6_cost 0.40 s report"), ""),
    "K3": (ev(R % k + " s4 307 MB"), ""),
    "K4": (ev(R % k + " s4 S6 py3-none-any"), ""),
    "L1": (ev(R % k + " s2 Apache-2.0 sha256 379054a0"), ""),
    "L2": (ev(R % k + " s2 bundled JS under MIT"), ""),
    "L4": (ev(R % k + " s2 hatchling, no hooks"), ""),
    "L5": (ev(R % k + " s2 UI service optional, not started"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "not imported by the lab; optional separate venv with DO_NOT_TRACK=1 and pandas<3"
DECISION[k] = "INSPIRED_IMPLEMENTATION"
ZERO_NOTES[k] = {"Q": "import fails under the default pandas 3 resolution (Q4 0)", "I": "needs pandas<3 (I2 0); 656 MB (I5 0)", "L": "UI telemetry on by default (L3 0)", "F": "NaN dropped silently (F1 0)"}

# ---------------- nannyml ----------------
k = "NannyML__nannyml"
AW[k] = {
    "T1": (ev(S % (k, "smoke_nannyml.py") + " timestamp_column_name chunking", P % (k, "nannyml/chunk.py", 165)), ""),
    "T3": (ev(S % (k, "smoke_nannyml.out.txt") + " ROLE_cbpe estimates for 107 rows without labels"), ""),
    "C3": (ev(S % (k, "smoke_nannyml.out.txt") + " ROLE_cbpe 4 of 4 chunks inside 3 SE"), ""),
    "C5": (ev(S % (k, "smoke_nannyml.out.txt") + " needs_calibration ECE check"), ""),
    "D1": (ev(P % (k, "nannyml/performance_estimation/confidence_based/metrics.py", 2121) + " business_value cost matrix"), ""),
    "D4": (ev(S % (k, "smoke_nannyml.out.txt") + " per-chunk alerts: holdout_alerts and reference_alerts per column, holdout_chunk_alerts 1"), ""),
    "Q2": (ev(S % (k, "repo_tests_subset.out.txt") + " CBPE and drift tests pass"), ""),
    "I2": (ev(R % k + " s4 smoke ran on pandas 3.1.0, numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s3 calculator API"), ""),
    "I4": (ev(R % k + " s8 monitoring idea"), ""),
    "R2": (ev(S % (k, "smoke_nannyml.out.txt") + " S5_persist identical estimates"), ""),
    "K1": (ev(S % (k, "telemetry_switch_off.meta.json") + " 0 connects with the documented switch"), "NM-2"),
    "K2": (ev(R % k + " s4 CBPE 0.075 ms per row"), ""),
    "K3": (ev(R % k + " s4 325 MB"), ""),
    "L1": (ev(R % k + " s2 Apache-2.0 sha256 4712221f"), ""),
    "L4": (ev(R % k + " s2 bare setup(), poetry-core"), ""),
    "L5": (ev(R % k + " s2 no service by default"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "not imported; ideas reimplemented; optional Python 3.12 venv with NML_DISABLE_USAGE_LOGGING=1"
DECISION[k] = "INSPIRED_IMPLEMENTATION"
ZERO_NOTES[k] = {"Q": "34 test errors under pandas 3 (Q1 0); last commit 2025-07-12 (Q3 0); statsmodels undeclared (Q4 0); invalid probabilities accepted (Q5 0)",
                 "I": "Python <3.13 (I1 0); 1.7 GB with NVIDIA and Chromium binaries (I5 0)", "L": "NVIDIA NCCL binary in a CPU install (L2 0); telemetry on by default (L3 0)", "R": "AP band unseeded (R1 0)"}

# ---------------- frouros ----------------
k = "IFCA-Advanced-Computing__frouros"
AW[k] = {
    "T1": (ev(S % (k, "smoke_frouros.out.txt") + " ROLE_streaming_concept detectors on the time-ordered error stream"), ""),
    "D4": (ev(S % (k, "smoke_frouros.out.txt") + " ROLE_batch_ks flagged_at_0.05 holdout liq_usd and ret_1h; ddm_drifts_with_trap 2"), ""),
    "Q1": (ev(S % (k, "repo_tests_subset.out.txt") + " 114 passed; 7 download-fixture errors offline"), ""),
    "Q2": (ev(R % k + " s3 detector tests"), ""),
    "Q4": (ev(R % k + " s2 declared dependencies install"), ""),
    "I1": (ev(S % (k, "smoke_frouros.meta.json") + " python 3.13.17"), ""),
    "I3": (ev(R % k + " s3 detector API"), ""),
    "I4": (ev(R % k + " s8 reference implementations"), ""),
    "I5": (ev("verify/closure_size.py: closure 253.4 MB"), ""),
    "R1": (ev("verify/repeat_runs.json IFCA-Advanced-Computing__frouros: reviewer script re-run by the lead, identical after normalization"), "REPEAT"),
    "R2": (ev(S % (k, "smoke_frouros.out.txt") + " S5_persist identical"), ""),
    "K1": (ev(S % (k, "smoke_frouros.meta.json") + " 0 inet connects"), ""),
    "K2": (ev(R % k + " s4 KS 0.05 s, ADWIN 58 us"), ""),
    "K3": (ev(R % k + " s4 211 MB"), ""),
    "L1": (ev(R % k + " s2 BSD-3 sha256 1e54672a"), ""),
    "L2": (ev(R % k + " s2 permissive base set"), ""),
    "L3": (ev(R % k + " s2 no telemetry"), ""),
    "L4": (ev(R % k + " s2 setup.py reads pyproject only"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "not installed (numpy and scipy upper bounds); detectors reimplemented"
DECISION[k] = "INSPIRED_IMPLEMENTATION"
ZERO_NOTES[k] = {"Q": "no release since 2024-10-05 and last commit 2026-02-11 (Q3 0); NaN gives PSI 0.0 (Q5 0)", "I": "numpy<2.3 and scipy<1.16 pins (I2 0)", "K": "PyPI release declares <3.13 (K4 0)"}

# ---------------- mlflow ----------------
k = "mlflow__mlflow"
AW[k] = {
    "T6": (ev(S % (k, "smoke_mlflow_pin.out.txt") + " LINEAGE training_label_cutoff_epoch, dataset digest, utc_time_created"), "ML-2"),
    "C1": (ev(S % (k, "smoke_mlflow_pin.out.txt") + " S4_evaluate log_loss 0.13826"), ""),
    "Q1": (ev(S % (k, "repo_tests_subset.out.txt") + " 72 of 74 pass; 2 need pyspark"), ""),
    "Q2": (ev(R % k + " s3 dataset and telemetry tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-23; 3.17.2 2026-10-21"), ""),
    "Q4": (ev(R % k + " s1 pin build imports"), ""),
    "Q5": (ev(R % k + " s4 no silent wrong output found"), ""),
    "I1": (ev(S % (k, "smoke_mlflow_pin.meta.json") + " python 3.13.17"), ""),
    "I2": (ev(R % k + " s4 pandas 3.1.0, numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s4 client with sqlite, no server"), ""),
    "R2": (ev(S % (k, "smoke_mlflow_pin.out.txt") + " S5_persist reload identical"), ""),
    "R3": (ev(S % (k, "smoke_mlflow_pin.out.txt") + " model.skops artifact"), ""),
    "R4": (ev(S % (k, "smoke_mlflow_pin.out.txt") + " LINEAGE run and registered version"), "ML-2"),
    "R5": (ev(S % (k, "smoke_mlflow_pin.out.txt") + " MLmodel mlflow_version; signature refuses a missing column"), ""),
    "K1": (ev(S % (k, "smoke_mlflow_pin.connect.txt") + " 0 inet connects at the pin"), ""),
    "K2": (ev(R % k + " s4 2.7 ms per call"), ""),
    "K3": (ev(R % k + " s4 419 MB"), ""),
    "K4": (ev(R % k + " s4 S6 pure wheel"), ""),
    "L1": (ev("pin:%s/LICENSE.txt:1 Apache-2.0" % k), ""),
    "L2": (ev(R % k + " s2 permissive transitive set"), ""),
    "L4": (ev(R % k + " s2 setuptools, no custom step"), ""),
    "L5": (ev(R % k + " s2 server optional"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "not a lab dependency; optional separate venv with MLFLOW_DISABLE_TELEMETRY=true"
DECISION[k] = "INSPIRED_IMPLEMENTATION"
ZERO_NOTES[k] = {"I": "duplicates the planned files-with-sha256 registry (I4 0); 558 MB (I5 0)", "L": "release telemetry on by default; DO_NOT_TRACK=1 does not stop it (L3 0)", "R": "no repeat run compared (R1 0)"}

# ---------------- skore ----------------
k = "probabl-ai__skore"
AW[k] = {
    "T4b": (ev(S % (k, "smoke_skore.out.txt") + " SKD011 names leak_future_ret; SKD013 flags shuffled KFold"), "SO-1"),
    "T6": (ev(S % (k, "smoke_skore.out.txt") + " LINEAGE data_refs with uuid7 report ids, UTC creation date and content-hashed train and test data"), ""),
    "C1": (ev(S % (k, "smoke_skore.out.txt") + " S2_probs Brier and log loss equal the harness"), ""),
    "D4": (ev(S % (k, "smoke_skore.out.txt") + " check codes SKD001 and others with issue and tip severities"), "SO-1"),
    "Q1": (ev(S % (k, "repo_tests_subset.out.txt") + " 34 passed with the hub extra"), ""),
    "Q2": (ev(R % k + " s3 SKD011, SKD013, SKD004 tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-21; 0.28.0 2026-10-14"), ""),
    "Q4": (ev(R % k + " s1 library installs and imports"), ""),
    "I1": (ev(S % (k, "smoke_skore.meta.json") + " python 3.13.17"), ""),
    "I2": (ev(R % k + " s1 pandas 3.1.0, numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s3 EstimatorReport"), ""),
    "I4": (ev(R % k + " s8 reports without the project store"), ""),
    "I5": (ev("verify/closure_size.py: closure 383.3 MB"), ""),
    "R1": (ev("verify/repeat_runs.json probabl-ai__skore: reviewer script re-run by the lead; 279 of 287 values identical, the 8 others are uuid7 report ids and creation dates by design"), "REPEAT"),
    "R2": (ev(S % (k, "smoke_skore.out.txt") + " S5_persist identical"), ""),
    "R4": (ev(S % (k, "smoke_skore.out.txt") + " LINEAGE metadata.json"), ""),
    "R5": (ev(S % (k, "smoke_skore.out.txt") + " metadata skore-version"), ""),
    "K1": (ev(S % (k, "smoke_skore.connect.txt") + " 0 inet connects"), ""),
    "K2": (ev(R % k + " s4 S6 report 0.05 s; checks 22 to 30 s for one report"), ""),
    "K3": (ev(R % k + " s4 234 MB"), ""),
    "K4": (ev(R % k + " s4 S6 py3-none-any"), ""),
    "L1": (ev(R % k + " s2 MIT sha256 1a326199"), ""),
    "L2": (ev(R % k + " s2 vendored BSD-2-Clause file"), ""),
    "L3": (ev(R % k + " s2 no telemetry, 0 connects"), ""),
    "L4": (ev(R % k + " s2 hatch hook inspected"), ""),
    "L5": (ev(R % k + " s2 hub and CLI network only on explicit use"), ""),
}
FLAGS[k] = "NOT_REALTIME (checks take tens of seconds)"
ROUTE[k] = "research venv with SKORE_WORKSPACE outside the repo; two checks reimplemented as hard gates"
DECISION[k] = "INSPIRED_IMPLEMENTATION"
ZERO_NOTES[k] = {"C": "calibration curve has no bin counts (C5 0)", "Q": "git_commit recorded as a wrong string outside a repository (Q5 0)", "R": "pickle storage (R3 0)"}

# ---------------- pandera ----------------
k = "unionai-oss__pandera"
AW[k] = {
    "T3": (ev(S % (k, "smoke_pandera.out.txt") + " P05_label_maturity: a labelled PENDING row refused"), ""),
    "T4a": (ev("verify/rerun_pandera.out.txt lead's own registered check: trap 3,000 rows refused, 1-second-late row caught", S % (k, "smoke_pandera.out.txt")), "PA-1"),
    "F1": (ev(S % (k, "smoke_pandera.out.txt") + " S3_nullable declared nullability enforced"), ""),
    "F5": (ev(S % (k, "smoke_pandera.out.txt") + " S2_forecast_schema typed forecast and S1_asof_gate feature schemas"), ""),
    "D4": (ev(S % (k, "smoke_pandera.out.txt") + " lazy failure cases: checks_failed, first_failure_index, n_failure_cases"), "PA-1"),
    "Q1": (ev(S % (k, "repo_tests_subset.out.txt") + " 56 passed"), ""),
    "Q2": (ev(R % k + " s3 checks, extensions, format conversions"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-23; 0.34.1 2026-10-06"), ""),
    "Q4": (ev(R % k + " s1 installs and imports"), ""),
    "Q5": (ev(R % k + " s4 fail-closed; lambda-check loss warned"), "PA-1"),
    "I1": (ev(S % (k, "smoke_pandera.out.txt") + " python 3.13"), ""),
    "I2": (ev(S % (k, "smoke_pandera.out.txt") + " pandas 3.1.0, numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s3 schema API"), ""),
    "I4": (ev(R % k + " s8 validator for the planned feature and label tables"), ""),
    "I5": (ev("verify/closure_size.py: closure 10.2 MB plus pandas"), ""),
    "R1": (ev("verify/repeat_runs.json unionai-oss__pandera: reviewer script re-run by the lead, identical after normalization"), "REPEAT"),
    "R2": (ev(S % (k, "smoke_pandera.out.txt") + " S5 YAML round trip keeps registered checks"), ""),
    "R3": (ev(S % (k, "smoke_pandera.out.txt") + " YAML schema (safe_load)"), ""),
    "R5": (ev("verify/rerun_pandera.out.txt strict=True refuses an undeclared column"), "PA-1"),
    "K1": (ev(S % (k, "smoke_pandera.connect.txt") + " 0 inet connects"), ""),
    "K2": (ev(R % k + " s4 0.036 s for 30,000 rows"), ""),
    "K3": (ev(R % k + " s4 189 MB"), ""),
    "K4": (ev(R % k + " s4 S6 pure wheel"), ""),
    "L1": (ev(R % k + " s2 MIT sha256 142d0a4e"), ""),
    "L2": (ev(R % k + " s2 permissive transitive set"), ""),
    "L3": (ev(R % k + " s2 no telemetry, 0 connects"), ""),
    "L4": (ev(R % k + " s2 bare setup()"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = ""
ROUTE[k] = "PyPI wheel imported lazily inside a small schemas module; registered checks only, strict=True"
DECISION[k] = "ADAPTER"
ZERO_NOTES[k] = {"R": "failure cases are not run records (R4 0)"}

# ---------------- MiroFish ----------------
k = "666ghj__MiroFish"
AW[k] = {
    "F5": (ev(S % (k, "sim_summary.json") + " typed SQLite tables post, like and trace with counts (sqlite_sequence listed)"), "MI-3"),
    "Q1": (ev(S % (k, "backend_pytest.txt") + " 129 passed"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-02; tag v0.1.2 2026-03-06 (lead git fetch)"), ""),
    "R3": (ev(S % (k, "sim_run1/simulation_config.json") + " JSON and SQLite outputs"), ""),
    "L3": (ev(R % k + " s2 no telemetry in MiroFish code; unstructured analytics not triggered"), ""),
    "L4": (ev(R % k + " s2 only sdists langdetect and docopt, plain setup()"), ""),
}
FLAGS[k] = "RESEARCH_ONLY (scenario hypotheses, no testable events, no accuracy evidence); LEAKAGE_FAIL (LLM pretraining knowledge, no as-of seeds); NOT_REALTIME; REJECT for in-process use, code copying and running the shipped service on a reachable network"
ROUTE[k] = "unmodified Reddit simulation script as a subprocess, own Python 3.12 venv, loopback-only namespace, mock or approved LLM; default SIMULATION_NOT_AVAILABLE"
DECISION[k] = "ISOLATED_RESEARCH"
ZERO_NOTES[k] = {"all": "no probability, no seed control, silent success when the LLM is down, AGPL, keys required, unauthenticated service on 0.0.0.0"}

# ---------------- OASIS ----------------
k = "camel-ai__oasis"
AW[k] = {
    "F5": (ev(S % (k, "smoke_run1.json") + " typed action trace: sign_up, create_post, refresh, do_nothing"), "OA-2"),
    "Q1": (ev(S % (k, "oasis_pytest_offline.txt") + " 31 passed; 1 needs an API key"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-19; camel-oasis 0.2.5 2025-12-04"), ""),
    "Q4": (ev(R % k + " s1 exact pins install"), ""),
    "I4": (ev(R % k + " s8 inside the planned behavioral boundary"), ""),
    "R3": (ev(S % (k, "smoke_run1.json") + " SQLite trace"), ""),
    "L1": (ev(R % k + " s2 Apache-2.0 sha256 950deb34"), ""),
    "L3": (ev(R % k + " s2 no telemetry in OASIS"), ""),
    "L4": (ev(R % k + " s2 wheels only"), ""),
}
FLAGS[k] = "RESEARCH_ONLY; LEAKAGE_FAIL (LLM agents, wall-clock time in prompts); NOT_REALTIME; route-level REJECT for the bundled data/twitter_dataset pickles (real propagation data, rights UNKNOWN; not loaded by the package)"
ROUTE[k] = "separate Python 3.11 venv and process, loopback-only, only if an LLM simulation is approved"
DECISION[k] = "ISOLATED_RESEARCH"
ZERO_NOTES[k] = {"all": "no outcome, no seed, swallowed LLM exceptions, GPL igraph imported, Python <3.12, LLM key needed"}

# ---------------- mesa ----------------
k = "mesa__mesa"
AW[k] = {
    "Q1": (ev(S % (k, "mesa_pytest_offline.txt") + " 411 passed"), ""),
    "Q2": (ev(R % k + " s3 model, agent, datacollector, scenarios, events tests"), ""),
    "Q3": (ev(R % k + " s1 commit 2026-10-22; 3.5.1 2026-03-15"), ""),
    "Q4": (ev(R % k + " s1 core dependencies"), ""),
    "Q5": (ev(R % k + " s4 none in the library (NaN handling is the smoke model's)"), ""),
    "I1": (ev(S % (k, "smoke_mesa_traders_output.json") + " python 3.13"), ""),
    "I2": (ev(R % k + " s1 pandas 3.1.0, numpy 2.5.4"), ""),
    "I3": (ev(R % k + " s3 in-process model API"), ""),
    "I4": (ev(R % k + " s8 inside the planned behavioral boundary"), ""),
    "I5": (ev("verify/closure_size.py venv 263 MB"), ""),
    "R1": (ev(S % (k, "smoke_mesa_traders_output.json") + " same seeds byte-identical frequency vector"), "ME-1"),
    "K1": (ev(S % (k, "commands.txt") + " All runs inside unshare -n with lo_up.py (loopback only)", R % k + " s4 S6"), ""),
    "K2": (ev(R % k + " s4 S6 0.78 ms per run"), ""),
    "K3": (ev(R % k + " s4 S6 102 MB"), ""),
    "K4": (ev(R % k + " s1 3.5.1 py3-none-any"), ""),
    "L1": (ev(R % k + " s2 Apache-2.0 sha256 cfc7749b"), ""),
    "L2": (ev(R % k + " s2 permissive core dependencies"), ""),
    "L3": (ev(R % k + " s2 none"), ""),
    "L4": (ev(R % k + " s2 binary-only dependency install"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = "RESEARCH_ONLY (any model built on it)"
ROUTE[k] = "numpy trader loop first; released Mesa 3.5.x only if heterogeneity grows"
DECISION[k] = "INSPIRED_IMPLEMENTATION"
ZERO_NOTES[k] = {"all": "a framework: the market model, its events and features are the smoke's own code"}

# ---------------- black-it ----------------
k = "bancaditalia__black-it"
AW[k] = {
    "Q4": (ev(R % k + " s1 wheel resolution installs"), ""),
    "I3": (ev(R % k + " s3 Calibrator API"), ""),
    "I4": (ev(R % k + " s8 offline fitting step"), ""),
    "R1": (ev(S % (k, "smoke_blackit_summary.json") + " same random_state byte-identical"), ""),
    "R3": (ev(S % (k, "smoke_blackit_summary.json") + " checkpoint_files calibration_params.json and calibration_results.csv", R % k + " s4 S5"), ""),
    "R4": (ev(S % (k, "smoke_blackit_summary.json") + " checkpoint_files (parameters, losses, series_samp.h5)", R % k + " s4 S5"), ""),
    "K1": (ev(S % (k, "commands.txt") + " All runs inside unshare -n with lo_up.py (loopback only)", R % k + " s4 S6"), ""),
    "K2": (ev(S % (k, "smoke_blackit_output.txt") + " 0.6 s per calibration"), ""),
    "K3": (ev(R % k + " s4 S6 165 MB"), ""),
    "L2": (ev(R % k + " s2 permissive transitive set"), ""),
    "L3": (ev(R % k + " s2 none"), ""),
    "L4": (ev(R % k + " s2 wheels only"), ""),
    "L5": (ev(R % k + " s2 none"), ""),
}
FLAGS[k] = "RESEARCH_ONLY (parameter estimates, not forecasts)"
ROUTE[k] = "own Python 3.12 venv and process, files in and out, never imported or copied"
DECISION[k] = "ISOLATED_RESEARCH"
ZERO_NOTES[k] = {"all": "AGPL; 6 golden tests fail; no commit in 11 months; Python <3.13; NaN moments set to 0"}
