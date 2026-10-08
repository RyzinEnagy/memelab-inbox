---
name: memecoin-scout
description: Run the Memecoin Investing Lab opportunity scout (market regime, chain rotation with SOI, narrative rotation, then token discovery and due diligence on Solana, Base, BNB and other chains) or a single-token deep analysis by chain and contract. Use when asked to find memecoin opportunities, analyze a memecoin by mint or contract, refresh the watchlist, compare chains, or review a memecoin trade.
---

# Memecoin Investing Lab: opportunity scout

Research system only. Never execute trades, never ask for seed phrases or private keys, never connect a wallet with signing authority. "ENTRY CONDITIONS MET" is an evidence statement, not an instruction. Finding nothing is a valid result.

## Where things live

- Code and database: the `memelab` project folder (Python package `memelab/`, SQLite at `data/memelab.sqlite`, reports in `data/reports/`, inbox in `data/inbox/`). If the folder is not in the sandbox, pull it from the user's computer or the hand-off repo first.
- Hand-off repo for data: GitHub `RyzinEnagy/memelab-inbox` (public, market data only). The sandbox reads `raw.githubusercontent.com`; the browser writes by committing files.
- Config: `data/config.json` holds `gh_owner`, `gh_repo`, `gh_branch`, `helius_api_key`. Never print the key, never commit it.
- Docs: `docs/ARCHITECTURE.md` (module contract), `docs/SOURCES.md` (what each source gives and its tier).

## Collection: API pulls first, Chrome only as fallback

Since 2026-10-08 the sandbox reaches the crypto APIs directly (Jupiter, GeckoTerminal, RugCheck, DEX Screener, CoinGecko, GoPlus, honeypot.is, DefiLlama, Raydium LaunchLab, pump.fun, Clanker, Zora, Virtuals). Default path for every step:
- saved plans: `python -m memelab fetch <plan id> [<more plan ids>] [--as <result id>] [--dedupe]` runs them with Node and the same collector + projections the browser uses, retries rate-limited requests twice, writes `data/inbox/<id>.result.json` and lists anything that still failed;
- in-browser JS steps run the same way: `python -m memelab fetch --as <id> --pre <previous result id> --js 'await __ML.screen({...})'` (also `__ML.stage2([...])`, `__ML.deepPlan(...)`, `__ML.evmDeepPlan(...)`; a returned plan is executed);
- plan groups meant for different browser tabs (launch `_ex`, `_pump`, `_clanker`) are fetched together in one call.
Results fetched this way need no GitHub hand-off: they are already in the inbox. The Chrome bridge below is the fallback only for requests that fail from the sandbox (and for navigate-mode catalyst pages that need a DOM). If a host fails from both, record the source gap and continue.

## Chrome bridge (fallback)

Use Claude in Chrome, work in a tab on `https://example.com/` (no CSP, so fetch and eval work); same-origin-only hosts get a tab on their own origin. GitHub pages have a strict CSP: never fetch APIs from a github.com tab. Ship results with `__ML.ship`, commit, pull with `memelab.bridge.github_inbox.pull`.

## Standard run: "Find memecoin opportunities"

