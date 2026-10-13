"""Phase 20: Discord bot adapter (REST and gateway). Recorded synthetic fixtures only; no network, fixed clock, temp DB
and private folder.

Fixtures: tests/fixtures/social/discord_bot/ (invented server, users, ids and sentences shaped like the documented
responses and gateway payloads; generated once and committed).
"""
import json
import logging
import sqlite3
from pathlib import Path

import pytest

from memelab import cli, db
from memelab.social import discord_bot as D
from memelab.social import ingest as I
from memelab.social import schema, store
from memelab.social.api_common import TextSink, extract_after_ingest

ROOT = Path(__file__).resolve().parent.parent
FXD = ROOT / "tests" / "fixtures" / "social" / "discord_bot"
CONFIG, MAIN, SECOND = FXD / "fx_discord_config.json", FXD / "fx_discord_main.json", FXD / "fx_discord_second.json"
GATEWAY, GW4014 = FXD / "fx_discord_gateway.json", FXD / "fx_discord_gateway_4014.json"
BODIES = ROOT / "tests" / "fixtures" / "social" / "resolve" / "fx_providers.json"
T1, T2, T3 = 1791676800.0, 1791763200.0, 1791849600.0     # 2026-10-11, -12, -13 00:00Z
TOKEN = "fixtureDiscordTokenNotReal01.GfIxTr.fixtureTokenNotRealDoNotLeak0123456789"   # not the [MNO] shape the audit flags
CA = "8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ"
G, BOT = "1080278227353600001", "1191168914227200002"
C1, C2, C3 = "1080278479011840006", "1080278730670080007", "1080278982328320008"
M = {1: "1558571573575680101", 2: "1558573335183360102", 3: "1558575096791040103", 4: "1558576858398720104",
     5: "1558578620006400105", 6: "1558595481108480106", 7: "1558597242716160107", 8: "1558599004323840108",
     9: "1558600765931520109", 10: "1558602527539200110"}
GM = {1: "1559309687193600301", 2: "1559324786688000302", 3: "1559339886182400303"}
K = lambda n: f"discord:{C1}_{M[n]}"
GK = lambda n: f"discord:{C1}_{GM[n]}"
CONN = lambda c: f"discord_bot:channel:{c}"
A_AT = "2026-10-10T23:00:00Z"


