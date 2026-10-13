"""Phase 19: Farcaster adapter on the Snapchain node HTTP API. Recorded synthetic fixtures only; no network, fixed clock,
temp DB and private folder.

Fixtures: tests/fixtures/social/farcaster_hub/ (invented fids, usernames, hashes and sentences shaped like the documented
responses; generated once and committed).
"""
import json
import logging
import sqlite3
from pathlib import Path

import pytest

from memelab import cli, db
from memelab.social import farcaster_hub as F
from memelab.social import ingest as I
from memelab.social import schema, store
from memelab.social.api_common import TextSink, extract_after_ingest

ROOT = Path(__file__).resolve().parent.parent
FXD = ROOT / "tests" / "fixtures" / "social" / "farcaster_hub"
CONFIG, MAIN, SECOND = FXD / "fx_fc_config.json", FXD / "fx_fc_main.json", FXD / "fx_fc_second.json"
BODIES = ROOT / "tests" / "fixtures" / "social" / "resolve" / "fx_providers.json"
T1, T2 = 1791676800.0, 1791763200.0
H = lambda c: "0x" + (c * 40)[:40]
A1, A2, B1, C1, R1, R2 = H("a1"), H("a2"), H("b1"), H("c1"), H("d1"), H("d2")
FIDS, CHAN = "farcaster_hub:fid:9001", "farcaster_hub:channel:examplememes"
CA = "8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ"
KEY = "fc-hub-key-DO-NOT-LEAK-0123456789abcdef"
RUNS = iter(range(1, 10_000))


