# Phase 12 acceptance checklist and pre-registration (written before any Phase 12 code, any holdout prediction and the opening of the seal)

Written 2026-10-26 from 16:40Z by the Phase 12 agent, after the entry gate at `63076ad` (suite `1 failed, 1398 passed in 251.15s`, exit 1, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; strays `data/reports/20261026_1630_BRETT_0x532f.md`, `data/memelab.sqlite-shm` and `-wal` removed by hand; `check_seal.py` exit 0 with `"problems": []` and the three pinned hashes; Phase 11's key check `verify_trace_analog.py` exit 0 with 0 differences; Phase 11 RESULTS.json PASS; tracked `data/memelab.sqlite` sha256 `068287c0...` unchanged; both private stores equal to the sha256 in Phase 11's run log), after reading the package (checksums OK), the phase prompt, ADVERSARIAL_SCENARIOS, DATA_TIME_CONTRACT, SCIENTIFIC_VALIDATION, every PI-D entry (PI-D-001 to PI-D-063), ROADMAP's known constraints, the Phase 06 to 11 deliverables and `memelab/predictive/*.py`. This file, `experiments/EXPERIMENT_REGISTRY.csv`, `validation/WALK_FORWARD_PROTOCOL.md` (the frozen evaluation plan) and PI-D-064 are committed before any Phase 12 code is written (PI-D-045 item 5).

What was looked at before writing it is listed at the top of the protocol. No holdout label was read.

## Status rules carried in

- Phase 12 is the only phase allowed to open `phase_06/sealed/`, once, after `check_seal.py` passes (PI-D-041). Development labels still come only through `labels.training_labels` (NC1 refits). Holdout labels come only through the new opening function, which reads the one sealed label file and nothing else in the folder.
- Phase 06's frozen 48 h re-read passed (PI-D-059): cards and numbers may state that the frozen revision check passed.
- No refit, tuning or selection after any holdout outcome is seen. Every holdout prediction is computed and committed before the opening.
- Verdicts use Phase 07's frozen functions (`baselines.evaluate`, `verdict`, `evaluation_gate`, `nc1_verdict`) unchanged; the only renaming is SKILL_INDICATED_DEVELOPMENT_ONLY to SKILL_INDICATED_RETROSPECTIVE_HOLDOUT on holdout rows.
- No vendor, crawler, Firecrawl or language-model call; 0 network calls (audit hook). The prospective holdout (from 2026-10-24) is not scored.
- numpy-only core in `memelab/predictive/` (flag OFF, imported by no existing module); scikit-learn only as an oracle in the research venv.

## Deliverables

`validation/WALK_FORWARD_PROTOCOL.md` (this plan plus the protocol), `validation/FULL_EXPERIMENT_LEDGER.csv`, `validation/FINAL_HOLDOUT_RESULTS.md`, the run scripts (`probes/run_holdout.py` with `plan`, `predict`, `open`), model SHAs (`validation/CANDIDATES.json`), `validation/PREOPEN_MANIFEST.json`, `validation/OPENING_LOG.json`, `validation/REPLAY_AUDIT.json`, the metric, calibration, shift and control tables, `memelab/predictive/evaluation.py`, `tests/test_predictive_evaluation.py`, evidence, RESULTS.json, SKEPTIC_PACKET.md, records.

## Checklist

