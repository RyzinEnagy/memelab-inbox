# Phase 16 skeptic packet

Task for the independent reviewer: falsify Phase 16 (select trustworthy champions, preserve baselines, version artifacts, build the model registry). Read the phase prompt `phases/PHASE_16_champion_selection_ensemble_and_model_registry.md`, `EXECUTION_RULES.md`, `references/ADVERSARIAL_SCENARIOS.md` (P22, P24, P27, P38, P39, P46), `references/SCIENTIFIC_VALIDATION.md`, `references/NO_GO_DECISION_TREE.md`, then this phase's pre-registration and outputs. Claims in the records are to be tested, not trusted.

## Artifacts

- Pre-registration (committed first, `8af3cd4`): `ACCEPTANCE_CHECKLIST.md`, `experiments/EXPERIMENT_REGISTRY.csv`, `docs/predictive-intelligence/DECISIONS.md` PI-D-084 and PI-D-085.
- Change controls after the first recorded run: PI-D-086 (CP16-0, self-review) and PI-D-088 (CP16-1, found by the post-commit suite).
- Registry: `registry/entries/*.json` (69), `registry/REGISTRY_LOG.jsonl`, `registry/REGISTRY_INDEX.json`, `registry/TODAY_STATUS.json`, `registry/TODAY_RESULTS.jsonl`, `registry/TODAY_RECORDS.jsonl`.
- Ensemble: `ensemble/ENSEMBLE_ABLATION.json` and `.csv`, `ensemble/STABILITY.json`, `ensemble/LATENCY.json`, `ensemble/POST_OPENING_LOG.json`.
- Evidence: `evidence/INFERENCE_CHECK.json`, `evidence/COMPATIBILITY_P46.json`, `evidence/ROLLBACK_TEST.json`, `evidence/determinism_repeat.json` (first run), `evidence/rerun_cp16_0_diff.json` (first run against the CP16-0 repeat), `evidence/rerun_cp16_1_diff.json` (CP16-1 repeat), `evidence/mutation_registry.json` and `evidence/mutation_registry_cp16_0.json`, `evidence/run_log.json`, `evidence/entry/`.
- Ledger: `experiments/SEARCH_LEDGER.csv`, `experiments/LEDGER_TOTALS.json`.
- Policy and schema: `models/CHAMPION_POLICY.md`, `models/REGISTRY_SCHEMA.md`, `models/ENSEMBLE_ABLATION.md`.
- Inputs it relies on: `phase_12/validation/CANDIDATES.json`, `HOLDOUT_METRICS.csv`, `PRIMARY_RESULTS.json`, `POST_OPENING_CORRECTIONS.csv`, `HOLDOUT_PREDICTIONS.csv`, `HOLDOUT_SCORED.csv`, `PREOPEN_TRAPS.json`, `REPLAY_AUDIT.json`; `phase_13/artifacts/*/CALIBRATION_CARD.json`; `phase_07` and `phase_10` `OOS_PREDICTIONS.csv` and fold cards; `phase_15/experiments/SEARCH_LEDGER.csv` and `SEARCH_LEDGER_RP2_ADDITION.csv`.

## Code

- `memelab/predictive/registry.py` (registry-1).
- `tests/test_predictive_registry.py`, `tests/test_predictive_phase16_outputs.py`, `tests/fixtures/predictive/registry_probe_examples.json`.
- `audits/predictive-intelligence/phase_16/probes/build_registry.py` (recorded run; it loads `phase_12/probes/run_holdout.py` for the holdout inputs), `probes/mutation_registry.py`.
- Consumers that stay unchanged: `memelab/predictive/abstention.py`, `calibration.py`, `evaluation.py`, `baselines.py`.

## Commands to reproduce

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/predictive-intelligence
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests/test_predictive_registry.py tests/test_predictive_phase16_outputs.py -q
python -B audits/predictive-intelligence/phase_16/probes/build_registry.py /tmp/p16_out      # needs the p05 and p06 stores
python -B audits/predictive-intelligence/phase_16/probes/mutation_registry.py /tmp/p16_mut.json
python -m pytest tests -q
```

The recorded-run probe needs `/home/claude/pi_research/p05/predictive_store.sqlite` and `/home/claude/pi_research/p06/dev_store.sqlite` (rebuild recipes in the Phase 05 and 06 records). Use a full clone (the commit-order output test fails on a shallow one by design).

## Things worth attacking

- Whether any entry, pin, index line or document can be read as a champion with skill; whether the references (B0, B2) can reach a document as a probability.
- Whether a level can be raised without the evidence (forged facts, forged calibration, forged pins in the log, a fixture entry in the real registry).
- Whether the champion restatement reads the opened holdout, and whether anything computed on holdout outcomes became a choice.
- Whether the ensemble rows are really out of fold, whether the evidence-source map misses a shared source, whether the stacking gate could be passed with in-sample rows.
- Whether the identical-inference check would notice a changed card or a changed input path.
- P46 (feature or schema change without retrain), P39 (drift and staleness thresholds, history preserved), P38 (malformed outputs), P27 (behavioral sources), P22 (selection over the search), P24 (small calibration).
- Whether the frozen promotion table can be satisfied at all after the holdout opening, and whether the records say so.
- Tests that cannot fail: mutate `registry.py` and check that a test fails.
