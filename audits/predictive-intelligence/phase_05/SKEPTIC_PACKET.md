# Phase 05 skeptic packet

For the orchestrator's independent skeptic (PI-D-013). Artifacts, code paths and commands only; the phase's conclusions are in PHASE_05_EVIDENCE.md and are deliberately not repeated here.

## Task

Phase 05 of the package: "Implement provenance-preserving point-in-time feature storage without future leakage" (`phases/PHASE_05_immutable_temporal_evidence_and_feature_store.md`, references DATA_TIME_CONTRACT.md, SCIENTIFIC_VALIDATION.md, ADVERSARIAL_SCENARIOS.md). Gate: executable as-of invariants and regression. Assume the phase looks successful but is wrong. Produce a new wrong-but-plausible counterexample (a row, a read, an export or a call sequence) and show whether a test or a recorded check catches it. Scenarios named for this phase: P01, P02, P03, P04, P07, P09, P36, P43, P46, P47, and PI-D-011 rule 3.

## Code

- `memelab/predictive/store.py`: schema v1 (`V1_UP`, `V1_DOWN`, `migrate`, `rollback`), `connect`, `check_address`, `b58decode`, `epoch_seconds`, `ingest_exports`, `gt_identity`, `ingest_gt_response`, `record_series_status`, `verify`, `snapshot_ref_ok`.
- `memelab/predictive/sources.py`: `export_versions`, `development_period`, `fetch_scope`, `plan_backfill`, `check_plan`, `gt_url`, `curl_get`, `fetch_series`.
- `memelab/predictive/features.py`: `FEATURES`, `REASONS`, `AsOfView`, `_val`, `_candle_values`, `compute`, `features_as_of`, `save_snapshot`, `build_snapshots`, `recompute_matches`, `training_view`, `validate_rows`, `truncated_copy`, `truncation_check`.
- Reused, unchanged: `memelab/predictive/decisions.py`, `memelab/predictive/runtime.py` (`CallGuard`, `guarded`), `memelab/social/replay_core.py` (`Audit`, `LeakageError`), `memelab/social/outcomes_core.py` (`normalize_observation`, `visible`), `memelab/social/replay_sources.py` (`PROVIDER_LAG`), `memelab/state.py` (`import_`, used by a test).

## Tests

- `tests/test_predictive_asof_store.py`, `tests/test_predictive_asof_features.py`, `tests/test_predictive_asof_fixture.py`
- Helpers and fixtures: `tests/fixtures/predictive/asof_helpers.py`, `asof_pid011_export.json`, `asof_fixture.json`

## Artifacts

- Contract: `audits/predictive-intelligence/phase_05/data/FEATURE_STORE_CONTRACT.md`; coverage: `data/SOURCE_COVERAGE.md`; plan: `data/backfill_plan.json`
- Raw vendor bodies: `audits/predictive-intelligence/phase_05/raw/*.json.gz` and `raw/MANIFEST.csv`
- Call log: `evidence/backfill_calls.json` (first run); later calls: `evidence/backfill_calls.json` entries after the first run, `evidence/revision_check_inbox15.json`
- Checks: `evidence/store_summary.json`, `evidence/coverage_counts.json`, `evidence/asof_real_truncation.json`, `evidence/asof_real_traps.json`, `evidence/asof_real_recompute.json`, `evidence/asof_real_fresh.json`, `evidence/revision_check_p04.json`, `evidence/revision_check_inbox15.json`, `evidence/revision_check_store.json`, `evidence/mutation_asof.json`, `evidence/cli_regression.json`
- Probes: `probes/build_store.py`, `probes/build_fixtures.py`, `probes/revision_check.py`, `probes/asof_real_checks.py`, `probes/coverage_counts.py`, `probes/mutation_asof.py`, `probes/cli_regression.py`, `probes/render_contract.py`
- The real store (not in git): `/home/claude/pi_research/p05/predictive_store.sqlite`; the first-run store it was rebuilt from: `/home/claude/pi_research/p05/predictive_store_firstread.sqlite`; the inbox comparison store: `/home/claude/pi_research/p05/revision_inbox15.sqlite`; Phase 04's raw bodies: `/home/claude/pi_research/p04_gt_raw/`

## Commands to reproduce

From the repository root:

```
python -m pytest tests/test_predictive_asof_store.py tests/test_predictive_asof_features.py tests/test_predictive_asof_fixture.py -q
python -m pytest tests -q
python -m memelab social guard
python tools/release_audit.py --history
```

From `audits/predictive-intelligence/phase_05/probes/` (the store paths above; no network except where marked):

```
python -B build_store.py summary
python -B coverage_counts.py
python -B asof_real_checks.py truncation
python -B asof_real_checks.py traps
python -B asof_real_checks.py recompute
python -B asof_real_checks.py fresh
python -B revision_check.py p04
python -B revision_check.py store
python -B mutation_asof.py /tmp/mut05.json
python -B cli_regression.py 074953d HEAD /tmp/cli05.json
python -B build_store.py rebuild        # offline: needs the first-run store, writes a new store (move the current one away first)
python -B revision_check.py inbox15     # network: 9 GeckoTerminal calls
```

Rebuilding the store from the committed raw archive alone: every `raw/*.json.gz` row of `raw/MANIFEST.csv` carries the request URL, retrieval time, HTTP status, pool, mint and boundary that `store.ingest_gt_response` needs; the export rows come from git at ref `98338a8`.
