# Phase 13 independent skeptic review

Reviewer: independent skeptic (orchestrator-launched), 2026-10-26. Branch `feature/predictive-intelligence`, tip `08faa99`. Work done in my own clone `/home/claude/pi_orchestration/skeptic_13` (temp `MEMELAB_DB`), never in `/home/claude/memelab-inbox`. No network call, no Firecrawl, no vendor call.

The retrospective holdout was opened in Phase 12. Every number below that reads holdout rows (my reliability recomputation on `phase_12/validation/HOLDOUT_SCORED.csv`) is POST_OPENING description only: it fits nothing, selects nothing and supports no claim. I never read `phase_06/sealed/`.

## Verdict

Material failures found, all in the publication path (the part the phase itself marks TEST_ONLY). The empirical result reproduces exactly: all three primary targets UNCALIBRATED, every development, POST_OPENING holdout and today request ABSTAIN with named reasons, publication coverage 0%. Nothing published today is wrong. But four routes let a probability through `abstention.forecast_result` plus `abstention.validate_publication`, the functions PI-D-069 item 5 tells later phases to rely on, when the frozen rules say it must not be published. One of them (CX-S13) goes through the honest path with no forgery.

G7: the numpy Platt is correct (equal to a 60-digit Newton solution within 1e-15); scikit-learn stops early. Recommendation in the G7 section.

## Checks run

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Phase 13 tests | `python -m pytest tests/test_predictive_calibration.py tests/test_predictive_abstention.py tests/test_predictive_phase13_outputs.py -q` | 124 passed, exit 0 |
| 2 | Runner reproduces committed outputs | `python -B .../probes/run_calibration.py $W/run1` then sha256 per file | 22 of 23 files byte-equal; `POST_OPENING_LOG.json` differs only in `head_code` (08faa99 vs 2e1488a), expected. failures [] |
| 3 | Phase mutation probe | `python -B .../probes/mutation_calibration.py $W/mut.json` | 79 of 79 caught, exit 0 |
| 4 | Phase oracles | `p04_bundle` and `ip200__venn-abers` venvs, `oracle_calibration.py` | reproduces: Platt vs `_sigmoid_calibration` 9.4166e-6 (fails 1e-6), newton-cholesky 5.27e-15, isotonic 6.9e-18, Venn-Abers vs ip200 6.9e-18, exit 1 as recorded |
| 5 | Full suite | `python -m pytest tests -q` | `1 failed, 1579 passed` in 191.97 s, only `test_catalyst.py::test_dedup_corroboration_resurface_denial`; stray `data/reports/20261026_2126_BRETT_0x532f.md` removed by hand (known pattern) |
| 6 | Seal | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | `"problems": []`, exit 0 |
| 7 | Stores unchanged | sha256 | dev `d2a5a7c6...`, feature `2525f0c4...`, equal to the packet |
| 8 | Gates not moved | `git diff 0fdf698 HEAD -- ACCEPTANCE_CHECKLIST.md EXPERIMENT_REGISTRY.csv`; registry sha256 | no diff; `d73e19cf...` |
| 9 | Order of commits | `git show --stat` of 0fdf698, 5a3c582, 9cd5288, 2e1488a | pre-registration has no code; code before recorded run; repair code before rerun |
| 10 | No existing module imports the new ones; no existing module changed | grep, `git diff 6f4f8ea HEAD --stat -- memelab/` | only the two new files |
| 11 | Flag in this checkout | `contract.enabled()` | False (no `data/config.json`) |
| 12 | Independent recomputation | `p13_independent.py` (below) | see re-derived numbers |
| 13 | Publication attacks | `p13_publication_attacks.py` | see findings |
| 14 | G7 convergence | `p13_g7_platt_convergence.py` (p04_bundle venv) | see G7 |
| 15 | My own mutations | `p13_skeptic_mutations.py` | 21 applied, 12 caught, 9 survived |
| 16 | Abstention matrix recount from records; every committed document ABSTAIN with FLAG_OFF and UNCALIBRATED, reasons equal to its record | inline script | 0 mismatches over 76 + 193 records; 299 documents OK |

## Re-derived numbers (my own code)

`p13_independent.py`, output `p13_independent_out.json`.

