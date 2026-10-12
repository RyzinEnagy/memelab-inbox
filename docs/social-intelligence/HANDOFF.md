# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md), [IDENTITY_05.md](IDENTITY_05.md), [CLAIMS_06.md](CLAIMS_06.md), [NARRATIVES_07.md](NARRATIVES_07.md), [REGISTRY_08.md](REGISTRY_08.md), [WALLETS_09.md](WALLETS_09.md), [PERFORMANCE_10.md](PERFORMANCE_10.md), [ALPHA_11.md](ALPHA_11.md), [CHRONOLOGY_12.md](CHRONOLOGY_12.md), [INTEGRATION_13.md](INTEGRATION_13.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 13 (Prompt 13: integrate social signals into the existing scout and catalyst workflow), 2026-10-12. Prompt 13 took the Phase 13 slot; the old proposed Phase 13 (trader identity verification) is now carry-over C-13 (D-085).
- Model status: unchanged, none configured (D-036). Phase 13 makes no model call.
- Data status: no live post, wallet fetch or candle source was used. The tracked database has no social tables, so a real `scout --social` today prints an explicit no-op. Every enriched result in this phase ran on invented, labelled fixtures.
- Next phase: 14 as proposed in ROADMAP.md, or a carry-over, unless Elving supplies Prompt 14. Not started.
- Active branch: `feature/social-intelligence`.
- Phase 13 started from `4c8d69f` ("social-intel phase 12: record commit and push route in handoff"), the commit on the remote branch. No drift. Baseline `python -m pytest tests -q --deselect tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` at the start: exit 0, `505 passed, 1 deselected`, matching the Phase 12 handoff's `1 failed, 505 passed`.
- No migration in this phase. Schema stays at 12 (D-086).

## What Phase 13 added

- `memelab/social/research_core.py`: pure engine. Policy (`make_policy`, schema `memelab.social.research.policy/1`, refusals), three lanes (`attention_lane`, `structure_lane`, `entry_lane`), research states, earlier-rejection review, finding dedupe, `build` (deterministic, `result_sha256`), `render` (markdown section).
- `memelab/social/research_store.py`: read only. `load_policy` (defaults, `data/config.json` key `social_research`, policy file), `findings_from_db` (newest Phase 07 snapshot with cutoff at or before as_of, contract clusters and ticker-only mentions, Phase 12 `current_flags`), `prior_rejections`, `evaluated_from_scout`, `evaluated_from_catalyst`, `section` (never raises; unavailable store is a no-op).
- `memelab/social/research_cli.py` and `cli.py`: `python -m memelab social research <policy|show|demo>`.
- `memelab/cli.py`: scout list building moved unchanged into `scout_lists`; `scout --social`, `--social-policy`, `--social-include-fixtures`, `--report-dir`. With none of them the scout does not open the social store.
- `memelab/report.py`: `render_scout_report(..., social=None)` appends the section; `None` returns the old text.
- `memelab/catalyst/cli.py`: `catalyst report --social`, `--social-policy`.
- Tests: `tests/test_social_research.py` (23). Fixture: `tests/fixtures/social/research/scout_before_after.json`, built by `make_research.py` (a test checks the file matches the script). Invented tokens, sources and counts.
- Docs: `INTEGRATION_13.md` (lanes, rules, policy, no-op behaviour, commands, the fixture before/after, test map, limits), DECISIONS D-085 to D-090, ROADMAP (13 DONE, C-13 added, 14 and 15 depend on C-13, 19 notes the scout section), SOURCE_COVERAGE.

## Gate, item by item

