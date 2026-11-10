# etcherfx/sol-trade

- URL: https://github.com/etcherfx/sol-trade
- Pinned commit: c8f37ad221b415132e766f104559ed80d65072db (2026-10-22T12:54:12-07:00), cloned 2026-10-23T15:52:41Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23.
- Category: crypto/DEX/Solana
- Discovery channel: seed (workplans/backtesting/references/CANDIDATE_SEEDS.md)
- Stars/forks (low weight, from search time): not recorded (seed entry; GitHub API not reachable from this review session)
- License (from LICENSE file text, not badge): GPL-3.0 (full GNU GPL v3 text in LICENSE) ; transitive notes: runtime deps ccxt (MIT), solana-py and solders (MIT/Apache), httpx (BSD), pandas 3.0.5, vaderSentiment (MIT), defusedxml (PSF). Copyleft sits in this repo itself, so no code may be copied or imported into the lab.
- Package: none on PyPI (`sol-trade` not found); pyproject `sol-trade` 3.0.0 ; Python/OS: requires-python >=3.11, `.python-version` 3.13, run scripts for sh/cmd/ps1 (Linux and Windows) ; native deps: solders wheels (Rust-built), otherwise pure Python
- Maintenance: last commit 2026-10-22; CI files .github/workflows/release.yml only (runs `uv run pytest` at release, no push/PR test workflow); tests 20 files, 212 test functions, pytest, deterministic fakes (tests/fakes.py) and recorded fixtures
- Security surface: live Jupiter Ultra swaps signed with a base58 private key from `.env` (`SOLTRADE_PRIVATE_KEY`); Solana RPC client; httpx client created at import time (sol_trade/jupiter.py:22); Reddit, alternative.me and Jupiter HTTP calls; Docker/compose and packaging shell scripts (not run). No obfuscation seen.

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | SOURCE_CODE_VERIFIED | Closed bars from a ccxt CEX (default fixture Coinbase SOL/USDC) stored in SQLite: sol_trade/history.py:157-188, sol_trade/data_source.py:13,35 |
| tick/trade replay | NOT_SUPPORTED | Only bars; ticks exist only in test fakes that build bars (tests/fakes.py) |
| CPMM math | NOT_SUPPORTED | No pool or reserve math anywhere in sol_trade/ |
| CLMM/DLMM math | NOT_SUPPORTED | none |
| routes | NOT_SUPPORTED | Router name is recorded from a live Jupiter quote (sol_trade/costs.py:73); no route simulation |
| fees/taxes | SOURCE_CODE_VERIFIED | All-in bps (fee+impact+spread) from Jupiter quote-only `/order` plus signature/priority fee in USD: sol_trade/costs.py:56-75, 145-168. No explicit Token-2022 transfer fee |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED (partial) | bps linearly interpolated between probe sizes, extrapolated above the largest: sol_trade/costs.py:155-164. Probes are taken now (costs.py:116-121) and applied to all history |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | Signal at close i queues an action, fills at open i+1: sol_trade/engine.py:288-307, 320-343; test tests/test_engine.py:36-47. No latency model |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED | Signals from lookback windows ending at the closed bar: sol_trade/backtest.py:30-62, sol_trade/spec.py:624-650,718-721; forming bar never stored: sol_trade/history.py:4-5,224-226; live-vs-backtest parity test tests/test_parity.py:41-87 |
| async event/catalyst injection | SOURCE_CODE_VERIFIED (limited) | Reddit mention/VADER features over (t-window, t] at bar close: sol_trade/sentiment.py:531-573, called with close times sol_trade/spec.py:180; keyed on post time `created`, not `fetched_at` (sentiment.py:558-567). Fear and Greed uses the prior UTC day only: sol_trade/fear_greed.py:127-150 |
| wallets/on-chain | SOURCE_CODE_VERIFIED (live only) | Whale balances via RPC sol_trade/whale_tracker.py:20-103; used only as a live gate (sol_trade/engine.py:261-263 "Only the live loop sets it") |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED (partial) | Book holds many symbols (engine.py:247-284) but `simulate` backtests one symbol (backtest.py:87-128) |
| walk-forward / holdout / multiple testing | SOURCE_CODE_VERIFIED | Sealed newest-days holdout evaluation.py:56-65,324-401; "folds" are slices of one continuous run evaluation.py:156-166; deflated Sharpe with SQLite trial registry per (symbol, timeframe) evaluation.py:71-134,258-261; tests tests/test_evaluation.py:67-114 |
| metrics/report | SOURCE_CODE_VERIFIED | backtest.py:152-188; buy-and-hold and cash baselines backtest.py:191-223 |
| live trading code present (must be avoidable) | SOURCE_CODE_VERIFIED | Key: sol_trade/config.py:191 (load_dotenv), :312 (SOLTRADE_PRIVATE_KEY), :471-476 (Keypair.from_base58_string). Signing and send: sol_trade/transactions.py:39-50 (sign_message), :175 (`/execute`), :205 (perform_swap). Live executor: sol_trade/trading.py:167-203. Not avoidable by import: the backtest import closure reaches config.py (smoke test) |

