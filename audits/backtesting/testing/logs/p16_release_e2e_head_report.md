# Release end-to-end run

Commit `41488adeb52bb77342ae7a75947568d31c7c3e38`. Python 3.13.17. Clean clone in a temp folder, network blocked by an audit hook, every credential variable removed, every database and private file in the temp folder.

Result: PASS. Stages with the expected exit code: 78 of 78. Network attempts: 0. Tracked files changed in the clone: 0. Tracked database byte-identical: yes.

## 00 setup: interpreter and test tooling

```
$ python -c "import sys, numpy, pytest; print(sys.version.split()[0], 'numpy', numpy.__version__, 'pytest', pytest.__version__)"
exit 0 (expected 0), 0.2 s
3.13.17 numpy 2.5.3 pytest 9.1.1
```

## 00 setup: CLI loads

```
$ python -m memelab social --help
exit 0 (expected 0), 0.7 s
usage: memelab social [-h]
                      {ingest,status,guard,x-health,x-ingest,tg-health,tg-ingest,tg-webhook-ingest,resolve,identity,extract,claims,llm-health,narrative-snapshot,narrative-show,narrative-why,narrative-changes,registry,wallet,perf,alpha,chrono,research,brief,trader-digest,feed,feed-demo,alerts,evaluate,replay,reddit-health,reddit-ingest,reddit-purge,fc-health,fc-ingest,discord-health,discord-ingest,discord-gateway,discord-purge,discord-reset,youtube-health,youtube-ingest,youtube-purge,sources} ...

positional arguments:
  {ingest,status,guard,x-health,x-ingest,tg-health,tg-ingest,tg-webhook-ingest,resolve,identity,extract,claims,llm-health,narrative-snapshot,narrative-show,narrative-why,narrative-changes,registry,wallet,perf,alpha,chrono,research,brief,trader-digest,feed,feed-demo,alerts,evaluate,replay,reddit-health,reddit-ingest,reddit-purge,fc-health,fc-ingest,discord-health,discord-ingest,discord-gateway,discord-purge,discord-reset,youtube-health,youtube-ingest,youtube-purge,sources}
    ingest              ingest social units from bridge result files
    status              runs, connector health, checkpoints, quarantine counts
    guard               fail if a tracked file holds raw third-party social
                        content
    x-health            X API adapter health (credentials, consent, cursors,
                        live evidence); no network
    x-ingest            ingest configured X scopes through the official X API
                        v2
    tg-health           Telegram Bot API health (credentials, channel access,
                        update cursor, live evidence)
    tg-ingest           poll approved Telegram channels through the Bot API
                        (getUpdates)
    tg-webhook-ingest   ingest Telegram webhook updates spooled in the private
                        folder
    resolve             resolve a post's token references to (chain,
                        contract); store candidates and evidence
    identity            stored token identity, candidates, evidence and market
                        context for an item
    extract             structured claim extraction for one observation
                        (deterministic + model if configured)
... (65 more lines)
```

## 01 migrations: empty database to latest

```
$ python tools/release_e2e.py --migrate-check $TMP/e2e.sqlite
exit 0 (expected 0), 0.2 s
{
 "database_existed": false,
 "latest": 12,
 "legacy_rows_after": {
  "entries": 0,
  "rejections": 0,
  "social_snapshots": 0,
  "theses": 0,
  "tokens": 0,
  "watchlist": 0
 },
 "legacy_rows_before": {},
 "legacy_unchanged": true,
 "migration_rows": 12,
 "social_version_after": 12,
 "social_version_before": 0
}
```

## 01 migrations: idempotent second init

```
$ python tools/release_e2e.py --migrate-check $TMP/e2e.sqlite
exit 0 (expected 0), 0.1 s
{
 "database_existed": true,
 "latest": 12,
 "legacy_rows_after": {
  "entries": 0,
  "rejections": 0,
  "social_snapshots": 0,
  "theses": 0,
  "tokens": 0,
  "watchlist": 0
 },
 "legacy_rows_before": {
  "entries": 0,
  "rejections": 0,
  "social_snapshots": 0,
  "theses": 0,
  "tokens": 0,
  "watchlist": 0
 },
 "legacy_unchanged": true,
 "migration_rows": 12,
 "social_version_after": 12,
 "social_version_before": 12
}
```

## 01 migrations: copy of the tracked database (legacy rows unchanged)

```
$ cp data/memelab.sqlite $TMP/tracked_copy.sqlite && python tools/release_e2e.py --migrate-check $TMP/tracked_copy.sqlite
exit 0 (expected 0), 0.1 s
{
 "database_existed": true,
 "latest": 12,
 "legacy_rows_after": {
  "entries": 43,
  "rejections": 20,
  "social_snapshots": 99,
  "theses": 33,
  "tokens": 13,
  "watchlist": 5
 },
 "legacy_rows_before": {
  "entries": 43,
  "rejections": 20,
  "social_snapshots": 99,
  "theses": 33,
  "tokens": 13,
  "watchlist": 5
 },
 "legacy_unchanged": true,
 "migration_rows": 12,
 "social_version_after": 12,
 "social_version_before": 0
}
```

## 02 fixture inbox load (bridge result file)

```
$ python -m memelab social ingest --file tests/fixtures/social/inbox/soc_fx01.json --db $TMP/e2e.sqlite --now 1791566000
exit 0 (expected 0), 0.9 s
{
 "budget": {
  "max_cost": null,
  "max_items": null,
  "max_units": null,
  "pace_seconds": 0.0,
  "used": {
   "cost": 0.0,
   "items": 7,
   "units": 4
  }
 },
 "counts": {
  "budget_stopped": 0,
  "created": 4,
  "duplicates": 0,
  "items_seen": 7,
  "quarantined": 3,
  "stale_items": 0,
  "units": 4,
  "units_failed": 0,
  "units_ok": 2,
  "units_rejected": 0,
  "units_replayed": 0,
  "units_unavailable": 2
... (32 more lines)
--- stderr
{"connector": "bridge_inbox:x:example_down_account", "error": "TypeError: Failed to fetch", "event": "unit_unavailable", "run_id": "ingest_20261009_171320_7ce4da", "source_ref": "soc_fx01.json#soc:x:example_down_account", "status": "DOWN"}
{"connector": "bridge_inbox:x:example_login_wall", "error": "page asked for login", "event": "unit_unavailable", "run_id": "ingest_20261009_171320_7ce4da", "source_ref": "soc_fx01.json#soc:x:example_login_wall", "status": "LOGIN_REQUIRED"}
{"connector": "bridge_inbox:x:example_trader_a", "errors": ["published_at: unparseable or naive timestamp", "metrics: non-numeric values for views"], "event": "quarantined", "item_index": 2, "payload_sha256": "a34fd4ae04cb356ca6e023f6fdd160f09d9c6ac1809bdfa459d811a075647485", "reason": "INVALID", "run_id": "ingest_20261009_171320_7ce4da", "source_ref": "soc_fx01.json#soc:x:example_trader_a"}
{"connector": "bridge_inbox:x:example_trader_a", "errors": ["text: content class not allowed in the inbox (D-010)"], "event": "quarantined", "item_index": 3, "payload_sha256": "e6506b0f024d99ecaaeffcda2e5e07c314d5d04a3d57d3d66ed78736590180ca", "reason": "BLOCKED_CONTENT", "run_id": "ingest_20261009_171320_7ce4da", "source_ref": "soc_fx01.json#soc:x:example_trader_a"}
{"connector": "bridge_inbox:x:example_trader_a", "errors": ["visibility: only PUBLIC content is ingested (D-009)"], "event": "quarantined", "item_index": 4, "payload_sha256": "f8cb71db70a628118f8e86316df7abc8b846ed9210e03685ccdb1cb5e4cffb19", "reason": "NOT_PUBLIC", "run_id": "ingest_20261009_171320_7ce4da", "source_ref": "soc_fx01.json#soc:x:example_trader_a"}
```

## 03 duplicate replay: same file again adds nothing

```
$ python -m memelab social ingest --file tests/fixtures/social/inbox/soc_fx01.json --db $TMP/e2e.sqlite --now 1791566100
exit 1 (expected 1), 0.7 s
{
 "budget": {
  "max_cost": null,
  "max_items": null,
  "max_units": null,
  "pace_seconds": 0.0,
  "used": {
   "cost": 0.0,
   "items": 0,
   "units": 4
  }
 },
 "counts": {
  "budget_stopped": 0,
  "created": 0,
  "duplicates": 0,
  "items_seen": 0,
  "quarantined": 0,
  "stale_items": 0,
  "units": 4,
  "units_failed": 0,
  "units_ok": 0,
  "units_rejected": 0,
  "units_replayed": 2,
  "units_unavailable": 2
... (20 more lines)
--- stderr
{"connector": "bridge_inbox:x:example_down_account", "error": "TypeError: Failed to fetch", "event": "unit_unavailable", "run_id": "ingest_20261009_171500_629293", "source_ref": "soc_fx01.json#soc:x:example_down_account", "status": "DOWN"}
{"connector": "bridge_inbox:x:example_login_wall", "error": "page asked for login", "event": "unit_unavailable", "run_id": "ingest_20261009_171500_629293", "source_ref": "soc_fx01.json#soc:x:example_login_wall", "status": "LOGIN_REQUIRED"}
```

## 03 duplicate replay: renamed copy adds nothing

```
$ cp tests/fixtures/social/inbox/soc_fx01.json $TMP/renamed_copy.json && python -m memelab social ingest --file $TMP/renamed_copy.json --db $TMP/e2e.sqlite --now 1791566200
exit 0 (expected 0), 0.7 s
{
 "budget": {
  "max_cost": null,
  "max_items": null,
  "max_units": null,
  "pace_seconds": 0.0,
  "used": {
   "cost": 0.0,
   "items": 7,
   "units": 4
  }
 },
 "counts": {
  "budget_stopped": 0,
  "created": 0,
  "duplicates": 4,
  "items_seen": 7,
  "quarantined": 3,
  "stale_items": 0,
  "units": 4,
  "units_failed": 0,
  "units_ok": 2,
  "units_rejected": 0,
  "units_replayed": 0,
  "units_unavailable": 2
... (32 more lines)
--- stderr
{"connector": "bridge_inbox:x:example_down_account", "error": "TypeError: Failed to fetch", "event": "unit_unavailable", "run_id": "ingest_20261009_171640_d4f58e", "source_ref": "renamed_copy.json#soc:x:example_down_account", "status": "DOWN"}
{"connector": "bridge_inbox:x:example_login_wall", "error": "page asked for login", "event": "unit_unavailable", "run_id": "ingest_20261009_171640_d4f58e", "source_ref": "renamed_copy.json#soc:x:example_login_wall", "status": "LOGIN_REQUIRED"}
{"connector": "bridge_inbox:x:example_trader_a", "errors": ["published_at: unparseable or naive timestamp", "metrics: non-numeric values for views"], "event": "quarantined", "item_index": 2, "payload_sha256": "a34fd4ae04cb356ca6e023f6fdd160f09d9c6ac1809bdfa459d811a075647485", "reason": "INVALID", "run_id": "ingest_20261009_171640_d4f58e", "source_ref": "renamed_copy.json#soc:x:example_trader_a"}
{"connector": "bridge_inbox:x:example_trader_a", "errors": ["text: content class not allowed in the inbox (D-010)"], "event": "quarantined", "item_index": 3, "payload_sha256": "e6506b0f024d99ecaaeffcda2e5e07c314d5d04a3d57d3d66ed78736590180ca", "reason": "BLOCKED_CONTENT", "run_id": "ingest_20261009_171640_d4f58e", "source_ref": "renamed_copy.json#soc:x:example_trader_a"}
{"connector": "bridge_inbox:x:example_trader_a", "errors": ["visibility: only PUBLIC content is ingested (D-009)"], "event": "quarantined", "item_index": 4, "payload_sha256": "f8cb71db70a628118f8e86316df7abc8b846ed9210e03685ccdb1cb5e4cffb19", "reason": "NOT_PUBLIC", "run_id": "ingest_20261009_171640_d4f58e", "source_ref": "renamed_copy.json#soc:x:example_trader_a"}
```