1. Reliability and coverage table (`calibration/RELIABILITY_COVERAGE.csv`), development out-of-sample raw B2 from `CALIBRATION_SETS.csv`, my Wilson and my quantile binning: T1 24/8, mean 0.230235, Wilson [0.179722, 0.532937], ok; T1b 44/3, two bins; T2 8/1. Counts, positives, ok flags and bin counts equal; largest numeric difference 4.5e-13 (the table rounds to 12 decimals).
2. POST_OPENING only: holdout raw B2 reliability from Phase 12's committed file: T1 66/15 ok (3 bins ok), T1b 68/12 fails in the large (bins 0 and 1 fail), T2 59/7 ok; equal to the table, difference 3.8e-13.
3. Chronology: every calibration row decided before H, matured by H, scored by a card with cutoff at or before its decision, split DEVELOPMENT (0 violations); fold calibration card counts equal to my counts at every fold cutoff (T1 0/0, 0/0, 11/4; T1b 0, 8/1, 19/2, 27/2, 34/3; T2 0). Calibrators are fitted only on time-ordered calibration folds.
4. Base rate: Wilson equal to the table to 1e-9 (T1 [0.184772, 0.328963], T1b [0.080452, 0.164637], T2 [0.152224, 0.291568]); my own day-block bootstrap (different RNG) [0.1856, 0.3333], [0.0756, 0.1905], [0.0935, 0.3056] against [0.1869, 0.3333], [0.0755, 0.1915], [0.0952, 0.3056].
5. Exchangeability permutation p (100,000 permutations, my code): days T1 0.2528, T1b 0.0217, T2 0.0198; route T1 0.0213, T1b 0.0104, T2 0.1498. Table: 0.249, 0.023, 0.020; 0.021, 0.011, 0.152. Reproduces.
6. Platt parameters: equal to a 60-digit decimal Newton solution (G7 section).

## G7 judgment

Facts, from `p13_g7_platt_convergence.py` (`p13_g7_platt_convergence_out.json`):

| Set | numpy Platt vs 60-digit truth | sklearn options (gtol 1e-6) vs truth | L-BFGS gtol 1e-13, ftol 0 vs truth | trust-exact vs truth |
|---|---|---|---|---|
| T1 (24) | 9.7e-16 | 1.14e-7 | 2.8e-11 | 2.2e-15 |
| T1b (44) | 0 | 1.50e-6 | 1.8e-11 | 1.2e-14 |
| T2 (8) | 5.6e-17 | 9.42e-6 | 2.1e-8 | 2.2e-10 |
| synthetic n 30 | 0 | 4.4e-7 | 5.1e-11 | 6.4e-8 |
| synthetic n 500 | 3.6e-15 | 3.4e-8 | 1.8e-10 | 2.2e-13 |

My scipy call with scikit-learn's own options reproduces `_sigmoid_calibration` to 4e-15, so the 1.5e-6 and 9.4e-6 gaps are scikit-learn's stopping rule (gradient 3.7e-8 and 5.7e-7 there), not a numpy error. Tightening the same L-BFGS moves it to within 2e-8 of the numpy answer (its line search limits it on the flat T2 surface); an exact solve agrees within 1e-15.

Decision recommendation: the implementation is correct. The post-hoc newton-cholesky comparison is acceptable as recorded change control, for a reason the phase records understate: PI-D-053 had already frozen, before Phase 13, "scikit-learn LogisticRegression with solver newton-cholesky as the reference, coefficient tolerance 1e-9" for every later phase. Phase 13's pre-registration registered a different, weaker oracle (`_sigmoid_calibration`, 1e-6) contrary to that frozen rule; the newton-cholesky check is the already-binding rule, not an invention after the result. G7 should stay worded "failed as registered" in the records (do not rewrite it) and be closed by an orchestrator decision citing PI-D-053, with no effect on status, because no output, status or decision uses a Platt fit (all three cards are below the gate). Condition I would attach: the suite currently cannot detect a broken Platt solver (my mutations K1, tolerance 1e-12 to 1e-2, and K2, one Newton step, both survive all Phase 13 tests and `test_predictive_stats.py`); add a test pinning the numpy Platt on fixed data to a newton-cholesky or decimal reference within 1e-9 before any phase relies on PLATT.

## Findings

### MATERIAL (publication path; none changes today's ABSTAIN result)

