"""Phase 04: Telegram Bot API adapter. Recorded synthetic exchanges only; no network, fixed clock, temp DB and private folder.

Fixtures: tests/fixtures/social/telegram_bot/ (invented channels, ids and sentences shaped like Bot API responses).
"""
import json
import logging
import sqlite3
import urllib.request
from pathlib import Path

import pytest

from memelab import cli, db
from memelab.social import ingest as I
from memelab.social import schema, store
from memelab.social import telegram_bot as T

ROOT = Path(__file__).resolve().parent.parent
FXD = ROOT / "tests" / "fixtures" / "social" / "telegram_bot"
CONFIG = FXD / "fx_tg_config.json"
MAIN = FXD / "fx_tg_main.json"
SECOND = FXD / "fx_tg_second.json"
ACCESS = FXD / "fx_tg_access.json"
REC = 1791558000.0              # 2026-10-09T15:00:00Z, recorded_at of fx_tg_main.json
T_RUN = 1791561600.0            # 16:00Z
T_SECOND = 1791565200.0 + 3600  # 18:00Z (fx_tg_second recorded 17:00Z)
A, B, C = "-1001000000001", "-1001000000002", "-1001000000003"
CA, CB, CC = (f"telegram_bot:channel:{x}" for x in (A, B, C))
BOT = "telegram_bot:example_lab_bot"
TOKEN = "123456789:AAH-THIS-IS-A-FAKE-TOKEN-0123456789ab"
PARAMS = {"limit": 100, "timeout": 0, "allowed_updates": T.ALLOWED_UPDATES}
K = lambda chat, mid: f"telegram:{chat}_{mid}"