- Integrated path genuinely executes: `test_scout_command_off_is_unchanged_and_on_attaches_from_the_real_snapshot` runs the real `cmd_scout` against a temp database holding a real Phase 07 snapshot built from invented posts (only `analyze_token` and the inbox loader return fixture results); the report gains the section with the CORROBORATED candidate, its originators and the unresolved ticker. `test_catalyst_report_social_section_is_opt_in` does the same for `catalyst report`. Demo: `python -m memelab social research demo --fixture tests/fixtures/social/research/scout_before_after.json` exit 0, "Report body unchanged by the social layer: yes."
- Old pipeline still works: scout on the repo inbox files (`--mints 98kfF7rm.. ondohH8V.. 7KEPApdb.. --results disc01 s2_01 deep01a deep02 deep03 deep04 forensics01 --stage1 disc01`) from 4c8d69f and from this branch, each on its own copy of the tracked database in /tmp: both exit 0; stdout and every file under `data/reports` identical except the absolute checkout path in the "Report:" line; theses 36, rejections 21 and the watchlist row identical. In tests: `test_no_social_data_is_an_explicit_no_op_and_the_report_is_unchanged`, `test_before_after_report_enriches_one_candidate_and_leaves_rejections_alone`.
- Explicit no-op when the source is unavailable: the same real scout with `--social --report-dir /tmp/...` exit 0, body identical, last section line "No-op: social source unavailable: social tables not present in this database (social schema not migrated)". Tests: `test_no_op_when_the_social_store_is_missing_empty_or_unopenable` (missing tables, empty store, store that cannot be opened).
- Separation and no override: `test_fatal_flag_override_high_hype_never_clears_a_fatal_flag`, `test_social_top_pick_with_no_liquidity_stays_out_of_tradable_rankings`, `test_weights_order_the_section_only`, `test_no_trade_or_watchlist_side_effects`, `test_policy_is_opt_in_versioned_and_refuses_anything_that_reaches_scoring_or_execution`.
- Prompt test list, each a named test: see INTEGRATION_13.md "Test list".

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change: exit 1, `1 failed, 528 passed`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched).
- `python -m pytest tests/test_social_research.py -q` -> `23 passed`.
- `python -m memelab social guard` exit 0 (0 violations, 306 files scanned).
- The EVM test still writes `data/reports/<stamp>_BRETT_*.md`; deleted by hand after each run (C-1).

## Things the next phase should know

- To see real candidates, the tracked database needs the social schema (`schema.migrate`) and live narrative snapshots. Until then `scout --social` is a no-op by design.
- `scout_lists` is the one place the scout builds its lists; reuse it rather than copying the logic.
- The section reads the newest narrative snapshot with cutoff at or before the scout's as_of. Run `social narrative-snapshot` before the scout if the section should reflect the latest posts.
- Fixture snapshots and flags are ignored unless `include_fixtures` is set (policy or `--social-include-fixtures`).
- Nothing is scheduled. The daily discovery and watchlist-refresh tasks do not pass `--social` (Phase 20).

## Helius key

The key is not in the repo and must never be committed. Code reads it through `memelab/secrets.py`, in this order:

1. The `HELIUS_API_KEY` environment variable. Use this for a scheduled run, CI or a cloud session (set it as a secret there).
2. `helius_api_key` in `data/config.json`. That file is gitignored. On a machine, create it with `python -m memelab.secrets set` (prompts without echo).

Check with `python -m memelab.secrets status` (prints "set" or "missing" and the source, never the value). The social research policy reads only the `social_research` key of the same file and never prints other keys (`test_policy_is_opt_in_versioned_and_refuses_anything_that_reaches_scoring_or_execution`).

A new session that needs the key should ask Elving to supply it (it is not stored in memory or project docs). The key was pasted into a chat once; rotate it if that chat is shared.

## Blockers and open decisions

- Push: the session's own `git push` is not used. Working route: Elving's GitHub connection in Composio, Git Data API (blobs, trees, commits, fast-forward of the feature branch ref, no force, D-001).
- No live posts, wallet fetches or candle provider in session; the tracked database has no social schema.
- D-025, D-028, D-023 and D-036 remain open.
- Phase prompts 14 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 528 passed` and `python -m memelab social guard` exit 0.

## Commit and push

Phase 13 code commit on `feature/social-intelligence`: `a489825` (tree 3cc35f90f3c18af31394f648500c0ae3342abbd1, parent 4c8d69f34fef5f5b4442010cd82e0e26f43c6a07; local hash cb5d70e). This handoff correction is the commit on top of it.

The sandbox `git push` is not used. The push went through Composio and the GitHub Git Data API: the diff against 4c8d69f went over as a checksummed xz bundle in eight chunks (each chunk and the reassembled patch checked by sha256), was applied to the base files fetched at 4c8d69f, every blob sha was checked against the local file before and after upload, the tree sha was compared with the local tree before the commit was created, and the branch ref was moved forward once, without force. `main` was not touched.

Phase 14 is not started.
