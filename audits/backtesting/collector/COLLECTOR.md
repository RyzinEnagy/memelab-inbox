# Forward depth collector (D-BT-034, repair D-BT-035)

Work record for the collector Elving approved on 2026-10-25 (predictive PI-D-020, now PI-D-044), folded into the hourly shadow tracker. Branch `work/backtesting-collector`, based on feature/backtesting at 054a619. Operator text: docs/backtesting/RUNBOOK.md, "Forward depth collection". The independent review is in COLLECTOR_SKEPTIC.md (copied verbatim) with its probes in skeptic_probes/; the repair is recorded below.

## What the tracker already recorded

- `refresh` (outcomes.refresh): new hourly OHLCV bars, and an OHLCV_FETCHED observation, for the basis pool of each outcome window that waits on a refresh. Bars only: no reserves, no quotes.
- `track` (outcomes.track): outcome windows of 1, 6, 24 and 72 h for the frozen opportunities in bt_universe_members and the stored assessments. The universe was built from the exports up to the corpus build; no command imports newer lab records (RUNBOOK, "Backfills").
- Reserves: only POOL_RESERVE_USD_PRESENT observations written when the corpus listed a mint's pools (gecko.fetch_pools): USD only, once per corpus build, not on a grid, not in token units.
- Quotes: none stored. Assessments can price a fill from a router quote seen at the decision (QUOTE_OBSERVED), but the module never kept quotes for later.

Missing for PI-D-020: for every decision, reserves and sell quotes at fixed sizes after the decision and on a grid to 24 h, keyed by chain, exact mint and pool.

## What was added

- `memelab/backtest/depth.py`: decisions from the exports (reuses sources/labstate.py and timeguard.utc_ts), pool lookups, pool reads and quotes (reuses gecko.Budget for counts and spacing, gecko.BASE and default_http_get, and the raw store by sha256), status. The read itself (one call, at most one retry, never raising) is in depth.py since the repair pass, because gecko.get_json raises BudgetExhausted on a retry at the cap (skeptic M1).
- `gecko.get_json` gained a `provider` argument (default unchanged).
- Schema migration 2: `bt_depth_decisions`, `bt_depth_pool_lookups`, `bt_depth_snapshots`, append-only, rollback to 1. Migration 1 and its checksum are unchanged. Migration 2 has never been applied outside scratch databases, so the repair pass changed it in place.
- CLI: `python -m memelab backtest depth collect|status`.
- `audits/backtesting/release/hourly_shadow.sh`: step `collect` between refresh and track, on the work copy only; it passes the refresh step's GeckoTerminal call count and end time to collect.
- Tests: tests/test_backtest_depth.py (28), fixtures tests/fixtures/backtest/depth/ (recorded smoke bodies; the quote-side pool, the no-route, 401, 429, 5xx and timeout answers are built in the test file). tests/test_backtest_timeguard.py expects migrations [1, 2].

## Quote source

- Jupiter's migration and plans pages, read 2026-10-25 with WebFetch: keyless requests on `api.jup.ag` at 0.5 requests a second (30 a minute), "great for AI agent or test use cases"; `lite-api.jup.ag` "will be phased out" with a rate limit "reduced progressively". The free plan with a key is 1 a second; no key is used.
- Probe from this workspace, 2026-10-25 13:11Z: SOL to USDC (`EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`) returned HTTP 200 on both `api.jup.ag/swap/v1/quote` and `lite-api.jup.ag/swap/v1/quote`, headers `x-ratelimit-remaining: 4`. The earlier TOKEN_NOT_TRADABLE was not reproduced with this USDC mint.
- Result: quotes are available free and within the documented keyless use, so QUOTE_SOURCE_BLOCKED was not needed. It stays as a run status for the day keyless access ends.
- GeckoTerminal's multi-pool endpoint with `include_composition=true` returns `base_token_balance` and `quote_token_balance` (reserves in token units) besides `reserve_in_usd`.

## Live calls made in this work

