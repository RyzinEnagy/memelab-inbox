# Phase 20 independent skeptic review

Reviewer: orchestrator's independent skeptic (PI-D-013), 2026-11-09. Branch `feature/predictive-intelligence` at `b4d4768` (Phase 20 content at `0b24539`, CP20-1 code `5ebce8a`, frozen audit code `0d66379`). Own clone `/home/claude/pi_orchestration/skeptic_20` and a scratch worktree for mutations; every lab command under `unshare -n` with a temp `MEMELAB_DB`; no vendor call, no Firecrawl, nothing written in `/home/claude/memelab-inbox` (read-only `git log`/`git show` there for the origin/main exports).

Scripts and outputs next to this file: `p20_mutations.py` (+ `_out.json`), `p20_cp20_attacks.py` (CP20-1 attacks and CX-SK20), `p20_own_recompute.py` (+ `_out.json`).

## Verdict

Material failures found (3). The audit's machinery is real: its checks fail when the code under test is broken (14 of 17 mutations killed, the 3 survivors explained), the recalculation reproduces with my own code, flag-off identity, release_e2e, smoke, release audit and the suite reproduce at `b4d4768`, and CP20-1 was written before its code. But the audit missed a new variant of the Phase 18 CX-SK18 defect (and states the opposite in F20-01), the F20-02 repair can be bypassed through the pool field with the same outcome F20-02 described, and F20-01 is classed MINOR although the same defect was MATERIAL in Phase 18. Phase 20 should stay NEEDS_REVIEW until these are repaired or explicitly accepted.

## Checks run

| # | Check | Command (from the clone or worktree) | Result |
|---|---|---|---|
| 1 | All 48 own checks at HEAD | `unshare -n python -B .../probes/scenarios.py Pxx` for P01..P48 | 48 exit 0; 229 gating assertions, all pass; 3 probe assertions fail (P41, P44, P46), as recorded |
| 2 | Mutations of the system under test | `python3 -B p20_mutations.py WORKTREE p20_mutations_out.json` | 14 of 17 killed (see below); git status clean after |
| 3 | Survivors against all 48 checks | each survivor mutant, all 48 probes | M09, M10, M16 survive all 48; M09 and M10 caught by `test_predictive_integration.py` (g19 tests), M16 equivalent (second maturity check in `features.validate_rows`) |
| 4 | P05 vacuity | double mutant: `fit_all` maturity check and `features.validate_rows` maturity raise both removed | P05 and P43 still exit 0; P05's assertion raises `AsOfError: ... available_at missing`, an availability error, not maturity; `test_predictive_baselines` and `test_predictive_asof_features` do fail (2 tests) |
| 5 | CP20-1 ordering | `git log`, `git show 67acbc3:docs/.../DECISIONS.md` | PI-D-110 committed in `67acbc3` (13:43:01-04:00), code in `5ebce8a` (13:59:07-04:00); PI-D-110 text unchanged since |
| 6 | Old-code check | worktree at `0d66379` + current cross tests | 12 failed, 12 passed, 2 xfailed (matches `repair/OLD_CODE_CHECK.txt`) |
| 7 | Cross tests at HEAD | `pytest tests/test_predictive_phase20_cross.py -rxX` | 24 passed, 2 xfailed (F20-04) |
| 8 | Counterexample rerun | `unshare -n sh -c "lo_up.py && cx_rerun.py OUT"` | 39 of 39 caught, 85 passed; without loopback 37 of 39 (CX-14, CX-S14 report "not caught" because the Phase 14 tests need loopback, F20-11) |
| 9 | CP20-1 attacks | `pytest -rfE p20_cp20_attacks.py` | 4 defeats (A1 x3, A2), 12 refused (case variant, missing mint column, 8 bad capture times, numpy capture time accepted, capture time 10 days before observation gives no number) |
| 10 | Own label recompute | `python3 -I -B p20_own_recompute.py CLONE OUT /home/claude/memelab-inbox` (own parser and target rules, no lab or probe import) | 61 of 61 Phase 19 LABELED outcomes equal (19 INVALIDATION_FIRST, 18 NEITHER, 12 NO_SEVERE_EVENT, 8 TARGET_FIRST, 3 DRAWDOWN_50, 1 NO_TRADES_AFTER_ENTRY); identity and body sha ok on all |
| 11 | Own B2 recompute | same script, 12 decisions by a different sample rule (sha256 order) | 36 of 36 B2 numbers equal, max abs difference 2.1e-10 (card JSON rounding); my first pass differed on T1b only because I had left out the card's missing-value indicator, my bug |
| 12 | Flag-off identity | `flag_off_identity.sh <sha of HEAD> OUT` + summary | 24 runs, 12 of 12 identical, frozen runs at `b4d4768`, malformed config exits 1 in base and frozen alike |
| 13 | Flag-off with the packet's literal command | `flag_off_identity.sh HEAD OUT` | all_identical true, but every "frozen" run is at `b0fad12` (finding S20-4) |
| 14 | e2e | `e2e.sh <sha of HEAD> OUT` | release_e2e ok, 78 of 78 stages; smoke exit 0, flag-off reports byte-equal; single-branch clone (3 refs) release audit exit 0, "Needs action: no." |
| 15 | Full suite (post-commit check) | `python -m pytest tests -q -p no:cacheprovider` | `2 failed, 2224 passed, 1 skipped, 2 xfailed` in 241 s; the 2 known clock-dependent failures; stray `data/reports/20261109_2108_BRETT_0x532f.md` removed by hand |
| 16 | Claims grep | `grep -rnoiE "edge|skill|profit|calibrated|validated|predicts"` over `docs/predictive-intelligence/*.md`, `README.md` (no phase README exists) | no overstated claim found; every skill number is labelled descriptive, INSUFFICIENT_* or NOT_A_CLAIM; "a validated forecast" in ROADMAP row 18 is a watermarked format-only fixture |

