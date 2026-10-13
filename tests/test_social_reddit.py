"""Phase 19: Reddit Data API adapter. Recorded synthetic HTTP fixtures only; no network, fixed clock, temp DB and private folder.

Fixtures: tests/fixtures/social/reddit_api/ (invented community, users, ids and sentences shaped like the documented
responses; generated once and committed).
"""
import json
import logging
import sqlite3
from pathlib import Path

import pytest

from memelab import cli, db
from memelab.social import ingest as I
from memelab.social import reddit_api as R
from memelab.social import schema, store
from memelab.social.api_common import TextSink, extract_after_ingest

ROOT = Path(__file__).resolve().parent.parent
FXD = ROOT / "tests" / "fixtures" / "social" / "reddit_api"
CONFIG, MAIN, SECOND = FXD / "fx_reddit_config.json", FXD / "fx_reddit_main.json", FXD / "fx_reddit_second.json"
BODIES = ROOT / "tests" / "fixtures" / "social" / "resolve" / "fx_providers.json"
T1 = 1791676800.0              # 2026-10-11T00:00:00Z (main recorded 2026-10-10T23:00Z)
T2 = 1791763200.0              # 2026-10-12T00:00:00Z (second recorded 2026-10-11T23:00Z)
CID, SECRET = "fixture-client-id", "fixture-secret-DO-NOT-LEAK-0123456789"
SUBS = "reddit_api:sub:examplememes:submissions"
COMS = "reddit_api:sub:examplememes:comments"
CA = "8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ"
RL = {"x-ratelimit-used": "3", "x-ratelimit-remaining": "97", "x-ratelimit-reset": "420"}


