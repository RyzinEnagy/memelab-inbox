# Firecrawl in Catalyst Intelligence

Module: `memelab/catalyst/firecrawl.py`. Commands: `catalyst fc-health`, `catalyst enrich`, `catalyst fc-search`, `catalyst pull-pages --firecrawl`. Example config: `firecrawl.example.json` (off). Tests: `tests/test_catalyst_firecrawl.py` (32). Fixtures: `tests/fixtures/catalyst/firecrawl/` (invented).

Status on 2026-10-22: built and proved on fixtures. Not operational: no API key, no config, no live call made.

## What Firecrawl is

Firecrawl (github.com/firecrawl/firecrawl, AGPL-3.0 server, MIT SDKs) is a web data API. Given a URL it renders the page in a browser, strips navigation and ads, and returns clean markdown, the page's links and its metadata (title, language, published time, HTTP status). It also has a search endpoint (web and news results, optionally scraped), crawl and map endpoints for whole sites, a change-tracking format, and several LLM features (JSON extraction, summaries, an agent). It runs as a hosted service (api.firecrawl.dev, credit-billed) or self-hosted with Docker.

## The gap it closes in catalyst research

Before this change the catalyst pass only ever saw what feeds said about a story:

- an event's description was the RSS snippet (1,200 characters at most), never the article itself;
- token links came almost entirely from ticker and name searches, which are WEAK or AMBIGUOUS by design. NAMED_IN_SOURCE (STRONG) fired only when a contract happened to sit in the snippet or the URL;
- corroboration counted publisher domains, so a follow-up story that only rewrote and linked an earlier report counted as independent confirmation;
- navigate-mode sources that fail a direct pull had only the Chrome route left;
- corroboration was limited to the nine news feeds in the registry.

What it does now:

| Use | Command | Effect on the pipeline |
|---|---|---|
| Read the article behind each recent event | `catalyst enrich` | contracts named on the page become exact-address search terms and NAMED_IN_SOURCE / STRONG links; the page's own publication time is shown next to the feed time; the links on the page drive a citation check |
| Find other publishers of a stored story | `catalyst fc-search --events N` | new items (source `web:firecrawl:search`, aggregator tier) go through the normal ingest, so a new publisher is INDEPENDENT corroboration and a known one is dropped before ingest |
| Topic search | `catalyst fc-search --query TEXT` | same path, for a narrative the feeds do not cover |
| Second API route for failed navigate-mode sources | `catalyst pull-pages ID --firecrawl` | only sources listed in `pull_fallback.sources`; parsed with the same parser as the direct pull |

Run order in a catalyst pass (optional steps, only when the config is enabled):

```
python -m memelab catalyst plan --id cat_<stamp> ; ... fetch ... ; catalyst pull-pages cat_<stamp> [--firecrawl]
python -m memelab catalyst ingest --results cat_<stamp>
python -m memelab catalyst fc-search --events 5          # more publishers -> corroboration
python -m memelab catalyst enrich                        # read the articles
python -m memelab catalyst match-plan --id catm_<stamp>  # named contracts are searched by exact address
... match, assess, monitor, report as before
```

## What changed in the existing code

