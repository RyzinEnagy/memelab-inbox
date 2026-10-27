# Prospective plan: outcome tracking, prospective replay and model refresh

Written 2026-10-27 with `../ACCEPTANCE_CHECKLIST.md` and PI-D-104, before any Phase 19 code, prediction or prospective read. The checklist's rules are the binding text; this file explains the plan and what happens after this phase.

## What is evaluated now

- Window: decisions of the state exports on `origin/main` up to `71fc50e` (2026-10-24, -25 and -26) with decision time from 2026-10-24T00:00:00Z: 52 events, 33 Solana (scored population), 19 EVM (out of scope, kept in the ledger).
- Predictions: the 69 frozen holdout-start cards (cutoff 2026-10-17T00:00:00Z) and 20 NC1 controls per target, made and committed before any label read. The registry's references B0 and B2 also enter the outcome ledger as PREDICTION entries (internal, `published: false`).
- System output: the 156 ABSTAIN documents and their records from the integration-1 replay of the window, byte-equal to the Phase 18 published run, in the ledger before any label read.
- Outcomes: labels-1 on reads made after the predictions commit; one outcome per decision and target with its state; T2 of the 2026-10-26 decisions stays PENDING until 2026-10-28 about 10:28Z.
- Expected verdicts: INSUFFICIENT_DAYS (3 decision days, minimum 5) and below 50 events for every target. Nothing is promoted, calibrated or published.

## Later maturity runs (append-only)

1. Each later session that has new matured outcomes for already predicted decisions runs `probes/run_prospective.py outcomes` again: PENDING outcomes are superseded by new OUTCOME entries (`supersedes`), nothing is edited; the evaluation is rerun and its outputs are written under a new dated folder, never over the committed ones.
2. New decisions (exports from 2026-10-27 on) need their own predictions commit before their labels are read: `run_prospective.py inputs`, `predict` and `documents` at a new REF, a new PREDICTION_SET entry, a commit, then the reads. A decision after 2026-10-31T00:00:00Z is MODEL_STALE for every frozen card (no number), so the frozen cards can add at most the decisions of 2026-10-27 to 2026-10-30.
3. The frozen 48 h re-read (PI-D-018) of at least 10% of this phase's label reads is owed from 2026-10-29 (48 h after the reads); a changed label is a revision entry with `revision_of`, both kept.
4. The verdicts can leave INSUFFICIENT_DAYS only with at least 5 decision days and 50 events with 10 per class per target. At the lab's current rate (about 10 Solana decisions a day, fewer after thinning and eligibility) that needs several weeks of decisions, which the frozen cards cannot cover (MODEL_STALE after 2026-10-31).

## Refresh plan (model staleness and drift)

- No automatic retraining (PI-D-005: no scheduled job is approved). A retrain is a phase step: a plan committed before its evaluation data are read, cards fitted only through `labels.training_labels` (DEVELOPMENT rows matured by the new cutoff), registered as new registry entries at ABSTAIN (registry-1), with the new configurations added to the search ledger (N_search grows).
- Version pinning: every card keeps its file sha256, model sha, feature set sha, labels version and code-file hashes (registry `code`); a change in any of them is MODEL_INCOMPATIBLE_RETRAIN_REQUIRED (P46). Pins resolve as of the decision time, so an older decision keeps the pin it had.
- Promotion: only through `registry.promotion_decision` from committed facts, and only after a change control to ACCEPTANCE `promotion` decided by Elving or the orchestrator (PI-D-091), registered before the prospective labels it would use are read. A human reviews the registry entry, the prospective evaluation and the drift report before any pin; no level is set by hand.
- Drift: a DRIFT_ALERT never retrains anything; it demotes, rolls back or keeps abstention (checklist rule 10) and is recorded. Reviewing it is a person's job; the notice says what moved and on how many events.
- Reference cards after 2026-10-31: the prospective comparison of B0 and B2 needs retrained reference cards from a committed plan (Phase 16 constraint); until then the window above is the whole prospective record of the frozen cards.

## What is not tracked, and why

- Liquidity drawdown, exit capacity, catalyst follow-through and distribution outcomes: their targets are proposals, not frozen (PI-D-044, PI-D-055, PI-D-058). The forward depth collector (feature/backtesting D-BT-034, repaired D-BT-035) is built and pushed but not deployed on Elving's computer; the hourly task (2026-10-26) runs four steps without `collect`. No depth snapshot exists for this window, so every size or exit question is EXECUTION_DATA_MISSING and the status is COLLECTOR_NOT_DEPLOYED.
- Catalyst and social tables are not exported (CATALYST_TABLES_NOT_EXPORTED, SOCIAL_TABLES_NOT_EXPORTED); no catalyst outcome exists.
- Behavioral scenarios: MIROFISH_NO_GO; nothing to track.
