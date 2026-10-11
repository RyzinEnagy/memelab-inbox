"""CLI for Catalyst Intelligence (wired into `python -m memelab catalyst ...`).

Run order for a full catalyst pass:
  catalyst plan --id cat_<stamp>           prints (1) the fetch-mode __ML.run call, (2) the navigate-mode URL list
  [browser] run the fetch plan, ship as inbox/cat_<stamp>.json; for each navigate URL: navigate, run
            __CAT.parsePage(kind, source_id), get_page_text, then here: catalyst save-page cat_<stamp> --file page.txt
  catalyst ingest --results cat_<stamp>    items -> events (dedup, corroboration, revisions)
  catalyst match-plan --id catm_<stamp>    prints the Jupiter/DEX Screener search plan for NEW events' terms
  [browser] run, ship, pull as catm_<stamp>
  catalyst match --results catm_<stamp>    verified token links with competing matches
  catalyst assess --results <deep ids>     eight assessments per linked mint that has deep data
  catalyst monitor                         token-first alerts, expiry sweep, outcomes
  catalyst report                          markdown report
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from .. import db
from ..bridge import ingest as bingest
from ..bridge.plan import Plan
from . import assess as A, attention, ingest as I, match as M, monitor as MON, report as R
from .sources import active_sources, sync_registry, TRADER_RESEARCH_LIST

INBOX = db.DATA_DIR / "inbox"


def _merged(result_ids: list[str]) -> dict:
    res = [bingest.load_result(INBOX / f"{i}.result.json") for i in result_ids if (INBOX / f"{i}.result.json").exists()]
    return {k: v[0] for k, v in bingest.merged_bodies(res).items()}


def cmd_plan(a):
    db.init_db()
    with db.connect() as con:
        sync_registry(con)
        fetch_srcs = active_sources(con, modes=("fetch",))
        nav_srcs = active_sources(con, modes=("navigate",))
        traders = [dict(r) for r in con.execute("SELECT * FROM catalyst_sources WHERE source_group='trader' AND enabled=1")]
    plan = Plan(a.id or f"cat_{int(time.time())}")
    for s in fetch_srcs:
        plan.add(f"cat:{s['source_id']}", s["url"], proj=s["parser"] or "raw", delay_ms=400)
    if a.verify_traders:
        for s in traders:
            plan.add(f"xprof:{s['source_id']}", s["url"], proj="x_profile", delay_ms=800)
    print(f"# plan {plan.id} -> {plan.save()}  (preferred: python -m memelab fetch {plan.id})")
    print("# 1) fetch-mode sources (Chrome fallback: run in the example.com tab after loading collector.js AND bridge/catalyst.js):")
    print(plan.js_call() if hasattr(plan, "js_call") else json.dumps(plan.to_dict()))
    print(f"# then: __ML.ship(\"inbox/{plan.id}.json\") ; land ; commit ; pull as {plan.id}")
    print("\n# 2) navigate-mode sources (CORS-blocked). For each: navigate the tab to the URL, then run")
    print("#    __CAT.parsePage(<kind>, <source_id>)  (catalyst.js must be loaded on that page too: eval the raw file first)")
    print("#    then get_page_text and: python -m memelab catalyst save-page <plan id> --file <saved page text>")
    for s in nav_srcs:
        print(f"{s['parser'] or 'rss'}\t{s['source_id']}\t{s['url']}")


def cmd_save_page(a):
    """Append a navigate-mode page JSON ({_cat,...}) into inbox/<id>.result.json under key cat:<source_id>."""
    txt = Path(a.file).read_text()
    js = bingest.clean_page_text(txt)
    page = json.loads(js)
    sid = page.get("_cat")
    if not sid:
        raise SystemExit("page JSON lacks _cat (source id); was __CAT.parsePage run on the page?")
    p = INBOX / f"{a.id}.result.json"
    data = json.loads(p.read_text()) if p.exists() else {"_plan": a.id, "_at": page.get("_at"), "_n": 0}
    data[f"cat:{sid}"] = {"s": page.get("s", 0), "len": len(js), "ms": 0, "body": page.get("body"), "err": page.get("err"), "_cat": sid}
    data["_n"] = len([k for k in data if not k.startswith("_")])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, separators=(",", ":")))
    print(f"saved {sid} -> {p} ({'ok' if page.get('s') == 200 else 'ERR ' + str(page.get('err'))})")


def _S(x, n=600):
    import re as _re
    return None if x is None else _re.sub(r"\s+", " ", str(x)).strip()[:n]


def _parse_feed(xml_text: str) -> list[dict]:
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_text)
    loc = lambda t: t.split("}")[-1]

    def g(el, *names):
        for c in el.iter():
            if c is not el and loc(c.tag) in names:
                return _S("".join(c.itertext()), 1200)
        return None
    items = [e for e in root.iter() if loc(e.tag) == "item"]
    if items:
        return [{"title": g(it, "title"), "link": g(it, "link"), "pub": g(it, "pubDate"), "guid": g(it, "guid"), "desc": g(it, "description"),
                 "author": g(it, "creator", "author"), "src": g(it, "source")} for it in items]
    out = []
    for it in (e for e in root.iter() if loc(e.tag) == "entry"):
        link = next((c.get("href") for c in it if loc(c.tag) == "link"), None)
        out.append({"title": g(it, "title"), "link": link, "pub": g(it, "published", "updated"), "guid": g(it, "id"), "desc": g(it, "summary", "content"), "author": g(it, "name")})
    return out


def _parse_page(kind: str, text: str):
    if kind == "rss":
        return _parse_feed(text)
    j = json.loads(text)
    if kind == "binance_cms":
        d = j.get("data") or {}
        arts = [a for c in d.get("catalogs") or [] for a in c.get("articles") or []] + list(d.get("articles") or [])
        return [{"id": a.get("id"), "code": a.get("code"), "title": _S(a.get("title"), 240), "pub": a.get("releaseDate"),
                 "link": "https://www.binance.com/en/support/announcement/" + a["code"] if a.get("code") else None} for a in arts]
    if kind == "bybit_ann":
        return [{"title": _S(a.get("title"), 240), "desc": _S(a.get("description"), 400), "link": a.get("url"), "pub": a.get("dateTimestamp"),
                 "type": (a.get("type") or {}).get("title"), "tags": a.get("tags")} for a in ((j.get("result") or {}).get("list") or [])]
    if kind == "okx_ann":
        det = ((j.get("data") or [{}])[0] or {}).get("details") or []
        return [{"title": _S(a.get("title"), 240), "link": a.get("url"), "pub": float(a["pTime"]) if a.get("pTime") else None, "type": a.get("annType")} for a in det]
    return j


def cmd_pull_pages(a):
    """Navigate-mode sources as direct API pulls (no browser): fetch, parse like catalyst.js, append into inbox/<id>.result.json.
    Sources that still fail are listed; only those need the Chrome page route."""
    import urllib.request
    from datetime import datetime, timezone
    db.init_db()
    with db.connect() as con:
        sync_registry(con)
        nav = active_sources(con, modes=("navigate",))
    p = INBOX / f"{a.id}.result.json"
    data = json.loads(p.read_text()) if p.exists() else {"_plan": a.id, "_at": datetime.now(timezone.utc).isoformat(), "_n": 0}
    failed = []
    for s in nav:
        sid, kind = s["source_id"], s["parser"] or "rss"
        try:
            req = urllib.request.Request(s["url"], headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0", "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=30) as r:
                text = r.read().decode("utf-8", "replace")
            body = _parse_page(kind, text)
            data[f"cat:{sid}"] = {"s": 200, "len": len(text), "ms": 0, "body": body, "err": None, "_cat": sid}
            print(f"  ok   {sid}: {len(body) if isinstance(body, list) else 1} items")
        except Exception as e:
            failed.append(sid)
            data.setdefault(f"cat:{sid}", {"s": 0, "len": 0, "ms": 0, "body": None, "err": str(e)[:200], "_cat": sid})
            print(f"  FAIL {sid}: {str(e)[:120]}")
        time.sleep(0.5)
    data["_n"] = len([k for k in data if not k.startswith("_")])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, separators=(",", ":")))
    print(f"{len(nav) - len(failed)}/{len(nav)} navigate-mode sources pulled -> {p}" + (f"; Chrome fallback only for: {', '.join(failed)}" if failed else ""))


def cmd_ingest(a):
    db.init_db()
    bodies = {}
    for rid in a.results:
        p = INBOX / f"{rid}.result.json"
        if not p.exists():
            print("missing", p); continue
        data = json.loads(p.read_text())
        for k, v in data.items():
            if k.startswith("cat:") and isinstance(v, dict):
                bodies[k] = {"_cat": k[4:], "s": v.get("s"), "err": v.get("err"), "body": v.get("body")}
            if k.startswith("xprof:") and isinstance(v, dict):
                _verify_trader(k[6:], v)
    stats = I.ingest_bodies(bodies)
    print(json.dumps({k: v for k, v in stats.items() if k != "touched_events"}, indent=1))
    print("touched events:", stats["touched_events"][:50])


def _verify_trader(source_id: str, v: dict):
    body = v.get("body") or {}
    handle = source_id.split(":")[-1]
    with db.connect() as con:
        if v.get("s") == 200 and body.get("exists") and handle.lower() in (body.get("title") or "").lower():
            # no profile text is copied (D-020): the public database records only that the page exists and its
            # title names the handle. A bio in an older result file is ignored.
            note = " | profile page found, title names the handle"
            con.execute("UPDATE catalyst_sources SET identity_verified='VERIFIED', identity_notes=CASE WHEN instr(COALESCE(identity_notes,''), ?) > 0 "
                        "THEN identity_notes ELSE COALESCE(identity_notes,'') || ? END WHERE source_id=?", (note, note, source_id))
        else:
            con.execute("UPDATE catalyst_sources SET identity_verified='NOT_FOUND', last_error=? WHERE source_id=?", (f"profile fetch status {v.get('s')}", source_id))


def cmd_match_plan(a):
    per_event, plan = M.terms_for_events(limit_events=a.limit)
    plan.id = a.id or plan.id
    (INBOX / f"{plan.id}.terms.json").write_text(json.dumps(per_event))
    print(f"# {len(per_event)} events, {len(plan.to_dict().get('reqs', []))} search requests")
    print(plan.js_call() if hasattr(plan, "js_call") else json.dumps(plan.to_dict()))
    print(f"# then: __ML.ship(\"inbox/{plan.id}.json\") ; land ; commit ; pull as {plan.id} ; python -m memelab catalyst match --results {plan.id}")


def cmd_match(a):
    bodies = _merged(a.results)
    per_event = None
    for rid in a.results:
        tp = INBOX / f"{rid}.terms.json"
        if tp.exists():
            per_event = {int(k): v for k, v in json.loads(tp.read_text()).items()}
    print(json.dumps(M.link_events(bodies, per_event, min_liq_usd=a.min_liq), indent=1))


def cmd_assess(a):
    from .. import pipeline
    bodies = _merged(a.results) if a.results else {}
    sol = None
    cg = bodies.get("cg:price") or {}
    if isinstance(cg, dict) and isinstance(cg.get("solana"), dict):
        sol = cg["solana"].get("usd")
    t = time.time()
    done = 0
    with db.connect() as con:
        pairs = [dict(r) for r in con.execute("SELECT l.event_id, l.mint FROM catalyst_token_links l JOIN catalyst_events e ON e.id=l.event_id WHERE e.status NOT IN ('EXPIRED','REJECTED','DENIED','CANCELLED')")]
        events = {r["id"]: dict(r) for r in con.execute("SELECT * FROM catalyst_events")}
        links = {(r["event_id"], r["mint"]): dict(r) for r in con.execute("SELECT * FROM catalyst_token_links")}
    for p in pairs:
        ev = events[p["event_id"]]; link = links[(p["event_id"], p["mint"])]
        core = None
        has_deep = any(k.endswith(p["mint"]) and k.startswith(("jq:", "gt_pools:token:", "rug:")) for k in bodies)
        if has_deep:
            try:
                core = pipeline.analyze_token(p["mint"], bodies, sol_price=sol, persist=a.persist)
            except Exception as e:  # keep assessing with what exists
                print("core analysis failed for", p["mint"][:8], str(e)[:120])
        att = attention.sample_event(p["event_id"], bundle=(core or {}).get("bundle"), t=t)
        res = A.assess(ev, link, att, core, t=t)
        quotes = None
        if core:
            dp = (core.get("modules") or {}).get("depth") or {}
            quotes = {"dated": t, "table": dp.get("table")}
        A.store(p["event_id"], p["mint"], res, quotes=quotes, price_at_discovery=res.get("price_now"), t=t)
        done += 1
        print(f"{ev['title'][:70]:70} {link.get('symbol') or p['mint'][:6]:>8} triage {res['triage_score']:>3} {res['verdict']:16} missing={len(res['missing'])} fatal={len(res['fatal'])}")
    # events without links still get an attention sample + EVENT_ONLY assessment so the record is complete
    with db.connect() as con:
        unl = [dict(r) for r in con.execute("SELECT * FROM catalyst_events WHERE status IN ('NEW','EVENT_ONLY') AND id NOT IN (SELECT event_id FROM catalyst_token_links)")]
    for ev in unl[: a.limit_unlinked]:
        att = attention.sample_event(ev["id"], t=t)
        res = A.assess(ev, None, att, None, t=t)
        A.store(ev["id"], None, res, t=t)
    print(f"assessed {done} event-token pairs and {min(len(unl), a.limit_unlinked)} unlinked events")


def cmd_monitor(a):
    out = MON.run()
    n = MON.record_outcomes()
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in out.items()}, indent=1), "outcomes recorded:", n)
    for k in ("contradictions", "deteriorations", "event_day", "new_catalysts"):
        for x in out[k]:
            print(f"- {k}: {x['text']}")


def cmd_report(a):
    md = R.render()
    t = time.time()
    p = db.DATA_DIR / "reports" / f"{time.strftime('%Y%m%d_%H%M', time.gmtime(t))}_CATALYST.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(md)
    print(md if a.print else md[:3000])
    print("\n->", p)


def cmd_note(a):
    I.note_event(a.event_id, a.text, kind=a.kind)
    print("recorded")


def cmd_sources(a):
    db.init_db()
    with db.connect() as con:
        sync_registry(con)
        for r in con.execute("SELECT source_id, source_group, access_mode, tier, enabled, identity_verified, last_ok_at, last_error, coverage_gap FROM catalyst_sources ORDER BY source_group, source_id"):
            print(f"{r['source_group']:9} {r['access_mode']:8} {r['tier'] or '':10} {'on ' if r['enabled'] else 'off'} {r['source_id']:34} {r['identity_verified'] or '':10} {('ok ' + time.strftime('%m-%d %H:%M', time.gmtime(r['last_ok_at']))) if r['last_ok_at'] else ''} {('ERR ' + r['last_error'][:40]) if r['last_error'] else ''} {('GAP: ' + r['coverage_gap'][:70]) if r['coverage_gap'] else ''}")


def add_subparser(sp):
    p = sp.add_parser("catalyst", help="Catalyst Intelligence: events -> tokens -> assessment -> monitoring")
    ssp = p.add_subparsers(dest="ccmd", required=True)
    q = ssp.add_parser("plan"); q.add_argument("--id"); q.add_argument("--verify-traders", action="store_true"); q.set_defaults(fn=cmd_plan)
    q = ssp.add_parser("save-page"); q.add_argument("id"); q.add_argument("--file", required=True); q.set_defaults(fn=cmd_save_page)
    q = ssp.add_parser("pull-pages", help="navigate-mode sources as direct API pulls (preferred over Chrome)"); q.add_argument("id"); q.set_defaults(fn=cmd_pull_pages)
    q = ssp.add_parser("ingest"); q.add_argument("--results", nargs="+", required=True); q.set_defaults(fn=cmd_ingest)
    q = ssp.add_parser("match-plan"); q.add_argument("--id"); q.add_argument("--limit", type=int, default=40); q.set_defaults(fn=cmd_match_plan)
    q = ssp.add_parser("match"); q.add_argument("--results", nargs="+", required=True); q.add_argument("--min-liq", type=float, default=5000); q.set_defaults(fn=cmd_match)
    q = ssp.add_parser("assess"); q.add_argument("--results", nargs="*", default=[]); q.add_argument("--persist", action="store_true"); q.add_argument("--limit-unlinked", type=int, default=60); q.set_defaults(fn=cmd_assess)
    q = ssp.add_parser("monitor"); q.set_defaults(fn=cmd_monitor)
    q = ssp.add_parser("report"); q.add_argument("--print", action="store_true"); q.set_defaults(fn=cmd_report)
    q = ssp.add_parser("note"); q.add_argument("event_id", type=int); q.add_argument("text"); q.add_argument("--kind", default="REVISED"); q.set_defaults(fn=cmd_note)
    q = ssp.add_parser("sources"); q.set_defaults(fn=cmd_sources)
