"""CLI for the source and trader registry: `python -m memelab social registry <action> ...` (Phase 08).

  registry import FILE [--meta M] [--dry-run]       safe import of a permitted list (registry_import.py); creates candidates only
  registry import-catalyst [--dry-run]              bring the repo research list in as unverified, undated candidates
  registry add account|wallet|org|network ...       manual entry (a person adds a source or a wallet they have a reason to track)
  registry evidence ENTITY --kind K --ref R ...     attach evidence (manual note with a URL, or an observation id)
  registry link --type T --from A --to B ...        record an assertion (wallet claim, label, proof, same operator, organization, network)
  registry review-link LINK --approve|--reject      only reviewed links count toward corroboration and merges
  registry retract-link LINK                        append a retraction; history stays
  registry list [--q TEXT] [filters] [--json]       searchable list, ordered by label (the registry never ranks)
  registry show ENTITY [--json]                     candidate, evidence, links, wallets, listings, warnings, review history
  registry approve | reject | update ENTITY         manual decisions; every one is logged with reviewer and reason
  registry category ENTITY CATEGORY --propose|--confirm|--retract
  registry account-status ENTITY SUSPENDED|NOT_FOUND|UNVERIFIED
  registry check-listing LISTING RESULT             evaluate a list's own claim, separately from ownership
  registry attribution ACCOUNT WALLET [--as-of T]   what the registry can say about control of the wallet
  registry discover [--run N]                       propose originators and amplifiers from a stored narrative snapshot
  registry status                                   counts, including how many captures are real and how many fixtures

Exit codes: 0 done, 1 refused (message on stderr, nothing written), 2 usage.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from .. import db
from . import registry as R, registry_import as RI


def _out(obj) -> None:
    print(json.dumps(obj, indent=1, sort_keys=True, default=str))


def _con(a, write: bool):
    dbp = Path(a.db) if a.db else db.DB_PATH
    if write:
        db.init_db(dbp)
    elif not dbp.exists():
        print(json.dumps({"error": "no database", "path": str(dbp)}), file=sys.stderr)
        raise SystemExit(1)
    con = sqlite3.connect(str(dbp))
    con.row_factory = sqlite3.Row
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name='social_registry_entities'").fetchone():
        con.close()
        print(json.dumps({"error": "registry tables not found; run a registry write command or social schema migrate"}), file=sys.stderr)
        raise SystemExit(1)
    return con, dbp


def _tracked(dbp: Path) -> bool:
    return dbp.resolve() == (db.DATA_DIR / "memelab.sqlite").resolve()


def _precheck(a, act: str):
    """Refuse before the database is even opened: demonstration data and the repo research list never go to the tracked database by accident."""
    dbp = Path(a.db) if a.db else db.DB_PATH
    if not _tracked(dbp):
        return None
    if act == "import":
        try:
            doc, _ = RI.read_file(a.file, a.meta)
        except RI.ImportRefused:
            return None
        if isinstance(doc, dict) and isinstance(doc.get("source"), dict) and doc["source"].get("is_fixture"):
            return {"status": "REFUSED", "code": "FIXTURE_IN_TRACKED_DB", "detail": "fixtures are never written to the tracked database; use --db", "written": False}
    if act == "import-catalyst" and not a.dry_run and not a.allow_tracked_db:
        return {"status": "REFUSED", "code": "TRACKED_DB", "detail": "this writes the tracked database; pass --allow-tracked-db to do it on purpose", "written": False}
    return None


def cmd_registry(a):
    act = a.reg_cmd
    write = act not in ("list", "show", "attribution", "status")
    refused = _precheck(a, act) if act in ("import", "import-catalyst") else None
    if refused:
        _out(refused)
        raise SystemExit(1)
    con, dbp = _con(a, write)
    try:
        res = _dispatch(a, act, con, dbp)
        if write:
            con.commit()
    except (ValueError, KeyError) as e:
        con.rollback()
        print(json.dumps({"error": str(e).strip("'\"")}), file=sys.stderr)
        raise SystemExit(1)
    finally:
        con.close()
    if isinstance(res, str):
        print(res)
    elif res is not None:
        _out(res)
    if isinstance(res, dict) and res.get("status") == "REFUSED":
        raise SystemExit(1)
    raise SystemExit(0)


def _dispatch(a, act, con, dbp):
    now = a.now
    if act == "import":
        return RI.import_file(con, a.file, meta=a.meta, dry_run=a.dry_run, now=now)
    if act == "import-catalyst":
        return R.import_catalyst_list(con, now=now, dry_run=a.dry_run)
    if act == "add":
        fx = a.fixture_label
        if a.kind == "account":
            eid = R.ensure_account(con, a.platform, handle=a.handle, provider_user_id=a.provider_id, display_name=a.display_name,
                                   profile_url=a.profile_url, fixture_label=fx, now=now)
        elif a.kind == "wallet":
            eid = R.ensure_wallet(con, a.chain, a.address, fixture_label=fx, now=now)
        elif a.kind == "org":
            eid = R.ensure_org(con, a.key, a.label, fixture_label=fx, now=now)
        else:
            eid = R.ensure_network(con, a.key, a.label, fixture_label=fx, now=now)
        return {"entity_id": eid, "review_state": "CANDIDATE", "note": "added as a candidate with no evidence; add evidence before approving"}
    if act == "evidence":
        at = R.store.to_utc(a.captured_at)
        kind = a.kind
        ref = a.ref
        created = R.add_evidence(con, a.entity, kind, ref, url=a.url, captured_at=at, note=a.note, now=now)
        return {"entity_id": a.entity, "evidence_added": created}
    if act == "link":
        return R.add_link(con, link_type=a.type, from_entity=a.from_entity, to_entity=a.to_entity, basis=a.basis, recorded_by=a.by,
                          asserted_by=a.asserted_by, confidence=a.confidence, evidence_ref=a.ref, valid_from=a.valid_from, valid_to=a.valid_to,
                          asserted_at=a.asserted_at, note=a.note, now=now)
    if act == "review-link":
        return R.review_link(con, a.link, "APPROVED" if a.approve else "REJECTED", reviewer=a.reviewer, reason=a.reason, now=now)
    if act == "retract-link":
        return R.retract_link(con, a.link, reviewer=a.reviewer, reason=a.reason, now=now)
    if act == "list":
        rows = R.search(con, q=a.q, kind=a.kind, review_state=a.state, watch=a.watch, category=a.category, platform=a.platform,
                        fixture=True if a.fixture else False if a.real else None, stale=True if a.stale else None,
                        attribution=a.attribution, suspended=True if a.suspended else None, limit=a.limit, now=now)
        if a.json:
            return {"count": len(rows), "ordering": "label, then id; the registry never ranks", "entities": rows}
        lines = [f"{len(rows)} entities (ordered by label; no ranking, no scores)"]
        for r in rows:
            cats = ",".join(f"{k}:{v}" for k, v in sorted(r["categories"].items())) or "-"
            lines.append(f"{r['entity_id']} | {r['kind']} | {r['review_state']}/{r['watch_status']} | {r['label']} | wallet {r['wallet_attribution'] or '-'} "
                         f"| categories {cats} | flags {','.join(r['flags']) or '-'}")
        return "\n".join(lines)
    if act == "show":
        v = R.show(con, a.entity, now=now)
        return v if a.json else R.report(v)
    if act == "approve":
        return R.approve(con, a.entity, reviewer=a.reviewer, reason=a.reason, specialty=a.specialty, topical_focus=a.focus, watch=a.watch,
                         accept_stale_reason=a.accept_stale_reason, now=now)
    if act == "reject":
        return R.reject(con, a.entity, reviewer=a.reviewer, reason=a.reason, now=now)
    if act == "update":
        return R.update_record(con, a.entity, reviewer=a.reviewer, specialty=a.specialty, topical_focus=a.focus, follow_reason=a.reason,
                               watch_status=a.watch, now=now)
    if act == "category":
        st = "PROPOSED" if a.propose else "CONFIRMED" if a.confirm else "RETRACTED"
        return R.set_category(con, a.entity, a.category, st, basis=a.basis, set_by=a.reviewer, evidence_ref=a.ref, now=now)
    if act == "account-status":
        return R.set_account_status(con, a.entity, a.status, reviewer=a.reviewer, reason=a.reason, evidence_ref=a.ref, checked_at=a.checked_at, now=now)
    if act == "check-listing":
        return R.review_listing_claim(con, a.listing, a.result, reviewer=a.reviewer, evidence_ref=a.ref, now=now)
    if act == "attribution":
        return R.wallet_attribution(con, a.account, a.wallet, as_of=a.as_of)
    if act == "discover":
        return R.discover_from_narratives(con, a.run, min_amplified=a.min_amplified, now=now)
    if act == "status":
        out = R.counts(con)
        out["live_data"] = "none: no permitted live list has been supplied; every capture here is a fixture" if out["live_captures"] == 0 else "see captures"
        return out
    raise ValueError(f"unknown registry action {act}")


def add_parser(ssp) -> None:
    p = ssp.add_parser("registry", help="source and trader registry: candidates, evidence, review, wallets, categories (Phase 08)")
    sub = p.add_subparsers(dest="reg_cmd", required=True)

    def common(q):
        q.add_argument("--db", help="database path (default: MEMELAB_DB or data/memelab.sqlite)")
        q.add_argument("--now", type=float, help="fixed clock (epoch seconds)")
        q.set_defaults(fn=cmd_registry)
        return q

    q = common(sub.add_parser("import", help="safe import of a permitted list file (JSON, or CSV with --meta)"))
    q.add_argument("file")
    q.add_argument("--meta")
    q.add_argument("--dry-run", action="store_true")
    q = common(sub.add_parser("import-catalyst", help="import the repo research list as unverified candidates"))
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--allow-tracked-db", action="store_true")
    q = common(sub.add_parser("add", help="manually add an entity"))
    q.add_argument("kind", choices=["account", "wallet", "org", "network"])
    q.add_argument("--platform"); q.add_argument("--handle"); q.add_argument("--provider-id"); q.add_argument("--display-name")
    q.add_argument("--profile-url"); q.add_argument("--chain"); q.add_argument("--address"); q.add_argument("--key"); q.add_argument("--label")
    q.add_argument("--fixture-label")
    q = common(sub.add_parser("evidence", help="attach evidence to an entity"))
    q.add_argument("entity")
    q.add_argument("--kind", required=True, choices=["MANUAL_NOTE", "OBSERVATION"])
    q.add_argument("--ref", required=True, help="https URL or observation:<id>")
    q.add_argument("--url"); q.add_argument("--captured-at"); q.add_argument("--note")
    q = common(sub.add_parser("link", help="record an assertion between two entities"))
    q.add_argument("--type", required=True, choices=sorted(R.LINK_RULES))
    q.add_argument("--from", dest="from_entity", required=True)
    q.add_argument("--to", dest="to_entity", required=True)
    q.add_argument("--basis", required=True)
    q.add_argument("--by", required=True, help="who is recording this")
    q.add_argument("--asserted-by", help="entity that makes the statement (required for a third-party label)")
    q.add_argument("--confidence", default="UNKNOWN", choices=list(R.CONFIDENCES))
    q.add_argument("--ref"); q.add_argument("--valid-from"); q.add_argument("--valid-to"); q.add_argument("--asserted-at"); q.add_argument("--note")
    q = common(sub.add_parser("review-link", help="approve or reject a link"))
    q.add_argument("link", type=int)
    g = q.add_mutually_exclusive_group(required=True)
    g.add_argument("--approve", action="store_true"); g.add_argument("--reject", action="store_true")
    q.add_argument("--reviewer", required=True); q.add_argument("--reason", required=True)
    q = common(sub.add_parser("retract-link", help="retract a link (append-only)"))
    q.add_argument("link", type=int)
    q.add_argument("--reviewer", required=True); q.add_argument("--reason", required=True)
    q = common(sub.add_parser("list", help="searchable list; ordered by label, never by rank"))
    q.add_argument("--q"); q.add_argument("--kind", choices=list(R.KINDS)); q.add_argument("--state", choices=["CANDIDATE", "APPROVED", "REJECTED"])
    q.add_argument("--watch", choices=list(R.WATCH)); q.add_argument("--category", choices=list(R.CATEGORIES)); q.add_argument("--platform")
    q.add_argument("--attribution", choices=list(R.LEVELS))
    q.add_argument("--fixture", action="store_true"); q.add_argument("--real", action="store_true")
    q.add_argument("--stale", action="store_true", help="only records whose evidence is all stale or undated")
    q.add_argument("--suspended", action="store_true"); q.add_argument("--limit", type=int, default=200); q.add_argument("--json", action="store_true")
    q = common(sub.add_parser("show", help="one entity: candidate, evidence, links, wallets, listings, warnings, review history"))
    q.add_argument("entity"); q.add_argument("--json", action="store_true")
    q = common(sub.add_parser("approve", help="approve as a research source worth watching (not as profitable or correct)"))
    q.add_argument("entity"); q.add_argument("--reviewer", required=True); q.add_argument("--reason", required=True, help="why follow, in your own words")
    q.add_argument("--specialty"); q.add_argument("--focus"); q.add_argument("--watch", action="store_true")
    q.add_argument("--accept-stale-reason", help="required when all evidence is stale or undated")
    q = common(sub.add_parser("reject", help="reject a candidate"))
    q.add_argument("entity"); q.add_argument("--reviewer", required=True); q.add_argument("--reason", required=True)
    q = common(sub.add_parser("update", help="update specialty, focus, reason or watch status"))
    q.add_argument("entity"); q.add_argument("--reviewer", required=True)
    q.add_argument("--specialty"); q.add_argument("--focus"); q.add_argument("--reason"); q.add_argument("--watch", choices=list(R.WATCH))
    q = common(sub.add_parser("category", help="propose, confirm or retract a category"))
    q.add_argument("entity"); q.add_argument("category", choices=list(R.CATEGORIES))
    g = q.add_mutually_exclusive_group(required=True)
    g.add_argument("--propose", action="store_true"); g.add_argument("--confirm", action="store_true"); g.add_argument("--retract", action="store_true")
    q.add_argument("--basis", required=True); q.add_argument("--reviewer", required=True); q.add_argument("--ref")
    q = common(sub.add_parser("account-status", help="record suspension, disappearance or reset of a platform account"))
    q.add_argument("entity"); q.add_argument("status", choices=["SUSPENDED", "NOT_FOUND", "UNVERIFIED"])
    q.add_argument("--reviewer", required=True); q.add_argument("--reason", required=True); q.add_argument("--ref"); q.add_argument("--checked-at")
    q = common(sub.add_parser("check-listing", help="review a list's own claim (rank or figure), separately from ownership"))
    q.add_argument("listing", type=int); q.add_argument("result", choices=["CORROBORATED", "CONTRADICTED", "NOT_CHECKABLE"])
    q.add_argument("--reviewer", required=True); q.add_argument("--ref")
    q = common(sub.add_parser("attribution", help="what the registry can say about an account controlling a wallet"))
    q.add_argument("account"); q.add_argument("wallet"); q.add_argument("--as-of")
    q = common(sub.add_parser("discover", help="propose categories from a stored narrative snapshot"))
    q.add_argument("--run", type=int); q.add_argument("--min-amplified", type=int, default=3)
    common(sub.add_parser("status", help="registry counts"))
