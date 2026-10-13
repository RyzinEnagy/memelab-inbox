# Phase 04: Telegram channel monitoring through the official Bot API

Source of truth: `memelab/social/telegram_bot.py` (adapter, webhook receiver, spool adapter, access check, health), `memelab/social/cli.py` (`social tg-health`, `social tg-ingest`, `social tg-webhook-ingest`), migration 4 in `memelab/social/schema.py`, inbound schema `/3` in `memelab/social/ingest.py`, `store.is_independent_original()` and `store.current_version()`. Tests: `tests/test_social_telegram.py` (41). Fixtures: `tests/fixtures/social/telegram_bot/`. Example config: [telegram_bot.example.json](telegram_bot.example.json).

Related: [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md), [DECISIONS.md](DECISIONS.md) (D-026 to D-029), [HANDOFF.md](HANDOFF.md).

## Status

Live Telegram ingest is UNAVAILABLE. No bot exists, no `TELEGRAM_BOT_TOKEN` is set, and no channel admin has added a bot. `python -m memelab social tg-health` reports `credentials_missing` and `live_evidence: none`; `social tg-ingest` (live) prints `NOT_RUN credentials_missing` and makes no network call. Once a token exists, a channel the bot cannot read reports `access_denied` (bot not an administrator, removed, chat not found) or `not_public` (no public username). Everything below is proved on recorded synthetic exchanges, labelled `fixture` in every table they touch.

## Which integration, and why

Three ways exist to read Telegram channels programmatically:

| Route | What it can read | Used here |
|---|---|---|
| Bot API (`api.telegram.org/bot<token>/...`) | posts in channels where the bot is a member, from the moment it was added | yes |
| MTProto client API with a user account (e.g. Telethon) | history of any public channel the account can open | no: needs an api_id/api_hash tied to Elving's phone number and automates a personal account; not approved |
| `t.me/s/<channel>` previews or Telegram Web in Chrome | what a browser shows | no: proposed Phase 07, now needs D-028 |

The Bot API is the only route that is both official and does not automate a personal account. Its cost is coverage: a bot sees only channels whose admins added it.

## What the official docs say (read 2026-10-11)

FACT, from core.telegram.org (Bot API changelog top entry: Bot API 10.3, August 24, 2026) and telegram.org/tos/bot-developers.

