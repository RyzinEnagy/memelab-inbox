# Data coverage (Phase 00 baseline)

What dated real data exists, where, with which clocks, and how far back the free public APIs reach. Measured 2026-10-24 (UTC). Nothing here was bulk-downloaded; the API checks are four single calls. Feeds Phase 01 feasibility.

Sources: the tracked SQLite file (copied to scratch and opened read-only), `git show` of every committed state export on `origin/main` (probe `probes/state_history_probe.py`, exit 0, output sha256 `120d6bb9a9e75455e85f5c000f1924d8432f582fda6e00373f9df4285d14856d`), the tracked collector files, and the provider docs linked below.

## Summary for Phase 01

- The lab holds 17 days of real history (2026-10-06T23:48Z to 2026-10-23T10:11Z), and almost all of it is sparse thesis snapshots, not price series.
- Price and liquidity series per mint and pool exist only in 40 collector files from 2026-10-06 to 2026-10-08 (125 GeckoTerminal OHLCV series for 33 pools). Nothing after 2026-10-08 is kept: the scheduled runs use a fresh database and export only the tables in state.py:21, which carry no candles, no pool snapshots and no quotes.
- Union over all 89 committed exports: 1,801 thesis snapshots (time, price, liquidity, exit capacity at 3%, score, status) for 248 mints; 93 mints have two or more priced snapshots, median span 120 h, median gap 0.93 h, 90th percentile gap 23.8 h. Snapshots exist only for tokens that reached deep analysis (selection, see "Universe").
- Launch-cohort outcome fields are nearly empty: of 1,422 launches ever exported, 8 have a 24 h market cap, 3 a 7 d value, 0 a 30 d value, and `rug_flag` is never 1. The launch pass stopped adding launches after 2026-10-09.
- The free GeckoTerminal API returns historical pool OHLCV back to pool creation for a pool created 2026-10-04 (15-minute candles reached back 20 days with `before_timestamp`), including a pool that stopped trading on 2026-10-20. DEX Screener returns only current state. Both answered HTTP 200 from this environment.
- So a historical training set must be built from GeckoTerminal backfills keyed by the pools the lab already recorded, with the backfill date recorded as the retrieval time (crawl date is not availability date), or collected forward. Phase 01 decides; nothing was pulled in Phase 00.

## Tracked SQLite file `data/memelab.sqlite`

sha256 `068287c0d7e454361eb42f54b2f90e49e4075ae3a962a3c57867165ab6a679ca`, 2,863,104 bytes, one commit (`b6c424d`, 2026-10-06T21:12-04:00), never updated. Tracked although `.gitignore:2 *.sqlite*` matches it. It predates the catalyst, chain, launch and social schemas (none of their tables exist in it).

| Table | Rows | Time range (UTC) | Clock column |
|---|---:|---|---|
| tokens | 13 | first_seen_at 2026-10-06T23:54 to 2026-10-07T00:45; graduated_at 2026-09-09 to 2026-10-04; first_pool_at 2026-07-23 to 2026-10-04 | first_seen_at, last_seen_at (run time t); graduated_at, first_pool_at (provider) |
| market_snapshots | 33 | observed_at 2026-10-06T23:48 to 2026-10-07T00:16 | observed_at = t (see clocks) |
| pool_snapshots | 182 | same window | observed_at = t |
| pools | 58 | pool_created_at 2026-08-12 to 2026-10-06 | pool_created_at (provider), first_seen_at |
| liquidity_quotes | 498 | same window | observed_at = t |
| holders | 660 | same window | observed_at = t |
| wallet_clusters | 172 | same window | observed_at = t |
| wallet_transactions | 3,774 | block_time 2026-10-05T23:59 to 2026-10-07T00:09 (6 mints) | block_time (provider trade time) |
| price_levels | 615 | same window | observed_at = t |
| social_snapshots | 99 | same window | observed_at = t |
| token_authorities | 33 | same window | observed_at = t |
| theses | 33 | created_at 2026-10-06T23:48 to 2026-10-07T00:16 | created_at = t |
| entries | 43 | | via thesis |
| rejections | 20 | rejected_at 2026-10-06T23:25 to 2026-10-07T00:16 | rejected_at = t |
| watchlist | 5 | added_at 2026-10-06T23:48 to 2026-10-07T00:07 | added_at |
| exits, positions, trade_reviews, wallets, fetch_log | 0 | | |

`positions`, `exits` and `trade_reviews` are empty: no real or paper trade history exists for m27/m28.

## State export `data/state/latest.json`

