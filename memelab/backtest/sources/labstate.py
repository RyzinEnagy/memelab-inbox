"""Frozen discovery universe from the lab's own exported history (git versions of the state file).

Each daily scan commits `data/state/latest.json` (earlier: `state/latest.json`). A single export is trimmed
(theses capped per mint), so the universe is the union across every committed version. For each record:
- entered_at / available_at = the lab's own observation time (thesis created_at, rejection rejected_at);
- committed_by = the commit time of the first export that contains it (an independent upper bound proving the
  record was not written later).
Rejected tokens and tokens that later died stay in the universe: that is the survivorship defense.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable

from .. import store
from ..timeguard import utc_ts

STATE_PATHS = ("data/state/latest.json", "state/latest.json")
DISCOVERY_RULE = ("lab daily discovery scan (memelab discover -> stage2 -> scout); members are every token the lab analyzed "
                  "(thesis) or rejected (structural, deep, stage2-evm) as exported in the state file; chain inferred from the address "
                  "format when not stored (0x... = EVM, otherwise Solana)")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def state_versions(repo: Path, ref: str = "origin/main") -> list[tuple[str, float, str]]:
    """(commit, commit_time, path) for every committed version of the state file, oldest first."""
    out = []
    for path in STATE_PATHS:
        try:
            log = _git(repo, "log", "--format=%H %ct", ref, "--", path)
        except subprocess.CalledProcessError:
            continue
        for line in log.splitlines():
            if line.strip():
                h, ct = line.split()
                out.append((h, float(ct), path))
    out.sort(key=lambda x: x[1])
    return out


def load_version(repo: Path, commit: str, path: str) -> dict | None:
    try:
        d = json.loads(_git(repo, "show", f"{commit}:{path}"))
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None
    return d.get("_tables", d)


def chain_of(mint: str, stored: str | None = None) -> str:
    if stored:
        return stored
    return "evm-unknown" if mint.lower().startswith("0x") else "solana"


def members_from_tables(t: dict, commit: str | None, commit_time: float | None) -> Iterable[dict]:
    toks = {x["mint"]: x for x in t.get("tokens", [])}
    for th in t.get("theses", []):
        m = th["mint"]
        snap = json.loads(th["snapshot_json"]) if th.get("snapshot_json") else None
        fatal = json.loads(th["fatal_flags_json"]) if th.get("fatal_flags_json") else []
        yield dict(chain=chain_of(m, (toks.get(m) or {}).get("chain")), mint=m, symbol=(toks.get(m) or {}).get("symbol"), basis="THESIS",
                   entered_at=utc_ts(th["created_at"]), committed_by=commit_time, source_commit=commit, status_at_entry=th.get("status"),
                   score_at_entry=th.get("score"), fatal_flags=[f.get("flag") if isinstance(f, dict) else f for f in fatal], snapshot=snap, stage="deep")
    for r in t.get("rejections", []):
        m = r["mint"]
        yield dict(chain=chain_of(m, (toks.get(m) or {}).get("chain")), mint=m, symbol=r.get("symbol"), basis="REJECTION",
                   entered_at=utc_ts(r["rejected_at"]), committed_by=commit_time, source_commit=commit, status_at_entry="REJECTED",
                   score_at_entry=None, fatal_flags=None, snapshot={"why_failed": r.get("why_failed"), "evidence": r.get("evidence"), "why_surfaced": r.get("why_surfaced")},
                   stage=r.get("stage"))


def build_universe(con, repo: Path, universe_id: str = "lab_state_history", ref: str = "origin/main") -> dict:
    """Write the union of all exported theses/rejections into bt_universe_members. Idempotent.
    committed_by is the FIRST commit containing the record (inserts from later commits are no-ops)."""
    store.ensure(con)
    versions = state_versions(repo, ref)
    stats = {"versions": len(versions), "read_ok": 0, "inserted": 0, "seen": 0, "first_commit": None, "last_commit": None}
    for commit, ct, path in versions:
        t = load_version(repo, commit, path)
        if t is None:
            continue
        stats["read_ok"] += 1
        stats["first_commit"] = stats["first_commit"] or commit
        stats["last_commit"] = commit
        for mem in members_from_tables(t, commit, ct):
            stats["seen"] += 1
            if mem["committed_by"] is not None and mem["entered_at"] > mem["committed_by"] + 1:
                mem["snapshot"] = {**(mem["snapshot"] or {}), "_anomaly": "entered_at after commit time"}
            _, ins = store.record_universe_member(con, universe_id=universe_id, **mem)
            stats["inserted"] += ins
        for tok in t.get("tokens", []):
            if tok.get("decimals") is not None and tok.get("first_seen_at"):
                store.record_asset_version(con, chain=chain_of(tok["mint"], tok.get("chain")), mint=tok["mint"], symbol=tok.get("symbol"),
                                           decimals=tok.get("decimals"), token_program=tok.get("token_program"),
                                           observed_at=utc_ts(tok["first_seen_at"]), source=f"labstate:{commit[:12]}")
    con.commit()
    return stats


def universe_summary(con, universe_id: str = "lab_state_history") -> dict:
    q = lambda sql, *a: con.execute(sql, a).fetchall()
    rows = q("SELECT chain, basis, COUNT(*) n, COUNT(DISTINCT mint) m, MIN(entered_at) t0, MAX(entered_at) t1 FROM bt_universe_members WHERE universe_id=? GROUP BY chain, basis", universe_id)
    return {"by_chain_basis": [dict(r) for r in rows],
            "distinct_mints": q("SELECT COUNT(DISTINCT chain||':'||mint) FROM bt_universe_members WHERE universe_id=?", universe_id)[0][0],
            "content_hash": store.sha256([list(r) for r in q("SELECT chain, mint, basis, entered_at, status_at_entry, score_at_entry FROM bt_universe_members WHERE universe_id=? ORDER BY chain, mint, entered_at, basis", universe_id)])}
