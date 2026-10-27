# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-108). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_19/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-27

- Phases 00 to 13 and 16 to 18: PASS. Phases 14 and 15: TEST_ONLY (behavioral path, optional, OFF).
- Phase 19 (outcome tracking, prospective replay and drift): **NEEDS_REVIEW** after repair pass 2 (CP19-1 PI-D-107, result PI-D-108) with one open gate item, G25: the frozen 48 h revision re-read (PI-D-106), due from 2026-10-29T14:35Z and run by the orchestrator. Every Phase 19 outcome and number is PROVISIONAL_PENDING_REVISION_REREAD. Phases 20 and 21 may proceed on Elving's instruction (PI-D-106 item 3).
- The independent skeptic (`phase_19/skeptic/PHASE_19_SKEPTIC.md`) found 2 MATERIAL (M1 the re-read scoped out of the gate; M2 nine non-equivalent mutation survivors), 7 minor and CX-SK19 (a revision citing the read it revises); all reproduced and repaired at `7c177de`; no primary number or verdict changed.
- Spend: 0 Firecrawl credits, 0 language-model calls; 44 free GeckoTerminal calls, all after the predictions commit.

## What Phase 19 built

- `memelab/predictive/monitoring.py` (monitoring-1), imported by no module: the outcome ledger `outcome-ledger-1` (append-only, sha-chained; a prediction or document is written once and never after its outcome, CX-19; a final outcome is revised only with `revision_of`, both kept; `load` and `verify` replay every rule), prospective outcomes through labels-1 (`labels.build` then `labels.classify`), drift monitors D1 to D8 with thresholds frozen in the checklist, the response policy (DEGRADE_TO_SHADOW, ROLLBACK_TO_ABSTAIN, KEEP_ABSTAIN, KEEP_ABSTAIN_SOURCE; never a retrain) and plain notices.
- Probes: `phase_19/probes/run_prospective.py` (inputs, predict through the unchanged Phase 12 step, outcomes, evaluate, drift, rollback, audit, report), `fetch_labels.py` (opening check, paced reads), `rebuild_outcomes.py` (offline rebuild from the archive), `mutation_monitoring.py` (46 of 46), `contact_scan.py`.
- Deliverables: `phase_19/monitoring/OUTCOME_LEDGER.md` (and `.jsonl`), `PROSPECTIVE_REPORT.md` (the calibration report: leakage tests, historical out-of-sample record and prospective shadow accuracy kept apart), `DRIFT_REPORT.json`, `ROLLBACK_DEMO.json`, `MISSES.csv`, `PROSPECTIVE_PLAN.md` (later maturity runs, refresh plan with human-reviewed promotion and version pinning); tests `tests/test_predictive_monitoring.py` (30) and `tests/test_predictive_phase19_outputs.py` (7).

## Results (PI-D-105)

- Window: exports to `71fc50e`, 52 decisions from 2026-10-24T00:00Z, 33 Solana. Predictions (69 frozen cards and 20 NC1 seeds per target, 4,257 rows) and the 156 ABSTAIN documents committed at `765eadb` before any read; the documents are byte-equal to the Phase 18 published run.
- Outcomes: T1 22 labelled (5 positive), T1b 24 (3), T2 15 (3); T2 of the 2026-10-26 decisions PENDING (7, mature 2026-10-28 about 10:28Z); offline rebuild equal for 156 of 156.
- Every verdict INSUFFICIENT_DAYS (3 decision days, 2 for T2; minimum 5) and below 50 events: no claim, no promotion, no calibration. The B2 against B0 point estimates (BSS T1 +0.264, T1b +0.033, T2 +0.419) are descriptive only.
- Drift (after CP19-1): SUPPORT_BELOW_MINIMUM for every target; D1 INSUFFICIENT_DATA (1 of 5 columns measurable); D6 COLLECTOR_NOT_DEPLOYED (0 of 28 planned decisions without a usable read; 11 of 39 attempts retried, reported); the rest OK or INSUFFICIENT_DATA. Response KEEP_ABSTAIN everywhere (first pass: KEEP_ABSTAIN_SOURCE from the attempt-based D6). CONTACT_EXCLUDED now also drops 9aqmJj (n 17, 17, 11). The champion drift response and rollback are fixtures only (TEST_ONLY).
- CP19-1 rules: a revision or supersede must cite a later, different read (REVISION_NEEDS_A_LATER_READ, in `append`, `load` and `verify`); the outputs tests anchor the ledger and manifest in git history and rebuild the outcomes from the archive; mutation probe 71 of 71.
- Forward depth collector (feature/backtesting D-BT-034, D-BT-035): not deployed on Elving's computer; no depth snapshot exists, so depth, liquidity, catalyst and distribution outcomes are not reconciled.

