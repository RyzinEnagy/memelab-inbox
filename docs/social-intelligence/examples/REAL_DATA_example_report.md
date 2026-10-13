# Real-data example report (Phase 18 release)

REAL DATA, captured by the lab's own scheduled runs. Not a fixture. Nothing in it is a trade instruction.

Source: the lab database `data/memelab.sqlite` and the 39 collector files in `inbox/` on `main` at commit `f69a044` (2026-10-12 daily scan), read from a scratch copy. Database sha256 `068287c0d7e45436`, unchanged before and after both commands. No network call was made and nothing was written to the repo.

Reproduce from a scratch folder holding a copy of those files:

```
git archive origin/main data/memelab.sqlite inbox | tar -x -C SCRATCH && cd SCRATCH && cp data/memelab.sqlite ro.sqlite
python -m memelab social brief --db ro.sqlite --as-of 2026-10-12T12:00:00+00:00 --tz America/New_York
python -m memelab social replay run --db ro.sqlite --inbox inbox
```

(Run with the repo on `PYTHONPATH`.) What this shows: the lab has captured real market data (trending lists and candles) but no social posts and no wallet events, and its price history covers about one day. So the brief has nothing to report and every replay strategy is INSUFFICIENT_DATA. That is the correct answer for this data, not a failure.

## Part 1: morning brief on the real lab database

## Morning brief: social narratives, last 24 hours

As of 2026-10-12 08:00 EDT (12:00 UTC). Window: 2026-10-11 08:00 EDT (12:00 UTC) to 2026-10-12 08:00 EDT (12:00 UTC) (24 h).
Data: no narrative snapshot. Source status UNAVAILABLE: social tables not present in this database (social schema not migrated).
Model: not used (status on this machine: model\_not\_configured). The feed is built from stored structure only.

No supported high-priority observations. Reason: social tables not present in this database (social schema not migrated).

---
Research notes only. Nothing here is a trade instruction, a score or a watchlist change; social attention says nothing about whether a token can be bought or sold.
Feed feed-v1, schema memelab.social.feed/1, sha256 8ad1e232403401d8.

## Part 2: historical replay on real stored history

## Historical replay of research signals against matched controls

Real stored history. Where coverage is poor the verdict is 'insufficient sample/data' or 'cannot validate yet'; nothing is extrapolated beyond the data.

What kind of evidence this is: a historical replay (backtest) on stored data, run with a causal cutoff clock. It is not a forward test. Signals whose inputs the lab actually captured at decision time are counted separately (test split, primary horizon: 10); outcome prices are provider history in every case. Positions are hypothetical (Phase 16 evaluation size); nothing here is a trade instruction.

### Data and coverage

label lab database ro.sqlite + collector files inbox; fixture: no; coverage version real-a2fa248e6d60; engine replay-v1, rules replay-rules-v1

data clock ends 2026-10-08T13:55:07Z; input sha256 0205d4694084b412; policy sha256 b204fc4086786dc0

```
posts 0 (reposts 0, content duplicates 0), wallet events 0, trending entries 410
market observations 17063 on 225 tokens; tokens known 225
excluded candles: FUTURE_DATED_AT_CAPTURE x29, UNFINISHED_CANDLE_AT_CAPTURE x108
universe: only tokens the lab's runs happened to fetch; delisted tokens are not tracked; includes delisted tokens: False
provider dexscreener-boosts: kind TRENDING, publication lag None s, window 2026-10-07T17:14:55Z to 2026-10-08T13:45:01Z
provider geckoterminal-ohlcv: kind PRICE, publication lag None s, window 2026-06-10T00:00:00Z to 2026-10-08T14:01:00Z
provider geckoterminal-pools: kind PRICE, publication lag None s, window 2026-10-07T17:14:55Z to 2026-10-07T17:14:55Z
provider geckoterminal-trending: kind TRENDING, publication lag None s, window 2026-10-07T17:14:55Z to 2026-10-07T17:14:55Z
provider geckoterminal-trending1h: kind TRENDING, publication lag None s, window 2026-10-07T17:14:55Z to 2026-10-07T17:14:55Z
provider geckoterminal-trending24: kind TRENDING, publication lag None s, window 2026-10-07T17:14:55Z to 2026-10-07T17:14:55Z
provider lab-snapshot:merged: kind PRICE, publication lag None s, window 2026-10-06T23:48:23Z to 2026-10-07T00:16:35Z
```

