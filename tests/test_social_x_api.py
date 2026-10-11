"""Phase 03: X API v2 adapter. Recorded synthetic HTTP fixtures only; no network, fixed clock, temp DB and private folder.

Fixtures: tests/fixtures/social/x_api/ (invented accounts, ids and sentences shaped like the documented responses).
"""
import json
import logging
import sqlite3
from pathlib import Path

import pytest

from memelab import cli, db
from memelab.social import ingest as I
from memelab.social import schema, store
from memelab.social import x_api as X

ROOT = Path(__file__).resolve().parent.parent
FXD = ROOT / "tests" / "fixtures" / "social" / "x_api"
CONFIG = FXD / "fx_x_config.json"
MAIN = FXD / "fx_x_main.json"
SECOND = FXD / "fx_x_second.json"
REC = 1791558000.0              # 2026-10-09T15:00:00Z, recorded_at in fx_x_main.json
T_RUN = 1791561600.0            # 2026-10-09T16:00:00Z
T_SECOND = 1791568800.0         # 2026-10-09T18:00:00Z (fx_x_second recorded 17:00)
USER = "x_api:user:example_alpha"
LIST = "x_api:list:1500000000000000001"
SEARCH = "x_api:search:example_token"
TOKEN = "xbt-THIS-IS-A-FAKE-TOKEN-0123456789abcdef"
P = lambda n: f"1840000000000000{n:03d}"
TF = X.TWEET_FIELDS
BASE = {"tweet.fields": TF, "user.fields": X.USER_FIELDS, "max_results": "10", "expansions": X.EXPANSIONS}


