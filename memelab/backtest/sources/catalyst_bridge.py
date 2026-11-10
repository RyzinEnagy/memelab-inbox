"""Read the lab's existing catalyst tables (read-only) into catalyst records for strategies.

No second collector: this only reshapes what memelab/catalyst already stored. Times:
- available_at = max(token link time, the first_seen_at of every item counted so far): a record is knowable only once
  the lab had both the story and the token link; published_at stays a claim.
- one record per (event, linked mint) per corroboration step: each new independent item adds a record whose
  available_at is that item's first_seen_at, so corroboration grows over time exactly as the lab saw it.
- origin_group = the item's source_id; ORIGINAL/INDEPENDENT roles count as origins; SYNDICATED/CIRCULAR/COMMENTARY do not.
- event status (denied, cancelled) is stored in place by the lab, so it is carried as `current_status` for reports and
  never used as a historical denial.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ORIGIN_ROLES = ("ORIGINAL", "INDEPENDENT")
POSITIVE = ("SCHEDULED", "UNEXPECTED", "CULTURAL", "ROTATION", "ACCESS")


def records_from_lab_db(db_path: Path | str) -> list[dict]:
    con = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE name='catalyst_events'").fetchone():
            return []
        out = []
        q = """SELECT e.id eid, e.category, e.status, e.published_at, e.discovered_at, l.mint, l.chain, l.verified_mint, l.link_strength, l.linked_at,
                      i.id iid, i.source_id, i.first_seen_at, s.role
               FROM catalyst_events e JOIN catalyst_token_links l ON l.event_id=e.id
               JOIN catalyst_event_sources s ON s.event_id=e.id JOIN catalyst_items i ON i.id=s.item_id
               ORDER BY e.id, l.mint, i.first_seen_at, i.id"""
        for r in con.execute(q):
            out.append({"event_id": f"cat{r['eid']}:{r['iid']}", "catalyst_event": r["eid"], "chain": r["chain"], "mint": r["mint"],
                        "origin_group": r["source_id"],
                        "counts_as_origin": r["role"] in ORIGIN_ROLES, "claim_type": r["category"],
                        "published_at": r["published_at"], "first_seen_at": r["first_seen_at"], "event_time": r["published_at"],
                        "available_at": max(r["first_seen_at"], r["linked_at"]),
                        # the lab updates event status and link strength in place, so they are TODAY's values, not what
                        # was known at available_at (Phase 16, D10): a later denial must never help an earlier decision
                        "verified": None, "denied": False, "current_status": r["status"], "status_is_current": True,
                        "mint_verified": bool(r["verified_mint"]) and r["link_strength"] in ("STRONG", "MODERATE"), "link_status_is_current": True,
                        "sentiment": 1 if r["category"] in POSITIVE else -1, "historical_asof_proof": "CONTEMPORANEOUS_CAPTURE"})
        # syndicated / circular / commentary copies never count as confirmation (G20): only origin roles are records
        return [x for x in out if x["counts_as_origin"]]
    finally:
        con.close()
