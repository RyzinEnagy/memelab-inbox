"""D-020 follow-up: the catalyst trader check never ships or stores an X profile bio."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from memelab import db
from memelab.catalyst import cli as ccli
from memelab.catalyst.sources import sync_registry
from memelab.social import content_guard as G

ROOT = Path(__file__).resolve().parent.parent
BIO = "invented bio sentence that must never be stored"
PAGE = ('<html><head><title>Example Trader (@example_trader) / X</title>'
        f'<meta name="description" content="{BIO}"></head></html>')


@pytest.mark.parametrize("path", ["bridge/catalyst.js", "memelab/bridge/catalyst.js"])
def test_x_profile_projection_drops_the_bio(path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    script = ("globalThis.window = globalThis;\n" + (ROOT / path).read_text() +
              "\nconsole.log(JSON.stringify(window.__ML.PROJ.x_profile(process.argv[1])));")
    res = subprocess.run([node, "-e", script, PAGE], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout.strip().splitlines()[-1])
    assert out == {"title": "Example Trader (@example_trader) / X", "exists": True}


def test_verify_trader_stores_no_profile_text(tmp_path, monkeypatch):
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    monkeypatch.setattr(db, "DB_PATH", p)
    with db.connect(p) as con:
        sync_registry(con)                                   # the real trader rows, as catalyst plan creates them
        sid = con.execute("SELECT source_id FROM catalyst_sources WHERE source_group='trader' ORDER BY source_id LIMIT 1").fetchone()[0]
    handle = sid.split(":")[-1]
    title = f"Example Trader (@{handle}) / X"
    # an older result file that still carries a bio: it must be ignored
    v = {"s": 200, "body": {"title": title, "bio": BIO, "exists": True}}
    ccli._verify_trader(sid, v)
    ccli._verify_trader(sid, v)          # re-run does not grow the note
    with db.connect(p) as con:
        r = con.execute("SELECT identity_verified, identity_notes FROM catalyst_sources WHERE source_id=?", (sid,)).fetchone()
    assert r["identity_verified"] == "VERIFIED"
    assert BIO not in r["identity_notes"] and "Example Trader" not in r["identity_notes"]
    assert r["identity_notes"].count("profile page found") == 1
    tracked = tmp_path / "repo" / "data" / "memelab.sqlite"
    tracked.parent.mkdir(parents=True)
    shutil.copy(p, tracked)
    assert G.scan(tmp_path / "repo", ["data/memelab.sqlite"])["violations"] == []