1. `python -m memelab init` (idempotent).
2. Load the collector in the example.com tab. If `bridge/collector.js` exists in the repo: `eval(await (await fetch("https://raw.githubusercontent.com/RyzinEnagy/memelab-inbox/main/bridge/collector.js")).text())`. Otherwise paste `memelab/bridge/collector.js` as one javascript_tool call. Same for `bridge/screen.js` and `bridge/stage2.js` when needed.
3. Discovery (stage 1): `python -m memelab plan discovery --id <disc_id>` prints the `await __ML.run({...})` call. Run it, then `await __ML.screen({minLiq:20000,minVol:50000})`, then the pre-score/trim step (top 28 full rows + rest summary, drop names), then `__ML.ship("inbox/<disc_id>.json")`.
4. On the GitHub new-file page: run the `land` snippet (decode `location.hash`, synthetic paste into `.cm-content`, then `history.replaceState`), click "Commit changes..." (top right, about x=1467,y=125 at 1553-wide viewport) and confirm. The user gave standing approval for data commits into this repo; ask again for anything else on GitHub.
5. Pull: `python - <<'EOF'` using `memelab.bridge.github_inbox.pull("inbox/<disc_id>.json", result_name="<disc_id>")`. Then `python -m memelab discover <disc_id>`.
6. Stage 2: in the example.com tab, `await __ML.stage2([...survivor mints...], {keep: 8})`, then the slimming step for rug/jup/ds bodies, ship as `inbox/<s2_id>.json`, commit, pull, then `python -m memelab stage2 <disc_id> --results <disc_id> <s2_id>`.
7. Deep fetch: print token params with the snippet in the CLI notes (`[mint, mainPool, decimals, price, liq]` per candidate). In the tab: `__ML.plan = __ML.deepPlan("<deep_id>", TOKENS, SOL_PRICE, {rpc: "https://mainnet.helius-rpc.com/?api-key=<key>"})`; `__ML.start(__ML.plan, 5)`; poll `__ML.done ? __ML.summary : __ML.progress()` (GeckoTerminal is paced at one call per 2.6 s; 3 tokens take about 2 minutes). Batch 3 tokens per file (URL fragment limit ~2 MB). Ship, commit, pull.
8. Optional forensics: for the top economic holders and the dev wallet, `Plan().wallet_forensics(wallets)` (Helius Enhanced Transactions) and `Plan().holders_full(mint)`; run in the tab, ship as `inbox/<id>_wallets.json`, pull. The pipeline picks up `helius_tx:*` bodies automatically.
9. Analyze and report: `python -m memelab scout --mints <deep candidates> --results <all result ids> --stage1 <disc_id>`. Per-token reports land in `data/reports/`, the scout report as `*_SCOUT.md`. Deliver the scout report and the top per-token reports to the user.
10. Watchlist and rejections: `python -m memelab watchlist`, `python -m memelab rejections`. Every analysis diffs against the previous thesis snapshot and prints WHAT CHANGED.

## Single token: "Analyze <mint>"

Never analyze from a ticker. Require the mint. Run stage2 for that mint alone (identity + structure), then the deep plan, then `python -m memelab analyze <mint> --results ... [--account-size X --max-loss-usd Y]`. Without account inputs the report gives only the liquidity-implied maximum size.

## Known data behaviours

- RugCheck `token_extensions` lists every Token-2022 extension with null/false when absent; only non-null values count. pump.fun now mints Token-2022 with metadataPointer, which is benign.
- RugCheck `insiderNetworks[].tokenAmount` is in base units.
- GeckoTerminal answers 429 without CORS headers; the browser sees "Failed to fetch". The collector paces and retries.
- GeckoTerminal trades: when the memecoin is the quote side of a pool, price_from/price_to flip; the normalizer picks the side closest to the reference price.
- Only candles/trades from the token's own pools are used; the normalizer filters by pool id.
- Jupiter `priceImpactPct` is a fraction (0.0186 = 1.86%).
- Holder counts differ across providers (RugCheck counts all accounts, Jupiter/GeckoTerminal filter); the report records the discrepancy rather than choosing.

## Evidence discipline

Every report keeps FACT / INFERENCE / HEURISTIC / UNKNOWN separate. Never promote an inference. Never fabricate missing data; write UNABLE TO DETERMINE. A fatal flag overrides the score. Write "what would make this token unacceptable" before deep research.

## Catalyst Intelligence pass (event-first and token-first)

