# Phase 15: controlled research alerts and scheduling

Prompt 15, 2026-10-12. Code: `memelab/social/alerts_core.py` (policies and candidates, pure), `memelab/social/alerts_engine.py` (private state, dedupe, cooldown, cap, quiet hours, delivery, ledger), `memelab/social/alerts_transport.py` (file sink, Telegram, email, private config), `memelab/social/alerts_schedule.py` (daily and weekly templates, time zone and DST rules), `memelab/social/alerts_cli.py` (commands). Feed additions in `memelab/social/feed_core.py`. Tests: `tests/test_social_alerts.py` (28). Fixture: `tests/fixtures/social/alerts/` (`make_alerts.py` builds `alerts_day.json` from the Phase 14 feed fixture; `sample_run.md` is the CLI output). Decisions D-097 to D-104.

## What it does

Alerts read the Phase 14 feed document (`memelab.social.feed/1`) and nothing else. They are not another detector: every condition is a field the feed already computed. Nothing reaches a score, a watchlist, a rejection or a trade (`trade_execution_impact: none`, policy keys that would reach them are refused).

The feed items gained three things (schema name kept, D-098): `activity.window_mentions`, `chronology` (Phase 12 flags with category, bucket, attribution, time, rule and run) and, on each stance change, `source_id`, `before_at` and `after_at`. The Phase 14 sample report changed only in its printed `feed_sha256`.

## Policies

Defaults in `alerts_core.DEFAULT_POLICY` (schema `memelab.social.alerts.policy/1`, version `alerts-policy-v1`). Overrides go in the private config under `policy`. Thresholds are HEURISTIC, not calibrated.

| Policy | Fires when | Severity | Cooldown | Token-specific |
|---|---|---|---|---|
| convergence | 3 or more independent sources (status ok), 2 or more of them registry-linked traders or on the `reputable_sources` allowlist; bots and aggregators never count; follower counts never read | notice | 12 h per item | no |
| wallet_corroboration | a Phase 12 CORROBORATION flag on a LINKED wallet, event no older than 24 h | notice | 12 h per item | yes |
| risk | a Phase 12 RISK flag no older than 48 h, or NO_SELL_ROUTE in the newest exit check | warning | 6 h per item and flag | yes |
| stance_switch | a registry-linked source moves from positive to negative, mixed or neutral, newer statement no older than 48 h | notice | 24 h per item and source | yes |
| conversation_growth | window mentions at least 10 and at least 3x the median of the item's own earlier snapshots (3 to 14 points), with 2 or more independent sources | info | 24 h per item | no |

Every candidate needs FRESH feed data (snapshot no older than 24 h) and a FRESH item observed within 24 h. Token-specific policies also need a readable chain and contract; otherwise the candidate is suppressed as `missing_token`. Every suppression is stored and printed with a reason code: `missing_token`, `stale_source`, `stale_event`, `unverified_wallet`, `not_reputable`, `below_threshold`, `insufficient_coverage`, `no_baseline`, `repetition_only`, `cooldown`, `daily_cap`.

Each alert carries severity, reason, confidence, evidence bucket, evidence, provenance (feed sha, narrative run, cluster key, claim ids, chronology runs, market fact ids, snapshot window), freshness, policy version and sha, a dedupe key and a cooldown key.

## Spam control

- Dedupe key: sha of policy, item and the evidence fingerprint (reputable sources; flag, source and time; stance pair and time; snapshot window for growth; the literal NO_SELL_ROUTE). A key alerts once per mode within the 30-day retention.
- Cooldown per policy and item (risk also per flag, stance per source). `social alerts reset-cooldown --key K --reason R` ends one early and is recorded.
- Daily cap: 8 alerts per local calendar day in America/New_York, all policies together, highest severity first.
- Quiet hours 22:00 to 07:00 New York wall time (follows DST). New alerts are held, released on the first run after 07:00, and expire unsent after 14 h. No severity bypasses quiet hours by default.
- No evaluation more often than every 60 minutes (the policy refuses less), and none when the feed carries a snapshot this mode already evaluated (`no_new_upstream_data`). Delivery retries still run.

## Delivery

- File sink (always): one text file per alert in the outbox (default `data/private/alerts_outbox/`, gitignored). `preview/` in dry run, `sent/` in send mode. A file is never reported as a delivery to a device.
- Telegram (optional): one bot, one chat, plain text with no parse mode. Token from `MEMELAB_ALERT_TELEGRAM_TOKEN` only; chat id from `MEMELAB_ALERT_TELEGRAM_CHAT_ID` or the private config.
- Email (optional): SMTP with STARTTLS; password from `MEMELAB_ALERT_SMTP_PASSWORD` only.
- Dry run is the default. Sending needs `--send` and both `notifications_opt_in` and `send_enabled` set to true in the private config (`data/private/alerts.json`, example `docs/social-intelligence/alerts.example.json`). A config that holds a token, password, secret or key is refused, naming the key and never the value.
- Missing credentials: the remote transport is absent, the run says "not_configured ... nothing sent through it", and the file sink still works.
- Fixture alerts never go to a remote transport.
- Ledger (`alert_deliveries`): one row per attempt, `attempted` written and committed before the call, closed as `succeeded` or `failed`. An attempt left open by a crash becomes `outcome_unknown` and is never resent (at most once). Retryable failures (network, 5xx, 429 with its `retry_after`) are retried on later runs after 5 min, 30 min, 2 h, up to 4 attempts; 401, 403 and other 4xx are not retried. Destinations are stored as a 12-character hash. Errors are redacted (bot tokens, bearer tokens, the configured secrets).
- Per-provider daily cost ceilings: transports (`file`, `telegram`, `email`, all 0 USD per message today) and upstream paid APIs (`x_api`, `llm` at 0 USD, so no paid refresh; `telegram_bot` free). `social alerts preflight` reads live `social_api_spend` rows for the UTC billing day and says which refresh step may run.

