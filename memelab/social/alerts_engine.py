"""Phase 15: alert state, delivery and the delivery ledger.

State lives in a private SQLite file (default data/private/alerts.sqlite, gitignored; override MEMELAB_ALERT_DB),
never in the public lab database: destinations and delivery history are personal, and the public schema stays at 12.

One run (run()):
  1. claim the schedule slot if one is given (a slot already finished, or started less than 2 h ago, is a no-op, so a
     restart or a repeated trigger never evaluates twice);
  2. evaluate only when the policy interval has passed and the feed carries a snapshot this mode has not evaluated yet
     (never more often than the upstream refresh);
  3. turn candidates into alerts: dedupe key (never repeated in a mode), cooldown per policy and item, daily cap per
     local day, quiet hours (held, then released or expired);
  4. deliver: the file sink always, remote transports only in send mode with consent and credentials, fixtures never
     remote. Every attempt is written to the ledger as 'attempted' before the call and closed as 'succeeded' or
     'failed'. An attempt left open by a crash becomes 'outcome_unknown' and is never resent (at most once).
     Failed retryable attempts are retried on later runs after a backoff, up to max_attempts.

Dry run and send keep separate state (mode column), so a dry run never uses up the dedupe key of a real alert.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from . import alerts_core as AC

STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS alert_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alert_runs (
  run_id INTEGER PRIMARY KEY, mode TEXT NOT NULL CHECK (mode IN ('dry_run','send')),
  started_at REAL NOT NULL, finished_at REAL, as_of REAL, slot_key TEXT,
  feed_sha256 TEXT, snapshot_run_id INTEGER, snapshot_window TEXT, fixture INTEGER NOT NULL DEFAULT 0,
  policy_version TEXT, policy_sha256 TEXT,
  outcome TEXT NOT NULL,          -- evaluated | no_new_upstream_data | too_soon | feed_unavailable | slot_done | slot_in_progress
  summary_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS alert_events (
  alert_id INTEGER PRIMARY KEY, mode TEXT NOT NULL, dedupe_key TEXT NOT NULL, cooldown_key TEXT NOT NULL,
  policy TEXT NOT NULL, severity TEXT NOT NULL, item_id TEXT, label TEXT, created_at REAL NOT NULL, local_day TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('PENDING','HELD','COMPLETE','EXPIRED','PREVIEW')),
  fixture INTEGER NOT NULL DEFAULT 0, transports_json TEXT NOT NULL, alert_json TEXT NOT NULL, run_id INTEGER NOT NULL,
  UNIQUE (mode, dedupe_key)
);
CREATE INDEX IF NOT EXISTS ix_ae_cool ON alert_events(mode, cooldown_key, created_at);
CREATE INDEX IF NOT EXISTS ix_ae_day ON alert_events(mode, local_day);
CREATE TABLE IF NOT EXISTS alert_suppressions (
  run_id INTEGER NOT NULL, policy TEXT NOT NULL, item_id TEXT, reason_code TEXT NOT NULL, reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alert_baseline (
  mode TEXT NOT NULL, item_id TEXT NOT NULL, snapshot_run_id INTEGER NOT NULL, snapshot_window TEXT, mentions REAL NOT NULL,
  recorded_at REAL NOT NULL, PRIMARY KEY (mode, item_id, snapshot_run_id)
);
CREATE TABLE IF NOT EXISTS alert_deliveries (
  delivery_id INTEGER PRIMARY KEY, alert_id INTEGER NOT NULL, mode TEXT NOT NULL, transport TEXT NOT NULL, dest_ref TEXT,
  attempt INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('attempted','succeeded','failed','outcome_unknown','dry_run_preview','skipped')),
  started_at REAL NOT NULL, finished_at REAL, error TEXT, retryable INTEGER NOT NULL DEFAULT 0, next_attempt_at REAL,
  cost_usd REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_ad_alert ON alert_deliveries(alert_id, transport, attempt);
CREATE TABLE IF NOT EXISTS alert_cooldown_resets (mode TEXT NOT NULL, cooldown_key TEXT NOT NULL, reset_at REAL NOT NULL, reason TEXT);
CREATE TABLE IF NOT EXISTS alert_slots (
  template TEXT NOT NULL, slot_key TEXT NOT NULL, mode TEXT NOT NULL, started_at REAL NOT NULL, finished_at REAL, run_id INTEGER,
  PRIMARY KEY (template, slot_key, mode)
);
"""
SLOT_LEASE_SECONDS = 7200