- `catalyst/match.py`: up to 3 Solana contracts named on the event's pages lead the term list (SOL, stablecoins and other majors from `m01.MAJOR_IGNORE` excluded). An address term links only the exact mint it names (a DEX Screener pair whose base token is another mint is ignored). A named contract is NAMED_IN_SOURCE / STRONG. A ticker or name match that lands on a different mint with the same symbol as a named contract is AMBIGUOUS and says it is a symbol collision. EVM contracts are recorded but not linked: the catalyst matcher is Solana-only (see Gaps).
- `catalyst/attention.py` and `assess.py`: when every ORIGINAL and INDEPENDENT source of an event was read, an article that links another non-official publisher in the same event is derivative. `uncited_publishers` then replaces `independent_sources` for the attention point that needs two independent sources, and the flag CITES OTHER COVERAGE names the citing publishers. Linking the exchange's own notice is not derivative. When coverage is partial nothing changes and a note says so.
- `catalyst/report.py`: a coverage line for pages read in the last 36 h (live only) and, per linked event, pages read, contracts named (FACT about the page), cashtags, and the page time against the feed time.
- `catalyst/ingest.py`: parser `fc_search`. `catalyst/sources.py`: source `web:firecrawl:search` (access mode `api`, never planned as a URL). `catalyst/schema.py`: tables `catalyst_page_fetches` and `catalyst_page_facts`. `catalyst/cli.py`: the four commands and `catalyst ingest --file` for result files kept outside the inbox.
- `memelab/state.py`: the state export now carries live page reads (10 days), their facts, and live Firecrawl spend rows (40 days). Scheduled runs start from a fresh database and only `state/latest.json` carries history, so without this every run would pay again for the same articles and the monthly cap would reset each session. Imported reads lose their event and item ids (those belong to another database); pages are found by `url_key`.
- `social/ingest.py redact()`, `tools/release_audit.py` (key shape `fc-` + 32 hex, `api.firecrawl.dev` as a credentialed host, example config checked), `tools/release_e2e.py` (7 stages, `FIRECRAWL_API_KEY` removed from children), `social/content_guard.py` (no `markdown` or `rawHtml` key in tracked JSON, no content column in `catalyst_page_*`, every page fact shaped like an address, ticker or domain).

## What was read (contract)

From the Firecrawl source at commit 5442955 (2026-10-22), `apps/api/src`:

- `routes/v2.ts`: POST `/v2/scrape` and `/v2/search` check credits before running; GET `/v2/team/credit-usage` has no credit check (free).
- `controllers/v2/types.ts`: scrape options (`formats`, `onlyMainContent` default true, `proxy` basic, auto, stealth or enhanced with auto the default, `maxAge`, `storeInCache`, `parsers` default pdf and image, `zeroDataRetention`); document metadata (`statusCode`, `url`, `sourceURL`, `language`, `publishedTime`, `modifiedTime`, `cacheState`, `proxyUsed`, `creditsUsed`); search request (`query`, `limit` up to 100, `sources` web, news or images, `tbs`, `lang`).
- `controllers/v2/scrape.ts` and `search.ts`: scrape returns credits in `data.metadata.creditsUsed`, search at the top level as `creditsUsed`.
- `lib/scrape-billing.ts`, `search/execute.ts`: 1 credit per returned document; 0 when no document comes back; +1 per extra PDF page when PDF parsing is on (the lab sends `parsers: []`); +1 with zero data retention; +4 for JSON extraction; x.com pages +29.
- `scraper/scrapeURL/shouldCheckRobots.ts`: a single scrape checks robots.txt only for teams with that flag or safe mode. Firecrawl's own robots user agent is `FirecrawlAgent` (`lib/robots-txt.ts`).
- `lib/parseApi.ts`: keys are `fc-` followed by a UUID without dashes.

From docs.firecrawl.dev/billing and firecrawl.dev/pricing (read 2026-10-22): Free plan 1,000 credits a month, 10 scrape or search requests a minute, no pay-as-you-go, HTTP 402 once used up. Hobby $19 a month for 5,000 credits; paid plans auto-recharge in $5 steps unless the monthly limit in billing settings is 0. A page that answers 403 or 404 still costs 1 credit. Search costs 2 credits per 10 results. Credits do not roll over (except Scale).

From the Terms of Use (firecrawl.dev/terms-of-service, read 2026-10-22): use must comply with laws and contracts; personal data of others may not be spread without permission; section 5.d.1 restricts commercial use unless authorized (the lab is personal, non-commercial research). The terms say nothing about robots.txt or storing scraped pages; that is left to the user.

