# Target registry v1 (pre-registered)

Frozen before any price-path or outcome data was read. Machine-readable copy: `memelab/predictive/contract.py` (`TARGETS`, `ACCEPTANCE`). Pre-registered fingerprint `registry_sha256()` = `dd3b4576aa1e408052dd227e361aa2cbf4b38450994c3b5e6a2be5dc199fbccd`, committed in `b6f2621` at 2026-10-24T01:35:23Z. The GeckoTerminal coverage probe ran after that commit (first call 01:36:23Z) and reports coverage only.

Change control CC-01 (PI-D-019), made in this phase's own adversarial pass before any label existed: the first rule let a candle that closed between the decision and the entry (or closed too recently to have been served) decide eligibility, a look-ahead in sample selection. The reference candle must now be available at the decision. Thinning runs after eligibility, and theses of one mint that share a decision time count once. Fingerprint after CC-01: `9f8c9debdb66b28ab5d758c29d67f46f287965aa0d0bf2c1a64a94f9733d9912`. Recomputed offline on the saved sample, the coverage counts did not change (`probes/gt_coverage_cc01.json`). 

Change control CC-02 (PI-D-021, repair pass 2 after the independent skeptic, still before any label existed) fixed three definitional faults and moved the whole acceptance plan into the fingerprint: (1) the decision unit is an exact thesis row, identity `(mint, created_at, row_sha256)`, and its decision time is the first export holding that exact row, because one key can hold several different rows and a row can first appear in a later export than its key (skeptic counterexample CX-S1: a REJECTED, fatal-flagged row exported 26.7 min after its key); (2) every acceptance rule later phases could loosen is in `ACCEPTANCE` (ACCEPTANCE_METRICS.md); (3) a missing reference candle is classified as MARKET_INACTIVE only with evidence available at the decision, otherwise as VENDOR_OR_ROUTE_GAP, which is censored and counted, never dropped. It also corrected the liquidity follow-up count and froze the list of holdout decisions whose price data was already fetched. Fingerprint after CC-02: `91d03c769dde1d8cbba0f6a40257e7e3c060544ddb2f2b6b8a17556554b5a81a`. Event counts per split did not change (`probes/split_counts.json`). `tests/test_predictive_contract.py` pins the fingerprint, so any further edit to a target or an acceptance rule fails the suite until it is recorded as change control in DECISIONS.md.

Change control CC-03 (PI-D-040, Phase 06, before any label was computed): an absence of candles (NO_TRADES_AFTER_ENTRY, TRADING_HALT) counts only with evidence that the read saw the whole span, an empty or short page alone never does (PI-D-039); the T2 halt's other pools are the first three other pools of the vendor's current list, each with that evidence; a candle is in the halt span when it overlaps it; every target of one decision comes from one read. Fingerprint after CC-03: `4b4aabce77a5a6f9214c4cfdddf5223f410ed6126410cf4b213b3c80b035f896`. Labels: `audits/predictive-intelligence/phase_06/labels/TARGET_SCHEMA.md`.

Where this document and the code differ, the code is the registry and this document is wrong.

## What the data allow (feasibility, from real timestamped records)

| Source | What it gives | Evidence |
|---|---|---|
| 89 state exports on `main` (2026-10-07 to 10-23) | 1,801 thesis snapshots, 248 mints (201 Solana, 47 EVM); after thinning, 252 matured 24 h, 359 matured 6 h and 136 matured 7 d Solana decisions | `probes/decision_universe_probe.py`, output `probes/decision_universe_summary.json` (sha256 `4d2a8df5...`) |
| Export commit times | time by which the exact thesis row existed (the row is inside the commit; committer clock): commit minus `created_at` p50 11.6 min, p90 28.7 min, max 1,325.5 min; never before `created_at`, never before the token's `first_seen_at`. Public availability: a GitHub push event lands 1 to 5 s after the commit for 82 of 89 exports; GitHub `/activity` shows the 3 newest (10-21 to 10-23) pushed 2 s after commit; the other 4 (`996190ce`, `2c6cbf54`, `53a616e1`, `fe8fc3bb`) were already the branch tip on GitHub 886 s, 413 s, 3,609 s and 6,269 s after their commit times (the push that created them is missing from the event feed), so their public availability is bounded only by those times. All 206 main pushes in the feed (2026-10-07T14:08Z to 10-20T10:24Z) are fast-forwards | same probe; `push_events.json` from 3 unauthenticated GitHub REST calls (sha256 `7dd8c46f...`, kept outside the repo) |
| Point-in-time pool address | `primary_pool` or `graduated_pool` in the token row of the first export holding the thesis: 132 of 201 Solana mints; 163 of 252 matured 24 h decisions | same probe |
| GeckoTerminal OHLCV (free, about 10 calls a minute) | 5-minute candles reach back to at least 2026-10-07 decisions (17 days); sample of 10 seeded decisions: 5 OK, 4 with no trade in the hour before entry, 1 HTTP 429 (on the 6th call at about 9 a minute); re-reading one series 101 s later changed 0 of 1,000 candles | `probes/gt_coverage_probe.py`, `probes/gt_coverage_sample.json` (sha256 `b4c96925...`) |
| Historical executable depth | none after 2026-10-08: quotes and pool snapshots are not exported; each thesis carries one `exit_cap_3pct` at its own time | Phase 00 DATA_COVERAGE.md; state.py TABLES |
| Liquidity at decision and 20 to 28 h later | 29 of 278 thinned 24 h decision events (the first version counted 53 of 351 thesis rows; skeptic M5), all from tokens the scheduled runs kept analysing, a selected subset | `probes/split_counts.py` |
| Launch cohort | 1,422 launches first seen inside one 22 h window (2026-10-08T13:45Z to 10-09T11:57Z) | same probe |
| Catalyst, holder, wallet history | not exported; each scheduled session starts empty | state.py TABLES |

