"""Carry-over C-2: repo-wide guard against raw third-party social content in tracked files.

The first test scans this checkout's tracked files. The others build small temp trees with known leaks and
known look-alikes, so each rule is shown to fire, and not to fire on lab-written or market data.
"""
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

from memelab import cli
from memelab.social import content_guard as G

ROOT = Path(__file__).resolve().parent.parent
LEAK = "invented leaked sentence that stands in for a copied post"


def test_tracked_repo_is_clean():
    if not (ROOT / ".git").exists() or not shutil.which("git"):
        pytest.skip("not a git checkout")
    out = G.scan(ROOT)
    assert out["sqlite_files"] == 1 and out["json_files"] > 0
    assert out["violations"] == [], json.dumps(out["violations"], indent=1)


def _write(root: Path, rel: str, data) -> str:
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data))
    return rel


def _unit(items, **body_extra):
    return {"s": 200, "body": {"schema": "memelab.social.inbound/1", "source": {"platform": "x", "visibility": "PUBLIC"},
                               "fetched_at": "2026-10-09T15:00:00Z", "items": items, **body_extra}}


def test_json_rules_fire_and_never_echo_values(tmp_path):
    paths = [
        _write(tmp_path, "inbox/soc_leak.json", {"_plan": "soc_leak", "soc:x:a": _unit([
            {"provider_item_id": "1", "text": LEAK},
            {"provider_item_id": "2", "account": {"handle": "h", "bio": LEAK}},
            {"provider_item_id": "3", "visibility": "PRIVATE_GROUP", "summary": "a group post"},
            {"provider_item_id": "4", "summary": "x" * 401},
            {"provider_item_id": "5", "media": ["https://example.invalid/img.png"]},
        ], html="<p>" + LEAK + "</p>")}),
        _write(tmp_path, "inbox/cat_xprof.json", {"xprof:trader:x:someone": {"s": 200, "body": {"title": "Someone (@someone)", "bio": LEAK}}}),
    ]
    out = G.scan(tmp_path, paths)
    got = {(v["path"], v["where"]) for v in out["violations"]}
    assert ("inbox/soc_leak.json", "soc:x:a.body.items[0].text") in got
    assert ("inbox/soc_leak.json", "soc:x:a.body.items[1].account.bio") in got
    assert ("inbox/soc_leak.json", "soc:x:a.body.items[2].visibility") in got
    assert ("inbox/soc_leak.json", "soc:x:a.body.items[3].summary") in got
    assert ("inbox/soc_leak.json", "soc:x:a.body.items[4].media") in got
    assert ("inbox/soc_leak.json", "soc:x:a.body.html") in got
    assert ("inbox/cat_xprof.json", "xprof:trader:x:someone.body.bio") in got
    assert LEAK not in json.dumps(out) and "a group post" not in json.dumps(out)


def test_lookalike_keys_outside_social_units_are_not_flagged(tmp_path):
    paths = [
        _write(tmp_path, "inbox/market.json", {"gt_pools:solana:new:1": {"s": 200, "body": {"pools": [{"pool": "p", "quote": "So111"}]}},
                                               "gt_info:m": {"s": 200, "body": {"description": "issuer text"}}}),
        _write(tmp_path, "inbox/cat01.json", {"cat:news:x": {"s": 200, "body": [{"title": "headline", "desc": "teaser"}]}}),
        _write(tmp_path, "state/latest.json", {"_tables": {"launch_alerts": [{"text": "lab-written alert"}]}}),
        _write(tmp_path, "inbox/soc_ok.json", {"soc:x:a": _unit([{"provider_item_id": "1", "content_hash": "a" * 64,
                                                                 "summary": "Own-words note.", "metrics": {"likes": 3}}])}),
    ]
    assert G.scan(tmp_path, paths)["violations"] == []


