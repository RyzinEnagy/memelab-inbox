# Independent rescore (Phase 03)

The orchestrator's blind second reviewer scored the seven repositories in `BLIND_RESCORE_PACKET.md` (the lead's first-pass top five plus the 6th and 7th as controls) from a blind working copy built with `verify/make_blind_copy.sh`, without opening the lead's scores, items, order or records. Its report and scores are in `BLIND_RESCORE/PHASE_03_BLIND_RESCORE.md` and `.csv`, its reruns in `BLIND_RESCORE/reruns/`. It used its own item split of the locked rubric (written before scoring), so a criterion difference can come from a different item split as well as from a different reading of the evidence. The lead's repair pass resolved each difference by evidence: a lead score changed only where the blind reviewer cited something the lead had missed or misread, and the lead adopted the blind reviewer's split nowhere, because the lead's items are frozen (PI-D-026). Nothing was averaged.

## Totals

| Repository | Lead first pass | Lead final | Blind | Final minus blind |
|---|---:|---:|---:|---:|
| scikit-learn/scikit-learn | 51 | 51 | 58 | -7 |
| eslazarev/purged-cross-validation | 50 | 48 | 54 | -6 |
| online-ml/river | 49 | 49 | 42 | +7 |
| statsmodels/statsmodels | 49 | 49 | 43 | +6 |
| scikit-learn-contrib/MAPIE | 49 | 44 | 46 | -2 |
| soda-inria/hazardous | 48 | 43 | 32 | +11 |
| interpretml/interpret | 48 | 50 | 42 | +8 |

First-pass differences above 10 points: hazardous (+16). After the repair pass: hazardous (+11), resolved criterion by criterion below.

## Per criterion (lead final / blind / difference)

| Repository | Temporal 18 | Outcomes 14 | Calibration 12 | Features 10 | Decision 10 | Code 8 | Integration 8 | Reproducibility 8 | Cost 5 | License 7 |
|---|---|---|---|---|---|---|---|---|---|---|
| scikit-learn | 3 / 5 / -2 | 5 / 8 / -3 | 5 / 7 / -2 | 2 / 3 / -1 | 3 / 3 / 0 | 8 / 8 / 0 | 8 / 8 / 0 | 5 / 5 / 0 | 5 / 5 / 0 | 7 / 6 / +1 |
| purged-cross-validation | 9 / 14 / -5 | 0 / 3 / -3 | 0 / 0 / 0 | 3 / 1 / +2 | 2 / 4 / -2 | 8 / 7 / +1 | 8 / 8 / 0 | 6 / 6 / 0 | 5 / 5 / 0 | 7 / 6 / +1 |
| river | 5 / 6 / -1 | 5 / 7 / -2 | 0 / 2 / -2 | 3 / 4 / -1 | 5 / 2 / +3 | 7 / 4 / +3 | 8 / 5 / +3 | 4 / 4 / 0 | 5 / 4 / +1 | 7 / 4 / +3 |
| statsmodels | 3 / 1 / +2 | 5 / 7 / -2 | 2 / 3 / -1 | 2 / 2 / 0 | 5 / 2 / +3 | 8 / 7 / +1 | 8 / 6 / +2 | 4 / 4 / 0 | 5 / 5 / 0 | 7 / 6 / +1 |
| MAPIE | 0 / 3 / -3 | 0 / 3 / -3 | 7 / 8 / -1 | 0 / 0 / 0 | 6 / 6 / 0 | 7 / 6 / +1 | 8 / 7 / +1 | 4 / 3 / +1 | 5 / 4 / +1 | 7 / 6 / +1 |
| hazardous | 2 / 1 / +1 | 8 / 9 / -1 | 4 / 5 / -1 | 2 / 2 / 0 | 0 / 0 / 0 | 7 / 3 / +4 | 7 / 3 / +4 | 4 / 2 / +2 | 4 / 3 / +1 | 5 / 4 / +1 |
| interpret | 2 / 1 / +1 | 8 / 7 / +1 | 2 / 1 / +1 | 2 / 3 / -1 | 3 / 2 / +1 | 8 / 7 / +1 | 8 / 7 / +1 | 5 / 4 / +1 | 5 / 5 / 0 | 7 / 5 / +2 |

## hazardous (difference above 10): criterion by criterion

