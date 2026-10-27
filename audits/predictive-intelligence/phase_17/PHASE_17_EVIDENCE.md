# Phase 17 evidence: every eligible discovery or catalyst change gets a forecast or a visible abstention

Status: **NEEDS_REVIEW** (first pass plus the self-review change control CP17-0; every gate item holds on the agent's own checks; the orchestrator's independent skeptic has not run yet). TEST_ONLY parts: the FORECAST path (fixture champion), the reference-price reader path, the backtest adapter, depth from collector rows, catalyst-triggered changes (no catalyst event or link exists in the imported export).

- Branch `feature/predictive-intelligence`; HEAD before `b0fad12`. Commits: pre-registration `7f7bc28` (05:44Z), frozen code `3d2089b` (06:37:55Z), recorded runs `6f4e8f7`, CP17-0 code `6172b49`, repeated recorded runs `30be448`, records after it (see HANDOFF.md for the final hashes).
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

- The only change to existing lab code: `memelab/cli.py` gains `_predictive_section` and `_predictive_line` (each imports `memelab.predictive.integration` lazily and returns None on any import failure) and two call sites: `cmd_scout` appends the section after the unchanged body before the file is written; `cmd_analyze` prints one line after the existing line. `git diff b0fad12 HEAD --stat -- memelab` shows `memelab/cli.py` (25 added lines, 0 removed) and the two new modules only.
- `memelab/predictive/integration.py` (integration-1): the request flow of `integration/REQUEST_FLOW.md`; exactly one request record per trigger, three documents and three abstention-1 records per attempted event, the frozen material gate (as of the capture; the served model, pin and serve state of each target are in the key), one attempt per mint and 64 per pass, 30 s budget, no socket, reads only for a served champion through `runtime.CallGuard` with cost cap 0, INPUT_STALE after 7,200 s, capture-store features, `registry.serve` then `abstention.forecast_result`, `check_document` (Phase 13 m4) and `verify_point` (Phase 13 m3), decision support (`onchain.decision_support` plus the backtest veto), append-only sha-checked state with a chained pass log, a state directory inside the repository refused unless under `data/private/` (CP17-0), the plain-language section, ops metrics, `python -m memelab.predictive.integration status|check|catalyst-pass`.
- `memelab/predictive/bt_adapter.py` (bt-adapter-1): read-only interface to the backtesting branch's assessment record and `bt_assessments` table at `69bc5c3`, fixtures only.
- Isolation seams (PI-D-093 item 7): four tests amended to allow exactly `memelab/cli.py` -> `integration` and `integration.py` -> registry, calibration, abstention, onchain and depth_adapter, each with a negative case. Found while amending: the Phase 09 isolation test does not see relative imports, and `memelab/predictive/analog.py` (Phase 11) imports `onchain` lazily for its divergence attributes; recorded and pinned in the amended test, not changed.
- Tests: `tests/test_predictive_integration.py` (91), `tests/test_predictive_phase17_outputs.py` (9).

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
| Ledger | `python -B probes/ledger.py audits/predictive-intelligence/phase_17` | 3,308 rows (3,294 plus 4 debug runs and 10 recorded runs), N_search 130, sensitivity 169 |

## Results on real data (TEST_ONLY parts excluded)

Sandbox scout (`smoke/REAL_PATH_SMOKE.json`): `python -m memelab scout` on the committed inbox bodies (disc01, s2_01, deep01a to deep04, forensics01; 8 mints) after `python -m memelab.state import` of the `71fc50e` export (2026-10-26) into a temporary lab database, in a sandbox clone, every command inside `unshare -n`.

- Flag off at the frozen code against `b0fad12`: all 9 reports (the scout report and 8 token reports) byte-equal; the lab tables (tokens without the two wall-clock write times, theses, entries, watchlist, rejections) equal.
- Flag on: the same body plus the appended section (`smoke/REAL_SCOUT_SECTION.md`); token reports byte-equal; lab tables equal to the flag-off run. 8 DISCOVERY events, 24 documents, every one ABSTAIN with MODEL_NOT_SELECTED, UNCALIBRATED, INSUFFICIENT_HISTORY and SOURCE_STALE (INPUT_STALE: the bodies were collected on 2026-10-06 and 2026-10-07), TARGET_NOT_FEASIBLE for the 2 mints without a point-in-time pool; model `not_selected`; registry NO_VIABLE_CHAMPION and Phase 13 UNCALIBRATED named for each target; BACKTEST_NOT_AVAILABLE; COLLECTOR_NOT_AVAILABLE and size EXECUTION_DATA_MISSING; fatal-flag vetoes shown for GOMO (CANNOT_EXIT_5K), HIGGS and slopcannon (WASH_TRADING_HIGH); 0 FORECAST lines.
- Rerun on the same database and state, and a retry on a fresh database with the same state: 16 DUPLICATE, 0 new documents. Storm (PAID listed five times): 8 attempts, 4 SUPERSEDED_IN_PASS. Research mode: 48 internal reference records (B0 and B2 per target), never documents. `analyze` with the flag on: one line `predictive: DISCOVERY ABSTAIN (INSUFFICIENT_HISTORY, MODEL_NOT_SELECTED, SOURCE_STALE, UNCALIBRATED) | ... | research only, not advice`. `check` on every state: 0 problems. Latency per request p50 under 16 ms, max 27 ms (research mode).
- The checkout's `git status` stayed clean; the sandbox clone shows no tracked change after the scout runs; `analyze` writes its token report under the sandbox's `data/reports` by design (no report-dir option), recorded and restored.

