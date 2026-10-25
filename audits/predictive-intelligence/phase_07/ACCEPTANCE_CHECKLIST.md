# Phase 07 acceptance checklist and pre-registration (written before any fit)

Written 2026-10-25 around 19:55Z by the Phase 07 agent, after the entry gate (`1 failed, 1124 passed in 220.79s` at `b0275c6`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; the stray `data/reports/20261025_1942_BRETT_0x532f.md` removed by hand; `check_seal.py` exit 0 with `"problems": []`), after reading the package (checksums OK), the phase prompt, SCIENTIFIC_VALIDATION, FORECAST_OUTPUT_SCHEMA, NO_GO_DECISION_TREE, ADVERSARIAL_SCENARIOS, DATA_TIME_CONTRACT, every PI-D entry, Phase 01 ACCEPTANCE_METRICS and TARGET_REGISTRY, Phase 04 BAKEOFF and INSTALL_DECISION, the Phase 05 contract and the Phase 06 labels and gate. This file and the experiment registry are committed before any baseline is fitted or any out-of-sample number is computed (PI-D-045 item 5). What was looked at before writing it: thesis status vocabulary, the presence of creator and narrative ids, decision-key overlap between the Phase 05 and Phase 06 stores, and same-symbol mint pairs among labelled development decisions; no label value, prevalence, fold or metric. The development class counts printed by Phase 06 (T1 136 with 34 positive, T1b 224 with 26, T2 131 with 28) were already public.

## Entry-gate exception (recorded as PI-D-046)

Phase 06 is NEEDS_REVIEW with one open item, the frozen 48 h revision re-read (not before 2026-10-26T13:49Z). Elving decided on 2026-10-25 at 15:40 New York time: "continue with the subsequent phases, beginning with phase 07". So: Phase 07 proceeds on his explicit instruction; every Phase 07 number is PROVISIONAL until the re-read is folded in; if the re-read changes any development label, Phase 07 reruns from the frozen code and the provisional numbers are superseded, not edited; no Phase 07 output claims the frozen revision check.

## Backtesting branch check (PI-D-043, recorded as PI-D-047)

Read `origin/feature/backtesting` at `12f278b` only as far as needed (memelab/backtest/strategies/baselines.py, outcomes.py, sources/gecko.py, validation.py, strategies/labstatus.py; a search for Brier, log loss, prevalence, logistic and calibration in memelab/backtest and docs/backtesting). Its baselines are trading strategies (NO_TRADE, ENTER_AT_DISCOVERY, RANDOM_ENTRY) scored on simulated fills; its outcomes ledger (outcomes-v1) measures 1 h, 6 h, 24 h and 72 h windows on hourly bars from its own discovery universe; its "calibration" is segment outcome shares with Wilson intervals. It has no probability baseline, no Brier or log loss, no logistic model and no frozen-target label. Phase 07 builds no loader, no vendor call, no outcome store and no report renderer: it reads the Phase 06 labels through `labels.training_labels` and the Phase 05 stored feature snapshots only. Nothing is imported from that branch. No duplication.

## Inputs (fixed)

| Input | Rule |
|---|---|
| Labels | `labels.training_labels(dev_con, as_of, target, mode="provider")` on `/home/claude/pi_research/p06/dev_store.sqlite` only (rebuilt from `phase_06/raw/` and git if missing); never the sealed folder; provider mode because every label was read on 2026-10-24, so capture mode at any development cutoff is empty (stated as a RETROSPECTIVE reconstruction, DATA_TIME_CONTRACT) |
| Features | stored provider-mode snapshots of the Phase 05 store `/home/claude/pi_research/p05/predictive_store.sqlite` through `features.training_view` (feature version 2, definitions hash `90781ad7...`), each validated by `features.validate_rows` |
| Join | by `decision_key`; chain, mint (byte for byte) and decision time of the label row and the snapshot must be equal, else refused (P01) |
| Registry | fingerprint `4b4aabce77a5a6f9214c4cfdddf5223f410ed6126410cf4b213b3c80b035f896`, ACCEPTANCE unchanged; nothing in `contract.py` is edited |

