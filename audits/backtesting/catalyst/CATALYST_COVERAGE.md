# Catalyst, wallet and social coverage (Phase 09)

What point-in-time catalyst evidence exists for historical study, measured 2026-10-23.

| Source | Rows | Known-at basis | Use |
|---|---|---|---|
| Lab launch monitor (`upcoming_launches` in every committed state export; `sources/lab_events.py`) | 65 records (45 pump.fun graduations, 11 live curves, 5 LaunchLab launches, 3 new pools, 1 curve market-cap); all chain-derived contracts | the lab's own `discovered_at` at first appearance; the git commit that first held the row is an upper bound (median 0.26 h later, max 0.34 h) | real historical catalyst records (CONTEMPORANEOUS_CAPTURE) |
| Lab catalyst tables (`catalyst_events`, items, links) | not present in the repository database (the lab writes them on the machine where it runs) | n/a | SOURCE_BLOCKED for history here; `sources/catalyst_bridge.py` reads them read-only when present (tested on a synthetic database) |
| Crawler captures (`bt_capture_provenance` via `sources/webcapture.py`) | 24 origins from the Phase 06A bake-off | our capture time | present-day only; old pages are UNKNOWN_AS_OF before capture |
| Lab `wallet_transactions` | 3,774 swap rows with block time and kind | block time is the event time; no capture time is stored, so availability is bounded only by the database commit | not used as a historical signal until a capture time exists; the strategy accepts only SWAP_SELL with an availability time |
| Lab `wallet_clusters`, `holders`, `token_authorities` | 172, 660, 33 | the lab's `observed_at` | through the thesis snapshots (cluster and insider shares, authorities) |
| Lab `social_snapshots` | 99 (holder-change metrics from Jupiter) | `observed_at` | not a catalyst |
| Narratives and narrative snapshots (state exports) | 170 narratives, 925 snapshots | `observed_at` | narrative-level only, never linked to a mint by name |

Timing fact from the launch records: the claimed event (first trade) came a median 0.57 h before the lab saw it, up to 53.5 h. A study that used the claimed time would trade before the lab could have known (G03); the records are usable only from `available_at`.

A real defect in the exports: the lab rewrote `discovered_at` for some launch rows in later exports (for example swordinu: 13:45Z in its first export, 15:41Z later). `lab_events` keeps the first committed value; a test and a mutation (M09-10) guard it.

## Event study (descriptive, `p09_event_study.py`, output `p09_event_study.json`)

19 launch events had bars on the pool the lab recorded at discovery. Entry is the open of the first bar after the lab saw the event (median wait 0.33 h). Placebo: the same tokens 12 to 72 hours later (seed 20261023).

| | n | Median return 24 h | Share positive 24 h | Median worst drop in 72 h |
|---|---|---|---|---|
| Launch events | 19 | -91.7% | 26% | -97.6% |
| Placebo times, same tokens | 18 | -1.8% | 33% | -13.4% |

15 of 19 events lost at least half their value within 72 hours of the lab seeing them. The placebo is not a clean control: by 12 to 72 hours later most of these tokens had already collapsed, so the placebo mostly measures dead tokens. The comparison says buying at detection was far worse than random later times on this sample; it does not show any edge.

## One failed and one non-failed catalyst, with archived evidence

- Failed: "D O T" `3GVSN8DLVvrxEafP7JQj6CwBFRxCq8vuUVmsRbCEpump`, pump.fun graduation, first seen by the lab 2026-10-09 11:57Z, archived in state export commit `2bd890dfb4` (committed 15 minutes later). Entry would have been 0.011315 USD at the 12:00Z bar; it fell 99.98% within 6 hours. The lab's status at the time was IGNORE; its later thesis REJECTED it at score 48.
- Non-failed: FEEBIE `2LMiWGyNjGKyUkH2oFYmMxzwLzUY84dHZf6DUUZFpump`, live pump.fun curve, first seen 2026-10-08 18:40Z, archived in commit `001b382854`. Entry 3.20e-05 USD at the 19:00Z bar; +106% at 24 h, +6.9% at 72 h, worst drop 5.6% in 72 h.

These are observations of what happened after the lab saw each event. Neither is a forecast and neither validates a strategy.
