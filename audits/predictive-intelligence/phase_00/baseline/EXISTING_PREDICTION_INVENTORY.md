# Existing forecasting, scoring, outcome, label, replay, calibration and alpha components

Inventory of what already exists at HEAD `f99c6c7`, so later phases reuse it instead of building a parallel copy. Anchors are `file:line`. "Tests" names the test file that exercises the component (from `grep -l` over tests/). "Data" says whether the component has ever run on real data in the tracked record.

Search used for completeness: `git grep -i -E` over memelab/ for brier, log loss, calibration, isotonic, Platt, AUC, sklearn, LightGBM, XGBoost, statsmodels, logistic, conformal, walk-forward (all zero hits), and bootstrap, Wilson, Bonferroni, embargo or purge (hits listed below), plus every module's `def` list.

## Headline

- No probabilistic forecaster, no calibration, no proper scoring rule (Brier, log loss), no trained model and no ML library exists in the repo. Runtime dependency is numpy only (imports across memelab/, tests/ and tools/).
- The repo already has a strong outcome and replay toolkit, all from social-intel phases 11, 16 and 17: an append-only hash-chained signal ledger with PENDING / MEASURED / NON_EXECUTABLE outcomes at 1h, 6h, 24h, 72h and 7d; an event-study engine with matched baselines and Wilson intervals; and a causal replay harness with a cutoff clock, `LeakageError`, chronological splits, embargo, label gate and Bonferroni adjustment. They have run only on fixtures and on the thin real data, where every strategy is INSUFFICIENT_DATA (REPLAY_17.md "Result first").
- The independent social-intel audit (branch `audit/social-intelligence-phase06`, not merged) rates the social engine NOT READY and reports reproduced look-ahead and fixture-versus-real provenance faults in historical screens. Remediation M00 is BLOCKED with acceptance withheld (verification branch HANDOFF). Reuse of these components must keep that status visible and re-test the clocks it touches.
- The 100-point score (m24) and fatal-flag overrides are deterministic rules, not forecasts; they must stay unchanged (EXECUTION_RULES "Integration policy").

## Core scout (memelab/modules, deterministic, per Bundle)

| Component | Anchor | What it outputs | Kind | Tests | Data |
|---|---|---|---|---|---|
| m24 opportunity ranker, 100-point score | m24_opportunity_ranker.py:478 `derive_components`, :592 `score`, :41 `MISSING_CAP`, :44 `STATUSES` | 8 components (15/15/10/10/15/10/10/15), total, breakdown | rule score | test_m21_28.py, test_evm.py, test_social_research.py | yes: every thesis in the state export carries `score` |
| m24 fatal flags | m24_opportunity_ranker.py:494 `fatal_flags` (e.g. :569 WASH_TRADING_HIGH) | FATAL flag list forcing REJECTED or a risk status | veto rules | same | yes (`fatal_flags_json` in theses) |
| m24 status | m24_opportunity_ranker.py:625 `assign_status` | REJECTED ... ENTRY CONDITIONS MET (10 statuses) | rule classifier | same | yes |
| m14 breakout classifier | m14_breakout_classifier.py:33 `CLASSES`, :140 `analyze` | NO_BREAKOUT, EARLY_BREAKOUT_ATTEMPT, CONFIRMED_BREAKOUT, BREAKOUT_RETEST, FAILED_BREAKOUT, RECLAIM | rule classifier on candles | test_m13_18.py, test_m21_28.py | yes, inside theses (`structure` in snapshot_json; breakout not exported separately) |
| m13 price structure | m13_price_structure.py:226 `analyze`, :34 `find_swings`, :66 `cluster_zones` | UPTREND, DOWNTREND, RANGE, TRANSITION, PRICE_DISCOVERY; support and resistance zones | rule features | test_m13_18.py | yes (snapshot_json `structure`, `nearest_support`, `nearest_resistance`) |
| m15 entries and invalidation | m15_entry_invalidation.py:56 `analyze` | entry zones by style, invalidation levels | rule plan | test_m13_18.py | yes (`entries` table, 1,465 rows on main) |
| m16 risk / reward | m16_risk_reward.py:28 `_ev_range`, :37 `analyze` | four scenarios, R multiples, expected-value RANGE from configurable probability bands; text at :177-178 says the bands "are priors, not measured frequencies" and "nothing here is a forecast" | prior bands, explicitly not calibrated | test_m13_18.py | inside reports only |
| m17 sizing, m18 exits | m17_position_sizing.py:88, m18_exit_planning.py:39 | size under risk and liquidity constraints; exit plan | rules | test_m13_18.py | reports only |
| m20 manipulation | m20_manipulation_detection.py:12 `analyze` | wash and manipulation labels (turnover, organic share, tx per trader) | heuristic flags | none direct (test_m21_28.py feeds m24 a hand-made manipulation dict) | inside theses via fatal flags |
| m21 lifecycle | m21_lifecycle_classifier.py:17 `STAGES`, :82 `analyze`, :65 `_confidence_label` | lifecycle stage with a confidence label from evidence families | rule classifier | test_m21_28.py | yes (`lifecycle` in theses) |
| m22 relative strength | m22_relative_strength.py:63 `analyze` | token change minus SOL, BTC and peer medians at 1h, 6h, 24h | feature | test_m21_28.py | reports only |
| m25 watchlist monitor | m25_watchlist_monitor.py:8 `compact_snapshot`, :43 `diff` | the snapshot stored in `theses.snapshot_json`; change detection against the previous thesis | snapshot and diff | none found | yes: 1,801 snapshots across exports |
| m27 post-trade review | m27_post_trade_review.py:62 `_mae_mfe`, :84 `review`, :431 `store_review` | MAE, MFE, decision-quality review of a closed position | outcome for real positions | test_m21_28.py | no: `positions`, `exits`, `trade_reviews` are empty |
| m28 statistical analysis | m28_statistical_analysis.py:38 `sample_flag`, :58 `load_trades`, :178 `stats`, :276 `bootstrap_diff_ci`, :289 `compare_signal` | grouped trade statistics, n thresholds (20, 50), bootstrap CI on expectancy difference | evaluation over closed trades | test_m21_28.py | no trades to read |
| m23 thesis | m23_trade_thesis.py:8 `unacceptable_conditions`, :37 `assemble` | thesis text and invalidation text | text | indirect | yes |

