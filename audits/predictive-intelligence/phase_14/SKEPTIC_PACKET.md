# Phase 14 skeptic packet (task, artifacts, code, commands; no conclusions)

## Task

Falsify Phase 14 ("implement an isolated behavioral-simulation hypothesis interface only if feasible"). Approvals: no LLM, Zep or other paid spend and no API key; a live MiroFish run is out of scope. Test whether the boundary really keeps lab data on the machine, really refuses probabilities, post-decision seeds and ungrounded or identity claims, really caps cost, really reports SIMULATION_NOT_AVAILABLE on every failure, really detects instability, and really leaves the statistical engine untouched; whether any test cannot fail; whether any AGPL code entered; whether a gate in `ACCEPTANCE_CHECKLIST.md` moved; and whether the status claims rest on code or on prose. Construct one new wrong-but-plausible counterexample.

## Read first

- Package: `phases/PHASE_14_mirofish_behavioral_simulator_adapter_and_safety.md`, `references/MIROFISH_EVALUATION.md`, `references/ADVERSARIAL_SCENARIOS.md` (P26 to P31, P41, P45, P48), `references/FORECAST_OUTPUT_SCHEMA.md`.
- Pre-registration (committed before any code): `audits/predictive-intelligence/phase_14/ACCEPTANCE_CHECKLIST.md`, `experiments/EXPERIMENT_REGISTRY.csv`, `docs/predictive-intelligence/DECISIONS.md` PI-D-072; changes before the frozen code: PI-D-073, PI-D-074.
- Earlier MiroFish evidence: `audits/predictive-intelligence/phase_03/research/MIROFISH.md`, `phase_04/adoption/MIROFISH_FEASIBILITY.md`, `phase_04/adoption/prototypes/mirofish_adapter.py`.

## Code

- `memelab/predictive/behavioral.py` (behavioral-1): seeds and `check_seed`, `build_request`, `code_response`, `scenario_doc`, `validate_scenario`, `forecast_entries`, `stability`, `loopback_endpoint`, `cost_plan`, `preflight`, `ServiceAdapter`, `SubprocessAdapter`, `LLMMeter`, `RULES` and `rule_scenarios`.
- `memelab/predictive/runtime.py` (`simulation_state`, `CallGuard`, `guarded`; unchanged), `contract.py`, `abstention.py` (`PROB_LIKE`, `validate_publication`; unchanged).
- `tools/release_audit.py` (three EXPLAINED entries added, PI-D-074).
- Fixtures: `tests/fixtures/predictive/behavioral_mock.py` (mock service modes, mock LLM, subprocess entry).
- Tests: `tests/test_predictive_behavioral.py`, `tests/test_predictive_phase14_outputs.py`.
- Probes: `audits/predictive-intelligence/phase_14/probes/build_seeds.py`, `seed_convert.py`, `run_behavioral.py`, `mirofish_runner.py`, `mutation_behavioral.py`, `oracle_schema.py`, `release_exempt_compare.py`.

## Artifacts

- `behavioral/MIROFISH_INTERFACE.md`, `behavioral/SCENARIO_SCHEMA.json`
- `behavioral/SEEDS_DEV.jsonl`, `SEEDS_DEV_LOG.json`, `RULE_SCENARIOS_DEV.jsonl`, `RULE_COUNTS.json`
- `behavioral/MOCK_GRID_RUNS.json`, `P30_MATRIX.csv`, `COST_CAP.json`, `MIROFISH_PROBE.json`, `CORE_UNAFFECTED.json`
- `evidence/run_log.json`, `mutation_behavioral.json`, `oracle_jsonschema.json`, `release_exempt_compare.json`, `entry/`
- `experiments/SEARCH_LEDGER.csv`, `PHASE_14_EVIDENCE.md`, `PHASE_14_RESULTS.json`

## Commands (own clone; temp MEMELAB_DB; the stores are under /home/claude/pi_research)

```
git log --oneline -6                                  # 9ed8377 pre-registration, c59c494 frozen code, 872578d recorded run, records on top
python -m pytest tests/test_predictive_behavioral.py tests/test_predictive_phase14_outputs.py -q
python -m pytest tests -q                             # expect only tests/test_catalyst.py::test_dedup_corroboration_resurface_denial
python -B audits/predictive-intelligence/phase_14/probes/build_seeds.py /tmp/p14       # about 10 s, needs the Phase 05 store and origin/main history
python -B audits/predictive-intelligence/phase_14/probes/run_behavioral.py /tmp/p14 --skip-mirofish   # about 1 min
python -B audits/predictive-intelligence/phase_14/probes/run_behavioral.py /tmp/p14b   # with MiroFish: needs root (unshare -n), the venv
                                                      # /home/claude/pi_research/venvs/p04_mirofish, the clone at 7657031a and the
                                                      # tokenizer cache given by --tiktoken-cache; about 2 min
python -B audits/predictive-intelligence/phase_14/probes/mutation_behavioral.py /tmp/p14_mut.json      # about 6 min
python -B audits/predictive-intelligence/phase_14/probes/oracle_schema.py /tmp/p14_oracle.json
python -B audits/predictive-intelligence/phase_14/probes/release_exempt_compare.py 2fd0aae
python -m memelab social guard
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
```

The rule documents of a rerun differ from the committed ones only in `created_at_utc` and the dependent `doc_sha256`; `tests/test_predictive_phase14_outputs.py` re-derives them from the committed seeds with the recorded creation time.