## 03 ingest status

```
$ python -m memelab social status --db $TMP/e2e.sqlite
exit 0 (expected 0), 0.7 s
{
 "checkpoints": [
  {
   "connector": "bridge_inbox:telegram:example_alpha_channel",
   "item_count": 1,
   "last_run_id": "ingest_20261009_171640_d4f58e",
   "next_index": 1,
   "source_ref": "renamed_copy.json#soc:telegram:example_alpha_channel",
   "status": "COMPLETE"
  },
  {
   "connector": "bridge_inbox:x:example_trader_a",
   "item_count": 6,
   "last_run_id": "ingest_20261009_171640_d4f58e",
   "next_index": 6,
   "source_ref": "renamed_copy.json#soc:x:example_trader_a",
   "status": "COMPLETE"
  },
  {
   "connector": "bridge_inbox:telegram:example_alpha_channel",
   "item_count": 1,
   "last_run_id": "ingest_20261009_171320_7ce4da",
   "next_index": 1,
   "source_ref": "soc_fx01.json#soc:telegram:example_alpha_channel",
   "status": "COMPLETE"
... (70 more lines)
```

## 04 token resolution: ambiguous ticker

```
$ python -m memelab social resolve --post tests/fixtures/social/resolve/post_ambiguous.json --bodies tests/fixtures/social/resolve/fx_providers.json --context --db $TMP/e2e.sqlite --now 1791676800
exit 0 (expected 0), 0.7 s
{
 "resolutions": [
  {
   "candidates": [
    {
     "chain": "ethereum",
     "contract": "0x7059d8e5faab71a5e2628cad88bcc1df0b68c305",
     "liquidity_usd_seen": 9000000.0,
     "name_seen": "Pepe Fixture Eth",
     "provider_chain": "ethereum",
     "providers": [
      "dexscreener"
     ],
     "rank": 0,
     "ref_id": 2,
     "resolution_id": 1,
     "support": "supported",
     "symbol_seen": "PEPE",
     "verdict": "viable",
     "why": "symbol_match_only"
    },
    {
     "chain": "solana",
     "contract": "4JFBJ56AUWfSGaJwqhqfsKHMJNJX22Xg3WM3K9fTdLZW",
     "liquidity_usd_seen": 300000.0,
... (136 more lines)
```

## 04 token resolution: exact contract

```
$ python -m memelab social resolve --post tests/fixtures/social/resolve/post_resolved.json --bodies tests/fixtures/social/resolve/fx_providers.json --context --db $TMP/e2e.sqlite --now 1791676800
exit 0 (expected 0), 0.8 s
{
 "resolutions": [
  {
   "candidates": [
    {
     "chain": "solana",
     "contract": "8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ",
     "liquidity_usd_seen": 230000.0,
     "name_seen": "Lab Dog Fixture",
     "provider_chain": "solana",
     "providers": [
      "dexscreener",
      "geckoterminal",
      "jupiter"
     ],
     "rank": 0,
     "ref_id": 6,
     "resolution_id": 2,
     "support": "supported",
     "symbol_seen": "LABDOG",
     "verdict": "chosen",
     "why": "contract_found_on_chain"
    },
    {
     "chain": "solana",
... (395 more lines)
```

## 05 structured extraction without a model

```
$ python -m memelab social extract --post tests/fixtures/social/claims/demo_post_nollm.json --db $TMP/e2e.sqlite --now 1791676800
exit 0 (expected 0), 0.8 s
{
 "report": [
  "Observation 5, deterministic rules: done",
  "Observation 5, model analysis (no provider): not available (model_not_configured)",
  "Claim 1 from post x:1900000000000000001",
  "  Source: https://x.com/example_poster/status/1900000000000000001; posted 2026-10-10 02:30 UTC; seen 2026-10-10 02:31 UTC (fixture); observation 5",
  "  What it is: a token reference, a reference found in the text; stance neutral; time frame: no time frame given",
  "  In the lab's words: The post contains a link reference (identity unresolved).",
  "  Token: link:https://pump.fun/coin/8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ -> no exact identity (unresolved); not counted as this token",
  "  Author position: the author does not say whether they hold it",
  "  Whose words: the poster's own words",
  "  Uncertainty: low",
  "  Evidence (token): characters 62-106 of the post text (sha256 e7df620ffcc3)",
  "  Evidence bucket: FACT (the post contains this); verification: present in text",
  "  Extracted by: deterministic rules (claims-extract-v1), no model used",
  "Claim 2 from post x:1900000000000000001",
  "  Source: https://x.com/example_poster/status/1900000000000000001; posted 2026-10-10 02:30 UTC; seen 2026-10-10 02:31 UTC (fixture); observation 5",
  "  What it is: a token reference, a reference found in the text; stance neutral; time frame: no time frame given",
  "  In the lab's words: The post contains a ticker reference (identity unresolved).",
  "  Token: ticker:LABDOG -> no exact identity (unresolved); not counted as this token",
  "  Author position: the author does not say whether they hold it",
  "  Whose words: the poster's own words",
  "  Uncertainty: low",
  "  Evidence (token): characters 32-39 of the post text (sha256 b109bcb1de25)",
  "  Evidence bucket: FACT (the post contains this); verification: present in text",
... (41 more lines)
```

## 05 structured extraction with the offline mock provider

```
$ python -m memelab social extract --post tests/fixtures/social/claims/demo_post_model.json --mock tests/fixtures/social/claims/demo_mock.json --db $TMP/e2e.sqlite --now 1791676800
exit 0 (expected 0), 1.0 s
{
 "report": [
  "Observation 6, deterministic rules: done",
  "Observation 6, model analysis (mock): done",
  "Claim 3 from post x:1900000000000000002",
  "  Source: https://x.com/example_poster/status/1900000000000000002; posted 2026-10-10 03:00 UTC; seen 2026-10-10 03:01 UTC (fixture); observation 6",
  "  What it is: a token reference, a reference found in the text; stance neutral; time frame: no time frame given",
  "  In the lab's words: The post contains a link reference (identity unresolved).",
  "  Token: link:https://pump.fun/coin/8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ -> no exact identity (unresolved); not counted as this token",
  "  Author position: the author does not say whether they hold it",
  "  Whose words: the poster's own words",
  "  Uncertainty: low",
  "  Evidence (token): characters 100-144 of the post text (sha256 e7df620ffcc3)",
  "  Evidence bucket: FACT (the post contains this); verification: present in text",
  "  Extracted by: deterministic rules (claims-extract-v1), no model used",
  "Claim 4 from post x:1900000000000000002",
  "  Source: https://x.com/example_poster/status/1900000000000000002; posted 2026-10-10 03:00 UTC; seen 2026-10-10 03:01 UTC (fixture); observation 6",
  "  What it is: a token reference, a reference found in the text; stance neutral; time frame: no time frame given",
  "  In the lab's words: The post contains a ticker reference (identity unresolved).",
  "  Token: ticker:LABDOG -> no exact identity (unresolved); not counted as this token",
  "  Author position: the author does not say whether they hold it",
  "  Whose words: the poster's own words",
  "  Uncertainty: low",
  "  Evidence (token): characters 34-41 of the post text (sha256 b109bcb1de25)",
  "  Evidence bucket: FACT (the post contains this); verification: present in text",
... (59 more lines)
```

## 05 model status (none configured)

```
$ python -m memelab social llm-health
exit 0 (expected 0), 0.7 s
{
 "config_file": "$TMP/private/llm.json",
 "fixture_calls": 1,
 "live_calls_ok": 0,
 "model": null,
 "provider": null,
 "status": "model_not_configured"
}
```

## 06 narrative snapshot, day before

```
$ python -m memelab social narrative-snapshot --day 2026-10-09 --tz UTC --db $TMP/e2e.sqlite --now 1791849600
exit 0 (expected 0), 0.9 s
{
 "created": true,
 "report": [
  "Narrative snapshot 1: window 2026-10-09 UTC (1791504000 to 1791590400 UTC epoch), cutoff 1791590400, complete, engine narr-v1.",
  "0 cluster(s) from 0 claim(s). Compared with: none (first comparable snapshot).",
  "Changes since the previous snapshot: none.",
  "Not clustered: 5 not observed by cutoff."
 ],
 "run_id": 1,
 "summary": {
  "changes": {},
  "clusters": 0,
  "compared_to": "none (first comparable snapshot)",
  "highlights": [],
  "insufficient_coverage": [],
  "new": [],
  "prev_run_id": null
 },
 "unassigned": {
  "claims_by_reason": {
   "not_observed_by_cutoff": 5
  },
  "claims_clustered": 0,
  "claims_considered": 0,
  "ticker_only_mentions": {}
... (2 more lines)
```

## 06 narrative snapshot, claim day

```
$ python -m memelab social narrative-snapshot --day 2026-10-10 --tz UTC --db $TMP/e2e.sqlite --now 1791849600
exit 0 (expected 0), 0.8 s
{
 "created": true,
 "report": [
  "Narrative snapshot 2: window 2026-10-10 UTC (1791590400 to 1791676800 UTC epoch), cutoff 1791676800, complete, engine narr-v1.",
  "1 cluster(s) from 5 claim(s). Compared with: run 1.",
  "Contains fixture data (not live provider data).",
  "- theme: animal [tag:animal]: insufficient_coverage, confidence UNKNOWN, 1 mention(s) in window, independent sources not estimable, amplifiers 0, dependent 0, fresh.",
  "Changes since the previous snapshot: 1 NEW.",
  "Not clustered: 4 token not resolved to a contract."
 ],
 "run_id": 2,
 "summary": {
  "changes": {
   "NEW": 1
  },
  "clusters": 1,
  "compared_to": "run 1",
  "highlights": [],
  "insufficient_coverage": [
   "tag:animal"
  ],
  "new": [
   "tag:animal"
  ],
  "prev_run_id": 1
... (12 more lines)
```

## 06 narrative change since the previous snapshot

```
$ python -m memelab social narrative-changes --db $TMP/e2e.sqlite
exit 0 (expected 0), 0.7 s
{
 "changes": [
  {
   "after": {
    "confidence": "UNKNOWN",
    "conflicted": 0,
    "independent_source_count": null,
    "item_count": 1,
    "stance": {
     "positive": 1
    },
    "status": "insufficient_coverage",
    "window_mentions": 1
   },
   "before": null,
   "change_type": "NEW",
   "cluster_key": "tag:animal",
   "prev_run_id": 1,
   "run_id": 2
  }
 ],
 "run_id": 2,
 "summary": {
  "changes": {
   "NEW": 1
... (13 more lines)
```

## 07 trader registry: import a permitted list (fixture)

```
$ python -m memelab social registry import tests/fixtures/social/registry/leaderboard_fresh.json --db $TMP/e2e.sqlite --now 1791849600
exit 0 (expected 0), 0.7 s
{
 "capture_id": 1,
 "captured_at": 1791806400.0,
 "entities_new": 11,
 "fixture_label": "invented demonstration list; no real people, wallets or figures",
 "freshness": "FRESH",
 "is_fixture": true,
 "links_new": 12,
 "listings": 6,
 "never_done": [
  "approve",
  "assign category",
  "mark wallet as owned",
  "rank"
 ],
 "rejects": [
  {
   "code": "INVALID_WALLET",
   "row": 5
  },
  {
   "code": "BLOCKED_CONTENT_KEY",
   "row": 6
  }
 ],
... (13 more lines)
```

## 07 trader registry: add an account (fixture)

