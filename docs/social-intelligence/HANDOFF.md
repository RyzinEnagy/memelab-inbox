# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 04 (Prompt 04: Telegram public-channel monitoring through the official Bot API), 2026-10-11. Prompt 04 took the Phase 04 slot; the old proposed Phase 04 (manual capture) is now carry-over C-4 (D-026).
- Live Telegram ingest: UNAVAILABLE (D-027). No bot, `TELEGRAM_BOT_TOKEN` or cooperating channel exists; no live Telegram call has been made. `social tg-health` reports `credentials_missing`, `live_evidence: none`.
- Live X ingest: still UNAVAILABLE (D-023).
- Next phase: 05 (source registry) as proposed in ROADMAP.md, unless Elving supplies Prompt 05.
- Active branch: `feature/social-intelligence`.
- Phase 04 started from `054fb8a` ("Update HANDOFF.md"). Drift since the Phase 03 handoff: `e739182` and `0672cb3` (a root-level HANDOFF.md added then deleted) and `054fb8a` (HANDOFF correction), all by Elving through the GitHub UI, docs only. Tree clean; baseline `python -m pytest tests -q` gave `1 failed, 142 passed`, as recorded.
- Phase 04 commit: `b147108` "social-intel phase 04: Telegram channel monitoring through the official Bot API" (local). This HANDOFF is the next commit on top of it. Not pushed: the session cannot push to this repo (same blocker as Phases 00 to 03); the changed files go to Elving for upload.

## What Phase 04 added

- `memelab/social/telegram_bot.py`: config loader (`memelab.telegram_bot.config/1`, refuses credentials, needs `approval` per channel), `UrllibTransport` (only network code; token in the URL path, never in an error), `FixtureTransport` (`memelab.telegram_bot.fixture/1`), `classify_error()`, `message_item()` and `normalize_update()` (text, caption, signature and forward sender name hashed or dropped), `TelegramBotAdapter` (getUpdates polling, offset cursor, gap warning, 429 window), `webhook_receive()` (secret header, size, JSON checks; hashed spool), `WebhookSpoolAdapter`, `purge_spool()`, `check_access()` (getMe, getChat, getChatMember), `health()`.
- `memelab/social/ingest.py`: inbound schema `memelab.social.inbound/3` (item `forward`, `version`), `_validate_forward`, `_validate_version`, `_persist_forward`, version rows; `redact()` strips Telegram bot tokens.
- `memelab/social/schema.py`: migration 4 (`social_item_forwards`, `social_item_versions`), added to `SOCIAL_TABLES`.
- `memelab/social/store.py`: `is_independent_original()` (False for forwards and reposts, D-029), `current_version()`.
- `memelab/social/cli.py`: `social tg-health [--check-access [--fixture]]`, `social tg-ingest [--fixture]`, `social tg-webhook-ingest`. Default config `data/private/telegram_bot.json` (gitignored).
- Tests: `tests/test_social_telegram.py` (41). Fixtures: `tests/fixtures/social/telegram_bot/fx_tg_main.json`, `fx_tg_second.json`, `fx_tg_access.json`, `fx_tg_config.json` (invented channels, ids and sentences).
- Docs: `TELEGRAM_04.md` (integration choice, verified contract with quotes and sources, what a bot cannot see, safety rails, setup steps), `SOURCE_COVERAGE.md` (new source-coverage table), `telegram_bot.example.json`, DECISIONS D-026 to D-029, ROADMAP (row 04 DONE, 05 NEXT, 07 flagged, C-4 added).

## Gate, item by item

