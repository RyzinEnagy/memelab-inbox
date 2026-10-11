"""Phase 02 (social intelligence ingestion): inbound contract, bridge/inbox adapter, checkpoints, quarantine, health.

Temp databases, a fixed clock and a temp private folder only. No network: the pull test replaces the raw fetch.
"""
import json
import logging
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

from memelab import cli, db
from memelab.bridge import github_inbox
from memelab.social import ingest as I
from memelab.social import schema, store
from memelab.social.bridge_adapter import BridgeInboxAdapter

ROOT = Path(__file__).resolve().parent.parent
FX = ROOT / "tests" / "fixtures" / "social" / "inbox" / "soc_fx01.json"
FETCHED = 1791558000.0          # 2026-10-09T15:00:00Z, fetched_at in the fixture
T_RUN = 1791561600.0            # 2026-10-09T16:00:00Z, fixed run clock
X = "bridge_inbox:x:example_trader_a"
TG = "bridge_inbox:telegram:example_alpha_channel"
DOWN = "bridge_inbox:x:example_down_account"
LOGIN = "bridge_inbox:x:example_login_wall"
COUNTED = ["social_observations", "social_items", "social_accounts", "social_observation_provenance", "social_ingest_quarantine"]


@pytest.fixture()
def priv(tmp_path, monkeypatch):
    p = tmp_path / "private" / "p.sqlite"
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(p))
    return p


@pytest.fixture()
def dbp(tmp_path, priv):
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    return p


def run(dbp, paths, **kw):
    kw.setdefault("now", T_RUN)
    return I.ingest(BridgeInboxAdapter(paths, sleep=lambda s: None), dbp, **kw)


def counts(dbp):
    con = sqlite3.connect(dbp)
    out = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in COUNTED}
    con.close()
    return out


def rows(dbp, sql, *args):
    con = sqlite3.connect(dbp)
    con.row_factory = sqlite3.Row
    out = [dict(r) for r in con.execute(sql, args)]
    con.close()
    return out


def latest_health(dbp):
    return {r["connector"]: r for r in rows(dbp, "SELECT * FROM social_connector_health h WHERE checked_at="
                                               "(SELECT MAX(checked_at) FROM social_connector_health WHERE connector=h.connector)")}


def all_text(dbp):
    """Every string value in every social table, for content-leak checks."""
    con = sqlite3.connect(dbp)
    out = []
    for t in schema.SOCIAL_TABLES:
        for r in con.execute(f"SELECT * FROM {t}"):
            out += [v for v in r if isinstance(v, str)]
    con.close()
    return "\n".join(out)


def fixture_items():
    return json.loads(FX.read_text())["soc:x:example_trader_a"]["body"]["items"]


# ---------- the established route, through the CLI ----------

def test_cli_ingest_persists_verifiable_observation(dbp, capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "ingest", "--file", str(FX), "--db", str(dbp), "--now", str(T_RUN)])
    assert e.value.code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "PARTIAL" and out["counts"]["created"] == 4 and out["counts"]["quarantined"] == 3

    con = sqlite3.connect(dbp)
    con.row_factory = sqlite3.Row
    rec = I.event_record(con, "x:fx-x-0001")
    con.close()
    item0 = fixture_items()[0]
    p, o, it, acc = rec["provenance"], rec["observation"], rec["item"], rec["account"]
    assert o["content_hash"] == item0["content_hash"]                       # hash from the collector, verifiable
    assert o["observed_at"] == FETCHED and p["fetched_at"] == FETCHED       # fetched time
    assert it["published_at"] == store.to_utc(item0["published_at"]) == p["provider_published_at"]  # provider time
    assert it["published_at_basis"] == "PROVIDER"
    assert it["original_url"] == item0["url"] and it["provider_item_id"] == item0["provider_item_id"]
    assert acc["account_id"] == "x:id:1000000001" and acc["handle"] == "Example_Trader_A"
    assert p["source_ref"] == "soc_fx01.json#soc:x:example_trader_a" and p["plan_id"] == "soc_fx01"
    assert p["inbound_schema"] == I.INBOUND_SCHEMA and p["visibility"] == "PUBLIC" and p["freshness"] == "FRESH"
    assert p["rights_basis"] == "fixture_invented_content" and o["access_mode"] == "fixture"
    assert json.loads(o["metrics_json"]) == item0["metrics"] and o["summary"] == item0["summary"]
    assert o["analysis_version"] == I.ANALYSIS_VERSION and o["retained_content"] == "SUMMARY"

    # item without event_id gets a derived id; unknown field is dropped and listed; relative time keeps its basis
    der = rows(dbp, "SELECT * FROM social_observation_provenance WHERE event_id LIKE 'derived:%'")
    assert len(der) == 1 and json.loads(der[0]["ignored_fields"]) == ["lang"]
    assert rows(dbp, "SELECT published_at_basis b FROM social_items WHERE provider_item_id='1845000000000000102'")[0]["b"] == "PARSED_RELATIVE"

    cli.main(["social", "status", "--db", str(dbp), "--event", "x:fx-x-0001"])
    shown = json.loads(capsys.readouterr().out)
    assert shown["observation"]["content_hash"] == item0["content_hash"]


