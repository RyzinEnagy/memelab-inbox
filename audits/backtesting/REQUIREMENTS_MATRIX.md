# Requirements matrix (Phase 01)

Baseline f99c6c7 plus Phase 00 commit 912fc96. Status: EXISTS_TESTED, EXISTS_UNTESTED, PARTIAL, MISSING, BLOCKED. "Owner" is the phase that must close the row. Paths are relative to `memelab/`.

## 1. Data contracts (references/REQUIRED_DATA_CONTRACTS.md)

| Contract | Existing coverage | Status | Gap | Owner |
|---|---|---|---|---|
| asset_id {chain, exact_mint}, symbol display-only, program/decimals versioned | `tokens` keyed by mint, chain column; decimals/token_program updated in place | PARTIAL | no versioning of decimals/program; update in place | 05 |
| pool_id {chain, pool, dex_program, pool_type, quote_asset} | `pools` (pool_address, mint, dex, quote_mint) | PARTIAL | no pool_type, no dex program id | 05, 06 |
| observation {provider, raw id, payload hash, event_time, observed_at, available_at, validity_until, raw_ref, slot, confidence, ingest_version} | core tables carry observed_at only; social/catalyst carry more | PARTIAL | no available_at, hash or raw_ref in core | 05 |
| signal {ids, strategy version, asset, observation ids, candidate/decision/earliest_execution, features, params, invalidation} | none for TA; social replay signals in memory only | MISSING | | 05, 08, 09 |
| robot_capture {collector, robot/run ids, url, canonical origin, content hash, captured/first_seen/published/edited/available, raw_ref, schema, edition, status} | catalyst_page_fetches (url, hashes, page_published_at, page_modified_at, fetched_at); catalyst_items (published_at, first_seen_at) | PARTIAL | no collector/robot/run id, no edition, no canonical origin group across tools | 05, 06A |
| catalyst {origin, claim hash, evidence refs, event_time, first_seen, verified_at, type, credibility, origin group, outcome} | catalyst_events/items/sources/revisions/outcomes | EXISTS_TESTED (mostly) | origin group is publisher-level; first-known vs published separated | 09 |
| market_bar {mint, pool basis, tf, start, end, OHLCV, observed_at, available_at, venues, quality flags, source} | OHLCV fetched per run, not stored | MISSING | | 05, 06 |
| liquidity_state {pool, asof, available_at, reserves, fees, ticks/bins, routing id, raw_ref} | pool_snapshots (reserve_usd, base/quote reserve at observed_at) | PARTIAL | present-tense only; no fees, no ticks/bins | 05, 06, 07 |
| execution_quote {mints, raw amounts, quote_at, available_at, expiry, legs, fees, slot, provider, failed paths, hash} | liquidity_quotes (in/out, impact, route_json, status at observed_at) | PARTIAL | no slot, expiry or hash; quote is present tense only | 05, 07 |
| experiment_run {run_id, code sha, dataset hash, label/universe/discovery rule, splits, embargo, seed, versions, baseline, fees, concurrency, assumptions, status} | social replay outputs sha256s per run (not persisted as table) | MISSING | | 05, 10, 11 |
| fill {run, asset, decision/submission/fill time, action, requested/filled, price, impact, fee breakdown, basis, status, reason} | none | MISSING | | 07, 10 |
| risk_result {snapshot, run, size, tier, coverage, scenarios, proceeds by size, invalidation, uncertainty, blocking flags} | m26 stress (portfolio level), m17/m18 sizing and realizable | PARTIAL | not per opportunity, not persisted | 12, 13 |
| outcome {opportunity, horizon, observed_asof, path, depth path, viability, protocol version, censored, missing reason} | catalyst_outcomes (untested), social outcomes ledger, launch cohort | PARTIAL | no outcome tracker for scout theses | 15 |
| Time guard (available_at <= decision_time; execution after decision) | social replay CutoffView/Audit; outcomes_core visible() | EXISTS_TESTED (social only) | core has no guard; m13 uses unfinished bars (C2) | 05, 08 |
| Denominators (chain-native amounts, USD at time, decimals, supply definitions) | normalize keeps raw in/out for quotes; sol_price at observation | PARTIAL | no time-indexed SOL/USD series | 06, 07 |

## 2. Golden scenarios G01 to G35

