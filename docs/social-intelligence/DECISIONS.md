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

## D-022 Prompt 03 is the X API phase (ADOPTED, Phase 03, 2026-10-10)

Elving supplied Prompt 03 ("X/Twitter monitoring as a real, permitted source"). The Phase 03 slot in ROADMAP.md was SUPERSEDED (D-011), so Prompt 03 takes it over as a new phase: an adapter on the official X API v2. Proposed Phase 06 (X through signed-in Chrome, D-009) is unchanged and still PLANNED; the two routes feed the same ingester.

## D-023 Live X ingest is marked UNAVAILABLE; fixtures carry the proof (ADOPTED, Phase 03)

There is no X developer app, Bearer token or budget consent, so no live call was made and none is claimed. The adapter, the request/response contract (from docs.x.com, read 2026-10-10), the billing guard and the health command are real; the proof runs on recorded synthetic HTTP exchanges in `tests/fixtures/social/x_api/`. Fixture rows are labelled `access_mode='fixture'`, `rights_basis='synthetic_fixture'` and spend `mode='fixture'`, and `social x-health` counts only `mode='live'` rows as live evidence.

The billing guard is off by default (`allow_billable` false, caps 0). A request is made only when its worst-case cost fits both the per-run and per-month caps. Enabling it is Elving's cost decision (D-009: paid APIs only with his approval). X integration is not commercially impractical at the lab's scale (roughly $30 to $180 a month for 20 followed accounts, see X_API_03.md), so no source-alternative decision is recorded.

## D-024 Inbound schema /2 and migration 3 (ADOPTED, Phase 03)

`memelab.social.inbound/2` adds an optional per-item `context` (reference type, conversation id, reply-to user id, edit history ids, referenced post ids with original author ids; ids and enums only). `/1` is unchanged and still what the browser bridge ships. Migration 3 adds `social_item_context`, `social_item_refs`, `social_source_cursors`, `social_api_spend` and `social_api_billed_resources`. The X adapter stores ids, hashes, counts and context, never post text (D-013, D-016), although X's own terms would allow storing API content: the database is public.

`ingest.redact()` now strips `Bearer <token>` before the generic `key: value` rule, so "Authorization: Bearer <t>" loses the token (it kept it before).

## D-025 X's Developer Guidelines prohibit browser automation (PROPOSED, needs Elving, Phase 03)

While verifying the API terms, the official Developer Guidelines (docs.x.com/developer-guidelines, read 2026-10-10) say: "Non-API automation (scraping, browser automation) results in permanent suspension." D-009 already accepted the risk that X restricts automated collection; this is the current, explicit wording, and it names the exact route D-009 prefers. Nothing in Phase 03 changes D-009. Elving should reconfirm D-009 for X specifically (keep Chrome reads for X, pay for the API for X, or drop X) before proposed Phase 06 is built. Telegram and other platforms are not affected by this entry.

## D-026 Prompt 04 is the Telegram Bot API phase (ADOPTED, Phase 04, 2026-10-11)

Elving supplied Prompt 04 ("Telegram public-channel monitoring"). It takes the Phase 04 slot. The proposed Phase 04 (manual capture onto the inbound schema) moves to carry-over C-4, unscheduled. Proposed Phase 07 (Telegram through `t.me/s/` or Telegram Web in Chrome) stays PLANNED and now also waits on D-028. Both Telegram routes feed the same ingester.

## D-027 Telegram live ingest is UNAVAILABLE; the bot reads only channels whose admins added it (ADOPTED, Phase 04)

No bot, token or cooperating channel exists, so no live call was made and none is claimed. `social tg-health` reports `credentials_missing`; live `tg-ingest` exits 1 with `NOT_RUN credentials_missing` before any network call. Proof runs on recorded synthetic exchanges in `tests/fixtures/social/telegram_bot/`, labelled `access_mode='fixture'`, `rights_basis='synthetic_fixture'`, ledger `mode='fixture'`.

Scope rules in code: only channels listed in `data/private/telegram_bot.json` with a public username and an `approval` basis (`own_channel` or `admin_invited_bot`) are converted; every other update is dropped in memory. Text, captions, author signatures and forward sender names are hashed or dropped, never stored; a forward from a user keeps only the origin type (no user id). The Bot API was chosen over an MTProto user client because the latter automates Elving's personal account. Polling is the operational route; the webhook receiver and spool exist but no HTTP server is shipped (no public HTTPS endpoint).

Schema: inbound `memelab.social.inbound/3` = `/2` plus optional item `forward` and `version`; `/1` and `/2` are unchanged and ignore those keys. Migration 4 adds `social_item_forwards` and `social_item_versions`. `ingest.redact()` now strips Telegram bot tokens.

## D-028 Telegram's bot developer terms restrict channel data collection (PROPOSED, needs Elving, Phase 04)

The Bot Platform Developer Terms (telegram.org/tos/bot-developers, read 2026-10-11), section 4.3: bots may not "collect, store, aggregate or process data beyond what is essential for the operation of your services", and "Always prohibited uses include any form of data collection aimed at creating large datasets, machine learning models and AI products, such as scraping public group or channel contents." Section 4.2 requires deleting user data once it is no longer needed.

What the code already does about it: reads only listed, admin-approved channels; keeps ids, times and hashes; no text; spool retention purge. Whether a research lab that scores memecoin attention from channel posts is "essential for the operation" of the bot, or "data collection aimed at creating large datasets", is a judgment for Elving (this is not legal advice). The same clause names "scraping public group or channel contents", which is what proposed Phase 07 would do through a browser; the developer terms bind bots and Mini Apps, and whether Telegram's general terms of service restrict automated browser reads was not checked. Elving should decide: (a) use the bot only for channels he runs or has written consent from, (b) also go ahead with Phase 07, or (c) drop Telegram collection.

## D-029 Forwards and reposts are never independent originals (ADOPTED, Phase 04)

A forwarded Telegram post is stored as its own item with `reference_type='REPOST'` and a `social_item_forwards` row pointing at the origin. `store.is_independent_original()` returns False for any item with a forward row or a REPOST reference type (X reposts included). Replies and quotes stay independent because they are the poster's own words. Later counting phases (10, 11, 15) must call it, so one claim forwarded to ten channels counts once with ten sightings.

## D-030 Prompt 05 is the token identity phase (ADOPTED, Phase 05, 2026-10-12)

Elving supplied Prompt 05 ("Resolve exact token identity and snapshot market conditions"). It takes the Phase 05 slot. The proposed Phase 05 (source registry) moves to carry-over C-5, unscheduled; phases 06, 07, 08 and 13 now depend on C-5 instead. Phase 05 also delivers the token side of proposed Phase 09. No live provider call was made; every proof runs on synthetic bodies in `tests/fixtures/social/resolve/`.

## D-031 Four resolution outcomes; a ticker alone never resolves (ADOPTED, Phase 05)

Each reference in a post gets `resolved`, `ambiguous`, `unresolved` or `conflicted` (lower-case, as the prompt names them), with every candidate and its evidence stored (`social_token_resolutions`, `social_token_candidates`). A ticker resolves only when a contract in the same post resolves to a token whose providers report that ticker, or when it names a registry asset (wrapped native or stablecoin) on a chain the caller states. One search hit is still `ambiguous`. A contract that copies another token's symbol resolves to itself and is flagged. A ticker that disagrees with the posted contract makes both `conflicted`. Typos are never corrected; near matches are listed. A migration keeps the old contract as the identity and lists the successor. Reason: the prompt's gate ("no silent symbol-only matches") and D-003 (identity by contract, never ticker).

