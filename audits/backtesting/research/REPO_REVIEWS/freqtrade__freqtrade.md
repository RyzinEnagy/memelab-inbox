# freqtrade/freqtrade

- URL: https://github.com/freqtrade/freqtrade
- Pinned commit: c051e9065c5b677f03817dd1f83cb980af1ed684 (2026-10-22T07:26:11+02:00), cloned 2026-10-23T15:52:38Z with `git clone --depth 1` (branch develop, version 2026.10-dev). Matches LONGLIST head_sha_2026_10_23.
- Category: event-driven (vectorized signal generation, per-candle loop for orders)
- Discovery channel: seed (LONGLIST)
- Stars/forks (low weight, from search time): not recorded at search time
- License (from LICENSE file text, not badge): GPL-3.0 (674-line GNU GPL v3 text) ; transitive notes: ccxt (MIT), TA-Lib python wrapper (BSD), python-telegram-bot (LGPL-3.0), fastapi (MIT); GPL copyleft applies to any vendored excerpt
- Package: PyPI freqtrade 2026.9 (HEAD is 2026.10-dev; the two functions exercised in the smoke test are byte-identical between wheel and pinned source) ; Python/OS: CI matrix python 3.12/3.13/3.14 on ubuntu, macOS and windows-2022/2025 (.github/workflows/ci.yml:24-28) ; native deps: TA-Lib, numpy, pandas, pyarrow, scipy wheels (cp313 available); sdnotify is sdist-only (pyproject.toml:73)
- Maintenance: last commit 2026-10-22; CI files ci.yml, docker-build.yml, zizmor_action.yml and 6 more; tests 104 test files (pytest)
- Security surface: full live trading bot (exchange API keys via ccxt), Telegram bot, REST API server (fastapi/uvicorn), setup.sh/setup.ps1 (not run); Backtesting() instantiates a ccxt exchange and loads markets over the network at startup (freqtrade/optimize/backtesting.py:170, freqtrade/exchange/exchange.py:328-330); no wallet or key code needed for backtesting (dry_run forced at backtesting.py:152)

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | SOURCE_CODE_VERIFIED | backtesting.py:518-572 converts analyzed dataframes to row lists (date, open, high, low, close, signals) |
| tick/trade replay | NOT_SUPPORTED | trades are only converted to candles (freqtrade/data/converter/trade_converter.py); backtest loop consumes candles (backtesting.py:1523-1583); `--timeframe-detail` uses smaller candles, not ticks |
| CPMM math | NOT_SUPPORTED | none |
| CLMM/DLMM math | NOT_SUPPORTED | none |
| routes | NOT_SUPPORTED | none |
| fees/taxes | SOURCE_CODE_VERIFIED | single fee rate: config `fee` or worst-case exchange taker/maker fee (backtesting.py:268-281); no transfer tax |
| thin exits / size-dependent impact | NOT_SUPPORTED | fills use row[OPEN_IDX] or stop/ROI price with no slippage and no volume cap (backtesting.py:574-595, 1126-1170); a fixed 0.05% "slippage" exists only inside two hyperopt loss functions (hyperopt_loss/hyperopt_loss_sharpe_daily.py:38) |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | entry/exit signal columns shifted by 1 and first row dropped (backtesting.py:552-567); entries priced at row[OPEN_IDX] of the next candle (backtesting.py:1152-1166); smoke case A |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED (detect-only) | shift(1) above; `lookahead-analysis` and `recursive-analysis` commands (freqtrade/optimize/analysis/lookahead.py:34-203, recursive.py) compare full vs truncated runs; user indicator code still runs vectorized over the whole history (strategy/interface.py:1200) so lookahead is possible and only detected after the fact |
| async event/catalyst injection | NOT_SUPPORTED | only dataframe merges; merge_informative_pair aligns other timeframes (strategy/strategy_helper.py:117); no timestamped event stream |
| wallets/on-chain | NOT_SUPPORTED | none |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED | multi-pair loop with max_open_trades, stake sizing, wallets (backtesting.py:1306-1313, freqtrade/wallets.py) |
| walk-forward / holdout / multiple testing | SOURCE_CODE_VERIFIED (partial) | hyperopt over one timerange (no holdout); FreqAI sliding train/backtest windows (freqai/data_kitchen.py:316-346) are walk-forward for ML models only; no multiple-testing correction |
| metrics/report | SOURCE_CODE_VERIFIED | freqtrade/optimize/optimize_reports/ (Sharpe, Sortino, Calmar, drawdown, per-pair tables) |
| live trading code present (must be avoidable) | SOURCE_CODE_VERIFIED | freqtrade/freqtradebot.py, rpc/telegram, rpc/api_server; avoidable (backtesting forces dry_run, backtesting.py:152) |

