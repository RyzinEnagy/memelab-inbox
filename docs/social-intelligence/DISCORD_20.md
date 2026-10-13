# Phase 20: optional Discord community monitoring

Optional Prompt 20, run after Phase 19. One adapter (`memelab/social/discord_bot.py`) with two routes: the bot REST API (the live route) and a gateway protocol layer proved on recorded frames. Built and proved on invented fixtures. Not live: there is no bot application, no token and no server whose admin has agreed. No live call was made and none is claimed.

Related: [DECISIONS.md](DECISIONS.md) D-132 to D-140, [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md), [OPERATIONS.md](OPERATIONS.md), [SOURCES_19.md](SOURCES_19.md) (the two adapters this one follows), [CONNECTORS_02.md](CONNECTORS_02.md) (inbound schema).

## What was read (2026-10-12)

All on docs.discord.com (the old discord.com/developers/docs paths now redirect there), plus Discord's policy pages.

- Gateway (events/gateway): privileged intents are GUILD_PRESENCES, GUILD_MEMBERS and MESSAGE_CONTENT. MESSAGE_CONTENT is `1 << 15`; "Apps without the intent will receive empty values in fields that contain user-inputted content": `content`, `embeds`, `attachments`, `components`, `poll`; exceptions are the app's own messages, DMs with the app, messages that mention the app, and context-menu targets. GUILD_MESSAGES is `1 << 9` and carries MESSAGE_CREATE, MESSAGE_UPDATE, MESSAGE_DELETE, MESSAGE_DELETE_BULK. Close code 4014 when an app asks for "a privileged intent that hasn't been configured or approved", 4013 for invalid intents. Verified apps (required for 100+ servers) need the intent approved. Resume uses `session_id`, `resume_gateway_url` and the last `seq`; 120 gateway events per connection per 60 seconds; 1000 IDENTIFY per 24 hours.
- Gateway events (events/gateway-events): MESSAGE_CREATE adds `guild_id`, `member`, `mentions`; MESSAGE_UPDATE is a message object with the same extra fields (the docs do not say whether it can be partial); MESSAGE_DELETE has `id`, `channel_id`, `guild_id`; MESSAGE_DELETE_BULK has `ids`; GUILD_DELETE without `unavailable` means the user (bot) was removed; INVALID_SESSION `d` says whether the session is resumable.
- Opcodes and close codes (topics/opcodes-and-status-codes): 4004 authentication failed, 4010 to 4014 do not allow a reconnect; JSON codes 10003 Unknown channel, 10004 Unknown guild, 10008 Unknown message, 50001 Missing access, 50013 lack of permissions.
- Messages (resources/message): `id`, `channel_id`, `author`, `content`, `timestamp`, `edited_timestamp`, `type` (19 REPLY), `message_reference` (type 0 DEFAULT for replies, 1 FORWARD with `message_snapshots`), `referenced_message` (null when the referenced message was deleted), `webhook_id`. Get Channel Messages: `GET /channels/{id}/messages`, one of `around`, `before`, `after`, `limit` 1 to 100; needs VIEW_CHANNEL, and "returns no messages" without READ_MESSAGE_HISTORY. A snapshot has no author.
- Rate limits (topics/rate-limits): headers X-RateLimit-Limit, -Remaining, -Reset, -Reset-After, -Bucket; on 429 also -Global and -Scope (`user`, `global`, `shared`); body `retry_after`, `global`; 50 requests per second per bot; 10,000 invalid requests (401, 403, 429 except scope shared) per 10 minutes lead to a temporary IP restriction.
- Permissions (topics/permissions): ADMINISTRATOR `1 << 3`, VIEW_CHANNEL `1 << 10`, READ_MESSAGE_HISTORY `1 << 16`; the computation order (owner, @everyone plus member roles, administrator, then overwrites @everyone, member roles, member).
- Application (resources/application): `GET /applications/@me`; flags GATEWAY_MESSAGE_CONTENT `1 << 18` (100+ servers, approved) and GATEWAY_MESSAGE_CONTENT_LIMITED `1 << 19` (under 100 servers, the toggle on the Bot page).
- Developer Policy (support-dev.discord.com 8563934450327): do not use API data beyond the stated functionality, do not profile users, do not "mine or scrape any data", do not sell or commercialize API data, do not train models on message content without permission, respect users' ability to remove the app.
- Developer Terms (support-dev.discord.com 8562894815383) section 5: a privacy policy, delete API data when retaining it "is no longer necessary", when Discord or the user asks, or when the app stops; give users an easy way to ask for deletion; encryption at rest. No rule requires deletion when a server removes the app.
- Self-bots (support.discord.com 115002192352): "Automating normal user accounts (generally called "self-bots") outside of the OAuth2/bot API is forbidden".

