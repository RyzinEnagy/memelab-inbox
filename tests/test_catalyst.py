import json
import os
import time

import pytest


@pytest.fixture()
def tmpdb(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_DB", str(tmp_path / "t.sqlite"))
    import importlib
    from memelab import db
    importlib.reload(db)
    db.DB_PATH = tmp_path / "t.sqlite"
    db.init_db()
    yield db


def _rss(items):
    return {"_cat": "news:cointelegraph", "s": 200, "body": items}


def test_dedup_corroboration_resurface_denial(tmpdb):
    from memelab.catalyst import ingest as I
    t0 = time.time()
    # run 1: two outlets, same story (different domains) + one syndicated copy on the same domain
    b1 = {
        "cat:news:cointelegraph": _rss([{"title": "Binance will list Shielded Inu (SHINU) on spot", "link": "https://cointelegraph.com/news/binance-shinu", "pub": "Wed, 07 Oct 2026 01:00:00 +0000", "desc": "Binance announced it will list SHINU on Oct 9."}]),
        "cat:news:decrypt": {"_cat": "news:decrypt", "s": 200, "body": [{"title": "Binance to list Shielded Inu SHINU on spot market", "link": "https://decrypt.co/binance-shinu", "pub": "Wed, 07 Oct 2026 01:20:00 +0000", "desc": "Binance announced it will list SHINU on Oct 9."}]},
    }
    s1 = I.ingest_bodies(b1, retrieved_at=t0)
    assert s1["items_new"] == 2 and s1["events_new"] == 1 and s1["events_corroborated"] == 1
    with tmpdb.connect() as con:
        ev = con.execute("SELECT * FROM catalyst_events").fetchone()
        assert ev["independent_sources"] == 2 and ev["evidence_status"] == "REPORTED" and ev["category"] == "ACCESS"
    # run 2: same items again -> idempotent
    s2 = I.ingest_bodies(b1, retrieved_at=t0 + 60)
    assert s2["items_new"] == 0 and s2["events_new"] == 0
    # official source joins -> evidence upgrade to CONFIRMED, recorded as a revision
    b3 = {"cat:exch:binance:listings": {"_cat": "exch:binance:listings", "s": 200, "body": [{"id": 1, "code": "abc", "title": "Binance Will List Shielded Inu (SHINU) - 2026-10-09", "pub": (t0 + 120) * 1000}]}}
    I.ingest_bodies(b3, retrieved_at=t0 + 120)
    with tmpdb.connect() as con:
        ev = con.execute("SELECT * FROM catalyst_events").fetchone()
        assert ev["evidence_status"] == "CONFIRMED" and ev["independent_sources"] == 3 and ev["event_at"] is None  # event_at set only on creation
        kinds = [r["kind"] for r in con.execute("SELECT kind FROM catalyst_event_revisions WHERE event_id=?", (ev["id"],))]
        assert "CORROBORATED" in kinds and "REVISED" in kinds
    # denial from a reputable source
    b4 = {"cat:news:coindesk": {"_cat": "news:coindesk", "s": 200, "body": [{"title": "Binance denies Shielded Inu SHINU listing report", "link": "https://coindesk.com/x", "pub": "Wed, 07 Oct 2026 03:00:00 +0000"}]}}
    I.ingest_bodies(b4, retrieved_at=t0 + 7200)
    with tmpdb.connect() as con:
        ev = con.execute("SELECT * FROM catalyst_events").fetchone()
        assert ev["status"] == "DENIED"
    # resurfacing: same story 10 days later from a fresh domain
    b5 = {"cat:news:theblock": {"_cat": "news:theblock", "s": 200, "body": [{"title": "Binance will list Shielded Inu (SHINU) on spot", "link": "https://theblock.co/y", "pub": "Sat, 17 Oct 2026 01:00:00 +0000"}]}}
    s5 = I.ingest_bodies(b5, retrieved_at=t0 + 10 * 86400)
    with tmpdb.connect() as con:
        new = con.execute("SELECT * FROM catalyst_events ORDER BY id DESC LIMIT 1").fetchone()
        assert new["resurfaced"] == 1 and new["resurfaced_of"] is not None


def test_future_dated_flag_and_category(tmpdb):
    from memelab.catalyst import ingest as I
    t0 = time.time()
    b = {"cat:news:cointelegraph": _rss([{"title": "Memecoin hack drains $4M from pool", "link": "https://cointelegraph.com/h", "pub": time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(t0 + 12 * 3600))}])}
    I.ingest_bodies(b, retrieved_at=t0)
    with tmpdb.connect() as con:
        ev = con.execute("SELECT * FROM catalyst_events").fetchone()
        assert ev["future_dated"] == 1 and ev["category"] == "NEGATIVE"


