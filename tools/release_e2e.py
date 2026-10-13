"""Release end-to-end run (Phase 18): every social-intelligence stage, on fixtures, in a clean clone, with the network blocked.

Usage:
    python tools/release_e2e.py [--src REPO] [--out FILE.md] [--json FILE.json] [--keep] [--skip-replay]

What it does:
  1. `git clone --local` the committed HEAD of REPO (default: this repo) into a temp folder. Uncommitted changes are not
     part of the run, so the run proves what is committed.
  2. Points every database and private file at the temp folder (MEMELAB_DB, MEMELAB_PRIVATE_DB, MEMELAB_ALERT_DB,
     MEMELAB_ALERT_CONFIG, MEMELAB_SIGNAL_LEDGER, MEMELAB_LLM_CONFIG) and removes every credential variable from the
     environment, so nothing live or billable can run.
  3. Installs a Python audit hook (sitecustomize) that refuses and logs every socket connect and DNS lookup, and points
     HTTP(S)_PROXY at a closed local port for any non-Python child.
  4. Runs the stages in order and records each command, exit code and the head of its output.
  5. Checks afterwards: no network attempt, the clone's tracked files unchanged (`git status --porcelain` empty),
     the tracked database byte-identical.

Exit 0 when every stage returned its expected exit code and every after-check passed, else 1. Never touches the
working copy it is started from.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SECRET_VARS = ("HELIUS_API_KEY", "X_BEARER_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_WEBHOOK_SECRET", "ANTHROPIC_API_KEY",
               "MEMELAB_ALERT_TELEGRAM_TOKEN", "MEMELAB_ALERT_TELEGRAM_CHAT_ID", "MEMELAB_ALERT_SMTP_PASSWORD",
               "GH_TOKEN", "GITHUB_TOKEN")

NETGUARD = r'''
import os, socket, sys
_LOG = os.environ.get("RELEASE_NETGUARD_LOG")
def _hook(ev, args):
    if ev not in ("socket.connect", "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex"):
        return
    if ev == "socket.connect":
        sock = args[0]
        if getattr(sock, "family", None) == getattr(socket, "AF_UNIX", -1):
            return
        target = args[1]
    else:
        target = args[0]
    if _LOG:
        with open(_LOG, "a") as fh:
            fh.write(f"{ev} {target!r} argv={sys.argv[:3]!r}\n")
    raise PermissionError("network blocked by tools/release_e2e.py")
sys.addaudithook(_hook)
'''

# stage id, title, command (format keys: {db} {tmp} {py}), expected exit codes
FIX = "tests/fixtures/social"
NOW = "1791849600"  # 2026-10-13T00:00:00Z, fixed clock
T1 = "5rXq7LtW6VnvMo16bB67FBstaaCr5RFeA7MCgECdkcpD"  # invented fixture wallet in fx_helius_ok.json

STAGES: list[tuple[str, str, str, tuple[int, ...]]] = [
    ("00", "setup: interpreter and test tooling", "{py} -c \"import sys, numpy, pytest; print(sys.version.split()[0], 'numpy', numpy.__version__, 'pytest', pytest.__version__)\"", (0,)),
    ("00", "setup: CLI loads", "{py} -m memelab social --help", (0,)),
    ("01", "migrations: empty database to latest", "{py} {me} --migrate-check {db}", (0,)),
    ("01", "migrations: idempotent second init", "{py} {me} --migrate-check {db}", (0,)),
    ("01", "migrations: copy of the tracked database (legacy rows unchanged)", "cp data/memelab.sqlite {tmp}/tracked_copy.sqlite && {py} {me} --migrate-check {tmp}/tracked_copy.sqlite", (0,)),
    ("02", "fixture inbox load (bridge result file)", "{py} -m memelab social ingest --file " + FIX + "/inbox/soc_fx01.json --db {db} --now 1791566000", (0,)),
    ("03", "duplicate replay: same file again adds nothing", "{py} -m memelab social ingest --file " + FIX + "/inbox/soc_fx01.json --db {db} --now 1791566100", (1,)),
    ("03", "duplicate replay: renamed copy adds nothing", "cp " + FIX + "/inbox/soc_fx01.json {tmp}/renamed_copy.json && {py} -m memelab social ingest --file {tmp}/renamed_copy.json --db {db} --now 1791566200", (0,)),
    ("03", "ingest status", "{py} -m memelab social status --db {db}", (0,)),
    ("04", "token resolution: ambiguous ticker", "{py} -m memelab social resolve --post " + FIX + "/resolve/post_ambiguous.json --bodies " + FIX + "/resolve/fx_providers.json --context --db {db} --now 1791676800", (0,)),
    ("04", "token resolution: exact contract", "{py} -m memelab social resolve --post " + FIX + "/resolve/post_resolved.json --bodies " + FIX + "/resolve/fx_providers.json --context --db {db} --now 1791676800", (0,)),
    ("05", "structured extraction without a model", "{py} -m memelab social extract --post " + FIX + "/claims/demo_post_nollm.json --db {db} --now 1791676800", (0,)),
    ("05", "structured extraction with the offline mock provider", "{py} -m memelab social extract --post " + FIX + "/claims/demo_post_model.json --mock " + FIX + "/claims/demo_mock.json --db {db} --now 1791676800", (0,)),
    ("05", "model status (none configured)", "{py} -m memelab social llm-health", (0,)),
    ("06", "narrative snapshot, day before", "{py} -m memelab social narrative-snapshot --day 2026-10-09 --tz UTC --db {db} --now " + NOW, (0,)),
    ("06", "narrative snapshot, claim day", "{py} -m memelab social narrative-snapshot --day 2026-10-10 --tz UTC --db {db} --now " + NOW, (0,)),
    ("06", "narrative change since the previous snapshot", "{py} -m memelab social narrative-changes --db {db}", (0,)),
    ("07", "trader registry: import a permitted list (fixture)", "{py} -m memelab social registry import " + FIX + "/registry/leaderboard_fresh.json --db {db} --now " + NOW, (0,)),
    ("07", "trader registry: add an account (fixture)", "{py} -m memelab social registry add account --platform x --handle example_poster --provider-id 4242 --fixture-label 'INVENTED FIXTURE: release e2e' --db {db} --now " + NOW, (0,)),
    ("07", "trader registry: status", "{py} -m memelab social registry status --db {db}", (0,)),
    ("08", "wallet attribution: track a fixture wallet", "{py} -m memelab social wallet track add solana " + T1 + " --reason 'fixture e2e wallet' --by release --fixture --db {db} --now " + NOW, (0,)),
    ("08", "wallet attribution: ingest fixture activity", "{py} -m memelab social wallet ingest " + FIX + "/wallets/fx_helius_ok.json --fixture --db {db} --now " + NOW, (0,)),
    ("08", "wallet attribution: self-disclosure assertion", "ACCT=$({py} -c \"import sqlite3; c=sqlite3.connect('{db}'); print(c.execute(\\\"SELECT entity_id FROM social_registry_entities WHERE entity_kind='SOCIAL_ACCOUNT' ORDER BY rowid DESC LIMIT 1\\\").fetchone()[0])\") && {py} -m memelab social wallet assert \"$ACCT\" solana " + T1 + " --type OFFICIAL_SELF_DISCLOSURE --ref https://example.invalid/post/1 --by release --db {db} --now " + NOW + " && {py} -m memelab social wallet why \"$ACCT\" solana " + T1 + " --db {db} --now " + NOW, (0,)),
    ("08", "wallet attribution: custody wallet refused", "{py} -m memelab social wallet track add solana 5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9 --reason 'custody check' --by release --fixture --db {db} --now " + NOW, (1,)),
    ("09", "P&L reconstruction (FIFO, AVCO sensitivity, reconciliation)", "{py} -m memelab social perf run --ledger " + FIX + "/perf/ledger_main.json", (0,)),
    ("10", "information-alpha evaluation", "{py} -m memelab social alpha run --input " + FIX + "/alpha/alpha_main.json --policy '{{\"horizons_s\":[3600,21600,86400]}}'", (0,)),
    ("11", "social and on-chain chronology: confident order", "{py} -m memelab social chrono run --input " + FIX + "/chrono/confident.json", (0,)),
    ("11", "social and on-chain chronology: indeterminate order", "{py} -m memelab social chrono run --input " + FIX + "/chrono/indeterminate.json", (0,)),
    ("12", "main discovery integration: scout before/after (opt-in)", "{py} -m memelab social research demo --fixture " + FIX + "/research/scout_before_after.json", (0,)),
    ("12", "integration policy (off by default, zero execution impact)", "{py} -m memelab social research policy", (0,)),
    ("13", "report generation: brief, digest, feed on the fixture store", "{py} -m memelab social feed-demo --fixture " + FIX + "/feed/demo_day.json", (0,)),
    ("13", "report generation: brief on the e2e store (real read path)", "{py} -m memelab social brief --db {db} --as-of 2026-10-13T00:00:00+00:00 --tz America/New_York --include-fixtures", (0,)),
    ("14", "alert dry run on the fixture day, deduped second run", "{py} -m memelab social alerts demo --fixture " + FIX + "/alerts/alerts_day.json", (0,)),
    ("14", "alert dry run on the e2e store", "{py} -m memelab social alerts run --db {db} --as-of 2026-10-13T12:00:00+00:00 --state {tmp}/alerts_dry.sqlite --outbox {tmp}/outbox", (0,)),
    ("14", "alert send without consent is refused", "{py} -m memelab social alerts run --db {db} --as-of 2026-10-13T13:30:00+00:00 --send --state {tmp}/alerts_send.sqlite --outbox {tmp}/outbox", (2,)),
    ("15", "forward outcome evaluation (ledger before and after two runs)", "{py} -m memelab social evaluate demo --fixture " + FIX + "/outcomes/outcomes_fixture.json", (0,)),
    ("16", "causal replay on the synthetic world", "{py} -m memelab social replay demo", (0,)),
    ("16", "causal replay on real stored history (copy of the tracked database)", "{py} -m memelab social replay run --db {tmp}/tracked_copy.sqlite", (0,)),
    ("17", "no credentials: X API health", "{py} -m memelab social x-health --db {db}", (1,)),
    ("17", "no credentials: live X ingest refuses before any call", "{py} -m memelab social x-ingest --db {db}", (1,)),
    ("17", "no credentials: Telegram health", "{py} -m memelab social tg-health --db {db}", (1,)),
    ("17", "no credentials: live Telegram ingest refuses before any call", "{py} -m memelab social tg-ingest --db {db}", (1,)),
    ("17", "no credentials: Helius key status", "{py} -m memelab.secrets status", (1,)),
    ("17", "no credentials: alert spend preflight", "{py} -m memelab social alerts preflight --db {db}", (0,)),
    ("18", "content guard over every tracked file", "{py} -m memelab social guard", (0,)),
]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "missing"


def _head(s: str, n: int) -> str:
    lines = s.rstrip("\n").splitlines()
    out = "\n".join(lines[:n])
    if len(lines) > n:
        out += f"\n... ({len(lines) - n} more lines)"
    return out


LEGACY_TABLES = ("watchlist", "theses", "entries", "rejections", "social_snapshots", "tokens")


def migrate_check(path: str) -> int:
    """Init (or re-init) one database from the current directory's code; print versions and legacy row counts."""
    import sqlite3
    sys.path.insert(0, os.getcwd())
    from memelab import db
    from memelab.social import schema

    def counts(con):
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in LEGACY_TABLES if t in names}

    existed = Path(path).exists()
    raw = sqlite3.connect(path)
    before = counts(raw)
    v0 = raw.execute("SELECT MAX(version) FROM social_schema_migrations").fetchone()[0] if "social_schema_migrations" in {
        r[0] for r in raw.execute("SELECT name FROM sqlite_master")} else 0
    raw.close()
    db.init_db(path)
    with db.connect(path) as con:
        after = counts(con)
        v1 = schema.current_version(con)
        rows = con.execute("SELECT COUNT(*) FROM social_schema_migrations").fetchone()[0]
    unchanged = before == after if existed else not any(after.values())
    print(json.dumps({"database_existed": existed, "social_version_before": v0 or 0, "social_version_after": v1,
                      "latest": schema.LATEST, "migration_rows": rows, "legacy_rows_before": before,
                      "legacy_rows_after": after, "legacy_unchanged": unchanged}, indent=1, sort_keys=True))
    return 0 if (v1 == schema.LATEST and unchanged) else 1


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--migrate-check"]:
        return migrate_check(argv[1])
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--out")
    ap.add_argument("--json")
    ap.add_argument("--keep", action="store_true", help="keep the temp folder")
    ap.add_argument("--skip-replay", action="store_true", help="skip the 35 s synthetic replay")
    ap.add_argument("--lines", type=int, default=25)
    a = ap.parse_args(argv)

    tmp = Path(tempfile.mkdtemp(prefix="memelab_release_"))
    clone = tmp / "clone"
    head = subprocess.run(["git", "-C", a.src, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "clone", "-q", "--local", "--no-hardlinks", a.src, str(clone)], check=True)
    subprocess.run(["git", "-C", str(clone), "checkout", "-q", head], check=True)
    guard = tmp / "netguard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(NETGUARD)
    netlog = tmp / "network_attempts.log"

    env = {k: v for k, v in os.environ.items() if k not in SECRET_VARS and not k.startswith("MEMELAB_")}
    env.update({
        "MEMELAB_DB": str(tmp / "e2e.sqlite"),
        "MEMELAB_PRIVATE_DB": str(tmp / "private" / "social_private.sqlite"),
        "MEMELAB_ALERT_DB": str(tmp / "private" / "alerts.sqlite"),
        "MEMELAB_ALERT_CONFIG": str(tmp / "private" / "alerts.json"),
        "MEMELAB_SIGNAL_LEDGER": str(tmp / "private" / "signal_ledger.sqlite"),
        "MEMELAB_LLM_CONFIG": str(tmp / "private" / "llm.json"),
        "PYTHONPATH": str(guard),
        "PYTHONDONTWRITEBYTECODE": "1",
        "RELEASE_NETGUARD_LOG": str(netlog),
        "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9",
        "http_proxy": "http://127.0.0.1:9", "https_proxy": "http://127.0.0.1:9", "NO_PROXY": "",
    })
    (tmp / "private").mkdir()
    tracked_db_before = _sha(clone / "data" / "memelab.sqlite")

    fmt = {"db": str(tmp / "e2e.sqlite"), "tmp": str(tmp), "py": shlex.quote(sys.executable), "me": shlex.quote(str(Path(__file__).resolve()))}
    results = []
    for sid, title, cmd, expect in STAGES:
        if a.skip_replay and "synthetic world" in title:
            continue
        line = cmd.format(**fmt)
        t0 = time.time()
        p = subprocess.run(["bash", "-c", line], cwd=clone, env=env, capture_output=True, text=True, timeout=900)
        dt = time.time() - t0
        shown = line.replace(str(Path(__file__).resolve()), "tools/release_e2e.py").replace(str(tmp), "$TMP").replace(sys.executable, "python")
        results.append({"stage": sid, "title": title, "command": shown, "exit": p.returncode, "expected": list(expect),
                        "ok": p.returncode in expect, "seconds": round(dt, 1),
                        "stdout": _head(p.stdout.replace(str(tmp), "$TMP"), a.lines),
                        "stderr": _head(p.stderr.replace(str(tmp), "$TMP"), 8)})
        print(f"[{'ok' if p.returncode in expect else 'FAIL'}] {sid} {title}: exit {p.returncode} ({dt:.1f}s)", file=sys.stderr)

    status = subprocess.run(["git", "-C", str(clone), "status", "--porcelain"], capture_output=True, text=True).stdout
    attempts = netlog.read_text() if netlog.exists() else ""
    checks = {
        "network_attempts": len(attempts.splitlines()),
        "network_attempt_lines": attempts.splitlines()[:20],
        "git_status_porcelain": status.splitlines(),
        "tracked_db_unchanged": _sha(clone / "data" / "memelab.sqlite") == tracked_db_before,
        "stages_ok": sum(r["ok"] for r in results), "stages_total": len(results),
    }
    ok = all(r["ok"] for r in results) and not attempts and not status.strip() and checks["tracked_db_unchanged"]
    summary = {"schema": "memelab.release.e2e/1", "commit": head, "python": sys.version.split()[0], "ok": ok,
               "checks": checks, "stages": results}

    md = [f"# Release end-to-end run", "", f"Commit `{head}`. Python {summary['python']}. Clean clone in a temp folder, "
          "network blocked by an audit hook, every credential variable removed, every database and private file in the temp folder.", "",
          f"Result: {'PASS' if ok else 'FAIL'}. Stages with the expected exit code: {checks['stages_ok']} of {checks['stages_total']}. "
          f"Network attempts: {checks['network_attempts']}. Tracked files changed in the clone: {len(checks['git_status_porcelain'])}. "
          f"Tracked database byte-identical: {'yes' if checks['tracked_db_unchanged'] else 'no'}.", ""]
    for r in results:
        md += [f"## {r['stage']} {r['title']}", "", "```", "$ " + r["command"], f"exit {r['exit']} (expected {', '.join(map(str, r['expected']))}), {r['seconds']} s",
               r["stdout"]]
        if r["stderr"].strip():
            md += ["--- stderr", r["stderr"]]
        md += ["```", ""]
    if checks["git_status_porcelain"]:
        md += ["## Stray files in the clone", "", "```", *checks["git_status_porcelain"], "```", ""]
    if attempts:
        md += ["## Network attempts", "", "```", *checks["network_attempt_lines"], "```", ""]
    text = "\n".join(md)
    text = re.sub(r"[ \t]+\n", "\n", text)
    if a.out:
        Path(a.out).write_text(text)
    else:
        print(text)
    if a.json:
        Path(a.json).write_text(json.dumps(summary, indent=1, sort_keys=True))
    if not a.keep:
        subprocess.run(["rm", "-rf", str(tmp)])
    else:
        print(f"kept {tmp}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
