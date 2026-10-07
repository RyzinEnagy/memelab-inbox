"""Source registry for Catalyst Intelligence.

Access modes (verified 2026-10-07 from the Chrome bridge; nothing here is reachable from the sandbox):
  fetch     : fetch() from the example.com tab works (CORS allowed)
  navigate  : CORS-blocked; the tab navigates to the URL and a parse snippet reads the document
  manual    : only readable by a person (login wall, app-only platform); operator notes go in via `catalyst note`
  blocked   : browser safety policy or no public endpoint; recorded as a coverage gap

Tiers: official (the issuer / exchange itself), reputable (editorial newsroom), aggregator (feeds of others),
social (public posts), proxy (third party mirror; delayed, flagged, never treated as real time).
"""
from __future__ import annotations

import time

TRADER_RESEARCH_LIST = [
    # handle, display, reason the list includes them (research sources, not certified profitable traders)
    ("rasmr_eth", "Rasmr", "high-frequency commentary on Solana memecoin flows; verified handle, joined 2011"),
    ("Rewkang", "Andrew Kang", "macro and rotation framing for crypto risk appetite"),
    ("thedefivillain", "VIKTOR", "on-chain flow commentary"),
    ("redphonecrypto", "redphone", "narrative framing and cycle commentary"),
    ("0xSisyphus", "Sisyphus", "memecoin narrative commentary"),
    ("blknoiz06", "Ansem", "memecoin attention commentary; note: tokens named after this account exist and are NOT endorsements"),
]

NEWS_FEEDS = [
    ("news:cointelegraph", "https://cointelegraph.com/rss", "reputable"),
    ("news:coindesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", "reputable"),
    ("news:decrypt", "https://decrypt.co/feed", "reputable"),
    ("news:theblock", "https://www.theblock.co/rss.xml", "reputable"),
    ("news:gnews:solana-memecoin", "https://news.google.com/rss/search?q=solana+memecoin&hl=en-US&gl=US&ceid=US:en", "aggregator"),
    ("news:gnews:memecoin", "https://news.google.com/rss/search?q=memecoin+OR+%22meme+coin%22&hl=en-US&gl=US&ceid=US:en", "aggregator"),
    ("news:gnews:base-memecoin", "https://news.google.com/rss/search?q=%22base%22+memecoin+OR+%22base+chain%22+meme&hl=en-US&gl=US&ceid=US:en", "aggregator"),
    ("news:gnews:bnb-memecoin", "https://news.google.com/rss/search?q=BNB+memecoin+OR+%22four.meme%22+OR+%22BNB+Chain%22+meme&hl=en-US&gl=US&ceid=US:en", "aggregator"),
    ("news:gnews:chain-rotation", "https://news.google.com/rss/search?q=%22memecoin%22+%28Base+OR+BNB+OR+Sui+OR+Hyperliquid+OR+Ethereum%29&hl=en-US&gl=US&ceid=US:en", "aggregator"),
]

EXCHANGE_FEEDS = [
    ("exch:binance:listings", "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48&pageNo=1&pageSize=20", "official", "navigate", "binance_cms"),
    ("exch:coinbase:assets", "https://api.exchange.coinbase.com/currencies", "official", "fetch", "cb_currencies"),
    ("exch:kraken:assets", "https://api.kraken.com/0/public/Assets", "official", "fetch", "kraken_assets"),
    ("exch:bybit:new", "https://api.bybit.com/v5/announcements/index?locale=en-US&type=new_crypto&limit=20", "official", "navigate", "bybit_ann"),
    ("exch:okx:listings", "https://www.okx.com/api/v5/support/announcements?annType=announcements-new-listings", "official", "navigate", "okx_ann"),
]

MARKET_FEEDS = [
    ("mkt:coingecko:trending", "https://api.coingecko.com/api/v3/search/trending", "aggregator", "fetch", "cg_trending"),
    ("mkt:dexscreener:profiles", "https://api.dexscreener.com/token-profiles/latest/v1", "aggregator", "fetch", "ds_profiles"),
    ("mkt:dexscreener:boosts", "https://api.dexscreener.com/token-boosts/top/v1", "aggregator", "fetch", "ds_profiles"),
]

