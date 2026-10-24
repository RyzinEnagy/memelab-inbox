# blue-yonder/tsfresh (reviewer R3)

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | blue-yonder/tsfresh, https://github.com/blue-yonder/tsfresh |
| Pinned SHA | `6af3c0030b6c9f02c3862a20e00cce87c984aa5b` |
| Commit date | 2026-07-06T13:28:19+12:00 |
| How fetched | `git fetch --depth 1` of the SHA, `/home/claude/pi_research/src/blue-yonder__tsfresh` (14 MB); tag `v0.21.2` (commit `6aa24fde...`) fetched shallowly for a diff |
| Review time (UTC) | 2026-10-24T05:23Z to 05:35Z |
| Version tested | PyPI wheel `tsfresh==0.21.2` (uploaded 2026-05-31) in venv `/home/claude/pi_research/venvs/blue-yonder__tsfresh` with pandas 3.0.5 (the lab's runtime version), numpy 2.5.4, scipy 1.18.1, statsmodels 0.15.0, stumpy 1.14.1, numba 0.68.0, scikit-learn 1.9.1, Python 3.13.17 (venv deleted after the review: 538 MB, over the 500 MB rule) |
| Relation to the pin | `git diff v0.21.2 <pin>` touches only `README.md` and one docstring line in `tsfresh/feature_extraction/feature_calculators.py` (a typo, "estimamte"); `diff -r` of the pin's `tsfresh/` against the installed package shows only that line and `tsfresh/scripts/data.txt` (absent from the wheel). The tested code is the pinned code |

## 2. License and security

- Root `LICENSE.txt` at the pin: MIT ("MIT LICENCE", "Copyright (c) 2016 Maximilian Christ, Blue Yonder GmbH"), sha256 `1804283622c8e51a4427aaa772d5ca522f89932fd610b294055435922af1c748`; `docs/license.rst` includes the same file.
- Dependencies (installed metadata): requests (Apache-2.0) with urllib3 (MIT), idna (BSD-3), charset-normalizer (MIT), certifi (MPL-2.0); statsmodels (BSD-3), patsy (BSD-2), pywavelets (MIT and BSD-3), scikit-learn, scipy, numpy, pandas (BSD), tqdm (MPL-2.0 and MIT), cloudpickle (BSD-3), stumpy (BSD-3) with numba (BSD) and llvmlite (BSD-2 and Apache-2.0 with LLVM exception). MPL-2.0 is file-level copyleft and only matters if those files are modified and distributed.
- Model weights: none.
- Install-time scripts: the wheel needs none. Building from source needs `pyscaffold>=3.3a0,<4` and `setuptools<70` (`pyproject.toml`), an old toolchain.
- Network: `requests` is a hard dependency but is used only in `tsfresh/examples/robot_execution_failures.py:72` and `tsfresh/examples/har_dataset.py:62` (UCI downloads on explicit call). No network at import, extraction or selection; all runs under `unshare -n` succeeded. No telemetry.
- Parallelism: default `n_jobs = N_PROCESSES = max(1, cores // 2)` from `tsfresh/defaults.py` (`NUMBER_OF_CPUS` env var overrides), so extraction starts a multiprocessing pool unless `n_jobs=0`.

## 3. Code paths inspected at the pin

| Concern | Anchor |
|---|---|
| Rolling windows (time handling) | `tsfresh/utilities/dataframe_functions.py:376` `roll_time_series(..., rolling_direction=1, max_timeshift=None, min_timeshift=0, ...)`; `:294` `_roll_out_time_series`: positive direction takes rows up to and including the shift, window named by the last row's sort value; negative direction takes rows from the shift onward and names the window by its first row's sort value. Windows count rows, not time, so gaps stretch them |
| Extraction (fit-like path) | `tsfresh/feature_extraction/extraction.py:30` `extract_features`, `:193` `_do_extraction`; `default_fc_parameters` is the second positional argument |
| Feature settings | `tsfresh/feature_extraction/settings.py:133` `ComprehensiveFCParameters`, `:297` `MinimalFCParameters`, `:323` `EfficientFCParameters`, `:23` `from_columns`. Defect at `:272-278`: `"mean_n_absolute_max": [{"number_of_maxima": 3, "number_of_maxima": 5, "number_of_maxima": 7}]` is one dict with a repeated key, so only 7 is computed |
| Missing values | `dataframe_functions.py:21` `check_for_nans_in_columns`; `:49` `impute` uses each column's finite max, min and median over the whole frame passed in (`:176` `get_range_values_per_column`); the `astype(np.float64, copy=False)` results at `:76`, `:98`, `:172` are discarded and raise a Pandas4Warning under pandas 3 |
| Selection | `tsfresh/feature_selection/selection.py:17` `select_features(X, y, fdr_level=0.05, hypotheses_independent=False, ...)` (univariate tests with Benjamini-Yekutieli); `tsfresh/convenience/relevant_extraction.py:17` `extract_relevant_features` extracts and selects in one call on whatever rows it gets |
| sklearn wrappers | `tsfresh/transformers/relevant_feature_augmenter.py:21` `RelevantFeatureAugmenter`, `per_column_imputer.py:15` `PerColumnImputer` |
| Probability, calibration | none |
| Serialization | settings are plain dicts (`from_columns`), `PickableSettings` |
| Tests | 26 test files, 331 `def test` functions. Ran `tests/units/utilities/test_dataframe_functions.py` against the installed wheel (copied out of the tree): 36 passed, 15 warnings (Pandas4Warning about `copy=`), exit 0, 6.0 s |

## 4. Smoke results

Script `SMOKES/blue-yonder__tsfresh/smoke_tsfresh.py` (sha256 `62a024b8...`), helper `r3_common.py`, runner `run_smoke.py`. Final command `unshare -n <venv>/bin/python -I -B smoke_tsfresh.py`, exit 0, wall 87.0 s, peak RSS 334.5 MB, user CPU 84.2 s. Raw: `smoke_tsfresh.out.txt`, `smoke_tsfresh.result.json` (sha256 `11cd9430...`). An earlier run exited 1 with `TypeError: extract_features() got multiple values for argument 'default_fc_parameters'` (R3 passed `column_id` positionally); fixed with keywords. Data: 150 of the seeded synthetic paths (seed 20261026), 21,469 rows of log return and log volume; one decision per path long enough (149 decisions, 76 positives) at a seeded index (seed 20261028), R3 synthetic label = close rises 5% above the decision close within the next 12 kept candles. challenge.csv has no paths and was not used.

| Smoke | Result | Numbers |
|---|---|---|
| S1 leak trap: rolling direction | FAIL (allowed silently) | 12-row windows for the 149 decisions: with `rolling_direction=1` 0 of 1,788 rows are later than the window's name time; with `rolling_direction=-1` 1,639 of 1,788 are. AUC of `ret__sum_values` 0.847 backward versus 0.959 forward; `ret__maximum` 0.786 versus 0.796. Nothing warns |
| S1: truncation invariance of backward windows | PASS | one path cut at 60%: 82 windows, 1,554 Efficient features, 127,428 of 127,428 cells equal between full and truncated input |
| S1: imputation scope | FAIL (leak if misused) | `impute()` on all rows versus train rows only gives a different fill for the same train cell (-0.01796 versus -0.02308): imputation must be fitted on training rows inside each fold |
| S2 probability shape | SKIPPED | feature extraction only |
| S3 missing values | FAIL (refuses, clear error) | NaN in a series: `ValueError: Column must not contain NaN values: ret`; gaps must be encoded by the caller |
| S4 calibration/uncertainty | SKIPPED | none offered |
| S5 persistence | PASS | `from_columns` of the 69 selected features, pickled (2,575 bytes) and reused, re-extracts all 69 columns with identical values |
| S6 cost | PASS offline, heavy | Comprehensive settings: 1,566 features from 2 series kinds, 125 ms per decision window in batch, 151 ms for one window alone; Efficient 137 ms; Minimal 2.8 ms; `roll_time_series` 10 s for 21,469 rows per direction (`n_jobs=0`); import 5.2 s; peak RSS 335 MB; venv 503 MB (numba via stumpy, statsmodels). Pure-Python wheel, Python 3.13 covered; ran on pandas 3.0.5 |
| P22: selection under null labels at small N | PASS | 149 decisions x 1,566 features: true labels select 69; five permuted label vectors select 0, 0, 0, 0, 0 at FDR 0.05 (synthetic, independent decisions) |

## 5. README or docs claims the code does not support (P42)

- "any types of sampled data or even event sequences can be characterised": calculators see only the sort order; timestamps and gaps are not used, and windows count rows (section 3). For irregular 5-minute paths with omitted intervals this is UNSUPPORTED without a caller-side gap encoding.
- "the filtering process mathematically controls the percentage of irrelevant extracted features": held on independent synthetic decisions (0 selected under 5 permutations), but the tests assume independent samples; decisions clustered by day and mint, as in the lab's data, are outside that guarantee (UNSUPPORTED for clustered data).
- `impute` docstring: "This function modifies df_impute in place ... all columns will be guaranteed to be of type np.float64": the `astype` calls' results are discarded (`:76`, `:98`, `:172`); the type guarantee rests on other code and is not shown by the line that claims it.
- Comprehensive settings promise `mean_n_absolute_max` for 3, 5 and 7 maxima; only 7 is computed (settings defect).

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 5 | Backward windows are truncation-invariant (S1, 127,428 of 127,428 cells); forward windows allowed silently with AUC 0.847 to 0.959 inflation; row-count windows; whole-frame `impute`; `extract_relevant_features` selects on whatever rows it is given; no splitter, no provider-lag handling |
| Transferable measurable predictive outcomes (14) | 2 | No model; features carried signal on synthetic data (69 selected), nothing about events or survival |
| Calibration, uncertainty and abstention (12) | 0 | none |
| Catalyst/social/on-chain features (10) | 5 | Hundreds of path features per series kind (returns, volume), per mint id; no timestamp awareness, no event covariates |
| Decision/execution and stress compatibility (10) | 0 | nothing relevant |
| Code quality, maintenance and tests (8) | 5 | 331 tests, 36 passed on pandas 3.0.5 with deprecation warnings; settings duplicate-key defect; discarded `astype`; old PyScaffold build; last release 2026-05-31 |
| Integration fit and extensibility (8) | 4 | pandas long-format API fits candle tables; heavy dependency tree (statsmodels, numba, requests; 503 MB venv); default multiprocessing must be turned off for a scout path |
| Experiment reproducibility and audit (8) | 6 | Deterministic extraction; `from_columns` reproduces the selected set exactly (S5); settings picklable; no run lineage |
| Cost, latency and operational reliability (5) | 3 | 2.8 ms per window with Minimal settings, 125 to 151 ms with Comprehensive; 335 MB; offline |
| Licensing, security and data rights (7) | 7 | MIT verified at the pin; permissive dependencies (MPL-2.0 files unmodified); network only in example loaders (section 2) |
| Total | 37 | |

## 7. Flags

- RESEARCH_ONLY: a feature generator; with 1,566 features against 100 to 300 eligible events per target (ACCEPTANCE_METRICS), selection must run inside each walk-forward fold and be logged in the experiment ledger (P22).
- Not LEAKAGE_FAIL: strict as-of use is possible (positive direction, truncation-invariant), but containment is required: forbid `rolling_direction < 0`, apply the 300 s provider lag before rolling, fit `impute` and `select_features` on training rows only, never call `extract_relevant_features` on mixed periods (P13, P36, P20).
- Scenarios touched: P22, P36, P20, P42.

## 8. Proposed role and integration decision

- Role: Phase 05 and 08 feature exploration on candles available at the decision, mainly as a catalogue of candidate calculators; the Minimal set is cheap enough for inference.
- Candidate INTEGRATION_DECISION: ISOLATED_RESEARCH; for production features, INSPIRED_IMPLEMENTATION of the few calculators that survive walk-forward selection in numpy (MIT allows it with notice), which also avoids the numba and statsmodels runtime.
- Phase 01 gap cells: HIST_MARKET:POINT_IN_TIME_FEATURES and REGIME_NARRATIVE:POINT_IN_TIME_FEATURES (N06).
