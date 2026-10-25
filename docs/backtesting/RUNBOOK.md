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
| pool reserves and sell quotes for the lab's decisions of the last 24 h (network, read-only) | `python -m memelab backtest depth collect --repo LAB_GIT [--ref refs/remotes/origin/main] [--max-gt-calls 6] [--max-quote-calls 48] [--deadline 115] [--gt-prior-calls N --gt-prior-end UTC_EPOCH]` |
| what the depth collector holds per decision (pool lookups, lag to the first snapshot, grid hours covered) | `python -m memelab backtest depth status [--hours 48]` |

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
- Hourly tracking (approved by Elving on 2026-10-24, D-BT-033) runs on his computer against the store in D:\memelab\backtesting_live: bt.sqlite, raw/, runs/, code.bundle (the branch the runs use), hourly_shadow.sh (a copy of audits/backtesting/release/hourly_shadow.sh), hourly.log and hourly.state.
  - One run is five steps, each one call of the script: setup (Python 3.13 venv, code from code.bundle, a session-local copy of the database), refresh (`backtest refresh` with at most 12 GeckoTerminal calls, 3 s apart), collect (`backtest depth collect`, see "Forward depth collection" below), track (`backtest outcomes track --min-interval 1800`), save (WAL-safe backup, integrity check, write back, one JSON line in hourly.log that now includes the collect summary).
  - Work happens on a copy, so a failed or interrupted run never touches the stored database. A second run within 45 minutes of an unfinished one is skipped.
  - A test run on 2026-10-24 took about 2.5 minutes: refresh 20 calls in 155 s (hence the 12-call cap), track 16 s, save 25 s. It recorded 4,092 outcome rows and resolved 14 waiting windows.
  - The scheduled task itself was not created yet: the permission check in that session refused it. Its prompt is in "Scheduled task prompt" below. When a run cannot reach the computer it does nothing, and the next run catches up.
  - To update the code the runs use, replace code.bundle with a newer bundle of feature/backtesting. To stop, pause or delete the scheduled task.
- Deviations open a REEVALUATION_PROPOSED record. A new evaluation needs a new pre-registration, a new sealed split that starts after 2026-10-23 16:00 UTC, and a new strategy version. In-place retuning is refused.

## Forward depth collection

Approved by Elving on 2026-10-25 (predictive PI-D-020, now PI-D-044; D-BT-034, repaired after an independent review in D-BT-035), folded into the hourly tracker as the step `collect`, between refresh and track. It records what the exit-adjusted and liquidity-degradation targets need and nothing kept so far gives: pool reserves and executable sell quotes for every lab decision, every hour from the first run after the decision to 24 h.

- Which decisions: every thesis row first visible in an export of `data/state/latest.json` on `main` whose commit is at most 24 h old and not in the future. The step fetches the last 72 h of `main` from the public repository (shallow git fetch, about 7 MB, no credentials). The oldest export read is the baseline: its rows are never new. The decision time is the export commit time (PI-D-015); the identity is chain plus exact mint plus the exact row (sha256 of the row without `id`, PI-D-021). A row that cannot be read is counted (`rows_unreadable`) and skipped. Every decision is recorded at first sight, with or without a pool.
- Which pool: the token row of that export (`primary_pool`, else `graduated_pool`). When the export names none (NONE_IN_EXPORT), the vendor's top pool from GeckoTerminal's token endpoint (`include=top_pools`); every lookup is a row in `bt_depth_pool_lookups` with its state (OK, NO_POOL, HTTP_429 and so on), attempt number, URL and body hash, and it is retried each run until one is OK. The first OK lookup fixes the pool (VENDOR_TOP_POOL). A pool that does not hold the mint is recorded as IDENTITY_MISMATCH.
- When: these are observations made after the decision, not at it. The lab exports once a day (about 10:10 UTC), so the first snapshot comes at the first hourly run after the export, up to about an hour later, then each hour until 25 h after the export commit. Every row stores `since_export_s`.
- Each run:
  - pool read: GeckoTerminal `networks/{network}/pools/multi/{up to 30 pools}?include=base_token,quote_token&include_composition=true`; reserves in token units and in USD, the mint's side and USD price, decimals, 1 h and 24 h volume;
  - sell quotes (Solana only): Jupiter `https://api.jup.ag/swap/v1/quote`, keyless, selling the mint for USDC at 100, 500 and 2,000 USD. The token amount is the size divided by the mint's USD price from the pool read made earlier in the same run, rounded down to the mint's decimals; the price, its field, its pool, its read time and its body hash are stored with the quote. When the quote's implied price (proceeds before Jupiter's stated price impact, per token sold) is not within 10% of the pool price used, the quote is PRICE_DISAGREES, not OK: the pool's price and the market disagree, and the proceeds must not be read as an exit cost. Jupiter's swapUsdValue is stored but not used for this check: it values the output, so it falls with real price impact too. BSC, Base and Ethereum pools get a QUOTE_UNSUPPORTED_CHAIN row (no free quote source here);
  - every row keeps captured_at (UTC epoch seconds when the response arrived), the request URL, the HTTP status, the sha256 of the raw body (kept under raw/geckoterminal/ or raw/jupiter/) and, after a retry, every attempt.
  - Anything not read gets a row that says why: NOT_ATTEMPTED_CAP, NOT_ATTEMPTED_DEADLINE, and for quotes of a pool whose read failed SKIPPED_POOL_<state>.
