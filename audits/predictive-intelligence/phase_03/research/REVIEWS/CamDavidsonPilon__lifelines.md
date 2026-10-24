# CamDavidsonPilon/lifelines (reviewer R3)

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | CamDavidsonPilon/lifelines, https://github.com/CamDavidsonPilon/lifelines |
| Pinned SHA | `7a8fc34a013ecd79fa405017b89e1697c1cc6e17` ("Merge pull request #1675 from matheusft/perf-optimize-to-long-format") |
| Commit date | 2026-03-06T20:40:07-05:00 (no later commit at the Phase 02 pin time) |
| How fetched | `git fetch --depth 1` of the SHA, `/home/claude/pi_research/src/CamDavidsonPilon__lifelines` (24 MB) |
| Review time (UTC) | 2026-10-24T04:50Z to 05:00Z |
| Version tested | the pin, installed from a copy of the pinned tree with `uv pip install --no-deps .` (`setup.py` only execs `lifelines/version.py` and reads `reqs/base-requirements.txt`; inspected), version string 0.30.3. Python 3.13.17, pandas 2.3.3, numpy 2.5.4, scipy 1.18.1, autograd 1.9.1, formulaic 1.2.2, matplotlib 3.11.2. Venv `/home/claude/pi_research/venvs/CamDavidsonPilon__lifelines`. A second run used pandas 3.0.5 (the lab's runtime version) with the same pinned build |
| Relation to releases | no tag points at the pin; PyPI 0.30.3 (uploaded 2026-03-05). The 0.30.3 wheel differs from the pin only in `lifelines/utils/__init__.py` `to_long_format` (the merged PR) and ships `datasets/ACTG175.csv`, which the pin tree does not have |

## 2. License and security

- Root `LICENSE` at the pin: MIT, "Copyright (c) 2017 Cameron Davidson-Pilon", sha256 `01ab03783d77f529d375f5db2a037804cc8c801951cbd605b3ad2d36b078c1fd`. No other header or nested license (Phase 02 LICENSE_SCAN).
- Dependencies (from installed metadata): autograd MIT, autograd-gamma MIT, formulaic MIT (pulls interface_meta MIT, narwhals MIT, wrapt), matplotlib (PSF-style matplotlib license), pandas, numpy, scipy BSD. All permissive.
- Bundled data: `lifelines/datasets/*` public example datasets (not reviewed one by one; not needed by the lab).
- Model weights: none. Install scripts: none beyond the plain `setup.py`.
- Network: grep of `lifelines/` for requests, urllib, socket, http.client, telemetry finds nothing. Smokes and tests ran under `unshare -n`. No telemetry.
- Serialization is pickle only (unsafe to load untrusted files).

## 3. Code paths inspected at the pin

| Concern | Anchor |
|---|---|
| Fit path | `lifelines/fitters/coxph_fitter.py:32` `CoxPHFitter`, `:167` `fit`; semi-parametric core `:1001` `SemiParametricPHFitter`, `:1092` `fit`, penalized Newton steps around `:1472-1551` |
| Prediction | `coxph_fitter.py:2233` `predict_partial_hazard`, `:2395` `predict_survival_function`; parametric base `lifelines/fitters/__init__.py:2312` |
| Competing risks | `lifelines/fitters/aalen_johansen_fitter.py:69` `AalenJohansenFitter.fit(durations, event_observed, event_of_interest)`, marginal only; `:171-190` `_jitter` calls `np.random.seed(seed)` on the global RNG; no Fine-Gray or cause-specific CIF regression anywhere (grep for fine gray, subdistribution, cause specific: none) |
| Time handling and splitters | `lifelines/utils/__init__.py:631` `datetimes_to_durations`; `:708` `k_fold_cross_validation`, which at `:765` does `df.reindex(np.random.permutation(df.index)).sort_values(event_col)`: random folds stratified by event, no time order, no gap; left truncation via `entry=` |
| Input checks | `lifelines/utils/__init__.py:1171` `check_nans_or_infs` raises on NaN |
| Calibration and uncertainty | `lifelines/calibration.py:12` `survival_probability_calibration(model, df, t0)` returns ICI and E50 from a spline fit; confidence intervals on coefficients and on univariate curves; no recalibration, no conformal |
| Metrics | `lifelines/utils/concordance.py:36` `concordance_index`; no Brier or integrated Brier score in the package |
| Serialization | pickle (docs `Changelog.rst` mentions pickle and joblib support) |
| Tests | 8 test files, 619 `def test` functions. Ran `tests/utils/test_concordance.py` and `tests/test_estimation.py -k "AalenJohansen or concordance or Concordance"` offline: 16 passed, 2 xfailed, 389 deselected, exit 0, 13.1 s. Collection first failed with `NameError: name 'flaky' is not defined`: `flaky` is used by the tests but not listed in `reqs/dev-requirements.txt`; installed it to run them |

## 4. Smoke results

Script `SMOKES/CamDavidsonPilon__lifelines/smoke_lifelines.py` (sha256 `bb16f650...`), helpers `r3_common.py` and `r3_survival.py` (sha256 `ed38e033...`, competing-risk variant, seed 20261025), runner `run_smoke.py`. Command `unshare -n <venv>/bin/python -I -B smoke_lifelines.py`, exit 0, wall 9.8 s, peak RSS 194.3 MB, user CPU 6.0 s. Raw: `smoke_lifelines.out.txt`, `smoke_lifelines.result.json` (sha256 `bb8dfb97...`). Same script with pandas 3.0.5: exit 0, wall 9.0 s, `smoke_lifelines_pandas3.*`; every metric identical, only the pickle size differs. Data: challenge.csv (sha256 checked), duration `time_to_event_h`, event `event_observed`; fit on train (1,746 rows, 74 events), scored on holdout (634 rows of which 107 censored; binary metrics on the 527 labeled rows, 17 positives, censored rows never scored as negatives). Probability of the target by 24 h = 1 - S(23.99 h). Train-median imputation is R3 wrapper code. Integrated Brier is R3's numpy IPCW implementation (`r3_common.ipcw_brier_at`, censoring Kaplan-Meier from the holdout itself), because lifelines has none.

| Smoke | Result | Numbers |
|---|---|---|
| S1 leak trap | FAIL (nothing stops it) | CoxPH with `leak_future_ret`: holdout concordance 0.991 versus 0.696 clean; IPCW IBS (1 to 23 h) 0.0078 versus 0.0157; binary Brier 0.0044 versus 0.0308, AUC 1.000. No availability-time mechanism; the only CV helper shuffles rows (`utils/__init__.py:765`) |
| S2 probability shape | PASS | 527 finite values in [0.0028, 0.2510], mean 0.0386; Brier 0.03083 versus 0.03132 for train prevalence 0.0424 (BSS +0.016); log loss 0.1369 versus 0.1439; AUC 0.696. 17 positives, so these are format checks, not skill |
| S3 missing values | FAIL (no native handling) | `CoxPHFitter.fit` with NaN raises `TypeError: NaNs were detected in the dataset`; imputation required (clear error, not silent) |
| S4 calibration/uncertainty | PASS (diagnostic only) | `survival_probability_calibration` at 23.99 h: ICI 0.0087, E50 0.0061, 0.34 s. Calibration in the large: mean prediction 0.0386 inside the Wilson 95% interval [0.0202, 0.0510] of the observed 0.0323. No recalibration, conformal or abstention API |
| S5 persistence | PASS | pickle of the fitted CoxPH (137,314 bytes) reloads with identical survival predictions; no native safe format |
| S6 cost | PASS | import 4.0 s (matplotlib, autograd, formulaic); CoxPH fit 0.038 s on 1,746 rows; predict 0.004 ms per row; WeibullAFT fit 0.33 s; peak RSS 194 MB; offline. Pure-Python wheel (py3-none-any), so Windows and 3.13 are covered by the dependencies' wheels. Declares `pandas>=2.1,<3.0`; the lab runtime has pandas 3.0.5, and the pinned code passed the same smoke on pandas 3.0.5 |
| Role: time-to-barrier with censoring | PASS (behaviour) | CoxPH holdout concordance 0.696 including the 107 censored rows; IPCW IBS 0.01569 versus 0.01577 for a train Kaplan-Meier baseline; WeibullAFT concordance 0.696, BSS +0.015 |
| Role: competing risks (target first versus invalidation first) | PARTIAL | Aalen-Johansen on the R3 variant (train events: 968 censored, 74 target first, 704 invalidation first): CIF of target first at 24 h 0.04238 (equals the train prevalence 0.04238, as it must with no censoring before 24 h in train), invalidation first 0.403; as a constant forecast its holdout Brier is 0.03132 (the B0 baseline). No covariate-conditional competing-risk model exists at the pin |

## 5. README or docs claims the code does not support (P42)

- `docs/Changelog.rst` still heads with "0.28.0 - Upcoming" while the code is 0.30.3: the changelog is outdated, so release notes cannot be relied on for behaviour changes.
- The README presents lifelines as "a pure Python implementation of the best parts of survival analysis"; for this lab's T1 question (target first versus invalidation first) only the marginal Aalen-Johansen estimator exists, so covariate competing-risk prediction is UNSUPPORTED.
- `reqs/base-requirements.txt` says `pandas<3.0`; the code ran unchanged on pandas 3.0.5 in this smoke, so the pin is a packaging constraint rather than a demonstrated incompatibility (tested on one path only).

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 5 | Right censoring and left truncation (`entry=`) represent not-yet-matured labels without calling them negative (S2 scoring of 634 rows with 107 censored); no availability or time-ordered split mechanism, CV shuffles rows (`:765`), trap column passes straight through (S1) |
| Transferable measurable predictive outcomes (14) | 8 | Time-to-barrier models with censoring produce P(target by any horizon) from one fit (6 h and 24 h from the same model); holdout concordance 0.696, BSS +0.016 on synthetic data; competing risks only marginal (AJ) |
| Calibration, uncertainty and abstention (12) | 5 | ICI/E50 calibration diagnostic and coefficient/curve intervals; calibration in the large inside Wilson (S4); no recalibration, conformal or abstention |
| Catalyst/social/on-chain features (10) | 2 | Static covariates; time-varying covariates exist in `CoxTimeVaryingFitter` (code present, not smoke-tested here) |
| Decision/execution and stress compatibility (10) | 2 | Event-time curves let a consumer choose a horizon; no execution, fee or size hook |
| Code quality, maintenance and tests (8) | 5 | 619 tests, subset passed offline; mature API; last commit 2026-03-06 (7.5 months before review); stale changelog; undeclared test dependency `flaky`; AJ reseeds the global RNG |
| Integration fit and extensibility (8) | 4 | Pure Python with a pandas DataFrame API; `pandas<3.0` declared against the lab's pandas 3.0.5 (works with `--no-deps`, S6); matplotlib imported at package import; no scikit-learn adaptor (removed per Changelog) |
| Experiment reproducibility and audit (8) | 4 | Deterministic Cox fit, pickle round trip identical (S5); no lineage or saved feature transforms; AJ jitter touches global RNG |
| Cost, latency and operational reliability (5) | 5 | 38 ms fit, 0.004 ms per row predict, 194 MB, offline, pure-Python wheel (S6) |
| Licensing, security and data rights (7) | 7 | MIT verified at pin; dependencies MIT/BSD/PSF-style; no network or telemetry (section 2) |
| Total | 47 | |

## 7. Flags

- No REJECT, NOT_REALTIME or RESEARCH_ONLY flag: it produces testable event-time probabilities quickly and offline.
- Not LEAKAGE_FAIL: strict as-of use is possible because the caller builds the design matrix; but nothing in the library enforces it (S1), so the lab's as-of feature view and walk-forward splitter must wrap every fit (P13, P36, P20).
- Scenarios touched: P05 (pending labels as censored rather than negative, natively supported), P20 (no purge or embargo in its CV), P23 (both IBS and binary Brier reported), P37 (vendor gaps can be censoring), P42 (stale changelog).

## 8. Proposed role and integration decision

- Role: time-to-barrier baseline for T1/T1b/T2 that uses censored and not-yet-matured decisions correctly (Kaplan-Meier and Aalen-Johansen as the censoring-aware B0, CoxPH/WeibullAFT as a B2-like covariate model), plus `concordance_index` as a secondary metric.
- Candidate INTEGRATION_DECISION: ADAPTER (thin wrapper in `memelab/predictive/` that takes the as-of design matrix, imputes with training statistics, and stores the fitted model with sha256 and training cutoff); install with `--no-deps` or a pandas override until lifelines lifts `pandas<3.0`.
- Phase 01 gap cells: HIST_MARKET:EVENT_LABELS and DECISION_RECORDS:EVENT_LABELS (N05, censoring and competing-risk description), HIST_MARKET:MODEL_TRAINING (survival baselines), partly HIST_MARKET:CALIBRATION_SCORING (calibration diagnostic only).
