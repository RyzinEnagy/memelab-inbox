# Phase 20 skeptic packet

For the orchestrator's independent skeptic (PI-D-013). This packet lists the task, the artifacts, the code and the commands. It holds no conclusions; the phase's claims are in `PHASE_20_EVIDENCE.md` and `qa/` and are to be tested, not trusted.

## Task

Phase 20 of the package: the independent adversarial integration and scientific audit of the completed pathway. Try to falsify: that every one of P01 to P48 has an own executable check whose assertions prove the required behaviour (positive passes and expected error states alike); that every recorded counterexample is still refused at the audited code and at the repair; that the cross-component scenarios X01 to X06 are new and reach at least three components each; that no CRITICAL defect exists (a leak into a published number or training row, a number where the contract abstains, a quote or size from a forecast, copyleft code, a trade or key path, an unbounded spend path, a changed flag-off lab output, a write under tracked `inbox/`, `state/` or `data/`); that the flag-off lab output is byte-identical to `b0fad12`; that the independent recalculation really is independent; that no record claims skill, edge, calibration or profit beyond its evidence; that the CP20-1 repairs close F20-02, F20-03, F20-06 and F20-08 without changing any recorded real output; that the severity of every finding is right (in particular F20-04, F20-01, F20-05 and F20-07 left open).

Rules to read first: `/home/claude/pi_orchestration/PHASE_BRIEF.md`, the package's `phases/PHASE_20_*.md`, `references/ADVERSARIAL_SCENARIOS.md`, `references/COMPLETION_CHECKLIST.md`, `NO_GO_DECISION_TREE.md`, `EXECUTION_RULES.md`, `SCIENTIFIC_VALIDATION.md`, `DATA_TIME_CONTRACT.md`; in the repository `docs/predictive-intelligence/DECISIONS.md` (PI-D-013, PI-D-106, PI-D-109 to PI-D-111) and the ROADMAP's known constraints of Phases 12 to 19.

## Artifacts (under `audits/predictive-intelligence/phase_20/` unless a path says otherwise)

- Pre-registration: `ACCEPTANCE_CHECKLIST.md` (G1 to G17, severity classes, scenario method, X01 to X05; additions before the frozen code: X06, probe assertions, xfail rule), `experiments/EXPERIMENT_REGISTRY.csv` (commit `9e1f29d`).
- Frozen audit code `0d66379`: `probes/` and `tests/test_predictive_phase20_cross.py`.
- Recorded runs at `0d66379` (commit `67acbc3`): `qa/SCENARIO_MATRIX.csv`, `qa/raw/P01.json` to `P48.json`, `qa/COUNTEREXAMPLES.csv`, `evidence/` (matrix_run, mapped_tests, cx_rerun, cx_raw, cross_tests, independent_recalc, oos_sensitivity, threat_scan, flag_off_identity, e2e, fresh_env, reproductions, phase14_mock_grid_check, run_times).
- Findings and audits: `qa/INDEPENDENT_FINDINGS.md`, `qa/SCIENTIFIC_CLAIMS_AUDIT.md`, `qa/FULL_E2E_LOG.md`, `qa/COMPLETION_CHECKLIST_AUDIT.md`; summaries at the pre-registered paths `evidence/cross_component.json`, `evidence/real_event_traces.json`, `evidence/operations.json`, `evidence/fresh_env.json`.
- Change control: PI-D-110; code `5ebce8a`; `repair/OLD_CODE_CHECK.txt`, `repair/REAL_ENTRIES_SCAN.json`, `repair/PHASE19_REGISTRY_PATHS.json`; reruns `evidence/repair_rerun/`.
- Records: `PHASE_20_EVIDENCE.md`, `PHASE_20_RESULTS.json`, `experiments/SEARCH_LEDGER.csv`, `experiments/LEDGER_TOTALS.json`, `postcommit/`, `../COST_LEDGER.md`, `docs/predictive-intelligence/{DECISIONS,ROADMAP,HANDOFF}.md`.

## Code

- Audit code: `probes/scenarios.py` (P01 to P48; `Check.ok(..., gate=False)` marks a probe assertion that records a finding without failing the check), `run_matrix.py` (scenario-to-test map), `cx_rerun.py`, `reproductions.py`, `recalc.py` (own parser, label rules and logistic arithmetic), `oos_sensitivity.py`, `threat_scan.py`, `flag_off_identity.sh` and `flag_off_summary.py`, `e2e.sh`, `fresh_env.sh` and `lo_up.py`, `cli_import_trace.py`, `ledger.py`.
- Changed lab code (CP20-1 only): `memelab/predictive/registry.py` (`training_after_cutoff`, `status_at`, `pin_event`), `memelab/predictive/integration.py` (`run_pass` capture-time check, `_process` token-row identity, `recompute_point`, `render`, `analyze_line`), `memelab/predictive/reports.py` (one call to `recompute_point` in `_target_view`); `tests/fixtures/predictive/phase18/PINNED_SHA256.json`.
- Not changed: `memelab/predictive/monitoring.py` (frozen G25 path), every lab module outside `memelab/predictive/`.

## Commands to reproduce (your own clone; private stores under `/home/claude/pi_research/` for the reproductions)

```
git log --format='%h %cI %s' e0bc906..HEAD
python -m pytest tests/test_predictive_phase20_cross.py -q -rxX
python -B audits/predictive-intelligence/phase_20/probes/scenarios.py P01      # any of P01 to P48; exit 0 when every gating assertion holds
python -B audits/predictive-intelligence/phase_20/probes/run_matrix.py /tmp/p20_matrix
python -B audits/predictive-intelligence/phase_20/probes/cx_rerun.py /tmp/p20_cx
python -B audits/predictive-intelligence/phase_20/probes/recalc.py /tmp/p20_recalc.json
python -B audits/predictive-intelligence/phase_20/probes/oos_sensitivity.py /tmp/p20_oos.json
python -B audits/predictive-intelligence/phase_20/probes/threat_scan.py /tmp/p20_threat.json
bash audits/predictive-intelligence/phase_20/probes/flag_off_identity.sh HEAD /tmp/p20_flagoff && python -B audits/predictive-intelligence/phase_20/probes/flag_off_summary.py /tmp/p20_flagoff /tmp/p20_flagoff.json
bash audits/predictive-intelligence/phase_20/probes/e2e.sh HEAD /tmp/p20_e2e
python -B audits/predictive-intelligence/phase_20/probes/reproductions.py HEAD /tmp/p20_repro.json
# old-code check: the current cross-test file against the audited code
git worktree add --detach /tmp/p20_old 0d66379 && cp tests/test_predictive_phase20_cross.py /tmp/p20_old/tests/ && (cd /tmp/p20_old && python -m pytest -q tests/test_predictive_phase20_cross.py)
```

The e2e, flag-off and fresh-environment scripts need `unshare` (root or a user namespace); the flag-off script checks the checkout's `git status` at the end, so do not edit the checkout while it runs. `run_prospective.py drift` appends to the committed Phase 19 ledger (F20-14): run it only in a sandbox clone. No paid call is needed; no network is needed except PyPI for the fresh environment.
