# tradingstrategy-ai/trade-executor

- URL: https://github.com/tradingstrategy-ai/trade-executor
- Pinned commit: 34fc7eb0b6594d21acc2fc88ab230a95794779f7 (2026-10-14T22:59:04+02:00), cloned 2026-10-23T15:53:12Z with `git clone --depth 1` (submodules not fetched). Matches LONGLIST head_sha_2026_10_23.
- Category: crypto/DEX/Solana (EVM DEX backtest and live execution framework)
- Discovery channel: citation from tradingstrategy-ai/getting-started (GITHUB_API "solana backtest")
- Stars/forks (low weight, from search time): not recorded (citation entry; GitHub API not reachable from this review session)
- License (from LICENSE file text, not badge): AGPL-3.0-or-later (LICENSE.txt: "GNU Affero General Public License ... version 3 ... or (at your option) any later version", Copyright (C) 2022 Market Software Ltd.); pyproject says `license = "APGL"` (typo) ; transitive notes: path dependency trading-strategy is AGPL (PyPI metadata), web3-ethereum-defi submodule, git-pinned fork `lighter-sdk` (sui294801854/lighter-python rev 253fd8f0) that ships a native signer
- Package: PyPI `trade-executor` 0.3 (last upload 2023-04-29, Requires-Python >=3.10,<3.11), repo is 0.3.2 via Poetry ; Python/OS: repo requires >=3.11,<3.15; CI on Linux Python 3.14 ; native deps: lighter-sdk signer, lxml (libxml2-dev), kaleido, duckdb; 304 packages in poetry.lock
- Maintenance: last commit 2026-10-14; CI files .github/workflows/test.yml (Python 3.14, recursive submodules, paid "Beefy runners" group), test-slow.yml, docker.yml, notebook-docker-image.yml, devcontainer.yml; tests 362 test files (pytest), many need the Trading Strategy API (`persistent_test_client`) or an Anvil mainnet fork
- Security surface: hot-wallet private keys via CLI options/env (tradeexecutor/cli/commands/start.py:138-139,156), Enzyme/Lagoon vault deploy commands, web server (pyramid), Discord/Telegram loggers, git dependencies; eth_defi imported in the backtest path (tradeexecutor/backtest/backtest_execution.py:10)

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | SOURCE_CODE_VERIFIED | BacktestPricing on GroupedCandleUniverse, default `candle_timepoint_kind="open"`: tradeexecutor/backtest/backtest_pricing.py:57-76, 320-326 |
| tick/trade replay | NOT_SUPPORTED | No tick lane in tradeexecutor/backtest/ |
| CPMM math | NOT_SUPPORTED (backtest) | x*y=k quoting exists only in live/test helpers through eth_defi (tradeexecutor/testing/ethereumtrader_uniswap_v3.py:57) |
| CLMM/DLMM math | UNKNOWN | Uniswap v3 LP adapter tradeexecutor/strategy/demeter/adapter.py:68 depends on zelos-demeter, marked optional and "TODO: Disabled" in pyproject; not exercised |
| routes | SOURCE_CODE_VERIFIED | Three-leg fee resolution through intermediary pairs: backtest_pricing.py:483-495; tradeexecutor/backtest/backtest_routing.py |
| fees/taxes | SOURCE_CODE_VERIFIED | Pair fee tier + intermediary leg fee + buy/sell token tax: backtest_pricing.py:463-530; tests/backtest/test_token_tax.py:134 |
| thin exits / size-dependent impact | NOT_SUPPORTED (pricing) | "# TODO: Include price impact" at backtest_pricing.py:305 and :379; price = mid x (1 -/+ fee) (:340 sell, :415 buy); TVL caps position size only: tradeexecutor/strategy/alpha_model.py:1443,1905-1964, tests/backtest/test_backtest_tvl_trade_size_by_liquidity.py:171; UncappedTradeSizer sell sizing raises NotImplementedError (backtest_price_impact.py:51-58) |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | Decisions read the previous bar: strategy_input.py:144-158 (docstring), :471 `shifted_ts = ts + time_frame*index` with index=-1; trades priced at the open of the candle stamped at the decision timestamp: backtest_pricing.py:76,320-326. No latency model |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED (partial) | Shift by one bar as above; ffill fallback keyed on `self.timestamp` at strategy_input.py:493 (see negative finding); maintainers document a past lookahead bug of this class at :1073-1081; tests/backtest/test_forward_fill.py:19-224 |
| async event/catalyst injection | NOT_SUPPORTED | Only alternative candle feeds (tradeexecutor/strategy/pandas_trader/alternative_market_data.py:136-401) and vault events |
| wallets/on-chain | SOURCE_CODE_VERIFIED (live only) | Hot wallet and vault execution under tradeexecutor/ethereum/, cli/commands/ |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED | Multi-pair alpha model with weights and TVL risk: tradeexecutor/strategy/alpha_model.py; tests/test_multipair.py |
| walk-forward / holdout / multiple testing | NOT_SUPPORTED | Grid search and scikit-optimize optimiser only (tradeexecutor/backtest/grid_search.py, optimiser.py); grep finds no walk-forward, holdout or deflated Sharpe |
| metrics/report | SOURCE_CODE_VERIFIED | quantstats tearsheet tradeexecutor/backtest/tearsheet.py, tradeexecutor/statistics/, tradeexecutor/analysis/ |
| live trading code present (must be avoidable) | SOURCE_CODE_VERIFIED | Live CLI and private keys: tradeexecutor/cli/commands/start.py:138-139,156,382; same package as the backtester |

