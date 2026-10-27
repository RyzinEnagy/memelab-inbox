# Phase 19 evidence: outcome tracking, prospective replay and model drift

Status: **NEEDS_REVIEW** after repair pass 2, with one open gate item (G25, the frozen 48 h revision re-read, due from 2026-10-29T14:35Z, PI-D-106). Every Phase 19 outcome and number is PROVISIONAL_PENDING_REVISION_REREAD. The first-pass sections below are kept as written; the repair pass is the last section. Branch `feature/predictive-intelligence`; HEAD before `4b07b0d`; work 2026-10-27 13:05Z to about 14:55Z. Decisions PI-D-104 (rules) and PI-D-105 (result).

## Entry gate

| Check | Command | Result |
|---|---|---|
| Package checksums | `sha256sum -c SHA256SUMS.txt` | every file OK |
| Full suite at `4b07b0d` | `python -m pytest tests -q -p no:cacheprovider` | exit 1, `2 failed, 2145 passed, 1 skipped, 1 warning in 466.03s`: only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` and `tests/test_catalyst_firecrawl.py::test_page_history_and_spend_survive_a_new_session_through_the_state_export`; strays removed by hand |
| Seal | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | exit 0, `"problems": []` |
| Phase 18 status | `PHASE_18_RESULTS.json` | PASS, 31 checks, 0 failed |
| Predecessor key check | `unshare -n python -B audits/predictive-intelligence/phase_17/probes/run_integration.py replay` | exit 0; 52 events, 156 ABSTAIN documents, 0 probabilities; documents `9b839e76...` and records `a8114c19...` byte-equal to the Phase 18 published run (`evidence/entry/p17_export_replay_at_head.json`) |
| Prior contact, metadata only | `probes/contact_scan.py` | two sealed Phase 06 reads end 8.2 and 13.2 minutes after two prospective entries; one prospective mint had measured changes printed by the Phase 18 replay report (`evidence/entry/prospective_contact_scan.json`) |

## What was built

- `memelab/predictive/monitoring.py` (monitoring-1, sha256 `4de67f85...`): the outcome ledger `outcome-ledger-1` (canonical JSON lines with `seq`, `prev`, `sha`; `append` validates every payload; `load` and `verify` replay every rule), the append rules of checklist rule 4 (PREDICTION_EDIT_REFUSED, LATE_PREDICTION_REFUSED, NOT_YET_MATURED, FINAL_OUTCOME_REPLACED, SUPERSEDE_REQUIRED, IDENTITY_MISMATCH, OUTCOME_WITHOUT_PREDICTION, CONCURRENT_WRITE, token=<mint> on every labelled read), `current_outcomes`, `scorable` (LABELED, uncensored, matured only), `prospective_records` (labels-1 `build` then `classify` for the prospective split, the same steps `build` applies to development and holdout decisions), `outcome_payload` and `next_outcomes` (supersede or revise, never edit), drift monitors D1 to D8, `response`, `notice`, `misses`. Imports numpy, the standard library, `contract`, `stats`, `labels`, `baselines`; imported by no module.
- `tests/test_predictive_monitoring.py` (30 tests) and `tests/test_predictive_phase19_outputs.py` (7 tests on the committed outputs).
- Probes: `run_prospective.py` (inputs, predict through the unchanged Phase 12 `cmd_predict` with its window end, input class and file names set by the runner, outcomes, evaluate, drift, rollback, audit, report), `fetch_labels.py` (opening check, paced reads, re-read, archive), `mutation_monitoring.py`, `contact_scan.py`, `rebuild_outcomes.py` (added after the runs; an independent offline check).

## Commits and order (checklist rule 1)

| Step | Commit or time (UTC) |
|---|---|
| Pre-registration (checklist, registry, plan, PI-D-104) | `5ffa5cf` 13:30:09Z |
| Frozen code | `fce102e` 13:57:02Z |
| Predictions (4,257 rows, 156 documents, 356 ledger entries, no OUTCOME) | `765eadb` 14:00:20Z |
| Opening logged (FIRST_OPENING, head `765eadb`) | 14:00:26Z |
| Label calls | first 14:00:26Z, last 14:35:15Z |
| Outcomes appended | 14:35:37Z |
| Outputs | `b1a18f7` 14:43:53Z |

`run_prospective.py audit` checks the order from git: the predictions commit time precedes the first call and the ledger at that commit holds no OUTCOME (`monitoring/FEEDBACK_AUDIT.json`). The first `fetch` invocation was stopped by the session's 10-minute command limit at 14:11:43Z while it slept after a 502 (no call in flight; the read map is saved after every read); the run was resumed in the background and completed.

## Commands and exits (recorded runs at `fce102e`)

| Command | Exit | Result |
|---|---|---|
| `unshare -n python -B probes/run_prospective.py inputs` | 0 | store copies from the recorded Phase 05 and 06 stores (sha256 checked), exports to `71fc50e` ingested (52 fs and 34 dev decisions added), 52 snapshots per mode, contact check 0 problems (`evidence/inputs.json`) |
| `unshare -n python -B probes/run_prospective.py predict monitoring` | 0 | 4,257 rows (33 decisions x 3 targets x 43 candidates), traps 0 failures, replay audit ok (card age at most 9.43 days), P46 equal, 156 documents byte-equal to the published run, 356 ledger entries |
| second `predict` into the scratchpad | 0 | every file byte-equal except the manifest, which also lists the plan file of the committed folder (`evidence/determinism_predict.json`) |
| `python -B probes/fetch_labels.py open`, `lists`, `fetch`, `others`, `reread`, `archive` | 0 | 44 calls (at most 5 in any 60 s); 28 planned decisions read through 25 distinct OK reads; 0 T2 records needed other pools; re-read of 3 reads 7 to 21 minutes later: 2,996 candles, 0 changed; 40 archived files |
| `unshare -n python -B probes/run_prospective.py outcomes` | 0 | 156 records, cross-target violations 0, 156 OUTCOME entries (ledger 512), verify ok, prospective rows in `training_labels` 0 per target |
| `... evaluate monitoring` | 0 | every verdict INSUFFICIENT_DAYS; N_search 130 |
| `... drift monitoring`, `rollback`, `audit`, `report` | 0, 0, 0, 0 | see below |
| `unshare -n python -B probes/rebuild_outcomes.py evidence/rebuild_outcomes.json` | 0 | 35 OHLCV bodies re-ingested with equal response keys; 156 of 156 outcomes equal to the ledger |
| `python -B probes/mutation_monitoring.py evidence/mutation_monitoring.json` | 0 | 46 of 46 caught (pre-freeze: 41 of 46; the five survivors killed by new tests before the freeze) |

## Results

Prospective window: 52 decisions (33 Solana, 30 mints; 19 EVM out of scope), decision days 2026-10-24, -25, -26.

| Target | Labelled | Positives | Days | Other states (Solana) | Brier B2 | Brier B0 | BSS (descriptive) | Verdict |
|---|---:|---:|---:|---|---:|---:|---:|---|
| T1 24 h | 22 | 5 | 3 | MARKET_INACTIVE 3, NO_SNAPSHOT_PRICE 5, THINNED 2, VENDOR_OR_ROUTE_GAP 1 | 0.1296 | 0.1761 | +0.264 | INSUFFICIENT_DAYS |
| T1b 6 h | 24 | 3 | 3 | MARKET_INACTIVE 3, NO_SNAPSHOT_PRICE 5, VENDOR_OR_ROUTE_GAP 1 | 0.1058 | 0.1095 | +0.033 | INSUFFICIENT_DAYS |
| T2 24 h | 15 | 3 | 2 | PENDING 7, MARKET_INACTIVE 3, NO_SNAPSHOT_PRICE 5, THINNED 2, VENDOR_OR_ROUTE_GAP 1 | 0.0931 | 0.1602 | +0.419 | INSUFFICIENT_DAYS |

- No claim. The verdict order is frozen: fewer than 5 decision days gives INSUFFICIENT_DAYS before any interval is read; no day interval exists, the one-sided p values and their Holm adjustment are undefined, and every count is far below 50 events with 10 per class. The positive point estimates (T1, T2) rest on 5 and 3 positives over 3 and 2 days; the mint intervals (T1 0.036 to 0.498, T2 0.117 to 0.761) are not the governing interval and are not a test. The retrospective holdout gave B2 against B0 BSS -0.024 (T1) and -0.083 (T1b) on 66 and 68 events. Nothing is promoted, calibrated or published; VALIDATED_EXPERIMENTAL is not reached.
- Secondary family: 105 card comparisons, all INSUFFICIENT_DAYS, selection status NO_UNCORRECTED_SKILL (Bonferroni over 130; max-T not computed below 5 days). NC1 mean BSS -0.041, -0.029, -0.069, INSUFFICIENT_DAYS. Sensitivities (conservative lens, no key conflict, PIT only, new mints, contact excluded): all INSUFFICIENT_DAYS.
- Calibration in the large of B2 inside the Wilson interval for all three targets (n 22, 24, 15; no bins below 40 events). AUC and average precision not computed (fewer than 10 per class), named in the report (P10).
- System documents: 156, all ABSTAIN; publication coverage 0%; every pair's outcome sits beside its document in `MISSES.csv` (ABSTAIN_NOT_SCORED 61, OUT_OF_SCOPE_CHAIN 57, NO_SNAPSHOT_PRICE 15, MARKET_INACTIVE 9, PENDING 7, THINNED 4, VENDOR_OR_ROUTE_GAP 3).
- Drift (`monitoring/DRIFT_REPORT.json`): D1 PSI of the fatal-flag column 0.066 (OK), other four B2 columns INSUFFICIENT_DATA (28 or 29 finite values against the minimum 30; missing share 0.15 against 0.0, below the 0.20 alert); D2 and D3 OK for T1 and T1b, INSUFFICIENT_DATA for T2; Page-Hinkley INSUFFICIENT_DATA; D4 OK (28 of 28 against 85 of 86 on the retrospective holdout); D5 SUPPORT_BELOW_MINIMUM; D6 SOURCE_FAILURE (11 of 39 read attempts failed: 429 x4, 504 x3, 502 x2, network x2; all retried, every planned decision read) and COLLECTOR_NOT_DEPLOYED; D7 OK (all QUIET/RISK_OFF, a label seen in training); D8 OK, 3.39 days to MODEL_STALE. Response KEEP_ABSTAIN_SOURCE for every target, notices plain, nothing retrained, nothing rewritten (MONITOR and RESPONSE ledger entries).
- Rollback demo (fixtures through `registry.serve` and `rollback_event`, TEST_ONLY): a Page-Hinkley alarm on a pinned VALIDATED_EXPERIMENTAL fixture gives DRIFT_ALERT blocking, `rollback_required`, response DEGRADE_TO_SHADOW, rollback to the earlier SHADOW pin; a second alarm gives ROLLBACK_TO_ABSTAIN to NO_VIABLE_CHAMPION; earlier pins resolve unchanged; the log only grows.
- Feedback and selection (F1 to F5): the REF tree has no `memelab/predictive/` and no `data/config.json` (forecasts cannot steer the watchlist); evaluation on every scorable decision, never an alerted subset; 156 of 156 pairs have an outcome; documents and records byte-equal to the published run; short-gap re-read 0 of 2,996 candles changed, the frozen 48 h re-read owed.
- Forward depth collector (feature/backtesting at `69bc5c3`, D-BT-034 and D-BT-035): built, pushed and reviewed, not deployed on Elving's computer; the hourly task created 2026-10-26 runs four steps without `collect`. No depth snapshot exists for the window (two live test runs on 2026-10-25 are evidence files on that branch, not a series). Depth, liquidity, catalyst and distribution outcomes: EXECUTION_DATA_MISSING, COLLECTOR_NOT_DEPLOYED.

## Gate items

| Id | Result |
|---|---|
| G1 | held (entry gate table) |
| G2 | held: `5ffa5cf` precedes any Phase 19 code, prediction and read |
| G3 | held: recorded runs at `fce102e`; `rebuild_outcomes.py` and the outputs test were added after the runs and change no output |
| G4 | held: contact check 0 problems; window snapshots at version 2 and the cards' feature set sha |
| G5 | held: 4,257 rows, traps 0, replay audit ok, 0 MODEL_STALE |
| G6 | held: 156 documents and records byte-equal; DOCUMENT entries before any read |
| G7 | held: opening after the commit; 44 calls, at most 5 a minute; token=<mint>; archive with manifest |
| G8 | held: 156 outcomes, labels-1 unchanged, rebuild equal; PENDING and censored never scored |
| G9 | held: verify ok; negative tests and CX-19 pass |
| G10 | held: rule 7 exactly; INSUFFICIENT_DAYS everywhere |
| G11 | held: report sections 1 to 3 |
| G12 | held with two self-review notes (below) |
| G13 | held on fixtures (TEST_ONLY part) |
| G14 | held |
| G15 | held |
| G16 | held: `monitoring/PROSPECTIVE_PLAN.md` |
| G17 | held |
| G18 | held: only new files plus DECISIONS, ROADMAP, HANDOFF and COST_LEDGER changed; no lab module touched |
| G19 | held: 46 of 46 |
| G20 | held: 3,573 ledger rows (217 for Phase 19), N_search 130 (169); the outputs commit message said 3,544 rows, which was wrong |
| G21 | held: cost ledger row, spend 0 |
| G22 | held at the records commit `aefbea6`: suite `2 failed, 2182 passed, 1 skipped in 472.06s` (the two known clock-dependent failures only; strays removed by hand), guard exit 0 with 0 violations over 2,828 files, seal check exit 0 with `"problems": []`, single-branch release audit exit 0 "Needs action: no." (`postcommit/`) |
| G23 | held: 0 prospective rows in `training_labels` |
| G24 | held |

## Self-review (not independent)

- SR-1 (D6 wording): the checklist says "a share of label reads that failed", the code counts failed attempts, retried ones included. Here 11 of 39 attempts failed while 0 of the 25 final reads did; the code's reading is the stricter one and only adds a visible status to an abstention already in force. Left as frozen; a change control would be needed to count final reads.
- SR-2 (D1 summary): the monitor's overall state is the worst column state among OK, WATCH, DRIFT_ALERT and INSUFFICIENT_DATA, so one computable column shows OK while four columns are INSUFFICIENT_DATA. The per-column states are in the report. Left as frozen; noted for the repair pass.
- SR-3 (expectation): the checklist expected D1 INSUFFICIENT_DATA and D6 OK for exports; D1's fatal-flag column computed (33 values) and D6 raised SOURCE_FAILURE from vendor errors. Both are results, not changes.
- SR-4 (window): two of the prospective mints were partly contacted by public sealed reads (first 8 and 13 minutes of the path) and one by printed measured changes; the CONTACT_EXCLUDED sensitivity removes them; nothing in the predictions depends on them (the predictions were committed before any read and come from as-of inputs).
- Carried: Phase 18 minor 5 (recompute a FORECAST point in a reader, or sign the state) is not done; no FORECAST exists. Phase 20.

## Counterexample CX-19

A backdated prediction appended after its outcome with an early time claim. Caught by rule 4(c) in `check_payload` (sequence order, not time), by `load`/`verify` replaying the rules on a ledger written around `append`, and by the git order check of `audit`. Test: `tests/test_predictive_monitoring.py::test_cx19_a_backdated_prediction_after_its_outcome_is_refused_whatever_time_it_claims`; mutation R2 (the late check removed) is caught.

## Iteration log

1. Pass 1 (13:05Z to 13:30Z): entry gate, contact scan, feasibility of the input build (scratch, recorded as a debug row), pre-registration.
2. Pass 2 (13:30Z to 13:57Z): code and tests; debug runs on real data without labels (two input builds: a contact-check error fixed; two predict runs: a document-record link fixed); a synthetic dry run of evaluate, drift, rollback and report with random SYNTHETIC outcomes (D6 separated from drift, `load` made strict); mutation probe 41 of 46, five survivors killed by new tests, 46 of 46; frozen at `fce102e`.
3. Pass 3 (13:57Z to 14:44Z): recorded inputs and predictions, commit, opening, reads, outcomes, evaluation, drift, rollback, audit, report, offline rebuild, outputs test, commit `b1a18f7`.
4. Pass 4: records `aefbea6` and post-commit checks (suite, guard, seal, single-branch release audit), recorded in the commit after it.

## Artifacts (sha256)

| Path | sha256 |
|---|---|
| memelab/predictive/monitoring.py | 4de67f8560e2117fdaaadae0b7950f5fc7bec8a4cf1bfa94f57d508f4a35c16b |
| tests/test_predictive_monitoring.py | d2876e9ca919794efd56bac8232704b22d2af6425d0b02fa3b7c88aafb4c1e76 |
| tests/test_predictive_phase19_outputs.py | 544daf9995ca5fd7b17d330b83bde3aecf07828704786745220f6b0618d25e91 |
| phase_19/ACCEPTANCE_CHECKLIST.md | e59dfe79cfa3b82ba818303332ee16862fd5119188fcce4c6a9d91ffb9fdf7a1 |
| phase_19/experiments/EXPERIMENT_REGISTRY.csv | 96e707be6f6bcbf6051e06199e0793ccd7146548755ddfa55b7809a171a13d91 |
| phase_19/monitoring/PROSPECTIVE_PLAN.md | 710e46e20bd7215a87ea908aa307a278a4333900a2d54ee40e49207ddb78dc1d |
| phase_19/monitoring/OUTCOME_LEDGER.jsonl | c36128466eef09d6204520b1f66cf0c38d752e22f7ac4fb3749ace3eef0c4e6b |
| phase_19/monitoring/OUTCOME_LEDGER.md | b7d48b987817d017e7389291ea416d3eb6d80229928b18de39bbd4e008a604b2 |
| phase_19/monitoring/PROSPECTIVE_REPORT.md | 1589d42ba8d1c973139ee1f5749b162458b1e0aa7fe9b81e27340382c276835a |
| phase_19/monitoring/PROSPECTIVE_PREDICTIONS.csv | b0c2722afba20b15ffb82cd0d9d07f8f370144f0f5a9e8ba779fbb6d2c2b67d0 |
| phase_19/monitoring/PREREG_MANIFEST.json | fbdc025cdcb570d4d60423415b47f704460e576c8d0f301574214cbe74393012 |
| phase_19/monitoring/DRIFT_REPORT.json | ff3ed09513178bf6870695cb6bb38b7254da6c9096dc2692d740186758a838aa |
| phase_19/monitoring/ROLLBACK_DEMO.json | f73ee715f139d5d2320659a42ef3870acfd12dcc127c091fa91819a9136e4daa |
| phase_19/monitoring/FEEDBACK_AUDIT.json | a108d56a8bc973b479e26980cc74e775ae7d2063ef939f55a351e8dc15a81eae |
| phase_19/monitoring/MISSES.csv | 83c0f230314a5de10a95060d42637f0e3f43eefef034849fbd08e66e359c5224 |
| phase_19/monitoring/PROSPECTIVE_METRICS.csv | 0a5db128466b7a3a59274a626e419d1ce0e5d26767bef52fb896041bdb03a1cd |
| phase_19/monitoring/PRIMARY_RESULTS.json | 55ecd43f8ef911304eb5aa17e135b013b0cfe5288d50afbff487e104d5332bf1 |
| phase_19/monitoring/OPENING_LOG.json | ff497505e767868c0eed489fbd66bdc584e5540a81bcd2f9bdfed0b5c44400ab |
| phase_19/evidence/label_calls.json | 7b000569ff92cc2dd6d5b05170200c98d7c991071908c0e8c946aa5767159eda |
| phase_19/raw/MANIFEST.csv | b9b10f9cc614f7356594fd2cbcaddd980bab984773f745449f7960660b01f92f |
| phase_19/experiments/SEARCH_LEDGER.csv | ad4498b75e75e76cc22d64575246b023070198afdecad05d6554f6d6cd3995b9 |

## Sources

- GeckoTerminal public API (free): `https://api.geckoterminal.com/api/v2/networks/solana/pools/<pool>/ohlcv/minute?aggregate=5&limit=1000&before_timestamp=<b>&currency=usd&token=<mint>` and `.../tokens/<mint>/pools?page=1`; every call in `evidence/label_calls.json`.
- Repository `https://github.com/RyzinEnagy/memelab-inbox`: state exports on `main` up to `71fc50e`; `feature/backtesting` at `69bc5c3` (`docs/backtesting/DECISIONS.md` D-BT-034, D-BT-035; `docs/backtesting/HANDOFF.md`).

