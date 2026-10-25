# Feature store contract (Phase 05, schema `memelab.predictive.store/1`, feature version 2)

The point-in-time evidence and feature store of the predictive engine. Code: `memelab/predictive/store.py` (schema, migrations, ingestion, integrity), `memelab/predictive/sources.py` (git export reader, GeckoTerminal plan and fetch), `memelab/predictive/features.py` (as-of view, features, snapshots, training view, truncation proof). Tests: `tests/test_predictive_asof_store.py`, `tests/test_predictive_asof_features.py`, `tests/test_predictive_asof_fixture.py`. Where this document and the code differ, the code is the contract and this document is wrong; `tests/test_predictive_asof_fixture.py` checks that every table, feature, missing reason, the schema checksum and the definitions hash below appear here.

Research only. The feature flag stays OFF and no existing module imports these files (`tests/test_predictive_contract.py::test_no_existing_module_imports_the_predictive_package`). Standard library only (numpy is allowed by PI-D-031 and not needed). No label, barrier or class is computed here; labels are Phase 06's.

## Where the store lives (PI-D-036)

| Item | Rule |
|---|---|
| File | a private SQLite file; default `data/private/predictive_store.sqlite` (gitignored), override `MEMELAB_PREDICTIVE_STORE`, or any path given to `store.connect` |
| Never | the tracked `data/memelab.sqlite` or the file named by `MEMELAB_DB`: `store.connect` refuses both before creating anything (test `test_store_refuses_the_tracked_lab_database`) |
| Lab schema | unchanged: `db.init_db` does not create, migrate or know any `predictive_*` table (test `test_init_db_creates_no_predictive_table`); no existing table, migration or module changed |
| Phase 05 build | `/home/claude/pi_research/p05/predictive_store.sqlite`, outside the repository, built by `audits/predictive-intelligence/phase_05/probes/build_store.py`; the raw vendor bodies are committed as gzip under `phase_05/raw/` with `raw/MANIFEST.csv`, so the store can be rebuilt offline |

## Migration and rollback

Numbered migrations with a checksum ledger, the pattern of `memelab/social/schema.py`: `store.migrate(con)` applies pending versions in one transaction each and records `(version, name, sha256 of the up script, applied_at)` in `predictive_schema_migrations`; an applied version whose script changed is refused. `store.rollback(con, target=0)` runs the down scripts newest first, drops only `predictive_*` tables and, at target 0, the ledger, so the database schema is byte-identical to before (test `test_migrate_then_rollback_leaves_a_full_lab_database_identical`, on a database that already holds the lab, social, catalyst, chains and launch tables, P33). Take a backup first with `memelab.social.schema.backup_db`: a rollback deletes the store's rows.

<!-- generated:migrations:start -->
| Version | Name | Up script sha256 |
|---|---|---|
| 1 | point-in-time evidence and feature store | `775d6683f76b89c68938007eb8c6009fe537ab4e06e33409dbc81454fc270f12` |
<!-- generated:migrations:end -->

## Tables (version 1)

Every data table is append-only: triggers refuse UPDATE and DELETE (test `test_every_data_table_is_append_only`). Every time column is UTC epoch seconds (REAL); a value outside 1e9 to 1e10 (a millisecond stamp, for example) is refused at ingestion (`store.epoch_seconds`). Addresses are TEXT compared byte for byte (`COLLATE BINARY`).

