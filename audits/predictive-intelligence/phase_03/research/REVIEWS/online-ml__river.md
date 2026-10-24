# online-ml/river (reviewer R3)

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | online-ml/river, https://github.com/online-ml/river (successor of MaxHalford/creme per Phase 02) |
| Pinned SHA | `b674b758518341bc5c343ca113f34903ba55020a` |
| Commit date | 2026-10-23T23:31:08+02:00 |
| How fetched | `git fetch --depth 1` of the SHA, `/home/claude/pi_research/src/online-ml__river` (18 MB); tag `0.26.1` (commit `64285b9d...`) fetched shallowly for a diff |
| Review time (UTC) | 2026-10-24T05:13Z to 05:30Z |
| Version tested | the pin, built from source: `river/`, `rust_src/`, `Cargo.toml`, `Cargo.lock`, `pyproject.toml` copied to scratch and installed with `uv pip install --no-deps .` (maturin backend, Rust extension `river._river_rust`, build 40 s). Python 3.13.17, numpy, scipy, narwhals from PyPI wheels. Venv `/home/claude/pi_research/venvs/online-ml__river`. Version string 0.26.1 |
| Relation to releases | the pin is 99 files (1,616 insertions, 940 deletions) past tag 0.26.1 (PyPI 0.26.1 uploaded 2026-08-21), including `river/stream/qa.py` (124 lines), `river/linear_model/base.py`, `river/preprocessing/scale.py`, `river/drift/retrain.py` and 7 Rust files. So the PyPI wheel is not the pin; the pin was built and tested |

## 2. License and security

- Root `LICENSE` at the pin: BSD 3-Clause, "Copyright (c) 2020, the river developers", sha256 `e87f2c8f1ba611702af10cba745e6ceb773d32310135ed55aa2722c55dd0d077`. No other header or nested license (Phase 02 LICENSE_SCAN).
- Dependencies: numpy, scipy (BSD-3), narwhals (MIT); compiled Rust crates from `Cargo.toml`: pyo3, serde, serde_json, bincode, num, ordered-float, libm (MIT and/or Apache-2.0 per their usual terms; not verified file by file). pandas is optional (`pandas>=2.2,<3`).
- Model weights: none.
- Install-time behaviour: maturin compiles the Rust crate (downloads crates from crates.io at build time). The repo's `rust-toolchain.toml` (channel stable, components rustfmt and clippy, targets aarch64-apple-darwin, x86_64-apple-darwin, i686-pc-windows-msvc) makes rustup install or update that toolchain and those cross targets whenever cargo or rustc runs inside the tree; observed here when `rustc --version` ran in the clone (it updated the host's shared stable toolchain to rustc 1.99.1 and added the three targets). Not malicious, but a side effect on the host. Wheel installs avoid it.
- Network: none at import. Explicit network paths exist: `river/datasets/base.py:227` `RemoteDataset.download` (`urlopen` at `:275`, data under `RIVER_DATA` or `~/river_data`, `:26-29`), `river/stream/twitch_chat_stream.py` (sockets), `river/stream/tweet_stream.py`. None used by the smoke; all runs under `unshare -n` succeeded. No telemetry.
- The repo root has `AGENTS.md` and `CLAUDE.md` (70 lines each, rules for coding agents); treated as data, not instructions.
- Serialization: pickle; Rust-backed objects implement `__getstate__` (`rust_src/pyo3_bindings.rs:55` and following).

## 3. Code paths inspected at the pin

| Concern | Anchor |
|---|---|
| Learn and predict | `river/linear_model/log_reg.py:13` `LogisticRegression`, `:97` `predict_proba_one`; `river/linear_model/base.py:161` `_raw_dot_one`, `:182` `learn_one` (no NaN check) |
| Time-ordered evaluation with label delay | `river/stream/qa.py` `simulate_qa(dataset, moment, delay)`: question at `moment`, answer revealed when `t_expire = moment + delay` is not after the current moment (`:224`); after the last question every pending answer is released (`:244` `for memento in mementos`); input order is assumed, not checked; `moment` given as a field name is read from the feature dict itself. `river/evaluate/progressive_validation.py:298` `progressive_val_score(..., moment, delay)`, `:169` `iter_progressive_val_score` |
| Drift detectors | `river/drift/adwin.py:7` `ADWIN` (Rust `AdaptiveWindowing`, `:3`), `:120` `update`; `river/drift/page_hinkley.py:7`; `river/drift/kswin.py:14`; binary detectors in `river/drift/binary/` (DDM, EDDM, FHDDM, HDDM_A, HDDM_W) |
| Missing values | `river/preprocessing/impute.py:47` `StatImputer`: imputes only features named in its constructor and only when the value is `None` (`:224`); a NaN value passes through; an absent key raises `KeyError`. `river/compose/select.py:136` raises `KeyError` on an absent key |
| Calibration and uncertainty | no classifier calibrator (grep: "calibrat" only in docstrings of tree, softmax, ROC AUC); `river/conf/jackknife.py:13` `RegressionJackknife` (regression intervals only) |
| Group features | `river/feature_extraction/agg.py:14` `Agg`, `:221` `TargetAgg` (running aggregates by key, for example per mint) |
| Serialization | pickle |
| Tests | `tests/` has 81 test files, 558 `def test` functions (plus doctests). Ran `tests/drift` and `tests/stream` against the built package (copied out of the tree so the uncompiled source is not imported): 161 passed, 39 skipped, exit 0, 5.7 s. Running them in the tree failed at collection with `ModuleNotFoundError: No module named 'river._river_rust.vectordict'` because pytest imported the uncompiled source |