- Two mutually exclusive ways to receive updates: `getUpdates` or a webhook. `getUpdates` "will not work if an outgoing webhook is set up". ([Bot API, getting updates](https://core.telegram.org/bots/api#getting-updates))
- `getUpdates`: "An update is considered confirmed as soon as getUpdates is called with an offset higher than its update_id." Updates "will not be kept longer than 24 hours". `limit` 1 to 100; `timeout` 0 = short polling; `allowed_updates` keeps the previous setting when omitted. ([getUpdates](https://core.telegram.org/bots/api#getupdates))
- `setWebhook` `secret_token`: "A secret token to be sent in a header 'X-Telegram-Bot-Api-Secret-Token' in every webhook request, 1-256 characters", only `A-Z a-z 0-9 _ -`. Telegram retries a failed delivery "and give[s] up after a reasonable amount of attempts". Ports 443, 80, 88, 8443; a valid TLS certificate is needed. ([setWebhook](https://core.telegram.org/bots/api#setwebhook), [FAQ](https://core.telegram.org/bots/faq))
- Update fields used: `channel_post` ("New incoming channel post of any kind"), `edited_channel_post` ("New version of a channel post that is known to the bot and was edited"), `my_chat_member` ("The bot's chat member status was updated in a chat"). No Update field reports a deleted channel post; `deleted_business_messages` is for business accounts only. ([Update](https://core.telegram.org/bots/api#update))
- Message fields used: `message_id` ("Unique message identifier inside this chat"), `chat`, `sender_chat`, `date`, `edit_date`, `author_signature`, `forward_origin` (MessageOriginUser, MessageOriginHiddenUser, MessageOriginChat, MessageOriginChannel; the channel origin has `chat` and `message_id`), `is_automatic_forward`, `reply_to_message` (same chat), `external_reply` (may come from another chat), `text`, `caption`. `InaccessibleMessage` describes "a message that was deleted or is otherwise inaccessible to the bot" and has `date` always 0. ([Message](https://core.telegram.org/bots/api#message))
- Membership: bots receive "All messages from channels where they are a member" ([FAQ](https://core.telegram.org/bots/faq), [features](https://core.telegram.org/bots/features)). The pages read do not say how a bot becomes a channel member; in the Telegram apps a channel admin adds it as an administrator. The adapter treats `administrator` or `creator` as access and anything else as `access_denied`.
- Responses: `{"ok": true, "result": ...}`; on error `ok` false, `description`, an `error_code` whose "contents are subject to change", and optional `parameters`. ([making requests](https://core.telegram.org/bots/api#making-requests))
- Bot Platform Developer Terms 4.3: "You agree not to use your TPA to collect, store, aggregate or process data beyond what is essential for the operation of your services. Always prohibited uses include any form of data collection aimed at creating large datasets, machine learning models and AI products, such as scraping public group or channel contents." 4.2 requires deleting user data when it is no longer needed and on request. TPA means bots and Mini Apps. ([bot developer terms](https://telegram.org/tos/bot-developers)) See D-028.

UNKNOWN (not on the pages the fetch tool could read; the API page text was cut before these sections):

- The exact definitions of `ResponseParameters.retry_after`, `getChat`, `getChatMember` and the `ChatMember` status values. The adapter uses the commonly documented values (`retry_after` seconds; statuses creator, administrator, member, restricted, left, kicked) and treats any status other than administrator or creator as no access. Verify on the first live call.
- Whether a reply to a deleted message still carries `reply_to_message`. If it does not, the reply is stored as ORIGINAL.

## What a bot cannot see

- Arbitrary public channels. A newly created bot reads nothing until a channel admin adds it. There is no way around that through the Bot API, and the adapter never claims otherwise.
- History. No Bot API method returns earlier channel messages, and there is no fetch-by-id. Coverage starts when the bot was added and the first poll ran.
- Deletions. A deleted post is never reported; it just stops changing. Stored sightings of it stay as they were (no deletion status is invented).
- Anything older than 24 hours that was never confirmed. If polling stops for more than a day, posts in between can be lost; `tg-ingest` records a DEGRADED `gap` unit and `tg-health` sets `gap_risk`.
- Views and reactions. Channel posts delivered to bots carry no view counts; `metrics` stays empty.

## What the adapter does

Config: `data/private/telegram_bot.json` (gitignored; example [telegram_bot.example.json](telegram_bot.example.json)). Each channel needs `chat_id` (`-100...`), the public `username`, and `approval` = `own_channel` or `admin_invited_bot`, which becomes `rights_basis = telegram_bot_api_<approval>` on every live observation. Nothing is discovered automatically.

Per channel post it stores: item id `<chat_id>_<message_id>` (message ids are only unique inside a chat), channel id and username as the account, link `https://t.me/<username>/<message_id>`, send time (`date`, basis PROVIDER), fetch time, sha256 of the normalized text or caption, and inbound/3 extras:

- `version`: ORIGINAL at `date` or EDIT at `edit_date`, with the version's content hash and a sha256 of `author_signature` (the name is never stored). `social_item_versions` keeps every version; `store.current_version()` picks the highest provider time, so an edit that arrives before its original still wins.
- `forward`: origin type and, for channel or chat origins, the origin chat id, message id, origin item key and origin time. For user and hidden-user origins only the type is kept: no user id, no name.
- `context`: REPOST for a forward, REPLY with `replied_to` references for `reply_to_message` (same chat) and `external_reply` (other chat), else ORIGINAL.

Event ids are `bot.<chat>_<msg>.v<version time>.<hash of state>`, so a redelivered update (webhook retry, unconfirmed batch polled again, duplicate in one batch) adds nothing, and every edit is a new sighting.

Forwards are never independent originals: `store.is_independent_original()` returns False for any item with a forward record or a REPOST reference type. A forward and its original share a content hash, so later counting phases see one claim with two sightings.

Dropped without being written anywhere (counted in `dropped_updates`): updates from channels not in the config, any non-channel chat, update types other than the three requested (for example a DM to the bot), service messages (pins, title changes) and inaccessible messages. A configured channel without a public username is quarantined as NOT_PUBLIC (D-009 allows public content only).

Health per channel connector `telegram_bot:channel:<chat_id>` and for the bot connector `telegram_bot:<label>`: `my_chat_member` removal or demotion turns the channel BLOCKED with `access_denied`; re-adding as administrator turns it OK. `social tg-health --check-access` calls getMe, getChat and getChatMember (read-only, free) and records `OK`, `access_denied`, `not_public` or `not_a_channel` per channel.

## Safety rails

- Credentials only in the environment: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`. The config refuses credential-like keys.
- The token sits in the request URL path. The transport never lets an exception that could carry the URL escape; messages are rebuilt and scrubbed, and `ingest.redact()` now removes anything shaped like a bot token (`<digits>:<30+ characters>`, with or without the `bot` prefix). `test_token_never_leaks` injects the token into a transport error.
- Offset: `social_source_cursors(telegram_bot:<label>, updates).newest_id` advances only after `ingest()` committed every unit of the batch, and never moves backwards. A crash, a kill or a budget stop leaves the updates unconfirmed, Telegram sends them again, and event-id dedupe absorbs the repeats (tests prove the end state equals a clean run).
- Errors: 401 and 404 BLOCKED `credentials_rejected`; 403 and 400 "chat not found" BLOCKED `access_denied`; 409 BLOCKED `webhook_conflict`; 429 RATE_LIMITED, `retry_after` stored and the next run skips until then; 5xx and network errors three attempts with backoff, then DOWN; other 4xx DOWN.
- Request ledger: every call is a row in `social_api_spend` (cost 0, mode live or fixture). `tg-health` counts only live successful `getUpdates` rows as live evidence.
- Webhook route: `webhook_receive()` answers 503 without a configured secret, 401 on a missing or wrong `X-Telegram-Bot-Api-Secret-Token` (constant-time compare), 413 over 1 MB, 400 for malformed JSON or no `update_id`. A valid update is converted in memory and only the hashed record is written to `<private folder>/telegram_spool/<update_id>.json`; a redelivery of the same update id is a no-op. `social tg-webhook-ingest` ingests the spool and moves finished files to `done/`; `purge_spool()` deletes processed records after a retention period (terms 4.2). No HTTP server is shipped: the lab has no public HTTPS endpoint, so polling is the operational route.
- The Chrome/GitHub inbox bridge is not used: the Bot API is a direct HTTPS API that the cloud sandbox reaches (api.telegram.org answered on 2026-10-11), so routing it through a browser would add nothing.

## Commands

```
python -m memelab social tg-health [--config data/private/telegram_bot.json] [--check-access [--fixture <file>]]
python -m memelab social tg-ingest [--config <path>] [--fixture <file>] [--now <epoch>] [--max-items N]
python -m memelab social tg-webhook-ingest [--config <path>] [--spool <dir>]
python -m memelab social status --event telegram:bot.<chat>_<msg>.v<time>.<hash>
```

Fixture demo (no network, temp DB):

```
python -m memelab social tg-ingest --config tests/fixtures/social/telegram_bot/fx_tg_config.json \
  --fixture tests/fixtures/social/telegram_bot/fx_tg_main.json --db /tmp/tg.sqlite --now 1791561600
```

## How to authorize it (Elving's decision; nothing here has been done)

1. Decide D-028 first (Telegram's terms on data collection).
2. In Telegram, message @BotFather, `/newbot`, pick a name and a username. Keep the token secret; never paste it into a chat with Claude or a file in the repo.
3. For each channel: only channels Elving runs, or whose admins agree. A channel admin opens the channel, Administrators, Add Admin, picks the bot. The bot needs no posting rights. Note the channel's public username and numeric id (`-100...`).
4. Write `data/private/telegram_bot.json` from the example with `approval` set truthfully.
5. In the shell that runs memelab: `export TELEGRAM_BOT_TOKEN=...`, then `python -m memelab social tg-health --check-access`. Expect `ready`; any `access_denied` or `not_public` channel names the fix.
6. `python -m memelab social tg-ingest`, then `tg-health` should show `live_evidence: live authorized ingest proved`. Poll at least daily (24-hour retention).

## Known limits

- Coverage is limited to cooperating channels; most third-party call channels will not add a research bot. That makes this route useful for Elving's own channels and partner channels, not for broad monitoring.
- Edits are delivered only for posts "known to the bot", so edits of posts from before the bot joined are never seen. If an edit arrives without its original (original lost to the 24-hour window), it is stored as an EDIT version with no ORIGINAL.
- `author_signature` hashes let later phases count distinct signers without names; unsigned channels give NULL.
- Text-level evidence (exact wording) is not kept even in the private store; a later phase that needs it must ask under D-013 with a reason.

## Migration 4 (exact DDL in `memelab/social/schema.py`)

`social_item_forwards(item_key PK, origin_type CHECK channel|chat|user|hidden_user|unknown, origin_chat_id, origin_message_id, origin_item_key, origin_published_at, is_automatic_forward 0|1, recorded_at)` with index on `origin_item_key`.
`social_item_versions(item_key, provider_version_at, version_kind CHECK ORIGINAL|EDIT, content_hash, poster_hash, first_event_id, first_recorded_at, PK(item_key, provider_version_at))`.
Down script drops both. `rollback(target=3)` and re-`migrate()` are tested.