## Open items, in order

1. G25 (PI-D-106): from 2026-10-29T14:35Z the orchestrator runs `python -B audits/predictive-intelligence/phase_19/probes/fetch_labels.py reread48` (network, 3 calls; refuses earlier). No label change: record it, lift PROVISIONAL_PENDING_REVISION_REREAD and set Phase 19 PASS. A label change: the revisions are appended by the command, then `run_prospective.py evaluate|drift|report audits/predictive-intelligence/phase_19/monitoring/after_reread48` under `unshare -n`, and record the result.
2. After 2026-10-28 10:30Z: a maturity run supersedes the 7 PENDING T2 outcomes (append only, citing the new read): `fetch_labels.py open`, `fetch` (it plans the T2 boundary), `archive`, then `run_prospective.py outcomes`.
3. Decisions from the 2026-10-27 to 2026-10-30 exports can still be scored by the frozen cards (stale after 2026-10-31) only with their own predictions commit before their reads (`monitoring/PROSPECTIVE_PLAN.md`).
4. Carried to Phase 20: Phase 18 minor 5 (recompute a FORECAST point in a reader allowed to import the calibration module, or sign the state).
5. If Elving wants a promotion path: the change control to ACCEPTANCE `promotion` (PI-D-091), registered before the prospective labels it would use are read.
6. Carried: catalyst and social tables are not exported; forward depth collection approved but not deployed (PI-D-044); keep `tests/test_predictive_reproductions.py` green; a merge of the backtesting PR #4 needs the steps in `phase_17/integration/REQUEST_FLOW.md`; any external alert delivery needs Elving's approval.

## Phase 19 commits

HEAD before `4b07b0d`; pre-registration `5ffa5cf`; frozen code `fce102e`; predictions `765eadb`; reads, outcomes and outputs `b1a18f7`; records `aefbea6`; post-commit at `aefbea6`: suite `2 failed, 2182 passed, 1 skipped` (the two known clock-dependent failures only), guard 0 violations, seal check 0 problems, single-branch release audit exit 0 "Needs action: no." (`phase_19/postcommit/`); post-commit record `6258fc0` (pushed). Repair pass 2: decisions and frozen sample `c7e3c25`, CP19-1 code `7c177de`, repeated runs `bb2639a`, records and the post-commit record after them (`phase_19/postcommit/rp2_*`). Local only; the orchestrator pushes.

## Waiting on Elving

- The change control that could reopen promotion (ACCEPTANCE `promotion`), any paid data, LLM, Zep or MiroFish use, any external alert delivery (Telegram or email), scheduled catalyst or social collection into a store this engine can read, a merge of the backtesting PR #4 into this line, a merge into `main`, deploying the forward depth collector (approved, PI-D-044; not yet done), and turning the flag on anywhere outside a sandbox.

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (a reviewed false positive on that branch, D-BT-016; PI-D-049 item 6). It is not reachable from `feature/predictive-intelligence`, whose own audit passes on a single-branch clone.

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no seed phrases or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flag overrides unchanged. Forecasts stay a separate evidence section with the flag OFF by default. No raw social content in the repository. Behavioral output is fictional, never a probability. References are never forecasts. Alerts are previews in a local outbox; nothing is sent.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git fetch origin main && git log -8 --oneline
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
python -m pytest tests/test_predictive_monitoring.py tests/test_predictive_phase19_outputs.py -q
python -c "from memelab.predictive import monitoring as M; print(M.verify('audits/predictive-intelligence/phase_19/monitoring/OUTCOME_LEDGER.jsonl'))"
unshare -n python -B audits/predictive-intelligence/phase_19/probes/rebuild_outcomes.py /tmp/p19_rebuild.json
python -B audits/predictive-intelligence/phase_19/probes/mutation_monitoring.py /tmp/p19_mut.json
```

Use a full clone (the commit-order tests of Phases 15 to 19 need the history). Expect `"problems": []` from the seal check and, in the suite, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` and `tests/test_catalyst_firecrawl.py::test_page_history_and_spend_survive_a_new_session_through_the_state_export` (real clock) failing; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The input and prediction steps need the private stores of Phases 05 and 06 under `/home/claude/pi_research/` (rebuildable from the committed archives).
