# PHASE 10: deterministic event and portfolio backtesting core

State: PASS. Date 2026-10-23. Entry gate: Phase 09 PASS at 58abf7d (catalyst tests 11 passed, 11/11 mutations, clean-tree backtest tests 94 passed).

## Changed files

- `memelab/backtest/engine.py` (committed with Phase 09 as a test dependency; gated here): event replay with bar MANAGE at bar close, decisions at availability, order life cycle (SUBMITTED, FILLED, CANCELED, EXPIRED, REJECTED_LIMIT, partial and failed exits), per-token limits and cooldown, max positions, exposure and cash checks, correlated-group cap (new), account drawdown halt (new), crash-through-stop rule (new), network fee on canceled entries, marked vs realizable value, end-of-run marking without reading past the cutoff, journal in the result, run hash.
- New: `memelab/backtest/runner.py` (frozen universe and stored bars to TokenData with point-in-time pool basis, first bar versions only, lab liquidity observations, per-pool fees, SOL/USD series; saved runs with restart recovery), `memelab/backtest/cli.py` (`python -m memelab backtest status|run`), registration in `memelab/cli.py` (one line).
- Changed: `store.register_run` adds a content hash of the package so uncommitted code changes cannot reuse a run id; `baselines.ENTER_AT_DISCOVERY` version 2 (one attempt only).
- Tests: `tests/test_backtest_engine.py` (18), `tests/test_backtest_runner.py` (4, on the real collapsed-token fixture).
- Evidence: `audits/backtesting/engine/RUNS.md`, `p10_runs.json`; `testing/p10_mutations.json`, log.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_backtest_engine.py tests/test_backtest_runner.py -q` | 0 | 22 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p10_mutations.json` | 0 | 14 of 14 caught |
| `python -m memelab backtest run --strategy <each of 12>` | 0 | runs saved; table in engine/RUNS.md |
| full suite, release audit and release e2e after commit | see HANDOFF | |

## Gate

G24 (competing signals conserve cash and limits), G25 (gap-through stop fills at the open; real loss exceeds the intended stop), G28 (baselines under the same execution), G29 (engine matches the Phase 04 hand oracle), plus G35 on synthetic data and on the real corpus. No negative cash (raises), no phantom fills (canceled and expired orders fill nothing; non-executable exits return 0). Same config, data and code give the same ledger hash; a second run returns the stored result (restart recovery).

## Bounded loop

Pass 1: the runner test on the real collapsed token expected a -99% loss and got -27.5%: the engine filled an intrabar stop at the stop price on a bar that fell from 0.0127 to 0.0000019 (a rug). Unrealistic; new rule fills crash-through bars (low more than 50% below the stop, close below the stop) at the bar's close. Tests and mutation M10-7 added.
Pass 2: the discovery baseline kept re-signaling until some later bar could fill (29,033 submissions on the corpus), which turns "enter at discovery" into "enter whenever tradable". Now one attempt (version 2); test and M10-13.
Pass 3: a run with changed but uncommitted code returned a cached result under the old run id. The run id now includes a content hash of the package; test and M10-12. Mutation M10-10 (network fee skipped on canceled entries) survived until a test checked final cash; caught.

## Independent negative review

Caught: bar applied before it completed (M10-1), gap stop at the stop price (M10-2), target before stop in one bar (M10-3), entry without cash (M10-4), group cap ignored (M10-5), drawdown halt ignored (M10-6), crash filled at the stop (M10-7), fill on the bar open at decision time (M10-8), end-of-run marking past the cutoff (M10-9), fee skipped on canceled entries (M10-10), later bar revisions applied (M10-11), run id blind to code (M10-12), discovery baseline retried (M10-13), commit-time rule ignored (M10-14).

## Limitations

Fills use LIQ_SNAPSHOT_APPROX from the lab's token-level liquidity observations, which can overstate one pool's depth when a token has several pools. Liquidity exists only where the lab wrote a thesis (selection effect, see RUNS.md). Creator-wallet groups are supported by the engine but the corpus has no point-in-time creator data yet, so the group cap is unused in these runs.

NEXT ELIGIBLE PHASE: 11.
