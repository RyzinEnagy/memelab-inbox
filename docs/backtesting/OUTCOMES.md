# Outcomes, calibration and drift

Shadow evaluation only. Nothing here trades, and nothing changes a stored run, a stored assessment or a strategy.

## What is tracked

Every frozen decision the lab recorded becomes an opportunity:
- the first appearance of each {mint, lab status} among the lab's theses;
- every screened-out rejection;
- every stored FAST assessment.

Outcomes are measured at fixed windows of 1 h, 6 h, 24 h and 72 h (protocol `outcomes-v1`), using only bars available at the outcome's own as-of time. Each window ends in one of these states:
- COMPLETE: the window has price bars to its end. The record holds close, worst and best returns against the first open after the decision, and a down-50% flag.
- CENSORED: bars stop early (the drawdown is a lower bound) or there are none after the decision (the token stopped trading or the provider has a gap).
- NOT_OBSERVABLE: no bars were stored for the mint, or no pool had bars within 48 h of the decision.
- PENDING: the window has not closed and published yet.

Nothing is dropped.

Rows are append-only:
- recomputing with the same data adds nothing;
- a late backfill or a provider revision adds a new row that points at the one it supersedes;
- an earlier as-of never sees a later revision.

## Commands

| Command | What it does |
|---|---|
| `python -m memelab backtest outcomes track [--now UTC] [--asof UTC] [--min-interval S]` | One scheduled pass. At most one per interval; unchanged results add no rows. |
| `python -m memelab backtest outcomes calibrate [--horizon-h 24] [--with-launches] [--json]` | Calibration by segment, with sample counts and censoring. |
| `python -m memelab backtest outcomes reconcile [--horizon-h 24]` | Stress-model liquidity against the lab's own later snapshot. |
| `python -m memelab backtest outcomes drift` | Coverage drift, stale pending windows, calibration drift, provider revisions, collector health. |
| `python -m memelab backtest outcomes daily --day YYYY-MM-DD --asof UTC` | Replayable daily report, byte-identical for the same as-of. |
| `python -m memelab backtest outcomes shadow --strategy ID --since UTC` | Frozen strategy run forward, not saved, no order path. |

## Segments

There are six segments, all known at decision time:
- lab cohort (source and status);
- token age (from the pool's creation time);
- liquidity band (from the lab's snapshot);
- SOL regime (24 h SOL/USD change from bars available then);
- catalyst type;
- source credibility.

Catalyst type and credibility come only from records available at the decision. A capture made later, a corrected publication time or a later deletion never changes an earlier decision.

Segments are correlations among the lab's own records, not causes. Any segment with fewer than 30 complete outcomes is INSUFFICIENT_SAMPLE. When more than 20% of opportunities are not observable, the study is flagged for selection-bias risk.

## Re-evaluation policy (no in-place retuning)

When drift or reconciliation finds a deviation (calibration drift, provider coverage drift, or a slippage-model error above 25% over 30 or more pairs), it opens a REEVALUATION_PROPOSED record. A new evaluation requires:
1. a new pre-registration, hashed before any new data is looked at;
2. a new sealed train/validation/test split that starts after the current sealed test;
3. a new strategy version id. The current version and its runs stay as they are;
4. a logged entry in DECISIONS.md.

`retune_in_place` always refuses.

## Collector monitoring

Maxun was not adopted (Phase 06A), so no Maxun metrics exist and none are reported. Monitoring covers the chosen collectors as stored in `bt_capture_provenance`:
- late-arrival share;
- duplicate share;
- misattribution risk;
- extractor versions and incomplete extractions;
- failed runs;
- the longest gap between captures.

The store refuses a mint attached without verification, so misattribution shows up as zero by construction; unverified mentions are kept as claims instead.
