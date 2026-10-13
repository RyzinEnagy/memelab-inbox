# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). This phase: [YOUTUBE_21.md](YOUTUBE_21.md). Previous phases: [DISCORD_20.md](DISCORD_20.md), [SOURCES_19.md](SOURCES_19.md). Release record: [RELEASE_18.md](RELEASE_18.md). Operator docs: [README.md](README.md), [OPERATIONS.md](OPERATIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md). Earlier phase notes are linked from ROADMAP.md.

## Position

- Current phase completed: 21 (optional Prompt 21: YouTube metadata and authorized transcript snippets), 2026-10-13. Prompt 21 took the Phase 21 slot; the old Phase 21 (supervised live run, docs check, rebase and merge) is carry-over C-21 and still depends on C-20 (D-141).
- Prompt 21 says stop after this phase. No further phase is started.
- Active branch: `feature/social-intelligence`. Start state matched the Phase 20 handoff: HEAD `2fc3266` (the pushed "record push in handoff" commit), `git status` clean.
- Baseline before any change: `python -m pytest tests -q --deselect tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` gave `727 passed, 1 deselected` (matches Phase 20's `1 failed, 727 passed`).
- No migration. Public schema stays at 12. No change under `inbox/`, `state/` or `data/`.
- Live status: not operational and no live call was made (D-148). No `YOUTUBE_API_KEY` or `YOUTUBE_OAUTH_TOKEN` in the session.

## What Phase 21 added

- `memelab/social/youtube_data.py`: config (channels by id or handle, configured videos, terms review gate, transcript routes `captions_api` for owned channels and `licensed` files with permission basis and reference; refuses credential keys, `tlang`, `timedtext`, downloaders and URLs as transcript files), REST and fixture transports (API key as `key=` on metadata reads, OAuth Bearer on caption calls only), Google error classification, `QuotaGuard` (units per call, per-run cap, Pacific Time daily cap from `social_api_spend`), `YouTubeDataAdapter` (channel resolution with duplicate detection, uploads playlist paging with a time cursor and page cap, `videos.list` batches, pending and listed videos, transcripts with timing, drift, delayed-archive and language rules, refresh of stored videos with NOT_FOUND for removed videos and their snippets), WebVTT and SRT parsing, snippet windows, `purge` (gone plus 30-day expiry), `health`.
- `memelab/social/api_common.py`: `clear_item_keys`, the erasure half of `purge_gone_items` (Reddit and Discord behaviour unchanged; their tests pass).
- `memelab/social/ingest.py`: `redact()` strips Google API keys (`AIza` + 35) and OAuth tokens (`ya29.`).
- `memelab/social/feed_core.py`: `safe_url` keeps `v=` and `&t=<n>s` on `www.youtube.com/watch` only.
- `memelab/social/sources_cli.py`: `social youtube-health`, `youtube-ingest`, `youtube-purge`; YouTube row in `social sources`. `memelab/social/cli.py` docstring.
- `tools/release_audit.py`: `google_api_key` and `google_oauth_token` shapes, `www.googleapis.com/youtube` in the credentialed-host list. `tools/release_e2e.py`: 7 stages (21), `YOUTUBE_API_KEY` and `YOUTUBE_OAUTH_TOKEN` in the removed credential list.
- Fixtures: `tests/fixtures/social/youtube_data/` (config, two runs, a quota failure, four transcript files; invented). Tests: `tests/test_social_youtube.py` (20), one test in `tests/test_release_tools.py`, the connector set in `tests/test_social_farcaster.py` now includes `youtube_data`.
- Docs: YOUTUBE_21.md (docs read with quotes, rights and scope, field mapping, time rules, language, quota, retention, proof table, cost and health, setup, first-live-run checks, gaps), `youtube_data.example.json` (off), DECISIONS D-141 to D-148, ROADMAP (21 DONE, C-21 added, C-8 no longer covers YouTube), SOURCE_COVERAGE (two rows), README, OPERATIONS, ARCHITECTURE.

## Gate, item by item (Prompt 21)

- Run after Phase 18: PASS (Phase 18 done, D-119; D-141).
- Official YouTube Data API, captions access, quota terms and retention rights verified: PASS (YOUTUBE_21.md "What was read": captions.download needs edit permission, OAuth for captions.list, quota costs and PT reset, 30-day storage, no downloading or scraping). Not read: the API Services ToS itself and the audit guide (listed for D-146).
- No prohibited downloads or fictional transcription access: PASS (no timedtext, downloader or `tlang` path in the code; config keys refused; `test_config_refuses_credentials_translation_downloaders_and_weak_permission`; captions only for owned channels or licensed files; 403 recorded as `UNAVAILABLE_NOT_PERMITTED`).
- Metadata ingestion and transcript snippets where allowed: PASS on fixtures (`test_run1_stores_ids_times_and_hashes_only_and_reads_a_duplicate_channel_once`, `test_transcript_statuses_missing_captions_and_unavailable_authorized_routes`).
- Video id, channel, published time, caption offsets, source link and timepoint, quotation context: PASS (snippet ids `<video>_t<start>_<end>`, URL `&t=180s`, cue windows within 15 s; brief prints the timepoint link).
- Publication time never taken as spoken time; no future livestream transcript before broadcast: PASS (`test_timestamp_drift_and_livestream_offsets`, `test_no_transcript_before_broadcast_and_delayed_archive`, `test_timing_never_places_an_unfinished_broadcast`; D-144).
- Token mentions, attribution and narrative relevance through the current pipeline: PASS (8 claims in run 1, two clusters, brief HIGH, ticker-only listed as unresolved; CLI test and e2e).
- Tests for multi-token mentions, missing captions, delayed livestream archiving, timestamp drift, channel and video dedupe, language and translation uncertainty, quota failure, unavailable authorized transcripts: PASS (proof table in YOUTUBE_21.md).
- Source-to-report fixture path: PASS (CLI test; e2e stages 21: 12 items, 8 claims, snapshot and brief, second run, quota stop exit 1, expiry purge, live refusal).
- Authenticated public-data smoke test: NOT RUN, BLOCKED (no key, no terms review; D-148). Not claimed.
- Costs and limitations documented: PASS (YOUTUBE_21.md "Cost and health", "Not done").

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change (on commit `7d166ab`): exit 1, `1 failed, 748 passed in 211.93s`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1).
- `python tools/release_e2e.py --out e2e.md` on `7d166ab`: exit 0, `Result: PASS. Stages with the expected exit code: 71 of 71. Network attempts: 0. Tracked files changed in the clone: 0. Tracked database byte-identical: yes.`
- `python tools/release_audit.py --history`: exit 0, `Needs action: no.`
- `python -m memelab social guard`: `violations: []` (395 files scanned).
- `python -m pyflakes` on `youtube_data.py`, `sources_cli.py`, `api_common.py`, `feed_core.py`, `tests/test_social_youtube.py`: no messages.
- The EVM test still writes `data/reports/<stamp>_BRETT_*.md`; deleted by hand after each run (C-1). `git status` clean before each commit.