- Official integration verified: Bot API pages read 2026-10-11 (Bot API 10.3): getUpdates, setWebhook secret_token, Update, Message, MessageOrigin, InaccessibleMessage, FAQ and features pages, Bot Platform Developer Terms 4.2 and 4.3. Quotes and links in TELEGRAM_04.md. UNKNOWN items listed there (ResponseParameters, getChatMember status list: the fetch tool could not read that part of the page).
- Membership and limits explained: TELEGRAM_04.md "What a bot cannot see" (admin-added channels only, no history, no deletions, 24-hour retention, no views). No code path claims an arbitrary public channel can be read.
- Adapter operational under documented permissions, or truthfully blocked: truthfully blocked (`credentials_missing`), all fixture paths work. `test_cli_fixture_demo_and_no_false_live_claim` proves live `tg-ingest` exits 1 with `NOT_RUN credentials_missing` and makes no network call (`urlopen` patched to fail), and fixture rows are not live evidence.
- Fields: channel id, message id, poster (signature hash), sent and edited time, forward origin, text hash (no text: the repo's public database rule, D-013, D-016), link, reply-to: `test_main_fixture_channel_posts_into_observations`, `test_provenance_of_one_event`, `test_text_signature_and_forward_sender_never_stored`, `test_reply_context_same_chat_and_external`.
- Prompt test list:
  - message edits: `test_edit_is_a_new_version_and_sighting`
  - duplicate updates: `test_duplicate_updates_and_redelivery_add_nothing`, `test_redelivery_with_a_new_fetch_time_is_deduped_by_event_id`, main test (1 duplicate in the batch), webhook redelivery in `test_webhook_secret_validation_and_spool_without_text`
  - forwards, not counted as independent originals: `test_forwards_keep_origin_and_are_not_independent_originals`
  - deleted or inaccessible: `test_inaccessible_message_dropped`, service pin with an inaccessible message in the main fixture, membership removal (`test_webhook_membership_removal_blocks_channel`, main test BLOCKED). Deletions themselves are not observable through the Bot API; documented.
  - authorization denial: `test_access_check_reports_denied_and_not_public`, `test_access_check_chat_not_found_and_bad_token`, `test_http_errors_map_to_status_and_hold_cursor` (401, 404, 403, 409, 400)
  - out-of-order updates: `test_out_of_order_edit_before_original_and_readded_bot`, `test_out_of_order_update_ids_never_move_the_cursor_back`, `test_webhook_spool_ingest_out_of_order_and_idempotent`
  - restart and resume: `test_crash_between_batches_holds_offset_then_resumes`, `test_process_killed_mid_ingest_resumes_without_duplicates`, `test_item_budget_stop_holds_offset`
  - also: `test_429_retry_after_stops_and_skips_until_reset`, `test_5xx_bounded_retries_then_down`, `test_5xx_then_success`, `test_paging_until_short_batch_and_poll_cap`, `test_gap_warning_after_24_hours`, `test_token_never_leaks`, `test_config_refuses_credentials_and_bad_channels`, `test_health_states_without_network`, `test_private_channel_quarantined_unapproved_and_dm_dropped`, `test_migration_4_rolls_back_cleanly`, `test_inbound_v2_ignores_forward_and_version_keys`
- CLI fixture demo (temp DB and private folder, no token in the environment):
  - `social tg-health --config tests/fixtures/social/telegram_bot/fx_tg_config.json` exit 1: `credentials_missing`, network_calls_made 0, `none: no live Telegram Bot API read has been made`
  - `social tg-ingest --config <same>` (live) exit 1: `{"network_calls_made": 0, "reason": "credentials_missing", "status": "NOT_RUN", ...}`
  - `social tg-ingest --config <same> --fixture .../fx_tg_main.json --now 1791561600` exit 0: `PARTIAL fixture`, 1 request, 8 created, 1 duplicate, 1 quarantined; dropped service_message 1, unapproved_channel 1, update_type_not_used 1; alpha OK, beta BLOCKED (bot removed), private channel DEGRADED
  - same with `fx_tg_second.json --now 1791568800` exit 0: `OK`, 1 request, 2 created
  - `social status --event telegram:bot.-1001000000001_11.v1791554600.9cf3a3b17e6a`: inbound/3, rights_basis synthetic_fixture, connector `telegram_bot:channel:-1001000000001`, fetched 1791558000, provider 1791554600, FRESH, access_mode fixture, URL `https://t.me/example_alpha_calls/11`, handle `example_alpha_calls`; its forward row: origin channel, origin item `telegram:-1001000000002_5`
  - `social tg-health --check-access --fixture .../fx_tg_access.json` exit 1: still `credentials_missing` (no token), channels alpha OK, beta access_denied, private not_public, live requests 0
- Migration on a copy of the tracked DB: `schema.migrate()` on a copy of `data/memelab.sqlite` applied `[1, 2, 3, 4]` (the tracked DB has no social tables yet); `content_guard.check_sqlite` on the copy: no violations. The tracked file is unchanged.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`; node optional).
- Outcome after the last code change: exit 1, `1 failed, 183 passed in 9.65s`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched).
- `python -m pytest tests/test_social_telegram.py -q` -> `41 passed`.
- `python -m memelab social guard` exit 0 (233 files, 66 JSON, 0 violations, with the Phase 04 files staged).
- Side effect still present: the EVM test writes `data/reports/<stamp>_BRETT_0x532f.md`; deleted by hand after each run (C-1). `git status` clean after that.

## Things the next phase should know

- Telegram goes live only after Elving's steps in TELEGRAM_04.md ("How to authorize it"), and D-028 should be decided first. Realistic coverage is his own channels and channels whose admins agree.
- Later counting phases must call `store.is_independent_original()` (D-029); a forward shares its original's content hash.
- `social_api_spend` is now also the free request ledger for Telegram (cost 0); queries on X spend filter by `connector LIKE 'x_api:%'`, Telegram by `'telegram_bot:%'`.
- Event ids now come in three shapes: `x:api.<id>.<h>`, `telegram:bot.<chat>_<msg>.v<time>.<h>`, and the bridge's own or derived ids.
- Social tables are still not in the `state.py` export (scheduled-run phase).

## Blockers and open decisions

- Push: the session cannot push to `memelab-inbox`; each phase ends with a manual upload unless the repo is added to the session's sources.
- D-028 (Telegram bot developer terms vs channel data collection, and Phase 07) is Elving's decision. D-025 (X browser automation) and the X budget (D-023) are still open.
- Phase prompts 05 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 183 passed` and `python -m memelab social guard` exit 0. Then start the next phase.
