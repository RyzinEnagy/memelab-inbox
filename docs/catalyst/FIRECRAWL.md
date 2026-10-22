# Firecrawl in Catalyst Intelligence

Module: `memelab/catalyst/firecrawl.py`. Commands: `catalyst fc-health`, `catalyst enrich`, `catalyst fc-search`, `catalyst pull-pages --firecrawl`. Example config: `firecrawl.example.json` (off). Tests: `tests/test_catalyst_firecrawl.py` (37). Fixtures: `tests/fixtures/catalyst/firecrawl/` (invented).

Status on 2026-10-22: built, proved on fixtures, and one supervised live run (Free plan key, 12 credits, scratch database; see "First live run"). Not wired into the scheduled runs yet.

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

FC-4 Proxies: basic (ADOPTED, Elving 2026-10-22). `auto` would let Firecrawl retry through its enhanced anti-bot proxies (no extra credits today); getting past bot protection is a choice about a site's wishes, and nothing in the first live run needed it. `stealth` and `enhanced` are not accepted in the config.

FC-5 No circumvention of location blocks (ADOPTED). Same rule as four.meme in docs/SOURCES.md. No `location` override is configurable. `pull_fallback.sources` is empty by default; Bybit (403 from US addresses) should not be listed. Binance's CMS API is disallowed by robots.txt, so it cannot be a fallback either.

FC-6 Credits are capped before every call (ADOPTED). Per run (`max_credits_per_run`), per UTC month from the lab's own ledger (`max_credits_per_month`, rows in `social_api_spend` with connector `firecrawl`), requests per run, and, once per run before the first billable call, the plan balance Firecrawl reports (`check_remote_balance`, keeping `min_remaining_credits` in reserve). A call whose worst case does not fit is not made. Both caps 0 means no live call. A cost per credit above 0 needs `allow_billable` (same rule as D-023 and D-036). A 401, 402 or 400 stops the run; 429 stops it as partial; 5xx and transport errors are retried once.

FC-7 No model reads page text (ADOPTED). Only regular expressions read it, and a base58 check rejects look-alike words. Firecrawl's LLM features (JSON format, summary, question, agent, extract) are not used: they would be a paid model run on untrusted text outside D-036 and D-039. Page text is evidence and never an instruction.

FC-8 A contract named on a page is FACT about the page, not about the token (ADOPTED). It earns NAMED_IN_SOURCE / STRONG for that exact mint only, which is what match.py always allowed when the contract sat in the snippet. It does not show that the token is official or that anyone bought it.

FC-9 Citation counts only on complete coverage (ADOPTED). The uncited count replaces the independence count only when every original and independent source was read. Thresholds are unchanged.

FC-10 Search results are aggregator items (ADOPTED). A new story from search starts as RUMOR; a reputable or official domain is recognized by its domain, as with Google News. URLs already stored and refused hosts are dropped before ingest. Relative dates are kept only to hour precision ("2 hours ago"); "3 days ago" stays unknown so an old story cannot look fresh. Only the hash of the query is stored.

FC-11 Fixture runs never touch the tracked database (ADOPTED). `--fixture` is refused when `MEMELAB_DB` is `data/memelab.sqlite`. Fixture rows carry `access_mode='fixture'`, never count as live coverage, and are never exported.

FC-12 Live use is supervised so far (ADOPTED). One live run on 2026-10-22 in a scratch database; the tracked database and the inbox were not touched. Fixture proof stays in `tools/release_e2e.py` with the network blocked.

FC-13 Credits go to memecoin stories first (ADOPTED, HEURISTIC). With `enrich.relevance` "memecoin" (default) an event is read or searched only when its title or snippet names a ticker ("$X" or "(XYZ)") or uses memecoin, launch, listing or venue words (`RELEVANCE_RX`). The category alone does not qualify: the catalyst classifier files spot ETF flow stories as ACCESS. An explicit `--event` is read regardless. "all" turns the filter off. It decides only which pages are read, never a grade or a score.

FC-15 Search is on in the scheduled runs, at most once per `search.min_hours_between_runs` (ADOPTED, Elving 2026-10-22). Default 10 h, counted from the ledger, which travels between sessions in the state export. A pass that comes too soon skips search and says SEARCH_TOO_SOON; enrichment still runs.

