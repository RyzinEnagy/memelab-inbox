# Phase 11 skeptic packet

For the orchestrator's independent skeptic (PI-D-013). Task, artifacts, code and commands only; the phase agent's conclusions are in `PHASE_11_EVIDENCE.md` and are deliberately not summarised here.

## Task

Phase 11 of the Memecoin Predictive Intelligence Engine package: "Forecast low-history opportunities via explicit analog cohorts and regime handling" (package `phases/PHASE_11_analog_cohort_and_regime_predictions.md`). Try to falsify it. In particular:

1. Can any analog pool, at any cutoff or decision, contain information not available at that time: a row decided at or after the cohort time, a label maturing after it, a token first seen after it, an input available after its own decision, a later export, a current token or vendor list (P09, P36, P43)?
2. Can the same token or the same deployer reach a cohort as an analog, or can similarity be used as identity (P01, P14)? Are duplicate windows of one token or deployer counted more than once?
3. Is the regime label at T computable at T? Does anything in it (window, past median, warmup, status mapping, volume availability) read after T? Is it a market regime or the lab's export cadence?
4. Are the effective sample sizes honest? Does `G >= 20` and `analog days >= 5` support the numbers given how decisions are batched by export day (compare the day Kish ESS)? Is any number shown below a minimum?
5. Do the out-of-distribution, ANALOGS_TOO_FEW, REGIME_UNKNOWN and REGIME_UNSEEN states trigger when they should, and only then?
6. Are the verdicts, coverage, regime breakdown (P21) and cross-phase comparisons produced by the frozen Phase 07 code and minimums, with no claim below them? Do B0 and B2 equal Phase 07's?
7. Are the divergence flags (authority, fee, token program, exit-capacity share, friction) correct and never removed by segmentation (phase prompt step 5)? Is any execution or profit claim made (P44)?
8. Was everything registered before it ran (checklist, registry, PI-D-061 commit before the runs; frozen code before the recorded run; debug runs in the ledger)?
9. Produce one new wrong-but-plausible counterexample of your own and a check (a test or a script) that catches it, or show that nothing catches it.

Work in your own clone; do not edit the main checkout. Never open `audits/predictive-intelligence/phase_06/sealed/` (Phase 12 only). No paid calls; no vendor calls are needed.

## Artifacts

- Pre-registration: `audits/predictive-intelligence/phase_11/ACCEPTANCE_CHECKLIST.md`, `experiments/EXPERIMENT_REGISTRY.csv`, `docs/predictive-intelligence/DECISIONS.md` PI-D-061 (commit `46afc85`).
- Spec: `audits/predictive-intelligence/phase_11/models/ANALOG_MATCHING_SPEC.md`.
- Outputs: `experiments/ANALOG_METRICS.csv`, `OOS_PREDICTIONS.csv`, `COHORT_COVERAGE.csv`, `REGIME_SERIES.csv`, `REGIME_BREAKDOWN.csv`, `CROSS_PHASE_COMPARISON.csv`, `DIVERGENCE_FLAGS.csv`, `LOCO_SENSITIVITY.csv`, `NC1AC_SEEDS.csv`, `SEARCH_LEDGER.csv`.
- Cards: `artifacts/<target>/AC1_STRATA.json`, `AC2_KNN.json`, `AC3_KNN_REGIME.json` (holdout start), `artifacts/folds/<target>.json` (one pool per fold plus card headers; a card is the header with its fold's pool put back as `body.pool`).
- Evidence: `evidence/run_log.json`, `traps.json`, `folds.json`, `serialization_smoke.json`, `determinism.json`, `sklearn_crosscheck.json`, `trace/trace.json`, `trace/verify_trace.json`, `postrun_checks.json`, `mutation_analog.json`, `regime_counts.json`, `entry/`.

## Code

- `memelab/predictive/analog.py` (the module), `tests/test_predictive_analog.py`.
- Reused, unchanged: `memelab/predictive/baselines.py` (join, gate, evaluate, verdict), `labels.py` (`training_labels`, `cohort_of`), `features.py` (`training_view`, `validate_rows`), `onchain.py` (`onchain_as_of`, `size_cap_usd`), `stats.py`, `contract.py`, `memelab/social/replay_core.py`.
- Probes: `audits/predictive-intelligence/phase_11/probes/run_analog.py`, `cohort_query.py`, `verify_trace_analog.py`, `sklearn_crosscheck_analog.py`, `postrun_checks.py`, `mutation_analog.py`; and `audits/predictive-intelligence/phase_07/probes/run_baselines.py` (loading helpers the runner imports).

## Inputs (private, outside the repository)

- `/home/claude/pi_research/p06/dev_store.sqlite` (sha256 `d2a5a7c6...`), `/home/claude/pi_research/p05/predictive_store.sqlite` (`2525f0c4...`); rebuild instructions in HANDOFF.md if absent.
- Git object `e245d91` (`origin/main`, survivorship count only).

## Commands

```
cd <your clone>; git checkout feature/predictive-intelligence
python -m pytest tests/test_predictive_analog.py -q
python -B audits/predictive-intelligence/phase_11/probes/run_analog.py /tmp/p11_skeptic_run --npz /tmp/p11_skeptic.npz
diff -r /tmp/p11_skeptic_run/experiments audits/predictive-intelligence/phase_11/experiments   # EXPERIMENT_REGISTRY.csv exists only in the repo
python -B audits/predictive-intelligence/phase_11/probes/verify_trace_analog.py audits/predictive-intelligence/phase_11
python -B audits/predictive-intelligence/phase_11/probes/postrun_checks.py audits/predictive-intelligence/phase_11 /tmp/p11_postrun.json
python -B audits/predictive-intelligence/phase_11/probes/cohort_query.py --target T1b_6h --decision-key <key> --as-of 2026-10-14T00:00:00Z
/home/claude/pi_research/venvs/p04_bundle/bin/python -B audits/predictive-intelligence/phase_11/probes/sklearn_crosscheck_analog.py /tmp/p11_skeptic.npz /tmp/p11_oracle.json
python -B audits/predictive-intelligence/phase_11/probes/mutation_analog.py /tmp/p11_mut.json
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
```