def default_state_path() -> Path:
    env = os.environ.get("MEMELAB_ALERT_DB")
    if env:
        return Path(env)
    from .. import db
    return Path(db.DB_PATH).parent / "private" / "alerts.sqlite"


def default_outbox() -> Path:
    from .. import db
    return Path(db.DB_PATH).parent / "private" / "alerts_outbox"


def _tracked_paths() -> set[Path]:
    from .. import db
    return {Path(db.DB_PATH).resolve()}


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    p = Path(path) if path else default_state_path()
    if p.resolve() in _tracked_paths():
        raise AC.AlertError("alert state never goes into the tracked lab database")
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.row_factory = sqlite3.Row
    con.executescript(STATE_SCHEMA)
    con.execute("INSERT OR IGNORE INTO alert_meta(key, value) VALUES ('state_schema', 'memelab.social.alerts.state/1')")
    con.commit()
    return con


# ---------- slots ----------

def claim_slot(con, template: str, slot_key: str, mode: str, now: float) -> str:
    r = con.execute("SELECT * FROM alert_slots WHERE template=? AND slot_key=? AND mode=?", (template, slot_key, mode)).fetchone()
    if r is None:
        con.execute("INSERT INTO alert_slots(template, slot_key, mode, started_at) VALUES (?,?,?,?)", (template, slot_key, mode, now))
        con.commit()
        return "claimed"
    if r["finished_at"] is not None:
        return "slot_done"
    if now - r["started_at"] < SLOT_LEASE_SECONDS:
        return "slot_in_progress"
    con.execute("UPDATE alert_slots SET started_at=? WHERE template=? AND slot_key=? AND mode=?", (now, template, slot_key, mode))
    con.commit()
    return "claimed"


def finish_slot(con, template: str, slot_key: str, mode: str, now: float, run_id: int) -> None:
    con.execute("UPDATE alert_slots SET finished_at=?, run_id=? WHERE template=? AND slot_key=? AND mode=?", (now, run_id, template, slot_key, mode))
    con.commit()


# ---------- evaluation ----------

def _baselines(con, mode: str, items: list[dict], snapshot_run_id: int | None) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for it in items:
        rows = con.execute("SELECT mentions FROM alert_baseline WHERE mode=? AND item_id=? AND snapshot_run_id<>? "
                           "ORDER BY snapshot_run_id", (mode, it["item_id"], snapshot_run_id if snapshot_run_id is not None else -1)).fetchall()
        out[it["item_id"]] = [r["mentions"] for r in rows]
    return out


def _record_baselines(con, mode: str, feed: dict, now: float) -> None:
    snap = (feed.get("data_freshness") or {}).get("snapshot_run_id")
    if snap is None:
        return
    for it in feed.get("items") or []:
        m = (it.get("activity") or {}).get("window_mentions")
        if m is not None:
            con.execute("INSERT OR IGNORE INTO alert_baseline(mode, item_id, snapshot_run_id, snapshot_window, mentions, recorded_at) VALUES (?,?,?,?,?,?)",
                        (mode, it["item_id"], snap, (feed.get("data_freshness") or {}).get("snapshot_window"), float(m), now))


def _in_cooldown(con, mode: str, key: str, now: float, hours: float) -> bool:
    r = con.execute("SELECT MAX(created_at) AS t FROM alert_events WHERE mode=? AND cooldown_key=?", (mode, key)).fetchone()
    if r is None or r["t"] is None or now - r["t"] >= hours * 3600:
        return False
    reset = con.execute("SELECT MAX(reset_at) AS t FROM alert_cooldown_resets WHERE mode=? AND cooldown_key=?", (mode, key)).fetchone()
    return not (reset and reset["t"] is not None and reset["t"] >= r["t"])


