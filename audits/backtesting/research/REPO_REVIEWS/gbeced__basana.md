# gbeced/basana

- URL: https://github.com/gbeced/basana
- Pinned commit: 0c65f58ba8562f4507b3055b3583b66e4934dff3 (2026-10-23T11:20:16-03:00), cloned 2026-10-23T15:52:36Z with `git clone --depth 1` (branch develop). Matches LONGLIST head_sha_2026_10_23.
- Category: event-driven
- Discovery channel: GITHUB_API search 'backtesting framework ... stars:>200'
- Stars/forks (low weight, from search time): 871/not recorded
- License (from LICENSE file text, not badge): Apache-2.0 (LICENSE is the 16-line Apache 2.0 notice form, "Copyright 2022 Gabriel Martin Becedillas Ruiz"; GitHub reported NOASSERTION only because the full license text is not in the file; pyproject.toml also says `license = "Apache-2.0"`) ; transitive notes: runtime deps aiohttp (Apache-2.0), python-dateutil (Apache/BSD); optional plotly, kaleido, ccxt (MIT)
- Package: PyPI basana 1.11 (same version as HEAD pyproject) ; Python/OS: requires-python >=3.10,<4, CI on 3.10 to 3.14 x windows/ubuntu/macos ; native deps: none (pure Python wheel; aiohttp speedups wheels)
- Maintenance: last commit 2026-10-23; CI files .github/workflows/runtests.yml (matrix python 3.10 to 3.14, windows/ubuntu/macos, runtests.yml:28-29); tests 57 test files (pytest, pytest-asyncio)
- Security surface: no install scripts (uv build backend); live exchange clients for Binance and Bitstamp (basana/external/binance, basana/external/bitstamp) need API keys only if used; backtesting path makes no network calls; no wallet code, no binaries, no obfuscation

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | SOURCE_CODE_VERIFIED | basana/core/bar.py:85-93 BarEvent; basana/external/common/csv/bars.py:32-50 CSV rows become BarEvent stamped at dt + bar duration (bar close) |
| tick/trade replay | NOT_SUPPORTED | backtesting Exchange only accepts BarEvent (basana/backtesting/exchange.py:438-447 asserts bar.BarEvent); trade-to-bar builder exists only for realtime (basana/core/bar.py:100-170) |
| CPMM math | NOT_SUPPORTED | no x*y=k anywhere; only pluggable LiquidityStrategy interface basana/backtesting/liquidity.py:24-65 (take_liquidity / calculate_price_impact / calculate_amount) where a CPMM curve could be plugged |
| CLMM/DLMM math | NOT_SUPPORTED | none |
| routes | NOT_SUPPORTED | single pair per order; no multi-hop |
| fees/taxes | SOURCE_CODE_VERIFIED | basana/backtesting/fees.py:50-93 NoFee and Percentage (with min_fee, quote or base currency); no transfer-tax model |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED | basana/backtesting/liquidity.py:96-171 VolumeShareImpact: quadratic impact (used/total)^2 x max impact, cap 25% of bar volume; market orders that exceed available liquidity are not partially filled and are canceled (orders.py:257-262, order_mgr.py:254-264); stop orders wait (orders.py:355-363) |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | default: order processed on the next BarEvent at bar.open (exchange.py:438-447 processes orders before forwarding the bar; orders.py:264); option immediate_order_processing=True fills at last close (order_mgr.py:111-131); no latency model |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED (partial) | dispatcher asserts monotone event time (core/dispatcher/backtesting.py:55-74); bar events at close; but see backdated async fill below |
| async event/catalyst injection | SOURCE_CODE_VERIFIED | any Event(when) source is time-multiplexed with bars (core/event.py:54-77, core/dispatcher/backtesting.py:91-104); smoke case C |
| wallets/on-chain | NOT_SUPPORTED | none |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED | multi-pair balances with holds and margin loans (backtesting/account_balances.py, loan_mgr.py, order_mgr.py:163-186) |
| walk-forward / holdout / multiple testing | NOT_SUPPORTED | no statistics module (grep for sharpe/drawdown/walk-forward returns nothing in basana/) |
| metrics/report | DEMO_ONLY | plotly charts only (backtesting/charts.py); no performance metrics |
| live trading code present (must be avoidable) | SOURCE_CODE_VERIFIED | basana/external/binance, basana/external/bitstamp, core/dispatcher/realtime.py; avoidable by importing only basana.backtesting |

