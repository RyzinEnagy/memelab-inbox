# Backtesting and stress module: operator runbook

Research only. Nothing here places, sizes or suggests an order, and nothing touches a wallet. Every command runs from the repository root.

## What runs where

| Piece | Storage | Default |
|---|---|---|
| research database | `data/backtest/bt.sqlite` (gitignored, append-only bt_* tables; override with `MEMELAB_BT_DB`) | created on first use |
| raw provider responses | `data/backtest/raw/` (override with `MEMELAB_BT_RAW`) | written by fetches only |
| stored runs | `data/backtest/runs/<run_id>/` | written by `backtest run` |
| policy | `data/backtest/policy.json` or `MEMELAB_BACKTEST=1` | off |
| lab database | `data/memelab.sqlite` | never written by this module |

All times are UTC epoch seconds inside the module, and every report prints UTC. The social alert layer keeps its own America/New_York day boundaries.

## Turn on, turn off, crisis shutdown

- On: set `MEMELAB_BACKTEST=1` or write `{"enabled": true}` to `data/backtest/policy.json`.
- Off, including a crisis shutdown of the stress module only: unset `MEMELAB_BACKTEST` or set it to 0, and set `"enabled": false` in the policy file.
  - Scout, analyze and social alerts then behave exactly as without the module: the hook returns before opening any database.
  - Existing research keeps running.
  - No data is deleted.
- The switch covers the hook in scout and analyze and the alert label line. Commands run by name still work when the policy is off, because asking for them is explicit: `backtest stress`, `backtest run`, `backtest refresh` and the `backtest outcomes` actions. To stop them, do not run them, and remove any scheduled task that calls them.
- If the research database itself is suspect:
  1. Stop every process that writes to it (scout or analyze with the module on, `backtest` commands, scheduled tasks).
  2. Take a consistent copy first: `python -m memelab backtest backup --to data/backtest/bt.backup.sqlite`. The database runs in WAL mode, so recent commits can sit in `bt.sqlite-wal`; the backup command includes them.
  3. Then move `bt.sqlite`, `bt.sqlite-wal` and `bt.sqlite-shm` aside together. The next use starts an empty database.
  Never delete the database: it is the record of what was known when.
- Schema rollback (bt tables only, destroys bt rows; take a backup first): `python -c "from memelab.backtest import schema, store; schema.rollback(store.connect(), 0)"`. The lab database is untouched. Phase 17 tested a rollback followed by a re-apply in a clean clone.

## Policy settings (scenario config)

`data/backtest/policy.json`, any subset of:

| Key | Default | Meaning |
|---|---|---|
| enabled | false | the hook runs in scout and analyze |
| sizes_usd | [250, 1000, 5000] | position sizes stressed |
| max_loss_usd | 250 | loss cap for the size search |
| max_exit_impact | 0.05 | exit impact cap for the size search |
| deep_stage | "queue" | queue the DEEP stage for `backtest deep` |
| ta_strategies | 4 TA strategies | token signal states shown |
| min_cohort_trades | 30 | minimum measured windows before cohort percentiles appear |
| provider_lag_s | 300 | modeled publication lag of a closed bar |

A changed policy is a new request key: earlier assessments stay as they were.

## Daily use

| Task | Command |
|---|---|
| what the database holds | `python -m memelab backtest status` and `python -m memelab backtest data` |
| report for one mint from saved results | `python -m memelab backtest stress MINT --results ID ... [--position-usd 250 1000] [--now UTC] [--json]` |
| newest stored report for a mint | `python -m memelab backtest assess MINT [--json]` |
| queued DEEP assessments | `python -m memelab backtest deep --limit 20` |
| counts and wall time | `python -m memelab backtest assess-stats` |
| JSON Schema of the report | `python -m memelab backtest schema` |
| consistent backup of the research database | `python -m memelab backtest backup --to PATH` |
| new bars for windows waiting on a refresh (network, read-only) | `python -m memelab backtest refresh [--mints ...] [--max-calls 20] [--spacing 3]` |

## Manual replays

- Strategy replay with a cutoff: `python -m memelab backtest run --strategy ID [--params JSON] --as-of 2026-10-20T00:00:00Z [--decide-from UTC --decide-until UTC] --label NAME`.
  - Nothing after the as-of is read.
  - The same code (the same commit) and data give the same run id, and the second call is a cache HIT. The ledger hash depends only on the data, the config and the engine version, so it also reproduces across commits.
  - Changed code or data give a new id; old runs are never overwritten.
  - Run files go next to the database used: `data/backtest/runs/`, or `runs/` beside a `--db` copy.