@pytest.fixture()
def dbp(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private" / "p.sqlite"))
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    return p


def raw_cfg():
    return json.loads(CONFIG.read_text())


def cfg(**over):
    c = raw_cfg()
    c.update(over)
    return D.load_config(c)


def only_c1(**over):
    c = raw_cfg()
    c["guilds"][0]["channels"] = c["guilds"][0]["channels"][:1]
    c.update(over)
    return D.load_config(c)


RUNS = iter(range(1, 10_000))


def run(dbp, fixture, config=None, now=T1, token=TOKEN, sink=None, sleeps=None):
    tr = fixture if isinstance(fixture, D.FixtureTransport) else D.FixtureTransport(fixture)
    rid = f"d{now}_{next(RUNS)}"
    ad = D.DiscordBotAdapter(config or cfg(), tr, token, dbp, run_id=rid, mode="fixture", clock=lambda: now,
                             sleep=(sleeps.append if sleeps is not None else (lambda s: None)), text_sink=sink)
    out = I.ingest(ad, dbp, now=now, run_id=rid)
    return out, tr, ad


def gw(dbp, fixture=GATEWAY, config=None, now=T3, token=TOKEN, sink=None):
    tr = D.GatewayFixtureTransport(fixture)
    rid = f"g{now}_{next(RUNS)}"
    ad = D.DiscordGatewayAdapter(config or cfg(), tr, token, dbp, run_id=rid, mode="fixture", clock=lambda: now, text_sink=sink)
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


def ex_list(path=MAIN):
    return json.loads(Path(path).read_text())["exchanges"]


def fixture(*exchanges):
    return {"schema": D.FIXTURE_SCHEMA, "exchanges": list(exchanges)}


def ex(path, params, status, body, headers=None, at=A_AT):
    return {"request": {"method": "GET", "path": path, "params": params or {}}, "recorded_at": at,
            "response": {"status": status, "headers": headers or {}, "body": body}}


def preflight(at=A_AT, flags=1 << 19):
    e = ex_list()
    return [ex("/applications/@me", None, 200, {"id": "1", "flags": flags}, at=at), {**e[1], "recorded_at": at},
            {**e[2], "recorded_at": at}, {**e[3], "recorded_at": at}]


def ch1(at=A_AT, **over):
    body = {**ex_list()[4]["response"]["body"], **over}
    return ex(f"/channels/{C1}", None, 200, body, at=at)


def page(msgs, params=None, headers=None, at=A_AT):
    return ex(f"/channels/{C1}/messages", params or {"limit": 100}, 200, msgs, headers=headers, at=at)


def m(mid, content="Invented words", **kw):
    d = {"id": mid, "channel_id": C1, "author": {"id": "794354201395200010", "username": "example_poster_a"}, "content": content,
         "timestamp": "2026-10-10T20:00:00+00:00", "edited_timestamp": None, "type": 0, "attachments": [], "embeds": []}
    d.update(kw)
    return d


def call(argv):
    try:
        cli.main(argv)
    except SystemExit as e:
        return e.code
    return 0


# ---------- the main fixture: permitted channel observations ----------

def test_main_fixture_ids_authors_replies_forwards_links_edits(dbp):
    out, tr, ad = run(dbp, MAIN)
    assert out["status"] == "PARTIAL" and out["counts"]["created"] == 9 and out["counts"]["quarantined"] == 0
    assert ad.requests == 8 and [c["path"] for c in tr.calls][:2] == ["/applications/@me", "/users/@me"]
    assert ad.dropped == {"system_message": 1}
    items = {r["item_key"]: r for r in q(dbp, "SELECT * FROM social_items")}
    assert sorted(items) == sorted(K(n) for n in (1, 2, 3, 4, 5, 6, 7, 8, 10))
    assert items[K(1)]["original_url"] == f"https://discord.com/channels/{G}/{C1}/{M[1]}"
    assert items[K(1)]["published_at"] == store.to_utc("2026-10-10T20:07:00Z")
    assert items[K(1)]["account_id"] == "discord:id:794354201395200010"
    acct = q(dbp, "SELECT * FROM social_accounts WHERE account_id='discord:id:794354201395200010'")[0]
    assert acct["handle"] == "example_poster_a" and acct["display_name"] is None
    assert items[K(8)]["account_id"] is None and items[K(10)]["account_id"] is None      # bot and webhook: no author
    ctx = {r["item_key"]: r["reference_type"] for r in q(dbp, "SELECT * FROM social_item_context")}
    assert ctx[K(1)] == "ORIGINAL" and ctx[K(2)] == "REPLY" and ctx[K(4)] == "REPOST" and ctx[K(5)] == "REPOST"
    assert ctx[K(6)] == "QUOTE"
    refs = {(r["item_key"], r["ref_type"]): r for r in q(dbp, "SELECT * FROM social_item_refs")}
    assert refs[(K(2), "replied_to")]["referenced_item_key"] == K(1)
    assert refs[(K(2), "replied_to")]["referenced_author_id"] == "794354201395200010"
    assert refs[(K(5), "retweeted")]["referenced_item_key"] == K(1)
    assert refs[(K(6), "quoted")]["referenced_item_key"] == K(3)
    assert not [r for r in refs.values() if "@me" in r["referenced_item_key"]]           # a DM link is never followed
    fw = q(dbp, "SELECT * FROM social_item_forwards")
    assert len(fw) == 1 and fw[0]["item_key"] == K(4) and fw[0]["origin_item_key"] == K(1) and fw[0]["origin_type"] == "channel"
    vers = q(dbp, "SELECT * FROM social_item_versions WHERE item_key=?", K(3))
    assert [v["version_kind"] for v in vers] == ["EDIT"] and vers[0]["provider_version_at"] == store.to_utc("2026-10-10T20:40:00Z")
    cur = q(dbp, "SELECT * FROM social_source_cursors WHERE connector=?", CONN(C1))[0]
    assert cur["newest_id"] == M[10] and cur["last_status"] == "OK" and cur["provider_scope_id"] == G
    app = q(dbp, "SELECT last_status FROM social_source_cursors WHERE scope='application'")[0]
    assert app["last_status"] == "message_content_enabled"


def test_text_embeds_names_and_topics_are_never_stored(dbp):
    run(dbp, MAIN)
    blob = all_text(dbp)
    for word in ("Invented fixture text", "Invented reply", "Invented separate take", "Invented embed preview", "Invented own words",
                 "invented.png", "Invented Display", "Invented Example Community", "invented-alpha-chat", "Invented channel topic",
                 "Invented bot price alert", "Invented webhook relay", "example_price_bot"):
        assert word not in blob, word
    body = ex_list()[5]["response"]["body"]
    m1 = next(x for x in body if x["id"] == M[1])
    assert q(dbp, "SELECT content_hash FROM social_observations WHERE item_key=?", K(1))[0]["content_hash"] == store.text_hash(m1["content"])
    # a forward is hashed on the forwarded words, so the identical-text heuristic sees the copy
    assert q(dbp, "SELECT content_hash FROM social_observations WHERE item_key=?", K(4))[0]["content_hash"] == store.text_hash(m1["content"])


def test_provenance_rights_basis_and_fixture_labels(dbp):
    run(dbp, MAIN)
    prov = q(dbp, "SELECT * FROM social_observation_provenance")
    assert {p["rights_basis"] for p in prov} == {"synthetic_fixture"} and {p["inbound_schema"] for p in prov} == {I.INBOUND_SCHEMA_V3}
    assert {r["access_mode"] for r in q(dbp, "SELECT access_mode FROM social_observations")} == {"fixture"}
    spend = q(dbp, "SELECT * FROM social_api_spend")
    assert len(spend) == 8 and {s["mode"] for s in spend} == {"fixture"} and sum(s["est_cost_usd"] for s in spend) == 0
    assert {s["endpoint"] for s in spend} >= {"/applications/@me", "/channels/{channel}/messages"}


def test_role_gated_and_history_less_channels_are_not_read(dbp):
    out, tr, _ = run(dbp, MAIN)
    paths = [c["path"] for c in tr.calls]
    assert f"/channels/{C2}/messages" not in paths and f"/channels/{C3}/messages" not in paths
    assert "not_public" in out["health"][CONN(C2)]["errors"][0]
    assert "READ_MESSAGE_HISTORY" in out["health"][CONN(C3)]["errors"][0]


def test_rerun_adds_nothing(dbp):
    run(dbp, MAIN)
    n = q(dbp, "SELECT COUNT(*) n FROM social_observations")[0]["n"]
    out, _, _ = run(dbp, MAIN)
    assert out["counts"]["created"] == 0 and q(dbp, "SELECT COUNT(*) n FROM social_observations")[0]["n"] == n


def test_forwards_and_link_only_shares_are_never_independent(dbp):
    run(dbp, MAIN)
    con = sqlite3.connect(dbp)
    assert store.is_independent_original(con, K(4)) is False          # forward
    assert store.is_independent_original(con, K(5)) is False          # link-only share
    assert store.is_independent_original(con, K(6)) is True           # own words with a link: a quote (D-029)
    assert store.is_independent_original(con, K(1)) is True
    con.close()


# ---------- second run: cursor, recheck, edits, deletion, purge ----------

def test_second_run_cursor_recheck_edit_and_deletion_purge(dbp):
    sink = TextSink()
    run(dbp, MAIN, sink=sink)
    extract_after_ingest(dbp, sink, now=T1, bodies=json.loads(BODIES.read_text())["bodies"])
    h1 = q(dbp, "SELECT content_hash FROM social_observations WHERE item_key=?", K(1))[0]["content_hash"]
    out, tr, _ = run(dbp, SECOND, now=T2)
    assert out["counts"]["created"] == 3          # the new message, m1 DELETED, the second edit of m3; m2 unchanged
    after = [c for c in tr.calls if c["path"] == f"/channels/{C1}/messages"][0]
    assert after["params"] == {"limit": "100", "after": M[10]}
    last = {r["item_key"]: r["retrieval_status"] for r in q(dbp, "SELECT item_key, retrieval_status FROM social_observations ORDER BY id")}
    assert last[K(1)] == "DELETED" and last[K(2)] == "OK"
    assert [v["version_kind"] for v in q(dbp, "SELECT version_kind FROM social_item_versions WHERE item_key=? ORDER BY provider_version_at",
                                          K(3))] == ["EDIT", "EDIT"]
    res = D.purge_deleted(dbp, now=T2)
    assert res["items_purged"] == 1 and res["claims_cleared"] >= 1
    # the forward of m1 is a message of its own that still exists, so its copy of the hash stays; nothing else does
    assert {r["item_key"] for r in q(dbp, "SELECT item_key FROM social_observations WHERE content_hash=?", h1)} == {K(4)}
    rows = q(dbp, "SELECT content_hash, metrics_json, account_id FROM social_observations WHERE item_key=?", K(1))
    assert all(r["content_hash"] is None and r["metrics_json"] is None and r["account_id"] is None for r in rows)
    assert D.purge_deleted(dbp, now=T2) == {"items_purged": 0, "observations_cleared": 0, "claims_cleared": 0,
                                            "private_rows_deleted": 0, "accounts_erased": 0}


def test_user_deletion_request_erases_the_account(dbp):
    run(dbp, MAIN)
    res = D.purge_deleted(dbp, now=T1, users=["805588225228800011"])     # example_poster_b asks to be forgotten
    assert res["accounts_erased"] == 1
    assert "example_poster_b" not in all_text(dbp) and "805588225228800011" not in all_text(dbp)
    assert q(dbp, "SELECT account_id FROM social_items WHERE item_key=?", K(2))[0]["account_id"] is None


def test_health_reports_pending_purge(dbp):
    run(dbp, MAIN)
    run(dbp, SECOND, now=T2)
    assert D.health(CONFIG, dbp, env={})["deletion_purge_pending_items"] == 1
    D.purge_deleted(dbp, now=T2)
    assert D.health(CONFIG, dbp, env={})["deletion_purge_pending_items"] == 0


# ---------- permission revocation ----------

def test_permission_revoked_between_runs_blocks_the_channel_and_never_marks_deletion(dbp):
    run(dbp, MAIN, config=only_c1(recheck={"enabled": False}))
    revoked = ch1(at="2026-10-11T23:00:00Z", permission_overwrites=[{"id": "1191531302092800004", "type": 0, "allow": "0",
                                                                     "deny": str(1 << 10)}])
    out, tr, _ = run(dbp, fixture(*preflight("2026-10-11T23:00:00Z"), revoked), config=only_c1(), now=T2)
    assert f"/channels/{C1}/messages" not in [c["path"] for c in tr.calls]
    assert not [c for c in tr.calls if c["path"].startswith(f"/channels/{C1}/messages/")]      # no recheck while blocked
    assert out["health"][CONN(C1)]["status"] == "BLOCKED" and "VIEW_CHANNEL" in out["health"][CONN(C1)]["errors"][0]
    assert not q(dbp, "SELECT 1 FROM social_observations WHERE retrieval_status IN ('DELETED','NOT_FOUND')")
    assert q(dbp, "SELECT last_status FROM social_source_cursors WHERE connector=?", CONN(C1))[0]["last_status"] == "access_denied"
    assert CONN(C1) in D.health(CONFIG, dbp, env={})["blocked_channels"]


def test_403_missing_access_mid_run_blocks_that_channel_only(dbp):
    c = raw_cfg()
    c["guilds"][0]["channels"] = [c["guilds"][0]["channels"][0], {"channel_id": C3, "label": "ann"}]
    c3_open = {**ex_list()[7]["response"]["body"], "permission_overwrites": []}
    f = fixture(*preflight(), ch1(), ex(f"/channels/{C1}/messages", {"limit": 100}, 403, {"message": "Missing Access", "code": 50001}),
                ex(f"/channels/{C3}", None, 200, c3_open),
                ex(f"/channels/{C3}/messages", {"limit": 100}, 200, [m("1558571573575680999", channel_id=C3)]))
    out, _, _ = run(dbp, f, config=D.load_config(c))
    assert out["health"][CONN(C1)]["status"] == "BLOCKED" and "access_denied" in out["health"][CONN(C1)]["errors"][0]
    assert out["health"][CONN(C3)]["status"] == "OK" and out["counts"]["created"] == 1


def test_recheck_403_is_not_a_deletion(dbp):
    run(dbp, MAIN, config=only_c1())
    f = fixture(*preflight("2026-10-11T23:00:00Z"), ch1("2026-10-11T23:00:00Z"),
                page([], {"limit": 100, "after": M[10]}, at="2026-10-11T23:00:00Z"),
                *[ex(f"/channels/{C1}/messages/{M[n]}", None, 403, {"message": "Missing Access", "code": 50001},
                     at="2026-10-11T23:00:00Z") for n in (1, 2, 3, 4, 5, 6, 7, 8, 10)])
    out, tr, _ = run(dbp, f, config=only_c1(), now=T2)
    assert len([c for c in tr.calls if "/messages/" in c["path"]]) == 1      # first 403 blocks the channel's recheck
    assert not q(dbp, "SELECT 1 FROM social_observations WHERE retrieval_status IN ('DELETED','NOT_FOUND')")


def test_gateway_revocation_removal_and_role_gate(dbp):
    out, tr, ad = gw(dbp)
    assert out["health"][CONN(C1)]["status"] == "BLOCKED" and "VIEW_CHANNEL" in out["health"][CONN(C1)]["errors"][0]
    assert "not_public" in out["health"][CONN(C2)]["errors"][0]
    assert ad.dropped["channel_blocked"] == 2           # the holders-only post and the post after revocation
    keys = {r["item_key"] for r in q(dbp, "SELECT item_key FROM social_items")}
    assert not any("1559" in k and k.endswith("397") for k in keys) and not any(k.startswith(f"discord:{C2}_") for k in keys)
    removal = {"schema": D.GATEWAY_FIXTURE_SCHEMA, "recorded_at": "2026-10-12T23:30:00Z", "connections": [{"frames": [
        *json.loads(GATEWAY.read_text())["connections"][0]["frames"][:3],
        {"op": 0, "s": 4, "t": "GUILD_DELETE", "d": {"id": G}},
        {"op": 0, "s": 5, "t": "MESSAGE_CREATE", "d": {**m("1559339886182400999"), "guild_id": G}}], "close": 1000}]}
    out, _, ad = gw(dbp, removal)
    assert "removed from this server" in out["health"][CONN(C1)]["errors"][0] and ad.dropped["channel_blocked"] == 1


# ---------- message content intent ----------

def test_intent_missing_blocks_with_a_clear_reason_and_reads_nothing(dbp):
    out, tr, ad = run(dbp, fixture(ex("/applications/@me", None, 200, {"id": "1", "flags": 0})))
    assert [c["path"] for c in tr.calls] == ["/applications/@me"]
    app = out["health"]["discord_bot:app:memelab-research"]
    assert app["status"] == "BLOCKED" and app["errors"][0].startswith("message_content_intent_missing")
    assert all(h["status"] == "BLOCKED" for h in out["health"].values()) and out["status"] == "FAILED"
    h = D.health(CONFIG, dbp, env={D.TOKEN_ENV: TOKEN})
    assert h["status"] == "intent_missing" and h["message_content_intent"] == "message_content_intent_missing"
    assert "Message Content Intent" in h["next_step"]


def test_intent_missing_metadata_only_when_allowed(dbp):
    body = [m(M[1], content=""), m(M[2], content="", type=19, message_reference={"type": 0, "message_id": M[1], "channel_id": C1})]
    f = fixture(*preflight(flags=0), ch1(), page(body))
    out, _, ad = run(dbp, f, config=only_c1(require_message_content=False, recheck={"enabled": False}))
    assert out["counts"]["created"] == 2 and out["health"][CONN(C1)]["status"] == "DEGRADED"
    assert "message_content_intent_missing" in out["health"][CONN(C1)]["errors"][0]
    assert all(r["content_hash"] is None for r in q(dbp, "SELECT content_hash FROM social_observations"))
    assert q(dbp, "SELECT reference_type FROM social_item_context WHERE item_key=?", K(2))[0]["reference_type"] == "REPLY"


def test_gateway_4014_reports_privileged_intent_missing_and_never_asks_for_dms(dbp):
    out, tr, ad = gw(dbp, GW4014)
    gwc = "discord_bot:gateway:memelab-research"
    assert out["health"][gwc]["status"] == "BLOCKED" and out["health"][gwc]["errors"][0].startswith("privileged_intent_missing")
    ident = tr.sent[0]
    assert ident["op"] == 2 and ident["d"]["intents"] & D.INTENT_MESSAGE_CONTENT and not ident["d"]["intents"] & D.INTENT_DIRECT_MESSAGES
    assert D.health(CONFIG, dbp, env={D.TOKEN_ENV: TOKEN})["status"] == "intent_missing"
    with pytest.raises(ValueError, match="direct-message"):
        D.GatewaySession(TOKEN, intents=D.INTENT_GUILD_MESSAGES | (1 << 12))


# ---------- gateway: duplicates, out-of-order, resume, partial updates ----------

def test_gateway_duplicates_resume_out_of_order_and_delete_before_create(dbp):
    out, tr, ad = gw(dbp)
    s = ad.session
    assert s.duplicates == 2 and s.resumed == 1 and s.connection == 2
    assert [f["op"] for f in tr.sent] == [2, 1, 6]          # identify, heartbeat reply, resume on the second connection
    assert tr.sent[2]["d"]["seq"] == 6
    assert ad.dropped["direct_message"] == 1 and ad.dropped["partial_update"] == 1
    assert out["counts"]["created"] == 5
    con = sqlite3.connect(dbp)
    con.row_factory = sqlite3.Row
    cv = store.current_version(con, GK(2))
    assert cv["version_kind"] == "EDIT" and cv["provider_version_at"] == store.to_utc("2026-10-12T22:10:00Z")
    con.close()
    assert len(q(dbp, "SELECT * FROM social_item_versions WHERE item_key=?", GK(2))) == 2
    # the delete arrived before the create: the message ends deleted and the purge erases what the create stored
    D.purge_deleted(dbp, now=T3)
    rows = q(dbp, "SELECT retrieval_status, content_hash FROM social_observations WHERE item_key=?", GK(3))
    assert {r["retrieval_status"] for r in rows} == {"DELETED", "OK"} and all(r["content_hash"] is None for r in rows)
    assert len(q(dbp, "SELECT 1 FROM social_observations WHERE item_key=?", GK(1))) == 1      # unfurl and duplicate: one row
    blob = all_text(dbp)
    assert "fixture-session-not-secret" not in blob and "Invented gateway" not in blob and "Invented direct message" not in blob


def test_same_message_from_rest_and_gateway_is_one_observation(dbp):
    g1 = json.loads(GATEWAY.read_text())["connections"][0]["frames"][3]["d"]
    f = fixture(*preflight(), ch1(), page([{k: v for k, v in g1.items() if k not in ("guild_id", "member")}]))
    run(dbp, f, config=only_c1(recheck={"enabled": False}))
    gw(dbp)
    assert len(q(dbp, "SELECT 1 FROM social_observations WHERE item_key=?", GK(1))) == 1


def test_gateway_rerun_adds_nothing(dbp):
    gw(dbp)
    out, _, _ = gw(dbp)
    assert out["counts"]["created"] == 0


# ---------- checkpoint reset, no text, no-source day ----------

def test_reset_checkpoint_rereads_without_duplicates(dbp):
    run(dbp, MAIN)
    n = q(dbp, "SELECT COUNT(*) n FROM social_observations")[0]["n"]
    r = D.reset_checkpoint(dbp, C1, now=T1)
    assert r["had_cursor"] and r["previous_newest_id"] == M[10]
    assert not q(dbp, "SELECT 1 FROM social_source_cursors WHERE connector=? AND scope='messages'", CONN(C1))
    out, tr, _ = run(dbp, MAIN)
    assert {"limit": "100"} in [c["params"] for c in tr.calls if c["path"] == f"/channels/{C1}/messages"]
    assert out["counts"]["created"] == 0 and q(dbp, "SELECT COUNT(*) n FROM social_observations")[0]["n"] == n
    assert q(dbp, "SELECT newest_id FROM social_source_cursors WHERE connector=?", CONN(C1))[0]["newest_id"] == M[10]


def test_attachment_only_message_has_no_text(dbp):
    sink = TextSink()
    run(dbp, MAIN, sink=sink)
    obs = q(dbp, "SELECT content_hash, metrics_json FROM social_observations WHERE item_key=?", K(7))[0]
    assert obs["content_hash"] is None and json.loads(obs["metrics_json"]) == {"attachment_count": 1, "embed_count": 0}
    assert not [k for k in sink.items() if k[0][1].endswith(M[7])]


def test_no_source_day_empty_pages_keep_the_cursor_and_the_brief_says_so(dbp, capsys):
    run(dbp, MAIN, config=only_c1(recheck={"enabled": False}))
    f = fixture(*preflight("2026-10-11T23:00:00Z"), ch1("2026-10-11T23:00:00Z"),
                page([], {"limit": 100, "after": M[10]}, at="2026-10-11T23:00:00Z"))
    out, _, _ = run(dbp, f, config=only_c1(recheck={"enabled": False}), now=T2)
    assert out["status"] == "OK" and out["counts"]["created"] == 0
    cur = q(dbp, "SELECT newest_id, last_success_at FROM social_source_cursors WHERE connector=?", CONN(C1))[0]
    assert cur["newest_id"] == M[10] and cur["last_success_at"] == T2
    call(["social", "narrative-snapshot", "--day", "2026-10-11", "--tz", "UTC", "--db", str(dbp), "--now", str(T2 + 3600)])
    capsys.readouterr()
    call(["social", "brief", "--db", str(dbp), "--as-of", "2026-10-12T01:00:00+00:00", "--tz", "UTC", "--include-fixtures"])
    assert "No supported high-priority observations." in capsys.readouterr().out


def test_nothing_configured_is_not_run(dbp, tmp_path, capsys):
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"schema": D.CONFIG_SCHEMA, "bot_label": "x", "guilds": []}))
    assert D.health(empty, dbp, env={D.TOKEN_ENV: TOKEN})["status"] == "not_configured"
    assert call(["social", "discord-ingest", "--config", str(empty), "--db", str(dbp)]) == 1
    assert json.loads(capsys.readouterr().out)["reason"] == "not_configured"