@pytest.fixture()
def dbp(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private" / "p.sqlite"))
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    return p


def cfg(**over):
    c = json.loads(CONFIG.read_text())
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(c.get(k), dict):
            c[k] = {**c[k], **v}
        else:
            c[k] = v
    return F.load_config(c)


def run(dbp, fixture, config=None, now=T1, key=None, sink=None, mode="fixture"):
    tr = fixture if isinstance(fixture, F.FixtureTransport) else F.FixtureTransport(fixture)
    rid = f"f{now}_{next(RUNS)}"
    ad = F.FarcasterHubAdapter(config or cfg(), tr, key, dbp, run_id=rid, mode=mode, clock=lambda: now, sleep=lambda s: None,
                               text_sink=sink)
    return I.ingest(ad, dbp, now=now, run_id=rid), tr, ad


def q(dbp, sql, *args):
    con = sqlite3.connect(dbp)
    con.row_factory = sqlite3.Row
    out = [dict(r) for r in con.execute(sql, args)]
    con.close()
    return out


def all_text(dbp):
    con = sqlite3.connect(dbp)
    out = []
    for t in schema.SOCIAL_TABLES:
        for r in con.execute(f"SELECT * FROM {t}"):
            out += [str(v) for v in r if v is not None]
    con.close()
    return "\n".join(out)


def call(argv):
    try:
        cli.main(argv)
    except SystemExit as e:
        return e.code
    return 0


def fixture(*exchanges):
    return {"schema": F.FIXTURE_SCHEMA, "exchanges": list(exchanges)}


def ex(path, params, status, body, headers=None, at="2026-10-10T23:00:00Z"):
    return {"request": {"method": "GET", "path": path, "params": params}, "recorded_at": at,
            "response": {"status": status, "headers": headers or {}, "body": body}}


FID_ONLY = {"scopes": [{"kind": "fid", "fid": 9001}], "recasts": {"enabled": False}, "recheck": {"enabled": False}}
FIDP = {"fid": 9001, "pageSize": 100, "reverse": 1}
UNAME = ex("/v1/userDataByFid", {"fid": 9001, "user_data_type": 6}, 200, {"messages": [], "nextPageToken": ""})


def main_cast(h):
    for e in json.loads(MAIN.read_text())["exchanges"]:
        for m in (e["response"]["body"] or {}).get("messages") or []:
            if m.get("hash") == h:
                return m


# ---------- main fixture ----------

def test_main_fixture_casts_replies_quotes_recasts(dbp):
    out, tr, ad = run(dbp, MAIN)
    assert out["status"] == "OK" and out["counts"]["created"] == 6 and ad.requests == 11
    items = {r["item_key"]: r for r in q(dbp, "SELECT * FROM social_items")}
    assert sorted(items) == [f"farcaster:{h}" for h in (A1, A2, B1, C1, R1, R2)]       # the LINK_ADD message is ignored
    ctx = {r["item_key"]: r["reference_type"] for r in q(dbp, "SELECT * FROM social_item_context")}
    assert ctx == {f"farcaster:{A1}": "ORIGINAL", f"farcaster:{A2}": "REPLY", f"farcaster:{B1}": "ORIGINAL",
                   f"farcaster:{C1}": "QUOTE", f"farcaster:{R1}": "REPOST", f"farcaster:{R2}": "REPOST"}
    refs = {(r["item_key"], r["ref_type"]): (r["referenced_item_key"], r["referenced_author_id"]) for r in q(dbp, "SELECT * FROM social_item_refs")}
    assert refs[(f"farcaster:{A2}", "replied_to")] == (f"farcaster:{B1}", "9002")
    assert refs[(f"farcaster:{C1}", "quoted")] == (f"farcaster:{A1}", "9001")
    assert refs[(f"farcaster:{R1}", "retweeted")] == (f"farcaster:{A1}", "9001")
    # Farcaster epoch: 2021-01-01T00:00:00Z + data.timestamp
    assert items[f"farcaster:{A1}"]["published_at"] == store.to_utc("2026-10-10T02:10:00Z")
    assert items[f"farcaster:{A1}"]["original_url"] == "https://farcaster.xyz/example-caster-a/0xa1a1a1a1"
    assert items[f"farcaster:{C1}"]["original_url"] is None            # no username known: id only
    accts = {r["account_id"]: r["handle"] for r in q(dbp, "SELECT * FROM social_accounts")}
    assert accts == {"farcaster:id:9001": "example-caster-a", "farcaster:id:9002": "example-caster-b", "farcaster:id:9003": None,
                     "farcaster:id:9004": "example-recaster", "farcaster:id:9005": None}
    cur = {r["connector"]: r["newest_id"] for r in q(dbp, "SELECT * FROM social_source_cursors")}
    assert cur[FIDS] == str(int(store.to_utc("2026-10-10T04:00:00Z"))) and cur[CHAN] == str(int(store.to_utc("2026-10-10T05:00:00Z")))


def test_only_the_username_is_requested_and_no_text_is_stored(dbp):
    _, tr, _ = run(dbp, MAIN)
    assert all(c["params"].get("user_data_type") == "6" for c in tr.calls if c["path"] == "/v1/userDataByFid")
    blob = all_text(dbp)
    for w in ("Invented cast", "Invented reply cast", "Invented channel cast", "Invented quote", "pump.fun", "example.invalid"):
        assert w not in blob, w
    a1 = main_cast(A1)["data"]["castAddBody"]
    want = store.text_hash(a1["text"] + "\n" + a1["embeds"][0]["url"])       # words plus embedded URL
    assert q(dbp, "SELECT content_hash FROM social_observations WHERE item_key=?", f"farcaster:{A1}")[0]["content_hash"] == want


def test_recasts_are_amplification_quotes_and_replies_are_own_words(dbp):
    run(dbp, MAIN)
    con = sqlite3.connect(dbp)
    assert store.is_independent_original(con, f"farcaster:{R1}") is False
    assert store.is_independent_original(con, f"farcaster:{C1}") is True and store.is_independent_original(con, f"farcaster:{A2}") is True
    con.close()
    assert q(dbp, "SELECT content_hash FROM social_observations WHERE item_key=?", f"farcaster:{R1}")[0]["content_hash"] is None


def test_second_run_cursor_recheck_not_found_and_no_duplicate_claims(dbp):
    bodies = json.loads(BODIES.read_text())["bodies"]
    s1 = TextSink()
    run(dbp, MAIN, sink=s1)
    r1 = extract_after_ingest(dbp, s1, now=T1, bodies=bodies)
    assert r1["extracted"] == 4 and r1["claims"] == 2
    s2 = TextSink()
    out, tr, _ = run(dbp, SECOND, now=T2, sink=s2)
    assert out["status"] == "OK"
    rechecked = sorted(c["params"]["hash"] for c in tr.calls if c["path"] == "/v1/castById")
    assert rechecked == [A1, A2, B1]          # C1 was listed again in this run (fresh), recasts are not rechecked
    last = {r["item_key"]: r["retrieval_status"] for r in q(dbp, "SELECT item_key, retrieval_status FROM social_observations ORDER BY id")}
    assert last[f"farcaster:{A2}"] == "NOT_FOUND" and last[f"farcaster:{A1}"] == "OK"
    r2 = extract_after_ingest(dbp, s2, now=T2, bodies=bodies)
    assert r2["skipped_already_extracted"] == 2 and q(dbp, "SELECT COUNT(*) n FROM social_claims")[0]["n"] == 2


# ---------- gates ----------

def test_metered_hub_needs_key_and_consent_before_any_request(dbp):
    out, tr, _ = run(dbp, MAIN, config=cfg(hub={"base_url": "https://hub.example.invalid", "billing": "metered"}), mode="live")
    assert tr.calls == [] and all("credentials_missing" in h["errors"][0] for h in out["health"].values())
    out, tr, _ = run(dbp, MAIN, config=cfg(hub={"base_url": "https://hub.example.invalid", "billing": "metered"}), key=KEY, mode="live")
    assert tr.calls == [] and all("billing_not_consented" in h["errors"][0] for h in out["health"].values())


def test_metered_cost_is_recorded_and_capped(dbp):
    c = cfg(hub={"base_url": "https://hub.example.invalid", "billing": "metered", "usd_per_request": 0.01},
            budget={"allow_billable": True, "max_usd_per_run": 0.025}, **FID_ONLY)
    f = fixture(ex("/v1/castsByFid", FIDP, 200, {"messages": [main_cast(A1)], "nextPageToken": "p2"}), UNAME,
                ex("/v1/castsByFid", {**FIDP, "pageToken": "p2"}, 200, {"messages": [], "nextPageToken": ""}))
    out, tr, _ = run(dbp, f, config=c, key=KEY)
    assert len(tr.calls) == 2 and "cost cap" in out["health"][FIDS]["errors"][0]
    spend = q(dbp, "SELECT est_cost_usd, mode FROM social_api_spend")
    assert [s["est_cost_usd"] for s in spend] == [0.01, 0.01] and {s["mode"] for s in spend} == {"fixture"}


def test_config_refuses_keys_and_unsafe_urls():
    base = json.loads(CONFIG.read_text())
    for bad in ({"hub": {**base["hub"], "api_key": "x"}}, {"signer": "x"}):
        with pytest.raises(ValueError, match="must not hold credentials"):
            F.load_config({**base, **bad})
    for url in ("http://hub.example.invalid:3381", "ftp://127.0.0.1", "https://user:pw@hub.example.invalid", "https://hub.example.invalid/?k=1"):
        with pytest.raises(ValueError, match="base_url"):
            F.load_config({**base, "hub": {**base["hub"], "base_url": url}})
    with pytest.raises(ValueError, match="fid"):
        F.load_config({**base, "scopes": [{"kind": "fid", "fid": "9001"}]})
    with pytest.raises(ValueError, match="parent_url"):
        F.load_config({**base, "scopes": [{"kind": "channel", "name": "x", "parent_url": "http://insecure"}]})


# ---------- errors ----------

def test_429_stops_the_run_and_records_retry_after(dbp):
    f = fixture(ex("/v1/castsByFid", FIDP, 429, {"errCode": "rate_limited"}, headers={"retry-after": "120"}))
    out, tr, _ = run(dbp, f, config=cfg(scopes=[{"kind": "fid", "fid": 9001}, {"kind": "channel", "name": "examplememes",
                                                                               "parent_url": "https://example.invalid/channels/examplememes"}]))
    assert len(tr.calls) == 1 and out["health"][FIDS]["status"] == "RATE_LIMITED" and out["health"][CHAN]["status"] == "DEGRADED"
    reset = q(dbp, "SELECT rate_limit_reset_at FROM social_source_cursors WHERE connector=?", FIDS)[0]["rate_limit_reset_at"]
    assert reset == store.to_utc("2026-10-10T23:00:00Z") + 120
    out, tr, _ = run(dbp, fixture(), config=cfg(**FID_ONLY), now=reset - 1)
    assert tr.calls == [] and out["health"][FIDS]["status"] == "RATE_LIMITED"


def test_401_blocks_and_stops(dbp):
    f = fixture(ex("/v1/castsByFid", FIDP, 401, {"errCode": "unauthorized"}))
    out, tr, _ = run(dbp, f, config=cfg(**FID_ONLY))
    assert out["health"][FIDS]["status"] == "BLOCKED" and len(tr.calls) == 1


def test_page_cap_and_request_cap(dbp):
    f = fixture(ex("/v1/castsByFid", FIDP, 200, {"messages": [main_cast(A1)], "nextPageToken": "p2"}), UNAME)
    out, _, _ = run(dbp, f, config=cfg(max_pages_per_scope=1, **FID_ONLY))
    assert out["health"][FIDS]["status"] == "DEGRADED"
    out, tr, _ = run(dbp, MAIN, config=cfg(max_requests_per_run=2))
    assert len(tr.calls) == 2 and any("request cap" in (h["errors"] or [""])[0] for h in out["health"].values())


def test_key_never_leaks(dbp, caplog, capsys):
    c = cfg(hub={"base_url": "https://hub.example.invalid", "billing": "metered", "usd_per_request": 0.0},
            budget={"allow_billable": True, "max_usd_per_run": 1.0}, **FID_ONLY)
    f = fixture(*[{"recorded_at": "2026-10-10T23:00:00Z", "request": {"method": "GET", "path": "/v1/castsByFid", "params": FIDP},
                   "raise": "reset while sending x-api-key: {secret}"}] * 3)
    with caplog.at_level(logging.INFO, logger="memelab.social.ingest"):
        out, tr, ad = run(dbp, f, config=c, key=KEY)
    blob = json.dumps(out) + caplog.text + all_text(dbp) + repr(ad) + json.dumps(tr.calls) + capsys.readouterr().err
    assert KEY not in blob and "0123456789abcdef" not in blob and out["health"][FIDS]["status"] == "DOWN"


# ---------- health, CLI, example config ----------

def test_health_states_without_network(dbp, tmp_path, monkeypatch):
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network used")))
    ex_cfg = ROOT / "docs" / "social-intelligence" / "farcaster_hub.example.json"
    assert F.health(ex_cfg, dbp, env={})["status"] == "not_configured"
    assert F.health(tmp_path / "none.json", dbp, env={})["status"] == "not_configured"
    met = tmp_path / "met.json"
    base = json.loads(CONFIG.read_text())
    met.write_text(json.dumps({**base, "hub": {"base_url": "https://hub.example.invalid", "billing": "metered"}}))
    assert F.health(met, dbp, env={})["status"] == "credentials_missing"
    assert F.health(met, dbp, env={F.DEFAULT_KEY_ENV: KEY})["status"] == "billing_not_consented"
    h = F.health(CONFIG, dbp, env={})
    assert h["status"] == "ready" and h["credentials"] == "not_needed" and h["network_calls_made"] == 0
    assert h["live_evidence"]["verdict"].startswith("none")


def test_cli_fixture_flow_extract_narrative_brief_and_live_refusal(dbp, capsys, monkeypatch):
    """Source -> storage -> claim -> narrative -> report, on the fixture, through the real commands."""
    assert call(["social", "fc-ingest", "--config", str(CONFIG), "--fixture", str(MAIN), "--extract", "--bodies", str(BODIES),
                 "--db", str(dbp), "--now", str(T1), "--run-id", "cli_fc"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["mode"] == "fixture" and out["counts"]["created"] == 6 and out["extraction"]["claims"] == 2
    call(["social", "narrative-snapshot", "--day", "2026-10-10", "--tz", "UTC", "--db", str(dbp), "--now", str(T1 + 3600)])
    capsys.readouterr()
    cl = q(dbp, "SELECT * FROM social_narrative_clusters")[0]
    assert cl["cluster_key"] == f"ca:solana:{CA}" and cl["independent_source_count"] == 2
    call(["social", "brief", "--db", str(dbp), "--as-of", "2026-10-11T01:00:00+00:00", "--tz", "UTC", "--include-fixtures"])
    brief = capsys.readouterr().out
    assert "Coverage: farcaster COVERED" in brief and "https://farcaster.xyz/example-caster-b/0xb1b1b1b1" in brief
    assert "Invented" not in brief.replace("invented accounts", "")
    # the sources table and a live refusal, both without network
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network used")))
    call(["social", "sources", "--db", str(dbp)])
    rows = {r["connector"]: r for r in json.loads(capsys.readouterr().out)["connectors"]}
    assert set(rows) == {"x_api", "telegram_bot", "reddit_api", "farcaster_hub"} and rows["farcaster_hub"]["live_requests"] == 0
    assert call(["social", "fc-ingest", "--config", str(ROOT / "docs" / "social-intelligence" / "farcaster_hub.example.json"),
                 "--db", str(dbp)]) == 1
    r = json.loads(capsys.readouterr().out)
    assert r["status"] == "NOT_RUN" and r["reason"] == "not_configured" and r["network_calls_made"] == 0


def test_example_config_loads_and_is_off_by_default():
    c = F.load_config(ROOT / "docs" / "social-intelligence" / "farcaster_hub.example.json")
    assert c.base_url is None and c.allow_billable is False and c.billing == "self_hosted"
