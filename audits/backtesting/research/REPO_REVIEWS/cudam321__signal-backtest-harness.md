# cudam321/signal-backtest-harness

- URL: https://github.com/cudam321/signal-backtest-harness
- Pinned commit: 84643ded87e90c266b9defb72b5aad862ce38528 (2026-06-26T21:09:28+07:00), cloned 2026-10-23T15:53:12Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23.
- Category: catalyst/event
- Discovery channel: GITHUB_API "memecoin backtest" (rank 5)
- Stars/forks (low weight, from search time): 0/not recorded
- License (from LICENSE file text, not badge): MIT (Copyright (c) 2026 cudam321) ; transitive notes: core deps httpx (BSD) and numpy (BSD) only; optional telethon (MIT), solders/solana
- Package: none on PyPI; local package `memebot` 0.0.1 ; Python/OS: requires-python >=3.12, pure Python ; native deps: none in core
- Maintenance: last commit 2026-06-26; CI files none; tests 3 files (tests/test_signal_parser.py, test_horizon_backtest.py, test_fill_simulator.py), pytest; 22 ad hoc `scripts/stage*.py` research scripts with no tests
- Security surface: network clients for GeckoTerminal, Jupiter lite-api, DexScreener, RugCheck, Dune (API key), Telegram via an external MCP server (session string = full account access, documented in .env.example); `WALLET_PRIVATE_KEY` appears only as an empty placeholder in .env.example and is read by no code at this SHA

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | SOURCE_CODE_VERIFIED | GeckoTerminal per-pool OHLCV src/memebot/data/geckoterminal.py:229-345; Jupiter charts per mint src/memebot/data/jupiter.py:177-269 (CLI default, scripts/backtest_channel.py:49) |
| tick/trade replay | DEMO_ONLY | Dune SQL over dex_solana.trades in src/memebot/data/dune.py and scripts/stage0_dune_spike.py; not wired into the backtest |
| CPMM math | NOT_SUPPORTED | none |
| CLMM/DLMM math | NOT_SUPPORTED | none |
| routes | NOT_SUPPORTED | none |
| fees/taxes | SOURCE_CODE_VERIFIED (flat) | Per-side flat bps slippage, PumpSwap fee, MEV drag, fixed priority fee + Jito tip per tx: src/memebot/sim/fill_simulator.py:100-105,130-132; config.toml:20-40. `pumpfun_fee_bps` is loaded (src/memebot/config.py:32,75) but never used by the simulator. No Token-2022 fees |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED (partial) | No exit price at horizon -> total loss: fill_simulator.py:107-125; no size dependence |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | Entry time = posted_at + latency_seconds: fill_simulator.py:93-94; price = close of the bar whose open covers t: fill_simulator.py:53-74 |
| point-in-time guard / no lookahead | NOT_SUPPORTED | Default reference price is a future bar close (smoke); pool picked by current liquidity src/memebot/data/geckoterminal.py:226,305; no PIT tests (flat-candle fixtures) |
| async event/catalyst injection | SOURCE_CODE_VERIFIED | Telegram message dicts -> Signal(posted_at) src/memebot/ingest/telegram_mcp.py:38-79; parser src/memebot/parser/signal_parser.py; first call per mint telegram_mcp.py:104-115. Only one timestamp (posted_at, models.py:32); no received/known-at, no edit_date |
| wallets/on-chain | DEMO_ONLY | Wallet cohort screens and copier OOS in scripts/stage2_screen.py, scripts/stage3_oos.py via Dune |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED (partial) | Equal-weight per-call aggregation src/memebot/backtest/horizon_backtest.py:38-76; bankroll sim only in scripts/stage12_bankroll_sim.py (DEMO_ONLY) |
| walk-forward / holdout / multiple testing | DEMO_ONLY | Bootstrap CI horizon_backtest.py:54-60 (source verified); TRAIN/OOS date windows only in scripts/stage3_oos.py:44; best horizon chosen by max PF with no multiple-testing correction horizon_backtest.py:194-205 |
| metrics/report | SOURCE_CODE_VERIFIED | Net PF, win rate, quantiles, bootstrap CI, verdict: horizon_backtest.py:38-76,160-212 |
| live trading code present (must be avoidable) | NOT_SUPPORTED | No signing or swap code; `solana` extra only declared in pyproject.toml |

## Fill and chronology assumptions (read the code)

