# Phase 12 skeptic packet (for the orchestrator's independent reviewer; no conclusions)

## Task

Falsify Phase 12 (walk-forward discipline, search discipline and the single evaluation of the sealed retrospective holdout, decisions 2026-10-17 to 2026-10-24). In particular: was anything chosen, refitted, tuned or re-run after the holdout labels were read; was the seal opened more than once or before the plan, code and predictions were committed; are the exclusions (two contacted decisions, PI-D-021 item 4) and the T2 note (PI-D-045 item 6) applied; do the reported numbers follow from the committed predictions and the sealed labels; do the selection corrections and the ledger totals hold; can a future-trained model reach a historical decision; does any claim exceed the frozen minimums (50 events, 10 per class, 5 days).

Rules for the reviewer: work in your own clone (never in `/home/claude/memelab-inbox`). Running the committed program again on the same inputs is a REPRODUCTION (`run_holdout.py open OUT --reproduction`, which needs the committed `validation/OPENING_LOG.json` and writes its own log in OUT); any other analysis of the holdout labels is EXPLORATORY and should be named as such in the review. Do not open the prospective window (decisions from 2026-10-24): it belongs to Phase 19.

## Order of commits to check

- `79d30f5` pre-registration: `ACCEPTANCE_CHECKLIST.md`, `experiments/EXPERIMENT_REGISTRY.csv`, `validation/WALK_FORWARD_PROTOCOL.md`, PI-D-064.
- `3ea7030` frozen code: `memelab/predictive/evaluation.py`, `tests/test_predictive_evaluation.py`, `probes/run_holdout.py`, `probes/mutation_evaluation.py`, `probes/sklearn_crosscheck_holdout.py`.
- `d58de61` pre-opening outputs: `validation/CANDIDATES.json`, `LEDGER_TOTALS.json`, `HOLDOUT_PREDICTIONS.csv`, `HOLDOUT_DECISIONS.csv`, `PREOPEN_TRAPS.json`, `REPLAY_AUDIT.json`, `PREOPEN_MANIFEST.json`, `evidence/mutation_evaluation.json`, `evidence/determinism_predict.json`.
- Later commits: the opening's outputs (`validation/OPENING_LOG.json` and the metric files), the results document, evidence and records.

## Artifacts

- Plan: `audits/predictive-intelligence/phase_12/validation/WALK_FORWARD_PROTOCOL.md`, `ACCEPTANCE_CHECKLIST.md`, `experiments/EXPERIMENT_REGISTRY.csv`, DECISIONS PI-D-064.
- Opening: `validation/OPENING_LOG.json`; seal `audits/predictive-intelligence/phase_06/sealed/SEAL.json` and `phase_06/probes/check_seal.py`; pins in DECISIONS PI-D-041 and PI-D-045 and `evaluation.SEAL_PINS`.
- Results: `validation/PRIMARY_RESULTS.json`, `HOLDOUT_METRICS.csv`, `CALIBRATION_BINS.csv`, `SENSITIVITY.csv`, `SHIFT_BREAKDOWN.csv`, `HOLDOUT_NEGATIVE_CONTROLS.json`, `HOLDOUT_COUNTS.json`, `HOLDOUT_SCORED.csv`, `FULL_EXPERIMENT_LEDGER.csv`, `FULL_LEDGER_TOTALS.json`, `FINAL_HOLDOUT_RESULTS.md`; `evidence/`.
- Frozen cards evaluated: `audits/predictive-intelligence/phase_07/artifacts/` to `phase_11/artifacts/` (69 files, hashes in `CANDIDATES.json`).

## Code

- `memelab/predictive/evaluation.py` (new): `check_seal_report`, `open_holdout`, `holdout_rows`, `check_identity`, `check_card_time`, `score`, `champion`, `holdout_verdict`, `holm`, `bonferroni`, `max_t`, `ledger_totals`, `shadow_criteria`.
- Reused unchanged: `baselines.evaluate`, `verdict`, `evaluation_gate`, `nc1_verdict`, `fit_b2`, `join_by_symbol`; `labels.split_of`, `cohort_of`, `groups_of`; `features.training_view`; the families' `loads`, `attach` and `predict` (`technical`, `onchain`, `socialcat`, `analog`); the Phase 07, 10 and 11 runners' loaders.
- Runner: `audits/predictive-intelligence/phase_12/probes/run_holdout.py` (`plan`, `predict`, `open`, `--reproduction`, `--synthetic-dry-run`).

## Commands to reproduce

```
cd <your clone>; git checkout feature/predictive-intelligence
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests/test_predictive_evaluation.py -q
python -B audits/predictive-intelligence/phase_12/probes/mutation_evaluation.py /tmp/mut.json
python -B audits/predictive-intelligence/phase_12/probes/run_holdout.py plan /tmp/p12plan
python -B audits/predictive-intelligence/phase_12/probes/run_holdout.py predict /tmp/p12plan     # compare with validation/ byte for byte
python -B audits/predictive-intelligence/phase_12/probes/run_holdout.py open /tmp/p12repro --reproduction   # about 12 min; compare metric files
/home/claude/pi_research/venvs/p04_bundle/bin/python -B audits/predictive-intelligence/phase_12/probes/sklearn_crosscheck_holdout.py audits/predictive-intelligence/phase_12/validation /tmp/oracle.json
```

`predict` and `open` need the private stores `/home/claude/pi_research/p05/predictive_store.sqlite` and `/home/claude/pi_research/p06/dev_store.sqlite` (sha256 in `validation/run_log_predict.json`) and the git objects of the holdout decisions' export commits.
