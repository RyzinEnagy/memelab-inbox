# Phase 00 independent skeptic review

| Item | Value |
|---|---|
| Phase reviewed | predictive-intelligence Phase 00, "authoritative repository baseline" |
| Commits reviewed | `59a2cfc` (content) and `dea735c` (hash record) on `feature/predictive-intelligence`; baseline `f99c6c7` |
| Reviewer clone | `/home/claude/pi_orchestration/skeptic_00` (clone of the local repo plus `git fetch` of every GitHub branch and `refs/pull/*`); temp databases only |
| Time (UTC) | 2026-10-24T00:52Z to 01:08Z |
| Spend | 0 (one free GeckoTerminal call) |
| Inputs read | SKEPTIC_PACKET.md, PHASE_BRIEF.md, all Phase 00 baseline files, evidence, results JSON, the four probes, package references ADVERSARIAL_SCENARIOS.md and BACKTEST_V12_BRIDGE.md |
| Check script | `/home/claude/pi_orchestration/skeptic/skeptic_00_checks.py` (read-only, sha256 `ff93477c5c77f8bb53373ec24a396da72acea5bc73923cee9dc2df9d769ea841`) |

## Verdict

Material failure found (one). The baseline is mostly sound: branch map, main code identity, test counts, lineage reproduction, P34, P01 core result, P41 result and most data numbers reproduce from git and code. But the clock table states a wrong meaning for the only wall-clock column the lab stores, and that hides a measurable decision lag that later phases need. One count error (launch-cohort outcomes) comes from a probe bug that makes the oldest row of each mint win. Both are doc fixes; no code change is needed. Phase 00 should not be marked PASS until the clock row and the launch numbers are corrected.

## Checks run

