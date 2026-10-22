"""Firecrawl adapter for Catalyst Intelligence (memelab/catalyst/firecrawl.py). Every exchange is an invented fixture;
no test makes a network call (urlopen is patched to fail in the live-refusal tests)."""
import argparse
import copy
import json
import sqlite3
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / "tests" / "fixtures" / "catalyst" / "firecrawl"
MINT = "FrT7HpiiRiepDhLfokujd49yHAnhzMeTceY4PKyoxfjH"           # invented, see fixtures
COPYCAT = "72wubYQTaqaaFB5EsifS3WcJBPZRzkonaPY57ftHFCm7"         # invented
EVM = "0x55b4468d3105afbff8696e1af523ebad70554b4b"              # invented
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
T = 1792512000.0          # 2026-10-20T16:00:00Z, two hours after the fixture stories
FAKE_KEY = "fc-" + "ab" * 16     # built at run time: no key-shaped literal sits in the tree


@pytest.fixture()
def tmpdb(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_DB", str(tmp_path / "t.sqlite"))
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private" / "p.sqlite"))
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    monkeypatch.delenv("MEMELAB_FIRECRAWL_CONFIG", raising=False)
    import importlib
    from memelab import db
    importlib.reload(db)
    db.DB_PATH = tmp_path / "t.sqlite"
    db.init_db()
    yield db


def cfg(**over):
    from memelab.catalyst import firecrawl as FC
    raw = json.loads((FX / "config.json").read_text())
    for k, v in over.items():
        if isinstance(v, dict):
            raw.setdefault(k, {}).update(v)
        else:
            raw[k] = v
    return FC.validate_config(raw)


def seed(tmpdb, feed=None, t=T):
    from memelab.catalyst import ingest as I
    data = feed or json.loads((FX / "feed_fx01.json").read_text())
    bodies = {k: {"_cat": k[4:], "s": v.get("s"), "body": v.get("body")} for k, v in data.items() if k.startswith("cat:")}
    return I.ingest_bodies(bodies, retrieved_at=t)


def fixture(name):
    return json.loads((FX / name).read_text())


def scrape_ok(url, md="", links=(), status_code=200, credits=1, published=None):
    return {"recorded_at": "2026-10-20T16:00:00Z", "request": {"method": "POST", "path": "/v2/scrape", "match": {"url": url}},
            "response": {"status": 200, "body": {"success": True, "data": {"markdown": md, "links": list(links), "metadata": {
                "statusCode": status_code, "sourceURL": url, "url": url, "creditsUsed": credits, "publishedTime": published}}}}}


def api_error(url, status, code="X"):
    return {"recorded_at": "2026-10-20T16:00:00Z", "request": {"method": "POST", "path": "/v2/scrape", "match": {"url": url}},
            "response": {"status": status, "body": {"success": False, "code": code, "error": f"invented {status}"}}}


def feed_of(stories, source="news:cointelegraph"):
    """stories: [(title, url, pub epoch)] -> a feed with distinct, ungrouped stories."""
    from email.utils import formatdate
    return {f"cat:{source}": {"s": 200, "body": [{"title": t, "link": u, "pub": formatdate(p, usegmt=True), "desc": "invented"} for t, u, p in stories]}}


# ---------- config and readiness ----------

def test_config_validation_refuses_secrets_unknown_keys_bad_hosts_and_anti_bot_proxies():
    from memelab.catalyst import firecrawl as FC
    base = json.loads((FX / "config.json").read_text())
    assert FC.validate_config(base)["scrape"]["proxy"] == "basic"
    for bad, word in (({"budget": {"api_key": "x"}}, "FIRECRAWL_API_KEY"), ({"extra": 1}, "unknown config key"),
                      ({"base_url": "https://evil.example"}, "billing cloud"), ({"scrape": {"proxy": "stealth"}}, "basic or auto"),
                      ({"scrape": {"headers": {"Cookie": "a"}}}, "refused key"), ({"search": {"limit": 50}}, "search.limit"),
                      ({"enrich": {"tiers": ["social"]}}, "enrich.tiers"), ({"schema": "other"}, "schema")):
        raw = copy.deepcopy(base)
        for k, v in bad.items():
            if isinstance(v, dict) and isinstance(raw.get(k), dict):
                raw[k] = {**raw[k], **v}
            else:
                raw[k] = v
        with pytest.raises(FC.ConfigError) as e:
            FC.validate_config(raw)
        assert word in str(e.value), (bad, str(e.value))
    sh = {**copy.deepcopy(base), "billing": "self_hosted", "base_url": "http://localhost:3002"}
    assert FC.validate_config(sh)["base_url"] == "http://localhost:3002"
    with pytest.raises(FC.ConfigError):
        FC.validate_config({**sh, "base_url": "http://192.168.1.20:3002"})      # plain http only on this machine
    assert FC.validate_config({**sh, "base_url": "https://firecrawl.home.example"})["billing"] == "self_hosted"


def test_example_config_is_valid_and_off(tmp_path):
    from memelab.catalyst import firecrawl as FC
    ex = FC.validate_config(json.loads((ROOT / "docs" / "catalyst" / "firecrawl.example.json").read_text()))
    assert ex["enabled"] is False and ex["budget"]["max_credits_per_run"] == 0 and ex["budget"]["allow_billable"] is False
    assert ex["scrape"]["proxy"] == "basic" and ex["search"]["enabled"] is False and ex["pull_fallback"]["sources"] == []
    assert FC.readiness(ex, FAKE_KEY)[0] == "disabled"


def test_readiness_states():
    from memelab.catalyst import firecrawl as FC
    assert FC.readiness(None, None)[0] == "config_missing"
    assert FC.readiness(None, None, "bad json")[0] == "config_invalid"
    assert FC.readiness(cfg(enabled=False), FAKE_KEY)[0] == "disabled"
    assert FC.readiness(cfg(), None)[0] == "credentials_missing"
    assert FC.readiness(cfg(budget={"max_credits_per_month": 0}), FAKE_KEY)[0] == "caps_zero"
    assert FC.readiness(cfg(budget={"usd_per_credit": 0.004}), FAKE_KEY)[0] == "billing_not_consented"
    assert FC.readiness(cfg(budget={"usd_per_credit": 0.004, "allow_billable": True}), FAKE_KEY)[0] == "ready"
    assert FC.readiness(cfg(billing="self_hosted", base_url="http://127.0.0.1:3002"), None)[0] == "ready"


def test_load_config_missing_and_invalid(tmp_path):
    from memelab.catalyst import firecrawl as FC
    assert FC.load_config(tmp_path / "none.json")[0] is None and FC.load_config(tmp_path / "none.json")[2] is None
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    c, _, err = FC.load_config(p)
    assert c is None and err


# ---------- enrichment ----------

def test_enrich_keeps_hashes_and_identifiers_never_page_text(tmpdb, tmp_path):
    from memelab.catalyst import firecrawl as FC
    seed(tmpdb)
    tr = FC.FixtureTransport(fixture("fx_enrich.json"))
    with tmpdb.connect() as con:
        st = FC.enrich(con, cfg(), tr, mode="fixture", run_id="fx1", now=T + 60)
    assert (st["ok"], st["robots_disallowed"], st["robots_unreachable"], st["credits"], st["requests"]) == (2, 1, 1, 2, 2)
    # only the two allowed pages were requested, with the configured request shape
    assert [c["url"] for c in tr.calls] == ["https://cointelegraph.com/news/fixture-moonfrog-binance-listing", "https://decrypt.co/fixture-moonfrog-binance"]
    b = tr.calls[0]["body"]
    assert b["formats"] == ["markdown", "links"] and b["proxy"] == "basic" and b["parsers"] == [] and b["onlyMainContent"] is True
    assert "zeroDataRetention" not in b and "location" not in b and "headers" not in b and "actions" not in b
    with tmpdb.connect() as con:
        rows = {r["requested_url"]: dict(r) for r in con.execute("SELECT * FROM catalyst_page_fetches")}
        ct = rows["https://cointelegraph.com/news/fixture-moonfrog-binance-listing"]
        assert ct["status"] == "OK" and len(ct["content_sha256"]) == 64 and ct["word_count"] > 20 and ct["language"] == "en"
        assert ct["final_url"] == "https://cointelegraph.com/news/fixture-moonfrog-binance-listing"     # query (utm, session) dropped
        assert ct["page_published_at"] == 1792504500.0 and ct["credits_used"] == 1 and ct["private_ref"].startswith("sha256:")
        assert rows["https://news.google.com/rss/articles/FIXTURE-ARTICLE-1"]["status"] == "ROBOTS_DISALLOWED"
        assert rows["https://www.theblock.co/post/fixture-fee-switch"]["status"] == "ROBOTS_UNREACHABLE"
        facts = {(r["kind"], r["value"], r["chain_hint"]) for r in con.execute("SELECT kind, value, chain_hint FROM catalyst_page_facts")}
        assert ("ADDRESS_LINK", MINT, "solana") in facts and ("CONTRACT", EVM, "evm") in facts and ("TICKER", "MFROG", None) in facts
        assert ("CITED_DOMAIN", "cointelegraph.com", None) in facts and ("CITED_DOMAIN", "binance.com", None) in facts
        spend = [dict(r) for r in con.execute("SELECT * FROM social_api_spend WHERE connector='firecrawl'")]
        assert len(spend) == 2 and {s["mode"] for s in spend} == {"fixture"} and sum(json.loads(s["resources_json"])["credits"] for s in spend) == 2
        assert all(s["endpoint"] == "/v2/scrape" and s["est_cost_usd"] == 0 for s in spend)
    # the page wording never reached the public database; the private copy holds it for 7 days
    dump = "\n".join(sqlite3.connect(tmpdb.DB_PATH).iterdump())
    assert "FIXTURE-SENTENCE" not in dump and "invented test wording" not in dump
    pcon = sqlite3.connect(tmp_path / "private" / "p.sqlite")
    rows = pcon.execute("SELECT exact_text, retain_until - stored_at, platform FROM private_content").fetchall()
    assert len(rows) == 2 and all(r[1] == 7 * 86400 and r[2] == "web" for r in rows) and any("FIXTURE-SENTENCE-ALPHA" in r[0] for r in rows)


def test_enrich_second_run_reads_nothing_again(tmpdb):
    from memelab.catalyst import firecrawl as FC
    seed(tmpdb)
    with tmpdb.connect() as con:
        FC.enrich(con, cfg(), FC.FixtureTransport(fixture("fx_enrich.json")), mode="fixture", run_id="fx1", now=T + 60)
        tr2 = FC.FixtureTransport(fixture("fx_enrich.json"))
        st = FC.enrich(con, cfg(), tr2, mode="fixture", run_id="fx2", now=T + 120)
    assert tr2.calls == [] and tr2.robots_calls == [] and st["already_read"] == 2 and st["recent_failure"] == 2 and st["credits"] == 0


def test_enrich_retries_a_failed_robots_check_after_the_wait(tmpdb):
    from memelab.catalyst import firecrawl as FC
    seed(tmpdb)
    with tmpdb.connect() as con:
        FC.enrich(con, cfg(), FC.FixtureTransport(fixture("fx_enrich.json")), mode="fixture", run_id="fx1", now=T + 60)
        tr = FC.FixtureTransport(fixture("fx_enrich.json"))
        st = FC.enrich(con, cfg(enrich={"event_window_hours": 72}), tr, mode="fixture", run_id="fx2", now=T + 60 + 25 * 3600)
    assert st["robots_disallowed"] == 1 and st["robots_unreachable"] == 1 and tr.calls == []


def test_copies_and_refused_platforms_are_never_requested(tmpdb):
    from memelab.catalyst import firecrawl as FC
    body = "Invented identical wire copy about a fixture listing that two outlets published word for word today, long enough to compare."
    feed = {"cat:news:cointelegraph": {"s": 200, "body": [
                {"title": "Exchange lists Pondfrog PFROG token for spot trading", "link": "https://cointelegraph.com/news/fx-pondfrog", "pub": "Tue, 20 Oct 2026 14:00:00 +0000", "desc": body}]},
            "cat:news:coindesk": {"s": 200, "body": [
                {"title": "Exchange lists Pondfrog PFROG token for spot trading", "link": "https://www.coindesk.com/fx-pondfrog", "pub": "Tue, 20 Oct 2026 14:05:00 +0000", "desc": body}]},
            "cat:news:decrypt": {"s": 200, "body": [
                {"title": "Viral clip of a dancing hamster spawns tokens", "link": "https://x.com/someone/status/123", "pub": "Tue, 20 Oct 2026 13:00:00 +0000", "desc": "invented"},
                {"title": "Video interview on hamster token craze", "link": "https://www.youtube.com/watch?v=abcdefghijk", "pub": "Tue, 20 Oct 2026 12:00:00 +0000", "desc": "invented"}]}}
    seed(tmpdb, feed)
    with tmpdb.connect() as con:
        roles = {r["url"]: r["role"] for r in con.execute("SELECT i.url, es.role FROM catalyst_items i JOIN catalyst_event_sources es ON es.item_id=i.id")}
        assert roles["https://www.coindesk.com/fx-pondfrog"] == "SYNDICATED"
        targets, _ = FC.select_targets(con, cfg(), T + 60, mode="fixture")
        assert "https://www.coindesk.com/fx-pondfrog" not in [t["url"] for t in targets]
        fx = {"schema": FC.FIXTURE_SCHEMA, "robots": {"cointelegraph.com": "User-agent: *\nAllow: /\n"},
              "exchanges": [scrape_ok("https://cointelegraph.com/news/fx-pondfrog", "# invented page\n\nWords about nothing.")]}
        tr = FC.FixtureTransport(fx)
        st = FC.enrich(con, cfg(), tr, mode="fixture", run_id="fx", now=T + 60)
    assert st["refused_host"] == 2 and st["ok"] == 1
    assert [c["url"] for c in tr.calls] == ["https://cointelegraph.com/news/fx-pondfrog"]
    assert not any("x.com" in u or "youtube" in u for u in tr.robots_calls)
    for u in ("https://x.com/a", "https://mobile.twitter.com/a", "https://old.reddit.com/r/x", "https://t.me/s/chan",
              "https://discord.gg/abc", "https://youtu.be/abc", "https://warpcast.com/a", "https://user:pw@example.com/a", "ftp://example.com/a"):
        assert FC.refused_reason(u), u
    assert FC.refused_reason("https://www.coindesk.com/markets/x") is None


def test_one_robots_refusal_covers_the_whole_site_until_the_wait_passes(tmpdb):
    from memelab.catalyst import firecrawl as FC
    titles = ("Lighthouse keepers union wins pension case", "Orchard harvest festival draws record crowds", "Submarine cable repair finishes early")
    stories = [(t, f"https://news.google.com/rss/articles/FIXTURE-{i}", T - 600 * (i + 1)) for i, t in enumerate(titles)]
    seed(tmpdb, feed_of(stories, source="news:gnews:memecoin"))
    with tmpdb.connect() as con:
        st = FC.enrich(con, cfg(), FC.FixtureTransport(fixture("fx_enrich.json")), mode="fixture", run_id="g1", now=T + 60)
        assert st["robots_disallowed"] == 1 and st["site_refused_robots"] == 2
        assert con.execute("SELECT COUNT(*) FROM catalyst_page_fetches").fetchone()[0] == 1
        st2 = FC.enrich(con, cfg(), FC.FixtureTransport(fixture("fx_enrich.json")), mode="fixture", run_id="g2", now=T + 120)
        assert st2["targets"] == 0 and st2["recent_failure"] == 1 and st2["site_refused_robots"] == 2


def test_robots_follow_rfc_9309():
    from memelab.catalyst import firecrawl as FC
    answers = {"https://a.test/robots.txt": (200, "User-agent: *\nDisallow: /\n\nUser-agent: FirecrawlAgent\nAllow: /news/\nDisallow: /\n"),
               "https://b.test/robots.txt": (404, ""), "https://c.test/robots.txt": (403, ""), "https://d.test/robots.txt": (503, ""),
               "https://e.test/robots.txt": (None, ""), "https://f.test/robots.txt": (429, ""),
               "https://g.test/robots.txt": (200, "User-agent: *\nDisallow: /private/\n")}
    calls = []

    def fetch(u):
        calls.append(u)
        return answers[u]
    r = FC.Robots(fetch)
    assert r.check("https://a.test/news/x") == (True, "ROBOTS_ALLOWED")          # the specific group wins over *
    assert r.check("https://a.test/other") == (False, "ROBOTS_DISALLOWED")
    assert r.check("https://b.test/x") == (True, "ROBOTS_NONE")                   # 4xx: no rules
    assert r.check("https://c.test/x") == (True, "ROBOTS_NONE")
    assert r.check("https://d.test/x") == (False, "ROBOTS_UNREACHABLE")           # 5xx: disallow all
    assert r.check("https://e.test/x") == (False, "ROBOTS_UNREACHABLE")
    assert r.check("https://f.test/x") == (False, "ROBOTS_UNREACHABLE")
    assert r.check("https://g.test/a") == (True, "ROBOTS_ALLOWED") and r.check("https://g.test/private/1")[0] is False
    assert calls.count("https://a.test/robots.txt") == 1                            # one read per origin per run


# ---------- caps, errors, redaction ----------

def _five_stories(tmpdb):
    urls = [f"https://cointelegraph.com/news/fx-story-{i}" for i in range(5)]
    titles = ["Alpha protocol unveils staking vaults", "Bravo exchange halts withdrawals briefly", "Charlie chain upgrade date announced",
              "Delta foundation grants program expands", "Echo wallet adds hardware support"]
    seed(tmpdb, feed_of([(titles[i], urls[i], T - 600 * (i + 1)) for i in range(5)]))
    return urls


def test_run_and_month_credit_caps_stop_before_the_request(tmpdb):
    from memelab.catalyst import firecrawl as FC
    from memelab.social.api_common import billing_day
    urls = _five_stories(tmpdb)
    robots = {"cointelegraph.com": "User-agent: *\nAllow: /\n"}
    fx = {"schema": FC.FIXTURE_SCHEMA, "robots": robots, "exchanges": [scrape_ok(u, "invented page words") for u in urls]}
    with tmpdb.connect() as con:
        tr = FC.FixtureTransport(fx)
        st = FC.enrich(con, cfg(budget={"max_credits_per_run": 2}), tr, mode="fixture", run_id="cap1", now=T + 60)
        assert st["ok"] == 2 and len(tr.calls) == 2 and st["stopped"].startswith("RUN_CREDIT_CAP")
        # month cap: 50 per month, 48 already used in this UTC month (2 by the run above + 46 recorded earlier); live rows and
        # rows from last month do not count against a fixture run
        con.execute("INSERT INTO social_api_spend(connector,run_id,endpoint,http_status,billing_day,resources_json,est_cost_usd,mode,requested_at)"
                    " VALUES ('firecrawl','old','/v2/scrape',200,?, '{\"credits\": 46}',0,'fixture',?)", (billing_day(T), T))
        con.execute("INSERT INTO social_api_spend(connector,run_id,endpoint,http_status,billing_day,resources_json,est_cost_usd,mode,requested_at)"
                    " VALUES ('firecrawl','live','/v2/scrape',200,?, '{\"credits\": 900}',0,'live',?)", (billing_day(T), T))
        con.execute("INSERT INTO social_api_spend(connector,run_id,endpoint,http_status,billing_day,resources_json,est_cost_usd,mode,requested_at)"
                    " VALUES ('firecrawl','prev','/v2/scrape',200,'2026-09-30', '{\"credits\": 900}',0,'fixture',?)", (T - 30 * 86400,))
        con.commit()
        assert FC.month_credits(con, "fixture", T) == 48
        tr2 = FC.FixtureTransport(fx)
        st2 = FC.enrich(con, cfg(), tr2, mode="fixture", run_id="cap2", now=T + 120)
    assert st2["ok"] == 2 and st2["stopped"].startswith("MONTH_CREDIT_CAP") and len(tr2.calls) == 2


def test_provider_errors_retry_record_and_stop(tmpdb):
    from memelab.catalyst import firecrawl as FC
    urls = _five_stories(tmpdb)
    fx = {"schema": FC.FIXTURE_SCHEMA, "robots": {"cointelegraph.com": "User-agent: *\nAllow: /\n"}, "exchanges": [
        api_error(urls[0], 503), scrape_ok(urls[0], "invented words after a retry"),
        scrape_ok(urls[1], "", status_code=404),                    # the page itself answered 404: Firecrawl still bills 1
        api_error(urls[2], 408, "SCRAPE_TIMEOUT"),                  # no document: no credit, keep going
        api_error(urls[3], 402),                                    # credits used up: stop the run
        scrape_ok(urls[4], "never requested")]}
    tr = FC.FixtureTransport(fx)
    with tmpdb.connect() as con:
        st = FC.enrich(con, cfg(), tr, mode="fixture", run_id="err", now=T + 60)
        rows = {r["requested_url"]: dict(r) for r in con.execute("SELECT * FROM catalyst_page_fetches")}
        spend = con.execute("SELECT COUNT(*), SUM(CAST(json_extract(resources_json,'$.credits') AS INT)) FROM social_api_spend").fetchone()
    assert [c["url"] for c in tr.calls] == [urls[0], urls[0], urls[1], urls[2], urls[3]]
    assert rows[urls[0]]["status"] == "OK" and rows[urls[1]]["status"] == "TARGET_HTTP_ERROR" and rows[urls[1]]["credits_used"] == 1
    assert rows[urls[2]]["status"] == "PROVIDER_TIMEOUT" and rows[urls[3]]["status"] == "PROVIDER_PAYMENT_REQUIRED" and urls[4] not in rows
    assert st["stopped"].startswith("PAYMENT_REQUIRED") and tuple(spend) == (5, 2)
    from memelab.catalyst import cli
    with pytest.raises(SystemExit) as e:
        cli._fc_exit(st)
    assert e.value.code == 1


def test_transport_errors_are_redacted(tmpdb):
    from memelab.catalyst import firecrawl as FC
    from memelab.social.ingest import redact
    urls = _five_stories(tmpdb)
    boom = {"recorded_at": "2026-10-20T16:00:00Z", "request": {"method": "POST", "path": "/v2/scrape", "match": {"url": urls[0]}},
            "raise": "connection reset; Authorization: Bearer {secret}; key={secret}"}
    fx = {"schema": FC.FIXTURE_SCHEMA, "robots": {"cointelegraph.com": "User-agent: *\nAllow: /\n"}, "exchanges": [boom, dict(boom)]}
    with tmpdb.connect() as con:
        FC.enrich(con, cfg(enrich={"max_pages_per_run": 1}), FC.FixtureTransport(fx, secret=FAKE_KEY), mode="fixture", run_id="r",
                  now=T + 60, secret=FAKE_KEY)
        err = con.execute("SELECT status, error FROM catalyst_page_fetches").fetchone()
    assert err[0] == "PROVIDER_TRANSPORT_ERROR" and FAKE_KEY not in err[1] and "[REDACTED]" in err[1]
    assert FAKE_KEY not in redact(f"plain text mentioning {FAKE_KEY} somewhere")
    assert FAKE_KEY not in FC.scrub(f"x {FAKE_KEY} y")


def test_remote_balance_caps_the_run_and_a_rejected_key_stops_it(tmpdb):
    from memelab.catalyst import firecrawl as FC
    urls = _five_stories(tmpdb)
    bal = lambda status, body: {"recorded_at": "2026-10-20T16:00:00Z", "request": {"method": "GET", "path": "/v2/team/credit-usage"},
                                "response": {"status": status, "body": body}}
    robots = {"cointelegraph.com": "User-agent: *\nAllow: /\n"}
    fx = {"schema": FC.FIXTURE_SCHEMA, "robots": robots,
          "exchanges": [bal(200, {"success": True, "data": {"remainingCredits": 3}})] + [scrape_ok(u, "invented words") for u in urls]}
    tr = FC.FixtureTransport(fx)
    with tmpdb.connect() as con:
        st = FC.enrich(con, cfg(budget={"check_remote_balance": True, "min_remaining_credits": 1}), tr, mode="fixture", run_id="b", now=T + 60)
    assert [c["path"] for c in tr.calls] == ["/v2/team/credit-usage", "/v2/scrape", "/v2/scrape"]
    assert st["ok"] == 2 and st["stopped"].startswith("REMOTE_BALANCE")
    fx2 = {"schema": FC.FIXTURE_SCHEMA, "robots": robots, "exchanges": [bal(401, {"success": False, "error": "Unauthorized"})]}
    tr2 = FC.FixtureTransport(fx2)
    with tmpdb.connect() as con:
        st2 = FC.enrich(con, cfg(budget={"check_remote_balance": True}), tr2, mode="fixture", run_id="b2", now=T + 120)
    assert [c["path"] for c in tr2.calls] == ["/v2/team/credit-usage"] and st2["stopped"].startswith("UNAUTHORIZED")


def test_page_history_and_spend_survive_a_new_session_through_the_state_export(tmp_path, monkeypatch):
    """Scheduled runs start from a fresh database and import state/latest.json. Pages already paid for must not be read
    again, their facts must still reach the new session's events, and the month's credits must still count. Uses the real
    clock because the export window is relative to now."""
    import importlib
    from memelab import db
    from memelab.catalyst import firecrawl as FC, match as M
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "p.sqlite"))
    now = time.time()

    def fresh(name):
        monkeypatch.setenv("MEMELAB_DB", str(tmp_path / name))
        importlib.reload(db)
        db.DB_PATH = tmp_path / name
        db.init_db()
        return db
    d1 = fresh("session1.sqlite")
    seed(d1, t=now)
    with d1.connect() as con:
        FC.enrich(con, cfg(), FC.FixtureTransport(fixture("fx_enrich.json")), mode="live", run_id="s1", now=now + 60)
        con.execute("INSERT INTO catalyst_page_fetches(run_id,purpose,provider,access_mode,requested_url,url_key,status,fetched_at)"
                    " VALUES ('fx','ENRICH','firecrawl','fixture','https://example.test/fixture-only','https://example.test/fixture-only','OK',?)", (now,))
    from memelab import state
    out = state.export(tmp_path / "latest.json")
    tables = json.loads(out.read_text())["_tables"]
    assert len(tables["catalyst_page_fetches"]) == 4 and all(r["access_mode"] == "live" for r in tables["catalyst_page_fetches"])
    assert {r["connector"] for r in tables["social_api_spend"]} == {"firecrawl"} and len(tables["social_api_spend"]) == 2
    assert "FIXTURE-SENTENCE" not in out.read_text()
    d2 = fresh("session2.sqlite")
    added = state.import_(str(out))
    assert added["catalyst_page_fetches"] == 4 and added["catalyst_page_facts"] == 7 and added["social_api_spend"] == 2
    assert state.import_(str(out))["catalyst_page_fetches"] == 0                       # importing twice adds nothing
    seed(d2, t=now + 3600)
    with d2.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM catalyst_page_fetches WHERE event_id IS NOT NULL OR item_id IS NOT NULL").fetchone()[0] == 0
        assert FC.event_contracts(con, 1) == [MINT] and FC.month_credits(con, "live", now + 3600) == 2
        tr = FC.FixtureTransport(fixture("fx_enrich.json"))
        st = FC.enrich(con, cfg(), tr, mode="live", run_id="s2", now=now + 3660)
    assert tr.calls == [] and st["already_read"] == 2 and st["recent_failure"] == 2
    assert M.terms_for_events()[0][1][0] == MINT