def test_allowlist_is_exact_about_locations(tmp_path):
    rel = "tests/fixtures/social/inbox/soc_fx01.json"
    items = [{"provider_item_id": str(i), "content_hash": "a" * 64} for i in range(14)]
    items[3]["text"] = LEAK
    items[13]["text"] = LEAK            # must not ride on the items[3] allowance
    _write(tmp_path, rel, {"soc:x:example_trader_a": _unit(items)})
    where = [v["where"] for v in G.scan(tmp_path, [rel])["violations"]]
    assert where == ["soc:x:example_trader_a.body.items[13].text"]


def test_path_rules(tmp_path):
    paths = ["data/private/social_private.sqlite", "data/private/quarantine/abc.json", "data/wallet/w.json",
             "tools/cache.db", "data/memelab.sqlite", "memelab/social/ingest.py"]
    out = G.check_paths(paths)
    assert sorted(v.path for v in out) == ["data/private/quarantine/abc.json", "data/private/social_private.sqlite",
                                           "data/wallet/w.json", "tools/cache.db"]


def test_sqlite_rules(tmp_path):
    f = tmp_path / "data" / "memelab.sqlite"
    f.parent.mkdir(parents=True)
    con = sqlite3.connect(f)
    con.executescript("""
      CREATE TABLE social_snapshots(mint TEXT, observed_at REAL, source TEXT, metric TEXT, value REAL, text_value TEXT, notes TEXT);
      CREATE TABLE catalyst_sources(source_id TEXT, identity_notes TEXT);
      CREATE TABLE social_observations(id INTEGER PRIMARY KEY, summary TEXT);
      CREATE TABLE social_extra(id INTEGER, exact_text TEXT);
      CREATE TABLE private_content(private_ref TEXT, exact_text TEXT);
    """)
    con.execute("INSERT INTO social_snapshots VALUES ('m',1,'jupiter','holder_change_1h',3,NULL,NULL)")
    con.execute("INSERT INTO social_snapshots VALUES ('m',1,'browser','label',NULL,'bullish',NULL)")
    con.execute("INSERT INTO social_snapshots VALUES ('m',1,'browser','post',NULL,?,NULL)", (LEAK + " and then a few more words here",))
    con.execute("INSERT INTO catalyst_sources VALUES ('trader:x:a', 'seed | profile: Name / " + LEAK + "')")
    con.execute("INSERT INTO catalyst_sources VALUES ('trader:x:b', 'seed list')")
    con.execute("INSERT INTO social_observations VALUES (1, ?)", ("y" * 401,))
    con.commit()
    con.close()
    out = G.scan(tmp_path, ["data/memelab.sqlite"])
    got = {v["where"] for v in out["violations"]}
    assert got == {"private_content", "social_extra.exact_text", "social_observations.summary",
                   "social_snapshots[rowid=3].text_value", "catalyst_sources[trader:x:a].identity_notes"}
    assert LEAK not in json.dumps(out)
    assert not (tmp_path / "data" / "memelab.sqlite-wal").exists()     # read-only scan leaves nothing behind


def test_cli_guard_exit_codes(tmp_path, capsys):
    if not shutil.which("git"):
        pytest.skip("git not installed")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    _write(tmp_path, "inbox/ok.json", {"gt_pools:x": {"s": 200, "body": {"pools": []}}})
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "guard", "--root", str(tmp_path)])
    assert e.value.code == 0
    _write(tmp_path, "inbox/soc_bad.json", {"soc:x:a": _unit([{"provider_item_id": "1", "full_text": LEAK}])})
    _write(tmp_path, "inbox/untracked.json", {"soc:x:a": _unit([{"provider_item_id": "1", "text": LEAK}])})
    subprocess.run(["git", "-C", str(tmp_path), "add", "inbox/soc_bad.json"], check=True)
    capsys.readouterr()
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "guard", "--root", str(tmp_path)])
    assert e.value.code == 1
    out = json.loads(capsys.readouterr().out)
    assert {v["path"] for v in out["violations"]} == {"inbox/soc_bad.json"}       # untracked files are not published
    assert LEAK not in json.dumps(out)