## Catalyst, chains and launch layers

| Component | Anchor | What it outputs | Kind | Tests | Data |
|---|---|---|---|---|---|
| catalyst assessment | catalyst/assess.py:17 `GRADE_PTS`, :28 `assess`, :176 `_price_move_before`, :189 `store` (`price_at_discovery`) | eight graded components, triage score (sorting only), verdict EVENT_ONLY ... WATCH_FOR_ENTRY / REJECTED | rule grades | test_catalyst.py | not exported; each scheduled session starts empty |
| catalyst symbol-only alerts | catalyst/monitor.py:45-50 | DETERIORATION alert keyed by mint for every watched or linked token whose symbol appears in an unlinked NEGATIVE event title (`norm_tokens`); the text says "verify it is the same asset" | heuristic alert by symbol (P01 path, skeptic F3) | none found | not exported |
| catalyst outcomes | catalyst/monitor.py:64 `record_outcomes`; table catalyst/schema.py:136 | price change at 1h, 6h, 24h, 72h after assessment, from the first market snapshot at or after the horizon (no maximum wait) | outcome label | none | not exported |
| catalyst token links | catalyst/match.py:109 `link_events` | NAMED_IN_SOURCE / STRONG by exact address; TICKER_MATCH or NAME_MATCH graded MODERATE, WEAK or AMBIGUOUS | identity link | test_catalyst.py, test_catalyst_firecrawl.py | not exported. P01 risk: a single visible ticker candidate is linked MODERATE (probe `p01_ticker_identity_probe.py`), and catalyst outcomes key on that mint |
| launch cohort statistics | launch/cohort.py:31 `launchpad_stats`, :62 `comparables`, :104 `followup_mints`; constants :16-18 (`MIN_N` 20, `ALIVE_USD` 20,000, `RUG_FRACTION` 0.1) | graduation rate, reach 100k and 1M rates, survival 24h and 7d, collapse rate, comparables distributions or INSUFFICIENT HISTORY | base rates and outcome labels | comparables: test_launch.py; launchpad_stats and followup_mints: none | 1,422 launches exported, outcomes on 19 (24h), 8 (7d) and 2 (30d), below MIN_N 20; rug_flag NULL in every row (corrected in repair pass 2, skeptic F2) |
| launch horizon fill | launch/discover.py:383 | mcap_24h / 7d / 30d read in 20-48 h, 6-10 d, 27-40 d windows, no read time stored | outcome label | test_launch.py (partly) | as above |
| launch ranker | launch/ranker.py:40 `score` | pre-launch opportunity score 100 with data completeness and confidence | rule score | test_launch.py | launch_scores not exported |
| launch monitor | launch/monitor.py:67 `price_discovery`, :34 `windows`, :159 `handover` | PARABOLIC OPEN, PUMP AND DUMP, BASE, RANGE, ORDERLY TREND, FAILED LAUNCH, SELL-OFF AND RECOVERY; expected vs actual | rule classifier | test_launch.py | 124 monitor rows (2026-10-08/09) |
| market regime | chains/regime.py:45 `compute` | RISK-ON, NEUTRAL, RISK-OFF, HIGH-VOLATILITY SPECULATION, CAPITAL FLIGHT with a size multiplier | rule regime label | test_ecosystem.py | 23 regime snapshots, 2026-10-07 to 10-23 |
| chain rotation (SOI) | chains/rotation.py:64 `score_chain`, :172 `compute` | 0-100 Speculative Opportunity Index per chain, trend vs previous score | rule score | test_ecosystem.py | 207 chain scores |
| narrative lifecycle | chains/narrative.py:30 `compute` | EMERGING, ACCELERATING, MANIA, EXHAUSTING, DEAD, MATURE from stored 14 and 30 day highs | rule classifier with history | test_ecosystem.py | 925 narrative snapshots |
| emerging chains | chains/emerging.py:23 `detect`, :120 `benchmark_baskets` | MONITOR / BUILD PARTIAL / BUILD FULL; cap-bucket benchmark baskets | rules | test_ecosystem.py | 88 baskets |

