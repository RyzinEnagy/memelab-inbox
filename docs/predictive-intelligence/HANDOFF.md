# Predictive Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Phase 06 evidence: `audits/predictive-intelligence/phase_06/` (PHASE_06_EVIDENCE.md, PHASE_06_RESULTS.json, ACCEPTANCE_CHECKLIST.md, SKEPTIC_PACKET.md, labels/, data/, evidence/, probes/, raw/, sealed/). Earlier phases stay in `phase_00/` to `phase_05/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position

- Phase 06 (outcome label registry and censoring): NEEDS_REVIEW, 2026-10-24, first pass. Waiting for the orchestrator's independent skeptic (PI-D-013) and for the frozen 48 h revision re-read, which cannot run before 2026-10-26T13:05Z (PI-D-041 item 5).
- Branch `feature/predictive-intelligence`, Phase 06 commits on top of `ed82f3a` (Phase 05 PASS): the deliverables commit and a records commit on top of it (read the hashes with `git log -2`). Not pushed. Spend 0 credits; 381 free GeckoTerminal calls.
- Code: `memelab/predictive/labels.py` (new, standard library only, flag OFF, imported by no existing module); `contract.py` changed only by change control CC-03 (registry fingerprint `4b4aabce...`, PI-D-040); one docstring line in `__init__.py`. Tests: `tests/test_predictive_labels.py` (41), fixture `tests/fixtures/predictive/labels_hand_trace.json`; `tests/test_predictive_contract.py` re-pinned. Nothing under `inbox/`, `state/` or `data/` changed.

## What Phase 06 holds

- Labels for exactly T1 24 h, T1b 6 h and T2 24 h version 1, from `token=<mint>` GeckoTerminal reads, one read per decision, the end-time candle rule, the frozen tie rule, pending before maturity, censoring with the conservative lens, and absence evidence for no-trade and halt classes (CC-03).
- Development labels (decisions before 2026-10-17, matured before then): T1 136 (34 TARGET_FIRST, 70 INVALIDATION_FIRST, 1 AMBIGUOUS_BAR, 31 NEITHER), T1b 224 (26, 67, 1, 129, 1 NO_TRADES_AFTER_ENTRY), T2 131 (28 DRAWDOWN_50, 0 TRADING_HALT, 103 NO_SEVERE_EVENT). Censored VENDOR_OR_ROUTE_GAP 39, 41, 37; UNVERIFIABLE 0.
- Holdout labels sealed in `phase_06/sealed/holdout_labels.jsonl.gz` (sha256 `e695500d...`), 99 sealed files hashed in `SEAL.json` (digest `d5059bae...`), `probes/check_seal.py` exit 0; holdout counts and censoring only: labelled 67, 69, 60, T2 7 pending.
- The phase gate `labels.training_labels(con, as_of, target)`: matured development labels only, bake-off and sealed labels refused.
- Evidence: offline rebuild from the committed archive 0 differences; 25 of 25 mutations caught; hand-checked fixture (6 cases) and real traces (4 shapes); cross-target invariants 0 violations; revisions at 0.5 to 2.6 h: 0 close or volume changes, 0 label changes.

## Tests

- Entry gate at `ed82f3a`: `1 failed, 1066 passed in 152.58s` (known failure only).
- Before commit: `1106 passed, 1 deselected` (known failure deselected); guard 0 violations; release audit "Needs action: no".
- Post-commit results: see PHASE_06_EVIDENCE.md "Post-commit results".

## Blockers and open items

- The 48 h revision re-read of the 16 sampled reads: run `python -B audits/predictive-intelligence/phase_06/probes/make_labels.py reread48` at or after 2026-10-26T13:49Z (it refuses earlier), then fold the result into the evidence. Until then no fit may claim the frozen revision check. The orchestrator or Elving may instead record a decision that moves it (for example to Phase 07's entry, before any fit).
- PI-D-020 (forward depth and quote collector) stays PROPOSED for Elving.

## Approvals needed

None for the work done. Paid data, LLM, Zep or MiroFish use, any scheduled collector, copying AGPL or GPL code, adding a research package to the lab's runtime, or a merge into `main` need Elving (PI-D-005, PI-D-032).

## Next

After the skeptic's repair pass and the 48 h re-read (or a recorded decision on its timing): Phase 07 (transparent predictive baselines), fitting only through `labels.training_labels` on the development store with the constraints in ROADMAP.md "Known constraints carried from Phase 06".

## Exact next command

```
cd /home/claude/memelab-inbox && git checkout feature/predictive-intelligence && git log -3 --oneline && python -B audits/predictive-intelligence/phase_06/probes/check_seal.py && python -m pytest tests/test_predictive_labels.py tests/test_predictive_contract.py -q && python -m pytest tests -q
```

Expect the Phase 06 commits on top of `ed82f3a`, `"problems": []`, `107 passed`, and `1 failed, 1107 passed` (known failure only); then remove `data/reports/*_BRETT_*.md` by hand.
