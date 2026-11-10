# CM-2 change control PI-D-129: corrections after the records commit (mutation probe offline; three Phase 16 tests)

Written 2026-11-10. Test and probe code only; `memelab/predictive/*`, `predictive_daily.py` (after PI-D-128) and `build_cm2.py` are unchanged.

## Item 1: the mutation probe runs mutant tests without a network

Mutation D08 (decisions at or before the freeze are predicted) made the daily cycle plan label reads for old, matured decisions inside the end-to-end test's temp clone, and the real reader made 63 free GeckoTerminal pool-list calls over two probe runs before they were stopped by hand (`evidence/mutation_probe_network.json`, `COST_LEDGER.md`). `probes/mutation_probe.py` now runs every mutant's tests inside `unshare -n` (`2f72034`). The first offline run had a failing baseline (the tests' scratch commits use this session's commit signing service, unreachable without a network), so every mutant counted as caught; that run is kept as `evidence/mutation_probe_run4_invalid_baseline.log` and not used. The probe now makes those scratch commits unsigned and stops on a failing baseline (`4e020cb`). The valid run: 35 applied, 34 caught, D07 equivalent.

## Item 2: three Phase 16 tests that the frozen code broke

The full suite after the records commit `f403b1b` failed 5 tests: the two known clock-dependent ones and three that the frozen code commit `e79d846` broke and that were never run against it (the entry suite ran at `ed85b2c`; no full suite ran between `e79d846` and the records):

| Test | Why it fails |
|---|---|
| `test_predictive_integration.py::test_g22_every_registry_entry_still_sees_its_code_files_unchanged` | each Phase 16 entry records the sha256 of its code files, including `contract.py` and `labels.py`, which PI-D-122 changed |
| `test_predictive_phase16_outputs.py::test_cp16_2_every_entry_s_facts_are_rebuilt_by_the_registry_and_its_code_files_are_unchanged` | same |
| `test_predictive_reproductions.py::test_phase_16_registry_reproduces_its_committed_files` | the rebuilt entries carry the new code hashes, so 72 files differ |

What this means at run time: the Phase 16 entries, retired by CM-2 and still read by integration-1, now see two changed code files (P46, MODEL_INCOMPATIBLE_RETRAIN_REQUIRED) besides being MODEL_STALE; their answers stay ABSTAIN. That is the intended behavior of P46, so the tests change, not the code:

1. g22 and cp16_2 now require that the code changes each entry sees are exactly the PI-D-123 files it records, that each recorded hash is the PI-D-123 "was" pin, and (g22) that each current file is the PI-D-123 new pin. Any other drift still fails.
2. The reproduction reruns the Phase 16 builder in the state of its own commit for those two files only, as PI-D-120 did for the backtesting package: a scratch clone of HEAD with each file restored to the bytes whose sha256 is its "was" pin (taken from `ed85b2c`), and the git-ignored `data/memelab.sqlite` copied in. A trial run gave 0 differing files.

Checked: the three tests pass after the change (with the rest of their files, 19 passed); the full suite is run again after this commit.