### Chronological splits

```
train       2026-10-07T17:14:55Z to 2026-10-08T03:35:01Z   labels as known at 2026-10-08T03:35:01Z
validation  2026-10-08T03:35:01Z to 2026-10-08T08:45:04Z   labels as known at 2026-10-08T08:45:04Z
test        2026-10-08T08:45:04Z to 2026-10-08T13:55:07Z   labels as known at 2026-10-08T13:55:07Z
embargo: a sample whose outcome window crosses its split boundary is purged, never moved
decision evidence spans 20.7 h; the primary horizon needs 24 h plus lag and exit wait inside a split
```

Order of operations:

- 1. thresholds chosen on train labels only (label clock 2026-10-08T03:35:01Z); validation and test labels locked
- 2. configuration frozen: sha256 c2a7309786c5d7435f8598dbeaf79e7dae6de825e832fc1937b16a84b811bc04
- 3. validation evaluated with the frozen configuration (label clock 2026-10-08T08:45:04Z)
- 4. test evaluated once (label clock 2026-10-08T13:55:07Z)

### Tuning (train split only)

configurations tried: 16. Held-out splits were not used to choose any threshold.

```
* INDIVIDUAL:max_capture_lag_s=900                         train signals    0  purged    0  with controls    0  median rel n<8
  INDIVIDUAL:max_capture_lag_s=3600                        train signals    0  purged    0  with controls    0  median rel n<8
  INDIVIDUAL:max_capture_lag_s=21600                       train signals    0  purged    0  with controls    0  median rel n<8
* CONVERGENCE:min_sources=2,window_s=21600                 train signals    0  purged    0  with controls    0  median rel n<8
  CONVERGENCE:min_sources=2,window_s=86400                 train signals    0  purged    0  with controls    0  median rel n<8
  CONVERGENCE:min_sources=3,window_s=21600                 train signals    0  purged    0  with controls    0  median rel n<8
  CONVERGENCE:min_sources=3,window_s=86400                 train signals    0  purged    0  with controls    0  median rel n<8
  CONVERGENCE:min_sources=4,window_s=21600                 train signals    0  purged    0  with controls    0  median rel n<8
  CONVERGENCE:min_sources=4,window_s=86400                 train signals    0  purged    0  with controls    0  median rel n<8
* SOCIAL_WALLET:min_sources=1,wallet_window_s=21600        train signals    0  purged    0  with controls    0  median rel n<8
  SOCIAL_WALLET:min_sources=1,wallet_window_s=86400        train signals    0  purged    0  with controls    0  median rel n<8
  SOCIAL_WALLET:min_sources=2,wallet_window_s=21600        train signals    0  purged    0  with controls    0  median rel n<8
  SOCIAL_WALLET:min_sources=2,wallet_window_s=86400        train signals    0  purged    0  with controls    0  median rel n<8
* TRENDING:max_rank=10,min_mentions=3,window_s=86400       train signals  112  purged  112  with controls    0  median rel n<8
  TRENDING:max_rank=10,min_mentions=5,window_s=86400       train signals  112  purged  112  with controls    0  median rel n<8
  TRENDING:max_rank=10,min_mentions=10,window_s=86400      train signals  112  purged  112  with controls    0  median rel n<8
```

`*` chosen. Basis: INDIVIDUAL no configuration had 8 train values: the first (default) configuration is used, untuned; CONVERGENCE no configuration had 8 train values: the first (default) configuration is used, untuned; SOCIAL_WALLET no configuration had 8 train values: the first (default) configuration is used, untuned; TRENDING no configuration had 8 train values: the first (default) configuration is used, untuned.

### Results at the primary horizon (24h), conservative lens

Intervals are adjusted for 16 comparisons (4 strategies x 4 horizons, Bonferroni). Relative = signal net modeled return minus the median of matched controls at the same decision time. Precision = share of signals that beat their controls. Estimates below the reporting minimum are not shown.