# ---------- access gates and config ----------

def test_no_token_or_no_consent_means_no_request(dbp):
    out, tr, _ = run(dbp, MAIN, token=None)
    assert tr.calls == [] and all("credentials_missing" in h["errors"][0] for h in out["health"].values())
    c = raw_cfg()
    c["guilds"][0]["consent"] = {}
    out, tr, _ = run(dbp, MAIN, config=D.load_config(c))
    assert tr.calls == [] and all("consent_missing" in h["errors"][0] for h in out["health"].values())
    c = raw_cfg()
    del c["guilds"][0]["server_visibility"]
    out, tr, _ = run(dbp, MAIN, config=D.load_config(c))
    assert tr.calls == [] and all("not_public" in h["errors"][0] for h in out["health"].values())


def test_config_refuses_tokens_invites_self_bots_and_weak_consent():
    base = raw_cfg()
    for bad, match in (({"bot_token": "x"}, "must not hold credentials"), ({"user_token": "x"}, "self-bots are forbidden"),
                       ({"self_bot": True}, "self-bots are forbidden"), ({"note": "join via https://discord.gg/abc"}, "invite"),
                       ({"guilds": [{**base["guilds"][0], "consent": {"basis": "public_invite", "reference": "x"}}]}, "not consent"),
                       ({"guilds": [{**base["guilds"][0], "guild_id": "abc"}]}, "snowflake"),
                       ({"guilds": [base["guilds"][0], base["guilds"][0]]}, "duplicate")):
        with pytest.raises(ValueError, match=match):
            D.load_config({**base, **bad})