def test_fixture_runs_are_refused_on_the_tracked_database(tmpdb, monkeypatch):
    from memelab.catalyst import cli
    monkeypatch.setattr(cli.db, "DB_PATH", cli.db.ROOT / "data" / "memelab.sqlite")
    a = argparse.Namespace(config=str(FX / "config.json"), fixture=str(FX / "fx_enrich.json"))
    with pytest.raises(SystemExit) as e:
        cli._fc_setup(a)
    assert "refused against the tracked database" in str(e.value.code)


def test_live_runs_without_key_or_config_refuse_before_any_network_call(tmpdb, tmp_path, monkeypatch, capsys):
    import urllib.request
    from memelab.catalyst import cli

    def no_network(*a, **k):
        raise AssertionError("network call attempted")
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    live = tmp_path / "fc.json"
    live.write_text((FX / "config.json").read_text())
    for config, reason in ((str(tmp_path / "missing.json"), "config_missing"), (str(live), "credentials_missing")):
        for fn, extra in ((cli.cmd_enrich, dict(limit=None, event=None, now=None, run_id=None)),
                          (cli.cmd_fc_search, dict(query=None, events=3, now=None, run_id=None, no_ingest=False))):
            with pytest.raises(SystemExit) as e:
                fn(argparse.Namespace(config=config, fixture=None, **extra))
            assert e.value.code == 1
            assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["reason"] == reason


