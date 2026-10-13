# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md), [IDENTITY_05.md](IDENTITY_05.md), [CLAIMS_06.md](CLAIMS_06.md), [NARRATIVES_07.md](NARRATIVES_07.md), [REGISTRY_08.md](REGISTRY_08.md), [WALLETS_09.md](WALLETS_09.md), [PERFORMANCE_10.md](PERFORMANCE_10.md), [ALPHA_11.md](ALPHA_11.md), [CHRONOLOGY_12.md](CHRONOLOGY_12.md), [INTEGRATION_13.md](INTEGRATION_13.md), [REPORTS_14.md](REPORTS_14.md), [ALERTS_15.md](ALERTS_15.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 15 (Prompt 15: controlled research alerts and scheduling), 2026-10-12. Prompt 15 took the Phase 15 slot; the old proposed Phase 15 (trader call capture) is now carry-over C-15 (D-097).
- Model status: unchanged, none configured (D-036). Alerts never call a model.
- Data status: no live post, wallet fetch or candle source was used. The tracked database has no social tables, so a real `social alerts run` today exits 0 with outcome `feed_unavailable (social tables not present in this database (social schema not migrated))`. Every alert in this phase came from invented, watermarked fixtures or synthetic feed documents in tests.
- Delivery status: no transport is configured, no message was sent to any device, no scheduled job was created or enabled. The Telegram and email transports were tested with fakes only.
- Next phase: 16 as proposed in ROADMAP.md (now depends on C-15), or a carry-over, unless Elving supplies Prompt 16. Not started.
- Active branch: `feature/social-intelligence`.
- Phase 15 started from `67b5f81` ("social-intel phase 14: record commit and push route in handoff"), the commit on the remote branch. No drift. Baseline `python -m pytest tests -q --deselect tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`: `565 passed, 1 deselected`, matching the Phase 14 handoff (`1 failed, 565 passed` with the C-1 test included).
- No migration in this phase. Public schema stays at 12. Alert state is a separate private SQLite file.

## What Phase 15 added

- `memelab/social/alerts_core.py` (pure): policy schema `memelab.social.alerts.policy/1` with defaults and validation (trading keys refused, interval at least 60 min, `trade_execution_impact: none`), `candidates()` for the five policies with suppression reasons, quiet-hour and local-day helpers, plain-text rendering.
- `memelab/social/alerts_engine.py`: private state (`data/private/alerts.sqlite`, `MEMELAB_ALERT_DB`; the tracked database is refused), runs, dedupe per mode, cooldowns and resets, daily cap, quiet-hour hold, release and expiry, growth baselines, delivery with at-most-once ledger and retry backoff, schedule slots, readable run and state output.
- `memelab/social/alerts_transport.py`: file sink, Telegram bot transport (plain text), SMTP email transport, private config `memelab.social.alerts.config/1` (refused if it holds a secret), env-only secrets, redaction, destination hashing.
- `memelab/social/alerts_schedule.py`: disabled daily (07:47) and weekly (Monday 08:13) America/New_York templates, DST gap and fold rules, slot keys.
- `memelab/social/alerts_cli.py`: `social alerts run|status|reset-cooldown|schedule|preflight|demo`. Registered in `memelab/social/cli.py`.
- `memelab/social/feed_core.py`: feed items gained `activity`, `chronology` and stance-change times (schema name kept, D-098). `tests/fixtures/social/feed/sample_report.md` regenerated; only its three printed `feed_sha256` values changed.
- Tests: `tests/test_social_alerts.py` (28). Fixture: `tests/fixtures/social/alerts/` (`make_alerts.py` builds `alerts_day.json` from the Phase 14 fixture; `sample_run.md` is the demo output, checked byte for byte).
- Docs: `ALERTS_15.md`, `alerts.example.json`, DECISIONS D-097 to D-104, ROADMAP (15 DONE, C-15 added, 16, 19 and 20 notes), SOURCE_COVERAGE.

## Gate, item by item

