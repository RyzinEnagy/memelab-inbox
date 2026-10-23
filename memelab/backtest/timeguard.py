"""Clocks, as-of joins and leakage guards.

Every strategy or report reads history only through these helpers. They make three mistakes impossible by
construction:
- reading a record whose available_at is after the decision time (LeakageError),
- reading a bar that has not closed by the decision time (closed_bars),
- turning "not observed" into zero (AsOf.state keeps OBSERVED / ZERO / MISSING / STALE / UNAVAILABLE apart).
"""
from __future__ import annotations

import math
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

OBSERVED, ZERO, MISSING, STALE, UNAVAILABLE, UNKNOWN_AS_OF = "OBSERVED", "ZERO", "MISSING", "STALE", "UNAVAILABLE", "UNKNOWN_AS_OF"

# earliest plausible epoch second for this project's data (2020-01-01) and a sanity ceiling (2100-01-01)
_MIN_TS, _MAX_TS = 1_577_836_800.0, 4_102_444_800.0


class LeakageError(RuntimeError):
    """A record that was not yet available reached a decision."""


class ClockError(ValueError):
    """An ambiguous or invalid timestamp."""


def utc_ts(v: Any) -> float:
    """Normalize a timestamp to UTC epoch seconds. Refuses ambiguous input instead of guessing.

    Accepts: int/float epoch seconds; ISO 8601 strings with 'Z' or an explicit offset; aware datetimes.
    Refuses: naive datetimes and naive ISO strings, epoch milliseconds (must be converted explicitly), NaN, out-of-range.
    """
    if isinstance(v, bool) or v is None:
        raise ClockError(f"not a timestamp: {v!r}")
    if isinstance(v, (int, float)):
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            raise ClockError("timestamp is NaN/inf")
        if x > _MAX_TS * 10:
            raise ClockError(f"{v} looks like epoch milliseconds; divide by 1000 explicitly")
        if not (_MIN_TS <= x <= _MAX_TS):
            raise ClockError(f"timestamp {v} outside 2020..2100")
        return x
    if isinstance(v, datetime):
        if v.tzinfo is None or v.utcoffset() is None:
            raise ClockError("naive datetime refused; attach a timezone")
        return utc_ts(v.timestamp())
    if isinstance(v, str):
        s = v.strip()
        if not s:
            raise ClockError("empty timestamp string")
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError as e:
            raise ClockError(f"unparseable timestamp {v!r}") from e
        if dt.tzinfo is None:
            raise ClockError(f"naive ISO timestamp refused: {v!r}")
        return utc_ts(dt.timestamp())
    raise ClockError(f"unsupported timestamp type {type(v).__name__}")


def iso(t: float | None) -> str | None:
    return None if t is None else datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def available_after(*times: float | None) -> float:
    """available_at is the latest of the moments that had to happen before the lab could act (ingest, processing...)."""
    ts = [float(t) for t in times if t is not None]
    if not ts:
        raise ClockError("no time given")
    return max(ts)


# ---------------- bars ----------------

@dataclass(frozen=True)
class Bar:
    start: float
    tf: int
    o: float
    h: float
    l: float
    c: float
    v: float | None = None
    available_at: float | None = None   # default: start + tf (+ provider lag)

    @property
    def end(self) -> float:
        return self.start + self.tf

    def avail(self, provider_lag: float = 0.0) -> float:
        return self.available_at if self.available_at is not None else self.end + provider_lag


def closed_bars(bars: Sequence[Bar], decision_time: float, provider_lag: float = 0.0) -> list[Bar]:
    """Bars that a decision at decision_time may use: closed and published. The forming bar is excluded."""
    return [b for b in bars if b.avail(provider_lag) <= decision_time]


def bar_decision_time(bar: Bar, provider_lag: float = 0.0) -> float:
    """A signal computed from this bar's close can only be decided once the bar is available."""
    return bar.avail(provider_lag)


def earliest_execution(decision_time: float, bars: Sequence[Bar], latency_s: float = 0.0) -> Bar | None:
    """First bar whose open is at or after decision_time + latency. Its open is the earliest price we may trade at
    on bar data. Returns None when no such bar exists (signal at the end of data: no fill)."""
    t = decision_time + latency_s
    i = bisect_left([b.start for b in bars], t)
    return bars[i] if i < len(bars) else None


