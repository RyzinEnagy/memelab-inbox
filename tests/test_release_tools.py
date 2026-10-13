"""Phase 18 release tools: the audit's patterns, the no-trading and no-credential checks on the tracked tree, the
migration check, and the end-to-end stage list. Offline; nothing is written into tracked paths."""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AUD = _load("release_audit")
E2E = _load("release_e2e")


def _hits(path, data):
    out, rev = [], []
    AUD.scan_bytes(path, data, out, rev)
    return out, rev


def test_credential_shapes_are_caught_and_values_never_reported():
    # built at run time so this file does not itself carry the shapes
    shapes = {
        "anthropic_key": "sk-" + "ant-" + "q7Rk2LmZ9xVb4NcT8wYp1sDf",
        "github_token": "gh" + "p_" + "9fK2mQ7xL4vB8nR1tZ6cW3yH5jD0sAeU2iOq",
        "telegram_bot_token": "7381" + "92645:AA" + "Hq3Lm9Zx2Vb7Nc4Tw8Yp1Sd6Fg5Jk0Rtu",
        "pem_private_key": "-----BEGIN " + "PRIVATE KEY-----",
        "api_key_param": "api-" + "key=" + "3f9a1c2e-7b4d-4e8a-9c1f-2d3e4f5a6b7c",
        "solana_keypair_array": "[" + ",".join(str((i * 37) % 256) for i in range(64)) + "]",
    }
    for rule, value in shapes.items():
        out, _ = _hits("x.json", ("prefix " + value + " suffix").encode())
        assert [h["rule"] for h in out] == [rule], rule
        assert value not in json.dumps(out)


def test_placeholder_shapes_are_reviewed_not_findings():
    out, rev = _hits("tests/x.py", ("123456789:AA" + "A" * 33).encode())
    assert out == [] and rev and "placeholder" in rev[0]["why"]


def test_tracked_tree_has_no_credentials_or_key_material():
    out, _ = AUD.scan_tree()
    assert out == [], [(h["path"], h["line"], h["rule"]) for h in out]


def test_no_trade_execution_or_signing_code_in_tracked_files():
    out, _ = AUD.scan_exec()
    assert out == [], [(h["path"], h["line"], h["rule"]) for h in out]


def test_example_configs_are_safe_by_default():
    for name, v in AUD.billing_defaults().items():
        assert not (v["allow_billable_true"] or v["send_enabled_true"] or v["holds_secret_key"]), name


def test_migrate_check_on_an_empty_database(tmp_path):
    p = subprocess.run([sys.executable, str(ROOT / "tools" / "release_e2e.py"), "--migrate-check", str(tmp_path / "e.sqlite")],
                       cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    d = json.loads(p.stdout)
    assert d["social_version_after"] == d["latest"] and d["legacy_unchanged"] and not d["database_existed"]


def test_e2e_stages_reference_existing_fixtures_and_expect_refusals_without_credentials():
    for sid, title, cmd, expect in E2E.STAGES:
        for rel in re.findall(r"tests/fixtures/social/[\w/.-]+", cmd.replace('" + FIX + "', "tests/fixtures/social")):
            assert (ROOT / rel).exists(), (title, rel)
        if title.startswith("no credentials") and ("ingest" in title or "health" in title or "Helius" in title):
            assert 0 not in expect, title
        if "--send" in cmd:
            assert expect == (2,), title
    titles = " ".join(s[1] for s in E2E.STAGES)
    for need in ("migrations", "fixture inbox load", "duplicate replay", "token resolution", "structured extraction",
                 "narrative change", "trader registry", "wallet attribution", "P&L", "information-alpha", "chronology",
                 "main discovery integration", "report generation", "alert dry run", "forward outcome", "causal replay",
                 "content guard"):
        assert need in titles, need


def test_e2e_never_passes_credentials_to_children():
    for v in ("HELIUS_API_KEY", "X_BEARER_TOKEN", "TELEGRAM_BOT_TOKEN", "ANTHROPIC_API_KEY", "MEMELAB_ALERT_SMTP_PASSWORD"):
        assert v in E2E.SECRET_VARS
    assert "socket.connect" in E2E.NETGUARD and "raise PermissionError" in E2E.NETGUARD


def test_audit_knows_the_discord_bot_token_shape():
    shape = b"M" + b"T" * 25 + b".GaBcDe." + b"x1" * 16          # built at run time so no literal token sits in the tree
    assert AUD.CRED["discord_bot_token"].search(shape)
    assert not AUD.CRED["discord_bot_token"].search(b"fixtureDiscordTokenNotReal01.GfIxTr.fixtureTokenNotRealDoNotLeak0123456789")


def test_audit_knows_google_api_key_and_oauth_token_shapes():
    assert AUD.CRED["google_api_key"].search(b"key=AIza" + b"Q" * 35 + b"&part=id")
    assert not AUD.CRED["google_api_key"].search(b"fixtureYoutubeKeyNotReal_0123456789")
    assert AUD.CRED["google_oauth_token"].search(b"Authorization: Bearer ya29." + b"a1" * 20)