@pytest.fixture()
def dbp(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private" / "p.sqlite"))
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    return p


def cfg(**over):
    c = json.loads(CONFIG.read_text())
    c.update(over)
    return R.load_config(c)


RUNS = iter(range(1, 10_000))


def run(dbp, fixture, config=None, now=T1, cid=CID, secret=SECRET, sink=None, mode="fixture"):
    tr = fixture if isinstance(fixture, R.FixtureTransport) else R.FixtureTransport(fixture)
    rid = f"r{now}_{next(RUNS)}"
    ad = R.RedditApiAdapter(config or cfg(), tr, cid, secret, dbp, run_id=rid, mode=mode, clock=lambda: now,
                            sleep=lambda s: None, text_sink=sink)
    out = I.ingest(ad, dbp, now=now, run_id=rid)
    return out, tr, ad


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
    return {"schema": R.FIXTURE_SCHEMA, "exchanges": list(exchanges)}


def ex(path, params, status, body, method="GET", headers=RL, at="2026-10-10T23:00:00Z"):
    return {"request": {"method": method, "path": path, "params": params}, "recorded_at": at,
            "response": {"status": status, "headers": headers, "body": body}}


def main_exchanges():
    return json.loads(MAIN.read_text())["exchanges"]


TOKEN_EX = lambda: main_exchanges()[0]
ABOUT_EX = lambda: main_exchanges()[1]
NEW = {"limit": 100, "raw_json": 1}
SUBS_ONLY = {"communities": [{"name": "examplememes", "submissions": True, "comments": False}], "recheck": {"enabled": False}}


def listing(children, after=None):
    return {"kind": "Listing", "data": {"after": after, "children": children}}


def post(i, created=1791597600, **kw):
    d = {"id": i, "name": "t3_" + i, "subreddit": "examplememes", "subreddit_type": "public", "author": "example_poster_a",
         "author_fullname": "t2_aaa01", "title": f"Invented title {i}", "selftext": "Invented text", "is_self": True,
         "created_utc": created, "edited": False, "score": 1, "num_comments": 0}
    d.update(kw)
    return {"kind": "t3", "data": d}


# ---------- the main fixture ----------

def test_main_fixture_submissions_comments_crosspost_deleted_edited(dbp):
    out, tr, ad = run(dbp, MAIN)
    assert out["status"] == "OK" and out["counts"]["created"] == 8 and out["counts"]["quarantined"] == 0
    assert [c["method"] for c in tr.calls] == ["POST", "GET", "GET", "GET", "GET"] and ad.requests == 5
    items = {r["item_key"]: r for r in q(dbp, "SELECT * FROM social_items")}
    assert sorted(items) == ["reddit:t1_cm001", "reddit:t1_cm002", "reddit:t3_ab000", "reddit:t3_ab001", "reddit:t3_ab002",
                             "reddit:t3_ab003", "reddit:t3_ab004", "reddit:t3_ab005"]      # cm003 (other community) dropped
    ctx = {r["item_key"]: r for r in q(dbp, "SELECT * FROM social_item_context")}
    assert ctx["reddit:t3_ab001"]["reference_type"] == "ORIGINAL" and ctx["reddit:t3_ab001"]["conversation_id"] == "t3_ab001"
    assert ctx["reddit:t1_cm001"]["reference_type"] == "REPLY" and ctx["reddit:t1_cm001"]["conversation_id"] == "t3_ab001"
    assert ctx["reddit:t3_ab002"]["reference_type"] == "REPOST"
    refs = {(r["item_key"], r["ref_type"]): r for r in q(dbp, "SELECT * FROM social_item_refs")}
    assert refs[("reddit:t3_ab002", "retweeted")]["referenced_item_key"] == "reddit:t3_zz900"
    assert refs[("reddit:t3_ab002", "retweeted")]["referenced_author_id"] == "t2_bbb02"
    assert refs[("reddit:t1_cm002", "replied_to")]["referenced_item_key"] == "reddit:t1_cm001"
    # the cross-posted original lives in a community that was not approved: no item, no content, ids only
    assert "reddit:t3_zz900" not in items
    obs = {r["item_key"]: r for r in q(dbp, "SELECT * FROM social_observations")}
    for gone in ("reddit:t3_ab003", "reddit:t1_cm002"):
        assert obs[gone]["retrieval_status"] == "DELETED" and obs[gone]["content_hash"] is None and obs[gone]["account_id"] is None
    # account deleted but content visible: the item is stored without an author
    assert obs["reddit:t3_ab005"]["account_id"] == "reddit:id:t2_eee06"
    assert items["reddit:t3_ab001"]["account_id"] == "reddit:id:t2_aaa01"
    vers = q(dbp, "SELECT * FROM social_item_versions WHERE item_key='reddit:t3_ab004'")
    assert [v["version_kind"] for v in vers] == ["EDIT"] and vers[0]["provider_version_at"] == 1791612000.0
    assert items["reddit:t3_ab001"]["published_at"] == 1791597600.0 and items["reddit:t3_ab001"]["published_at_basis"] == "PROVIDER"
    assert json.loads(obs["reddit:t3_ab001"]["metrics_json"]) == {"num_comments": 3, "num_crossposts": 0, "score": 12, "upvote_ratio": 0.9}
    cur = {r["connector"]: r for r in q(dbp, "SELECT * FROM social_source_cursors")}
    assert cur[SUBS]["newest_id"] == "t3_ab005" and cur[COMS]["newest_id"] == "t1_cm002"
    assert cur[SUBS]["provider_scope_id"] == "t5_exmem1"


def test_text_titles_flair_and_slugs_are_never_stored(dbp):
    run(dbp, MAIN)
    blob = all_text(dbp)
    for word in ("Invented post", "Invented fixture text", "Invented crosspost title", "Invented original", "Invented flair",
                 "invented_slug", "Invented community description", "Invented reply", "example_origin", "othersub", "Invented comment"):
        assert word not in blob, word
    urls = [r["original_url"] for r in q(dbp, "SELECT original_url FROM social_items")]
    assert all(u.startswith("https://www.reddit.com/comments/") and "invented" not in u for u in urls)
    # the hash is of the title and body, as the extractor will see it
    ab001 = json.loads(MAIN.read_text())["exchanges"][2]["response"]["body"]["data"]["children"][4]["data"]
    h = store.text_hash(ab001["title"] + "\n\n" + ab001["selftext"])
    assert q(dbp, "SELECT content_hash FROM social_observations WHERE item_key='reddit:t3_ab001'")[0]["content_hash"] == h


def test_provenance_rights_basis_and_fixture_labels(dbp):
    run(dbp, MAIN)
    prov = q(dbp, "SELECT * FROM social_observation_provenance")
    assert {p["rights_basis"] for p in prov} == {"synthetic_fixture"} and {p["inbound_schema"] for p in prov} == {I.INBOUND_SCHEMA_V3}
    assert all(p["connector"].startswith("reddit_api:sub:examplememes:") for p in prov)
    assert {r["access_mode"] for r in q(dbp, "SELECT access_mode FROM social_observations")} == {"fixture"}
    spend = q(dbp, "SELECT * FROM social_api_spend")
    assert len(spend) == 5 and {s["mode"] for s in spend} == {"fixture"} and sum(s["est_cost_usd"] for s in spend) == 0


def test_crosspost_is_amplification_not_an_independent_thread(dbp):
    run(dbp, MAIN)
    con = sqlite3.connect(dbp)
    assert store.is_independent_original(con, "reddit:t3_ab002") is False
    assert store.is_independent_original(con, "reddit:t3_ab001") is True
    assert store.is_independent_original(con, "reddit:t1_cm001") is True     # a reply is the poster's own words (D-029)
    con.close()


def test_rerun_adds_nothing(dbp):
    run(dbp, MAIN)
    n = q(dbp, "SELECT COUNT(*) n FROM social_observations")[0]["n"]
    out, _, _ = run(dbp, MAIN)
    assert out["counts"]["created"] == 0 and q(dbp, "SELECT COUNT(*) n FROM social_observations")[0]["n"] == n


# ---------- second run: cursor, recheck, deletion and account deletion, purge ----------

def test_second_run_cursor_recheck_and_purge(dbp):
    run(dbp, MAIN)
    out, tr, ad = run(dbp, SECOND, now=T2)
    assert out["status"] == "OK"
    assert ("reddit:t3_ab006",) in [(r["item_key"],) for r in q(dbp, "SELECT item_key FROM social_items")]
    info = [c for c in tr.calls if c["path"] == "/api/info"][0]
    assert "t3_ab006" not in info["params"]["id"]           # items first stored in this run are not re-asked
    assert ad.account_deletion_items == ["t1_cm001"]
    last = {r["item_key"]: r["retrieval_status"] for r in q(dbp, "SELECT item_key, retrieval_status FROM social_observations ORDER BY id")}
    assert last["reddit:t3_ab001"] == "DELETED" and last["reddit:t3_ab000"] == "NOT_FOUND" and last["reddit:t1_cm001"] == "OK"
    assert [v["version_kind"] for v in q(dbp, "SELECT version_kind FROM social_item_versions WHERE item_key='reddit:t3_ab004' "
                                             "ORDER BY provider_version_at")] == ["EDIT", "EDIT"]
    ab001_hash = q(dbp, "SELECT content_hash FROM social_observations WHERE item_key='reddit:t3_ab001' AND content_hash IS NOT NULL")[0]["content_hash"]
    res = R.purge_deleted(dbp, now=T2, deleted_account_items=ad.account_deletion_items)
    assert res["items_purged"] == 2 and res["accounts_erased"] == 1
    assert ab001_hash not in all_text(dbp)
    for key in ("reddit:t3_ab001", "reddit:t3_ab000"):
        rows = q(dbp, "SELECT content_hash, metrics_json, account_id FROM social_observations WHERE item_key=?", key)
        assert all(r["content_hash"] is None and r["metrics_json"] is None and r["account_id"] is None for r in rows)
        assert q(dbp, "SELECT account_id FROM social_items WHERE item_key=?", key)[0]["account_id"] is None
    # the deleted account (author of cm001) is gone everywhere
    assert q(dbp, "SELECT COUNT(*) n FROM social_accounts WHERE provider_user_id='t2_ddd05'")[0]["n"] == 0
    assert "example_poster_d" not in all_text(dbp) and "t2_ddd05" not in all_text(dbp)
    # other accounts and items are untouched; ids of gone items stay with their gone sighting
    assert q(dbp, "SELECT account_id FROM social_items WHERE item_key='reddit:t3_ab004'")[0]["account_id"] == "reddit:id:t2_ccc04"
    assert R.purge_deleted(dbp, now=T2, deleted_account_items=ad.account_deletion_items) == {
        "items_purged": 0, "observations_cleared": 0, "claims_cleared": 0, "private_rows_deleted": 0, "accounts_erased": 0}


def test_purge_removes_claim_evidence_and_private_copies_of_deleted_items(dbp, tmp_path):
    from memelab.social import private
    sink = TextSink()
    run(dbp, MAIN, sink=sink)
    bodies = json.loads(BODIES.read_text())["bodies"]
    ab001 = q(dbp, "SELECT content_hash FROM social_observations WHERE item_key='reddit:t3_ab001'")[0]["content_hash"]
    private.put(ab001, "exact words kept for evidence (fixture)", "fixture evidence", platform="reddit")
    res = extract_after_ingest(dbp, sink, now=T1, bodies=bodies)
    assert res["extracted"] == 6 and len(sink) == 0
    cid = q(dbp, "SELECT id FROM social_claims WHERE item_key='reddit:t3_ab001'")[0]["id"]
    assert q(dbp, "SELECT COUNT(*) n FROM social_claim_spans WHERE claim_id=?", cid)[0]["n"] >= 1
    _, _, ad = run(dbp, SECOND, now=T2)
    out = R.purge_deleted(dbp, now=T2, deleted_account_items=ad.account_deletion_items)
    assert out["private_rows_deleted"] == 1 and out["claims_cleared"] >= 1
    assert q(dbp, "SELECT COUNT(*) n FROM social_claim_spans WHERE claim_id=?", cid)[0]["n"] == 0
    ext = q(dbp, "SELECT content_hash, output_json FROM social_claim_extractions WHERE item_key='reddit:t3_ab001'")
    assert ext and all(e["content_hash"] == "0" * 64 and e["output_json"] is None for e in ext)
    assert ab001 not in all_text(dbp) and private.get_text(ab001) is None


def test_health_reports_pending_purge(dbp, tmp_path):
    run(dbp, MAIN)
    run(dbp, SECOND, now=T2)
    assert R.health(CONFIG, dbp, env={})["deletion_purge_pending_items"] == 2
    R.purge_deleted(dbp, now=T2)
    assert R.health(CONFIG, dbp, env={})["deletion_purge_pending_items"] == 0


# ---------- access gates: approval, credentials, commercial use ----------

def test_no_approval_means_no_request(dbp):
    out, tr, _ = run(dbp, MAIN, config=cfg(access_approval={"approved": False}))
    assert tr.calls == [] and out["status"] == "FAILED"
    assert all("approval_missing" in h["errors"][0] for h in out["health"].values())


def test_credentials_missing_no_request(dbp):
    out, tr, _ = run(dbp, MAIN, secret=None)
    assert tr.calls == [] and all("credentials_missing" in h["errors"][0] for h in out["health"].values())


def test_config_refuses_commercial_use_secrets_and_bad_names():
    base = json.loads(CONFIG.read_text())
    with pytest.raises(ValueError, match="commercial_use"):
        R.load_config({**base, "commercial_use": True})
    with pytest.raises(ValueError, match="commercial_use"):
        R.load_config({k: v for k, v in base.items() if k != "commercial_use"})
    for bad in ({"client_secret": "x"}, {"user_agent": {**base["user_agent"], "password": "x"}}):
        with pytest.raises(ValueError, match="must not hold credentials"):
            R.load_config({**base, **bad})
    with pytest.raises(ValueError, match="community name"):
        R.load_config({**base, "communities": [{"name": "r/not ok"}]})
    with pytest.raises(ValueError, match="duplicate"):
        R.load_config({**base, "communities": [{"name": "abc"}, {"name": "ABC"}]})
    assert R.load_config(base).user_agent == "python:memelab-research:0.19 (by /u/example_operator)"


def test_private_or_quarantined_community_is_not_read(dbp):
    for about in ({"subreddit_type": "private"}, {"subreddit_type": "public", "quarantine": True}):
        f = fixture(TOKEN_EX(), ex("/r/examplememes/about", {"raw_json": 1}, 200, {"kind": "t5", "data": about}))
        out, tr, _ = run(dbp, f, config=cfg(**SUBS_ONLY))
        assert [c["path"] for c in tr.calls] == ["/api/v1/access_token", "/r/examplememes/about"]
        assert out["health"][SUBS]["status"] == "BLOCKED" and q(dbp, "SELECT COUNT(*) n FROM social_items")[0]["n"] == 0


def test_item_from_a_private_community_is_quarantined(dbp):
    f = fixture(TOKEN_EX(), ABOUT_EX(), ex("/r/examplememes/new", NEW, 200,
                                           listing([post("ab100", subreddit_type="private")])))
    # the community said public; an item that says otherwise is refused by the ingester (NOT_PUBLIC)
    out, _, _ = run(dbp, f, config=cfg(**SUBS_ONLY))
    assert out["counts"]["quarantined"] == 1 and q(dbp, "SELECT COUNT(*) n FROM social_items")[0]["n"] == 0


# ---------- rate limits and errors ----------

def test_token_rejected_stops_everything(dbp):
    f = fixture(ex("/api/v1/access_token", {"grant_type": "client_credentials"}, 401, {"message": "Unauthorized", "error": 401},
                   method="POST", headers={}))
    out, tr, _ = run(dbp, f)
    assert len(tr.calls) == 1 and out["health"]["reddit_api:auth"]["status"] == "BLOCKED"
    assert "401" in out["health"]["reddit_api:auth"]["errors"][0]


def test_429_records_reset_and_the_next_run_waits(dbp):
    f = fixture(TOKEN_EX(), ABOUT_EX(), ex("/r/examplememes/new", NEW, 429, {"message": "Too Many Requests"},
                                           headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "300"}))
    out, _, _ = run(dbp, f, config=cfg(**SUBS_ONLY))
    assert out["health"][SUBS]["status"] == "RATE_LIMITED"
    reset = q(dbp, "SELECT rate_limit_reset_at FROM social_source_cursors WHERE connector=?", SUBS)[0]["rate_limit_reset_at"]
    assert reset == R.store.to_utc("2026-10-10T23:00:00Z") + 300
    out, tr, _ = run(dbp, fixture(TOKEN_EX()), config=cfg(**SUBS_ONLY), now=reset - 10)
    assert [c["path"] for c in tr.calls] == ["/api/v1/access_token"] and out["health"][SUBS]["status"] == "RATE_LIMITED"


