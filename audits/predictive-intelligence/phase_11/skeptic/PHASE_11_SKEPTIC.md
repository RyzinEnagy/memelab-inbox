# Phase 11 independent skeptic review (analog cohorts and regimes)

Reviewer: orchestrator-run independent skeptic (PI-D-013). Branch tip `fcb76be` (outputs `208cdc1`, recorded run at `ff98b8d`, frozen code `0482a60`, pre-registration `46afc85`). Work in `/home/claude/pi_orchestration/skeptic_11` (own clone) and copies of the two private stores under the scratchpad. `phase_06/sealed/` was never opened. No network call, no vendor call, no Firecrawl.

## Verdict

Material failure found: 1 MATERIAL, 7 MINOR. The as-of pool, the regime label's truncation invariance, the frozen gates, the verdicts and the post-commit checks all reproduce. The material finding is in the independence unit: one token can be two "independent" analogs.

## Checks run

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Phase tests | `python -m pytest tests/test_predictive_analog.py -q -p no:cacheprovider` | `51 passed`, exit 0 |
| 2 | Recorded run reproduces | `python -B probes/run_analog.py /tmp/.../run --npz arr.npz` then `diff -r` against the committed folder | exit 0, `failed_traps: []`, 0 socket events, stores unchanged; every experiment CSV, every card, `folds`, `traps`, `serialization_smoke`, `label_sets`, `regime_counts`, `trace` byte-equal (only EXPERIMENT_REGISTRY.csv is repo-only, as stated) |
| 3 | Trace verifier | `python -B probes/verify_trace_analog.py audits/predictive-intelligence/phase_11` | exit 0, 0 differences on 3 traces |
| 4 | Post-run checks | `python -B probes/postrun_checks.py ... /tmp/.../postrun.json` | exit 0, byte-equal to the committed file; 93 numbers, 59 with day Kish ESS below 5, max day share 0.6333 |
| 5 | scikit-learn oracle | `p04_bundle/bin/python -B probes/sklearn_crosscheck_analog.py arr.npz oracle.json` | exit 0, 148 real plus 5 synthetic queries equal, max distance difference 3.9e-15 |
| 6 | Phase mutation probe | `python -B probes/mutation_analog.py /tmp/.../mut.json` | 47 of 47 caught |
| 7 | Seal | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | `"problems": []`, exit 0 |
| 8 | Independent recomputation from raw SQL (no memelab import) | `python3 -I p11_independent.py dev.sqlite fs.sqlite <clone> p11_independent_out.json` | 8 answers (T1 AC2/AC3, two T1b rows AC2/AC3, T2 AC2/AC3): regime, G, days, raw rate, number or abstention all equal (T2 AC3 abstains with 4 days, as committed) |
| 9 | All 152 AC2/AC3 answers from my own code | `python3 -I p11_unionfind_effect.py` | 152 of 152 equal to the committed numbers or abstentions |
| 10 | Fold pools and regime from raw SQL | `python3 -I p11_pool_regime_check.py` | 9 of 9 committed fold pools equal the SQL pool at the cutoff; 0 rows decided at or after or maturing after the cutoff; 0 first seen after it; regime label equal at 79 of 79 instants; each label unchanged when every later decision is deleted (79 of 79) |
| 11 | Minimums | scan of `OOS_PREDICTIONS.csv` | 0 numbers with G below 20, days below 5 or a reason; coverage AC3 2/24, 0/8, 21/44, AC2 23/24, 8/8, 39/44 as stated |
| 12 | Frozen gates | code constants against the checklist, registry and `contract.ACCEPTANCE`; `baselines.verdict` | K 30, OOD 0.95, m 20, G 20, days 5, warmup 5 as registered; `min_effective_days` is a distinct-day count in Phase 07's frozen `verdict` too, so not loosened |
| 13 | Search ledger | ledger against Phase 10's and the registry | first 2,508 rows equal Phase 10's; 386 Phase 11 rows (AC1 12, AC2 24, AC3 72, LOCO 12, B0 12, B2 12, NC1 240, 2 debug runs) |
| 14 | Own mutations | `python3 p11_own_mutations.py p11_own_mutations.json` | 9 of 18 caught (see m3) |
| 15 | Full suite at `fcb76be` | `python -m pytest tests -q -p no:cacheprovider` | `1 failed, 1386 passed in 236.72s`, only the known `test_dedup_corroboration_resurface_denial`; stray `data/reports/..._BRETT_0x532f.md` removed by hand |
| 16 | Guard and release audit | `python -m memelab social guard`; `tools/release_audit.py --history` on a single-branch clone | guard 0 violations, exit 0; `Needs action: no.`, exit 0 |

## Findings

### M1 (MATERIAL): one token counted as two independent analogs; the frozen holdout-start cards carry it

`cluster_of` keys each pool row by that row's own creator field (`creator:<wallet>`, else `mint:<chain>:<mint>`). In the development store the creator field of two mints changes between decisions: `6p6xgHyF7A...` has no creator on one decision and `5e2qRc...` on four; `MukLDtJ8...pump` flips between `Ex48bN...` and `6SJHhn...` across 36 decisions. Each of these mints therefore sits in two clusters, and both clusters can be among the K nearest.