- Inspect and reproduce a stored run: `python -m memelab backtest inspect RUN_ID`. It prints the config, the code, dataset, result and ledger hashes, the stored files, and the exact command that reproduces the run. The result hash includes the run's creation time, so it never reproduces; compare ledger hashes.
- Replay an assessment at its own time: `backtest stress ... --now UTC`. The cohort evidence only uses what the lab had recorded and published by then.

## Backfills

- Routine refresh for outcome tracking: `python -m memelab backtest refresh --max-calls 20`. It fetches new hourly bars for the basis pools of windows that wait on a refresh, records the fetch time even when nothing new traded, and stays inside the call budget.
  - It only covers tokens already in the corpus. A mint given with `--mints` that has no stored pool gets no request. There is no command yet that imports new lab records or finds pools for new mints; that takes the Python steps in the Phase 06 runners named below. A new sealed test after 2026-10-23 16:00 UTC needs those steps first.
  - Run it at least every few weeks. A fetch records only the newest bar it saw, so a refresh made long after a window (a fetch returns at most 1,000 hourly bars, about six weeks on a pool that trades every hour) may not reach back into that window and can read it as "no trades".
- Corpus fetches go through `memelab/backtest/sources/corpus.py` and `gecko.py`. Each fetch has a call budget, at least 3 s between calls, exponential backoff on 429 and 5xx, and raw responses saved by hash. The Phase 06 runners `audits/backtesting/data/run_corpus2.py` and `run_corpus3.py` are records of how the corpus was built. They hard-code that session's paths: adapt the paths before reusing them.
  - GeckoTerminal answered 429 at 2.2 s pacing in Phase 01. Keep the spacing at 3 s or more.
  - A mint counts as done only after its bar fetches complete (`CORPUS_MINT_DONE`), so an interrupted run resumes cleanly.
- A backfilled bar is available at its close plus the modeled lag. A later different version is a revision, available only from its own fetch time, so an earlier decision never sees it.
- Two corrupted mint strings exist in the lab's exports (GAPS C4). They are reported, never merged by similarity.

## Shadow-mode calibration (continue this)

- `python -m memelab backtest outcomes track` records outcomes at 1, 6, 24 and 72 h for every frozen lab opportunity and every stored assessment.
  - It runs at most once per hour (`--min-interval`) and skips when another writer is busy.
  - It never fetches. A window whose pool was last fetched before the window closed stays PENDING (NOT_FETCHED_SINCE_WINDOW_END) until `backtest refresh` brings bars or shows nothing traded. A stale pass never turns missing data into "cut short" or "dead".
  - Unchanged results add no rows.
  - A provider revision adds a row that supersedes the old one.
- `outcomes calibrate [--horizon-h 24] [--with-launches]` gives segments with counts, censoring and a selection-bias flag. A segment with fewer than 30 complete windows is INSUFFICIENT_SAMPLE.
- `outcomes drift` checks provider coverage, stale pending windows, calibration shifts, provider revisions and collector health.
- `outcomes daily --day YYYY-MM-DD --asof UTC` produces a replayable daily report, byte-identical for the same as-of.
- `outcomes shadow --strategy ID --since 2026-10-23T16:00:00Z` runs a frozen strategy forward without saving a run.
- No scheduled task was created. To run tracking every hour, Elving has to approve a scheduled task that runs `backtest refresh` and then `backtest outcomes track`, within the GeckoTerminal budget above.
- Deviations open a REEVALUATION_PROPOSED record. A new evaluation needs a new pre-registration, a new sealed split that starts after 2026-10-23 16:00 UTC, and a new strategy version. In-place retuning is refused.

## Reading the output

- The lab's score and status stay as computed and describe the project. The backtest label describes the entry: execution under stress, plus what history exists.
- Labels, first match wins:
  1. FATAL FLAW: the lab's veto stands.
  2. UNTESTED: missing, stale, blocked, failed or invalid.
  3. BAD EXECUTION.
  4. INCONCLUSIVE: the usual case today.
  5. TESTED: cohort or token evidence plus a feasible exit; still research only.