### Mutation results (system under test mutated, audit code untouched)

| Mutation | Checks | Result |
|---|---|---|
| M01 reference candle ignores the provider lag | P06 | killed |
| M02 path keeps the candle holding t_entry | P06 | killed |
| M03 label_state always MATURED | P05 | killed |
| M04 new-mint caveat not required | P12 | killed |
| M05 degeneracy never flat | P11 | killed |
| M06 minority note never flags a constant | P10, P11 | killed |
| M07 cost cap not enforced | P48 | killed |
| M08 vendor body identity check off | P01 | killed |
| M09 MODEL_STALE removed from status_at | all 48 | survives every scenario check; caught by an existing integration test |
| M10 DRIFT_ALERT removed from status_at | P39 (all 48) | survives (abstention's own drift check masks it); caught by existing integration tests |
| M11 report text trading-word check off | P41, P44 | killed |
| M12 CP20-1 training_after_cutoff off | P05, P43, cross x06 | killed by x06 only |
| M13 CP20-1 token identity check off | P01, cross x02 | killed by x02 only |
| M14 CP20-1 capture time check off | cross x03 | killed |
| M15 CP20-1 recompute_point off | cross carried | killed |
| M16 fit_all maturity check off | P05, P43 (all 48) | survives; equivalent mutant (features.validate_rows checks maturity too) |
| M17 snapshot dedup off | P35 | killed |

So the scenario checks are real tests, not tautologies, for the mutated behaviours. The weak spots are listed as findings S20-5 and S20-6.

## Findings

### MATERIAL

**S20-1 (new counterexample CX-SK20): a run-together multiplier symbol is printed in the Phase 18 report, its alert and the Phase 17 section.** `reports._MULTIPLIER` is `(?<![0-9a-z])\d+\s*x(?![0-9a-z])|...`, so a multiplier followed by letters passes: `RP._token_text` returns `100XGAIN`, `1000XGEM`, `GAIN100X`, `10XPLAY`, `100XCOIN` unchanged (it withholds `100X`, `MOON100X`, `PUMP100X` only because of the bounded form or a trading word), and `integration._ident` passes all of them. `p20_cp20_attacks.py::test_cx_sk20_...` renders `## 1000XGEM \`solana:...\``, `| 100XGAIN | ... | CANNOT_EXIT_5K | FRESH |` in the report and the dry-run alert line `100XGAIN on solana (...)` under a risk override, and the scout section prints `100XGAIN`. This is the CX-SK18 class the Phase 18 skeptic rated MATERIAL (a gain or trade claim printed as token text). Nothing in Phase 20 catches it: P41 only tries `SELLNOW` in the scout section, P44's probe only tries spaced report text. Worse, F20-01 states the report's `_token_text` withholds `100XGAIN`, and F20-05 says token text "already passes the multiplier rule"; both statements are false for this form. Fix: withhold any `\d+\s*x` or `x\s*\d+` run not part of a `0x` hex address in both `_ident` and `_token_text`, and add the run-together cases to the tests.

**S20-2: the F20-02 repair is bypassed through the pool field.** CP20-1 compares only the token row's `mint` and `chain`. A replayed token row that keeps the decision's own mint but names another token's pool (`primary_pool = POOL2`) passes: POOL2 is read through the reader, recorded as the decision's pool, and the fixture champion publishes a FORECAST (`p20_cp20_attacks.py::test_a2_...`: event DISCOVERY, completed_forecasts 1, reads `[POOL2]`). That is the exact outcome F20-02 described (another token's pool read and recorded as this decision's), and worse, a number is published because the model inputs come from the right token. Nothing in `integration` checks that a pool belongs to the mint; it is left to the caller-supplied reader (no real reader or champion exists, so it is latent, as F20-02 was). Under the audit's own classification of F20-02 this residual is MATERIAL; at minimum the "REPAIRED" outcome must be narrowed to "token-row identity only" with an explicit acceptance, or the reader contract must return the pool's base-token identity and `_eligibility` must refuse a mismatch.

**S20-3: F20-01 is under-classified.** The Phase 18 skeptic's MATERIAL finding 4 (CX-SK18) named `integration._ident` as the helper that lets `SELLNOW` through; Phase 18 repaired only the report. Phase 20 finds the unrepaired remainder in the same helper and classes it MINOR (the lab body prints the symbol anyway). PI-D-109 requires a MATERIAL finding to be repaired or accepted by the orchestrator or Elving before Phase 20 passes; classing it MINOR skips that step. It should be MATERIAL (and fixed with S20-1), or accepted explicitly.

### MINOR

- **S20-4 (tooling, misleading packet):** `flag_off_identity.sh HEAD OUT`, the command in `SKEPTIC_PACKET.md`, resolves `HEAD` inside the sandbox after `git checkout b0fad12`, so every "frozen" run is `b0fad12` and the comparison is base against base (24 runs, all_identical true, `runs.txt` shows `commit b0fad12` on every frozen line). The recorded runs used `0d66379` and `5ebce8a`, so the evidence holds. Fix: `git rev-parse` the argument in the checkout before cloning, and have `flag_off_summary.py` fail when the frozen commit equals the base or differs from the one requested. Phase 21's runbook must not copy the packet command.
- **S20-5 (vacuous assertion):** P05's "fit_all refuses training rows maturing after the cutoff" uses `raises(..., Exception)`; it passes on `AsOfError: ... available_at missing` (the rows have no availability times). With both maturity checks removed P05 still exits 0. The same broad form is used once more in P43. Existing mapped tests do catch the double mutant.
- **S20-6 (assertions that test no code):** P10 "an always-zero forecast is worse than the base rate in Brier" is numpy arithmetic on the probe's own arrays; P43 "prospective label rows never reach the training gate" is `hasattr` on a test name. Both count among the 229 gating assertions.
- **S20-7 (coverage):** no scenario check catches the removal of MODEL_STALE (M09) or of the registry's DRIFT_ALERT (M10, masked by abstention's drift check). Existing integration tests catch both; the scenario matrix's claim of an own check per behaviour should say these rest on mapped tests.
- **S20-8 (CP20-1 fails open):** `registry.training_after_cutoff` and `evaluation.check_card_time` return no problem when a card records `max_train_decision_time` and `max_train_label_matures_at` as None. A fixture card trained on labels maturing five days after its cutoff, with those two fields set to None, is pinned and publishes a FORECAST (`test_a1_*`, 3 tests). 0 of the 69 committed entries have None (scan of the entries), so no real path; recommend refusing a fitted card with `n_train > 0` and either field missing.
- **S20-9 (stale deferral):** F20-04 stays OPEN "until after G25"; G25 ran on 2026-10-29 (PI-D-112). The stated reason has lapsed: repair it now or record an acceptance.
- **S20-10 (records):** G14 says "post-commit checks recorded" in `postcommit/`; no `phase_20/postcommit/` exists, `head_after` in `PHASE_20_RESULTS.json` is prose, not a hash, and no post-commit record commit follows `0b24539`. My own post-commit run is check 15 above.
- **S20-11 (records):** the `unpatched_severity` column of `qa/SCENARIO_MATRIX.csv` is empty for all 48 rows, including P41, P44 and P46 with probe findings; the phase prompt requires it.
- **S20-12 (counts):** of the "168 reference numbers recomputed", 84 are the B0 constant read from the same card file on both sides; the independent content is 84 B2 numbers and 28 decision keys. Of the "12 repair tests that fail at `0d66379`", two X06 tests fail by AttributeError (the new function is absent), not by behaviour. Both counts are true but read as stronger than they are.

