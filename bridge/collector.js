// memelab browser-bridge collector.
// Define once per page with the javascript_tool, then call:  await __ML.run(PLAN)
// PLAN = {id:"...", reqs:[{key, url, method?, body?, proj?}]}
// Results are rendered into <pre id="ml"> so get_page_text returns them whole.
(() => {
  const N = (x, p = 8) => { if (x === null || x === undefined || x === "") return null; const v = Number(x); return Number.isFinite(v) ? Number(v.toPrecision(p)) : null; };
  const pick = (o, keys) => { const r = {}; for (const k of keys) if (o && o[k] !== undefined) r[k] = o[k]; return r; };

  const poolProj = (p) => {
    const a = p.attributes || {}, rel = p.relationships || {};
    const tx = a.transactions || {}, v = a.volume_usd || {}, c = a.price_change_percentage || {};
    const t = (w) => tx[w] ? [tx[w].buys, tx[w].sells, tx[w].buyers, tx[w].sellers] : null;
    return {
      pool: a.address, name: a.name, dex: rel.dex?.data?.id, created: a.pool_created_at,
      base: (rel.base_token?.data?.id || "").replace("solana_", ""),
      quote: (rel.quote_token?.data?.id || "").replace("solana_", ""),
      price: N(a.base_token_price_usd), price_native: N(a.base_token_price_native_currency),
      fdv: N(a.fdv_usd), mcap: N(a.market_cap_usd), reserve: N(a.reserve_in_usd),
      chg: { m5: N(c.m5, 5), h1: N(c.h1, 5), h6: N(c.h6, 5), h24: N(c.h24, 5) },
      tx: { m5: t("m5"), h1: t("h1"), h6: t("h6"), h24: t("h24") },
      vol: { m5: N(v.m5), h1: N(v.h1), h6: N(v.h6), h24: N(v.h24) },
    };
  };

  const PROJ = {
    gt_pools: (j) => ({ pools: (j.data || []).map(poolProj) }),
    gt_info: (j) => { const a = (j.data || {}).attributes || {}; delete a.image; delete a.image_url; delete a.banner_image_url; return a; },
    gt_ohlcv: (j) => ({ ohlcv: ((j.data || {}).attributes || {}).ohlcv_list || [], meta: j.meta }),
    gt_trades: (j) => ({ trades: (j.data || []).map(t => { const a = t.attributes || {}; return [a.block_timestamp, a.tx_from_address, a.kind, N(a.from_token_amount), N(a.to_token_amount), N(a.volume_in_usd), N(a.price_from_in_usd), N(a.price_to_in_usd), (a.tx_hash || "").slice(0, 10)]; }) }),
    rug: (j) => ({
      ...pick(j, ["mint", "tokenProgram", "creator", "creatorBalance", "token", "token_extensions", "tokenMeta", "transferFee", "totalHolders", "totalMarketLiquidity", "totalLPProviders", "score", "score_normalised", "detectedAt", "graphInsidersDetected", "rugged", "freezeAuthority", "mintAuthority"]),
      risks: (j.risks || []).map(r => pick(r, ["name", "level", "score", "value", "description"])),
      topHolders: (j.topHolders || []).map(h => pick(h, ["address", "owner", "pct", "uiAmount", "insider"])),
      insiderNetworks: (j.insiderNetworks || []).map(n => pick(n, ["id", "size", "type", "tokenAmount", "activeAccounts", "wallets"])),
      lockers: j.lockers, lockerOwners: j.lockerOwners,
      markets: (j.markets || []).map(m => ({ ...pick(m, ["pubkey", "marketType", "mintA", "mintB", "mintLP", "liquidityA", "liquidityB"]), lp: m.lp ? { ...pick(m.lp, ["lpLockedPct", "lpLockedUSD", "lpUnlocked", "lpLocked", "lpTotalSupply", "lpCurrentSupply", "basePrice", "quotePrice", "baseUSD", "quoteUSD", "reserveSupply", "currentSupply", "tokenSupply", "lpMaxSupply", "pctSupply", "pctReserve"]), holders: (m.lp.holders || []).slice(0, 8).map(h => pick(h, ["address", "owner", "pct", "uiAmount", "insider"])) } : null })),
    }),
    jup_tok: (j) => (Array.isArray(j) ? j : [j]).map(t => { const c = { ...t }; delete c.icon; return c; }),
    jup_disc: (j) => (Array.isArray(j) ? j : [j]).map(t => {
      const st = (w) => { const s = t["stats" + w]; if (!s) return undefined; return { v: N((s.buyVolume || 0) + (s.sellVolume || 0), 6), o: N((s.buyOrganicVolume || 0) + (s.sellOrganicVolume || 0), 6), nb: s.numNetBuyers, tr: s.numTraders, hc: N(s.holderChange, 4), lc: N(s.liquidityChange, 4), pc: N(s.priceChange, 4), b: s.numBuys, s: s.numSells }; };
      return { id: t.id, symbol: t.symbol, name: t.name, liq: N(t.liquidity, 6), mcap: N(t.mcap, 6), fdv: N(t.fdv, 6), holders: t.holderCount, org: N(t.organicScore, 4), orgL: t.organicScoreLabel,
        lp: t.launchpad, fp: t.firstPool?.createdAt, dev: t.dev, audit: t.audit ? { m: t.audit.mintAuthorityDisabled, f: t.audit.freezeAuthorityDisabled, th: N(t.audit.topHoldersPercentage, 4), dv: N(t.audit.devBalancePercentage, 4) } : undefined,
        s1h: st("1h"), s6h: st("6h"), s24h: st("24h") };
    }),
    jq: (j) => j.error ? { error: j.error, errorCode: j.errorCode } : {
      inMint: j.inputMint, outMint: j.outputMint, inAmount: j.inAmount, outAmount: j.outAmount, impact: N(j.priceImpactPct, 6), usd: N(j.swapUsdValue), slot: j.contextSlot,
      route: (j.routePlan || []).map(r => [r.swapInfo?.ammKey, r.swapInfo?.label, r.percent, r.swapInfo?.inputMint, r.swapInfo?.outputMint, r.swapInfo?.inAmount, r.swapInfo?.outAmount]),
    },
    ds: (j) => (Array.isArray(j) ? j : (j.pairs || [])).map(p => { const c = { ...p }; if (c.info) c.info = pick(c.info, ["websites", "socials"]); delete c.url; return c; }),
    ds_profiles: (j) => (j || []).map(p => pick(p, ["chainId", "tokenAddress", "description", "links", "amount", "totalAmount"])),
    helius_tx: (j) => (Array.isArray(j) ? j : []).map(t => ({ sig: (t.signature || "").slice(0, 12), ts: t.timestamp, type: t.type, src: t.source, fee: t.fee, payer: t.feePayer,
      nt: (t.nativeTransfers || []).filter(x => x.amount >= 1e7).slice(0, 12).map(x => [x.fromUserAccount, x.toUserAccount, N(x.amount / 1e9, 6)]),
      tt: (t.tokenTransfers || []).slice(0, 12).map(x => [x.fromUserAccount, x.toUserAccount, x.mint, N(x.tokenAmount, 8)]) })),
    raw: (j) => j,
  };

  async function one(r) {
    const t0 = performance.now();
    try {
      const init = { method: r.method || "GET", headers: {} };
      if (r.body) { init.headers["Content-Type"] = "application/json"; init.body = typeof r.body === "string" ? r.body : JSON.stringify(r.body); }
      const resp = await fetch(r.url, init);
      const txt = await resp.text();
      let j; try { j = JSON.parse(txt); } catch { j = { _text: txt.slice(0, 2000) }; }
      const projName = r.proj || Object.keys(PROJ).find(k => r.key.startsWith(k)) || "raw";
      let body; try { body = resp.ok ? (PROJ[projName] || PROJ.raw)(j) : j; } catch (e) { body = { _projError: String(e), _raw: txt.slice(0, 1500) }; }
      return [r.key, { s: resp.status, len: txt.length, ms: Math.round(performance.now() - t0), body }];
    } catch (e) {
      return [r.key, { s: 0, err: String(e) }];
    }
  }

  // Per-host pacing: GeckoTerminal free tier allows ~30 calls/min and answers 429 without CORS headers (seen as "Failed to fetch").
  const PACE = { "api.geckoterminal.com": 2600, "api.rugcheck.xyz": 400, "solana-rpc.publicnode.com": 600 };
  const sleep = (ms) => new Promise(res => setTimeout(res, ms));
  async function paced(reqs, out, host, gap) {
    for (const r of reqs) { let [k, v] = await one(r); if (v.s === 0 || v.s === 429) { await sleep(Math.max(gap * 4, 8000)); [k, v] = await one(r); } out[k] = v; await sleep(gap); }
  }
  async function run(plan, conc = 6) {
    const all = plan.reqs.slice(); const prev = plan.merge && window.__ML.last ? JSON.parse(window.__ML.last) : {};
    const out = { ...prev, _plan: plan.id, _at: new Date().toISOString(), _n: all.length + (prev._n || 0) };
    const seen = new Set();
    const dedupe = (k, v) => { if (!plan.dedupe || !v || v.s !== 200 || !Array.isArray(v.body)) return; v.body = v.body.map(t => { if (!t || !t.id) return t; if (seen.has(t.id)) return { id: t.id, symbol: t.symbol, _dup: true }; seen.add(t.id); return t; }); };
    const byHost = {}; const free = [];
    for (const r of all) { const h = new URL(r.url).host; if (PACE[h]) (byHost[h] ||= []).push(r); else free.push(r); }
    const workers = Array.from({ length: Math.min(conc, free.length) }, async () => {
      while (free.length) { const r = free.shift(); const [k, v] = await one(r); out[k] = v; if (r.delayMs) await sleep(r.delayMs); }
    });
    window.__ML.progress = () => `${all.filter(r => out[r.key]).length}/${all.length} done`;
    await Promise.all([...workers, ...Object.entries(byHost).map(([h, rs]) => paced(rs, out, h, PACE[h]))]);
    for (const r of plan.reqs) dedupe(r.key, out[r.key]);
    const s = JSON.stringify(out); window.__ML.last = s;
    document.body.innerHTML = '<pre id="ml" style="white-space:pre-wrap;word-break:break-all"></pre>';
    document.getElementById("ml").textContent = s;
    const ok = Object.values(out).filter(v => v && v.s === 200).length;
    return `rendered ${s.length} chars; ${ok}/${plan.reqs.length} ok`;
  }

  // Deep-plan builder mirroring memelab/bridge/plan.py Plan.deep(). tokens: [[mint, mainPool, decimals, priceUsd, liqUsd], ...]
  const SOL = "So11111111111111111111111111111111111111112", GT = "https://api.geckoterminal.com/api/v2/networks/solana", JUP = "https://lite-api.jup.ag";
  function deepPlan(id, tokens, solPrice, opts = {}) {
    const RPC = opts.rpc || "https://solana-rpc.publicnode.com";
    const tfs = opts.tfs || [["day", 1, 120], ["hour", 1, 300], ["minute", 15, 200]]; let sizesAll = opts.sizes || [500, 1000, 2500, 5000, 10000, 25000, 50000, 100000];
    const reqs = [];
    for (const [mint, pool, dec, price, liq] of tokens) {
      let sizes = sizesAll; if (liq && liq < 100000) sizes = sizes.filter(s => s <= 25000); else if (liq && liq < 400000) sizes = sizes.filter(s => s <= 50000);
      reqs.push({ key: `gt_info:${mint}`, url: `${GT}/tokens/${mint}/info` }, { key: `gt_pools:token:${mint}`, url: `${GT}/tokens/${mint}/pools?page=1` });
      if (pool) { for (const [tf, agg, lim] of tfs) reqs.push({ key: `gt_ohlcv:${pool}:${tf}${agg}`, url: `${GT}/pools/${pool}/ohlcv/${tf}?aggregate=${agg}&limit=${lim}&currency=usd` });
        reqs.push({ key: `gt_trades:${pool}:all`, url: `${GT}/pools/${pool}/trades` }, { key: `gt_trades:${pool}:big`, url: `${GT}/pools/${pool}/trades?trade_volume_in_usd_greater_than=2000` }); }
      for (const usd of sizes) { const lam = Math.round(usd / solPrice * 1e9), base = Math.round(usd / price * 10 ** dec);
        reqs.push({ key: `jq:BUY:${usd}:${mint}`, url: `${JUP}/swap/v1/quote?inputMint=${SOL}&outputMint=${mint}&amount=${lam}&slippageBps=300` }, { key: `jq:SELL:${usd}:${mint}`, url: `${JUP}/swap/v1/quote?inputMint=${mint}&outputMint=${SOL}&amount=${base}&slippageBps=300` }); }
      reqs.push({ key: `rpc:mint:${mint}`, url: RPC, method: "POST", body: { jsonrpc: "2.0", id: 1, method: "getAccountInfo", params: [mint, { encoding: "jsonParsed" }] } });
    }
    return { id, reqs };
  }
  // Ship the rendered result to the GitHub hand-off repo: carries the JSON in the URL fragment to the new-file editor.
  function ship(path, owner = "RyzinEnagy", repo = "memelab-inbox", branch = "main") {
    const data = window.__ML.last || document.getElementById("ml").textContent;
    location.href = `https://github.com/${owner}/${repo}/new/${branch}?filename=${path}#` + encodeURIComponent(data);
    return "shipping " + data.length;
  }
  // On the GitHub new-file page: pull the fragment into the editor via a synthetic paste.
  async function land() {
    const txt = decodeURIComponent(location.hash.slice(1)); history.replaceState(null, "", location.pathname + location.search);
    const cm = document.querySelector(".cm-content"); if (!cm) return "no editor";
    cm.focus(); const dt = new DataTransfer(); dt.setData("text/plain", txt); cm.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
    await new Promise(r => setTimeout(r, 1200)); return `landed ${txt.length} chars; editor tail: ` + cm.textContent.slice(-30);
  }
  function start(plan, conc = 6) { window.__ML.done = false; window.__ML.summary = null; run(plan, conc).then(s => { window.__ML.summary = s; window.__ML.done = true; }); return "started " + plan.reqs.length + " requests (poll __ML.done / __ML.progress())"; }
  window.__ML = { run, start, PROJ, N, deepPlan, ship, land };
  return "collector ready";
})();
