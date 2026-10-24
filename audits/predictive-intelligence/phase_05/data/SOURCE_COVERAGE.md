# Source coverage (Phase 05)

What the point-in-time store holds, from which source, with which clock, and what is missing. Counts come from the real store built in this phase (`/home/claude/pi_research/p05/predictive_store.sqlite`) through `probes/coverage_counts.py` (output `evidence/coverage_counts.json`) and `probes/build_store.py summary` (output `evidence/store_summary.json`). Ref of the exports: `98338a8` (origin/main as read by Phases 01 and 04). Synthetic data appear only in tests.

## Source matrix

| Source | Ingested | Historical coverage | Chain and venue | Availability (basis) | Terms and rights | Known missingness |
|---|---|---|---|---|---|---|
| State exports `data/state/latest.json` on main (git history, first parent) | yes: 89 versions, 1,500 decision events of 247 mints (one more event refused, below) | decisions 2026-10-07T21:53Z to 2026-10-23T10:20Z | Solana 925 events, BSC 318, Base 225, Ethereum 32; point-in-time pool from the token row (`graduated_pool` for all 603 Solana events that have one; `primary_pool` never set for Solana) | export commit time of the first version holding the exact row (FACT; PI-D-015, PI-D-021) | the lab's own research output, already public in this repository | theses capped at 12 per mint per export (older rows survive in git history); snapshot fields NULL when a module had no input; one time per thesis (PI-D-011); scores version-dependent (PI-D-008); 57 events carry KEY_CONFLICT |
| GeckoTerminal public OHLCV, 5-minute, `currency=usd` | yes, development-period Solana decisions with a point-in-time pool only (541 events, 96 pools) | candles 2026-08-25T19:35Z to 2026-10-16T10:40Z over 94 pools; how far back the vendor's history goes is not established (a short or empty page bounds nothing, skeptic m2), so coverage starts at the earliest candle read | Solana; DEX not recorded per pool (OHLCV bodies carry base and quote only; launchpads of the Solana decision tokens: pump.fun 482 events, none recorded 257, met-dbc 67, ember 61, stonkfun 51, others 4) | candle end plus 300 s (`replay_sources.PROVIDER_LAG`, HEURISTIC reconstruction); retrieval time kept apart; capture mode uses the retrieval time | free public API; the OpenAPI spec's rate text ("approximately 10 calls/minute") read in Phase 00; redistribution terms not reviewed: bodies are committed under `raw/` as research evidence, as the orchestrator allowed | omitted intervals mean no trade; retention UNKNOWN beyond the observed range; 2 pools served nothing (NO_DATA); 9 pools have the mint as quote token, so a read without `token=<mint>` priced another token (refused, re-read with `token=<mint>`); a candle's open (and with it high or low) depends on the request window |
| Collector files `inbox/*.json` (GeckoTerminal projections, 2026-10-06 to 10-08) | no; used only for the vendor revision comparison | 2026-10-06 to 2026-10-08 | Solana, 33 pools (9 of them development pools, 15-minute) | collector run start `_at` (a lower bound of the read) | lab's own collector output, public in this repository | projections drop the vendor's meta, so a read's priced token is verifiable only where its plan (request URL) is in the repository (2 of 12 files) |
| Tracked `data/memelab.sqlite` | no | 2026-10-06/07 only, 33 theses | Solana | no export commit: no decision time under PI-D-015 | lab's own | predates every export; not a point-in-time decision source |
| DEX Screener | no | current state only | multi-chain | a current quote is present-day evidence, never a historical observation | free public API | no history at all (DATA_COVERAGE.md) |
| Live read at capture (prospective inference, Phase 17) | not in Phase 05 | from the capture | Solana | the read's retrieval time (CAPTURE basis) | as GeckoTerminal above | one paced read per request (ACCEPTANCE latency row) |
| Catalyst, social, holders, wallet transactions, quotes, pool snapshots | no | not exported after each scheduled session | | | social content never enters this store | BLOCKED_NO_DATA for v1 (TARGET_REGISTRY not-primary table) |

## Decisions by split and fetch scope

| Split (Solana) | Events |
|---|---:|
| Development for the 6 h target (decision before 2026-10-17T00:00Z, label maturity at or before it) | 830 |
| Retrospective holdout [2026-10-17, 2026-10-24) | 95 |
| Prospective (from 2026-10-24) | 0 at ref `98338a8` |

| Fetch scope (all chains) | Events | Candle features |
|---|---:|---|
| DEVELOPMENT (Solana, point-in-time pool, development period) | 541 | read from the vendor |
| NOT_FETCHED_SEALED (Solana, point-in-time pool, holdout or purged) | 62 | MISSING NOT_FETCHED_SEALED (RETRIEVAL) |
| NO_POOL_AT_DECISION (Solana without a point-in-time pool) | 322 | MISSING NO_POOL_AT_DECISION (AS_OF) |
| OUT_OF_SCOPE_CHAIN (EVM) | 575 | MISSING OUT_OF_SCOPE_CHAIN (AS_OF) |

Refused at ingestion: one export row of mint `MukLDtJ8Cx9DxLbeyLRWPSposTMWuwHANbuaudpump` (export commit 2026-10-10T01:34:29Z), a base58 string that decodes to 31 bytes, so it is not a Solana address (PI-D-022). It is counted, not stored.

