# Phase 02: ingestion contract and the bridge/inbox adapter

Source of truth: `memelab/social/ingest.py` (contract, validation, pipeline), `memelab/social/bridge_adapter.py` (the adapter), `memelab/social/cli.py` (CLI), `memelab/bridge/social.js` (browser-side shaping), migration 2 in `memelab/social/schema.py`. Tests: `tests/test_social_ingest.py`. Fixture: `tests/fixtures/social/inbox/soc_fx01.json`.

Related: [SCHEMA_01.md](SCHEMA_01.md) (version 1 tables), [DECISIONS.md](DECISIONS.md) (D-015 to D-019), [HANDOFF.md](HANDOFF.md).

## The route

This is the lab's existing bridge route, not a new one:

1. The collector runs in the signed-in Chrome tab (D-009). For social sources it shapes each read with `__SOC.put(source, items)` from `memelab/bridge/social.js`, which writes into `window.__ML.last` under the key `soc:<platform>:<source_id>`.
2. `__ML.ship("inbox/<id>.json")` and `__ML.land()` commit the result file to the hand-off repo, as for market data.
3. The cloud side pulls and ingests in one command: `python -m memelab social ingest --pull inbox/<id>.json [--ref <commit sha>]`. `github_inbox.pull()` writes `data/inbox/<id>.result.json` and the adapter reads it. Already pulled files: `--results <id>`. Any file: `--file <path>`.

Cloud Python is not assumed to reach any social or crypto API. The adapter only reads files; the network step is the existing raw GitHub pull.

A result file can mix social keys with market or catalyst keys. The social adapter reads `soc:*` keys only and leaves the rest to the modules that own them.

## Inbound schema `memelab.social.inbound/1`

One inbox entry per source read:

```
"soc:<platform>:<source_id>": {
  "s": 200, "len": <bytes>, "ms": <latency>, "err": null,
  "challenge": "login" | "captcha" | "blocked"      (only when the page asked for one; then s=0 and body=null)
  "body": {
    "schema": "memelab.social.inbound/1",
    "source": {"platform", "source_id", "access_mode", "collector", "rights_basis", "visibility": "PUBLIC", "terms_note"?, "url"?},
    "fetched_at": "<ISO with zone, or epoch>",        collector time
    "items": [ {
      "event_id"?             collector's id for this sighting; namespaced as '<platform>:<event_id>'. Absent -> 'derived:<sha256>'
      "provider_item_id" | "url"   at least one; url must be https
      "account"?              {"handle" | "provider_user_id", "profile_url"?, "display_name"?}
      "published_at"?         provider time; "published_at_basis"? PROVIDER | PARSED_RELATIVE
      "fetched_at"?           per-item override of the envelope time
      "retrieval_status"?     OK (default) | PARTIAL | NOT_FOUND | DELETED | PROTECTED | BLOCKED | RATE_LIMITED | LOGIN_REQUIRED | CAPTCHA | ERROR
      "content_hash"?         sha256 of the normalized text, computed in the browser (__SOC.hash); the text never ships
      "summary"?              own words, at most 400 characters (D-010)
      "metrics"?              numbers only
      "visibility"?           overrides source.visibility; anything but PUBLIC is quarantined
    } ]
  }
}
```

Rules enforced by the ingester:

- Whole-unit checks (schema id, source fields, platform matches the key, `fetched_at` parseable, zone-aware and not in the future). A failing unit is quarantined once with `item_index` NULL and its checkpoint is REJECTED, so it is not retried every run.
- Item checks. Errors name the field and the rule, never the value. A bad item is quarantined and the next item is processed.
- Blocked content classes (`text`, `raw_text`, `full_text`, `html`, `bio`, `description`, `media`, `image(s)`, `video(s)`, `dm(s)`, `members`, `quote(s)`, `screenshot`, `transcript`, also inside `account`) quarantine the item as BLOCKED_CONTENT. Non-public items are NOT_PUBLIC.
- Unknown fields are dropped and listed in `social_observation_provenance.ignored_fields`.
- Timestamps: provider time goes to `social_items.published_at` (and `provider_published_at` in provenance), collector time to `social_observations.observed_at` and `fetched_at`. A `published_at` more than 5 minutes after `fetched_at` is invalid.
- Stale data: a `fetched_at` older than `--max-age-hours` (default 12) is stored, marked `freshness='STALE'`, and the connector's health for the run is DEGRADED with the age; coverage is PARTIAL. Old sightings are still true history, so they are not dropped.

