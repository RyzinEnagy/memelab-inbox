# Phase 20 scientific claims audit

Auditor's reading of every claim the predictive-intelligence records make about skill, edge, calibration or profit, against the evidence class each claim needs (SCIENTIFIC_VALIDATION.md, ACCEPTANCE in `memelab/predictive/contract.py`). Code and data at the frozen audit commit `0d66379` (lab and predictive code identical to `e0bc906`). Every statement that rests on a Phase 19 outcome is PROVISIONAL_PENDING_REVISION_REREAD (PI-D-106, G25 open).

## Bottom line

- No record claims predictive skill, an edge, a calibrated probability or a profit. Every real forecast document abstains: the 156 documents of the prospective window (Phase 18 published run, reproduced byte for byte in G5) and every document of the real-path smoke (G6) carry ABSTAIN with named reasons and no number.
- Publication coverage is 0%. The champion question is NO_VIABLE_CHAMPION for every primary target (Phase 16), every calibration card is UNCALIBRATED (Phase 13), MIROFISH_NO_GO and BACKTEST_NOT_AVAILABLE hold.
- The only evidence of out-of-sample value is descriptive and below the frozen minimums, or Holm-only on the spent holdout and failing the selection correction. None of the sensitivity readings below changes that.

## Claims found and their evidence class

| Claim (where) | Evidence class needed | Evidence present | Verdict of this audit |
|---|---|---|---|
| "B2 against B0: T1 NOT_DISTINGUISHABLE_FROM_BASE_RATE, T1b NOT_DISTINGUISHABLE (calibration failed), T2 INSUFFICIENT_EVENTS" (Phase 12, PI-D-065) | first opening of an untouched holdout, frozen minimums, Holm, selection correction | single logged opening, REPRODUCTION byte-equal (re-run here through `tests/test_predictive_reproductions.py`), max-T and Bonferroni recorded | supported; a negative result, correctly not a claim |
| "0 of 129 secondary comparisons survive the selection correction" (Phase 12, PI-D-066) | max-T over the search, N_search | corrected ledger; the static B1 against B0 on T1 is SKILL_INDICATED (Holm only) and FAILS_SELECTION_CORRECTION, NOT_A_CLAIM | supported; the sensitivity below finds the same small static signal and it stays not a claim |
| "No primary target is calibrated" (Phase 13, PI-D-069) | the frozen calibration gate | cards UNCALIBRATED, level ABSTAIN, publishable false (checked by scenario P24 against the committed cards) | supported |
| "MIROFISH_NO_GO, INSUFFICIENT_VALIDATION" (Phase 15) | eligible dated catalyst events, comparators | 0 of 100 eligible events, comparators B and D BLOCKED | supported; a research conclusion, not an engine claim |
| "Prospective B2 against B0 BSS T1 +0.264, T1b +0.033, T2 +0.419" (Phase 19 report) | at least 5 decision days, 50 events and 10 per class, the governing interval | 3 decision days (2 for T2), 22, 24 and 15 events; marked "descriptive only" in the report header and below the table; every verdict INSUFFICIENT_DAYS | supported as descriptive; not a claim; PROVISIONAL_PENDING_REVISION_REREAD |
| Any "FORECAST" number (fixtures, Phases 13, 17, 18) | a promoted champion, a calibration card on admissible prospective evidence | fixture only, watermarked FORMAT-ONLY, `is_fixture` true | TEST_ONLY by construction; scenario P25 and X01, X05 show the fixture number is withheld or refused under every planted defect |
| Execution or profit (any record) | historic executable depth, net-of-cost evidence | none exists (NO_HISTORICAL_EXECUTABLE_DEPTH, EXECUTION_DATA_MISSING, PRICE_PATH_NOT_PROCEEDS on every document and label) | no claim made; scenarios P08, P25, P44 show a size or profit wording is refused |

## Does the out-of-sample picture survive the changes the prompt names? (`evidence/oos_sensitivity.json`, POST_OPENING and PROVISIONAL, descriptive)

B2 against B0, Brier skill, day and mint bootstrap (2,000 replicates per seed, seeds 1 to 5, the wider interval governs). "Bound" is the range over the five seeds of the governing lower 95% bound.