def test_low_remaining_stops_before_the_next_page(dbp):
    f = fixture(TOKEN_EX(), ABOUT_EX(), ex("/r/examplememes/new", NEW, 200, listing([post("ab101")], "t3_ab101"),
                                           headers={"x-ratelimit-remaining": "2", "x-ratelimit-reset": "100"}))
    out, tr, _ = run(dbp, f, config=cfg(**SUBS_ONLY))
    assert len(tr.calls) == 3 and out["health"][SUBS]["status"] == "RATE_LIMITED" and out["counts"]["created"] == 1


def test_page_cap_records_gap(dbp):
    f = fixture(TOKEN_EX(), ABOUT_EX(), ex("/r/examplememes/new", NEW, 200, listing([post("ab102")], "t3_ab102")))
    out, _, _ = run(dbp, f, config=cfg(max_pages_per_listing=1, **SUBS_ONLY))
    assert out["health"][SUBS]["status"] == "DEGRADED"
    assert any("page cap" in c["gap_reason"] for c in q(dbp, "SELECT gap_reason FROM social_coverage WHERE gap_reason IS NOT NULL"))


def test_request_cap_per_run(dbp):
    out, tr, _ = run(dbp, MAIN, config=cfg(max_requests_per_run=3))
    assert len(tr.calls) == 3
    assert any("request cap" in (h["errors"] or [""])[0] for h in out["health"].values())


