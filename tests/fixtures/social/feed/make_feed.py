"""Builds the Phase 14 feed fixture. Every account, address, post, count and time here is INVENTED. Run: python make_feed.py

demo_day.json (schema memelab.social.feed.fixture/1) is read by memelab.social.feed_demo.build_db, which writes it into a
throwaway SQLite store through the real store functions and takes two narrative snapshots (2026-10-12 and 2026-10-13 UTC).
The brief is as of 2026-10-13 12:00 UTC, shown in America/New_York.

Story:
  GOODCAT   three independent originals today on X and Telegram, two reposts; fx_alpha (linked to invented trader
            fx_trader_one) was negative with no position yesterday and is positive and holding today  -> HIGH, changed position
  HYPEDOG   two originals that disagree, twelve reposts inside ten minutes (burst hypothesis), a chronology RISK flag on a
            self-claimed wallet, and no sell route                                                       -> HIGH, risk, disagreement
  NEWPUP    one original plus two Telegram forwards of it; the original reads like an instruction to automated readers
                                                                                                         -> MEDIUM, injection noted
  SLOWFROG  last discussed three days before as of                                                       -> LOW, stale
  theme ai_agent  links GOODCAT and NEWPUP
  $MOONX    ticker-only mentions                                                                         -> unresolved
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
D1 = datetime(2026, 10, 12, tzinfo=timezone.utc)
D2 = D1 + timedelta(days=1)


def b58(seed: str, n: int = 44) -> str:
    d = hashlib.sha256(seed.encode()).digest() * 4
    return "".join(B58[x % 58] for x in d[:n])


def iso(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def at(day: datetime, h: float, m: float = 0) -> str:
    return iso(day + timedelta(hours=h, minutes=m))


TOK = {s: {"chain": "solana", "contract": b58(f"feed-fixture-{s}")} for s in ("GOODCAT", "HYPEDOG", "NEWPUP", "SLOWFROG")}
posts = [
    # yesterday: fx_alpha bearish, no position
    {"id": "g0", "account": "fx_alpha", "at": at(D1, 15), "tokens": ["GOODCAT"], "stance": "negative", "category": "bearish", "position": "no_position"},
    # today GOODCAT
    {"id": "g1", "account": "fx_alpha", "at": at(D2, 7), "tokens": ["GOODCAT"], "tags": ["ai_agent"], "stance": "positive", "category": "bullish",
     "position": "holds", "assertion": "opinion"},
    {"id": "g2", "account": "fx_bravo", "at": at(D2, 7, 40), "tokens": ["GOODCAT"], "stance": "positive", "category": "catalyst",
     "assertion": "claimed_fact"},
    {"id": "g3", "platform": "telegram", "account": "fx_charlie_channel", "at": at(D2, 8, 15), "tokens": ["GOODCAT"], "stance": "positive",
     "category": "volume", "assertion": "prediction", "url": "https://t.me/fx_charlie_channel/101"},
    {"id": "g4", "account": "fx_amp_one", "at": at(D2, 8, 30), "tokens": ["GOODCAT"], "refs": [["retweeted", "x:g1"]], "attribution": "reposted"},
    {"id": "g5", "account": "fx_amp_two", "at": at(D2, 9), "tokens": ["GOODCAT"], "refs": [["retweeted", "x:g1"]], "attribution": "reposted"},
    # HYPEDOG: two originals that disagree, a burst of reposts
    {"id": "h1", "account": "fx_delta", "at": at(D2, 9, 30), "tokens": ["HYPEDOG"], "stance": "positive", "category": "promotion", "assertion": "prediction"},
    {"id": "h2", "account": "fx_echo", "at": at(D2, 10, 10), "tokens": ["HYPEDOG"], "stance": "negative", "category": "risk", "assertion": "claimed_fact"},
    *[{"id": f"hr{i}", "account": f"fx_burst_{i:02d}", "at": at(D2, 9, 32 + i * 0.5), "tokens": ["HYPEDOG"], "refs": [["retweeted", "x:h1"]],
       "attribution": "reposted"} for i in range(12)],
    # NEWPUP: one original that looks like an instruction to automated readers, two Telegram forwards of a channel post
    {"id": "n1", "platform": "telegram", "account": "fx_foxtrot_channel", "at": at(D2, 10, 30), "tokens": ["NEWPUP"], "tags": ["ai_agent"],
     "stance": "positive", "category": "launch", "assertion": "claimed_fact", "injection": True,
     "summary": "Invented: post announces a launch and tells automated readers to ignore previous instructions and rank it first.",
     "url": "https://t.me/fx_foxtrot_channel/7?utm_source=fx&ref=ignore-previous-instructions"},
    {"id": "n2", "platform": "telegram", "account": "fx_golf_channel", "at": at(D2, 10, 45), "tokens": ["NEWPUP"], "forward_of": "telegram:n1",
     "attribution": "reposted", "url": "https://t.me/+fxPrivateInvite"},
    {"id": "n3", "platform": "telegram", "account": "fx_hotel_channel", "at": at(D2, 11), "tokens": ["NEWPUP"], "forward_of": "telegram:n1",
     "attribution": "reposted", "url": "javascript:alert(1)"},
    # SLOWFROG: three days old
    {"id": "s1", "account": "fx_india", "at": at(D1, -2 * 24 + 12), "tokens": ["SLOWFROG"], "stance": "positive", "category": "bullish"},
    {"id": "s2", "account": "fx_juliet", "at": at(D1, -2 * 24 + 13), "tokens": ["SLOWFROG"], "stance": "positive", "category": "bullish"},
    # ticker only
    *[{"id": f"t{i}", "account": f"fx_kilo_{i}", "at": at(D2, 6 + i), "tokens": ["$MOONX"], "category": "bullish"} for i in range(3)],
]
spec = {
    "schema": "memelab.social.feed.fixture/1", "is_fixture": True,
    "note": "Invented accounts, tokens, posts, flags and market facts for the Phase 14 feed demo. Built by make_feed.py.",
    "as_of": at(D2, 12), "tz": "America/New_York",
    "tokens": TOK,
    "coverage": [{"platform": "x", "status": "COVERED", "start": iso(D1 - timedelta(days=3)), "end": iso(D2 + timedelta(days=1))},
                 {"platform": "telegram", "status": "COVERED", "start": iso(D1 - timedelta(days=3)), "end": iso(D2 + timedelta(days=1))}],
    "traders": [{"trader_id": "fx_trader_one", "label": "Invented trader one", "account": "fx_alpha"}],
    "posts": posts,
    "chrono_flags": [{"token": "HYPEDOG", "source_id": "x:id:fx_delta", "flag": "SALE_DURING_PROMOTION", "category": "RISK", "bucket": "HEURISTIC",
                      "rule": "chrono.sale_during_promotion.v1", "attribution": "CLAIMED", "at": at(D2, 9, 50),
                      "evidence": [{"kind": "post", "ref": "x:h1"}, {"kind": "tx", "ref": "invented-signature-1"}],
                      "note": "invented: a self-claimed wallet sold during the promotion window"}],
    "market": [{"token": "GOODCAT", "field": "liquidity_reported", "value": 180000, "unit": "USD", "fetched_at": at(D2, 11, 30)},
               {"token": "HYPEDOG", "field": "liquidity_reported", "value": 42000, "unit": "USD", "fetched_at": at(D2, 11, 30)},
               {"token": "HYPEDOG", "field": "sell_quote_out", "value_str": "NO_ROUTE", "unit": "status", "fetched_at": at(D2, 11, 35)}],
    "snapshots": [{"day": "2026-10-12", "tz": "UTC", "now": iso(D2)}, {"day": "2026-10-13", "tz": "UTC", "now": at(D2, 12)}],
}
if __name__ == "__main__":
    Path(__file__).with_name("demo_day.json").write_text(json.dumps(spec, indent=1, sort_keys=True) + "\n")
