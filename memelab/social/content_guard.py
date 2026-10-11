"""Repo-wide guard: no raw third-party social content in tracked files (DECISIONS D-010, D-013, D-016).

The repo is public, so anything tracked is published. This check walks the tracked files (git ls-files) and
fails when it finds a blocked content class. It reports file, location and rule only, never the value.

Rules
  PATH      no tracked file under data/private/, data/wallet/ or any quarantine/ folder; no tracked SQLite file
            other than data/memelab.sqlite
  JSON      in a social inbox unit ("soc:*" key): no blocked key (ingest.BLOCKED_KEYS) in the envelope, items or
            accounts; every item PUBLIC; summary at most 400 characters
            anywhere in any JSON file: no key that only ever holds social content (SOCIAL_ONLY_KEYS), e.g. "bio"
            from an X profile projection, "full_text", "members"
  SQLITE    in data/memelab.sqlite: no social_* column named like a content field; no private_content table;
            summaries at most 400 characters; social_snapshots.text_value short labels only (no prose);
            catalyst_sources.identity_notes without copied profile text
  ALLOW     explicit entries for invented test fixtures, each with a reason

Scope: generic keys such as "text", "title", "description" or "quote" are not flagged outside social units,
because in this repo they hold lab-written alerts, news headlines (AUDIT_00), token metadata written by the
issuer, or a pool's quote token. Markdown reports are lab-written and not scanned.

Usage: python -m memelab social guard [--root <repo>]   (exit 0 clean, 1 violations)
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path

from .ingest import BLOCKED_KEYS
from .store import SUMMARY_MAX

SOCIAL_ONLY_KEYS = {"bio", "full_text", "raw_text", "post_text", "tweet_text", "message_text", "dm", "dms",
                    "members", "member_list", "transcript", "screenshot", "exact_text"}
CONTENT_COLUMNS = {"text", "raw_text", "full_text", "exact_text", "post_text", "bio", "body", "html", "content",
                   "message", "quote", "transcript"}
TRACKED_DB = "data/memelab.sqlite"
PROSE_WORDS = 12          # social_snapshots.text_value longer than this many words reads as copied prose

# (path glob, JSON location glob, reason). Locations look like "soc:x:example_trader_a.body.items[3].text".
ALLOW = [
    ("tests/fixtures/social/inbox/soc_fx01.json", "soc:x:example_trader_a.body.items[3].text",
     "invented placeholder the ingester must quarantine (test_bad_items_quarantined_good_items_kept)"),
    ("tests/fixtures/social/inbox/soc_fx01.json", "soc:x:example_trader_a.body.items[4].visibility",
     "invented PROTECTED item (hash of an invented sentence) the ingester must quarantine as NOT_PUBLIC"),
    ("tests/fixtures/social/roundtrip_01.json", "observations[*].text",
     "invented sentences used to prove the store hashes text and never writes it (Phase 01)"),
]


@dataclass
class Violation:
    path: str
    where: str
    rule: str


def _glob(pattern: str, s: str) -> bool:
    """'*' matches anything; every other character, brackets included, is literal."""
    return re.fullmatch(".*".join(re.escape(x) for x in pattern.split("*")), s) is not None


def _allowed(path: str, where: str) -> bool:
    return any(_glob(p, path) and _glob(w, where) for p, w, _ in ALLOW)


def tracked_files(root: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True)
    return [p for p in out.stdout.decode().split("\0") if p]


def check_paths(paths: list[str]) -> list[Violation]:
    v = []
    for p in paths:
        parts = p.split("/")
        if p.startswith(("data/private/", "data/wallet/")) or "quarantine" in parts[:-1]:
            v.append(Violation(p, "", "PATH: private, wallet or quarantine file is tracked"))
        elif re.search(r"\.sqlite3?$|\.db$", p) and p != TRACKED_DB:
            v.append(Violation(p, "", "PATH: SQLite file other than data/memelab.sqlite is tracked"))
    return v


def _walk(o, where: str, path: str, out: list[Violation]) -> None:
    if isinstance(o, dict):
        for k, x in o.items():
            loc = f"{where}.{k}" if where else str(k)
            if isinstance(k, str) and k.lower() in SOCIAL_ONLY_KEYS and x not in (None, "", [], {}) and not _allowed(path, loc):
                out.append(Violation(path, loc, f"JSON: social-only content key '{k}'"))
            _walk(x, loc, path, out)
    elif isinstance(o, list):
        for i, x in enumerate(o):
            _walk(x, f"{where}[{i}]", path, out)


def _check_unit(key: str, entry, path: str, out: list[Violation]) -> None:
    if not isinstance(entry, dict):
        return
    body = entry.get("body")
    if not isinstance(body, dict):
        return
    for k in sorted(BLOCKED_KEYS & set(body)):
        if not _allowed(path, f"{key}.body.{k}"):
            out.append(Violation(path, f"{key}.body.{k}", f"JSON: blocked content class '{k}' in a social unit"))
    src = body.get("source") if isinstance(body.get("source"), dict) else {}
    items = body.get("items") if isinstance(body.get("items"), list) else []
    for i, it in enumerate(items):
        base = f"{key}.body.items[{i}]"
        if not isinstance(it, dict):
            continue
        acct = it.get("account") if isinstance(it.get("account"), dict) else {}
        for k in sorted(BLOCKED_KEYS & set(it)):
            if not _allowed(path, f"{base}.{k}"):
                out.append(Violation(path, f"{base}.{k}", f"JSON: blocked content class '{k}' in a social item"))
        for k in sorted(BLOCKED_KEYS & set(acct)):
            if not _allowed(path, f"{base}.account.{k}"):
                out.append(Violation(path, f"{base}.account.{k}", f"JSON: blocked content class '{k}' in an account"))
        vis = it.get("visibility", src.get("visibility"))
        if vis != "PUBLIC" and not _allowed(path, f"{base}.visibility"):
            # a tracked non-public item is a leak even if the ingester would quarantine it
            if any(k in it for k in ("content_hash", "summary", "metrics", "url", "provider_item_id")):
                out.append(Violation(path, f"{base}.visibility", "JSON: non-public social item in a tracked file"))
        s = it.get("summary")
        if isinstance(s, str) and len(s) > SUMMARY_MAX:
            out.append(Violation(path, f"{base}.summary", f"JSON: summary longer than {SUMMARY_MAX} characters"))


def check_json(path: str, data) -> list[Violation]:
    out: list[Violation] = []
    _walk(data, "", path, out)
    if isinstance(data, dict):
        for k, entry in data.items():
            if isinstance(k, str) and k.startswith("soc:"):
                _check_unit(k, entry, path, out)
    seen, uniq = set(), []
    for v in out:
        if (v.where, v.rule) not in seen:
            seen.add((v.where, v.rule))
            uniq.append(v)
    return uniq


def check_sqlite(path: str, file: Path) -> list[Violation]:
    out: list[Violation] = []
    con = sqlite3.connect(f"file:{file}?mode=ro&immutable=1", uri=True)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "private_content" in tables:
            out.append(Violation(path, "private_content", "SQLITE: private store table inside the public database"))
        for t in sorted(x for x in tables if x.startswith("social_")):
            for col in (r[1] for r in con.execute(f"PRAGMA table_info({t})")):
                if col.lower() in CONTENT_COLUMNS:
                    out.append(Violation(path, f"{t}.{col}", "SQLITE: content column in a social table"))
        for t in ("social_observations", "social_claims"):
            if t in tables:
                n = con.execute(f"SELECT COUNT(*) FROM {t} WHERE length(summary) > ?", (SUMMARY_MAX,)).fetchone()[0]
                if n:
                    out.append(Violation(path, f"{t}.summary", f"SQLITE: {n} summaries longer than {SUMMARY_MAX} characters"))
        if "social_snapshots" in tables:
            for rid, tv in con.execute("SELECT rowid, text_value FROM social_snapshots WHERE text_value IS NOT NULL"):
                if len(re.findall(r"\w+", str(tv))) > PROSE_WORDS:
                    out.append(Violation(path, f"social_snapshots[rowid={rid}].text_value", "SQLITE: prose in social_snapshots.text_value"))
        if "catalyst_sources" in tables:
            cols = {r[1] for r in con.execute("PRAGMA table_info(catalyst_sources)")}
            if "identity_notes" in cols:
                for sid, in con.execute("SELECT source_id FROM catalyst_sources WHERE identity_notes LIKE '%profile:%'"):
                    out.append(Violation(path, f"catalyst_sources[{sid}].identity_notes", "SQLITE: copied profile title/bio text"))
    finally:
        con.close()
    return out


def scan(root: Path | str, paths: list[str] | None = None) -> dict:
    """Scan tracked files under root. Returns {"files_scanned", "json_files", "sqlite_files", "violations": [...]}."""
    root = Path(root)
    paths = tracked_files(root) if paths is None else paths
    v = check_paths(paths)
    nj = ns = 0
    for p in paths:
        f = root / p
        if not f.is_file():
            continue
        if p.endswith(".json"):
            nj += 1
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue  # not our concern here; invalid JSON is caught by the modules that read it
            v += check_json(p, data)
        elif p == TRACKED_DB:
            ns += 1
            v += check_sqlite(p, f)
    return {"files_scanned": len(paths), "json_files": nj, "sqlite_files": ns, "violations": [asdict(x) for x in v],
            "allowlist": [{"path": p, "where": w, "reason": r} for p, w, r in ALLOW]}
