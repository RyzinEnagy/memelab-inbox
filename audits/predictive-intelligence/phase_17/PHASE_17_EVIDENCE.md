# Phase 17 evidence: every eligible discovery or catalyst change gets a forecast or a visible abstention

Status: **PASS** after repair pass 2 (CP17-1, PI-D-096): the orchestrator's independent skeptic reviewed `ea73cfb` and found 2 MATERIAL findings (both latent today: no real request reaches the failing branches) and 8 minor; each was checked against the code, fixed with a test that fails on `ea73cfb` (or, for checks that pin existing calls or close unused gaps, with a mutation that the new tests catch), and the recorded runs were repeated at the repair code. Every gate item holds. TEST_ONLY parts: the FORECAST path (fixture champion), the reference-price reader path, the backtest adapter, depth from collector rows, catalyst-triggered changes (no catalyst event or link exists in the imported export).

- Branch `feature/predictive-intelligence`; HEAD before `b0fad12`. Commits: pre-registration `7f7bc28` (05:44Z), frozen code `3d2089b` (06:37:55Z), recorded runs `6f4e8f7`, CP17-0 code `6172b49`, repeated recorded runs `30be448`, first-pass records `c25ce00` and `ea73cfb` (reviewed by the skeptic), CP17-1 repair code `148e3da`, recorded runs repeated at `148e3da` and the records after it (see HANDOFF.md for the final hashes).
- Date 2026-10-27 (UTC 05:25Z to about 07:20Z). Python 3.13, numpy only in the lab runtime. Spend: 0 Firecrawl credits, 0 vendor calls, 0 language-model calls; every real-data command ran inside `unshare -n` or under an audit hook that refuses sockets (0 socket events).
- Package: 41 of 41 checksums OK.

## Entry gate (re-run before any change)