def test_user_token_is_refused_after_the_identity_check(dbp):
    e = ex_list()
    f = fixture(e[0], ex("/users/@me", None, 200, {"id": BOT, "username": "someone"}))
    out, tr, _ = run(dbp, f)
    assert len(tr.calls) == 2 and "not_a_bot" in out["health"]["discord_bot:app:memelab-research"]["errors"][0]


def test_channel_of_another_server_is_refused(dbp):
    f = fixture(*preflight(), ch1(guild_id="1080278227353600999"))
    out, tr, _ = run(dbp, f, config=only_c1())
    assert "config_mismatch" in out["health"][CONN(C1)]["errors"][0] and len(tr.calls) == 5


# ---------- rate limits and errors ----------

def test_429_records_retry_after_and_the_next_run_waits(dbp):
    f = fixture(*preflight(), ch1(), ex(f"/channels/{C1}/messages", {"limit": 100}, 429,
                                       {"message": "You are being rate limited.", "retry_after": 30.5, "global": False},
                                       headers={"X-RateLimit-Scope": "user"}))
    out, _, _ = run(dbp, f, config=only_c1())
    assert out["health"][CONN(C1)]["status"] == "RATE_LIMITED"
    reset = q(dbp, "SELECT rate_limit_reset_at FROM social_source_cursors WHERE connector=?", CONN(C1))[0]["rate_limit_reset_at"]
    assert reset == store.to_utc(A_AT) + 30.5
    out, tr, _ = run(dbp, fixture(*preflight()), config=only_c1(), now=reset - 5)
    assert out["health"][CONN(C1)]["status"] == "RATE_LIMITED" and len(tr.calls) == 2


