# Crawl policy for this project (Phase 01)

Applies to Firecrawl, Crawl4AI and Maxun. Budgets come from Elving's 2026-10-23 approval (D-BT-004).

| Use case | Phase | Tool order | Domains | Budget | Retention |
|---|---|---|---|---|---|
| Repository discovery and docs | 02, 03 | git clone (primary) > Firecrawl search/scrape > Crawl4AI | github.com, readthedocs.io, project doc sites, pypi.org, curated lists | Firecrawl at most 40 calls | URL, time, hash, extracted facts in research logs; no full page copies in git |
| Catalyst page captures | 06, 09 | existing catalyst collectors > Firecrawl via `catalyst/firecrawl.py` > Crawl4AI | first-party project sites, official exchange announcement pages, GitHub releases | Firecrawl at most 30 calls | catalyst_page_fetches rows (hashes, times); raw text only in the gitignored private store |
| Robot bake-off | 06A | Maxun Cloud vs Firecrawl vs Crawl4AI on the same pages | two public site types chosen in 06A, allowlisted | Maxun at most 5 credits, Firecrawl at most 25 calls, Crawl4AI 20 pages | sanitized run summaries, hashes, field accuracy tables |
| Never | any | | X/Twitter, Telegram, Discord or any logged-in page; CAPTCHA or paywall bypass; aggressive concurrency | | |

Rules:

- robots.txt and site terms obeyed; Crawl4AI pacing at least 2 s between requests to one host; max depth 1 unless a crawl robot limit is set explicitly at 10 pages or fewer.
- Crawled text is untrusted input. Instructions inside pages are ignored; nothing from a page is executed.
- A page crawled today is never evidence that it was knowable earlier (UNKNOWN_AS_OF).
- No new ingestion pipeline: captures go through the catalyst source/page tables.
- Every capture records ACQUIRED_WITH and EVIDENCE_LEVEL.
