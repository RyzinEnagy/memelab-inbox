# Phase 15 incremental-value results

Every number here comes from `INCREMENTAL_VALUE_RESULTS.json` (sha256 `9d993f30...`), written by `../probes/score_scenarios.py` at the frozen code `de41d26` (the repeat, after change control CP15-0, PI-D-080, of the first recorded run at `0abffd5`; every first-run value is equal, `../evidence/rerun_cp15_0_diff.json`). The blind coding it scores was committed first (`7b787bf`, `CODING_LOG.json`). Protocol: `EXPERIMENT_PROTOCOL.md` (PI-D-079). Nothing here is a probability, a model input or a claim.

## Headline

| Question | Answer | Basis |
|---|---|---|
| Eligible independently dated catalyst events | **0** of the 100 required | `EVENT_SET.csv`: no catalyst table in the tracked lab DB (only `social_snapshots`, 99 holder-change readings), none in the 79 development export commits (21 table names, none catalyst or social), `data/private/` absent, 0 CATALYST_EVENT observations in the 830 seeds; the 27 inbox candidate items are a listing state, a paid-boost list and ticker or name searches, one read before the first decision export, never classified |
| Did behavioral simulation (MiroFish, D) improve the forecast? | **Not tested**: D BLOCKED | no approved LLM or Zep spend (PI-D-005, PI-D-078); MIROFISH_GATE BLOCKED (PI-D-077) |
| Evidence-only LLM (B) | **Not tested**: BLOCKED | no approved LLM spend |
| Calibrated statistical classifier (C) | none exists | Phase 13 UNCALIBRATED everywhere; stand-ins B2, R2_SC_RULE, S2_SC_LOGIT_B2 (uncalibrated) |
| Rule-based narratives (A) against no-simulation baselines, out of sample | **INSUFFICIENT_DAYS** (T1, T2) and **INSUFFICIENT_EVENTS** (T1b), NO_UNCORRECTED_SKILL | E1 below |
| Decision | **INSUFFICIENT_VALIDATION**; **MIROFISH_NO_GO** for adoption (optional module stays OFF); **RULES_NOT_PROMOTED** | `scenario_eval.decide`, reasons ELIGIBLE_EVENTS_BELOW_100, D_NOT_RUN, B_NOT_RUN |

## What could not be compared, and why

- D, MiroFish: no approved LLM or Zep spend and no key. Even with spend, the Phase 14 evidence says its script path returns free text (NOT_CODABLE) and two same-seed runs differ, so it is UNSTABLE under the frozen grid until many repetitions and a pre-registered coder exist.
- B, the evidence-only LLM: no approved spend.
- P26 for both: the evaluated decisions are dated 2026-10-06 to 2026-10-23 and any evaluation would run after them. The lab cannot verify a hosted model's training cutoff, or that it has no later retrieval or tuning, so every such document carries LLM_PRETRAINING_CONTAMINATION_RISK and EXPLORATORY_NOT_AS_OF (Phase 14 rule 13). A retrospective MiroFish or LLM evaluation on these dates is therefore not a valid as-of test, whatever it scores. Only prospective events, with the run committed before the outcome matures, could be.
- C: no calibrated classifier exists (PI-D-069). The comparison uses the uncalibrated no-simulation numbers already committed in Phase 10, unchanged.
- Net decision utility: NOT_COMPUTABLE (NO_HISTORICAL_EXECUTABLE_DEPTH, EXECUTION_DATA_MISSING, BACKTEST_NOT_AVAILABLE).
- Abstention: the engine's actual state; every request abstains (Phase 13), coverage 0%, nothing to score.

## Event and snapshot counts

| Set | Rows | Distinct mints | Days | Export commits | Catalyst events |
|---|---|---|---|---|---|
| Development decision snapshots | 830 | 148 | 10 | 79 | 0 |
| Holdout-window decision snapshots | 95 | 81 | 7 | 7 | 0 |

