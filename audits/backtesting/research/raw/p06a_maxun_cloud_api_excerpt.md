# Maxun Cloud API documentation excerpt (retrieved 2026-10-23 with Firecrawl, scrapeId 01a169c0-cf00-7344-917f-e75afd94b290)

Source: https://docs.maxun.dev/api/cloud-api (verbatim lines relevant to Phase 06A)

- "From October 2026, the original `/api/robots` API is deprecated on Maxun Cloud. Use the v1 endpoints on this page."
- Base URL `https://app.maxun.dev/api/v1`; auth `Authorization: Bearer <api-key>` or `x-api-key: <api-key>`.
- Status table: "`402` | Not enough credits"; "`403` | Invalid API key, plan limit reached, or your team role doesn't allow it".
- "`POST /robots/{id}/runs` ... Each run needs at least 1 credit."
- Crawl config defaults: mode "domain", limit 50, maxDepth 3, useSitemap true, followLinks true, respectRobots true.

Source: https://docs.maxun.dev/robot/crawl (scrapeId 01a169c0-ceb6-76f8-8488-e02df8d1cb6a)

- "**Note:** URL Filtering is currently in development and not fully enforced."

Observed on 2026-10-23 instead of 402: HTTP 403 with body `{"success": false, "error": "Insufficient credits to perform this operation", "message": "Each data point requires 1/4 credits", "available": 0, "minimum": 0.25}` (bakeoff/p06a_maxun/run_start_crawl2_nocredit.json).
