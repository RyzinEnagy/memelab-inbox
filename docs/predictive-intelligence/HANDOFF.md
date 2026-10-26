# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-060). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_10/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-26

- Phases 00 to 10: PASS. Phase 06 became PASS on 2026-10-26 when the frozen 48 h revision re-read ran (PI-D-059): 16 of 16 sampled reads re-read 48.0 to 48.9 h later, 12,617 candle positions compared, 0 changed (0 close, 0 volume, 0 open, high or low), 0 appeared or vanished; 44 development labels re-derived, 0 changed, no revision row; an independent comparison without the lab's code agrees. 20 free GeckoTerminal calls (4 HTTP 429 retried), at most 6 a minute. No rerun of Phases 07 to 10 is owed; PI-D-046's provisional condition is lifted for the revision check (outputs not rewritten). Commit `c127b08` (see "Phase 06 re-read commits" below).
- Phase 10 (social and catalyst outcome forecasts): PASS on 2026-10-26 after repair pass 2 (PI-D-060). TEST_ONLY parts: the catalyst classifier, the social evidence adapter and the catalyst target proposals (no catalyst or social row exists for any decision). The orchestrator's independent skeptic found 2 MATERIAL, both in those TEST_ONLY parts, and 6 minor; no real-data number changed. Commits (local only; the orchestrator pushes): pre-registration `c3f04c8`, code `0784a9a`, outputs and records `f4b3a89`; repair code `1c75a12`, repair outputs `06999b7`, repair records and post-commit records on top (see "Phase 10 repair commits").
- Spend: 0 Firecrawl credits; Phase 10 made no vendor, crawler or language-model call (one `git fetch` of `origin/main`); the Phase 06 re-read made 20 free GeckoTerminal calls (COST_LEDGER.md).

## What Phase 10 found

- Data sufficiency: no social item, observation, claim, trader link or track record and no catalyst event, item, link or assessment exists for any of the lab's decisions in anything readable here (social and catalyst tables are not exported, `data/private/` is absent, every social route is BUILT on fixtures or BLOCKED). Every decision carries CATALYST_TABLES_NOT_EXPORTED and SOCIAL_TABLES_NOT_EXPORTED; no catalyst is VERIFIED and no catalyst probability exists. No crawl stands in for history (P04).
- What the lab did record at each decision is socialcat-1 (`memelab/predictive/socialcat.py`, PI-D-057): the m19 attention proxy (trend, narrative strength, organic or paid), the m20 manipulation screen, the m21 lifecycle stage, the token row's channels and narrative tag, and the narrative tables of the decision's own export; available at the export commit, LAB_RECORDED, 0 unparseable over 925 decisions. These are on-chain and market proxies, not social text. Lab-derived classes: HIGH_ATTENTION_PROXY 74, NARRATIVE_REVERSAL 56 decisions (never a verified catalyst).
- Models (PI-D-058): R2 attention rule, R3 amplification alarm (counts only), S1 attention logistic, S2 attention plus B2 (primary), S3 with change features, G1 boosted stumps, A2 B2 on S2's rows. 306 metric rows, all INSUFFICIENT_HISTORY (T2, and T1 fold 0 with 98 usable rows), INSUFFICIENT_DAYS (T1: 13 rows, 4 positive, 2 days) or INSUFFICIENT_EVENTS (T1b: 37 rows, 3 positive, 5 days); no incremental value beyond B2 claimed; all MODEL_NOT_PROMOTED; same folds and B0/B2 numbers as Phase 07.
- Leakage controls on the real history: token rows equal their own export 925 of 925 (CX-10: the newest export would add 20 narrative tags, 74 websites, 4 twitter links); a later export's tables refused 240 of 240 (P04-SC); next-decision values refused 156 of 156 (NC2-SC); snapshot time after the decision refuses all values (P36-SC); holdout-start cards refused on development decisions (P13-SC).
- Checks: 56 tests; mutation probe 102 of 102 at HEAD (1 equivalent reported apart); trace recomputed independently (0 differences); every out-of-sample number (326) recomputed from the cards without the module (0 differences); oracle newton-cholesky within 1.9e-11 on 40 real logistic designs and GradientBoostingClassifier within 2.2e-16 on the 10 fitted G1 stump designs; two runs identical.
- Catalyst follow-through, withdrawal and amplification reversal are written as proposals only (`phase_10/models/CATALYST_TARGET_PROPOSALS.md`), registry unchanged.

## What the Phase 10 repair changed (PI-D-060)

