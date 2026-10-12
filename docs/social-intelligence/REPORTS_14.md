# Phase 14: readable, cited intelligence feed and digest

Prompt 14, 2026-10-12. Code: `memelab/social/feed_store.py` (read side), `memelab/social/feed_core.py` (build and render, no I/O), `memelab/social/feed_cli.py` (commands), `memelab/social/feed_demo.py` (fixture store builder), `memelab/report.py` (`render_social_feed`). Tests: `tests/test_social_feed.py` (37). Fixture: `tests/fixtures/social/feed/` (`make_feed.py` builds `demo_day.json`; `sample_report.md` is the CLI output). Decisions D-091 to D-096.

## What it does

One read-only renderer over what earlier phases stored. It needs no dashboard and no model.

Inputs, all read only (database opened with `mode=ro`):

- the newest Phase 07 narrative snapshot with cutoff at or before as_of (fixture snapshots only with `--include-fixtures` or `--fixture`), its clusters, members, edges and change rows;
- per member: Phase 06 claim attributes (category, assertion type, stance, sarcasm, disclosed position, verification, injection reasons), the item's public link and publication time (Phase 01), the account handle and kind, the Phase 08 trader link;
- the previous comparable snapshot's stance per source (changed positions);
- Phase 12 current chronology flags for the exact contract, none timed after as_of;
- the latest Phase 05 market facts for the exact contract: `liquidity_reported`, `sell_quote_out` (NO_ROUTE), `volume_24h`;
- the model status from `llm.llm_status` (no network call). The feed never uses a model.

Output: one JSON document (schema `memelab.social.feed/1`, engine `feed-v1`, sorted keys, `feed_sha256`) and three markdown views of it.

| View | Command | What it is |
|---|---|---|
| Morning brief | `social brief` | last 24 h, narrative first: one block per token or theme, grouped High priority / Also active / Older or weakly covered, then unresolved tickers |
| Trader digest | `social trader-digest` | per token or theme: each attributable source's latest stance and disclosed position, changed positions (against the previous snapshot or inside this one), disagreement as sides, repetition as a count |
| Feed | `social feed` | the same blocks, filtered by `--chain`, `--token` (contract, `chain:contract` or `$SYM`), `--source` (source id, account id, trader id or handle), `--since`, `--until`, `--risk any|none|FLAG`, `--min-priority` |

Every block answers, in this order: priority (HEURISTIC), what happened, first observed / first published / last observed, who said it (with original links), independence vs repetition, why it matters (HEURISTIC), what is corroborated, what is speculation, reasons to doubt, liquidity and exit, next step, freshness and coverage, provenance (narrative run, cluster key, claim ids, chronology runs, market fact ids).

## Rules

- Grouping is by exact identity (`ca:<chain>:<contract>`) or structured theme tag, never by author or by time. One account posting five times is one person line. Reposts and forwards are counted once with their original and not listed one by one (the first two are linked, the rest counted).
- Ticker-only mentions are listed apart as unresolved, never joined and never ranked. A `$SYM` filter matches the displayed symbol and the output says symbols are not identity.
- Corroborated means only that two or more independent sources discuss it (INFERENCE); the content of what they claim is never called corroborated. Phase 12 CORROBORATION flags are listed with bucket, order and rule.
- Speculation counts opinions, predictions, questions, conditional claims and unverified claimed facts.
- Reasons to doubt include insufficient coverage, lower-bound counts, disagreement (shown, never resolved), burst and copy hypotheses (HEURISTIC, not proven), unseen originals, inaccessible items, bots and unknown authors, sarcasm, injection suspected, LOW or UNKNOWN confidence, staleness, Phase 12 RISK flags (never FACT) and single-source items.
- Liquidity and exit is always present: NO_DATA says attention says nothing about exit; NO_SELL_ROUTE says treat as not exitable; a reported liquidity figure says pool liquidity is not exit depth. Themes say to check each contract.
- Priority is HEURISTIC and orders the report only: HIGH for fresh, adequately covered, in-window items with two or more independent sources or a chronology RISK flag; MEDIUM for one source or not estimable; LOW for out of window, insufficient coverage or stale (older than 24 h). It reaches no score, watchlist, rejection or trade (`trade_execution_impact: none`).
- With no HIGH item the brief opens with "No supported high-priority observations." and the reason (no social tables, no snapshot, empty snapshot, nothing matches the filters, or nothing qualifies). Nothing is invented.
- No post wording, own-words summary, claim summary, display name or private-store text is rendered. Handles, symbols, ids, chains and contracts must match a safe character set or are replaced by a neutral label; everything else from a provider is markdown-escaped with control and bidi characters removed. Links: http(s) only, no credentials, no query or fragment, ASCII hosts with a dot, no Telegram invite or private-chat links, path percent-encoded.
- Times are stored in UTC and shown in `--tz` (IANA) with the UTC time beside them. Naive ISO times are refused.
- Fixture input is watermarked at the top and bottom of every view and flagged `fixture: true` in the JSON; `--report-dir` file names end in `_FIXTURE`.
- The same input, zone, filters and options give byte-identical JSON and markdown.

