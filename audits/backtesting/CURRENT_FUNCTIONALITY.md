# Current functionality evidence matrix (baseline f99c6c7)

Produced in Phase 00 by a read-only code inventory, then spot-checked by the phase auditor (items marked [checked] were re-read or reproduced by script). Line numbers refer to `memelab/` at the baseline SHA.

Status vocabulary for the backtesting needs: EXISTS_TESTED, EXISTS_UNTESTED, PARTIAL, MISSING.

## A. Capabilities that matter for backtesting and stress testing

| Need | Where it exists today | Status | Note |
|---|---|---|---|
| Exact mint identity, ticker display-only | m02 identity :22, normalize keys by mint, chains.registry.norm_address | EXISTS_TESTED | tokens table keyed by mint; EVM lowercased |
| Pool identity per venue | normalize pools from DexScreener/GT :123-197, `pools` table | PARTIAL | no pool_type (CPMM/CLMM/DLMM) field; m05 sets only a concentrated flag :27 |
| Observation time on stored rows | every core table has `observed_at` = bundle observed_at (pipeline.py:189) | PARTIAL | one clock per analysis; `_at` set at run start, earlier than contained rows [checked C3] |
| Separate event/available/decision/execution times | social replay_core (`_avail`, CutoffView, Audit), outcomes_core, chrono_core three clocks, catalyst four timestamps | EXISTS_TESTED in social/catalyst; MISSING in core scout | core pipeline has no available_at or decision_time |
| As-of join with leakage guard | social/replay_core.py CutoffView :457, Audit :441, leakage_check :1013 | EXISTS_TESTED (social replay only) | reusable pattern; not wired to core tables |
| Immutable observation trail | outcomes_ledger hash chain with abort triggers :26-40 | EXISTS_TESTED (private ledger only) | core tables use INSERT OR IGNORE, no triggers; tokens/watchlist updated in place |
| Historical OHLCV | GT pool ohlcv day1x120, hour1x400, minute15x400 in deep plans (plan.py:95-101) | PARTIAL | fetched for current analysis only; not stored as series in DB; unfinished bar not filtered [checked C2] |
| Historical swaps | GT trades last page (plan.py:99-101), Helius tx history for wallets | PARTIAL | recent window only |
| Historical pool reserves / ticks / bins | none | MISSING | base/quote reserves stored, never used |
| Constant-product swap math | none | MISSING | |
| CLMM/DLMM math | none | MISSING | concentrated flag only |
| Present-tense executable depth | Jupiter quotes BUY/SELL at $500..$100k (plan.py:37, :102-107), m06, m17, m18 | EXISTS_TESTED (module level) | quote slot not read by m06; impacts are fractions |
| Token-2022 transfer fee in costs | m08 parses it :32-35/:85-102; m06/m17 read a key nobody writes | PARTIAL (bug) [checked C1] | fee dropped from friction and sizing haircut |
| Network fee, priority fee, failed tx cost | none | MISSING | |
| Position sizing (risk and liquidity) | m17 | EXISTS_TESTED | never above largest tested size |
| Exit realizable value | m18 realizable = displayed*(1-impact) :208-226 | EXISTS_TESTED | extrapolates beyond tested size |
| Portfolio stress | m26 STRESS SCENARIO SOL -20%, meme -50%, liquidity -40% :25, :258-290 | EXISTS_TESTED (unit mismatch) | percent vs fraction issue :23, :62-64 |
| Price structure, breakout, entries, R/R | m13, m14, m15, m16 | EXISTS_TESTED | discretionary-free but not bar-close safe; R/R bands are fixed priors |
| Statistics | m28 bootstrap CI :276, sample gates 20/50/10; replay_core Wilson, median CI, Bonferroni | EXISTS_TESTED | m28 reads paper positions that nothing writes |
| Train/validation/test with embargo | replay_core split_bounds :700, LabelGate :719, PURGED_EMBARGO :755 | EXISTS_TESTED (social replay) | reusable |
| Outcome tracking after discovery | catalyst monitor.record_outcomes :64; social outcomes_core/ledger; launch cohort | PARTIAL | catalyst outcomes untested; no outcome tracker for scout theses |
| Survivorship-safe universe | launch cohort `sample_basis='newest'`; state/latest.json theses+rejections over time | PARTIAL | replay_sources says includes_delisted False :233 |
| Catalyst provenance | catalyst_items published_at / retrieved_at / first_seen_at; page fetches with page_published_at/modified_at/fetched_at | EXISTS_TESTED | retrieved_at overwritten on re-read (ingest.py:243); first_seen_at immutable |
| Cross-source dedup | catalyst ingest Jaccard + domain corroboration :265-305 | EXISTS_TESTED (one clock-dependent test fails, C-1) | |
| Fatal-flag override | m24.fatal_flags :494-578; pipeline IDENTITY_NOT_VERIFIED :164 | EXISTS_TESTED | |
| Research-only guard | release_audit trade-code scan; FORBIDDEN_POLICY_KEYS (outcomes_core :62); replay trade_execution_impact must be "none" | EXISTS_TESTED | |
| Report / CLI / alerts | report.py token and scout reports; social alerts dry-run; catalyst monitor alerts | EXISTS_TESTED | no backtest or stress section |

