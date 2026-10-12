# Phase 13: social signals in the scout and catalyst workflows

Prompt 13, 2026-10-12. Code: `memelab/social/research_core.py` (engine, no I/O), `memelab/social/research_store.py` (read side), `memelab/social/research_cli.py` (`social research`), hooks in `memelab/cli.py` (`scout --social`), `memelab/report.py` (`render_scout_report(..., social=)`), `memelab/catalyst/cli.py` (`catalyst report --social`). Tests: `tests/test_social_research.py` (23). Fixture: `tests/fixtures/social/research/` (built by `make_research.py`, invented). Decisions D-085 to D-090.

## What it does

A sourced social finding becomes a research candidate next to the tokens the scout or the catalyst already evaluated. It does not replace or rescore anything.

Inputs, all read only:

- Phase 07 narrative clusters from the newest snapshot whose cutoff is at or before the scout's as_of (contract clusters only; theme clusters are not tokens). Fixture snapshots are skipped unless the policy or `--social-include-fixtures` asks for them.
- Phase 07 unassigned ticker-only mentions.
- Phase 12 current chronology flags for the same exact (chain, contract), none timed after as_of.
- The existing `theses` and `rejections` tables, for the latest verdict before as_of.
- The tokens the scout analyzed in this run (`pipeline.analyze_token` results) or the latest catalyst assessment per token.

Every candidate carries three lanes that never read each other:

| Lane | Comes from | Values |
|---|---|---|
| Narrative attention | social findings only | NONE, NOT_ESTIMABLE, STALE, CONFLICTED, EMERGING, CORROBORATED (ticker-only mentions are UNRESOLVED and listed apart) |
| Token structure | the existing fatal checks (m24 fatal flags, stage-2, catalyst fatal list), copied | ACCEPTABLE, FATAL, NOT_EVALUATED |
| Executable entry | the existing status, copied | ATTRACTIVE (NEAR ENTRY, ENTRY CONDITIONS MET, WATCH_FOR_ENTRY), NOT_YET, NOT_EVALUATED |

Research state follows from the lanes: RESEARCH_CANDIDATE (structure acceptable), REJECTED_STRUCTURE (fatal, whatever the attention), NEEDS_STRUCTURAL_ANALYSIS (contract not analyzed this run; not tradable), NO_SOCIAL_SIGNAL (only an earlier rejection to review).

Each candidate also lists originators (source, time, time basis), independent source count, first and last observation, age at as_of, confidence, promotional risks (Phase 07 burst and copy hypotheses, Phase 12 RISK flags, never FACT), timeline evidence (Phase 12 CORROBORATION, CONTEXT and DATA_QUALITY flags), provenance (narrative run and cluster key, chronology run and flag key, the existing evaluation), the unchanged existing score and status, and `trade_execution_impact: none`.

## Rules

- Identity is exact (chain, contract). A finding never joins a token by ticker or name. A finding whose symbol matches an analyzed token on another contract gets `identity_warning: SYMBOL_COLLISION` and inherits nothing. The same address on another chain is another identity.
- High attention never clears a fatal flag. A rejected token stays in the scout's rejected list, unchanged, and appears in the social section under "hype does not override".
- Earlier rejections: STANDS when the structure still fails (with "new social evidence does not reopen a rejection" when there is attention), STANDS when the token was not re-analyzed, REOPEN_FOR_REVIEW only when the existing checks ran again and no longer fired. The review is a label; the pipeline status is whatever the pipeline computed.
- Staleness: the attention lane is STALE when the newest observation is older than `max_age_hours` at as_of (default 48 h) or the snapshot marked the cluster STALE. A stale lane earns weight 0.
- Conflict: a conflicted cluster is CONFLICTED with its stance counts; it is shown and penalised, never resolved.
- Insufficient coverage: NOT_ESTIMABLE (UNKNOWN), with the Phase 07 reasons.
- Repeated ingest: the same finding read twice counts once; the same inputs give the same `result_sha256`.
- The attention weight is HEURISTIC and orders the social section only. It never reaches the m24 score, the status, the ranking, the watchlist, the rejections or any trade.

## Opt-in and policy