## Social and trader intelligence (memelab/social)

| Component | Anchor | What it outputs | Kind | Tests | Data |
|---|---|---|---|---|---|
| signal ledger engine | outcomes_core.py:35 `STATUSES`, :40 `HORIZON_NAMES`, :120 `market_at_generation`, :169 `make_signal`, :378 `evaluate`, :544 `coverage` | per signal and horizon: PENDING, MEASURED, MISSING, NON_EXECUTABLE, INVALIDATED; `return_mid_gross`, `return_net_modeled`, `return_net_quoted`, MAE/MFE with gap rule | forward outcome labels with execution realism | test_social_outcomes.py (28) | fixtures only; ledger is private and empty in the repo |
| signal ledger store | outcomes_ledger.py:45 `default_path` (data/private/signal_ledger.sqlite), :104 `record_signal`, :225 `evaluate_all`, :272 `verify` | append-only, hash-chained journal; UPDATE and DELETE refused by triggers | immutable outcome store | test_social_outcomes.py | none |
| information alpha (event study) | alpha_core.py:110 `median_ci`, :125 `wilson`, :205 `entry_for`, :230 `exit_for`, :256 `net_return`, :358 `_baseline`, :565 `_score`, :650 `evaluate`; selection rules :65 | per-call returns at 1h to 7d vs matched comparison tokens, net of delay and costs; source score with intervals and sample gates | event study and score | test_social_alpha.py (39) | fixtures only |
| alpha store | alpha_store.py:20 `put_series`, :55 `build_input`, :98 `save_run` | stored candles (`as_of_kind` HISTORICAL_CANDLE), runs | data store | test_social_alpha.py | none |
| causal replay | replay_core.py:104 `LeakageError`, :457 `CutoffView`, :644 `outcome`, :667 `controls_for`, :700 `split_bounds`, :719 `LabelGate`, :741 `samples`, :787 `summarize` (Wilson, Bonferroni), :852 `verdict`, :883 `survivorship`, :897 `tune`, :918 `run`, :983 `truncate`, :1013 `leakage_check` | four strategies vs matched controls; chronological 50/25/25 splits, embargo, label gate, leakage proof by truncation | backtest harness | test_social_replay.py (22) | real run on tracked DB plus main inbox: INSUFFICIENT_DATA for all four strategies (REPLAY_17.md) |
| replay sources | replay_sources.py:28 `PROVIDER_LAG` (300 s, HEURISTIC), :52 `from_db`, :130 `from_inbox`, :202 `merge`, :238 `inventory` | read-only adapters from the lab DB and collector files into replay input; candle availability by capture time or provider lag | data adapter | test_social_replay.py, test_social_research.py | yes, read-only over the tracked DB and inbox |
| synthetic world | replay_synth.py:54 `build` | seeded synthetic market with planted pumps, leakage canaries, delistings | fixture generator | test_social_replay.py | synthetic only |
| wallet performance | perf_core.py:128 `wilson`, :180 `parse_ledger`, :890 `run_engine`; perf_analysis.py:33 `position_rows`, :89 `metrics`, :196 `liquidation` | FIFO and AVCO P&L, realized vs unrealized vs liquidation estimate, coverage and score gate | accounting and score gate | test_social_performance.py (57) | fixtures only |
| market context | market_context.py:56 `build_bundle`, :77 `observed_facts`, :149 `_ohlcv_series` | versioned market facts at posting time and fetch time | point-in-time features | test_social_identity.py, test_social_extraction.py | fixtures only |
| chronology | chrono_core.py:364 `evaluate`, :113 `relation`, :121 `gap` | ordered timeline with clock types (SOURCE_PUBLICATION, CHAIN_BLOCK, COLLECTION, CANDLE) and intervals | temporal ordering | test_social_chronology.py (31) | fixtures only |
| narratives | narratives.py:508 `snapshot` | clusters, first-observed time, independent source count, velocity | features | test_social_narratives.py (39) | fixtures only |
| research candidates | research_core.py:112 `attention_lane`, :136 `structure_lane`, :145 `entry_lane`, :220 `build` | social candidates beside the scout with separate lanes; never changes score | integration adapter | test_social_research.py (23) | opt-in; not in scheduled runs |
| alerts baseline | alerts_core.py:14, :64-65 (`conversation_growth`, `baseline_points` 14) | growth against an item's own baseline | heuristic trigger | test_social_alerts.py (28) | dry-run only |
| social claim records (external forecasts) | extraction.py:49-51 (`ASSERTION_TYPES` with 'prediction', `STANCES`, `HORIZONS`); schema.py:579-585 (`social_claim_attributes.assertion_type`, `stance`, `time_horizon` intraday to long_term, `conditional`, `author_position`) | per-claim stance and horizon of a public prediction | external forecasts with a horizon, natural Phase 10 input (skeptic F4) | test_social_extraction.py (28) | fixtures only |
| identity | identity.py:353 `resolve_address`, :456 `resolve_ticker`, :499 `resolve_post`, :600 `token_identity` | exact chain plus contract identity; ticker resolves only through a same-post contract or a registry asset | identity contract | test_social_identity.py (29) | fixtures only |

