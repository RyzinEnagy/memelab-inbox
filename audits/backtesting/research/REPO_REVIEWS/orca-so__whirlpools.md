# orca-so/whirlpools

- URL: https://github.com/orca-so/whirlpools
- Pinned commit: cc683ec92acb5e7606caa3d8e514d9383e9c7c11 (2026-10-12T18:29:17+09:00, "add 2026-01-14 audit reports (#1414)"), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23.
- Category: AMM math (Solana CLMM program plus Rust/TS SDKs)
- Discovery channel: seed (CANDIDATE_SEEDS.md:27); GITHUB_API search "orca whirlpools" (SEARCH_LOG.md:22)
- Stars/forks (low weight, from search time): not recorded / not recorded
- License (from LICENSE file text, not badge): proprietary "Orca License" (LICENSE lines 1-44): code was Apache-2.0 until 2025-02-26; from 2025-02-27 a limited, revocable, non-transferable, non-commercial licence for listed uses (education, research and experimentation that "clearly disclose[s] its non-commercial nature", personal use, non-profit, testnet simulation); section 1(b) removes that grant for any use that "does or could benefit" a competitor, where competitor includes "bodies engaged in cryptocurrency trading"; licensor may modify terms at any time (2(b)); reading and viewing count as "Use"; rust-sdk/core/Cargo.toml points `license-file` at the same LICENSE. Not an OSI licence. ; transitive notes: core crate deps ethnum, libm (permissive).
- Package: crates.io `orca_whirlpools_core` 2.1.1 and npm `@orca-so/whirlpools-core` (WASM) (not installed per brief) ; Python/OS: none (Rust, TypeScript) ; native deps: Rust toolchain or Node for the WASM build.
- Maintenance: last commit 2026-10-12; CI: .github/workflows/checks.yml (docker-compose build, test, lint), security.yml, publish.yml; tests: 155 `#[test]` in rust-sdk/core/src, 22 `*.test.ts` in ts-sdk, 40 test-bearing .rs files in programs/whirlpool/src; 11 audit PDFs in .audits (latest 2026-09-30).
- Security surface: on-chain program and SDKs; TS SDK fetches live RPC state and builds/signs transactions (ts-sdk/whirlpool/src/swap.ts); the core quote crate is pure (no RPC, no keys). Nothing was built or run.

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | NOT_SUPPORTED | |
| tick/trade replay | NOT_SUPPORTED | quote against one state snapshot |
| CPMM math | NOT_SUPPORTED (CLMM only; in-range step equals CPMM on virtual reserves, smoke check 1) | |
| CLMM/DLMM math | SOURCE_CODE_VERIFIED (CLMM) | rust-sdk/core/src/quote/swap.rs:198-376 (compute_swap tick loop), 406-492 (compute_swap_step), 379-397 (liquidity_net on crossing); math/token.rs:22-200 (amount deltas, next sqrt price) |
| routes | NOT_SUPPORTED | single pool quotes |
| fees/taxes | SOURCE_CODE_VERIFIED | swap fee in hundredths of a bp, FEE_RATE_DENOMINATOR 1_000_000 (constants/swap.rs:8; math/token.rs:321-343); adaptive fee (math/adaptive_fee.rs:242-260, 363-401; hard cap 10% constants/adaptive_fee.rs:25); Token-2022 transfer fee applied to input and output (quote/swap.rs:49-50, 71-77; TransferFee {fee_bps, max_fee} types/token.rs:8-11); protocol fee is inside the swap fee and not separately quoted |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED (errors rather than partial fill) | swap leaving the supplied tick arrays returns INVALID_TICK_ARRAY_SEQUENCE (math/tick_array.rs:82-123; test quote/swap.rs:782-810); at most six tick arrays of 88 ticks (types/tick_array.rs:5-30, constants/tick.rs:8) |
| fill timing (next bar, latency) | NOT_SUPPORTED | |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED (narrow) | explicit `timestamp` argument (quote/swap.rs:33-43); adaptive-fee `update_reference` rejects a timestamp earlier than the oracle's last update (math/adaptive_fee.rs:403-414, INVALID_TIMESTAMP); TS wrapper uses wall clock `Date.now()` (ts-sdk/whirlpool/src/swap.ts:317) |
| async event/catalyst injection | NOT_SUPPORTED | |
| wallets/on-chain | SOURCE_CODE_VERIFIED (avoidable) | TS/Rust clients fetch accounts and build transactions; core crate needs only decoded facades (types/pool.rs:10-34) |
| cross-token cohorts / portfolio | NOT_SUPPORTED | |
| walk-forward / holdout / multiple testing | NOT_SUPPORTED | |
| metrics/report | NOT_SUPPORTED | |
| live trading code present (must be avoidable) | SOURCE_CODE_VERIFIED (present, avoidable) | ts-sdk/whirlpool/src/swap.ts, rust-sdk/whirlpool; core quote functions are separate |

