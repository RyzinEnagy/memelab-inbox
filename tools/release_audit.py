"""Release audit (Phase 18): credential leakage, wallet keys, restricted social content, trade execution, network and
billable paths, schema compatibility and static checks. Read only.

Usage:
    python tools/release_audit.py [--history] [--main-ref origin/main] [--out FILE.md] [--json FILE.json]

  --history    also scan every blob reachable from any ref (public history), not only the tracked tree
  --main-ref   also run the content guard and a migration check on that ref's tree (default origin/main if it exists)

Prints locations and rule names, never a matched value. Exit 0 when nothing needs action, 1 when a finding needs a
person (credential shape, key material, trade-execution code, guard violation, migration failure, syntax error).
Pattern hits that are known and explained (see EXPLAINED) are listed as reviewed, not as findings.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# credential and key-material shapes; values are never printed
CRED = {
    "anthropic_key": re.compile(rb"sk-ant-[A-Za-z0-9_\-]{20,}"),
    "github_token": re.compile(rb"\b(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "telegram_bot_token": re.compile(rb"\b\d{8,10}:AA[A-Za-z0-9_\-]{33}\b"),
    "aws_key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "discord_bot_token": re.compile(rb"(?<![A-Za-z0-9_\-])[MNO][A-Za-z0-9_\-]{23,27}\.[A-Za-z0-9_\-]{6}\.[A-Za-z0-9_\-]{27,40}(?![A-Za-z0-9_\-])"),
    "google_api_key": re.compile(rb"(?<![A-Za-z0-9_\-])AIza[0-9A-Za-z_\-]{35}(?![A-Za-z0-9_\-])"),
    "google_oauth_token": re.compile(rb"\bya29\.[0-9A-Za-z_\-]{30,}"),
    "x_bearer": re.compile(rb"AAAAAAAAAAAAAAAAAAAAA[A-Za-z0-9%]{20,}"),
    "firecrawl_key": re.compile(rb"(?<![A-Za-z0-9_\-])fc-[0-9a-fA-F]{32}(?![A-Za-z0-9_\-])"),
    "pem_private_key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "api_key_param": re.compile(rb"api[-_]?key=([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[A-Za-z0-9_\-]{24,})"),
    "bearer_header": re.compile(rb"Bearer [A-Za-z0-9%._\-]{30,}"),
    "solana_keypair_array": re.compile(rb"\[\s*(?:\d{1,3}\s*,\s*){63}\d{1,3}\s*\]"),
    "key_material_field": re.compile(rb"""["'](?:private_?key|secret_?key|privateKey|secretKey|mnemonic|seed_?phrase|seedPhrase)["']\s*[:=]\s*["'][^"']{16,}["']"""),
}

# code that would sign, send or place anything; reviewed by hand when it matches
EXEC = re.compile(r"sendTransaction|sendRawTransaction|signTransaction|signAllTransactions|eth_sendRawTransaction|"
                  r"signAndSendTransaction|Keypair\b|from_secret_key|fromSecretKey|ethers\.Wallet|nacl\.sign\(|"
                  r"/swap-instructions|/v6/swap\b|/swap/v1/swap\b|window\.solana|window\.ethereum|place_?order|"
                  r"create_?order|submit_?order|executeSwap|execute_swap|mnemonic|seed phrase", re.I)

# reviewed hits: (path regex, rule regex, why it is not a finding)
EXPLAINED = [
    (r"^tests/test_secrets\.py$", r".*", "the secrets test builds key-shaped strings to prove the scanner catches them"),
    (r"^tools/release_audit\.py$", r".*", "this file holds the patterns"),
    (r"^memelab/secrets\.py$", r".*", "the key reader names the parameter; it holds no value"),
    (r"^docs/social-intelligence/.*\.md$", r"exec:.*", "documentation of the no-trading rule"),
    (r"^(README\.md|docs/.*\.md|skills/.*\.md)$", r"exec:(mnemonic|seed phrase|place_?order|create_?order)", "the hard rules text (never handle a seed phrase, never place an order)"),
    (r"^memelab/social/sigverify\.py$", r"exec:.*", "verify-only signature check, no signing code (D-059)"),
    (r"^tests/test_social_wallets\.py$", r"exec:.*", "tests that signing material is refused"),
    (r"^memelab/social/(content_guard|ingest|registry_import|alerts_core|outcomes_core|replay_core|research_core)\.py$", r"exec:.*", "refusal lists: keys or words the lab rejects"),
]

SOCIAL_LOGIN_HOSTS = re.compile(r"(api\.x\.com|api\.twitter\.com|api\.telegram\.org|api\.anthropic\.com|smtp\.|oauth\.reddit\.com|www\.reddit\.com|discord\.com/api|www\.googleapis\.com/youtube|api\.firecrawl\.dev)")