def reset_cooldown(con, mode: str, cooldown_key: str, now: float, reason: str) -> int:
    n = con.execute("SELECT COUNT(*) FROM alert_events WHERE mode=? AND cooldown_key=?", (mode, cooldown_key)).fetchone()[0]
    con.execute("INSERT INTO alert_cooldown_resets(mode, cooldown_key, reset_at, reason) VALUES (?,?,?,?)", (mode, cooldown_key, now, reason[:200]))
    con.commit()
    return n


def _evaluate(con, *, run_id: int, mode: str, feed: dict, policy: dict, now: float, transports: list) -> dict:
    tz = policy["tz"]
    items = feed.get("items") or []
    snap = (feed.get("data_freshness") or {}).get("snapshot_run_id")
    cands, supp = AC.candidates(feed, policy, now=now, baselines=_baselines(con, mode, items, snap))
    _record_baselines(con, mode, feed, now)
    day = AC.local_day(now, tz)
    used = con.execute("SELECT COUNT(*) FROM alert_events WHERE mode=? AND local_day=?", (mode, day)).fetchone()[0]
    quiet = AC.in_quiet_hours(now, policy)
    new, deduped = [], 0
    for c in cands:
        if con.execute("SELECT 1 FROM alert_events WHERE mode=? AND dedupe_key=?", (mode, c["dedupe_key"])).fetchone():
            deduped += 1
            continue
        cfg = policy["policies"][c["policy"]]
        if _in_cooldown(con, mode, c["cooldown_key"], now, float(cfg["cooldown_hours"])):
            supp.append({"policy": c["policy"], "item_id": c["item_id"], "label": c["label"], "reason_code": "cooldown",
                         "reason": f"an alert for this went out less than {cfg['cooldown_hours']:g} h ago"})
            continue
        if used >= int(policy["daily_cap"]):
            supp.append({"policy": c["policy"], "item_id": c["item_id"], "label": c["label"], "reason_code": "daily_cap",
                         "reason": f"daily cap of {policy['daily_cap']} alerts reached for {day} ({tz})"})
            continue
        held = quiet and c["severity"] not in (policy.get("quiet_hours_bypass") or [])
        status = "PREVIEW" if mode == "dry_run" else ("HELD" if held else "PENDING")
        tnames = [t.name for t in transports if not (t.remote and c["fixture"])]
        a = {**c, "schema": AC.ALERT_SCHEMA, "policy_version": policy["version"], "policy_sha256": policy["policy_sha256"],
             "created_at": now, "created_text": AC.local_text(now, tz), "mode": mode, "quiet_hours": quiet,
             "trade_execution_impact": "none"}
        bt = _backtest_context(c, now)
        if bt is not None:                     # backtesting package policy on: token alerts carry its label (UNTESTED when none)
            a["backtest"] = bt
        cur = con.execute("INSERT INTO alert_events(mode, dedupe_key, cooldown_key, policy, severity, item_id, label, created_at, local_day, status, fixture, "
                          "transports_json, alert_json, run_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (mode, c["dedupe_key"], c["cooldown_key"], c["policy"], c["severity"], c["item_id"], c["label"], now, day, status,
                           int(c["fixture"]), json.dumps(tnames), "{}", run_id))
        a["alert_id"] = cur.lastrowid
        con.execute("UPDATE alert_events SET alert_json=? WHERE alert_id=?", (json.dumps(a, sort_keys=True, default=str), a["alert_id"]))
        used += 1
        new.append(a)
    for s in supp:
        con.execute("INSERT INTO alert_suppressions(run_id, policy, item_id, reason_code, reason) VALUES (?,?,?,?,?)",
                    (run_id, s["policy"], s.get("item_id"), s["reason_code"], s["reason"]))
    con.commit()
    return {"candidates": len(cands), "new": [a["alert_id"] for a in new], "deduped": deduped, "suppressed": supp, "quiet_hours": quiet}


def _backtest_context(c: dict, now: float) -> dict | None:
    """None unless the backtesting policy is on, so alerts are unchanged when it is off. Never raises."""
    try:
        if not (c.get("chain") and c.get("contract")):
            return None                        # theme alerts: no token, nothing to label
        from ..backtest import hook
        return hook.alert_context(c["chain"], c["contract"], now=now)      # None when the backtesting policy is off
    except Exception as e:  # the alert still goes out, labeled
        return {"label": "UNTESTED", "why": f"backtest context unavailable ({type(e).__name__})"}