- HIGH_STATUS_MISMATCH means the lab says NEAR ENTRY or ENTRY CONDITIONS MET while the entry reads badly. A good project is not a good entry.
- Strategy confidence comes from whole-universe history. Every strategy is INSUFFICIENT_SAMPLE on the sealed test, and every rankable strategy loses money after modeled costs. Token opportunity comes from this token's own stress, quote and signals. Neither one predicts the next move.
- Stress scenarios are hypothetical with no probabilities. The cohort percentiles are empirical frequencies for past tokens with the same lab status. Windows that were cut short count at their last traded price. Read the selection-bias line.
- Evidence classes: FACT, INFERENCE, HEURISTIC and UNKNOWN are marked on every group of the JSON report.

## Quality statuses

| Where | Status | Meaning |
|---|---|---|
| bars | AVAIL_MODELED | first version, available at close plus the modeled 300 s lag |
| bars | BACKFILLED | fetched long after the close |
| bars | REVISION | a later, different version; available only from its own fetch time |
| bars | DUP_TS_IN_RESPONSE | the provider returned the same start twice |
| assessment state | COMPLETE, PARTIAL_WITH_LIMITATIONS, INSUFFICIENT_HISTORY, INSUFFICIENT_EXECUTION_DATA, UNSUPPORTED_POOL, STALE_DATA, INVALID_TOKEN_ID, RISK_FATAL_FLAW, SOURCE_BLOCKED, ERROR | see REPORTS.md |
| evidence tier | TOKEN_SPECIFIC, HISTORICAL_COHORT, SCENARIO_ONLY, UNAVAILABLE | what kind of evidence backs the assessment |
| execution basis | EXACT_CPMM, QUOTE_OBSERVED, LIQ_SNAPSHOT_APPROX, UNSUPPORTED_POOL | how a fill was priced |
| outcome window | COMPLETE, CENSORED, NOT_OBSERVABLE, PENDING | see OUTCOMES.md; PENDING includes NOT_FETCHED_SINCE_WINDOW_END |
| catalyst source | OK, DEGRADED, DOWN | collector health for a batch |
| validation verdict | INSUFFICIENT_SAMPLE and the others in validation.py | sealed-test result per strategy |

## Diagnostics and source outages

| Symptom | Meaning | Action |
|---|---|---|
| label UNTESTED, state SOURCE_BLOCKED | no price in the analysis bundle | re-run the scout when the price source answers; retriable |
| quotes show HTTP_429 | the Jupiter quote was rate limited | nothing is fabricated; execution falls back to the depth model with a note |
| STALE_DATA | the analysis is more than 2 h old | analyze again |
| INVALID_TOKEN_ID | the mint is not a 32-byte base58 key | fix the source record; permanent |
| assessment ERROR with "database is locked" | another writer held the research database for over 10 s | retriable; check for a stuck process |
| tracker SKIPPED_BUSY or SKIPPED_MIN_INTERVAL | another pass is running, or one ran within the interval | normal |
| cohort INSUFFICIENT_HISTORY with a selection-bias flag | too few measurable past tokens | expected with today's corpus |
| POOL_DISAGREEMENT windows | pools of one mint closed more than 30% apart for a lasting share of hours | not measured by design; see OUTCOMES.md |
| catalyst source DOWN or DEGRADED | the collector failed | no record and no signal are created; the next run retries |
| many outcome windows PENDING with NOT_FETCHED_SINCE_WINDOW_END | bars were not refreshed after those windows closed | run `backtest refresh`, then `outcomes track` |

Collectors: the existing lab catalyst layer (Firecrawl) and one-shot captures through `sources/webcapture.py` with allowlists and page caps. Maxun is NOT_ADOPTED. No schedule exists, and none may be created without Elving's approval. Credentials never enter this module's records, and status text is redacted.

## Costs and limits

- GeckoTerminal, DexScreener, Jupiter quote and Solana public RPC: free, read-only, rate limited. Keep budgets small and pacing slow.
- Firecrawl: paid per call, owned by Elving. About 32 of the roughly 100 calls approved for this work were used.
- Maxun Cloud: no credits left, no schedule, nothing running.
- Storage: the research database is about 155 MB for 139,168 hourly bars over 258 mints. It grows with each corpus refresh.

## Migration recovery

The bt schema is versioned in `bt_schema_migrations` with checksums. A changed migration script is refused; add a new migration instead. On a fresh database, concurrent first use is safe: the write lock is taken first, with a bounded retry. Recovery is to restore the backed-up file, or to move the bad file aside and start empty. Stored runs record the code and dataset hashes they used.
