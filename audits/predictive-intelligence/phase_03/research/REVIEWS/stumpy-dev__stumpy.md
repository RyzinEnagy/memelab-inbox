# stumpy-dev/stumpy (reviewer R3)

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | stumpy-dev/stumpy, https://github.com/stumpy-dev/stumpy (same history as TDAmeritrade/stumpy per Phase 02) |
| Pinned SHA | `248e34409dd09feac1d82422fa64ea887174ce13` |
| Commit date | 2026-10-16T12:53:39-04:00 |
| How fetched | `git fetch --depth 1` of the SHA, `git checkout FETCH_HEAD`, `/home/claude/pi_research/src/stumpy-dev__stumpy` (194 MB, of which docs 108 MB) |
| Review time (UTC) | 2026-10-24T04:42Z to 04:50Z |
| Version tested | the pin: `stumpy/`, `pyproject.toml`, `LICENSE.txt`, `README.rst` copied to a scratch build folder and installed with `uv pip install --no-deps .` (setuptools backend, static version "1.14.1"); `diff -rq` of the pin's `stumpy/` against the installed package is empty. Python 3.13.17, numba 0.68.0, llvmlite 0.50.0, numpy 2.5.4, scipy 1.18.1. Venv `/home/claude/pi_research/venvs/stumpy-dev__stumpy` |
| Relation to releases | no tag points at the pin; PyPI 1.14.1 was uploaded 2026-02-08 and declares `>=3.10`, the pin's `pyproject.toml` still says 1.14.1 but `>=3.11`, so the pin is unreleased code carrying the last release's version string |

## 2. License and security

- Root `LICENSE.txt` at the pin: 3-Clause BSD, "Copyright 2019 TD Ameritrade", plus "STUMPY is a trademark of TD Ameritrade IP Company, Inc." (a name notice, not a use restriction). sha256 `36af10790ccc8faa741b5e483f648d101f4df9795e485e2b01b089039a388a4f` (matches Phase 02). No other header or nested license (Phase 02 LICENSE_SCAN).
- Runtime dependencies: numpy, scipy (BSD-3), numba 0.68.0 (dist-info `License: BSD`, ships `LICENSES.third-party`), llvmlite 0.50.0 (`License-Expression: BSD-2-Clause AND Apache-2.0 WITH LLVM-exception`). All permissive.
- Model weights: none.
- Install-time scripts: none in the wheel build (setuptools, pure Python). The repo root has shell helpers (`setup.sh`, `pip.sh`, `conda.sh`, `numba.sh`, `test.sh`) for CI; not run.
- Network: grep of `stumpy/` for requests, urllib, socket, http finds nothing; only env read is `STUMPY_SEED` (`stumpy/rng.py:8`). All runs under `unshare -n` succeeded. No telemetry.
- Disk writes: `stumpy.cache.save()` writes numba cache files into `site-packages/stumpy/__pycache__` by default (`stumpy/cache.py:125`, `:171`); not called by default.

## 3. Code paths inspected at the pin

| Concern | Anchor |
|---|---|
| Matrix profile (fit-like path) | `stumpy/stump.py:513` `stump(T_A, m, T_B=None, ...)`; left and right indices kept at `:470-475`; output described at `:594-610` (`.P_`, `.I_`, `.left_I_`, `.right_I_`) |
| Causal / streaming | `stumpy/stumpi.py:19` class `stumpi` (wrapped by `@core.non_normalized` at `:12`), `:271` `update`, `:450-456` left profile appended from past-only distances; `stumpy/floss.py:308` `floss` (online regime segmentation), `:234` `fluss` (offline) |
| Distance / analog search | `stumpy/core.py:1604` `mass`; `stumpy/motifs.py:404` `match`; `stumpy/ostinato.py:285` consensus motif across many series |
| Missing values | `stumpy/core.py:2517` `rolling_isfinite`, `:675` `_welford_nanvar`: windows with NaN get infinite distance |
| Output container | `stumpy/mparray.py:4` `mparray(np.ndarray)`, object dtype (S5) |
| Time handling, splitters | none: arrays only, no timestamps, no availability field; cross-series time cutoffs are the caller's job |
| Probability, calibration | none |
| Serialization | none native (S5) |
| Tests | 51 test files, 599 `def test` functions. Ran `tests/test_motifs.py` offline: 22 passed, exit 0, 7.4 s, peak RSS 287 MB (`SMOKES/stumpy-dev__stumpy/repo_tests.out.txt`). `test_mparray.py` needs pandas (ci extra) and was not run |