## D-032 Supported chains for identity: Solana, Ethereum, Base, BNB Chain (ADOPTED, Phase 05)

These four have provider coverage in the existing code (DEX Screener, GeckoTerminal, Jupiter for Solana, GoPlus for EVM, Jupiter or KyberSwap quotes). Other registry chains and chains the registry does not know are stored as `support='unsupported'` candidates and never resolve. Adding a chain later means adding it to `identity.SUPPORTED` once its sources are confirmed.

## D-033 Market facts are per provider, versioned, and split by time meaning (ADOPTED, Phase 05)

`social_market_facts` keeps one row per provider value with unit, quote currency, supply basis for valuation fields, collector key, source URL, as_of, as_of_kind, fetched_at and a validity window, versioned per series with `supersedes_fact_id`. Providers that disagree are never merged. The price at posting time comes only from a GeckoTerminal candle that contains the publication time, or from an observation fetched within 120 seconds of it; otherwise it is NULL with `NO_HISTORY`, and the current price stays an observed-at-fetch fact with its lag. Reported liquidity and executable sell proceeds are separate facts. The validity windows and the supply-basis reading of provider fields are lab conventions, not checked against provider documentation in this phase.

## D-034 Market context reuses the bundle builders, not analyze_token (ADOPTED, Phase 05)

`market_context` calls `normalize.build_bundle` and `chains/evm.build_bundle` and stores its facts in new `social_` tables. It does not call `pipeline.analyze_token`, which writes reports, theses and the legacy `tokens` table, whose primary key is the mint alone (one EVM address on two chains would collide there). The catalyst matcher (`catalyst/match.py`), which picks the most liquid Solana token for a term, is unchanged; social code uses the new resolver.

## D-035 Prompt 06 is the claim extraction phase (ADOPTED, Phase 06, 2026-10-12)

Elving supplied Prompt 06 ("Evidence-grounded structured claim extraction"). It takes the Phase 06 slot. The proposed Phase 06 (X reads through signed-in Chrome) moves to carry-over C-6, unscheduled, and still needs D-025. Phases 07, 08, 09 and 13 that depended on the old 06 now depend on C-6 or C-5 as noted in ROADMAP.md. Phase 06 also delivers the claim side of proposed Phase 15 (call capture) except the collector wiring. No live model call was made (D-036).

## D-036 No model is configured; model status is reported, never assumed (ADOPTED, Phase 06)

The repo had no LLM configuration. Phase 06 adds one in a gitignored file (`data/private/llm.json`, example in `docs/social-intelligence/llm.example.json`) with the key read only from `ANTHROPIC_API_KEY`; a config holding a key is refused. `social llm-health` reports `model_not_configured`, `credentials_missing`, `billing_not_consented`, `configured_unverified` or `live_ok` (only after a live 200 in `social_api_spend`). With no usable provider the model part of every extraction is stored as `analysis_unavailable` with the reason, and no category, stance or opinion is guessed. All model proofs use an offline mock provider (`mode='fixture'`) or a fake HTTP transport. Turning a live model on is Elving's cost decision (same rule as D-009 and D-023): model id, prices and caps must be set and `allow_billable` true.

## D-037 Deterministic extraction is limited to token references (ADOPTED, Phase 06)

Without a model the lab extracts only what text matching can prove: each address, address-bearing link and cashtag, anchored by character offset and resolved through Phase 05. It is stored as a `token_reference` claim, evidence FACT (the post contains it), verification `present_in_text`. Keyword rules for bullish, risk or wallet claims were not built, because they would be the false classification the prompt rules out.

## D-038 Evidence is stored as offsets and hashes; quotes and raw model replies stay private (ADOPTED, Phase 06)

The model must quote the post for every claim; the validator finds each quote in the normalized text (the text the content hash is computed on) and stores only `char_start`, `char_end` and the span's sha256 in `social_claim_spans`. Quotes are never stored in the public database (content guard rule added for `social_claim_extractions.output_json`). The raw model reply can quote the post, so it goes to the private store (`private_model_responses`, 30-day retention), where it doubles as the replay cache. Summaries from the model are kept only if they pass `store.check_summary` (own words, D-010).

## D-039 Model output is schema-validated and grounded; the lab's rules override the model (ADOPTED, Phase 06)

Model output must match `memelab.social.claims.model/1` exactly. A field outside the schema drops that claim; a top-level field outside it, or non-JSON after one retry, rejects the whole reply (`invalid_model_output`). Quotes not in the text, unknown mention ids and contracts the post does not contain are removed. Provider ids decide attribution (repost, forward, quote) over the model's reading. Wallet statements stay text claims (no `social_wallet_attributions` row). Contradictions, sarcasm, unanchored conditions, unresolved tokens and injection-like text raise uncertainty. All rules are listed in CLAIMS_06.md. Reason: the gate asks for validated output and the lab's evidence rules (D-003) cannot depend on a model following instructions.

## D-040 Extraction versions, cache and replay (ADOPTED, Phase 06)

`PROMPT_VERSION` (what the model is asked) and `EXTRACTOR_VERSION` (validation and post-processing) are separate. One extraction row per observation x provider x model x prompt version x extractor version; repeats add nothing. The cache key is text hash + provenance context + provider + model + prompt version + output schema + mention identities, so the same text seen twice is analysed once. An extractor change replays from the private raw reply with no call; a prompt change makes a new call. A successful new extraction sets `superseded_by` on the older ones; nothing is deleted. The `social_claims.claim_type` projection (CALL/LONG for bullish and so on) is coarse; the classification lives in `social_claim_attributes`.

## D-041 Prompt 07 is the narrative phase (ADOPTED, Phase 07, 2026-10-12)

Elving supplied Prompt 07 ("Narrative clustering, originators, amplifiers and independent corroboration"). It takes the Phase 07 slot. The proposed Phase 07 (Telegram public channels through Chrome, needs D-028) moves to carry-over C-7, unscheduled. Phase 07 is built on Phase 06 claims, Phase 05 identity and the Phase 03 and 04 provider references. No live data and no live model call; every proof runs on invented fixtures (`tests/fixtures/social/narratives/`, builders in `tests/test_social_narratives.py`).

## D-042 Independence is counted per dependency group, from observed origins only (ADOPTED, Phase 07)

Items that reach one original through reposts, forwards, quotes or replies, or that share a content hash, form one dependency group with one origin. `independent_source_count` is the number of distinct sources among observed independent origins, so 100 reposts or 6 commenters under one post are one source. Reposts, forwards and quotes that repeat a claim are AMPLIFIER; replies, own-words quotes and identical copies are DEPENDENT; neither adds independence. A bot, an aggregator or an unknown author is never counted as independent. Accounts the lab linked to one trader count as one source. An unobserved original is counted separately as `unobserved_origin_count` and never as an independent source; with no observed independent origin the cluster is `insufficient_coverage`. A reply to an observed item that makes no claim about the token is its own origin. This is stricter than `store.is_independent_original()` (D-029), which decides attention counting and stays unchanged; corroboration needs the stricter test because an own-words reply still depends on the post it answers.

## D-043 Clustering is deterministic; no semantic clustering in Phase 07 (ADOPTED, Phase 07)

Clusters are keyed by resolved `(chain, contract)` or by a structured tag from the closed list. Tickers and names never key a cluster. Vector or LLM clustering was not built: no model is configured (D-036), there is no labelled fixture set to evaluate it against, and an unevaluated semantic cluster would be a fabricated topic. The snapshot records `semantic_clustering: not_enabled`. A later semantic step must run first on fixtures with a stored evaluation, fall back to the deterministic keys when the model or the embedding is unavailable, and label its clusters as semantic.

