# pmorissette/bt

- URL: https://github.com/pmorissette/bt
- Pinned commit: 3adebef0316c5165ee0fb1fb27b2ec9866c30e3c (2026-10-20T17:08:22-04:00), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23 (no difference).
- Category: vectorized (portfolio tree of strategies/securities stepped date by date)
- Discovery channel: seed (LONGLIST)
- Stars/forks (low weight, from search time): not recorded in LONGLIST / not recorded
- License (from LICENSE file text, not badge): MIT ("The MIT License (MIT) Copyright (c) 2015 Philippe Morissette") ; transitive notes: ffn 1.4.1 (MIT per its metadata; pulls scikit-learn, scipy, matplotlib, tabulate), pyprind, tqdm; no copyleft in the installed tree.
- Package: PyPI `bt` 1.4.1, binary wheel cp313 manylinux (core.py compiled with Cython to core.cpython-313-x86_64-linux-gnu.so; the .py source ships alongside). The pinned HEAD still says version 1.4.1 in pyproject.toml but differs from the PyPI build (core.py 143 diff lines of refactoring, backtest.py cost-model hook refactor `_CostModelHook`); smoke ran the PyPI build ; Python/OS: requires-python >=3.9; cibuildwheel matrix ubuntu x86/arm, macos, windows x cp311-cp314 (.github/workflows/build.yaml:32-49) ; native deps: Cython-compiled extension (wheel provided, sdist needs a C toolchain)
- Maintenance: last commit 2026-10-20; CI files build.yaml, regression.yaml, docs.yaml; tests: tests/test_core.py, test_algos.py, test_backtest.py, 402 `def test_` (pytest, plus bench.py)
- Security surface: no install scripts run (wheel); compiled .so is built from the shipped core.py (auditable source, binary not independently rebuilt here); no network calls in bt/ (no requests/urllib/yfinance imports); no wallet, key or order-routing code.

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | NOT_SUPPORTED (close-only) | one price per security per date: `prc = self._prices_arr[inow]` (bt/core.py:1560); no open/high/low concept |
| tick/trade replay | SOURCE_CODE_VERIFIED (blotter only) | `ReplayTransactions` applies a dated (quantity, price) blotter falling in (previous bar, current bar] at its own prices (bt/algos.py:2530-2580); market data stays bar-based |
| CPMM math | NOT_SUPPORTED | none |
| CLMM/DLMM math | NOT_SUPPORTED | none |
| routes | NOT_SUPPORTED | none; `SimulateRFQTransactions` delegates fill/no-fill to a user model (bt/algos.py:2583) |
| fees/taxes | SOURCE_CODE_VERIFIED | `commissions=fn(q, p)` hook (bt/core.py:1821-1832); bid/offer spread frame charged as half-spread per unit (bt/core.py:1849-1856) |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED (cost only) | `SqrtCostModel` (2/3)*Y*sigma*\|q\|*sqrt(\|q\|/V)*p (bt/core.py:2345-2375) and `AlmgrenChrissCostModel` (bt/core.py:2378-2417) wired per security from same-date volume/volatility frames (bt/backtest.py:394-407); booked as a fee, fill price unchanged; returns 0 when V == 0 (core.py:2373, :2415); no participation cap |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | per date: `strategy.update(dt)` then `strategy.run()` then `update(dt)` (bt/backtest.py:474-481); trades book at the same date's price (`outlay = q * self._price`, bt/core.py:1856): same-bar fill at whatever price series is passed; next-bar open only by passing open prices with lagged signals (smoke [2]) |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED (partial) | `target.universe` is sliced to `[: now]` (bt/core.py:578); but `get_data` returns full additional-data frames unsliced (bt/core.py:720-728) and SelectWhere/WeighTarget read `signal.loc[target.now]` from those frames (bt/algos.py:767-777, :1176-1185); stat lags default to 0 days (bt/algos.py:18); SelectWhere docstring warns about restated data (bt/algos.py:728-733) |
| async event/catalyst injection | NOT_SUPPORTED (adaptable) | only via date-aligned `additional_data` frames or the blotter-replay pattern above |
| wallets/on-chain | NOT_SUPPORTED | none |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED | strategy/security node tree, weights, rebalancing, nested strategies (bt/core.py:386, :1263; bt/algos.py:1948 Rebalance, :1054-1408 Weigh*) |
| walk-forward / holdout / multiple testing | SOURCE_CODE_VERIFIED (baseline only) | `benchmark_random` runs N random-strategy controls on the same data, costs and capital (bt/backtest.py:42-120); no splitter, holdout or multiple-testing correction |
| metrics/report | SOURCE_CODE_VERIFIED | ffn GroupStats via `Result` (bt/backtest.py:624), transactions, weights, turnover |
| live trading code present (must be avoidable) | NOT_SUPPORTED | none |

