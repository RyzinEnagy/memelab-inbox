"""memelab CLI.

Typical cycle (browser bridge):
  python -m memelab init
  python -m memelab plan discovery                      -> prints JS to run in the browser tab
  (run JS, read page text, save to data/inbox/<plan>.result.json via `python -m memelab save <plan_id> < pagetext.txt`)
  python -m memelab discover <plan_id>                  -> stage-1 survivors, writes stage1.json
  python -m memelab plan structural <plan_id>           -> JS for stage-2 fetch of survivors
  python -m memelab stage2 <structural_plan_id>         -> structural filter, picks deep candidates
  python -m memelab plan deep <mint> [--sizes ...]      -> JS for deep fetch
  python -m memelab analyze <mint> --results <result ids...>   -> full report
  python -m memelab scout --results ...                 -> opportunity report across analyzed tokens
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import db
from .db import DATA_DIR
from .bridge.plan import Plan, DEFAULT_SIZES
from .bridge import ingest
from .modules import m01_token_discovery as m01
from .normalize import build_bundle
from . import pipeline, report

INBOX = db.DATA_DIR / "inbox"


def _result(pid: str) -> ingest.Result:
    p = INBOX / f"{pid}.result.json"
    if not p.exists():
        sys.exit(f"missing {p}")
    return ingest.load_result(p)


def _bodies(ids: list[str]) -> tuple[dict, float]:
    res = [_result(i) for i in ids]
    merged = ingest.merged_bodies(res)
    bodies = {k: v[0] for k, v in merged.items()}
    t = max((r.observed_at for r in res), default=time.time())
    return bodies, t


def _sol_price(bodies: dict) -> float | None:
    cg = bodies.get("raw:cg_sol")
    if isinstance(cg, dict) and cg.get("solana"):
        return cg["solana"].get("usd")
    jt = bodies.get("jup_tok:So11111111111111111111111111111111111111112")
    if isinstance(jt, list) and jt:
        return jt[0].get("usdPrice")
    return None


def _benchmarks(bodies: dict, stage1: list[dict] | None) -> dict:
    cg = bodies.get("raw:cg_sol") or {}
    bm = {}
    for k, name in (("solana", "SOL"), ("bitcoin", "BTC")):
        if isinstance(cg.get(k), dict):
            bm[name] = {"chg_24h": cg[k].get("usd_24h_change"), "chg_1h": None, "chg_6h": None}
    peers = []
    for c in stage1 or []:
        s = c.get("signals") or {}
        peers.append({"symbol": c.get("symbol"), "mint": c.get("mint"), "chg_1h": s.get("j_chg_1h"), "chg_6h": s.get("j_chg_6h"), "chg_24h": s.get("j_chg_24h") or (s.get("chg") or {}).get("h24"),
                      "vol_24h": s.get("j_vol_24h") or s.get("vol_24h"), "vol_6h": s.get("j_vol_6h") or s.get("vol_6h")})
    bm["peers"] = peers
    return bm


def cmd_init(a):
    db.init_db(); print(f"db ready at {db.DB_PATH}")


def cmd_plan(a):
    pl = Plan(a.id)
    if a.kind == "discovery":
        pl.discovery(gt_pages=a.pages)
    elif a.kind == "structural":
        s1 = json.loads((INBOX / f"{a.source}.stage1.json").read_text())
        mints = [c["mint"] for c in s1["survivors"]][: a.limit]
        pl.structural(mints)
    elif a.kind == "deep":
        bodies, _ = _bodies(a.results)
        sol = _sol_price(bodies)
        for mint in ([a.mint] if a.mint else []) + list(a.mints or []):
            b = build_bundle(mint, bodies, sol_price=sol)
            pools = sorted([p for p in b["pools"] if p.get("pool")], key=lambda p: p.get("reserve_usd") or 0, reverse=True)
            pool_ids = [p["pool"] for p in pools]
            dec = b["identity"].get("decimals") or 6
            price = b["market"].get("price_usd")
            if not price or not sol:
                sys.exit(f"{mint}: need price (got {price}) and SOL price (got {sol}) from structural results before planning deep fetch")
            sizes = a.sizes or DEFAULT_SIZES
            liq = b["market"].get("liquidity_usd_total") or 0
            if liq and liq < 100_000:
                sizes = [s for s in sizes if s <= 25_000]
            elif liq and liq < 400_000:
                sizes = [s for s in sizes if s <= 50_000]
            pl.deep(mint, pool_ids, sizes=sizes, sol_price=sol, decimals=dec, price_usd=price)
    elif a.kind == "wallets":
        pl.wallet_sigs(a.wallets, limit=a.limit)
    path = pl.save()
    print(f"# plan {pl.id}: {len(pl.reqs)} requests -> {path}\n")
    print(pl.js_call())


def cmd_save(a):
    text = sys.stdin.read() if a.file is None else Path(a.file).read_text()
    p = ingest.save_result(text, a.id)
    r = ingest.load_result(p); r.log()
    fails = r.failures()
    print(f"saved {p} ({len(list(r.items()))} keys, {len(fails)} failed)")
    for k, v in list(fails.items())[:10]:
        print("  FAIL", k, v)


def cmd_discover(a):
    bodies, t = _bodies([a.id])
    with db.connect() as con:
        rej = {r["mint"]: r for r in con.execute("SELECT mint, why_failed, rejected_at, reconsider_if FROM rejections")}
    out = m01.discover(bodies, min_liquidity=a.min_liq, min_vol_24h=a.min_vol, max_candidates=a.limit)
    skipped = []
    for c in list(out["survivors"]):
        if c["mint"] in rej and (t - rej[c["mint"]]["rejected_at"]) < a.rejection_ttl_hours * 3600:
            skipped.append({"mint": c["mint"], "symbol": c["symbol"], "why": rej[c["mint"]]["why_failed"], "reconsider_if": rej[c["mint"]]["reconsider_if"]})
            out["survivors"].remove(c)
    out["previously_rejected"] = skipped
    out["sol_price"] = _sol_price(bodies); out["observed_at"] = t
    (INBOX / f"{a.id}.stage1.json").write_text(json.dumps(out, indent=1, default=list))
    print(f"universe {out['universe_size']}, stage-1 survivors {len(out['survivors'])}, stage-1 rejects {len(out['rejected_stage1'])}, previously rejected skipped {len(skipped)}")
    for c in out["survivors"][: a.show]:
        print(f"  {c['pre_score']:5.1f}  {str(c['symbol']):>12}  {c['mint']}  liq ${c['liquidity_est']:,.0f}  vol24 ${c['vol_24h_est']:,.0f}  | {'; '.join(c['why'][:3])}")


def cmd_stage2(a):
    """Structural filter over stage-1 survivors using ds/jup_tok/rug bodies; emits deep candidates and stage-2 rejections."""
    bodies, t = _bodies(a.results)
    s1 = json.loads((INBOX / f"{a.source}.stage1.json").read_text())
    sol = s1.get("sol_price") or _sol_price(bodies)
    keep, reject, deferred = [], [], []
    # browser-side stage-2 verdicts (stage2.js) travel with the result file
    browser_rej, browser_pass = {}, set()
    for rid in a.results:
        raw = json.loads((INBOX / f"{rid}.result.json").read_text())
        for m_, sym_, why_ in raw.get("stage2_rejected") or []:
            browser_rej[m_] = why_
        browser_pass |= set(raw.get("stage2_pass") or [])
    from .modules import m02_identity_verification as m02, m07_lp_analysis as m07, m08_token_mechanics as m08, m09_holder_classification as m09
    for c in s1["survivors"]:
        mint = c["mint"]
        b = build_bundle(mint, bodies, observed_at=t, sol_price=sol)
        if not any(k.endswith(mint) for k in bodies if k.startswith(("jup_tok", "rug"))) and not b["pools"]:
            if mint in browser_rej:
                reject.append({"mint": mint, "symbol": c["symbol"], "why": browser_rej[mint], "stage": "structural (browser filter)", "why_surfaced": c["why"]})
            elif mint in browser_pass:
                deferred.append({"mint": mint, "symbol": c["symbol"], "why": "passed structural filter but beyond the deep-candidate cap this run", "pre_score": c["pre_score"]})
            else:
                reject.append({"mint": mint, "symbol": c["symbol"], "why": "no structural data returned", "stage": "structural", "why_surfaced": c["why"]})
            continue
        idm, mech, lp, hold = m02.analyze(b), m08.analyze(b), m07.analyze(b), m09.analyze(b)
        why = []
        if idm["status"] != "OK": why.append("identity not verified")
        if mech["flags"]: why.append("mechanics: " + ", ".join(mech["flags"]))
        if lp["lp_risk"] == "CRITICAL": why.append("LP risk CRITICAL: " + lp["reason"])
        if (hold.get("largest_unexplained_pct") or 0) > a.max_single_holder: why.append(f"largest unexplained holder {hold['largest_unexplained_pct']:.1f}%")
        if (hold.get("adjusted_top10_pct") or 0) > a.max_top10: why.append(f"adjusted top-10 {hold['adjusted_top10_pct']:.1f}%")
        liq = b["market"].get("liquidity_usd_total") or 0
        if liq < a.min_liq: why.append(f"liquidity ${liq:,.0f} below ${a.min_liq:,.0f}")
        if (b["market"].get("age_hours") or 1e9) < a.min_age_hours: why.append(f"age {b['market'].get('age_hours', 0):.0f}h below {a.min_age_hours}h")
        row = {"mint": mint, "symbol": b["identity"].get("symbol") or c["symbol"], "pre_score": c["pre_score"], "liq": liq, "mcap": b["market"].get("market_cap"),
               "adj_top10": hold.get("adjusted_top10_pct"), "lp_risk": lp["lp_risk"], "flags": mech["flags"], "why_surfaced": c["why"], "signals": c.get("signals")}
        if why:
            row["why"] = "; ".join(why); row["stage"] = "structural"; reject.append(row)
        else:
            keep.append(row)
    with db.connect() as con:
        for r in reject:
            db.insert(con, "rejections", {"mint": r["mint"], "symbol": r.get("symbol"), "rejected_at": t, "stage": "structural", "why_surfaced": "; ".join(r.get("why_surfaced") or [])[:500],
                      "why_failed": r["why"], "evidence": json.dumps({k: r.get(k) for k in ("liq", "adj_top10", "lp_risk", "flags")}), "reconsider_if": "structural condition changes (authority revoked, LP locked, concentration absorbed, liquidity grows)"})
    keep.sort(key=lambda r: r["pre_score"], reverse=True)
    out = {"deep_candidates": keep[: a.limit], "rejected_stage2": reject, "deferred": deferred, "observed_at": t, "sol_price": sol, "stage1_source": a.source}
    (INBOX / f"{a.source}.stage2.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"stage-2: {len(keep)} pass, {len(reject)} rejected, {len(deferred)} deferred")
    for d in deferred:
        print(f"  DEFER  {str(d['symbol']):>12} {d['mint'][:8]}.. {d['why']}")
    for r in keep[: a.limit]:
        print(f"  {r['pre_score']:5.1f} {str(r['symbol']):>12} {r['mint']} liq ${r['liq']:,.0f} mcap ${(r['mcap'] or 0):,.0f} top10adj {r['adj_top10']} lp {r['lp_risk']}")
    for r in reject[:15]:
        print(f"  REJECT {str(r.get('symbol')):>12} {r['mint'][:8]}.. {r['why']}")


def cmd_analyze(a):
    bodies, t = _bodies(a.results)
    s1 = None
    if a.stage1:
        s1 = json.loads((INBOX / f"{a.stage1}.stage1.json").read_text())
    sol = (s1 or {}).get("sol_price") or _sol_price(bodies)
    disc = None
    if s1:
        disc = next((c for c in s1["survivors"] if c["mint"] == a.mint), None)
    account = {k: getattr(a, k) for k in ("account_size", "max_loss_usd", "max_loss_pct", "position_usd") if getattr(a, k) is not None}
    r = pipeline.analyze_token(a.mint, bodies, observed_at=t, sol_price=sol, benchmarks=_benchmarks(bodies, (s1 or {}).get("survivors")), account=account,
                               discovery_signals=disc, persist=not a.no_persist)
    print(f"{r['bundle']['identity'].get('symbol')} score {r['score']['total']} status {r['status']['status']} -> {r.get('report_path')}")
    if a.print:
        print(r["report_md"])


def cmd_scout(a):
    bodies, t = _bodies(a.results)
    s1 = json.loads((INBOX / f"{a.stage1}.stage1.json").read_text()) if a.stage1 else {}
    s2 = json.loads((INBOX / f"{a.stage1}.stage2.json").read_text()) if a.stage1 and (INBOX / f"{a.stage1}.stage2.json").exists() else {}
    sol = s1.get("sol_price") or _sol_price(bodies)
    bm = _benchmarks(bodies, s1.get("survivors"))
    results = []
    for mint in a.mints:
        disc = next((c for c in s1.get("survivors", []) if c["mint"] == mint), None)
        r = pipeline.analyze_token(mint, bodies, observed_at=t, sol_price=sol, benchmarks=bm, discovery_signals=disc, persist=True)
        results.append(r)
    from .modules import m24_opportunity_ranker as m24
    ranked = m24.rank([{"symbol": r["bundle"]["identity"].get("symbol"), "mint": r["mint"], "score_result": r["score"], "modules": r["ranker_inputs"], "status": r["status"]} for r in results])
    serious = [r for r in results if not r["score"]["untradeable"] and r["status"]["status"] in ("WATCH", "SETUP DEVELOPING", "NEAR ENTRY", "ENTRY CONDITIONS MET") and (r["score"]["total"] or 0) >= a.min_score]
    serious.sort(key=lambda r: r["score"]["total"], reverse=True)
    serious = serious[:5]
    near = [{"symbol": r["bundle"]["identity"].get("symbol"), "mint": r["mint"], "score": r["score"]["total"], "status": r["status"]["status"], "why": r["status"].get("reasoning")} for r in results if r not in serious and not r["score"]["untradeable"] and r["status"]["status"] not in ("REJECTED",)]
    rejected = [{"symbol": r["bundle"]["identity"].get("symbol"), "mint": r["mint"], "why": r["status"].get("reasoning") + ("; fatal: " + ", ".join(f["flag"] for f in r["score"]["fatal_flags"]) if r["score"].get("fatal_flags") else "")} for r in results if r["score"]["untradeable"] or r["status"]["status"] == "REJECTED"]
    for x in s2.get("rejected_stage2", []):
        rejected.append({"symbol": x.get("symbol"), "mint": x["mint"], "why": "stage-2 structural: " + x.get("why", "")})
    cg = bodies.get("raw:cg_sol") or {}
    env = {"SOL": f"${sol:,.2f}" + (f" ({cg['solana'].get('usd_24h_change', 0):+.1f}% 24h)" if cg.get("solana") else ""),
           "BTC": f"${cg['bitcoin'].get('usd'):,.0f} ({cg['bitcoin'].get('usd_24h_change', 0):+.1f}% 24h)" if cg.get("bitcoin") else "n/a",
           "Discovery universe": f"{s1.get('universe_size', 'n/a')} mints, {len(s1.get('survivors', []))} stage-1 survivors, {len(s2.get('deep_candidates', []))} deep candidates",
           "Peer median 24h change": _median([p.get("chg_24h") for p in bm.get("peers", []) if p.get("chg_24h") is not None]),
           "Best token vs best trade": ranked.get("best_token_vs_best_trade")}
    md = report.render_scout_report(env, serious, near, rejected, when=t)
    path = db.DATA_DIR / "reports" / f"{time.strftime('%Y%m%d_%H%M', time.gmtime(t))}_SCOUT.md"
    path.write_text(md)
    print(md)
    print(f"\n-> {path}")


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return "n/a"
    m = xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2
    return f"{m:+.1f}% (n={len(xs)})"


def cmd_watchlist(a):
    with db.connect() as con:
        rows = con.execute("SELECT w.mint, t.symbol, w.status, w.last_status_change, (SELECT score FROM theses th WHERE th.mint=w.mint ORDER BY created_at DESC LIMIT 1) score FROM watchlist w JOIN tokens t ON t.mint=w.mint ORDER BY score DESC").fetchall()
    for r in rows:
        print(f"{str(r['symbol']):>12} {r['mint']} {r['status']:<22} score {r['score']} as of {time.strftime('%Y-%m-%d %H:%M', time.gmtime(r['last_status_change']))}")
    if not rows:
        print("watchlist empty")


def cmd_rejections(a):
    with db.connect() as con:
        rows = con.execute("SELECT * FROM rejections ORDER BY rejected_at DESC LIMIT ?", (a.limit,)).fetchall()
    for r in rows:
        print(f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(r['rejected_at']))} {str(r['symbol']):>12} {r['mint']} [{r['stage']}] {r['why_failed']} || reconsider if: {r['reconsider_if']}")


def cmd_social_note(a):
    with db.connect() as con:
        db.upsert_token(con, a.mint)
        db.insert(con, "social_snapshots", {"mint": a.mint, "observed_at": time.time(), "source": a.source, "metric": a.metric, "value": a.value, "text_value": a.text, "notes": a.note})
    print("recorded")


def cmd_wallet(a):
    """Read-only wallet tracking. plan: print the browser call; report: analyze pulled results."""
    from . import wallet as W
    from .modules import m26_portfolio_risk as m26
    addrs = a.addresses or [w["address"] for w in W.tracked_wallets()]
    if not addrs:
        print("no addresses: pass them or add tracked_wallets to data/config.json"); return
    if a.action == "plan":
        plan = W.wallet_plan(a.id or f"wallet_{int(time.time())}", addrs, tx_limit=a.tx_limit)
        if hasattr(plan, "save"):
            print(f"# plan {plan.id} -> {plan.save()}  (fetch it with: python -m memelab fetch {plan.id})")
        print(plan.js_call() if hasattr(plan, "js_call") else json.dumps(plan.to_dict()))
        return
    res = [ingest.load_result(DATA_DIR / "inbox" / f"{i}.result.json") for i in a.results]
    bodies = {k: v[0] for k, v in ingest.merged_bodies(res).items()}
    sol = _sol_price(bodies) if "_sol_price" in globals() else None
    for addr in addrs:
        w = W.positions_from_wallet(addr, bodies, sol_price=sol)
        print(f"\n# Wallet {addr} (read-only)")
        for f in w["facts"]: print("- FACT:", f)
        for f in w["inferences"]: print("- INFERENCE:", f)
        for f in w["unknowns"]: print("- UNKNOWN:", f)
        if w["positions"]:
            pr = m26.analyze(w["positions"], {}, account_size=a.account_size)
            print("\nPortfolio risk:")
            for f in pr.get("facts", []): print("- FACT:", f)
            for f in pr.get("inferences", []): print("- INFERENCE:", f)
            for f in pr.get("unknowns", []): print("- UNKNOWN:", f)
        else:
            print("- no open token positions; portfolio and post-trade review modules have nothing to evaluate yet")


def cmd_fetch(a):
    """Run saved plan(s), or an in-browser JS step, directly from this machine via API pulls (Node + the same collector the
    browser uses). This is the default collection path; the Chrome bridge is the fallback for requests that fail here."""
    import os, shutil, subprocess, tempfile
    reqs, ids = [], []
    for pid in a.plans:
        pp = Path(pid) if pid.endswith(".json") else INBOX / f"{pid}.plan.json"
        if not pp.exists():
            print(f"skip {pid}: no plan file (empty group)"); continue
        d = json.loads(pp.read_text()); reqs += d["reqs"]; ids.append(d["id"])
    rid = a.as_id or (ids[0] if ids else None)
    if not rid:
        raise SystemExit("give --as <result id> when no plan file is used")
    node = shutil.which("node")
    if not node:
        raise SystemExit("node not found: install Node 18+, or fall back to the Chrome bridge")
    args = [node, str(Path(__file__).parent / "bridge" / "run_plan.js")]
    if reqs:
        tmp = Path(tempfile.mkdtemp()) / "plan.json"
        tmp.write_text(json.dumps({"id": rid, "reqs": reqs, **({"dedupe": True} if a.dedupe else {})}))
        args.append(str(tmp))
    else:
        args.append("-")
    out = INBOX / f"{rid}.result.json"
    args += [str(out), "--conc", str(a.concurrency)]
    if a.pre:
        args += ["--pre", str(INBOX / f"{a.pre}.result.json") if not a.pre.endswith(".json") else a.pre]
    if a.js:
        args += ["--js", a.js]
    env = dict(os.environ)
    if env.get("HTTPS_PROXY") or env.get("https_proxy"):
        env.setdefault("NODE_USE_ENV_PROXY", "1")   # Node's fetch ignores proxy variables unless told to use them
        env.setdefault("NODE_NO_WARNINGS", "1")
    r = subprocess.run(args, env=env)
    if r.returncode:
        raise SystemExit(r.returncode)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="memelab")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("init").set_defaults(fn=cmd_init)
    p = sp.add_parser("plan"); p.add_argument("kind", choices=["discovery", "structural", "deep", "wallets"]); p.add_argument("--id"); p.add_argument("--pages", type=int, default=3)
    p.add_argument("--source"); p.add_argument("--limit", type=int, default=40); p.add_argument("--mint"); p.add_argument("--mints", nargs="*"); p.add_argument("--results", nargs="*", default=[]); p.add_argument("--sizes", nargs="*", type=float); p.add_argument("--wallets", nargs="*", default=[])
    p.set_defaults(fn=cmd_plan)
    p = sp.add_parser("fetch", help="run saved plan(s) directly via API pulls (preferred over Chrome)"); p.add_argument("plans", nargs="*"); p.add_argument("--as", dest="as_id"); p.add_argument("--concurrency", type=int, default=6); p.add_argument("--dedupe", action="store_true"); p.add_argument("--pre", help="previous result id to preload (what the browser tab would show)"); p.add_argument("--js", help="in-browser step to run, e.g. 'await __ML.screen({minLiq:20000,minVol:50000})'"); p.set_defaults(fn=cmd_fetch)
    p = sp.add_parser("save"); p.add_argument("id"); p.add_argument("--file"); p.set_defaults(fn=cmd_save)
    p = sp.add_parser("discover"); p.add_argument("id"); p.add_argument("--min-liq", type=float, default=20_000); p.add_argument("--min-vol", type=float, default=50_000); p.add_argument("--limit", type=int, default=60); p.add_argument("--show", type=int, default=40); p.add_argument("--rejection-ttl-hours", type=float, default=72); p.set_defaults(fn=cmd_discover)
    p = sp.add_parser("stage2"); p.add_argument("source"); p.add_argument("--results", nargs="+", required=True); p.add_argument("--limit", type=int, default=8); p.add_argument("--max-single-holder", type=float, default=15); p.add_argument("--max-top10", type=float, default=50); p.add_argument("--min-liq", type=float, default=30_000); p.add_argument("--min-age-hours", type=float, default=6); p.set_defaults(fn=cmd_stage2)
    p = sp.add_parser("analyze"); p.add_argument("mint"); p.add_argument("--results", nargs="+", required=True); p.add_argument("--stage1"); p.add_argument("--account-size", type=float); p.add_argument("--max-loss-usd", type=float); p.add_argument("--max-loss-pct", type=float); p.add_argument("--position-usd", type=float); p.add_argument("--no-persist", action="store_true"); p.add_argument("--print", action="store_true"); p.set_defaults(fn=cmd_analyze)
    p = sp.add_parser("scout"); p.add_argument("--mints", nargs="+", required=True); p.add_argument("--results", nargs="+", required=True); p.add_argument("--stage1"); p.add_argument("--min-score", type=int, default=55); p.set_defaults(fn=cmd_scout)
    p = sp.add_parser("wallet"); p.add_argument("action", choices=["plan", "report"]); p.add_argument("--addresses", nargs="*"); p.add_argument("--id"); p.add_argument("--results", nargs="*", default=[]); p.add_argument("--tx-limit", type=int, default=100); p.add_argument("--account-size", type=float); p.set_defaults(fn=cmd_wallet)
    from .catalyst.cli import add_subparser as _cat; _cat(sp)
    from .chains.cli import add_subparser as _chains; _chains(sp)
    from .launch.cli import add_subparser as _launch; _launch(sp)
    from .social.cli import add_subparser as _social; _social(sp)
    sp.add_parser("watchlist").set_defaults(fn=cmd_watchlist)
    p = sp.add_parser("rejections"); p.add_argument("--limit", type=int, default=50); p.set_defaults(fn=cmd_rejections)
    p = sp.add_parser("social-note"); p.add_argument("mint"); p.add_argument("metric"); p.add_argument("--value", type=float); p.add_argument("--text"); p.add_argument("--source", default="browser"); p.add_argument("--note"); p.set_defaults(fn=cmd_social_note)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
