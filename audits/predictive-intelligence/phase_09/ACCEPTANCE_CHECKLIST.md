# Phase 09 acceptance checklist and pre-registration (written before any on-chain feature is computed on a labelled row and before any fit)

Written 2026-10-25 from 22:36Z by the Phase 09 agent, after the entry gate at `c7d6a2f` (suite `1 failed, 1229 passed in 169.59s`, exit 1, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; the stray `data/reports/20261025_2229_BRETT_0x532f.md` and `data/memelab.sqlite-shm`, `-wal` removed by hand; `check_seal.py` exit 0 with `"problems": []`; tracked `data/memelab.sqlite` sha256 `068287c0...` unchanged; both private stores equal to the sha256 in Phase 08's run log), after reading the package (checksums OK), the phase prompt, ADVERSARIAL_SCENARIOS, DATA_TIME_CONTRACT, SCIENTIFIC_VALIDATION, FORECAST_OUTPUT_SCHEMA, BACKTEST_V12_BRIDGE, INTEGRATION_AND_CONFLICTS, NO_GO_DECISION_TREE, every PI-D entry (PI-D-001 to PI-D-053), the Phase 05 to 08 deliverables, `memelab/predictive/*.py`, and, read only through `git show` on `origin/feature/backtesting` at `12f278b`, `memelab/backtest/depth.py`, `memelab/backtest/schema.py` (migration 2), `memelab/backtest/store.py`, `audits/backtesting/data/PROVENANCE.md` and `docs/backtesting/DECISIONS.md` (D-BT-034, D-BT-035). This file, `experiments/EXPERIMENT_REGISTRY.csv` and PI-D-054 are committed before any on-chain feature is computed on a labelled decision and before any model is fitted on real data (PI-D-045 item 5).

What was looked at before writing it, with no label read: over the 925 Solana decision rows of the Phase 05 store, the counts of the score-breakdown rationale patterns (for example "token mechanics clean" 917, "token mechanics N critical issue(s)" 5, "LP risk HIGH/MODERATE/LOW" 323/411/188, "LP locked/burned X%" 861, "no sell route (NO_ROUTE)" 24, "early wallets UNKNOWN" 147), the fatal-flag counts over all 1,500 decisions (CANNOT_EXIT_5K 140 on Solana, INSIDER_DISTRIBUTION 37, NO_SELL_ROUTE 24, MINT_AUTHORITY_ACTIVE 3, FREEZE_AUTHORITY_ACTIVE 0), the snapshot null counts, the token rows' token program (Token-2022 507, SPL 405), and the tables of the tracked lab database (Oct 6 to 7 reads: 33 authority rows, 660 holder rows with CEX, POOL, BURN and DEV classes, 172 cluster rows, 3,774 swap rows, 58 pools with their DEX). No label value, class split or model number was computed. From these counts the on-chain inputs are expected to be present on most labelled rows, so the binding limit stays the frozen training minimum and the few out-of-sample days, exactly as in Phases 07 and 08.

## Status rules carried in

- PROVISIONAL (PI-D-046): Phase 06's 48 h revision re-read is still owed (not before 2026-10-26T13:49Z). Every Phase 09 number, card and verdict carries `PROVISIONAL_PENDING_REVISION_REREAD` and `revision_check_claimed: false`; if the re-read changes any development label, `probes/run_onchain.py` is rerun at the Phase 09 code commit and the outputs are superseded, never edited.
- Phase 09 never opens `phase_06/sealed/`; labels only through `labels.training_labels`.
- Verdicts use Phase 07's frozen functions unchanged (`baselines.evaluate`, `verdict`, `evaluation_gate`, `nc1_verdict`), Holm across the three primary targets per (model, reference). No new verdict code.
- Logistic oracle: scikit-learn `LogisticRegression(solver="newton-cholesky")` in the research venv, coefficients within 1e-9 (PI-D-053), on every fitted fold design and every fitted holdout-start card.
- Anything resting only on fixtures (the collector adapter, the proposed liquidity and exit labels, the wallet-movement rules) is TEST_ONLY for that part and says so.

## What exists and what does not (the data sufficiency statement, fixed before building)

| Item the phase prompt names | State at the lab's decisions | Use here |
|---|---|---|
| Point-in-time pool reserves or depth history | none after 2026-10-08; backtesting PROVENANCE.md: reserves, ticks, bins, LP changes SOURCE_BLOCKED | never substituted by a modern quote; UNKNOWN |
| Historical sell quotes at a size | none after 2026-10-08 (lab DB has 498 quotes of Oct 6 to 7 for 33 thesis rows) | inventory and cross-check only |
| Forward depth and quotes (PI-D-044) | collector pushed on `feature/backtesting` (D-BT-034/035), not deployed: 0 forward rows | read-only adapter contract, fixtures only (TEST_ONLY) |
| Mint, freeze authority, transfer fee, Token-2022 | inside each thesis row (fatal flags, score-breakdown rationale) and token row of the export | as-of features, availability = the export commit (decision time) |
| LP risk and LP locked or burned share | thesis row rationale | as-of features |
| Holder concentration, cluster ownership, dev and insider share | snapshot fields and rationale (lab's own classification) | as-of features; clustering is INFERRED (RugCheck transfer networks), recorded as such |
| Early-wallet direction, wash level | rationale (lab's heuristics) | as-of features, HEURISTIC |
| Swaps, wallet flows, creator transfers, holder history | not exported after 2026-10-07; backtesting: wallet history SOURCE_BLOCKED; lab DB holds Oct 5 to 7 swaps of 6 mints with 10-character signature prefixes | not features; one real cross-check of swaps against candles |
| Pool program version (Raydium, Meteora, Orca, PumpSwap) at the decision | not in the export; lab DB pools table has the DEX of 58 pools read Oct 6 to 7 | inventory only |

## On-chain feature set onchain-1 (fixed)

Source: the decision row of the export (the thesis row and its token row) and the previous decision of the same chain and mint, read only through `features.AsOfView.decisions_of` at the decision time T (audited by `replay_core.Audit`; a row available after T raises). Availability of every value: the export commit time of the row it comes from (decision time of that row), evidence LAB_RECORDED (what the lab recorded at the decision; the chain state behind it is the lab module's reading, not re-verified). Missing reasons all have the AS_OF basis: NOT_IN_UNIVERSE, OUT_OF_SCOPE_CHAIN, UNPARSEABLE, NOT_OBSERVED_BY_LAB (the module output or the rationale line says UNKNOWN or is absent), ABSENT_IN_SNAPSHOT, NO_PRIOR_DECISION, NO_TOKEN_ROW. Rationale text is version dependent (PI-D-008): an unknown line format is UNPARSEABLE, never guessed. No value is imputed in the feature layer.

| Feature | Definition |
|---|---|
| `oc_structural_fatal` | 1 when the row's fatal flags hold a mechanics, liquidity or exitability flag (MINT_AUTHORITY_ACTIVE, FREEZE_AUTHORITY_ACTIVE, PERMANENT_DELEGATE, TRANSFER_FEE_GT_5PCT, TRANSFER_HOOK_UNKNOWN, NON_TRANSFERABLE, HONEYPOT, CANNOT_BUY, HIDDEN_OWNER, EXTREME_TAX, SIMULATION_FAILED, AIRDROP_SCAM, SELFDESTRUCT, CREATOR_PRIOR_HONEYPOT, PROXY_WITH_LIVE_OWNER, TAX_MODIFIABLE_BY_OWNER, LP_RISK_CRITICAL, NO_SELL_ROUTE, CANNOT_EXIT_5K), else 0 |
| `oc_distribution_fatal` | 1 when the fatal flags hold an ownership or distribution flag (LARGEST_HOLDER_GT_15PCT, TOP10_GT_50PCT, DEV_WALLET_FARM, CLUSTER_OWNERSHIP_GT_25PCT, INSIDER_DISTRIBUTION), else 0 |
| `oc_mechanics_issues` | 0 for "token mechanics clean ...", N for "token mechanics N critical issue(s)" |
| `oc_mint_authority_active`, `oc_freeze_authority_active` | with mechanics observed: 1 when the flag MINT_AUTHORITY_ACTIVE (FREEZE_AUTHORITY_ACTIVE) is present, else 0 (the lab derives both from the same mechanics reading) |
| `oc_transfer_fee_pct` | "transfer fee X%" |
| `oc_token2022` | 1 when the token row's program is Token-2022 (`TokenzQd...`), 0 for SPL Token (`Tokenkeg...`) |
| `oc_lp_risk_ord` | LP risk LOW 0, MODERATE 1, HIGH 2, CRITICAL 3 |
| `oc_lp_locked_pct` | "LP locked/burned X%" |
| `oc_exit_cap_share` | snapshot exit_cap_3pct / snapshot liquidity (share of reported liquidity sellable at 3% impact; P08: reported TVL is not exit capacity); missing when either is missing or liquidity is 0 |
| `oc_no_sell_route` | 1 for "no sell route (...)" or the NO_SELL_ROUTE flag, 0 for "route OK, N hop(s)" |
| `oc_route_hops` | N of "route OK, N hop(s)" |
| `oc_round_trip_friction_pct` | "round-trip friction X%" |
| `oc_largest_unexplained_pct` | "largest unexplained holder X%" |
| `oc_cluster_confidence_ord` | cluster confidence LOW 0, MODERATE 1, HIGH 2 (INFERRED clustering) |
| `oc_early_wallet_dir_ord` | early wallets ACCUMULATING 0, HOLDING 1, SCALING_OUT 2, DISTRIBUTING 3, EXITING 4 (UNKNOWN is NOT_OBSERVED_BY_LAB) |
| `oc_wash_ord` | wash LOW 0, MODERATE 1, HIGH 2 |
| `oc_capture_delay_s` | decision time minus the snapshot's own collector time `t` (how stale the on-chain reading is at the decision); a `t` after the decision is INCONSISTENT_TIME and every snapshot-based value of the row is refused (P36) |
| `oc_d_log1p_liquidity`, `oc_d_log1p_exit_cap`, `oc_d_adj_top10_pp`, `oc_d_lp_locked_pp` | change since the previous decision of the mint (decision time strictly before T): ln(1 + now) - ln(1 + before) for liquidity and exit capacity, percentage-point difference for the others |
| `oc_authority_switch` | 1 when mint or freeze authority state differs from the previous decision, 0 when equal (both observed) |
| `oc_fee_change_pp` | transfer fee now minus before |
| `oc_prior_gap_h` | hours since the previous decision |

Reused version 2 columns (not redefined): `thesis_adj_top10_pct`, `thesis_cluster_pct`, `thesis_dev_pct`, `thesis_insider_pct`, `thesis_holders`, `thesis_net_buyers_24h`, `thesis_log1p_exit_cap_3pct_usd`; where onchain-1 reads the same snapshot field the value must equal the stored version 2 snapshot at 10 significant digits (adjusted top-10 and the exit capacity inside `oc_exit_cap_share`), else the run stops.

Not built, recorded UNKNOWN in the source ledger: sell concentration, swap net flows (beyond the version 2 net buyers count), creator transfers, LP removal events (only the change proxies above), fee authority changes beyond the fee value, pool program version at the decision, holder classes beyond the lab's adjusted numbers, wallet cluster flows.

## Candidate models (one configuration each, no tuning)

Fitted on each fold's training rows only, a fit only when the rows a model uses reach 100 events and 20 per class, else INSUFFICIENT_HISTORY. Cards are JSON read by numpy code (no pickle), with model sha, onchain-1 and version 2 feature-set sha, cutoff, label-set and data-snapshot sha.

| Id | Model | Inputs | Fixed settings |
|---|---|---|---|
| R1 `OC_RULE` | the simple on-chain rule as a forecaster: training prevalence per cell of (`oc_structural_fatal`, `oc_distribution_fatal`), shrunk to B0 with m = 20 (the B1 and B3F convention); a missing cell value gives B0 | 2 flags | m = 20 |
| R0 `OC_VETO` | the hard structural veto as an alarm, not a probability: alarm when `oc_structural_fatal` = 1 | 1 flag | counts only (hits, misses, false alarms, correct rejections, lead time) |
| M1 `OC_LOGIT` | L2 logistic regression | required `oc_structural_fatal`, `oc_distribution_fatal`; optional (median fill and missing indicator, AS_OF missingness only) `oc_lp_risk_ord`, `oc_lp_locked_pct`, `oc_exit_cap_share`, `oc_largest_unexplained_pct`, `thesis_adj_top10_pct`, `oc_wash_ord` | C = 1.0, `stats.Prep` |
| M2 `OC_LOGIT_B2` (primary) | L2 logistic regression | B2's columns (liquidity, market cap, 24 h volume, fatal flag required; token age optional) plus M1's columns (same required and optional split) | C = 1.0, `stats.Prep` |
| M3 `OC_LOGIT_TREND` | L2 logistic regression | M2's columns plus optional `oc_d_log1p_liquidity`, `oc_d_log1p_exit_cap`, `oc_d_adj_top10_pp`, `oc_d_lp_locked_pp` | C = 1.0, `stats.Prep` |
| A1 `OC_B2_TC` | B2's columns only, fitted on M2's training rows | B2's columns | as B2 |
| NC1-OC | M2 refitted on training labels permuted inside each fold's training rows | as M2 | seeds 0 to 19 |
| B0, B2 | Phase 07's, refitted by `baselines.fit_b0` and `fit_b2` in the same folds | as Phase 07 | out-of-sample numbers must equal Phase 07's `OOS_PREDICTIONS.csv` at 6 decimals |

The other onchain-1 features are computed, covered and described, but enter no model. No other model, feature, threshold or calibration variant is run.

## Comparisons, metrics and verdicts (fixed)

| Item | Rule |
|---|---|
| Primary | M2 against B0 (Brier skill), all three primary targets, Holm across the three; T2 (half the price or a halt in 24 h) is the target this phase is about and is reported first |
| Model against the simple on-chain rule | M1, M2 and M3 against R1 on the same rows (`baselines.evaluate(reference="R1")`), verdict by the same function |
| Secondary | M1, M3, R1 and A1 against B0; M2, M3 and R1 against B2; M2 against A1 (incremental value of the on-chain columns on the same rows) |
| Views | ALL, NEW_MINTS, NEW_CREATORS, NEW_NARRATIVES, PIT_ONLY, NO_KEY_CONFLICT |
| Scores and intervals | Phase 07's: Brier, skill, log loss (clip 1e-6), AUC and AP only with 10 per class, day and mint bootstrap 2,000, seed 20261025, wider governs, day interval undefined below 5 days, out-of-sample gate 50 events and 10 per class |
| Early warning (step 4) | for R0 and for M1 to M3 at the fold's B0 as threshold: hits, misses (unseen risks), false alarms (their count is the false-alarm cost; no money value, the targets carry no size), correct rejections; lead time of each hit from the decision to the label's first touch (`first_touch_start`) on T2 and T1; every alarm is raised at the decision, before the label window opens, by construction (checked) |
| Cohorts | route, liquidity bucket, launch age bucket, token program, LP risk, structural flag, week, day; no rate below 20 events |
| Degeneracy (P11, P38) | zero variance flagged DEGENERATE; non-finite raises |
| Coverage | per target: rows with every required input, OOD counts with reasons, per feature missing reasons, parse coverage of the rationale by export day |
| Cost | wall and CPU time, 0 network calls (audit hook), 0 vendor calls |
| Promotion | none: every model MODEL_NOT_PROMOTED |

## Collector adapter (read-only, TEST_ONLY until forward rows exist)

`memelab/predictive/depth_adapter.py`, numpy-free standard library. It never imports `memelab.backtest`, never fetches, never writes: it opens a backtesting database file read-only (`mode=ro`), refuses the tracked lab database and the predictive stores, and checks the migration ledger (`bt_schema_migrations` version 2 or later) and the column sets of `bt_depth_decisions`, `bt_depth_pool_lookups` and `bt_depth_snapshots` as documented in `memelab/backtest/schema.py` at `12f278b` (copied as a fixture with its source path and commit). States: COLLECTOR_NOT_AVAILABLE (no file), SCHEMA_MISMATCH, NO_ROWS, OK. Rules: identity by chain and exact mint (Solana byte for byte; EVM case-insensitive, as the collector); a link to a predictive decision needs the same chain, mint, row sha256 and export time equal to the decision time; every observation is available at its `captured_at` and is post-decision for its own decision (never a feature of that decision; usable for a later decision of the mint); rows stay per pool (P02); `reserve_usd` is reported reserve, never exit capacity (P08); a quote has a number only in state OK (PRICE_DISAGREES, HTTP errors, NOT_ATTEMPTED have none).

Proposed targets (written in `models/LIQUIDITY_TARGET_PROPOSALS.md`, not frozen, not in the registry, no default parameters in code): a quote-based liquidity drawdown at a stated size between the first OK quote after the decision and the quote nearest 24 h, an exit-capacity target, and the distribution-event requirements. The proposal code labels fixtures only and carries PROPOSED_NOT_FROZEN; NO_ROUTE or NOT_TRADABLE after an OK baseline is route lost (never a favourable fill, P37); a failed or skipped read is censored.

## Structural veto and size cap (step 5)

`onchain.decision_support(forecast_doc, fatal_flags, depth_context)` returns the forecast beside the lab's fatal flags (every fatal flag is a veto, as the existing overrides; structural ones listed apart) and a size cap computed from depth only (forward OK quotes at the stated sizes, else EXECUTION_DATA_MISSING). The forecast's probability or abstention is not an input to the veto or the cap (tests and mutations); a veto is never cleared by any forecast.

## Wallet movements (P18, P19, developer wallet)

`onchain.movement_role(...)`: a transfer without a pool counterparty is MOVEMENT_NOT_SALE; only a pool-confirmed swap is a sale; an exchange or custody address (lab holder classes CEX, or a supplied custody list) is CUSTODY_OR_EXCHANGE, never INSIDER; a cluster link is INFERRED with its confidence, never OBSERVED; a developer label is OBSERVED only when the address equals the token row's creator or dev wallet and does not look like a mint (the real case: one token row's `dev_wallet` ends in the pump.fun mint suffix, a likely mint address, so DEV_LABEL_SUSPECT). Fixture tests; real holder classes cross-checked.

## Real cross-checks (step 1 and the prompt's historical example)

- Authority: the lab DB `token_authorities` rows (Oct 6 to 7, 8 mints) against `oc_mint_authority_active` and `oc_freeze_authority_active` of the nearest later decision of the same mint.
- Swaps against movements: the lab DB `wallet_transactions` rows (GeckoTerminal trades of 6 mints, Oct 5 to 7, kinds buy and sell only) summed per 5-minute bucket against the Phase 05 store's candles of the decision's point-in-time pool; agreement and disagreement reported (pool fragmentation, P02), signatures are 10-character prefixes, so no transaction is verified on chain (stated).

## Forecast trace

The earliest out-of-sample T2 row (then T1, T1b) by decision time then mint with every M2 input present; the trace lists the decision row's sha256, the parsed rationale lines and fatal flags behind each feature, the fold card (sha, cutoff) and the number or abstention. `probes/verify_trace_onchain.py` recomputes the features from the row JSON with its own parser (no `onchain.py`) and the number from the card's JSON. Invalid inputs that must be rejected: the next decision's values of the same mint declared at their availability (P36), a snapshot `t` after the decision, a non-finite input (P38), the holdout-start card on a development decision (P13).

## New counterexample CX-09 (named before building)

The collector's first pool read or quote for a decision arrives at the first hourly run after the export, often minutes later (`since_export_s`). A plausible wrong design takes that first read as "depth at the decision" and uses it as a feature or as the baseline of a forecast made at the decision. It is post-decision information (it can already show the liquidity pull the label is about). Caught by `depth_adapter.visible_at(T)` refusing any row with `captured_at` after T and by a test that fails when the refusal is removed; the proposed labels use such reads only as label inputs, never as features.

## Checklist

| Id | Check | How it is verified | Fails if |
|---|---|---|---|
| G1 | Package unchanged | `sha256sum -c SHA256SUMS.txt` | a line not OK |
| G2 | Entry gate | suite at `c7d6a2f`, `check_seal.py` | anything but `1 failed, 1229 passed` with the known failure, or seal problems |
| G3 | Pre-registration before any fit | this file, the registry and PI-D-054 committed before `evidence/run_log.json` start | a run before the commit |
| G4 | Numpy core with tests | `onchain.py` numpy and standard library only, `depth_adapter.py` standard library only (tests); `tests/test_predictive_onchain.py` | a third-party import or an untested rule |
| G5 | As-of on-chain features | every value from rows available at T (audit); the next decision never used; NO_PRIOR_DECISION for a first decision; a snapshot `t` after T refused | a later row read |
| G6 | Version 2 consistency | adjusted top-10 and exit capacity equal the stored snapshots for every labelled development decision | one difference |
| G7 | Same frozen folds | split fingerprints equal Phase 07's; B0 and B2 out-of-sample numbers equal at 6 decimals | a difference |
| G8 | Gate use and identity | training rows only from `training_labels`; identity join with chain, mint, time and key; sealed and bake-off paths refused | a row from anywhere else |
| G9 | Count gates | no fit below 100 events or 20 per class on the rows used | a fit below the minimum |
| G10 | Metrics and verdicts | `experiments/ONCHAIN_METRICS.csv` per target, model, reference and view with counts, intervals, verdict, PROVISIONAL | a missing count or verdict, or a claim under the minimums |
| G11 | Model against simple rules | `experiments/RULES_VS_MODEL.csv`: M1 to M3 against R1, R0 alarm counts | missing |
| G12 | Negative controls and traps | NC1-OC under `nc1_verdict`; NC2-OC (next decision's values) refused by allowlist and `validate_rows` on every row; P13 trap refused; P36 snapshot-time trap refused | a trap accepted |
| G13 | Early warning and cohorts | lead time, false alarms, misses per target; cohort tables; no rate below 20 | missing or a rate below 20 |
| G14 | Artifacts | holdout-start cards written, read back identical, model sha recomputed, tamper refused, `runtime.verify_artifact` | a mismatch or a pickle |
| G15 | Contract | an ABSTAIN document from each M2 card passes `contract.validate`; a FORECAST with a probability refused | a probability accepted |
| G16 | Oracle | newton-cholesky within 1e-9 on every fitted logistic design (folds and holdout start) and `stats.Prep` against SimpleImputer plus StandardScaler | a larger difference |
| G17 | Determinism and isolation | two runs, identical outputs (except run log times and trace latency); 0 network calls; stores unchanged; nothing written under tracked `data/`, `inbox/`, `state/` | any difference or write |
| G18 | Adapter contract | fixture tests: schema check, read-only (a write raises), identity, per-pool rows, availability at `captured_at`, own-decision rows never features, states, P08 and P37 semantics; real state on this machine recorded (no database: COLLECTOR_NOT_AVAILABLE); no import of `memelab.backtest` (test) | any failure |
| G19 | Proposals not frozen | registry fingerprint `4b4aabce...` and ACCEPTANCE unchanged; proposal functions have no default parameters; outputs carry PROPOSED_NOT_FROZEN and TEST_ONLY | a frozen or defaulted parameter |
| G20 | Veto and size cap | tests: a forecast cannot clear a veto; the cap does not change with the probability; mutation caught | a forecast-dependent veto or cap |
| G21 | Wallet movements | tests for P18, P19, inferred clusters and the developer-wallet case; real holder classes: CEX rows never insider | a transfer counted as a sale or a CEX as insider |
| G22 | Real cross-checks | authority and swap-against-candle checks written with their counts | missing |
| G23 | Forecast trace | written, recomputed independently equal, four invalid inputs rejected | a difference or an acceptance |
| G24 | Search ledger | `experiments/SEARCH_LEDGER.csv` = Phase 08's ledger plus every Phase 09 configuration, view, NC1 seed and any debug run | an unlogged run |
| G25 | Adversarial scenarios and mutation probe | tests for P02, P08, P09, P18, P19, P25, P36, P37, P44, P13, P38 and the new counterexample CX-09; mutation probe catches every listed mutation | a scenario without a test or a surviving mutation |
| G26 | Flag and imports | flag OFF; no existing module imports the new code; score and fatal flags unchanged | a change |
| G27 | Suite, guard and audits after the commit | full suite (no new failure), `python -m memelab social guard`, `python tools/release_audit.py --history` on a single-branch clone, `check_seal.py`; `git status` clean | any new failure |

## Expected result, stated in advance

The on-chain inputs exist on most labelled rows, so the on-chain models meet the same walls as Phase 07's B2: on T1 and T2 the folds stay near or below 100 training events and the out-of-sample days are 3 and 1 (INSUFFICIENT_DAYS); on T1b the out-of-sample set is 44 events with 3 positive (INSUFFICIENT_EVENTS). No model can be called better or worse than the base rate or than the simple rule; every model is MODEL_NOT_PROMOTED. Liquidity degradation, exit capacity and distribution stay DEFERRED or BLOCKED with a written proposal and an adapter tested on fixtures only. The phase gate is met by honest data sufficiency, the as-of feature layer, the adapter contract and the veto semantics, or by an explicit stop.
