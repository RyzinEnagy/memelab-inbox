# Baseline specification and results (Phase 07)

Status of every number here: PROVISIONAL_PENDING_REVISION_REREAD (PI-D-046). Phase 06's frozen 48 h revision re-read has not run yet; if it changes any development label, `probes/run_baselines.py` is rerun at the Phase 07 repair code commit `f977aab75e13f7d72c6c254491c697b3ba695173` (first-pass code `6672447`) and its outputs replace these files (superseded, never edited). Nothing here claims the frozen revision check.

Research only. No number here is a published probability: publication needs a passed calibration check on the sealed holdout (Phase 12 and 13) and a selected champion (Phase 16). These are price-path targets with no execution data (PRICE_PATH_NOT_PROCEEDS, NO_HISTORICAL_EXECUTABLE_DEPTH, BACKTEST_NOT_AVAILABLE): nothing here says anything about proceeds, fills or trading.

Pre-registration: `../ACCEPTANCE_CHECKLIST.md` and `../experiments/EXPERIMENT_REGISTRY.csv`, committed in `74183c9` (2026-10-25T19:51:19Z) before any baseline was fitted; the code was committed in `6672447` (20:05:44Z) before the first recorded run. Repair pass 2 (PI-D-049, after the independent skeptic) changed the verdict function and NC1 rules, not any number; the outputs here come from the rerun at `f977aab` (`../evidence/run_log.json`).

## Answer in one paragraph

On the development labels and the frozen walk-forward, no baseline is distinguishable from the training base rate for any primary target. T1 (24 h) and T2 (24 h) do not reach the frozen minimum of 5 out-of-sample decision days (3 and 1), so their verdict is INSUFFICIENT_DAYS: no claim either way. T1b (6 h) reaches exactly 5 days but has only 44 events with 3 positive out of sample, below the frozen out-of-sample minimums (50 events, 10 per class), so its verdict is INSUFFICIENT_EVENTS (PI-D-049; in the first pass it read NOT_DISTINGUISHABLE_FROM_BASE_RATE, and every governing interval does contain 0, with Holm-adjusted p 0.28 or more). This is the outcome stated in advance in Phase 01 (PI-D-016). The engine stays at ABSTAIN with INSUFFICIENT_HISTORY and MODEL_NOT_SELECTED; the train-only cards below are frozen for Phase 12, which evaluates them once on the sealed holdout.

## Inputs

| Input | What was used |
|---|---|
| Labels | `labels.training_labels(dev_con, as_of, target, mode="provider")` on `/home/claude/pi_research/p06/dev_store.sqlite` (opened read-only; sha256 unchanged by the run). Label version `labels-1`, registry `4b4aabce...`. Provider mode because every label was read on 2026-10-24: a RETROSPECTIVE reconstruction, not what the lab held at the cutoffs (DATA_TIME_CONTRACT) |
| Label sets at the development end (as of 2026-10-17T00:00Z) | T1 136 events, 34 positive, 9 days, 99 mints (label-set sha `9fae5b7e...`); T1b 224, 26, 10 days, 104 mints (`c0396967...`); T2 131, 28, 8 days, 96 mints (`4bf69e80...`) |
| Features | stored provider-mode snapshots of `/home/claude/pi_research/p05/predictive_store.sqlite` through `features.training_view` (feature version 2, definitions `90781ad7...`); only export-row features are used (FACT, available at the export commit that is the decision time); no vendor candle feature enters any baseline |
| Decision facts | thesis status and token `narrative_id` from the decision row of the same export (`predictive_decisions`) |
| Join | `baselines.join`: by decision_key with chain, mint (byte for byte) and decision time equal, else IdentityJoinError |
| Not used | the sealed holdout (never opened), Phase 04 bake-off labels (refused by the gate), `feature/backtesting` (PI-D-047), any network |

## Baselines