| Table | One row per | Key fields |
|---|---|---|
| `predictive_raw_responses` | external read: a GeckoTerminal response, or a state-export version read from git | `response_key` = sha256(source, URL, retrieval, body sha256); `request_url`, `request_json` (parameters, including `token`), `retrieved_at` (when the bytes arrived), `http_status`, `body_sha256`, `body_bytes`, `body_gzip` (vendor bodies; an export body stays in git, named by commit and blob), `boundary_at` (the request's `before_timestamp`), `cover_from` (the earliest candle the read returned) and `cover_complete` (always 0 since the repair pass: a short page proves nothing earlier), counts of candles kept, dropped after the boundary and refused, `identity_check`, `collector`, `ingest_version`, `schema_version`, `recorded_at` |
| `predictive_candles` | distinct version of one candle position | `obs_key`; `series_key` = sha256(source, chain, pool, period, start); `source_record_id` = `<pool>:<period>:<start>`; `chain`, `mint`, `pool_address`; `period_s`, `start_at`, `end_at`; `o`, `h`, `l`, `c`, `v`; `vanished`; `event_time` (provider candle start); `published_at` (NULL: UNKNOWN for this vendor); `retrieved_at` (first read of this version); `available_at` and `available_basis`; `revision_of`, `revision_kind`; `response_key`, `raw_sha256` |
| `predictive_candle_reads` | later read that returned an existing version unchanged | `obs_key`, `response_key`, `retrieved_at` |
| `predictive_source_status` | planned fetch series (one pool, one boundary) and how it ended | `status` (OK, NO_DATA, READ_FAILED, CIRCUIT_OPEN, CALL_CAP_REACHED, BAD_BODY, IDENTITY_MISMATCH), `period_s`, `boundary_at`, `need_from`, `cover_from`, `cover_complete`, `last_end_at`, `calls`, `candles_kept`, `response_keys_json`, `checked_at` |
| `predictive_decisions` | decision event of `decisions.py` | `decision_key` = sha256(chain, mint, created_at, row_sha256, decision_time); `chain` (NULL when the export has no token row, never a default), `mint`, `pool_address` (point-in-time `primary_pool` or `graduated_pool`); `row_sha256`, `created_at` (data only); `decision_time`, `decision_time_basis` (EXPORT_COMMIT or CAPTURE_TIME only, CHECK); `export_commit`, `export_blob`, `row_first_visible`; `token_first_seen_at` (the token row's write-time trace); `status`, `flags_json` (KEY_CONFLICT), `rows_sharing_key`; `row_json`, `token_json`; `response_key`; `recorded_at` (the store's own write time); CHECK `decision_time >= row_first_visible` and `decision_time >= created_at` |
| `predictive_feature_sets` | feature definitions hash | `feature_set_sha`, `feature_version`, `definitions_json` |
| `predictive_snapshots` | feature snapshot of one (chain, mint, time, version, mode) | `snapshot_key` = sha256(chain, mint, time, version, mode); `decision_key`; `decision_time` = `cutoff_at` (CHECK); `feature_version`, `feature_set_sha`, `availability_mode`; `data_version` (sha256 of the input fingerprints); `source_status_json`; `max_input_available_at` (CHECK at or before the cutoff); `snapshot_sha256` |
| `predictive_feature_values` | value of one feature in one snapshot | `chain`, `mint`, `pool_address`, `decision_time`, `cutoff_at`, `feature_name`, `feature_version`; `value` or `missing_reason` with `missing_basis` (CHECK exactly one); `feature_available_at` (CHECK at or before the cutoff), `available_basis`, `evidence` (FACT, HEURISTIC, INFERENCE, UNKNOWN); `source_ids_json`, `raw_hashes_json`, `source_record_count`, `retrieved_at`, `source_fingerprint` |

## Clocks

| DATA_TIME_CONTRACT field | Here | Meaning |
|---|---|---|
| `event_time` | `predictive_candles.event_time`; for a decision the thesis's `created_at` is kept as data | when the market interval started; `created_at` is the collector-run start (PI-D-011), never used as a time for availability |
| `published_at` | `predictive_candles.published_at` | NULL: GeckoTerminal states no publication time (UNKNOWN) |
| `first_seen_at` | `predictive_decisions.token_first_seen_at`, `row_first_visible` | the token row's wall-clock write time in the export; the first export commit that holds the exact row |
| `ingested_at` | `recorded_at` on every table | when this store wrote the row |
| `retrieved_at` | raw responses, candles, candle reads, feature values | when the lab received the bytes; never a historical availability claim (P04) |
| `available_at` | candles; decisions use `decision_time` | the conservative moment inference may use the row, with `available_basis` |
| `decision_time` | decisions, snapshots, values | the first export commit holding the exact decision row (EXPORT_COMMIT, PI-D-015 as amended by PI-D-021) or a capture time; the validator and a CHECK refuse anything else |
| `cutoff_at` | snapshots, values | equal to the decision time of the snapshot |
| `feature_available_at` | values | the latest availability among the inputs the value used |
| `label_matures_at` | not here | Phase 06 |

Availability bases of a candle version:

| Basis | When | `available_at` |
|---|---|---|
| PROVIDER_LAG_RECONSTRUCTION | first version of a position, read after its end plus the provider lag | `end_at + 300` (`replay_sources.PROVIDER_LAG`, a HEURISTIC: the vendor is assumed to serve a closed candle 300 s after it ends) |
| CAPTURE | first version read before that time (a live read) | the read's `retrieved_at` |
| REVISION_FIRST_READ | a changed version, a position that appears after an earlier read covered it without it, or a vanished position (tombstone) | the revising read's `retrieved_at` |

Two availability modes for features: `provider` uses `available_at` (the reconstruction above for backfilled history); `capture` uses `retrieved_at`, so a backfill never counts for a decision before the lab read it (P04). Decision-row features are available at the export commit in both modes (the row is inside the commit).

## Identity (P01, P02, PI-D-022)

- A Solana mint or pool must be base58 that decodes to exactly 32 bytes; an EVM token is `0x` plus 40 hex; an EVM pool may also be a 32-byte pool id (`0x` plus 64 hex, Uniswap v4). Nothing is lowercased or trimmed: two strings that differ in one character or in letter case are two identities (`store.check_address`). A decision whose identity fails is refused and counted, never stored.
- No symbol or name column exists in any table, so none can take part in a join.
- A pool belongs to exactly one mint: a read of a pool already read for another mint is refused (`ingest_gt_response`), and a plan that gives one pool to two mints is refused (`sources.plan_backfill`).
- Candle features read only the point-in-time pool of the decision row's export; another pool of the same mint never enters (test `test_same_symbol_mints_and_other_pools_never_join`).
- Vendor identity: GeckoTerminal prices the pool's base token unless `token=<address>` asks for another. The token parameter is read from the URL actually sent (`store.url_token`); a read whose recorded parameters name another token than its URL is refused before anything is stored (skeptic counterexample CX-05). A read whose body does not show that the candles are the mint's price is kept as a raw read and gives no candle: `identity_check` OK_BASE (no token parameter, mint is base) or OK_TOKEN_PARAM (the URL's `token` equals the mint exactly and the body's meta shows the mint as base, as every real `token=<mint>` read does; amended in Phase 06, PI-D-045) pass; MINT_IS_QUOTE, MINT_NOT_IN_POOL, OTHER_TOKEN_PARAM (`base`, `quote` or any other address), TOKEN_PARAM_NOT_BASE (`token=<mint>` sent but the body still shows the other token as base, Phase 06 counterexample CX-S06) and NO_META refuse every candle and the series ends IDENTITY_MISMATCH. Every Phase 05 request now carries `token=<mint>`, as the lab's collector does (`memelab/bridge/plan.py`).
- `store.snapshot_ref_ok(con, chain, mint, snapshot_hash)` is the PI-D-022 check that a forecast's `snapshot_hash` is the `row_sha256` of a decision record of that exact (chain, mint).

## Ingestion rules

State exports (`store.ingest_exports`, `sources.export_versions`): every version of `data/state/latest.json` along the first-parent history of the pinned ref, oldest first, read from git objects (nothing checked out). Decision events come from `decisions.candidates` and `decisions.decisions` unchanged. A call must include every export version already stored (decision events depend on every earlier version; a partial history would turn a re-exported old row into a new decision); later versions only add later decisions. Re-ingesting the same history adds nothing.

GeckoTerminal reads (`store.ingest_gt_response`), in retrieval order per pool:

1. The raw read is stored with its request, retrieval time, HTTP status, body sha256 and gzip body; the same read twice adds nothing.
2. The identity check above.
3. Candles ending after the request boundary are dropped and counted (`start + period > boundary`): `before_timestamp` is inclusive and returns the candle that holds an unaligned boundary (PI-D-034, PI-D-035).
4. Each candle passes `outcomes_core.normalize_observation` (high and low contain open and close; a candle that closes after the read is refused), positive prices, non-negative volume and the epoch-seconds unit check; anything else is refused and counted.
5. A version equal to the current one adds a read record; a changed one, a late appearance or a vanished position adds a new version available from this read, pointing at the version it follows, with `revision_kind` OPEN_WINDOW (only open, high or low differ: the vendor computes the open of the earliest candle of a response from the request window), VALUES, APPEARED or VANISHED. History is never rewritten (P07). Features use closes and volumes only, so an OPEN_WINDOW version never changes a feature.

Fetch (`sources.fetch_series`): paged newest first through `runtime.CallGuard` (5.7 calls a minute in the Phase 05 run, under the frozen 6; 1,200 calls a run; breaker after 5 consecutive failures, every non-200 answer counts); HTTP 429 waits 60 s and retries up to 3 times; the series ends OK, NO_DATA, READ_FAILED, BAD_BODY, IDENTITY_MISMATCH, CIRCUIT_OPEN or CALL_CAP_REACHED, and that status is a row of `predictive_source_status`.

Holdout seal (`sources.plan_backfill`, `check_plan`, `fetch_scope`): only Solana decisions with a point-in-time pool in the development period (decision before 2026-10-17T00:00Z and the 6 h label maturity at or before it) are fetched; each pool's request boundary is its latest such decision and at most 2026-10-16T23:00Z, so no read touches a holdout decision's window [decision - 3600 s, maturity] (ACCEPTANCE holdout_contacted rule). Retrospective-holdout, purged and prospective decisions keep their rows and get candle features MISSING with NOT_FETCHED_SEALED.

## The invariant and how it is enforced

Every feature input's conservatively established `available_at` is at or before the decision time, and a feature input 1 s after the decision is absent:

| Layer | Mechanism | Test |
|---|---|---|
| SQL | the view selects decisions and candle versions with availability at or before the cutoff | `test_an_input_available_one_second_after_the_decision_is_absent_and_one_at_it_is_present` |
| Revisions | `outcomes_core.visible` picks, per position, the newest version available at the cutoff | `test_stored_snapshots_do_not_move_when_later_data_arrive` |
| Audit | every row the computation reads passes `replay_core.Audit`, which raises `replay_core.LeakageError` for a later row | `test_a_view_whose_filters_are_bypassed_is_caught_by_the_audit` |
| Values | a value available after the cutoff raises LeakageError before it is returned; CHECKs on the snapshot and value tables | `test_features_as_of_is_deterministic_and_complete` |
| Truncation | features from the store truncated at the decision equal the full store's (`features.truncation_check`, the replay harness's leakage proof); a feature that peeks ahead is caught | `test_truncation_invariance_in_both_modes`, `test_truncation_check_is_sensitive_to_a_read_past_the_cutoff` |
| Rows | `features.validate_rows` (ported from the Phase 04 prototype): exact columns, every availability present, finite and at or before the decision, decision at or before the training as-of, labels only when matured | `test_the_row_validator_refuses_future_unknown_and_undeclared_inputs` |
| Universe | universe features count only decisions at or before the cutoff (P43) | `test_a_later_mint_never_enters_an_earlier_universe` |