# ---------- match, attention, report ----------

def _enriched(tmpdb):
    from memelab.catalyst import firecrawl as FC
    seed(tmpdb)
    with tmpdb.connect() as con:
        FC.enrich(con, cfg(), FC.FixtureTransport(fixture("fx_enrich.json")), mode="fixture", run_id="fx1", now=T + 60)


def test_contract_named_on_a_page_leads_the_search_and_links_as_named_in_source(tmpdb):
    from memelab.catalyst import match as M
    _enriched(tmpdb)
    with tmpdb.connect() as con:
        # a stablecoin named on a page is not a catalyst term
        fid = con.execute("SELECT id FROM catalyst_page_fetches WHERE status='OK' ORDER BY id LIMIT 1").fetchone()[0]
        con.execute("INSERT INTO catalyst_page_facts(fetch_id,kind,value,chain_hint) VALUES (?,?,?,?)", (fid, "CONTRACT", USDC, "solana"))
    per_event, plan = M.terms_for_events()
    ev1 = per_event[1]
    assert ev1[0] == MINT and USDC not in ev1 and EVM not in ev1 and "MFROG" in ev1
    keys = [r["key"] for r in plan.to_dict()["reqs"]]
    assert f"jup_tok:{MINT}" in keys and f"ds_search:{MINT}" in keys
    bodies = {f"jup_tok:{MINT}": [{"id": MINT, "symbol": "MFROG", "name": "Moonfrog", "liquidity": 50_000}],
              "jup_tok:MFROG": [{"id": MINT, "symbol": "MFROG", "name": "Moonfrog", "liquidity": 50_000},
                                {"id": COPYCAT, "symbol": "MFROG", "name": "Moonfrog Copy", "liquidity": 200_000}]}
    M.link_events(bodies, {1: ev1})
    with tmpdb.connect() as con:
        links = {r["mint"]: dict(r) for r in con.execute("SELECT * FROM catalyst_token_links WHERE event_id=1")}
    assert links[MINT]["link_type"] == "NAMED_IN_SOURCE" and links[MINT]["link_strength"] == "STRONG"
    assert "named on a page read for this event" in links[MINT]["rationale"]
    assert links[COPYCAT]["link_strength"] == "AMBIGUOUS" and "symbol collision" in links[COPYCAT]["rationale"]


