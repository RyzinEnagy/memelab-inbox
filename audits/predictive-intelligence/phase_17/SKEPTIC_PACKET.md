# Phase 17 skeptic packet

Task for the independent reviewer: try to falsify Phase 17 ("connect every eligible discovery or material catalyst change to a forecast or a visible abstention"). The phase's own conclusions are claims to test. Work in your own clone (`git clone -q /home/claude/memelab-inbox <dir> && git checkout -q feature/predictive-intelligence`), a temporary `MEMELAB_DB`, no network beyond what the brief allows (none is needed here).

## Read first

- Prompt: package `phases/PHASE_17_opportunity_discovery_prediction_integration.md`, `EXECUTION_RULES.md`, `references/INTEGRATION_AND_CONFLICTS.md`, `BACKTEST_V12_BRIDGE.md`, `FORECAST_OUTPUT_SCHEMA.md`, `ADVERSARIAL_SCENARIOS.md` (P01, P02, P15, P34, P35, P39, P40, P44, P47, P48).
- Orchestrator note for this phase: the hook placement of PI-D-017, flag `predictive.enabled` OFF by default, byte-identical output when OFF (P40), fatal-flaw overrides always win, idempotent ids, bounded latency and cost, stale status on outage, bounded queue, today every request ABSTAIN (Phase 16 NO_VIABLE_CHAMPION, Phase 13 UNCALIBRATED), BACKTEST_NOT_AVAILABLE with a read-only adapter on fixtures, Phase 13 carried items m3 and m4.
- Pre-registration: `ACCEPTANCE_CHECKLIST.md` (rules 1 to 17, G1 to G27, CX-17), `experiments/EXPERIMENT_REGISTRY.csv`, `docs/predictive-intelligence/DECISIONS.md` PI-D-093 (and the Phase 16 records PI-D-085 to PI-D-092, Phase 13 PI-D-067 to PI-D-071, Phase 01 PI-D-017, PI-D-022).

## Code

- `memelab/cli.py` (the hook: `_predictive_section`, `_predictive_line`, two call sites); pre-Phase-17 copy `tests/fixtures/predictive/cli_before_phase17.py.txt` (sha256 pinned in the test).
- `memelab/predictive/integration.py` (integration-1), `memelab/predictive/bt_adapter.py` (bt-adapter-1).
- Existing modules it calls: `registry.py` (`serve`, `resolve`, `target_plan`, `reference_record`), `abstention.py` (`forecast_result`, `evaluate`, `validate_publication`, `append`), `calibration.py`, `features.py` (`features_as_of` capture mode), `store.py` (`ingest_exports`, `check_address`), `decisions.py` (`row_sha256`), `onchain.py` (`decision_support`), `depth_adapter.py`, `runtime.py` (`CallGuard`, `guarded`), `contract.py` (`forecast_id`, `backtest_status`, `enabled`).
- Amended isolation tests: `tests/test_predictive_contract.py` (seam), `test_predictive_registry.py`, `test_predictive_calibration.py`, `test_predictive_onchain.py` (`git diff 7f7bc28 3d2089b -- tests/`).
- Read-only context: `origin/feature/backtesting` at `69bc5c3` (`memelab/backtest/hook.py`, `assess.py`, `schema.py`).

## Artifacts

- `integration/REQUEST_FLOW.md`; `smoke/REAL_PATH_SMOKE.json`, `smoke/REAL_SCOUT_SECTION.md`, `smoke/real_path_runs.txt`, `smoke/REAL_EXPORT_REPLAY.json`, `smoke/TRACE_EXAMPLES.json`, `smoke/FIXTURE_E2E.json`; `evidence/mutation_integration.json`, `evidence/mutation_prefreeze_first_probe.json`, `evidence/entry/`; `experiments/SEARCH_LEDGER.csv`, `LEDGER_TOTALS.json`; `PHASE_17_EVIDENCE.md`, `PHASE_17_RESULTS.json`.
- Probes: `probes/real_path_smoke.sh`, `probes/run_integration.py` (replay, smoke, trace, fixture, summarize), `probes/mutation_integration.py`, `probes/ledger.py`.
- Tests: `tests/test_predictive_integration.py`, `tests/test_predictive_phase17_outputs.py`.

## Commands to reproduce

```
python -m pytest tests/test_predictive_integration.py tests/test_predictive_phase17_outputs.py -q
python -m pytest tests/test_predictive_contract.py tests/test_predictive_registry.py tests/test_predictive_calibration.py tests/test_predictive_onchain.py -q
bash audits/predictive-intelligence/phase_17/probes/real_path_smoke.sh <frozen commit 3d2089b...> /tmp/p17_smoke
python -B audits/predictive-intelligence/phase_17/probes/run_integration.py smoke /tmp/p17_smoke /tmp/p17_smoke/REAL_PATH_SMOKE.json
python -B audits/predictive-intelligence/phase_17/probes/run_integration.py replay /tmp/p17_replay
python -B audits/predictive-intelligence/phase_17/probes/run_integration.py trace /tmp/p17_smoke /tmp/p17_replay /tmp/p17_trace.json
python -B audits/predictive-intelligence/phase_17/probes/run_integration.py fixture /tmp/p17_fx
python -B audits/predictive-intelligence/phase_17/probes/mutation_integration.py /tmp/p17_mut.json
python -m memelab.predictive.integration status --state-dir /tmp/p17_smoke/state
python -m pytest tests -q
```

The smoke script needs `unshare -n` (it runs every lab command without a network namespace) and `git show 71fc50e:data/state/latest.json` (fetch `origin/main` if your clone lacks it).

## Questions worth attacking (not conclusions)

- Can any input make a section, line or document carry a probability, a size or a trading word on real data, or make the scout body, lists, statuses, scores or lab tables differ with the flag on or off?
- Is "exactly once" true under reorderings, repeated mints, rows sharing a key, crashes between appends, clock skew, a registry change between passes, or a replay older than the state?
- Does the material gate miss a change that should be material, or make one that should not (CX-17 is the pre-registered one)?
- Do the outage states hide anything, and can an outage ever turn into a FORECAST?
- Do the amended isolation tests still catch what they caught before, and does any other module now reach the integration or the protected modules?
- Is the backtesting adapter honest about what it can know, and is BACKTEST_NOT_AVAILABLE truly derived rather than asserted?
- Are the Phase 13 items m3 and m4 really closed, or only closed for the paths the tests exercise?
