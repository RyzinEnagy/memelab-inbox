"""Report for "Find upcoming memecoins". Markdown, plain wording, at most five candidates, no BUY status anywhere."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .discover import STATES
from .sources import GAPS

SHOW = ("LAUNCH MONITOR", "HIGH-INTEREST WATCH", "WATCH")


def _ts(x):
    return datetime.fromtimestamp(x, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if x else "UNKNOWN"


def _usd(x):
    if x is None:
        return "UNKNOWN"
    return f"${x / 1e6:,.2f}M" if x >= 1e6 else f"${x / 1e3:,.1f}k" if x >= 1e3 else f"${x:,.0f}"


def _pct(x):
    return "UNKNOWN" if x is None else f"{x:.1f}%"


def _age(c, t):
    s = c.get("first_trade_at") or c.get("created_at")
    if not s:
        return "UNKNOWN"
    h = (t - s) / 3600
    return f"{h * 60:.0f} min" if h < 1 else f"{h:.1f} h"


def environment(con, t: float, disc: dict | None, pads: dict) -> list[str]:
    L = ["# PRE-LAUNCH MARKET ENVIRONMENT", ""]
    g = con.execute("SELECT regime, confidence, observed_at FROM regime_snapshots ORDER BY observed_at DESC LIMIT 1").fetchone()
    L.append(f"Market regime: {g['regime']} ({g['confidence']} confidence, read {_ts(g['observed_at'])})" if g else "Market regime: UNKNOWN (no ecosystem run stored)")
    rows = con.execute("SELECT chain_id, soi, trend FROM chain_scores c WHERE observed_at=(SELECT MAX(observed_at) FROM chain_scores WHERE chain_id=c.chain_id) ORDER BY soi DESC").fetchall()
    if rows:
        L.append("Chain SOI: " + ", ".join(f"{r['chain_id']} {r['soi']:.0f} ({r['trend'] or 'n/a'})" for r in rows if r["soi"] is not None))
    if disc:
        by = {}
        for c in disc["cands"].values():
            by[c["state"]] = by.get(c["state"], 0) + 1
        L.append("Launches seen this run: " + ", ".join(f"{STATES[k]} {v}" for k, v in sorted(by.items())))
    if pads:
        L.append("")
        L.append("Launchpad outcomes (newest-launch cohort, launches older than 24h):")
        for p, s in sorted(pads.items(), key=lambda x: -x[1]["n"]):
            L.append(f"- {p}: n={s['n']}, graduated {s['graduation_rate']:.1%}, reached $100k {s['reach_100k_rate']:.1%}, reached $1M {s['reach_1m_rate']:.1%}"
                     + (f", alive at 24h {s['survival_24h']:.0%}" if s.get("survival_24h") is not None else "")
                     + (f", quality score {s['quality_score']:.0f}" if s.get("quality_score") is not None else " (INSUFFICIENT HISTORY for a quality score)"))
    else:
        L.append("Launchpad outcomes: INSUFFICIENT HISTORY (the cohort needs launches older than 24 hours; it builds up with every run)")
    L.append("")
    return L


def candidate(r: dict, t: float, i: int) -> list[str]:
    c, tk, dep, hold, snip, clus, soc, comp, ct, res = (r[k] for k in ("c", "tk", "dep", "hold", "snip", "clus", "soc", "comp", "contract", "res"))
    o = c.get("obs") or {}
    ev = res["entry_view"]
    exp_launch = _ts(c.get("scheduled_at")) if c["state"] == "A" else (f"live for {_age(c, t)}" if c["state"] == "E" else f"on the curve ({_pct(o.get('curve_progress_pct'))} to graduation), created {_age(c, t)} ago")
    why = ", ".join(c.get("sources") or []) or "UNKNOWN"
    wallet = "; ".join((snip.get("facts") or []) + (clus.get("facts") or []) + [f"UNKNOWN: {u}" for u in (snip.get("unknowns") or []) + (clus.get("unknowns") or [])][:3]) or "UNKNOWN"
    comp_line = f"{comp.get('verdict')} (n={comp.get('n', 0)})" + (": " + "; ".join(comp.get("facts") or []) if comp.get("facts") else "")
    risks = (res.get("avoid") or []) + list(tk.get("flags") or []) + list(ct.get("warnings") or []) + [f for f in c.get("flags") or [] if not f.startswith("CONTRACT_NOT")]
    L = [f"## {i}. {c.get('symbol') or '?'} ({c.get('project') or '?'})", "",
         f"TOKEN: {c.get('symbol')} / {c.get('project')}",
         f"CHAIN: {c.get('chain') or 'UNKNOWN'}",
         f"EXPECTED LAUNCH: {exp_launch}",
         f"CONTRACT: {c.get('contract') or 'NOT YET PUBLISHED (CONTRACT NOT YET VERIFIED)'}" + (f" (source: {c.get('contract_source')})" if c.get("contract") else ""),
         f"IDENTITY STATE: {c['state']} {STATES[c['state']]}",
         f"LAUNCHPAD: {c.get('launchpad') or 'none / direct pool'}",
         f"WHY IT SURFACED: {why}",
         f"NARRATIVE: {res.get('narrative') or 'no tracked narrative matched'} ({res.get('narrative_lifecycle') or 'UNKNOWN'})",
         f"SOCIAL MOMENTUM: {soc['classification']}. " + "; ".join(soc["facts"][:4]) + ". X/Telegram/Discord not readable.",
         f"LAUNCH STRUCTURE: " + ("; ".join(tk["facts"][:2]) or "UNKNOWN") + (f". Contract: {'clean' if ct['clean'] else 'issues: ' + '; '.join(ct['fatal'] + ct['warnings']) if ct['clean'] is not None else 'UNKNOWN'}"),
         f"EXPECTED FLOAT: {_pct(tk.get('initial_float_pct'))} ({tk.get('basis')})",
         f"INSIDER ALLOCATION: {_pct(tk.get('initial_insider_pct'))} ({tk.get('insider_basis') or 'UNKNOWN'})" + (f"; creator holds {hold['dev_pct']:.2f}%" if hold.get("dev_pct") is not None else ""),
         f"LIQUIDITY PLAN: " + (f"observed {_usd(o.get('liquidity_usd'))}" if c["state"] == "E" and o.get("liquidity_usd") else f"PROJECTED {_usd(tk.get('expected_liquidity_usd'))} at migration" if tk.get("expected_liquidity_usd") else "UNKNOWN")
             + f"; LP control {ct.get('lp_control') or 'UNKNOWN'}",
         f"EXPECTED VALUATION: " + (f"now {_usd(o.get('mcap_usd'))}" if o.get("mcap_usd") else "") + (f"; PROJECTED {_usd(tk.get('expected_valuation_usd'))} at graduation/launch" if tk.get("expected_valuation_usd") else ""),
         f"DEPLOYER HISTORY: {dep['classification']}. " + "; ".join(dep.get("evidence") or [])[:300],
         f"PRE-LAUNCH WALLET ACTIVITY: {wallet}",
         f"COMPARABLE LAUNCHES: {comp_line}",
         f"PRIMARY RISKS: " + ("; ".join(risks[:6]) or "none identified beyond the base rate: most launches fail"),
         "WHAT MUST BE VERIFIED AT LAUNCH:"]
    L += [f"- {v}" for v in res["verify_at_launch"]]
    L += [f"PRE-LAUNCH SCORE: {res['score']:.0f}/100",
          f"DATA COMPLETENESS: {res['completeness']:.0f}/100",
          f"CONFIDENCE: {res['confidence']}",
          f"STATUS: {res['status']} ({res['status_reason']})",
          f"PROJECT: {ev['project']}. PRE-LAUNCH ENTRY: {ev['pre_launch_entry']}. POST-LAUNCH ENTRY: {ev['post_launch_entry']}."]
    if r.get("price_discovery"):
        pd = r["price_discovery"]
        L.append(f"PRICE DISCOVERY: {pd['pattern']}" + (f" (high {pd.get('minutes_to_high')} min after open, {pd.get('drawdown_from_high_pct')}% from high, last/open {pd.get('last_vs_open')}x)" if pd.get("open") else f" ({pd.get('why')})"))
    if r.get("conversion"):
        L.append("EXPECTED VS ACTUAL: " + r["conversion"]["interpretation"])
        L += [f"- {x}" for x in r["conversion"]["lines"]]
    if r.get("windows"):
        L.append("LAUNCH WINDOWS: " + "; ".join(f"{k} [{w['basis']}] " + ", ".join(f"{m}={_fmtv(v)}" for m, v in w["metrics"].items() if v is not None and m in ("close", "high", "volume_usd", "unique_buyers", "unique_sellers", "liquidity_usd", "mcap_usd", "holders"))
                                              for k, w in r["windows"].items()))
    L.append("")
    return L


def _fmtv(v):
    return f"{v:.3g}" if isinstance(v, float) else str(v)


def render(con, t: float, results: list[dict], disc: dict | None, pads: dict) -> str:
    L = [f"Pre-launch and new-launch scan, {_ts(t)}", "", "Statuses describe what deserves attention. None of them is a buy signal, and nothing here was traded.", ""]
    L += environment(con, t, disc, pads)
    best = [r for r in results if r["res"]["status"] in SHOW][:5]
    L += ["# BEST UPCOMING CANDIDATES", ""]
    if not best:
        L += ["No launch met the bar this run. That is a normal result: most launches are not worth attention, and finding nothing is not a failure.", ""]
    for i, r in enumerate(best, 1):
        L += candidate(r, t, i)
    rest = [r for r in results if r not in best]
    if rest:
        L += ["# OTHER LAUNCHES RESEARCHED", ""]
        for r in rest:
            c, res = r["c"], r["res"]
            L.append(f"- {c.get('symbol')} ({c.get('chain')}, {c.get('launchpad') or 'pool'}, state {c['state']}, {(c.get('contract') or '')[:12]}..): {res['status']}, score {res['score']:.0f}, completeness {res['completeness']:.0f}. {res['status_reason'][:200]}")
        L.append("")
    al = con.execute("SELECT * FROM launch_alerts WHERE alerted_at >= ? ORDER BY alerted_at DESC LIMIT 40", (t - 6 * 3600,)).fetchall()
    L += ["# ALERTS", ""]
    L += [f"- {a['kind']}: {a['text']}" for a in al] or ["- none"]
    L.append("")
    L += ["# UPCOMING_LAUNCHES", "", "| symbol | chain | state | phase | status | score | completeness | launchpad | contract |", "|---|---|---|---|---|---|---|---|---|"]
    for u in con.execute("SELECT * FROM upcoming_launches WHERE status IS NOT NULL AND phase IN ('PRE_LAUNCH','NEW_LAUNCH_MONITOR') ORDER BY prelaunch_score DESC LIMIT 25"):
        L.append(f"| {u['symbol']} | {u['chain']} | {u['state']} | {u['phase']} | {u['status']} | {u['prelaunch_score'] or 0:.0f} | {u['completeness'] or 0:.0f} | {u['launchpad'] or ''} | {(u['contract'] or 'NOT YET PUBLISHED')[:14]} |")
    L.append("")
    tr = con.execute("SELECT t.*, u.symbol FROM launch_transitions t JOIN upcoming_launches u USING(launch_id) WHERE t.at >= ? ORDER BY t.at DESC LIMIT 20", (t - 86400,)).fetchall()
    if tr:
        L += ["# HAND-OVERS", ""] + [f"- {x['symbol']}: {x['from_phase']} -> {x['to_phase']} ({x['reason']}). {x['interpretation'] or ''}" for x in tr] + [""]
    rj = con.execute("SELECT * FROM launch_rejections WHERE rejected_at >= ? ORDER BY rejected_at DESC LIMIT 15", (t - 86400,)).fetchall()
    L += ["# REJECTED PRE-LAUNCH RECORDS", ""]
    L += [f"- {x['symbol']} ({x['chain']}, {(x['contract'] or '')[:12]}..): " + "; ".join(json.loads(x["reasons_json"] or "[]"))[:240] for x in rj] or ["- none this run"]
    L += ["", "# DATA GAPS", ""] + [f"- {g}" for g in GAPS]
    L += ["- before trading there is no executable depth: planned liquidity and projected valuations are labeled PROJECTED until a pool is observed", ""]
    return "\n".join(L)