- The phase's own trace shows it: the T1 AC2 trace answer has `G` 30 but `analog_mints` 28 (`6p6xgHyF7A` and `MukLDtJ8` twice each); T2 AC2 and T1b AC2 and AC3 have `analog_mints` 29.
- Over every out-of-sample answer (`p11_dupmint_scan.py`): 98 of 152 AC2/AC3 answers hold one mint twice, 76 of them answers with a number (of 93).
- Clustering by connected components of mint and creator instead (`p11_unionfind_effect.py`): 13 numbers change (largest 0.040) and 3 answers move between a number and an abstention. No verdict changes (all INSUFFICIENT).
- The holdout-start cards frozen for Phase 12 store these split clusters in `body.pool` (checked on `artifacts/T1b_6h/AC3_KNN_REGIME.json`), so Phase 12 would inherit the defect.
- This contradicts checklist G7 ("one analog per cluster", "duplicate windows of one token or one deployer never count twice"), PI-D-061 ("one analog per cluster") and the P14 scenario ("purge duplicate clusters"). The P14-AC trap only checks the target's own creator, so it passes.
- Repair: cluster by connected components over (mint, creator) across the pool (union-find), a test with one mint under two creator values, a mutation that reverts it, rerun and refreeze the cards.

### m1 (MINOR): "Effective N = G" overstates independence

PI-D-061, HANDOFF and the checklist call G "effective N". The phase discloses that 59 of 93 numbers have a day Kish ESS below 5 (reproduced). A design-effect view with the day ICC of the development labels (one-way ANOVA: 0.02 T1, 0.06 T1b, 0.089 T2; noisy) gives `n_eff = G / (1 + (G/Kish - 1) ICC)` below 20 for 11 of 93 numbers (all 8 T2 AC2 numbers, 3 T1b), minimum 16.8, median 23.7; the Wilson 95% half-width on G is too narrow by a median 13% (`p11_day_ess.py`). No verdict uses it, so no claim is wrong, but the wording should be "G = distinct clusters" and the Wilson interval in `OOS_PREDICTIONS.csv` should say it assumes independent analogs (P24).

### m2 (MINOR): the activity half of the regime label partly measures the decision mix

The as-of rule holds (truncation invariance reproduced). But `window_decisions` is 222 to 244 on the hourly days and 12 to 26 on the daily days, and the share of first decisions of a mint is 71 of 652 (11%) on 10-08 to 10-10 against 41 of 68 (60%) on 10-12 to 10-16, with a lower median 24 h volume (12.39 against 13.49 for repeat decisions). Every daily-era instant is QUIET partly because the lab's decision mix changed, not only the market. Within repeat decisions the drop is still there (14.46 to 13.49), so the label is not pure cadence. Tone is the lab's own status mix, not market risk appetite. The spec says "lab-universe proxy"; RISK_ON/RISK_OFF names oversell it.

### m3 (MINOR): unit tests do not pin several rules

Of 18 mutations of `analog.py` outside the phase's probe, 9 survive the test file: the router using AC2 instead of AC3 (nothing on real data exercises the router either), the index cache ignoring the regime (latent: each fold tests one export instant, so no real output changes), ACTIVE on equality, a 48 h regime window, the day Kish ESS replaced by the day count (the number the phase's main limitation rests on), the 10th to 90th percentile divergence band widened to min..max, NC1 with one fixed seed, `degenerate` never true, and pool rows with missing inputs entering the neighbour search. Some would be caught end to end (oracle, trace verifier); none by the tests.

### m4 (MINOR): `new_mint` means "no matured labelled row", not "no earlier decision"

The checklist says `new_mint` is set when the mint has no earlier decision visible at T. The code and the NEW_MINTS view use the matured pool. 2 of 41 new_mint rows had an earlier decision before T.

### m5 (MINOR): metric rows with intervals off zero

`ANALOG_METRICS.csv` / `CROSS_PHASE_COMPARISON.csv`: T1b AC3 against P09's primary has skill 0.219 with mint interval 0.049 to 0.616 (21 rows, 1 positive, 3 days); T1 AC3 against P09 has -2.05 to -0.47 (2 rows, 1 day). The verdict column correctly says INSUFFICIENT_DAYS, but there is no claim column like REGIME_BREAKDOWN's. A reader taking the interval alone would see skill or harm.

### m6 (MINOR): unlabelled looks before pre-registration not in the ledger

The 15:00Z to 15:03Z unlabelled looks (export counts, volumes, statuses, CX-11 flips, creators) and the choice of median volume over the count after seeing them are in the checklist and evidence but not in `SEARCH_LEDGER.csv` as debug runs. No label was read, so no leakage, but the ledger's rule is "every real-data run".

### m7 (MINOR): creator coverage

115 of 925 Solana decisions have no creator (stated limitation 2). M1 shows the creator field is also unstable where present, so the same-creator exclusion (P14) depends on which decision's creator the target carries.

## Counterexample CX-S11 (new)

`p11_counterexample_cx_s11.py`: a pool of 120 fixture tokens plus one mint `DUPMINT` decided twice before the cohort time, once with no creator and once with creator `WALLET_X`, both next to the target. `analog.select("AC2_KNN", ...)` returns G 30 with `analog_mints` 29: `DUPMINT` is selected twice, as `mint:solana:DUPMINT` and `creator:WALLET_X`. All 51 phase tests and all 47 phase mutations pass with this behaviour, and the P14-AC trap passes on real data; nothing in the phase catches it. The real store has two such mints, and they appear twice in 98 of 152 real answers.

## Files

- `/home/claude/pi_orchestration/skeptic/p11_independent.py` (and `_out.json`): raw-SQL recomputation of the pool, regime, neighbours, G, days, Kish and number.
- `p11_dupmint_scan.py` (and `_out.json`), `p11_unionfind_effect.py` (and `_out.json`), `p11_day_ess.py` (and `_out.json`), `p11_pool_regime_check.py` (and `_out.json`), `p11_own_mutations.py` (and `.json`), `p11_counterexample_cx_s11.py`.
