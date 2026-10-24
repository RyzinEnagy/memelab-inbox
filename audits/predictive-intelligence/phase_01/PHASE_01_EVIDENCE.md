# Phase 01 evidence: gap analysis, placement and prediction requirements

| Item | Value |
|---|---|
| Phase | 01, "Freeze the measurable prediction objectives and determine the minimally invasive architecture" |
| Status | NEEDS_REVIEW: every gate item below holds on the phase agent's own checks; the independent skeptic is run by the orchestrator (PI-D-013) and must be folded in before PASS |
| Branch | `feature/predictive-intelligence` |
| HEAD before | `94be1bf` (Phase 00 repair pass 2, pushed to `origin/feature/predictive-intelligence`) |
| Commits | `b6f2621` pre-registration (2026-10-24T01:35:23Z, before any price data was read); the Phase 01 content commit on top (read with `git log -1`; this file is part of it) |
| Time (UTC) | 2026-10-24T01:22Z to 02:00Z |
| Spend | 0 Firecrawl credits; free calls: 15 GeckoTerminal, 3 GitHub REST (COST_LEDGER.md) |
| Package | 41 of 41 files OK against SHA256SUMS.txt |

## Inputs read

Package: START_HERE.md, EXECUTION_RULES.md, PHASE_INDEX.md, ORCHESTRATOR.md, `phases/PHASE_01_gap_analysis_placement_and_prediction_requirements.md`, references FORECAST_OUTPUT_SCHEMA.md, DATA_TIME_CONTRACT.md, SCIENTIFIC_VALIDATION.md, INTEGRATION_AND_CONFLICTS.md, BACKTEST_V12_BRIDGE.md, NO_GO_DECISION_TREE.md, ADVERSARIAL_SCENARIOS.md, COMPLETION_CHECKLIST.md, GRADING_RUBRIC.md, WORK_PRODUCT_EXAMPLE.md, MIROFISH_EVALUATION.md. Orchestration brief `/home/claude/pi_orchestration/PHASE_BRIEF.md`. Records: docs/predictive-intelligence/{HANDOFF, EXECUTION, DECISIONS, ROADMAP}.md; Phase 00 baseline (REPO_MAP, DATA_COVERAGE incl. "Clocks", EXISTING_PREDICTION_INVENTORY, FEATURE_TRACE), skeptic review and packet, results JSON. Code read for seams: outcomes_core.py, outcomes_ledger.py, replay_core.py, replay_sources.py, alpha_core.py, alpha_store.py, social/schema.py (alpha tables), research_store.py, cli.py, report.py, pipeline.py, state.py, db.py, launch/schema.py, launch/discover.py, test_content_guard.py, plus every file cited in GAP_MATRIX.csv.

## Commands and exits

