# Predictive Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Phase 03 evidence: `audits/predictive-intelligence/phase_03/` (PHASE_03_EVIDENCE.md, PHASE_03_RESULTS.json, ACCEPTANCE_CHECKLIST.md, SKEPTIC_PACKET.md, skeptic/, research/). Earlier phases stay in `phase_00/` to `phase_02/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position

- Phase 03 (pinned source audit, rubric and ranked top ten): PASS, 2026-10-24, after the repair pass that folds in the orchestrator's skeptic (3 MATERIAL, 9 MINOR) and blind rescore. Post-commit suite, content guard and release audit with history are clean (`phase_03/postcommit/`, `phase_03/PHASE_03_RESULTS.json`).
- Branch `feature/predictive-intelligence`, two Phase 03 commits on top of `77e78ce`: the repair commit `e1b2c5e` and the records commit on top of it (read its hash with `git log -1`; this file is part of it). The first-pass commit `c9e894d` was never pushed and was rewritten because its smoke files failed the lab's content guard (PI-D-030). No production code: nothing under `memelab/` or `tests/` changed; nothing under `inbox/`, `state/` or `data/` changed. Not pushed. Spend 0 credits.

## What Phase 03 found

- 30 pinned source reviews by five reviewers, verified by the lead: 89 targeted checks (78 first pass, 11 in the repair pass) and 5 generic checks on all 30, 0 failed, plus re-executions. Three review claims were found wrong in the repair pass and corrected: interpret's "no standard deviations" (a wrong attribute name, IN-5), river's "not LEAKAGE_FAIL" (the end-of-stream flush is learned, RV-4) and purgedcv's leak-free group k-fold, k-fold and CPCV (empty folds and training on later rows, PC-3).
- Locked weights applied through 50 frozen items (PI-D-026) under the application rules of PI-D-029: verified-finding veto on every item that credits a defective output, wrapper and pass-through rules, fold audit for splitter evidence, an evidence rule the checker now enforces, one data-rights rule.
- 29 of 30 eligible; mlfinpy REJECT. Top ten: scikit-learn 51, interpret 50, river 49, statsmodels 49, purged-cross-validation 48, LightGBM 45, pandera 44, lifelines 44, MAPIE 44, hazardous 43. Seven are stable under every reading, the reviewers' totals and the blind scores; places 8 to 10 rotate among pandera, MAPIE, hazardous, sktime and crepes (`research/RANKED_TOP10.md`).
- Category winners: scikit-learn (tabular), sktime (time series, design only), river (online), MAPIE (calibration; never its Venn-Abers port), lifelines (event time; on-chain anomaly NONE verified), Mesa (behavioral), purged-cross-validation (evaluation, `WalkForwardSplit` only). Adoption roles: PI-D-028, ADOPTED as amended; bundle in `research/CATEGORY_WINNERS.md`.
- Blind rescore (`research/INDEPENDENT_RESCORE.md`): lead minus blind from -7 to +11; hazardous (+16 first pass) resolved criterion by criterion to +11, the rest being item-definition differences cited on both sides.
- MiroFish 8 of 100: scenario generation only, AGPL, needs paid LLM and Zep (BLOCKED), non-reproducible, silent success when the LLM is down; no accuracy assigned (`research/MIROFISH.md`).
- Challenge limitation: label overlap cannot inflate a metric on this generator; purged versus unpurged differences up to about 0.002 Brier are noise (`research/SMOKES/_challenge/NOTE.md`).

## How to check it

From `audits/predictive-intelligence/phase_03/research/`:

```
python3 -B verify/build_scorecard.py && git diff --stat -- SCORECARD.csv SCORE_ITEMS.csv   # rebuild, expect no diff
python3 -B verify/check_scorecard.py            # problems 0
python3 -B verify/check_scorecard_negative.py   # 31 of 31 mutations refused
python3 -B verify/verify_reviews.py             # checks 89, failed 0 (needs /home/claude/pi_research/src clones)
python3 -B verify/verify_generic.py             # award mismatches 0
python3 -B ../skeptic/p03/skeptic_mutations.py .   # 6 of 6 refused
```

From the repository root: `python -m memelab social guard` (exit 0, no violations) and `python tools/release_audit.py --history` (exit 0).

## Tests

- Entry gate at `77e78ce`: `python -m pytest tests -q` exit 1, `1 failed, 858 passed in 143.26s (0:02:23)`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known).
- First pass, before its commit: `1 failed, 858 passed in 135.45s`. At the first-pass commit `c9e894d` (orchestrator): `4 failed, 855 passed`, three content-guard tests on the MiroFish smoke files (fixed).
- Repair pass, after the repair commit `e1b2c5e`: exit 1, `1 failed, 858 passed in 144.44s (0:02:24)`, only the known failure; `python -m memelab social guard` exit 0 with no violations; `python tools/release_audit.py --history` exit 0, "Needs action: no".
- Strays after each run: `data/reports/<stamp>_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`; remove by hand; tracked DB sha256 `068287c0...` unchanged.

## Blockers and open items

- None. The orchestrator verifies the two commits and pushes.
- MiroFish maintainer FAQ (issue 726) still unread; nothing rests on it.
- PI-D-020 (forward depth and quote collector) stays PROPOSED for Elving.

## Approvals needed

None for Phase 04 to start. Paid data, LLM, Zep or MiroFish use, any scheduled collector (PI-D-020), copying AGPL or GPL code, accepting TabPFN-3.5 or other non-commercial weight terms, or a merge into `main` need Elving (PI-D-005).

## Next

Next eligible phase: 04 (adoption, install, adapter or build bake-off), after the orchestrator verifies Phase 03 and pushes. Phase 04 starts from PI-D-028 and must honour the Phase 03 constraints in ROADMAP.md (banned defaults, REJECT routes, fold audits for splitters, the content guard for committed artifacts).

## Exact next command

```
cd /home/claude/memelab-inbox && git checkout feature/predictive-intelligence && git log -3 --oneline && python -m memelab social guard && cd audits/predictive-intelligence/phase_03/research && python3 -B verify/check_scorecard.py && python3 -B verify/check_scorecard_negative.py && cd /home/claude/memelab-inbox && python -m pytest tests -q
```

Expect the two Phase 03 commits on top of `77e78ce`, `"violations": []`, `problems 0`, `31 of 31 mutations refused` and `1 failed, 858 passed`; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand.
