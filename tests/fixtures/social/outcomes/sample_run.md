# Phase 16 sample: signal ledger and forward evaluation on an invented fixture

FIXTURE DEMO: invented signals, tokens, references, prices and times. This is not live data and not a trade record.

Reproduce: `python -m memelab social evaluate demo --fixture tests/fixtures/social/outcomes/outcomes_fixture.json`

Throwaway ledger. Five signals are recorded at emission (emitted, rejected and suppressed alike), then evaluated twice: at 2026-10-13T19:00:00Z and at 2026-10-14T14:00:00Z, with new and revised price observations arriving in between. Positions are hypothetical (500 USD evaluation size, not a recommendation).

Recorded: 5 signal(s), refused 0.

## Signal snapshot before evaluation (sig_9f7fd7b580400fddd0c87400)

context body sha256 0777c37f26a6e4b6272118c21238ebcc2446af2dc35d8efb7839707beb25bb9b

```json
{
 "assumptions": {
  "direction": "LONG",
  "execution_lag_s": 300,
  "fee_bps_per_side": 100.0,
  "horizons_s": [
   3600,
   21600,
   86400,
   259200,
   604800
  ],
  "max_participation": 0.05,
  "policy_sha256": "63060eb3acf7ce68d8af74db2a241e883d76375e74db11d01af59cd8877e1f8d",
  "policy_version": "default-1",
  "position_size_note": "hypothetical evaluation size, not a recommendation",
  "position_size_usd": 500.0,
  "slippage_bps_per_side": 50.0
 },
 "context_sha256": "6c99af104832514ca16fc1a75f3b491950859f54d7be4b01d36042a07746912b",
 "disposition": "EMITTED",
 "disposition_reason": "feed priority HIGH (HEURISTIC)",
 "emitter": "feed",
 "emitter_ref": "contract:solana:B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY",
 "flags": [],
 "is_fixture": true,
 "market_at_generation": {
  "facts_after_generation_excluded": 1,
  "liquidity": {
   "as_of": 1791891000.0,
   "basis": "reported pool liquidity, not exit depth",
   "fact_id": 502,
   "provider": "dexscreener",
   "value_usd": 180000
  },
  "observed_price": {
   "age_s": 60.0,
   "as_of": 1791892740.0,
   "basis": "observed midpoint or provider price at fetch, not proceeds",
   "fact_id": 501,
   "provider": "jupiter",
   "stale": false,
   "unit": "USD",
   "value": 0.01
  },
  "sell_route": {
   "as_of": 1791892740.0,
   "basis": "actual route quote",
   "fact_id": 503,
   "out_usd": 488.0,
   "provider": "jupiter.quote_v1",
   "size_usd": 500,
   "status": "OK"
  }
 },
 "missing": [],
 "references": {
  "claims": [
   9101,
   9102
  ],
  "narrative_run_id": 1,
  "sources": [
   "x:id:fx_alpha",
   "x:id:fx_bravo"
  ]
 },
 "schema": "memelab.social.signal/1",
 "signal_id": "sig_9f7fd7b580400fddd0c87400",
 "times": {
  "captured_at": 1791892860.0,
  "event_time": 1791885600.0,
  "generated_at": 1791892800.0,
  "publication_delay_s": 7200.0
 },
 "token": {
  "chain": "solana",
  "contract": "B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY",
  "symbol_display_only": "GOODCAT"
 },
 "trade_execution_impact": "none",
 "versions": {
  "classifier": "feed-v1",
  "ledger_engine": "outcomes-v1",
  "policy": "fixture",
  "scoring": "alerts-default-1"
 }
}
```

## Evaluation 1

Observations appended 153, duplicate 0, refused 0.

