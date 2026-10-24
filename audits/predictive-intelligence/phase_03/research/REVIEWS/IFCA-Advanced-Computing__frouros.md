# IFCA-Advanced-Computing/frouros

Reviewer: R4 (Phase 03 parallel source review). Proposed scores only; the Phase 03 lead applies the rubric across all reviews.

## 1. Identity

| Field | Value |
|---|---|
| Canonical repo | IFCA-Advanced-Computing/frouros |
| URL | https://github.com/IFCA-Advanced-Computing/frouros |
| Pinned SHA | 9fc1f1cd2174f0aaa7eefb7133f2a17b7ba7b970 |
| Commit date | 2026-02-11T11:53:49+01:00 ("Update pytest requirement from <8.4,>=8.3.1 to >=8.3.1,<8.5") |
| How fetched | `git init; git fetch --depth 1 origin <sha>; git checkout FETCH_HEAD` into /home/claude/pi_research/src/IFCA-Advanced-Computing__frouros (8.6 MB) |
| Review time (UTC) | 2026-10-24T04:53Z to 05:00Z |
| Version tested | Built from the pinned tree (`uv pip install ./src/IFCA-Advanced-Computing__frouros`, setuptools; `setup.py` read first: it only loads pyproject.toml and README.md). pyproject says 0.10.0 but `frouros/__init__.py:3` says `__version__ = "0.9.0"`. PyPI's latest is 0.9.0 (2024-10-05, requires-python <3.13), so the pin is unreleased code. |
| Python | 3.13.17 venv at /home/claude/pi_research/venvs/IFCA-Advanced-Computing__frouros |
| Dependency set tested | `SMOKES/IFCA-Advanced-Computing__frouros/freeze_tested.txt` (25 packages including scikit-learn 1.6.1 and pandas 3.1.0 added for the harness). frouros alone resolves 20 packages (`base_dependency_dryrun.txt`): numpy 2.2.6, scipy 1.15.3, matplotlib 3.9.4, requests, tqdm |

## 2. License and security

- Root license: BSD-3-Clause, "Copyright (c) 2022, Spanish National Research Council (CSIC)". `LICENSE` read at the pin, sha256 1e54672abe1afa46fb35a7d49bee018fc1e5ce7490c557c75e3282b22bd6e091 (matches Phase 02). No per-file licenses found by Phase 02.
- Transitive: numpy, scipy BSD-3; matplotlib PSF-based (matplotlib license); requests Apache-2.0; tqdm MPL-2.0 and MIT. No copyleft in the base set.
- Model weights: none.
- Install-time scripts: `setup.py` (setuptools backend) only reads `pyproject.toml` with `toml` and calls `setup()`; nothing else runs.
- Network: no telemetry code (grep for telemetry, socket, analytics finds none). The only network code is the optional datasets module (`frouros/datasets/base.py:100-138`, `requests.head` and `requests.get` on explicit `download()`). Measured: the full smoke under `unshare -n` with strace made 0 inet connects (`smoke_frouros.meta.json`).
- Secrets: none in source.
- Persistence is pickle (`frouros/utils/persistence.py:11-60`): load only files you wrote.

## 3. Code paths inspected at the pin

