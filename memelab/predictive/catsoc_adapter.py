"""Phase 10 companion adapter (CM-3, PI-D-130, ED-3): catalyst and social evidence read from state-export versions as of the
export commit, fed to the unchanged Phase 10 functions `socialcat.classify_catalyst` and `socialcat.social_as_of`.

`socialcat.py` is pinned by 18 registry entries and by the Phase 18 pin file, so it is not edited; this module only shapes rows.
Pure: the caller supplies export versions `[{"commit", "commit_time", "doc"}]`, oldest first (as `decisions.candidates`); nothing
here reads git, the network or the clock.

Rules
  - an exact row (sha256 of the canonical row) is available from the commit time of the first export version that carries it in
    a valid `_catsoc` section (`available_at`); before that it does not exist (PI-D-015 as for decision rows, PI-D-021);
  - every time field the classifier or the social function reads is replaced by max(own time, available_at), so a row exported
    later is never seen earlier because its own clock says so;
  - mutable rows (events, accounts, items) use the newest version available at T;
  - identity is exact chain plus mint only; a section that fails `catsoc_export.problems` is ignored as withheld;
  - mint naming and duplicate collapse use the exported hashes and `mints_in_url` / `mints_in_body`: the classifier gets lab-made
    stand-in strings built from them (equal hashes give equal stand-ins; the stand-in names a mint exactly when the original text did);
  - evidence class TEST_ONLY until a phase registers catalyst targets on exported rows.
"""
from __future__ import annotations

import json
import hashlib
from typing import Any, Sequence

from .. import catsoc_export as CE
from . import socialcat as SC

CATALYST_NOT_EXPORTED = SC.CATALYST_STATE_REAL          # CATALYST_TABLES_NOT_EXPORTED
SOCIAL_NOT_EXPORTED = SC.SOCIAL_STATE_REAL              # SOCIAL_TABLES_NOT_EXPORTED
NO_CATALYST = "NO_EXPORTED_CATALYST_FOR_MINT"
NO_SOCIAL = "NO_EXPORTED_SOCIAL_FOR_MINT"
SOCIAL_EXPORTED = "SOCIAL_EXPORTED"
STATE_ORDER = ("VERIFIED", "UNVERIFIED_EVENT", "IDENTITY_UNVERIFIED", "NOT_AVAILABLE_AT_DECISION")
ADAPTER_VERSION = "catsoc-adapter-1"


class CatsocAdapterError(ValueError):
    pass


def _row_sha(row: dict) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _clamp(v: Any, avail: float) -> float:
    return avail if v is None else max(float(v), avail)


def prepare(versions: Sequence[dict]) -> dict:
    """Index export versions: each exact row with its first commit and time, the first commit carrying a valid section, and the
    versions whose section was withheld or refused."""
    rows: dict[str, list[dict]] = {t: [] for t in CE.COLUMNS}
    seen: set[tuple[str, str]] = set()
    first_at = None
    withheld = []
    last = None
    for v in versions:
        t = float(v["commit_time"])
        if last is not None and t < last:
            raise CatsocAdapterError("export versions must be oldest first with non-decreasing commit times")
        last = t
        doc = v.get("doc") or {}
        sec = doc.get("_catsoc") if isinstance(doc, dict) else None
        if sec is None:
            continue
        if not isinstance(sec, dict) or sec.get("version") != CE.VERSION or "tables" not in sec or CE.problems(sec):
            withheld.append({"commit": v.get("commit"), "commit_time": t})
            continue
        first_at = t if first_at is None else first_at
        for tab in CE.COLUMNS:
            for r in sec["tables"][tab]:
                k = (tab, _row_sha(r))
                if k in seen:
                    continue
                seen.add(k)
                rows[tab].append({"row": r, "available_at": t, "first_commit": v.get("commit")})
    return {"rows": rows, "first_section_at": first_at, "withheld": withheld, "versions": len(versions),
            "adapter_version": ADAPTER_VERSION}


def _visible(prep: dict, tab: str, T: float) -> list[dict]:
    return [dict(r["row"], _avail=r["available_at"]) for r in prep["rows"][tab] if r["available_at"] <= T]