```
Evaluation at 2026-10-13T19:00:00Z: 5 signal(s), 25 signal-horizon outcome(s) computed.
  status now: PENDING 12, MEASURED 4, MISSING 6, NON_EXECUTABLE 3, INVALIDATED 0
  appended: 25 (FIRST 25); unchanged and not appended: 0

sig_9f7fd7b580400fddd0c87400 GOODCAT (EMITTED, feed)
    1h MEASURED        MEASURED | mid +9.17%, net modeled +4.72%, net quoted n/a | path OK mfe +9.17% mae +0.00% | flags NO_ROUTE_QUOTE_AT_EXIT
    6h MEASURED        MEASURED | mid +23.88%, net modeled +18.73%, net quoted +17.26% | path OK mfe +23.88% mae +0.00%
   24h PENDING         HORIZON_NOT_MATURED
   72h PENDING         HORIZON_NOT_MATURED
    7d PENDING         HORIZON_NOT_MATURED
sig_caf0292b9a457c9da7f49ce5 HYPEDOG (REJECTED, research)
    1h MEASURED        MEASURED | mid +18.11%, net modeled +2.69%, net quoted n/a | path OK mfe +18.11% mae +0.00% | flags NO_ROUTE_QUOTE_AT_EXIT
    6h NON_EXECUTABLE  EXIT_LIQUIDITY_LOST; NO_SELL_ROUTE | mid -80.32%, net modeled -85.44%, net quoted n/a | path OK mfe +18.11% mae -80.32%
   24h PENDING         HORIZON_NOT_MATURED
   72h PENDING         HORIZON_NOT_MATURED
    7d PENDING         HORIZON_NOT_MATURED
sig_6545430994d1954497d3e03c NEWPUP (EMITTED, feed)
    1h MEASURED        MEASURED | mid +52.72%, net modeled +42.05%, net quoted n/a | path OK mfe +52.72% mae +0.00% | flags NO_ROUTE_QUOTE_AT_EXIT
    6h NON_EXECUTABLE  TOKEN_DELISTED_BEFORE_EXIT
   24h PENDING         HORIZON_NOT_MATURED
   72h PENDING         HORIZON_NOT_MATURED
    7d PENDING         HORIZON_NOT_MATURED
sig_aa5d6f4d9a7c80a2b019c175 SLOWFROG (SUPPRESSED, alerts)
    1h MISSING         MISSING_MIDPOINT_AT_EXIT
    6h NON_EXECUTABLE  PRICE_QUOTE_MISMATCH | mid +3.30%, net modeled -0.26%, net quoted -40.10% | path INSUFFICIENT_PATH | flags PRICE_QUOTE_MISMATCH
   24h PENDING         HORIZON_NOT_MATURED
   72h PENDING         HORIZON_NOT_MATURED
    7d PENDING         HORIZON_NOT_MATURED
sig_843569429cf2a516462189a7 theme:dogs (EMITTED, feed)
    1h MISSING         UNRESOLVED_IDENTITY
    6h MISSING         UNRESOLVED_IDENTITY
   24h MISSING         UNRESOLVED_IDENTITY
   72h MISSING         UNRESOLVED_IDENTITY
    7d MISSING         UNRESOLVED_IDENTITY
```

## Evaluation 2

Observations appended 121, duplicate 0, refused 0.