| Id | Definition | Fixed settings |
|---|---|---|
| B0 | training prevalence | none |
| B1 | prevalence by thesis status group, shrunk toward B0: (k + 20 B0) / (n + 20) | REJECTED; RISK_OR_UNRESOLVED (DISTRIBUTION RISK, OVEREXTENDED, THESIS DETERIORATING, THESIS INVALIDATED, RESEARCH REQUIRED); CONSTRUCTIVE (WATCH, SETUP DEVELOPING, NEAR ENTRY, ENTRY CONDITIONS MET); unseen group gives B0 |
| B2 | L2 logistic regression, numpy Newton, intercept unpenalised, C = 1 | required: log1p liquidity, log1p market cap, log1p 24 h volume, fatal flag present; optional: log1p token age in days (negative age is missing); training-only preprocessing: drop constant or all-missing columns, median fill, missing indicators, standardise |
| B3 | Platt sigmoid on the lab's 100-point score, fitted on training rows only | non-probability comparator; the score itself is unchanged; no score gives OOD |
| B3F | prevalence by fatal flag present or absent, shrunk toward B0 (m = 20) | added from the phase guidance ("score and fatal flags") |
| B4 | matched-training prevalence: training rows of other mints with liquidity and market cap each within a factor 3, shrunk toward B0 (m = 20) | the as-of form of ACCEPTANCE B4 |
| B4C | contemporaneous matched control: outcome rate of other-mint development decisions within 12 h, liquidity and market cap within a factor 3, at least 3 controls | DESCRIPTION ONLY: uses outcomes not known at the decision; never a forecaster, never a card, never in a verdict |
| NC1 | B2 refitted on training labels permuted inside each fold's training rows | seeds 0 to 19 |
| NC2 | future-feature trap: the label itself as a column, declared available at the first-touch candle's end plus the provider lag, or at maturity | must be refused |
| NC3 | same-ticker join trap: the 4 real same-symbol mint pairs among labelled development decisions | must be refused |

B1 to B4 are fitted only when their training rows reach 100 events and 20 per class (ACCEPTANCE); otherwise they abstain with INSUFFICIENT_HISTORY. Every fold of every target passed the gate, so no fold-level abstention occurred and out-of-sample coverage is 100% for every baseline (no row missed a required input).

## Splits: the frozen walk-forward

Expanding window by UTC decision day; first cutoff 2026-10-12T00:00Z, extended by whole days until 100 training events; training rows are `training_labels(dev, cutoff)` (decided before the cutoff, labels matured by it); validation rows are development labels decided on the day starting at the cutoff. The walk-forward index and the gate's rows are compared for every fold (WalkForwardMismatch otherwise; equal on every fold). The ported fold audit with the target's own maturity lag is valid for every fold (0 training rows decided or maturing after the cutoff, 0 overlap). `../evidence/folds.json` has the full audit.

| Target | Fold cutoffs (UTC) | Training events (positive) | Validation events (positive) | Validation rows whose mint is also in training |
|---|---|---|---|---|
| T1 24 h | 10-13, 10-14, 10-15 | 104 (25), 112 (26), 123 (30) | 11 (4), 8 (1), 5 (3) | 4, 5, 2 |
| T1b 6 h | 10-12, 10-13, 10-14, 10-15, 10-16 | 180 (23), 188 (24), 199 (25), 207 (25), 214 (26) | 8 (1), 11 (1), 8 (0), 7 (1), 10 (0) | 2, 4, 5, 4, 5 |
| T2 24 h | 10-14 | 104 (27) | 8 (1) | 4 |

Why so few validation days: a fold needs 100 matured training labels, and the 24 h and 48 h maturities (T2 has a 24 h halt confirmation) consume the end of the 10-day development window. Of the development events only 24 of 136 (T1), 44 of 224 (T1b) and 8 of 131 (T2) are ever out of sample. Split fingerprints: T1 `0ab64525e04b...`, T1b `aa16e7adeae7...`, T2 `82a1c33b12ce...` (`evidence/folds.json`).

## Results (pooled out-of-sample, ALL view)

Brier skill score (BSS) is against B0 on the same rows. Intervals are 95% bootstrap percentiles over whole decision days and over whole mints (2,000 replicates each, seed 20261025); the wider governs; a day interval needs at least 5 days. Full table with log loss, ESS, calibration and every view: `../experiments/BASELINE_METRICS.csv`.

