# Outcome calibration, 24 h window (outcomes-v1)

segments are historical correlations among the lab's own records, not causes; a segment with fewer than 30 complete outcomes is INSUFFICIENT_SAMPLE; censored outcomes count in drawdown shares as observed lower bounds.

Overall: 1023 opportunities, 385 complete, 133 censored, 463 not observable, 42 pending. Selection-bias risk: yes (45% not observable or not tracked).

## cohort

- LAB_REJECTION:REJECTED_AT_SCREEN: n 641, complete 155, censored 67, not observable 390; median close -6.1%; down 50% or more 25% (95% 19% to 31%, n 195); REPORTABLE
- LAB_THESIS:DISTRIBUTION RISK: n 49, complete 25, censored 1, not observable 18; median close -2.5%; down 50% or more 8% (95% 2% to 25%, n 25); INSUFFICIENT_SAMPLE
- LAB_THESIS:NEAR ENTRY: n 8, complete 8, censored 0, not observable 0; median close -5.8%; down 50% or more 0% (95% 0% to 32%, n 8); INSUFFICIENT_SAMPLE
- LAB_THESIS:OVEREXTENDED: n 16, complete 14, censored 1, not observable 0; median close +0.4%; down 50% or more 13% (95% 4% to 38%, n 15); INSUFFICIENT_SAMPLE
- LAB_THESIS:REJECTED: n 192, complete 105, censored 51, not observable 30; median close -7.6%; down 50% or more 23% (95% 17% to 31%, n 136); REPORTABLE
- LAB_THESIS:RESEARCH REQUIRED: n 51, complete 23, censored 12, not observable 16; median close -0.1%; down 50% or more 22% (95% 11% to 41%, n 27); INSUFFICIENT_SAMPLE
- LAB_THESIS:SETUP DEVELOPING: n 27, complete 26, censored 0, not observable 0; median close -5.7%; down 50% or more 8% (95% 2% to 24%, n 26); INSUFFICIENT_SAMPLE
- LAB_THESIS:THESIS DETERIORATING: n 9, complete 5, censored 0, not observable 4; median close -6.6%; down 50% or more 0% (95% 0% to 43%, n 5); INSUFFICIENT_SAMPLE
- LAB_THESIS:THESIS INVALIDATED: n 23, complete 17, censored 1, not observable 5; median close -3.0%; down 50% or more 6% (95% 1% to 27%, n 17); INSUFFICIENT_SAMPLE
- LAB_THESIS:WATCH: n 7, complete 7, censored 0, not observable 0; median close -15.4%; down 50% or more 0% (95% 0% to 35%, n 7); INSUFFICIENT_SAMPLE

## token_age

- 1-7d: n 105, complete 82, censored 18, not observable 2; median close -2.8%; down 50% or more 39% (95% 29% to 49%, n 93); REPORTABLE
- 6-24h: n 41, complete 26, censored 14, not observable 0; median close -55.4%; down 50% or more 61% (95% 45% to 75%, n 36); INSUFFICIENT_SAMPLE
- <6h: n 40, complete 13, censored 26, not observable 0; median close -67.6%; down 50% or more 55% (95% 38% to 71%, n 31); INSUFFICIENT_SAMPLE
- >=7d: n 342, complete 262, censored 75, not observable 0; median close -4.8%; down 50% or more 5% (95% 3% to 8%, n 299); REPORTABLE
- UNKNOWN: n 495, complete 2, censored 0, not observable 461; median close -81.9%; down 50% or more 100% (95% 34% to 100%, n 2); INSUFFICIENT_SAMPLE

## liquidity_band

- 250k-1M: n 100, complete 73, censored 5, not observable 20; median close -6.6%; down 50% or more 14% (95% 8% to 24%, n 78); REPORTABLE
- 50k-250k: n 101, complete 67, censored 8, not observable 20; median close -9.4%; down 50% or more 27% (95% 18% to 38%, n 71); REPORTABLE
- <50k: n 92, complete 43, censored 45, not observable 2; median close +0.0%; down 50% or more 19% (95% 12% to 30%, n 67); REPORTABLE
- >=1M: n 49, complete 25, censored 4, not observable 18; median close -1.3%; down 50% or more 0% (95% 0% to 13%, n 25); INSUFFICIENT_SAMPLE
- UNKNOWN: n 681, complete 177, censored 71, not observable 403; median close -5.6%; down 50% or more 22% (95% 17% to 28%, n 220); REPORTABLE

## market_regime

- SOL_DOWN: n 247, complete 120, censored 49, not observable 78; median close -6.0%; down 50% or more 24% (95% 18% to 32%, n 152); REPORTABLE
- SOL_FLAT: n 723, complete 255, censored 70, not observable 356; median close -5.3%; down 50% or more 19% (95% 15% to 24%, n 293); REPORTABLE
- SOL_UP: n 53, complete 10, censored 14, not observable 29; median close -6.9%; down 50% or more 0% (95% 0% to 19%, n 16); INSUFFICIENT_SAMPLE

## catalyst_type

- CURVE_LIVE: n 14, complete 6, censored 6, not observable 2; median close -32.8%; down 50% or more 67% (95% 39% to 86%, n 12); INSUFFICIENT_SAMPLE
- GRADUATION: n 37, complete 17, censored 20, not observable 0; median close +29.5%; down 50% or more 60% (95% 44% to 74%, n 35); INSUFFICIENT_SAMPLE
- LAUNCHLAB_NEW: n 2, complete 0, censored 2, not observable 0; median close n/a; down 50% or more 0% (95% 0% to 66%, n 2); INSUFFICIENT_SAMPLE
- NONE: n 970, complete 362, censored 105, not observable 461; median close -5.3%; down 50% or more 15% (95% 12% to 19%, n 412); REPORTABLE

## source_credibility

- NO_CATALYST: n 970, complete 362, censored 105, not observable 461; median close -5.3%; down 50% or more 15% (95% 12% to 19%, n 412); REPORTABLE
- VERIFIED_CONTEMPORANEOUS: n 53, complete 23, censored 28, not observable 2; median close +29.5%; down 50% or more 59% (95% 45% to 72%, n 49); INSUFFICIENT_SAMPLE
