# soda-inria/hazardous (reviewer R3)

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | soda-inria/hazardous, https://github.com/soda-inria/hazardous |
| Pinned SHA | `1504934e6d886820ca5fcd9e8ccaefd49cc2dd78` |
| Commit date | 2026-07-15T15:13:07+02:00 |
| How fetched | `git fetch --depth 1` of the SHA, `/home/claude/pi_research/src/soda-inria__hazardous` (2.4 MB) |
| Review time (UTC) | 2026-10-24T04:53Z to 05:20Z |
| Version tested | the pin, installed from a copy of the pinned tree with `uv pip install --no-deps .` (flit_core backend; `hazardous/VERSION.txt` = 0.2.0). Python 3.13.17, scikit-learn 1.9.1, numpy 2.5.4, pandas 2.3.3, lifelines 0.30.3 (PyPI wheel, a declared dependency), tqdm 4.70.1. Venv `/home/claude/pi_research/venvs/soda-inria__hazardous` (installed package 300 KB, no data files) |
| Relation to releases | tags list only `0.1.0`; PyPI 0.2.0 was uploaded 2026-07-15T16:33Z, 80 minutes after the pin commit. Its Python sources equal the pin's, but both the 0.2.0 wheel (11.1 MB, sha256 `0c25c1b2...`) and sdist (10.1 MB) also contain files that are not in the pinned tree: `hazardous/data/seer_cancer_cardio_raw_data.txt` (213,846,118 bytes, 477,032 lines, sha256 `f53b7e42...`), `hazardous/data/41586_2019_1007_MOESM7_ESM.txt` (386,802 bytes, a METABRIC table from a Nature supplementary file, sha256 `ada4a9e3...`), `competing_synthetic.csv`, `.DS_Store` files, `.ipynb_checkpoints/_seer-checkpoint.py` and `hazardous/metrics/_negative_log_likelihood.py`. The releases were built from a working tree that differs from any commit seen here |

## 2. License and security

- Root `LICENSE` at the pin: MIT, "Copyright (c) 2023 Soda team @ Inria", sha256 `cb492c051a3442da45dbac60fe69044acbd3044a5f9984d5645757bc351775cd`. No other header or nested license in the pinned tree.
- Dependencies: numpy, scikit-learn (BSD-3), tqdm (MPL-2.0 and MIT), lifelines (MIT, reviewed separately; it declares `pandas<3.0`), setuptools (MIT; declared only because `lifelines.datasets` imports it, `pyproject.toml` comment).
- Data rights of the released artifacts: UNKNOWN and likely restricted. The SEER registry file ships in the PyPI wheel and sdist with no license or data-use statement, while the project's own loader `hazardous/data/_seer.py:71` `load_seer(input_path)` expects a local copy and its error message points to a download page (`:139-141`), which suggests access is normally gated. The METABRIC file carries no terms either. Installing `hazardous==0.2.0` from PyPI puts both files into site-packages. The pinned source does not contain them.
- Model weights: none.
- Install-time scripts: none (flit).
- Network: grep of `hazardous/` for requests, urllib, socket, http.client, telemetry, download finds nothing; all runs under `unshare -n` succeeded. No telemetry.
- Serialization: pickle only.

## 3. Code paths inspected at the pin

| Concern | Anchor |
|---|---|
| Fit path | `hazardous/_survival_boost.py:171` `SurvivalBoost(BaseEstimator, ClassifierMixin)`, `:350` `fit(X, y, times=None)`; `:379` `check_array(X, ensure_all_finite="allow-nan")`; each of `n_iter` iterations samples time horizons with IPCW weights and adds one tree to a warm-started `HistGradientBoostingClassifier` (`:575` `_build_base_estimator`, no monotonic constraint) |
| Censoring weights | `hazardous/_ipcw.py:11` `KaplanMeierIPCW`, `:166` `AlternatingCensoringEstimator` (default `ipcw_strategy="alternating"`) |
| Prediction | `_survival_boost.py:467` `predict_proba(X, time_horizon)` returns (n, 1 + events): no event, event 1, event 2; `:508` `predict_cumulative_incidence(X, times)` predicts each time independently by passing t as a feature, so the CIF is not forced to be monotone in t |
| Metrics (censor-aware) | `hazardous/metrics/_brier_score.py:500` `integrated_brier_score_incidence`, `:328` `integrated_brier_score_survival`; `metrics/_concordance_index.py:11` `concordance_index_incidence` (requires a DataFrame `y_test`; fails with a dict at `:226`) |
| Calibration | `metrics/_aj_calibration.py:109` `aj_calibration_per_event`, `:214` `aj_calibration`; `metrics/_km_calibration.py:142` `km_calibration`, `:221` `recalibrate_survival_function` (marginal shift of the any-event survival function, not clipped) |
| Time handling and splitters | none; scikit-learn estimator, so external splitters can be used |
| Serialization | pickle (scikit-learn estimator) |
| Tests | 9 test files, 82 `def test` functions. Ran `tests/test_metrics.py`, `test_aj_calibration.py`, `test_km_calibration.py`, `test_cindex.py` offline: 104 passed, exit 0, 18.1 s, peak RSS 297 MB (`SMOKES/soda-inria__hazardous/repo_tests.out.txt`) |
| Maturity markers | constructor comments at `:318-322`: "TODO: run a grid search on a few datasets to find good defaults", "TODO: implement convergence criterion and use max_iter instead of n_iter" |

