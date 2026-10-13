# Phase 19: optional Reddit and Farcaster sources

Prompt 19 (optional) after Phase 18 was accepted (pull request #1 merged into `main` as `f084b60`). Two separate adapters, both on official or protocol-native APIs, both built and proved on recorded synthetic fixtures. Neither is live: Reddit needs Reddit's written approval and app credentials, Farcaster needs a node or a hosted hub that Elving chooses. No live call was made in this phase and none is claimed.

Related: [DECISIONS.md](DECISIONS.md) D-125 to D-131, [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md), [OPERATIONS.md](OPERATIONS.md), [CONNECTORS_02.md](CONNECTORS_02.md) (inbound schema), [CLAIMS_06.md](CLAIMS_06.md), [NARRATIVES_07.md](NARRATIVES_07.md).

## What was read (2026-10-12)

Reddit:

- Reddit Data API Wiki, support.reddithelp.com/hc/en-us/articles/16160319875092: OAuth required for all traffic, unique User-Agent `<platform>:<app id>:<version> (by /u/<username>)`, 100 queries per minute per OAuth client id averaged over 10 minutes, headers X-Ratelimit-Used, -Remaining, -Reset; deleted posts, comments and accounts must be removed from stored data, Reddit recommends within 48 hours, and keeping deleted content is a violation even if de-identified.
- Responsible Builder Policy, support.reddithelp.com/hc/en-us/articles/42728983564564: explicit approval is required before any Reddit data is accessed through the API; selling, licensing or sharing data and training models need separate written approval; no inference of sensitive characteristics, no re-identification.
- Endpoint shapes (`/api/v1/access_token`, `/r/{sub}/about`, `/r/{sub}/new`, `/r/{sub}/comments`, `/api/info`, Listing and `t1`/`t3` fields such as `name`, `author_fullname`, `parent_id`, `link_id`, `edited`, `crosspost_parent`, `removed_by_category`) are the long-standing Data API shapes. They were not re-read from Reddit's API reference in this phase; the fixtures follow those shapes and the first live run must confirm them (see "First live run" below).

Farcaster:

- Snapchain HTTP API pages (docs.neynar.com/snapchain/httpapi/httpapi, casts, reactions, userdata): node serves HTTP on port 3381; `castsByFid`, `castsByParent` (`url` for a channel), `castById`, `reactionsByCast` (`reaction_type` Recast), `userDataByFid` (`user_data_type` 6 = USER_DATA_TYPE_USERNAME); list replies are `{messages, nextPageToken}` with an empty token at the end; timestamps are seconds since the Farcaster epoch 2021-01-01T00:00:00Z. No authentication is documented for a self-hosted node and no public node is documented.
- Farcaster docs, docs.farcaster.xyz/developers/guides/querying/fetch-channel-casts: channel casts through `castsByParent` with the channel's parent URL.
- Neynar pricing page: a free plan with compute units and paid plans from $9 a month; whether the free plan includes the hosted hub endpoint is not clear from the page. Neynar has announced it is acquiring Farcaster (neynar.com/blog/neynar-is-acquiring-farcaster), and the Snapchain docs now live on its site.
- Not documented anywhere read: rate limits of a self-hosted node, the exact error body for a missing cast (the adapter treats HTTP 404, or a 400/404 with `errCode` containing `not_found`, as NOT_FOUND), the `parentUrl` field in examples. The cast web link `https://farcaster.xyz/<username>/<first 10 characters of the hash>` is the lab's convention from the old Warpcast share format, not checked.

## Reddit adapter (`memelab/social/reddit_api.py`)

Scope: only communities listed in `data/private/reddit_api.json`. Per community, submissions (`/new`), comments (`/comments`) or both. Then a recheck of stored items (`/api/info`, 100 ids per call) that were first stored in an earlier run.

| Reddit field | Stored as |
|---|---|
| `name` (`t3_...`, `t1_...`) | `provider_item_id`, item key `reddit:<fullname>` |
| `author_fullname` (`t2_...`), `author` | account provider id and handle; profile URL `https://www.reddit.com/user/<name>/` |
| `created_utc` | provider publication time |
| `edited` (epoch) | `social_item_versions` row, kind EDIT, at the edit time; ORIGINAL at creation otherwise |
| title + body (+ link target for link posts), or comment body | `content_hash` only (sha256 of normalized text); words dropped in memory |
| `score`, `num_comments`, `upvote_ratio`, `num_crossposts` | metrics (Reddit fuzzes scores) |
| `parent_id`, `link_id` | REPLY with a `replied_to` reference; thread id as `conversation_id` |
| `crosspost_parent`, `crosspost_parent_list[0].author_fullname` | REPOST with a `retweeted` reference to the original id and its author id |
| `[deleted]`, `[removed]`, `removed_by_category` | `retrieval_status` DELETED, no hash, no metrics, no author |
| author `[deleted]` with content still there | account deleted: item stored without an author; the purge erases the stored account |
| subreddit type not public, restricted or archived; quarantined | community not read (BLOCKED `not_public`); an item that says private is quarantined by the ingester |

URLs carry ids only (`https://www.reddit.com/comments/<post>/` and `.../comments/<post>/_/<comment>/`) because the usual slug is the title. Titles, bodies, flair, link targets, community descriptions, display names and anything from the cross-posted original's community are never stored.

Independent threads vs cross-post amplification: a cross-post is a REPOST of its original (D-029), so `store.is_independent_original` is false and the narrative engine counts it as an amplifier of one dependency group (D-042). Two separate submissions of the same link are separate originals unless their title and body hash the same, in which case the existing identical-text heuristic applies (D-046). The original's own community is not read unless it is also approved.

Access gates, in this order, each before any network call: config has `access_approval.approved` true and `commercial_use` false; `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` are set. Then a client-credentials token, held in memory only.

Rate limits: 429 records the reset time and stops every scope (one client id shares one limit); X-Ratelimit-Remaining below `min_remaining` (default 5) stops before the next page; the next run does not call before the reset. 5xx and network errors get 3 attempts with backoff. Default caps: 100 items per page, 3 pages per listing (example config: 1), 30 requests per run (example: 20).

Deletion compliance (D-128): after every ingest the CLI runs `purge_deleted`. For each Reddit item with a DELETED or NOT_FOUND sighting it clears content hashes, summaries, metrics and private refs on all its observations, removes its version rows, claim spans and claim summaries, blanks extraction outputs (content hash set to 64 zeros, output and cache key NULL), deletes private copies of the text, and unlinks the author from the item, its observations and claims. For a deleted account it deletes the account row and handle history and unlinks it everywhere. Ids and the DELETED or NOT_FOUND sighting stay. `reddit-health` reports `deletion_purge_pending_items`.

## Farcaster adapter (`memelab/social/farcaster_hub.py`)

Scope: fids and channels listed in `data/private/farcaster_hub.json`. Then recasts (Recast reactions) of the casts read in this run, capped (default 20 casts), and a recheck (`castById`) of stored casts from earlier runs.

| Snapchain field | Stored as |
|---|---|
| message `hash` (0x + 40 hex) | `provider_item_id`, item key `farcaster:<hash>` |
| `data.fid` | account provider id; handle from `USER_DATA_TYPE_USERNAME` only (one lookup per fid per run, at most 200) |
| `data.timestamp` | publication time = 2021-01-01T00:00:00Z + timestamp |
| `castAddBody.text` plus embedded URLs | `content_hash` only |
| `parentCastId` | REPLY with a `replied_to` reference and the parent fid |
| embedded `castId` | QUOTE with a `quoted` reference (own words, independent per D-029) |
| Recast reaction | its own item, REPOST with a `retweeted` reference to the target cast; no text |
| `castById` miss | NOT_FOUND sighting (remove and never-existed look the same) |

Casts cannot be edited (a change is a remove plus a new cast), so every cast gets one ORIGINAL version row. Bio, profile picture, display name, location and linked accounts are never requested. Likes are not read. There are no private casts on Farcaster.

Gates: `hub.base_url` must be https, or http only for a node on this machine; `billing` is `self_hosted` (no key, no per-request charge) or `metered` (API key from the environment variable named in `hub.api_key_env`, sent in `hub.api_key_header`, plus `budget.allow_billable` true and a non-zero `max_usd_per_run`). A config holding a key is refused. 429 stops the run and records `retry-after`. Request cap per run (default 60) and a cost cap per run for metered hubs; every request writes a `social_api_spend` row with its estimated cost.

## Shared pieces (`memelab/social/api_common.py`, `memelab/social/sources_cli.py`)

- Recorded-fixture transport matched on method, path and exact parameters; request guard; cursor helpers on `social_source_cursors`.
- `TextSink` and `extract_after_ingest` (D-130): with `--extract`, the adapter keeps `{(platform, id, hash): text}` in memory until ingest has stored the observation, runs Phase 06 extraction (deterministic token references without a model; `analysis_unavailable` for the model part), then clears the sink. Text is never written. A re-sighting of words already analysed is skipped, so cursor overlap and recheck do not create a second claim set.
- Commands: `social reddit-health`, `reddit-ingest`, `reddit-purge`, `fc-health`, `fc-ingest`, `social sources` (every social connector with status, credentials, cost, live requests and next step; no network).

## Mapping onto the Phase 02 schema (D-126)

Both adapters emit `memelab.social.inbound/3` envelopes through the shared ingester: same validation, quarantine, checkpoints, provenance, health and coverage as X and Telegram. No migration; the public schema stays at 12. `reddit` was added to the platform list (`ingest.PLATFORMS`, `registry.PLATFORMS`); `farcaster` was already there. The reference type names come from the X adapter: `retweeted` is used as the generic repost reference for a Reddit cross-post and a Farcaster recast.

## Proof

Fixtures (invented, generated once and committed): `tests/fixtures/social/reddit_api/` (config, main run, second run) and `tests/fixtures/social/farcaster_hub/` (config, main run, second run).

Tests: `tests/test_social_reddit.py` (23) and `tests/test_social_farcaster.py` (14). They cover submissions, comments, cross-posts, deleted and removed items, edits, account deletion, a comment from another community being dropped, text never stored (titles, bodies, flair, slugs, the cross-posted original), provenance and fixture labels, rerun dedupe, cursor and recheck, the purge (including claim spans, extraction outputs and private copies), approval, credentials, commercial use, private and quarantined communities, 401, 429 with a reset that the next run respects, low remaining, page and request caps, 5xx retries, secret redaction; casts, replies, quotes, recasts, the Farcaster epoch, username-only lookups, metered key and consent gates, cost recording and cap, unsafe base URLs, 429 with retry-after, 401, removed casts, no duplicate claims on re-sighting; health states with the network patched to fail; and for each adapter the CLI flow source to storage to claim to narrative to brief.

Source to report on the fixtures (from `tools/release_e2e.py` stages 19, also in the tests):

- Reddit: 8 items stored (one comment from another community dropped), 6 texts extracted in memory, 3 token-reference claims for the LABDOG fixture contract; narrative snapshot for 2026-10-10: one cluster, 3 mentions, 2 independent sources (the reply depends on the post it answers); the brief lists it HIGH with id-only Reddit links. Second run: 1 new post, recheck marks one post DELETED and one NOT_FOUND, one account deleted; purge clears 2 items and erases 1 account.
- Farcaster: 6 items (2 casts by fid 9001, 2 channel casts, 2 recasts), 4 texts extracted, 2 claims; snapshot: one cluster, 2 independent sources; recasts and the quote do not add independence. Second run: recheck marks the removed reply NOT_FOUND; re-sighted words are not extracted again.

## Cost and health

| Connector | Cost | Health command | Status in this repo today |
|---|---|---|---|
| reddit_api | free tier, non-commercial only, 100 queries per minute per client; estimated $0 per request | `social reddit-health` | `not_configured` (no private config); with the example config `approval_missing` |
| farcaster_hub | self-hosted node: $0 per request (own server); hosted hub: metered, estimate set in config | `social fc-health` | `not_configured` (no base URL) |

Both health commands make no network call and exit 1 until the status is `ready`. Live ingest refuses with `NOT_RUN` and the reason before any call. Only `mode='live'` rows in `social_api_spend` count as live evidence.

## Setup (for Elving, when you decide to turn one on)

Reddit:

1. Decide whether you want Reddit at all. Access is free but needs Reddit's approval for your use case (personal, non-commercial research on public posts in named communities). Your stated preference is to avoid paid APIs; this one is not paid, but it is gated.
2. Request Data API access from Reddit (Responsible Builder Policy, link above). Say what it is: a personal research tool that reads a few named public communities, stores ids, times, counts and hashes, never text, and deletes what it derived from deleted posts at the next run. Do not mention or plan commercial use or model training.
3. After approval, create the app Reddit tells you to create. Keep the client id and secret out of chat and out of the repo.
4. Copy `docs/social-intelligence/reddit_api.example.json` to `data/private/reddit_api.json`. Set `user_agent.reddit_username` to your Reddit username, list the communities, set `access_approval.approved` to true and `access_approval.reference` to Reddit's ticket or approval note.
5. In the shell that runs memelab: `export REDDIT_CLIENT_ID=...` and `export REDDIT_CLIENT_SECRET=...`.
6. `python -m memelab social reddit-health` must say `ready`. Then one small run: `python -m memelab social reddit-ingest --extract`, then `social reddit-health` again: `live_evidence` must show a successful request.

Farcaster:

1. Choose a route. Free: run your own Snapchain node (see the Snapchain getting-started page; it needs a server with disk and bandwidth). Metered: a hosted hub such as Neynar's, with an API key and a monthly plan.
2. Copy `docs/social-intelligence/farcaster_hub.example.json` to `data/private/farcaster_hub.json`. For your own node set `hub.base_url` to `http://127.0.0.1:3381` and keep `billing` `self_hosted`. For a hosted hub set the https base URL, `billing` `metered`, the per-request estimate, `budget.allow_billable` true and a run cap, and export the key in the variable named by `hub.api_key_env`.
3. List the fids and channels (channel id plus its parent URL).
4. `python -m memelab social fc-health` must say `ready`. Then `python -m memelab social fc-ingest --extract` and check `fc-health` `live_evidence`.

## First live run: what to confirm

- Reddit: the token response, `/about` fields, Listing shape, the `edited` and `removed_by_category` values and the rate-limit headers match the fixtures; a deleted test comment shows `[deleted]`; record the result in this file and in SOURCE_COVERAGE.md.
- Farcaster: the error body for a removed cast; whether the node rate-limits; the channel parent URL form for the channels chosen.

## Not done, and why

- No live call: no Reddit approval or credentials, no Farcaster node or hosted hub (D-131).
- Derived claim rows of deleted Reddit posts (contract address, category) and dated narrative snapshot counts are kept; whether Reddit's deletion rule requires dropping those too is Elving's call (D-128, PROPOSED part).
- Reddit comments older than the newest listing page are not backfilled; comment trees under a post are not walked (`/comments/<id>` not used).
- Farcaster replies under channel casts are not walked (`castsByParent` with fid and hash not used); likes are not read.
- No scheduled job runs either adapter (Phase 20 territory).
