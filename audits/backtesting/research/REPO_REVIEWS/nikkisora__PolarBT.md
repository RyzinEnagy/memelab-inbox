# nikkisora/PolarBT

- URL: https://github.com/nikkisora/PolarBT
- Pinned commit: 18f9363a0d131bb5f3a7fb266f7a071b07b0a727 (2026-03-14T18:04:24+03:00), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23 (no difference).
- Category: vectorized preprocessing plus event-driven bar loop (Polars), with DEX trade-to-bar helpers
- Discovery channel: GITHUB_API search "memecoin backtest"; Firecrawl developer search (per LONGLIST)
- Stars/forks (low weight, from search time): 13/n.a.
- License (from LICENSE file text, not badge): MIT (Copyright (c) 2024 PolarBtest Contributors) ; transitive notes: runtime deps only polars>=0.19.0 and numpy>=1.24.0 (unpinned lower bounds, pyproject.toml:24-27); optional plotly, TA-Lib.
- Package: PyPI `polarbt` (pyproject version 0.2.1; publish workflow auto-bumps on every push) ; Python/OS: requires-python >=3.10, classifiers up to 3.12; ran on 3.13 with polars 2.0.0 in the smoke test ; native deps: none (polars wheels).
- Maintenance: last commit 2026-03-14 (7 months before review); CI files `.github/workflows/publish.yml` only (bumps version, commits, publishes to PyPI on push to main; no test job); tests: 40 pytest files, 909 test functions (not run here).
- Security surface: no network, subprocess, eval or pickle in the package (grep of polarbt/ found only a URL string in an ImportError message, polarbt/integrations/talib.py:53); multiprocessing used by optimizer/permutation workers (runner.py, analysis.py); `agents.md` holds contributor instructions for AI agents (ignored). No wallet or live trading code.

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | SOURCE_CODE_VERIFIED | Engine loop per timestamp over long-format bars (polarbt/core.py:2818-2911) |
| tick/trade replay | NOT_SUPPORTED (aggregation only) | trades are only aggregated to time or trade-count bars (polarbt/data/trades.py:78-146, 149-212); fills never see individual trades |
| CPMM math | SOURCE_CODE_VERIFIED (incorrect for buys) | `AMMSlippage`: rate = trade_value/(reserve+trade_value) applied symmetrically (polarbt/slippage.py:82-126). Exact for sells; understates buys (smoke [3]: 1.5x vs x*y=k 2.0x when trade value equals reserve); test locks in the wrong value (tests/test_slippage_and_exchange.py:137-142); no fee inside the curve, no virtual reserves, reserves never updated |
| CLMM/DLMM math | NOT_SUPPORTED | none |
| routes | NOT_SUPPORTED | none |
| fees/taxes | SOURCE_CODE_VERIFIED (flat) | percent, fixed+percent, maker/taker, tiered, custom commission models (polarbt/commissions.py:36-49, 120-168, 187-203); Token-2022 transfer fees NOT_SUPPORTED |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED (partial) | only via AMMSlippage on a user-supplied `pool_reserve_last` column (slippage.py:101-126; data/trades.py:122-123); no volume cap, no failed/partial fills |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED + smoke | default order_delay=0 executes inside `order()` at the current bar close (core.py:1542-1544, 1280-1285); order_delay=1 fills at bar k+1 CLOSE, not open (core.py:1078-1090 + 2873-2875 run before next()); smoke: delay 0 -> 110.5 (bar 10 close), delay 1 -> 111.5 (bar 11 close) |
| point-in-time guard / no lookahead | DEMO_ONLY | no structural guard: preprocess() sees the full frame (core.py:2795); `detect_look_ahead_bias` is a sampled truncation probe on 5 bars of preprocess columns (analysis.py:148-243); bars from `group_by_dynamic` are labeled at window start (data/trades.py:128-131, polars default) |
| async event/catalyst injection | NOT_SUPPORTED | only columns added in preprocess(); exchange-rate asof join (data/trades.py:275-293) |
| wallets/on-chain | NOT_SUPPORTED | `unique_traders` count only (data/trades.py:120-121) |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED | multi-asset long format (core.py:2622-2669), token lifecycle `first_seen_bar`/`bar_count` and AgeFilter/VolumeFilter/TopN (core.py:2826-2864, universe.py:59-128), cash ledger with leverage/shorts (core.py:1322-1362) |
| walk-forward / holdout / multiple testing | SOURCE_CODE_VERIFIED (partial) | rolling/anchored walk-forward by row index, no purge/embargo (runner.py:989-1163); grid/Bayesian optimizers; permutation test and Monte Carlo (analysis.py:45, 291); no multiple-testing correction |
| metrics/report | SOURCE_CODE_VERIFIED | metrics.py:15-125 (annualizes with 252 regardless of bar length, lines 44, 56, 65) |
| live trading code present (must be avoidable) | NOT_SUPPORTED (none present) | grep of polarbt/ |

## Fill and chronology assumptions (read the code)

