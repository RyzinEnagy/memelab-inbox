# Source review: scikit-learn/scikit-learn

Reviewer R1, Phase 03. Smoke data are the shared synthetic challenge (`challenge.csv`, sha256 `18fda40cc7a2a6f5aa607a32f1a096976317f901f5b75d1ae23b4bcaddd5f23d`): results show format and behaviour only, never memecoin predictive value. Holdout scored rows: 527 (17 positives, prevalence 0.0323); 107 censored holdout rows excluded, never scored as negatives; training prevalence B0 = 0.04238.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | scikit-learn/scikit-learn, https://github.com/scikit-learn/scikit-learn |
| Pinned SHA | `59106029d483678e79825f753bde67f8ade4332b` |
| Commit date | 2026-10-23T15:36:06+02:00 ("DOC fix soft-threshold and dual objective in Lasso coordinate descent docs (#35136)") |
| How fetched | `git init; git fetch --depth 1 https://github.com/scikit-learn/scikit-learn.git <sha>; git checkout FETCH_HEAD` into `/home/claude/pi_research/src/scikit-learn__scikit-learn` (38 MB) |
| Review time (UTC) | 2026-10-24T04:33Z to 05:45Z |
| Version tested | built from the pinned source: `uv pip install <clone>` (meson-python, Cython; build 4 min 34 s, exit 0) into `/home/claude/pi_research/venvs/scikit-learn__scikit-learn` (Python 3.13.17). `sklearn.__version__` = `1.10.dev0` (sklearn/__init__.py:45 at the pin). This is the pin, not a PyPI release. Latest release 1.9.1 (2026-09-10) differs from the pin in 577 files; `sklearn/calibration.py` alone differs by 359 lines and `sklearn/linear_model/_logistic.py` by 1,557 lines (`git diff --stat 1.9.1 HEAD`). |
| Build scripts inspected before building | `meson.build:4` runs `sklearn/_build_utils/version.py` (reads `__version__`); `sklearn/meson.build` runs `_min_dependencies.py` and inline Python that reads compiler env vars. No network or file writes outside the build dir. |

## 2. License and security

| Item | Finding |
|---|---|
| Root license | `COPYING` at the pin: BSD 3-Clause, "Copyright (c) 2007-2026 The scikit-learn developers" (read at the pin) |
| Vendored or nested | `sklearn/externals/array_api_extra/LICENSE` MIT, `sklearn/externals/array_api_compat/LICENSE` MIT, `sklearn/svm/src/liblinear/COPYRIGHT` BSD-3-Clause; MIT grants in `sklearn/externals/_arff.py` and `doc/sphinxext/sphinx_issues.py` (Phase 02 LICENSE_SCAN). `build_tools/wheels/LICENSE_*.txt` describe bundled runtime libraries in release wheels (OpenMP runtime); not part of a source build |
| Runtime dependencies at the pin | numpy 2.5.4 (BSD-3-Clause and others), scipy 1.18.1 (BSD-3-Clause), joblib 1.6.0 (BSD-3-Clause), narwhals 2.27.1 (MIT), threadpoolctl 3.7.0 (BSD-3-Clause) |
| Model weights | none |
| Install-time scripts | meson build only (inspected above) |
| Network at import, fit, predict | none observed: network guard recorded 0 connect attempts at import and over the whole smoke (`SMOKES/scikit-learn__scikit-learn/smoke_output.txt`, `network_attempts: []`). Network code exists only in dataset fetchers: `sklearn/datasets/_openml.py:183` (urlopen), `sklearn/datasets/_base.py:1462` (urlretrieve) |
| Telemetry | none found (no telemetry or analytics code under `sklearn/`) |
| Persistence safety | pickle and joblib execute code on load; the project says so itself (`doc/model_persistence.rst:31-44`, "Loading can execute arbitrary code") and points to skops or ONNX (`doc/model_persistence.rst:58-70`) |
| Secrets | none handled |

## 3. Code paths inspected at the pin