| Target | Baseline | n (positive) | Days | Brier | B0 Brier | BSS | Day interval | Mint interval | Holm p | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 24 h | B1 | 24 (8) | 3 | 0.2301 | 0.2297 | -0.001 | undefined | -0.029 to 0.023 | undefined | INSUFFICIENT_DAYS |
| T1 24 h | B2 | 24 (8) | 3 | 0.2449 | 0.2297 | -0.066 | undefined | -0.246 to 0.106 | undefined | INSUFFICIENT_DAYS |
| T1 24 h | B3 | 24 (8) | 3 | 0.2208 | 0.2297 | 0.039 | undefined | -0.156 to 0.282 | undefined | INSUFFICIENT_DAYS |
| T1 24 h | B3F | 24 (8) | 3 | 0.2301 | 0.2297 | -0.002 | undefined | -0.012 to 0.009 | undefined | INSUFFICIENT_DAYS |
| T1 24 h | B4 | 24 (8) | 3 | 0.2138 | 0.2297 | 0.070 | undefined | -0.004 to 0.139 | undefined | INSUFFICIENT_DAYS |
| T1b 6 h | B1 | 44 (3) | 5 | 0.0664 | 0.0667 | 0.004 | -0.163 to 0.101 | -0.275 to 0.082 | 1.00 | INSUFFICIENT_EVENTS |
| T1b 6 h | B2 | 44 (3) | 5 | 0.0595 | 0.0667 | 0.108 | -0.022 to 0.206 | -0.127 to 0.219 | 0.28 | INSUFFICIENT_EVENTS |
| T1b 6 h | B3 | 44 (3) | 5 | 0.0732 | 0.0667 | -0.097 | -0.189 to -0.059 | -0.493 to 0.028 | 1.00 | INSUFFICIENT_EVENTS |
| T1b 6 h | B3F | 44 (3) | 5 | 0.0663 | 0.0667 | 0.006 | -0.096 to 0.083 | -0.129 to 0.073 | 1.00 | INSUFFICIENT_EVENTS |
| T1b 6 h | B4 | 44 (3) | 5 | 0.0655 | 0.0667 | 0.017 | -0.132 to 0.116 | -0.415 to 0.136 | 1.00 | INSUFFICIENT_EVENTS |
| T2 24 h | B1 | 8 (1) | 1 | 0.1232 | 0.1275 | 0.034 | undefined | -0.176 to 0.514 | undefined | INSUFFICIENT_DAYS |
| T2 24 h | B2 | 8 (1) | 1 | 0.1526 | 0.1275 | -0.197 | undefined | -2.049 to 0.914 | undefined | INSUFFICIENT_DAYS |
| T2 24 h | B3 | 8 (1) | 1 | 0.1277 | 0.1275 | -0.002 | undefined | -0.023 to 0.055 | undefined | INSUFFICIENT_DAYS |
| T2 24 h | B3F | 8 (1) | 1 | 0.1232 | 0.1275 | 0.034 | undefined | -0.257 to 0.667 | undefined | INSUFFICIENT_DAYS |
| T2 24 h | B4 | 8 (1) | 1 | 0.1331 | 0.1275 | -0.044 | undefined | -0.196 to 0.354 | undefined | INSUFFICIENT_DAYS |

Brier and log loss disagree in direction relative to B0 in 6 rows of the CSV (P23): T2 B2 in the ALL view (Brier worse, 0.1526 against 0.1275; log loss better, 0.419 against 0.432; 8 rows, 1 positive), T2 B2 new narratives, T2 B1 PIT only, and T1 B3 in the new-mints, new-creators and no-KEY_CONFLICT views. Both are always shown with counts; neither changes a verdict, which rests on Brier (the frozen primary score) and its interval. ROC AUC and average precision are not computed: no out-of-sample set has 10 events in each class (ACCEPTANCE). Calibration: T1 and T2 have fewer than 40 out-of-sample events, so only calibration in the large is checked (passes for every baseline: mean prediction inside the Wilson interval of the observed rate); T1b has 44 events, 2 quantile bins of 22, every bin inside its Wilson interval for every baseline (`../experiments/CALIBRATION_BINS.csv`). With 3 positives this check has almost no power and supports no calibration claim.

What to read into the T1b numbers: B2's point estimate (BSS 0.108) rests on 3 positive events over 5 days in one week (2026-W42); its day interval just includes 0 and its mint interval is wide; Holm across the three targets (undefined tests counted as p = 1) gives 0.28. B3's day interval lies below 0 while its mint interval does not; by the frozen rule the wider (mint) interval governs, so the interval rule alone would not say "worse than base rate" (and the count gate now stops any directional verdict on 3 positives), but nothing suggests the lab's score carries probability information for this target either.

Unit of dependence: every out-of-sample decision day is one export batch, one decision instant near 10:15Z (T1 3 instants, T1b 5, T2 1; all 8 T2 rows at 2026-10-14T10:17:43Z), so the day bootstrap resamples whole batches; two of T1b's five batches hold no positive.

Missing-feature coverage by cohort (development set and out-of-sample set): `../experiments/FEATURE_COVERAGE.csv`. Every model column is complete except token age on T1b (2 of 224 development rows, 2 of 44 out-of-sample rows; B2 fills it with the training median and a missing indicator).