Coverage sample by eligibility class (CC-02 rule, recomputed offline from the saved bodies with each decision's own thesis snapshot, `probes/gt_coverage_f3.json`; n is tiny, so these are signs, not rates): ELIGIBLE 5, MARKET_INACTIVE 3 (snapshot 24 h volume $0, $0.34 and $3.22), VENDOR_OR_ROUTE_GAP 1 (`CqjaL6...`, a vendor-list pool with no candle that day while the lab recorded $94,115 of 24 h volume), not read 1 (HTTP 429, retried in Phase 06). A pool chosen from today's vendor list is often not the pool that traded at the decision, and it conditions on which pools survived. Phase 06 reports every class by route and status and stratifies every result by route.

## Common definitions (all primary targets)

| Item | Rule |
|---|---|
| Scope | Solana, exact mint (`{chain, mint}`); EVM decisions abstain with `OUT_OF_SCOPE_CHAIN` in v1 |
| Unit | one decision event (`memelab/predictive/decisions.py`): a candidate is one exact thesis row, identity `(mint, created_at, row_sha256)` with `row_sha256` over the row without `id`. At each export commit where a row of the mint first becomes visible, the decision row is the newest visible row (largest `created_at`; ties by earliest first-visible export, then position in that export). A decision event exists when the decision row changes. KEY_CONFLICT flags a chosen `created_at` whose visible rows differ in status, score, fatal flags or price (4 of 278 thinned 24 h events); every result is repeated without them |
| Decision time, historical | commit time of the first `data/state/latest.json` commit on `main` (first-parent history) that contains the exact decision row (`decision_time_basis` EXPORT_COMMIT). A row that first appears in a later export gets that later time, never its key's earlier one (CC-02, PI-D-021; amends PI-D-015) |
| Decision time, prospective | capture time recorded when the forecast request is created (`CAPTURE_TIME`) |
| Never a decision time | `theses.created_at` or any other `t`-stamped column (PI-D-011) |
| Entry time | `t_entry` = decision time + 300 s (execution lag of outcomes_core DEFAULT_POLICY) |
| Eligibility | every thesis status counts, REJECTED and fatal-flagged included; snapshot price present; class ELIGIBLE (below). Then thinning: per mint the first eligible decision, then each next eligible decision at least one horizon after the previous kept one (non-overlapping label windows; repeated updates inside a window are the same event, P35) |
| Reference pool | `primary_pool` or `graduated_pool` of the token row in the export where the decision row first appears (PIT_RECORDED); else the vendor's current top pool for the mint at label time (CURRENT_VENDOR_LIST, flagged, stratified, survivorship risk) |
| Price source | GeckoTerminal public OHLCV of the reference pool, minute timeframe aggregate 5, currency usd, empty intervals omitted (an omitted interval means no trade, so no barrier can be crossed in it) |
| Reference price P0 | close of the newest 5-minute candle available at the decision: candle end + 300 s provider lag (replay_sources.PROVIDER_LAG, HEURISTIC) at or before the decision time, and candle end no earlier than decision time - 3600 s (`contract.reference_candle`). At forecast time the same rule runs on one paced read at capture |
| Eligibility class (`contract.eligibility`) | ELIGIBLE: a reference candle exists. MARKET_INACTIVE: no reference candle, and either the thesis snapshot's own 24 h volume (as of the thesis, so available at the decision) is below $1,000, or the route is PIT_RECORDED and the vendor shows a candle on that pool in the 24 h before the decision (a quiet hour on the lab's own pool); not labeled, counted, and at forecast time the abstain reason NO_RECENT_PRICE. VENDOR_OR_ROUTE_GAP: no pool resolved, the vendor read failed after retries (HTTP 429 is retried, never a class), or no reference candle without that evidence; censored and counted (below), and at forecast time SOURCE_STALE. A backfill read cannot by itself prove that a market was quiet (P04, P07) |
| Gap | candles between the reference candle and `t_entry` are neither reference nor path |
| Path | 5-minute candles that start at or after `t_entry` and end at or before `t_entry` + horizon (`contract.path_candles`). The candle holding `t_entry` is never used (no same-candle entry, P06) |
| Timestamps kept per label | decision time and basis, export commit, `t_entry`, P0 candle start, first touch candle start, `label_matures_at`, `label_observed_at` (retrieval time of the candles, never a claim of historical availability, P04, P07), reference pool and route, request URL and body sha256 |
| First availability | a label exists only from `label_observed_at`, which must be at or after `label_matures_at` = `t_entry` + horizon + confirmation window + 900 s |
| Pending | before `label_matures_at` the label is PENDING: never trained on, never scored, never counted negative (P05) |
| Censored | VENDOR_OR_ROUTE_GAP (above), and UNVERIFIABLE_NO_VENDOR_HISTORY: a reference candle was found but a later read needed for the label window fails after retries. Both are excluded from scoring, counted in coverage by route and status, and shown beside a conservative lens that counts them T1 negative and T2 positive (a pool the vendor stopped serving may be a rug) |
| Position size | none. These are price-path targets: `position_usd` is null and every forecast carries `PRICE_PATH_NOT_PROCEEDS` and `NO_HISTORICAL_EXECUTABLE_DEPTH` (P08, P44). The thesis's own `exit_cap_3pct` at decision may be shown beside the forecast as stale context only |
| Naming | every target name starts with `price_path_`; the words "profit", "return", "exit" or "executable" never appear in a primary target name or its display text |