```
Evaluation at 2026-10-14T14:00:00Z: 5 signal(s), 25 signal-horizon outcome(s) computed.
  status now: PENDING 8, MEASURED 6, MISSING 6, NON_EXECUTABLE 5, INVALIDATED 0
  appended: 6 (INPUTS_REVISED 2, MATURED 4); unchanged and not appended: 19

sig_9f7fd7b580400fddd0c87400 GOODCAT (EMITTED, feed)
    1h MEASURED        MEASURED | mid +3.20%, net modeled -0.97%, net quoted n/a | path OK mfe +8.42% mae +0.00% | flags NO_ROUTE_QUOTE_AT_EXIT
    6h MEASURED        MEASURED | mid +23.88%, net modeled +18.73%, net quoted +17.26% | path OK mfe +23.88% mae +0.00%
   24h MEASURED        MEASURED | mid -10.69%, net modeled -14.23%, net quoted n/a | path OK mfe +23.88% mae -10.69% | flags NO_ROUTE_QUOTE_AT_EXIT
   72h PENDING         HORIZON_NOT_MATURED
    7d PENDING         HORIZON_NOT_MATURED
sig_caf0292b9a457c9da7f49ce5 HYPEDOG (REJECTED, research)
    1h MEASURED        MEASURED | mid +18.11%, net modeled +2.69%, net quoted n/a | path OK mfe +18.11% mae +0.00% | flags NO_ROUTE_QUOTE_AT_EXIT
    6h NON_EXECUTABLE  EXIT_LIQUIDITY_LOST; NO_SELL_ROUTE | mid -80.32%, net modeled -85.44%, net quoted n/a | path OK mfe +18.11% mae -80.32%
   24h NON_EXECUTABLE  EXIT_LIQUIDITY_LOST | mid -84.54%, net modeled -87.95%, net quoted n/a | path OK mfe +18.11% mae -84.54% | flags NO_ROUTE_QUOTE_AT_EXIT
   72h PENDING         HORIZON_NOT_MATURED
    7d PENDING         HORIZON_NOT_MATURED
sig_6545430994d1954497d3e03c NEWPUP (EMITTED, feed)
    1h MEASURED        MEASURED | mid +52.72%, net modeled +42.05%, net quoted n/a | path OK mfe +52.72% mae +0.00% | flags NO_ROUTE_QUOTE_AT_EXIT
    6h NON_EXECUTABLE  TOKEN_DELISTED_BEFORE_EXIT
   24h NON_EXECUTABLE  TOKEN_DELISTED_BEFORE_EXIT
   72h PENDING         HORIZON_NOT_MATURED
    7d PENDING         HORIZON_NOT_MATURED
sig_aa5d6f4d9a7c80a2b019c175 SLOWFROG (SUPPRESSED, alerts)
    1h MISSING         MISSING_MIDPOINT_AT_EXIT
    6h NON_EXECUTABLE  PRICE_QUOTE_MISMATCH | mid +3.30%, net modeled -0.26%, net quoted -40.10% | path INSUFFICIENT_PATH | flags PRICE_QUOTE_MISMATCH
   24h MEASURED        MEASURED | mid +6.15%, net modeled +2.49%, net quoted n/a | path OK mfe +6.15% mae +0.00% | flags NO_ROUTE_QUOTE_AT_EXIT
   72h PENDING         HORIZON_NOT_MATURED
    7d PENDING         HORIZON_NOT_MATURED
sig_843569429cf2a516462189a7 theme:dogs (EMITTED, feed)
    1h MISSING         UNRESOLVED_IDENTITY
    6h MISSING         UNRESOLVED_IDENTITY
   24h MISSING         UNRESOLVED_IDENTITY
   72h MISSING         UNRESOLVED_IDENTITY
    7d MISSING         UNRESOLVED_IDENTITY
```

## Same evaluation repeated

```
Evaluation at 2026-10-14T14:00:00Z: 5 signal(s), 25 signal-horizon outcome(s) computed.
  status now: PENDING 8, MEASURED 6, MISSING 6, NON_EXECUTABLE 5, INVALIDATED 0
  appended: 0 (none); unchanged and not appended: 25
```

## Signal snapshot after two evaluations (sig_9f7fd7b580400fddd0c87400)

context body sha256 0777c37f26a6e4b6272118c21238ebcc2446af2dc35d8efb7839707beb25bb9b

Original context unchanged, byte for byte, for all 5 signals: yes.

Attempted rewrite: UPDATE refused by the ledger: signal ledger is append-only: entries are never updated

## Outcome entries for sig_9f7fd7b580400fddd0c87400

