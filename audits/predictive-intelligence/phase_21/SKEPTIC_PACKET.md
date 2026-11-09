# Phase 21 skeptic packet

Task for the independent reviewer (fresh context, own clone, never the main checkout): try to falsify the Phase 21 release decision and its evidence. In particular: is the classification higher than the evidence allows; did the clean-environment run really come from the pushed branch with only numpy and pytest, no credentials and no network; does the chronology audit check what it says (and would it miss a real leak); are the out-of-sample statements and the maturity result stated correctly; do the operator documents give a command that does something other than they say, or omit a decision that waits on Elving. Produce one new wrong-but-plausible counterexample and a check that catches it. Class findings MATERIAL or MINOR.

## Pre-registration and decisions

- `audits/predictive-intelligence/phase_21/ACCEPTANCE_CHECKLIST.md` (commit `0bb361e`), `experiments/EXPERIMENT_REGISTRY.csv`
- `docs/predictive-intelligence/DECISIONS.md` PI-D-115, PI-D-116; earlier PI-D-091 (promotion), PI-D-081 (MiroFish), PI-D-005 (not approved)

## Artifacts

- Release documents: `audits/predictive-intelligence/phase_21/release/` (RELEASE_DECISION.md, INSTALL_RUNBOOK.md, USER_GUIDE.md, MODEL_LIMITS.md, ROLLBACK_PROOF.md, SMOKE_LOG.md, OPEN_DECISIONS.md); `docs/predictive-intelligence/RELEASE.md`
- Release checks: `audits/predictive-intelligence/phase_21/evidence/release_checks/` (logs/, suite tails, chronology_audit.json, p19_audit/, matrix/, cx/, oos_sensitivity.json, independent_recalc.json, threat_scan.json, e2e/, flag_off_identity.json, flagoff/, reproductions.json)
- Doc commands: `evidence/doc_commands/`; documents check: `evidence/release_docs_check.json`
- Maturity step: `evidence/maturity/` and the appended record in `audits/predictive-intelligence/phase_19/evidence/outcomes_runs.json`
- Ledger rows: `experiments/SEARCH_LEDGER_P21_ROWS.csv`, `LEDGER_TOTALS.json`; cost row in `audits/predictive-intelligence/COST_LEDGER.md`
- `PHASE_21_EVIDENCE.md`, `PHASE_21_RESULTS.json`

## Code paths

- Phase 21 probes: `audits/predictive-intelligence/phase_21/probes/release_checks.sh`, `chronology_audit.py`, `measure.py`, `doc_commands.sh`, `docs_demo.py`, `release_docs_check.py`
- Reused probes: `audits/predictive-intelligence/phase_20/probes/` (e2e.sh, flag_off_identity.sh, flag_off_summary.py, run_matrix.py, scenarios.py, cx_rerun.py, oos_sensitivity.py, recalc.py, threat_scan.py, reproductions.py, lo_up.py); `phase_17/probes/real_path_smoke.sh`, `run_integration.py`; `phase_19/probes/fetch_labels.py`, `run_prospective.py`
- Engine: `memelab/predictive/` (registry.py, integration.py, reports.py, monitoring.py), `memelab/cli.py` (`_predictive_enabled`, `_predictive_section`, `_predictive_line`)

## Commands to reproduce

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/predictive-intelligence
# (after the orchestrator pushes the Phase 21 commits; until then fetch them from the local checkout)
bash audits/predictive-intelligence/phase_21/probes/release_checks.sh 90e4c6f <phase-21 commit> /tmp/p21_rc
python -B audits/predictive-intelligence/phase_21/probes/chronology_audit.py 2026-11-09T00:00:00Z /tmp/p21_chrono.json
bash audits/predictive-intelligence/phase_21/probes/doc_commands.sh /tmp/p21_rc/e2e/smoke /tmp/p21_doc
python -B audits/predictive-intelligence/phase_21/probes/release_docs_check.py /tmp/p21_docs.json --plant
python -B audits/predictive-intelligence/phase_21/probes/docs_demo.py 2026-11-09T00:00:00Z /tmp/p21_demo.json
```

The maturity commands (`fetch_labels.py fetch`, `run_prospective.py outcomes`) write to the private store under `/home/claude/pi_research/p19/` and append to tracked files; run them only in a sandbox copy. `release_checks.sh` needs root for `unshare` and about 25 minutes.