def test_address_term_never_links_a_different_mint(tmpdb):
    from memelab.catalyst import match as M
    _enriched(tmpdb)
    # the address search answered with a pair whose base token is another mint: no link from the address term
    bodies = {f"ds_search:{MINT}": {"pairs": [{"chainId": "solana", "baseToken": {"address": COPYCAT, "symbol": "X", "name": "X"},
                                               "liquidity": {"usd": 90_000}}]}}
    M.link_events(bodies, {1: [MINT]})
    with tmpdb.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM catalyst_token_links").fetchone()[0] == 0


def test_match_works_on_a_database_without_page_tables(tmpdb):
    from memelab.catalyst import match as M
    con = sqlite3.connect(":memory:")
    assert M.page_contracts(con, 1) == []


def test_citation_check_counts_derivative_coverage_only_when_every_source_was_read(tmpdb):
    from memelab.catalyst import assess as A, attention, firecrawl as FC
    _enriched(tmpdb)
    with tmpdb.connect() as con:
        cit = FC.citation_check(con, 1)
    assert cit == {"sources": 2, "read": 2, "complete": True, "citing": ["decrypt.co"], "uncited_publishers": 1}
    att = attention.sample_event(1, t=T + 120)
    assert att["metrics"]["uncited_publishers"] == 1 and any(f.startswith("CITES OTHER COVERAGE: decrypt.co") for f in att["flags"])
    with tmpdb.connect() as con:
        ev = dict(con.execute("SELECT * FROM catalyst_events WHERE id=1").fetchone())
    res = A.assess(ev, None, att, None, t=T + 120)
    assert res["components"]["attention_quality"]["uncited_publishers"] == 1
    # with the citation only one publisher is uncited, so the independence point is not earned (WEAK instead of MODERATE)
    no_cit = {**att, "metrics": {**att["metrics"], "uncited_publishers": None}}
    assert res["components"]["attention_quality"]["grade"] == "WEAK"
    assert A.assess(ev, None, no_cit, None, t=T + 120)["components"]["attention_quality"]["grade"] == "MODERATE"
    # a third publisher found later and not yet read makes the check partial: no uncited count
    from memelab.catalyst import ingest as I
    I.ingest_bodies({"cat:news:coindesk": {"_cat": "news:coindesk", "s": 200, "body": [
        {"title": "Binance will list Moonfrog MFROG on spot trading", "link": "https://www.coindesk.com/fx-moonfrog", "pub": "Tue, 20 Oct 2026 15:00:00 +0000", "desc": "x"}]}},
        retrieved_at=T + 200)
    with tmpdb.connect() as con:
        cit2 = FC.citation_check(con, 1)
    assert cit2["complete"] is False and cit2["uncited_publishers"] is None
    att2 = attention.sample_event(1, t=T + 300)
    assert att2["metrics"]["uncited_publishers"] is None and any("citation check partial" in n for n in att2["notes"])


