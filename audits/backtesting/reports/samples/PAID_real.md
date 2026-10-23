# Backtest and stress: PAID `solana:98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump`

As of 2026-10-06 23:48:23 UTC. Assessment PARTIAL_WITH_LIMITATIONS, evidence SCENARIO_ONLY, request b77f916cc9ece264, engine bt-0.2.0.

Research only. Backtests describe the past over the lab's discovery universe, stress scenarios are hypothetical with no probabilities, and nothing here is an instruction to buy, sell or size a position.

## Headline (HEURISTIC)

Label: INCONCLUSIVE. Why: state PARTIAL_WITH_LIMITATIONS, evidence SCENARIO_ONLY, stress RESEARCHABLE.
Project (lab view, unchanged): score 64, status SETUP DEVELOPING, good project by the lab's rubric.
Entry (execution view): INCONCLUSIVE, stress RESEARCHABLE, size under caps $599.

## Historical evidence

Token-specific: NOT_RUN (no token-specific backtest; nothing here claims token-specific validation).
Cohort of past tokens with lab status SETUP DEVELOPING: 0 complete cases of 0 tokens the lab had recorded by then, tier INSUFFICIENT_HISTORY (minimum 30).

Strategies over the lab's whole discovery universe (net of modeled costs, ranked by net; paper is mid to mid before costs; under 30 trades is listed, not ranked):

- #1 BREAKOUT_RETEST: 34 trades, net -11.3%, paper -3.3% (paper rank 4), NET_NEGATIVE, run e3b5638df4, ledger 34524dcda0
- #2 ENTER_AT_DISCOVERY: 36 trades, net -13.3%, paper -10.3% (paper rank 7), NET_NEGATIVE, run 6826f91100, ledger 31820d4308
- #3 BREAKOUT_CLOSE: 47 trades, net -13.5%, paper -3.0% (paper rank 3), NET_NEGATIVE, run b201e999d6, ledger b88184fbae
- #4 MOMENTUM: 47 trades, net -14.1%, paper -2.4% (paper rank 1), NET_NEGATIVE, run 328b428953, ledger fb0a81672f
- #5 MA_CROSS: 51 trades, net -15.9%, paper -2.6% (paper rank 2), NET_NEGATIVE, run 824ef58f32, ledger 4c9485d3f3
- #6 RANDOM_ENTRY: 80 trades, net -18.5%, paper -4.2% (paper rank 5), NET_NEGATIVE, run 852635cfcc, ledger e0eef32c34
- #7 RECLAIM: 42 trades, net -20.5%, paper -6.4% (paper rank 6), NET_NEGATIVE, run fd6c48dc7e, ledger d5b3f56215
- not ranked CATALYST_VERIFIED: 2 trades, net +34.9%, paper +40.8%, NET_POSITIVE, run 934212acbc, ledger e730db8631
- not ranked LAB_STATUS: 26 trades, net -3.9%, paper -1.2%, NET_NEGATIVE, run 19ff1209a8, ledger b0819ce00d
- not ranked ABSORPTION_BREAK: 22 trades, net -29.9%, paper -1.9%, NET_NEGATIVE, run 5ca512c12b, ledger 19658022a6
- not ranked TREND_HHHL: 21 trades, net -34.3%, paper -9.4%, NET_NEGATIVE, run c650105964, ledger 43befddc52
- not ranked NO_TRADE: 0 trades, net n/a, paper n/a, NO_TRADES, run e9741bce51, ledger 178f852c10

Sealed-test validation (audits/backtesting/validation/p11_results.json, sha256 da986bcfcd90, pre-registration d0b3686f2d61, 55 trials counted):
- LAB_STATUS: INSUFFICIENT_SAMPLE, test 2026-10-21 12:00:00 UTC to 2026-10-23 16:00:00 UTC, 0 trades, mean n/a, enter-at-discovery baseline -42.2%
- BREAKOUT_CLOSE: INSUFFICIENT_SAMPLE, test 2026-10-21 12:00:00 UTC to 2026-10-23 16:00:00 UTC, 6 trades, mean -3.1%, enter-at-discovery baseline -42.2%
- MOMENTUM: INSUFFICIENT_SAMPLE, test 2026-10-21 12:00:00 UTC to 2026-10-23 16:00:00 UTC, 7 trades, mean -26.6%, enter-at-discovery baseline -42.2%
- BREAKOUT_RETEST: INSUFFICIENT_SAMPLE, test 2026-10-21 12:00:00 UTC to 2026-10-23 16:00:00 UTC, 6 trades, mean +3.0%, enter-at-discovery baseline -42.2%
- RECLAIM: INSUFFICIENT_SAMPLE, test 2026-10-21 12:00:00 UTC to 2026-10-23 16:00:00 UTC, 4 trades, mean -8.3%, enter-at-discovery baseline -42.2%
- TREND_HHHL: INSUFFICIENT_SAMPLE, test 2026-10-21 12:00:00 UTC to 2026-10-23 16:00:00 UTC, 3 trades, mean -54.6%, enter-at-discovery baseline -42.2%
- ABSORPTION_BREAK: INSUFFICIENT_SAMPLE, test 2026-10-21 12:00:00 UTC to 2026-10-23 16:00:00 UTC, 3 trades, mean -8.5%, enter-at-discovery baseline -42.2%
- RANDOM_ENTRY: INSUFFICIENT_SAMPLE, test 2026-10-21 12:00:00 UTC to 2026-10-23 16:00:00 UTC, 9 trades, mean -17.6%, enter-at-discovery baseline -42.2%
- Walk-forward BREAKOUT_CLOSE: 32 out-of-sample trades, mean -7.1%, 95% interval -13.5% to -1.8%

