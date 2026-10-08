"""PRE_LAUNCH_SOCIAL_ANALYSIS with the signals that are actually readable.

Readable: launchpad comment counts, creator livestreams, official links present (and whether 'twitter' is an account or a borrowed
post), DEX Screener paid profile / boosts (PAID by definition), news/catalyst mentions, Jupiter organic score after trading, holder
growth between observations. Not readable: X followers and post velocity, Telegram and Discord membership, Farcaster casts,
search trends. Those stay UNKNOWN and earn nothing; the classification says how much of the picture is missing.
"""
from __future__ import annotations

import re
from typing import Any


def analyze(con, c: dict, t: float) -> dict[str, Any]:
    s = c.get("signals") or {}
    o = c.get("obs") or {}
    links = c.get("links") or {}
    facts, inferences, unknowns = [], [], ["X follower and post growth", "Telegram/Discord membership growth", "Farcaster activity", "search interest"]
    organic_pts, paid_pts = 0, 0
    replies = o.get("replies")
    if replies is not None:
        facts.append(f"{replies} launchpad comments")
        organic_pts += 2 if replies >= 200 else 1 if replies >= 50 else 0
    if o.get("is_live"):
        facts.append("creator is livestreaming on the launchpad")
        organic_pts += 1
    tw = links.get("twitter") or ""
    if tw:
        borrowed = bool(re.search(r"/status/\d+", tw))
        facts.append("X link is " + ("a post by someone else (borrowed attention: the token rides an existing tweet)" if borrowed else "an account"))
        if borrowed:
            inferences.append("a borrowed-tweet launch has no team-controlled audience; attention depends on the original post")
    else:
        unknowns.append("official X account (none linked)")
    if s.get("ds_profile"):
        paid_pts += 1; facts.append("DEX Screener enhanced profile (paid listing)")
    if s.get("ds_boost"):
        paid_pts += 2; facts.append(f"DEX Screener boosts purchased ({s['ds_boost']})")
    org = o.get("organic_score")
    if org is not None:
        facts.append(f"Jupiter organic score {org:.0f}")
        organic_pts += 2 if org >= 60 else 1 if org >= 30 else 0
    # catalyst/news mentions of the symbol or name (last 7 days)
    sym, name = (c.get("symbol") or "").strip(), (c.get("project") or "").strip()
    mentions = 0
    pats = [p for p in (sym if len(sym) >= 3 else None, name if len(name) >= 4 else None) if p]
    if pats:
        rx = re.compile(r"\b(" + "|".join(re.escape(p) for p in pats) + r")\b", re.I)
        mentions = sum(1 for r in con.execute("SELECT title FROM catalyst_events WHERE discovered_at > ?", (t - 7 * 86400,)) if rx.search(r["title"] or ""))
        if mentions:
            facts.append(f"{mentions} news/catalyst item(s) mention it (7d)")
            organic_pts += 1
    # holder growth across our own observations
    hist = [r for r in con.execute("SELECT observed_at, holders, replies FROM launch_observations WHERE launch_id=? ORDER BY observed_at", (c["launch_id"],)) if r["holders"] or r["replies"]]
    if len(hist) >= 2:
        a, b = hist[0], hist[-1]
        hrs = max((b["observed_at"] - a["observed_at"]) / 3600, 0.1)
        if a["holders"] and b["holders"]:
            facts.append(f"holders {a['holders']} -> {b['holders']} over {hrs:.1f}h")
        if a["replies"] is not None and b["replies"] is not None:
            facts.append(f"comments {a['replies']} -> {b['replies']} over {hrs:.1f}h")
            if b["replies"] - a["replies"] >= 30:
                organic_pts += 1
    if paid_pts >= 2 and organic_pts <= 1:
        cls = "PAID / COORDINATED-LEANING"
        inferences.append("visible promotion is paid while organic signals are thin")
    elif organic_pts >= 3 and paid_pts == 0:
        cls = "ORGANIC-LEANING"
    elif organic_pts == 0 and paid_pts == 0:
        cls = "UNKNOWN"
    else:
        cls = "MIXED"
    coverage = 0.35  # share of the attention picture that is readable at all (no X/Telegram/Discord)
    return {"classification": cls, "organic_points": organic_pts, "paid_points": paid_pts, "mentions_7d": mentions, "coverage": coverage,
            "facts": facts, "inferences": inferences, "unknowns": unknowns}
