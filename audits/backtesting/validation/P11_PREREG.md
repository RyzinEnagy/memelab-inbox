# Phase 11 validation pre-registration

Written 2026-10-23 before any validation run on the real corpus. The sha256 of this file is logged in `testing/logs/p11_prereg.sha256`.

## Data

Universe `lab_state_history` (Solana), tokens built by `runner.build_tokens` (point-in-time pool basis, first bar versions, lab liquidity observations, per-pool fees). Dataset hash recorded by each run. Delisted, rugged and dead tokens stay in (G06).

## Split (decision time, UTC)

t0 = 2026-10-07 00:00 (1791331200), t1 = 2026-10-23 16:00 (1792771200). Fractions 0.50 / 0.25 / 0.25: train to 2026-10-15 08:00, validation to 2026-10-19 12:00, sealed test to t1. Embargo 2 days before each window end (the longest default hold is 48 hourly bars), so no trade opened in one window can be judged with the next window's bars. Engine: `EngineConfig()` defaults. Theses known at the lab's record time; one sensitivity run of LAB_STATUS with theses known at their first commit.

## Strategies and grids (every point counts as a trial)

| Strategy | Grid | Trials |
|---|---|---|
| LAB_STATUS | min_score 55; min_score 65; min_score 55 with statuses ENTRY CONDITIONS MET and NEAR ENTRY only | 3 |
| BREAKOUT_CLOSE | lookback 12 or 24, vol_mult 1.0 or 1.5 | 4 |
| MOMENTUM | min_roc 0.05 or 0.10, min_bar_volume_usd 2,000 or 10,000 | 4 |
| BREAKOUT_RETEST, RECLAIM, TREND_HHHL, ABSORPTION_BREAK | defaults | 1 each |
| Overfit control: RANDOM_ENTRY p = 0.02 | seeds 0 to 39 (pick the luckiest in training) | 40 |

Total trials: 55. Baselines on the sealed test under identical execution: NO_TRADE, ENTER_AT_DISCOVERY, RANDOM_ENTRY (seed 7), MA_CROSS.

## Rules

Tuning on train only, choice = highest training mean return among configurations with at least 8 training trades. The choice is frozen (sha256) before the sealed test is read, once. Verdicts: fewer than 30 sealed-test trades -> INSUFFICIENT_SAMPLE (no performance claim); else CANDIDATE_EDGE_OUT_OF_SAMPLE only if the day-block bootstrap 95% interval of the mean trade return is above 0 and above the best baseline mean and the overfit flag is off; otherwise NO_EVIDENCE_OF_EDGE. Holm correction at 0.05 across strategies on the sealed-test one-sided p-values. Deflated Sharpe only if a sealed test has at least 100 trades. Walk-forward check: BREAKOUT_CLOSE grid, 3 expanding folds, 2-day embargo. Regime split of sealed-test trades by SOL/USD 24 h move known at entry.

## Expected

With a 17-day universe the sealed test spans about 2 days of decisions. INSUFFICIENT_SAMPLE is the expected verdict for most or all strategies; that is a valid result, not a failure.