- No alert spam: dedupe key once per mode (`test_duplicate_alert_across_retries_and_new_snapshots`), cooldowns (`test_cooldown_blocks_new_evidence_until_it_expires_or_is_reset`), daily cap 8 per New York day, 60-minute interval and no re-evaluation of the same snapshot (`test_daily_cap_and_min_interval_and_same_snapshot`), quiet hours with hold, release and expiry (`test_quiet_hours_hold_release_and_expiry`), 100 reposts raise nothing (`test_hundred_reposts_without_independent_corroboration_raise_nothing`).
- Explicit configured delivery: `--send` needs `notifications_opt_in` and `send_enabled` true in the private config, else exit 2; a config holding a secret is refused; remote transports exist only with env credentials; fixtures never go remote (`test_send_needs_consent_and_config_never_holds_secrets`, `test_fixture_alerts_never_go_to_a_remote_transport`). Previews and local files are never reported as deliveries (`test_dry_run_and_send_keep_separate_state_and_previews_are_not_deliveries`, `test_notification_transport_failure_retry_and_honest_state`).
- Works under missing credentials via dry run: the default mode; on the tracked database exit 0 with "Nothing was sent." (`test_cli_live_run_on_a_database_without_social_tables_is_a_no_op`).
- Fixture-generated alert, deduped second run and readable delivery state: `tests/fixtures/social/alerts/sample_run.md`, reproduced by `python -m memelab social alerts demo --fixture tests/fixtures/social/alerts/alerts_day.json` (exit 0). Run 1: 4 new alerts, 5 suppressions with reasons. Run 2: 0 new, 4 deduped. State: 4 dry-run previews, 0 messages delivered to a device.
- Prompt test list, each a named test: see ALERTS_15.md "Test list".
- Job templates exist and are not enabled (`enabled: false`); no scheduled task and no GitHub Actions workflow was created.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change: exit 1, `1 failed, 593 passed`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched).
- `python -m pytest tests/test_social_alerts.py -q` -> `28 passed`.
- `python -m memelab social guard` exit 0 (0 violations).
- Commands run on the tracked database: `social alerts run --as-of 2026-10-13T12:00:00+00:00 --state <scratch>` exit 0 (`feed_unavailable`), `social alerts status --state <scratch>` exit 0 ("No alerts recorded."), `social alerts schedule --after 2026-10-30T12:00:00+00:00 --count 3` exit 0 (07:47 EDT = 11:47 UTC, then 07:47 EST = 12:47 UTC from 1 Nov), `social alerts preflight --now 2026-10-13T12:00:00+00:00` exit 0 (x_api and llm SKIPPED at a 0 USD ceiling, telegram_bot allowed, spend ledger absent).
- The EVM test still writes `data/reports/<stamp>_BRETT_*.md`; deleted by hand after each run (C-1). `git status` clean after that.

## Things the next phase should know

- Alerts read only `memelab.social.feed/1`. Fields added to feed items must keep their meaning or bump the schema name.
- To turn alerts on for real: create `data/private/alerts.json` from `docs/social-intelligence/alerts.example.json`, set `notifications_opt_in` and `send_enabled` to true, enable one transport, put `MEMELAB_ALERT_TELEGRAM_TOKEN` (and chat id) or `MEMELAB_ALERT_SMTP_PASSWORD` in the environment, run `social alerts run --send` once by hand, then create a scheduled task from `alerts_schedule.TEMPLATES["daily"]`. All of that is Elving's decision.
- "Reputable" depends on registry trader links (unreviewed identity until C-13) or the allowlist in the private config.
- NO_SELL_ROUTE alerts once per item within 30 days (see ALERTS_15.md "Known limits").

## Helius key

The key is not in the repo and must never be committed. Code reads it through `memelab/secrets.py`, in this order:

1. The `HELIUS_API_KEY` environment variable. Use this for a scheduled run, CI or a cloud session (set it as a secret there).
2. `helius_api_key` in `data/config.json`. That file is gitignored. On a machine, create it with `python -m memelab.secrets set` (prompts without echo).

Check with `python -m memelab.secrets status` (prints "set" or "missing" and the source, never the value). A new session that needs the key should ask Elving to supply it (it is not stored in memory or project docs). The key was pasted into a chat once; rotate it if that chat is shared.

## Blockers and open decisions

- Push: the session's own `git push` is not used. Working route: Elving's GitHub connection in Composio, Git Data API (blobs, trees, commits, fast-forward of the feature branch ref, no force, D-001).
- No live posts, wallet fetches or candle provider in session; the tracked database has no social schema.
- No alert transport configured and no consent recorded; enabling delivery or a scheduled job is Elving's call.
- C-1 (the clock-dependent catalyst test) keeps the full suite from being fully green.
- D-025, D-028, D-023 and D-036 remain open.
- Phase prompts 16 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 593 passed` and `python -m memelab social guard` exit 0.

## Commit and push

Phase 15 code commit on `feature/social-intelligence`: `098d2be4c3bd00d48d95a0390b2db807ff894142` (tree 8800ce7f0e0e3661efa9172fc204734415bd8cbe, parent 67b5f8113b7ac9932432121de8ef602272b99b0f). This handoff is the commit on top of it.

The push went through Composio and the GitHub Git Data API: the diff against 67b5f81 went over as a checksummed xz patch in two chunks (each chunk and the reassembled patch checked by sha256), was applied to the six base files fetched at 67b5f81 (their blob shas checked first), all 17 blob shas were checked against the local files, the tree sha matched the local tree before the commit was created, and the branch ref was moved forward once, without force. `main` was not touched. The local commit was then reset to the remote one (same tree, different author metadata).

Phase 16 is not started.
