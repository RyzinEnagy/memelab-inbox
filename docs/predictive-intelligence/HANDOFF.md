# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-062). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_11/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-26

- Phases 00 to 10: PASS (Phase 06 since the frozen 48 h re-read, PI-D-059; Phase 10 after repair pass 2, PI-D-060, with TEST_ONLY parts).
- Phase 11 (analog cohorts and regime handling): NEEDS_REVIEW after its first pass. Every gate item is reproduced by the phase agent; the orchestrator's independent skeptic has not run yet (PI-D-013). Commits (local only; the orchestrator pushes): pre-registration `46afc85` (PI-D-061), frozen code `0482a60`, ledger repair `ff98b8d`, outputs and records on top (see "Phase 11 commits").
- Spend: 0 Firecrawl credits, 0 vendor calls, 0 language-model calls, no network use in Phase 11 (COST_LEDGER.md).

## What Phase 11 built and found

- `memelab/predictive/analog.py` (analog-1, numpy and the standard library, flag OFF, imported by no other module): analog pools only from `labels.training_labels` at the cohort time and checked row by row (decided before, matured by, token first seen by it; inputs available at each decision); the same mint is token history and never an analog; the same creator wallet is excluded; one analog per creator or mint cluster; effective N = clusters G, a number needs G >= 20 and 5 analog days; AC1 strata (launch age, liquidity), AC2 30 nearest clusters (liquidity, market cap, 24 h volume, token age, launchpad class, token program) with an out-of-distribution rule, AC3 (primary) AC2 restricted to the target's regime label; the as-of regime label (median 24 h volume and constructive-status share of the lab's visible decisions against the past median of earlier export instants, WARMUP below 5); the router (TOKEN_HISTORY, COHORT_ESTIMATE_NOT_TOKEN_HISTORY or ABSTAIN with reasons); divergence flags for authority, fee, token program, exit-capacity share and friction; EXECUTION_DATA_MISSING with a size.
- Result on development data: same folds and B0/B2 as Phase 07. AC3 numbers 2 of 24 (T1), 0 of 8 (T2), 21 of 44 (T1b) and abstains otherwise, almost always because its regime-matched analogs fall on fewer than 5 days (the out-of-sample days are QUIET/RISK_OFF; the regime rule refuses to copy the busier 2026-10-08 to 10-10 period). AC2 numbers 70 of 76, AC1 none. 132 metric rows, all INSUFFICIENT_DAYS, INSUFFICIENT_HISTORY or INSUFFICIENT_EVENTS, including the regime breakdown (P21) and the comparisons with the frozen primaries of Phases 08 to 10; all MODEL_NOT_PROMOTED.
- Leakage and identity on the real history: NC2-AC 27 of 27 refused, P43-AC 76 of 76, P13-AC 9 of 9, P36-AC 28 of 28; 106 mints first decided after a first cutoff never in a pool; 0 same-creator analogs (42 rows excluded); CX-11 (full-sample regime medians) relabels 32 of 74 instants and fails the truncation check, the as-of series is truncation-invariant at 79 of 79 instants.
- Checks: 51 tests; mutation probe 47 of 47; scikit-learn NearestNeighbors oracle on 148 real queries (distances within 3.9e-15); trace recomputed from plain SQL without the module (0 differences); the cohort query reproduces the trace and all 93 AC2 and AC3 numbers; two runs identical.
- Limitation to watch: 59 of 93 cohort numbers have a day Kish ESS below 5 (largest single-day share 63%); G overstates independence on batched export days. Any rule on it is a change control.

## What exists now

- Targets frozen before any price data was read (Phase 01): T1 +25% before -15% within 24 h; T1b the same within 6 h; T2 half the reference price or a trading halt within 24 h. Price-path labels only, no fill, size, depth or profit claims.
- Code (flag OFF, imported by no existing module): `memelab/predictive/` contract, decisions, runtime, store, sources, features, labels, stats, baselines, technical, onchain, depth_adapter, socialcat, analog, with `tests/test_predictive_*.py`.
- Data: point-in-time feature store (1,500 decisions, 3,000 snapshots), development labels (T1 136 with 34 positive, T1b 224 with 26, T2 131 with 28; frozen 48 h revision check passed, PI-D-059), holdout labels sealed in `phase_06/sealed/` (open only in Phase 12 after `check_seal.py`). Frozen cards for Phase 12: `phase_07/artifacts/` to `phase_11/artifacts/`.

## Open items, in order

1. The orchestrator runs Phase 11's independent skeptic (`audits/predictive-intelligence/phase_11/SKEPTIC_PACKET.md`) and returns the review for a repair pass; Phase 11 can then become PASS and Phase 12 eligible.
2. Residual risks for Phase 12: the day dependence of cohort numbers; creator missing for 115 of 925 Solana decisions (cluster falls back to the mint); regime labels describe the lab's exported universe, not chain-wide conditions.
3. Carried: catalyst source roles and event categories have no time in the lab schema; replayed social bot shares are lower bounds; collector deployment on Elving's computer (backtesting RUNBOOK); forward social and catalyst collection needs new approvals.

## Phase 11 commits

- HEAD before: `aae7a55` (pushed). Pre-registration `46afc85` (2026-10-26T15:04:46Z), frozen code `0482a60` (15:20:20Z), ledger repair `ff98b8d` (15:26:22Z), outputs and records `208cdc1` (15:33:04Z), and this post-commit record on top (local only; the orchestrator pushes). Post-commit at `208cdc1`: suite `1 failed, 1386 passed` (known failure only; stray BRETT report and sqlite -shm, -wal removed by hand), guard 0 violations, seal check 0 problems, single-branch release audit exit 0 "Needs action: no.", `git status` clean.

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
python -B audits/predictive-intelligence/phase_11/probes/verify_trace_analog.py audits/predictive-intelligence/phase_11
```

Expect `"problems": []` from the seal check and `1 failed, 1386 passed` from the suite (only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`, a known clock-dependent failure). Then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The Phase 07 to 11 runners need the two private stores under `/home/claude/pi_research/` (rebuild them from the committed archives if the workspace was reclaimed: `phase_05/data/FEATURE_STORE_CONTRACT.md`, `phase_06/labels/TARGET_SCHEMA.md`); the Phase 10 and 11 runners also read the `origin/main` commit `e245d91`.