def test_report_shows_pages_read_and_contracts(tmpdb):
    from memelab.catalyst import match as M, report as R
    _enriched(tmpdb)
    M.link_events({f"jup_tok:{MINT}": [{"id": MINT, "symbol": "MFROG", "name": "Moonfrog", "liquidity": 50_000}]}, {1: [MINT]})
    md = R.render(t=T + 300)
    assert "Pages read: 2 of 2 attempt(s)" in md and f"solana `{MINT}`" in md and "$MFROG" in md
    assert "Article pages (Firecrawl): none read in the last 36h" in md      # fixture rows are never live coverage
    assert "FIXTURE-SENTENCE" not in md


# ---------- search ----------

def test_search_finds_other_publishers_and_drops_known_and_refused_urls(tmpdb):
    from memelab.catalyst import firecrawl as FC, ingest as I
    seed(tmpdb)
    tr = FC.FixtureTransport(fixture("fx_search.json"))
    with tmpdb.connect() as con:
        bodies, st = FC.search(con, cfg(), tr, mode="fixture", run_id="s1", now=T + 60, events=5)
    assert (st["queries"], st["results"], st["kept"], st["already_stored"], st["refused_host"], st["credits"]) == (2, 3, 1, 1, 1, 4)
    q = tr.calls[0]["body"]
    assert q["sources"] == ["news"] and q["tbs"] == "qdr:w" and "scrapeOptions" not in q and q["limit"] == 10
    # three events have at most 2 independent sources; max_queries_per_run 2 searches the two newest
    assert {c["query"] for c in tr.calls} == {"Binance will list Moonfrog (MFROG) on spot trading", "Senate shutdown vote scheduled for Friday"}
    s = I.ingest_bodies(bodies, retrieved_at=T + 60)
    assert s["items_new"] == 1 and s["events_corroborated"] == 1
    with tmpdb.connect() as con:
        ev = con.execute("SELECT independent_sources FROM catalyst_events WHERE id=1").fetchone()[0]
        src = con.execute("SELECT tier, access_mode FROM catalyst_sources WHERE source_id='web:firecrawl:search'").fetchone()
        raw = json.loads(con.execute("SELECT raw_json FROM catalyst_items WHERE source_id='web:firecrawl:search'").fetchone()[0])
    assert ev == 3 and tuple(src) == ("aggregator", "api") and "query" not in raw and len(raw["query_sha"]) == 16


