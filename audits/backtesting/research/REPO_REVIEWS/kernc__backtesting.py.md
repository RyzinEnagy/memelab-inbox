# kernc/backtesting.py

- URL: https://github.com/kernc/backtesting.py
- Pinned commit: ca2e2611621e472542ba90f7243a1fa06a7d7108 (2026-08-05T14:39:16+02:00), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23 (no difference).
- Category: event-driven (bar-by-bar loop over vectorized precomputed indicators)
- Discovery channel: seed; GITHUB_API 'backtesting framework language:python stars:>200' (LONGLIST)
- Stars/forks (low weight, from search time): 9117 / not recorded
- License (from LICENSE file text, not badge): AGPL-3.0 (LICENSE.md: "GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007"; setup.py classifier says AGPLv3+) ; transitive notes: copyleft with network-use clause. Running the unmodified PyPI package locally for private research triggers no obligation; copying any of its code into memelab would put memelab under AGPL-3.0. Runtime deps only numpy, pandas, bokeh.
- Package: PyPI `backtesting` 0.6.6 (py3-none-any; differs from the pinned HEAD only in _util.py shared-memory sizing, a pdoc flag in __init__.py and tests) ; Python/OS: python_requires >=3.9, CI runs 3.11/3.12/3.13/3.* on Linux and 3.14 on windows-latest ; native deps: none
- Maintenance: last commit 2026-08-05 (release 0.6.6 on 2026-07-22 per CHANGELOG.md); CI .github/workflows/ci.yml (lint, coverage, build, prerelease deps, docs, win64, monthly schedule), deploy-docs.yml; tests: 1 test module backtesting/test/_test.py, 81 `def test_` (unittest)
- Security surface: no install scripts run (wheel); no network calls during `run()`; BUT `Backtest.plot()` injects a hidden 1x1 iframe into every generated HTML that loads `https://kernc.github.io/backtesting.py/plx.gif.html?utm_source=`+location.origin on DocumentReady (backtesting/_plotting.py:90-91, `_add_popcon`, called from `_bokeh_reset` at :87); present in the PyPI 0.6.6 build; not mentioned in README.md or CHANGELOG.md. Multiprocessing pool with shared memory in optimize (_util.py:312). No wallet/key/order-routing code.

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | SOURCE_CODE_VERIFIED | requires Open/High/Low/Close(/Volume) DataFrame, rejects NaN OHLC (backtesting.py:1236-1244) |
| tick/trade replay | NOT_SUPPORTED | one loop step per bar (backtesting.py:1340-1354) |
| CPMM math | NOT_SUPPORTED | none |
| CLMM/DLMM math | NOT_SUPPORTED | none |
| routes | NOT_SUPPORTED | none; only broker cancels for insufficient margin (backtesting.py:1005-1012) |
| fees/taxes | SOURCE_CODE_VERIFIED | commission = fixed + relative, or a callable(order_size, price) (backtesting.py:733-760); relative bounded to [-10%, 10%) (:742-744); charged at open and again at close (:1087-1093, :1102) |
| thin exits / size-dependent impact | NOT_SUPPORTED | `spread` is a constant fraction (backtesting.py:838-843); a callable commission can be size-dependent but does not move price or limit size; smoke [4] |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | default `trade_on_close=False` (backtesting.py:1203): market order placed in `next()` of bar t fills at Open[t+1] (:918-919, loop order :1349 then :1354); `trade_on_close=True` fills at Close[t] booked on bar t (:919, :925-928); contingent SL/TP never use trade_on_close (:917) |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED (partial) | `next()` sees data sliced to the current bar (_util.py:156-215 `_Data._set_length`; backtesting.py:1342-1346); indicators are computed once on the FULL series in `init()` (backtesting.py:144) and only revealed progressively, so a non-causal indicator function leaks silently; `resample_apply` uses right-labelled bins to avoid lookahead (lib.py:301, :328-329); tests for trade_on_close (backtesting/test/_test.py:1204) |
| async event/catalyst injection | NOT_SUPPORTED (adaptable) | extra DataFrame columns are revealed bar by bar like OHLC (_util.py:171-178), so a pre-aligned event column works; no timestamps beyond the bar index |
| wallets/on-chain | NOT_SUPPORTED | none |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED (limited) | one instrument per Backtest; `MultiBacktest` runs the same strategy on several frames separately (lib.py:568); no shared cash across instruments |
| walk-forward / holdout / multiple testing | NOT_SUPPORTED | `optimize()` grid or SAMBO search on the full sample (backtesting.py:1386-1393); `random_ohlc_data` for resampled paths (lib.py:338); no splitter, no holdout, no multiple-testing correction |
| metrics/report | SOURCE_CODE_VERIFIED | compute_stats (backtesting/_stats.py; annualization picks 365 when weekends are present, :121-130); Bokeh HTML plots |
| live trading code present (must be avoidable) | NOT_SUPPORTED | none |

## Fill and chronology assumptions (read the code)

