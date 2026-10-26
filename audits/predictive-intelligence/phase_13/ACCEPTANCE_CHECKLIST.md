# Phase 13 acceptance checklist and pre-registration (written before any Phase 13 code and before any fit on real data)

Written 2026-10-26 from 20:20Z by the Phase 13 agent, after the entry gate at `6f4f8ea` (suite `1 failed, 1455 passed in 197.15s`, exit 1, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; strays `data/reports/20261026_2012_BRETT_0x532f.md`, `data/memelab.sqlite-shm` and `-wal` removed by hand; `check_seal.py` exit 0 with `"problems": []` and the three pinned hashes; Phase 12's key tests `tests/test_predictive_evaluation.py` and `tests/test_predictive_phase12_outputs.py` 57 passed; Phase 12 RESULTS.json PASS; tracked `data/memelab.sqlite` sha256 `068287c0...` and both private stores equal to Phase 12's records), after reading the package (41 of 41 checksums OK), the phase prompt, ADVERSARIAL_SCENARIOS, DATA_TIME_CONTRACT, SCIENTIFIC_VALIDATION, NO_GO_DECISION_TREE, FORECAST_OUTPUT_SCHEMA, every PI-D entry (PI-D-001 to PI-D-066), ROADMAP's known constraints, the Phase 07 and 12 deliverables and `memelab/predictive/*.py`. Evidence of the entry gate: `evidence/entry/`.

This file, `experiments/EXPERIMENT_REGISTRY.csv` and PI-D-067 are committed before any Phase 13 code is written and before any calibrator, interval or diagnostic is computed on real data (PI-D-045 item 5).

What was looked at before writing it: the recorded Phase 07 out-of-sample counts (T1 24 h 24 rows with 8 positive over 3 days, T1b 6 h 44 with 3 over 5 days, T2 24 h 8 with 1 over 1 day; PI-D-049, PI-D-055) and the Phase 12 holdout results (PI-D-065, PI-D-066). Nothing new was computed on any label.

## Status rules carried in

- The retrospective holdout is opened and spent (PI-D-065). It is never a calibration fit set, never calibration evidence for publication and never a selection basis. Anything Phase 13 computes on it is POST_OPENING: logged in `calibration/POST_OPENING_LOG.json`, computed from committed Phase 12 outputs (never `phase_06/sealed/`), and combined through `evaluation.conservative_status` so it can only make a statement more conservative.
- Development labels only through `labels.training_labels` (and the Phase 07 runner functions that call it). No new vendor, crawler, Firecrawl or language-model call; 0 network calls (audit hook).
- Champion per target is B2 by default (Phase 12, PI-D-064 item 2), not by evidence; every other card is MODEL_NOT_PROMOTED. Nothing reached SHADOW; every card level is ABSTAIN.
- numpy-only core in `memelab/predictive/` (flag OFF, imported by no existing module); scikit-learn, ip200/venn-abers and statsmodels only as oracles in the research venvs.
- The contract (`contract.py`: CONTRACT_VERSION `memelab.predictive.forecast/1`, ABSTAIN_REASONS, ACCEPTANCE, registry fingerprint `4b4aabce...`) is not changed. New vocabulary lives in the new modules as detail codes, each mapped to one existing contract reason.

## Frozen rules of calibration-1 and abstention-1 (fixed here, before any code)

