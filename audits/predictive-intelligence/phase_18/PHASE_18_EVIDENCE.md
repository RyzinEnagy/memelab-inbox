# Phase 18 evidence: reports, CLI and alerts without trading directives

Status: **NEEDS_REVIEW** (first pass, with two self-review change controls CP18-0 and CP18-1; the orchestrator's independent skeptic has not run yet). Every gate item below was reproduced by the phase agent, G21 after the records commit `ac19668`; the attack step is not independent until the orchestrator's skeptic reports (PI-D-013). TEST_ONLY parts: the FORECAST display path and the reevaluate and forecast_withdrawn alerts (no real FORECAST exists; shown on watermarked format-only fixtures).

- Branch `feature/predictive-intelligence`; HEAD before `4ebccc3`. Commits (UTC): pre-registration `ebb7059` (09:49:07Z), frozen code `96c4445` (10:27:14Z), recorded runs `3601881` (10:38:02Z), CP18-0 code `0127d2e` (10:39:31Z), repeated runs `44118a1` (10:53:24Z), CP18-1 code `ea799da` (10:54:50Z), repeated runs and these records after it (hashes in HANDOFF.md).
- Date 2026-10-27, UTC 09:36Z (entry suite start) to about 11:30Z. Python 3.13, numpy only in the lab runtime. Spend: 0 Firecrawl credits, 0 vendor calls, 0 language-model calls, no network use at all; every real-data command ran inside `unshare -n`, and every probe and test refuses sockets (0 events).
- Package: 41 of 41 checksums OK.
- Erratum: the checklist header says it was written "from 09:55Z"; its commit `ebb7059` is at 09:49:07Z (written before that). Nothing else in it depends on the time.

## Entry gate (re-run before any change)

| Check | Command | Result |
|---|---|---|
| Full suite | `python -m pytest tests -q -p no:cacheprovider` at `4ebccc3` | exit 1, `2 failed, 2050 passed, 1 skipped in 447.20s`; only the two known clock-dependent failures (`tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`, `tests/test_catalyst_firecrawl.py::test_page_history_and_spend_survive_a_new_session_through_the_state_export`); strays `data/reports/20261027_0936_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal` removed by hand |
| Seal check | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | exit 0, `"problems": []` |
| Phase 17 key check | `bash audits/predictive-intelligence/phase_17/probes/real_path_smoke.sh 4ebccc3... <scratch>` then `run_integration.py smoke` | every run exit 0 (16 commands); flag off byte-equal to `b0fad12` over every report; flag on the base body plus the appended section; lab tables equal; 24 ABSTAIN lines, 0 FORECAST lines |
| Phase 17 status | `PHASE_17_RESULTS.json` | PASS, 27 checks, 0 failed |
| Tracked lab database | sha256 | `data/memelab.sqlite` `068287c0...` (unchanged) |

Evidence: `evidence/entry/`.

## What was built (rules in ACCEPTANCE_CHECKLIST.md, PI-D-098, CP18-0 PI-D-099, CP18-1 PI-D-100)

- `memelab/predictive/reports.py` (report-1 and alerts-rules-1), imported by no module; CLI `python -m memelab.predictive.reports report|alerts|alerts-state`. No existing file changes except the one isolation test of rule 14: `git diff --stat 4ebccc3 HEAD -- memelab tests` lists `memelab/predictive/reports.py`, the new tests and fixtures, and `tests/test_predictive_contract.py` (4 lines: the integration leaf now allows exactly `reports.py`). `tests/fixtures/predictive/phase18/PINNED_SHA256.json` pins the sha256 of all 164 Python files under `memelab/` at `4ebccc3`, and a test checks every one.
- Reading: `integration.load_state` and `integration.check_state` only; each document with its record and its owning request; a FORECAST number only when the record has no condition, the request's raw number, stored calibrated point and interval and calibration card sha agree with the document, and the registry-resolved cards pass `integration.check_document`; otherwise DOCUMENT_REFUSED with the failed checks and no number; a state-check problem that names no document refuses every document. The backtest veto, decision support, staleness, catalyst state and served registry state are read from the request record.
- Rendering: sections in the lab's buckets through `memelab.report._ev`; at a glance (probabilities shown n of m, reasons across the targets, per target registry and calibration, BACKTEST_NOT_AVAILABLE, SIMULATION_NOT_AVAILABLE, a table of every opportunity with each target's status, vetoes and input state), system status, target definitions from `contract.TARGETS`, carried constraints (Phase 13 rules, Phase 17 sanitization), per opportunity the ten sections of rule 6, events not attempted, units and times. Lab facts only from the thesis row whose snapshot hash matches. An unblock line per contract reason (`UNBLOCK`).
- Sanitization: token text through the Phase 17 helpers; lab codes as codes (CP18-0); the lab status withheld when it carries trade wording; whole-text trading-word and local-path check (raises, nothing written).
- Alerts: the social-intel state schema, `_in_cooldown`, local day, quiet hours, local times, disclaimer, `FileSink` previews, `state_view`, `render_state`, `render_run`; dry run only; risk_override, reevaluate, forecast_withdrawn, pipeline_health; veto overrides a forecast; warnings first; new passes only; `too_soon`, `no_new_upstream_data`, `feed_unavailable`.
- Deliverables: `ui/EXAMPLE_REPORTS.md` (real excerpts and watermarked format-only examples; generated by `probes/make_examples_doc.py`), `ui/ALERT_RULE_MATRIX.md`, `ui/MISSING_DATA_UX.md`, `real/` (reports, alert runs, checks), golden files `tests/fixtures/predictive/phase18/golden/` (7).
- Tests: `tests/test_predictive_reports.py` (65), `tests/test_predictive_phase18_outputs.py` (7).

