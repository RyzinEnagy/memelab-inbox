# Forecast trace (Phase 08, price_path_target_before_invalidation_6h)

PROVISIONAL_PENDING_REVISION_REREAD (PI-D-046). Research only; no number here is a published probability.

Selection rule (fixed before the run): earliest out-of-sample row of T1b (then T1, T2) by decision time then mint with every tech-1 feature.

| Item | Value |
|---|---|
| Decision key | `efa03ae4fa14ee4d6825f87cc4015ef2cc9c5ffd80226944db9bac72899cc426` |
| Mint (exact) | `1zJX5gRnjLgmTpq5sVwkq69mNDQkCemqoasyjaPW6jm` |
| Point-in-time pool | `4SBYWY5UuxybWuj8FwHdFXUN6mbtACrqbJwiZ9mXworP` |
| Decision time (export commit) | 2026-10-12T10:18:37Z |
| Decision row sha256 | `419cb84e7fb62a249125c43f672b2a950cc60fe2212ca69dba927fd50e81cb81` |
| Fold and cutoff | 0, trained to 2026-10-12T00:00:00Z |
| tech-1 snapshot sha | `d456dccbedad97f21a3ba040b281023cf0b166940f46243bedc181a752c13a90` |
| Outcome (known only after maturity, not an input) | 0 |

## Candles of the last hour, in time order

Every candle read is visible at T: its end plus the 300 s provider lag, or the lab's read, is at or before T. Only closes and volumes are read.

| Start (UTC) | End (UTC) | Available at (UTC) | Basis | Close (USD) | Volume (USD) |
|---|---|---|---|---|---|
| 2026-10-12T09:10:00Z | 2026-10-12T09:15:00Z | 2026-10-12T09:20:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.01689118263 | 1260.9 |
| 2026-10-12T09:50:00Z | 2026-10-12T09:55:00Z | 2026-10-12T10:00:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.01739139739 | 396.934 |
| 2026-10-12T09:55:00Z | 2026-10-12T10:00:00Z | 2026-10-12T10:05:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.01763644262 | 2287.68 |
| 2026-10-12T10:00:00Z | 2026-10-12T10:05:00Z | 2026-10-12T10:10:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.01780449079 | 2714.36 |
| 2026-10-12T10:05:00Z | 2026-10-12T10:10:00Z | 2026-10-12T10:15:00Z | PROVIDER_LAG_RECONSTRUCTION | 0.01807792236 | 2959.16 |

## Candles that existed for this pool but were not available at T (never read)

| Start (UTC) | End (UTC) | Available at (UTC) | Basis |
|---|---|---|---|
| 2026-10-12T10:10:00Z | 2026-10-12T10:15:00Z | 2026-10-12T10:20:00Z | PROVIDER_LAG_RECONSTRUCTION |

## tech-1 values at T

| Feature | Value | Available at (UTC) | Independent recomputation |
|---|---|---|---|
| `tech_failed_breakout_1h` | 0 | 2026-10-12T10:15:00Z | 0 |
| `tech_log1p_candles_24h` | 4.634728988 | 2026-10-12T10:15:00Z | 4.634728988 |
| `tech_log1p_last_close_age_min` | 2.263497704 | 2026-10-12T10:15:00Z | 2.263497704 |
| `tech_log_breakout_1h` | -0.09963590937 | 2026-10-12T10:15:00Z | -0.09963590937 |
| `tech_log_dist_24h_high` | -0.09963590937 | 2026-10-12T10:15:00Z | -0.09963590937 |
| `tech_log_pullback_6h` | -0.0878808018 | 2026-10-12T10:15:00Z | -0.0878808018 |
| `tech_log_range_24h` | 0.468174895 | 2026-10-12T10:15:00Z | 0.468174895 |
| `tech_log_range_6h` | 0.1557804885 | 2026-10-12T10:15:00Z | 0.1557804885 |
| `tech_log_rel_vol_1h` | -0.567335191 | 2026-10-12T10:15:00Z | -0.567335191 |
| `tech_log_ret_1h` | 0.06789968667 | 2026-10-12T10:15:00Z | 0.06789968667 |
| `tech_log_ret_24h` | 0.3296181551 | 2026-10-12T10:15:00Z | 0.3296181551 |
| `tech_log_ret_6h` | -0.01433559365 | 2026-10-12T10:15:00Z | -0.01433559365 |
| `tech_retest_6h` | 0 | 2026-10-12T10:15:00Z | 0 |
| `tech_rv_1h` | 0.03700922347 | 2026-10-12T10:15:00Z | 0.03700922347 |
| `tech_rv_6h` | 0.1634581521 | 2026-10-12T10:15:00Z | 0.1634581521 |

## Numbers from the fold's cards

| Model | Card model sha (first 12) | Trained to | Number | Abstain reason | Independent |
|---|---|---|---|---|---|
| B0 | `4db8e3c93fa0` | 2026-10-12T00:00:00Z | 0.127778 |  | 0.127778 |
| B2 | `cb6a5b5f88c3` | 2026-10-12T00:00:00Z | 0.026526 |  | 0.026526 |
| M1_T_LOGIT | `11c5a3325999` | 2026-10-12T00:00:00Z |  | INSUFFICIENT_HISTORY |  |
| M2_T_LOGIT_B2 | `e548dc99c273` | 2026-10-12T00:00:00Z |  | INSUFFICIENT_HISTORY |  |
| M3_T_STUMPS | `706c2bdd7685` | 2026-10-12T00:00:00Z |  | INSUFFICIENT_HISTORY |  |

## Invalid inputs, each rejected

| Input | Result |
|---|---|
| candle_closing_at_T_used | REFUSED: row 0: tech_log_ret_1h__available_at 1791800617.0 is after the decision 1791800317.0 (future feature, P36) |
| holdout_start_card_on_this_development_decision | REFUSED: card M2_T_LOGIT_B2:price_path_target_before_invalidation_6h trained to 2026-10-17T00:00:00Z cannot score 1 earlier decision(s) (P13, RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF) |
| non_finite_feature | no number, reason INSUFFICIENT_HISTORY |
| non_finite_feature_in_a_fit | REFUSED: Stumps.fit: inputs must be finite (run Prep first; P38) |
| view_row_available_after_T | REFUSED: candle record available at 1791800318.0 reached a strategy at cutoff 1791800317.0 |

Independent check (`probes/verify_trace.py`): no difference; latency of one forecast from the store, median of 20: 0.0141 s.
