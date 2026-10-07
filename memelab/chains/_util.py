"""Shared scoring helpers for the ecosystem engines. Every scaled component returns (points, facts, unknowns) so scores stay transparent."""
from __future__ import annotations

import math
import statistics
from typing import Any, Iterable


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def lin(x: float | None, x0: float, x1: float) -> float | None:
    """Linear 0..1 between x0 and x1 (x0 may exceed x1 for inverse scales). None stays None."""
    if x is None:
        return None
    if x0 == x1:
        return 1.0 if x >= x1 else 0.0
    return clamp((x - x0) / (x1 - x0))


def loglin(x: float | None, x0: float, x1: float) -> float | None:
    """0..1 on a log scale between x0 and x1 (both > 0)."""
    if x is None or x <= 0:
        return None if x is None else 0.0
    return clamp((math.log10(x) - math.log10(x0)) / (math.log10(x1) - math.log10(x0)))


def ratio(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def median(xs: Iterable[float | None]) -> float | None:
    v = [x for x in xs if x is not None and x == x]
    return statistics.median(v) if v else None


def pct_change(new: float | None, old: float | None) -> float | None:
    if new is None or old in (None, 0):
        return None
    return (new / old - 1) * 100


class Component:
    """One SOI / regime component. add(weight, value01, label) accumulates; unknown(weight, what) records a gap that earns nothing."""

    def __init__(self, name: str, max_points: float):
        self.name, self.max = name, max_points
        self.parts: list[tuple[float, float | None, str]] = []
        self.unknowns: list[str] = []
        self.facts: list[str] = []

    def add(self, weight: float, value01: float | None, label: str) -> None:
        if value01 is None:
            self.unknowns.append(label)
            self.parts.append((weight, None, label))
        else:
            self.parts.append((weight, clamp(value01), label))

    def fact(self, s: str) -> None:
        self.facts.append(s)

    @property
    def points(self) -> float:
        tw = sum(w for w, _, _ in self.parts) or 1.0
        got = sum(w * v for w, v, _ in self.parts if v is not None)  # unknown parts contribute zero, never redistributed
        return round(self.max * got / tw, 1)

    @property
    def coverage(self) -> float:
        tw = sum(w for w, _, _ in self.parts) or 1.0
        return sum(w for w, v, _ in self.parts if v is not None) / tw

    def to_dict(self) -> dict[str, Any]:
        return {"points": self.points, "max": self.max, "coverage": round(self.coverage, 2), "parts": [{"w": w, "v": (round(v, 3) if v is not None else None), "label": l} for w, v, l in self.parts],
                "facts": self.facts, "unknowns": self.unknowns}


def confidence_from_coverage(cov: float) -> str:
    return "HIGH" if cov >= 0.85 else "MODERATE" if cov >= 0.6 else "LOW"


def clear_at(con, t: float, tables: dict[str, str]) -> None:
    """Make a rerun on the same result idempotent: delete rows written at exactly this observed_at. tables: {table: time_column}."""
    for table, col in tables.items():
        con.execute(f"DELETE FROM {table} WHERE {col}=?", (t,))
