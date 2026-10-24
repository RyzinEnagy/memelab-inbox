# Acceptance metrics (pre-registered before any modeling)

Fixed in Phase 01 before any label, feature or model exists. The numeric constants are in `memelab/predictive/contract.py` `ACCEPTANCE` and are covered by the registry fingerprint (pre-registered `dd3b4576...` in commit `b6f2621`; `9f8c9deb...` after change control CC-01, which changed only the reference-price and thinning rules, PI-D-019). A later change is allowed only as a recorded change-control decision that names its reason, and never because a metric looked better (package EXECUTION_RULES "Preserve the original scope ... log change-control if metrics evolve").

## What the data can and cannot support

- Real history is 17 days (2026-10-07 to 10-23) of decisions from one lab, one market regime and one universe filter (stage 1: liquidity at least $20k, 24 h volume at least $50k). Counts before eligibility: T1 24 h 177 development and 58 holdout events; T1b 6 h 280 and 79; T2 161 and 49 (TARGET_REGISTRY.md). Eligibility will remove a further share.
- Design arithmetic (`probes/power_simulation.py`, synthetic, seeded, independent events, a perfectly calibrated model): with 50 holdout events, a true Brier skill score (BSS) of 0.10 over the prevalence baseline is detected about 24% of the time and 0.20 about 45%; with 150 events, 53% and 86%. Real events cluster by day and mint, so real detectability is lower.
- Therefore the data can support: honest base rates with wide intervals; checks that a model is not worse than base rate; calibration checks in at most 2 or 3 bins; leakage and provenance tests. They cannot support: claims of small or moderate skill, per-cohort or per-regime probabilities, any statement about another market regime, any executable or profit statement (no historical depth), and any 7-day claim.
- The expected and acceptable outcome of the retrospective evaluation is "not distinguishable from the prevalence baseline" or INSUFFICIENT_HISTORY. The engine then ships baseline-or-abstain (NO_GO_DECISION_TREE "complex model underperforms").

## Out-of-sample windows

| Window | Rule |
|---|---|
| Development | decisions before 2026-10-17T00:00Z whose label matures before that time (`label_matures_at` <= holdout start); others in that span are purged, never moved |
| Walk-forward inside development | expanding window by UTC decision day; the first fold trains on decision days up to 2026-10-11 (at least 100 eligible labeled events, else the first fold starts later); each fold validates on the next day whose decisions start after the last training label matured (embargo = horizon + confirmation + 900 s); every fit sees only labels matured by its training cutoff; a model artifact carries its training cutoff |
| Retrospective holdout | decisions in [2026-10-17T00:00Z, 2026-10-24T00:00Z), sealed: Phase 06 builds its labels but stores them with a hash and prints counts and censoring only, no class prevalence; Phase 12 opens it once for the frozen champion and baselines; reuse after opening is logged and voids it as a holdout |
| Prospective holdout | decisions from 2026-10-24T00:00Z on, from the scheduled runs' daily exports (no new job needed); evaluated in Phase 19 once at least 50 eligible matured events exist per target; at about 12 thinned 24 h decisions a day before eligibility, expect one to two weeks or more |
| Group sensitivity | every holdout result is repeated on the subset of mints never seen in development, and with mints grouped by creator wallet where known (P14) |
| Regime | no regime claim; results are reported by week and by thesis status group (REJECTED versus other) as description |

## Minimum counts and abstention by count

| Gate | Value | Below it |
|---|---|---|
| Training events per target (eligible, matured, labeled) | 100, with at least 20 per class | INSUFFICIENT_HISTORY: no model for that target, prevalence only as description |
| Holdout events per target | 50, with at least 10 per class | no probability is published for that target (INSUFFICIENT_HISTORY) |
| Events per calibration bin | 20 | fewer bins; with fewer than 40 events only calibration-in-the-large is checked |
| Effective days | reported beside every metric | no claim that rests on fewer than 5 decision days |

## Baselines (all fitted on training data only)

| Id | Baseline | Role |
|---|---|---|
| B0 | training prevalence of the target | reference for the Brier skill score; the minimum any model must not lose to |
| B1 | prevalence by thesis status group (REJECTED, risk statuses, constructive statuses), shrunk toward B0 | tests whether the existing status already carries the information |
| B2 | logistic regression on a few as-of features (log liquidity, log market cap, log 24 h volume, token age when known, fatal-flag present) | the simple model a complex one must beat (package SCIENTIFIC_VALIDATION baseline 2) |
| B3 | the existing 100-point score, calibrated on training only (Platt), as a comparator | shows whether the score carries probability information; the score itself is never changed |
| B4 | matched-control prevalence: outcome rate of comparable tokens at the same decision time (pattern of `replay_core.controls_for`, `alpha_core` matched baselines) | controls for market-wide moves |
| NC1 | labels shuffled inside training | must score no better than B0 on validation |
| NC2 | future-feature trap (a feature from candles after `t_entry`) | must be refused by the as-of check (LeakageError), never reach a model |
| NC3 | same-ticker join trap (P01) | must be refused by the identity check |

## Scores