def test_search_times_keep_only_hour_precision_relative_dates():
    from memelab.catalyst import firecrawl as FC
    assert FC.search_time("2 hours ago", T) == T - 7200 and FC.search_time("45 minutes ago", T) == T - 2700
    assert FC.search_time("3 days ago", T) is None and FC.search_time("2026-10-20T15:10:00Z", T) == T - 50 * 60
    assert FC.search_time("2030-01-01T00:00:00Z", T) is None and FC.search_time(None, T) is None


def test_search_query_mode_and_disabled_search(tmpdb, tmp_path, monkeypatch, capsys):
    from memelab.catalyst import firecrawl as FC, cli
    seed(tmpdb)
    fx = {"schema": FC.FIXTURE_SCHEMA, "exchanges": [{"recorded_at": "2026-10-20T16:00:00Z",
          "request": {"method": "POST", "path": "/v2/search", "match": {"query": "solana memecoin listing"}},
          "response": {"status": 200, "body": {"success": True, "creditsUsed": 2, "data": {"web": [
              {"url": "https://decrypt.co/fx-other-story", "title": "Another invented story", "description": "d"}]}}}}]}
    tr = FC.FixtureTransport(fx)
    with tmpdb.connect() as con:
        bodies, st = FC.search(con, cfg(), tr, mode="fixture", run_id="q", now=T, query="solana memecoin listing")
    assert tr.calls[0]["body"]["tbs"] == "qdr:d" and st["kept"] == 1
    off = tmp_path / "off.json"
    raw = json.loads((FX / "config.json").read_text())
    raw["search"]["enabled"] = False
    off.write_text(json.dumps(raw))
    with pytest.raises(SystemExit) as e:
        cli.cmd_fc_search(argparse.Namespace(config=str(off), fixture=str(FX / "fx_search.json"), query=None, events=2, now=T,
                                             run_id=None, no_ingest=False))
    assert e.value.code == 1 and "search_disabled" in capsys.readouterr().out