def test_global_429_stops_every_channel(dbp):
    c = raw_cfg()
    c["guilds"][0]["channels"] = [c["guilds"][0]["channels"][0], {"channel_id": C3, "label": "ann"}]
    f = fixture(*preflight(), ex(f"/channels/{C1}", None, 429, {"message": "rl", "retry_after": 2.0, "global": True},
                                 headers={"X-RateLimit-Global": "true", "X-RateLimit-Scope": "global"}))
    out, tr, _ = run(dbp, f, config=D.load_config(c))
    assert len(tr.calls) == 5 and "global rate limit" in out["health"][CONN(C3)]["errors"][0]


def test_exhausted_bucket_waits_for_reset_after(dbp):
    sleeps = []
    hdr = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset-After": "1.25"}
    f = fixture(*preflight(), ch1(), page([m(M[1])], headers=hdr))
    run(dbp, f, config=only_c1(recheck={"enabled": False}), sleeps=sleeps)
    assert sleeps == [1.25]


def test_invalid_request_cap_stops_the_run(dbp):
    c = raw_cfg()
    c["max_invalid_requests_per_run"] = 1
    c["guilds"][0]["channels"] = [c["guilds"][0]["channels"][0], {"channel_id": C3, "label": "ann"}]
    f = fixture(*preflight(), ex(f"/channels/{C1}", None, 403, {"message": "Missing Access", "code": 50001}))
    out, tr, _ = run(dbp, f, config=D.load_config(c))
    assert len(tr.calls) == 5 and "invalid-request cap" in out["health"][CONN(C3)]["errors"][0]


