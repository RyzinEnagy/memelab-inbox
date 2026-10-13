# Phase 03: X monitoring through the official X API v2

Source of truth: `memelab/social/x_api.py` (adapter, transports, billing guard, health), `memelab/social/cli.py` (`social x-health`, `social x-ingest`), migration 3 in `memelab/social/schema.py`, inbound schema `/2` in `memelab/social/ingest.py`. Tests: `tests/test_social_x_api.py` (36). Fixtures: `tests/fixtures/social/x_api/`. Example config: [x_api.example.json](x_api.example.json).

Related: [CONNECTORS_02.md](CONNECTORS_02.md) (ingestion contract), [DECISIONS.md](DECISIONS.md) (D-022 to D-025), [HANDOFF.md](HANDOFF.md).

## Status

Live X ingest is UNAVAILABLE. There is no X developer account, app or Bearer token on record, and no budget consent. `python -m memelab social x-health` reports `credentials_missing` and `live_evidence: none`. No live X API call has been made by this project. Everything below is proved on recorded synthetic HTTP fixtures, and those rows are labelled `fixture` in every table they touch.

## What the official docs say (checked 2026-10-10)

FACT, from docs.x.com on 2026-10-10. Prices and limits change; recheck before enabling.

- Pricing is pay-per-use with prepaid credits, no subscription tier listed. Reads are charged per resource returned: posts $0.005, users $0.010, lists $0.005 (also DM events $0.010, likes $0.001 and others). A resource returned again on the same UTC day is charged once ("soft guarantee"). Only successful responses that return data are billed. Pay-per-use is capped at 3 million post reads per month; above that is Enterprise. Spend limits and alerts are set in the Developer Console. ([pricing](https://docs.x.com/x-api/getting-started/pricing), [usage and billing](https://docs.x.com/x-api/fundamentals/post-cap))
- `GET /2/users/{id}/tweets`: app-only Bearer or user context; `max_results` 5 to 100; `pagination_token`, `since_id`, `until_id`, `start_time`, `end_time`; `exclude=replies,retweets`. The reference page states no depth cap. ([get posts](https://docs.x.com/x-api/users/get-posts))
- `GET /2/lists/{id}/tweets`: `max_results` 1 to 100 (default 100), `pagination_token`; no `since_id`. ([list posts](https://docs.x.com/x-api/lists/get-list-posts))
- `GET /2/tweets/search/recent`: last 7 days only; `query` up to 4096 characters; `max_results` 10 to 100; `next_token`; `since_id` (not together with `start_time`). Full-archive search exists but is not used here. ([recent search](https://docs.x.com/x-api/posts/search-recent-posts), [quickstart](https://docs.x.com/x-api/posts/search/quickstart/recent-search))
- Rate limits per 15 minutes, app-only: recent search 450, user posts 10,000, list posts 900, user by username 300, post lookup 3,500. Headers `x-rate-limit-limit`, `-remaining`, `-reset` (epoch seconds). 429 until the reset. ([rate limits](https://docs.x.com/x-api/fundamentals/rate-limits))
- Errors: problem objects `{type, title, detail}`. 401 bad credentials; 403 with `client-forbidden` (app not enrolled or lacks access) or `not-authorized-for-resource` (protected or private); 404 `resource-not-found`; 429 `rate-limit-exceeded`; a 200 can carry partial `errors`. ([response codes](https://docs.x.com/x-api/fundamentals/response-codes-and-errors))
- Developer Guidelines: content deleted or removed on X must be removed from your systems within 24 hours; X data must be deleted within 10 business days if API access ends; no ML training on X data; no deriving sensitive attributes; "Non-API automation (scraping, browser automation) results in permanent suspension." ([developer guidelines](https://docs.x.com/developer-guidelines))

UNKNOWN until the first live call:

- Field parameter name. The quickstart examples use `tweet.fields`, `referenced_tweets` and `edit_history_tweet_ids`; the generated API reference pages show `post.fields`, `referenced_posts` and `edit_history_post_ids`. The adapter sends `tweet.fields` (config `fields_param` can switch it) and reads both response spellings.
- Whether expanded objects in `includes` (authors, referenced posts) are billed as reads. The billing guard assumes they are (worst case); the spend ledger records them as billed.
- The status code when prepaid credits run out (the docs say requests fail; 402 is mapped to BLOCKED just in case).

## What the adapter does

Scopes are explicit in a config file (`data/private/x_api.json`, gitignored; example in [x_api.example.json](x_api.example.json)). Nothing is discovered on its own.

| Scope kind | Endpoint | Incremental | Cannot see |
|---|---|---|---|
| `user` (username or user_id) | `/2/users/{id}/tweets` | `since_id` from the cursor | protected accounts; quotes and replies by other accounts; replies or reposts when excluded |
| `list` | `/2/lists/{id}/tweets` | cursor applied client-side (no `since_id`), stops paging at the cursor | private lists (need user-context auth, not used) |
| `search` | `/2/tweets/search/recent` | `since_id` | anything older than 7 days; protected posts |
| `recheck` | `/2/tweets?ids=` | none | deleted, never existed and suspended author all look the same (NOT_FOUND) |

The "cannot see" text is written into every envelope (`source.terms_note`), so it is stored in `social_observation_provenance.terms_note` next to each observation.

Per post it stores: post id, author user id and handle, link (`https://x.com/<handle>/status/<id>`), provider time (`created_at`, basis PROVIDER), fetch time (response time), a sha256 of the normalized text (long-form `note_tweet` text when present), public metric counts, and context: reference type ORIGINAL / REPLY / REPOST / QUOTE (UNKNOWN when not requested), conversation id, in-reply-to user id, edit history ids, and each referenced post with its original author id. The text itself is hashed in memory and dropped. Summaries are not generated by the adapter (D-010: own-words summaries are written by a session).

Event ids are `api.<post id>.<hash of state>`: the same post in the same state from any scope or rerun is a duplicate; a change in metrics, handle or edit history is a new sighting. Handles are keyed by user id, so a renamed account stays one account and `social_account_handles` keeps both names.

Edits create a new post id on X. The new id carries the full edit history; the old version keeps the history that was visible when it was read. Deletions never show up in timelines or search: a post simply stops appearing. The `recheck` scope looks stored posts up again and records NOT_FOUND or PROTECTED sightings. That is the only deletion signal available without the Enterprise compliance stream.

## Safety rails

- Credentials: env `X_BEARER_TOKEN` only. The config refuses any key that looks like a credential. The token is sent in one header, never logged, stored or returned; transport errors are re-raised with the token scrubbed (`test_token_never_leaks` injects an error message that contains it).
- No credentials: `social x-ingest` (live) prints `NOT_RUN credentials_missing` and exits 1 before any network call. The adapter itself reports every scope BLOCKED `credentials_missing` if reached.
- Billing guard: a request is made only when `budget.allow_billable` is true and its worst case (`max_results` posts, the same number of referenced posts, two users per post) fits the per-run cap and the per-month cap. Month spend is the sum of `social_api_spend` rows of the same mode, so fixture rows never use or prove live budget. Defaults are off and zero. The ingest `Budget(max_cost=...)` is honoured as well.
- Rate limits: 429 stops the scope, records `rate_limit_reset_at`, and later runs skip the scope until then (`max_rate_wait_seconds` allows one short wait, default 0). `x-rate-limit-remaining: 0` stops before the next page.
- Errors: 401 and 402 BLOCKED, 403 BLOCKED split by problem type, 404 and 400 DOWN, 5xx and network errors three attempts with backoff then DOWN. Problem `detail` is never copied (it can echo ids or query text).
- Cursor: `social_source_cursors.newest_id` advances only after `ingest()` committed every page of the scope (checkpoint COMPLETE). A page cap stop advances it and records a GAP coverage row saying older posts were not read.
- Fixture mode labels every row: `access_mode='fixture'`, `collector='x-api-v2/fixture'`, `rights_basis='synthetic_fixture'`, spend `mode='fixture'`. `x-health` counts only `mode='live'` rows as live evidence.

## Commands

```
python -m memelab social x-health [--config data/private/x_api.json] [--db ...]
python -m memelab social x-ingest --config <cfg> --fixture tests/fixtures/social/x_api/fx_x_main.json --db <tmp> --now 1791561600
python -m memelab social x-ingest [--config data/private/x_api.json]          # live; refuses without token and consent
python -m memelab social status --event <event_id>
```

`x-health` exit 0 only when `ready`; otherwise 1 with `next_step`.

## How to authorize it (Elving's decision; nothing here has been done)

1. Decide whether to pay for X reads at all. D-009 says social data goes through signed-in Chrome first and paid APIs only with approval; see also D-025.
2. Sign in at the X Developer Console with the account that will own the app, accept the developer agreement, create a project and app. Do not use a personal account you cannot afford to lose.
3. Buy a small amount of prepaid credit and set a spend limit and alert in the console (the console limit is the real cap; the lab's guard is a second one).
4. Copy the app's Bearer Token. Do not paste it into a chat, a file in the repo or the config. Set it only in the shell that runs memelab: `export X_BEARER_TOKEN=...` (on Windows PowerShell: `$env:X_BEARER_TOKEN="..."`).
5. Copy `docs/social-intelligence/x_api.example.json` to `data/private/x_api.json`. Start with one scope, `max_results` 10 to 20, `max_pages_per_scope` 1. Set `budget.allow_billable` true, `max_usd_per_run` 0.50, `max_usd_per_month` a number you accept.
6. `python -m memelab social x-health` must say `ready`. Then run `python -m memelab social x-ingest` once and check `x-health` again: `live_evidence.successful` above 0, spend recorded, cursor set. Compare the estimated spend with the console.
7. Only then add scopes. Run `recheck` at least daily if live data is kept (24-hour deletion rule).

The cloud session cannot do steps 2 to 6: it has no X account and must not hold the token.

## Rough cost (INFERENCE, from the prices above)

One post read is $0.005; with author and referenced-post expansions the worst case is about $0.03 per post, usually less because users dedupe per day. Following 20 accounts that post 10 times a day each is 200 posts a day: roughly $1 to $6 a day, $30 to $180 a month, depending on expansions and reposts. A busy search query can cost far more; keep search scopes narrow (contract address, `-is:retweet`). Dropping the expansions (config `expansions: ""`) brings it to $0.005 per post but loses handles and original authors.

## Known limits

- No live verification of the request and response shapes; the fixtures follow the docs, not a recorded live call.
- Deletion compliance is not automatic: `recheck` records NOT_FOUND, but earlier observations (hash, metrics, ids) of that post are not purged. If live X data is ever kept, a purge step for posts NOT_FOUND for 24 hours is needed (carry-over C-3).
- Reposts are stored as the reposting account's item with `reference_type='REPOST'`; the original post is a reference (id and author), not its own observation.
- Spend is an estimate. The console is the bill.
- Health and coverage are per run, as in Phase 02.

## Migration 3 (exact DDL in `memelab/social/schema.py`)

`social_item_context` (reference type, conversation, reply-to user, edit history ids, basis), `social_item_refs` (replied_to / quoted / retweeted with original author id), `social_source_cursors` (newest id, resolved user id, last status, rate-limit reset), `social_api_spend` (one row per paid request: endpoint template, status, UTC billing day, resource counts, estimated cost, mode live/fixture), `social_api_billed_resources` (per-day billing dedupe). Ids, numbers and status words only; the content guard scans them like the other social tables. Down script drops the five tables; versions 1 and 2 are untouched.

Inbound schema `memelab.social.inbound/2` is `/1` plus an optional per-item `context` object (ids and enums only). `/1` units are read as before; a `context` key in a `/1` item is ignored and listed in `ignored_fields`.
