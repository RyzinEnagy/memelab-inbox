# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md), [IDENTITY_05.md](IDENTITY_05.md), [CLAIMS_06.md](CLAIMS_06.md), [NARRATIVES_07.md](NARRATIVES_07.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 07 (Prompt 07: narrative clustering, originators, amplifiers and independent corroboration), 2026-10-12. Prompt 07 took the Phase 07 slot; the old proposed Phase 07 (Telegram public channels via Chrome, needs D-028) is now carry-over C-7 (D-041).
- Model status: unchanged, none configured (`social llm-health` -> `model_not_configured`, D-036). Phase 07 makes no model call at all; clustering is deterministic (D-043).
- Data status: no live provider data and no stored claims exist in the tracked database. Every proof ran on invented fixtures. Snapshots carry `contains_fixture`.
- Next phase: 08 as proposed in ROADMAP.md (needs C-5 for sources), or C-5 / C-6 / C-7, unless Elving supplies Prompt 08.
- Active branch: `feature/social-intelligence`.
- Phase 07 started from `1eaca1b` ("social-intel phase 06: handoff records the push"), the head the Phase 06 push left on the remote branch. No drift. Baseline `python -m pytest tests -q` gave `1 failed, 240 passed`, as recorded in the Phase 06 handoff.
- Commit and push: see "Commit and push" at the end of this file.

## What Phase 07 added

- `memelab/social/narratives.py`: `snapshot()` (build and store one immutable snapshot), `day_window()`, `run_view()`, `members()`, `edges_for()`, `changes_for()`, `latest_run()`, `explain()`, `report()`. Engine version `narr-v1`.
- `memelab/social/schema.py`: migration 7 (`social_narrative_runs`, `_clusters`, `_members`, `_edges`, `_changes`).
- `memelab/social/cli.py`: `social narrative-snapshot`, `narrative-show`, `narrative-why`, `narrative-changes`.
- Tests: `tests/test_social_narratives.py` (39). `tests/test_social_extraction.py::test_migration_6_rolls_back_cleanly` changed to stop assuming 6 is the newest migration (same fix Phase 06 made for Phase 05's test).
- Fixture: `tests/fixtures/social/narratives/two_days.json` (invented posts, two controlled windows, expected results beside them).
- Docs: `NARRATIVES_07.md` (rules, metrics, snapshot semantics, sample output, test map, limits), DECISIONS D-041 to D-046, ROADMAP (row 07 DONE, C-7 added, 08 NEXT), SCHEMA_01 (later migrations line).

## Gate, item by item

- Working engine that groups related claims by resolved contract or labelled theme without conflating similar assets: `ca:<chain>:<contract>` and `tag:<tag>` keys only. Tests `test_same_ticker_on_different_contracts_stays_in_separate_clusters`, `test_ticker_only_claims_never_create_or_join_a_contract_cluster`, `test_multi_token_theme_links_tokens_and_chains`.
- Metrics (first-observed time, source count, independent count, forwarding and repost edges, shared dependencies, mentions per sliding window, rate of change, confidence, coverage limits, chain and linked tokens): stored per cluster; `test_sliding_windows_report_rate_of_change`, `test_two_separate_early_originals_count_twice_and_first_observed_is_the_earliest_observation`, `test_one_hundred_reposts_of_one_original_are_one_independent_source`.
- Independent count defensible: one origin per dependency group, distinct sources only, bots, aggregators and unknown authors excluded, linked accounts merged, unobserved originals never counted. Tests `test_different_accounts_citing_one_shared_original_are_not_independent`, `test_quote_that_repeats_is_amplifier_reply_and_commentary_are_dependent_and_none_is_independent`, `test_byte_identical_copies_from_several_accounts_collapse_to_one_group_with_a_hypothesis`, `test_bots_aggregators_unknown_authors_and_linked_accounts_do_not_inflate_independence`, `test_reposts_group_with_their_original_even_when_the_text_differs`, `test_a_reply_to_an_item_that_makes_no_claim_is_its_own_origin_but_a_reply_to_an_unseen_item_is_not`.
- Inferred coordination marked as hypothesis: flags carry `evidence: HEURISTIC`, `proven: false`.
- `insufficient_coverage` when volume or independence is not estimable: four tests in NARRATIVES_07.md, plus `test_reposts_whose_original_was_never_observed_make_volume_but_not_independence`.
- Snapshots and deltas with timestamps, versioning and provenance links: `social_narrative_runs` (engine version, window, cutoff, input hash, previous run), `social_narrative_members` (claim id, observation id, role, reason), `social_narrative_changes`. Tests `test_snapshot_is_idempotent_immutable_and_a_replay_of_a_past_window_reproduces_it`, `test_open_window_is_marked_incomplete_and_the_cutoff_is_the_clock`, `test_every_member_names_its_claim_observation_and_reason_and_the_text_is_never_stored`.
- Prompt test list: repeated reposts by 100 handles, two separate early originals, same ticker different contracts, multi-token themes, conflicting narratives (`test_conflicting_independent_narratives_are_flagged_not_averaged`, `test_a_contradicts_relation_between_claims_also_marks_the_conflict`), changed opinion (`test_changed_opinion_counts_only_the_latest_stance_of_that_source`, `test_sarcasm_and_neutral_posts_do_not_vote`), deleted or inaccessible source (`test_deleted_original_stays_an_origin_but_its_stance_is_not_counted`, `test_a_protected_or_blocked_source_keeps_its_stance_and_lowers_confidence`), time-zone boundaries (four tests incl. DST day lengths and a half-open window), stale data (`test_stale_cluster_is_marked_dormant_and_a_late_observation_is_not_todays_mention`).
- Daily change proven on two controlled windows: `test_two_controlled_windows_produce_the_expected_daily_change` (expected values come from the fixture file, written before the run). Day 2 against day 1: LABDOG window mentions 5 -> 21 (ACTIVITY_UP), independent sources 2 -> 3 (INDEPENDENCE_CHANGED), no conflict -> conflict (CONFLICT_CHANGED), MIDCAT and the `animal` tag DORMANT, NEWPUP NEW; the 20 added reposts add no independent source.
- Explainable "why this cluster": `narratives.explain()` and `social narrative-why`; `test_why_this_cluster_explains_rule_members_groups_and_confidence`.
- Durable snapshot and change summary: stored in the database (migration 7); CLI demo below.
- Not built, on purpose: vector or LLM semantic clustering (D-043: no model configured, no evaluation set, so it would be an unevaluated topic).

## Demo (temp database, fixed clocks, every command exit 0)

`social narrative-snapshot --day 2026-10-12 --now 1791849600` then `--day 2026-10-13 --now 1791936000` on the fixture loaded by `tests.test_social_narratives.load_fixture`; `social narrative-changes`, `social narrative-why --run 2 --cluster ca:solana:8CyKBG...`. Output is reproduced in NARRATIVES_07.md ("Sample: two controlled windows"). Run 2 reports `1 ACTIVITY_UP, 1 CONFLICT_CHANGED, 2 DORMANT, 1 INDEPENDENCE_CHANGED, 1 NEW` against run 1.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change: exit 1, `1 failed, 279 passed in 19.61s`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched).
- `python -m pytest tests/test_social_narratives.py -q` -> `39 passed`.
- `python -m memelab social guard` exit 0 (253 files, 74 JSON, 1 SQLite, 0 violations, Phase 07 files staged).
- Side effect still present: the EVM test writes `data/reports/<stamp>_BRETT_0x532f.md`; deleted by hand after each run (C-1). `git status` clean after that.

