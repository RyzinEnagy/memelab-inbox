# Source review: baobach/mlfinpy (reviewer R2)

Synthetic challenge and constructed price paths only. Every number below is a format and behaviour check, never evidence of memecoin edge.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | baobach/mlfinpy, https://github.com/baobach/mlfinpy |
| Pinned SHA | `e21e4066164fafd6e59e1d067e75e6096bfc8d07` (Phase 02 SHORTLIST.csv) |
| Commit date | 2026-10-11T11:24:12-04:00 (merge of PR #7) |
| How fetched | shallow fetch of the pinned SHA at 2026-10-24T04:33Z into `/home/claude/pi_research/src/baobach__mlfinpy` (93 MB, mostly `mlfinpy/dataset/data/tick_data.csv` and research notebooks); HEAD verified equal to the pin |
| Review time (UTC) | 2026-10-24T04:33Z to 05:22Z |
| Version tested | `pyproject.toml` version 0.1.2, built from the pinned source with poetry-core into venv `/home/claude/pi_research/venvs/baobach__mlfinpy` on Python 3.12.3 (numpy 1.26.4, numba 0.60.0, llvmlite 0.43.0, pandas 2.3.3, scikit-learn 1.9.1, scipy 1.17.1, statsmodels 0.14.6). Python 3.13 is not possible (below) |
| Relation to PyPI | PyPI's latest is 0.1.2 (wheel 2024-10-09, sha256 `2e0237e0a5f693bb...`). Against it the pin differs in `__init__.py` (extra imports) and `cross_validation/combinatorial.py` (docstrings only) and adds `bet_sizing/`; `cross_validation/cross_validation.py` and `labeling/labeling.py` are byte-identical, so the defects below are in the release too |

## 2. License and security

- Root `LICENSE`: MIT ("Copyright (c) 2024, Robert Bach"), sha256 `db54d4e2b7046968250ed5cf55294bcdb13d0f2f8616f0223382085116db303b` (matches Phase 02).
- Provenance finding: parts of the code and tests come from the BSD-3-Clause era of Hudson and Thames' mlfinlab (fork `closedloop/mlfinlab` at `47889b88`, 2020-03-19, LICENSE "BSD 3-Clause License, Copyright (c) 2019, Hudson and Thames Quantitative Research"). The defective `PurgedKFold` line is the same statement (`test_times = pd.Series(index=[self.samples_info_sets[start_ix]], ...)`, mlfinlab `cross_validation.py:91`), the test docstring "This is how the observations dataset looks like" appears in both test files, and 77% of the non-blank lines of `tests/test_cross_validation.py` (37% of `labeling.py`, 36% of `cross_validation.py` after reformatting) sit in blocks identical to mlfinlab. mlfinpy carries no Hudson and Thames notice (0 matches in LICENSE and package code). INFERENCE: BSD-3 requires keeping that copyright notice, so the MIT relicensing looks incomplete. Evidence: `SMOKES/baobach__mlfinpy/provenance_check.sh`, `raw_provenance_check.txt`.
- The README describes the source material as "proprietary works and code snippent by Dr. Marcos López de Prado" (spelling as in the README), and the `mlfinpy/__init__.py` docstring states the package is for academic purposes only and not meant for live trading. Data rights for the snippet-derived code: UNKNOWN.
- Runtime dependencies: numpy below 1.27, numba 0.60.x (BSD; bundles llvmlite with LLVM, Apache-2.0 with LLVM exception), pandas below 3, scipy, matplotlib, statsmodels; scikit-learn is declared only under the extra `optionals` but imported unconditionally. Licenses: `SMOKES/baobach__mlfinpy/raw_dep_licenses.txt`.
- Model weights: none. Install-time scripts: none (poetry-core). Data files ship inside the package (`mlfinpy/dataset/data/`), read locally.
- Network: no network code (grep); smoke ran inside `unshare -n`. No telemetry.
- Secrets: none. Persistence: pickle of plain objects.

## 3. Code paths inspected at the pin

| Area | Anchor | Observation |
|---|---|---|
| Purge primitive | `mlfinpy/cross_validation/cross_validation.py:19` `ml_get_train_times` | correct when given the test window (closed intervals, conservative) |
| Purged k-fold | `cross_validation.py:51` `PurgedKFold`, `split` `:80`; test window built at `:122` to `:124` as `[samples_info_sets.iloc[start_ix], samples_info_sets.iloc[end_ix - 1]]` | `iloc[start_ix]` is the label END of the first test row, not its start (AFML uses the start), so training labels that end before the first test label ends are never purged; `get_loc` on duplicate times returns slices that break `split` |
| Combinatorial purged CV | `cross_validation/combinatorial.py:35` `CombinatorialPurgedKFold`; `self.embargo = 0` inside `split` (`:156`); scalar `get_loc` results appended then `np.concatenate` (`:190`); dead code after the loop (`:198` to `:210`) that always raises; positional `Series[0]` indexing (`:157`, `:166`) deprecated in pandas | embargo argument ignored; docstring documents `pct_embargo` but the parameter is `embargo` |
| Triple barrier | `mlfinpy/labeling/labeling.py:18` `triple_barriers` (close prices only, path from the event bar, strict `>` and `<`), `:80` `add_vertical_barrier` (next bar at or after t + horizon), `:136` `get_events` (with `side_prediction=None` the stop-loss multiple is replaced by the profit-taking one), `:237` `barrier_touched`, `:285` `get_bins` | see Part B of the smoke |
| Packaging | `mlfinpy/__init__.py` imports `mlfinpy.util`, which imports scikit-learn (`util/generate_dataset.py:10`) | `import mlfinpy` fails unless the `optionals` extra is installed |
| Tests | 21 test files | ran `tests/test_cross_validation.py` and `tests/test_labels.py`: 17 passed in 9.46 s, exit 0 (`SMOKES/baobach__mlfinpy/raw_repo_tests_mlfinpy.txt`). `test_purgedkfold_03_simple` builds its expected window with the same label-end start, so the test encodes the defect; no test covers `CombinatorialPurgedKFold` |

## 4. Smoke results

Script `SMOKES/baobach__mlfinpy/smoke_mlfinpy.py` (with `common.py`, `leakcheck.py`, `runner.py`) inside `unshare -n` on Python 3.12; exit 0, wall 10.56 s, peak RSS 278.1 MB; raw output `SMOKES/baobach__mlfinpy/raw_smoke_mlfinpy.txt`. Label window of a row = `[decision_time, label_matures_at)`; leaks counted by an independent brute-force checker.

Part A, purge and embargo:

| Check | Result | Numbers |
|---|---|---|
| Constructed case (six 24 h labels at 0, 6, 12, 30, 36, 60 h; PurgedKFold, 3 folds) | FAIL | fold with test rows [12, 36) and [30, 54): training rows [0, 24) and [6, 30) still overlap; fold with test rows [36, 60) and [60, 84): training row [30, 54) still overlaps. `ml_get_train_times` given the correct window [30, 54] keeps only the rows decided at 0 h and 60 h, which is correct (closed intervals) |
| Challenge decision_time / label_matures_at, PurgedKFold(5, pct_embargo 0.01) | FAIL | 2,892 rows (one duplicate time dropped, see next row): training rows overlapping a test label window per fold 0, 99, 96, 95, 111; plain KFold leaves 111, 167, 208, 200, 111, so the pre-test side is barely purged. The configured 28-row post-test embargo is respected (0 violations) |
| Shared decision times (each time twice, as memelab theses share an export commit time) | FAIL | `PurgedKFold.split` raises `TypeError: '<' not supported between instances of 'int' and 'slice'` |
| CombinatorialPurgedKFold(6, 2) | FAIL | unique times: `ValueError: zero-dimensional arrays cannot be concatenated`; duplicated times: all 15 splits are yielded, then the generator raises `ValueError` from the dead code after the loop, so `list()` or scikit-learn would fail. Training sets for `embargo=0` and `embargo=5` are identical (embargo forced to 0). Purge itself leaves 0 overlaps here (it uses the correct test start) |
| Python 3.13 | FAIL | `uv pip compile -p 3.13 --only-binary :all:` cannot resolve: numba 0.60 has no cp313 wheel (`raw_py313_wheel_resolution.txt`); numpy 1.26.4 has none either |
| Import without the extra | FAIL | `import mlfinpy` raises `ModuleNotFoundError: No module named 'sklearn'` (`raw_import_without_extra.txt`) |

Part B, triple-barrier labels against a reference of the memelab T1 rule (TARGET_REGISTRY.md: P0 = close of the newest candle available at the decision; entry 300 s after the decision; path = candles starting at or after entry and ending within 24 h; touch when high >= 1.25 x P0 or low <= 0.85 x P0; both in one candle = AMBIGUOUS_BAR, negative; PENDING until entry + 24 h + 900 s). mlfinpy events were stamped at the reference candle's close, `pt_sl = [1, 0.6]`, target 0.25 (so +25% and -15%):

| Constructed 5-minute path | memelab T1 | mlfinpy, side None | mlfinpy, side +1 |
|---|---|---|---|
| A: clean rise to +30% | TARGET_FIRST (1) | 1 | 1 |
| B: -16% first, then +30% | INVALIDATION_FIRST (0) | 1 (stop replaced by the +-25% symmetric barrier) | 0 |
| C: +26% wick, closes stay at or below +5% | TARGET_FIRST (1) | 0 (close prices only) | 0 |
| D: one candle touches both barriers, then +26% close | AMBIGUOUS_BAR (0) | 1 | 1 |
| E: high and close exactly +25.0% | TARGET_FIRST (1) | 0 (strict >) | 0 |
| F: +28% inside the 5 to 10 minute entry gap, flat after entry | NEITHER (0) | 1 (path starts at the event bar, P06) | 1 |
| G: +31% at 5.8 h, data ends at 6.8 h | PENDING | 1 (labeled before maturity, P05) | 1 |
| H: no candles from 2 h to 40 h, then +31% | NEITHER (0) | 1 (vertical barrier moved to +40 h) | 1 |

13 of 16 case-mode pairs disagree with the memelab rule. Labeling cost: 200 events on 5,000 bars in 0.37 s (1.9 ms per event, single process).

| ID | Result | Numbers |
|---|---|---|
| S1 leak trap | FAIL | no feature-availability notion; its CV purges by label windows only, and PurgedKFold does so incorrectly (Part A) |
| S2, S3, S4 | SKIPPED | labeling and CV library; no probabilities or calibration produced; bet sizing (pin only) not tested |
| S5 persistence | PASS | pickled PurgedKFold yields identical folds |
| S6 cost | PARTIAL | import 2.4 to 4.3 s (numba), labeling 1.9 ms per event, peak RSS 278 MB, offline. Only Python 3.11 and 3.12 work (numpy below 1.27, numba 0.60); pandas below 3 required; PyPI ships one `py3-none-any` wheel, and numba 0.60 and numpy 1.26 have win_amd64 wheels up to cp312 (`raw_pypi_files_r2.txt`) |
| Repo tests | PASS (but encode the defect) | 17 passed |

## 5. Claims the code does not support (P42)

- UNSUPPORTED: `PurgedKFold` docstring, "The train is purged of observations overlapping test-label intervals" (Part A: 95 to 111 overlapping rows per fold).
- UNSUPPORTED: `CombinatorialPurgedKFold` docstring documents `pct_embargo` ("Percent that determines the embargo size. Default is 1"); the parameter is `embargo` and `split` sets it to 0.
- UNSUPPORTED: README installation `pip install mlfinpy` then use; `import mlfinpy` fails without the `optionals` extra.
- UNSUPPORTED: README "build this package from ground up" next to "inspired by MlFinLab"; tests and code lines match the BSD-3 mlfinlab (section 2).
- UNSUPPORTED: `pyproject.toml` classifiers advertise Python 3.8, 3.9 and 3.10 while the dependency spec requires `python = "^3.11"`; and Python 3.13 cannot install at all (Part A).

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 1 | only `ml_get_train_times` behaves correctly when called directly (constructed case); PurgedKFold leaks 95 to 111 rows per fold, CPCV crashes and ignores the embargo, triple barrier labels pending events and uses the event bar (Part A, Part B G and F) |
| Transferable measurable predictive outcomes (14) | 2 | triple-barrier and meta-label concepts fit the lab's event targets, but the implementation disagrees with the memelab rule in 13 of 16 cases (Part B) |
| Calibration, uncertainty and abstention (12) | 0 | none tested or found for calibration |
| Catalyst, social and on-chain features (10) | 0 | none evaluated |
| Decision and execution compatibility (10) | 1 | meta-labeling with `side_prediction` honours asymmetric barriers (Part B, side +1 column); bet sizing exists at the pin but was not tested |
| Code quality, maintenance and tests (8) | 2 | 21 test files and 17 passing tests, but a test encodes the purge defect, CPCV is untested and broken, packaging is broken, pandas deprecation warnings |
| Integration fit and extensibility (8) | 1 | no Python 3.13, numpy and pandas upper bounds, numba, import fails without an extra (Part A rows) |
| Experiment reproducibility and audit (8) | 2 | deterministic outputs, pickle identical (S5); no audit of what was purged |
| Cost, latency and operational reliability (5) | 3 | 1.9 ms per event and offline, but multi-second import and a CPCV generator that always raises at the end (S6, Part A) |
| Licensing, security and data rights (7) | 3 | MIT declared, no network; code derived from BSD-3 mlfinlab without its notice and snippet data rights UNKNOWN (section 2) |
| **Total** | **15** | |

## 7. Flags and adversarial scenarios

- LEAKAGE_FAIL: PurgedKFold leaves overlapping label windows in training (constructed case and challenge); triple-barrier labels a pending event (P05) and enters on the event bar (P06). Not usable for strict as-of training without replacement code.
- License caution (P31): probable BSD-3 attribution gap (INFERENCE from the provenance check); copying mlfinpy code would need both the MIT and the Hudson and Thames BSD-3 notices, and the snippet rights are UNKNOWN.
- RESEARCH_ONLY is self-declared by the package (its `__init__.py` docstring says academic use only, not live trading).
- P20: overlapping horizons not purged on the leading side of each fold.
- P05, P06, P37: pending labeled, same-bar entry, sparse vendor data silently stretches the horizon to 40 h.
- P42: five claims in section 5.
- New wrong-but-plausible case found: a library whose own unit test passes because the test builds the expected purge window with the same wrong start time; caught only by an independent overlap checker on constructed windows.

## 8. Proposed role and integration decision

No role as a dependency. purgedcv covers purged and combinatorial CV correctly (separate review), and the lab's TARGET_REGISTRY already defines a stricter barrier label (high/low touches, entry lag, ambiguous bars, pending and censored classes) than mlfinpy implements. The constructed paths A to H in `smoke_mlfinpy.py` are worth keeping as test fixtures for the lab's own Phase 06 barrier evaluator.

Candidate INTEGRATION_DECISION: REJECT. Phase 01 gap cells it was shortlisted for (DECISION_RECORDS:EVENT_LABELS MISSING, HIST_MARKET:EVENT_LABELS PARTIAL, SOCIAL_REPLAY:MODEL_TRAINING PARTIAL) are not addressed by this package; they stay with the lab's own evaluator and purgedcv.