## Fill and chronology assumptions (read the code)

`Backtest.run` (bt/backtest.py:440-488) prepends a synthetic NaN row one calendar day before the first date (`_process_data`, :409-438), then for each date updates every node to that date's price, runs the algo stack, and updates again. Allocations and `transact` book at `self._price`, the current date's value of the single price series supplied (bt/core.py:1560, :1856). With closes as input this is a same-bar close fill with zero latency (smoke [1]); there is no OHLC, no stop or limit order type, and no intrabar logic. Signals in `additional_data` are read by exact date lookup from the full frame, so any lag must be built into the frame by the caller. Costs: flat or callable commissions, a bid/offer frame, or (new) a CostModel that converts same-date volume and volatility into a cash fee; the price itself never moves with size, and V == 0 yields zero cost.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3 -m venv /home/claude/ext/venvs/pmorissette__bt
/home/claude/ext/venvs/pmorissette__bt/bin/pip install -q --prefer-binary bt   # exit 0, bt 1.4.1 cp313 wheel, ffn 1.4.1, pandas 3.1.0
cd audits/backtesting/research/smoke/pmorissette__bt
/home/claude/ext/venvs/pmorissette__bt/bin/python -I script.py > output.txt   # EXIT_CODE=0
```
Outcome: exit 0. [1] close series, signal true from bar 10: first transaction 2026-01-01 10:00 at 110.5 (SAME_BAR_CLOSE_FILL=True). [2] open series with signal shifted 1: 11:00 at 111.0 (NEXT_BAR_OPEN=True). [3] SqrtCostModel(Y=0.6), sigma 0.02: entry-bar volume 1000 gives qty 8,839.53 (8.8x the bar's volume, no cap) with fee 23,232.48; entry-bar volume 0 gives qty 9,049.77 with fee 0.00; fill price 110.5 in both.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 1.5 | 4.50 | generic price frames and fractional positions (integer_positions=False); daily-oriented scaffolding (t0-1 day row, Run* calendars); no DEX semantics |
| B microstructure | 17 | 2.0 | 6.80 | size-aware sqrt/Almgren-Chriss costs from volume/volatility (core.py:2345-2417), bid/offer frame, custom-price transactions; but cost-only, zero at V=0, no cap, single price per bar |
| C point-in-time | 15 | 2.0 | 6.00 | universe sliced to now (core.py:578) but additional data unsliced (core.py:728); same-bar fills; lag defaults 0 |
| D catalyst/on-chain events | 11 | 1.5 | 3.30 | date-aligned additional_data; blotter replay over (prev, now] windows is a usable causal join pattern |
| E TA/strategy flexibility | 9 | 2.5 | 4.50 | composable algos and custom Algo classes; no stops/limits/intrabar exits; allocation-centric |
| F statistical validation | 11 | 2.0 | 4.40 | random-strategy baseline (backtest.py:42); ffn stats; no walk-forward/holdout/multiple testing |
| G integration fit | 9 | 3.0 | 5.40 | cp313 wheels incl. Windows, small deps, pandas 3 OK; tree API and compiled core are harder to extend/debug |
| H maintenance/tests | 6 | 4.0 | 4.80 | commit 3 days before review; 402 tests, 4-platform x 4-Python wheel CI; PyPI build lags HEAD under the same version string |
| I license/supply chain | 5 | 4.0 | 4.00 | MIT; small dependency set; compiled extension from shipped source |
| J operational footprint | 2 | 4.0 | 1.60 | 463 MB venv (scikit-learn via ffn), no services |
| Total | 100 | | 45.30 | |

Hard gates: none. Most important limitation for memecoins: one price per security per bar and same-bar booking, with impact charged as a fee computed from bar volume; there is no notion of pool reserves, exit liquidity or a failed sell, and a zero-volume bar is free. One credible negative finding: both size-aware cost models return 0 when bar volume is 0 (bt/core.py:2373, :2415) and nothing caps participation; smoke [3] bought 9,050 units on a zero-volume bar at zero impact, the exact situation (dead pool, no exit liquidity) where memecoin losses happen.
Disposition: REIMPLEMENT_IDEA (MIT would allow excerpts, but the useful parts are small: blotter replay into a portfolio ledger at our own AMM fill prices, random-strategy baselines, sqrt-law cost with a participation cap and V=0 treated as no-fill). Suggested use: REFERENCE.
