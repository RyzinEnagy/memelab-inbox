# Phase 10 acceptance checklist and pre-registration (written before any social or catalyst feature is computed on a labelled row and before any fit)

Written 2026-10-25 from 23:56Z by the Phase 10 agent, after the entry gate at `1a52308` (suite `1 failed, 1279 passed in 179.56s`, exit 1, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; the stray `data/reports/20261025_2349_BRETT_0x532f.md` and `data/memelab.sqlite-shm`, `-wal` removed by hand; `check_seal.py` exit 0 with `"problems": []`; tracked `data/memelab.sqlite` sha256 `068287c0...` unchanged; both private stores equal to the sha256 in Phase 09's run log), after reading the package (checksums OK), the phase prompt, ADVERSARIAL_SCENARIOS, DATA_TIME_CONTRACT, RESEARCH_TOOLING, SCIENTIFIC_VALIDATION, every PI-D entry (PI-D-001 to PI-D-056), Phase 00's EXISTING_PREDICTION_INVENTORY and DATA_COVERAGE, the Phase 05 to 09 deliverables, `memelab/predictive/*.py`, and (read only) `docs/social-intelligence/SOURCE_COVERAGE.md`, `memelab/social/schema.py`, `identity.py`, `alpha_core.py`, `replay_core.py`, `outcomes_core.py`, `memelab/catalyst/schema.py`, `match.py`, `memelab/chains/narrative.py`, `memelab/modules/m19_attention_analysis.py` and `m24_opportunity_ranker.py`. This file, `experiments/EXPERIMENT_REGISTRY.csv` and PI-D-057 are committed before any social or catalyst feature is computed on a labelled decision and before any model is fitted (PI-D-045 item 5).

What was looked at before writing it, with no label read: over the 925 Solana decision rows of the Phase 05 store, the counts of the attention and lifecycle rationale lines (`attention trend EXHAUSTION` 354, `STABILITY` 314, `ACCELERATION` 101, `UNKNOWN: attention trend missing` 153; `narrative strength N` 870; `attention organic` 720, `attention paid/boosted` 150; manipulation screen MOSTLY ORGANIC 205, MIXED / UNCERTAIN 466, LIKELY MANUFACTURED 245, SEVERELY MANIPULATED 6), the snapshot `lifecycle` stages, the token rows' channel fields (website set 656, twitter set 616, telegram never set) and narrative tags (39 of 925 tagged at the decision; 20 more mints carry a tag only in the newest export, 74 a website and 4 a twitter link only there), the exact decision mints named in the inbox catalyst reads of 2026-10-07 (14 in the Coinbase asset list, 1 in the DEX Screener boosts list) and the 86 export commits that hold the decisions. No label value, class split or model number was computed.

## Status rules carried in

- PROVISIONAL (PI-D-046): Phase 06's 48 h revision re-read is still owed (not before 2026-10-26T13:49Z). Every Phase 10 number, card and verdict carries `PROVISIONAL_PENDING_REVISION_REREAD` and `revision_check_claimed: false`; if the re-read changes any development label, `probes/run_social.py` is rerun at the Phase 10 code commit and the outputs are superseded, never edited.
- Phase 10 never opens `phase_06/sealed/`; labels only through `labels.training_labels`.
- Verdicts use Phase 07's frozen functions unchanged (`baselines.evaluate`, `verdict`, `evaluation_gate`, `nc1_verdict`), Holm across the three primary targets per (model, reference). No new verdict code.
- Logistic oracle: scikit-learn `LogisticRegression(solver="newton-cholesky")` in the research venv, coefficients within 1e-9 (PI-D-053), on every fitted logistic design (folds and holdout start). The stump booster is technical.Stumps (Phase 08), unchanged; its oracle is Phase 08's.
- The catalyst-follow-through target was not frozen in Phase 01 (TARGET_REGISTRY: BLOCKED_NO_DATA). Phase 10 forecasts only the frozen targets T1, T1b, T2; catalyst follow-through, withdrawal and network amplification are written as proposals for a later change control on forward data, never frozen here.
- Anything resting only on fixtures (the catalyst classifier on catalyst tables, the social evidence adapter on social tables, the proposed catalyst labels) is TEST_ONLY for that part and says so.
- No Firecrawl, crawler, LLM or paid call. No language-model judgment is used anywhere (P26); a claim extracted by a model is excluded from every feature and flagged.

## What exists and what does not (the data sufficiency statement, fixed before building)

| Item the phase prompt names | State at the lab's decisions | Use here |
|---|---|---|
| Social items, observations, edits, deletions, token resolutions, claims, trader links, wallet attribution, trader scores (social schema) | no row anywhere this initiative can read: every social table is not exported (Phase 00 DATA_COVERAGE), `data/private/` does not exist in this checkout, every social route is BUILT fixtures only or BLOCKED (SOURCE_COVERAGE.md) | read-only adapter `social_as_of` tested on fixtures (TEST_ONLY); every real decision carries `social_state` SOCIAL_TABLES_NOT_EXPORTED |
| Catalyst items, events, revisions, token links, attention samples, assessments, outcomes | not exported; each scheduled catalyst pass starts empty (FIRECRAWL.md, Phase 00) | read-only classifier `classify_catalyst` tested on fixtures (TEST_ONLY); every real decision carries `catalyst_state` CATALYST_TABLES_NOT_EXPORTED |
| Catalyst reads committed to `inbox/` (cat01*.json, read 2026-10-07T14:06:04Z, first committed 14:07:14Z) | exchange asset lists, trending lists, DEX Screener profiles and boosts, news feeds, X profile reads of six traders; 14 decision mints named by exact address in the Coinbase asset list, 1 in the boosts list, 0 in the news feeds | real cross-check and catalyst-class counts only (one read, a listing state, not an event); not a model input |
| The lab's attention reading at the decision (m19 proxy: holder growth, traders, Jupiter organic score, paid DEX Screener boost) | inside each thesis row: rationale lines of `attention_narrative` and `demand_order_flow`, snapshot `attention` and `lifecycle` | as-of features, availability = the export commit of the row (decision time); evidence LAB_RECORDED; these are on-chain and market proxies of attention, not social text |
| Token channels and narrative tag | token row of the decision's own export (website, twitter, telegram, narrative_id) | as-of features; the newest export's token row is never used (CX-10) |
| Narrative context (narrative lifecycle, novelty, keyword catalyst counts) | `narratives` and `narrative_snapshots` tables of the decision's own export commit | as-of context; keyword catalyst counts are name matches of headline words, never identity and never a model input |
| Price and liquidity baseline | Phase 07 B2 (version 2 snapshot columns) | unchanged reference |

## Social and catalyst feature set socialcat-1 (fixed)

Source: the decision row of the export (the thesis row and its token row, read through `features.AsOfView.decisions_of` at T, audited by `replay_core.Audit`), the previous decision of the same chain and mint (decision time strictly before T), and the `narratives` and `narrative_snapshots` tables of the export commit that is the decision (its commit time must equal T and its blob the stored `export_blob`, else the context is refused). Availability of every value: T (the export commit), evidence LAB_RECORDED. Missing reasons, all with the AS_OF basis: NOT_IN_UNIVERSE, OUT_OF_SCOPE_CHAIN, UNPARSEABLE, NOT_OBSERVED_BY_LAB, ABSENT_IN_SNAPSHOT, NO_PRIOR_DECISION, NO_TOKEN_ROW, NO_NARRATIVE_TAG, NO_NARRATIVE_SNAPSHOT, INCONSISTENT_TIME, INCONSISTENT_RECORD, CONTEXT_NOT_SUPPLIED. No value is imputed in the feature layer. Solana only (EVM decisions OUT_OF_SCOPE_CHAIN, as onchain-1).

| Feature | Definition | Model input |
|---|---|---|
| `sc_attention_trend_ord` | rationale "attention trend X": EXHAUSTION 0, STABILITY 1, ACCELERATION 2; "UNKNOWN: attention trend missing" NOT_OBSERVED_BY_LAB; the snapshot `attention` must name the same word when set, else INCONSISTENT_RECORD | yes |
| `sc_narrative_strength` | rationale "narrative strength N" (the lab's 0 to 1 proxy) | yes |
| `sc_attention_paid` | "attention paid/boosted" 1, "attention organic" 0 | no (inside `sc_attention_suspect`) |
| `sc_manipulation_ord` | "manipulation screen X / wash Y": MOSTLY ORGANIC 0, MIXED / UNCERTAIN 1, LIKELY MANUFACTURED 2, SEVERELY MANIPULATED 3 | yes |
| `sc_attention_suspect` | P16 downgrade flag: 1 when paid or manipulation at least 2; 0 when both observed and neither; missing otherwise | yes |
| `sc_organic_acceleration` | 1 when trend ACCELERATION and suspect 0; 0 when trend observed and not ACCELERATION, or suspect 1 (suspect attention counts nothing) | no |
| `sc_lifecycle_late` | snapshot `lifecycle`: DISTRIBUTION, BREAKDOWN, POST_BREAKDOWN 1; DISCOVERY, LAUNCH, EARLY_EXPANSION, BROAD_ATTENTION, MANIA 0; UNKNOWN NOT_OBSERVED_BY_LAB | yes |
| `sc_lifecycle_conf_ord` | rationale "lifecycle X (confidence Y)": LOW 0, MODERATE 1, HIGH 2 | no |
| `sc_channels_n` | website, twitter and telegram links of the token row that are http links and not search pages (`/search`, `search?`, `?q=`) | yes |
| `sc_channel_search_url` | 1 when a channel field is a search page (a fake channel), else 0 | no |
| `sc_narrative_tagged` | 1 when the token row carries a narrative id, else 0 (a name-keyword classification, not identity) | no |
| `sc_narrative_lifecycle_ord` | newest snapshot of the tagged narrative with `observed_at` at or before T in the decision's export: DEAD 0, EXHAUSTING 1, MATURE 2, EMERGING 3, ACCELERATING 4, MANIA 5; UNKNOWN NOT_OBSERVED_BY_LAB | no |
| `sc_narrative_age_h` | T minus the narrative's `first_seen_at` (novelty) | no |
| `sc_narrative_catalyst_kw_7d` | the snapshot's `catalyst_events_7d` (headline keyword matches; context only, never identity) | no |
| `sc_narrative_mcap_chg_24h_pct` | the snapshot's 24 h market cap change | no |
| `sc_narrative_snapshot_age_h` | T minus the snapshot's `observed_at` | no |
| `sc_d_attention_trend` | trend now minus trend at the previous decision of the mint | yes (S3 only) |
| `sc_attention_reversal` | 1 when the previous trend was ACCELERATION or STABILITY and now EXHAUSTION; 0 when both observed otherwise | yes (S3 only) |
| `sc_d_narrative_strength` | narrative strength now minus at the previous decision | no |

Every snapshot also carries the states `catalyst_state` (CATALYST_TABLES_NOT_EXPORTED for every real decision) and `social_state` (SOCIAL_TABLES_NOT_EXPORTED), and `lab_event_classes`: HIGH_ATTENTION_PROXY when `sc_organic_acceleration` is 1, NARRATIVE_REVERSAL when `sc_attention_reversal` is 1 (both LAB_RECORDED readings, never a verified catalyst).

## Catalyst classifier (`classify_catalyst`, TEST_ONLY)

Input: one catalyst event with its items, event-source roles, revisions, token links and any crawled page facts, plus the exact (chain, mint) and T. Rules:

1. Availability. An item counts only when its `first_seen_at` (first lab sighting) is at or before T; `published_at` is a source claim and never availability (P04); a crawled page counts only when its `fetched_at` is at or before T; a revision counts only when `revised_at` is at or before T. The event's conservative `first_seen_at` is the earliest visible item's `first_seen_at`; its `available_at` is the later of that and the token link's `linked_at`. No visible item: NOT_AVAILABLE_AT_DECISION (P45: an event without source evidence is refused).
2. Identity (PI-D-007, PI-D-012). Only a link of the exact chain and mint with type NAMED_IN_SOURCE, strength STRONG and `linked_at` at or before T, whose mint appears in a visible ORIGINAL or INDEPENDENT item's own url or body, is identity. A mint named only on a crawled page is PAGE_NAMED_ONLY (the Phase 00 P41 finding: a hostile page that names a contract becomes STRONG); TICKER_MATCH, NAME_MATCH, THEMATIC or a weaker strength is TICKER_OR_NAME_ONLY. Either gives IDENTITY_UNVERIFIED.
3. Evidence as of T. The event's evidence status is the newest `evidence_status` revision at or before T, else the row's value only when the row's `updated_at` is at or before T, else UNKNOWN_AS_OF. A DENIED, CANCELLED or DELETED_SOURCE revision at or before T, a RUMOR status or a deleted source item gives UNVERIFIED_EVENT (P17).
4. Independence (P15). Only visible items with role ORIGINAL or INDEPENDENT count, deduplicated by url and by body hash; SYNDICATED, CIRCULAR and COMMENTARY add nothing.
5. VERIFIED needs identity, evidence CONFIRMED as of T, no denial or deletion at or before T, and either an official-tier source or at least two independent sources. Anything else is UNVERIFIED_EVENT (or the states above) with `probability_allowed: false`: an unverified catalyst returns an explicit state, never a positive probability.
6. Type from structured fields only (no headline taxonomy chosen after outcomes): RUMOR whenever the evidence as of T is RUMOR; else social claim type LISTING or catalyst category ACCESS gives LISTING, PARTNERSHIP gives PARTNERSHIP, LAUNCH gives CODE_RELEASE, CALL or WALLET_CLAIM from a trader source gives BIG_TRADER_CLAIM, an attention-sample-only event gives HIGH_SOCIAL_ATTENTION, category ROTATION gives NARRATIVE_REVERSAL, a token-mechanics source gives TOKEN_MECHANIC_CHANGE, anything else OTHER.

## Social evidence adapter (`social_as_of`, TEST_ONLY)

Read-only (`mode=ro`) over a social store; refuses the tracked lab database and the predictive stores. Every row passes `replay_core.Audit` at T. Rules: an item is visible when an OK or PARTIAL observation was ingested at or before T; its content is the ORIGINAL version recorded at or before T (an item whose only visible version is an EDIT is excluded, P03); an item with a DELETED or NOT_FOUND observation at or before T is excluded and counted (P17); identity only from a `resolved` CONTRACT or LINK resolution of the exact chain and mint resolved at or before T (TICKER mentions are counted apart and never used, PI-D-007); originals deduplicated by content hash, and accounts linked to one trader at or before T count as one source (P15); BOT accounts and SUSPENDED identities are excluded from counts and reported as a share (P16); claims extracted by a model are excluded and flagged (P26). Features: `sx_mentions_exact`, `sx_ticker_only_mentions` (never a model input), `sx_distinct_sources`, `sx_verified_traders`, `sx_track_record_wilson_lo` (mean Wilson lower bound, `alpha_core.wilson`, over each mentioning trader's calls called before T whose outcome matured at or before T), `sx_disagreement`, `sx_volume_accel` (ln((originals in the last hour + 1) / (originals in the 6 h before that / 6 + 1))), `sx_concentration`, `sx_novelty_h`, `sx_official_link`, `sx_bot_share`, `sx_corroboration_platforms`, `sx_deleted_before_t`, `sx_llm_claims_excluded`.

## Candidate models (one configuration each, no tuning)

Fitted on each fold's training rows only, a fit only when the rows a model uses reach 100 events and 20 per class, else INSUFFICIENT_HISTORY. Cards are JSON read by numpy code (no pickle), with model sha, socialcat-1 and version 2 feature-set sha, cutoff, label-set and data-snapshot sha.

| Id | Model | Inputs | Fixed settings |
|---|---|---|---|
| R2 `SC_RULE` | the simple attention rule as a forecaster: training prevalence per cell of (`sc_attention_trend_ord`, `sc_attention_suspect`), shrunk to B0 with m = 20; a missing cell value gives B0 | 2 columns | m = 20 |
| R3 `SC_AMPLIFICATION_ALARM` | network-amplification alarm, not a probability: alarm when `sc_attention_suspect` = 1 | 1 flag | counts only (hits, misses, false alarms, correct rejections, lead time) |
| S1 `SC_LOGIT` | L2 logistic regression | required `sc_attention_trend_ord`, `sc_attention_suspect`; optional (median fill and missing indicator) `sc_narrative_strength`, `sc_manipulation_ord`, `sc_lifecycle_late`, `sc_channels_n` | C = 1.0, `stats.Prep` |
| S2 `SC_LOGIT_B2` (primary) | L2 logistic regression | B2's columns (liquidity, market cap, 24 h volume, fatal flag required; token age optional) plus S1's columns (same split) | C = 1.0, `stats.Prep` |
| S3 `SC_LOGIT_TREND` | L2 logistic regression | S2's columns plus optional `sc_d_attention_trend`, `sc_attention_reversal` | C = 1.0, `stats.Prep` |
| G1 `SC_STUMPS_B2` | gradient boosting of stumps (technical.Stumps, 100 rounds, rate 0.1, leaf at least 10) on `stats.Prep`-transformed S2 columns | S2's columns and rows | Phase 08 constants |
| A2 `SC_B2_TC` | B2's columns only, fitted on S2's training rows | B2's columns | as B2 |
| NC1-SC | S2 refitted on training labels permuted inside each fold's training rows | as S2 | seeds 0 to 19 |
| B0, B2 | Phase 07's, refitted by `baselines.fit_b0` and `fit_b2` in the same folds | as Phase 07 | out-of-sample numbers must equal Phase 07's `OOS_PREDICTIONS.csv` at 6 decimals |

The other socialcat-1 features are computed, covered and described, but enter no model. No other model, feature, threshold or calibration variant is run.

## Comparisons, metrics and verdicts (fixed)

| Item | Rule |
|---|---|
| Primary | S2 against B0 (Brier skill), all three primary targets, Holm across the three; T1 (the follow-through-like target, +25% before -15% in 24 h) reported first |
| Contribution beyond price and liquidity (step 5) | S2 against A2 (B2 refitted on S2's rows) and G1 against A2, same rows; S2, S3, G1 and R2 against B2 |
| Secondary | S1, S3, G1, R2 and A2 against B0; S1, S2, S3 against R2 |
| Views | ALL, NEW_MINTS, NEW_CREATORS, NEW_NARRATIVES, PIT_ONLY, NO_KEY_CONFLICT |
| Event-level grouping by campaign | the day and mint bootstraps of Phase 07 govern; a campaign bootstrap (group = the token's narrative tag at the decision, else the mint) is reported beside them as a description, never governing |
| Scores and intervals | Phase 07's: Brier, skill, log loss (clip 1e-6), AUC and AP only with 10 per class, day and mint bootstrap 2,000, seed 20261025, wider governs, day interval undefined below 5 days, out-of-sample gate 50 events and 10 per class |
| Network-amplification risk (step 4) | R3 alarm counts on T2 and T1 out of sample; lead time from the decision to the label's first touch; no rate below 20 events |
| Cohorts | route, attention trend, suspect flag, lifecycle stage, narrative tagged, week, day; no rate below 20 events |
| Degeneracy (P11, P38) | zero variance flagged DEGENERATE; non-finite raises |
| Coverage | per target: rows with every required input, OOD counts with reasons, per feature missing reasons; narrative context coverage by export day |
| Cost | wall and CPU time, 0 network calls (audit hook), 0 vendor calls, 0 Firecrawl credits |
| Promotion | none: every model MODEL_NOT_PROMOTED |

## Proposed catalyst targets (not frozen)

`models/CATALYST_TARGET_PROPOSALS.md` and proposal functions without default parameters, fixtures only, PROPOSED_NOT_FROZEN and TEST_ONLY: catalyst follow-through (a VERIFIED catalyst's price path from the first price available after its `available_at`), catalyst failure or withdrawal (a denial, cancellation or deleted source after `available_at` within a horizon, or a drawdown), and network-amplification reversal (suspect attention acceleration followed by the T2 event). Freezing any of them is a later change control on forward data, registered before any of its outcomes is read. The registry fingerprint `4b4aabce...` and ACCEPTANCE stay unchanged.

## Forecast trace and the two named validations

- Trace: the earliest out-of-sample T1 row (then T2, T1b) by decision time then mint with every S2 input present; the decision row's sha256, the parsed rationale lines, the token row of the decision's export, the narrative context, the fold card (sha, cutoff) and the number or abstention. `probes/verify_trace_social.py` recomputes the features from the row JSON with its own parser (no `socialcat.py`) and the number from the card's JSON.
- One event without post-event text (real): for the trace decision, the socialcat-1 snapshot computed from a store truncated at T (`features.truncated_copy`) and from the decision's own export equals the full computation, and handing the next export commit's tables (post-decision text) is refused. The fixture twin: a catalyst event whose article is edited and denied after T classifies at T exactly as on inputs truncated at T.
- One duplicated influencer article (fixture): the same article posted by one trader on X and Telegram under two accounts and syndicated by a news site counts once (one original, one source, one independent source).

## New counterexample CX-10 (named before building)

The token row is updated in place by later sessions: the narrative tagger and the providers' channel fields fill it later. A plausible wrong design reads the token row (narrative tag, website, twitter) from the newest export or from the lab's `tokens` table instead of the export that holds the decision. Measured before building, without labels: 20 Solana decisions untagged at the decision carry a narrative tag in the newest export, 74 gain a website and 4 a twitter link. Caught by `socialcat_as_of` reading only the token row stored with the decision (the export where the decision row first appears) and by `narrative_context` refusing tables whose commit time is not T or whose blob is not the decision's stored `export_blob`; a test fails when either refusal is removed, and the runner counts the 20, 74 and 4 on the real history.

## Checklist

| Id | Check | How it is verified | Fails if |
|---|---|---|---|
| G1 | Package unchanged | `sha256sum -c SHA256SUMS.txt` | a line not OK |
| G2 | Entry gate | suite at `1a52308`, `check_seal.py` | anything but `1 failed, 1279 passed` with the known failure, or seal problems |
| G3 | Pre-registration before any fit | this file, the registry and PI-D-057 committed before `evidence/run_log.json` start | a run before the commit |
| G4 | Numpy core with tests | `socialcat.py` numpy and standard library plus the reused `memelab.social.replay_core` and `alpha_core` (no social or catalyst module changed); `tests/test_predictive_social.py` | a third-party import, a changed social or catalyst file, or an untested rule |
| G5 | As-of features | every value from rows available at T (audit); token row and narrative tables of the decision's own export only (CX-10); next decision never used; snapshot `t` after T refused | a later row read |
| G6 | Same frozen folds | split fingerprints equal Phase 07's; B0 and B2 out-of-sample numbers equal at 6 decimals | a difference |
| G7 | Gate use and identity | training rows only from `training_labels`; identity join with chain, mint, time and key; sealed and bake-off paths refused | a row from anywhere else |
| G8 | Count gates | no fit below 100 events or 20 per class on the rows used | a fit below the minimum |
| G9 | Metrics and verdicts | `experiments/SOCIAL_METRICS.csv` per target, model, reference and view with counts, intervals, verdict, PROVISIONAL | a missing count or verdict, or a claim under the minimums |
| G10 | Ablation | `experiments/ABLATION.csv`: S2 and G1 against A2 on the same rows, S2 against B2, with counts and verdicts; any claim of incremental value needs a directional verdict | a claim without one |
| G11 | Negative controls and traps | NC1-SC under `nc1_verdict`; NC2-SC (next decision's values) refused by allowlist and `validate_rows` on every row; P13-SC; P36-SC (snapshot time after T); P04-SC (a later export's context) refused | a trap accepted |
| G12 | Amplification alarm and cohorts | R3 counts, lead times; cohort tables; no rate below 20 | missing or a rate below 20 |
| G13 | Artifacts | holdout-start cards written, read back identical, model sha recomputed, tamper refused, `runtime.verify_artifact` | a mismatch or a pickle |
| G14 | Contract | an ABSTAIN document from each S2 card passes `contract.validate`; a FORECAST with a probability refused; an UNVERIFIED catalyst gives no probability | a probability accepted |
| G15 | Oracle | newton-cholesky within 1e-9 on every fitted logistic design (folds and holdout start) | a larger difference |
| G16 | Determinism and isolation | two runs, identical outputs (except run log times and trace latency); 0 network calls; stores unchanged; nothing written under tracked `data/`, `inbox/`, `state/` | any difference or write |
| G17 | Catalyst classifier | fixture tests for P04, P15, P17, P41, P45, identity rules, evidence as of T, type from fields, no probability when unverified | any failure |
| G18 | Social adapter | fixture tests for P03, P15, P16, P17, P26, P36, ticker-only, track record before T, read-only, refusal of lab and predictive stores | any failure |
| G19 | Two named validations | event without post-event text (real truncation and fixture); duplicated influencer article counted once | a difference or a double count |
| G20 | Proposals not frozen | registry fingerprint `4b4aabce...` and ACCEPTANCE unchanged; proposal functions have no default parameters; outputs carry PROPOSED_NOT_FROZEN and TEST_ONLY | a frozen or defaulted parameter |
| G21 | Provenance and rights | `data/CATALYST_PROVENANCE.md`: every source with its clock, availability rule, rights and permitted access, real row counts at the decisions | missing |
| G22 | Real cross-checks | inbox catalyst reads against decision mints (exact address only); CX-10 counts on the real history; narrative context coverage | missing |
| G23 | Forecast trace | written, recomputed independently equal, invalid inputs rejected | a difference or an acceptance |
| G24 | Search ledger | `experiments/SEARCH_LEDGER.csv` = Phase 09's ledger plus every Phase 10 configuration, view, NC1 seed and any debug run | an unlogged run |
| G25 | Adversarial scenarios and mutation probe | tests for P03, P04, P15, P16, P17, P26, P36, P41, P45, P13, P38 and CX-10; the mutation probe runs at HEAD and catches every listed mutation | a scenario without a test or a surviving mutation |
| G26 | Flag and imports | flag OFF; no existing module imports the new code; score and fatal flags unchanged | a change |
| G27 | Suite, guard and audits after the commit | full suite (no new failure), `python -m memelab social guard`, `python tools/release_audit.py --history` on a single-branch clone, `check_seal.py`; `git status` clean | any new failure |

## Expected result, stated in advance

The attention inputs exist on about 83% of decisions, so the social models meet the same walls as Phase 07's B2 and Phase 09: on T1 and T2 the out-of-sample days are 3 and 1 (INSUFFICIENT_DAYS); on T1b the out-of-sample set is 44 events with 3 positive (INSUFFICIENT_EVENTS). No incremental value of social features beyond price and liquidity can be claimed. No real decision has a verified catalyst or any social item, so every catalyst and social state is an explicit abstention; the classifier and the adapter are TEST_ONLY. The phase gate is met by honest data sufficiency, the as-of feature layer, the leakage tests and the adapters, or by an explicit stop.
