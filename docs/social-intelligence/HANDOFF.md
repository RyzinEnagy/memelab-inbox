# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). This phase: [SOURCES_19.md](SOURCES_19.md). Release record: [RELEASE_18.md](RELEASE_18.md). Operator docs: [README.md](README.md), [OPERATIONS.md](OPERATIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md). Earlier phase notes are linked from ROADMAP.md.

## Position

- Current phase completed: 19 (optional Prompt 19: Reddit and Farcaster sources), 2026-10-12. Prompt 19 took the Phase 19 slot; the old Phase 19 (report sections and watchlist alerts) is carry-over C-19 and Phase 20 now depends on it (D-125).
- Precondition: Elving confirmed Phase 18 was accepted; pull request #1 was merged into `main` as `f084b60`.
- Prompt 19 says stop after this phase. No further phase is started.
- Active branch: `feature/social-intelligence`. Phase 19 started by fast-forwarding the branch from `629d402` to `f084b60` (the merge commit on `main`; the only file difference was `data/state/latest.json` from the scheduled runs, not edited by this phase).
- Baseline before any change: `python -m pytest tests -q --deselect tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` gave `651 passed, 1 deselected`; the deselected test is the known clock failure C-1. Matches the Phase 18 handoff (`1 failed, 651 passed`).
- No migration. Public schema stays at 12. No change under `inbox/`, `state/` or `data/`.
- Live status: neither new adapter is operational and no live call was made (D-131).

## What Phase 19 added

- `memelab/social/reddit_api.py`: Reddit Data API adapter. Approved communities only; submissions (`/new`), comments (`/comments`), recheck (`/api/info`); canonical fullnames, parent and thread ids, edit versions, deleted and removed states, account deletion, cross-post parent id and author id as a REPOST reference; rate limits from X-Ratelimit headers and 429; approval flag, non-commercial and credential gates before any request; `purge_deleted` (D-128); `health`.
- `memelab/social/farcaster_hub.py`: Snapchain node HTTP adapter. Fids (`castsByFid`), channels (`castsByParent`), recasts (`reactionsByCast`), recheck (`castById`), username only (`userDataByFid` type 6); replies, quotes and recasts as references; self-hosted or metered hub with key, consent and cost cap; `health`.
- `memelab/social/api_common.py`: fixture transport, request guard with `social_api_spend` rows, cursor helpers, `TextSink` and `extract_after_ingest` (text to claim extraction in memory only, D-130).
- `memelab/social/sources_cli.py`: `social reddit-health`, `reddit-ingest`, `reddit-purge`, `fc-health`, `fc-ingest`, `social sources`. Registered in `memelab/social/cli.py`.
- `reddit` added to `PLATFORMS` in `ingest.py` and `registry.py`.
- Fixtures: `tests/fixtures/social/reddit_api/` and `tests/fixtures/social/farcaster_hub/` (invented). Tests: `tests/test_social_reddit.py` (23), `tests/test_social_farcaster.py` (14).
- `tools/release_e2e.py`: 10 new stages (19): both fixture flows source to brief, Reddit second run with purge, no-credential and not-configured refusals, `social sources`; Reddit and Farcaster variables added to the removed credential list. `tools/release_audit.py`: Reddit hosts added to the credentialed-host list.
- Docs: SOURCES_19.md (contract read, field mapping, gates, deletion purge, proof, cost and health, setup steps, first-live-run checks, gaps), examples `reddit_api.example.json` and `farcaster_hub.example.json` (both off), DECISIONS D-125 to D-131, ROADMAP (19 DONE, C-19 added, 20 depends on C-19), SOURCE_COVERAGE (two rows), README, OPERATIONS, ARCHITECTURE.

## Gate, item by item (Prompt 19)