## API

| Function | Contract |
|---|---|
| `features.features_as_of(con, chain, mint, decision_time, feature_version, *, mode="provider", persist=False, now=None)` | the snapshot of the exact (chain, mint) as of the time: the newest decision record of that mint at or before it, its export row, the mint's earlier decisions, the chain's universe, and the decision's point-in-time pool candles, all through the as-of view. Deterministic (same store and arguments, same `snapshot_sha256`, also across fresh processes). Refuses another feature version (FeatureVersionError), a malformed identity (StoreError) and a non-finite time |
| `features.build_snapshots(con, *, feature_version, mode, now)` | one persisted snapshot per decision record at its own decision time; records without a known chain are counted |
| `features.save_snapshot` | writes once; a second write of the same key with another hash raises SnapshotDriftError and changes nothing |
| `features.recompute_matches(con, snapshot_key)` | the stored snapshot equals its recomputation from the store as it is now (later rows must not move it) |
| `features.training_view(con, *, as_of, feature_version, mode)` | stored decision snapshots with decision time at or before `as_of`, one version, one definitions hash, one mode; checked by `validate_rows`; refuses a store that holds another version or hash for that period |
| `features.truncated_copy`, `features.truncation_check` | the truncation proof |
| `features.require_compatible(version, sha=None)` | versions are incompatible by default (P46) |
| `store.verify(con)` | recomputes body hashes, candle-to-body hashes, decision row hashes, value invariants and snapshot hashes |

