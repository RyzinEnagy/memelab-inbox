// Stage-1 in-browser merge + cheap screen. Call after __ML.run(plan) has rendered: await __ML.screen({minLiq:20000,minVol:50000})
// Produces merged per-mint rows in the same shape as m01's candidate signals, renders them, and returns a summary.
(() => {
  const MAJORS = new Set(["So11111111111111111111111111111111111111112","EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v","Es9vMGANM1E2EjMA4c6kQX8m3KdMMw2sCkChfR4ZF9","mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So","J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn","7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs","DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263","EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm","JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN","rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof","HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3","orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE","jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL","27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4","cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij","3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh","9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E","2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo","USD1ttGY1N17NEEHLmELoaybftRBUSErhqYiQzvEmuB","Fw6HfsiMK7Qdt9JBGxtn4QmZzW8gKeNg7uZc6wVYSDFF"]);
  const QUOTES = new Set(["So11111111111111111111111111111111111111112","EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v","Es9vMGANM1E2EjMA4c6kQX8m3KdMMw2sCkChfR4ZF9","USD1ttGY1N17NEEHLmELoaybftRBUSErhqYiQzvEmuB"]);
  async function screen(opts = {}) {
    const minLiq = opts.minLiq ?? 20000, minVol = opts.minVol ?? 50000;
    const out = JSON.parse(document.getElementById("ml").textContent);
    const C = {};
    const cand = (m) => (C[m] ||= { mint: m, symbol: null, name: null, feeds: new Set(), signals: {} });
    const setv = (s, k, v) => { if (v !== null && v !== undefined) s[k] = v; };
    for (const [key, v] of Object.entries(out)) {
      if (!key.startsWith("gt_pools") || !v || v.s !== 200) continue;
      const feed = key.split(":")[1];
      for (const p of v.body.pools || []) {
        if (!p.base || MAJORS.has(p.base) || !QUOTES.has(p.quote)) continue;
        const c = cand(p.base); c.feeds.add("gt:" + feed); const s = c.signals;
        s.gt_reserve = Math.max(s.gt_reserve || 0, p.reserve || 0);
        const vol = p.vol || {}, tx = p.tx || {};
        s.vol_24h = (s.vol_24h || 0) + (vol.h24 || 0); s.vol_1h = (s.vol_1h || 0) + (vol.h1 || 0); s.vol_6h = (s.vol_6h || 0) + (vol.h6 || 0);
        if (tx.h24) { s.buyers_24h = (s.buyers_24h || 0) + (tx.h24[2] || 0); s.sellers_24h = (s.sellers_24h || 0) + (tx.h24[3] || 0); }
        if (tx.h1) { s.buyers_1h = (s.buyers_1h || 0) + (tx.h1[2] || 0); s.sellers_1h = (s.sellers_1h || 0) + (tx.h1[3] || 0); }
        s.chg ||= p.chg; s.fdv ??= p.fdv; s.mcap ??= p.mcap; s.created ??= p.created;
        c.name ||= (p.name || "").split(" / ")[0]; c.symbol ||= c.name;
      }
    }
    for (const [key, v] of Object.entries(out)) {
      if (!key.startsWith("jup_disc") || !v || v.s !== 200) continue;
      const feed = key.split(":").slice(1).join(":");
      for (const t of v.body) {
        if (!t.id || MAJORS.has(t.id)) continue;
        const c = cand(t.id); c.feeds.add("jup:" + feed); c.symbol = t.symbol || c.symbol; c.name = t.name || c.name;
        if (t._dup) continue;
        const s = c.signals;
        setv(s, "jup_liq", t.liq); setv(s, "mcap", t.mcap); setv(s, "fdv", t.fdv); setv(s, "holders", t.holders); setv(s, "organic_score", t.org); setv(s, "organic_label", t.orgL);
        setv(s, "launchpad", t.lp); setv(s, "first_pool_at", t.fp); setv(s, "dev", t.dev);
        const au = t.audit || {}; setv(s, "mint_disabled", au.m); setv(s, "freeze_disabled", au.f); setv(s, "top_holders_pct", au.th); setv(s, "dev_pct", au.dv);
        for (const w of ["1h", "6h", "24h"]) { const st = t["s" + w]; if (!st) continue; setv(s, "j_vol_" + w, st.v); setv(s, "j_org_" + w, st.o); setv(s, "j_netbuyers_" + w, st.nb); setv(s, "j_traders_" + w, st.tr); setv(s, "j_holderchg_" + w, st.hc); setv(s, "j_liqchg_" + w, st.lc); setv(s, "j_chg_" + w, st.pc); }
      }
    }
    for (const [key, v] of Object.entries(out)) {
      if (!key.startsWith("ds_profiles") || !v || v.s !== 200) continue;
      for (const p of v.body) { if (p.chainId !== "solana" || !p.tokenAddress) continue; const c = cand(p.tokenAddress); c.feeds.add(key.includes("boosts") ? "ds:boost" : "ds:profile"); setv(c.signals, "ds_boost_amount", p.totalAmount ?? p.amount); }
    }
    const rt = out["raw:rug_trending"]; if (rt && rt.s === 200 && Array.isArray(rt.body)) for (const t of rt.body) if (t && t.mint && !MAJORS.has(t.mint)) cand(t.mint).feeds.add("rug:trending");
    const survivors = [], rejected = [];
    for (const c of Object.values(C)) {
      const s = c.signals; const liq = Math.max(s.jup_liq || 0, s.gt_reserve || 0); const vol = Math.max(s.vol_24h || 0, s.j_vol_24h || 0);
      const why = [];
      if (liq && liq < minLiq) why.push("liq<" + minLiq); if (vol && vol < minVol) why.push("vol<" + minVol); if (!liq && !vol) why.push("no data");
      if (s.mint_disabled === false) why.push("mint auth active"); if (s.freeze_disabled === false) why.push("freeze auth active");
      c.feeds = [...c.feeds].sort();
      if (why.length) rejected.push([c.mint, c.symbol, why.join(";")]); else survivors.push(c);
    }
    const res = { _plan: out._plan, _at: out._at, _screen: { minLiq, minVol, universe: Object.keys(C).length, survivors: survivors.length, rejected: rejected.length }, merged: survivors, stage1_rejected: rejected, "raw:cg_sol": out["raw:cg_sol"] };
    const s = JSON.stringify(res);
    document.getElementById("ml").textContent = s;
    return `screened: universe ${res._screen.universe}, survivors ${survivors.length}, rejected ${rejected.length}; rendered ${s.length} chars`;
  }
  window.__ML.screen = screen; return "screen ready";
})();