```
INDIVIDUAL    validation signals    0 labeled    0 coverage  n/a with controls    0 executable  n/a inputs captured live 0/0
                         not shown: 0 values with matched controls, at least 10 needed
INDIVIDUAL    test       signals    0 labeled    0 coverage  n/a with controls    0 executable  n/a inputs captured live 0/0
                         not shown: 0 values with matched controls, at least 10 needed
CONVERGENCE   validation signals    0 labeled    0 coverage  n/a with controls    0 executable  n/a inputs captured live 0/0
                         not shown: 0 values with matched controls, at least 10 needed
CONVERGENCE   test       signals    0 labeled    0 coverage  n/a with controls    0 executable  n/a inputs captured live 0/0
                         not shown: 0 values with matched controls, at least 10 needed
SOCIAL_WALLET validation signals    0 labeled    0 coverage  n/a with controls    0 executable  n/a inputs captured live 0/0
                         not shown: 0 values with matched controls, at least 10 needed
SOCIAL_WALLET test       signals    0 labeled    0 coverage  n/a with controls    0 executable  n/a inputs captured live 0/0
                         not shown: 0 values with matched controls, at least 10 needed
TRENDING      validation signals    0 labeled    0 coverage  n/a with controls    0 executable  n/a inputs captured live 0/0
                         not shown: 0 values with matched controls, at least 10 needed
TRENDING      test       signals   10 labeled    0 coverage  n/a with controls    0 executable  n/a inputs captured live 10/10
                         not shown: 0 values with matched controls, at least 10 needed
```

### Verdicts

- (a) individual analyst signal: one original LONG post: **INSUFFICIENT_DATA**. No eligible signal in the test window.
- (b) independent convergence: original LONG posts from several independence groups: **INSUFFICIENT_DATA**. No eligible signal in the test window.
- (c) social + wallet confirmation: independent posts plus a linked-wallet buy: **INSUFFICIENT_DATA**. No eligible signal in the test window.
- (d) raw mention / trending baseline: raw mentions incl. reposts, or a provider trending list: **INSUFFICIENT_DATA**. No test signal has a matured outcome window inside the data.

Test minus trending baseline (descriptive only, not a test): INDIVIDUAL n/a; CONVERGENCE n/a; SOCIAL_WALLET n/a (baseline estimate not available)

### Secondary horizons (exploratory, test split)

```
INDIVIDUAL    1h n=0 - | 6h n=0 - | 24h n=0 - | 72h n=0 -
CONVERGENCE   1h n=0 - | 6h n=0 - | 24h n=0 - | 72h n=0 -
SOCIAL_WALLET 1h n=0 - | 6h n=0 - | 24h n=0 - | 72h n=0 -
TRENDING      1h n=0 - | 6h n=0 - | 24h n=0 - | 72h n=0 -
```

### Bias and caveats

- INDIVIDUAL: the token universe is not declared to include delisted tokens: survivorship bias cannot be ruled out
- CONVERGENCE: the token universe is not declared to include delisted tokens: survivorship bias cannot be ruled out
- SOCIAL_WALLET: the token universe is not declared to include delisted tokens: survivorship bias cannot be ruled out
- TRENDING: the token universe is not declared to include delisted tokens: survivorship bias cannot be ruled out; 27 of 122 signalled tokens have no price history: losers may be missing from the data
- Selection: only signals the replay itself generated from stored evidence are evaluated; posts the collectors never saw cannot be judged, and the collected sources are not a random sample of all sources.
- Multiple testing: 16 configurations were tried on train; held-out results are reported for the chosen one only. Secondary horizons are exploratory.
- Missing prices are never filled in. A delisting before the exit counts as a total loss in the conservative lens for signals and controls alike; the measured-only lens is shown beside it.

### Leakage check (truncation invariance)

The replay was repeated on the data as it existed at each boundary (every record available later removed). Signals decided by then, and the train metrics used for tuning, must not change.

```
train boundary       at 2026-10-08T03:35:01Z: identical
validation boundary  at 2026-10-08T08:45:04Z: identical
tuning               at 2026-10-08T03:35:01Z: identical
```

No leakage detected: yes

### Audit

cutoff accesses 3537, records checked 110567, records from after a cutoff 0 (any would have stopped the run with LeakageError)

result sha256 1c298d8c9b1e22860165399117759447252ab010ebc09699a31e6b61766ba0c0

Real stored history. Where coverage is poor the verdict is 'insufficient sample/data' or 'cannot validate yet'; nothing is extrapolated beyond the data.

