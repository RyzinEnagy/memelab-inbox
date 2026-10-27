# Missing-data UX (report-1, Phase 18)

What a reader sees when a number, a source or a check is missing, and what would unblock it. Every line below is rendered by `memelab/predictive/reports.py` from the persisted state (the request record, the document and its abstention record); nothing is inferred from memory of a run. Tests: `tests/test_predictive_reports.py` (G10, G7, G15). The text in the third column is the report's own wording (`UNBLOCK` and `STATE_TEXT` in the code).

## Abstention reasons (one per contract reason, `contract.ABSTAIN_REASONS`)

Every abstaining target shows "ABSTAIN (no number)" in the at-a-glance table and in its opportunity's table, the reasons in contract order, the plain explanations taken from its abstention record, and one "What would unblock" line per distinct reason. No base rate, cohort number, reference-model number or score-like number is shown for it.

| Reason | Seen today on real data | What would unblock it (shown in the report) |
|---|---|---|
| MODEL_NOT_SELECTED | every target (Phase 16 NO_VIABLE_CHAMPION) | a champion pinned at SHADOW or VALIDATED_EXPERIMENTAL in the Phase 16 registry; that needs the ACCEPTANCE promotion change control (PI-D-091, Elving's decision) and admissible prospective evidence |
| UNCALIBRATED | every target (Phase 13) | a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence |
| INSUFFICIENT_HISTORY | every target | at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set |
| SOURCE_STALE | every target without a served champion (no reference-price read), and every stale capture | a fresh capture (inputs younger than 7,200 s) and one reference-price read on the point-in-time pool |
| TARGET_NOT_FEASIBLE | tokens without a point-in-time pool | a point-in-time pool recorded at the capture on the registered price route |
| OUT_OF_SCOPE_CHAIN | EVM tokens | the targets are defined for Solana only; another chain needs a change control and its own evidence |
| EXECUTION_DATA_MISSING | any size question | forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it |
| NOT_YET_MATURED, MODEL_STALE, DRIFT_ALERT, OOD, FEATURE_SCHEMA_MISMATCH, NO_RECENT_PRICE, OUT_OF_SCOPE_OPPORTUNITY_TYPE, UNVERIFIED_EVENT, RESTRICTED_SOURCE, FLAG_OFF | not on today's real data (fixtures) | one line each in `UNBLOCK` (for example MODEL_STALE: a model card retrained from a committed plan; frozen cards are stale after 2026-10-31T00:00:00Z) |

## States outside the reasons

| State | Where it shows | Text |
|---|---|---|
| FLAG_OFF | the command prints it and stops | the predictive flag is off: nothing was read or rendered |
| NO_STATE | report header | no predictive state exists yet: the scout has not run with the flag on |
| STATE_DIR_REFUSED | report header | the state directory is inside the repository and not under data/private/ |
| STATE_TAMPERED | report header; no opportunity and no number; one pipeline_health alert | the state files do not match their record ids or the pass chain: nothing is shown |
| STATE_CHECK_FAILED | at a glance; the documents named are refused | some documents are not paired with their records or requests: those documents are refused |
| DOCUMENT_REFUSED | the target's row says "REFUSED (no number)" and lists the failed checks | the document failed a check: it is not shown and no number is shown |
| INPUT_STALE | at a glance (Inputs column), identity and snapshot section | the inputs were older than 7,200 s at the capture |
| SNAPSHOT_NOT_VERIFIED | identity section; symbol shown as "symbol not verified"; age and lab labels UNKNOWN | no lab database row matches the snapshot hash: lab facts (age, symbol, labels) are unknown here |
| REGISTRY_UNAVAILABLE | at a glance and system status ("blocking at the pass") | the model registry could not be read or verified: every target abstains |
| REGISTRY_INDEX_MISMATCH | historical prediction section | the committed registry index does not match the pin the request recorded |
| COLLECTOR_NOT_AVAILABLE | execution and stress section (depth) | no forward depth collector rows: no size can be supported (EXECUTION_DATA_MISSING) |
| BACKTEST_NOT_AVAILABLE | at a glance, system status, execution and stress | the backtesting module is not installed on this line; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase |
| CATALYST_SOURCE_NOT_AVAILABLE | catalyst evidence section | the catalyst tables were not available to the pass |
| SIMULATION_NOT_AVAILABLE | at a glance, system status, every opportunity | MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs |
| Events not attempted (UNCHANGED, DUPLICATE, SUPERSEDED_IN_PASS, DEFERRED_QUEUE_FULL, DEFERRED_LATENCY_BUDGET, NO_DECISION_SNAPSHOT, NOT_EXACT_IDENTITY, ERROR) | the "Events not attempted" table, with whether a report above covers the token | never dropped; an inexact mint is printed as "not-an-exact-address" |
| Lab status with trade wording (NEAR ENTRY, ENTRY CONDITIONS MET) | structural research section, UNKNOWN bucket | kept in the lab's token report (its label uses trade wording) |
| Token text carrying a trading or forecast word | wherever the symbol, chain, labels or file name appear | withheld |
