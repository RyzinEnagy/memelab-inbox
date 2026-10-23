# Maxun capabilities and license (Phase 00 audit note, updated in Phase 04 and 06A)

This is an audit note, not a claim that any Maxun feature is live in the lab.

## Availability (2026-10-23)

| Level | State | Evidence |
|---|---|---|
| Installed (self-hosted OSS) | NO | no Maxun checkout, server or container on Elving's work computer; Docker not installed (`docker --version` returned nothing) |
| Configured | YES, Cloud | `D:\memelab\maxun-mcp.cmd` points `mcp-remote` at `https://app.maxun.dev/api/mcp`; key in `D:\memelab\maxun-token.txt` (32 bytes, never printed) |
| Authenticated | YES | `GET /api/v1/usage` HTTP 200 |
| Functional (a real run) | NOT YET | 0 robots, 0 runs on the account |
| Authorized | one-shot runs only, capped (Elving, 2026-10-23) | AskUserQuestion answer in session |
| Approved for persistent scheduling | NO | 0 schedules; must stay 0 |
| Claude MCP tools in this session | NO | Maxun MCP launcher exists but is not running in the desktop app's local MCP list |

Account: plan TRIAL, 5 credits, monthly cycle, rate limit 30 requests/min. Each run costs at least 1 credit (Cloud API docs). That caps a fair Maxun sample at about 5 runs unless a crawl robot covers several pages in one run.

## Editions and endpoints (verified from docs, retrieved 2026-10-23 with Firecrawl, scrapeId 01a16960-5594-7619-ab9d-8a49c2a7f420; and with Crawl4AI, sha256 45a02ace...)

- Cloud base URL `https://app.maxun.dev/api/v1`; auth `Authorization: Bearer <key>` or `x-api-key: <key>`. The original Cloud `/api/robots` API is deprecated from October 2026.
- Cloud robots: scrape, crawl (mode, limit, maxDepth, include/exclude paths, sitemap, respectRobots default true), search, document extract/parse; agents (prompt-built). Runs: `POST /robots/{id}/runs` (202, async), `GET /runs/{runId}` with `startedAt`, `finishedAt`, `isPartial`, `hasChanges`, `data.markdown`, `data.crawlData`. Monitoring diffs: `GET /runs/{runId}/diff`. Schedules: `PUT/GET/DELETE /robots/{id}/schedule`. Webhooks: up to 10 per robot, retries, test event.
- Self-hosted OSS API is a separate document (`/api/open-source-api`) with different routes; never mixed with Cloud routes.

## Source and license

- Repo `getmaxun/maxun` cloned shallow at `80ba04547eef4c4a39a16f9e4a1f1e18cdc48d63` (2026-10-22T02:44:59+05:30). `package.json`: name maxun, version 0.0.48, license `AGPL-3.0-or-later`. `LICENSE`: GNU AGPL v3.
- Self-hosting uses docker-compose with postgres:13, minio, maxun-backend, maxun-frontend and maxun-browser images.
- Install scripts were read, not run.

## License assessment for the lab (preliminary, closed in Phase 04)

- Calling Maxun Cloud over HTTPS from a thin adapter does not copy, modify or distribute Maxun source, so AGPL obligations do not attach to the lab's code. GO for "external hosted service + thin adapter".
- Vendoring or modifying Maxun source inside the lab would bring AGPL network-use obligations to the combined work. NO-GO without a separate legal decision by Elving.
- Self-hosting unmodified Maxun as a separate service would not by itself change the lab's license, but needs Docker, a database and an always-on service. Not authorized.

## Overlap with existing collectors

The lab already has: catalyst source registry and collectors (`memelab/catalyst/sources.py`, `bridge/catalyst.js`), Firecrawl page reads and news search (`memelab/catalyst/firecrawl.py`), and social connectors (X, Telegram, Discord, Reddit, YouTube, Farcaster) behind credentials. Any Maxun robot must beat these on a measured task before adoption (Phase 06A).