## Prompt-package concepts versus what exists

| Package concept | Exists? | Where | Gap for this initiative |
|---|---|---|---|
| Immutable observation or decision snapshot | partly | theses `snapshot_json` (m25:8); signal ledger (outcomes_ledger.py) | no input ids, no code version, one time per thesis (FEATURE_TRACE.md gaps 1 and 2) |
| Point-in-time feature store with available_at | partly | social `_avail` clock (replay_core.py `CutoffView`), social_market_facts | core scout features have no per-field availability |
| Outcome or label registry with censoring | partly | outcomes_core.py statuses (PENDING, NON_EXECUTABLE, MISSING); launch cohort; catalyst_outcomes | no target registry, no first-touch target-vs-invalidation label, no liquidity-drawdown label |
| Baselines (prevalence, simple classifier) | partly | matched controls (replay_core.py:667, alpha_core.py:358) | no prevalence baseline, no classifier |
| Walk-forward, purge, embargo, holdout | partly | replay_core.py:700-741 (chronological splits, embargo, label gate) | single split, not walk-forward; no model artifact chronology |
| Calibration, Brier, log loss, abstention | no | | everything |
| Model registry | no | | everything |
| Drift monitoring | no | | everything |
| Backtesting & Stress-Testing v1.2 | no | not on any branch | BACKTEST_NOT_AVAILABLE (P34) |
| MiroFish or behavioral simulation | no | not on any branch | everything, gated on approvals |

## Reuse rules proposed for Phase 01 (not decided here)

- Use `outcomes_core.evaluate` semantics (entry after lag, first midpoint at or after the target, PENDING until matured, no midpoint no return, delisting handling) for any price-based label instead of writing a new one; adapt its input, do not fork it.
- Use the replay harness's `CutoffView` / `LeakageError` / `truncate` pattern for leakage proofs.
- Use only NAMED_IN_SOURCE or STRONG catalyst links (or social `token_identity` resolutions) as identity for training or labels; TICKER_MATCH and NAME_MATCH links are not identity.
- Never use `theses.created_at` as decision_time or available_at without a conservative delay or a separately recorded capture time; it is the collector-run start, and the thesis row was written a median 16.9 min later (PI-D-011).
- Treat stored thesis scores as version-dependent: either recompute with a pinned code SHA or carry the export commit SHA as the version.
