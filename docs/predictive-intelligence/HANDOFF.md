# Predictive Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Phase 04 evidence: `audits/predictive-intelligence/phase_04/` (PHASE_04_EVIDENCE.md, PHASE_04_RESULTS.json, ACCEPTANCE_CHECKLIST.md, SKEPTIC_PACKET.md, adoption/). Earlier phases stay in `phase_00/` to `phase_03/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position

- Phase 04 (adoption, install, adapter or build bake-off): NEEDS_REVIEW, 2026-10-24, first pass complete. The orchestrator runs the independent skeptic (PI-D-013); a repair pass folds the review in before any PASS.
- Branch `feature/predictive-intelligence`, two Phase 04 commits on top of `a146a29`: the deliverables commit and the records commit on top of it (read both with `git log -3 --oneline`; this file is part of the records commit). Not pushed. Spend 0 credits.
- Code added: `memelab/predictive/runtime.py` (standard library only, flag OFF, imported by no existing module), `tests/test_predictive_runtime.py`, `tests/fixtures/predictive/copyleft_fingerprints.json` (hashes only), `docs/predictive-intelligence/locks/` (two hash locks). No existing file under `memelab/` or `tests/` changed; nothing under `inbox/`, `state/` or `data/` changed.

## What Phase 04 found

- One common point-in-time dataset: a real development sample (BAKEOFF_ONLY labels, T1 24 h 102 events, T1b 6 h 159, decisions before 2026-10-17 with labels matured by then, PIT pools, 132 GeckoTerminal calls at no more than 6 a minute, holdout untouched) plus the synthetic challenge with a label-maturity purge. Six approaches on identical walk-forward folds: B0, numpy logistic, scikit-learn logistic, HistGradientBoosting, LightGBM, lifelines Cox, plus Platt, frozen sigmoid and Venn-Abers calibration. Behaviour, cost and correctness only: 26 and 33 out-of-sample real events cannot rank anything on skill, and nothing was selected on a score.
- The essential engine is numpy code: logistic equal to scikit-learn within 2.6e-7, Platt equal to the frozen sigmoid within 5.9e-8, Venn-Abers equal to the reference package within 1.4e-17, Page-Hinkley equal to river's positions; byte-identical predictions in a numpy-only venv, offline. Third-party packages are research-only (PI-D-031, PI-D-032).
- Library behaviours that shape later phases: HGB raises on an all-missing training column and lifelines on a constant one (training-window column rule added); tree models and Cox return silent near-zero probabilities on one-class windows (count gates first); river's detectors absorb NaN; pandera mutates numpy and the environment at import (REJECT); a plain Mesa install cannot be imported (REJECT); Venn-Abers fails calibration in the large with few positives; purgedcv's docstring contradicts its (safe) purge default; GeckoTerminal's `before_timestamp` is inclusive (PI-D-034).
- Fold audit now checks each fold's declared training cutoff as well as its test start (own adversarial pass: 31 against 29 leaked labels on the 24 h mutation).
- Install route: hash locks for CPython 3.13 on Linux, Windows and macOS arm64, `--require-hashes --only-binary=:all: --no-deps`, research venv only; three-platform download verified, offline install and clean uninstall shown, hostile sdist refused without running its `setup.py` (PI-D-032, P32).
- Runtime states and breakers: `runtime.py`, 46 tests for P30, P31, P32, P34 and the absent crawler, GPU, weights, network and library cases, 17 of 17 mutations caught (PI-D-033).
- MiroFish: ISOLATED_MOCK_ONLY. Service refuses to start without keys; mock runs not reproducible; exit 0 when the LLM is down, caught by the adapter. No probability, no paid call, no copied code.

## How to check it

From `audits/predictive-intelligence/phase_04/adoption/prototypes/`:

```
python -B build_dev_sample.py label ../data /home/claude/pi_research/p04_gt_raw && git diff --stat -- ../data   # expect no diff
python -B holdout_candle_check.py /home/claude/pi_research/p04_gt_raw     # verdict: no holdout decision can use these candles
python -B banned_scan.py /tmp/banned.json                                  # hits 0
python -B summarize.py                                                     # not_identical_or_failed: []
python -B mutation_runtime.py /tmp/mut.json                                # 17 of 17 caught
```

From the repository root: `python -m pytest tests/test_predictive_runtime.py tests/test_predictive_contract.py -q` (112 passed), `python -m memelab social guard`, `python tools/release_audit.py --history`.

## Tests

- Entry gate at `a146a29`: `python -m pytest tests -q` exit 1, `1 failed, 858 passed in 145.42s (0:02:25)`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known).
- After the deliverables commit (post-commit, on the committed tree): recorded in `audits/predictive-intelligence/phase_04/postcommit/` and PHASE_04_EVIDENCE.md "Post-commit results".
- Strays after each run: `data/reports/<stamp>_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`; remove by hand; tracked DB sha256 `068287c0...` unchanged.

## Blockers and open items

- None for the skeptic. Open: the skeptic's review and the repair pass.
- An ignored uv venv `hazardous/` sits at the repository root from an earlier session (2026-10-24T06:48Z); untracked and ignored, left in place.
- PI-D-020 (forward depth and quote collector) stays PROPOSED for Elving.

## Approvals needed

None for the skeptic or the repair pass. Paid data, LLM, Zep or MiroFish use, any scheduled collector (PI-D-020), copying AGPL or GPL code, accepting non-commercial weight terms, adding a research package to the lab's runtime, or a merge into `main` need Elving (PI-D-005, PI-D-032).

## Next

Orchestrator: run the independent skeptic on `audits/predictive-intelligence/phase_04/SKEPTIC_PACKET.md`, then return the review for the Phase 04 repair pass. Next eligible phase after a verified PASS: 05 (immutable temporal evidence and feature store), which starts from PI-D-031 to PI-D-034 and the Phase 04 constraints in ROADMAP.md.

## Exact next command

```
cd /home/claude/memelab-inbox && git checkout feature/predictive-intelligence && git log -3 --oneline && python -m memelab social guard && python -m pytest tests/test_predictive_runtime.py tests/test_predictive_contract.py -q && python -m pytest tests -q
```

Expect the two Phase 04 commits on top of `a146a29`, `"violations": []`, `112 passed`, and `1 failed, 904 passed` (858 earlier tests plus 46 new); then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand.