- Two distinct adapters, neither a stub: PASS (both fully built and tested; neither blocked from being built, both blocked from going live).
- Reddit: selected approved communities, submissions and comments, canonical ids, parent relations, edited and deleted states, rate limits, cross-post provenance and independence: PASS on fixtures (`test_main_fixture_submissions_comments_crosspost_deleted_edited`, `test_crosspost_is_amplification_not_an_independent_thread`, `test_second_run_cursor_recheck_and_purge`, rate-limit tests).
- Farcaster: casts, channels, recasts, replies, stable ids, identity and provenance: PASS on fixtures (`test_main_fixture_casts_replies_quotes_recasts`, `test_recasts_are_amplification_quotes_and_replies_are_own_words`).
- Phase 02 schema and data minimization, no private messages, no terms bypass: PASS (inbound/3 through `ingest()`; text, titles, bios and slugs never stored, tests scan every social table; no DM endpoint exists; Reddit gated on approval, D-127).
- Adapter fixtures and tests: PASS (37 tests).
- One source to storage to claim to narrative report flow per functioning adapter: PASS on fixtures (CLI tests and e2e stages 19: Reddit 3 claims, 1 cluster with 2 independent sources, brief HIGH; Farcaster 2 claims, 1 cluster with 2 independent sources). No adapter functions live yet, so no live flow.
- Connector cost and health status, precise setup: PASS (`reddit-health`, `fc-health`, `social sources`; SOURCES_19.md "Setup").
- Permission unavailable marked blocked without claiming operation: PASS (Reddit BLOCKED on approval and credentials; Farcaster BLOCKED on node or hub; D-131; health reports `none` live evidence).

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change (commit `9927e45`, run before the handoff commit): exit 1, `1 failed, 688 passed in 147.41s`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1).
- `python -m pytest tests/test_social_reddit.py tests/test_social_farcaster.py tests/test_release_tools.py -q`: `45 passed`.
- `python tools/release_e2e.py --out e2e.md` on `9927e45`: exit 0, `Result: PASS. Stages with the expected exit code: 55 of 55. Network attempts: 0. Tracked files changed in the clone: 0. Tracked database byte-identical: yes.`
- `python tools/release_audit.py --history`: exit 0, `Needs action: no.`
- `python -m memelab social guard`: exit 0, `violations: []`.
- `python -m pyflakes` on the four new modules and two new test files: no messages.
- The EVM test still writes `data/reports/<stamp>_BRETT_*.md`; deleted by hand after each run (C-1). `git status` clean before each commit.

## Things the next session should know

- Reddit's Listing field shapes were not re-read from Reddit's API reference; the first live run must confirm them (SOURCES_19.md "First live run").
- D-128 is partly PROPOSED: derived claim rows of deleted Reddit posts and narrative snapshot counts are kept. Elving decides whether to drop them.
- `--extract` exists only on the two new ingest commands; X and Telegram extraction still needs `--text-file`.
- Neither adapter is in any scheduled run (Phase 20).

## Helius key

Unchanged from Phase 18: never in the repo; read through `memelab/secrets.py` (`HELIUS_API_KEY`, else gitignored `data/config.json`); `python -m memelab.secrets status` prints set or missing only. It was pasted into a chat once; rotate it if that chat is shared.

## Blockers and open decisions

- Reddit live: Reddit's written approval (Responsible Builder Policy) and app credentials (`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`), Elving's.
- Farcaster live: a self-hosted Snapchain node, or a hosted hub with a key and a cost decision, Elving's.
- D-128 (derived rows of deleted Reddit posts), D-025, D-028, D-023 and D-036 remain open.
- C-1 keeps the full suite from being fully green.
- Push: the session's own `git push` is refused by the git proxy; the working route is Elving's GitHub connection in Composio with the Git Data API (blobs, trees, commits, fast-forward of the feature branch ref, no force, D-001).

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q && python tools/release_e2e.py --out e2e.md
```

Expect `1 failed, 688 passed` and `Result: PASS` with 55 of 55 stages.

## Commit and push

Local commits on `feature/social-intelligence`: `9927e45` (code, tests, fixtures, docs, tree `10c3d42`) and `13718df` (handoff, tree `f49a8ea`), on top of `f084b60`.

Pushed 2026-10-13 through Composio and the GitHub Git Data API: the diff was rebuilt in Composio's workbench from the files at `f084b60` plus the patch and the fixture generator; all 27 blob shas were checked equal to the local blobs before upload; both trees came back equal to the local trees (`10c3d42`, `f49a8ea`). Remote commits: `76eac304a17e8d665f0d85774b1875212a536dbe` (code and docs) and `6a6762f0d7ce496c45628fb8a8a3add32f99944d` (handoff), then this record on top. Branch ref fast-forwarded from `629d402` (no force, D-001). `main` untouched (`f084b60`).

Pull request #1 is already merged, so these commits are not in any open pull request. Opening a new one (feature into `main`) is Elving's call; merging changes nothing the scheduled runs load except new modules and commands, but it is still his decision.

Phase 19 is complete. Stop here; no further phase is started.
