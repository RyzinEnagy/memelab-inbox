# Notes on the frozen needs

`NEEDS.csv` is frozen (sha256 `90c9391aa6674abbf138b59e610ce0b72ab7eeb6a15763458e341d6fd6560f5e`, written 2026-10-24T02:55:41Z before the first query) and is not edited after the queries ran; the checker refuses any change. Clarifications made later are recorded here instead.

## N13 behavioral simulation (repair pass 2, independent skeptic finding m6)

GAP_MATRIX.csv has no behavioral-simulation facility. N13 cites `SOCIAL_SIGNALS:MODEL_TRAINING` and `CATALYST:MODEL_TRAINING` only as a proxy: those are the cells where Phase 15 would test whether simulated scenarios add predictive value to a social or catalyst model. The need itself belongs to the PLANNED_SEAMS boundary "Behavioral simulation" (isolated adapter, optional, outside the core package, no probability field). No simulator fills a model-training gap, and MiroFish, OASIS, Mesa and black-it are shortlisted only as scenario generators or comparators. SHORTLIST.csv repeats this in the `gap_link_note` column of every N13 row.

## N06 and N07 in repair pass 2

N06 (point-in-time features) and N07 (analog cohorts and regime-aware estimates, including regime models) are unchanged. Repair pass 2 searched two families under them that the first pass had not: point-in-time feature stores and as-of joins (N06) and regime or state models (N07).