## Feature set version 2

<!-- generated:sha:start -->
Definitions hash (`features.feature_set_sha()`): `90781ad72ac1ab81d3e52882c22e4c89214e5d6cba0e3f843042fe8dc8c2848b`, 32 features.
<!-- generated:sha:end --> Transform revision `asof-2` (version 1 assumed a short vendor page proved no earlier trade; version 2 assumes nothing before the earliest candle read, repair m2). Values are stored to 10 significant digits so hashes are stable across platforms. "t" is the snapshot time; a window counts candles that end in (t - window, t] and are available at t.

<!-- generated:features:start -->
| Feature | Group | Source | Unit | Window | Transform | Evidence when a value |
|---|---|---|---|---|---|---|
| `thesis_log_price_usd` | thesis | state-export | ln usd | none | ln(snapshot.price); price <= 0 is NON_POSITIVE | FACT |
| `thesis_log1p_liquidity_usd` | thesis | state-export | ln usd | none | ln(1 + snapshot.liquidity); negative is NEGATIVE | FACT |
| `thesis_log1p_mcap_usd` | thesis | state-export | ln usd | none | ln(1 + snapshot.mcap) | FACT |
| `thesis_log1p_vol_24h_usd` | thesis | state-export | ln usd | none | ln(1 + snapshot.vol_24h) | FACT |
| `thesis_log1p_exit_cap_3pct_usd` | thesis | state-export | ln usd | none | ln(1 + snapshot.exit_cap_3pct); stale context, not depth now | FACT |
| `thesis_holders` | thesis | state-export | count | none | snapshot.holders | FACT |
| `thesis_adj_top10_pct` | thesis | state-export | percent | none | snapshot.adj_top10 | FACT |
| `thesis_cluster_pct` | thesis | state-export | percent | none | snapshot.cluster_pct | FACT |
| `thesis_dev_pct` | thesis | state-export | percent | none | snapshot.dev_pct | FACT |
| `thesis_insider_pct` | thesis | state-export | percent | none | snapshot.insider_pct | FACT |
| `thesis_net_buyers_24h` | thesis | state-export | count | none | snapshot.net_buyers_24h (may be negative) | FACT |
| `thesis_score` | thesis | state-export | points | none | row.score; version-dependent (PI-D-008): data_version names the export commit | FACT |
| `thesis_fatal_present` | thesis | state-export | 0 or 1 | none | 1 when row.fatal_flags_json is a non-empty list | FACT |
| `thesis_status_rejected` | thesis | state-export | 0 or 1 | none | 1 when row.status is REJECTED | FACT |
| `thesis_snapshot_age_s` | thesis | state-export | s | none | query time - row.created_at (created_at as data, PI-D-011) | FACT |
| `token_age_s` | token | state-export | s | none | query time - token.first_pool_at (provider claim recorded in the export) | FACT |
| `hist_prior_decisions` | history | state-export | count | none | decision events of the same chain and mint before this one | FACT |
| `hist_seconds_since_prior_decision` | history | state-export | s | none | decision time - previous decision time of the mint | FACT |
| `hist_log_price_change_since_prior` | history | state-export | ln ratio | none | ln(price now / price at the previous decision) | FACT |
| `universe_decisions_24h` | universe | state-export | count | 86400 s | decision events of the chain in (t - 24 h, t] | FACT |
| `universe_new_mints_24h` | universe | state-export | count | 86400 s | mints of the chain whose first decision is in (t - 24 h, t] | FACT |
| `cdl_last_close_age_s` | candle | geckoterminal-ohlcv | s | none | t - end of the newest available candle of the point-in-time pool | HEURISTIC |
| `cdl_log_ret_1h` | candle | geckoterminal-ohlcv | ln ratio | 3600 s | ln(last close / close of the newest candle ending at or before t - 1 h) | HEURISTIC |
| `cdl_log_ret_6h` | candle | geckoterminal-ohlcv | ln ratio | 21600 s | same over 6 h | HEURISTIC |
| `cdl_log_ret_24h` | candle | geckoterminal-ohlcv | ln ratio | 86400 s | same over 24 h | HEURISTIC |
| `cdl_vol_usd_1h` | candle | geckoterminal-ohlcv | usd | 3600 s | sum of candle volume, candles ending in (t - 1 h, t] and available | HEURISTIC |
| `cdl_vol_usd_24h` | candle | geckoterminal-ohlcv | usd | 86400 s | same over 24 h | HEURISTIC |
| `cdl_candles_24h` | candle | geckoterminal-ohlcv | count | 86400 s | 5-minute candles with trades ending in (t - 24 h, t] | HEURISTIC |
| `cdl_rv_6h` | candle | geckoterminal-ohlcv | ln | 21600 s | sqrt(sum of squared ln close-to-close changes) from the price at t - 6 h through the window | HEURISTIC |
| `cdl_log_drawdown_24h` | candle | geckoterminal-ohlcv | ln ratio | 86400 s | ln(last close / max close over the window and the price at t - 24 h); closes only: a candle's open, and with it high or low, depends on the request window | HEURISTIC |
| `cdl_log_range_24h` | candle | geckoterminal-ohlcv | ln ratio | 86400 s | ln(max close / min close) over the window and the price at t - 24 h; closes only | HEURISTIC |
| `xsrc_log_close_over_thesis_price` | cross | geckoterminal-ohlcv+state-export | ln ratio | none | ln(last close / snapshot.price): pool route consistency (P02) | HEURISTIC |
<!-- generated:features:end -->

