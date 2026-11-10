# Maxun adoption decision (Phase 06A)

Decision: EXISTING_TOOL_WINS for the catalyst watch (site type A), with the Maxun cells marked INSUFFICIENT_BAKEOFF_SAMPLE; BLOCKED_EXTERNAL for the release-watch cell (site type B, no credits), which is moot because the GitHub Releases API is the preferred source there. Maxun is NOT_ADOPTED and is not installed, embedded or called by the lab runtime.

Date 2026-10-23. Evidence: `MAXUN_BAKEOFF_PREREG.md`, `MAXUN_BAKEOFF.md`, `bakeoff/p06a_scores.json`, `bakeoff/p06a_maxun/`, `testing/MAXUN_ROBOT_E2E.md`.

## Rule by rule (rules as pre-registered)

| Rule | Outcome |
|---|---|
| 1 ADOPT needs (a) +10 points accuracy or a needed persistent capability, and (b) cost within the approved budget, and (c) Cloud plus thin adapter, and (d) no duplicate ingestion | (a) not testable: no Maxun cell reached 10 sample pages, and the existing route was capped at 1.0 because the oracle came from its own HTML and API, so +10 points was unreachable by construction; Maxun's change monitoring was not run. (b) fails: a daily watch needs about 30 to 60 credits a month at the observed rate, the trial gives 5, and no paid plan is approved. (c) would hold. (d) would hold only through `webcapture`. ADOPT is not supported. |
| 2 EXISTING_TOOL_WINS if an existing tool matches or beats Maxun at lower cost | Plain HTTP and Crawl4AI covered 10 of 10 pages on both site types with every field right, at no credit cost. Maxun's accuracy cannot be claimed (rule 5), so "beats" rests on coverage, cost and setup, not on measured quality. Holds for site type A. |
| 3 NO_GO if Maxun cannot be bounded safely | Not triggered. The docs say URL filters are not fully enforced, but all 5 returned pages were inside /news, and the lab-side allowlist refused the /news index anyway. |
| 4 BLOCKED_EXTERNAL if no Maxun run can complete | One run completed (aborted at the credit limit) and returned correct metadata. Applies only to the type B cell, refused with 403 for lack of credits. |
| 5 Ties go to the existing tool; fewer than 10 usable sample pages means no accuracy claim | Applied to both Maxun cells. |

Precedence was not set in the pre-registration. Used here: a safety failure (3) would override everything; then cost and policy limits (1b, contract C.3) decide before accuracy; an untestable accuracy rule never produces ADOPT. Future pre-registrations should state this order and give the challenger the same URL list as the incumbents.

## Measured trade-offs

| | Existing route (plain HTTP or Crawl4AI, plus GitHub API for releases) | Maxun Cloud |
|---|---|---|
| Coverage of the sample | 10/10 on both site types | 0/10 on A (budget spent on other pages), not run on B |
| Field accuracy | 1.0 (oracle is not independent of it) | 1.0 on the 5 pages it returned (not a sample claim) |
| Cost | no credits | all 5 trial credits for 5 pages; 0 left |
| Setup | none (plain HTTP); local Python env (Crawl4AI) | account, key, polling client |
| Change detection | claim fingerprint per origin (title, machine date, tag); body edits not detected | monitoring diff exists; untested |
| Failure reporting | HTTP status per page | `aborted` with `isPartial: false`; 403 where docs say 402 |
| License | lab code | AGPL-3.0-or-later source; Cloud use through HTTPS adds no AGPL obligation to the lab (D-BT-015) |

Version and environment: Maxun Cloud API v1 (October 2026 docs), account plan TRIAL; source reviewed at `getmaxun/maxun` 80ba045 (0.0.48). Domains touched: solana.com only. No webhooks, no schedules, no monitoring alerts.

## Independent reviewer objections (summary) and responses

1. Unfair task: Maxun had to discover pages with a budget below the sample size, while others got URLs. Accepted; stated in the results. A fair rerun needs Maxun scrape robots on the same 10 URLs with markdown and HTML, plus two runs for a rescan and diff: about 22 credits or more, which needs Elving's approval and a paid plan.
2. Oracle not independent; ADOPT unreachable by accuracy. Accepted; stated above and in the oracle file. Labels unchanged.
3. Firecrawl misses are an extractor artifact, and its records cannot be re-audited. Accepted; the time-zone explanation was wrong and is corrected. Raw Firecrawl outputs were not kept.
4. Change detection overstated. Accepted; the results now say dedup and replay were proven, live change detection was not, and body edits are not covered.
5. Cost rests on one reading. Accepted; restated as a range for an index-plus-new-items design; no dollar figure without a price sheet.
6. No decision recorded and rules ambiguous. Resolved by this file and the precedence note.
7. Missing metrics. Marked as not measured.
8. Provenance gaps (sitemap Maxun used, 402 citation, times). The 402 excerpt is saved (`raw/p06a_maxun_cloud_api_excerpt.md`); times corrected; the sitemap Maxun read is unknown.

The reviewer's own verdict was EXISTING_TOOL_WINS, scoped to cost, coverage and policy, with type B BLOCKED_EXTERNAL and moot. This file adopts that scope.

## Rollout plan and approvals

- Now: no Maxun rollout. The catalyst watch uses the existing collectors through `memelab/backtest/sources/webcapture.py` (allowlists, page caps, claim fingerprints, UNKNOWN_AS_OF for late captures). Release watch uses the GitHub Releases API when wired.
- If Elving wants a fair Maxun retest later: approve a paid credit budget (about 22+ credits), then run scrape robots on a fixed URL list, two runs each, with markdown and HTML, and compare monitoring diffs with the lab's fingerprints on a page known to change. Schedules stay off until separately approved.
- The one evaluation robot stays idle with no schedule; its removal command is in `data/MAXUN_ROBOT_REGISTRY.md`.
