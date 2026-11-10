# Execution model comparison worksheet (Phase 07)

Retrieved 2026-10-23 at about 18:15Z. Script: `audits/backtesting/execution/p07_spotcheck.py` (read-only Solana JSON-RPC and Jupiter quote endpoint; no swap transaction requested). Raw output: `p07_spotcheck.json`; committed test fixture: `tests/fixtures/backtest/real/pumpswap_spotcheck.json`. This is present-tense evidence about the math. It is never used as a historical fill.

## Pools

| Pool | Quote | Token program | Base vault (raw) | Quote vault (raw) | i64 at byte 245 (virtual quote) |
|---|---|---|---|---|---|
| 5wNu5Qhd... | SOL | SPL Token | 30,219,804,254,733 | 8,404,531,659,572 | -54,230,560 |
| 3KFCgJ5R... | SOL | Token-2022 (metadata extensions only, no transfer fee) | 48,696,366,938,147 | 2,549,524,110,454 | -5,201,251 |
| Cb7ZRgPL... | PUMP (pumpCmX...) | Token-2022 (metadata only) | 37,753,821,539,706 | 54,724,102,704,265 | +585,068,882,233 |

Layout check: owner `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` (Jupiter label "Pump.fun Amm"), account 301 bytes; the two vault addresses read at bytes 139 and 171 hold exactly the base and quote mints read at bytes 43 and 75 (checked from the vaults' own token-account data). Every Jupiter quote was restricted to that DEX with direct routes only, and its `ammKey` equals the pool.

## Results

| Pool | Implied fee, buy (fee on input), effective reserves | Implied fee, sell (fee on output) | Same with vault-only reserves (buy / sell) | Model error vs Jupiter at that tier |
|---|---|---|---|---|
| 5wNu5Qhd | 0.298% (0.05, 0.5, 5 SOL) | 0.301% | 0.297% / 0.302% | -0.002% |
| 3KFCgJ5R | 0.547% | 0.551% | 0.547% / 0.551% | -0.003% |
| Cb7ZRgPL | 1.235% to 1.240% | 1.250% | 2.28% / 0.19% | -0.012% to -0.016% |

Findings:

1. The constant-product math (`cpmm_out_raw`, integer fee rounding against the user) reproduces the router's quotes within 0.02% once two things are right: the pool's own fee tier and the effective quote reserve.
2. PumpSwap fees are per pool: 0.30%, 0.55% and 1.25% here, in whole 5 bp steps. The old engine default (0.25%) overstated every fill. Historical runs now use the highest observed tier, 1.25%, for PumpSwap unless the pool's fee was observed (`execution.assumed_swap_fee`, labeled `ASSUMED_UPPER_OBSERVED_TIER`).
3. The signed value at byte 245 is the virtual quote reserve. On the PUMP-quoted pool it is about 1.07% of the vault; with vault balances alone the implied buy and sell fees disagree (2.28% vs 0.19%), with the effective reserve they agree (1.24% vs 1.25%). `execution.pumpswap_effective` uses vault + virtual.
4. GeckoTerminal's present `reserve_in_usd` for the two SOL pools was within 1% of twice the on-chain quote side (SOL at about 104.21 USD from a Jupiter quote earlier the same hour), so a fresh USD snapshot halved and cut by the 0.8 haircut understates depth by about 20%: conservative, as intended for LIQ_SNAPSHOT_APPROX.
5. Not reproduced: multi-hop routes, other DEXes, and Jupiter's own routing choices. The check is single-pool only.

## Sizing at the observed tiers (`p07_sizing_curves.json`)

| Pool | Round-trip loss at small size | Entry impact at 100 SOL | Largest buy with exit impact <= 3% | <= 10% |
|---|---|---|---|---|
| 5wNu5Qhd (0.30%) | 0.60% | 1.49% | about 235 SOL | about 911 SOL |
| 3KFCgJ5R (0.55%) | 1.10% | 4.48% | about 65 SOL | about 271 SOL |
| Cb7ZRgPL (1.25%, PUMP-quoted) | 2.48% | n/a | about 1.02M PUMP | about 5.5M PUMP |

These pools were among the largest PumpSwap pools in the corpus; most corpus pools are far smaller.