Written by `python -m memelab.state export` (state.py:45), committed to `main` by the scheduled runs, imported into a fresh database at the start of the next session (state.py:77). Exported tables are fixed (state.py:21); theses are capped at the newest 12 per mint, launch cohort at 45 days, launch alerts at 7 days, rejections of launches at 30 days (state.py:28-32, theses cap state.py:45 and :55-60).

| Table | main `98338a8` rows | main time range (UTC) | HEAD `f99c6c7` rows (export of 2026-10-12) |
|---|---:|---|---:|
| tokens | 984 (solana 937, bsc 28, ethereum 13, base 6) | first_seen_at 2026-10-06T23:54 to 2026-10-23T10:19 | 576 |
| theses | 701 (248 mints, 104 with 2 or more) | created_at 2026-10-06T23:59 to 2026-10-23T10:11 | 473 |
| entries | 1,465 | | 1,218 |
| watchlist | 69 | added_at 2026-10-07T14:28 to 2026-10-23T10:11 | 35 |
| rejections | 1,013 (structural 400, stage2-evm 342, deep 271) | rejected_at 2026-10-06T23:25 to 2026-10-23T10:11 | 446 |
| chains | 23 | updated_at to 2026-10-23T10:19 | 22 |
| chain_snapshots | 483 | observed_at 2026-10-07T17:14 to 2026-10-23T09:47 | 252 |
| chain_scores | 207 | same | 108 |
| regime_snapshots | 23 | same | 12 |
| narratives / narrative_snapshots | 170 / 925 | same | 147 / 483 |
| benchmark_baskets | 88 | same | 44 |
| ecosystem_alerts | 277 | same | 144 |
| upcoming_launches | 56 | created_at 2026-10-06T01:34 to 2026-10-09T11:50 | 56 |
| launch_cohort | 1,176 | created_at 2026-09-09 to 2026-10-09T11:57 | 1,182 |
| launch_monitor / transitions / rejections | 124 / 24 / 56 | 2026-10-08T15:41 to 2026-10-09T12:21 | same |
| launch_alerts | 0 | | 5 |
| catalyst_page_fetches, catalyst_page_facts, social_api_spend | 0 (main runs `f084b60` code, which does not export them) | | not present in the 2026-10-12 export |

Not exported at all: market_snapshots, pool_snapshots, liquidity_quotes, holders, wallet_transactions, price_levels, catalyst events, items, links, assessments and outcomes, every social table. Each scheduled session's catalyst pass starts empty (FIRECRAWL.md "Gaps and open items" says the same).

Theses `snapshot_json` keys (m25_watchlist_monitor.py:8-20): `t, price, mcap, fdv, liquidity, exit_cap_3pct, holders, adj_top10, cluster_pct, dev_pct, insider_pct, direction, vol_24h, net_buyers_24h, structure, nearest_support, nearest_resistance, lifecycle, attention, score, status, fatal`.

### History across all committed exports (probe `state_history_probe.py`)

| Measure | Value |
|---|---|
| `data/state/latest.json` commits on main | 89, first 2026-10-07T17:53-04:00, last 2026-10-23T06:20-04:00 |
| Commits per day | 10-07: 6, 10-08: 28, 10-09: 23, 10-10: 19, then 1 a day from 10-11 to 10-23 (around 06:20 New York time) |
| Root `state/latest.json` (older format) | 6 commits, all 2026-10-07 |
| Thesis snapshots, union by (mint, created_at) | 1,801 for 248 mints |
| Snapshots per mint | 1 for 144 mints, 2 for 42, 3 to 9 for 36, 12 to 122 for 26 |
| Mints with 2 or more priced snapshots | 93; span p50 120 h, p90 330 h, max 394 h |
| Gap between consecutive snapshots | p10 0.12 h, p50 0.93 h, p90 23.8 h |
| Priced mints last seen more than 72 h before the last export | 58 of 93 |
| Priced mints whose last price is under 10% of their max | 2 of 93 |
| Last status of priced mints | REJECTED 47, DISTRIBUTION RISK 24, RESEARCH REQUIRED 12, THESIS INVALIDATED 6, SETUP DEVELOPING 2, OVEREXTENDED 2 |
| Distinct tokens across exports | 989 |
| Symbols shared by 2 or more mints | 102 (XMR 10 mints, BTC 7, ETH 5, XRP 5, PLAGUE 5) |
| Distinct rejected mints | 640 |
| Launch cohort, distinct mints | 1,422; mcap_24h known 8, mcap_7d 3, mcap_30d 0, rug_flag 1: 0 |

