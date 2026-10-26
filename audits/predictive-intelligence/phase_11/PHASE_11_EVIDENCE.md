# Phase 11 evidence: analog cohorts and regime handling for low-history opportunities

Status: PASS after repair pass 2 (the orchestrator's independent skeptic: 1 MATERIAL, 7 minor, counterexample CX-S11; each verified and repaired or recorded, see "Independent skeptic and repair pass 2"; PI-D-063). The sections above that section describe the first pass; where a number changed in the repair, the repair section gives the current value and the outputs in this folder are the repaired run's. Cohort numbers are research numbers only; nothing is promoted or published.

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

## Post-commit results at `208cdc1` (outputs and records commit)

| Command | Result | Exit |
|---|---|---|
| `python -m pytest tests -q -p no:cacheprovider` | `1 failed, 1386 passed in 277.33s`; only the known `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; strays removed by hand; `data/memelab.sqlite` sha256 unchanged | 1 |
| `python -m memelab social guard` | 0 violations | 0 |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | `"problems": []` | 0 |
| `python tools/release_audit.py --history` on a single-branch clone at `208cdc1` | `Needs action: no.` | 0 |
| `git status --short` | clean after the stray removal | |

Files: `postcommit/pytest_summary.txt`, `social_guard.out.txt`, `seal_check.json`, `release_audit_history.summary.txt`.

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

## Independent skeptic and repair pass 2

Review: `skeptic/PHASE_11_SKEPTIC.md` (attempt at `fcb76be`) with its scripts and outputs copied beside it. The skeptic reproduced every output byte for byte, the trace, the oracle, the seal, the suite and the post-run checks, and recomputed 152 of 152 AC2 and AC3 answers and the 9 fold pools from raw SQL. Each finding was verified against the code first.

| Finding | Verified | Repair |
|---|---|---|
| M1 MATERIAL, CX-S11: `cluster_of` keyed each row by its own creator field; 4 development mints carry different creator values on different decisions (none on some, one or two wallets on others), so one mint sat in two clusters and could be two analogs (98 of 152 first-pass answers held a mint twice; the trace shows G 30 with 28 analog mints). The holdout-start cards carried it | yes (`skeptic/p11_dupmint_scan_out.json`; the CX-S11 fixture passes every first-pass test and mutation) | `analog.groups`: connected components (union-find) over (chain, mint) and every creator wallet recorded for that mint in the pool, as of the cohort time; `regroup` sets each row's cluster to its group in `select` and `fit`; the P14 exclusion removes every row in a group that holds the target's mint or the target's own creator. Tests `test_cx_s11_one_mint_under_two_creator_values_is_one_analog`, `test_groups_join_a_mint_and_every_creator_ever_recorded_for_it`, `test_a_target_whose_mint_had_another_creator_excludes_that_deployers_other_mints_p14` fail on the first-pass module and pass now (`probes/cx_s11_check.py`, `evidence/cx_s11_check.json`); three mutations revert it and are caught. On the real history: 0 answers with a mint twice (`evidence/traps.json` P14_AC), G equals the analog mint count on every answer (committed-outputs test). Recorded run repeated, cards refrozen |
| m1: G called "effective N" | yes | wording: G = distinct groups, not an effective sample size (`G_meaning` on every answer); each answer adds the pool's day ICC (one-way ANOVA on the pool labels by day, clipped to 0 to 1), `n_eff_icc = G / (1 + (G / day Kish ESS - 1) x ICC)` and a Wilson interval on it; `wilson_assumes_independent_analogs: true` beside the G interval. No gate uses them (a gate would be change control). On the repaired run: median ICC-N 28.8 (T1 AC2), 22.1 (T2 AC2), 22.2 (T1b AC2), 23.1 (T1b AC3); 8 numbers below 20 (all T1b AC2, minimum 15.7) |
| m2: activity and tone partly measure the lab's decision mix; RISK_ON / RISK_OFF oversell | yes (first-decision share 11% on the hourly days against 60% on the daily days) | recorded, not repaired: the names are kept so the frozen labels stay comparable; the spec, ROADMAP and HANDOFF say they are lab-universe proxies, not market risk appetite. Carried to Phase 12 and 13 (any rename or new input is change control) |
| m3: 9 of the skeptic's 18 mutations survived the tests | yes | tests added for each (router uses AC3, cache kept apart by regime, equality is QUIET, 24 h window, day Kish value, 10th to 90th percentile band, NC1 seeds differ, `degenerate`, missing-input pool rows never candidates); all 9 added to the probe, which now holds 61 mutations and catches 61 |
| m4: `new_mint` meant "no matured labelled row" | yes (2 of 41 rows) | `new_mint` now means no earlier decision visible at T (version 2 `hist_prior_decisions` = 0), falling back to the pool only when unknown; `no_matured_token_rows` and `no_prior_decision` reported apart. The NEW_MINTS view keeps Phase 07's definition (mint absent from the fold's training rows) |
| m5: intervals off zero with no claim column | yes | `claim` column on every metric row: "none: below the frozen minimums; the skill and interval columns are descriptive only" |
| m6: unlabelled looks not in the ledger | yes | logged as debug run 1 in `SEARCH_LEDGER.csv` (4 debug runs now: the looks, the features-only probe, recorded run 1, the first-pass run at `ff98b8d`) |
| m7: creator coverage | yes | the group rule uses every creator recorded for the mint in the pool; 115 of 925 Solana decisions still have none, so a shared deployer that was never recorded is not caught (limitation 2 stands) |

Counterexample CX-S11 and what catches it now: a mint decided twice before the cohort time, once with no creator and once with a wallet (and a third time with a second wallet), next to the target. The first-pass module selects it twice; the repaired one selects it once in AC1, AC2 and AC3 (`test_cx_s11_...`, failing on `0482a60`).

### Repair commits and the rerun

- Repair code `b0fbf80` (2026-10-26T16:08:21Z): `analog.py` (groups, group exclusion, ICC N, new_mint), the runner (claim column, ICC and analog-mint columns, P14 trap counts mints twice, oracle arrays use the groups, ledger entries), the independent verifier (union-find over mints and creators), the mutation probe (61), `cx_s11_check.py`, 12 tests.
- Recorded run at `b0fbf80` and a twin: 28 of 28 outputs identical. Against the first-pass run, 24 files changed (cards, fold cards, traps, smoke, trace and every experiment table except the regime series) and 4 are byte-equal (`folds.json`, `label_sets.json`, `regime_counts.json`, `REGIME_SERIES.csv`) (`evidence/determinism.json`).
- Number changes (`OOS_PREDICTIONS.csv`): AC1 none; AC2 12 numbers changed (largest 0.040) and 2 answers moved between a number and an abstention (T1b still 39 numbers); AC3 1 number changed (0.020) and 1 answer lost its number (T1b 21 to 20); AC3_LOCO the same. Coverage now AC3 2 / 24, 0 / 8, 20 / 44; AC2 23 / 24, 8 / 8, 39 / 44; AC1 0. Day Kish ESS below 5 on 58 of 92 numbers (was 59 of 93). No verdict changed: 132 metric rows, INSUFFICIENT_DAYS 76, INSUFFICIENT_HISTORY 40, INSUFFICIENT_EVENTS 16.
- Checks after the rerun: oracle 148 real and 5 synthetic queries equal (3.9e-15); trace verifier 0 differences, 6 of 6 invalid inputs rejected; post-run checks pass (27 fold cards verify, the cohort query reproduces the trace and all 92 numbers); 63 tests; mutation probe 61 of 61; guard 0 violations; every trap passes.
- Post-commit results of the repair: `postcommit/repair2_*` and `PHASE_11_RESULTS.json`.
