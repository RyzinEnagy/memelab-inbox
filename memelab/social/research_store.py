"""Phase 13: read side of the social research adapter.

Reads what earlier phases stored and what the existing workflows produced; writes nothing. There is no new table and
no second watchlist (D-086): the research section travels inside the scout and catalyst reports.

  load_policy          effective policy and its provenance (defaults, data/config.json key "social_research", a policy file)
  findings_from_db     Phase 07 narrative clusters (latest snapshot at or before as_of) and Phase 12 current flags
  evaluated_from_scout tokens the scout already analyzed, as the three-lane adapter expects them
  evaluated_from_catalyst latest catalyst assessment per token
  prior_rejections     the latest verdict per mint before as_of, when it was a rejection
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from . import research_core as RC

CONFIG_KEY = "social_research"


def load_policy(policy_file: str | Path | None = None, config_path: str | Path | None = None) -> dict:
    """Defaults, then data/config.json["social_research"] (gitignored, per machine), then an explicit policy file."""
    over: dict = {}
    source, path = "default", None
    if config_path is None:
        from ..db import DATA_DIR
        config_path = DATA_DIR / "config.json"
    cp = Path(config_path)
    if cp.exists():
        try:
            cfg = json.loads(cp.read_text())
        except (OSError, ValueError) as e:
            raise RC.PolicyError(f"cannot read {cp}: {e}")
        if isinstance(cfg, dict) and isinstance(cfg.get(CONFIG_KEY), dict):
            over = dict(cfg[CONFIG_KEY])
            source, path = "config", str(cp)
    if policy_file:
        pf = Path(policy_file)
        doc = json.loads(pf.read_text())
        if not isinstance(doc, dict):
            raise RC.PolicyError("a policy file holds one JSON object")
        merged = json.loads(json.dumps(over))
        for k, v in doc.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k] = {**merged[k], **v}
            else:
                merged[k] = v
        over = merged
        source, path = ("config+file" if source == "config" else "file"), str(pf)
    return RC.make_policy(over, source=source, path=path)


def _has(con, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def findings_from_db(con: sqlite3.Connection, *, as_of: float, policy: dict) -> tuple[list[dict], dict]:
    """(findings, availability). Never raises for a missing or empty social store: that is an explicit no-op."""
    try:
        if not _has(con, "social_narrative_runs"):
            return [], {"status": "UNAVAILABLE", "reason": "social tables not present in this database (social schema not migrated)"}
        if not policy["signals"].get("narratives"):
            return [], {"status": "AVAILABLE", "reason": "narrative signal disabled by policy"}
        q = "SELECT run_id FROM social_narrative_runs WHERE cutoff<=?"
        if not policy.get("include_fixtures"):
            q += " AND contains_fixture=0"
        row = con.execute(q + " ORDER BY window_end DESC, cutoff DESC, run_id DESC LIMIT 1", (as_of,)).fetchone()
        if row is None:
            return [], {"status": "AVAILABLE", "reason": "no narrative snapshot at or before as_of"}
        from . import narratives as NR
        v = NR.run_view(con, row[0])
        symbols = NR._load_symbols(con)
        rr = v["run"]
        out: list[dict] = []
        for c in v["clusters"]:
            if c["cluster_kind"] != "CONTRACT":
                continue
            _, chain, contract = c["cluster_key"].split(":", 2)
            out.append({"kind": "CONTRACT", "chain": chain, "contract": contract, "symbol": symbols.get(c["cluster_key"]),
                        "status": c["status"], "reasons": c["reasons"], "confidence": c["confidence"], "freshness": c["freshness"],
                        "first_observed_at": c["first_observed_at"], "last_observed_at": c["last_observed_at"],
                        "earliest_published_at": c["earliest_published_at"], "item_count": c["item_count"],
                        "independent_source_count": c["independent_source_count"], "amplifier_count": c["amplifier_count"],
                        "conflicted": c["conflicted"], "stance": c["stance"], "originators": c["originators"], "flags": c["flags"],
                        "is_fixture": bool(rr["contains_fixture"]),
                        "source": {"run_id": rr["run_id"], "cluster_key": c["cluster_key"], "engine_version": rr["engine_version"],
                                   "window": rr["window_label"], "cutoff": rr["cutoff"]}})
        for sym, n in sorted((v["unassigned"].get("ticker_only_mentions") or {}).items()):
            out.append({"kind": "TICKER_ONLY", "symbol": sym, "mentions": n, "is_fixture": bool(rr["contains_fixture"]),
                        "source": {"run_id": rr["run_id"], "engine_version": rr["engine_version"], "window": rr["window_label"]}})
        if policy["signals"].get("chronology_flags") and _has(con, "social_chrono_flags"):
            from . import chrono_store as CS
            for f in out:
                if f["kind"] == "CONTRACT":
                    f["chrono_flags"] = [fl for fl in CS.current_flags(con, chain=f["chain"], contract=f["contract"],
                                                                      include_fixtures=bool(policy.get("include_fixtures")))
                                         if fl.get("at") is None or fl["at"] <= as_of]
        return out, {"status": "AVAILABLE", "reason": None if out else "the latest narrative snapshot has no contract or ticker findings",
                     "narrative_run_id": rr["run_id"]}
    except sqlite3.Error as e:
        return [], {"status": "UNAVAILABLE", "reason": f"social store error: {type(e).__name__}: {e}"}


def prior_rejections(con: sqlite3.Connection, mints: Iterable[str], *, before: float) -> dict[str, dict]:
    """The latest verdict per mint strictly before `before`, when that verdict was a rejection. A later non-rejected
    thesis supersedes an older rejection."""
    out: dict[str, dict] = {}
    for m in sorted(set(mints)):
        th = con.execute("SELECT created_at, status, fatal_flags_json FROM theses WHERE mint=? AND created_at<? ORDER BY created_at DESC, id DESC LIMIT 1",
                         (m, before)).fetchone()
        rj = con.execute("SELECT rejected_at, stage, why_failed, reconsider_if FROM rejections WHERE mint=? AND rejected_at<? ORDER BY rejected_at DESC, id DESC LIMIT 1",
                         (m, before)).fetchone()
        if th is not None and th["status"] != "REJECTED" and (rj is None or th["created_at"] >= rj["rejected_at"]):
            continue
        if th is not None and th["status"] == "REJECTED":
            flags = [f.get("flag") for f in json.loads(th["fatal_flags_json"] or "[]") if isinstance(f, dict)]
            out[m] = {"rejected_at": th["created_at"], "stage": "deep", "fatal_flags": flags,
                      "why_failed": rj["why_failed"] if rj else None, "reconsider_if": rj["reconsider_if"] if rj else None}
        elif rj is not None:
            out[m] = {"rejected_at": rj["rejected_at"], "stage": rj["stage"], "fatal_flags": [rj["why_failed"]],
                      "why_failed": rj["why_failed"], "reconsider_if": rj["reconsider_if"]}
    return out


def evaluated_from_scout(results: list[dict], tradable_mints: Iterable[str], prior: dict[str, dict] | None = None) -> list[dict]:
    tradable = set(tradable_mints)
    prior = prior or {}
    out = []
    for r in results:
        b = r.get("bundle") or {}
        sc = r.get("score") or {}
        out.append({"workflow": "scout", "chain": b.get("chain") or "solana", "contract": r["mint"], "symbol": (b.get("identity") or {}).get("symbol"),
                    "fatal_flags": [f.get("flag") for f in sc.get("fatal_flags") or []], "untradeable": bool(sc.get("untradeable")),
                    "status": (r.get("status") or {}).get("status"), "score": sc.get("total"), "in_tradable_ranking": r["mint"] in tradable,
                    "prior_rejection": prior.get(r["mint"]), "ref": r.get("report_path")})
    return out


def evaluated_from_catalyst(con: sqlite3.Connection, *, as_of: float, prior: dict[str, dict] | None = None) -> list[dict]:
    prior = prior or {}
    rows = con.execute("SELECT a.* FROM catalyst_assessments a JOIN (SELECT mint, MAX(assessed_at) m FROM catalyst_assessments "
                       "WHERE mint IS NOT NULL AND assessed_at<=? GROUP BY mint) l ON l.mint=a.mint AND l.m=a.assessed_at ORDER BY a.mint, a.id",
                       (as_of,)).fetchall() if _has(con, "catalyst_assessments") else []
    out, seen = [], set()
    for a in rows:
        if a["mint"] in seen:
            continue
        seen.add(a["mint"])
        fatal = [str(x.get("flag") if isinstance(x, dict) else x) for x in json.loads(a["fatal_json"] or "[]")]
        tok = con.execute("SELECT chain, symbol FROM tokens WHERE mint=?", (a["mint"],)).fetchone()
        out.append({"workflow": "catalyst", "chain": (tok["chain"] if tok and tok["chain"] else "solana"), "contract": a["mint"],
                    "symbol": tok["symbol"] if tok else None, "fatal_flags": fatal, "untradeable": bool(fatal) or a["verdict"] == "REJECTED",
                    "status": a["verdict"], "score": a["triage_score"], "in_tradable_ranking": a["verdict"] not in ("REJECTED", "EVENT_ONLY"),
                    "prior_rejection": prior.get(a["mint"]), "ref": f"catalyst_assessments:{a['id']}"})
    return out


def section(con_factory, *, as_of: float, policy: dict, evaluated: list[dict]) -> dict:
    """Open the store, read findings and build the section. A store that cannot be opened is an explicit no-op."""
    prior: dict[str, dict] = {}
    try:
        with con_factory() as con:
            findings, avail = findings_from_db(con, as_of=as_of, policy=policy)
            done = {e.get("contract") for e in evaluated}
            rest = [f["contract"] for f in findings if f.get("kind") == "CONTRACT" and f["contract"] not in done]
            if rest and _has(con, "theses") and _has(con, "rejections"):
                prior = prior_rejections(con, rest, before=as_of)
    except Exception as e:  # the social layer must never break a scout or catalyst run
        findings, avail = [], {"status": "UNAVAILABLE", "reason": f"cannot open the social store: {type(e).__name__}: {e}"}
    return RC.build(findings, evaluated, policy, as_of=as_of, availability=avail, prior=prior)
