# Abstention matrix (Phase 13, abstention-1)

Source: `ABSTENTION_MATRIX.csv`, written by `probes/run_calibration.py` (run at `2e1488a`). Each of the 28 conditions maps to one reason of the frozen contract (`contract.ABSTAIN_REASONS`, unchanged); every condition is evaluated for every request, so a request is counted under each condition that holds. Development: the champion B2's out-of-sample rows with the fold card and the calibration card as of each fold cutoff. Holdout: the scored retrospective-holdout rows, POST_OPENING description only (PI-D-066). Tests are in `tests/test_predictive_abstention.py`.

| Condition | Contract reason | Dev T1 | Dev T1b | Dev T2 | Holdout T1 | Holdout T1b | Holdout T2 | Test that triggers it alone |
|---|---|---|---|---|---|---|---|---|
| FLAG_OFF | FLAG_OFF | 24 | 44 | 8 | 66 | 68 | 59 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[FLAG_OFF]` |
| CHAIN_OUT_OF_SCOPE | OUT_OF_SCOPE_CHAIN | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[CHAIN_OUT_OF_SCOPE]` |
| MINT_NOT_VERIFIED | UNVERIFIED_EVENT | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[MINT_NOT_VERIFIED]` |
| TARGET_NOT_PRIMARY | TARGET_NOT_FEASIBLE | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[TARGET_NOT_PRIMARY]` |
| POOL_NOT_POINT_IN_TIME | TARGET_NOT_FEASIBLE | 5 | 11 | 1 | 12 | 14 | 11 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[POOL_NOT_POINT_IN_TIME]` |
| MARKET_INACTIVE | NO_RECENT_PRICE | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[MARKET_INACTIVE]` |
| SOURCE_GAP | SOURCE_STALE | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[SOURCE_GAP]` |
| DISALLOWED_INPUT | RESTRICTED_SOURCE | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[DISALLOWED_INPUT]` |
| SIZE_REQUESTED | EXECUTION_DATA_MISSING | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[SIZE_REQUESTED]` |
| BACKTEST_REQUIRED_NOT_AVAILABLE | EXECUTION_DATA_MISSING | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[BACKTEST_REQUIRED_NOT_AVAILABLE]` |
| MISSING_REQUIRED_INPUT | OOD | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[MISSING_REQUIRED_INPUT]` |
| FEATURE_OUT_OF_RANGE | OOD | 0 | 1 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[FEATURE_OUT_OF_RANGE]` |
| SCORE_OUTSIDE_CALIBRATION_RANGE | OOD | 0 | 4 | 0 | 4 | 2 | 10 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[SCORE_OUTSIDE_CALIBRATION_RANGE]` |
| NO_TOKEN_HISTORY | INSUFFICIENT_HISTORY | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[NO_TOKEN_HISTORY]` |
| MODEL_NOT_PROMOTED | MODEL_NOT_SELECTED | 24 | 44 | 8 | 66 | 68 | 59 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[MODEL_NOT_PROMOTED]` |
| NO_CHAMPION | MODEL_NOT_SELECTED | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[NO_CHAMPION]` |
| MODEL_TRAINED_AFTER_DECISION | MODEL_NOT_SELECTED | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[MODEL_TRAINED_AFTER_DECISION]` |
| MODEL_TOO_OLD | MODEL_STALE | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[MODEL_TOO_OLD]` |
| FEATURE_SET_MISMATCH | FEATURE_SCHEMA_MISMATCH | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[FEATURE_SET_MISMATCH]` |
| INVALID_PROBABILITY | MODEL_NOT_SELECTED | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[INVALID_PROBABILITY]` |
| NO_CALIBRATOR | UNCALIBRATED | 24 | 44 | 8 | 66 | 68 | 59 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[NO_CALIBRATOR]` |
| DEGENERATE_FLAT_PREDICTIONS | UNCALIBRATED | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[DEGENERATE_FLAT_PREDICTIONS]` |
| POINT_OUTSIDE_DISPLAY_RANGE | UNCALIBRATED | 0 | 0 | 0 | 0 | 0 | 0 | `test_display_range_and_support_conditions[POINT_OUTSIDE_DISPLAY_RANGE-patch0]` |
| CALIBRATION_SET_TOO_SMALL | INSUFFICIENT_HISTORY | 24 | 44 | 8 | 66 | 68 | 59 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[CALIBRATION_SET_TOO_SMALL]` |
| CALIBRATION_EVIDENCE_TOO_SMALL | INSUFFICIENT_HISTORY | 24 | 44 | 8 | 66 | 68 | 59 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[CALIBRATION_EVIDENCE_TOO_SMALL]` |
| LOW_SUPPORT | INSUFFICIENT_HISTORY | 24 | 28 | 8 | 4 | 2 | 59 | `test_display_range_and_support_conditions[LOW_SUPPORT-patch1]` |
| CALIBRATION_EVIDENCE_PENDING | NOT_YET_MATURED | 24 | 44 | 8 | 66 | 68 | 59 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[CALIBRATION_EVIDENCE_PENDING]` |
| DRIFT | DRIFT_ALERT | 0 | 0 | 0 | 0 | 0 | 0 | `test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason[DRIFT]` |

## Coverage

| Measure | Dev T1 | Dev T1b | Dev T2 | Holdout T1 | Holdout T1b | Holdout T2 |
|---|---|---|---|---|---|---|
| requests | 24 | 44 | 8 | 66 | 68 | 59 |
| forecast | 0 | 0 | 0 | 0 | 0 | 0 |
| raw_number | 24 | 44 | 8 | 66 | 68 | 59 |
| calibrated_number | 0 | 0 | 0 | 0 | 0 | 0 |

Abstention rate 100% everywhere; published probability 0 of 269 requests (76 development, 193 holdout); calibrated number 0. Conditions with 0 here are the ones today's data cannot trigger (for example every development decision is Solana with a verified mint and an ELIGIBLE label); each is still triggered by its test. The 10 prospective decisions of `TODAY_STATUS.json` are not in this table: they add OOD (missing inputs) and SOURCE_STALE (no price read) to the standing reasons.

