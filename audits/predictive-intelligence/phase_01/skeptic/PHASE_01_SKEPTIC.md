# Phase 01 independent skeptic review

Reviewer: independent skeptic run by the orchestrator (PI-D-013), fresh context. Date 2026-10-24 (UTC).
Clone: `/home/claude/pi_orchestration/skeptic_01` at `0decbbe` on `feature/predictive-intelligence` (origin/main `98338a8`, same as the inbox checkout). Nothing was written inside `/home/claude/memelab-inbox`.
Scripts written for this review (all next to this file): `skeptic_01_universe.py`, `skeptic_01_revisions.py`, `skeptic_01_gt_check.py`, `skeptic_01_mutations.py`, `skeptic_01_counterexample.py`; outputs `skeptic_01_universe.json`, `skeptic_01_revisions.json`, `skeptic_01_gt_check.json`, `skeptic_01_mutations.txt`, live bodies in `gt_live/` and `gh_live/`.
External calls: 2 GeckoTerminal (02:06:35Z and 02:06:47Z, 12 s apart), 1 GitHub REST (`/repos/RyzinEnagy/memelab-inbox/activity`, 02:07Z). No Firecrawl, no paid call.

## Verdict

Material failures found: 3, all definitional and repairable before any label exists. The phase's numbers re-derive exactly, the GeckoTerminal coverage claims hold, the suite result reproduces and the new code is isolated. The failures are in what the frozen rules say (thesis identity behind the decision time, how much of the acceptance plan is actually frozen, and how vendor gaps are classified), which later phases would inherit.

## Checks run

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Full suite | `MEMELAB_DB=<tmp> python -m pytest tests -q -p no:cacheprovider` (clone) | `1 failed, 806 passed in 137.49s`; only `test_catalyst.py::test_dedup_corroboration_resurface_denial` (known). Matches the phase |
| 2 | Contract tests | `python -m pytest tests/test_predictive_contract.py -q` | `21 passed` |
| 3 | Independent universe and split counts (own code, `git rev-list --first-parent`) | `python skeptic_01_universe.py origin/main skeptic_01_universe.json` | 89 exports, 1,801 theses, 248 mints (201 Solana, 6 base, 28 bsc, 13 ethereum); thinned/matured 6 h 366/359, 24 h 278/252, 7 d 213/136; splits T1 177/17/58/26, T1b 280/0/79/7, T2 161/33/49/35, 7 d 75/61/0/77. All equal the phase's numbers |
| 4 | Clock statistics (own code) | inline script | commit minus created_at p50 11.59, p90 28.72, max 1,325.52 min, 0 negative; first-thesis write lag n 149, p50 16.92, max 116.50 min. Equal the phase's |
| 5 | History shape | `git log --merges`, `--full-history`, first-parent monotonic check | 1 merge on main (`f084b60`), its latest.json equals the first parent's; `--full-history` adds only that merge, no thesis; commit times monotonic on first parent |
| 6 | Force pushes | every main push event: `git merge-base --is-ancestor before head` | 206 of 206 fast-forward; no rewritten history in the window |
| 7 | The 7 unconfirmed exports | containing push per commit (`before` ancestor of commit, commit ancestor of `head`) plus GitHub `/activity` | see finding M1 |
| 8 | Registry pre-registration | `git archive b6f2621 memelab` then `registry_sha256()`; diff TARGETS/ACCEPTANCE b6f2621 vs HEAD | `dd3b4576...` at b6f2621, `9f8c9deb...` at HEAD; CC-01 changed only `reference_price`, `thinning`, added `gap_rule`; ACCEPTANCE unchanged |
| 9 | GeckoTerminal bodies vs recorded hashes | `sha256sum /home/claude/pi_orchestration/phase01/gt_raw/*` | all 15 match `gt_coverage_sample.json` calls |
| 10 | GeckoTerminal coverage recomputed (own code, CC-01 rule) | `python -I skeptic_01_gt_check.py <gt_raw> gt_live <sample>` | all 9 HTTP 200 OHLCV bodies agree on candle count, reference candle, 24 h path count and max gap |
| 11 | GeckoTerminal retention and revision, live | 2 paced re-reads of the phase's exact URLs | ioaDGk (decision 2026-10-07T21:53Z): 870 of 870 candles identical, oldest candle 2026-10-06T19:55Z still served on 10-24; AVaw6h: 1,000 of 1,000 identical (about 30 min after the phase's read) |
| 12 | Power arithmetic | `python audits/.../probes/power_simulation.py` | reproduces the table (0.10 at n 50: 0.24; 0.20 at n 50: 0.45; at n 150: 0.53 and 0.86) |
| 13 | Thesis key identity across exports | `python skeptic_01_revisions.py origin/main skeptic_01_revisions.json` | see finding F1 |
| 14 | Validator on forbidden documents (unmutated code) | inline script | rejects p = 1.2 (even with interval [1.0, 1.4]), p = NaN (also from JSON), ABSTAIN with p 0.4 / NaN / 0, FORECAST with cutoff None, missing or without Z. Accepts the cases listed in M3 |
| 15 | Mutations the phase did not try | `python skeptic_01_mutations.py <clone>` | 10 of 12 survive (finding M2) |
| 16 | Acceptance text freeze | 5 loosening edits to ACCEPTANCE_METRICS.md in a temp copy, then contract tests and `check_doc_anchors.py` | `21 passed`; `anchors 34, problems 0` (finding F2) |
| 17 | Isolation | grep for imports, `pkgutil`, `import_module`, `__import__` outside `memelab/predictive`; `git diff --stat 94be1bf..HEAD -- . ':!audits' ':!docs'` | nothing imports or loads the package; only 4 non-doc files added; no tracked inbox/state/data change |
| 18 | Gap matrix VERIFIED_PRESENT cells | read code behind each of the 16 | see finding M4 |
| 19 | Liquidity follow-up figure | inline script, events deduplicated per the registry's own rule | 30 of 278 events (53 of 351 counts thesis rows) |
| 20 | Universe filter statement | inline script over first-export Solana priced theses | 156 of 1,006 below "liquidity at least $20k, 24 h volume at least $50k"; 99 with 24 h volume under $1k |

