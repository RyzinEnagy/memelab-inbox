# Phase 13 evidence: calibration, uncertainty and abstention

Status: PASS after repair pass 2 (PI-D-070), with G7 failed as registered and closed by the orchestrator's decision PI-D-071. The first-pass text below is kept as it was; the repair is in the last sections. Branch `feature/predictive-intelligence`; HEAD before `6f4f8ea`; commits listed below; HEAD after: see `PHASE_13_RESULTS.json` and HANDOFF.md. Agent session 2026-10-26 from 20:12Z.

## Entry gate (G1, G2)

| Command | Result | Exit |
|---|---|---|
| `sha256sum -c SHA256SUMS.txt` in the package folder | 41 of 41 OK | 0 |
| `python -m pytest tests -q -p no:cacheprovider` at `6f4f8ea` (20:12:29Z) | `1 failed, 1455 passed in 197.15s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` | 1 |
| strays removed by hand | `data/reports/20261026_2012_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal` | |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | `"problems": []`, the three pinned hashes | 0 |
| Phase 12 key tests `tests/test_predictive_evaluation.py tests/test_predictive_phase12_outputs.py` | `57 passed in 1.93s` | 0 |
| Phase 12 RESULTS.json status | PASS | |
| sha256 `data/memelab.sqlite`, p06 dev store, p05 store | `068287c0...`, `d2a5a7c6...`, `2525f0c4...`, equal to Phase 12's records | |

Files: `evidence/entry/entry_summary.txt`, `evidence/entry/seal_check.json`.

## Order of work (G3, G4)

| Step | Commit | Time (UTC) |
|---|---|---|
| Acceptance checklist, experiment registry (52 rows, `d73e19cf...`), PI-D-067 | `0fdf698` | 20:21:18Z |
| Debug runs of the runner on real data at uncommitted code (scratchpad), listed in the runner's DEBUG_RUNS and in the search ledger | none | 20:37:42Z, 20:38:30Z, 20:39:50Z |
| Frozen code: `calibration.py`, `abstention.py`, schema, tests, runner, oracle and mutation probes | `5a3c582` | 20:52:33Z |
| Recorded run (20:52:39Z to 20:52:49Z) and determinism twin (identical files), oracles, mutation probe 75 of 75, jsonschema check | `9cd5288` | 20:56:53Z |
| Self-review pass 2 code (PI-D-068) | `2e1488a` | 21:03:53Z |
| Recorded run repeated at `2e1488a` (21:03:54Z to 21:04:04Z): 23 of 24 output files byte-equal, `POST_OPENING_LOG.json` differs only in the code commit it names (`evidence/frozen_code_rerun_sr2.json`) | outputs and records on top | |

## Recorded commands

| Command | Result | Exit |
|---|---|---|
| `python -B probes/run_calibration.py audits/predictive-intelligence/phase_13` at `5a3c582` | `{"failures": [], "status": UNCALIBRATED x3, dev_requests 24/44/8, dev_forecasts 0, holdout_requests 66/68/59, today_decisions 10}` | 0 |
| same into the scratchpad (twin) | every file under `calibration/`, `artifacts/`, `experiments/` identical | 0 |
| same at `2e1488a` | same summary; only the code commit line of `POST_OPENING_LOG.json` and the run log changed | 0 |
| `p04_bundle/bin/python -B probes/oracle_calibration.py ... evidence/oracle_sklearn_statsmodels.json` | isotonic inside Venn-Abers 6.9e-18; Brier and log loss 1.0e-13; Wilson (statsmodels) 4.9e-13; Platt against `_sigmoid_calibration` 9.4e-6 (G7 fails as registered on T1b and T2); Platt against newton-cholesky 5.3e-15 | 1 |
| `ip200__venn-abers/bin/python -B probes/oracle_calibration.py ... evidence/oracle_venn_abers.json` | Venn-Abers p0, p1, p against ip200/venn-abers 1.5.4: 6.9e-18 on the real descriptive sets, the recorded grids and three fixtures | 1 (the same G7 sub-check also runs there) |
| `python -B probes/mutation_calibration.py evidence/mutation_calibration.json` at `9cd5288` | 75 of 75 caught | 0 |
| same, `evidence/mutation_calibration_sr2.json` after PI-D-068 | 79 of 79 caught | 0 |
| jsonschema 4.26.0 Draft 2020-12 over every written result (`evidence/schema_jsonschema_check.json`) | 76, 193 and 30 pairs, 0 errors | 0 |
| `python -m pytest tests/test_predictive_calibration.py tests/test_predictive_abstention.py tests/test_predictive_phase13_outputs.py -q` | `124 passed` (55 + 62 + 7) | 0 |
| first-pass `abstention.py` with the four self-review tests (`evidence/sr2_old_code_check.json`) | 4 failed | 1 (expected) |