| What | GeckoTerminal | Jupiter | GitHub |
|---|---|---|---|
| probes (multi-pool 1, token multi 2, SOL to USDC quotes 2) | 3 | 2 | 1 ls-remote, 1 shallow fetch |
| development run, 13:19Z (found the raw folder fault) | 4 | 6 | 1 shallow fetch |
| smoke, 13:22Z (smoke/) | 4 | 6 | 1 shallow fetch |
| live full-size run in the repair pass, 14:13Z (live_repair_run/) | 6 | 40 | 1 shallow fetch |
| total | 17 | 54 | 5 |

The repair pass's tests are offline. One live run happened by mistake: during the local run of hourly_shadow.sh at c7c8dd4, the network was blocked for refresh, collect, track and save, and then one more `collect` was typed without the proxy variables. It ran the full collector against the live exports (free endpoints, inside the caps and pacing) and is kept as evidence below; it changed the price check. The smoke rows in smoke/ were made by the first-pass code; their columns are the same except that the decision row then held the vendor's top pool directly (now a lookup row) and quotes carried no price source.

## Smoke, 2026-10-25 13:22Z (first-pass code)

Command: `python -m memelab backtest depth collect --repo LAB_GIT --db SCRATCH/bt.sqlite --max-gt-calls 4 --max-quote-calls 6`, exit 0, 42.2 s. LAB_GIT is a shallow fetch of `main` since 72 h before: exports 98338a8 (baseline), efdaee9 and e245d91 (2026-10-25T10:10:02Z).

- 19 decisions, all from e245d91: 16 Solana, 2 BSC, 1 Base. Pools: 11 EXPORT_GRADUATED_POOL, 3 EXPORT_PRIMARY_POOL, 5 VENDOR_TOP_POOL (one token-endpoint call).
- 19 pool snapshots OK (3 multi-pool calls: Solana 16 pools, BSC 2, Base 1), 3 QUOTE_UNSUPPORTED_CHAIN rows.
- 6 quotes OK, the cap; 42 quotes not attempted (the first-pass code counted them in the summary only; the repaired code writes a row for each).

| Mint | Size USD | Tokens sold | USDC out | Out / size | priceImpactPct |
|---|---|---|---|---|---|
| 7M3gDRgo...pump | 100 | 41,635.11 | 99.96 | 0.9996 | 0.0015 |
| 7M3gDRgo...pump | 500 | 208,175.56 | 497.88 | 0.9958 | 0.0054 |
| 7M3gDRgo...pump | 2,000 | 832,702.26 | 1,980.46 | 0.9902 | 0.0109 |
| 9aqmJjCn...qjj | 100 | 278,932.04 | 99.54 | 0.9954 | 0.0052 |
| 9aqmJjCn...qjj | 500 | 1,394,660.21 | 493.20 | 0.9864 | 0.0142 |
| 9aqmJjCn...qjj | 2,000 | 5,578,640.82 | 1,904.60 | 0.9523 | 0.0483 |

