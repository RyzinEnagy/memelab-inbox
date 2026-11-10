"""Catalyst and social tables in the state export (format catsoc-export-1; CM-3, PI-D-130, ED-3). Opt-in, OFF by default.

    flag: MEMELAB_STATE_EXPORT_CATSOC=1, or data/config.json {"state_export": {"catalyst_social": true}} (JSON true only)
    python -m memelab.catsoc_export import SRC DEST [--commit-time EPOCH]   copy an export's _catsoc section into a separate SQLite file
    python -m memelab.catsoc_export check SRC           guard and column check of an export's section (exit 1 on a problem)

The export is published (the inbox repository is public), so this section carries identifiers, hashes, exact chain plus mint
links, enum states, times and short own-words summaries only. Every table has an explicit column list; third-party identifiers
(account ids, item keys, trader ids, registry entity ids) are replaced by a salted sha256 prefix; no title, body, URL, handle,
display name, bio, note, label or mention text leaves the database. Database row ids are dropped: a scheduled session starts
from a fresh database, so rows are linked by stable keys (`event_ref`, `item_ref`, the social tables' own *_key hashes).

The section is checked before it is written (column lists, then `content_guard.check_json`); a violation or an error replaces
it by a small record naming the rule, and the export itself still succeeds.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

VERSION = "catsoc-export-1"
WINDOW_DAYS = 30
SUMMARY_MAX = 200
ENV_FLAG = "MEMELAB_STATE_EXPORT_CATSOC"
ENUM_REVISION_FIELDS = ("evidence_status", "status")
EXACT_MENTIONS = ("CONTRACT", "LINK")
EXACT_REF_KINDS = ("CONTRACT_ADDRESS", "OFFICIAL_LINK")

COLUMNS: dict[str, tuple[str, ...]] = {
    "catalyst_events": ("event_ref", "narrative_id", "category", "original_source_id", "published_at", "discovered_at", "retrieved_at",
                        "event_at", "evidence_status", "independent_sources", "repetitions", "resurfaced", "future_dated", "status",
                        "expires_at", "created_at", "updated_at"),
    "catalyst_event_revisions": ("event_ref", "revised_at", "kind", "field", "old_value", "new_value", "source_id"),
    "catalyst_event_sources": ("event_ref", "item_ref", "role"),
    "catalyst_items": ("item_ref", "source_id", "platform", "url_sha256", "body_norm_sha256", "mints_in_url", "mints_in_body",
                       "published_at", "retrieved_at", "first_seen_at"),
    "catalyst_token_links": ("event_ref", "chain", "mint", "link_type", "link_strength", "verified_mint", "linked_at"),
    "catalyst_sources": ("source_id", "source_group", "kind", "tier", "identity_verified", "added_at"),
    "catalyst_assessments": ("event_ref", "mint", "assessed_at", "verdict", "triage_score", "expires_at"),
    "social_accounts": ("account_ref", "platform", "account_kind", "identity_status", "identity_checked_at", "first_seen_at"),
    "social_items": ("item_ref", "platform", "account_ref", "published_at", "published_at_basis", "first_observed_at", "first_ingested_at"),
    "social_observations": ("observation_key", "item_ref", "account_ref", "observed_at", "observed_at_basis", "ingested_at", "access_mode",
                            "retrieval_status", "content_hash", "summary", "analysis_version"),
    "social_item_versions": ("item_ref", "provider_version_at", "version_kind", "content_hash", "first_recorded_at"),
    "social_token_resolutions": ("resolution_key", "item_ref", "mention_kind", "status", "resolved_chain", "resolved_contract",
                                 "resolved_at"),
    "social_claims": ("claim_key", "item_ref", "account_ref", "claim_type", "token_ref_key", "direction", "claimed_at", "extracted_at",
                      "evidence_status", "claim_status", "summary"),
    "social_claim_extractions": ("extraction_key", "item_ref", "extractor", "status", "extracted_at"),
    "social_trader_accounts": ("trader_ref", "account_ref", "evidence_status", "linked_at"),
    "social_token_refs": ("ref_key", "ref_kind", "chain", "contract", "first_seen_at"),
    "social_registry_entities": ("entity_ref", "entity_kind", "account_ref", "first_seen_at"),
    "social_registry_reviews": ("target_type", "target_ref", "to_state", "reviewed_at"),
}
CATALYST_TABLES = tuple(t for t in COLUMNS if t.startswith("catalyst_"))
SOCIAL_TABLES = tuple(t for t in COLUMNS if t.startswith("social_"))


class CatsocError(ValueError):
    pass


def ref(value: Any) -> str | None:
    """Salted sha256 prefix of a third-party identifier (never reversible to a handle by the reader of the export)."""
    return None if value is None else hashlib.sha256(f"{VERSION}:{value}".encode()).hexdigest()[:32]


def _sha(text: str | None) -> str | None:
    return None if text is None else hashlib.sha256(text.encode()).hexdigest()


def _norm(text: Any) -> str | None:
    """The normalization the Phase 10 classifier applies before hashing a body (whitespace collapsed, lower case)."""
    if text is None or str(text).strip() == "":
        return None
    return " ".join(str(text).split()).lower()


def enabled(config_path: str | Path | None = None) -> bool:
    if os.environ.get(ENV_FLAG) == "1":
        return True
    if config_path is None:
        from .db import DATA_DIR
        config_path = Path(DATA_DIR) / "config.json"
    try:
        cfg = json.loads(Path(config_path).read_text())
    except (OSError, ValueError):
        return False
    sect = cfg.get("state_export") if isinstance(cfg, dict) else None
    return isinstance(sect, dict) and sect.get("catalyst_social") is True


def summary_ok(s: Any) -> bool:
    if s is None:
        return True
    s = str(s)
    return len(s) <= SUMMARY_MAX and "\n" not in s and "\r" not in s and "@" not in s and "http" not in s.lower()


def _tables(con: sqlite3.Connection) -> set[str]:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _rows(con: sqlite3.Connection, sql: str, args: tuple = ()) -> list[dict]:
    cur = con.execute(sql, args)
    names = [c[0] for c in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def _in(ids) -> tuple[str, list]:
    ids = sorted({i for i in ids if i is not None}, key=str)
    return ("(" + ",".join("?" * len(ids)) + ")" if ids else "(NULL)"), ids


def _catalyst(con: sqlite3.Connection, have: set[str], since: float) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {t: [] for t in CATALYST_TABLES}
    if "catalyst_events" not in have:
        return out
    evs = _rows(con, "SELECT * FROM catalyst_events WHERE updated_at > ? ORDER BY id", (since,))
    eref = {e["id"]: ref(e["event_key"]) for e in evs}
    ph, ids = _in(eref)
    for e in evs:
        out["catalyst_events"].append({"event_ref": eref[e["id"]], **{k: e.get(k) for k in COLUMNS["catalyst_events"][1:]}})
    links = _rows(con, f"SELECT * FROM catalyst_token_links WHERE event_id IN {ph} ORDER BY id", tuple(ids)) if "catalyst_token_links" in have else []
    mints_of: dict[int, set[str]] = {}
    for k in links:
        mints_of.setdefault(k["event_id"], set()).add(k["mint"])
        out["catalyst_token_links"].append({"event_ref": eref[k["event_id"]], "chain": k.get("chain"), "mint": k.get("mint"),
                                            "link_type": k.get("link_type"), "link_strength": k.get("link_strength"),
                                            "verified_mint": k.get("verified_mint"), "linked_at": k.get("linked_at")})
    if "catalyst_event_revisions" in have:
        for r in _rows(con, f"SELECT * FROM catalyst_event_revisions WHERE event_id IN {ph} ORDER BY id", tuple(ids)):
            enum = r.get("field") in ENUM_REVISION_FIELDS
            out["catalyst_event_revisions"].append({"event_ref": eref[r["event_id"]], "revised_at": r.get("revised_at"), "kind": r.get("kind"),
                                                    "field": r.get("field"), "old_value": r.get("old_value") if enum else None,
                                                    "new_value": r.get("new_value") if enum else None, "source_id": r.get("source_id")})
    roles = _rows(con, f"SELECT * FROM catalyst_event_sources WHERE event_id IN {ph}", tuple(ids)) if "catalyst_event_sources" in have else []
    items_ev: dict[int, set[int]] = {}
    for r in roles:
        items_ev.setdefault(r["item_id"], set()).add(r["event_id"])
    if "catalyst_items" in have:
        iph, iids = _in(set(items_ev))
        items = _rows(con, f"SELECT * FROM catalyst_items WHERE id IN {iph} OR event_id IN {ph} ORDER BY id", tuple(iids) + tuple(ids))
    else:
        items = []
    iref: dict[int, str] = {}
    srcs = {e.get("original_source_id") for e in evs}
    for it in items:
        iref[it["id"]] = ref(f"{it['source_id']}|{it['item_key']}")
        evset = set(items_ev.get(it["id"], set())) | ({it["event_id"]} if it.get("event_id") in eref else set())
        mints = set().union(*(mints_of.get(e, set()) for e in evset)) if evset else set()
        url, body = str(it.get("url") or ""), str(it.get("body") or "")
        srcs.add(it.get("source_id"))
        out["catalyst_items"].append({"item_ref": iref[it["id"]], "source_id": it.get("source_id"), "platform": it.get("platform"),
                                      "url_sha256": _sha(it.get("url")) if it.get("url") else None,
                                      "body_norm_sha256": _sha(_norm(it.get("body"))),
                                      "mints_in_url": sorted(m for m in mints if m and m in url),
                                      "mints_in_body": sorted(m for m in mints if m and m in body),
                                      "published_at": it.get("published_at"), "retrieved_at": it.get("retrieved_at"),
                                      "first_seen_at": it.get("first_seen_at")})
    for r in roles:
        if r["item_id"] in iref:
            out["catalyst_event_sources"].append({"event_ref": eref[r["event_id"]], "item_ref": iref[r["item_id"]], "role": r.get("role")})
    out["catalyst_event_sources"].sort(key=lambda r: (r["event_ref"], r["item_ref"]))
    srcs |= {r.get("source_id") for r in out["catalyst_event_revisions"]}
    if "catalyst_sources" in have:
        sph, sids = _in(srcs)
        for s in _rows(con, f"SELECT * FROM catalyst_sources WHERE source_id IN {sph} ORDER BY source_id", tuple(sids)):
            out["catalyst_sources"].append({k: s.get(k) for k in COLUMNS["catalyst_sources"]})
    if "catalyst_assessments" in have:
        for a in _rows(con, f"SELECT * FROM catalyst_assessments WHERE event_id IN {ph} ORDER BY id", tuple(ids)):
            out["catalyst_assessments"].append({"event_ref": eref[a["event_id"]], "mint": a.get("mint"), "assessed_at": a.get("assessed_at"),
                                                "verdict": a.get("verdict"), "triage_score": a.get("triage_score"),
                                                "expires_at": a.get("expires_at")})
    return out


def _social(con: sqlite3.Connection, have: set[str], since: float, withheld: list[int]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {t: [] for t in SOCIAL_TABLES}
    if not {"social_items", "social_token_resolutions"} <= have:
        return out

    def summ(s):
        if summary_ok(s):
            return s
        withheld[0] += 1
        return None
    res = _rows(con, "SELECT * FROM social_token_resolutions WHERE status='resolved' AND resolved_chain IS NOT NULL AND resolved_contract "
                     "IS NOT NULL AND mention_kind IN ('CONTRACT','LINK') AND item_key IS NOT NULL ORDER BY resolution_id")
    ph, keys = _in({r["item_key"] for r in res})
    items = _rows(con, f"SELECT * FROM social_items WHERE first_ingested_at > ? AND item_key IN {ph} ORDER BY item_key", (since, *keys))
    keep = {i["item_key"] for i in items}
    kph, kk = _in(keep)
    accts = {i.get("account_id") for i in items}
    for i in items:
        out["social_items"].append({"item_ref": ref(i["item_key"]), "platform": i.get("platform"), "account_ref": ref(i.get("account_id")),
                                    "published_at": i.get("published_at"), "published_at_basis": i.get("published_at_basis"),
                                    "first_observed_at": i.get("first_observed_at"), "first_ingested_at": i.get("first_ingested_at")})
    refs_used: set = set()
    for r in res:
        if r["item_key"] in keep:
            refs_used.add(r.get("resolved_ref_id"))
            out["social_token_resolutions"].append({"resolution_key": r.get("resolution_key"), "item_ref": ref(r["item_key"]),
                                                    "mention_kind": r.get("mention_kind"), "status": r.get("status"),
                                                    "resolved_chain": r.get("resolved_chain"), "resolved_contract": r.get("resolved_contract"),
                                                    "resolved_at": r.get("resolved_at")})
    if "social_observations" in have:
        for o in _rows(con, f"SELECT * FROM social_observations WHERE item_key IN {kph} ORDER BY id", tuple(kk)):
            accts.add(o.get("account_id"))
            out["social_observations"].append({"observation_key": o.get("observation_key"), "item_ref": ref(o["item_key"]),
                                               "account_ref": ref(o.get("account_id")), "observed_at": o.get("observed_at"),
                                               "observed_at_basis": o.get("observed_at_basis"), "ingested_at": o.get("ingested_at"),
                                               "access_mode": o.get("access_mode"), "retrieval_status": o.get("retrieval_status"),
                                               "content_hash": o.get("content_hash"), "summary": summ(o.get("summary")),
                                               "analysis_version": o.get("analysis_version")})
    if "social_item_versions" in have:
        for v in _rows(con, f"SELECT * FROM social_item_versions WHERE item_key IN {kph} ORDER BY item_key, provider_version_at", tuple(kk)):
            out["social_item_versions"].append({"item_ref": ref(v["item_key"]), "provider_version_at": v.get("provider_version_at"),
                                                "version_kind": v.get("version_kind"), "content_hash": v.get("content_hash"),
                                                "first_recorded_at": v.get("first_recorded_at")})
    rkey: dict[int, str] = {}
    if "social_token_refs" in have:
        for t in _rows(con, "SELECT * FROM social_token_refs ORDER BY ref_id"):
            rkey[t["ref_id"]] = t["ref_key"]
    if "social_claims" in have:
        for c in _rows(con, f"SELECT * FROM social_claims WHERE item_key IN {kph} ORDER BY id", tuple(kk)):
            refs_used.add(c.get("token_ref_id"))
            out["social_claims"].append({"claim_key": c.get("claim_key"), "item_ref": ref(c["item_key"]), "account_ref": ref(c.get("account_id")),
                                         "claim_type": c.get("claim_type"), "token_ref_key": rkey.get(c.get("token_ref_id")),
                                         "direction": c.get("direction"), "claimed_at": c.get("claimed_at"),
                                         "extracted_at": c.get("extracted_at"), "evidence_status": c.get("evidence_status"),
                                         "claim_status": c.get("claim_status"), "summary": summ(c.get("summary"))})
    if "social_claim_extractions" in have:
        for x in _rows(con, f"SELECT * FROM social_claim_extractions WHERE item_key IN {kph} ORDER BY extraction_id", tuple(kk)):
            out["social_claim_extractions"].append({"extraction_key": x.get("extraction_key"), "item_ref": ref(x["item_key"]),
                                                    "extractor": x.get("extractor"), "status": x.get("status"),
                                                    "extracted_at": x.get("extracted_at")})
    if "social_token_refs" in have:
        rph, rids = _in(refs_used)
        for t in _rows(con, f"SELECT * FROM social_token_refs WHERE ref_kind IN ('CONTRACT_ADDRESS','OFFICIAL_LINK') AND (ref_id IN {rph} "
                            "OR (ref_kind='OFFICIAL_LINK' AND first_seen_at > ?)) ORDER BY ref_id", (*rids, since)):
            out["social_token_refs"].append({k: t.get(k) for k in COLUMNS["social_token_refs"]})
    accts.discard(None)
    aph, aids = _in(accts)
    if "social_accounts" in have:
        for a in _rows(con, f"SELECT * FROM social_accounts WHERE account_id IN {aph} ORDER BY account_id", tuple(aids)):
            out["social_accounts"].append({"account_ref": ref(a["account_id"]), "platform": a.get("platform"),
                                           "account_kind": a.get("account_kind"), "identity_status": a.get("identity_status"),
                                           "identity_checked_at": a.get("identity_checked_at"), "first_seen_at": a.get("first_seen_at")})
    if "social_trader_accounts" in have:
        for t in _rows(con, f"SELECT * FROM social_trader_accounts WHERE account_id IN {aph} ORDER BY trader_id, account_id", tuple(aids)):
            out["social_trader_accounts"].append({"trader_ref": ref(t["trader_id"]), "account_ref": ref(t["account_id"]),
                                                  "evidence_status": t.get("evidence_status"), "linked_at": t.get("linked_at")})
    ents = []
    if "social_registry_entities" in have:
        ents = _rows(con, f"SELECT * FROM social_registry_entities WHERE entity_kind='SOCIAL_ACCOUNT' AND account_id IN {aph} ORDER BY entity_id",
                     tuple(aids))
        for e in ents:
            out["social_registry_entities"].append({"entity_ref": ref(e["entity_id"]), "entity_kind": e.get("entity_kind"),
                                                    "account_ref": ref(e.get("account_id")), "first_seen_at": e.get("first_seen_at")})
    if "social_registry_reviews" in have and ents:
        eph, eids = _in({e["entity_id"] for e in ents})
        for r in _rows(con, f"SELECT * FROM social_registry_reviews WHERE target_type='ACCOUNT_STATUS' AND target_id IN {eph} ORDER BY review_id",
                       tuple(eids)):
            out["social_registry_reviews"].append({"target_type": r.get("target_type"), "target_ref": ref(r["target_id"]),
                                                   "to_state": r.get("to_state"), "reviewed_at": r.get("reviewed_at")})
    return out


def problems(sec: dict) -> list[str]:
    """Rule names (never values) of anything in a section that the export must not carry."""
    out = []
    tabs = sec.get("tables")
    if not isinstance(tabs, dict) or set(tabs) != set(COLUMNS):
        return ["TABLE_SET"]
    for t, rows in tabs.items():
        for r in rows:
            if not isinstance(r, dict) or tuple(r) != COLUMNS[t]:
                out.append(f"COLUMNS:{t}")
                break
            if "summary" in r and not summary_ok(r["summary"]):
                out.append(f"SUMMARY:{t}")
                break
    from .social.content_guard import check_json
    out += sorted({f"GUARD:{v.rule}" for v in check_json("data/state/latest.json", {"_catsoc": sec})})
    return out


def section(con: sqlite3.Connection, now: float | None = None) -> dict:
    """The `_catsoc` section of one export. Never raises: an error or a failed check gives a withheld record."""
    try:
        now = float(now) if now is not None else time.time()
        since = now - WINDOW_DAYS * 86400
        have = _tables(con)
        withheld = [0]
        tabs = {**_catalyst(con, have, since), **_social(con, have, since, withheld)}
        sec = {"version": VERSION, "window_days": WINDOW_DAYS, "window_start": since, "tables": tabs,
               "withheld_summaries": withheld[0], "tables_missing": sorted(t for t in COLUMNS if t not in have)}
        bad = problems(sec)
        if bad:
            return {"version": VERSION, "withheld": "GUARD_VIOLATION", "rules": bad}
        return sec
    except Exception as e:  # noqa: BLE001  (a scheduled export must not fail because of this section)
        return {"version": VERSION, "withheld": "ERROR", "error": type(e).__name__}


# ---------------------------------------------------------------- importer path back (a separate store, never the lab tables)
IMPORT_TABLES = ("catsoc_rows", "catsoc_imports")
IMPORT_DDL = """
CREATE TABLE IF NOT EXISTS catsoc_rows (
  table_name TEXT NOT NULL, row_sha256 TEXT NOT NULL, row_json TEXT NOT NULL,
  first_export_at REAL NOT NULL, time_basis TEXT NOT NULL CHECK (time_basis IN ('COMMIT','EXPORTED_AT')),
  first_import_id INTEGER NOT NULL,
  PRIMARY KEY (table_name, row_sha256)
);
CREATE TABLE IF NOT EXISTS catsoc_imports (
  import_id INTEGER PRIMARY KEY, source_sha256 TEXT NOT NULL, exported_at REAL, version TEXT NOT NULL, rows_added INTEGER NOT NULL
);
"""


def row_sha256(row: dict) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _dest_refusal(dest: Path) -> str | None:
    from . import db
    p = dest.resolve()
    if p == Path(db.DB_PATH).resolve():
        return "it is the lab database"
    root = Path(__file__).resolve().parents[1]
    if p == root or root in p.parents:
        priv = (root / "data" / "private").resolve()
        if not (priv in p.parents):
            return "inside the repository and not under data/private/"
    if p.exists():
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            try:
                names = _tables(con)
            finally:
                con.close()
        except sqlite3.DatabaseError:
            return "an existing file that is not a catsoc store"
        if names - set(IMPORT_TABLES) - {"sqlite_sequence"}:
            return "an existing database with other tables"
    return None


def import_(src: str | Path, dest: str | Path, *, commit_time: float | None = None) -> dict:
    """Copy the `_catsoc` section of one local export file into DEST. Idempotent (rows keyed by table and row sha256). With
    `commit_time` (the time of the commit that carried this export) a new row's time is that commit time (basis COMMIT, usable
    as `available_at`); without it the export's own `_exported_at` is kept (basis EXPORTED_AT, for inspection only: the engine
    never treats an export as available before its commit)."""
    if str(src).startswith(("http:", "https:")):
        raise CatsocError("the importer reads local files only")
    raw = Path(src).read_bytes()
    doc = json.loads(raw)
    sec = doc.get("_catsoc") if isinstance(doc, dict) else None
    if not isinstance(sec, dict) or sec.get("version") != VERSION or "tables" not in sec:
        return {"state": "NO_CATSOC_SECTION" if not isinstance(sec, dict) else "SECTION_WITHHELD", "rows_added": 0}
    bad = problems(sec)
    if bad:
        raise CatsocError("section refused: " + ", ".join(bad))
    d = Path(dest)
    why = _dest_refusal(d)
    if why:
        raise CatsocError(f"destination refused: {why}")
    d.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(d)
    try:
        con.executescript(IMPORT_DDL)
        cur = con.execute("INSERT INTO catsoc_imports(source_sha256, exported_at, version, rows_added) VALUES (?,?,?,0)",
                          (hashlib.sha256(raw).hexdigest(), doc.get("_exported_at"), VERSION))
        iid = cur.lastrowid
        at, basis = (float(commit_time), "COMMIT") if commit_time is not None else (float(doc.get("_exported_at") or 0.0), "EXPORTED_AT")
        added = 0
        for t in COLUMNS:
            for r in sec["tables"][t]:
                c = con.execute("INSERT OR IGNORE INTO catsoc_rows(table_name, row_sha256, row_json, first_export_at, time_basis, "
                                "first_import_id) VALUES (?,?,?,?,?,?)",
                                (t, row_sha256(r), json.dumps(r, sort_keys=True, separators=(",", ":")), at, basis, iid))
                added += c.rowcount
                if c.rowcount == 0:       # imported out of order: keep the earliest time of the same basis
                    con.execute("UPDATE catsoc_rows SET first_export_at=? WHERE table_name=? AND row_sha256=? AND time_basis=? "
                                "AND first_export_at > ?", (at, t, row_sha256(r), basis, at))
        con.execute("UPDATE catsoc_imports SET rows_added=? WHERE import_id=?", (added, iid))
        con.commit()
    finally:
        con.close()
    return {"state": "IMPORTED", "rows_added": added, "import_id": iid}


def read_store(path: str | Path) -> dict[str, list[dict]]:
    """The rows of a catsoc store, read only, per table (each with `_first_export_at` and `_time_basis`)."""
    con = sqlite3.connect(f"file:{Path(path)}?mode=ro", uri=True)
    try:
        out: dict[str, list[dict]] = {t: [] for t in COLUMNS}
        for t, js, at, basis in con.execute("SELECT table_name, row_json, first_export_at, time_basis FROM catsoc_rows "
                                            "ORDER BY first_export_at, table_name, row_sha256"):
            if t in out:
                out[t].append(dict(json.loads(js), _first_export_at=at, _time_basis=basis))
        return out
    finally:
        con.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if cmd == "import" and len(sys.argv) in (4, 6) and (len(sys.argv) == 4 or sys.argv[4] == "--commit-time"):
            ct = float(sys.argv[5]) if len(sys.argv) == 6 else None
            print(json.dumps(import_(sys.argv[2], sys.argv[3], commit_time=ct), sort_keys=True))
        elif cmd == "check" and len(sys.argv) == 3:
            d = json.loads(Path(sys.argv[2]).read_text())
            s = d.get("_catsoc")
            if not isinstance(s, dict):
                print(json.dumps({"state": "NO_CATSOC_SECTION"}))
            elif "tables" not in s:
                print(json.dumps({"state": "SECTION_WITHHELD", "withheld": s.get("withheld"), "rules": s.get("rules")}))
                raise SystemExit(1)
            else:
                bad = problems(s)
                print(json.dumps({"state": "OK" if not bad else "PROBLEMS", "rules": bad,
                                  "rows": {t: len(v) for t, v in s["tables"].items()}}, sort_keys=True))
                raise SystemExit(1 if bad else 0)
        else:
            raise SystemExit("usage: python -m memelab.catsoc_export import SRC DEST [--commit-time EPOCH] | check SRC")
    except CatsocError as e:
        print(f"catsoc: {e}", file=sys.stderr)
        raise SystemExit(2)