# ---------- delivery ----------

def _spent_today(con, transport: str, day: str, tz: str) -> float:
    tot = 0.0
    for r in con.execute("SELECT d.cost_usd, d.started_at FROM alert_deliveries d WHERE d.transport=? AND d.mode='send' AND d.status IN ('attempted','succeeded','failed','outcome_unknown')",
                         (transport,)):
        if AC.local_day(r["started_at"], tz) == day:
            tot += r["cost_usd"] or 0.0
    return tot


def _ledger(con, alert_id: int, transport: str) -> list[sqlite3.Row]:
    return con.execute("SELECT * FROM alert_deliveries WHERE alert_id=? AND transport=? ORDER BY attempt", (alert_id, transport)).fetchall()


def _deliver_one(con, ev: sqlite3.Row, transports: dict, *, mode: str, policy: dict, now: float) -> None:
    a = json.loads(ev["alert_json"])
    text = AC.render_text(a, policy["tz"])
    names = json.loads(ev["transports_json"])
    preview = mode == "dry_run"
    retry = policy["retry"]
    final = True
    for name in names:
        t = transports.get(name)
        rows = _ledger(con, ev["alert_id"], name)
        last = rows[-1] if rows else None
        if last is not None:
            if last["status"] == "attempted":       # opened by a run that died before closing it: never resend
                con.execute("UPDATE alert_deliveries SET status='outcome_unknown', finished_at=?, error=? WHERE delivery_id=?",
                            (now, "run ended before the outcome was recorded; not resent (at most once)", last["delivery_id"]))
                continue
            if last["status"] in ("succeeded", "outcome_unknown", "dry_run_preview", "skipped"):
                continue
            if last["status"] == "failed":
                if not last["retryable"] or last["attempt"] >= int(retry["max_attempts"]):
                    continue
                if last["next_attempt_at"] is not None and now < last["next_attempt_at"]:
                    final = False
                    continue
        attempt = (last["attempt"] if last is not None else 0) + 1
        if t is None:
            con.execute("INSERT INTO alert_deliveries(alert_id, mode, transport, dest_ref, attempt, status, started_at, finished_at, error) "
                        "VALUES (?,?,?,?,?,?,?,?,?)", (ev["alert_id"], mode, name, None, attempt, "skipped", now, now,
                                                        "transport no longer configured"))
            continue
        cost = float((policy.get("transport_cost_usd") or {}).get(name, 0.0))
        ceiling = float((policy.get("cost_ceilings_usd_per_day") or {}).get(name, 0.0))
        if not preview and _spent_today(con, name, AC.local_day(now, policy["tz"]), policy["tz"]) + cost > ceiling:
            con.execute("INSERT INTO alert_deliveries(alert_id, mode, transport, dest_ref, attempt, status, started_at, finished_at, error, retryable, next_attempt_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?)", (ev["alert_id"], mode, name, AC_dest(t), attempt, "failed", now, now,
                                                           f"daily cost ceiling {ceiling:g} USD for {name} reached", 1, now + 3600))
            final = False
            continue
        if preview:
            res = t.send(ev["alert_id"], text, preview=True) if name == "file" else None
            con.execute("INSERT INTO alert_deliveries(alert_id, mode, transport, dest_ref, attempt, status, started_at, finished_at, error) "
                        "VALUES (?,?,?,?,?,?,?,?,?)", (ev["alert_id"], mode, name, AC_dest(t), attempt, "dry_run_preview", now, now,
                                                        ("preview file written; nothing sent" if res and res.ok else
                                                         (res.error if res else "dry run: not sent"))))
            continue
        cur = con.execute("INSERT INTO alert_deliveries(alert_id, mode, transport, dest_ref, attempt, status, started_at, cost_usd) "
                          "VALUES (?,?,?,?,?,?,?,?)", (ev["alert_id"], mode, name, AC_dest(t), attempt, "attempted", now, cost))
        con.commit()                                 # 'attempted' is durable before the call
        res = t.send(ev["alert_id"], text, preview=False)
        if res.ok:
            con.execute("UPDATE alert_deliveries SET status='succeeded', finished_at=? WHERE delivery_id=?", (now, cur.lastrowid))
        else:
            back = list(retry["backoff_seconds"])
            wait = back[min(attempt - 1, len(back) - 1)] if back else 3600
            if res.retry_after:
                wait = max(wait, res.retry_after)
            can = res.retryable and attempt < int(retry["max_attempts"])
            con.execute("UPDATE alert_deliveries SET status='failed', finished_at=?, error=?, retryable=?, next_attempt_at=? WHERE delivery_id=?",
                        (now, res.error, int(res.retryable), now + wait if can else None, cur.lastrowid))
            if can:
                final = False
        con.commit()
    if mode == "send" and final:
        con.execute("UPDATE alert_events SET status='COMPLETE' WHERE alert_id=?", (ev["alert_id"],))
    con.commit()


