# Predictive Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Phase 05 evidence: `audits/predictive-intelligence/phase_05/` (PHASE_05_EVIDENCE.md, PHASE_05_RESULTS.json, ACCEPTANCE_CHECKLIST.md, SKEPTIC_PACKET.md, skeptic/, data/, evidence/, probes/, raw/, postcommit/). Earlier phases stay in `phase_00/` to `phase_04/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position

- Phase 05 (immutable temporal evidence and feature store): PASS, 2026-10-24, after the repair pass that folds in the orchestrator's independent skeptic (no material failure, 4 minor findings, `phase_05/skeptic/PHASE_05_SKEPTIC.md`; PI-D-039).
- Branch `feature/predictive-intelligence`, four Phase 05 commits on top of `074953d`: first pass `b4baa78` and its records commit `c89bb02`, the repair commit `7116c55` and the records commit on top of it (read its hash with `git log -1`; this file is part of it). Not pushed. Spend 0 credits; 155 free GeckoTerminal calls by the phase, 4 by the skeptic.
- Code: `memelab/predictive/store.py`, `sources.py`, `features.py` (standard library only, flag OFF, imported by no existing module); `__init__.py` docstring. Tests: `tests/test_predictive_asof_store.py` (43), `test_predictive_asof_features.py` (26), `test_predictive_asof_fixture.py` (4); fixtures `tests/fixtures/predictive/asof_*`. Nothing else under `memelab/` or `tests/` changed; nothing under `inbox/`, `state/` or `data/`.

## What the repair changed

- m1, counterexample CX-05: the vendor token parameter is read from the URL actually sent (`store.url_token`); a read whose recorded parameters disagree is refused; only `token == mint` counts (else OTHER_TOKEN_PARAM, refused). The CX-05 test fails on the first-pass code.
- m2: a short or empty vendor page is no longer taken as the whole history (`cover_complete` always 0); BEFORE_FIRST_CANDLE removed; feature version 2 (`asof-2`); store and snapshots rebuilt offline: 102 values of 16 decisions moved to OUTSIDE_FETCHED_WINDOW, the `BvkPHKx2...` values among them; "58 of 115 series" claim withdrawn.
- m3: tests for the skeptic's five surviving mutations; while writing them, an earlier read of another candle period was found to count as covering a position, fixed (`store.url_period`). 43 of 43 mutations caught.
- m4: the truncation proof's limit (provider mode keeps retrieval metadata) is stated in the evidence.

## What Phase 05 holds

- A private SQLite store, append-only `predictive_*` tables, reversible migration, never the tracked DB (PI-D-036); 1,500 decision events from 89 exports at `98338a8`; a bounded backfill of the 541 development-period decisions on 96 pools with the holdout untouched; 3,000 snapshots of 32 features in provider and capture modes.
- Real-data proofs after the repair: truncation 0 differences over 1,500 decisions in each mode, traps 40 of 40 at the decision and 0 of 40 one second after, 3,000 of 3,000 snapshots equal their recomputation, rebuild from the committed archive identical, determinism across fresh processes.
- Findings for later phases: request `token=<mint>` (9 of 96 pools have the mint as quote; Phase 04 bake-off events affected 8 of 102 and 9 of 159, PI-D-038); candle opens, highs and lows can depend on the request window; an empty page is not evidence of no trade; give `ingest_exports` the full history (PI-D-037, PI-D-039).

## Tests

- Entry gate at `074953d`: `1 failed, 993 passed in 146.88s` (known failure only).
- First pass post-commit at `b4baa78`: `1 failed, 1059 passed`.
- Repair post-commit at `7116c55`: `1 failed, 1066 passed in 166.97s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; guard exit 0 with no violations; release audit with history exit 0, "Needs action: no"; CLI regression identical.
- Strays after each run: `data/reports/<stamp>_BRETT_0x532f.md` (removed by hand); tracked DB sha256 `068287c0...` unchanged.

## Blockers and open items

- None. PI-D-020 (forward depth and quote collector) stays PROPOSED for Elving.

## Approvals needed

None for Phase 06. Paid data, LLM, Zep or MiroFish use, any scheduled collector, copying AGPL or GPL code, adding a research package to the lab's runtime, or a merge into `main` need Elving (PI-D-005, PI-D-032).

## Next

Next eligible phase after the orchestrator verifies Phase 05: 06 (outcome label registry and censoring). It starts from the Phase 05 constraints in ROADMAP.md: `token=<mint>` on every read with the store's identity check, the 9 quote-side pools' paths re-read with the parameter, highs and lows window-dependent, an empty page never read as a halt, the 48 h re-read of at least 10% of label series (PI-D-018), `runtime.refuse_bakeoff_labels` on every label source.

## Exact next command

```
cd /home/claude/memelab-inbox && git checkout feature/predictive-intelligence && git log -5 --oneline && python -m memelab social guard && python -m pytest tests/test_predictive_asof_store.py tests/test_predictive_asof_features.py tests/test_predictive_asof_fixture.py -q && python -m pytest tests -q
```

Expect four Phase 05 commits on top of `074953d`, `"violations": []`, `73 passed`, and `1 failed, 1066 passed`; then remove `data/reports/*_BRETT_*.md` by hand.