## Findings

### F1 (MATERIAL) The decision time is attached to a key that is not a point-in-time identity

PI-D-015 and the registry define the historical decision time as the commit time of the first export holding the thesis row `(mint, created_at)`, justified by "the row is inside the commit, so the thesis existed by then". But `created_at` is the collector-run start (PI-D-011), so several analyses of one mint from one input share the key, and `state.import_` keeps whichever row comes first in file order.

- 122 keys hold two or more distinct rows inside their first export: 18 with conflicting `status`, 7 conflicting `fatal_flags_json`, 43 conflicting `score`, 34 conflicting snapshot `price`. 132 keys are duplicated inside some export (20 exports).
- 19 of the 278 thinned 24 h decisions (20 of 366 for 6 h) are such keys, 3 with conflicting status. Example: `6GmAFSYs...` key `1791394883.462` in `996190ce` holds both `REJECTED`, score 0, fatal `IDENTITY_NOT_VERIFIED` and `WATCH`, score 56.
- 3 keys gain rows after their first export (26.7 min later, `996190ce`, the merged export). For `6GmAFSYs...` key `1791331150.554` the first export `15c2087e` (2026-10-07T21:53:55Z) holds one row, `SETUP DEVELOPING` 69, no fatal flag; `996190ce` adds `REJECTED` 60 with `CLUSTER_OWNERSHIP_GT_25PCT`, and every later single-row export carries only the REJECTED row.
- The registry's tie rule ("theses of one mint that share a decision time count once, as the newest created_at") is undefined when the created_at values are equal. The probe happens to take the first row of the first export, which is point-in-time correct, but no document says that and no test checks it. Features B1 (status group), B2 (fatal flag present) and B3 (score) depend on the choice.

Effect: a Phase 05 loader that keys on `(mint, created_at)` through the existing import seam (PI-D-017 says reuse first) attaches a 21:53Z decision time to a REJECTED/fatal row that first existed at 22:20Z: look-ahead in a fatal-flag feature, and an arbitrary pick among conflicting rows for about 7% of 24 h events. Repair: identity is `(mint, created_at, sha256 of the row)`; decision time is the first export holding that exact row; a written, deterministic rule for keys with several rows in one export (for example one event, the first row of the first export, conflict flagged, plus a sensitivity run excluding conflicted keys); a fixture test on the `6GmAFSYs...` case. Counterexample CX-S1 below.

### F2 (MATERIAL) Only part of the acceptance plan is frozen; the pass/fail rules can move without any check failing

ACCEPTANCE_METRICS.md says "The numeric constants are in `contract.ACCEPTANCE` and are covered by the registry fingerprint". The fingerprint covers TARGETS and nine constants (training and holdout minimums, bin minimum, display range, holdout window, prospective start, model age). It does not cover the rules that decide whether anything is published or promoted: the 95% Wilson calibration tolerance, quantile bins of at least 20 and at most 5, the under-40-events rule, SHADOW (BSS point estimate at least 0), VALIDATED_EXPERIMENTAL (BSS lower 95% bound above 0, Holm across three, not worse than B2), Brier as primary score, day and mint block bootstrap, the 5-decision-day minimum, the first walk-forward fold date 2026-10-11, the baseline list, the API limits (6 a minute, 1,200 a run, breaker after 5) and the 10% AMBIGUOUS_BAR sensitivity trigger. Check 16: five loosening edits (Wilson 95% to 99.9%, Holm lower bound to point estimate, bins to a single bin, 5 days to 1, first fold 10-11 to 10-15) pass every test and checker. These texts were first committed in `e64c6ca` (01:56:38Z), after the coverage probe had read ten price bodies (01:36Z to 01:38Z), two of them holdout decisions; the pre-registration commit `b6f2621` held only `contract.py`, the checklist and the universe probe. I found no sign the criteria were tuned to those bodies, but the "fixed before outcome data" claim is provable only for the nine constants. Repair: move every acceptance criterion into `ACCEPTANCE` (recorded as change control CC-02) or pin the sha256 of ACCEPTANCE_METRICS.md and TARGET_REGISTRY.md in the test, and correct the sentence.