Earlier versions of the export can be read with `git show <sha>:data/state/latest.json`, so trimmed theses (beyond 12 per mint) survive in git history. The git commit time is a conservative public availability time for every row in a version.

## Collector files

| Location | Files | Dates (first commit) | Content |
|---|---:|---|---|
| `inbox/*.json` (main and HEAD identical) | 40 (+2 plans) | 2026-10-06T19:42-04:00 to 2026-10-08T10:03-04:00 | raw projections keyed `gt_pools:`, `gt_info:`, `gt_ohlcv:<pool>:<tf>`, `gt_trades:`, `jq:<side>:<usd>:<mint>` (Jupiter quotes), `jup_tok:`, `ds:`, `rug:`, `rpc:`, `rpc_evm:`, `goplus:`, catalyst feeds |
| `data/inbox/*.json` | 13 | 2026-10-06 to 2026-10-07 | the session behind the tracked DB (disc01, s2_01, deep01a to deep04, forensics01, stage1 and stage2 files) |
| `data/reports/*.md` | 24 | 2026-10-06/07 | token and scout reports |

No collector file was committed after 2026-10-08 (`git log --format=%cd origin/main -- inbox/`). Since then the scheduled runs collect with `python -m memelab fetch` in their own session and keep only the state export.

OHLCV in `inbox/` (my count; REPLAY_17.md reports 16,847 candles on the same files): 128 `gt_ohlcv` keys, 125 with candles, 3 empty; 33 pools; day1 series 34 (median 22 candles, earliest 2026-06-10), hour1 34 (median 300, earliest 2026-09-24), minute15 33 (median 200, earliest 2026-10-02), minute5 9, minute1 15; every series ends by 2026-10-07T17:45Z to 2026-10-08.

## Clocks

| Field | Meaning in the code | Anchor | Risk for a predictive feature |
|---|---|---|---|
| result `_at` | collector run start, ISO UTC | bridge/collector.js:86 | per-request fetch time is not stored (only `ms` duration); a merge plan re-stamps earlier bodies with the new `_at` |
| `Result.observed_at` | `_at`, or `time.time()` when `_at` is missing | bridge/ingest.py:24 | a file without `_at` gets the processing time |
| command time `t` | max `observed_at` over every result file given | cli.py:44 | a thesis mixes inputs fetched up to ~50 min apart under one time (HIGGS: s2_01 23:25Z and deep02 23:59Z stamped 00:16Z) |
| theses.created_at, snapshot_json.t, market_snapshots.observed_at, pool_snapshots, liquidity_quotes, holders, rejections.rejected_at | `t` | pipeline.py:187-260, cli.py:181 | not a per-field availability time |
| tokens.first_seen_at / last_seen_at | `t` at upsert | db.py:288-300 | |
| wallet_transactions.block_time | provider trade time | db.py:141 | chain or provider clock, not lab clock |
| GeckoTerminal OHLCV row `ts` | candle open time | provider | candle closes at ts + timeframe; availability needs close plus provider delay (replay_sources.py:28 assumes 300 s, HEURISTIC) |
| pools.pool_created_at, tokens.graduated_at, first_pool_at | provider claims | normalize.py | |
| catalyst items: published_at, retrieved_at, first_seen_at; events: published_at, discovered_at, retrieved_at, event_at | source claim, lab read, first lab sighting, scheduled event time | catalyst/schema.py:35-37, :50-51 | separated already |
| catalyst page fetches: fetched_at and the page's own published/modified time (no zone means UNKNOWN, FC-14) | | catalyst/firecrawl.py:679 | crawl date is not publication date (P04) |
| launch_cohort: created_at (launch), first_seen_at, last_checked; mcap_24h / 7d / 30d | value read when the launch is 20-48 h, 6-10 d or 27-40 d old; the read time is not stored | launch/discover.py:383, launch/cohort.py:107-110 | the horizon is a window, not a point; no measured_at |
| social: published_at, first_observed_at, `_avail` (earliest demonstrable availability) | | social/replay_core.py (cutoff clock), outcomes_core.py:115-120 | the most complete clock model in the repo |
| state export `_exported_at`; git commit time | export time; public availability | state.py:48 | conservative available_at for exported rows |

## Universe and survivorship