| Area | Anchor |
|---|---|
| Fit path (batch data drift) | `frouros/detectors/data_drift/batch/statistical_test/ks.py:16` `KSTest` (scipy `ks_2samp`, `:60`); `.../batch/statistical_test/base.py:11` `StatisticalResult(statistic, p_value)` |
| Distance detectors and binning | `frouros/detectors/data_drift/batch/distance_based/psi.py:16` `PSI` (default 10 bins), `:76-92` zero bins replaced by `sys.float_info.min`; equal-width bins over the combined min and max, `.../distance_based/base.py:198-206` |
| Permutation p-values | `frouros/callbacks/batch/permutation_test.py:16` `PermutationTestDistanceBased(num_permutations, random_state, num_jobs)`; multiprocessing pool in `frouros/utils/stats.py:269` |
| Streaming concept drift | `frouros/detectors/concept_drift/streaming/window_based/adwin.py`, `.../statistical_process_control/ddm.py`, `.../change_detection/page_hinkley.py`, also BOCD, CUSUM, EDDM, HDDM, KSWIN, RDDM, STEPD |
| Time handling | none: detectors take arrays; streaming detectors process values in the order given; no timestamps, availability times or splitters |
| Calibration/uncertainty | p-values only; no probability calibration |
| Serialization | `frouros/utils/persistence.py` `save` and `load` (pickle) |
| Tests | 13 test files under `frouros/tests`. Offline: `frouros/tests/unit/detectors frouros/tests/unit/utils frouros/tests/unit/callbacks frouros/tests/integration/test_concept_drift.py` 114 passed, exit 0; `frouros/tests/integration/test_data_drift.py` 25 passed, 7 errors, all `DownloadError` from a fixture that downloads a real dataset (blocked offline by design) (`repo_tests_subset.*`, `repo_tests_integration.*`) |

## 4. Smoke results

Offline (`unshare -n` plus strace: 0 inet connects), Python 3.13.17. Main run `smoke_frouros.*`: exit 0, wall 10.7 s (with strace), peak RSS 211 MB. Money columns log1p-transformed and NaN removed by the harness unless stated.

| Smoke | Result | Numbers | Raw output |
|---|---|---|---|
| S1 leak trap | FAIL (no mechanism) | No availability time or splitter. A model with `leak_future_ret` has stream Brier 0.0027 vs 0.0306 without; DDM on its error stream reports 2 drifts and nothing about leakage | RESULT S1_leak |
| S2 probability shape | SKIPPED | frouros takes no probabilities and computes no proper scores (only `metrics/prequential_error.py`) | n/a |
| S3 missing covariates | FAIL (silent) | Raw liq_usd with NaN: KSTest returns statistic NaN and p-value NaN, EMD distance NaN, and PSI returns 0.0 (reads as no drift) with no error or warning | RESULT S3_nan |
| S4 calibration/uncertainty | FAIL (no calibration; p-values only) | Test p-values and permutation p-values with a `random_state`; no calibration. EMD permutation p (300 permutations): liq_usd holdout 0.0033, val 0.435; ret_1h holdout 0.0033, val 0.033 (a false alarm at 0.05) | RESULT ROLE_distance |
| S5 persistence | PASS (pickle) | `persistence.save` and `load`, 13,705 bytes, identical KS statistic and p-value after reload | RESULT S5_persist |
| S6 cost | PASS | KS on 5 columns 0.052 s; ADWIN update 58 microseconds; MMD with 100 permutations on 600 vs 300 rows 0.87 s; 211 MB RSS; no network; ran on Python 3.13 although PyPI 0.9.0 declares <3.13. Pins `numpy<2.3`, `scipy<1.16`, `matplotlib<3.10`, which conflict with memelab's runtime (numpy 2.5.3, scipy 1.18.1). Windows not tested (pure-Python) | RESULT S6_cost |
| Role: holdout drift detection | PASS (K-S, CvM, EMD, MMD), FAIL (PSI) | K-S at 0.05: holdout flags exactly liq_usd and ret_1h (p 0.0 and 0.0); 4 of 4 holdout chunks of 150 detect both. CvM: same two flagged. MMD (5 standardized columns) holdout p 0.0099. PSI is unusable: on log liq_usd the no-shift val comparison gives 0.027 and holdout 15.85, but on raw liq_usd val gives 4.68 and holdout 3.53, because empty bins are replaced by 2.2e-308 and dominate the sum | RESULT ROLE_batch_*, ROLE_distance, ROLE_mmd_multivariate |
| Role: false alarms train vs val | FAIL at alpha 0.05 without correction | No shift between train and val. K-S flags 1 of 5 columns (ret_1h p 0.040), CvM 2 of 5 (ret_1h 0.033, vol_24h 0.025), MMD p 0.040; train halves 0 of 5 for both. Chunks of 150: K-S 4 false column flags out of 15, CvM 6 of 15. No multiple-testing control is offered | same |
| Role: streaming concept drift on the error stream | PASS (no false alarm) | Fixed model, matured val then holdout rows in time order (556 + 527): DDM on 0/1 errors, ADWIN and Page-Hinkley on per-row Brier: 0 drifts in val and 0 in holdout (the challenge has covariate shift only) | RESULT ROLE_streaming_concept |

