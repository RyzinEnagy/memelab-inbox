# Historical replay of research signals against matched controls

FIXTURE DEMO: a synthetic, seeded world. Tokens, sources, posts, wallets, trending lists and prices are invented. Nothing here is evidence about any real token or source, and nothing is a trade record.

Reproduce: `python -m memelab social replay demo`

Synthetic world with planted pumps, informative and noise posts, reposts, ingest duplicates, leakage canaries (posts published before a pump but first available after it), a huge winner, delisted and illiquid tokens, revised candles and a source that sells right after posting.

What kind of evidence this is: a historical replay (backtest) on stored data, run with a causal cutoff clock. It is not a forward test. Signals whose inputs the lab actually captured at decision time are counted separately (test split, primary horizon: 30); outcome prices are provider history in every case. Positions are hypothetical (Phase 16 evaluation size); nothing here is a trade instruction.

## Data and coverage

label synthetic world seed 17; fixture: yes; coverage version synthetic-17-v1; engine replay-v1, rules replay-rules-v1

data clock ends 2026-08-31T00:00:00Z; input sha256 2cea0be1c2ec5a2a; policy sha256 b204fc4086786dc0

```
posts 1289 (reposts 573, content duplicates 0), wallet events 119, trending entries 2300
market observations 220632 on 79 tokens; tokens known 79
excluded candles: AFTER_DATA_END x75
excluded posts: AFTER_DATA_END x2, DUPLICATE_POST_ID x10
universe: every invented token, delisted ones included; includes delisted tokens: True
provider synth-candles: kind PRICE, publication lag 120 s, window 2026-08-01T00:00:00Z to 2026-08-31T00:00:00Z
provider synth-social: kind SOCIAL, publication lag None s, window 2026-08-01T00:00:00Z to 2026-08-31T00:00:00Z
provider synth-trending: kind TRENDING, publication lag 60 s, window 2026-08-02T00:00:00Z to 2026-08-31T00:00:00Z
```

## Chronological splits

```
train       2026-08-01T01:09:23Z to 2026-08-16T00:34:41Z   labels as known at 2026-08-16T00:34:41Z
validation  2026-08-16T00:34:41Z to 2026-08-23T12:17:20Z   labels as known at 2026-08-23T12:17:20Z
test        2026-08-23T12:17:20Z to 2026-08-31T00:00:00Z   labels as known at 2026-08-31T00:00:00Z
embargo: a sample whose outcome window crosses its split boundary is purged, never moved
decision evidence spans 718.8 h; the primary horizon needs 24 h plus lag and exit wait inside a split
```

Order of operations:

- 1. thresholds chosen on train labels only (label clock 2026-08-16T00:34:41Z); validation and test labels locked
- 2. configuration frozen: sha256 a8aa58bac804a051c973c056e714a6390495bb24cac1f5456a220d28faf25c6e
- 3. validation evaluated with the frozen configuration (label clock 2026-08-23T12:17:20Z)
- 4. test evaluated once (label clock 2026-08-31T00:00:00Z)

## Tuning (train split only)

configurations tried: 16. Held-out splits were not used to choose any threshold.