SCHEDULED_FEEDS = [
    ("sched:polymarket:top", "https://gamma-api.polymarket.com/events?limit=60&active=true&closed=false&order=volume24hr&ascending=false", "aggregator", "fetch", "poly_events"),
]

SOCIAL_SOURCES = [
    # platform, access_mode, coverage gap text
    ("social:x:timelines", "x.com", "manual", "X timelines require a logged-in session; the bridge tab is not logged in. Profile pages (bio, join date, follower count, verification badge) are readable and are used for identity verification only. Closing the gap: sign into X in the Chrome profile the bridge uses, after which navigate-and-read of public timelines works."),
    ("social:reddit", "reddit.com", "blocked", "Blocked by the browser safety policy for this session (navigation refused) and CORS-blocked for fetch. No alternative in place."),
    ("social:youtube:feeds", "youtube.com/feeds", "navigate", "Channel RSS feeds are readable by navigation, but no channels are configured yet; add rows with a channel_id feed URL when a tracked narrative has an originating channel."),
    ("social:tiktok", "tiktok.com", "blocked", "No public read API; app-first platform. Not covered."),
    ("social:instagram", "instagram.com", "blocked", "Login wall; no public read API. Not covered."),
    ("social:telegram:public", "t.me/s/", "navigate", "Public channel previews (t.me/s/<channel>) are readable by navigation; no channels configured yet."),
]


def registry_rows(now: float | None = None) -> list[dict]:
    t = now or time.time()
    rows: list[dict] = []
    for sid, url, tier in NEWS_FEEDS:
        rows.append(dict(source_id=sid, source_group="news", kind="rss", access_mode="navigate", url=url, parser="rss", tier=tier, cadence_minutes=240, added_at=t, added_reason="initial registry"))
    for sid, url, tier, mode, parser in EXCHANGE_FEEDS:
        rows.append(dict(source_id=sid, source_group="news", kind="json", access_mode=mode, url=url, parser=parser, tier=tier, cadence_minutes=240, added_at=t, added_reason="initial registry (access changes / listings)"))
    for sid, url, tier, mode, parser in MARKET_FEEDS:
        rows.append(dict(source_id=sid, source_group="market", kind="json", access_mode=mode, url=url, parser=parser, tier=tier, cadence_minutes=240, added_at=t, added_reason="initial registry"))
    for sid, url, tier, mode, parser in SCHEDULED_FEEDS:
        rows.append(dict(source_id=sid, source_group="scheduled", kind="json", access_mode=mode, url=url, parser=parser, tier=tier, cadence_minutes=240, added_at=t, added_reason="initial registry (scheduled/anticipated events with market-implied odds)"))
    for sid, url, mode, gap in SOCIAL_SOURCES:
        rows.append(dict(source_id=sid, source_group="social", kind="html", access_mode=mode, url=url, parser=None, tier="social", cadence_minutes=None, enabled=0 if (mode in ("blocked", "manual") or gap) else 1, coverage_gap=gap, added_at=t, added_reason="initial registry"))
    for handle, display, reason in TRADER_RESEARCH_LIST:
        rows.append(dict(source_id=f"trader:x:{handle}", source_group="trader", kind="html", access_mode="manual", url=f"https://x.com/{handle}", parser="x_profile", tier="social", cadence_minutes=None, enabled=1,
                         identity_verified="UNVERIFIED", identity_notes=display, coverage_gap="Posts not readable without an X login in the bridge Chrome profile; identity verified from the public profile page only.", added_at=t, added_reason=reason))
    return rows


def sync_registry(con) -> int:
    """Idempotent: insert missing sources, never overwrite operator edits."""
    n = 0
    for r in registry_rows():
        hit = con.execute("SELECT source_id FROM catalyst_sources WHERE source_id=?", (r["source_id"],)).fetchone()
        if hit:
            continue
        cols = list(r)
        con.execute(f"INSERT INTO catalyst_sources ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", [r[c] for c in cols])
        n += 1
    return n


def active_sources(con, group: str | None = None, modes=("fetch", "navigate")) -> list[dict]:
    q = "SELECT * FROM catalyst_sources WHERE enabled=1 AND access_mode IN (%s)" % ",".join("?" * len(modes))
    args = list(modes)
    if group:
        q += " AND source_group=?"; args.append(group)
    return [dict(r) for r in con.execute(q, args)]
