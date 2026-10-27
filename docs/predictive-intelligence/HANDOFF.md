# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-083). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_15/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-27

- Phases 00 to 13: PASS. Phase 14 (isolated behavioral-simulation interface): TEST_ONLY (PI-D-077), MIROFISH_GATE BLOCKED for live use.
- Phase 15 (incremental value of behavioral simulation): **TEST_ONLY** after repair pass 2 (PI-D-082, PI-D-083). Decision: **INSUFFICIENT_VALIDATION**, **MIROFISH_NO_GO**, **RULES_NOT_PROMOTED** (PI-D-081), unchanged by the repair. The independent skeptic found no material failure, 7 minor findings and CX-S15 (rule warnings cluster by mint, so the decision-level permutation is optimistic); all handled by a recorded addition at `869d597` that can only make statements more conservative.
- Admission: the orchestrator started Phase 15 with Phase 14 at TEST_ONLY because the behavioral module is optional and flag OFF, a MiroFish NO_GO does not block the statistical system, and no LLM spend is approved (PI-D-078, PI-D-081 item 1). Phase 15 could not have been validated with spend either: 0 of the 100 required eligible dated catalyst events exist.
- Spend: 0 Firecrawl credits, 0 vendor calls, 0 language-model calls, no socket in the Phase 15 probes, no key.

## What Phase 15 did (PI-D-078 to PI-D-081)

- Pre-registered the question, event population, coding rules, comparators, measures, controls, examples rule and decision rule before any code, coding or label read (`b274cbc`).
- `memelab/predictive/scenario_eval.py` (scenario-eval-1, numpy, flag OFF, imported by no other module): blind mechanical coder, warning metrics with a day-stratified permutation, Holm, A_WARN, selection status, `decide`. 34 unit tests plus 5 output tests; mutation probe 45 of 45; standard-library oracle recompute 0 differences.
- Blind coding of the 830 development and 95 holdout-window rule documents, committed before any scoring (`7b787bf`); scoring run, self-review CP15-0 (PI-D-080, outputs added only), repeated run with every first-run value equal (`3135060`).
- The first agent's session ended while writing the records; a second agent finished them from the committed outputs without rerunning any recorded step.
- Repair pass 2 (PI-D-082): mint-block nulls (`mint_block_permutation`, `clustered_metrics`, conservative p = largest of three nulls) recorded beside the frozen outputs in `phase_15/behavioral/MINT_CLUSTERED_NULL.json`; calibration on 400 per-mint salts per target (decision null 0.0975 low-side rejections on T1b against a bound of 0.0718; conservative p holds everywhere); controls judged as single tests (the recorded bogus control is FLAGGED by the decision null, raw p 0.032, NOT_FLAGGED by the conservative p, 0.120; a per-mint bogus control is NOT_FLAGGED on every target); registry-ledger map both ways (`experiments/REGISTRY_LEDGER_MAP.csv`); tests for the skeptic's surviving mutations; the order test fails on a shallow clone; mutation probe 56 of 56; wording fixed (blinding basis, "does not replicate" instead of "reverses", all three per-label rows named as noise).

## Result

- Eligible independently dated catalyst events: 0 of 100 (`behavioral/EVENT_SET.csv`).
- A (behavioral-rules-1, as A_WARN) out of sample: INSUFFICIENT_DAYS on T1 and T2, INSUFFICIENT_EVENTS on T1b, NO_UNCORRECTED_SKILL everywhere. Descriptive warnings: not distinguishable from chance after Holm. Bogus catalyst control not flagged after Holm (raw p 0.032). Holdout (POST_OPENING): the T2 subgroup reverses.
- B (evidence-only LLM) and D (MiroFish): BLOCKED, no approved spend; P26 makes any retrospective run on these dates EXPLORATORY_NOT_AS_OF. C: no calibrated classifier (Phase 13).
- N_search primary 121, sensitivity 160; cumulative ledger `phase_15/experiments/SEARCH_LEDGER.csv` plus `SEARCH_LEDGER_RP2_ADDITION.csv`.

## Open items, in order

1. The orchestrator re-verifies Phase 15 (TEST_ONLY) and pushes.
2. Phase 16 (champion selection): nothing behavioral enters selection; count searches from Phase 15's ledger and its addition; it cannot promote from the retrospective holdout; any warning p value uses the conservative mint-block null; any rule promotion needs the max-T correction first (PI-D-082 item 5).
3. Carried: Phase 17 calls `abstention.forecast_result` and `validate_publication` and validates every document with its record; Phase 19 supplies prospective evidence; champion cards MODEL_STALE after 2026-10-31; catalyst and social tables are not exported; forward depth collection approved but not deployed (PI-D-044).

## Phase 15 commits

HEAD before `b0243b4`; pre-registration `b274cbc`; frozen coding code `9ab0160`; blind coding run `7b787bf`; frozen scoring code `0abffd5`; first scoring run `01e535d`; change control CP15-0 `de41d26`; repeated scoring run `3135060`; records `cda97c3`; post-commit record `08e8670` (pushed, reviewed by the skeptic). Repair pass 2: code `869d597` (frozen before the recorded addition), recorded addition `aea95f0`, records `e59d9d9`, post-commit record on top. Post-commit at `e59d9d9`: suite `1 failed, 1853 passed, 1 skipped` (known failure only; strays removed by hand), guard 0 violations, seal check 0 problems, single-branch release audit exit 0 "Needs action: no." (`phase_15/postcommit/rp2_*`). First-pass post-commit at `cda97c3`: suite `1 failed, 1846 passed, 1 skipped` (known failure only; strays removed by hand), guard 0 violations, seal check 0 problems, single-branch release audit exit 0 "Needs action: no.", `git status` clean (`phase_15/postcommit/`). Local only; the orchestrator pushes.

## Waiting on Elving

- Any paid data, LLM, Zep or MiroFish use; scheduled catalyst or social collection into a store this engine can read (needed before the simulation question can ever be tested, on prospective events only); social API credentials or consent; research packages in the lab's runtime; a merge into `main`; deploying the forward depth collector (approved, PI-D-044; not yet done).

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (a reviewed false positive on that branch, D-BT-016; PI-D-049 item 6). It is not reachable from `feature/predictive-intelligence`, whose own audit passes on a single-branch clone.

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no seed phrases or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flag overrides unchanged. Forecasts stay a separate evidence section with the flag OFF. No raw social content in the repository. Behavioral output is fictional, never a probability.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git log -12 --oneline
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
python -m pytest tests/test_predictive_scenario_eval.py tests/test_predictive_phase15_outputs.py -q
python -B audits/predictive-intelligence/phase_15/probes/mint_null.py /tmp/p15m
python -B audits/predictive-intelligence/phase_15/probes/code_scenarios.py /tmp/p15c
python -B audits/predictive-intelligence/phase_15/probes/score_scenarios.py /tmp/p15s
```

Use a full clone: the Phase 15 commit-order test fails on a shallow one by design. Expect `"problems": []` from the seal check and only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` failing in the suite; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The coding probe needs the Phase 05 store and the scoring and mint-null probes the Phase 06 development store under `/home/claude/pi_research/` (rebuild recipes: `phase_05/data/FEATURE_STORE_CONTRACT.md` and the Phase 06 records).