| Criterion | Lead / blind | What each side cites | Resolution |
|---|---|---|---|
| Temporal | 2 / 1 | Lead T3: censored rows kept as event 0 in the fit and in the IPCW scores (`smoke_hazardous.py`, `smoke_hazardous.result.json`). Blind: T5 1 for the recalibration on the later split; it credits the same censoring under its outcome item O6 | Same facts, different item placement. The blind's T5 point rests on `recalibrate_survival_function`, which the lead's probe shows moves the wrong way (HZ-3), so the lead does not adopt it. Lead keeps 2 |
| Outcomes | 8 / 9 | Both credit `predict_proba` at a horizon and the competing-risk fit with censoring. The blind's O2 is 2 of 3 "with a structural defect" (non-monotone curve) and adds discrimination metrics (O5) | The blind's structural-defect point was adopted and taken further: the lead's O3 (competing-risk race output) is now 0 by the verified-finding veto, because the cumulative incidence decreases in time for 634 of 634 rows (HZ-2). The lead's items have no discrimination-metric item. Lead 10 to 8 |
| Calibration | 4 / 5 | Both credit the integrated Brier and AJ-calibration. The blind gives K2 1 for a "marginal, unclipped recalibration" | The blind's caveat led the lead to probe the function: it subtracts the absolute error (`_km_calibration.py:131`), so it moves survival away from the Kaplan-Meier curve when the model under-states survival, and it leaves [0, 1] (to -0.27) in the mirror case (`verify/rerun_hazardous_recal.out.txt`, HZ-3). A definition error found means C2 0. Lead 7 to 4 |
| Features | 2 / 2 | NaN rows accepted | agree |
| Decision | 0 / 0 | no weights, no thresholds | agree |
| Code | 7 / 3 | Blind: Q2 0 for release parity (0.2.0 artifacts differ from every commit, two releases), Q3 1 for the lifelines dependency and its pandas cap, Q4 0 for the documented dict `y` that its own metric rejects and the incidence docstring | Each fact is real and each already costs the lead a point elsewhere: release parity is L4 0 and K4 0 (HZ-1), the pandas cap is I2 0, the rejected `y` and the non-monotone incidence are Q5 0 (HZ-2). The lead's Q1 (104 tests passed), Q2 (the test subset covers the metric functions; see the strict reading H in RANKED_TOP10.md, under which Q2 is 0), Q3 (commit and release dates) and Q4 (declared dependencies complete) are checked facts. Lead keeps 7 |
| Integration | 7 / 3 | Blind: I1 0 because lifelines requires `pandas<3.0` while the lab runs 3.0.5; I3 1 because a PyPI install drops 214 MB of data; I4 1 | The pandas cap is the lead's I2 (0). The 214 MB data is in the REJECTed PyPI route only; the recommended route is the pinned source, whose venv holds no data file (`hazardous/data/` holds only the loader modules `_seer.py` and `_competing_weibull.py` and tests) and whose closure is 330.9 MB (I5). I1 (runs on Python 3.13) holds. Lead keeps 7 |
| Reproducibility | 4 / 2 | Blind: R1 1 because another seed moves P by up to 0.169; R2 1 because pickle only | The lead's R1 asks for identical output with the same inputs and seed (true, HZ-2); seed sensitivity is model variance, not irreproducibility. The lead's R2 is an identical reload; the pickle format is scored separately in R3 (0). Lead keeps 4 |
| Cost | 4 / 3 | Blind L2 1: default fit 253.8 s | The lead's K2 asks whether some configuration fits the challenge in under 60 s: 14.7 s at `n_iter=10`, 19.6 s at 20 (HZ-T). Lead keeps 4 |
| License | 5 / 4 | Blind S3 0 and S4 0 for the PyPI artifacts, S5 0 for pickle | The lead's L2 0 and L4 0 cover the same artifacts; pickle is R3. The lead's L5 (no key, no service) holds. Lead keeps 5 |

Remaining difference 11: the blind's points for facts the lead's items do not score (discrimination metrics, seed variance, release cadence) and the lead's points for checked binary facts (tests passed, dates, Python 3.13, footprint, offline). Neither side cited evidence the other misread on these.

## Differences of 5 to 10 points

