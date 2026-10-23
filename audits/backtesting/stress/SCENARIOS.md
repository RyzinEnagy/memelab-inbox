# Stress scenarios on two real present-day pools (Phase 12)

Snapshots built from the Phase 07 live spot-check (on-chain effective reserves, each pool's observed fee tier, one observed Jupiter sell quote) and SOL at 104.21 USD. Liquidity is twice the quote side. Invalidation set at -20% for the purpose of the FAILED_BREAKOUT shock. Script: `python audits/backtesting/stress/p12_scenarios.py` (output `p12_scenarios.json`). Every shock is hypothetical and has no probability attached.

Return after all costs, per size (USD):

| Scenario | 5wNu5Qhd (0.30% fee, 1.75M USD liquidity) $500 / $5k / $25k / $100k | 3KFCgJ5R (0.55% fee, 0.53M USD) $500 / $5k / $25k / $100k |
|---|---|---|
| BASE (exit right away) | -0.7% / -1.7% / -5.9% / -19.0% | -1.5% / -4.7% / -16.7% / -43.4% |
| LIQ_50 | -0.8 / -2.3 / -8.4 / -25.9 | -1.7 / -6.3 / -22.7 / -53.3 |
| LIQ_75 | -0.9 / -3.3 / -13.0 / -36.6 | -2.0 / -9.5 / -32.5 / -65.5 |
| STOP_GAP (40% gap) | -40.4 / -41.0 / -43.2 / -50.4 | -40.9 / -42.6 / -49.1 / -64.3 |
| DELAYED_EXIT (30 min, -20%, liquidity -30%) | -20.6 / -21.5 / -25.3 / -36.8 | -21.2 / -24.1 / -34.7 / -57.2 |
| ATTENTION_COLLAPSE | -50.4 / -51.1 / -53.9 / -62.2 | -50.8 / -53.0 / -60.7 / -75.7 |
| VOLUME_GONE (liquidity -90%) | -1.2 / -6.4 / -24.2 / -55.8 | -3.1 / -17.9 / -51.1 / -80.6 |
| SOL_DOWN_30 | -30.5 / -31.2 / -34.2 / -43.3 | -31.0 / -33.3 / -41.7 / -60.4 |
| CONGESTION (fees x200, 3 failed exits) | -2.9 / -1.9 / -6.0 / -19.0 | -3.6 / -4.9 / -16.7 / -43.4 |
| COMBINED_WORST | -37.5 / -38.8 / -43.8 / -57.0 | -38.2 / -42.0 / -54.6 / -75.0 |
| HONEYPOT | -100 at every size | -100 at every size |
| QUOTE_DEPLETION | -100 at every size (see note) | -100 at every size |

Max size with a 1,000 USD loss cap under BASE, LIQ_50 and STOP_GAP and a 5% base exit impact: about 2,460 USD and 2,404 USD. Both pools came out RESEARCHABLE (execution is feasible at small sizes); the tables show the downside, not a forecast.

Notes:

- INSIDER_DUMP equals BASE here because these snapshots carry no holder concentration. The engine records "insider share unknown: not modeled (not assumed zero)" rather than treating it as zero.
- QUOTE_DEPLETION is measured against the largest size that had a working sell quote. These snapshots carry one quote of about 52 USD, so every requested size is above it. With the lab's normal quote ladder the shock bites only above the largest size the router could fill.
- FREEZE and MINT_DILUTION are absent because both pools' mints have no freeze or mint authority (read on chain). They appear only when the authority exists.
- Realizable value is about 99.6% and 99.3% of marked value at the smallest size, and much less at larger sizes; marked value is never shown as cash.

## Historical cohorts (empirical, separate from the shocks)

`stress.empirical_cohort`, 24 h after the first bar that opened after each lab thesis, mid prices before costs, minimum 30 cases:

| Lab status at thesis | Cases | Result |
|---|---|---|
| ENTRY CONDITIONS MET | 0 | INSUFFICIENT_HISTORY |
| NEAR ENTRY | 8 | INSUFFICIENT_HISTORY |
| SETUP DEVELOPING | 27 | INSUFFICIENT_HISTORY |
| WATCH | 7 | INSUFFICIENT_HISTORY |
| REJECTED | 136 | 24 h return p10 -77.6%, median -4.5%, p90 +29.5%; worst drop p10 -93.0%, median -23.5% |

Only the REJECTED cohort is large enough to report. These are frequencies for past tokens the lab rejected, not probabilities for any token.
