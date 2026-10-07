// memelab multi-chain projections. Define AFTER collector.js: extends __ML.PROJ with EVM / ecosystem sources.
// Keys (plan.py chains): goplus:<chain>:<addr>, hp:<chain>:<addr>, kq:<chain>:BUY|SELL:<usd>:<addr>, rpc_evm:<chain>:<what>:<addr>,
// llama_dex:<chain>, llama_chains, llama_stables, cg_cat, cg_mkts:<category>:<page>, cg_chart:<id>, cg_global, hl_meta, gt_nets, gt_xnet:<page>,
// gt_pools:<network>:... (shared with the Solana collector; poolProj now strips any network prefix), ds:<chain>:..., ds_boosts.
(() => {
  const P = window.__ML.PROJ, N = window.__ML.N;
  const pick = (o, keys) => { const r = {}; for (const k of keys) if (o && o[k] !== undefined) r[k] = o[k]; return r; };
  const daily = (pairs) => { // CoinGecko market_chart: keep one point per UTC day (last of the day)
    const out = {}; for (const [ts, v] of pairs || []) out[Math.floor(ts / 86400000)] = [ts, N(v, 7)]; return Object.values(out);
  };
  Object.assign(P, {
    goplus: (j) => { if (j.code !== undefined && j.code !== 1) return { _rateLimited: true, code: j.code, message: j.message }; /* GoPlus rate limit answers HTTP 200 with code 4029 */ const res = j.result || {}; const out = {}; for (const [addr, t] of Object.entries(res)) {
      out[addr.toLowerCase()] = { ...pick(t, ["token_name", "token_symbol", "total_supply", "holder_count", "lp_holder_count", "lp_total_supply", "creator_address", "creator_percent", "creator_balance", "owner_address", "owner_percent", "owner_balance", "owner_change_balance",
        "is_open_source", "is_proxy", "is_mintable", "can_take_back_ownership", "hidden_owner", "selfdestruct", "external_call", "buy_tax", "sell_tax", "transfer_tax", "cannot_buy", "cannot_sell_all", "slippage_modifiable", "is_honeypot", "honeypot_with_same_creator",
        "transfer_pausable", "is_blacklisted", "is_whitelisted", "is_anti_whale", "anti_whale_modifiable", "trading_cooldown", "personal_slippage_modifiable", "is_in_dex", "is_airdrop_scam", "trust_list", "other_potential_risks", "note", "gas_abuse", "is_in_cex"]),
        dex: (t.dex || []).slice(0, 6).map(d => pick(d, ["name", "liquidity_type", "liquidity", "pair"])),
        holders: (t.holders || []).slice(0, 25).map(h => pick(h, ["address", "tag", "is_contract", "balance", "percent", "is_locked"])),
        lp_holders: (t.lp_holders || []).slice(0, 12).map(h => ({ ...pick(h, ["address", "tag", "is_contract", "balance", "percent", "is_locked", "NFT_list"]), locked_detail: (h.locked_detail || []).slice(0, 3) })) }; }
      return out; },
    hp: (j) => ({ ...pick(j, ["honeypotResult", "simulationSuccess", "simulationError", "flags", "chain"]), token: pick(j.token || {}, ["name", "symbol", "decimals", "address", "totalHolders"]), withToken: pick(j.withToken || {}, ["symbol", "address"]),
      pair: j.pair ? { ...pick(j.pair.pair || {}, ["name", "address", "type"]), liquidity: N(j.pair.liquidity), reserves0: j.pair.reserves0, reserves1: j.pair.reserves1 } : undefined,
      sim: pick(j.simulationResult || {}, ["buyTax", "sellTax", "transferTax", "buyGas", "sellGas", "maxBuy", "maxSell"]), risk: (j.summary || {}).risk, riskLevel: (j.summary || {}).riskLevel, contract: pick(j.contractCode || {}, ["openSource", "rootOpenSource", "isProxy", "hasProxyCalls"]) }),
    kq: (j) => { const r = (j.data || {}).routeSummary; if (!r) return { error: j.message || j.error || "no route", code: j.code };
      return { tokenIn: r.tokenIn, tokenOut: r.tokenOut, amountIn: r.amountIn, amountOut: r.amountOut, amountInUsd: N(r.amountInUsd), amountOutUsd: N(r.amountOutUsd), gasUsd: N(r.gasUsd, 5), gas: r.gas, gasPrice: r.gasPrice,
        route: (r.route || []).map(path => path.map(h => [h.pool, h.exchange, h.poolType, h.tokenIn, h.tokenOut, h.swapAmount, h.amountOut])) }; },
    rpc_evm: (j) => j,
    llama_dex: (j) => ({ ...pick(j, ["total24h", "total48hto24h", "total7d", "total30d", "change_1d", "change_7d", "change_1m", "change_7dover7d", "change_30dover30d"]),
      chart: (j.totalDataChart || []).slice(-60).map(([ts, v]) => [ts, N(v, 7)]), protocols: (j.protocols || []).sort((a, b) => (b.total24h || 0) - (a.total24h || 0)).slice(0, 12).map(p => [p.name, N(p.total24h, 6), N(p.change_7d, 4)]) }),
    llama_chains: (j) => (j || []).map(c => [c.name, N(c.tvl, 7), c.tokenSymbol, c.chainId]),
    llama_stables: (j) => (j || []).map(c => [c.name, N((c.totalCirculatingUSD || {}).peggedUSD, 7)]),
    cg_cat: (j) => (j || []).map(c => pick(c, ["id", "name", "market_cap", "market_cap_change_24h", "volume_24h", "top_3_coins_id", "updated_at"])),
    cg_mkts: (j) => (j || []).map(c => ({ ...pick(c, ["id", "symbol", "name", "current_price", "market_cap", "market_cap_rank", "fully_diluted_valuation", "total_volume", "price_change_percentage_24h", "ath_change_percentage", "ath_date"]),
      p7d: N(c.price_change_percentage_7d_in_currency, 5), p1h: N(c.price_change_percentage_1h_in_currency, 5), p30d: N(c.price_change_percentage_30d_in_currency, 5) })),
    cg_chart: (j) => ({ prices: daily(j.prices), volumes: daily(j.total_volumes), mcaps: daily(j.market_caps) }),
    cg_global: (j) => { const d = j.data || {}; return { total_mcap: N((d.total_market_cap || {}).usd, 7), total_vol: N((d.total_volume || {}).usd, 7), btc_dom: N((d.market_cap_percentage || {}).btc, 5), eth_dom: N((d.market_cap_percentage || {}).eth, 5), mcap_chg_24h: N(d.market_cap_change_percentage_24h_usd, 5), active: d.active_cryptocurrencies, updated: d.updated_at }; },
    hl_meta: (j) => { const [meta, ctxs] = Array.isArray(j) ? j : [j.meta, j.ctxs]; const want = new Set(["BTC", "ETH", "SOL", "BNB", "HYPE", "DOGE", "WIF", "PEPE", "BONK", "FARTCOIN", "TRUMP", "PENGU", "SUI", "AVAX", "ARB"]); const out = {};
      ((meta || {}).universe || []).forEach((u, i) => { if (want.has(u.name) && ctxs && ctxs[i]) { const c = ctxs[i]; out[u.name] = { funding: N(c.funding, 5), oi: N(c.openInterest, 7), dayVlm: N(c.dayNtlVlm, 7), mark: N(c.markPx, 7), prevDay: N(c.prevDayPx, 7), premium: N(c.premium, 5) }; } });
      return out; },
    gt_nets: (j) => (j.data || []).map(n => [n.id, (n.attributes || {}).name]),
    gt_xnet: (j) => ({ pools: (j.data || []).map(p => { const a = p.attributes || {}, rel = p.relationships || {}, tx = a.transactions || {}, v = a.volume_usd || {}, c = a.price_change_percentage || {};
        return { pool: a.address, name: a.name, net: rel.network?.data?.id, dex: rel.dex?.data?.id, created: a.pool_created_at, base: (rel.base_token?.data?.id || "").replace(/^[a-z0-9-]+_/, ""), price: N(a.base_token_price_usd), fdv: N(a.fdv_usd), mcap: N(a.market_cap_usd), reserve: N(a.reserve_in_usd),
          chg: { h1: N(c.h1, 5), h6: N(c.h6, 5), h24: N(c.h24, 5) }, tx: { h24: tx.h24 ? [tx.h24.buys, tx.h24.sells, tx.h24.buyers, tx.h24.sellers] : null, h1: tx.h1 ? [tx.h1.buys, tx.h1.sells, tx.h1.buyers, tx.h1.sellers] : null }, vol: { h1: N(v.h1), h6: N(v.h6), h24: N(v.h24) } }; }),
      networks: (j.included || []).filter(x => x.type === "network").map(x => [x.id, (x.attributes || {}).name]) }),
    ds_boosts: (j) => (j || []).map(p => pick(p, ["chainId", "tokenAddress", "amount", "totalAmount"])),
  });
  // EVM deep-plan builder mirroring memelab/chains/plan.py evm_deep(). tokens: [[addr, mainPool, decimals, priceUsd, liqUsd], ...]
  function evmDeepPlan(id, chain, cfg, tokens, nativePrice, opts = {}) {
    const GT = `https://api.geckoterminal.com/api/v2/networks/${cfg.gt}`; const tfs = opts.tfs || [["day", 1, 120], ["hour", 1, 300], ["minute", 15, 200]];
    let sizesAll = opts.sizes || [500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]; const reqs = [];
    for (const [addr, pool, dec, price, liq] of tokens) {
      let sizes = sizesAll; if (liq && liq < 100000) sizes = sizes.filter(s => s <= 25000); else if (liq && liq < 400000) sizes = sizes.filter(s => s <= 50000);
      reqs.push({ key: `gt_info:${addr}`, url: `${GT}/tokens/${addr}/info` }, { key: `gt_pools:token:${addr}`, url: `${GT}/tokens/${addr}/pools?page=1` });
      if (pool) { for (const [tf, agg, lim] of tfs) reqs.push({ key: `gt_ohlcv:${pool}:${tf}${agg}`, url: `${GT}/pools/${pool}/ohlcv/${tf}?aggregate=${agg}&limit=${lim}&currency=usd&token=${addr}` });
        reqs.push({ key: `gt_trades:${pool}:all`, url: `${GT}/pools/${pool}/trades` }, { key: `gt_trades:${pool}:big`, url: `${GT}/pools/${pool}/trades?trade_volume_in_usd_greater_than=2000` }); }
      if (cfg.goplus) reqs.push({ key: `goplus:${chain}:${addr}`, url: `https://api.gopluslabs.io/api/v1/token_security/${cfg.goplus}?contract_addresses=${addr}` });
      if (cfg.chainId) reqs.push({ key: `hp:${chain}:${addr}`, url: `https://api.honeypot.is/v2/IsHoneypot?address=${addr}&chainID=${cfg.chainId}` });
      if (cfg.kyber && nativePrice && price) for (const usd of sizes) {
        const inWei = BigInt(Math.round(usd / nativePrice * 1e6)) * 10n ** 12n, base = BigInt(Math.round(usd / price * 1e6)) * 10n ** BigInt(Math.max(dec - 6, 0));
        reqs.push({ key: `kq:${chain}:BUY:${usd}:${addr}`, url: `https://aggregator-api.kyberswap.com/${cfg.kyber}/api/v1/routes?tokenIn=${cfg.wnative}&tokenOut=${addr}&amountIn=${inWei}` },
                  { key: `kq:${chain}:SELL:${usd}:${addr}`, url: `https://aggregator-api.kyberswap.com/${cfg.kyber}/api/v1/routes?tokenIn=${addr}&tokenOut=${cfg.wnative}&amountIn=${base}` }); }
      if (cfg.rpc) { const call = (data, what) => ({ key: `rpc_evm:${chain}:${what}:${addr}`, url: cfg.rpc, method: "POST", body: { jsonrpc: "2.0", id: 1, method: "eth_call", params: [{ to: addr, data }, "latest"] } });
        reqs.push(call("0x18160ddd", "totalSupply"), call("0x313ce567", "decimals"), call("0x8da5cb5b", "owner"), { key: `rpc_evm:${chain}:code:${addr}`, url: cfg.rpc, method: "POST", body: { jsonrpc: "2.0", id: 1, method: "eth_getCode", params: [addr, "latest"] } }); }
    }
    return { id, reqs };
  }
  window.__ML.evmDeepPlan = evmDeepPlan;
  return "chains projections ready";
})();