def AC_dest(t) -> str | None:
    from .alerts_transport import dest_ref
    return dest_ref(t.name, t.destination())


def deliver(con, *, mode: str, policy: dict, transports: list, now: float) -> dict:
    tmap = {t.name: t for t in transports}
    quiet = AC.in_quiet_hours(now, policy)
    expired, released = [], []
    if mode == "dry_run":
        evs = con.execute("SELECT * FROM alert_events WHERE mode='dry_run' AND alert_id NOT IN (SELECT alert_id FROM alert_deliveries) "
                          "ORDER BY alert_id").fetchall()
    else:
        for ev in con.execute("SELECT * FROM alert_events WHERE mode='send' AND status='HELD' ORDER BY alert_id").fetchall():
            if now - ev["created_at"] > float(policy["hold_max_hours"]) * 3600:
                con.execute("UPDATE alert_events SET status='EXPIRED' WHERE alert_id=?", (ev["alert_id"],))
                expired.append(ev["alert_id"])
            elif not quiet:
                con.execute("UPDATE alert_events SET status='PENDING' WHERE alert_id=?", (ev["alert_id"],))
                released.append(ev["alert_id"])
        con.commit()
        evs = con.execute("SELECT * FROM alert_events WHERE mode='send' AND status='PENDING' ORDER BY alert_id").fetchall()
    for ev in evs:
        _deliver_one(con, ev, tmap, mode=mode, policy=policy, now=now)
    return {"processed": [ev["alert_id"] for ev in evs], "released": released, "expired": expired}


def purge(con, *, policy: dict, now: float) -> int:
    cut = now - float(policy["dedupe_retention_days"]) * 86400
    ids = [r[0] for r in con.execute("SELECT alert_id FROM alert_events WHERE created_at<? AND status IN ('COMPLETE','EXPIRED','PREVIEW')", (cut,))]
    for i in ids:
        con.execute("DELETE FROM alert_deliveries WHERE alert_id=?", (i,))
        con.execute("DELETE FROM alert_events WHERE alert_id=?", (i,))
    con.commit()
    return len(ids)


# ---------- one run ----------

