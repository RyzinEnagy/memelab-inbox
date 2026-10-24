"""Point-in-time decision records from state-export versions (Phase 01 repair pass 2, change control CC-02, PI-D-021). Pure: the
caller supplies the export versions; nothing here reads git, a database or the network.

Why: `theses.created_at` is the collector-run start (PI-D-011), so one key (mint, created_at) can hold several different rows,
and a row can first appear in a later export than its key (skeptic counterexample CX-S1: a REJECTED, fatal-flagged row first
exported 26.7 minutes after its key's first export). A decision must never take a row that did not exist at its decision time.

Rules (TARGET_REGISTRY.md "Decision unit"):
  1. A candidate row is one exact thesis row: identity (mint, created_at, row_sha256), row_sha256 = sha256 of the canonical row
     without `id` (ids are reassigned in every session). Its first-visible time is the commit time of the first export version,
     oldest first, that contains that exact row. A row that first appears later gets the later time, never its key's earlier time.
  2. For each mint, at each distinct first-visible time T, the decision row is the newest visible row: largest created_at among
     rows first visible at or before T; ties by the earliest first-visible time, then by position in that export's theses list.
     KEY_CONFLICT is flagged when visible rows sharing the chosen created_at differ in status, score, fatal flags or snapshot price.
  3. A decision event exists at T when the decision row at T differs from the decision row at the mint's previous candidate time.
  4. Chain and point-in-time pool come from the mint's token row in the export where the decision row first appears; a missing
     token row gives chain None (never a default).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

ROW_EXCLUDE = ("id",)
CONFLICT_FIELDS = ("status", "score", "fatal_flags_json")


def row_sha256(row: dict) -> str:
    body = {k: v for k, v in row.items() if k not in ROW_EXCLUDE}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _snap(row: dict) -> dict:
    s = row.get("snapshot_json")
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s or "{}")
    except (TypeError, ValueError):
        return {}


def candidates(exports: list[dict]) -> list[dict]:
    """exports: [{"commit": sha, "commit_time": float, "theses": [row, ...], "tokens": [row, ...]}], oldest first.
    Returns one candidate per exact row with its first-visible commit, time and position, chain and point-in-time pool."""
    seen: dict[tuple, dict] = {}
    last_t = None
    for ex in exports:
        t = float(ex["commit_time"])
        if last_t is not None and t < last_t:
            raise ValueError("export versions must be given oldest first with non-decreasing commit times")
        last_t = t
        toks = {k["mint"]: k for k in ex.get("tokens") or []}
        for pos, row in enumerate(ex.get("theses") or []):
            ident = (row["mint"], float(row["created_at"]), row_sha256(row))
            if ident in seen:
                continue
            tk = toks.get(row["mint"])
            seen[ident] = {"mint": row["mint"], "created_at": float(row["created_at"]), "row_sha256": ident[2],
                           "first_commit": ex["commit"], "first_visible": t, "position": pos, "row": row,
                           "chain": (tk.get("chain") if tk else None),
                           "pool_pit": ((tk.get("primary_pool") or tk.get("graduated_pool")) if tk else None)}
    return list(seen.values())


def decisions(cands: list[dict]) -> list[dict]:
    """Decision events per rule 2 and 3, sorted by (mint, decision_time)."""
    by_mint: dict[str, list[dict]] = {}
    for c in cands:
        by_mint.setdefault(c["mint"], []).append(c)
    out = []
    for mint, lst in by_mint.items():
        times = sorted({c["first_visible"] for c in lst})
        prev = None
        for T in times:
            vis = [c for c in lst if c["first_visible"] <= T]
            newest = max(c["created_at"] for c in vis)
            same = sorted((c for c in vis if c["created_at"] == newest), key=lambda c: (c["first_visible"], c["position"]))
            chosen = same[0]
            ident = (chosen["created_at"], chosen["row_sha256"])
            if ident == prev:
                continue
            prev = ident
            sigs = {(tuple(c["row"].get(k) for k in CONFLICT_FIELDS), _snap(c["row"]).get("price")) for c in same}
            flags = []
            if len(sigs) > 1:
                flags.append("KEY_CONFLICT")
            # rows never leave the visible set, so a changed decision row is always one first visible at T
            out.append({"mint": mint, "decision_time": T, "decision_time_basis": "EXPORT_COMMIT", "commit": chosen["first_commit"],
                        "created_at": chosen["created_at"], "row_sha256": chosen["row_sha256"],
                        "row_first_visible": chosen["first_visible"], "chain": chosen["chain"], "pool_pit": chosen["pool_pit"],
                        "status": chosen["row"].get("status"), "score": chosen["row"].get("score"),
                        "fatal_flags_json": chosen["row"].get("fatal_flags_json"), "snapshot": _snap(chosen["row"]), "flags": flags,
                        "rows_sharing_key": len(same)})
    return sorted(out, key=lambda d: (d["mint"], d["decision_time"]))


def thin(events: list[dict], horizon_s: float) -> list[dict]:
    """Per mint the first event, then each next event at least one horizon after the previous kept one. Callers pass eligible
    events only (eligibility before thinning, CC-01)."""
    kept, last = [], {}
    for e in sorted(events, key=lambda e: (e["mint"], e["decision_time"])):
        t = last.get(e["mint"])
        if t is None or e["decision_time"] >= t + horizon_s:
            kept.append(e)
            last[e["mint"]] = e["decision_time"]
    return kept


def export_from_doc(commit: str, commit_time: float, doc: dict[str, Any]) -> dict:
    """Both export layouts (state.py `{"_tables": ...}` and the older flat one), as state.import_ reads them."""
    tables = doc.get("_tables") or {k: v for k, v in doc.items() if not k.startswith("_") and isinstance(v, list)}
    return {"commit": commit, "commit_time": float(commit_time), "theses": tables.get("theses") or [], "tokens": tables.get("tokens") or []}