### F3 (MATERIAL) Eligibility turns vendor and route gaps into "no recent trade" and drops them silently

The registry says INELIGIBLE_NO_RECENT_TRADE is "decided only from data available at the decision". Historically it is decided from a backfill read today (the registry itself says a backfill read is not history, P04, P07). A pool the vendor no longer serves, or a vendor-list pool that is not where the mint traded, yields no reference candle and the decision leaves the sample uncounted. DEPENDENCY_GRAPH.md ("Price source" gate) says the opposite: retention loss makes labels censored and counted. The censored rule needs "a reference trade existed before entry", which no stated test establishes; with one request spanning the reference hour and the path it can hardly occur. In the sample, 4 of 9 resolved decisions were ineligible, the largest effect on the sample; one of them (`CqjaL6...`, BAT, CURRENT_VENDOR_LIST, raydium-clmm pool with 57 candles over about 13 days) had a lab-recorded 24 h volume of $94,115 at the decision, so "no recent trade" is not established. If delisted or unserved pools are disproportionately rugs, T2 prevalence is biased down and the conservative lens never sees them. Repair: decide market inactivity from the thesis snapshot's own as-of volume and liquidity together with the vendor read; split the class into MARKET_INACTIVE and VENDOR_OR_ROUTE_GAP; count the latter as censored with the conservative lens; make the registry and dependency graph agree (change control, before any label).

### M1 (MINOR) The 7 unconfirmed export times are misdescribed

Evidence and RESULTS say the 7 exports without a push event are "before 2026-10-08T14:04Z". Three are the newest: `6e09bfae` (10-21), `1aa6fcd1` (10-22), `98338a8b` (10-23), first exports of 77 theses and of 9 of 58 T1 and 28 of 79 T1b holdout events. The events API returned no push after 2026-10-20T10:24Z. GitHub `/activity` (`gh_live/activity_main.json`) shows those three pushed 2 s after commit, so they are confirmed by another source. Of the other four, `2c6cbf54`, `53a616e1` and `fe8fc3bb` (56 theses) reached GitHub in a later push 413 s, 3,609 s and 6,269 s after their commit time, so commit time is not "the provable public availability time" (probe docstring, PI-D-008 wording) for them; it remains an existence bound if the committer clock was right. `996190ce` (26 theses, the merged export) has no containing push. "291 push events back to 2026-10-08T14:04Z": main pushes in the file span 2026-10-07T14:08Z to 10-20T10:24Z. No force push and no rebase was found (checks 5 and 6), which the phase did not test.

### M2 (MINOR) Several contract rules are not pinned by any test

The unmutated validator rejects the four bad forecasts named in the task. But in check 15 these mutations survive with `21 passed`: range check removed from `_num01` (the P38 test passes on the message "probability lies outside its uncertainty_interval", so p = 1.2 with interval [1.0, 1.4] would pass validation), bool accepted as a probability, `training_cutoff_utc` no longer required, `model_sha`/`feature_set_sha`/`data_snapshot_sha` no longer required, ABSTAIN allowed an interval, ABSTAIN allowed NaN or 0 probability, `generated_at` before the decision allowed, `base_rate` range check removed, and the isolation test fooled by `from memelab import predictive` or `importlib.import_module("memelab.predictive.contract")`. Caught: forbidden-key removal, calibration `passed` ignored. Repair: one assertion per rule on its exact message, a separate range test with a wide interval, and an import check on the AST (`ImportFrom` with module `memelab` and name `predictive`, relative imports, `import_module` strings).

### M3 (MINOR) The validator accepts documents the contract text rules out

Accepted by the current code: a FORECAST whose model is 111 days older than the decision (`max_model_age_s` is frozen but not enforced; MODEL_STALE exists only in docs); a self-reported `training_cutoff_utc` of 10-16 while the model was trained to 10-22 (the model card has no cutoff, so P13 rests on the forecast's own claim); a mint with a trailing newline (`_B58` uses `$`, which matches before "\n", and the forecast_id then differs from the canonical mint's: a P35 duplicate); ABSTAIN with `base_rate` NaN or 7.5, with mint "BONK", or with keys `opportunity_score` and `confidence: 0.93` (FORBIDDEN_KEYS is an exact, top-level match). Repair in Phase 05 or 13; record as known gaps now.

