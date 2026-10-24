# Backtest reports, CLI and alert labels

Research only. Nothing below places, sizes or suggests an order.

## Turning it on

Off by default. Turn it on with `MEMELAB_BACKTEST=1` or `data/backtest/policy.json` with `{"enabled": true}`. When it is off, scout reports, analyze output and social alerts are byte-identical to the lab without the backtesting package.

When it is on:
- `scout` appends a "Backtest and stress (research only)" section after the unchanged scout body. It also writes `<stamp>_SCOUT.backtest.json` and one `.backtest.md` / `.backtest.json` pair per analyzed mint next to the scout report.
- `analyze` prints one extra line.
- Token-specific social alerts get a `Backtest:` line.

## Commands

| Command | What it does |
|---|---|
| `python -m memelab backtest stress MINT --results ID ... [--position-usd 250 1000] [--max-loss-usd N] [--now UTC] [--json]` | Analyzes the mint from saved results without writing the lab database, assesses it, prints the report. Runs even with the policy off, because you asked for it by name. |
| `python -m memelab backtest assess MINT [--chain solana] [--json]` | Report for the newest stored assessment. A mint with none is reported as UNTESTED. |
| `python -m memelab backtest run --strategy ID [--as-of UTC] ...` | Replays a strategy over the frozen discovery universe. `--as-of` is the cutoff: nothing after it is read. |
| `python -m memelab backtest inspect RUN_ID [--json]` | Config, code, dataset, result and ledger hashes, summary, stored files and the command that reproduces the run. |
| `python -m memelab backtest data` | Coverage of the research database and the sources that are blocked. |
| `python -m memelab backtest schema` | JSON Schema of the report (also in [REPORT_SCHEMA.json](REPORT_SCHEMA.json)). |
| `python -m memelab backtest deep` / `assess-stats` | Runs queued DEEP assessments; shows counts and wall time. |

## Labels

The labels are checked in this order, and the first one that applies wins:

1. FATAL FLAW: the lab has a fatal flag. Its veto stands. If anything downstream still reads as usable, the report says "override detected".
2. UNTESTED: there is no assessment, or it is stale, source-blocked, failed, or the mint id is invalid. A missing assessment is never shown as neutral or positive.
3. BAD EXECUTION: there is no sell route, the smallest size exits above 10% impact, no size fits the caps, or the pool is not supported.
4. INCONCLUSIVE: anything that is not one of the others. This is the usual outcome today, because cohorts are small and every strategy is INSUFFICIENT_SAMPLE.
5. TESTED: historical cohort or token-specific evidence, plus a feasible exit under base conditions. It is still research only.

The report keeps "good project" (the lab's score and status, unchanged) apart from "good entry" (execution under stress). When the lab status is NEAR ENTRY or ENTRY CONDITIONS MET but the entry reads BAD EXECUTION, UNTESTED or FATAL FLAW, the report says HIGH_STATUS_MISMATCH.

## What a report contains

Every group carries an evidence class:
- token and trace: chain, mint, as-of time, request key, state, tier;
- headline: label and why, project view against entry view, any mismatch;
- lab: score, status, fatal flags, override check;
- historical evidence:
  - token-specific results (DEEP stage);
  - cohort of past tokens with the same lab status (at least 30 cases, or reported as too few);
  - strategies over the whole universe, ranked by net return after modeled costs, with paper next to it. A strategy with under 30 trades is listed but not ranked. PAPER_ONLY_PROFIT marks a strategy that profits on paper and loses after costs. Every row names its run id, dataset hash, result hash and ledger hash;
  - the sealed-test validation record, with its file hash and pre-registration hash;
- token signal states (closed bars only; states, not validation);
- execution quote now (present tense);
- adverse stress: hypothetical shocks with no probabilities, executable proceeds against paper value, worst case per scenario, sensitivity;
- conditions: the lab's entry condition, the invalidation and the largest size inside the caps. These are not instructions;
- catalyst provenance: origin, capture method, first-known time, publication confidence and late-crawl warnings, plus collector status (Maxun NOT_ADOPTED, no schedules);
- alternate explanations, uncertainty and coverage.

Samples: [audits/backtesting/reports/samples/](../../audits/backtesting/reports/samples/).