```
$ python -m memelab social registry add account --platform x --handle example_poster --provider-id 4242 --fixture-label 'INVENTED FIXTURE: release e2e' --db $TMP/e2e.sqlite --now 1791849600
exit 0 (expected 0), 0.7 s
{
 "entity_id": "acct:x:id:4242",
 "note": "added as a candidate with no evidence; add evidence before approving",
 "review_state": "CANDIDATE"
}
```

## 07 trader registry: status

```
$ python -m memelab social registry status --db $TMP/e2e.sqlite
exit 0 (expected 0), 0.7 s
{
 "captures": 1,
 "entities": {
  "LEADERBOARD_CANDIDATE": 5,
  "OBSERVED_WALLET": 3,
  "SOCIAL_ACCOUNT": 4,
  "SOURCE_ORGANIZATION": 1
 },
 "fixture_entities": 13,
 "links": 12,
 "live_captures": 0,
 "live_data": "none: no permitted live list has been supplied; every capture here is a fixture",
 "records": {
  "CANDIDATE": 13
 }
}
```

## 08 wallet attribution: track a fixture wallet

```
$ python -m memelab social wallet track add solana 5rXq7LtW6VnvMo16bB67FBstaaCr5RFeA7MCgECdkcpD --reason 'fixture e2e wallet' --by release --fixture --db $TMP/e2e.sqlite --now 1791849600
exit 0 (expected 0), 0.7 s
{
 "created": true,
 "status": "ACTIVE",
 "tracked_id": 1
}
```

## 08 wallet attribution: ingest fixture activity

```
$ python -m memelab social wallet ingest tests/fixtures/social/wallets/fx_helius_ok.json --fixture --db $TMP/e2e.sqlite --now 1791849600
exit 0 (expected 0), 0.7 s
{
 "chain": "solana",
 "fetched_at": 1791844200.0,
 "payload_sha256": "175c349ac120f34b2bf798825b5ad16496c3e1e069fd14a52b8e9431f4f6d4c9",
 "provider": "helius",
 "results": [
  {
   "already_stored": 0,
   "beyond_limit": 0,
   "reject_codes": [],
   "rejected": 0,
   "seen": 2,
   "status": "OK",
   "stored": 2,
   "wallet": "5rXq7LtW6VnvMo16bB67FBstaaCr5RFeA7MCgECdkcpD"
  },
  {
   "detail": "not a tracked wallet; ignored",
   "status": "UNTRACKED",
   "wallet": "5zeWRRxzaTBVKhLo8edrqsPe2rnAguMio78DiVJ5Mkjj"
  },
  {
   "detail": "not a tracked wallet; ignored",
   "status": "UNTRACKED",
   "wallet": "GKSw5BerNKY1fb14QzgWXcxMweiKdmtu6oJ3NjxAzRZc"
... (5 more lines)
```

## 08 wallet attribution: self-disclosure assertion

```
$ ACCT=$(python -c "import sqlite3; c=sqlite3.connect('$TMP/e2e.sqlite'); print(c.execute(\"SELECT entity_id FROM social_registry_entities WHERE entity_kind='SOCIAL_ACCOUNT' ORDER BY rowid DESC LIMIT 1\").fetchone()[0])") && python -m memelab social wallet assert "$ACCT" solana 5rXq7LtW6VnvMo16bB67FBstaaCr5RFeA7MCgECdkcpD --type OFFICIAL_SELF_DISCLOSURE --ref https://example.invalid/post/1 --by release --db $TMP/e2e.sqlite --now 1791849600 && python -m memelab social wallet why "$ACCT" solana 5rXq7LtW6VnvMo16bB67FBstaaCr5RFeA7MCgECdkcpD --db $TMP/e2e.sqlite --now 1791849600
exit 0 (expected 0), 1.6 s
{
 "assertion_id": 1,
 "confidence": "LOW",
 "control_hypothesis": "ACCOUNT_CLAIMS_WALLET",
 "created": true,
 "signature_check": "NOT_APPLICABLE"
}
Account acct:x:id:4242  wallet solana:5rXq7LtW6VnvMo16bB67FBstaaCr5RFeA7MCgECdkcpD
Level: SELF_CLAIMED (CLAIMED), confidence LOW
Real-world identity: UNKNOWN. This says nothing about who the person is.
Why: the account says so; nothing independent confirms it
Awaiting review: assertions 1
  #1 OFFICIAL_SELF_DISCLOSURE by acct:x:id:4242 ref https://example.invalid/post/1 seen 1791849600.0 [UNREVIEWED/ACTIVE] counts as SELF_CLAIM
```

## 08 wallet attribution: custody wallet refused

```
$ python -m memelab social wallet track add solana 5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9 --reason 'custody check' --by release --fixture --db $TMP/e2e.sqlite --now 1791849600
exit 1 (expected 1), 0.8 s

--- stderr
{"error": "custody_wallet_not_monitored_by_default: this address is labelled CUSTODY_EXCHANGE (Binance hot); its activity is many people's, not one trader's. Pass allow_custody to watch it anyway."}
```

## 09 P&L reconstruction (FIFO, AVCO sensitivity, reconciliation)

```
$ python -m memelab social perf run --ledger tests/fixtures/social/perf/ledger_main.json
exit 0 (expected 0), 0.7 s
Wallet performance (wallet-level, not person-level)   scope: W1   chain: solana   as of 1790864000   convention: FIFO
Label: FIXTURE: invented wallet, invented prices; hand-checked in PERFORMANCE_10.md
Reconstruction: PARTIAL. Comprehensive reconstruction cannot be achieved: history coverage is UNKNOWN: earlier transactions may exist that are not in the ledger; 1 disposal(s) exceeded the inventory the ledger can explain; an opening lot of unknown basis was added (missing earlier history or a unit error); 1 lot(s) of unknown basis (transfers in, unpriced buys or liquidity excess): sales from them show proceeds but no gain or loss; 1 entry(ies) were unclassified, unsupported or rejected and are not in the P&L; tokens touched by unclassified, unsupported or suspect entries: TOKQ, TOKZ
Reconciled: True (13 pass, 1 warn, 0 fail)
History coverage: UNKNOWN; first entry 1790000000.0, last 1790372600.0; 1 disposal(s) needed an opening lot from missing history

Realized (trading lots, known basis and proceeds, before fees): 1720 USD
Known fees: 0.178 USD (0 fee(s) unknown, 0 unpriced)
Realized after known fees: 1719.822 USD
Proceeds from lots of unknown basis (no gain or loss computed): 600 USD
Unrealized, marked at last supplied price: 1000 USD on 2 of 2 open positions of known basis
If sold now per supplied quotes (lower bound): -300 USD on 2 of 2; the mark overstates the executable value by 1300 USD where both are known

Trades (closed, fully known positions): 3 of 5 positions; swaps accounted for: 13
Win rate: 0.666666666667 (95% interval ['0.207659598808', '0.938508055979']); median return 0.136340909091; aggregate return 0.392675799087
Profit share from biggest winner: 0.943404058605; return excluding biggest winner: -0.202927536232
Drawdown: INSUFFICIENT_DATA (3 fully valued points of 19 (need at least 20 and 0.8 of all points))
Sensitivity: convention_AVCO 0 USD; stablecoins_at_1.00 -120 USD (MATERIAL); no_return_matching 0 USD

Score: INSUFFICIENT_DATA
  refused because: sample of 3 closed, fully known position(s) is below the minimum of 20
  refused because: the sample spans 2.0 days, below the minimum of 7
Limits: Wallet-level only. A wallet is not a person; other wallets, exchange flows and off-chain activity are not in the data. Amounts are the provider's legs. Decimals cannot be re-verified from stored events; a ledger with raw amounts and decimals is checked.
result sha256 d733edf5529c98f0..
```

## 10 information-alpha evaluation

```
$ python -m memelab social alpha run --input tests/fixtures/social/alpha/alpha_main.json --policy '{"horizons_s":[3600,21600,86400]}'
exit 0 (expected 0), 0.7 s
Information Alpha (information-alpha-v1, alpha-rules-v1)  label: FIXTURE: invented sources, tokens, posts and prices
INVENTED FIXTURE DATA: this is a demonstration of the calculation, not evidence about any real source.
as of 1790204400; delay 300s; size $500; primary horizon 24h; policy 82e8fe741984

Source src_a: 23 calls supplied, 16 eligible and independent, 14 evaluated, 14 with a matched baseline at the primary horizon.
  ineligible: CONDITIONAL_CLAIM 1, CONFLICTING_STATEMENTS 2, HINDSIGHT_CAPTURE_RISK 1, NOT_ORIGINAL 1, NO_DIRECTION 1, REPEAT_POST 1
  no usable price data: ILLIQUID_ENTRY 1, NO_PRICE_HISTORY 1
    1h  n=14  median net    -4.3%  baseline    -4.8%  relative     0.5%  ci95 ['-1.3%', '1.5%']  beat 0.57  false positives 14
    6h  n=14  median net    -1.3%  baseline    -5.3%  relative     4.0%  ci95 ['-6.7%', '9.9%']  beat 0.64  false positives 9
   24h  n=14  median net    -0.1%  baseline    -6.8%  relative     6.5%  ci95 ['-36.3%', '39.9%']  beat 0.57  false positives 7
  lead time: 6 with an onset, 8 none, 1 posted after the move; quantiles {'p25': 27900.0, 'median': 41400.0, 'p75': 57600.0}
  SCORE 50 (PRELIMINARY), point estimate 53, shrinkage weight 0.41. 50 means no demonstrated edge over matched tokens. Above 50: the low end of the 95% interval of the median relative return beat them, after shrinkage for sample size. Below 50: it did worse. The point estimate is shown as score_point. Not a probability and not a ranking of skill.
    not validated: 14 independent calls, validation needs 30
    not validated: 14 distinct tokens, validation needs 20
    not validated: the 95% interval of the median relative return includes zero: the result cannot be told apart from no edge
    not validated: chronological halves have 7 and 7 calls, the split-sample check needs 10 each

Source src_b: 3 calls supplied, 3 eligible and independent, 3 evaluated, 3 with a matched baseline at the primary horizon.
    1h  n=3   median net    -1.3%  baseline    -4.8%  relative     3.5%  ci95 none  beat 1.0  false positives 3
    6h  n=3   median net    16.5%  baseline    -5.3%  relative    21.8%  ci95 none  beat 1.0  false positives 0
   24h  n=3   median net    80.7%  baseline    -6.9%  relative    87.6%  ci95 none  beat 1.0  false positives 0
  lead time: 3 with an onset, 0 none, 0 posted after the move; quantiles {'p25': 19800.0, 'median': 21600.0, 'p75': 23400.0}
  NO SCORE (declined): 3 independent calls with a matched baseline at the primary horizon; at least 10 are needed to publish a score

Source src_c: 6 calls supplied, 0 eligible and independent, 0 evaluated, 0 with a matched baseline at the primary horizon.
... (9 more lines)
```

## 11 social and on-chain chronology: confident order