def run(con, *, feed: dict | None, policy: dict, mode: str, now: float, transports: list, slot: tuple[str, str] | None = None,
        unavailable_reason: str | None = None) -> dict:
    if mode not in ("dry_run", "send"):
        raise AC.AlertError("mode is dry_run or send")
    out: dict[str, Any] = {"mode": mode, "now": now, "now_text": AC.local_text(now, policy["tz"]), "policy_version": policy["version"],
                           "policy_sha256": policy["policy_sha256"]}
    if slot:
        st = claim_slot(con, slot[0], slot[1], mode, now)
        if st != "claimed":
            out.update({"outcome": st, "slot": list(slot)})
            con.execute("INSERT INTO alert_runs(mode, started_at, finished_at, slot_key, outcome, summary_json, policy_version, policy_sha256) "
                        "VALUES (?,?,?,?,?,?,?,?)", (mode, now, now, f"{slot[0]}:{slot[1]}", st, json.dumps({}), policy["version"], policy["policy_sha256"]))
            con.commit()
            return out
    df = (feed or {}).get("data_freshness") or {}
    cur = con.execute("INSERT INTO alert_runs(mode, started_at, as_of, slot_key, feed_sha256, snapshot_run_id, snapshot_window, fixture, policy_version, "
                      "policy_sha256, outcome) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (mode, now, (feed or {}).get("as_of"), f"{slot[0]}:{slot[1]}" if slot else None, (feed or {}).get("feed_sha256"),
                       df.get("snapshot_run_id"), df.get("snapshot_window"), int(bool((feed or {}).get("fixture"))), policy["version"],
                       policy["policy_sha256"], "started"))
    run_id = cur.lastrowid
    out["run_id"] = run_id
    purge(con, policy=policy, now=now)
    prev = con.execute("SELECT started_at, snapshot_run_id, fixture FROM alert_runs WHERE mode=? AND outcome='evaluated' AND run_id<>? "
                       "ORDER BY started_at DESC, run_id DESC LIMIT 1", (mode, run_id)).fetchone()
    ev: dict[str, Any] = {"candidates": 0, "new": [], "deduped": 0, "suppressed": [], "quiet_hours": AC.in_quiet_hours(now, policy)}
    if feed is None or (feed.get("availability") or {}).get("status") == "UNAVAILABLE" or df.get("snapshot_run_id") is None:
        outcome = "feed_unavailable"
        out["reason"] = unavailable_reason or (feed or {}).get("headline_reason") or ((feed or {}).get("availability") or {}).get("reason") or "no feed"
    elif prev is not None and now - prev["started_at"] < float(policy["min_interval_minutes"]) * 60:
        outcome = "too_soon"
        out["reason"] = f"last evaluation {round((now - prev['started_at']) / 60)} min ago; policy interval {policy['min_interval_minutes']} min"
    elif prev is not None and prev["snapshot_run_id"] == df.get("snapshot_run_id") and bool(prev["fixture"]) == bool(feed.get("fixture")):
        outcome = "no_new_upstream_data"
        out["reason"] = f"snapshot run {df.get('snapshot_run_id')} was already evaluated"
    else:
        outcome = "evaluated"
        ev = _evaluate(con, run_id=run_id, mode=mode, feed=feed, policy=policy, now=now, transports=transports)
    dl = deliver(con, mode=mode, policy=policy, transports=transports, now=now)
    out.update({"outcome": outcome, "evaluation": ev, "delivery": dl, "fixture": bool((feed or {}).get("fixture"))})
    summary = {"candidates": ev["candidates"], "new": ev["new"], "deduped": ev["deduped"], "suppressed": len(ev["suppressed"]),
               "delivery": dl, "reason": out.get("reason")}
    con.execute("UPDATE alert_runs SET finished_at=?, outcome=?, summary_json=? WHERE run_id=?", (now, outcome, json.dumps(summary, sort_keys=True), run_id))
    con.commit()
    if slot:
        finish_slot(con, slot[0], slot[1], mode, now, run_id)
    return out


# ---------- readable state ----------

def state_view(con, *, mode: str | None = None, limit: int = 50) -> dict:
    q = "SELECT * FROM alert_events" + (" WHERE mode=?" if mode else "") + " ORDER BY alert_id DESC LIMIT ?"
    evs = con.execute(q, ((mode, limit) if mode else (limit,))).fetchall()
    rows = []
    for e in evs:
        dels = con.execute("SELECT transport, attempt, status, error, next_attempt_at, dest_ref FROM alert_deliveries WHERE alert_id=? "
                           "ORDER BY transport, attempt", (e["alert_id"],)).fetchall()
        rows.append({"alert_id": e["alert_id"], "mode": e["mode"], "policy": e["policy"], "severity": e["severity"], "label": e["label"],
                     "status": e["status"], "created_at": e["created_at"], "fixture": bool(e["fixture"]), "dedupe_key": e["dedupe_key"],
                     "deliveries": [dict(d) for d in dels]})
    counts = {r["status"]: r["n"] for r in con.execute("SELECT status, COUNT(*) AS n FROM alert_deliveries" + (" WHERE mode=?" if mode else "")
                                                       + " GROUP BY status", ((mode,) if mode else ()))}
    remote_ok = con.execute("SELECT COUNT(*) FROM alert_deliveries WHERE status='succeeded' AND transport<>'file'" + (" AND mode=?" if mode else ""),
                            ((mode,) if mode else ())).fetchone()[0]
    runs = [dict(r) for r in con.execute("SELECT run_id, mode, started_at, outcome, snapshot_run_id, fixture, summary_json FROM alert_runs"
                                         + (" WHERE mode=?" if mode else "") + " ORDER BY run_id DESC LIMIT 10", ((mode,) if mode else ()))]
    return {"alerts": rows, "ledger_counts": counts, "remote_deliveries_succeeded": remote_ok, "runs": runs}


