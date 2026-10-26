# Phase 13 skeptic packet (artifacts, code and commands; no conclusions)

## Task for the reviewer

Try to falsify Phase 13 of the predictive-intelligence package: "make forecast probabilities interpretable, stable and willing to abstain" (package `phases/PHASE_13_calibration_uncertainty_and_abstention.md`; scenarios P10, P11, P12, P23, P24, P27, P38, P39 plus an injected NaN and a model overconfident on a rare class). Check the claims against code, git and executions, not against the documents. In particular look for: a calibrator or interval fitted on rows that were not available at the cutoff, on in-sample scores or on the spent retrospective holdout; any path by which a number reaches `probability` without the frozen gates; a condition of the pre-registration that the code does not enforce or enforces differently; tests that cannot fail; a post-opening computation that could make a statement less conservative; outputs that do not reproduce; gates moved after results (compare `ACCEPTANCE_CHECKLIST.md` at `0fdf698` with the code and the records). Build one new wrong-but-plausible counterexample and show which check catches it, or that nothing does.

## Records and pre-registration

- `docs/predictive-intelligence/DECISIONS.md` PI-D-067 (rules), PI-D-068 (self-review pass 2), PI-D-069 (result); earlier rules PI-D-016, PI-D-021, PI-D-022, PI-D-053, PI-D-064 to PI-D-066.
- `audits/predictive-intelligence/phase_13/ACCEPTANCE_CHECKLIST.md` and `experiments/EXPERIMENT_REGISTRY.csv` (sha256 `d73e19cf...`), both in commit `0fdf698`.
- Commits: `0fdf698` pre-registration, `5a3c582` frozen code, `9cd5288` recorded run outputs, `2e1488a` self-review pass 2 code, then outputs and records on top (see `git log --oneline 6f4f8ea..HEAD`).

## Code

- `memelab/predictive/calibration.py` (calibration-1): calibration rows, gates, method rule, Platt and Venn-Abers through `stats`, support bins, intervals, degeneracy, score report, base-rate uncertainty, heterogeneity and prevalence-shift permutation tests, drift alarms, calibration cards and the `calibration_reference`.
- `memelab/predictive/abstention.py` (abstention-1): the 28 conditions and their contract reasons, `evaluate`, `build`, `forecast_result`, `validate_publication`, `append`, `describe`.
- Unchanged and reused: `memelab/predictive/contract.py`, `stats.py`, `baselines.py`, `labels.py`, `evaluation.py` (`check_card_time` cross-check, `conservative_status`, `ledger_totals`, only in the runner).
- Tests: `tests/test_predictive_calibration.py`, `tests/test_predictive_abstention.py` (includes the in-house schema checker), `tests/test_predictive_phase13_outputs.py`.
- Probes: `audits/predictive-intelligence/phase_13/probes/run_calibration.py` (the run), `oracle_calibration.py` (scikit-learn, statsmodels, ip200/venn-abers), `mutation_calibration.py`.

## Artifacts

- `models/CALIBRATION_CARD.md`, `models/FORECAST_RESULT_SCHEMA.json`.
- `artifacts/T1_24h/CALIBRATION_CARD.json`, `artifacts/T1b_6h/CALIBRATION_CARD.json`, `artifacts/T2_24h/CALIBRATION_CARD.json`.
- `calibration/`: `RELIABILITY_COVERAGE.csv`, `ABSTENTION_MATRIX.csv` and `.md`, `CALIBRATION_SETS.csv`, `SCORE_REPORT_DEV.json`, `BELOW_GATE_DESCRIPTIVE.json`, `BASE_RATE_UNCERTAINTY.csv`, `EXCHANGEABILITY.json`, `DRIFT_DEV.json`, `FOLD_CALIBRATION_CARDS.json`, `FORECAST_RESULTS_DEV.jsonl`, `FORECAST_RESULTS_HOLDOUT_POST_OPENING.jsonl`, `FORECAST_RESULTS_TODAY.jsonl`, `ABSTENTION_RECORDS_DEV.jsonl`, `ABSTENTION_RECORDS_HOLDOUT_POST_OPENING.jsonl`, `TODAY_STATUS.json`, `HOLDOUT_POST_OPENING.json`, `POST_OPENING_LOG.json`, `REPLAY_CHECKS.json`.
- `experiments/SEARCH_LEDGER.csv`, `experiments/LEDGER_TOTALS.json`.
- `evidence/`: `run_log.json`, `oracle_sklearn_statsmodels.json`, `oracle_venn_abers.json`, `mutation_calibration.json`, `mutation_calibration_sr2.json`, `sr2_old_code_check.json`, `frozen_code_rerun_sr2.json`, `schema_jsonschema_check.json`, `entry/`.
- Inputs it reads: Phase 07 fold and holdout-start cards (`phase_07/artifacts/`), `phase_07/experiments/OOS_PREDICTIONS.csv`, Phase 12 `validation/HOLDOUT_SCORED.csv`, `HOLDOUT_DECISIONS.csv`, `CALIBRATION_BINS.csv`, `FULL_EXPERIMENT_LEDGER_CORRECTED.csv`; private stores `/home/claude/pi_research/p06/dev_store.sqlite` (sha256 `d2a5a7c6...`) and `/home/claude/pi_research/p05/predictive_store.sqlite` (`2525f0c4...`).

## Commands (work in your own clone; use a temporary MEMELAB_DB)

```
git clone -q /home/claude/memelab-inbox /home/claude/pi_orchestration/skeptic_13 && cd /home/claude/pi_orchestration/skeptic_13 && git checkout -q feature/predictive-intelligence
python -m pytest tests/test_predictive_calibration.py tests/test_predictive_abstention.py tests/test_predictive_phase13_outputs.py -q
python -B audits/predictive-intelligence/phase_13/probes/run_calibration.py /tmp/p13_out          # about 10 s; compare with audits/predictive-intelligence/phase_13 (calibration/, artifacts/, experiments/)
python -B audits/predictive-intelligence/phase_13/probes/mutation_calibration.py /tmp/p13_mut.json  # about 4 min
/home/claude/pi_research/venvs/p04_bundle/bin/python -B audits/predictive-intelligence/phase_13/probes/oracle_calibration.py audits/predictive-intelligence/phase_13 /tmp/p13_or1.json
/home/claude/pi_research/venvs/ip200__venn-abers/bin/python -B audits/predictive-intelligence/phase_13/probes/oracle_calibration.py audits/predictive-intelligence/phase_13 /tmp/p13_or2.json
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
```

The runner reads the retrospective holdout outcomes only from committed Phase 12 files (any such computation is POST_OPENING, PI-D-066); it never opens `phase_06/sealed/`. A run of yours on those files is also POST_OPENING; please say so in the review.
