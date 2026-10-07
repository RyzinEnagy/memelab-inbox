// Stage-2 structural filter in the browser. Requires collector (__ML.run) defined.
// await __ML.stage2(["mint1","mint2",...], {maxSingle:15, maxTop10:50, minLiq:30000, keep:8})
// Fetches rugcheck report + jupiter token + dexscreener pairs per mint, rejects obvious structural failures,
// and renders full projected bodies only for survivors (plus a compact rejection table).
(() => {
  const POOL_OWNERS = new Set(["5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1","GpMZbSM2GgvTKHJirzeGfMFoaZ8UR2X7F4v8vHTvxFbL","39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg","pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA","6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P","LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo","Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB","cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG","dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN","whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc","CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK","CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C","LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj"]);
  const LOCKERS = new Set(["strmRqUCoQUgGUan5YhzUZa6KqdzwX5L6FpUxfmKg5m","LocpQgucEQHbqNABEYvBvwoxCPsSbG91A1QaQhQQqjn","BLoCKvQEZZdhkjx8fZYF1sDxCt9Td9iQdcsCxZ4GpR4A"]);
  const BURN = new Set(["1nc1nerator11111111111111111111111111111111","11111111111111111111111111111111"]);
  async function stage2(mints, opts = {}) {
    const o = { maxSingle: 15, maxTop10: 50, minLiq: 30000, keep: 8, ...opts };
    const reqs = [];
    for (let i = 0; i < mints.length; i += 30) reqs.push({ key: "ds:batch:" + i, url: "https://api.dexscreener.com/tokens/v1/solana/" + mints.slice(i, i + 30).join(",") });
    for (const m of mints) { reqs.push({ key: "jup_tok:" + m, url: "https://lite-api.jup.ag/tokens/v2/search?query=" + m }); reqs.push({ key: "rug:" + m, url: "https://api.rugcheck.xyz/v1/tokens/" + m + "/report", delayMs: 300 }); }
    await window.__ML.run({ id: "s2_" + Date.now(), reqs }, 4);
    const out = JSON.parse(document.getElementById("ml").textContent);
    const pairsAll = []; for (const [k, v] of Object.entries(out)) if (k.startsWith("ds:") && v.s === 200) pairsAll.push(...v.body);
    const rows = [], rejected = [];
    for (const m of mints) {
      const jt = (out["jup_tok:" + m]?.body || []).find(t => t.id === m); const rg = out["rug:" + m]?.s === 200 ? out["rug:" + m].body : null;
      const pairs = pairsAll.filter(p => p.baseToken?.address === m);
      const why = []; const sym = jt?.symbol || rg?.tokenMeta?.symbol || pairs[0]?.baseToken?.symbol;
      if (!jt && !rg && !pairs.length) { rejected.push([m, sym, "no structural data"]); continue; }
      const names = [jt?.name, rg?.tokenMeta?.name, pairs[0]?.baseToken?.name].filter(Boolean).map(s => s.trim().toLowerCase());
      if (names.length >= 2 && new Set(names).size > 1) why.push("name differs across sources: " + [...new Set(names)].join(" | "));
      if (rg) {
        if (rg.token?.mintAuthority) why.push("mint authority active"); if (rg.token?.freezeAuthority) why.push("freeze authority active");
        const ext = rg.token_extensions || {}; const dangerous = [];
        if (ext.permanentDelegate) dangerous.push("permanentDelegate"); if (ext.transferHook && (ext.transferHook.programId || ext.transferHook.authority)) dangerous.push("transferHook");
        if (ext.nonTransferable === true) dangerous.push("nonTransferable"); if (ext.defaultAccountState && String(ext.defaultAccountState.state || ext.defaultAccountState).toLowerCase().includes("frozen")) dangerous.push("defaultFrozen");
        if (ext.pausableConfig && ext.pausableConfig.paused) dangerous.push("paused");
        if (dangerous.length) why.push("dangerous Token-2022 extension: " + dangerous.join(","));
        const fee = rg.transferFee?.pct || 0; if (fee > 5) why.push("transfer fee " + fee + "%");
        const markets = rg.markets || []; const mk = new Set(markets.map(x => x.pubkey));
        const econ = (rg.topHolders || []).filter(h => !POOL_OWNERS.has(h.owner) && !mk.has(h.owner) && !mk.has(h.address) && !LOCKERS.has(h.owner) && !BURN.has(h.owner));
        const largest = econ[0]?.pct || 0; const top10 = econ.slice(0, 10).reduce((a, h) => a + (h.pct || 0), 0);
        if (largest > o.maxSingle) why.push(`largest non-pool holder ${largest.toFixed(1)}%`); if (top10 > o.maxTop10) why.push(`adjusted top-10 ${top10.toFixed(1)}%`);
        const main = markets.slice().sort((a, b) => ((b.lp?.baseUSD || 0) + (b.lp?.quoteUSD || 0)) - ((a.lp?.baseUSD || 0) + (a.lp?.quoteUSD || 0)))[0];
        const tl = main?.lp?.holders?.[0]; const lk = main?.lp?.lpLockedPct;
        if (tl && (tl.pct || 0) >= 50 && (lk || 0) < 50 && !POOL_OWNERS.has(tl.owner) && (tl.owner === rg.creator)) why.push("creator controls main pool LP");
      } else why.push("no rugcheck report (authorities unknown)");
      const liq = jt?.liquidity || pairs.reduce((a, p) => a + (p.liquidity?.usd || 0), 0); if (liq < o.minLiq) why.push(`liquidity $${Math.round(liq)} < $${o.minLiq}`);
      if (jt?.audit?.mintAuthorityDisabled === false) why.push("mint authority active (jup)"); if (jt?.audit?.freezeAuthorityDisabled === false) why.push("freeze authority active (jup)");
      if (why.length) rejected.push([m, sym, why.join("; ")]); else rows.push(m);
    }
    const keep = rows.slice(0, o.keep);
    const res = { _plan: out._plan, _at: out._at, _stage2: { n: mints.length, pass: rows.length, kept: keep.length, rejected: rejected.length, opts: o }, stage2_rejected: rejected, stage2_pass: rows };
    const dsKeep = pairsAll.filter(p => keep.includes(p.baseToken?.address)); res["ds:keep"] = { s: 200, body: dsKeep };
    for (const m of keep) { res["jup_tok:" + m] = out["jup_tok:" + m]; const r = out["rug:" + m]; if (r && r.s === 200) { r.body.topHolders = (r.body.topHolders || []).slice(0, 20); r.body.insiderNetworks = (r.body.insiderNetworks || []).map(n => ({ ...n, wallets: (n.wallets || []).slice(0, 12) })); r.body.risks = (r.body.risks || []).map(x => ({ name: x.name, level: x.level, value: x.value })); } res["rug:" + m] = r; }
    window.__ML.last = JSON.stringify(res); document.getElementById("ml").textContent = window.__ML.last;
    return `stage2: ${rows.length}/${mints.length} pass, kept ${keep.length}; rejected ${rejected.length}; rendered ${window.__ML.last.length} chars`;
  }
  window.__ML.stage2 = stage2; return "stage2 ready";
})();
