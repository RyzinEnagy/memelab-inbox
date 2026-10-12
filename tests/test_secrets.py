"""The Helius key must be reachable by the code and must never reach a committed file. Invented key values only."""
import json
import re
import subprocess
from pathlib import Path

from memelab import secrets
from memelab.bridge import github_inbox
from memelab.bridge.plan import Plan

ROOT = Path(__file__).resolve().parent.parent
FAKE = "00000000-1111-2222-3333-444444444444"
W = "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"


def test_env_beats_config_and_config_is_the_fallback(tmp_path, monkeypatch):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"helius_api_key": "from-config"}))
    monkeypatch.setattr(github_inbox, "CONFIG_PATH", cfg)
    monkeypatch.delenv(secrets.ENV, raising=False)
    assert secrets.helius_key() == "from-config"
    monkeypatch.setenv(secrets.ENV, FAKE)
    assert secrets.helius_key() == FAKE
    monkeypatch.setenv(secrets.ENV, "  ")
    assert secrets.helius_key() == "from-config"


def test_plan_uses_the_key_in_memory_but_saved_file_is_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv(secrets.ENV, FAKE)
    p = Plan("t1").wallet_activity([W])
    assert FAKE in p.js_call()                       # the browser run needs the real key
    saved = p.save(tmp_path / "t1.plan.json").read_text()
    assert FAKE not in saved and "api-key=REDACTED" in saved


def test_redact_handles_rpc_and_tx_urls():
    t = "https://mainnet.helius-rpc.com/?api-key=abc-123 and https://api.helius.xyz/v0/x?api-key=zzz&limit=5"
    r = secrets.redact(t)
    assert "abc-123" not in r and "zzz" not in r and "limit=5" in r


# A Helius key is a UUID. The check flags a value after "api-key=" only when it is shaped like a key (a UUID or a 24+ character token), so prose such as
# "api-key=..." in a handoff, a regex in secrets.py and the short invented strings in this file are not reported as leaks.
KEY_SHAPED = re.compile(r"^(?:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[A-Za-z0-9_-]{24,})$")


def test_no_tracked_file_holds_a_key_value():
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    bad = []
    for f in files:
        p = ROOT / f
        if p.suffix in (".sqlite", ".png", ".gz") or not p.is_file():
            continue
        txt = p.read_text(errors="ignore")
        for m in re.finditer(r"api-key=([^&\"'`\s\\<>{}]+)", txt):
            if m.group(1) not in ("REDACTED", "KEY", "key", "SECRET123") and not m.group(1).startswith("{") and KEY_SHAPED.match(m.group(1)):
                bad.append(f)
    assert not bad, sorted(set(bad))


def test_the_key_shape_check_still_catches_a_uuid_key_and_ignores_prose():
    assert KEY_SHAPED.match(FAKE) and KEY_SHAPED.match("a" * 24)
    assert not KEY_SHAPED.match("...") and not KEY_SHAPED.match("abc-123") and not KEY_SHAPED.match("zzz") and not KEY_SHAPED.match("[^&")
