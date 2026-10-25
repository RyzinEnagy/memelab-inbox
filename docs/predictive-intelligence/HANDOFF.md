# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-049). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_07/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-25

- Phases 00 to 05: PASS, each with an independent skeptic review and a repair pass folded in, re-verified by the orchestrator and pushed.
- Phase 06 (outcome labels and censoring): NEEDS_REVIEW with one item open, the frozen 48 h revision re-read (not before 2026-10-26T13:49Z; the orchestrator's session has a scheduled follow-up to run it). Everything else in Phase 06 is folded in (PI-D-045).
- Phase 07 (transparent baselines): PASS, PROVISIONAL. Started on Elving's instruction of 2026-10-25 15:40 New York time ("continue with the subsequent phases, beginning with phase 07"), recorded as PI-D-046: every Phase 07 result is PROVISIONAL until the Phase 06 re-read is folded in; if it changes any development label, Phase 07 reruns from its repair code `f977aab` and the outputs are superseded, not edited; nothing claims the revision check. The orchestrator's independent skeptic (1 MATERIAL, 8 minor, CX-S07) is folded in by repair pass 2 (PI-D-049). Commits: pre-registration `74183c9`, first-pass code `6672447`, outputs `ccee7ad`, records `0fa5cb8`, repair code `f977aab`, repair outputs and records on top (hashes in `phase_07/PHASE_07_EVIDENCE.md`).
- Branch `feature/predictive-intelligence`: the Phase 06 repair commits and all Phase 07 commits are local (the orchestrator pushes). `main` untouched. No pull request.
- Spend: 0 Firecrawl credits; Phase 07 made no vendor call (the runner refuses any socket connect).

## What Phase 07 found

- No baseline can be called better or worse than the training base rate on development data (retrospective, provider mode). T1 24 h: 3 folds, 24 out-of-sample events (8 positive) over 3 days; T2 24 h: 1 fold, 8 events (1 positive) on 1 day; both INSUFFICIENT_DAYS (frozen minimum 5 days). T1b 6 h: 5 folds, 44 events (3 positive) over 5 days: INSUFFICIENT_EVENTS for every baseline (below the frozen out-of-sample minimums of 50 events and 10 per class, PI-D-049); its numbers: B2 Brier 0.0595 against B0 0.0667, skill 0.108, governing mint interval -0.127 to 0.219, Holm p 0.28; B3 (the lab's score through Platt) skill -0.097. This is the outcome Phase 01 stated in advance.
- Why so few days: a fold needs 100 matured training labels, and the 24 h and 48 h maturities consume the end of the 10-day development window; each out-of-sample day is one export batch. The sealed holdout (Phase 12) and the prospective data from 2026-10-24 (Phase 19) are where any difference can show.
- Controls: NC1 (shuffled training labels) is uninformative at this size (INSUFFICIENT_DAYS or INSUFFICIENT_EVENTS; shuffled fits beat the real B2 in 70% of seeds on T1 and 95% on T2, so B2 is noise there). NC2 (future feature) refused on 136 of 136 rows, NC3 (same ticker) 8 of 8 pairs, CX-07 (join by mint with its newest snapshot) 250 of 250 rows, CX-S07 (skill on one positive) now INSUFFICIENT_EVENTS.
- Frozen train-only cards for Phase 12: B0, B1, B2, B3, B3F, B4 per primary target at 2026-10-17T00:00Z (`phase_07/artifacts/`), JSON read by numpy, round trip identical, tampering refused.
- Engine: `memelab/predictive/stats.py` and `baselines.py` (numpy and standard library only, flag OFF); frozen interval and verdict rules pinned by tests (42 of 42 mutations caught); scikit-learn agrees within 3.0e-7; two runs give identical files. `features.training_view` now refuses a value without an availability time (rows unchanged).

## What exists now

- Targets frozen before any price data was read (Phase 01): T1 +25% before -15% within 24 h; T1b the same within 6 h; T2 a fall to half the reference price or trading stopping within 24 h. Price-path labels only, no fill, size, depth or profit claims. Exit-adjusted and liquidity targets wait for forward data from the backtesting tracker (PI-D-044).
- Decision unit and time: the exact thesis row, timed by the first state export on `main` that holds it (PI-D-015, PI-D-021).
- Code (flag OFF): `memelab/predictive/` contract, decisions, runtime, store, sources, features, labels, stats, baselines, with `tests/test_predictive_*.py`.
- Data: point-in-time feature store (1,500 decisions, 3,000 snapshots) and development labels (T1 136 with 34 positive, T1b 224 with 26, T2 131 with 28), rebuildable offline from committed raw archives; holdout labels sealed in `phase_06/sealed/` (open only in Phase 12 after `check_seal.py`).
- Backtesting branch (PI-D-043, PI-D-047): read at `12f278b`; it has no probability baseline, no Brier or log loss and no frozen-target label; Phase 07 duplicates nothing there and imports nothing from it.

## Open items, in order

1. Phase 06 48 h revision re-read: `python -B audits/predictive-intelligence/phase_06/probes/make_labels.py reread48`, at or after 2026-10-26T13:49Z (the orchestrator's session has a scheduled follow-up). Fold the result into Phase 06. If any development label changes: rerun `python -B audits/predictive-intelligence/phase_07/probes/run_baselines.py audits/predictive-intelligence/phase_07` at `f977aab` (or later Phase 07 code), commit the superseding outputs and record it.
2. Phase 08 is eligible (orchestrator's decision), with Phase 07's results PROVISIONAL until item 1 is done.

## Waiting on Elving

- Any paid data, LLM, Zep or MiroFish use; adding research packages to the lab's runtime; a merge into `main`.

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (`audits/backtesting/research/smoke/etcherfx__sol-trade/output.txt`, rule key_material_field; fetched here to read that branch for PI-D-047). It is a reviewed false positive on that branch (the environment variable name SOLTRADE_PRIVATE_KEY quoted by a static scan; that branch's own `tools/release_audit.py` line 64 lists it, D-BT-016). It is not reachable from `feature/predictive-intelligence`, whose own audit passes.

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no seed phrases or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flaw overrides unchanged. Forecasts stay a separate evidence section with the flag OFF.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git log -5 --oneline
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
```

Expect `"problems": []` from the seal check and `1 failed, 1179 passed` from the suite (only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`, a known clock-dependent failure). Then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The Phase 07 runner needs the two private stores under `/home/claude/pi_research/` (rebuild them from the committed archives if the workspace was reclaimed: `phase_05/data/FEATURE_STORE_CONTRACT.md`, `phase_06/labels/TARGET_SCHEMA.md`).