Off by default. On with `--social` on `scout` or `catalyst report`, or `"social_research": {"enabled": true}` in `data/config.json` (gitignored, per machine). A policy file passed with `--social-policy` is merged over the config. `python -m memelab social research policy [--policy FILE]` prints the effective policy.

Policy schema `memelab.social.research.policy/1`, defaults in `research_core.DEFAULT_POLICY`: `enabled`, `signals.narratives`, `signals.chronology_flags`, `max_age_hours` 48, `corroborated_min_independent` 2, `include_fixtures` false, weights (per independent source 1.0 capped at 5, confidence HIGH 3 / MODERATE 2 / LOW 1 / UNKNOWN 0, conflicted -2, per risk flag -1), `trade_execution_impact` fixed at `none`. Unknown keys, keys that name the score, status, rank, watchlist, fatal checks, size, position, execution or orders, and any execution impact other than none are refused. Provenance in every section: source (default, config, file, config+file, +cli), path, override keys, sha256 of the effective policy.

## Behaviour when off, empty or unavailable

- Off: no database read, no extra section; the report is the pre-Phase-13 report. Checked on real data: the scout on the repo's inbox files (`disc01 s2_01 deep01a deep02 deep03 deep04 forensics01`, three mints) from commit 4c8d69f and from this branch, each against its own copy of the tracked database, gave identical stdout and identical files under `data/reports` except for the absolute checkout path inside the "Report:" line. Theses, rejections and watchlist rows matched (36, 21, one watchlist row).
- On, social tables missing (the tracked database today): one line, "No-op: social source unavailable: social tables not present in this database (social schema not migrated)". Same run with `--social` on a copy: exit 0, report body identical to the run without it.
- On, no snapshot at or before as_of, or only fixture snapshots: "No-op: no narrative snapshot at or before as_of".
- On, store cannot be opened: "No-op: social source unavailable: cannot open the social store ...". The scout never fails because of the social layer.

## Commands

```
python -m memelab scout --mints ... --results ... [--stage1 ID] --social [--social-policy FILE] [--social-include-fixtures] [--report-dir DIR]
python -m memelab catalyst report --social [--social-policy FILE]
python -m memelab social research policy [--policy FILE]
python -m memelab social research show [--as-of T] [--db PATH] [--include-fixtures] [--json]
python -m memelab social research demo --fixture tests/fixtures/social/research/scout_before_after.json [--out FILE]
```

`--report-dir` is new on `scout` (default unchanged, `data/reports`); it lets a check run without touching tracked paths.

## Fixture before and after

`python -m memelab social research demo --fixture tests/fixtures/social/research/scout_before_after.json` exit 0. Scout lists and report body come from the real scout code (`cli.scout_lists`, `report.render_scout_report`); the social section is appended. "Report body unchanged by the social layer: yes."

| Token | Score | Status | Scout list | Score after | Status after | Narrative attention | Research state |
|---|---|---|---|---|---|---|---|
| GOODCAT | 68 | WATCH | serious | same | same | CORROBORATED | RESEARCH_CANDIDATE |
| HYPEDOG | 0 | REJECTED | rejected | same | same | CORROBORATED | REJECTED_STRUCTURE |
| TOPPICK | 0 | REJECTED | rejected | same | same | CORROBORATED | REJECTED_STRUCTURE |
| OLDRUG | 0 | REJECTED | rejected | same | same | NONE | NO_SOCIAL_SIGNAL |
| SLOWFROG | 48 | RESEARCH REQUIRED | near miss | same | same | STALE | RESEARCH_CANDIDATE |
| GOODCAT (other contract) | not analyzed | not analyzed | not listed | n/a | n/a | EMERGING | NEEDS_STRUCTURAL_ANALYSIS |
| $MOONX (ticker only) | n/a | n/a | not listed | n/a | n/a | UNRESOLVED | never ranked |

The after report is the before report plus this section (invented tokens and sources):

### Social research candidates (opt-in)

This section does not change the score, status, ranking, watchlist, rejections or any trade. Narrative attention, token structure and executable entry are reported separately.
- Policy default-1 (fixture), sha256 622d1b25b461, engine research-v1, as of 2026-10-12 12:00 UTC.