## D-044 Snapshots are immutable and replayable (ADOPTED, Phase 07)

A run is keyed by engine version, window, knowledge cutoff, zone, parameters and a hash of the input rows. The cutoff is `min(window_end, clock)`, so replaying a past window reproduces it and new information makes a new run. Windows are calendar days in an IANA zone with times stored as UTC epoch seconds, half open, 23 or 25 hours on clock-change days; naive datetimes are refused. Event time is provider publication time when known, else collector time, else unknown. Changes compare a run with the latest earlier run that has the same parameters and zone. Narrative tables are `social_narrative_*` (migration 7); the legacy `narratives` table and `social_claims.narrative_id` are not written.

## D-045 Insufficient coverage and confidence caps (ADOPTED, Phase 07)

`insufficient_coverage` is emitted when volume or independence cannot be estimated: no coverage record for a contributing platform (switchable with `require_coverage`), only GAP, BLOCKED or SKIPPED coverage, most items without a usable time, or no independent origin. Counts stay as lower bounds; independent count is NULL; confidence is UNKNOWN. Partial coverage, an unobserved original, an inaccessible source, a coordination hypothesis or disagreement cap confidence at MODERATE; nothing observed in 48 hours caps it at LOW. HIGH needs 5 independent sources. Deleted or not-found items stay as origins (they were observed) but do not vote on stance. These thresholds are heuristics, not calibrated.

## D-046 Coordination is a hypothesis, never ownership (ADOPTED, Phase 07)

Many sources repeating one original within a short time (default 10 sources in 900 s) and byte-identical text from several sources (default 3, when no repost or forward explains the copying) raise `burst_amplification` and `identical_text_multi_source`. Both carry evidence HEURISTIC and `proven: false`. They lower confidence; they do not merge or discard sources, because reposts and copies are already collapsed into their group. No account is called a bot or an owner on this basis.


## D-047 Prompt 08 is the registry phase (ADOPTED, Phase 08, 2026-10-12)

Elving supplied Prompt 08 ("Source and trader registry"). It takes the Phase 08 slot. The proposed Phase 08 (YouTube RSS and token-listed links collector) moves to carry-over C-8, unscheduled. C-5 (source registry) is met by the registry for trader and list sources; access-mode metadata for collectors stays in the Phase 02 to 04 configs. No live list was supplied, so everything is proved on invented, labelled fixtures.

## D-048 Five entity kinds plus link types, no merging (ADOPTED, Phase 08)

Accounts, wallets, source organizations, social networks and leaderboard candidates are entities. Relations (self-disclosed wallet, third-party label, on-chain proof, dispute, same operator, operated by organization, network membership, listed by, observed as) are links with basis, window, evidence reference and review state. Entities are never merged; a person's cluster is the set joined by reviewed SAME_OPERATOR links.

## D-049 Names are not identity evidence (ADOPTED, Phase 08)

A link with a name-based basis is refused. Identical screen names are flagged on both entities. A handle change keeps one entity only when a provider id ties them.

## D-050 Attribution is computed from reviewed links (ADOPTED, Phase 08)

Levels NONE, THIRD_PARTY_LABELED, SELF_CLAIMED, CORROBORATED, DISPUTED. A self claim becomes CORROBORATED only through an independent reviewed label (not from an organization that operates the claimant) or a reviewed on-chain proof. A dispute overrides. Unreviewed links never count. Confidence stays LOW or MODERATE except for proof (HIGH). Levels respect time windows.

## D-051 No ranking and no superlatives (ADOPTED, Phase 08)

The registry stores the rank a list claimed, as stated, and never its own rank, score or grade. Search orders by label. Superlative phrasing is refused in every free-text field by a regex (a guard, not a proof). A profit claim is its own category and does not imply other categories.

## D-052 Fixture controls (ADOPTED, Phase 08)

Fixture entities carry a label, cannot be watched, cannot be linked to real entities, and fixture imports are refused against the tracked database before it is opened. The content guard checks stored labels.

## D-053 Stale evidence needs a written reason (ADOPTED, Phase 08)

Evidence older than the source's max age, or undated, is stale. Approval needs fresh evidence or `accept_stale_reason`, stored and shown. Undated evidence is never fresh.

## D-054 Mirror to social_wallet_attributions by recomputed state (ADOPTED, Phase 08)

Each link change recomputes the level and writes it (or RETRACTED for NONE) to the Phase 01 append-only table, with `[sync N]` in the basis. Retracting a dispute restores the earlier level instead of leaving a stale row on top.

## D-055 Catalyst research list imports as undated candidates (ADOPTED, Phase 08)

`import-catalyst` adds the repo's trader research list as unreviewed candidates with undated REPO_LIST evidence. It is refused against the tracked database until a person decides to commit those rows.

## D-056 Prompt 09 is the wallet attribution and activity phase (ADOPTED, Phase 09, 2026-10-12)

Elving supplied Prompt 09 ("Verify wallet links and observe activity without identity overreach"). It takes the Phase 09 slot. The proposed Phase 09 (entity resolution for accounts and projects) moves to carry-over C-9, unscheduled. Phase 09 delivers most of what proposed Phase 14 (claimed-wallet linking) described; what is left of 14 is collecting live evidence. No live provider call was made.

## D-057 Assertions are the record; identity and control are kept apart (ADOPTED, Phase 09)

`social_wallet_assertions` (migration 9) holds one claim per row with evidence type, evidence reference, observed and validity times, confidence, review state and status. The claim never changes; review and status changes go to `social_wallet_audit`. `real_world_identity` is UNKNOWN on every row and no name column exists. The level a reader sees comes from `wallet_assertions.explain()`, which recomputes it from active, reviewed rows at a given time and lists why any row does not count.

## D-058 What each evidence type can prove (ADOPTED, Phase 09)

Self-disclosure reaches SELF_CLAIMED. A signed message reaches SIGNATURE_VERIFIED only if the signature verifies in code, the message names the account, and a person approves. An independent source corroborates a self claim only after review and only if it neither is nor operates the account. A third-party claim stays THIRD_PARTY_CLAIMED. A transaction pattern never counts. Confidence cannot be set above the evidence type's maximum. Reason: the prompt's rule that matching names and suggestive transfers never create a link, and D-003.

## D-059 Signature verification is built in, pure Python, verify-only (ADOPTED, Phase 09)

`sigverify.py` checks ed25519 (Solana) and EIP-191 personal_sign (EVM) with no new dependency, tested against public vectors (RFC 8032 test 2 and the published eth-account "Some data" vector). There is no signing code and no key handling in the lab (hard rule). Other chain families return UNSUPPORTED rather than a guess. The message text is hashed, not stored (D-013).

## D-060 Custody, protocol and pool addresses are not controlled by a person (ADOPTED, Phase 09)

A wallet labelled CUSTODY_EXCHANGE, CUSTODY_OTHER, PROTOCOL or POOL cannot be approved as controlled and shows UNSUPPORTED_CUSTODY; it is not tracked unless `--allow-custody` is given. Labels come from sourced, append-only rows, with the existing m09 list as the fallback; a sourced NO_SPECIAL_LABEL row corrects a built-in label.

## D-061 Wallet-level monitoring claims no owner; safe defaults (ADOPTED, Phase 09)

Tracking needs a reason and a name, caps at 25 active wallets and 50 transactions per fetch by default, starts at the time of adding, and keeps history on pause and remove. Fixture wallets are refused against the tracked database. Reason: the prompt asks for add, remove and pause with safe defaults and for monitoring that does not claim who the wallet belongs to.

