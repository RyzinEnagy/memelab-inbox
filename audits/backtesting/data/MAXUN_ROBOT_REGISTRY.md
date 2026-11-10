# Maxun robot registry (Phase 06A)

Adopted robots: none. Decision EXISTING_TOOL_WINS (research/MAXUN_ADOPTION.md).

## Robots that exist on the account (evaluation only)

| Robot | Type | Target | Schedule | Webhooks | Monitoring alerts | Runs | State |
|---|---|---|---|---|---|---|---|
| `ef435421-7926-43d2-89ea-0ad337cf05db` "memelab-p06a-solana-news-crawl" | crawl (Cloud v1) | `https://solana.com/news`, mode path, limit 12, maxDepth 1, includePaths `/news/.*`, robots respected | none (`GET /robots/{id}/schedule` returned null; `GET /schedules` returned []) | none | off (`compareRuns` false) | 1: `005f58a3-4fff-4b2e-8750-b5e4947eb291`, aborted after 5 pages when credits ran out | idle, cannot run (0 credits) |

Owner: Elving's Maxun Cloud trial account. Created 2026-10-23T17:26:34Z through `POST /api/v1/robots/crawl`.

## Disable and removal

- It has no schedule, so nothing runs unless someone starts it. Check with `GET https://app.maxun.dev/api/v1/schedules` (must be `[]`).
- To remove it and its one run: `DELETE https://app.maxun.dev/api/v1/robots/ef435421-7926-43d2-89ea-0ad337cf05db` with the account key. Not done here because the run is evidence for this phase and deleting needs no credits later. Elving may delete it at any time.
- The lab runtime contains no Maxun client (test `test_g40_maxun_is_not_a_runtime_path_and_runtime_has_no_maxun_or_webhook_code`), so removing the robot changes nothing in the lab.

## Domain allowlists in use (existing collectors, `memelab/backtest/sources/webcapture.py`)

| Use case | Allowed pattern | Extra rule | Page cap per run |
|---|---|---|---|
| project_catalyst_watch | `https://solana.com/news/<slug>` | the /news index itself is refused | 20 |
| developer_release_watch | `https://github.com/<owner>/<repo>/releases/tag/<tag>` | owner/repo must be one of 11 tracked repositories | 20 |