# ---------- navigate-mode fallback ----------

def test_pull_fallback_reads_listed_sources_only_and_parses_rendered_json(tmpdb):
    from memelab.catalyst import cli, firecrawl as FC
    from memelab.catalyst.sources import active_sources, sync_registry
    with tmpdb.connect() as con:
        sync_registry(con)
        nav = [s for s in active_sources(con, modes=("navigate",)) if s["source_id"] in ("exch:binance:listings", "exch:okx:listings")]
        tr = FC.FixtureTransport(fixture("fx_pull.json"))
        got, st = FC.pull_fallback(con, cfg(), tr, nav, mode="fixture", run_id="p", parse=cli._parse_page, now=T)
        row = dict(con.execute("SELECT * FROM catalyst_page_fetches").fetchone())
    assert st["listed"] == 1 and st["not_listed"] == 1 and st["ok"] == 1 and len(tr.calls) == 1
    assert tr.calls[0]["body"]["formats"] == ["rawHtml"] and tr.calls[0]["body"]["onlyMainContent"] is False
    entry = got["cat:exch:binance:listings"]
    assert entry["s"] == 200 and entry["via"] == "firecrawl" and entry["body"][0]["title"].startswith("Binance Will List Moonfrog")
    assert row["purpose"] == "PULL_FALLBACK" and row["status"] == "OK" and row["final_url"].endswith("/article/list/query")
    from memelab.catalyst import ingest as I
    s = I.ingest_bodies({"cat:exch:binance:listings": {"_cat": "exch:binance:listings", "s": 200, "body": entry["body"]}}, retrieved_at=T)
    assert s["events_new"] == 1


def test_page_text_from_raw():
    from memelab.catalyst import firecrawl as FC
    assert FC.page_text_from_raw('{"a": 1}') == '{"a": 1}'
    assert FC.page_text_from_raw("<html><pre>{&quot;a&quot;: 1}</pre></html>") == '{"a": 1}'
    assert FC.page_text_from_raw("<html><body><rss version='2.0'><channel/></rss></body></html>").startswith("<rss")