## D-062 Activity is observation, classified by provider type and by shape, never P&L (ADOPTED, Phase 09)

One event per (chain, transaction, wallet). The classifier uses the provider's type and the shape of what moved; disagreement is UNCLASSIFIED with a rule id. A token transfer is never a sell. No price, cost basis, profit or loss column exists, and a test scans every column name. The existing `wallet.positions_from_wallet` is untouched. Reason: the gate says activity must not become P&L until the next phase.

## D-063 New Helius projection with full signatures; the old one is not used for activity (ADOPTED, Phase 09)

`helius_tx` truncates signatures to 12 characters, drops slot and failure state, and caps transfers at 12. Activity needs verifiable signatures, so `helius_wallet_tx` was added next to it in both collector copies (`bridge/collector.js`, `memelab/bridge/collector.js`) and in `Plan.wallet_activity`. The browser loads the collector from `main`, so the new projection reaches scheduled runs only when this branch is merged (same as D-021). Rows with truncated signatures are rejected, not stored.

## D-064 Funding relations are hypotheses and never attribute (ADOPTED, Phase 09)

Shared first funding is stored in its own table with `status` constrained to HYPOTHESIS, marked uninformative when the funder is custody, protocol or a pool, and shown in `why` as related by funding only. It never creates an assertion or changes a level.

## D-065 Phase 10 takes the slot of "mention extraction"; that work becomes carry-over C-10 (ADOPTED, Phase 10)

Prompt 10 asked for wallet performance accounting. The old proposed Phase 10 (mentions by contract address) moves to C-10 with its text unchanged. Phases 11 onward keep their numbers.

## D-066 FIFO is the primary lot convention; AVCO is always a sensitivity (ADOPTED, Phase 10)

FIFO is what most tax and exchange tools show and is easy to audit by hand. AVCO (pro rata across open lots) is computed on every run. A position that closes with only trading lots has the same total under both, so the choice matters only for partly closed positions. A delta is material above 5% of the primary realized figure or on a sign flip. Stablecoins at 1.00 and no return matching are the other sensitivities.

## D-067 Wallet-level only; a transfer is never a trade (ADOPTED, Phase 10)

Results carry `person_level_claim: false`. A transfer in is an unknown-basis lot, never a buy. An analyst-marked airdrop has zero basis and is reported apart from trading. A transfer out keeps its basis off-book and gets it back only from the same counterparty. Reason: the gate forbids treating external flows as free profitable buys or gains.

## D-068 Wallet groups are declared, with a reason, and matched by signature (ADOPTED, Phase 10)

Moves between wallets of a group move basis and make no profit, but only when both sides carry the same transaction signature. A group without a declared reason is an error. A fee-on-transfer shortfall is a TRANSFER_TAX slice. The group is the analyst's choice, never an ownership claim (consistent with D-064).

## D-069 The score gate refuses sparse or incomplete wallets (ADOPTED, Phase 10)

No score below 20 closed fully known positions (the m28 floor), a 7-day span, 0.8 basis coverage, 0.9 price coverage, 0.2 unknown fee share, 0.1 unclassified share, or on a failed reconciliation. LOW_CONFIDENCE below 50 positions, with unestablished history, or when one position makes over half the profit. The score is the return excluding the biggest winner. Rankings include only scored wallets.

## D-070 Prices are supplied observations and are never fetched by the accounting (ADOPTED, Phase 10)

Prices and sell quotes are stored in `social_perf_prices` with a source, labelled estimates, and are inputs to the input hash. Mark-to-market goes stale after 24 h and quotes after 1 h. A missing quote is UNKNOWN, not zero. Liquidity estimates reuse the lab's own quote readers. A provider's P&L can be compared but is labelled an estimate and never changes a result.

## D-071 Performance gets its own tables; Phase 09 tables are read only (ADOPTED, Phase 10)

Migration 10 adds `social_perf_token_meta`, `social_perf_prices`, `social_perf_runs`, `social_perf_positions`, `social_perf_checks`. Phase 09 forbids price, USD and P&L columns in its wallet tables (D-062) and a test enforces it. A run is stored with its full input and result and can be verified by recomputation.

## D-072 The secrets test checks the shape of a key (ADOPTED, Phase 10)

The old check flagged any value after `api-key=` in a tracked file, including prose such as `api-key=...` in the handoff and the regex in `secrets.py`, so it failed on the Phase 09 branch. It now flags only a UUID or a token of 24 or more characters, with a test that the shape check still catches a UUID. This is why the Phase 10 baseline showed two failures, not the one the Phase 09 handoff expected.

## D-073 Information alpha is its own measurement; wallet profit and popularity are not inputs (ADOPTED, Phase 11)

The score judges public commentary against matched tokens. Phase 10 wallet performance stays separate, in separate tables, and `alpha_core` imports nothing from it. Attributed author trades appear as context flags only. Follower counts, views and engagement are never read; a source's `context` is echoed and ignored. Tests change both and show the score does not move. Reason: the gate keeps wallet profits apart, and popularity is not evidence of predictive value.

## D-074 Selection rules are fixed before outcomes and every exclusion is listed (ADOPTED, Phase 11)

Eligibility depends only on what was known at or near publication (source, resolved token, original, direction, conditional, sarcasm, extraction uncertainty, capture lag, conflicts, repeats, as_of). Excluded calls stay in the output with a reason. Calls first seen more than an hour after publication, or never timestamped, are HINDSIGHT_CAPTURE_RISK. A source whose supplied posts are under 80% of the posts the collector enumerated for it is declined, and an unknown universe caps the tier at PRELIMINARY. Opposite statements within 24 h exclude all of them; the later one never wins. Reason: the usual way to fake a track record is to pick the winners afterwards.

## D-075 Historical candles only, nothing after as_of, a delay and costs (ADOPTED, Phase 11)

Prices are supplied candles marked HISTORICAL_CANDLE; the schema refuses anything else, and a live quote replayed as a past price is rejected. No candle starting after `as_of` is read, a horizon not yet elapsed is not evaluable, and a gap is never filled beyond a 15 minute order wait. Entry is at max(published, first observed) + 300 s. Costs per side are 1.0% fee, 0.5% slippage and constant-product impact; participation over 5% at entry is not tradable at that size. Reason: Phase 05 already forbids today's price as the posting-time price, and a result that ignores delay and costs flatters every source.

## D-076 The comparison pool excludes everything anyone called, and includes the dead (ADOPTED, Phase 11)

Controls are matched on liquidity and trailing volume from candles completed before entry, require a candle at entry, and follow the same entry, exit and cost rules. Tokens called by any source in the run are excluded, since promotion selects pumpers; delisted tokens are included. Fewer than 5 controls means no relative return. Reason: a control group chosen with hindsight, or one that drops rugs, inflates every score.

## D-077 Delisting is a total loss for a long and gets no extra credit for a short (ADOPTED, Phase 11)

Both treatments are conservative toward the source. A series that ends with no delisting is not evaluable and is not treated as a loss; coverage reports it and gates the tier. Reason: neither choice may depend on whether the token later went up.

## D-078 The score is conservative, shrunk, tiered and may be absent (ADOPTED, Phase 11)

One primary horizon (24 h) fixed by policy. Score = 50 + 50 * tanh(w * edge / 0.5) with w = n / (n + 20) and the edge taken at the end of the 95% interval nearest zero (zero if it spans zero). The point estimate is shown as `score_point`. Tiers: UNVERIFIED (no score), PRELIMINARY, VALIDATED (30 calls, 20 tokens, coverage 0.7, known completeness 0.9, interval excludes zero, same sign in both halves, no token over 20%). Below 10 independent calls with a baseline there is no score. Ranking lists only scored sources and says so when nobody is. Fixture runs are never evidence. Reason: 3 good calls must not look like skill, and a noisy sample must read as no edge.

