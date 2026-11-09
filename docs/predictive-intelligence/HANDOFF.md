# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-114). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_20/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-11-09

- Phases 00 to 13 and 16 to 20: PASS. Phases 14 and 15: TEST_ONLY (behavioral path, optional, OFF).
- Phase 19: PASS since 2026-10-29 (G25: 0 revisions, 0 label changes, PI-D-112).
- Phase 20 (independent adversarial integration and scientific audit): **PASS** after the orchestrator's independent skeptic and repair pass 2 (CP20-2, PI-D-113; result PI-D-114). No CRITICAL finding; no MATERIAL finding open.
- Next eligible phase: 21 (reproducible research-only release or explicit NO-GO).
- Spend: 0. No vendor or language-model call in Phase 20 or its repair passes.

## What Phase 20 did

- Pre-registered the audit (`phase_20/ACCEPTANCE_CHECKLIST.md`, G1 to G17) at `9e1f29d`, froze the audit code at `0d66379`, recorded the runs at `67acbc3`, repaired its own MATERIAL findings under CP20-1 at `5ebce8a`.
- The orchestrator's skeptic (2026-11-09, `phase_20/skeptic/`) found a new variant of the Phase 18 CX-SK18 defect (CX-SK20: run-together multiplier symbols such as 100XGAIN printed in the report, alert and scout section), a bypass of the F20-02 repair through the pool field (S20-2), and F20-01 under-classified (S20-3), plus 9 MINOR items.
- Repair pass 2: change control PI-D-113 at `f5a174b`, code at `243cd32`: one token-text rule for all rendered token text and a multiplier rule in the report's final text check; the token row's pool bound to the exact mint before any read; fail closed on a fitted card without its maturity record; F20-04 (exact `token` parameter in the outcome ledger); probes P05, P10, P41, P43, P44 strengthened; flag-off script resolves its commit; `unpatched_severity` filled. Old-code check: the new tests fail at `b4d4768` (18 of 21; the 3 controls pass).
- Reruns at `243cd32` (`phase_20/evidence/repair2_rerun/`): cross tests 43 passed; 39 of 39 counterexamples; 48 scenario checks, 239 of 239 gating assertions; flag-off identity 12 of 12; release_e2e ok; real-path smoke unchanged apart from time fields; single-branch release audit exit 0; reproductions of Phases 05 to 19.

## Findings (`phase_20/qa/INDEPENDENT_FINDINGS.md`)

- CRITICAL: none.
- MATERIAL, all repaired and all latent (no champion exists): F20-02 and F20-06 (CP20-1); F20-01 (reclassified), CX-SK20 and S20-2 (CP20-2).
- MINOR repaired: F20-03, F20-08 (CP20-1); F20-04, F20-05, S20-4, S20-5, S20-6, S20-8, S20-10, S20-11 (CP20-2). Recorded: S20-7, S20-12, F20-09, F20-12.
- MINOR open for Phase 21: F20-07, F20-10, F20-11, F20-13, F20-14.

## Open items, in order

1. Phase 21 (research-only release or explicit NO-GO): the honest classification on the evidence is a research-only abstention engine, no validated or shadow model; carry F20-07, F20-10, F20-11 (loopback), F20-13 and F20-14 (drift appends to the ledger) into the install runbook or close them.
2. After 2026-10-28 10:30Z: the maturity run for the 7 PENDING T2 outcomes (Phase 19 HANDOFF steps in `phase_19/monitoring/PROSPECTIVE_PLAN.md`), if not yet done.
3. Carried: catalyst and social tables are not exported; forward depth collection approved but not deployed (PI-D-044); keep `tests/test_predictive_reproductions.py` green; a merge of the backtesting PR #4 needs the steps in `phase_17/integration/REQUEST_FLOW.md`; any external alert delivery needs Elving's approval.

## Phase 20 commits

HEAD before `e0bc906`; pre-registration `9e1f29d`; frozen audit code `0d66379`; recorded runs `67acbc3`; CP20-1 code `5ebce8a`; first-pass records `0b24539`; Phase 19 G25 `b4d4768`; CP20-2 change control `f5a174b`; CP20-2 code `243cd32`; repair pass 2 records and the post-commit record after it (`phase_20/postcommit/`). Local only; the orchestrator pushes.

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
python -m pytest tests/test_predictive_phase20_cross.py -q
python -B audits/predictive-intelligence/phase_20/probes/scenarios.py P01
python -B audits/predictive-intelligence/phase_20/probes/run_matrix.py /tmp/p20_matrix
python -B audits/predictive-intelligence/phase_20/probes/cx_rerun.py /tmp/p20_cx
```

Use a full clone (the commit-order tests of Phases 15 to 19 need the history). Expect `"problems": []` from the seal check and, in the suite, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` and `tests/test_catalyst_firecrawl.py::test_page_history_and_spend_survive_a_new_session_through_the_state_export` (real clock) failing; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The reproductions need the private stores of Phases 05 and 06 under `/home/claude/pi_research/` (rebuildable from the committed archives). The flag-off, smoke and fresh-environment scripts need `unshare`.
