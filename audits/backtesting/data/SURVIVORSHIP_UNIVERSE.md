# Frozen discovery universe and survivorship (Phase 06)

Universe id `lab_state_history`, built by `labstate.build_universe(con, repo, ref="origin/main")` from every git version of `data/state/latest.json` (95 versions).

## What is in it

| Chain | Theses (distinct mints) | Rejections (distinct mints) |
|---|---|---|
| solana | 201 | 462 |
| bsc | 28 | 22 |
| ethereum | 13 | 9 |
| base | 6 | 2 |
| evm-unknown | 0 | 146 |

2,901 universe rows in total (1,882 thesis rows, 1,019 rejection rows). Each row keeps the lab's own `created_at` as `entered_at`, and the git commit time of the first version that contained it as an upper bound on when the record existed. A token enters at its first lab record, never earlier.

## Selection logic, recorded

- All-eligible signals: every thesis and every rejection the lab ever exported, across all versions. Taking only the latest file would have dropped about 60% of theses (D-BT-010).
- The historical corpus (Phase 06) fetched all 201 Solana thesis mints plus a seeded random 60 of the 438 Solana mints that were only ever rejected (seed 20261023). The rejected sample exists so studies can compare what the lab passed with what it turned down.
- Nothing is selected by outcome. Dead, rugged and untraded tokens stay: 45 tokens had no bar in the last 3 days, one fell 99.99% in three days and is kept as a fixture, and the 4 mints with no bars at all (two of them corrupted copies of real mints, see DATA_COVERAGE) stay listed as INSUFFICIENT_HISTORY.
- `store.universe_asof(con, universe_id, t)` returns only members whose entry was knowable at t.

## Remaining survivorship risks

- The lab's own discovery is the filter. Tokens the scout never saw are absent, so results describe "tokens this lab discovered", not the market.
- GeckoTerminal may stop indexing dead pools or tokens. The HTTP 404s in this fetch turned out to be corrupted mint strings from the lab's exports, not delisted tokens, but a later re-fetch could lose pools that exist today; raw responses are kept for that reason.
- Social archives: no historical social capture exists before the lab's own collectors started. Crawls made now of old posts are UNKNOWN_AS_OF before their capture time.
- The universe covers 17 days. Any statistic from it is short-sample (Phase 11 reports INSUFFICIENT_SAMPLE where the count is below the pre-set minimum).
