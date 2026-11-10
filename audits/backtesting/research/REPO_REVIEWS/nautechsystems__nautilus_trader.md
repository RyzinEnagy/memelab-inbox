# nautechsystems/nautilus_trader

- URL: https://github.com/nautechsystems/nautilus_trader
- Pinned commit: 7b3ed05d980a344c1f698661d542ebcbae2c8972 (2026-10-23T23:45:09+10:00), cloned 2026-10-23T15:52:58Z with `git clone --depth 1` (branch develop). Matches LONGLIST head_sha_2026_10_23. HEAD is the v2 Rust/PyO3 line, 2.0.0rc8 (python/pyproject.toml:3), not yet on PyPI; `pip install nautilus_trader` resolves to legacy v1 1.231.0 (Cython, maintained on develop_v1 for security backports only per MIGRATION_V2.md:6); newest PyPI pre-release is 2.0.0rc7.
- Category: event-driven (also crypto/DEX: EVM pool event replay and Uniswap V3 math)
- Discovery channel: seed (LONGLIST)
- Stars/forks (low weight, from search time): not recorded at search time
- License (from LICENSE file text, not badge): LGPL-3.0-only (164-line GNU LGPL v3 text; python/pyproject.toml:21 agrees) ; transitive notes: weak copyleft; using the unmodified wheel as a library is fine, vendoring or modifying excerpts carries LGPL obligations; CLA.md and TRADEMARK.md present
- Package: PyPI nautilus_trader 1.231.0 (v1, cp313 manylinux wheel 189 MB) and 2.0.0rc7 (v2 pre-release, cp313 wheel, zero declared deps) ; Python/OS: v2 requires-python >=3.13,<3.15 (python/pyproject.toml:24); Linux, macOS, Windows x86_64 wheels (docs/getting_started/installation.md:10, 140) ; native deps: compiled Rust core (_libnautilus .so); v1 pulls numpy, pandas, pyarrow, msgspec, uvloop
- Maintenance: last commit 2026-10-23; CI files build.yml, test.yml, nightly-tests.yml, codeql-analysis.yml, security-audit.yml, openssf-scorecard.yml, performance.yml and more; tests 168 Python test files under python/tests plus Rust unit/integration tests (34 tests dirs under crates)
- Security surface: Makefile/scripts not run; compiled binary core from PyPI; live adapters for 18 venues with API keys (crates/adapters/*); EVM blockchain execution client configured with a private key (crates/adapters/blockchain/src/config.rs, execution/client.rs); none of these are loaded by a pure BacktestEngine run; smoke ran offline

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | SOURCE_CODE_VERIFIED | crates/execution/src/matching_engine/mod.rs:1955-2047 process_bar turns each bar into O/H/L/C synthetic ticks (2056-2110) |
| tick/trade replay | SOURCE_CODE_VERIFIED | quotes, trades, L2/L3 order book deltas and depth (crates/model/src/data/: quote.rs, trade.rs, delta.rs, depth.rs) |
| CPMM math | NOT_SUPPORTED | AmmType enum lists CPAMM (crates/model/src/defi/dex.rs:60-73) but no reserve-based swap math exists (grep reserve0/get_amount_out in crates/model/src/defi returns nothing) |
| CLMM/DLMM math | SOURCE_CODE_VERIFIED (EVM Uniswap V3 only) | crates/model/src/defi/tick_map/{tick_math,sqrt_price_math,full_math,liquidity_math,tick_bitmap}.rs; pool_analysis/profiler.rs:440 execute_swap, :519 simulate_swap_through_ticks, :803-934 quote_swap / size_for_impact_bps; 4940-line test file pool_analysis/tests.rs. No DLMM bins; no Solana chain (Blockchain enum crates/model/src/defi/chain.rs:55-110 has no Solana; repo-wide grep finds "solana" only in currencies.rs and docs) |
| routes | NOT_SUPPORTED | no multi-hop routing in matching or defi code |
| fees/taxes | SOURCE_CODE_VERIFIED | maker/taker, fixed, per-contract fee models (python stubs execution/__init__.pyi:168-241; v2 requires an explicit fee model per venue); no token transfer-fee model |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED (book data only) | with L2/L3 data orders walk the book; on bars, volume is split into 4 tick sizes (matching_engine/mod.rs:8419-8460) and any remainder is filled one tick worse with no limit (mod.rs:5761-5800 "Exhausted L1 volume: slip remainder by a single price increment"); SizeAwareFillModel uses hard-coded 10/50-unit levels and one tick (crates/execution/src/models/fill.rs:1004-1124) |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | market order submitted in on_bar fills at that bar's close at the same timestamp (smoke A, v1 and v2); optional latency model (crates/execution/src/models/latency.rs:29-43, backtest config.rs:301) |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED | every data item carries ts_event and ts_init and the engine sorts and replays by ts_init (crates/backtest/src/engine.rs:422, 520, 862-870); bar stamping at close is the user's responsibility |
| async event/catalyst injection | SOURCE_CODE_VERIFIED (engine) / limited in v2 node | CustomData (crates/model/src/data/custom.rs:385-390) replayed by timestamp; MIGRATION_V2.md "Known limitations": v2 BacktestNode catalog config does not support custom data (BacktestEngine does) |
| wallets/on-chain | SOURCE_CODE_VERIFIED (EVM, replay) | DeFi pool events (swaps, mints, burns, collects, flash, blocks) replayed via BacktestEngine.add_defi_data (crates/backtest/src/defi/engine.rs:16-55); TokenBalance is an ERC-20 balance record (crates/model/src/defi/wallet.rs); these events update pool state for actors, they do not drive the matching engine (no defi references in crates/execution/src/matching_engine/mod.rs) |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED | multi-venue, multi-instrument portfolio and accounts (crates/portfolio, crates/model/src/accounts) |
| walk-forward / holdout / multiple testing | NOT_SUPPORTED | none found (grep walk-forward/holdout/deflated in crates and python returns no validation code) |
| metrics/report | SOURCE_CODE_VERIFIED | 34 statistics in crates/analysis/src/statistics/ (sharpe_ratio.rs, sortino_ratio.rs, max_drawdown.rs, expected_shortfall.rs, ...) |
| live trading code present (must be avoidable) | SOURCE_CODE_VERIFIED | crates/live, crates/adapters/* incl. blockchain execution client; avoidable by using BacktestEngine only |

## Fill and chronology assumptions (read the code)

Bars are processed by the venue's matching engine before the strategy sees them: the bar becomes up to four synthetic trade ticks O, H, L, C (or O, L, H, C with adaptive ordering, mod.rs:2081-2089) with the bar volume split across them (mod.rs:8419). When on_bar(k) submits a market order, the L1 book is at bar k's close, so the order fills at close(k) at bar k's timestamp, with zero latency unless a LatencyModel is configured (smoke A: 110.50 at 11:00). If the order exceeds the quarter of bar volume assigned to the close tick, the remainder fills one price increment worse without any cap (mod.rs:5773; smoke B: 5000 units against a 10-unit bar, 2.5 at 110.50 and 4997.5 at 110.51). Probabilistic fill models only add a one-tick slip with probability prob_slippage (fill.rs:166-220). Custom fill models (Rust trait fill.rs:48-98, Python subclass per docs/concepts/backtesting/fill-models.md:130-143) can return a synthetic OrderBook from get_orderbook_for_fill_simulation, which is the hook where an AMM curve could be expressed as a ladder. Indicators only see completed bars if bars are timestamped at close. The Uniswap V3 PoolProfiler can quote exact-in/exact-out swaps and size-for-impact on EVM pools, but it is analysis code, not wired into order fills.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3 -m venv /home/claude/ext/venvs/nautechsystems__nautilus_trader
pip install --only-binary :all: nautilus_trader        # exit 0, 97 s, 1.231.0 (v1) cp313 wheel
python -I script.py > output.txt                       # v1
python3 -m venv /home/claude/ext/venvs/nautechsystems__nautilus_trader-v2rc
pip install --pre --only-binary :all: nautilus_trader==2.0.0rc7 pandas   # exit 0
python -I script_v2rc7.py > output_v2rc7.txt           # v2 rc7, closest released build to pinned rc8
```
Outcome: both exit 0, identical results. A: MARKET BUY 1 submitted in on_bar for bar 10 (close 110.50) filled at 110.50 at 2026-01-01 11:00 (same bar close, no latency). B: MARKET BUY 5000 with bar volume 10 filled 2.5 at 110.50 and 4997.5 at 110.51 (0.009% worse for 500x bar volume). The pinned rc8 source itself was not built (Rust toolchain build not attempted).

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 1.5 | 4.50 | EVM-only DeFi model (Uniswap V3 math, pool event replay); no Solana, no CPMM math, no DLMM; AMM math not used for fills |
| B microstructure | 17 | 3.0 | 10.20 | order-book matching with depth, partial fills, latency and fee models, custom fill-model hook; on bar data impact is one tick regardless of size (smoke B) |
| C point-in-time | 15 | 3.5 | 10.50 | ts_event vs ts_init on every record, deterministic ts_init replay; same-close zero-latency market fills by default (smoke A) |
| D catalyst/on-chain events | 11 | 2.5 | 5.50 | CustomData and DeFi event replay; EVM only; v2 BacktestNode lacks custom data |
| E TA/strategy flexibility | 9 | 4.0 | 7.20 | indicators crate, bar aggregation, full Python strategy API, order types incl. emulated |
| F statistical validation | 11 | 1.0 | 2.20 | rich performance statistics, no walk-forward, holdout or multiple-testing tools |
| G integration fit | 9 | 2.5 | 4.50 | py3.13 wheels on Linux/Windows, no services for backtests; but a large framework with its own data model, and v1 to v2 API break in progress (pinned HEAD is unreleased rc8) |
| H maintenance/tests | 6 | 5.0 | 6.00 | daily commits, extensive CI incl. CodeQL, security audit, OpenSSF scorecard, large test suites |
| I license/supply chain | 5 | 3.0 | 3.00 | LGPL-3.0 (no vendoring without review), 189 MB compiled binary wheel |
| J operational footprint | 2 | 3.5 | 1.40 | no always-on services for backtests (Redis/Postgres optional for live), heavy wheel |
| Total | 100 | | 55.00 | |

Hard gates: none for pip use (LGPL-3.0 needs review before any vendoring). Most important limitation for memecoins: it has no Solana or constant-product pool model and its matching engine never consults AMM state, so pool-depth impact on PumpSwap/Raydium/Orca/Meteora must be faked through a custom fill model returning a synthetic book. One credible negative finding: on bar data a market order 500 times the bar volume fills only one tick worse than the close (mod.rs:5773, smoke B), so default bar backtests effectively assume unlimited liquidity.
Disposition: REFERENCE. Suggested use: REFERENCE (study ts_event/ts_init separation, the FillModel get_orderbook_for_fill_simulation hook and the Uniswap V3 swap math tests as a golden-test source; re-evaluate PIP only after v2 is released and a Solana pool fill model is prototyped).