| # | Check | Command (in the reviewer clone unless stated) | Result | Holds? |
|---|---|---|---|---|
| 1 | Remote refs and PRs | `git ls-remote https://github.com/RyzinEnagy/memelab-inbox.git` | 6 branches with the tips REPO_MAP lists; `refs/pull/1/head` 629d402 with no merge ref (closed or merged), `pull/2` = 3b434e1 and `pull/3` = 2605b5f with merge refs (open). `feature/predictive-intelligence` not on GitHub yet (expected, orchestrator pushes) | yes, and PR state is now confirmed from git, not only docs |
| 2 | Merge bases and only-on counts | `git merge-base`, `git rev-list --count` for each branch against `f99c6c7` | main mb f084b60, 11/12; social 3f27fc7, 0/3; firecrawl 0/0; audit 3/12; remediation 18/12; verification 22/12 | yes, every number matches REPO_MAP |
| 3 | Ancestry | `git merge-base --is-ancestor` f084b60, 3f27fc7, 698f73b vs f99c6c7 | 0, 0, 1 | yes |
| 4 | Main runs f084b60 code | `git diff --stat f084b60 origin/main -- memelab tests tools bridge skills docs` (empty); `git diff --name-only f084b60 origin/main` (only `data/state/latest.json`) | main code = f084b60 | yes (git fact) |
| 5 | Scheduled runs execute main | key set of `origin/main:data/state/latest.json` (2026-10-23 export) | exactly the 19 tables of `state.py` TABLES at f084b60; no `catalyst_page_fetches` (added to state.py in 5bfb4f3). `state.py` is identical at f084b60 and 3f27fc7, so the export proves "pre-5bfb4f3 state.py", not f084b60 exactly | consistent; the rest rests on FIRECRAWL.md "Scheduled runs" and SKILL.md:33 (collector JS loaded from main's raw URL) |
| 6 | Test collection | `python -m pytest tests -q --collect-only -p no:cacheprovider` | `786 tests collected`; per-file counts identical to COMMIT_AND_TEST_LOG; 660 in test_social_*.py | yes |
| 7 | Full suite at dea735c | `MEMELAB_DB=<scratch> python -m pytest tests -q -p no:cacheprovider` | `1 failed, 785 passed in 132.13s`, exit 1, only `test_dedup_corroboration_resurface_denial` (tests/test_catalyst.py:44) | yes |
| 8 | Strays and tracked DB | `git status --porcelain --ignored`; `sha256sum data/memelab.sqlite` before and after | `data/reports/<stamp>_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`; DB sha256 068287c0...a6679ca unchanged; strays removed, clone clean | yes |
| 9 | Untested paths | `grep -l` over tests/ for record_outcomes, previous_thesis, compact_snapshot, launchpad_stats, followup_mints, `persist=True`, `state.export` | none, none, none, none, none, only test_evm.py, only test_catalyst_firecrawl.py | yes |
| 10 | Lineage probe | `python3 audits/.../probes/lineage_reproduction_probe.py` | stored 48/REJECTED/4 pools; A 47/DISTRIBUTION RISK/18/LOW; B 48/REJECTED/18; C (b6c424d) 48/REJECTED/4, 442 = 442 non-blank lines equal; clone status empty | yes |
| 11 | HIGGS input clocks | `_at` of each `data/inbox/*.result.json` | s2_01 23:25:47Z (jup_tok, rug for HIGGS), deep02 23:59:10Z (gt_*, jq, rpc for HIGGS), deep04 00:16:35Z (3 keys, none for HIGGS) = t. Extra: forensics01 has the same `_at` as deep03 to the millisecond, so `_at` is not per-file fetch time either | yes |
| 12 | Tracked SQLite counts | read-only copy, `SELECT COUNT(*)`, min/max of time columns per table | all 20 table counts and time ranges in DATA_COVERAGE match (e.g. market_snapshots 33, pool_snapshots 182, wallet_transactions 3,774 over 6 mints, theses 33) | yes |
| 13 | Main export counts | parse `origin/main:data/state/latest.json` | tokens 984 (solana 937, bsc 28, ethereum 13, base 6); theses 701, 248 mints, 104 with 2+; rejections 1,013 (400/342/271) | yes |
| 14 | History union | own script over all 89 export versions (`git log origin/main -- data/state/latest.json`) | 89 commits, per-day cadence as stated; 1,801 snapshots, 248 mints, per-mint histogram 144/42/36/26; 93 mints with 2+ priced; span p50 120 h, p90 330 h, max 394 h; 989 distinct tokens; 102 upper-case symbols with 2+ mints (PLAGUE 5); 640 rejected mints | yes |
| 15 | Launch-cohort outcomes | `skeptic_00_checks.py` | 1,422 mints; mcap_24h 19, mcap_7d 8, mcap_30d 2 (newest row = any version); the phase's 8 / 3 / 0 is reproduced exactly only by keeping the OLDEST row per mint | no, see F2 |
| 16 | Inbox OHLCV | parse `inbox/*.json` | 128 `gt_ohlcv` keys, 125 with candles, 33 pools; 40 tracked JSON files in all, 2 of them plans in `inbox/plans/` | counts yes; "40 (+2 plans)" should read "40 including 2 plans"; my per-series medians (day1 18, hour1 266.5) differ from 22 and 300, method not recorded |
| 17 | GeckoTerminal depth | one `curl` of the HIGGS pool day OHLCV | HTTP 200, 17 candles 2026-10-04 to 2026-10-20 | yes |
| 18 | Anchors, FEATURE_TRACE | `sed -n` at cited lines | ingest.py:24, :89; cli.py:44, :120, :138, :181, :226, :252, :350, :397; pipeline.py:26, :116, :156, :187; db.py:18, :141, :171, :271, :323; normalize.py:59; plan.py:60, :92; report.py:29, :235; state.py:21, :45, :48, :70, :77; collector.js:79, :86 | all correct (run() starts at :84, cited as :85-86) |
| 19 | Anchors, inventory | `sed -n` | m24 :41, :44, :478, :494, :569, :592, :625; m14 :140; m16 :177-178; m25 :8, :43; m27 :62; m28 :276; m20 :12; catalyst monitor :64, match :109, assess :176, schema :136; launch cohort :31, :104, discover :298, :383; outcomes_core :120, :378; outcomes_ledger :45; replay_core :104, :457, :700, :719, :1013, :1067; replay_sources :28; alpha_core :125; identity :456; firecrawl :679; regime :45 | all correct |
| 20 | record_outcomes semantics | read catalyst/monitor.py:64-82 | first market snapshot at or after the horizon, no maximum wait | yes |
| 21 | P34 | `git ls-tree -r` and `git grep -i -E 'backtesting|stress[- ]test|BACKTEST_NOT_AVAILABLE|walk[- ]forward'` on every branch and PR head; `git log --all -i --grep`; `ls /mnt/user-data/uploads`; project knowledge search | no backtest or stress paths anywhere; grep hits on audit branches are only "stress tests" wording in social audit notes; no commits; uploads hold only the predictive package; project search returns social docs only | yes, BACKTEST_NOT_AVAILABLE |
| 22 | P01 probe | `python3 audits/.../probes/p01_ticker_identity_probe.py origin/main` | 984 tokens = 984 mints; 101 symbols, 261 mints; 701 theses, 0 orphans; join by mint 701, by symbol 970; impostor link TICKER_MATCH / MODERATE | yes, but incomplete, see F3 |
| 23 | P41 probe | `python3 audits/.../probes/p41_untrusted_page_probe.py` | only identifiers kept, no instruction words, no key shape, no `javascript`; attacker string is a valid pubkey and is kept as CONTRACT. The "match.py then links it STRONG" step is read from code (match.py:145-148), not executed | yes |
| 24 | Inventory completeness | `grep -rl -i` over memelab/ tools/ bridge/ for forecast, predict, probabilit, calibrat, outcome, horizon, hit/win rate, expectancy, survival, base rate, simulat, polyfit, label, replay, backtest, precision/recall, percentile, kelly | no calibration, regression or ML anywhere (confirms headline); two items missing, see F4 and F5 | mostly |
| 25 | Clock of tokens.first_seen_at | read db.py:254-255, :288-299 and pipeline.py:197; tracked DB and all 89 exports | `upsert_token` stamps `db.now()` = `time.time()`, not `t` | no, see F1 |
| 26 | Artifact hashes | sha256 of every path in PHASE_00_RESULTS.json `artifacts` at dea735c | 0 mismatches; `git diff --name-only f99c6c7..dea735c` is 18 files, all under the two predictive namespaces | yes |

## Findings

### F1 (MATERIAL): the clock table gives the wrong clock for tokens.first_seen_at and last_seen_at, and misses the decision lag it reveals

- DATA_COVERAGE.md "Clocks" says `tokens.first_seen_at / last_seen_at | t at upsert | db.py:288-300`; the tracked SQLite table says "first_seen_at, last_seen_at (run time t)", and REPO_MAP repeats it.
- Code: `db.upsert_token` sets both from `db.now()` (db.py:254-255, `return time.time()`), the processing wall clock. `t` (max collector `_at`, cli.py:44) is used for every other persisted time in `persist_result`.
- Data: in the tracked DB, all 8 tokens with theses have `first_seen_at` 6.2 to 9.6 minutes AFTER their first thesis `created_at` (HIGGS: first thesis 23:59:10Z, first_seen_at 00:07:47Z; every token's last_seen_at is 00:20:33Z, so the HIGGS thesis stamped 00:16:35Z was written at about 00:20:33Z). Over all 89 main exports, 149 of 248 mints with theses have their earliest first_seen_at after their earliest thesis, median 16.9 min, p90 28.7 min, max 116.5 min (`skeptic_00_checks.py`).
- Why it matters: `upsert_token` runs in the same transaction as the thesis insert (pipeline.py:197, then the theses insert at pipeline.py:243), so first_seen_at is a lower bound on when the first thesis row was written. `theses.created_at` is therefore earlier than the moment the score and status existed, by at least 17 minutes for the median late mint. No other column stores a write time. Combined with FEATURE_TRACE gap 2 (inputs up to about 50 minutes older than `t`), a thesis's inputs can be over an hour old when the thesis appears. A universe filter "first_seen_at <= cutoff" would also drop mints that already had theses before the cutoff.
- Fix: correct the Clocks row (wall clock of first and latest persist, not `t`) and add the decision-lag measurement to DATA_COVERAGE and to the Phase 01 inputs.

### F2 (MINOR, count error from a probe bug): launch-cohort outcome counts are 19 / 8 / 2, not 8 / 3 / 0

- DATA_COVERAGE (summary and history table), EXISTING_PREDICTION_INVENTORY and PHASE_00_EVIDENCE say 8 launches have mcap_24h, 3 mcap_7d, 0 mcap_30d. The newest row per mint and "any version" both give 19, 8 and 2; main's latest export alone has 19, 8 and 1.
- Cause: `state_history_probe.py` walks `git log` newest first and does `cohort[c["mint"]] = c`, so the oldest copy of each row (before outcomes were filled) wins. Keeping the oldest row reproduces 8 / 3 / 0 exactly.
- The conclusion "nearly empty" still holds (19 of 1,422; below cohort.py MIN_N 20). Classed MINOR because no decision changes, but the probe pattern must not be reused to build labels: it systematically picks pre-outcome rows. `rug_flag` is NULL in every row, never 0 or 1 ("never 1" is true).

### F3 (MINOR): P01 analysis misses a second symbol-only path

- PHASE_00_EVIDENCE says "One existing path links by ticker: the catalyst matcher". catalyst/monitor.py:45-50 also raises a DETERIORATION alert, keyed by mint, on every watched or linked token whose symbol appears in an unlinked NEGATIVE event title (`norm_tokens(e["title"])`); with 10 XMR mints on record, one headline would alert all watched XMR mints. The alert text says "verify it is the same asset", and catalyst tables are not exported, so there is no real data affected yet. PI-D-007 covers links only; it should also exclude `catalyst_alerts` of this kind from identity, features and labels. The matcher also writes the impostor's symbol into `tokens` (match.py:166, `COALESCE`).

### F4 (MINOR): inventory omits the social claim records that are themselves forecasts

- memelab/social/extraction.py:49-51 and social/schema.py:579 store per-claim `assertion_type` ('prediction' among others), stance and `time_horizon` (intraday ... long_term). These are external forecasts with a horizon, the natural input for Phase 10. Not listed in EXISTING_PREDICTION_INVENTORY.

### F5 (MINOR): silent module failure is not recorded on the thesis

- pipeline.py:19-23 `_safe` turns a module exception into an `unknowns` line. The theses row (score, breakdown, fatal flags, snapshot_json) keeps no failure flag, and report files are not kept by the scheduled runs, so a stored score computed with a crashed module cannot be filtered out. Worth adding to FEATURE_TRACE gaps (it is a sibling of gap 1).

### F6 (MINOR, wording and definitions)

- Gap percentiles (p10 0.12 h, p50 0.93 h, p90 23.8 h) are over all snapshots of the 93 priced mints, priced or not; over priced snapshots only they are 0.24 h, 1.05 h, 24.1 h. "Last seen more than 72 h before the last export" is computed against the last thesis time (58); against the last export time it is 60.
- REPO_MAP calls top-level `bridge/` "older copies of the JS collectors". The six shared files are byte-identical to memelab/bridge/, and SKILL.md:33 and tools/direct/direct_refresh.py load `bridge/*.js` from main's raw URL at run time, so these are the live collector copies for the browser and direct routes.
- "40 (+2 plans)" for inbox/: 40 tracked JSON files in total, 2 of them plans.
- REPO_MAP and FEATURE_TRACE cite `bridge/collector.js:85-86 run()`; run() is at :84.

## New counterexample (not P01 to P48)

Claim, plausible and wrong: "`theses.created_at` is the decision time. A Phase 06 label can enter at the first price after `created_at` plus the outcome engine's 300 s execution lag (outcomes_core.py:46, the reuse rule the inventory proposes), and `tokens.first_seen_at <= cutoff` tells which mints the lab knew at a cutoff." The thesis did not exist at `created_at`: `created_at` is the start of the newest collector run (cli.py:44, collector.js:86), and the row is written later. The only wall-clock trace is `tokens.first_seen_at` (db.now(), set in the same transaction), which is after the first thesis for 149 of 248 mints by a median of 16.9 min and up to 116.5 min, and for 8 of 8 tokens in the tracked DB. So a 300 s lag places the simulated entry before the score existed for at least half of those mints, a "1 h" label contains up to 2 h of movement the lab had not yet reacted to, and the cutoff filter drops tokens that already had theses. This is not P06 (candle close) or P36 (feature after available_at): it is the decision record stamped earlier than its own creation, hidden by a clock column the baseline documented as `t`. Nothing in Phase 00 catches it; outcomes_core's LATE_CAPTURE check cannot fire because theses store no capture time. The catching check is `skeptic_00_checks.py` section 2 (or the SQL `SELECT COUNT(*) FROM tokens k JOIN (SELECT mint, MIN(created_at) c FROM theses GROUP BY mint) t USING(mint) WHERE k.first_seen_at > t.c` on an imported export), which should become a fixture test in Phase 05 or 06.

## Process notes

- During the first suite run I mistakenly ran `git checkout f99c6c7 --` in the reviewer clone, which switched its tree from dea735c to f99c6c7 mid-run (only predictive docs and audits differ). That run also ended `1 failed, 785 passed in 131.77s`. I re-ran the suite cleanly at dea735c (check 7) and use that result.
- In `/home/claude/memelab-inbox` I ran only read commands (`cat`, `git log`, `git branch -v`) and one `git status --short` at the start; `git status` can refresh `.git/index` stat data. No tracked file there was changed.
- The reviewer clone was left clean at dea735c.