## Commands and exits (recorded runs)

| Step | Command | Exit and result |
|---|---|---|
| Golden stability | `python -B probes/run_reports.py goldens <scratch>` twice | identical sha256 for all 7 texts |
| First mutation probe (before the freeze) | `python -B probes/mutation_reports.py <scratch>` | 42 of 46; survivors R2, R3, R5, R9 (below) |
| Mutation probe at `96c4445` | same | exit 0, 46 of 46 (`evidence/mutation_reports_frozen_96c4445.json`) |
| Real-path smoke at `96c4445` | `bash audits/predictive-intelligence/phase_17/probes/real_path_smoke.sh 96c4445 <scratch>`, `run_integration.py smoke` | every run exit 0 (16 commands); flag off byte-identical to `b0fad12` (9 reports, lab tables) |
| Export replay at `96c4445` | `unshare -n python -B audits/predictive-intelligence/phase_17/probes/run_integration.py replay <scratch>` | exit 0; 52 window events, 156 abstentions, replay again 52 DUPLICATE and 0 documents |
| Real reports and alerts at `96c4445` | `unshare -n python -B probes/run_reports.py real <smoke> <replay> real/` | exit 0; committed at `3601881` |
| CP18-0 tests on the old code | `python -B probes/cp18_0_old_code_check.py` | 2 of 2 fail on `96c4445` (`evidence/cp18_0_old_code_check.json`) |
| Repeat at `0127d2e` | smoke, replay, real, mutation probe | exit 0; `evidence/rerun_cp18_0_diff.json`: every count, status, reason and alert decision equal; the replay report and alert show NO_SELL_ROUTE instead of "withheld", the snapshot detail keeps its spaces; mutation probe 48 of 48 |
| CP18-1 tests on the old code | `python -B probes/cp18_1_old_code_check.py` | 2 of 2 fail on `0127d2e` (`evidence/cp18_1_old_code_check.json`) |
| Golden regeneration at CP18-1 | `python -B probes/run_reports.py goldens tests/fixtures/predictive/phase18/golden` | 6 lines changed (the units line in 5 files, the refused line in 1), reviewed |
| Repeat at `ea799da` | smoke (10:55:03Z to 10:55:30Z), replay, real (to 10:55:49Z) | exit 0; flag off byte-identical to `b0fad12`; `evidence/rerun_cp18_1_diff.json`: only `replay_report.percent_or_fraction_outside_definitions` changes (1 to 0, the measured change now labelled and counted apart as 1); text differences after masking ids and times: the labelled event line and the units line |
| Mutation probe at `ea799da` | `python -B probes/mutation_reports.py` | exit 0, 49 of 49 (`evidence/mutation_reports.json`) |
| Ledger | `python -B probes/ledger.py audits/predictive-intelligence/phase_18` | 3,350 rows (3,328 plus 4 debug runs, 6 recorded runs and 6 for each of the two repeats), N_search 130, sensitivity 169 |
| Post-commit at `ac19668` | `python -m pytest tests -q -p no:cacheprovider`; `python -m memelab social guard`; `check_seal.py`; `python tools/release_audit.py --history` on a single-branch clone | suite exit 1, `2 failed, 2122 passed, 1 skipped in 490.69s` (known failures only); guard exit 0, `"violations": []` over 2,710 files; seal exit 0, `"problems": []`; audit exit 0, "Needs action: no." |
| Suite before the records commit | `python -m pytest tests -q -p no:cacheprovider` | exit 1, `2 failed, 2122 passed, 1 skipped in 544.49s` (the two known failures only); strays removed by hand |

## Results on real data (TEST_ONLY parts excluded)

