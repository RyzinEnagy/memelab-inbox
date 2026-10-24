# Phase 01 evidence: gap analysis, placement and prediction requirements

| Item | Value |
|---|---|
| Phase | 01, "Freeze the measurable prediction objectives and determine the minimally invasive architecture" |
| Status | PASS after repair pass 2. Was NEEDS_REVIEW at `0decbbe`; the orchestrator's independent skeptic (PI-D-013) found 3 MATERIAL and 8 MINOR findings; each was verified and fixed or answered (section "Independent skeptic"), change control CC-02 (PI-D-021) before any label |
| Branch | `feature/predictive-intelligence` |
| HEAD before | `94be1bf` (Phase 00 repair pass 2, pushed to `origin/feature/predictive-intelligence`) |
| Commits | `b6f2621` pre-registration (2026-10-24T01:35:23Z, before any price data was read); `e64c6ca` content; `27df593`, `ae6a9cb`, `0531044`, `58f3f5b`, `0decbbe` hash bookkeeping; the repair pass 2 commit on top (read with `git log -1`; this file is part of it) |
| Time (UTC) | 2026-10-24T01:22Z to 02:00Z (passes 1 and 2); repair pass 2 02:20Z to 02:50Z |
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
| 6 | GitHub push times | `curl https://api.github.com/repos/RyzinEnagy/memelab-inbox/events?per_page=100&page={1,2,3}` (01:25:35Z to 01:25:52Z) | 0 | HTTP 200 x3; 300 events, 291 pushes, the oldest event 2026-10-08T14:04Z (corrected in repair pass 2: the 206 main pushes span 2026-10-07T14:08Z to 10-20T10:24Z, skeptic M1); 82 of 89 export commits matched; push minus commit 1 to 5 s |
| 7 | Acceptance checklist written | `ACCEPTANCE_CHECKLIST.md` | n/a | 2026-10-24T01:31Z, before any deliverable or GeckoTerminal call |
| 8 | Contract tests (pre-registration) | `python -m pytest tests/test_predictive_contract.py -q -p no:cacheprovider` | 0 | `19 passed in 0.99s` |
| 9 | Pre-registration commit | `git commit` | 0 | `b6f2621` 2026-10-24T01:35:23Z, registry sha256 `dd3b4576...` |
| 10 | GeckoTerminal coverage sample | `python .../probes/gt_coverage_probe.py <universe> <scratch>/gt_raw .../probes/gt_coverage_sample.json` (01:36:22Z to 01:38:05Z) | 0 | 15 calls (14 HTTP 200, 1 HTTP 429 on call 6); sample of 10 seeded decisions: 5 OK, 4 INELIGIBLE_NO_RECENT_TRADE, 1 HTTP_429; routes 6 point-in-time pool, 4 vendor list; revision check 1,000 of 1,000 candles unchanged after 101 s |
| 11 | Power arithmetic | `python .../probes/power_simulation.py` | 0 | table in ACCEPTANCE_METRICS.md (seeded, synthetic) |
| 12 | Gap matrix | `python .../probes/build_gap_matrix.py` then `python .../probes/check_gap_anchors.py` | 0, 0 | 88 cells (11 facilities x 8 needs): first 16 VERIFIED_PRESENT, 23 PARTIAL, 46 MISSING, 3 CONFLICT, 0 UNKNOWN; after repair pass 2 (skeptic M4) 14 VERIFIED_PRESENT, 25 PARTIAL; `cells 88, facilities 11, needs 8, problems 0` |
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
| 23 | Orchestrator's rerun at `0decbbe` (reported by the orchestrator) | `python -m pytest tests -q` | 1 | `1 failed, 806 passed in 136.07s`; DB hash unchanged |
| 24 | CX-S1 reproduced (repair pass 2) | `cd /home/claude/pi_orchestration/skeptic_01 && python /home/claude/pi_orchestration/skeptic/skeptic_01_counterexample.py` | 0 | `LOOK-AHEAD REPRODUCED`: key decision time 15c2087e 21:53:55Z, rows then `[('SETUP DEVELOPING', 69, 0)]`, `state.import_` of the newest export gives REJECTED 60 CLUSTER_OWNERSHIP_GT_25PCT, first shown in 996190ce 22:20:37Z |
| 25 | Row identity statistics with the new rule | `python .../probes/split_counts.py origin/main .../probes/split_counts.json` | 0 | 1,882 distinct rows, 1,801 keys; 122 keys with two or more rows in their first export (60 with different contents); 6 rows (3 keys) first visible after their key; 4 of 278 thinned 24 h events KEY_CONFLICT; split counts unchanged (177/17/58/26, 280/0/79/7, 161/33/49/35); liquidity follow-up 29 of 278 events; 125 of 881 Solana priced events below the stage-1 filter, 77 with 24 h volume under $1,000 |
| 26 | Containing pushes for unconfirmed exports | inline script over `push_events.json` with `git merge-base --is-ancestor`; GitHub `/activity` (skeptic's read) | 0 | 206 of 206 main pushes fast-forward; `996190ce`, `2c6cbf54`, `53a616e1`, `fe8fc3bb` were already the branch tip (`before`) of pushes 886 s, 413 s, 3,609 s, 6,269 s after their commit times; `/activity` shows `6e09bfae`, `1aa6fcd1`, `98338a8b` pushed 2 s after commit |
| 27 | F3 classes on the coverage sample (offline) | `python .../probes/gt_coverage_recompute.py .../gt_coverage_sample.json <scratch>/gt_raw .../gt_coverage_f3.json --eligibility origin/main` | 0 | `{"ELIGIBLE": 5, "MARKET_INACTIVE": 3, "NOT_READ_RATE_LIMITED": 1, "VENDOR_OR_ROUTE_GAP": 1}`; CC-01 mode output unchanged (sha256 `03837ced...`) |
| 28 | Holdout contact | `python .../probes/holdout_contact.py .../gt_coverage_sample.json <scratch>/gt_raw /home/claude/pi_orchestration/skeptic/gt_live` | 0 | exactly 2 holdout decisions (`CnPL1x...` 10-17, `Tm2iq...` 10-19), both coverage-sampled; frozen as excluded |
| 29 | Predictive tests after repair | `python -m pytest tests/test_predictive_contract.py tests/test_predictive_decisions.py -q -p no:cacheprovider` | 0 | `73 passed` |
| 30 | Mutation check after repair | `python .../probes/mutation_check.py` | 0 | `mutations 36, survived or not applied 0` (includes the skeptic's twelve, adapted where the text moved) |
| 31 | Skeptic's own mutation script on the repaired tree | `python /home/claude/pi_orchestration/skeptic/skeptic_01_mutations.py /home/claude/memelab-inbox` | 0 | its baseline now fails (`1 failed, 65 passed`) because it copies `memelab/` and `tests/` but not ACCEPTANCE_METRICS.md, which the new document test reads; 10 caught, 2 not applied (texts moved); `mutation_check.py` copies the document and covers all twelve |
| 32 | Anchors after repair | `check_gap_anchors.py`; `check_doc_anchors.py` | 0, 0 | `cells 88, facilities 11, needs 8, problems 0`; `anchors 34, problems 0` |
| 33 | Final full suite (repair pass 2) | `python -m pytest tests -q` (2026-10-24T02:40:39Z) | 1 | `1 failed, 858 passed in 136.08s (0:02:16)`; same single known failure; 858 = 785 + 73 predictive |
| 34 | Strays and tracked data after the final suite | `git status --porcelain --ignored`; `sha256sum data/memelab.sqlite`; `git diff --name-only 94be1bf -- inbox state data` | 0 | BRETT report, shm, wal, `.pytest_cache/` removed by hand; DB `068287c0...a6679ca` unchanged; no tracked data change |
| 35 | Content guard with every new file staged | `python -m pytest tests/test_content_guard.py tests/test_release_tools.py tests/test_predictive_contract.py tests/test_predictive_decisions.py -q -p no:cacheprovider` | 0 | `90 passed in 6.57s` |

## Sources (links)

- GeckoTerminal public API v2: `https://api.geckoterminal.com/api/v2/networks/solana/pools/{pool}/ohlcv/minute?aggregate=5&limit=1000&before_timestamp={ts}&currency=usd` and `.../networks/solana/tokens/{mint}/pools?page=1`; rate statement in the OpenAPI spec `https://api.geckoterminal.com/docs/v2/swagger.json` (read in Phase 00). Every call, its retrieval time, HTTP status and body sha256 are in `probes/gt_coverage_sample.json`; raw bodies kept outside the repo in `/home/claude/pi_orchestration/phase01/gt_raw/`.
- GitHub REST events: `https://api.github.com/repos/RyzinEnagy/memelab-inbox/events` (pages 1 to 3); push list saved outside the repo (`/home/claude/pi_orchestration/phase01/gh/push_events.json`, sha256 `7dd8c46f956f23d6c2e06ba69797c3e45b3a602ed2d5a06a99848a306d90eec5`). The skeptic's GitHub `/activity` read is at `/home/claude/pi_orchestration/skeptic/gh_live/activity_main.json`; its two GeckoTerminal re-reads at `/home/claude/pi_orchestration/skeptic/gt_live/` (outside the repo; raw bodies with prices are never committed).
- No web pages were crawled; no Firecrawl call.

## Acceptance checklist results

| Id | Result | Evidence |
|---|---|---|
| C1 | holds | command 1 |
| C2 | holds | command 3 |
| C3 | holds | command 5 (149 mints, p50 16.92, max 116.5) |
| C4 | holds | commands 12, 13 and 32; two cells corrected to PARTIAL (skeptic M4) |
| C5 | holds | targets and nine constants committed in `b6f2621` at 01:35:23Z; first GeckoTerminal call 01:36:23Z; the probe computes no barrier or class; three primary targets each with every required field (test `test_registry_is_frozen_and_has_two_to_four_primary_targets`); two changes afterwards, CC-01 (PI-D-019) and CC-02 (PI-D-021), both recorded as change control before any label |
| C6 | holds | counts from the exports (commands 5, 14), coverage with retrieval times (command 10), infeasible targets named with the missing data (TARGET_REGISTRY.md "Registered but not primary"); exit-adjusted target BLOCKED and refused by the validator (P08 test) |
| C7 | holds | ACCEPTANCE_METRICS.md; every rule inside the fingerprint since CC-02, the document block checked by a test, 19 loosening edits shown to change the fingerprint; no model fitted, no label built in this phase. Stated in the document: rules beyond the first nine constants were first written after the coverage probe read ten price bodies (no outcome computed) |
| C8 | holds | PLANNED_SEAMS.md seam table with anchors (command 18); "not reused" table with reasons; ranker isolation and flag rules |
| C9 | holds | DEPENDENCY_GRAPH.md hard ordering rules 1 to 10 |
| C10 | holds | `tests/fixtures/predictive/forecast_examples_format_only.json` (marked FORMAT ONLY; the checklist's first path was wrong, corrected there); one test per validator rule; P05, P08, P34, P46, P38, P13, P35, P01, P27, P06, MODEL_STALE covered; mutation check command 30 |
| C11 | holds | `test_no_existing_module_imports_the_predictive_package` now walks the syntax tree (plain, from-import, relative, `import_module` and `__import__` strings; `test_the_isolation_check_sees_every_import_form`); `test_flag_defaults_off_and_needs_an_explicit_true`; command 33 shows no new failure. The flag gates nothing yet (Phase 17) |
| C12 | holds | commands 21 and 34 |
| C13 | holds | this file, PHASE_01_RESULTS.json (parses), SKEPTIC_PACKET.md (marked USED), skeptic review and scripts in `skeptic/`, ROADMAP row, DECISIONS PI-D-014 to PI-D-022, HANDOFF rewritten |
| C14 | holds | command 19 |
| C15 | holds | COST_LEDGER.md row for Phase 01 (0 credits); free calls listed above; repair pass 2 made no external call |
| C16 | holds | decision records keyed on the exact row: `memelab/predictive/decisions.py`, `tests/test_predictive_decisions.py` (7 tests on the real CX-S1 rows), mutation "decision identity keyed on (mint, created_at) only" caught |
| C17 | holds | eligibility classes in `contract.eligibility`, `test_eligibility_never_turns_a_vendor_or_route_gap_into_a_quiet_market`; registry, dependency graph and code agree; sample counts in command 27 |
| C18 | holds | contacted holdout decisions listed (command 28) and frozen as excluded (`ACCEPTANCE["holdout_contacted"]`) |

## Iteration log

| Pass | What happened | Changed files | Result |
|---|---|---|---|
| 1 | Entry gate; read package, records, Phase 00 outputs and the reuse candidates in code; universe probe and GitHub push check; acceptance checklist; contract, registry, format examples and tests; pre-registration commit; GeckoTerminal coverage probe (coverage only); power arithmetic; gap matrix and checker; split counts; the five architecture documents | everything under `audits/predictive-intelligence/phase_01/`, `memelab/predictive/`, `tests/test_predictive_contract.py`, `tests/fixtures/predictive/` | registry `dd3b4576...`, 19 tests pass |
| 2 | Own adversarial pass (not independent): reviewed the registry against P05, P06, P08, P09, P35, P36, P37, P43; found CC-01 (below); fixed it as recorded change control, added `reference_candle` and `path_candles` with tests, recomputed coverage offline, wrote the mutation check and the checker negative tests, added measurement limits and inference-read SLO | contract.py, tests, TARGET_REGISTRY.md, ACCEPTANCE_METRICS.md, PLANNED_SEAMS.md, new probes | registry `9f8c9deb...`, 21 tests pass, 10 of 10 mutations caught, full suite `1 failed, 806 passed` |
| 3 (repair pass 2) | Folded in the orchestrator's independent skeptic: reproduced CX-S1, verified every finding against code and data, wrote `decisions.py` and its tests, froze the whole acceptance plan with a document check, split eligibility into three classes, listed and excluded the contacted holdout decisions, tightened the validator, corrected two matrix cells and the M1, M5, M6 statements; change control CC-02 (PI-D-021) and later-phase requirements (PI-D-022) | contract.py, decisions.py (new), both test files, fixtures, ACCEPTANCE_METRICS.md, TARGET_REGISTRY.md, PLANNED_SEAMS.md, DEPENDENCY_GRAPH.md, GAP_MATRIX.csv, probes, records, `skeptic/` | registry `91d03c76...`, 73 predictive tests pass, 36 of 36 mutations caught, full suite `1 failed, 858 passed` |

## Own adversarial counterexample (not independent)

Claim, plausible and wrong: "A decision is eligible when a trade happened in the hour before entry (decision + 300 s), using the backfilled candles." The backfill is read after the fact, and the window ending at entry includes the five minutes after the decision and candles that had closed but were not yet served (provider lag). A forecaster at the decision cannot reproduce that test, so eligibility (who is in the sample) depended on post-decision trades: a look-ahead in selection that is not a feature leak (P36) and not a label leak (P05). Caught by `tests/test_predictive_contract.py::test_reference_price_uses_only_candles_available_at_the_decision` (a candle ending after the decision, and one ending inside the provider lag, are never the reference; with only such candles the decision is ineligible) and by the mutation "CC-01 reference may use a post-decision candle" in `probes/mutation_check.py`. Fixed by CC-01 (PI-D-019). On the saved coverage sample no decision changed eligibility, so the fix was not driven by a result.

Other attack points examined and how they are handled: decision staleness (snapshot up to 22 h older than its commit) reported as a stratum; vendor-list pool route conditions on survival, flagged and stratified; single-trade wick touches reported; holdout likely below 50 eligible events, stated in advance with the prospective holdout as the real test; GeckoTerminal 429 at about 9 a minute, so 6 a minute is planned.

## Independent skeptic (orchestrator-run, folded in by repair pass 2)

Review and scripts: `skeptic/PHASE_01_SKEPTIC.md` and `skeptic/skeptic_01_*.py` with their outputs (copied unchanged; the skeptic's live GeckoTerminal bodies and GitHub `/activity` read stay outside the repo). Its numbers for counts, clocks, splits, power and coverage re-derived the phase's exactly.

| Finding | Verified | What changed | Now caught by |
|---|---|---|---|
| F1 MATERIAL: `(mint, created_at)` is not a point-in-time identity | yes: CX-S1 reproduced (command 24); 122 keys with several rows in their first export (60 distinct), 6 late rows of 3 keys | `memelab/predictive/decisions.py`: identity `(mint, created_at, row_sha256)`, time = first export holding the exact row, newest visible row per commit, KEY_CONFLICT flag and sensitivity; registry, PI-D-015 amended (PI-D-021) | `tests/test_predictive_decisions.py` (built from the real rows), mutations "decision identity keyed on (mint, created_at) only", "same-time tie broken by last position", "KEY_CONFLICT never flagged", "revision of the newest key becomes the decision row" |
| F2 MATERIAL: most of the acceptance plan was outside the fingerprint | yes: only nine constants were hashed; the rest were first written in `e64c6ca`, after the coverage probe | every rule moved into `ACCEPTANCE`; the document carries it verbatim; timing stated plainly (CC-02) | pinned fingerprint, `test_loosening_any_frozen_acceptance_rule_changes_the_fingerprint` (19 edits), `test_acceptance_document_carries_the_frozen_block_verbatim`, mutations on code and document |
| F3 MATERIAL: vendor or route gaps silently dropped as "no recent trade" | yes: the BAT decision (`CqjaL6...`, $94,115 of lab-recorded 24 h volume) had no vendor candle that day on a vendor-list pool | `contract.eligibility`: ELIGIBLE, MARKET_INACTIVE (evidence available at the decision), VENDOR_OR_ROUTE_GAP (censored, counted, conservative lens); registry and dependency graph agree | `test_eligibility_never_turns_a_vendor_or_route_gap_into_a_quiet_market`, mutations "vendor gap called a quiet market", "quiet-route evidence accepted from a vendor-list pool"; sample: 5 / 3 / 1 / 1 not read |
| M1 export times misdescribed | partly: the three newest are confirmed by `/activity` (2 s); for the other four the event feed shows them already as the branch tip (`before`) 413 s to 6,269 s after commit, so these are upper bounds on public availability, not the time of a later push as the review says | wording in registry, evidence, PI-D-021 item 6; fast-forward check recorded (206 of 206) | command 26 |
| M2 contract rules not pinned | yes: 10 of the skeptic's 12 mutations survived | one test per rule with its exact message; AST-based isolation test | all twelve in `mutation_check.py`, caught |
| M3 validator accepts documents the text rules out | yes, each case reproduced | exact field set, exact address match (Solana and EVM) on every document, base-rate range on ABSTAIN, MODEL_STALE, cutoff from the model card; remaining checks assigned to later phases (PI-D-022) | tests per case; mutations "MODEL_STALE not enforced", "model card cutoff not compared", "mint regex matches a trailing newline", "unknown top-level fields allowed" |
| M4 two VERIFIED_PRESENT cells overstated | yes: only tests call m27/m28; the cutoff view is fixture-only and social-only | both cells PARTIAL | `check_gap_anchors.py` (anchors); statuses read against code by hand |
| M5 "53 of 351" counts rows | yes: 29 of 278 events with this rule (the skeptic's own definition gave 30) | registry, `TARGETS` text, PI-D-020 | `split_counts.py` |
| M6 universe filter statement untrue | yes: 125 of 881 Solana priced events below the stage-1 filter, 77 under $1,000 of 24 h volume. Disagreement: the review says all four sampled ineligible decisions have 24 h volume under $1,000; the BAT one had $94,115, as its own F3 states | ACCEPTANCE_METRICS.md statement | `split_counts.json` |
| M7 holdout contact before the seal | yes: exactly `CnPL1x...` 10-17 and `Tm2iq...` 10-19 (empty stretches counted as contact) | both excluded from the primary retrospective holdout, frozen in `ACCEPTANCE["holdout_contacted"]`, reported as a sensitivity | `holdout_contact.py`; fingerprint test edit "contacted holdout decisions readmitted" |
| M8 housekeeping | yes | checklist correction appended, empty `contract/` folder removed, no default chain in the probe, flag wording | review of the files |

### Counterexample CX-S1 and what catches it now

The skeptic's wrong-but-plausible step: build decision records by importing the newest export through `state.import_`, join on `(mint, created_at)`, and give each the key's first export time. For mint `6GmAFSYs...` and key `1791331150.554` that attaches a REJECTED row with fatal flag CLUSTER_OWNERSHIP_GT_25PCT, first exported in `996190ce` at 2026-10-07T22:20:37Z, to the 21:53:55Z decision time of `15c2087e`, where only a SETUP DEVELOPING row existed. The existing `state.import_` seam is unchanged and still does that, so the plan forbids it for decisions (DEPENDENCY_GRAPH rule 1, PLANNED_SEAMS). The executable catch is `tests/test_predictive_decisions.py::test_cx_s1_a_row_first_exported_later_never_inherits_its_key_time` on the real rows (fixture `tests/fixtures/predictive/cx_s1_exports.json`): it fails under the old rule (mutation check), and `test_every_candidate_row_exists_in_the_export_at_its_first_visible_time` states the general invariant.

## Limitations

- The coverage sample has 10 decisions; its rates are signs, not estimates (the 95% Wilson interval for 5 of 9 resolved is 27% to 81%).
- GeckoTerminal retention of 5-minute candles is UNKNOWN beyond the 17 days observed; a late backfill could lose the earliest decisions.
- The provider lag of 300 s is HEURISTIC (replay_sources.PROVIDER_LAG).
- Export commit times are a bound on when the row existed (committer clock). As public availability they hold within 5 s for 85 of 89 exports (push events and GitHub `/activity`); for `996190ce`, `2c6cbf54`, `53a616e1`, `fe8fc3bb` only upper bounds of 886 s to 6,269 s after commit exist (PI-D-021 item 6).
- The coverage sample does not show how often VENDOR_OR_ROUTE_GAP will occur in the population; Phase 06 measures it, and a high rate weakens every result through censoring.
- The power arithmetic assumes independent events and a perfectly calibrated model; real detectability is lower.
- The scheduled runs execute `main`; nothing from this branch runs there before Elving merges (PI-D-005).

## Blockers and approvals

- Blockers for Phase 01: none.
- Approvals needed: none for Phase 02. PI-D-020 (forward depth and quote collector, a scheduled job) is PROPOSED for Elving; without it the exit-adjusted and liquidity targets stay BLOCKED or DEFERRED.

## Next

Phase 01 is PASS after repair pass 2. Next eligible phase: 02 (independent predictive GitHub discovery), after the orchestrator's verification.
