# PHASE 17: release hardening, documentation and decision memo

State: PASS, decision CONDITIONAL RELEASE (scenario-only research mode). Date 2026-10-23. The release remains conditional on Elving accepting G16 and G27 (RELEASE_REPORT.md). Nothing is deployed, no order path exists, and no scheduled task was created.

Entry gate: Phase 16 PASS for scenario-only research mode at f50b24d, reproduced. The full suite gave 1024 passed plus C-1, and every mutation set was caught.

## Deliverables

- docs/backtesting/RELEASE_REPORT.md: decision, evidence without inflated claims, disclosed limitations, open defects, final hashes, risk disclaimer, shadow-mode instructions, sign-offs.
- docs/backtesting/RUNBOOK.md:
  - turn on and off, and crisis shutdown of the stress module only;
  - WAL-safe backup and recovery;
  - scenario config;
  - manual replays, backfills and the routine bar refresh;
  - shadow-mode calibration;
  - how to read the output, and quality statuses;
  - diagnostics and source outages;
  - costs and limits, storage, migration recovery.
- docs/backtesting/LICENSE_ATTRIBUTIONS.md: bill of materials (no third-party runtime dependency added), verified version matrix and honest support matrix (Linux only), ideas and their pinned sources, audit-only tools, services, and the Maxun closure with the AGPL decision.
- docs/backtesting/requirements-test.txt: pinned pytest 9.1.1 and numpy 2.5.3.
- audits/backtesting/release/p17_clean_install.sh and p17_fixture_import.py: clean-clone reproduction. Log: release/logs/p17_clean_install.log.

## Code changes made in this phase (from the independent review)

- M2:
  - an outcome window whose pool was last fetched before the window closed now stays PENDING (NOT_FETCHED_SINCE_WINDOW_END) instead of reading as cut short;
  - OHLCV fetches record their fetch time (OHLCV_FETCHED);
  - new `backtest refresh` (network, read-only, budgeted) fetches bars for waiting windows.
  - On a corpus copy judged 3 days after the last fetch, 51 such windows now wait instead of being recorded as cut short or empty.
- M1: new `backtest backup --to PATH` (sqlite backup API, safe with WAL); the runbook's recovery steps use it.
- L8: run files go next to the database given with `--db`.
- Tests: fetch evidence, refresh with and without new bars, WAL-safe backup, run-file location, and same-inode file replacement (C4).
- R3 (from the re-check): run files follow MEMELAB_BT_DB when `--db` is not given.
- Guard set: audits/backtesting/testing/p17_builder_mutations.json, 8 of 8 caught (log: testing/logs/p17_builder_r.log).

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests -q` | 1 | 1030 passed, 1 failed (C-1, pre-existing) |
| every mutation set p05 to p16, p16_repair, p16_repair2, p17_builder | 0 | all caught (7+12+9+14+11+11+14+11+12+24+20+22+13+10+24+8 = 222) |
| reviewer's p16r4 and p17 sets | 1 / 1 | p16r4 8 of 9 caught, the ninth (R4-9) not applicable because its line was replaced by the C4 fix; p17 1 of 2, the second's killer test skipped in the harness copy. Both are covered by builder mutations R16d-9, R16d-10 and P17-7, all caught. Log: testing/logs/p17_reviewer_sets.log |
| `bash audits/backtesting/release/p17_clean_install.sh <repo> <out>` | 0 | RESULT PASS at bc7ce30, 9 steps (below), document checker 72 of 72 |
| `python tools/release_audit.py` / `python tools/release_e2e.py` | 0 / 0 | Needs action: no / PASS 78 of 78 |

Clean install steps:
1. migration from empty;
2. rollback and re-apply;
3. offline import of the real GeckoTerminal responses;
4. a deterministic run twice (MISS, then HIT, same ledger);
5. an opportunity report with adversarial scenarios;
6. policy off against on (only the one backtest line differs; the lab database is byte-identical);
7. the backtest tests in the clean clone;
8. the release audit;
9. the reviewer's document checker against the code, the evidence and a corpus copy.

## Independent review

The reviewer's report is audits/backtesting/testing/P17_REVIEW.md.

First sign-off: CONDITIONAL RELEASE agreed, with a fix list.
- Two Medium procedure defects: M1, the backup steps could lose WAL data; M2, shadow tracking without a bar refresh recorded misleading outcomes.
- Low items L1 to L15.

All were fixed except L15. L15 asks that the push, bundle and zip wait for Elving's authorization. Elving gave that authorization at the start of this work: the "Both" delivery answer, which was to push a new feature/backtesting branch through the Composio Git Data API route (fast-forward, no merge, no PR merge, no main changes) and to put a git bundle plus a zip in D:\memelab.

The reviewer re-checked the fixes at efd890d, offline, and AGREED (P17_REVIEW.md, "Re-check of the fixes at efd890d"; logs testing/logs/p17r_*.log). It reproduced the clean install, the full suite (1029 passed plus C-1 at that commit), 221 of 221 builder mutations, the checker's 72 of 72, the cohort figures at all 6 real decision points, and release_e2e 78 of 78. It confirmed M1 and M2 by repeating its own reproductions, and confirmed the non-circular release-commit check.

It left seven Low residuals. R3 (run files ignore MEMELAB_BT_DB), R4 (the install script did not check the repeated run) and R5 (every .md counted as prose, though a test reads MAXUN_ADOPTION.md) are fixed. R1 (refresh covers only corpus tokens) and R2 (a fetch records only its newest bar) are documented in RUNBOOK.md and listed as open Low items in the release report. R6 (its own same-inode test can skip) and R7 (wording written before the re-check ran) need no change. The Firecrawl count is corrected to about 32.

The reviewer's own wrong-but-plausible outputs (a misspelled flag, a wrong hash digit, a transposed count, a wrong default) slipped past the existing release checks. Its document checker catches all four, and the clean-install script now runs that checker.

One checker item was circular: "the clean-install log was made at the release commit". The log is made from a commit and then committed, so HEAD always moves one step past it. The check now passes when the log was made at HEAD, or at a commit after which only prose (.md) and the log itself changed (bc7ce30). The release report names the run id with the commit it was made at.

Clean-install run at bc7ce30: RESULT PASS. Run id afa0d2f66467 (MISS, then HIT), ledger f9d7dd89c462, 244 backtest tests passed, "Needs action: no", and the document checker passed 72 of 72.

## Not proven

- Behavior on Windows and macOS.
- A second keyless historical price source.
- Exact historical pool state.
- Any edge for any strategy.

NEXT ELIGIBLE PHASE: none in the package. The remaining steps are Elving's decisions (G16, G27, the conditional release, any scheduled shadow tracking), plus delivery: push, bundle and zip.
