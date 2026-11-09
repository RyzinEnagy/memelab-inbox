# Phase 21 evidence: reproducible research-only release or explicit NO-GO

- Branch `feature/predictive-intelligence`. HEAD before `90e4c6f` (pushed, orchestrator-verified). Pre-registration `0bb361e`; frozen release-check probes `2a29c68`, fixed `b048aac`; frozen doc-command probes `24c02a6`; recorded runs, release documents and evidence `67f1f7d`; records commit `6fafc1d`; post-commit checks in `postcommit/` (suite 2 failed, the two known, 2,243 passed, 1 skipped; guard 0 violations; seal 0 problems; single-branch release audit exit 0, "Needs action: no.").
- Work from 2026-11-09T22:10Z; first-pass records committed 22:50:40Z (corrected by CP21-1, skeptic F4: first written "to about 23:10Z"); repair pass from about 23:05Z. Package checksums: `sha256sum -c SHA256SUMS.txt` all OK.
- Status: **PASS** after the orchestrator's independent skeptic (no material finding, eight minor findings, counterexample CX-S21) and repair pass CP21-1 (PI-D-117, PI-D-118); see "Repair pass" below.
- Decision: GO for a research-only release of the abstention engine with the flag OFF (classification RESEARCH_BASELINE_ONLY, scoped); NOT_READY and NO-GO for any predictive release (`release/RELEASE_DECISION.md`, PI-D-115).

## Entry gate (G1)

| Command | Result | Exit |
|---|---|---|
| `python -m pytest tests -q -p no:cacheprovider` (22:11:14Z to 22:15:21Z) | `2 failed, 2243 passed, 1 skipped, 1 warning in 246.84s`; failures exactly `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` and `tests/test_catalyst_firecrawl.py::test_page_history_and_spend_survive_a_new_session_through_the_state_export` | 1 |
| `python -m pytest tests/test_predictive_phase20_cross.py -q -p no:cacheprovider` | 43 passed | 0 |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | `problems: []` | 0 |
| `monitoring.verify` on `phase_19/monitoring/OUTCOME_LEDGER.jsonl` | ok, 520 entries, head `fbcea491...` | n/a |
| `PHASE_20_RESULTS.json` status | PASS, head_after `18b907e` | n/a |

Stray `data/reports/20261109_2211_BRETT_0x532f.md` removed by hand. Disk: about 9 GB free at the start; the uv cache (8.6 GB), old pytest temp folders and this session's earlier phase scratch folders (Phases 03 to 20, all results committed) were removed, leaving about 21 GB free. A broader sweep of shared temp folders was refused by the permission system and not attempted again.

## Release checks (G2 to G7), `probes/release_checks.sh 90e4c6f b048aac OUTDIR`

Outputs in `evidence/release_checks/` (scratch paths replaced by OUTDIR). Table of steps with exit codes, wall times and memory: `release/SMOKE_LOG.md` and `evidence/release_checks/logs/steps.jsonl`.