## 4. Smoke results

Script `SMOKES/soda-inria__hazardous/smoke_hazardous.py` (sha256 `fc8a8079...`), helpers `r3_common.py`, `r3_survival.py` (competing-risk variant, seed 20261025: train 968 censored, 74 target first, 704 invalidation first; holdout 413, 17, 204), runner `run_smoke.py`. Final command `unshare -n <venv>/bin/python -I -B smoke_hazardous.py`, exit 0, wall 595.4 s, peak RSS 181.5 MB, user CPU 468.8 s. Raw: `smoke_hazardous.out.txt`, `smoke_hazardous.result.json` (sha256 `db5ba21a...`). The first run exited 1 after 233 s with `AttributeError: 'dict' object has no attribute 'shape'` from `concordance_index_incidence` (the dict form that `fit` documents is not accepted by the metric); the script now passes DataFrames, and the three seed-reproducibility refits use `n_iter=20` to bound CPU. Fit on train, evaluate on holdout (634 rows incl. 107 censored; binary metrics on the 527 labeled rows, 17 positives). Load average was about 3 on 2 CPUs during the runs (shared host).

| Smoke | Result | Numbers |
|---|---|---|
| S1 leak trap | FAIL (nothing stops it) | with `leak_future_ret`: IBS event 1 0.0061 versus 0.0150 clean; concordance (tau 12 h, 23 h) 0.987, 0.991 versus 0.594, 0.615; binary Brier 0.0016 versus 0.0320, AUC 1.000. No availability or time-split mechanism |
| S2 probability shape | PASS on format, FAIL on skill | `predict_proba` shape (634, 3), rows sum to 1, target-first probability in [0.0005, 0.2771], finite. Brier 0.03196 versus 0.03132 for train prevalence (BSS -0.020); log loss 0.1571 versus 0.1439; AUC 0.640 |
| S3 missing values | PASS (native) | 264 NaN in the train design matrix accepted (`:379`), no imputation needed |
| S4 calibration/uncertainty | FAIL on this run, tools PASS | mean predicted P(target first by 24 h) 0.0179 versus observed 0.0323, outside the Wilson 95% interval [0.0202, 0.0510]. AJ-calibration per event on holdout: 0.00033 (no event), 0.00012 (target), 0.00011 (invalidation). `recalibrate_survival_function` with the val split as calibration set produced survival values in [0.121, 0.999], none outside [0, 1] on this run, though the code does not clip. No conformal or abstention API |
| S5 persistence | PASS | pickle (1,289,974 bytes) reloads with identical predictions; refits with the same `random_state` are identical; a different seed changes P(target first) by up to 0.169 (n_iter 20) |
| S6 cost | FAIL for routine refits, PASS for inference | fit 253.8 s at default `n_iter=100` on 1,746 rows (about 13 s at 10 iterations, 48 s at 30, measured separately); predict 0.052 ms per row for one horizon, 3.14 ms per row for 23 horizons; import 4.6 s; peak RSS 182 MB; offline. Pure-Python wheel; Python 3.13 covered |
| Role: competing risks (target first versus invalidation first, censoring) | PARTIAL | maps exactly onto T1's classes. Holdout IBS event 1 0.01504 versus 0.01464 for the marginal Aalen-Johansen baseline (lifelines, train only); event 2 0.1197 versus 0.1178: the covariate model did not beat the marginal baseline on this synthetic data. CIF of event 1 decreases somewhere in time for 634 of 634 holdout rows (largest drop 0.058) |

