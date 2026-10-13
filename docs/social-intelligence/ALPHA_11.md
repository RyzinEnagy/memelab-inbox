# Phase 11: Information Alpha Score

Code: `memelab/social/alpha_core.py` (engine, no I/O, no clock), `alpha_store.py` (stored candles, runs, input from Phase 06 claims), `alpha_cli.py`. Migration 11 adds four tables, all `social_alpha_*`. Tests: `tests/test_social_alpha.py` (39). Fixture: `tests/fixtures/social/alpha/alpha_main.json`, built by `make_alpha.py`, invented and labelled. Engine `information-alpha-v1`, rules `alpha-rules-v1`.

This measures public commentary: after a post about a token, did the token do better than comparable tokens, net of a delay and trading costs, and is the sample big and clean enough to say so. It is not a wallet measurement. Phase 10 wallet profit is a separate result in separate tables and is not an input here. Follower counts, views and engagement are not inputs either. A source may legitimately get no score, and a ranking may legitimately be empty.

## What goes in

An input document (`memelab.alpha.input/1`): `sources` (label, optional `universe_count` and basis, optional `context` that is echoed and never used), `calls`, `series` (historical candles) and optional `author_trades`. Every call carries `item_key`, `observation_ref` or `source_url`; every series carries a `source`. `as_of` is the last moment the run may use.

