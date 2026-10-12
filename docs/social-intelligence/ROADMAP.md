# Social & Trader Intelligence: roadmap

Contract: [EXECUTION.md](EXECUTION.md). Choices: [DECISIONS.md](DECISIONS.md). Current position: [HANDOFF.md](HANDOFF.md). Baseline: [AUDIT_00.md](AUDIT_00.md).

Status values: DONE, NEXT, PLANNED, BLOCKED.

Phases 00 to 07 came with written phase prompts. Phases 08 to 21 below are a proposed sequence built from the Phase 00 audit. When the prompt for a phase is supplied, that prompt replaces the entry here and the change is logged in DECISIONS.md (Phase 01: D-011, Phase 02: D-015, Phase 03: D-022, Phase 04: D-026, Phase 05: D-030, Phase 06: D-035, Phase 07: D-041). Source status per route: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

Status values also include SUPERSEDED (folded into another phase).

Every gate also includes the standing gate: full test suite run and recorded, no new failures, no stray files, no raw third-party social content in the public repo, HANDOFF.md rewritten, commit made.

| Phase | Title | Depends on | Status |
|---|---|---|---|
| 00 | Repo audit and execution contract | none | DONE |
| 01 | Durable schemas, evidence provenance and migration safety (Prompt 01) | 00 | DONE |
| 02 | Ingestion contract and bridge/inbox adapter (Prompt 02) | 01 | DONE |
| 03 | X monitoring through the official X API v2 (Prompt 03; old slot "social schema" was SUPERSEDED by 01) | 02 | DONE (live UNAVAILABLE, D-023) |
| 04 | Telegram channel monitoring through the official Bot API (Prompt 04; old slot "manual capture" moved to C-4) | 02, 03 | DONE (live UNAVAILABLE, D-027) |
| 05 | Exact token identity and timestamped market context (Prompt 05; old slot "source registry" moved to C-5) | 01, 02 | DONE (fixtures only, D-030) |
| 06 | Evidence-grounded structured claim extraction (Prompt 06; old slot "X via signed-in Chrome" moved to C-6) | 05 | DONE (no model configured, D-036) |
| 07 | Narrative clustering, originators, amplifiers and independent corroboration (Prompt 07; old slot "Telegram via Chrome" moved to C-7) | 04, 05, 06 | DONE (fixtures only, D-041) |
| 08 | Collector: other readable sources (YouTube RSS, token-listed links) | 04, C-5 | NEXT (proposed) |
| 09 | Entity resolution: accounts, projects, tokens by address | C-6 | PLANNED |
| 10 | Mention extraction by contract address | 09 | PLANNED |
| 11 | Attention metrics with sampling notes | 10 | PLANNED |
| 12 | Paid, bot and coordination signals | 11 | PLANNED |
| 13 | Trader registry and identity verification | C-5, C-6 | PLANNED |
| 14 | Trader claimed-wallet linking (evidence levels) | 13 | PLANNED |
| 15 | Trader call capture | 10, 13 | PLANNED |
| 16 | Call outcome tracking and trader scoring | 15 | PLANNED |
| 17 | Integration: m19 attention and launch social | 11, 12 | PLANNED |
| 18 | Integration: catalyst attention and assessment | 11, 12 | PLANNED |
| 19 | Reporting sections and watchlist alerts | 16, 17, 18 | PLANNED |
| 20 | Scheduled-run integration and state export rules | 19 | PLANNED |
| 21 | End-to-end validation, docs, merge request | 20 | PLANNED |
| C-1 | Carry-over: test isolation and clock (old Phase 01) | 00 | PLANNED, unscheduled |
| C-2 | Carry-over: repo-wide guard against raw social text in tracked files (old Phase 02) | 02 | DONE |
| C-3 | Carry-over: purge stored X observations of posts NOT_FOUND for 24 h (X deletion rule), needed before live X data is kept | 03 | PLANNED, unscheduled |
| C-4 | Carry-over: manual capture onto the inbound schema (old proposed Phase 04) | 02 | PLANNED, unscheduled |
| C-5 | Carry-over: source registry for social and trader sources (old proposed Phase 05) | 02, 03, 04 | PLANNED, unscheduled |
| C-6 | Carry-over: X collector via signed-in Chrome (old proposed Phase 06, needs D-025) | 04, C-5 | PLANNED, unscheduled |
| C-7 | Carry-over: Telegram public channels via Chrome (old proposed Phase 07, needs D-028) | 04, C-5 | PLANNED, unscheduled |