Each Telegram call has one timestamp, `posted_at` (src/memebot/models.py:32), taken from the message `date` (telegram_mcp.py:66). There is no separate observed/received time; the subscriber's delay is a constant `latency_seconds` (config.toml:20, placeholder 3.0). Entry time = posted_at + latency and exit time = entry + horizon (fill_simulator.py:93-94). Both are priced by `price_at`, which finds the candle whose OPEN is the latest at or before t (bisect on open times, fill_simulator.py:70) and returns that candle's CLOSE by default (fill_simulator.py:74; default `price_mode="close"` at fill_simulator.py:77 and horizon_backtest.py:79; CLI default scripts/backtest_channel.py:41). So the entry price is the price at the end of the covering bar, after the modeled entry time. Bar size depends on the query window: both data clients switch from minute to hour bars when the window exceeds 16 h (geckoterminal.py:77,307; jupiter.py:167,259), and the default horizons include "1d" (config.toml:12), so the default run uses hourly bars. Costs are applied multiplicatively (fill_simulator.py:130-132). A call whose entry cannot be priced, or whose data fetch raises, is silently dropped from the sample (fill_simulator.py:97-98; horizon_backtest.py:104-109). `exit_sim.py` (triple barrier with stop checked before take-profit inside a bar) exists but is used only by stage scripts and has no tests.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
# Not installed: niche repo (0 stars), not on PyPI. Static AST analysis only; timing computed independently from extracted constants:
python3 -I audits/backtesting/research/smoke/cudam321__signal-backtest-harness/script.py /home/claude/ext/reviews/cudam321__signal-backtest-harness
```
Outcome: exit 0. Default config: query window 24.12 h, so hour bars. The entry reference price lies up to 3600 s after the modeled entry time for every horizon; entry and exit fall in the same hourly bar (gross forced to 1.0) for 99.2% of calls at 30s, 91.7% at 5m and 75.0% at 15m. The repo's tests build flat candles (open=high=low=close) with latency 0, so they cannot detect either effect. Output in smoke/cudam321__signal-backtest-harness/output.txt.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 3.0 | 9.00 | Solana memecoin semantics: mint resolution, PumpSwap/Jito costs, RugCheck gates, dead-token denominator, first-call dedupe |
| B microstructure | 17 | 1.5 | 5.10 | Flat bps slippage/fee/MEV plus fixed gas per tx; no size, reserves or route failure; pump.fun fee unused |
| C point-in-time | 15 | 1.5 | 4.50 | Latency concept exists, but default pricing uses a future bar close up to 1 h late, current-liquidity pool choice, no known-at |
| D catalyst/on-chain events | 11 | 2.0 | 4.40 | Telegram calls as timestamped events with parse confidence; posted time only; on-chain only in scripts |
| E TA/strategy flexibility | 9 | 1.5 | 2.70 | Fixed-horizon hold; managed exits only in untested exit_sim.py |
| F statistical validation | 11 | 2.0 | 4.40 | Bootstrap CI, full denominator, PF over win rate; OOS and drop-top-3 only in scripts; best-of-6 horizon selection uncorrected |
| G integration fit | 9 | 2.5 | 4.50 | Python 3.12+, httpx + numpy, small modules, no keys; network-bound clients and no SQLite store |
| H maintenance/tests | 6 | 1.0 | 1.20 | 3 test files, no CI, 4 months idle, flat-candle tests |
| I license/supply chain | 5 | 4.0 | 4.00 | MIT, uv.lock, two core deps; single anonymous author |
| J operational footprint | 2 | 4.0 | 1.60 | Tiny install; relies on free rate-limited APIs |
| Total | 100 | | 41.40 | |

Hard gates: none (MIT, small and auditable; the fill path is auditable and wrong by default, which is a score issue, not a gate). Most important limitation for memecoins: entry and exit are priced from bar closes keyed by posted time, so on the default hourly bars a call is "bought" at a price up to an hour after the post, which is where most of a memecoin call's move happens. One credible negative finding: the README promises the full dead-token denominator, but calls with no locatable entry price or a failed data fetch are silently excluded (fill_simulator.py:97-98, horizon_backtest.py:104-109), and the chosen pool is today's most liquid pool (geckoterminal.py:226,305), which biases the sample toward tokens that survived long enough to be indexed.
Disposition: REIMPLEMENT_IDEA. Suggested use: REFERENCE.
