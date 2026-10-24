import asyncio, json, time, hashlib, os, urllib.request
OUT = r"D:\memelab\backtesting_work\p06a"
A = """https://solana.com/news/solana-changelog-october-16-2026
https://solana.com/news/geo-aware-leader-schedule
https://solana.com/news/breakpoint-2026-london-speakers-2
https://solana.com/news/payments-on-solana-september-2026-in-five-stories
https://solana.com/news/breakpoint-guide-part2
https://solana.com/news/solana-changelog-october-8-2026
https://solana.com/news/samsung-wallet
https://solana.com/news/solana-ecosystem-roundup-september-2026
https://solana.com/news/solana-foundation-launches-solana-dv-p-an-atomic-settlement-program-built-for-financial-institutions
https://solana.com/news/solana-microscope""".split()
rel = json.load(open(os.path.join(OUT, "gh_releases.json")))["releases"]
B = [v["html_url"] for v in rel.values() if v]
UA = "memelab-research/0.1 (one-shot bake-off)"
os.makedirs(os.path.join(OUT, "plain"), exist_ok=True); os.makedirs(os.path.join(OUT, "c4ai"), exist_ok=True)
plain = []
for u in B:
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "text/html"}), timeout=30) as r:
            st, b, fu = r.status, r.read(), r.geturl()
    except urllib.error.HTTPError as e:
        st, b, fu = e.code, e.read(), u
    h = hashlib.sha256(b).hexdigest()
    open(os.path.join(OUT, "plain", h + ".html"), "wb").write(b)
    plain.append({"url": u, "final_url": fu, "status": st, "bytes": len(b), "sha256": h, "secs": round(time.time() - t0, 2), "fetched_at": t0})
    time.sleep(2)
json.dump(plain, open(os.path.join(OUT, "plain_B.json"), "w"), indent=1)
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
async def main():
    rows = []
    async with AsyncWebCrawler() as c:
        for u in A + B:
            t0 = time.time()
            try:
                r = await c.arun(u, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
                md = str(r.markdown or "")
                html = r.html or ""
                rec = {"url": u, "success": r.success, "status_code": r.status_code, "error": r.error_message, "metadata": r.metadata,
                       "final_url": getattr(r, "redirected_url", None), "markdown_sha256": hashlib.sha256(md.encode()).hexdigest(),
                       "html_sha256": hashlib.sha256(html.encode()).hexdigest(), "markdown_chars": len(md), "secs": round(time.time() - t0, 2), "fetched_at": t0}
                open(os.path.join(OUT, "c4ai", rec["markdown_sha256"] + ".md"), "w", encoding="utf-8").write(md)
                open(os.path.join(OUT, "c4ai", rec["html_sha256"] + ".html"), "w", encoding="utf-8").write(html)
            except Exception as e:
                rec = {"url": u, "success": False, "error": f"{type(e).__name__}: {e}", "secs": round(time.time() - t0, 2), "fetched_at": t0}
            rows.append(rec)
            await asyncio.sleep(2)
    json.dump(rows, open(os.path.join(OUT, "c4ai_results.json"), "w"), indent=1, default=str)
    print(sum(1 for x in rows if x.get("success")), "of", len(rows))
asyncio.run(main())
open(os.path.join(OUT, "C4AI_DONE"), "w").write(str(time.time()))
