# Phase 12 evidence: out-of-sample evaluation discipline and the single opening of the retrospective holdout

Status: PASS after repair pass 2 (the orchestrator's independent skeptic: no material failure, 5 minor, counterexample CX-S12; each verified and repaired or recorded, see "Independent skeptic and repair pass 2"; PI-D-066). The sections before that one describe the first pass; no recorded number, verdict or output changed in the repair.

- Branch `feature/predictive-intelligence`; HEAD before `63076ad`; pre-registration `79d30f5` (2026-10-26T16:41:13Z); frozen code `3ea7030` (17:32:01Z); pre-opening outputs `d58de61` (17:33:19Z); opening outputs `de7ac77` (17:47:49Z); results, evidence and records in the commit that carries this file (hash in HANDOFF.md and `PHASE_12_RESULTS.json` after the post-commit records commit).
- Package: `sha256sum -c SHA256SUMS.txt` 41 OK, 0 failed.
- Spend: 0 Firecrawl credits, 0 vendor calls, 0 language-model calls, 0 socket events in the runner (audit hook), no `git fetch`.
- The sealed folder `phase_06/sealed/` was opened once, by `run_holdout.py open` at 17:33:27Z (`validation/OPENING_LOG.json`). Later reads of the label file: the REPRODUCTION run (17:47:58Z, `evidence/reproduction_open_log.json`) and the independent label check (17:59:27Z, `evidence/independent_label_check.json`), both reproductions of the committed program's scored rows with no new analysis. No EXPLORATORY look was made. The seal check after the opening still reports 0 problems (`evidence/postopen_seal.json`).

## Entry gate (G2)

| Command | Result | Exit |
|---|---|---|
| `python -m pytest tests -q -p no:cacheprovider` at `63076ad` (from 2026-10-26T16:30Z) | `1 failed, 1398 passed in 251.15s`; only the known `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (`evidence/entry/entry_suite_summary.txt`) | 1 |
| stray files after the suite | `data/reports/20261026_1630_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`, removed by hand | |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | `"problems": []`, label file `e695500d...`, seal digest `d5059bae...`, `SEAL.json` `f362ca12...` | 0 |
| `python -B audits/predictive-intelligence/phase_11/probes/verify_trace_analog.py audits/predictive-intelligence/phase_11` (Phase 11's key check) | 3 traces, 0 differences | 0 |
| Phase 11 `PHASE_11_RESULTS.json` | status PASS | |
| sha256 of `data/memelab.sqlite`, the p05 and p06 stores | `068287c0...`, `2525f0c4...`, `d2a5a7c6...`, equal to Phase 11's run log | |

## Commands of this phase

| Command | Result | Exit |
|---|---|---|
| looks before the plan (16:35Z to 16:40Z) | the 69 cards' states and hashes, the development metric files' verdict counts, the cumulative ledger, the 95 Solana holdout decisions' version 2 inputs, days and tech-1 states; no label read | 0 |
| commit `79d30f5` (checklist, registry 248 rows, protocol, PI-D-064) | before any Phase 12 code | |
| debug run 1: `run_holdout.py plan` and `predict` at uncommitted code (16:47:52Z to 16:48:01Z, scratch) | 69 cards, champions P07_B2 x3, N_search 118, 12,255 prediction rows over 95 decisions, 0 trap failures; no label | 0 |
| debug run 2: `run_holdout.py open --synthetic-dry-run` (17:00:19Z to 17:12:06Z, scratch) | random SYNTHETIC labels in the sealed file's shape, no seal, no holdout label; every evaluation ran; the scikit-learn oracle on its output 616 values within 1.1e-16 | 0 |
| `python -m pytest tests/test_predictive_evaluation.py -q` (first) | 1 failed (import allowlist missed `datetime`), fixed; then `41 passed` | 0 |
| `python -B probes/mutation_evaluation.py` (first) | 44 mutations, 42 caught; survivors "censored scored", "pending scored" (fixtures gave censored and pending rows no label value); 1 test added | 1 |
| debug run 3: plan and predict again after the ledger edits, then a SYNTHETIC open at 50 replicates through a scratch wrapper (two attempts cut by a 10 min timeout, one complete about 17:31Z) | predictions byte-equal to debug run 1; synthetic labels only | 0 |
| commit `3ea7030` (evaluation.py, 42 tests, runner, mutation probe, oracle) | before the recorded runs | |
| `python -B probes/mutation_evaluation.py evidence/mutation_evaluation.json` (at `3ea7030`) | 44 of 44 caught | 0 |
| `python -B probes/run_holdout.py plan validation` (17:32:47Z) | `{"cards": 69, "champions": {"T1_24h": "P07_B2", "T1b_6h": "P07_B2", "T2_24h": "P07_B2"}, "n_search": 118}` | 0 |
| `python -B probes/run_holdout.py predict validation` (head `3ea7030`, wall 7.6 s) | `{"prediction_rows": 12255, "decisions": 95, "failures": [], "stores_unchanged": true}` | 0 |
| the same two commands into a scratch folder | 7 of 7 files byte-equal (`evidence/determinism_predict.json`) | 0 |
| `python -m memelab social guard` | 0 violations | 0 |
| commit `d58de61` (pre-opening outputs and `PREOPEN_MANIFEST.json`) | the predictions fixed before the opening | |
| `python -B probes/run_holdout.py open validation` (17:33:26Z to 17:44:05Z, head `d58de61`, clean tree, wall 638 s, CPU 619 s) | seal check exit 0, pins equal, opening log written before decompression; `{"T1_24h": {"n": 66, "positives": 15, "bss": -0.0242, "verdict": "NOT_DISTINGUISHABLE_FROM_BASE_RATE"}, "T1b_6h": {"n": 68, "positives": 12, "bss": -0.0833, "verdict": "NOT_DISTINGUISHABLE_FROM_BASE_RATE"}, "T2_24h": {"n": 59, "positives": 7, "bss": 0.2925, "verdict": "INSUFFICIENT_EVENTS"}}`, failures [] | 0 |
| commit `de7ac77` (the opening's outputs as written) | | |
| `python -B probes/run_holdout.py open SCRATCH --reproduction` (17:47:58Z to 17:58:41Z) | 10 of 10 output files byte-equal to the recorded run | 0 |
| `p04_bundle/bin/python -B probes/sklearn_crosscheck_holdout.py validation evidence/sklearn_crosscheck.json` | 572 values (Brier, log loss, AUC, AP of every primary and secondary row with a number), max difference 1.1e-16, scikit-learn 1.9.1 | 0 |
| `python -B probes/independent_label_check.py evidence/independent_label_check.json` (no `memelab` import) | sealed bytes equal the pin; scorable rows 66, 68, 59 with 15, 12, 7 positive; 0 label mismatches with `HOLDOUT_SCORED.csv`; 0 sealed scorable rows unscored | 0 |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` after the opening | `"problems": []` | 0 |
| `python -m pytest tests/test_predictive_evaluation.py tests/test_predictive_phase12_outputs.py -q` | `47 passed` | 0 |

Post-commit suite, guard, seal check and single-branch release audit: see "Post-commit results" below.

## Checklist results

| Id | Result |
|---|---|
| G1 | 41 OK |
| G2 | as above |
| G3 | `79d30f5` precedes the first code commit `3ea7030`; the three debug runs (no holdout label) are ledger rows |
| G4 | the recorded `plan` and `predict` ran at `3ea7030`, the opening at `d58de61` (code unchanged since `3ea7030`) |
| G5 | 69 cards loaded through their family's `loads`; cutoff 2026-10-17T00:00Z; every `max_train_decision_time` before and `max_train_label_matures_at` at or before it (`CANDIDATES.json`) |
| G6 | champions by `evaluation.champion` on the committed development metric files: P07_B2 for T1, T1b, T2 (0 development rows with SKILL_INDICATED_DEVELOPMENT_ONLY) |
| G7 | 2,896 rows, 87, 31, 306, 15, N_search 118 (`LEDGER_TOTALS.json`) |
| G8 | 12,255 prediction rows committed with their sha256 before the opening; the opener and `tests/test_predictive_phase12_outputs.py` check the manifest; two runs identical |
| G9 | seal check exit 0, `"problems": []`, the three hashes equal to DECISIONS and `evaluation.SEAL_PINS`; label bytes hashed on read |
| G10 | one FIRST_OPENING entry, written before decompression (test `test_the_log_exists_even_when_the_label_bytes_cannot_be_decompressed`); a second FIRST_OPENING raises |
| G11 | holdout rows filtered by `holdout_rows`; per target 1 labelled contacted decision excluded; 5 censored, 7 T2 PENDING counted and not scored |
| G12 | `PRIMARY_RESULTS.json`, `HOLDOUT_METRICS.csv`, `CALIBRATION_BINS.csv`; see `FINAL_HOLDOUT_RESULTS.md` |
| G13 | 129 secondary rows with Holm, max-T and full-search Bonferroni columns; 0 survive all three |
| G14 | NC1 20 seeds per target; NC2 1,425 of 1,425 and 15 of 15 refused; NC3 22 of 22 refused |
| G15 | `REPLAY_AUDIT.json` 0 violations; P13 traps 69 of 69 twice, TRAINING_LABEL_AFTER_CUTOFF 69 of 69 |
| G16 | `SENSITIVITY.csv` (7 views), `SHIFT_BREAKDOWN.csv` (8 breakdowns and prior shift), T2 rows carry the PI-D-045 note |
| G17 | `FINAL_HOLDOUT_RESULTS.md` states empirical validity and engineering validation separately; nothing promoted |
| G18 | 572 values within 1.1e-16 |
| G19 | predict twin identical; REPRODUCTION identical (10 files); 0 network calls; stores unchanged; seal unchanged after the opening |
| G20 | 42 + 5 tests; mutation probe 44 of 44 at `3ea7030` |
| G21 | `FULL_EXPERIMENT_LEDGER.csv` 3,145 rows (Phase 12: 249 = 186 holdout evaluation, trap and check rows, 60 NC1 controls, 3 debug runs); `FULL_LEDGER_TOTALS.json` |
| G22 | flag OFF; tests show no existing module imports `evaluation` and only it names the holdout label file; registry fingerprint `4b4aabce...` and ACCEPTANCE unchanged (contract tests pass) |
| G23 | holds (see "Post-commit results") |

## Results (summary; detail in `validation/FINAL_HOLDOUT_RESULTS.md`)

- Primary (B2 against B0, Holm across three): T1 66 events (15 positive), BSS -0.024 (governing mint interval -0.156 to 0.134), Holm p 1.0, NOT_DISTINGUISHABLE_FROM_BASE_RATE; T1b 68 (12), BSS -0.083 (day interval -0.174 to -0.020, governing mint interval -0.168 to 0.002), Holm p 1.0, NOT_DISTINGUISHABLE_FROM_BASE_RATE, calibration in the large failed; T2 59 (7), BSS +0.292, INSUFFICIENT_EVENTS (fewer than 10 positive), with the PI-D-045 item 6 note.
- No secondary card survives the selection correction. The champion fails the SHADOW criteria on every target. Every complex model stays MODEL_NOT_PROMOTED; the engine prefers base rate or abstention. Matches the expected outcome stated in Phase 01.

## Iteration log

- Pass 1 (this): plan, code, pre-opening predictions, single opening, reproduction, oracle, independent label check, records. Three debug runs before the freeze, none with a holdout label (ledger rows). One test fix and one test added before the code commit.

## Own adversarial pass (not independent)

1. Champion picked after the fact (CX-12, named before building): blocked by `CANDIDATES.json` and `HOLDOUT_PREDICTIONS.csv` in `d58de61` before the opening, the manifest check and the single-opening refusal; `test_cx12_*` shows a no-skill best of 63 with an uncorrected p that looks good and a max-T p that does not.
2. The secondary `verdict` column applies Holm only and shows SKILL_INDICATED_RETROSPECTIVE_HOLDOUT for one row (T1, B1 against B0); a reader could take it for a claim. The frozen claim rule is `skill_after_selection_correction` (0 everywhere). Recorded in the results; outputs not edited.
3. The pre-registered max-T is centred, not studentized, so high-variance candidates dominate the maximum and a small, low-variance improvement (B1, BSS +0.016) cannot pass it. This makes the correction conservative, never permissive. Recorded as a limitation; a studentized version would be change control before any prospective read.
4. Technical cards could not be scored (no holdout candles under the Phase 05 seal). Their absence is a coverage result, not a hidden failure.
5. `CALIBRATION_BINS.csv` repeats the champion's bins (primary and secondary rows). Identical copies; no number affected.
6. Regime and crash-day shift are untestable here (one regime label, no crash day).
7. T1b is borderline: the frozen "wider interval governs" rule keeps it at NOT_DISTINGUISHABLE while two sensitivities say WORSE. Reported as is; no rule changed after the result.

## Counterexample CX-12

Stated before building in `ACCEPTANCE_CHECKLIST.md`: scoring every card on the holdout and calling the best one the champion. Caught by the committed pre-opening champion and predictions, the opener's manifest check and its refusal of a second FIRST_OPENING, and the selection correction on every secondary row (test `test_cx12_the_best_of_63_no_skill_candidates_looks_good_uncorrected_but_not_after_max_t`). On the real holdout the best secondary card against B0 by BSS (T2, B2 and A1, +0.292) is INSUFFICIENT_EVENTS and its max-T p is 0.16.

## Artifacts

sha256 of every Phase 12 file is in `PHASE_12_RESULTS.json` (`artifacts`).

## Post-commit results (at `c549748`, the results and records commit)

| Command | Result | Exit |
|---|---|---|
| `python -m pytest tests -q -p no:cacheprovider` (from 18:04:12Z) | `1 failed, 1445 passed in 199.06s`; only the known `test_dedup_corroboration_resurface_denial`; stray `data/reports/20261026_1804_BRETT_0x532f.md` and `data/memelab.sqlite-shm`, `-wal` removed by hand; `data/memelab.sqlite` sha256 `068287c0...` unchanged (`postcommit/pytest_summary.txt`) | 1 |
| `python -m memelab social guard` | 0 violations (`postcommit/social_guard.out.txt`) | 0 |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | `"problems": []` (`postcommit/seal_check.json`) | 0 |
| `python tools/release_audit.py --history` on a single-branch clone at `c549748` | "Needs action: no." (`postcommit/release_audit_history.summary.txt`) | 0 |
| `git status --short` | clean | 0 |

## Independent skeptic and repair pass 2 (PI-D-066)

Review: `skeptic/PHASE_12_SKEPTIC.md` with the reviewer's scripts `skeptic/p12_*.py` and outputs, at `ae911ac`. Verdict: no material failure; every primary number, the NC1 shares, the max-T and Holm values, the manifest and opening-log hashes, the frozen cards and both reproductions confirmed independently. Each finding verified against the code first:

| Finding | Verified | Disposition |
|---|---|---|
| CX-S12 and m5: `p_max_t` is None for every row against B2 and the claim rule needs it, so no card could be shown to beat B2 after correction | yes (`run_holdout.py` secondary loop; 63 rows against B2) | `evaluation.selection_status` (CORRECTION_NOT_COMPUTED is never a pass or a fail); max-T against B2 computed POST_OPENING: 51 cards, smallest p 0.638; all 129 rows now fully corrected: 13 FAIL, 116 no uncorrected skill, 0 survive, 0 not computed (`validation/POST_OPENING_CORRECTIONS.csv`) |
| m1: skill-sounding Holm-only verdict in `HOLDOUT_METRICS.csv` and `FULL_EXPERIMENT_LEDGER.csv` (T1 B1 against B0) | yes | recorded files kept byte-equal (hashes in the opening log); `validation/FULL_EXPERIMENT_LEDGER_CORRECTED.csv` adds `selection_status` and `claim` (that row: FAILS, NOT_A_CLAIM_VERDICT_IS_HOLM_ONLY) and is the cumulative ledger from here on; results, PI-D-065 and PI-D-066, HANDOFF reworded |
| m2: five mutations of `max_t` and `champion` survived the tests | yes (rerun of the reviewer's probe) | tests: a plain restatement of the max-T on two targets with ties and undefined replicates, ties, the +1, undefined replicates, the cross-target family, champion with NOT_DISTINGUISHABLE and WORSE rows; mutation probe 63 of 63 (44 first pass + 12 skeptic + 7 new) |
| m3: N_search leaves out 9 non-probability rule configurations | yes (`evaluation.rule_configurations` = 9) | POST_OPENING sensitivity N 127; B1's Bonferroni 0.032; same outcome (fails max-T) |
| m4: the seal is procedural | yes | stated plainly as honour-based in the results, PI-D-066 and HANDOFF; Phase 19 must keep prospective labels out of any file the runner can read until its plan and predictions are committed |

Rule for anything computed on holdout outcomes after the opening: labelled POST_OPENING, logged in `validation/POST_OPENING_LOG.json`, computed from committed outputs only (the sealed folder is not read), and combined with the recorded state by `evaluation.conservative_status`, which can only make a result more conservative and never creates a claim, a candidate or a champion.

| Command (repair pass 2) | Result | Exit |
|---|---|---|
| reviewer's 12 mutations against the first-pass tests (from the review, `skeptic/p12_skeptic_mut.json`) | 7 caught, 5 survived (S1 to S4, S8); now rows of the phase probe, all caught | |
| new tests against the first-pass `evaluation.py` (scratch copy) | 3 failed (CX-S12 state, conservative combination, rule count), 47 passed | 1 |
| commit `e7f0b6c` (repair code, review copied) | before any post-opening computation | |
| `python -m pytest tests/test_predictive_evaluation.py tests/test_predictive_phase12_outputs.py -q` | `57 passed` | 0 |
| `python -B probes/mutation_evaluation.py evidence/mutation_evaluation_repair2.json` | 63 of 63 caught | 0 |
| `python -B probes/cx_s12_check.py evidence/cx_s12_check.json` (SYNTHETIC, 20,000 replicates) | first-pass rule reports X against B2 as not surviving on all three targets; repaired status CORRECTION_NOT_COMPUTED as recorded, SURVIVES with a max-T against B2 | 0 |
| `run_holdout.py plan` and `predict` at `e7f0b6c` into scratch | 7 of 7 byte-equal (`evidence/frozen_code_rerun_repair2.json`) | 0 |
| `run_holdout.py open SCRATCH --reproduction` at `e7f0b6c` (19:47:09Z to 19:57:46Z; a logged holdout read, `evidence/reproduction_open_log_repair2.json`) | 10 of 10 byte-equal | 0 |
| `python -B probes/post_opening_corrections.py validation` (19:49:31Z, POST_OPENING) and a twin into scratch | N 127; max-T against B2 51 cards, 0 below 0.05, smallest 0.638; status 13 FAILS, 116 NO_UNCORRECTED_SKILL; recorded outputs unchanged; twin identical | 0 |

Holdout reads after the first opening, all logged: the first-pass REPRODUCTION and independent label check, the reviewer's REPRODUCTION and recomputation (named in the review) plus one EXPLORATORY T1-only max-T and a T2 state count by the reviewer, the repair REPRODUCTION, and the POST_OPENING corrections (from `HOLDOUT_SCORED.csv`). None changed a verdict, a champion or a promotion.

## Counterexample CX-S12 and what catches it now

The reviewer's: "0 of 129 secondary comparisons survive the selection correction" read as "no frozen card beats B2 after correction", although the first-pass rule could not report any comparison against B2 as surviving. Now caught by `tests/test_predictive_evaluation.py::test_cx_s12_a_correction_that_was_not_computed_is_never_read_as_did_not_survive` (fails on the first-pass module), by `probes/cx_s12_check.py` on the reviewer's synthetic data, and on the real holdout by the POST_OPENING max-T against B2 (all 129 rows corrected, 0 not computed; `tests/test_predictive_phase12_outputs.py` asserts no row is CORRECTION_NOT_COMPUTED or a survivor).
