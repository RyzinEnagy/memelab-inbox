# Phase 17: historical replay, baselines and statistical honesty

Prompt 17. Code: `memelab/social/replay_core.py` (pure engine), `memelab/social/replay_synth.py` (seeded synthetic world), `memelab/social/replay_sources.py` (read-only adapters for the lab database and collector files), `memelab/social/replay_cli.py` (`social replay ...`). Tests: `tests/test_social_replay.py` (22). Fixture: `tests/fixtures/social/replay/` (`synthetic_spec.json` is the default world spec, `sample_report.md` is the demo output, checked byte for byte). Decisions: D-112 to D-118.

## Result first

On the history the lab holds today, nothing can be validated. All four strategies are INSUFFICIENT_DATA:

- the tracked database has no social tables, so there are 0 posts and 0 wallet events: strategies (a), (b) and (c) have no signal to test;
- the collector files on `main` hold 410 trending-list entries from 19 lists, all collected between 2026-10-07T17:14Z and 2026-10-08T13:45Z, and 16,847 GeckoTerminal candles that end by 2026-10-08T14:01Z. Only 4 trending entries have even 1 h of later prices and none has 24 h, so (d) has 0 matured test outcomes;
- the universe is "tokens the lab's runs happened to fetch", with no delisted tokens tracked: survivorship bias cannot be ruled out, and 27 of 122 trending-listed tokens have no price history at all.

Command (collector files copied read-only from `origin/main:inbox/` into a scratch folder; nothing committed):

```
python -m memelab social replay inventory --db data/memelab.sqlite --inbox <copy of main:inbox>
python -m memelab social replay run --db data/memelab.sqlite --inbox <copy of main:inbox>
```

Both exit 0. The run prints "No leakage detected: yes" and INSUFFICIENT_DATA for each strategy. No 90-day backtest was fabricated. What would change this: the social collectors running (C-6, C-7) into a migrated database, the Phase 16 ledger recording signals as they are emitted, and price history kept for every signalled and control token, delisted ones included, for at least several weeks.

## What it does

A replay walks a cutoff clock forward over every moment new social, wallet or trending evidence became available. At each cutoff, four strategies decide from what was visible then:

- INDIVIDUAL (a): one original LONG post whose first observation came within `max_capture_lag_s` of publication.
- CONVERGENCE (b): original LONG posts from at least `min_sources` independence groups inside `window_s`.
- SOCIAL_WALLET (c): at least `min_sources` independent LONG posts in 24 h plus a BUY by a wallet with accepted linkage (SELF_CLAIMED, SIGNED_MESSAGE, CHAIN_EVIDENCE) inside `wallet_window_s`.
- TRENDING (d), the raw baseline: at least `min_mentions` raw mentions (reposts and duplicates counted) in 24 h, or a provider trending list entry at rank 10 or better.

Each signal is one research observation; nothing trades (`trade_execution_impact: none`). The same strategy configuration emits at most one signal per token in 72 h.

## The cutoff clock

Every record carries `_avail`, the earliest time it was demonstrably available:

- post: first observation by the lab (not the publication time; a post available before its publication time is refused as a clock error);
- wallet event, trending list: arrival time;
- candle: close plus the provider's documented publication lag, or the lab's capture time when given (real collector files use the capture time; a candle that was still open at capture is refused, and one dated after its capture time is refused);
- delisting: when it became known.

Strategies only see records through `CutoffView`. Its accessors slice by availability, and every returned record is checked again by `Audit`; a record from after the cutoff stops the run with `LeakageError`. Decision time is the availability of the newest input. Entry is decision time plus the Phase 16 execution lag (300 s); outcomes come from `outcomes_core.evaluate` (dated prices only, no invented exits).

## Splits, tuning and the label gate

- Chronological train / validation / test, 50 / 25 / 25 of the span from the first decision evidence to the end of the data.
- Label clocks: train outcomes as known at the train boundary, validation at the validation boundary, test at the data end.
- Embargo: a sample whose outcome window (lag + horizon + exit wait) crosses its split boundary is purged, never moved.
- Tuning: 16 configurations (3 + 6 + 4 + 3). For each strategy the configuration with the highest train median relative return (conservative lens) among those with at least 8 train values is chosen; with none eligible, the first (default) configuration is used and the report says it is untuned.
- `LabelGate` releases labels by phase: TUNE sees train only; validation labels need the VALIDATE phase; test labels need a frozen configuration (sha256 recorded). The order of operations is printed in the report.

## Matched controls

At the decision time, from what was visible then: same chain; a price no older than 2 h; no delisting known; not mentioned in a visible post in the last 7 days and not on a visible trending list in the last 24 h; reported liquidity within a factor 3 of the signal token's; market cap within a factor 4 when both are known. Up to 8 controls, nearest first. Controls share the decision time, so the calendar regime is matched by construction; results are also broken down by regime (ISO week, or supplied regime labels). Fewer than 3 measured controls: no relative return (NO_VALID_CONTROLS, SIGNAL_LIQUIDITY_UNKNOWN_AT_DECISION or TOO_FEW_MEASURED_CONTROLS), counted, never filled in.

## Statistics

Per strategy, split and horizon (1h, 6h, 24h primary, 72h):

