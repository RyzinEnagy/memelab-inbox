# Forecast trace (Phase 08, price_path_target_before_invalidation_6h)

PROVISIONAL_PENDING_REVISION_REREAD (PI-D-046). Research only; no number here is a published probability.

Selection rule (fixed before the run): earliest out-of-sample row of T1b (then T1, T2) by decision time then mint with every tech-1 feature and a number from the primary model M2 (second trace, added after recorded run 1 because the pre-registered row's fold had no fitted technical model).

| Item | Value |
|---|---|
| Decision key | `9105b9d11b14eff43cfc58e66ed479442d651792cc274acd505525dd8814b505` |
| Mint (exact) | `2j5SaS7xy776qCBpyPQbZjyQSAtKiFgrwjfErthnW2ZM` |
| Point-in-time pool | `Fe7bpDYCs74GqiCUF14HwgUMToPKV1d9mDYVX5BTohFr` |
| Decision time (export commit) | 2026-10-16T10:42:06Z |
| Decision row sha256 | `2e9d8f63d3b494bc3ecbd950913dc363d6dbc5208a7ef7d9140212c32a7c06c8` |
| Fold and cutoff | 4, trained to 2026-10-16T00:00:00Z |
| tech-1 snapshot sha | `4bf8dcfe38bc482bff038f87b1a5b7a408d3c0fb4a9145d3d59c07782613618e` |
| Outcome (known only after maturity, not an input) | 0 |

## Candles of the last hour, in time order

Every candle read is visible at T: its end plus the 300 s provider lag, or the lab's read, is at or before T. Only closes and volumes are read.

| Start (UTC) | End (UTC) | Available at (UTC) | Basis | Close (USD) | Volume (USD) |
|---|---|---|---|---|---|
| 2026-10-16T09:35:00Z | 2026-10-16T09:40:00Z | 2026-10-16T09:45:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.006515002496 | 31296.1 |
| 2026-10-16T09:40:00Z | 2026-10-16T09:45:00Z | 2026-10-16T09:50:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.006360159741 | 10610.9 |
| 2026-10-16T09:45:00Z | 2026-10-16T09:50:00Z | 2026-10-16T09:55:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.00620736185 | 11087.5 |
| 2026-10-16T09:50:00Z | 2026-10-16T09:55:00Z | 2026-10-16T10:00:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.005974391208 | 11245.4 |
| 2026-10-16T09:55:00Z | 2026-10-16T10:00:00Z | 2026-10-16T10:05:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.00598230201 | 6447.7 |
| 2026-10-16T10:00:00Z | 2026-10-16T10:05:00Z | 2026-10-16T10:10:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.006058370478 | 2981.28 |
| 2026-10-16T10:05:00Z | 2026-10-16T10:10:00Z | 2026-10-16T10:15:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.006144451048 | 1529.87 |
| 2026-10-16T10:10:00Z | 2026-10-16T10:15:00Z | 2026-10-16T10:20:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.006123090533 | 1243.13 |
| 2026-10-16T10:15:00Z | 2026-10-16T10:20:00Z | 2026-10-16T10:25:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.006124971233 | 1115.59 |
| 2026-10-16T10:20:00Z | 2026-10-16T10:25:00Z | 2026-10-16T10:30:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.006227739828 | 2839.6 |
| 2026-10-16T10:25:00Z | 2026-10-16T10:30:00Z | 2026-10-16T10:35:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.006199661588 | 1788.13 |
| 2026-10-16T10:30:00Z | 2026-10-16T10:35:00Z | 2026-10-16T10:40:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.006051514394 | 3214.95 |

## Candles that existed for this pool but were not available at T (never read)

| Start (UTC) | End (UTC) | Available at (UTC) | Basis |
|---|---|---|---|
| 2026-10-16T10:35:00Z | 2026-10-16T10:40:00Z | 2026-10-16T10:45:00Z | PROVIDER_LAG_RECONSTRUCTION |

## tech-1 values at T

| Feature | Value | Available at (UTC) | Independent recomputation |
|---|---|---|---|
| `tech_failed_breakout_1h` | 0 | 2026-10-16T10:40:00Z | 0 |
| `tech_log1p_candles_24h` | 5.66296048 | 2026-10-16T10:40:00Z | 5.66296048 |
| `tech_log1p_last_close_age_min` | 2.091864062 | 2026-10-16T10:40:00Z | 2.091864062 |
| `tech_log_breakout_1h` | 0 | 2026-10-16T10:40:00Z | 0 |
| `tech_log_dist_24h_high` | -0.07379903981 | 2026-10-16T10:40:00Z | -0.07379903981 |
| `tech_log_pullback_6h` | -0.07379903981 | 2026-10-16T10:40:00Z | -0.07379903981 |
| `tech_log_range_24h` | 0.7140790538 | 2026-10-16T10:40:00Z | 0.7140790538 |
| `tech_log_range_6h` | 0.2219067627 | 2026-10-16T10:40:00Z | 0.2219067627 |
| `tech_log_rel_vol_1h` | -0.7066900961 | 2026-10-16T10:40:00Z | -0.7066900961 |
| `tech_log_ret_1h` | -0.07379903981 | 2026-10-16T10:40:00Z | -0.07379903981 |
| `tech_log_ret_24h` | 0.616437956 | 2026-10-16T10:40:00Z | 0.616437956 |
| `tech_log_ret_6h` | 0.07260963854 | 2026-10-16T10:40:00Z | 0.07260963854 |
| `tech_retest_6h` | 0 | 2026-10-16T10:40:00Z | 0 |
| `tech_rv_1h` | 0.06235567199 | 2026-10-16T10:40:00Z | 0.06235567199 |
| `tech_rv_6h` | 0.174306385 | 2026-10-16T10:40:00Z | 0.174306385 |

## Numbers from the fold's cards

| Model | Card model sha (first 12) | Trained to | Number | Abstain reason | Independent |
|---|---|---|---|---|---|
| B0 | `ac2c93610d83` | 2026-10-16T00:00:00Z | 0.121495 |  | 0.121495 |
| B2 | `acc8aa8ff065` | 2026-10-16T00:00:00Z | 0.167003 |  | 0.167003 |
| M1_T_LOGIT | `ca638cf4bf5b` | 2026-10-16T00:00:00Z | 0.092696 |  | 0.092696 |
| M2_T_LOGIT_B2 | `ac5c960cb004` | 2026-10-16T00:00:00Z | 0.120400 |  | 0.120400 |
| M3_T_STUMPS | `a0c1d14a26d0` | 2026-10-16T00:00:00Z | 0.152859 |  | 0.152859 |

## Invalid inputs, each rejected

| Input | Result |
|---|---|
| candle_closing_at_T_used | REFUSED: row 0: tech_log_ret_1h__available_at 1792147626.0 is after the decision 1792147326.0 (future feature, P36) |
| holdout_start_card_on_this_development_decision | REFUSED: card M2_T_LOGIT_B2:price_path_target_before_invalidation_6h trained to 2026-10-17T00:00:00Z cannot score 1 earlier decision(s) (P13, RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF) |
| non_finite_feature | no number, reason OOD |
| non_finite_feature_in_a_fit | REFUSED: Stumps.fit: inputs must be finite (run Prep first; P38) |
| view_row_available_after_T | REFUSED: candle record available at 1792147327.0 reached a strategy at cutoff 1792147326.0 |

Independent check (`probes/verify_trace.py`): no difference; latency of one forecast from the store, median of 20: 0.0499 s.
