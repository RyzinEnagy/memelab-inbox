# Source review: eslazarev/purged-cross-validation (purgedcv) (reviewer R2)

Synthetic challenge only. Every number below is a format and behaviour check on `challenge.csv` (sha256 `18fda40c...d5f23d`), never evidence of memecoin edge.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | eslazarev/purged-cross-validation, https://github.com/eslazarev/purged-cross-validation (PyPI name `purgedcv`) |
| Pinned SHA | `07692dd862d37a988233e190706afb18c5101948` (Phase 02 SHORTLIST.csv) |
| Commit date | 2026-10-23T10:58:37+03:00 |
| How fetched | shallow fetch of the pinned SHA at 2026-10-24T04:33Z into `/home/claude/pi_research/src/eslazarev__purged-cross-validation`; HEAD verified equal to the pin |
| Review time (UTC) | 2026-10-24T04:33Z to 05:20Z |
| Version tested | 0.1.11 (static version in `pyproject.toml`, hatchling build) from the pinned source, venv `/home/claude/pi_research/venvs/eslazarev__purged-cross-validation`, Python 3.13.17, numpy 2.5.4, pandas 3.1.0, scikit-learn 1.9.1, scipy 1.18.1; hypothesis 6.170.9 added for the repo's property tests |
| Relation to PyPI | the 18 `.py` files of `purgedcv-0.1.11-py3-none-any.whl` (2026-10-16, sha256 `b7d80142a10ef615...`) are byte-identical to the pin (the pin was committed a week after the release, without changes to the package files) |

## 2. License and security

- Root `LICENSE`: MIT ("Copyright (c) 2026 Evgenii Lazarev"), sha256 `554e85fd9686cec7c3046c9b6f192a76e6e05c6413b29cf8732feadb80e98341` (matches Phase 02). No vendored code. Methods follow Lopez de Prado (AFML ch. 7 and 12) and Bailey et al.; the code is a separate implementation (half-open interval primitives in `src/purgedcv/_intervals.py`), not a transcription of the book's snippets.
- Runtime dependencies: numpy, pandas, scikit-learn, scipy (BSD-3). Optuna is optional and imported lazily (`optuna_integration.py:1` to `:17`); not installed. Licenses: `SMOKES/eslazarev__purged-cross-validation/raw_dep_licenses.txt`.
- Repo extras not installed with the package: `paper/` (PDF and TeX), `tools/` (release and benchmark scripts), `context7.json` (a documentation-indexing config). None run at install or import.
- Model weights: none. Install-time scripts: none (hatchling).
- Network: no network code in `src/purgedcv` (grep); smoke ran inside `unshare -n`. No telemetry.
- Secrets: none. Persistence: splitters are deterministic configuration; nothing to persist beyond the times.

## 3. Code paths inspected at the pin

| Area | Anchor | Observation |
|---|---|---|
| Purge primitive | `src/purgedcv/_purge.py` `purge`; `_intervals.py:68` `overlaps_any_half_open_interval` | a training row is dropped if `[prediction_time, evaluation_time)` overlaps any test interval `[prediction - h, evaluation + h)`; half-open, so a label maturing exactly at the test decision is kept |
| Embargo | `src/purgedcv/_embargo.py` `apply_embargo`; `_intervals.py:101` `points_in_any_closed_interval` | drops training rows decided inside `[test evaluation, test evaluation + embargo]`; row-count and fraction modes too |
| Splitter pipeline | `src/purgedcv/_base.py:32` `BaseTemporalSplitter`, `__init__` `:52` (times validated, `require_monotonic=True`), `split` `:148`, stages `:177` (candidate, purge, embargo, finalize) | groups, when bound, are checked disjoint on every fold |
| Splitters | `_walk_forward.py:18` `WalkForwardSplit` (test folds are row-count blocks at the end; no `groups` argument; embargo is a no-op by construction), `_purged_kfold.py:20` `PurgedKFold`, `:125` `PurgedGroupKFold`, `_cpcv.py:26` `CombinatorialPurgedCV` | folds are by row count, not by calendar day |
| Diagnostics | `diagnostics.py:133` `audit_splitter`, `:288` `assert_no_temporal_leakage`, `:349` `assert_embargo_respected` | per-fold counts of rows removed by purge and embargo |
| Selection overfitting | `_pbo.py:279` `probability_of_backtest_overfitting`; `_metrics.py:197` `deflated_sharpe_ratio` | P22 tools |
| Feature availability | none | the library sees label windows only |
| Tests | 54 test files | ran `test_purge.py`, `test_embargo.py`, `test_walk_forward.py`, `test_purged_kfold.py`, `test_purge_embargo_properties.py` (hypothesis), `test_cpcv.py`: 122 passed in 4.77 s, exit 0 (`SMOKES/eslazarev__purged-cross-validation/raw_repo_tests_purgedcv.txt`) |

