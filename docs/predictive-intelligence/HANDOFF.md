# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-101). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_18/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-27

- Phases 00 to 13, 16 and 17: PASS. Phases 14 and 15: TEST_ONLY (behavioral path, optional, OFF).
- Phase 18 (reports, CLI and alerts without trading directives): **NEEDS_REVIEW**, first pass with two self-review change controls (CP18-0 PI-D-099, CP18-1 PI-D-100); result PI-D-101. The orchestrator's independent skeptic has not run; the skeptic packet is `audits/predictive-intelligence/phase_18/SKEPTIC_PACKET.md`.
- Spend: 0 Firecrawl credits, 0 vendor calls, 0 language-model calls, no network use; every real-data command ran inside `unshare -n` with sockets refused.

## What Phase 18 built

- `memelab/predictive/reports.py` (report-1 and alerts-rules-1, PI-D-098), imported by no module; CLI `python -m memelab.predictive.reports report|alerts|alerts-state` (`--state-dir`, `--config`, `--lab-db`, `--registry-dir`, `--out`, `--json`; alerts `--alert-db`, `--outbox`, `--as-of`, `--fixture-run`; `--send` refused). Flag `predictive.enabled` off: each command prints FLAG_OFF and writes nothing. No existing file changed except the one isolation test of checklist rule 14 (the integration is a leaf for every module but `reports.py`); every lab module is pinned at `4ebccc3` by `tests/fixtures/predictive/phase18/PINNED_SHA256.json`.
- Reports read the persisted state only through `integration.load_state` and `check_state`; a document only with its record and its request; a FORECAST number only when the record, the stored raw number, point, interval and calibration card sha, and the registry-resolved cards agree (`integration.check_document`); otherwise DOCUMENT_REFUSED with no number. Sections in the lab's FACT / INFERENCE / HEURISTIC / UNKNOWN buckets (`memelab.report._ev`): at a glance, system status (registry, Phase 13 calibration, BACKTEST_NOT_AVAILABLE, SIMULATION_NOT_AVAILABLE), target definitions, carried constraints, per opportunity (identity and snapshot, the lab's structural research and technical labels from the thesis row whose snapshot hash matches, catalyst evidence, predictive research with an unblock line per reason, historical out-of-sample record, execution and stress with the request record's backtest veto, behavioral scenarios, sources and ids, limitations), events not attempted, units and times.
- Alerts reuse the social-intel alert state schema, cooldown, daily cap, quiet hours, local times, disclaimer, file sink and readable-state renderers, in dry run only: risk_override (warning), reevaluate (notice, TEST_ONLY), forecast_withdrawn (notice, TEST_ONLY), pipeline_health; a veto overrides a forecast; never an alert for an abstention alone; warnings first under the cap; new passes only.
- Deliverables: `phase_18/ui/EXAMPLE_REPORTS.md`, `ui/ALERT_RULE_MATRIX.md`, `ui/MISSING_DATA_UX.md`, `real/` (the real reports and dry-run alert runs), golden files `tests/fixtures/predictive/phase18/golden/` (7), tests `tests/test_predictive_reports.py` (65) and `tests/test_predictive_phase18_outputs.py` (7); mutation probe 49 of 49.

## Results (PI-D-101)

- Real sandbox scout state at `ea799da`: 8 opportunities, 24 targets, 0 probabilities, every target ABSTAIN (MODEL_NOT_SELECTED, UNCALIBRATED, INSUFFICIENT_HISTORY, SOURCE_STALE; TARGET_NOT_FEASIBLE 6), inputs INPUT_STALE, 8 of 8 snapshots verified, 3 fatal-flag vetoes (GOMO CANNOT_EXIT_5K, HIGGS and slopcannon WASH_TRADING_HIGH); dry-run alerts 0 (3 suppressed SOURCE_STALE).
- Real export replay: 47 opportunities, 141 targets, 0 probabilities, 22 with a veto; dry-run alerts 8 risk_override previews, 15 suppressed SOURCE_STALE; nothing sent.
- Flag off: the real scout is byte-identical to `b0fad12` at `96c4445`, `0127d2e` and `ea799da`.
- Format-only fixtures (watermarked): a validated forecast, a strong forecast (83%) with an impossible exit (the veto overrides it, the notice is suppressed), a withdrawn forecast, a forged number refused, injected symbols withheld.

