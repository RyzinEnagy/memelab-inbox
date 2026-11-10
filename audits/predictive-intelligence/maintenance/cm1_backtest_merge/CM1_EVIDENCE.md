# CM-1 evidence: merge of the backtesting module (PR #4) into feature/predictive-intelligence

Change control: PI-D-120 (written and committed before the merge, `445d2d7`). Result: PI-D-121. Approved by Elving on 2026-11-09. Local only; not pushed.

## Commits

| Commit | What |
|---|---|
| `79bcd7e` | HEAD before (pushed) |
| `445d2d7` | change control PI-D-120 |
| `69b7b57` | `git merge --no-ff origin/feature/backtesting` (tip `69bc5c3`, base `f99c6c7`), two conflicts resolved by keeping both sides |
| `6ea454d` | bt-adapter-2 and the test updates |
| records commit | this file, DECISIONS, HANDOFF, ROADMAP, RELEASE.md |

## Merge and conflicts

`git merge --no-ff --no-commit origin/feature/backtesting` reported two content conflicts; everything else (about 500 files under `memelab/backtest/`, `tests/test_backtest_*`, `docs/backtesting/`, `audits/backtesting/`, `workplans/backtesting/`, `.gitignore`, `memelab/social/alerts_core.py`, `memelab/social/alerts_engine.py`) merged without conflict.

1. `memelab/cli.py`: both branches hook `cmd_analyze` and `cmd_scout` at the same lines. Kept both: the backtest hook lines of `69bc5c3` verbatim (35 added lines, kept as `tests/fixtures/predictive/cli_backtest_hook_69bc5c3.txt`) and the Phase 17 predictive hook (42 lines). Order: backtest line, then predictive line after `analyze`; backtest section, then predictive section after the unchanged scout body. Each stays behind its own flag (backtest policy; `predictive.enabled`).
2. `tools/release_audit.py`: both branches append reviewed EXPLAINED entries at the end of the list. Kept both sets (PI-D-074 entries, then D-BT-016 entries).

No record of either initiative was edited by the other (`docs/backtesting/` unchanged from `69bc5c3`; `docs/predictive-intelligence/` changed only by this change control).

## What changed in forecast and report output

| Where | Before (on `79bcd7e`) | After |
|---|---|---|
| `contract.backtest_status()`, every document's `backtest_status` | BACKTEST_NOT_AVAILABLE | UNVERIFIED (package importable, not verified) |
| `backtest_assessment_ref`, `execution_stress_assessment_ref` | None | None (the contract refuses a ref while not VERIFIED) |
| `prediction_status` | ABSTAIN | ABSTAIN |
| request record `backtest.result`, no store | BACKTEST_NOT_AVAILABLE | BACKTEST_STORE_MISSING |
| request record, store present | not read without `predictive.backtest_db` | read read-only from the package's default store: ASSESSMENT_UNVERIFIED (context, veto when fatal or untradeable), UNTESTED (no row for the mint), ASSESSMENT_REFUSED (schema, identity, time) |
| pass summary | `backtest_status` | plus `backtest_store.state` (OK, BACKTEST_STORE_MISSING, SCHEMA_MISMATCH, STORE_UNREADABLE) |
| scout section | `- Backtesting: BACKTEST_NOT_AVAILABLE` | `- Backtesting: UNVERIFIED; store BACKTEST_STORE_MISSING` and per opportunity `backtest BACKTEST_STORE_MISSING` |
| report system line and FACT | `Backtesting: BACKTEST_NOT_AVAILABLE`; "not installed on this line" | `Backtesting: UNVERIFIED`; "installed but not verified by a phase" with the new unblock text |
| report per opportunity | `backtest: BACKTEST_NOT_AVAILABLE (installed state BACKTEST_NOT_AVAILABLE)` and UNKNOWN "...: BACKTEST_NOT_AVAILABLE" | `backtest: BACKTEST_STORE_MISSING (installed state UNVERIFIED)` and UNKNOWN "...: BACKTEST_STORE_MISSING" |
| alerts | | unchanged (both alert goldens byte-identical) |

