# PHASE 16: adversarial cross-component and independent E2E audit

State: PASS for scenario-only research mode, with disclosed limitations. Date 2026-10-23. This is not an empirically validated engine and makes no full release claim.

- The reviewer's strict reading is FAILED. On that reading the Low residuals keep G02 and G39 PARTIAL, and G16 and G27 need Elving's acceptance.
- The independent reviewer's final judgment, and the builder's, is PASS for the labeled research mode.
- If Elving rejects G16 or G27 as disclosed limitations, the phase is FAILED. Neither can be fixed in code, and the five-pass loop is used up.

Entry gate: Phase 15 PASS at 41488ad, reproduced by the reviewer (outcome tests 14 passed; p15 mutations 22 of 22).

## Who did what

The audit was run by an independent reviewer agent that had not written phases 05 to 15. Its brief listed the code, docs, data and hard rules, but none of the builder's conclusions. It wrote its own tests, scripts and verdicts:
- `audits/backtesting/testing/E2E_RESULTS.md`, with the original record and four re-run sections;
- `tests/test_backtest_e2e_audit.py`;
- `testing/test_p16r1_*`, `test_p16r2_*`, `test_p16r3_*` and `test_p16r4_repair_attacks.py`;
- `p16_*.py`, `p16r*_*.py`, `p16_mutations.json` and `p16r4_mutations.json`;
- logs `p16*`.

The reviewer never edited production code. The builder repaired code between passes and never edited the reviewer's tests.

## Bounded loop (5 passes)

| Pass | Commit | Reviewer verdict | Main findings |
|---|---|---|---|
| 1 | 30863a6 + 41488ad | FAILED, 32 PASS / 6 PARTIAL / 3 FAILED | D1 cohort read the future in replays (High); D2 cohort spliced pools (High); D3 and D4 partial exits; D5 network fee in the cash check; D6 migration race; D7 long write transactions; D8 to D10 Low; 3 leak mutations survived |
| 2 | 47a7845 | FAILED, 35 / 6 / 0 | D1 to D10 fixed. N1 dead feeds dropped from the cohort (Medium), N2 pool choice after the as-of, N3 wash volume, N4 redaction, N5 version, N6 duplicate run rows |
| 3 | 0e63563 | FAILED (Low only), 36 / 5 / 0 | N7 guard hid rugs, N3b volume floor evaded, N4b and N4c redaction, C1 and C2 cache |
| 4 | c42045b | FAILED, 36 / 5 / 0 | N8 report Markdown hid the cohort's bias and censoring (Medium, present since pass 1); N4d to N4f redaction; N3c guard shapes; C3 |
| 5 | 7c7b582 | PASS for scenario-only research mode, 39 / 2 / 0 | all pass-4 findings fixed; Low residuals N3d to N3f, N4g to N4i, C4, N8b, T1 |

After the final review, the builder added only:
- the N8b wording;
- C4 (database birth time added to the cohort cache key);
- tests for the four mutants the reviewer found surviving (T1).

The reviewer's final mutant set now catches 8 of 9. The ninth (R4-9) targets a line that C4 replaced, and is superseded by R16d-9 and R16d-10 in `p16_repair2_mutations.json`. Log: `testing/logs/p16r4_mutations_after_followups.log`.

## Final results (HEAD after the follow-ups)

| Check | Result |
|---|---|
| Full suite | 1024 passed, 1 failed (C-1, the pre-existing clock-dependent catalyst test; fails the same way on base f99c6c7) |
| Mutation sets p05 to p16, p16_repair, p16_repair2 | all caught (p16_repair2: 24 of 24) |
| Reviewer's test files (5 files, 74 tests) | 65 pass. The 9 that fail are: the accepted N3 fail-closed test, the 7 Low residual reproductions (N3d to N3f, N4g to N4i) and 1 accepted limitation test (exit-hour print). C4's reproduction now passes |
| Sealed benchmark rerun | cutoff hash 35f836f3 and both sealed-test ledger hashes (88ae4054, e4781814) reproduce under engine bt-0.2.0 |
| Golden math (reviewer's exact fractions) | 45 of 45 agree |
| Concurrency | 16-process first connects, 12 parallel assessments, parallel trackers and identical runs: no crash, no duplicate rows |
| Regression matrix | policy off: scout, analyze and alerts identical to base; policy on: additions only |
| `tools/release_audit.py` / `tools/release_e2e.py` | Needs action: no / PASS 78 of 78, no network |
| Clean local clone | backtest tests pass; release audit clean |

## Real historical cases (lab commit provenance; E2E_RESULTS.md "Real historical cases")

- Rug, 3GVSN8 "D O T F":
  - the lab rejected it for DEV_WALLET_FARM; the package says RISK_FATAL_FLAW;
  - the price collapsed by 99.98%, recorded as CENSORED.
- Failed catalyst, puter: the graduation was seen at 2026-10-08 18:40; the price was down 99% at 24 h.
- Positive catalyst, PQC:
  - up 190% at 24 h;
  - the replay canceled the entry for want of a liquidity observation, so no phantom fill.
- Fresh token, QTC: 3 closed bars; INSUFFICIENT_HISTORY, with no token-specific claim.
- Independent confirmation, all read-only:
  - DexScreener pool addresses and creation times;
  - DexScreener's current price confirms puter's collapse;
  - a fresh GeckoTerminal fetch matches the stored bars;
  - the lab's own Jupiter prices recorded at the time agree.
  - Historical bars from a second keyless provider were not available. Price paths are therefore single-provider.

## Release classification

Scenario-only research mode, clearly labeled:
- every sealed test is INSUFFICIENT_SAMPLE, and a new sealed test needs data after 2026-10-23 16:00 UTC;
- historical fills are LIQ_SNAPSHOT_APPROX, and exact historical pool state is SOURCE_BLOCKED;
- historical prices come from a single provider.

## Disclosed limitations (reviewer's list, accepted by the builder; Elving may reject G16 and G27)

1. G16: multi-hop routes are not modeled.
2. G27: the Phase 10 whole-period runs saw the sealed window before the Phase 11 pre-registration. The seal is procedural, per object.
3. Fills are LIQ_SNAPSHOT_APPROX, and prices are single-provider.
4. The pool-disagreement guard is a heuristic. Shapes N3d, N3e and N3f slip through; none occurs in the real corpus. A window steered by wash volume is refused rather than measured (N3).
5. Cohort selection bias is flagged, not corrected. 27% of measurable REJECTED tokens could not be measured, mostly mints whose bars were never fetched.
6. Redaction of diagnostics is heuristic (N4g, N4h, N4i). Credentials are never stored, and the name=value, JSON, header and URL-query forms are removed.
7. C-1, the pre-existing failing test outside this package.

## Defects fixed in this phase (all with tests and guard mutations)

D1 to D11, N1 to N8, C1 to C4 and T1. Details and reproductions are in E2E_RESULTS.md. Guard mutation sets: `testing/p16_repair_mutations.json` and `testing/p16_repair2_mutations.json`.

NEXT ELIGIBLE PHASE: 17.
