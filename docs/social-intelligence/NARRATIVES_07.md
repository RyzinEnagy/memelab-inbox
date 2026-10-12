# Phase 07: narrative clustering, originators, amplifiers and independent corroboration

Source of truth: `memelab/social/narratives.py` (engine), `memelab/social/schema.py` migration 7 (tables), `memelab/social/cli.py` (commands). Tests: `tests/test_social_narratives.py` (39). Fixtures: `tests/fixtures/social/narratives/two_days.json` (invented posts, expected results written next to them).

Related: [HANDOFF.md](HANDOFF.md), [DECISIONS.md](DECISIONS.md) (D-041 to D-046), [CLAIMS_06.md](CLAIMS_06.md), [IDENTITY_05.md](IDENTITY_05.md), [SCHEMA_01.md](SCHEMA_01.md).

## What it does and what it does not

It groups current Phase 06 claims into clusters, works out who originated a claim and who only repeated it, and stores an immutable snapshot for one window with a change summary against the previous comparable snapshot. It reads only what earlier phases stored: claims and attributes, provider references (reposts, quotes, replies, forwards), account kinds, trader links, observation times and statuses, and coverage rows.

Nothing in the real database feeds it yet. Ingestion still does not call extraction (HANDOFF, Phase 06), so the tracked database holds no claims, and every proof here runs on invented fixtures. Snapshots report `contains_fixture` when any member observation has `access_mode='fixture'`.

## Clusters (deterministic only)

| Key | Joined by | Never joined by |
|---|---|---|
| `ca:<chain>:<contract>` | a claim token that Phase 05 resolved to that exact chain and contract | ticker, token name, wording |
| `tag:<tag>` | a structured narrative tag on the claim (closed list `extraction.NARRATIVE_TAGS`) | free text, topics invented by the engine |

A claim can join several clusters (a two-token claim joins both contract clusters, plus its theme clusters). A ticker-only, ambiguous or unresolved mention joins no contract cluster; it is listed under `unassigned` by reason and by symbol. Two contracts that share a ticker are two clusters, each flagged `ticker_collision` with the other cluster named. No vector or LLM clustering runs (D-043); the snapshot parameters record `semantic_clustering: not_enabled`.

## Counting rules

- Mentions are distinct items. Claims, accounts and reposts are not mentions of their own.
- Dependency groups: items that reach the same original through any chain of references (repost, forward, quote, reply), or that carry the same content hash, are one group. A group has one origin: its earliest item that points at nothing else.
- Roles: `INDEPENDENT_ORIGINAL` (the origin, with an attributable source), `UNVERIFIED_ORIGINAL` (origin with an unknown author, a BOT or an AGGREGATOR account), `AMPLIFIER` (repost, forward, or a quote that repeats), `DEPENDENT` (reply, quote with its own words, identical copy).
- `independent_source_count` is the number of distinct sources among the independent origins. A source is the trader id when the account is linked to a trader, else the account id. Two originals by one source count once.
- A reply or own-words quote to an item that the engine has observed but that makes no claim about this token is its own origin in this cluster. A reply to an item never observed leaves the group with no observed origin.
- Not estimable: no independent origin at all gives `insufficient_coverage` (`origins_not_observed` when only reposts of unseen originals exist, `no_attributable_source` otherwise).
- Inferred coordination is a hypothesis flag (`burst_amplification`, `identical_text_multi_source`) with evidence `HEURISTIC` and `proven: false`. Reposts and copies are already collapsed into their group, so a hypothesis changes confidence, not the source count. Identical text that a repost or forward already explains is not flagged.

## Metrics per cluster

First and last observed time (collector clock, so "first observed" and not "first ever mentioned"), earliest provider publication time, item count, mentions in the window, source count, independent source and group counts, amplifier and dependent counts, unobserved origin count, edge count, stance counts by source (latest non-neutral stance per source; deleted items and sarcasm do not vote; reposts do not vote), opinion changes, conflict flag (opposite stances, or a `CONTRADICTS` relation), trailing sliding windows (default 1 h, 6 h, 24 h: current, previous, delta, percent change, peak sliding count, plus the same for independent origins), chain and linked-token context (other resolved tokens and tags that co-occur), coverage by platform, confidence with its basis, freshness, flags, dependency groups, originators.