## D-079 Phase 11 slot taken by Prompt 11; attention metrics move to C-11 (ADOPTED, Phase 11)

Prompt 11 replaced the proposed "attention metrics" phase. That entry is carried over as C-11 in ROADMAP.md unchanged. Migration 11 adds `social_alpha_series`, `social_alpha_candles`, `social_alpha_runs`, `social_alpha_scores` and touches no earlier table. The prompt asked for `delisted tokens`, `price gaps` and `temporal leakage` tests; they are `test_delisted_tokens_are_total_losses_for_longs_and_get_no_extra_credit_for_shorts`, `test_price_gaps_are_not_filled`, `test_nothing_after_as_of_is_used` and `test_entry_and_matching_do_not_depend_on_later_candles`.

## D-080 Phase 12 slot taken by Prompt 12; paid, bot and coordination signals move to C-12 (ADOPTED, Phase 12)

Prompt 12 replaced the proposed "paid, bot and coordination signals" phase. That entry is carried over as C-12 in ROADMAP.md unchanged, and Phases 17 and 18 now also depend on it. Migration 12 adds `social_chrono_runs` and `social_chrono_flags` and touches no earlier table.

## D-081 Order is decided by intervals, never by point times (ADOPTED, Phase 12)

Every entry gets an interval from its clock and precision: a platform timestamp [t - 1, t + precision + 1), with precision 1 s unless the input says otherwise (60 s for a minute display); a relative "x ago" time +/- 3600 s by default; a block time [t - 2, t + 3); a collector sighting +/- 5 s. A publication time is capped by the first sighting, and a missing one is "no later than the first sighting". A slot without a block time is bounded by the block times of neighbouring slots in the input, or left unplaced. Two entries are ordered only when one interval ends before the other starts; otherwise the pair is INDETERMINATE and the summary lists it under not established. Reason: a minute-precision post and a swap in the same minute have no knowable order, and inventing one is the error the prompt warns about.

## D-082 Only LINKED and uncontested SELF_CLAIMED wallets feed patterns (ADOPTED, Phase 12)

The Phase 09 level decides. SIGNATURE_VERIFIED and CORROBORATED are LINKED (patterns are INFERENCE). An uncontested SELF_CLAIMED wallet is CLAIMED (patterns are HEURISTIC). A self-claim that another account also makes is CONTESTED; DISPUTED, THIRD_PARTY_CLAIMED, HYPOTHESIS_ONLY and NONE are not attributed; their events stay on the timeline as "unverified association" with a data-quality flag and no pattern. A wallet labelled exchange custody, protocol or pool, or at UNSUPPORTED_CUSTODY, is left off the timeline. Reason: an uncertain attribution must never become an accusation, and a shared custodian mixes different people.

## D-083 Risk flags are never FACT and never name intent (ADOPTED, Phase 12)

Flag categories are CORROBORATION, RISK, CONTEXT and DATA_QUALITY. A RISK flag is INFERENCE or HEURISTIC, needs a LINKED or CLAIMED wallet and cites evidence; the schema refuses anything else, and only DATA_QUALITY flags may be FACT. A buy before a bullish post is RISK only when the post did not say the author holds; with a stated holding it is DISCLOSED_POSITION_CONSISTENT (CORROBORATION). A sale after a bullish post and within 24 h is POTENTIAL_DISTRIBUTION_DURING_PROMOTION, INFERENCE when the order is certain, HEURISTIC when it is not. Generated text is checked against a list of accusatory words (whole words) and a hit refuses the result. Reason: the gate forbids unsupported ownership or manipulation claims, and wording drifts unless something checks it.

## D-084 Absence and transfers are never read as trades (ADOPTED, Phase 12)

TALK_WITHOUT_OBSERVED_TRADE and TRADE_WITHOUT_OBSERVED_TALK are UNKNOWN and carry the coverage behind them (no associated wallet, provider unavailable, not monitored, partial, full) or whether the source's posts were enumerated. A token transfer out is not a sale, a move to a custody-labelled address is "moved to exchange custody", a transfer between two associated wallets is internal, and a leg in another token or the native coin is UNRELATED_ASSET. Monitoring coverage for stored wallets runs from `watch_since` to the last good fetch, which overstates coverage when a fetch hit its transaction cap; that limit is written in CHRONOLOGY_12.md. Reason: absence of a monitored trade is not evidence that none occurred.


## D-085 Phase 13 slot taken by Prompt 13; trader identity verification moves to C-13 (ADOPTED, Phase 13)

Prompt 13 replaced the proposed "trader identity verification" phase. That entry is carried over as C-13 in ROADMAP.md unchanged, and Phases 14 and 15 now depend on C-13 instead of 13. Prompt 13 delivers part of the old Phase 19 (a social section in scout reports); Phase 19 keeps token and launch reports and watchlist alerts. No migration: the schema stays at 12.

## D-086 Social findings travel inside the existing reports; no table and no second watchlist (ADOPTED, Phase 13)

The research section is built at report time from stored Phase 07 and Phase 12 results and the tokens the scout or catalyst evaluated, and is appended to the report. It writes nothing: no table, no watchlist row, no rejection, no thesis. Reason: the prompt forbids duplicate scoring and parallel watchlists, and the inputs are already stored with provenance (snapshot run id, cluster key, chronology run and flag key, policy sha are printed in the section).

## D-087 Three lanes, copied not recomputed (ADOPTED, Phase 13)

Narrative attention comes from social findings only. Token structure is the existing fatal checks, copied. Executable entry is the existing status, copied. No lane reads another, so high attention cannot clear a fatal flag and a missing signal costs nothing. Research state follows the lanes: RESEARCH_CANDIDATE, REJECTED_STRUCTURE, NEEDS_STRUCTURAL_ANALYSIS, NO_SOCIAL_SIGNAL. A ticker-only mention is UNRESOLVED and listed apart. A finding whose symbol matches an analyzed token on another contract is SYMBOL_COLLISION and inherits nothing.

## D-088 Opt-in, versioned policy with provenance and a fixed zero execution impact (ADOPTED, Phase 13)

Off unless `--social` is given or `data/config.json` sets `social_research.enabled`. Policy schema `memelab.social.research.policy/1`; a policy file merges over the config. The attention weight is HEURISTIC and orders the social section only. Keys that would reach the score, status, rank, watchlist, fatal checks, sizing or orders are refused, and `trade_execution_impact` must be `none`. Every section prints the policy version, source, path and sha256. With the feature off the scout does not open the social store and the report is the pre-Phase-13 report; with it on and no data the section is a one-line no-op naming the reason.

## D-089 social-note is left as it is (ADOPTED, Phase 13)

`social-note` writes manual metrics into `social_snapshots` with no observation, account or time basis. The adapter does not read those rows, and the command keeps its arguments. Manual capture onto the inbound schema stays C-4. Reason: the prompt asks for sourced findings, and a manual metric is not one.

## D-090 Earlier rejections are reviewed, never reopened by attention (ADOPTED, Phase 13)

The latest verdict per mint before as_of (theses, then rejections; a later non-rejected thesis supersedes) is the prior rejection. It STANDS when the structure still fails or the token was not re-analyzed, and is REOPEN_FOR_REVIEW only when the existing checks ran again and no longer fired. The review is a label in the social section; the pipeline status is what the pipeline computed. Reason: changed social evidence is not a changed token.

