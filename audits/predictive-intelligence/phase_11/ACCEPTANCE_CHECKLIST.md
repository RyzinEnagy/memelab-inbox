# Phase 11 acceptance checklist and pre-registration (written before any cohort is built on a labelled row and before any fit)

Written 2026-10-26 from 15:05Z by the Phase 11 agent, after the entry gate at `aae7a55` (suite `1 failed, 1335 passed in 238.57s`, exit 1, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; the stray `data/reports/20261026_1455_BRETT_0x532f.md` and `data/memelab.sqlite-shm`, `-wal` removed by hand; `check_seal.py` exit 0 with `"problems": []`; Phase 10's key check `recompute_oos_social.py` exit 0, 326 numbers, 0 differences; Phase 10 RESULTS.json PASS; tracked `data/memelab.sqlite` sha256 `068287c0...` unchanged; both private stores equal to the sha256 in Phase 10's run log), after reading the package (checksums OK), the phase prompt, ADVERSARIAL_SCENARIOS, DATA_TIME_CONTRACT, SCIENTIFIC_VALIDATION, every PI-D entry (PI-D-001 to PI-D-060), ROADMAP's known constraints, the Phase 05 to 10 deliverables and `memelab/predictive/*.py`. This file, `experiments/EXPERIMENT_REGISTRY.csv` and PI-D-061 are committed before any cohort is computed on a labelled decision and before any model is evaluated (PI-D-045 item 5).

What was looked at before writing it, with no label read: over the 830 Solana decisions of the Phase 05 store decided before the holdout start, the 79 export instants, per instant the number of decisions and the median thesis 24 h volume in the trailing 24 h and the share of constructive lab statuses; the regime labels those give with a past-only median and with a full-sample median (counterexample CX-11 below); the launchpad (pump.fun 482 of all 925 Solana decisions, none recorded 257, others 186) and token program fields; creators (122 creators over the development decisions, 5 of them with more than one mint, 13 mints). No label value, class split, cohort rate or model number was computed.

## Status rules carried in

- Phase 06's frozen 48 h revision re-read passed (PI-D-059): Phase 11 numbers may state that the frozen revision check passed; its cards carry `revision_check_claimed: true` with the reference PI-D-059.
- Phase 11 never opens `phase_06/sealed/`; labels only through `labels.training_labels`. Censoring counts for the missing-data columns come from a SELECT of `decision_key, target, split, state, censored, decision_time, label_matures_at` on the development label store, never the `label` column.
- Verdicts use Phase 07's frozen functions unchanged (`baselines.evaluate`, `verdict`, `evaluation_gate`, `nc1_verdict`), Holm across the three primary targets per (model, reference). No new verdict code.
- No logistic or boosted model is fitted in this phase; B0 and B2 are refitted by Phase 07's code in the same folds and must equal Phase 07's out-of-sample numbers at 6 decimals. The neighbour search has its own oracle (scikit-learn `NearestNeighbors`, brute force, Euclidean) in the research venv.
- No vendor, crawler, Firecrawl or language-model call. 0 network calls (audit hook).
- The development data covers 9 to 10 decision days, most of them under one regime label, and the out-of-sample sets are 24 (T1), 44 (T1b) and 8 (T2) rows on 3, 5 and 1 days. Every regime breakdown (P21) is therefore expected to be INSUFFICIENT_DAYS or INSUFFICIENT_EVENTS, and is reported as such, not as a finding.

## Definitions (fixed)

Analog-1 (`memelab/predictive/analog.py`, version `analog-1`), numpy and the standard library only, flag OFF, imported by no existing module.

