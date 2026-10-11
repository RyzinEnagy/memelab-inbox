# Data source inventory (verified 2026-10-06)

## Transport reality

The Cowork cloud sandbox cannot reach any crypto data host (egress policy returns 403 on CONNECT for
api.dexscreener.com, api.geckoterminal.com, lite-api.jup.ag, api.rugcheck.xyz, api.coingecko.com,
public-api.birdeye.so, api.mainnet-beta.solana.com, pro-api.solscan.io and others). WebFetch reaches them
but passes the response through a summarizer, so raw JSON is lost.

What does work: fetch() executed inside a Chrome tab (Claude in Chrome extension) against hosts that allow
cross-origin requests, with results rendered into the page body and read back whole with get_page_text.
This is the "browser bridge" in memelab/bridge/. Per-call JS return values truncate near 1,000 characters,
page text does not (31 KB+ read intact).

## Reachable from the browser bridge (no key)

| Source | Endpoint family | What it supplies | Tier |
|---|---|---|---|
| Jupiter lite-api | /swap/v1/quote | Executable quotes, route plan, priceImpactPct, per-pool split. Buy and sell separately. | execution quote |
| Jupiter lite-api | /tokens/v2/search?query=MINT | dev wallet, launchpad, graduatedPool, circ/total supply, tokenProgram, holderCount, stats5m/1h/6h/24h incl. organic vs total volume, numNetBuyers, audit flags (mint/freeze disabled, topHoldersPercentage, devBalancePercentage), organicScore | structured market data |
| Jupiter lite-api | /tokens/v2/recent, /tokens/v2/toptrending/{interval}, /tokens/v2/toporganicscore/{interval}, /tokens/v2/toptraded/{interval} | Discovery universe | discovery input |
| Jupiter lite-api | /price/v3?ids= | Price cross-check | structured market data |
| DEX Screener | /tokens/v1/solana/{mints} (up to 30), /latest/dex/search, /token-profiles/latest/v1, /token-boosts/top/v1 | Pairs per token, liquidity usd/base/quote, txns buys/sells, volume, priceChange, pairCreatedAt, socials/website | structured market data |
| GeckoTerminal | /networks/solana/tokens/{mint}/info | holders count + distribution (top10, 11-20, 21-40, rest), mint/freeze authority flags, developer address and holding pct, gt_score, launchpad graduation | analytics |
| GeckoTerminal | /networks/solana/tokens/{mint}/pools | all pools for a token with reserve, volume, txns per window | structured market data |
| GeckoTerminal | /networks/solana/pools/{pool}/ohlcv/{day,hour,minute}?aggregate=&limit=1000&before_timestamp= | Candles for price structure | structured market data |
| GeckoTerminal | /networks/solana/pools/{pool}/trades?trade_volume_in_usd_greater_than= | Last 300 trades with tx_from_address, kind, amounts, usd | on-chain derived |
| GeckoTerminal | /networks/solana/trending_pools, /new_pools, /pools (sorted) | Discovery universe | discovery input |
| RugCheck | /v1/tokens/{mint}/report | mintAuthority, freezeAuthority, token_extensions (Token-2022), tokenMeta mutability/updateAuthority, topHolders with owner and insider flag, markets with LP lock pct and LP holders, lockers, risks, insiderNetworks, transferFee, creator, totalHolders | on-chain derived + scanner |
| RugCheck | /v1/stats/new_tokens, /v1/stats/trending, /v1/stats/recent | Discovery universe | discovery input |
| CoinGecko public | /api/v3/simple/price, /api/v3/coins/markets | SOL and broad-market benchmark for relative strength | structured market data |
| Solana RPC (PublicNode) | https://solana-rpc.publicnode.com | getAccountInfo (jsonParsed mint and token accounts), getSignaturesForAddress, getTransaction. getTokenLargestAccounts is rate limited (429). | primary on-chain |

## Blocked from the browser bridge (CORS or origin policy)

- api.mainnet-beta.solana.com (403 to browser origin), rpc.ankr.com (key required), solana.drpc.org (chain unavailable), Alchemy demo (CORS)
- frontend-api-v3.pump.fun (CORS), api.solana.fm (CORS), reddit.com JSON (CORS), api.x.com (auth)
- Birdeye public API (401, key required)
- Solscan pro API (key required)

## Would materially improve the system (needs a key; stop point for the user)

1. Helius (free tier exists): full-rate RPC, DAS getAsset/getTokenAccounts (complete holder list), Enhanced Transactions API (parsed swaps, transfers, funding source tracing). Unlocks Phase 6-8 wallet forensics at scale.
2. Birdeye (free tier exists): wallet PnL, token holder history, trader leaderboards. Partial substitute for Helius on holder analytics.
3. X/Twitter API (paid) or a social-listening service: mention velocity and unique accounts. Without it, attention analysis uses proxies (DexScreener boosts/profiles, GeckoTerminal info social links, holder growth, Jupiter organic score) plus manual browser reads of public X search pages.

## Source precedence used by the modules

1. Direct on-chain (RPC getAccountInfo for mint authorities and extensions) when fetched
2. Jupiter quotes for anything about execution
3. RugCheck report fields that are direct account reads (authorities, LP holders, top holders)
4. Jupiter token search and DEX Screener for market structure
5. GeckoTerminal analytics fields (gt_score, holder distribution)
6. Social/community claims

When sources disagree the discrepancy is recorded in the snapshot, not resolved by picking the favorable number.

## Catalyst Intelligence sources (verified 2026-10-07)

Access modes from the browser bridge. Nothing below is reachable from the sandbox.