Not found in what was read: whether `after=` returns the messages right after the id or the newest page (the adapter sorts by id and reads forward; the first live run must confirm); whether MESSAGE_UPDATE can be partial today (the adapter treats an update with no `edited_timestamp` and no `content` as an unfurl and drops it).

## Rights and scope (D-133, D-134)

- Bot only. The token is a bot token in `DISCORD_BOT_TOKEN`; `/users/@me` must say `bot: true` or the run stops (`not_a_bot`). Config keys such as `user_token` or `self_bot` are refused.
- Consent per server, recorded in the config: `consent.basis` `own_server` or `server_admin_installed_bot`, plus a reference. Without it no request is made. An invite link anywhere in the config is refused: an invite lets a person join, it gives no collection rights.
- Public only (D-009): the server must be `discoverable` or `open_invite` (attested in the config), and the channel must be visible to @everyone. A role-gated channel (holders-only and similar) is refused even when the bot can read it.
- No DMs: no DM endpoint is called, the gateway never asks for DIRECT_MESSAGES intents (the session refuses to be built with them), and a gateway message event without `guild_id` is dropped unread.
- Channel types: text (0) and announcement (5). Threads and forums are not read.

## Message content intent (D-135)

Before any channel read the adapter calls `GET /applications/@me`. With neither content flag set it stops with `message_content_intent_missing` and the exact fix (enable Message Content Intent on the Bot page, or get it approved above 100 servers). `discord-health` then reports `intent_missing`. With `require_message_content: false` the run continues with ids, times, authors and references only, and every channel that delivered items gets a DEGRADED unit saying so. On the gateway, close code 4014 is reported as `privileged_intent_missing`.

## Field mapping onto inbound/3 (D-136)