Effective sample size: the design-effect ESS (n times the independent-rows variance over the block-bootstrap variance of the mean squared error) is reported beside every row. For T1b the day ESS exceeds n (about 98 against 44): with 5 day-groups the bootstrap variance is itself unstable and small, so an ESS above n means "no information beyond n", not more data. Mint ESS is close to n (each mint appears about once out of sample).

### Sensitivities (frozen views)

| View | T1 24 h B2 | T1b 6 h B2 | T2 24 h B2 |
|---|---|---|---|
| new mints only | 13 rows, BSS -0.089, INSUFFICIENT_DAYS | 24 rows (2 positive), BSS 0.099, INSUFFICIENT_EVENTS | 4 rows (0 positive), INSUFFICIENT_DAYS |
| new creators (unknown kept) | 14 rows, -0.095, INSUFFICIENT_DAYS | 25 rows (2), 0.097, INSUFFICIENT_EVENTS | 5 rows (0), INSUFFICIENT_DAYS |
| new narratives (unknown kept) | 19 rows, -0.057, INSUFFICIENT_DAYS | 34 rows (3), 0.125, INSUFFICIENT_EVENTS | 6 rows (0), INSUFFICIENT_DAYS |
| PIT_RECORDED route only | 19 rows, -0.069, INSUFFICIENT_DAYS | 33 rows (3), 0.087, INSUFFICIENT_EVENTS | 7 rows (1), INSUFFICIENT_DAYS |
| without KEY_CONFLICT (refitted) | 24 rows, -0.054, INSUFFICIENT_DAYS | 42 rows (3), 0.105, INSUFFICIENT_EVENTS | 8 rows (1), INSUFFICIENT_DAYS |

No view changes a verdict (T1 and T2 INSUFFICIENT_DAYS, T1b INSUFFICIENT_EVENTS in every view). Narrative ids are known for about 8% of labelled decisions, so the narrative view is close to the ALL view. Descriptive cohort tables by route, status group, liquidity bucket, launch-age bucket, week and day: `../experiments/OOS_COHORTS.csv` (no rate is claimed below 20 events; every T1b out-of-sample event is in one ISO week, so no regime statement is possible, P21).

### Negative controls and traps

| Control | Result | Pass |
|---|---|---|
| NC1, 20 seeds | mean BSS of the shuffled B2 against B0: T1 -0.033, T1b -0.033, T2 +0.022; share of shuffled fits beating the real B2: T1 0.70, T1b 0.00, T2 0.95 | uninformative at this size: T1 and T2 INSUFFICIENT_DAYS, T1b INSUFFICIENT_EVENTS under the same rules as a baseline verdict (PI-D-049 item 3). The shares say B2 is noise on T1 and T2; the first pass's "degrades" and "finding" readings are withdrawn |
| NC2, future feature | 136 of 136 T1 rows refused by the allowlist and 136 of 136 by `validate_rows`; 0 accepted; smallest trap delay 965 s after the decision | yes |
| NC3, same-ticker join | 4 real symbol groups, 8 ordered pairs, 8 refused, 0 accepted | yes |
| CX-07 (new counterexample) | joining by mint with the mint's newest stored snapshot would attach a later decision's features to 250 of 491 development label rows; all 250 refused by the identity join (decision time and key must match) | yes |

### Training prevalence at the development end (description, B0 at 2026-10-17T00:00Z)

| Target | n | Positive | Prevalence | Wilson 95% | Days | Mints |
|---|---|---|---|---|---|---|
| T1 24 h | 136 | 34 | 0.250 | 0.185 to 0.329 | 9 | 99 |
| T1b 6 h | 224 | 26 | 0.116 | 0.080 to 0.165 | 10 | 104 |
| T2 24 h | 131 | 28 | 0.214 | 0.152 to 0.292 | 8 | 96 |

By cohort (rate shown only where n is at least 20): `../experiments/TRAINING_PREVALENCE.csv`. These rates come from one market regime over 8 to 10 days; they are not base rates for any other period.

## Train-only artifacts (frozen for Phase 12)

Fitted on all development labels as of 2026-10-17T00:00:00Z (the holdout start) through the gate; every training gate passed. Each card is JSON read by numpy code (no pickle) and carries model id, model sha (sha256 of the canonical card without the sha), feature-set sha `90781ad7...`, feature version 2, label version `labels-1`, store schema `memelab.predictive.store/1`, label migration 2, label mode provider, registry `4b4aabce...`, training cutoff, counts, label-set sha, data-snapshot sha (decision keys with their snapshot sha256), evidence class DEVELOPMENT_RETROSPECTIVE_PROVIDER_MODE, status PROVISIONAL_PENDING_REVISION_REREAD, `revision_check_claimed: false`, `publishable: false`.

