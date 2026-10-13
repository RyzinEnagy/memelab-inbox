# Phase 21 (optional Prompt 21): YouTube metadata and authorized transcript snippets

Adapter: `memelab/social/youtube_data.py`. Commands: `social youtube-health`, `social youtube-ingest`, `social youtube-purge` (in `memelab/social/sources_cli.py`). Tests: `tests/test_social_youtube.py`. Fixtures: `tests/fixtures/social/youtube_data/` (invented). Decisions: D-141 to D-148. Example config: [youtube_data.example.json](youtube_data.example.json).

Status: built and proved on fixtures. Live is BLOCKED: no API key, and the terms review (D-146) is Elving's. No live call was made.

Purpose: periodic contextual intelligence from long-form analyst content (what a channel said about which contract, and when that became public). Not real-time launch detection: YouTube metadata arrives in batches, quota is daily, and transcripts of livestreams arrive after the broadcast.

## When this phase runs

Prompt 21 says to run it after Phase 18 unless a verified high-value analyst relies on long-form content. Phase 18 is done (D-119, PR #1 merged), so the condition held. It takes the Phase 21 slot the same way Prompts 19 and 20 took theirs (D-141).

## What was read (2026-10-13)

Official pages on developers.google.com, read through the session's fetch tool:

- `youtube/v3/docs/captions/download`: OAuth scope `youtube.force-ssl` or `youtubepartner`; "This method requires the user to have permission to edit the video"; 200 units; `tfmt` (sbv, scc, srt, ttml, vtt); `tlang` is "machine translation, such as Google Translate"; 403 forbidden, 404 captionNotFound.
- `youtube/v3/docs/captions/list`: OAuth required (same scopes); 50 units; `videoId`, `part`; 403 forbidden, 404 captionNotFound and videoNotFound.
- `youtube/v3/docs/captions` (resource): `language` (BCP-47), `trackKind` ASR, forced, standard; `audioTrackType`; `isDraft`; `isAutoSynced`; `status` serving, syncing, failed.
- `youtube/v3/docs/videos` (resource): `snippet.publishedAt` ("might be different than the time that the video was uploaded"), `liveBroadcastContent` live, none, upcoming, `defaultAudioLanguage`, `contentDetails.duration` (ISO 8601) and `caption`, `liveStreamingDetails.actualStartTime` ("unavailable until the broadcast begins") and `actualEndTime` ("unavailable until the broadcast is over"), `status.privacyStatus`; statistics exist but are not requested.
- `youtube/v3/docs/channels` and `channels/list`: `forHandle`, `id` (comma list), `maxResults` 0 to 50, 1 unit; `contentDetails.relatedPlaylists.uploads` is "the ID of the playlist that contains the channel's uploaded videos".
- `youtube/v3/docs/playlistItems` and `playlistItems/list`: `contentDetails.videoId`, `videoPublishedAt`; `maxResults` 0 to 50, default 5; 1 unit; the page states no ordering of results.
- `youtube/v3/determine_quota_cost` and `getting-started`: 10,000 units a day for all endpoints except `search.list` and `videos.insert` (100 calls a day each); "Daily quotas reset at midnight Pacific Time (PT)"; "All API requests, including invalid requests, incur at least a one-point quota cost"; unauthorized list requests return public data.
- `youtube/v3/docs/errors`: 403 quotaExceeded, 403 forbidden, 404 channelNotFound, playlistNotFound, videoNotFound, 403 playlistItemsNotAccessible.
- `youtube/terms/developer-policies`: III.E.4 (non-authorized data stored at most 30 calendar days, then refreshed or deleted; statistics not stored beyond 30 days); III.E.1 (no downloading, caching or storing audiovisual content without YouTube's written approval); III.E.6 (no scraped data); III.E.4.h (no new or derived metrics from API data); III.E.2 (no aggregation across content owners); III.D.2 and III.E.4.g (deletion within 7 days of a user's request or revocation).

Not read in this phase: the YouTube API Services Terms of Service itself and the "Quota and Compliance Audits" guide. They belong in Elving's review (D-146).

## Rights and scope (D-142)

- Metadata of public videos through the Data API with an API key. Channels and videos named in the private config only. No `search.list`.
- Transcripts only on an authorized route, both off by default:
  - `captions_api`: `captions.list` and `captions.download` with an OAuth token in `YOUTUBE_OAUTH_TOKEN`, only for channels listed as owned/editable. A 403 marks the video `UNAVAILABLE_NOT_PERMITTED` and is not retried.
  - `licensed_file`: a WebVTT or SRT file the operator supplies, with `permission.basis` (`own_channel` or `creator_written_permission`) and a reference. Paths only; a URL is refused (nothing is downloaded).
- Never: `tlang` (machine translation), the timedtext endpoint, downloaders, scraping the watch page or player. The config refuses keys named `tlang`, `translate`, `timedtext`, `yt_dlp`, `downloader` and any credential key.
- So for an analyst the lab does not own and has no written permission from, the honest status is metadata only, transcript `UNAVAILABLE_NO_AUTHORIZED_ROUTE`.

## Field mapping onto inbound/3 (D-143)

Video item: provider id = video id; URL `https://www.youtube.com/watch?v=<id>`; account = channel id (provider user id), the channel's handle (`customUrl`, stored without `@`), profile URL by channel id; `published_at` = `snippet.publishedAt` (PROVIDER); content hash = hash of title + description (words in memory only); reference type ORIGINAL, conversation id = video id. No metrics, no summary, no titles, no thumbnails.

Transcript snippet item: provider id `<video>_t<start ms>_<end ms>`; URL with the timepoint `&t=<seconds>s`; the cue that names a token candidate (address, address-bearing link or cashtag, `identity.extract_mentions`) plus up to `context_cues` cues on each side, each within 15 s of its neighbour (quotation context); windows that share a cue are merged; content hash of the snippet words; same account and conversation id as the video. Cues with no candidate are never kept. The observation's `terms_note` records the route, track language and kind, audio language, the language check and how the time was set.

Narratives: snippets and their video share one source (the channel), so a video that names a contract in its description and again in its transcript is one independent source, not two (D-042 unchanged).

Feed: `feed_core.safe_url` keeps exactly `v=<11 chars>` and `&t=<n>s` on `www.youtube.com/watch` and drops every other query, so briefs link to the moment in the video.

## Time (D-144)

`published_at` on a snippet is when the words became public, never a guess of when they were spoken:

| Video | Snippet `published_at` | Basis |
|---|---|---|
| uploaded or premiered | the video's `publishedAt` (the words may have been recorded earlier; the time they were spoken is unknown) | PROVIDER |
| archived livestream (`actualEndTime` present) | `actualStartTime` + cue start offset, clamped to `actualEndTime` and to the fetch time | PARSED_RELATIVE |
| upcoming or live | no transcript (`PENDING_BROADCAST`), even if a licensed file exists | n/a |

PARSED_RELATIVE makes downstream engines conservative: narratives use the collection time as the event time (D-044), chronology gives it a wide interval (D-081), and the replay clock uses first observation (D-113). So a livestream transcript can never be placed before its broadcast, and a prediction is never evaluated against words that were not public yet.

Drift: a cue that starts after the media length (duration, or end minus start for a livestream) plus `drift_tolerance_seconds` (30) is dropped and counted (`timestamp_drift`, DEGRADED unit).

Delayed archive: an archived livestream whose captions are not ready (`contentDetails.caption` false, or no serving track) is `PENDING_ARCHIVE`; later runs re-read it through `videos.list` (1 unit per 50) until captions appear or `pending_max_days` (7) after the broadcast ended, then `UNAVAILABLE_NO_CAPTIONS`.

## Language (D-142)

Track language is compared with the video's `defaultAudioLanguage` (primary subtag): MATCH, MISMATCH or UNVERIFIED (audio language not stated). A MISMATCH track is a translation of what was said and is not used unless `allow_language_mismatch` is true (`UNAVAILABLE_LANGUAGE_MISMATCH`, DEGRADED unit `language_uncertain`). Among owner tracks the order is MATCH, then UNVERIFIED, then standard before ASR. An ASR track is noted in `terms_note` ("words, tickers and addresses may be misheard"): a misheard address does not resolve and stays unresolved; a ticker alone never resolves (D-031).

## Quota (D-147)

Units per call: channels, playlistItems, videos 1; captions.list 50; captions.download 200. `quota.max_units_per_run` (200 by default) and `quota.daily_units` (10,000, the default allocation, capped there) are checked before every call; the daily count is the sum of `quota_units` in `social_api_spend` rows of the same mode since midnight Pacific Time (DST handled: 23 and 25 hour days tested). 403 `quotaExceeded` stops the whole run and stores the next Pacific midnight in `social_source_cursors` (`youtube_data:quota`); runs before then make no call. 429 or `rateLimitExceeded` stops the run; 5xx is retried three times; `keyInvalid` and 401 stop the run as `credentials_rejected`; `accessNotConfigured` as `api_not_enabled`.

A daily run over 20 channels with one new upload each costs about 20 (channels) + 20 (playlists) + 1 (videos) + 1 (refresh) = 42 units. An owner caption costs 250.

## Retention and deletion (D-145)

- Refresh: each run re-reads stored videos last seen OK more than `refresh_after_days` (7, capped at 29) ago, 50 per `videos.list` call. A refresh is a new dated sighting (`.rYYYYMMDD` in the event id), so the 30-day clock restarts. A video that is missing from the response (deleted, private) or no longer public becomes NOT_FOUND, and so does every stored snippet of it.
- Purge after every ingest (`youtube_data.purge`, also `social youtube-purge`): items with a NOT_FOUND or DELETED sighting lose their derived data through the shared `purge_gone_items`; videos not seen OK within `retention_days` (30, capped there), and their snippets, lose it through `clear_item_keys` (new in `api_common`, the erasure half of `purge_gone_items`, behaviour unchanged). Erased: content hashes, claim spans and summaries, extraction outputs, private copies, the author link. Kept: ids, times and the gone sighting. Whether those must go too is part of D-146.

## Proof

| Prompt asks for | Where |
|---|---|
| Authorized channel and video metadata ingestion | `test_run1_stores_ids_times_and_hashes_only_and_reads_a_duplicate_channel_once` (12 items, ids, handles, no metrics, no text) |
| Transcript snippets only where allowed | `test_transcript_statuses_missing_captions_and_unavailable_authorized_routes`, `test_config_refuses_credentials_translation_downloaders_and_weak_permission` |
| Video id, channel, published time, offsets, link with timepoint, quotation context | run 1 test (snippet URL `&t=180s`), `test_caption_parsing_ids_and_durations` (windows, id round trip) |
| Publication time is not a spoken time; no transcript before broadcast | `test_timestamp_drift_and_livestream_offsets` (VOD snippet = publishedAt), `test_no_transcript_before_broadcast_and_delayed_archive`, `test_timing_never_places_an_unfinished_broadcast` |
| Token mentions, attribution and narrative relevance through the pipeline | `test_multi_token_snippet_ticker_only_and_description_mentions`, `test_cli_fixture_flow_extract_narrative_brief_purge_and_live_refusal` |
| Multi-token mentions | two contracts in one snippet, two claims (multi-token test) |
| Missing captions | video 05 `PENDING_ARCHIVE`, video 09 no route (statuses test) |
| Delayed livestream archiving | video 03 and 05 across two runs (delayed archive test) |
| Timestamp drift | cue past the end dropped and counted (drift test) |
| Channel and video dedupe | duplicate handle entry read once (run 1 test); `test_rerun_dedupes_videos_snippets_and_transcript_work` |
| Language and translation uncertainty | `test_language_mismatch_is_refused_and_asr_is_noted` |
| Quota failure | `test_quota_exceeded_stops_the_run_until_midnight_pacific`, `test_quota_caps_per_run_and_daily`, `test_pacific_quota_day_handles_daylight_saving` |
| Unavailable authorized transcripts | video 08 captions.list 403, video 09 no route (statuses test) |
| Retention and deletion | `test_refresh_purges_removed_video_and_its_snippets_and_restarts_the_clock`, `test_thirty_day_expiry_clears_derived_data_of_unrefreshed_videos` |
| Secrets | `test_secrets_never_reach_logs_errors_or_repr`; `redact()` strips Google API keys and `ya29.` tokens; release audit shapes `google_api_key`, `google_oauth_token` |
| Source-to-report fixture path | CLI test and release e2e stages 21 (ingest with extraction, snapshot, brief HIGH with timepoint links, second run, quota stop, expiry purge, live refusal) |
| Authenticated public-data smoke test | NOT RUN: no API key and no terms review (D-148) |

## Cost and health

No money: the Data API is free. The limit is quota (10,000 units a day by default; more needs Google's quota extension form, which can involve a compliance audit). `social youtube-health` makes no network call and reports status (`not_configured`, `terms_review_missing`, `credentials_missing`, `quota_exhausted`, `ready`), units used today (Pacific), the quota reset time, channel cursors, transcript statuses, connector health, live evidence (only `mode='live'` rows count) and how many stored videos are past retention.

## Setup (for Elving, when you decide to turn it on)

1. Read the YouTube API Services Terms of Service and the Developer Policies sections listed above, and decide D-146 (aggregation across channels, what the 30-day rule requires the lab to delete).
2. In a Google Cloud project, enable YouTube Data API v3 and create an API key restricted to that API. Export it as `YOUTUBE_API_KEY` in the shell that runs memelab. Never put it in a file in the repo.
3. Copy `youtube_data.example.json` to `data/private/youtube_data.json`, add channels (`{"id": "UC..."}` or `{"handle": "@name"}`) and set `terms_review.accepted` true with a reference to where your review is written down.
4. Optional, transcripts: for a channel you own, get an OAuth token with the `youtube.force-ssl` scope, export `YOUTUBE_OAUTH_TOKEN`, list the channel under `transcripts.captions_api.owned_channels` and set `enabled` true. For another creator, only with written permission: save their transcript file under `data/private/` and add a `licensed` entry with the permission reference.
5. `python -m memelab social youtube-health` should say `ready`. Then one small live run: one channel, `max_pages_per_channel` 1, `python -m memelab social youtube-ingest --extract`.

## First live run: what to confirm

- `playlistItems.list` on an uploads playlist returns newest first (the docs state no order; the adapter does not depend on it but the page cap does).
- `snippet.customUrl` is the `@handle` form.
- An API key read of a members-only or age-restricted video: what comes back.
- An archived livestream: how long until `contentDetails.caption` turns true.
- The units in `social_api_spend` match the Cloud console quota page for the day.

## Not done, and why

- No live call and no smoke test: no API key, no terms review (D-148).
- No transcript of channels the lab does not own: not permitted by the API (edit permission required) and downloading is prohibited (D-142).
- No statistics (views, likes, comments): not needed, and the policies limit storing them and forbid deriving metrics from them.
- No comments, no search, no RSS route (C-8 keeps token-listed links only).
- Speaker attribution inside a video (guests): the channel is the account; a guest's words are attributed to the channel that published them.
- Whether ids and times must also be deleted after 30 days: open in D-146; the code erases derived data only.