## Fill and chronology assumptions (read the code)

Not a backtester. `swap_quote_by_input_token` (quote/swap.rs:33-91) removes the input Token-2022 transfer fee, runs `compute_swap`, reverses the input fee, applies the output transfer fee and a bps slippage floor. `compute_swap` walks initialized ticks inside the supplied tick-array sequence; per step it updates the volatility accumulator, takes `static + adaptive` fee (capped), bounds the target to the current tick group, computes the step with `compute_swap_step` (fee taken on input: floor(amount*(1e6-fee)/1e6), math/token.rs:321-324), and on reaching an initialized tick applies `liquidity_net` (subtract when a_to_b and net>0). If the price limit is hit, the partial amount is returned correctly (swap.rs:349-374). If the supplied tick arrays run out first, the quote errors instead of returning a partial fill. Needed on-chain state for a historical replay: Whirlpool account (sqrt_price, liquidity, tick_current_index, fee_rate, tick_spacing, fee_tier_index_seed), up to six TickArray accounts in the swap direction, the Oracle account for adaptive-fee pools (types/oracle.rs) with its last-update timestamps, the block timestamp, and both mints' TransferFeeConfig selected for the epoch (ts-sdk/whirlpool/src/token.ts:296-321).

## Smoke test (if feasible, no wallets, no network beyond pip)

```
# Nothing from the repo installed, built or executed, per brief and licence.
cd audits/backtesting/research/smoke/orca-so__whirlpools
python3 -I script.py > output.txt   # independent stdlib Uniswap-v3-style step math, synthetic pool; exit_code=0
```
Outcome (output.txt): (1) one in-range step equals x*y=k on virtual reserves with the same 0.30% fee (relative difference 4e-57). (2) Size ladder with liquidity dropping from 1e12 to 4e11 at tick -200: average-price impact 0.31%, 0.40%, 1.28%, then 9.07% once the tick is crossed. (3) Adaptive fee example (control 20000, tick group 16): 0.30% static rises to 0.38% after 4 tick groups and 1.61% after 16. The script re-derives public formulas; it does not copy Orca code.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 3.0 | 9.00 | Solana CLMM with adaptive fee and Token-2022; a smaller share of memecoin volume than Raydium/PumpSwap/Meteora |
| B microstructure | 17 | 4.0 | 13.60 | exact step math, tick crossing, adaptive fee, transfer fees, slippage, explicit insufficient-liquidity error; 155 core tests and audits |
| C point-in-time | 15 | 2.0 | 6.00 | pure quote with explicit timestamp and a monotonic-timestamp guard; no historical state handling; TS wrapper uses wall clock |
| D catalyst/on-chain events | 11 | 1.0 | 2.20 | account decoders (codama clients) usable for archived state; no event ingestion |
| E TA/strategy flexibility | 9 | 0.0 | 0.00 | none |
| F statistical validation | 11 | 0.0 | 0.00 | none |
| G integration fit | 9 | 2.0 | 3.60 | small pure Rust core crate (or WASM) could sit behind a subprocess; no Python |
| H maintenance/tests | 6 | 4.0 | 4.80 | active, CI on PRs, broad unit tests, recurring audits; tests not run here |
| I license/supply chain | 5 | 0.5 | 0.50 | non-OSI, revocable, non-commercial licence with a competitor clause covering "bodies engaged in cryptocurrency trading" and unilateral changes |
| J operational footprint | 2 | 2.5 | 1.00 | core crate light; full repo needs Rust, Node, Anchor and docker compose |
| Total | 100 | | 40.70 | |

Hard gates: license (Orca License, not OSI; grant excludes uses that could benefit "bodies engaged in cryptocurrency trading" and is revocable and changeable at will). Keep as RESEARCH_ONLY reference; any implementation must be derived from public Uniswap-v3 math, not transcribed from this repo. Most important limitation for memecoins: quotes need the exact historical Whirlpool, TickArray and Oracle accounts at the decision slot plus the block timestamp, and a thin exit that runs past the supplied tick arrays errors (INVALID_TICK_ARRAY_SEQUENCE) instead of returning the fillable portion, so a backtest must source enough archived tick arrays and treat the error as a failed route. One credible negative finding: the high-level TS swap path takes the adaptive-fee timestamp from `Date.now()` (ts-sdk/whirlpool/src/swap.ts:317) while the oracle state comes from RPC, so wrapper-level quotes are not reproducible for historical replay; only the core crate with an explicit timestamp is.
Disposition: REFERENCE. Suggested use: REFERENCE.