Run after discovery in the daily run and after the watchlist refresh:
1. `python -m memelab catalyst plan --id cat_<stamp> --verify-traders` prints the fetch-mode `__ML.run` call and the navigate-mode URL list. In the example.com tab load collector.js then `bridge/catalyst.js`, run the fetch plan, ship `inbox/cat_<stamp>.json`. For each navigate URL: navigate the tab there, eval catalyst.js (on Google News CSP forbids eval, so parse inline with the same DOM code), build `{_cat, _kind, _url, _at, s, err, body}`, ship it as `inbox/cat_<stamp>_<source>.json`. Pull all of them and merge into one result (cli `_merged` or `catalyst save-page`).
2. `python -m memelab catalyst ingest --results cat_<stamp>`; then `catalyst match-plan --id catm_<stamp>` (run the term searches in the tab, slim ds_search bodies to solana pairs before shipping), `catalyst match --results catm_<stamp>`.
3. Deep-fetch the MODERATE/STRONG linked memecoins (deepPlan plus `rug:`/`jup_tok:`/`ds:` by mint), then `catalyst assess --results <deep ids> catm_<stamp> --persist`, `catalyst monitor`, `catalyst report`.
4. Verify trader identities from the full profile HTML (the collector truncates text bodies): a 404 means NOT_FOUND; disable the source and ask for a replacement handle.
Rules: evidence status comes from source tier, never tone; a trending story with no verified mint stays an event record; WEAK/THEMATIC links never alert; UNKNOWN never improves a score; a fatal core check rejects regardless of catalyst strength.


## Multi-chain ecosystem pass (runs FIRST in the daily scan)

The system is chain-agnostic. Solana is one chain; never start from the assumption that it is the best place to look. Order: regime -> chain rotation -> narratives -> discovery on the chains the allocation favours -> structural -> deep -> cross-chain ranking.

1. Ecosystem inputs: `python -m memelab chains plan eco --id eco_<stamp>` (56 requests: CoinGecko charts/global/categories/meme markets, DefiLlama DEX/TVL/stablecoins, Hyperliquid funding, GeckoTerminal per-network and cross-network pools, DEX Screener boosts/profiles). In the example.com tab load `bridge/collector.js` then `bridge/chains.js`, `__ML.start(plan)`, poll, `__ML.ship("inbox/eco_<stamp>.json")`, commit, pull. Then `python -m memelab chains eco --results eco_<stamp>` writes `*_ECOSYSTEM.md` (regime, SOI table with components and FACT/INFERENCE/CONFIDENCE statements, narratives with lifecycle, benchmark basket, launchpads, emerging chains, de-emphasis). CoinGecko is paced at 2.4 s and still answers network errors on bursts: re-fetch any `cg_*` key that failed before shipping.
2. Research allocation: read `chains.research_allocation` (FULL / PARTIAL / WATCHLIST). Run discovery on FULL chains with 2 pages, PARTIAL with 1 page, WATCHLIST chains only refresh existing watchlist tokens. Tier-1 chains never drop below WATCHLIST; an open thesis on a cooling chain keeps refreshing.
3. EVM discovery per chain: `chains plan disc <chain>`, run, ship, pull, `chains discover <chain> <id> --results <ids>` (meme filter excludes majors, stables, LSTs, tokenized stocks, DeFi governance tokens, Backed bStocks `0xb2000...` addresses, FDV >= $2B). Stage 2: `chains plan struct <chain> <id>` (DEX Screener batch, GoPlus ONE address per call, honeypot.is per token), run, ship, pull, `chains struct <id> --results <ids>` (fatal contract checks, live owner with dangerous functions, holder concentration from GoPlus with pool/locked/burn holders removed, liquidity = max(DS, GT) with the discrepancy recorded). Deep: build with `__ML.evmDeepPlan(id, chain, cfg, tokens, nativePrice)` from chains.js (cfg from `chains.plan.js_cfg(chain)`), run (about 30 requests per token: GT info/pools/ohlcv/trades, GoPlus, honeypot.is, DS, 16 KyberSwap quotes, 4 eth_calls), ship, pull.
4. Cross-chain report: `python -m memelab chains scout --tokens chain:addr ... --results <all ids> --eco eco_<stamp> --account-size X [--max-loss-pct 2]`. Output `*_SCOUT_MULTICHAIN.md`: ecosystem sections, then BEST CROSS-CHAIN OPPORTUNITIES (<= 5, any chain mix, fewer is fine), correlation-aware allocation (same chain + same narrative share one budget; regime multiplier), NEAR MISSES, REJECTED AFTER DUE DILIGENCE. Each token line carries CHAIN / CONTRACT / TOKEN STANDARD / PRIMARY POOL / IDENTITY CONFIDENCE, execution friction (gas + taxes + route legs) and cross-chain RS vs chain memes, global basket (same cap bucket) and native coin. Tokens whose data is older than the ecosystem snapshot are marked DATA AGE / STALE.
5. Single EVM token: `python -m memelab chains analyze <chain> <0x...> --results <ids>`. Require chain + contract; a ticker is never an identity.

