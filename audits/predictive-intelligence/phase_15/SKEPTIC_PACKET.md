# Phase 15 skeptic packet (task, artifacts, code, commands; no conclusions)

## Task for the independent reviewer

Phase 15 of the predictive-intelligence package: test whether behavioral simulation improves outcomes over simpler approaches (`phases/PHASE_15_mirofish_incremental_predictive_value_trial.md`, `references/MIROFISH_EVALUATION.md`). The orchestrator admitted the phase with Phase 14 at TEST_ONLY and no approved spend (PI-D-078). Try to falsify: the event count, the blindness of the coding, the coding rules, the label join, the E1 comparison, the descriptive E2 numbers and their verdicts, the controls, the POST_OPENING use of the opened holdout, the decision, the search ledger, and the statements about what could not be compared (MiroFish, the evidence-only LLM, P26). Look for look-ahead, label leakage, outcome-informed coding, quietly moved gates (compare with PI-D-079, the protocol and the checklist, all committed in `b274cbc` before any code), p-hacking across subgroups, survivorship, claims resting on docs, tests that cannot fail. Build one new wrong-but-plausible counterexample and show what catches it.

## Commit order (verify with `git log --oneline b0243b4..HEAD`)

1. `b274cbc` pre-registration: `ACCEPTANCE_CHECKLIST.md`, `behavioral/EXPERIMENT_PROTOCOL.md`, `experiments/EXPERIMENT_REGISTRY.csv`, entry evidence, PI-D-078, PI-D-079.
2. `9ab0160` frozen coding code: `memelab/predictive/scenario_eval.py`, `tests/test_predictive_scenario_eval.py`, `probes/code_scenarios.py`.
3. `7b787bf` recorded blind coding outputs (`behavioral/CODING_LOG.json`, `SCENARIO_CODING.csv`, `CONTROL_CODING.csv`, `EVENT_SET.csv`, `HOLDOUT_RULE_SCENARIOS.jsonl`).
4. `0abffd5` frozen scoring code (`probes/score_scenarios.py`, `probes/mutation_scenario_eval.py`, three tests).
5. `01e535d` first recorded scoring outputs.
6. `de41d26` change control CP15-0 (PI-D-080, self-review): per-label holdout descriptions and independence counts added; oracle probe; output tests.
7. `3135060` repeated scoring outputs, rerun diff, oracle and mutation evidence.
8. Records commit(s) on top.

## Artifacts (all under `audits/predictive-intelligence/phase_15/`)

- `behavioral/EXPERIMENT_PROTOCOL.md`, `ACCEPTANCE_CHECKLIST.md`, `experiments/EXPERIMENT_REGISTRY.csv`
- `behavioral/EVENT_SET.csv`, `SCENARIO_CODING.csv`, `CONTROL_CODING.csv`, `HOLDOUT_RULE_SCENARIOS.jsonl`, `CODING_LOG.json`
- `behavioral/INCREMENTAL_VALUE_RESULTS.json` and `.md`, `E1_OOS_ROWS.csv`, `E2_SCORED_ROWS.csv`, `POST_OPENING_LOG.json`, `GO_NO_GO.md`
- `experiments/SEARCH_LEDGER.csv`, `LEDGER_TOTALS.json`
- `evidence/entry/`, `score_run_log.json`, `rerun_cp15_0_diff.json`, `oracle_recompute.json`, `mutation_scenario_eval.json`
- `PHASE_15_EVIDENCE.md`, `PHASE_15_RESULTS.json`
- Inputs from earlier phases: `phase_14/behavioral/SEEDS_DEV.jsonl`, `RULE_SCENARIOS_DEV.jsonl`, `MIROFISH_PROBE.json`; `phase_10/experiments/OOS_PREDICTIONS.csv`, `SOCIAL_METRICS.csv`, `phase_10/evidence/crosschecks.json`; `phase_12/validation/HOLDOUT_SCORED.csv` (opened, spent); `phase_13/experiments/SEARCH_LEDGER.csv`.

## Code

- `memelab/predictive/scenario_eval.py` (scenario-eval-1): `check_blind`, `code_document`, `warnings_of`, `labels_by_target`, `verify_file`, `day_permutation`, `gate`, `warning_metrics`, `descriptive_verdict`, `holm_by_target`, `fit_warn`, `verify_warn_card`, `predict_warn`, `selection_status_dev`, `decide`, `summarize_rows`.
- Reused: `memelab/predictive/behavioral.py` (`rule_scenarios`, `check_seed`, `validate_scenario`), `baselines.evaluate`, `verdict`, `gate`, `evaluation.ledger_totals`, `bonferroni`, `conservative_status`, `labels.training_labels`, `stats.wilson`, `holm`.
- Probes: `probes/code_scenarios.py`, `score_scenarios.py`, `oracle_recompute.py`, `mutation_scenario_eval.py`, `rerun_diff.py`; `phase_14/probes/seed_convert.py`, `phase_10/probes/run_social.py` (snapshot builder).
- Tests: `tests/test_predictive_scenario_eval.py`, `tests/test_predictive_phase15_outputs.py`.

## Commands to reproduce (use your own clone and a scratch output folder)

```
git clone -q /home/claude/memelab-inbox /home/claude/pi_orchestration/skeptic_15 && cd /home/claude/pi_orchestration/skeptic_15 && git checkout -q feature/predictive-intelligence
python -m pytest tests/test_predictive_scenario_eval.py tests/test_predictive_phase15_outputs.py -q -p no:cacheprovider
python -B audits/predictive-intelligence/phase_15/probes/code_scenarios.py /tmp/p15c        # needs /home/claude/pi_research/p05/predictive_store.sqlite
python -B audits/predictive-intelligence/phase_15/probes/score_scenarios.py /tmp/p15s       # needs /home/claude/pi_research/p06/dev_store.sqlite; reads coding files of the clone
python -B audits/predictive-intelligence/phase_15/probes/oracle_recompute.py /tmp/p15_oracle.json
python -B audits/predictive-intelligence/phase_15/probes/mutation_scenario_eval.py /tmp/p15_mut.json
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
```

`code_scenarios.py` output should be byte-equal to the committed coding files (CODING_LOG.json equal except times and head); `score_scenarios.py` output byte-equal to the committed scoring files except `evidence/score_run_log.json`. The stores are outside the repository; their rebuild recipes are in `phase_05/data/FEATURE_STORE_CONTRACT.md` and the Phase 06 records.
