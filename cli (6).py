"""`python -m memelab chains ...` : ecosystem layers and chain-aware token research.

  plan eco [--id]                       ecosystem inputs (regime, rotation, narratives, launchpads, emerging)
  plan disc <chain> [--id]              EVM discovery universe for a chain
  plan struct <chain> <stage1-id>       EVM stage-2 (DEX Screener + GoPlus + honeypot.is) for stage-1 survivors
  plan deep <chain> <stage2-id>         EVM deep plans for stage-2 candidates (one plan file per token, plus a merged one)
  eco --results <ids>                   compute regime / SOI / narratives / launchpads / emerging, write ECOSYSTEM report
  discover <chain> <id> --results <ids> EVM stage 1 -> <id>.stage1.json
  struct <chain> <stage1-id> --results  EVM stage 2 -> <stage1-id>.stage2.json
  analyze <chain> <addr> --results      full pipeline for one token on any registered chain
  scout --tokens chain:addr ... --results <ids> [--eco <ids>]   cross-chain ranked report
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import db, pipeline
from ..bridge import ingest as bingest
from ..db import DATA_DIR
from . import emerging as E, narrative as NR, plan as P, regime as RG, registry as R, report as RP, rotation as RO

INBOX = DATA_DIR / "inbox"
REPORTS = DATA_DIR / "reports"


_KEY_TIMES: dict[str, float] = {}


def _merged(ids: list[str]) -> tuple[dict, float]:
    res = [bingest.load_result(INBOX / f"{i}.result.json") for i in ids if (INBOX / f"{i}.result.json").exists()]
    missing = [i for i in ids if not (INBOX / f"{i}.result.json").exists()]
    if missing:
        print(f"warning: results missing locally: {', '.join(missing)}")
    for r in res:  # remember when each key was collected so a token's snapshot carries its own data time, not the newest file's
        for k, _ in r.items():
            _KEY_TIMES[k] = max(_KEY_TIMES.get(k, 0), r.observed_at)
    return {k: v[0] for k, v in bingest.merged_bodies(res).items()}, max((r.observed_at for r in res), default=time.time())


def _token_time(mint: str, default: float) -> float:
    ts = [t for k, t in _KEY_TIMES.items() if k.endswith(f":{mint}") and k.split(":")[0] in ("gt_info", "jq", "kq", "goplus", "jup_tok", "rug", "hp")]
    return max(ts) if ts else default


def _native_price(bodies: dict, chain: str) -> float | None:
    cfg = R.CHAINS[chain]
    cg = bodies.get("cg_price") or bodies.get("raw:cg_sol") or {}
    if isinstance(cg, dict) and isinstance(cg.get(cfg["cg_native"]), dict):
        return cg[cfg["cg_native"]].get("usd")
    return None


def _hours_ago(iso, t):
    try:
        return (t - datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()) / 3600
    except Exception:
        return None


# ---------------- plans ----------------
def cmd_plan(a):
    if a.kind == "eco":
        plan = P.ecosystem(a.id or f"eco_{int(time.time())}")
    elif a.kind == "disc":
        plan = P.evm_discovery(a.chain, a.id or f"disc_{a.chain}_{int(time.time())}")
    elif a.kind == "struct":
        s1 = json.loads((INBOX / f"{a.target}.stage1.json").read_text())
        plan = P.evm_structural(a.chain, [c["mint"] for c in s1["survivors"]], a.id or f"{a.target}_s2")
    elif a.kind == "deep":
        s2 = json.loads((INBOX / f"{a.target}.stage2.json").read_text())
        merged = P.Plan(a.id or f"{a.target}_deep")
        for c in s2["deep_candidates"]:
            one = P.evm_deep(a.chain, c["mint"], [c["pool"]] if c.get("pool") else [], c.get("decimals") or 18, c.get("price"), s2.get("native_price"), c.get("liq"))
            merged.reqs += one.reqs
        plan = merged
    else:
        raise SystemExit("unknown plan kind")
    path = plan.save()
    print(f"{plan.id}: {len(plan.reqs)} requests -> {path}")
    if a.js:
        print(plan.js_call())


# ---------------- ecosystem ----------------
def run_ecosystem(bodies: dict, t: float, persist: bool = True) -> dict[str, Any]:
    reg = RG.compute(bodies, t, persist=persist)
    rot = RO.compute(bodies, t, persist=persist)
    nar = NR.compute(bodies, t, persist=persist)
    em = E.detect(bodies, t, persist=persist)
    lp = E.launchpads(bodies, t, persist=persist)
    bk = E.benchmark_baskets(bodies, t, persist=persist)
    md = RP.render(reg, rot, nar, em, lp, bk, when=t)
    return {"regime": reg, "rotation": rot, "narratives": nar, "emerging": em, "launchpads": lp, "baskets": bk, "md": md}


def cmd_eco(a):
    db.init_db()
    bodies, t = _merged(a.results)
    out = run_ecosystem(bodies, t, persist=not a.no_persist)
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"{time.strftime('%Y%m%d_%H%M', time.gmtime(t))}_ECOSYSTEM.md"
    path.write_text(out["md"])
    print(out["md"] if a.print else f"regime {out['regime']['regime']} ({out['regime']['confidence']}); SOI " + ", ".join(f"{c} {out['rotation']['chains'][c]['soi']}" for c in out["rotation"]["ranked"]))
    print(f"-> {path}")


# ---------------- EVM stage 1 ----------------
def cmd_discover(a):
    db.init_db()
    bodies, t = _merged(a.results)
    cfg = R.get(a.chain); net = cfg["gt_network"]
    pools: dict[str, dict] = {}
    for k, v in bodies.items():
        if k.startswith(f"gt_pools:{net}:") and isinstance(v, dict):
            kind = k.split(":")[2]
            for p in v.get("pools") or []:
                if not p.get("base") or not RO._is_meme_pool(p):
                    continue
                base = R.norm_address(a.chain, p["base"])
                row = pools.setdefault(base, {"mint": base, "symbol": (p.get("name") or "").split("/")[0].strip(), "pools": [], "sources": set(), "signals": {}})
                row["pools"].append(p); row["sources"].add(kind)
    boosts = {R.norm_address(a.chain, b.get("tokenAddress") or ""): b for k, v in bodies.items() if k.startswith("ds_boosts") and isinstance(v, list) for b in v if b.get("chainId") == cfg["ds_chain"]}
    profiles = {R.norm_address(a.chain, b.get("tokenAddress") or ""): b for b in (bodies.get("ds_profiles:latest") or []) if isinstance(b, dict) and b.get("chainId") == cfg["ds_chain"]}
    with db.connect() as con:
        rejected_recent = {r["mint"] for r in con.execute("SELECT mint FROM rejections WHERE rejected_at > ?", (t - a.rejection_ttl_hours * 3600,))}
    survivors, dropped = [], []
    for mint, row in pools.items():
        main = max(row["pools"], key=lambda p: p.get("reserve") or 0)
        liq = sum(p.get("reserve") or 0 for p in {p["pool"]: p for p in row["pools"]}.values())
        vol = sum((p.get("vol") or {}).get("h24") or 0 for p in {p["pool"]: p for p in row["pools"]}.values())
        tx = (main.get("tx") or {}).get("h24") or [None, None, None, None]
        age = _hours_ago(main.get("created"), t)
        sig = {"liq": liq, "vol_24h": vol, "buyers_24h": tx[2], "sellers_24h": tx[3], "chg": main.get("chg"), "fdv": main.get("fdv"), "age_hours": age, "sources": sorted(row["sources"]),
               "boosted": mint in boosts, "profile": mint in profiles, "dex": main.get("dex")}
        why = []
        if liq < a.min_liq: why.append(f"liquidity ${liq:,.0f} < ${a.min_liq:,.0f}")
        if vol < a.min_vol: why.append(f"24h volume ${vol:,.0f} < ${a.min_vol:,.0f}")
        if age is not None and age < a.min_age_hours: why.append(f"pool age {age:.1f}h < {a.min_age_hours}h")
        if (tx[2] or 0) < a.min_buyers: why.append(f"{tx[2]} unique buyers 24h < {a.min_buyers}")
        if liq and vol / liq > 25: why.append(f"volume/liquidity {vol / liq:.0f}x (wash-trade shape)")
        if mint in rejected_recent: why.append("rejected within TTL")
        rec = {"mint": mint, "symbol": row["symbol"], "pool": main.get("pool"), "price": main.get("price"), "liq": liq, "vol_24h": vol, "fdv": main.get("fdv"), "signals": sig, "chain": a.chain}
        (dropped if why else survivors).append({**rec, "why": "; ".join(why)} if why else rec)
    survivors.sort(key=lambda c: -(c["vol_24h"] or 0))
    survivors = survivors[:a.limit]
    out = {"id": a.id, "chain": a.chain, "observed_at": t, "native_price": _native_price(bodies, a.chain), "universe_size": len(pools), "survivors": survivors, "dropped": dropped[:200]}
    INBOX.mkdir(parents=True, exist_ok=True)
    (INBOX / f"{a.id}.stage1.json").write_text(json.dumps(out, indent=1, default=list))
    print(f"{a.chain}: universe {len(pools)} meme pools -> {len(survivors)} survivors ({len(dropped)} dropped)")
    for c in survivors[:a.show]:
        s = c["signals"]
        print(f"  {c['symbol']:<12} {c['mint']}  liq ${c['liq']:>11,.0f}  vol24 ${c['vol_24h']:>12,.0f}  buyers {s['buyers_24h']}  age {s['age_hours'] and round(s['age_hours'] / 24, 1)}d  {s['dex']}")


# ---------------- EVM stage 2 ----------------
def cmd_struct(a):
    from . import evm as EV
    bodies, t = _merged(a.results)
    s1 = json.loads((INBOX / f"{a.stage1}.stage1.json").read_text())
    chain = s1["chain"]
    deep, rejected = [], []
    with db.connect() as con:
        for c in s1["survivors"]:
            mint = c["mint"]
            b = EV.build_bundle(chain, mint, bodies, observed_at=t, native_price=s1.get("native_price"))
            mech = EV.mechanics(b)
            why = []
            fatal = {"HONEYPOT", "CANNOT_BUY", "EXTREME_TAX", "HIDDEN_OWNER", "SIMULATION_FAILED", "AIRDROP_SCAM", "CREATOR_PRIOR_HONEYPOT"}
            hit = fatal & set(mech.get("flags") or [])
            if hit: why.append("contract: " + ", ".join(sorted(hit)))
            if mech.get("owner_state") == "ACTIVE" and ({"TAX_MODIFIABLE", "UPGRADEABLE_PROXY", "MINT_FUNCTION", "TRANSFER_PAUSABLE", "BLACKLIST"} & set(mech.get("flags") or [])):
                why.append("live owner with " + ", ".join(sorted({"TAX_MODIFIABLE", "UPGRADEABLE_PROXY", "MINT_FUNCTION", "TRANSFER_PAUSABLE", "BLACKLIST"} & set(mech["flags"]))))
            top = [h for h in (b["holders"].get("top") or []) if not h.get("is_pool") and not h.get("is_locked") and (h.get("account") or "") not in EV.DEAD]
            if top and (top[0].get("pct") or 0) > a.max_single_holder: why.append(f"largest non-pool holder {top[0]['pct']:.1f}% > {a.max_single_holder}%")
            t10 = sum(h.get("pct") or 0 for h in top[:10])
            if top and t10 > a.max_top10: why.append(f"top-10 non-pool holders {t10:.1f}% > {a.max_top10}%")
            if (mech.get("sell_tax_pct") or 0) > a.max_sell_tax: why.append(f"sell tax {mech['sell_tax_pct']}% > {a.max_sell_tax}%")
            if not b.get("evm") and not (b.get("evm") or {}).get("hp"): why.append("no GoPlus/honeypot data (contract risk UNKNOWN; not advanced without it)")
            ds_liq = b["market"].get("liquidity_usd_total"); gt_liq = c.get("liq") or 0
            liq = max(ds_liq or 0, gt_liq)
            if ds_liq is not None and gt_liq and ds_liq < 0.5 * gt_liq:
                b["discrepancies"].append(f"liquidity: DEX Screener ${ds_liq:,.0f} vs GeckoTerminal ${gt_liq:,.0f} (DS may not index this pool type, e.g. PancakeSwap Infinity / Uniswap V4)")
            if liq < a.min_liq: why.append(f"liquidity ${liq:,.0f} < ${a.min_liq:,.0f}")
            rec = {"mint": mint, "symbol": b["identity"].get("symbol") or c.get("symbol"), "pool": b["identity"].get("primary_pool") or c.get("pool"), "decimals": b["identity"].get("decimals") or 18,
                   "price": b["market"].get("price_usd") or c.get("price"), "liq": liq, "contract_risk": mech.get("contract_risk"), "flags": mech.get("flags"), "owner_state": mech.get("owner_state"),
                   "taxes": [mech.get("buy_tax_pct"), mech.get("sell_tax_pct")], "top_holder_pct": top[0].get("pct") if top else None, "top10_pct": t10 if top else None}
            if why:
                rejected.append({**rec, "why": "; ".join(why)})
                db.insert(con, "rejections", {"mint": mint, "symbol": rec["symbol"], "rejected_at": t, "stage": "stage2-evm", "why_surfaced": f"{chain} discovery: " + ", ".join((c.get("signals") or {}).get("sources") or []),
                          "why_failed": "; ".join(why)[:400], "evidence": json.dumps({"flags": sorted(hit), "owner_state": mech.get("owner_state"), "taxes": rec["taxes"], "top_holder_pct": rec["top_holder_pct"]}),
                          "reconsider_if": "contract state changes (renounce, tax to 0) or holder concentration falls below thresholds" if not hit else "never: fatal contract check"})
            else:
                deep.append(rec)
    deep = deep[:a.limit]
    out = {"id": a.stage1, "chain": chain, "observed_at": t, "native_price": s1.get("native_price"), "deep_candidates": deep, "rejected_stage2": rejected}
    (INBOX / f"{a.stage1}.stage2.json").write_text(json.dumps(out, indent=1))
    print(f"{chain}: {len(deep)} deep candidates, {len(rejected)} rejected at stage 2")
    for c in deep:
        print(f"  {c['symbol']:<12} {c['mint']}  risk {c['contract_risk']}  owner {c['owner_state']}  tax {c['taxes']}  top {c['top_holder_pct']}  liq ${c['liq']:,.0f}")
    for c in rejected:
        print(f"  x {c['symbol']:<10} {c['mint']}  {c['why'][:110]}")


# ---------------- analyze / scout ----------------
def _analyze(chain: str, addr: str, bodies: dict, t: float, bench: dict, account: dict | None, persist: bool, disc: dict | None = None):
    sol = _native_price(bodies, "solana") if chain == "solana" else None
    t = _token_time(R.norm_address(chain, addr), t)
    return pipeline.analyze_token(addr, bodies, observed_at=t, sol_price=sol, benchmarks=bench, account=account, discovery_signals=disc, persist=persist,
                                  chain=chain, native_price=_native_price(bodies, chain))


def _bench(bodies: dict, chain: str) -> dict:
    cfg = R.CHAINS[chain]; cg = bodies.get("cg_price") or {}
    bm = {}
    if isinstance(cg, dict):
        for cid, name in ((cfg["cg_native"], cfg["native_symbol"]), ("bitcoin", "BTC")):
            if isinstance(cg.get(cid), dict):
                bm[name] = {"chg_24h": cg[cid].get("usd_24h_change"), "chg_1h": None, "chg_6h": None}
    cat = cfg.get("cg_meme_category")
    peers = bodies.get(f"cg_mkts:{cat}:1") if cat and isinstance(bodies.get(f"cg_mkts:{cat}:1"), list) else bodies.get("cg_mkts:meme-token:1") or []
    bm["peers"] = [{"symbol": (m.get("symbol") or "").upper(), "mint": m.get("id"), "chg_24h": m.get("price_change_percentage_24h"), "chg_1h": m.get("p1h"), "chg_6h": None, "vol_24h": m.get("total_volume")} for m in peers if isinstance(m, dict)]
    return bm


def cmd_analyze(a):
    db.init_db()
    bodies, t = _merged(a.results)
    r = _analyze(a.chain, a.addr, bodies, t, _bench(bodies, a.chain), None, not a.no_persist)
    print(f"{a.chain} {r['bundle']['identity'].get('symbol')} score {r['score']['total']} status {r['status']['status']} -> {r.get('report_path')}")
    if a.print:
        print(r["report_md"])


def cmd_scout(a):
    db.init_db()
    bodies, t = _merged(a.results)
    eco = None
    if a.eco:
        eb, et = _merged(a.eco)
        eco = run_ecosystem(eb, et, persist=False)  # already persisted by `eco`; render only
        bodies = {**eb, **bodies}
    results = []
    for spec in a.tokens:
        chain, addr = spec.split(":", 1)
        r = _analyze(chain, addr, bodies, t, _bench(bodies, chain), {"account_size": a.account_size, "max_loss_pct": a.max_loss_pct} if a.account_size else None, True)
        r["chain"] = chain
        results.append(r)
    from ..modules import m24_opportunity_ranker as m24
    ranked = m24.rank([{"symbol": r["bundle"]["identity"].get("symbol"), "mint": r["mint"], "score_result": r["score"], "modules": r["ranker_inputs"], "status": r["status"]} for r in results])
    ok_status = ("WATCH", "SETUP DEVELOPING", "NEAR ENTRY", "ENTRY CONDITIONS MET")
    serious = sorted([r for r in results if not r["score"]["untradeable"] and r["status"]["status"] in ok_status and (r["score"]["total"] or 0) >= a.min_score], key=lambda r: -r["score"]["total"])[:5]
    near = [r for r in results if r not in serious and not r["score"]["untradeable"] and r["status"]["status"] != "REJECTED"]
    rejected = [r for r in results if r["score"]["untradeable"] or r["status"]["status"] == "REJECTED"]
    with db.connect() as con:
        rs = E.cross_chain_rs(con, t, [{"chain": r["chain"], "mint": r["mint"], "symbol": r["bundle"]["identity"].get("symbol"), "chg_24h": (r["bundle"]["market"].get("chg") or {}).get("24h"), "mcap": r["bundle"]["market"].get("market_cap")} for r in results], bodies)
        # narrative tagging
        for r in results:
            nid = NR.narrative_for_token(con, r["mint"], r["bundle"]["identity"].get("name"), r["bundle"]["identity"].get("symbol"))
            r["narrative_id"] = nid
            if nid:
                con.execute("UPDATE tokens SET narrative_id=? WHERE mint=?", (nid, r["mint"]))
    alloc = allocate(serious, eco["regime"] if eco else None, a.account_size)
    md = render_cross_chain(eco, serious, near, rejected, rs, alloc, ranked, t)
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"{time.strftime('%Y%m%d_%H%M', time.gmtime(t))}_SCOUT_MULTICHAIN.md"
    path.write_text(md)
    print(md if a.print else f"{len(serious)} serious, {len(near)} near misses, {len(rejected)} rejected")
    print(f"-> {path}")


def allocate(serious: list[dict], regime: dict | None, account_size: float | None) -> dict[str, Any]:
    """Cross-chain allocation with correlation awareness: same chain or same narrative shares one risk budget."""
    mult = (regime or {}).get("size_multiplier", 0.75) if regime else 0.75
    base = (account_size or 0) * 0.25 * mult  # at most a quarter of the account at risk across all open ideas, scaled by regime
    groups: dict[str, list[dict]] = {}
    for r in serious:
        key = f"{r['chain']}|{r.get('narrative_id') or 'none'}"
        groups.setdefault(key, []).append(r)
    rows = []
    n_groups = max(len(groups), 1)
    for key, rs in groups.items():
        budget = base / n_groups
        for r in rs:
            sz = (r["modules"].get("sizing") or {}).get("allowed_size_usd")
            cap = budget / len(rs)
            rows.append({"symbol": r["bundle"]["identity"].get("symbol"), "chain": r["chain"], "narrative": r.get("narrative_id"), "group": key, "module_size_usd": sz, "group_cap_usd": round(cap, 2),
                         "size_usd": round(min(sz, cap), 2) if sz is not None and base else None, "note": ("shares a budget with " + ", ".join(x["bundle"]["identity"].get("symbol") or "?" for x in rs if x is not r)) if len(rs) > 1 else "independent group"})
    return {"regime_multiplier": mult, "total_risk_budget_usd": round(base, 2), "groups": n_groups, "rows": rows,
            "rule": "same chain + same narrative = one group; budget splits across groups equally, then within a group; the per-token size is the smaller of the sizing module's number and the group cap"}


def render_cross_chain(eco: dict | None, serious: list, near: list, rejected: list, rs: list, alloc: dict, ranked: dict, t: float) -> str:
    from ..report import render_scout_report, _usd, _pct
    L = []
    if eco:
        L.append(eco["md"])
    L += ["# BEST CROSS-CHAIN OPPORTUNITIES", ""]
    if not serious:
        L.append("No token on any chain met the bar this run. That is a valid outcome.")
    for i, r in enumerate(serious, 1):
        b, m, sc, st = r["bundle"], r["modules"], r["score"], r["status"]
        ident, mk = b["identity"], b["market"]
        dp, hold, lc, mech, ex = (m.get(k) or {} for k in ("depth", "holders", "lifecycle", "mechanics", "execution"))
        rsr = next((x for x in rs if x["mint"] == r["mint"]), {})
        L.append(f"## #{i} {ident.get('symbol')} on {R.CHAINS[r['chain']]['name']}")
        L.append("")
        L.append(f"- CHAIN: {r['chain']}; CONTRACT/MINT: `{r['mint']}`; TOKEN STANDARD: {ident.get('token_standard') or m['identity'].get('token_program')}; PRIMARY POOL: `{ident.get('primary_pool') or (b['pools'][0]['pool'] if b.get('pools') else 'UNKNOWN')}`; IDENTITY CONFIDENCE: {m['identity'].get('confidence')}")
        L.append(f"- Narrative: {r.get('narrative_id') or 'none assigned'}; lifecycle {lc.get('stage')} ({lc.get('confidence')}); market cap {_usd(mk.get('market_cap'))}; liquidity {_usd(mk.get('liquidity_usd_total'))}")
        L.append(f"- Executable depth: sell ~{_usd(dp.get('exit_capacity_usd_3pct'))} at 3%, ~{_usd(dp.get('exit_capacity_usd_10pct'))} at 10%" + (f"; execution friction on $1,000 about {ex.get('friction_pct_on_1000'):.2f}% (gas ~${ex.get('gas_round_trip_usd'):.2f}, taxes {ex.get('tax_round_trip_pct')}%)" if ex else ""))
        L.append(f"- Contract risk: {mech.get('contract_risk') or 'see mechanics'}" + (f"; owner {mech.get('owner_state')}; flags {', '.join(mech.get('flags') or []) or 'none'}" if mech.get("contract_risk") else ""))
        L.append(f"- Ownership: adjusted top-10 {_pct(hold.get('adjusted_top10_pct'), 1)}, largest unexplained {_pct(hold.get('largest_unexplained_pct'))}")
        stale = (t - b["observed_at"]) / 3600 > 3
        L.append(("- Cross-chain RS (24h, STALE: token data older than the chain medians, treat as indicative only): " if stale else "- Cross-chain RS (24h): ") + f"vs chain memes {rsr.get('rs_vs_chain') if rsr.get('rs_vs_chain') is None else round(rsr['rs_vs_chain'], 1)}; vs global basket {rsr.get('rs_vs_global') if rsr.get('rs_vs_global') is None else round(rsr['rs_vs_global'], 1)}; vs native {rsr.get('rs_vs_native') if rsr.get('rs_vs_native') is None else round(rsr['rs_vs_native'], 1)} ({rsr.get('note')})")
        age_h = (t - b["observed_at"]) / 3600
        L.append(f"- Score {sc.get('total')}/100; status {st['status']}; {st.get('reasoning', '')}" + (f" DATA AGE: {age_h:.0f}h older than this report (refresh blocked this run)" if age_h > 3 else ""))
        L.append(f"- Report: {r.get('report_path')}")
        L.append("")
    L += ["## Cross-chain allocation", "", f"- Regime multiplier {alloc['regime_multiplier']}; total risk budget ${alloc['total_risk_budget_usd']:,.2f} across {alloc['groups']} correlation group(s). {alloc['rule']}"]
    for row in alloc["rows"]:
        L.append(f"- {row['symbol']} ({row['chain']}, narrative {row['narrative'] or 'none'}): module size {row['module_size_usd']}, group cap ${row['group_cap_usd']:,.2f} -> size {row['size_usd']}; {row['note']}")
    L.append("")
    L += ["# NEAR MISSES", ""]
    L += [f"- {r['bundle']['identity'].get('symbol')} ({r['chain']}) `{r['mint']}`: score {r['score']['total']}, status {r['status']['status']}; {r['status'].get('reasoning')}" for r in near] or ["- none"]
    L += ["", "# REJECTED AFTER DUE DILIGENCE", ""]
    L += [f"- {r['bundle']['identity'].get('symbol')} ({r['chain']}) `{r['mint']}`: {r['status'].get('reasoning')}" + ("; fatal: " + ", ".join(f['flag'] for f in r['score']['fatal_flags']) if r["score"].get("fatal_flags") else "") for r in rejected] or ["- none"]
    L.append("")
    L.append(f"Best token vs best trade: {ranked.get('best_token_vs_best_trade')}")
    return "\n".join(L)


def add_subparser(sp):
    p = sp.add_parser("chains", help="multi-chain ecosystem layer")
    s = p.add_subparsers(dest="chains_cmd", required=True)
    q = s.add_parser("plan"); q.add_argument("kind", choices=["eco", "disc", "struct", "deep"]); q.add_argument("chain", nargs="?"); q.add_argument("target", nargs="?"); q.add_argument("--id"); q.add_argument("--js", action="store_true"); q.set_defaults(fn=cmd_plan)
    q = s.add_parser("eco"); q.add_argument("--results", nargs="+", required=True); q.add_argument("--print", action="store_true"); q.add_argument("--no-persist", action="store_true"); q.set_defaults(fn=cmd_eco)
    q = s.add_parser("discover"); q.add_argument("chain"); q.add_argument("id"); q.add_argument("--results", nargs="+", required=True); q.add_argument("--min-liq", type=float, default=50_000); q.add_argument("--min-vol", type=float, default=100_000)
    q.add_argument("--min-age-hours", type=float, default=12); q.add_argument("--min-buyers", type=int, default=150); q.add_argument("--limit", type=int, default=40); q.add_argument("--show", type=int, default=40); q.add_argument("--rejection-ttl-hours", type=float, default=72); q.set_defaults(fn=cmd_discover)
    q = s.add_parser("struct"); q.add_argument("stage1"); q.add_argument("--results", nargs="+", required=True); q.add_argument("--limit", type=int, default=8); q.add_argument("--max-single-holder", type=float, default=15); q.add_argument("--max-top10", type=float, default=50)
    q.add_argument("--max-sell-tax", type=float, default=5); q.add_argument("--min-liq", type=float, default=50_000); q.set_defaults(fn=cmd_struct)
    q = s.add_parser("analyze"); q.add_argument("chain"); q.add_argument("addr"); q.add_argument("--results", nargs="+", required=True); q.add_argument("--no-persist", action="store_true"); q.add_argument("--print", action="store_true"); q.set_defaults(fn=cmd_analyze)
    q = s.add_parser("scout"); q.add_argument("--tokens", nargs="+", required=True, help="chain:address"); q.add_argument("--results", nargs="+", required=True); q.add_argument("--eco", nargs="*"); q.add_argument("--min-score", type=int, default=55)
    q.add_argument("--account-size", type=float); q.add_argument("--max-loss-pct", type=float, default=2.0, help="max loss per idea as %% of account (default 2)"); q.add_argument("--print", action="store_true"); q.set_defaults(fn=cmd_scout)
