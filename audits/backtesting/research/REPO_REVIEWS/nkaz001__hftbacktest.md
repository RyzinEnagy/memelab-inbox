# nkaz001/hftbacktest

- URL: https://github.com/nkaz001/hftbacktest
- Pinned commit: 5f3ec40b2afb764e0fea112f941ed85523ef4e88 (2025-12-23T10:31:05-05:00), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23 (no difference).
- Category: event-driven (tick-level L2/L3 order-book replay with latency and queue models; Rust core, PyO3 + numba Python API)
- Discovery channel: seed; curated awesome-quant (per LONGLIST)
- Stars/forks (low weight, from search time): not recorded in LONGLIST
- License (from LICENSE file text, not badge): MIT (Copyright (c) 2022 nkaz001@protonmail.com) ; transitive notes: PyPI wheel built with features `backtest` + `s3` (py-hftbacktest/Cargo.toml:11-12 and hftbacktest dependency line), so aws-sdk-s3/aws-config/tokio are compiled in; Python deps numba, numpy, polars, holoviews, matplotlib (pull panel, bokeh, pandas).
- Package: PyPI `hftbacktest` 2.4.4 (wheel tag cp313-cp313-manylinux_2_28_x86_64, maturin; release workflow also builds Windows wheels) ; Python/OS: 3.13 wheel installed and ran ; native deps: none needed with wheels (Rust only to build from source).
- Maintenance: last commit 2025-12-23 (10 months before review); CI files codeql.yml, release-python.yml (wheel builds), stale.yml; no workflow runs cargo test or pytest; tests: 27 Rust `#[test]` functions across 8 files, 1 Python test (py-hftbacktest/tests/test_hftbacktest.py) that loads `tmp_20240501.npz`, a file not in the repo.
- Security surface: no install scripts run (wheel only). Live trading code exists in the repo: `connector/` (Binance futures/spot, Bybit with api_key/secret, connector/src/binancefutures/mod.rs:94-96, 197) and `hftbacktest/src/live` behind feature `live`, which is in the Rust crate defaults (hftbacktest/Cargo.toml:24) but not in the PyPI wheel (py-hftbacktest/Cargo.toml:11; smoke: `LIVE_FEATURE False`). S3 data loading compiled into the wheel (hftbacktest/src/backtest/data/npy/mod.rs:170-210), used only for `s3://` paths. Memory-safety footgun: `BacktestAsset.data(ndarray)` passes a raw pointer that Rust does not own or copy (py-hftbacktest/src/lib.rs:206-210; hftbacktest/src/backtest/data/mod.rs:153-165); a temporary array gives silent use-after-free (observed, see smoke).

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | NOT_SUPPORTED | event feed only (event_dtype fields ev, exch_ts, local_ts, px, qty, order_id, ival, fval; py-hftbacktest/hftbacktest/types.py:74-86) |
| tick/trade replay | SOURCE_CODE_VERIFIED + smoke | depth/trade/BBO/L3 event flags (hftbacktest/src/types.rs:150-195); backtest clock `goto` (hftbacktest/src/backtest/mod.rs:755); local side processes events at local_ts (hftbacktest/src/backtest/proc/local.rs:284-307) |
| CPMM math | NOT_SUPPORTED | order books only |
| CLMM/DLMM math | NOT_SUPPORTED | order books only (tick grids are price ticks, not liquidity ranges) |
| routes | NOT_SUPPORTED | per-asset exchange models, no routing |
| fees/taxes | SOURCE_CODE_VERIFIED | maker/taker fee models by traded value, qty or flat per trade, negative for rebates (hftbacktest/src/backtest/models/fee.rs:6-153); no transfer-fee concept |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED (no impact) | NoPartialFillExchange fills any taker size fully at the best price (proc/nopartialfillexchange.rs:56-60, 370-372); PartialFillExchange walks resting depth (proc/partialfillexchange.rs:67-70, 404-460) but the book is not depleted by our fills |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED + smoke | order reaches the exchange after entry latency and takes the best price there (proc/nopartialfillexchange.rs:314-372); ConstantLatency and historical IntpOrderLatency (models/latency.rs:28-53, 98-236); smoke: same decision, 100 ms latency fills 110.5, 1 s latency fills 115.5 after a book jump at +500 ms |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED | every event carries exch_ts and local_ts; strategy sees an event only once local_ts <= current time (proc/local.rs:284-286); exchange processes at exch_ts; feed latency recorded (local.rs:306) |
| async event/catalyst injection | NOT_SUPPORTED | event types are market data and order events only (types.rs:150-195) |
| wallets/on-chain | NOT_SUPPORTED | CEX connectors only, excluded from wheel |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED (partial) | multi-asset backtest over a list of BacktestAsset; per-asset position/balance/fee state (py-hftbacktest/hftbacktest/state.py:10-52); no cross-asset cash ledger |
| walk-forward / holdout / multiple testing | NOT_SUPPORTED | none in repo |
| metrics/report | SOURCE_CODE_VERIFIED | py-hftbacktest/hftbacktest/stats/metrics.py (Sharpe, Sortino, drawdown, returns; trading_days_per_year=252 default at :65, :91, :118) |
| live trading code present (must be avoidable) | SOURCE_CODE_VERIFIED (present, avoidable) | connector/src/*, hftbacktest/src/live, py-hftbacktest/src/live.rs; not compiled into PyPI wheel (`live` feature off) |

## Fill and chronology assumptions (read the code)

There are no bars. Market data events are applied to the exchange-side book at exch_ts and to the local (strategy) book at local_ts (proc/local.rs:284-299), so the strategy only sees what had arrived by its clock; `elapse(d)` advances the clock and processes both queues in timestamp order (backtest/mod.rs:755, 1106-1118). An order submitted at local time t is processed by the exchange model at t + entry_latency (ConstantLatency or interpolated from recorded order latencies), and a market or marketable order fills against the exchange book at that moment (proc/nopartialfillexchange.rs:314-372). Resting limit orders fill when the book or trades cross them, with queue position from a selectable queue model (models/queue.rs:44-481). Responses reach the strategy after the response latency. Liquidity-taking orders do not consume depth, so large orders get unrealistic fills (doc comment proc/nopartialfillexchange.rs:56-60). The clock starts at i64::MAX until the first elapse (backtest/mod.rs:709, 1107-1112); computing a duration from `current_timestamp` before the first elapse overflows silently.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3 -m venv /home/claude/ext/venvs/nkaz001__hftbacktest
/home/claude/ext/venvs/nkaz001__hftbacktest/bin/pip install --only-binary=:all: hftbacktest   # 2.4.4, 2m32s, venv 840 MB
unshare -rn timeout 540 /home/claude/ext/venvs/nkaz001__hftbacktest/bin/python -I script.py
```
Outcome: exit 0. Synthetic book: bar k at t_k has bid 99.5+k / ask 100.5+k; jump to 114.5/115.5 at t_10 + 500 ms. Decision at local t_10 + 2 ms (sees 109.5/110.5), market buy 1 unit: entry latency 0 ms and 100 ms fill at 110.5 (exchange time t_10+2 ms and +102 ms); 1000 ms fills at 115.5 (t_10+1002 ms); taker fee 0.1% charged. Two earlier attempts exited 0 with garbage and no error: (1) duration computed from the initial i64::MAX clock; (2) a temporary ndarray passed to `BacktestAsset.data()`, after which the first backtest in the process saw a NaN book and filled at 4.6e18 with position 1.0 (use-after-free). Files: smoke/nkaz001__hftbacktest/script.py, output.txt.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 1.5 | 4.50 | CEX order-book semantics (Binance/Bybit), tick sizes and queues; no AMM, curve or Solana slot concept; irregular-event replay is the only transferable idea |
| B microstructure | 17 | 3 | 10.20 | strong latency, queue, partial-fill and fee models, verified latency-dependent fills; taker fills never move the book and nothing models pool reserves |
| C point-in-time | 15 | 3.5 | 10.50 | dual exch_ts/local_ts per event and order latency, verified in smoke; no tests that target lookahead, no available_at for non-market events, correctness depends on the user supplying true local_ts |
| D catalyst/on-chain events | 11 | 1 | 2.20 | timestamp machinery exists but no event type for catalysts, social or wallets |
| E TA/strategy flexibility | 9 | 2.5 | 4.50 | any logic in numba njit loops; no bar or indicator layer, breakout/retest must be hand-written on ticks |
| F statistical validation | 11 | 1 | 2.20 | performance metrics only |
| G integration fit | 9 | 2.5 | 4.50 | 3.13 wheel on Linux and Windows, no wallets in wheel; numba-only API, npz event format, raw-pointer lifetime hazard, heavy plotting deps |
| H maintenance/tests | 6 | 3 | 3.60 | mature design, 27 Rust unit tests; no test CI, Python test needs a missing data file, 10 months since last commit |
| I license/supply chain | 5 | 4 | 4.00 | MIT text, maturin-built wheels from this repo; wheel bundles AWS S3 SDK; live connectors excluded |
| J operational footprint | 2 | 3 | 1.20 | no services; 840 MB venv, 2.5 min install |
| Total | 100 | | 47.40 | |

Hard gates: none (live connectors are not in the PyPI wheel; the pointer hazard yields wrong results, not a security exposure, but must be guarded if ever used). Most important limitation for memecoins: it models limit order books, not AMM pools; Solana memecoin execution would have to be faked as a synthetic depth ladder, and taker fills do not deplete that ladder, so size-dependent pool impact is lost. One credible negative finding: `BacktestAsset.data()` stores a raw pointer to the caller's NumPy buffer without a reference (py-hftbacktest/src/lib.rs:206-210), so passing a temporary array silently produced a 4.6e18 fill and a phantom position in the smoke test with exit code 0.
Disposition: REIMPLEMENT_IDEA (dual exch_ts/local_ts event model and entry/response order latency as the template for the lab's observed_at/execution_time handling). Suggested use: REFERENCE.
