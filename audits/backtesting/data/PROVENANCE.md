# Historical corpus provenance (Phase 06)

Built 2026-10-23 between about 16:45Z and 17:45Z. Database: `data/backtest/bt.sqlite` (gitignored, separate from the lab's tracked DB; D-BT-018). Raw responses: `data/backtest/raw/geckoterminal/<sha256>.json` (gitignored, immutable, keyed by content hash). Every stored row carries its raw reference.

## Sources actually used

| Data | Source | Access | Status |
|---|---|---|---|
| Discovery universe (who the lab saw, when, and what it decided) | git history of `data/state/latest.json` on `origin/main` (95 versions), `memelab/backtest/sources/labstate.py` | local git | OBSERVED. Union of every thesis and rejection over all versions, not the latest file |
| Pool list per mint | GeckoTerminal `GET /networks/solana/tokens/{mint}/pools?page=1` | public, no key, about 30 calls/min | OBSERVED as of the fetch time (`POOL_LIST_PRESENT_DAY`). Pools are valid for a decision only from `pool_created_at` and their availability time |
| Hourly OHLCV per pool | GeckoTerminal `GET /networks/solana/pools/{pool}/ohlcv/hour?aggregate=1&limit=1000&currency=usd&token={mint}` | public | OBSERVED, backfilled. First version of a bar is available at close + 300 s (modeled, flagged `AVAIL_MODELED,BACKFILLED`). A later different version is a `REVISION` available from its own fetch time |
| Raw swaps | GeckoTerminal `GET /networks/solana/pools/{pool}/trades` | public | Present-only: the latest 300 trades. Probe (`p06_trades_probe.json`): a liquid pool's 300 trades covered 27 minutes; a dead pool returned 0. Historical swaps: SOURCE_BLOCKED |
| Pool reserves, CLMM ticks, DLMM bins, LP changes at past times | none reachable without a paid indexer or archive RPC | | SOURCE_BLOCKED (D-BT-011). No reserve history is inferred from today's pool share |
| Token authorities, holders, concentration | the lab's own thesis snapshots (contemporaneous) | local | OBSERVED only at the lab's own analysis times. No holder history between snapshots |
| Wallet activity history | needs Helius or similar (no key in this session) | | SOURCE_BLOCKED |
| Catalyst and social observations | the lab's catalyst tables (read-only bridge, Phase 09) and `bt_capture_provenance` (crawler captures, Phase 06A) | local | Captured-at times only; old pages crawled now are UNKNOWN_AS_OF before their capture |

## Fetch runs

| Run | Where | Mints | Calls | 429 retries | Result |
|---|---|---|---|---|---|
| container A (`run_corpus2.py`, plus 7 mints from an earlier start) | cloud workspace | 100 (list `p06_mints_container.json`) | 296 | 72 | log `p06_corpus_log_container_a.jsonl` |
| work computer (`gt_fetch_win.py`, stdlib only, GET to api.geckoterminal.com only) | Elving's work computer, to split the per-IP rate limit | 91 of 161 (list `p06_mints_workpc.json`, forward order) | 424 (212 OK, 211 HTTP 429, 1 HTTP 404) | in the 424 | manifest `p06_gt_manifest_workpc.jsonl` with observed_at and sha256 per response |
| container B (`run_corpus3.py`) | cloud workspace | 77 of the same 161, reverse order, stopped by a stop file once the two runs overlapped | 247 | 46 | log `p06_corpus_log_container_b.jsonl` |
| replay of the work-computer responses (`ingest_win.py`) | cloud workspace | 82 new, 9 already present; after the resume fix one more mint (bars interrupted by the stop file) | 0 network | | the same parser as live fetches, fed the saved bytes with their recorded observed_at; a further replay added 0 rows |

All 261 selected mints were covered by at least one run. Commands: `python3 audits/backtesting/data/run_corpus2.py`, `python3 audits/backtesting/data/run_corpus3.py`, `python3 audits/backtesting/data/ingest_win.py` (they hold absolute scratch paths from this session; the logic is `corpus.build` and `gecko.fetch_*`). Run summaries: `testing/logs/p06_corpus_runs.log`.

## Choices that limit what the corpus can say

- One page of hourly bars per pool (limit 1000). 9 tokens hit the cap, so their history before the last 1000 hours was not fetched.
- Container runs fetched bars for one candidate pool per mint (largest present reserve, plus the oldest pool and the lab's own pool when different). The work-computer run used the same candidate rule. Other pools are listed (1,557 pool versions) but have no bars.
- GeckoTerminal omits hours with no swaps. A missing hour is reported as a gap, never filled, and the engine treats it as no observation.
- The corpus is Solana only. The universe also holds 47 EVM theses (base, bsc, ethereum); they are out of this corpus.
- USD prices are GeckoTerminal's own USD conversion at the time of each bar. SOL/USD for fee conversion comes from the Raydium SOL/USDC pool when a study needs it; a missing rate raises instead of defaulting.

## Dataset identity

`quality.dataset_hash(con, all 261 mints, tf=3600)` = `3d8dfd1e6dfa70575fc3f322de8b53b4e2cd316d793c3a8b0d02b9851e54e62a` over 139,168 bars, 1,557 pool versions, 1,560 pool-reserve observations and 2,901 universe rows (before the resume fix it was `8d3a89dd...` over 138,827 bars). The hash covers mint, pool, start, OHLCV and availability of every bar, so any re-fetch that changes visible data changes it.
