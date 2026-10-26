# eslazarev/purged-cross-validation

- URL: https://github.com/eslazarev/purged-cross-validation
- Pinned commit: 07692dd862d37a988233e190706afb18c5101948 (2026-10-23T10:58:37+03:00), cloned 2026-10-23T15:53:13Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23.
- Category: validation/metrics
- Discovery channel: GITHUB_API "purged cross validation" (rank 1) and "deflated sharpe ratio" (rank 1); Firecrawl developer search; curated wilsonfreitas/awesome-quant
- Stars/forks (low weight, from search time): 58/not recorded
- License (from LICENSE file text, not badge): MIT (Copyright (c) 2026 Evgenii Lazarev) ; transitive notes: numpy, pandas, scipy (BSD), scikit-learn (BSD); optional optuna (MIT)
- Package: PyPI `purgedcv` 0.1.11 (wheel purgedcv-0.1.11-py3-none-any.whl, uploaded 2026-10-16; 24 releases since 2026-05-16) ; Python/OS: requires-python >=3.11, classifiers 3.11-3.15, OS Independent, pure Python ; native deps: none beyond numpy/scipy/sklearn wheels
- Maintenance: last commit 2026-10-23; CI files .github/workflows/ci.yml (pytest with coverage on Linux, Python 3.11-3.15), docs.yml; tests 21 unit + 33 e2e test files, 540 test functions, includes property-based tests (tests/test_purge_embargo_properties.py, test_splitter_properties.py, test_time_properties.py). No Windows CI
- Security surface: none found in the library: no network, file or subprocess calls in src/purgedcv; CI has a PR version-bump job with scoped write permission that checks out trusted base tooling (ci.yml:14-36); tools/ release scripts not run

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | NOT_SUPPORTED | Not a backtester |
| tick/trade replay | NOT_SUPPORTED | |
| CPMM math | NOT_SUPPORTED | |
| CLMM/DLMM math | NOT_SUPPORTED | |
| routes | NOT_SUPPORTED | |
| fees/taxes | NOT_SUPPORTED | |
| thin exits / size-dependent impact | NOT_SUPPORTED | |
| fill timing (next bar, latency) | NOT_SUPPORTED | Rows carry prediction_time and evaluation_time only |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED | Purge on half-open label horizons src/purgedcv/_purge.py:59-80; embargo src/purgedcv/_embargo.py:74; monotonic prediction times enforced src/purgedcv/_time.py:233-234 and src/purgedcv/_base.py (validate_times at construction); audit_splitter src/purgedcv/diagnostics.py:133; assert_no_temporal_leakage :288; assert_embargo_respected :349; independently re-checked in the smoke test |
| async event/catalyst injection | NOT_SUPPORTED | Out-of-order event rows are rejected (smoke [5]) |
| wallets/on-chain | NOT_SUPPORTED | |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED (limited) | PurgedGroupKFold src/purgedcv/_purged_kfold.py:125-259 with group-disjoint assertion src/purgedcv/_base.py:148-176; purge still applies across groups by time, so concurrent tokens empty the train set (smoke [7]) |
| walk-forward / holdout / multiple testing | SOURCE_CODE_VERIFIED | WalkForwardSplit expanding/sliding src/purgedcv/_walk_forward.py:18-173; PurgedKFold _purged_kfold.py:20-122; CombinatorialPurgedCV and CombinatoriallySymmetricCV src/purgedcv/_cpcv.py:26,299; PBO via CSCV src/purgedcv/_pbo.py:279; DSR src/purgedcv/_metrics.py:197; MinTRL :385; MinBTL :486; effective_n_trials :557. No built-in sealed holdout or baseline strategy (caller supplies) |
| metrics/report | SOURCE_CODE_VERIFIED | path_metrics src/purgedcv/_path_metrics.py:112; reconstruct_paths src/purgedcv/_paths.py:19; per-fold audit DataFrame (19 columns, smoke [4]) |
| live trading code present (must be avoidable) | NOT_SUPPORTED | none |

## Fill and chronology assumptions (read the code)

