"""Token-first monitoring and alerting.

For every token on the core watchlist (and every token with an open catalyst link), answer:
  - is there a NEW catalyst since the last catalyst snapshot?
  - does any NEGATIVE event, denial or cancellation contradict the current thesis?
  - has an event expired or its scheduled day arrived (event-day reassessment)?
Alerts are rows in catalyst_alerts; the report and the scheduled-task summary read them. Nothing here trades.
"""
from __future__ import annotations

import time
from typing import Any

from .. import db
from .ingest import norm_tokens, jaccard, STOP as STOPWORDS


def run(t: float | None = None) -> dict[str, Any]:
    t = t or time.time()
    out = {"new_catalysts": [], "contradictions": [], "deteriorations": [], "expired": [], "event_day": []}
    with db.connect() as con:
        wl = {r["mint"]: dict(r) for r in con.execute("SELECT w.mint, w.status, t.symbol, t.name FROM watchlist w LEFT JOIN tokens t ON t.mint=w.mint")}
        linked = {r["mint"]: dict(r) for r in con.execute("SELECT l.mint, t.symbol, t.name FROM catalyst_token_links l LEFT JOIN tokens t ON t.mint=l.mint")}
        universe = {**linked, **wl}
        last_alert = {r["mint"]: r["m"] for r in con.execute("SELECT mint, MAX(alerted_at) m FROM catalyst_alerts WHERE mint IS NOT NULL GROUP BY mint")}
        for mint, tok in universe.items():
            since = last_alert.get(mint, 0)
            links = con.execute("SELECT l.*, e.title, e.category, e.status es, e.evidence_status, e.discovered_at, e.event_at, e.expires_at FROM catalyst_token_links l JOIN catalyst_events e ON e.id=l.event_id WHERE l.mint=?", (mint,)).fetchall()
            rejected_mints = {r["mint"] for r in con.execute("SELECT mint FROM catalyst_assessments WHERE verdict='REJECTED' AND mint IS NOT NULL")}
            for l in links:
                if mint in rejected_mints and l["category"] != "NEGATIVE":
                    continue  # a token that failed a fatal core check does not generate catalyst alerts
                if l["discovered_at"] > since and l["category"] != "NEGATIVE" and l["link_strength"] in ("STRONG", "MODERATE"):  # weak/thematic links never alert
                    out["new_catalysts"].append(_alert(con, l["event_id"], mint, "NEW_CATALYST", f"{tok.get('symbol') or mint[:6]}: new {l['category']} catalyst ({l['evidence_status']}, link {l['link_strength']}): {l['title'][:140]}", t))
                if l["category"] == "NEGATIVE" and l["discovered_at"] > since:
                    out["deteriorations"].append(_alert(con, l["event_id"], mint, "DETERIORATION", f"{tok.get('symbol') or mint[:6]}: NEGATIVE event ({l['evidence_status']}): {l['title'][:140]}", t))
                if l["es"] in ("DENIED", "CANCELLED"):
                    seen = con.execute("SELECT 1 FROM catalyst_alerts WHERE event_id=? AND mint=? AND kind='CONTRADICTION'", (l["event_id"], mint)).fetchone()
                    if not seen:
                        out["contradictions"].append(_alert(con, l["event_id"], mint, "CONTRADICTION", f"{tok.get('symbol') or mint[:6]}: catalyst {l['es']}: {l['title'][:140]}", t))
                if l["event_at"] and abs(l["event_at"] - t) <= 12 * 3600:
                    seen = con.execute("SELECT 1 FROM catalyst_alerts WHERE event_id=? AND mint=? AND kind='EVENT_DAY'", (l["event_id"], mint)).fetchone()
                    if not seen:
                        out["event_day"].append(_alert(con, l["event_id"], mint, "EVENT_DAY", f"{tok.get('symbol') or mint[:6]}: scheduled event is today; reassess (sell-the-news risk): {l['title'][:120]}", t))
            # unlinked NEGATIVE events whose title names the token symbol: possible contradiction not yet linked
            sym = (tok.get("symbol") or "").strip()
            if len(sym) >= 2 and sym.lower() not in STOPWORDS:
                for e in con.execute("SELECT id, title FROM catalyst_events WHERE category='NEGATIVE' AND discovered_at > ? AND status NOT IN ('EXPIRED')", (since,)):
                    if sym.lower() in norm_tokens(e["title"]):
                        out["deteriorations"].append(_alert(con, e["id"], mint, "DETERIORATION", f"{sym}: unlinked NEGATIVE event mentions the symbol: {e['title'][:140]} (verify it is the same asset)", t))
        # expiry sweep
        for e in con.execute("SELECT id, title, status FROM catalyst_events WHERE expires_at IS NOT NULL AND expires_at < ? AND status NOT IN ('EXPIRED','REJECTED','DENIED','CANCELLED')", (t,)):
            con.execute("UPDATE catalyst_events SET status='EXPIRED', status_reason='expired without entry', updated_at=? WHERE id=?", (t, e["id"]))
            db.insert(con, "catalyst_event_revisions", {"event_id": e["id"], "revised_at": t, "kind": "STATUS", "field": "status", "old_value": e["status"], "new_value": "EXPIRED", "note": "expiry sweep", "source_id": "monitor"})
            out["expired"].append({"event_id": e["id"], "title": e["title"]})
    return out


def _alert(con, event_id: int, mint: str | None, kind: str, text: str, t: float) -> dict:
    db.insert(con, "catalyst_alerts", {"event_id": event_id, "mint": mint, "alerted_at": t, "channel": "report", "kind": kind, "text": text})
    return {"event_id": event_id, "mint": mint, "kind": kind, "text": text}


def record_outcomes(t: float | None = None) -> int:
    """For assessed event-token pairs older than each horizon, record price change since discovery using market_snapshots."""
    t = t or time.time()
    n = 0
    with db.connect() as con:
        rows = con.execute("SELECT a.event_id, a.mint, a.assessed_at, a.price_at_discovery FROM catalyst_assessments a WHERE a.mint IS NOT NULL AND a.price_at_discovery IS NOT NULL").fetchall()
        for r in rows:
            for h, secs in (("1h", 3600), ("6h", 6 * 3600), ("24h", 86400), ("72h", 72 * 3600)):
                if t - r["assessed_at"] < secs:
                    continue
                if con.execute("SELECT 1 FROM catalyst_outcomes WHERE event_id=? AND mint=? AND horizon=?", (r["event_id"], r["mint"], h)).fetchone():
                    continue
                snap = con.execute("SELECT price_usd FROM market_snapshots WHERE mint=? AND observed_at >= ? ORDER BY observed_at LIMIT 1", (r["mint"], r["assessed_at"] + secs)).fetchone()
                if not snap or not snap["price_usd"]:
                    continue
                db.insert(con, "catalyst_outcomes", {"event_id": r["event_id"], "mint": r["mint"], "recorded_at": t, "horizon": h, "price_change_pct": round((snap["price_usd"] / r["price_at_discovery"] - 1) * 100, 2), "note": "from market_snapshots"})
                n += 1
    return n