These snapshots are not catalyst events and not independent units; they carry the lab's attention proxies only.

## E1: A_WARN on the development walk-forward out-of-sample rows (the as-of comparison)

A_WARN is the training-only event rate of the warned and the not-warned stratum, shrunk toward the training prevalence (m 20), fitted at each fold cutoff from `labels.training_labels`. Rows are the Phase 07 and Phase 10 folds. Every row's label equals `training_labels`. The restated B2, R2 and S2 numbers equal Phase 10's SOCIAL_METRICS (tolerance 1e-5 for 6-decimal inputs).

| Target | Rows (positives, days) | A_WARN Brier | B0 | B2 | R2_SC_RULE | S2_SC_LOGIT_B2 | A_WARN skill vs B0 | vs B2 | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| T1 24 h | 24 (8, 3) | 0.229726 | 0.229726 | 0.244867 | 0.221180 | 0.274380 (13 rows) | 0 (equal to B0: no rule speaks to T1) | +0.062 | INSUFFICIENT_DAYS |
| T1b 6 h | 44 (3, 5) | 0.066494 | 0.066669 | 0.059460 | 0.070635 | 0.066415 (37 rows) | +0.0026, interval -0.019 to 0.027 | -0.118 | INSUFFICIENT_EVENTS |
| T2 24 h | 8 (1, 1) | 0.138842 | 0.127496 | 0.152604 | 0.123434 | no number | -0.089 | +0.090 | INSUFFICIENT_DAYS |

Holm over the three targets: T1b 1.0 (T1 and T2 have no defined test and enter the family of three as p 1, `stats.holm`). Bonferroni at N_search 121: 1.0. Selection status NO_UNCORRECTED_SKILL on every target. Shuffled-seed control (warnings permuted within day): skill 0 (T1), -0.017 (T1b), -0.011 (T2). Rule statements in the out-of-sample rows: T1 0, T1b 6, T2 3.

## E2: rule warnings on every development label (descriptive only)

The rule table was written in Phase 14 after summaries of the same socialcat-1 inputs were public, so none of this is out of sample (RULES_AUTHORED_AFTER_DATA_PUBLIC). Day-stratified permutation with 2000 replicates, then Holm over the three targets.

| Target | Labelled (positives, days) | Warned | Hits | Precision (Wilson) | Prevalence (Wilson) | Lift | Recall | Coverage | p up (Holm) | Lead time of hits | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 24 h | 136 (34, 9) | 0 | 0 | none | 0.250 | none | 0 | 0 | none | none | NO_WARNINGS |
| T1b 6 h | 224 (26, 10) | 24 | 4 | 0.167 (0.067 to 0.359) | 0.116 (0.080 to 0.165) | +0.051 | 0.154 | 0.107 | 0.191 (0.382) | median 1.8 h (1.1 to 2.7, n 4) | DESCRIPTIVE_NOT_DISTINGUISHABLE |
| T2 24 h | 131 (28, 8) | 75 | 22 | 0.293 (0.202 to 0.404) | 0.214 (0.152 to 0.292) | +0.080 | 0.786 | 0.573 | 0.066 (0.198) | median 7.0 h (0.1 to 21.4, n 22) | DESCRIPTIVE_NOT_DISTINGUISHABLE |

No conflicting, not-codable, refused-window or missing-seed row exists (0 excluded). Independence: T1 136 rows on 99 mints, T1b 224 on 104 (96 rows share a mint and a day with another row), T2 131 on 96; the permutation exchanges decisions, so its p values are optimistic where mints repeat.

Read the T2 recall of 0.786 with its coverage of 0.573: the rules warn on most decisions, so they catch most drawdowns, and the precision is only 0.08 above the prevalence, which the permutation cannot tell from chance after Holm.

Per label (secondary, no verdict beyond the gates):