FC-16 The key lives in the environment or in a token file, never in a config, a prompt or the repo (ADOPTED, Elving 2026-10-22). Order: `FIRECRAWL_API_KEY`, then the first `firecrawl_token.txt` found at `MEMELAB_FIRECRAWL_TOKEN_FILE`, `data/private/`, the repo root, a Cowork connected folder (`~/mnt/memelab/`, `~/mnt/*/`) or `C:\Users\<user>\memelab\`, the same places `commit_file.py` looks for `gh_token.txt`. `firecrawl_token.txt` is in .gitignore. `catalyst fc-health` names the source, never the value.

FC-14 A page time without a zone is UNKNOWN (ADOPTED). Decrypt and CoinDesk publish `article:published_time` without an offset; read in the machine's zone it was 4 hours off on the first live run. Same rule as D-019 for social timestamps.

## Cost

The pipeline reads a page once. A run picks new events' original and independent sources only (copies are skipped), memecoin-relevant events first (FC-13), newest first, official and reputable before aggregators. What one run can spend is capped by `max_pages_per_run` and `max_credits_per_run`.

Measured on 2026-10-22 from one pull of the registry's news feeds (553 items, 470 events, about three days of feed history): 179 article URLs were eligible, 67 of them Google News links that robots.txt refuses (no credit). Of the 112 publisher articles, 14 passed the relevance filter; about 3 to 5 relevant new articles a day. Without the filter the backlog was 112 and about 59 new a day.

Starting point for the Free plan (1,000 credits a month): `max_credits_per_run` 10, `max_credits_per_month` 900, `min_remaining_credits` 50, relevance "memecoin". Enrichment then needs roughly 100 to 150 credits a month. Search costs 2 credits per query and is where most memecoin stories become readable (they reach the lab through Google News, whose article links cannot be read): 3 queries in 2 passes a day is about 360 credits a month, plus about 1 credit for each new publisher article it surfaces. Both together fit the Free plan under a 900 cap. Five passes a day with search needs Hobby ($19, 5,000 credits). `catalyst fc-health --remote` shows what was used and what is left.

## Setup (Elving)

1. Firecrawl account and API key: done 2026-10-22 (Free plan). On a paid plan, set the pay-as-you-go monthly limit to 0 in Firecrawl's billing settings unless you want auto-recharge. The key was pasted into a chat once; rotate it in the Firecrawl dashboard if that chat is shared.
2. Key file: in the memelab folder on the computer the scheduled tasks use (`C:\Users\<you>\memelab\`, next to `gh_token.txt`), create `firecrawl_token.txt` holding only the key on one line (FC-16). For a one-off run in a terminal, `FIRECRAWL_API_KEY` in the environment works too.
3. Config: scheduled runs copy `docs/catalyst/firecrawl.scheduled.json` (enabled, 10 credits a run, 900 a month, 50 in reserve, search on, basic proxy, memecoin relevance) to `data/private/firecrawl.json`. For a local run, copy that file or `firecrawl.example.json` there yourself, or point `MEMELAB_FIRECRAWL_CONFIG` at it.
4. `python -m memelab catalyst fc-health --remote` should print `live_ok` (or `configured_unverified` before the first live call) with the key source and the remaining credits.

## Scheduled runs

Both memelab scheduled tasks carry a guarded Firecrawl step (added 2026-10-22): copy the scheduled config and the key file into the session's `data/private/`, run `catalyst fc-health`, and only when it exits 0 run `catalyst fc-search --events 5` and `catalyst enrich` between `catalyst ingest` and `catalyst match-plan`. The tasks rebuild the project from `main`, so the step is a no-op (the command does not exist there and the health check fails) until this branch is merged. The state export already carries the page reads and the spend ledger between sessions.

## First live run (2026-10-22)

Free plan, 1,000 plan credits, billing period 2026-10-22 to 2026-11-22. Scratch database, news feeds pulled directly (10 of 12 navigate-mode sources; Google News base-memecoin answered 503, Bybit 403). Two enrich passes, 12 credits in all, 0 failures.

Confirmed:
- `/v2/team/credit-usage` answers `remainingCredits`, `planCredits`, `billingPeriodStart`, `billingPeriodEnd` and costs nothing.
- Scrape metadata has `statusCode`, `creditsUsed` (1 per page), `cacheState` (all "hit": popular articles come from Firecrawl's cache, still 1 credit), `proxyUsed` ("basic"), `language` ("en", "en-US"), `publishedTime` and `modifiedTime` (Cointelegraph and The Block with an offset; Decrypt and CoinDesk without, see FC-14).
- Articles came back at 1,155 to 7,267 words with `onlyMainContent`; related-article lists and newsletter prompts are still included. Linked domains include share buttons (flipboard, google). Neither affects a score; a contract in a sidebar list could, so watch NAMED_IN_SOURCE links on pages with long related lists.
- Pacing: 4 requests in 22 s.
- End to end: Decrypt's article on the "Dacity" meme coin links a pump.fun Solana contract that the RSS snippet did not contain. Enrich stored it as an address link, match searched it by address on Jupiter and DEX Screener, and the event got a NAMED_IN_SOURCE / STRONG link to that mint (Jupiter reported about $1.0M liquidity). Before this change the same event could only reach a ticker or name match.

Still to check: a JSON or XML document through `pull_fallback` (only the `<pre>`-wrapped form is tested; Binance's API is disallowed by robots.txt, OKX is reachable directly, so no fallback source is listed yet).

## Gaps and open items

- Scheduled runs: wired with a guard (see "Scheduled runs"), active once the branch is on `main`. Related: C-20.
- The catalyst tables themselves (events, items, links) are not in the state export, so each scheduled session's catalyst pass starts empty; corroboration and resurfacing across sessions do not work in scheduled runs. This predates Firecrawl. The page history added here survives; the events do not.
- EVM contracts named on pages are stored but the catalyst matcher is Solana-only. The social resolver (`social resolve`, D-031) handles Base, BNB and Ethereum and is the place to connect them.
- Dates named inside articles (listing dates, unlocks) are not extracted; `event_at` still comes from feeds.
- Not used: crawl, map, change tracking (would suit exchange listing pages and project roadmaps), batch scrape, self-hosting (supported by the config, not tested), the keyless tier.
- Licensing: the lab calls Firecrawl over HTTP and copies none of its code, and no SDK is used, so the AGPL-3.0 of the server does not reach this repo. A self-hosted server is a separate program. Not legal advice.