## Token signal states (not validation)

299 closed hourly bars, 1 unfinished bar(s) dropped. BREAKOUT_CLOSE NONE, BREAKOUT_RETEST NONE, TREND_HHHL NONE, ABSORPTION_BREAK NONE.

## Execution quote now (FACT)

Source: Jupiter /swap/v1/quote at observed_at (present tense, never historical), observed 2026-10-06 23:48:23 UTC.
Proceeds are the quoted SOL converted at the bundle's SOL price.
- sell $500: proceeds $500, impact 0.0027235
- sell $1,000: proceeds $998, impact 0.00391897
- sell $2,500: proceeds $2,479, impact 0.0106259
- sell $5,000: proceeds $4,926, impact 0.0170481
- sell $10,000: proceeds $9,751, impact 0.0271657
- sell $25,000: proceeds $23,652, impact 0.0561399
- sell $50,000: proceeds $45,032, impact 0.101493
- sell $100,000: proceeds $81,588, impact 0.186049

## Adverse stress (hypothetical, no probabilities)

Decision RESEARCHABLE: execution is feasible at the smaller sizes under base conditions; scenarios show the downside, not a forecast.
Probabilities: NOT_ASSIGNED (shocks are hypothetical; see historical_evidence for empirical frequencies when available).

Executable proceeds versus paper value (BASE, exit right away):
- $250: paper $247, executable $243, net -2.7%, fee 0.0125 (ASSUMED_UPPER_OBSERVED_TIER)
- $1,000: paper $984, executable $968, net -3.2%, fee 0.0125 (ASSUMED_UPPER_OBSERVED_TIER)
- $5,000: paper $4,846, executable $4,699, net -6.0%, fee 0.0125 (ASSUMED_UPPER_OBSERVED_TIER)

Worst net return per scenario across sizes:
- BASE: -6.0% at $5,000
- LIQ_25: -6.6% at $5,000
- LIQ_50: -7.7% at $5,000
- LIQ_75: -10.8% at $5,000
- INSIDER_DUMP: -63.7% at $5,000
- STOP_GAP: -43.4% at $5,000
- DELAYED_EXIT: -25.2% at $5,000
- FAILED_BREAKOUT: -27.7% at $5,000
- ATTENTION_COLLAPSE: -53.7% at $5,000
- VOLUME_GONE: -19.1% at $5,000
- SOL_DOWN_30: -34.2% at $5,000
- CONGESTION: -7.7% at $250
- HONEYPOT: -100.0% at $250
- COMBINED_WORST: -92.7% at $5,000
- QUOTE_DEPLETION: -6.0% at $5,000
No exit at all under: HONEYPOT.

Would improve the view: deeper liquidity observed at decision time; a fresh sell quote at the intended size.
Would worsen it: liquidity withdrawn or LP unlocked; large holders selling into thin depth; quote staleness beyond its TTL; price closes below the invalidation level.

## Conditions (not instructions)

Lab entry condition: resting bid inside 0.004132-0.004188 (15-minute support, 5 touches) while price is above the zone; fill only if a 15-minute candle trades into the zone without closing below 0.004132.
Invalidation: a 15-minute close below 0.004132 (zone low). That would mean the buyers who defended this level 5 time(s) have been absorbed and the level has flipped; the rotation thesis is wrong. (level 0.004131734365873996).
Largest size inside the caps {'max_loss_usd': 250.0, 'max_exit_impact': 0.05, 'shocks': ['BASE', 'LIQ_50', 'STOP_GAP']}: $599.

## Catalyst provenance

no catalyst record for this mint; absence of a catalyst is not a negative or a positive signal.
Collector status: MAXUN: NOT_ADOPTED (Phase 06A, D-BT-020). No Maxun robot runs; the evaluation robot is idle with no schedule. webcapture: one-shot captures only; no schedule is approved (policy schedules_approved false). lab_catalyst_tables: the lab's own Firecrawl catalyst layer, read only.

## Alternate explanations (HEURISTIC)

- a high lab score can reflect attention that is already in the price (price first, attention later)
- no tested setup is active on this token now; a move from here is outside what the strategies were tested on
- the cohort of past tokens with this lab status is 0 cases (minimum 30); past outcomes cannot separate skill from luck
- the pool fee is assumed at the highest observed tier; if the real tier is lower, costs here are overstated

## Uncertainty (UNKNOWN)

- stress magnitudes are fixed hypothetical shocks, not forecasts; no probabilities are assigned
- historical fills use LIQ_SNAPSHOT_APPROX (constant-product depth from a liquidity snapshot); exact historical execution is SOURCE_BLOCKED
- sell quotes are present tense (observed once at the assessment time) and expire quickly

## Coverage

139,168 hourly bars over 258 mints, 2025-02-03 00:00:00 UTC to 2026-10-23 17:00:00 UTC; universe 2,901 records over 686 mints. Blocked: historical swaps, historical reserves, ticks and bins, historical holders and wallet flows. The universe is every token the lab recorded, including ones that later died; no survivor filter.