## Phase gates

00. Baseline test results recorded; architecture and source-access constraints mapped; working branch established; EXECUTION, ROADMAP, DECISIONS, HANDOFF exist, are accurate and linked; no existing functionality changed.

01. (Prompt 01, DONE 2026-10-10) Exact schema and migrations documented in SCHEMA_01.md; tests prove insert/read/update/idempotency, empty-DB init, migration from a copy of the tracked DB, repeated ingestion, missing timestamps, duplicate provider ids, conflicting claims, rollback and recovery, and that watchlist, theses, entries, rejections and snapshot tables are unchanged; a fixture round trip runs through real SQLite. Full suite: only the known pre-existing clock failure remains. Performance and outcome tables are left to their own phases.

C-1. (old Phase 01 gate, carried over) `test_catalyst.py::test_dedup_corroboration_resurface_denial` passes on any date (fixed clock in the test); the EVM test no longer leaves `data/reports/*_BRETT_*.md` behind; pytest documented as the test dependency. Full suite green.

02. (Prompt 02, DONE 2026-10-10) Runnable import CLI (`python -m memelab social ingest`) on the existing bridge route (ship, `github_inbox.pull`, result file); versioned inbound schema; an observation persisted with provenance and verifiable by `social status --event`; repeated ingestion adds nothing (same file and renamed file); malformed, blocked, non-public, future and stale data handled; one unavailable connector recorded without ending the run or marking others healthy; tests pass and existing tests still pass. Details: CONNECTORS_02.md.

C-2. (old Phase 02 guard, DONE 2026-10-10, D-020) A check script or test fails if a tracked file holds a raw post text field or another blocked class; existing `social_snapshots` rows reviewed (99 rows, all numeric Jupiter holder-change metrics, `text_value` NULL in every row).

03. (Prompt 03, DONE 2026-10-10) Real adapter on the official X API v2 with the contract confirmed from docs.x.com (X_API_03.md); configured user, list, recent-search and recheck scopes; stable ids, author, provider time, link, text hash (no text kept), reference type, conversation and edit context, provenance and freshness through ingest(); pagination, rate limits, 429/403 handling, incremental cursor, billing guard, re-ingest dedupe; health command reports `credentials_missing`; live ingest explicitly marked UNAVAILABLE (D-023); fixture tests for originals, replies, reposts, quotes, duplicate ids, author changes, edits, deletions via recheck, pagination, 429, 403, billing guard, timestamps, freshness and secret redaction.

C-3. Posts that `recheck` finds NOT_FOUND have their earlier X observations (hash, metrics) purged or nulled within 24 hours; test proves it. Only needed once live X data is stored.

04. (Prompt 04, DONE 2026-10-11) Telegram Bot API adapter with the contract read from core.telegram.org (TELEGRAM_04.md): approved public channels only, getUpdates polling with a committed-only offset and webhook receiver with secret validation and a hashed spool; channel id, message id, poster (signature hash), send and edit time, forward origin ids, reply ids, text hash (no text kept), link, provenance; per-channel health with `credentials_missing` / `access_denied` / `not_public`; live ingest marked UNAVAILABLE (D-027); fixture tests for edits, duplicate and redelivered updates, forwards (never independent originals, D-029), deleted or inaccessible messages, authorization denial, out-of-order updates, 429/409/401/403/5xx, crash and kill resume; CLI fixture demo persisting an observation with provenance.

C-4. (old Phase 04) Manual captures (and `social-note`, without breaking its arguments) produce items in `memelab.social.inbound/1` with `access_mode='manual'` and go through the same ingester. Tests cover validation and rejection.

05. (Prompt 05, DONE 2026-10-12, IDENTITY_05.md) Downstream can request exact token identity plus timestamped evidence (`identity.token_identity`); no silent symbol-only match (a ticker resolves only through a same-post contract or a registry asset on a stated chain); resolved, ambiguous, unresolved and conflicted stored with candidates and evidence; market facts versioned with provider, units, quote currency, supply basis, source key and URL, fetched_at and validity window; posting-time price only from a covering candle; tests cover the prompt's list; demo of one ambiguous message and one resolved address; full suite with only the known clock failure.