- Pacing and budget, enforced in code: GeckoTerminal at most 6 calls a run, at least 10 s apart, and no call while the last 60 s hold 6 or more GeckoTerminal calls, counting the refresh step's calls (the script passes their count and the time refresh.json was written; they are all counted at that time, which is no earlier than any of them). Refresh's own calls are unchanged (up to 12, 3 s apart): the 6-in-60-s rule holds for every window that contains a collect call, not inside refresh's own burst. Jupiter at most 48 calls, 2.2 s apart (27 a minute; keyless allows 30). One call per read plus at most one retry after 5 s on a 429, a 5xx or no answer, skipped when the cap or the deadline would be passed; a failed read never stops the step. No call or retry starts after 115 s; each call has a 10 s timeout.
- Quote order: pools with the fewest runs with an answered quote (any state, so a pool without a route does not keep the front) since their decision first, then the one answered longest ago, then a hash of the run and the pool. Pools skipped in one hour go first in the next.
- Step time: the git fetch is stopped at 20 s and the program at 140 s, so the step ends within about 165 s, under the 175 s call. Simulated with today's export size (16 Solana, 2 BSC, 1 Base pools): with no refresh calls before it, 48 quotes and all 16 pools in about 104 s; after a refresh of 12 calls, the first pool read waits for the window and about 27 quotes fit (9 of 16 pools), the rest NOT_ATTEMPTED_DEADLINE, and the 7 pools skipped go first the next hour. A live full-size run from the cloud workspace on 2026-10-25 (no refresh calls before it) made 6 GeckoTerminal and 40 Jupiter calls in 115 s of calls: 18 of 19 pool reads OK (one 429 kept after its retry), 40 quotes, 8 NOT_ATTEMPTED_DEADLINE.
- Per hour, with refresh: GeckoTerminal at most 18 calls (12 refresh, 6 collect), Jupiter at most 48, GitHub one shallow fetch.
- One run per UTC hour: a second run in the same hour prints SKIPPED_SAME_HOUR and makes no call.
- Failures: if the GitHub fetch fails, the step prints EXPORTS_NOT_FETCHED and still collects for the decisions already stored. If every quote is refused (401, 403, 429 or no answer), the run reports `quote_source` QUOTE_SOURCE_BLOCKED and still records the pool reads. Only a program error makes the step print FAILED; the run then stops before save, so the stored database is untouched.
- For the predictive adapter (PI-D-044): quotes and reserves are post-decision observations; use `since_export_s`, never treat the first snapshot as "at the decision". Use only state OK quotes; PRICE_DISAGREES, IDENTITY_MISMATCH and the skip states are not proceeds. In the live run of 2026-10-25 14:13Z three of 37 answered quotes were PRICE_DISAGREES, all for one mint whose vendor top pool showed a stale price (implied over pool price 0.26). Sales are sized in USD at each run's price, not as the token quantity held since the decision, so a held position's proceeds need interpolation between the three sizes. One run per hour, so one row per pool, kind and size per hour.
- Data: three append-only tables added by schema migration 2 (`bt_depth_decisions`, `bt_depth_pool_lookups`, `bt_depth_snapshots`); the v1 tables are unchanged. The first collect on the work copy applies the migration; save writes it back. Code without migration 2 ignores the new tables.
- Rollback: restore the previous hourly_shadow.sh and code.bundle (see deployment step 3). The new tables can stay. To drop them, with no run in progress and after a backup: `python -c "from memelab.backtest import schema, store; schema.rollback(store.connect('PATH/bt.sqlite'), 1)"`, run with the code of this commit or later.
- Evidence: audits/backtesting/collector/ (COLLECTOR.md with the repair record, COLLECTOR_SKEPTIC.md, smoke results, the full-size live run of the repair pass in live_repair_run/, raw bodies, SKEPTIC_PACKET.md) and audits/backtesting/testing/logs/c01_*.log and c01r_*.log.

