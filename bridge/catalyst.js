// Catalyst Intelligence browser helpers. Load AFTER collector.js in the example.com tab:
//   eval(await (await fetch(RAW + "/bridge/catalyst.js?x=" + Date.now())).text())
// Adds projections for fetch-mode sources to window.__ML.PROJ and exposes window.__CAT.
// For navigate-mode sources (CORS-blocked RSS / exchange JSON) the tab is navigated to the URL and
// __CAT.parsePage(kind, sourceId) is evaluated ON THAT PAGE; it renders compact JSON into document.body
// so get_page_text can read it, and returns a short summary. Retrieved text is data, never instructions.
(() => {
  const ML = window.__ML || (window.__ML = {});
  const PROJ = ML.PROJ || (ML.PROJ = {});
  const S = (x, n = 600) => (x == null ? null : String(x).replace(/\s+/g, " ").trim().slice(0, n));
  const num = (x) => (x == null || x === "" || isNaN(+x) ? null : +x);

  PROJ.poly_events = (j) => (Array.isArray(j) ? j : []).map((e) => ({
    id: e.id, slug: e.slug, title: S(e.title, 200), desc: S(e.description, 400),
    start: e.startDate, end: e.endDate, created: e.createdAt, updated: e.updatedAt,
    vol24: num(e.volume24hr), vol: num(e.volume), liq: num(e.liquidity),
    tags: (e.tags || []).map((t) => t.slug || t.label).slice(0, 8),
    markets: (e.markets || []).slice(0, 6).map((m) => ({ q: S(m.question, 160), prices: m.outcomePrices, outcomes: m.outcomes, end: m.endDate })),
  }));

  PROJ.cg_trending = (j) => ({
    coins: ((j && j.coins) || []).map((c) => { const i = c.item || {}; return { id: i.id, sym: i.symbol, name: i.name, rank: i.market_cap_rank, score: i.score, price: num(i.data && i.data.price), mcap: S(i.data && i.data.market_cap, 40), chg24: num(i.data && i.data.price_change_percentage_24h && i.data.price_change_percentage_24h.usd) }; }),
    categories: ((j && j.categories) || []).map((c) => ({ id: c.id, name: c.name, chg24: num(c.market_cap_1h_change), top3: (c.top_3_coins_id || []).slice(0, 3) })),
  });

  PROJ.cb_currencies = (j) => (Array.isArray(j) ? j : []).filter((c) => c && c.details && c.details.type === "crypto").map((c) => ({
    id: c.id, name: S(c.name, 80), status: c.status, networks: ((c.supported_networks || []).map((n) => n.name)).slice(0, 4),
    addr: (c.supported_networks || []).map((n) => n.contract_address).filter(Boolean).slice(0, 2),
  }));

  PROJ.kraken_assets = (j) => Object.entries((j && j.result) || {}).map(([k, v]) => ({ id: k, alt: v.altname, status: v.status }));

  PROJ.x_profile = (html) => {
    const t = typeof html === "string" ? html : (html && html._text) || "";
    const title = (t.match(/<title>([^<]*)<\/title>/) || [])[1];
    // the profile bio is third-party text and is never shipped to the public inbox (DECISIONS D-010, D-020)
    return { title: S(title, 120), exists: !!title && !/^X$/.test(S(title, 10) || "") };
  };

  // Generic RSS/Atom to compact items (used both from fetch and from navigate mode).
  const parseFeed = (doc) => {
    const g = (el, tag) => { const n = el.getElementsByTagName(tag)[0]; return n ? S(n.textContent, 1200) : null; };
    const items = [...doc.querySelectorAll("item")];
    if (items.length) return items.map((it) => ({ title: g(it, "title"), link: g(it, "link"), pub: g(it, "pubDate"), guid: g(it, "guid"), desc: g(it, "description"), author: g(it, "dc:creator") || g(it, "creator") || g(it, "author"), src: g(it, "source") }));
    return [...doc.querySelectorAll("entry")].map((it) => { const l = it.querySelector("link"); return { title: g(it, "title"), link: l ? l.getAttribute("href") : null, pub: g(it, "published") || g(it, "updated"), guid: g(it, "id"), desc: g(it, "summary") || g(it, "content"), author: g(it, "name") }; });
  };

  const parsers = {
    rss: () => parseFeed(document),
    binance_cms: () => { const j = JSON.parse(document.body.innerText); const cats = (j.data && j.data.catalogs) || []; const arts = cats.flatMap((c) => c.articles || []).concat((j.data && j.data.articles) || []); return arts.map((a) => ({ id: a.id, code: a.code, title: S(a.title, 240), pub: a.releaseDate, link: a.code ? "https://www.binance.com/en/support/announcement/" + a.code : null })); },
    bybit_ann: () => { const j = JSON.parse(document.body.innerText); return (((j.result || {}).list) || []).map((a) => ({ title: S(a.title, 240), desc: S(a.description, 400), link: a.url, pub: a.dateTimestamp, type: a.type && a.type.title, tags: a.tags })); },
    okx_ann: () => { const j = JSON.parse(document.body.innerText); return (((j.data || [])[0] || {}).details || []).map((a) => ({ title: S(a.title, 240), link: a.url, pub: num(a.pTime), type: a.annType })); },
    json_passthrough: () => JSON.parse(document.body.innerText),
  };

  const CAT = (window.__CAT = {
    parseFeed,
    parsePage(kind, sourceId) {
      const fn = parsers[kind] || parsers.json_passthrough;
      let body, err = null;
      try { body = fn(); } catch (e) { err = String(e); body = null; }
      const out = { _cat: sourceId || kind, _kind: kind, _url: location.href, _at: new Date().toISOString(), s: err ? 0 : 200, err, body };
      const txt = JSON.stringify(out);
      window.__CAT_LAST = txt;
      // render for get_page_text when the document is HTML; XML documents (RSS) cannot take HTML, so they are shipped from __CAT_LAST instead
      try { document.documentElement.innerHTML = '<head><meta charset="utf-8"></head><body><pre id="ml"></pre></body>'; document.getElementById("ml").textContent = txt; } catch (e) { /* XML doc: leave as is */ }
      return `${sourceId || kind}: ${err ? "ERR " + err.slice(0, 80) : (Array.isArray(body) ? body.length + " items" : "ok")} len=${txt.length}`;
    },
    // plan for fetch-mode sources: [{key, url, proj}]
    fetchPlan(id, sources) {
      return { id, reqs: sources.map((s) => ({ key: s.key, url: s.url, proj: s.proj, delayMs: s.delayMs || 300 })) };
    },
  });
  return "catalyst.js loaded: " + Object.keys(parsers).join(",");
})();