def test_5xx_bounded_retries_then_down(dbp):
    f = fixture(TOKEN_EX(), *[ex("/r/examplememes/about", {"raw_json": 1}, 503, None)] * 3)
    out, tr, _ = run(dbp, f, config=cfg(**SUBS_ONLY))
    assert len(tr.calls) == 4 and out["health"][SUBS]["status"] == "DOWN"


def test_secrets_never_leak(dbp, caplog, capsys):
    f = fixture(TOKEN_EX(), *[{"recorded_at": "2026-10-10T23:00:00Z", "request": {"method": "GET", "path": "/r/examplememes/about",
                                                                                  "params": {"raw_json": 1}},
                               "raise": "reset while sending Authorization: bearer {secret}"}] * 3)
    with caplog.at_level(logging.INFO, logger="memelab.social.ingest"):
        out, tr, ad = run(dbp, f, config=cfg(**SUBS_ONLY))
    access = "fixture-access-token-0123456789abcdef"
    blob = json.dumps(out) + caplog.text + all_text(dbp) + repr(ad) + json.dumps(tr.calls) + capsys.readouterr().err
    assert SECRET not in blob and access not in blob and "0123456789abcdef" not in blob
    assert "[REDACTED]" in out["health"][SUBS]["errors"][0]


# ---------- health, CLI, example config ----------