def test_status_command(dbp, capsys):
    run(dbp, [FX])
    cli.main(["social", "status", "--db", str(dbp)])
    st = json.loads(capsys.readouterr().out)
    assert st["events"] == 4
    assert st["quarantine_by_reason"] == {"BLOCKED_CONTENT": 1, "INVALID": 1, "NOT_PUBLIC": 1}
    assert {c["connector"]: c["status"] for c in st["connector_health"]}[DOWN] == "DOWN"


def test_pull_route_then_ingest(dbp, tmp_path, monkeypatch, capsys):
    """inbox/<id>.json in the hand-off repo -> github_inbox.pull -> data/inbox/<id>.result.json -> ingest."""
    monkeypatch.setattr(github_inbox, "DATA_DIR", tmp_path / "data")
    (tmp_path / "data" / "inbox").mkdir(parents=True)
    seen = {}

    def fake_fetch(path, ref=None, **kw):
        seen["path"], seen["ref"] = path, ref
        return FX.read_text()
    monkeypatch.setattr(github_inbox, "fetch_raw", fake_fetch)
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "ingest", "--pull", "inbox/soc_fx01.json", "--ref", "abc123", "--db", str(dbp), "--now", str(T_RUN)])
    assert e.value.code == 0
    assert seen == {"path": "inbox/soc_fx01.json", "ref": "abc123"}
    assert (tmp_path / "data" / "inbox" / "soc_fx01.result.json").exists()
    out = json.loads(capsys.readouterr().out)
    assert out["counts"]["created"] == 4
    assert rows(dbp, "SELECT source_ref FROM social_observation_provenance WHERE event_id='x:fx-x-0001'")[0]["source_ref"] == "soc_fx01.result.json#soc:x:example_trader_a"


# ---------- idempotency and replay ----------

def test_rerun_is_idempotent(dbp):
    first = run(dbp, [FX])
    c1 = counts(dbp)
    second = run(dbp, [FX], now=T_RUN + 60)
    assert counts(dbp) == c1
    assert second["counts"]["created"] == 0 and second["counts"]["units_replayed"] == 2
    assert first["counts"]["created"] == 4 and c1["social_observations"] == 4 and c1["social_ingest_quarantine"] == 3


def test_replay_from_renamed_file_creates_no_duplicates(dbp, tmp_path):
    run(dbp, [FX])
    c1 = counts(dbp)
    copy = tmp_path / "soc_fx01_reshipped.json"
    shutil.copy(FX, copy)
    r = run(dbp, [copy], now=T_RUN + 60)          # new source_ref, so no checkpoint helps: event ids must
    assert r["counts"]["created"] == 0 and r["counts"]["duplicates"] == 4
    after = counts(dbp)
    assert after["social_observations"] == c1["social_observations"]
    assert after["social_observation_provenance"] == c1["social_observation_provenance"]


def _crash_once(connector, after_index):
    state = {"done": False}

    def hook(unit, next_index):
        if not state["done"] and unit.connector == connector and next_index >= after_index:
            state["done"] = True
            raise RuntimeError("simulated crash between batches")
    return hook