- CX-10b-A (M1): a VERIFIED catalyst is available only from the time its last condition held (link, item naming the mint, start of CONFIRMED in the revision log, official item naming the mint or second independent item), classified as of the decision; a follow-through window starts at `max(available_at, decision) + lag` and an availability after the decision is refused. The first-pass rule is withdrawn from the proposals.
- CX-10b-B (M2): `social_as_of` applies a suspension only when recorded by the decision (`identity_checked_at` and the ACCOUNT_STATUS review) and treats `account_kind` (no time in the lab schema) as UNKNOWN in a replay; live callers pass `accounts_read_at`. Replayed bot shares are lower bounds.
- Minors: provenance lists the adjacent lab rows that name decision mints (`social_snapshots`, launch tables, inbox boosts and metadata; none used); "paid/boosted" is m19's organic flag (mostly organic score below 40); item versions recorded after T ignored; G1 stumps checked by the Phase 08 oracle; an item without a role is not independent, OFFICIAL / STRONG is a strong link, an official source must name the mint; the runner reads the pinned `origin/main` commit `e245d91`.
- Frozen-code discipline: the recorded run was repeated at `1c75a12`; every metric, card, fold, prediction, ledger and trap file is byte-equal to the first pass (trace latency only). Evidence: `phase_10/PHASE_10_EVIDENCE.md` section "Independent skeptic and repair pass 2", `evidence/cx10b_check.json`, `evidence/determinism.json`.

## What exists now

- Targets frozen before any price data was read (Phase 01): T1 +25% before -15% within 24 h; T1b the same within 6 h; T2 half the reference price or a trading halt within 24 h. Price-path labels only, no fill, size, depth or profit claims.
- Code (flag OFF, imported by no existing module): `memelab/predictive/` contract, decisions, runtime, store, sources, features, labels, stats, baselines, technical, onchain, depth_adapter, socialcat, with `tests/test_predictive_*.py`.
- Data: point-in-time feature store (1,500 decisions, 3,000 snapshots), development labels (T1 136 with 34 positive, T1b 224 with 26, T2 131 with 28; frozen 48 h revision check passed, PI-D-059), holdout labels sealed in `phase_06/sealed/` (open only in Phase 12 after `check_seal.py`). Frozen cards for Phase 12: `phase_07/artifacts/`, `phase_08/artifacts/`, `phase_09/artifacts/`, `phase_10/artifacts/`.

## Open items, in order

1. The orchestrator re-verifies Phase 10 and pushes; Phase 11 (analog cohorts and regimes) is eligible once it records Phase 10 PASS.
2. Residual Phase 10 risks for later phases: catalyst source roles and event categories have no time in the lab schema; replayed social bot shares are lower bounds (no timed bot label exists).
3. Collector deployment on Elving's computer (backtesting RUNBOOK); forward social and catalyst collection would need new approvals (credentials, consent, scheduled jobs).

## Phase 10 repair commits

- HEAD before: `70bd8d9` (pushed). Repair code `1c75a12` (2026-10-26T14:34:34Z), outputs `06999b7` (recorded run at `1c75a12`, 14:34:40Z), records commit on top, then a post-commit records commit (local only; the orchestrator pushes). Post-commit results are recorded in `PHASE_10_RESULTS.json` (G27 repair entries) and the evidence file.

## Phase 06 re-read commits

- HEAD before: `564be76` (pushed). Re-read commit `c127b08`, with this record on top (local only; the orchestrator pushes). Post-commit at `c127b08`: suite `1 failed, 1330 passed` (known failure only), guard 0 violations, seal check 0 problems, single-branch release audit exit 0. Details: `audits/predictive-intelligence/phase_06/PHASE_06_EVIDENCE.md` (section "48 h revision re-read") and `PHASE_06_RESULTS.json`.
- The development store `/home/claude/pi_research/p06/dev_store.sqlite` now also holds the 16 second reads (raw rows only, no label rows added); a copy taken before the re-read is in `/home/claude/pi_research/p06/backup_pre_reread48/`. The second bodies are committed in `phase_06/raw_reread48/`.

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

Expect `"problems": []` from the seal check and `1 failed, 1335 passed` from the suite (only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`, a known clock-dependent failure). Then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The Phase 07 to 10 runners need the two private stores under `/home/claude/pi_research/` (rebuild them from the committed archives if the workspace was reclaimed: `phase_05/data/FEATURE_STORE_CONTRACT.md`, `phase_06/labels/TARGET_SCHEMA.md`); the Phase 10 runner also reads `origin/main` git objects.