## 4. Smoke results

Script `SMOKES/eslazarev__purged-cross-validation/smoke_purgedcv.py` (with `common.py`, `leakcheck.py`, `runner.py`) inside `unshare -n`; exit 0, wall 43.65 s (most of it the 12,870-combination PBO), peak RSS 163.1 MB; raw output `SMOKES/eslazarev__purged-cross-validation/raw_smoke_purgedcv.txt`. Every split was re-checked by an independent brute-force checker (`leakcheck.py`): a training row leaks when its label window `[decision_time, label_matures_at)` overlaps any test row's window.

| ID | Result | Numbers |
|---|---|---|
| Purge, constructed case | PASS | six 24 h labels at 0, 6, 12, 30, 36, 60 h; test row [30, 54). `purge` kept rows 0, 1, 5 (row 1 matures exactly at 30 h, allowed; rows 2 and 4 overlap and were removed); with row 1 maturing one second later it was removed too; embargo 24 h then removed row 5 (decided at 60 h, inside [54, 78] h). The independent checker flags exactly rows 2 and 4 |
| Purge on the challenge's decision_time and label_matures_at | PASS | 2,893 labeled rows, irregular gaps (0 to 6,694 s, median 604 s, one duplicate time). WalkForwardSplit (5 folds of 280 rows), PurgedKFold (5 folds, embargo 24 h) and CombinatorialPurgedCV (6 groups, 2 test, 15 folds, embargo 24 h): 0 overlapping training rows and 0 embargo violations in every fold. `audit_splitter` per fold for PurgedKFold: purge removed 111, 168, 207, 200, 111 rows and embargo 112, 107, 110, 104, 0. For contrast, scikit-learn KFold(5) leaves 111, 168, 207, 200, 111 overlapping rows and TimeSeriesSplit(5, 280) leaves 90, 102, 110, 111, 91 |
| The challenge's own split | finding | the "embargo" split spans 14.0 h but labels run 24 h: 45 val rows overlap holdout label windows and 96 train rows overlap val windows (purgedcv and the independent checker agree; same counts as rows with `label_matures_at` after the next split's first decision). The shared base model in the other R2 smokes purged these rows |
| Groups | PASS with a gap | PurgedGroupKFold by exact mint: 0 mints shared between train and test and 0 overlaps in every fold. WalkForwardSplit does not accept `groups` (TypeError). Grouping by symbol would merge 300 mints into 120 groups; the library cannot know which key is identity |
| S1 leak trap | FAIL (no guard in the library) | walk-forward with legitimate features: mean Brier 0.03330, mean AUC 0.7504; with the trap column: 0.00325 and 0.9994. Purging works on label windows; feature availability is the wrapper's job |
| Input validation | PASS | rows out of time order: `ValueError: prediction_times must be monotonic non-decreasing`; NaT: `ValueError: evaluation_times contains NaT values`; evaluation before prediction: `ValueError` |
| S2, S3, S4 | SKIPPED | a splitter produces no probabilities and takes no features; NaN times are refused (above) |
| P22 role | PASS | PBO by CSCV (16 blocks, 12,870 combinations): 20 pure-noise configurations PBO 0.609; with one configuration given a real drift PBO 0.000 |
| S5 persistence | PASS | pickled splitter (46,805 bytes) gives identical folds after reload; folds are deterministic |
| S6 cost | PASS | folds in 17 to 153 ms on 2,893 rows; peak RSS 163 MB; offline. PyPI ships one `py3-none-any` wheel, Python 3.11 to 3.15 declared, 3.13 tested; Windows uses the same wheel |