## Files changed in Phase 07

`docs/social-intelligence/NARRATIVES_07.md`, `DECISIONS.md`, `HANDOFF.md`, `ROADMAP.md`, `SCHEMA_01.md`; `memelab/social/cli.py`, `narratives.py`, `schema.py`; `tests/test_social_narratives.py`, `tests/test_social_extraction.py`; `tests/fixtures/social/narratives/two_days.json`.

## Things the next phase should know

- Nothing calls the narrative engine on a schedule, and ingestion still does not call extraction, so the tracked database has no claims for it. A collector has to run `extraction.extract_observation()` while it holds the text (Phase 06 note), and a scheduled run has to call `narratives.snapshot()` and commit. That wiring belongs to Phase 20.
- Counting: use `narratives` roles and `independent_source_count` for corroboration, not raw mention counts. `store.is_independent_original()` still governs attention counting (D-029); D-042 explains why corroboration is stricter.
- A snapshot needs coverage rows (`social_coverage`, written by ingestion) for every platform it uses, otherwise the cluster is `insufficient_coverage` (`no_coverage_record:<platform>`). `--no-require-coverage` turns that off and gives a different parameter set, so those runs are not compared with the default ones.
- The window is cut in the zone given by `--tz`. Compare runs only within one zone; the change summary does.
- Thresholds (burst 10 sources in 900 s, copies from 3 sources, confidence ceilings, 48 h staleness) are heuristics in `narratives.DEFAULTS`, recorded in each run's parameters.
- Contract clusters with different `(chain, contract)` are never merged, including migrated or bridged tokens (`social_token_relations` is not used yet).

## Blockers and open decisions

- Push: the session's own `git push` still gets 403 (repo not in its sources). Working route: Elving's GitHub connection in Composio, Git Data API, fast-forward of the feature branch ref, no force (D-001: feature work only on `feature/social-intelligence`, never `main`).
- D-025 (X browser automation), D-028 (Telegram bot terms), the X budget (D-023) and the model choice and budget (D-036) are open.
- Phase prompts 08 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 279 passed` and `python -m memelab social guard` exit 0. Then start the next phase.

## Commit and push

- Phase 07 commit on `feature/social-intelligence`: `8319baf` ("social-intel phase 07: narrative clustering, originators, amplifiers and independent corroboration"), parent `1eaca1b`. Its tree (`d666cdd`) is identical to the original local commit, so content was verified end to end. The branch was rewritten once after the first push so the commit author is noreply@anthropic.com (force-moved ref, Elving approved).
- Route: the session's own `git push` gets 403. The local commit was sent as a compressed patch (checksums checked) to a fresh clone in the Composio sandbox, applied, and committed with Composio's GitHub tool (Git Data API, fast-forward, no force). Nothing touched `main`.
- This handoff text was added in one more small commit after that, same route.
