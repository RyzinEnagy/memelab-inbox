# Data coverage and quality (Phase 06)

Per-token detail: `p06_coverage.json` (from `corpus.coverage`). Numbers below were computed on 2026-10-23 at about 17:45Z.

## Coverage

| Measure | Value |
|---|---|
| Selected mints | 261 (all 201 Solana thesis mints plus 60 rejected-only Solana mints drawn with seed 20261023 from 438) |
| Mints with at least one stored hourly bar | 257 |
| Mints with no bars | 4: two are corrupted copies of real mints in the lab's own exports (HTTP 404 or no pools; see mint integrity below), two had no pools listed |
| Hourly bars stored | 139,168 across 378 pools of 258 mints (the extra mint is SOL, from the SOL/USDC reference pool) |
| Bars per token on its best pool | median 356, 10th percentile 5, max 1,000 (9 tokens at the one-page cap) |
| Tokens with fewer than 25 bars | 47 (too short for most TA warm-ups: INSUFFICIENT_HISTORY in Phase 08) |
| Missing hours inside each token's own span | median 4.0%, mean 25.7% (no-swap hours; never filled) |
| First and last bar | 2025-02-03 to 2026-10-23 |
| Universe entry window | 2026-10-06 23:25Z to 2026-10-23 10:11Z (17 days) |
| Tokens whose last bar is more than 3 days old | 45 (dead or untraded; kept, not dropped) |

Best-pool types: pumpswap CPMM 114, raydium-clmm 37, meteora DLMM 25, raydium CPMM 25, pump-fun bonding curve 19, meteora-damm-v2 19 (classed CLMM), orca 15, unknown 2. Only CPMM pools can get modeled fills (LIQ_SNAPSHOT_APPROX); the rest are UNSUPPORTED_POOL for fills unless a quote observed at decision time exists.

## Mint integrity (a real defect in the lab's exports)

`quality.mint_integrity` over the 494 Solana mints in the universe found two corrupted copies of real mints:

| Real mint (has bars, many records) | Corrupted copy in the exports | What is wrong |
|---|---|---|
| `6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx` (65 theses, 3 rejections) | `6GmAFSYS4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx` (1 thesis) | one letter case-flipped; valid length but a different key; HTTP 404 |
| `MukLDtJ8Cx9DxLbeyLRSWPSposTMWuwHANbuaudpump` (48 theses, 2 rejections) | `MukLDtJ8Cx9DxLbeyLRWPSposTMWuwHANbuaudpump` (1 thesis, 1 rejection) | one letter dropped; decodes to 31 bytes, not a public key; HTTP 404 |

The copies are kept as separate members with no data (INSUFFICIENT_HISTORY) and reported. They are never merged into the real token by similarity, since a near-match is how impostor tokens work (G38). The source of the corruption in the lab's export path is not fixed here (lab code is out of scope); it is listed in GAPS for the lab owner.

## Bar quality flags

| Flags | Bars |
|---|---|
| `AVAIL_MODELED,BACKFILLED` | 138,867 |
| `AVAIL_MODELED` (fetched within an hour of close) | 185 |
| `DUP_TS_IN_RESPONSE,AVAIL_MODELED,BACKFILLED` | 58 |
| `DUP_TS_IN_RESPONSE,REVISION` | 58 |

GeckoTerminal returned the same start time twice inside one response for 58 bars. The first copy is stored as the bar, the second as a revision available only from its fetch time, so neither can leak earlier.

## Reconciliation (two independent observations of one moment)

`quality.reconcile_lab_vs_bars`: the lab's own spot price in each thesis snapshot (from its contemporaneous provider pulls) against the GeckoTerminal bar that contains that moment.

| Measure | Value |
|---|---|
| Theses with a price | 1,019 |
| A bar exists at that moment | 913 (106 without: pool not fetched, or no swap that hour) |
| Lab price inside the bar's low-high range | 811 (88.8%) |
| Outside the range but within 10% | 98 |
| Outside 10% | 4 (0.4%): two snapshots of 55Vr2Vp... at +21%, G8uXpbg... at -20%, 6GmAFSY... at +16%. Likely a different pool or quote source; such tokens get PARTIAL_WITH_LIMITATIONS |
| Median relative difference | 0.0 |

## A collapsed token, inspected by hand

`3GVSN8DLVvrxEafP7JQj6CwBFRxCq8vuUVmsRbCEpump`, pumpswap pool `7AvDaHL...` (created 2026-10-08). Close 0.0255 USD in its first hour, 2.3e-06 USD three days later (a 99.99% fall). The lab analyzed it on 2026-10-09 12:18Z at 0.0114 USD with score 48 and status REJECTED. Its 38 bars stay in the corpus; the engine marks an untradeable exit as NON_EXECUTABLE (proceeds 0). The raw responses are committed as the real-data fixture `tests/fixtures/backtest/real/` (unmodified bytes, hashes in its MANIFEST).

## Raw swaps, inspected

`p06_trades_probe.json`: GeckoTerminal's trades endpoint gives the latest 300 trades only. For pumpCmX... the newest trade was a sell of 2,004.16 tokens for 9.107 USDC at 17:36:49Z, and the 300 trades reached back only to 17:10:05Z. The dead pool above returned none. So swap-level history (needed for exact fills and wallet-flow features) is not available from this source.

## Refusal policy (quality.REFUSAL_POLICY)

no pool valid at decision -> INSUFFICIENT_HISTORY; non-CPMM without an observed quote -> UNSUPPORTED_POOL; bars before decision below warm-up -> INSUFFICIENT_HISTORY; last bar older than the staleness limit -> STALE_DATA; provider blocked -> SOURCE_BLOCKED; lab price and bars disagree beyond tolerance -> PARTIAL_WITH_LIMITATIONS; historical reserves requested -> INSUFFICIENT_EXECUTION_DATA.
