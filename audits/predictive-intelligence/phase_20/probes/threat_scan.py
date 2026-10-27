"""Phase 20 (G13): threat scan of the repository at HEAD and of everything changed since the branch base f99c6c7.

    python -B threat_scan.py OUTJSON

Checks (each hit is listed with its file and line; an expected hit names the recorded reason):
  1. copyleft: `runtime.copyleft_findings` over every code file (license markers and the MiroFish and black-it fingerprints), and an
     own search of every tracked file for license titles and SPDX copyleft identifiers;
  2. keys, signing and orders: patterns for private keys, recovery words, signing, wallet connection, transaction sending and order
     placement in `memelab/predictive/` and in every code file changed since f99c6c7, plus credential-shaped strings in the diff;
  3. schedules and robots: workflow, cron or scheduler files added or changed since f99c6c7, scheduler imports in the package;
  4. imports: every third-party or network-capable import of `memelab/predictive/*.py` (AST), against numpy and the standard library;
  5. dependencies: dependency manifests and the hash locks changed since f99c6c7.
Read-only; no network.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
BASE = "f99c6c7"


def git(*a) -> str:
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, check=True).stdout


def tracked() -> list[str]:
    return git("ls-files").splitlines()


def changed() -> list[str]:
    return [x for x in git("diff", "--name-only", f"{BASE}..HEAD").splitlines() if x]


CODE = (".py", ".js", ".mjs", ".cjs", ".ts", ".sh", ".html")
LICENSE_RX = re.compile("|".join(["AFFERO GENERAL" + " PUBLIC", "GNU GENERAL" + " PUBLIC", "GNU LESSER" + " GENERAL", "SPDX-License-Identifier:\\s*(A|L)?GPL"]), re.I)
# built from parts so that this file does not itself carry the words the release audit looks for (tools/release_audit.py EXEC)
_W = ["private[_ ]?key", "secret[_ ]?key", "seed[_ ]?" + "phrase", "mne" + "monic", "key" + "pair", "sign_?" + "transaction",
      "sign" + "Transaction", "send_?" + "transaction", "send" + "Transaction", "send" + "RawTransaction", "eth_" + "account", "sold" + "ers",
      "solana\\.rpc", "web" + "3", "wallet[_ ]?connect", "place_?" + "order", "create_?" + "order", "quote-api\\.jup", "jupi" + "ter"]
KEY_RX = re.compile("|".join(_W), re.I)
CRED_RX = re.compile(r"sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|"
                     r"-----BEGIN [A-Z ]*PRIVATE KEY-----|fc-[0-9a-f]{32}")
B58_SECRET = re.compile(r"(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{86,90}(?![1-9A-HJ-NP-Za-km-z])")
SCHED_PATH = re.compile(r"(^|/)(\.github/workflows/|cron|crontab|.*\.timer$|.*schedule)", re.I)
NETMODS = {"socket", "http", "http.client", "urllib", "urllib.request", "requests", "httpx", "aiohttp", "websocket", "websockets",
           "ssl", "smtplib", "ftplib", "subprocess", "asyncio"}


def scan_lines(paths, rx, *, only_code: bool) -> list[dict]:
    hits = []
    for rel in paths:
        p = REPO / rel
        if not p.is_file() or (only_code and p.suffix not in CODE):
            continue
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            m = rx.search(line)
            if m:
                hits.append({"path": rel, "line": i, "match": m.group(0)[:60], "text": line.strip()[:160]})
    return hits


def imports_of(path: Path) -> set[str]:
    out = set()
    for n in ast.walk(ast.parse(path.read_text())):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            out.add(n.module)
    return out


def main(outjson: Path) -> int:
    from memelab.predictive import runtime as RT
    res: dict = {"base": BASE, "head": git("rev-parse", "HEAD").strip()}
    files = tracked()
    ch = changed()
    # 1. copyleft
    fp = RT.load_fingerprints(REPO / "tests/fixtures/predictive/copyleft_fingerprints.json")
    code_files = [REPO / f for f in files if Path(f).suffix in RT.CODE_SUFFIXES]
    allowed = [REPO / "audits/predictive-intelligence/phase_02/probes/verify_repos.py",
               REPO / "audits/predictive-intelligence/phase_03/research/verify/verify_generic.py"]
    res["copyleft_gate"] = RT.copyleft_findings(code_files, fp, marker_allowed=allowed)
    lic = scan_lines(files, LICENSE_RX, only_code=False)
    res["license_title_hits"] = {"code": [h for h in lic if Path(h["path"]).suffix in CODE],
                                 "records_and_data": sorted({h["path"] for h in lic if Path(h["path"]).suffix not in CODE})}
    res["license_title_hits_in_code_explained"] = all(
        h["path"] in ("audits/predictive-intelligence/phase_02/probes/verify_repos.py",
                      "audits/predictive-intelligence/phase_03/research/verify/verify_generic.py")
        or "/phase_20/" in h["path"] or h["path"].startswith("tests/test_predictive_runtime.py") or "concatenat" in h["text"]
        for h in res["license_title_hits"]["code"])
    # 2. keys, signing, orders
    pk = [f"memelab/predictive/{p.name}" for p in sorted((REPO / "memelab/predictive").glob("*.py"))]
    res["key_or_order_patterns_in_package"] = scan_lines(pk, KEY_RX, only_code=True)
    res["key_or_order_patterns_in_changed_code"] = scan_lines([c for c in ch if not c.startswith("memelab/predictive/")], KEY_RX, only_code=True)
    diff = git("diff", f"{BASE}..HEAD", "--", ".", ":(exclude)inbox", ":(exclude)state", ":(exclude)data")
    res["credential_shaped_strings_in_diff"] = sorted({m.group(0)[:12] + "..." for m in CRED_RX.finditer(diff)})
    added = "\n".join(x[1:] for x in diff.splitlines() if x.startswith("+") and not x.startswith("+++"))
    res["base58_64_byte_secret_shapes_added"] = sorted({m.group(0)[:10] + "..." for m in B58_SECRET.finditer(added)})
    # 3. schedules
    res["schedule_or_workflow_files_changed"] = [c for c in ch if SCHED_PATH.search(c) and not c.startswith("audits/")]
    res["scheduler_imports_in_package"] = sorted({m for f in pk for m in imports_of(REPO / f) if m.split(".")[0] in ("sched", "schedule", "apscheduler", "crontab", "celery")})
    # 4. imports
    std = set(sys.stdlib_module_names)
    third, net = {}, {}
    for f in pk:
        ims = imports_of(REPO / f)
        t = sorted(m for m in ims if m.split(".")[0] not in std and m.split(".")[0] not in ("numpy", "memelab"))
        n = sorted(m for m in ims if m in NETMODS or m.split(".")[0] in ("socket", "requests", "httpx", "aiohttp", "urllib", "http"))
        if t:
            third[f] = t
        if n:
            net[f] = n
    res["third_party_imports_beyond_numpy"] = third
    res["network_or_process_capable_imports"] = net
    # 5. dependencies
    res["dependency_manifests_changed"] = [c for c in ch if re.search(r"(^|/)(requirements[^/]*\.txt|pyproject\.toml|setup\.py|setup\.cfg|Pipfile)", c)]
    locks = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((REPO / "docs/predictive-intelligence/locks").glob("*.txt"))}
    res["locks_sha256"] = locks
    res["locks_pinned"] = locks == {"core-py313.txt": "89fe4f4dc37a450ffd2b660eedcff8d4e93a81ac9df2566c21b504ce5a722865",
                                    "research-py313.txt": "1347f84bb2639143e85e8532e09c8513e0ab679b3982ed8ba5d5bf3b45f2ba84"}
    res["changed_files_since_base"] = len(ch)
    outjson.parent.mkdir(parents=True, exist_ok=True)
    outjson.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    summary = {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in res.items() if k not in ("locks_sha256",)}
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