- Primary proper score: Brier score per target. Headline: Brier skill score versus B0, with a 95% interval from a bootstrap that resamples whole decision days (and, as a second interval, whole mints). Both intervals are shown; the wider one governs.
- Secondary: log loss (probabilities clipped to [1e-6, 1 - 1e-6] for computation only), ROC AUC and average precision when each class has at least 10 events, class prevalence and N always beside them. Brier and log loss are both shown with counts when they disagree (P23).
- Multiple testing: three primary outcomes (T1, T1b, T2). Any claim of skill uses Holm adjustment across the three. Every model, feature set and hyperparameter tried is written to the Phase 12 experiment ledger, including failures (P22).

## Calibration tolerance (with support)

A probability may be published only when, on the most recent out-of-sample evaluation for that target:

1. Calibration in the large: the mean predicted probability lies inside the 95% Wilson interval of the observed prevalence.
2. Reliability: events sorted by predicted probability into quantile bins of at least 20 events (at most 5 bins); in every bin the mean predicted probability lies inside the 95% Wilson interval of the observed frequency.
3. Expected calibration error and calibration slope are reported with bootstrap intervals as description (slope only with at least 100 events); they are not pass criteria at this sample size.

Failing 1 or 2 means UNCALIBRATED: no probability is shown.

## Promotion levels

| Level | Requirements |
|---|---|
| ABSTAIN (default) | anything below |
| SHADOW (research display, flag on only) | leakage, provenance and contract tests pass; counts above minimums; calibration tolerance met on the retrospective holdout; BSS point estimate versus B0 at least 0. Display says "no skill over the base rate demonstrated" when the BSS interval includes 0 |
| VALIDATED_EXPERIMENTAL | SHADOW plus: BSS lower 95% bound above 0 (Holm-adjusted) on the retrospective holdout and on the prospective holdout (at least 50 events), and the model is not worse than B2 on Brier point estimate. A complex model replaces B2 as champion only if its Brier difference to B2 has a lower bound above 0 |
| NO_GO | no level reached: ship the baseline description or abstain; mark the advanced model NO_INCREMENTAL_PREDICTIVE_EDGE |

No level ever implies a trading edge. All three primary targets are price-path targets with no execution data, so the trading-usefulness gate of EXECUTION_RULES cannot be passed by this initiative's data; any economic statement is NO_NET_TRADING_EDGE_CLAIMABLE until forward depth collection is approved and evaluated.

## Abstention policy (per forecast)

| Reason | When |
|---|---|
| FLAG_OFF | the feature flag is off (default) |
| OUT_OF_SCOPE_CHAIN | not Solana |
| OUT_OF_SCOPE_OPPORTUNITY_TYPE | launch-pass or catalyst-only opportunities in v1 |
| TARGET_NOT_FEASIBLE | a BLOCKED or DEFERRED target was asked for |
| NO_RECENT_PRICE | no trade in the hour before entry |
| INSUFFICIENT_HISTORY | count gates above not met, or no model passed |
| MODEL_NOT_SELECTED | no champion yet |
| UNCALIBRATED | calibration tolerance failed |
| OOD | a required feature is missing, or outside the training range by more than the range itself |
| FEATURE_SCHEMA_MISMATCH | the request's feature-set fingerprint differs from the model's (P46) |
| MODEL_STALE | the model's training cutoff is more than 14 days before the decision |
| DRIFT_ALERT | Phase 19 drift rule fired |
| SOURCE_STALE | an input needed at decision time is older than its allowed age or the source is down (P47) |
| NOT_YET_MATURED | used on outcome displays, never on a forecast |

Abstentions are always shown, with reasons, and never serialized as a score.

## Wording rules

- Allowed form (the numbers here are format only): "P(price path touches +25% before -15% within 24 h of the decision) = 0.31, 95% interval 0.20 to 0.43; base rate 0.34; holdout N = 58 over 7 days; model M (trained to 2026-10-16); research only, not proceeds, no execution data."
- Always present: target name, horizon, base rate, holdout N and days, interval, model id and training cutoff, the PRICE_PATH_NOT_PROCEEDS caveat, BACKTEST_NOT_AVAILABLE.
- Probabilities shown with two decimals at most, clipped for display to [0.01, 0.99]; never "certain", "guaranteed", "will", "likely to pump", "buy", "sell", "entry", "edge" or "alpha".
- When the interval is wider than 0.20, the text says "wide uncertainty". When the BSS interval includes 0, it says "no skill over the base rate demonstrated".
- A forecast never changes, re-ranks or annotates the 100-point score, the fatal flags, the status or the watchlist; it is a separate section.

## Latency and cost limits

| Item | Limit |
|---|---|
| Inference per decision | at most one paced GeckoTerminal read at capture (for the reference price, CC-01), 10 s timeout, retrieval time kept; at most 2 s CPU otherwise; failure or timeout gives ABSTAIN with SOURCE_STALE or NO_RECENT_PRICE, never a delay of the scout |
| Label building | offline, on demand inside a phase session; Phase 06 also reports, as description, the share of barrier touches made by candles under $500 USD volume (single-trade wicks, P25); GeckoTerminal at most 6 calls a minute with exponential backoff on HTTP 429 (the probe saw 429 at about 9 a minute), at most 1,200 calls per run, a circuit breaker after 5 consecutive failures (P48); raw bodies cached with retrieval time and sha256 so nothing is fetched twice |
| Firecrawl | 0 credits planned for phases 05 to 13; the 150-credit initiative cap is unchanged |
| LLM, Zep, MiroFish, paid APIs | 0; not approved (PI-D-005) |
| Scheduled jobs | none added; forward depth collection needs Elving's approval |