Post-commit suite, guard, seal check and release audit: section "Post-commit results" (added after the commit).

## Checklist (as registered in `0fdf698`)

| Id | Result |
|---|---|
| G1 | Package 41 of 41 OK. |
| G2 | Entry gate as above. |
| G3 | Pre-registration `0fdf698` before any code or real-data fit. |
| G4 | Frozen code `5a3c582` before the recorded run; three earlier debug runs logged (DEBUG_RUNS, ledger kind DEBUG_RUN_REAL_DATA). |
| G5 | Calibration rows re-derived from the fold cards through the gate: fold card sha256 equal (3, 5, 1 folds), out-of-sample numbers equal to Phase 07's file within its 6-decimal rounding (largest 5.0e-7). The checklist said "within 1e-12": the committed file holds 6 decimals, so the comparison is to its rounding, and the fold cards themselves are equal byte for byte in model_sha. Refusals tested: at or after the cutoff, maturing after, holdout split, holdout relabelled development, in-sample, NaN, duplicate. |
| G6 | Gate and method boundaries tested (99/100, 19/20, 80/81 negatives, 4/5 days, 199/200, 39/40). |
| G7 | FAILED as registered: Platt against `_sigmoid_calibration` within 1e-6 holds on T1 and three fixtures, fails on T1b (1.5e-6) and T2 (9.4e-6) where scikit-learn's lbfgs stops early (its gradient up to 5.7e-7, the numpy fit's below 1e-15). Isotonic 6.9e-18 and Venn-Abers 6.9e-18 pass. The PI-D-053 newton-cholesky comparison (5.3e-15) was added after seeing this result. Needs a decision by the orchestrator or Elving (PI-D-069 item 6). |
| G8 | The check is `stats.calibration_bins` with the ACCEPTANCE values; constants pinned by test. |
| G9 | Width non-increasing in support (test); 30-event set with a 0.95 number gives no calibrated card; real widths in `BELOW_GATE_DESCRIPTIVE.json`. |
| G10 | 28 conditions, each with a test that triggers it alone and checks its contract reason; the codes and reasons equal the checklist's rule 12 (parsed by a test); all evaluated (test). |
| G11 | NaN, infinities, -0.1, 1.1 raw numbers abstain INVALID_PROBABILITY; the validator refuses injected NaN, inf, 1.5, -0.2, strings, None; NaN features are MISSING_REQUIRED_INPUT. |
| G12 | Flat 0.9 predictions: FLAT, calibration fails; always-negative on a 1% event: Brier skill at most 0, log loss worse, no AUC. |
| G13 | 0.9 on a 2% class: calibration fails, card UNCALIBRATED. |
| G14 | Constructed conflict flagged with both scores, counts and intervals; T2's real development rows show it too. |
| G15 | Agreement 0.9 refused in scenarios (the frozen contract alone lets `agent_agreement` through), cohort, `calibration_reference`, simulation model kind, simulation calibration source, behavioral input. |
| G16 | Token-history card on a new mint abstains INSUFFICIENT_HISTORY; a cross-sectional new-mint forecast needs COHORT_ESTIMATE_NOT_TOKEN_HISTORY. |
| G17 | A step in the loss stream alarms after the step only; later decisions abstain DRIFT_ALERT, earlier ones keep their forecast; the record file refuses a rewrite (sha chain). On real development data there are 24, 44 and 8 observations and no alarm. |
| G18 | A fixture meeting every condition publishes a FORECAST that passes `contract.validate`, `validate_publication` and the schema; each single condition turns it into ABSTAIN; tampered references, caveats, levels, intervals, base rates and support are refused. |
| G19 | Schema validates every written pair (in-house checker in the tests, jsonschema oracle 0 errors); 12 mutated documents refused by both. |
| G20 | UNCALIBRATED for all three with counts, reliability, base rates, Wilson bands, exchangeability, abstention and coverage by fold (`CALIBRATION_CARD.md`). |
| G21 | Holdout outputs are POST_OPENING: computed from committed Phase 12 files (input sha256 in `POST_OPENING_LOG.json`), combined by `conservative_status` (FAILS for all three), never fitted, selected or promoted; seal check after the run: see post-commit. |
| G22 | `TODAY_STATUS.json`: ABSTAIN for every target with the five standing reasons. |
| G23 | `SEARCH_LEDGER.csv` = Phase 12's corrected ledger (3,148 rows) plus 42 Phase 13 rows (33 DESCRIPTION_ONLY, 9 POST_OPENING_CHECK), 10 fixture rows (TRAP_OR_CHECK) and 3 debug runs: 3,203 rows; candidate configurations 87 and N_search 118 unchanged; `evaluation.rule_configurations` (distinct target and candidate pairs of OTHER_KINDS) is now 33 because the descriptive rows use DESCRIPTION_ONLY; they are descriptions, not forecasters. |
| G24 | Twin identical; 0 socket events; stores unchanged (run log); tracked `data/` untouched. |
| G25 | Mutation probe 79 of 79 at the repair commit. |
| G26 | Flag OFF (`contract.enabled()` false); no module outside the two new files imports them (test); `contract.py`, ACCEPTANCE and the fingerprint `4b4aabce...` unchanged; score and fatal flags untouched. |
| G27 | Post-commit section. |