## Baselines pre-registered (one configuration each, no tuning)

All fitted on each fold's training rows only; every fitted object is a JSON card read by numpy code (no pickle).

| Id | Definition | Fixed settings |
|---|---|---|
| B0 | training prevalence of the target | none |
| B1 | prevalence by thesis status group, shrunk toward B0: (k_g + m B0) / (n_g + m) | groups REJECTED; RISK_OR_UNRESOLVED (DISTRIBUTION RISK, OVEREXTENDED, THESIS DETERIORATING, THESIS INVALIDATED, RESEARCH REQUIRED); CONSTRUCTIVE (WATCH, SETUP DEVELOPING, NEAR ENTRY, ENTRY CONDITIONS MET); m = 20; an unseen or missing status uses B0. RESEARCH REQUIRED is placed with the risk statuses because it is not a constructive status (interpretation written here before any fit) |
| B2 | L2 logistic regression (numpy Newton, intercept unpenalised) on log1p liquidity, log1p market cap, log1p 24 h volume, fatal flag present (required) and log1p(token age in days) (optional: median fill and a missing indicator, a negative age is missing) | C = 1.0, training-only preprocessing (drop columns constant or all missing in training, median fill, missing indicators, standardisation); a row missing a required feature gets no number (OOD) and is not a training row |
| B3 | the lab's 100-point score, Platt sigmoid fitted on training rows only (non-probability comparator; the score is never changed) | none; a row without a score is OOD |
| B3F | prevalence by fatal flag present or absent, shrunk toward B0 as B1 | m = 20 (added from the phase guidance "score and fatal flags") |
| B4 | matched-training prevalence: training rows of other mints whose liquidity and market cap are each within a factor 3 of the row's, shrunk toward B0 | factor 3, m = 20; no match gives B0; liquidity or market cap missing gives B0 |
| B4C | contemporaneous matched control, DESCRIPTION ONLY: outcome rate of other-mint development decisions within 12 h of the row, liquidity and market cap within a factor 3; uses outcomes that are not known at the decision, so it is never a forecaster, never in a skill comparison and never an artifact; it shows how much of the outcome is shared by concurrent tokens | window 12 h, factor 3, at least 3 controls else none |
| NC1 | B2 refitted on training labels shuffled inside each fold's training rows | seeds 0 to 19 |
| NC2 | future-feature trap: a column made from path candles after `t_entry` (the label's first-touch candle), declared with its true availability | must be refused by `validate_rows` and by the baseline column allowlist on every row; never reaches a fit |
| NC3 | same-ticker join trap: the 4 real same-symbol mint pairs among labelled development decisions, joined by symbol | must be refused by the identity join on every pair |

Not run: any other model, feature set, hyperparameter or calibration variant. Venn-Abers and Page-Hinkley are ported with tests (ROADMAP) but not used here.

## Splits (frozen, ACCEPTANCE walk_forward)

Expanding window by UTC decision day; first cutoff at 2026-10-12T00:00Z, extended by whole days until at least 100 training events; a fold's training rows are `training_labels(dev_con, cutoff, target)` (decided before the cutoff, labels matured by it); its validation rows are development labels decided in [cutoff, cutoff + 1 day). The walk-forward index computed from the label table must equal the gate's rows (cross-check, fails loudly). A fold fits B1 to B4 only when its training rows reach 100 events and 20 per class (ACCEPTANCE minimums); otherwise only B0 is described for that fold and the other baselines abstain with INSUFFICIENT_HISTORY. Fold audit (ported, fail closed) with the target's own maturity lag and mint groups. Split-rule fingerprint `46b6b9052b770d5d91888fa6c855f1e7e91260f4dbe838fbcb5233de08ba96c6` (sha of ACCEPTANCE walk_forward, registry fingerprint and the two training minimums); the realised fold indices are fingerprinted at run time.

## Metrics and their rules (fixed)

| Item | Rule |
|---|---|
| Pooled out-of-sample set | all validation rows of all folds, each predicted by its own fold's models |
| Scores | Brier (primary), Brier skill score versus B0 on the same rows, log loss (clip 1e-6), ROC AUC and average precision only when each class has at least 10 out-of-sample events; counts, positives, prevalence, decision days and mints beside every number (P23) |
| Intervals | bootstrap of the Brier skill score over whole decision days and over whole mints, 2,000 replicates each, seed 20261025, 95% percentile; the wider governs; a day bootstrap with fewer than 5 days is UNDEFINED (no interval) and then the governing interval is UNDEFINED |
| Effective sample size | decision days, distinct mints, and n times the ratio of the independent-rows variance to the block-bootstrap variance of the mean squared error, for days and for mints |
| p-value and Holm | one-sided bootstrap p = (1 + replicates with BSS <= 0) / 2,001 from the governing bootstrap; Holm across the three primary targets per baseline; undefined when the governing interval is undefined |
| Calibration | quantile bins of at least 20 events, at most 5; with fewer than 40 events calibration in the large only; mean prediction inside the 95% Wilson interval of the observed rate; ECE descriptive |
| Coverage | per baseline: share of out-of-sample rows with a computed number, and abstention reasons (INSUFFICIENT_HISTORY, OOD); no number is published (no holdout calibration exists) |
| Verdict per target and baseline | INSUFFICIENT_HISTORY (no fold passes the training gate or no out-of-sample rows), INSUFFICIENT_DAYS (fewer than 5 out-of-sample decision days: no claim, ACCEPTANCE min_effective_days), NOT_DISTINGUISHABLE_FROM_BASE_RATE (governing interval contains 0), WORSE_THAN_BASE_RATE (upper bound below 0), SKILL_INDICATED_DEVELOPMENT_ONLY (Holm-adjusted lower bound above 0; never a promotion, the holdout is untouched) |
| Sensitivities | new mints only, creator groups (rows whose creator is not in training; unknown creator kept), narrative groups where `narrative_id` is known, without KEY_CONFLICT decisions, PIT_RECORDED route only; descriptive cohort tables by route, status group, liquidity bucket, launch-age bucket, week and day |
| Training prevalence description | per target at the development end (as of 2026-10-17T00:00Z): n, positives, Wilson interval, days, mints; per cohort a rate only where n >= 20 |
| Cost | wall and CPU time per run, 0 network calls (audit hook refuses any socket connect), 0 vendor calls |

## Train-only artifacts

Per primary target, B0, B1, B2, B3, B3F and B4 fitted on all development labels as of 2026-10-17T00:00Z (the holdout start; development rule), each a JSON card with model id, model sha (sha256 of the canonical card without its own sha), feature-set sha, model column list and its sha, training cutoff, target and version, labels version, registry fingerprint, label-set sha, data snapshot sha (decision keys with their snapshot sha256), counts, code sha256 of `stats.py` and `baselines.py`, status PROVISIONAL_PENDING_REVISION_REREAD and `revision_check_claimed: false`. Only fitted when the ACCEPTANCE training minimums hold. Phase 12 evaluates them once on the sealed holdout; Phase 07 never opens it.

## Checklist

| Id | Check | How it is verified | Fails if |
|---|---|---|---|
| G1 | Package unchanged | `sha256sum -c SHA256SUMS.txt` | a line not OK |
| G2 | Entry gate | suite at `b0275c6`, `check_seal.py` | anything but `1 failed, 1124 passed` with the known failure, or seal problems |
| G3 | PI-D-046 and PI-D-047 recorded before any fit | DECISIONS.md in the pre-registration commit | missing or after a fit |
| G4 | Pre-registration before any fit | this file and `experiments/EXPERIMENT_REGISTRY.csv` committed before the first run of the baseline runner (commit time versus `evidence/run_log.json` start time) | a run before the commit |
| G5 | Numpy core ported with tests | `memelab/predictive/stats.py` (numpy and standard library only): scores, Wilson, Holm, preprocessing, logistic, Platt, Venn-Abers, day walk-forward, fold audit, Page-Hinkley, AUC, average precision, calibration bins, block bootstrap; every Phase 04 prototype test ported to synthetic data in `tests/test_predictive_stats.py` | a prototype test not ported, or a third-party import |
| G6 | Oracle agreement | scikit-learn 1.9.1 in the research venv only: logistic within 1e-6 on every real fold design, AUC, average precision, Brier and log loss within 1e-12 | a larger difference |
| G7 | Gate use | every training row comes from `labels.training_labels` at the fold cutoff; the walk-forward index equals it; no file under the sealed folder or the bake-off folder is opened (the gate refuses both; a test) | a row from anywhere else |
| G8 | As-of features | every model column passes `validate_rows` with its availability at or before the decision and the decision at or before the fold cutoff; columns outside the allowlist refused (NC2) | a future or undeclared column reaching a fit |
| G9 | Fold audit | every fold valid under the ported audit with the target's maturity lag; training labels mature by the cutoff; mint overlap reported | an invalid fold |
| G10 | Count gates | no B1 to B4 fit on a fold or artifact below 100 events or 20 per class; abstention INSUFFICIENT_HISTORY recorded | a fit below the minimum |
| G11 | Metrics complete and honest | `experiments/BASELINE_METRICS.csv` holds, per target and baseline, the rows above, the verdict, and the provisional flag; no claim on fewer than 5 days | a missing count, interval or verdict, or a claim on fewer than 5 days |
| G12 | Negative controls | NC1 mean Brier skill over 20 seeds at or below 0 (a positive mean is recorded as a finding, not hidden); NC2 refused on every row; NC3 refused on every pair | NC2 or NC3 accepted anywhere |
| G13 | Artifacts and serialization | cards written, read back, predictions identical, model sha recomputed equal, a changed coefficient refused; `runtime.verify_artifact` passes on the files | a mismatch or a pickle |
| G14 | Contract | an ABSTAIN document per target built from the artifacts passes `contract.validate`; a FORECAST document claiming a probability is refused (no holdout calibration) | a probability accepted |
| G15 | Determinism and isolation | the runner twice in fresh processes gives identical output sha256; 0 network calls; nothing written under tracked `data/`, `inbox/`, `state/` | any difference or a write |
| G16 | Synthetic fixture | a seeded synthetic fixture with known signal: B2 beats B0, NC1 does not, and its outputs carry NO_REAL_HISTORICAL_EVIDENCE | fixture output without the flag |
| G17 | Search ledger | `experiments/SEARCH_LEDGER.csv` lists every configuration run here (including each NC1 seed and every evaluation view) and the Phase 04 bake-off runs as tried configurations (PI-D-034) | an unlogged run |
| G18 | Flag and imports | flag OFF; no existing module imports the new code (existing test); no change to the score or fatal flags | a change |
| G19 | Adversarial scenarios | tests for P10, P11, P13, P20, P21 (by-week view), P23, P24, P38, P43, and a new counterexample CX-07 caught by a test | a scenario without a test |
| G20 | Suite, guard and audits after the commit | full suite (no new failure), `python -m memelab social guard`, `python tools/release_audit.py --history`, `check_seal.py`; `git status` clean | any new failure |

## Expected result, stated in advance

With about 9 to 10 decision days in development and 26 to 34 positives per target, the frozen walk-forward will leave few out-of-sample days. The expected verdicts are INSUFFICIENT_HISTORY or INSUFFICIENT_DAYS, at best NOT_DISTINGUISHABLE_FROM_BASE_RATE (Phase 01 ACCEPTANCE_METRICS, PI-D-016). The phase gate is met by actual baseline numbers or by this explicit insufficient-evidence stop.
