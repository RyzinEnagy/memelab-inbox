# Gaps (Phase 01 summary)

Full row-by-row status: [REQUIREMENTS_MATRIX.md](REQUIREMENTS_MATRIX.md). Data sources and cost: [DATA_FEASIBILITY.md](DATA_FEASIBILITY.md). Design: [ARCHITECTURE_DECISION.md](ARCHITECTURE_DECISION.md).

## What the lab already does well (reuse, do not rebuild)

- Mint-keyed identity, fatal-flag override and a transparent 100-point score.
- Present-tense executable depth from router quotes at eight sizes, sizing under risk and liquidity limits, exit ladders.
- In the social layer: a cutoff clock with leakage audit, chronological splits with embargo and a label gate, a hash-chained append-only ledger, Wilson and order-statistic intervals with Bonferroni correction.
- In the catalyst layer: separate published, first-seen and retrieved times, revisions, publisher-level corroboration, Firecrawl reads with robots checks and credit caps.
- A survivorship-safe discovery universe in git history (1,801 distinct theses and 1,014 rejections across 89 exports).

## What is missing (must be built)

1. Point-in-time core: available_at and decision_time on core observations; a bar-close filter; append-only enforcement (Phase 05).
2. Stored historical bars with provenance and gap semantics (Phase 06).
3. Any reserve-based execution math; pool-type awareness; fee stack including Token-2022 and network fees; route aggregation without double counting (Phase 07).
4. Mechanical, bar-close-safe TA signals with explicit decision and execution times (Phase 08).
5. Catalyst signals that use first-known time and origin dedup, with placebo controls (Phase 09).
6. An event-driven portfolio ledger with order lifecycle and gap-through stops (Phase 10).
7. Walk-forward with sealed test and overfit controls for this engine (Phase 11).
8. Per-opportunity stress with size-specific proceeds and max size (Phase 12).
9. The hook, report section, CLI and outcome tracker (Phases 13 to 15).

## Defects found in existing code that the engine must not inherit

C1 transfer-fee key never written (m06/m17), C2 unfinished bar read by m13, C3 result `_at` earlier than contained rows, m14/m22 window-key mismatch, m26 percent-vs-fraction impact, catalyst assess pre-publication price up to one hour after publication, alpha_core OPEN rule entry from a bar that started before t0. The engine re-derives what it needs instead of reusing these outputs for historical decisions. Fixing them in place would change scoring, which is outside this project (D-BT-006).

## External blockers

Historical reserves/ticks/bins and historical swaps (need Helius key or archival source): exact historical fills BLOCKED; LIQ_SNAPSHOT_APPROX and QUOTE_OBSERVED tiers only. Social credentials: not needed for the first engine. Universe span only 17 days: statistics will be wide or abstain.