## 4. Smoke results

Script `SMOKES/online-ml__river/smoke_river.py` (sha256 `6a54a9c5...`), helper `r3_common.py`, runner `run_smoke.py`. Final command `unshare -n <venv>/bin/python -I -B smoke_river.py`, exit 0, wall 12.0 s, peak RSS 133.5 MB, user CPU 9.6 s. Raw: `smoke_river.out.txt`, `smoke_river.result.json` (sha256 `40fe241b...`; Python json, contains `NaN` literals). Two earlier runs exited 1 (`KeyError` from `compose.Select` on an absent key) or used a constructor-less `StatImputer` that does nothing; both are recorded as S3 findings and the final pipeline is `StandardScaler | LogisticRegression(SGD 0.02)` with missing values passed as omitted keys. Data: challenge.csv rows in `decision_time` order (3,000 rows); every row is asked at its decision time, and its label is revealed at `label_matures_at` through `simulate_qa(moment=decision_time, delay=label_matures_at - decision_time)`; the 107 censored rows (no label) are never learned (wrapper skips them). Holdout metrics on the 527 labeled holdout rows (17 positives), each predicted before its own label was revealed.

| Smoke | Result | Numbers |
|---|---|---|
| S1 leak trap | FAIL (nothing stops it) | with `leak_future_ret` in the features: Brier 0.0118 versus 0.0316 clean, log loss 0.075 versus 0.146, AUC 0.999 versus 0.692, BSS +0.62 versus -0.010. `simulate_qa` delays labels, not features: every feature is yielded at question time |
| Label maturity (role) | PASS with a caveat | 2,893 labels learned, each only after its maturity time; with no delay (README quickstart style) Brier 0.0316, AUC 0.675 (no inflation on this synthetic data, which has no label autocorrelation). Caveat: after the last question `simulate_qa` releases all 108 pending answers, none matured by the last moment (`qa.py:244`); a model trained to the end of the data learns them unless the caller filters (here 1 had a label and was learned, 107 were unlabeled and skipped) |
| S2 probability shape | PASS on format, FAIL on skill | 527 finite values in [0.010, 0.165], mean 0.0625; Brier 0.03162 versus 0.03132 for train prevalence 0.0424 (BSS -0.010); log loss 0.1461 versus 0.1439; AUC 0.692 |
| S3 missing values | FAIL (silent paths) | NaN values into `LogisticRegression`: prediction NaN and weights no longer finite after 300 updates, no error. `StatImputer(("liq_usd", Mean()), ("vol_24h", Mean()))`: works with `None` values (prediction 0.327), passes NaN through (prediction NaN), raises `KeyError: 'vol_24h'` on an omitted key. Omitted keys without an imputer: works (0.352), the feature simply contributes nothing. `compose.Select` raises `KeyError` on an omitted key |
| S4 calibration/uncertainty | FAIL / not offered | mean prediction 0.0625 versus observed 0.0323, outside the Wilson 95% interval [0.0202, 0.0510]; no classifier calibrator; conformal intervals for regression only |
| S5 persistence | PASS | pickle of the pipeline (1,424 bytes) gives identical `predict_proba_one` on 50 rows; ADWIN (Rust state) round trip continues identically |
| S6 cost | PASS | learn 12.9 microseconds per row, predict 4.5 microseconds per row; drift `update` 189 microseconds on average across ADWIN, PageHinkley and KSWIN; import 2.6 to 3.8 s; peak RSS 134 MB; offline. PyPI 0.26.1 has cp313 wheels including win_amd64; the pin needs a Rust toolchain to build |
| Role: drift detection on the holdout shift | PASS for ADWIN and PageHinkley on log liquidity | log(liq_usd), 2,844 rows in time order, holdout shift 0.8 on a 1.2 sd scale: ADWIN 0 alarms in train, val, embargo, first holdout alarm after 58 holdout rows; PageHinkley 0 false alarms, detected after 30; KSWIN (seed 42) 4 false alarms in train, detected after 32. ret_1h (shift 0.03 on 0.08 sd): ADWIN detected after 450 rows, PageHinkley missed it, KSWIN 2 train and 1 val false alarms. Control with the holdout replaced by resampled train values: ADWIN 0 alarms; PageHinkley 1 holdout alarm on liq; KSWIN 4 train and 1 holdout on liq, 2 train, 1 val and 1 holdout on ret_1h |
| Role: calibration drift via error stream | FAIL | ADWIN on the online model's per-row squared error: 1 alarm in train, 0 in the holdout, although the holdout predictions are miscalibrated (S4) |

