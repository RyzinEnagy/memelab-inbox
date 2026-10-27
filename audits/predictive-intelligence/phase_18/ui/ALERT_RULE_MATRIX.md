# Alert rule matrix (alerts-rules-1, Phase 18)

Research alerts over the persisted predictive state. Code: `memelab/predictive/reports.py` (`make_alert_policy`, `alert_candidates`, `alert_run`, `render_alert_text`). Pre-registration: `../ACCEPTANCE_CHECKLIST.md` rules 9 to 11, PI-D-098. Tests: `tests/test_predictive_reports.py` (G8, G12 to G14).

Delivery is dry run only. `--send` is refused with "no external delivery is approved (PI-D-005)", and no transport other than the local file sink is ever built. A preview file in the outbox is not a delivery; the state view says so ("Nothing has been sent to a device").

## Policies

| Policy | Severity | Fires when | Does not fire when | Cooldown key (hours) | Dedupe fingerprint | Bucket |
|---|---|---|---|---|---|---|
| risk_override | warning | an attempted request whose structural veto is true (any lab fatal flag, liquidity, exitability, ownership or mechanics), whose fatal-flag check is unknown, whose backtest veto is true, or whose changes include a liquidity fall of 20% or more since the previous attempt of the mint | no flag, no backtest veto, liquidity fall under 20% or a rise | `risk_override:chain:mint` (6) | snapshot hash and the named parts | FACT |
| reevaluate | notice; warning for the drawdown target T2 | a FORECAST verified under rule 1 (record, stored point, cards), level SHADOW or VALIDATED_EXPERIMENTAL, interval lower bound above its base rate | an abstention; a refused document; level ABSTAIN; interval reaching the base rate; any veto on the snapshot (suppressed VETO_OVERRIDES_FORECAST) | `reevaluate:chain:mint:target` (12) | forecast id | INFERENCE |
| forecast_withdrawn | notice | a target with a verified FORECAST in the previous attempt of the mint abstains or is refused in the newest attempt | no earlier verified FORECAST | `forecast_withdrawn:chain:mint:target` (12) | earlier and newer forecast ids | FACT |
| pipeline_health | warning for STATE_TAMPERED and STATE_CHECK_FAILED; notice otherwise | the state fails its checks; an ERROR event in a new pass; MODEL_STALE, DRIFT_ALERT or REGISTRY_UNAVAILABLE among a target's blocking states at the pass | a clean state and served states without those | `pipeline_health:STATE` (24) | state and problem labels, or the request record id | FACT |

Never: an alert for an abstention alone (every abstention is visible in the report instead); an alert that names a size, an order, a target price or a trade step; an alert that changes a score, a status, the watchlist or a list.

## Suppressions (recorded in `alert_suppressions` with the run, printed in the run output)

| Code | When |
|---|---|
| NOT_EXACT_IDENTITY | the mint is not an exact address of its chain |
| SOURCE_STALE | the inputs were INPUT_STALE at the capture, or the request was captured more than 24 h before the run; the report still shows the flag |
| FIXTURE_IN_LIVE_RUN | a fixture document in a run not marked `--fixture-run` |
| VETO_OVERRIDES_FORECAST | a reevaluate candidate on a snapshot that carries any veto: the risk warning stands instead |
| cooldown | an alert with the same cooldown key less than the policy's hours ago (the social-intel `_in_cooldown`) |
| daily_cap | 8 alerts per local day (America/New_York) already stored; candidates are sorted warning first, so a notice never takes a warning's place |

## Conventions reused from the social-intel alerts (no new engine)

| Convention | Reused code |
|---|---|
| alert state schema `memelab.social.alerts.state/1`, private path (default `data/private/predictive_alerts/alerts.sqlite`, refused inside the repository unless under `data/private/`, refused for the lab database) | `alerts_engine.connect` |
| dedupe key unique per mode | `alert_events UNIQUE(mode, dedupe_key)` |
| cooldown per key | `alerts_engine._in_cooldown` |
| daily cap per local day, quiet hours 22:00 to 07:00, local and UTC times | `alerts_core.local_day`, `in_quiet_hours`, `local_text` |
| policy validation and its sha256 (schema, `trade_execution_impact` none, zone, quiet hours, cap 0 to 50, interval 60 min or more, cooldown 1 h or more, forbidden keys) | `alerts_core._merge`, `zone`, `_hhmm`, `_sha` |
| disclaimer | `alerts_core.DISCLAIMER` |
| preview files | `alerts_transport.FileSink` (preview folder only) |
| delivery ledger statuses (`dry_run_preview`), run records (`evaluated`, `no_new_upstream_data`, `too_soon`, `feed_unavailable`), retention purge | `alert_deliveries`, `alert_runs`, `alerts_engine.purge` |
| readable state and run text | `alerts_engine.state_view`, `render_state`, `render_run` |

## Runs

A run evaluates only the attempted requests of the passes after the last pass this alert state evaluated; a run within 60 minutes of the last evaluation is `too_soon`; no new pass is `no_new_upstream_data`; a flag-off state returns nothing and writes nothing; a tampered state is `feed_unavailable` with one pipeline_health candidate.

Commands: `python -m memelab.predictive.reports alerts [--state-dir] [--config] [--alert-db] [--outbox] [--lab-db] [--as-of] [--fixture-run] [--json]` and `alerts-state [--alert-db] [--json]`.