def _fmt_ts(ts, tz) -> str:
    return AC.local_text(ts, tz) if ts is not None else "none"


def render_state(view: dict, tz: str = "America/New_York") -> str:
    L = ["Alert delivery state", ""]
    if not view["alerts"]:
        L.append("No alerts recorded.")
    for a in reversed(view["alerts"]):
        L.append(f"Alert {a['alert_id']} [{a['mode']}] {a['severity']} {a['policy']}: {a['label']}{' (FIXTURE)' if a['fixture'] else ''}")
        L.append(f"  status {a['status']}, created {_fmt_ts(a['created_at'], tz)}, dedupe {a['dedupe_key'][:12]}")
        if not a["deliveries"]:
            L.append("  no delivery attempt yet" + (" (held for quiet hours)" if a["status"] == "HELD" else ""))
        for d in a["deliveries"]:
            what = {"succeeded": ("written to the local outbox file, not sent to any device" if d["transport"] == "file" else "sent, provider confirmed"),
                    "failed": "failed" + (f", next try {_fmt_ts(d['next_attempt_at'], tz)}" if d["next_attempt_at"] else ", no retry"),
                    "attempted": "attempt in progress or interrupted",
                    "outcome_unknown": "outcome unknown after an interrupted run; not resent",
                    "dry_run_preview": "dry run: preview only, nothing sent",
                    "skipped": "skipped"}[d["status"]]
            err = f" ({d['error']})" if d.get("error") and d["status"] not in ("succeeded", "dry_run_preview") else ""
            L.append(f"  {d['transport']} attempt {d['attempt']}: {d['status']}: {what}{err}")
    L += ["", "Ledger totals: " + (", ".join(f"{k} {v}" for k, v in sorted(view["ledger_counts"].items())) or "none"),
          f"Messages confirmed delivered to a device (telegram or email): {view['remote_deliveries_succeeded']}"]
    if view["remote_deliveries_succeeded"] == 0:
        L.append("Nothing has been sent to a device. Local files and previews are not deliveries.")
    return "\n".join(L) + "\n"


def render_run(out: dict, tz: str) -> str:
    L = [f"Alert run {out.get('run_id', '-')} ({out['mode']}), {out['now_text']}, policy {out['policy_version']} {out['policy_sha256'][:12]}"]
    if out.get("fixture"):
        L.append("FIXTURE DEMO: invented data, not live alerts.")
    L.append(f"Outcome: {out['outcome']}" + (f" ({out['reason']})" if out.get("reason") else ""))
    ev = out.get("evaluation") or {}
    if out["outcome"] == "evaluated":
        L.append(f"Candidates {ev['candidates']}, new alerts {len(ev['new'])}, deduped {ev['deduped']}, suppressed {len(ev['suppressed'])}"
                 + (", quiet hours: new alerts held" if ev.get("quiet_hours") and out["mode"] == "send" else ""))
        if not ev["new"]:
            L.append("No alerts today." if ev["candidates"] == 0 else "No new alerts (all deduped or suppressed).")
        for s in ev["suppressed"]:
            L.append(f"  suppressed {s['policy']} {s.get('label') or s.get('item_id')}: {s['reason_code']} ({s['reason']})")
    dl = out.get("delivery") or {}
    if dl.get("released"):
        L.append(f"Released after quiet hours: {', '.join(map(str, dl['released']))}")
    if dl.get("expired"):
        L.append(f"Expired while held (never sent): {', '.join(map(str, dl['expired']))}")
    if out["mode"] == "dry_run":
        L.append("Dry run: previews only. Nothing was sent.")
    return "\n".join(L) + "\n"
