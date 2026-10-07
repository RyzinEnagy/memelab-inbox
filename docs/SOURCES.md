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
