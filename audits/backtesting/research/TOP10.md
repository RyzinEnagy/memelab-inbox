# Top ten and implementation shortlist (Phase 03)

Rubric R1.0 (locked before scoring). 25 repositories reviewed at pinned commits by five reviewers working from the same brief; every card is in `REPO_REVIEWS/<owner>__<repo>.md` with file:line evidence; smoke scripts and outputs in `smoke/`. Totals recomputed from the per-criterion grades by script (all 25 match the cards). Machine-readable table: `RANKING.csv`.

## Ranked ten (research ranking, not an install list)

| Rank | Repo @ sha | License (file) | Total | Blind rescore | What it gets right | What it cannot model for Solana memecoins | Use |
|---:|---|---|---:|---:|---|---|---|
| 1 | lblommesteyn/slotfish @ 4f760c80 | MIT | 65.10 | 59.30 | exact x*y=k on the pump.fun curve, deterministic slot-ordered event engine, a lookahead test for features | only fixed-size buys on ungraduated curves with fixed-horizon exits; ignores PumpSwap `virtual_quote_reserves`; strategies receive the full tape (future) | REIMPLEMENT_IDEA |
| 2 | nautechsystems/nautilus_trader @ 7b3ed05d | LGPL-3.0 | 55.00 | | mature event engine, order lifecycle, Uniswap V3 tick math in a defi crate | fills never use pool state; same-bar close fills on bars; no Solana | REFERENCE |
| 3 | etcherfx/sol-trade @ c8f37ad2 | GPL-3.0 | 52.40 | 54.50 | next-open fills, closed-bar storage, live/backtest parity test, sealed holdout, deflated Sharpe with persistent trial count | applies today's Jupiter quote costs to all past bars; CEX candles; backtest import path loads the private key | REIMPLEMENT_IDEA (no code: GPL, wallet code) |
| 4 | gbeced/basana @ 0c65f58b | Apache-2.0 | 51.00 | 58.10 | async event-driven design, pluggable `LiquidityStrategy` hook, next-bar open fills | mid-bar events fill at that bar's open (before the event); impact as share of bar volume, which is unknown at the open | REIMPLEMENT_IDEA |
| 5 | QuantConnect/Lean @ f3d841e6 | Apache-2.0 | 49.90 | 55.70 | reference fill/slippage/fee model architecture | C#/.NET host, Python 3.11 only; volume-share slippage capped so tiny it is meaningless; no AMM | REFERENCE |
| 6 | nikkisora/PolarBT @ 18f9363a | MIT | 48.40 | | pump.fun trade aggregation into bars, AMM slippage idea | buy-side AMM formula wrong (uses sell formula; its own test asserts the wrong value); same-bar close fills; TP wins over SL in one bar | REIMPLEMENT_IDEA (as a cautionary example) |
| 7 | polakowo/vectorbt @ 8e30b8ce | Apache-2.0 + Commons Clause | 47.90 | | fast parameter sweeps, open-source deflated Sharpe | flat-fraction slippage; stop exits fill exactly at the stop even on gaps; purge/embargo splitters are PRO-only | REIMPLEMENT_IDEA |
| 8 | nkaz001/hftbacktest @ 5f3ec40b | MIT | 47.40 | | latency-aware fills (feed and order latency) | order-book only; taker fills never deplete depth; Python binding has a use-after-free on temporary arrays | REIMPLEMENT_IDEA (latency model) |
| 9 | eslazarev/purged-cross-validation @ 07692dd8 | MIT | 46.90 | 40.30 | purged k-fold, walk-forward, CPCV, PBO, DSR, 500+ tests; independent leakage check agreed | split leakage only, not feature availability; group folds can silently return empty training sets | REIMPLEMENT_IDEA for the engine (below 70); usable as an external cross-check |
| 10 | kernc/backtesting.py @ ca2e2611 | AGPL-3.0 | 45.90 | 50.90 | cleanest bar chronology: next-bar open with `trade_on_close=False`, gap-through stops fill at the open, SL priority over TP | one OHLC series per instrument, flat spread; indicators computed over the full series without a causality check; plot embeds a tracking iframe | REFERENCE; test-only oracle in an isolated venv (Phase 04) |

Positions 11 to 25 (scores in RANKING.csv): bt 45.30, flint 44.70, signal-backtest-harness 41.40, freqtrade 41.10, jesse 40.90, Meteora dlmm-sdk 40.80, Orca whirlpools 40.70, trade-executor 39.70, alphalens-reloaded 39.40, Raydium sdk-V2 34.70, uniswappy 34.40, quantstats 27.50, pypbo 21.00; INELIGIBLE (hard gate): pumpfun-momentum-bot 19.90 (live seed-phrase wallet and blind signing), pumpsim-api 10.40 (no source code).

## Eligibility outcome

No repository reaches the 70-point adoption threshold. Only slotfish has B >= 3 (3.5 primary, 3.0 blind), and its scope is limited to pump.fun curve buys. Under GRADING_RUBRIC: "If no finalist is adequate, implement a small purpose-built engine informed by documented ideas, with a baseline independent test oracle and without copied incompatible code." That is the decision carried to Phase 04 for confirmation by bake-off.

## Why #1 is not the core engine

slotfish is Rust, simulates one trade shape (fixed-size curve buy, fixed-slot exit), skips any token after graduation (the lab's universe is almost entirely graduated tokens on PumpSwap, Raydium, Meteora and Orca), and hands strategies the full data tape. Its value is ideas: exact curve math, slot-ordered deterministic replay, and an explicit lookahead test.

## Implementation shortlist (1 to 3 pieces plus custom code)

1. Custom `memelab/backtest` engine (unavoidable): AMM execution ladder, point-in-time store, event replay, ledger. Ideas from slotfish (deterministic ordering, curve math), basana (liquidity hook, but no mid-bar backdating), sol-trade (next-open fills, closed bars only, persistent trial count, sealed holdout), backtesting.py (gap-through stop at open, SL before TP).
2. Validation: reimplement chronological walk-forward with purge and embargo (about 100 lines, independently tested), reusing the lab's own `social/replay_core` LabelGate pattern. purgedcv may be used outside the runtime as a cross-check in tests only if Phase 04 shows it adds value.
3. AMM math: write CPMM swap math from the constant-product formula with explicit fee handling, cross-checked against the Raydium AMM v4/CPMM formulas read in the SDK (ceil fee, floor output) without copying GPL code; PumpSwap must use effective quote reserves (vault + signed `virtual_quote_reserves`) and the market-cap fee tier. CLMM (Raydium/Orca) and DLMM (Meteora) require tick/bin state at the trade's slot, which no free source provides: refuse with UNSUPPORTED_POOL unless a quote observed at decision time exists.

## Findings that change our design

- Several popular engines fill at the same bar's close by default (vectorbt, nautilus on bars, Lean, jesse, PolarBT, bt). Our engine fills at the next bar open after decision plus latency, never the signal bar.
- Gap-through stops: vectorbt, freqtrade and trade-executor book the stop price on a gap; backtesting.py and jesse fill at the gapped open. We fill at the open (G25).
- Today's quote applied to history (sol-trade, signal-harness pool choice) is the exact error G15 forbids.
- Same-bar SL and TP: PolarBT gives TP; we give SL (conservative).
- Size-blind costs (vectorbt, bt at zero volume, Lean) are the error G10/G35 target.
