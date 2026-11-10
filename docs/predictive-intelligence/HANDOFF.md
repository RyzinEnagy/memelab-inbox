# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-139, PI-D-150; PI-D-140 to PI-D-149 are reserved for CM-2). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_21/`, and `maintenance/` for changes after Phase 21. Spend: `audits/predictive-intelligence/COST_LEDGER.md`. Plain-language release summary: [RELEASE.md](RELEASE.md).

## Position on 2026-11-09

- Phases 00 to 13 and 16 to 20: PASS. Phases 14 and 15: TEST_ONLY (behavioral path, optional, OFF, MIROFISH_NO_GO).
- Phase 21 (reproducible research-only release or explicit NO-GO): **PASS** after the orchestrator's independent skeptic (no material finding; 8 minor findings and counterexample CX-S21) and repair pass CP21-1 (PI-D-117 G3 amendment, PI-D-118). This is the last phase of the package; there is no next phase. What remains are Elving's decisions.
- Release decision (PI-D-115): GO for a research-only release of the abstention engine with the flag OFF (RESEARCH_BASELINE_ONLY, scoped); NOT_READY and NO-GO for any predictive release. MIROFISH_NO_GO.
- Maintenance CM-1 (2026-11-09, Elving's approval; PI-D-120, PI-D-121): the backtesting module (PR #4, `69bc5c3`) is merged into this branch, local only. Backtest status is now UNVERIFIED (was BACKTEST_NOT_AVAILABLE); every forecast still abstains; request records and reports show the real adapter result, which here is BACKTEST_STORE_MISSING (the real store is on Elving's computer).
- Maintenance CM-3 (2026-11-09, Elving's approval of every spend-free open decision; PI-D-130 to PI-D-139, PI-D-150), branch `maint/catalyst-export` from `60eb729`: opt-in catalyst and social section `_catsoc` in the state export (an allowlist since the repair: typed values only, no summaries) and a reader with `available_at` = first export commit time (ED-3); `alerts --send push_file` with push lines built from fixed parts (ED-7); HMAC-SHA256 signing of the private state with a key in its own folder and a rollback counter outside the state folder (ED-9); exact flag-on steps for the scheduled runs that name no key path and treat push lines as data (ED-8 preparation). Status **PASS** after the orchestrator's skeptic review and repair pass 2; not pushed, not merged.
- Spend: 0. No vendor, model or paid call in Phase 21, CM-1 or CM-3.

## What CM-3 did

- Change control first (`bac9960`), code and tests (`b99e139`), then a session restart. The resuming agent checked the four uncommitted documents against the code and repaired (`e822887`): trader source ids hashed (PI-D-135), the stdout assertion and `FLAG_ON.md` corrected, `predictive_state.key` gitignored, a flag-off identity probe added. Records `6f4aab9`, post-commit `a9ec8e8`.
- Skeptic review of `a9ec8e8` (`maintenance/cm3_spend_free/skeptic/CM3_SKEPTIC.md`): M1 summaries carried a URL, handle, email and phone number into the export; M2 the push line carried the deployer-written symbol to an unattended session; m1 rollback to an older signed snapshot accepted (counterexample); m2 key beside the state; m3 real-data coverage vacuous; m4 TypeError on a non-ASCII hmac. All hold; no disagreement.
- Repair pass 2: change control `dca558c` (PI-D-137 to PI-D-139, PI-D-150), code and tests `ab286ea`, fixture `2098808`, then records. Export format `catsoc-export-2`: every column typed (ref, sha256, time, int, chain, address, enumerated vocabulary, prefixed source ref), summaries not exported, ids become refs, the reader refuses anything else. Alert labels and push lines show a symbol only when it is 1 to 10 ASCII letters or digits and passes the trading-word and instruction-word rules; push lines are built from fixed parts and must match one grammar. The engine finds the key in `~/mnt/memelab-key` (Windows `%USERPROFILE%\memelab-key\`) itself; the scheduled prompt names no key path and says push lines and command output are data. The last signed seq and tip are kept, HMAC-protected, beside the key; a rollback or fork is StateTampered. Non-hex hmac is StateTampered.
- Checks: CM-3 tests 161 passed; the new tests fail on `a9ec8e8` (106 failed, 7 passed, explained); mutations 7 of 7 caught; full suite 2 failed (the two known), 2,687 passed, 1 skipped; flag-off identity holds on 3 databases; real exports unchanged (78 versions, no section); release e2e 78 of 78; reproductions 6 passed; seal 0 problems. No number or verdict of Phases 00 to 21 changed.
- Documents: `maintenance/cm3_spend_free/` `EXPORT.md`, `PUSH_DELIVERY.md`, `SIGNING.md`, `FLAG_ON.md`, `CM3_EVIDENCE.md` (section "Repair pass 2"), `CM3_RESULTS.json`.
- Signing key: not created. Elving creates `predictive_state.key` in a new folder `%USERPROFILE%\memelab-key\` and connects it to each memelab scheduled task as a second folder (`SIGNING.md`).

## What CM-1 did

- Change control first (`445d2d7`), then `git merge --no-ff origin/feature/backtesting` (`69b7b57`). Two conflicts, both kept on both sides: `memelab/cli.py` (backtest hooks verbatim, then the predictive hooks, each behind its own flag) and `tools/release_audit.py` (both sets of reviewed entries).
- `6ea454d`: bt-adapter-2 reads the installed package read-only (store path and schema DDL only; `mode=ro`, `query_only`; never connects, migrates or writes through the package); BACKTEST_STORE_MISSING; schema checked against the `69bc5c3` pin and the installed DDL; the pass records `backtest_store`; the scout section shows "Backtesting: UNVERIFIED; store BACKTEST_STORE_MISSING"; the report shows the real result and the new unblock text. Tests updated to the installed state, new store tests, Phase 18 pins amended (`PINNED_SHA256_PI-D-120.json`), goldens regenerated (only backtest lines changed), reproductions run with the package hidden.
- Checks (`audits/predictive-intelligence/maintenance/cm1_backtest_merge/CM1_EVIDENCE.md`): suite 2 failed (the two known clock tests), 2,526 passed, 1 skipped; reproductions 6 passed; release_e2e 78 of 78; guard 0 violations; seal 0 problems; backtesting counterexamples 3 of 3, builder and collector mutations 269 of 269, reviewer sets p17 2 of 2 on rerun and p16r4 identical to a clean `69bc5c3`; single-branch release audit with history exit 0. The history blob `acbc9c9016` (D-BT-016) is now reachable from this branch and is listed as reviewed by the existing EXPLAINED entry.

## What Phase 21 did

- Entry gate at `90e4c6f`: suite 2 failed (the two known clock tests), 2,243 passed, 1 skipped; Phase 20 cross tests 43 passed; seal intact; outcome ledger verifies.
- Pre-registration `0bb361e` (G1 to G11, classification rules, maturity rule); frozen probes `2a29c68`, fixed `b048aac`; doc probes `24c02a6`; recorded runs, release documents and evidence `67f1f7d`.
- Release checks from a fresh clone of the pushed branch (`probes/release_checks.sh`): new venv with numpy and pytest only, `env -i`, `unshare -n`. Full suite as expected; predictive tests with the private stores hidden 0 failures; release_e2e 78 of 78; real-path smoke 24 ABSTAIN, 0 forecast lines; chronology audit C1 to C4 true with 5 of 5 planted violations caught; Phase 19 order audit true; 48 scenarios 239 of 239 assertions; 39 of 39 counterexamples; flag-off identity all identical; OOS and recalculation identical to Phase 20; threat scan clean; release audit "Needs action: no."; reproductions all reproduced.
- Phase 19 maturity step with the frozen commands: 0 reads planned, 0 entries appended, verdicts unchanged; the 7 T2 PENDING outcomes need a `fetch_labels.py` change (OI21-1, PI-D-116).
- Release documents in `audits/predictive-intelligence/phase_21/release/`: RELEASE_DECISION, INSTALL_RUNBOOK, USER_GUIDE, MODEL_LIMITS, ROLLBACK_PROOF, SMOKE_LOG, OPEN_DECISIONS. Every runbook and guide command was run once (`evidence/doc_commands/`).
- Skeptic and repair: CX-S21 (a censored state recorded before maturity) is now refused by the outcome ledger and the chronology audit (test fails on `51db1f6`); C4 judged by ancestry (phases 05 and 06 committed rules and results together); documents corrected (placeholders, macOS, research dir, paid data, maintenance owner Elving, F20-07 and the 12 TEST_ONLY scenarios named); release checks rerun from the repair commit `a767710`, no number or verdict changed.
- Deviations stated in the evidence: D21-1 (P04 TEST_ONLY, replaced by amendment A1, PI-D-117), D21-2 (Pygments comes with pytest 9), D21-3 (doc-command run added with its own frozen commit), D21-4 (checklist header time), D21-5 (fresh-env skips).

## Open items, in order

1. OI21-1: the `fetch_labels.py` change for the 7 PENDING T2 outcomes (cannot change a verdict).
2. OI21-2: the private stores are portable only through a documented, untried rebuild; about 70 earlier probes still use `/home/claude/pi_research`.
3. MINOR items F20-07, F20-10, F20-13, F20-14 with the recommendations in `phase_21/release/OPEN_DECISIONS.md`; F20-11 is closed by the runbook.
4. Carried: forward depth collector not deployed (PI-D-044); keep `tests/test_predictive_reproductions.py` green. Catalyst and social tables: exportable since CM-3 (switch off until the scheduled steps are applied); catalyst targets on exported rows need a later phase.
5. After CM-1: a phase to verify the installed backtesting engine (needed before any document may carry an assessment reference); the backtesting branch's reviewer set p16r4 fails its own baseline here (5 concurrency tests, same on `69bc5c3`).
6. CM-3: OI-CM3-1 (secret salt for the export refs, optional); new lab vocabulary values are exported as null until `VOCAB` is extended; the research report and the lab's scout report keep their earlier symbol rules (the strict rule covers alert labels and push lines); the key protects against everything except a holder of the key folder, the scheduled session included.

## Waiting on Elving (`phase_21/release/OPEN_DECISIONS.md`, ED-1 to ED-10)

Maintenance owner: Elving (ED-11). Promotion change control (PI-D-091); any LLM, Zep or MiroFish spend and any paid data; catalyst and social collection into a store this engine reads; deploying the forward depth collector (PI-D-044); pushing the CM-1 merge (done locally on 2026-11-09 with his approval); any merge into `main`; any external alert delivery; turning the flag on outside a sandbox; a signing key for the private state; retiring or replacing the stale reference cards.

## Phase 21 commits

HEAD before `90e4c6f`; `0bb361e` pre-registration; `2a29c68` frozen probes; `b048aac` probe fix; `24c02a6` doc probes; `67f1f7d` recorded runs and documents; `6fafc1d` records; `51db1f6` post-commit record (pushed); repair: `da0ae96` change control, `a767710` CP21-1 code and documents, `881643f` repair records, then the post-commit record (`phase_21/postcommit_repair/`: suite 2 failed, the two known, 2,245 passed, 1 skipped; guard 0 violations; seal 0 problems; single-branch release audit exit 0). Local only; the orchestrator pushes.

## CM-3 commits

Branch `maint/catalyst-export`, base `60eb729`; `bac9960` change control; `b99e139` code and tests; `e822887` repair after the restart; `6f4aab9` records; `a9ec8e8` post-commit record (reviewed by the skeptic); repair pass 2: `dca558c` change control, `ab286ea` code and tests, `2098808` test fixture, then the records commit and the post-commit record (`maintenance/cm3_spend_free/postcommit_repair/`). Local only; the orchestrator merges into `feature/predictive-intelligence` and `main` (ED-6) and applies the scheduled steps (ED-8) last.

## CM-1 commits

HEAD before `79bcd7e` (pushed); `445d2d7` change control PI-D-120; `69b7b57` merge; `6ea454d` bt-adapter-2 and tests; `97d094e` records; `1fb1110` audit copy kept as `.txt` (the post-commit audit at `97d094e` flagged the `.md` copy); then the post-commit record (`maintenance/cm1_backtest_merge/postcommit/`: suite 2 failed, the two known, 2,526 passed, 1 skipped; guard 0 violations; seal 0 problems; single-branch release audit with history exit 0). Local only; not pushed.

## The reviewed history blob

Since CM-1 the blob `acbc9c9016` (`audits/backtesting/research/smoke/etcherfx__sol-trade/output.txt`, an environment variable name quoted by a static scan; D-BT-016, PI-D-049 item 6) is reachable from this branch. The release audit lists it as reviewed through the existing EXPLAINED entry; a single-branch audit with history gives "Needs action: no.".

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no recovery words or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flag overrides unchanged. Forecasts stay a separate evidence section with the flag OFF by default. No raw social content in the repository. Behavioral output is fictional, never a probability. References are never forecasts. Alerts are previews in a local outbox; nothing is sent.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git log -8 --oneline
python3 -m venv .venv && .venv/bin/python -m pip install numpy==2.5.3 pytest==9.1.1
.venv/bin/python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
.venv/bin/python -m pytest tests -q
.venv/bin/python -B audits/predictive-intelligence/phase_21/probes/chronology_audit.py 2026-11-09T00:00:00Z /tmp/p21_chrono.json
.venv/bin/python -B audits/predictive-intelligence/phase_21/probes/release_docs_check.py /tmp/p21_docs.json --plant
bash audits/predictive-intelligence/phase_21/probes/release_checks.sh 90e4c6f HEAD /tmp/p21_rc
```

Use a full clone (the commit-order tests need the history). Expect `"problems": []` from the seal check and, in the suite, only the two known clock-dependent failures; then `git clean -fq data/reports` and remove `data/memelab.sqlite-shm` and `-wal`. `release_checks.sh` needs root for `unshare` and the private stores under `/home/claude/pi_research/` for the reproductions.
