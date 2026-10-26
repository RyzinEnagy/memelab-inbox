# MeteoraAg/dlmm-sdk

- URL: https://github.com/MeteoraAg/dlmm-sdk
- Pinned commit: af36dd53ab180783ccecda306926189a4700953c (2026-10-23T14:51:02+08:00, "feat(ts-client): apply Token-2022 ScaledUiAmount multiplier to display prices (#307)"), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23.
- Category: AMM math (Solana DLMM SDK: Rust commons, TypeScript client, Python HTTP client)
- Discovery channel: seed (CANDIDATE_SEEDS.md:26); GITHUB_API search "meteora dlmm" (raw/p02_github_search_hits.csv, rank 2)
- Stars/forks (low weight, from search time): 310 / not recorded
- License (from LICENSE file text, not badge): UNKNOWN. No LICENSE or COPYING file anywhere in the repo; no `license` field in any Cargo.toml; only ts-client/package.json:63 declares "ISC" (metadata, no licence text). Treat Rust commons, CLI, market_making and python-client as all rights reserved (research-only); ts-client as ISC-claimed but unconfirmed. ; transitive notes: anchor-lang/anchor-client 0.31, solana-sdk 2.1 (Apache-2.0); python-client deps solana, solders, requests.
- Package: npm `@meteora-ag/dlmm` (ts-client, not installed); python-client has committed dist files (python-client/dlmm/dist/dlmm-0.1.0*.whl/.tar.gz), not on PyPI as checked; no crates.io package for commons ; Python/OS: Python client requires a local Node server ; native deps: Rust toolchain (anchor, solana-sdk) for commons.
- Maintenance: last commit 2026-10-23 (same day as review); CI: .github/workflows/ci-pr-main-program.yml:39 (`cargo t -p commons --test '*'`), ci-pr-main-sdk.yml:55-57 (anchor localnet plus ts-client jest), plus cli and market_making build jobs; tests: Rust integration tests in commons/tests/integration (test_swap.rs, test_swap_token2022.rs, test_swap_quote_with_limit_order.rs) and unit tests in commons/src/quote.rs (some hit mainnet RPC); 10 ts-client test files.
- Security surface: committed prebuilt program binaries (artifacts/lb_clmm.so, token_2022.so, transfer_hook_counter.so; commons/tests/artifacts/*.so) and committed localnet keypairs including secret bytes (keys/localnet/admin-*.json, program-*.json), all for local tests; none were loaded or executed. ts-client/src/server runs an Express HTTP server; python-client/dlmm/dlmm/dlmm.py:9 hardcodes `API_URL = "http://localhost:3000"` and forwards the RPC URL in headers (31-49). CLI and market_making build and sign transactions.

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | NOT_SUPPORTED | |
| tick/trade replay | NOT_SUPPORTED | quote against one state snapshot |
| CPMM math | NOT_SUPPORTED | |
| CLMM/DLMM math | SOURCE_CODE_VERIFIED (DLMM) | bin price from id and bin step: commons/src/math/price_math.rs:3-13 (Q64.64, SCALE_OFFSET 64 and ONE in math/u64x64_math.rs:5,17); constant-price in-bin amounts: commons/src/extensions/bin.rs:69-100; bin walk: commons/src/quote.rs:543-649 (exact in), 435-541 (exact out) |
| routes | NOT_SUPPORTED | single pair |
| fees/taxes | SOURCE_CODE_VERIFIED | base fee = base_factor*bin_step*10*10^power (extensions/lb_pair.rs:136-144); variable fee = ceil(variable_fee_control*(volatility_accumulator*bin_step)^2/1e11) (150-176); total capped at MAX_FEE_RATE 1e8 of FEE_PRECISION 1e9 (178-185; constants.rs:22-24); fee on input or output by collect_fee_mode (279-287); protocol share and limit-order fee split (quote.rs:140-196); Token-2022 transfer fee on in and out (quote.rs:576-577, 641-642; commons/src/token_2022.rs) |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED | bin-by-bin depletion with advancing active id (quote.rs:599-638); Rust returns error "Pool out of liquidity" when no further bin array has liquidity (quote.rs:590, tests 1024-1077); TS `swapQuote` has `isPartialFill` (ts-client/src/dlmm/index.ts:5574-5643) |
| fill timing (next bar, latency) | NOT_SUPPORTED | |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED (narrow) | Rust quote takes an explicit `Clock` (slot, unix_timestamp, epoch) and enforces pair status and activation point (quote.rs:385-410, 554-561); TS `swapQuote` uses wall-clock `Date.now()` for volatility decay (index.ts:5582) but the instance's cached clock epoch for transfer fees (index.ts:5595-5599) |
| async event/catalyst injection | NOT_SUPPORTED | |
| wallets/on-chain | SOURCE_CODE_VERIFIED (avoidable) | RPC fetchers and tx builders in ts-client/src/dlmm/index.ts and cli/src/instructions/*; commons quote needs only decoded accounts |
| cross-token cohorts / portfolio | NOT_SUPPORTED | |
| walk-forward / holdout / multiple testing | NOT_SUPPORTED | |
| metrics/report | NOT_SUPPORTED | |
| live trading code present (must be avoidable) | SOURCE_CODE_VERIFIED (present, avoidable) | cli swap_exact_in/out, market_making crate, ts-client swap builders |

## Fill and chronology assumptions (read the code)

Not a backtester. `quote_exact_in` (commons/src/quote.rs:543-649): validate pair status and activation (slot or timestamp) against the supplied Clock; `update_references(clock.unix_timestamp)` (lb_pair.rs:77-107) sets index_reference to the current active id and decays volatility_reference by reduction_factor if more than filter_period has passed, or zeroes it after decay_period; remove the input Token-2022 fee for the clock's epoch; then, for each bin from the active id outward, update the volatility accumulator to `volatility_reference + |index_reference - active_id|*10000` (capped), recompute the total fee, fill market-maker liquidity then limit orders at the bin's constant price (Q64.64, `amount_out = amount_in*price >> 64` rounding down), and advance the active id while input remains. The fee therefore rises inside a single large swap as it walks away from the reference bin. Output Token-2022 fee is removed at the end. Needed on-chain state for a historical replay: LbPair account (active_id, bin_step, static parameters, v_parameters incl. volatility_accumulator, volatility_reference, index_reference, last_update_timestamp, activation fields, collect_fee_mode, bitmap), the BinArray accounts on the swap side (bins with amount_x, amount_y, cached price, limit-order amounts), the BinArrayBitmapExtension when ids overflow the default bitmap, the Clock (slot, timestamp, epoch) and both mint accounts. Because v_parameters carry the previous swap's state, the fee for a historical trade depends on the exact account snapshot just before it, not on a periodic snapshot.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
# Nothing from the repo installed, built or executed, per brief (binaries and keypairs untouched).
cd audits/backtesting/research/smoke/MeteoraAg__dlmm-sdk
python3 -I script.py > output.txt   # independent stdlib re-expression of the cited DLMM formulas, synthetic pool; exit_code=0
```
Outcome (output.txt): synthetic pool, bin_step 100 (1%), base fee 1%, 2 SOL per bin below active id -1047. Bin price check: adjacent-bin ratio exactly 1.01 and Q64 price equals the float formula. Selling 1M/50M TOKEN stays in one bin (1.00% fee); 300M uses 5 bins (fee rises 1.00% to 1.48%, impact 2.81%); 1B uses 14 bins (fee 1.00% to 6.07%, impact 8.76%). The same 50M sell 10 s after a prior sell moved the price 20 bins pays the 10% capped fee in its first bin and receives 1.3450 SOL instead of 1.4795 SOL, showing that DLMM execution cost depends on the preceding swap history in `v_parameters`.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 3.5 | 10.50 | DLMM is a major Solana memecoin venue; bin math, volatility fee, Token-2022 and activation gates are memecoin-relevant; not a backtester |
| B microstructure | 17 | 4.0 | 13.60 | exact per-bin fill with variable fee, limit orders, transfer fees and out-of-liquidity handling; integration test asserts quote equals actual program output in a local bank with the production binary (commons/tests/integration/test_swap.rs:211-310, assert at 305-308) |
| C point-in-time | 15 | 2.0 | 6.00 | Rust quote is a pure function of an explicit Clock and enforces activation; TS quote mixes wall clock and cached clock |
| D catalyst/on-chain events | 11 | 1.0 | 2.20 | IDL (idls/dlmm.json) and account decoders usable for archived state; no event ingestion |
| E TA/strategy flexibility | 9 | 0.0 | 0.00 | none |
| F statistical validation | 11 | 0.0 | 0.00 | none |
| G integration fit | 9 | 1.5 | 2.70 | Rust commons pulls anchor-client/solana-sdk; TS client heavy; Python client is an HTTP shim to a localhost Node server (always-on service, live RPC) |
| H maintenance/tests | 6 | 3.5 | 4.20 | very active, CI runs quote tests on PRs, quote-vs-program tests; some tests depend on mainnet RPC |
| I license/supply chain | 5 | 1.0 | 1.00 | no licence file (unknown, research-only); committed binaries and keypairs |
| J operational footprint | 2 | 1.5 | 0.60 | heavy Solana/Anchor Rust build or Node stack; Python path needs a running server |
| Total | 100 | | 40.80 | |

Hard gates: license (no LICENSE file; unknown licence for Rust and Python code, ISC claimed only in ts-client/package.json metadata). Keep as RESEARCH_ONLY reference; re-implement from public DLMM documentation and the formulas, do not copy code. Most important limitation for memecoins: the variable fee and the walked bins depend on `v_parameters` and bin reserves exactly as they stood just before the historical trade, so a backtest needs per-slot archived LbPair and BinArray account state (or a reconstruction from every prior swap); periodic snapshots will misprice fees in exactly the volatile minutes that matter. One credible negative finding: the TS `swapQuote` uses `Date.now()` for the volatility-reference decay (ts-client/src/dlmm/index.ts:5582) while transfer fees use the cached on-chain clock epoch, so TS quotes on archived state are neither historical nor reproducible; only the Rust `quote_exact_in` with an explicit Clock is replay-safe.
Disposition: REIMPLEMENT_IDEA (Python DLMM bin-walk quoter from the documented formulas, golden-tested against archived swaps). Suggested use: REFERENCE.