def test_health_states_without_network(dbp, tmp_path, monkeypatch):
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network used")))
    env = {R.ID_ENV: CID, R.SECRET_ENV: SECRET}
    assert R.health(tmp_path / "none.json", dbp, env=env)["status"] == "not_configured"
    off = tmp_path / "off.json"
    off.write_text(json.dumps({**json.loads(CONFIG.read_text()), "access_approval": {"approved": False}}))
    assert R.health(off, dbp, env=env)["status"] == "approval_missing"
    assert R.health(CONFIG, dbp, env={})["status"] == "credentials_missing"
    h = R.health(CONFIG, dbp, env=env)
    assert h["status"] == "ready" and SECRET not in json.dumps(h) and h["network_calls_made"] == 0
    assert h["live_evidence"]["verdict"].startswith("none")


def test_cli_fixture_flow_extract_narrative_brief_and_live_refusal(dbp, capsys, monkeypatch):
    """Source -> storage -> claim -> narrative -> report, on the fixture, through the real commands."""
    monkeypatch.delenv(R.ID_ENV, raising=False)
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "reddit-ingest", "--config", str(CONFIG), "--fixture", str(MAIN), "--extract", "--bodies", str(BODIES),
                  "--db", str(dbp), "--now", str(T1), "--run-id", "cli_rd"])
    out = json.loads(capsys.readouterr().out)
    assert e.value.code == 0 and out["mode"] == "fixture" and out["counts"]["created"] == 8
    assert out["extraction"]["extracted"] == 6 and out["extraction"]["claims"] == 3 and out["deletion_purge"]["items_purged"] == 0
    claims = q(dbp, "SELECT c.item_key, a.category, a.tokens_json FROM social_claims c JOIN social_claim_attributes a ON a.claim_id=c.id")
    assert sorted(c["item_key"] for c in claims) == ["reddit:t1_cm001", "reddit:t3_ab001", "reddit:t3_ab004"]
    assert all(json.loads(c["tokens_json"])[0]["contract"] == CA and c["category"] == "token_reference" for c in claims)
    call(["social", "narrative-snapshot", "--day", "2026-10-10", "--tz", "UTC", "--db", str(dbp), "--now", str(T1 + 3600)])
    snap = json.loads(capsys.readouterr().out)
    assert snap["summary"]["new"] == [f"ca:solana:{CA}"]
    cl = q(dbp, "SELECT * FROM social_narrative_clusters")[0]
    assert cl["independent_source_count"] == 2      # ab001 and ab004; cm001 replies to ab001 (dependent)
    call(["social", "brief", "--db", str(dbp), "--as-of", "2026-10-11T01:00:00+00:00", "--tz", "UTC", "--include-fixtures"])
    brief = capsys.readouterr().out
    assert "FIXTURE DEMO" in brief and "Coverage: reddit COVERED" in brief and "https://www.reddit.com/comments/ab001/" in brief
    assert "Invented fixture text" not in brief
    # live ingest refuses before any network call
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network used")))
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "reddit-ingest", "--config", str(CONFIG), "--db", str(dbp)])
    r = json.loads(capsys.readouterr().out)
    assert e.value.code == 1 and r["status"] == "NOT_RUN" and r["reason"] == "credentials_missing" and r["network_calls_made"] == 0


def test_example_config_loads_and_is_off_by_default(dbp):
    ex_cfg = ROOT / "docs" / "social-intelligence" / "reddit_api.example.json"
    c = R.load_config(ex_cfg)
    assert c.approved is False and c.commercial_use is False and c.max_pages_per_listing == 1
    assert R.health(ex_cfg, dbp, env={R.ID_ENV: CID, R.SECRET_ENV: SECRET})["status"] == "approval_missing"
