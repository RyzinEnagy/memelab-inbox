# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-129 and PI-D-140). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_21/`, and `maintenance/` for changes after Phase 21. Spend: `audits/predictive-intelligence/COST_LEDGER.md`. Plain-language release summary: [RELEASE.md](RELEASE.md).

## Position on 2026-11-10

- Phases 00 to 13 and 16 to 20: PASS. Phases 14 and 15: TEST_ONLY (behavioral path, optional, OFF, MIROFISH_NO_GO).
- Phase 21 (reproducible research-only release or explicit NO-GO): **PASS** after the orchestrator's independent skeptic (no material finding; 8 minor findings and counterexample CX-S21) and repair pass CP21-1 (PI-D-117 G3 amendment, PI-D-118). This is the last phase of the package; there is no next phase. What remains are Elving's decisions.
- Release decision (PI-D-115): GO for a research-only release of the abstention engine with the flag OFF (RESEARCH_BASELINE_ONLY, scoped); NOT_READY and NO-GO for any predictive release. MIROFISH_NO_GO.
- Maintenance CM-1 (2026-11-09, Elving's approval; PI-D-120, PI-D-121): the backtesting module (PR #4, `69bc5c3`) is merged into this branch, local only. Backtest status is now UNVERIFIED (was BACKTEST_NOT_AVAILABLE); every forecast still abstains; request records and reports show the real adapter result, which here is BACKTEST_STORE_MISSING (the real store is on Elving's computer).
- Maintenance CM-2 (approved by Elving on 2026-11-09; PI-D-122 to PI-D-129): ED-1 and ED-10 closed locally. `contract.PROMOTION_CM2` lets a model reach SHADOW only from an admissible prospective window after the recipe freeze (2026-11-10T01:13:46Z), with every frozen minimum and correction kept. The 69 stale Phase 16 cards are retired (kept); 6 fresh R-CM2-1 v1 cards (B0 and B2 by 3 targets, cutoff 2026-10-28T10:43:04Z, stale after 2026-11-11T10:43:04Z) are registered ABSTAIN under NO_VIABLE_CHAMPION pins. The daily cycle is ready, not scheduled. The orchestrator's skeptic found no material failure, six minor findings and counterexample CX-CM2-1; the repair pass (PI-D-140) fixed all of them (`maintenance/cm2_promotion_cards/skeptic/REPAIR_RESPONSE.md`): committed ledgers must be append-only across commits and anchors are by content, a run pushes its predictions before any label read and only on `feature/predictive-intelligence`, a reference is never SHADOW and a CANDIDATE has a PROMOTE and CHAMPION path, windows are per recipe, `--max-calls` at most 60 and `--now` for tests only. No number or level changed.
- Spend: 0. CM-2 made 8 free GeckoTerminal calls for labels, and a mutant of the mutation probe made 63 more from test clones before the probe was moved offline (PI-D-129); no paid, vendor-keyed or model call.

## What CM-2 did

- Change control and recipe first (`ed85b2c`), then the frozen code before any label read or fit (`e79d846`): PROMOTION_CM2 with pinned fingerprints, explicit training splits, `promotion.py`, the daily cycle, the build probe, tests.
- The previous session was cut off by a restart after the first of the 7 T2 reads. The read was checked against the frozen plan before resuming (`evidence/interruption.json`: all consistent); the resumed `fetch_t2` made 7 calls (one 429 retried), at most 6 in any 60 s. The first call's log entry is reconstructed from its read record and labelled so.
- `a140986`: 7 T2 labels (2 DRAWDOWN_50, 5 NO_SEVERE_EVENT), base label set (Phase 19 ledger pairs 61 of 61 equal), 6 cards (refit byte-identical), registry (1 RETIRE event for 69 entries, 6 REGISTER, 3 PIN), search ledger rows (N_search 130), cost ledger row.
- Change controls after the freeze: PI-D-124 (`43a485b`, the daily end-to-end test fixture), PI-D-126 (`b7aabe3`, tests for guards the first mutation probe found untested; the probe now commits each mutation), PI-D-128 (`a8c96d7`, a failed run no longer commits a ledger that does not verify; the only change to frozen cycle code), PI-D-129 (`2f72034`, `4e020cb`, mutant tests run offline; then three Phase 16 tests that the frozen code broke, found by the post-records suite: the retired Phase 16 entries now also see MODEL_INCOMPATIBLE_RETRAIN_REQUIRED for `contract.py` and `labels.py`, answers still ABSTAIN). `07a815e` adds `daily/PROCEDURE.md` (PI-D-125).
- Checks (`maintenance/cm2_promotion_cards/CM2_EVIDENCE.md`): old-code probe (CM-2 tests fail on `ed85b2c`), mutation probe offline (35 applied, 34 caught, D07 equivalent), two fresh-clone runs of the daily command (exit 0 twice; 0 decisions after the freeze, 0 calls; repeated at `a8c96d7`), full suite, guard, seal, reproductions, single-branch release audit with history.

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