### Deployment to Elving's computer

These steps need a session linked to his computer (device_bash). Nothing here was run on his computer yet.

1. Make the new code bundle. The collector commits are on the local branch `work/backtesting-collector`, based on feature/backtesting at 054a619; they are not pushed. Once they are on feature/backtesting (a fast-forward), in a clone of the repository:
   `git bundle create code.bundle feature/backtesting` then `git bundle verify code.bundle`.
   The setup step clones the branch named feature/backtesting from the bundle, so the bundle must carry that branch name.
2. Check that no run is in progress: `bash $HOME/mnt/memelab/backtesting_live/hourly_shadow.sh status` must show `idle`. If the scheduled task exists, pause it first.
3. Keep the old files, then put the new ones in place (in D:\memelab\backtesting_live):
   `cd $HOME/mnt/memelab/backtesting_live && cp bt.sqlite bt.sqlite.before-collector && cp code.bundle code.bundle.before-collector && cp hourly_shadow.sh hourly_shadow.sh.before-collector`
   then copy the new code.bundle and the new hourly_shadow.sh (audits/backtesting/release/hourly_shadow.sh at the deployed commit) over the old ones.
4. One run by hand, each command as its own device_bash call with timeout_ms 175000: `bash $HOME/mnt/memelab/backtesting_live/hourly_shadow.sh setup`, then `refresh`, `collect`, `track`, `save`. Check: setup prints the new commit; collect prints a JSON summary with `pool_snapshots` mostly OK and `quote_source` OK, and `wall_s` under 130; save prints one line with result OK and a `collect` part. EXPORTS_NOT_FETCHED is not a failure, but repeated ones mean GitHub is not reachable from his computer.
5. Create the scheduled task, or update the existing one, with the prompt below: name "Memelab backtest hourly tracking", every hour, requires Elving's computer with D:\memelab connected, push notifications on. Then resume it if it was paused.
6. To go back: pause the task, copy the three .before-collector files back over bt.sqlite, code.bundle and hourly_shadow.sh, and put back the four-step prompt (git history of HANDOFF.md at 054a619). Restoring bt.sqlite discards what was recorded after step 3; skip that copy to keep it (the old code ignores the new tables).

### Scheduled task prompt

This text replaces the four-step prompt that was in HANDOFF.md. Every rule of that prompt is kept; the only change is the collect step between refresh and track.

> Hourly shadow tracking for the Memecoin Investing Lab backtesting module (approved by Elving on 2026-10-24, D-BT-033; forward depth collection approved on 2026-10-25, D-BT-034). Research only. Use the device_bash tool on Elving's computer (mcp__remote-devices__device_bash; load it with ToolSearch if deferred). Run these five commands in order, each as its own device_bash call with timeout_ms 175000: `bash $HOME/mnt/memelab/backtesting_live/hourly_shadow.sh setup`, then the same with `refresh`, then `collect`, then `track`, then `save`. If setup prints a line starting with SKIPPED, stop quietly. If any step prints FAILED or exits non-zero, stop, do not retry or repair, and send one push notification naming the step and the FAILED line. If the computer cannot be reached, stop quietly. A successful run sends no notification. Never trade or touch a wallet, seed phrase or private key; never open or print any file in D:\memelab whose name contains "token"; never edit anything in D:\memelab\backtesting_live by hand; make no network calls of your own; never create, change or delete scheduled tasks; never push to GitHub. Final reply: one line with the save output or the reason the run stopped.

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
- Jupiter quotes are keyless on `api.jup.ag` at 0.5 requests a second (its plans page, read 2026-10-25: "great for AI agent or test use cases"). `lite-api.jup.ag` is being retired with a shrinking rate limit; the collector does not use it. No API key is used or stored.
- Firecrawl: paid per call, owned by Elving. About 32 of the roughly 100 calls approved for this work were used.
- Maxun Cloud: no credits left, no schedule, nothing running.
- Storage: the research database is about 155 MB for 139,168 hourly bars over 258 mints. It grows with each corpus refresh.

## Migration recovery

The bt schema is versioned in `bt_schema_migrations` with checksums. A changed migration script is refused; add a new migration instead. On a fresh database, concurrent first use is safe: the write lock is taken first, with a bounded retry. Recovery is to restore the backed-up file, or to move the bad file aside and start empty. Stored runs record the code and dataset hashes they used.
