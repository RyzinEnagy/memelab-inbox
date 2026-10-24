# Predictive Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Phase 01 evidence: `audits/predictive-intelligence/phase_01/` (PHASE_01_EVIDENCE.md, PHASE_01_RESULTS.json, ACCEPTANCE_CHECKLIST.md, architecture/, probes/, skeptic/, SKEPTIC_PACKET.md marked USED). Phase 00 evidence stays in `phase_00/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position

- Phase completed: 01 (gap analysis, placement and prediction requirements), 2026-10-24. Status PASS after repair pass 2. It was NEEDS_REVIEW at `0decbbe`; the orchestrator's independent skeptic found 3 MATERIAL and 8 MINOR findings, all verified and fixed or answered by change control CC-02 (PI-D-021) before any label existed.
- Branch `feature/predictive-intelligence`. Phase 01 commits on top of `94be1bf`: `b6f2621` (pre-registration, before any price data was read), `e64c6ca` (content), five hash-bookkeeping commits up to `0decbbe`, then the repair pass 2 commit (see "Commit").
- Code added: `memelab/predictive/__init__.py`, `contract.py` (format-only contract, registry, acceptance plan, validator, reference-price, path and eligibility helpers), `decisions.py` (point-in-time decision records), `tests/test_predictive_contract.py` and `tests/test_predictive_decisions.py` (73 tests), fixtures in `tests/fixtures/predictive/`. No existing module imports the package (checked on the syntax tree); the flag `predictive.enabled` defaults OFF and gates nothing yet. No existing file outside the predictive namespaces changed; nothing under `inbox/`, `state/` or `data/` changed. Not pushed (PI-D-003). Spend 0 credits.

## What Phase 01 decided

- Primary targets (PI-D-014): T1 `price_path_target_before_invalidation_24h` (+25% before -15%), T1b the same at 6 h, T2 `price_path_severe_drawdown_or_halt_24h`. Price path only, no position size. Exit-adjusted target BLOCKED (no historical depth, P08); liquidity degradation DEFERRED (forward collector, PI-D-020 PROPOSED); failed breakout DEFERRED to Phase 08; catalyst and distribution BLOCKED_NO_DATA; 7 d and launch cohort EXPLORATORY.
- Decision records (PI-D-015 as amended by PI-D-021): `memelab/predictive/decisions.py`, identity `(mint, created_at, row_sha256)`, time = commit time of the first export (first-parent history) holding the exact row, newest visible row per commit, KEY_CONFLICT flagged (4 of 278 thinned 24 h events) with a sensitivity run. Never key decisions on `(mint, created_at)` through `state.import_` (skeptic counterexample CX-S1).
- Eligibility (PI-D-019, PI-D-021): reference candle available at the decision; classes ELIGIBLE, MARKET_INACTIVE (evidence available at the decision), VENDOR_OR_ROUTE_GAP (censored, counted, conservative lens).
- Acceptance plan (PI-D-016, PI-D-021): every rule frozen in `contract.ACCEPTANCE` inside the fingerprint `91d03c769dde1d8cbba0f6a40257e7e3c060544ddb2f2b6b8a17556554b5a81a`, which a test pins; ACCEPTANCE_METRICS.md carries it verbatim (tested). Retrospective holdout [2026-10-17, 2026-10-24) sealed, minus two decisions whose price data Phase 01 fetched (`CnPL1x...` 10-17, `Tm2iq...` 10-19); prospective holdout from 2026-10-24. Only nine constants were frozen before any price data was read; the rest were written after the coverage probe and frozen before any label (stated in the documents).
- Placement (PI-D-017): separate evidence section after m24, never feeding score, fatal flags, status or watchlist; reuse of the replay leakage pattern, LabelGate, outcomes_core checks, the outcomes_ledger journal, PROVIDER_LAG, Wilson intervals and the appended report pattern.
- Label source (PI-D-018): bounded GeckoTerminal 5-minute backfills, 6 calls a minute or less, 1,200 per run.
- Contract checks owed by later phases (PI-D-022): model card authenticity, calibration reference contents, snapshot hash to decision row, nested forbidden keys, base58 decoding.

## What the data allow

- Thinned Solana decision events before eligibility: development 177 / 280 / 161 and retrospective holdout 58 / 79 / 49 (T1 / T1b / T2). Coverage sample of 10 with the CC-02 classes: 5 ELIGIBLE, 3 MARKET_INACTIVE, 1 VENDOR_OR_ROUTE_GAP, 1 not read. The retrospective holdout will likely end under 50 eligible events; the prospective holdout is the evaluation that counts.
- Expected outcome stated in advance: "not distinguishable from the base rate" or INSUFFICIENT_HISTORY.

## Tests

- Entry gate at `94be1bf`: `python -m pytest tests -q` exit 1, `1 failed, 785 passed in 137.59s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known).
- Final after repair pass 2: `python -m pytest tests -q` exit 1, `1 failed, 858 passed in 136.08s (0:02:16)`, same single known failure (858 = 785 + 73 predictive).
- `mutation_check.py`: 36 of 36 mutations caught (includes the skeptic's twelve). `check_gap_anchors.py`: 88 cells, 0 problems. `check_doc_anchors.py`: 34 anchors, 0 problems.
- Strays after each suite run: `data/reports/<stamp>_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`, `.pytest_cache/`; removed by hand; tracked DB sha256 `068287c0...a6679ca` unchanged.

## Blockers and open items

- None blocking Phase 02.
- PI-D-020 (forward depth and quote collector, a scheduled job) is PROPOSED for Elving.
- GeckoTerminal 5-minute retention beyond 17 days is UNKNOWN; Phase 06 should backfill early. The share of VENDOR_OR_ROUTE_GAP in the population is unknown until then.
- Windows-side items from Phase 00 remain BLOCKED for verification.

## Approvals needed

None for Phase 02. Paid data, LLM, Zep or MiroFish use, any scheduled collector (PI-D-020), or a merge into `main` need Elving (PI-D-005).

## Next

Next eligible phase: 02 (independent predictive GitHub discovery), after the orchestrator verifies repair pass 2.

## Commit

- Pre-registration `b6f26218002a009e6d96bf17bde9188d5e809758`; content `e64c6cae0b9d66c77f03f1049fa693282a25d823`; bookkeeping up to `0decbbe`. The repair pass 2 commit is the next commit on top of `0decbbe` and is HEAD (read its hash with `git log -1`; this file is part of it).
- `git diff --name-only 94be1bf..HEAD` lists only files under `docs/predictive-intelligence/`, `audits/predictive-intelligence/`, `memelab/predictive/`, `tests/test_predictive_*.py` and `tests/fixtures/predictive/`.
- Not pushed. `git status` clean after the commit.

## Exact next command

```
cd /home/claude/memelab-inbox && git checkout feature/predictive-intelligence && git log -3 --oneline && python -m pytest tests -q
```

Expect the repair pass 2 commit on top of `0decbbe` and `1 failed, 858 passed`; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm`, `-wal` and `.pytest_cache/` by hand.
