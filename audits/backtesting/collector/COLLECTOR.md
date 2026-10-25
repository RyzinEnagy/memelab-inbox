# Forward depth collector (D-BT-034)

Work record for the collector Elving approved on 2026-10-25 (predictive PI-D-020, now PI-D-044), folded into the hourly shadow tracker. Branch `work/backtesting-collector`, based on feature/backtesting at 054a619. Operator text: docs/backtesting/RUNBOOK.md, "Forward depth collection".

## What the tracker already recorded

- `refresh` (outcomes.refresh): new hourly OHLCV bars, and an OHLCV_FETCHED observation, for the basis pool of each outcome window that waits on a refresh. Bars only: no reserves, no quotes.
- `track` (outcomes.track): outcome windows of 1, 6, 24 and 72 h for the frozen opportunities in bt_universe_members and the stored assessments. The universe was built from the exports up to the corpus build; no command imports newer lab records (RUNBOOK, "Backfills").
- Reserves: only POOL_RESERVE_USD_PRESENT observations written when the corpus listed a mint's pools (gecko.fetch_pools): USD only, once per corpus build, not on a grid, not in token units.
- Quotes: none stored. Assessments can price a fill from a router quote seen at the decision (QUOTE_OBSERVED), but the module never kept quotes for later.

Missing for PI-D-020: for every decision, reserves and sell quotes at fixed sizes at the decision and on a grid to 24 h, keyed by chain, exact mint and pool.

## What was added

- `memelab/backtest/depth.py`: decisions from the exports (reuses sources/labstate.py), pool reads and quotes (reuses sources/gecko.py: Budget, get_json with backoff, the raw store by sha256), status.
- `gecko.get_json` gained a `provider` argument (default unchanged) so Jupiter bodies are kept under raw/jupiter/. The development run found them filed under raw/geckoterminal/.
- Schema migration 2: `bt_depth_decisions`, `bt_depth_snapshots`, append-only, rollback to 1. Migration 1 and its checksum are unchanged.
- CLI: `python -m memelab backtest depth collect|status`.
- `audits/backtesting/release/hourly_shadow.sh`: step `collect` between refresh and track, on the work copy only.
- Tests: tests/test_backtest_depth.py (13), fixtures tests/fixtures/backtest/depth/ (recorded bodies of the smoke below). tests/test_backtest_timeguard.py now expects migrations [1, 2].

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
| total | 11 | 14 | 4 |

No retry was needed in the smoke. The local run of hourly_shadow.sh (testing/logs/c01_hourly_script_e2e.log) had the network blocked and made no market call.

## Smoke, 2026-10-25 13:22Z

Command: `python -m memelab backtest depth collect --repo LAB_GIT --db SCRATCH/bt.sqlite --max-gt-calls 4 --max-quote-calls 6`, exit 0, 42.2 s. LAB_GIT is a shallow fetch of `main` since 72 h before: exports 98338a8 (baseline), efdaee9 and e245d91 (2026-10-25T10:10:02Z).

- 19 decisions, all from e245d91: 16 Solana, 2 BSC, 1 Base. Pools: 11 EXPORT_GRADUATED_POOL, 3 EXPORT_PRIMARY_POOL, 5 VENDOR_TOP_POOL (one token-endpoint call).
- 19 pool snapshots OK (3 multi-pool calls: Solana 16 pools, BSC 2, Base 1), 3 QUOTE_UNSUPPORTED_CHAIN rows.
- 6 quotes OK, the cap; 42 quotes not attempted and reported as such.

| Mint | Size USD | Tokens sold | USDC out | Out / size | priceImpactPct |
|---|---|---|---|---|---|
| 7M3gDRgo...pump | 100 | 41,635.11 | 99.96 | 0.9996 | 0.0015 |
| 7M3gDRgo...pump | 500 | 208,175.56 | 497.88 | 0.9958 | 0.0054 |
| 7M3gDRgo...pump | 2,000 | 832,702.26 | 1,980.46 | 0.9902 | 0.0109 |
| 9aqmJjCn...qjj | 100 | 278,932.04 | 99.54 | 0.9954 | 0.0052 |
| 9aqmJjCn...qjj | 500 | 1,394,660.21 | 493.20 | 0.9864 | 0.0142 |
| 9aqmJjCn...qjj | 2,000 | 5,578,640.82 | 1,904.60 | 0.9523 | 0.0483 |

- Lag from the export commit to the first snapshot: 11,545 s, because the smoke ran 3.2 h after the export. In hourly operation the first snapshot comes at the first run after the export.
- Files: smoke/collect.json, smoke/status.json, smoke/decisions.csv, smoke/snapshots.csv (one line per row: URL, captured_at, HTTP status, raw sha256, values), smoke/raw/ (the 10 bodies; each file name is its sha256), smoke/dev_run_collect.json (the development run's summary).

## Checks

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_backtest_depth.py -q -p no:cacheprovider` | 0 | 13 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/collector_mutations.json` | 0 | 18 of 18 caught (first pass 17 of 18; a test for a recent baseline export was added) |
| `python -m pytest tests -q -p no:cacheprovider` | 1 | 1 failed (C-1, tests/test_catalyst.py::test_dedup_corroboration_resurface_denial), 1043 passed |
| `python tools/release_audit.py` | 0 | Needs action: no |
| `python tools/release_e2e.py --out e2e.md` at 50565ad | 0 | PASS, 78 of 78, network attempts 0 |
| hourly_shadow.sh setup, refresh, collect, track, save in a scratch HOME, network blocked after setup | 0 each | EXPORTS_NOT_FETCHED, 19 pool rows SOURCE_BLOCKED, save OK; a broken work copy gave FAILED and left the stored file byte-identical |

Logs: audits/backtesting/testing/logs/c01_*.log. Not run: audits/backtesting/testing/p17_doc_claims_check.py, which needs the research database (data/backtest/bt.sqlite), now kept only on Elving's computer; the two new runbook commands were checked by hand against `python -m memelab backtest depth --help`.

## Limits

- Quotes only on Solana. BSC, Base and Ethereum get reserves only.
- A quote is Jupiter's route at that moment (any pool), not a fill in the export's pool. The reserves are the export's pool only.
- The USD price used to size a sale comes from the same run's GeckoTerminal read; a stale vendor price gives a different token amount, and the stored amount says which.
- 40 quotes per run cover about 13 pools at three sizes; on a busy day some pools miss some hours.
- The refresh step that runs just before still paces GeckoTerminal at 3 s (D-BT-033); only collect keeps to 6 a minute.
- Nothing ran on Elving's computer; the timing there is not measured.