### Severity review of the audit's own findings

F20-04, F20-07, F20-09 to F20-14 are honestly MINOR under PI-D-109 (F20-14 writes into a tracked audits file, not under inbox/state/data; F20-12 is conservative for P01; F20-04 is a second line behind `labels.read_from_body`). F20-01 should be MATERIAL (S20-3). F20-05 is MINOR on its own, but its mitigation is wrong and together with F20-01 it leaves S20-1 open. F20-02's "REPAIRED" needs S20-2. F20-06's repair holds against the X06 leak and a hand-written pin (M12 killed by x06) but fails open on missing fields (S20-8). F20-03 and F20-08 repairs hold against everything I tried (8 bad capture times refused visibly with nothing written; forged raw number, input or in-band point refused; the joint rewrite of inputs, raw number, point and document is the stated residual).

## Counterexample (new): CX-SK20

A memecoin named `100XGAIN` (run-together, as many real symbols are) with a fatal flag `CANNOT_EXIT_5K`. Every Phase 17 and 18 sanitizer passes it: `_ident` sees no trading word, `_token_text`'s multiplier regex needs a non-letter after the X, `check_text` has no multiplier rule. The report prints `| 100XGAIN | ... | CANNOT_EXIT_5K |` and the alert prints "100XGAIN on solana (...)" under its risk-override heading; `1000XGEM` and `GAIN100X` reach the report too. No Phase 20 check catches it (P41 tries SELLNOW only, P44 tries spaced text only), and F20-01 records the report as withholding `100XGAIN`. Script: `p20_cp20_attacks.py::test_cx_sk20_a_run_together_multiplier_symbol_is_withheld_in_report_alert_and_section` (fails at `b4d4768`, which is the finding).

## Cleanup

Clone, scratch worktree and temp databases deleted after the review; `/home/claude/memelab-inbox` untouched (`git status` there unchanged by this review).