## Commands

```
python -m memelab social brief [--as-of T] [--tz ZONE] [--db PATH] [--run ID] [--include-fixtures] [--window-hours H] [filters] [--json] [--report-dir DIR]
python -m memelab social trader-digest (same options)
python -m memelab social feed (same options)
python -m memelab social <brief|trader-digest|feed> --fixture tests/fixtures/social/feed/demo_day.json --tz America/New_York
python -m memelab social feed-demo --fixture tests/fixtures/social/feed/demo_day.json [--out FILE] [--json-out FILE]
```

Default output is stdout. `--report-dir` writes `<stamp>_social_<view>.md` and `.json`. Exit 0 when rendered (including the no-signal brief), 2 for a usage error (unknown zone, bad filter, naive time).

## Sample

`python -m memelab social feed-demo --fixture tests/fixtures/social/feed/demo_day.json` reproduces `tests/fixtures/social/feed/sample_report.md` byte for byte (`test_sample_report_is_reproduced_by_the_cli`). The fixture is written into a throwaway SQLite store through the real store functions, snapshotted by the real narrative engine (two days, so changed positions have a previous snapshot) and read back through the same read path as the lab database. It shows: GOODCAT (three independent sources, an invented trader who flipped from bearish with no position to bullish and holding), HYPEDOG (disagreement, a burst of twelve reposts, a HEURISTIC chronology risk flag on a self-claimed wallet, no sell route), the `ai_agent` theme, NEWPUP (one source, two Telegram forwards, an injection-suspected post; its tracking query, a private invite link and a javascript link are dropped), SLOWFROG (three days old, LOW) and $MOONX (ticker only).

On the real tracked database, which has no social schema: `python -m memelab social brief --as-of 2026-10-13T12:00:00+00:00 --tz America/New_York` exit 0, "No supported high-priority observations. Reason: social tables not present in this database (social schema not migrated)."

## Test list (prompt item -> test)

- 0 narratives: `test_zero_narratives_says_no_supported_high_priority_observations`
- 1 narrative: `test_one_narrative_has_every_required_field`
- multiple narratives: `test_multiple_narratives_are_grouped_by_token_and_theme_and_ordered`
- conflicting opinions: `test_conflicting_opinions_are_shown_as_a_disagreement_never_resolved`
- changed positions: `test_changed_position_against_the_previous_snapshot_and_inside_one`, `test_liquidity_and_risk_flags_from_stored_facts`
- repeated forwards: `test_repeated_forwards_count_once_and_are_not_listed_as_people`
- unresolved ticker: `test_unresolved_ticker_is_listed_apart_and_never_joined`
- source-link sanitation: `test_source_link_sanitation` (17 cases)
- stale data: `test_stale_data_is_labelled_low_and_never_high`
- time zone formatting: `test_time_zone_formatting`
- missing paid model: `test_feed_works_without_a_paid_model_and_never_calls_one`
- prompt-injection text: `test_prompt_injection_text_never_reaches_the_report`, `test_no_post_wording_or_summary_is_rendered`
- identical rerun: `test_identical_rerun_gives_identical_json_and_markdown`
- also: `test_filters_by_chain_token_source_time_and_risk`, `test_live_view_ignores_fixture_snapshots_unless_asked`, `test_sample_report_is_reproduced_by_the_cli`, `test_fixture_file_matches_its_builder`, `test_cli_views_report_dir_and_usage_errors`, `test_demo_refuses_non_fixture_specs`

## Limits

- No live social data exists, so every real run today is the no-signal brief. The feed is as current as the newest narrative snapshot; run `social narrative-snapshot` first.
- The 24 h window and the 24 h staleness limit are options (`--window-hours`; `stale_after_hours` in code), not a stored policy.
- Changed positions compare against the previous comparable narrative snapshot only; a source that changed its mind twice between snapshots shows the net change.
- The feed reads `liquidity_reported`, `sell_quote_out` and `volume_24h` facts only; it does not compute depth. The existing structural checks remain the place for exit analysis.
- Nothing is sent or scheduled (Phases 19 and 20).
