# Backtest and stress: PAID `solana:98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump`

As of 2026-10-06 23:48:23 UTC. Assessment STALE_DATA, evidence UNAVAILABLE, request 35cf517401dca8dd, engine bt-0.1.0.

Research only. Backtests describe the past over the lab's discovery universe, stress scenarios are hypothetical with no probabilities, and nothing here is an instruction to buy, sell or size a position.

## Headline (HEURISTIC)

Label: UNTESTED. Why: assessment STALE_DATA: analysis snapshot is 403.9 h old.
Project (lab view, unchanged): score 64, status SETUP DEVELOPING, good project by the lab's rubric.
Entry (execution view): UNTESTED, stress n/a, size under caps n/a.
Not assessed because: analysis snapshot is 403.9 h old (retriable: True).

## Historical evidence

Token-specific: NONE (no token-specific backtest; nothing here claims token-specific validation).

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

## Execution quote now (FACT)

Source: n/a, observed n/a.
Proceeds are the quoted SOL converted at the bundle's SOL price.
- no quote in the analysis bundle

## Catalyst provenance

no catalyst record for this mint; absence of a catalyst is not a negative or a positive signal.
Collector status: MAXUN: NOT_ADOPTED (Phase 06A, D-BT-020). No Maxun robot runs; the evaluation robot is idle with no schedule. webcapture: one-shot captures only; no schedule is approved (policy schedules_approved false). lab_catalyst_tables: the lab's own Firecrawl catalyst layer, read only.

## Alternate explanations (HEURISTIC)

- none generated (no assessment)

## Uncertainty (UNKNOWN)

- the assessment did not run (STALE_DATA); there is no backtest, stress or quote result to show

## Coverage

139,168 hourly bars over 258 mints, 2025-02-03 00:00:00 UTC to 2026-10-23 17:00:00 UTC; universe 2,901 records over 686 mints. Blocked: historical swaps, historical reserves, ticks and bins, historical holders and wallet flows. The universe is every token the lab recorded, including ones that later died; no survivor filter.