```
#159 as of 2026-10-13T19:00:00Z FIRST             1h MEASURED        MEASURED | mid +9.17%, net modeled +4.72%, net quoted n/a | path OK mfe +9.17% mae +0.00% | flags NO_ROUTE_QUOTE_AT_EXIT
#305 as of 2026-10-14T14:00:00Z INPUTS_REVISED    1h MEASURED        MEASURED | mid +3.20%, net modeled -0.97%, net quoted n/a | path OK mfe +8.42% mae +0.00% | flags NO_ROUTE_QUOTE_AT_EXIT
#160 as of 2026-10-13T19:00:00Z FIRST             6h MEASURED        MEASURED | mid +23.88%, net modeled +18.73%, net quoted +17.26% | path OK mfe +23.88% mae +0.00%
#306 as of 2026-10-14T14:00:00Z INPUTS_REVISED    6h MEASURED        MEASURED | mid +23.88%, net modeled +18.73%, net quoted +17.26% | path OK mfe +23.88% mae +0.00%
#161 as of 2026-10-13T19:00:00Z FIRST            24h PENDING         HORIZON_NOT_MATURED
#307 as of 2026-10-14T14:00:00Z MATURED          24h MEASURED        MEASURED | mid -10.69%, net modeled -14.23%, net quoted n/a | path OK mfe +23.88% mae -10.69% | flags NO_ROUTE_QUOTE_AT_EXIT
#162 as of 2026-10-13T19:00:00Z FIRST            72h PENDING         HORIZON_NOT_MATURED
#163 as of 2026-10-13T19:00:00Z FIRST             7d PENDING         HORIZON_NOT_MATURED
```

## Outcome coverage

```
Signals in ledger: 5 (fixture: 5); by disposition: EMITTED 3, REJECTED 1, SUPPRESSED 1
Outcome entries that supersede an earlier entry (matured, changed or revised): 6

horizon  signals  pending  measured  missing  non-exec  invalid  not-eval  coverage
1h             5        0         3        2         0        0         0  60% of 5 matured
6h             5        0         1        1         3        0         0  20% of 5 matured
24h            5        0         2        1         2        0         0  40% of 5 matured
72h            5        4         0        1         0        0         0  0% of 1 matured
7d             5        4         0        1         0        0         0  0% of 1 matured

Reasons for exclusion (latest outcome per signal and horizon):
  1h MISSING: MISSING_MIDPOINT_AT_EXIT x1, UNRESOLVED_IDENTITY x1
  6h MISSING: UNRESOLVED_IDENTITY x1
  6h NON_EXECUTABLE: EXIT_LIQUIDITY_LOST x1, NO_SELL_ROUTE x1, PRICE_QUOTE_MISMATCH x1, TOKEN_DELISTED_BEFORE_EXIT x1
  24h MISSING: UNRESOLVED_IDENTITY x1
  24h NON_EXECUTABLE: EXIT_LIQUIDITY_LOST x1, TOKEN_DELISTED_BEFORE_EXIT x1
  72h MISSING: UNRESOLVED_IDENTITY x1
  7d MISSING: UNRESOLVED_IDENTITY x1

By disposition (rejected and suppressed signals are evaluated the same way):
  1h: EMITTED MEASURED 2, MISSING 1; REJECTED MEASURED 1; SUPPRESSED MISSING 1
  6h: EMITTED MEASURED 1, MISSING 1, NON_EXECUTABLE 1; REJECTED NON_EXECUTABLE 1; SUPPRESSED NON_EXECUTABLE 1
  24h: EMITTED MEASURED 1, MISSING 1, NON_EXECUTABLE 1; REJECTED NON_EXECUTABLE 1; SUPPRESSED MEASURED 1
  72h: EMITTED MISSING 1, PENDING 2; REJECTED PENDING 1; SUPPRESSED PENDING 1
  7d: EMITTED MISSING 1, PENDING 2; REJECTED PENDING 1; SUPPRESSED PENDING 1

Medians are descriptive, over MEASURED outcomes only, never a score; positions are hypothetical; no trade is implied.
```

## Ledger check

entries 310, hash chain and body hashes OK, head a647cda2f4151237cd0747d3592f95ad4e4c53d65b71ffca2cef8105927dea30

FIXTURE DEMO: invented signals, tokens, references, prices and times. This is not live data and not a trade record.