1. Schedule the daily cycle (needs Elving's approval of a scheduled task): once a day, `python -B audits/predictive-intelligence/daily/predictive_daily.py run` in a full clone with `feature/predictive-intelligence` checked out and push access; the script pushes the branch itself, before reading outcomes and at the end (PI-D-140). Before that, the orchestrator pushes the repair commits. No window can start until the lab's state exports on `origin/main` resume (none after `71fc50e`, 2026-10-26). (OI21-1 is done for CM-2: the 7 labels are in the CM-2 base set; the Phase 19 ledger stays as recorded.)
2. Make the daily end-to-end tests refuse a network on their own (today only the mutation probe runs them inside `unshare -n`, PI-D-129); point the scout hook at the CM-2 registry (separate change control).
3. OI21-2: the private stores are portable only through a documented, untried rebuild; about 70 earlier probes still use `/home/claude/pi_research`.
4. MINOR items F20-07, F20-10, F20-13, F20-14 with the recommendations in `phase_21/release/OPEN_DECISIONS.md`; F20-11 is closed by the runbook.
5. Carried: catalyst and social tables are not exported; forward depth collector not deployed (PI-D-044); keep `tests/test_predictive_reproductions.py` green.
6. After CM-1: a phase to verify the installed backtesting engine (needed before any document may carry an assessment reference); the backtesting branch's reviewer set p16r4 fails its own baseline here (5 concurrency tests, same on `69bc5c3`).

## Waiting on Elving (`phase_21/release/OPEN_DECISIONS.md`, ED-1 to ED-10)

Maintenance owner: Elving (ED-11). ED-1 (promotion) and ED-10 (stale cards) are closed by CM-2. Still waiting: scheduling the daily cycle and letting it push; pointing the scout hook at the CM-2 registry; any LLM, Zep or MiroFish spend and any paid data; catalyst and social collection into a store this engine reads; deploying the forward depth collector (PI-D-044); pushing the CM-1 merge (done locally on 2026-11-09 with his approval); any merge into `main`; any external alert delivery; turning the flag on outside a sandbox; a signing key for the private state.

## Phase 21 commits

HEAD before `90e4c6f`; `0bb361e` pre-registration; `2a29c68` frozen probes; `b048aac` probe fix; `24c02a6` doc probes; `67f1f7d` recorded runs and documents; `6fafc1d` records; `51db1f6` post-commit record (pushed); repair: `da0ae96` change control, `a767710` CP21-1 code and documents, `881643f` repair records, then the post-commit record (`phase_21/postcommit_repair/`: suite 2 failed, the two known, 2,245 passed, 1 skipped; guard 0 violations; seal 0 problems; single-branch release audit exit 0). Local only; the orchestrator pushes.

## CM-1 commits

HEAD before `79bcd7e` (pushed); `445d2d7` change control PI-D-120; `69b7b57` merge; `6ea454d` bt-adapter-2 and tests; `97d094e` records; `1fb1110` audit copy kept as `.txt` (the post-commit audit at `97d094e` flagged the `.md` copy); then the post-commit record (`maintenance/cm1_backtest_merge/postcommit/`: suite 2 failed, the two known, 2,526 passed, 1 skipped; guard 0 violations; seal 0 problems; single-branch release audit with history exit 0). Local only; not pushed.

## CM-2 commits

HEAD before `e79d846` (CM-1 pushed up to `60eb729`); `ed85b2c` change control PI-D-122 and recipe; `e79d846` frozen code; `a140986` reads, labels, cards, registry; `43a485b` PI-D-124; `b7aabe3` PI-D-126; `07a815e` PROCEDURE.md; `a8c96d7` PI-D-128; `2f72034` PI-D-129 item 1 (also carried the OPEN_DECISIONS update, the skeptic packet and the second fresh-clone record); `4e020cb` probe fix; `f403b1b` records; `c66211c` PI-D-129 item 2; then the post-commit record (`maintenance/cm2_promotion_cards/postcommit/`, checks at `c66211c`: suite 2 failed, the two known, 2,568 passed, 1 skipped; guard 0 violations over 3,948 files; seal 0 problems; reproductions 6 passed; single-branch release audit with history exit 0, "Needs action: no."). Pushed by the orchestrator up to `cdff266`. Repair pass: `833b2f6` change control PI-D-140 and skeptic files; `fdc0f24` code and tests; `1818db3` probe mutations; then the repair records and their post-commit record (`maintenance/cm2_promotion_cards/postcommit_repair/`). Local only; not pushed.

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
