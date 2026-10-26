# Minimum point-in-time contracts for implementation — align to actual repo schema

These are **conceptual required fields**, not an instruction to create duplicate tables before auditing the existing SQLite or bundle schema. Prefer append-only versioned records and adapter extensions:

- `asset_id`: `{chain, exact_mint}`, token symbol is display-only; token program and decimals versioned.
- `pool_id`: `{chain, pool_address, dex_program, pool_type, quote_asset}`, reserve/bin/tick snapshot when observed and historical availability.
- `observation`: `{provider, raw_source_id, raw_payload_hash, event_time, observed_at, available_at, validity_until, raw_ref, chain_height?, block_time?, confidence, ingest_version}`; time must be UTC and unambiguous.
- `signal`: `{signal_id, strategy_id, strategy_version, asset_id, based_on_observation_ids, candidate_time, decision_time, earliest_execution_time, feature_values, parameters, confidence, invalidation, applicable_asof}`.
- `robot_capture`: `{collector, robot_id?, run_id?, source_url, canonical_origin, content_hash, captured_at, first_seen_at, source_published_at?, source_edited_at?, available_at, raw_ref, schema_version, edition?, status}`. A Maxun collector is optional; version original observations rather than overwrite and use canonical source registry across crawlers. The act of crawling an old page now never establishes past known-at.
- `catalyst`: `{catalyst_id, origin_source, claim_text_hash, evidence_refs, event_time, first_seen, verified_at?, claim_type, credibility_score, correlated_origin_group, subsequent_outcome?}`; distinguish claims from onchain observed transactions and executed swaps.
- `market_bar`: `{mint, pool/route basis, timeframe, start, end, OHLCV, observed_at, available_at, covered_venues, quality_flags, source}`; bars aren't L2/reserves.
- `liquidity_state`: `{pool_id, asof, available_at, reserve_base, reserve_quote, fees, ticks/bins_if_applicable, routing_id_if_applicable, raw_ref}`; don't pretend consolidated USD liquidity is tradable stablecoin inventory.
- `execution_quote`: `{from_mint, to_mint, input_amount_raw, output_amount_raw, quote_at, available_at, expiry, route_legs, fees, slot/block, provider, failed_paths, source_hash}`; real **present** quotes are not retroactive.
- `experiment_run`: `{run_id, code_sha, dataset_hash, label_definition, universe_definition, discovery_rule, train_valid_test_ranges, embargo_policy, seed, strategy_version, cost_model_version, engine_version, baseline, fees, concurrency_limit, assumptions, created_at, status}`.
- `fill`: `{run_id, asset_id, decision_time, submission_time, fill_time?, action, requested_amount, filled_amount, price, impact, fee_breakdown, source_basis, status, reason}`.
- `risk_result`: `{snapshot_id, run_id, position_usd, evidence_tier, backtest_coverage, downside_scenarios, executable_proceeds_by_size, chance_estimates_if_justified, invalidation, uncertainty, blocking_flags}`.
- `outcome`: `{opportunity_id, horizon, observed_asof, realized_price_path, route_depth_path, actual_viability, measurement_protocol_version, censored_flag, missing_reason}`.

### Time guard

Every feature must have `available_at <= decision_time`; every trade must have `execution_time >= decision_time` and must use a price/route observable **after** submission or a justified model. As-of joins must choose last eligible records with staleness limits. If `event_time < available_at`, that does not make the event historically knowable earlier. Preserve original immutable observations when later corrected.

### History & denominators

Track chain-native amounts and quote currency, USD conversion rates by time, token decimals, pool-specific reserves, circulating/total supply with provider definitions, liquidity source and route coverage. Label locked/burned/LP/treasury wallets separately, with attribution confidence. Do not infer wallet common human identity from common funding alone.

### State labels

Recommended machine states: `COMPLETE`, `PARTIAL_WITH_LIMITATIONS`, `INSUFFICIENT_HISTORY`, `INSUFFICIENT_EXECUTION_DATA`, `UNSUPPORTED_POOL`, `STALE_DATA`, `INVALID_TOKEN_ID`, `UNVERIFIED_CATALYST`, `RISK_FATAL_FLAW`, `SOURCE_BLOCKED`, `ERROR`.

Historical point-in-time evidence has precedence over present snapshots for historical replay. If source lacks historical reserves, CPMM/CLMM precision **cannot** be asserted; report a conservative estimate/tier if explicitly justified, otherwise abstain.