def run(cmd, cwd=ROOT, check=False):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def explained(path: str, rule: str) -> str | None:
    for pr, rr, why in EXPLAINED:
        if re.search(pr, path) and re.fullmatch(rr, rule):
            return why
    return None


def scan_bytes(path: str, data: bytes, out: list, reviewed: list) -> None:
    for name, rx in CRED.items():
        for m in rx.finditer(data):
            line = data.count(b"\n", 0, m.start()) + 1
            why = explained(path, name)
            body = re.sub(rb"^(\d+:AA|sk-ant-|gh[pousr]_|github_pat_|AKIA|api[-_]?key=|Bearer )", b"", m.group(0))
            if not why and len(set(body)) < 8:
                why = "placeholder shape, not a credential (fewer than 8 distinct characters)"
            (reviewed if why else out).append({"path": path, "line": line, "rule": name, **({"why": why} if why else {})})


def tracked_files() -> list[str]:
    return [p for p in run(["git", "ls-files"]).stdout.splitlines() if p]


def scan_tree() -> tuple[list, list]:
    out, rev = [], []
    for p in tracked_files():
        fp = ROOT / p
        if fp.is_file() and fp.stat().st_size < 50_000_000:
            scan_bytes(p, fp.read_bytes(), out, rev)
    return out, rev


def scan_history() -> tuple[list, list, int]:
    objs = run(["git", "rev-list", "--objects", "--all"]).stdout.splitlines()
    seen, out, rev = set(), [], []
    batch = subprocess.Popen(["git", "cat-file", "--batch"], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    n = 0
    for line in objs:
        parts = line.split(" ", 1)
        if len(parts) < 2 or parts[0] in seen:
            continue
        sha, path = parts
        seen.add(sha)
        batch.stdin.write((sha + "\n").encode())
        batch.stdin.flush()
        hdr = batch.stdout.readline().split()
        size = int(hdr[2])
        data = batch.stdout.read(size)
        batch.stdout.read(1)
        if hdr[1] != b"blob":
            continue
        n += 1
        scan_bytes(f"{path} (blob {sha[:10]})", data, out, rev)
    batch.stdin.close()
    batch.wait()
    # a blob reviewed under its path is reviewed in history too
    keep = []
    for f in out:
        p = f["path"].split(" (blob ")[0]
        why = explained(p, f["rule"])
        (rev if why else keep).append({**f, **({"why": why} if why else {})})
    return keep, rev, n


def scan_exec() -> tuple[list, list]:
    out, rev = [], []
    for p in tracked_files():
        if not re.search(r"\.(py|js|sh|md)$", p):
            continue
        txt = (ROOT / p).read_text(errors="replace")
        for i, l in enumerate(txt.splitlines(), 1):
            for m in EXEC.finditer(l):
                rule = "exec:" + m.group(0).lower()
                why = explained(p, rule)
                (rev if why else out).append({"path": p, "line": i, "rule": rule, **({"why": why} if why else {})})
    return out, rev


def network_paths() -> list[dict]:
    rows = []
    for p in tracked_files():
        if not p.endswith((".py", ".js")) or p.startswith("tests/"):
            continue
        txt = (ROOT / p).read_text(errors="replace")
        libs = sorted(set(re.findall(r"\b(urllib\.request|http\.client|import requests|smtplib|import socket|fetch\(|https?\.request|XMLHttpRequest)", txt)))
        if libs:
            hosts = sorted(set(SOCIAL_LOGIN_HOSTS.findall(txt)))
            rows.append({"path": p, "uses": libs, "paid_or_credentialed_hosts": hosts})
    return rows


LOCAL_PATH = re.compile(rb"(/tmp/claude-[^\"'\s]*|/root/[^\"'\s]*|/home/[a-z_][a-z0-9_-]*/[^\"'\s]*|[A-Z]:\\\\Users\\\\[^\"'\s]*)")


def local_paths(tree: Path = ROOT) -> list[dict]:
    """Absolute local paths (session folders, home folders) in tracked data files; counts only."""
    out = []
    for p in run(["git", "ls-files"], cwd=tree).stdout.splitlines():
        if not p.startswith(("data/", "state/", "inbox/")) or not (tree / p).is_file():
            continue
        data = (tree / p).read_bytes()
        n = len(LOCAL_PATH.findall(data))
        if n:
            out.append({"path": p, "count": n})
    return out


def billing_defaults() -> dict:
    out = {}
    for f in sorted([*(ROOT / "docs" / "social-intelligence").glob("*.example.json"), *(ROOT / "docs" / "catalyst").glob("*.example.json")]):
        d = json.loads(f.read_text())
        flat = json.dumps(d)
        out[f.name] = {"allow_billable_true": bool(re.search(r'"allow_billable":\s*true', flat)) or bool(re.search(r'"enabled":\s*true', flat) and "firecrawl" in f.name),
                       "send_enabled_true": bool(re.search(r'"(send_enabled|notifications_opt_in)":\s*true', flat)),
                       "holds_secret_key": bool(re.search(r'"(token|api_key|password|secret|bearer)"\s*:', flat, re.I))}
    return out


def guard_on(tree: Path | None) -> dict:
    cmd = [sys.executable, "-m", "memelab", "social", "guard"]
    p = run(cmd, cwd=tree or ROOT)
    return {"exit": p.returncode, "tail": (p.stdout + p.stderr).strip().splitlines()[-3:]}


def migrate_on(dbfile: Path) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="memelab_audit_"))
    shutil.copy(dbfile, tmp / "copy.sqlite")
    p = run([sys.executable, str(ROOT / "tools" / "release_e2e.py"), "--migrate-check", str(tmp / "copy.sqlite")])
    shutil.rmtree(tmp)
    try:
        return {"exit": p.returncode, **json.loads(p.stdout)}
    except ValueError:
        return {"exit": p.returncode, "error": (p.stderr or p.stdout)[-400:]}


