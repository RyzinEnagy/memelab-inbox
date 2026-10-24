# PHASE 05: chronology-safe immutable data and experiment schema

State: PASS. Date 2026-10-23. Entry gate: Phase 04 PASS (`python3 audits/backtesting/bakeoff/compare.py` exit 0, 16/16, rerun at start).

## Changed files

- New: `memelab/backtest/__init__.py`, `schema.py` (bt v1: 16 tables, append-only triggers, checksummed migrations, rollback, backup), `timeguard.py` (utc_ts, Bar, closed_bars, earliest_execution, Series, asof with OBSERVED/ZERO/MISSING/STALE/UNAVAILABLE/UNKNOWN_AS_OF, Audit/LeakageError, visible_events, latest_versions), `store.py` (idempotent append-only writes, bar availability and revision rules, pools_valid_at, universe_asof, register_run with reproducible run_id).
- New: `tests/test_backtest_timeguard.py` (15 tests: G01-G08, bar revisions, partial bars, migration on a copy of the tracked DB, changed-migration refusal, triggers on every table, run-id reproducibility, research-only import/text guard).
- Changed: `tools/release_audit.py`, five reviewed-hit entries for backtesting audit notes, the prompt package, isolated smoke scripts, one env-var-name match and the backtest refusal-list tests (D-BT-016). Negative control: the same rule inside `memelab/backtest/` is not exempt.
- Docs: `audits/backtesting/data/CONTRACTS.md`.
- `db.init_db` NOT changed: bt tables are created lazily by the backtest package, so the lab is unchanged when the feature is off.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_backtest_timeguard.py -q` | 0 | 15 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p05_mutations.json` | 0 | 7 of 7 mutations caught (pass 2; pass 1 found M05-7 survived, fixed by a new G02 assertion) |
| full suite before the release-audit entries (`testing/logs/p05_full_pytest.log`) | 1 | 3 failed (C-1 plus two release-audit scans hitting audit prose), 798 passed |
| full suite and release tools after commit | see PHASE_05 addendum in HANDOFF | |

## Gate

G01-G08 PASS (tests named test_g01 ... test_g08). Existing DB copy migrated, reopened and rolled back with every legacy table fingerprint unchanged. Prior analysis results unchanged (no legacy code path modified).

## Negative review

Plausible wrong output: "a bar revision fetched later can be backdated to the original bar availability" (M05-5) and "pools listed today are valid for past decisions" (M05-7). Both mutations are caught by tests; the first pass showed M05-7 surviving because the G02 test only exercised pools observed after the cutoff, so a test with a pre-announced pool address was added.

## Limitations

Bar availability for backfilled history is modeled (end + provider lag, flagged AVAIL_MODELED/BACKFILLED). Catalyst rows stay in the existing catalyst tables; bt_capture_provenance only extends them.

NEXT ELIGIBLE PHASE: 06.
