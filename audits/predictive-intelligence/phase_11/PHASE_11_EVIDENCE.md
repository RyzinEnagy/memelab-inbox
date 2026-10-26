# Phase 11 evidence: analog cohorts and regime handling for low-history opportunities

Status: NEEDS_REVIEW (every gate item reproduced by the phase agent; the orchestrator's independent skeptic has not run yet, PI-D-013). Cohort numbers are research numbers only; nothing is promoted or published.

- Branch `feature/predictive-intelligence`; HEAD before `aae7a55`; pre-registration `46afc85` (2026-10-26T15:04:46Z); frozen code `0482a60` (15:20:20Z); ledger repair `ff98b8d` (15:26:22Z); outputs and records in the commit that carries this file (hash in HANDOFF.md and `PHASE_11_RESULTS.json` after the post-commit records commit).
- Package: `sha256sum -c SHA256SUMS.txt` 41 OK, 0 failed.
- Spend: 0 Firecrawl credits, 0 vendor calls, 0 language-model calls, 0 socket events in the runner, no `git fetch` (the pinned `origin/main` commit `e245d91` was already local).
- The frozen 48 h revision check passed (PI-D-059); Phase 11 cards and tables carry `revision_check_claimed: true` with that reference.

## Entry gate (G2)

| Command | Result | Exit |
|---|---|---|
| `python -m pytest tests -q -p no:cacheprovider` at `aae7a55` (from 2026-10-26T14:55:19Z) | `1 failed, 1335 passed in 238.57s`; only the known `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (`evidence/entry/entry_suite_summary.txt`) | 1 |
| stray files after the suite | `data/reports/20261026_1455_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`, removed by hand | |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | `"problems": []`, seal digest `d5059bae...` (`evidence/entry/entry_seal.json`) | 0 |
| `python -B audits/predictive-intelligence/phase_10/probes/recompute_oos_social.py` (Phase 10's key check) | 76 rows, 456 model values, 326 numbers recomputed, 0 differences (`evidence/entry/entry_phase10_recompute.json`) | 0 |
| Phase 10 `PHASE_10_RESULTS.json` | status PASS, head_after `717dc99` | |
| sha256 of `data/memelab.sqlite`, the p05 and p06 stores | `068287c0...`, `2525f0c4...`, `d2a5a7c6...`, equal to Phase 10's run log | |

## Commands of this phase

| Command | Result | Exit |
|---|---|---|
| unlabelled looks before the checklist (15:00Z to 15:03Z) | decision counts per export instant, median 24 h volume, constructive share, regime labels past-only and full-sample (32 of 74 differ), launchpads, creators; no label read | 0 |
| commit `46afc85` (checklist, registry, PI-D-061) | before any cohort on a labelled row. The checklist's header says "from 15:05Z"; the commit is 15:04:46Z, so the header's minute is approximate (writing started about 15:03Z) | |
| features-only probe (15:14:33Z to 15:14:37Z, after `46afc85`) | regime series (WARMUP 5, QUIET/RISK_ON 40, QUIET/RISK_OFF 31, ACTIVE/RISK_ON 3 instants), CX-11 32 flips, analog-1 inputs; no label read, no cohort (debug run 1 in the ledger) | 0 |
| `python -m pytest tests/test_predictive_analog.py -q` (first) | 1 failed (a NaN compared with NaN in the regime record; NaN stored as null), then `45 passed` | 0 |
| `python -B probes/mutation_analog.py` (first) | 47 mutations, 42 caught; survivors: pool availability check, cluster by mint, sample sd, tie by position, tone of every status | 1 |
| 5 tests added for the survivors (before the code commit) | `50 passed`; mutation probe 47 of 47 | 0 |
| commit `0482a60` (module, tests, probes) | before the recorded run | |
| `python -B probes/run_analog.py OUT --npz ...` (run 1, 15:20:26Z to 15:21:09Z, head `0482a60`) and its twin | exit 0, no failed trap, stores unchanged; identical outputs. The committed-outputs test then showed SEARCH_LEDGER.csv lacked the B0 and AC3_LOCO rows | 0 |
| commit `ff98b8d` (runner ledger repair; run 1 logged as debug run 2) | the only change: ledger rows for B0 and AC3_LOCO | |
| `python -B probes/run_analog.py OUT --npz ...` (recorded run, 15:26:22Z to 15:27:03Z, head `ff98b8d`, wall 40.6 s, CPU 38.1 s, 150 MB) | `{"targets": {"T1_24h": "OK", "T2_24h": "OK", "T1b_6h": "OK"}, "outputs": 28, "failed_traps": [], "socket_events": 0, "stores_unchanged": true}` | 0 |
| same command into a second folder | 28 of 28 outputs identical (`evidence/determinism.json`); against run 1 only `SEARCH_LEDGER.csv` differs; the oracle arrays are byte-equal | 0 |
| `p04_bundle/bin/python -B probes/sklearn_crosscheck_analog.py arrays.npz evidence/sklearn_crosscheck.json` | 148 real neighbour queries plus 5 synthetic: same analog sets, distances within 3.9e-15, thresholds within 8.9e-16 (tolerance 1e-9), scikit-learn 1.9.1 | 0 |
| `python -B probes/verify_trace_analog.py audits/predictive-intelligence/phase_11` | 3 traces (T1, T2, T1b): regime, pool inputs, analogs, distances, threshold and number recomputed from plain SQL without `analog.py`, 0 differences; 6 of 6 invalid inputs rejected (`evidence/trace/verify_trace.json`) | 0 |
| `python -B probes/postrun_checks.py audits/predictive-intelligence/phase_11 evidence/postrun_checks.json` | 27 of 27 fold card headers verify with their pool put back; the cohort query reproduces the 3 traced answers and all 93 AC2 and AC3 numbers; day dependence described | 0 |
| `python -m pytest tests/test_predictive_analog.py -q` (with the committed-outputs test) | `51 passed` | 0 |
| `python -B probes/mutation_analog.py evidence/mutation_analog.json` | 47 of 47 caught, 0 survived | 0 |
| `python -m memelab social guard` | 0 violations | 0 |

## What was built

- `memelab/predictive/analog.py` (analog-1; numpy, the standard library, the predictive package and `memelab.social.replay_core.LeakageError`; flag OFF; imported by no other module, tested): the as-of pool checks, AC1 strata, AC2 neighbours, AC3 regime-matched neighbours, LOCO, one analog per cluster, effective N and states, the as-of regime label and the CX-11 trap, the router, the divergence flags, cards and the walk-forward on Phase 07's folds.
- `tests/test_predictive_analog.py`, 51 tests: P01, P09, P12, P13, P14, P21 (regime restriction), P24, P36, P43, P44, NC2-AC, CX-11, future-issued tokens, leave one campaign out, OOD states, minimums, neighbours against a brute force, cards, contract, walk-forward fixture, isolation, committed outputs.
- Probes: `run_analog.py`, `cohort_query.py` (the reproducible cohort query), `verify_trace_analog.py`, `sklearn_crosscheck_analog.py`, `postrun_checks.py`, `mutation_analog.py`.
- Deliverables: `models/ANALOG_MATCHING_SPEC.md`, `experiments/COHORT_COVERAGE.csv` (count and coverage validation), `OOS_PREDICTIONS.csv`, `ANALOG_METRICS.csv`, `REGIME_SERIES.csv`, `REGIME_BREAKDOWN.csv`, `CROSS_PHASE_COMPARISON.csv`, `DIVERGENCE_FLAGS.csv`, `LOCO_SENSITIVITY.csv`, `NC1AC_SEEDS.csv`, `SEARCH_LEDGER.csv`; holdout-start cards `artifacts/<target>/AC*.json` and fold cards `artifacts/folds/`.

## Result

- Folds and B0/B2 equal Phase 07's: split fingerprints equal on all three targets, 76 out-of-sample rows with 0 differences at 6 decimals.
- Coverage (out-of-sample, numbers / rows): AC3 (primary, regime-matched) T1 2 / 24, T2 0 / 8, T1b 21 / 44; AC2 (regime-blind) 23 / 24, 8 / 8, 39 / 44; AC1 (strata) 0 on every target (cells hold a median 10 to 11.5 clusters, below 20). AC3's abstentions are almost all ANALOGS_TOO_FEW:DAYS_BELOW_MIN: the out-of-sample decisions are QUIET/RISK_OFF, and the pool rows with that label fall on fewer than 5 days. That is the regime rule refusing to copy the outcome distribution of the busier days of 2026-10-08 to 10-10, as designed.
- Verdicts: 132 metric rows, every one INSUFFICIENT_DAYS (76), INSUFFICIENT_HISTORY (40) or INSUFFICIENT_EVENTS (16); AC3 against B0: T1 2 rows on 1 day, T2 none, T1b 21 rows with 1 positive on 3 days. No analog model is better or worse than the base rate, B2 or the frozen primaries of Phases 08 to 10 as far as this data can tell; all MODEL_NOT_PROMOTED. NC1-AC INSUFFICIENT_DAYS or INSUFFICIENT_EVENTS.
- Low-history views: NEW_MINTS and NO_PRIOR_DECISION (13, 4 or 3, 24 or 23 rows) are INSUFFICIENT on every model.
- Regime breakdown (P21): every out-of-sample row is QUIET/RISK_OFF except 8 T1b rows on 2026-10-12 (QUIET/RISK_ON); every cell INSUFFICIENT_DAYS or INSUFFICIENT_HISTORY. No regime claim is made.
- Leakage and identity on the real history: NC2-AC 27 of 27 refused; P43-AC 76 of 76 refused; 106 mints first decided at or after a first cutoff, 0 in a pool; P13-AC 9 of 9 refused; P36-AC 28 of 28 refused; P14: 42 same-creator pool rows excluded over 9 answers, 0 same-creator analogs; CX-11: as-of series equal to its truncated recomputation at 79 of 79 instants, full-sample medians relabel 32 of 74 and fail the truncation check at 37.
- Cross-phase join: 228 rows joined to Phases 08 to 10, 0 disagreements in y or B0.
- Divergence flags (step 5): present on many answers (AC3 with analogs: token program differs 20 of 74, transfer fee 14, exit-capacity share 15, friction 13); every answer carries NO_HISTORICAL_EXECUTABLE_DEPTH.
- Leave one campaign out: 0 answers change (narrative tags are rare: 6, 4 and 13 tagged out-of-sample rows).
- Holdout-start cards (9) written, read back identical, tamper refused, `runtime.verify_artifact` passed; an ABSTAIN document per AC3 card passes `contract.validate`; a FORECAST with a probability is refused. MODEL_STALE after 2026-10-31.

## Limitations (stated, not repaired)

1. Day dependence: of 93 answers with a cohort number, 59 have a day Kish ESS below 5 and the largest single-day share reaches 63% (min Kish 2.27). The frozen rule counts days, so G = 30 clusters overstates independence when analogs come from batched export days. A later rule on the day Kish ESS would be a change control.
2. Creator coverage: 115 of 925 Solana decisions lack a creator; their cluster is the mint, so an unrecorded shared deployer is not caught. Dev wallets are not used.
3. Regime inputs are the lab's own exported universe and statuses (version dependent, PI-D-008); the past median is dominated by the hourly export days; no chain-wide data or catalyst category exists.
4. Survivorship check: the newest export at `e245d91` still lists every analog mint (2,220 of 2,220), because the lab never drops a token row, so that count cannot discriminate. The guard is by construction (no current list is an input; tests), and T2 pools hold 27 to 28 crash outcomes.
5. Censoring: each pool period has 36 to 39 censored development decisions that are not in any pool (`evidence/folds.json` `pool_missing_data`), inherited from Phase 06.
6. Only 9 to 10 development decision days and one regime label out of sample; the sealed holdout (Phase 12) and the prospective data are where any analog effect could show.

## Adversarial pass by the phase agent (not independent)

- Tried: a cohort built at the fold cutoff that includes rows decided before it but maturing after it (NC2-AC, refused); a pool that sees later rows (truncation invariance test); a same-symbol twin at distance 0 (stays an analog, never token history); two mints of one deployer (one analog); a WARMUP target (abstains); a full-sample regime (CX-11, caught); a position size (EXECUTION_DATA_MISSING); a freeze-authority target among clean analogs (flag kept beside the number).
- Found and fixed before the recorded run: 5 surviving mutations (tests added). Found after recorded run 1: the ledger missed B0 and AC3_LOCO rows (repair `ff98b8d`, rerun, all other outputs byte-equal).
- Left for the independent skeptic: the day-dependence weakness (limitation 1) and whether the regime label measures the market or the lab's cadence.

## Independent skeptic

Not yet run; `SKEPTIC_PACKET.md` holds the task. The skeptic's counterexample and the repair pass will be recorded here.
