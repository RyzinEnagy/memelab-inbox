"""Catalyst Intelligence report. Every event answers the operating question:
what is new, who could buy because of it, who could sell to them, and can a realistic position exit?
UTC stored; America/New_York displayed."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .. import db

NY = ZoneInfo("America/New_York")


def ny(ts: float | None) -> str:
    if not ts:
        return "unknown"
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(NY).strftime("%Y-%m-%d %H:%M ET")


def render(t: float | None = None, max_events: int = 25) -> str:
    t = t or time.time()
    L = [f"# Catalyst Intelligence report, {ny(t)}", "",
         "Operating question: what is new, who could buy because of it, who could sell to them, and can a realistic position exit?",
         "Grades are STRONG / MODERATE / WEAK / UNKNOWN. UNKNOWN earns nothing. A fatal core check overrides every grade. The triage score sorts the list; it is not a probability.", ""]
    with db.connect() as con:
        srcs = [dict(r) for r in con.execute("SELECT * FROM catalyst_sources ORDER BY source_group, source_id")]
        ok = [s for s in srcs if s["last_ok_at"] and t - s["last_ok_at"] < 36 * 3600]
        gaps = [s for s in srcs if s["access_mode"] in ("blocked", "manual")]
        failed = [s for s in srcs if s["last_error"] and s["source_group"] != "trader"]
        L.append("## Coverage this run")
        L.append(f"- Sources read in the last 36h: {len(ok)} ({', '.join(s['source_id'] for s in ok) or 'none'})")
        if failed:
            L.append("- Sources that failed: " + ", ".join(f"{s['source_id']} ({(s['last_error'] or '')[:60]})" for s in failed))
        for s in gaps:
            L.append(f"- GAP {s['source_id']}: {s['coverage_gap']}")
        traders = [s for s in srcs if s["source_group"] == "trader"]
        L.append("- Trader research list: " + "; ".join(f"@{s['source_id'].split(':')[-1]} ({s['identity_verified']})" for s in traders) + ". Research sources, not certified profitable traders. Posts are not readable until an X login exists in the bridge profile; identity is checked from public profile pages.")
        L.append("")
        # alerts
        alerts = [dict(r) for r in con.execute("SELECT * FROM catalyst_alerts WHERE alerted_at > ? ORDER BY alerted_at DESC", (t - 36 * 3600,))]
        L.append("## Alerts (last 36h)")
        if not alerts:
            L.append("- none")
        for a in alerts[:30]:
            L.append(f"- {ny(a['alerted_at'])} {a['kind']}: {a['text']}")
        L.append("")
        # events: latest assessment per event
        evs = [dict(r) for r in con.execute("SELECT * FROM catalyst_events WHERE status NOT IN ('EXPIRED') ORDER BY updated_at DESC LIMIT ?", (max_events * 3,))]
        ranked = []
        for e in evs:
            # best of the latest assessment per linked mint (an event with several links is judged by its strongest token)
            a = con.execute("SELECT * FROM catalyst_assessments WHERE event_id=? AND assessed_at = (SELECT MAX(assessed_at) FROM catalyst_assessments WHERE event_id=?) ORDER BY triage_score DESC LIMIT 1", (e["id"], e["id"])).fetchone()
            ranked.append((a["triage_score"] if a else -1, e, dict(a) if a else None))
        ranked.sort(key=lambda x: -x[0])
        L.append("## Events with a verified token connection")
        n = 0
        for score, e, a in ranked:
            links = [dict(r) for r in con.execute("SELECT * FROM catalyst_token_links WHERE event_id=?", (e["id"],))]
            if not links:
                continue
            n += 1
            if n > max_events:
                break
            L += _event_block(con, e, a, links, t)
        if n == 0:
            L.append("- none. Popular stories without a verified token stay event records below; nothing is manufactured from a trend.")
        L.append("")
        L.append("## Event records without a token connection (most recent)")
        k = 0
        for score, e, a in sorted(ranked, key=lambda x: -(x[1]["discovered_at"] or 0)):
            if con.execute("SELECT 1 FROM catalyst_token_links WHERE event_id=?", (e["id"],)).fetchone():
                continue
            k += 1
            if k > 25:
                break
            L.append(f"- [{e['category']}/{e['evidence_status']}] {e['title'][:140]} (published {ny(e['published_at'])}, discovered {ny(e['discovered_at'])}, {e['independent_sources']} independent source(s), {e['repetitions']} repetition(s){', RESURFACED' if e['resurfaced'] else ''}{', FUTURE-DATED' if e['future_dated'] else ''}; {e['original_source_id']})")
        L.append("")
        L.append("## Scheduled events ahead (next 14 days)")
        sched = [dict(r) for r in con.execute("SELECT * FROM catalyst_events WHERE event_at BETWEEN ? AND ? ORDER BY event_at", (t, t + 14 * 86400))]
        for e in sched[:30]:
            L.append(f"- {ny(e['event_at'])}: {e['title'][:120]} ({e['evidence_status']}, {e['original_source_id']})")
        if not sched:
            L.append("- none recorded")
        L.append("")
        L.append("## Method notes")
        L += ["- Evidence status comes from the source tier (official / reputable / other), never from how certain the text sounds. Inferences are labelled INFERENCE and never stored as event facts.",
              "- Syndicated copies and circular citations are grouped under one event; only distinct publisher domains count as corroboration.",
              "- Timestamps: publication (source claim), discovery (first run that saw it), retrieval (this run), event time (scheduled) are kept separately. All stored in UTC.",
              "- Attention metrics here are publisher-level (news, exchange, prediction-market and screen feeds). Social platforms are not covered; unique-author and remix metrics are UNKNOWN and stay UNKNOWN rather than being estimated.",
              "- Holder growth is not independent new owners. Attention is not buying. Scores are triage, not probabilities."]
    return "\n".join(L)


def _event_block(con, e: dict, a: dict | None, links: list[dict], t: float) -> list[str]:
    L = [f"### {e['title'][:160]}", ""]
    L.append(f"- Category {e['category']}; evidence {e['evidence_status']}; status {e['status']}" + (f" ({e['status_reason']})" if e.get("status_reason") else ""))
    L.append(f"- Published {ny(e['published_at'])}; discovered {ny(e['discovered_at'])}; retrieved {ny(e['retrieved_at'])}" + (f"; event time {ny(e['event_at'])}" if e.get("event_at") else "") + (f"; expires {ny(e['expires_at'])}" if e.get("expires_at") else ""))
    L.append(f"- Corroboration: {e['independent_sources']} independent source(s), {e['repetitions']} repetition(s)" + ("; RESURFACED story" if e["resurfaced"] else "") + ("; publication time ahead of retrieval (clock error)" if e["future_dated"] else ""))
    if e.get("original_url"):
        L.append(f"- Original: {e['original_url']}")
    others = [dict(r) for r in con.execute("SELECT i.url, i.platform, es.role FROM catalyst_items i JOIN catalyst_event_sources es ON es.item_id=i.id WHERE es.event_id=? AND es.role != 'ORIGINAL'", (e["id"],))]
    if others:
        L.append("- Supporting: " + "; ".join(f"{o['platform'] or ''} [{o['role']}] {o['url'] or ''}"[:120] for o in others[:6]))
    if e.get("access_limits"):
        L.append(f"- Not checkable: {e['access_limits']}")
    for l in links:
        comp = json.loads(l.get("competing_json") or "[]")
        L.append(f"- Token: {l.get('symbol')} ({l.get('name')}), mint `{l['mint']}`, link {l['link_type']} / {l['link_strength']}, mint verified {bool(l['verified_mint'])}" + (f"; competing matches: " + ", ".join(f"{c.get('symbol')} {str(c.get('mint'))[:6]}.. (${(c.get('liquidity') or 0):,.0f} liq)" for c in comp[:4]) if comp else ""))
        L.append(f"- What is new and why it could create buying (INFERENCE): {l.get('rationale')}")
        L.append(f"- Who could buy: {l.get('new_audience')}. Access: {l.get('buying_access')}")
    if a:
        c = json.loads(a["components_json"])
        L.append(f"- Assessment (triage {a['triage_score']}/100, verdict {a['verdict']}): " + ", ".join(f"{k} {a[k]}" for k in ("event_credibility", "token_connection", "attention_quality", "timing", "demand_evidence", "ownership_risk", "execution_feasibility", "entry_quality")))
        own = c.get("ownership_risk", {}); ex = c.get("execution_feasibility", {}); dem = c.get("demand_evidence", {}); tm = c.get("timing", {}); at = c.get("attention_quality", {})
        L.append(f"- Who could sell to them: adjusted top-10 {own.get('adjusted_top10_pct')}%, largest unexplained {own.get('largest_unexplained_pct')}%, cluster-adjusted {own.get('cluster_adjusted_pct')}%, large holders {own.get('dev_direction') or 'UNKNOWN'}")
        L.append(f"- Can a position exit: exit capacity ~${(ex.get('exit_capacity_usd_3pct') or 0):,.0f} at 3% impact, ~${(ex.get('exit_capacity_usd_10pct') or 0):,.0f} at 10%; round-trip friction {ex.get('round_trip_friction_pct')}%" if ex.get("grade") != "UNKNOWN" else "- Can a position exit: UNKNOWN (no router quotes yet)")
        L.append(f"- Demand evidence: net buyers 24h {dem.get('net_buyers_24h')}, buy/sell vol {dem.get('buy_sell_vol_ratio')}, holder change 24h {dem.get('holder_change_24h_pct')}%, organic share {dem.get('organic_share')}" if dem.get("grade") != "UNKNOWN" else "- Demand evidence: UNKNOWN (token not yet deep-fetched)")
        L.append(f"- Timing: {tm.get('hours_since_publication')} h since publication; price move in the 24h before publication {tm.get('price_move_before_publication_pct')}%; already known: {tm.get('already_known') or 'nothing recorded'}")
        if at.get("flags"):
            L.append("- Attention flags: " + " | ".join(at["flags"]))
        if a.get("entry_conditions"):
            L.append(f"- Entry conditions (from the core entry module): {a['entry_conditions'][:300]}")
            L.append(f"- Invalidation: {(a.get('invalidation') or '')[:300]}")
        if json.loads(a.get("missing_json") or "[]"):
            L.append("- Missing data (earns zero): " + ", ".join(json.loads(a["missing_json"])))
        if json.loads(a.get("fatal_json") or "[]"):
            L.append("- FATAL: " + "; ".join(json.loads(a["fatal_json"])))
        L.append(f"- Reassess {ny(a.get('reassess_at'))}; verdict reason: {a['verdict_reason']}")
    else:
        L.append("- Not yet assessed (no deep market data for the linked token).")
    revs = [dict(r) for r in con.execute("SELECT * FROM catalyst_event_revisions WHERE event_id=? ORDER BY revised_at", (e["id"],))]
    if len(revs) > 1:
        L.append("- History: " + "; ".join(f"{ny(r['revised_at'])} {r['kind']}" + (f" {r['field']} {r['old_value']}->{r['new_value']}" if r.get("field") else "") + (f" ({r['note'][:80]})" if r.get("note") else "") for r in revs[-6:]))
    L.append("")
    return L
