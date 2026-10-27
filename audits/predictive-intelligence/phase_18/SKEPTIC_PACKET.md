# Phase 18 skeptic packet

Task for the independent reviewer: try to falsify Phase 18 ("expose explainable calibrated predictions and scenarios through reports, CLI and alerts without trading directives"). The phase's own conclusions are claims to test. Work in your own clone (`git clone -q /home/claude/memelab-inbox <dir> && git checkout -q feature/predictive-intelligence`), a temporary `MEMELAB_DB`, no network (none is needed).

## Read first

- Prompt: package `phases/PHASE_18_reports_cli_alerts_and_decision_support.md`, `EXECUTION_RULES.md`, `references/FORECAST_OUTPUT_SCHEMA.md`, `INTEGRATION_AND_CONFLICTS.md`, `BACKTEST_V12_BRIDGE.md`, `MIROFISH_EVALUATION.md`, `WORK_PRODUCT_EXAMPLE.md`, `ADVERSARIAL_SCENARIOS.md` (P08, P12, P17, P24, P25, P27, P34, P38, P40, P44).
- Orchestrator note for this phase: today every forecast abstains (NO_VIABLE_CHAMPION, UNCALIBRATED); the reports must make the abstention, its reasons, the target definitions, horizons, cohort, snapshots, sources, model status, BACKTEST_NOT_AVAILABLE and SIMULATION_NOT_AVAILABLE readable at a glance and never show a probability, a score boost or trading language; reuse the lab's FACT / INFERENCE / HEURISTIC / UNKNOWN buckets and the social-intel alert conventions (dedupe, cooldown, caps, dry-run default) instead of a new renderer; alerts dry run or file sink only; the backtest veto of a forecast lives in its request record; render the Phase 13 carried constraints and the Phase 17 sanitization; fixture examples watermarked as format-only; the real report from the sandbox run; flag OFF by default with the flag-off lab outputs byte-identical.
- Pre-registration: `ACCEPTANCE_CHECKLIST.md` (rules 1 to 15, G1 to G24, CX-18), `experiments/EXPERIMENT_REGISTRY.csv`, `docs/predictive-intelligence/DECISIONS.md` PI-D-098, and the two self-review change controls PI-D-099 (CP18-0) and PI-D-100 (CP18-1, amends rule 13). Earlier records that bind it: PI-D-068, PI-D-070 (Phase 13), PI-D-085 to PI-D-092 (Phase 16), PI-D-093 to PI-D-097 (Phase 17).

## Code

- `memelab/predictive/reports.py` (report-1: `build`, `render`, `check_text`; alerts-rules-1: `make_alert_policy`, `alert_candidates`, `alert_run`, `render_alert_text`; CLI `main`). Imported by no module.
- What it reuses: `memelab/predictive/integration.py` (`load_state`, `check_state`, `pair_errors`, `check_document`, `load_registry`, `_load_card`, `_calibration_card`, `_ident`, `_mint_text`, `_plain_ok`, `snapshot_sha`, `connect_lab_ro`, `state_dir_refusal`), `memelab/report.py` (`_ev`), `memelab/social/alerts_core.py`, `alerts_engine.py`, `alerts_transport.py`.
- The one amended existing test: `tests/test_predictive_contract.py::test_no_predictive_module_imports_the_integration_module` (`git diff 4ebccc3 HEAD -- tests/test_predictive_contract.py`).
- Tests: `tests/test_predictive_reports.py`, `tests/test_predictive_phase18_outputs.py`; golden files `tests/fixtures/predictive/phase18/golden/`; pinned sha256 of every lab module at `4ebccc3` in `tests/fixtures/predictive/phase18/PINNED_SHA256.json`.

## Artifacts

- `ui/EXAMPLE_REPORTS.md`, `ui/ALERT_RULE_MATRIX.md`, `ui/MISSING_DATA_UX.md`.
- `real/REAL_SCOUT_REPORT.md`, `real/REAL_REPLAY_REPORT.md`, `real/REAL_ALERTS_SCOUT_DRY_RUN.txt`, `real/REAL_ALERTS_REPLAY_DRY_RUN.txt`, `real/REAL_RUN_CHECKS.json`, `real/REAL_PATH_SMOKE.json`, `real/REAL_EXPORT_REPLAY.json`, `real/real_path_runs.txt`.
- `evidence/` (entry gate, mutation probes, old-code checks, rerun diffs), `experiments/SEARCH_LEDGER.csv`, `LEDGER_TOTALS.json`, `PHASE_18_EVIDENCE.md`, `PHASE_18_RESULTS.json`.
- Probes: `probes/run_reports.py` (goldens, real), `probes/mutation_reports.py`, `probes/cp18_0_old_code_check.py`, `probes/cp18_1_old_code_check.py`, `probes/rerun_diff.py`, `probes/ledger.py`, `probes/make_examples_doc.py`.

## Commands to reproduce

```
python -m pytest tests/test_predictive_reports.py tests/test_predictive_phase18_outputs.py tests/test_predictive_contract.py -q
python -B audits/predictive-intelligence/phase_18/probes/run_reports.py goldens /tmp/p18_gold && diff -r /tmp/p18_gold tests/fixtures/predictive/phase18/golden
bash audits/predictive-intelligence/phase_17/probes/real_path_smoke.sh <code commit> /tmp/p18_smoke
unshare -n python -B audits/predictive-intelligence/phase_17/probes/run_integration.py smoke /tmp/p18_smoke /tmp/p18_smoke/REAL_PATH_SMOKE.json
unshare -n python -B audits/predictive-intelligence/phase_17/probes/run_integration.py replay /tmp/p18_replay
unshare -n python -B audits/predictive-intelligence/phase_18/probes/run_reports.py real /tmp/p18_smoke /tmp/p18_replay /tmp/p18_real
python -B audits/predictive-intelligence/phase_18/probes/mutation_reports.py /tmp/p18_mut.json
echo '{"predictive": {"enabled": true}}' > /tmp/cfg_on.json
python -m memelab.predictive.reports report --config /tmp/cfg_on.json --state-dir /tmp/p18_smoke/state --lab-db /tmp/p18_smoke/runs/frozen_on/lab.sqlite
python -m memelab.predictive.reports alerts --config /tmp/cfg_on.json --state-dir /tmp/p18_smoke/state --alert-db /tmp/p18_alerts/a.sqlite
python -m pytest tests -q
```

The smoke script needs `unshare -n` and `git show 71fc50e:data/state/latest.json` (fetch `origin/main` if your clone lacks it). Use a full clone.

## Questions worth attacking (not conclusions)

- Can any persisted state, token text, lab row, registry file or config make a report or an alert show a number for an abstaining or refused target, a base rate or reference-model number, a size, a trade step, a local path, or text that reads as a score change? Can a fixture number appear without the watermark, or in a live alert run?
- Is every FORECAST number really tied to the raw number and cards, or only for the forgeries the tests try? What can an adversary who re-seals the state consistently still do?
- Are the checks in `_target_view` independent, or does one mask another in a way the mutation probe cannot see?
- Do the alert conventions (dedupe, cooldown, daily cap, quiet hours, new passes only, dry run) hold under reordering, repeated runs, clock changes, a lost run record, a tampered alert database, or two states sharing one alert database? Can a notice crowd out a warning? Can an alert be sent?
- Is anything material hidden from the at-a-glance view (a veto, a refused document, a stale input, an unverified snapshot, a not-attempted event)?
- Is the lab snapshot verification sound (could a row of another snapshot or another chain be used)?
- Does the flag-off claim hold for every lab output, and do the amended and new isolation tests still catch what they should?