| Term | Definition |
|---|---|
| Analog pool at `as_of` | exactly the rows `labels.training_labels(dev, as_of, target)` returns, joined by `baselines.join` (identity, allowlist, availability) to version 2 snapshots, plus the decision's own token row (launchpad) and onchain-1 at its decision. Every pool row must have `decision_time < as_of` and `label_matures_at <= as_of` (checked again, FutureUniverseError), so a token first seen after `as_of` cannot enter (P43). No current token list, vendor list or later export is read (P09) |
| Target decision | one decision at T with `as_of <= T`; its inputs pass `features.validate_rows` with availability at or before T (P36) |
| Exclusions | a pool row of the same chain and mint is token history, never an analog; a pool row of the same creator wallet (token row `creator` at the decision) is excluded (P14); the leave-one-campaign-out sensitivity also excludes the same narrative tag at the decision |
| Independence unit | cluster = `creator:<wallet>` when the token row names a creator, else `mint:<address>`. One analog per cluster: the cluster's nearest row (kNN) or its newest row in the cell (strata). Duplicate windows of one token or one deployer never count twice |
| Effective N | `G` = number of distinct clusters among the selected analogs. Also reported: analog decision days, the day Kish ESS `(sum of per-day counts)^2 / sum of squared per-day counts`, analog mints, pool size, pool censored decisions (missing data) |
| Minimums | `G >= 20` (ACCEPTANCE `min_bin_events`) and analog days `>= 5` (`min_effective_days`), else ANALOGS_TOO_FEW. The pool itself must pass the training gate (100 events, 20 per class), else INSUFFICIENT_HISTORY |
| Cohort number | `(sum of analog labels + 20 x b0) / (G + 20)`, b0 = the pool prevalence (the lab's shrinkage convention m = 20, `baselines.M_SHRINK`); the raw cohort rate and its Wilson 95% interval on `G` are reported beside it. Research number only: `publishable: false`, never a probability in a forecast document |
| Time-change sensitivity | analogs split at their median decision time into OLDER and NEWER halves; both rates and Wilson intervals reported; TIME_UNSTABLE when the two intervals do not overlap (a flag, not a gate) |
| Strata (AC1) | cell = (`launch_age_bucket`, `liquidity_bucket`) of `labels.cohort_of` at the decision (first pool time and snapshot liquidity of the decision's own export). A target bucket UNKNOWN is OUT_OF_DISTRIBUTION (MISSING_INPUT); an empty cell OUT_OF_DISTRIBUTION (CELL_UNSEEN) |
| Neighbours (AC2) | distance over z-scored `thesis_log1p_liquidity_usd`, `thesis_log1p_mcap_usd`, `thesis_log1p_vol_24h_usd`, `log1p_token_age_days` (mean and population sd of the pool rows; sd 0 counts 1) plus 1 for each categorical mismatch of launchpad class (PUMP_FUN, OTHER_LAUNCHPAD, NONE_RECORDED) and `oc_token2022`; Euclidean. A missing input on the target is OUT_OF_DISTRIBUTION (MISSING_INPUT); pool rows missing an input are not candidates. K = 30 nearest clusters (cluster distance = its nearest row, ties by decision key); fewer than 30 eligible clusters uses all of them, then the minimums apply |
| Out of distribution | the target's distance to its K-th analog above the 95th percentile (numpy linear) of the pool rows' own K-th nearest other-cluster distances: OUT_OF_DISTRIBUTION (FAR_FROM_ANALOGS) |
| Regime at T | from the Solana decisions visible at T (decision time at or before T, before the holdout start): activity = median `thesis_log1p_vol_24h_usd` of the decisions in (T - 24 h, T]; tone = share of them with a constructive lab status (`baselines.status_group` CONSTRUCTIVE). Each is compared with the median of the same quantity over the export instants strictly before T (past only): ACTIVE or QUIET (above the past median, else QUIET), RISK_ON or RISK_OFF (same); label `ACTIVE/RISK_ON` etc.; fewer than 5 earlier export instants is WARMUP. Every row read must be at or before T (LeakageError otherwise). Chain-wide state CHAIN_WIDE_DATA_NOT_AVAILABLE and catalyst category CATALYST_TABLES_NOT_EXPORTED (PI-D-058) on every record. No smoothing, no full-sample statistic, no fitted switching model (statsmodels MarkovRegression smoothed probabilities are banned, Phase 03) |
| Regime-matched (AC3) | AC2 restricted to pool rows whose own regime label (at their own decision time) equals the target's label at T. Target WARMUP: ABSTAIN (REGIME_UNKNOWN); no pool row in that label: OUT_OF_DISTRIBUTION (REGIME_UNSEEN); OOD threshold from the restricted pool |
| Token history | rows of the pool with the same chain and exact mint; valid when at least 20 (`min_bin_events`); never merged by symbol or name (P01) |
| Router (`cohort_forecast`) | TOKEN_HISTORY when valid; else ANALOG_COHORT from AC3 (primary), labelled `COHORT_ESTIMATE_NOT_TOKEN_HISTORY` with `new_mint` set when the mint has no earlier decision visible at T; else ABSTAIN with every reason (TOKEN_HISTORY_TOO_SHORT and AC3's). A position size in the request gives EXECUTION_DATA_MISSING from `onchain.size_cap_usd` (no historical quotes, P44); every answer carries NO_HISTORICAL_EXECUTABLE_DEPTH and PRICE_PATH_NOT_PROCEEDS |
| Divergence (step 5) | for each answer with analogs: the target's `oc_mint_authority_active`, `oc_freeze_authority_active`, transfer fee present (`oc_transfer_fee_pct > 0`) and `oc_token2022` against the analogs; `<ATTR>_DIFFERS_FROM_ANALOGS` when fewer than half of the analogs with a known value share the target's value; `<ATTR>_UNKNOWN` when the target's value is missing; `oc_exit_cap_share` and `oc_round_trip_friction_pct` outside the analogs' 10th to 90th percentile gives `EXIT_CAP_SHARE_DIFFERS` or `FRICTION_DIFFERS`. Flags are part of the answer and never removed by segmentation |

## Candidate models (one configuration each, no tuning)

| Id | Model | Notes |
|---|---|---|
| AC1_STRATA | stratified cohort number | per the definitions |
| AC2_KNN | regime-blind neighbour cohort | the comparison that shows what regime handling changes |
| AC3_KNN_REGIME (primary) | regime-matched neighbour cohort | the router's analog path |
| AC3_LOCO | AC3 with the same narrative tag also excluded | sensitivity (leave one campaign out), never a separate claim |
| NC1-AC | AC2 on pool labels permuted inside each fold's pool | seeds 0 to 19, `nc1_verdict` |
| B0, B2 | Phase 07's, refitted by `baselines.fit_b0` and `fit_b2` in the same folds | out-of-sample numbers must equal Phase 07's at 6 decimals |

No other model, distance, K, threshold, shrinkage or regime definition is run.

## Comparisons, metrics and verdicts (fixed)

| Item | Rule |
|---|---|
| Primary | AC3 against B0 (Brier skill), all three primary targets, Holm across the three; T1 reported first |
| Secondary | AC1, AC2 against B0; AC2, AC3 against B2; AC3 against AC2 (regime handling); AC3 against the frozen primaries of Phases 08, 09 and 10 (`M2_T_LOGIT_B2`, `M2_OC_LOGIT_B2`, `S2_SC_LOGIT_B2`) on the rows where both have a number, read from their committed `OOS_PREDICTIONS.csv` (6 decimals; y and B0 per row must agree with this run) |
| Views | ALL, NEW_MINTS (mint absent from the fold's pool), NO_PRIOR_DECISION (version 2 `hist_prior_decisions` = 0), NO_KEY_CONFLICT |
| Regime breakdown (P21) | AC3, B2 and B0 by the target's regime label, same verdict code; a label with fewer than 5 days or below the out-of-sample minimums is INSUFFICIENT_DAYS or INSUFFICIENT_EVENTS |
| Scores and intervals | Phase 07's: Brier, skill, log loss (clip 1e-6), AUC and AP only with 10 per class, day and mint bootstrap 2,000, seed 20261025, wider governs, day interval undefined below 5 days, out-of-sample gate 50 events and 10 per class |
| Coverage | per target and model: answers with a number, abstentions by reason, median G, median analog days, day Kish ESS, pool size, pool censored decisions; per fold the pool's regime mix |
| Leave one campaign out | AC3 against AC3_LOCO: answers that change, Brier on common rows; descriptive |
| Degeneracy (P11, P38) | zero variance flagged DEGENERATE; non-finite raises |
| Cost | wall and CPU time, 0 network calls, 0 vendor calls, 0 Firecrawl credits |
| Promotion | none: every model MODEL_NOT_PROMOTED |

## Counterexample CX-11 (named before building)

A plausible wrong design labels regimes with full-sample statistics (a median, quantile or smoothed state over the whole development period, as a Markov switching model's smoothed probabilities do). Measured before building, without labels: with full-sample medians in place of past-only medians, 32 of the 74 non-warmup development export instants get a different regime label. Caught by `regime_as_of` reading only decisions at or before T and comparing with earlier export instants only (a test fails when either restriction is removed, and the truncation invariance test fails for the full-sample variant `regime_full_sample`, kept only as a trap), and the runner records the 32 on the real history.

Also measured before building: the count-based activity (decisions in the trailing 24 h) follows the lab's export cadence (hourly exports until 2026-10-11, one a day after), not the market, so activity uses the median 24 h volume of the visible decisions instead. This choice was made after seeing those unlabelled counts.

## Forecast trace and the two named validations

- Trace: the earliest out-of-sample T1 row (then T2, T1b) by decision time then mint with an AC3 number (else the earliest with any AC number, else the earliest row and its abstention): decision key, inputs, regime record, the pool keys at the fold cutoff, the selected analogs with distances, G, days, the number and interval. `probes/verify_trace_analog.py` recomputes the regime, the distances, the analog set and the number from plain SQL and the committed CSVs without `analog.py`.
- Reproducible cohort query: `probes/cohort_query.py --target T --decision-key K --as-of ISO` prints the cohort answer for any development decision as of any time at or before it; the runner calls the same function.
- New-token abstention test and OOD test: fixture tests for a new mint (cohort estimate labelled or ABSTAIN), ANALOGS_TOO_FEW, CELL_UNSEEN, FAR_FROM_ANALOGS, REGIME_UNSEEN, REGIME_UNKNOWN, MISSING_INPUT; real counts per reason.

## Checklist

| Id | Check | How it is verified | Fails if |
|---|---|---|---|
| G1 | Package unchanged | `sha256sum -c SHA256SUMS.txt` | a line not OK |
| G2 | Entry gate | suite at `aae7a55`, `check_seal.py`, Phase 10 recompute | anything but `1 failed, 1335 passed` with the known failure, seal problems, a recompute difference |
| G3 | Pre-registration before any cohort on labels | this file, the registry and PI-D-061 committed before `evidence/run_log.json` start | a run before the commit |
| G4 | Numpy core with tests | `analog.py` numpy and standard library plus `memelab.social.replay_core` (LeakageError) only; `tests/test_predictive_analog.py` | a third-party import or an untested rule |
| G5 | As-of pool | every pool row decided before and matured by `as_of`; no current list, later export or vendor list read; future-issued token refused (P43); cohort unchanged when rows after `as_of` are added (truncation invariance, P09) | a later row used |
| G6 | Same frozen folds | split fingerprints equal Phase 07's; B0 and B2 out-of-sample numbers equal at 6 decimals | a difference |
| G7 | Identity and groups | exact chain and mint for token history (P01); same creator excluded (P14); one analog per cluster; similarity never identity | a merge by symbol or a same-creator analog |
| G8 | Minimums and states | no number below G 20 or 5 analog days or a pool below the training gate; states ANALOGS_TOO_FEW, OUT_OF_DISTRIBUTION (with sub-reason), REGIME_UNKNOWN, INSUFFICIENT_HISTORY, TOKEN_HISTORY_TOO_SHORT | a number below a minimum |
| G9 | Regime as of T | `regime_as_of` past-only; WARMUP below 5 instants; truncation invariance on the real history (every instant); CX-11 flips recorded | a label that changes with later data |
| G10 | Metrics and verdicts | `experiments/ANALOG_METRICS.csv` per target, model, reference and view with counts, intervals, verdict | a missing count or verdict, or a claim under the minimums |
| G11 | Regime breakdown | `experiments/REGIME_BREAKDOWN.csv`, verdicts by the frozen code, stated INSUFFICIENT where so | a regime claim under the minimums |
| G12 | Cross-phase comparison | `experiments/CROSS_PHASE_COMPARISON.csv`; y and B0 agree per row with Phases 08 to 10 | a disagreement |
| G13 | Coverage and missing data | `experiments/COHORT_COVERAGE.csv`, `OOS_PREDICTIONS.csv` with G, days, Kish ESS, pool size, censored count, reasons | missing |
| G14 | Divergence | `experiments/DIVERGENCE_FLAGS.csv`; a fixture where the target's freeze authority differs keeps the flag beside a number | a flag dropped |
| G15 | Negative controls and traps | NC1-AC under `nc1_verdict`; NC2-AC (a pool label maturing after `as_of`) refused; P13-AC (a holdout-start card on an earlier decision) refused; P36-AC (target input available after T) refused; P43-AC (future-issued token in the pool) refused; P14-AC (same creator) excluded with real count; CX-11 | a trap accepted |
| G16 | Artifacts | holdout-start cards per target and model written, read back identical, model sha recomputed, tamper refused, `runtime.verify_artifact` | a mismatch or a pickle |
| G17 | Contract | an ABSTAIN document from each AC3 card passes `contract.validate`; a FORECAST with a cohort number refused | a probability accepted |
| G18 | Oracle | scikit-learn NearestNeighbors (brute, Euclidean) on every real AC2 and AC3 query of the run: same analog set, distances within 1e-9 | a difference |
| G19 | Determinism and isolation | two runs, identical outputs (except run log times); 0 network calls; stores unchanged; nothing written under tracked `data/`, `inbox/`, `state/` | any difference or write |
| G20 | Trace and cohort query | trace recomputed independently equal; `cohort_query.py` reproduces the trace's answer | a difference |
| G21 | Search ledger | `experiments/SEARCH_LEDGER.csv` = Phase 10's ledger plus every Phase 11 configuration, view, NC1 seed and any debug run | an unlogged run |
| G22 | Adversarial scenarios and mutation probe | tests for P01, P09, P12, P14, P21, P24, P43, P44, CX-11, future-issued tokens, leave one campaign out; the mutation probe runs at HEAD and catches every listed mutation | a scenario without a test or a surviving mutation |
| G23 | Flag and imports | flag OFF; no existing module imports `analog`; score and fatal flags unchanged; registry fingerprint `4b4aabce...` and ACCEPTANCE unchanged | a change |
| G24 | Suite, guard and audits after the commit | full suite (no new failure), `python -m memelab social guard`, `python tools/release_audit.py --history` on a single-branch clone, `check_seal.py`; `git status` clean | any new failure |

## Expected result, stated in advance

The analog numbers meet the same walls as every earlier phase: T1 and T2 out-of-sample sets reach 3 and 1 days (INSUFFICIENT_DAYS), T1b reaches 44 rows with 3 positive (INSUFFICIENT_EVENTS). The regime-matched cohort will often abstain, because the out-of-sample days fall in a quieter period than most of the pool; that abstention is the intended behaviour, not a defect. No regime breakdown can support a claim. The phase gate is met by the as-of cohort and regime layer, the abstention states, the leakage and identity tests and the honest coverage tables, or by an explicit stop.
