# Catalyst and social model card (Phase 10)

Status: PROVISIONAL_PENDING_REVISION_REREAD (PI-D-046), `revision_check_claimed: false`. Every model MODEL_NOT_PROMOTED; no number here is a published probability. Research only: nothing here is an order, a size or a trade signal.

Code `memelab/predictive/socialcat.py` (socialcat-1, feature-set sha in `evidence/run_log.json`), frozen at `0784a9a` before the recorded run (`evidence/run_log.json`: start 2026-10-26T00:20:50Z, head `0784a9a`, 61 s, 0 socket events, 0 vendor calls, 0 Firecrawl credits, 0 language-model calls, stores unchanged). Pre-registration `c3f04c8` (checklist, `experiments/EXPERIMENT_REGISTRY.csv`, PI-D-057). Provenance and rights: `data/CATALYST_PROVENANCE.md`. Proposed catalyst targets: `CATALYST_TARGET_PROPOSALS.md`.

## The answer first

- No catalyst event, item, link or assessment and no social item exists for any of the lab's decisions in anything this engine can read. Every one of the 925 Solana decisions carries `catalyst_state` CATALYST_TABLES_NOT_EXPORTED and `social_state` SOCIAL_TABLES_NOT_EXPORTED. No catalyst is VERIFIED, so no catalyst probability exists, and the catalyst-follow-through target stays BLOCKED_NO_DATA (a proposal, not frozen).
- What the lab recorded at each decision (the m19 attention proxy, the m20 manipulation screen, the m21 lifecycle stage, the token's channels and narrative tag, and the narrative tables of the same export) is the feature set socialcat-1, available at the export commit. On the frozen targets every social model and every comparison is INSUFFICIENT_HISTORY, INSUFFICIENT_DAYS or INSUFFICIENT_EVENTS, as stated in advance. No incremental value of social features beyond price and liquidity is claimed or claimable on this data.
- The leakage controls hold on the real history: the token row and narrative tables of every decision equal those of its own export (925 of 925, CX-10), a later export's tables are refused for all 240 labelled decisions (P04-SC), the next decision's values are refused on all 156 decisions that have one (NC2-SC), a snapshot time after the decision refuses all 19 values (P36-SC), and holdout-start cards cannot score development decisions (P13-SC).

## Targets

The three frozen primary targets only (TARGET_REGISTRY, fingerprint `4b4aabce...`): T1 +25% before -15% within 24 h (reported first: the follow-through-like target), T2 half the reference price or a halt within 24 h, T1b the T1 race within 6 h. Price-path labels, PRICE_PATH_NOT_PROCEEDS, NO_HISTORICAL_EXECUTABLE_DEPTH. Labels only through `labels.training_labels`; the sealed holdout was not opened.

## Inputs (socialcat-1, model inputs)

`sc_attention_trend_ord` (EXHAUSTION 0, STABILITY 1, ACCELERATION 2), `sc_attention_suspect` (paid boost or manufactured flow: the P16 downgrade flag), `sc_narrative_strength`, `sc_manipulation_ord`, `sc_lifecycle_late`, `sc_channels_n`, and for S3 `sc_d_attention_trend` and `sc_attention_reversal`. These are on-chain and market proxies of attention computed by the lab (holder growth, traders, Jupiter organic score, a paid DEX Screener boost), not social text (HEURISTIC). Coverage of the rows the attention models need: T1 129 of 136 development decisions, T2 124 of 131, T1b 210 of 224 (the rest `UNKNOWN: attention trend missing` in the lab's own row, NOT_OBSERVED_BY_LAB, OOD). Narrative context is described but not a model input: 39 of 925 decisions carry a narrative tag at the decision, all keyword clusters with lifecycle UNKNOWN.

## Models (one configuration each, no tuning)

| Id | Model | Rows |
|---|---|---|
| R2 `SC_RULE` | prevalence per (trend, suspect) cell, shrunk to B0 with m = 20 | all |
| R3 `SC_AMPLIFICATION_ALARM` | alarm when attention is suspect (counts only) | suspect known |
| S1 `SC_LOGIT` | L2 logistic (C = 1) on the attention columns | trend and suspect known |
| S2 `SC_LOGIT_B2` (primary) | L2 logistic on B2's columns plus S1's | B2 required plus trend and suspect |
| S3 `SC_LOGIT_TREND` | S2 plus the change features | as S2 |
| G1 `SC_STUMPS_B2` | boosted stumps (technical.Stumps, 100 rounds, rate 0.1, leaf 10) on S2's columns after `stats.Prep` | as S2 |
| A2 `SC_B2_TC` | B2's columns on S2's rows (the ablation) | as S2 |
| NC1-SC | S2 on labels permuted inside each training fold, seeds 0 to 19 | as S2 |

Phase 07's day walk-forward, fold audit, minimums (100 training events, 20 per class; 50 out-of-sample events, 10 per class; 5 days), verdict code and Holm across the three targets, unchanged. Split fingerprints equal Phase 07's on all three targets and the B0 and B2 out-of-sample numbers equal Phase 07's at 6 decimals (`evidence/phase07_equality.json`).

## Results on development data (retrospective, provider mode)

Folds: T1 3 folds (training 104 to 123 events), the attention models fit from fold 1 (fold 0 has 98 usable rows: INSUFFICIENT_HISTORY); T2 1 fold (104 events, 98 usable): every attention model INSUFFICIENT_HISTORY; T1b 5 folds (180 to 214 events), every model fits.

| Target | Model vs B0 | Rows with a number | Positives | Days | Brier skill | Mint interval | Verdict |
|---|---|---:|---:|---:|---:|---|---|
| T1 24 h | S2 | 13 | 4 | 2 | -0.274 | -0.543 to -0.087 | INSUFFICIENT_DAYS |
| T1 24 h | S1 | 13 | 4 | 2 | -0.136 | -0.308 to 0.161 | INSUFFICIENT_DAYS |
| T1 24 h | G1 | 13 | 4 | 2 | -0.155 | -0.650 to 0.177 | INSUFFICIENT_DAYS |
| T1 24 h | R2 | 24 | 8 | 3 | 0.037 | | INSUFFICIENT_DAYS |
| T2 24 h | S1, S2, S3, G1, A2 | 0 | | | | | INSUFFICIENT_HISTORY |
| T2 24 h | R2 | 8 | 1 | 1 | 0.032 | | INSUFFICIENT_DAYS |
| T1b 6 h | S2 | 37 | 3 | 5 | 0.131 | -0.658 to 0.344 (day -0.277 to 0.275) | INSUFFICIENT_EVENTS (Holm p 0.75) |
| T1b 6 h | S1 | 37 | 3 | 5 | 0.036 | -0.709 to 0.274 | INSUFFICIENT_EVENTS |
| T1b 6 h | G1 | 37 | 3 | 5 | -0.057 | -1.567 to 0.238 | INSUFFICIENT_EVENTS |
| T1b 6 h | R2 | 44 | 3 | 5 | -0.059 | | INSUFFICIENT_EVENTS |

Every view (ALL, NEW_MINTS, NEW_CREATORS, NEW_NARRATIVES, PIT_ONLY, NO_KEY_CONFLICT) gives INSUFFICIENT_HISTORY, INSUFFICIENT_DAYS or INSUFFICIENT_EVENTS: 306 metric rows, 0 directional verdicts (`experiments/SOCIAL_METRICS.csv`). The point estimates above are descriptions of 13 to 44 rows over 1 to 5 days and support no claim in either direction; the T1 S2 mint interval below zero rests on 2 days and 4 positives and is not a WORSE_THAN_BASE_RATE verdict (the frozen gate stops it).

## Ablation: social features beyond price and liquidity (step 5)

`experiments/ABLATION.csv`, same rows: S2 against A2 (B2 refitted on S2's rows) gives T1 -0.041 (13 rows, 2 days, INSUFFICIENT_DAYS) and T1b +0.045 (37 rows, 3 positive, INSUFFICIENT_EVENTS); G1 against A2 gives T1 +0.056 and T1b -0.162 under the same verdicts; T2 has no number. The campaign bootstrap (group = narrative tag at the decision, else the mint; 13 to 34 groups) is reported beside the governing day and mint intervals and never governs; it is close to the mint interval (T1b S2 against A2: mint -0.489 to 0.249, campaign -0.422 to 0.240). No incremental value is claimed (`incremental_value_claimed: false` on every row). The phase gate's "independently attributable incremental performance if claimed" therefore has nothing to attribute.

## Network-amplification alarm (R3, counts only)

`experiments/AMPLIFICATION_ALARM.csv` (ALL view, out of sample): T2 8 scored, 0 hits, 1 miss, 1 false alarm, 6 correct rejections; T1 24 scored, 2 hits, 6 misses, 2 false alarms, 14 correct rejections (lead time median 16.3 h); T1b 39 scored, 0 hits, 3 misses, 6 false alarms, 30 correct rejections. Below 20 events per cell no rate is claimed; these are counts. Cohorts by attention trend, suspect flag, lifecycle stage, narrative tag, route, week and day: `experiments/ALARM_COHORTS.csv`.

## Negative control and traps

- NC1-SC: T1 mean skill -0.102 over 13 rows (INSUFFICIENT_DAYS), T1b -0.079 over 37 (INSUFFICIENT_EVENTS), T2 none: uninformative at this size, as in Phases 07 to 09.
- NC2-SC 156 of 156 refused by the allowlist and by `validate_rows`, 0 accepted (minimum trap delay 72 s); P13-SC every holdout-start card refused on the earliest development decision; P36-SC 19 of 19 values INCONSISTENT_TIME; P04-SC 240 of 240 refused; CX-10: 925 of 925 stored token rows equal their own export's, and reading the newest export instead would tag 20 more decisions with a narrative and add a website to 74 and a twitter link to 4 (`evidence/traps.json`).

## Catalyst classification and social evidence (TEST_ONLY)

`classify_catalyst` (exact-mint identity in a visible original source, evidence as of T from the revision log, independence after deduplication, VERIFIED only with confirmed evidence and an official or two independent sources, type from structured fields only) and `social_as_of` (first-known originals, deletions, duplicates, bots, ticker-only mentions, model-extracted claims, track records matured by T) are proved on fixtures only (`tests/test_predictive_social.py`, 51 tests). Real use: none possible (no rows). On the real record the lab's own readings give two derived classes, never a verified catalyst: HIGH_ATTENTION_PROXY on 74 decisions and NARRATIVE_REVERSAL on 56 (`evidence/crosschecks.json`).

## The two named validations

- One event without post-event text (real): the trace decision (T1, `5Upkgkqx...`, 2026-10-13T10:20:23Z, export `698f73b8`) gives the same socialcat-1 snapshot from a store truncated at T as from the full store, and the next export's tables (`45a28eed`) are refused; the fixture twin (an article edited and the event denied after T) classifies at T exactly as on inputs truncated at T.
- One duplicated influencer article (fixture): one trader's article on X and Telegram plus a syndicated copy counts as one independent source (catalyst) and one original (social).

## Checks of the numbers

- Trace: `probes/verify_trace_social.py` (no socialcat.py) recomputes 8 values, 11 inputs and 8 model results; the stored token row equals the decision's own export; 0 differences (`evidence/trace/verify_trace.json`). The trace row falls in T1 fold 0, where the attention models abstain, so its numbers are B0, B2 and R2.
- Every out-of-sample number: `probes/recompute_oos_social.py` (no socialcat.py, features.py or stats.py) recomputes 456 model values (326 numbers, logistic and stumps included) from the committed features and fold cards: 0 differences (`evidence/recompute_oos.json`).
- Oracle (PI-D-053): newton-cholesky within 1.9e-11 on 40 real logistic designs and the synthetic ones; `stats.Prep` against SimpleImputer plus StandardScaler within 4.9e-15 (`evidence/sklearn_crosscheck.json`).
- Determinism: a second run into another folder wrote identical files except the trace's latency (`evidence/determinism.json`).
- Frozen cards for Phase 12: R2, S1, S2, S3, G1 and A2 per target at 2026-10-17T00:00Z (`artifacts/<target>/`; T1 129 rows and 33 positive, T1b 210 and 25, T2 124 and 26), read back identical, tamper refused, no pickle (`evidence/serialization_smoke.json`); MODEL_STALE after 2026-10-31. An ABSTAIN document from each S2 card validates; a FORECAST with a probability is refused.

## Limits

- The attention inputs are the lab's proxies, with the lab's code version behind each row (PI-D-008); a version change in m19, m20 or m21 changes the meaning without a flag (an unknown line is UNPARSEABLE, a changed meaning is not detectable here).
- The decision time is the export commit; the lab's inputs behind a row are up to about 50 minutes older (PI-D-011), so these features are conservative in time, not fresh.
- Development only, retrospective, provider mode; 1 to 5 out-of-sample days. Any comparison must come from the sealed holdout (Phase 12) or the prospective data (Phase 19). Real catalyst and social evaluation needs forward data and approvals that do not exist.