# ---------- facts, health, guard, audit ----------

def test_page_facts_reject_lookalike_words_and_keep_only_identifiers():
    from memelab.catalyst import firecrawl as FC
    short = "2" + "z" * 31            # base58 characters, 32 long, but decodes to far fewer than 32 bytes
    md = ("Words like ThisIsNotAKeyButLooksLikeOneMaybeXX and AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA are not keys, nor is "
          f"{short}. Real-shaped: {MINT} and {EVM.upper().replace('0X', '0x')} and $GOOD and a tx 0x{'a' * 64}.")
    facts = FC.page_facts(md, ["https://www.example-news.test/story", "https://example-news.test/other", "mailto:x@y.z"], "example-news.test")
    kinds = {(k, v) for k, v, _ in facts}
    assert ("CONTRACT", MINT) in kinds and ("CONTRACT", EVM) in kinds and ("TICKER", "GOOD") in kinds
    assert not any("ThisIsNot" in v or v.startswith("AAAA") or v == short for _, v in kinds)
    assert not FC.is_solana_pubkey(short)
    assert not any(k == "CITED_DOMAIN" for k, _ in kinds)            # own domain and its www. alias are not citations
    assert FC.is_solana_pubkey("So11111111111111111111111111111111111111112") and not FC.is_solana_pubkey("1" * 44)


def test_health_reports_status_credits_and_remote_balance(tmpdb, monkeypatch):
    from memelab.catalyst import firecrawl as FC
    with tmpdb.connect() as con:
        assert FC.health(con, None, key=None)["status"] == "config_missing"
        assert FC.health(con, cfg(), key=FAKE_KEY)["status"] == "configured_unverified"
        fx = {"schema": FC.FIXTURE_SCHEMA, "exchanges": [{"recorded_at": "2026-10-20T16:00:00Z", "request": {"method": "GET", "path": "/v2/team/credit-usage"},
              "response": {"status": 200, "body": {"success": True, "data": {"remainingCredits": 940, "planCredits": 1000,
                                                                              "billingPeriodStart": "2026-10-01T00:00:00Z", "billingPeriodEnd": None}}}}]}
        h = FC.health(con, cfg(), key=FAKE_KEY, transport=FC.FixtureTransport(fx), remote=True, now=T)
        assert h["remote"]["remainingCredits"] == 940 and h["status"] == "configured_unverified"   # a fixture never proves live access
        con.execute("INSERT INTO social_api_spend(connector,run_id,endpoint,http_status,billing_day,resources_json,est_cost_usd,mode,requested_at)"
                    " VALUES ('firecrawl','l','/v2/scrape',200,'2026-10-20','{\"credits\": 3}',0,'live',?)", (T,))
        con.commit()
        h2 = FC.health(con, cfg(), key=FAKE_KEY, now=T)
        assert h2["status"] == "live_ok" and h2["credits_this_month_live"] == 3 and h2["key"] == "set"
        assert FAKE_KEY not in json.dumps(h2)


def test_content_guard_flags_page_text_in_tracked_files_and_tables(tmp_path):
    from memelab.social import content_guard as G
    assert G.check_json("inbox/x.json", {"cat:x": {"body": {"markdown": "copied article"}}})
    assert not G.check_json("tests/fixtures/catalyst/firecrawl/fx_enrich.json",
                            {"exchanges": [{"response": {"body": {"data": {"markdown": "invented"}}}}]})
    f = tmp_path / "m.sqlite"
    con = sqlite3.connect(f)
    con.executescript("CREATE TABLE catalyst_page_fetches (id INTEGER, markdown TEXT);"
                      "CREATE TABLE catalyst_page_facts (id INTEGER, fetch_id INTEGER, kind TEXT, value TEXT, chain_hint TEXT);"
                      "INSERT INTO catalyst_page_facts VALUES (1, 1, 'TICKER', 'not a ticker but a sentence', NULL);"
                      f"INSERT INTO catalyst_page_facts VALUES (2, 1, 'CONTRACT', '{MINT}', 'solana');")
    con.commit()
    con.close()
    rules = [(v.where, v.rule) for v in G.check_sqlite("data/memelab.sqlite", f)]
    assert ("catalyst_page_fetches.markdown", "SQLITE: page content column in a catalyst page table") in rules
    assert any(w == "catalyst_page_facts[1].value" for w, _ in rules) and not any(w == "catalyst_page_facts[2].value" for w, _ in rules)


def test_real_schema_passes_the_guard(tmpdb):
    from memelab.social import content_guard as G
    _enriched(tmpdb)
    assert [v for v in G.check_sqlite("data/memelab.sqlite", tmpdb.DB_PATH) if "catalyst_page" in v.where] == []


def test_audit_and_e2e_know_firecrawl():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ra", ROOT / "tools" / "release_audit.py")
    ra = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ra)
    assert ra.CRED["firecrawl_key"].search(b"Authorization: Bearer " + FAKE_KEY.encode())
    assert not ra.CRED["firecrawl_key"].search(b"fc-not-a-key-0123")
    assert ra.SOCIAL_LOGIN_HOSTS.search("https://api.firecrawl.dev/v2/scrape")
    spec = importlib.util.spec_from_file_location("re2e", ROOT / "tools" / "release_e2e.py")
    e2e = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(e2e)
    assert "FIRECRAWL_API_KEY" in e2e.SECRET_VARS
    fc_stages = [s for s in e2e.STAGES if s[0] == "FC"]
    for _, title, cmd, expect in fc_stages:
        for rel in __import__("re").findall(r"tests/fixtures/catalyst/firecrawl/[\w.]+", cmd.replace('" + FCX + "', "tests/fixtures/catalyst/firecrawl")):
            assert (ROOT / rel).exists(), rel
        if title.startswith("not configured"):
            assert expect == (1,), title
    assert len(fc_stages) == 7
