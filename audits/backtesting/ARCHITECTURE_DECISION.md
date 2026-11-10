# Architecture decision (Phase 01)

Status: ACCEPTED for Phases 02 to 17, amendable only by a recorded decision plus renewed tests.

## 1. Placement

A new package `memelab/backtest/` beside `catalyst/`, `chains/`, `launch/` and `social/`. It reads the lab's existing outputs and never changes how the scout scores or labels a token.

```
memelab/backtest/
  schema.py        additive migrations for bt_* tables (Phase 05)
  timeguard.py     clocks, as-of join, LeakageError, Audit, bar-close filter (Phase 05)
  store.py         append-only writes, content hashes, idempotent ingest (Phase 05)
  sources/         gecko.py (historical OHLCV, pools), labstate.py (lab history from git), dexscreener.py (pool type),
                   jupiter.py (present quotes), capture.py (crawler/robot captures), maxun.py (only if 06A adopts) (Phases 06, 06A)
  execution.py     CPMM exact math, fee stack, route aggregation, CLMM/DLMM refusal, liquidity-snapshot tier, capacity (Phase 07)
  strategies/      ta.py, catalyst.py, labstatus.py, baselines.py, registry.py (Phases 08, 09)
  engine.py        deterministic event replay, order lifecycle, portfolio ledger (Phase 10)
  validation.py    chronological splits, walk-forward, sealed test, bootstrap, multiple testing (Phase 11)
  stress.py        scenario engine, max size under loss/impact caps (Phase 12)
  assess.py        per-opportunity request, cache, tiers, abstention (Phase 13)
  report.py        Markdown and JSON sections (Phase 14)
  outcomes.py      outcome tracker, calibration, drift (Phase 15)
  cli.py           python -m memelab backtest {status, data, run, stress, assess, outcomes, inspect}
```

## 2. Integration seam (verified in code)

The strongest seam is the return value of `pipeline.analyze_token` (pipeline.py:116-185), consumed in `cli.cmd_scout` (:252) and `cli.cmd_analyze` (:195). That dict already holds the bundle (quotes, pools, authorities, OHLCV), module outputs (depth, mechanics, structure, entries, sizing, exits), score, fatal flags and status. The backtest hook is called after `analyze_token` returns and before the scout report is rendered:

```
cli.cmd_scout / cmd_analyze
  r = pipeline.analyze_token(...)                      unchanged
  if backtest policy enabled:                          off by default
      a = backtest.assess.attach(r, policy, as_of=r.bundle.observed_at)
          -> request key = sha256(mint, snapshot hash, engine version)   idempotent
          -> fast stage (sync, no network): current-quote execution, stress scenarios, cached cohort evidence
          -> deep stage (deferred): queued request row; `backtest assess --deep` runs it later with bounded fetches
      r["backtest"] = a
  report.render_scout_report(..., backtest=sections or None)   section omitted when None -> byte-identical report
```

Mirrors the social Phase 13 pattern (`social_section`, cli.py:226): opt-in policy, explicit no-op, report unchanged when off.

## 3. Sequence (one opportunity)

```
scout ─► analyze_token ─► result r (score, fatal flags, status, quotes, pools, mechanics)
   │
   └─► assess.attach(r)
         ├─ identity check: {chain, mint}; EVM/unknown chain -> UNSUPPORTED for now (Solana first)
         ├─ fatal flag present? -> RISK_FATAL_FLAW tier, stress still computed, no positive verdict possible
         ├─ execution.current(r.quotes, mechanics) -> proceeds by size (present tense, quote time = observed_at, TTL)
         ├─ stress.run(snapshot, sizes) -> scenario table, max size under caps
         ├─ evidence lookup (DB, as-of r.observed_at): cohort runs whose dataset cutoff <= as_of and whose
         │    eligibility rule matches this opportunity (status, liquidity band, age band)
         │      found -> HISTORICAL_COHORT tier with stored run id, sample sizes, sealed-test metrics
         │      none  -> SCENARIO_ONLY or INSUFFICIENT_HISTORY
         ├─ token-specific history? bars for this mint closed before as_of >= minimum -> TOKEN_SPECIFIC signals (TA)
         └─ persist bt_assessments (append-only) -> report section + JSON
```

Batch research path (not per opportunity): `backtest data universe` builds the frozen discovery universe from git history of `data/state/latest.json`; `backtest data bars` fetches historical OHLCV per (mint, pool) with bounded rate; `backtest run` replays strategies with walk-forward and sealed test; results stored as experiment runs that assess.py can cite.

## 4. Dependency graph

```
timeguard ◄── store ◄── schema
    ▲           ▲
    │           ├── sources/* (gecko, labstate, dexscreener, jupiter, capture[, maxun])
    │           │
execution ◄─────┤
strategies ◄────┤ (features only through timeguard.asof)
engine ◄── execution, strategies, timeguard
validation ◄── engine
stress ◄── execution
assess ◄── stress, execution, store (evidence lookup), validation results
report ◄── assess
outcomes ◄── store, sources.gecko, timeguard
cli ◄── all
```

Hard rule (tested from Phase 05): `memelab/backtest` imports nothing that can sign, send or place orders, and no module under it calls any URL path other than read-only GETs and Jupiter `/swap/v1/quote`.

