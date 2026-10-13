# Phase 16: immutable signal ledger and forward evaluation

Prompt 16. Code: `memelab/social/outcomes_core.py` (pure engine), `memelab/social/outcomes_ledger.py` (private append-only ledger), `memelab/social/outcomes_cli.py` (`social evaluate ...`). Tests: `tests/test_social_outcomes.py`. Fixture: `tests/fixtures/social/outcomes/` (`make_outcomes.py` builds `outcomes_fixture.json`; `sample_run.md` is the demo output, checked byte for byte). Decisions: D-105 to D-111.

## What it does

When the lab emits a research signal (a feed item, a research candidate, an alert, or one that was rejected or suppressed), the ledger records what the lab knew at that moment. Later, outcomes at 1h, 6h, 24h, 72h and 7d are measured from dated price observations and appended. The original record is never rewritten.

Nothing here trades, sizes a position or changes a score, status, rank or watchlist (`trade_execution_impact: none`). The 500 USD position size is a hypothetical evaluation size used to model price impact, not a recommendation.

## The signal record (`memelab.social.signal/1`)

- signal_id (hash of emitter, emitter ref, chain, contract and generated time), emitter and emitter ref, disposition (EMITTED, REJECTED, SUPPRESSED, NEEDS_REVIEW) with its reason.
- versions: classifier, scoring, policy, ledger engine.
- references: claim ids, source ids, narrative run, chronology runs, market fact ids, cluster key or research provenance.
- token: exact chain and contract (the symbol is kept for display only).
- times: event time, generated time, captured time, publication delay.
- market at generation: observed price (provider, as_of, age, stale flag), reported liquidity, sell route quote (OK with proceeds, or NO_ROUTE), and how many market facts were dropped because they were dated after generation.
- assumptions: direction, horizons, execution lag (300 s), hypothetical size (500 USD), fees (100 bps per side), slippage (50 bps per side), max participation (5%), policy version and hash.
- missing: every field that was not known, with the reason. flags: LATE_CAPTURE (recorded more than 1 h after generation), EVENT_AFTER_GENERATION.

Re-recording the same signal is a no-op. Recording the same signal id with a different context is refused.

## Ledger

One journal table, `ledger_entries`, in `data/private/signal_ledger.sqlite` (gitignored; `MEMELAB_SIGNAL_LEDGER` overrides; the tracked database is refused). Entry kinds: SIGNAL, OBSERVATION, ANNOTATION, OUTCOME, in the order recorded. SQLite triggers refuse UPDATE and DELETE. Each entry stores the sha256 of its body and of the previous entry, so `social evaluate verify` can recompute the chain. A revised provider snapshot is a new observation of the same series with a later `available_at`. A matured or changed outcome is a new outcome entry with `supersedes_seq` and a `revision_reason` (MATURED, STATUS_CHANGED, INPUTS_REVISED). The earlier entry stays.

## Outcome rules

- Entry time is generated time plus the execution lag, never the earlier event time. Exit time is entry time plus the horizon.
- Only observations the lab had at the evaluation time count (`available_at <= as_of`). An observation dated after it became available is refused, and so is a candle that had not closed.
- Entry and exit prices are the first dated midpoint at or after the target time, within 15 minutes. A candle gives its open at its start and its close at its end, so no price from before the target is used.
- No midpoint, no return. A route quote is not a midpoint and never stands in for one (MISSING_MIDPOINT_AT_ENTRY or MISSING_MIDPOINT_AT_EXIT, NO_ENTRY_PRICE, NO_EXIT_PRICE). While the exit window is still open the outcome stays PENDING (EXIT_WINDOW_OPEN).
- Three returns are kept apart: `return_mid_gross` (displayed price move, not proceeds), `return_net_modeled` (fees, slippage and constant-product impact `2 x size / liquidity` at the hypothetical size) and `return_net_quoted` (exit from an actual sell route quote within 120 s of the exit price). The entry cost basis is stated (ROUTE_QUOTE or MODELED_IMPACT).
- Max favourable and adverse excursion only when no gap in the path is wider than horizon / 12; otherwise INSUFFICIENT_PATH.
- Statuses: PENDING (HORIZON_NOT_MATURED, EXIT_WINDOW_OPEN), MEASURED, MISSING (UNRESOLVED_IDENTITY, no price, no midpoint), NON_EXECUTABLE (TOKEN_DELISTED_BEFORE_EXIT, DELISTED_BEFORE_ENTRY, ILLIQUID_ENTRY, EXIT_LIQUIDITY_LOST, NO_SELL_ROUTE, NO_BUY_ROUTE, PRICE_QUOTE_MISMATCH when the quote returns less than 75% of the displayed value, SHORT_NOT_EXECUTABLE_ON_SPOT), INVALIDATED (INVALIDATED or IDENTITY_REVISED annotation, EVENT_AFTER_GENERATION).
- A delisted token gets no exit price. The last observed price and time are shown and no return is computed. Prices after a delisting are ignored.
- A quote that pays more than the displayed price by over 2% is flagged PRICE_QUOTE_MISMATCH and ignored.
- A deleted source is an annotation: the signal and its outcomes stay and carry a SOURCE_DELETED flag.