def static_checks() -> dict:
    py = [p for p in tracked_files() if p.endswith(".py")]
    js = [p for p in tracked_files() if p.endswith(".js")]
    bad_py = []
    for p in py:
        r = run([sys.executable, "-c", "import ast,sys; ast.parse(open(sys.argv[1]).read(), sys.argv[1])", p])
        if r.returncode:
            bad_py.append(p)
    node = shutil.which("node")
    bad_js = [p for p in js if node and run([node, "--check", p]).returncode]
    pyflakes = None
    try:
        import pyflakes  # noqa: F401
        r = run([sys.executable, "-m", "pyflakes", *py])
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        kinds: dict[str, int] = {}
        for l in lines:
            k = re.sub(r"^[^:]+:\d+:(\d+:)? ", "", l)
            k = re.sub(r"'[^']*'", "'X'", k)
            kinds[k] = kinds.get(k, 0) + 1
        serious = [l for l in lines if re.search(r"undefined name|syntax error|invalid syntax|redefinition of unused", re.sub(r"^[^:]+:\d+:(\d+:)? ", "", l))]
        pyflakes = {"messages": len(lines), "by_kind": dict(sorted(kinds.items(), key=lambda kv: -kv[1])[:12]),
                    "undefined_or_syntax": serious}
    except ImportError:
        pyflakes = "not installed (pip install pyflakes)"
    return {"python_files": len(py), "python_syntax_errors": bad_py, "js_files": len(js),
            "js_syntax_errors": bad_js if node else "node not found", "pyflakes": pyflakes}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--main-ref", default="origin/main")
    ap.add_argument("--out")
    ap.add_argument("--json")
    a = ap.parse_args(argv)

    head = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    cred, cred_rev = scan_tree()
    hist = hist_rev = None
    blobs = 0
    if a.history:
        hist, hist_rev, blobs = scan_history()
    exe, exe_rev = scan_exec()
    res = {"schema": "memelab.release.audit/1", "commit": head,
           "credentials_tracked": cred, "credentials_tracked_reviewed": cred_rev,
           "credentials_history": hist, "credentials_history_reviewed": hist_rev, "history_blobs_scanned": blobs,
           "trade_execution": exe, "trade_execution_reviewed": exe_rev,
           "local_paths_head": local_paths(), "network_paths": network_paths(), "example_config_defaults": billing_defaults(),
           "guard_head": guard_on(None), "migrate_tracked_db": migrate_on(ROOT / "data" / "memelab.sqlite"),
           "static": static_checks()}
    main_ok = run(["git", "rev-parse", "--verify", a.main_ref]).returncode == 0
    if main_ok:
        tmp = Path(tempfile.mkdtemp(prefix="memelab_audit_main_"))
        run(["git", "worktree", "add", "--detach", "-q", str(tmp / "wt"), a.main_ref])
        try:
            # the guard of this branch, applied to the main tree
            g = run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); from memelab.social import content_guard as g; "
                     "from pathlib import Path; r = g.scan(Path(sys.argv[2])); print(len(r.get('violations', r) if isinstance(r, dict) else r))",
                     str(ROOT), str(tmp / "wt")])
            res["guard_main"] = {"ref": a.main_ref, "commit": run(["git", "rev-parse", a.main_ref]).stdout.strip(),
                                 "exit": g.returncode, "violations": g.stdout.strip(), "error": g.stderr.strip()[-300:]}
            res["migrate_main_db"] = migrate_on(tmp / "wt" / "data" / "memelab.sqlite")
            res["local_paths_main"] = local_paths(tmp / "wt")
        finally:
            run(["git", "worktree", "remove", "--force", str(tmp / "wt")])
            shutil.rmtree(tmp, ignore_errors=True)
    st = res["static"]
    needs = bool(cred or hist or exe or res["guard_head"]["exit"] or res["migrate_tracked_db"].get("exit")
                 or st["python_syntax_errors"] or (isinstance(st["js_syntax_errors"], list) and st["js_syntax_errors"])
                 or any(v["allow_billable_true"] or v["send_enabled_true"] or v["holds_secret_key"] for v in res["example_config_defaults"].values())
                 or (main_ok and (res.get("migrate_main_db", {}).get("exit") or res.get("guard_main", {}).get("violations") not in ("0",))))
    res["needs_action"] = needs
    text = json.dumps(res, indent=1, sort_keys=True)
    if a.json:
        Path(a.json).write_text(text)
    if a.out:
        Path(a.out).write_text(render(res))
    if not a.out and not a.json:
        print(render(res))
    return 1 if needs else 0


