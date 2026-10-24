# NannyML/nannyml

Reviewer: R4 (Phase 03 parallel source review). Proposed scores only; the Phase 03 lead applies the rubric across all reviews.

## 1. Identity

| Field | Value |
|---|---|
| Canonical repo | NannyML/nannyml |
| URL | https://github.com/NannyML/nannyml |
| Pinned SHA | 4c86ee350dc541cb244f965cf555b4b2a004ae99 |
| Commit date | 2025-07-12T10:08:06+02:00 ("[skip ci] Updated CHANGELOG.md"); no newer commit at the Phase 02 pin observation (2026-10-24T03:12:42Z) |
| How fetched | `git init; git fetch --depth 1 origin <sha>; git checkout FETCH_HEAD` into /home/claude/pi_research/src/NannyML__nannyml (136 MB, of which 67 MB bundled datasets) |
| Review time (UTC) | 2026-10-24T04:44Z to 04:58Z |
| Version tested | 0.13.1 built from the pinned tree (`uv pip install ./src/NannyML__nannyml`, poetry-core backend). pyproject version at the pin is 0.13.1, matching the PyPI 0.13.1 upload of 2025-07-12, but the PyPI wheel was not the code tested. |
| Python | 3.12 venv at /home/claude/pi_research/venvs/NannyML__nannyml (requires-python `>=3.9,<3.13`) |
| Dependency set tested | `SMOKES/NannyML__nannyml/freeze_tested.txt` (102 lines: the 92 packages of the default resolution plus statsmodels and what it pulled in (patsy, formulaic, interface-meta), pytz and tzdata, and pytest tooling; pandas 3.1.0, numpy 2.5.4, scikit-learn 1.9.1, statsmodels added by hand, xgboost 2.1.4, nvidia-nccl-cu12, lightgbm 4.5.0; 1.7 GB site-packages) |

## 2. License and security

- Root license: Apache-2.0. `LICENSE` read at the pin, sha256 4712221f9c77dad5ee69ce85987d2154a689b91f53c13dd98a056036187d2ab0 (matches Phase 02). No nested or per-file license found by Phase 02.
- Key transitive licenses (declared, not audited file by file): pandas, numpy, scipy, scikit-learn BSD-3; lightgbm MIT; FLAML MIT; xgboost Apache-2.0; segment-analytics-python MIT; kaleido MIT (bundles a Chromium binary); category-encoders BSD-3; APScheduler MIT; python-dotenv BSD-3. `FLAML[automl]` pulls xgboost and `nvidia-nccl-cu12` (NVIDIA license, binary) into a CPU-only install.
- Bundled data: `nannyml/datasets/data/*` (67 MB) are synthetic and public-sample datasets; their individual terms were not reviewed (UNKNOWN), not needed for use.
- Model weights: none.
- Install-time scripts: none run. `setup.py` is a bare `setup()`; the build backend is poetry-core.
- Telemetry (FACT, source and measurement):
  - `nannyml/usage_logging.py:138-167`: `SegmentUsageTracker` with a hard-coded Segment write key (`:139`), created at import (`:167`). Every fit, run, plot and writer call is decorated with `log_usage` (for example `nannyml/performance_estimation/confidence_based/cbpe.py:339` on `_estimate`). The user id is `uuid.UUID(int=uuid.getnode())` (`:162`), the machine MAC address written as a UUID. Metadata include run times, exception type, OS, Python version and runtime environment.
  - Off switch: env `NML_DISABLE_USAGE_LOGGING` (any value) checked at each log call (`:122`), or `nannyml.disable_usage_logging()` (`:31`). Default is ON. Disclosed in `docs/usage_logging.rst`, not in README.
  - In Kubernetes (`/var/run/secrets/kubernetes.io/` exists) it probes the cloud metadata endpoint `169.254.169.254` to tell AKS from EKS (`:296-321`). Not triggered here (path absent).
  - Import side effect: `load_dotenv()` at module import (`usage_logging.py:28`). python-dotenv 1.2.4 `find_dotenv` walks up from the installed package directory in script mode and from the working directory in interactive sessions. Measured in script mode: a `.env` in the working directory was not loaded (`telemetry_switch_*.out.txt`). In a notebook it would be, and any `.env` above the venv path is loaded into `os.environ` in script mode.
  - Measured under `unshare -n` plus strace: with the switch absent, UnivariateDriftCalculator fit and calculate plus CBPE made 2 inet connects (to the HTTPS proxy at 127.0.0.1:45127 on the way to `api.segment.io/v1/batch`) and printed `error uploading`; with `NML_DISABLE_USAGE_LOGGING=1`, 0 connects (`telemetry_switch_on.*`, `telemetry_switch_off.*`).
