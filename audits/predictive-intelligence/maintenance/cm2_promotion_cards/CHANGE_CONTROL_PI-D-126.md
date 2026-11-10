# CM-2 change control PI-D-126: tests added for guards the mutation probe showed untested; the probe itself corrected

Written 2026-11-10 after the first mutation probe run (`evidence/mutation_probe_run1.json`, at `43a485b`). Test and probe code only: `memelab/predictive/*`, `predictive_daily.py` and `build_cm2.py` stay as frozen at `e79d846`.

## First run: 34 mutations applied, 23 caught, 11 survived

| Survivor | Why it survived |
|---|---|
| P03 window closes at 49 events | no test placed a window at exactly the 50-event edge |
| P13, P14 evaluate drops its own event and day checks | `next_window` never closes below the minimums, so no test gave `evaluate_window` such a window; the checks are a second line |
| P20 an undefined bootstrap replicate counts for skill | no test with a perfect reference |
| D01, D02 recipe and governing pins not checked | the pin test compared the constants, never called `recipe()` with a different pin |
| D05, D06, D07, D08, D09 | a probe defect: the mutation was left uncommitted, but the end-to-end tests clone the committed tree, so the mutated script never ran |

## Changes

1. New file `tests/test_predictive_cm2_guards.py` (5 tests): the 50 and 49 event edge; `evaluate_window` refusing a closed window below the event minimum and below the day minimum; a perfect reference gives a lower bound of minus infinity; `recipe()` refusing a different recipe pin and a different governing pin; `--no-commit` with a planned read stops with LABEL_FETCH_FAILED and makes no call (`--max-calls 0`, `--no-fetch`, no network either way). The frozen test files are not edited for this.
2. `probes/mutation_probe.py` commits each mutation in its scratch clone before running the tests and resets it afterwards, and runs the new file with both test groups.
3. The probe is run again; its result is `evidence/mutation_probe.json`. The first run's output is kept as `evidence/mutation_probe_run1.json`.