C-5. (old proposed Phase 05) Social and trader sources registered with access mode (fetch, navigate, manual, blocked), tier, terms constraint and coverage gap, reusing the catalyst source registry pattern. Blocked sources stay disabled with the reason recorded. No collector code yet.

06. (Prompt 06, DONE 2026-10-12, CLAIMS_06.md) Observable, schema-validated pipeline from an ingested observation to a cited claim: text checked against the observation hash; Phase 05 identity per mention (unresolved allowed); deterministic token-reference claims without a model; model output validated against `memelab.social.claims.model/1` and grounded in exact quotes stored as offsets and hashes; `analysis_unavailable` with the reason when no model or budget; budget, cache, dedupe and replay; prompt-injection handling; truthful `llm-health` (`model_not_configured`); tests for the prompt's list; demo of one claim without a model and one mock-provider analysis; full suite with only the known clock failure.

C-6. (old proposed Phase 06) X reads through Elving's signed-in Chrome (D-009): profiles, public timelines and search results, read only, human-paced, stopping on any challenge. Output is derived fields plus own-words summaries (D-010). Fixtures recorded from real pages; parser tests pass offline. Needs D-025.

07. (Prompt 07, DONE 2026-10-12, NARRATIVES_07.md) Deterministic narrative clusters by resolved contract or structured tag; first-observed time, source count, independent source count, reposts and shared-original dependencies, mentions per sliding window, rate of change, confidence, coverage limits, chain and linked-token context; reposts and quotes never count as independent; inferred coordination is a hypothesis; `insufficient_coverage` when volume or independence is not estimable; immutable snapshots with change summaries and provenance; explain output; tests for 100-handle reposts, two early originals, same ticker on different contracts, multi-token themes, conflicts, changed opinion, deleted sources, time zones, stale data and two controlled daily windows.

C-7. (old proposed Phase 07) Telegram public channels (`t.me/s/<channel>` previews, or Telegram Web while signed in) parsed to channel-level metrics and summaries. Same fixture and policy rules as 06; no private groups. Needs D-028 first.

08. Additional readable sources wired in the same way, each with fixtures and coverage notes. Sources that fail from both routes are recorded as gaps, not worked around.

09. (token side delivered by Phase 05: tokens by address, ticker collisions and spoofed symbols) Accounts linked to projects and tokens only through evidence (official link on the token profile, link from the account to the contract address). Impersonation and name collisions flagged. Ticker-only matches never create a link.

10. Mentions counted only when they contain a contract address or a verified official link. Uses `identity.resolve_post` before the text is hashed (Phase 05 left the ingest wiring to this phase). Cashtag-only mentions are THEMATIC and never score.

11. Attention metrics (counts, velocity, unique accounts) with window, sample size and sampling note on every value. Missing data stays UNKNOWN.

12. Paid placement, bot-like and coordinated patterns recorded as INFERENCE or HEURISTIC with the rule that fired. Nothing is labelled as fact without direct evidence.

13. Trader registry extends the existing catalyst trader list (handles in `memelab/catalyst/sources.py`). Identity status VERIFIED / NOT_FOUND / UNVERIFIED with date. Research sources, not certified profitable traders.

14. A wallet is linked to a trader only when the trader publicly claims it or chain evidence meets a documented bar; linkage level is recorded. Shared funding is linkage, not proof of control (existing rule).

15. Calls captured with timestamp, account, contract address, stated direction, source URL and an own-words summary (D-010). Phase 06 already extracts and stores the claim structure; what is left is wiring collectors to it and the trader link.

16. Forward returns of calls measured from market data already collected by the lab, with survivorship and selection bias controls written next to every score. Below a minimum sample the score is INSUFFICIENT HISTORY.

17. m19 and `memelab/launch/social.py` read the new metrics. Where data is absent the output is identical to Phase 00 behaviour (regression test proves it).

18. Catalyst attention (`memelab/catalyst/attention.py`) and assessment read the new metrics under the same rule. UNKNOWN never improves a score.

19. Social and trader sections in token, scout and launch reports with FACT / INFERENCE / HEURISTIC / UNKNOWN kept apart. Watchlist alerts for social changes with thresholds documented.

20. Scheduled runs (daily discovery, watchlist refresh) run the social pass without breaking timing; state export includes only public-safe derived tables; SKILL.md updated.

21. Full run on fixtures and one supervised live run; docs (README, ARCHITECTURE, SOURCES, SKILL) match the code; feature branch rebased or merged with current `main`; merge left for Elving to approve.