Zero is a value only where the covered vendor history shows no trade in the window (volume, candle count, realized variation); a window that the fetched history does not cover is OUTSIDE_FETCHED_WINDOW, never zero. `thesis_score` is version-dependent (PI-D-008); `data_version` and the value's raw hash name the export it came from. `thesis_log1p_exit_cap_3pct_usd` is stale context, not executable depth at any later time (P08).

## Missing reasons

Every missing value names a reason and its basis. AS_OF reasons are decided by what existed at the decision and may be model inputs. HEURISTIC reasons are decided by the vendor history under the provider-lag reconstruction. RETRIEVAL reasons are decided by what the lab fetched or what the vendor served when read (sealed windows, failed reads, a vendor with no data, a read that priced another token): they are censoring, never a model input, because they can carry information from after the decision (a pool the vendor no longer serves may have died later, P09).

<!-- generated:reasons:start -->
| Reason | Basis |
|---|---|
| `ABSENT_IN_SNAPSHOT` | AS_OF |
| `INCONSISTENT_TIME` | AS_OF |
| `NEGATIVE` | AS_OF |
| `NON_POSITIVE` | AS_OF |
| `NOT_IN_UNIVERSE` | AS_OF |
| `NOT_NUMERIC` | AS_OF |
| `NO_POOL_AT_DECISION` | AS_OF |
| `NO_PRIOR_DECISION` | AS_OF |
| `NO_TOKEN_ROW` | AS_OF |
| `OUT_OF_SCOPE_CHAIN` | AS_OF |
| `UNPARSEABLE` | AS_OF |
| `NO_CANDLE_AVAILABLE` | HEURISTIC |
| `CALL_CAP_REACHED` | RETRIEVAL |
| `CIRCUIT_OPEN` | RETRIEVAL |
| `NOT_FETCHED` | RETRIEVAL |
| `NOT_FETCHED_SEALED` | RETRIEVAL |
| `NOT_RETRIEVED_BY_DECISION` | RETRIEVAL |
| `OUTSIDE_FETCHED_WINDOW` | RETRIEVAL |
| `VENDOR_BAD_BODY` | RETRIEVAL |
| `VENDOR_IDENTITY_MISMATCH` | RETRIEVAL |
| `VENDOR_NO_DATA` | RETRIEVAL |
| `VENDOR_READ_FAILED` | RETRIEVAL |
<!-- generated:reasons:end -->

