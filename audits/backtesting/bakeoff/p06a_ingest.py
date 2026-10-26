"""Phase 06A evidence: push every real bake-off capture through the runtime ingestion path (webcapture), twice.

    python audits/backtesting/bakeoff/p06a_ingest.py audits/backtesting/bakeoff/p06a_views.jsonl [DB_PATH]
Checks, on real captures: cross-tool dedup (one record per canonical origin and claim), idempotent rescan, allowlist
refusal of the crawl start page, low-confidence date handling, and UNKNOWN_AS_OF for old pages first captured today.
"""
from __future__ import annotations

import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from memelab.backtest import store  # noqa: E402
from memelab.backtest.sources import captures, pagefields, webcapture  # noqa: E402

TOOL = {"PLAIN_HTTP": "EXISTING_COLLECTOR", "CRAWL4AI": "CRAWL4AI", "FIRECRAWL": "FIRECRAWL", "MAXUN": "MAXUN"}
UC = {"A": "project_catalyst_watch", "A_EXTRA": "project_catalyst_watch", "B": "developer_release_watch"}
ORDER = {"EXISTING_COLLECTOR": 0, "CRAWL4AI": 1, "FIRECRAWL": 2, "MAXUN": 3}


def run(views: list[dict], con) -> dict:
    views = sorted(views, key=lambda v: (v["captured_at"], ORDER[TOOL[v["tool"]]]))
    passes = []
    for p in (1, 2):
        c = Counter()
        rows = []
        for v in views:
            col = TOOL[v["tool"]]
            try:
                r = webcapture.record_page(con, use_case=UC[v["site"]], collector=col, url=v["url"], view=v, captured_at=v["captured_at"],
                                           run_id=v.get("run_id"), robot_id=v.get("robot_id"), raw_ref=f"{col}:{v.get('content_sha256') or v.get('scrape_id')}",
                                           evidence_only=col == "MAXUN")
                state = "RECORDED" if r.get("recorded") else ("DUPLICATE" if r.get("duplicate") else r.get("reason"))
                c[state] += 1
                rows.append({"tool": v["tool"], "url": v["url"], "state": state, "id": r.get("id"), "dup_of": r.get("duplicate_of_collector"),
                             "date_disagreement": r.get("date_disagreement")})
            except webcapture.OffAllowlist as e:
                c["OFF_ALLOWLIST"] += 1
                rows.append({"tool": v["tool"], "url": v["url"], "state": "OFF_ALLOWLIST", "error": str(e)})
        con.commit()
        passes.append({"pass": p, "counts": dict(c), "rows": rows})
    origins = {r["canonical_origin"]: r["n"] for r in con.execute("SELECT canonical_origin, COUNT(*) n FROM bt_capture_provenance "
                                                                  "WHERE extraction_status != 'REFINED_DATE' GROUP BY canonical_origin")}
    refined = con.execute("SELECT COUNT(*) FROM bt_capture_provenance WHERE extraction_status='REFINED_DATE'").fetchone()[0]
    old, seen_old = [], set()
    for v in views:
        if v["site"] != "A_EXTRA" or v["url"] in seen_old:
            continue
        seen_old.add(v["url"])
        d = pagefields.extract(v)["date"]
        try:
            canon = webcapture.allowed("project_catalyst_watch", v["url"])
        except webcapture.OffAllowlist:
            continue
        if d:
            cut = pagefields.date_epoch(d) + 86400
            a = captures.captures_asof(con, canon, cut)
            old.append({"url": v["url"], "claimed_date": d, "asof_claimed_date_plus_1d": a["state"],
                        "first_seen_at": con.execute("SELECT MIN(first_seen_at) FROM bt_capture_provenance WHERE canonical_origin=?", (canon,)).fetchone()[0]})
    return {"passes": passes, "versions_per_origin": origins, "origins": len(origins), "max_versions": max(origins.values()) if origins else 0,
            "refined_date_rows": refined,
            "old_pages_asof": old, "catalyst_records_with_mint": sum(1 for r in webcapture.catalyst_records(con) if r["mint"])}


if __name__ == "__main__":
    views = [json.loads(l) for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
    db = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(tempfile.mkdtemp()) / "p06a.sqlite"
    con = store.connect(db)
    res = run(views, con)
    print(json.dumps({k: v for k, v in res.items() if k != "passes"} | {"passes": [{"pass": p["pass"], "counts": p["counts"]} for p in res["passes"]]}, indent=1))
    out = Path(__file__).resolve().parents[1] / "testing" / "logs" / "p06a_ingest.json"
    out.write_text(json.dumps(res, indent=1, sort_keys=True))
