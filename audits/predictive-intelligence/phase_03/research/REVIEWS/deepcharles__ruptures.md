# deepcharles/ruptures (reviewer R3)

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | deepcharles/ruptures, https://github.com/deepcharles/ruptures |
| Pinned SHA | `ee1c8ff8a548d54c641b2bb471562165931f31c7` (Phase 02 SHORTLIST.csv) |
| Commit date | 2026-05-26T16:40:03+02:00 |
| How fetched | `git init; git fetch --depth 1 https://github.com/deepcharles/ruptures <sha>; git checkout FETCH_HEAD` into `/home/claude/pi_research/src/deepcharles__ruptures` (8.2 MB) |
| Review time (UTC) | 2026-10-24T04:33Z to 04:45Z |
| Version tested | the pin itself, built from source (`setup.py` only runs `cythonize` on two extensions; inspected first) with `SETUPTOOLS_SCM_PRETEND_VERSION=1.1.11.dev0+gee1c8ff`, `uv pip install --no-deps .`, Python 3.13.17, venv `/home/claude/pi_research/venvs/deepcharles__ruptures` (numpy 2.5.4, scipy 1.18.1, typing-extensions 4.16.0, scikit-learn 1.9.1 for nothing but the shared helper) |
| Relation to releases | no tag points at the pin (`git ls-remote --tags`); latest PyPI release 1.1.10 (uploaded 2025-09-10). The 1.1.10 cp313 manylinux wheel has 43 .py files, none importing `typing_extensions`, and no `l1potts` module, so the pin is unreleased code newer than 1.1.10 |

## 2. License and security

- Root `LICENSE` at the pin: BSD 2-Clause, "Copyright (c) 2017-2021, ENS Paris-Saclay, CNRS", sha256 `f29c48be39fff974e2d631b2317c194409531cc86e16e05f3968ead0456bc920`. `docs/license.md` says "BSD license" (consistent). Phase 02 LICENSE_SCAN found no other header license.
- `src/ruptures/detection/l1potts.py:1-9` states the implementation was prepared with an AI coding agent; no license change attached to it.
- Dependencies: numpy (BSD-3), scipy (BSD-3) declared. Undeclared at the pin: `typing_extensions` (PSF-2.0), imported at `src/ruptures/base.py:8` and every cost module; `setup.cfg:39-41` declares only numpy and scipy. Proven: in a venv with only numpy and scipy, `import ruptures` from the pin build fails with `ModuleNotFoundError: No module named 'typing_extensions'`.
- Model weights: none.
- Install-time scripts: `setup.py` builds two Cython extensions (`ekcpd`, `convert_path_matrix`) from bundled C; no downloads, no post-install hooks. Build used isolated build deps from PyPI (setuptools, Cython, setuptools_scm, numpy, scipy per `pyproject.toml`).
- Network: grep of `src/` for requests, urllib, socket, http.client, telemetry finds nothing. All smokes ran inside `unshare -n` (no network namespace) and succeeded. No telemetry. No secrets handling.

## 3. Code paths inspected at the pin

| Concern | Anchor |
|---|---|
| Fit path (PELT) | `src/ruptures/detection/pelt.py:99` `fit` (stores the whole array in the cost), `:50` `_seg` dynamic program over every admissible index of the passed array, `:117` `predict(pen)` |
| Fast kernel PELT (C) | `src/ruptures/detection/kernelcpd.py:74` `fit`, `:89` `predict`; C in `src/ruptures/detection/_detection/ekcpd_pelt_computation.c` |
| Window detector | `src/ruptures/detection/window.py:116` `fit`; `:142` `start, end = k - self.width // 2, k + self.width // 2`: the score at index k reads half a window of later samples |
| Costs | `src/ruptures/costs/costl2.py:39` `error`, `src/ruptures/costs/costnormal.py:55` `error` |
| Input checks | only `src/ruptures/detection/l1potts.py:92` refuses NaN/Inf; PELT, Binseg, Window and KernelCPD do not check |
| Time handling and splitters | none: every detector takes an index-ordered array with no timestamp argument; no splitter, no availability field |
| Probability, calibration, uncertainty | none (penalty or number of breakpoints is a hard setting) |
| Serialization | none native; estimators are plain Python objects (pickle works, S5) |
| Metrics | `src/ruptures/metrics/precisionrecall.py:8` `precision_recall(true, pred, margin)` used in R1 |
| Tests | 7 test files, 101 `def test` functions (`tests/`). Ran `test_l1potts.py`, `test_costs.py`, `test_metrics.py` offline: 130 passed, 5 warnings, exit 0, 4.4 s, peak RSS 116 MB (`SMOKES/deepcharles__ruptures/repo_tests.out.txt`) |

## 4. Smoke results

Script `SMOKES/deepcharles__ruptures/smoke_ruptures.py` (sha256 `a894257f...`), helper `r3_common.py` (sha256 `f740b55c...`), runner `run_smoke.py`. Command `unshare -n <venv>/bin/python -I smoke_ruptures.py`, exit 0, wall 137.2 s, peak RSS 105.8 MB, user CPU 110.4 s. Raw: `smoke_ruptures.out.txt`, `smoke_ruptures.result.json` (sha256 `597cdd46...`), `smoke_ruptures.meta.json`. Data: 300 seeded synthetic 5-minute paths (`r3_common.seeded_paths`, seed 20261026), 20 to 251 kept candles each after dropping 15% of intervals (no-trade gaps), 199 with 1 or 2 planted drift/volatility changes. The shared challenge.csv has no price paths, so it was not used here.

