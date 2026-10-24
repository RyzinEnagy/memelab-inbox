# PHASE 12: adversarial position and opportunity stress engine

State: PASS. Date 2026-10-23. Entry gate: Phase 11 PASS at 38d2fcc (validation tests 13 passed, 11/11 mutations, release audit clean).

## Changed files

- New: `memelab/backtest/stress.py` (Snapshot with pool fee and its basis; hypothetical shocks: liquidity -25/-50/-75%, insider dump, stop gap, delayed exit (new), failed breakout, attention collapse, volume gone, SOL -30%, congestion with failed transactions, honeypot, combined worst, and conditional fee hike, freeze, mint dilution, stablecoin depeg, quote depletion (new); CPMM depth scaled with sqrt(price); observed sell quotes cap an optimistic model and are never extrapolated; max size under loss and impact caps; decisions RESEARCHABLE / INCONCLUSIVE / NO_TRADE / STRUCTURALLY_UNTRADEABLE / RISK_FATAL_FLAW / INSUFFICIENT_EXECUTION_DATA; what would improve or worsen the view; probabilities NOT_ASSIGNED; empirical cohorts reported separately).
- Tests: `tests/test_backtest_stress.py` (13).
- Evidence: `audits/backtesting/stress/SCENARIOS.md`, `p12_scenarios.py`, `p12_scenarios.json`; `testing/p12_mutations.json`, log.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_backtest_stress.py -q` | 0 | 13 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p12_mutations.json` | 0 | 12 of 12 caught |
| `python audits/backtesting/stress/p12_scenarios.py` | 0 | two real pools, 4 sizes, 15 scenarios each; 5 cohorts (one large enough) |

## Gate

G12 (state at exit time; liquidity withdrawn before our exit), G17 and G35 (realizable below marked, capacity limits), G25 (gap through the stop), G30 (combined extreme shock coherent, no negative proceeds), G31 (new token: no historical claim; cohorts below 30 cases are INSUFFICIENT_HISTORY). Every shock lowers achievable proceeds; no likelihood labels appear in any output (tested).

## Bounded loop

Pass 1: three mutations survived. A test claimed exit impact should grow after a price crash; the physics says the opposite in percentage terms (the token reserve doubles while USD depth halves), so the test now pins the ratio to the sqrt-price model and catches the no-sqrt mutant. HONEYPOT outcomes were not asserted; now they are. The "never scale up from quotes" guard is doubled in code, so single-guard mutants were equivalent; the mutation now removes both and is caught.
Negative control: a token with a fatal flag never gets a positive decision (test and M12-2).

## Independent negative review

Caught: depth unchanged when price falls (M12-1), fatal flag overridable (M12-2), unknown insider share silently zero (M12-3), honeypot sells (M12-4), quotes extrapolated (M12-5), quotes scale the model up (M12-6), pool fee ignored (M12-7), probability labels (M12-8), marked shown as realizable (M12-9), quote depletion never fails (M12-10), authority shocks for every token (M12-11), cohort percentiles from too few cases (M12-12).

## Limitations

Shocks are fixed, hypothetical magnitudes. Liquidity is modeled as one constant-product pool per token. Cohorts use mid prices before costs and only the REJECTED cohort reaches 30 cases.

NEXT ELIGIBLE PHASE: 13.