Sandbox scout state (`real/REAL_SCOUT_REPORT.md`, `real/REAL_RUN_CHECKS.json`): the Phase 17 real path (committed inbox bodies, the `71fc50e` export imported into a temporary lab database, `unshare -n`) at `ea799da`, report built with the sandbox lab database of the flag-on run.

- 8 opportunities, 24 targets, 0 probabilities, 24 ABSTAIN, 0 refused; reasons MODEL_NOT_SELECTED 24, UNCALIBRATED 24, INSUFFICIENT_HISTORY 24, SOURCE_STALE 24, TARGET_NOT_FEASIBLE 6; inputs INPUT_STALE 8 (the bodies are from 2026-10-07); 8 of 8 snapshots verified against the lab database (symbol, token age from the vendor's first pool time, lifecycle and structure labels); 3 opportunities with a fatal-flag veto (GOMO CANNOT_EXIT_5K, HIGGS and slopcannon WASH_TRADING_HIGH); BACKTEST_NOT_AVAILABLE on every opportunity; SIMULATION_NOT_AVAILABLE 10 times (at a glance, system status, each opportunity); 16 events not attempted (DUPLICATE, from the rerun and the retry), listed. No percent outside the target definitions, no fraction, no trading word, no local path (checked on the committed text).
- Dry-run alerts at the newest capture plus 60 s (`real/REAL_ALERTS_SCOUT_DRY_RUN.txt`): outcome evaluated, 0 candidates, 0 alerts; 3 risk_override candidates suppressed SOURCE_STALE (the report still shows the flags).

Export-replay state (`real/REAL_REPLAY_REPORT.md`): the 52 prospective-window decision events (47 mints, 3 export commits) at `ea799da`, no lab database.

- 47 opportunities, 141 targets, 0 probabilities, 141 ABSTAIN; reasons MODEL_NOT_SELECTED, UNCALIBRATED, INSUFFICIENT_HISTORY and SOURCE_STALE 141 each, OUT_OF_SCOPE_CHAIN 51 (EVM tokens), TARGET_NOT_FEASIBLE 21; 22 opportunities with a veto (CANNOT_EXIT_5K, CLUSTER_OWNERSHIP_GT_25PCT, INSIDER_DISTRIBUTION, LARGEST_HOLDER_GT_15PCT, NO_SELL_ROUTE, TRANSFER_FEE_GT_5PCT); snapshots not verified (no lab database: symbol, age and lab labels UNKNOWN); 52 DUPLICATE events listed; one labelled measured market change (vol_24h -78.6%).
- Dry-run alerts at 2026-10-26T10:24:04Z (`real/REAL_ALERTS_REPLAY_DRY_RUN.txt`): 8 candidates, 8 risk_override previews (fatal-flagged requests captured within 24 h), 15 suppressed SOURCE_STALE; ledger `file:dry_run_preview` 8; 0 deliveries to a device; no `sent` folder.

Flag off: the real scout with the flag off is byte-identical to `b0fad12` (9 reports and the lab tables) at `96c4445`, `0127d2e` and `ea799da` (`real/REAL_PATH_SMOKE.json`); Phase 18 changes no lab file, and no module imports `reports.py`.

## Gate items

| Id | Result | Evidence |
|---|---|---|
| G1 | held | `evidence/entry/` |
| G2 | held: only `reports.py`, the new tests and fixtures and the 4-line amendment of `tests/test_predictive_contract.py`; 164 lab modules pinned | `git diff --stat 4ebccc3 HEAD -- memelab tests`; `test_g2_*` |
| G3 | held | `test_g3_*` (FLAG_OFF for no config and four malformed configs, the three commands write nothing); `real/REAL_PATH_SMOKE.json` |
| G4 | held: 7 golden files reproduced byte for byte (ids that depend on the temporary folder replaced, everything else compared) | `test_g4_*` |
| G5 | held | `test_g5_*`; real checks |
| G6 | held | `test_g6_*`; real checks (0 percents or fractions outside the definitions and the labelled measured change) |
| G7 | held: forged point, wider forged interval, other reasons, orphan document, document moved to another request, out-of-range number, unresolved cards, duplicate forecast id, tampered file, flag turned off after the pass | `test_g7_*`, `test_g7_cx18_*` |
| G8 | held (fixture): FORECAST 83% on FXC with CANNOT_EXIT_5K shows "overridden by veto", PRICE_PATH_NOT_PROCEEDS and EXECUTION_DATA_MISSING; risk_override first; reevaluate suppressed VETO_OVERRIDES_FORECAST | `test_g8_*`; golden; `ui/EXAMPLE_REPORTS.md` |
| G9 | held | `test_g9_*` |
| G10 | held | `test_g10_*`; `ui/MISSING_DATA_UX.md` |
| G11 | held | `test_g11_*`, `test_cp18_0_*` |
| G12 | held | `test_g12_*` |
| G13 | held | `test_g13_*` |
| G14 | held | `test_g14_*`; `ui/ALERT_RULE_MATRIX.md` |
| G15 | held | `test_g15_*` |
| G16 | held | `real/REAL_SCOUT_REPORT.md`, `real/REAL_RUN_CHECKS.json`, `tests/test_predictive_phase18_outputs.py` |
| G17 | held | `real/REAL_REPLAY_REPORT.md`, `real/REAL_ALERTS_*`, outputs tests |
| G18 | held: 0 socket events | audit hooks in tests and probes; `unshare -n` |
| G19 | held | `test_g19_*`; the Phase 01 to 17 isolation tests pass |
| G20 | held | `test_g20_*` |
| G21 | held at `ac19668`: suite `2 failed, 2122 passed, 1 skipped in 490.69s` (the two known failures only; strays removed by hand), guard 0 violations, seal check 0 problems, single-branch release audit exit 0 "Needs action: no." | `postcommit/` |
| G22 | held: 49 of 49 at `ea799da` | `evidence/mutation_reports.json` |
| G23 | held: 22 rows added, N_search 130 (169); content guard on every Phase 18 JSON (test) | `experiments/`, outputs test |
| G24 | held: CX-18 caught | below |

## Counterexample CX-18 and what catches it

Pre-registered: a renderer that trusts `document.probability` whenever the status is FORECAST, and alerts evaluated policy by policy. Caught: `test_g7_cx18_a_forged_probability_in_a_resealed_state_is_refused_and_shows_no_number` re-seals a state whose FXA probability was raised by 0.05 (every record id, file sha and the pass chain recomputed; `check_state` reports 0 problems), and the report refuses the document ("probability differs from the point stored with the raw number") and prints no number; `test_g8_*` gives one risk_override and a suppressed reevaluate on the impossible exit. Removing the comparison (mutation R4) or the veto rule (A6) makes the tests fail.

## Self-review (not independent): iteration log

1. Pass 1 (before the freeze): the first real render refused itself (the report's own wording used a word of the Phase 18 list); the wording was changed. The first mutation probe left 4 survivors: R5 (a wider forged interval passes `check_document` because it still holds the support interval) was a test gap, closed by `test_g7_a_wider_forged_interval_*`; R2, R3 and R9 are layered checks that mask each other (ownership, state-check refusal, abstention validator), now probed as the combinations that remove every layer (R2+R3+Q, R3+R9) and caught by a new test that moves a document to another request; a state-check problem naming no document (a duplicated forecast id) now refuses every document.
2. Pass 2 (CP18-0, PI-D-099), found in the recorded real replay output: the lab fatal flag NO_SELL_ROUTE was printed as "withheld" (the Phase 17 token-text helper withholds a string whose words include a trading word), a concealed risk; lab codes are now rendered as codes and never withheld; the report's own detail text kept its spaces.
3. Pass 3 (CP18-1, PI-D-100), found while checking the repeated outputs: the replay report printed a measured market change (vol_24h -78.6%) that rule 13 and the report's units line did not allow for; the line is now labelled "measured market changes since the previous attempt, not probabilities", the units line says so, and rule 13 is amended; a refused line's punctuation was fixed with it.
4. Deviation from the stated expectation, not from a rule: the checklist expected "GOMO with the fatal-flag veto"; the real report shows three vetoes (GOMO, HIGGS, slopcannon), all already present in Phase 17's section, so the expectation was incomplete. The scout alerts therefore have 3 suppressed SOURCE_STALE candidates, not 1.

## Limitations

- No real probability exists, so the FORECAST display path, reevaluate and forecast_withdrawn are TEST_ONLY; the examples of a validated forecast are format-only fixtures.
- The request record does not keep the feature availabilities, so a report cannot re-run `verify_point`; a FORECAST number is tied to the point stored with the raw number at publication, the hash-chained state and the registry-resolved cards. A writer who rewrites the stored point and the document together and re-seals the chain is not caught: the state is hash-chained, not signed.
- The replay report has no lab database: its snapshots are not verified and lab facts are UNKNOWN.
- Codes such as NO_ENTRY_AT_SHADOW_OR_ABOVE (registry), NO_TRADES_AFTER_ENTRY (label outcome) and NO_SELL_ROUTE (fatal flag) contain trade words inside a code; the whole-word check passes them by design (as in Phase 17), and the examples document say what they mean.
- The Phase 18 report is a separate command over the persisted state; the scout report keeps the Phase 17 section unchanged.
- The daily cap was not reached on real data (8 candidates, cap 8); the cap, cooldown, dedupe and quiet hours are proven on fixtures.
- The real dry-run alerts were evaluated at the newest capture plus 60 s (replay: 2026-10-26); at a later wall-clock time every real candidate would be SOURCE_STALE.
