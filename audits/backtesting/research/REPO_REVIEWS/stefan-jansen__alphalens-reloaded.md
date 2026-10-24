# stefan-jansen/alphalens-reloaded

- URL: https://github.com/stefan-jansen/alphalens-reloaded
- Pinned commit: 1bc181de4aafbe33437ed0e362ff96aa7ce20acd (2026-10-17T14:17:37-04:00), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23 (no difference).
- Category: validation/metrics (cross-sectional factor and event study analysis; not a backtesting engine)
- Discovery channel: maintained successor of seed quantopian/alphalens (LONGLIST)
- Stars/forks (low weight, from search time): not recorded in LONGLIST / not recorded
- License (from LICENSE file text, not badge): Apache-2.0 (LICENSE, full Apache License 2.0 text; file headers "Copyright 2017 Quantopian, Inc." under Apache-2.0) ; transitive notes: empyrical-reloaded, statsmodels, seaborn, matplotlib, scipy, IPython, pytz, tzdata; no copyleft observed.
- Package: PyPI `alphalens-reloaded` 0.5.0 (py3-none-any; installed tree identical to the pinned source except generated _version.py) ; Python/OS: requires-python >=3.11,<3.16; CI ubuntu/windows/macos x 3.11-3.15 (.github/workflows/unit_tests.yml:16-21) ; native deps: none
- Maintenance: last commit 2026-10-17; CI unit_tests.yml, build_wheels.yml, test_wheels.yml, conda_package.yml; tests: 10 test files, 42 `def test_` (pytest, several parameterized), including intraday, sub-second and weekend-expiry workflow tests (tests/test_intraday_workflow.py, tests/test_subsecond_workflow.py, tests/test_position_expiry.py)
- Security surface: no network code in src/alphalens (no requests/urllib); tear sheets call `plt.show()` (9 call sites in tears.py); no order, wallet or key code.

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | NOT_SUPPORTED (single price frame) | one wide price frame, dates x assets (src/alphalens/utils.py:227-246) |
| tick/trade replay | NOT_SUPPORTED | none |
| CPMM math | NOT_SUPPORTED | none |
| CLMM/DLMM math | NOT_SUPPORTED | none |
| routes | NOT_SUPPORTED | none |
| fees/taxes | NOT_SUPPORTED | forward returns are gross |
| thin exits / size-dependent impact | NOT_SUPPORTED | none; missing prices are forward-filled (utils.py:309) |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED (implicit) | forward return at factor time t = `prices.ffill().pct_change(N).shift(-N)` (utils.py:309, :313): entry at the price stamped t; docstring tells the caller to pass prices that avoid lookahead (utils.py:757-759 in get_clean_factor_and_forward_returns) |
| point-in-time guard / no lookahead | NOT_SUPPORTED | default `filter_zscore=20` (utils.py:714) masks forward returns using full-sample mean/std (utils.py:315-319), which the docstring itself calls lookahead (utils.py:257, :816); no available_at concept |
| async event/catalyst injection | SOURCE_CODE_VERIFIED (bar-snapped) | event study tear sheet and event-window returns (src/alphalens/tears.py:620 create_event_study_tear_sheet, :514; performance.py:706 common_start_returns, :796 average_cumulative_return_by_quantile); events whose timestamps are not in the price index are dropped by `factor_dateindex.intersection(prices.index)` (utils.py:289) |
| wallets/on-chain | NOT_SUPPORTED | none |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED | per-date cross-sectional quantile/bin assignment, optional group neutralization (utils.py:91 quantize_factor; performance.py:141 factor_weights, :223 factor_returns, :382 positions) |
| walk-forward / holdout / multiple testing | SOURCE_CODE_VERIFIED (uncertainty only) | Spearman IC per date (performance.py:38-88, :67), IC t-test and p-value (plotting.py:204-220, :223), quantile mean returns with standard errors (performance.py:483-551), turnover and rank autocorrelation (performance.py:613, :658); no walk-forward, holdout or multiple-testing correction |
| metrics/report | SOURCE_CODE_VERIFIED | summary/returns/information/turnover/event tear sheets (tears.py:62-712) |
| live trading code present (must be avoidable) | NOT_SUPPORTED | none |

## Fill and chronology assumptions (read the code)