def _newest(rows: list[dict], key: str, order: str | None = None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in sorted(rows, key=lambda r: (r["_avail"], float(r.get(order) or 0.0) if order else 0.0)):
        out[r[key]] = r
    return out


def _exported_by(prep: dict, T: float) -> bool:
    return prep["first_section_at"] is not None and prep["first_section_at"] <= float(T)


def catalyst_as_of(prep: dict, chain: str, mint: str, decision_time: float) -> dict:
    """Catalyst evidence of one exact (chain, mint) at T from export versions."""
    Tq = float(decision_time)
    base = {"chain": chain, "mint": mint, "decision_time": Tq, "source": "STATE_EXPORT", "available_at_basis": "EXPORT_FIRST_COMMIT",
            "evidence_class": "TEST_ONLY", "adapter_version": ADAPTER_VERSION, "probability": None}
    if not _exported_by(prep, Tq):
        return {**base, "state": CATALYST_NOT_EXPORTED, "events": []}
    links = _visible(prep, "catalyst_token_links", Tq)
    refs = sorted({k["event_ref"] for k in links if k.get("chain") == chain and k.get("mint") == mint})
    if not refs:
        return {**base, "state": NO_CATALYST, "events": []}
    events = _newest(_visible(prep, "catalyst_events", Tq), "event_ref", "updated_at")
    roles_all = _visible(prep, "catalyst_event_sources", Tq)
    items_all = _newest(_visible(prep, "catalyst_items", Tq), "item_ref")
    revs_all = _visible(prep, "catalyst_event_revisions", Tq)
    srcs = _newest(_visible(prep, "catalyst_sources", Tq), "source_id")
    groups = {s: r.get("source_group") for s, r in srcs.items()}
    official = sorted(s for s, r in srcs.items() if r.get("tier") == "official")
    out = []
    for er in refs:
        ev = events.get(er)
        if ev is None:
            out.append({"event_key": er, "state": "NOT_AVAILABLE_AT_DECISION", "reasons": ["EVENT_ROW_NOT_EXPORTED_BY_T"],
                        "probability": None, "probability_allowed": False})
            continue
        e = {k: v for k, v in ev.items() if not k.startswith("_")}
        e["event_key"] = er
        for f in ("updated_at", "discovered_at", "created_at"):
            e[f] = _clamp(e.get(f), ev["_avail"])
        roles = {r["item_ref"]: r["role"] for r in roles_all if r["event_ref"] == er}
        items = []
        for ir in sorted(roles):
            it = items_all.get(ir)
            if it is None:
                continue
            url = ("catsoc:url:" + it["url_sha256"] + "".join(" " + m for m in it.get("mints_in_url") or [])) if it.get("url_sha256") else None
            body = ("catsoc:body:" + it["body_norm_sha256"] + "".join(" " + m for m in it.get("mints_in_body") or [])) \
                if it.get("body_norm_sha256") else None
            items.append({"id": ir, "source_id": it.get("source_id"), "url": url, "body": body,
                          "first_seen_at": _clamp(it.get("first_seen_at"), it["_avail"])})
        revs = [{"id": i, "kind": r.get("kind"), "field": r.get("field"), "old_value": r.get("old_value"), "new_value": r.get("new_value"),
                 "source_id": r.get("source_id"), "revised_at": _clamp(r.get("revised_at"), r["_avail"])}
                for i, r in enumerate(sorted((r for r in revs_all if r["event_ref"] == er), key=lambda r: (r["_avail"], float(r.get("revised_at") or 0))))]
        lks = [{"mint": k.get("mint"), "chain": k.get("chain"), "link_type": k.get("link_type"), "link_strength": k.get("link_strength"),
                "linked_at": _clamp(k.get("linked_at"), k["_avail"])} for k in links if k["event_ref"] == er]
        res = SC.classify_catalyst(e, items, roles, revs, lks, chain=chain, mint=mint, decision_time=Tq, source_groups=groups,
                                   official_sources=official)
        res = {k: v for k, v in res.items() if k != "rows_audited"} | {"rows_audited": res.get("rows_audited")}
        out.append(res)
    states = [o["state"] for o in out]
    best = min(states, key=STATE_ORDER.index) if states else NO_CATALYST
    return {**base, "state": best, "events": out}


def _social_tables(prep: dict, T: float) -> dict[str, list[dict]]:
    v = lambda t: _visible(prep, t, T)
    acc = _newest(v("social_accounts"), "account_ref")
    items = _newest(v("social_items"), "item_ref")
    obs = sorted(v("social_observations"), key=lambda o: (_clamp(o.get("ingested_at"), o["_avail"]), str(o.get("observation_ref"))))
    return {
        "social_accounts": [{"account_id": a["account_ref"], "platform": a.get("platform"), "account_kind": a.get("account_kind"),
                             "identity_status": a.get("identity_status"),
                             "identity_checked_at": None if a.get("identity_checked_at") is None else _clamp(a["identity_checked_at"], a["_avail"])}
                            for a in acc.values()],
        "social_items": [{"item_key": i["item_ref"], "platform": i.get("platform"), "account_id": i.get("account_ref"),
                          "first_ingested_at": _clamp(i.get("first_ingested_at"), i["_avail"])} for i in items.values()],
        "social_observations": [{"id": n, "item_key": o["item_ref"], "account_id": o.get("account_ref"),
                                 "ingested_at": _clamp(o.get("ingested_at"), o["_avail"]), "retrieval_status": o.get("retrieval_status"),
                                 "content_hash": o.get("content_hash")} for n, o in enumerate(obs)],
        "social_item_versions": [{"item_key": x["item_ref"], "version_kind": x.get("version_kind"), "content_hash": x.get("content_hash"),
                                  "first_recorded_at": _clamp(x.get("first_recorded_at"), x["_avail"])} for x in v("social_item_versions")],
        "social_token_resolutions": [{"item_key": r["item_ref"], "mention_kind": r.get("mention_kind"), "status": r.get("status"),
                                      "resolved_chain": r.get("resolved_chain"), "resolved_contract": r.get("resolved_contract"),
                                      "resolved_at": _clamp(r.get("resolved_at"), r["_avail"])} for r in v("social_token_resolutions")],
        "social_claims": [{"item_key": c["item_ref"], "claim_type": c.get("claim_type"), "direction": c.get("direction"),
                           "extracted_at": _clamp(c.get("extracted_at"), c["_avail"])} for c in v("social_claims")],
        "social_claim_extractions": [{"extraction_id": x["extraction_ref"], "item_key": x["item_ref"], "extractor": x.get("extractor"),
                                      "extracted_at": _clamp(x.get("extracted_at"), x["_avail"])} for x in v("social_claim_extractions")],
        "social_trader_accounts": [{"trader_id": t["trader_ref"], "account_id": t["account_ref"],
                                    "linked_at": _clamp(t.get("linked_at"), t["_avail"])} for t in v("social_trader_accounts")],
        "social_token_refs": [{"ref_kind": r.get("ref_kind"), "chain": r.get("chain"), "contract": r.get("contract"),
                               "first_seen_at": _clamp(r.get("first_seen_at"), r["_avail"])} for r in v("social_token_refs")],
        "social_registry_entities": [{"entity_id": e["entity_ref"], "entity_kind": e.get("entity_kind"), "account_id": e.get("account_ref")}
                                     for e in v("social_registry_entities")],
        "social_registry_reviews": [{"target_type": r.get("target_type"), "target_id": r.get("target_ref"), "to_state": r.get("to_state"),
                                     "reviewed_at": _clamp(r.get("reviewed_at"), r["_avail"])} for r in v("social_registry_reviews")],
    }


def social_as_of(prep: dict, chain: str, mint: str, decision_time: float, *, track_rows: Sequence[dict] = ()) -> dict:
    """Social evidence of one exact (chain, mint) at T from export versions (account labels in replay mode: known at T only)."""
    Tq = float(decision_time)
    base = {"chain": chain, "mint": mint, "decision_time": Tq, "source": "STATE_EXPORT", "available_at_basis": "EXPORT_FIRST_COMMIT",
            "evidence_class": "TEST_ONLY", "adapter_version": ADAPTER_VERSION, "llm_used": False}
    if not _exported_by(prep, Tq):
        return {**base, "state": SOCIAL_NOT_EXPORTED, "values": None}
    tabs = _social_tables(prep, Tq)
    if not any(r["status"] == "resolved" and r["resolved_chain"] == chain and r["resolved_contract"] == mint
               for r in tabs["social_token_resolutions"]):
        return {**base, "state": NO_SOCIAL, "values": None}
    res = SC.social_as_of(tabs, chain, mint, Tq, track_rows=track_rows, accounts_read_at=None)
    return {**base, **{k: v for k, v in res.items() if k not in ("evidence_class",)}, "state": SOCIAL_EXPORTED}


def states_as_of(prep: dict, chain: str, mint: str, decision_time: float) -> dict:
    """The two states a socialcat-1 snapshot would carry for this exact (chain, mint) at T, read from the exports."""
    c = catalyst_as_of(prep, chain, mint, decision_time)
    s = social_as_of(prep, chain, mint, decision_time)
    return {"catalyst_state": c["state"], "social_state": s["state"], "catalyst": c, "social": s}