def test_crash_between_batches_resumes_without_duplicates(dbp, tmp_path, priv):
    r1 = run(dbp, [FX], batch_size=2, hooks={"after_batch": _crash_once(X, 2)})
    assert r1["health"][X]["status"] == "DOWN" and r1["counts"]["units_failed"] == 1
    assert r1["health"][TG]["status"] == "OK"                    # the other connector carried on
    cp = rows(dbp, "SELECT * FROM social_ingest_checkpoints WHERE connector=?", X)[0]
    assert cp["status"] == "IN_PROGRESS" and cp["next_index"] == 2
    r2 = run(dbp, [FX], batch_size=2, now=T_RUN + 60)
    assert rows(dbp, "SELECT status FROM social_ingest_checkpoints WHERE connector=?", X)[0]["status"] == "COMPLETE"
    assert r2["counts"]["units_replayed"] == 1                   # telegram was already complete

    clean = tmp_path / "clean.sqlite"
    db.init_db(clean)
    run(clean, [FX], batch_size=2)
    assert counts(dbp) == counts(clean)
    ids = lambda p: {r["event_id"] for r in rows(p, "SELECT event_id FROM social_observation_provenance")}
    assert ids(dbp) == ids(clean)


def test_budget_stops_cleanly_and_resumes(dbp, tmp_path):
    r1 = run(dbp, [FX], budget=I.Budget(max_items=3))
    assert r1["counts"]["budget_stopped"] >= 1
    cov = {r["connector"]: r for r in rows(dbp, "SELECT * FROM social_coverage WHERE run_id=?", r1["run_id"])}
    assert any(c["status"] in ("PARTIAL", "SKIPPED") and "budget" in (c["gap_reason"] or "") for c in cov.values())
    run(dbp, [FX], now=T_RUN + 60)
    clean = tmp_path / "clean.sqlite"
    db.init_db(clean)
    run(clean, [FX])
    assert counts(dbp) == counts(clean)


# ---------- quarantine, stale data, malformed units ----------

def test_bad_items_quarantined_good_items_kept(dbp, priv):
    run(dbp, [FX])
    q = rows(dbp, "SELECT * FROM social_ingest_quarantine ORDER BY item_index")
    assert [(r["item_index"], r["reason_code"]) for r in q] == [(2, "INVALID"), (3, "BLOCKED_CONTENT"), (4, "NOT_PUBLIC")]
    errs = " ".join(r["errors_json"] for r in q)
    assert "published_at" in errs and "metrics" in errs and "text" in errs
    for value in ("5.4K", "yesterday", "placeholder"):
        assert value not in errs                                  # errors name fields, never values
    # item 5 comes after the bad ones and is still stored
    assert rows(dbp, "SELECT 1 FROM social_items WHERE provider_item_id='1845000000000000106'")
    # the payloads went to the gitignored private quarantine folder, not to the public DB
    for r in q:
        f = priv.parent / r["private_payload_ref"]
        assert f.exists() and json.loads(f.read_text())["item_index"] == r["item_index"]
    assert "placeholder" not in all_text(dbp)


def test_stale_data_is_flagged_not_dropped(dbp):
    r = run(dbp, [FX], now=FETCHED + 48 * 3600, max_age_hours=12)
    assert r["counts"]["created"] == 4 and r["counts"]["stale_items"] == 4
    assert {x["freshness"] for x in rows(dbp, "SELECT freshness FROM social_observation_provenance")} == {"STALE"}
    h = latest_health(dbp)
    assert h[X]["status"] == "DEGRADED" and h[TG]["status"] == "DEGRADED" and "stale" in h[TG]["error"]
    cov = rows(dbp, "SELECT * FROM social_coverage WHERE connector=?", TG)[0]
    assert cov["status"] == "PARTIAL" and "stale" in cov["gap_reason"]
    assert r["status"] == "PARTIAL"


def _result_file(tmp_path, name, entries):
    p = tmp_path / name
    p.write_text(json.dumps({"_plan": name.split(".")[0], "_at": "2026-10-09T15:00:00Z", **entries}))
    return p