| Gate | Command (inside the clone, `env -i`, `unshare -n`) | Result | Exit |
|---|---|---|---|
| G2 | `git ls-remote https://github.com/RyzinEnagy/memelab-inbox.git refs/heads/feature/predictive-intelligence` | `90e4c6fddae2...` | 0 |
| G2 | `git clone` of that URL, `checkout feature/predictive-intelligence`, fetch `b048aac` from the checkout, `merge --ff-only` | HEAD `90e4c6f` then `b048aac`; 5 changed paths, 0 outside `phase_21/` | 0 |
| G2 | `python3 -m venv`; `pip install numpy==2.5.3 pytest==9.1.1 iniconfig==2.3.1 pluggy==1.7.0 packaging==26.3` | freeze: iniconfig, numpy, packaging, pluggy, Pygments, pytest; no system site packages | 0 |
| G2 | `sh -c "python -B audits/predictive-intelligence/phase_20/probes/lo_up.py && python -m pytest tests -q -p no:cacheprovider"` | `2 failed, 2239 passed, 5 skipped` (the two known; skips: node 3, jsonschema 1, IPv6 loopback 1) | 1 |
| G2 | the predictive tests with a tmpfs over `/home/claude/pi_research` (`unshare -m -n`) | `1453 passed, 7 skipped`, 0 failed; every skip names its reason | 0 |
| G2, G4, G6 | `bash audits/predictive-intelligence/phase_20/probes/e2e.sh b048aac OUTDIR/e2e` | release_e2e 78 of 78 stages, 0 network attempts; real-path smoke all checks true, 24 ABSTAIN, 0 forecast lines, `check_state` problems [] x4; release audit with history on a single-branch clone exit 0, "Needs action: no." | 0 |
| G3 | `python -B audits/predictive-intelligence/phase_21/probes/chronology_audit.py 2026-11-09T00:00:00Z OUTDIR/chronology_audit.json` | C1 to C4 true, 5 of 5 planted violations caught, 0 network events | 0 |
| G3 | `python -B audits/predictive-intelligence/phase_19/probes/run_prospective.py audit OUTDIR/p19_audit` | predictions commit `765eadb` 14:00:20Z before the first label call 14:00:26Z; no outcome at that commit; F1, F3, F4 ok | 0 |
| G3, G6 | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py`; `python -m memelab social guard` | `problems: []`; 0 violations | 0, 0 |
| G4 | `python -m pytest -q tests/test_predictive_phase20_cross.py` | 43 passed | 0 |
| G3, G4 | `python -B audits/predictive-intelligence/phase_20/probes/run_matrix.py OUTDIR/matrix` | 48 scenarios, 239 of 239 assertions, 25 PASS, 10 PASS_EXPECTED_ERROR, 12 TEST_ONLY, 1 PASS_WITH_PROBE_FINDING (P46, F20-07); mapped tests 232 passed; every row equal to Phase 20's repair-pass run | 0 |
| G4 | `python -B audits/predictive-intelligence/phase_20/probes/cx_rerun.py OUTDIR/cx` | 39 of 39 caught | 0 |
| G4 | `flag_off_identity.sh b048aac` then `flag_off_summary.py` | all identical (24 runs), frozen commit is the requested one; import traces empty | 0, 0 |
| G5 | `oos_sensitivity.py`, `recalc.py` | 0 differences from the committed Phase 20 files | 0, 0 |
| G6 | `threat_scan.py` | equal to Phase 20 apart from head, changed-file count and one license-title hit that is the Phase 20 scan file itself | 0 |
| G7 | `reproductions.py b048aac OUTDIR/reproductions.json` | all_reproduced true, 19 runners exit 0, differing {} | 0 |

Clone `git status` clean at the end (one test stray removed, `logs/strays_seen.txt`). Inside every check the environment held only HOME, LANG, LC_ALL, MEMELAB_RELEASE_CHECK and PATH (`logs/env_names_inside.txt`).

## Maturity step (G8), `evidence/maturity/MATURITY_RUN.json`

| Command (checkout at `b048aac`, 22:21Z to 22:26Z; corrected by CP21-1, skeptic F4: first written as `24c02a6`) | Result | Exit |
|---|---|---|
| `python -B audits/predictive-intelligence/phase_19/probes/fetch_labels.py fetch` | `{"mapped": 28, "planned": 28, "counts": {"planned": 28, "no_snapshot_price": 5}}`; 0 vendor calls | 0 |
| `python -B audits/predictive-intelligence/phase_19/probes/run_prospective.py outcomes` | T2 PENDING 7; label rows added 0; ledger appended 0, 520 entries, verify ok; network 0 | 0 |
| `unshare -n python -B audits/predictive-intelligence/phase_19/probes/run_prospective.py evaluate SCRATCH/evaluate` | verdicts INSUFFICIENT_DAYS x3, n 22, 24, 15, equal to the committed ones; every output byte-equal apart from `ledger_head` in PRIMARY_RESULTS.json and the run log | 0 |

The rewritten read plan moves the needed boundary of the 7 decisions to the T2 boundary (2026-10-28T10:30Z) but all 7 are already mapped to reads ending 2026-10-27T10:30Z, and `cmd_fetch` reads only unmapped decisions. Maturing them needs a code change: open item OI21-1 (PI-D-116). Files changed by the frozen commands: `phase_19/evidence/outcomes_runs.json` (one run record appended, earlier records byte-equal), and in the private store `read_plan.json` and one `predictive_label_runs` row. `drift` was not run (F20-14). A first `evaluate` call was stopped by a 120 s tool timeout before it wrote anything (git status unchanged) and was rerun in the background; logged in the search ledger.

## Doc commands and documents (G9, G10)

- `bash audits/predictive-intelligence/phase_21/probes/doc_commands.sh OUTDIR/e2e/smoke OUTDIR2` at `24c02a6`: 10 commands, exits as expected (9 zero, `check` on a damaged copy 2 STATE_TAMPERED); `evidence/doc_commands/`.
- `python -B audits/predictive-intelligence/phase_21/probes/release_docs_check.py audits/predictive-intelligence/phase_21/evidence/release_docs_check.json --plant` at `67f1f7d`: registry levels ABSTAIN and NO_GO only; 0 GO rows above the registry, 0 missing paths, 0 dashes, 0 guide commands missing from the doc-command log; planted defects 3 of 3 caught. Exit 0.
- Documents: `release/RELEASE_DECISION.md`, `INSTALL_RUNBOOK.md`, `USER_GUIDE.md`, `MODEL_LIMITS.md`, `ROLLBACK_PROOF.md`, `SMOKE_LOG.md`, `OPEN_DECISIONS.md`; `docs/predictive-intelligence/RELEASE.md`.

## Iteration log

1. Pass 1 (inspect and do): entry gate; chronology probe and maturity derivation as debug runs; pre-registration `0bb361e`; frozen probes `2a29c68`; release checks attempt 1 failed at setup (a short sha cannot be fetched; the fast-forward failed silently; measure.py was absent in the clone, so no step ran and nothing was recorded as a result). Fixed at `b048aac` (full sha, stop on a failed fast-forward); rerun complete.
2. Pass 2 (check): maturity step with the frozen commands; doc probes frozen at `24c02a6` then run; evidence copied with scratch paths replaced.
3. Pass 3 (own adversarial pass, not independent): the counterexample below; three path errors in the documents found by it (two evidence files copied under `_tail` names, one flag-off log path) and corrected before the documents commit; a claim in the first guide draft ("eligibility NOT_ASSESSED") corrected after reading `_process` (INPUT_STALE when inputs are older than 2 h, as in the smoke).

## Own counterexample (not independent)

Wrong but plausible: a release memo that marks SHADOW_ONLY (or VALIDATED_EXPERIMENTAL) as GO while the registry holds no entry at that level, or that cites an evidence file that does not exist. Caught by `probes/release_docs_check.py`: it reads the committed registry levels (ABSTAIN, NO_GO) and fails a GO row naming a higher level; it resolves every backticked path; planted copies of each defect are caught (`evidence/release_docs_check.json`, `planted_caught` all true). The chronology audit carries five more planted violations (`chronology_audit.json`, `negative_controls`).

## Deviations from the pre-registration

- D21-1 (withdrawn: replaced by amendment A1 of G3, PI-D-117, orchestrator ruling on skeptic F1): G3 asked the chronology scenarios P04, P05, P06, P07, P13, P20, P36, P43 to be PASS or PASS_EXPECTED_ERROR. P04 (a page crawled today describing an older event) is TEST_ONLY, as it was in Phase 20: no crawl source feeds the engine, so its guard is shown on fixtures only (3 of 3 assertions). The checklist row did not look up P04's class. Recorded, not reclassified; for the skeptic.
- D21-2: G2 said "pytest's three dependencies"; pytest 9.1.1 also installs Pygments, so the venv holds four. Still numpy and pytest only.
- D21-3: the doc-command run (G9) was not in the experiment registry at pre-registration; it got its own frozen commit `24c02a6` before its run and a registry row marked as added.
- D21-4: the checklist header says it was written "from 22:20Z"; its commit time is 22:18:42Z. The header time was an estimate; nothing else differs.
- D21-5: the full suite in the fresh venv skips 5 tests (3 need node, 1 jsonschema, 1 IPv6 loopback) where the checkout skips 1; all are environment skips with reasons.

## Artifacts

sha256 of every Phase 21 file: `PHASE_21_RESULTS.json` `artifacts`.

## Skeptic

Review: `skeptic/PHASE_21_SKEPTIC.md` (independent, fresh clone from GitHub at `51db1f6`, 2026-11-09 22:58Z to about 23:30Z), with its counterexample script `skeptic/p21_cx_early_censor.py` and output. No material failure; the release decision is supported item by item. Eight MINOR findings (F1 to F8) and counterexample CX-S21.

CX-S21 (wrong but plausible): a T2 decision recorded as VENDOR_OR_ROUTE_GAP (censored, final) before its label matures, because the vendor pool list was empty at that moment; for T2 a vanished pool is the likeliest positive, so an early censor drops it from every later evaluation. At `51db1f6` the ledger appended it and `verify` passed, and chronology C3 passed. Caught now (CP21-1): `monitoring.check_payload` refuses VENDOR_OR_ROUTE_GAP, UNVERIFIABLE_NO_VENDOR_HISTORY and NOT_READ with `recorded_at` before `label_matures_at` (NOT_YET_MATURED), `verify` replays it, chronology C3 refuses it and plants it as a sixth violation. Proof: `repair/CX_S21_AT_REPAIR_CODE.json` (the skeptic's script on the repair code: C3 not ok, append refused), `repair/OLD_CODE_CHECK.txt` (the new refusal test fails at `51db1f6`, the positive control passes on both), `tests/test_predictive_monitoring.py::test_cx_s21_*`.

## Repair pass (CP21-1, PI-D-118; G3 amendment PI-D-117)

| Finding | Verified | Repair |
|---|---|---|
| F1 G3 fail condition literally met by P04 | yes | amendment A1 (PI-D-117): P04 was TEST_ONLY in Phase 20 before the checklist; the row now requires P04 TEST_ONLY with all assertions; G3 passes as amended |
| F2 C4 by timestamps; 05 and 06 same commit; RELEASE.md overstated | yes (05 `b4baa78`, 06 `4565e0b`) | C4 by `git merge-base --is-ancestor`: STRICT_ANCESTOR for 07 to 20, SAME_COMMIT named for 05 and 06; RELEASE.md and the memo say so |
| F3 / CX-S21 early censored state | yes | code above, with a test failing on the old code |
| F4 maturity commit cited as `24c02a6` | yes (the run was at `b048aac`, 22:21Z) | corrected in the G8 table, PI-D-116 and the evidence header times |
| F5 RELEASE.md "all handled" | yes | says 12 scenarios TEST_ONLY and F20-07 open |
| F6 placeholders, hard-coded store path, macOS, checker scope | yes | USER_GUIDE section 1 uses the smoke's real values and was run literally (`probes/guide_sandbox.sh`, 14 lines, all exit 0); `PI_RESEARCH_DIR` for the Phase 19 runner and the reproduction test, rebuild route documented and the rest carried as OI21-2; runbook states the Linux-only isolation and what to do on macOS, and "12 comparisons over 24 runs"; `release_docs_check.py` checks every run command of the runbook and guide against the recorded runs (it found one more error: result files live under `data/inbox/`, fixed) |
| F7 paid data, maintenance owner, PI-D-020 status | yes | ED-2 adds any paid data; ED-11 maintenance owner Elving; PI-D-020 marked SUPERSEDED by PI-D-044 |
| F8 completion checklist not re-marked | yes | `qa/COMPLETION_CHECKLIST_PHASE21.md` (item 20 MET, item 10 note updated) |

Rerun from the repair commit (`release_checks.sh 51db1f6 a767710`, fresh GitHub clone of the pushed `51db1f6`, 20 changed paths, 7 outside `phase_21/`: the CP21-1 code, tests and decisions), outputs in `evidence/repair_rerun/`: full suite 2 failed (the two known), 2,241 passed (the 2 new tests), 5 skipped; predictive tests with stores hidden 1,455 passed, 7 skipped; cross 43 passed; seal and guard 0; chronology ok with 6 of 6 planted; Phase 19 order audit ok; matrix rows identical to the first pass; 39 of 39 counterexamples; OOS and recalculation 0 differences; threat scan equal apart from head and file count; release_e2e 78 of 78, smoke unchanged checks (24 ABSTAIN, 0 forecast lines), release audit "Needs action: no."; flag-off all identical; reproductions all reproduced (19 runners exit 0, 0 differing files). Doc commands rerun: same exits. No number or verdict changed; the only changed outputs are the chronology audit fields added by CP21-1 (C3 window rule, C4 relation per phase, the sixth planted violation).