Each snapshot's `source_status` names, per source, OK or the RETRIEVAL reasons that left values missing: an outage, a dead pool or a sealed window is visible next to the decision features that remain (P47, P09).

## Versions and immutable references

| Item | Value | Rule |
|---|---|---|
| Schema | `memelab.predictive.store/1` | a schema change is a new migration, never an edit of version 1 (checksum); the repair pass edited only comments of version 1 before any store outside this phase existed, and the pinned checksum moved with it |
| Ingest versions | `state-export/1`, `geckoterminal-ohlcv/1` | on every raw read, candle and decision row |
| Feature version | `2` | any transform change bumps it with `TRANSFORM_REVISION`; the definitions hash, the golden fixture and this document change with it (1 to 2 in the Phase 05 repair pass, m2) |
| Snapshot reference | `snapshot_key` and `snapshot_sha256` | training, inference and reports cite a snapshot by key and hash; the decision behind it by `decision_key` and `row_sha256` (the forecast contract's `snapshot_hash`) |

## Known limits

- Historical candle availability is a reconstruction (HEURISTIC): the store proves what the vendor served when read, not what it served at the decision. Revisions are detected only between reads the lab made (Phase 05 re-read sample and the comparisons in `evidence/revision_check_*.json`); a revision before the lab's first read cannot be seen.
- A short or empty vendor page is not evidence that nothing traded earlier: the vendor bounds each request in time (an empty page at 2026-10-14 for a pool with a candle on 2026-09-28, skeptic m2). Coverage starts at the earliest candle read, and a window that starts before it is OUTSIDE_FETCHED_WINDOW (RETRIEVAL). Labels must not read an empty page as "no trade" (the halt target, Phase 06).
- A candle's open, and with it high or low, depends on the request window (80 of 57,584 candles read twice); only closes and volumes feed features. Labels that test barriers on highs and lows (Phase 06) inherit this.
- A read without `token=<mint>` prices the vendor's base token, and the vendor's orientation of a pool can change: an inbox read of 2026-10-06 priced the other token of a pool whose meta now names the mint as base. Only a read's own meta, or the token parameter, establishes whose price it is.
- Only the point-in-time pool is read; a decision without one gets NO_POOL_AT_DECISION. No executable depth exists for past times (P08).
- Export decision times inherit the export clocks of PI-D-021 item 6 (four exports reached GitHub later than their commit time).