#### Attention on tokens whose structure passed the existing checks

- GOODCAT `solana:XqnDJ6wKKd4bjhFtNnHnbnKDBtQRPaBmXqnDJ6wKKd4b`
  - Narrative attention: CORROBORATED (INFERENCE). 3 independent source(s), reposts and copies collapsed. First seen 2026-10-11 16:00 UTC, last seen 2026-10-12 10:00 UTC.
  - Token structure: ACCEPTABLE. no fatal flag from the existing checks.
  - Executable entry: NOT_YET. existing status WATCH.
  - Originators: fx_source_a at 2026-10-11 16:00 UTC (PROVIDER), fx_source_b at 2026-10-11 16:10 UTC (PROVIDER), fx_source_c at 2026-10-11 16:20 UTC (PROVIDER)
  - Existing workflow, unchanged: score 68, status WATCH.
  - Attention weight (HEURISTIC, orders this section only): 5.
- SLOWFROG `solana:H9ayi4b7b1bDVagsTS5TpCfVMFr6iWvqH9ayi4b7b1bD`
  - Narrative attention: STALE (FACT). newest observation 72.0 h before as_of; limit 48 h. First seen 2026-10-08 18:00 UTC, last seen 2026-10-09 12:00 UTC.
  - Token structure: ACCEPTABLE. no fatal flag from the existing checks.
  - Executable entry: NOT_YET. existing status RESEARCH REQUIRED.
  - Originators: fx_source_h at 2026-10-08 18:00 UTC (PROVIDER), fx_source_i at 2026-10-08 18:10 UTC (PROVIDER)
  - Existing workflow, unchanged: score 48, status RESEARCH REQUIRED.
  - Attention weight (HEURISTIC, orders this section only): 0.

#### Attention on contracts not analyzed in this run (not tradable until analyzed)

- GOODCAT `solana:e6sE6SXuhKoMShW9ts1aPdaJkeAGeFKee6sE6SXuhKoM`
  - Narrative attention: EMERGING (INFERENCE). 1 independent source(s); not corroborated. First seen 2026-10-12 08:00 UTC, last seen 2026-10-12 09:00 UTC.
  - Token structure: NOT_EVALUATED. the existing pipeline has not analyzed this contract in this run.
  - Executable entry: NOT_EVALUATED. not analyzed.
  - Originators: fx_source_g at 2026-10-12 08:00 UTC (PROVIDER)
  - Note: the symbol GOODCAT also names analyzed contract(s) XqnDJ6wKKd4bjhFtNnHnbnKDBtQRPaBmXqnDJ6wKKd4b on solana; this is a different contract (possible spoof) and inherits nothing from them.
  - Attention weight (HEURISTIC, orders this section only): 2.

#### Attention on tokens that failed the existing structural checks (hype does not override)

- TOPPICK `solana:HYgZd4ttK4uQaCnL1KfXfCbGzYeLaXQYHYgZd4ttK4uQ`
  - Narrative attention: CORROBORATED (INFERENCE). 5 independent source(s), reposts and copies collapsed. First seen 2026-10-12 09:00 UTC, last seen 2026-10-12 11:00 UTC.
  - Token structure: FATAL. existing fatal checks: NO_SELL_ROUTE.
  - Executable entry: NOT_YET. structure fails, so no entry is considered.
  - Originators: fx_source_f at 2026-10-12 09:00 UTC (PROVIDER)
  - Note: narrative attention does not override a fatal flag.
  - Existing workflow, unchanged: score 0, status REJECTED.
  - Attention weight (HEURISTIC, orders this section only): 8.
- HYPEDOG `solana:ud7KPUQpjkB1QSrBS4N8p1oHerDnEPshud7KPUQpjkB1`
  - Narrative attention: CORROBORATED (INFERENCE). 8 independent source(s), reposts and copies collapsed. First seen 2026-10-12 06:00 UTC, last seen 2026-10-12 11:00 UTC.
  - Token structure: FATAL. existing fatal checks: MINT_AUTHORITY_ACTIVE.
  - Executable entry: NOT_YET. structure fails, so no entry is considered.
  - Originators: fx_source_d at 2026-10-12 06:00 UTC (PROVIDER), fx_source_e at 2026-10-12 06:10 UTC (PROVIDER)
  - Promotional risk (HEURISTIC, not proven): burst_amplification. invented: 40 amplifying sources inside 15 minutes
  - Note: narrative attention does not override a fatal flag.
  - Existing workflow, unchanged: score 0, status REJECTED.
  - Attention weight (HEURISTIC, orders this section only): 7.