```
$ python -m memelab social chrono run --input tests/fixtures/social/chrono/confident.json
exit 0 (expected 0), 0.7 s
INVENTED FIXTURE DATA: no real post, wallet, token or person.
Chronology for solana:S5vznK6GJNtHJWH66MPdNBLHGx35G7HyS5vznK6GJNtH (LABCAT, symbol shown for reading only)
Source: FIXTURE source A (invented)   evaluated as of 2026-10-12 08:00:00Z   window 2026-10-08 01:59:59Z to 2026-10-12 08:00:00Z
Order between posts and trades: CONFIDENT

Clocks: SOURCE_PUBLICATION is the platform's time for a post; CHAIN_BLOCK is the block time of a transaction; COLLECTION is when the lab saw the post. Entries in the same group overlap in time and their order is not established.

Timeline
   1 g1    2026-10-11 00:00:00Z       CHAIN_BLOCK         ut3Tma..zF3E (a wallet linked to the source) bought 1,000,000 of the token in tx fyYNUQ..i8Mn.
   2 g2    2026-10-11 02:00:00Z       SOURCE_PUBLICATION  The source posted about the token in x:1900000000000000101, stance LONG (platform timestamp, 1 s precision).
   3 g3    2026-10-11 02:00:30Z       COLLECTION          The lab first saw post x:1900000000000000101 (collector clock).
   4 g4    2026-10-11 02:10:00Z       CHAIN_BLOCK         5xX8F4..ipwA (a wallet with an unverified association) bought 50,000 of the token in tx pMRRu2..kp2C.
   5 g5  ~ 2026-10-11 05:00:00Z       CANDLE              Price rose 60% between 2026-10-11 02:00:00Z and 2026-10-11 05:00:00Z (candle closes, fixture-candles (INVENTED)).
   6 g5  ~ 2026-10-11 05:00:00Z       CHAIN_BLOCK         ut3Tma..zF3E (a wallet linked to the source) sold 400,000 of the token in tx oWNTxW..PGwK.
   7 g6  ~ 2026-10-11 06:00:00Z       CHAIN_BLOCK         Liquidity was removed from pool 5Au11f..1a49 (liquidity 30,000 USD as reported).
   8 g6  ~ 2026-10-11 07:00:00Z       CANDLE              Pool liquidity fell 40% to 30,000 USD between 2026-10-11 06:00:00Z and 2026-10-11 07:00:00Z (fixture-candles (INVENTED)).
   9 g7    2026-10-11 09:00:00Z       CANDLE              Price fell 31% between 2026-10-11 05:00:00Z and 2026-10-11 09:00:00Z (candle closes, fixture-candles (INVENTED)).

Observed patterns
  TRADE_BEFORE_TALK [INFERENCE, order CONFIDENT] post x:1900000000000000101 trade fyYNUQ..i8Mn
  TALK_BEFORE_TRADE [INFERENCE, order CONFIDENT] post x:1900000000000000101 trade oWNTxW..PGwK
  POTENTIAL_DISTRIBUTION_DURING_PROMOTION [INFERENCE, order CONFIDENT] post x:1900000000000000101 trade oWNTxW..PGwK: A wallet associated with the source sold after its bullish post and while the post was recent. This is an observed sequence. Intent, the source's total holding and any coordination are not established.

Fact
  - The source posted about the token in x:1900000000000000101, stance LONG (platform timestamp, 1 s precision) at 2026-10-11 02:00:00Z.  [https://example.invalid/fixture/status/1900000000000000101; x:1900000000000000101; fx-obs-1900000000000000101-1]
... (20 more lines)
```

## 11 social and on-chain chronology: indeterminate order

```
$ python -m memelab social chrono run --input tests/fixtures/social/chrono/indeterminate.json
exit 0 (expected 0), 0.7 s
INVENTED FIXTURE DATA: no real post, wallet, token or person.
Chronology for solana:S5vznK6GJNtHJWH66MPdNBLHGx35G7HyS5vznK6GJNtH (LABCAT, symbol shown for reading only)
Source: FIXTURE source A (invented)   evaluated as of 2026-10-12 08:00:00Z   window 2026-10-08 01:59:59Z to 2026-10-12 08:00:00Z
Order between posts and trades: INDETERMINATE

Clocks: SOURCE_PUBLICATION is the platform's time for a post; CHAIN_BLOCK is the block time of a transaction; COLLECTION is when the lab saw the post. Entries in the same group overlap in time and their order is not established.

Timeline
   1 g1  ~ no later than 2026-10-11 03:00:05Z SOURCE_PUBLICATION  The source posted about the token in x:1900000000000000202, stance LONG (publication time unknown; published no later than the lab's first sighting).
   2 g1  ~ 2026-10-11 02:00:00Z       SOURCE_PUBLICATION  The source posted about the token in x:1900000000000000201, stance LONG (platform timestamp, 60 s precision).
   3 g1  ~ 2026-10-11 02:00:25Z       CHAIN_BLOCK         ut3Tma..zF3E (a wallet linked to the source) bought 800,000 of the token in tx m9WBmK..aDzf.
   4 g1  ~ 2026-10-11 02:00:50Z       CHAIN_BLOCK         ut3Tma..zF3E (a wallet linked to the source) sold 300,000 of the token in tx fk1o2B..ABsA.
   5 g1  ~ 2026-10-11 02:01:30Z       COLLECTION          The lab first saw post x:1900000000000000201 (collector clock).
   6 g1  ~ 2026-10-11 03:00:00Z       COLLECTION          The lab first saw post x:1900000000000000202 (collector clock).

Observed patterns
  ORDER_INDETERMINATE [UNKNOWN, order INDETERMINATE] post x:1900000000000000201 trade m9WBmK..aDzf
  ORDER_INDETERMINATE [UNKNOWN, order INDETERMINATE] post x:1900000000000000201 trade fk1o2B..ABsA
  ORDER_INDETERMINATE [UNKNOWN, order INDETERMINATE] post x:1900000000000000202 trade m9WBmK..aDzf
  ORDER_INDETERMINATE [UNKNOWN, order INDETERMINATE] post x:1900000000000000202 trade fk1o2B..ABsA
  POTENTIAL_DISTRIBUTION_DURING_PROMOTION [HEURISTIC, order INDETERMINATE] post x:1900000000000000201 trade fk1o2B..ABsA: A wallet associated with the source sold close to its bullish post; whether the sale came after the post is not established. This is an observed sequence. Intent, the source's total holding and any coordination are not established.

Fact
  - The source posted about the token in x:1900000000000000201, stance LONG (platform timestamp, 60 s precision) at 2026-10-11 02:00:00Z.  [https://example.invalid/fixture/status/1900000000000000201; x:1900000000000000201; fx-obs-1900000000000000201-1]
  - The lab first saw x:1900000000000000201 90 s after its publication time.  [https://example.invalid/fixture/status/1900000000000000201; x:1900000000000000201; fx-obs-1900000000000000201-1]
... (23 more lines)
```

## 12 main discovery integration: scout before/after (opt-in)

```
$ python -m memelab social research demo --fixture tests/fixtures/social/research/scout_before_after.json
exit 0 (expected 0), 0.7 s
# Phase 13 fixture: scout report before and after social research candidates

Invented tokens and findings. The scout lists and the report body come from the real scout code; the social section is appended.
Report body unchanged by the social layer: yes.

| Token | Score | Status | Scout list | Score after | Status after | Narrative attention | Research state |
|---|---|---|---|---|---|---|---|
| GOODCAT | 68 | WATCH | serious | same | same | CORROBORATED | RESEARCH_CANDIDATE |
| HYPEDOG | 0 | REJECTED | rejected | same | same | CORROBORATED | REJECTED_STRUCTURE |
| TOPPICK | 0 | REJECTED | rejected | same | same | CORROBORATED | REJECTED_STRUCTURE |
| OLDRUG | 0 | REJECTED | rejected | same | same | NONE | NO_SOCIAL_SIGNAL |
| SLOWFROG | 48 | RESEARCH REQUIRED | near miss | same | same | STALE | RESEARCH_CANDIDATE |
| GOODCAT (other contract) | not analyzed | not analyzed | not listed | n/a | n/a | EMERGING | NEEDS_STRUCTURAL_ANALYSIS |
| $MOONX (ticker only) | n/a | n/a | not listed | n/a | n/a | UNRESOLVED | never ranked |

## Before: social off

# Opportunity Scout report — 2026-10-12 12:00 UTC

## Market environment

- Fixture: invented tokens and findings (tests/fixtures/social/research)
- Best token vs best trade: Best token by score is GOODCAT (68), but no candidate qualifies as a trade: none combine a defined invalidation, exit capacity and an EV estimate.

## #1 GOODCAT — Goodcat (invented)
... (132 more lines)
```

## 12 integration policy (off by default, zero execution impact)

```
$ python -m memelab social research policy
exit 0 (expected 0), 0.7 s
{
 "corroborated_min_independent": 2,
 "enabled": false,
 "include_fixtures": false,
 "max_age_hours": 48.0,
 "policy_version": "default-1",
 "provenance": {
  "override_keys": [],
  "path": null,
  "sha256": "d12f1a160fc4b631cb8cdabb309a034d68fb3523e244911de3d92162eee1597e",
  "source": "default"
 },
 "schema": "memelab.social.research.policy/1",
 "signals": {
  "chronology_flags": true,
  "narratives": true
 },
 "trade_execution_impact": "none",
 "weights": {
  "confidence": {
   "HIGH": 3.0,
   "LOW": 1.0,
   "MODERATE": 2.0,
   "UNKNOWN": 0.0
  },
... (6 more lines)
```

## 13 report generation: brief, digest, feed on the fixture store

```
$ python -m memelab social feed-demo --fixture tests/fixtures/social/feed/demo_day.json
exit 0 (expected 0), 0.9 s
# Phase 14 sample: social intelligence feed on an invented fixture

FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.

Reproduce: `python -m memelab social feed-demo --fixture tests/fixtures/social/feed/demo_day.json`

The fixture is written into a throwaway SQLite store through the real store functions, snapshotted by the real narrative engine and read back by the same read path the lab database uses. Section headings below are shifted one level down.

## View 1: morning brief

## Morning brief: social narratives, last 24 hours

FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.

As of 2026-10-13 08:00 EDT (12:00 UTC). Window: 2026-10-12 08:00 EDT (12:00 UTC) to 2026-10-13 08:00 EDT (12:00 UTC) (24 h).
Data: narrative snapshot run 2 (2026-10-13 UTC), cutoff 2026-10-13 08:00 EDT (12:00 UTC), 0.0 h old, FRESH.
Coverage: telegram COVERED 1; x COVERED 1.
Not clustered: 3 token not resolved to a contract.
Model: not used (status on this machine: not checked in the fixture demo). The feed is built from stored structure only.

### High priority

#### GOODCAT on solana (B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY)

- Priority: HIGH (HEURISTIC, orders this report only): 3 independent sources, fresh.
... (203 more lines)
```

## 13 report generation: brief on the e2e store (real read path)

```
$ python -m memelab social brief --db $TMP/e2e.sqlite --as-of 2026-10-13T00:00:00+00:00 --tz America/New_York --include-fixtures
exit 0 (expected 0), 0.7 s
# Morning brief: social narratives, last 24 hours

FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.

As of 2026-10-12 20:00 EDT (2026-10-13 00:00 UTC). Window: 2026-10-11 20:00 EDT (2026-10-12 00:00 UTC) to 2026-10-12 20:00 EDT (2026-10-13 00:00 UTC) (24 h).
Data: narrative snapshot run 2 (2026-10-10 UTC), cutoff 2026-10-10 20:00 EDT (2026-10-11 00:00 UTC), 48.0 h old, STALE (older than 24 h).
Coverage: no coverage record (volumes not estimable).
Not clustered: 4 token not resolved to a contract.
Model: not used (status on this machine: model\_not\_configured). The feed is built from stored structure only.

No supported high-priority observations. Reason: no fresh, adequately covered narrative with two or more independent sources or a chronology risk flag in the window.

## Older or weakly covered

### theme animal

- Priority: LOW (HEURISTIC, orders this report only): no activity inside the window.
- What happened: 1 post(s) about the theme animal from 1 account(s): independence not estimable, 0 repeat(s) (reposts, forwards, quotes that repeat) and 0 reply or copy item(s). Claim types among originals: bullish 1.
- First observed 2026-10-09 23:01 EDT (2026-10-10 03:01 UTC); first published 2026-10-09 23:00 EDT (2026-10-10 03:00 UTC); last observed 2026-10-09 23:01 EDT (2026-10-10 03:01 UTC).
- Who said it: [example\_poster (x)](<https://x.com/example_poster/status/1900000000000000002>) (independent original, 2026-10-09 23:00 EDT (2026-10-10 03:00 UTC), stance positive).
- Independence vs repetition: not estimable; 0 reply or copy item(s); 0 repeat(s) of an unseen original.
- Why it matters (HEURISTIC): new in this snapshot.
- Corroborated: Nothing: independence could not be estimated.
- Speculation: 1 of 1 original claim(s) are opinion, prediction or question.
- Reasons to doubt: Coverage is insufficient: no\_coverage\_record:x. Counts are lower bounds (partial coverage). Narrative confidence UNKNOWN. Stale: newest observation 69.0 h before as of.
... (14 more lines)
```