def _env(fetched_at="2026-10-09T15:00:00Z", items=None, **src):
    source = {"platform": "x", "source_id": "s1", "access_mode": "fixture", "collector": "fixture-bridge",
              "rights_basis": "fixture_invented_content", "visibility": "PUBLIC", **src}
    return {"s": 200, "body": {"schema": I.INBOUND_SCHEMA, "source": source, "fetched_at": fetched_at,
                               "items": items if items is not None else []}}


def test_malformed_and_future_units_and_items(dbp, tmp_path):
    good = {"provider_item_id": "1", "content_hash": "a" * 64}
    p = _result_file(tmp_path, "soc_bad.json", {
        "soc:x:future_env": _env(fetched_at="2026-10-12T00:00:00Z", items=[good]),           # fetched in the future
        "soc:x:wrong_schema": {"s": 200, "body": {"schema": "memelab.social.inbound/0", "items": []}},
        "soc:x:naive_time": _env(fetched_at="2026-10-09T15:00:00", items=[good]),             # zone unknown
        "soc:x:mixed": _env(items=[good, {"provider_item_id": "2", "published_at": "2026-10-09T18:00:00Z"},  # after fetch
                                   {"provider_item_id": "3", "content_hash": "NOTAHASH"}, {"url": "http://insecure"},
                                   "not-an-object", {"provider_item_id": "4", "account": {"handle": "h", "bio": "x"}}]),
        "soc:x:not_an_entry": "garbage",
    })
    r = run(dbp, [p])
    q = rows(dbp, "SELECT source_ref, item_index, reason_code FROM social_ingest_quarantine ORDER BY source_ref, item_index")
    units = {(x["source_ref"].split("#")[1], x["item_index"], x["reason_code"]) for x in q}
    assert ("soc:x:future_env", None, "SCHEMA") in units
    assert ("soc:x:wrong_schema", None, "SCHEMA") in units
    assert ("soc:x:naive_time", None, "SCHEMA") in units
    assert {(i, c) for k, i, c in units if k == "soc:x:mixed"} == {(1, "INVALID"), (2, "INVALID"), (3, "INVALID"), (4, "INVALID"), (5, "BLOCKED_CONTENT")}
    assert rows(dbp, "SELECT COUNT(*) n FROM social_observations")[0]["n"] == 1      # the one good item
    assert r["health"]["bridge_inbox:x:not_an_entry"]["status"] == "DOWN"
    cps = {x["source_ref"].split("#")[1]: x["status"] for x in rows(dbp, "SELECT * FROM social_ingest_checkpoints")}
    assert cps["soc:x:future_env"] == "REJECTED" and cps["soc:x:mixed"] == "COMPLETE"
    again = run(dbp, [p], now=T_RUN + 60)
    assert again["counts"]["quarantined"] == 0 and again["counts"]["created"] == 0   # rejected units are not retried


# ---------- connector isolation and health ----------

def test_unavailable_connectors_do_not_mark_all_healthy(dbp):
    r = run(dbp, [FX])
    h = latest_health(dbp)
    assert h[DOWN]["status"] == "DOWN" and h[LOGIN]["status"] == "LOGIN_REQUIRED"
    assert h[TG]["status"] == "OK" and h[X]["status"] == "DEGRADED"
    assert r["status"] == "PARTIAL"
    cov = {x["connector"]: x for x in rows(dbp, "SELECT * FROM social_coverage")}
    assert cov[DOWN]["status"] == "GAP" and cov[LOGIN]["status"] == "BLOCKED" and cov[TG]["status"] == "COVERED"
    assert "gt_pools" not in json.dumps(r["health"])                 # non-social keys are left to other modules


def test_unreadable_files_do_not_end_the_run(dbp, tmp_path):
    bad = tmp_path / "broken.json"
    bad.write_text("{not json")
    r = run(dbp, [tmp_path / "missing.json", bad, FX])
    assert r["health"]["bridge_inbox:file:missing.json"]["status"] == "DOWN"
    assert r["health"]["bridge_inbox:file:broken.json"]["status"] == "DOWN"
    assert r["counts"]["created"] == 4