## Open items, in order

1. The orchestrator runs the independent skeptic on Phase 18 and returns the review for the repair pass; then the orchestrator pushes.
2. Phase 19 (only after Phase 18 PASS): outcome tracking reads the request records and documents through the same pairing; the reports can then show matured outcomes beside past documents without rewriting them.
3. If Elving wants a promotion path: the change control to ACCEPTANCE `promotion` (PI-D-091), registered before prospective labels are read. A promoted champion would still abstain in integration-1 (family 07 only; INFERENCE_NOT_CHECKED for a real champion) until a change control adds its feature builder and probe inputs.
4. Frozen cards are MODEL_STALE after 2026-10-31T00:00:00Z; the reports then name MODEL_STALE in the system status.
5. Carried: catalyst and social tables are not exported; forward depth collection approved but not deployed (PI-D-044); keep `tests/test_predictive_reproductions.py` green; a merge of the backtesting PR #4 needs the steps in `phase_17/integration/REQUEST_FLOW.md`; any external alert delivery needs Elving's approval.

## Phase 18 commits

HEAD before `4ebccc3`; pre-registration `ebb7059`; frozen code `96c4445`; recorded outputs `3601881`; CP18-0 code `0127d2e`; repeated outputs `44118a1`; CP18-1 code `ea799da`; repeated outputs `100d262`; the records commit on top of it and the post-commit record commit (suite, guard, seal check, single-branch release audit in `phase_18/postcommit/`). Local only; the orchestrator pushes.

## Waiting on Elving

- The change control that could reopen promotion (ACCEPTANCE `promotion`), any paid data, LLM, Zep or MiroFish use, any external alert delivery (Telegram or email), scheduled catalyst or social collection into a store this engine can read, a merge of the backtesting PR #4 into this line, a merge into `main`, deploying the forward depth collector (approved, PI-D-044; not yet done), and turning the flag on anywhere outside a sandbox.

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (a reviewed false positive on that branch, D-BT-016; PI-D-049 item 6). It is not reachable from `feature/predictive-intelligence`, whose own audit passes on a single-branch clone.

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no seed phrases or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flag overrides unchanged. Forecasts stay a separate evidence section with the flag OFF by default. No raw social content in the repository. Behavioral output is fictional, never a probability. References are never forecasts. Alerts are previews in a local outbox; nothing is sent.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git log -14 --oneline
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
python -m pytest tests/test_predictive_reports.py tests/test_predictive_phase18_outputs.py -q
bash audits/predictive-intelligence/phase_17/probes/real_path_smoke.sh $(git rev-parse HEAD) /tmp/p18_smoke
unshare -n python -B audits/predictive-intelligence/phase_17/probes/run_integration.py replay /tmp/p18_replay
unshare -n python -B audits/predictive-intelligence/phase_18/probes/run_reports.py real /tmp/p18_smoke /tmp/p18_replay /tmp/p18_real
python -B audits/predictive-intelligence/phase_18/probes/mutation_reports.py /tmp/p18_mut.json
```

Use a full clone (the commit-order tests of Phases 15 to 17 fail on a shallow one by design) and fetch `origin/main` so `71fc50e` exists. Expect `"problems": []` from the seal check and, in the suite, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` and `tests/test_catalyst_firecrawl.py::test_page_history_and_spend_survive_a_new_session_through_the_state_export` (real clock) failing; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The smoke script needs `unshare -n`.