## Fill and chronology assumptions (read the code)

Every bar runs on_open, on_low, on_close in that order (sol_trade/backtest.py:107-117). A signal is evaluated on the lookback window that ends at the closed bar i (backtest.py:55-61) and queues an Action (engine.py:320-343); the action fills at the open of bar i+1 (engine.py:288-307), so a signal on bar k close fills at bar k+1 open, at that open price adjusted by the cost model: tokens = notional x (1 - bps/1e4) / open, plus a network fee in USD (engine.py:220-234). Stops are checked against the bar low with levels frozen at the previous close and fill at min(level, open), so gaps through the stop fill at the open (engine.py:141-150; tests/test_engine.py:50-66). Take-profit triggers on close >= level and fills next open (engine.py:165-177). Trailing stops ratchet only on closed highs (engine.py:153-162). Indicators see only the window, and batched windows equal single windows (tests/test_indicators.py:81). The weak link is the cost model: `measure` probes Jupiter today and `model_for` applies that one curve to every historical bar (costs.py:78-133,185-205); the only guard is a COSTS_STALE flag on probe age (evaluation.py:191-197), not a historical liquidity model. Candles come from a CEX pair, so DEX-only memecoins have no data source at all.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
# Not installed: not on PyPI, niche repo, GPL-3.0, live swap code in the same package.
# Static AST analysis only (no repo code imported or executed):
python3 -I audits/backtesting/research/smoke/etcherfx__sol-trade/script.py /home/claude/ext/reviews/etcherfx__sol-trade
```
Outcome: exit 0. The import closure of `sol_trade.backtest` is 12 modules and includes `config` (loads .env, holds SOLTRADE_PRIVATE_KEY), `jupiter` (creates an httpx client at import) and `rpc`; `engine` and `costs` reach the same modules. Only `sol_trade.indicators` is clean (numpy/pandas). The closure does not reach `transactions` or `trading` (swap execution). The repo's own test asserts next-open fills (tests/test_engine.py:36-47). Output in smoke/etcherfx__sol-trade/output.txt.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 2.5 | 7.50 | Solana/Jupiter cost semantics, but CEX candles via ccxt, one symbol per run, no pool/launch data |
| B microstructure | 17 | 2.0 | 6.80 | Size-interpolated all-in bps plus network fee from real quotes; quotes are today's, applied to all history; no reserves, failed routes or thin exits |
| C point-in-time | 15 | 3.5 | 10.50 | Closed-bar windows, next-open fills, parity and no-look-ahead tests; social joins on post time, single timestamp per bar |
| D catalyst/on-chain events | 11 | 2.5 | 5.50 | Reddit and Fear and Greed with causal windows and coverage gating; no generic async event injection; whale data live only |
| E TA/strategy flexibility | 9 | 3.0 | 5.40 | JSON grammar: SMA/EMA/RSI/ATR/MACD/BB/highest/lowest/zscore, crosses, stop/TP/trailing; long-only, one position, no retest state |
| F statistical validation | 11 | 3.5 | 7.70 | Sealed holdout, DSR with persistent trial count, buy-and-hold and cash baselines; folds are slices, not re-fit walk-forward |
| G integration fit | 9 | 1.5 | 2.70 | Python 3.13 and SQLite fit, but backtest path imports config/.env key handling and network clients; GPL blocks vendoring |
| H maintenance/tests | 6 | 3.0 | 3.60 | Commit 2026-10-22, 212 tests incl. parity; tests only run in the release workflow |
| I license/supply chain | 5 | 1.5 | 1.50 | GPL-3.0 copyleft; uv.lock pins deps |
| J operational footprint | 2 | 3.0 | 1.20 | No services; solana/solders/ccxt deps; local SQLite |
| Total | 100 | | 52.40 | |

Hard gates: incompatible license for import or vendoring (GPL-3.0); RESEARCH_ONLY. Most important limitation for memecoins: historical costs are today's Jupiter quotes at a few sizes applied to every past bar, on CEX candles, so launch-phase liquidity, thin exits and rugs are invisible. One credible negative finding: running the backtester is not key-free: `backtest.sizing()` calls `config()` (backtest.py:65-68), which runs `load_dotenv` and copies SOLTRADE_PRIVATE_KEY into the singleton (config.py:191,312-323), so the lab must never import any sol_trade module except, at most, studying `indicators.py`.
Disposition: REIMPLEMENT_IDEA. Suggested use: REFERENCE.