## Primary targets

### T1 `price_path_target_before_invalidation_24h` (version 1)

| Item | Rule |
|---|---|
| Question | from P0, does the 5-minute price path touch +25% before it touches -15% within 24 h after `t_entry`? |
| Barriers | upper U = 1.25 x P0 (candle high >= U); lower L = 0.85 x P0 (candle low <= L) |
| Classes | positive: TARGET_FIRST. Negative: INVALIDATION_FIRST, AMBIGUOUS_BAR, NEITHER (no touch by `t_entry` + 24 h), NO_TRADES_AFTER_ENTRY |
| Tie inside one candle | a candle whose high >= U and low <= L is AMBIGUOUS_BAR, counted negative (conservative). No 1-minute refinement in v1. If AMBIGUOUS_BAR exceeds 10% of labeled events, Phase 06 reports the opposite resolution as a sensitivity, never as the label |
| Dead, rugged, unquoted | no candle after entry: NO_TRADES_AFTER_ENTRY (negative). A crash shows as a low <= L: INVALIDATION_FIRST. Pool gone from the vendor: censored as above (P09, P37) |
| Maturity | `t_entry` + 24 h + 900 s |

### T1b `price_path_target_before_invalidation_6h` (version 1)

Same as T1 with a 6 h horizon (maturity `t_entry` + 6 h + 900 s) and 6 h thinning. Counted as a separate primary outcome for multiple-testing purposes.

### T2 `price_path_severe_drawdown_or_halt_24h` (version 1)

| Item | Rule |
|---|---|
| Question | within 24 h after `t_entry`, does the price path fall to half of P0, or does trading stop and stay stopped? |
| Positive | DRAWDOWN_50: some path candle has low <= 0.5 x P0. TRADING_HALT: no candle on the reference pool from `t_entry` + 18 h to `t_entry` + 48 h, and none on up to 3 other vendor-listed pools of the mint in the same span |
| Negative | NO_SEVERE_EVENT |
| Tie rule | not needed (one barrier); when both a drawdown touch and a halt occur, the class is DRAWDOWN_50 and the halt is kept as a flag |
| Dead, rugged, unquoted | a rug shows as DRAWDOWN_50 or TRADING_HALT (positive). Pool gone from the vendor: censored, with the conservative lens counting it positive |
| Maturity | `t_entry` + 24 h + 24 h halt confirmation + 900 s; a T2 label read at 30 h is PENDING (P05) |

## Registered but not primary

