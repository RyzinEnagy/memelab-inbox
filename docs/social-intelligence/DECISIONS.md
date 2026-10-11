# Social & Trader Intelligence: decisions

Durable choices and their reasons. Add new entries at the bottom; do not edit an old entry, supersede it with a new one.

Related: [EXECUTION.md](EXECUTION.md), [ROADMAP.md](ROADMAP.md), [HANDOFF.md](HANDOFF.md), [AUDIT_00.md](AUDIT_00.md).

Status values: ADOPTED (in force), PROPOSED (needs Elving's approval before any phase relies on it), SUPERSEDED.

## D-001 Branch strategy (ADOPTED, Phase 00, 2026-10-10)

Work happens on `feature/social-intelligence`, created from `main` at `48fe2900fa2e8643e592365a558fa0d469551e41`. The working tree was clean, so no uncommitted work needed preserving.

Reason: `main` receives scheduled-run commits several times a day (inbox/ and state/ data). Keeping all feature work on one branch means those runs are never disturbed. The feature branch never edits inbox/, state/ or data/ so merges from `main` stay conflict-free. No force-push, no history rewrite.

## D-002 One phase per session (ADOPTED, Phase 00)

Each session implements one phase, tests it, proves it, commits, rewrites HANDOFF.md and stops.

Reason: the work spans many sessions with no shared memory. A fixed contract and a written handoff are the only reliable continuity.

## D-003 Evidence discipline carries over (ADOPTED, Phase 00)

Social and trader outputs use the existing FACT / INFERENCE / HEURISTIC / UNKNOWN buckets (docs/ARCHITECTURE.md). UNKNOWN earns zero and is not redistributed. Identity is by mint or contract, never ticker. Paid placement is never counted as organic attention. Trader handles are research sources, not certified profitable traders.

Reason: these rules already govern every module in the code (m19, catalyst/attention.py, launch/social.py) and the reports depend on them.

## D-004 No raw third-party social content in the public repo (SUPERSEDED by D-010)

Proposal: the public repo may hold derived, non-expressive data only: account handle, public profile URL, timestamps, numeric counts, contract addresses found, evidence status, a hash of the source text. Raw post text, bios, images, member lists and anything behind a login stay in a private, gitignored local store, or are not stored at all.

Reason: `RyzinEnagy/memelab-inbox` is public. Republishing third-party posts in bulk raises copyright and platform-terms problems (X and Telegram terms restrict redistribution of content collected outside their APIs) and privacy problems for individual accounts. The repo already republishes news RSS titles and descriptions in `inbox/cat01_*.json`; that is a smaller version of the same risk and is noted in AUDIT_00.md. This is not legal advice; Elving decides.

Needs: Elving's approval before Phase 02.

## D-005 Collection route (ADOPTED, Phase 00)

API pulls through `python -m memelab fetch` (Node runner `memelab/bridge/run_plan.js`) are the first route; the Claude in Chrome bridge is the fallback. If both fail, the gap is recorded and the run continues. If Chrome or GitHub sign-in is needed and unavailable, the session stops and reports.

Reason: this is Elving's stated rule and what SKILL.md and the code implement. On 2026-10-10 the cloud sandbox reached Jupiter, GeckoTerminal, DEX Screener and RugCheck directly (HTTP 200), which contradicts the older README and docs/SOURCES.md text saying the sandbox cannot reach crypto APIs.

## D-006 No logged-in social scraping (SUPERSEDED by D-009)

Proposal: social collectors read only what is public without signing in (X profile pages, `t.me/s/` previews, RSS). No reading of X timelines through a signed-in browser profile, no automation of a personal account.

Reason: signed-in scraping ties the lab to Elving's personal accounts, risks account suspension and goes beyond the public-data scope of the repo. docs/SOURCES.md and `memelab/catalyst/sources.py` mention signing into X in the bridge Chrome profile as a way to close the gap; this proposal says not to, unless Elving chooses otherwise.

Needs: Elving's decision before Phase 06.

## D-007 Phase 00 left committed locally, not pushed (SUPERSEDED by D-008)

The Phase 00 commit exists on the local feature branch only and was delivered to Elving as a patch.

Reason: the standing approval on record covers public market data in `inbox/` and `state/` only, and the cloud session had no valid GitHub credentials (GH_TOKEN invalid, api.github.com answered 403 through the proxy).

## D-008 Branch pushed through the GitHub web UI (ADOPTED, Phase 00, 2026-10-10)

Elving approved pushing `feature/social-intelligence`. The branch was created from `main` at `48fe290` on github.com and the five Phase 00 docs were added through the web editor in his signed-in Chrome, one commit per file. No personal access token was created.

Reason: the cloud session has no working GitHub credential, and minting a token would put a live secret in the chat and session logs. The local commit `d72e550` has the same content but a different hash; the remote branch is the record.

## D-009 Social reading through Elving's signed-in Chrome (ADOPTED, 2026-10-10)

Decided by Elving. Social collectors may read X, Telegram and other platforms through Claude in Chrome while his accounts are signed in. This is the preferred route for social data because paid social APIs cost money. D-005 still applies to market data (direct API pulls first); for social data the order is reversed: signed-in Chrome first, paid APIs only if Elving approves the cost.

Rules that come with it:
- Read only. Never post, reply, like, repost, follow, join, DM, vote or change any account setting.
- Public content only: what any signed-in user can see. No DMs, closed or private groups, protected accounts or paid-subscriber content.
- Human pace: paced page reads, no bulk scrolling loops, stop on any rate-limit, captcha or login challenge and report it (CAPTCHAs are never solved by the agent).
- If Chrome or the sign-in is unavailable, stop and report (same as D-005).

Known risk, accepted by Elving: platform terms (X in particular) restrict automated collection even when signed in, so the account could be rate-limited or suspended.

## D-010 Summaries of public social content may be stored (ADOPTED, 2026-10-10)

Decided by Elving. The repo may store short, general summaries of publicly posted social content, written in the system's own words, alongside the derived fields from D-004 (handle, public URL, timestamps, numeric counts, contract addresses found, evidence status, hash of the source text).

Not stored in the repo: verbatim post text in bulk, images or video, DMs, content from private or closed spaces, and personal details about private individuals beyond their public handle. Short quotes are kept out of tracked files; if a phase needs exact wording for evidence, it stays in the gitignored private store.

Summaries are INFERENCE-level descriptions of what was posted, not FACT about the token, and never count as attention on their own.

## D-011 Prompt 01 replaces the proposed Phase 01 (ADOPTED, Phase 01, 2026-10-10)

Elving supplied Prompt 01 ("Implement durable schemas, evidence provenance, and migration safety"). It replaces the proposed Phase 01 (baseline hygiene) and absorbs the proposed Phase 03 (social schema and migrations), which is now SUPERSEDED. The hygiene work (clock-dependent catalyst test, stray BRETT report from the EVM test) is kept as carry-over item C-1 in ROADMAP.md and was not done in Phase 01, so the known failure stays isolated rather than fixed.

## D-012 Social tables live in the main lab database, under a migration ledger (ADOPTED, Phase 01)

New tables use the `social_` prefix in `data/memelab.sqlite`, defined in `memelab/social/schema.py` and applied by `db.init_db()` after the existing schemas. No parallel data store. Unlike the earlier modules (bare `CREATE TABLE IF NOT EXISTS` plus column guards), social tables are versioned: `social_schema_migrations` records each version with a checksum, each version applies in one transaction, and each has a down script. Existing narratives (`narratives`, chains schema) and the source registry (`catalyst_sources`) are reused through soft links; `social_snapshots` is unchanged.

Reason: the prompt asks for schema versions and a rollback plan, and the repo convention gives neither. Keeping one database keeps `state.py`, tests and scheduled runs working as they are. No foreign key points at a legacy table, so applying or rolling back the social schema cannot touch legacy rows (proved in tests on a copy of the tracked DB).

## D-013 The public database never holds source text; exact wording goes to a gitignored private store (ADOPTED, Phase 01)

`data/memelab.sqlite` is tracked in git (force-added despite `*.sqlite*` in .gitignore), so anything in it is public. The store hashes source text and keeps only the hash, numeric metrics and own-words summaries (max 400 characters, refused if they repeat 8+ consecutive source words). Exact wording, when a caller gives a reason, goes to `data/private/social_private.sqlite` (gitignored, `MEMELAB_PRIVATE_DB` override) with a 30-day default retention and `purge_expired()`. This implements D-010 at the storage layer; the repo-wide leak guard is still Phase 02.

## D-014 References are checked in code because foreign keys are off (ADOPTED, Phase 01)

`db.connect()` does not enable `PRAGMA foreign_keys`, so FK clauses in every schema, old and new, are declarative only. Phase 01 does not change that repo-wide (it could break existing writers that rely on it being off). The social store checks the references that matter in code: analysis version registered, wallet-attribution subject exists, addresses valid for the chain.

## D-015 Prompt 02 replaces the proposed Phase 02 (ADOPTED, Phase 02, 2026-10-10)

Elving supplied Prompt 02 ("Build one operational ingestion contract and the existing browser bridge adapter"). It replaces the proposed Phase 02 (content policy and public/private storage split). The storage-side policy is already in code from Phase 01 (D-013) and the inbound side is now enforced by the ingester (D-016); the repo-wide guard that scans tracked files for raw post text was not built and is kept as carry-over C-2. Prompt 02 also delivers the observation contract of proposed Phase 04; what is left of Phase 04 is the manual-capture path onto the same schema.

## D-016 The public inbox carries hashes and own-words summaries, never post text (ADOPTED, Phase 02)

Inbox files are committed to the public hand-off repo before the cloud side sees them, so the storage guard of D-013 comes too late for them. Inbound schema `memelab.social.inbound/1` therefore has no text field: the browser computes `content_hash` (`__SOC.hash`, same normalization as `store.text_hash`), and the ingester quarantines any item carrying text, bios, media, DMs, member lists, quotes, transcripts or a visibility other than PUBLIC. Errors and logs name fields, never values.

## D-017 Ingestion state is versioned with the social schema (ADOPTED, Phase 02)

Migration 2 adds `social_ingest_runs`, `social_ingest_checkpoints`, `social_ingest_quarantine` and `social_observation_provenance`. Dedupe is two-layered: a unit checkpoint (connector, source_ref, sha of the unit) skips a file already processed, and the event id (collector id or derived hash) is the primary key of provenance, so a renamed or re-shipped file adds nothing. Items commit in batches with the checkpoint's next index in the same transaction. Quarantined payloads go to `<private folder>/quarantine/` (gitignored), never to the public database.

## D-018 Connector health is per connector per run (ADOPTED, Phase 02)

Each connector gets one `social_connector_health` row per run, worst status wins (OK < DEGRADED < RATE_LIMITED < LOGIN_REQUIRED/CAPTCHA/BLOCKED < DOWN). A down connector, unreadable file or unexpected error in one unit is recorded and the run continues. A run is PARTIAL when anything was degraded or down and FAILED only when no unit was usable; the CLI exits 0 for OK and PARTIAL and 1 for FAILED, so one bad connector does not fail a scheduled run.

## D-019 Stale sightings are stored and flagged, not dropped (ADOPTED, Phase 02)

A `fetched_at` older than the stale threshold (default 12 hours, `--max-age-hours`) is still a true historical sighting, so it is stored with `freshness='STALE'`, its connector is DEGRADED for that run and coverage is PARTIAL with the age. Timestamps in the future (beyond 5 minutes of clock skew), naive timestamps and provider times after the fetch time are invalid and quarantined.

## D-020 Repo-wide content guard (ADOPTED, carry-over C-2, 2026-10-10)

Built at Elving's request after Phase 02. `memelab/social/content_guard.py` (CLI `python -m memelab social guard`, test `tests/test_content_guard.py::test_tracked_repo_is_clean`) scans every tracked file and fails on: private, wallet or quarantine files being tracked; a SQLite file other than `data/memelab.sqlite`; blocked content classes or non-public items inside `soc:*` inbox units; social-only keys (`bio`, `full_text`, `members` ...) anywhere in tracked JSON; content columns in social tables, a `private_content` table, over-long summaries, prose in `social_snapshots.text_value` or copied profile text in `catalyst_sources.identity_notes` in the tracked database. It reports location and rule, never the value. Generic keys (`text`, `title`, `description`, `quote`) are not flagged outside social units because in this repo they hold lab alerts, news headlines, issuer metadata or a pool's quote token. Invented fixture content is allowed only by exact location, each entry with a reason.

Known conflict: the existing catalyst trader check (`catalyst plan --verify-traders`) ships an X profile `bio` into the inbox (`x_profile` projection in `memelab/bridge/catalyst.js`) and copies title and bio into `catalyst_sources.identity_notes`. Neither is in any tracked file today (feature branch and `origin/main` at `6b0a054` both scan clean), but the next run that uses it would fail the guard. Changing that projection is left for Elving to decide.

## D-021 The catalyst trader check no longer collects X profile bios (ADOPTED, 2026-10-10)

Decided by Elving, resolving the conflict noted in D-020. The `x_profile` projection (`bridge/catalyst.js` and `memelab/bridge/catalyst.js`) returns only the page title and whether the profile exists. `catalyst._verify_trader` marks the source VERIFIED when the title names the handle and appends a fixed note ("profile page found, title names the handle") once, with no copied text; a bio in an older result file is ignored. Test: `tests/test_catalyst_xprofile.py`. The change reaches the scheduled runs only when this branch is merged into `main`, because the browser loads `bridge/catalyst.js` from `main`.
