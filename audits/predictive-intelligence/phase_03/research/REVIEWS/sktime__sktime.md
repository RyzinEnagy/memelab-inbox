# sktime/sktime (reviewer R3)

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | sktime/sktime, https://github.com/sktime/sktime |
| Pinned SHA | `2cc1253c7f032494ec278c60662596944e053369` |
| Commit date | 2026-10-23T15:07:10+02:00 |
| How fetched | `git fetch --depth 1 --filter=blob:none` of the SHA with a sparse checkout of the relevant paths, then `git sparse-checkout disable` to materialize the tree (81 MB, 1,865 `.py` files) at `/home/claude/pi_research/src/sktime__sktime`; tag `v1.2.0` (commit `3dd7ef4c...`) fetched blob-less for a diff |
| Review time (UTC) | 2026-10-24T05:30Z to 05:45Z |
| Version tested | the pin: `sktime/`, `pyproject.toml`, `LICENSE`, `README.md` copied to scratch and installed with `uv pip install --no-deps .` (setuptools backend, version string 1.2.0); core dependencies only from PyPI wheels: joblib 1.6.0, numpy 2.5.4, pandas 3.0.5 (the lab's version), scikit-base 1.1.1, scikit-learn 1.9.1, scipy 1.18.1; Python 3.13.17. Venv `/home/claude/pi_research/venvs/sktime__sktime` (277 MB). Package data files (`sktime/datasets/data/*`) were not copied by this install |
| Relation to releases | PyPI 1.2.0 was uploaded 2026-09-22; the pin is past tag v1.2.0, including `sktime/datatypes/_vectorize.py` (407 lines changed), `sktime/classification/base.py` and `sktime/split/testplustrain.py`, so the pin itself was tested |

## 2. License and security

- Root `LICENSE` at the pin: BSD 3-Clause, "Copyright (c) 2019 - present, The sktime developers", sha256 `4f5bdd0f809b9e09f22eab0459a5b8f35fc18fc0207eeadbc2f6107288d2132d`.
- Phase 02 LICENSE_SCAN leads, checked at the pin: `sktime/classification/shapelet_based/_mrseql.py:12` "mrseql itself is copyleft (GPL3). This interface is permissive license (BSD3)" (the GPL code is a separate pip soft dependency); `sktime/forecasting/tirex.py` header: wraps TiRex "licensed under the NXAI Community License" (source-available) via a pip dependency; vendored `sktime/libs/*` (uni2ts, falcon_tst, sundial, mira and others) carry Apache-2.0 or MIT headers. None of these is imported by the core paths used here.
- Model weights: foundation-model forecasters (`sktime/forecasting/lagllama.py`, `moirai.py`, `moirai2.py`, `ttm.py`, `tirex2.py`, `kronos.py`, `windfm.py`, `falcon_x.py`, and `sktime/libs/timesfm`, `momentfm`) fetch weights from Hugging Face or similar at use time; their terms were not read and are UNKNOWN; not needed for the lab's role.
- Core dependencies: joblib, numpy, pandas, scikit-base, scikit-learn, scipy (all BSD-3), packaging (Apache-2.0 or BSD-2).
- Install-time scripts: none (setuptools, pure Python).
- Network: no network at import or in the tested paths (all runs under `unshare -n`); network code exists in dataset downloaders (`sktime/datasets/_dataset_downloader.py`, `_fpp3_loaders.py`) and the weight-downloading wrappers above. No telemetry found by grep.
- Serialization: `BaseObject.save()` (`sktime/base/_base.py:258`) pickles or cloudpickles; on disk a zip of pickles; unsafe for untrusted files.

## 3. Code paths inspected at the pin

| Concern | Anchor |
|---|---|
| Splitters | `sktime/split/expandingwindow.py:14` `ExpandingWindowSplitter(fh, initial_window, step_length)` (windows as int or timedelta); `sktime/split/expandingcutoff.py:36` `ExpandingCutoffSplitter`; `sktime/split/cutoff.py:103` `CutoffSplitter`; `sktime/split/instance.py:18` `InstanceSplitter` (splits instances of a panel with a scikit-learn CV, ignores time); `sktime/split/base/_base_splitter.py:141` `_split`, `:245` `split_series`. Grep of `sktime/split/` for gap, embargo or purge finds nothing: a gap can only be emulated by offsetting `fh` |
| Forecast evaluation | `sktime/forecasting/model_evaluation/_functions.py:430` `evaluate`; `:249` fit on the training fold; `:289` `method(fh=fh, X=X_test, ...)`: exogenous rows of the test period are passed to `predict`, i.e. treated as known at the cutoff |
| Classification | `sktime/classification/base.py` (fit, `predict_proba`), capability tags `capability:unequal_length`, `capability:missing_values`; `sktime/classification/distance_based/_time_series_neighbors.py:149` sets the class tag `capability:unequal_length` True while its docstring (`:36-49`) says the default string distances cannot handle unequal length |
| Panel data checks | `sktime/datatypes` `check_is_mtype(..., return_metadata=True)` reports `is_equal_length`, `is_equally_spaced`, `has_nans` |
| Calibration and uncertainty | no classifier calibration in core; `sktime/forecasting/conformal.py:23` `ConformalIntervals` (forecasting only; not smoke-tested because forecasting failed on irregular series, see D) |
| Serialization | `sktime/base/_base.py:258` `save`, `:342` `load_from_serial`, `:358` `load_from_path`; `sktime.base.load` |
| Tests | 432 `test_*.py` files in the tree. Ran `sktime/split/tests/test_expandingwindow.py`, `test_cutoff.py`, `test_temporaltraintest.py`, `test_expandingcutoff.py` from the installed pin: 1,417 passed, 2 skipped, 2 failed, exit 1, 15.7 s. Both failures are `FileNotFoundError` for `sktime/datasets/data/Airline/Airline.csv`, a data file R3's install did not copy, not a library defect (`SMOKES/sktime__sktime/repo_tests.out.txt`) |

## 4. Smoke results

Script `SMOKES/sktime__sktime/smoke_sktime.py` (sha256 `4e998a36...`), helper `r3_common.py`, runner `run_smoke.py`. Final command `unshare -n <venv>/bin/python -I -B smoke_sktime.py`, exit 0, wall 9.4 s, peak RSS 206.1 MB, user CPU 9.7 s. Raw: `smoke_sktime.out.txt`, `smoke_sktime.result.json` (sha256 `d8c93685...`). The first run recorded a `TypeError` from `InstanceSplitter` when given a `pd.Series` with a (mint, time) MultiIndex; the final run passes a DataFrame. Data: (a) challenge.csv decision rows on a UTC DatetimeIndex of `decision_time` (3,000 rows, monotonic, 2 duplicate timestamps, no inferable frequency); (b) a panel of 289 decision windows (last up to 24 kept candles of log return before a seeded decision, unequal length, irregular timestamps) from the seeded paths, R3 synthetic label "close rises 5% within the next 12 candles" (145 positives), split 70/30 by decision time.

| Smoke | Result | Numbers |
|---|---|---|
| Splitter, row-count expanding window | PASS on order, FAIL on label maturity | `ExpandingWindowSplitter(fh=1..100, initial_window=1000, step_length=400)`: 5 folds, time gap between train end and test start 36 to 1,237 s; each training fold holds 84 to 116 rows whose 24 h label had not matured at the test start (P20) |
| Splitter, timedelta windows on irregular index | FAIL | `ExpandingWindowSplitter(fh=[1 day], initial_window=12 days, step_length=3 days)`: `KeyError: Timestamp('2026-10-03 14:27:48+0000')`, 0 folds |
| Splitter, gap via `fh` offset of 100 rows | PARTIAL | gaps of 76,245 to 95,535 s, still 0 to 15 unmatured training labels per fold: a row-count gap is not a time embargo on irregular decisions |
| Splitter, expanding cutoff at a timestamp | PASS on order, FAIL on label maturity | 4 folds, 91 to 115 unmatured training labels per fold |
| Group split by mint | PASS (group only) | `InstanceSplitter(KFold(3))` on a (mint, time) DataFrame: 3 folds, 0 mints shared between train and test; time order inside folds not enforced |
| S1 leak trap | FAIL (nothing stops it) | scikit-learn logistic regression over the 5 row-count folds: mean fold Brier 0.00355 with `leak_future_ret` versus 0.03357 without (prevalence baseline 0.03471). sktime has no feature availability notion; forecasting `evaluate` passes future exogenous rows to `predict` (`_functions.py:289`) |
| D: forecasting a short irregular series | FAIL | `NaiveForecaster(strategy="last")` on one synthetic path with a DatetimeIndex lacking a frequency: `TypeError: unsupported operand type(s) for *: 'int' and 'NoneType'` raised inside fit or predict (caught by the script without the traceback); the forecaster could not handle an index without a frequency |
| C: panel metadata | PASS | `check_is_mtype(..., "pd-multiindex")`: valid, 289 instances, `is_equal_length` false, `is_equally_spaced` false, no NaN |
| C: classifiers for unequal-length panels | PARTIAL | registry: 80 classifiers, 7 tagged unequal length, 11 missing values, 6 both; with core dependencies only: DummyClassifier, KNeighborsTimeSeriesClassifier, MultiplexClassifier, SklearnClassifierPipeline, TSCGridSearchCV, TimeSeriesSVC. `KNeighborsTimeSeriesClassifier(n_neighbors=15)` refused the unequal-length panel despite its class tag; `SummaryClassifier` refused (tag false, consistent) |
| S2 probability shape | PASS | `SklearnClassifierPipeline(LogisticRegression, [SummaryTransformer()])`: `predict_proba` shape (87, 2), finite, in [0.475, 0.631]; Brier 0.2486 versus 0.2546 for train prevalence 0.530 (BSS +0.024), AUC 0.663 (synthetic, 87 test instances). `DummyClassifier(prior)` reproduces the baseline exactly |
| S3 missing values | PASS for the summary pipeline, clear refusal elsewhere | one NaN in the panel: the summary pipeline fits and returns finite probabilities (its instance tags say no missing-value capability); `SummaryClassifier` raises a ValueError naming missing values and unequal length |
| S4 calibration/uncertainty | SKIPPED | no classifier calibration in core; forecasting intervals not applicable because forecasting failed on irregular series (D) |
| S5 persistence | PASS | `est.save()` then `sktime.base.load(...)`: identical `predict_proba` on 87 instances; pickle-based |
| S6 cost | PASS | import 3.6 s; registry scan 1.2 s; summary pipeline fit 0.73 s on 202 instances, predict 3.7 ms per instance; peak RSS 206 MB; offline. Pure-Python wheel for 1.2.0, Python 3.10 to 3.14 declared; core install works with pandas 3.0.5 |

## 5. README or docs claims the code does not support (P42)

- "A unified interface for machine learning with time series": the forecasting interface does not accept the lab's irregular decision series (D), and time-based splitter windows fail on an irregular index (A2). UNSUPPORTED for this data shape.
- Registry tags as documentation: `KNeighborsTimeSeriesClassifier` is listed by `all_estimators(filter_tags={"capability:unequal_length": True})` but its default configuration refuses unequal-length data; conversely the summary pipeline reports no unequal-length or missing-value capability yet handles both. Tag-based discovery is unreliable for this use.
- README "interfaces to related libraries": true at the code level; the GPL3 (mrseql) and source-available (TiRex) interfaces carry obligations of their own when those packages are installed.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 7 | Many ordered splitters on real timestamps, timestamp cutoffs and instance (group) splits (A1, A4, A5); no purge or embargo by label maturity (84 to 116 unmatured training labels per fold), timedelta windows fail on irregular data (A2), forecasting evaluation passes future exogenous values to predict, trap passes (S1) |
| Transferable measurable predictive outcomes (14) | 4 | Panel classification of short unequal windows works through a summary pipeline (BSS +0.024 on synthetic); forecasting needs regular series (D); no survival or event-time models in core |
| Calibration, uncertainty and abstention (12) | 1 | `ConformalIntervals` exists for forecasting (code only, `conformal.py:23`), not usable on this data; nothing for classifiers |
| Catalyst/social/on-chain features (10) | 3 | Panel containers with unequal length and irregular spacing are validated (C metadata); series transformers such as `SummaryTransformer`; no event covariates |
| Decision/execution and stress compatibility (10) | 0 | nothing relevant |
| Code quality, maintenance and tests (8) | 6 | 432 test files; 1,417 splitter tests passed (2 failures from R3's missing data files); very active (pin 2026-10-23); capability tags inconsistent with behaviour (C) |
| Integration fit and extensibility (8) | 5 | Small core dependency set, works with pandas 3.0.5 and scikit-learn; large API surface and mtype conversions; forecasting assumes regular frequency |
| Experiment reproducibility and audit (8) | 5 | `save`/`load` round trip identical (S5); seeded estimators; splitters are deterministic and inspectable; no run lineage |
| Cost, latency and operational reliability (5) | 4 | 3.6 s import, 206 MB, sub-second fits on this panel, offline (S6) |
| Licensing, security and data rights (7) | 6 | BSD-3 verified at pin; GPL3 and source-available third-party packages and Hugging Face weights only behind optional wrappers with UNKNOWN weight terms (section 2) |
| Total | 41 | |

## 7. Flags

- RESEARCH_ONLY for its learners on this data (forecasting does not run on irregular decision series; panel classifiers tested only on synthetic data).
- Not LEAKAGE_FAIL as a splitter library, but containment is required: the lab's walk-forward must purge training rows whose labels mature after the fold's test start (sktime does not), use time-based embargo rather than row offsets, and never pass test-period exogenous features to `predict` (P20, P36).
- Scenarios touched: P20 (no purge), P14 (instance splitter gives mint-disjoint folds), P36, P31 (GPL and source-available wrappers are opt-in), P42.

## 8. Proposed role and integration decision

- Role: reference designs for walk-forward splitters (expanding windows on timestamps, cutoff splitters, instance splits) and a source of panel-validation metadata; not a forecasting engine for this lab's irregular, short paths.
- Candidate INTEGRATION_DECISION: INSPIRED_IMPLEMENTATION: the lab's `split` for N04 should copy the expanding-cutoff idea and add what sktime lacks (label-maturity purge, time embargo, mint grouping), in a few lines of numpy over decision and maturity timestamps, rather than adding sktime and its mtype layer.
- Phase 01 gap cells: SOCIAL_REPLAY:MODEL_TRAINING (N04 walk-forward); HIST_MARKET:POINT_IN_TIME_FEATURES and REGIME_NARRATIVE:POINT_IN_TIME_FEATURES (N06) only through transformers, weakly.