Checked from this sandbox on 2026-10-22: `api.firecrawl.dev` is reachable (a keyless call answered 429: the keyless tier is per IP and was used up, so a key is needed). robots.txt today allows FirecrawlAgent on cointelegraph.com, coindesk.com, decrypt.co, theblock.co, okx.com announcements and binance.com support pages; it disallows news.google.com article links, binance.com `/bapi/` and reuters.com.

## Decisions

FC-1 Page text never reaches the public repo (ADOPTED). `data/memelab.sqlite`, `inbox/` and `state/` are public. Stored: a sha256 of the normalized text, a word count, the page's own times, statuses, credits, and identifiers found on it (contract addresses, address-bearing explorer or DEX links, cashtags, linked domains). The final URL is stored without query or fragment (it can carry session tokens). A private copy of the text goes to the gitignored private store for `private_copy_days` (7 by default, 0 to keep none), for re-extraction and manual review. Same principle as D-010, D-013, D-016 for social content.

FC-2 Platforms with their own decisions are refused before any request (ADOPTED). x.com and twitter.com (D-025, and 30 credits a page), reddit.com (D-127), discord.com and discord.gg (D-133), youtube.com and youtu.be (D-142), t.me and telegram (D-028), warpcast.com and farcaster.xyz (D-129), TikTok, Instagram, Facebook, Threads, LinkedIn. Search results on those hosts are dropped. URLs with credentials or non-http schemes are refused.

FC-3 The lab checks robots.txt itself (ADOPTED). RFC 9309 for user agent FirecrawlAgent: 2xx rules apply (the most specific group wins), 4xx means no rules, 429, 5xx or no answer means disallow everything. One refusal row per site per run; the site is not tried again for `retry_failed_after_hours` (24).

FC-4 Proxies: basic by default (PROPOSED for "auto", needs Elving). `auto` lets Firecrawl retry through its enhanced anti-bot proxies (no extra credits today). Getting past bot protection is a choice about a site's wishes, so it is off until Elving says otherwise. `stealth` and `enhanced` are not accepted in the config.

FC-5 No circumvention of location blocks (ADOPTED). Same rule as four.meme in docs/SOURCES.md. No `location` override is configurable. `pull_fallback.sources` is empty by default; Bybit (403 from US addresses) should not be listed. Binance's CMS API is disallowed by robots.txt, so it cannot be a fallback either.

FC-6 Credits are capped before every call (ADOPTED). Per run (`max_credits_per_run`), per UTC month from the lab's own ledger (`max_credits_per_month`, rows in `social_api_spend` with connector `firecrawl`), requests per run, and, once per run before the first billable call, the plan balance Firecrawl reports (`check_remote_balance`, keeping `min_remaining_credits` in reserve). A call whose worst case does not fit is not made. Both caps 0 means no live call. A cost per credit above 0 needs `allow_billable` (same rule as D-023 and D-036). A 401, 402 or 400 stops the run; 429 stops it as partial; 5xx and transport errors are retried once.

FC-7 No model reads page text (ADOPTED). Only regular expressions read it, and a base58 check rejects look-alike words. Firecrawl's LLM features (JSON format, summary, question, agent, extract) are not used: they would be a paid model run on untrusted text outside D-036 and D-039. Page text is evidence and never an instruction.

FC-8 A contract named on a page is FACT about the page, not about the token (ADOPTED). It earns NAMED_IN_SOURCE / STRONG for that exact mint only, which is what match.py always allowed when the contract sat in the snippet. It does not show that the token is official or that anyone bought it.

FC-9 Citation counts only on complete coverage (ADOPTED). The uncited count replaces the independence count only when every original and independent source was read. Thresholds are unchanged.

FC-10 Search results are aggregator items (ADOPTED). A new story from search starts as RUMOR; a reputable or official domain is recognized by its domain, as with Google News. URLs already stored and refused hosts are dropped before ingest. Relative dates are kept only to hour precision ("2 hours ago"); "3 days ago" stays unknown so an old story cannot look fresh. Only the hash of the query is stored.

