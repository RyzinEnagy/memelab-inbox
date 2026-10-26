# Point-in-time data contracts as implemented (Phase 05)

Code: `memelab/backtest/schema.py` (tables, triggers, migrations), `memelab/backtest/timeguard.py` (clocks, as-of), `memelab/backtest/store.py` (writes, reads, experiment ids). Schema version: bt v1. Tests: `tests/test_backtest_timeguard.py`.

## Clock vocabulary

| Field | Meaning | Rule |
|---|---|---|
| event_time | when the thing happened (post published, block time, bar start) | never makes a record visible earlier |
| observed_at | when a collector saw it | available_at >= observed_at (CHECK) |
| available_at | earliest moment the lab could act on it | the only field as-of joins use |
| decision_time | when a strategy decided | features must have available_at <= decision_time (Audit raises LeakageError) |
| earliest_execution_time | first bar open at or after decision_time + latency | `timeguard.earliest_execution`; None at end of data |
| fill_time | when a fill happened | >= submission_time >= decision_time (CHECK) |

All times are UTC epoch seconds. `timeguard.utc_ts` refuses naive datetimes, naive ISO strings, epoch milliseconds, NaN and out-of-range values.

## Mapping to the package contracts

| Contract (REQUIRED_DATA_CONTRACTS) | Table | Notes |
|---|---|---|
| asset_id | bt_asset_versions | key {chain, mint}; symbol display only; decimals/program versioned by content hash |
| pool_id | bt_pool_versions | pool_type CPMM/CLMM/DLMM/BONDING_CURVE/STABLE/UNKNOWN; pools_valid_at() requires pool_created_at <= cutoff |
| observation | bt_observations | value_state OBSERVED/ZERO/MISSING/STALE/UNAVAILABLE/UNKNOWN_AS_OF; corrections via supersedes_id; idempotent on (provider, kind, payload hash) |
| robot_capture | bt_capture_provenance (+ existing catalyst tables) | historical_asof_proof NONE unless contemporaneous capture / independent archive / signed observation; mint only when mint_verified = 1 |
| catalyst | existing catalyst_* tables + bt_observations kind CATALYST_CLAIM | reused, not duplicated |
| market_bar | bt_market_bars | closed bars only; first version available at end + provider lag (AVAIL_MODELED, BACKFILLED flags); revisions available from their own observed_at (REVISION) |
| liquidity_state | bt_liquidity_states | basis OBSERVED_RESERVES / LIQ_SNAPSHOT / QUOTE_DERIVED; effective_quote_adj for PumpSwap virtual reserves |
| execution_quote | bt_execution_quotes | present-tense quotes with quote_at, expiry, slot; never used as historical fills |
| experiment_run | bt_experiment_runs + bt_run_results | run_id = sha256(config + dataset hash + seed + engine version + code sha); trials_before recorded |
| fill | bt_fills | statuses FILLED/PARTIAL/FAILED/CANCELED/EXPIRED |
| risk_result | bt_assessments (+ bt_assessment_events) | idempotent request_key; FAST and DEEP stages |
| outcome | bt_outcomes | observed_asof >= decision_time; censored flag; supersedes_id |
| universe | bt_universe_members, bt_token_lifecycle | frozen discovery universe incl. rejected and dead tokens |

## Immutability

Every bt data table has BEFORE UPDATE and BEFORE DELETE triggers that abort. Rollback drops bt tables only (back up first with `schema.backup_db`). Legacy tables are never touched; verified on a copy of the tracked database (fingerprint of every non-bt table equal before migrate, after migrate and reopen, and after rollback).

## Integration status

The schema is created lazily by the backtest package (`store.ensure`) and is not added to `db.init_db`, so `python -m memelab init` and the existing pipeline behave exactly as before when the feature is off.
