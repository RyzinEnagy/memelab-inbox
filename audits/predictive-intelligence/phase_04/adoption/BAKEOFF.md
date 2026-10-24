# Bake-off (Phase 04)

What this measures: behaviour, cost and correctness of 3 to 6 complementary approaches and of the components around them, on one common point-in-time dataset. What it does not measure: predictive edge. The real sample is small (26 and 33 out-of-sample events), the second dataset is synthetic, and no approach was chosen for a score; the numbers below support no claim of skill over the base rate (package SCIENTIFIC_VALIDATION, PI-D-016).

Decisions that follow from it: INSTALL_DECISION.md. Pins: BOM_LOCKS.md. MiroFish: MIROFISH_FEASIBILITY.md. Machine-readable results: `BAKEOFF_RESULTS.json` (built by `prototypes/summarize.py`, which re-runs every approach and check a third time and requires the same output sha256 as the two measured runs).

## Candidates and roles

From Phase 03 (`phase_03/research/CATEGORY_WINNERS.md`, PI-D-028), not from the package's examples:

| Role | Candidates in this bake-off | Phase 03 evidence |
|---|---|---|
| Probability baseline | numpy logistic (new code), scikit-learn LogisticRegression | SK-3, SK-4 |
| Complex comparator | scikit-learn HistGradientBoosting, LightGBM | LG-2, LG-4 |
| Event time | lifelines CoxPHFitter | LL-1, LL-2 |
| Calibration layer | numpy Platt and Venn-Abers (new code), scikit-learn sigmoid with FrozenEstimator, ip200/venn-abers as oracle, MAPIE offline | SK-4, VA-1, MA-1, MA-2, MA-4, MA-5 |
| Time-ordered splitter | the lab's frozen day walk-forward (new code), purgedcv WalkForwardSplit, scikit-learn TimeSeriesSplit as a negative control | PC-1, PC-3, SK-2, SK-7 |
| Drift | numpy Page-Hinkley (new code), river PageHinkley and ADWIN | RV-1, RV-3 |
| Validation schema | the lab's row validator (new code), pandera | PA-1, PA-2 |
| Behavioral comparator | numpy trader loop (new code), Mesa | ME-1 |
| Behavioral simulator | MiroFish, isolated, mock LLM only | MI-1 to MI-4 |

Every prototype was scanned for the defaults Phase 03 banned (`prototypes/banned_scan.py`, 15 rules, each rule self-tested on a matching and a non-matching example): 0 hits in 26 files (24 prototypes, `runtime.py` and its tests); the one allowed hit is TimeSeriesSplit in `splitter_check.py`, used as the negative control (`evidence/banned_scan.json`).

## The common point-in-time dataset

### Real development sample (BAKEOFF_ONLY)

Built by `prototypes/build_dev_sample.py` (plan, fetch, label) into `data/`:

