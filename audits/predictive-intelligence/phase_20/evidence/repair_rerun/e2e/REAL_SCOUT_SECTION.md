
## Predictive research section (flag on, research only)

This section is separate from the opportunity score. It does not change the 100-point score, the fatal flags, the status, the watchlist or the lists above, and it is not advice.

- Integration: integration-1, mode fast, capture 2026-10-27T18:04:15Z, pass d565327d1f62
- Backtesting: BACKTEST_NOT_AVAILABLE
- Model registry: OK
  - T1_24h: NO_VIABLE_CHAMPION (NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_BSS_BELOW_0+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); calibration UNCALIBRATED
  - T1b_6h: NO_VIABLE_CHAMPION (NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_CALIBRATION_FAILED+RETROSPECTIVE_BSS_BELOW_0+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); calibration UNCALIBRATED
  - T2_24h: NO_VIABLE_CHAMPION (NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_BELOW_MINIMUM+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); calibration UNCALIBRATED
- Depth collector: COLLECTOR_NOT_AVAILABLE
- Counts: 8 events, 8 attempted, 0 published, 24 abstentions, 0 unchanged, 0 duplicates, 0 superseded, 0 deferred, 0 not attempted, 0 errors; latency p50 2.957 ms, max 3.622 ms; models in use: not_selected
- Records: the predictive state directory (`python -m memelab.predictive.integration status`)

### PAID `solana:98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump`
- Snapshot 744ef961b24239b9; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 867edf09ecf9
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record cdc94e33d237
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 7fd8b33909bd
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_PAID_98kfF7.md

### STONK `solana:6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx`
- Snapshot 771e6521fb6cef2b; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record 996ff3dccb7b
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record b1a36c710c2b
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record 4cf5571e45e4
  - No probability for whether the price halves or trading halts within 24 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_STONK_6GmAFS.md

### DARK `solana:7KEPApdbBMByrmqihz3bht2uMhFQcatjfSFQCKq66kH3`
- Snapshot c1c7dae80d324251; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record c3a04c8408a8
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record f6ff17a0985a
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record b017ea65f499
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_DARK_7KEPAp.md

### GOMO `solana:9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump`
- Snapshot 599dbfcdf78eba2e; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: CANNOT_EXIT_5K; no forecast clears it
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record f17b90b42470
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 4a3146f1de13
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 86420acb9501
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_GOMO_9XKzy4.md

### HIGGS `solana:DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump`
- Snapshot 94125012eafce70e; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: WASH_TRADING_HIGH; no forecast clears it
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 5136fd499a83
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record b794acdb5e38
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record c6c041a080a6
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_HIGGS_DoVAVz.md

### ZCAT `solana:HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR`
- Snapshot 7b982f14be1d1a8b; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record 3529585b5d13
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record 22cf651f1c7a
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record 3ddd1ee30f39
  - No probability for whether the price halves or trading halts within 24 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_ZCAT_HcRLc9.md

### baton `solana:Hg5Ja55T5wESq4vyFoiVCMeHXtGyVA69X2UHq8hgpump`
- Snapshot 3299be006a2bb1ac; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record f72d44634e4c
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record e624984ea14d
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 667e0cb2792d
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_baton_Hg5Ja5.md

### slopcannon `solana:55Vr2VpSwxsDkB6uGGHAvRv86K6zax2Zb4TT8ivwDEzW`
- Snapshot b6f9f499178e9563; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: WASH_TRADING_HIGH; no forecast clears it
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 4eca711cbac4
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record cf63e92dae97
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 644d65d27cbf
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_slopcannon_55Vr2V.md

- Stage-2 structural rejects (8) are not decisions (no thesis row) and get no forecast attempt.
