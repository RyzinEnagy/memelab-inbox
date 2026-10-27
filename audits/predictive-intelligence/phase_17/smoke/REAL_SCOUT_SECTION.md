
## Predictive research section (flag on, research only)

This section is separate from the opportunity score. It does not change the 100-point score, the fatal flags, the status, the watchlist or the lists above, and it is not advice.

- Integration: integration-1, mode fast, capture 2026-10-27T08:44:59Z, pass 4ba112f38edc
- Backtesting: BACKTEST_NOT_AVAILABLE
- Model registry: OK
  - T1_24h: NO_VIABLE_CHAMPION (NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_BSS_BELOW_0+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); calibration UNCALIBRATED
  - T1b_6h: NO_VIABLE_CHAMPION (NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_CALIBRATION_FAILED+RETROSPECTIVE_BSS_BELOW_0+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); calibration UNCALIBRATED
  - T2_24h: NO_VIABLE_CHAMPION (NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_BELOW_MINIMUM+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); calibration UNCALIBRATED
- Depth collector: COLLECTOR_NOT_AVAILABLE
- Counts: 8 events, 8 attempted, 0 published, 24 abstentions, 0 unchanged, 0 duplicates, 0 superseded, 0 deferred, 0 not attempted, 0 errors; latency p50 2.911 ms, max 4.18 ms; models in use: not_selected
- Records: the predictive state directory (`python -m memelab.predictive.integration status`)

### PAID `solana:98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump`
- Snapshot 744ef961b24239b9; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 19005b666141
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record fcf000bc5a65
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 176304691b82
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_PAID_98kfF7.md

### STONK `solana:6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx`
- Snapshot 771e6521fb6cef2b; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record a09ce7e3daf4
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record ae668039a816
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record 1f254310d827
  - No probability for whether the price halves or trading halts within 24 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_STONK_6GmAFS.md

### DARK `solana:7KEPApdbBMByrmqihz3bht2uMhFQcatjfSFQCKq66kH3`
- Snapshot c1c7dae80d324251; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 954286f3f929
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 577e61b0efb1
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record a7911c89bd28
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_DARK_7KEPAp.md

### GOMO `solana:9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump`
- Snapshot 599dbfcdf78eba2e; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: CANNOT_EXIT_5K; no forecast clears it
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record ee1abea4770e
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 2ef507c103bf
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record bb83dad2aa8e
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_GOMO_9XKzy4.md

### HIGGS `solana:DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump`
- Snapshot 94125012eafce70e; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: WASH_TRADING_HIGH; no forecast clears it
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record f097ad2e9434
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record f47ab3c66f82
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record b7aab8e6e566
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_HIGGS_DoVAVz.md

### ZCAT `solana:HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR`
- Snapshot 7b982f14be1d1a8b; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record c130dbbc3c05
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record 0dce5ca5eda0
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record 2bb7fec3e5e3
  - No probability for whether the price halves or trading halts within 24 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_ZCAT_HcRLc9.md

### baton `solana:Hg5Ja55T5wESq4vyFoiVCMeHXtGyVA69X2UHq8hgpump`
- Snapshot 3299be006a2bb1ac; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 6f075365a99f
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record a4d112af13b8
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record d12c4e12bb38
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_baton_Hg5Ja5.md

### slopcannon `solana:55Vr2VpSwxsDkB6uGGHAvRv86K6zax2Zb4TT8ivwDEzW`
- Snapshot b6f9f499178e9563; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: WASH_TRADING_HIGH; no forecast clears it
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record d21089db9d5b
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 9f61994fa5cb
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record e5b2806fe370
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: 20261007_0016_slopcannon_55Vr2V.md

- Stage-2 structural rejects (8) are not decisions (no thesis row) and get no forecast attempt.