| Smoke | Result | Numbers |
|---|---|---|
| S1 leak trap (as-of) | FAIL (no mechanism; leak shown; containment possible) | No availability or split mechanism. Decision index d = 60% of each path (245 paths of at least 60 returns): PELT on the full path versus PELT on the path cut at d gives different breakpoints before d on 31 of 245 paths, and the derived feature "candles since last break" differs on the same 31. Window detector: editing only samples after k changed score[k] from 1.25e-05 to 1.005. Refitting on `signal[:d]` at each decision is truncation-invariant by construction; that is wrapper code |
| S2 probability shape | SKIPPED | no probability output |
| S3 missing values | FAIL (silent) | one NaN in a 69-return path: `Pelt(l2)` and `Pelt(normal)` return a breakpoint every 5 samples (15, 20, ... 65, 69) with no error; `KernelCPD(rbf)` returns no breakpoint; only `L1Potts` raises `ValueError: signal must contain only finite values` |
| S4 calibration/uncertainty | SKIPPED | none offered |
| S5 persistence | PASS | pickle of a fitted PELT (1,728 bytes) reloads and predicts identical breakpoints; pickle is unsafe for untrusted files; results are int lists and can be stored as JSON |
| S6 cost | PASS (KernelCPD), slow (PELT) | PELT `normal` per path fit+predict median 0.149 s, p95 0.570 s, max 1.016 s (250 returns); causal use needs a refit per decision: 19 expanding refits on one 250-return path took 2.77 s for PELT (146 ms each) and 0.010 s for KernelCPD rbf (0.54 ms each). Offline import, fit and predict work with no network. PyPI 1.1.10 has cp313 wheels including `win_amd64`; the pin itself has no wheel |
| Role: change points on OHLCV-like paths | PASS (behaviour) | PELT normal, pen 3 log n, on log returns: mean precision 0.632 and recall 0.616 within 3 candles over 199 changed paths; 16 false-alarm paths of 101 without a change. Synthetic only, no claim about real memecoin regimes |
| Role: irregular timestamps | FAIL (by design) | `fit(signal)` has no time argument; a 3-candle gap is one step to the detector (path PMINT0011, 273 dense, 217 kept candles). The wrapper must decide how to encode omitted intervals |

## 5. README or docs claims the code does not support (P42)

- The README describes the library as off-line change point detection, which matches the code; it makes no predictive or online claim.
- UNSUPPORTED at the pin: installing from the pinned source with the declared dependencies gives an importable package. It does not (`typing_extensions` undeclared, section 2).
- UNSUPPORTED for this lab's use: README badge lists Python 3.10 to 3.14; only 3.13 was tested here, and the 1.1.10 release declares `<3.14`.
- The README "Latest news" use cases (NASA, Chelsea FC and others) are not verifiable from the code and earn nothing.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 3 | No as-of, availability or splitter mechanism (section 3); full-series fits leak into 31 of 245 decision features and Window reads future samples (S1). Credit only because a refit on `signal[:d]` is causal and cheap with KernelCPD (S6) |
| Transferable measurable predictive outcomes (14) | 2 | Produces segment boundaries, not outcome predictions; R1 recovers planted changes at precision 0.63, recall 0.62 on synthetic paths only |
| Calibration, uncertainty and abstention (12) | 0 | none offered (S4) |
| Catalyst/social/on-chain features (10) | 2 | Regime/change-point features from price or volume paths; index-only, no irregular timestamps, no event covariates (role row) |
| Decision/execution and stress compatibility (10) | 0 | no hook or output relevant to execution |
| Code quality, maintenance and tests (8) | 4 | 101 tests, 130 parametrized cases passed offline; last release 2025-09-10, pin 2026-05-26; undeclared dependency breaks a clean install at the pin; NaN accepted silently by PELT (S3) |
| Integration fit and extensibility (8) | 6 | numpy and scipy only, small, clean fit/predict API, Python 3.13; needs a wrapper for time and gaps |
| Experiment reproducibility and audit (8) | 4 | deterministic algorithms (identical output on reload, S5); no lineage, no saved transformation format |
| Cost, latency and operational reliability (5) | 4 | KernelCPD 0.54 ms per causal refit, PELT 146 ms; offline; cp313 and Windows wheels for 1.1.10 (S6) |
| Licensing, security and data rights (7) | 7 | BSD-2-Clause verified at pin; numpy/scipy BSD; build script only cythonizes; no network or telemetry (section 2) |
| Total | 32 | |

## 7. Flags

- RESEARCH_ONLY: a feature generator; there is no evidence that change-point features add skill on 17 days of one regime, and it cannot output testable event probabilities.
- Not LEAKAGE_FAIL, but containment is required: only refits on data available at the decision are allowed, with the truncation-invariance check of PLANNED_SEAMS (replay_core truncate/leakage_check pattern); the Window detector is excluded because its score reads future samples (P36).
- Scenarios touched: P36 (future samples in a feature, S1), P38-like silent garbage on NaN (S3), P42 (README use cases earn nothing), P32 (install inspected; undeclared dependency found, no destructive script).

## 8. Proposed role and integration decision

- Role: optional regime-state feature for Phase 08 exploration ("candles since last detected break", "volatility of the current segment"), computed only on candles available at the decision, with KernelCPD (C) for cost.
- Candidate INTEGRATION_DECISION: ISOLATED_RESEARCH; ADAPTER only if a change-point feature survives walk-forward evaluation, and then pinned to a released wheel (1.1.10 or later) with an explicit NaN check in the wrapper.
- Phase 01 gap cells: HIST_MARKET:POINT_IN_TIME_FEATURES (PARTIAL), REGIME_NARRATIVE:POINT_IN_TIME_FEATURES; supports LAUNCH_COHORT:MODEL_TRAINING and REGIME_NARRATIVE:MODEL_TRAINING (N07) only as a segmentation step.
