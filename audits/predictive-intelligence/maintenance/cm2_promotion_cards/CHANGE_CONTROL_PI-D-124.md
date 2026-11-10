# CM-2 change control PI-D-124: the end-to-end fixture of tests/test_predictive_daily.py

Written 2026-11-10 after the recorded label reads and the card fit (commit `a140986`), before the recorded daily runs were used as evidence. Test code only: `memelab/predictive/*`, `predictive_daily.py` and `build_cm2.py` are unchanged from the frozen commit `e79d846` (checked by `git diff e79d846 -- memelab audits/predictive-intelligence/daily/predictive_daily.py audits/predictive-intelligence/maintenance/cm2_promotion_cards/probes/build_cm2.py`, empty).

## What was wrong

The two end-to-end tests of `tests/test_predictive_daily.py` skip until a CM-2 registry is committed, so at `e79d846` they never ran. Once `a140986` committed the registry they ran and errored or failed for three reasons, all in the test, none in the cycle:

| Id | Frozen test text | Fact | Change |
|---|---|---|---|
| F1 | `doc["tokens"]`, `doc["theses"]` | the state export keeps its tables under `doc["_tables"]` (KeyError `tokens`) | read `doc["_tables"]` |
| F2 | first run: `"OUTCOME" not in kinds` | the cycle appends PENDING outcomes (no read, no label) after the prediction commit, as Phase 19 did | every OUTCOME is PENDING with no label and comes after every PREDICTION in the ledger |
| F3 | third run (`--max-calls 0`, T1b matured): ledger unchanged | the matured T1b outcome is appended as NOT_READ (no call, no label), a non-final state | ledger prefix unchanged, the added entries are only NOT_READ T1b outcomes with no label, tree clean |

The changed assertions still test the property the change control states (predictions committed before any read; a second run with nothing new appends nothing; no call when the cap is 0). The second run's "appends nothing" check is unchanged and passes.

## How it was found and checked

1. F1 by running the file after `a140986`; F2 and F3 by printing the ledger of a scratch run (`test_dbg.py` in the session scratchpad, not committed): 3 PENDING outcomes after 6 predictions, then 1 NOT_READ T1b outcome.
2. After the change: `python -m pytest -q tests/test_predictive_daily.py`: 11 passed.
3. The mutation probe (`probes/mutation_probe.py`) runs against the changed tests, so a weakened assertion would show as a surviving mutation of the guards they cover (D05, D06, D07, D09).
