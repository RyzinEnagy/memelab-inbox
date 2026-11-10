# Example opportunity stress report contract — illustrative data only

**IMPORTANT: The following is a structure/fixture, NOT an observed token or trade recommendation.**

```
Asset: chain=solana | mint=EXAMPLE_SYNTHETIC_NOT_VALID | as_of=... UTC
Current opportunity: score=... (existing Lab score; fatal flaw override preserved)
Signal: BREAKOUT_CONFIRMED_v2 / SOCIAL_CATALYST_VERIFIED_v1
Signal evidence: raw_refs, first_seen, decision_time, pool/quote basis
Backtest tier: HISTORICAL_COHORT | TOKEN_SPECIFIC | SCENARIO_ONLY | UNAVAILABLE
Universe: 214 historically discovered tokens, including delisted tokens
Coverage: train / validation / sealed test, years, event count, missingness
Outcome versus baselines: expectancy net of fees & impact, max loss/drawdown,
    sample sizes, trade win %, profit factor, median tail loss, uncertainty band
No-lookahead: PASS (run fixture IDs)
Proposed position sizes: $500 / $2,500 / $10,000 — historic model vs live quote separated
Execution: sell proceeds per size; impact, tax, route, stale flag and max exit capacity
Scenarios: base, adverse-liquidity, LP withdraw, coordinated wallet exit,
    failed confirmation, sentiment rug, transfer-fee change, MEV/delay
Sensitivity: entry delay, size, reserves, costs, stop gap, source credibility
Thesis: ...
Entry conditions: ...
Invalidation: ...
What improves / deteriorates setup: ...
Decision status: RESEARCHABLE | STRUCTURALLY_UNTRADEABLE | INSUFFICIENT_DATA
Disclosure: hypothetical, backtests not forecasts, alternative outcomes
Reproduce: git SHA / dataset hash / strategy config / as_of / run ID / artifacts
```

**Do not implement a bare success-shaped field set.** Every substantive field must have a source/traced calculation and a negative/missing-data test. Existing memecoin ranking can remain independent; a bad stress result can flag or cap confidence without rewriting the original score unless architecture decision explicitly accepts a tested change.
