# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-055). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_09/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-25

- Phases 00 to 05: PASS. Phase 06: NEEDS_REVIEW, one item open (the frozen 48 h revision re-read, not before 2026-10-26T13:49Z). Phases 07 and 08: PASS, PROVISIONAL under PI-D-046.
- Phase 09 (on-chain, liquidity, wallet and authority forecasts): NEEDS_REVIEW after its first pass. Every gate item holds on the phase agent's checks; the independent skeptic (PI-D-013) is the orchestrator's next step, then a repair pass. All numbers PROVISIONAL under PI-D-046. Commits (local only; the orchestrator pushes): pre-registration `3079af1`, code `15bc5b5`, runner repairs `a52233c` and `18bd243`, outputs and records `934d2d4`, and a post-commit records commit on top. Post-commit at `934d2d4`: suite `1 failed, 1272 passed` (known failure only), guard 0 violations, seal check 0 problems, single-branch release audit exit 0.
- Spend: 0 Firecrawl credits; Phase 09 made no vendor or network call (one `git fetch` of `origin/feature/backtesting`).

## What Phase 09 found

- Data sufficiency: no historical reserves, quotes, swaps, holder distributions, wallet flows or authority histories exist for the lab's decisions, and none is substituted by a modern read. What exists is the lab's own on-chain reading inside each exported thesis and token row (fatal flags, score-breakdown rationale, snapshot fields, token program). Phase 09 turns it into the as-of feature set onchain-1 (`memelab/predictive/onchain.py`, PI-D-054): 0 unparseable values over 925 Solana decisions, availability at the export commit, capture delay median 17 min and up to 21.6 h.
- Models (PI-D-055): the simple on-chain rule R1, the veto alarm R0 (counts only), the on-chain logistic M1, M2 (with B2's columns, primary), M3 (with change features) and A1 (B2 on M2's rows). Every model passes the training gate in every fold; every verdict is INSUFFICIENT_DAYS (T2: 8 out-of-sample rows, 1 positive, 1 day; T1: 24, 8, 3 days) or INSUFFICIENT_EVENTS (T1b: 44, 3, 5 days). Nothing is better or worse than the base rate, B2 or the simple rule as far as this data can tell. All MODEL_NOT_PROMOTED. Same folds and B0/B2 numbers as Phase 07 (76 of 76).
- Authority features have no variance in development (0 of 240 decisions with mint or freeze authority active). The R0 veto alarm on T2 out of sample: 0 hits, 1 miss, 1 false alarm, 6 correct rejections (counts only).
- Execution semantics: `onchain.decision_support` keeps every lab fatal flag as a veto no forecast clears; `size_cap_usd` uses depth only and is EXECUTION_DATA_MISSING on every decision here.
- Collector (PI-D-044): read-only adapter `memelab/predictive/depth_adapter.py` against the documented schema of migration 2 (no import of `memelab.backtest`); this checkout has no collector database (COLLECTOR_NOT_AVAILABLE); fixture-tested only (TEST_ONLY). Counterexample CX-09: a collector read captured after the decision is never a feature of that decision.
- Liquidity drawdown, exit capacity and distribution stay DEFERRED or BLOCKED; written as proposals in `phase_09/models/LIQUIDITY_TARGET_PROPOSALS.md`, not frozen, registry unchanged.
- Real cross-checks: authority 33 of 33 agree between the lab DB and the export; the token program of one mint (`6GmAFSYs...`) disagrees; swaps against candles agree on one mint and differ on four (pool fragmentation, latest-trades page; signatures truncated, no on-chain verification possible); 19 exchange holders never insider; one dev wallet looks like a mint (`55Vr2VpS...`).
- Checks: traps NC2-OC 170 of 170, P13-OC 15 of 15, P36-OC, CX-09; trace recomputed independently (0 differences); oracle newton-cholesky within 1.75e-11 on 48 real designs; 43 tests; mutation probe 55 of 55; two runs identical.

## What exists now

- Targets frozen before any price data was read (Phase 01): T1 +25% before -15% within 24 h; T1b the same within 6 h; T2 half the reference price or a trading halt within 24 h. Price-path labels only, no fill, size, depth or profit claims.
- Code (flag OFF, imported by no existing module): `memelab/predictive/` contract, decisions, runtime, store, sources, features, labels, stats, baselines, technical, onchain, depth_adapter, with `tests/test_predictive_*.py`.
- Data: point-in-time feature store (1,500 decisions, 3,000 snapshots), development labels (T1 136 with 34 positive, T1b 224 with 26, T2 131 with 28), holdout labels sealed in `phase_06/sealed/` (open only in Phase 12 after `check_seal.py`). Frozen cards for Phase 12: `phase_07/artifacts/`, `phase_08/artifacts/`, `phase_09/artifacts/`.

## Open items, in order

1. Phase 09 independent skeptic and repair pass (orchestrator), then the post-repair records.
2. Phase 06 48 h revision re-read: `python -B audits/predictive-intelligence/phase_06/probes/make_labels.py reread48`, at or after 2026-10-26T13:49Z. If any development label changes: rerun `phase_07/probes/run_baselines.py` at `f977aab`, `phase_08/probes/run_technical.py` at `e81ee46` and `phase_09/probes/run_onchain.py` at `18bd243` (or later), commit the superseding outputs and record it.
3. Collector deployment on Elving's computer (backtesting RUNBOOK); once rows exist, measure the adapter's link rate before any proposal is frozen.

## Waiting on Elving

- Any paid data, LLM, Zep or MiroFish use; adding research packages to the lab's runtime; a merge into `main`; deploying the forward depth collector (already approved, PI-D-044; not yet done).

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (a reviewed false positive on that branch, D-BT-016; PI-D-049 item 6). It is not reachable from `feature/predictive-intelligence`, whose own audit passes on a single-branch clone.

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no seed phrases or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flag overrides unchanged. Forecasts stay a separate evidence section with the flag OFF.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git log -8 --oneline
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
```

Expect `"problems": []` from the seal check and `1 failed, 1272 passed` from the suite (only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`, a known clock-dependent failure). Then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The Phase 07 to 09 runners need the two private stores under `/home/claude/pi_research/` (rebuild them from the committed archives if the workspace was reclaimed: `phase_05/data/FEATURE_STORE_CONTRACT.md`, `phase_06/labels/TARGET_SCHEMA.md`).
