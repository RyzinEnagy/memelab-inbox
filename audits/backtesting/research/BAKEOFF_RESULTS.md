# Bake-off results (Phase 04)

Folder: `audits/backtesting/bakeoff/`. Canonical dataset `dataset.json` (sha256 f287bf0f...; synthetic, labeled SYNTHETIC_BAKEOFF_V1). Independent hand oracle `oracle_hand.py` -> `oracle_expected.json` (shares no code with any engine). Comparison `compare.py` -> `compare_output.txt`: 16 of 16 checks pass, exit 0.

## Scenarios (same data, same definitions for every engine)

1. Tiny deterministic strategy: breakout when a bar closes above the prior 20 closed bars' high; stop 10% below entry; signal bar 20.
2. Stop gap: bar 35 opens at 0.95, below the 0.999 stop (gap through).
3. Event after known-at: published 05:30, first seen by the collector 07:10; hold 6 bars.
4. Two trade sizes: $1,000 and $50,000 against a CPMM pool with $60,000 quote reserve and 0.25% fee per swap, $0.01 network fee per transaction.

## Results

| Check | Custom prototype | backtesting.py 0.6.6 | vectorbt 1.2.0 default | vectorbt adjusted (shift, price=open) | Oracle |
|---|---|---|---|---|---|
| Breakout entry | bar 21 open 1.11 | bar 21 open 1.11 | bar 20 close 1.10 (signal bar: optimistic) | bar 21 open 1.11 | bar 21 open 1.11 |
| Gap stop exit | bar 35 open 0.95 | bar 35 open 0.95 | bar 35 close 0.93 (no OHLC given) | bar 35 open 0.95 | bar 35 open 0.95 |
| P&L $1k flat fee | -148.418074 | -148.3047 (898 integer units; reconciles exactly by formula) | -158.76 | -148.412752 (fee added to entry price; reconciles exactly) | -148.418074 |
| Event entry (first_seen_at) | bar 8 | bar 8 (signal placed on bar containing first_seen) | n/a | n/a | bar 8 |
| Published-time join (leak control) | bar 6 (detected as 2 bars early) | would equally leak if the user aligns to published time | n/a | n/a | bar 6 is wrong |
| CPMM $1k | proceeds 826.112457, ret -17.39% | not supported | not supported | not supported | 826.112457 |
| CPMM $50k | proceeds 16,757.465459, ret -66.49% | not supported | not supported | not supported | 16,757.465459 |
| Speed, 200 tokens x 1,000 bars, stop-only breakout | 0.123 s, 1,395 trades | 3.879 s, 1,395 trades | | 6.68 s, 1,398 trades (3 extra: re-entry differences) | |

Paired validation (G29): the prototype and backtesting.py agree on every fill bar and price; their P&L differs only by unit rounding and fee basis, and both reconcile exactly to closed-form formulas in `compare.py`. vectorbt agrees once signals are shifted and fills priced at the open.

## Adapter to the real opportunity record

`adapter_proto.py` runs the unchanged `pipeline.analyze_token` on the committed inbox fixture (PAID, `persist=False`, `observed_at` = latest capture time of the merged bodies, not the wall clock) and builds the snapshot the engine needs: chain, mint, as_of, pools, fatal flags, score, status, and a present-tense sell curve from raw quote units (tokens in by decimals, SOL out by 1e9). Transfer fee taken from the mechanics output (`transfer_fee_bps` = 0 here) while `authorities.transfer_fee_bps` is None, confirming the C1 workaround. Proceeds per quoted dollar fall from 0.9996 at $500 to 0.8159 at $100k. Production scoring and stored snapshots untouched (persist=False).

## Dependency weight and install path

| Engine | Install on Python 3.13 | Footprint | Windows/Linux | License |
|---|---|---|---|---|
| Custom prototype | none (stdlib) | 0 MB | both | the lab's |
| backtesting.py | pip wheel OK | ~120 MB venv (numpy, pandas, bokeh) | both | AGPL-3.0 |
| vectorbt | pip wheel OK | ~835 MB venv (numba, plotly, ...) | both | Apache-2.0 + Commons Clause |
| nautilus_trader | wheel OK for 1.231.0; 2.0 rc separate | ~945 MB | both | LGPL-3.0 |
| jesse | fails on 3.13 (numpy 1.26 pin) | ~1 GB on 3.12 | Linux/macOS (CI excludes Windows 3.13) | MIT |
| trade-executor | fails (Python < 3.11 only) | 304 locked packages | | AGPL-3.0 |
