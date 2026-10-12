# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md), [IDENTITY_05.md](IDENTITY_05.md), [CLAIMS_06.md](CLAIMS_06.md), [NARRATIVES_07.md](NARRATIVES_07.md), [REGISTRY_08.md](REGISTRY_08.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 08 (Prompt 08: source and trader registry), 2026-10-12. Prompt 08 took the Phase 08 slot; the old proposed Phase 08 (YouTube RSS and token-listed links collector) is now carry-over C-8 (D-047).
- Model status: unchanged, none configured (D-036). Phase 08 makes no model call.
- Data status: no live list or provider data exists. Every proof ran on invented, labelled fixtures. The tracked database holds no registry rows, and fixture imports into it are refused.
- Next phase: 09 as proposed in ROADMAP.md, or carry-overs C-5/C-6/C-7/C-8, unless Elving supplies Prompt 09.
- Active branch: `feature/social-intelligence`.
- Phase 08 started from `a689d1b` ("social-intel phase 07: handoff records the push"). Baseline `python -m pytest tests -q`: one known clock failure, the rest passing.
- Commit and push: see the end of this file.

## What Phase 08 added

- `memelab/social/registry.py`: entities, links, attribution ladder, mirror to `social_wallet_attributions`, review (approve, reject, update, account status), categories, listing claim review, search, show, report, catalyst list import, discovery from narrative snapshots. Version `registry-v1`.
- `memelab/social/registry_import.py`: strict JSON or CSV import with per-row rejects and whole-file refusals, dry run, idempotent by file hash.
- `memelab/social/registry_cli.py` and `cli.py`: `python -m memelab social registry <action>` (18 actions).
- `memelab/social/schema.py`: migration 8 (nine `social_registry_*` tables).
- `memelab/social/content_guard.py`: allow entry for the one invented blocked-key row, plus SQLite checks for fixture labels and superlative text in registry tables.
- Tests: `tests/test_social_registry.py` (51). Fixtures: `tests/fixtures/social/registry/` (invented).
- Docs: `REGISTRY_08.md`, DECISIONS D-047 to D-055, ROADMAP (08 DONE, C-8 added), SOURCE_COVERAGE (registry row), SCHEMA_01 (migrations line).

## Gate, item by item

- Records usable by later stages: `registry.search`, `show`, `wallets_of`, `owners_of`, `wallet_attribution(as_of=)`, `identity_cluster`; test `test_a_later_stage_can_read_sources_wallets_and_attribution`. Each record has identities, provenance, confidence, time span, categories and watch status.
- No "best trader" assertions: superlative text refused in all free-text fields, no rank or score columns, search ordered by label (`test_no_best_trader_assertions_anywhere`, `test_duplicate_rankings_and_duplicate_identifiers_are_flagged_not_resolved`).
- Discovery from accessible sources only: file import, repo research list, narrative snapshots. No network code (`test_registry_modules_make_no_network_calls`). No live list exists, so none was used.
- Prompt test list: identical screen names, handle rename, suspension, self claim versus corroborated ownership, stale leaderboard, duplicate rankings, missing platform link, sources without wallets, each a named test (see the test map in REGISTRY_08.md).
- Fixtures labelled, no fabricated rankings or seed accounts: every fixture entity carries a label, cannot be watched, tracked-database imports refused.
- CLI demo of candidate, evidence, reviewed record: REGISTRY_08.md sample, and `test_cli_candidate_to_evidence_to_reviewed_record`.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change: exit 1, `1 failed, 330 passed`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched).
- `python -m pytest tests/test_social_registry.py -q` -> `51 passed`.
- `python -m memelab social guard` exit 0 (0 violations).
- The EVM test still writes `data/reports/<stamp>_BRETT_0x532f.md`; deleted by hand after the run (C-1).

## Things the next phase should know

- Nothing calls `registry.discover_from_narratives` or imports on a schedule. Phase 20 wires scheduling.
- `import-catalyst` and fixture imports refuse the tracked database by design. Use a temp database or a private one.
- A reviewer name is required for every review action and is logged in `social_registry_reviews`.
- The superlative filter is a regex and will miss novel phrasing.
- Handle length limits are enforced per platform (X handles are 15 characters at most); a fixture handle that is too long is rejected as INVALID_HANDLE.
- Outcome tracking and trader scoring are not built (Phase 16 in the proposal). The registry stores no performance judgment.

## Blockers and open decisions

- Push: the session's own `git push` gets 403. Working route: Elving's GitHub connection in Composio, Git Data API, fast-forward of the feature branch ref, no force (D-001).
- No permitted live trader list or export has been supplied; live registry status is UNAVAILABLE.
- D-025, D-028, D-023 and D-036 remain open.
- Phase prompts 09 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 330 passed` and `python -m memelab social guard` exit 0.

## Commit and push

Phase 08 commit adcd2f51f57b05215e634e1c3fab0cbf098415f8 (tree dd0f0842bc7902595cef12a1eb765748e826cafe, parent a689d1be55eee1d50c52f5bec7f15fca7fd5ca83) is on feature/social-intelligence.

Route: the session's own git push returns 403, so the push went through Elving's GitHub connection in Composio using the Git Data API (20 blobs, one tree, one commit, fast-forward ref update, no force). Every blob sha and the tree sha matched the locally built values. This handoff note was filled in by a small follow-up commit on the same route.