- swapUsdValue was within 0.1% of the size on all six (the price check of the repair would have passed them).
- Lag from the export commit to the first snapshot: 11,545 s, because the smoke ran 3.2 h after the export. In hourly operation the first snapshot comes at the first run after the export, up to about an hour later.
- Files: smoke/collect.json, smoke/status.json, smoke/decisions.csv, smoke/snapshots.csv (one line per row: URL, captured_at, HTTP status, raw sha256, values), smoke/raw/ (the 10 bodies; each file name is its sha256), smoke/dev_run_collect.json (the development run's summary).

## Repair pass after the independent skeptic (D-BT-035)

Each finding was reproduced on the first-pass code before the change (skeptic_probes/: probe_429.py gave `BudgetExhausted` for Jupiter at cap 4 and for GeckoTerminal at cap 6; sim_cap.py gave 13 of 16 pools quoted every hour, the missing three always export positions 13, 14 and 15; probe_cx.py gave three OK quotes with proceeds ratio 0.500, 0.498 and 0.495).

| Finding | Change | Caught by |
|---|---|---|
| M1 a 429, 5xx or timeout on the last budgeted call crashed collect | `_Run.get` makes one call and at most one retry, never raises; the retry is skipped when the cap or the deadline would be passed (`retry_refused` cap or deadline in the row); every attempt's status, time and body hash are kept (`attempts`) | test_failure_on_the_last_budgeted_quote_ends_cleanly and ..._pool_read_ends_cleanly (429, 5xx, timeout), test_one_retry_is_made_and_both_bodies_kept; MR-1, MR-2, MR-3, MR-14 |
| M2 refresh plus collect over 6 GeckoTerminal calls a minute | collect makes no GeckoTerminal call while the last 60 s hold 6 or more, counting the refresh step's calls (the script passes their count and the time refresh.json was written; all are counted at that time, which is no earlier than any of them); plus 10 s between collect's own calls. Refresh itself is unchanged: its own burst (12 calls 3 s apart) is Elving's call, see HANDOFF | test_gt_pacing_counts_the_refresh_calls; MR-4, MR-16, MC-9, MC-10 |
| M3 first quote not at the decision, and the same export positions skipped every day | quotes are ordered by fewest runs with an answered quote for the pool since its decision (any state, so a pool without a route cannot keep the front), then the one answered longest ago, then a hash of the run and the pool; Jupiter cap 48 at 2.2 s (27 a minute, under the keyless 30); every quote not made gets a row (NOT_ATTEMPTED_CAP, NOT_ATTEMPTED_DEADLINE, SKIPPED_POOL_<state>); docs say the first snapshot is up to about an hour after the export and is a post-decision observation | test_quote_order_rotates_and_prefers_unquoted_pools, test_every_pool_gets_its_turn_including_pools_without_a_route, test_call_caps_leave_rows_that_say_so; MR-5, MR-6, MR-7, MR-18, MR-19 |
| M4 counterexample: a stale pool price reads as a 50% exit haircut | the token amount still comes from this run's pool read; the price, its field, its pool, its read time and its body hash are stored with the quote; a quote whose implied price (out_usd / ((1 - priceImpactPct) x tokens sold)) is outside 0.9 to 1.1 of that pool price is PRICE_DISAGREES (price_check DISAGREES), not OK. Not the review's proposed swapUsdValue / size: the live run showed swapUsdValue values the output and falls with real impact | test_counterexample_stale_pool_price_is_flagged (the skeptic's case: three rows PRICE_DISAGREES, ratio 0.50), test_real_price_impact_is_not_a_price_disagreement; MR-8, MR-9, MR-17 |
| minor 1 step could run about 220 s | git fetch stopped at 20 s, the program at 140 s; no call or retry starts after 115 s, 10 s per call; worst case about 165 s | test_hourly_script_... (fetch plus program at most 165 s, program at least deadline plus timeout plus 10 s), test_deadline_stops_new_calls_and_bounds_the_run, test_slow_network_ends_by_the_deadline; MR-15 |
| minor 2 no quote row when the pool read failed | SKIPPED_POOL_<state> rows, three per pool | test_collect_pools_quotes_and_provenance (X, P); MR-6 |
| minor 3 ten surviving mutations | quote-side pool, Solana case, future export, missing pool, URL parameters, route and newest-decision tests | S3 to S12 all caught |
| minor 4 failed or empty pool lookups lost | every decision is recorded at first sight (NONE_IN_EXPORT when the export names no pool); each lookup is a row in bt_depth_pool_lookups with state, attempt number, URL and body hash; it is retried each run until OK (NO_POOL too) | test_pool_lookup_failures_are_recorded_and_retried; MR-11, MR-12 |
| minor 5 same-hour rerun duplicated rows and calls | run id is the UTC hour; a second run in that hour returns SKIPPED_SAME_HOUR with no call | test_same_hour_rerun_adds_nothing; MR-10 |
| minor 7 one bad row made the export unreadable | rows are read one by one with utc_ts; an unreadable row is counted (rows_unreadable) and skipped | test_export_decisions_baseline_window_and_pool; MR-13 |
| minor 6 sales sized in USD each hour | kept as is and written for the predictive adapter (RUNBOOK) | not a code change |
| minor 9 release audit rule for audit notes is broad | not changed here: tools/release_audit.py belongs to the release and the rule predates this work; noted in HANDOFF. The audit was rerun with `--history` | c01r_release_audit_history.log |

Simulation (skeptic_probes/sim_cap.py on the repaired code, 16 Solana, 2 BSC, 1 Base pools): with no refresh calls before it, 48 Jupiter calls, 16 of 16 pools quoted, 104 s; after a refresh step of 12 calls, the first GeckoTerminal read waits for the window, 27 Jupiter calls, 9 of 16 pools quoted, 21 NOT_ATTEMPTED_DEADLINE rows; the 7 pools skipped in hour 0 were all quoted in hour 1. An intermediate version that counted only OK quotes let pools without a route keep the front (the same two pools skipped three hours running); that is MR-18.

## Live full-size run in the repair pass, 2026-10-25 14:13Z (live_repair_run/)

Code c7c8dd4 (before the implied-price change), cloud workspace, no refresh calls before it. Exports 98338a8 (baseline), efdaee9, e245d91; 19 decisions, 5 pool lookups OK.

- GeckoTerminal 6 calls (2 retries): 18 pool reads OK, the Base read HTTP_429 after its retry. Jupiter 40 calls: 32 OK, 3 NO_ROUTE (2SESmE4A...), 5 PRICE_DISAGREES under the first repair check, 8 NOT_ATTEMPTED_DEADLINE; 115 s of calls.
- swapUsdValue tracks the output: on the $2,000 sales of 3vZY2MKB... (priceImpactPct 0.203, out/size 0.798) and 43N5UGr3... (0.284, 0.716), swapUsdValue / size was 0.797 and 0.716, so the first repair check flagged real depth as PRICE_DISAGREES. The implied price check gives 1.001 and 1.000 for them.
- PonziBtgw... (export names no pool; the vendor's top pool showed 0 reserve in USD on the first smoke) sold at 0.22 to 0.25 of the size at every size with 6 to 16% stated impact: implied over pool price 0.262. That is the skeptic's counterexample in live data, flagged by both checks.
- recheck_implied_price.json applies the final check to the 37 answered quotes: 34 OK, 3 PRICE_DISAGREES (PonziBtgw... only).
- Files: collect.json, snapshots.csv (with value_json), pool_lookups.csv, raw/ (42 bodies, each named by its sha256).

## Checks

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_backtest_depth.py -q -p no:cacheprovider` | 0 | 31 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/collector_mutations.json` | see c01r_mutations.log | 47 mutations: the 18 of the first pass (texts updated; MC-11 and MC-12 retargeted at the read itself, because the loop's own checks made them equivalent), 19 for the repair, the skeptic's 10 survivors |
| `python -m pytest tests -q -p no:cacheprovider` | see c01r_full_pytest.log | only the known clock test may fail |
| `python tools/release_audit.py --history` | see c01r_release_audit_history.log | |
| `python tools/release_e2e.py --out e2e.md` | see c01r_release_e2e.log | |

First-pass logs: audits/backtesting/testing/logs/c01_*.log. Repair logs: c01r_*.log. Not run: audits/backtesting/testing/p17_doc_claims_check.py, which needs the research database (data/backtest/bt.sqlite), now kept only on Elving's computer; the runbook's depth commands were checked against `python -m memelab backtest depth --help`.

## Limits

- Quotes only on Solana. BSC, Base and Ethereum get reserves only.
- Observations start after the decision: the first one comes at the first hourly run after the export commit, up to about an hour later (since_export_s on every row). Nothing here is a quote at the decision time.
- A quote is Jupiter's route at that moment (any pool), not a fill in the export's pool. The reserves are the export's pool only.
- Sales are sized in USD at each run's price, not as the token quantity held since the decision; proceeds of a held position need interpolation between the three sizes.
- When the refresh step made 6 or more GeckoTerminal calls, collect's first pool read waits up to 60 s and fewer quotes fit before the deadline; the rows say NOT_ATTEMPTED_DEADLINE.
- The refresh step still paces GeckoTerminal at 3 s (D-BT-033); the 6-in-60-s rule is kept for every window that holds a collect call, not inside refresh's own burst.
- Nothing ran on Elving's computer; the timing there is not measured.
