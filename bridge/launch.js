// memelab launch projections. Define AFTER collector.js (extends __ML.PROJ). Pump.fun and Clanker answer only same-origin requests:
// run their plan groups from a tab opened on https://frontend-api-v3.pump.fun/coins?limit=1 or https://www.clanker.world/api/tokens
// (load collector.js + launch.js there by eval of the fetched text; raw.githubusercontent.com allows CORS).
(() => {
  const P = window.__ML.PROJ, N = window.__ML.N;
  const pick = (o, keys) => { const r = {}; for (const k of keys) if (o && o[k] !== undefined && o[k] !== null) r[k] = o[k]; return r; };
  const pumpRow = (c) => ({ ...pick(c, ["mint", "name", "symbol", "creator", "created_timestamp", "complete", "usd_market_cap", "market_cap", "ath_market_cap", "ath_market_cap_timestamp",
      "real_sol_reserves", "real_token_reserves", "virtual_sol_reserves", "virtual_token_reserves", "total_supply", "base_decimals", "pool_address", "last_trade_timestamp",
      "reply_count", "is_currently_live", "twitter", "telegram", "website", "token_program", "transfer_fee_bps", "transfer_hook_program", "is_banned", "nsfw", "verified", "protocol", "quote_mint", "program", "bonding_curve", "associated_bonding_curve"]) });
  Object.assign(P, {
    pump_coins: (j) => (Array.isArray(j) ? j : (j.coins || [j])).map(pumpRow),
    pump_coin: (j) => pumpRow(j),
    ray_list: (j) => ((j.data || {}).rows || []).map(r => ({ ...pick(r, ["mint", "poolId", "creator", "createAt", "name", "symbol", "decimals", "supply", "marketCap", "volumeU", "finishingRate", "initPrice", "endPrice",
        "totalLockedAmount", "cliffPeriod", "unlockPeriod", "startTime", "totalAllocatedShare", "totalSellA", "totalFundRaisingB", "migrateType", "mintProgramA", "transferFeeBasePoints", "twitter", "telegram", "website"]),
        platform: (() => { try { return JSON.parse(r.platformInfo || "{}").name } catch { return (r.platformInfo || {}).name } })(), quote: (r.mintB || {}).symbol || r.mintB })),
    clanker_list: (j) => (j.data || []).map(t => ({ ...pick(t, ["contract_address", "name", "symbol", "created_at", "deployed_at", "admin", "msg_sender", "supply", "pool_address", "type", "pair", "chain_id", "locker_address", "starting_market_cap", "warnings", "tags"]),
        social: (t.socialLinks || []).slice(0, 4), ext: t.extensions ? { sniperTax: t.extensions.sniperTax, vault: t.extensions.vault, airdrop: t.extensions.airdrop, devBuy: t.extensions.devBuy, fees: t.extensions.fees ? { type: t.extensions.fees.type, clankerFee: t.extensions.fees.clankerFee, pairedFee: t.extensions.fees.pairedFee } : undefined } : undefined,
        mkt: (t.related || {}).market })),
    zora_new: (j) => (((j.exploreList || {}).edges) || []).map(e => { const n = e.node || {}; return { ...pick(n, ["name", "symbol", "address", "coinType", "totalSupply", "totalVolume", "volume24h", "createdAt", "creatorAddress", "marketCap", "marketCapDelta24h", "uniqueHolders", "chainId"]), creator: (n.creatorProfile || {}).handle }; }),
    virt_gen: (j) => (j.data || []).map(g => ({ ...pick(g, ["id", "status", "genesisId", "genesisAddress", "startsAt", "endsAt", "totalParticipants", "totalVirtuals"]),
        v: pick(g.virtual || {}, ["chain", "name", "symbol", "tokenAddress", "preToken", "lpCreatedAt"]), socials: g.virtual && g.virtual.socials ? Object.keys(g.virtual.socials) : [] })),
  });
  return "launch projections ready";
})();