| Discord field | Stored as |
|---|---|
| `channel_id`, `id` | `provider_item_id` `<channel>_<message>`, item key `discord:<channel>_<message>` |
| guild, channel, message ids | URL `https://discord.com/channels/<guild>/<channel>/<message>` |
| `author.id`, `author.username` | account provider id and handle, profile `https://discord.com/users/<id>`; display name, avatar and roles never |
| `author.bot`, `webhook_id` | no author (bots, relays and webhooks never count as independent, D-042) |
| `timestamp`, `edited_timestamp` | publication time; `social_item_versions` ORIGINAL or EDIT at the edit time |
| `content` (or the forward snapshot's content) | `content_hash` only |
| type 19 / `message_reference` type 0 | REPLY with `replied_to` (author id from `referenced_message` when present) |
| `message_reference` type 1 + `message_snapshots` | REPOST with a forward row (origin channel and message ids) |
| content that is only a message link | REPOST with a `retweeted` reference |
| own words plus a message link | QUOTE with a `quoted` reference |
| `https://discord.com/channels/@me/...` | ignored (a DM link) |
| attachments, embeds, reactions | counts only (attachments and embeds only when content is available) |
| system message types (joins, pins, boosts) | dropped |
| MESSAGE_DELETE, MESSAGE_DELETE_BULK, recheck 404 code 10008 | DELETED sighting, then purged |

The event id is message plus version plus content hash plus reference ids. Reactions, embed unfurls and a referenced message that disappears do not make a new event; an edit does. The same message version read over REST and over the gateway is one observation.

## REST route (`discord-ingest`)

Per run: application flags, bot user, then per configured server `GET /guilds/{id}` and the bot's member roles, per channel `GET /channels/{id}`, a permission check, and `GET /channels/{id}/messages` with `after=<cursor>` (or one newest page on the first run, `backfill_max_pages` default 1). Then a recheck of stored messages from earlier runs (`max_items` default 25), only in channels that are readable right now. The cursor is the newest message id and moves only after ingest committed every unit.

Permission revocation: an overwrite that removes VIEW_CHANNEL or READ_MESSAGE_HISTORY, a 403 with 50001 or 50013, or 404 with 10003 or 10004 marks the channel BLOCKED (`access_denied`) with the reason; other channels go on. Absence is never read as deletion: a recheck that gets 403 stops that channel's recheck and marks nothing.

Rate limits: an exhausted bucket (`Remaining: 0`) waits `Reset-After` when it is at most `max_wait_seconds` (default 5); a 429 records `retry_after` on the channel and the next run does not call it before then; a global 429 stops the run; 5xx and network errors get 3 attempts; 401 stops the run; after `max_invalid_requests_per_run` (default 10) 401/403/429 responses the run stops, far below Discord's 10,000 per 10 minutes.

## Gateway route (`discord-gateway`)

`GatewaySession` is the protocol as a state machine: Hello leads to Identify (intents GUILDS, GUILD_MESSAGES and MESSAGE_CONTENT) or to Resume when a session exists; heartbeat requests are answered; Reconnect and Invalid Session end the connection (Invalid Session with `false` forgets the session); a dispatch whose (session, seq) was already seen is a duplicate and is dropped. Session id, resume URL and token stay in memory.

`DiscordGatewayAdapter` sorts dispatches by (connection, seq) and keeps per-server state from GUILD_CREATE (roles, the bot's roles, channel overwrites), CHANNEL_UPDATE and GUILD_ROLE_UPDATE. A permission change or a GUILD_DELETE without `unavailable` blocks the channel for the rest of the pass; GUILD_DELETE with `unavailable` is an outage and blocks nothing. Message events become items, deletes become DELETED sightings. A close code that forbids reconnecting ends the pass with its reason.

There is no live websocket transport in the repo: Python's standard library has none, and a gateway client is a long-running process. `discord-gateway` without `--fixture` exits 1 with `gateway_transport_not_shipped`. REST polling covers the same messages, edits (through recheck) and deletions (through recheck).

## Deletions and user requests (D-137)

Every `discord-ingest` and `discord-gateway` ends with `purge_deleted`: for each Discord item with a DELETED or NOT_FOUND sighting it clears content hashes, metrics and summaries on all observations, versions, claim spans and summaries, extraction outputs, private copies, and the link to the author. Ids and the gone sighting stay. A forward of a deleted message is its own message and keeps its hash. `discord-purge --user <id>` erases a user's account row, handle history and links everywhere (a user's deletion request, Developer Terms 5(b)). The purge code is shared with Reddit (`api_common.purge_gone_items`, `erase_accounts`).

## Proof

Fixtures (invented, generated once and committed): `tests/fixtures/social/discord_bot/` with the config, a first REST run, a second REST run, a gateway pass with two connections, and a 4014 close.

Tests: `tests/test_social_discord.py` (38). The prompt's list:

| Prompt item | Test |
|---|---|
| channel permission revocation | `test_permission_revoked_between_runs_blocks_the_channel_and_never_marks_deletion`, `test_403_missing_access_mid_run_blocks_that_channel_only`, `test_recheck_403_is_not_a_deletion`, `test_gateway_revocation_removal_and_role_gate` |
| intent missing | `test_intent_missing_blocks_with_a_clear_reason_and_reads_nothing`, `test_intent_missing_metadata_only_when_allowed`, `test_gateway_4014_reports_privileged_intent_missing_and_never_asks_for_dms` |
| duplicate gateway events | `test_gateway_duplicates_resume_out_of_order_and_delete_before_create`, `test_same_message_from_rest_and_gateway_is_one_observation`, `test_gateway_rerun_adds_nothing` |
| message edits | `test_main_fixture_ids_authors_replies_forwards_links_edits`, `test_second_run_cursor_recheck_edit_and_deletion_purge`, the gateway test |
| quote/link duplication | `test_forwards_and_link_only_shares_are_never_independent`, `test_main_fixture_...` (DM link ignored), the gateway test (unfurl update is not a version) |
| out-of-order events | the gateway test (edit before original: current version is the edit; delete before create: purged) |
| reset checkpoint | `test_reset_checkpoint_rereads_without_duplicates` |
| no available text | `test_attachment_only_message_has_no_text`, `test_intent_missing_metadata_only_when_allowed` |
| no-source day | `test_no_source_day_empty_pages_keep_the_cursor_and_the_brief_says_so`, `test_nothing_configured_is_not_run` |
| full fixture flow | `test_cli_fixture_flow_extract_narrative_brief_gateway_and_live_refusal` |

Also: consent, token and visibility gates with no request, config refusals (token, invite, self-bot keys, weak consent), user token refused, channel of another server, 429 with the next run waiting, global 429, bucket wait, invalid-request cap, 5xx retries, 401, secret redaction, health states with the network patched to fail, the example config off, and the permission algorithm.

Fixture flow (also release e2e stages 20): first REST run stores 9 messages in the open channel (one system message dropped), refuses the role-gated channel (`not_public`) and the channel without history permission; 8 texts extracted in memory, 6 token-reference claims for the LABDOG fixture contract; the narrative snapshot for 2026-10-10 has one cluster with 2 independent sources (the reply, the forward, the link share, the bot and the webhook add none); the brief lists it HIGH with id-only Discord links. Second run: 1 new message, recheck finds one deletion and one second edit, the purge clears the deleted message. Gateway pass: 5 items, 2 duplicates dropped, one resume, the DM and the holders-only message dropped, the unfurl update dropped, the channel blocked after CHANNEL_UPDATE removed the bot's view.

## Cost and health

| Connector | Cost | Health command | Status in this repo today |
|---|---|---|---|
| discord_bot | free; 50 requests per second per bot; estimated $0 per request (every request still writes a `social_api_spend` row) | `social discord-health` | `not_configured` (no private config); with the example config `consent_missing` |

Health states: `not_configured`, `consent_missing`, `credentials_missing`, `intent_missing` (after a run found no content flag), `ready`. It also shows `message_content_intent`, `gateway_last_status`, `blocked_channels`, cursors, `deletion_purge_pending_items` and `live_evidence` (only `mode='live'` rows count). No network call; exit 1 until `ready`.

## Setup (for Elving, when you decide to turn it on)

1. Decide which server. It has to be one you run, or one whose admin agrees in writing to a read-only research bot. Joining a server through its invite is not that agreement.
2. In the Discord Developer Portal create an application and a bot. On the Bot page turn on Message Content Intent (allowed without review below 100 servers). Leave Presence and Server Members off. Keep the token out of chat and out of the repo.
3. Invite the bot with only View Channels and Read Message History. The server admin does this step.
4. Copy `docs/social-intelligence/discord_bot.example.json` to `data/private/discord_bot.json`. Fill the server id, `server_visibility` (`discoverable` or `open_invite`), `consent.basis`, `consent.reference` (where the agreement is written down) and the channel ids (Developer Mode in Discord, right-click, Copy ID). Only channels everyone in the server can see will be read.
5. In the shell that runs memelab: `export DISCORD_BOT_TOKEN=...`.
6. `python -m memelab social discord-health` must say `ready`. Then one small run: `python -m memelab social discord-ingest --extract`, then `discord-health` again: `live_evidence` must show a successful request and `message_content_intent` must say `message_content_enabled`.
7. Discord's Developer Terms ask for a privacy policy and a way for users to ask for deletion. For a personal research bot that can be a short note in the server; `discord-purge --user <id>` carries out a request.

## First live run: what to confirm

- `after=` returns the messages right after the cursor (not the newest page); the fixtures assume it.
- `GET /guilds/{id}` includes `roles` and `owner_id` for a bot; the member call returns the bot's roles.
- The rate-limit headers and a 404 body with code 10008 for a deleted message.
- Record the result here and in SOURCE_COVERAGE.md.

## Not done, and why

- No live call: no bot, token or consenting server (D-140).
- No live gateway transport (D-139).
- Threads, forums and replies under threads are not read; older history beyond `backfill_max_pages` is not backfilled.
- When the bot is removed from a server, reads stop; stored data from that server is kept. Whether to purge it is Elving's call (D-137, PROPOSED part).
- No scheduled job runs this adapter (C-20).