| Area | Anchor | Note |
|---|---|---|
| Logistic fit / proba | `sklearn/linear_model/_logistic.py:1135` class, `:1580` fit, `:1881` predict_proba | at the pin `C` is deprecated in favour of `alpha` (FutureWarning at `_logistic.py:1615`; 42 such warnings in the smoke stderr) |
| Gradient boosting with native NaN | `sklearn/ensemble/_hist_gradient_boosting/gradient_boosting.py:394` fit, `:1769` HistGradientBoostingClassifier, `:2148` predict_proba | missing values get their own bin (`:616-618`) |
| Calibration | `sklearn/calibration.py:179` CalibratedClassifierCV, `:448` fit, `:623` predict_proba, `:798` `_fit_calibrator`, `:842` isotonic calibrator with `out_of_bounds="clip"`, `:1107` `_SigmoidCalibration`, `:1162` `_TemperatureScaling`, `:1328` calibration_curve | `ensemble="auto"` turns into False for a FrozenEstimator (`:476-477`); default `cv=None` resolves to 5-fold StratifiedKFold (`calibration.py:254-266`, `_split.py:2730-2737`) |
| Frozen (prefit) estimator | `sklearn/frozen/_frozen.py:27` FrozenEstimator | lets a model fitted on an earlier window be calibrated on a later one |
| Time splitter | `sklearn/model_selection/_split.py:1104` TimeSeriesSplit, `:1224` split (groups ignored with a warning at `:1247-1251`), `:1254` `_split`, `:1292-1306` train end = test start minus `gap` rows | counts rows, assumes rows are already in time order, knows nothing about timestamps or label maturity |
| Custom splits | `_split.py:2621` `_CVIterableWrapper`, `:2674` check_cv | any iterable of (train, test) index pairs is accepted, which is how a day walk-forward with maturity embargo can be supplied |
| cross_val_predict partition rule | `sklearn/model_selection/_validation.py:1195` | raises for non-partition splitters, so `CalibratedClassifierCV(ensemble=False)` cannot use TimeSeriesSplit |
| Proper scores | `sklearn/metrics/_classification.py:3318` log_loss, `:3708` brier_score_loss | |
| Serialization | `sklearn/base.py:499` `__getstate__` adds `_sklearn_version`, `:521-529` `__setstate__` warns InconsistentVersionWarning | |
| Tests | 260 `test_*.py` files under `sklearn/**/tests`; `sklearn/tests/test_calibration.py` 55 test functions, `sklearn/model_selection/tests/test_split.py` 73 | subset run at the pin: `pytest --pyargs sklearn.tests.test_calibration sklearn.model_selection.tests.test_split -k "calibrat or time_series or TimeSeries"`: 137 passed, 138 skipped (array-API variants without torch/cupy), exit 0, 14 s (`SMOKES/scikit-learn__scikit-learn/repo_tests_subset.txt`) |

## 4. Smoke results

Script `SMOKES/scikit-learn__scikit-learn/smoke_sklearn.py`, raw output `smoke_output.txt` (JSON line), stderr `smoke_stderr.txt`, run line `smoke_run.txt`. Command: `OMP_NUM_THREADS=1 <venv>/bin/python -I smoke_sklearn.py challenge.csv <scratch>`, exit 0, wall 8.7 s, peak RSS 143.3 MB (resource.ru_maxrss). An earlier identical run without `OMP_NUM_THREADS=1`, while a source build ran beside it (`smoke_output_run1.txt`, wall 130.5 s), gave the same metrics but 11.9 s for the HGB fit (thread oversubscription).

