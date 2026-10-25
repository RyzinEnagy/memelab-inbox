# Phase 07 independent skeptic review

Reviewer: orchestrator's independent skeptic (PI-D-013), 2026-10-25 around 20:30Z. Clone `/home/claude/pi_orchestration/skeptic_07` at `0fa5cb8` on `feature/predictive-intelligence`. Store copies in `/home/claude/pi_orchestration/skeptic/p07work/` (originals unchanged: dev store `58213988...`, feature store `2525f0c4...`). Nothing written inside `/home/claude/memelab-inbox`; `phase_06/sealed/` not opened. No network call.

Scripts next to this file:

- `p07_independent.py`: recomputes folds, B0 and B2 out-of-sample Brier, Brier skill and the day and mint bootstrap from plain SQL on the two stores, with scikit-learn (research venv) for the logistic and preprocessing written from the pre-registered text. No memelab import.
- `p07_mutations.py`: 20 new mutations of `stats.py` and `baselines.py` (none in the agent's list), each run against the two Phase 07 test files. Result in `PHASE_07_mutations.json`.
- `p07_counterexample.py`: CX-S07 (below).

## Verdict

Numbers, folds, leakage controls, determinism, pre-registration order and the post-commit checks reproduce. One MATERIAL finding: the tests do not protect the frozen interval and verdict rules (a mutation that flips six real verdicts passes all 43 Phase 07 tests), so the "29 of 29 mutations caught" claim overstates what the suite guards for Phase 12. Eight MINOR findings.

## Checks

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Phase 07 tests | `python -m pytest tests/test_predictive_stats.py tests/test_predictive_baselines.py -q` | `43 passed` |
| 2 | Recorded run reproduced | `python -B .../probes/run_baselines.py p07work/out1 --dev-store <copy> --feature-store <copy> --npz p07work/p07.npz` | exit 0, 32 outputs, 0 socket events, stores unchanged; all 27 generated files byte identical to the committed ones and to `run_log.json` hashes (determinism holds across a third process) |
| 3 | Independent recomputation | `p04_bundle/bin/python -I p07_independent.py <dev> <fs> p07work/indep.json` | T1b: 5 folds (train 180/188/199/207/214, test 8/11/8/7/10), 44 OOS rows, 3 positive, 5 days, 37 mints; B0 Brier 0.066669, B2 0.059460, BSS 0.108133; day CI -0.02223 to 0.20597, mint CI -0.12716 to 0.21879, mint p 0.09195 (Holm x3 = 0.2759). T1: B2 BSS -0.06591, mint CI -0.2463 to 0.1065, day UNDEFINED. T2: B2 BSS -0.19693. All equal to `BASELINE_METRICS.csv` to 6 decimals |
| 4 | Fold construction | indep folds vs `evidence/folds.json` | identical (cutoff, n, k per fold) for all three targets; every training label matured by its cutoff (max training maturity before the first test decision in every fold); first cutoff 2026-10-12 skipped for T1 and T2 below 100 events as frozen; T2 single fold 2026-10-14 (48.3 h maturity lag) |
| 5 | Bootstrap seed sensitivity | indep, seeds 1 to 4 | T1b B2 mint CI lower bound -0.107 to -0.132, day lower -0.022 to -0.033: verdict NOT_DISTINGUISHABLE stable |
| 6 | Verdicts follow frozen rules | read `baselines.verdict`, metrics table | T1 and T2 fewer than 5 days: INSUFFICIENT_DAYS (rule PI-D-021 item 2). T1b: wider interval governs; B3's day interval (-0.189 to -0.059) is wholly below 0 but the wider mint interval (-0.493 to 0.028) governs, so NOT_DISTINGUISHABLE is the frozen outcome |
| 7 | CX-07 count | own SQL on copies | 491 development label rows; for 250 the mint's newest provider snapshot is another, later decision (T1 59, T1b 133, T2 58); `traps.json` says 250 refused |
| 8 | As-of features | SQL on feature values | every model column (liquidity, mcap, volume, fatal, age, score) is EXPORT_COMMIT basis, availability equal to the decision time, 0 non-null values with NULL availability |
| 9 | Train-only fitting | code read plus check 3 | B0 prevalence, Prep medians/indicators/standardisation, logistic and Platt use fold training rows only; my independent train-only refit gives the same predictions |
| 10 | No holdout or sealed rows | card fields | every card `training_cutoff` = 2026-10-17T00:00Z, `max_train_label_matures_at` at or before it; OOS decisions all before it |
| 11 | Pre-registration integrity | `git show --stat`, `git diff 74183c9 HEAD -- ACCEPTANCE_CHECKLIST.md EXPERIMENT_REGISTRY.csv`, reflog | checklist and registry unchanged since `74183c9` (19:51:19Z); no amend or reset in Phase 07; code hashes in `run_log.json` equal the files at `6672447`; `contract.py`, `labels.py`, `features.py` unchanged since Phase 06; registry fingerprint `4b4aabce...` |
| 12 | Debug runs | session scratchpad `xcheck.json` (written 19:58:42Z, between the two commits) | byte-for-byte equal to committed `sklearn_crosscheck.json`: B2 fold designs, coefficients and the B2, B3, B4 OOS arrays did not change between the last debug run and the recorded run |
| 13 | Agent mutation probe | `python -B .../probes/mutation_baselines.py` | 29 of 29 caught, clean exit 0 (reproduced) |
| 14 | New mutations | `python -B p07_mutations.py <clone> PHASE_07_mutations.json` | 9 of 20 caught; 11 survive (finding M1) |
| 15 | sklearn oracle | `sklearn_crosscheck.py p07work/p07.npz` | identical file to the committed evidence |
| 16 | Full suite | `python -m pytest tests -q -p no:cacheprovider` | exit 1, `1 failed, 1167 passed in 180.41s`, only `test_catalyst.py::test_dedup_corroboration_resurface_denial`; stray `data/reports/20261025_2023_BRETT_0x532f.md` removed |
| 17 | Guard | `python -m memelab social guard` | exit 0, `"violations": []` |
| 18 | Seal | `python -B .../phase_06/probes/check_seal.py` | exit 0, `"problems": []` |
| 19 | Release audit, full clone | `python tools/release_audit.py --history` | exit 1, one history hit, blob `acbc9c9016` (finding m6) |

## Findings

### M1 (MATERIAL): frozen interval and verdict rules are not protected by any test

New mutations that survive the 43 Phase 07 tests: the narrower interval governs instead of the wider; the mint bootstrap groups by day (copy error); a 90% instead of 95% interval; WORSE_THAN_BASE_RATE when the upper bound is below 0.05 instead of 0; the one-sided p counting only BSS < 0; unseen status predicted at 0.5 instead of B0; log loss clip ignored; ddof 1 standardisation; B4C window x10. The first was run end to end: in a scratch copy with `max(` changed to `min(` in `evaluate`, the tests pass (`43 passed`) and six real verdicts change, T1b B3 in every view from NOT_DISTINGUISHABLE_FROM_BASE_RATE to WORSE_THAN_BASE_RATE. Determinism checks compare run to run, not to an expected value, so nothing would notice. The recorded numbers are right (check 3), but Phase 12 reuses `evaluate` and `verdict`, and the evidence's 29 of 29 reads as if the frozen rules were guarded. Fix: unit tests that pin "wider governs" (an input where the two intervals disagree in sign), the 95% level, day versus mint grouping, the WORSE threshold at 0, and the p convention; add them to the mutation probe. (Two other survivors, chain check and fit_all maturity, are redundant guards: the decision key and `validate_rows` catch the same cases. Not gaps.)

### m1: no event or class minimum behind a skill verdict (counterexample CX-S07, below)

The frozen ACCEPTANCE has only the 5-day rule for development claims; `verdict` needs no event count. SKILL_INDICATED_DEVELOPMENT_ONLY is reachable on 6 rows with 1 positive. Real T1b already sits at 3 positives over exactly 5 days. Within the frozen plan, so MINOR, but it should get a change control before Phase 12 (for example the AUC minimum of 10 per class, or INSUFFICIENT_EVENTS).

### m2: NC1 verdicts ignore the 5-day rule and are not meaningful at this size

NC1 is labelled NC1_DEGRADES_OR_EQUAL on T1 (3 days) and NC1_FINDING on T2 (1 day, 8 rows, 1 positive), both claims on fewer than 5 days. Across seeds the T2 NC1 skill has sd 0.114 (min -0.279, max 0.180); the NO_KEY_CONFLICT view on the same 8 test rows flips to DEGRADES because the training set differs. Against the real B2: 14 of 20 shuffles beat B2 on T1, 19 of 20 on T2, 0 of 20 on T1b. So NC1 shows B2 is noise on T1 and T2 and cannot fail meaningfully there. Under the frozen criterion ("must score no better than B0") T2 ALL formally fails. Suggest NC1 verdict INSUFFICIENT_DAYS below 5 days and reporting NC1 versus B2. "NC1 degrades on T1" in PI-D-048 is true only against B0.

### m3: unknown feature availability becomes "available at the decision" on the read path

`features.training_view` (Phase 05 code that Phase 07 depends on) replaces a NULL `feature_available_at` with the decision time before `validate_rows` sees it, so the rule "an unknown availability time is not available" is bypassed for any value stored with NULL availability. Shown on a scratch copy with the append-only triggers dropped: a changed liquidity value with NULL availability passes `training_view` and `check_asof`. Today 0 non-null model values have NULL availability and the table is append-only, so nothing is affected. Fix in Phase 05 code: refuse a non-null value with NULL availability.

### m4: search ledger incomplete

`SEARCH_LEDGER.csv` (512 rows) lacks the two Phase 07 debug runs on real data (disclosed in the evidence, not in the ledger) and Phase 04's first real-data run before the age fix (`phase_04/adoption/evidence/first_real_run_failures/`). Phase 04's 13 challenge configurations are synthetic and rightly absent. No selection rests on any of them; add the rows for P22 bookkeeping.

### m5: Holm change after the debug runs (disclosed)

The convention moved from "drop undefined tests" to "undefined counts as p = 1 in the family of three" after outcomes were seen. It is more conservative and matches the frozen family of three targets; with T1b B2's governing lower bound at -0.127 no verdict could have changed either way. Check 12 shows the B2, B3 and B4 predictions were already final at the last debug run. Not a defect; noted for completeness.

### m6: the release-audit hit is a known false positive, already explained on its own branch

Blob `acbc9c90161a2a5ea76e7cfeb343b3808a57e601`, path `audits/backtesting/research/smoke/etcherfx__sol-trade/output.txt`, line 42, rule `key_material_field`, added in `2922adb` (2026-10-23, backtesting phase 03), still in the tip tree of the backtesting branch (`12f278b`). The matched string is 20 characters of capitals and underscores (shape `AAAAAAAA_AAAAAAA_AAA`, not base58, cannot be a Solana key): the environment variable name in a static-scan line quoting `sol_trade/config.py:312`. The backtesting branch's own `tools/release_audit.py` line 64 lists exactly this path and rule as reviewed ("quoting an environment variable name (SOLTRADE_PRIVATE_KEY), not a key value (D-BT-016)"). Not a real problem on that branch; 0 objects reachable from `feature/predictive-intelligence`. The evidence's "that branch's owner should review it" should say it is already reviewed there (D-BT-016) and that only this branch's audit lacks the entry. Side note: the inbox also holds a local branch `work/backtesting-collector` at `12f278b`.

### m7: out-of-sample "days" are single export batches

Every OOS day is one decision instant (one export near 10:15Z): T1 3 instants, T1b 5, T2 1 (all 8 T2 rows at 2026-10-14T10:17:43Z). The day bootstrap on T1b resamples 5 batches, two of them with no positive. The spec should say so; it is the real unit of dependence here.

### m8: missing-feature coverage not tabulated

Phase prompt step 2 asks for missing feature coverage per cohort. No table carries it. Measured here: 0% missing for every model column on T1 and T2, token age 0.9% (2 rows) on T1b.

## Counterexample CX-S07 (new)

A baseline evaluated on 6 out-of-sample rows with one positive, spread over 5 decision days (B0 0.20 everywhere; the model 0.45 on the positive, 0.05 to 0.07 on the negatives) gets BSS 0.621, day CI 0.565 to 0.932, mint CI 0.550 to 0.933, one-sided p 0.0005, Holm (with the other two targets undefined, p = 1) 0.0015, and the frozen function returns SKILL_INDICATED_DEVELOPMENT_ONLY. Every bootstrap replicate without the positive still favours the model because it is lower on the negatives, so the interval cannot see that the claim rests on one event. Command: `python -B /home/claude/pi_orchestration/skeptic/p07_counterexample.py /home/claude/pi_orchestration/skeptic_07` (exit 0 means the verdict was awarded). No test, probe or contract check catches it: `test_verdicts_need_five_days_an_interval_above_zero_and_holm` only varies days, interval and Holm.
