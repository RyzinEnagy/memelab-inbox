# Maxun bake-off pre-registration (Phase 06A)

Written 2026-10-23 at about 17:20Z, before any bake-off page was fetched by any tool. Its sha256 is recorded in `testing/logs/p06a_prereg.sha256` and a copy was written to the work computer at the same time. Results are in `MAXUN_BAKEOFF.md`; nothing below was changed after results came in.

## Question

Does a Maxun Cloud robot give the lab a persistent collection capability, or a measurable reliability gain, that the existing collectors (plain HTTP plus the lab's parsers, the GitHub Releases API, Firecrawl, Crawl4AI) do not?

## Samples (fixed by rule, not by hand)

Site type A, first-party project announcements: every URL in `https://solana.com/news/sitemap-news.xml` as retrieved at 2026-10-23T17:14:00Z. It listed exactly 10 article URLs. robots.txt for solana.com: `User-Agent: * Allow: /`.

Site type B, developer release pages: for each of the repos anza-xyz/agave, solana-foundation/anchor, orca-so/whirlpools, helius-labs/helius-sdk, jito-foundation/jito-solana, solana-program/token-2022, metaplex-foundation/mpl-token-metadata, anza-xyz/kit, raydium-io/raydium-sdk-V2, jup-ag/jupiter-swap-api-client, the most recent release returned by `GET /repos/{repo}/releases?per_page=1`. Repos with no release were replaced in order from two backup lists until 10 releases were found (pyth-network/pyth-crosschain and metaplex-foundation/umi were the ones used). The release page `html_url` is the sample URL. github.com robots.txt does not disallow `/{owner}/{repo}/releases/tag/` for `*`.

## Oracle

Type A: title and publication date (UTC calendar date) hand-labeled from the raw HTML of each page (fetched once with a plain GET), checked against the visible byline text. Type B: tag, release name and published date (UTC) from the GitHub Releases API, which is the authoritative source for those fields, spot-checked against the page. The oracle is written to `bakeoff/p06a_oracle.json` before any tool output is scored.

## Tools and budget

| Tool | Route | Budget |
|---|---|---|
| PLAIN_HTTP (existing lab route) | one GET per page, lab-style parser (sitemap for A, Releases API for B) | 20 GETs plus the sitemap and 10 API calls already made for sampling |
| FIRECRAWL | Claude MCP scrape, markdown, onlyMainContent false | at most 22 calls |
| CRAWL4AI | local crawl4ai 0.9.5 on the work computer, cache bypass | 20 pages, 2 s spacing |
| MAXUN | Maxun Cloud v1, one-shot runs only, no schedule, no webhook, no monitoring alerts | at most 5 credits; `/v1/usage` read before and after every run |

Maxun runs planned: one crawl robot started at `https://solana.com/news` (mode path, limit 12, maxDepth 1, useSitemap true, followLinks true, respectRobots true) and one scrape robot on one type B page. A second run of a robot (rescan) only if credits remain. Maxun therefore cannot reach 10 pages on type B; that cell is reported as `INSUFFICIENT_BAKEOFF_SAMPLE` unless a crawl covers it.

## Scoring (the same extractor for every tool)

`bakeoff/p06a_score.py` turns each tool's output (metadata plus markdown or text) into fields with one shared extractor: title from og:title or the HTML title with the site suffix removed, falling back to the first H1; date from article/published metadata, JSON-LD datePublished or a `<relative-time datetime>` attribute when the tool keeps HTML, else the first full date written in the text; tag from the first H1 or title that contains a version-like string. The URL is never used to fill a field. Metrics per tool and site type: usable pages (status 200 and non-empty content), exact-field accuracy per field, duplicate outputs, wall time per page, credits, setup steps, and whether a rerun can tell changed content from unchanged content.

## Decision rules

1. ADOPT a Maxun robot only if all hold: (a) on at least one site type its exact-field accuracy is at least 10 points above the best existing tool, or it delivers a needed persistent capability (change detection between runs) that the existing tools cannot match with a stored content hash; (b) the monthly cost for that use case at a useful cadence fits the approved budget (the trial gives 5 credits a month); (c) license stays Cloud plus thin adapter; (d) it adds no second ingestion path.
2. EXISTING_TOOL_WINS if an existing tool matches or beats Maxun's accuracy and coverage on both site types at lower cost or setup work.
3. NO_GO if Maxun cannot be bounded safely (for example scope filters not enforced and no client-side way to stop off-allowlist pages entering the lab).
4. BLOCKED_EXTERNAL if no Maxun run can complete (credits, auth, outage).
5. Ties go to the existing tool. Fewer than 10 usable attempts in a cell means `INSUFFICIENT_BAKEOFF_SAMPLE` for that cell, and no accuracy claim from it.

## Negative control in every pass

Each pass ingests at least one page whose stated publication date is earlier than its first capture. The record must come out `UNKNOWN_AS_OF` with available_at equal to the capture time, never the stated date.