def render(r: dict) -> str:
    def rows(lst):
        return [f"- `{x['path']}` line {x['line']}: {x['rule']}" + (f" (reviewed: {x['why']})" if x.get("why") else "") for x in lst] or ["- none"]
    st = r["static"]
    pf = st["pyflakes"]
    L = ["# Release audit", "", f"Commit `{r['commit']}`. Generated by `python tools/release_audit.py --history`. Values are never printed, only locations and rule names.", "",
         f"Needs action: {'yes' if r['needs_action'] else 'no'}.", "",
         "## Credential and key-material shapes in tracked files", "", *rows(r["credentials_tracked"]), "",
         "Reviewed, not findings:", "", *rows(r["credentials_tracked_reviewed"]), ""]
    if r["credentials_history"] is not None:
        L += [f"## The same shapes in public history ({r['history_blobs_scanned']} blobs from every ref)", "", *rows(r["credentials_history"]), "",
              f"Reviewed hits in history: {len(r['credentials_history_reviewed'])} (same reasons as above).", ""]
    L += ["## Trade-execution and signing code", "", *rows(r["trade_execution"]), "", "Reviewed, not findings:", "", *rows(r["trade_execution_reviewed"]), "",
          "## Network paths (non-test code)", "", "| File | Uses | Credentialed or paid hosts named |", "|---|---|---|"]
    L += [f"| `{n['path']}` | {', '.join(n['uses'])} | {', '.join(n['paid_or_credentialed_hosts']) or '-'} |" for n in r["network_paths"]]
    L += ["", "## Local paths in tracked data (informational; written by the scheduled runs, not by this branch)", ""]
    for k in ("local_paths_head", "local_paths_main"):
        if k in r:
            L.append(f"- {k}: " + (", ".join(f"`{x['path']}` {x['count']}" for x in r[k]) or "none"))
    L += ["", "## Example config defaults", "", "| File | allow_billable true | send or opt-in true | holds a secret key |", "|---|---|---|---|"]
    L += [f"| `{k}` | {v['allow_billable_true']} | {v['send_enabled_true']} | {v['holds_secret_key']} |" for k, v in r["example_config_defaults"].items()]
    L += ["", "## Content guard and migrations", "",
          f"- guard on this branch: exit {r['guard_head']['exit']} ({'; '.join(r['guard_head']['tail'])})"]
    if "guard_main" in r:
        g = r["guard_main"]
        L.append(f"- this branch's guard applied to `{g['ref']}` at `{g['commit'][:7]}`: violations {g['violations'] or '?'}" + (f", error {g['error']}" if g["error"] else ""))
    for k in ("migrate_tracked_db", "migrate_main_db"):
        if k in r:
            m = r[k]
            L.append(f"- {k}: exit {m['exit']}, social schema {m.get('social_version_before')} -> {m.get('social_version_after')} (latest {m.get('latest')}), legacy rows unchanged {m.get('legacy_unchanged')}"
                     + (f", error {m['error']}" if m.get("error") else ""))
    L += ["", "## Static checks", "", f"- Python files {st['python_files']}, syntax errors {len(st['python_syntax_errors'])} {st['python_syntax_errors'] or ''}",
          f"- JavaScript files {st['js_files']}, `node --check` errors {st['js_syntax_errors'] if isinstance(st['js_syntax_errors'], str) else len(st['js_syntax_errors'])}"]
    if isinstance(pf, dict):
        L.append(f"- pyflakes: {pf['messages']} messages; undefined names or syntax: {len(pf['undefined_or_syntax'])}")
        L += [f"  - {k}: {v}" for k, v in pf["by_kind"].items()]
        L += [f"  - {x}" for x in pf["undefined_or_syntax"]]
    else:
        L.append(f"- pyflakes: {pf}")
    L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