@pytest.fixture()
def dbp(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private" / "p.sqlite"))
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    return p


def cfg(**over):
    c = json.loads(CONFIG.read_text())
    for k, v in over.items():
        if k == "budget":
            c["budget"].update(v)
        else:
            c[k] = v
    return X.load_config(c)


def run(dbp, fixture, config=None, now=T_RUN, token=TOKEN, mode="fixture", run_id=None, **kw):
    tr = fixture if isinstance(fixture, X.FixtureTransport) else X.FixtureTransport(fixture)
    ad = X.XApiAdapter(config or cfg(), tr, token, dbp, run_id=run_id or f"r{now}", mode=mode, clock=lambda: now,
                       sleep=lambda s: None)
    out = I.ingest(ad, dbp, now=now, run_id=run_id or f"r{now}", **kw)
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


def fixture(*exchanges):
    return {"schema": X.FIXTURE_SCHEMA, "exchanges": list(exchanges)}


def ex(path, params, status=200, body=None, headers=None, at="2026-10-09T15:00:00Z"):
    return {"recorded_at": at, "request": {"path": path, "params": params},
            "response": {"status": status, "headers": headers or {}, "body": body}}


def post(n, author="2000000000000000001", created="2026-10-09T14:00:00.000Z", text="Invented sentence.", **kw):
    return {"id": P(n), "author_id": author, "created_at": created, "text": text, "edit_history_tweet_ids": [P(n)], **kw}


ALPHA_USER = ex("/2/users/by/username/example_alpha", {"user.fields": X.USER_FIELDS},
                body={"data": {"id": "2000000000000000001", "username": "example_alpha", "protected": False}})
ONLY_USER = {"scopes": [{"kind": "user", "username": "example_alpha"}]}


# ---------- the main recorded flow ----------

def test_main_fixture_originals_replies_reposts_quotes_edits(dbp):
    out, tr, _ = run(dbp, MAIN)
    assert out["status"] == "PARTIAL"
    assert out["counts"]["created"] == 7 and out["counts"]["duplicates"] == 1 and out["counts"]["quarantined"] == 0
    ctx = {r["item_key"]: r for r in q(dbp, "SELECT * FROM social_item_context")}
    assert ctx[f"x:{P(101)}"]["reference_type"] == "ORIGINAL"
    assert ctx[f"x:{P(102)}"]["reference_type"] == "REPLY" and ctx[f"x:{P(102)}"]["conversation_id"] == P(90)
    assert ctx[f"x:{P(102)}"]["in_reply_to_user_id"] == "2000000000000000009"
    assert ctx[f"x:{P(103)}"]["reference_type"] == "REPOST"
    assert ctx[f"x:{P(104)}"]["reference_type"] == "QUOTE"
    assert json.loads(ctx[f"x:{P(105)}"]["edit_history_json"]) == [P(100), P(105)]
    refs = {(r["item_key"], r["ref_type"]): r for r in q(dbp, "SELECT * FROM social_item_refs")}
    # the original author of a repost and a quote is kept (expansion referenced_tweets.id.author_id)
    assert refs[(f"x:{P(103)}", "retweeted")]["referenced_item_key"] == f"x:{P(80)}"
    assert refs[(f"x:{P(103)}", "retweeted")]["referenced_author_id"] == "2000000000000000007"
    assert refs[(f"x:{P(104)}", "quoted")]["referenced_author_id"] == "2000000000000000007"
    assert refs[(f"x:{P(102)}", "replied_to")]["referenced_author_id"] == "2000000000000000009"
    # every item row has a stable id, author, link and provider time
    items = {r["item_key"]: r for r in q(dbp, "SELECT * FROM social_items")}
    it = items[f"x:{P(101)}"]
    assert it["provider_item_id"] == P(101) and it["account_id"] == "x:id:2000000000000000001"
    assert it["original_url"] == f"https://x.com/example_alpha/status/{P(101)}"
    assert it["published_at"] == store.to_utc("2026-10-09T14:10:00Z") and it["published_at_basis"] == "PROVIDER"
    # the pages went through the expected requests, in order, with the pagination token on page 2
    paths = [(c["path"], c["params"].get("pagination_token")) for c in tr.calls]
    assert paths[:3] == [("/2/users/by/username/example_alpha", None), ("/2/users/2000000000000000001/tweets", None),
                         ("/2/users/2000000000000000001/tweets", "7140dibdnow9c7btw3w29grvxfcgvpb9n9coehpk7xz5i")]


def test_text_is_hashed_never_stored_and_long_form_wins(dbp):
    run(dbp, MAIN)
    blob = all_text(dbp)
    for ex_ in json.loads(MAIN.read_text())["exchanges"]:
        body = ex_["response"]["body"] or {}
        for p in (body.get("data") if isinstance(body.get("data"), list) else []) + (body.get("includes") or {}).get("tweets", []):
            assert p["text"] not in blob
    o = q(dbp, "SELECT content_hash, summary, retained_content, access_mode, collector FROM social_observations o "
               "JOIN social_items i USING(item_key) WHERE i.provider_item_id=?", P(101))[0]
    assert o["content_hash"] == store.text_hash("Invented original post about a made-up token, long form version.")
    assert o["summary"] is None and o["retained_content"] == "NONE"
    assert o["access_mode"] == "fixture" and o["collector"] == "x-api-v2/fixture"


def test_provenance_and_freshness(dbp):
    run(dbp, MAIN)
    p = q(dbp, "SELECT * FROM social_observation_provenance WHERE event_id LIKE ?", f"x:api.{P(102)}.%")[0]
    assert p["inbound_schema"] == I.INBOUND_SCHEMA_V2
    assert p["rights_basis"] == "synthetic_fixture" and "user timeline" in p["terms_note"]
    assert p["fetched_at"] == REC and p["freshness"] == "FRESH"
    assert p["provider_published_at"] == store.to_utc("2026-10-09T14:20:00Z")


def test_author_handle_change_keeps_one_account_and_history(dbp):
    run(dbp, MAIN)
    acc = q(dbp, "SELECT * FROM social_accounts WHERE provider_user_id='2000000000000000001'")
    assert len(acc) == 1 and acc[0]["handle"] == "example_alpha_new"
    hist = {r["handle_normalized"] for r in q(dbp, "SELECT * FROM social_account_handles WHERE account_id='x:id:2000000000000000001'")}
    assert hist == {"example_alpha", "example_alpha_new"}


def forget_cursors(dbp):
    """Simulate a lost cursor (crash after commit, restored DB): the same pages are read again."""
    con = sqlite3.connect(dbp)
    con.execute("DELETE FROM social_source_cursors")
    con.commit()
    con.close()


def test_duplicate_ids_and_rerun_add_nothing(dbp):
    run(dbp, MAIN)
    forget_cursors(dbp)
    before = {t: q(dbp, f"SELECT COUNT(*) n FROM {t}")[0]["n"] for t in ("social_observations", "social_items", "social_observation_provenance")}
    out, _, _ = run(dbp, MAIN, run_id="rerun")
    assert out["counts"]["created"] == 0 and out["counts"]["units_replayed"] == 3
    after = {t: q(dbp, f"SELECT COUNT(*) n FROM {t}")[0]["n"] for t in before}
    assert after == before
    # same post returned by the user timeline and the list: one item, the second sighting a duplicate event
    assert len(q(dbp, "SELECT * FROM social_items WHERE provider_item_id=?", P(101))) == 1


def test_billing_dedupe_within_utc_day(dbp):
    run(dbp, MAIN)
    forget_cursors(dbp)
    run(dbp, MAIN, run_id="rerun")
    rows = q(dbp, "SELECT * FROM social_api_spend WHERE mode='fixture' AND http_status=200 ORDER BY id")
    first, second = rows[:4], rows[4:]
    assert round(sum(r["est_cost_usd"] for r in first), 6) == 0.09   # 1 user lookup, 10 posts, 4 users
    assert sum(r["est_cost_usd"] for r in second) == 0                 # same resources, same UTC day
    assert all(r["endpoint"].startswith("/2/") and "?" not in r["endpoint"] for r in rows)


# ---------- incremental cursor and rate limits ----------

def test_cursor_since_id_and_rate_limit_window(dbp):
    run(dbp, MAIN)
    cur = {r["connector"]: r for r in q(dbp, "SELECT * FROM social_source_cursors")}
    assert cur[USER]["newest_id"] == P(105) and cur[USER]["provider_scope_id"] == "2000000000000000001"
    assert cur[LIST]["newest_id"] is None and cur[LIST]["rate_limit_reset_at"] == 1791558900.0
    assert cur[SEARCH]["last_status"] == "BLOCKED"
    # second run: user asks since_id (fixture only answers that exact request), list resumes after its window
    out, tr, _ = run(dbp, SECOND, now=T_SECOND)
    assert any(c["params"].get("since_id") == P(105) for c in tr.calls)
    assert not any(c["path"].startswith("/2/users/by/username") for c in tr.calls)   # resolved id was cached
    assert out["counts"]["created"] == 1 and out["counts"]["duplicates"] == 1         # P202 new; P201 same state as run 1
    assert q(dbp, "SELECT newest_id FROM social_source_cursors WHERE connector=?", LIST)[0]["newest_id"] == P(202)


def test_rate_limited_scope_is_not_called_before_reset(dbp):
    run(dbp, MAIN)
    tr = X.FixtureTransport(fixture())   # any request would be a FixtureMiss
    c = cfg(scopes=[{"kind": "list", "list_id": "1500000000000000001"}])
    out, tr, _ = run(dbp, tr, config=c, now=REC + 600, run_id="early")
    assert tr.calls == [] and out["health"][LIST]["status"] == "RATE_LIMITED"
    assert "not called" in out["health"][LIST]["errors"][0]


def test_429_records_reset_and_stops_scope(dbp):
    out, _, _ = run(dbp, MAIN)
    h = out["health"][LIST]
    assert h["status"] == "RATE_LIMITED" and "resets 2026-10-09T15:15:00" in h["errors"][0]
    assert out["health"][USER]["status"] == "OK"   # one limited scope does not mark the others


def test_429_short_wait_is_waited_once_when_configured(dbp):
    slept = []
    f = fixture(ALPHA_USER,
                ex("/2/users/2000000000000000001/tweets", BASE, 429, {"title": "Too Many Requests", "type": "https://api.x.com/2/problems/rate-limit-exceeded"},
                   {"x-rate-limit-remaining": "0", "x-rate-limit-reset": str(int(REC + 30))}),
                ex("/2/users/2000000000000000001/tweets", BASE, body={"data": [post(1)], "meta": {"result_count": 1}}))
    c = cfg(max_rate_wait_seconds=60, **ONLY_USER)
    ad = X.XApiAdapter(c, X.FixtureTransport(f), TOKEN, dbp, run_id="w", mode="fixture", clock=lambda: REC, sleep=slept.append)
    out = I.ingest(ad, dbp, now=T_RUN, run_id="w")
    assert out["health"][USER]["status"] == "OK" and slept == [30.0]


def test_remaining_zero_stops_before_next_page(dbp):
    f = fixture(ALPHA_USER,
                ex("/2/users/2000000000000000001/tweets", BASE, body={"data": [post(1)], "meta": {"result_count": 1, "next_token": "tok2"}},
                   headers={"x-rate-limit-remaining": "0", "x-rate-limit-reset": str(int(REC + 900))}))
    out, tr, _ = run(dbp, f, config=cfg(**ONLY_USER))
    assert out["health"][USER]["status"] == "RATE_LIMITED" and len(tr.calls) == 2
    assert out["counts"]["created"] == 1
    assert q(dbp, "SELECT newest_id FROM social_source_cursors WHERE connector=?", USER)[0]["newest_id"] is None


def test_page_cap_records_gap_and_advances_cursor(dbp):
    f = fixture(ALPHA_USER,
                ex("/2/users/2000000000000000001/tweets", BASE, body={"data": [post(5), post(4)], "meta": {"next_token": "t2"}}),
                ex("/2/users/2000000000000000001/tweets", dict(BASE, pagination_token="t2"), body={"data": [post(3)], "meta": {"next_token": "t3"}}))
    out, tr, _ = run(dbp, f, config=cfg(max_pages_per_scope=2, **ONLY_USER))
    assert len(tr.calls) == 3 and out["counts"]["created"] == 3
    assert out["health"][USER]["status"] == "DEGRADED" and "page cap 2 reached" in out["health"][USER]["errors"][0]
    assert q(dbp, "SELECT status FROM social_coverage WHERE scope LIKE ?", f"{USER}#%gap")[0]["status"] == "GAP"
    assert q(dbp, "SELECT newest_id FROM social_source_cursors WHERE connector=?", USER)[0]["newest_id"] == P(5)


def test_list_cursor_applied_client_side(dbp):
    c = cfg(scopes=[{"kind": "list", "list_id": "1500000000000000001"}])
    lp = "/2/lists/1500000000000000001/tweets"
    run(dbp, fixture(ex(lp, BASE, body={"data": [post(10), post(9)], "meta": {}})), config=c, run_id="a")
    f = fixture(ex(lp, BASE, body={"data": [post(12), post(11), post(10), post(9)], "meta": {"next_token": "never-followed"}}))
    out, tr, _ = run(dbp, f, config=c, run_id="b")
    assert len(tr.calls) == 1 and out["counts"]["created"] == 2   # stopped at the cursor, did not page further


# ---------- error classes ----------

@pytest.mark.parametrize("status,body,expect,text", [
    (401, {"title": "Unauthorized", "type": "about:blank"}, "BLOCKED", "credentials rejected (401)"),
    (403, {"title": "Forbidden", "type": "https://api.x.com/2/problems/not-authorized-for-resource"}, "BLOCKED", "protected or private"),
    (403, {"title": "Client Forbidden", "type": "https://api.x.com/2/problems/client-forbidden"}, "BLOCKED", "not enrolled"),
    (404, {"title": "Not Found Error", "type": "https://api.x.com/2/problems/resource-not-found"}, "DOWN", "404 not found"),
    (400, {"title": "Invalid Request", "detail": "secret detail 12345", "type": "https://api.x.com/2/problems/invalid-request"}, "DOWN", "400 invalid"),
])
def test_http_errors_map_to_connector_status(dbp, status, body, expect, text):
    f = fixture(ALPHA_USER, ex("/2/users/2000000000000000001/tweets", BASE, status, body))
    out, _, _ = run(dbp, f, config=cfg(**ONLY_USER))
    h = out["health"][USER]
    assert h["status"] == expect and text in h["errors"][0]
    assert "secret detail" not in json.dumps(out)       # problem detail is never copied
    assert out["status"] == "FAILED"


def test_protected_or_missing_user_scope(dbp):
    f = fixture(ex("/2/users/by/username/example_alpha", {"user.fields": X.USER_FIELDS},
                   body={"data": {"id": "2000000000000000001", "username": "example_alpha", "protected": True}}))
    out, tr, _ = run(dbp, f, config=cfg(**ONLY_USER))
    assert out["health"][USER]["status"] == "BLOCKED" and "protected account" in out["health"][USER]["errors"][0]
    assert len(tr.calls) == 1
    f = fixture(ex("/2/users/by/username/example_alpha", {"user.fields": X.USER_FIELDS},
                   body={"errors": [{"title": "Not Found Error", "type": "https://api.x.com/2/problems/resource-not-found"}]}))
    out, _, _ = run(dbp, f, config=cfg(**ONLY_USER), run_id="nf")
    assert out["health"][USER]["status"] == "DOWN" and "user not found" in out["health"][USER]["errors"][0]


def test_5xx_bounded_retries_then_down(dbp):
    f = fixture(ALPHA_USER, *[ex("/2/users/2000000000000000001/tweets", BASE, 503, {"title": "Service Unavailable"})] * 3)
    out, tr, _ = run(dbp, f, config=cfg(**ONLY_USER))
    assert len(tr.calls) == 4 and out["health"][USER]["status"] == "DOWN" and "after 3 attempts" in out["health"][USER]["errors"][0]


def test_protected_post_in_includes_is_quarantined_not_stored(dbp):
    body = {"data": [post(1, author="2000000000000000005")],
            "includes": {"users": [{"id": "2000000000000000005", "username": "example_locked", "protected": True}]}, "meta": {}}
    out, _, _ = run(dbp, fixture(ALPHA_USER, ex("/2/users/2000000000000000001/tweets", BASE, body=body)), config=cfg(**ONLY_USER))
    assert out["counts"]["quarantined"] == 1 and out["counts"]["created"] == 0
    assert q(dbp, "SELECT reason_code FROM social_ingest_quarantine")[0]["reason_code"] == "NOT_PUBLIC"


# ---------- edits and deletions ----------

def test_recheck_marks_missing_and_protected_posts(dbp):
    run(dbp, MAIN)
    ids = [r["provider_item_id"] for r in q(dbp, "SELECT i.provider_item_id FROM social_items i ORDER BY COALESCE(i.first_observed_at,"
                                                 " i.first_ingested_at) DESC LIMIT 100")]
    params = {"ids": ",".join(ids), "tweet.fields": TF, "user.fields": X.USER_FIELDS, "expansions": X.EXPANSIONS}
    body = {"data": [post(101, created="2026-10-09T14:10:00.000Z", text="Invented original post about a made-up token.",
                          public_metrics={"like_count": 9})],
            "includes": {"users": [{"id": "2000000000000000001", "username": "example_alpha_new", "protected": False}]},
            "errors": [{"resource_id": P(102), "resource_type": "tweet", "title": "Not Found Error", "detail": "Could not find tweet",
                        "type": "https://api.x.com/2/problems/resource-not-found"},
                       {"resource_id": P(104), "resource_type": "tweet", "title": "Authorization Error",
                        "type": "https://api.x.com/2/problems/not-authorized-for-resource"}]}
    c = cfg(scopes=[{"kind": "recheck", "max_items": 100}])
    out, _, _ = run(dbp, fixture(ex("/2/tweets", params, body=body, at="2026-10-09T19:00:00Z")), config=c, now=1791579600.0, run_id="re")
    st = {r["provider_item_id"]: r["retrieval_status"] for r in q(
        dbp, "SELECT i.provider_item_id, o.retrieval_status FROM social_observations o JOIN social_items i USING(item_key)"
             " WHERE o.observed_at=?", store.to_utc("2026-10-09T19:00:00Z"))}
    assert st == {P(101): "OK", P(102): "NOT_FOUND", P(104): "PROTECTED"}
    # a NOT_FOUND post is not looked up again
    c2 = X.load_config({"schema": X.CONFIG_SCHEMA, "scopes": [{"kind": "recheck"}], "budget": {"allow_billable": True, "max_usd_per_run": 1, "max_usd_per_month": 5}})
    con = X.store_connect(dbp)
    left = [r[0] for r in con.execute("SELECT i.provider_item_id FROM social_items i WHERE NOT EXISTS (SELECT 1 FROM social_observations o"
                                      " WHERE o.item_key=i.item_key AND o.retrieval_status IN ('NOT_FOUND','DELETED'))")]
    con.close()
    assert P(102) not in left and P(104) in left and c2.scopes[0].kind == "recheck"


def test_edit_creates_new_id_and_longer_history_wins(dbp):
    c = cfg(**ONLY_USER)
    run(dbp, fixture(ALPHA_USER, ex("/2/users/2000000000000000001/tweets", BASE,
                                    body={"data": [post(100, edit_history_tweet_ids=[P(100)])], "meta": {}})), config=c, run_id="v1")
    since = dict(BASE, since_id=P(100))
    run(dbp, fixture(ex("/2/users/2000000000000000001/tweets", since,
                        body={"data": [post(105, text="Edited invented sentence.", edit_history_tweet_ids=[P(100), P(105)])], "meta": {}})),
        config=c, run_id="v2")
    ctx = {r["item_key"]: r for r in q(dbp, "SELECT * FROM social_item_context")}
    assert json.loads(ctx[f"x:{P(105)}"]["edit_history_json"]) == [P(100), P(105)]
    assert json.loads(ctx[f"x:{P(100)}"]["edit_history_json"]) == [P(100)]   # the old version keeps what was seen then


# ---------- timestamps and freshness ----------

def test_timestamps_provider_vs_fetch_and_future_post_quarantined(dbp):
    body = {"data": [post(1, created="2026-10-09T14:59:59.000Z"), post(2, created="2026-10-09T16:00:00.000Z")], "meta": {}}
    out, _, _ = run(dbp, fixture(ALPHA_USER, ex("/2/users/2000000000000000001/tweets", BASE, body=body)), config=cfg(**ONLY_USER))
    assert out["counts"]["created"] == 1 and out["counts"]["quarantined"] == 1
    o = q(dbp, "SELECT o.observed_at, i.published_at FROM social_observations o JOIN social_items i USING(item_key)")[0]
    assert o["observed_at"] == REC and o["published_at"] == REC - 1
    assert "published_at: after fetched_at" in q(dbp, "SELECT errors_json FROM social_ingest_quarantine")[0]["errors_json"]


def test_stale_response_is_flagged_and_health_reports_cursor_age(dbp, tmp_path):
    out, _, _ = run(dbp, MAIN, now=REC + 13 * 3600)
    assert out["counts"]["stale_items"] == 7 and out["health"][USER]["status"] == "DEGRADED"
    assert {r["freshness"] for r in q(dbp, "SELECT freshness FROM social_observation_provenance")} == {"STALE"}
    h = X.health(CONFIG, dbp, env={X.TOKEN_ENV: TOKEN}, now=REC + 13 * 3600 + 7200)
    ages = {c["connector"]: c["age_hours"] for c in h["cursors"]}
    assert ages[USER] == 2.0 and ages[LIST] is None


# ---------- billing guard ----------

def test_no_consent_means_no_request(dbp):
    out, tr, _ = run(dbp, MAIN, config=cfg(budget={"allow_billable": False}))
    assert tr.calls == [] and out["status"] == "FAILED"
    assert "not consented" in out["health"][USER]["errors"][0]
    assert {h["status"] for h in out["health"].values()} == {"BLOCKED", "DEGRADED"}


def test_run_cap_blocks_before_the_request_that_could_exceed_it(dbp):
    # resolve costs at most $0.01; one page of 10 posts costs at most 10*0.005 + 10*0.005 + 20*0.01 = $0.30
    out, tr, _ = run(dbp, MAIN, config=cfg(budget={"max_usd_per_run": 0.25}, **ONLY_USER))
    assert len(tr.calls) == 1 and "run cap" in out["health"][USER]["errors"][0]
    out, tr, _ = run(dbp, MAIN, config=cfg(budget={"max_usd_per_run": 0.31}, **ONLY_USER), run_id="b")
    # the user id was cached by the first run; page 1 fits ($0.30), page 2 would pass the cap with what page 1 cost
    assert [c["path"] for c in tr.calls] == ["/2/users/2000000000000000001/tweets"]
    assert "run cap $0.310" in out["health"][USER]["errors"][0] and out["counts"]["created"] == 5


def spend(dbp, usd, mode, day="2026-10-01"):
    con = X.store_connect(dbp)
    con.execute("INSERT INTO social_api_spend(connector,endpoint,http_status,billing_day,est_cost_usd,mode,requested_at)"
                " VALUES ('x_api:user:someone','/2/users/{id}/tweets',200,?,?,?,?)", (day, usd, mode, REC - 8 * 86400))
    con.commit()
    con.close()


def test_monthly_cap_counts_spend_of_the_same_mode_only(dbp):
    spend(dbp, 4.0, "live")
    spend(dbp, 99.0, "fixture")
    spend(dbp, 99.0, "live", day="2026-09-30")   # last month
    # live mode over a fixture transport: the guard sees $4.00 of live spend this month, not the fixture or September rows
    out, tr, _ = run(dbp, MAIN, config=cfg(**ONLY_USER), mode="live")
    assert len(tr.calls) == 3 and out["health"][USER]["status"] == "OK"
    spend(dbp, 0.9, "live")
    forget_cursors(dbp)
    out, tr, _ = run(dbp, MAIN, config=cfg(**ONLY_USER), mode="live", run_id="b")
    assert len(tr.calls) == 1 and "monthly cap $5.000" in out["health"][USER]["errors"][0]
    forget_cursors(dbp)
    out, tr, _ = run(dbp, MAIN, config=cfg(**ONLY_USER), run_id="fx")   # fixture spend ($99) blocks fixture mode only
    assert "monthly cap" in out["health"][USER]["errors"][0]


def test_ingest_cost_budget_also_stops_requests(dbp):
    out, tr, _ = run(dbp, MAIN, config=cfg(**ONLY_USER), budget=I.Budget(max_cost=0.05))
    assert len(tr.calls) == 1 and "run budget" in out["health"][USER]["errors"][0]


# ---------- credentials and secrets ----------

def test_credentials_missing_no_request(dbp):
    out, tr, _ = run(dbp, MAIN, token=None)
    assert tr.calls == [] and out["status"] == "FAILED"
    assert all("credentials_missing" in h["errors"][0] for h in out["health"].values())


def test_token_never_leaks(dbp, caplog, capsys):
    f = fixture(ALPHA_USER, *[{"recorded_at": "2026-10-09T15:00:00Z", "request": {"path": "/2/users/2000000000000000001/tweets", "params": BASE},
                               "raise": "connection reset while sending Authorization: Bearer {token}"}] * 3)
    with caplog.at_level(logging.INFO, logger="memelab.social.ingest"):
        out, tr, ad = run(dbp, f, config=cfg(**ONLY_USER))
    assert out["health"][USER]["status"] == "DOWN"
    blob = json.dumps(out) + caplog.text + all_text(dbp) + repr(ad) + json.dumps(tr.calls) + capsys.readouterr().err
    assert TOKEN not in blob and "TOKEN-0123" not in blob
    assert "[REDACTED]" in out["health"][USER]["errors"][0]


def test_config_refuses_credentials_and_bad_scopes():
    base = json.loads(CONFIG.read_text())
    for bad in ({"bearer_token": "x"}, {"budget": {"api_key": "x", "allow_billable": False}}):
        with pytest.raises(ValueError, match="must not hold credentials"):
            X.load_config({**base, **bad})
    with pytest.raises(ValueError, match="username"):
        X.load_config({**base, "scopes": [{"kind": "user", "username": "not a handle!"}]})
    with pytest.raises(ValueError, match="duplicate"):
        X.load_config({**base, "scopes": [{"kind": "list", "list_id": "1"}, {"kind": "list", "list_id": "1"}]})


def test_health_states_without_network(dbp, tmp_path, monkeypatch):
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network used")))
    assert X.health(CONFIG, dbp, env={})["status"] == "credentials_missing"
    assert X.health(tmp_path / "none.json", dbp, env={X.TOKEN_ENV: TOKEN})["status"] == "not_configured"
    off = tmp_path / "off.json"
    off.write_text(json.dumps({**json.loads(CONFIG.read_text()), "budget": {"allow_billable": False}}))
    assert X.health(off, dbp, env={X.TOKEN_ENV: TOKEN})["status"] == "billing_not_consented"
    h = X.health(CONFIG, dbp, env={X.TOKEN_ENV: TOKEN})
    assert h["status"] == "ready" and TOKEN not in json.dumps(h) and h["network_calls_made"] == 0


# ---------- CLI harness: fixture ingest -> stored observation; live refuses without credentials ----------

def test_cli_fixture_flow_and_no_false_live_claim(dbp, capsys, monkeypatch):
    monkeypatch.delenv(X.TOKEN_ENV, raising=False)
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "x-ingest", "--config", str(CONFIG), "--fixture", str(MAIN), "--db", str(dbp), "--now", str(T_RUN),
                  "--run-id", "cli_fx"])
    assert e.value.code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["mode"] == "fixture" and out["status"] == "PARTIAL" and out["counts"]["created"] == 7
    eid = q(dbp, "SELECT event_id FROM social_observation_provenance WHERE event_id LIKE ?", f"x:api.{P(103)}.%")[0]["event_id"]
    cli.main(["social", "status", "--db", str(dbp), "--event", eid])
    rec = json.loads(capsys.readouterr().out)
    assert rec["item"]["provider_item_id"] == P(103) and rec["observation"]["access_mode"] == "fixture"
    # health: fixture rows are not live evidence
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "x-health", "--config", str(CONFIG), "--db", str(dbp)])
    h = json.loads(capsys.readouterr().out)
    assert e.value.code == 1 and h["status"] == "credentials_missing"
    assert h["live_evidence"]["requests"] == 0 and h["live_evidence"]["verdict"].startswith("none")
    # live ingest refuses before any network call
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network used")))
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "x-ingest", "--config", str(CONFIG), "--db", str(dbp)])
    r = json.loads(capsys.readouterr().out)
    assert e.value.code == 1 and r == {"network_calls_made": 0, "next_step": r["next_step"], "reason": "credentials_missing", "status": "NOT_RUN"}