Each timestamp: `update_prices()` sets close prices and OHLC, checks stops, expires orders and executes pending orders whose `created_bar + order_delay <= current_bar` (core.py:492-545, 1078-1090); then `strategy.next(ctx)` runs with the full current bar (including its close) (core.py:2906-2911). A market order placed in next() with the default order_delay=0 fills immediately at that same bar's close plus slippage (core.py:1542-1544, 1280-1293): same-bar close fill. With order_delay=1 it fills during the next bar's update_prices at the next bar's close (smoke verified), so "next bar" means a full-bar delay at close, never next open; docs only say "1=next bar (more realistic)" (docs/complete-reference.md:125). Indicators are computed vectorized on the whole frame in preprocess(); library indicators use no negative shifts (grep `shift(-` empty), but nothing stops a user column from leaking. Intrabar stops with OHLC use priority open, then high, then low (core.py:961-1064): for a long, a take-profit hit by the high wins over a stop-loss hit by the low in the same bar (smoke [2]: exit at TP 118 on a bar with low 90), which is optimistic for wick-heavy memecoin bars. Stop fills use the trigger price, or the open on gaps (core.py:1018-1026). Trade data aggregated with `group_by_dynamic` gets window-start timestamps, so joining external events by bar timestamp would treat the bar close as known at the window open.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3 -m venv /home/claude/ext/venvs/nikkisora__PolarBT
/home/claude/ext/venvs/nikkisora__PolarBT/bin/pip install --only-binary=:all: polars numpy   # polars 2.0.0, numpy 2.5.4; PolarBT itself NOT installed
# stub package: empty __init__.py + core, commissions, orders, results, slippage, trades, universe, metrics
# (read in full, copied byte-identical, sha256 in /home/claude/ext/smoke_stage/nikkisora__PolarBT/SHA256SUMS.txt)
unshare -rn timeout 300 /home/claude/ext/venvs/nikkisora__PolarBT/bin/python -I script.py /home/claude/ext/smoke_stage/nikkisora__PolarBT
```
Outcome: exit 0. 30 hourly bars, signal on bar k=10 (open 110, close 110.5). order_delay=0: filled_bar=10 at 110.5 (same-bar close). order_delay=1: filled_bar=11 at 111.5 (next-bar close, not the 111.0 open). SL=105 and TP=118 both inside bar 12: exit at 118 (TP wins). AMMSlippage with reserve 1000: buy 1.0909 vs exact 1.1000 at trade value 100, buy 1.5000 vs exact 2.0000 at trade value 1000; sells match x*y=k. Files: smoke/nikkisora__PolarBT/script.py, output.txt.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 2.5 | 7.50 | trade-to-bar aggregation incl. trade-count bars, DeFi indicators, token lifecycle universe filters, SOL-to-USD rate join; no Solana adapter, pump.fun data only synthetic (examples/example_defi_trades.py:1-8) |
| B microstructure | 17 | 1.5 | 5.10 | close fills, flat commissions, AMM slippage that understates buy impact, no reserves update, no failures or latency |
| C point-in-time | 15 | 2 | 6.00 | sequential bar loop, optional one-bar delay; default same-bar close fill; sampled lookahead probe only; TP-before-SL intrabar optimism; window-start bar labels |
| D catalyst/on-chain events | 11 | 1 | 2.20 | no event channel; only pre-joined columns |
| E TA/strategy flexibility | 9 | 4 | 7.20 | programmable next(), limit/stop/stop-limit, brackets, trailing stops, sizers, 900-line indicator set, TA-Lib integration |
| F statistical validation | 11 | 2.5 | 5.50 | walk-forward (row-indexed, no purge), permutation test, Monte Carlo; no multiple-testing control; 252-period annualization on any bar size |
| G integration fit | 9 | 3.5 | 6.30 | pure Python on polars+numpy, ran on 3.13; adds polars to a pandas lab; no wallets |
| H maintenance/tests | 6 | 2.5 | 3.00 | 909 tests exist but CI only publishes; dormant 7 months; alpha |
| I license/supply chain | 5 | 4 | 4.00 | MIT text, two runtime deps, PyPI trusted publishing; unpinned lower bounds, auto-bump on every push |
| J operational footprint | 2 | 4 | 1.60 | small wheel-only install, no services |
| Total | 100 | | 48.40 | |

Hard gates: none. Most important limitation for memecoins: fills are at bar close (same bar by default, next bar close with delay) with an AMM impact formula that understates buy-side impact and ignores curve fees and reserve updates, so entries into thin pump.fun pools look cheaper than they are. One credible negative finding: `AMMSlippage` uses rate = v/(R+v) for buys, which is the sell-side formula; exact constant-product buys cost v/R (spend-exact) or more, and tests/test_slippage_and_exchange.py:137-142 asserts the wrong 1.5x value, so the bug is locked in by a test.
Disposition: REIMPLEMENT_IDEA (trade-count bars, token-lifecycle universe filters, truncation-based lookahead probe). Suggested use: REFERENCE.