## B. Core tables (db.py)

| table | time columns | append-only | writer |
|---|---|---|---|
| tokens | first_seen_at, last_seen_at, graduated_at, first_pool_at | no (UPDATE) | pipeline :197 |
| pools | pool_created_at, first_seen_at | insert once | pipeline :214 |
| market_snapshots | observed_at | yes (convention) | pipeline :203 |
| pool_snapshots | observed_at | yes | pipeline :216 |
| liquidity_quotes | observed_at | yes | pipeline :218 (effective_price_usd, in/out_mint, n_hops never written) |
| token_authorities | observed_at | yes | pipeline :225 |
| holders | observed_at | yes | pipeline :229 |
| wallet_clusters | observed_at | yes | pipeline :232 |
| wallet_transactions | block_time (ISO) | UNIQUE dedup | pipeline :235 |
| social_snapshots, price_levels | observed_at | yes | pipeline |
| theses | created_at | yes | pipeline :243 |
| entries | via thesis_id | yes | pipeline :247 |
| positions, exits, trade_reviews | opened/closed/exited/reviewed_at | n/a | no writer in memelab/ (tests only) |
| rejections | rejected_at | yes | pipeline :253, cli :181 |
| watchlist | added_at, last_status_change | no (upsert + delete) | pipeline :256 |
| fetch_log | fetched_at (= plan _at) | yes | bridge/ingest :44 |

`db.insert` is INSERT OR IGNORE for every table (:302-309). Catalyst, chains, launch and social schemas are applied by `init_db` (:271-285).

Local `data/memelab.sqlite` (tracked in the repo despite the `*.sqlite*` ignore rule): 13 tokens, 33 market snapshots over 28 minutes (2026-10-06T23:48Z to 2026-10-07T00:16Z), 498 quotes, 3,774 wallet transactions; positions/exits/trade_reviews/fetch_log empty; catalyst/social/launch tables absent (never migrated).

## C. Modules m01 to m28 (one line each)

| Module | Role | Time handling | Tests |
|---|---|---|---|
| m01 discovery | universe, stage-1 survivors, pre-score | carries pool created as a signal | none direct |
| m02 identity | confidence, status | observed_at only | live fixture |
| m03 market | pace, liq/mcap | provider rolling windows | indirect |
| m04 supply | FDV recompute, overhang | none | indirect |
| m05 pools | pool ages, top-pool share, concentrated flag | age vs observed_at | indirect |
| m06 depth | quote table, capacity at impact, friction | quote slot unread | live fixture, EVM |
| m07 LP | control, removable USD | none | indirect |
| m08 mechanics | Token-2022 extensions, transfer fee, flags | none | indirect |
| m09 holders | classification, adjusted top-10 | distribution_updated unread | indirect |
| m10 clusters | funding/timing clusters | trade minute buckets | indirect |
| m11 early wallets | large-holder direction, absorption | trade event window | indirect |
| m12 order flow | ratios, sizes, drift | 6h cutoff mixes observed_at and event time | indirect |
| m13 structure | swings, zones, ATH/ATL, vol | uses unfinished bars [checked C2] | test_m13_18 |
| m14 breakout | state machine on closes | candle ts only; h1/h24 key mismatch | test_m13_18 |
| m15 entries | styles, zones, invalidation | none | test_m13_18 |
| m16 R/R | scenario bands (fixed priors) | none | test_m13_18 |
| m17 sizing | risk and liquidity constraints | none | test_m13_18 |
| m18 exits | ladder, realizable | none | test_m13_18 |
| m19 attention | trend, organic, paid boost | rolling windows | indirect |
| m20 manipulation | wash trading label | none | indirect |
| m21 lifecycle | stage | age vs observed_at | test_m21_28 |
| m22 relative strength | RS vs SOL/BTC/peers | key mismatch h6/h24 | test_m21_28 |
| m23 thesis | thesis questions, unacceptable conditions | age < 24h rule | indirect |
| m24 ranker | 100-point score, fatal flags, status | previous status | test_m21_28, test_evm |
| m25 monitor | compact snapshot, diff | snapshot t = observed_at | indirect |
| m26 portfolio risk | exposure, HHI, stress scenario | none | test_m21_28 |
| m27 post-trade review | MAE/MFE, grades using info available at each decision | info_available per log ts | test_m21_28 |
| m28 statistics | group stats, bootstrap CI, signal compare | opened/closed times | test_m21_28 |

## D. Provider hosts called by plans

GeckoTerminal (pools, OHLCV day1/hour1/minute15, trades), Jupiter lite-api (tokens v2, swap/v1/quote, slippageBps 300), DexScreener (profiles, boosts, tokens), RugCheck (reports, trending), CoinGecko (simple price), public Solana RPC and Helius (getAccountInfo, signatures, DAS token accounts, enhanced transactions), GoPlus, honeypot.is, KyberSwap (EVM), GitHub raw. Quote size grid $500 to $100k, capped at $25k under $100k liquidity and $50k under $400k.

## E. Orders, keys, signing

None. Verify-only signature code in `social/sigverify.py`. `positions.paper` defaults to 1 and nothing writes positions.