def test_5xx_bounded_retries_then_down(dbp):
    f = fixture(*preflight(), *[ex(f"/channels/{C1}", None, 502, None)] * 3)
    out, tr, _ = run(dbp, f, config=only_c1())
    assert len(tr.calls) == 7 and out["health"][CONN(C1)]["status"] == "DOWN"


def test_401_stops_everything(dbp):
    out, tr, _ = run(dbp, fixture(ex("/applications/@me", None, 401, {"message": "401: Unauthorized", "code": 0})))
    assert len(tr.calls) == 1 and "credentials_rejected" in out["health"]["discord_bot:app:memelab-research"]["errors"][0]


def test_secrets_never_leak(dbp, caplog, capsys):
    f = fixture(*preflight(), *[{"recorded_at": A_AT, "request": {"method": "GET", "path": f"/channels/{C1}", "params": {}},
                                 "raise": "reset while sending Authorization: Bot {secret}"}] * 3)
    with caplog.at_level(logging.INFO, logger="memelab.social.ingest"):
        out, tr, ad = run(dbp, f, config=only_c1())
    blob = json.dumps(out) + caplog.text + all_text(dbp) + repr(ad) + json.dumps(tr.calls) + capsys.readouterr().err
    assert TOKEN not in blob and "fixtureTokenNotRealDoNotLeak" not in blob
    assert "[REDACTED]" in out["health"][CONN(C1)]["errors"][0]
    assert TOKEN not in I.redact(f"Authorization: Bot {TOKEN}") and TOKEN not in I.redact(f"token {TOKEN}")