- Theses exist only for tokens that passed discovery (stage 1, m01 filters: liquidity at least $20k, 24 h volume at least $50k by default, cli.py:397) and stage 2, or that sat on the watchlist. Stage-1 universes are not exported, so the denominator of "tokens seen" is lost after each session; rejections keep the mint, stage and reason only.
- Dead tokens do not get deleted, but they stop being observed: 58 of 93 priced mints have no snapshot in the last 72 h of the record. A label computed from theses alone would treat silence as missing, not as death; a token that rugs after its last snapshot is invisible unless a backfill is pulled.
- GeckoTerminal still served candles for HIGGS's Meteora pool, whose daily candles end 2026-10-20 (no trades after that day; empty intervals are omitted by default). DEX Screener's current answer for the same mint lists one pair (PumpSwap, $40.7k liquidity), while the 2026-10-07 bundle listed 18 pools across providers. A current vendor snapshot is not the historical pool set (P02, P09).

## Free public APIs (checked 2026-10-24, single calls)

| Call (UTC time) | Result |
|---|---|
| GeckoTerminal `GET /api/v2/networks/solana/pools/DQyGMAGx8nB6ykixotLNFC6eVVQjrMqz7AkRyinNkEm1/ohlcv/day?aggregate=1&limit=1000&currency=usd` | HTTP 200, 0.79 s, 17 daily candles 2026-10-04 to 2026-10-20 (pool created 2026-10-04) |
| GeckoTerminal same pool `ohlcv/minute?aggregate=15&limit=1000&before_timestamp=1791331200` | HTTP 200, 0.72 s, 237 candles 2026-10-04T13:00Z to 2026-10-07T00:00Z, i.e. 15-minute history reachable 17 to 20 days back |
| DEX Screener `GET /tokens/v1/solana/DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump` | HTTP 200, 0.33 s, 1 pair, current fields only (`priceChange`, `volume`, `liquidity` by window, `pairCreatedAt`) |
| GitHub REST `GET /repos/RyzinEnagy/memelab-inbox/pulls` (unauthenticated) | HTTP 403 from this environment; PR state taken from docs |

Provider documentation (read 2026-10-24):

- GeckoTerminal OpenAPI spec `https://api.geckoterminal.com/docs/v2/swagger.json` (sha256 `041b6d03d6a49e69a146e6787462cc3e36191c5b21709de277aa0c31f521fbbe`, version "v2-beta"): "This Public API is limited to approximately 10 calls/minute, which may fluctuate based on network traffic"; endpoints cached for 1 minute; OHLCV `timeframe` day (aggregate 1), hour (1, 4, 12), minute (1, 5, 15); `limit` maximum 1000; `before_timestamp` in epoch seconds; `include_empty_intervals` default false; `currency` usd or token; trades endpoint returns "the last 300 trades in the past 24 hours" (longer windows are Pro API only). No stated limit on how far back OHLCV goes; the HIGGS check shows at least to pool creation for a 20-day-old pool. The page https://www.geckoterminal.com/dex-api says "from 10 calls/min to 250 calls/min" with a paid plan; an older CoinGecko support article (https://support.coingecko.com/hc/en-us/articles/22612838274841-Does-GeckoTerminal-have-an-API) says 30 calls/minute, and the lab's collector paces GeckoTerminal at 2.6 s per call assuming about 30 per minute (collector.js:78-79). Plan for 10 per minute.
- DEX Screener OpenAPI spec linked from https://docs.dexscreener.com/api/reference (sha256 `e40964ed9f7c598680b80abf4d296c23f20d67991735ada30c4a9a5ef5d12992`): token profiles, community takeovers, ads, boosts and orders "rate-limit 60 requests per minute"; pairs by chain and pair address, pairs by token address, token pools and search "rate-limit 300 requests per minute". No endpoint returns a historical series.

What Phase 01 can count on: GeckoTerminal OHLCV per pool (price and volume history, not executable depth); current DEX Screener and Jupiter state; the lab's own sparse thesis snapshots (which include exit capacity at 3% impact at each snapshot, the only historical executable-depth measure the lab has). Historical executable depth for arbitrary past times does not exist in any source checked (P08, P25).

## Tracked or ignored

Tracked: `data/memelab.sqlite` (forced), `data/state/latest.json`, `state/latest.json`, `inbox/`, `data/inbox/`, `data/reports/`. Ignored: `*.sqlite*` (all other DBs, including temp DBs and `-wal`/`-shm` files), `data/private/` (signal ledger, private social content, Firecrawl config), `data/config.json`, `data/wallet/`, key files. Phase 00 changed none of them; the suite created `data/memelab.sqlite-shm` and an empty `-wal` beside the tracked DB (ignored; the DB hash is unchanged) and an untracked `data/reports/<stamp>_BRETT_0x532f.md` (removed by hand, see COMMIT_AND_TEST_LOG.md).