## Limitations

- Three decision days and at most 24 labelled events per target: no directional statement is possible under the frozen rules; the frozen cards go stale on 2026-10-31.
- T2 of the 2026-10-26 decisions pending; the frozen 48 h re-read owed.
- Self-review notes SR-1 and SR-2; the champion drift response and rollback are fixtures only (no champion exists); no FORECAST outcome can be tracked because none exists.
- Depth, liquidity, catalyst and distribution outcomes unavailable (collector not deployed; tables not exported).

## Repair pass 2 (CP19-1, PI-D-106 to PI-D-108)

The orchestrator's independent skeptic (`skeptic/PHASE_19_SKEPTIC.md`, at `6258fc0`; scripts beside it) found 2 MATERIAL, 7 minor and counterexample CX-SK19. Each was reproduced on `fce102e` before any change (CX-SK19 appended and verified; attacks A3, A4, A5, A6, A7 and A8b accepted; 10 of 14 own mutations surviving).

| Finding | Verified | Repair | What catches it now |
|---|---|---|---|
| M1 frozen 48 h re-read scoped out of the gate | yes: no gate item, no frozen command, no sample | orchestrator decision PI-D-106: gate item G25, frozen command `fetch_labels.py reread48` (refuses before 48 h after each first read), frozen sample `data/revision_sample.json` (sha256 `11874dd9...`, 3 of 25 OK reads, 8 LABELED outcomes, earliest 2026-10-29T14:14:24Z to 14:26:44Z), results PROVISIONAL_PENDING_REVISION_REREAD, a changed label reruns the scoring from frozen code | the command refused at 15:2xZ before any call ("too early"); an offline simulation on scratch copies gave 0 revisions with unchanged bodies and 1 revision (citing the new read, ledger verifying) with halved lows. G25 stays open |
| M2 9 non-equivalent mutation survivors | yes (10 of 14 survive on `fce102e`) | 16 repair tests; the skeptic's 14 mutations and 11 repair mutations join the probe | `evidence/mutation_monitoring.json`: 71 of 71 caught (K3 is pinned on an index built without the rules) |
| CX-SK19 and m1 revision citing the read it revises, or no read | yes | rule 4(e) enforced: a revision or supersede cites a read with another response key and body sha256, captured later, token URL; an unread gap only at or after maturity | `test_cx_sk19_*` (fail on `fce102e`); the skeptic's script now raises REVISION_NEEDS_A_LATER_READ; A5, A6, A7 refused (`evidence/rp2_skeptic_attacks.json`) |
| m2 no external anchor | yes (A3, A4 pass the 37 first-pass tests) | `test_m2_the_ledger_and_the_manifest_are_anchored_in_git_history`, `test_m1_the_outcomes_rebuild_from_the_archive_alone` | both fail on a clone with A4 applied; A8b (a fake read) is caught by the rebuild |
| m3 D1 OK with 4 of 5 columns unmeasurable | yes | overall INSUFFICIENT_DATA unless every column is measurable; notice names the counts | D1 now INSUFFICIENT_DATA (1 of 5 OK); test and mutation X10 |
| m4 D6 counted retried attempts | yes (11 of 39 attempts, 0 of 25 final reads) | alarm on final reads of the planned decisions; attempts reported | D6 now 0 of 28 planned decisions without a usable read, attempts 11 of 39; SOURCE_FAILURE removed; test and mutation K7 |
| m5 champion with SUPPORT_BELOW_MINIMUM gave NO_CHANGE | yes | KEEP_ABSTAIN (rule 10 literal) | test m5, mutation X11 |
| m6 report table without "descriptive only" | yes | header and sentence (descriptive only, mint interval not governing, provisional) | `PROSPECTIVE_REPORT.md` section 3 |
| m7 contact scan missed repeat-mint export rows | yes (9aqmJj 23.9 h after its entry; 7M3gDR already listed) | `contact_scan.py` lists repeat-mint rows after an entry; CONTACT_EXCLUDED reads `evidence/prospective_contact_scan_cp19_1.json` | CONTACT_EXCLUDED rerun: n 17, 17, 11; BSS 0.241, 0.006, 0.398 (the skeptic's re-derivation), INSUFFICIENT_DAYS |

Also changed (PI-D-107 item 3): a read whose boundary stops before a matured target's window end is NOT_READ with READ_BOUNDARY_BEFORE_WINDOW_END instead of raising (needed by the re-read and later maturity runs); `run_prospective.py` writes a rerun's evaluation into its own folder without touching the cumulative ledger, and the report reads prediction-time files from `monitoring/`.

Commits: decisions and frozen sample `c7e3c25` (before any code change), repair code `7c177de`, repeated runs `bb2639a`, these records and the post-commit record after them.

Repeated runs at `7c177de` (`evidence/rerun_cp19_1_diff.json` against `b1a18f7`): predictions into the scratchpad byte-equal (the manifest differs only by the plan file of the committed folder, as in the first pass); `outcomes` on the committed ledger appended 0 entries (0 prospective rows in `training_labels`, 0 cross-target violations); every primary metric, count, verdict, scored row, calibration bin, breakdown, negative control and miss equal; changed: SENSITIVITY (CONTACT_EXCLUDED), DRIFT_REPORT (D1, D6, KEEP_ABSTAIN), PROSPECTIVE_REPORT, OUTCOME_LEDGER.md, PRIMARY_RESULTS and FEEDBACK_AUDIT (ledger head and size only), LEDGER_TOTALS and SEARCH_LEDGER (5 reproduction rows, 3,578 rows, N_search 130). The ledger's first 516 entries are byte-equal to `b1a18f7`'s; the drift rerun appended a second MONITOR entry and 3 RESPONSE entries.

Old-code check (`probes/cp19_1_old_code_check.py`, `evidence/cp19_1_old_code_check.json`): 8 of 16 repair tests fail on the `fce102e` module (CX-SK19 twice, the boundary gap, D6 final reads, D1 overall, m5, X4, X8); the other 8 pass there by design: they pin first-pass behaviour that was correct but unpinned (K3/K4, K8, K9, K11, K12, K13, K15, K17), shown by the mutations.

Counterexample CX-SK19 (skeptic): a revision of a final LABELED outcome appended through `append` citing the same read with the class flipped. Caught now by `monitoring._later_read` inside `check_payload` (used by `append`, `load` and `verify`); tests `test_cx_sk19_a_revision_citing_the_read_it_revises_or_no_read_is_refused` and `test_cx_sk19_a_pending_is_superseded_only_by_a_later_read_or_an_unread_gap_after_maturity`; mutations X1 to X7.

Disagreements: none with the findings. The skeptic offered two remedies for M1; the orchestrator chose (b) as PI-D-106. The A3 and A4 attacks are not refused by the module itself (a consistent rewrite is indistinguishable from a ledger without history); they are caught by history (git) and by the rebuild, which is what the tests now check.

Remaining open item: G25 (PI-D-106). Post-commit checks at the repair records commit `afb024d`: suite `2 failed, 2200 passed, 1 skipped in 503.48s` (the two known clock-dependent failures only; strays removed by hand), guard 0 violations over 2,850 files, seal check 0 problems, single-branch release audit exit 0 "Needs action: no." (`postcommit/rp2_*`).
