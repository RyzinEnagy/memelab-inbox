# PHASE 07: execution-aware DEX AMM simulation and capacity

State: PASS. Date 2026-10-23. Entry gate: Phase 06A PASS at db91542 (webcapture tests 20 passed, 06A mutations 9/9, full suite on the clean commit 1 failed C-1 only / 837 passed, release e2e PASS 78/78).

## Changed files

- New: `memelab/backtest/execution.py` (versioned cost model `cost-1`: Fees with each component applied once, exact CPMM float and integer forms, invariant guard, PumpSwap effective reserves, liquidity-snapshot approximation with haircut, observed-quote curves with freshness and no extrapolation, multi-pool buy and sell routing without double counting, partial and failed legs, impact caps, round trip, max size, sizing curves, pool classification ladder, time-indexed state, USD conversion that refuses missing rates, P&L in two denominators, per-DEX fee defaults).
- New tests: `tests/test_backtest_execution.py` (15: G09-G17, G29, PumpSwap effective reserves, snapshot labeling, live-quote fixture checks, fee defaults).
- Evidence: `audits/backtesting/execution/SPOTCHECK.md`, `p07_spotcheck.py`, `p07_spotcheck.json`, `p07_sizing_curves.json`; fixture `tests/fixtures/backtest/real/pumpswap_spotcheck.json`; `testing/p07_mutations.json`, `testing/logs/p07_mutations.log`.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_backtest_execution.py -q` | 0 | 15 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p07_mutations.json` | 0 | 14 of 14 caught |
| `python audits/backtesting/execution/p07_spotcheck.py 5wNu5Qhd... 3KFCgJ5R... Cb7ZRgPL...` | 0 | 9 buys and 3 sells, all routed through the named pool; model within 0.02% at the pool's tier |

## Gate

G09 hand calculation and no free money; G10 size-dependent fills; G11 CLMM/DLMM/bonding curves never priced as x*y=k, even with vault balances; G12 state at execution time; G13 route failure and impact cap (PARTIAL, never phantom); G14 fee stack once; G15 quote freshness (future and stale quotes refused, no extrapolation above the largest quoted size); G16 denominators (each leg at its own USD rate, missing rate raises); G17 take-profit mark above realizable exit; G29 float vs integer reference. All pass. No impossible fills: the invariant check raises on any decrease of x*y, and reserves can never go non-positive.

## Bounded loop

Pass 1: mutation M07-5 (CLMM with known vault balances priced as constant product) survived; G11 now also covers pools with balances. Caught.
Pass 2 (adversarial, live data): the spot-check showed the 0.25% default fee was optimistic for every PumpSwap pool tested (0.30% to 1.25%) and that vault-only reserves misprice pools with large virtual reserves. Repair: per-DEX conservative fee defaults with labels, a fee override per token in the engine, and two fixture tests from the live quotes. Mutations M07-13 (virtual reserves dropped) and M07-14 (optimistic default) caught.

## Independent negative review

Wrong-but-plausible outputs and the test that catches each: double fee (M07-1), transfer fee ignored (M07-2), quote from the future (M07-3), stale quote (M07-4), CLMM as CPMM (M07-5), failed legs counted (M07-6), no exit impact cap (M07-7), rounding in the user's favor (M07-8), pool state after the execution time (M07-9), exit at the entry USD rate (M07-10), missing rate treated as 1 (M07-11), extrapolating quotes (M07-12), dropping virtual reserves (M07-13), optimistic fee default (M07-14).

## Limitations

Exact historical fills stay BLOCKED (no reserve history). Historical runs use LIQ_SNAPSHOT_APPROX from the lab's own liquidity observations with a 0.8 haircut and the conservative fee; this approximation was checked only against present-day pools. CLMM, DLMM and bonding-curve pools are UNSUPPORTED_POOL for historical fills. Sell-side fee placement (input vs output) differs by under 0.01% at the sizes checked and is not modeled separately.

NEXT ELIGIBLE PHASE: 08.
