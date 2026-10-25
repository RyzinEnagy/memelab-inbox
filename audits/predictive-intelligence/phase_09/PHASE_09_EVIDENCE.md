# Phase 09 evidence: on-chain, liquidity, wallet and authority forecasts

Status: NEEDS_REVIEW (first pass; every gate item below holds on this agent's checks; the independent skeptic of PI-D-013 is the orchestrator's next step). All numbers PROVISIONAL under PI-D-046 (`revision_check_claimed: false`). Parts resting only on fixtures are TEST_ONLY: the collector adapter, the proposed liquidity and exit labels, and the wallet-movement rules.

## Where and when

- Branch `feature/predictive-intelligence`; HEAD before `c7d6a2f` (pushed); pre-registration `3079af1` (2026-10-25T22:37:55Z); code `15bc5b5` (22:54:36Z); runner repairs `a52233c` (22:55:49Z) and `18bd243` (22:57:03Z); outputs and records in the commit after; HEAD after in `PHASE_09_RESULTS.json` and HANDOFF.md.
- Work from 2026-10-25T22:29Z to about 23:20Z (UTC) in `/home/claude/memelab-inbox`, Python 3.13, numpy; scikit-learn 1.9.1 only in the research venv `/home/claude/pi_research/venvs/p04_bundle`.
- Package: `sha256sum -c SHA256SUMS.txt` exit 0, 41 lines OK.
- Sources read: the package files above; `docs/predictive-intelligence/*` (PI-D-001 to PI-D-053); Phase 05 to 08 deliverables; `memelab/predictive/*.py`; `origin/feature/backtesting` at `12f278b` through `git show` only (`memelab/backtest/depth.py`, `schema.py`, `store.py`, `sources/labstate.py`, `audits/backtesting/data/PROVENANCE.md`, `docs/backtesting/DECISIONS.md` D-BT-034/035); the tracked `data/memelab.sqlite` read-only. No web source, no vendor call, 0 Firecrawl credits; 1 `git fetch origin feature/backtesting` (already at `12f278b`).

## Entry gate (re-run independently)