| Source | Mode | Tier | Notes |
|---|---|---|---|
| CoinGecko /search/trending | fetch | aggregator | trending coins and categories; cross-chain, so matches need a Solana mint check |
| DEX Screener token-profiles, token-boosts | fetch | aggregator | PAID placements; recorded as promotion signal, never as organic attention |
| Polymarket gamma /events | fetch | aggregator | scheduled and political/cultural events with market-implied odds; sports fixtures and price-threshold markets filtered out |
| Coinbase /currencies, Kraken /Assets | fetch | official | asset lists; consecutive snapshots are diffed to detect ACCESS changes |
| Binance CMS announcements | navigate | official | CORS-blocked; read by navigating the tab and parsing the JSON document |
| Cointelegraph, CoinDesk, Decrypt, The Block RSS | navigate | reputable | CORS-blocked; XML documents parsed in place |
| Google News RSS (query feeds) | navigate | aggregator | 100 items per query with publisher names; CSP forbids eval on this origin, so parse inline |
| Bybit, OKX announcement APIs | navigate | official | Bybit returned a non-JSON challenge page on 2026-10-07; OKX untested |
| X profile pages | fetch | social | identity verification only (page title; bio not collected, D-020); timelines need a logged-in Chrome profile |
| X timelines, Reddit, TikTok, Instagram | blocked / manual | social | coverage gaps recorded per source in catalyst_sources.coverage_gap |

Trader research list (identity checked from public profile pages on 2026-10-07): @rasmr_eth, @Rewkang, @thedefivillain, @0xSisyphus, @blknoiz06 VERIFIED; @redphonecrypto NOT FOUND (404) and disabled pending a replacement handle. These are research sources, not certified profitable traders.

## Multi-chain sources (verified from the browser bridge 2026-10-07)

Working with plain fetch (CORS open): DefiLlama `api.llama.fi/overview/dexs/{chain}` (daily DEX volume chart), `/v2/chains` (TVL), `stablecoins.llama.fi/stablecoinchains`; CoinGecko `/coins/categories`, `/coins/markets?category=...` (existing meme categories: meme-token, solana-meme-coins, base-meme-coins, four-meme-ecosystem (BNB), sui-meme, ai-meme-coins, tiktok-meme, chinese-meme ...; there is NO ethereum or avalanche meme category), `/global`, `/coins/{id}/market_chart`; GoPlus `api.gopluslabs.io/api/v1/token_security/{chainId}?contract_addresses=` (ONE address per call: the comma list answers only the first on the free tier; rate limit answers HTTP 200 with code 4029, paced at 2.3s); honeypot.is `v2/IsHoneypot?address=&chainID=` (404 for pools on PancakeSwap Infinity / V3 and Uniswap V4: simulation UNKNOWN there); KyberSwap `aggregator-api.kyberswap.com/{base|bsc|ethereum|...}/api/v1/routes` (quotes with amountInUsd/amountOutUsd/gasUsd); Hyperliquid `api.hyperliquid.xyz/info` POST metaAndAssetCtxs (funding/OI); GeckoTerminal per-network `trending_pools`, `new_pools`, `pools?sort=`, `tokens/{addr}/info|pools`, `pools/{pool}/ohlcv|trades`, cross-network `/networks/trending_pools?include=network`, `/networks`; PublicNode EVM RPCs (base, bsc, ethereum, arbitrum, avalanche, polygon); DEX Screener `tokens/v1/{chain}/{addrs}` (does not index every PancakeSwap Infinity / Uniswap V4 pool: liquidity can read near zero where GeckoTerminal shows millions; the system keeps the larger figure and records the discrepancy), `token-boosts`, `token-profiles`.

Blocked or failed: Odos (CORS), Sui fullnode (CORS), OpenOcean (403), Binance futures API (CORS), bsc-dataseed.binance.org, four.meme, clanker.world, basescan free V1 API (deprecated). HyperEVM and Sui therefore have market-level data only: contract risk and executable depth stay UNKNOWN for tokens there.

Google News catalyst feeds now include Base, BNB and chain-rotation queries so chain attention stops skewing to Solana after a week of runs.

## Launch sources (verified from the browser bridge 2026-10-08)

Plain fetch: Jupiter `tokens/v2/recent` (first pool just created, launchpad, dev, audit, stats), RugCheck `stats/new_tokens` and `/tokens/{mint}/report`, Raydium LaunchLab `launch-mint-v1.raydium.io/get/list?sort=new|marketCap` and `get/by/user?wallet=` (supply, curve progress, locked/vesting amounts, cliff/unlock, platform such as Bonk.fun), Zora `api-sdk.zora.engineering/explore?listType=NEW`, Virtuals `api.virtuals.io/api/geneses` (scheduled starts; on 2026-10-08 every recent Genesis was CANCELLED or FINALIZED), GeckoTerminal `new_pools` per network and `/networks/solana/dexes/pumpswap/pools`, DEX Screener token-profiles/boosts (paid).
Same-origin only (run from a tab opened on that host): pump.fun `frontend-api-v3.pump.fun/coins?sort=created_timestamp|market_cap|last_trade_timestamp&complete=`, `/coins/currently-live`, `/coins?creator=`, `/coins-v2/{mint}`; Clanker `www.clanker.world/api/tokens?sort=desc&page=` and `/api/tokens/fetch-deployed-by-address?address=`.
Not available: Clanker from the home-computer network (connection reset on 2026-10-08; the plan group stays in place for when it answers), four.meme (access restricted from the user's location; not circumvented; BNB launches appear only once they reach PancakeSwap), Moonshot, Meteora DBC, Believe, CryptoRank / CoinMarketCap / CoinMarketCal calendars, CoinGecko new-coins list (401), X / Telegram / Discord.