## 5. Claims the code does not support (P42)

- None found UNSUPPORTED among the claims tested (purge, embargo, walk-forward, purged k-fold, group k-fold, CPCV, PBO).
- NOT TESTED by me: the README's results tables (for example k-NN R2 of 0.83 under shuffled KFold against -1.48 under PurgedKFold, and the deployment comparisons) come from notebooks I did not run; treat them as unverified.
- The README states the limits plainly: "These controls do not guarantee independence or prevent every form of leakage", which matches S1.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 14 | purge by label maturity correct on the constructed case including the one-second boundary, and zero leaks on the challenge for walk-forward, purged k-fold, group k-fold and CPCV under an independent checker; embargo verified; time inputs validated. Not covered: feature availability (S1), calendar-day folds, model-artifact cutoffs for replay |
| Transferable measurable predictive outcomes (14) | 3 | group k-fold by exact mint measures cross-token generalization (Groups row); produces no outcome model |
| Calibration, uncertainty and abstention (12) | 2 | PBO detects selection overfitting (P22 row); deflated Sharpe exists (not tested); nothing for probability calibration |
| Catalyst, social and on-chain features (10) | 0 | none |
| Decision and execution compatibility (10) | 1 | PBO and deflated Sharpe guard against false confidence in strategy selection (P22 row); no fees or execution |
| Code quality, maintenance and tests (8) | 6 | 54 test files including hypothesis property tests, 122 core tests pass; typed; clear docs; young project (0.1.x, Alpha classifier) with one maintainer |
| Integration fit and extensibility (8) | 7 | pure Python, scikit-learn splitter interface, Python 3.13, `purge` and `apply_embargo` usable as primitives for the lab's day-based folds; WalkForwardSplit lacks groups |
| Experiment reproducibility and audit (8) | 6 | deterministic folds, identical after pickle, `audit_splitter` records rows removed by purge and embargo per fold (S5, splitter rows) |
| Cost, latency and operational reliability (5) | 5 | millisecond splits, offline (S6) |
| Licensing, security and data rights (7) | 7 | MIT, independent implementation, no network, optional dependency imported lazily (section 2) |
| **Total** | **51** | |

## 7. Flags and adversarial scenarios

- Flags: none.
- P20: overlapping 24 h labels across fold boundaries are purged; verified on hand-built and challenge data. The challenge's 14 h embargo split itself is too short for 24 h labels, which this library exposes.
- P14 and P01: group k-fold by exact mint keeps mints out of both sides; the choice of identity key (mint, not symbol) stays with the caller.
- P22: PBO separates noise (0.609) from a real effect (0.000).
- P36: feature availability is not checked (S1); the lab's as-of view must do it.
- P13: no notion of model-artifact training cutoffs; the lab's walk-forward artifacts must carry their own cutoff.
- New wrong-but-plausible case found: a dataset "embargo" band shorter than the label horizon (14 h band, 24 h labels) looks like a gap but leaves 45 overlapping rows; caught by `purge` and by the independent checker.

## 8. Proposed role and integration decision

Training-time splitter for Phases 07 to 12: build the lab's day-based walk-forward folds, pass `label_matures_at` as the evaluation time and the decision time as the prediction time, and let `purge` (and `audit_splitter`) enforce and document the "label matured by the training cutoff" rule; use PurgedGroupKFold by exact mint for the group sensitivity runs and PBO for the experiment ledger. Feature availability stays in the lab's own as-of view.

Candidate INTEGRATION_DECISION: ADAPTER (offline training and evaluation only; pin 0.1.11). Phase 01 gap cells addressed: HIST_MARKET:MODEL_TRAINING (MISSING), SOCIAL_REPLAY:MODEL_TRAINING (PARTIAL), and the MODEL_REGISTRY cells named in Phase 02 (DECISION_RECORDS PARTIAL, HIST_MARKET MISSING, SOCIAL_REPLAY MISSING) for split audit records. License obligation if code is copied: MIT notice.