## D-091 Phase 14 slot taken by Prompt 14; trader claimed-wallet linking moves to C-14 (ADOPTED, Phase 14)

Prompt 14 (readable, cited intelligence feed and digest) replaced the proposed Phase 14 "trader claimed-wallet linking: live evidence collection". That entry is carried over as C-14 in ROADMAP.md unchanged, and Phase 15 keeps its dependency on C-13. Prompt 14 delivers part of the old Phase 19 (a readable social report); Phase 19 keeps token and launch report sections and watchlist alerts. No migration: schema stays at 12.

## D-092 The feed is a read-only renderer with one stable JSON form (ADOPTED, Phase 14)

`feed_store` opens the database read only and builds an input document; `feed_core.build` turns it into `memelab.social.feed/1` (sorted keys, no clock, `feed_sha256`); the three markdown views render from that one document. Nothing is stored for the feed: an old brief is audited from its JSON, the narrative run id, the claim ids and the chronology runs it names. Reason: later alerts and the scheduler need a stable machine-readable source, and a second store of derived social data would drift.

## D-093 Group by identity or theme; repeats are counts, not people (ADOPTED, Phase 14)

Blocks are Phase 07 clusters (exact contract or structured theme), never authors or time slices. Each source appears once per role with its latest claim; reposts, forwards and repeating quotes are counted once with their original and only the first two are linked. Ticker-only mentions are a separate unresolved list. Reason: the prompt asks for discussion grouped by token or theme rather than reverse-chronological influencer output.

## D-094 Priority is HEURISTIC and orders the report only; the no-signal line is literal (ADOPTED, Phase 14)

HIGH: in window, fresh (24 h), coverage ok, and two or more independent sources or a Phase 12 RISK flag. MEDIUM: one source or not estimable. LOW: out of window, insufficient coverage or stale. Priority reaches no score, status, watchlist, rejection or trade. With no HIGH item the brief opens with "No supported high-priority observations." and the reason, and lists lower items below it.

## D-095 No post wording, summaries or display names in a report; provider strings reduced to safe forms (ADOPTED, Phase 14)

Reports are lab-written but may be shared, and post text can carry instructions to automated readers. So the feed renders only structure: counts, enums, times, ids, handles and symbols that match a safe character set (else a neutral label), and links that pass `safe_url` (http(s), no credentials, no query or fragment, ASCII host, no Telegram invite or private-chat link). Own-words summaries (D-010) stay in `social claims` and are not rendered here. Any remaining provider string is markdown-escaped with control and bidi characters removed. A post the extractor marked injection-suspected is named as a reason to doubt.

## D-096 Fixture demos run the real read path and are watermarked (ADOPTED, Phase 14)

`social feed-demo` and `--fixture` build a throwaway SQLite store from an invented spec through the real store functions and the real narrative engine, then read it with `feed_store`. Every view carries the watermark at top and bottom, the JSON says `fixture: true`, and `--report-dir` names end in `_FIXTURE`. The live commands skip fixture snapshots unless `--include-fixtures` is given. Reason: the prompt forbids fake live output, and a demo that bypassed the store would not prove the read path.

## D-097 Phase 15 slot taken by Prompt 15; trader call capture moves to C-15 (ADOPTED, Phase 15, 2026-10-12)

Prompt 15 (controlled research alerts and scheduling) replaced the proposed Phase 15 "trader call capture". That entry is carried over as C-15 in ROADMAP.md unchanged, and Phase 16 now depends on C-15. Prompt 15 delivers the watchlist-alert part of the old Phase 19 for social changes and the scheduling templates part of Phase 20; neither job is enabled. No migration: the public schema stays at 12.

## D-098 Alerts read the feed document only; the feed gains three fields under the same schema name (ADOPTED, Phase 15)

Alerts consume `memelab.social.feed/1` and nothing else, so there is no second detector. Feed items gained `activity.window_mentions`, `chronology` (Phase 12 flags with category, bucket, attribution, time, rule, run) and, on each stance change, `source_id`, `before_at` and `after_at`. The schema name is kept because no field changed meaning (Phase 14 handoff rule); the Phase 14 sample report changed only in its printed `feed_sha256`.

## D-099 Five alert policies; reputation is registry link or allowlist; repetition never qualifies (ADOPTED, Phase 15)

convergence, wallet_corroboration, risk, stance_switch and conversation_growth, with thresholds in ALERTS_15.md (HEURISTIC). A reputable source is an independent original linked to a registry trader or named on Elving's allowlist; follower counts and engagement are never read (same rule as D-073), bots and aggregators never count. Wallet corroboration needs a LINKED wallet (D-082); CLAIMED is suppressed as unverified. Growth is measured against the item's own earlier snapshots and needs two independent sources, so 100 reposts of one post raise nothing. Token-specific policies need a readable chain and contract and fresh data.

## D-100 Spam control: dedupe, cooldown, daily cap, quiet hours, interval (ADOPTED, Phase 15)

A dedupe key alerts once per mode within 30 days. Cooldowns per policy and item (risk per flag, stance per source). Daily cap 8 per America/New_York day. Quiet hours 22:00 to 07:00 New York wall time: alerts are held, released after 07:00 and expire unsent after 14 h; no severity bypasses by default. Evaluation at most every 60 minutes and never twice on the same snapshot. Suppressions are stored with a reason code and printed.

## D-101 Alert state is private and split by mode (ADOPTED, Phase 15)

State (runs, alerts, suppressions, baselines, ledger, cooldown resets, schedule slots) is in `data/private/alerts.sqlite` (gitignored; `MEMELAB_ALERT_DB`), never in the tracked database, which `connect()` refuses. Destinations are personal and the public schema stays at 12. Dry run and send keep separate state so a dry run never uses up a real alert's dedupe key or cooldown.

## D-102 Delivery: file sink first, remote only with consent and credentials, at most once (ADOPTED, Phase 15)

The file sink always runs and is never reported as a delivery to a device. Telegram (one bot, one chat, plain text) and email (SMTP STARTTLS) exist only when the private config enables them and their secrets are in the environment. Sending needs `--send` plus `notifications_opt_in` and `send_enabled` true; otherwise it is a dry run, and `--send` without consent exits 2. A config holding a secret is refused. Fixture alerts never go remote. The ledger records `attempted` before every call; a crash leaves `outcome_unknown`, which is never resent. Retryable failures retry after 5 min, 30 min, 2 h, up to 4 attempts; 4xx other than 429 do not retry. Destinations are hashed in the ledger; errors are redacted.

## D-103 Per-provider daily cost ceilings (ADOPTED, Phase 15)

Ceilings per provider per day cover transports (file, telegram, email: 0 USD per message today) and upstream paid APIs (x_api and llm at 0 USD, so no paid refresh; telegram_bot free). A transport over its ceiling is not called and the attempt is logged as failed with the reason. `social alerts preflight` reads live `social_api_spend` rows for the UTC billing day and tells a scheduled run which refresh step may run. Raising a ceiling is Elving's cost decision (D-009, D-023, D-036).

## D-104 Schedule templates are data, disabled, DST-safe and idempotent; no GitHub Actions (ADOPTED, Phase 15)

Daily (07:47 New York) and weekly (Monday 08:13) templates carry `enabled: false` and the consent keys they need. Gap times run once at the first valid minute; repeated fall-back times run once at the first occurrence. A slot key per local date or ISO week makes a repeated trigger or a restart a no-op; a slot started under 2 h ago is skipped, an older unfinished one is taken over. Templates may not run more often than hourly. No Actions workflow was added: a public repo's Actions would need the delivery secrets as repository secrets and would hold state outside the private file. Enabling a job is a scheduled task Elving approves.

