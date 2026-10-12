"""Phase 14: read side of the intelligence feed.

Reads what earlier phases stored and writes nothing. The output is a plain input document
(schema memelab.social.feed.input/1) that feed_core.build turns into the feed, the morning brief and the trader digest.

  load_input   newest Phase 07 narrative snapshot with cutoff at or before as_of, every cluster with its members joined to
               their claim attributes (Phase 06), items and accounts (Phase 01), trader links (Phase 08), the previous
               comparable snapshot's stances (for changed positions), the snapshot's change rows, Phase 12 current flags and
               the latest Phase 05 liquidity and exit facts. A missing or empty store is an explicit availability status.

Nothing here reads post wording, the private store or a model. The model status comes from llm.llm_status, which never
makes a network call.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

INPUT_SCHEMA = "memelab.social.feed.input/1"
MARKET_FIELDS = ("liquidity_reported", "sell_quote_out", "volume_24h")


def _has(con, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _empty(as_of: float, status: str, reason: str, model: dict) -> dict:
    return {"schema": INPUT_SCHEMA, "as_of": as_of, "availability": {"status": status, "reason": reason}, "snapshot": None,
            "clusters": [], "unresolved": [], "model": model}


def model_status(con=None) -> dict:
    """The truthful model status, or UNKNOWN if even that cannot be read. The feed never needs a model."""
    try:
        from . import llm
        s = llm.llm_status(con)
        return {"status": s.get("status") or "unknown"}
    except Exception as e:  # noqa: BLE001  the feed must render without the model layer
        return {"status": "unknown", "detail": type(e).__name__}


def _members(con, run_id: int, key: str) -> list[dict]:
    rows = con.execute(
        "SELECT m.claim_id, m.item_key, m.observation_id, m.account_id, m.source_id, m.role, m.group_id, m.event_time, m.event_time_basis, "
        "m.in_window, m.source_state, m.stance AS member_stance, m.why, "
        "a.category, a.assertion_type, a.stance, a.sarcasm_suspected, a.author_position, a.verification, a.conditional, a.negated, a.uncertainty_reasons_json, "
        "c.claim_type, c.direction, e.flags_json, e.mode AS extraction_mode, "
        "i.platform, i.original_url, i.published_at, i.published_at_basis, i.first_observed_at, "
        "o.access_mode, acc.handle, acc.account_kind, acc.identity_status "
        "FROM social_narrative_members m "
        "LEFT JOIN social_claim_attributes a ON a.claim_id=m.claim_id "
        "LEFT JOIN social_claims c ON c.id=m.claim_id "
        "LEFT JOIN social_claim_extractions e ON e.extraction_id=a.extraction_id "
        "LEFT JOIN social_items i ON i.item_key=m.item_key "
        "LEFT JOIN social_observations o ON o.id=m.observation_id "
        "LEFT JOIN social_accounts acc ON acc.account_id=COALESCE(m.account_id, i.account_id) "
        "WHERE m.run_id=? AND m.cluster_key=? ORDER BY m.claim_id", (run_id, key)).fetchall()
    traders = {}
    for r in con.execute("SELECT ta.account_id, t.trader_id, t.label FROM social_trader_accounts ta JOIN social_traders t ON t.trader_id=ta.trader_id "
                         "ORDER BY ta.account_id, t.trader_id"):
        traders.setdefault(r["account_id"], (r["trader_id"], r["label"]))
    out = []
    for r in rows:
        d = dict(r)
        try:
            flags = json.loads(d.pop("flags_json") or "[]")
        except ValueError:
            flags = []
        try:
            reasons = json.loads(d.pop("uncertainty_reasons_json") or "[]")
        except ValueError:
            reasons = []
        d["extraction_flags"] = sorted(str(f.get("flag") if isinstance(f, dict) else f) for f in flags)
        d["injection_suspected"] = "injection_suspected" in reasons or any(f.startswith("injection") for f in d["extraction_flags"])
        tr = traders.get(d.get("account_id"))
        d["trader_id"], d["trader_label"] = (tr if tr else (None, None))
        out.append(d)
    return out


def _prev_stances(con, prev_run_id: int | None, key: str) -> dict[str, dict]:
    """Latest stance per source in the previous comparable snapshot, for the same cluster key."""
    if prev_run_id is None:
        return {}
    out: dict[str, dict] = {}
    for m in _members(con, prev_run_id, key):
        sid = m.get("source_id")
        if not sid or m.get("role") == "AMPLIFIER" or m.get("sarcasm_suspected"):
            continue
        t = m.get("event_time") or 0
        if sid not in out or t >= (out[sid]["event_time"] or 0):
            out[sid] = {"stance": m.get("stance") or m.get("member_stance"), "author_position": m.get("author_position"),
                        "event_time": m.get("event_time"), "run_id": prev_run_id}
    return out


def _market(con, chain: str, contract: str, as_of: float) -> list[dict]:
    if not _has(con, "social_market_facts"):
        return []
    out = []
    for f in MARKET_FIELDS:
        r = con.execute("SELECT field, value_num, value_str, unit, quote_currency, provider, source_url, as_of, fetched_at, valid_until, bucket, fact_id "
                        "FROM social_market_facts WHERE chain=? AND contract=? AND field=? AND fetched_at<=? "
                        "ORDER BY fetched_at DESC, fact_version DESC, fact_id DESC LIMIT 1", (chain, contract, f, as_of)).fetchone()
        if r is not None:
            out.append(dict(r))
    return out


def _flags(con, chain: str, contract: str, as_of: float, include_fixtures: bool) -> list[dict]:
    if not _has(con, "social_chrono_flags"):
        return []
    from . import chrono_store as CS
    try:
        fl = CS.current_flags(con, chain=chain, contract=contract, include_fixtures=include_fixtures)
    except Exception:  # noqa: BLE001  an unknown chain in chrono identity rules: no flags rather than no feed
        return []
    return [f for f in fl if f.get("at") is None or f["at"] <= as_of]


def load_input(con: sqlite3.Connection, *, as_of: float, include_fixtures: bool = False, run_id: int | None = None) -> dict:
    """Never raises for a missing, empty or broken social store: that becomes availability UNAVAILABLE."""
    model = model_status(con)
    try:
        if not _has(con, "social_narrative_runs"):
            return _empty(as_of, "UNAVAILABLE", "social tables not present in this database (social schema not migrated)", model)
        if run_id is not None:
            row = con.execute("SELECT * FROM social_narrative_runs WHERE run_id=?", (run_id,)).fetchone()
            if row is None:
                return _empty(as_of, "AVAILABLE", f"no narrative snapshot with run id {run_id}", model)
        else:
            q = "SELECT * FROM social_narrative_runs WHERE cutoff<=?"
            if not include_fixtures:
                q += " AND contains_fixture=0"
            row = con.execute(q + " ORDER BY window_end DESC, cutoff DESC, run_id DESC LIMIT 1", (as_of,)).fetchone()
            if row is None:
                return _empty(as_of, "AVAILABLE", "no narrative snapshot at or before as_of", model)
        if row["contains_fixture"] and not include_fixtures:
            return _empty(as_of, "AVAILABLE", "the requested snapshot contains fixture data and fixtures were not requested", model)
        from . import narratives as NR
        v = NR.run_view(con, row["run_id"])
        rr = v["run"]
        symbols = NR._load_symbols(con)
        changes: dict[str, list[str]] = {}
        for ch in NR.changes_for(con, rr["run_id"]):
            changes.setdefault(ch["cluster_key"], []).append(ch["change_type"])
        clusters = []
        for c in v["clusters"]:
            d = {k: c.get(k) for k in ("cluster_key", "cluster_kind", "label", "status", "reasons", "confidence", "freshness", "first_observed_at",
                                       "last_observed_at", "earliest_published_at", "item_count", "window_mentions", "source_count",
                                       "independent_source_count", "independent_group_count", "amplifier_count", "dependent_count",
                                       "unobserved_origin_count", "edge_count", "conflicted", "stance", "opinion_changes", "flags",
                                       "originators", "linked_tokens", "chains", "coverage")}
            d["symbol"] = symbols.get(c["cluster_key"])
            d["changes"] = sorted(changes.get(c["cluster_key"], []))
            d["members"] = _members(con, rr["run_id"], c["cluster_key"])
            d["prev_stances"] = _prev_stances(con, rr["prev_run_id"], c["cluster_key"])
            if c["cluster_kind"] == "CONTRACT":
                _, chain, contract = c["cluster_key"].split(":", 2)
                d["chain"], d["contract"] = chain, contract
                d["chrono_flags"] = _flags(con, chain, contract, as_of, include_fixtures or bool(rr["contains_fixture"]))
                d["market"] = _market(con, chain, contract, as_of)
            else:
                d["chain"], d["contract"], d["chrono_flags"], d["market"] = None, None, [], []
            clusters.append(d)
        unresolved = [{"symbol": s, "mentions": n} for s, n in sorted((v["unassigned"].get("ticker_only_mentions") or {}).items())]
        snap = {k: rr[k] for k in ("run_id", "engine_version", "window_label", "tz", "window_start", "window_end", "cutoff", "window_complete",
                                   "contains_fixture", "prev_run_id", "input_claims", "cluster_count")}
        snap["compared_to"] = v["summary"].get("compared_to")
        snap["claims_by_reason"] = v["unassigned"].get("claims_by_reason") or {}
        return {"schema": INPUT_SCHEMA, "as_of": as_of, "availability": {"status": "AVAILABLE", "reason": None}, "snapshot": snap,
                "clusters": clusters, "unresolved": unresolved, "model": model}
    except sqlite3.Error as e:
        return _empty(as_of, "UNAVAILABLE", f"social store error: {type(e).__name__}", model)


def load_from_path(path: str, *, as_of: float, include_fixtures: bool = False, run_id: int | None = None) -> dict:
    """Open the database read only. A file that cannot be opened is an explicit UNAVAILABLE, never a crash."""
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        return _empty(as_of, "UNAVAILABLE", f"cannot open the social store: {type(e).__name__}", model_status())
    try:
        return load_input(con, as_of=as_of, include_fixtures=include_fixtures, run_id=run_id)
    finally:
        con.close()


def _jsonable(o: Any) -> Any:
    return json.loads(json.dumps(o, default=str, sort_keys=True))