## 14 alert dry run on the fixture day, deduped second run

```
$ python -m memelab social alerts demo --fixture tests/fixtures/social/alerts/alerts_day.json
exit 0 (expected 0), 0.9 s
# Phase 15 sample: research alerts on an invented fixture

FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.

Reproduce: `python -m memelab social alerts demo --fixture tests/fixtures/social/alerts/alerts_day.json`

Dry run with the local file sink only, in a throwaway state file. Run 2 reads a later snapshot that carries the same evidence.

## Run 1

```
Alert run 1 (dry_run), 2026-10-13 08:00 EDT (2026-10-13 12:00 UTC), policy alerts-policy-v1 6d5d61ff4a80
FIXTURE DEMO: invented data, not live alerts.
Outcome: evaluated
Candidates 4, new alerts 4, deduped 0, suppressed 5
  suppressed wallet_corroboration GOODCAT on solana (B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY): stale_event (wallet event behind DISCLOSED_POSITION_CONSISTENT_OLD is older than 24.0 h or undated)
  suppressed convergence HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ): below_threshold (2 independent source(s), policy needs 3)
  suppressed conversation_growth HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ): no_baseline (0 earlier snapshot(s) recorded, policy needs 3)
  suppressed convergence theme ai_agent: below_threshold (2 independent source(s), policy needs 3)
  suppressed convergence SLOWFROG on solana (6DntXA18w931KFERa8e2VvvazqQA4hJp6DntXA18w931): stale_source (the newest observation for this item is older than the freshness limit)
Dry run: previews only. Nothing was sent.
```

### Alert text

... (120 more lines)
```

## 14 alert dry run on the e2e store

```
$ python -m memelab social alerts run --db $TMP/e2e.sqlite --as-of 2026-10-13T12:00:00+00:00 --state $TMP/alerts_dry.sqlite --outbox $TMP/outbox
exit 0 (expected 0), 0.7 s
Alert run 1 (dry_run), 2026-10-13 08:00 EDT (2026-10-13 12:00 UTC), policy alerts-policy-v1 56edda8e78d1
Outcome: evaluated
Candidates 0, new alerts 0, deduped 0, suppressed 0
No alerts today.
Dry run: previews only. Nothing was sent.
```

## 14 alert send without consent is refused

```
$ python -m memelab social alerts run --db $TMP/e2e.sqlite --as-of 2026-10-13T13:30:00+00:00 --send --state $TMP/alerts_send.sqlite --outbox $TMP/outbox
exit 2 (expected 2), 0.7 s

--- stderr
alerts: --send refused: the private alert config does not set notifications_opt_in and send_enabled to true. Run without --send for a dry run.
```

## 15 forward outcome evaluation (ledger before and after two runs)

