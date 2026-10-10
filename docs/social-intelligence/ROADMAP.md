# Social & Trader Intelligence: roadmap

Contract: [EXECUTION.md](EXECUTION.md). Choices: [DECISIONS.md](DECISIONS.md). Current position: [HANDOFF.md](HANDOFF.md). Baseline: [AUDIT_00.md](AUDIT_00.md).

Status values: DONE, NEXT, PLANNED, BLOCKED.

Only Phase 00 came with a written phase prompt. Phases 01 to 21 below are a proposed sequence built from the Phase 00 audit. When the prompt for a phase is supplied, that prompt replaces the entry here and the change is logged in DECISIONS.md.

Every gate also includes the standing gate: full test suite run and recorded, no new failures, no stray files, no raw third-party social content in the public repo, HANDOFF.md rewritten, commit made.

| Phase | Title | Depends on | Status |
|---|---|---|---|
| 00 | Repo audit and execution contract | none | DONE |
| 01 | Baseline hygiene: test isolation and clock | 00 | NEXT |
| 02 | Content policy and public/private storage split | 00 | PLANNED |
| 03 | Social schema and migrations | 02 | PLANNED |
| 04 | Observation contract and manual capture CLI | 03 | PLANNED |
| 05 | Source registry for social and trader sources | 02, 03 | PLANNED |
| 06 | Collector: X public profile pages | 04, 05 | PLANNED |
| 07 | Collector: Telegram public channel previews | 04, 05 | PLANNED |
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

## Phase gates

00. Baseline test results recorded; architecture and source-access constraints mapped; working branch established; EXECUTION, ROADMAP, DECISIONS, HANDOFF exist, are accurate and linked; no existing functionality changed.

01. `test_catalyst.py::test_dedup_corroboration_resurface_denial` passes on any date (fixed clock in the test, not in production code unless a real bug is found); the EVM test no longer leaves `data/reports/*_BRETT_*.md` behind; pytest is documented as the test dependency. Full suite green. No behaviour change outside tests unless the root cause is a production bug, in which case the fix and its proof are recorded.

02. Written content policy approved by Elving: which social content classes may be stored, where (public repo, private local store, nowhere) and for how long. A gitignored private store path exists. A guard (test or check script) fails if a tracked file contains a raw post text field or other blocked class. Existing `social_snapshots` rows reviewed (99 rows at Phase 00, all numeric Jupiter holder-change metrics).

03. New tables created through `db.py` with `CREATE TABLE IF NOT EXISTS`, idempotent on an existing database; append-only observation tables; every row carries source, observed_at, retrieved_at, access mode and evidence status. Existing `social_snapshots` keeps working. Migration tested on a copy of the current DB.

04. One normalized observation format for every social source. `social-note` either extended or wrapped without breaking its current arguments. Manual captures are labelled as manual. Tests cover validation and rejection of malformed input.

05. Social and trader sources registered with access mode (fetch, navigate, manual, blocked), tier, terms constraint and coverage gap, reusing the catalyst source registry pattern. Blocked sources stay disabled with the reason recorded. No collector code yet.

06. X public profile reads (identity fields and public counts only) through the existing collection route (`memelab fetch` first, Chrome bridge fallback). No logged-in scraping unless D-006 is changed by Elving. Fixtures recorded from real responses; parser tests pass offline.

07. Telegram `t.me/s/<channel>` previews parsed to channel-level metrics. Same fixture and policy rules as 06.

08. Additional readable sources wired in the same way, each with fixtures and coverage notes. Sources that fail from both routes are recorded as gaps, not worked around.

09. Accounts linked to projects and tokens only through evidence (official link on the token profile, link from the account to the contract address). Impersonation and name collisions flagged. Ticker-only matches never create a link.

10. Mentions counted only when they contain a contract address or a verified official link. Cashtag-only mentions are THEMATIC and never score.

11. Attention metrics (counts, velocity, unique accounts) with window, sample size and sampling note on every value. Missing data stays UNKNOWN.

12. Paid placement, bot-like and coordinated patterns recorded as INFERENCE or HEURISTIC with the rule that fired. Nothing is labelled as fact without direct evidence.

13. Trader registry extends the existing catalyst trader list (handles in `memelab/catalyst/sources.py`). Identity status VERIFIED / NOT_FOUND / UNVERIFIED with date. Research sources, not certified profitable traders.

14. A wallet is linked to a trader only when the trader publicly claims it or chain evidence meets a documented bar; linkage level is recorded. Shared funding is linkage, not proof of control (existing rule).

15. Calls captured with timestamp, account, contract address, stated direction, and source URL. Raw text follows the D-004 policy.

16. Forward returns of calls measured from market data already collected by the lab, with survivorship and selection bias controls written next to every score. Below a minimum sample the score is INSUFFICIENT HISTORY.

17. m19 and `memelab/launch/social.py` read the new metrics. Where data is absent the output is identical to Phase 00 behaviour (regression test proves it).

18. Catalyst attention (`memelab/catalyst/attention.py`) and assessment read the new metrics under the same rule. UNKNOWN never improves a score.

19. Social and trader sections in token, scout and launch reports with FACT / INFERENCE / HEURISTIC / UNKNOWN kept apart. Watchlist alerts for social changes with thresholds documented.

20. Scheduled runs (daily discovery, watchlist refresh) run the social pass without breaking timing; state export includes only public-safe derived tables; SKILL.md updated.

21. Full run on fixtures and one supervised live run; docs (README, ARCHITECTURE, SOURCES, SKILL) match the code; feature branch rebased or merged with current `main`; merge left for Elving to approve.