### M4 (MINOR) Two VERIFIED_PRESENT cells overstate the code

`TRADE_OUTCOMES x REPORT_CONSUMERS` cites `m27.store_review` with "post-trade review stored and reported", but nothing outside `tests/test_m21_28.py` calls m27 or m28 (only constants are imported by `social/perf_core.py`); no CLI, pipeline or report consumes `trade_reviews`. That is PARTIAL. `SOCIAL_REPLAY x POINT_IN_TIME_FEATURES` rests on fixtures only and covers social records, not decision snapshots or candles (the seam table itself plans new code for that), so PARTIAL or a fixture-only note in the status is more accurate. `check_gap_anchors.py` checks that a keyword sits on the cited line, not that the status is earned. The other 14 VERIFIED_PRESENT cells hold (spot checks: no network inside `run_modules`; Firecrawl `cap_reason` runs before every attempt at `firecrawl.py:579`).

### M5 (MINOR) "53 of 351" counts rows, not events

The liquidity-degradation figure in TARGET_REGISTRY.md, the fingerprinted `TARGETS["liquidity_degradation_24h"]["why"]` and PI-D-020 counts thesis rows sharing a decision time separately. Deduplicated as the registry requires: 30 of 278 events. The conclusion (DEFERRED) is unchanged; correcting the text changes the fingerprint, so it belongs in the same change control as F1 to F3.

### M6 (MINOR) The universe filter statement is not true of the theses

ACCEPTANCE_METRICS.md describes "one universe filter (stage 1: liquidity at least $20k, 24 h volume at least $50k)". 156 of 1,006 first-export Solana priced theses are below it; 99 have 24 h volume under $1k (all four sampled ineligible decisions are of this kind). The ineligible share will be driven by these.

### M7 (MINOR) Holdout contact before the seal

The coverage probe fetched and processed the 24 h path (candle counts, gaps) of two retrospective holdout decisions (`CnPL1x...` 2026-10-17, `Tm2iq...` 2026-10-19); raw bodies with prices sit in `/home/claude/pi_orchestration/phase01/gt_raw/`. No outcome was computed. The "sealed until Phase 12" statement should say so, and Phase 12 should report holdout results with and without these two.

### M8 (MINOR) Housekeeping

Checklist C10 names `contract/FORECAST_EXAMPLE_FORMAT_ONLY.json`; the file delivered is `tests/fixtures/predictive/forecast_examples_format_only.json`, and an empty untracked `audits/predictive-intelligence/phase_01/contract/` folder remains in the inbox working tree. `decision_universe_probe.py` defaults a missing chain to "solana" (no thesis affected today: 0 theses lack a token row in their first export); Phase 05 should not copy that default. The feature flag gates nothing yet (no code reads `enabled()`), so "unreachable with the flag OFF" holds because nothing imports the package, not because of the flag.

## What held

Event counts, clock statistics, split counts and power numbers re-derive exactly from my own code. The pre-registration fingerprint and the CC-01 diff are as stated. GeckoTerminal coverage recomputes identically from the saved bodies, and two live re-reads match candle for candle, with a 2026-10-07 decision window still served 17 days later. Main has no force push or rebase in the observed window and its first-parent history is linear with monotonic commit times. The validator rejects probability outside [0, 1], NaN, a probability on ABSTAIN and a missing or malformed training cutoff. No existing module imports or dynamically loads `memelab.predictive`; the full suite shows only the known failure.

## Counterexample CX-S1 (new)

Wrong but plausible later-phase step: "build decision records by importing the newest export through the existing `state.import_` seam, join on `(mint, created_at)`, and give each the PI-D-015 decision time". Script: `skeptic_01_counterexample.py`, run from the clone (temp `MEMELAB_DB`). Output:

```
PI-D-015 decision time (first export holding the key): 15c2087e 2026-10-07T21:53:55Z
rows in that export (what existed at the decision): [('SETUP DEVELOPING', 69, 0)]
row(s) a loader gets via state.import_ of the newest export holding the key 25bb1e43 : [('REJECTED', 60, ['CLUSTER_OWNERSHIP_GT_25PCT'])]
first export that shows the REJECTED row: 996190ce 2026-10-07T22:20:37Z (26.7 min after the decision time)
LOOK-AHEAD REPRODUCED
```

The decision at 21:53:55Z receives a REJECTED status and a fatal flag that first existed at 22:20:37Z. Nothing in Phase 01 catches it: the contract tests, the mutation check, the anchor checkers and the probes all pass, and the registry's tie rule is silent on equal `created_at`. `skeptic_01_revisions.py` detects it in the data; a Phase 05 test that keys decision time on the row hash would catch it in code.
