"""CLI for the PRE-LAUNCH & NEW-LAUNCH INTELLIGENCE ENGINE (`python -m memelab launch ...`).

Run order ("Find upcoming memecoins"):
  launch plan --id lp_<stamp>                writes three plan groups: lp_<stamp>_ex / _pump / _clanker (+ page to run each on)
  [browser] run each group on its page (collector.js + launch.js loaded), ship, commit, pull
  launch discover --results <ids>            candidates -> upcoming_launches, cohort, alerts; writes <first id>.launch_short.json
  launch deep-plan <short id> --id ld_<stamp> per-shortlist research plans (three groups again)
  [browser] run, ship, pull
  launch assess <short id> --results <all ids>   scores, wallets, monitor windows, hand-overs; writes the report
  launch cohort-plan --id lc_<stamp>         outcome re-reads for cohort tokens (24h / 7d / 30d); then `launch cohort --results lc_<stamp>_pump`
  launch status                              tracked launches, phases, recent alerts
  launch note <launch_id or symbol> ...      record a manual / announced launch (state A, CLAIMED details)
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .. import db
from ..bridge import ingest as bingest
from . import cohort, engine as E, report as REP, sources as S

INBOX = db.DATA_DIR / "inbox"
REPORTS = db.DATA_DIR / "reports"


def _merged(ids: list[str]) -> tuple[dict, float]:
    files = []
    for i in ids:
        hits = [INBOX / f"{i}.result.json"] if (INBOX / f"{i}.result.json").exists() else sorted(INBOX.glob(f"{i}_*.result.json"))
        if not hits:
            print(f"warning: no result file for {i}")
        files += hits
    res = [bingest.load_result(f) for f in files]
    return {k: v[0] for k, v in bingest.merged_bodies(res).items()}, max((r.observed_at for r in res), default=time.time())


def _emit(groups: dict, js: bool):
    for g, p in groups.items():
        if not p.reqs:
            continue
        path = p.save()
        print(f"[{g}] {p.id}: {len(p.reqs)} requests -> {path}\n    run on: {S.GROUP_PAGES[g]}")
        if js:
            print("    " + p.js_call())


def cmd_plan(a):
    _emit(S.discovery(a.id or f"lp_{int(time.time())}"), a.js)


def cmd_discover(a):
    db.init_db()
    bodies, t = _merged(a.results)
    with db.connect() as con:
        d = E.run_discovery(con, bodies, t)
        short = E.shortlist(con, d["cands"], t, a.limit)
    sid = a.id or a.results[0]
    (INBOX / f"{sid}.launch_short.json").write_text(json.dumps({"t": t, "sol_price": d["sol_price"], "eth_price": d["eth_price"], "cands": short,
                                                               "by_state": _states(d["cands"])}, default=str))
    print(f"{len(d['cands'])} launches normalized; states {_states(d['cands'])}; {len(d['alerts'])} alerts; shortlist {len(short)} -> {sid}.launch_short.json")
    for c in short:
        o = c.get("obs") or {}
        print(f"  {c['state']} {c.get('chain'):7} {c.get('launchpad') or '-':22} {str(c.get('symbol'))[:12]:12} mcap {o.get('mcap_usd') or 0:>12,.0f}  prog {o.get('curve_progress_pct') or 0:5.1f}  replies {o.get('replies') or 0:>4}  {c.get('contract')}")


def _states(cands):
    by = {}
    for c in cands.values():
        by[c["state"]] = by.get(c["state"], 0) + 1
    return dict(sorted(by.items()))


def cmd_deep_plan(a):
    sh = json.loads((INBOX / f"{a.short}.launch_short.json").read_text())
    _emit(S.deep(a.id or f"ld_{int(time.time())}", sh["cands"], helius=a.helius), a.js)


def cmd_assess(a):
    db.init_db()
    sh = json.loads((INBOX / f"{a.short}.launch_short.json").read_text())
    bodies, t = _merged(a.results)
    with db.connect() as con:
        E.cohort_ingest(con, bodies, t, sh.get("sol_price"))
        results = E.run_assess(con, bodies, sh["cands"], t, persist=not a.no_persist)
        pads = cohort.launchpad_stats(con, t, persist=False)
        disc = {"cands": {c["launch_id"]: c for c in sh["cands"]}}
        md = REP.render(con, t, results, None, pads)
    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / f"launch_{time.strftime('%Y%m%d_%H%M', time.gmtime(t))}.md"
    out.write_text(md)
    print(f"report -> {out}")
    for r in results:
        c, res = r["c"], r["res"]
        print(f"  {res['status']:20} {res['score']:5.1f} c{res['completeness']:4.0f} {c['state']} {str(c.get('symbol'))[:12]:12} {c.get('launchpad') or '-':20} {c.get('contract')}")
    if a.print:
        print(md)


def cmd_cohort_plan(a):
    db.init_db()
    with db.connect() as con:
        mints = cohort.followup_mints(con, time.time(), a.limit)
    p = S.cohort_followup(a.id or f"lc_{int(time.time())}", mints)
    if not p.reqs:
        print("no cohort tokens due for an outcome reading"); return
    _emit({"pump": p}, a.js)


def cmd_cohort(a):
    db.init_db()
    bodies, t = _merged(a.results)
    with db.connect() as con:
        n = E.cohort_ingest(con, bodies, t, None)
        pads = cohort.launchpad_stats(con, t)
    print(f"{n} cohort outcome readings stored")
    for p, s in pads.items():
        print(f"  {p}: n={s['n']} grad {s['graduation_rate']:.1%} >=100k {s['reach_100k_rate']:.1%} score {s['quality_score']}")


def cmd_status(a):
    db.init_db()
    with db.connect() as con:
        for u in con.execute("SELECT * FROM upcoming_launches WHERE phase IN ('PRE_LAUNCH','NEW_LAUNCH_MONITOR') AND status IS NOT NULL ORDER BY prelaunch_score DESC LIMIT ?", (a.limit,)):
            print(f"{u['phase']:18} {u['status'] or '-':20} {u['prelaunch_score'] or 0:5.1f} {u['state']} {str(u['symbol'])[:12]:12} {u['chain']} {u['launchpad'] or '-'} {u['contract'] or 'NOT YET PUBLISHED'}")
        print("\nrecent alerts:")
        for x in con.execute("SELECT * FROM launch_alerts ORDER BY alerted_at DESC LIMIT 15"):
            print(f"  {time.strftime('%m-%d %H:%M', time.gmtime(x['alerted_at']))} {x['kind']}: {x['text']}")
        n = {r["phase"]: r["n"] for r in con.execute("SELECT phase, COUNT(*) n FROM upcoming_launches GROUP BY phase")}
        c = con.execute("SELECT COUNT(*) n, SUM(sample_basis='newest') nn FROM launch_cohort").fetchone()
        print(f"\nphases {n}; cohort {c['n']} launches ({c['nn']} in the unbiased newest-launch sample)")


def cmd_note(a):
    """Record a launch you heard about. Details are CLAIMED; the contract stays NOT VERIFIED until a chain index reports it."""
    db.init_db()
    t = time.time()
    slug = re.sub(r"[^a-z0-9]+", "-", (a.project or a.symbol or "").lower()).strip("-")
    lid = f"ann:{slug}"
    claimed = {k: v for k, v in (("team_pct", a.team_pct), ("launch_fdv_usd", a.fdv), ("launch_liquidity_usd", a.liquidity), ("circulating_at_launch_pct", a.float_pct)) if v is not None}
    when = None
    if a.when:
        from datetime import datetime
        when = datetime.fromisoformat(a.when.replace("Z", "+00:00")).timestamp()
    with db.connect() as con:
        row = {"project": a.project, "symbol": a.symbol, "chain": a.chain, "launchpad": a.launchpad, "state": "A", "scheduled_at": when, "source": "manual", "sources_json": json.dumps(["manual"]),
               "official_links_json": json.dumps({"url": a.url} if a.url else {}), "tokenomics_json": json.dumps({"basis": "CLAIMED", **claimed}), "team_alloc_pct": a.team_pct,
               "expected_valuation_usd": a.fdv, "expected_liquidity_usd": a.liquidity, "valuation_basis": "CLAIMED" if a.fdv else None,
               "risk_flags_json": json.dumps(["CONTRACT_NOT_YET_VERIFIED"]), "notes": a.note, "updated_at": t, "status": "RESEARCH INCOMPLETE",
               "status_reason": "CONTRACT NOT YET VERIFIED. Manual note; details are claimed until verified"}
        if con.execute("SELECT 1 FROM upcoming_launches WHERE launch_id=?", (lid,)).fetchone():
            row = {k: v for k, v in row.items() if v is not None}
            con.execute(f"UPDATE upcoming_launches SET {','.join(k + '=?' for k in row)} WHERE launch_id=?", list(row.values()) + [lid])
        else:
            db.insert(con, "upcoming_launches", {"launch_id": lid, "discovered_at": t, "phase": "PRE_LAUNCH", **row})
    print(f"{lid}: recorded as ANNOUNCED - NO CONTRACT (CONTRACT NOT YET VERIFIED)")


def add_subparser(sp):
    p = sp.add_parser("launch", help="pre-launch and new-launch intelligence")
    s = p.add_subparsers(dest="launch_cmd", required=True)
    q = s.add_parser("plan"); q.add_argument("--id"); q.add_argument("--js", action="store_true"); q.set_defaults(fn=cmd_plan)
    q = s.add_parser("discover"); q.add_argument("--results", nargs="+", required=True); q.add_argument("--id"); q.add_argument("--limit", type=int, default=E.MAX_SHORTLIST); q.set_defaults(fn=cmd_discover)
    q = s.add_parser("deep-plan"); q.add_argument("short"); q.add_argument("--id"); q.add_argument("--helius", action="store_true"); q.add_argument("--js", action="store_true"); q.set_defaults(fn=cmd_deep_plan)
    q = s.add_parser("assess"); q.add_argument("short"); q.add_argument("--results", nargs="+", required=True); q.add_argument("--no-persist", action="store_true"); q.add_argument("--print", action="store_true"); q.set_defaults(fn=cmd_assess)
    q = s.add_parser("cohort-plan"); q.add_argument("--id"); q.add_argument("--limit", type=int, default=150); q.add_argument("--js", action="store_true"); q.set_defaults(fn=cmd_cohort_plan)
    q = s.add_parser("cohort"); q.add_argument("--results", nargs="+", required=True); q.set_defaults(fn=cmd_cohort)
    q = s.add_parser("status"); q.add_argument("--limit", type=int, default=30); q.set_defaults(fn=cmd_status)
    q = s.add_parser("note"); q.add_argument("--project"); q.add_argument("--symbol"); q.add_argument("--chain"); q.add_argument("--launchpad"); q.add_argument("--when", help="ISO time")
    q.add_argument("--url"); q.add_argument("--team-pct", type=float); q.add_argument("--fdv", type=float); q.add_argument("--liquidity", type=float); q.add_argument("--float-pct", type=float); q.add_argument("--note")
    q.set_defaults(fn=cmd_note)