A call: source id, token (chain and contract), direction (LONG, SHORT, EXIT, NEUTRAL, UNKNOWN), `published_at` (the post's own timestamp), `first_observed_at` (when the lab first saw it), `original`, and the extraction flags `conditional`, `sarcasm_suspected`, `uncertainty`, `author_position`.

A series: chain, contract, `candle_seconds`, `as_of_kind` (must be `HISTORICAL_CANDLE`), rows `t,o,h,l,c` with optional `v` (USD volume) and `liq` (pool liquidity in USD at the candle start), optional `delisted_at`. A series that is a live quote (`OBSERVED_AT_FETCH`), has no source, has bad or out-of-order candles, has a candle after its delisting, or is supplied twice for one token is rejected whole, with the reason shown. Nothing is repaired and nothing is fetched. From the database, `alpha series import` stores supplied candles and `alpha run --as-of T` builds the document from current Phase 06 claims (newest extraction only, tokens resolved by Phase 05 only, `store.is_independent_original`).

## Selection rules (fixed before any outcome is seen)

They are written into every result (`selection_rules`) and the policy is hashed with the input.

1. A call needs a source reference, a resolved token, a known publication time, `original`, and a direction of LONG, SHORT or EXIT.
2. After as_of: a call published or first observed after `as_of` is out (AFTER_AS_OF).
3. NEUTRAL or UNKNOWN direction (NO_DIRECTION), conditional claims, suspected sarcasm, and extraction uncertainty above `max_uncertainty` (default medium) are listed, not scored.
4. Hindsight capture: first observed more than `max_capture_lag_s` (3600) after publication, or never timestamped, is out (HINDSIGHT_CAPTURE_RISK). A sighting earlier than the post is a data error (OBSERVED_BEFORE_PUBLISHED).
5. Opposite statements on one token by one source within `conflict_window_s` (24 h) exclude all of them (CONFLICTING_STATEMENTS). The later one never overrides the earlier one.
6. Repeats: same source, token and direction within `dedupe_window_s` (7 d) after an evaluated call is REPEAT_POST. Reposts, forwards and quotes of someone else are NOT_ORIGINAL. After the window, the same token is a new independent call.
7. Eligibility never looks at the outcome. Every eligible call is evaluated whether it won, lost or went nowhere. An eligible call with no usable data stays in the coverage count (NO_PRICE_HISTORY, ILLIQUID_ENTRY, price gap, and so on).
8. One primary horizon (24 h) is fixed by policy. The others (1 h, 6 h, 72 h, 7 d) are reported and never blended into the score.

Ineligible and unevaluable calls are counted by reason in the output. `selection.completeness` is calls supplied divided by the posts the collector enumerated for that source (`universe_count`). Below 0.8 the source is declined; below 0.9, or unknown, it cannot be validated.

## Event study

Decision time: `max(published_at, first_observed_at) + delay_s` (300 s). You cannot trade on a post before you knew about it.

Entry: the candle that covers the decision time; if none does, the first candle starting within `max_entry_wait_s` (900 s) after it; otherwise PRICE_GAP and the call is not evaluable. Price is that candle's open (known at its start, at most one candle old), or the adverse side of the candle under `entry_price_rule: CANDLE_ADVERSE`. No candle that starts after `as_of` is read.

Exit at each horizon: the candle covering decision time + horizon, same wait rule. A horizon that has not elapsed at `as_of` is HORIZON_NOT_ELAPSED, not a loss. A series that ends without a delisting is HISTORY_ENDS, not a loss, and not extended.

Costs per side: fee 100 bps + slippage 50 bps + constant-product impact `2 * size / liquidity` (size 500 USD). Participation above 5% at entry is ILLIQUID_ENTRY (unknown liquidity is LIQUIDITY_UNKNOWN). At exit the cost is charged, capped at 100%, and unknown exit liquidity costs 50%.

Return: long = `P_exit * (1 - c_out) / (P_entry * (1 + c_in)) - 1`, never below -1. Short and exit (an information return, not executable on spot, flagged) = `-(P_exit / P_entry - 1) - c_in - c_out`.

Delisting: a long exits at zero (DELISTED_TOTAL_LOSS). A short exits at the last observed close with no extra credit. Both are conservative toward the source. Delisted tokens stay in the comparison pool.

Maximum favourable and adverse excursion: from the fill, gross of exit costs, at the primary horizon only, and only when at least 80% of the expected candles exist (else INSUFFICIENT_PATH_COVERAGE).

Publication-to-move lag: time from publication to the end of the first candle that moved the call's way by 20% from the entry price. Lead time: with the reference set at the start of the 6 h before publication, the end of the first candle that moved 20% the call's way, minus publication. Negative means the move had already happened (POSTED_AFTER_ONSET). A signed pre-post move of +100% or more is flagged LATE_PROMOTION; the call is still scored, with a negative lead time. Pre and post liquidity are reported (pre-window, entry, exit, and ratios).

Attributed author trades (`author_trades`, each with an assertion level and a source): a buy in the 24 h before the post with no declared position is UNDISCLOSED_PRIOR_BUY; a sale in the 24 h after a LONG post is SOLD_AFTER_PROMOTING. They are context. They never change the score (tested).

## Matched baseline

For each call: tokens on the same chain with a candle at the decision time that pass the same entry rules, with pool liquidity within 4x of the call token's, ranked by `|ln liquidity ratio| + 0.5 * |ln trailing volume ratio|` (volume from candles completed before the decision time), up to 8 of them. Every token any source in the run called is excluded, because promoted tokens are not a neutral control. Delisted tokens are included. Each control gets the same delay, entry rule, exit rule and costs, and the same sign as the call. At least 5 controls at a horizon are needed, else there is no relative return there (the call still has a raw net return). Relative return = call net - median control net.

## Metrics per source and horizon

Coverage (evaluated over eligible), independent calls with a baseline, median net return, median matched return, median relative return with a distribution-free 95% interval (order statistics) from 8 values, share that beat the baseline with a Wilson interval, failures to beat the baseline, false positives (evaluated calls with net return of zero or less, and the rate), lead-time quantiles with counts of no onset and posted-after-onset, excursion medians, late-promotion count, author-trade flags, ineligible counts by reason.

## Score, shrinkage, tiers

Primary horizon only. With n independent calls that have a baseline and median relative return m:

- weight `w = n / (n + 20)`
- conservative edge = `w * (the end of the 95% interval nearest zero, or 0 if the interval spans zero)`
- `score = round(50 + 50 * tanh(edge / 0.5))`. 50 means no demonstrated edge. `score_point` uses `w * m` and is shown beside it.

Tiers:

- UNVERIFIED: no score. Fewer than 10 independent calls with a baseline, no eligible calls, coverage under 0.5, or selection completeness under 0.8. The output says which.
- PRELIMINARY: scored. A lead to check, not a finding.
- VALIDATED: all of 30 independent calls, 20 distinct tokens, coverage 0.7, completeness known and at least 0.9, no token above 20% of calls, an interval that excludes zero, and the same sign in both chronological halves (10 calls each).

Even with the floor lowered, 3 calls get weight 0.13 and a score under 70 (tested). Fixture runs carry `usable_as_evidence: false`. `alpha rank` lists scored sources, validated first, and declines the rest with reasons. With nobody scored it says "Declining is the correct output."

## Hand check

One call, entry 1.00, exit 1.50 at 24 h, 500 USD into a 100000 pool. Cost per side = 1.00% + 0.50% + 2 * 500 / 100000 = 2.5%. Net = 1.5 * 0.975 / (1.0 * 1.025) - 1 = 0.4268292683. Six matched tokens exit at 0.8, 0.9, 1.0, 1.0, 1.1, 1.2, median 1.0, net 0.975 / 1.025 - 1 = -0.0487804878. Relative = 0.4756097561. `test_hand_checked_single_call` asserts each of these. `test_fixture_calls_recompute_independently_from_raw_candles` recomputes six fixture calls and their control medians with a second implementation that shares no code with the engine.

## End-to-end fixture

Three invented sources over hourly candles, policy horizons 1 h, 6 h and 24 h, as of 57 hours after the first candle. Source A has 23 supplied posts (universe 23): twelve ordinary calls with outcomes from -40% to +80%, plus a repost, a repeat, a neutral post, a bullish then bearish pair, a call found 5 hours late, a conditional claim, a late promotion after a pump, a delisting, a pool too thin for the size, and a token with no candles. Source B has three good calls. Source C has six winners found 6 hours late, from an account with a huge following, and 6 of 40 enumerated posts supplied.

Source A, 24 h table (every source reference is `fixture:x:<call id>`, candles `fixture:invented-candles`):

| call | dir | token | entry | exit 24h | gross | net | matched median | relative | lead time | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| a01 | LONG | TA01 | 1.000 | 1.800 | 80.0% | 71.2% | -7.0% | 78.3% | POSTED_BEFORE_ONSET | UNDISCLOSED_PRIOR_BUY |
| a02 | LONG | TA02 | 1.000 | 1.500 | 50.0% | 42.7% | -7.0% | 49.6% | POSTED_BEFORE_ONSET | - |
| a03 | LONG | TA03 | 1.000 | 1.300 | 30.0% | 23.7% | -6.9% | 30.5% | POSTED_BEFORE_ONSET | - |
| a04 | LONG | TA04 | 1.000 | 1.200 | 20.0% | 14.1% | -6.8% | 20.9% | NO_ONSET | - |
| a05 | LONG | TA05 | 1.000 | 1.100 | 10.0% | 4.6% | -6.7% | 11.3% | NO_ONSET | - |
| a06 | LONG | TA06 | 1.000 | 1.000 | 0.0% | -4.9% | -6.6% | 1.7% | NO_ONSET | - |
| a07 | LONG | TA07 | 1.000 | 0.900 | -10.0% | -14.4% | -7.0% | -7.3% | NO_ONSET | - |
| a08 | LONG | TA08 | 1.000 | 0.800 | -20.0% | -23.9% | -7.0% | -16.9% | NO_ONSET | - |
| a09 | LONG | TA09 | 1.000 | 0.700 | -30.0% | -33.4% | -6.9% | -26.6% | NO_ONSET | - |
| a10 | LONG | TA10 | 1.000 | 1.400 | 40.0% | 33.2% | -6.8% | 39.9% | POSTED_BEFORE_ONSET | - |
| a11 | LONG | TA11 | 1.000 | 0.600 | -40.0% | -42.9% | -6.7% | -36.3% | NO_ONSET | - |
| a12 | LONG | TA12 | 1.000 | 1.250 | 25.0% | 18.9% | -6.6% | 25.5% | POSTED_BEFORE_ONSET | - |
| a13 | LONG | TA01 | - | - | - | - | - | - | INELIGIBLE: NOT_ORIGINAL | - |
| a14 | LONG | TA01 | - | - | - | - | - | - | INELIGIBLE: REPEAT_POST | - |
| a15 | NEUTRAL | TA02 | - | - | - | - | - | - | INELIGIBLE: NO_DIRECTION | - |
| a16 | LONG | TA13 | - | - | - | - | - | - | INELIGIBLE: CONFLICTING_STATEMENTS | - |
| a17 | SHORT | TA13 | - | - | - | - | - | - | INELIGIBLE: CONFLICTING_STATEMENTS | - |
| a18 | LONG | TA14 | - | - | - | - | - | - | INELIGIBLE: HINDSIGHT_CAPTURE_RISK | - |
| a19 | LONG | TA14 | - | - | - | - | - | - | INELIGIBLE: CONDITIONAL_CLAIM | - |
| a20 | LONG | TA15 | 3.000 | 1.500 | -50.0% | -52.4% | -6.5% | -46.0% | POSTED_AFTER_ONSET | LATE_PROMOTION |
| a21 | LONG | TA16 | 1.000 | 0.000 | -100.0% | -100.0% | -6.9% | -93.1% | NO_ONSET | - |
| a22 | LONG | TA17 | - | - | - | - | - | - | UNEVALUABLE: ILLIQUID_ENTRY | - |
| a23 | LONG | TA18 | - | - | - | - | - | - | UNEVALUABLE: NO_PRICE_HISTORY | - |
| b01 | LONG | TB01 | 1.000 | 2.000 | 100.0% | 90.2% | -7.0% | 97.2% | POSTED_BEFORE_ONSET | - |
| b02 | LONG | TB02 | 1.000 | 1.900 | 90.0% | 80.7% | -6.9% | 87.6% | POSTED_BEFORE_ONSET | - |
| b03 | LONG | TB03 | 1.000 | 1.700 | 70.0% | 61.7% | -6.8% | 68.5% | POSTED_BEFORE_ONSET | - |
| c01 | LONG | TC01 | - | - | - | - | - | - | INELIGIBLE: HINDSIGHT_CAPTURE_RISK | - |
| c02 | LONG | TC02 | - | - | - | - | - | - | INELIGIBLE: HINDSIGHT_CAPTURE_RISK | - |
| c03 | LONG | TC03 | - | - | - | - | - | - | INELIGIBLE: HINDSIGHT_CAPTURE_RISK | - |
| c04 | LONG | TC04 | - | - | - | - | - | - | INELIGIBLE: HINDSIGHT_CAPTURE_RISK | - |
| c05 | LONG | TC05 | - | - | - | - | - | - | INELIGIBLE: HINDSIGHT_CAPTURE_RISK | - |
| c06 | LONG | TC06 | - | - | - | - | - | - | INELIGIBLE: HINDSIGHT_CAPTURE_RISK | - |

Source A at the primary horizon: 14 evaluated, median net -0.1%, median matched -6.8%, median relative +6.5%, 95% interval -36.3% to +39.9%, beat the baseline in 57%, 7 false positives. Weight 14/34 = 0.41. The interval spans zero, so the score is 50 (PRELIMINARY); the point estimate is 53. Not validated: 14 calls (needs 30), 14 distinct tokens (needs 20), the interval includes zero, halves of 7 (needs 10). Source B: 3 calls, no score. Source C: all six calls HINDSIGHT_CAPTURE_RISK, no eligible calls, completeness 0.15, no score. Ranking: source A only, preliminary. The 5,000,000 followers of source C changed nothing (tested).

Report as printed by `python -m memelab social alpha run --input tests/fixtures/social/alpha/alpha_main.json --policy '{"horizons_s":[3600,21600,86400]}'`:

```
Information Alpha (information-alpha-v1, alpha-rules-v1)  label: FIXTURE: invented sources, tokens, posts and prices
INVENTED FIXTURE DATA: this is a demonstration of the calculation, not evidence about any real source.
as of 1790204400; delay 300s; size $500; primary horizon 24h; policy 82e8fe741984

Source src_a: 23 calls supplied, 16 eligible and independent, 14 evaluated, 14 with a matched baseline at the primary horizon.
  ineligible: CONDITIONAL_CLAIM 1, CONFLICTING_STATEMENTS 2, HINDSIGHT_CAPTURE_RISK 1, NOT_ORIGINAL 1, NO_DIRECTION 1, REPEAT_POST 1
  no usable price data: ILLIQUID_ENTRY 1, NO_PRICE_HISTORY 1
    1h  n=14  median net    -4.3%  baseline    -4.8%  relative     0.5%  ci95 ['-1.3%', '1.5%']  beat 0.57  false positives 14
    6h  n=14  median net    -1.3%  baseline    -5.3%  relative     4.0%  ci95 ['-6.7%', '9.9%']  beat 0.64  false positives 9
   24h  n=14  median net    -0.1%  baseline    -6.8%  relative     6.5%  ci95 ['-36.3%', '39.9%']  beat 0.57  false positives 7
  lead time: 6 with an onset, 8 none, 1 posted after the move; quantiles {'p25': 27900.0, 'median': 41400.0, 'p75': 57600.0}
  SCORE 50 (PRELIMINARY), point estimate 53, shrinkage weight 0.41. 50 means no demonstrated edge over matched tokens. Above 50: the low end of the 95% interval of the median relative return beat them, after shrinkage for sample size. Below 50: it did worse. The point estimate is shown as score_point. Not a probability and not a ranking of skill.
    not validated: 14 independent calls, validation needs 30
    not validated: 14 distinct tokens, validation needs 20
    not validated: the 95% interval of the median relative return includes zero: the result cannot be told apart from no edge
    not validated: chronological halves have 7 and 7 calls, the split-sample check needs 10 each

Source src_b: 3 calls supplied, 3 eligible and independent, 3 evaluated, 3 with a matched baseline at the primary horizon.
    1h  n=3   median net    -1.3%  baseline    -4.8%  relative     3.5%  ci95 none  beat 1.0  false positives 3
    6h  n=3   median net    16.5%  baseline    -5.3%  relative    21.8%  ci95 none  beat 1.0  false positives 0
   24h  n=3   median net    80.7%  baseline    -6.9%  relative    87.6%  ci95 none  beat 1.0  false positives 0
  lead time: 3 with an onset, 0 none, 0 posted after the move; quantiles {'p25': 19800.0, 'median': 21600.0, 'p75': 23400.0}
  NO SCORE (declined): 3 independent calls with a matched baseline at the primary horizon; at least 10 are needed to publish a score

Source src_c: 6 calls supplied, 0 eligible and independent, 0 evaluated, 0 with a matched baseline at the primary horizon.
  ineligible: HINDSIGHT_CAPTURE_RISK 6
    1h  n=0   median net      n/a  baseline      n/a  relative      n/a  ci95 none  beat None  false positives 0
    6h  n=0   median net      n/a  baseline      n/a  relative      n/a  ci95 none  beat None  false positives 0
   24h  n=0   median net      n/a  baseline      n/a  relative      n/a  ci95 none  beat None  false positives 0
  lead time: 0 with an onset, 0 none, 0 posted after the move; quantiles None
  NO SCORE (declined): no eligible calls | 0 independent calls with a matched baseline at the primary horizon; at least 10 are needed to publish a score | only 0.15 of the posts enumerated for this source were supplied, below 0.8; the sample may be picked

Ranked by tier first (validated above preliminary), then score. A preliminary score is a lead to check, not a finding.
```

Result sha256 `5b3b8fddbe061d9cd9e767e3f6a7acf4d9efb09fd4225f236114af443cd595cd`.

## Limits

- No live candles, no live claims, no live wallet data were used. Every proof ran on invented fixtures. The tracked database holds no alpha rows and fixture runs into it are refused.
- No price source is wired in. Candles are supplied (`alpha series import`). A run on real data needs a historical candle provider with pool liquidity, and the answer will mostly be "declined" until there is enough history.
- Candle liquidity is assumed to be pool liquidity at the candle start. Providers that only give a close-of-candle figure need a rule before they are used.
- The comparison pool only contains tokens somebody supplied candles for. If that set is already a survivor set, the matched baseline is biased. Delisted tokens in the pool help but do not cure it.
- A token with a series that ends early and no delisting is not evaluable. Tokens that die quietly therefore lower coverage rather than score as losses. Coverage is reported and gated, and unevaluable-by-reason is listed.
- Shorts are information returns. Spot shorts are not executable, so SHORT and EXIT results are flagged and should be read as "did the token fall".
- The posts the collector enumerated for a source (`universe_count`) are not stored by the earlier phases. From the database it is unknown unless an annotations file supplies it, which caps the tier at PRELIMINARY.
- Author trades come from an annotations file in this phase. Wiring Phase 09 wallet events in as attributed trades is not done.
- Calls by different sources on one token share market moves. Scores are per source; no pooled score exists.
- Impact is a constant-product approximation; real routes, MEV and failed transactions are not modelled.
