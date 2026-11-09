# Phase 21 independent skeptic review

Reviewer: independent skeptic (fresh context), 2026-11-09, 22:58Z to about 23:30Z. Branch tip reviewed: `51db1f6` (equal to `refs/heads/feature/predictive-intelligence` on GitHub; my clone was made from the GitHub URL, not from the local checkout). Nothing was written inside `/home/claude/memelab-inbox`. All lab and test commands ran in my own clone under `env -i` and `unshare -n`, with a temp `MEMELAB_DB`; no vendor call was made.

## Verdict

No material failure found. The release decision (PI-D-115: GO only for the research-only abstention engine with the flag OFF; NOT_READY and NO-GO for any predictive release; BACKTEST_NOT_AVAILABLE; MIROFISH_NO_GO) is supported item by item, and no release document claims skill, edge, calibration or profit. Eight MINOR findings, one of which (F1) needs an explicit orchestrator ruling because the phase's own pre-registered G3 fail condition is literally met.

## Checks run

| # | Check | Command (in my clone, env -i, unshare -n) | Result |
|---|---|---|---|
| 1 | Pushed branch | `git clone https://github.com/RyzinEnagy/memelab-inbox.git; git checkout feature/predictive-intelligence; git log -1` | `51db1f6713cd...`, clean |
| 2 | Fresh venv | `python3 -m venv venv; pip install numpy==2.5.3 pytest==9.1.1 iniconfig==2.3.1 pluggy==1.7.0 packaging==26.3; pip freeze` | iniconfig, numpy, packaging, pluggy, Pygments 2.21.0, pytest; `include-system-site-packages = false` (D21-2 confirmed) |
| 3 | Full suite, venv outside the clone | `unshare -n sh -c "python -B .../phase_20/probes/lo_up.py && python -m pytest tests -q -p no:cacheprovider"` | `2 failed, 2239 passed, 5 skipped` in 241 s, exit 1; failures exactly the two known clock tests. Matches the release-check figures (re-derived number 1) |
| 4 | INSTALL_RUNBOOK literally, `.venv` inside the clone (steps 2 to 4) | step 3 `check_seal.py` and `memelab social guard`; step 4 as written with `.venv/bin` first on PATH; then `git clean -fq data/reports`, `rm -f data/memelab.sqlite-shm data/memelab.sqlite-wal` | seal `problems: []` exit 0; guard 0 violations exit 0; suite `2 failed, 2239 passed, 5 skipped` (the in-repo `.venv` does not disturb the guard or the scans; Python 3.13 writes `.venv/.gitignore`, so git status stays clean); one stray `data/reports/<stamp>_BRETT_0x532f.md`, removed by the step; `git status` clean |
| 5 | release_e2e, real-path smoke, single-branch release audit | `bash audits/.../phase_20/probes/e2e.sh 51db1f6 OUT/e2e` | release_e2e exit 0, ok true at `51db1f6`; smoke: 8 attempted, 24 documents, 24 ABSTAIN, 0 forecast lines, 16 duplicates, storm superseded 4 with one attempt per mint, every `check_state` exit 0, flag-off reports byte-equal to `b0fad12`, lab tables equal (re-derived number 2); release audit `--history` exit 0, "Needs action: no." |
| 6 | Flag-off identity | `flag_off_identity.sh 51db1f6 OUT/flagoff && flag_off_summary.py OUT/flagoff OUT/flag_off_identity.json` | all_identical true, 24 runs (12 comparisons), commit_check true, malformed config exit 1 at base and frozen alike (F20-13) |
| 7 | Chronology audit | `python -B audits/.../phase_21/probes/chronology_audit.py 2026-11-09T00:00:00Z OUT/chrono.json` | exit 0; output equal to the committed `chronology_audit.json` apart from `head`; 69 of 69 MODEL_STALE, three targets NO_VIABLE_CHAMPION, 198 predictions, outcomes LABELED 61, PENDING 7 (re-derived number 3); 5 of 5 planted violations caught |
| 8 | Doc commands and rollback | `doc_commands.sh OUT/e2e/smoke OUT/doc` | 10 commands with the recorded exits (9 zero, tampered state 2 STATE_TAMPERED); `docs_demo.json` equal to the committed one |
| 9 | Rollback: a JSON-valid tamper (my own) | change `SOURCE_STALE` to `SOURCE_FRESH` in a copy of `DOCUMENTS.jsonl`, `integration check` | exit 2, STATE_TAMPERED "content does not match its record id" (stronger than the one-byte JSON break in ROLLBACK_PROOF) |
| 10 | OI21-1 code claim | read `phase_19/probes/fetch_labels.py` `cmd_fetch` | `if p["decision_key"] not in rmap` skips every mapped decision: the description is correct |
| 11 | OI21-1 cannot change a verdict | current outcome per (decision, T2) from the committed ledger | T2 LABELED on 2026-10-24 and 10-25 only; the 7 PENDING are all 2026-10-26; maturing them gives 3 decision days, below 5 (re-derived number 4) |
| 12 | C4 git order, by ancestry and by commit | `git log --diff-filter=A` for each phase 05 to 20 checklist and RESULTS, `git merge-base --is-ancestor` | 07 to 20: checklist commit is a strict ancestor of the RESULTS commit; 05 (`b4baa78`) and 06 (`4565e0b`): checklist and RESULTS added in the same commit (F2) |
| 13 | Overstatement grep | every hit of edge, skill, profit, calibrat*, validated, predicts, accura*, signal*, buy, sell*, beat*, works? in RELEASE.md, HANDOFF.md, ROADMAP.md, release/*.md, PHASE_21_EVIDENCE.md, printed with context | every hit is a negation, a state name (UNCALIBRATED, SELLNOW as a withheld token example) or a historical description; no claim of skill, edge, calibration or profit. Two softer overstatements in RELEASE.md (F2, F5) |
| 14 | Mutation for the counterexample | in `monitoring.prospective_records` drop `if mature else "PENDING"` for VENDOR_OR_ROUTE_GAP; run the monitoring, Phase 19, Phase 20 cross and reproduction tests | 1 failed (`test_prospective_records_classify_with_the_frozen_rule_pending_before_maturity_and_gaps_censored`), 102 passed; reverted |

Clone removed at the end. Disk used at peak about 0.6 GB.

## Release decision, item by item

| Item | Evidence I checked | Supported |
|---|---|---|
| Abstention engine GO, flag OFF, research only | checks 3 to 8: suite, e2e, smoke 24 of 24 ABSTAIN, flag-off identity at `51db1f6`; no `data/config.json` in the tree | yes |
| Predictive release NOT_READY, NO-GO | chronology C1: 69 entries, all MODEL_STALE, no CHAMPION; MODEL_LIMITS verdicts with their files (Phase 12 holdout, Phase 13 UNCALIBRATED, Phase 19 INSUFFICIENT_DAYS) | yes |
| BACKTEST_NOT_AVAILABLE | every smoke request carries `backtest_status: BACKTEST_NOT_AVAILABLE` (state DOCUMENTS); no `memelab.backtest` module | yes |
| MIROFISH_NO_GO | PI-D-081, Phase 15 evidence; module OFF; no LLM key in env (check 2 env -i) | yes (on records; not re-run) |
| RESEARCH_BASELINE_ONLY as the label | G10 scopes it to "abstention engine, references internal"; the package's term suggests a usable baseline, but nothing is shown. The scoping is explicit in every document | yes, with F1 and F6 |

## Findings

F1 (MINOR, needs an orchestrator ruling). D21-1: G3's pre-registered fail condition is "a chronology scenario not PASS or PASS_EXPECTED_ERROR", and P04 is TEST_ONLY; G10 then says RESEARCH_BASELINE_ONLY needs G2 to G7 to pass. Read literally, the phase's own rules give NOT_READY. Substantively it is a drafting error, not an outcome-driven move: P04 was already TEST_ONLY in Phase 20's matrix, before this checklist was written, and no crawl source feeds the engine. Acceptable only if recorded as an amendment of G3 (a change control naming the row), not as "G3 PASS with deviation".

F2 (MINOR). Chronology C4 tests `checklist_commit_time <= results_commit_time` on committer timestamps. It passes Phases 05 and 06, where the checklist and RESULTS were added in the same commit, so for those two phases there is no git proof that the checklist preceded the results; a backdated committer date would also pass. RELEASE.md's "every phase wrote its rules before its results" overstates this (RELEASE_DECISION's "committed no later than" is literally true). Fix: C4 should require the checklist commit to be a strict ancestor (`git merge-base --is-ancestor` and not equal), and RELEASE.md should say "phases 07 to 20" or name 05 and 06 (their target rules were frozen earlier, in Phase 01 at `b6f2621`).

F3 (MINOR). The counterexample below: an early censored outcome is not refused by the ledger or by the chronology audit.

F4 (MINOR, records). The G8 table in PHASE_21_EVIDENCE.md and PI-D-116 say the maturity commands ran in the checkout at `24c02a6`; `evidence/maturity/MATURITY_RUN.json` records head `b048aac`, and the appended `outcomes_runs.json` record has `as_of_utc` 2026-11-09T22:21:54Z, before `24c02a6` existed (committed 22:26:13Z). The evidence header says work ran "to about 23:10Z" but the file was committed at 22:50:40Z.

F5 (MINOR, wording). RELEASE.md: "48 trap scenarios and 39 earlier counterexamples: all handled." 12 scenarios are TEST_ONLY (fixtures only) and P46 is PASS_WITH_PROBE_FINDING with F20-07 open. Say so in the plain-language summary.

F6 (MINOR, operability). Following the documents literally:
- USER_GUIDE section 1 uses `/path/to/latest_export.json`, `MINT1 MINT2` and `RESULT_IDS` without saying where an export or result ids come from (the smoke uses `git show 71fc50e:data/state/latest.json` and the mints and results listed in `flag_off_identity.sh`). A reader cannot run it as written.
- USER_GUIDE section 3 (maturity run) and the reproduction scripts hard-code `/home/claude/pi_research/`; they cannot run on another machine (for example Elving's Mac). The documents say the stores are "rebuildable" but give no rebuild command, and no rebuild was run in Phase 21.
- INSTALL_RUNBOOK says "Linux or macOS", but the recommended step 4 needs `unshare` and root, and `lo_up.py` is a Linux ioctl; on macOS only the plain `pytest` line applies. The runbook's "12 of 12 runs" means 12 comparisons of 24 runs (ROLLBACK_PROOF says 24 runs).
- `release_docs_check.py` checks only the `python -B -m memelab.predictive...` commands of USER_GUIDE against the doc-command log; G9 says every command of the runbook and the guide. The runbook commands were in fact run by `release_checks.sh` (except the in-repo `.venv`, which I ran: it works).

F7 (MINOR, open decisions). OPEN_DECISIONS covers everything the Phase 20 HANDOFF listed as waiting on Elving except "any paid data" (ED-2 names only LLM, Zep and MiroFish spend). The maintenance owner is "Elving decides", not named, and is not an ED row. PI-D-020 is still marked PROPOSED although PI-D-044 resolved it (ED-4 covers the remaining deployment, so no decision is missing, but the status should read SUPERSEDED by PI-D-044). No other PI-D is PROPOSED.

F8 (MINOR). COMPLETION_CHECKLIST: the only item-by-item audit is Phase 20's (`phase_20/qa/COMPLETION_CHECKLIST_AUDIT.md`), with item 20 NOT_MET "Phase 21's deliverable" and item 10 still noting "G25 open" (closed by PI-D-112). Phase 21 does not re-mark it. On my checks items 1, 2, 13, 14, 16, 17, 19 hold at `51db1f6` (checks 3 to 8), item 20 is met by RELEASE_DECISION.md, item 18 holds (spend 0, no schedule). Recommend a one-line Phase 21 addendum.

## Deviations D21-1 to D21-5 and OI21-1

- D21-1: see F1 (substantively acceptable; procedurally an amendment, not a deviation).
- D21-2: acceptable; Pygments is a pytest 9 dependency (check 2).
- D21-3: acceptable; the doc-command probe has its own frozen commit before its run.
- D21-4: acceptable; header time only.
- D21-5: acceptable; I got the same 5 skips with reasons (node 3, jsonschema 1, IPv6 1).
- OI21-1: acceptable as recorded, not a gate failure. G8's rule was fixed before the recorded run (after a disclosed debug derivation), the code reason is correct (check 10), the ledger stays append-only and verifies, and the verdict cannot change (check 11: T2 would reach 3 decision days, minimum 5). The 7 PENDING are matured but unread; they should not be counted as PENDING-before-maturity anywhere, and C3 does not (it only checks that a PENDING was recorded before maturity).

## Counterexample CX-S21 (new)

Script: `/home/claude/pi_orchestration/skeptic/p21_cx_early_censor.py`, output `p21_cx_early_censor_out.json`.

Wrong but plausible: a maturity run, or a hand-run append, records a T2 decision as VENDOR_OR_ROUTE_GAP before its label matures because the vendor pool list was empty at that moment. VENDOR_OR_ROUTE_GAP is censored and FINAL, and for T2 ("halves, or trading stops and stays stopped") a vanished pool is the decision most likely to be a positive, so an early censor silently removes a likely positive from every later evaluation. It is the same class as "LABELED before maturity", which both the ledger and the chronology audit refuse.

Result on the committed ledger (the first-of-pair T2 VENDOR_OR_ROUTE_GAP outcome, `recorded_at` moved to `label_matures_at - 3600`):
- chronology audit C3: ok true (not caught); control with an early LABELED: ok false (caught);
- `monitoring.append` on a truncated temp copy: appended, `verify` ok true (not caught); control with an early LABELED: refused NOT_YET_MATURED;
- the code path that would produce it in production (`prospective_records` with `if mature else "PENDING"` removed) is caught by `tests/test_predictive_monitoring.py::test_prospective_records_classify_with_the_frozen_rule_pending_before_maturity_and_gaps_censored`.

So the production generator is guarded by a test, but the ledger guard and the release's chronology audit are not: `check_payload` applies the maturity rule to VENDOR_OR_ROUTE_GAP only when it supersedes a PENDING, never for the first outcome of a pair, and C3 checks only LABELED and PENDING. Fix (change control): in `check_payload`, refuse a VENDOR_OR_ROUTE_GAP (and any window-dependent state) with `recorded_at < label_matures_at`, first outcome or not; add the same rule to C3 and a sixth planted violation. MARKET_INACTIVE, THINNED, NO_SNAPSHOT_PRICE and OUT_OF_SCOPE_CHAIN are decision-time classes and may be recorded early (8 OUT_OF_SCOPE_CHAIN outcomes in the ledger are), so the rule must name the window-dependent states only. No real ledger entry has this defect today (all 3 VENDOR_OR_ROUTE_GAP outcomes were recorded 4 h to 46 h after maturity).
