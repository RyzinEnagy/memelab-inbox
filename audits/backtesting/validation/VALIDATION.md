# Statistical validation on the real corpus (Phase 11)

Pre-registration: `P11_PREREG.md` (sha256 `d0b3686f...`, logged before any run; the results file repeats the hash). Script: `python audits/backtesting/validation/p11_validate.py` (exit 0, about 2.5 minutes). Results: `p11_results.json`. Dataset hash at the cutoff: `35f836f372c4...` over 256 tokens. 55 trials in total.

Split by decision time: train 2026-10-07 00:00 to 10-15 08:00, validation to 10-19 12:00, sealed test to 10-23 16:00, each with a 2-day embargo before its end.

## Sealed-test results

| Strategy | Chosen on train | Train mean | Validation n / mean | Sealed test n / mean | Verdict |
|---|---|---|---|---|---|
| LAB_STATUS | min_score 65 | -1.2% | 1 / +4.0% | 0 | INSUFFICIENT_SAMPLE |
| BREAKOUT_CLOSE | lookback 12, vol_mult 1.5 | -6.9% | 16 / -6.6% | 6 / -3.1% | INSUFFICIENT_SAMPLE |
| MOMENTUM | min_roc 0.05, floor 2,000 USD | -7.7% | 10 / -10.5% | 7 / -26.6% | INSUFFICIENT_SAMPLE |
| BREAKOUT_RETEST | defaults | -6.1% | 5 / -1.1% | 6 / +3.0% | INSUFFICIENT_SAMPLE |
| RECLAIM | defaults | -18.1% | 4 / -19.8% | 4 / -8.3% | INSUFFICIENT_SAMPLE |
| TREND_HHHL | defaults | -39.7% | 5 / -5.1% | 3 / -54.6% | INSUFFICIENT_SAMPLE |
| ABSORPTION_BREAK | defaults | -28.8% | 5 / -24.7% | 3 / -8.5% | INSUFFICIENT_SAMPLE |
| Overfit control: RANDOM_ENTRY, best of 40 seeds | seed 0 | -1.0% | 11 / -29.3% | 9 / -17.6% | INSUFFICIENT_SAMPLE |

Baselines on the same sealed test and execution: NO_TRADE 0 trades; ENTER_AT_DISCOVERY 8 trades, mean -42.2%; RANDOM_ENTRY (seed 7) 8, -7.9%; MA_CROSS 3, -13.5%.

No strategy reached 30 sealed-test trades, so there is no performance claim for any of them, positive or negative. Holm comparison: no strategy eligible. Sensitivity (LAB_STATUS with theses known at their first commit): also INSUFFICIENT_SAMPLE, zero sealed-test trades.

## Walk-forward check (BREAKOUT_CLOSE, 3 expanding folds, 2-day embargo)

| Fold | Chosen | In-sample mean | Out-of-sample n / mean |
|---|---|---|---|
| 1 | lookback 24, vol_mult 1.0 | +6.4% | 10 / -10.2% |
| 2 | lookback 12, vol_mult 1.5 | -6.9% | 16 / -6.6% |
| 3 | lookback 12, vol_mult 1.5 | -10.3% | 6 / -3.1% |

Pooled out of sample: 32 trades, mean -7.1%, day-block bootstrap 95% interval [-13.5%, -1.8%]. Fold 1 is the winner's curse on real data: the best in-sample configuration (+6.4%) lost 10.2% on the next block. Net of the assumed costs, this breakout rule lost money out of sample on this corpus; that is the only interval here that excludes zero, and it is negative.

## Regime split of sealed-test trades

Almost every sealed-test trade happened while SOL/USD was up over the prior 24 h (for example BREAKOUT_CLOSE 6 of 6, RANDOM_ENTRY 8 of 9), so the test window cannot say anything about down regimes.

## A defect found by the real data (pass 1, kept as `p11_results_pass1.json`)

The first run reported BREAKOUT_RETEST as significant after Holm correction (6 sealed-test trades over 3 exit days, bootstrap interval +2.2% to +4.7%, p = 0.0005). Three days of exits make a falsely narrow bootstrap. Fixed: the day-block bootstrap and its p-value now need at least 5 exit days, and the Holm comparison only admits strategies at or above the 30-trade minimum (both were already the pre-registered intent: fewer than 30 trades means no performance claim). Test `test_g26_few_days_and_few_trades_never_produce_significance` and mutations M11-1 and M11-2.

## What would make a claim possible

More history. At the lab's current rate (about 1,900 thesis rows in 17 days, of which a few dozen produce fillable signals per strategy), a sealed test of 30 trades per strategy needs roughly two to three months of new discoveries with the lab's liquidity observations attached. Phase 15 (outcome tracking) accumulates exactly that.