Export replay (`smoke/REAL_EXPORT_REPLAY.json`): the 92 export versions on `origin/main` up to `71fc50e`, 1,553 decision events, 52 of them in the prospective window (from 2026-10-24T00:00Z, 3 export commits, 47 mints), one pass per export commit at its commit time (EXPORT_COMMIT basis, research mode): DISCOVERY 47, MATERIAL_CHANGE 5, 156 documents, all ABSTAIN (OUT_OF_SCOPE_CHAIN for the 19 EVM decisions), every document with its record, forecast ids unique; the same replay again: 52 DUPLICATE, 0 documents. Registry mode NO_VIABLE_CHAMPION with pin reason NO_PIN (these decisions are before the registry's pins of 2026-10-27), so no reference record. No label, no vendor read.

Traced examples (`smoke/TRACE_EXAMPLES.json`): PAID (scout, no fatal flag), GOMO (scout, CANNOT_EXIT_5K veto) and the BSC token `0x3d4f0513...` (replay: DISCOVERY then MATERIAL_CHANGE twice, each snapshot row found in its export commit). For each: thesis row sha256 recomputed from the lab database equal to the snapshot hash, forecast ids, abstention record ids, reasons, registry mode, the token report named in the section, record ids in the section, contract and pairing checks empty.

Fixture path (`smoke/FIXTURE_E2E.json`, TEST_ONLY): a fixture B2 champion pinned with `allow_fixture`, a SHADOW calibration card from synthetic prospective evidence, a fixture reader: 2 FORECAST documents (T1 24 h) with SHADOW_RESEARCH_ONLY, INTERVAL_EXCLUDES_UNMODELED_RISK and COHORT_ESTIMATE_NOT_TOKEN_HISTORY, 4 abstentions, the fatal-flag veto shown beside the fixture forecast, the record ids in the section.

## Gate items

| Id | Holds | Evidence |
|---|---|---|
| G1 | yes | entry gate above |
| G2 | yes | `test_g2_cli_differs_from_the_pre_phase17_copy_only_by_the_hook`; git diff |
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
| G23 | after the post-commit checks | `postcommit/` |
| G24 | yes | 59 of 59 |
| G25 | yes | social guard 0 violations; content-guard test; trading-word checks |
| G26 | yes | `test_the_search_ledger_extends_phase_16_*` |
| G27 | yes | `test_cx17_*` (fails with the pin removed from the key: mutation G3) |

## Iteration log (passes)

1. Build: the module, the adapter, the hook and 75 tests; failures fixed (report paths in byte comparisons, a precedence bug in the pool expression, float tolerance at the 10% bound, row factories in the catalyst reader, the depth fixture's migration ledger, the analyze test clock).
2. Gate as of the capture (a replay older than the state compared with a later attempt); no default chain; 13 more tests. Debug runs on real data: 2 replays, 2 sandbox smokes (logged in the ledger as DEBUG_RUN_REAL_DATA).
3. First mutation probe 53 of 56: the export-staleness, link-time and reason-pairing tests were too weak; tightened; freeze at `3d2089b`; recorded runs; 56 of 56.
4. Own adversarial pass (not independent), CP17-0 (PI-D-094): a tracked state directory, a serve-state change hidden inside the hour, a non-ImportError import failure; fixed with tests that fail on `3d2089b`; recorded runs repeated; 59 of 59.

## Counterexample

CX-17 (own, pre-registered): a cache keyed on decision content alone keeps a withdrawn FORECAST after a rollback. Caught by `test_cx17_a_rollback_makes_an_unchanged_snapshot_material_so_the_withdrawn_forecast_is_not_kept` and by mutation G3; extended by CP17-0 to a serve-state change (`test_cp17_0_a_serve_state_change_within_the_hour_is_material`, mutation K2). The independent skeptic's counterexample: pending (orchestrator).

## Limitations

- No probability can be published today: no champion (Phase 16), no calibration (Phase 13). The FORECAST path is shown on fixtures only.
- integration-1 builds features for family 07 only and gives a real champion `inference=None` (INFERENCE_NOT_CHECKED): both fail closed; lifting either is a change control.
- Capture features hold the single decision row and its token row: history, universe and candle groups are missing with their reasons.
- The committed inbox bodies are three weeks old, so every real scout request is INPUT_STALE; a fresh scout needs new collector reads, which this phase did not make.
- The export carries no catalyst events or links: catalyst-triggered changes and refreshes are exercised on fixtures only (on real data the source is OK with 0 exact links).
- The thesis row stores the report path, so the same analysis written into another report folder is another snapshot (the gate then decides UNCHANGED or MATERIAL_CHANGE; no duplicate document either way).
- A crash between two appends leaves the state refused (STATE_TAMPERED) until repaired by hand; there is no scheduler, so deferred events wait for the next scout pass.
- Backtesting: BACKTEST_NOT_AVAILABLE on this branch; the adapter is TEST_ONLY; a merge of PR #4 is Elving's decision (requirements in REQUEST_FLOW.md).
- The Phase 09 isolation test cannot see relative imports; `analog.py`'s lazy `onchain` import (Phase 11) is pinned, not removed.

## Artifacts (sha256 in PHASE_17_RESULTS.json)

`ACCEPTANCE_CHECKLIST.md`, `experiments/EXPERIMENT_REGISTRY.csv`, `experiments/SEARCH_LEDGER.csv`, `experiments/LEDGER_TOTALS.json`, `integration/REQUEST_FLOW.md`, `smoke/*`, `evidence/*`, `probes/*`, `SKEPTIC_PACKET.md`, code and tests named above.
