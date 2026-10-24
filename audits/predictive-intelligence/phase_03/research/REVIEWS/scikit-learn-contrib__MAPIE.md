# Source review: scikit-learn-contrib/MAPIE (reviewer R2)

Synthetic challenge only. Every number below is a format and behaviour check on `challenge.csv` (sha256 `18fda40c...d5f23d`), never evidence of memecoin edge.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | scikit-learn-contrib/MAPIE, https://github.com/scikit-learn-contrib/MAPIE |
| Pinned SHA | `f1cc3d07460b2d7198f557d40d60cd563c51822b` (Phase 02 SHORTLIST.csv) |
| Commit date | 2026-10-19T10:27:36+02:00 (merge of PR #1010) |
| How fetched | `git init; git fetch --depth 1 origin <sha>; git checkout FETCH_HEAD` at 2026-10-24T04:33:43Z into `/home/claude/pi_research/src/scikit-learn-contrib__MAPIE`; HEAD verified equal to the pin |
| Review time (UTC) | 2026-10-24T04:33Z to 05:10Z |
| Version tested | built from the pinned source with `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_MAPIE=1.6.0+pinf1cc3d07` (the shallow clone has no tags), venv `/home/claude/pi_research/venvs/scikit-learn-contrib__MAPIE`, Python 3.13.17, numpy 2.5.4, scipy 1.18.1, scikit-learn 1.9.1, pandas 3.1.0 |
| Relation to PyPI | all 95 `.py` files of the PyPI wheel `mapie-1.6.0-py3-none-any.whl` (uploaded 2026-10-19T09:08:14, sha256 `6bb6b217f33f1301...`) are byte-identical to the pin, so the results also apply to the 1.6.0 release |

## 2. License and security

- Root `LICENSE`: BSD-3-Clause text, sha256 `92372faa472615c49bd4255fb56d998644e60b255b1093c7dad969ac70c1a60c` (matches Phase 02 LICENSE_SCAN.csv).
- Vendored code: `THIRD_PARTY_NOTICES.md` carries the MIT notices for code adapted from confseq (`mapie/exchangeability_testing/bounds.py`, header names the source) and reused from conditional-conformal (`mapie/conditional_conformal_prediction/`). `pyproject.toml` lists both files in `license-files`. Obligation if copied: keep the BSD-3 notice and both MIT notices.
- Runtime dependencies: numpy, scipy, scikit-learn only (all BSD-3). Optional extras pull torch and cvxpy; not installed and not needed for the classes tested. Installed dependency licenses: `SMOKES/scikit-learn-contrib__MAPIE/raw_dep_licenses.txt` (BSD, MIT, Apache-2.0, PSF only; pytest and typing_extensions were added by me for the repo tests).
- Model weights: none downloaded by any tested path. The docs extra lists huggingface-hub and torch for documentation examples only.
- Install-time scripts: none. Build is `setuptools` plus `setuptools-scm` from `pyproject.toml`; no `setup.py`.
- Network: no `requests`, `urllib`, `socket` or `http` use in `mapie/` outside tests (grep at the pin). Every smoke ran inside `unshare -n` (no network namespace) and completed. No telemetry code; nothing to switch off.
- Secrets: none handled.
- Persistence: no save format of its own; objects are pickled. Loading a pickle executes code, so only files the lab wrote itself may be loaded.

## 3. Code paths inspected at the pin

| Area | Anchor | Observation |
|---|---|---|
| Split conformal classifier | `mapie/classification.py:49` `SplitConformalClassifier`, `:190` conformalize, `:238` predict_set, backend `_MapieClassifier` `:623` | prefit mode takes any fitted estimator, so the wrapper decides which rows calibrate. Default `estimator=LogisticRegression()` is one instance shared as a default argument (`:124`, `:408`) |
| Binary scores | `mapie/conformity_scores/utils.py:123` | only "lac" is accepted for a binary target (APS/RAPS refused) |
| Venn-Abers wrapper | `mapie/calibration.py:636` `VennAbersCalibrator` | with a Pipeline estimator it slices the pipeline (`:989`) and calls `fit_transform` on the caller's own transformer objects (`:992`) before the prefit branch (`:1000`), so `cv="prefit"` refits the caller's imputer and scaler on the calibration rows |
| Venn-Abers core | `mapie/_venn_abers.py:19` `calc_p0p1`, `:151` `calc_probs`, `:397` `VennAbers` (`fit` at `:459` returns None) | the p1 loop (`:104` to `:123`) lacks the `p1[-1, 1] = 1.0` line that the reference implementation added in venn-abers 1.5.4 (`ip200/venn-abers src/venn_abers.py:118`); no NaN check in `calc_probs` |
| Calibration metrics | `mapie/metrics/calibration.py:105` `expected_calibration_error`; edges `np.linspace(0, 1, num_bins)` (`:46`) with `np.digitize(right=True)` (`:86`); Spiegelhalter, KS and Kuiper tests `:499` to `:878` | `num_bins=10` gives 9 usable intervals of width 1/9 (bin 0 holds only scores at 0) |
| Time handling | `mapie/utils.py:28` `train_conformalize_test_split` (default `shuffle=True`); `mapie/regression/time_series_regression.py:20` `TimeSeriesRegressor` (EnbPI/ACI, regression only); `mapie/subsample.py:104` `BlockBootstrap` (regression ensembles) | no feature-availability check, no purge or embargo, nothing about label maturity |
| Exchangeability tests | `mapie/exchangeability_testing/permutations.py:270` `PValuePermutationTest`, statistic `:34`; an unfitted estimator is fitted on the first 30% of the rows (`:240`, `shuffle=False`) | tests the conformity-score sequence for a mean shift |
| Risk control | `mapie/risk_control/binary_classification.py:24` `BinaryClassificationController` | Learn-then-Test threshold selection with a guarantee; returns no threshold when none is valid |
| Serialization | none | pickle or joblib only |
| Tests | 63 test files at the pin | ran `mapie/tests/test_calibration.py` and `test_metrics.py` from the installed package: 234 passed in 27.11 s, exit 0 (`SMOKES/scikit-learn-contrib__MAPIE/raw_repo_tests_mapie.txt`; `test_metrics.py` needed the dev dependency typing_extensions) |

## 4. Smoke results

Script `SMOKES/scikit-learn-contrib__MAPIE/smoke_mapie.py` (with `common.py`, `runner.py`), command `python3 runner.py raw_smoke_mapie.txt -- <venv>/bin/python -I smoke_mapie.py` inside `unshare -n`; exit 0, wall 13.55 s, peak RSS 165.9 MB; raw output `SMOKES/scikit-learn-contrib__MAPIE/raw_smoke_mapie.txt`. Shared base model: Pipeline(SimpleImputer median, StandardScaler, LogisticRegression) on the six legitimate features (log1p on liq_usd and vol_24h), fit on train rows whose label matured before the first val decision (96 train rows purged), calibration on val rows whose label matured before the first holdout decision (45 val rows purged; 511 rows, 16 positives), holdout 527 labeled rows (17 positives), 107 censored rows excluded. Holdout base predictions hash `cc58f5135049e5ed`, identical in the crepes, venn-abers, model-diagnostics and arch smokes.

| ID | Result | Numbers |
|---|---|---|
| S1 leak trap | FAIL (no guard in the library) | `leak_available_at > decision_time` in 3000 of 3000 rows. Base holdout BSS 0.0123 (AUC 0.6988); with the trap column BSS 0.9452 (AUC 1.0000). `SplitConformalClassifier` and `VennAbersCalibrator` accepted the trap column (leaky Venn-Abers BSS 0.9221). Exclusion by availability time has to happen in the lab's wrapper |
| S2 probability shape and imbalance | PASS | shape (527,), finite, in [0, 1] (min 0.0008, max 0.3236). Brier 0.03089 vs train-prevalence baseline 0.03128 (BSS 0.0123); log loss 0.13763 vs 0.14334. Calibration in the large: mean p 0.0356, prevalence 0.0323, Wilson 95% (0.0202, 0.0510), inside |
| S3 missing covariates | PASS (defers to the estimator) | 77 holdout rows have a NaN feature. MAPIE does not impute: a bare LogisticRegression raises `ValueError: Input X contains NaN`; NaN rows pass through a Pipeline with SimpleImputer and through HistGradientBoosting. The Venn-Abers core returns `[0.5, 0.5]` for a NaN score without an error (P38) |
| S4 calibration and uncertainty | PARTIAL | LAC sets, confidence 0.90: coverage 0.9184 (library score agrees) but 0 of 17 positives covered; sets: 498 `{0}`, 29 empty, no `{1}`, no `{0,1}`. Confidence 0.95: coverage 0.9431, 0 of 17 positives. Venn-Abers (MAPIE port, prefit on the same scores): Brier 0.03261 (BSS -0.0427), log loss 0.13905, ECE 10 uniform bins 0.01287, 5 quantile bins 0.01488, all 5 quantile bins inside Wilson; p1 - p0 median 0.0075, p90 0.0210, max 0.5342. Definition check against an isotonic refit with the test score appended (530 probe scores): p0 exact, p1 wrong for scores above the largest calibration score (MAPIE 0.6000, definition 1.0000; 6 probes, 4 of them holdout rows). Passing the Pipeline with `cv="prefit"` changed the caller's base predictions (max abs change 0.0106, imputer refit on val) |
| S5 persistence | PASS | pickle of the conformal and Venn-Abers objects, 31,848 bytes; identical sets and probabilities after reload. Pickle only |
| S6 cost | PASS | base fit 40 to 170 ms across runs; conformalize 1.8 to 6.9 ms; predict_set 2.2 to 17.4 us per row; Venn-Abers fit 5 to 24 ms, predict 1.7 to 1.9 us per row; peak RSS 166 MB; runs with no network. PyPI ships one `py3-none-any` wheel; Python 3.13 declared and tested; Windows uses the same pure-Python wheel (numpy, scipy, scikit-learn have win_amd64 wheels). File list: `SMOKES/scikit-learn-contrib__MAPIE/raw_pypi_files_r2.txt` |
| Role: exchangeability | no false alarm, shift not detected | permutation test on time-ordered LAC scores (200 permutations): val only p = 0.8905 (exchangeable); val then holdout p = 0.7264 (exchangeable) although liq_usd shifts (mean log1p 10.016 to 10.820); mean LAC score 0.0667 vs 0.0639, so the score sequence barely moves |
| Role: risk control | abstains | precision at least 0.10 or 0.20 with 90% confidence: no valid threshold on 16 calibration positives; the controller returns none and warns |

Reliability bins, holdout, 10 uniform bins (n, mean p, observed, positives, Wilson 95%):

| Bin | Base n | Base mean p | Base observed | Base pos | Venn-Abers n | VA mean p | VA observed | VA pos |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| [0.0, 0.1) | 500 | 0.0295 | 0.0280 | 14 | 512 | 0.0323 | 0.0293 | 15 |
| [0.1, 0.2) | 23 | 0.1330 | 0.1304 | 3 | 5 | 0.1713 | 0.0000 | 0 |
| [0.2, 0.3) | 3 | 0.2118 | 0.0000 | 0 | 0 | | | |
| [0.3, 0.4) | 1 | 0.3235 | 0.0000 | 0 | 3 | 0.3769 | 0.6667 | 2 |
| [0.5, 0.6) | 0 | | | | 7 | 0.5000 | 0.0000 | 0 |

ECE (count-weighted, 10 uniform bins): base 0.00331, Venn-Abers 0.01287. MAPIE's own `expected_calibration_error(num_bins=10, "uniform")` returns the same values although its bins differ, because every bin has observed below mean p, so any binning gives |mean p - prevalence|. Spiegelhalter p 0.6215 (base), 0.6746 (Venn-Abers); KS p 0.9960, 0.4882.

## 5. Claims the code does not support (P42)

- UNSUPPORTED: `VennAbersCalibrator` docstring, "well-calibrated probabilities with validity guarantees" and "based on the reference implementation by the user ip200". The port departs from the reference and from the inductive Venn-Abers definition for test scores above every calibration score (S4: p1 0.6 instead of 1.0).
- UNSUPPORTED: same docstring, "Prefit Venn-ABERS: estimator is already fitted, only calibration is performed". For a Pipeline the transformers are refit on the calibration data and the caller's object is changed (S4).
- UNSUPPORTED: README "MAPIE runs on Python >=3.9"; `pyproject.toml` requires `>=3.10`.
- Not contradicted but limited here: README "exchangeability tests ... help users verify when MAPIE can be legitimately applied". The test ran correctly and gave no false alarm, but did not flag this challenge's covariate shift on LAC scores.
- The coverage guarantee is marginal. Marginal coverage held (0.9184 at 0.90) while the minority class had 0 of 17 covered; nothing in the README claims class-conditional coverage for binary targets.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 2 | exchangeability tests exist and run (val p = 0.8905, no false alarm) but missed the holdout shift; no feature-time check (S1 trap accepted), no purge, `train_conformalize_test_split` shuffles by default (`mapie/utils.py:28`) |
| Transferable measurable predictive outcomes (14) | 3 | wraps any binary classifier into sets and calibrated probabilities (S2, S4); regression intervals exist (not tested); produces no outcome model itself |
| Calibration, uncertainty and abstention (12) | 7 | split conformal sets, Venn-Abers, ECE/Spiegelhalter/KS tests (S4, agree with own computation), risk control that abstains (role row); minus: Venn-Abers port defect and Pipeline mutation (S4), binary limited to LAC with 0 of 17 positives covered |
| Catalyst, social and on-chain features (10) | 0 | none |
| Decision and execution compatibility (10) | 1 | `BinaryClassificationController` gives alert thresholds with a precision guarantee and returned no threshold rather than a false one on 16 positives (role row); no execution or fee notion |
| Code quality, maintenance and tests (8) | 6 | 63 test files, 234 calibration and metric tests pass; release 1.6.0 on 2026-10-19; minus the defects found in S4 and a shared mutable default estimator (`classification.py:124`) |
| Integration fit and extensibility (8) | 6 | pure Python, numpy/scipy/scikit-learn only, Python 3.13 works, scikit-learn API (S6); the lab has no scikit-learn yet (GAP_MATRIX MODEL_TRAINING MISSING) |
| Experiment reproducibility and audit (8) | 3 | deterministic given the inputs, `random_state` parameters, pickle reload identical (S5); no lineage, run registry or saved transformation metadata |
| Cost, latency and operational reliability (5) | 5 | millisecond fits, microsecond predictions, 166 MB, fully offline (S6) |
| Licensing, security and data rights (7) | 6 | BSD-3 with vendored MIT notices present, no network, no install scripts (section 2); fitted state is only persistable as pickle |
| **Total** | **39** | |

## 7. Flags and adversarial scenarios

- Flags: none of REJECT, RESEARCH_ONLY, NOT_REALTIME. Not LEAKAGE_FAIL as a component: prefit mode accepts exactly the purged calibration rows the wrapper builds (S2, S4), but the library itself enforces nothing (S1).
- P10: marginal coverage met while minority coverage was 0 of 17; LAC sets cannot flag the rare positive at this prevalence.
- P24: 16 calibration positives; Venn-Abers made Brier worse than the base (BSS -0.0427) and the risk controller found no valid threshold.
- P36 and P13: the trap column and any future-trained artifact pass through unchecked; the wrapper must refuse them.
- P38: a NaN score yields 0.5 from the Venn-Abers core with no error.
- P31: vendored MIT code carries its notices; pass. P32: no install scripts; pickle trust boundary noted.
- P42: four documentation claims listed in section 5.
- New wrong-but-plausible case found: a calibrator that silently refits the model's preprocessing on calibration data (Pipeline plus `cv="prefit"`) changes the base model's holdout predictions; caught by comparing the base prediction hash before and after `fit`.

## 8. Proposed role and integration decision

Offline evaluation helper for Phases 08 to 12, never in the forecast path: Spiegelhalter/KS calibration tests, the exchangeability permutation test as an extra check next to a drift monitor, and `BinaryClassificationController` if alert thresholds are ever needed (it abstains on small data). Split conformal LAC sets add little for a 3 to 4% event. Do not use the MAPIE Venn-Abers port until the p1 defect is fixed; never pass a Pipeline to `VennAbersCalibrator`.

Candidate INTEGRATION_DECISION: ADAPTER (offline only, prefit mode with wrapper-built purged calibration sets). Phase 01 gap cells addressed: DECISION_RECORDS:CALIBRATION_SCORING (MISSING), HIST_MARKET:CALIBRATION_SCORING (MISSING), SOCIAL_REPLAY:CALIBRATION_SCORING (PARTIAL), TRADE_OUTCOMES:CALIBRATION_SCORING (PARTIAL). License obligation if code is copied: BSD-3 notice plus the two MIT notices in `THIRD_PARTY_NOTICES.md`.