Event time is the provider publication time when known, else the collector time, else unknown. Windows are half open `[start, end)`. An item observed more than 48 hours after publication is `late_observed`: it is placed by publication time, so it never counts as today's mention.

## Insufficient coverage and confidence

`status = insufficient_coverage` (reasons listed) when: a platform has no coverage record and `require_coverage` is on, a platform has only GAP, BLOCKED or SKIPPED coverage in the window, most items have no usable time, or there is no independent origin. Then `independent_source_count` is NULL, confidence is UNKNOWN, and the observed counts remain as lower bounds. Partial coverage keeps `ok` and marks `counts_are_lower_bounds`.

Confidence (HEURISTIC labels): HIGH from 5 independent sources, MODERATE from 2, LOW for 1. Ceilings: MODERATE for a coordination hypothesis, partial coverage, an unobserved original, an inaccessible source or disagreement; LOW when nothing was observed in the last 48 hours. Each ceiling that binds is written into `confidence_basis`.

## Snapshots and changes

- One run per (engine version, window, cutoff, zone, parameters, input hash). The input hash covers the claims, item times and states, references, account kinds, trader links and coverage rows used. The same inputs return the same run (`created: false`); new information is a new run; runs are never edited.
- Knowledge cutoff is `min(window_end, clock)`. Nothing observed after it is used, so replaying a past window later reproduces the stored run. A window that has not ended is stored with `window_complete = 0`.
- Windows are calendar days in an IANA zone (`--day 2026-10-12 --tz America/New_York`), or explicit aware bounds. Times stay UTC epoch seconds; a day with a clock change is 23 or 25 hours long. A naive datetime is refused.
- Change summary against the latest earlier run with the same parameters and zone: `NEW`, `ACTIVITY_UP`, `ACTIVITY_DOWN`, `DORMANT`, `REVIVED`, `INDEPENDENCE_CHANGED`, `STANCE_SHIFT`, `CONFLICT_CHANGED`, `STATUS_CHANGED`, each with before and after numbers. Activity compares in-window mentions of one window with the previous window. Cumulative fields (first observed, item and source counts) cover everything up to the cutoff.
- Provenance: `social_narrative_members` holds one row per claim with its observation id, source, role, group, event time and its reason code; `social_narrative_edges` holds who repeats whom.

## Why this cluster

`narratives.explain(con, run_id, cluster_key)` and `social narrative-why` return the rule that put claims in the cluster, what was never used, every member with claim id, observation id, role and reason, the dependency groups and edges, flags, coverage, windows, the confidence basis, and a plain-English paragraph.

## Commands

```
python -m memelab social narrative-snapshot --day 2026-10-12 [--tz America/New_York] [--now <epoch>] [--db <path>]
python -m memelab social narrative-snapshot --window-start <epoch|ISO+offset> --window-end <...>
python -m memelab social narrative-show [--run N] [--json]
python -m memelab social narrative-why --run N --cluster <key>
python -m memelab social narrative-changes [--run N]
```

## Sample: two controlled windows

Fixture `two_days.json`: day 1 is 2026-10-12 UTC, day 2 is 2026-10-13 UTC. Token LABDOG: day 1 has two separate original posts and three reposts of the first; day 2 adds a third original with the opposite stance and 20 reposts of the first original inside one minute. Token MIDCAT has one post on day 1 and none on day 2. Token NEWPUP appears on day 2. The tag `animal` is on one day 1 post. Expected results are in the fixture file and asserted in `test_two_controlled_windows_produce_the_expected_daily_change`.

