# PHASE 15: post-discovery outcomes, calibration and drift

State: PASS. Date 2026-10-23. Entry gate: Phase 14 PASS at 30863a6, reproduced (report and assess tests 49 passed; 20 of 20 Phase 14 mutations caught).

## Changed files

- New: `memelab/backtest/outcomes.py`:
  - frozen opportunities (lab theses, screened-out rejections, stored assessments);
  - point-in-time outcomes at 1, 6, 24 and 72 h with COMPLETE, CENSORED, NOT_OBSERVABLE and PENDING states;
  - append-only rows with supersede links;
  - scheduled tracker with a minimum interval, deduplication and exponential retry for optional fetches;
  - calibration by six segments, all known at decision time;
  - exit-model reconciliation against the lab's own later snapshot;
  - drift and staleness warnings;
  - collector health for the chosen collectors (no Maxun metrics, because it was not adopted);
  - shadow evaluation (not saved, no order path);
  - re-evaluation proposals, with in-place retuning refused;
  - a replayable daily report.
- `memelab/backtest/cli.py`: `backtest outcomes {track,calibrate,drift,reconcile,daily,shadow}`.
- Docs: `docs/backtesting/OUTCOMES.md`.
- Tests: `tests/test_backtest_outcomes.py` (14).
- Evidence: `audits/backtesting/outcomes/p15_outcomes.py`, `p15_outcomes.json`, `CALIBRATION_24H.md`, `DAILY_SAMPLE.md`; `testing/p15_mutations.json` and its log.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_backtest_outcomes.py -q` | 0 | 14 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p15_mutations.json` | 0 | 22 of 22 caught |
| `python audits/backtesting/outcomes/p15_outcomes.py` (copy of the real corpus) | 0 | 1,023 opportunities, 4,092 window rows, about 54 s |
| `python -m pytest tests -q` | 1 | 1 failed (C-1 only), 990 passed |
| `python tools/release_audit.py` / `python tools/release_e2e.py` | 0 / 0 | Needs action: no / PASS 78 of 78 |

## Real outcomes (research corpus, as of 2026-10-23 17:34 UTC)

The study covers 1,023 frozen opportunities over 686 mints: 382 lab theses and 641 screened-out rejections. Segments use 65 contemporaneous launch-monitor records from the lab's git history.

| Window | Complete | Censored | Not observable | Pending | Median close (complete) | Down 50% or more (observed, 95% interval) |
|---|---|---|---|---|---|---|
| 1 h | 417 | 111 | 495 | 0 | -0.4% | 1.7% (0.8% to 3.4%) |
| 6 h | 421 | 107 | 495 | 0 | -2.2% | 7.3% (5.3% to 10.1%) |
| 24 h | 385 | 133 | 463 | 42 | -5.3% | 20.0% (16.6% to 23.9%) |
| 72 h | 348 | 129 | 433 | 113 | -10.0% | 27.6% (23.7% to 32.0%) |

Selection-bias risk is flagged: 45% of opportunities are not observable, mostly screened-out and EVM mints whose bars were never fetched in Phase 06.

Segments are correlations, not causes. At 24 h:
- token age at the decision separates outcomes most clearly:
  - at least 7 days old: median -4.8%, 5% down by half or more (n 299);
  - under 24 h old: median -55% to -68%, 55% to 61% down by half (complete samples under 30, INSUFFICIENT_SAMPLE);
- graduation records known at the decision: median +29.5%, but 60% fell by half or more within the window (17 complete, INSUFFICIENT_SAMPLE);
- every lab-status cohort except REJECTED is under 30 complete outcomes.

Exit-model reconciliation covered 36 pairs where the lab itself observed liquidity within 2 h of the window end. The median error of the stress model (decision liquidity times the square root of the price ratio) was +0.04%, with a 10th to 90th percentile range of -9.9% to +24.2%. 303 opportunities had no later lab snapshot, so their exit could not be reconciled. Exact historical pool state stays SOURCE_BLOCKED.

Drift: no warnings. Shadow evaluation of BREAKOUT_CLOSE after the sealed test made 0 trades, because no data exists after it yet. Stored runs were unchanged before and after.

## Gate

- G06: tokens that collapsed or stopped trading stay in the study.
  - The real 3GVSN8 fixture is down 50% or more at 24 h and down more than 99% at 72 h.
  - Missing outcomes are recorded with reasons: bars ending early (CENSORED, drawdown a lower bound), no bars after the decision, no bars stored (NOT_OBSERVABLE), no pool basis.
  - Screened-out rejections stay in the study, and a selection-bias flag is raised.
- G08: catalyst segments use only records available at the decision.
  - A capture made later with an earlier claimed publication time does not count.
  - A record seen an hour later does not count.
  - A later deletion does not erase what was known.
  - Catalysts never change an outcome.
- G32: the daily report is replayed from frozen records.
  - It is byte-identical for the same as-of after later bars and a provider revision arrive (tested, and on the real corpus).
  - Decision columns never change at a later as-of; only outcome columns can.
- Prior signed runs:
  - stored runs, assessments and universe records are byte-identical after tracking, later data, calibration and drift;
  - UPDATE and DELETE on runs, assessments and outcomes are refused by append-only triggers.

## Bounded loop

Pass 1 had four test failures:
1. The capture store refuses an unverified mint, so the test data was wrong.
2. A pool appearing days later reads as NO_BARS_STORED at an early as-of; the test now uses a later as-of.
3. The collapsed token fell 76% within 24 h and more than 99% by 72 h; the test now checks each.
4. Coverage drift had counted windows without bars as covered. Coverage now means the window has price bars.

Pass 2 had one surviving mutation (M15-8). The G08 test could not tell a late launch record from an early capture. It now checks a mint with no captures.

Pass 3: all green.

## Independent negative review

Wrong-but-plausible outputs invented and caught (22 mutations):
- bars after the window (M15-1) or not yet available (M15-2) used; unfinished window reported (M15-3);
- not-observable outcomes dropped (M15-4); screened-out tokens left out (M15-5);
- duplicate rows on rerun (M15-6); supersede link lost (M15-7);
- catalysts judged by claimed publication time (M15-8, M15-9);
- tracker not rate limited (M15-10); retry not exponential (M15-11);
- daily report reads later outcomes (M15-12) or is not ranked by the lab score (M15-13);
- censored windows left out of the drawdown share (M15-14); small segments called reportable (M15-15);
- in-place retune allowed (M15-16); shadow saved as a run (M15-18); slippage model not price-scaled (M15-19);
- coverage, stale-pending and calibration drift not warned (M15-17, M15-20, M15-22);
- stored assessments not tracked (M15-21).

## Robot and collector checkpoint

Maxun was not adopted (Phase 06A), so no Maxun health metrics are reported. Monitoring covers the chosen collectors in `bt_capture_provenance`:
- late arrival, duplicates and misattribution risk;
- extractor versions and incomplete extractions;
- failed runs and the longest gap.

The research corpus holds no captures yet, so the real report says NO_DATA. A test shows the metrics on captured rows.

## Limitations

- 45% of opportunities have no bars (selection bias, flagged).
- Most segments are under 30 complete outcomes.
- Exit reconciliation rests on the lab's own liquidity snapshots, not historical pool state.
- The corpus spans 17 days, so the drift checks have little history to compare.
- No fetch was run during tracking. The fetch hook is tested with a failing fake and is bounded by `max_fetches`.

NEXT ELIGIBLE PHASE: 16.