```
$ python -m memelab social evaluate demo --fixture tests/fixtures/social/outcomes/outcomes_fixture.json
exit 0 (expected 0), 1.3 s
# Phase 16 sample: signal ledger and forward evaluation on an invented fixture

FIXTURE DEMO: invented signals, tokens, references, prices and times. This is not live data and not a trade record.

Reproduce: `python -m memelab social evaluate demo --fixture tests/fixtures/social/outcomes/outcomes_fixture.json`

Throwaway ledger. Five signals are recorded at emission (emitted, rejected and suppressed alike), then evaluated twice: at 2026-10-13T19:00:00Z and at 2026-10-14T14:00:00Z, with new and revised price observations arriving in between. Positions are hypothetical (500 USD evaluation size, not a recommendation).

Recorded: 5 signal(s), refused 0.

## Signal snapshot before evaluation (sig_9f7fd7b580400fddd0c87400)

context body sha256 0777c37f26a6e4b6272118c21238ebcc2446af2dc35d8efb7839707beb25bb9b

```json
{
 "assumptions": {
  "direction": "LONG",
  "execution_lag_s": 300,
  "fee_bps_per_side": 100.0,
  "horizons_s": [
   3600,
   21600,
   86400,
   259200,
... (228 more lines)
```

## 16 causal replay on the synthetic world

```
$ python -m memelab social replay demo
exit 0 (expected 0), 42.0 s
# Historical replay of research signals against matched controls

FIXTURE DEMO: a synthetic, seeded world. Tokens, sources, posts, wallets, trending lists and prices are invented. Nothing here is evidence about any real token or source, and nothing is a trade record.

Reproduce: `python -m memelab social replay demo`

Synthetic world with planted pumps, informative and noise posts, reposts, ingest duplicates, leakage canaries (posts published before a pump but first available after it), a huge winner, delisted and illiquid tokens, revised candles and a source that sells right after posting.

What kind of evidence this is: a historical replay (backtest) on stored data, run with a causal cutoff clock. It is not a forward test. Signals whose inputs the lab actually captured at decision time are counted separately (test split, primary horizon: 30); outcome prices are provider history in every case. Positions are hypothetical (Phase 16 evaluation size); nothing here is a trade instruction.

## Data and coverage

label synthetic world seed 17; fixture: yes; coverage version synthetic-17-v1; engine replay-v1, rules replay-rules-v1

data clock ends 2026-08-31T00:00:00Z; input sha256 2cea0be1c2ec5a2a; policy sha256 b204fc4086786dc0

```
posts 1289 (reposts 573, content duplicates 0), wallet events 119, trending entries 2300
market observations 220632 on 79 tokens; tokens known 79
excluded candles: AFTER_DATA_END x75
excluded posts: AFTER_DATA_END x2, DUPLICATE_POST_ID x10
universe: every invented token, delisted ones included; includes delisted tokens: True
provider synth-candles: kind PRICE, publication lag 120 s, window 2026-08-01T00:00:00Z to 2026-08-31T00:00:00Z
provider synth-social: kind SOCIAL, publication lag None s, window 2026-08-01T00:00:00Z to 2026-08-31T00:00:00Z
provider synth-trending: kind TRENDING, publication lag 60 s, window 2026-08-02T00:00:00Z to 2026-08-31T00:00:00Z
... (126 more lines)
```

## 16 causal replay on real stored history (copy of the tracked database)

```
$ python -m memelab social replay run --db $TMP/tracked_copy.sqlite
exit 0 (expected 0), 0.6 s
# Historical replay of research signals against matched controls

Real stored history. Where coverage is poor the verdict is 'insufficient sample/data' or 'cannot validate yet'; nothing is extrapolated beyond the data.

What kind of evidence this is: a historical replay (backtest) on stored data, run with a causal cutoff clock. It is not a forward test. Signals whose inputs the lab actually captured at decision time are counted separately (test split, primary horizon: 0); outcome prices are provider history in every case. Positions are hypothetical (Phase 16 evaluation size); nothing here is a trade instruction.

## Data and coverage

label lab database tracked_copy.sqlite; fixture: no; coverage version real-cd007e51702a; engine replay-v1, rules replay-rules-v1

data clock ends 2026-10-07T00:16:35Z; input sha256 87de06437513bda3; policy sha256 b204fc4086786dc0

```
posts 0 (reposts 0, content duplicates 0), wallet events 0, trending entries 0
market observations 33 on 8 tokens; tokens known 8
universe: only tokens the lab's runs happened to fetch; delisted tokens are not tracked; includes delisted tokens: False
provider lab-snapshot:merged: kind PRICE, publication lag None s, window 2026-10-06T23:48:23Z to 2026-10-07T00:16:35Z
```

## Result

INSUFFICIENT_DATA for all four strategies: no social, wallet or trending evidence with a usable availability time. Nothing was estimated and nothing is extrapolated.

## Leakage check (truncation invariance)

... (12 more lines)
```

## 17 no credentials: X API health

```
$ python -m memelab social x-health --db $TMP/e2e.sqlite
exit 1 (expected 1), 0.6 s
{
 "adapter": "x_api",
 "config": null,
 "connector_health": [],
 "contract_verified": "2026-10-10",
 "credentials": "missing",
 "cursors": [],
 "live_evidence": {
  "last_request_at": null,
  "requests": 0,
  "successful": 0,
  "verdict": "none: no live X API read has been made"
 },
 "network_calls_made": 0,
 "next_step": "authorize: see docs/social-intelligence/X_API_03.md, then export X_BEARER_TOKEN in the shell that runs memelab",
 "spend_this_month_usd": {
  "live": 0
 },
 "status": "credentials_missing",
 "token_env": "X_BEARER_TOKEN"
}
```

## 17 no credentials: live X ingest refuses before any call

```
$ python -m memelab social x-ingest --db $TMP/e2e.sqlite
exit 1 (expected 1), 0.7 s
{
 "network_calls_made": 0,
 "next_step": "authorize: see docs/social-intelligence/X_API_03.md, then export X_BEARER_TOKEN in the shell that runs memelab",
 "reason": "credentials_missing",
 "status": "NOT_RUN"
}
```

## 17 no credentials: Telegram health

```
$ python -m memelab social tg-health --db $TMP/e2e.sqlite
exit 1 (expected 1), 0.7 s
{
 "adapter": "telegram_bot",
 "bot_api_version_seen": "10.3",
 "channels": [],
 "connector_health": [],
 "contract_verified": "2026-10-11",
 "credentials": "missing",
 "live_evidence": {
  "last_request_at": null,
  "requests": 0,
  "successful_polls": 0,
  "verdict": "none: no live Telegram Bot API read has been made"
 },
 "network_calls_made": 0,
 "next_step": "create a bot with @BotFather and export TELEGRAM_BOT_TOKEN in the shell that runs memelab (docs/social-intelligence/TELEGRAM_04.md, 'How to authorize it')",
 "status": "credentials_missing",
 "token_env": "TELEGRAM_BOT_TOKEN",
 "update_cursor": null,
 "webhook_secret": "missing"
}
```

## 17 no credentials: live Telegram ingest refuses before any call

```
$ python -m memelab social tg-ingest --db $TMP/e2e.sqlite
exit 1 (expected 1), 0.7 s
{
 "network_calls_made": 0,
 "next_step": "create a bot with @BotFather and export TELEGRAM_BOT_TOKEN in the shell that runs memelab (docs/social-intelligence/TELEGRAM_04.md, 'How to authorize it')",
 "reason": "credentials_missing",
 "status": "NOT_RUN"
}
```

## 17 no credentials: Helius key status

```
$ python -m memelab.secrets status
exit 1 (expected 1), 0.0 s
{"helius_key": "missing", "source": "none"}
```

## 17 no credentials: alert spend preflight

```
$ python -m memelab social alerts preflight --db $TMP/e2e.sqlite
exit 0 (expected 0), 0.8 s
Paid-API spend for UTC day 2026-10-23 against per-provider daily ceilings:
  x_api: spent 0 USD, ceiling 0.0 USD, refresh SKIPPED (spend ledger present)
  llm: spent 0 USD, ceiling 0.0 USD, refresh SKIPPED (spend ledger present)
  telegram_bot: spent 0 USD, ceiling 0.0 USD, refresh allowed (spend ledger present)
```

## 18 content guard over every tracked file

```
$ python -m memelab social guard
exit 0 (expected 0), 1.2 s
{
 "allowlist": [
  {
   "path": "tests/fixtures/social/inbox/soc_fx01.json",
   "reason": "invented placeholder the ingester must quarantine (test_bad_items_quarantined_good_items_kept)",
   "where": "soc:x:example_trader_a.body.items[3].text"
  },
  {
   "path": "tests/fixtures/social/inbox/soc_fx01.json",
   "reason": "invented PROTECTED item (hash of an invented sentence) the ingester must quarantine as NOT_PUBLIC",
   "where": "soc:x:example_trader_a.body.items[4].visibility"
  },
  {
   "path": "tests/fixtures/social/registry/leaderboard_fresh.json",
   "reason": "invented placeholder the registry importer must reject as BLOCKED_CONTENT_KEY (Phase 08)",
   "where": "rows[6].bio"
  },
  {
   "path": "tests/fixtures/social/discord_bot/fx_discord_gateway.json",
   "reason": "invented GUILD_CREATE member entry for the bot itself (its role ids), needed to compute its channel permissions (Phase 20)",
   "where": "connections[0].frames[2].d.members"
  },
  {
   "path": "tests/fixtures/social/roundtrip_01.json",
   "reason": "invented sentences used to prove the store hashes text and never writes it (Phase 01)",
... (18 more lines)
```

## 19 Reddit fixture: ingest approved community, extract claims in memory, purge deleted items

```
$ python -m memelab social reddit-ingest --config tests/fixtures/social/reddit_api/fx_reddit_config.json --fixture tests/fixtures/social/reddit_api/fx_reddit_main.json --extract --bodies tests/fixtures/social/resolve/fx_providers.json --db $TMP/reddit.sqlite --now 1791676800
exit 0 (expected 0), 0.8 s
{
 "budget": {
  "max_cost": null,
  "max_items": null,
  "max_units": null,
  "pace_seconds": 0.0,
  "used": {
   "cost": 0.0,
   "items": 8,
   "units": 4
  }
 },
 "counts": {
  "budget_stopped": 0,
  "created": 8,
  "duplicates": 0,
  "items_seen": 8,
  "quarantined": 0,
  "stale_items": 0,
  "units": 4,
  "units_failed": 0,
  "units_ok": 4,
  "units_rejected": 0,
  "units_replayed": 0,
  "units_unavailable": 0
... (45 more lines)
```

## 19 Reddit fixture: second run (cursor, recheck, deletion and account deletion, purge)

```
$ python -m memelab social reddit-ingest --config tests/fixtures/social/reddit_api/fx_reddit_config.json --fixture tests/fixtures/social/reddit_api/fx_reddit_second.json --db $TMP/reddit.sqlite --now 1791763200
exit 0 (expected 0), 0.8 s
{
 "budget": {
  "max_cost": null,
  "max_items": null,
  "max_units": null,
  "pace_seconds": 0.0,
  "used": {
   "cost": 0.0,
   "items": 7,
   "units": 3
  }
 },
 "counts": {
  "budget_stopped": 0,
  "created": 5,
  "duplicates": 2,
  "items_seen": 7,
  "quarantined": 0,
  "stale_items": 0,
  "units": 3,
  "units_failed": 0,
  "units_ok": 3,
  "units_rejected": 0,
  "units_replayed": 0,
  "units_unavailable": 0
... (30 more lines)
```

## 19 Reddit fixture: narrative snapshot and brief

```
$ python -m memelab social narrative-snapshot --day 2026-10-10 --tz UTC --db $TMP/reddit.sqlite --now 1791680400 && python -m memelab social brief --db $TMP/reddit.sqlite --as-of 2026-10-11T01:00:00+00:00 --tz UTC --include-fixtures
exit 0 (expected 0), 1.5 s
{
 "created": true,
 "report": [
  "Narrative snapshot 1: window 2026-10-10 UTC (1791590400 to 1791676800 UTC epoch), cutoff 1791676800, complete, engine narr-v1.",
  "1 cluster(s) from 3 claim(s). Compared with: none (first comparable snapshot).",
  "Contains fixture data (not live provider data).",
  "- LABDOG (solana 8CyKBG..tgkJ) [ca:solana:8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ]: ok, confidence LOW, 3 mention(s) in window, independent sources 1, amplifiers 0, dependent 1, fresh.",
  "Changes since the previous snapshot: 1 NEW."
 ],
 "run_id": 1,
 "summary": {
  "changes": {
   "NEW": 1
  },
  "clusters": 1,
  "compared_to": "none (first comparable snapshot)",
  "highlights": [],
  "insufficient_coverage": [],
  "new": [
   "ca:solana:8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ"
  ],
  "prev_run_id": null
 },
 "unassigned": {
  "claims_by_reason": {},
... (38 more lines)
```

## 19 Farcaster fixture: ingest fid and channel, recasts, extract claims in memory

```
$ python -m memelab social fc-ingest --config tests/fixtures/social/farcaster_hub/fx_fc_config.json --fixture tests/fixtures/social/farcaster_hub/fx_fc_main.json --extract --bodies tests/fixtures/social/resolve/fx_providers.json --db $TMP/farcaster.sqlite --now 1791676800
exit 0 (expected 0), 0.9 s
{
 "budget": {
  "max_cost": null,
  "max_items": null,
  "max_units": null,
  "pace_seconds": 0.0,
  "used": {
   "cost": 0.0,
   "items": 6,
   "units": 7
  }
 },
 "counts": {
  "budget_stopped": 0,
  "created": 6,
  "duplicates": 0,
  "items_seen": 6,
  "quarantined": 0,
  "stale_items": 0,
  "units": 7,
  "units_failed": 0,
  "units_ok": 7,
  "units_rejected": 0,
  "units_replayed": 0,
  "units_unavailable": 0
... (41 more lines)
```

## 19 Farcaster fixture: narrative snapshot and brief

```
$ python -m memelab social narrative-snapshot --day 2026-10-10 --tz UTC --db $TMP/farcaster.sqlite --now 1791680400 && python -m memelab social brief --db $TMP/farcaster.sqlite --as-of 2026-10-11T01:00:00+00:00 --tz UTC --include-fixtures
exit 0 (expected 0), 1.6 s
{
 "created": true,
 "report": [
  "Narrative snapshot 1: window 2026-10-10 UTC (1791590400 to 1791676800 UTC epoch), cutoff 1791676800, complete, engine narr-v1.",
  "1 cluster(s) from 2 claim(s). Compared with: none (first comparable snapshot).",
  "Contains fixture data (not live provider data).",
  "- LABDOG (solana 8CyKBG..tgkJ) [ca:solana:8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ]: ok, confidence MODERATE, 2 mention(s) in window, independent sources 2, amplifiers 0, dependent 0, fresh.",
  "Changes since the previous snapshot: 1 NEW."
 ],
 "run_id": 1,
 "summary": {
  "changes": {
   "NEW": 1
  },
  "clusters": 1,
  "compared_to": "none (first comparable snapshot)",
  "highlights": [],
  "insufficient_coverage": [],
  "new": [
   "ca:solana:8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ"
  ],
  "prev_run_id": null
 },
 "unassigned": {
  "claims_by_reason": {},
... (36 more lines)
```

## 19 no credentials: Reddit health

```
$ python -m memelab social reddit-health --db $TMP/e2e.sqlite
exit 1 (expected 1), 1.0 s
{
 "adapter": "reddit_api",
 "config": null,
 "connector_health": [],
 "contract_verified": "2026-10-12",
 "cost": "free tier: 100 queries per minute per OAuth client, non-commercial use only; estimated $0 per request",
 "credential_env": [
  "REDDIT_CLIENT_ID",
  "REDDIT_CLIENT_SECRET"
 ],
 "credentials": "missing",
 "cursors": [],
 "deletion_purge_pending_items": 0,
 "live_evidence": {
  "last_request_at": null,
  "requests": 0,
  "successful": 0,
  "verdict": "none: no live Reddit read has been made"
 },
 "network_calls_made": 0,
 "next_step": "write the community config (docs/social-intelligence/reddit_api.example.json) to data/private/reddit_api.json",
 "requests_this_month": 0,
 "status": "not_configured"
}
```

## 19 no credentials: live Reddit ingest refuses before any call

```
$ python -m memelab social reddit-ingest --db $TMP/e2e.sqlite
exit 1 (expected 1), 0.8 s
{
 "network_calls_made": 0,
 "next_step": "write the community config (docs/social-intelligence/reddit_api.example.json) to data/private/reddit_api.json",
 "reason": "not_configured",
 "status": "NOT_RUN"
}
```

## 19 not configured: Farcaster health

```
$ python -m memelab social fc-health --db $TMP/e2e.sqlite
exit 1 (expected 1), 0.6 s
{
 "adapter": "farcaster_hub",
 "config": null,
 "connector_health": [],
 "contract_verified": "2026-10-12",
 "cost": "self-hosted node: no per-request charge (your own server and bandwidth)",
 "credentials": "not_needed",
 "cursors": [],
 "live_evidence": {
  "est_cost_usd_total": 0,
  "last_request_at": null,
  "requests": 0,
  "successful": 0,
  "verdict": "none: no live Farcaster read has been made"
 },
 "network_calls_made": 0,
 "next_step": "run a Snapchain node (free, self-hosted) or choose a hosted hub, then write data/private/farcaster_hub.json from docs/social-intelligence/farcaster_hub.example.json with hub.base_url and scopes",
 "status": "not_configured"
}
```

## 19 not configured: live Farcaster ingest refuses before any call

```
$ python -m memelab social fc-ingest --db $TMP/e2e.sqlite
exit 1 (expected 1), 0.7 s
{
 "network_calls_made": 0,
 "next_step": "run a Snapchain node (free, self-hosted) or choose a hosted hub, then write data/private/farcaster_hub.json from docs/social-intelligence/farcaster_hub.example.json with hub.base_url and scopes",
 "reason": "not_configured",
 "status": "NOT_RUN"
}
```

## 19 every social connector: status, cost, next step

```
$ python -m memelab social sources --db $TMP/e2e.sqlite
exit 0 (expected 0), 0.9 s
{
 "connectors": [
  {
   "connector": "x_api",
   "cost": {
    "live": 0
   },
   "credentials": "missing",
   "live_requests": 0,
   "live_verdict": "none: no live X API read has been made",
   "next_step": "authorize: see docs/social-intelligence/X_API_03.md, then export X_BEARER_TOKEN in the shell that runs memelab",
   "status": "credentials_missing"
  },
  {
   "connector": "telegram_bot",
   "cost": null,
   "credentials": "missing",
   "live_requests": 0,
   "live_verdict": "none: no live Telegram Bot API read has been made",
   "next_step": "create a bot with @BotFather and export TELEGRAM_BOT_TOKEN in the shell that runs memelab (docs/social-intelligence/TELEGRAM_04.md, 'How to authorize it')",
   "status": "credentials_missing"
  },
  {
   "connector": "reddit_api",
   "cost": "free tier: 100 queries per minute per OAuth client, non-commercial use only; estimated $0 per request",
... (36 more lines)
```

## 20 Discord fixture: consented channel over REST, role-gated and history-less channels refused, extract claims in memory

```
$ python -m memelab social discord-ingest --config tests/fixtures/social/discord_bot/fx_discord_config.json --fixture tests/fixtures/social/discord_bot/fx_discord_main.json --extract --bodies tests/fixtures/social/resolve/fx_providers.json --db $TMP/discord.sqlite --now 1791676800
exit 0 (expected 0), 0.9 s
{
 "budget": {
  "max_cost": null,
  "max_items": null,
  "max_units": null,
  "pace_seconds": 0.0,
  "used": {
   "cost": 0.0,
   "items": 9,
   "units": 4
  }
 },
 "counts": {
  "budget_stopped": 0,
  "created": 9,
  "duplicates": 0,
  "items_seen": 9,
  "quarantined": 0,
  "stale_items": 0,
  "units": 4,
  "units_failed": 0,
  "units_ok": 2,
  "units_rejected": 0,
  "units_replayed": 0,
  "units_unavailable": 2
... (59 more lines)
--- stderr
{"connector": "discord_bot:channel:1080278730670080007", "error": "not_public: the channel is hidden from @everyone (role-gated); not read", "event": "unit_unavailable", "run_id": "discord_fixture_20261011_000000_e34c0c", "source_ref": "discord_bot:channel:1080278730670080007#access", "status": "BLOCKED"}
{"connector": "discord_bot:channel:1080278982328320008", "error": "access_denied: the bot lacks READ_MESSAGE_HISTORY in this channel", "event": "unit_unavailable", "run_id": "discord_fixture_20261011_000000_e34c0c", "source_ref": "discord_bot:channel:1080278982328320008#access", "status": "BLOCKED"}
```

## 20 Discord fixture: narrative snapshot and brief

```
$ python -m memelab social narrative-snapshot --day 2026-10-10 --tz UTC --db $TMP/discord.sqlite --now 1791680400 && python -m memelab social brief --db $TMP/discord.sqlite --as-of 2026-10-11T01:00:00+00:00 --tz UTC --include-fixtures
exit 0 (expected 0), 1.4 s
{
 "created": true,
 "report": [
  "Narrative snapshot 1: window 2026-10-10 UTC (1791590400 to 1791676800 UTC epoch), cutoff 1791676800, complete, engine narr-v1.",
  "1 cluster(s) from 6 claim(s). Compared with: none (first comparable snapshot).",
  "Contains fixture data (not live provider data).",
  "- LABDOG (solana 8CyKBG..tgkJ) [ca:solana:8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ]: ok, confidence MODERATE, 6 mention(s) in window, independent sources 2, amplifiers 1, dependent 1, fresh.",
  "Changes since the previous snapshot: 1 NEW."
 ],
 "run_id": 1,
 "summary": {
  "changes": {
   "NEW": 1
  },
  "clusters": 1,
  "compared_to": "none (first comparable snapshot)",
  "highlights": [],
  "insufficient_coverage": [],
  "new": [
   "ca:solana:8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ"
  ],
  "prev_run_id": null
 },
 "unassigned": {
  "claims_by_reason": {},
... (36 more lines)
```

## 20 Discord fixture: second run (cursor, recheck, edit, deletion, purge)

```
$ python -m memelab social discord-ingest --config tests/fixtures/social/discord_bot/fx_discord_config.json --fixture tests/fixtures/social/discord_bot/fx_discord_second.json --db $TMP/discord.sqlite --now 1791763200
exit 0 (expected 0), 0.7 s
{
 "budget": {
  "max_cost": null,
  "max_items": null,
  "max_units": null,
  "pace_seconds": 0.0,
  "used": {
   "cost": 0.0,
   "items": 10,
   "units": 13
  }
 },
 "counts": {
  "budget_stopped": 0,
  "created": 3,
  "duplicates": 7,
  "items_seen": 10,
  "quarantined": 0,
  "stale_items": 0,
  "units": 13,
  "units_failed": 0,
  "units_ok": 11,
  "units_rejected": 0,
  "units_replayed": 0,
  "units_unavailable": 2
... (45 more lines)
--- stderr
{"connector": "discord_bot:channel:1080278730670080007", "error": "not_public: the channel is hidden from @everyone (role-gated); not read", "event": "unit_unavailable", "run_id": "discord_fixture_20261012_000000_f67fb2", "source_ref": "discord_bot:channel:1080278730670080007#access", "status": "BLOCKED"}
{"connector": "discord_bot:channel:1080278982328320008", "error": "access_denied: the bot lacks READ_MESSAGE_HISTORY in this channel", "event": "unit_unavailable", "run_id": "discord_fixture_20261012_000000_f67fb2", "source_ref": "discord_bot:channel:1080278982328320008#access", "status": "BLOCKED"}
```

## 20 Discord fixture: gateway pass (duplicates, resume, out-of-order, delete, permission revocation)

```
$ python -m memelab social discord-gateway --config tests/fixtures/social/discord_bot/fx_discord_config.json --fixture tests/fixtures/social/discord_bot/fx_discord_gateway.json --extract --bodies tests/fixtures/social/resolve/fx_providers.json --db $TMP/discord.sqlite --now 1791849600
exit 0 (expected 0), 0.8 s
{
 "budget": {
  "max_cost": null,
  "max_items": null,
  "max_units": null,
  "pace_seconds": 0.0,
  "used": {
   "cost": 0.0,
   "items": 5,
   "units": 3
  }
 },
 "counts": {
  "budget_stopped": 0,
  "created": 5,
  "duplicates": 0,
  "items_seen": 5,
  "quarantined": 0,
  "stale_items": 0,
  "units": 3,
  "units_failed": 0,
  "units_ok": 1,
  "units_rejected": 0,
  "units_replayed": 0,
  "units_unavailable": 2
... (47 more lines)
--- stderr
{"connector": "discord_bot:channel:1080278479011840006", "error": "access_denied: the bot lacks VIEW_CHANNEL in this channel", "event": "unit_unavailable", "run_id": "discord_gw_fixture_20261013_000000_6a6f96", "source_ref": "discord_bot:channel:1080278479011840006#gateway-blocked@1791847800", "status": "BLOCKED"}
{"connector": "discord_bot:channel:1080278730670080007", "error": "not_public: the channel is hidden from @everyone (role-gated); not read", "event": "unit_unavailable", "run_id": "discord_gw_fixture_20261013_000000_6a6f96", "source_ref": "discord_bot:channel:1080278730670080007#gateway-blocked@1791847800", "status": "BLOCKED"}
```

## 20 Discord fixture: gateway closes 4014, privileged intent missing is reported

```
$ python -m memelab social discord-gateway --config tests/fixtures/social/discord_bot/fx_discord_config.json --fixture tests/fixtures/social/discord_bot/fx_discord_gateway_4014.json --db $TMP/discord_4014.sqlite --now 1791849600
exit 1 (expected 1), 0.7 s
{
 "budget": {
  "max_cost": null,
  "max_items": null,
  "max_units": null,
  "pace_seconds": 0.0,
  "used": {
   "cost": 0.0,
   "items": 0,
   "units": 1
  }
 },
 "counts": {
  "budget_stopped": 0,
  "created": 0,
  "duplicates": 0,
  "items_seen": 0,
  "quarantined": 0,
  "stale_items": 0,
  "units": 1,
  "units_failed": 0,
  "units_ok": 0,
  "units_rejected": 0,
  "units_replayed": 0,
  "units_unavailable": 1
... (23 more lines)
--- stderr
{"connector": "discord_bot:gateway:memelab-research", "error": "privileged_intent_missing: gateway closed 4014 (disallowed intents); enable Message Content Intent on the Bot page or run with require_message_content false", "event": "unit_unavailable", "run_id": "discord_gw_fixture_20261013_000000_8f0951", "source_ref": "discord_bot:gateway:memelab-research#close@1791847800", "status": "BLOCKED"}
```

## 20 Discord fixture: reset one channel checkpoint

```
$ python -m memelab social discord-reset --channel 1080278479011840006 --db $TMP/discord.sqlite
exit 0 (expected 0), 0.6 s
{
 "connector": "discord_bot:channel:1080278479011840006",
 "had_cursor": true,
 "previous_newest_id": "1558856702361600211"
}
```

## 20 not configured: Discord health

```
$ python -m memelab social discord-health --db $TMP/e2e.sqlite
exit 1 (expected 1), 0.6 s
{
 "adapter": "discord_bot",
 "blocked_channels": [],
 "config": null,
 "connector_health": [],
 "contract_verified": "2026-10-12",
 "cost": "free: Discord's bot API has no per-request charge; 50 requests per second per bot; estimated $0 per request",
 "credential_env": [
  "DISCORD_BOT_TOKEN"
 ],
 "credentials": "missing",
 "cursors": [],
 "deletion_purge_pending_items": 0,
 "gateway_last_status": null,
 "live_evidence": {
  "last_request_at": null,
  "requests": 0,
  "successful": 0,
  "verdict": "none: no live Discord read has been made"
 },
 "message_content_intent": "unknown: no run has checked the application flags",
 "network_calls_made": 0,
 "next_step": "write the server and channel config (docs/social-intelligence/discord_bot.example.json) to data/private/discord_bot.json",
 "status": "not_configured"
}
```

## 20 not configured: live Discord ingest refuses before any call

```
$ python -m memelab social discord-ingest --db $TMP/e2e.sqlite
exit 1 (expected 1), 0.6 s
{
 "network_calls_made": 0,
 "next_step": "write the server and channel config (docs/social-intelligence/discord_bot.example.json) to data/private/discord_bot.json",
 "reason": "not_configured",
 "status": "NOT_RUN"
}
```

## 20 no live gateway transport: Discord gateway refuses before any call

```
$ python -m memelab social discord-gateway --db $TMP/e2e.sqlite
exit 1 (expected 1), 0.8 s
{
 "network_calls_made": 0,
 "next_step": "the live gateway needs a websocket client that this repo does not ship; use `social discord-ingest` (REST) for live reads",
 "reason": "gateway_transport_not_shipped",
 "status": "NOT_RUN"
}
```

## 21 YouTube fixture: channels and videos (metadata), licensed and owner-caption transcript snippets, extract claims in memory

```
$ python -m memelab social youtube-ingest --config tests/fixtures/social/youtube_data/fx_youtube_config.json --fixture tests/fixtures/social/youtube_data/fx_youtube_run1.json --extract --bodies tests/fixtures/social/resolve/fx_providers.json --db $TMP/youtube.sqlite --now 1791676800
exit 0 (expected 0), 0.8 s
{
 "budget": {
  "max_cost": null,
  "max_items": null,
  "max_units": null,
  "pace_seconds": 0.0,
  "used": {
   "cost": 0.0,
   "items": 12,
   "units": 11
  }
 },
 "counts": {
  "budget_stopped": 0,
  "created": 12,
  "duplicates": 0,
  "items_seen": 12,
  "quarantined": 0,
  "stale_items": 0,
  "units": 11,
  "units_failed": 0,
  "units_ok": 8,
  "units_rejected": 0,
  "units_replayed": 0,
  "units_unavailable": 3
... (100 more lines)
--- stderr
{"attempt": 1, "delay_s": 1.0, "error": "TransientError", "event": "retry", "of": 3, "what": "youtube playlist_items"}
{"connector": "youtube_data:transcript:licensed_file", "error": "timestamp_drift: 1 of 4 cues start after the media length plus 30 s and were dropped", "event": "unit_unavailable", "run_id": "youtube_fixture_20261011_000000_3221bf", "source_ref": "youtube_data:transcript:licensed_file#video=fxVideo02bB&drift", "status": "DEGRADED"}
{"connector": "youtube_data:transcript:licensed_file", "error": "language_uncertain: transcript language es differs from the audio language en; a translation is not what was said, so it was not used", "event": "unit_unavailable", "run_id": "youtube_fixture_20261011_000000_3221bf", "source_ref": "youtube_data:transcript:licensed_file#video=fxVideo07gG&language", "status": "DEGRADED"}
{"connector": "youtube_data:transcript:captions_api", "error": "not_permitted: the OAuth account cannot edit this video, so its captions are not available to the lab (403 forbidden; The permissions associated with the request are not sufficient to download the c)", "event": "unit_unavailable", "run_id": "youtube_fixture_20261011_000000_3221bf", "source_ref": "youtube_data:transcript:captions_api#video=fxVideo08hH&list", "status": "BLOCKED"}
```

## 21 YouTube fixture: narrative snapshot and brief

```
$ python -m memelab social narrative-snapshot --day 2026-10-10 --tz UTC --db $TMP/youtube.sqlite --now 1791680400 && python -m memelab social brief --db $TMP/youtube.sqlite --as-of 2026-10-11T01:00:00+00:00 --tz UTC --include-fixtures
exit 0 (expected 0), 1.4 s
{
 "created": true,
 "report": [
  "Narrative snapshot 1: window 2026-10-10 UTC (1791590400 to 1791676800 UTC epoch), cutoff 1791676800, complete, engine narr-v1.",
  "2 cluster(s) from 7 claim(s). Compared with: none (first comparable snapshot).",
  "Contains fixture data (not live provider data).",
  "- LABDOG (solana 8CyKBG..tgkJ) [ca:solana:8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ]: ok, confidence MODERATE, 3 mention(s) in window, independent sources 2, amplifiers 0, dependent 0, fresh.",
  "- NOPOOL (solana urqBcc..JA5v) [ca:solana:urqBccf819k8ttGdxBnfxDfRR7yH62RJxww3QnxJA5v]: ok, confidence MODERATE, 3 mention(s) in window, independent sources 2, amplifiers 0, dependent 0, fresh.",
  "Changes since the previous snapshot: 2 NEW.",
  "Not clustered: 1 event time after window end, 1 token not resolved to a contract."
 ],
 "run_id": 1,
 "summary": {
  "changes": {
   "NEW": 2
  },
  "clusters": 2,
  "compared_to": "none (first comparable snapshot)",
  "highlights": [],
  "insufficient_coverage": [],
  "new": [
   "ca:solana:8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ",
   "ca:solana:urqBccf819k8ttGdxBnfxDfRR7yH62RJxww3QnxJA5v"
  ],
  "prev_run_id": null
... (66 more lines)
```

## 21 YouTube fixture: second run (archived livestream transcript, delayed captions, refresh, removed video purged)

```
$ python -m memelab social youtube-ingest --config tests/fixtures/social/youtube_data/fx_youtube_config.json --fixture tests/fixtures/social/youtube_data/fx_youtube_run2.json --extract --bodies tests/fixtures/social/resolve/fx_providers.json --db $TMP/youtube.sqlite --now 1791763200
exit 0 (expected 0), 0.8 s
{
 "budget": {
  "max_cost": null,
  "max_items": null,
  "max_units": null,
  "pace_seconds": 0.0,
  "used": {
   "cost": 0.0,
   "items": 13,
   "units": 7
  }
 },
 "counts": {
  "budget_stopped": 0,
  "created": 12,
  "duplicates": 1,
  "items_seen": 13,
  "quarantined": 0,
  "stale_items": 0,
  "units": 7,
  "units_failed": 0,
  "units_ok": 7,
  "units_rejected": 0,
  "units_replayed": 0,
  "units_unavailable": 0
... (81 more lines)
```

## 21 YouTube fixture: daily quota exceeded stops the run until midnight Pacific Time

```
$ python -m memelab social youtube-ingest --config tests/fixtures/social/youtube_data/fx_youtube_config.json --fixture tests/fixtures/social/youtube_data/fx_youtube_quota.json --db $TMP/youtube_quota.sqlite --now 1791676800
exit 1 (expected 1), 0.7 s
{
 "budget": {
  "max_cost": null,
  "max_items": null,
  "max_units": null,
  "pace_seconds": 0.0,
  "used": {
   "cost": 0.0,
   "items": 0,
   "units": 4
  }
 },
 "counts": {
  "budget_stopped": 0,
  "created": 0,
  "duplicates": 0,
  "items_seen": 0,
  "quarantined": 0,
  "stale_items": 0,
  "units": 4,
  "units_failed": 0,
  "units_ok": 0,
  "units_rejected": 0,
  "units_replayed": 0,
  "units_unavailable": 4
... (58 more lines)
--- stderr
{"connector": "youtube_data:channels:resolve", "error": "quota_exceeded: daily quota used up (quotaExceeded); resets 2026-10-11T07:00:00.000000Z (midnight Pacific Time)", "event": "unit_unavailable", "run_id": "youtube_fixture_20261011_000000_39acda", "source_ref": "youtube_data:channels:resolve#ids", "status": "RATE_LIMITED"}
{"connector": "youtube_data:channel:UCfxLongAnalyst00000001A", "error": "not run: quota_exceeded: daily quota used up (quotaExceeded); resets 2026-10-11T07:00:00.000000Z (midnight Pacific Time)", "event": "unit_unavailable", "run_id": "youtube_fixture_20261011_000000_39acda", "source_ref": "youtube_data:channel:UCfxLongAnalyst00000001A#not-run", "status": "DEGRADED"}
{"connector": "youtube_data:channel:@fx_long_analyst", "error": "not run: quota_exceeded: daily quota used up (quotaExceeded); resets 2026-10-11T07:00:00.000000Z (midnight Pacific Time)", "event": "unit_unavailable", "run_id": "youtube_fixture_20261011_000000_39acda", "source_ref": "youtube_data:channel:@fx_long_analyst#not-run", "status": "DEGRADED"}
{"connector": "youtube_data:channel:@fx_second_show", "error": "not run: quota_exceeded: daily quota used up (quotaExceeded); resets 2026-10-11T07:00:00.000000Z (midnight Pacific Time)", "event": "unit_unavailable", "run_id": "youtube_fixture_20261011_000000_39acda", "source_ref": "youtube_data:channel:@fx_second_show#not-run", "status": "DEGRADED"}
```

## 21 YouTube fixture: 30-day expiry purge

```
$ python -m memelab social youtube-purge --db $TMP/youtube.sqlite --now 1794441600
exit 0 (expected 0), 0.7 s
{
 "expired": {
  "claims_cleared": 35,
  "items_purged": 13,
  "observations_cleared": 20,
  "private_rows_deleted": 0,
  "videos_past_retention": 9
 },
 "gone": {
  "claims_cleared": 0,
  "items_purged": 0,
  "observations_cleared": 0,
  "private_rows_deleted": 0
 }
}
```

## 21 not configured: YouTube health

```
$ python -m memelab social youtube-health --db $TMP/e2e.sqlite
exit 1 (expected 1), 0.7 s
{
 "adapter": "youtube_data",
 "config": null,
 "connector_health": [],
 "contract_verified": "2026-10-13",
 "cost": "no charge; quota 10,000 units per day (PT): channels, playlistItems and videos 1 unit per call, captions.list 50, captions.download 200; search.list not used",
 "credential_env": [
  "YOUTUBE_API_KEY",
  "YOUTUBE_OAUTH_TOKEN"
 ],
 "credentials": "missing",
 "cursors": [],
 "live_evidence": {
  "last_request_at": null,
  "requests": 0,
  "successful": 0,
  "verdict": "none: no live YouTube read has been made"
 },
 "network_calls_made": 0,
 "next_step": "write the channel config (docs/social-intelligence/youtube_data.example.json) to data/private/youtube_data.json",
 "oauth_token": "missing",
 "quota_reset_at": null,
 "quota_used_today_pt": 0,
 "retention": {
  "past_retention_unpurged": 0,
... (5 more lines)
```

## 21 not configured: live YouTube ingest refuses before any call

```
$ python -m memelab social youtube-ingest --db $TMP/e2e.sqlite
exit 1 (expected 1), 0.7 s
{
 "network_calls_made": 0,
 "next_step": "write the channel config (docs/social-intelligence/youtube_data.example.json) to data/private/youtube_data.json",
 "reason": "not_configured",
 "status": "NOT_RUN"
}
```

## FC catalyst feed fixture: ingest a result file kept outside the inbox

```
$ python -m memelab catalyst ingest --file tests/fixtures/catalyst/firecrawl/feed_fx01.json
exit 0 (expected 0), 0.7 s
{
 "items_new": 4,
 "items_seen": 0,
 "events_new": 3,
 "events_corroborated": 1,
 "events_resurfaced": 0,
 "sources_ok": [
  "news:cointelegraph",
  "news:decrypt",
  "news:gnews:memecoin",
  "news:theblock"
 ],
 "sources_failed": [],
 "access_changes": []
}
touched events: [1, 2, 3]
```

## FC catalyst Firecrawl fixture: news search for other publishers of stored stories, ingested as corroboration

```
$ python -m memelab catalyst fc-search --config tests/fixtures/catalyst/firecrawl/config.json --fixture tests/fixtures/catalyst/firecrawl/fx_search.json --events 5
exit 0 (expected 0), 0.6 s
{
 "already_stored": 1,
 "credits": 4,
 "kept": 1,
 "queries": 2,
 "refused_host": 1,
 "results": 3,
 "stopped": null
}
{
 "items_new": 1,
 "items_seen": 0,
 "events_new": 0,
 "events_corroborated": 1,
 "events_resurfaced": 0,
 "sources_ok": [
  "web:firecrawl:search"
 ],
 "sources_failed": []
}
```

## FC catalyst Firecrawl fixture: read article pages (robots.txt, refused hosts, hashes and identifiers only)

```
$ python -m memelab catalyst enrich --config tests/fixtures/catalyst/firecrawl/config.json --fixture tests/fixtures/catalyst/firecrawl/fx_enrich.json
exit 0 (expected 0), 0.7 s
{
 "already_read": 0,
 "credits": 2,
 "duplicate_url": 0,
 "empty": 0,
 "facts": 7,
 "mode": "fixture",
 "not_relevant": 0,
 "ok": 2,
 "private_copies": 2,
 "provider_failed": 0,
 "recent_failure": 0,
 "refused_host": 0,
 "requests": 2,
 "robots_disallowed": 1,
 "robots_unreachable": 2,
 "run_id": "fce_20261023T204150Z_5607",
 "site_refused_robots": 0,
 "stopped": null,
 "target_http_error": 0,
 "targets": 5
}
# next: python -m memelab catalyst match-plan --id catm_<stamp>  (contracts named on pages are searched by address)
```

## FC catalyst Firecrawl fixture: second read adds nothing and makes no request

```
$ python -m memelab catalyst enrich --config tests/fixtures/catalyst/firecrawl/config.json --fixture tests/fixtures/catalyst/firecrawl/fx_enrich.json
exit 0 (expected 0), 0.7 s
{
 "already_read": 2,
 "credits": 0,
 "duplicate_url": 0,
 "empty": 0,
 "facts": 0,
 "mode": "fixture",
 "not_relevant": 0,
 "ok": 0,
 "private_copies": 0,
 "provider_failed": 0,
 "recent_failure": 3,
 "refused_host": 0,
 "requests": 0,
 "robots_disallowed": 0,
 "robots_unreachable": 0,
 "run_id": "fce_20261023T204151Z_5611",
 "site_refused_robots": 0,
 "stopped": null,
 "target_http_error": 0,
 "targets": 0
}
# next: python -m memelab catalyst match-plan --id catm_<stamp>  (contracts named on pages are searched by address)
```

## FC not configured: Firecrawl health

```
$ python -m memelab catalyst fc-health
exit 1 (expected 1), 0.7 s
{
 "config": "$TMP/clone/data/private/firecrawl.json",
 "contract_verified": "2026-10-22",
 "credits_this_month_live": 0,
 "detail": "no config file; copy docs/catalyst/firecrawl.example.json to $TMP/clone/data/private/firecrawl.json",
 "key": "missing",
 "key_source": null,
 "last_live_ok_at": null,
 "provider": "firecrawl",
 "status": "config_missing"
}
```

## FC not configured: live Firecrawl enrich refuses before any call

```
$ python -m memelab catalyst enrich
exit 1 (expected 1), 0.7 s
{"result": "NOT_RUN", "reason": "config_missing", "detail": "no config file; copy docs/catalyst/firecrawl.example.json to $TMP/clone/data/private/firecrawl.json"}
```

## FC not configured: live Firecrawl search refuses before any call

```
$ python -m memelab catalyst fc-search --events 3
exit 1 (expected 1), 0.6 s
{"result": "NOT_RUN", "reason": "config_missing", "detail": "no config file; copy docs/catalyst/firecrawl.example.json to $TMP/clone/data/private/firecrawl.json"}
```
