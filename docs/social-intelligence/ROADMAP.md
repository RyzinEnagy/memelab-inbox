# Social & Trader Intelligence: roadmap

Contract: [EXECUTION.md](EXECUTION.md). Choices: [DECISIONS.md](DECISIONS.md). Current position: [HANDOFF.md](HANDOFF.md). Baseline: [AUDIT_00.md](AUDIT_00.md).

Status values: DONE, NEXT, PLANNED, BLOCKED.

Phases 00 and 01 came with written phase prompts. Phases 02 to 21 below are a proposed sequence built from the Phase 00 audit. When the prompt for a phase is supplied, that prompt replaces the entry here and the change is logged in DECISIONS.md (Phase 01: D-011).

Status values also include SUPERSEDED (folded into another phase).

Every gate also includes the standing gate: full test suite run and recorded, no new failures, no stray files, no raw third-party social content in the public repo, HANDOFF.md rewritten, commit made.

| Phase | Title | Depends on | Status |
|---|---|---|---|
| 00 | Repo audit and execution contract | none | DONE |
| 01 | Durable schemas, evidence provenance and migration safety (Prompt 01) | 00 | DONE |
| 02 | Content policy and public/private storage split | 01 | NEXT |
| 03 | Social schema and migrations | 02 | SUPERSEDED by 01 |
| 04 | Observation contract and manual capture CLI | 03 | PLANNED |
| 05 | Source registry for social and trader sources | 02, 03 | PLANNED |
| 06 | Collector: X via signed-in Chrome | 04, 05 | PLANNED |
| 07 | Collector: Telegram public channels | 04, 05 | PLANNED |
| 08 | Collector: other readable sources (YouTube RSS, token-listed links) | 04, 05 | PLANNED |
| 09 | Entity resolution: accounts, projects, tokens by address | 06 | PLANNED |
| 10 | Mention extraction by contract address | 09 | PLANNED |
| 11 | Attention metrics with sampling notes | 10 | PLANNED |
| 12 | Paid, bot and coordination signals | 11 | PLANNED |
| 13 | Trader registry and identity verification | 05, 06 | PLANNED |
| 14 | Trader claimed-wallet linking (evidence levels) | 13 | PLANNED |
| 15 | Trader call capture | 10, 13 | PLANNED |
| 16 | Call outcome tracking and trader scoring | 15 | PLANNED |
| 17 | Integration: m19 attention and launch social | 11, 12 | PLANNED |
| 18 | Integration: catalyst attention and assessment | 11, 12 | PLANNED |
| 19 | Reporting sections and watchlist alerts | 16, 17, 18 | PLANNED |
| 20 | Scheduled-run integration and state export rules | 19 | PLANNED |
| 21 | End-to-end validation, docs, merge request | 20 | PLANNED |
| C-1 | Carry-over: test isolation and clock (old Phase 01) | 00 | PLANNED, unscheduled |

## Phase gates

00. Baseline test results recorded; architecture and source-access constraints mapped; working branch established; EXECUTION, ROADMAP, DECISIONS, HANDOFF exist, are accurate and linked; no existing functionality changed.

01. (Prompt 01, DONE 2026-10-10) Exact schema and migrations documented in SCHEMA_01.md; tests prove insert/read/update/idempotency, empty-DB init, migration from a copy of the tracked DB, repeated ingestion, missing timestamps, duplicate provider ids, conflicting claims, rollback and recovery, and that watchlist, theses, entries, rejections and snapshot tables are unchanged; a fixture round trip runs through real SQLite. Full suite: only the known pre-existing clock failure remains. Performance and outcome tables are left to their own phases.

C-1. (old Phase 01 gate, carried over) `test_catalyst.py::test_dedup_corroboration_resurface_denial` passes on any date (fixed clock in the test); the EVM test no longer leaves `data/reports/*_BRETT_*.md` behind; pytest documented as the test dependency. Full suite green.

02. Content policy from D-010 written into code (Phase 01 already added the storage defaults: text hashed not stored, own-words summary guard, numeric-only metrics, gitignored private store with retention; Phase 02 adds the repo-wide guard): allowed fields (derived data plus short own-words summaries of public posts) and blocked classes (bulk verbatim text, media, DMs, private-space content). A gitignored private store path exists for exact wording needed as evidence. A guard (test or check script) fails if a tracked file contains a raw post text field or other blocked class. Existing `social_snapshots` rows reviewed (99 rows at Phase 00, all numeric Jupiter holder-change metrics).

03. SUPERSEDED by Phase 01 (D-011).

04. One normalized observation format for every social source. `social-note` either extended or wrapped without breaking its current arguments. Manual captures are labelled as manual. Tests cover validation and rejection of malformed input.

05. Social and trader sources registered with access mode (fetch, navigate, manual, blocked), tier, terms constraint and coverage gap, reusing the catalyst source registry pattern. Blocked sources stay disabled with the reason recorded. No collector code yet.

06. X reads through Elving's signed-in Chrome (D-009): profiles, public timelines and search results, read only, human-paced, stopping on any challenge. Output is derived fields plus own-words summaries (D-010). Fixtures recorded from real pages; parser tests pass offline.

07. Telegram public channels (`t.me/s/<channel>` previews, or Telegram Web while signed in) parsed to channel-level metrics and summaries. Same fixture and policy rules as 06; no private groups.

08. Additional readable sources wired in the same way, each with fixtures and coverage notes. Sources that fail from both routes are recorded as gaps, not worked around.

09. Accounts linked to projects and tokens only through evidence (official link on the token profile, link from the account to the contract address). Impersonation and name collisions flagged. Ticker-only matches never create a link.

10. Mentions counted only when they contain a contract address or a verified official link. Cashtag-only mentions are THEMATIC and never score.

11. Attention metrics (counts, velocity, unique accounts) with window, sample size and sampling note on every value. Missing data stays UNKNOWN.

12. Paid placement, bot-like and coordinated patterns recorded as INFERENCE or HEURISTIC with the rule that fired. Nothing is labelled as fact without direct evidence.

13. Trader registry extends the existing catalyst trader list (handles in `memelab/catalyst/sources.py`). Identity status VERIFIED / NOT_FOUND / UNVERIFIED with date. Research sources, not certified profitable traders.

14. A wallet is linked to a trader only when the trader publicly claims it or chain evidence meets a documented bar; linkage level is recorded. Shared funding is linkage, not proof of control (existing rule).

15. Calls captured with timestamp, account, contract address, stated direction, source URL and an own-words summary (D-010).

16. Forward returns of calls measured from market data already collected by the lab, with survivorship and selection bias controls written next to every score. Below a minimum sample the score is INSUFFICIENT HISTORY.

17. m19 and `memelab/launch/social.py` read the new metrics. Where data is absent the output is identical to Phase 00 behaviour (regression test proves it).

18. Catalyst attention (`memelab/catalyst/attention.py`) and assessment read the new metrics under the same rule. UNKNOWN never improves a score.

19. Social and trader sections in token, scout and launch reports with FACT / INFERENCE / HEURISTIC / UNKNOWN kept apart. Watchlist alerts for social changes with thresholds documented.

20. Scheduled runs (daily discovery, watchlist refresh) run the social pass without breaking timing; state export includes only public-safe derived tables; SKILL.md updated.

21. Full run on fixtures and one supervised live run; docs (README, ARCHITECTURE, SOURCES, SKILL) match the code; feature branch rebased or merged with current `main`; merge left for Elving to approve.
