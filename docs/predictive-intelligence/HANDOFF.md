# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-118). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_21/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`. Plain-language release summary: [RELEASE.md](RELEASE.md).

## Position on 2026-11-09

- Phases 00 to 13 and 16 to 20: PASS. Phases 14 and 15: TEST_ONLY (behavioral path, optional, OFF, MIROFISH_NO_GO).
- Phase 21 (reproducible research-only release or explicit NO-GO): **PASS** after the orchestrator's independent skeptic (no material finding; 8 minor findings and counterexample CX-S21) and repair pass CP21-1 (PI-D-117 G3 amendment, PI-D-118). This is the last phase of the package; there is no next phase. What remains are Elving's decisions.
- Release decision (PI-D-115): GO for a research-only release of the abstention engine with the flag OFF (RESEARCH_BASELINE_ONLY, scoped); NOT_READY and NO-GO for any predictive release. BACKTEST_NOT_AVAILABLE. MIROFISH_NO_GO.
- Spend: 0. No vendor, model or paid call in Phase 21.

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
4. Carried: catalyst and social tables are not exported; forward depth collector not deployed (PI-D-044); keep `tests/test_predictive_reproductions.py` green.

## Waiting on Elving (`phase_21/release/OPEN_DECISIONS.md`, ED-1 to ED-10)

Maintenance owner: Elving (ED-11). Promotion change control (PI-D-091); any LLM, Zep or MiroFish spend and any paid data; catalyst and social collection into a store this engine reads; deploying the forward depth collector (PI-D-044); merging the backtesting PR #4; any merge into `main`; any external alert delivery; turning the flag on outside a sandbox; a signing key for the private state; retiring or replacing the stale reference cards.

## Phase 21 commits

HEAD before `90e4c6f`; `0bb361e` pre-registration; `2a29c68` frozen probes; `b048aac` probe fix; `24c02a6` doc probes; `67f1f7d` recorded runs and documents; `6fafc1d` records; `51db1f6` post-commit record (pushed); repair: `da0ae96` change control, `a767710` CP21-1 code and documents, then the repair records commit and its post-commit record (`phase_21/postcommit/`, see RESULTS `head_after`). Local only; the orchestrator pushes.

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (a reviewed false positive on that branch, D-BT-016; PI-D-049 item 6). It is not reachable from `feature/predictive-intelligence`, whose own audit passes on a single-branch clone.

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