The Phase 18 goldens were regenerated (`python -B audits/predictive-intelligence/phase_18/probes/run_reports.py goldens OUTDIR` gives the same bytes): 46 lines changed in 5 report files, every one a backtest line above. Forward depth snapshot rows are still read only through a configured `predictive.depth_db` and only as post-decision observations (backtesting RUNBOOK, "For the predictive adapter"); the depth pin of `12f278b` equals the installed migration 2 (new test).

## Checks (on the tree of `6ea454d`)

| Check | Command | Exit | Result |
|---|---|---|---|
| Full suite at the merge commit, before the adapter change | `python -m pytest tests -q` | 1 | 50 failed, 2,473 passed, 1 skipped: the two known clock tests plus 48 that asserted BACKTEST_NOT_AVAILABLE, the pre-merge CLI or pins, or reproduced pre-merge outputs |
| Full suite | `python -m pytest tests -q` | 1 | 2 failed, 2,526 passed, 1 skipped; the two failures are the known clock-dependent `test_catalyst.py::test_dedup_corroboration_resurface_denial` and `test_catalyst_firecrawl.py::test_page_history_and_spend_survive_a_new_session_through_the_state_export` |
| Reproductions | `python -m pytest tests/test_predictive_reproductions.py -q` | 0 | 6 passed (private stores present; runners see the backtest package hidden, the state of their commits) |
| Release e2e | `python tools/release_e2e.py` | 0 | PASS, 78 of 78, network attempts 0, tracked files changed 0 (`logs/release_e2e.log`) |
| Content guard | `python -m memelab social guard` | 0 | 3,850 files scanned, 0 violations (`logs/social_guard.log`) |
| Phase 06 seal | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | 0 | `"problems": []` |
| Release docs check | `python -B audits/predictive-intelligence/phase_21/probes/release_docs_check.py OUT.json` | 0 | ok true, 8 documents |
| Backtesting Phase 00 counterexamples | `python audits/backtesting/testing/p00_counterexamples.py` | 0 | 3 of 3 reproduced |
| Backtesting builder and collector mutation sets (17 sets: collector, p05 to p16_repair2, p17_builder) | `python audits/backtesting/testing/mutate.py SET.json` each | 0 each | 269 of 269 caught, every unmutated baseline passes |
| Backtesting reviewer set p17 | same | 1 then 0, 0 | first run: P17-2 SURVIVED because its killer test skipped ("the filesystem gave the new file another inode", filesystem-dependent; the same test passes or skips run to run on `69bc5c3` too); two reruns 2 of 2 caught |
| Backtesting reviewer set p16r4 | same | 1 | baseline 5 failed (`test_p16r3_repair_attacks.py::test_r3_fresh_database_burst_repeated[0..4]`), 8 caught, R4-9 not applicable; byte-identical result on a clean checkout of `69bc5c3` (`logs/pristine_69bc5c3_*`): a pre-existing state of that branch in this environment, not caused by the merge |
| Release audit with history, single-branch clone | `git clone --no-local --single-branch -b feature/predictive-intelligence REPO CLONE && python tools/release_audit.py --history` | 0 | "Needs action: no.", 5,324 blobs, 0 history findings, 14 reviewed |

Not run: the backtesting branch's `audits/backtesting/release/p17_clean_install.sh` (a fresh-install script for that module; the fresh-environment checks of this line are `phase_21/probes/release_checks.sh`, rerun when the merge is pushed).

## The reviewed history blob (D-BT-016, PI-D-049 item 6)

Blob `acbc9c9016`, `audits/backtesting/research/smoke/etcherfx__sol-trade/output.txt` line 42, rule key_material_field, is now reachable from this branch (it is also in the tracked tree). It is the environment variable name SOLTRADE_PRIVATE_KEY quoted by a static scan, not a key value. It is handled by the existing EXPLAINED entry of D-BT-016 that the merge brought into `tools/release_audit.py`: listed as reviewed in both the tree and the history sections of the audit (`logs/release_audit_history_single_branch.md`), not suppressed, not removed from history.

## Files

- `logs/`: every log named above, `head_checked.txt`.
