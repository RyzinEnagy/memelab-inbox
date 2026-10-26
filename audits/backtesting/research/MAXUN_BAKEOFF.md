# Maxun bake-off results (Phase 06A)

Rules, samples and decision thresholds were fixed before any fetch in `MAXUN_BAKEOFF_PREREG.md`. Its text says "about 17:20Z"; the hash log (`testing/logs/p06a_prereg.sha256`, sha256 `a8feeb36...`) shows 17:15:46Z, before the first bake-off fetch at 17:16:04Z. The hash file sits in the same repo, so that timing is self-attested; a copy was also written to the work computer at 17:15Z. Everything below is measured from saved outputs. This version includes corrections from an independent review (end of file).

## Samples

Site type A (first-party announcements): the 10 URLs of `https://solana.com/news/sitemap-news.xml` at 17:14:00Z (`bakeoff/p06a_sitemap-news.xml`). Site type B (developer releases): latest release of 10 tracked repos from the GitHub Releases API (`bakeoff/p06a_gh_releases.json`; two listed repos had no releases and were replaced by the pre-set backup rule with pyth-network/pyth-crosschain and metaplex-foundation/umi; GitHub's API returned `otter-sec/anchor` for `solana-foundation/anchor`, a repository transfer).

Oracle: `bakeoff/p06a_oracle.json`, written 17:28:30Z, before any scoring. Type A titles and dates were read from each page's raw HTML (H1, article:published_time) and checked against the visible byline (recorded per page; all 10 agree). Type B is the Releases API. The oracle is not independent of the existing route: it comes from the same HTML and the same API, so that route scores 1.0 by construction (see MAXUN_ADOPTION.md).

## Runs

| Tool | Route | When (UTC) | Calls / credits |
|---|---|---|---|
| PLAIN_HTTP | one GET per page (type A from the cloud workspace, type B from the work computer) | 17:16-17:25 | 20 GETs, 0 credits |
| CRAWL4AI | crawl4ai 0.9.5 on the work computer, cache bypass, 2 s spacing (`bakeoff/p06a_crawl4ai_runner.py`); raw files on the work computer, hashes in the views | 17:25-17:26 | 20 pages, 0 credits |
| FIRECRAWL | Claude MCP scrape, markdown only, onlyMainContent false, maxAge 0. A subagent transcribed fields verbatim from each response (`bakeoff/p06a_firecrawl_records.jsonl`, scrapeIds kept); raw responses were not saved, so these records cannot be re-audited byte for byte | 17:18-17:25 | 20 calls, 20 credits |
| MAXUN | Maxun Cloud v1 crawl robot `ef435421-7926-43d2-89ea-0ad337cf05db`, run `005f58a3-4fff-4b2e-8750-b5e4947eb291`, start `https://solana.com/news`, mode path, limit 12, maxDepth 1, sitemap and links on, robots respected, includePaths `/news/.*` (added at build time, not in the pre-registration), no output formats requested (`bakeoff/p06a_maxun_client.py`, responses in `bakeoff/p06a_maxun/`) | 17:26:35-17:26:43 | all 5 trial credits |

## Scores (shared extractor `memelab/backtest/sources/pagefields.py`; `python audits/backtesting/bakeoff/p06a_score.py audits/backtesting/bakeoff/p06a_views.jsonl audits/backtesting/bakeoff/p06a_oracle.json`; an independent reviewer recomputed it and got the same file)

| Cell | Usable | Sample pages returned | Title | Date | Tag | Duplicates | Credits | Sample sufficient |
|---|---|---|---|---|---|---|---|---|
| PLAIN_HTTP, A | 10 | 10/10 | 1.0 | 1.0 | | 0 | 0 | yes |
| PLAIN_HTTP, B | 10 | 10/10 | 1.0 | 1.0 | 1.0 | 0 | 0 | yes |
| CRAWL4AI, A | 10 | 10/10 | 1.0 | 1.0 | | 0 | 0 | yes |
| CRAWL4AI, B | 10 | 10/10 | 1.0 | 1.0 | 1.0 | 0 | 0 | yes |
| FIRECRAWL, A | 10 | 10/10 | 1.0 | 1.0 | | 0 | 10 | yes |
| FIRECRAWL, B | 10 | 10/10 | 1.0 | 0.8 | 1.0 | 0 | 10 | yes |
| MAXUN, A | 5 | 0/10 | | | | 0 | 5 | no: INSUFFICIENT_BAKEOFF_SAMPLE |
| MAXUN, B | 0 | 0/10 | | | | | 0 left | no: BLOCKED_EXTERNAL (no credits) |

Not measured: comparable speed (tools ran on different hosts, Firecrawl was not timed, Maxun's figure is run time over pages of a parallel metadata-only crawl), fetch-to-storage latency, breakage under a small page change, CPU and memory. Setup work is described in prose only.

On the 5 pages Maxun returned (the /news index and four outage reports dated 2022 to 2024), its metadata gave the right title on 5 of 5 and the right date on 4 of 4 articles, checked against raw HTML fetched for the purpose. That shows its extraction works on what it fetched. It says nothing about coverage of the sample.

## What the numbers show

- Maxun was not given the same task. The other tools got the 10 URLs; Maxun had to find them by crawling, with a budget (5 credits) below the sample size. It returned 4 old outage reports and the index and then stopped. The order in which it discovered pages is not known (the sitemap it read was not saved). So "0 of 10" measures discovery under this budget, not extraction quality.
- The run cost all 5 credits for 5 returned pages and ended `status: aborted` with `isPartial: false` and `error: null`. A client must treat `aborted` as partial whatever `isPartial` says.
- A further run with 0 credits was refused with HTTP 403 `Insufficient credits ... Each data point requires 1/4 credits` (`minimum: 0.25`). The Cloud API page lists 402 for that case (`research/raw/p06a_maxun_cloud_api_excerpt.md`). How credits map to pages is not settled by one run: 1 per page, 0.25 per data point, or a run minimum all fit.
- Without output formats, crawl pages carry metadata only (`markdown`, `html` null). The metadata held og:title and article:published_time.
- Firecrawl's two type B date misses come from the extractor, not the tool. GitHub shows a release date without a year ("16 Oct"); the shared extractor only accepts a written date with a year, so it took the first such date on the page, which for jito is a commit-signature date ("Oct 15, 2026", from `2026-10-15 23:43:49 UTC`), and for token-2022 found none ("4 hours ago"). Tools that keep the HTML read the release's machine time (`2026-10-16T15:18:29Z`) and got all 10. Lesson kept in the extractor: a text date is lowest confidence and never enters a record's identity.
- Type B pages repeat what the GitHub Releases API returns exactly. The contract prefers the API, and so does this result.
- What the ingestion run proves (`testing/logs/p06a_ingest.json`): cross-tool deduplication and idempotent replay on real captures (24 origins, 1 version each, 10 REFINED_DATE rows where a text date came first and a machine date later, second pass 68 of 68 duplicates). It does not prove live change detection: no page changed between passes. New versions on a changed title, date or tag are shown only with modified copies in tests. Body-only edits are not detected (the fingerprint is title, machine date and tag), and a raw-byte hash would not work on solana.com, whose pages carry per-request tracing values. Maxun's monitoring diff was not tried.

## Cost (arithmetic on the one observation)

A daily watch needs the index or sitemap plus each new article, about one to two pages a day on this site, so roughly 30 to 60 credits a month at 1 credit per page, or 8 to 15 at 0.25 per data point. The trial grants 5 a month. No paid price was looked up, so no dollar figure is given. The existing route costs one sitemap GET a day plus one GET per new article, with no account.

## Negative control

Every pass ingested the four old outage reports Maxun returned (claimed 2022-05-02, 2022-06-04, 2023-04-18, 2024-02-09; first captured 2026-10-23). At each claimed date plus one day, `captures_asof` returns UNKNOWN_AS_OF.

## Corrections made after the independent review

The first draft attributed Firecrawl's date misses to its browser time zone (wrong: an extractor artifact), claimed Maxun "visited pages in sitemap order" (not shown), estimated about 300 credits a month (based on re-crawling 10 pages daily; the index-plus-new-items design is cheaper), implied change detection was proven live (it was not), gave a speed column as if comparable, and dated the oracle 17:40Z (it was 17:28:30Z). All corrected above. Scores did not change.