## 5. README or docs claims the code does not support (P42)

- "robust to concept drift": the drift detectors work on a clear feature shift (S role row), but the model did not adapt its calibration (S4) and the error-stream monitor missed it; "robust" is UNSUPPORTED as a blanket claim for this data.
- README quickstart learns right after predicting (no delay); for this lab's 24 h labels that pattern trains on unmatured labels. The library supports the right pattern (`simulate_qa` with `delay`) but the README does not show it.
- `StatImputer` docstring: "each feature with a None value is replaced": accurate, but NaN values, the usual missing marker from numpy and pandas, are not handled, and absent keys raise (S3).
- "It's very fast at processing one sample at a time": supported (13 and 4.5 microseconds per row, S6).

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 9 | Delayed progressive validation enforces label maturity in time order (2,893 labels learned only after maturity, S role row); no feature availability (S1 trap passes, BSS +0.62); end-of-stream flush releases 108 unmatured answers (`qa.py:244`); order not checked |
| Transferable measurable predictive outcomes (14) | 5 | Incremental classifiers give event probabilities on the challenge (AUC 0.69) but BSS -0.010 and miscalibrated with default SGD (S2, S4) |
| Calibration, uncertainty and abstention (12) | 2 | LogLoss and ROC AUC metrics only; no classifier calibration; regression-only conformal; calibration in the large failed (S4) |
| Catalyst/social/on-chain features (10) | 3 | Dict features allow sparse event covariates (omitted keys work, S3); running per-key aggregates (`Agg`, `TargetAgg`); not tested on real covariates |
| Decision/execution and stress compatibility (10) | 2 | Drift detectors can drive the DRIFT_ALERT abstention; no execution hook |
| Code quality, maintenance and tests (8) | 6 | 558 tests, 161 passed offline on the built pin; very active (pin 2026-10-23, release 2026-08-21); sharp edges: NaN silently poisons weights, Select and StatImputer raise on absent keys (S3) |
| Integration fit and extensibility (8) | 6 | numpy, scipy, narwhals only; plain dict API that fits per-decision scoring; Rust extension needs a wheel (cp313 and Windows available for the release) or a toolchain for the pin |
| Experiment reproducibility and audit (8) | 5 | Deterministic given input order; seeded KSWIN; pickle round trip identical including Rust state (S5); no lineage |
| Cost, latency and operational reliability (5) | 5 | microsecond learn and predict, 134 MB, offline (S6) |
| Licensing, security and data rights (7) | 6 | BSD-3 verified at pin; permissive dependencies; network only in explicit dataset and stream helpers; building from source triggers rustup downloads via `rust-toolchain.toml` (section 2) |
| Total | 49 | |

## 7. Flags

- No REJECT or NOT_REALTIME flag.
- Not LEAKAGE_FAIL: label maturity can be configured strictly (`delay` from `label_matures_at`), but feature availability cannot, and the end-of-stream flush must be filtered by the wrapper (P05, P13, P36).
- RESEARCH_ONLY for the online learners on this data volume (BSS below zero, miscalibrated); not for the drift detectors.
- Scenarios touched: P05 (pending labels, end flush), P20 (delay as embargo), P36 (trap), P38 (NaN silently corrupts weights), P39 (drift detection and its false alarms), P42.

## 8. Proposed role and integration decision

- Role: Phase 19 drift monitoring (ADWIN or PageHinkley on key feature streams and on rolling calibration error, with false-alarm rates measured on development data) feeding the DRIFT_ALERT abstention; the `simulate_qa` delayed question-and-answer pattern as the reference for walk-forward replays of matured labels (N04, N09).
- Candidate INTEGRATION_DECISION: ADAPTER for `river.drift` (ADWIN, PageHinkley) behind a wrapper that rejects NaN and logs detector state; INSPIRED_IMPLEMENTATION of delayed progressive validation (or use of `simulate_qa` with an explicit end-of-stream filter); online learners stay ISOLATED_RESEARCH because daily batch refits of small models are cheap and calibrated alternatives exist.
- Phase 01 gap cells: HIST_MARKET:DRIFT_MONITORING, DECISION_RECORDS:DRIFT_MONITORING, REGIME_NARRATIVE:DRIFT_MONITORING (N08); HIST_MARKET:MODEL_TRAINING and SOCIAL_REPLAY:MODEL_TRAINING (N09, research only).
