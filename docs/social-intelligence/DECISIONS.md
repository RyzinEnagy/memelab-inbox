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
