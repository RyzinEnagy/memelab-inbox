# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). This phase: [DISCORD_20.md](DISCORD_20.md). Previous phase: [SOURCES_19.md](SOURCES_19.md). Release record: [RELEASE_18.md](RELEASE_18.md). Operator docs: [README.md](README.md), [OPERATIONS.md](OPERATIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md). Earlier phase notes are linked from ROADMAP.md.

## Position

- Current phase completed: 20 (optional Prompt 20: Discord community monitoring), 2026-10-12. Prompt 20 took the Phase 20 slot; the old Phase 20 (scheduled-run integration and state export) is carry-over C-20 and Phase 21 now depends on it (D-132).
- Prompt 20 says stop after this phase. No further phase is started.
- Active branch: `feature/social-intelligence`. Start state matched the Phase 19 handoff: HEAD `f028ece`, `git status` clean.
- Baseline before any change: `python -m pytest tests -q --deselect tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` gave `688 passed, 1 deselected` (matches Phase 19's `1 failed, 688 passed`).
- No migration. Public schema stays at 12. No change under `inbox/`, `state/` or `data/`.
- Live status: not operational and no live call was made (D-140).

## What Phase 20 added

- `memelab/social/discord_bot.py`: config (servers with recorded consent and visibility, channels; refuses tokens, invites, user-token and self-bot keys), the documented permission computation and an @everyone visibility check, REST transport and fixture transport, message to inbound/3 mapping (ids, author id and username only, versions, reply, forward, message-link REPOST or QUOTE, counts, bots and webhooks without author, system messages dropped), `DiscordBotAdapter` (application flags for the message content intent, bot identity check, per-server and per-channel access, cursor reads with `after=`, recheck for edits and deletions, 429, global 429, bucket wait, invalid-request cap, 5xx retries), `GatewaySession` (identify, resume, heartbeat, reconnect, invalid session, close codes, sequence dedupe; DM intents refused), `DiscordGatewayAdapter` (permission state from GUILD_CREATE, CHANNEL_UPDATE, GUILD_ROLE_UPDATE, GUILD_DELETE; events sorted by connection and sequence), `purge_deleted` (with `users` for deletion requests), `reset_checkpoint`, `health`.
- `memelab/social/api_common.py`: `purge_gone_items` and `erase_accounts`, moved out of `reddit_api.purge_deleted` (Reddit behaviour unchanged; `items_purged` now counts only items where something was erased).
- `memelab/social/sources_cli.py`: `social discord-health`, `discord-ingest`, `discord-gateway` (fixture only), `discord-purge`, `discord-reset`; Discord added to `social sources`. `memelab/social/cli.py` docstring.
- `memelab/social/ingest.py`: `redact()` strips `Bot <token>` and the Discord token shape. `tools/release_audit.py`: `discord_bot_token` credential shape, `discord.com/api` in the credentialed-host list. `memelab/social/content_guard.py`: one ALLOW entry (the bot's own member entry in the gateway fixture, needed for its role ids).
- Fixtures: `tests/fixtures/social/discord_bot/` (config, two REST runs, a gateway pass, a 4014 close; invented). Tests: `tests/test_social_discord.py` (38), one test added to `tests/test_release_tools.py`, the connector set in `tests/test_social_farcaster.py` now includes `discord_bot`.
- `tools/release_e2e.py`: 9 stages (20) and `DISCORD_BOT_TOKEN` in the removed credential list.
- Docs: DISCORD_20.md (contract read, rights and scope, intent, field mapping, both routes, deletions, proof table, cost and health, setup, first-live-run checks, gaps), `discord_bot.example.json` (off), DECISIONS D-132 to D-140, ROADMAP (20 DONE, C-20 added, 21 depends on C-20), SOURCE_COVERAGE (two rows), README, OPERATIONS, ARCHITECTURE.

## Gate, item by item (Prompt 20)

- Official gateway/API docs and privileged message-content rules inspected: PASS (DISCORD_20.md "What was read", nine pages listed with what each says).
- Bot installation and permissions confirmed for selected servers and channels: PASS on fixtures (consent gate before any request; `/users/@me` must be a bot; per channel guild match, type, @everyone visibility, VIEW_CHANNEL and READ_MESSAGE_HISTORY by the documented algorithm; `test_role_gated_and_history_less_channels_are_not_read`, `test_permission_algorithm_matches_the_documented_order`).
- Never assume a public invite grants rights; no DMs; no self-bot: PASS (invite strings and self-bot keys refused, `test_config_refuses_tokens_invites_self_bots_and_weak_consent`, `test_user_token_is_refused_after_the_identity_check`; no DM endpoint; DM intents refused and DM events dropped, `test_gateway_4014_...`, gateway test `direct_message` drop).
- Observations with channel ids, message ids, author, reply thread, edits and deletions when observable, UTC publication and ingestion times, forwarding and link provenance, allowed retention: PASS (`test_main_fixture_ids_authors_replies_forwards_links_edits`, `test_text_embeds_names_and_topics_are_never_stored`, `test_second_run_cursor_recheck_edit_and_deletion_purge`).
- Rate-limit and permission-denied handling correct; missing privileged intent reported clearly: PASS (429, global 429, bucket wait, invalid cap, 5xx, 401, 403 tests; `test_intent_missing_blocks_with_a_clear_reason_and_reads_nothing`, `test_intent_missing_metadata_only_when_allowed`, 4014 test; health `intent_missing`).
- Integrated into the existing normalized ingestion, token resolver, claim extraction and narrative feed, no second social schema: PASS (inbound/3 through `ingest()`, `extract_after_ingest`, narrative snapshot and brief in `test_cli_fixture_flow_extract_narrative_brief_gateway_and_live_refusal`; no migration).
- Tests for permission revocation, intent missing, duplicate gateway events, message edits, quote/link duplication, out-of-order events, reset checkpoint, no available text, no-source day: PASS (mapping table in DISCORD_20.md "Proof").
- Full fixture flow: PASS (CLI test and e2e stages 20: 9 messages stored, 8 texts extracted in memory, 6 claims, one cluster with 2 independent sources, brief HIGH; second run with recheck, edit and purge; gateway pass).
- Live demonstration only with an authorized guild and configured bot: NOT RUN, BLOCKED (no bot, token or consenting server; D-140). Not claimed.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change (on commit `82e37e2`): exit 1, `1 failed, 727 passed in 133.51s`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1).
- `python tools/release_e2e.py --out e2e.md` on `82e37e2`: exit 0, `Result: PASS. Stages with the expected exit code: 64 of 64. Network attempts: 0. Tracked files changed in the clone: 0. Tracked database byte-identical: yes.`
- `python tools/release_audit.py --history`: exit 0, `Needs action: no.`
- `python -m memelab social guard`: exit 0, `violations: []`.
- `python -m pyflakes` on `discord_bot.py`, `sources_cli.py`, `api_common.py`, `reddit_api.py`, `tests/test_social_discord.py`: no messages.
- The EVM test still writes `data/reports/<stamp>_BRETT_*.md`; deleted by hand after each run (C-1). One such file was caught in the first local commit and removed by amending that local, unpushed commit before anything else was built on it. `git status` clean before each commit.

## Things the next session should know

- Whether `after=` returns the messages right after the cursor is not stated in the docs read; the first live run must confirm (DISCORD_20.md "First live run").
- D-137 is partly PROPOSED: when the bot is removed from a server, stored data from that server is kept. Elving decides.
- D-134 defines a public Discord channel as an open server plus @everyone visibility; Elving can tighten it.
- No live gateway transport (D-139). `discord-gateway` runs on recorded frames only.
- No scheduled job runs the Reddit, Farcaster or Discord adapters (C-20).

## Helius key

Unchanged: never in the repo; read through `memelab/secrets.py` (`HELIUS_API_KEY`, else gitignored `data/config.json`); `python -m memelab.secrets status` prints set or missing only. It was pasted into a chat once; rotate it if that chat is shared.

## Blockers and open decisions

- Discord live: a bot application with Message Content Intent on, `DISCORD_BOT_TOKEN`, and a server whose admin installs the bot and agrees in writing (Elving's).
- Reddit live: Reddit's written approval and app credentials. Farcaster live: a node or a hosted hub with a cost decision.
- D-137 (server removal), D-128 (derived rows of deleted Reddit posts), D-025, D-028, D-023 and D-036 remain open.
- C-1 keeps the full suite from being fully green.
- Push: the session's own `git push` is refused by the git proxy; the working route is Elving's GitHub connection in Composio with the Git Data API (blobs, trees, commits, fast-forward of the feature branch ref, no force, D-001).

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q && python tools/release_e2e.py --out e2e.md
```

Expect `1 failed, 727 passed` and `Result: PASS` with 64 of 64 stages.

## Commit and push

Local commits on `feature/social-intelligence`: `82e37e2` (code, tests, fixtures, docs) and the handoff commit on top of it, both on `f028ece`. Push status is recorded in the commit that follows this file, or in the chat if the push could not be made.

Phase 20 is complete. Stop here; no further phase is started.
