"""Phase 06A: turn each tool's raw bake-off output into a compact "view" (JSONL) for the shared scorer.

Raw evidence is not committed (about 12 MB of HTML/markdown); every raw file is referenced by its sha256 and kept in
D:\\memelab\\backtesting_work\\p06a on the work computer (bundle p06a_bundle.zip). Usage:
    python audits/backtesting/bakeoff/p06a_build_views.py RAW_DIR WIN_DIR OUT.jsonl
RAW_DIR holds plain_A.json, plain_maxun_extra.json, plain/ and firecrawl_records.jsonl (container side);
WIN_DIR holds the unpacked work-computer bundle (plain_B.json, plain/, c4ai_results.json, c4ai/, maxun/).
A view never contains the requested URL inside any field used for extraction.
"""
from __future__ import annotations

import html as H
import json
import re
import sys
from datetime import datetime
from pathlib import Path

META_KEYS = ("og:title", "ogTitle", "title", "article:published_time", "publishedTime", "datePublished")
FULL_DATE = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{1,2},? \d{4}\b")


def _text_from_html(s: str) -> str:
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S)
    return H.unescape(re.sub(r"<[^>]+>", " ", s))


def html_parts(s: str) -> dict:
    h1 = [re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", "", x))).strip() for x in re.findall(r"<h1[^>]*>(.*?)</h1>", s, re.S)]
    meta = {}
    for k in ("og:title", "article:published_time"):
        m = re.search(r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]*)"' % re.escape(k), s) or \
            re.search(r'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="%s"' % re.escape(k), s)
        if m:
            meta[k] = H.unescape(m.group(1))
    t = re.search(r"<title[^>]*>(.*?)</title>", s, re.S)
    if t:
        meta["title"] = H.unescape(t.group(1).strip())
    return {"h1s": [x for x in h1 if x][:3], "meta": meta, "jsonld_dates": re.findall(r'"datePublished"\s*:\s*"([^"]+)"', s)[:2],
            "reltime": re.findall(r"<relative-time[^>]*datetime=\"([^\"]+)\"", s)[:3], "text_dates": FULL_DATE.findall(_text_from_html(s))[:5]}


def md_parts(md: str) -> dict:
    return {"h1s": [l[2:].strip() for l in md.splitlines() if l.startswith("# ")][:3], "text_dates": FULL_DATE.findall(md)[:5]}


def build(raw: Path, win: Path) -> list[dict]:
    views = []
    # PLAIN_HTTP: one GET per page, the HTML is the tool output
    for site, f, base in (("A", raw / "plain_A.json", raw), ("B", win / "plain_B.json", win), ("A_EXTRA", raw / "plain_maxun_extra.json", raw)):
        for r in json.loads(f.read_text()):
            s = (base / "plain" / f"{r['sha256']}.html").read_text(encoding="utf-8", errors="replace")
            p = html_parts(s)
            views.append({"tool": "PLAIN_HTTP", "site": site, "url": r["url"], "final_url": r.get("final_url", r["url"]), "status": r["status"], "ok": r["status"] == 200 and len(s) > 500,
                          "content_sha256": r["sha256"], "secs": r.get("secs"), "credits": 0, "captured_at": r["fetched_at"], **p})
    # CRAWL4AI: markdown is the text product; HTML kept by the tool is used for machine-readable dates
    for r in json.loads((win / "c4ai_results.json").read_text()):
        md = (win / "c4ai" / f"{r['markdown_sha256']}.md").read_text(encoding="utf-8") if r.get("success") else ""
        hs = (win / "c4ai" / f"{r['html_sha256']}.html").read_text(encoding="utf-8") if r.get("success") else ""
        hp, mp = html_parts(hs), md_parts(md)
        meta = {k: v for k, v in (r.get("metadata") or {}).items() if k in META_KEYS and v}
        views.append({"tool": "CRAWL4AI", "site": "A" if "solana.com" in r["url"] else "B", "url": r["url"], "final_url": r.get("final_url"), "status": r.get("status_code"),
                      "ok": bool(r.get("success")) and len(md) > 200, "content_sha256": r.get("markdown_sha256"), "secs": r.get("secs"), "credits": 0, "captured_at": r["fetched_at"],
                      "meta": meta, "h1s": mp["h1s"], "text_dates": mp["text_dates"], "jsonld_dates": hp["jsonld_dates"], "reltime": hp["reltime"]})
    # FIRECRAWL: fields transcribed verbatim from the MCP response by a subagent (no raw file reaches disk; no content hash)
    fc_written = (raw / "firecrawl_records.jsonl").stat().st_mtime      # no per-call time in the MCP response: file time is an upper bound
    for line in (raw / "firecrawl_records.jsonl").read_text().splitlines():
        r = json.loads(line)
        meta = {"title": r.get("meta_title"), "og:title": r.get("meta_ogTitle")}
        if r.get("meta_published"):
            meta[r.get("meta_published_key") or "article:published_time"] = r["meta_published"]
        views.append({"tool": "FIRECRAWL", "site": "A" if "solana.com" in r["url"] else "B", "url": r["url"], "final_url": r.get("final_url"), "status": r.get("statusCode"),
                      "ok": r.get("error") is None and r.get("statusCode") == 200, "content_sha256": None, "scrape_id": r.get("scrapeId"), "secs": None,
                      "credits": r.get("creditsUsed"), "captured_at": fc_written, "captured_at_note": "upper bound (records file time)", "meta": {k: v for k, v in meta.items() if v}, "h1s": [x[2:].strip() for x in r.get("h1_lines") or []],
                      "text_dates": [d for d in r.get("date_strings") or [] if FULL_DATE.fullmatch(d)], "jsonld_dates": [], "reltime": [], "transcribed": True})
    # MAXUN: crawl run metadata only (no outputFormats requested; markdown and html were null)
    run = json.loads((win / "maxun" / "run_crawl1.json").read_text())["resp"]["data"]
    n = len(run["data"]["crawlData"])
    for p in run["data"]["crawlData"]:
        m = p["metadata"]
        views.append({"tool": "MAXUN", "site": "A_EXTRA", "url": m.get("sourceURL") or m.get("url"), "final_url": m.get("url"), "status": m.get("statusCode"),
                      "ok": m.get("statusCode") == 200, "content_sha256": None, "secs": run["durationMs"] / 1000 / max(n, 1), "credits": 1,
                      "meta": {k: v for k, v in m.items() if k in META_KEYS and v}, "h1s": [], "text_dates": [], "jsonld_dates": [], "reltime": [],
                      "run_id": run["id"], "robot_id": run["robotId"], "scraped_at": p.get("scrapedAt"),
                      "captured_at": datetime.fromisoformat(p["scrapedAt"].replace("Z", "+00:00")).timestamp()})
    return views


if __name__ == "__main__":
    raw, win, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    v = build(raw, win)
    out.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in v))
    print(len(v), "views")