- Decisions: `memelab/predictive/decisions.py` over the 89 state exports on `main` at `98338a8` (the ref Phase 01 counted from), Solana, priced snapshot, point-in-time pool recorded in the export (PIT_RECORDED route only, so no vendor pool list and no survivorship from today's list), decision before the holdout start 2026-10-17T00:00Z and 6 h label maturity at or before it: 521 decision events on 95 pools.
- Features: B2 of ACCEPTANCE_METRICS.md, all from the decision row and its token row in the export where the row first appears, so available at the decision (`feature_available_at` = decision time = export commit time, PI-D-015): log liquidity, log market cap, log 24 h volume, log token age (from `first_pool_at`, known for 102 of 102 and 157 of 159 events) and the fatal-flag indicator. Status and score are in the file but not used by any approach.
- Labels: frozen registry rules through `contract.reference_candle`, `contract.eligibility` and `contract.path_candles`; barriers +25% and -15%; a candle touching both is AMBIGUOUS_BAR (negative); eligibility before thinning; thinning per target. T1 24 h: 102 events, 30 positive, 77 mints, 9 decision days (2026-10-07 to 10-15). T1b 6 h: 159 events, 23 positive, 80 mints, 10 decision days. Eligibility of the 521 unthinned events: 502 ELIGIBLE, 17 MARKET_INACTIVE, 2 VENDOR_OR_ROUTE_GAP.
- Prices: GeckoTerminal 5-minute OHLCV of the recorded pool, 132 calls from 2026-10-24T08:02:05Z to 08:40:44Z: 115 HTTP 200 and 17 HTTP 429 (each followed by a 60 s wait and a retry), at most 6 calls in any 60 s window (minimum gap 11.1 s), no failure left after retries, breaker never opened; every call logged with URL, retrieval time, status, size and body sha256 (`data/dev_sample_calls.json`); raw bodies kept outside the repository (`/home/claude/pi_research/p04_gt_raw`) and re-hashed before use.
- Holdout protection: every request ended at or before the holdout start (largest `before_timestamp` equal to it). GeckoTerminal's `before_timestamp` is inclusive: it also returned the candle starting exactly at the holdout start for 6 pools. Those 6 candles were dropped before any use and counted; none of the 3 holdout decisions on those pools was decided within the 4,200 s in which such a candle could serve as a reference price, and no holdout decision's path can include a candle before its own entry (`prototypes/holdout_candle_check.py`, `evidence/holdout_candle_check.json`). No decision at or after the holdout start and no label maturing after it is in the sample (asserted by the builder). Neither contacted holdout decision of PI-D-021 has a development row in it.
- Not Phase 06's labels: one read per pool, no 48 h revision re-read, PIT route only, no T2. Phase 06 rebuilds labels with its own backfill. The development outcomes behind these 261 target labels (102 and 159, many on the same decisions) were viewed in this phase; Phase 12's experiment ledger must count the runs below as tried configurations (PI-D-034).

### Synthetic challenge

The Phase 03 shared file (`phase_03/research/SMOKES/_challenge/challenge.csv`, sha256 `18fda40c...`, 3,000 rows, 2,893 labelled). Its 14.6 h embargo band against 24 h labels is not used: the bake-off ignores the file's `split` column and applies the same label-maturity rule as on the real sample, so no training label matures after its fold's cutoff (fold audit below). Censored rows (107) have no label and are never counted as negatives. The trap column `leak_future_ret` (available 6 h after the decision) is never a feature and is refused by both validators.

### Folds

One rule for every approach: the frozen walk-forward of ACCEPTANCE (`core_numpy.day_walk_forward`): expanding UTC day blocks, the first training cutoff at the midnight after 2026-10-11 (the challenge: after its sixth day), training rows decided before the cutoff with labels matured by it, validation on the next UTC day. The frozen first-fold minimum of 100 training events is lowered to 30 for the real sample (the 24 h sample has 67 to 91 matured training events per fold); this is a bake-off setting, not a change to the acceptance plan. Folds: challenge 23 (2,258 out-of-sample rows, 87 positive), T1 24 h 4 (26 rows, 8 positive), T1b 6 h 5 (33 rows, 3 positive). The fold audit (below) passes for every fold of every dataset.

## Approaches compared

Six approaches on the same rows and folds: B0 training prevalence; L2 logistic regression in numpy (LR_NUMPY) and in scikit-learn (LR_SKLEARN) on the same training-only preprocessing; HistGradientBoosting (HGB_SKLEARN) and LightGBM (LGBM) on raw features with native missing values; lifelines Cox on time to the target with competing events kept in the risk set until the horizon (1 - S(horizon) is then the target's cumulative incidence, valid because every training label has complete follow-up). Calibration variants on the logistic: Platt in numpy, scikit-learn sigmoid on a FrozenEstimator, Venn-Abers in numpy, each fitted on the later 30% of the fold's matured training rows with the model fitted on the earlier rows whose labels matured before the first calibration decision. The four numpy approaches were run twice more in a venv that holds numpy 2.5.3 and nothing else.

Results are in the generated tables at the end. What they show:

1. Equivalence: LR_NUMPY and LR_SKLEARN give the same Brier and log loss to 6 decimals on all three datasets (largest probability difference 1.3e-7 on the challenge, `calibration_check.py bundle`); numpy Platt and the frozen sigmoid agree to 6 decimals (largest difference 5.9e-8).
2. Reproducibility: every approach gave the same output sha256 in three fresh processes; the numpy approaches gave byte-identical predictions in the numpy-only venv and in the full research venv, so the essential engine needs nothing but numpy and is independent of which other packages are installed.
3. Cost: numpy approaches ran in 0.11 to 0.21 s with 33 to 40 MB peak memory (Venn-Abers 1.3 s on the 2,258-row challenge because the prototype refits the isotonic step per test point); every scikit-learn, LightGBM or lifelines approach costs 1.2 to 2.7 s and 136 to 150 MB, almost all of it import (cold-start table).
4. Network: 0 socket events in every run (audit hook) and 0 connect, sendto or bind system calls under strace for LightGBM, lifelines, HGB, the numpy logistic, the drift and the schema checks, against 1 for a positive control (`evidence/strace/strace_challenge_approaches.txt`).
5. Calibration in the large: Venn-Abers put its mean prediction outside the Wilson interval of the observed rate on the challenge (0.057 against 0.039) and on the 6 h sample (0.243 against 0.091): with few positives in the later window its merged probability is pulled up. It is a tool for Phase 13 to test, not a default.
6. Scores: on the challenge the logistic variants are 0.0005 to 0.0007 Brier below B0 and the tree models are not; on the real samples every difference rests on 8 or 3 out-of-sample positives over 4 or 5 days. The best real-sample number (HGB on 24 h, Brier 0.177 against B0 0.212) is one of nine approaches on 26 events; it is noise until Phase 12 tests it with the frozen plan, and Phase 04 selected nothing on it.

## Component checks

### Calibration layer (`calibration_check.py`)

- Venn-Abers in numpy against the reference package (`ip200/venn-abers` 1.5.4 in its Phase 03 venv): largest difference in p0, p1 or the merged probability 1.4e-17 over four probe sets: 579 challenge holdout scores, the same with scores rounded to create ties, 4 scores outside the calibration range (where MAPIE's port fails, Phase 03 MA-1), and 200 random scores on a 40-row calibration set. p0 <= p1 and the output inside [0, 1] everywhere.
- MAPIE 1.6.0 offline: `BinaryClassificationController` for precision at least 0.10 and 0.20 at 90% confidence found no valid threshold with 16 calibration positives, so it abstains; `spiegelhalter_p_value` ran (0.63). Its Venn-Abers port and prefit Pipelines are never called (banned scan).

### Splitter and fold audit (`splitter_check.py`)

The fold audit (`core_numpy.fold_audit`) counts, per fold, training rows decided after the test start, training labels maturing after the test start, overlap, training share and, when a splitter declares a training cutoff, rows decided or labels maturing after that cutoff. Results:

| Splitter | Challenge | T1 24 h | T1b 6 h |
|---|---|---|---|
| lab day rule | valid, 23 folds, smallest training share 0.18 | valid, 4 folds, 0.66 | valid, 5 folds, 0.79 |
| lab day rule with the maturity purge removed (mutation) | refused: 2,304 labels mature after their cutoff | refused: 31 | not refused: identical folds, because no 6 h label of a boundary day crosses a fold cutoff in this sample (the mutation changes nothing) |
| purgedcv WalkForwardSplit, default and `purge_horizon=0` | valid, 23 folds, 0.16 | valid, 4 folds, 0.54 | valid, 5 folds, 0.75 |
| scikit-learn TimeSeriesSplit (banned) | refused: 2,308 labels mature after the test start | refused: 87 | refused: 50 |

purgedcv's folds are fixed row counts, so it cannot express the frozen UTC-day rule; it stays an independent oracle. Its docstring says `purge_horizon=None` means no purge, but `src/purgedcv/_base.py:110-111` turns None into a zero horizon and purges; the code is the safe side of that mismatch.

### Drift (`drift_check.py`)

Streams standardised by their first 30% (a training window): the challenge's log liquidity and ret_1h (designed shift in the last 20%) and the 24 h sample's log liquidity (no designed shift). The numpy Page-Hinkley and river's PageHinkley gave identical detection positions on every stream at thresholds 25 and 50. At threshold 50 Page-Hinkley found the liquidity shift 42 rows after it with no false alarm and the ret_1h shift 79 rows after it with one false alarm; ADWIN found both with no false alarm (57 and 97 rows after). With a NaN input, river's PageHinkley and ADWIN keep running with a NaN mean and report nothing for the next 200 inputs; the numpy detector raises instead (P38).

### Validation schema (`schema_check.py`)

On the challenge (2,893 rows) and the 24 h sample (102 rows) both the lab's validator and a pandera schema with the same registered checks accepted the clean table and refused all four traps: a feature available one second after its decision, a missing availability time (declared non-nullable, the Phase 03 skeptic's case), an undeclared column (`leak_future_ret`) and a label that has not matured by the training cutoff. Importing pandera 0.34.1 added `NaN`, `float_`, `string_` and `unicode_` to the numpy module and set `PYARROW_IGNORE_TIMEZONE` and `SPARK_LOCAL_IP` in the process environment.

### Behavioral comparator (`behavior_check.py`)

One trader-reaction model written twice (Mesa agents and a numpy loop), 200 synthetic scenario seeds x 5 seeded runs. Both deterministic over three runs; numpy 0.34 to 0.38 ms per run, Mesa 1.04 to 1.08 ms (the two measured runs); similar frequency distributions (mean hit share 0.024 and 0.020; the random streams differ by design). Outputs are labelled SIMULATOR_FREQUENCY_NOT_A_PROBABILITY and are never scored as forecasts (P27). `import mesa` fails after a plain install of Mesa 3.5.1 (`ModuleNotFoundError: networkx`), measured in the bundle venv (`check__behavior_mesa_plain_install`); the Mesa numbers come from a venv with `mesa[network]`.

### Error semantics (`error_semantics.py`)

| Input | numpy logistic with Prep | scikit-learn logistic | HGB | LightGBM | lifelines Cox | numpy Platt and Venn-Abers |
|---|---|---|---|---|---|---|
| NaN or inf feature | handled as missing (indicator column) | raises ValueError | silent finite output (native missing values) | silent finite output (native missing values) | raises TypeError | raise ValueError |
| all-missing column | dropped by the training-window column rule | raises ValueError | raises ValueError (opaque, from binning) | handled | raises TypeError | raise ValueError |
| constant column | dropped by the column rule | handled | handled | handled | raises ConvergenceError | silent: one value near the prevalence |
| one-class training window | raises ValueError | raises ValueError | silent probability 2e-15 | silent 1e-15 | silent 0.0 | raise ValueError |
| two training rows | silent | silent | silent 0.5 | silent 0.5 | silent | silent |

Raising is the safe answer because `runtime.guarded` turns it into a visible abstention; the silent cases are why the count gates of ACCEPTANCE (at least 100 training events and 20 per class) run before any fit.

### MiroFish

Feasible only as an isolated, unmodified program against a local mock LLM; not reproducible; exits 0 when its LLM is down; refuses to start its service without LLM and Zep keys. Details and numbers: MIROFISH_FEASIBILITY.md.

## Iteration log (what the bake-off changed)

1. First real-data run (before the dataset fix): HGB raised `ValueError: window shape cannot be larger than input array shape` and lifelines raised `ConvergenceError` on both real samples, while the challenge had run cleanly. Cause: the age feature was missing for every row because the builder parsed `first_pool_at` as a number when the export stores ISO text (`normalize.py:81`). Fixes: the builder parses ISO text (age now known for 259 of 261 events), and the lab's preprocessing drops columns that are constant or all missing in the training window (`core_numpy.informative_columns`), applied to every approach. The failing runs are kept in `evidence/first_real_run_failures/`.
2. Error-semantics probe: the numpy logistic, Platt and Venn-Abers returned silent probabilities on a one-class window and NaN through an unprepared logistic; all three now raise (`_check_fit_inputs`).
3. Own adversarial pass on the splitter: the maturity-purge mutation passed the test-start audit on the 6 h sample. Investigation showed the mutation is a no-op there, but on the 24 h sample the test-start check counted 29 leaked labels where the declared-cutoff check counts 31 (2 labels matured between midnight and the first decision of the next day, which would make a model's recorded training cutoff false, P13). The audit now checks the declared cutoff too.
4. Drift thresholds: with raw units, Page-Hinkley at threshold 50 raised 58 false alarms on ret_1h scaled by 100; the streams are now standardised on a training window, and both thresholds are reported.

## Reproduce

All offline except the dataset fetch. From `audits/predictive-intelligence/phase_04/adoption/prototypes/`:

```
python -B build_dev_sample.py plan ../data
python -B build_dev_sample.py fetch ../data RAW_DIR          # network: 132 GeckoTerminal calls at <= 6 a minute
python -B build_dev_sample.py label ../data RAW_DIR          # offline from the raw bodies; asserts the holdout rules
python -B holdout_candle_check.py RAW_DIR
python -B run_measurements.py imports && python -B run_measurements.py approaches && python -B run_measurements.py checks
python -B summarize.py                                        # third run of everything; sha256 must match
python -B banned_scan.py ../evidence/banned_scan.json
python -B render_tables.py ../BAKEOFF.md ../BAKEOFF_RESULTS.json
```

The venvs: `p04_bundle` from `../evidence/bakeoff-bundle.in` with `uv pip compile --override pandas==3.0.5 --universal --generate-hashes --only-binary :all:` and `uv pip install --require-hashes --only-binary :all: --no-deps`; `p04_core` from `docs/predictive-intelligence/locks/core-py313.txt`; `p04_mesa` from `numpy==2.5.3 pandas==3.0.5 scipy==1.18.1 mesa[network]==3.5.1` the same way; the Venn-Abers oracle venv is Phase 03's `ip200__venn-abers`.

## Generated tables

<!-- tables below are generated by prototypes/render_tables.py; do not edit by hand -->

### Approaches: Synthetic challenge (2,893 labelled rows)

| Approach | Venv | Folds | OOS N | Positives | Brier | B0 Brier, same rows | BSS vs B0 | Log loss | Mean p | Observed | Mean p in Wilson 95% | Fold audit | Wall s | CPU s | Peak MB | Same output, 3 runs |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| B0 | bundle | 23 | 2258 | 87 | 0.037049 | 0.037049 | 0.0 | 0.163286 | 0.04133 | 0.03853 | yes | valid | 0.1673 | 0.1443 | 37.6 | yes |
| B0 | core_numpy_only | 23 | 2258 | 87 | 0.037049 | 0.037049 | 0.0 | 0.163286 | 0.04133 | 0.03853 | yes | valid | 0.1859 | 0.1554 | 37.5 | yes |
| COX_LIFELINES | bundle | 23 | 2258 | 87 | 0.036626 | 0.037049 | 0.0114 | 0.158085 | 0.041283 | 0.03853 | yes | valid | 2.1906 | 2.0282 | 138.4 | yes |
| HGB_SKLEARN | bundle | 23 | 2258 | 87 | 0.037228 | 0.037049 | -0.0048 | 0.163452 | 0.03481 | 0.03853 | yes | valid | 2.7052 | 2.5433 | 150.0 | yes |
| LGBM | bundle | 23 | 2258 | 87 | 0.037044 | 0.037049 | 0.0001 | 0.164128 | 0.034603 | 0.03853 | yes | valid | 1.8963 | 1.8146 | 146.9 | yes |
| LR_NUMPY_PLATT | bundle | 23 | 2258 | 87 | 0.036502 | 0.037049 | 0.0147 | 0.155515 | 0.040596 | 0.03853 | yes | valid | 0.1832 | 0.1784 | 39.3 | yes |
| LR_NUMPY_PLATT | core_numpy_only | 23 | 2258 | 87 | 0.036502 | 0.037049 | 0.0147 | 0.155515 | 0.040596 | 0.03853 | yes | valid | 0.208 | 0.1891 | 39.3 | yes |
| LR_NUMPY_VENN_ABERS | bundle | 23 | 2258 | 87 | 0.037855 | 0.037049 | -0.0218 | 0.158679 | 0.056769 | 0.03853 | no | valid | 1.3234 | 1.2628 | 39.6 | yes |
| LR_NUMPY_VENN_ABERS | core_numpy_only | 23 | 2258 | 87 | 0.037855 | 0.037049 | -0.0218 | 0.158679 | 0.056769 | 0.03853 | no | valid | 1.3965 | 1.2872 | 39.7 | yes |
| LR_NUMPY | bundle | 23 | 2258 | 87 | 0.036301 | 0.037049 | 0.0202 | 0.15367 | 0.041187 | 0.03853 | yes | valid | 0.187 | 0.1812 | 39.3 | yes |
| LR_NUMPY | core_numpy_only | 23 | 2258 | 87 | 0.036301 | 0.037049 | 0.0202 | 0.15367 | 0.041187 | 0.03853 | yes | valid | 0.2145 | 0.1915 | 39.3 | yes |
| LR_SKLEARN_SIGMOID_FROZEN | bundle | 23 | 2258 | 87 | 0.036502 | 0.037049 | 0.0147 | 0.155515 | 0.040596 | 0.03853 | yes | valid | 1.6001 | 1.4837 | 145.2 | yes |
| LR_SKLEARN | bundle | 23 | 2258 | 87 | 0.036301 | 0.037049 | 0.0202 | 0.15367 | 0.041187 | 0.03853 | yes | valid | 1.4838 | 1.3256 | 144.1 | yes |

### Approaches: Real development sample, T1 24 h (102 events)

| Approach | Venv | Folds | OOS N | Positives | Brier | B0 Brier, same rows | BSS vs B0 | Log loss | Mean p | Observed | Mean p in Wilson 95% | Fold audit | Wall s | CPU s | Peak MB | Same output, 3 runs |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| B0 | bundle | 4 | 26 | 8 | 0.212494 | 0.212494 | 0.0 | 0.615927 | 0.28398 | 0.307692 | yes | valid | 0.1529 | 0.1197 | 32.7 | yes |
| B0 | core_numpy_only | 4 | 26 | 8 | 0.212494 | 0.212494 | 0.0 | 0.615927 | 0.28398 | 0.307692 | yes | valid | 0.1112 | 0.1097 | 32.7 | yes |
| COX_LIFELINES | bundle | 4 | 26 | 8 | 0.213015 | 0.212494 | -0.0025 | 0.619673 | 0.257661 | 0.307692 | yes | valid | 1.2117 | 1.1991 | 136.1 | yes |
| HGB_SKLEARN | bundle | 4 | 26 | 8 | 0.177049 | 0.212494 | 0.1668 | 0.610746 | 0.217004 | 0.307692 | yes | valid | 1.5469 | 1.3688 | 148.1 | yes |
| LGBM | bundle | 4 | 26 | 8 | 0.227858 | 0.212494 | -0.0723 | 0.691269 | 0.241284 | 0.307692 | yes | valid | 1.2647 | 1.1945 | 145.7 | yes |
| LR_NUMPY_PLATT | bundle | 4 | 26 | 8 | 0.232375 | 0.212494 | -0.0936 | 0.679389 | 0.221097 | 0.307692 | yes | valid | 0.1331 | 0.1219 | 34.0 | yes |
| LR_NUMPY_PLATT | core_numpy_only | 4 | 26 | 8 | 0.232375 | 0.212494 | -0.0936 | 0.679389 | 0.221097 | 0.307692 | yes | valid | 0.1309 | 0.1216 | 34.0 | yes |
| LR_NUMPY_VENN_ABERS | bundle | 4 | 26 | 8 | 0.236912 | 0.212494 | -0.1149 | 0.675396 | 0.30649 | 0.307692 | yes | valid | 0.1538 | 0.1361 | 34.2 | yes |
| LR_NUMPY_VENN_ABERS | core_numpy_only | 4 | 26 | 8 | 0.236912 | 0.212494 | -0.1149 | 0.675396 | 0.30649 | 0.307692 | yes | valid | 0.1459 | 0.1254 | 34.2 | yes |
| LR_NUMPY | bundle | 4 | 26 | 8 | 0.214009 | 0.212494 | -0.0071 | 0.628617 | 0.254384 | 0.307692 | yes | valid | 0.1324 | 0.1183 | 33.7 | yes |
| LR_NUMPY | core_numpy_only | 4 | 26 | 8 | 0.214009 | 0.212494 | -0.0071 | 0.628617 | 0.254384 | 0.307692 | yes | valid | 0.1255 | 0.1167 | 33.7 | yes |
| LR_SKLEARN_SIGMOID_FROZEN | bundle | 4 | 26 | 8 | 0.232375 | 0.212494 | -0.0936 | 0.679389 | 0.221097 | 0.307692 | yes | valid | 1.3455 | 1.2338 | 143.4 | yes |
| LR_SKLEARN | bundle | 4 | 26 | 8 | 0.214009 | 0.212494 | -0.0071 | 0.628617 | 0.254384 | 0.307692 | yes | valid | 1.2197 | 1.1801 | 142.4 | yes |

### Approaches: Real development sample, T1b 6 h (159 events)

| Approach | Venv | Folds | OOS N | Positives | Brier | B0 Brier, same rows | BSS vs B0 | Log loss | Mean p | Observed | Mean p in Wilson 95% | Fold audit | Wall s | CPU s | Peak MB | Same output, 3 runs |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| B0 | bundle | 5 | 33 | 3 | 0.08672 | 0.08672 | 0.0 | 0.322459 | 0.154899 | 0.090909 | yes | valid | 0.1286 | 0.1188 | 32.8 | yes |
| B0 | core_numpy_only | 5 | 33 | 3 | 0.08672 | 0.08672 | 0.0 | 0.322459 | 0.154899 | 0.090909 | yes | valid | 0.1255 | 0.1129 | 32.8 | yes |
| COX_LIFELINES | bundle | 5 | 33 | 3 | 0.079754 | 0.08672 | 0.0803 | 0.291718 | 0.142166 | 0.090909 | yes | valid | 1.3291 | 1.2515 | 136.1 | yes |
| HGB_SKLEARN | bundle | 5 | 33 | 3 | 0.115522 | 0.08672 | -0.3321 | 0.412037 | 0.119395 | 0.090909 | yes | valid | 1.5055 | 1.4159 | 148.2 | yes |
| LGBM | bundle | 5 | 33 | 3 | 0.134531 | 0.08672 | -0.5513 | 0.446202 | 0.135324 | 0.090909 | yes | valid | 1.3758 | 1.243 | 145.8 | yes |
| LR_NUMPY_PLATT | bundle | 5 | 33 | 3 | 0.079261 | 0.08672 | 0.086 | 0.289852 | 0.162289 | 0.090909 | yes | valid | 0.127 | 0.12 | 33.9 | yes |
| LR_NUMPY_PLATT | core_numpy_only | 5 | 33 | 3 | 0.079261 | 0.08672 | 0.086 | 0.289852 | 0.162289 | 0.090909 | yes | valid | 0.1396 | 0.1225 | 33.9 | yes |
| LR_NUMPY_VENN_ABERS | bundle | 5 | 33 | 3 | 0.101936 | 0.08672 | -0.1755 | 0.353091 | 0.242536 | 0.090909 | no | valid | 0.1583 | 0.127 | 34.2 | yes |
| LR_NUMPY_VENN_ABERS | core_numpy_only | 5 | 33 | 3 | 0.101936 | 0.08672 | -0.1755 | 0.353091 | 0.242536 | 0.090909 | no | valid | 0.1371 | 0.1285 | 34.1 | yes |
| LR_NUMPY | bundle | 5 | 33 | 3 | 0.077572 | 0.08672 | 0.1055 | 0.277649 | 0.138274 | 0.090909 | yes | valid | 0.1309 | 0.1213 | 33.8 | yes |
| LR_NUMPY | core_numpy_only | 5 | 33 | 3 | 0.077572 | 0.08672 | 0.1055 | 0.277649 | 0.138274 | 0.090909 | yes | valid | 0.1283 | 0.1189 | 33.8 | yes |
| LR_SKLEARN_SIGMOID_FROZEN | bundle | 5 | 33 | 3 | 0.079261 | 0.08672 | 0.086 | 0.289852 | 0.162289 | 0.090909 | yes | valid | 1.3647 | 1.2402 | 143.2 | yes |
| LR_SKLEARN | bundle | 5 | 33 | 3 | 0.077572 | 0.08672 | 0.1055 | 0.277649 | 0.138274 | 0.090909 | yes | valid | 1.2595 | 1.202 | 142.7 | yes |

### Cold start (import in a fresh process, median of 5, offline)

| Component | Modules imported | Interpreter | Wall s | CPU s | Peak MB | Socket events | Heavy modules loaded |
|---|---|---|---:|---:|---:|---:|---|
| lab_runtime_stdlib | `memelab.predictive.runtime` | system 3.13 | 0.0398 | 0.0387 | 17.8 | 0 | none |
| core_numpy_prototype | `core_numpy` | p04_core | 0.0958 | 0.0943 | 26.8 | 0 | numpy |
| numpy | `numpy` | p04_core | 0.102 | 0.0973 | 26.7 | 0 | numpy |
| pandera | `pandera.pandas` | p04_bundle | 0.5669 | 0.5352 | 81.6 | 0 | numpy,pandas,pydantic |
| mesa | `mesa` | p04_mesa | 0.7932 | 0.752 | 105.3 | 0 | numpy,pandas,scipy,networkx |
| purgedcv | `purgedcv` | p04_bundle | 1.0868 | 1.0672 | 131.7 | 0 | numpy,pandas,scipy,sklearn,joblib |
| river_drift | `river.drift` | p04_bundle | 1.1374 | 1.1304 | 136.7 | 0 | numpy,pandas,scipy,sklearn,joblib |
| lifelines | `lifelines` | p04_bundle | 1.1415 | 1.0839 | 131.3 | 0 | numpy,pandas,scipy |
| crepes | `crepes` | p04_bundle | 1.1755 | 1.1637 | 143.4 | 0 | numpy,pandas,scipy,sklearn,joblib |
| sklearn_linear_calibration | `sklearn.linear_model,sklearn.calibration,sklearn.frozen` | p04_bundle | 1.2268 | 1.1595 | 141.3 | 0 | numpy,pandas,scipy,sklearn,joblib |
| sklearn_hgb | `sklearn.ensemble` | p04_bundle | 1.2295 | 1.1747 | 146.8 | 0 | numpy,pandas,scipy,sklearn,joblib |
| interpret | `interpret.glassbox` | p04_bundle | 1.2402 | 1.2052 | 146.4 | 0 | numpy,pandas,scipy,sklearn,joblib |
| venn_abers_oracle | `venn_abers` | ip200__venn-abers | 1.2846 | 1.1706 | 137.6 | 0 | numpy,pandas,scipy,sklearn,joblib |
| mapie | `mapie.risk_control,mapie.metrics.calibration` | p04_bundle | 1.2861 | 1.1933 | 143.9 | 0 | numpy,pandas,scipy,sklearn,joblib |
| lightgbm | `lightgbm` | p04_bundle | 1.2865 | 1.153 | 139.9 | 0 | numpy,pandas,scipy,sklearn,lightgbm,joblib |
| statsmodels | `statsmodels.api` | p04_bundle | 1.4793 | 1.3946 | 159.5 | 0 | numpy,pandas,scipy,statsmodels,joblib |
| arch | `arch.bootstrap` | p04_bundle | 1.5865 | 1.5143 | 159.4 | 0 | numpy,pandas,scipy,matplotlib,statsmodels |

### Wheels for CPython 3.13 at the exact version (PyPI file lists)

| Package | Requires Python | Linux x86_64 | Windows x86_64 | macOS arm64 | Note |
|---|---|---|---|---|---|
| arch==8.0.0 | >=3.10 | yes | yes | yes |  |
| crepes==0.9.1 | >=3.10 | yes | yes | yes |  |
| interpret-core==0.7.8 | None | yes | yes | yes |  |
| lifelines==0.30.3 | >=3.11 | yes | yes | yes |  |
| lightgbm==4.7.0 | >=3.10 | yes | yes | yes |  |
| mapie==1.6.0 | >=3.10 | yes | yes | yes |  |
| mesa==3.5.1 | >=3.12 | yes | yes | yes |  |
| numpy==2.5.3 | >=3.12 | yes | yes | yes |  |
| pandas==3.0.5 | >=3.11 | yes | yes | yes |  |
| pandera==0.34.1 | >=3.10 | yes | yes | yes |  |
| purgedcv==0.1.11 | >=3.11 | yes | yes | yes |  |
| river==0.26.1 | >=3.11 | yes | yes | yes |  |
| scikit-learn==1.9.1 | >=3.11 | yes | yes | yes |  |
| scipy==1.18.1 | >=3.12 | yes | yes | yes |  |
| statsmodels==0.15.0 | >=3.10 | yes | yes | yes |  |
| venn-abers==1.5.4 | None | no | no | no | sdist only: refused by the install route |

### Component checks (cost and reproducibility)

| Check | Wall s | CPU s | Peak MB | Socket events | Same output, 3 runs | Exit 0 |
|---|---:|---:|---:|---:|---|---|
| behavior_mesa | 1.2601 | 1.2378 | 106.6 | 0 | yes | yes |
| behavior_mesa_plain_install | 0.5919 | 0.5273 | 88.5 | 0 | yes | no (expected for mesa_plain_install) |
| behavior_numpy | 0.4759 | 0.4464 | 33.6 | 0 | yes | yes |
| calibration_bundle | 1.3373 | 1.2487 | 150.3 | 0 | yes | yes |
| calibration_oracle | 1.7028 | 1.5692 | 143.9 | 0 | yes | yes |
| drift | 1.2551 | 1.1707 | 140.8 | 0 | yes | yes |
| schema | 0.7657 | 0.7191 | 89.6 | 0 | yes | yes |
| splitter | 1.3708 | 1.2891 | 143.7 | 0 | yes | yes |