- Secrets: only the vendor Segment write key in source. Persistence uses pickle (see S5): never load a store file from an untrusted source.

## 3. Code paths inspected at the pin

| Area | Anchor |
|---|---|
| Fit path (drift) | `nannyml/drift/univariate/calculator.py:58` `UnivariateDriftCalculator`, `:260` `_fit`, `:320` `_calculate`; default thresholds `:48-54` (`StandardDeviationThreshold`, upper 3 std of the reference chunk values, `nannyml/thresholds.py:154`) |
| Drift methods and NaN | `nannyml/drift/univariate/methods.py:368` K-S, `:589` Wasserstein; `_remove_nans` on reference and analysis (`:412`, `:427`) |
| Performance estimation without labels | `nannyml/performance_estimation/confidence_based/cbpe.py:75` `CBPE.__init__` (calibration default isotonic, `:87`), `:317` `_fit`, `:340` `_estimate`; metrics registered at `confidence_based/metrics.py:337` (roc_auc), `:483` (average_precision), `:1217` (accuracy), `:2121` (business_value with a cost matrix) |
| Calibration | `nannyml/calibration.py:226` `needs_calibration` (ECE compared with and without isotonic calibration in 10 folds); calibrator applied in `_estimate` (`cbpe.py:372-373`) |
| Uncertainty | sampling-error bands, `nannyml/sampling_error/binary_classification.py`; AP uses an unseeded bootstrap on the global numpy RNG (`:124` `np.random.choice`) |
| Time handling | `nannyml/chunk.py:165` sorts by the timestamp column; `PeriodBasedChunker` (`:270`) groups by calendar period; reference and analysis periods kept apart in results. No feature availability time, no cutoff, no purge or embargo |
| Serialization | `nannyml/io/store/file_store.py:16` `FilesystemStore`; `nannyml/io/store/serializers.py:98` and `:101` `pickle.dumps` and `pickle.loads` |
| Tests | 37 `test_*.py` files. Subset offline with pandas 3.1.0 (`tests/test_calibration.py tests/drift/test_univariate_drift_methods.py tests/performance_estimation/CBPE/test_cbpe.py tests/test_chunk.py`): 135 passed, 34 errors, exit 1; all 34 errors are in `tests/test_chunk.py` fixtures (`TypeError: Invalid value ... for dtype 'int64'`, a pandas 3 change). `tests/test_chunk.py` with pandas 2.3.3: 46 passed, exit 0 (`repo_tests_subset.*`, `repo_tests_chunk_pandas2.*`) |

## 4. Smoke results

Offline (`unshare -n`), `NML_DISABLE_USAGE_LOGGING=1`, Python 3.12, pandas 3.1.0, fresh working directory. Main run `smoke_nannyml.*`: exit 0, wall 5.9 s, peak RSS 325 MB. Raw output in `SMOKES/NannyML__nannyml/`.