There are no orders. The implicit "fill" is the price row with the same timestamp as the factor value: `compute_forward_returns` forward-fills prices, takes `pct_change(N)` and shifts it back N rows onto the factor dates (utils.py:309-313). With close prices this is an entry at the close of the bar that produced the signal (smoke [1]); a next-bar-open entry requires the caller to pass open prices shifted by one bar (or to stamp the factor at available_at). Factor timestamps not present in the price index are silently intersected away (utils.py:289), subject only to the `max_loss=0.35` tolerance (utils.py:716, :695). The default z-score filter (utils.py:714, :315-319) uses each asset's full-sample forward-return mean and std, i.e. future data, and removes extreme outcomes. Because prices are forward-filled, an asset whose pool is drained (prices stop) shows 0% forward returns rather than a loss (smoke [3]). Trading calendar is inferred from observed weekdays (utils.py:182-224, called at :287), which handles 24/7 data but treats unobserved hours/days as holidays.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3 -m venv /home/claude/ext/venvs/stefan-jansen__alphalens-reloaded
/home/claude/ext/venvs/stefan-jansen__alphalens-reloaded/bin/pip install -q --prefer-binary alphalens-reloaded   # exit 0, alphalens-reloaded 0.5.0, statsmodels 0.15.0, pandas 3.1.0
cd audits/backtesting/research/smoke/stefan-jansen__alphalens-reloaded
/home/claude/ext/venvs/stefan-jansen__alphalens-reloaded/bin/python -I script.py > output.txt   # EXIT_CODE=0
```
Outcome: exit 0. 600 hourly bars x 5 tokens, random factor. [1] '1h' forward return for T0 at bar 10 equals close[11]/close[10]-1 (True): same-bar entry at the factor bar's price. [2] T1 with one +5,900% hour: default `filter_zscore=20` drops that row entirely ("ROW DROPPED"); with `filter_zscore=None` the forward return is 59.00. [3] T2 prices stop after bar 400 (pool drained): forward return at bar 400 is 0.0 and later rows stay in the analysis with 0% returns because prices are forward-filled.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 2.0 | 6.00 | cross-token cohort ranking fits memecoin research; intraday/sub-second tested; but ffill of dead tokens and equity-style defaults need overrides |
| B microstructure | 17 | 0.0 | 0.00 | no execution, costs or liquidity |
| C point-in-time | 15 | 1.5 | 4.50 | entry at factor-timestamp price unless caller shifts; default z-score filter is documented lookahead (utils.py:257, :714); no guards |
| D catalyst/on-chain events | 11 | 2.5 | 5.50 | event study tear sheet and event-window returns (tears.py:620, performance.py:706); events must be snapped to the price grid or are dropped (utils.py:289) |
| E TA/strategy flexibility | 9 | 1.0 | 1.80 | evaluates any factor/signal; no entry/exit rules |
| F statistical validation | 11 | 2.5 | 5.50 | IC with t-test/p-values, quantile spreads with std errors, turnover, group-neutral cohorts; no walk-forward/holdout/multiple testing |
| G integration fit | 9 | 3.5 | 6.30 | pure Python, MultiIndex Series in, DataFrames out; Py3.13 and Windows in CI; plt.show() in tear sheets |
| H maintenance/tests | 6 | 3.5 | 4.20 | commit 6 days before review, 3-OS x 5-Python CI; 42 test functions, modest coverage of a 4k-line package |
| I license/supply chain | 5 | 4.0 | 4.00 | Apache-2.0; moderate scientific deps, no network stack |
| J operational footprint | 2 | 4.0 | 1.60 | 544 MB venv, no services |
| Total | 100 | | 39.40 | |

Hard gates: none. Most important limitation for memecoins: forward returns forward-fill missing prices (utils.py:309), so a rugged or drained token scores 0% instead of a near-total loss, and the default z-score filter deletes the pumps; both bias a memecoin factor study toward looking safe and smooth. Single capability it would contribute: cross-sectional "does a score at t rank tokens' forward returns" analysis (per-date quantiles, Spearman IC with t-stats, event-window average returns) for social/catalyst scores, run with `filter_zscore=None`, prices pre-shifted to the executable time, and explicit NaN-to-loss handling for dead tokens. One credible negative finding: the default `filter_zscore=20` (utils.py:714) is documented as lookahead (utils.py:257) yet on by default; smoke [2] dropped a +5,900% hour from the analysis.
Disposition: REIMPLEMENT_IDEA (IC/quantile/event-window computations are compact and should be rebuilt with point-in-time inputs and rug-aware returns). Suggested use: REFERENCE.
