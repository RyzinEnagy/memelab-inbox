"""CLI for wallet attribution and monitoring: `python -m memelab social wallet <action> ...` (Phase 09).

  wallet track add CHAIN ADDRESS --reason R --by NAME [--max-tx N] [--allow-custody]   start watching a public wallet (no owner claimed)
  wallet track pause|resume|remove CHAIN ADDRESS --by NAME --reason R                  history is kept; nothing is deleted
  wallet track list [--status S]
  wallet plan                                                                          wallets and limits a Helius fetch plan would cover
  wallet ingest FILE [--max-age-hours H] [--fixture]                                   store events from a provider document
  wallet events [--chain C] [--wallet A] [--type T ...] [--json]
  wallet show CHAIN ADDRESS                                                            tracking, label, coverage, recent events (no P&L)
  wallet verify EVENT [--source FILE]                                                  provenance chain, hashes recomputed against the file
  wallet label CHAIN ADDRESS KIND --ref URL --by NAME [--text T]                       custody, protocol, pool, or no special label
  wallet assert ACCOUNT CHAIN ADDRESS --type T --ref R --by NAME [...]                 record an attribution assertion
  wallet review ID --approve|--reject --by NAME --reason R
  wallet revoke ID --by NAME --reason R
  wallet why ACCOUNT CHAIN ADDRESS [--as-of T] [--json]                                why the wallet is or is not linked to the account
  wallet adopt-registry                                                                bring Phase 08 registry wallet links in as assertions
  wallet funding                                                                       derive funding hypotheses from stored events
  wallet status                                                                        counts

Exit codes: 0 done, 1 refused (message on stderr, nothing written), 2 usage.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from .. import db
from . import wallet_activity as A, wallet_assertions as W


def _out(o) -> None:
    print(json.dumps(o, indent=1, sort_keys=True, default=str))


def _tracked(dbp: Path) -> bool:
    return dbp.resolve() == (db.DATA_DIR / "memelab.sqlite").resolve()


def _con(a, write: bool):
    dbp = Path(a.db) if a.db else db.DB_PATH
    if write:
        db.init_db(dbp)
    elif not dbp.exists():
        print(json.dumps({"error": "no database", "path": str(dbp)}), file=sys.stderr)
        raise SystemExit(1)
    con = sqlite3.connect(str(dbp))
    con.row_factory = sqlite3.Row
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name='social_tracked_wallets'").fetchone():
        con.close()
        print(json.dumps({"error": "wallet tables not found; run a wallet write command or social schema migrate"}), file=sys.stderr)
        raise SystemExit(1)
    return con, dbp


READ = {"events", "show", "verify", "why", "status", "plan"}


def cmd_wallet(a):
    act = a.w_cmd + (f" {a.t_cmd}" if a.w_cmd == "track" else "")
    write = (a.w_cmd not in READ) and act != "track list"
    dbp = Path(a.db) if a.db else db.DB_PATH
    if write and _tracked(dbp) and (getattr(a, "fixture", False) or getattr(a, "fixture_label", None)):
        print(json.dumps({"error": "fixtures are never written to the tracked database; use --db"}), file=sys.stderr)
        raise SystemExit(1)
    con, dbp = _con(a, write)
    try:
        res = _dispatch(a, con, dbp)
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
    if isinstance(res, dict) and res.get("status") == "FAILED":
        raise SystemExit(1)
    raise SystemExit(0)


def _dispatch(a, con, dbp):
    now = a.now
    c = a.w_cmd
    if c == "track":
        t = a.t_cmd
        if t == "add":
            return A.add_wallet(con, a.chain, a.address, reason=a.reason, added_by=a.by, max_tx=a.max_tx, allow_custody=a.allow_custody, fixture=a.fixture, now=now)
        if t in ("pause", "resume", "remove"):
            return A.set_status(con, a.chain, a.address, {"pause": "PAUSED", "resume": "ACTIVE", "remove": "REMOVED"}[t], by=a.by, reason=a.reason, now=now)
        return A.list_wallets(con, a.status)
    if c == "plan":
        ws = [w for w in A.list_wallets(con, "ACTIVE") if w["chain"] == "solana"]
        return {"provider": "helius", "projection": "helius_wallet_tx", "wallets": [{"wallet": w["wallet_address"], "limit": w["max_tx_per_fetch"]} for w in ws],
                "note": "Plan.wallet_activity(wallets, limit) builds the requests; the Helius key stays in data/config.json and is never printed",
                "unavailable": [w["wallet_address"] for w in A.list_wallets(con, "ACTIVE") if w["chain"] != "solana"]}
    if c == "ingest":
        return A.ingest_file(con, a.file, now=now, max_age=int(a.max_age_hours * 3600), fixture=a.fixture)
    if c == "events":
        ev = A.events(con, chain=a.chain, wallet=a.wallet, types=tuple(a.type) if a.type else None, limit=a.limit)
        if a.json:
            return {"count": len(ev), "note": "observations only; no profit, loss or price is computed", "events": ev}
        return "\n".join([f"{len(ev)} events (observations only; no P&L)"] + [
            f"{e['event_id']} {e['block_time']:.0f} {e['chain']}:{e['wallet_address'][:8]}.. {e['event_type']}{'/' + e['swap_side'] if e['swap_side'] else ''} {e['signature'][:14]}.. {e['classification_rule']}" for e in ev])
    if c == "show":
        return A.report(con, a.chain, a.address)
    if c == "verify":
        return A.provenance(con, a.event, source_file=a.source)
    if c == "label":
        return W.set_label(con, a.chain, a.address, a.kind, source_ref=a.ref, set_by=a.by, text=a.text, now=now)
    if c == "assert":
        msg = Path(a.message_file).read_text() if a.message_file else None
        return W.record(con, account_entity=a.account, chain=a.chain, wallet_address=a.address, evidence_type=a.type, evidence_ref=a.ref, recorded_by=a.by,
                        asserter_entity=a.asserter, message=msg, signature=a.signature, observed_at=a.observed_at, valid_from=a.valid_from, valid_to=a.valid_to,
                        confidence=a.confidence, note=a.note, supersedes=a.supersedes, now=now)
    if c == "review":
        return W.review(con, a.assertion, "APPROVED" if a.approve else "REJECTED", reviewer=a.by, reason=a.reason, now=now)
    if c == "revoke":
        return W.revoke(con, a.assertion, reviewer=a.by, reason=a.reason, now=now)
    if c == "why":
        v = W.explain(con, a.account, a.chain, a.address, as_of=a.as_of, now=now)
        return v if a.json else W.report(v)
    if c == "adopt-registry":
        return W.adopt_registry_links(con, now=now)
    if c == "funding":
        return A.derive_funding_hypotheses(con, now=now)
    if c == "status":
        n = lambda q: con.execute(q).fetchone()[0]
        return {"tracked": {r[0]: r[1] for r in con.execute("SELECT status, COUNT(*) FROM social_tracked_wallets GROUP BY status")},
                "events": {r[0]: r[1] for r in con.execute("SELECT event_type, COUNT(*) FROM social_wallet_events GROUP BY event_type")},
                "fetches": {r[0]: r[1] for r in con.execute("SELECT status, COUNT(*) FROM social_wallet_fetches GROUP BY status")},
                "assertions": {f"{r[0]}/{r[1]}": r[2] for r in con.execute("SELECT review_state, status, COUNT(*) FROM social_wallet_assertions GROUP BY 1,2")},
                "fixture_events": n("SELECT COUNT(*) FROM social_wallet_events WHERE is_fixture=1"), "pnl": "not computed in this phase"}
    raise ValueError(f"unknown action {c}")


def add_parser(ssp) -> None:
    p = ssp.add_parser("wallet", help="wallet attribution assertions and wallet-level monitoring (Phase 09)")
    sub = p.add_subparsers(dest="w_cmd", required=True)

    def common(q):
        q.add_argument("--db"); q.add_argument("--now", type=float, help="fixed clock (epoch seconds)")
        q.set_defaults(fn=cmd_wallet, t_cmd=None)
        return q

    tr = sub.add_parser("track", help="add, pause, resume, remove or list tracked wallets")
    ts = tr.add_subparsers(dest="t_cmd", required=True)
    q = common(ts.add_parser("add")); q.set_defaults(t_cmd="add")
    q.add_argument("chain"); q.add_argument("address"); q.add_argument("--reason", required=True); q.add_argument("--by", required=True)
    q.add_argument("--max-tx", type=int, default=50); q.add_argument("--allow-custody", action="store_true"); q.add_argument("--fixture", action="store_true")
    for n in ("pause", "resume", "remove"):
        q = common(ts.add_parser(n)); q.set_defaults(t_cmd=n)
        q.add_argument("chain"); q.add_argument("address"); q.add_argument("--by", required=True); q.add_argument("--reason", required=True)
    q = common(ts.add_parser("list")); q.set_defaults(t_cmd="list"); q.add_argument("--status", choices=["ACTIVE", "PAUSED", "REMOVED"])
    common(sub.add_parser("plan", help="wallets a Helius fetch plan would cover"))
    q = common(sub.add_parser("ingest", help="store events from a provider document"))
    q.add_argument("file"); q.add_argument("--max-age-hours", type=float, default=12.0); q.add_argument("--fixture", action="store_true")
    q = common(sub.add_parser("events", help="stored events, in block-time order"))
    q.add_argument("--chain"); q.add_argument("--wallet"); q.add_argument("--type", action="append", choices=list(A.EVENT_TYPES))
    q.add_argument("--limit", type=int, default=200); q.add_argument("--json", action="store_true")
    q = common(sub.add_parser("show", help="one wallet: tracking, label, coverage and recent events"))
    q.add_argument("chain"); q.add_argument("address")
    q = common(sub.add_parser("verify", help="provenance chain of one event"))
    q.add_argument("event", type=int); q.add_argument("--source")
    q = common(sub.add_parser("label", help="label a wallet as custody, protocol, pool or nothing special"))
    q.add_argument("chain"); q.add_argument("address"); q.add_argument("kind", choices=list(W.LABEL_KINDS))
    q.add_argument("--ref", required=True); q.add_argument("--by", required=True); q.add_argument("--text")
    q = common(sub.add_parser("assert", help="record an attribution assertion"))
    q.add_argument("account"); q.add_argument("chain"); q.add_argument("address")
    q.add_argument("--type", required=True, choices=list(W.EVIDENCE_TYPES)); q.add_argument("--ref", required=True); q.add_argument("--by", required=True)
    q.add_argument("--asserter"); q.add_argument("--message-file", help="the signed message, as published (its hash is stored, not its text)")
    q.add_argument("--signature"); q.add_argument("--observed-at"); q.add_argument("--valid-from"); q.add_argument("--valid-to")
    q.add_argument("--confidence", choices=["HIGH", "MODERATE", "LOW", "UNKNOWN"]); q.add_argument("--note"); q.add_argument("--supersedes", type=int)
    q = common(sub.add_parser("review", help="approve or reject an assertion"))
    q.add_argument("assertion", type=int)
    g = q.add_mutually_exclusive_group(required=True)
    g.add_argument("--approve", action="store_true"); g.add_argument("--reject", action="store_true")
    q.add_argument("--by", required=True); q.add_argument("--reason", required=True)
    q = common(sub.add_parser("revoke", help="revoke an assertion (kept, marked revoked)"))
    q.add_argument("assertion", type=int); q.add_argument("--by", required=True); q.add_argument("--reason", required=True)
    q = common(sub.add_parser("why", help="why a wallet is, or is not, linked to an account"))
    q.add_argument("account"); q.add_argument("chain"); q.add_argument("address"); q.add_argument("--as-of"); q.add_argument("--json", action="store_true")
    common(sub.add_parser("adopt-registry", help="adopt Phase 08 registry wallet links as assertions"))
    common(sub.add_parser("funding", help="derive funding hypotheses from stored events"))
    common(sub.add_parser("status", help="counts"))
