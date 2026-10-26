# Engine runs on the real corpus (Phase 10)

Not validation. These runs show that the replay works end to end on real data and what the default assumptions do; statistical claims come only from Phase 11's sealed test window. Command per strategy: `python -m memelab backtest run --strategy <ID> --label phase10-all` (CATALYST_VERIFIED with `--params '{"min_origins": 1}'`, since each launch record is one origin). Output with run ids, ledger and dataset hashes: `p10_runs.json`.

Assumptions (EngineConfig defaults): account 10,000 USD, 500 USD per entry, at most 5 positions and 50% exposure, 2 entries per token, 6 h cooldown, 5 s latency, entry at the next bar open, orders expire after 2 bars, entry impact cap 3%, fills priced from the lab's own liquidity observations (valid 3 days, 0.8 haircut), fees per pool from `execution.assumed_swap_fee` (PumpSwap 1.25%), network fee 0.000105 SOL at the stored SOL/USD price, crash-through-stop bars filled at the close. Theses are known at the lab's record time.

| Strategy | Trades | P&L (USD) | Mean return per trade (realizable) | Mean paper return at mid | Win rate |
|---|---|---|---|---|---|
| LAB_STATUS | 26 | -509 | -3.9% | -1.2% | 35% |
| BREAKOUT_CLOSE | 47 | -3,164 | -13.5% | -3.0% | 21% |
| BREAKOUT_RETEST | 34 | -1,922 | -11.3% | -3.3% | 29% |
| RECLAIM | 42 | -4,303 | -20.5% | -6.4% | 26% |
| TREND_HHHL | 21 | -3,602 | -34.3% | -9.4% | 14% |
| ABSORPTION_BREAK | 22 | -3,293 | -29.9% | -1.9% | 18% |
| MOMENTUM | 47 | -3,322 | -14.1% | -2.4% | 23% |
| CATALYST_VERIFIED (min_origins 1) | 2 | +349 | +34.9% | +40.8% | 2 of 2 |
| NO_TRADE | 0 | 0 | | | |
| ENTER_AT_DISCOVERY | 36 | -2,391 | -13.3% | -10.3% | 28% |
| RANDOM_ENTRY | 80 | -7,410 | -18.5% | -4.2% | 21% |
| MA_CROSS | 51 | -4,043 | -15.9% | -2.6% | 20% |

What this shows:

- The gap between paper return at mid and realizable return is large for every TA strategy (for ABSORPTION_BREAK -1.9% on paper, -29.9% after fees and modeled impact). Small, thin pools plus a 1.25% fee on each side eat most setups (G35 on real data).
- Every TA strategy and every active baseline lost money over these 17 days. LAB_STATUS lost least. Nothing here is evidence of an edge; the sample is short and overlapping.
- CATALYST_VERIFIED made 2 trades. 9 of its 11 signals were canceled for lack of a liquidity observation at that time: the lab records liquidity only when it writes a thesis, so the catalyst path can only fill on tokens the lab also analyzed. That is a selection effect, so the two winning trades mean nothing on their own. The Phase 09 event study (entry at the bar open after detection, no liquidity requirement) found the opposite picture: median -92% at 24 h.
- Abstain and cancel counts are in `p10_runs.json`: most TA signals on non-CPMM pools are canceled UNSUPPORTED_POOL, and many fail for INSUFFICIENT_EXECUTION_DATA (no recent liquidity observation).