## 5. README or docs claims the code does not support (P42)

- README citation abstract (line 500) "compatible with any machine learning framework": true in the narrow sense that detectors take numpy arrays; not scored.
- No README performance or accuracy claim to check. The version shown by the package (0.9.0) does not match pyproject (0.10.0) at the pin.

## 6. Proposed rubric scores

| Criterion | Max | Score | Evidence |
|---|---:|---:|---|
| Temporal integrity and leakage safeguards | 18 | 1 | Streaming detectors consume values in the order given (ordered error stream, 0 false drifts); no timestamps, availability time, cutoff or splitter; S1 trap unprotected |
| Transferable measurable predictive outcomes | 14 | 1 | Monitors model error streams (DDM, ADWIN, Page-Hinkley); produces no event predictions |
| Calibration, uncertainty and abstention | 12 | 1 | p-values and seeded permutation p-values only; no probability calibration or proper scores |
| Catalyst/social/on-chain features | 10 | 0 | None |
| Decision/execution and stress compatibility | 10 | 2 | Drift and warning flags from streaming detectors can trigger degrade or ABSTAIN (P39); nothing on costs or capacity |
| Code quality, maintenance and tests | 8 | 4 | 13 test files, 114 offline tests pass (7 errors only from a download fixture); mypy strict and ruff configured in pyproject; but version string mismatch at the pin, no PyPI release since 2024-10-05, NaN silently gives PSI 0.0, PSI zero-bin replacement gives meaningless values |
| Integration fit and extensibility | 8 | 3 | Small dependency set (20 packages) and a plain fit/compare API on arrays; upper bounds on numpy, scipy and matplotlib conflict with memelab's Python 3.13 runtime |
| Experiment reproducibility and audit | 8 | 3 | Deterministic tests, `random_state` on permutation tests, pickle round trip identical; no run records or lineage |
| Cost, latency and operational reliability | 5 | 5 | Sub-second batch tests, 58 microseconds per streaming update, 211 MB, fully offline (0 connects), runs on 3.13 |
| Licensing, security and data rights | 7 | 6 | BSD-3 verified; no telemetry; network only on explicit dataset download; benign setup.py; pickle persistence |
| Total | 100 | 26 | |

## 7. Flags

- REJECT: no.
- RESEARCH_ONLY: not applicable (monitor).
- NOT_REALTIME: no.
- LEAKAGE_FAIL: not applicable to a monitor; no as-of support, so inputs must be filtered by memelab first.
- Adversarial scenarios: P38-like silent failure (NaN input gives PSI 0.0, which reads as healthy: the wrapper must refuse NaN), P39 (holdout shift detected by K-S, CvM, EMD and MMD; no false drift on the ordered error stream), P22 (per-column tests at 0.05 with no correction produce false alarms on val; memelab needs a multiple-testing rule), P32 (setup.py inspected; no telemetry; 0 connects measured).

## 8. Proposed role and integration decision

- Role: a source of small, readable reference implementations for Phase 19: per-feature two-sample tests with permutation p-values, multivariate MMD, and streaming detectors (ADWIN, Page-Hinkley, DDM) on the per-forecast Brier or log-loss stream once labels mature. Do not use its PSI.
- Candidate INTEGRATION_DECISION: INSPIRED_IMPLEMENTATION. BSD-3 allows copying a detector (for example ADWIN or Page-Hinkley) into `memelab/predictive/` with the copyright notice kept; installing the package into memelab's environment is blocked by its numpy and scipy upper bounds.
- Gap cells addressed: DECISION_RECORDS:DRIFT_MONITORING, HIST_MARKET:DRIFT_MONITORING, REGIME_NARRATIVE:DRIFT_MONITORING (MISSING).