# ---------------- as-of joins ----------------

@dataclass(frozen=True)
class AsOf:
    value: Any
    state: str
    record: dict | None = None
    age_s: float | None = None

    @property
    def usable(self) -> bool:
        return self.state in (OBSERVED, ZERO)


@dataclass
class Audit:
    accesses: int = 0
    records: int = 0
    log: list = field(default_factory=list)

    def check(self, kind: str, rows: Iterable[dict], cutoff: float) -> list[dict]:
        rows = list(rows)
        self.accesses += 1
        for r in rows:
            self.records += 1
            if r["available_at"] > cutoff:
                raise LeakageError(f"{kind} record available at {iso(r['available_at'])} reached a decision at {iso(cutoff)}")
        return rows


class Series:
    """Append-only time series of records for one key, ordered by available_at. Corrections are new records."""

    def __init__(self, rows: Iterable[dict] = ()):
        self._rows: list[dict] = []
        self._av: list[float] = []
        for r in rows:
            self.add(r)

    def add(self, r: dict) -> None:
        if "available_at" not in r:
            raise ClockError("record without available_at")
        a = float(r["available_at"])
        i = bisect_right(self._av, a)
        self._av.insert(i, a)
        self._rows.insert(i, r)

    def visible(self, cutoff: float) -> list[dict]:
        return self._rows[: bisect_right(self._av, cutoff)]

    def __len__(self):
        return len(self._rows)


def asof(series: Series | None, cutoff: float, *, field_name: str = "value", max_age_s: float | None = None,
         event_time_field: str = "event_time", audit: Audit | None = None, kind: str = "record") -> AsOf:
    """Latest record visible at cutoff. States:
    OBSERVED  a value exists and is fresh
    ZERO      the provider reported zero (a real number, not absence)
    MISSING   nothing was ever visible by cutoff
    STALE     last visible record older than max_age_s (measured from its event_time, else available_at)
    UNAVAILABLE the provider reported an outage for this key at cutoff (record with state UNAVAILABLE)
    """
    if series is None:
        return AsOf(None, MISSING)
    vis = series.visible(cutoff)
    if audit is not None:
        audit.check(kind, vis[-1:], cutoff)
    if not vis:
        return AsOf(None, MISSING)
    r = vis[-1]
    if r.get("value_state") == UNAVAILABLE:
        return AsOf(None, UNAVAILABLE, r)
    if r.get("value_state") == UNKNOWN_AS_OF:
        return AsOf(None, UNKNOWN_AS_OF, r)
    t_ref = r.get(event_time_field) if r.get(event_time_field) is not None else r["available_at"]
    age = cutoff - float(t_ref)
    v = r.get(field_name)
    if v is None:
        return AsOf(None, MISSING, r, age)
    if max_age_s is not None and age > max_age_s:
        return AsOf(v, STALE, r, age)
    if isinstance(v, (int, float)) and v == 0:
        return AsOf(v, ZERO, r, age)
    return AsOf(v, OBSERVED, r, age)


def visible_events(rows: Iterable[dict], cutoff: float, audit: Audit | None = None, kind: str = "event") -> list[dict]:
    """All records with available_at <= cutoff (event_time may be earlier; that never makes them visible earlier)."""
    out = [r for r in rows if float(r["available_at"]) <= cutoff]
    if audit is not None:
        audit.check(kind, out, cutoff)
    return out


def latest_versions(rows: Iterable[dict], cutoff: float, key: str = "origin_key") -> list[dict]:
    """For corrected records (each new version names its key), return the version each key had at cutoff.
    A later correction or deletion can never change what an earlier cutoff sees."""
    best: dict[Any, dict] = {}
    for r in sorted((r for r in rows if float(r["available_at"]) <= cutoff), key=lambda r: (float(r["available_at"]), r.get("id", 0))):
        best[r[key]] = r
    return [r for r in best.values() if r.get("kind") not in ("POST_DELETED", "DELETED")]