| Name | Status | Why | What would change it |
|---|---|---|---|
| `exit_adjusted_target_before_invalidation_24h` | BLOCKED_NO_HISTORICAL_DEPTH | needs sell quotes at a stated size at entry and at the barrier times; none kept after 2026-10-08; one `exit_cap_3pct` per thesis is not a path (P08) | forward collection of quotes at entry and on a fixed grid, which needs a scheduled job (Elving's approval) |
| `liquidity_degradation_24h` | DEFERRED_FORWARD_COLLECTION | needs reserves or quotes at decision and decision + 24 h for every decision; snapshots give 29 of 278 thinned events, a watchlist-selected subset (missing not at random) | the same forward collector |
| `failed_breakout_6h` | DEFERRED_PHASE_08 | eligibility needs the m14 class as of the decision; not exported, must be recomputed on backfilled candles with a pinned code SHA | Phase 08 shows the recomputation is as-of correct |
| `catalyst_followthrough_24h_7d` | BLOCKED_NO_DATA | catalyst tables are not exported; every scheduled session starts empty | catalyst export plus months of history |
| `distribution_event_24h` | BLOCKED_NO_DATA | holders and wallet transactions are not exported after 2026-10-07 | holder snapshots kept per decision |
| `price_path_target_before_invalidation_7d` | EXPLORATORY | 213 thinned decisions, 75 in development, 0 matured in the holdout window yet | reported as description only |
| `launch_cohort_collapse_24h` | EXPLORATORY | 1,422 launches first seen inside one 22 h window: no temporal out-of-sample split exists | launches collected over several weeks |

## Known measurement limits (carried into every report of these targets)

| Limit | Consequence | Handling |
|---|---|---|
| Price path, not proceeds | a touch of +25% on a thin pool can be one small trade (P08, P25, P44) | caveat on every forecast; Phase 06 reports the share of touches made by candles under $500 USD volume |
| Vendor pool route | a pool picked from today's vendor list conditions on which pools survived (P02, P09) | flagged CURRENT_VENDOR_LIST, every result stratified by route |
| Provider lag | 300 s after candle close is HEURISTIC (replay_sources.PROVIDER_LAG) | features and the reference candle use it; Phase 05 records it as HEURISTIC |
| Backfill is not history | a candle read today proves today's vendor answer, not what was served then (P04, P07) | `label_observed_at` = retrieval time; Phase 06 re-reads at least 10% of series at least 48 h apart and treats any change to a candle older than 48 h as a revision (new ledger observation, label recomputed and flagged) |
| Retention | how long GeckoTerminal keeps 5-minute candles is UNKNOWN; at least 17 days observed | backfill early in Phase 06; decisions whose window is no longer served are VENDOR_OR_ROUTE_GAP or UNVERIFIABLE_NO_VENDOR_HISTORY, censored and counted |
| Decision staleness | the snapshot behind a historical decision is up to 22 h older than its export commit (commit minus `created_at` p90 28.7 min, max 1,325.5 min) | reported as a stratum; prospective capture is about 17 min after `created_at` (PI-D-011), so training and serving differ slightly and Phase 19 compares them |
| Empty intervals | GeckoTerminal omits intervals without trades | an omitted interval cannot hold a barrier touch; long gaps are reported as SPARSE_PATH (largest gap over 2 h) |
| Rate limit | HTTP 429 seen at about 9 calls a minute | at most 6 a minute with backoff (ACCEPTANCE_METRICS.md) |

## Event counts per split (before eligibility; counts only)

From `probes/split_counts.py` (output `probes/split_counts.json`, sha256 `0a6074e3...`, now built with the CC-02 decision rule; the counts are identical to the first version): thinned Solana decision events with a priced snapshot, split by the pre-registered holdout window [2026-10-17T00:00Z, 2026-10-24T00:00Z). Purged = the label would mature inside the holdout window.

| Target | Development | Purged | Retrospective holdout (matured by 2026-10-23T10:20Z) | Not yet matured |
|---|---:|---:|---:|---:|
| T1 24 h | 177 | 17 | 58 | 26 |
| T1b 6 h | 280 | 0 | 79 | 7 |
| T2 24 h | 161 | 33 | 49 | 35 |
| 7 d (exploratory) | 75 | 61 | 0 | 77 |

The holdout column includes the two decisions whose price data was fetched in Phase 01 (one each for every target); they are excluded from the primary retrospective holdout (ACCEPTANCE_METRICS.md "Holdout contact").

Eligibility (class ELIGIBLE) will remove more, and MARKET_INACTIVE and VENDOR_OR_ROUTE_GAP are counted beside every result; the coverage sample suggests a large share, so the retrospective holdout is expected to land near or below the 50-event minimum (ACCEPTANCE_METRICS.md). That is a stated expectation, not a result.
