# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md), [IDENTITY_05.md](IDENTITY_05.md), [CLAIMS_06.md](CLAIMS_06.md), [NARRATIVES_07.md](NARRATIVES_07.md), [REGISTRY_08.md](REGISTRY_08.md), [WALLETS_09.md](WALLETS_09.md), [PERFORMANCE_10.md](PERFORMANCE_10.md), [ALPHA_11.md](ALPHA_11.md), [CHRONOLOGY_12.md](CHRONOLOGY_12.md), [INTEGRATION_13.md](INTEGRATION_13.md), [REPORTS_14.md](REPORTS_14.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 14 (Prompt 14: readable, cited intelligence feed and digest), 2026-10-12. Prompt 14 took the Phase 14 slot; the old proposed Phase 14 (trader claimed-wallet linking) is now carry-over C-14 (D-091).
- Model status: unchanged, none configured (D-036). The feed never calls a model.
- Data status: no live post, wallet fetch or candle source was used. The tracked database has no social tables, so a real `social brief` today prints "No supported high-priority observations" with the reason "social tables not present in this database (social schema not migrated)". Every populated feed in this phase ran on invented, watermarked fixtures.
- Next phase: 15 as proposed in ROADMAP.md, or a carry-over, unless Elving supplies Prompt 15. Not started.
- Active branch: `feature/social-intelligence`.
- Phase 14 started from `fb23c39` ("social-intel phase 13: record commit and push route in handoff"), the commit on the remote branch. No drift. Baseline `python -m pytest tests -q` at the start: exit 1, `1 failed, 528 passed` (only the known C-1 clock failure), matching the Phase 13 handoff.
- No migration in this phase. Schema stays at 12.

## What Phase 14 added

- `memelab/social/feed_store.py`: read only (`mode=ro`). `load_input` builds the input document (schema `memelab.social.feed.input/1`) from the newest narrative snapshot at or before as_of: clusters, members joined to claim attributes, items, accounts and trader links, the previous comparable snapshot's stances, change rows, Phase 12 current flags and the latest liquidity and exit facts. Missing tables, no snapshot or an unopenable file become an explicit availability status. `model_status` uses `llm.llm_status` (no network).
- `memelab/social/feed_core.py`: pure. `build` gives the feed document (schema `memelab.social.feed/1`, `feed_sha256`); `render` gives the views `brief`, `trader-digest`, `feed`; `make_filters`, `safe_url`, `md`, `fmt_time`, `parse_time`.
- `memelab/social/feed_cli.py`: `social brief`, `social trader-digest`, `social feed` (with `--as-of`, `--tz`, `--db`, `--run`, `--include-fixtures`, `--fixture`, `--window-hours`, filters, `--json`, `--report-dir`) and `social feed-demo`.
- `memelab/social/feed_demo.py`: builds a throwaway store from a fixture spec through the real store functions and the real narrative engine.
- `memelab/report.py`: `render_social_feed(doc, view)`. `memelab/social/cli.py`: registration and docstring.
- Tests: `tests/test_social_feed.py` (37). Fixture: `tests/fixtures/social/feed/` (`make_feed.py` builds `demo_day.json`; a test checks they match; `sample_report.md` is the CLI output, checked byte for byte).
- Docs: `REPORTS_14.md`, DECISIONS D-091 to D-096, ROADMAP (14 DONE, C-14 added, 19 notes the feed), SOURCE_COVERAGE.

## Gate, item by item