M1. The feature flag is not enforced by the layer. `abstention.evaluate` raises FLAG_OFF only from the caller-supplied `req["flag_on"]`; `validate_publication` never reads `contract.enabled()`. With the flag OFF in this checkout (`enabled()` False), the phase's own fixture produces a FORECAST that the validator accepts (attack A1, probability 0.2045). Pre-registration rule 6 requires "flag ON"; the G10 test for FLAG_OFF only flips the request field, and the probe mutation A1 tests the same thing. A later phase that sets `flag_on=True` by default publishes with the flag off. Repair: `evaluate` reads `contract.enabled(config_path)` itself (config path injectable for tests) and `validate_publication` refuses any FORECAST while the flag is OFF.

M2. Calibration cards are self-certifying. `verify_card` checks the self-hash, version, registry, source, "CALIBRATED needs a calibrator and evidence.passed" and the publishable flag. It does not recompute the fit gate from `calibration_set` counts, the method rule, the evidence gate per class, the evidence split or source, or the row-date window. Attack A2: the below-gate 24-row fixture card with `fit_gate.passed` set True while `fit_gate.shortfalls` still lists "events 24 < 100", a Platt calibrator added, evidence `{"source": "RETROSPECTIVE_HOLDOUT", "n": 66, "k": 15, "passed": true}`, level SHADOW, `card_sha` recomputed: accepted by `verify_card`, `forecast_result` returns FORECAST 0.385, `validate_publication` returns []. This is CX-13 (a calibrator "checked" on the spent holdout) arriving as a card instead of as rows. A2c: a card whose `calibration_set` says its rows are in the holdout window publishes. A2b: a hand-built document on a card with evidence k = 2 (below 10 per class) passes the validator (only `evaluate` catches it). PI-D-022's "numbers match a stored evaluation" is met only against whatever card the caller hands in. Full authenticity needs the Phase 16 registry, but internal consistency is in scope now. Repair: `verify_card` recomputes `fit_gate`, `method_rule.chosen`, `evidence_gate`, `status`, `details` and `publishable` from the card's own counts and refuses any disagreement; evidence source must be the prospective holdout; `calibration_set.last_decision_utc` before the holdout start; `validate_publication` applies `evidence_gate` too.

M3. No time binding between the calibration card and the decision. Neither `evaluate` nor `validate_publication` compares the calibration card's `cutoff` or its evidence maturity with the decision time, and the card does not even store the evidence as-of time (`_evidence` drops `evidence["cutoff"]`). Attack A3: a request decided 2026-10-24T12:00Z uses a card whose evidence matured at 2026-10-29T00:00Z (P0 + 5 days): FORECAST, validator []. In any replay (Phase 17 backfill, Phase 19 prospective replay) a CALIBRATED status learned after the decision is applied to it; the calibration analogue of MODEL_TRAINED_AFTER_DECISION is missing. Repair: store `evidence_as_of` in the card and refuse (abstain, mapped to an existing reason such as MODEL_NOT_SELECTED or UNCALIBRATED) when `cutoff` or `evidence_as_of` is after the decision.

M4. Pre-registration rule 8 is enforced on the calibration set only. Rule 8 at `0fdf698`: "FLAT when max minus min of the predictions is at most 1e-9 (calibration set, evidence or a fixture stream): UNCALIBRATED, detail DEGENERATE_FLAT_PREDICTIONS." `build_card` checks `degeneracy` of the calibration rows; `_evidence` never checks the evidence scores. See CX-S13: a flat prospective evidence stream passes the frozen check trivially and the card becomes CALIBRATED. No test or probe mutation covers it (E6 mutates the calibration-set branch only).

### MINOR

m1. G7 as above: implementation correct; Platt accuracy not pinned by any test (K1, K2 survive).

m2. The "event rate not stable" finding is overstated. The raw p-values reproduce, but: (a) six tests, no multiplicity correction; Holm over the six gives 0.062 at best, none below 0.05; (b) the T1b day rejection is driven by one day, 2026-10-07 (16 distinct mints, 7 positive; T1b without that day p 0.95), and disappears under a mint-cluster permutation (p 0.15; 28 of 104 mints have more than one row); T2 survives the cluster permutation (p 0.014) but not dropping that day (p 0.19); (c) the route effect is the CURRENT_VENDOR_LIST rows having very low event rates (T1 3/34, T1b 2/65 against 31/102, 24/159), a label-route effect, not a time trend (both routes span every day). `CALIBRATION_CARD.md` says the assumption is one "the data contradicts" and "a regime or batch change moves the event rate by more than the iid interval admits". Suggested wording: heterogeneity suggested, not significant after correction, driven by the first day and the label route. The direction is conservative, so MINOR; it should not become a premise for later phases (for example a regime claim in Phase 16).

