# Data feasibility and expense matrix (Phase 01)

Ranked by value to the backtester divided by cost and risk. Probe evidence: `audits/backtesting/data/p01_gt_probe.json` (sha256 4b8c15c1...), 12 seeded-random Solana mints from the lab's own history.

| Rank | Data | Source | Historical? | Point-in-time basis | Cost | Feasibility today | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Lab discovery universe: theses (status, score, fatal flags, price, liquidity, exit capacity at 3%), rejections, tokens, launch cohort | git history of `data/state/latest.json` on `main` (89 commits) | yes, 2026-10-06 to now | `created_at` = lab observation; commit time = upper bound | free | AVAILABLE | includes rejected and later-dead tokens (survivorship defense); theses trimmed to 12 per mint per export, older ones recoverable from older commits |
| 2 | Hourly/15-min/daily OHLCV per pool | GeckoTerminal public API `pools/{p}/ohlcv/{tf}` with `before_timestamp`, up to 1000 bars | yes | bar start + period = earliest availability; plus provider lag | free, about 30 calls/min, 429 seen at 2.2 s pacing | AVAILABLE | dead pools still return bars (probe: reserve $0.0000001 pool returned bars); no-trade hours are absent rows, so missing must not become zero |
| 3 | Pool list, dex id, current reserve | GeckoTerminal `tokens/{m}/pools`, DexScreener | current only | today | free | AVAILABLE | dex id gives pool type (pumpswap = CPMM, raydium-clmm = CLMM, meteora DLMM) |
| 4 | Present-tense executable quotes by size | Jupiter `/swap/v1/quote`; the lab's own deep plans | present only | quote time + TTL | free | AVAILABLE | never a historical fill |
| 5 | Historical lab quotes | `liquidity_quotes` in local DB (28 min sample); `exit_cap_3pct` inside theses snapshots | yes (sparse) | observed_at | free | PARTIAL | capacity at the decision time for discovered tokens; exact per-size quotes only in the small local sample |
| 6 | Catalyst events with timestamps | `catalyst_*` tables, Firecrawl reads | yes from first capture | first_seen_at / fetched_at | Firecrawl credits | PARTIAL | catalyst tables not in exported state; local DB never migrated; real catalyst history therefore thin |
| 7 | Historical swaps (tick level) | GeckoTerminal trades (last 24 h only); Helius enhanced tx by pool address | Helius: yes | block time | Helius free tier; key not present in this workspace | BLOCKED (key) | needed for reserve reconstruction and exact historical fills |
| 8 | Historical pool reserves, CLMM ticks, DLMM bins | none free; would need archival RPC or a paid indexer | n/a | slot | paid / heavy | BLOCKED | EXACT historical CPMM/CLMM fills cannot be asserted; LIQ_SNAPSHOT_APPROX tier only where the lab observed liquidity |
| 9 | SOL/USD by time | GeckoTerminal SOL/USDC pool OHLCV | yes | bar close | free | AVAILABLE | for denominators (G16) |
| 10 | Wallet funding/activity | Helius (key), RugCheck insiders (present) | Helius yes | block time | key | BLOCKED (key) for history | present-tense holder data exists in theses snapshots |
| 11 | Social posts | social layer, credentials not configured | n/a | first_observed_at | credentials + cost | BLOCKED (Elving's credentials) | not needed for the first engine |

## Consequences

- Live historical backtests are possible for: lab-status signals and TA signals on GeckoTerminal bars, with fills modeled at LIQ_SNAPSHOT_APPROX or QUOTE_OBSERVED fidelity, over a survivorship-safe universe of about 660 Solana mints (201 thesis mints + 462 rejected mints, overlapping).
- Exact historical execution (reserve replay) is BLOCKED until a Helius key or an archival source is provided. Reports must say so.
- Catalyst strategies can be built and tested on fixtures plus whatever real catalyst captures exist; real catalyst history is thin, so Phase 09 will likely mark empirical catalyst validation PARTIAL.
- Window: the universe starts 2026-10-06, so about 17 days. Short. Statistical claims will be wide or abstain; that is the honest outcome.