Run loop (backtesting.py:1340-1354): for bar i, data and indicators are sliced to i+1 rows, then `broker.next()` processes queued orders against bar i's Open/High/Low, then `strategy.next()` runs with bar i fully visible (including its Close). A market order placed in `next()` at bar t therefore fills at Open[t+1] (default) or at Close[t] when `trade_on_close=True` (:918-919). Spread is applied as `price * (1 + spread)` for buys (:838-843), commission is fixed + relative or user callable. Stop/limit orders: a stop triggers when High>=stop (buy) or Low<=stop (sell) (:890); market-if-touched fill price is max/min(open, stop), so a gap through the stop fills at the open (:920-921, smoke [3] filled at 90 for a 105 SL). TP is a limit order filled at max/min(open, limit) (:901-914). SL orders are inserted at the front of the queue (:810-811), so a bar that spans both SL and TP closes at the SL (smoke [2]). After a market entry, SL/TP are re-processed in the same bar (:1029-1030); for stop/limit entries that would also hit SL/TP in the same bar, it warns and defers to the next bar (:1037-1047). Integer units only (`assert size == round(size)`, :980); prices above cash trigger a warning pointing to `FractionalBacktest` (:1246-1251, lib.py:509), which rescales data by 1e-8. Indicators are full-series arrays computed in `init()` (:144), so whether they see future bars depends on the function passed in.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3 -m venv /home/claude/ext/venvs/kernc__backtesting.py
/home/claude/ext/venvs/kernc__backtesting.py/bin/pip install -q --prefer-binary backtesting   # exit 0, backtesting 0.6.6, bokeh 3.10.1, pandas 3.1.0
cd audits/backtesting/research/smoke/kernc__backtesting.py
/home/claude/ext/venvs/kernc__backtesting.py/bin/python -I script.py > output.txt   # EXIT_CODE=0
```
Outcome: exit 0. [1] buy() on bar 10: default EntryBar=11 EntryPrice=111.0 (bar 11 open); trade_on_close=True EntryBar=10 EntryPrice=110.5 (bar 10 close). [2] SL=105 and TP=118 both inside bar 15 (O114 H125 L90 C95): exit at 105.0 (SL wins). [3] bar 15 opens at 90 below SL 105: exit at 90.0 (gap fill at open). [4] spread 1%: entry 112.11 for both 1 and 900 units (no size dependence). Plot not called, so the beacon did not fire.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 1.5 | 4.50 | any datetime index, 365-day annualization with weekends; single instrument, integer units unless FractionalBacktest; no DEX semantics |
| B microstructure | 17 | 1.5 | 5.10 | flat spread (:843), fixed/relative/callable commission, limit/stop orders, gap-aware stop fills; no depth, reserves or partial fills |
| C point-in-time | 15 | 3.0 | 9.00 | next-bar-open default verified (smoke [1]); progressive data reveal; right-labelled resample; but full-series indicator precompute (:144) has no causality guard and no available_at concept |
| D catalyst/on-chain events | 11 | 1.5 | 3.30 | extra columns revealed per bar; no async ingestion or known-at timestamps |
| E TA/strategy flexibility | 9 | 4.0 | 7.20 | arbitrary Python in next(), SL/TP/limit/stop, TrailingStrategy/SignalStrategy (lib.py:375, :447), crossover, resample_apply |
| F statistical validation | 11 | 1.5 | 3.30 | in-sample grid/SAMBO optimize only; random OHLC paths; no walk-forward, holdout or multiple-testing |
| G integration fit | 9 | 3.0 | 5.40 | 3 runtime deps, Py3.13 OK, Windows CI; single-asset API and integer units need wrapping for memecoin prices |
| H maintenance/tests | 6 | 4.0 | 4.80 | 2026 release, lint+coverage+Windows CI, 81 tests incl. trade_on_close; suite not run here |
| I license/supply chain | 5 | 1.5 | 1.50 | AGPL-3.0 (no vendoring); undisclosed third-party beacon in plot HTML (_plotting.py:90-91); deps minimal |
| J operational footprint | 2 | 4.5 | 1.80 | 239 MB venv, pure Python, no services |
| Total | 100 | | 45.90 | |

Hard gates: none for running the unmodified package locally (research oracle use); AGPL-3.0 is a gate for any VENDOR/copy into memelab; plot() beacon is a disclosed-here security concern, avoided by never calling `Backtest.plot()` or by viewing plots offline. Most important limitation for memecoins: one OHLC series per instrument with a constant-fraction spread, so pool reserves, size-dependent impact, transfer fees, failed routes and thin exits cannot be expressed; integer-unit sizing also breaks at sub-cent token prices without FractionalBacktest. One credible negative finding: `Backtest.plot()` silently embeds a hidden iframe that phones `kernc.github.io` with the page origin (backtesting/_plotting.py:90-91), undocumented in README/CHANGELOG and shipped in PyPI 0.6.6.
Disposition: REFERENCE (clean next-bar-open and SL/TP-priority semantics worth mirroring; can serve as an unmodified, pip-installed independent oracle for OHLC-level golden scenarios). Suggested use: REFERENCE.