No fills. Each row i has a prediction_time (when the decision is made) and an evaluation_time (when its label or trade outcome is known). Test folds are contiguous index blocks (_purged_kfold.py:112-122) or the trailing blocks for walk-forward (_walk_forward.py:139-152). A training row is dropped if its interval [prediction, evaluation) overlaps any test row's interval padded by purge_horizon (_purge.py:73-79, merged half-open intervals); training rows whose prediction time falls in [test evaluation, test evaluation + embargo] are dropped after each test block; walk-forward candidates are only rows strictly before the test fold (_walk_forward.py:154-159). Prediction times must be monotonic non-decreasing at construction (_time.py:233-234); tz-aware input is converted to UTC-naive (_time.py:45,63). The library knows nothing about data availability (known-at) inside features; the lab must set prediction_time to decision_time after all inputs are available and evaluation_time to the trade's last execution_time.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3.13 -m venv /home/claude/ext/venvs/eslazarev__purged-cross-validation
/home/claude/ext/venvs/eslazarev__purged-cross-validation/bin/pip install --only-binary :all: purgedcv==0.1.11
/home/claude/ext/venvs/eslazarev__purged-cross-validation/bin/python -I audits/backtesting/research/smoke/eslazarev__purged-cross-validation/script.py
```
Outcome: pip exit 0 in 20 s (numpy 2.5.4, pandas 3.1.0, scipy 1.18.1, scikit-learn 1.9.1); script exit 0 in 2 s, RESULT PASS. On 30 hourly bars with 3 h labels: PurgedKFold(5, embargo 2 h) dropped 5-7 rows per fold and an independent overlap checker found no leakage; WalkForwardSplit expanding and sliding (train_size 8) purged the 2 rows whose labels cross the test start (train ends at row 12, test starts at row 15); library asserts agreed; tz-aware UTC splits identical to naive; unsorted times rejected ("prediction_times must be monotonic non-decreasing."); DSR deterministic (0.012967 with 20 trials vs 0.978729 with 1). Warning: PurgedGroupKFold over 3 interleaved tokens returned an EMPTY training set in every fold with no error. Output in smoke/eslazarev__purged-cross-validation/output.txt.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 2.0 | 6.00 | Domain-agnostic, irregular timestamps fine, groups for tokens; no crypto semantics |
| B microstructure | 17 | 0.0 | 0.00 | Not applicable, absent |
| C point-in-time | 15 | 3.5 | 10.50 | Purge/embargo on label horizons, monotonic-time guard, audit and assert helpers, property tests, independently verified; covers split leakage only, not feature availability |
| D catalyst/on-chain events | 11 | 0.5 | 1.10 | Rows can be event times, but no event ingestion and unsorted rows rejected |
| E TA/strategy flexibility | 9 | 0.0 | 0.00 | Not applicable, absent |
| F statistical validation | 11 | 4.5 | 9.90 | Walk-forward, purged k-fold, CPCV with paths, PBO, DSR, PSR, MinTRL, MinBTL, effective trials; holdout and baselines left to the caller |
| G integration fit | 9 | 4.5 | 8.10 | Pure Python wheel, numpy/pandas/scipy/sklearn, sklearn splitter API, no I/O, works on Python 3.13 |
| H maintenance/tests | 6 | 4.0 | 4.80 | Active, 540 tests incl. property-based, CI 3.11-3.15; 5 months old, single maintainer, Linux-only CI |
| I license/supply chain | 5 | 4.5 | 4.50 | MIT, PyPI wheel matching repo version, uv.lock, minimal deps |
| J operational footprint | 2 | 5.0 | 2.00 | 20 s install, 2 s run, no services |
| Total | 100 | | 46.90 | |

Hard gates: none. Most important limitation for memecoins: the library validates splits, not data availability, and it cannot do leave-token-out CV across tokens that trade at the same time (purge by time empties the training set), which is the normal case for a memecoin cohort. One credible negative finding: `split()` yields an empty training index without warning or error when purging removes every candidate row (smoke [7]; no empty-train check in src/purgedcv/_base.py), so an unattended pipeline could fit on nothing; only `audit_splitter` exposes it through its `train_nonempty` column.
Disposition: PIP. Suggested use: INSTALL (validation layer only, outside the fill path).
