# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-092). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_16/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-27

- Phases 00 to 13: PASS. Phase 14: TEST_ONLY (PI-D-077). Phase 15: TEST_ONLY, INSUFFICIENT_VALIDATION, MIROFISH_NO_GO, RULES_NOT_PROMOTED (PI-D-083).
- Phase 16 (champion selection, ensemble, model registry): **PASS** after repair pass 2 (PI-D-089 to PI-D-092). The independent skeptic found no material failure, 9 minor findings and CX-S16 (a forged-facts entry pinned and served at SHADOW through a caller-supplied check); all fixed. TEST_ONLY part: the promotion branch on fixtures. The orchestrator admitted the phase with Phase 15 at TEST_ONLY (PI-D-084) and decided not to change the promotion table now (PI-D-091).
- Spend: 0 Firecrawl credits, 0 vendor calls, 0 language-model calls, no socket in the Phase 16 runner, no key.

## The state the registry records (PI-D-087, PI-D-092)

- **No champion for any target.** T1 24 h, T1b 6 h and T2 24 h are pinned NO_VIABLE_CHAMPION: every request abstains, every document says model `not_selected`, no probability is published.
- B0 (base rate) and B2 (simple model) are pinned beside each target as references for the prospective comparison. They are ABSTAIN, REFERENCE_ONLY_NEVER_PUBLISHED, and B2 is not a champion: Phase 12 named it only by default (T1 BSS -0.024, T1b -0.083 with calibration in the large failed, T2 7 positives, INSUFFICIENT_EVENTS; Phase 13 UNCALIBRATED everywhere).
- 69 immutable entries (one per frozen card): ABSTAIN 6, NO_GO 63, 0 SHADOW, 0 VALIDATED_EXPERIMENTAL, 0 publishable. Identical inference 69 of 69 equal to the committed Phase 12 predictions.
- NO_ENSEMBLE on every target: development out-of-fold rows give no verdict (INSUFFICIENT_DAYS or INSUFFICIENT_EVENTS), the chronological stack never clears its gate, and the combinations of B2 with the onchain-1 models count the lab's fatal flags twice (refused).
- The promotion path is closed under the frozen ACCEPTANCE table (the retrospective holdout is spent). Orchestrator decision PI-D-091: no change now; changing it is Elving's decision; the honest route is the prospective holdout of Phase 19.

## What Phase 16 built (PI-D-085, PI-D-086, PI-D-089)

- `memelab/predictive/registry.py` (registry-1; numpy, the standard library, `contract`, `stats`; flag OFF; imported by no other module): hash-addressed immutable entries; levels recomputed from facts (`promotion_decision`); facts rebuilt by the registry itself from the committed Phase 12 and 13 files (`facts_from_repo`, `check_facts`, PRIMARY rows first via `metric_rows`), run inside `pin_event`, `rollback_event` and `serve` with no caller-supplied verifier; code files hashed per entry (`code_of`, `code_changes`); nested agent fields refused; append-only sha-chained log with REGISTER, PIN, ROLLBACK, ENSEMBLE_DECISION; `resolve` as of a decision time; `compatibility` (P46); `status_at` (MODEL_STALE, RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF, DRIFT_ALERT, MODEL_NOT_PROMOTED) with retrain requirements; identical-inference hashes; `rollback_event`; `serve` (the only source of card, level and calibration card for the publication path); `select_champion` (refuses holdout rows); ensemble rules; `target_plan`; internal `reference_record`.
- 55 unit tests, 12 output tests, `tests/test_predictive_reproductions.py` (Phases 07, 12, 13, 16 reproduce their committed outputs), a synthetic probe fixture; mutation probe 96 of 96; the runner `phase_16/probes/build_registry.py`.
- CP12-2 (PI-D-090): the Phase 12 runner's card glob is narrowed to Phases 07 to 11; plan and predict 7 of 7 and the opening REPRODUCTION 10 of 10 byte-equal.

## Open items, in order

1. The orchestrator re-verifies Phase 16 (PASS) and pushes.
2. Phase 17 (after a PASS): every request goes through `registry.serve(..., root=<repository>, inference=<recomputed probe rows>)` then `abstention.forecast_result(...)` with `serve`'s `forecast_inputs`, and `validate_publication` with the persisted record; keep the raw model number in the request record (PI-D-068); show `onchain.decision_support` beside any forecast; the CURRENT_VENDOR_LIST route abstains.
3. If Elving wants a promotion path: a change control to ACCEPTANCE `promotion` (PI-D-091), registered before prospective labels are read; then Phase 19 supplies admissible prospective evidence (at least 50 matured events and 10 per class per target) and the lift of `calibration.verify_card`'s VALIDATED_EXPERIMENTAL refusal tied to a registry entry.
4. Frozen cards are MODEL_STALE after 2026-10-31T00:00:00Z; Phase 19's reference comparison after that needs retrained reference cards from a committed plan.
5. Carried: catalyst and social tables are not exported; forward depth collection approved but not deployed (PI-D-044); keep `tests/test_predictive_reproductions.py` green; the registry's internal row key `members` must be renamed before any JSON write (content guard, PI-D-088).

## Phase 16 commits

HEAD before `576f99d`; pre-registration `8af3cd4`; frozen code `d2038a7`; first recorded run `9eebb8d`; CP16-0 `8cd19bd`, repeat `72488dd`; records `ffcedb4`; CP16-1 `d74a16f`, repeat `b669615`; records `2f81759`; post-commit `35758c9` (pushed, reviewed by the skeptic). Repair pass 2: code `b4bb03b` (CP16-2, CP12-2), recorded run `0e71f55`, records `1d76ce1`; post-commit at `1d76ce1`: suite `1 failed, 1925 passed, 1 skipped` (known failure only; strays removed by hand), guard 0 violations, seal check 0 problems, single-branch release audit exit 0 "Needs action: no." (`phase_16/postcommit/rp2_*`); the post-commit record commit on top. Local only; the orchestrator pushes.

## Waiting on Elving

- The change control that could reopen promotion (ACCEPTANCE `promotion`), any paid data, LLM, Zep or MiroFish use, scheduled catalyst or social collection into a store this engine can read, social API credentials or consent, research packages in the lab's runtime, a merge into `main`, deploying the forward depth collector (approved, PI-D-044; not yet done).

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (a reviewed false positive on that branch, D-BT-016; PI-D-049 item 6). It is not reachable from `feature/predictive-intelligence`, whose own audit passes on a single-branch clone.

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no seed phrases or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flag overrides unchanged. Forecasts stay a separate evidence section with the flag OFF. No raw social content in the repository. Behavioral output is fictional, never a probability. References are never forecasts.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git log -12 --oneline
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
python -m pytest tests/test_predictive_registry.py tests/test_predictive_phase16_outputs.py -q
python -B audits/predictive-intelligence/phase_16/probes/build_registry.py /tmp/p16
python -B audits/predictive-intelligence/phase_16/probes/mutation_registry.py /tmp/p16_mut.json
python -m pytest tests/test_predictive_reproductions.py -q
```

Use a full clone: the Phase 15 and 16 commit-order tests fail on a shallow one by design. Expect `"problems": []` from the seal check and only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` failing in the suite; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The runner needs the Phase 05 feature store and the Phase 06 development store under `/home/claude/pi_research/` (rebuild recipes: `phase_05/data/FEATURE_STORE_CONTRACT.md` and the Phase 06 records).