| # | Check | Command | Exit | Result |
|---|---|---|---:|---|
| 1 | Package checksums | `sha256sum -c SHA256SUMS.txt \| grep -v OK` | 1 (grep found no non-OK line) | 41 of 41 OK |
| 2 | Checkout at start | `git status -sb; git log -5 --oneline` | 0 | clean, HEAD `94be1bf`, three Phase 00 commits on `f99c6c7` |
| 3 | Entry gate, full suite | `python -m pytest tests -q` (2026-10-24T01:23:04Z) | 1 | `1 failed, 785 passed in 137.59s (0:02:17)`; only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known) |
| 4 | Strays after entry suite | `git status --porcelain --ignored` | 0 | `data/reports/20261024_0123_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`, `.pytest_cache/`; removed by hand; `data/memelab.sqlite` sha256 `068287c0...a6679ca` unchanged |
| 5 | Predecessor key check (PI-D-011) and universe | `python audits/predictive-intelligence/phase_01/probes/decision_universe_probe.py origin/main <scratch>/universe.json <scratch>/gh/push_events.json` | 0 | 89 export versions, 1,801 theses, 248 mints; first-thesis write lag 149 mints, p50 16.92 min, max 116.5 min (matches Phase 00); output sha256 `4d2a8df5...` |
| 6 | GitHub push times | `curl https://api.github.com/repos/RyzinEnagy/memelab-inbox/events?per_page=100&page={1,2,3}` (01:25:35Z to 01:25:52Z) | 0 | HTTP 200 x3; 291 push events back to 2026-10-08T14:04Z; 82 of 89 export commits matched; push minus commit 1 to 5 s |
| 7 | Acceptance checklist written | `ACCEPTANCE_CHECKLIST.md` | n/a | 2026-10-24T01:31Z, before any deliverable or GeckoTerminal call |
| 8 | Contract tests (pre-registration) | `python -m pytest tests/test_predictive_contract.py -q -p no:cacheprovider` | 0 | `19 passed in 0.99s` |
| 9 | Pre-registration commit | `git commit` | 0 | `b6f2621` 2026-10-24T01:35:23Z, registry sha256 `dd3b4576...` |
| 10 | GeckoTerminal coverage sample | `python .../probes/gt_coverage_probe.py <universe> <scratch>/gt_raw .../probes/gt_coverage_sample.json` (01:36:22Z to 01:38:05Z) | 0 | 15 calls (14 HTTP 200, 1 HTTP 429 on call 6); sample of 10 seeded decisions: 5 OK, 4 INELIGIBLE_NO_RECENT_TRADE, 1 HTTP_429; routes 6 point-in-time pool, 4 vendor list; revision check 1,000 of 1,000 candles unchanged after 101 s |
| 11 | Power arithmetic | `python .../probes/power_simulation.py` | 0 | table in ACCEPTANCE_METRICS.md (seeded, synthetic) |
| 12 | Gap matrix | `python .../probes/build_gap_matrix.py` then `python .../probes/check_gap_anchors.py` | 0, 0 | 88 cells (11 facilities x 8 needs): 16 VERIFIED_PRESENT, 23 PARTIAL, 46 MISSING, 3 CONFLICT, 0 UNKNOWN; `cells 88, facilities 11, needs 8, problems 0` |
| 13 | Checker negative tests | inline harness over temp copies of the CSV | 0 | unchanged copy exit 0; wrong line, bad status, grep that hits, missing cell, missing data key, existing path for a nopath cell: each exit 1 with the right message |
| 14 | Split counts | `python .../probes/split_counts.py origin/main` | 0 | output `split_counts.json` sha256 `d35755bc...` (table in TARGET_REGISTRY.md) |
| 15 | Change control CC-01 tests | `python -m pytest tests/test_predictive_contract.py -q -p no:cacheprovider` | 0 | `21 passed in 0.90s`; registry sha256 now `9f8c9deb...` |
| 16 | CC-01 coverage recompute (offline) | `python .../probes/gt_coverage_recompute.py .../gt_coverage_sample.json <scratch>/gt_raw .../gt_coverage_cc01.json` | 0 | `{"HTTP_429": 1, "INELIGIBLE_NO_RECENT_TRADE": 4, "OK": 5} changed 0` |
| 17 | Mutation check | `python .../probes/mutation_check.py` | 0 | 10 mutations (P46, P34, CC-01, P05, P08, silent barrier edit, P06, P13, PI-D-011 basis, P38), all caught; baseline `21 passed` |
| 18 | Document anchors | `python .../probes/check_doc_anchors.py` | 0 | `anchors 34, problems 0` |
| 19 | Writing style | Python scan of 23 new or changed files for em and en dashes and curly quotes; grep for marketing words | 0 | no hits |
| 20 | Final full suite | `python -m pytest tests -q` (2026-10-24T01:51:40Z) | 1 | `1 failed, 806 passed in 136.72s (0:02:16)`; same single known failure; 806 = 785 + 21 new |
| 21 | Strays after final suite | `git status --porcelain --ignored` | 0 | same four strays, removed by hand; tracked DB unchanged; `git diff --name-only 94be1bf -- inbox state data` empty |
| 22 | Content guard and release tools with new files staged | `python -m pytest tests/test_content_guard.py tests/test_release_tools.py tests/test_predictive_contract.py -q -p no:cacheprovider` | 0 | `38 passed in 5.60s` |

## Sources (links)

- GeckoTerminal public API v2: `https://api.geckoterminal.com/api/v2/networks/solana/pools/{pool}/ohlcv/minute?aggregate=5&limit=1000&before_timestamp={ts}&currency=usd` and `.../networks/solana/tokens/{mint}/pools?page=1`; rate statement in the OpenAPI spec `https://api.geckoterminal.com/docs/v2/swagger.json` (read in Phase 00). Every call, its retrieval time, HTTP status and body sha256 are in `probes/gt_coverage_sample.json`; raw bodies kept outside the repo in `/home/claude/pi_orchestration/phase01/gt_raw/`.
- GitHub REST events: `https://api.github.com/repos/RyzinEnagy/memelab-inbox/events` (pages 1 to 3); push list saved outside the repo (`/home/claude/pi_orchestration/phase01/gh/push_events.json`, sha256 `7dd8c46f956f23d6c2e06ba69797c3e45b3a602ed2d5a06a99848a306d90eec5`).
- No web pages were crawled; no Firecrawl call.

## Acceptance checklist results

