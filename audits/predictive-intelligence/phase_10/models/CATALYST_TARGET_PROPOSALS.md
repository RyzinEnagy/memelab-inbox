# Catalyst target proposals (PROPOSED_NOT_FROZEN, TEST_ONLY)

Status: proposals only. Nothing here is in the target registry (fingerprint `4b4aabce...` unchanged) or in ACCEPTANCE. The catalyst-follow-through target was BLOCKED_NO_DATA in Phase 01 (TARGET_REGISTRY.md) and stays so: no catalyst event, item or token link exists for any of the lab's decisions (`data/CATALYST_PROVENANCE.md`). Freezing any of these targets is a later change control, committed before any of its outcomes is read, once forward catalyst and social data exist in a store this engine can read (approvals needed, PI-D-005). The proposal functions in `memelab/predictive/socialcat.py` have no default parameters, label fixtures only, and carry `PROPOSED_NOT_FROZEN` and `TEST_ONLY`.

## 1. Catalyst follow-through (`proposed_follow_through_label`)

- Unit: one catalyst event and one exact (chain, mint) for which `classify_catalyst` gives VERIFIED at the decision. UNVERIFIED_EVENT, IDENTITY_UNVERIFIED and NOT_AVAILABLE_AT_DECISION are never labelled and never get a probability.
- Start: the first 5-minute candle whose start is at or after `available_at + provider_lag_s`, where `available_at` is the later of the event's earliest visible source sighting (`first_seen_at`, never `published_at`) and the exact-mint link's `linked_at`. The reference price is that candle's close: the first price a reader of the catalyst could act on.
- Event: `up` touched before `down` within `horizon_s`; a candle touching both is negative (the AMBIGUOUS_BAR convention of T1); a path shorter than the horizon is PENDING or CENSORED, never negative; no price after availability is CENSORED_NO_PRICE_AFTER_AVAILABILITY.
- Parameters to freeze later (no default in code): `provider_lag_s`, `up`, `down`, `horizon_s`. The natural first choice is T1's (300 s, +25%, -15%, 24 h) so results compare with the frozen targets, but that is for the change control to decide.
- Price-path only: no size, no fill, PRICE_PATH_NOT_PROCEEDS and NO_HISTORICAL_EXECUTABLE_DEPTH as for T1 (P08, P44).

## 2. Catalyst failure or withdrawal (`proposed_withdrawal_label`)

- Unit: as above (VERIFIED at the decision).
- Event: a DENIED, CANCELLED or DELETED_SOURCE revision recorded after `available_at` and within `horizon_s`. Before the horizon has passed at the reading time without one, the label is PENDING (never a negative); a revision at or before `available_at` belongs to the classification (the event would not have been VERIFIED), not to the label.
- Parameter to freeze later: `horizon_s` (72 h would match the catalyst monitor's longest outcome horizon). A price drawdown variant (T2's half-price rule from the same start as proposal 1) is a separate target if wanted, not a second definition of this one.
- Data needed: the catalyst revision log of forward events with its `revised_at` clock, in a store this engine can read.

## 3. Network-amplification reversal (no code yet)

- Unit: a decision whose attention at T is suspect (`sc_attention_suspect` = 1: a paid boost or a manufactured flow screen) and accelerating (`sc_attention_trend_ord` = 2), or, once social data exist, whose exact-mint mentions are majority bot accounts (`sx_bot_share` above one half).
- Event: the frozen T2 event (half the reference price or a halt within 24 h) on that decision.
- Today this is measured only as the R3 alarm counts on the frozen targets (`experiments/AMPLIFICATION_ALARM.csv`), which is a description at counts this small, not a target. A separate target would need its own eligibility (only suspect, accelerating decisions) and enough of them to meet the training minimums (100 events, 20 per class), which the development data do not have.

## What a change control must state before any outcome is read

The unit and its eligibility, every parameter value, the availability clock, the censoring rules, the identity rule (exact chain and mint, NAMED_IN_SOURCE / STRONG with the mint in a visible original source), the split (forward only, with the prospective holdout), the minimums, the baselines (B0 and B2 at the same decision), and the verdict function (Phase 07's, unchanged).
