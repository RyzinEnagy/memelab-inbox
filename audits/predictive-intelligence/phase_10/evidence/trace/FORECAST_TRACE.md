# Phase 10 forecast trace

Decision `4b33b36c051d59016f7826b9d7fb62a92fdb179e79b4a5f97faf783de95f0917` of mint `5Upkgkqx9nZJGDCz4Kgo8tiT995Gu1PiF7AGMQbBxEg` at 2026-10-13T10:20:23Z (EXPORT_COMMIT `698f73b854`), target `price_path_target_before_invalidation_24h`, fold 0 (cutoff 2026-10-13T00:00:00Z), label 1.
Row sha256 `c914fcbd9f8567182f66046e94f5e1ffe8a3069501fb5c9a7fa34145fb0fd42c`; socialcat-1 snapshot sha `2955e33dc520026ff2a5038a3cd50f65ace6f8a9b3b26268da4dd45894cfc56f`. Status PROVISIONAL_PENDING_REVISION_REREAD.
Catalyst state CATALYST_TABLES_NOT_EXPORTED; social state SOCIAL_TABLES_NOT_EXPORTED; lab event classes: none.

## Lab readings behind the values

- Snapshot fields: {"attention": "STABILITY", "lifecycle": "BREAKDOWN", "t": 1791886774.0650861}
- Token row of the decision's export: {"narrative_id": null, "telegram": null, "twitter": "https://x.com/nearlytrade", "website": "https://nearly.trade"}
- attention_narrative: attention trend STABILITY; narrative strength 0.00; attention paid/boosted
- demand_order_flow: net buyers 24h +4; buy/sell volume ratio 0.07; UNKNOWN: organic volume share missing; manipulation screen MOSTLY ORGANIC / wash LOW
- lifecycle_relative_strength: lifecycle BREAKDOWN (confidence MODERATE); UNKNOWN: relative strength labels missing

## socialcat-1 values

| Feature | Value | Missing reason |
|---|---|---|
| `sc_attention_paid` | 1.0 |  |
| `sc_attention_reversal` |  | NO_PRIOR_DECISION |
| `sc_attention_suspect` | 1.0 |  |
| `sc_attention_trend_ord` | 1.0 |  |
| `sc_channel_search_url` | 0.0 |  |
| `sc_channels_n` | 2.0 |  |
| `sc_d_attention_trend` |  | NO_PRIOR_DECISION |
| `sc_d_narrative_strength` |  | NO_PRIOR_DECISION |
| `sc_lifecycle_conf_ord` | 1.0 |  |
| `sc_lifecycle_late` | 1.0 |  |
| `sc_manipulation_ord` | 0.0 |  |
| `sc_narrative_age_h` |  | NO_NARRATIVE_TAG |
| `sc_narrative_catalyst_kw_7d` |  | NO_NARRATIVE_TAG |
| `sc_narrative_lifecycle_ord` |  | NO_NARRATIVE_TAG |
| `sc_narrative_mcap_chg_24h_pct` |  | NO_NARRATIVE_TAG |
| `sc_narrative_snapshot_age_h` |  | NO_NARRATIVE_TAG |
| `sc_narrative_strength` | 0.0 |  |
| `sc_narrative_tagged` | 0.0 |  |
| `sc_organic_acceleration` | 0.0 |  |

## Models (fold cards)

| Model | Card sha | Cutoff | Number | Abstain |
|---|---|---|---|---|
| A2_SC_B2_TC | `1ac21646485c56e6` | 2026-10-13T00:00:00Z |  | INSUFFICIENT_HISTORY |
| B0 | `5f0659ee7ec23b12` | 2026-10-13T00:00:00Z | 0.240385 |  |
| B2 | `934181f497edcfc9` | 2026-10-13T00:00:00Z | 0.154677 |  |
| G1_SC_STUMPS_B2 | `a3671f4872fe9cab` | 2026-10-13T00:00:00Z |  | INSUFFICIENT_HISTORY |
| R2_SC_RULE | `cfbf72072fbfdc14` | 2026-10-13T00:00:00Z | 0.284413 |  |
| S1_SC_LOGIT | `6a884b5555dd4580` | 2026-10-13T00:00:00Z |  | INSUFFICIENT_HISTORY |
| S2_SC_LOGIT_B2 | `fecfb8670ed4316f` | 2026-10-13T00:00:00Z |  | INSUFFICIENT_HISTORY |
| S3_SC_LOGIT_TREND | `45ffd6a244a74b5b` | 2026-10-13T00:00:00Z |  | INSUFFICIENT_HISTORY |

## Event without post-event text

- {"later_decisions_of_this_mint_in_the_store": 2, "next_export_commit": "45a28eedc942220d245d8de8707fcb8f4d713da7", "next_export_context": "REFUSED: narrative tables of commit 45a28eedc9 are not the decision's export 698f73b854 at T (P04, CX-10)", "pass": true, "truncated_store_snapshot_equal": true}

## Invalid inputs

- holdout_start_card_on_this_development_decision: REFUSED: card S2_SC_LOGIT_B2:price_path_target_before_invalidation_24h trained to 2026-10-17T00:00:00Z cannot score 1 earlier decision(s) (P13, RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF)
- next_decision_value_used: REFUSED: row 0: sc_attention_trend_ord__available_at 1792406045.0 is after the decision 1791886823.0 (future feature, P36)
- next_export_narrative_tables: REFUSED: narrative tables of commit 45a28eedc9 are not the decision's export 698f73b854 at T (P04, CX-10)
- non_finite_value: REFUSED: value nan is not finite (P38)
- view_row_available_after_T: REFUSED: decision record available at 1791886824.0 reached a strategy at cutoff 1791886823.0

## Independent recomputation

`verify_trace_social.py` (no socialcat.py, no features.py): 8 values, 11 model inputs and 8 model numbers recomputed; token row equal to the decision's own export: True; differences: 0; values available after the decision: 0; pass: True.