```
* INDIVIDUAL:max_capture_lag_s=900                         train signals   91  purged    7  with controls   52  median rel +3.7%
  INDIVIDUAL:max_capture_lag_s=3600                        train signals   91  purged    7  with controls   52  median rel +3.7%
  INDIVIDUAL:max_capture_lag_s=21600                       train signals   91  purged    7  with controls   52  median rel +3.7%
  CONVERGENCE:min_sources=2,window_s=21600                 train signals   52  purged    3  with controls   30  median rel +64.7%
  CONVERGENCE:min_sources=2,window_s=86400                 train signals   68  purged    5  with controls   38  median rel +35.2%
  CONVERGENCE:min_sources=3,window_s=21600                 train signals   28  purged    3  with controls   15  median rel +80.1%
  CONVERGENCE:min_sources=3,window_s=86400                 train signals   41  purged    3  with controls   22  median rel +77.2%
  CONVERGENCE:min_sources=4,window_s=21600                 train signals   13  purged    0  with controls    8  median rel +84.8%
* CONVERGENCE:min_sources=4,window_s=86400                 train signals   22  purged    1  with controls   13  median rel +91.8%
  SOCIAL_WALLET:min_sources=1,wallet_window_s=21600        train signals   29  purged    1  with controls   19  median rel +40.1%
  SOCIAL_WALLET:min_sources=1,wallet_window_s=86400        train signals   32  purged    1  with controls   22  median rel +40.0%
* SOCIAL_WALLET:min_sources=2,wallet_window_s=21600        train signals   22  purged    1  with controls   16  median rel +49.6%
  SOCIAL_WALLET:min_sources=2,wallet_window_s=86400        train signals   27  purged    1  with controls   20  median rel +44.8%
* TRENDING:max_rank=10,min_mentions=3,window_s=86400       train signals  239  purged   17  with controls  129  median rel +1.5%
  TRENDING:max_rank=10,min_mentions=5,window_s=86400       train signals  236  purged   15  with controls  128  median rel +1.5%
  TRENDING:max_rank=10,min_mentions=10,window_s=86400      train signals  229  purged   12  with controls  127  median rel -0.1%
```

`*` chosen. Basis: INDIVIDUAL highest train median relative return (conservative lens) among configurations with enough train values; CONVERGENCE highest train median relative return (conservative lens) among configurations with enough train values; SOCIAL_WALLET highest train median relative return (conservative lens) among configurations with enough train values; TRENDING highest train median relative return (conservative lens) among configurations with enough train values.

## Results at the primary horizon (24h), conservative lens

Intervals are adjusted for 16 comparisons (4 strategies x 4 horizons, Bonferroni). Relative = signal net modeled return minus the median of matched controls at the same decision time. Precision = share of signals that beat their controls. Estimates below the reporting minimum are not shown.

```
INDIVIDUAL    validation signals   37 labeled   33 coverage  85% with controls   20 executable  82% inputs captured live 23/37
                         median rel +6.3% CI [-10.6%, +60.1%]  precision 65% CI [34%, 87%]  mean +17.0% without top +11.1%
                         median net -3.6%  measured-only median rel +6.6%  MAE median -12.6% worst -65.6%  delisted 1  non-exec 5
                         no relative return: NO_VALID_CONTROLS x8
INDIVIDUAL    test       signals   40 labeled   36 coverage  86% with controls   17 executable  86% inputs captured live 24/40
                         median rel +2.4% CI [-31.9%, +118.3%]  precision 53% CI [23%, 81%]  mean +26.6% without top +17.2%
                         median net -7.7%  measured-only median rel +2.4%  MAE median -12.0% worst -46.9%  delisted 0  non-exec 5
                         no relative return: NO_VALID_CONTROLS x14
CONVERGENCE   validation signals    8 labeled    7 coverage 100% with controls    5 executable 100% inputs captured live 2/8
                         not shown: 5 values with matched controls, at least 10 needed
                         no relative return: NO_VALID_CONTROLS x2
CONVERGENCE   test       signals    5 labeled    5 coverage 100% with controls    3 executable 100% inputs captured live 0/5
                         not shown: 3 values with matched controls, at least 10 needed
                         no relative return: NO_VALID_CONTROLS x2
SOCIAL_WALLET validation signals   12 labeled   10 coverage  90% with controls    6 executable  90% inputs captured live 4/12
                         not shown: 6 values with matched controls, at least 10 needed
                         no relative return: NO_VALID_CONTROLS x3
SOCIAL_WALLET test       signals   11 labeled   11 coverage 100% with controls    9 executable 100% inputs captured live 3/11
                         not shown: 9 values with matched controls, at least 10 needed
                         no relative return: NO_VALID_CONTROLS x2
TRENDING      validation signals  121 labeled  104 coverage  91% with controls   61 executable  91% inputs captured live 10/121
                         median rel +0.5% CI [-5.1%, +14.5%]  precision 52% CI [34%, 70%]  mean +12.0% without top +9.0%
                         median net -5.4%  measured-only median rel +0.5%  MAE median -8.5% worst -59.2%  delisted 0  non-exec 9
                         no relative return: NO_VALID_CONTROLS x34
TRENDING      test       signals  117 labeled  107 coverage  95% with controls   66 executable  95% inputs captured live 3/117
                         median rel +2.2% CI [-4.3%, +9.7%]  precision 58% CI [40%, 74%]  mean +11.8% without top +8.6%
                         median net -7.2%  measured-only median rel +2.2%  MAE median -9.2% worst -50.6%  delisted 0  non-exec 5
                         no relative return: NO_VALID_CONTROLS x36
```