## Iteration log (at most five passes)

1. Pass 1 (build and check): pre-registration, modules, tests; first mutation probe 67 of 75 (8 survivors), 8 tests added, 75 of 75; three debug runs (one false difference in the holdout reliability comparison, fixed in the runner); recorded run; oracle shows G7 failing as registered.
2. Pass 2 (own adversarial review, not independent, PI-D-068): four holes in the publication path (an edited calibration card with its old sha, a level that differs from the card's, a forged large support that narrows the required interval, an arbitrary base rate); fixed with four tests that fail on the first-pass module; A16's test strengthened after it survived the new code; 79 of 79; recorded run repeated, outputs byte-equal.

## Own adversarial pass (not independent)

Besides PI-D-068: (a) the development replay names CALIBRATION_EVIDENCE_PENDING at fold cutoffs before the prospective holdout existed; this follows the frozen rule that only prospective evidence is admissible and is stated, not hidden; (b) the CURRENT_VENDOR_LIST route abstains POOL_NOT_POINT_IN_TIME although Phase 12 scored those rows; this is more conservative and is a live-route question for Phase 17; (c) the holdout descriptive check maps a failed check to FAILS_SELECTION_CORRECTION so that `conservative_status` can combine it; the vocabulary is borrowed, the direction (only more conservative) is what matters; (d) the published point cannot be recomputed from the document alone (Phase 17 item).

## Counterexample CX-13 (named before building) and what catches it

Fit Platt on the 66, 68, 59 opened holdout rows, check it in the large on the same rows, publish calibrated B2 numbers. Caught by: `calibration.check_rows` (split RETROSPECTIVE_HOLDOUT refused; relabelled DEVELOPMENT refused by date), `check_evidence_rows` (only prospective, never the fit set), the fit gate, and `validate_publication` (level ABSTAIN refused). Tests: `test_cx13_platt_fitted_and_checked_on_the_spent_holdout_is_refused_at_every_step`; on the real holdout rows: `REPLAY_CHECKS.json` "traps_cx13_on_real_holdout_rows" (both refused, all three targets). The independent skeptic's counterexample is added after the review.

## Sources

No external source was read; the work uses the package, the repository and its committed outputs. Oracles: scikit-learn 1.9.1 and statsmodels 0.15.0 (`/home/claude/pi_research/venvs/p04_bundle`), ip200/venn-abers 1.5.4 (`/home/claude/pi_research/venvs/ip200__venn-abers`), jsonschema 4.26.0 (system interpreter, not a lab dependency; the tests skip that part without it). Cost: 0 (COST_LEDGER.md).

## POST_OPENING computations (logged)

Every run of the runner reads the opened holdout outcomes from committed Phase 12 files: debug runs at 20:37:42Z, 20:38:30Z, 20:39:50Z; recorded run 20:52:39Z; twin 20:52:49Z; repeat at 21:03:54Z. None fits, selects or promotes; all only describe; `POST_OPENING_LOG.json` names the inputs' sha256 and the run log the times.

## Limitations

- The publication path is TEST_ONLY (fixtures only).
- G7 failed as registered (above).
- The out-of-sample comparison with Phase 07 is to 6 decimals.
- Calibration intervals assume exchangeability, which the development data reject for some targets; no interval covers unmodelled risk.
- Prospective evidence does not exist yet (Phase 19).

## Post-commit results (at `9f95b71`)

| Command | Result | Exit |
|---|---|---|
| `python -m pytest tests -q -p no:cacheprovider` (21:09:02Z) | `1 failed, 1579 passed, 1 warning in 191.43s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` | 1 |
| strays removed by hand | `data/reports/20261026_2109_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal` | |
| `python -m memelab social guard` | 0 violations | 0 |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | `"problems": []`, the three pinned hashes (the sealed folder is unchanged) | 0 |
| `python tools/release_audit.py --history` on a single-branch clone at `9f95b71` | "Needs action: no." | 0 |
| `git status --short` | clean | 0 |

Files: `postcommit/`. The one warning is the expected RuntimeWarning of `test_a_calibrator_that_returns_a_non_finite_number_is_refused` (a NaN Platt parameter, refused).


## Repair pass 2 after the independent skeptic (PI-D-070, PI-D-071)

Review: `skeptic/PHASE_13_SKEPTIC.md` with its scripts and outputs (copied from the orchestrator's folder). Verdict: material failures, all in the TEST_ONLY publication path; the empirical result reproduced exactly (every recorded number re-derived by the skeptic's own code). Each finding was verified first: the skeptic's attack script published a probability on the first-pass code in A1 (flag OFF in the config), A2 (a 24-row card with spent holdout evidence, resealed), A2b, A2c, A3 (evidence matured after the decision), A7b (level relabelled) and CX-S13 (flat evidence: card CALIBRATED).

| Finding | Repair | Caught by |
|---|---|---|
| M1 caller-supplied flag | `evaluate` and `validate_publication` read `contract.enabled(config_path)` | `test_rp2_m1_*`; mutations R1, R2 |
| M2 self-certifying cards | `calibration.decide` recomputed by `verify_card`; spent evidence, holdout-window rows (float and text times), inconsistent counts, extra calibrator, pair counts, availability and a self-given VALIDATED_EXPERIMENTAL refused; validator evidence gate | `test_rp2_m2_*`, `test_rp2_a_card_cannot_relabel_*`, `test_rp2_a_below_gate_card_*`; mutations R3 to R12, R17, R18, E5, E6, E9, E10 |
| M3 no time binding | cards carry `evidence.as_of` and `available_at`; condition CALIBRATION_AFTER_DECISION (UNCALIBRATED); validator refuses a card available after the decision | `test_rp2_m3_*`; mutations R13, R14 |
| M4 and CX-S13 flat evidence | evidence degeneracy and score range on the card; flat evidence never passes; request scores outside the evidence range abstain | `test_rp2_m4_cx_s13_*`, `test_rp2_a_score_outside_the_calibration_bins_*`; mutations R8, R9, R15 |
| m1 Platt not pinned | regression test against an independent 60-digit decimal Newton solve (the recorded T2 set and two synthetic sets) | `test_rp2_numpy_platt_*`; the skeptic's K1, K2 now caught |
| m2 wording | Holm over six tests (smallest 0.065), first-day drop, route rates in `EXCHANGEABILITY.json`; card, PI-D-069 (amended by PI-D-070), ROADMAP and HANDOFF corrected | `evidence/rerun_rp2_diff.json` |
| m5 untested constants | tests for support ties, alpha 0.05, registry check, validator display range and support minimum, token-history minimum 20, FORECAST record with conditions | the skeptic's M5, M6, M11, M13, M14, M17, M18 now caught |
| m3, m4 | recorded for Phase 17 (recompute the point from the kept raw number; validate every document with its record) | not repairable from the document alone |
| m6 | description, unchanged | |

Commands and results:

| Command | Result | Exit |
|---|---|---|
| repair code committed | `075026d` (21:58:24Z) | |
| `python -B probes/run_calibration.py audits/predictive-intelligence/phase_13` at `075026d` | failures []; UNCALIBRATED x3; 76, 193, 30 requests all ABSTAIN | 0 |
| twin into the scratchpad | every file under `calibration/`, `artifacts/`, `experiments/` identical | 0 |
| comparison with the first-pass outputs (`evidence/rerun_rp2_diff.json`) | statuses, counts, condition codes and reasons equal for all 299 results; card sha256 changed (new fields); FLAG_OFF detail names the config; one matrix row added (0 everywhere); Holm, first-day and route-rate entries added; 8 files byte-equal | |
| `python -B probes/mutation_calibration.py evidence/mutation_calibration_rp2.json` | 104 of 104 caught; 1 equivalent mutation recorded (R16, the validator's evidence gate behind `verify_card`) | 0 |
| repair tests on the first-pass modules (`evidence/rp2_tests_on_first_pass_code.txt`) | 12 failed, 5 passed (the 5 pin behaviour that was already right: Platt accuracy, support ties, alpha, registry check, Platt synthetic). The whole test module passes `config_path`, so on the old code most failures are TypeErrors; the skeptic's own scripts on `08faa99` are the behavioural proof (attacks published, CX-S13 CALIBRATED) | 1 (expected) |
| `python -B skeptic/rp2_attacks_check.py . skeptic/rp2_attacks_check_out.json` | flag OFF: the legitimate fixture no longer publishes; flag ON (stubbed): none of the skeptic's attacks publishes | 0 |
| `python -m pytest tests/test_predictive_calibration.py tests/test_predictive_abstention.py tests/test_predictive_phase13_outputs.py -q` | `141 passed` | 0 |
| oracles | not rerun: the calibrators are unchanged and their inputs (`CALIBRATION_SETS.csv`, `BELOW_GATE_DESCRIPTIVE.json`) are byte-equal | |

G7 (PI-D-071): stays "failed as registered"; closed because the numpy Platt equals a 60-digit Newton solution within 1e-15, scikit-learn with tight tolerances converges to it, and PI-D-053 had already frozen newton-cholesky (5.3e-15 here) as the reference; the regression test above is the condition.

## Skeptic's counterexample CX-S13 and what catches it now

The phase's own fixture with every prospective evidence score set to one value: on the first-pass code the card became CALIBRATED (each bin's mean inside its Wilson interval trivially) and forecasts were published at scores the evidence never exercised. Now: `_evidence` records the evidence degeneracy and refuses a pass on flat evidence (card UNCALIBRATED, DEGENERATE_FLAT_PREDICTIONS), `verify_card` refuses any card marking flat evidence passed, and request scores outside the evidence range abstain. Caught by `tests/test_predictive_abstention.py::test_rp2_m4_cx_s13_flat_evidence_never_calibrates_and_scores_outside_the_evidence_abstain` and mutations R8, R9, R15.