| ID | Short | Existing evidence | Status | Owner |
|---|---|---|---|---|
| G01 | same ticker, two mints never merged | keyed by mint everywhere; social identity tests | EXISTS_TESTED (core keying) | 05 (retest in backtest store) |
| G02 | same mint, two pools, no double count | none | MISSING | 07 |
| G03 | news posted 09:00, ingested 09:08, processed 09:12 | catalyst four timestamps; chrono three clocks | PARTIAL | 05, 09 |
| G04 | transfer at 10:00 is not a sale until the 11:00 swap | social wallet events distinguish kinds | PARTIAL | 09 |
| G05 | bar high before close; earliest execution after close plus delay | none; C2 shows m13 reads unfinished bars | MISSING | 05, 08, 10 |
| G06 | delisted/rugged token stays in universe | lab history includes rejected and dead tokens; GT still serves dead pools (probe) | PARTIAL | 06, 11 |
| G07 | zero vs missing vs stale | modules keep None; GT omits no-trade hours | PARTIAL | 05, 06 |
| G08 | corrected/deleted posts stay immutable as-known | catalyst revisions, social observations append-only | PARTIAL | 05, 09 |
| G09 | static CPMM hand-calculated swap | none | MISSING | 07 |
| G10 | $1k/$10k/$100k non-linear fills | router quotes per size (present only) | PARTIAL | 07 |
| G11 | same USD liquidity, CLMM vs CPMM | concentrated flag only | MISSING | 07 |
| G12 | pool drained between signal and order | none | MISSING | 07, 12 |
| G13 | partial route fails, no phantom fill | quote status NO_ROUTE/ERROR | PARTIAL | 07 |
| G14 | buy/sell fees, Token-2022, decimals, network fee, fee authority change | m08 parses; C1 shows fee dropped downstream | PARTIAL (defective) | 07 |
| G15 | stale Jupiter quote flagged, never a historic fill | social market_context TTL 120 s | PARTIAL | 07 |
| G16 | depeg, SOL/USD move, multi-hop denominators | none | MISSING | 07, 12 |
| G17 | small quote ok, full exit impossible within impact cap | m17 exit_max, m18 realizable | PARTIAL | 07, 12 |
| G18 | wick vs confirmed close vs failed retest, no repaint | m14 state machine on closes (not bar-close-safe) | PARTIAL | 08 |
| G19 | insider sells, price holds, selling dries: observed vs interpreted | m11 absorption text | PARTIAL | 08, 09 |
| G20 | coordinated posts from one origin are one source | catalyst publisher corroboration; social narratives independence | EXISTS_TESTED (social/catalyst) | 09 (reuse) |
| G21 | attention after rally is not prescient | chrono_core ordering | PARTIAL | 09 |
| G22 | shuffled catalyst times weaken relationship | none | MISSING | 09, 11 |
| G23 | conflicting sentiment plus sell flow plus low depth is not a buy | m24 fatal flags, catalyst assess fatal override | PARTIAL | 09, 12 |
| G24 | 50 simultaneous signals, cash and risk conserved | none | MISSING | 10 |
| G25 | stop gaps through, loss exceeds intended risk | m27 MAE/MFE only | MISSING | 10, 12 |
| G26 | tiny sample, huge win rate, abstain | m28 n gates; replay min-n | PARTIAL | 11 |
| G27 | multiple trials, sealed test, winner's curse | replay LabelGate freeze | PARTIAL (social) | 11 |
| G28 | baselines under same costs and universe | replay raw-mention baseline | PARTIAL | 10, 11 |
| G29 | independent math vs framework ledgers reconcile | none | MISSING | 04, 07, 10 |
| G30 | combined extreme stress, no impossible outputs | m26 single scenario | PARTIAL | 12 |
| G31 | brand-new token: no token-specific validation claim | launch cohort INSUFFICIENT HISTORY | PARTIAL | 08, 12, 13, 14 |
| G32 | frozen replay reproduced byte for byte | replay sha256s; hash-chained ledger | PARTIAL | 15 |
| G33 | existing scout/analyze tests unchanged; live-order hook rejected | release audit trade-code scan | EXISTS_TESTED | 05 onward, 16 |
| G34 | missing provider gives degraded report, not blank or fake | modules record unknowns | PARTIAL | 13, 14 |
| G35 | paper-profitable strategy negative after exit costs | none | MISSING | 10, 11, 12 |
| G36-G41 | Maxun/crawler chronology, dedup, spoof, reliability, webhook, adoption | catalyst firecrawl refused hosts, robots, hashes | PARTIAL | 06A, 09, 16 |

Counts: EXISTS_TESTED 3, PARTIAL 22, MISSING 11 (of 36 rows incl. the G36-G41 group). No row is BLOCKED at the design level; some data needed to make rows live is BLOCKED (see DATA_FEASIBILITY.md).