| Target and label | Warned | Hits | Precision | Prevalence | Raw p up | Holdout (POST_OPENING): warned, hits, precision against prevalence |
|---|---|---|---|---|---|---|
| T1b ORGANIC_ATTENTION_CONTINUATION | 24 | 4 | 0.167 | 0.116 | 0.191 | 8, 4, 0.500 against 0.176 (INSUFFICIENT_WARNINGS) |
| T2 ATTENTION_EXHAUSTION | 32 | 2 | 0.063 | 0.214 | 0.9995 | 16, 0, 0 against 0.119 (INSUFFICIENT_EVENTS) |
| T2 MANUFACTURED_ATTENTION_DUMP | 58 | 22 | 0.379 | 0.214 | 0.0045 | 14, 1, 0.071 against 0.119 (INSUFFICIENT_EVENTS) |

All three per-label rows are uncorrected secondary descriptions, and all three read as noise. MANUFACTURED_ATTENTION_DUMP on T2 (the lab's suspect-attention flag) has a small raw p on development (0.0045; 0.0045 under the mint-block nulls too, repair pass 2) but reads the same input (`sc_attention_suspect`) that Phase 10's R2 rule and S models already used, so it is not new information from a behavioral scenario, and on the opened holdout it does not replicate: 1 hit in 14 against a prevalence of 0.119, below the event gate and indistinguishable from the prevalence (which is not the same as reversing). ORGANIC_ATTENTION_CONTINUATION on T1b looks favourable on the holdout (4 of 8 against 0.176, raw permutation p 0.026, also 0.026 under the mint-block nulls) but sits below the warning gate of 20. ATTENTION_EXHAUSTION on T2 points the wrong way on development (2 of 32 against 0.214, raw p down 0.0115, 0.014 under the mint-block nulls). None is a finding.

## Controls

| Control | Result | Expected |
|---|---|---|
| NCB, bogus VERIFIED catalyst planted on an outcome-independent half of the decisions (426 of 830) | T1: 65 of 136 labelled warned, 20 hits, precision 0.308 against 0.250, lift +0.058, raw p up 0.032. Recorded verdict DESCRIPTIVE_NOT_DISTINGUISHABLE only through Holm over a family of three padded with two absent targets at p 1 (0.096). Judged as the single test it is (repair pass 2): FLAGGED by the decision-level null at 0.05; NOT_FLAGGED by the conservative mint-block p (0.120) | not flagged |
| NCB, bogus UNVERIFIED_EVENT catalyst | 426 RUMOR_FADE statements, all UNSCORABLE_NO_OUTCOME_SOURCE; 0 T1 warnings | all unscorable |
| NCS, shuffled seeds | E1 skill 0, -0.017, -0.011; E2 null is the permutation | no skill |
| P28, observation available 1 s after the decision | 830 of 830 seeds refused (OBSERVATION_AFTER_DECISION, POST_DECISION_DATE), 0 statements | all refused |
| P28, quoted text holding the T2 window end date | 830 of 830 refused (POST_DECISION_DATE), 0 statements | all refused |

The bogus control's raw p of 0.032 matters: a planted catalyst that by construction knows nothing about outcomes reaches a raw p below 0.05 on these data, so the decision-level permutation is not shown to be calibrated here. Raw decision-level p values on this sample are not evidence. The repair pass 2 addition below shows why (CX-S15) and gives a null that passes the same kind of check.

## E3: the opened holdout (POST_OPENING description only)

Seeds for the 95 holdout-window decisions were built and coded blind with the development seeds. Labels come from the public, spent `phase_12/validation/HOLDOUT_SCORED.csv` (PI-D-065). Logged in `POST_OPENING_LOG.json`; combined only through `evaluation.conservative_status`.

| Target | Rows (positives, days) | Warned | Hits | Precision | Prevalence | Warning verdict | A_WARN fitted at the holdout start: skill vs B0 (interval), vs B2 | Status |
|---|---|---|---|---|---|---|---|---|
| T1 24 h | 66 (15, 7) | 0 | 0 | none | 0.227 | NO_WARNINGS | 0 (equal to B0), +0.024 | NO_UNCORRECTED_SKILL |
| T1b 6 h | 68 (12, 7) | 8 | 4 | 0.500 | 0.176 | INSUFFICIENT_WARNINGS | +0.015 (-0.004 to 0.036), +0.091 | NO_UNCORRECTED_SKILL |
| T2 24 h | 59 (7, 6) | 26 | 1 | 0.038 | 0.119 | INSUFFICIENT_EVENTS | -0.106, -0.564 | NO_UNCORRECTED_SKILL |

The T2 warnings that looked slightly favourable on development data are below the prevalence on the holdout (1 of 26, below the event gate). Combined status with E1: NO_UNCORRECTED_SKILL on every target; nothing becomes a claim.

## Other measures of comparator A

| Measure | A (behavioral-rules-1) |
|---|---|
| Hindsight contamination | 0 of 830 development and 0 of 95 holdout-window seeds refused; no post-decision content (the P28 traps show the checks fire); P26 NOT_APPLICABLE (no model). Blinding basis, stated as it is (skeptic m3): the coding probe's guard makes `training_labels`, the label stores, the sealed folder and the prediction files raise, but it does not block the Phase 05 feature store (which holds post-decision candles) or `data/memelab.sqlite`. Blindness rests on the code path (the coder reads only the rule documents, whose seeds carry socialcat-1 proxies available at each decision, 0 late observations in 925 seeds) and, for the 830 development documents, on their equality with Phase 14's committed documents, not on the guard alone |
| Variance | deterministic: the 830 documents recomputed equal to Phase 14's; coding and scoring twins byte-equal; no seed or persona grid applies |
| Hallucinations | 0 statements citing a non-seed observation (the validator), 0 ungrounded catalysts on real seeds, 0 refused claims |
| Ambiguous or vague | 227 development documents NO_GROUNDED_SCENARIO (no statement); 0 CONFLICT, 0 NOT_CODABLE, 0 REFUSED_WINDOW |
| Cost and latency | 0 USD, 0 LLM calls; coding about 41 s for 925 documents plus controls, scoring about 7 s |

## Adversarial tests the phase names

| Test | Where it is checked | Result |
|---|---|---|
| P26 LLM historical knowledge | protocol 8; `scenario_eval.decide` needs a verified training cutoff before the events (test `test_go_candidate_needs_every_condition`, reason P26_TRAINING_CUTOFF_NOT_VERIFIED) | NOT_APPLICABLE to A (no model); B and D would be EXPLORATORY_NOT_AS_OF on these dates |
| P27 90% agent consensus | Phase 14 validators (no agreement number, one hypothesis per label, PI-D-076); the decision rule never promotes on agreement | no agreement number in any A document; no probability created |
| P28 leaked future event | the two traps on every development seed | 830 of 830 refused for each, 0 statements |
| P29 seed reversal | Phase 14 stability (MONITOR_REVERSED, CX-S14); A is deterministic (twin runs byte-equal) | A has no seed; D not run, UNSTABLE under the frozen grid per Phase 14 |
| P30 unavailable provider | Phase 14 failure matrix; `decide` with D or B not run (test `test_decision_with_no_events_and_blocked_comparators_is_insufficient_and_no_go`) | B and D BLOCKED, reasons D_NOT_RUN and B_NOT_RUN, decision INSUFFICIENT_VALIDATION |
| P45 invented catalyst | NCB VERIFIED and UNVERIFIED_EVENT controls; repair pass 2 per-mint bogus control | VERIFIED: raw p 0.032, FLAGGED by the decision null as a single test, NOT_FLAGGED by the conservative p (0.120); per-mint bogus warning NOT_FLAGGED on every target; UNVERIFIED 426 of 426 unscorable |

## Examples chosen by the frozen rule (not cherry-picked)

- A correct: `1d2ce250...` (mint `EFn88Cii...`, 2026-10-07T21:53:55Z), MANUFACTURED_ATTENTION_DUMP, T2 EVENT, drawdown first touched 17.9 h after the decision.
- A fails: `09bfee4e...` (mint `6GmAFSYs...`, same export), ATTENTION_EXHAUSTION and MANUFACTURED_ATTENTION_DUMP, T2 EVENT, no drawdown.
- A cannot be scored: `3aa19f76...` (mint `8nnaeWCw...`, same export), NO_GROUNDED_SCENARIO, no statement on any target; and every NCB UNVERIFIED_EVENT statement (RUMOR_FADE, unscorable catalyst monitor).
- D (MiroFish): correct NOT_AVAILABLE, fails NOT_AVAILABLE; cannot be scored: the Phase 14 probe run `meter_cap_high` (SIMULATION_RAN, NOT_CODABLE free text on a fictional seed with a canned mock LLM), which `scenario_eval.code_document` refuses (test).

## Repair pass 2 addition: mint-block nulls (PI-D-082, skeptic CX-S15)

The rule warnings follow a mint's persistent attention proxies, so they cluster by mint, while the recorded permutation exchanges decisions within a day. `../probes/mint_null.py` at the frozen code `869d597` writes `MINT_CLUSTERED_NULL.json` beside the recorded outputs (which it does not change): two mint-block nulls (mints within each day; whole mints over the whole sample) and a conservative p, the largest of the three. Every decision-level p it recomputes equals the recorded one.

| Check | Decision-level null | Conservative p (mint-block) |
|---|---|---|
| E2 T1b, Holm p up | 0.382 | 0.733 |
| E2 T2, Holm p up | 0.198 | 0.198 |
| E2 verdicts | DESCRIPTIVE_NOT_DISTINGUISHABLE (T1b, T2), NO_WARNINGS (T1) | unchanged |
| E3 verdicts (POST_OPENING) | NO_WARNINGS, INSUFFICIENT_WARNINGS, INSUFFICIENT_EVENTS | unchanged |
| Recorded NCB VERIFIED on T1, single test at 0.05 | FLAGGED (raw p 0.032) | NOT_FLAGGED (0.120) |
| Bogus warning planted per mint, single test at 0.05 (T1, T1b, T2) | NOT_FLAGGED on each | NOT_FLAGGED on each |
| Calibration: share of 400 salts of a per-mint outcome-independent warning with p < 0.05 (up, down), bound 0.0718 | T1 0.040, 0.0325; T1b 0.060, **0.0975**; T2 0.0475, 0.025 | T1 0.020, 0.0225; T1b 0.030, 0.0375; T2 0.0375, 0.005: CALIBRATION_HOLDS |

CX-S15 holds on the real data: on T1b the decision-level null rejects a per-mint bogus warning on the low side in 9.75% of salts against a level of 5%. The conservative p stays within its bound on every target. No verdict changes and the decision does not change; the addition only removes any reading of the raw decision-level p values as evidence.

## Search ledger

`../experiments/SEARCH_LEDGER.csv`: Phase 13's 3,206 rows unchanged at the head, then 33 Phase 15 rows (A_WARN on three targets as SIMPLE_ATTENTION_RULE, controls, descriptions, POST_OPENING checks, traps, 5 debug runs). N_search 118 to 121 (primary, protocol 11); rule configurations 39, so the sensitivity N_search is 160, the like-for-like of Phase 12's post-opening 127 (PI-D-066 item 4); A_WARN's Bonferroni is 1.0 at either N; holdout evaluation rows 220 (`LEDGER_TOTALS.json`). The repair pass 2 addition adds 20 rows in `../experiments/SEARCH_LEDGER_RP2_ADDITION.csv` (descriptions, POST_OPENING checks, controls, calibration checks, one debug run) under the same candidate names, so neither count changes. `../experiments/REGISTRY_LEDGER_MAP.csv` maps every registry row to its ledger row or to the record that holds it, and every ledger row to its registry row or its basis (checklist G18, skeptic m7).