#### Earlier rejections reviewed (no current social signal)

- OLDRUG `solana:hEfghVNqp2Am87K17PXtgXoV5yaNCSXJhEfghVNqp2Am`
  - Narrative attention: NONE (UNKNOWN). no social finding for this exact contract. First seen unknown, last seen unknown.
  - Token structure: FATAL. existing fatal checks: LP_UNLOCKED_DEV_CONTROLLED.
  - Executable entry: NOT_YET. structure fails, so no entry is considered.
  - Earlier rejection: STANDS. structure still fails: LP_UNLOCKED_DEV_CONTROLLED.
  - Existing workflow, unchanged: score 0, status REJECTED.
  - Attention weight (HEURISTIC, orders this section only): 0.

#### Unresolved ticker-only mentions (no contract, never ranked)

- MOONX: 14 mention(s). ticker only, no contract on a stated chain; never ranked and never joined to a token.

- Contains fixture data (not live provider data).

## Test list (prompt item -> test)

- fatal-flag override: `test_fatal_flag_override_high_hype_never_clears_a_fatal_flag`
- spoof contract: `test_spoof_contract_with_the_same_symbol_inherits_nothing`
- social top pick with no liquidity: `test_social_top_pick_with_no_liquidity_stays_out_of_tradable_rankings`
- valid candidate with credible early discussion: `test_valid_candidate_with_credible_early_discussion_is_enriched_not_rescored`
- no social data: `test_no_social_data_is_an_explicit_no_op_and_the_report_is_unchanged`, `test_no_op_when_the_social_store_is_missing_empty_or_unopenable`
- stale sources: `test_stale_sources_are_labelled_and_earn_nothing`
- conflicting narratives: `test_conflicting_narratives_are_shown_and_penalised_never_resolved`
- repeated ingest: `test_repeated_ingest_of_the_same_findings_counts_once`, `test_findings_from_a_real_snapshot_and_repeated_ingest`
- rejected thesis and later materially changed evidence: `test_rejected_thesis_and_later_materially_changed_evidence`, `test_prior_rejections_read_from_the_existing_tables`
- before/after report: `test_before_after_report_enriches_one_candidate_and_leaves_rejections_alone`, `test_demo_cli_runs_and_writes_side_by_side`, `test_fixture_file_matches_its_builder`
- integrated path: `test_scout_command_off_is_unchanged_and_on_attaches_from_the_real_snapshot` (the real `cmd_scout` with a real Phase 07 snapshot in a temp database; only `analyze_token` and the inbox loader are replaced by fixture results), `test_scout_command_social_enabled_in_config_without_flag`, `test_catalyst_report_social_section_is_opt_in`
- also: `test_insufficient_coverage_is_not_estimable`, `test_ticker_only_mentions_stay_unresolved_and_out_of_every_list`, `test_policy_is_opt_in_versioned_and_refuses_anything_that_reaches_scoring_or_execution`, `test_weights_order_the_section_only`, `test_no_trade_or_watchlist_side_effects`

## Limits

- There is no live social data, so every real run is a no-op until live collection exists and the tracked database is migrated to the social schema.
- `social-note` is unchanged. Its rows are manual metrics in `social_snapshots` with no provenance chain (no observation, no account, no time basis), so the adapter does not read them (D-089).
- The social section lives in the report text. Nothing is stored for it; an audit of an old section is the report file plus the narrative run id and policy sha it names (D-086).
- The catalyst section reads the latest catalyst assessment per token; the catalyst's own triage score and verdict are copied, not recomputed. Catalyst events without a token link have no contract and are not candidates.
- m19, `launch/social.py` and `catalyst/attention.py` still do not read social metrics (Phases 17 and 18).