| Id | Result | Evidence |
|---|---|---|
| C1 | holds | command 1 |
| C2 | holds | command 3 |
| C3 | holds | command 5 (149 mints, p50 16.92, max 116.5) |
| C4 | holds | commands 12 and 13 |
| C5 | holds | registry committed in `b6f2621` at 01:35:23Z; first GeckoTerminal call 01:36:23Z; the probe computes no barrier or class; three primary targets each with every required field (test `test_registry_is_frozen_and_has_two_to_four_primary_targets`); one change afterwards, CC-01, recorded as change control before any label (PI-D-019) |
| C6 | holds | counts from the exports (commands 5, 14), coverage with retrieval times (command 10), infeasible targets named with the missing data (TARGET_REGISTRY.md "Registered but not primary"); exit-adjusted target BLOCKED and refused by the validator (P08 test) |
| C7 | holds | ACCEPTANCE_METRICS.md; no model fitted, no label built in this phase |
| C8 | holds | PLANNED_SEAMS.md seam table with anchors (command 18); "not reused" table with reasons; ranker isolation and flag rules |
| C9 | holds | DEPENDENCY_GRAPH.md hard ordering rules 1 to 10 |
| C10 | holds | `tests/fixtures/predictive/forecast_examples_format_only.json` (marked FORMAT ONLY); 21 tests pass; P05, P08, P34, P46, P38, P13, P35, P01, P27, P06 covered; mutation check command 17 |
| C11 | holds | `test_no_existing_module_imports_the_predictive_package`, `test_flag_defaults_off_and_needs_an_explicit_true`; command 20 shows no new failure |
| C12 | holds | command 21 |
| C13 | holds pending the orchestrator | this file, PHASE_01_RESULTS.json (parses), SKEPTIC_PACKET.md, ROADMAP row, DECISIONS PI-D-014 to PI-D-020, HANDOFF rewritten; status NEEDS_REVIEW |
| C14 | holds | command 19 |
| C15 | holds | COST_LEDGER.md row for Phase 01 (0 credits); free calls listed above |

## Iteration log

| Pass | What happened | Changed files | Result |
|---|---|---|---|
| 1 | Entry gate; read package, records, Phase 00 outputs and the reuse candidates in code; universe probe and GitHub push check; acceptance checklist; contract, registry, format examples and tests; pre-registration commit; GeckoTerminal coverage probe (coverage only); power arithmetic; gap matrix and checker; split counts; the five architecture documents | everything under `audits/predictive-intelligence/phase_01/`, `memelab/predictive/`, `tests/test_predictive_contract.py`, `tests/fixtures/predictive/` | registry `dd3b4576...`, 19 tests pass |
| 2 | Own adversarial pass (not independent): reviewed the registry against P05, P06, P08, P09, P35, P36, P37, P43; found CC-01 (below); fixed it as recorded change control, added `reference_candle` and `path_candles` with tests, recomputed coverage offline, wrote the mutation check and the checker negative tests, added measurement limits and inference-read SLO | contract.py, tests, TARGET_REGISTRY.md, ACCEPTANCE_METRICS.md, PLANNED_SEAMS.md, new probes | registry `9f8c9deb...`, 21 tests pass, 10 of 10 mutations caught, full suite `1 failed, 806 passed` |
| 3 | Reserved for the orchestrator's independent skeptic (PI-D-013) | | |

## Own adversarial counterexample (not independent)

Claim, plausible and wrong: "A decision is eligible when a trade happened in the hour before entry (decision + 300 s), using the backfilled candles." The backfill is read after the fact, and the window ending at entry includes the five minutes after the decision and candles that had closed but were not yet served (provider lag). A forecaster at the decision cannot reproduce that test, so eligibility (who is in the sample) depended on post-decision trades: a look-ahead in selection that is not a feature leak (P36) and not a label leak (P05). Caught by `tests/test_predictive_contract.py::test_reference_price_uses_only_candles_available_at_the_decision` (a candle ending after the decision, and one ending inside the provider lag, are never the reference; with only such candles the decision is ineligible) and by the mutation "CC-01 reference may use a post-decision candle" in `probes/mutation_check.py`. Fixed by CC-01 (PI-D-019). On the saved coverage sample no decision changed eligibility, so the fix was not driven by a result.

Other attack points examined and how they are handled: decision staleness (snapshot up to 22 h older than its commit) reported as a stratum; vendor-list pool route conditions on survival, flagged and stratified; single-trade wick touches reported; holdout likely below 50 eligible events, stated in advance with the prospective holdout as the real test; GeckoTerminal 429 at about 9 a minute, so 6 a minute is planned.

## Limitations

- The coverage sample has 10 decisions; its rates are signs, not estimates (the 95% Wilson interval for 5 of 9 resolved is 27% to 81%).
- GeckoTerminal retention of 5-minute candles is UNKNOWN beyond the 17 days observed; a late backfill could lose the earliest decisions.
- The provider lag of 300 s is HEURISTIC (replay_sources.PROVIDER_LAG).
- Export commit times for 7 of 89 exports (before 2026-10-08T14:04Z) have no GitHub push event to confirm them; they rest on the committer clock.
- The power arithmetic assumes independent events and a perfectly calibrated model; real detectability is lower.
- The scheduled runs execute `main`; nothing from this branch runs there before Elving merges (PI-D-005).

## Blockers and approvals

- Blockers for Phase 01: none.
- Approvals needed: none for Phase 02. PI-D-020 (forward depth and quote collector, a scheduled job) is PROPOSED for Elving; without it the exit-adjusted and liquidity targets stay BLOCKED or DEFERRED.

## Next

Independent skeptic by the orchestrator, then a repair pass that folds its review into `phase_01/skeptic/` and this file. Next eligible phase after PASS: 02.
