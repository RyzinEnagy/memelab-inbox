"""Phase 15: research-only alerts. Fixed clock, temp state files, fake transports, no network."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from memelab.social import alerts_cli as ACLI
from memelab.social import alerts_core as AC
from memelab.social import alerts_engine as AE
from memelab.social import alerts_schedule as AS
from memelab.social import alerts_transport as AT

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "social" / "alerts"
SPEC_PATH = "tests/fixtures/social/alerts/alerts_day.json"
T0 = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc).timestamp()   # 08:00 EDT
H = 3600.0
CONTRACT = "B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY"


# ---------- builders ----------

def who(handle, role="INDEPENDENT_ORIGINAL", trader=None, kind="UNKNOWN"):
    return {"display": f"{handle} (x)", "source_id": f"x:id:{handle}", "trader": trader, "role": role, "account_kind": kind,
            "url": f"https://example.invalid/x/{handle}"}


def item(key="ca:solana:" + CONTRACT, *, ind=3, last=None, people=None, chron=None, liq="REPORTED", changes=None, mentions=4,
         status="ok", fresh="FRESH", contract=CONTRACT, kind="CONTRACT", repeats=0):
    return {"item_id": key, "kind": kind, "label": f"FXCAT on solana ({contract})" if kind == "CONTRACT" else "theme fx",
            "symbol": "FXCAT" if kind == "CONTRACT" else None, "chain": "solana" if contract else None, "contract": contract,
            "times": {"last_observed_at": T0 - H if last is None else last},
            "freshness": {"status": fresh, "confidence": "MODERATE"},
            "independence": {"independent_sources": ind, "status": status, "repeats": repeats},
            "who": people if people is not None else [who("fx_a", trader="fx_trader_a"), who("fx_b", trader="fx_trader_b"), who("fx_c")],
            "links": [{"url": "https://example.invalid/x/fx_a", "who": "fx_a (x)", "role": "INDEPENDENT_ORIGINAL"}],
            "chronology": chron or [], "liquidity": {"status": liq, "facts": []}, "digest": {"changes": changes or []},
            "activity": {"window_mentions": mentions}, "is_fixture": False,
            "provenance": {"narrative_run_id": 7, "cluster_key": key, "claims": [1, 2], "chronology_runs": [], "market_fact_ids": []}}


def feed(items, *, snap=1, as_of=T0, fresh="FRESH", fixture=False):
    return {"schema": "memelab.social.feed/1", "as_of": as_of, "feed_sha256": f"sha{snap}", "fixture": fixture,
            "availability": {"status": "AVAILABLE"},
            "data_freshness": {"status": fresh, "snapshot_run_id": snap, "snapshot_window": f"day{snap}"}, "items": items}


def corr(at, attribution="LINKED", flag="DISCLOSED_POSITION_CONSISTENT"):
    return {"flag": flag, "category": "CORROBORATION", "bucket": "INFERENCE", "attribution": attribution, "order_status": "CONFIDENT",
            "at": at, "source_id": "fx_trader_a", "rule": "chrono.x.v1", "run_id": 3}


def risk(at, flag="SALE_DURING_PROMOTION"):
    return {"flag": flag, "category": "RISK", "bucket": "HEURISTIC", "attribution": "CLAIMED", "order_status": "CONFIDENT",
            "at": at, "source_id": "fx_trader_a", "rule": "chrono.y.v1", "run_id": 4}


class FakeTransport:
    remote = True

    def __init__(self, name="telegram", results=None):
        self.name = name
        self.results = list(results or [])
        self.sent = []

    def destination(self):
        return "chat-123"

    def send(self, alert_id, text, *, preview):
        if preview:
            return AT.Result(False, error="dry run: not sent")
        self.sent.append((alert_id, text))
        return self.results.pop(0) if self.results else AT.Result(True)


@pytest.fixture
def con(tmp_path):
    c = AE.connect(tmp_path / "state.sqlite")
    yield c
    c.close()


@pytest.fixture
def policy():
    return AC.make_policy({"policies": {"conversation_growth": {"min_mentions": 10}}})


def sink(tmp_path):
    return AT.FileSink(tmp_path / "outbox")


def ledger(con):
    return [dict(r) for r in con.execute("SELECT alert_id, transport, attempt, status, error FROM alert_deliveries ORDER BY delivery_id")]


# ---------- the prompt's list ----------

def test_fixture_alert_deduped_second_run_and_sample_reproduced():
    md = ACLI.demo_markdown(SPEC_PATH)
    assert md == (FIX / "sample_run.md").read_text()
    assert md.count("FIXTURE DEMO") >= 4
    run1, run2 = md.split("## Run 2")[0], md.split("## Run 2")[1].split("## Delivery state")[0]
    assert "new alerts 4" in run1 and "new alerts 0, deduped 4" in run2
    assert "Messages confirmed delivered to a device (telegram or email): 0" in md
    assert "Nothing has been sent to a device" in md


def test_alert_fixture_spec_matches_its_builder():
    sys.path.insert(0, str(FIX))
    try:
        import make_alerts
        assert json.loads((FIX / "alerts_day.json").read_text()) == json.loads(json.dumps(make_alerts.build(), sort_keys=True))
    finally:
        sys.path.remove(str(FIX))


def test_duplicate_alert_across_retries_and_new_snapshots(con, policy, tmp_path):
    f1 = feed([item(chron=[risk(T0 - 2 * H)])], snap=1)
    tg = FakeTransport()
    r1 = AE.run(con, feed=f1, policy=policy, mode="send", now=T0, transports=[sink(tmp_path), tg])
    assert len(r1["evaluation"]["new"]) == 2          # convergence + risk
    # the same evidence in the next snapshot, re-run twice, adds nothing and sends nothing
    for k, snap in enumerate((2, 3)):
        r = AE.run(con, feed=feed([item(chron=[risk(T0 - 2 * H)])], snap=snap), policy=policy, mode="send", now=T0 + (k + 2) * H,
                   transports=[sink(tmp_path), tg])
        assert r["evaluation"]["new"] == [] and r["evaluation"]["deduped"] == 2
    assert len(tg.sent) == 2


def test_interrupted_send_is_never_resent(con, policy, tmp_path):
    AE.run(con, feed=feed([item()], snap=1), policy=policy, mode="send", now=T0, transports=[sink(tmp_path)])
    aid = con.execute("SELECT alert_id FROM alert_events").fetchone()[0]
    # simulate a run that wrote 'attempted' for telegram and died before recording the outcome
    con.execute("UPDATE alert_events SET status='PENDING', transports_json=? WHERE alert_id=?", (json.dumps(["file", "telegram"]), aid))
    con.execute("INSERT INTO alert_deliveries(alert_id, mode, transport, attempt, status, started_at) VALUES (?,?,?,?,?,?)",
                (aid, "send", "telegram", 1, "attempted", T0))
    con.commit()
    tg = FakeTransport()
    AE.run(con, feed=feed([item()], snap=1), policy=policy, mode="send", now=T0 + 2 * H, transports=[sink(tmp_path), tg])
    assert tg.sent == []
    st = [d for d in ledger(con) if d["transport"] == "telegram"]
    assert [d["status"] for d in st] == ["outcome_unknown"]
    assert "not resent" in AE.render_state(AE.state_view(con))


def test_cooldown_blocks_new_evidence_until_it_expires_or_is_reset(con, policy, tmp_path):
    p3 = [who("fx_a", trader="t_a"), who("fx_b", trader="t_b"), who("fx_c")]
    AE.run(con, feed=feed([item(people=p3)], snap=1), policy=policy, mode="send", now=T0, transports=[sink(tmp_path)])
    p4 = p3 + [who("fx_d", trader="t_d")]           # new reputable source: new dedupe key, same cooldown key
    r = AE.run(con, feed=feed([item(people=p4, ind=4, last=T0 + 2 * H)], snap=2), policy=policy, mode="send", now=T0 + 3 * H,
               transports=[sink(tmp_path)])
    assert r["evaluation"]["new"] == [] and [s["reason_code"] for s in r["evaluation"]["suppressed"]] == ["cooldown"]
    # after the 12 h cooldown the same candidate goes out
    r = AE.run(con, feed=feed([item(people=p4, ind=4, last=T0 + 12 * H)], snap=3), policy=policy, mode="send", now=T0 + 13 * H,
               transports=[sink(tmp_path)])
    assert len(r["evaluation"]["new"]) == 1
    # a manual reset lets the next new evidence through inside the cooldown
    p5 = p4 + [who("fx_e", trader="t_e")]
    blocked = AE.run(con, feed=feed([item(people=p5, ind=5, last=T0 + 14 * H)], snap=4), policy=policy, mode="send", now=T0 + 15 * H,
                     transports=[sink(tmp_path)])
    assert blocked["evaluation"]["new"] == []
    AE.reset_cooldown(con, "send", f"convergence|ca:solana:{CONTRACT}", T0 + 15.5 * H, "test")
    p6 = p5 + [who("fx_f", trader="t_f")]
    r = AE.run(con, feed=feed([item(people=p6, ind=6, last=T0 + 16 * H)], snap=5), policy=policy, mode="send", now=T0 + 17 * H,
               transports=[sink(tmp_path)])
    assert len(r["evaluation"]["new"]) == 1


def test_hundred_reposts_without_independent_corroboration_raise_nothing(con, policy, tmp_path):
    people = [who("fx_orig", trader="t_o")] + [who(f"fx_rp{i}", role="AMPLIFIER") for i in range(100)]
    key = "ca:solana:" + CONTRACT
    for snap, m in ((1, 2), (2, 3), (3, 2)):
        AE.run(con, feed=feed([item(ind=1, mentions=m, people=people[:1])], snap=snap), policy=policy, mode="send",
               now=T0 + snap * 2 * H, transports=[sink(tmp_path)])
    r = AE.run(con, feed=feed([item(ind=1, mentions=101, repeats=100, people=people)], snap=4), policy=policy, mode="send",
               now=T0 + 10 * H, transports=[sink(tmp_path)])
    assert r["evaluation"]["new"] == []
    codes = {(s["policy"], s["reason_code"]) for s in r["evaluation"]["suppressed"]}
    assert ("conversation_growth", "repetition_only") in codes
    assert con.execute("SELECT COUNT(*) FROM alert_events").fetchone()[0] == 0
    assert key


def test_growth_against_baseline_alerts_with_independent_sources(con, policy, tmp_path):
    for snap, m in ((1, 3), (2, 4), (3, 2)):
        AE.run(con, feed=feed([item(ind=1, mentions=m, people=[who("fx_a")])], snap=snap), policy=policy, mode="dry_run",
               now=T0 + snap * 2 * H, transports=[sink(tmp_path)])
    r = AE.run(con, feed=feed([item(ind=3, mentions=30, people=[who("fx_a"), who("fx_b"), who("fx_c")], last=T0 + 9 * H)], snap=4),
               policy=policy, mode="dry_run", now=T0 + 10 * H, transports=[sink(tmp_path)])
    pols = [json.loads(x[0])["policy"] for x in con.execute("SELECT alert_json FROM alert_events WHERE alert_id IN (%s)" % ",".join(map(str, r["evaluation"]["new"])))]
    assert pols == ["conversation_growth"]
    a = json.loads(con.execute("SELECT alert_json FROM alert_events").fetchone()[0])
    assert a["evidence"]["baseline_median"] == 3 and a["evidence"]["ratio"] == 10.0 and a["bucket"] == "HEURISTIC"


def test_stale_wallet_event_is_suppressed_and_fresh_linked_one_alerts(policy):
    f = feed([item(people=[who("fx_a")], ind=1, chron=[corr(T0 - 30 * H), corr(T0 - H, flag="FRESH_ONE"), corr(T0 - H, attribution="CLAIMED", flag="C")])])
    cands, supp = AC.candidates(f, policy, now=T0)
    assert [c["evidence"]["flag"] for c in cands if c["policy"] == "wallet_corroboration"] == ["FRESH_ONE"]
    codes = sorted(s["reason_code"] for s in supp if s["policy"] == "wallet_corroboration")
    assert codes == ["stale_event", "unverified_wallet"]


def test_repeated_schedule_slot_after_restart_is_a_no_op(con, policy, tmp_path):
    tg = FakeTransport()
    slot = ("daily", "2026-10-13")
    r1 = AE.run(con, feed=feed([item()], snap=1), policy=policy, mode="send", now=T0, transports=[sink(tmp_path), tg], slot=slot)
    assert r1["outcome"] == "evaluated"
    for k in range(3):   # the scheduler fires again, or the process restarts and re-runs the same slot
        r = AE.run(con, feed=feed([item()], snap=2 + k), policy=policy, mode="send", now=T0 + (k + 2) * H, transports=[sink(tmp_path), tg], slot=slot)
        assert r["outcome"] == "slot_done"
    assert len(tg.sent) == 1
    # a slot left half done by a crash is skipped inside its lease and taken over after it
    con.execute("INSERT INTO alert_slots(template, slot_key, mode, started_at) VALUES ('daily','2026-10-14','send',?)", (T0 + 24 * H,))
    con.commit()
    assert AE.run(con, feed=feed([item()], snap=9), policy=policy, mode="send", now=T0 + 24.5 * H, transports=[sink(tmp_path)],
                  slot=("daily", "2026-10-14"))["outcome"] == "slot_in_progress"
    assert AE.run(con, feed=feed([item()], snap=9), policy=policy, mode="send", now=T0 + 27 * H, transports=[sink(tmp_path)],
                  slot=("daily", "2026-10-14"))["outcome"] == "evaluated"


def test_missing_token_blocks_token_specific_alerts(policy):
    theme = item(key="tag:fx", kind="THEME", contract=None, chron=[corr(T0 - H)], liq="NOT_A_TOKEN",
                 changes=[{"who": "fx_a (x)", "trader": "t", "source_id": "x:id:fx_a", "before": {"stance": "positive"},
                           "after": {"stance": "negative"}, "after_at": T0 - H, "basis": "inside this snapshot"}])
    unreadable = item(key="ca:solana:bad", contract=None, chron=[risk(T0 - H)])
    cands, supp = AC.candidates(feed([theme, unreadable]), policy, now=T0)
    assert all(c["policy"] == "convergence" for c in cands)
    missing = sorted((s["policy"], s["item_id"]) for s in supp if s["reason_code"] == "missing_token")
    assert ("wallet_corroboration", "tag:fx") in missing and ("stance_switch", "tag:fx") in missing and ("risk", "ca:solana:bad") in missing


def test_notification_transport_failure_retry_and_honest_state(con, policy, tmp_path, monkeypatch):
    monkeypatch.setenv(AT.TELEGRAM_TOKEN_ENV, "123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    tg = FakeTransport(results=[AT.Result(False, retryable=True, error="HTTP 502 bad gateway"),
                                AT.Result(False, retryable=True, error="HTTP 429 slow down", retry_after=4000),
                                AT.Result(True)])
    ts = [sink(tmp_path), tg]
    AE.run(con, feed=feed([item(people=[who("fx_a")], ind=1, liq="NO_SELL_ROUTE")]), policy=policy, mode="send", now=T0, transports=ts)
    st = AE.render_state(AE.state_view(con))
    assert "telegram attempt 1: failed" in st and "confirmed delivered to a device (telegram or email): 0" in st
    assert "file attempt 1: succeeded: written to the local outbox file, not sent to any device" in st
    AE.run(con, feed=feed([item(people=[who("fx_a")], ind=1, liq="NO_SELL_ROUTE")]), policy=policy, mode="send", now=T0 + 60, transports=ts)
    assert len(tg.sent) == 1                                    # inside the backoff: no new attempt
    AE.run(con, feed=None, policy=policy, mode="send", now=T0 + 400, transports=ts)
    assert len(tg.sent) == 2                                    # 429 with retry_after 4000 s
    AE.run(con, feed=None, policy=policy, mode="send", now=T0 + 400 + 1900, transports=ts)
    assert len(tg.sent) == 2
    AE.run(con, feed=None, policy=policy, mode="send", now=T0 + 400 + 4100, transports=ts)
    assert len(tg.sent) == 3
    assert [d["status"] for d in ledger(con) if d["transport"] == "telegram"] == ["failed", "failed", "succeeded"]
    assert con.execute("SELECT status FROM alert_events").fetchone()[0] == "COMPLETE"
    # a permanent error is not retried
    tg2 = FakeTransport(results=[AT.Result(False, retryable=False, error="HTTP 401 Unauthorized")])
    AE.run(con, feed=feed([item(people=[who("fx_a")], ind=1, chron=[risk(T0 + 8 * H)], last=T0 + 9 * H)], snap=2), policy=policy, mode="send",
           now=T0 + 10 * H, transports=[sink(tmp_path), tg2])
    AE.run(con, feed=None, policy=policy, mode="send", now=T0 + 20 * H, transports=[sink(tmp_path), tg2])
    assert len(tg2.sent) == 1


def test_telegram_transport_maps_responses_and_redacts_the_token():
    token = "123456789:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
    calls = []

    def http(url, body):
        calls.append((url, body))
        return 401, {"ok": False, "description": f"Unauthorized for {url}"}
    r = AT.TelegramTransport(token, "42", http=http).send(1, "hello", preview=False)
    assert not r.ok and not r.retryable and token not in r.error and "REDACTED" in r.error
    assert AT.TelegramTransport(token, "42", http=lambda u, b: (429, {"ok": False, "parameters": {"retry_after": 30}})).send(1, "x", preview=False).retry_after == 30

    def boom(url, body):
        raise OSError(f"connection reset talking to {url}")
    r = AT.TelegramTransport(token, "42", http=boom).send(1, "x", preview=False)
    assert r.retryable and token not in r.error
    assert AT.TelegramTransport(token, "42", http=lambda u, b: (200, {"ok": True})).send(1, "x", preview=False).ok
    assert "parse_mode" not in calls[0][1]          # plain text: no markup a post could inject


def test_email_transport_uses_injected_smtp_and_classifies_errors():
    import smtplib
    sent = []
    em = AT.EmailTransport(host="smtp.example.invalid", port=587, user="u", password="pw-123456", sender="a@example.invalid",
                           to="b@example.invalid", smtp=lambda m: sent.append(m))
    assert em.send(1, "memelab research alert, NOTICE\nbody", preview=False).ok and sent[0]["To"] == "b@example.invalid"

    def auth(m):
        raise smtplib.SMTPAuthenticationError(535, b"bad")
    assert not AT.EmailTransport(host="h", port=587, user="u", password="p", sender="a", to="b", smtp=auth).send(1, "x", preview=False).retryable


def test_dst_schedule_quiet_hours_and_local_day():
    t = AS.TEMPLATES["daily"]
    # fall back on 2026-11-01: 07:47 local is 11:47 UTC before and 12:47 UTC after
    runs = AS.next_runs(t, datetime(2026, 10, 30, 12, tzinfo=timezone.utc).timestamp(), 4)
    assert [r["utc"] for r in runs] == ["2026-10-31 11:47 UTC", "2026-11-01 12:47 UTC", "2026-11-02 12:47 UTC", "2026-11-03 12:47 UTC"]
    assert [r["slot"] for r in runs] == ["2026-10-31", "2026-11-01", "2026-11-02", "2026-11-03"]
    # spring forward on 2027-03-14
    runs = AS.next_runs(t, datetime(2027, 3, 13, 0, tzinfo=timezone.utc).timestamp(), 2)
    assert [r["utc"] for r in runs] == ["2027-03-13 12:47 UTC", "2027-03-14 11:47 UTC"]
    # a time inside the gap runs once at the first valid minute; a repeated time runs once at its first occurrence
    gap = dict(t, local_time="02:30")
    r = [x for x in AS.next_runs(gap, datetime(2027, 3, 13, 12, tzinfo=timezone.utc).timestamp(), 2) if x["slot"] == "2027-03-14"]
    assert r[0]["local"] == "2027-03-14 03:00 EDT"
    fold = dict(t, local_time="01:30")
    r = [x for x in AS.next_runs(fold, datetime(2026, 10, 31, 12, tzinfo=timezone.utc).timestamp(), 3) if x["slot"] == "2026-11-01"]
    assert len(r) == 1 and r[0]["utc"] == "2026-11-01 05:30 UTC"
    assert AS.slot_key(AS.TEMPLATES["weekly"], datetime(2026, 11, 2, 13, 13, tzinfo=timezone.utc)) == "2026-W45"
    assert AS.TEMPLATES["daily"]["enabled"] is False and AS.TEMPLATES["weekly"]["enabled"] is False
    # quiet hours 22:00 to 07:00 New York on both sides of the change
    p = AC.make_policy()
    assert AC.in_quiet_hours(datetime(2026, 10, 31, 2, 30, tzinfo=timezone.utc).timestamp(), p)        # 22:30 EDT
    assert not AC.in_quiet_hours(datetime(2026, 11, 2, 2, 30, tzinfo=timezone.utc).timestamp(), p)     # 21:30 EST
    assert AC.in_quiet_hours(datetime(2026, 11, 2, 3, 30, tzinfo=timezone.utc).timestamp(), p)         # 22:30 EST
    assert not AC.in_quiet_hours(datetime(2026, 11, 2, 12, 5, tzinfo=timezone.utc).timestamp(), p)     # 07:05 EST
    # the daily cap counts the local day: 03:30 UTC on 13 Oct is still 12 Oct in New York
    assert AC.local_day(datetime(2026, 10, 13, 3, 30, tzinfo=timezone.utc).timestamp(), "America/New_York") == "2026-10-12"
    with pytest.raises(AC.AlertError):
        AS.validate(dict(t, kind="hourly", every_hours=0))


def test_no_alert_day(con, policy, tmp_path):
    r = AE.run(con, feed=feed([], snap=1), policy=policy, mode="send", now=T0, transports=[sink(tmp_path)])
    assert r["outcome"] == "evaluated" and r["evaluation"]["new"] == []
    assert "No alerts today." in AE.render_run(r, policy["tz"])
    assert ledger(con) == [] and not (tmp_path / "outbox").exists()
    assert "No alerts recorded." in AE.render_state(AE.state_view(con))


# ---------- spam control, consent, safety ----------

def test_quiet_hours_hold_release_and_expiry(con, policy, tmp_path):
    night = datetime(2026, 10, 14, 3, 0, tzinfo=timezone.utc).timestamp()     # 23:00 EDT
    tg = FakeTransport()
    AE.run(con, feed=feed([item(last=night - H)], snap=1, as_of=night), policy=policy, mode="send", now=night, transports=[sink(tmp_path), tg])
    assert con.execute("SELECT status FROM alert_events").fetchone()[0] == "HELD" and ledger(con) == []
    morning = datetime(2026, 10, 14, 11, 10, tzinfo=timezone.utc).timestamp()   # 07:10 EDT
    r = AE.run(con, feed=None, policy=policy, mode="send", now=morning, transports=[sink(tmp_path), tg])
    assert r["delivery"]["released"] and len(tg.sent) == 1
    # held longer than hold_max_hours: expired, never sent
    night2 = night + 24 * H
    AE.run(con, feed=feed([item(last=night2 - H, people=[who("x1", trader="a"), who("x2", trader="b"), who("x3")], ind=3, liq="NO_SELL_ROUTE")],
                          snap=2, as_of=night2), policy=policy, mode="send", now=night2, transports=[sink(tmp_path), tg])
    r = AE.run(con, feed=None, policy=policy, mode="send", now=night2 + 15 * H, transports=[sink(tmp_path), tg])
    assert r["delivery"]["expired"] and len(tg.sent) == 1


def test_daily_cap_and_min_interval_and_same_snapshot(con, tmp_path):
    p = AC.make_policy({"daily_cap": 2})
    items = [item(key=f"ca:solana:{CONTRACT[:-2]}{i:02d}", contract=f"{CONTRACT[:-2]}{i:02d}", liq="NO_SELL_ROUTE") for i in range(5)]
    r = AE.run(con, feed=feed(items, snap=1), policy=p, mode="send", now=T0, transports=[sink(tmp_path)])
    assert len(r["evaluation"]["new"]) == 2
    assert sum(1 for s in r["evaluation"]["suppressed"] if s["reason_code"] == "daily_cap") == 8
    assert AE.run(con, feed=feed(items, snap=2), policy=p, mode="send", now=T0 + 600, transports=[sink(tmp_path)])["outcome"] == "too_soon"
    assert AE.run(con, feed=feed(items, snap=1), policy=p, mode="send", now=T0 + 2 * H, transports=[sink(tmp_path)])["outcome"] == "no_new_upstream_data"
    with pytest.raises(AC.AlertError):
        AC.make_policy({"min_interval_minutes": 5})


def test_dry_run_and_send_keep_separate_state_and_previews_are_not_deliveries(con, policy, tmp_path):
    r = AE.run(con, feed=feed([item()]), policy=policy, mode="dry_run", now=T0, transports=[sink(tmp_path)])
    assert len(r["evaluation"]["new"]) == 1 and "Nothing was sent" in AE.render_run(r, policy["tz"])
    assert [d["status"] for d in ledger(con)] == ["dry_run_preview"]
    assert (tmp_path / "outbox" / "preview").exists() and not (tmp_path / "outbox" / "sent").exists()
    r = AE.run(con, feed=feed([item()]), policy=policy, mode="send", now=T0 + 60, transports=[sink(tmp_path)])
    assert len(r["evaluation"]["new"]) == 1                    # the dry run did not use up the key
    assert AE.state_view(con)["remote_deliveries_succeeded"] == 0


def test_fixture_alerts_never_go_to_a_remote_transport(con, policy, tmp_path):
    tg = FakeTransport()
    AE.run(con, feed=feed([item()], fixture=True), policy=policy, mode="send", now=T0, transports=[sink(tmp_path), tg])
    assert tg.sent == [] and {d["transport"] for d in ledger(con)} == {"file"}


def test_cost_ceiling_blocks_a_paid_transport(con, tmp_path):
    p = AC.make_policy({"transport_cost_usd": {"file": 0.0, "telegram": 0.0, "email": 0.0, "sms": 0.05},
                        "cost_ceilings_usd_per_day": {"file": 0.0, "telegram": 0.0, "email": 0.0, "x_api": 0.0, "llm": 0.0,
                                                      "telegram_bot": 0.0, "sms": 0.0}})
    sms = FakeTransport(name="sms")
    AE.run(con, feed=feed([item()]), policy=p, mode="send", now=T0, transports=[sink(tmp_path), sms])
    assert sms.sent == [] and any("cost ceiling" in (d["error"] or "") for d in ledger(con))


def test_send_needs_consent_and_config_never_holds_secrets(tmp_path, monkeypatch):
    class A:
        send = True
    with pytest.raises(AC.AlertError, match="notifications_opt_in and send_enabled"):
        ACLI._mode(A, AT.load_config(tmp_path / "none.json"))
    bad = tmp_path / "alerts.json"
    bad.write_text(json.dumps({"telegram": {"enabled": True, "bot_token": "123456789:CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"}}))
    with pytest.raises(AT.ConfigError) as e:
        AT.load_config(bad)
    assert "telegram.bot_token" in str(e.value) and "CCCC" not in str(e.value)
    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps({"notifications_opt_in": True, "send_enabled": True, "telegram": {"enabled": True, "chat_id": "42"},
                              "email": {"enabled": True, "host": "h"}}))
    cfg = AT.load_config(ok)
    assert ACLI._mode(A, cfg) == "send"
    ts, notes = AT.build_transports(cfg, outbox=tmp_path / "o", env={})
    assert [t.name for t in ts] == ["file"]
    assert {n["transport"]: n["status"] for n in notes} == {"telegram": "not_configured", "email": "not_configured"}
    ts, _ = AT.build_transports(cfg, outbox=tmp_path / "o", env={AT.TELEGRAM_TOKEN_ENV: "123456789:DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD"})
    assert [t.name for t in ts] == ["file", "telegram"]


def test_policy_refuses_trading_keys_and_stance_switch_rules(policy):
    with pytest.raises(AC.AlertError):
        AC.make_policy({"policies": {"risk": {"watchlist": True}}})
    with pytest.raises(AC.AlertError):
        AC.make_policy({"trade_execution_impact": "size"})
    ch = [{"who": "fx_a (x)", "trader": "t_a", "source_id": "x:id:fx_a", "before": {"stance": "positive"}, "after": {"stance": "negative"},
           "after_at": T0 - H, "basis": "previous snapshot run 6"},
          {"who": "fx_z (x)", "trader": None, "source_id": "x:id:fx_z", "before": {"stance": "positive"}, "after": {"stance": "negative"},
           "after_at": T0 - H, "basis": "previous snapshot run 6"},
          {"who": "fx_y (x)", "trader": "t_y", "source_id": "x:id:fx_y", "before": {"stance": "negative"}, "after": {"stance": "positive"},
           "after_at": T0 - H, "basis": "previous snapshot run 6"}]
    cands, supp = AC.candidates(feed([item(people=[who("fx_a")], ind=1, changes=ch)]), policy, now=T0)
    assert [c["evidence"]["who"] for c in cands] == ["fx_a (x)"]
    assert [s["reason_code"] for s in supp if s["policy"] == "stance_switch"] == ["not_reputable"]


def test_stale_feed_and_bots_never_count(policy):
    cands, supp = AC.candidates(feed([item()], fresh="STALE"), policy, now=T0)
    assert cands == [] and {s["reason_code"] for s in supp} == {"stale_source"}
    bots = [who("fx_a", trader="t", kind="BOT"), who("fx_b", trader="t2", kind="AGGREGATOR"), who("fx_c")]
    cands, supp = AC.candidates(feed([item(people=bots)]), policy, now=T0)
    assert cands == [] and supp[0]["reason_code"] == "not_reputable"


def test_alert_text_has_provenance_and_no_markup_or_post_wording(con, policy, tmp_path):
    AE.run(con, feed=feed([item()]), policy=policy, mode="dry_run", now=T0, transports=[sink(tmp_path)])
    txt = (tmp_path / "outbox" / "preview" / "alert_000001.txt").read_text()
    assert "Provenance: narrative run 7" in txt and AC.DISCLAIMER in txt and "Confidence: MODERATE" in txt
    assert "*" not in txt and "](" not in txt and "—" not in txt


def test_state_never_goes_into_the_tracked_database():
    from memelab import db
    with pytest.raises(AC.AlertError):
        AE.connect(db.DB_PATH)


def test_cli_live_run_on_a_database_without_social_tables_is_a_no_op(tmp_path):
    import sqlite3
    dbp = tmp_path / "empty.sqlite"
    sqlite3.connect(dbp).close()
    env = {**__import__("os").environ, "MEMELAB_ALERT_CONFIG": str(tmp_path / "none.json")}
    r = subprocess.run([sys.executable, "-m", "memelab", "social", "alerts", "run", "--db", str(dbp), "--state", str(tmp_path / "s.sqlite"),
                        "--outbox", str(tmp_path / "o"), "--as-of", "2026-10-13T12:00:00+00:00"], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "feed_unavailable" in r.stdout and "social schema not migrated" in r.stdout and "Nothing was sent" in r.stdout
    r = subprocess.run([sys.executable, "-m", "memelab", "social", "alerts", "run", "--db", str(dbp), "--state", str(tmp_path / "s.sqlite"),
                        "--send"], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 2 and "--send refused" in r.stderr
    r = subprocess.run([sys.executable, "-m", "memelab", "social", "alerts", "status", "--state", str(tmp_path / "s.sqlite")],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0 and "No alerts recorded." in r.stdout


def test_preflight_reads_spend_against_ceilings(tmp_path):
    import sqlite3
    dbp = tmp_path / "spend.sqlite"
    c = sqlite3.connect(dbp)
    c.execute("CREATE TABLE social_api_spend (connector TEXT, billing_day TEXT, est_cost_usd REAL, mode TEXT)")
    c.execute("INSERT INTO social_api_spend VALUES ('x_api:user:1','2026-10-13',0.4,'live'), ('x_api:user:1','2026-10-13',9,'fixture')")
    c.commit(); c.close()
    p = AC.make_policy({"cost_ceilings_usd_per_day": {"x_api": 1.0, "llm": 0.0, "telegram_bot": 0.0, "file": 0, "telegram": 0, "email": 0}})
    r = ACLI.preflight(str(dbp), p, T0)
    assert r["providers"]["x_api"] == {"spent_usd": 0.4, "ceiling_usd": 1.0, "refresh_allowed": True, "paid": True, "ledger": "present"}
    assert r["providers"]["llm"]["refresh_allowed"] is False and r["providers"]["telegram_bot"]["refresh_allowed"] is True


def test_example_config_loads_and_sends_nothing():
    cfg = AT.load_config(ROOT / "docs" / "social-intelligence" / "alerts.example.json")
    assert cfg["notifications_opt_in"] is False and cfg["send_enabled"] is False
    AC.make_policy(cfg["policy"])
