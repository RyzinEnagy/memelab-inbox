# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-069). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_13/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-26

- Phases 00 to 12: PASS (Phase 12 after repair pass 2, PI-D-066; the retrospective holdout is opened and spent).
- Phase 13 (calibration, uncertainty and abstention): NEEDS_REVIEW, first pass plus the agent's own self-review pass 2 (PI-D-068), awaiting the orchestrator's independent skeptic (PI-D-013). One checklist item, G7, failed as registered and needs a decision (below).
- Spend: 0 Firecrawl credits, 0 vendor calls, 0 language-model calls, no network use in Phase 13.

## What Phase 13 did (PI-D-067, PI-D-068, PI-D-069)

- Rules frozen before any code or fit (`phase_13/ACCEPTANCE_CHECKLIST.md`, `0fdf698`): calibration rows only from the champion's chronologically valid development out-of-sample rows; calibrator fit gate 100 events, 20 per class, 5 days; fixed method rule (Venn-Abers from 200 events with 40 per class, else Platt); the frozen ACCEPTANCE tolerance checked only on prospective evidence that is not the fit set; a publication rule (flag ON, level SHADOW or VALIDATED_EXPERIMENTAL, CALIBRATED, support of 20 in the score's bin, display range [0.01, 0.99], interval holding the point, caveats); 28 abstention conditions, each mapped to one unchanged contract reason; CX-13 named in advance.
- `memelab/predictive/calibration.py` (calibration-1) and `memelab/predictive/abstention.py` (abstention-1): numpy and the standard library, flag OFF, imported by no other module. The contract (`memelab.predictive.forecast/1`) is unchanged; `validate_publication` adds the Phase 13 checks to `contract.validate` and closes the PI-D-022 items for `calibration_reference`. ForecastResult schema `phase_13/models/FORECAST_RESULT_SCHEMA.json` (a forecast/1 document plus its abstention-1 record). 124 tests (55 + 62 + 7 output tests); mutation probe 79 of 79.
- Self-review pass 2 (not independent, PI-D-068): a tampered calibration card, a level that differs from the card's, a forged support and an arbitrary base rate could have passed the publication path; closed with tests that fail on the first-pass module; recorded outputs byte-equal after the fix.

## Result (empirical)

- T1 24 h, T1b 6 h, T2 24 h: UNCALIBRATED. Calibration sets 24 (8 positive, 3 days), 44 (3, 5), 8 (1, 1); no chronologically valid development set can reach the gate. Calibration artifacts `phase_13/artifacts/<target>/CALIBRATION_CARD.json`, level ABSTAIN, publishable false.
- Every request ends ABSTAIN with named reasons: 76 development, 193 retrospective holdout (POST_OPENING description) and 30 prospective (10 decisions by 3 targets); publication coverage 0%. Today every target abstains with FLAG_OFF, MODEL_NOT_SELECTED, UNCALIBRATED, INSUFFICIENT_HISTORY and NOT_YET_MATURED.
- Exchangeability of the event rate is rejected across decision days (T1b p 0.023, T2 p 0.020) and routes (T1 p 0.021, T1b p 0.011); block intervals of the base rate are 1.04 to 1.51 times the Wilson width.
- POST_OPENING only: a development-fitted descriptive Venn-Abers fails the frozen check on the holdout for all three targets (combined FAILS, never a claim).
- Card and tables: `phase_13/models/CALIBRATION_CARD.md`, `calibration/RELIABILITY_COVERAGE.csv`, `calibration/ABSTENTION_MATRIX.md`.

## Open items, in order

1. The orchestrator runs the independent skeptic on `phase_13/SKEPTIC_PACKET.md`; the phase agent folds the review in (repair pass), then PASS only if every gate item holds.
2. G7 failed as registered: scikit-learn `_sigmoid_calibration` differs from the numpy Platt by 1.5e-6 (T1b) and 9.4e-6 (T2) on two descriptive below-gate fits because its lbfgs stops early (its gradient up to 5.7e-7, the numpy fit's below 1e-15); the PI-D-053 newton-cholesky construction agrees within 5.3e-15 (added after seeing the result). No output depends on these fits. Closing it needs a decision by the orchestrator or Elving, as PI-D-053 did for Phase 08.
3. For later phases: Phase 16 sets levels and cannot promote from the retrospective holdout; Phase 17 calls `abstention.forecast_result` and `validate_publication` for every eligible decision, keeps the raw model number in its request record and recomputes the calibrated point before publishing; Phase 19 supplies prospective evidence (at least 50 matured events and 10 per class, not the fit set) through `calibration.build_card`; the champion cards are MODEL_STALE for decisions after 2026-10-31.
4. Carried: the tech-1 cards have no holdout evaluation; catalyst and social tables are not exported; forward depth collection is approved but not deployed (PI-D-044); regime labels are lab-universe proxies; the CURRENT_VENDOR_LIST route abstains POOL_NOT_POINT_IN_TIME.

## Phase 13 commits

Pre-registration `0fdf698` (20:21:18Z); frozen code `5a3c582` (20:52:33Z); recorded run outputs `9cd5288`; self-review pass 2 code `2e1488a` (21:03:53Z); outputs, evidence and records on top; records `9f95b71`; post-commit record on top (local only; the orchestrator pushes). Post-commit at `9f95b71`: suite `1 failed, 1579 passed` (known failure only; strays removed by hand), guard 0 violations, seal check 0 problems, single-branch release audit exit 0 "Needs action: no.", `git status` clean.

## Waiting on Elving

- The G7 decision (or the orchestrator's). Any paid data, LLM, Zep or MiroFish use; social API credentials or consent; scheduled catalyst or social collection into a store this engine can read; research packages in the lab's runtime; a merge into `main`; deploying the forward depth collector (approved, PI-D-044; not yet done).

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (a reviewed false positive on that branch, D-BT-016; PI-D-049 item 6). It is not reachable from `feature/predictive-intelligence`, whose own audit passes on a single-branch clone.

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no seed phrases or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flag overrides unchanged. Forecasts stay a separate evidence section with the flag OFF. No raw social content in the repository.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git log -12 --oneline
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
python -m pytest tests/test_predictive_calibration.py tests/test_predictive_abstention.py tests/test_predictive_phase13_outputs.py -q
python -B audits/predictive-intelligence/phase_13/probes/run_calibration.py /tmp/p13   # about 10 s; compare with phase_13/ (POST_OPENING reads of committed Phase 12 files, logged)
```

Expect `"problems": []` from the seal check and only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` failing in the suite; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The runner needs the two private stores under `/home/claude/pi_research/` (rebuild them from the committed archives if the workspace was reclaimed: `phase_05/data/FEATURE_STORE_CONTRACT.md`, `phase_06/labels/TARGET_SCHEMA.md`).