## Commands

```
social evaluate record   (--signals FILE | --feed-json FILE | --research-json FILE) [--generated-at T] [--now T] [--ledger PATH] [--fixture]
social evaluate observe  (--prices FILE | --from-db PATH) [--now T] [--ledger PATH]
social evaluate run      [--as-of T] [--now T] [--ledger PATH] [--json]
social evaluate annotate --signal ID --kind SOURCE_DELETED|INVALIDATED|IDENTITY_REVISED|NOTE --reason TEXT [--at T] [--now T]
social evaluate show     --signal ID [--as-of T]
social evaluate report   [--json]
social evaluate verify
social evaluate demo     --fixture FILE [--out FILE]
```

`run` is safe to repeat and to resume: work goes in signal order and horizon order, every append is its own transaction, an unchanged outcome is not appended again, and the evaluation time may not move backwards (`show --as-of` replays an earlier time without writing). `--as-of` later than `--now` is refused. `observe --from-db` reads `social_market_facts` (price points, candles, liquidity, sell quotes) from a lab database.

## Coverage report

Per horizon: signals, pending, measured, missing, non-executable, invalidated, not evaluated, and coverage = measured / matured. Reasons for exclusion are counted per status. Every disposition is shown, so rejected and suppressed signals are visible next to emitted ones. A median of `return_net_modeled` is printed only over 5 or more MEASURED outcomes and is labelled descriptive, never a score.

## Proof

`python -m memelab social evaluate demo --fixture tests/fixtures/social/outcomes/outcomes_fixture.json` reproduces `sample_run.md`: five invented signals (emitted, rejected, suppressed, a theme without identity), evaluation 1 at 2026-10-13T19:00Z, evaluation 2 at 2026-10-14T14:00Z with a revised provider snapshot in between, a repeated evaluation that appends nothing, the GOODCAT context body before and after with the same sha256, "Original context unchanged, byte for byte, for all 5 signals: yes", an UPDATE refused by the ledger, and a verified hash chain.

## Test list (prompt items)

| Prompt item | Test |
|---|---|
| look-ahead protection | `test_lookahead_context_drops_later_facts_and_entry_is_never_before_the_signal`, `test_evaluation_clock_cannot_run_ahead_or_backwards`, `test_observation_validation`, `test_candles_give_open_at_start_and_close_at_end` |
| revising underlying provider snapshots | `test_revised_provider_snapshot_appends_a_revision_and_keeps_the_original` |
| delayed publication | `test_delayed_publication_is_measured_from_the_signal_not_the_event`, `test_late_capture_is_flagged_and_capture_before_generation_is_refused` |
| delisted tokens | `test_delisted_token_is_non_executable_and_no_exit_is_invented` |
| lost liquidity | `test_lost_liquidity_and_missing_sell_route_are_non_executable` |
| missing midpoints | `test_missing_midpoint_is_missing_and_a_route_quote_never_stands_in` |
| duplicate evaluation | `test_duplicate_evaluation_appends_nothing` |
| source deletion | `test_source_deletion_keeps_the_signal_and_its_outcomes` |
| postponed windows | `test_postponed_windows_pending_then_missing_and_a_late_run_uses_the_target_time_price` |
| price-quote mismatch | `test_price_quote_mismatch`, `test_route_quote_and_modeled_impact_are_kept_apart` |
| no outcomes matured | `test_no_outcomes_matured` |
| deterministic resumption | `test_deterministic_resumption_after_a_crash` |
| no cherry-picking | `test_rejected_and_suppressed_signals_are_kept_and_a_changed_context_is_refused` |
| immutable original context | `test_fixture_signal_snapshot_before_and_after_two_evaluations`, `test_ledger_is_append_only_and_verify_detects_tampering`, `test_fixture_is_reproducible_and_sample_matches_byte_for_byte` |

## Known limits

- Nothing records signals automatically yet. The feed, research and alert commands do not call the ledger; `social evaluate record` is run on their JSON output. Wiring it into scheduled runs belongs to Phase 19/20 and is Elving's call.
- No live price source was used. The tracked database has no social tables, so `observe --from-db data/memelab.sqlite` appends 0 observations today.
- The quoted net return uses a quote at the quoted size, which may differ from the position value (flagged QUOTE_SIZE_DIFFERS above 25%).
- Short signals are information only. Trader scoring on top of the ledger is carry-over C-16.