## Fill and chronology assumptions (read the code)

All indicators and entry/exit signals are computed once over the full dataframe (strategy/interface.py:1200, backtesting.py:539). The engine then shifts every signal column by one candle and drops the first row (backtesting.py:552-567), so a signal computed on candle k's close is acted on in the row of candle k+1 and priced at candle k+1 open (backtesting.py:1152-1166, smoke A: entry 111.0 = bar 11 open, exit 121.0 = bar 21 open). No slippage and no volume limit are applied; limit orders fill if low <= rate <= high (backtesting.py:791-793). Stop losses: if the stop is above the candle high the exit is at open, otherwise the exit is exactly the stop price (backtesting.py:612-616, 649). When a candle opens below the stop but trades back above it, the exit is booked at the stop, not at the gapped open (smoke B: open 100, stop 105.45, booked 105.45). Same-candle trailing stops use a pessimistic path (backtesting.py:618-644). Indicators can see the full candle k but not k+1 unless user code uses negative shifts or centered windows, which only the separate lookahead-analysis command detects.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3 -m venv /home/claude/ext/venvs/freqtrade__freqtrade
pip install --only-binary :all: freqtrade      # exit 1, ResolutionImpossible: sdnotify has no wheel
pip install --prefer-binary freqtrade          # exit 0, 112 s, freqtrade 2026.9 (only sdnotify built from sdist)
cd audits/backtesting/research/smoke/freqtrade__freqtrade
/home/claude/ext/venvs/freqtrade__freqtrade/bin/python -I script.py > output.txt 2>&1
```
Outcome: exit 0, with socket.connect blocked and the exchange object mocked the way freqtrade's own tests do (tests/conftest.py:220-271), because Backtesting() otherwise needs network access to load CEX markets (no credentials needed). A: enter_long on bar 10 -> entry 111.0 at bar 11 open; exit_long on bar 20 -> 121.0 at bar 21 open. B: stop at 105.45, bar 15 opens 100 (gap) with high 108 -> exit booked at 105.45 (optimistic by 5.45%).

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 1.0 | 3.00 | CEX/ccxt-bound; needs exchange markets to start; no AMM or Solana concepts |
| B microstructure | 17 | 1.0 | 3.40 | no slippage, no size limits, flat fee; optimistic gap stops (smoke B) |
| C point-in-time | 15 | 3.0 | 9.00 | verified shift(1) + next-open entries (smoke A); lookahead only detected post hoc |
| D catalyst/on-chain events | 11 | 1.0 | 2.20 | dataframe merges only, informative-pair alignment helper |
| E TA/strategy flexibility | 9 | 4.0 | 7.20 | TA-Lib, pandas-ta, technical; callbacks for custom stops/prices/position adjustment |
| F statistical validation | 11 | 2.0 | 4.40 | hyperopt + reports + lookahead/recursive analysis; FreqAI sliding windows; no holdout or multiple-testing control |
| G integration fit | 9 | 1.5 | 2.70 | installs on py3.13 (sdist for sdnotify), Windows CI; but a whole bot framework with its own CLI, config, data dir and ccxt exchange dependency; offline backtest needs mocking |
| H maintenance/tests | 6 | 5.0 | 6.00 | daily commits, 104 test files, broad OS/Python CI |
| I license/supply chain | 5 | 2.0 | 2.00 | GPL-3.0 copyleft; large dependency tree incl. telegram and web server |
| J operational footprint | 2 | 3.0 | 1.20 | no always-on services for backtest (sqlite in memory), but heavy install |
| Total | 100 | | 41.10 | |

Hard gates: none (GPL-3.0 is acceptable for an internal pip-installed research tool; it blocks vendoring code into memelab). Most important limitation for memecoins: fills assume unlimited liquidity at candle open with zero slippage on a CEX market list, so thin-pool exits and size-dependent AMM impact are invisible. One credible negative finding: gap-down stops are booked at the stop price instead of the gapped open whenever the candle high recovers above the stop (backtesting.py:615-616, 649; smoke B), which systematically flatters stop-loss strategies on gappy tokens.
Disposition: REFERENCE. Suggested use: REFERENCE (borrow the signal shift(1) convention and the lookahead/recursive analysis idea; do not install as the lab's engine).
