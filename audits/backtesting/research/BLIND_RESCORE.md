# Blind devil's-advocate rescore (rubric R1.0)

Reviewer: independent subagent, 2026-10-23. Scored blind: nothing under `research/REPO_REVIEWS/`, `research/smoke/`, `work/scratch/` or `ext/venvs/` was opened. Repos were read only (no installs, no repo code run). Rubric: `RUBRIC_LOCK.md` R1.0, grades 0 to 5 in half points, points = max x grade / 5, total rounded to 2 decimals. Stars ignored.

## Commits scored

| Repo | HEAD | Last commit |
|---|---|---|
| QuantConnect/Lean | f3d841e60dfd010ee5fc293ea893e56952484108 | 2026-10-21 |
| kernc/backtesting.py | ca2e2611621e472542ba90f7243a1fa06a7d7108 | 2026-08-05 |
| gbeced/basana | 0c65f58ba8562f4507b3055b3583b66e4934dff3 | 2026-10-23 |
| eslazarev/purged-cross-validation | 07692dd862d37a988233e190706afb18c5101948 | 2026-10-23 |
| etcherfx/sol-trade | c8f37ad221b415132e766f104559ed80d65072db | 2026-10-22 |
| lblommesteyn/slotfish | 4f760c8076bbebc15106cc03ddc3ea527e79dcd4 | 2026-10-12 |

## Scores

Max points: A 15, B 17, C 15, D 11, E 9, F 11, G 9, H 6, I 5, J 2.

| Repo | A | B | C | D | E | F | G | H | I | J | Total |
|---|---|---|---|---|---|---|---|---|---|---|---:|
| lblommesteyn/slotfish | 3 | 3 | 4 | 2.5 | 1.5 | 3 | 2 | 3 | 4.5 | 4 | **59.30** |
| gbeced/basana | 2 | 2 | 4 | 3.5 | 3 | 0.5 | 4 | 4.5 | 4.5 | 5 | **58.10** |
| QuantConnect/Lean | 1.5 | 2 | 4 | 3.5 | 4.5 | 2 | 1 | 5 | 4 | 1 | **55.70** |
| etcherfx/sol-trade | 2 | 2 | 3.5 | 2.5 | 3.5 | 4 | 2 | 3 | 2 | 3.5 | **54.50** |
| kernc/backtesting.py | 1.5 | 1.5 | 3.5 | 1 | 4 | 2 | 4 | 4 | 3 | 5 | **50.90** |
| eslazarev/purged-cross-validation | 1 | 0 | 2.5 | 0 | 0 | 4.5 | 4.5 | 4 | 5 | 5 | **40.30** |

No candidate reaches the 70/100 adoption threshold. Slotfish is the only one that clears B >= 3 (at exactly 3), and its lead over basana is 1.2 points, inside the noise of any single half-point call.

## Justifications for contestable grades

### lblommesteyn/slotfish (59.30)