| Check | Command | Result |
|---|---|---|
| Full suite | `MEMELAB_DB=<tmp> python -m pytest tests -q` | exit 1, `1 failed, 1925 passed, 1 skipped in 365.52s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; strays `data/reports/20261027_0528_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal` removed by hand |
| Seal check | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | exit 0, `"problems": []`, three pinned hashes |
| Phase 16 key check | `python -B audits/predictive-intelligence/phase_16/probes/build_registry.py <tmp>` | exit 0; 69 entries, ABSTAIN 6, NO_GO 63, inference 69 of 69, NO_ENSEMBLE x3, N_search 130, no failure; entries, log, index and the three TODAY files byte-equal to the committed ones |
| Phase 16 status | `PHASE_16_RESULTS.json` | PASS, 40 checks, 0 failed |
| Stores | sha256 | tracked `data/memelab.sqlite` `068287c0...`, `p05/predictive_store.sqlite` `2525f0c4...`, `p06/dev_store.sqlite` `d2a5a7c6...` (unchanged; the phase reads neither private store) |

Evidence: `evidence/entry/`.

## What was built (rules in ACCEPTANCE_CHECKLIST.md, PI-D-093, CP17-0 PI-D-094)

- The only change to existing lab code: `memelab/cli.py` gains `_predictive_enabled` (CP17-1: reads `data/config.json` itself; true only when `predictive.enabled` is the JSON value true; any exception means off), `_predictive_section` and `_predictive_line` (each returns None when the flag is off without importing the package; with the flag on, each imports `memelab.predictive.integration` lazily and, on any import failure, returns a visible not-available section or line) and two call sites: `cmd_scout` appends the section after the unchanged body before the file is written; `cmd_analyze` prints one line after the existing line. `git diff b0fad12 HEAD --stat -- memelab` shows `memelab/cli.py` (42 added lines, 0 removed) and the two new modules only.
- `memelab/predictive/integration.py` (integration-1): the request flow of `integration/REQUEST_FLOW.md`; exactly one request record per trigger, three documents and three abstention-1 records per attempted event, the frozen material gate (as of the capture; the served model, pin and serve state of each target are in the key), one attempt per mint and 64 per pass, 30 s budget, no socket, reads only for a served champion through `runtime.CallGuard` with cost cap 0, INPUT_STALE after 7,200 s, capture-store features, `registry.serve` then `abstention.forecast_result`, `check_document` (Phase 13 m4) and `verify_point` (Phase 13 m3), decision support (`onchain.decision_support` plus the backtest veto), append-only sha-checked state with a chained pass log, a state directory inside the repository refused unless under `data/private/` (CP17-0), the plain-language section, ops metrics, `python -m memelab.predictive.integration status|check|catalyst-pass`.
- `memelab/predictive/bt_adapter.py` (bt-adapter-1): read-only interface to the backtesting branch's assessment record and `bt_assessments` table at `69bc5c3`, fixtures only.
- Isolation seams (PI-D-093 item 7): four tests amended to allow exactly `memelab/cli.py` -> `integration` and `integration.py` -> registry, calibration, abstention, onchain and depth_adapter, each with a negative case. Found while amending: the Phase 09 isolation test does not see relative imports, and `memelab/predictive/analog.py` (Phase 11) imports `onchain` lazily for its divergence attributes; recorded and pinned in the amended test, not changed.
- Tests: `tests/test_predictive_integration.py` (104, of which 14 from CP17-1), `tests/test_predictive_phase17_outputs.py` (9).

## Commands and exits (recorded runs)

| Step | Command | Exit and result |
|---|---|---|
| Pre-freeze suite at the uncommitted code | `python -m pytest tests -q` | exit 1, `1 failed, 2019 passed, 1 skipped in 409.24s` (known failure only) |
| First mutation probe (before the freeze) | `python -B probes/mutation_integration.py` | 53 of 56; survivors T2, C2, D2 killed by tighter tests (code unchanged) |
| Mutation probe at `3d2089b` | same | exit 0, 56 of 56 |
| Real-path smoke at `3d2089b` | `bash probes/real_path_smoke.sh 3d2089b... <scratch>` then `run_integration.py smoke` | every run exit 0 (16 commands) |
| Export replay at `3d2089b` and its repeat | `run_integration.py replay <scratch>` twice | exit 0; the repeat differs only in latency, wall time and file hashes (`evidence/replay_repeat_diff.json`) |
| Trace and fixture at `3d2089b` | `run_integration.py trace`, `fixture` | exit 0 |
| CP17-0 tests on the old code | `python -B probes/cp17_0_old_code_check.py` | 3 of 3 fail on `3d2089b` (`evidence/cp17_0_old_code_check.json`) |
| Recorded runs repeated at `6172b49` | the same four commands | exit 0; `evidence/rerun_cp17_0_diff.json`: every count, event, reason and boolean equal; differences are capture times, ids and the report paths stored in thesis rows (each run writes its own output folder), and the replay's request record ids (the material key now holds the serve states) |
| Mutation probe at `6172b49` | same | 59 of 59 (`evidence/mutation_integration.json`) |
| CP17-1 pre-freeze suite at the uncommitted repair | `MEMELAB_DB=<tmp> python -m pytest tests -q` | exit 1, `6 failed, 2046 passed, 1 skipped in 448.40s`: the known catalyst test, `tests/test_catalyst_firecrawl.py::test_page_history_and_spend_survive_a_new_session_through_the_state_export` (uses the real clock; fails the same way on the `ea73cfb` tree, outside this phase) and 4 outputs tests waiting for the repeated runs |
| CP17-1 repair tests on the old code | `python -B probes/rp2_old_code_check.py` | 10 of 10 fail on `ea73cfb`; the 2 M2 and 2 m4 pinning tests pass there by design (`evidence/rp2_old_code_check.json`) |
| Recorded runs repeated at `148e3da` | real-path smoke, `run_integration.py smoke`, `replay`, `trace`, `fixture` | exit 0; flag off byte-identical to `b0fad12` (9 reports), flag on body unchanged plus the section; `evidence/rerun_rp2_diff.json` (below) |
| Mutation probe at `148e3da` | `python -B probes/mutation_integration.py` | 73 of 73 (`evidence/mutation_integration.json`) |
| Isolation mutations at `148e3da` | `python -B probes/rp2_isolation_mutations.py` | 14 of 15 (the one survivor is the recorded static-scan limit) (`evidence/rp2_isolation_mutations.json`) |
| Ledger | `python -B probes/ledger.py audits/predictive-intelligence/phase_17` | 3,328 rows (3,294 plus 4 debug runs, 10 recorded runs and 10 for each of the two repeats), N_search 130, sensitivity 169 |

## Results on real data (TEST_ONLY parts excluded)

Sandbox scout (`smoke/REAL_PATH_SMOKE.json`): `python -m memelab scout` on the committed inbox bodies (disc01, s2_01, deep01a to deep04, forensics01; 8 mints) after `python -m memelab.state import` of the `71fc50e` export (2026-10-26) into a temporary lab database, in a sandbox clone, every command inside `unshare -n`.

- Flag off at the frozen code against `b0fad12`: all 9 reports (the scout report and 8 token reports) byte-equal; the lab tables (tokens without the two wall-clock write times, theses, entries, watchlist, rejections) equal.
- Flag on: the same body plus the appended section (`smoke/REAL_SCOUT_SECTION.md`); token reports byte-equal; lab tables equal to the flag-off run. 8 DISCOVERY events, 24 documents, every one ABSTAIN with MODEL_NOT_SELECTED, UNCALIBRATED, INSUFFICIENT_HISTORY and SOURCE_STALE (INPUT_STALE: the bodies were collected on 2026-10-06 and 2026-10-07), TARGET_NOT_FEASIBLE for the 2 mints without a point-in-time pool; model `not_selected`; registry NO_VIABLE_CHAMPION and Phase 13 UNCALIBRATED named for each target; BACKTEST_NOT_AVAILABLE; COLLECTOR_NOT_AVAILABLE and size EXECUTION_DATA_MISSING; fatal-flag vetoes shown for GOMO (CANNOT_EXIT_5K), HIGGS and slopcannon (WASH_TRADING_HIGH); 0 FORECAST lines.
- Rerun on the same database and state, and a retry on a fresh database with the same state: 16 DUPLICATE, 0 new documents. Storm (PAID listed five times): 8 attempts, 4 SUPERSEDED_IN_PASS. Research mode: 48 internal reference records (B0 and B2 per target), never documents. `analyze` with the flag on: one line `predictive: DISCOVERY ABSTAIN (INSUFFICIENT_HISTORY, MODEL_NOT_SELECTED, SOURCE_STALE, UNCALIBRATED) | ... | research only, not advice`. `check` on every state: 0 problems. Latency per request p50 under 16 ms, max 27 ms (research mode).
- The checkout's `git status` stayed clean; the sandbox clone shows no tracked change after the scout runs; `analyze` writes its token report under the sandbox's `data/reports` by design (no report-dir option), recorded and restored.

Export replay (`smoke/REAL_EXPORT_REPLAY.json`): the 92 export versions on `origin/main` up to `71fc50e`, 1,553 decision events, 52 of them in the prospective window (from 2026-10-24T00:00Z, 3 export commits, 47 mints), one pass per export commit at its commit time (EXPORT_COMMIT basis, research mode): DISCOVERY 47, MATERIAL_CHANGE 5, 156 documents, all ABSTAIN (OUT_OF_SCOPE_CHAIN for the 19 EVM decisions), every document with its record, forecast ids unique; the same replay again: 52 DUPLICATE, 0 documents. Registry mode NO_VIABLE_CHAMPION with pin reason NO_PIN (these decisions are before the registry's pins of 2026-10-27), so no reference record. No label, no vendor read.

Traced examples (`smoke/TRACE_EXAMPLES.json`): PAID (scout, no fatal flag), GOMO (scout, CANNOT_EXIT_5K veto) and the BSC token `0x3d4f0513...` (replay: DISCOVERY then MATERIAL_CHANGE twice, each snapshot row found in its export commit). For each: the snapshot hash recomputed from the lab database's thesis row without `report_path`, and the full row hash equal to the request's `row_sha256`, forecast ids, abstention record ids, reasons, registry mode, the token report named in the section, record ids in the section, contract and pairing checks empty.

Fixture path (`smoke/FIXTURE_E2E.json`, TEST_ONLY): a fixture B2 champion pinned with `allow_fixture`, a SHADOW calibration card from synthetic prospective evidence, a fixture reader: 2 FORECAST documents (T1 24 h) with SHADOW_RESEARCH_ONLY, INTERVAL_EXCLUDES_UNMODELED_RISK and COHORT_ESTIMATE_NOT_TOKEN_HISTORY, 4 abstentions, the fatal-flag veto shown beside the fixture forecast, the record ids in the section.

## Gate items

| Id | Holds | Evidence |
|---|---|---|
| G1 | yes | entry gate above |
| G2 | yes | `test_g2_cli_differs_from_the_pre_phase17_copy_only_by_the_hook` (42 added lines, 0 removed after CP17-1); git diff |
| G3 | yes | `test_g3_*`; smoke base_off vs frozen_off |
| G4 | yes | `test_g4_*`; smoke frozen_on |
| G5 | yes | `test_g5_*`; smoke and replay counts |
| G6 | yes | `test_g6_*`; rerun, retry, replay round 2 |
| G7 | yes | `test_g7_*` (18 cases and the age trigger), `test_the_gate_compares_*` |
| G8 | yes | `test_g8_*`; storm run |
| G9 | yes | `test_g9_*`, `test_a_slow_reader_*`; 0 socket events |
| G10 | yes | `test_g10_*`, CP17-0 state directory test; real INPUT_STALE |
| G11 | yes | `test_g11_*`; smoke and replay |
| G12 | yes | `test_g12_*`; REQUEST_FLOW.md merge requirements |
| G13 | yes | `test_g13_*` |
| G14 | yes | `test_g14_*` |
| G15 | yes | `test_g15_*` |
| G16 | yes (fixture part TEST_ONLY) | `test_g16_*`; FIXTURE_E2E.json |
| G17 | yes | REAL_PATH_SMOKE.json, REAL_EXPORT_REPLAY.json |
| G18 | yes (catalyst part on fixtures) | `test_g18_*` |
| G19 | yes | `test_g19_*`, CP17-0 drift test |
| G20 | yes | `test_g20_*` |
| G21 | yes | `test_g21_*`, amended isolation tests |
| G22 | yes | `test_g22_*`; `tests/test_predictive_reproductions.py` green in the suite |
| G23 | yes | post-commit after repair pass 2 at `05874fd`: suite `2 failed, 2050 passed, 1 skipped in 450.61s` (the known catalyst test and `test_catalyst_firecrawl` page_history, which uses the real clock and fails the same way on the `ea73cfb` tree; stray removed by hand), guard 0 violations, seal `"problems": []`, single-branch release audit exit 0 "Needs action: no." (`postcommit/rp2_*`). First pass, post-commit at `c25ce00`: suite `1 failed, 2031 passed, 1 skipped in 425.14s` (known failure only; stray removed by hand), guard 0 violations, seal `"problems": []`, single-branch release audit exit 0 "Needs action: no." (`postcommit/`) |
| G24 | yes | 73 of 73 at `148e3da`. Corrected wording (skeptic M2): the first pass's "59 of 59" was every mutation of the probe's own set, which did not delete the integration's calls to `check_document` or `verify_point`; the skeptic's deletions Y1 and Y2 left every test green. Both are now in the set and caught by the flow tests |
| G25 | yes | social guard 0 violations; content-guard test; trading-word checks |
| G26 | yes | `test_the_search_ledger_extends_phase_16_*` |
| G27 | yes | `test_cx17_*` (fails with the pin removed from the key: mutation G3) |

## Repair pass 2 (CP17-1, PI-D-096): the skeptic's findings and what now holds

The review and the skeptic's scripts are in `skeptic/` (copied unchanged). Each finding was reproduced on `ea73cfb` first.

| Finding | Verified | Fix | Test or check that fails without the fix |
|---|---|---|---|
| M1 a request is not all or nothing: a refused target leaves its siblings' documents, `check_state` is blind to it, the section hides the token, no recovery | yes (`probe_leak.py`) | per-event buffers that join the pass only when the whole event finished; any failure is ERROR with nothing saved, shown as "Failed: ..." with the token; an attempted event without exactly three documents is an error; `check_state` requires each document to belong to an attempted request of its pass and each attempted request to own exactly its documents | `test_rp2_m1_cx_s17_*`, `test_rp2_m1_a_failure_after_the_targets_saves_no_document`, `test_rp2_m1_an_attempted_event_short_of_its_three_documents_is_an_error`, `test_rp2_m1_check_state_detects_*` (all fail on `ea73cfb`); mutations A1 to A4 |
| M2 the calls to `check_document` and `verify_point` are not pinned; G24 overstated | yes (`my_mutations.py` Y1, Y2; `probe_forged_point.py`) | flow-level tests forge the point (+0.01 inside the interval) and drop a reason inside `abstention.forecast_result`; G24 wording corrected | `test_rp2_m2_the_flow_refuses_a_forged_point_*`, `test_rp2_m2_the_flow_refuses_dropped_reasons_*` (pass on `ea73cfb`, where the calls exist; mutations Y1 and Y2 are caught) |
| m1 a pathological config changes the flag-off output (RecursionError inside `contract.enabled`) | yes | `cli._predictive_enabled` reads the flag itself, any exception is off; `contract.py` unchanged (its hash is in every registry entry) | `test_rp2_m1_m6_flag_off_never_imports_*` (deep-nested JSON, bad JSON, a string "true", a list, a bare true); mutations E1, E2 |
| m2 flag on and the package fails to load: silent | yes | a visible not-available section and analyze line naming the exception class | `test_rp2_m2_flag_on_and_a_broken_package_says_so`; mutations E3, K3 |
| m3 symbols and names rendered raw: a symbol can inject a FORECAST line, a probability or a trading word | yes | `_ident`: letters, digits, dot, dash, underscore, at most 24 characters, "withheld" when the whole string carries a trading or forecast word; the mint only after the exact-address check; the whole section passes the trading-word check | `test_rp2_m3_*`; mutations I1, I2 |
| m4 isolation gaps: `from . import stats, registry`, a lab module importing the cli helper, `from . import integration` inside the package | yes (`mutate_isolation.py`: 4 survivors) | AST scans of relative imports (registry, integration); no lab module but `cli.py` names the helpers; a subprocess imports every lab module with the flag off | `test_the_registry_seam_*`, `test_no_predictive_module_imports_the_integration_module`, `test_rp2_m4_*`; `evidence/rp2_isolation_mutations.json` 14 of 15 (the one survivor is the recorded static-scan limit) |
| m5 no test that the backtest table is opened read-only; a default chain in `check_record` | yes (Y3) | test writes after `PRAGMA query_only=OFF` and expects "readonly"; no default chain | `test_rp2_m5_*`; mutations Y3, B1 |
| m6 flag-off cost: the helpers import the package (about 0.2 s) before the flag is read | yes | closed by the m1 fix: nothing of the package is imported when the flag is off | `test_rp2_m1_m6_*` (asserts `memelab.predictive` not in `sys.modules`) |
| m7 the snapshot hash includes the report path | yes | `snapshot_sha` without `id` and `report_path`; the full row hash kept as `row_sha256` | `test_rp2_m7_*` (DUPLICATE across report folders); mutation Z1 |
| m8 the section prints a local state path and report path | yes | no path printed: state named as "the predictive state directory", token report by file name | `test_rp2_m8_*`; mutation L1 |

What changed in the recorded outputs (`evidence/rerun_rp2_diff.json`, `148e3da` against `ea73cfb`): no count, event, reason, verdict or boolean. Every snapshot hash changes once (m7), and with it every forecast id and record id, the replay's state file hashes and the analyze line; the section keeps its 120 lines and loses the two path lines (m8); the theses table hashes differ because each run writes its own output folder (as at CP17-0). Flag off is byte-identical to `b0fad12` for all 9 reports and the flag-on scout body is unchanged with the section appended.

## Iteration log (passes)

1. Build: the module, the adapter, the hook and 75 tests; failures fixed (report paths in byte comparisons, a precedence bug in the pool expression, float tolerance at the 10% bound, row factories in the catalyst reader, the depth fixture's migration ledger, the analyze test clock).
2. Gate as of the capture (a replay older than the state compared with a later attempt); no default chain; 13 more tests. Debug runs on real data: 2 replays, 2 sandbox smokes (logged in the ledger as DEBUG_RUN_REAL_DATA).
3. First mutation probe 53 of 56: the export-staleness, link-time and reason-pairing tests were too weak; tightened; freeze at `3d2089b`; recorded runs; 56 of 56.
4. Own adversarial pass (not independent), CP17-0 (PI-D-094): a tracked state directory, a serve-state change hidden inside the hour, a non-ImportError import failure; fixed with tests that fail on `3d2089b`; recorded runs repeated; 59 of 59.
5. Repair pass 2, CP17-1 (PI-D-096), after the independent skeptic: 14 tests, 14 more mutations (3 of the new ones survived the first run of the new tests: a partial attempted event, a failed token shown under another event name, a forecast word alone as a symbol; each killed by a sharper test before the freeze), recorded runs repeated at `148e3da`.

## Counterexample

CX-17 (own, pre-registered): a cache keyed on decision content alone keeps a withdrawn FORECAST after a rollback. Caught by `test_cx17_a_rollback_makes_an_unchanged_snapshot_material_so_the_withdrawn_forecast_is_not_kept` and by mutation G3; extended by CP17-0 to a serve-state change (`test_cp17_0_a_serve_state_change_within_the_hour_is_material`, mutation K2). The independent skeptic's counterexample, CX-S17 "a refused forecast leaks" (`skeptic/probe_leak.py`): on the fixture path, the second target's document loses one reason inside `abstention.forecast_result`; at `ea73cfb` the event is ERROR but the first target's FORECAST document and record were already in the pass buffers and were persisted, `check_state` reported 0 problems, the section hid the token, and the next pass saw "some but not all forecast ids exist" and never recovered. What catches it now: `test_rp2_m1_cx_s17_a_refused_target_leaves_nothing_of_its_event_and_the_next_pass_recovers` (fails on `ea73cfb`), the ownership checks in `check_state` (`test_rp2_m1_check_state_detects_a_document_without_an_attempted_request`) and mutations A1 to A4. The skeptic's own script on the repaired code: the first pass persists nothing (ERROR, 0 documents), the second pass is DISCOVERY with 3 documents, `check_state` 0 problems (`evidence/rp2_probe_leak_repaired.json`).

## Limitations

- No probability can be published today: no champion (Phase 16), no calibration (Phase 13). The FORECAST path is shown on fixtures only.
- integration-1 builds features for family 07 only and gives a real champion `inference=None` (INFERENCE_NOT_CHECKED): both fail closed; lifting either is a change control.
- Capture features hold the single decision row and its token row: history, universe and candle groups are missing with their reasons.
- The committed inbox bodies are three weeks old, so every real scout request is INPUT_STALE; a fresh scout needs new collector reads, which this phase did not make.
- The export carries no catalyst events or links: catalyst-triggered changes and refreshes are exercised on fixtures only (on real data the source is OK with 0 exact links).
- A crash between two appends leaves the state refused (STATE_TAMPERED) until repaired by hand; there is no scheduler, so deferred events wait for the next scout pass.
- Backtesting: BACKTEST_NOT_AVAILABLE on this branch; the adapter is TEST_ONLY; a merge of PR #4 is Elving's decision (requirements in REQUEST_FLOW.md).
- The Phase 09 isolation test cannot see relative imports; `analog.py`'s lazy `onchain` import (Phase 11) is pinned, not removed. CP17-1 adds AST scans of relative imports for the registry and the integration and a subprocess that imports every lab module with the flag off; a dynamic import of a string built at run time inside a function no test calls is invisible to every static scan (`pipeline_concat_string` in `evidence/rp2_isolation_mutations.json`, recorded as a known limit).
- `bt_adapter` stays TEST_ONLY; a FORECAST document's backtest veto lives in its request record, not in the document, so a later consumer (Phase 18) must read the request records (the skeptic's note, not a finding).

## Artifacts (sha256 in PHASE_17_RESULTS.json)

`ACCEPTANCE_CHECKLIST.md`, `experiments/EXPERIMENT_REGISTRY.csv`, `experiments/SEARCH_LEDGER.csv`, `experiments/LEDGER_TOTALS.json`, `integration/REQUEST_FLOW.md`, `smoke/*`, `evidence/*`, `probes/*`, `SKEPTIC_PACKET.md`, code and tests named above.
