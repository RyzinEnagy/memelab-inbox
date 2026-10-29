# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-112). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_20/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-29

- Phases 00 to 13 and 16 to 18: PASS. Phases 14 and 15: TEST_ONLY (behavioral path, optional, OFF).
- Phase 19: PASS (2026-10-29). G25, the frozen 48 h revision re-read, ran with 0 revisions and 0 label changes; the provisional marking of PI-D-106 is lifted (PI-D-112).
- Phase 20 (independent adversarial integration and scientific audit): **NEEDS_REVIEW**, pending the orchestrator's independent skeptic (PI-D-013). No CRITICAL finding; the two MATERIAL findings are repaired (CP20-1, PI-D-110); result PI-D-111.
- Spend: 0. No vendor or language-model call in Phase 20; free PyPI downloads for the fresh-environment check only.

## What Phase 20 did

- Pre-registered the audit (`phase_20/ACCEPTANCE_CHECKLIST.md`, G1 to G17, severity classes, cross-component scenarios) at `9e1f29d`, froze the audit code at `0d66379` (no lab module changed), ran and committed every recorded run at `67acbc3`, then wrote change control CP20-1 and repaired at `5ebce8a`.
- P01 to P48: an own executable check each (`phase_20/probes/scenarios.py`, one process, sockets refused, raw JSON in `qa/raw/`), 229 of 229 gating assertions, 232 mapped test cases (`qa/SCENARIO_MATRIX.csv`). 39 of 39 recorded counterexamples caught (`qa/COUNTEREXAMPLES.csv`). Cross-component scenarios X01 to X06 with controls (`tests/test_predictive_phase20_cross.py`).
- Independent recalculation with own code: 61 of 61 prospective and 40 of 40 development labels, 28 decision keys, 168 of 168 reference numbers, two real events traced end to end.
- End to end: release_e2e 78 of 78; the Phase 17 real-path smoke under `unshare -n`; flag-off identity against `b0fad12` 12 of 12; fresh venv with numpy and pytest only; single-branch release audit exit 0; the reproduction entry points of Phases 05 to 19 (`qa/FULL_E2E_LOG.md`).
- Claims: `qa/SCIENTIFIC_CLAIMS_AUDIT.md` (no claim of skill, edge, calibration or profit; sensitivity changes no verdict). Package checklist: `qa/COMPLETION_CHECKLIST_AUDIT.md` (15 MET, 2 MET_WITH_LIMIT, 2 MET_TEST_ONLY, item 20 NOT_MET as Phase 21's release memo).

## Findings (`phase_20/qa/INDEPENDENT_FINDINGS.md`)

- CRITICAL: none.
- MATERIAL, repaired at `5ebce8a`: F20-02 (export replay accepted a token row of another mint; now NOT_EXACT_IDENTITY, TOKEN_ROW_OF_ANOTHER_IDENTITY) and F20-06 (a card trained on labels maturing after its cutoff was pinned and published on a fixture; now PinRefused and blocked by `serve`, TRAINING_ROWS_AFTER_CUTOFF). Both were latent: no champion exists.
- MINOR, repaired with them: F20-03 (CAPTURE_TIME_REFUSED instead of an exception), F20-08 (the carried Phase 18 minor 5: the reader recomputes a FORECAST's raw number, point and interval).
- MINOR, open with a recommendation: F20-01, F20-04, F20-05, F20-07, F20-09 to F20-14 (see the ROADMAP's Phase 20 constraints).

## Open items, in order

1. The orchestrator's independent skeptic of Phase 20 (`phase_20/SKEPTIC_PACKET.md`). Phase 20 stays NEEDS_REVIEW until it has run and its findings are handled.
2. Done 2026-10-29: G25 of Phase 19 (0 revisions, PI-D-112). Next for that line: F20-04 (parse the token parameter in `monitoring.check_payload`) under its own change control.
3. After 2026-10-28 10:30Z: the maturity run for the 7 PENDING T2 outcomes (Phase 19 HANDOFF steps in `phase_19/monitoring/PROSPECTIVE_PLAN.md`).
4. Phase 21 (research-only release or explicit NO-GO): the honest classification on the evidence is a research-only abstention engine, no validated or shadow model; carry F20-11 (loopback) and F20-14 (drift appends to the ledger) into the install runbook; F20-01, F20-05, F20-07 need a change control that reruns the Phase 17 smoke and the Phase 18 goldens if they are to be closed.
5. Carried: catalyst and social tables are not exported; forward depth collection approved but not deployed (PI-D-044); keep `tests/test_predictive_reproductions.py` green; a merge of the backtesting PR #4 needs the steps in `phase_17/integration/REQUEST_FLOW.md`; any external alert delivery needs Elving's approval.

## Phase 20 commits

HEAD before `e0bc906`; pre-registration `9e1f29d`; frozen audit code `0d66379`; recorded runs `67acbc3` (with PI-D-110); CP20-1 code `5ebce8a`; records and the post-commit record after them (`phase_20/postcommit/`). Local only; the orchestrator pushes.

## Waiting on Elving

- The change control that could reopen promotion (ACCEPTANCE `promotion`), any paid data, LLM, Zep or MiroFish use, any external alert delivery (Telegram or email), scheduled catalyst or social collection into a store this engine can read, a merge of the backtesting PR #4 into this line, a merge into `main`, deploying the forward depth collector (approved, PI-D-044; not yet done), turning the flag on anywhere outside a sandbox, and a signing key for the private state if the residual of F20-08 is to be closed.

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (a reviewed false positive on that branch, D-BT-016; PI-D-049 item 6). It is not reachable from `feature/predictive-intelligence`, whose own audit passes on a single-branch clone.

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no recovery words or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flag overrides unchanged. Forecasts stay a separate evidence section with the flag OFF by default. No raw social content in the repository. Behavioral output is fictional, never a probability. References are never forecasts. Alerts are previews in a local outbox; nothing is sent.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git fetch origin main && git log -8 --oneline
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
python -m pytest tests/test_predictive_phase20_cross.py -q -rxX
python -B audits/predictive-intelligence/phase_20/probes/scenarios.py P01
python -B audits/predictive-intelligence/phase_20/probes/run_matrix.py /tmp/p20_matrix
python -B audits/predictive-intelligence/phase_20/probes/cx_rerun.py /tmp/p20_cx
```

Use a full clone (the commit-order tests of Phases 15 to 19 need the history). Expect `"problems": []` from the seal check and, in the suite, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` and `tests/test_catalyst_firecrawl.py::test_page_history_and_spend_survive_a_new_session_through_the_state_export` (real clock) failing, and 2 strict xfails (F20-04); then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The reproductions need the private stores of Phases 05 and 06 under `/home/claude/pi_research/` (rebuildable from the committed archives). The flag-off, smoke and fresh-environment scripts need `unshare`.