## Verdicts

- (a) individual analyst signal: one original LONG post: **INSUFFICIENT_SAMPLE**. 17 test signals with matched controls; 30 needed.
- (b) independent convergence: original LONG posts from several independence groups: **INSUFFICIENT_SAMPLE**. 3 test signals with matched controls; 30 needed.
- (c) social + wallet confirmation: independent posts plus a linked-wallet buy: **INSUFFICIENT_SAMPLE**. 9 test signals with matched controls; 30 needed.
- (d) raw mention / trending baseline: raw mentions incl. reposts, or a provider trending list: **CANNOT_VALIDATE_YET**. The adjusted interval of the median relative return includes zero: not distinguishable from matched controls.

Test minus trending baseline (descriptive only, not a test): INDIVIDUAL +0.2%; CONVERGENCE n/a; SOCIAL_WALLET n/a

## Secondary horizons (exploratory, test split)

```
INDIVIDUAL    1h n=18 -0.2% | 6h n=18 -0.5% | 24h n=17 +2.4% | 72h n=13 +31.7%
CONVERGENCE   1h n=3 - | 6h n=3 - | 24h n=3 - | 72h n=2 -
SOCIAL_WALLET 1h n=9 - | 6h n=9 - | 24h n=9 - | 72h n=5 -
TRENDING      1h n=73 +0.4% | 6h n=71 -0.3% | 24h n=66 +2.2% | 72h n=44 +6.4%
```

## Bias and caveats

- INDIVIDUAL: suppressed (contradictory evidence): CONFLICTING_DIRECTION x57
- CONVERGENCE: suppressed (contradictory evidence): CONFLICTING_DIRECTION x21
- SOCIAL_WALLET: suppressed (contradictory evidence): CONFLICTING_DIRECTION x20, LINKED_WALLET_SOLD x3
- TRENDING: none flagged
- Selection: only signals the replay itself generated from stored evidence are evaluated; posts the collectors never saw cannot be judged, and the collected sources are not a random sample of all sources.
- Multiple testing: 16 configurations were tried on train; held-out results are reported for the chosen one only. Secondary horizons are exploratory.
- Missing prices are never filled in. A delisting before the exit counts as a total loss in the conservative lens for signals and controls alike; the measured-only lens is shown beside it.

## Leakage check (truncation invariance)

The replay was repeated on the data as it existed at each boundary (every record available later removed). Signals decided by then, and the train metrics used for tuning, must not change.

```
train boundary       at 2026-08-16T00:34:41Z: identical
validation boundary  at 2026-08-23T12:17:20Z: identical
tuning               at 2026-08-16T00:34:41Z: identical
```

No leakage detected: yes

## Audit

cutoff accesses 88337, records checked 1006553, records from after a cutoff 0 (any would have stopped the run with LeakageError)

result sha256 685a49734ac2e5111a770e98fccf9a7e65764f8e7a1cf8be7a9150b0cb6caa9c

FIXTURE DEMO: a synthetic, seeded world. Tokens, sources, posts, wallets, trending lists and prices are invented. Nothing here is evidence about any real token or source, and nothing is a trade record.

