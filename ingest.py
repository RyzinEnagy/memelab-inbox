"""Catalyst ingestion: source bodies -> catalyst_items -> grouped catalyst_events.

Timestamps (all UTC epoch):
  published_at  what the source claims
  first_seen_at first run that saw the item (immutable)
  retrieved_at  this run
  event_at      scheduled time of the underlying event (Polymarket end date, dated announcement, parsed date)

Evidence status comes from the SOURCE TIER, never from how confident the text sounds:
  official tier (exchange / issuer)       -> CONFIRMED
  reputable newsroom                      -> REPORTED
  aggregator / social / proxy / unknown   -> RUMOR
  anything the system concludes itself    -> INFERENCE (only in assessments, never stored as an event's status)

Dedup: items whose normalized titles share >= 0.6 token-set Jaccard within a 72 h window are one underlying event.
Independent corroboration counts distinct publisher domains; copies on the same domain or syndicated wire text
(near-identical body) count as repetitions. A matching title older than 7 days marks the new event RESURFACED.

Retrieved text is evidence. Nothing in it is ever executed or treated as an instruction.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Iterable
from urllib.parse import urlparse, parse_qs

from .. import db
from .sources import sync_registry

OFFICIAL_DOMAINS = {"binance.com", "coinbase.com", "exchange.coinbase.com", "kraken.com", "bybit.com", "okx.com", "jup.ag", "solana.com", "pump.fun"}
REPUTABLE_DOMAINS = {"cointelegraph.com", "coindesk.com", "decrypt.co", "theblock.co", "reuters.com", "bloomberg.com", "apnews.com", "wsj.com", "ft.com", "nytimes.com", "cnbc.com", "bbc.co.uk", "bbc.com", "theverge.com"}

STOP = set("the a an and or of to in on for with at by from as is are was were be been will has have had its it this that these those new says said after before over under into out up down about how why what when who which than then also just more most".split())

CATEGORY_RULES = [
    ("NEGATIVE", r"\b(hack|exploit|drain|rug|rugpull|rug pull|delist|delisting|lawsuit|sues|charged|indict|arrest|ban|banned|halt|suspend|freeze|frozen|scam|fraud|denies|denied|cancel|cancelled|postpone|outage|down)\b"),
    ("ACCESS", r"\b(list|listing|lists|listed|will add|adds|trading pair|now available|launchpool|launchpad|airdrop|distribution|perpetual|futures|spot)\b"),
    ("SCHEDULED", r"\b(will|scheduled|upcoming|on (mon|tues|wednes|thurs|fri|satur|sun)day|q[1-4]|mainnet|launch date|unlock|halving|fomc|cpi|election|debate|hearing|vote|summit|conference|keynote|livestream|premiere|release date)\b"),
    ("ROTATION", r"\b(rotation|inflow|outflow|etf|treasury|buyback|institutional|fund|raise|funding|valuation|market cap|dominance|liquidity)\b"),
    ("CULTURAL", r"\b(meme|viral|trend|trending|tiktok|celebrity|influencer|cat|dog|frog|pepe|movie|song|album|game|sports|nfl|nba|world cup|olympic|super bowl|halloween|christmas)\b"),
]


def now() -> float:
    return time.time()


def to_epoch(x: Any) -> float | None:
    if x is None or x == "":
        return None
    if isinstance(x, (int, float)):
        v = float(x)
        return v / 1000.0 if v > 1e11 else v
    s = str(x).strip()
    if re.fullmatch(r"\d{10,13}", s):
        return to_epoch(int(s))
    try:
        return parsedate_to_datetime(s).timestamp()
    except Exception:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def domain_of(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return None
    host = host.split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    # Google News wraps publisher links; the publisher is in the <source> tag handled by caller
    return host or None


def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        u = urlparse(url)
        q = {k: v for k, v in parse_qs(u.query).items() if not k.lower().startswith(("utm_", "ref", "fbclid", "gclid"))}
        qs = "&".join(f"{k}={v[0]}" for k, v in sorted(q.items()))
        return f"{u.scheme}://{u.netloc.lower()}{u.path.rstrip('/')}" + (f"?{qs}" if qs else "")
    except Exception:
        return url


def strip_publisher(title: str | None) -> str:
    """Google News style 'Headline - Publisher' -> 'Headline'."""
    t = title or ""
    if " - " in t:
        head, _, tail = t.rpartition(" - ")
        if 0 < len(tail) <= 40 and len(head) > 15:
            return head
    return t


def norm_tokens(title: str | None) -> set[str]:
    title = strip_publisher(title)
    t = re.sub(r"\d{4}-\d{2}-\d{2}|\b\d+\b", " ", (title or "").lower())   # dates and bare numbers are not topic words
    t = re.sub(r"[^a-z0-9$ ]+", " ", t)
    return {w for w in t.split() if w not in STOP and len(w) > 1}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def tier_status(tier: str | None, domain: str | None) -> str:
    if tier == "official" or (domain and any(domain == d or domain.endswith("." + d) for d in OFFICIAL_DOMAINS)):
        return "CONFIRMED"
    if tier == "reputable" or (domain and any(domain == d or domain.endswith("." + d) for d in REPUTABLE_DOMAINS)):
        return "REPORTED"
    return "RUMOR"


def classify(title: str, body: str | None, source_group: str) -> str:
    text = f"{title} {body or ''}".lower()
    if source_group == "scheduled":
        return "SCHEDULED"
    for cat, rx in CATEGORY_RULES:
        if re.search(rx, text):
            return cat
    return "UNEXPECTED"


# ---------------------------------------------------------------- item extraction per parser

def items_from_body(source: dict, body: Any, retrieved_at: float) -> list[dict]:
    """Turn a projected source body into uniform item dicts: key, url, title, body, author, platform, published_at, event_at, raw."""
    parser = source.get("parser") or source.get("kind")
    sid = source["source_id"]
    out: list[dict] = []
    if parser == "rss":
        for it in body or []:
            link = it.get("link") or it.get("guid")
            pub = to_epoch(it.get("pub"))
            out.append(dict(key=canonical_url(link) or hashlib.sha1((it.get("title") or "").encode()).hexdigest(), url=link, title=it.get("title"), body=re.sub(r"<[^>]+>", " ", it.get("desc") or "")[:1200],
                            author=it.get("author"), platform=it.get("src") or domain_of(link), published_at=pub, event_at=None, raw=it))
    elif parser == "binance_cms":
        for a in body or []:
            pub = to_epoch(a.get("pub"))
            out.append(dict(key=str(a.get("id") or a.get("code") or a.get("title")), url=a.get("link"), title=a.get("title"), body=None, author="Binance", platform="binance.com", published_at=pub, event_at=_date_in_title(a.get("title")), raw=a))
    elif parser == "bybit_ann":
        for a in body or []:
            out.append(dict(key=a.get("link") or a.get("title"), url=a.get("link"), title=a.get("title"), body=a.get("desc"), author="Bybit", platform="bybit.com", published_at=to_epoch(a.get("pub")), event_at=_date_in_title(a.get("title")), raw=a))
    elif parser == "okx_ann":
        for a in body or []:
            out.append(dict(key=a.get("link") or a.get("title"), url=a.get("link"), title=a.get("title"), body=None, author="OKX", platform="okx.com", published_at=to_epoch(a.get("pub")), event_at=_date_in_title(a.get("title")), raw=a))
    elif parser == "poly_events":
        NOISE_TAGS = {"esports", "sports", "nfl", "nba", "mlb", "nhl", "soccer", "epl", "ucl", "la-liga", "serie-a", "tennis", "mma", "ufc", "boxing", "golf", "f1", "cricket", "games", "counter-strike", "dota-2", "league-of-legends", "valorant", "chess"}
        NOISE_RX = re.compile(r"\bvs\.?\b|\babove ___|\bbelow ___|# tweets|price on |hit \$|dip to|\(BO[135]\)", re.I)
        for e in body or []:
            tags = {str(x).lower() for x in (e.get("tags") or [])}
            if tags & NOISE_TAGS or NOISE_RX.search(e.get("title") or ""):
                continue  # sports fixtures and price-threshold markets are not catalysts for anything tradable here
            out.append(dict(key=str(e.get("id") or e.get("slug")), url=f"https://polymarket.com/event/{e.get('slug')}" if e.get("slug") else None, title=e.get("title"), body=e.get("desc"), author="Polymarket market", platform="polymarket.com",
                            published_at=to_epoch(e.get("created")), event_at=to_epoch(e.get("end")), raw=e))
    elif parser == "cg_trending":
        for c in (body or {}).get("coins") or []:
            out.append(dict(key=f"cg:{c.get('id')}:{datetime.utcfromtimestamp(retrieved_at).strftime('%Y%m%d')}", url=f"https://www.coingecko.com/en/coins/{c.get('id')}", title=f"CoinGecko trending: {c.get('name')} ({c.get('sym')})", body=f"rank {c.get('rank')} price {c.get('price')} mcap {c.get('mcap')} 24h {c.get('chg24')}",
                            author="CoinGecko", platform="coingecko.com", published_at=retrieved_at, event_at=None, raw=c))
    elif parser == "ds_profiles":
        for p in body or []:
            if p.get("chainId") != "solana":
                continue
            out.append(dict(key=f"ds:{p.get('tokenAddress')}:{datetime.utcfromtimestamp(retrieved_at).strftime('%Y%m%d')}", url=f"https://dexscreener.com/solana/{p.get('tokenAddress')}", title=f"DEX Screener paid profile/boost: {p.get('tokenAddress')}", body=(p.get("description") or "")[:400],
                            author="token team (paid placement)", platform="dexscreener.com", published_at=retrieved_at, event_at=None, raw=p))
    elif parser in ("cb_currencies", "kraken_assets"):
        # asset lists are diffed by the access-change detector, not turned into items one by one
        out.append(dict(key=f"{sid}:snapshot:{int(retrieved_at)}", url=source.get("url"), title=f"{sid} asset list snapshot ({len(body or [])} assets)", body=None, author=sid, platform=domain_of(source.get("url")), published_at=retrieved_at, event_at=None, raw={"n": len(body or []), "ids": [x.get("id") for x in (body or [])][:3000]}))
    return out


def _date_in_title(title: str | None) -> float | None:
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", title or "")
    if not m:
        return None
    try:
        return datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return None


# ---------------------------------------------------------------- persistence

def _rev(con, event_id: int, kind: str, field=None, old=None, new=None, note=None, source_id=None, t=None):
    db.insert(con, "catalyst_event_revisions", {"event_id": event_id, "revised_at": t or now(), "kind": kind, "field": field,
                                                 "old_value": None if old is None else str(old)[:500], "new_value": None if new is None else str(new)[:500], "note": note, "source_id": source_id})


def ingest_bodies(bodies: dict[str, Any], retrieved_at: float | None = None) -> dict[str, Any]:
    """bodies: {key: body} where key is 'cat:<source_id>' (fetch mode via collector) or the navigate-mode page JSON
    {_cat: source_id, body: ...}. Returns counts and the list of new/updated event ids."""
    t = retrieved_at or now()
    stats = {"items_new": 0, "items_seen": 0, "events_new": 0, "events_corroborated": 0, "events_resurfaced": 0, "sources_ok": [], "sources_failed": []}
    touched: list[int] = []
    with db.connect() as con:
        sync_registry(con)
        srcs = {r["source_id"]: dict(r) for r in con.execute("SELECT * FROM catalyst_sources")}
        for key, body in bodies.items():
            sid = None; payload = body
            if isinstance(body, dict) and body.get("_cat"):
                sid = body["_cat"]; payload = body.get("body")
                if body.get("err") or not body.get("s") == 200:
                    stats["sources_failed"].append(sid)
                    con.execute("UPDATE catalyst_sources SET last_error=? WHERE source_id=?", (str(body.get("err"))[:300], sid))
                    continue
            elif key.startswith("cat:"):
                sid = key[4:]
            if not sid or sid not in srcs:
                continue
            src = srcs[sid]
            items = items_from_body(src, payload, t)
            stats["sources_ok"].append(sid)
            con.execute("UPDATE catalyst_sources SET last_ok_at=?, last_error=NULL WHERE source_id=?", (t, sid))
            for it in items:
                hit = con.execute("SELECT id, event_id FROM catalyst_items WHERE source_id=? AND item_key=?", (sid, it["key"])).fetchone()
                if hit:
                    stats["items_seen"] += 1
                    con.execute("UPDATE catalyst_items SET retrieved_at=? WHERE id=?", (t, hit["id"]))
                    continue
                item_id = db.insert(con, "catalyst_items", {"source_id": sid, "item_key": it["key"], "url": it["url"], "title": it["title"], "body": it["body"], "author": it["author"], "platform": it["platform"],
                                                             "published_at": it["published_at"], "retrieved_at": t, "first_seen_at": t, "raw_json": json.dumps(it["raw"], default=str)[:6000]})
                stats["items_new"] += 1
                if src.get("parser") in ("cb_currencies", "kraken_assets"):
                    continue  # asset-list snapshots feed the access-change detector, they are not events themselves
                ev_id, how = _group_item(con, src, it, item_id, t)
                touched.append(ev_id)
                stats[{"new": "events_new", "corroborated": "events_corroborated", "repeat": "events_corroborated"}[how]] += 1 if how != "repeat" else 0
        # access-change detector (exchange asset list diffs)
        stats["access_changes"] = detect_access_changes(con, t)
    stats["touched_events"] = sorted(set(touched))
    return stats


def _group_item(con, src: dict, it: dict, item_id: int, t: float) -> tuple[int, str]:
    title = it["title"] or ""
    toks = norm_tokens(title)
    dom = it.get("platform") or domain_of(it["url"])
    status = tier_status(src.get("tier"), dom)
    # candidate events in a 72h window around publication (or retrieval)
    ref = it["published_at"] or t
    rows = con.execute("SELECT id, title, published_at, independent_sources, repetitions, evidence_status FROM catalyst_events WHERE COALESCE(published_at, discovered_at) BETWEEN ? AND ?", (ref - 72 * 3600, ref + 72 * 3600)).fetchall()
    best, best_j = None, 0.0
    for r in rows:
        j = jaccard(toks, norm_tokens(r["title"]))
        if j > best_j:
            best, best_j = r, j
    denial_words = bool(re.search(r"\b(denies|denied|denial|cancel|cancelled|postponed|retract|retracts|correction|fake|false)\b", title.lower()))
    threshold = 0.35 if denial_words else 0.42   # headlines of one story vary a lot; 0.42 keeps same-story pairs together without merging unrelated ones (tuned on 441 live items)
    if best and best_j >= threshold:
        ev_id = best["id"]
        # same domain already attached? then it is a repetition; new domain = independent corroboration
        doms = {x["platform"] or domain_of(x["url"]) for x in con.execute("SELECT i.url, i.platform FROM catalyst_items i JOIN catalyst_event_sources s ON s.item_id=i.id WHERE s.event_id=?", (ev_id,))}
        role = "SYNDICATED" if _near_identical_body(con, ev_id, it.get("body")) else ("INDEPENDENT" if dom not in doms else "CIRCULAR")
        db.insert(con, "catalyst_event_sources", {"event_id": ev_id, "item_id": item_id, "role": role})
        con.execute("UPDATE catalyst_items SET event_id=? WHERE id=?", (ev_id, item_id))
        if role == "INDEPENDENT":
            con.execute("UPDATE catalyst_events SET independent_sources=independent_sources+1, updated_at=? WHERE id=?", (t, ev_id))
            _rev(con, ev_id, "CORROBORATED", note=f"independent source {dom}", source_id=src["source_id"], t=t)
        else:
            con.execute("UPDATE catalyst_events SET repetitions=repetitions+1, updated_at=? WHERE id=?", (t, ev_id))
        # evidence upgrade: a CONFIRMED source joining a REPORTED/RUMOR event upgrades it (recorded as a revision)
        rank = {"RUMOR": 0, "REPORTED": 1, "CONFIRMED": 2}
        if rank[status] > rank[best["evidence_status"]]:
            con.execute("UPDATE catalyst_events SET evidence_status=? WHERE id=?", (status, ev_id))
            _rev(con, ev_id, "REVISED", field="evidence_status", old=best["evidence_status"], new=status, source_id=src["source_id"], t=t)
        # denial / cancellation language from an official or reputable source
        if status in ("CONFIRMED", "REPORTED") and denial_words:
            kind = "DENIED" if re.search(r"den|retract|correction|fake|false", title.lower()) else "CANCELLED"
            con.execute("UPDATE catalyst_events SET status=?, status_reason=? WHERE id=?", (kind, title[:300], ev_id))
            _rev(con, ev_id, kind, note=title[:300], source_id=src["source_id"], t=t)
        return ev_id, ("corroborated" if role == "INDEPENDENT" else "repeat")
    # new event; check for resurfacing (same story > 7 days ago)
    old = con.execute("SELECT id, title FROM catalyst_events WHERE COALESCE(published_at, discovered_at) < ?", (ref - 7 * 86400,)).fetchall()
    res_of = None
    for r in old:
        if jaccard(toks, norm_tokens(r["title"])) >= 0.42:
            res_of = r["id"]; break
    future = 1 if (it["published_at"] and it["published_at"] > t + 900) else 0
    cat = classify(title, it.get("body"), src["source_group"])
    ekey = hashlib.sha1((" ".join(sorted(toks)) + f"|{int(ref // (72 * 3600))}").encode()).hexdigest()[:24]
    exp = (it["event_at"] + 86400) if it.get("event_at") else (ref + 7 * 86400)
    stale_days = ((t - it["published_at"]) / 86400) if it.get("published_at") else None
    known = f"published {stale_days:.0f} days before discovery (search-feed backfill, not breaking)" if stale_days and stale_days > 2 else None
    ev_id = db.insert(con, "catalyst_events", {"event_key": ekey, "category": cat, "title": title[:300], "description": (it.get("body") or "")[:1200], "original_url": it["url"], "original_source_id": src["source_id"],
                                                "published_at": it["published_at"], "discovered_at": t, "retrieved_at": t, "event_at": it.get("event_at"), "evidence_status": status, "independent_sources": 1, "repetitions": 0,
                                                "resurfaced": 1 if res_of else 0, "resurfaced_of": res_of, "future_dated": future,
                                                "access_limits": "social:x timelines, reddit, tiktok, instagram not readable (see catalyst_sources.coverage_gap)", "already_known": known,
                                                "status": "NEW", "expires_at": exp, "created_at": t, "updated_at": t})
    db.insert(con, "catalyst_event_sources", {"event_id": ev_id, "item_id": item_id, "role": "ORIGINAL"})
    con.execute("UPDATE catalyst_items SET event_id=? WHERE id=?", (ev_id, item_id))
    _rev(con, ev_id, "CREATED", note=f"from {src['source_id']} ({status}); category {cat}" + ("; RESURFACED of event %d" % res_of if res_of else "") + ("; publication time is in the future relative to retrieval" if future else ""), source_id=src["source_id"], t=t)
    return ev_id, "new"


def _near_identical_body(con, ev_id: int, body: str | None) -> bool:
    if not body or len(body) < 80:
        return False
    b = norm_tokens(body)
    for r in con.execute("SELECT i.body FROM catalyst_items i JOIN catalyst_event_sources s ON s.item_id=i.id WHERE s.event_id=? AND i.body IS NOT NULL", (ev_id,)):
        if jaccard(b, norm_tokens(r["body"])) >= 0.85:
            return True
    return False


def detect_access_changes(con, t: float) -> list[dict]:
    """Diff consecutive exchange asset-list snapshots; a newly present id is an ACCESS event (CONFIRMED, official)."""
    out = []
    for sid in ("exch:coinbase:assets", "exch:kraken:assets"):
        rows = con.execute("SELECT raw_json, retrieved_at FROM catalyst_items WHERE source_id=? ORDER BY first_seen_at DESC LIMIT 2", (sid,)).fetchall()
        if len(rows) < 2:
            continue
        new_ids = set(json.loads(rows[0]["raw_json"]).get("ids") or []); old_ids = set(json.loads(rows[1]["raw_json"]).get("ids") or [])
        for a in sorted(new_ids - old_ids)[:20]:
            title = f"{sid.split(':')[1].title()} asset list now includes {a}"
            ekey = hashlib.sha1(f"{sid}|{a}".encode()).hexdigest()[:24]
            if con.execute("SELECT id FROM catalyst_events WHERE event_key=?", (ekey,)).fetchone():
                continue
            ev_id = db.insert(con, "catalyst_events", {"event_key": ekey, "category": "ACCESS", "title": title, "description": "detected by diffing two consecutive public asset-list snapshots; confirm the trading-enable date on the exchange's own status page",
                                                        "original_url": None, "original_source_id": sid, "published_at": None, "discovered_at": t, "retrieved_at": t, "evidence_status": "CONFIRMED", "status": "NEW", "expires_at": t + 7 * 86400, "created_at": t, "updated_at": t})
            _rev(con, ev_id, "CREATED", note="asset-list diff", source_id=sid, t=t)
            out.append({"event_id": ev_id, "asset": a, "source": sid})
    return out


def note_event(event_id: int, note: str, kind: str = "REVISED", source_id: str | None = "operator") -> None:
    """Operator-entered observation (e.g. something read manually on X). Stored as a revision, never as fact."""
    with db.connect() as con:
        _rev(con, event_id, kind, note=note[:1000], source_id=source_id)
        con.execute("UPDATE catalyst_events SET updated_at=? WHERE id=?", (now(), event_id))
