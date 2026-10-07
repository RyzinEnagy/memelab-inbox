"""Ingest a collector result (the JSON text read back from the browser page) into the inbox cache and DB fetch log.

Usage from Python:
    res = load_result("data/inbox/plan_123.result.json")
    bodies = res.ok_bodies()        # {key: body}
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from ..db import DATA_DIR, connect, insert


class Result:
    def __init__(self, data: dict[str, Any], path: Path | None = None):
        self.data = data
        self.path = path
        self.plan_id = data.get("_plan")
        self.observed_at_iso = data.get("_at")
        self.observed_at = _iso_to_epoch(self.observed_at_iso) if self.observed_at_iso else time.time()

    def items(self):
        for k, v in self.data.items():
            if not k.startswith("_") and k not in ("merged", "stage1_rejected"):
                yield k, v

    def ok_bodies(self) -> dict[str, Any]:
        out = {k: v.get("body") for k, v in self.items() if isinstance(v, dict) and v.get("s") == 200}
        for k in ("merged", "stage1_rejected", "_screen"):
            if k in self.data:
                out[k] = self.data[k]
        return out

    def by_prefix(self, prefix: str) -> dict[str, Any]:
        return {k: b for k, b in self.ok_bodies().items() if k.startswith(prefix)}

    def failures(self) -> dict[str, Any]:
        return {k: v for k, v in self.items() if not (isinstance(v, dict) and v.get("s") == 200)}

    def log(self):
        with connect() as con:
            for k, v in self.items():
                insert(con, "fetch_log", {
                    "fetched_at": self.observed_at, "plan_id": self.plan_id, "key": k,
                    "status": v.get("s") if isinstance(v, dict) else None,
                    "bytes": v.get("len") if isinstance(v, dict) else None,
                    "error": (v.get("err") if isinstance(v, dict) else str(v))[:300] if isinstance(v, dict) and v.get("err") else None,
                })


def _iso_to_epoch(s: str) -> float:
    from datetime import datetime, timezone
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()


def clean_page_text(text: str) -> str:
    """get_page_text prefixes a header ('Title: ...\\nURL: ...\\n---\\n'). Strip to the JSON object."""
    i = text.find("{")
    j = text.rfind("}")
    if i == -1 or j == -1:
        raise ValueError("no JSON object in page text")
    return text[i:j + 1]


def save_result(text: str, name: str | None = None) -> Path:
    js = clean_page_text(text)
    data = json.loads(js)
    name = name or data.get("_plan") or f"result_{int(time.time())}"
    p = DATA_DIR / "inbox" / f"{name}.result.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, separators=(",", ":")))
    return p


def load_result(path: Path | str) -> Result:
    p = Path(path)
    return Result(json.loads(p.read_text()), p)


def load_all_results(pattern: str = "*.result.json") -> list[Result]:
    return [load_result(p) for p in sorted((DATA_DIR / "inbox").glob(pattern))]


def merged_bodies(results: list[Result]) -> dict[str, tuple[Any, float]]:
    """Latest body per key across results, with observation time."""
    out: dict[str, tuple[Any, float]] = {}
    for r in sorted(results, key=lambda r: r.observed_at):
        for k, b in r.ok_bodies().items():
            out[k] = (b, r.observed_at)
    return out