- scikit-learn (-7). The blind credits capabilities seen only in source: `TunedThresholdClassifierCV` (D2), `QuantileRegressor` (O3, K4), group-aware CV (O4), `FrozenEstimator` as a past-only mode (T5), custom split iterables (T2). The lead's items need these exercised in the smoke (O4, D2, T5) or refuse caller-built iterables (PI-D-026), and the lead's fold audit shows `GroupKFold` by mint training on up to 2,314 rows decided after the test start (`verify/fold_audit_purgedcv.out.txt`, `sklearn.GroupKFold`; the reviewer's smoke counted 1,834 to 1,842). No lead score changes; this is the item split, not a misread.
- purged-cross-validation (-6). The blind gives temporal 14 (adds the embargo, `evaluation_times` as a past-only rule and validation checks as chronology) and credits `PurgedGroupKFold` with 0 shared mints (O4 2). The skeptic and the lead's fold audit show that group split has training folds of 0, 0, 45, 179 and 397 rows (PC-3), so the lead removed its own O5 and does not adopt the blind's O4. The blind's PBO and refusal points are the lead's D3 and Q5. No other change.
- river (+7). The blind gives 0 or 1 for NaN-related defects in decision, code and cost items (D1, Q4, L3) and for the Rust build side effect (I3, S4), and 0 for crate licenses "not checked by anyone" (S2). The lead's NaN finding is Q5 0 and F1 0 (RV-3); the build side effect concerns building the pin, not the recommended wheel route. The lead checked the crate licenses after the blind's remark: the 34 crates in the normal closure are permissive (RV-5), so L2 stands on new evidence. The blind's LEAKAGE_FAIL for model state after a replay is adopted: `progressive_val_score` learns every answer `simulate_qa` yields, including the end-of-stream flush (`progressive_validation.py:138-155` after `qa.py:244`, RV-4). Points unchanged; flag and route changed.
- statsmodels (+6). The blind's D1 0 cites p-values down to 2.7e-23 under quasi-separation without a warning; that is the S1 trap feature (a future return that nearly determines the label), so a tiny p-value is the right inference for that design, not a library defect; the lead's D1 is the weights hook (`freq_weights`, `var_weights`). The blind credits `PHReg` and GEE from source (O2, O4); the lead's items need a smoke. The blind's I4 notes that Wilson duplicates `alpha_core.wilson`; the lead's I4 is about parallel subsystems, and Wilson is a function, not a subsystem. No change.
- interpret (+8; was +6 before the repair). The blind found a false review claim: `has_term_standard_deviations false` probed a wrong attribute name. The lead reran it (IN-5): `standard_deviations_` exists, one finite array per term, so interpret gains C5 (+2). The blind's license point (an Apache-2.0 file compiled into libebm, wheel without license metadata) is a notice obligation, now in the license gate; Apache-2.0 is permissive, so L1 and L2 stand. The blind's I4 1 (overlaps the scikit-learn baseline role) is not a parallel subsystem under the lead's I4. No other change.
- MAPIE (-2, was +3). The blind's new finding is adopted: a fitted Pipeline passed with `cv="prefit"` has its transformers refit on the calibration rows, changing the caller's predictions (blind rerun 0.01056; lead rerun 0.0176, MA-4). It joins MA-1 in the veto for O1 and Q5; the route excludes it.

## Checks the package asks for (phase prompt, item 5)

- Reviewer preference creep: in the first pass the lead's totals exceeded the reviewers' for 21 of 30 repositories (mean +2.5; after the repair pass 20 of 30, mean +2.0). The excess sits in the near-binary hygiene criteria (integration +70, code +43, license +30, decision +25, cost +19 points summed over the 30 repositories), where the lead's items award the full value for checked facts such as a permissive license, a Python 3.13 run or no telemetry and reviewers docked points for broader concerns; in the criteria that decide the T1 role the lead awards less than the reviewers (temporal -51, outcomes -36, calibration -33). The items were written after the lead had read every review, so "frozen before scoring" does not mean blind to the evidence (skeptic m9); the blind rescore and the sensitivity readings are the control for that.
- Outdated docs and copied claims: docstrings that the code contradicts were found in statsmodels (out-of-sample `predict`, SM-1), hazardous (incidence docstring and the recalibration formula, HZ-2, HZ-3) and MAPIE (Venn-Abers, MA-1); none earned a point. mlfinpy's copied code is REJECT (MF-2).
- License incompatibility: none in the top ten; the obligations (TabPFN-2 naming and display, interpret's Apache-2.0 notice) are in LICENSE_AND_SECURITY_GATE.md.
