# Alert rule matrix (alerts-rules-1, Phase 18)

Research alerts over the persisted predictive state. Code: `memelab/predictive/reports.py` (`make_alert_policy`, `alert_candidates`, `alert_run`, `render_alert_text`). Pre-registration: `../ACCEPTANCE_CHECKLIST.md` rules 9 to 11, PI-D-098. Tests: `tests/test_predictive_reports.py` (G8, G12 to G14, and the repair-pass-2 tests `test_rp2_*`). Repair pass 2 (CP18-2, PI-D-102) changed the rules marked CP18-2 below.

Delivery is dry run only. `--send` is refused with "no external delivery is approved (PI-D-005)", and no transport other than the local file sink is ever built. A preview file in the outbox is not a delivery; the state view says so ("Nothing has been sent to a device").

## Policies

| Policy | Severity | Fires when | Does not fire when | Cooldown key (hours) | Dedupe fingerprint | Bucket |
|---|---|---|---|---|---|---|
| risk_override | warning | an attempted request with any item of its risk list (CP18-2): lab fatal flags (`FATAL_FLAGS`), an unknown fatal-flag check (`FATAL_CHECK_UNKNOWN`), a backtest veto (`BACKTEST_VETO`), a liquidity fall of 20% or more since the previous attempt of the mint (`LIQUIDITY_FALL_20PCT_OR_MORE`), liquidity that became unknown (`LIQUIDITY_BECAME_UNKNOWN`), or a newer snapshot of the mint that was deferred or failed and carries fatal flags or an unknown check (`NEWER_SNAPSHOT_NOT_ASSESSED`); also a newer snapshot of that kind on its own | an empty risk list; a newer snapshot whose recorded fatal flags are empty | `risk_override:chain:mint` (6) | snapshot hash and the named parts | FACT |
| reevaluate | notice; warning for the drawdown target T2 | a FORECAST verified under rule 1 (record, stored point, cards), level SHADOW or VALIDATED_EXPERIMENTAL, interval lower bound above its base rate | an abstention; a refused document; level ABSTAIN; interval reaching the base rate; any item of the risk list on the snapshot: the number is withheld and the candidate is suppressed RISK_OVERRIDES_FORECAST (CP18-2) | `reevaluate:chain:mint:target` (12) | forecast id | INFERENCE |
| forecast_withdrawn | notice | a target with a verified FORECAST in the previous attempt of the mint abstains or is refused in the newest attempt | no earlier verified FORECAST; a target whose number is withheld by a risk (the risk warning carries it) | `forecast_withdrawn:chain:mint:target` (12) | earlier and newer forecast ids | FACT |
| pipeline_health | warning for STATE_TAMPERED and STATE_CHECK_FAILED; notice otherwise | the state fails its checks; an ERROR event in a new pass; MODEL_STALE, DRIFT_ALERT or REGISTRY_UNAVAILABLE among a target's blocking states at the pass; FEED_CHANGED (CP18-2: the pass this alert database last evaluated is missing from the state or has another pass record id) | a clean state and served states without those | `pipeline_health:STATE` (24) | state and problem labels, or the request record id | FACT |

Never: an alert for an abstention alone (every abstention is visible in the report instead); an alert that names a size, an order, a target price or a trade step; an alert that changes a score, a status, the watchlist or a list.

## Suppressions (recorded in `alert_suppressions` with the run, printed in the run output)

| Code | When |
|---|---|
| NOT_EXACT_IDENTITY | the mint is not an exact address of its chain |
| SOURCE_STALE | the inputs were INPUT_STALE at the capture, or the request was captured more than 24 h before the run; the report still shows the flag |
| FIXTURE_IN_LIVE_RUN | a fixture document in a run not marked `--fixture-run` |
| RISK_OVERRIDES_FORECAST | a reevaluate candidate on a snapshot with any item of the risk list: the number is withheld and the risk warning stands instead (CP18-2; was VETO_OVERRIDES_FORECAST, vetoes only) |
| cooldown | an alert with the same cooldown key less than the policy's hours ago (the social-intel `_in_cooldown`) |
| daily_cap | separate caps per local day (America/New_York): `daily_cap` 8 notices and `daily_cap_warning` 8 warnings already stored (CP18-2), so notices from an earlier run never push a later warning out; candidates are also sorted warning first |

## Conventions reused from the social-intel alerts (no new engine)

| Convention | Reused code |
|---|---|
| alert state schema `memelab.social.alerts.state/1`, private path (default `data/private/predictive_alerts/alerts.sqlite`, refused inside the repository unless under `data/private/`; refused for the lab database, meaning the active `MEMELAB_DB` and any `--lab-db` given; refused for an existing file that is not SQLite or holds any table outside the alert schema (CP18-2)) | `alerts_engine.connect` |
| dedupe key unique per mode | `alert_events UNIQUE(mode, dedupe_key)` |
| cooldown per key | `alerts_engine._in_cooldown` |
| daily cap per local day, quiet hours 22:00 to 07:00, local and UTC times | `alerts_core.local_day`, `in_quiet_hours`, `local_text` |
| policy validation and its sha256 (schema, `trade_execution_impact` none, zone, quiet hours, cap 0 to 50, interval 60 min or more, cooldown 1 h or more, forbidden keys) | `alerts_core._merge`, `zone`, `_hhmm`, `_sha` |
| disclaimer | `alerts_core.DISCLAIMER` |
| preview files | `alerts_transport.FileSink` (preview folder only) |
| delivery ledger statuses (`dry_run_preview`), run records (`evaluated`, `no_new_upstream_data`, `too_soon`, `feed_unavailable`), retention purge | `alert_deliveries`, `alert_runs`, `alerts_engine.purge` |
| readable state and run text | `alerts_engine.state_view`, `render_state`, `render_run` |

## Runs

A run evaluates only the attempted requests of the passes after the last pass this alert state evaluated, and only while that pass is still in the state with the same pass record id (`feed_sha256`); otherwise the run says FEED_CHANGED with its reason, raises one pipeline_health notice and evaluates every pass of the state again (CP18-2), so a reset state or a second state on one alert database is never a silent "0 candidates". The previous run is the newest by run id. A run 0 to 60 minutes after the last evaluation is `too_soon`; a run whose clock is before the last evaluation is evaluated with the note CLOCK_BEHIND (CP18-2). No new pass with the same pass record id is `no_new_upstream_data`; a flag-off state returns nothing and writes nothing; a tampered state is `feed_unavailable` with one pipeline_health candidate.

Commands: `python -m memelab.predictive.reports alerts [--state-dir] [--config] [--alert-db] [--outbox] [--lab-db] [--as-of] [--fixture-run] [--json]` and `alerts-state [--alert-db] [--json]`.

## Token text in alerts (CP18-2)

The label of every alert is built from the same token text as the report: the Phase 17 sanitization, then withheld when the joined letters of the text contain a trading word from `TOKEN_WORDS` (for example buy, sell, long, short, moon, pump, takeprofit, stoploss, exitnow, apein, profit; a false match such as BELONG is withheld too, the safe side) or a multiplier such as 100X. A symbol `SELLNOW` is printed as "withheld", so no alert reads "WARNING: risk override / SELLNOW". Measured liquidity values stay on the labelled event line of the report; the alert text names the code LIQUIDITY_FALL_20PCT_OR_MORE without a percent (rule 13).