## 4. Smoke results

Script `SMOKES/stumpy-dev__stumpy/smoke_stumpy.py` (sha256 `b804701f...`), helper `r3_common.py`, runner `run_smoke.py`. Final run: `unshare -n <venv>/bin/python -I -B smoke_stumpy.py`, exit 0, wall 37.4 s, peak RSS 468.4 MB, user CPU 27.1 s. Two earlier runs exited 1 on the two persistence findings below; the script now records them instead of failing. Raw: `smoke_stumpy.out.txt`, `smoke_stumpy.result.json` (sha256 `502a8679...`), `smoke_stumpy.meta.json`. Data: the same 300 seeded paths as the ruptures smoke (seed 20261026) plus a planted 12-step motif (seed 20261027). challenge.csv has no paths and was not used.

| Smoke | Result | Numbers |
|---|---|---|
| S1 leak trap (as-of) | FAIL by default, PASS with stumpi or left indices | Self-join `stump` is not causal: editing only samples after i+m changed P[48] from 3.287 to 2.651 and its neighbour index from 128 to 106; `left_I_[48]` stayed 33. `stumpi(egress=False)` streamed 210 updates over a 250-return path; its `left_P_` equals a past-only `mass` recomputation at 33 checked indices (max abs diff 1.8e-15). No availability-time or split mechanism; the wrapper must pick the causal API and enforce cross-path time cutoffs |
| S2 probability shape | SKIPPED | distances and indices only |
| S3 missing values | PASS (native, but costly on gappy paths) | dense 5-minute grid with NaN for omitted intervals (271 steps, 100 NaN): 243 of 260 windows get infinite profile and mass distance, no error, no imputation. With 15% omitted intervals and m = 12 most windows become unusable, so gaps need an explicit encoding (for example zero return for a no-trade interval) chosen by the wrapper |
| S4 calibration/uncertainty | SKIPPED | none offered |
| S5 persistence | FAIL (partly) | `stump` output is an object-dtype array (144 x 4): `np.save(..., allow_pickle=False)` raises `ValueError: Object arrays cannot be saved`; splitting into float `P_` and int `I_` columns and saving with `np.savez` reloads equal. `pickle.dumps(stumpi)` raises `PicklingError: Can't pickle <class 'stumpy.stumpi.stumpi'>: it's not the same object as stumpy.stumpi.stumpi` (decorator-wrapped class), so streaming state cannot be persisted by pickle |
| S6 cost | PASS warm, poor cold | import 3.0 s; first `stump` call 31.0 s (numba JIT, no default disk cache), second 0.001 s; first `mass` 0.61 s, then 0.0009 s; `stumpi.update` 8.7 ms each (includes first-call compile); peak RSS 468 MB. Offline. stumpy is py3-none-any; numba 0.68.0 has cp313 wheels for Linux, macOS arm64 and Windows (amd64, arm64) |
| Role: motif and analog search over many short paths | PASS (behaviour) | planted motif in 36 of 120 paths: `match(max_distance=2.0, max_matches=1)` recovered all 36 within 2 steps and returned a match on 4 of 84 paths without it; 0.71 ms per path. One decision-time analog query (`mass`) over 119 paths and 16,634 candles: 42.6 ms. Synthetic only |