## 5. Synchronous vs deferred

- Fast stage: pure computation on the analyze result plus one DB read. Budget under 1 s per opportunity, zero network. Always runs when enabled.
- Deep stage: historical fetches and replays. Never blocks discovery. Bounded by policy: at most 200 GeckoTerminal calls per run, pacing at least 3 s between calls with exponential backoff on 429, at most 30 minutes wall time. Outage leaves the fast stage's honest tier in place.

## 6. Evidence tiers and abstention

| Tier | Requires | Allowed claims |
|---|---|---|
| TOKEN_SPECIFIC | closed bars for this mint before as_of covering the strategy's warm-up, plus a defined pool basis | signal state for this token; never a forecast |
| HISTORICAL_COHORT | a stored experiment run with a frozen universe that includes dead/rejected tokens, net-of-cost sealed-test results, n above the minimum | cohort statistics with uncertainty, labeled as cohort, not this token |
| SCENARIO_ONLY | current quotes or pool reserves | stress table and capacity; no historical performance |
| UNAVAILABLE | none of the above | abstention with a reason state |

Reason states: COMPLETE, PARTIAL_WITH_LIMITATIONS, INSUFFICIENT_HISTORY, INSUFFICIENT_EXECUTION_DATA, UNSUPPORTED_POOL, STALE_DATA, INVALID_TOKEN_ID, UNVERIFIED_CATALYST, RISK_FATAL_FLAW, SOURCE_BLOCKED, ERROR.

## 7. Execution fidelity ladder (no false universal x*y=k)

1. EXACT_CPMM: pool type known CPMM (pumpswap, raydium AMM v4 / CPMM, meteora DAMM v1 treated only if verified constant-product) and reserves observed at or before the decision time. Exact swap math with fees.
2. QUOTE_OBSERVED: a router quote observed at the decision time for the size (present-tense lab quotes, or historical lab quotes stored with their observation time). Interpolate only inside tested sizes.
3. LIQ_SNAPSHOT_APPROX: CPMM pool, only a USD liquidity snapshot at or before decision time. Conservative CPMM approximation (reserves = liquidity/2 each side), labeled lower fidelity, plus a haircut.
4. UNSUPPORTED_POOL: CLMM/DLMM/unknown without tick/bin state. No fill model; abstain or use QUOTE_OBSERVED only.

Today's quotes are never used as historical fills (G15). Candle close is never a guaranteed fill (fills at the next bar open after decision plus latency, then cost model).

## 8. Data layer and migrations

- Additive `bt_*` tables in the same SQLite file, created by `backtest.schema.migrate` (idempotent, versioned, backup before migrate, rollback = drop bt_* tables only). Existing tables untouched.
- Append-only enforced with SQLite triggers (abort UPDATE/DELETE) on observation, bar, liquidity, quote, fill, assessment and outcome tables. Corrections are new rows with `supersedes_id`.
- Immutable raw shards for fetched provider payloads under `data/backtest/raw/<provider>/<sha256>.json` (gitignored when large; small fixtures checked in under tests).

## 9. Operator controls

- Policy file `data/backtest_policy.json` (gitignored) or CLI flags; default disabled. Fields: enabled, sizes_usd, max_loss_usd, max_impact_pct, deep_stage, fetch budgets, provider allowlist.
- `python -m memelab backtest status` shows policy, last runs, budgets used.
- Kill switch: `enabled: false` (or env `MEMELAB_BACKTEST=0`) removes the section and the hook without touching the rest of the lab.

## 10. Scoring preservation

The 100-point score, fatal flags and status are never modified. Severe stress adds a separate `stress_flag` (e.g., STRUCTURALLY_UNTRADEABLE at the requested size) shown beside the score. Any future cap on status needs its own decision and tests (not planned).

## 11. Web crawlers and Maxun placement

Approved crawler use cases (budgets in research/CRAWL_POLICY.md):

1. Phase 02/03: docs and repo discovery (Firecrawl search/scrape, Crawl4AI local) as enrichment only.
2. Phase 06/09: capture of public catalyst pages through the existing catalyst layer (`catalyst/firecrawl.py`, `catalyst_page_fetches`). No second ingestion pipeline.
3. Phase 06A: bake-off pages on two public site types.

Maxun (if ever adopted) plugs in only as `backtest/sources/maxun.py`, a thin client that writes captures through the same capture contract into the existing catalyst source/page tables, keyed by canonical origin + content hash:

```
Maxun Cloud robot run ─► maxun.py (fetch run by id) ─► capture contract (collector=MAXUN, run id, url, hashes, first_seen_at = capture time)
   ─► existing catalyst registry / page tables (dedup by canonical origin + content version)
   ─► catalyst events (UNKNOWN_AS_OF until contemporaneous proof) ─► as-of catalyst features ─► assessment report
```

Maxun stays outside the backtesting top-ten ranking. Standing schedules need Elving's separate approval.

## 12. Resource budgets (this environment)

Workspace: Linux, Python 3.13, about 4 vCPU class. Targets: full test suite of the new package under 120 s; one cohort replay over 200 tokens under 60 s from cached bars; fast assessment under 1 s per opportunity.