```
Narrative snapshot 1: window 2026-10-12 UTC, cutoff 1791849600, complete, engine narr-v1.
3 cluster(s) from 6 claim(s). Compared with: none (first comparable snapshot).
- LABDOG ...: ok, confidence MODERATE, 5 mention(s) in window, independent sources 2, amplifiers 3, dependent 0, fresh.
- MIDCAT ...: ok, confidence LOW, 1 mention(s) in window, independent sources 1, amplifiers 0, dependent 0, fresh.
- theme: animal [tag:animal]: ok, confidence LOW, 1 mention(s) in window, independent sources 1, ...
Changes since the previous snapshot: 3 NEW.

Narrative snapshot 2: window 2026-10-13 UTC, cutoff 1791936000, complete, engine narr-v1.
4 cluster(s) from 28 claim(s). Compared with: run 1.
- LABDOG ...: ok, confidence MODERATE, 21 mention(s) in window, independent sources 3, amplifiers 23, dependent 0, fresh.
- MIDCAT ...: ok, confidence LOW, 0 mention(s) in window, independent sources 1, ...
- NEWPUP ...: ok, confidence LOW, 1 mention(s) in window, independent sources 1, ...
- theme: animal ...: ok, confidence LOW, 0 mention(s) in window, independent sources 1, ...
Changes since the previous snapshot: 1 ACTIVITY_UP, 1 CONFLICT_CHANGED, 2 DORMANT, 1 INDEPENDENCE_CHANGED, 1 NEW.
```

The 20 day 2 reposts raised LABDOG mentions from 5 to 21 and added no independent source; the third original moved it from 2 to 3 and made the sources disagree.

## Prompt test list to test names

| Prompt item | Test |
|---|---|
| repeated reposts by 100 handles | `test_one_hundred_reposts_of_one_original_are_one_independent_source` |
| two separate early originals | `test_two_separate_early_originals_count_twice_and_first_observed_is_the_earliest_observation` |
| same ticker, different contracts | `test_same_ticker_on_different_contracts_stays_in_separate_clusters`, `test_ticker_only_claims_never_create_or_join_a_contract_cluster` |
| multi-token themes | `test_multi_token_theme_links_tokens_and_chains` |
| conflicting narratives | `test_conflicting_independent_narratives_are_flagged_not_averaged`, `test_a_contradicts_relation_between_claims_also_marks_the_conflict` |
| changed opinion | `test_changed_opinion_counts_only_the_latest_stance_of_that_source` |
| deleted or inaccessible source | `test_deleted_original_stays_an_origin_but_its_stance_is_not_counted`, `test_a_protected_or_blocked_source_keeps_its_stance_and_lowers_confidence`, `test_reposts_whose_original_was_never_observed_make_volume_but_not_independence` |
| time-zone boundaries | `test_day_window_follows_the_zone_and_dst_changes_the_day_length`, `test_the_same_late_evening_post_is_in_different_days_depending_on_the_zone`, `test_window_is_half_open_and_an_item_at_the_end_belongs_to_the_next_day`, `test_naive_or_missing_window_is_refused` |
| stale data | `test_stale_cluster_is_marked_dormant_and_a_late_observation_is_not_todays_mention` |
| daily change from two windows | `test_two_controlled_windows_produce_the_expected_daily_change` |
| why this cluster | `test_why_this_cluster_explains_rule_members_groups_and_confidence` |
| insufficient_coverage | `test_no_coverage_record_means_volume_is_not_estimable`, `test_a_coverage_gap_is_insufficient_and_partial_coverage_gives_lower_bounds`, `test_only_unattributable_sources_is_not_estimable`, `test_items_with_no_usable_time_make_volume_not_estimable` |

## Limits

- No live data and no live claims have passed through it. Claim volume in production depends on a collector calling extraction (carry-over from Phase 06).
- Shared dependencies are found through provider references and identical hashes only. A paraphrased copy of someone's post with no reference is counted as an independent source. Semantic matching would find more of these and was not built (D-043).
- Source identity is the account, or the trader when the lab linked accounts. Several accounts under one owner with no recorded link count separately.
- The confidence labels and thresholds are heuristics set in this phase, not calibrated against outcomes.