| Smoke | Result | Numbers | Raw output |
|---|---|---|---|
| Install and import | FAIL as declared, PASS after a manual fix | Fresh install from the pin: `import nannyml` fails, `ModuleNotFoundError: statsmodels` (imported at `nannyml/plots/components/joy_plot.py:12`, not declared in pyproject). With statsmodels added: import exit 0, 11 s, 320 MB | `import_default_resolution.*`, `import_pandas3_statsmodels.*` |
| S1 leak trap | FAIL (no protection) | Baseline model: CBPE estimated holdout ROC AUC 0.739 (realized 0.696). With `leak_future_ret`: CBPE estimate 0.9998, realized 1.000. No availability-time or cutoff mechanism; nothing flagged the trap | RESULT S1_leak |
| S2 probability shape | FAIL for P38 | Inputs are not validated. A probability of 1.5 gives a NaN ROC AUC for its chunk with no error; NaN and -0.2 are accepted silently (chunk AUC 0.736 and 0.764). Reference scores from sklearn on matured holdout: Brier 0.03099 vs train-prevalence baseline 0.03132, log loss 0.1383 vs 0.1439. No Brier or log loss among CBPE metrics | RESULT S2_probs |
| S3 missing covariates | PASS (silent drop) | K-S statistic on liq_usd with NaN 0.285048 equals the value after dropna; NaN removed by `_remove_nans`. CBPE needs no features. Multivariate PCA drift needs an imputer (passed `SimpleImputer`) | RESULT S3_nan |
| S4 calibration and uncertainty | PASS (coverage 4 of 4, bands too wide to inform) | CBPE tests whether isotonic calibration lowers ECE on the reference (decided False here) and gives 3-sampling-error bands. All 4 evaluable holdout chunks had realized ROC AUC, AP and accuracy inside estimate plus or minus 3 SE (4 of 4), but at 150 rows and 3 to 7 positives the ROC AUC SE is 0.117 and AP SE 0.13 to 0.16, so the band spans most plausible values; no alert fired. AP SE changes between runs (0.1359 then 0.1629, unseeded bootstrap) | RESULT ROLE_cbpe |
| S5 persistence | PASS (unsafe format) | `FilesystemStore` pickle, 8,116 bytes; reloaded CBPE gives identical estimates. Pickle executes code on load | RESULT S5_persist |
| S6 cost | PASS with caveats | CBPE fit 0.21 s on 556 reference rows, estimate 0.048 s for 634 rows (0.075 ms per row); univariate drift 6 columns 0.08 to 0.30 s. Install 1.7 GB, 92 packages as declared (plus statsmodels and its dependencies, needed to import). Python 3.13: pip refuses (no matching distribution, requires-python <3.13, `py313_pip_download.txt`); uv ignores the upper bound and would install it (`py313_install_dryrun.txt`); not run on 3.13. Windows not tested (pure-Python wheel; xgboost and lightgbm ship Windows wheels) | RESULT S6_cost |
| Role: CBPE with labels not yet matured (P05) | PASS as a monitor, weak as evidence | Reference = val matured rows (556, 18 positives) with a model fitted on train. Holdout with every label hidden: estimated ROC AUC 0.739, AP 0.110, accuracy 0.911; realized on the 527 matured rows (17 positives) 0.696, 0.085, 0.907. The 107 censored rows, which have no label at all, get an estimate (ROC AUC 0.723, AP 0.092): this is the PENDING use case. Estimates assume calibrated probabilities and no concept shift; the challenge has covariate shift only | RESULT ROLE_cbpe |
| Role: holdout drift detection | PASS | Reference = train (12 chunks of 150), val and holdout chunked separately. K-S: liq_usd alerts in 5 of 5 holdout chunks, ret_1h 5 of 5; extra holdout alerts age_h 1. Jensen-Shannon: liq_usd 5 of 5, ret_1h 4 of 5, extras age_h, score100, vol_24h 1 each. Wasserstein: 5 of 5 and 5 of 5, extra age_h 1. Multivariate PCA reconstruction: 1 of 5 holdout chunks | RESULT ROLE_univariate_*, ROLE_multivariate_reconstruction |
| Role: false alarms train vs val | FAIL (3 of 24 column-chunks) | No shift between train and val. Column-chunk alerts in val: 3 of 24 for each of K-S, Jensen-Shannon and Wasserstein (12.5 percent); 0 alerts in the 12 reference chunks (thresholds are fitted on them); multivariate 0 of 4 | same |
| Telemetry (not a smoke) | n/a, finding | ON by default, Segment, MAC-derived id; off with `NML_DISABLE_USAGE_LOGGING` | `telemetry_switch_*` |

## 5. README or docs claims the code does not support (P42)

- README line 54 "automatically detect silent model failure": on this challenge CBPE raised no alert on any chunk and missed nothing only because nothing large happened; with a leaked feature it reports near-perfect performance (S1). UNSUPPORTED as a general claim.
- README line 45 "completely model-agnostic": true only for models that output probabilities; estimates are only as good as reference calibration (CBPE docs state this). Not credited beyond the measured result.
- `docs/usage_logging.rst` "We won't collect any information about your identity": the user id is the machine MAC address (`usage_logging.py:162`), a hardware identifier. Recorded as a privacy finding, not scored as a capability.

## 6. Proposed rubric scores

