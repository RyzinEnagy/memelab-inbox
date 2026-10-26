# Phase 10 independent skeptic review (attempt 10b)

Reviewer: orchestrator's independent skeptic (PI-D-013), fresh context. Branch `feature/predictive-intelligence` at `564be76`. Own clone `/home/claude/pi_orchestration/skeptic_10b`; copies of the stores in `/tmp/claude-0/p10b/`. Nothing was written inside `/home/claude/memelab-inbox` or the stores; `phase_06/sealed/` was not opened. No vendor, Firecrawl or language-model call. Scripts: `/home/claude/pi_orchestration/skeptic/p10b_*.py`.

## Verdict

Material failures found, both in the TEST_ONLY components (catalyst classifier with its follow-through proposal, and the social evidence adapter). No real-data number of Phase 10 changes: the central claim (no social or catalyst row for any decision) holds, every socialcat-1 value of the 240 development rows was re-derived with 0 differences, and the recorded run, oracle, trace, suite, guard, seal check and release audit reproduce at HEAD.

## Checks (command, result)

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Social or catalyst tables in any state export | `p10b_export_tables.py /home/claude/memelab-inbox origin/main` (all 92 versions of `data/state/latest.json`, 6 of `state/latest.json`) | no `catalyst_*` or `social_*` table ever exported. Tables seen: tokens, theses, entries, watchlist, rejections, chains, chain_snapshots, chain_scores, regime_snapshots, narratives, narrative_snapshots, benchmark_baskets, ecosystem_alerts, upcoming_launches, launch_cohort, launch_alerts, launch_monitor, launch_transitions, launch_rejections, pools, market_snapshots |
| 2 | Lab databases readable by the initiative | `find / -name '*.sqlite'`; `git log --all -- '*.sqlite'` | one tracked `data/memelab.sqlite` (one version, `b6c424d`, identical on every branch, sha256 `068287c0...`); no catalyst or social-schema table in it; no `data/private/`; no other lab store on disk |
| 3 | Adjacent rows naming decision mints | `p10b_rows_scan.py`, `p10b_inbox_attention.py`, `p10b_launch_channels.py` | see MINOR m1: `social_snapshots` (99 rows, Jupiter holder change, 8 mints, 216 dev-store decisions), launch tables, inbox provider reads. None is a social item or catalyst event |
| 4 | CX-10 and coverage re-derived from git objects | `p10b_rederive.py /home/claude/memelab-inbox p05.sqlite origin/main` | 925 of 925 token rows equal their own export; blob 925, commit time 925; website 659 set (656 after the 3 x.com search URLs), twitter 616, telegram 0, narrative tag 39; newest export adds 74 websites, 4 twitter, 20 tags; trend lines 101/314/354 known (769), 153 UNKNOWN, 3 no bucket. All equal the phase's numbers |
| 5 | Inbox catalyst cross-check re-derived | inline over `inbox/cat01.json` | Coinbase asset list 14 decision mints (11 Solana, 2 ethereum, 1 base); DEX Screener boosts 1. Equal to `crosschecks.json` |
| 6 | Every socialcat-1 value, own code | `p10b_features_indep.py ... SOCIAL_FEATURES_DEVELOPMENT.csv` (no memelab import; own line parsing, own git reads of each decision's export) | 4,560 values compared, 0 differences |
| 7 | OOS counts re-derived from the dev label store | inline SQL | T1 13 rows, 4 positive, 2 days; R2 24, 8, 3; T1b 37 rows, 3 positive, 5 days; T2 0. Equal to the card |
| 8 | Phase tests | `python -m pytest tests/test_predictive_social.py -q` | 51 passed |
| 9 | Recorded run on copies | `run_social.py /tmp/claude-0/p10b/out --dev-store ... --feature-store ...` | exit 0, stores unchanged, 0 socket events; 35 of 37 outputs byte-equal to `run_log.json`; `FORECAST_TRACE.json` differs by latency only; `traps.json` differs only in the CX-10 trap's newest-export counts because my clone's `origin/main` is `98338a8`, not `e245d91` (expected) |
| 10 | Trace verifier, OOS recompute, sklearn oracle | the three probes | 0 differences; 456 values, 326 numbers; max coef diff 1.9e-11 |
| 11 | Pre-registration and freeze order | `git log`, `git diff c3f04c8 HEAD -- checklist registry`, sha256 of `code_sha256` files at `0784a9a` | c3f04c8 23:58:29Z < 0784a9a 00:20:46Z < run 00:20:50Z to 00:21:52Z < f4b3a89 00:30:50Z; checklist and registry unchanged since c3f04c8; all 11 code hashes equal `0784a9a`; only `recompute_oos_social.py` and the 51st test were added after the run (disclosed) |
| 12 | Phase mutation probe | `mutation_social.py` | 85 applied, 85 caught |
| 13 | Own mutations | `p10b_own_mutations.py` (18 mutants) | 16 caught; 1 equivalent (track record without `called_at < T`, implied by `matured_at <= T`); 1 real survivor (MINOR m3) |
| 14 | Full suite at HEAD | `python -m pytest tests -q --deselect <known>`; known test run alone | 1330 passed, 1 deselected; the known clock test fails alone as recorded; stray `data/reports/..._BRETT_0x532f.md` removed by hand (as recorded) |
| 15 | Guard, seal, release audit | `python -m memelab social guard`; `check_seal.py`; single-branch clone at 564be76 `tools/release_audit.py --history` | 0 violations; 0 problems; exit 0, "Needs action: no." |
| 16 | Read-only adapter | `p10b_counterexamples.py` | write refused ("attempt to write a readonly database"); dev store and tracked lab DB refused |
| 17 | TEST_ONLY honesty | grep of card, evidence, metrics | 306 metric rows all INSUFFICIENT_*; 18 ablation rows, `incremental_value_claimed False`; no probability, verified catalyst, promotion or frozen catalyst target claimed; `revision_check_claimed: false` |

## Findings

### MATERIAL

M1. A VERIFIED catalyst's availability can precede its verification, and the follow-through proposal can label a move from before the decision (counterexample CX-10b-A). `classify_catalyst` sets `available_at = max(first sighting of any item, linked_at)` (socialcat.py, `avail = max([first_seen] + ...)`). It ignores the time the evidence became CONFIRMED and the time the official or second independent item arrived. Case: rumor item at T-3000, link at T-2900, official item and the CONFIRMED revision at T-600 (the lab writes these together, ingest.py:282-290). At T the state is VERIFIED with `available_at` T-2900; asked at T-1000 the same event is UNVERIFIED_EVENT. `proposed_follow_through_label` starts at `available_at + lag`, never at the decision, so a +30% move at T-1500 (before verification and before the decision) is labelled TARGET_FIRST 1. `test_verified_needs_exact_mint_in_source_...` asserts this rule ("later of first sighting and the link"), so no test can catch it. Fixture-only today, but PI-D-058 item 4 and `CATALYST_TARGET_PROPOSALS.md` carry it to later phases as "the first price a reader of the catalyst could act on", and the phase prompt asks for a conservative availability. Repair: available_at = max(linked_at, time of the CONFIRMED evidence by T, first_seen of the item that completed the official-or-two-sources rule); label start = max(available_at, decision time) + lag; add the CX test.

M2. The social adapter applies a later suspension or bot label to every past decision (counterexample CX-10b-B). `social_as_of` excludes accounts whose current `identity_status` is SUSPENDED without checking `identity_checked_at <= T`; `registry.set_account_status` updates that row in place with the check time. An account VERIFIED at T-1 d whose exact-mint post was ingested at T-2900, suspended at T+1 d: at T the truncated view gives `sx_mentions_exact` 2, `sx_bot_share` 0; the store read later gives 1 and 0.5. `account_kind` BOT has no timestamp at all, so a later BOT label also applies at every T. That is post-decision information in the path PI-D-058 names as the only social entry, and P16 hindsight in its purest form (accounts that get suspended after a pump). The checklist rule ("SUSPENDED identities are excluded") has no as-of qualifier and no test covers it. Repair: SUSPENDED only when `identity_checked_at <= T`, otherwise the state known at T; BOT kind only from a timestamped registry record, else UNKNOWN_AS_OF reported apart.

### MINOR

m1. The provenance inventory misses adjacent lab rows that name decision mints. (a) `data/memelab.sqlite` `social_snapshots`: 99 rows, Jupiter `holder_change_1h/6h/24h`, 8 mints that carry 216 of the 1,518 dev-store decisions, observed 2026-10-06T23:48Z to 10-07T00:16Z, committed 01:12Z, at least 21.6 h before the first of those decisions. (b) The export's `upcoming_launches` (official links, `social_json` with a DEX Screener profile flag), `launch_cohort` and `launch_monitor` name 24, 38 and 18 decision mints. 52 Solana decisions have an `upcoming_launches` row in their own export, with telegram links on 5, twitter on 9 and website on 16 that the token row lacks, so "telegram 0 of 925" is true of token rows only. (c) Inbox reads beyond `cat01`/`catm01`: DEX Screener boosts in `eco01.json` and `lp_t1_pump.json` name 2 more decision mints (3 in all), and 46 tracked inbox files name decision mints by exact address before decisions (provider metadata such as socials and telegram handles). None is a social item, observation, claim or catalyst event, the omissions are conservative, and no Phase 10 number depends on them. Phase 00 DATA_COVERAGE already lists `social_snapshots`. The provenance should name them so a later phase does not read "no social row" as "no social-named table".

m2. `sc_attention_paid` and `sc_attention_suspect` are documented as "paid boost" (card line 19, provenance P16 row). In the lab, "attention paid/boosted" means m19's `organic` is False, which is `organic_score < 40` or an active boost (m19_attention_analysis.py:77). Most of the 150 readings are low-organic-score tokens, not boosts.

m3. Surviving mutant: removing `float(v["first_recorded_at"]) <= Tq` from the item-version filter in `social_as_of` passes all 51 tests. An ORIGINAL version recorded after T would then count at T (P03 variant). Add a test.

m4. `recompute_oos_social.py` is independent code, but it takes features from the committed CSV and fits from the committed cards. The G1 stump fits have no oracle. Check 6 covers the feature part; the evidence should scope "independent recomputation of every out-of-sample number" to predictions from cards.

m5. Classifier edges (fixture-only): a missing role defaults to ORIGINAL (counted as independent); an OFFICIAL link is reported as TICKER_OR_NAME_ONLY; identity may come from a non-official independent item while CONFIRMED comes from an official item that never named the mint (allowed by the PI-D-057 item 3 wording; match.py's own rule asks the event's source to state the mint for OFFICIAL).

m6. `traps.json` reproduces byte-equal only when `origin/main` is at the phase's `e245d91` (the CX-10 trap counts the newest export). The packet says only the trace differs.

## Counterexample (new): CX-10b-A, and CX-10b-B

Script: `/home/claude/pi_orchestration/skeptic/p10b_counterexamples.py` (output `p10b_counterexamples_out.json`). CX-10b-A: a rumor that an exchange will list a mint is seen at T-3000 and linked by exact mint at T-2900. The exchange's own notice arrives and the evidence becomes CONFIRMED at T-600. `classify_catalyst` at T says VERIFIED with `available_at` T-2900, though at T-1000 it said UNVERIFIED_EVENT. The follow-through proposal then scores a +30% move at T-1500 as a catalyst follow-through success: the move happened before the catalyst was verified and before the decision. Nothing in the phase catches it, because the test asserts this availability rule. CX-10b-B: a mention account suspended a day after T is removed from the features at T (mentions 2 to 1, bot share 0 to 0.5). No test or check catches either.

## What was not checked

The Phase 06 48 h revision re-read (open, not a Phase 10 defect; nothing in Phase 10 claims it). I did not refit G1 stumps independently.
