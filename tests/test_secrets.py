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


def test_no_tracked_file_holds_a_key_value():
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    bad = []
    for f in files:
        p = ROOT / f
        if p.suffix in (".sqlite", ".png", ".gz") or not p.is_file():
            continue
        txt = p.read_text(errors="ignore")
        for m in re.finditer(r"api-key=([^&\"'`\s\\<>{}]+)", txt):
            if m.group(1) not in ("REDACTED", "KEY", "key", "SECRET123") and not m.group(1).startswith("{"):
                bad.append(f)
    assert not bad, sorted(set(bad))
