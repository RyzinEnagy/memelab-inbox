# PHASE 11: statistical validation and strategy-selection discipline

State: PASS (the gate requires discipline and honest verdicts, not a positive result). Date 2026-10-23. Entry gate: Phase 10 PASS at 941e4ed (engine and runner tests 22 passed, 14/14 mutations, full suite C-1 only, release e2e PASS 78/78).

## Changed files

- New: `memelab/backtest/validation.py` (blocked chronological splits with embargo, train-only tuning, frozen choice and one-time sealed test, baselines under identical execution, Wilson, day-block bootstrap with a 5-day minimum, one-sided bootstrap p-value, Holm limited to eligible samples, deflated Sharpe only at n >= 100, overfit flag, regime breakdown, expanding walk-forward).
- Tests: `tests/test_backtest_validation.py` (13).
- Evidence: `audits/backtesting/validation/P11_PREREG.md`, `p11_validate.py`, `p11_results.json`, `p11_results_pass1.json`, `VALIDATION.md`; `testing/p11_mutations.json`, logs, `testing/logs/p11_prereg.sha256`.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_backtest_validation.py -q` | 0 | 13 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p11_mutations.json` | 0 | 11 of 11 caught |
| `python audits/backtesting/validation/p11_validate.py` | 0 | 8 strategies INSUFFICIENT_SAMPLE; walk-forward BREAKOUT_CLOSE pooled OOS 32 trades, mean -7.1% |

## Gate

G06 (dead token counted as a total loss, not dropped), G22 (Phase 09 placebo), G26 (tiny samples never significant; strengthened after the real-data defect), G27 (trials counted, choice frozen, winner's curse reported, overfit flag; real-data fold 1 shows it), G28 (baselines on the same window and execution). No performance claim is made: every sealed test is below 30 trades.

## Bounded loop

Pass 1 (real data): BREAKOUT_RETEST "significant" on 6 trades over 3 days. Repair: minimum day blocks and Holm eligibility. Pass 2: rerun, no claims. Mutation pass: the walk-forward tuning bound was reported but not shared with the code that used it; one variable now drives both (M11-8 caught). Negative control: the best of 40 random seeds (overfit control) lost 29% in validation after -1% in training; a synthetic regime-change test proves the overfit flag fires when training gains vanish.

## Independent negative review

Caught: falsely narrow intervals from few days (M11-1), tiny samples in Holm (M11-2), sealed test read twice (M11-3), tuning on validation (M11-4), no embargo (M11-5), verdict ignoring sample size (M11-6), overfit flag disabled (M11-7), walk-forward tuning on its own out-of-sample block (M11-8), regime from a later price (M11-9), deflated Sharpe on small samples (M11-10), frozen config changed after the test (M11-11).

## Limitations

17 days of history. Sealed tests of 0 to 9 trades. One regime (SOL rising) dominates the test window. Results describe this lab's discoveries under the stated cost assumptions only.

NEXT ELIGIBLE PHASE: 12.
