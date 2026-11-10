# CM-2 change control PI-D-128: a failed daily run never commits a ledger that does not verify

Written 2026-11-10 during the second mutation probe run, before the change. This is the only change to the frozen cycle code of `e79d846`; `memelab/predictive/*` and `build_cm2.py` stay unchanged.

## Defect

Mutation D07 (remove the `verify` of the working ledger in the recovery step) survived. Looking at why showed a real defect next to it: whatever the reason a run stops, its last step commits every allowed path, which includes `LEDGER.jsonl`. A working ledger that fails verification (a tampered line, or an appended line whose chain is broken) makes the run stop with PREFLIGHT_FAILED, and then the same run commits that broken ledger. Every later run then stops on it, so nothing is scored, but `HEAD` (and, once pushed, GitHub) holds a ledger that does not verify, and the clean committed one has to be restored by hand.

Shown on the frozen code: the new test `test_a_run_that_stops_on_a_broken_working_ledger_does_not_commit_it` (in `tests/test_predictive_cm2_guards.py`) fails at `07a815e` with the broken ledger in `HEAD`.

## Change

`predictive_daily.py`: `commit()` takes the paths to commit (default: the allowed paths, as before). Before the final commit of a run, `ledger_committable()` checks that the working ledger verifies and is an append of the committed one (`monitoring.is_append_only`); if not, the run commits only its run record (`RUNS.jsonl`, `STATUS.json`, `ALERT_SUMMARY.txt`) and leaves the ledger in the working tree. Nothing else changes: the recovery step, the prediction commit and the order of steps are as frozen.

## D07 itself

D07 removes a check that `is_append_only` repeats (it verifies both chains), so the recovery step refuses a broken ledger with or without it. It is an equivalent mutant; it is listed as such in `evidence/mutation_probe.json`, not hidden.

## Checks

The new test passes after the change; the mutation probe gains D10 (the final commit ignores `ledger_committable`) and is run again in full; the full suite is run after the records commit.