| Criterion | Max | Score | Evidence |
|---|---:|---:|---|
| Temporal integrity and leakage safeguards | 18 | 3 | Time-ordered chunking on a timestamp column (`chunk.py:165`), period chunking, reference and analysis periods separated, CBPE monitors periods whose labels are pending (P05); no availability time, cutoff, purge or embargo; S1 trap passes through and CBPE reports 0.9998 |
| Transferable measurable predictive outcomes | 14 | 2 | Estimates and computes binary-classification performance per chunk (ROC AUC, AP, accuracy within 0.04 of realized on the whole holdout); produces no forecasts of its own; no survival |
| Calibration, uncertainty and abstention | 12 | 4 | Isotonic calibration check and calibrator in CBPE (`calibration.py:226`), sampling-error bands with 4 of 4 coverage but very wide at 3.8 percent prevalence; no Brier or log loss; invalid probabilities accepted silently (P38 fail); AP band not reproducible without a seed |
| Catalyst/social/on-chain features | 10 | 1 | Period chunking groups irregular timestamps; nothing for event covariates or cross-token features |
| Decision/execution and stress compatibility | 10 | 3 | Per-chunk alerts on drift and estimated performance can drive degrade or ABSTAIN (P39); `business_value` metric takes a payoff matrix per confusion cell (`metrics.py:2121`) that could carry fee-aware payoffs; nothing on execution capacity |
| Code quality, maintenance and tests | 8 | 3 | 37 test files; 135 subset tests pass but 34 fixture errors under pandas 3; undeclared statsmodels import breaks a clean install; last commit 2025-07-12; requires-python excludes 3.13 |
| Integration fit and extensibility | 8 | 1 | Cannot be installed by pip on memelab's Python 3.13; 1.7 GB footprint (xgboost, NVIDIA NCCL, kaleido Chromium) for a monitoring feature; import-time telemetry setup and `load_dotenv()` |
| Experiment reproducibility and audit | 8 | 4 | Deterministic drift and CBPE point estimates; pickle store reload identical; results carry chunk index, start and end dates; AP sampling error uses an unseeded global RNG |
| Cost, latency and operational reliability | 5 | 3 | CBPE 0.075 ms per row, drift under 0.3 s, 325 MB RSS, works offline with the switch set; heavy install and an 11 s import; tries the network on every fit by default |
| Licensing, security and data rights | 7 | 3 | Apache-2.0 verified; telemetry on by default with a MAC-derived id and a hard-coded key (off with env, measured); `.env` loading at import; pickle persistence; metadata-endpoint probe inside Kubernetes |
| Total | 100 | 27 | |

## 7. Flags

- REJECT: no.
- RESEARCH_ONLY: not applicable as a forecaster; as a monitor its estimates have no independent accuracy evidence on memecoin data.
- NOT_REALTIME: no.
- LEAKAGE_FAIL: not applicable (monitor), but S1 shows CBPE cannot detect a leaked feature; inputs must already be as-of filtered.
- Adversarial scenarios: P05 (CBPE gives an estimate for PENDING rows and never scores them as negatives; useful), P38 (out-of-range and NaN probabilities accepted silently: the wrapper must validate first), P39 (drift alerts on holdout chunks), P24 (wide sampling-error bands at small chunks are the honest answer; must be shown, not hidden), P32 (telemetry and dotenv side effects found by source review and measured), P42 (README "detect silent model failure" not credited).

## 8. Proposed role and integration decision

- Role: the CBPE idea fits Phase 19 "labels not yet matured": estimate the expected ROC AUC or Brier of recent forecasts from their own calibrated probabilities while barrier labels are PENDING, and show the sampling-error band. The math is small (expected confusion counts from calibrated probabilities plus an isotonic check) and can be written in numpy, with a seeded bootstrap, an expected Brier score added, and the P38 input validation NannyML lacks.
- Candidate INTEGRATION_DECISION: INSPIRED_IMPLEMENTATION for CBPE and the reference-chunk threshold rule (alert when a chunk statistic exceeds the reference chunk mean plus 3 std). The library itself only as ISOLATED_RESEARCH in a Python 3.12 venv with `NML_DISABLE_USAGE_LOGGING=1`, never imported by memelab.
- Gap cells addressed: DECISION_RECORDS:DRIFT_MONITORING, HIST_MARKET:DRIFT_MONITORING, REGIME_NARRATIVE:DRIFT_MONITORING (MISSING); partially the PENDING-label monitoring part of the Phase 19 plan.
