# Locked research rubric (recorded in Phase 01, before any candidate is scored)

Rubric version: R1.0. Locked 2026-10-23T16:00Z. Source: `workplans/backtesting/references/GRADING_RUBRIC.md` (sha256 0ca26ba8a425826d763ff2dd07b63b474fd36f14b6a47880327356f0ec5701ef).

Project-specific refinement: none to the weights. Reason: the base weights already put 47 of 100 points on what this lab lacks most (A transferability 15, B microstructure 17, C point-in-time 15), and changing weights before seeing candidates gains nothing but room for bias. Applies identically to every contender.

| Criterion | Max |
|---|---:|
| A. Memecoin/DEX transferability | 15 |
| B. Executable market microstructure | 17 |
| C. Point-in-time integrity | 15 |
| D. Social/catalyst/on-chain events | 11 |
| E. TA/strategy flexibility | 9 |
| F. Statistical validation | 11 |
| G. Integration fit (Python, modular, no wallets, fits the lab) | 9 |
| H. Maintenance and test credibility | 6 |
| I. License/supply-chain safety | 5 |
| J. Operational footprint | 2 |
| Total | 100 |

Scoring: grade 0 to 5 in half points per criterion; points = max x grade / 5; round only the total to two decimals. Missing evidence scores 0 to 1, never an assumed 3. Stars never earn points.

Clarifications fixed now (apply to all candidates):

- "Integration fit" (G) is judged against this lab: Python 3.13, SQLite, numpy/pandas available, no always-on services, Windows and Linux.
- A library that is not a backtester (AMM SDK, analytics) is scored on the same rubric; its category fit is tracked separately in the fit matrix, as the rubric allows.
- Hard gates (from RESEARCH_PROTOCOL): no verifiable source, malicious installer, unauditable fill path, serious unresolved security hazard, unknown or incompatible license for the intended use. A gated repo can stay in the ranking as RESEARCH_ONLY with the gate shown.
- Adoption thresholds (unchanged): >=70/100, license/security pass, C >= 3/5 or sandboxed outside chronology-sensitive paths, isolated POC success; any engine used for historical fill assumptions needs B >= 3/5 and the custom golden scenarios.
- Maxun is not scored here (separate Phase 06A track).