- eligible signals, labeled, purged or pending, status counts, coverage (usable / labeled), executable share, delisted, non-executable, signals on tokens with no price history;
- relative return = signal net modeled return minus the median of its controls, in two lenses: conservative (headline; a long whose token was delisted before the exit is -100%, for signals and controls alike) and measured-only;
- median relative return with an order-statistic interval, precision (share beating controls) with a Wilson interval, both Bonferroni-adjusted for 4 strategies x 4 horizons; mean with and without the top outcome and the top outcome's share of gains (dominance flag above 50%); median net return, hit rate, MAE median and worst; distinct tokens and top-token share;
- nothing is estimated below 10 values ("not shown").

Verdicts on the test split at the primary horizon: INSUFFICIENT_DATA (no signal, no matured outcome, or coverage under 60%), INSUFFICIENT_SAMPLE (fewer than 30 test values with controls), CANNOT_VALIDATE_YET (survivorship risk, interval includes zero, a dominating outcome, or validation disagrees in sign or is too small), otherwise BETTER_THAN_CONTROLS_IN_REPLAY or WORSE_THAN_CONTROLS_IN_REPLAY. Even the last two are labelled a historical replay. The report separates signals whose inputs the lab captured at decision time ("inputs captured live") from reconstructed ones; outcome prices are provider history in every case, so no result here is a forward test. Forward results come from the Phase 16 ledger.

## Leakage proof

`leakage_check` reruns signal generation on the data as it existed at the train and validation boundaries (every record available later removed) and compares the signals decided by then, for all 16 configurations, and the train metrics used for tuning. Any difference means the harness read future evidence. The demo and every `social replay run` print the result (`--no-leakage-check` skips it; exit 1 when a difference is found).

Mutation check run in this phase: with the cutoff removed from one accessor (`_raw_posts_on` returning everything after the lower bound), `python -m pytest tests/test_social_replay.py -q` gave `9 failed, 13 passed` (LeakageError from the audit, the truncation check, the sample report); restored, `22 passed`.

## Synthetic fixture replay

`python -m memelab social replay demo` (about 35 s) builds the seeded world in `synthetic_spec.json` (30 days, 79 tokens, 15-minute candles, 14 sources in 10 independence groups, 150 planted pumps with informative posts, noise posts, reposts, ingest duplicates, 10 leakage canaries published before a pump but available after it, a 41x winner, delisted and illiquid tokens, revised candles, linked-wallet buys and sells) and prints `sample_report.md`, watermarked. Its verdicts: INDIVIDUAL, CONVERGENCE and SOCIAL_WALLET INSUFFICIENT_SAMPLE (tuning picked CONVERGENCE with 4 sources, best on train, which leaves 3 test values: the cost of choosing on train is visible), TRENDING CANNOT_VALIDATE_YET (interval includes zero). `test_harness_can_report_an_edge_when_one_exists` shows the harness does return BETTER_THAN_CONTROLS_IN_REPLAY when a clear edge exists.

## Test list (prompt cases)

| Prompt case | Test |
|---|---|
| future information injected into training | `test_future_information_injected_into_training_window_does_not_change_tuning`, `test_backdated_post_is_decided_when_it_became_available_not_when_published` |
| duplicated reposts | `test_duplicated_reposts_are_raw_mentions_not_independent_sources` |
| missing delisted-token prices | `test_missing_delisted_token_prices_are_a_total_loss_only_with_delisting_evidence` |
| huge win dominating results | `test_one_huge_win_is_flagged_and_does_not_carry_the_headline` |
| survivorship bias | `test_survivorship_bias_is_flagged_when_losers_are_missing` |
| provider publication lag | `test_provider_publication_lag_hides_a_candle_until_it_is_published` |
| no valid matched controls | `test_no_valid_matched_controls_gives_no_relative_return` |
| contradictory signals | `test_contradictory_signals_are_suppressed` |
| no tradable depth | `test_no_tradable_depth_is_non_executable_not_a_return` |
| insufficient sample | `test_insufficient_sample_is_said_plainly_and_nothing_is_estimated` |
| a test that fails if the harness accesses future evidence | `test_harness_that_reads_future_evidence_fails` (leaky view caught by the audit; with the audit removed, truncation invariance reports differences) |
| no tuning on held-out outcomes | `test_label_gate_refuses_held_out_labels_before_they_are_allowed`, `test_train_labels_use_the_train_clock_and_embargo_purges_overlap` |
| synthetic replay, no leakage, determinism | `test_synthetic_replay_is_deterministic_and_leak_free`, `test_sample_report_is_reproduced_by_the_demo_command` |
| real data honest result | `test_tracked_database_has_no_social_history_and_gives_insufficient_data`, `test_cli_inventory_and_run_on_the_tracked_database` |
| adapters | `test_inbox_adapter_reads_candles_and_trending_lists_without_inventing_chains`, `test_db_adapter_reads_social_calls_reposts_and_linked_wallets` |

## Known limits

- Controls exclude tokens mentioned up to the decision time only; a token mentioned later is still a valid control at that time (using later mentions would be look-ahead).
- Overlapping outcome windows across different tokens are not de-correlated; the 72 h cooldown limits overlap on one token only. Intervals are therefore optimistic when many signals cluster in time.
- The GeckoTerminal publication lag (300 s) is an assumption (HEURISTIC) and is only used with `--candle-availability provider`; the default uses capture times.
- Collector files record the plan time as `_at`; some 1-minute candles are dated after it and are refused as FUTURE_DATED_AT_CAPTURE (29 in the real run).
- No post text is read or stored anywhere in the replay.