## 5. README or docs claims the code does not support (P42)

- "powerful and scalable", "efficiently computes": efficient after JIT warm-up only; a fresh process pays about 31 s and 468 MB before the first profile (S6). UNSUPPORTED for a per-decision subprocess on this hardware unless the numba cache is saved.
- "streaming (on-line) data": supported by `stumpi` and `floss`, but streaming state cannot be pickled (S5), so restart-safe streaming is UNSUPPORTED as shipped.
- "STUMPY is straightforward to install": true for the wheel; nothing here contradicts it.
- No predictive or forecasting claim is made in the README.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 5 | Causal primitives exist and are exact (stumpi left profile equals past-only recomputation, S1); the default self-join reads the future, and there are no timestamps, availability fields or splitters (section 3) |
| Transferable measurable predictive outcomes (14) | 2 | No outcome model; motif and analog retrieval works on synthetic paths (36 of 36 recovered, 4 false matches of 84) and could feed an analog base rate (N07) built elsewhere |
| Calibration, uncertainty and abstention (12) | 0 | none offered |
| Catalyst/social/on-chain features (10) | 3 | Cross-token analog distances, discords and regime segmentation on price paths; NaN-aware; index-only, no event covariates (S3, role row) |
| Decision/execution and stress compatibility (10) | 0 | nothing relevant |
| Code quality, maintenance and tests (8) | 6 | 599 tests, 22 motif tests passed offline; active (pin 2026-10-16, release 2026-02-08); object-dtype output and an unpicklable streaming class (S5) |
| Integration fit and extensibility (8) | 5 | Plain functions on numpy arrays; numba and llvmlite add a heavy JIT runtime (31 s cold, 468 MB) to a lab that is numpy-first |
| Experiment reproducibility and audit (8) | 3 | Exact algorithms give identical distances; `STUMPY_SEED` for approximate ones; no lineage; results need manual column split to save without pickle; stumpi state not persistable (S5) |
| Cost, latency and operational reliability (5) | 3 | Warm queries are fast (0.9 ms mass, 43 ms per analog query over 16.6k candles); cold start 31 s per process; offline; cp313 and Windows wheels (S6) |
| Licensing, security and data rights (7) | 7 | BSD-3 verified at the pin; numba BSD, llvmlite BSD-2 plus Apache-2.0 with LLVM exception; no network, no telemetry (section 2) |
| Total | 34 | |

## 7. Flags

- RESEARCH_ONLY: analog and motif search do not produce testable event probabilities; any analog base rate would be wrapper code with its own calibration test.
- NOT_REALTIME as installed (cold JIT 31 s, 468 MB per process); acceptable offline, or inside a long-lived process with a saved numba cache.
- Not LEAKAGE_FAIL: strict as-of use is possible through `stumpi`/left indices and past-only `mass`, shown exactly in S1; the default self-join and `fluss` are excluded from feature code (P36), and analog libraries must contain only paths whose candles were available before the decision (P13, P43).
- Scenarios touched: P13 and P43 (cross-path analogs must respect the decision time), P36, P12 (analogs for a new mint are an explicit cohort estimate, never a model output), P42.

## 8. Proposed role and integration decision

- Role: Phase 11 research tool for analog cohorts of short price paths (N07): find past paths whose last k candles resemble the current one, then report the matured outcome rate of those analogs as a labeled cohort estimate. Possibly a discord-based anomaly feature.
- Candidate INTEGRATION_DECISION: ISOLATED_RESEARCH. If an analog estimate survives walk-forward evaluation, INSPIRED_IMPLEMENTATION in numpy (z-normalized distance over a small library is a few lines) is likely cheaper than adding numba to the lab runtime.
- Phase 01 gap cells: LAUNCH_COHORT:MODEL_TRAINING, REGIME_NARRATIVE:MODEL_TRAINING (N07); marginally HIST_MARKET:POINT_IN_TIME_FEATURES.
