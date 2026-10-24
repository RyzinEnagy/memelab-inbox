# Predictive Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Phase 05 evidence: `audits/predictive-intelligence/phase_05/` (PHASE_05_EVIDENCE.md, PHASE_05_RESULTS.json, ACCEPTANCE_CHECKLIST.md, SKEPTIC_PACKET.md, data/, evidence/, probes/, raw/, postcommit/). Earlier phases stay in `phase_00/` to `phase_04/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position

- Phase 05 (immutable temporal evidence and feature store): NEEDS_REVIEW, 2026-10-24, first pass complete; waiting for the orchestrator's independent skeptic (PI-D-013), then a repair pass sets the final status.
- Branch `feature/predictive-intelligence`: the Phase 05 deliverables commit `b4baa78` and the records commit on top of it (read its hash with `git log -1`; this file is part of it), both on `074953d`. Not pushed. Spend 0 credits; 155 free GeckoTerminal calls.
- Code added: `memelab/predictive/store.py`, `sources.py`, `features.py` (standard library only, flag OFF, imported by no existing module); `memelab/predictive/__init__.py` docstring lists the modules. Tests: `tests/test_predictive_asof_store.py` (37), `test_predictive_asof_features.py` (25), `test_predictive_asof_fixture.py` (4); fixtures `tests/fixtures/predictive/asof_helpers.py`, `asof_pid011_export.json`, `asof_fixture.json`. No other file under `memelab/` or `tests/` changed; nothing under `inbox/`, `state/` or `data/` changed.

## What Phase 05 built and found

- A private SQLite store with eight append-only `predictive_*` tables and a reversible, checksum-guarded migration; never the tracked lab DB (PI-D-036). Contract and schema: `phase_05/data/FEATURE_STORE_CONTRACT.md`; source matrix and counts: `phase_05/data/SOURCE_COVERAGE.md`.
- 1,500 decision events from the 89 exports at `98338a8` (one 31-byte "mint" refused), a bounded GeckoTerminal backfill of the 541 development-period Solana decisions on 96 pools (holdout, purged and prospective decisions untouched), 74,541 candle versions, 3,000 feature snapshots (32 features, provider and capture modes).
- As-of proofs on real data: truncation invariance 0 differences over 1,500 decisions in each mode; 40 of 40 traps change the snapshot when available at the decision and 0 of 40 one second after; 3,000 of 3,000 stored snapshots equal their recomputation after a re-read; a rebuild from the committed raw archive gives identical hashes; determinism across fresh processes. 35 of 35 mutations caught.
- Findings: (1) reads without `token=<mint>` priced another token for 9 of 96 pools, including 8 of 102 T1 and 9 of 159 T1b Phase 04 BAKEOFF_ONLY events, and a vendor's default side can change over time (PI-D-038); (2) a candle's open, high or low depends on the request window (80 of 57,584 candles; closes and volumes stable), so features use closes and volumes only; (3) a partial export history would mint false decisions, so the store refuses it (PI-D-037).

## How to check it

From the repository root: `python -m pytest tests/test_predictive_asof_store.py tests/test_predictive_asof_features.py tests/test_predictive_asof_fixture.py -q` (66 passed). From `audits/predictive-intelligence/phase_05/probes/` with the store at `/home/claude/pi_research/p05/predictive_store.sqlite`:

```
python -B asof_real_checks.py truncation      # 0 differences in both modes (about 8 min)
python -B asof_real_checks.py traps           # after_1s_changed 0, at_decision_changed 40
python -B asof_real_checks.py recompute       # differ 0, verify []
python -B build_store.py fromarchive /tmp/p05_rebuild.sqlite   # identical true (offline)
python -B mutation_asof.py /tmp/mut05.json    # 35 of 35 caught
python -B revision_check.py p04               # 80 changed of 57,584, all in open, high or low
```

## Tests

- Entry gate at `074953d`: `1 failed, 993 passed in 146.88s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known).
- Pre-commit: `1 failed, 1059 passed in 151.20s` (993 plus 66), only the known failure.
- Post-commit on `b4baa78`: suite `1 failed, 1059 passed in 165.68s` (known failure only), `python -m memelab social guard` exit 0 with no violations, `python tools/release_audit.py --history` exit 0 "Needs action: no", CLI regression `074953d` against `b4baa78` in two clean clones identical (`phase_05/postcommit/`).
- Strays after each run: `data/reports/<stamp>_BRETT_0x532f.md` (removed by hand); `data/memelab.sqlite-shm` and `-wal` existed before this phase and are ignored; tracked DB sha256 `068287c0...` unchanged.

## Blockers and open items

- None for the skeptic. PI-D-020 (forward depth and quote collector) stays PROPOSED for Elving.
- For Phase 06: request `token=<mint>` and pass `store.gt_identity`; re-read label paths of the 9 quote-side pools; note that highs and lows can move with the request window; keep the 48 h re-read of at least 10% of label series (PI-D-018).

## Approvals needed

None. Paid data, LLM, Zep or MiroFish use, any scheduled collector (PI-D-020), copying AGPL or GPL code, adding a research package to the lab's runtime, or a merge into `main` need Elving (PI-D-005, PI-D-032).

## Next

Next step: the orchestrator's independent skeptic on Phase 05 (`phase_05/SKEPTIC_PACKET.md`), then the Phase 05 repair pass. Phase 06 (outcome label registry and censoring) is eligible only after Phase 05 is PASS.

## Exact next command

```
cd /home/claude/memelab-inbox && git checkout feature/predictive-intelligence && git log -4 --oneline && python -m memelab social guard && python -m pytest tests/test_predictive_asof_store.py tests/test_predictive_asof_features.py tests/test_predictive_asof_fixture.py -q && python -m pytest tests -q
```

Expect the two Phase 05 commits on top of `074953d`, `"violations": []`, `66 passed`, and `1 failed, 1059 passed`; then remove `data/reports/*_BRETT_*.md` by hand.
