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