## Pipeline guarantees

- Idempotent. The same file twice adds nothing (unit checkpoint COMPLETE). The same events from a renamed or re-shipped file add nothing (event id is the primary key of provenance; observations are also unique by `observation_key`).
- Replay safe. Items are committed in batches (`--batch-size`, default 50) and the checkpoint's `next_index` is updated in the same transaction. A crash or budget stop resumes at the next uncommitted item.
- Bounded retries. `with_retries()` retries transient failures (attempts 3, backoff 0.5 s doubling, cap 8 s). Non-transient errors are not retried.
- Budget hooks. `Budget(max_items, max_units, max_cost, pace_seconds)`. `charge()` is called per unit and per item; collectors that read pages call it per page read for human pacing and paid-call cost. When a budget is reached the current unit stops at a batch boundary, later units are recorded as SKIPPED coverage, and the next run continues.
- Connector isolation. Health is recorded per connector per run (worst status wins: OK < DEGRADED < RATE_LIMITED < LOGIN_REQUIRED / CAPTCHA / BLOCKED < DOWN). A down connector, an unreadable file or an unexpected exception in one unit is recorded and the run continues. The run is PARTIAL when anything was degraded or down and FAILED only when no unit was usable. The CLI exits 0 for OK and PARTIAL, 1 for FAILED.
- Quarantine. `social_ingest_quarantine` holds hashes and reasons only. The payload is written to `<private folder>/quarantine/<sha256>.json` (gitignored, next to `MEMELAB_PRIVATE_DB`).
- Logging. JSON lines on the `memelab.social.ingest` logger. Content-bearing fields are dropped and secret-looking values (api keys, tokens, bearer headers, GitHub and OpenAI style tokens) are redacted.

## How X and Telegram plug in (later phases)

A collector phase adds no new ingestion code. It needs:

1. A page parser in the browser that produces items in the inbound schema: ids, URLs, account handle, provider time, `__SOC.hash(text)`, numeric counts. Summaries are written by the session in its own words, not copied.
2. `__SOC.put({platform: "x" | "telegram", source_id, access_mode: "signed_in_browser" | "navigate", collector: "<name>-v1", rights_basis: "signed_in_browser_public_view" | "public_preview", visibility: "PUBLIC"}, items)`. On a login wall, captcha or rate limit the collector stops and calls `put(source, [], {challenge: "login"})` or ships `s: 429`; the connector is then recorded as LOGIN_REQUIRED or RATE_LIMITED and nothing is retried in a loop.
3. Ship, pull, `python -m memelab social ingest --pull ...`.

If a provider ever needs a transport other than inbox files (a paid API approved by Elving), it implements the same two members as `BridgeInboxAdapter`: `name` and `units(budget)` yielding `SourceUnit`s. Validation, dedupe, checkpoints, quarantine, health and coverage stay shared.

## Known limits

- The verbatim-summary guard (`store.check_summary`) needs the source text, which never reaches the cloud side on this route. It has to run in the session that writes the summary.
- `social.js` and Python normalize whitespace the same way for the tested cases (tabs, new lines, NBSP, combining accents, emoji); a test runs both and compares hashes. Exotic Unicode whitespace could still differ.
- Health is per run; a connector not touched by a run gets no new row.

## Migration 2 (exact DDL, copied from the code by script)