def test_match_competing_and_assess(tmpdb):
    from memelab.catalyst import ingest as I, match as M, assess as A, attention
    t0 = time.time()
    I.ingest_bodies({"cat:news:cointelegraph": _rss([{"title": "Coinbase adds support for Super Inu (SI)", "link": "https://cointelegraph.com/si", "pub": "Wed, 07 Oct 2026 01:00:00 +0000"}])}, retrieved_at=t0)
    per_event, plan = M.terms_for_events()
    terms = list(per_event.values())[0]
    assert "SI" in terms and "Super Inu" in terms
    bodies = {"jup_tok:SI": [{"id": "DEW9dSN6QpWyNthphCpMmAbZP1Q4cEKR9xQXAri98WDP", "symbol": "SI", "name": "Super Inu", "liquidity": 2_000_000, "mcap": 25e6},
                             {"id": "Fake111111111111111111111111111111111111111", "symbol": "SI", "name": "Super Inu 2.0", "liquidity": 900_000, "mcap": 1e6}],
              "jup_tok:Super Inu": [{"id": "DEW9dSN6QpWyNthphCpMmAbZP1Q4cEKR9xQXAri98WDP", "symbol": "SI", "name": "Super Inu", "liquidity": 2_000_000}]}
    st = M.link_events(bodies, per_event)
    assert st["linked"] >= 1 and st["ambiguous"] >= 1
    with tmpdb.connect() as con:
        link = con.execute("SELECT * FROM catalyst_token_links").fetchone()
        assert link["mint"].startswith("DEW9") and link["link_strength"] == "AMBIGUOUS" and json.loads(link["competing_json"])[0]["mint"].startswith("Fake")
        ev = dict(con.execute("SELECT * FROM catalyst_events").fetchone())
    att = attention.sample_event(ev["id"], t=t0)
    res = A.assess(ev, dict(link), att, core=None, t=t0)
    # missing core data: UNKNOWN components earn zero and the verdict cannot be WATCH_FOR_ENTRY
    assert res["verdict"] in ("RESEARCH",) and res["components"]["execution_feasibility"]["grade"] == "UNKNOWN"
    assert res["triage_score"] <= 15 + 20 + 10 + 15
    # fatal override
    core = {"modules": {"identity": {"status": "IDENTITY NOT VERIFIED"}, "depth": {"exit_capacity_usd_3pct": 50000}}, "score": {"fatal_flags": [{"flag": "CANNOT_EXIT_5K", "evidence": "x"}]}, "bundle": {"market": {"price_usd": 0.03}}}
    res2 = A.assess(ev, dict(link), att, core, t=t0)
    assert res2["verdict"] == "REJECTED" and res2["triage_score"] == 0
    rid = A.store(ev["id"], link["mint"], res2, t=t0)
    with tmpdb.connect() as con:
        assert con.execute("SELECT status FROM catalyst_events WHERE id=?", (ev["id"],)).fetchone()["status"] == "REJECTED"
        assert con.execute("SELECT COUNT(*) c FROM catalyst_assessments").fetchone()["c"] == 1


def test_access_change_detector(tmpdb):
    from memelab.catalyst import ingest as I
    t0 = time.time()
    I.ingest_bodies({"cat:exch:coinbase:assets": {"_cat": "exch:coinbase:assets", "s": 200, "body": [{"id": "BTC"}, {"id": "SOL"}]}}, retrieved_at=t0)
    st = I.ingest_bodies({"cat:exch:coinbase:assets": {"_cat": "exch:coinbase:assets", "s": 200, "body": [{"id": "BTC"}, {"id": "SOL"}, {"id": "SHINU"}]}}, retrieved_at=t0 + 3600)
    assert st["access_changes"] and st["access_changes"][0]["asset"] == "SHINU"
    with tmpdb.connect() as con:
        ev = con.execute("SELECT * FROM catalyst_events WHERE category='ACCESS'").fetchone()
        assert ev["evidence_status"] == "CONFIRMED"


def test_monitor_alerts_and_report(tmpdb):
    from memelab.catalyst import ingest as I, monitor as MON, report as R
    t0 = time.time()
    with tmpdb.connect() as con:
        tmpdb.upsert_token(con, "DEW9dSN6QpWyNthphCpMmAbZP1Q4cEKR9xQXAri98WDP")
        con.execute("UPDATE tokens SET symbol='SI' WHERE mint LIKE 'DEW9%'")
        con.execute("INSERT INTO watchlist (mint, added_at, status, last_status_change) VALUES (?,?,?,?)", ("DEW9dSN6QpWyNthphCpMmAbZP1Q4cEKR9xQXAri98WDP", t0, "SETUP DEVELOPING", t0))
    I.ingest_bodies({"cat:news:cointelegraph": _rss([{"title": "SI token team wallet drained in exploit", "link": "https://cointelegraph.com/si-hack", "pub": "Wed, 07 Oct 2026 01:00:00 +0000"}])}, retrieved_at=t0)
    out = MON.run(t=t0 + 10)
    assert out["deteriorations"], "unlinked NEGATIVE event naming the watchlist symbol must raise a deterioration alert"
    md = R.render(t=t0 + 20)
    assert "Catalyst Intelligence report" in md and "DETERIORATION" in md and "ET" in md
