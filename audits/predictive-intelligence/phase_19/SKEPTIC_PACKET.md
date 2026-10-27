# Phase 19 skeptic packet

For the orchestrator's independent skeptic (PI-D-013). This packet lists the task, the artifacts, the code and the commands. It holds no conclusions; the phase's claims are in `PHASE_19_EVIDENCE.md` and are to be tested, not trusted.

## Task

Phase 19 of the package: "Track each forecast after it matures, without rewriting historical record" (outcome tracking, prospective replay, model drift). Try to falsify: that every prospective prediction and system document was fixed before any prospective label or price path was read; that outcomes follow the frozen labels-1 rules; that the outcome ledger cannot be edited or back-filled without detection; that PENDING and censored outcomes are never scored; that the verdicts follow the frozen ACCEPTANCE order and minimums; that the drift monitors use the pre-registered thresholds and the response never retrains or rewrites history; that nothing reaches the lab's outputs.

Rules to read first: `/home/claude/pi_orchestration/PHASE_BRIEF.md`, the package's `phases/PHASE_19_*.md`, `EXECUTION_RULES.md`, `references/ADVERSARIAL_SCENARIOS.md`, `DATA_TIME_CONTRACT.md`, `SCIENTIFIC_VALIDATION.md`; in the repository `docs/predictive-intelligence/DECISIONS.md` (PI-D-016, PI-D-064 to PI-D-066, PI-D-085, PI-D-091, PI-D-104), the ROADMAP's known constraints of Phases 12, 13, 16, 17 and 18.

## Artifacts (all under `audits/predictive-intelligence/phase_19/`)

- Pre-registration: `ACCEPTANCE_CHECKLIST.md`, `experiments/EXPERIMENT_REGISTRY.csv`, `monitoring/PROSPECTIVE_PLAN.md` (commit `5ffa5cf`).
- Entry gate: `evidence/entry/` (suite, seal, Phase 17 replay at the entry HEAD, the metadata-only contact scan).
- Frozen code commit `fce102e`; predictions commit `765eadb` (`monitoring/PROSPECTIVE_PREDICTIONS.csv`, `PROSPECTIVE_DECISIONS.csv`, `PREOPEN_TRAPS.json`, `REPLAY_AUDIT.json`, `published/DOCUMENTS.jsonl`, `published/RECORDS.jsonl`, `OUTCOME_LEDGER.jsonl` at 356 entries, `PREREG_MANIFEST.json`), `evidence/inputs.json`, `evidence/determinism_predict.json`, `evidence/mutation_monitoring.json`.
- The opening and the reads: `monitoring/OPENING_LOG.json`, `evidence/label_calls.json` (every GeckoTerminal call), `raw/` (gzip bodies and `MANIFEST.csv`), `data/read_map.json`, `data/read_plan.json`, `data/other_pool_reads.json`, `evidence/revision_reread.json`, `evidence/outcomes_runs.json`.
- Outputs: `monitoring/OUTCOME_LEDGER.jsonl` (appended), `OUTCOME_LEDGER.md`, `PROSPECTIVE_REPORT.md`, `PROSPECTIVE_SCORED.csv`, `PROSPECTIVE_METRICS.csv`, `CALIBRATION_BINS.csv`, `SENSITIVITY.csv`, `SHIFT_BREAKDOWN.csv`, `MISSES.csv`, `PRIMARY_RESULTS.json`, `NEGATIVE_CONTROLS.json`, `COUNTS.json`, `DRIFT_REPORT.json`, `ROLLBACK_DEMO.json`, `FEEDBACK_AUDIT.json`, `LEDGER_TOTALS.json`, `run_log_*.json`; `experiments/SEARCH_LEDGER.csv`.
- Records: `PHASE_19_EVIDENCE.md`, `PHASE_19_RESULTS.json`, `docs/predictive-intelligence/{DECISIONS,ROADMAP,HANDOFF}.md`.

## Code

- `memelab/predictive/monitoring.py` (monitoring-1): ledger chain and append rules (`seal`, `read_ledger`, `check_payload`, `append`, `load`, `verify`), `current_outcomes`, `scorable`, `prospective_records` (labels-1 on the prospective split), `outcome_payload`, `next_outcomes`, drift monitors (`psi`, `feature_drift`, `label_rate_drift`, `calibration_drift`, `page_hinkley_alarms`, `coverage_drift`, `support_state`, `source_state`, `regime_drift`, `model_age`, `minority_note`), `target_states`, `response`, `notice`, `misses`.
- `tests/test_predictive_monitoring.py`.
- Probes: `probes/run_prospective.py` (inputs, predict, outcomes, evaluate, drift, rollback, audit, report; the predict step runs the unchanged `phase_12/probes/run_holdout.py` `cmd_predict` with its window end, input class and file names set by the runner), `probes/fetch_labels.py`, `probes/mutation_monitoring.py`, `probes/contact_scan.py`.
- Reused, unchanged: `labels.py`, `store.py`, `decisions.py`, `features.py`, `baselines.py`, `evaluation.py`, `registry.py`, `phase_12/probes/run_holdout.py`, `phase_17/probes/run_integration.py`.

## Commands to reproduce (use your own clone; private stores are rebuilt by `inputs` from `/home/claude/pi_research/p05` and `p06`)

```
git log --format='%h %cI %s' 5ffa5cf^..HEAD
python -m pytest tests/test_predictive_monitoring.py -q
python -B audits/predictive-intelligence/phase_19/probes/mutation_monitoring.py /tmp/p19_mut.json
python -c "from memelab.predictive import monitoring as M; print(M.verify('audits/predictive-intelligence/phase_19/monitoring/OUTCOME_LEDGER.jsonl'))"
git show 765eadb:audits/predictive-intelligence/phase_19/monitoring/OUTCOME_LEDGER.jsonl | wc -l
# the git order of the predictions commit and the first label call
python -c "import json;c=json.load(open('audits/predictive-intelligence/phase_19/evidence/label_calls.json'));print(min(x['requested_at'] for x in c))"
git log -1 --format=%cI 765eadb
# rebuild the inputs and repeat the predictions (no network needed): edit WORK in run_prospective.py to a scratch folder first
unshare -n python -B audits/predictive-intelligence/phase_19/probes/run_prospective.py inputs
unshare -n python -B audits/predictive-intelligence/phase_19/probes/run_prospective.py predict /tmp/p19_pred
# rebuild the outcomes offline from raw/ bodies with labels-1 and compare with the ledger's current outcomes
```

Free GeckoTerminal calls are allowed for a handful of spot checks at no more than 6 a minute (`token=<mint>` in every URL). No Firecrawl.