- Durable useful generated report: `tests/fixtures/social/feed/sample_report.md` (228 lines: morning brief, trader digest, feed filtered to `--risk any`). Reproduce with `python -m memelab social feed-demo --fixture tests/fixtures/social/feed/demo_day.json` (exit 0); `test_sample_report_is_reproduced_by_the_cli` proves the output equals the file. `--report-dir` writes `.md` and `.json` per view (`test_cli_views_report_dir_and_usage_errors`).
- Linked sources and provenance: every block lists who said it with sanitized original links, first observed and first published times, the narrative run, cluster key, claim ids, chronology runs and market fact ids (`test_one_narrative_has_every_required_field`, `test_liquidity_and_risk_flags_from_stored_facts`).
- No fake live output: fixture input is watermarked at top and bottom of every view and `fixture: true` in the JSON; live commands skip fixture snapshots unless asked (`test_live_view_ignores_fixture_snapshots_unless_asked`); with nothing qualifying the brief says "No supported high-priority observations." (`test_zero_narratives_says_no_supported_high_priority_observations`, `test_stale_data_is_labelled_low_and_never_high`). On the real tracked database: `python -m memelab social brief --as-of 2026-10-13T12:00:00+00:00 --tz America/New_York` exit 0, no-signal line with "social schema not migrated".
- Prompt test list, each a named test: see REPORTS_14.md "Test list".
- No notifications and no scheduling were added.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change: exit 1, `1 failed, 565 passed`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched, present since Phase 00). With it deselected: `565 passed, 1 deselected`. The prompt's "full suite green" is therefore met except for that pre-existing failure, which belongs to carry-over C-1.
- `python -m pytest tests/test_social_feed.py -q` -> `37 passed`.
- `python -m memelab social guard` exit 0 (0 violations).
- The EVM test still writes `data/reports/<stamp>_BRETT_*.md`; deleted by hand after each run (C-1). `git status` clean after that.

## Things the next phase should know

- The feed reads only stored snapshots. Run `social narrative-snapshot` (and `social chrono run` where wanted) before `social brief` for current results.
- `feed_core.build` output is the stable machine-readable form for later alerts and the scheduler (Phases 19 and 20). Keep the schema name when adding fields; bump it if a field changes meaning.
- Nothing from post wording or own-words summaries is rendered (D-095). If a later phase wants summaries in a report, that needs its own decision.
- Priority and the 24 h staleness limit are code defaults (`feed_core.DEFAULTS`), not a stored policy.

## Helius key

The key is not in the repo and must never be committed. Code reads it through `memelab/secrets.py`, in this order:

1. The `HELIUS_API_KEY` environment variable. Use this for a scheduled run, CI or a cloud session (set it as a secret there).
2. `helius_api_key` in `data/config.json`. That file is gitignored. On a machine, create it with `python -m memelab.secrets set` (prompts without echo).

Check with `python -m memelab.secrets status` (prints "set" or "missing" and the source, never the value). A new session that needs the key should ask Elving to supply it (it is not stored in memory or project docs). The key was pasted into a chat once; rotate it if that chat is shared.

## Blockers and open decisions

- Push: the session's own `git push` is not used. Working route: Elving's GitHub connection in Composio, Git Data API (blobs, trees, commits, fast-forward of the feature branch ref, no force, D-001).
- No live posts, wallet fetches or candle provider in session; the tracked database has no social schema.
- C-1 (the clock-dependent catalyst test) keeps the full suite from being fully green.
- D-025, D-028, D-023 and D-036 remain open.
- Phase prompts 15 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 565 passed` and `python -m memelab social guard` exit 0.

## Commit and push

Phase 14 code commit on `feature/social-intelligence`: `e78aa85` (tree 34a88c4ec3125f6b58eb82684cc41925aad2c95a, parent fb23c391cff62b326cd61d684aca1bb899459260; local hash 642431f). This handoff is the commit on top of it.

The push went through Composio and the GitHub Git Data API: the diff against fb23c39 went over as a checksummed xz patch in two chunks (each chunk and the reassembled patch checked by sha256), was applied to the five base files fetched at fb23c39 (their blob shas checked first), all 14 blob shas were checked against the local files before and after upload, the tree sha was compared with the local tree before the commit was created, and the branch ref was moved forward once, without force. `main` was not touched.

Phase 15 is not started.