Chain-specific facts learned from live testing (2026-10-07): GoPlus multi-address batches answer only the first address and rate limits come back as HTTP 200 with code 4029 (collector maps that to 429 and retries); honeypot.is returns 404 for tokens whose main pool is PancakeSwap Infinity/V3 or Uniswap V4 (simulation UNKNOWN, GoPlus static checks still apply); DEX Screener does not index some Infinity/V4 pools so its liquidity can read near zero where GeckoTerminal shows millions; concentrated-liquidity LP positions are NFTs, so GoPlus lp_holders "locked %" understates removable liquidity and LP risk reads HIGH unless the position NFT is locked; Kyber quote impact includes fees (1 - amountOutUsd/amountInUsd). The catalyst news feeds skew to Solana until the Base/BNB queries have a week of history, so the attention component of SOI is biased for now and says so.

## Pre-launch & new-launch pass: "Find upcoming memecoins" (runs before the normal pipeline)

1. `python -m memelab launch plan --id lp_<stamp>` writes three plan groups. Open a tab on `https://frontend-api-v3.pump.fun/coins?offset=0&limit=1`, load collector.js, chains.js and launch.js from the repo (`(0,eval)(await fetch(raw).then(r=>r.text()))`), run the `_ex` and `_pump` requests together there (CORS-open APIs work from that origin), ship as `inbox/lp_<stamp>_pump.json`. Open a tab on `https://www.clanker.world/api/tokens`, load the same scripts, run `_clanker`, ship. Commit both, pull.
2. `python -m memelab launch discover --results lp_<stamp>` -> shortlist file `lp_<stamp>.launch_short.json` (up to 14 fresh launches plus every launch already tracked in an active status).
3. `python -m memelab launch deep-plan lp_<stamp> --id ld_<stamp>`; run the groups the same way (creator history, coins-v2, RugCheck report, Jupiter search, token pools, early trades, minute candles, EVM GoPlus/honeypot.is); ship, commit, pull.
4. `python -m memelab launch assess lp_<stamp> --results lp_<stamp> ld_<stamp>` writes `data/reports/launch_<stamp>.md` (PRE-LAUNCH MARKET ENVIRONMENT, BEST UPCOMING CANDIDATES <= 5, other launches, alerts, UPCOMING_LAUNCHES, hand-overs, rejected records, data gaps).
5. Daily: `launch cohort-plan` -> run in the pump.fun tab -> `launch cohort --results lc_<stamp>_pump` so launchpad statistics and comparables keep growing. `launch status` lists tracked launches; `launch note --project ... --symbol ... --when ...` records an announced launch (state A, CLAIMED).
Rules: no BUY status exists here; before trading there is no executable depth; planned liquidity, valuations and team claims are PROJECTED or CLAIMED until observed; a state A token is CONTRACT NOT YET VERIFIED and any earlier token with that name is an impersonation risk; prefer "this launch is interesting, watch it" over any urgency to buy early.
