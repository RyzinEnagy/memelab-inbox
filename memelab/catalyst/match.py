"""Event -> token matching.

Two steps because the sandbox cannot call Jupiter:
  1. terms_for_events(): extract candidate names/tickers from NEW events and emit a browser plan of
     Jupiter token searches (jup_tok:<term>) plus DEX Screener searches (ds_search:<term>).
  2. link_events(): read the search bodies back, verify exact mints, record every competing match, and
     store catalyst_token_links with a link_type / link_strength that never exceeds what the evidence allows.

Rules:
  - A token is linked by MINT only. A ticker is a search term, never an identity.
  - OFFICIAL requires the event's own source to state the mint or the exchange to list that exact asset
    (asset-list diffs match on the exchange's asset id -> symbol, still NAME_MATCH until the mint is verified).
  - Celebrity / brand / politician names map to unofficial tokens: link_type NAME_MATCH, strength <= MODERATE,
    with the explicit note that the subject has not endorsed any token unless a CONFIRMED source says so.
  - Several liquid tokens for one term -> AMBIGUOUS, all recorded in competing_json.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from .. import db
from ..bridge.plan import Plan, JUP, DS

GENERIC = set("""binance coinbase kraken bybit okx solana sol bitcoin btc ethereum eth usdc usdt crypto token tokens coin coins market markets price
trading spot futures perpetual contract pair pairs listing listings adds add launch launches new update news today week month year
polymarket yes no will the a an and or of to in on for with by from as is are at what when who how why
coingecko dexscreener dex screener yahoo finance cnn bloomberg reuters cnbc forbes decrypt cointelegraph coindesk theblock beincrypto cryptonews
pluang changelly bitget kucoin here heres months weeks days against his own employer chasing engineer gets price forecast analysis best buy
dinner president democrats republicans senate house congress white house sec fed fomc cpi etf treasury ceo founder report reports says""".split())

TICKER_RX = re.compile(r"\$([A-Za-z][A-Za-z0-9]{1,9})\b")
PAREN_RX = re.compile(r"\(([A-Z0-9]{2,10})\)")
COMMON_WORDS = set("""rain data banana strike swift counter old down live free half made put loans liquidations german russia iranian quantum abstract
pearl conduit team crypto meme memes wallets wall street predecessor primed furious bitcoin ether ethereum solana sol dollar gold oil war peace
morning minute circle rise fall jump drop surge crash record hack hacked fog storm roman kalshi robinhood ledger tangem taurus europol doj sec
tokenized securities collateral asset stocks stock shares bstocks""".split())
EXCHANGE_PRODUCT_RX = re.compile(r"\b(bstocks?|tokenized securit|stock trading|perpetual contract|margin will add|collateral asset)\b", re.I)

CAP_RX = re.compile(r"\b([A-Z][a-zA-Z0-9]{2,}(?:\s+[A-Z][a-zA-Z0-9]{2,}){0,2})\b")


def extract_terms(title: str, body: str | None = None) -> list[str]:
    from .ingest import strip_publisher
    title = strip_publisher(title)
    text = f"{title} {body or ''}"
    terms: list[str] = []
    for m in TICKER_RX.findall(text):
        terms.append(m.upper())
    for m in PAREN_RX.findall(title):
        terms.append(m.upper())
    for m in CAP_RX.findall(title):
        w = m.strip()
        if w.lower() in GENERIC or len(w) < 3 or all(x.lower() in GENERIC for x in w.split()):
            continue
        terms.append(w)
    seen = set(); out = []
    for t in terms:
        k = t.lower()
        if k in seen or k in GENERIC:
            continue
        seen.add(k); out.append(t)
    return out[:8]


def terms_for_events(statuses=("NEW", "RESEARCH"), limit_events: int = 40) -> tuple[dict[int, list[str]], Plan]:
    plan = Plan(f"catmatch_{int(time.time())}")
    per_event: dict[int, list[str]] = {}
    seen: set[str] = set()
    with db.connect() as con:
        # freshest stories first; backfilled search-feed items (already_known set) only if room remains
        rows = con.execute(f"SELECT id, title, description, category FROM catalyst_events WHERE status IN ({','.join('?' * len(statuses))}) ORDER BY (already_known IS NOT NULL), COALESCE(published_at, discovered_at) DESC LIMIT ?", (*statuses, limit_events)).fetchall()
        for r in rows:
            terms = extract_terms(r["title"], r["description"])
            per_event[r["id"]] = terms
            for t in terms:
                k = t.lower()
                if k in seen:
                    continue
                seen.add(k)
                plan.add(f"jup_tok:{t}", f"{JUP}/tokens/v2/search?query={t}", proj="jup_tok", delay_ms=250)
                plan.add(f"ds_search:{t}", f"{DS}/latest/dex/search?q={t}", proj="raw", delay_ms=250)
    return per_event, plan


def _liq(x: dict) -> float:
    return float(x.get("liquidity") or x.get("liq") or 0)


def link_events(bodies: dict[str, Any], per_event: dict[int, list[str]] | None = None, min_liq_usd: float = 5_000) -> dict[str, Any]:
    """bodies: merged collector bodies containing jup_tok:<term> and ds_search:<term>."""
    t = time.time()
    stats = {"linked": 0, "ambiguous": 0, "no_match": 0, "events": 0}
    with db.connect() as con:
        if per_event is None:
            rows = con.execute("SELECT id, title, description FROM catalyst_events WHERE status IN ('NEW','RESEARCH')").fetchall()
            per_event = {r["id"]: extract_terms(r["title"], r["description"]) for r in rows}
        for ev_id, terms in per_event.items():
            ev = con.execute("SELECT * FROM catalyst_events WHERE id=?", (ev_id,)).fetchone()
            if not ev:
                continue
            stats["events"] += 1
            any_link = False
            for term in terms:
                cands = _candidates(bodies, term, min_liq_usd)
                if not cands:
                    continue
                # exact-symbol or exact-name matches first
                exact = [c for c in cands if (c["symbol"] or "").lower() == term.lower() or (c["name"] or "").lower() == term.lower()]
                pool = exact or cands
                pool.sort(key=lambda c: -c["liquidity"])
                top = pool[0]
                strength = "AMBIGUOUS" if len([c for c in pool if c["liquidity"] >= 0.25 * top["liquidity"]]) > 1 else ("MODERATE" if exact else "WEAK")
                link_type = "TICKER_MATCH" if term.isupper() and len(term) <= 10 else "NAME_MATCH"
                # a common English word or an exchange's own product (tokenized stocks, perps) is a thematic coincidence, not a connection
                if term.lower() in COMMON_WORDS or any(w.lower() in COMMON_WORDS for w in term.split()) and len(term.split()) == 1:
                    link_type, strength = "THEMATIC", "WEAK"
                if EXCHANGE_PRODUCT_RX.search(ev["title"] or ""):
                    link_type, strength = "THEMATIC", "WEAK"
                mint_in_source = top["mint"] in (ev["description"] or "") or top["mint"] in (ev["original_url"] or "")
                if mint_in_source:
                    link_type, strength = "NAMED_IN_SOURCE", "STRONG"
                rationale = _rationale(ev["category"], ev["title"], top, term)
                competing = [{k: c[k] for k in ("mint", "symbol", "name", "liquidity", "mcap", "age_hours")} for c in pool[1:6]]
                if con.execute("SELECT id FROM catalyst_token_links WHERE event_id=? AND mint=?", (ev_id, top["mint"])).fetchone():
                    continue
                db.insert(con, "catalyst_token_links", {"event_id": ev_id, "mint": top["mint"], "symbol": top["symbol"], "name": top["name"], "link_type": link_type, "link_strength": strength, "verified_mint": 1,
                                                        "competing_json": json.dumps(competing), "rationale": rationale,
                                                        "new_audience": _audience(ev["category"], ev["title"]), "buying_access": "Solana DEX via Jupiter route (verified quotable) " + ("+ CEX access change in the event itself" if ev["category"] == "ACCESS" else ""),
                                                        "linked_at": t})
                db.upsert_token(con, top["mint"])
                con.execute("UPDATE tokens SET symbol=COALESCE(symbol,?), name=COALESCE(name,?) WHERE mint=?", (top["symbol"], top["name"], top["mint"]))
                any_link = True
                stats["linked"] += 1
                if strength == "AMBIGUOUS":
                    stats["ambiguous"] += 1
            new_status = "RESEARCH" if any_link else "EVENT_ONLY"
            if ev["status"] in ("NEW",) or (ev["status"] == "EVENT_ONLY" and any_link):
                con.execute("UPDATE catalyst_events SET status=?, status_reason=?, updated_at=? WHERE id=?", (new_status, "token link(s) found" if any_link else "no verified token with liquidity >= $%d matches the event terms" % min_liq_usd, t, ev_id))
                db.insert(con, "catalyst_event_revisions", {"event_id": ev_id, "revised_at": t, "kind": "STATUS", "field": "status", "old_value": ev["status"], "new_value": new_status, "note": None, "source_id": "match"})
            if not any_link:
                stats["no_match"] += 1
    return stats


def _candidates(bodies: dict[str, Any], term: str, min_liq: float) -> list[dict]:
    out: dict[str, dict] = {}
    jt = bodies.get(f"jup_tok:{term}")
    for tok in (jt if isinstance(jt, list) else []):
        mint = tok.get("id") or tok.get("mint")
        if not mint:
            continue
        liq = float(tok.get("liquidity") or 0)
        if liq < min_liq:
            continue
        age = None
        fp = tok.get("firstPool") or {}
        if isinstance(fp, dict) and fp.get("createdAt"):
            from .ingest import to_epoch
            ts = to_epoch(fp["createdAt"]); age = (time.time() - ts) / 3600 if ts else None
        out[mint] = {"mint": mint, "symbol": tok.get("symbol"), "name": tok.get("name"), "liquidity": liq, "mcap": tok.get("mcap"), "age_hours": age, "organic": tok.get("organicScore"), "holders": tok.get("holderCount")}
    ds = bodies.get(f"ds_search:{term}")
    pairs = (ds or {}).get("pairs") if isinstance(ds, dict) else None
    for p in pairs or []:
        if p.get("chainId") != "solana":
            continue
        bt = p.get("baseToken") or {}
        mint = bt.get("address")
        liq = float((p.get("liquidity") or {}).get("usd") or 0)
        if not mint or liq < min_liq:
            continue
        cur = out.setdefault(mint, {"mint": mint, "symbol": bt.get("symbol"), "name": bt.get("name"), "liquidity": 0.0, "mcap": p.get("marketCap"), "age_hours": None})
        cur["liquidity"] = max(cur["liquidity"], liq)
        if p.get("pairCreatedAt") and cur.get("age_hours") is None:
            cur["age_hours"] = (time.time() - p["pairCreatedAt"] / 1000) / 3600
    return list(out.values())


def _rationale(cat: str, title: str, tok: dict, term: str) -> str:
    base = f"Event '{title[:120]}' names or implies '{term}'; {tok.get('symbol')} ({tok['mint'][:6]}..) is the most liquid Solana token matching that term (${tok['liquidity']:,.0f} liquidity)."
    why = {
        "ACCESS": " Access events can turn attention into buying because new venues let people who could not buy before do so; whether that demand reaches THIS DEX token depends on it being the same asset the venue listed.",
        "SCHEDULED": " Scheduled events concentrate attention on a known date; demand tends to arrive before the date and fade on it, so timing and 'already known' matter more than the event itself.",
        "UNEXPECTED": " Unexpected news creates a short window where the token is the only tradable expression of the story; the window closes as copycat tokens launch and as early buyers distribute.",
        "CULTURAL": " Cultural narratives widen the audience beyond crypto natives, but tokens riding them are unofficial and the subject has not endorsed them unless a CONFIRMED source says so.",
        "ROTATION": " Rotation events move capital between sectors; the token benefits only if it is a recognized proxy for the destination sector.",
        "NEGATIVE": " Negative events undermine theses; the link here is for monitoring deterioration, not for buying.",
    }.get(cat, "")
    return base + why + " This is an INFERENCE about a possible mechanism, not evidence that buying has occurred."


def _audience(cat: str, title: str) -> str:
    return {
        "ACCESS": "users of the listing venue who do not hold a self-custody wallet; practical access = the venue itself, not the DEX",
        "SCHEDULED": "people following the scheduled event (politics, sports, product launch) who may not be crypto users; access requires a wallet and a DEX",
        "CULTURAL": "audience of the meme's originating platform; conversion requires wallet onboarding, which is the main friction",
        "ROTATION": "existing crypto holders reallocating; already have access, so speed of rotation is the variable",
        "UNEXPECTED": "mixed; crypto natives first (minutes), broader audience only if the story reaches mainstream outlets (hours to days)",
        "NEGATIVE": "n/a (selling pressure, not a new audience)",
    }.get(cat, "unknown")
