# raydium-io/raydium-sdk-V2

- URL: https://github.com/raydium-io/raydium-sdk-V2
- Pinned commit: e2e8bcd865189c994682a9477ec8eaf1e2da8aaf (2026-10-08T20:36:55+08:00, "fix: operator priority"), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23.
- Category: crypto/DEX/Solana (AMM math SDK)
- Discovery channel: seed (CANDIDATE_SEEDS.md:25); GITHUB_API search "raydium clmm sdk" (SEARCH_LOG.md:21)
- Stars/forks (low weight, from search time): not recorded / not recorded
- License (from LICENSE file text, not badge): GPL-3.0 (LICENSE is the GNU GPL v3 text; package.json "license": "GPL-3.0") ; transitive notes: copyleft; vendoring or porting code into the lab would carry GPL obligations on distribution; deps (@solana/web3.js, @solana/spl-token, bn.js, decimal.js, axios, lodash) are permissive; yarn.lock present.
- Package: npm `@raydium-io/raydium-sdk-v2` 0.2.74-alpha (not installed per brief) ; Python/OS: none (TypeScript, Node) ; native deps: none known.
- Maintenance: last commit 2026-10-08; CI files: none (.github absent; only .husky/pre-commit lint); tests: 0 test files (test/init.ts is a mainnet-RPC script, not a test; jest.config.ts unused).
- Security surface: high-level classes fetch from Raydium HTTP APIs (src/api; hosts such as api-v3/transaction-v1/service.raydium.io, lite-api.jup.ag) and Solana RPC; transaction building and signing helpers (src/common/txTool/txTool.ts, src/common/owner.ts with Keypair). The pure math entry points (CurveCalculator, swapInternal, computeAmountOut) need neither keys nor network.

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | NOT_SUPPORTED | SDK has no bar data |
| tick/trade replay | NOT_SUPPORTED | quotes against one supplied state snapshot; no trade-log replay |
| CPMM math | SOURCE_CODE_VERIFIED | AMM v4: src/raydium/liquidity/liquidity.ts:1035-1146 (fee 1090, out 1092-1094); CPMM: src/raydium/cpmm/curve/calculator.ts:44-150, curve/constantProduct.ts:27-41, curve/fee.ts:6-31 |
| CLMM/DLMM math | SOURCE_CODE_VERIFIED (CLMM) / NOT_SUPPORTED (DLMM) | src/raydium/clmm/libraries/swapSimulator.ts:21-258 (tick traversal 99-243), swapMath.ts:283-382 (step), 113-142 (dynamic fee), sqrtPriceMath.ts:61-92, liquidityMath.ts:8-40 |
| routes | SOURCE_CODE_VERIFIED (live only) | src/raydium/tradeV2/trade.ts (multi-pool route quoting, e.g. 2693-2720 for CPMM legs); depends on live API/RPC pool lists |
| fees/taxes | SOURCE_CODE_VERIFIED (with gaps) | AMM v4 hardcoded 25/10000 (src/raydium/liquidity/constant.ts:4-5) though pool fee fields are decoded (liquidity/layout.ts:32-33); CPMM tradeFeeRate/creatorFeeRate/protocol/fund from config (cpmm.ts:1580-1599, FEE_RATE_DENOMINATOR 1e6 at src/common/fee.ts:2); CLMM base+dynamic fee, cap 10% (clmm/libraries/constants.ts:57,71-74); Token-2022 epoch-aware transfer fee in src/common/transfer.ts:65-130, applied in CLMM quote (clmm/libraries/pool.ts:461,479,491) but NOT in the CPMM route (trade.ts:2693-2720 sets fee: undefined) |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED | curve math is size-dependent; CLMM returns allTrade=false with remaining amount when tick arrays run out (swapSimulator.ts:124-135) |
| fill timing (next bar, latency) | NOT_SUPPORTED | |
| point-in-time guard / no lookahead | NOT_SUPPORTED | core functions take explicit `blockTimestamp`/`epochInfo` (swapSimulator.ts:32, pool.ts:430-433) but nothing validates them against the state snapshot |
| async event/catalyst injection | NOT_SUPPORTED | |
| wallets/on-chain | SOURCE_CODE_VERIFIED (avoidable) | account layouts (liquidity/layout.ts, cpmm/layout.ts, clmm/layout.ts) and RPC fetchers (cpmm.ts:90-171, liquidity.ts:1425-1450); tx/signing in src/common/txTool |
| cross-token cohorts / portfolio | NOT_SUPPORTED | |
| walk-forward / holdout / multiple testing | NOT_SUPPORTED | |
| metrics/report | NOT_SUPPORTED | |
| live trading code present (must be avoidable) | SOURCE_CODE_VERIFIED (present, avoidable) | swap/addLiquidity tx builders across src/raydium/*/; math classes are importable without them |

## Fill and chronology assumptions (read the code)

Not a backtester. Each quote is a pure function of one pool snapshot. AMM v4 (constant product): reserves = vault balance minus `needTakePnl` (liquidity.ts:1436-1437); fee = ceil(amountIn*25/10000) (liquidity.ts:1090, BNDivCeil); out = floor(reserveOut*(amountIn-fee)/(reserveIn+amountIn-fee)) (liquidity.ts:1092-1094). The fee is a compile-time constant even though the pool account's swapFee numerator/denominator are decoded. CPMM: reserves = vault minus protocol, fund and creator fees owed (cpmm.ts:153-160); tradeFee = ceil(in*tradeFeeRate/1e6), creator fee on input or output by `feeOn` (calculator.ts:44-93); out floors (constantProduct.ts:27-33). CLMM: loop over initialized ticks inside the supplied tick arrays; each step calls computeSwap with the base fee plus a volatility-accumulator dynamic fee (swapSimulator.ts:145-179, swapMath.ts:113-142), fills tick-level limit orders (184-206), applies liquidityNet on crossing (208-215). Needed on-chain state for a historical replay: AMM v4 vault balances and needTakePnl; CPMM vault balances, accrued protocol/fund/creator fees and the AmmConfig (fee rates, feeOn); CLMM pool state (sqrtPriceX64, liquidity, tickCurrent, tickSpacing, feeGrowth, dynamic-fee fields), AmmConfig, the tick arrays in the swap direction plus the bitmap extension, the block timestamp (dynamic fee decay) and the epoch plus mint TransferFeeConfig (Token-2022). Reported "executionPrice" for CLMM is the post-swap marginal price (pool.ts:288, 481-486), not the average fill price, so "priceImpact" there measures price movement, not cost.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
# Not installed and not executed, per brief (TypeScript SDK).
cd audits/backtesting/research/smoke/raydium-io__raydium-sdk-V2
python3 -I script.py > output.txt   # stdlib re-expression of the cited formulas, synthetic pool; exit_code=1 (by design: flags a formula mismatch)
```
Outcome (output.txt): synthetic pool 1e9 TOKEN (6 dp) / 30 SOL (9 dp). AMM v4 and CPMM at 0.25% give identical outputs; buying with 0.1/1/5/10 SOL costs 0.58%/3.58%/16.92%/33.58% average-price impact. Re-expressing the CPMM priceImpact formula (cpmm.ts:168-170 poolPrice in human units vs cpmm.ts:1602 executionPrice = out_raw/in_raw, cpmm.ts:1611) gives -995.5 for an A->B sell and -1.07e12 for a B->A buy, where the decimal- and direction-correct impacts are 0.35% and 3.46%. AMM v4's priceImpact (liquidity.ts:1067-1072, 1124-1133) is decimal-adjusted and direction-aware and does not have this problem.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 3.5 | 10.50 | the actual math of major memecoin venues on Solana (AMM v4, CPMM incl. creator fees, CLMM with dynamic fee and limit orders, LaunchLab bonding curves src/raydium/launchpad/curve/constantProductCurve.ts:128-170); not a backtester, no PumpSwap |
| B microstructure | 17 | 3.0 | 10.20 | exact integer on-chain-style amounts, fee tiers, dynamic fee, Token-2022 (CLMM), partial fill flag; but no tests, AMM v4 fee hardcoded, CPMM route omits transfer fee, CPMM priceImpact wrong across decimals/direction, CLMM price-limit path reports a partial fill as complete (swapSimulator.ts:99, 245-247) |
| C point-in-time | 15 | 1.5 | 4.50 | pure functions with explicit blockTimestamp/epoch inputs; high-level fetchers read live RPC/API; no guard |
| D catalyst/on-chain events | 11 | 1.0 | 2.20 | on-chain account layouts usable to decode archived state; no event ingestion |
| E TA/strategy flexibility | 9 | 0.0 | 0.00 | none |
| F statistical validation | 11 | 0.0 | 0.00 | none |
| G integration fit | 9 | 1.5 | 2.70 | TypeScript only; needs Node plus the npm dependency tree or a Python port; math entangled with web3.js types |
| H maintenance/tests | 6 | 1.5 | 1.80 | active commits but zero tests and no CI; "alpha" version |
| I license/supply chain | 5 | 2.0 | 2.00 | clear GPL-3.0 text and lockfile, but copyleft blocks vendoring without approval |
| J operational footprint | 2 | 2.0 | 0.80 | Node toolchain and a large dependency tree for a few hundred lines of math |
| Total | 100 | | 34.70 | |

Hard gates: conditional license gate (GPL-3.0): fine for reading and for independent re-implementation of the public formulas; no copying or vendoring into the lab without license approval. Most important limitation for memecoins: every quote needs the exact historical account state at the decision slot (vault balances, accrued fees, AmmConfig, CLMM tick arrays and dynamic-fee fields, mint transfer-fee config), and the SDK only fetches the current state from live RPC/API, so historical replay requires a separate archived-state source. One credible negative finding: CPMM `computeSwapAmount` reports priceImpact by comparing a decimal-adjusted pool price with a raw-unit, direction-agnostic execution price (cpmm.ts:168-170, 1602, 1611), producing values like -995 or -1e12 for a typical 6-dp memecoin vs 9-dp SOL pool, and the tradeV2 CPMM route sets the Token-2022 transfer fee to undefined (trade.ts:2693-2720).
Disposition: REIMPLEMENT_IDEA (fresh Python implementation of the AMM v4/CPMM/CLMM formulas, golden-tested against archived on-chain swaps). Suggested use: REFERENCE.