def test_inbound_v1_units_unchanged_by_v2_support(dbp):
    """A /1 item with a context key is read as before: the key is ignored, nothing written to the context tables."""
    from memelab.social.bridge_adapter import BridgeInboxAdapter
    f = dbp.parent / "r.result.json"
    f.write_text(json.dumps({"_plan": "p", "soc:x:example_a": {"s": 200, "body": {
        "schema": I.INBOUND_SCHEMA, "fetched_at": "2026-10-09T15:00:00Z",
        "source": {"platform": "x", "source_id": "example_a", "access_mode": "fixture", "collector": "t", "rights_basis": "synthetic_fixture", "visibility": "PUBLIC"},
        "items": [{"provider_item_id": "1", "context": {"reference_type": "REPOST"}}]}}}))
    out = I.ingest(BridgeInboxAdapter([f], sleep=lambda s: None), dbp, now=T_RUN)
    assert out["counts"]["created"] == 1 and q(dbp, "SELECT COUNT(*) n FROM social_item_context")[0]["n"] == 0
    assert json.loads(q(dbp, "SELECT ignored_fields FROM social_observation_provenance")[0]["ignored_fields"]) == ["context"]


def test_example_config_loads_and_is_off_by_default(dbp):
    ex_cfg = ROOT / "docs" / "social-intelligence" / "x_api.example.json"
    c = X.load_config(ex_cfg)
    assert [s.kind for s in c.scopes] == ["user", "list", "search", "recheck"] and c.allow_billable is False
    assert X.health(ex_cfg, dbp, env={X.TOKEN_ENV: TOKEN})["status"] == "billing_not_consented"