## 5. README or docs claims the code does not support (P42)

- README "Installation: pip install hazardous": the installed release contains a 214 MB SEER data file, a METABRIC table and a module that are not in the source tree (section 1). The claim that the package is the published source is UNSUPPORTED for 0.2.0.
- Class docstring: "estimates the cause-specific Cumulative Incidence Function": predictions at each time are independent classifier outputs and were non-monotone in time for every holdout row, so the outputs are not guaranteed to be cumulative incidence functions (UNSUPPORTED as a guarantee).
- `fit` docstring accepts `y` as a dict; the package's own `concordance_index_incidence` rejects it (S5 first run).
- CHANGES.rst for 0.2.0 lists the AJ-calibration metrics and Python 3.13 support; both were observed working.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 5 | Censoring represents unmatured labels and IPCW handles it (S2, 107 censored rows scored correctly in IBS); no availability or time-ordered split mechanism, trap passes through (S1); scikit-learn API accepts external splitters |
| Transferable measurable predictive outcomes (14) | 7 | Covariate competing-risk CIFs match the T1 structure exactly and give any horizon from one fit; on the challenge it did not beat the marginal AJ baseline (IBS 0.01504 versus 0.01464, BSS -0.020) and CIFs were non-monotone in time |
| Calibration, uncertainty and abstention (12) | 6 | Censor-aware proper scores for competing risks (IBS per event), AJ and KM calibration, a marginal recalibration; model failed calibration in the large here (S4); no conformal or abstention |
| Catalyst/social/on-chain features (10) | 2 | Static covariates only; native NaN handling (S3) |
| Decision/execution and stress compatibility (10) | 2 | P(target first) and P(invalidation first) by horizon is the barrier race a consumer needs; no execution or fee hook |
| Code quality, maintenance and tests (8) | 4 | 82 tests, 104 parametrized cases passed offline; small project, two releases; TODO defaults in the constructor; API inconsistency between `fit` and metrics; releases built from an unclean tree (section 1) |
| Integration fit and extensibility (8) | 5 | scikit-learn estimator with `predict_proba(X, time_horizon)` and native NaN; pulls lifelines and its `pandas<3.0` pin against the lab's pandas 3.0.5 |
| Experiment reproducibility and audit (8) | 4 | Fixed `random_state` reproduces exactly and pickle round trip is identical (S5); large seed sensitivity (0.169); no lineage |
| Cost, latency and operational reliability (5) | 2 | Inference 0.05 ms per row; training 254 s for 1,746 rows at defaults on this host, so walk-forward refits and seed sweeps are expensive; offline |
| Licensing, security and data rights (7) | 4 | Code MIT verified at the pin, no network; released artifacts bundle third-party clinical registry data with no stated rights (section 2), so the PyPI route needs a gate |
| Total | 41 | |

## 7. Flags

- REJECT for the PyPI 0.2.0 wheel and sdist as install sources: unverified data rights of the bundled SEER and METABRIC files and contents that differ from the source tree (P31, P32). Not a REJECT of the pinned source code, which is MIT and clean.
- Not RESEARCH_ONLY and not NOT_REALTIME (inference is fast); training cost makes it an offline batch tool.
- Not LEAKAGE_FAIL: as-of use is the caller's job, as with any scikit-learn estimator; nothing enforces it (S1).
- Scenarios touched: P05 and P37 (censoring instead of negatives), P10 and P11 (BSS below zero and under-prediction visible in S2/S4), P22 (seed sensitivity means seed sweeps must be logged), P31/P32 (release artifact contents), P42.

## 8. Proposed role and integration decision

- Role: research comparator for the T1 barrier race (target first versus invalidation first versus censored) in Phase 08, scored with its own censor-aware IBS and AJ-calibration against the marginal Aalen-Johansen baseline. Its metric functions (IBS for competing risks, AJ-calibration) are the most directly useful part.
- Candidate INTEGRATION_DECISION: ISOLATED_RESEARCH, installed only from the pinned source (or a later release verified clean), never from the 0.2.0 artifacts. If the metrics are adopted, INSPIRED_IMPLEMENTATION of the IPCW Brier for competing risks in numpy (MIT allows copying with notice) is the lighter route.
- Phase 01 gap cells: HIST_MARKET:EVENT_LABELS and DECISION_RECORDS:EVENT_LABELS (N05), HIST_MARKET:CALIBRATION_SCORING (censor-aware scores), HIST_MARKET:MODEL_TRAINING as a comparator.