m3. A forged point is undetectable inside a wide enough interval (A5b: probability moved from 0.2045 to 0.4764, the interval edge, validator []). Already recorded as open for Phase 17 (PI-D-068); confirmed.

m4. Dropped abstention reasons cannot be detected without the original record: a document with reasons cut and no record, or with a record cut and resealed, passes (A8); the validator never re-runs `evaluate`. The append-only record file limits this once written.

m5. Validator checks and constants that no test pins (my mutations surviving): M5 support ties to the upper bin, M6 exchangeability alpha 0.05 to 0.01, M11 registry check in `verify_card` off, M13 validator display-range check dropped (only `evaluate`'s POINT_OUTSIDE_DISPLAY_RANGE is tested), M14 validator support minimum 20 to 1, M17 token-history minimum 20 to 1, M18 "FORECAST whose record lists conditions" check off.

m6. Interval granularity: support is a whole quantile bin (at least 20 rows, at least n/5 once the fit gate holds), so a score at the edge of the calibration range gets the bin's Wilson width, not the local density. Widening with smaller support holds (width at rate 0.25: n 20 0.357, 40 0.260, 80 0.187, 160 0.133, 320 0.095, 640 0.082) and the hull includes a far-off Platt point (0.95 with a 10/25 bin gives [0.234, 0.95]). P24 small sets abstain through the fit gate. Description, not a defect.

### Confirmed, no issue

Non-finite and out-of-range probabilities, intervals and base rates are refused (NaN, numpy NaN, inf, -0.1, 1.1, True, "0.5", 0.001, NaN interval, NaN base rate); stale model refused by `contract.validate`; SHADOW caveat removal refused; calibration rows chronologically valid; outputs reproduce; holdout use is description only and combined through `conservative_status` (all three POST_OPENING states FAILS, never SURVIVES).

## Counterexample CX-S13 (new): flat evidence makes a card CALIBRATED

Script `p13_cx_s13_flat_evidence.py`, output `p13_cx_s13_flat_evidence_out.json`. Built on the phase's own `world()` fixture: a B2 card trained at H, 300 development out-of-sample rows (not flat: ptp 0.92, sd 0.22), and 120 prospective evidence rows. I set every evidence score to one value (the calibration-set median), as a broken upstream input would. `build_card` returns status CALIBRATED, details [], `evidence.passed` true: the in-the-large check passes and all five quantile bins have the same mean prediction 0.3077, each within its Wilson interval. Forecasts are then published at raw scores the evidence never exercised: 0.1138 to 0.111 [0.036, 0.181], 0.6755 to 0.677 [0.558, 0.787], each with `validate_publication` []. Nothing catches it: no test, no probe mutation, no validator check. A one-line evidence degeneracy check in `_evidence` (shown as a monkeypatch in the script) turns the card UNCALIBRATED with CALIBRATION_CHECK_FAILED; per rule 8 the detail should be DEGENERATE_FLAT_PREDICTIONS. A NEAR_FLAT evidence stream (sd below 0.005) would also pass and deserves at least the descriptive flag on the card.

## Files

- `/home/claude/pi_orchestration/skeptic/PHASE_13_SKEPTIC.md` (this review)
- `/home/claude/pi_orchestration/skeptic/p13_independent.py`, `p13_independent_out.json`
- `/home/claude/pi_orchestration/skeptic/p13_publication_attacks.py`, `p13_publication_attacks_out.json`
- `/home/claude/pi_orchestration/skeptic/p13_g7_platt_convergence.py`, `p13_g7_platt_convergence_out.json`
- `/home/claude/pi_orchestration/skeptic/p13_skeptic_mutations.py`, `p13_skeptic_mutations_out.json`
- `/home/claude/pi_orchestration/skeptic/p13_cx_s13_flat_evidence.py`, `p13_cx_s13_flat_evidence_out.json`
- Run outputs: `/home/claude/pi_orchestration/skeptic_13_work/` (run1, mut.json, suite.log, seal.log, or1.json, or2.json)