Development decisions with a 1 h return: 535 of 541; 2 VENDOR_NO_DATA (the two pools the vendor served nothing for in the requested window, P09), 4 OUTSIDE_FETCHED_WINDOW (the window starts before the earliest candle read). The first pass assumed that a page shorter than the limit proved no earlier trade; the repair (feature version 2) changed 102 values of 16 decisions to OUTSIDE_FETCHED_WINDOW (RETRIEVAL): 66 that were BEFORE_FIRST_CANDLE (HEURISTIC) and 36 that were numbers, among them the 3 BEFORE_FIRST_CANDLE values and the 2 numbers (24 h volume and candle count) of the `BvkPHKx2...` decision of 2026-10-15T10:13Z that the skeptic found.

## Vendor reads

| Item | Count |
|---|---:|
| GeckoTerminal calls in Phase 05 | 155 by the phase: 147 to the store (127 first run, 9 `token=<mint>` re-reads, 11 re-read sample) plus 8 for the inbox comparison; 4 more by the independent skeptic (11:55Z to 11:57Z) |
| HTTP status of the store's reads | 132 answered 200, 15 answered 429 (each retried after 60 s) |
| Most calls in any 60 s window (all 155) | 6 |
| Identity check of the 132 bodies | OK_BASE 114, OK_TOKEN_PARAM 9, MINT_IS_QUOTE 9 (refused) |
| Candles kept | 74,541 versions on 94 pools; 8,212 refused (the 9 quote-side bodies); 98 dropped because they end after the request boundary |
| Series | 115: 96 planned (85 OK, 9 IDENTITY_MISMATCH, 2 NO_DATA), 9 `token=<mint>` re-reads (OK), 10 re-reads (OK); `cover_complete` 0 for all (repair m2) |
| Raw bodies committed | 147 files, 3.4 MB gzip under `raw/`, with `raw/MANIFEST.csv` (file and body sha256, request, retrieval time, status, pool, mint, boundary, identity check, parameters) |

## Vendor revisions (P07)

| Comparison | Gap | Result |
|---|---|---|
| Phase 04 bodies (read 2026-10-24 from 08:02Z) against the Phase 05 first read of 84 pools (`evidence/revision_check_p04.json`) | 2.5 h (8,990 to 9,435 s) | 57,584 candle positions in both: 57,504 identical, 80 differ only in the open (36), open and low (23) or open and high (21); 0 differ in close or volume; none appeared or vanished. The open of the earliest candle of a response is computed from the request window, so the store records such a difference as an OPEN_WINDOW revision and the features use closes and volumes only |
| Re-read of 10 series with the first run's exact requests (`evidence/revision_check_store.json`) | 19 to 51 min | 7,223 candles re-read unchanged; 0 changed, appeared or vanished |
| Inbox 15-minute reads from 2026-10-06/07 with a recorded request URL against one re-read on 2026-10-24 (`evidence/revision_check_inbox15_verified.json`) | about 17 days | 3 pools: 198 of 199 candles unchanged and 1 OPEN_WINDOW each. 1 pool (`Cprsvqk2...`, mint DARK, quote wNEAR): every one of 199 candles differs, closes by a median factor of 3,325 while volumes agree within 0.15%: the 2026-10-06 read without a token parameter priced the other token, although the vendor's meta now lists the mint as base. A read without `token=<mint>` cannot be checked after the fact |
| First pass of the inbox comparison (`evidence/revision_check_inbox15.json`) | | superseded: it assumed every inbox read had asked for `token=<mint>`, which the recorded plans contradict; kept for its call log |

Not measured here: revisions after 48 h or more between the lab's own reads of the same request (PI-D-018 requires at least 10% of label series re-read 48 h or more later; that is Phase 06's).

## Missingness in the stored snapshots (3,000 = 1,500 decisions in two modes)

Provider mode, values and reasons by group (32 features per snapshot):

| Group | Values | Missing (reason: count) |
|---|---:|---|
| thesis (15) | 19,121 | ABSENT_IN_SNAPSHOT 3,379 |
| token (1) | 910 | ABSENT_IN_SNAPSHOT 590 |
| history (3) | 3,549 | NO_PRIOR_DECISION 494, ABSENT_IN_SNAPSHOT 457 |
| universe (2) | 3,000 | none |
| candle (10) | 5,288 | OUT_OF_SCOPE_CHAIN 5,750; NO_POOL_AT_DECISION 3,220; NOT_FETCHED_SEALED 620; OUTSIDE_FETCHED_WINDOW 102; VENDOR_NO_DATA 20 |
| cross (1) | 519 | OUT_OF_SCOPE_CHAIN 575; NO_POOL_AT_DECISION 322; NOT_FETCHED_SEALED 62; ABSENT_IN_SNAPSHOT 20; VENDOR_NO_DATA 2 |

Capture mode: every candle and cross value of a historical decision is MISSING NOT_RETRIEVED_BY_DECISION (6,633 values), because every vendor read in this phase happened after every decision; the decision-row, token, history and universe values equal the provider mode's.

## Gaps that stay open

- DEX type per pool is not recorded; adding it needs a pool-info read per pool (Phase 09 or later).
- The holdout's and the purged decisions' candles are not read in Phase 05 (seal); Phase 06 reads them under its own seal.
- Historical executable depth does not exist for past times (P08); `thesis_log1p_exit_cap_3pct_usd` is the only depth-like value, as of the thesis.