## D-105 Phase 16 slot taken by Prompt 16; call outcome tracking and trader scoring move to C-16 (ADOPTED, Phase 16, 2026-10-12)

Prompt 16 (immutable signal ledger and forward evaluation) replaced the proposed Phase 16 "call outcome tracking and trader scoring". The ledger delivers the forward-return measurement part for any lab signal. Scoring traders on top of it is carried over as C-16 (depends on C-15 and Phase 16). Phase 19 now also depends on 16 for an outcome section. No migration: the public schema stays at 12.

## D-106 The signal ledger is private, append-only and hash-chained (ADOPTED, Phase 16)

`data/private/signal_ledger.sqlite` (gitignored; `MEMELAB_SIGNAL_LEDGER`), never the tracked database, which `connect()` refuses. Signals hold claim and source references that are private research state, and outcomes would otherwise be committed by the scheduled runs on `main`. One journal table holds SIGNAL, OBSERVATION, ANNOTATION and OUTCOME entries in recorded order. SQLite triggers refuse UPDATE and DELETE; each entry stores its body hash and the previous entry hash, and `social evaluate verify` recomputes both. Revisions, maturity, deletions and invalidations are new entries that point at what they supersede.

## D-107 What a signal record holds and when it is captured (ADOPTED, Phase 16)

Signal id = hash of emitter, emitter ref, chain, contract and generated time. The record keeps disposition (EMITTED, REJECTED, SUPPRESSED, NEEDS_REVIEW), classifier, scoring and policy versions, references, exact chain and contract, event, generated and captured times, the market facts dated at or before generation (price, liquidity, sell route), the evaluation assumptions and every missing field with a reason. Facts dated after generation are dropped and counted. Capture more than 1 h after generation is flagged LATE_CAPTURE; capture before generation is refused. Same id with a different context is refused. Rejected and suppressed signals are recorded and evaluated like emitted ones.

## D-108 Outcome timing and look-ahead rules (ADOPTED, Phase 16)

Entry = generated time + 300 s execution lag, never the event time. Exit = entry + horizon (1h, 6h, 24h, 72h, 7d). Prices are the first dated midpoint at or after the target within 900 s; a candle gives its open at its start and its close at its end. Only observations with `available_at <= as_of` count; future-dated observations and unfinished candles are refused. An evaluation time may not go backwards and may not be later than the clock; replay of an earlier time is read-only. A missing exit stays PENDING while its window is open, then becomes MISSING.

## D-109 Returns: displayed, modeled and quoted kept apart; no invented exits (ADOPTED, Phase 16)

`return_mid_gross` is the displayed price move and is never called proceeds. `return_net_modeled` uses 100 bps fee and 50 bps slippage per side plus constant-product impact at a hypothetical 500 USD size (same convention as Phase 11). `return_net_quoted` uses an actual sell route quote within 120 s of the exit. A route quote never replaces a midpoint. A delisted token has no exit price and no return; the last observed price is shown. Max excursion needs a path with no gap over horizon / 12.

## D-110 Outcome statuses and executability thresholds (ADOPTED, Phase 16)

PENDING, MEASURED, MISSING, NON_EXECUTABLE, INVALIDATED, each with reason codes. NON_EXECUTABLE when entry participation or exit participation exceeds 5% of reported liquidity, liquidity is zero, a route is missing, the quote returns less than 75% of the displayed value (PRICE_QUOTE_MISMATCH), the token was delisted, or the signal is a short on spot. A quote above the displayed price by more than 2% is flagged and ignored. INVALIDATED only through an INVALIDATED or IDENTITY_REVISED annotation or an event time later than the signal. A deleted source does not invalidate.

## D-111 Coverage report, not a score (ADOPTED, Phase 16)

`social evaluate report` gives per horizon the count per status, coverage = measured / matured, exclusion reasons and the split by disposition. A median net modeled return is shown only with 5 or more MEASURED outcomes and is descriptive. No trader or source score is produced in this phase (C-16).


## D-112 Phase 17 slot taken by Prompt 17; m19 and launch integration move to C-17 (ADOPTED, Phase 17, 2026-10-12)

Prompt 17 (historical replay, baselines and statistical honesty) replaced the proposed Phase 17 "Integration: m19 attention and launch social". That integration is carried over as C-17 with its old gate. Phase 19 now depends on C-17 instead of 17. No migration: the public schema stays at 12. The replay reads stored data only and writes nothing unless `--out` is given.

## D-113 Availability, not publication, places a record on the replay clock (ADOPTED, Phase 17)

Every replay record carries the earliest time it was demonstrably available: a post's first observation, a wallet event's or trending list's arrival, a candle's close plus a documented provider lag, or the lab's capture time. Records without such a time are excluded and counted. Strategies read only through `CutoffView`, whose accessors are audited; a record from after the cutoff raises `LeakageError`. Real collector files use the capture time by default (demonstrable); provider lag is a labelled reconstruction (`--candle-availability provider`).

## D-114 Four strategies, one signal per configuration and token in 72 h (ADOPTED, Phase 17)