```sql
CREATE TABLE social_ingest_runs (         -- one row per ingestion run (any adapter)
  run_id TEXT PRIMARY KEY,
  adapter TEXT NOT NULL,                  -- e.g. 'bridge_inbox'
  started_at REAL NOT NULL,
  finished_at REAL,
  status TEXT NOT NULL CHECK (status IN ('RUNNING','OK','PARTIAL','FAILED')),
  counts_json TEXT,                       -- numbers only: units, items, created, duplicates, quarantined ...
  params_json TEXT                        -- batch size, budget, stale threshold; never secrets
);

CREATE TABLE social_ingest_checkpoints (  -- replay safety: where each inbound unit got to
  connector TEXT NOT NULL,
  source_ref TEXT NOT NULL,               -- '<result file name>#<key>'
  unit_sha TEXT NOT NULL,                 -- sha256 of the canonical JSON of the unit; a changed unit is a new checkpoint
  status TEXT NOT NULL CHECK (status IN ('IN_PROGRESS','COMPLETE','REJECTED')),
  next_index INTEGER NOT NULL DEFAULT 0,  -- first item not yet committed
  item_count INTEGER,
  first_run_id TEXT NOT NULL,
  last_run_id TEXT NOT NULL,
  updated_at REAL NOT NULL,
  PRIMARY KEY (connector, source_ref, unit_sha)
);

CREATE TABLE social_ingest_quarantine (   -- malformed or policy-blocked inbound items; no payload content here
  id INTEGER PRIMARY KEY,
  quarantine_key TEXT NOT NULL UNIQUE,    -- sha256(connector | source_ref | unit_sha | item_index)
  run_id TEXT NOT NULL,
  connector TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  item_index INTEGER,                     -- NULL = the whole unit was rejected
  reason_code TEXT NOT NULL CHECK (reason_code IN ('INVALID','BLOCKED_CONTENT','NOT_PUBLIC','SCHEMA','STORE_ERROR')),
  errors_json TEXT NOT NULL,              -- field names and rule names only, never values
  payload_sha256 TEXT NOT NULL,
  private_payload_ref TEXT,               -- file in the gitignored private quarantine folder, if kept
  quarantined_at REAL NOT NULL
);
CREATE INDEX ix_siq_run ON social_ingest_quarantine(run_id);

CREATE TABLE social_observation_provenance (  -- one row per inbound event; ties an observation to where it came from
  event_id TEXT PRIMARY KEY,              -- collector event id, or 'derived:<sha256>' when the collector gave none
  observation_id INTEGER NOT NULL REFERENCES social_observations(id),
  run_id TEXT NOT NULL,
  connector TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  unit_sha TEXT NOT NULL,
  item_index INTEGER NOT NULL,
  inbound_schema TEXT NOT NULL,
  plan_id TEXT,
  fetched_at REAL NOT NULL,               -- collector time (also social_observations.observed_at)
  provider_published_at REAL,             -- provider time as given (also social_items.published_at); NULL = UNKNOWN
  freshness TEXT NOT NULL CHECK (freshness IN ('FRESH','STALE')),
  visibility TEXT NOT NULL CHECK (visibility IN ('PUBLIC')),   -- only public content is ever ingested (D-009)
  rights_basis TEXT NOT NULL,             -- how it was read, e.g. 'signed_in_browser_public_view'
  terms_note TEXT,
  ignored_fields TEXT,                    -- JSON list of unknown field names that were dropped
  recorded_at REAL NOT NULL
);
CREATE INDEX ix_sop_obs ON social_observation_provenance(observation_id);
```

Down script:

```sql
DROP TABLE IF EXISTS social_observation_provenance;
DROP TABLE IF EXISTS social_ingest_quarantine;
DROP TABLE IF EXISTS social_ingest_checkpoints;
DROP TABLE IF EXISTS social_ingest_runs;
```

`social_observations` (version 1) is unchanged. `store.record_observation()` gained a `content_hash` argument for hashes computed by the collector; existing callers are unaffected.