| Target | Card | Model sha (first 12) | File sha256 (first 12) |
|---|---|---|---|
| T1 24 h | B0, B1, B2, B3, B3F, B4 | see `../evidence/serialization_smoke.json` | `d89ab4a62fba`, `f84066700ca6`, `451a38b2dbc0`, `f9a18b453224`, `cd28cf657ebf`, `ea96d08e5a83` |
| T1b 6 h | B0, B1, B2, B3, B3F, B4 | see the same file | `232f38edfb5e`, `f8d1f830870c`, `412db87d6ffb`, `d4b3bbdfaec3`, `cb23b7dbe791`, `5ef325adcdcf` |
| T2 24 h | B0, B1, B2, B3, B3F, B4 | see the same file | `ba7f22958de4`, `3431edd2bb96`, `412d4bce917b`, `cc5d58a8b07c`, `e05576ae3a74`, `0010b258c19e` |

Fold cards (one set per fold, used for the out-of-sample numbers): `../artifacts/folds/<target>.json`. Serialization smoke for all 18 cards: written, read back, predictions on the training rows identical, model sha recomputed equal, a changed number refused (ModelHashMismatch), `runtime.verify_artifact` passes on the file hash. Contract smoke per target: an ABSTAIN document (INSUFFICIENT_HISTORY, MODEL_NOT_SELECTED) built from the B2 card passes `contract.validate`; a FORECAST document claiming a probability is refused (no holdout calibration reference; and, because it was built on a development decision, P13 "model trained after the decision").

Coefficients of the final B2 cards (standardised inputs; liquidity, market cap, volume, fatal flag, age; T1b also an age-missing indicator) are in the cards. They describe one 10-day window and are not interpretable as effects.

## Engine and oracle agreement

`memelab/predictive/stats.py` ports the Phase 04 prototype (scores, Wilson, Holm, preprocessing, logistic, Platt, Venn-Abers, day walk-forward, fold audit, Page-Hinkley) and adds ROC AUC, average precision, quantile calibration bins, ECE, Brier skill, group bootstrap and the design-effect ESS; `memelab/predictive/baselines.py` holds the baselines, the join, the walk-forward and the cards. Both use numpy and the standard library only (test). Against scikit-learn 1.9.1 in the research venv (`../probes/sklearn_crosscheck.py`): logistic coefficients within 3.0e-7 and probabilities within 1.1e-7 on every real fold design; Brier, log loss, ROC AUC and average precision within 5.6e-17 on the pooled numbers and within 1.1e-16 on 50 tie-heavy random cases (`../evidence/sklearn_crosscheck.json`).

## Conventions fixed here

0. Count gate (PI-D-049): no directional verdict (skill or worse) on fewer than the frozen out-of-sample minimums, 50 events and 10 per class (ACCEPTANCE `min_holdout_events`, `min_holdout_per_class`); the verdict is then INSUFFICIENT_EVENTS. NC1 follows the same 5-day and count rules.

1. Holm across the three primary targets counts an undefined test as p = 1 in a family of three (conservative); its own adjusted value is shown as undefined.
2. A verdict above NOT_DISTINGUISHABLE needs at least 5 out-of-sample decision days, the count gate of item 0, a defined governing interval with its lower bound above 0 and a Holm-adjusted p below 0.05; even then it is SKILL_INDICATED_DEVELOPMENT_ONLY, never a promotion (the holdout is untouched).
3. B4C is a description of market-wide co-movement and never a forecaster.
4. All verdicts are on development data, retrospective, provider mode, PROVISIONAL.

## What these numbers do not support

Any claim of skill or of no skill beyond "not distinguishable" on T1b and "not enough days" on T1 and T2; any probability shown to a user; any per-cohort or per-regime rate; any statement about another period; any trading, proceeds or fill statement; any use of these cards in replay before their training cutoff (DATA_TIME_CONTRACT: a model trained at 2026-10-17 is not an as-of model for earlier decisions).

## Rerun

```
python -B audits/predictive-intelligence/phase_07/probes/run_baselines.py audits/predictive-intelligence/phase_07 --npz <scratch>/arrays.npz
/home/claude/pi_research/venvs/p04_bundle/bin/python -B audits/predictive-intelligence/phase_07/probes/sklearn_crosscheck.py <scratch>/arrays.npz audits/predictive-intelligence/phase_07/evidence/sklearn_crosscheck.json
```

Two runs into two folders gave identical sha256 for all 33 generated files (`../evidence/determinism.json`).