INDIVIDUAL (one original LONG post), CONVERGENCE (independence groups, not accounts; reposts and content duplicates never count), SOCIAL_WALLET (posts plus a linked-wallet BUY with accepted linkage SELF_CLAIMED, SIGNED_MESSAGE or CHAIN_EVIDENCE; a SELL by a posting source's wallet suppresses), TRENDING as the raw baseline (raw mentions including reposts, or a provider trending list). An opposite original post inside 24 h suppresses (a)-(c). Suppressions are counted in the report.

## D-115 Chronological splits with embargo and train-only tuning (ADOPTED, Phase 17)

50 / 25 / 25 by decision time. Labels are computed with the clock of their split (train boundary, validation boundary, data end). A sample whose outcome window crosses its boundary is purged. Thresholds are chosen on train only; `LabelGate` refuses validation labels during tuning and test labels before the configuration is frozen with a hash. Truncation invariance (signals and train metrics unchanged when all later data are removed) is the leakage proof printed with every run.

## D-116 Matched controls from what was visible at the decision time (ADOPTED, Phase 17)

Same chain, price at most 2 h old, no delisting known, no visible post mention in 7 days or trending listing in 24 h, liquidity within a factor 3, market cap within a factor 4 when known; up to 8, at least 3 measured. Unlike Phase 11 (which bans every token any source ever called), only mentions visible at the decision time exclude a control, because later mentions are future information. Calendar regime is matched by sharing the decision time.

## D-117 Two lenses; missing prices stay missing (ADOPTED, Phase 17)

Conservative (headline): a long whose token was delisted before the exit is -100%, for signals and controls alike. Measured-only is shown beside it. A missing price without delisting evidence is never filled in. Non-executable outcomes (Phase 16 rules) are counted in executability and never contribute a return.

## D-118 Honest verdicts (ADOPTED, Phase 17)

Medians, not means, are the headline. Intervals are Bonferroni-adjusted for 4 strategies x 4 horizons. Nothing is estimated below 10 values. Verdicts: INSUFFICIENT_DATA, INSUFFICIENT_SAMPLE (fewer than 30 test values with controls), CANNOT_VALIDATE_YET (survivorship risk, interval includes zero, one outcome dominates, validation disagrees or is too small), else BETTER_ or WORSE_THAN_CONTROLS_IN_REPLAY, always labelled a historical replay and never a forward test. A universe not declared to include delisted tokens is a survivorship risk.

## D-119 Phase 18 slot taken by Prompt 18; catalyst attention integration moves to C-18 (ADOPTED, Phase 18, 2026-10-12)

Prompt 18 (end-to-end release engineering, operational audit and delivery) replaced the proposed Phase 18 "Integration: catalyst attention and assessment". That entry is carried over as C-18 with its old gate. Phase 19 now depends on C-18 instead of 18. Prompt 18 also delivers part of the old Phase 21 (docs and an end-to-end validation on fixtures, a pull request for review); the supervised live run, the rebase on `main` and the merge stay in 21. No migration: the public schema stays at 12. No new provider integration and no refactor: the only code added is two read-only release tools and their tests.

## D-120 Release proof is a clean clone with the network blocked (ADOPTED, Phase 18)

`tools/release_e2e.py` clones the committed HEAD into a temp folder, removes every credential variable, points every database and private file at the temp folder, and installs a Python audit hook that refuses and logs any socket connect or DNS lookup (HTTP proxies point at a closed port for non-Python children). A run passes only when every stage returns its expected exit code, the hook logged nothing, `git status --porcelain` in the clone is empty and the tracked database is byte-identical. Reason: "no live billable request" and "no stray files" must be shown by the run itself, not asserted.

## D-121 Expected non-zero exits are part of the contract (ADOPTED, Phase 18)

Health commands exit 1 while a route is not ready (`x-health`, `tg-health`, `memelab.secrets status`); live ingest without a token exits 1 before any call; `alerts run --send` without consent exits 2; tracking a custody wallet exits 1. A pure re-ingest of an already processed file whose other units are down exits 1, because D-018 counts only usable units and a replayed unit is skipped, not usable. This is recorded as intended behaviour, not changed in a release phase; a scheduled run that re-ships an old file will report FAILED for that run, and `social status` still shows the earlier results. Changing it would be a small ingest change for a later phase if Elving wants replays to count as OK.

## D-122 Release audit scope and what it does not prove (ADOPTED, Phase 18)

`tools/release_audit.py` scans the tracked tree and every blob reachable from any ref for credential shapes (Anthropic, GitHub, Telegram bot, AWS, X bearer, PEM keys, `api-key=` values, bearer headers, 64-byte keypair arrays, key-material fields) and the code for signing, sending or order placement; it prints locations and rule names, never values. Placeholder shapes with fewer than 8 distinct characters are listed as reviewed. It also runs the content guard on this branch and on `main`, migrates copies of both lab databases, checks example configs are off by default, lists network paths, and runs syntax checks (Python `ast`, `node --check`) and pyflakes as information. It cannot prove a credential was never typed somewhere outside git, and pattern scans miss formats they do not know. pyflakes findings (unused imports and variables) are reported, not fixed, in a release phase.

## D-123 Session paths in public data on `main` are reported, not edited (ADOPTED, Phase 18)

The scheduled runs on `main` write absolute session paths (for example `report_path` values under `/tmp/claude-0/...`) into `data/state/latest.json`, `state/latest.json`, `data/memelab.sqlite` and two scout reports. They expose session folder names, not credentials. The feature branch never edits those files (D-001), so the audit lists them as information and the fix (write repo-relative paths in the state export) is left for Phase 20, where state export rules belong.

## D-124 Pull request opened for review, not merged (ADOPTED, Phase 18)

The prompt asks for a pull request where repo access permits. The branch is pushed by fast-forward through the GitHub Git Data API (no force, D-001) and a pull request from `feature/social-intelligence` into `main` is opened for Elving to review. Nobody merges it in this phase: merging changes what the scheduled runs load from `main` (for example the collector projections of D-021 and D-063) and is Phase 21 work.


## D-M00-001 Preserve immutable audit chronology and pin remediation branch (ADOPTED for M00, 2026-10-13)

Base the evidence remediation branch `remediation/social-intelligence-m00` on `audit/social-intelligence-phase06` at `b4c4216b9391227be5fdfe7cfe20b60e32d9e8f6`, with application baseline `698f73b854567ce60b56ce275b5ab6822a9d5f60`. Open a PR against the audit publication branch for review; do not merge to `main` or rewrite the 06 report. Preserve the old Phase 18 handoff as labeled history, while publishing the current M00 blocker above it.

## D-M00-002 Do not infer missing primary evidence from summaries (ADOPTED, 2026-10-13)

The Library search recovered five source titles; with Phase 06 tracked, 6/8 expected inputs can now be inspected. The separate Phase 05 statement that an earlier reviewer read Phase 02 is not a source copy. `02_ARCHITECTURE_AUDIT.md`, `03_RESEARCH_VALIDITY.md` and original probe scripts/logs remain unavailable. The crosswalk is indexed text only, with missing primary support visibly labeled. M00 cannot pass from metadata, hashes, test fixtures or prose alone.

## D-M00-003 Separate artifact integrity from independent finding resolution (ADOPTED, 2026-10-13)

Implement a no-network SHA-256 audit input check and negative tests. `tools/check_audit_evidence.py` can exit 0 when **partial integrity** is sound while loudly returning `BLOCKED`; acceptance requires `--require-complete` and independent source/probe reconciliation. Do not change module implementations in an evidence-recovery phase, do not conceal a killed full regression suite (exit 137), and do not mark an AUD/ARCH/ADV/OPS finding resolved on these checks.


## D-M00-004 Preserve non-deterministic QA failures as an open investigation (ADOPTED, 2026-10-13)

A one-process full pytest run was terminated with exit 137 around 70%. A bounded combined run stopped after two failures: the known catalyst assertion and social ingestion log-content test (2 failed, 295 passed); the latter passes alone. No tests were skipped, assertions weakened or implementation modified. This creates a new **potential test-order/environment reliability risk** requiring independent reproduction; M00 cannot certify the full suite.


## D-M00-005 Earlier project conversations locate missing originals but do not supply report bytes (ADOPTED, 2026-10-13)

Prior project conversation output explicitly linked `02_ARCHITECTURE_AUDIT.md` and `03_RESEARCH_VALIDITY.md` and sequential versions of `FINDINGS.md`. Phase 02 added AUD-018–023 and Phase 03 added AUD-024–033, which are missing from the published consolidated finding register. Locators are cataloged in `audits/social-intelligence/M00_PRIOR_CHAT_LOCATORS.md`. Original titles/link strings are valid recovery leads, not proof of report contents. Add these IDs to an **unverified** crosswalk partition; do not create synthetic report files, assign invented severities, or advance M01 until the originals are recovered and independently reviewed. The next reviewer should retrieve the original chat attachments or their original archives.


## D-M00-006 Restore original Phase 02 and 03 reports and preserve both findings snapshots (ADOPTED, 2026-10-13)

The owner supplied the original Phase 02 Architecture report, Phase 03 Research Validity report and their respective `FINDINGS.md` snapshots. Exact SHA-256 and byte count were matched before archiving (`audits/social-intelligence/recovered/`); the source snapshots remain unmodified. Canonical findings gain source-authored AUD-018–033 with original severity/evidence qualifications and retain all Phase 06 strategic entries. Crosswalk now tracks 33 AUD + 15 ARCH + 9 ADV + 10 OPS IDs; source line anchors do not constitute independently reproduced defects. Phase 03's historical lack of Phase 02 file is reconciled by retaining that original note but documenting its now-recovered state. AUD-032 explicitly reconfirms AUD-002, not a separate observed event. R-01/R-10/R-12 acceptance scope now explicitly includes intrabar fills, wallet future marks, predictive-validation qualifications and no-route exits. M00 is still blocked pending independent review and archive/probe/requirements acceptance. M01 is not authorized. No application changes, paid calls or live operations.