| Data | Target | Reading | n | positives | days | BSS | governing lower bound | frozen minimums met |
|---|---|---|---|---|---|---|---|---|
| holdout (spent) | T1 | all | 66 | 15 | 7 | -0.024 | -0.158 to -0.151 | yes |
| holdout (spent) | T1 | one decision per mint | 57 | 15 | 7 | -0.045 | -0.182 to -0.175 | yes |
| holdout (spent) | T1 | PIT route only | 54 | 15 | 7 | -0.080 | -0.219 to -0.208 | yes |
| holdout (spent) | T1 | without first day | 60 | 14 | 6 | 0.002 | -0.134 to -0.128 | yes |
| holdout (spent) | T1 | without last day | 59 | 14 | 6 | 0.004 | -0.139 to -0.123 | yes |
| holdout (spent) | T1b | all | 68 | 12 | 7 | -0.083 | -0.169 to -0.160 | yes |
| holdout (spent) | T1b | PIT route only | 54 | 11 | 7 | -0.089 | -0.190 to -0.180 | yes |
| holdout (spent) | T2 | all | 59 | 7 | 6 | 0.292 | -0.024 to -0.016 | no (7 positives) |
| holdout (spent) | T2 | PIT route only | 48 | 7 | 6 | 0.235 | -0.095 to -0.081 | no |
| prospective | T1 | all | 22 | 5 | 3 | 0.264 | -0.036 | no |
| prospective | T1 | without last day | 15 | 5 | 2 | 0.303 | 0.072 to 0.086 | no |
| prospective | T1b | all | 24 | 3 | 3 | 0.033 | -0.552 | no |
| prospective | T2 | all | 15 | 3 | 2 | 0.419 | 0.100 to 0.123 | no (2 days, 3 positives) |
| prospective | T2 | PIT route only | 14 | 3 | 2 | 0.407 | 0.078 to 0.112 | no |

Readings on the CURRENT_VENDOR_LIST route alone have 0 positives (n 1 to 14): their "skill" is B2 predicting a low number where nothing happened, not information; listed in the JSON, not read as signal.

Static baselines against B0 on the spent holdout: B1 (status-group prevalence) T1 BSS 0.016 (bound 0.008 to 0.009) and T1b 0.077 (0.027 to 0.029); B3F (fatal-flag prevalence) T1b 0.058 (0.023 to 0.025). These are the only readings that meet the frozen minimums with a lower bound above 0. They are the same static signal Phase 12 recorded as SKILL_INDICATED by Holm alone and FAILS_SELECTION_CORRECTION (ledger rows `P12:...:P07_B1_vs_B0`), they are post-opening and uncorrected over 15 static comparisons and 5 seeds here, and a status group or a fatal flag carrying some base-rate information is what the lab's existing structure already shows. Not a claim; not a reason to promote anything.

Answers to the prompt's list:

- Changed seed: the governing bounds move by at most 0.03 across seeds 1 to 5; no verdict changes.
- Token grouping (one decision per mint): no change of sign or verdict.
- Start and end selection: dropping the first or the last decision day moves the prospective T1 and T1b point estimates and can lift a bound above 0 on 15 to 17 rows over 2 days; that is fragility below the minimums, the opposite of a robust signal.
- Data provider and route: every label comes from one vendor (GeckoTerminal, PI-D-018); the route split (PIT_RECORDED against CURRENT_VENDOR_LIST) is the available provider-side variation and is shown above. A second price provider was not available (no free historical OHLCV alternative was adopted, Phase 01); stated as a limit.
- Regime: every prospective decision is QUIET/RISK_OFF (Phase 19 D7) and the holdout held one regime label (Phase 12): no regime breakdown is possible (scenario P21).
- Realistic costs: no executable depth exists; no net-of-cost statement is possible or made (NO_NET_TRADING_EDGE is the honest reading of the absence, PRICE_PATH_NOT_PROCEEDS on every label).
- Static baselines: B2 does not beat B0 where the minimums are met; the static B1 and B3F carry a small Holm-only signal that fails the correction.

## Leakage gate (prompt item 2: a leak in source, feature, target, model training or a report must fail the gate)

| Stage | Executable check at the frozen code | Result |
|---|---|---|
| Source and decision time | CX-00A, CX-00B, CX-S1 (decision time is the first export commit, never `created_at`); recalculation (c): 28 of 28 decision keys rebuilt from the exact export rows | refused or equal |
| Feature | P36, CX-10, CX-08, the Phase 05 truncation proof re-run (1,500 decisions, 0 differences in both modes, G5) | refused or equal |
| Target | P05, P06, P37, CX-06, CX-S06; recalculation (a) 61 of 61 prospective labels and (b) 40 of 40 development labels re-derived from the raw vendor bodies with own code | refused or equal |
| Model training | P13, P43, CX-07, CX-12; X06 shows the serving path itself does not re-check a card's training maturity (finding F20-06) | the replay guard refuses it; the serving path did not at the audited code |
| Report or reader | P27, P41, P44, CX-18, CX-SK18, X01, X05; the carried Phase 18 minor 5 (F20-08) | refused, except the carried forged-point case |

The leakage gate holds on every real path at the audited code: no real champion exists, so F20-06 and F20-08 are latent and reachable only through fixture champions today; both are classified in `INDEPENDENT_FINDINGS.md`.