# ---------- health, CLI, example config ----------

def test_health_states_without_network(dbp, tmp_path, monkeypatch):
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network used")))
    env = {D.TOKEN_ENV: TOKEN}
    assert D.health(tmp_path / "none.json", dbp, env=env)["status"] == "not_configured"
    c = raw_cfg()
    c["guilds"][0]["consent"] = {}
    noc = tmp_path / "noc.json"
    noc.write_text(json.dumps(c))
    assert D.health(noc, dbp, env=env)["status"] == "consent_missing"
    assert D.health(CONFIG, dbp, env={})["status"] == "credentials_missing"
    h = D.health(CONFIG, dbp, env=env)
    assert h["status"] == "ready" and TOKEN not in json.dumps(h) and h["network_calls_made"] == 0
    assert h["live_evidence"]["verdict"].startswith("none") and h["message_content_intent"].startswith("unknown")


def test_cli_fixture_flow_extract_narrative_brief_gateway_and_live_refusal(dbp, capsys, monkeypatch):
    """Source -> storage -> claim -> narrative -> report, on the fixtures, through the real commands."""
    monkeypatch.delenv(D.TOKEN_ENV, raising=False)
    code = call(["social", "discord-ingest", "--config", str(CONFIG), "--fixture", str(MAIN), "--extract", "--bodies", str(BODIES),
                 "--db", str(dbp), "--now", str(T1), "--run-id", "cli_dc"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["mode"] == "fixture" and out["counts"]["created"] == 9 and out["status"] == "PARTIAL"
    assert out["extraction"]["extracted"] == 8 and out["extraction"]["claims"] == 6
    claims = q(dbp, "SELECT c.item_key, a.category, a.tokens_json FROM social_claims c JOIN social_claim_attributes a ON a.claim_id=c.id")
    assert sorted(c["item_key"] for c in claims) == sorted(K(n) for n in (1, 2, 3, 4, 8, 10))
    assert all(json.loads(c["tokens_json"])[0]["contract"] == CA for c in claims)
    call(["social", "narrative-snapshot", "--day", "2026-10-10", "--tz", "UTC", "--db", str(dbp), "--now", str(T1 + 3600)])
    snap = json.loads(capsys.readouterr().out)
    assert snap["summary"]["new"] == [f"ca:solana:{CA}"]
    cl = q(dbp, "SELECT * FROM social_narrative_clusters")[0]
    assert cl["independent_source_count"] == 2          # m1 and m3; reply, forward, bot and webhook add no independence
    call(["social", "brief", "--db", str(dbp), "--as-of", "2026-10-11T01:00:00+00:00", "--tz", "UTC", "--include-fixtures"])
    brief = capsys.readouterr().out
    assert "FIXTURE DEMO" in brief and "Priority: HIGH" in brief and f"https://discord.com/channels/{G}/{C1}/{M[1]}" in brief
    assert "Invented fixture text" not in brief
    code = call(["social", "discord-gateway", "--config", str(CONFIG), "--fixture", str(GATEWAY), "--extract", "--bodies", str(BODIES),
                 "--db", str(dbp), "--now", str(T3)])
    g = json.loads(capsys.readouterr().out)
    assert code == 0 and g["counts"]["created"] == 5 and g["deletion_purge"]["items_purged"] == 1
    call(["social", "sources", "--db", str(dbp)])
    rows = {r["connector"]: r for r in json.loads(capsys.readouterr().out)["connectors"]}
    assert rows["discord_bot"]["status"] == "not_configured"
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network used")))
    assert call(["social", "discord-ingest", "--config", str(CONFIG), "--db", str(dbp)]) == 1
    r = json.loads(capsys.readouterr().out)
    assert r["status"] == "NOT_RUN" and r["reason"] == "credentials_missing" and r["network_calls_made"] == 0
    assert call(["social", "discord-gateway", "--config", str(CONFIG), "--db", str(dbp)]) == 1
    assert json.loads(capsys.readouterr().out)["reason"] == "gateway_transport_not_shipped"


def test_example_config_loads_and_is_off_by_default(dbp):
    ex_cfg = ROOT / "docs" / "social-intelligence" / "discord_bot.example.json"
    c = D.load_config(ex_cfg)
    assert c.require_message_content is True and not any(g.consented for g in c.guilds) and c.backfill_max_pages == 1
    assert D.health(ex_cfg, dbp, env={D.TOKEN_ENV: TOKEN})["status"] == "consent_missing"


def test_permission_algorithm_matches_the_documented_order():
    roles = [{"id": G, "permissions": str(1 << 10)}, {"id": "r1", "permissions": str(1 << 16)}, {"id": "r2", "permissions": "8"}]
    base = dict(guild_id=G, owner_id="owner", roles=roles, member_id="u1")
    p = D.compute_permissions(member_roles=["r1"], overwrites=[], **base)
    assert p & D.PERM_VIEW_CHANNEL and p & D.PERM_READ_HISTORY
    assert D.compute_permissions(member_roles=["r2"], overwrites=[{"id": G, "type": 0, "allow": "0", "deny": str(1 << 10)}],
                                 **base) == D.ALL_PERMISSIONS          # administrator skips overwrites
    ow = [{"id": G, "type": 0, "allow": "0", "deny": str(1 << 10)}, {"id": "r1", "type": 0, "allow": str(1 << 10), "deny": "0"},
          {"id": "u1", "type": 1, "allow": "0", "deny": str(1 << 16)}]
    p = D.compute_permissions(member_roles=["r1"], overwrites=ow, **base)
    assert p & D.PERM_VIEW_CHANNEL and not p & D.PERM_READ_HISTORY
    assert D.compute_permissions(member_roles=[], overwrites=ow, **{**base, "member_id": "owner"}) == D.ALL_PERMISSIONS
    assert D.everyone_can_view(guild_id=G, roles=roles, overwrites=ow) is False
