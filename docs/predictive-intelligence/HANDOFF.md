# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-065). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_12/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-26

- Phases 00 to 11: PASS (Phase 06 since the frozen 48 h re-read, PI-D-059; Phase 10 with TEST_ONLY parts; Phase 11 after repair pass 2, PI-D-063).
- Phase 12 (walk-forward discipline, search discipline and the single evaluation of the sealed retrospective holdout): NEEDS_REVIEW, first pass done, awaiting the orchestrator's independent skeptic (PI-D-013). Commits: pre-registration `79d30f5`, frozen code `3ea7030`, pre-opening predictions `d58de61`, opening outputs `de7ac77`, results and records on top (see "Phase 12 commits").
- Spend: 0 Firecrawl credits, 0 vendor calls, 0 language-model calls, no network use in Phase 12.

## What Phase 12 did (PI-D-064, PI-D-065)

- Plan frozen before any code, prediction or opening (`phase_12/validation/WALK_FORWARD_PROTOCOL.md`): the 69 frozen holdout-start cards of Phases 07 to 11 as candidates (no refit, no tuning); champion per target by a rule on committed development verdicts (B2 unless a card earned `champion_over_B2`; none did, so B2 by default); primary B2 against B0, Brier skill with day and mint bootstrap (20,000 replicates, wider governs), Holm across the three targets, Phase 07's frozen verdict and the 50-event, 10-per-class gate; secondary family with Holm, a max-T day-block correction and a full-search Bonferroni (N_search 118 = 87 development configurations + 31 Phase 04 bake-off configurations); NC1, NC2, NC3 and P13 traps; sensitivities and dataset-shift breakdowns.
- `memelab/predictive/evaluation.py` (evaluation-1, numpy and the standard library, flag OFF, imported by no other module): seal-report check against the pins, `open_holdout` (logs the opening before decompressing; refuses a second first opening), `holdout_rows`, identity join, `check_card_time` and `score` (RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF, MODEL_STALE), `champion`, `holdout_verdict`, `max_t`, `bonferroni`, `ledger_totals`, `shadow_criteria`. 42 tests plus 5 output tests; mutation probe 44 of 44.
- Every holdout prediction (12,255 rows: 69 cards and 60 NC1 controls over the 95 Solana holdout decisions) was computed with no label and committed with its sha256 before the opening. The tech-1 cards have no inputs on the holdout (NOT_FETCHED_SEALED, no pool) and abstain.
- The seal was opened once (2026-10-26T17:33:27Z at `d58de61`, `OPENING_LOG.json`); a REPRODUCTION gave byte-equal outputs; scikit-learn recomputed 572 metric values within 1.1e-16; an independent check without the lab's code found the same 66, 68, 59 scored rows and labels.

## Result (empirical)

- T1 24 h: 66 events (15 positive), BSS of B2 against B0 -0.024, governing mint interval -0.156 to 0.134, Holm p 1.0: NOT_DISTINGUISHABLE_FROM_BASE_RATE.
- T1b 6 h: 68 (12), BSS -0.083, day interval -0.174 to -0.020, governing mint interval -0.168 to 0.002, Holm p 1.0: NOT_DISTINGUISHABLE_FROM_BASE_RATE; calibration in the large failed (mean 0.082, observed 0.176); WORSE_THAN_BASE_RATE in two sensitivities (contacted included, point-in-time route).
- T2 24 h: 59 (7), BSS +0.292 (mostly a lower holdout prevalence, 0.119 against 0.214): INSUFFICIENT_EVENTS; possible partial contact (PI-D-045 item 6).
- 0 of 129 secondary comparisons survive the selection correction; shuffled-label B2 matches the real B2 in 45% (T1) and 85% (T1b) of seeds. No model shows out-of-sample value; base rate or abstention; every complex model MODEL_NOT_PROMOTED; nothing reaches SHADOW. This is the outcome Phase 01 stated in advance.

## Open items, in order

1. The orchestrator runs the independent skeptic on Phase 12 (`phase_12/SKEPTIC_PACKET.md`), then a repair pass folds it in; only then can Phase 12 be PASS and Phase 13 start.
2. For Phase 13 and later: the retrospective holdout is spent (any reuse is EXPLORATORY); calibration work uses development data only and cannot claim holdout calibration; only the prospective holdout (Phase 19) can support a promotion. tech-1 has no holdout evaluation. The max-T correction is centred, not studentized (change control before any prospective read if changed).
3. Carried: catalyst source roles and event categories have no time in the lab schema; replayed social bot shares are lower bounds; collector deployment on Elving's computer (backtesting RUNBOOK); forward social and catalyst collection needs new approvals; regime labels are lab-universe proxies.

## Phase 12 commits

- HEAD before `63076ad`; pre-registration `79d30f5` (16:41:13Z); frozen code `3ea7030` (17:32:01Z); pre-opening outputs `d58de61` (17:33:19Z); opening outputs `de7ac77` (17:47:49Z); results, evidence and records `c549748` (18:04:05Z); this post-commit records commit on top. Post-commit at `c549748`: suite `1 failed, 1445 passed` (known failure only; strays removed by hand), guard 0 violations, seal check 0 problems, single-branch release audit exit 0 "Needs action: no.", `git status` clean. Local only; the orchestrator pushes.

## Waiting on Elving

- Any paid data, LLM, Zep or MiroFish use; social API credentials or consent (X, Telegram, Reddit, Discord, YouTube, Farcaster routes are BLOCKED); scheduled catalyst or social collection into a store this engine can read; adding research packages to the lab's runtime; a merge into `main`; deploying the forward depth collector (already approved, PI-D-044; not yet done).

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (a reviewed false positive on that branch, D-BT-016; PI-D-049 item 6). It is not reachable from `feature/predictive-intelligence`, whose own audit passes on a single-branch clone.

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no seed phrases or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flag overrides unchanged. Forecasts stay a separate evidence section with the flag OFF. No raw social content in the repository.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git log -8 --oneline
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
python -m pytest tests/test_predictive_evaluation.py tests/test_predictive_phase12_outputs.py -q
```

Expect `"problems": []` from the seal check (the opening did not change the sealed files) and only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` failing in the suite. Then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. A REPRODUCTION of the opening (`python -B audits/predictive-intelligence/phase_12/probes/run_holdout.py open OUT --reproduction`, about 11 min) needs the two private stores under `/home/claude/pi_research/` (rebuild them from the committed archives if the workspace was reclaimed: `phase_05/data/FEATURE_STORE_CONTRACT.md`, `phase_06/labels/TARGET_SCHEMA.md`) and the git objects of the holdout decisions' export commits.