## Fill and chronology assumptions (read the code)

A strategy cycle at timestamp T reads indicators and prices at T minus one bar (strategy_input.py:144-158, :471). Trades decided at T are priced at the open of the candle stamped T (backtest_pricing.py:76, 320-326), so a signal on bar k close fills at bar k+1 open; buys pay mid x (1 + fee) and sells receive mid x (1 - fee), where fee = pair fee tier + intermediary leg fee + token tax (backtest_pricing.py:340, 415, 463-530). There is no size-dependent impact (TODO at :305 and :379); size realism comes only from optional TVL-based position caps in the alpha model. Missing candles are forward-filled up to `data_delay_tolerance=2d` (:75), so a pair with no trades is priced at a stale mid. Stop-losses are checked on the mid price of the trigger-granularity candle, not the bar low, and when no price exists the code assumes "price has not moved" (tradeexecutor/strategy/stop_loss.py:134-138). Indicators are precomputed over the full series and must themselves be causal; the per-cycle accessor applies the one-bar shift.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3.13 -m venv /home/claude/ext/venvs/tradingstrategy-ai__trade-executor
python3 -I audits/backtesting/research/smoke/tradingstrategy-ai__trade-executor/script.py /home/claude/ext/venvs/tradingstrategy-ai__trade-executor/bin/python
# runs: pip install --only-binary :all: trade-executor ; and trade-executor==0.3
```
Outcome: exit 1, install failed. pip: "Ignored the following versions that require a different python version: 0.1.0 ... 0.3 Requires-Python >=3.10,<3.11"; "No matching distribution found". Building the repo (Poetry, recursive submodules, git-pinned native signer fork) was not attempted because the brief forbids running those builds. The fill-timing test was therefore not executed; timing above is from code. Output in smoke/tradingstrategy-ai__trade-executor/output.txt.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 2.5 | 7.50 | DEX-native pair model with fee tiers, token tax, TVL; EVM only, zero Solana code |
| B microstructure | 17 | 1.5 | 5.10 | Candle open +/- flat fee and tax; price impact is a TODO; TVL caps sizing only; stale ffill prices |
| C point-in-time | 15 | 2.5 | 7.50 | One-bar shift and next-open fills, but ffill fallback can read the current bar on gaps; no lookahead test for it |
| D catalyst/on-chain events | 11 | 1.0 | 2.20 | Alternative candle feeds and vault events only |
| E TA/strategy flexibility | 9 | 4.0 | 7.20 | Python decide_trades, pandas_ta indicators, position manager, stops/TP/trailing, multi-pair alpha model |
| F statistical validation | 11 | 1.5 | 3.30 | Grid search, optimiser, benchmarks and quantstats; no walk-forward, holdout or multiple-testing correction |
| G integration fit | 9 | 0.5 | 0.90 | Not installable on 3.13 from PyPI; Poetry + submodules + native fork; web3 in the backtest import path; AGPL |
| H maintenance/tests | 6 | 4.0 | 4.80 | Active, 362 test files, CI on 3.14; many tests need API key or chain fork |
| I license/supply chain | 5 | 1.0 | 1.00 | AGPL-3.0 (network copyleft) here and in trading-strategy; git fork dependency |
| J operational footprint | 2 | 0.5 | 0.20 | 304 locked packages incl. Jupyter, web3, pyramid, kaleido |
| Total | 100 | | 39.70 | |

Hard gates: incompatible license for import or vendoring (AGPL-3.0); RESEARCH_ONLY. Most important limitation for memecoins: backtest fills are candle mid plus a flat fee with no size-dependent impact, so thin exits, launch liquidity and rugs cannot hurt a simulated position; and there is no Solana support. One credible negative finding: with the default `data_delay_tolerance="auto"`, when the previous bar is missing (normal for thin DEX pairs with no trades in a bar), `get_indicator_value` forward-fills from `self.timestamp` (strategy_input.py:493) and can return the row stamped at the current bar's open, whose value includes that unfinished bar's close; the maintainers' own comment at :1073-1081 describes a past lookahead bug that reached exactly this fallback. This is a code-reading inference; it was not executed here.
Disposition: REFERENCE. Suggested use: REFERENCE.
