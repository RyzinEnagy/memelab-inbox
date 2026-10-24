# Phase 02 search log

All searches run 2026-10-23. Primary channel: GitHub REST search API (`GET https://api.github.com/search/repositories?per_page=12&q=...`, unauthenticated, from Elving's work computer because the workspace proxy blocks GitHub search). Raw output: `raw/p02_github_search.txt` (sha256 in PHASE_02.md); parsed hits: `raw/p02_github_search_hits.csv` (273 hits, 268 unique repos).

## GitHub API queries

| # | Family | Query | total_count | UTC | rows read |
|---|---|---|---:|---|---:|
| 1 | VEC | `vectorized backtesting python` | 92 | 2026-10-23T15:43:32Z | 12 |
| 2 | VEC/EVT | `backtesting framework language:python stars:>200` | 17 | 2026-10-23T15:43:40Z | 12 |
| 3 | EVT | `event-driven backtesting engine` | 268 | 2026-10-23T15:43:48Z | 12 |
| 4 | EVT | `event driven trading simulator order book` | 5 | 2026-10-23T15:43:55Z | 5 |
| 5 | CRY | `solana backtest` | 79 | 2026-10-23T15:44:03Z | 12 |
| 6 | CRY | `solana dex trading bot backtest` | 1 | 2026-10-23T15:44:10Z | 1 |
| 7 | CRY | `memecoin backtest` | 17 | 2026-10-23T15:44:18Z | 12 |
| 8 | CRY | `pump.fun backtest` | 14 | 2026-10-23T15:44:25Z | 12 |
| 9 | AMM | `uniswap v3 backtest` | 25 | 2026-10-23T15:44:48Z | 12 |
| 10 | AMM | `concentrated liquidity simulator` | 5 | 2026-10-23T15:44:55Z | 5 |
| 11 | AMM | `amm simulation python` | 17 | 2026-10-23T15:45:03Z | 12 |
| 12 | AMM | `meteora dlmm` | 266 | 2026-10-23T15:45:10Z | 12 |
| 13 | AMM | `raydium clmm sdk` | 12 | 2026-10-23T15:45:18Z | 12 |
| 14 | AMM | `orca whirlpools` | 44 | 2026-10-23T15:45:26Z | 12 |
| 15 | CAT | `event study python finance` | 37 | 2026-10-23T15:45:41Z | 12 |
| 16 | CAT | `crypto sentiment backtest` | 48 | 2026-10-23T15:45:49Z | 12 |
| 17 | CAT | `solana wallet tracker` | 611 | 2026-10-23T15:45:57Z | 12 |
| 18 | CAT | `twitter sentiment trading backtest` | 10 | 2026-10-23T15:46:04Z | 10 |
| 19 | VAL | `walk forward optimization backtest` | 204 | 2026-10-23T15:46:19Z | 12 |
| 20 | VAL | `purged cross validation` | 63 | 2026-10-23T15:46:27Z | 12 |
| 21 | VAL | `deflated sharpe ratio` | 101 | 2026-10-23T15:46:34Z | 12 |
| 22 | VAL | `backtest overfitting probability` | 33 | 2026-10-23T15:46:42Z | 12 |
| 23 | EVT | `tick data replay backtest` | 8 | 2026-10-23T15:46:49Z | 8 |
| 24 | VAL | `portfolio performance analytics python` | 534 | 2026-10-23T15:46:57Z | 12 |
| 25 | EVT | `latency mev simulation` | 4 | 2026-10-23T15:47:05Z | 4 |
| 26 | CAT | `rug pull detection liquidity` | 14 | 2026-10-23T15:47:13Z | 12 |
| 27 | CRY | `crypto backtesting dex slippage` | 0 | 2026-10-23T15:44:33Z | 0 |
| 28 | AMM | `jupiter aggregator quote simulation` | 0 | 2026-10-23T15:44:40Z | 0 |
| 29 | AMM | `constant product amm math library` | 0 | 2026-10-23T15:45:33Z | 0 |
| 30 | CAT | `onchain historical data solana python` | 0 | 2026-10-23T15:46:12Z | 0 |

## Other channels

| Channel | Query / source | Result used |
|---|---|---|
| Firecrawl developer search | `backtest Solana memecoin strategy with AMM reserves slippage simulation python` (k=15) | nikkisora/PolarBT, hzcx404/memecoin-trading-bots (rejected) |
| Firecrawl developer search | `uniswap v3 concentrated liquidity backtesting simulator tick math python library` (k=15) | defipy-devs/uniswappy, atiselsts/uniswap-v3-liquidity-math, bowtieddevil/degenbot |
| Firecrawl developer search | `purged k-fold cross validation combinatorial purged CV backtest overfitting library python` (k=12) | eslazarev/purged-cross-validation; skfolio (citation) |
| Firecrawl developer search | `Solana pump.fun pumpswap raydium historical swaps pool reserves backtesting dataset python` (k=12) | solana-foundation/surfpool; data-vendor findings (Bitquery archive, PumpSwap virtual_quote_reserves) |
| Curated list (git clone) | WallStreetPete/awesome-open-source-trading @ 8f4e6d67 (462 GitHub links) | bsdz/yabte, Finance-broski/backtest-bias, rytjy/backtest-audit-kit, nkaz001/hftbacktest confirmation |
| Curated list (git clone) | wilsonfreitas/awesome-quant @ b52a1a94 (632 links) | eslazarev/purged-cross-validation confirmation |
| Curated list (git clone) | jeff3388/awesome-backtesting-python @ 957c0a6d (11 links) | no new candidates |
| Seeds | references/CANDIDATE_SEEDS.md (23 URLs) | 22 resolve; dexterous/serum-dex NOT_FOUND (git ls-remote) |
| Citation | tradingstrategy-ai/getting-started -> trade-executor | tradingstrategy-ai/trade-executor |
| Successor | quantopian/alphalens (archived) -> stefan-jansen/alphalens-reloaded | alphalens-reloaded |

## Gaps from access limits

- GitHub code search and topic search need authentication; not used. Repository search only (10 requests/min unauthenticated).
- Three queries returned 0 (`crypto backtesting dex slippage`, `jupiter aggregator quote simulation`, `constant product amm math library`, `onchain historical data solana python`): GitHub repo search ANDs all words. Covered through other queries and Firecrawl developer search.
- PyPI search was not used as a separate channel (PyPI has no search API); package names are checked per shortlisted repo in Phase 03.
