"""Phase 15: daily and weekly job templates for the alert run, with time zone and daylight-saving rules.

Templates are data. None is enabled here: turning one on means creating a scheduled task (or a cron entry) after Elving
agrees, with the private alert config in place. The repo has no GitHub Actions workflow and this phase adds none (a
public repo's Actions would need the delivery secrets as repository secrets and would run on GitHub, outside the
private state file).

Wall-clock rules in the template zone (America/New_York by default):
  - a local time that does not exist (spring forward gap) runs once at the first valid minute after the gap;
  - a local time that happens twice (fall back) runs once, at the first occurrence;
  - each run has a slot key (template + local date, or ISO week for weekly), and alerts_engine.claim_slot makes a
    repeated trigger or a restart inside the same slot a no-op.
Templates may not fire more often than hourly, the fastest any upstream source refreshes in this lab.
"""
from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from . import alerts_core as AC

TEMPLATES: dict[str, dict[str, Any]] = {
    "daily": {"name": "memelab social alerts, daily", "kind": "daily", "local_time": "07:47", "tz": "America/New_York",
              "weekdays": [0, 1, 2, 3, 4, 5, 6], "enabled": False, "requires": ["notifications_opt_in", "send_enabled"],
              "cron": "CRON_TZ=America/New_York 47 7 * * *",
              "steps": ["python -m memelab social alerts preflight",
                        "python -m memelab social narrative-snapshot (only when its sources are not over their cost ceiling)",
                        "python -m memelab social alerts run --slot daily --send"]},
    "weekly": {"name": "memelab social alerts, weekly review", "kind": "weekly", "local_time": "08:13", "tz": "America/New_York",
               "weekdays": [0], "enabled": False, "requires": ["notifications_opt_in"],
               "cron": "CRON_TZ=America/New_York 13 8 * * 1",
               "steps": ["python -m memelab social alerts status --mode send",
                         "python -m memelab social alerts run --slot weekly --dry-run"]},
}


def _wall(d: date, t: dtime, tz: ZoneInfo) -> datetime:
    """Aware datetime for local date d and wall time t, resolving gaps forward and folds to the first occurrence."""
    naive = datetime.combine(d, t)
    cand = naive.replace(tzinfo=tz, fold=0)
    back = cand.astimezone(timezone.utc).astimezone(tz)
    if back.replace(tzinfo=None) == naive:
        return cand
    # nonexistent: step forward minute by minute to the first valid wall time
    probe = naive
    for _ in range(180):
        probe += timedelta(minutes=1)
        c = probe.replace(tzinfo=tz, fold=0)
        if c.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) == probe:
            return c
    raise AC.AlertError("could not resolve a local time")


def validate(t: dict) -> dict:
    tz = AC.zone(t["tz"])
    lt = AC._hhmm(t["local_time"])
    if t["kind"] not in ("daily", "weekly", "hourly"):
        raise AC.AlertError("template kind is daily, weekly or hourly")
    if t["kind"] == "hourly" and int(t.get("every_hours", 1)) < 1:
        raise AC.AlertError("a template may not run more often than hourly (upstream refresh limit)")
    if not t.get("weekdays"):
        raise AC.AlertError("template needs at least one weekday")
    return {"tz": tz, "time": lt}


def slot_key(t: dict, fire: datetime) -> str:
    loc = fire.astimezone(ZoneInfo(t["tz"]))
    if t["kind"] == "weekly":
        y, w, _ = loc.isocalendar()
        return f"{y}-W{w:02d}"
    if t["kind"] == "hourly":
        return loc.strftime("%Y-%m-%dT%H")
    return loc.strftime("%Y-%m-%d")


def next_runs(t: dict, after: float, count: int = 5) -> list[dict]:
    """The next `count` fire times strictly after `after` (epoch seconds), each with local and UTC text and its slot key."""
    v = validate(t)
    tz = v["tz"]
    out = []
    d = datetime.fromtimestamp(after, timezone.utc).astimezone(tz).date() - timedelta(days=1)
    guard = 0
    while len(out) < count and guard < 800:
        guard += 1
        if d.weekday() in t["weekdays"]:
            fire = _wall(d, v["time"], tz)
            ts = fire.timestamp()
            if ts > after and (not out or ts > out[-1]["at"]):
                u = fire.astimezone(timezone.utc)
                out.append({"at": ts, "local": fire.strftime("%Y-%m-%d %H:%M %Z"), "utc": u.strftime("%Y-%m-%d %H:%M UTC"),
                            "slot": slot_key(t, fire), "utc_offset_hours": fire.utcoffset().total_seconds() / 3600})
        d += timedelta(days=1)
    return out


def due_slot(t: dict, now: float) -> str | None:
    """The slot whose fire time is the latest one at or before now (what a run started now belongs to), or None."""
    v = validate(t)
    tz = v["tz"]
    d = datetime.fromtimestamp(now, timezone.utc).astimezone(tz).date()
    for back in range(0, 8):
        day = d - timedelta(days=back)
        if day.weekday() in t["weekdays"]:
            fire = _wall(day, v["time"], tz)
            if fire.timestamp() <= now:
                return slot_key(t, fire)
    return None
