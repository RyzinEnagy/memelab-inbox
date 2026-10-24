# Predictive Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Phase 01 evidence: `audits/predictive-intelligence/phase_01/` (PHASE_01_EVIDENCE.md, PHASE_01_RESULTS.json, ACCEPTANCE_CHECKLIST.md, architecture/, probes/, SKEPTIC_PACKET.md). Phase 00 evidence stays in `phase_00/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position

- Phase in progress: 01 (gap analysis, placement and prediction requirements), 2026-10-24. Status NEEDS_REVIEW: every gate item holds on the phase agent's own checks; the orchestrator runs the independent skeptic (PI-D-013), then a repair pass folds it in before PASS.
- Branch `feature/predictive-intelligence`. Phase 01 commits on top of `94be1bf`: `b6f2621` (pre-registration, 2026-10-24T01:35:23Z, before any price data was read), `e64c6ca` (content), `27df593` (hash record) and a results-hash refresh (see "Commit").
- Code added: `memelab/predictive/__init__.py`, `memelab/predictive/contract.py` (format-only contract, registry, validator, reference-price and path helpers), `tests/test_predictive_contract.py` (21 tests), `tests/fixtures/predictive/forecast_examples_format_only.json`. No existing module imports it; flag `predictive.enabled` defaults OFF. No existing file outside the predictive namespaces changed; nothing under `inbox/`, `state/` or `data/` changed. Not pushed (PI-D-003). Spend 0 credits.

## What Phase 01 decided

- Primary targets (PI-D-014): T1 `price_path_target_before_invalidation_24h` (+25% before -15%), T1b the same at 6 h, T2 `price_path_severe_drawdown_or_halt_24h` (low at half the reference, or no trade from 18 h to 48 h). Price path only: no position size, caveats PRICE_PATH_NOT_PROCEEDS and NO_HISTORICAL_EXECUTABLE_DEPTH. Exit-adjusted target BLOCKED (no historical depth, P08); liquidity degradation DEFERRED (forward collection, PI-D-020 PROPOSED); failed breakout DEFERRED to Phase 08; catalyst and distribution BLOCKED_NO_DATA; 7 d and launch cohort EXPLORATORY. Registry fingerprint `9f8c9debdb66b28ab5d758c29d67f46f287965aa0d0bf2c1a64a94f9733d9912`, pinned by a test.
- Decision time (PI-D-015): first export commit time on `main` (the thesis row is inside the commit; push events confirm the commit clock within 5 s for 82 of 89 exports); prospective: capture time. Never `theses.created_at`.
- Change control CC-01 (PI-D-019, from the phase's own attack, before any label): the reference price must come from a candle available at the decision; eligibility before thinning; same-commit theses count once.
- Acceptance plan (PI-D-016): development before 2026-10-17, sealed retrospective holdout [2026-10-17, 2026-10-24), prospective holdout from 2026-10-24; minimums 100 training (20 per class), 50 holdout (10 per class), 20 per bin; Brier primary with day and mint bootstrap and Holm across three targets; Wilson-interval calibration tolerance; levels ABSTAIN, SHADOW, VALIDATED_EXPERIMENTAL, NO_GO; no trading-edge claim is possible from this data.
- Placement (PI-D-017): forecasts are a separate section after m24, never feeding score, fatal flags, status or watchlist; reuse `replay_core` LeakageError, cutoff view and LabelGate, `outcomes_core` observation checks, the `outcomes_ledger` journal (separate file, barrier evaluator through `evaluate_all`), `replay_sources.PROVIDER_LAG`, `alpha_core.wilson`, the appended report pattern. Not reused, with reasons: alpha_store candles, catalyst outcomes, launch horizons.
- Label source (PI-D-018): bounded GeckoTerminal 5-minute backfills, 6 calls a minute or less, 1,200 per run, retrieval time and sha256 kept, revision re-reads.

## What the data allow

- Thinned Solana decisions before eligibility: development 177 / 280 / 161 and retrospective holdout 58 / 79 / 49 (T1 / T1b / T2). A 10-decision coverage sample: 5 OK, 4 without a trade in the hour before the decision, 1 rate-limited. The retrospective holdout may end up under 50 eligible events; the prospective holdout is the evaluation that counts, and needs about one to two weeks or more of daily exports.
- Power arithmetic: with 50 holdout events even a true Brier skill score of 0.10 is detected about a quarter of the time. Expected outcome: "not distinguishable from the base rate" or INSUFFICIENT_HISTORY.
- Gap matrix: 88 cells, 16 VERIFIED_PRESENT, 23 PARTIAL, 46 MISSING, 3 CONFLICT (GeckoTerminal pacing, catalyst outcomes, thesis clock). Backtesting v1.2 still BACKTEST_NOT_AVAILABLE.

## Tests

- Entry gate at `94be1bf`: `python -m pytest tests -q` exit 1, `1 failed, 785 passed in 137.59s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known).
- Final: `python -m pytest tests -q` exit 1, `1 failed, 806 passed in 136.72s (0:02:16)`, same single known failure (806 = 785 + 21 new).
- `python audits/predictive-intelligence/phase_01/probes/mutation_check.py`: 10 of 10 mutations caught. `check_gap_anchors.py`: 88 cells, 0 problems. `check_doc_anchors.py`: 34 anchors, 0 problems.
- Strays after each suite run: `data/reports/<stamp>_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`, `.pytest_cache/`; removed by hand; tracked DB sha256 `068287c0...a6679ca` unchanged.

## Blockers and open items

- None blocking Phase 02.
- PI-D-020 (forward depth and quote collector, a scheduled job) is PROPOSED for Elving; nothing is planned or built without his approval.
- GeckoTerminal 5-minute retention beyond 17 days is UNKNOWN; Phase 06 should backfill early.
- Windows-side items from Phase 00 remain BLOCKED for verification (Crawl4AI token file, Maxun, scheduled task definitions).

## Approvals needed

None for Phase 02. Paid data, LLM, Zep or MiroFish use, any scheduled collector (PI-D-020), or a merge into `main` need Elving (PI-D-005).

## Next

The orchestrator runs the independent skeptic on `audits/predictive-intelligence/phase_01/SKEPTIC_PACKET.md` and returns the review; the phase agent then verifies each finding, copies the review into `audits/predictive-intelligence/phase_01/skeptic/`, updates the evidence and records, and sets the final status. Next eligible phase after PASS: 02 (independent predictive GitHub discovery).

## Commit

- Pre-registration `b6f26218002a009e6d96bf17bde9188d5e809758` (2026-10-24T01:35:23Z); content `e64c6cae0b9d66c77f03f1049fa693282a25d823` (2026-10-24T01:56:38Z); hash record `27df593`; a last commit refreshes the artifact hashes in PHASE_01_RESULTS.json (read it with `git log -1`).
- `git diff --name-only 94be1bf..HEAD` lists only files under `docs/predictive-intelligence/`, `audits/predictive-intelligence/`, `memelab/predictive/`, `tests/test_predictive_contract.py` and `tests/fixtures/predictive/`.
- Not pushed. `git status` clean after the commit.

## Exact next command

```
cd /home/claude/memelab-inbox && git checkout feature/predictive-intelligence && git log -4 --oneline && python -m pytest tests -q
```

Expect the four Phase 01 commits (`b6f2621` pre-registration, `e64c6ca` content, `27df593` hash record, then the results-hash refresh that also carries this line) on top of `94be1bf` and `1 failed, 806 passed`; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm`, `-wal` and `.pytest_cache/` by hand.