@pytest.fixture()
def dbp(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private" / "p.sqlite"))
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    return p


def cfg(**over):
    c = json.loads(CONFIG.read_text())
    c.update(over)
    return T.load_config(c)


def run(dbp, fixture, config=None, now=T_RUN, token=TOKEN, mode="fixture", run_id=None, **kw):
    tr = fixture if isinstance(fixture, T.FixtureTransport) else T.FixtureTransport(fixture)
    ad = T.TelegramBotAdapter(config or cfg(), tr, token, dbp, run_id=run_id or f"r{now}", mode=mode, clock=lambda: now,
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
    return {"schema": T.FIXTURE_SCHEMA, "exchanges": list(exchanges)}


def ex(method, params, status=200, body=None, at="2026-10-09T15:00:00Z"):
    return {"recorded_at": at, "request": {"method": method, "params": params}, "response": {"status": status, "body": body}}


def updates(*u, params=None, at="2026-10-09T15:00:00Z"):
    return ex("getUpdates", params or PARAMS, body={"ok": True, "result": list(u)}, at=at)


def chan(cid, username="example_alpha_calls"):
    c = {"id": int(cid), "type": "channel", "title": "Example"}
    if username:
        c["username"] = username
    return c


def post(uid, cid, mid, date=REC - 100, kind="channel_post", username="example_alpha_calls", **kw):
    ch = chan(cid, username)
    return {"update_id": uid, kind: {"message_id": mid, "chat": ch, "sender_chat": ch, "date": int(date), **kw}}


def counts(dbp):
    return {t: q(dbp, f"SELECT COUNT(*) n FROM {t}")[0]["n"] for t in
            ("social_items", "social_observations", "social_observation_provenance", "social_item_versions", "social_item_forwards",
             "social_item_refs", "social_item_context")}


def cursor(dbp, connector=BOT, scope="updates"):
    r = q(dbp, "SELECT * FROM social_source_cursors WHERE connector=? AND scope=?", connector, scope)
    return r[0] if r else None


# ---------- the main recorded flow ----------

def test_main_fixture_channel_posts_into_observations(dbp):
    out, tr, ad = run(dbp, MAIN)
    assert out["status"] == "PARTIAL"
    c = out["counts"]
    assert c["created"] == 8 and c["duplicates"] == 1 and c["quarantined"] == 1
    assert ad.dropped == {"service_message": 1, "unapproved_channel": 1, "update_type_not_used": 1}
    assert out["health"][CA]["status"] == "OK"
    assert out["health"][CB]["status"] == "BLOCKED"          # bot removed in the same batch
    assert out["health"][CC]["status"] == "DEGRADED"         # private channel item quarantined
    assert len(tr.calls) == 1 and tr.calls[0]["method"] == "getUpdates" and "offset" not in tr.calls[0]["params"]
    assert cursor(dbp)["newest_id"] == "1014" and cursor(dbp)["last_status"] == "OK"
    it = q(dbp, "SELECT * FROM social_items WHERE item_key=?", K(A, 12))[0]
    assert it["provider_item_id"] == f"{A}_12" and it["account_id"] == f"telegram:id:{A}"
    assert it["original_url"] == "https://t.me/example_alpha_calls/12"
    assert it["published_at"] == REC - 3300 and it["published_at_basis"] == "PROVIDER"
    acc = q(dbp, "SELECT * FROM social_accounts WHERE account_id=?", f"telegram:id:{A}")[0]
    assert acc["handle"] == "example_alpha_calls" and acc["profile_url"] == "https://t.me/example_alpha_calls"


def test_provenance_of_one_event(dbp):
    run(dbp, MAIN)
    eid = q(dbp, "SELECT p.event_id FROM social_observation_provenance p JOIN social_observations o ON o.id=p.observation_id"
                 " WHERE o.item_key=?", K(A, 12))[0]["event_id"]
    assert eid.startswith(f"telegram:bot.{A}_12.v{int(REC - 3300)}.")
    con = sqlite3.connect(dbp)
    con.row_factory = sqlite3.Row
    rec = I.event_record(con, eid)
    con.close()
    p = rec["provenance"]
    assert p["inbound_schema"] == I.INBOUND_SCHEMA_V3 and p["rights_basis"] == "synthetic_fixture"
    assert p["connector"] == CA and p["fetched_at"] == REC and p["provider_published_at"] == REC - 3300
    assert p["freshness"] == "FRESH" and "no history" in p["terms_note"] and "updates=1001-1013" in p["source_ref"]
    assert rec["observation"]["access_mode"] == "fixture" and rec["observation"]["collector"] == "telegram-bot-api/fixture"


def test_text_signature_and_forward_sender_never_stored(dbp):
    run(dbp, MAIN)
    txt = all_text(dbp)
    for s in ("Invented sentence one", "Invented original announcement", "Invented follow-up", "Invented caption",
              "Example Admin", "Invented Person", "7000001", "Invented forwarded remark", "/start", "7000002"):
        assert s not in txt
    obs = q(dbp, "SELECT content_hash FROM social_observations WHERE item_key=? ORDER BY observed_at, id", K(A, 15))
    assert obs[0]["content_hash"] == store.text_hash("Invented caption.")       # caption hashed like text
    v = q(dbp, "SELECT * FROM social_item_versions WHERE item_key=? AND version_kind='ORIGINAL'", K(A, 10))[0]
    assert v["poster_hash"] == store.text_hash("Example Admin")
    assert q(dbp, "SELECT COUNT(*) n FROM social_items WHERE item_key LIKE ?", "telegram:-1001000000099_%")[0]["n"] == 0
    assert q(dbp, "SELECT COUNT(*) n FROM social_items WHERE item_key LIKE ?", "telegram:7000002%")[0]["n"] == 0


def test_forwards_keep_origin_and_are_not_independent_originals(dbp):
    run(dbp, MAIN)
    fw = {r["item_key"]: r for r in q(dbp, "SELECT * FROM social_item_forwards")}
    assert set(fw) == {K(A, 11), K(B, 6), K(A, 15)}
    assert fw[K(A, 11)]["origin_type"] == "channel" and fw[K(A, 11)]["origin_item_key"] == K(B, 5)
    assert fw[K(A, 11)]["origin_chat_id"] == B and fw[K(A, 11)]["origin_message_id"] == "5"
    assert fw[K(A, 11)]["origin_published_at"] == REC - 3500
    assert fw[K(B, 6)]["origin_type"] == "hidden_user" and fw[K(B, 6)]["origin_chat_id"] is None
    assert fw[K(A, 15)]["origin_type"] == "user" and fw[K(A, 15)]["origin_chat_id"] is None
    con = sqlite3.connect(dbp)
    try:
        indep = {k: store.is_independent_original(con, k) for k in (K(A, 10), K(A, 11), K(A, 12), K(A, 13), K(A, 15), K(B, 5), K(B, 6))}
    finally:
        con.close()
    assert indep == {K(A, 10): True, K(A, 11): False, K(A, 12): True, K(A, 13): True, K(A, 15): False, K(B, 5): True, K(B, 6): False}
    # the forward and its original carry the same text hash: one claim, two sightings
    h = lambda k: q(dbp, "SELECT content_hash FROM social_observations WHERE item_key=?", k)[0]["content_hash"]
    assert h(K(A, 11)) == h(K(B, 5))
    ctx = {r["item_key"]: r["reference_type"] for r in q(dbp, "SELECT * FROM social_item_context")}
    assert ctx[K(A, 11)] == "REPOST" and ctx[K(A, 10)] == "ORIGINAL"


def test_reply_context_same_chat_and_external(dbp):
    run(dbp, MAIN)
    refs = {(r["item_key"], r["referenced_item_key"]): r for r in q(dbp, "SELECT * FROM social_item_refs")}
    assert refs[(K(A, 12), K(A, 10))]["ref_type"] == "replied_to" and refs[(K(A, 12), K(A, 10))]["referenced_author_id"] == A
    assert refs[(K(A, 13), K(B, 5))]["referenced_author_id"] == B
    ctx = {r["item_key"]: r["reference_type"] for r in q(dbp, "SELECT * FROM social_item_context")}
    assert ctx[K(A, 12)] == "REPLY" and ctx[K(A, 13)] == "REPLY"


def test_edit_is_a_new_version_and_sighting(dbp):
    run(dbp, MAIN)
    vs = q(dbp, "SELECT * FROM social_item_versions WHERE item_key=? ORDER BY provider_version_at", K(A, 10))
    assert [(v["version_kind"], v["provider_version_at"]) for v in vs] == [("ORIGINAL", REC - 3600), ("EDIT", REC - 1800)]
    assert vs[1]["content_hash"] == store.text_hash("Invented sentence one, corrected.")
    obs = q(dbp, "SELECT content_hash FROM social_observations WHERE item_key=?", K(A, 10))
    assert len({o["content_hash"] for o in obs}) == 2
    assert q(dbp, "SELECT published_at FROM social_items WHERE item_key=?", K(A, 10))[0]["published_at"] == REC - 3600
    con = sqlite3.connect(dbp)
    con.row_factory = sqlite3.Row
    assert store.current_version(con, K(A, 10))["version_kind"] == "EDIT"
    con.close()


def test_out_of_order_edit_before_original_and_readded_bot(dbp):
    run(dbp, MAIN)
    out, tr, _ = run(dbp, SECOND, now=T_SECOND)
    assert tr.calls[0]["params"]["offset"] == 1015                     # cursor 1014 -> offset 1015
    assert out["counts"]["created"] == 2 and out["health"][CA]["status"] == "OK"
    vs = q(dbp, "SELECT version_kind, provider_version_at FROM social_item_versions WHERE item_key=? ORDER BY provider_version_at", K(A, 20))
    assert [v["version_kind"] for v in vs] == ["ORIGINAL", "EDIT"]
    con = sqlite3.connect(dbp)
    con.row_factory = sqlite3.Row
    cur = store.current_version(con, K(A, 20))
    con.close()
    assert cur["version_kind"] == "EDIT" and cur["content_hash"] == store.text_hash("Invented later text, second version.")
    assert cursor(dbp, CB, "membership")["last_status"] == "OK"         # re-added as administrator
    assert cursor(dbp)["newest_id"] == "1017"


def test_out_of_order_update_ids_never_move_the_cursor_back(dbp):
    p2 = {**PARAMS, "limit": 2}
    tr = fixture(updates(post(2005, A, 1), post(2003, A, 2), params=p2),
                 updates(post(2001, A, 3), params={**p2, "offset": 2006}))
    t = T.FixtureTransport(tr)
    run(dbp, t, config=cfg(poll_limit=2))
    assert [c["params"].get("offset") for c in t.calls] == [None, 2006]
    assert cursor(dbp)["newest_id"] == "2005"
    # a later batch that carries only older ids (redelivery) keeps the cursor where it was
    assert q(dbp, "SELECT COUNT(*) n FROM social_items")[0]["n"] == 3


def test_duplicate_updates_and_redelivery_add_nothing(dbp):
    run(dbp, MAIN)
    before = counts(dbp)
    con = sqlite3.connect(dbp)
    con.execute("DELETE FROM social_source_cursors WHERE connector=?", (BOT,))      # Telegram redelivers unconfirmed updates
    con.commit()
    con.close()
    out, _, _ = run(dbp, MAIN, now=T_RUN + 60)
    assert out["counts"]["created"] == 0 and out["counts"]["units_replayed"] == 3
    assert counts(dbp) == before


def test_redelivery_with_a_new_fetch_time_is_deduped_by_event_id(dbp):
    first = fixture(updates(post(3001, A, 7, text="Invented."), at="2026-10-09T15:00:00Z"))
    again = fixture(updates(post(3001, A, 7, text="Invented."), at="2026-10-09T15:05:00Z"))
    run(dbp, first)
    con = sqlite3.connect(dbp)
    con.execute("DELETE FROM social_source_cursors")
    con.commit()
    con.close()
    out, _, _ = run(dbp, again, now=T_RUN + 60)
    assert out["counts"]["duplicates"] == 1 and out["counts"]["created"] == 0
    assert q(dbp, "SELECT COUNT(*) n FROM social_observation_provenance")[0]["n"] == 1


def test_private_channel_quarantined_unapproved_and_dm_dropped(dbp):
    out, _, ad = run(dbp, MAIN)
    qr = q(dbp, "SELECT * FROM social_ingest_quarantine")
    assert len(qr) == 1 and qr[0]["reason_code"] == "NOT_PUBLIC" and qr[0]["connector"] == CC
    assert q(dbp, "SELECT COUNT(*) n FROM social_items WHERE item_key LIKE ?", f"telegram:{C}_%")[0]["n"] == 0
    assert ad.dropped["unapproved_channel"] == 1 and ad.dropped["update_type_not_used"] == 1


def test_inaccessible_message_dropped(dbp):
    run(dbp, fixture(updates(post(4001, A, 9, date=0))))
    assert q(dbp, "SELECT COUNT(*) n FROM social_items")[0]["n"] == 0


# ---------- access, errors, rate limits ----------

def test_access_check_reports_denied_and_not_public(dbp):
    acc = T.check_access(cfg(), T.FixtureTransport(ACCESS), TOKEN, dbp, mode="fixture", clock=lambda: T_RUN)
    assert acc["bot"]["state"] == "OK"
    assert acc["channels"][A]["state"] == "OK" and acc["channels"][A]["member_status"] == "administrator"
    assert acc["channels"][B]["state"] == "access_denied" and acc["channels"][B]["member_status"] == "left"
    assert acc["channels"][C]["state"] == "not_public"
    h = T.health(None, dbp, env={T.TOKEN_ENV: TOKEN}, now=T_RUN, access=acc)
    assert h["status"] == "not_configured"
    h = T.health(CONFIG, dbp, env={T.TOKEN_ENV: TOKEN}, now=T_RUN, access=acc)
    assert h["status"] == "access_denied"
    assert {c["chat_id"]: c["access"] for c in h["channels"]} == {A: "OK", B: "access_denied", C: "not_public"}


def test_access_check_chat_not_found_and_bad_token(dbp):
    f = fixture(ex("getMe", {}, body={"ok": True, "result": {"id": 9000001, "is_bot": True}}),
                ex("getChat", {"chat_id": A}, 400, {"ok": False, "error_code": 400, "description": "Bad Request: chat not found"}),
                ex("getChat", {"chat_id": B}, 403, {"ok": False, "error_code": 403, "description": "Forbidden: bot is not a member of the channel chat"}),
                ex("getChat", {"chat_id": C}, 403, {"ok": False, "error_code": 403, "description": "Forbidden: bot was kicked from the channel chat"}))
    acc = T.check_access(cfg(), T.FixtureTransport(f), TOKEN, dbp, mode="fixture", clock=lambda: T_RUN)
    assert {k: v["state"] for k, v in acc["channels"].items()} == {A: "access_denied", B: "access_denied", C: "access_denied"}
    bad = fixture(ex("getMe", {}, 401, {"ok": False, "error_code": 401, "description": "Unauthorized"}))
    acc = T.check_access(cfg(), T.FixtureTransport(bad), TOKEN, dbp, mode="fixture", clock=lambda: T_RUN)
    assert acc["bot"]["state"] == "credentials_rejected" and acc["channels"] == {}
    assert T.health(CONFIG, dbp, env={T.TOKEN_ENV: TOKEN}, access=acc)["status"] == "access_denied"


@pytest.mark.parametrize("status,desc,expect,access", [
    (401, "Unauthorized", "BLOCKED", "credentials_rejected"),
    (404, "Not Found", "BLOCKED", "credentials_rejected"),
    (403, "Forbidden: bot was blocked", "BLOCKED", "access_denied"),
    (409, "Conflict: can't use getUpdates method while webhook is active; use deleteWebhook to delete the webhook first",
     "BLOCKED", "webhook_conflict"),
    (400, "Bad Request: invalid offset", "DOWN", "error"),
])
def test_http_errors_map_to_status_and_hold_cursor(dbp, status, desc, expect, access):
    out, _, _ = run(dbp, fixture(ex("getUpdates", PARAMS, status, {"ok": False, "error_code": status, "description": desc})))
    h = out["health"][BOT]
    assert h["status"] == expect and h["errors"][0].startswith(access)
    assert cursor(dbp)["newest_id"] is None


def test_429_retry_after_stops_and_skips_until_reset(dbp):
    body = {"ok": False, "error_code": 429, "description": "Too Many Requests: retry after 120", "parameters": {"retry_after": 120}}
    out, _, _ = run(dbp, fixture(ex("getUpdates", PARAMS, 429, body)))
    assert out["health"][BOT]["status"] == "RATE_LIMITED" and "retry after 120" in out["health"][BOT]["errors"][0]
    assert cursor(dbp)["rate_limit_reset_at"] == REC + 120
    out, tr, _ = run(dbp, fixture(), now=REC + 60)               # before the reset: no call at all
    assert tr.calls == [] and out["health"][BOT]["status"] == "RATE_LIMITED"
    out, tr, _ = run(dbp, fixture(updates(post(5001, A, 1))), now=REC + 200)
    assert len(tr.calls) == 1 and out["counts"]["created"] == 1


def test_5xx_bounded_retries_then_down(dbp):
    e = ex("getUpdates", PARAMS, 502, None)
    out, tr, _ = run(dbp, fixture(e, e, e))
    assert len(tr.calls) == 3 and out["health"][BOT]["status"] == "DOWN" and out["status"] == "FAILED"
    assert cursor(dbp)["last_status"] == "DOWN"


def test_5xx_then_success(dbp):
    out, tr, _ = run(dbp, fixture(ex("getUpdates", PARAMS, 503, None), updates(post(5101, A, 1))))
    assert len(tr.calls) == 2 and out["counts"]["created"] == 1


def test_paging_until_short_batch_and_poll_cap(dbp):
    f = fixture(updates(post(6001, A, 1), post(6002, A, 2)),
                updates(post(6003, A, 3), post(6004, A, 4), params={**PARAMS, "limit": 2, "offset": 6003}))
    f["exchanges"][0]["request"]["params"] = {**PARAMS, "limit": 2}
    out, tr, _ = run(dbp, f, config=cfg(poll_limit=2, max_polls_per_run=2))
    assert [c["params"].get("offset") for c in tr.calls] == [None, 6003]
    assert out["counts"]["created"] == 4 and cursor(dbp)["newest_id"] == "6004"


def test_empty_poll_records_bot_health(dbp):
    out, _, _ = run(dbp, fixture(updates()))
    assert out["health"][BOT]["status"] == "OK" and cursor(dbp)["last_success_at"] == T_RUN


def test_gap_warning_after_24_hours(dbp):
    run(dbp, fixture(updates(post(7001, A, 1))))
    later = T_RUN + 30 * 3600
    out, _, _ = run(dbp, fixture(updates(params={**PARAMS, "offset": 7002})), now=later)
    assert out["health"][BOT]["status"] == "DEGRADED" and "gap" in out["health"][BOT]["errors"][0]
    h = T.health(CONFIG, dbp, env={}, now=later + 3600 * 30)
    assert h["update_cursor"]["gap_risk"] is True


# ---------- interrupted ingest ----------

def _crash_once(connector, after_index, exc=RuntimeError):
    state = {"done": False}

    def hook(unit, next_index):
        if not state["done"] and unit.connector == connector and next_index >= after_index:
            state["done"] = True
            raise exc("simulated crash between batches")
    return hook


def test_crash_between_batches_holds_offset_then_resumes(dbp, tmp_path, monkeypatch):
    out, _, _ = run(dbp, MAIN, batch_size=2, hooks={"after_batch": _crash_once(CA, 2)})
    assert out["health"][CA]["status"] == "DOWN"
    assert cursor(dbp)["newest_id"] is None and cursor(dbp)["last_status"] == "PARTIAL"     # updates stay unconfirmed
    cp = q(dbp, "SELECT * FROM social_ingest_checkpoints WHERE connector=?", CA)[0]
    assert cp["status"] == "IN_PROGRESS" and cp["next_index"] == 2
    out2, tr, _ = run(dbp, MAIN, now=T_RUN + 60, batch_size=2)          # Telegram sends the same batch again
    assert "offset" not in tr.calls[0]["params"] and cursor(dbp)["newest_id"] == "1014"
    assert q(dbp, "SELECT status FROM social_ingest_checkpoints WHERE connector=?", CA)[0]["status"] == "COMPLETE"
    clean = tmp_path / "clean.sqlite"
    db.init_db(clean)
    run(clean, MAIN, batch_size=2)
    assert counts(dbp) == counts(clean)


def test_process_killed_mid_ingest_resumes_without_duplicates(dbp, tmp_path):
    with pytest.raises(KeyboardInterrupt):
        run(dbp, MAIN, batch_size=2, hooks={"after_batch": _crash_once(CA, 4, KeyboardInterrupt)})
    assert cursor(dbp) is None or cursor(dbp)["newest_id"] is None
    assert q(dbp, "SELECT status FROM social_ingest_runs")[0]["status"] == "RUNNING"
    run(dbp, MAIN, now=T_RUN + 60, batch_size=2)
    clean = tmp_path / "clean.sqlite"
    db.init_db(clean)
    run(clean, MAIN, batch_size=2)
    assert counts(dbp) == counts(clean) and cursor(dbp)["newest_id"] == "1014"


def test_item_budget_stop_holds_offset(dbp):
    out, _, _ = run(dbp, MAIN, budget=I.Budget(max_items=3))
    assert out["counts"]["budget_stopped"] >= 1 and cursor(dbp)["newest_id"] is None
    run(dbp, MAIN, now=T_RUN + 60)
    assert cursor(dbp)["newest_id"] == "1014" and q(dbp, "SELECT COUNT(*) n FROM social_item_versions")[0]["n"] == 8


# ---------- credentials and secrets ----------

def test_credentials_missing_no_request(dbp):
    out, tr, _ = run(dbp, MAIN, token=None)
    assert tr.calls == [] and out["health"][BOT]["status"] == "BLOCKED"
    assert out["health"][BOT]["errors"][0].startswith("credentials_missing")


def test_token_never_leaks(dbp, caplog, capsys):
    caplog.set_level(logging.INFO, logger="memelab.social.ingest")
    boom = {"recorded_at": "2026-10-09T15:00:00Z", "request": {"method": "getUpdates", "params": PARAMS},
            "raise": "connection reset for https://api.telegram.org/bot{token}/getUpdates"}
    out, _, ad = run(dbp, fixture(boom, boom, boom))
    blob = json.dumps(out) + caplog.text + capsys.readouterr().err + all_text(dbp) + repr(ad)
    assert TOKEN not in blob and TOKEN.split(":")[1] not in blob
    assert "[REDACTED]" in out["health"][BOT]["errors"][0]
    assert TOKEN not in I.redact(f"GET https://api.telegram.org/bot{TOKEN}/getMe")


def test_config_refuses_credentials_and_bad_channels():
    base = json.loads(CONFIG.read_text())
    with pytest.raises(ValueError, match="credentials"):
        T.load_config({**base, "bot_token": "x"})
    with pytest.raises(ValueError, match="credentials"):
        T.load_config({**base, "channels": [{**base["channels"][0], "secret_token": "x"}]})
    with pytest.raises(ValueError, match="chat_id"):
        T.load_config({**base, "channels": [{"chat_id": "12345", "approval": "own_channel"}]})
    with pytest.raises(ValueError, match="approval"):
        T.load_config({**base, "channels": [{"chat_id": A, "username": "example_alpha_calls"}]})
    with pytest.raises(ValueError, match="duplicate"):
        T.load_config({**base, "channels": [base["channels"][0], base["channels"][0]]})
    with pytest.raises(ValueError, match="schema"):
        T.load_config({**base, "schema": "x"})


def test_health_states_without_network(dbp, tmp_path):
    h = T.health(CONFIG, dbp, env={}, now=T_RUN)
    assert h["status"] == "credentials_missing" and h["network_calls_made"] == 0
    assert h["live_evidence"]["requests"] == 0 and h["live_evidence"]["verdict"].startswith("none")
    assert T.health(tmp_path / "missing.json", dbp, env={T.TOKEN_ENV: TOKEN})["status"] == "not_configured"
    assert T.health(CONFIG, dbp, env={T.TOKEN_ENV: TOKEN})["status"] == "access_unverified"
    con = sqlite3.connect(dbp)
    for cid in (A, B, C):
        T._save_cursor(con, f"telegram_bot:channel:{cid}", "membership", T_RUN, last_status="OK")
    con.close()
    assert T.health(CONFIG, dbp, env={T.TOKEN_ENV: TOKEN})["status"] == "ready"
    assert T.health(CONFIG, dbp, env={T.TOKEN_ENV: TOKEN, T.SECRET_ENV: "ok_secret-1"})["webhook_secret"] == "present"
    assert T.health(CONFIG, dbp, env={T.TOKEN_ENV: TOKEN, T.SECRET_ENV: "bad secret!"})["webhook_secret"] == "missing"


def test_fixture_requests_are_never_live_evidence(dbp):
    run(dbp, MAIN)
    h = T.health(CONFIG, dbp, env={T.TOKEN_ENV: TOKEN})
    assert h["live_evidence"]["requests"] == 0
    assert q(dbp, "SELECT mode FROM social_api_spend WHERE connector LIKE 'telegram_bot:%'") == [{"mode": "fixture"}]


# ---------- webhook ----------

SECRET = "invented_secret-123"


def _wh(cfg_, spool, upd, secret_header=SECRET, now=REC, secret=SECRET):
    raw = upd if isinstance(upd, bytes) else json.dumps(upd).encode()
    hdr = {} if secret_header is None else {"X-Telegram-Bot-Api-Secret-Token": secret_header}
    return T.webhook_receive(hdr, raw, cfg=cfg_, secret=secret, spool=spool, now=now, mode="fixture")


def test_webhook_secret_validation_and_spool_without_text(dbp, tmp_path):
    c, spool = cfg(), tmp_path / "spool"
    u = post(8001, A, 30, text="Invented webhook sentence.", author_signature="Example Admin")
    assert _wh(c, spool, u, secret=None)[0] == 503
    assert _wh(c, spool, u, secret_header=None)[0] == 401
    assert _wh(c, spool, u, secret_header="wrong")[0] == 401
    assert not spool.exists()
    assert _wh(c, spool, b"{not json")[0] == 400
    assert _wh(c, spool, {"no": "id"})[0] == 400
    assert _wh(c, spool, b"x" * (T.WEBHOOK_MAX_BYTES + 1))[0] == 413
    assert _wh(c, spool, u) == (200, {"stored": True})
    assert _wh(c, spool, u) == (200, {"stored": False, "duplicate": True})        # Telegram retry
    assert _wh(c, spool, post(8002, "-1001000000099", 1, username="example_unlisted", text="x"))[1]["dropped"] == "unapproved_channel"
    files = list(spool.glob("*.json"))
    assert len(files) == 1
    raw = files[0].read_text()
    assert "Invented webhook sentence" not in raw and "Example Admin" not in raw and store.text_hash("Invented webhook sentence.") in raw


def test_webhook_spool_ingest_out_of_order_and_idempotent(dbp, tmp_path):
    c, spool = cfg(), tmp_path / "spool"
    edit = post(8102, A, 31, date=REC - 500, kind="edited_channel_post", edit_date=int(REC - 100), text="Invented v2.")
    orig = post(8101, A, 31, date=REC - 500, text="Invented v1.")
    assert _wh(c, spool, edit, now=REC - 90)[0] == 200                 # the edit arrives first
    assert _wh(c, spool, orig, now=REC - 80)[0] == 200
    ad = T.WebhookSpoolAdapter(c, spool, dbp, run_id="wh1", clock=lambda: REC)
    out = I.ingest(ad, dbp, now=REC, run_id="wh1")
    assert out["counts"]["created"] == 2 and ad.files_done == 2 and not list(spool.glob("*.json"))
    con = sqlite3.connect(dbp)
    con.row_factory = sqlite3.Row
    assert store.current_version(con, K(A, 31))["content_hash"] == store.text_hash("Invented v2.")
    con.close()
    assert _wh(c, spool, orig, now=REC)[1] == {"stored": False, "duplicate": True}   # already processed
    out = I.ingest(T.WebhookSpoolAdapter(c, spool, dbp, run_id="wh2", clock=lambda: REC), dbp, now=REC + 10, run_id="wh2")
    assert out["counts"]["created"] == 0
    rb = q(dbp, "SELECT rights_basis, connector FROM social_observation_provenance")
    assert {r["rights_basis"] for r in rb} == {"synthetic_fixture"} and {r["connector"] for r in rb} == {CA}
    assert T.purge_spool(spool, 30, now=REC + 31 * 86400 + 10**10) == 2


def test_webhook_membership_removal_blocks_channel(dbp, tmp_path):
    c, spool = cfg(), tmp_path / "spool"
    m = {"update_id": 8201, "my_chat_member": {"chat": chan(B, "example_beta_news"), "date": int(REC),
                                               "new_chat_member": {"status": "kicked", "user": {"id": 1, "is_bot": True}}}}
    assert _wh(c, spool, m)[0] == 200
    out = I.ingest(T.WebhookSpoolAdapter(c, spool, dbp, run_id="wh3", clock=lambda: REC), dbp, now=REC, run_id="wh3")
    assert out["health"][CB]["status"] == "BLOCKED" and cursor(dbp, CB, "membership")["last_status"] == "access_denied"


# ---------- schema ----------

def test_inbound_v2_ignores_forward_and_version_keys(dbp):
    unit_body = {"schema": I.INBOUND_SCHEMA_V2, "fetched_at": "2026-10-09T15:00:00Z",
                 "source": {"platform": "telegram", "access_mode": "fixture", "collector": "t", "rights_basis": "synthetic_fixture",
                            "visibility": "PUBLIC"},
                 "items": [{"provider_item_id": f"{A}_99", "forward": {"origin_type": "channel"}, "version": {"kind": "EDIT"}}]}

    class One:
        name = "one"

        def units(self, budget):
            yield I.SourceUnit("one", "telegram", "one#1", "OK", I.canonical_sha(unit_body), unit_body)
    I.ingest(One(), dbp, now=T_RUN, run_id="v2")
    prov = q(dbp, "SELECT ignored_fields FROM social_observation_provenance")[0]
    assert json.loads(prov["ignored_fields"]) == ["forward", "version"]
    assert counts(dbp)["social_item_forwards"] == 0 and counts(dbp)["social_item_versions"] == 0


def test_v3_forward_rejects_user_ids(dbp):
    errs = []
    I._validate_forward({"origin_type": "user", "origin_chat_id": "7000001"}, errs)
    assert errs == ["forward: a user origin carries no ids"]


def test_migration_4_rolls_back_cleanly(tmp_path):
    p = tmp_path / "m.sqlite"
    db.init_db(p)
    con = sqlite3.connect(p)
    above_3 = [v for v in schema.ALL_VERSIONS if v > 3]      # 4 and anything added after it (Phase 05: 5)
    assert schema.rollback(con, target=3) == above_3[::-1]
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "social_item_forwards" not in names and "social_item_versions" not in names and "social_item_context" in names
    assert schema.migrate(con) == above_3
    con.close()


# ---------- CLI ----------

def test_cli_fixture_demo_and_no_false_live_claim(dbp, capsys, monkeypatch):
    monkeypatch.delenv(T.TOKEN_ENV, raising=False)

    def no_network(*a, **k):
        raise AssertionError("network call attempted")
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "tg-ingest", "--config", str(CONFIG), "--db", str(dbp)])
    assert e.value.code == 1
    out = json.loads(capsys.readouterr().out)
    assert out == {"network_calls_made": 0, "reason": "credentials_missing", "status": "NOT_RUN",
                   "next_step": out["next_step"]} and "BotFather" in out["next_step"]
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "tg-ingest", "--config", str(CONFIG), "--fixture", str(MAIN), "--db", str(dbp), "--now", str(T_RUN)])
    assert e.value.code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["mode"] == "fixture" and out["counts"]["created"] == 8 and out["requests_made"] == 1
    eid = q(dbp, "SELECT event_id FROM social_observation_provenance ORDER BY event_id LIMIT 1")[0]["event_id"]
    cli.main(["social", "status", "--db", str(dbp), "--event", eid])
    rec = json.loads(capsys.readouterr().out)
    assert rec["provenance"]["rights_basis"] == "synthetic_fixture" and rec["observation"]["access_mode"] == "fixture"
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "tg-health", "--config", str(CONFIG), "--db", str(dbp)])
    assert e.value.code == 1
    h = json.loads(capsys.readouterr().out)
    assert h["status"] == "credentials_missing" and h["live_evidence"]["requests"] == 0
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "tg-health", "--config", str(CONFIG), "--db", str(dbp), "--check-access", "--fixture", str(ACCESS)])
    h = json.loads(capsys.readouterr().out)
    assert {c["chat_id"]: c["access"] for c in h["channels"]}[B] == "access_denied"


def test_example_config_loads():
    c = T.load_config(ROOT / "docs" / "social-intelligence" / "telegram_bot.example.json")
    assert c.channels and all(ch.approval in T.APPROVALS for ch in c.channels)
