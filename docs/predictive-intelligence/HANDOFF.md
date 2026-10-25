# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-052). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_08/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-25

- Phases 00 to 05: PASS, each with an independent skeptic review and a repair pass folded in, re-verified by the orchestrator and pushed.
- Phase 06 (outcome labels and censoring): NEEDS_REVIEW with one item open, the frozen 48 h revision re-read (not before 2026-10-26T13:49Z; the orchestrator's session runs it). Everything else is folded in (PI-D-045).
- Phase 07 (transparent baselines): PASS, PROVISIONAL under PI-D-046 (repair pass 2, PI-D-049), pushed at `1139575`.
- Phase 08 (technical predictors): NEEDS_REVIEW for one item, PROVISIONAL under PI-D-046. The orchestrator's independent skeptic (no material failure, 8 minor findings, CX-S08) is folded in by repair pass 2 (PI-D-052). The only open item is checklist G16: the numpy logistic differs from scikit-learn lbfgs by up to 2.08e-6 against a pre-registered 1e-6; lbfgs stops early (gradients 1.0e-6 to 7.2e-6) and newton-cholesky agrees within 9.0e-12. It stays failed as registered until the orchestrator or Elving records whether the explanation closes it. Commits: pre-registration `8599318`, code `d290384`, runner repair `d9b2a9c`, outputs `fc6b990`, post-commit records `0656b7c`, repair code `e81ee46`, repair outputs and records `1dbfd86`, and a post-commit records commit on top (all local; the orchestrator pushes). Post-commit at `1dbfd86`: suite `1 failed, 1229 passed` (known failure only), guard 0 violations, seal check 0 problems, single-branch release audit exit 0.
- Spend: 0 Firecrawl credits; Phase 08 made no vendor or network call.

## What Phase 08 found

- Explicit no-go, as stated in advance in the checklist: no technical model can be called better or worse than the base rate, and every model is MODEL_NOT_PROMOTED (PI-D-051). Technical inputs exist only for decisions with a point-in-time pool and 24 h of fetched history (154 of 240 labelled development decisions; none on the CURRENT_VENDOR_LIST route). On those rows T1 and T2 never reach the training minimum (100 events, 20 per class): INSUFFICIENT_HISTORY. T1b reaches it only in the last fold (138 rows, 20 positive) and scores 6 rows with 0 positive on one day: INSUFFICIENT_DAYS. Its Brier skill there (M2 0.729) is the arithmetic of six negatives, not skill.
- Same frozen folds as Phase 07 (split fingerprints equal) and Phase 07's B0 and B2 out-of-sample numbers reproduced exactly (76 of 76).
- tech-1 (15 features: returns, realized variation, ranges, relative volume, activity, breakout, failed breakout, retest, distance from highs) uses closes and volumes only, candles closed and available at T only; it equals the stored version 2 snapshot wherever they overlap (240 of 240); 248 candles of the decision pools were not yet available at their decision and none was used.
- Traps: future next-hour return refused 98 of 98; moved cutoff 1,758 of 1,758 late values refused; holdout-start cards refused on development decisions 9 of 9; window-dependent opens, highs and lows cannot move a feature (CX-08, tests). Two forecast traces recomputed independently with no difference.
- Frozen for Phase 12: M1, M2, M3 cards per target at 2026-10-17T00:00Z (T1b fitted, T1 and T2 abstain), in `phase_08/artifacts/`. Cumulative search ledger: `phase_08/experiments/SEARCH_LEDGER.csv` (1,133 rows).
- Repair pass 2: 50 tests and 39 of 39 mutations caught (including CX-S08, a scorer that standardises the scored rows with their own statistics); the runner now exits 1 on a failed trap; the oracle covers the preprocessing (2.1e-14) and the frozen T1b cards.
- Young pools: 12 of the 15 censored development decisions are pools younger than the 24 h window at T. tech-1 models cannot score a pool younger than about 24 h 5 min, so in live use most new candidates would abstain.
- Fragility: both fitted T1b states sit exactly at 20 positives (fold 4: 138 rows; holdout start: 144). One development label changed by the 48 h re-read turns every fitted Phase 08 model into INSUFFICIENT_HISTORY, so the rerun in open item 2 must not be skipped.

## What exists now

- Targets frozen before any price data was read (Phase 01): T1 +25% before -15% within 24 h; T1b the same within 6 h; T2 half the reference price or a trading halt within 24 h. Price-path labels only, no fill, size, depth or profit claims.
- Code (flag OFF, imported by no existing module): `memelab/predictive/` contract, decisions, runtime, store, sources, features, labels, stats, baselines, technical, with `tests/test_predictive_*.py`.
- Data: point-in-time feature store (1,500 decisions, 3,000 snapshots), development labels (T1 136 with 34 positive, T1b 224 with 26, T2 131 with 28), holdout labels sealed in `phase_06/sealed/` (open only in Phase 12 after `check_seal.py`).

## Open items, in order

1. Orchestrator or Elving: record whether the lbfgs explanation closes Phase 08's G16 (PI-D-052 item 8); with it recorded, Phase 08 is PASS (provisional under PI-D-046).
2. Phase 06 48 h revision re-read: `python -B audits/predictive-intelligence/phase_06/probes/make_labels.py reread48`, at or after 2026-10-26T13:49Z. If any development label changes: rerun `phase_07/probes/run_baselines.py` at `f977aab` and `phase_08/probes/run_technical.py` at `e81ee46` (or later), commit the superseding outputs and record it.
3. Phase 09 only after Phase 08's gate (orchestrator's decision).

## Waiting on Elving

- Any paid data, LLM, Zep or MiroFish use; adding research packages to the lab's runtime; a merge into `main`.

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (a reviewed false positive on that branch, D-BT-016; PI-D-049 item 6). It is not reachable from `feature/predictive-intelligence`, whose own audit passes on a single-branch clone.

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no seed phrases or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flag overrides unchanged. Forecasts stay a separate evidence section with the flag OFF.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git log -6 --oneline
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
```

Expect `"problems": []` from the seal check and `1 failed, 1229 passed` from the suite (only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`, a known clock-dependent failure). Then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The Phase 07 and 08 runners need the two private stores under `/home/claude/pi_research/` (rebuild them from the committed archives if the workspace was reclaimed: `phase_05/data/FEATURE_STORE_CONTRACT.md`, `phase_06/labels/TARGET_SCHEMA.md`).