1. Calibration set. For target t at cutoff T: the champion's chronologically valid out-of-sample rows of the development walk-forward (each scored by the fold card trained at its fold cutoff, decided before T, label matured by T). They are re-derived by the runner from the Phase 07 fold cards and the gate, and must equal `phase_07/experiments/OOS_PREDICTIONS.csv` within 1e-12. In-sample predictions of the card on its own training rows are never a calibration set.
2. Fit gate (calibrator). n at least 100, at least 20 per class (ACCEPTANCE `min_train_events`, `min_train_per_class`) and at least 5 decision days (`min_effective_days`). Below it: no calibrator, status UNCALIBRATED, detail CALIBRATION_SET_TOO_SMALL.
3. Method rule, fixed, no selection on outcomes: VENN_ABERS when n is at least 200 with at least 40 per class; else PLATT when the fit gate holds; else none. Isotonic is used only inside Venn-Abers.
4. Calibration check, the frozen tolerance of ACCEPTANCE `calibration`: `stats.calibration_bins` (mean prediction inside the Wilson 95% interval of the observed rate, in the large and in every quantile bin of at least 20 events, at most 5 bins, in the large only below 40 events), on out-of-sample evidence not used for the fit, with at least 50 events and 10 per class (`min_holdout_events`, `min_holdout_per_class`). The only admissible evidence from here on is the prospective holdout (Phase 19); until it matures the evidence status is NOT_YET_MATURED.
5. Calibration status: CALIBRATED only when a calibrator was fitted and the check passed on admissible evidence; otherwise UNCALIBRATED with named details. Level: ABSTAIN unless a later registry (Phase 16) records SHADOW or VALIDATED_EXPERIMENTAL under ACCEPTANCE `promotion`.
6. Publication rule. A probability is issued only when every condition holds: flag ON; card level SHADOW or VALIDATED_EXPERIMENTAL; calibration status CALIBRATED; at least 20 calibration events in the score's calibration bin (support); the raw score inside the calibration score range; the calibrated point finite and inside the display range [0.01, 0.99] (ACCEPTANCE `display_probability_range`); the interval finite, inside [0, 1] and holding the point; no abstention condition. A SHADOW document carries the caveat SHADOW_RESEARCH_ONLY; every forecast carries INTERVAL_EXCLUDES_UNMODELED_RISK; a new mint's forecast carries COHORT_ESTIMATE_NOT_TOKEN_HISTORY. `calibration_reference` keys are an allowlist, and its numbers must equal the stored calibration card (PI-D-022). Otherwise the document is ABSTAIN with every named reason.
7. Interval. Hull of the calibrator's own interval (Venn-Abers [p0, p1]; the point for Platt) and the Wilson 95% interval of the observed rate in the support bin; so it widens as support falls (P23, P24). It describes calibration-sampling uncertainty under exchangeability only, never unmodelled risk (caveat above).
8. Degeneracy (P11). FLAT when max minus min of the predictions is at most 1e-9 (calibration set, evidence or a fixture stream): UNCALIBRATED, detail DEGENERATE_FLAT_PREDICTIONS. NEAR_FLAT when the population standard deviation is below 0.005: descriptive flag.
9. Score report (P10, P23). Brier, log loss (clip 1e-6), Brier skill and log-loss skill against the training prevalence, n, positives, days, day and mint bootstrap intervals of the Brier skill (2,000 replicates, seed 20261025, wider governs), AUC and average precision only with at least 10 per class, the FLAT and NEAR_FLAT flags, and BRIER_LOGLOSS_CONFLICT when the two skills have opposite signs. Both scores are always reported with their counts.
10. Event-rate uncertainty. Base rate with the Wilson interval and day-block and mint-block bootstrap 95% intervals (20,000 replicates, seed 20261025), the wider governing; design-effect ratio of widths.
11. Exchangeability. Day heterogeneity of the development event rate: chi-square statistic of the decision-day by outcome table, p from 20,000 label permutations (seed 20261025); p below 0.05 gives EXCHANGEABILITY_REJECTED_ACROSS_DAYS, otherwise NOT_REJECTED (never proof of exchangeability). The same for the label route (PIT_RECORDED against CURRENT_VENDOR_LIST). POST_OPENING only: development against retrospective-holdout prevalence by the same permutation test, descriptive.
12. Abstention conditions, each with its contract reason (all evaluated, none short-circuited, every one persisted with the attempted target and horizon):
    - FLAG_OFF: flag not ON (FLAG_OFF).
    - CHAIN_OUT_OF_SCOPE: chain not `solana` (OUT_OF_SCOPE_CHAIN).
    - MINT_NOT_VERIFIED: not an exact base58 address decoding to 32 bytes (UNVERIFIED_EVENT).
    - TARGET_NOT_PRIMARY: target not PRIMARY in the registry (TARGET_NOT_FEASIBLE).
    - POOL_NOT_POINT_IN_TIME: no point-in-time pool on the registry's price route at the decision (in replay the CURRENT_VENDOR_LIST route) (TARGET_NOT_FEASIBLE).
    - MARKET_INACTIVE: no reference candle with market-inactive evidence (NO_RECENT_PRICE).
    - SOURCE_GAP: vendor or route gap at the decision (SOURCE_STALE).
    - DISALLOWED_INPUT: an input from the sealed folder, a bake-off label, a column outside the card's allowlist, an input available after the decision, or a behavioral-simulation number (RESTRICTED_SOURCE).
    - SIZE_REQUESTED: a position size was asked for (EXECUTION_DATA_MISSING, NO_HISTORICAL_EXECUTABLE_DEPTH).
    - BACKTEST_REQUIRED_NOT_AVAILABLE: the caller requires a stress assessment and backtesting is BACKTEST_NOT_AVAILABLE (EXECUTION_DATA_MISSING).
    - MISSING_REQUIRED_INPUT: a required model input is missing (OOD).
    - FEATURE_OUT_OF_RANGE: a required input standardised by the card's training preprocessing has |z| above 4 (OOD).
    - SCORE_OUTSIDE_CALIBRATION_RANGE: raw score outside the calibration set's score range (OOD).
    - NO_TOKEN_HISTORY: the card needs the mint's own history and none is matured (INSUFFICIENT_HISTORY).
    - MODEL_NOT_PROMOTED: card level not SHADOW or VALIDATED_EXPERIMENTAL (MODEL_NOT_SELECTED).
    - NO_CHAMPION: no champion card for the target (MODEL_NOT_SELECTED).
    - MODEL_TRAINED_AFTER_DECISION: card cutoff after the decision (MODEL_NOT_SELECTED; the replay guard of `evaluation.check_card_time`).
    - MODEL_TOO_OLD: card older than 14 days at the decision (MODEL_STALE).
    - FEATURE_SET_MISMATCH: feature set sha differs from the card's (FEATURE_SCHEMA_MISMATCH).
    - INVALID_PROBABILITY: raw or calibrated number non-finite or outside [0, 1] (MODEL_NOT_SELECTED, the runtime's COMPONENT_ERROR mapping, P38).
    - NO_CALIBRATOR: calibration status not CALIBRATED (UNCALIBRATED).
    - DEGENERATE_FLAT_PREDICTIONS: rule 8 (UNCALIBRATED).
    - POINT_OUTSIDE_DISPLAY_RANGE: calibrated point outside [0.01, 0.99] (UNCALIBRATED).
    - CALIBRATION_SET_TOO_SMALL: rule 2 (INSUFFICIENT_HISTORY).
    - CALIBRATION_EVIDENCE_TOO_SMALL: admissible evidence below 50 events or 10 per class (INSUFFICIENT_HISTORY).
    - LOW_SUPPORT: fewer than 20 calibration events in the score's bin (INSUFFICIENT_HISTORY).
    - CALIBRATION_EVIDENCE_PENDING: the admissible evidence is the prospective holdout and its labels are not matured (NOT_YET_MATURED).
    - DRIFT: Page-Hinkley (delta 0.005, threshold 2.0, at least 30 observations, increase only) on the champion's matured Brier loss minus B0's, in maturity order up to the decision, has alarmed (DRIFT_ALERT); earlier records are kept, never rewritten (P39).
13. Persistence. Every abstention is an ABSTAIN document of contract forecast/1 plus an `abstention-1` record (forecast id, chain, mint, target, horizon, decision time, every condition with its detail, its contract reason and a plain-language explanation), written to an append-only JSONL file that refuses to rewrite or drop an earlier line.
14. Behavioral simulation (P27). A behavioral number (agent share, vote or agreement) can never become `probability`: the publication validator refuses scenario entries and `calibration_reference` or `cohort` entries holding probability-like keys or numbers, and a calibration card whose source is a simulation.
15. Today. With the as-of time 2026-10-26T20:00:00Z, the layer's answer for every primary target is recorded in `calibration/TODAY_STATUS.json`. Expected: ABSTAIN with FLAG_OFF, MODEL_NOT_SELECTED, UNCALIBRATED, INSUFFICIENT_HISTORY and NOT_YET_MATURED.

## Deliverables

`models/CALIBRATION_CARD.md`; `models/FORECAST_RESULT_SCHEMA.json` with schema tests; `calibration/RELIABILITY_COVERAGE.csv` (reliability and coverage table with counts, base rates and Wilson bands); `calibration/ABSTENTION_MATRIX.csv` and `.md`; the calibration artifacts `artifacts/<target>/CALIBRATION_CARD.json` (the calibrated artifact: status, gate, method, parameters or none, sha); `calibration/ABSTENTION_RECORDS_DEV.jsonl`, `calibration/ABSTENTION_RECORDS_HOLDOUT_POST_OPENING.jsonl`; `calibration/EXCHANGEABILITY.json`; `calibration/BASE_RATE_UNCERTAINTY.csv`; `calibration/TODAY_STATUS.json`; `calibration/POST_OPENING_LOG.json`; `experiments/SEARCH_LEDGER.csv` (the Phase 12 corrected ledger plus every Phase 13 row); `memelab/predictive/calibration.py`, `memelab/predictive/abstention.py`; `tests/test_predictive_calibration.py`, `tests/test_predictive_abstention.py`, `tests/test_predictive_phase13_outputs.py`; probes (runner, oracle, mutation probe); evidence, RESULTS.json, SKEPTIC_PACKET.md, records.

## Checklist

| Id | Check | How it is verified | Fails if |
|---|---|---|---|
| G1 | Package unchanged | `sha256sum -c SHA256SUMS.txt` | a line not OK |
| G2 | Entry gate | suite at `6f4f8ea`, `check_seal.py`, Phase 12 key tests | anything but the known failure, a seal problem, a failed key test |
| G3 | Pre-registration first | this file, the registry and PI-D-067 committed before the first Phase 13 code commit | code or a real-data fit before the commit |
| G4 | Frozen code before the recorded run | modules, tests and runner committed before `run_calibration.py` runs on real data | a recorded run from uncommitted code |
| G5 | Calibration set is chronologically valid | runner re-derives the champion's out-of-sample rows from the fold cards through the training gate; equal to Phase 07's file within 1e-12; every row decided before and matured by its use time; no holdout or prospective row; tests refuse a row decided at or after T, a row maturing after T, a holdout-window row and an in-sample row | any such row used |
| G6 | Fit gate and method rule | rules 2 and 3 in code, tested at the boundaries (99 and 100 events, 19 and 20 per class, 4 and 5 days, 199 and 200) | a calibrator fitted below the gate or a method chosen another way |
| G7 | Calibrators match oracles | numpy Platt against scikit-learn's sigmoid calibration fit (`_sigmoid_calibration`) within 1e-6 on the fit's parameters; isotonic inside Venn-Abers against scikit-learn `IsotonicRegression`; Venn-Abers p0, p1 against ip200/venn-abers within 1e-12 on fixtures and on the real descriptive fits | a larger difference |
| G8 | Frozen calibration tolerance | `stats.calibration_bins` with ACCEPTANCE `calibration` values, unchanged; a test pins each number | another tolerance |
| G9 | Intervals widen with small support | tests: at a fixed observed rate the interval width is non-increasing in the support; a 30-event calibration set with a 0.95 point gives ABSTAIN (P24); Venn-Abers interval on the real descriptive fits reported with widths | an interval that narrows with less data, or a confident number on a small set |
| G10 | Abstention conditions | every condition of rule 12 has a test that triggers it and checks its contract reason and detail; all conditions are evaluated, none short-circuited; reasons are only from `contract.ABSTAIN_REASONS` | an untested condition, an unknown reason or a hidden one |
| G11 | P38 and invalid input | NaN, infinity, -0.1 and 1.1 raw scores and calibrated numbers never publish; NaN features are MISSING_REQUIRED_INPUT; the validator refuses a non-finite probability | any of these published |
| G12 | P11 and P10 | flat all-positive predictions flagged FLAT and fail calibration in the large; an always-negative model on a 1% event shows Brier skill at most 0, a worse log loss than the prevalence and no AUC claim | a degenerate model passing |
| G13 | Overconfident on a rare class | a model giving 0.9 to a 2% event fails the calibration check and abstains UNCALIBRATED | a published number |
| G14 | P23 | a fixture where Brier and log loss disagree gives BRIER_LOGLOSS_CONFLICT with both scores, counts and intervals | one score hidden |
| G15 | P27 | an agent agreement of 0.9 in a scenario, in `calibration_reference`, in `cohort` or as a simulation-sourced calibration card is refused | accepted |
| G16 | P12 | a new mint with a token-history card abstains INSUFFICIENT_HISTORY; a cross-sectional fixture forecast for a new mint without COHORT_ESTIMATE_NOT_TOKEN_HISTORY is refused | accepted |
| G17 | P39 | a drifting loss stream raises DRIFT_ALERT for later decisions; earlier persisted records are byte-equal after the alarm; the JSONL writer refuses a rewrite | records rewritten or no alarm |
| G18 | Publication rule | a fixture with every condition met publishes a FORECAST that passes `contract.validate` and the new validator; removing any single condition turns it into ABSTAIN with that reason; a SHADOW forecast without its caveat, a `calibration_reference` number that differs from the card, an unknown key in it, or a level of ABSTAIN is refused | a probability published with a condition missing |
| G19 | Schema | `models/FORECAST_RESULT_SCHEMA.json` validates every document and record the runner writes (in-house checker in the tests; jsonschema in a research venv as an oracle when present); mutated documents are refused | a written document outside the schema |
| G20 | Real result | for each target: calibration set counts, gate result, status, reliability of the raw champion out-of-sample numbers with Wilson bands, base rate with Wilson and block intervals, exchangeability, abstention and coverage rates by fold; expected UNCALIBRATED for all three | a calibrated status or a published probability without the gate |
| G21 | Holdout description only | POST_OPENING rows logged, computed from committed Phase 12 files, labelled POST_OPENING, never used to fit, select or promote, combined by `conservative_status`; the sealed folder untouched (seal check after) | a holdout row in a fit or a claim |
| G22 | Today | `TODAY_STATUS.json` ABSTAIN for every target with named reasons | a probability |
| G23 | Search ledger | every Phase 13 configuration and description in `experiments/SEARCH_LEDGER.csv` with kinds `evaluation.ledger_totals` classifies; candidate configurations and N_search unchanged (87, 118) because no forecaster is added | an unlogged configuration or a changed N_search without a record |
| G24 | Determinism and isolation | two runs of the runner give identical output files except the run log; 0 network calls; stores, tracked `data/` and the sealed folder unchanged | any difference or write |
| G25 | Tests and mutation probe | a mutation probe at HEAD over `calibration.py` and `abstention.py` catches every listed mutation | a surviving mutation |
| G26 | Flag, imports, registry, contract | flag OFF; no existing module imports the new modules; `contract.py`, ACCEPTANCE and the registry fingerprint `4b4aabce...` unchanged; score and fatal flags unchanged | a change |
| G27 | Suite, guard and audits after the commit | full suite (no new failure), `python -m memelab social guard`, `check_seal.py`, single-branch `python tools/release_audit.py --history`; `git status` clean | any new failure |

## Counterexample CX-13 (named before building)

A plausible wrong design notices that the retrospective holdout now has 66 (T1), 68 (T1b) and 59 (T2) labelled rows, more than the 50-event evidence minimum, fits Platt on those rows, checks calibration in the large on the same rows (it passes by construction), and publishes "calibrated" B2 probabilities. That reuses a spent holdout, fits and checks on one set, and publishes from a card that never reached SHADOW. Caught by: the calibration set rule (only development out-of-sample rows decided before and matured by the cutoff; a holdout-window row is refused), the fit gate (100 events, 20 per class), the evidence rule (admissible evidence is not the fit set and not the spent holdout), and the publication validator (level ABSTAIN refused). A test builds exactly this case and shows each check refusing it.

## Expected result, stated in advance

Calibration cannot be fitted for any primary target on development data: the champion's out-of-sample calibration set holds 24 (T1), 44 (T1b) and 8 (T2) rows with 8, 3 and 1 positive, far below 100 events with 20 per class, and no larger chronologically valid set exists (the first fold needs 100 training events). Status UNCALIBRATED for all three; every forecast ABSTAIN with named reasons; publication coverage 0%. The gate is met by a layer that refuses unsupported numbers and states why, whatever the counts say.
