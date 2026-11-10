# jesse-ai/jesse

- URL: https://github.com/jesse-ai/jesse
- Pinned commit: 9a3ebe075d9d0af5f012f921f46c2286f234af68 (2026-10-22T12:12:19+02:00), cloned 2026-10-23T15:52:44Z with `git clone --depth 1` (branch master, jesse/version.py 3.4.0). Matches LONGLIST head_sha_2026_10_23.
- Category: event-driven (1-minute candle simulator)
- Discovery channel: seed (LONGLIST, flagged "license check")
- Stars/forks (low weight, from search time): not recorded at search time
- License (from LICENSE file text, not badge): MIT ("Copyright (c) 2020 Jesse.Trade", 21 lines; setup.py:49 classifier agrees) ; transitive notes: the MIT grant covers this repo only. The live-trading plugin is a separate closed-source package downloaded from api2.jesse.trade with a LICENSE_API_TOKEN and pip-installed by `jesse install-live` (jesse/services/installer.py:11-12, 25-36, 72-84); the web dashboard ships as a 27 MB prebuilt minified Nuxt bundle (jesse/static/_nuxt, 489 files) whose source is not in this repo; MCP tool usage is metered against the jesse.trade license backend (jesse/mcp/usage_limits.py:20-30). jesse_rust 1.3.1 (compiled indicators) declares MIT with a public repo. Not needed for research backtests.
- Package: PyPI jesse 3.4.0 ; Python/OS: requirements pin numpy~=1.26.4 (requirements.txt:4), peewee~=3.14.8, blinker~=1.4 etc.; CI claims 3.10 to 3.13 but excludes Windows + 3.13 because ray has no cp313 Windows wheel (.github/workflows/python-package.yml:32-38) ; native deps: numpy, scipy, ray, jesse_rust, psycopg2-binary, cryptography, eth-account
- Maintenance: last commit 2026-10-22; CI files python-package.yml, codeql-analysis.yml, docker-publish.yml, native-coordination.yml; tests 82 test files (pytest)
- Security surface: outbound calls to api1/api2.jesse.trade for license, plugin download, help search, feedback and exception reports (jesse/info.py:5-12, services/general_info.py:26-77, services/jesse_trade.py:12-76 user-triggered, may attach backtest logs); downloads and pip-installs a binary plugin (installer.py:72-84); app mode needs PostgreSQL and Redis (services/db.py, services/redis.py); wallet-signing libraries (eth-account, starkbank-ecdsa) are installed as deps; research.backtest path makes no network calls (smoke ran with sockets blocked)

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | SOURCE_CODE_VERIFIED | 1m candles are the base input; higher timeframes are generated from completed 1m rows (jesse/modes/backtest_mode.py:1155-1245) |
| tick/trade replay | NOT_SUPPORTED | 1m candles are the finest unit; "observed timestamp replay" handles sparse 1m rows (backtest_mode.py:555-640) |
| CPMM math | NOT_SUPPORTED | none |
| CLMM/DLMM math | NOT_SUPPORTED | none |
| routes | NOT_SUPPORTED | none |
| fees/taxes | SOURCE_CODE_VERIFIED | flat fee_rate x notional per order (jesse/services/order_service.py:82-86); no transfer tax |
| thin exits / size-dependent impact | NOT_SUPPORTED | no slippage code anywhere (grep "slippage" in jesse/*.py returns nothing); orders always fill full qty (order_service.py:67-80) |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | strategy runs after its timeframe candle completes (backtest_mode.py:1250-1265); market orders are priced at position.current_price = last 1m close (services/broker.py:55-63, strategies/Strategy.py:676-677) and executed in the same step (backtest_mode.py:1268); smoke A |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED | candles are appended one minute at a time and higher timeframes only published when complete (backtest_mode.py:1157-1245); warmup candle handling (backtest_mode.py:508-540) |
| async event/catalyst injection | NOT_SUPPORTED | only extra candle routes (data_routes); no generic timestamped events |
| wallets/on-chain | NOT_SUPPORTED | none in the open repo (DEX live trading lives in the closed plugin) |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED | multiple routes/symbols per backtest (backtest_mode.py:1328-1405 _prepare_routes) |
| walk-forward / holdout / multiple testing | SOURCE_CODE_VERIFIED (partial) | optimize mode scores training and testing candle sets (modes/optimize_mode/Optimize.py:31-73); Monte Carlo on trades and candles (research/monte_carlo/); stationary-bootstrap rule significance test (research/rule_significance_testing/bootstrap.py:1-80, rule_significance.py:42-117); single split, no rolling walk-forward, no multiple-testing correction |
| metrics/report | SOURCE_CODE_VERIFIED | backtest_mode.py:1773-1798 _generate_outputs; metrics dict returned by research.backtest |
| live trading code present (must be avoidable) | SOURCE_CODE_VERIFIED | live mode requires the external plugin; avoidable by using jesse.research.backtest only |

## Fill and chronology assumptions (read the code)

Jesse walks 1-minute candles. For each minute it appends the candle, runs `_simulate_price_change_effect` to execute resting limit/stop orders inside that minute by splitting the candle at the order price (backtest_mode.py:1630-1700), and handles opening gaps by filling crossed resting orders at the first available open (backtest_mode.py:1456-1580). When a higher-timeframe candle completes, the strategy runs on that completed candle (no unfinished-bar visibility) and a market entry is submitted at the current price, which is that candle's close; `execute_simulated_market_orders` fills it in the same step (backtest_mode.py:1263-1268; smoke A: signal on hour 10, filled at 110.5 = hour 10 close). This is a zero-latency same-close fill, optimistic for fast-moving tokens but not lookahead. There is no slippage and no volume limit on any order. Stop losses are realistic on gaps (smoke B: stop 104.975, filled at the gapped open 100.0).

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3 -m venv /home/claude/ext/venvs/jesse-ai__jesse
pip install --only-binary :all: jesse            # backtracked through 178 versions, killed; dry run of jesse==3.4.0:
                                                 # "No matching distribution found for numpy~=1.26.4" (exit 1) on Python 3.13
python3.12 -m venv /home/claude/ext/venvs/jesse-ai__jesse-py312
pip install --only-binary :all: jesse==3.4.0     # exit 1: peewee~=3.14.8 has no wheel
pip install --prefer-binary jesse==3.4.0         # exit 0, 288 s (built peewee, simplejson, starkbank-ecdsa, timeloop from sdist)
cd <scratch cwd>; /home/claude/ext/venvs/jesse-ai__jesse-py312/bin/python -I .../smoke/jesse-ai__jesse/script.py
```
Outcome: Python 3.13 install FAILED (finding). On Python 3.12, exit 0 with sockets blocked: A: should_long on hour 10 -> market entry 110.5 (hour 10 close) executed at 11:00; liquidate on hour 20 -> 120.5 (hour 20 close). B: stop 104.975, hour 15 opens at 100 -> STOP filled at 100.0.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 1.0 | 3.00 | CEX symbols and 1m candles only; no AMM concepts |
| B microstructure | 17 | 1.5 | 5.10 | intrabar 1m order simulation and correct gap fills (smoke B); but no slippage, no size limits, flat fee |
| C point-in-time | 15 | 3.0 | 9.00 | completed-candle execution verified; same-close zero-latency market fills |
| D catalyst/on-chain events | 11 | 0.5 | 1.10 | no event injection |
| E TA/strategy flexibility | 9 | 3.5 | 6.30 | indicator library (jesse_rust), clear strategy API, multi-timeframe routes |
| F statistical validation | 11 | 3.0 | 6.60 | train/test optimize split, Monte Carlo, stationary bootstrap significance test |
| G integration fit | 9 | 0.5 | 0.90 | does not install on Python 3.13 (numpy pin); Windows + 3.13 excluded by its own CI; pins old peewee/blinker; app mode needs Postgres + Redis; ray dependency |
| H maintenance/tests | 6 | 4.0 | 4.80 | active, 82 test files, multi-OS CI |
| I license/supply chain | 5 | 3.5 | 3.50 | MIT core; closed plugin, prebuilt dashboard bundle, phone-home endpoints and wallet-signing deps raise supply-chain review cost |
| J operational footprint | 2 | 1.5 | 0.60 | research mode serviceless, but full install is heavy (ray, scipy, sklearn) and app mode needs Postgres + Redis |
| Total | 100 | | 40.90 | |

Hard gates: none for research use of jesse.research.backtest (the fill path is open Python); the closed live plugin and minified dashboard are outside scope and must never be installed. Most important limitation for memecoins: no slippage or liquidity model at all, so every size fills at the candle close, which is exactly where memecoin backtests lie. One credible negative finding: the package cannot be installed on Python 3.13 with wheels because requirements.txt:4 pins numpy~=1.26.4, contradicting the CI matrix entry for 3.13; on 3.12 it needs four sdist builds.
Disposition: REIMPLEMENT_IDEA. Suggested use: REFERENCE (reimplement the 1m intrabar order execution with opening-gap handling and the stationary-bootstrap significance test; do not install).