- A 3: Solana memecoin native (decodes pump.fun and PumpSwap Anchor events, survivorship-free launch cohort, `src/decode.rs`, `src/market.rs:41-51`), but only the pump.fun ecosystem; decisions fire only on bonding-curve trades (`src/engine.rs:213-218`), so graduated tokens and Raydium, Meteora and Orca pools are out of scope. Could be argued 3.5.
- B 3: best microstructure of the six: program-faithful x*y=k with integer floor rounding and fees (`src/amm.rs:27-42`), slot latency, end-of-landing-slot fills, base plus priority fee on every landed tx, slippage rejects, seeded failures with exit retries, censoring (`src/exec.rs`), PumpSwap pre-trade reserves converted to post-trade (`src/decode.rs:262-272`), and a live same-slot fill check. Held to 3 because the lab's list also needs CLMM ticks, DLMM bins, Token-2022 transfer fees and route failures, none of which exist; our own orders never feed back into the pool; exits never fail on slippage.
- C 4: one clock `(slot, tx_idx, ev_idx)`, wallet-skill outcomes revealed only after their horizon (`src/features.rs:140-169`), launch-time universe rule, and a truncated-tape lookahead test with a mutation check (`tests/engine.rs:129-165`). Not 4.5 because: the `Strategy` context hands plugins the whole tape and a Timeline built from the whole tape (`src/engine.rs:20-27`, `src/main.rs:238-239`), so PIT is a convention for strategies and the test covers only `FeatureEngine`; there is no available-time model separate from execution latency (default 2 slots at `src/exec.rs:34`, while the repo's own paper run measured p50 real latency 8 slots and p90 data lag about 7 s, `results/paper.json`).
- D 2.5: genuine on-chain wallet intelligence (Beta-Binomial wallet skill, co-buy coordination pairs, creator sells, snipers), but no social or catalyst events and no generic event-injection API; adding a source means Rust changes.
- E 1.5: `Strategy` is entries only and exits are a fixed horizon (`src/strategy.rs:1-2`, `src/engine.rs:144`); no stops, take-profit, trailing or TA library; plugins must be Rust or precomputed score files.
- F 3: chronological train/val/test with a purge of one max horizon, threshold picked on validation, test touched once, 15-minute-block IC t-stats, token-cluster bootstrap CIs, paired block test for wallet increment (`python/slotfish/research.py`). Not higher: one split, no walk-forward, no DSR/PBO or multiple-testing correction across 2 models x 3 horizons x 6 ablations, and the whole study is a single 7.9 h window whose test has only 7 IC blocks (`results/research/research.json`), so a reported block t of 14.3 rests on 7 observations.
- G 2: Rust engine driven by CLI subprocess, no Python API; research pinned to Python 3.12 with polars/pyarrow/lightgbm (not 3.13, not SQLite); fetch supervisor is a bash script. Windows exe path is handled in `scripts/run_baseline.py:24`.
- H 3: CI runs fmt, clippy -D warnings and tests (`.github/workflows/ci.yml`), but only 10 tests in total (2 decode, 5 engine, 3 amm), Python is only `py_compile`d, single author, about two weeks old.

### gbeced/basana (58.10)

- B 2: pluggable `LiquidityStrategy` with `calculate_price_impact(amount)` and volume caps (`basana/backtesting/liquidity.py:24-153`), unfilled orders cancel next bar, bid-ask spread and percentage fees. The interface fits a constant-product implementation well, but none ships; impact is a bar-volume heuristic.
- C 4: dispatcher advances time only by event timestamps and asserts ascending order (`basana/core/dispatcher/backtesting.py:55-70`); CSV bar events are emitted at bar close (`basana/external/common/csv/bars.py:46-47`); orders fill on the next bar by default (`basana/backtesting/exchange.py:95-96`). Strategies cannot reach future events structurally. No explicit available-time field.
- D 3.5: any number of timestamped `EventSource`s are merged chronologically, so catalyst/social/wallet feeds are natural; none provided.
- F 0.5: no optimizer, no walk-forward, no Sharpe or overfitting statistics anywhere in `basana/`.
- G 4: pure Python 3.10 to 3.14, two runtime deps, CI on Windows, Linux and macOS; asyncio and Decimal style needs adapting to a pandas/SQLite lab.

### QuantConnect/Lean (55.70)

- C 4: Time/EndTime separation, data emitted at EndTime through the subscription synchronizer, stale-price checks in `Common/Orders/Fills/FillModel.cs`. Held below 4.5 because default market orders fill at the price of the bar that produced the signal, not the next bar.
- B 2: rich pluggable fill, fee and slippage models (`MarketImpactSlippageModel.cs` Almgren, `VolumeShareSlippageModel.cs`), no AMM or DEX concept.
- G 1: .NET 10 plus pythonnet bound to Python 3.11 in the Docker foundation image (`Common/QuantConnect.csproj:5`, `DockerfileLeanFoundation:27`); not importable into a Python 3.13 project.
- F 2: grid and Euler optimizers (`Optimizer/Strategies`), PSR in statistics; no walk-forward, sealed holdout, PBO or DSR.
- J 1: multi-GB Docker images and a .NET runtime.

### etcherfx/sol-trade (54.50)

- B 2: size-dependent all-in cost interpolated from Jupiter quote probes (`sol_trade/costs.py:1-14`), but it is a present-day snapshot applied to all history (not point in time), linearly extrapolated above the largest probe, with no AMM state, no failed swaps and no route failures in backtests.
- C 3.5: closed bars only, signal at close and fill at next open, gap-aware stops at min(level, open) (`sol_trade/engine.py:1-20`), Fear & Greed lagged one UTC day (`sol_trade/fear_greed.py:127-150`). Sentiment windows key on Reddit `created`, not `fetched_at` (`sol_trade/sentiment.py:556-560`), and the cost model is not historical.
- F 4: sealed newest-period holdout, walk-forward selection folds, SQLite trial registry, DSR with trial count and variance, paper-trading promotion gates (`sol_trade/evaluation.py:1-135`).
- G 2: it is a live trading bot that loads `SOLTRADE_PRIVATE_KEY` and swaps through Jupiter (README step 3, `sol_trade/wallet.py`, `sol_trade/trading.py`); the backtester depends on global `config()`; candles come from CEX exchanges via ccxt (`config.json.sample` `data_exchange: okx`), so DEX-only memecoins have no data path.
- I 2: GPL-3.0 copyleft plus key-handling and real-money code paths in the same package. Not a hard gate for read-only reuse of ideas, but importing it into the lab would pull wallet code in.
- H 3: 212 tests, but they run only in the release workflow, not on push or PR.

### kernc/backtesting.py (50.90)

- C 3.5: market orders fill at the next bar open unless `trade_on_close=True` (`backtesting/backtesting.py:919`), and data are truncated to the current bar during `next()` (`backtesting/backtesting.py:1342`). Indicators from `self.I` are computed on full arrays first, so a leaky indicator is not caught; no event or available time.
- B 1.5: constant relative spread and a commission that may be a callable of size and price (`backtesting/backtesting.py:1139-1160`), so size-dependent cost is possible by hand; every order fills in full, no liquidity limit or failure.
- I 3: AGPL-3.0 (`LICENSE.md`, `setup.py:14`). Acceptable for private research use; any distribution or network service built on it inherits copyleft obligations.

### eslazarev/purged-cross-validation (40.30)

- Scored as a validation library, not a backtester (B, D, E are 0 by design).
- F 4.5: PurgedKFold, PurgedGroupKFold, CPCV, walk-forward, embargo, PBO via CSCV, PSR, DSR, MinTRL, minimum backtest length, effective trial count, Optuna recorder. I re-derived the DSR expected-max-z term (Bailey and Lopez de Prado) and it matches `src/purgedcv/_metrics.py:161-176`; PSR uses sqrt(n-1) and non-excess kurtosis as in the paper. Not 5 because there is no sealed-holdout mechanism.
- C 2.5: sample-level label intervals with purge, embargo and leakage assertions (`src/purgedcv/diagnostics.py:288-426`); point in time only in the validation sense.
- H 4: about 540 test functions incl. property-based tests, CI on Python 3.11 to 3.15 with mypy; but "Development Status 3 - Alpha" and a single author.

## Slotfish: strongest weakness

Slotfish can simulate exactly one trade shape: a fixed-size market buy on a pump.fun bonding curve that has not graduated, followed by a market sell after a fixed number of slots. Decisions are only generated on bonding-curve `Trade` events for tokens that are still `tradable_at` the slot, which requires the curve to be incomplete (`src/engine.rs:213-218`, `src/market.rs:47-50`); an entry that lands after graduation is skipped as `graduated` in both the reference model and the streaming engine (`src/exec.rs:111-116`, `src/engine.rs:118-121`); the exit time is hard-coded as landing slot plus hold plus latency with no strategy hook (`src/engine.rs:144`, `src/strategy.rs:1-2`); and the only pricing function is x*y=k (`src/amm.rs:3-7`). In the reported run only 201 of 6,027 cohort tokens ever graduated (`results/info.json`), so every token that survives long enough to trade on PumpSwap, Raydium (CPMM or CLMM), Meteora DLMM or Orca Whirlpools is untradeable, and stops, take-profit, trailing exits and indicator-driven exits cannot be expressed. Its high B and A grades therefore apply only to the first minutes of a pump.fun launch; supporting the lab's TA, catalyst and post-graduation use cases means rewriting `engine`, `exec`, `market` and `decode` in Rust, not configuring it. A close runner-up weakness: the `Strategy` context exposes the full tape and a Timeline built from the full tape (`src/engine.rs:20-27`, `src/main.rs:238-239`), so a plugin can read future reserves or a token's future `complete_slot`; the lookahead test (`tests/engine.rs:129-165`) only covers `FeatureEngine`.