| Check | Command | Result |
|---|---|---|
| Suite at `c7d6a2f` | `python -m pytest tests -q -p no:cacheprovider` (22:29:20Z to 22:32:10Z) | exit 1, `1 failed, 1229 passed in 169.59s`; only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` |
| Strays | `git status --short` | `data/reports/20261025_2229_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`; removed by hand |
| Seal | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | exit 0, `"problems": []`, holdout labels `e695500d...`, seal `d5059bae...`, SEAL.json `f362ca12...` |
| Lab database | `sha256sum data/memelab.sqlite` | `068287c0...` before and after the suite |
| Stores | `sha256sum` of the p05 and p06 stores | `2525f0c4...` and `58213988...`, equal to Phase 08's run log |

## Commands of this phase (exit codes verbatim)

| Command | Exit | Result |
|---|---|---|
| features-only probe (inline, 22:42:40Z) over 925 Solana decisions | 0 | missing-reason counts only; no label, no fit (debug run 1 in the ledger) |
| `python -m pytest tests/test_predictive_onchain.py -q -p no:cacheprovider` | 0 | `43 passed` (42 before the outputs, the ledger test added with them) |
| `python -B audits/predictive-intelligence/phase_09/probes/mutation_onchain.py OUT.json` (first, 39 tests) | 1 | 46 of 55 caught; 9 survivors, each answered by a new test |
| same, after the new tests | 0 | 55 of 55 caught (`evidence/mutation_onchain.json`) |
| `python -B .../run_onchain.py OUT --npz ...` at `15bc5b5` (recorded run 1, 22:54:40Z) | 1 | stopped in the P36-OC trap (foreign key of the in-memory copy) after writing the experiment tables; outputs not read; debug run 2 |
| same at `a52233c` (recorded run 2, 22:55:49Z) | 1 | all traps pass; the ledger check failed (registry names `P09:<target>:NC1OC`, ledger had per-seed rows); debug run 3 |
| same at `18bd243` (recorded run 3, 22:57:03Z to 22:57:57Z) | 0 | `{"targets": {"T2_24h": "OK", "T1_24h": "OK", "T1b_6h": "OK"}, "outputs": 36, "socket_events": 0, "stores_unchanged": true, "ledger_missing": 0}` |
| same into a second folder (run 4) | 0 | identical outputs except the run log and the trace latency (`evidence/determinism.json`); run 2 and run 3 differ only in the ledger, `traps.json` (the ledger list) and the trace latency |
| `/home/claude/pi_research/venvs/p04_bundle/bin/python -B .../sklearn_crosscheck_onchain.py run3.npz OUT.json` | 0 | 48 real designs, newton-cholesky max coefficient difference 1.75e-11, Prep 5.8e-15 |
| `python -B .../verify_trace_onchain.py .../FORECAST_TRACE.json` | 0 | 25 values, 13 inputs, 7 model numbers, 0 differences |
| post-commit suite, guard, seal, release audit | see "Post-commit results" | |

## Results in short

- Data sufficiency (the phase gate): no historical reserves, quotes, swaps, holders, wallet flows or authority histories exist for the decisions; nothing is substituted by a modern read. The lab's own on-chain readings inside each export row exist on every decision and are now as-of features (onchain-1). Liquidity drawdown, exit capacity and distribution stay DEFERRED or BLOCKED; written as proposals only.
- Models: every on-chain model passes the training gate in every fold (inputs on every labelled row), and every verdict is INSUFFICIENT_DAYS (T2: 8 rows, 1 positive, 1 day; T1: 24, 8, 3 days) or INSUFFICIENT_EVENTS (T1b: 44, 3, 5 days). No model can be called better or worse than the base rate, B2 or the simple on-chain rule. All MODEL_NOT_PROMOTED.
- Execution semantics: a forecast never clears a fatal flag; a size cap comes from depth only and is EXECUTION_DATA_MISSING on every decision here.
- Collector adapter: read-only contract against the documented schema; this checkout has no collector database (COLLECTOR_NOT_AVAILABLE); fixture-tested only (TEST_ONLY).
- Real cross-checks: authority 33 of 33 agree; token program disagrees for one mint (lab DB against the export); swaps against candles agree on one mint and differ on four (pool fragmentation, latest-trades page); 19 exchange holders never insider; one dev wallet looks like a mint.

## Acceptance checklist results

| Id | Result | Evidence |
|---|---|---|
| G1 | PASS | package check exit 0 |
| G2 | PASS | entry suite `1 failed, 1229 passed` (known failure), seal 0 problems |
| G3 | PASS | `3079af1` at 22:37:55Z; first real-label run 22:54:40Z; the only earlier real-data execution was the features-only probe at 22:42:40Z (no label) |
| G4 | PASS | `test_imports_numpy_and_standard_library_only_and_never_the_backtesting_package`; 43 tests |
| G5 | PASS | tests `test_values_are_available_at_the_decision_and_never_use_a_later_decision`, `test_truncated_store_gives_the_same_snapshot`, `test_change_features_use_the_previous_decision_only`, `test_p36_*`; real: 0 INCONSISTENT_TIME over 925 decisions, P36-OC trap |
| G6 | PASS | `evidence/v2_consistency.json`: 240 of 240, 0 differences |
| G7 | PASS | `evidence/phase07_equality.json`: split fingerprints equal, 0 of 76 B0/B2 differences |
| G8 | PASS | training rows through `training_labels` and `baselines.join`, then `onchain.attach` (identity checked); stores opened read-only; sealed and bake-off paths refused at start |
| G9 | PASS | `test_count_gate_*`; real folds: used rows equal training rows, all at least 104 events and 23 per class (`evidence/folds.json`) |
| G10 | PASS | `experiments/ONCHAIN_METRICS.csv`, 270 rows, every verdict INSUFFICIENT_DAYS or INSUFFICIENT_EVENTS, PROVISIONAL |
| G11 | PASS | `experiments/RULES_VS_MODEL.csv`, `EARLY_WARNING.csv` |
| G12 | PASS | `evidence/traps.json`: NC2-OC 170 of 170 refused twice, P13-OC 15 of 15, P36-OC 25 of 25 values refused, CX-09 pass; NC1-OC rows in the metrics |
| G13 | PASS | `EARLY_WARNING.csv` and `EARLY_WARNING_COHORTS.csv`; no rate under 20 (counts only) |
| G14 | PASS | `evidence/serialization_smoke.json`: 15 cards round-trip identical, tamper refused, `verify_artifact` passes, no pickle |
| G15 | PASS | same file: ABSTAIN documents valid, FORECAST with a probability refused, for each target |
| G16 | PASS | `evidence/sklearn_crosscheck.json`: 48 real designs within 1e-9 (max 1.75e-11) |
| G17 | PASS | `evidence/determinism.json`; run log socket events 0, stores and lab database unchanged |
| G18 | PASS (TEST_ONLY) | adapter tests on fixtures; `evidence/collector_state.json` COLLECTOR_NOT_AVAILABLE |
| G19 | PASS | `test_proposals_have_no_defaults_and_the_registry_is_unchanged`; registry `4b4aabce...` |
| G20 | PASS | `test_a_forecast_never_clears_a_fatal_flag_and_the_cap_ignores_the_forecast`, mutations caught |
| G21 | PASS (rules TEST_ONLY; real holder check PASS) | wallet tests; `evidence/crosschecks.json` holder classes |
| G22 | PASS | `evidence/crosschecks.json` |
| G23 | PASS | `evidence/trace/verify_trace.json` pass; 4 invalid inputs refused |
| G24 | PASS | `experiments/SEARCH_LEDGER.csv` 1,804 rows: Phase 08's 1,133 first, then Phase 09's including 3 real-data debug runs; test |
| G25 | PASS | tests for P02, P08, P09, P13, P18, P19, P25, P36, P37, P38, P44, CX-09; mutation probe 55 of 55 |
| G26 | PASS | existing isolation test (no module outside the package imports it) plus `test_no_other_module_imports_the_phase_09_code`; flag OFF; no existing code or test file changed |
| G27 | see post-commit | |

## Iteration log

1. Pass 1 (build): onchain.py, depth_adapter.py, 39 tests, mutation probe: 46 of 55 caught. Survivors: authority switch ignoring freeze, attach ignoring the decision time, a missing value becoming zero, the count gate on all rows, the walk-forward index check, alarm at equality, the read-only open (masked by `query_only`), proceeds from a reported reserve, a number on PRICE_DISAGREES.
2. Pass 2 (repair): three new tests (attach identity and missing values, count gate on used rows, walk-forward mismatch) and four new assertions in existing tests (freeze-only authority switch, alarm at equality, write refused with `query_only` off, reserve and PRICE_DISAGREES rows): 42 tests, 55 of 55. Code committed.
3. Recorded runs: run 1 stopped in a trap's fixture (runner bug); run 2 failed its ledger check (bookkeeping); run 3 recorded. Both repairs are runner-only, committed before the next run, logged as debug runs. No configuration, threshold or model changed between runs; run 2 and run 3 numbers are identical.

## Own adversarial pass (not independent)

- A later m24 wording parsed with a value: refused as UNPARSEABLE (test); real data: 0 unparseable values on 17 days, so no day is silently dropped.
- "No MINT_AUTHORITY_ACTIVE flag" read as "revoked" when the mechanics module did not run: refused (NOT_OBSERVED_BY_LAB, test, mutation).
- The collector's first read taken as depth at the decision (CX-09): refused (`visible_at`, `assert_visible`, test, two mutations).
- A forecast lowering the veto or raising the cap: impossible by construction (no probability argument; test with 0.001 to 0.999; mutation).
- Limitation found, not fixed: the collector times a decision with `git log` over its state paths (`labstate.state_versions`), the predictive engine with the first-parent history of `data/state/latest.json`. Main's pushes were all fast-forwards (PI-D-021 item 6), so they should agree; where they do not, `depth_adapter.link` raises instead of guessing. The first real rows must measure the link rate.
- Limitation: authority features have no variance in development (0 active of 240) and the T2 out-of-sample set is one day; nothing about authority risk can be learned here.
- Limitation: the capture delay reaches 21.6 h; a model sees what the lab saw, which can be stale.

## Artifacts

sha256 of every file under `audits/predictive-intelligence/phase_09/` except this file and `PHASE_09_RESULTS.json` is listed in `PHASE_09_RESULTS.json` (`artifacts`); the run's own output hashes are in `evidence/run_log.json`.

## Post-commit results

At the outputs commit `934d2d4` (files in `postcommit/`):

| Check | Command | Result |
|---|---|---|
| Suite | `python -m pytest tests -q -p no:cacheprovider` (23:05:56Z to 23:08:43Z) | exit 1, `1 failed, 1272 passed in 166.48s`; only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` |
| Strays | `git status --short` | `data/reports/20261025_2306_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`; removed by hand; `data/memelab.sqlite` sha256 `068287c0...` unchanged |
| Guard | `python -m memelab social guard` | exit 0, `"violations": []` |
| Seal | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | exit 0, `"problems": []` |
| Release audit | `python tools/release_audit.py --history` on a single-branch clone at `934d2d4` | exit 0, "Needs action: no." |
| Working tree | `git status --short` | clean |

G27: PASS. The follow-up commit records these results and the hash; it changes no code, test or output.
