# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-058). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_10/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-26

- Phases 00 to 05: PASS. Phase 06: NEEDS_REVIEW, one item open (the frozen 48 h revision re-read, not before 2026-10-26T13:49Z). Phases 07 to 09: PASS, PROVISIONAL under PI-D-046.
- Phase 10 (social and catalyst outcome forecasts): NEEDS_REVIEW after the first pass; the orchestrator's independent skeptic (PI-D-013) is next, then a repair pass. PROVISIONAL under PI-D-046. TEST_ONLY parts: the catalyst classifier, the social evidence adapter and the catalyst target proposals (no catalyst or social row exists for any decision). Commits (local only; the orchestrator pushes): pre-registration `c3f04c8`, code `0784a9a`, outputs and records on top (the post-commit records commit holds the final hash in `phase_10/PHASE_10_RESULTS.json`).
- Spend: 0 Firecrawl credits, no vendor, crawler or language-model call; one `git fetch` of `origin/main`.

## What Phase 10 found

- Data sufficiency: no social item, observation, claim, trader link or track record and no catalyst event, item, link or assessment exists for any of the lab's decisions in anything readable here (social and catalyst tables are not exported, `data/private/` is absent, every social route is BUILT on fixtures or BLOCKED). Every decision carries CATALYST_TABLES_NOT_EXPORTED and SOCIAL_TABLES_NOT_EXPORTED; no catalyst is VERIFIED and no catalyst probability exists. No crawl stands in for history (P04).
- What the lab did record at each decision is socialcat-1 (`memelab/predictive/socialcat.py`, PI-D-057): the m19 attention proxy (trend, narrative strength, organic or paid), the m20 manipulation screen, the m21 lifecycle stage, the token row's channels and narrative tag, and the narrative tables of the decision's own export; available at the export commit, LAB_RECORDED, 0 unparseable over 925 decisions. These are on-chain and market proxies, not social text. Lab-derived classes: HIGH_ATTENTION_PROXY 74, NARRATIVE_REVERSAL 56 decisions (never a verified catalyst).
- Models (PI-D-058): R2 attention rule, R3 amplification alarm (counts only), S1 attention logistic, S2 attention plus B2 (primary), S3 with change features, G1 boosted stumps, A2 B2 on S2's rows. 306 metric rows, all INSUFFICIENT_HISTORY (T2, and T1 fold 0 with 98 usable rows), INSUFFICIENT_DAYS (T1: 13 rows, 4 positive, 2 days) or INSUFFICIENT_EVENTS (T1b: 37 rows, 3 positive, 5 days); no incremental value beyond B2 claimed; all MODEL_NOT_PROMOTED; same folds and B0/B2 numbers as Phase 07.
- Leakage controls on the real history: token rows equal their own export 925 of 925 (CX-10: the newest export would add 20 narrative tags, 74 websites, 4 twitter links); a later export's tables refused 240 of 240 (P04-SC); next-decision values refused 156 of 156 (NC2-SC); snapshot time after the decision refuses all values (P36-SC); holdout-start cards refused on development decisions (P13-SC).
- Checks: 51 tests; mutation probe 85 of 85 at HEAD (1 equivalent reported apart); trace recomputed independently (0 differences); every out-of-sample number (326) recomputed without the module (0 differences); oracle newton-cholesky within 1.9e-11 on 40 real designs; two runs identical.
- Catalyst follow-through, withdrawal and amplification reversal are written as proposals only (`phase_10/models/CATALYST_TARGET_PROPOSALS.md`), registry unchanged.

## What exists now

- Targets frozen before any price data was read (Phase 01): T1 +25% before -15% within 24 h; T1b the same within 6 h; T2 half the reference price or a trading halt within 24 h. Price-path labels only, no fill, size, depth or profit claims.
- Code (flag OFF, imported by no existing module): `memelab/predictive/` contract, decisions, runtime, store, sources, features, labels, stats, baselines, technical, onchain, depth_adapter, socialcat, with `tests/test_predictive_*.py`.
- Data: point-in-time feature store (1,500 decisions, 3,000 snapshots), development labels (T1 136 with 34 positive, T1b 224 with 26, T2 131 with 28), holdout labels sealed in `phase_06/sealed/` (open only in Phase 12 after `check_seal.py`). Frozen cards for Phase 12: `phase_07/artifacts/`, `phase_08/artifacts/`, `phase_09/artifacts/`, `phase_10/artifacts/`.

## Open items, in order

1. Phase 10 independent skeptic and repair pass (orchestrator, PI-D-013): `audits/predictive-intelligence/phase_10/SKEPTIC_PACKET.md`.
2. Phase 06 48 h revision re-read: `python -B audits/predictive-intelligence/phase_06/probes/make_labels.py reread48`, at or after 2026-10-26T13:49Z. If any development label changes: rerun `phase_07/probes/run_baselines.py` at `f977aab`, `phase_08/probes/run_technical.py` at `e81ee46`, `phase_09/probes/run_onchain.py` at `e306d43` and `phase_10/probes/run_social.py` at `0784a9a` (or later), commit the superseding outputs and record it.
3. Phase 11 is eligible only after the orchestrator records Phase 10 PASS (provisional under PI-D-046).
4. Collector deployment on Elving's computer (backtesting RUNBOOK); forward social and catalyst collection would need new approvals (credentials, consent, scheduled jobs).

## Waiting on Elving

- Any paid data, LLM, Zep or MiroFish use; social API credentials or consent (X, Telegram, Reddit, Discord, YouTube, Farcaster routes are BLOCKED); scheduled catalyst or social collection into a store this engine can read; adding research packages to the lab's runtime; a merge into `main`; deploying the forward depth collector (already approved, PI-D-044; not yet done).

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (a reviewed false positive on that branch, D-BT-016; PI-D-049 item 6). It is not reachable from `feature/predictive-intelligence`, whose own audit passes on a single-branch clone.

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no seed phrases or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flag overrides unchanged. Forecasts stay a separate evidence section with the flag OFF. No raw social content in the repository.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git log -8 --oneline && git fetch origin main
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
```

Expect `"problems": []` from the seal check and `1 failed, 1330 passed` from the suite (only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`, a known clock-dependent failure). Then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The Phase 07 to 10 runners need the two private stores under `/home/claude/pi_research/` (rebuild them from the committed archives if the workspace was reclaimed: `phase_05/data/FEATURE_STORE_CONTRACT.md`, `phase_06/labels/TARGET_SCHEMA.md`); the Phase 10 runner also reads `origin/main` git objects.