FC-11 Fixture runs never touch the tracked database (ADOPTED). `--fixture` is refused when `MEMELAB_DB` is `data/memelab.sqlite`. Fixture rows carry `access_mode='fixture'`, never count as live coverage, and are never exported.

FC-12 Not operational (ADOPTED). No key, no config, no live call. Proof is on invented fixtures and in `tools/release_e2e.py` with the network blocked.

## Cost

The pipeline reads a page once. A run picks new events' original and independent sources only (copies are skipped), newest events first, official and reputable before aggregators. What one run can spend is capped by `max_pages_per_run` and `max_credits_per_run`.

Starting point for the Free plan (1,000 credits a month): `max_credits_per_run` 10, `max_credits_per_month` 900, `min_remaining_credits` 50, `search.enabled` false. That allows about 30 article reads a day across all runs. Turning search on costs 2 credits per query (limit 10); 3 queries in each of 5 daily passes is about 900 a month on its own, so search needs Hobby ($19, 5,000 credits) or fewer passes. These are estimates; `catalyst fc-health --remote` shows what was used and what is left, and a week of runs will show the real volume (the catalyst tables are not kept between scheduled sessions today, so there is no history to size it from).

## Setup (Elving)

1. Create a Firecrawl account and an API key. On the Free plan nothing can be charged. On a paid plan, set the pay-as-you-go monthly limit to 0 in Firecrawl's billing settings unless you want auto-recharge.
2. Put the key in the environment as `FIRECRAWL_API_KEY` on the machine or environment that runs the catalyst pass (never in a file in the repo; a config holding a key is refused).
3. Copy `docs/catalyst/firecrawl.example.json` to `data/private/firecrawl.json` (or point `MEMELAB_FIRECRAWL_CONFIG` at another path), set `enabled` true and the two credit caps.
4. `python -m memelab catalyst fc-health --remote` should print `configured_unverified` with the remaining credits; after the first live read it prints `live_ok`.

## First live run: check these

- Scrape response: `data.metadata.creditsUsed`, `publishedTime` and `statusCode` are where the source says.
- A typical reputable article returns more than a few hundred words with `onlyMainContent` and names contracts as plain text or as explorer links.
- The credit-usage answer has `remainingCredits` as a number.
- Rate limits on the Free plan: the 6.5 s pacing keeps a run under 10 requests a minute.
- If `pull_fallback.sources` gets an entry: whether a JSON or XML document comes back as raw text or wrapped in `<pre>` (both are handled; only the wrapped form was tested).

## Gaps and open items

- Scheduled runs: the daily and refresh tasks do not run these commands yet, and `data/private/firecrawl.json` does not exist in a scheduled session. Options: the task writes the config at the start of each run, or a non-secret config is committed under another path and `MEMELAB_FIRECRAWL_CONFIG` points at it. Elving's choice. Related: C-20.
- The catalyst tables themselves (events, items, links) are not in the state export, so each scheduled session's catalyst pass starts empty; corroboration and resurfacing across sessions do not work in scheduled runs. This predates Firecrawl. The page history added here survives; the events do not.
- EVM contracts named on pages are stored but the catalyst matcher is Solana-only. The social resolver (`social resolve`, D-031) handles Base, BNB and Ethereum and is the place to connect them.
- Dates named inside articles (listing dates, unlocks) are not extracted; `event_at` still comes from feeds.
- Not used: crawl, map, change tracking (would suit exchange listing pages and project roadmaps), batch scrape, self-hosting (supported by the config, not tested), the keyless tier.
- Licensing: the lab calls Firecrawl over HTTP and copies none of its code, and no SDK is used, so the AGPL-3.0 of the server does not reach this repo. A self-hosted server is a separate program. Not legal advice.
