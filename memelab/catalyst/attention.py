"""Attention quality for a catalyst event, measured from what the system can actually observe.

Observable here (and only here): the catalyst_items table (publisher-level mentions across news, exchange and
market feeds), DEX Screener paid placements, and the token-side proxies already in the core bundle (holder
growth, unique traders, organic volume share, net buyers). NOT observable: X post counts, Reddit, TikTok.
Every sample records its window and a sampling note so the bias is visible in the report.

Nothing here equates attention with buying. Holder-count growth is not independent new owners.
"""
from __future__ import annotations

import json
import time
from collections import Counter
from typing import Any

from .. import db
from .ingest import domain_of, norm_tokens, jaccard

PLATFORM_GROUP = {"news": "news", "scheduled": "prediction-markets", "market": "market-screens", "social": "social", "trader": "social"}


def sample_event(event_id: int, bundle: dict | None = None, t: float | None = None) -> dict[str, Any]:
    t = t or time.time()
    out: dict[str, Any] = {"metrics": {}, "flags": [], "notes": [], "unknowns": []}
    with db.connect() as con:
        ev = con.execute("SELECT * FROM catalyst_events WHERE id=?", (event_id,)).fetchone()
        if not ev:
            return out
        items = [dict(r) for r in con.execute("SELECT i.*, s.source_group, s.tier, es.role FROM catalyst_items i JOIN catalyst_event_sources es ON es.item_id=i.id JOIN catalyst_sources s ON s.source_id=i.source_id WHERE es.event_id=?", (event_id,))]
        pubs = {i["platform"] or domain_of(i["url"]) or i["source_id"] for i in items}
        groups = {PLATFORM_GROUP.get(i["source_group"], i["source_group"]) for i in items}
        roles = Counter(i["role"] for i in items)
        first = min((i["first_seen_at"] for i in items), default=t)
        span_days = max(1, len({int(i["first_seen_at"] // 86400) for i in items}))
        # acceleration: mentions of similar titles in the last 24h vs the mean per day over the prior 7 days (our own store)
        toks = norm_tokens(ev["title"])
        recent = con.execute("SELECT title, first_seen_at FROM catalyst_items WHERE first_seen_at >= ?", (t - 8 * 86400,)).fetchall()
        sim = [r for r in recent if jaccard(toks, norm_tokens(r["title"])) >= 0.4]
        last24 = sum(1 for r in sim if r["first_seen_at"] >= t - 86400)
        prior = sum(1 for r in sim if r["first_seen_at"] < t - 86400)
        base = prior / 7.0
        accel = (last24 / base) if base > 0 else (None if last24 == 0 else float("inf"))
        m = out["metrics"]
        m["unique_publishers"] = len(pubs)
        m["independent_sources"] = ev["independent_sources"]
        m["repetitions"] = ev["repetitions"]
        m["syndicated_or_circular"] = roles.get("SYNDICATED", 0) + roles.get("CIRCULAR", 0)
        m["platform_groups"] = sorted(groups)
        m["persistence_days"] = span_days
        m["mentions_24h"] = last24
        m["mention_baseline_per_day"] = round(base, 2)
        m["mention_acceleration_x"] = (None if accel is None else (999.0 if accel == float("inf") else round(accel, 2)))
        top_share = (Counter(i["platform"] or domain_of(i["url"]) for i in items).most_common(1)[0][1] / len(items)) if items else None
        m["top_publisher_share"] = round(top_share, 2) if top_share is not None else None
        if m["syndicated_or_circular"] and m["syndicated_or_circular"] >= max(1, m["independent_sources"]):
            out["flags"].append("MORE COPIES THAN INDEPENDENT SOURCES: syndication or circular citation dominates; corroboration count is %d" % m["independent_sources"])
        if top_share is not None and top_share >= 0.7 and len(items) >= 3:
            out["flags"].append("ATTENTION CONCENTRATED: one publisher accounts for %.0f%% of mentions" % (top_share * 100))
        if ev["resurfaced"]:
            out["flags"].append("RESURFACED STORY: a matching story exists in the store from more than 7 days ago (event %s)" % ev["resurfaced_of"])
        if ev["future_dated"]:
            out["flags"].append("PUBLICATION TIME AHEAD OF RETRIEVAL: source clock or timezone error; event time unreliable")
        # paid placement signal (DEX Screener) for linked tokens
        links = [dict(r) for r in con.execute("SELECT mint FROM catalyst_token_links WHERE event_id=?", (event_id,))]
        for l in links:
            paid = con.execute("SELECT COUNT(*) c FROM catalyst_items WHERE source_id IN ('mkt:dexscreener:profiles','mkt:dexscreener:boosts') AND item_key LIKE ?", (f"ds:{l['mint']}:%",)).fetchone()["c"]
            if paid:
                out["flags"].append(f"PAID PLACEMENT: {l['mint'][:8]}.. appears in DEX Screener paid profiles/boosts ({paid} snapshot(s)); promotion, not organic attention")
        # token-side participation proxies from the core bundle when supplied
        if bundle:
            mk = bundle.get("market") or {}
            hc = (mk.get("holder_change") or {})
            m["token_holder_change_24h_pct"] = hc.get("24h")
            m["token_unique_traders_24h"] = mk.get("num_traders_24h")
            m["token_organic_share_24h"] = None
            v = (mk.get("vol") or {}).get("24h"); ov = (mk.get("organic_vol") or {}).get("24h") if isinstance(mk.get("organic_vol"), dict) else None
            if v and ov is not None:
                m["token_organic_share_24h"] = round(ov / v, 3) if v else None
            out["notes"].append("token-side proxies come from Jupiter/GeckoTerminal aggregates; holder growth can be airdrops or split wallets, not independent new owners")
        out["notes"].append("publisher-level sample only (news, exchange, prediction-market and market-screen feeds); no X, Reddit, TikTok or Instagram coverage, so unique-author and remix-vs-copy metrics for social media are UNKNOWN")
        out["unknowns"] += ["unique social authors", "original vs remixed social content", "participation outside existing holder circles"]
        window = {"window_start": t - 86400, "window_end": t}
        for k, v in m.items():
            if isinstance(v, (int, float)) or v is None:
                db.insert(con, "catalyst_attention_samples", {"event_id": event_id, "mint": links[0]["mint"] if len(links) == 1 else None, "sampled_at": t, **window, "metric": k, "value": v, "detail_json": None, "sampling_note": out["notes"][-1]})
        db.insert(con, "catalyst_attention_samples", {"event_id": event_id, "sampled_at": t, **window, "metric": "flags", "value": len(out["flags"]), "detail_json": json.dumps(out["flags"]), "sampling_note": None})
    return out