State lives in a private SQLite file (default `data/private/alerts.sqlite`, override `MEMELAB_ALERT_DB` or `--state`), never in the tracked database (refused in code). Dry run and send keep separate state, so a dry run never uses up a real alert's dedupe key.

## Scheduling

`alerts_schedule.TEMPLATES` holds a daily template (07:47 New York, `CRON_TZ=America/New_York 47 7 * * *`: preflight, snapshot when allowed, `alerts run --slot daily --send`) and a weekly one (Monday 08:13: status and a dry run). Both are `enabled: false`. Nothing was scheduled in this phase. Turning one on means creating a scheduled task after Elving agrees and the private config is in place. The repo has no GitHub Actions workflow and none was added: a public repo's Actions would need the delivery secrets as repository secrets and would keep state outside the private file.

Rules: a local time in the spring-forward gap runs once at the first valid minute after it; a time that occurs twice in the fall-back hour runs once at the first occurrence. Each run has a slot key (local date, ISO week for weekly); a finished slot is a no-op, a slot started less than 2 h ago is skipped, an older unfinished one is taken over. Templates may not run more often than hourly.

## Commands

```
python -m memelab social alerts run [--db PATH | --feed-json FILE | --fixture SPEC] [--as-of T] [--send] [--slot daily|weekly] [--state PATH] [--config PATH] [--outbox DIR] [--json]
python -m memelab social alerts status [--mode dry_run|send] [--state PATH] [--json]
python -m memelab social alerts reset-cooldown --key KEY --reason TEXT [--mode send|dry_run]
python -m memelab social alerts schedule [--template daily|weekly] [--after T] [--count N]
python -m memelab social alerts preflight [--db PATH] [--now T]
python -m memelab social alerts demo --fixture tests/fixtures/social/alerts/alerts_day.json
```

## Proof

- Fixture-generated alert and deduped second run: `tests/fixtures/social/alerts/sample_run.md`, reproduced byte for byte by `python -m memelab social alerts demo --fixture tests/fixtures/social/alerts/alerts_day.json` (`test_fixture_alert_deduped_second_run_and_sample_reproduced`). Run 1: 4 new alerts (two risk, one convergence, one wallet corroboration) and 5 suppressions with reasons, including a stale linked-wallet event. Run 2 on a later snapshot with the same evidence: 0 new, 4 deduped. Delivery state: 4 dry-run previews, 0 messages delivered to a device.
- Tracked database: `python -m memelab social alerts run --as-of 2026-10-13T12:00:00+00:00 --state <scratch>` exit 0, outcome `feed_unavailable (social tables not present in this database (social schema not migrated))`, "Nothing was sent."

## Test list (prompt items)

| Prompt item | Test |
|---|---|
| duplicate alert across retries | `test_duplicate_alert_across_retries_and_new_snapshots`, `test_interrupted_send_is_never_resent` |
| cooldown reset | `test_cooldown_blocks_new_evidence_until_it_expires_or_is_reset` |
| 100 reposts and no independent corroboration | `test_hundred_reposts_without_independent_corroboration_raise_nothing` |
| stale wallet event | `test_stale_wallet_event_is_suppressed_and_fresh_linked_one_alerts` |
| repeated schedule after restart | `test_repeated_schedule_slot_after_restart_is_a_no_op` |
| missing token | `test_missing_token_blocks_token_specific_alerts` |
| notification transport failure | `test_notification_transport_failure_retry_and_honest_state`, `test_telegram_transport_maps_responses_and_redacts_the_token`, `test_email_transport_uses_injected_smtp_and_classifies_errors` |
| timezone/DST changes | `test_dst_schedule_quiet_hours_and_local_day` |
| no-alert day | `test_no_alert_day` |

Also: quiet-hour hold, release and expiry; daily cap, minimum interval and same snapshot; dry run vs send state; fixtures never remote; cost ceiling; consent and secret refusal; missing credentials; trading keys refused; stance switch rules; stale feed and bots; alert text has provenance and no markup; state refused in the tracked database; CLI no-op on a database without social tables; preflight; the example config.

## Known limits

- NO_SELL_ROUTE alerts once per item within the 30-day retention: if a route returns and disappears again inside that time, the second loss is not alerted (the feed keeps no history of route status).
- "Reputable" means registry-linked or on Elving's allowlist. The registry has no reviewed identity check yet (C-13), so a registry link is a research label, not proof of who runs the account.
- Thresholds are defaults chosen by hand, not tuned on live data. There is no live data.
- The Telegram and email transports were tested only with fakes. No message was sent.