## Things the next session should know

- D-146 is PROPOSED: aggregation across content owners, derived mention counts, and whether ids and times must be deleted after 30 days. Live reads are gated on `terms_review.accepted`.
- Transcripts of channels the lab does not own are not available by policy; the realistic route for an outside analyst is metadata only, or a transcript file with written permission.
- Whether `playlistItems.list` returns newest first is not documented; the first live run must confirm (YOUTUBE_21.md "First live run").
- A guest speaking on a channel is attributed to the channel.
- No scheduled job runs the Reddit, Farcaster, Discord or YouTube adapters (C-20).

## Helius key

Unchanged: never in the repo; read through `memelab/secrets.py` (`HELIUS_API_KEY`, else gitignored `data/config.json`); `python -m memelab.secrets status` prints set or missing only. It was pasted into a chat once; rotate it if that chat is shared.

## Blockers and open decisions

- YouTube live: Elving's terms review (D-146) and `YOUTUBE_API_KEY`; transcripts additionally an owner OAuth token or written permission.
- Discord live: a bot, a consenting server and Message Content Intent. Reddit live: Reddit's approval and credentials. Farcaster live: a node or a hosted hub.
- D-146, D-137 (server removal), D-128, D-025, D-028, D-023 and D-036 remain open.
- C-1 keeps the full suite from being fully green.
- Push: the session's own `git push` is refused by the git proxy; the working route is Elving's GitHub connection in Composio with the Git Data API (blobs, trees, commits, fast-forward of the feature branch ref, no force, D-001).

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q && python tools/release_e2e.py --out e2e.md
```

Expect `1 failed, 748 passed` and `Result: PASS` with 71 of 71 stages.

## Commit and push

Local commits on `feature/social-intelligence`: `7d166ab` (code, tests, fixtures, docs, tree `116f170`) and `d72b9e5` (handoff, tree `cdb6ceb`), on top of `2fc3266`.

Pushed 2026-10-13 through Composio and the GitHub Git Data API: a git bundle of the two commits was rebuilt in Composio's workbench and verified (sha256 equal to the local bundle, `git bundle verify`, same commit ids and trees); every blob sha came back equal to the local blob, and both trees came back equal to the local trees (`116f170`, `cdb6ceb`). Remote commits: `8f7609f9b205b7abf9bb15e6b0ebf196365efb6d` (code and docs) and `eda318cffd6976249bde4aaafe1fea700e337b63` (handoff), then this record on top. The remote ids differ from the local ones because the API re-serializes the commit header; the trees are identical. Branch ref fast-forwarded from `2fc3266` (no force, D-001). `main` untouched by this session (it is at `698f73b`, moved by the scheduled runs).

These commits are not in any open pull request. Opening one (feature into `main`) is Elving's call.

Phase 21 is complete. Stop here; no further phase is started.