| Id | Check | How it is verified | Fails if |
|---|---|---|---|
| G1 | Package unchanged | `sha256sum -c SHA256SUMS.txt` | a line not OK |
| G2 | Entry gate | suite at `63076ad`, `check_seal.py`, Phase 11 trace verifier | anything but the known failure, a seal problem, a trace difference |
| G3 | Pre-registration first | this file, the registry, the protocol and PI-D-064 committed before the first Phase 12 code commit | code or a prediction before the commit |
| G4 | Frozen code before the recorded runs | `evaluation.py`, tests and runner committed before `plan` and `predict` run on real data | a recorded run from uncommitted code |
| G5 | Candidates and cards | 69 cards loaded through their family's `loads` (sha refused on mismatch); every card cutoff = H, last training decision before H, last training maturity at or before H; `CANDIDATES.json` with path, file sha256, model sha | a card refused or out of time |
| G6 | Champion rule before the opening | `evaluation.champion` on the committed development metric files gives the champion per target, written to `CANDIDATES.json` before any prediction | a champion chosen after a holdout outcome |
| G7 | Ledger totals | `evaluation.ledger_totals` reproduces 2,896 rows, 87 candidate configurations, 31 bake-off configurations, 306 controls, 15 debug runs, N_search 118 | a different count |
| G8 | Predictions before the opening | every card and NC1 seed predicted on every Solana holdout decision without any label; files and their sha256 committed in `PREOPEN_MANIFEST.json` before the opening; two prediction runs identical | a prediction computed or changed after the opening |
| G9 | Seal check and pins | `check_seal.py` exit 0, `"problems": []`, the three hashes equal the DECISIONS pins and `evaluation.SEAL_PINS`; the label file sha256 checked on the bytes read | any mismatch |
| G10 | Opening once, logged | `OPENING_LOG.json` written before the label bytes are decompressed (time, HEAD, hashes, manifest); the opener refuses when the log exists unless the call is a logged REPRODUCTION | a second unlogged opening |
| G11 | Holdout set | split recomputed HOLDOUT, LABELED, uncensored, label 0 or 1, versions equal, identity join to the decision's own feature row, the two contacted decisions excluded and the row flag agreeing; PENDING and censored counted, never scored (P05) | a pending, censored, contacted or mismatched row scored |
| G12 | Primary result | champion against B0 per target with Brier, BSS, day and mint intervals (20,000 replicates), Holm across three, frozen verdict, log loss, AUC and AP where defined, calibration bins with counts, coverage and abstention, prevalence and Wilson interval, against the minimums 50 and 10 per class | a missing item or a claim under the minimums |
| G13 | Secondary family and selection correction | every fitted card against B0 and B2; Holm, max-T and full-search Bonferroni columns | a missing correction |
| G14 | Negative controls | NC1 (20 seeds, `nc1_verdict`), NC2 refused on every row and family, NC3 refused on every same-symbol row | a trap accepted |
| G15 | Replay discipline | `REPLAY_AUDIT.json`: every development OOS row of Phases 07 to 11 from a fold cutoff at or before its decision; every holdout prediction from cutoff H, not stale; P13 traps raise RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF | a later-trained model on an earlier decision |
| G16 | Sensitivities and dataset shift | the views and breakdowns of protocol 9 with the frozen verdict code; T2 rows carry the PI-D-045 note | a missing view or note |
| G17 | Empirical validity apart from engineering validation | `FINAL_HOLDOUT_RESULTS.md` states the two separately; no promotion; baseline-or-abstain if no reliable value | a promotion or an edge claim |
| G18 | Oracle | scikit-learn `brier_score_loss`, `log_loss`, `roc_auc_score`, `average_precision_score` on the scored holdout rows agree with the module within 1e-12 | a difference |
| G19 | Determinism and isolation | two `predict` runs identical; a REPRODUCTION of the opening run gives identical metric files; 0 network calls; stores and tracked `data/` unchanged; sealed folder unchanged (seal check after) | any difference or write |
| G20 | Tests and mutation probe | tests for the opening (refusals), the holdout filter, the replay guard, the champion rule, the max-T correction, the ledger totals, the verdict renaming; a mutation probe at HEAD catches every listed mutation | an untested rule or a surviving mutation |
| G21 | Full experiment ledger | `FULL_EXPERIMENT_LEDGER.csv` = Phase 11's cumulative ledger plus every Phase 12 evaluation, control, trap, sensitivity, breakdown and run | an unlogged evaluation |
| G22 | Flag, imports, registry | flag OFF; no existing module imports `evaluation`; registry fingerprint `4b4aabce...` and ACCEPTANCE unchanged; score and fatal flags unchanged | a change |
| G23 | Suite, guard and audits after the commit | full suite (no new failure), `python -m memelab social guard`, `check_seal.py`, single-branch `python tools/release_audit.py --history`; `git status` clean | any new failure |

## Counterexample CX-12 (named before building)

A plausible wrong design scores the holdout with the cards and only then writes down which card is "the champion" (or quietly reports the best of the 63 fitted cards as the result). On 63 candidates even with no real skill the best holdout BSS is expected to look positive. Caught by: the champion and every prediction committed before the opening (`PREOPEN_MANIFEST.json`, checked by the opener), the opener refusing a second opening, and the max-T and full-search corrections on every secondary result; a test shows that a synthetic best-of-63 with no skill gets an uncorrected one-sided p below 0.05 in many draws while its max-T adjusted p does not.

## Expected result, stated in advance

Not distinguishable from the base rate, or INSUFFICIENT_EVENTS for at least one target (Phase 01). The gate is met by the protected, logged, single opening, exact reproducibility and the replay discipline, whatever the numbers say.