| Smoke | Result | Numbers |
|---|---|---|
| S1 leak trap | FAIL (library stops nothing, as expected) | trap available after the decision in 3,000 of 3,000 rows. Logistic: holdout BSS 0.0104, AUC 0.696 without the trap; BSS 0.9494, AUC 1.000 with it. HGB: BSS -0.0245 without, 0.8902 with. No availability-time concept; the wrapper must drop the column |
| S1 splitters | PARTIAL | TimeSeriesSplit(5) on 2,302 dev rows: training rows whose label matures after the test start, per fold: gap 0 rows [102, 106, 93, 99, 107]; gap 50 [52, 56, 43, 49, 57]; gap 100 [2, 6, 0, 0, 7]; gap 150 [0, 0, 0, 0, 0]. A row gap only works when the row rate is known. `groups` ignored with a warning. GroupKFold by mint put 1,834 to 1,842 later rows in each training fold. A custom day walk-forward iterable (19 folds, training only on labels matured by the test day's first decision) ran through `cross_val_score` with 0 maturity violations |
| S2 probability shape | PASS | `predict_proba` shape (527, 2), rows sum to 1, all finite, all in [0, 1]. Logistic Brier 0.030994 vs B0 0.031320, log loss 0.1383 vs 0.1439. HGB Brier 0.032087 (worse than B0) |
| S3 missing covariates | PASS | LogisticRegression on raw NaN: `ValueError: Input X contains NaN.`; SimpleImputer pipeline works; HistGradientBoosting fits natively, 77 holdout rows with NaN all finite |
| S4 calibration | PASS with caveats | HGB fit on train, calibrated on the later val window with FrozenEstimator. Sigmoid: Brier 0.030943 (BSS 0.0120), 3 of 3 quantile bins inside the Wilson 95% interval. Isotonic: BSS 0.0037, 2 of 3 bins, and `min_p` exactly 0.0 (a hard 0 probability, P38). Temperature: BSS -0.0420, 0 of 3 bins. Uncalibrated HGB: 1 of 3 bins. Default `cv=None` (non-temporal StratifiedKFold) ran without complaint. `ensemble=False` with TimeSeriesSplit: `ValueError: cross_val_predict only works for partitions`. Walk-forward iterable with `ensemble=True`: 19 calibrator pairs, BSS 0.0075. `calibration_curve` returns no bin counts. No conformal set, interval or abstention method in the library |
| S5 persistence | PASS (unsafe format) | pickle 271,455 bytes and joblib 284,068 bytes reload with identical predictions; state carries `_sklearn_version` = `1.10.dev0`. Pickle bytes differed between the two runs (sha256 `d7725338...` in run 1, `24598515...` in the final run) although predictions were identical, so an artifact sha256 is not reproducible across fits. skops and ONNX are separate packages: SKIPPED |
| S6 cost | PASS | fit: logistic pipeline 0.0074 s, HGB 0.19 s (1,746 rows, 1 thread). Batch predict 0.012 to 0.018 ms per row; single-row median 0.82 ms (logistic), 1.12 ms (HGB), 1.91 ms (calibrated); offline; Python 3.13 and Windows: 1.9.1 has `cp313-win_amd64` and `cp313-win_arm64` wheels on PyPI |

## 5. Claims the code does not support (P42)

- None found among the claims relevant here. The docs describe `TimeSeriesSplit.gap` as "Number of samples to exclude" (`_split.py:1140-1142`), which matches the code; it is a row count, not a time embargo, and the docs do not claim otherwise.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity (18) | 6 | Custom walk-forward iterables accepted with 0 maturity violations, FrozenEstimator allows train-then-calibrate on a later window; but TimeSeriesSplit is row based (93 to 107 violations at gap 0), groups ignored, default calibration cv is non-temporal, no availability or maturity concept, leak trap passed straight through (BSS 0.0104 to 0.9494) |
| Transferable predictive outcomes (14) | 7 | Binary event probabilities from logistic and HGB with correct shape; regression available; no survival, censoring or competing risks |
| Calibration and uncertainty (12) | 7 | Brier and log loss, Platt, isotonic and temperature calibration, FrozenEstimator; sigmoid passed 3 of 3 Wilson bins; isotonic emitted a hard 0; temperature failed; no intervals, conformal or abstention; calibration_curve has no counts |
| Catalyst, social, on-chain features (10) | 2 | Native NaN in HGB and imputers; nothing for irregular timestamps, event covariates or cross-token features |
| Decision and execution compatibility (10) | 2 | `sample_weight` reaches estimator and calibrator (`calibration.py:448-515`) and custom scorers exist; no execution or cost hooks |
| Code quality, maintenance, tests (8) | 7 | 260 test files, 137 relevant tests pass at the pin, commits daily, releases 1.9.0 (2026-06-02) and 1.9.1 (2026-09-10); API churn at the pin (`C` deprecated) |
| Integration fit (8) | 7 | Builds and runs on Python 3.13, numpy and scipy are already lab dependencies, three small extra deps, sklearn estimator API fits the planned `models.py` seam |
| Reproducibility and audit (8) | 4 | Identical metrics across two runs, `random_state`, version stamp and mismatch warning on unpickle; pickle bytes not stable across runs; no run ledger or lineage |
| Cost, latency, reliability (5) | 5 | Sub-second fits, about 1 ms single-row inference, 143 MB peak, no network, Windows cp313 wheels |
| Licensing, security, data rights (7) | 6 | BSD-3-Clause verified, permissive vendored code, no telemetry; pickle is the native format (code execution on load), mitigated only by loading local files the lab wrote |
| Total | 53 | |

## 7. Flags and adversarial scenarios

- Flags: none of REJECT, RESEARCH_ONLY, NOT_REALTIME. Not LEAKAGE_FAIL because strict as-of evaluation can be configured (custom iterable plus FrozenEstimator), but the defaults leak: `CalibratedClassifierCV(cv=None)` and `TimeSeriesSplit` without a time-aware gap must be banned in the wrapper.
- P13 (model trained from the future): the library cannot detect it; the S1 splitter counts show how TimeSeriesSplit with a small row gap trains on unmatured labels. The wrapper must record and check a training cutoff.
- P38 (probability outside [0,1], NaN or degenerate): isotonic calibration produced exact 0.0 probabilities on holdout rows; the lab's display clip [0.01, 0.99] and log-loss clip are needed.
- P20 (overlapping horizons): handled only by the custom walk-forward iterable, not by the library.
- P42: no README-only claim used for scoring.
- P31, P32: BSD-3-Clause, build scripts inspected, nothing destructive.

## 8. Proposed role and integration decision

- Role: baseline B2 (logistic regression on a few as-of features), the B3 Platt calibration of the 100-point score, the calibration layer for any later model (train on the training window, calibrate on a later window with FrozenEstimator and `method="sigmoid"`), and proper-score helpers. Splitting stays custom: the lab's day walk-forward with maturity embargo is passed in as an iterable.
- INTEGRATION_DECISION: INSTALL (pin a release wheel; never load a pickle the lab did not write; record artifact sha256 at save time rather than expecting byte-identical refits).
- Gap cells addressed: DECISION_RECORDS:MODEL_TRAINING, HIST_MARKET:MODEL_TRAINING, DECISION_RECORDS:CALIBRATION_SCORING, HIST_MARKET:CALIBRATION_SCORING, SOCIAL_REPLAY:MODEL_TRAINING, SOCIAL_REPLAY:CALIBRATION_SCORING (needs N01, N02; N04 only through a custom splitter).
