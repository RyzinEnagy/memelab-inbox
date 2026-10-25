# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-051). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_08/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-25

- Phases 00 to 05: PASS, each with an independent skeptic review and a repair pass folded in, re-verified by the orchestrator and pushed.
- Phase 06 (outcome labels and censoring): NEEDS_REVIEW with one item open, the frozen 48 h revision re-read (not before 2026-10-26T13:49Z; the orchestrator's session runs it). Everything else is folded in (PI-D-045).
- Phase 07 (transparent baselines): PASS, PROVISIONAL under PI-D-046 (repair pass 2, PI-D-049), pushed at `1139575`.
- Phase 08 (technical predictors): NEEDS_REVIEW, first pass, PROVISIONAL under PI-D-046. Phase agents cannot run the independent skeptic (PI-D-013); `audits/predictive-intelligence/phase_08/SKEPTIC_PACKET.md` is ready for the orchestrator. Commits: pre-registration `8599318`, code `d290384`, runner repair `d9b2a9c`, outputs and records after it, and a post-commit records commit on top (hashes in `phase_08/PHASE_08_EVIDENCE.md`). Branch commits after `1139575` are local; the orchestrator pushes.
- Spend: 0 Firecrawl credits; Phase 08 made no vendor or network call.

## What Phase 08 found

- Explicit no-go, as stated in advance in the checklist: no technical model can be called better or worse than the base rate, and every model is MODEL_NOT_PROMOTED (PI-D-051). Technical inputs exist only for decisions with a point-in-time pool and 24 h of fetched history (154 of 240 labelled development decisions; none on the CURRENT_VENDOR_LIST route). On those rows T1 and T2 never reach the training minimum (100 events, 20 per class): INSUFFICIENT_HISTORY. T1b reaches it only in the last fold (138 rows, 20 positive) and scores 6 rows with 0 positive on one day: INSUFFICIENT_DAYS. Its Brier skill there (M2 0.729) is the arithmetic of six negatives, not skill.
- Same frozen folds as Phase 07 (split fingerprints equal) and Phase 07's B0 and B2 out-of-sample numbers reproduced exactly (76 of 76).
- tech-1 (15 features: returns, realized variation, ranges, relative volume, activity, breakout, failed breakout, retest, distance from highs) uses closes and volumes only, candles closed and available at T only; it equals the stored version 2 snapshot wherever they overlap (240 of 240); 248 candles of the decision pools were not yet available at their decision and none was used.
- Traps: future next-hour return refused 98 of 98; moved cutoff 1,758 of 1,758 late values refused; holdout-start cards refused on development decisions 9 of 9; window-dependent opens, highs and lows cannot move a feature (CX-08, tests). Two forecast traces recomputed independently with no difference.
- Frozen for Phase 12: M1, M2, M3 cards per target at 2026-10-17T00:00Z (T1b fitted, T1 and T2 abstain), in `phase_08/artifacts/`. Cumulative search ledger: `phase_08/experiments/SEARCH_LEDGER.csv` (1,133 rows).
- Open own finding for the skeptic: the logistic differs from scikit-learn lbfgs by 1.13e-6 on one real fold (pre-registered tolerance 1e-6); lbfgs stops early there, and the exact Newton solvers agree within 7.1e-14 (diagnosis added after the result, disclosed).

## What exists now

- Targets frozen before any price data was read (Phase 01): T1 +25% before -15% within 24 h; T1b the same within 6 h; T2 half the reference price or a trading halt within 24 h. Price-path labels only, no fill, size, depth or profit claims.
- Code (flag OFF, imported by no existing module): `memelab/predictive/` contract, decisions, runtime, store, sources, features, labels, stats, baselines, technical, with `tests/test_predictive_*.py`.
- Data: point-in-time feature store (1,500 decisions, 3,000 snapshots), development labels (T1 136 with 34 positive, T1b 224 with 26, T2 131 with 28), holdout labels sealed in `phase_06/sealed/` (open only in Phase 12 after `check_seal.py`).

## Open items, in order

1. Orchestrator: run the independent skeptic on Phase 08 from `phase_08/SKEPTIC_PACKET.md`; the phase agent then folds the review in (repair pass), copies it into `phase_08/skeptic/` and finalises the status.
2. Phase 06 48 h revision re-read: `python -B audits/predictive-intelligence/phase_06/probes/make_labels.py reread48`, at or after 2026-10-26T13:49Z. If any development label changes: rerun `phase_07/probes/run_baselines.py` at `f977aab` and `phase_08/probes/run_technical.py` at `d9b2a9c` (or later), commit the superseding outputs and record it.
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

Expect `"problems": []` from the seal check and `1 failed, 1219 passed` from the suite (only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`, a known clock-dependent failure). Then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The Phase 07 and 08 runners need the two private stores under `/home/claude/pi_research/` (rebuild them from the committed archives if the workspace was reclaimed: `phase_05/data/FEATURE_STORE_CONTRACT.md`, `phase_06/labels/TARGET_SCHEMA.md`).
