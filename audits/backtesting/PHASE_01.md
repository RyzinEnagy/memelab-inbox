# PHASE 01: gap-to-requirements and integration placement

State: PASS. Date 2026-10-23. Entry gate: Phase 00 PASS re-verified (`python audits/backtesting/testing/p00_counterexamples.py` exit 0 at 912fc96).

## Deliverables

- REQUIREMENTS_MATRIX.md: data contracts and G01 to G41 against the code, with owners.
- GAPS.md: reuse list, missing list, defects the engine must not inherit, external blockers.
- ARCHITECTURE_DECISION.md: package layout, verified seam (`analyze_token` result in `cli.cmd_scout`/`cmd_analyze`), sequence diagram, dependency graph, sync vs deferred stages with budgets, evidence tiers, execution fidelity ladder, migration policy, operator controls, scoring preservation, crawler and Maxun placement.
- DATA_FEASIBILITY.md: ranked data/expense matrix with a live GeckoTerminal probe (data/p01_gt_probe.json).
- research/RUBRIC_LOCK.md (R1.0 locked before scoring), research/CRAWL_POLICY.md.

## Gate

| Item | Result |
|---|---|
| Every downstream function has a real seam | yes: section 2 and 4 of ARCHITECTURE_DECISION, seam lines verified in cli.py and pipeline.py |
| Every data need has a feasibility status | yes: DATA_FEASIBILITY (AVAILABLE / PARTIAL / BLOCKED) |
| No framework chosen before research | yes: engine choice deferred to Phases 03/04 |
| Scoring preserved | yes: section 10 |
| Rubric locked before scoring | yes: R1.0 |

## Negative review (testing/logs/p01_negative_review.log)

1. Plausible claim: "today's top GeckoTerminal pool is the pool the lab saw at decision time." Checked on 7 probed mints: not contradicted in this sample (0 of 7). Kept as a rule anyway: the pool basis must have pool_created_at <= decision_time (test in Phase 06).
2. Plausible claim: "the latest `data/state/latest.json` export holds the full thesis history." Contradicted: the latest export has 701 theses; the union across 89 commits has 1,801 distinct (mint, created_at) theses; 1,100 exist only in older commits. A universe built from the latest file alone would drop 61% of decisions. The Phase 06 adapter must walk git history.

## Not proven

Exact historical fills (BLOCKED, no reserves source). Real catalyst history depth (thin). Maxun runs (06A).

NEXT ELIGIBLE PHASE: 02.