def test_unexpected_error_in_one_connector_is_contained(dbp, monkeypatch):
    real = I._persist_item

    def boom(con, **kw):
        if kw["unit"].connector == TG:
            raise RuntimeError("unexpected bug")
        return real(con, **kw)
    monkeypatch.setattr(I, "_persist_item", boom)
    r = run(dbp, [FX])
    assert r["health"][TG]["status"] == "DOWN" and "unexpected bug" in r["health"][TG]["errors"][0]
    assert r["health"][X]["status"] == "DEGRADED" and r["counts"]["created"] == 3
    monkeypatch.setattr(I, "_persist_item", real)
    r2 = run(dbp, [FX], now=T_RUN + 60)
    assert r2["health"][TG]["status"] == "OK" and r2["counts"]["created"] == 1


def test_all_connectors_down_is_failed_and_exits_1(dbp, tmp_path, capsys):
    p = _result_file(tmp_path, "soc_down.json", {"soc:x:a": {"s": 0, "err": "Failed to fetch"}, "soc:x:b": {"s": 429}})
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "ingest", "--file", str(p), "--db", str(dbp), "--now", str(T_RUN)])
    assert e.value.code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "FAILED" and out["health"]["bridge_inbox:x:b"]["status"] == "RATE_LIMITED"


# ---------- retries, logging, browser hash ----------

def test_bounded_retries(tmp_path):
    sleeps, calls = [], {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise I.TransientError("not yet")
        return "ok"
    assert I.with_retries(flaky, attempts=3, base_delay=0.5, sleep=sleeps.append) == "ok" and sleeps == [0.5, 1.0]
    with pytest.raises(I.TransientError):
        I.with_retries(lambda: (_ for _ in ()).throw(I.TransientError("x")), attempts=2, sleep=lambda s: None)
    with pytest.raises(ValueError):                                      # not transient: no retry
        I.with_retries(lambda: (_ for _ in ()).throw(ValueError("x")), attempts=5, sleep=sleeps.append)
    empty = tmp_path / "empty.json"
    empty.write_text("")
    slept = []
    units = list(BridgeInboxAdapter([empty], retries=3, sleep=slept.append).units(I.Budget()))
    assert units[0].status == "DOWN" and len(slept) == 2


def test_logs_never_carry_secrets_or_content(dbp, tmp_path, caplog):
    data = json.loads(FX.read_text())
    data["soc:x:example_down_account"]["err"] = "fetch https://api.example.com/v1?api-key=SECRET123&x=1 failed, Bearer abc.def"
    p = tmp_path / "soc_secret.json"
    p.write_text(json.dumps(data))
    with caplog.at_level(logging.INFO, logger="memelab.social.ingest"):
        r = run(dbp, [p])
    text = caplog.text
    assert "SECRET123" not in text and "abc.def" not in text and "[REDACTED]" in text
    assert "placeholder" not in text and "5.4K" not in text
    for it in fixture_items():
        if it.get("summary"):
            assert it["summary"] not in text
    for line in caplog.records:
        json.loads(line.getMessage())                                   # every log line is one JSON object
    assert "SECRET123" not in json.dumps(r) and "SECRET123" not in all_text(dbp)


def test_browser_hash_matches_python():
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    samples = ["Plain text", "  tabs\tand\nnew lines  ", "café vs café", "nbsp inside", "emoji \U0001F680 ok"]
    js = (ROOT / "memelab" / "bridge" / "social.js").read_text()
    script = "globalThis.window = globalThis;\n" + js + "\n(async () => { const s = JSON.parse(process.argv[1]);" \
             " const out = []; for (const t of s) out.push(await window.__SOC.hash(t)); console.log(JSON.stringify(out)); })();"
    res = subprocess.run([node, "-e", script, json.dumps(samples)], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    assert json.loads(res.stdout) == [store.text_hash(s) for s in samples]


def test_schema_v2_rolls_back_to_v1_only(dbp):
    con = sqlite3.connect(dbp)
    assert schema.current_version(con) == 2
    assert schema.rollback(con, 1) == [2]
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "social_observations" in names and "social_ingest_runs" not in names
    assert schema.migrate(con) == [2]
    con.close()