## Fill and chronology assumptions (read the code)

Bars are BarEvents stamped at bar close (csv/bars.py:46-50). When a BarEvent arrives, the exchange first updates prices and processes all open orders against that bar (exchange.py:440-442, order_mgr.py:87-91), and only then forwards the bar to strategy handlers (exchange.py:445-447). A market order created in the handler for bar k therefore fills on bar k+1 at bar k+1 open plus VolumeShareImpact slippage (orders.py:257-275, slipped_price orders.py:565-581). Indicators only see completed bars. Limit orders fill at open if already crossed, else at the limit (orders.py:287-316); stop orders fill at open on a gap, else at the stop, then slipped (orders.py:359-390). Partial fills exist for limit and stop-limit orders, not for market or stop orders. Two chronology defects: (1) an order placed by a non-bar event at time t inside bar j (open_j < t < close_j) is processed when bar j's event arrives and fills at open_j, a price from before the decision (smoke case C); (2) the liquidity cap and impact use the full volume of the execution bar (liquidity.py:114-116), which is not known at that bar's open. Strategy handler exceptions are logged and swallowed by default (core/dispatcher/base.py:127, 288-297), so a broken strategy still exits 0.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3 -m venv /home/claude/ext/venvs/gbeced__basana
/home/claude/ext/venvs/gbeced__basana/bin/pip install --only-binary :all: basana   # exit 0, 21 s, basana 1.11
cd audits/backtesting/research/smoke/gbeced__basana
/home/claude/ext/venvs/gbeced__basana/bin/python -I script.py > output.txt 2>&1
```
Outcome: exit 0. A (default): order placed in bar 10 close handler filled at 111.0000 = bar 11 open (next-bar). B (immediate_order_processing=True): filled at 110.5000 = bar 10 close (same bar). C (catalyst event at 20:30, inside bar 20 which opened 20:00): filled at 120.0000 = bar 20 open, 30 minutes before the decision (backdated fill). D (VolumeShareImpact, 50k of 250k cap): 111.4440 = 111 x (1 + 0.2^2 x 10%). E: handler exception swallowed, 25 more bars processed, exit 0.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 1.5 | 4.50 | CEX bar model; no AMM math; but LiquidityStrategy plug point (liquidity.py:24-65) can host a pool curve |
| B microstructure | 17 | 2.5 | 8.50 | quadratic volume-share impact, per-bar volume cap, unfilled market orders canceled, limit/stop/stop-limit, % fees; no depth, routes, transfer taxes |
| C point-in-time | 15 | 2.5 | 7.50 | close-stamped bars, next-open default, monotone dispatcher; backdated fills for mid-bar async events (smoke C), same-bar volume used for impact |
| D catalyst/on-chain events | 11 | 2.5 | 5.50 | generic time-multiplexed event sources verified (smoke C); no on-chain/social adapters |
| E TA/strategy flexibility | 9 | 3.0 | 5.40 | free-form async Python strategies; no indicator library (samples use talipp) |
| F statistical validation | 11 | 0.5 | 1.10 | nothing beyond charts |
| G integration fit | 9 | 4.0 | 7.20 | pure Python, 2 runtime deps, py3.13 wheel installed in 21 s, Windows CI; asyncio + Decimal API differs from lab's pandas style |
| H maintenance/tests | 6 | 4.0 | 4.80 | commit same day, 57 test files, 15-cell CI matrix; single maintainer |
| I license/supply chain | 5 | 4.5 | 4.50 | Apache-2.0 notice form (not full text), tiny dependency tree |
| J operational footprint | 2 | 5.0 | 2.00 | no services, small install |
| Total | 100 | | 51.00 | |

Hard gates: none. Most important limitation for memecoins: liquidity is modelled as a share of bar volume, not as pool reserves, so impact on a thin PumpSwap/Raydium pool is unrelated to actual depth and there is no route, transfer-fee or failed-swap model. One credible negative finding: an order triggered by an asynchronous event in the middle of a bar fills at that bar's open, i.e. before the event (smoke case C, order_mgr.py:87-91 + orders.py:264); this silently rewards catalyst strategies.
Disposition: REIMPLEMENT_IDEA. Suggested use: REFERENCE (copy the idea of a pluggable LiquidityStrategy with take_liquidity/calculate_amount and the close-stamped event mux; do not use its fill timing for async events without a fix).
