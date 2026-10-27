
## Predictive research section (flag on, research only)

This section is separate from the opportunity score. It does not change the 100-point score, the fatal flags, the status, the watchlist or the lists above, and it is not advice.

- Integration: integration-1, mode fast, capture 2026-10-27T06:38:23Z, pass 244885271bf3
- Backtesting: BACKTEST_NOT_AVAILABLE
- Model registry: OK
  - T1_24h: NO_VIABLE_CHAMPION (NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_BSS_BELOW_0+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); calibration UNCALIBRATED
  - T1b_6h: NO_VIABLE_CHAMPION (NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_CALIBRATION_FAILED+RETROSPECTIVE_BSS_BELOW_0+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); calibration UNCALIBRATED
  - T2_24h: NO_VIABLE_CHAMPION (NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_BELOW_MINIMUM+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); calibration UNCALIBRATED
- Depth collector: COLLECTOR_NOT_AVAILABLE
- Counts: 8 events, 8 attempted, 0 published, 24 abstentions, 0 unchanged, 0 duplicates, 0 superseded, 0 deferred, 0 not attempted, 0 errors; latency p50 3.075 ms, max 3.534 ms; models in use: not_selected
- Records: OUTDIR/state

### PAID `solana:98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump`
- Snapshot 1274c59c1f2f3b4b; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record a05a5f795ba1
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 4d38f3162942
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 0c7944e1a3bc
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: OUTDIR/reports/20261007_0016_PAID_98kfF7.md

### STONK `solana:6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx`
- Snapshot a9c7bba688ee7967; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record 85996cb2a188
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record 2cc335168489
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record c344d869c75b
  - No probability for whether the price halves or trading halts within 24 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: OUTDIR/reports/20261007_0016_STONK_6GmAFS.md

### DARK `solana:7KEPApdbBMByrmqihz3bht2uMhFQcatjfSFQCKq66kH3`
- Snapshot 32a060fdc78c3382; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 77f40ab24580
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record bdf82520be75
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 5f6a14e268df
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: OUTDIR/reports/20261007_0016_DARK_7KEPAp.md

### GOMO `solana:9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump`
- Snapshot c1f3d8e09db98608; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: CANNOT_EXIT_5K; no forecast clears it
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 9d1eb1107beb
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 92776015268d
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 1fdb6ee50a6c
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: OUTDIR/reports/20261007_0016_GOMO_9XKzy4.md

### HIGGS `solana:DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump`
- Snapshot 02d31819d228d9ca; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: WASH_TRADING_HIGH; no forecast clears it
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record deafdaf9e607
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record f2bc250c429b
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 5527fbd29b56
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: OUTDIR/reports/20261007_0016_HIGGS_DoVAVz.md

### ZCAT `solana:HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR`
- Snapshot 912628fd7b3210ba; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record 7cb8e2e0be84
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record 0dbf7645264a
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED); record 6bb94005530d
  - No probability for whether the price halves or trading halts within 24 hours: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: OUTDIR/reports/20261007_0016_ZCAT_HcRLc9.md

### baton `solana:Hg5Ja55T5wESq4vyFoiVCMeHXtGyVA69X2UHq8hgpump`
- Snapshot 2ce35195fed57456; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: none recorded by the lab
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 37d8cfb1d174
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 6b38ccde53db
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record bfdf78dcb17e
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: OUTDIR/reports/20261007_0016_baton_Hg5Ja5.md

### slopcannon `solana:55Vr2VpSwxsDkB6uGGHAvRv86K6zax2Zb4TT8ivwDEzW`
- Snapshot a00eb3ce7d014cf8; event DISCOVERY (first attempt for this chain and mint)
- Fatal-flag veto: WASH_TRADING_HIGH; no forecast clears it
- Size: EXECUTION_DATA_MISSING; no position size comes from a forecast
- Inputs: INPUT_STALE; reference price INPUT_STALE; backtest BACKTEST_NOT_AVAILABLE
- 24 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 04ade3807d0f
  - No probability for whether the price rises 25 percent before it falls 15 percent within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 6 hours, +25% before -15%: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record 05998e926d53
  - No probability for whether the price rises 25 percent before it falls 15 percent within 6 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- 24 hours, halving or halt: ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED); record bed1e816a17b
  - No probability for whether the price halves or trading halts within 24 hours: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- Token report: OUTDIR/reports/20261007_0016_slopcannon_55Vr2V.md

- Stage-2 structural rejects (8) are not decisions (no thesis row) and get no forecast attempt.
