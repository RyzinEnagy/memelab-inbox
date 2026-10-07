"""Pipeline orchestration: bundle -> all modules -> score/status -> persistence -> report."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from . import db
from .normalize import build_bundle
from .modules import (m02_identity_verification as m02, m03_market_data as m03, m04_supply_reconciliation as m04, m05_pool_discovery as m05,
                      m06_executable_depth as m06, m07_lp_analysis as m07, m08_token_mechanics as m08, m09_holder_classification as m09,
                      m10_wallet_clustering as m10, m11_early_wallet_analysis as m11, m12_order_flow as m12, m13_price_structure as m13,
                      m14_breakout_classifier as m14, m15_entry_invalidation as m15, m16_risk_reward as m16, m17_position_sizing as m17,
                      m18_exit_planning as m18, m19_attention_analysis as m19, m20_manipulation_detection as m20, m21_lifecycle_classifier as m21,
                      m22_relative_strength as m22, m23_trade_thesis as m23, m24_opportunity_ranker as m24, m25_watchlist_monitor as m25)


def _safe(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as e:  # modules should never raise, but the pipeline must survive if one does
        return {"error": f"{type(e).__name__}: {e}", "facts": [], "inferences": [], "heuristics": [], "unknowns": [f"module failed: {type(e).__name__}: {e}"]}


def run_modules(bundle: dict[str, Any], benchmarks: dict | None = None, account: dict | None = None, wallet_txs: dict | None = None,
                social_obs: list | None = None) -> dict[str, dict]:
    account = account or {}
    m: dict[str, dict] = {}
    m["identity"] = _safe(m02.analyze, bundle)
    m["market"] = _safe(m03.analyze, bundle)
    m["pools"] = _safe(m05.analyze, bundle)
    m["depth"] = _safe(m06.analyze, bundle)
    m["lp"] = _safe(m07.analyze, bundle)
    m["mechanics"] = _safe(m08.analyze, bundle, depth=m["depth"])
    m["holders"] = _safe(m09.analyze, bundle)
    m["supply"] = _safe(m04.analyze, bundle, holders_out=m["holders"])
    m["clusters"] = _safe(m10.analyze, bundle, holders_out=m["holders"], wallet_txs=wallet_txs)
    m["early"] = _safe(m11.analyze, bundle, holders_out=m["holders"])
    m["orderflow"] = _safe(m12.analyze, bundle)
    m["structure"] = _safe(m13.analyze, bundle)
    m["breakout"] = _safe(m14.analyze, bundle, structure=m["structure"])
    m["entries"] = _safe(m15.analyze, bundle, structure=m["structure"], breakout=m["breakout"])
    m["rr"] = _safe(m16.analyze, bundle, entries=m["entries"], structure=m["structure"])
    m["sizing"] = _safe(m17.analyze, bundle, entries=m["entries"], structure=m["structure"], **{k: account.get(k) for k in ("account_size", "max_loss_usd", "max_loss_pct") if account.get(k) is not None})
    m["exit"] = _safe(m18.analyze, bundle, entries=m["entries"], structure=m["structure"], position_usd=account.get("position_usd"))
    m["attention"] = _safe(m19.analyze, bundle, social_obs=social_obs)
    m["manipulation"] = _safe(m20.analyze, bundle, orderflow=m["orderflow"], clusters=m["clusters"], attention=m["attention"])
    m["lifecycle"] = _safe(m21.analyze, _lifecycle_view(bundle), structure=m["structure"], flows=m["early"], attention=m["attention"])
    m["rs"] = _safe(m22.analyze, bundle, benchmarks or {})
    return m


def _lifecycle_view(bundle: dict[str, Any]) -> dict[str, Any]:
    """m21 reads windows as h1/h6/h24 and holder change as *_pct; the bundle uses 1h/6h/24h. Provide both."""
    mk = dict(bundle.get("market") or {})
    alias = {"5m": "m5", "1h": "h1", "6h": "h6", "24h": "h24"}
    for key in ("vol", "chg", "net_buyers", "txns"):
        d = dict(mk.get(key) or {})
        for k, v in list(d.items()):
            if k in alias:
                d[alias[k]] = v
        mk[key] = d
    hc = dict(mk.get("holder_change") or {})
    for k, v in list(hc.items()):
        if k in alias and v is not None:
            hc[f"{alias[k]}_pct"] = v
    mk["holder_change"] = hc
    if mk.get("liquidity_change_24h") is not None:
        mk["liquidity_change_pct"] = mk["liquidity_change_24h"]
    b = dict(bundle); b["market"] = mk
    return b


def ranker_inputs(m: dict[str, dict]) -> dict[str, dict]:
    """Adapt module outputs to the key aliases m24 reads."""
    st, bo, en, rr, sz, dp = m.get("structure") or {}, m.get("breakout") or {}, m.get("entries") or {}, m.get("rr") or {}, m.get("sizing") or {}, m.get("depth") or {}
    price = st.get("price") or (en.get("price"))
    zones = []
    for e in en.get("entries") or []:
        lo, hi = e.get("zone_low"), e.get("zone_high")
        in_zone = bool(price and lo is not None and hi is not None and lo <= price <= hi)
        zones.append({"style": e.get("style"), "in_zone": in_zone, "invalidation_level": e.get("invalidation_level"), "pending": e.get("pending")})
    entries_adapted = {"zones": zones, "in_zone": any(z["in_zone"] for z in zones) if zones else None,
                       "invalidation_defined": any(z["invalidation_level"] is not None for z in zones) if zones else False, "n": len(zones)}
    pe = rr.get("per_entry") or []
    best = None
    if pe:
        best = max(pe, key=lambda p: ((p.get("ev_r_low") or -9) + (p.get("ev_r_high") or -9)) / 2)
    rr_adapted = {"rr_ratio": best.get("rr_base") if best else None, "rr_bull": best.get("rr_bull") if best else None,
                  "ev_r": ((best.get("ev_r_low") or 0) + (best.get("ev_r_high") or 0)) / 2 if best else None,
                  "invalidation_defined": bool(best and best.get("invalidation_level") is not None), "best_style": best.get("style") if best else None}
    size = sz.get("allowed_size_usd")
    sizing_adapted = {"size_usd": size, "fits_constraints": (size is not None and size > 0) if not sz.get("needs_account_inputs") else None, **sz}
    structure_adapted = {**st, "levels": st.get("zones") or [], "support_defined": bool(st.get("nearest_support"))}
    breakout_adapted = {**bo, "chase_risk": bool((bo.get("chase_risk") or {}).get("overextended")) if isinstance(bo.get("chase_risk"), dict) else bool(bo.get("chase_risk"))}
    return {"depth": dp, "lp": m.get("lp"), "mechanics": m.get("mechanics"), "holders": m.get("holders"), "clusters": m.get("clusters"), "early": m.get("early"),
            "orderflow": m.get("orderflow"), "structure": structure_adapted, "breakout": breakout_adapted, "entries": entries_adapted, "rr": rr_adapted,
            "attention": m.get("attention"), "manipulation": m.get("manipulation"), "lifecycle": m.get("lifecycle"), "rs": m.get("rs"), "sizing": sizing_adapted}


def analyze_token(mint: str, bodies: dict[str, Any], observed_at: float | None = None, sol_price: float | None = None, benchmarks: dict | None = None,
                  account: dict | None = None, discovery_signals: dict | None = None, wallet_txs: dict | None = None, social_obs: list | None = None,
                  persist: bool = True, report_dir: Path | None = None) -> dict[str, Any]:
    bundle = build_bundle(mint, bodies, observed_at=observed_at, sol_price=sol_price)
    forensics_out = None
    if wallet_txs is None and any(k.startswith("helius_tx:") for k in bodies):
        from . import forensics
        wallet_txs, profiles = forensics.build_wallet_txs(bodies, mint)
        bundle["wallet_profiles"] = profiles
        forensics_out = profiles
    if discovery_signals:
        bundle["discovery_signals"] = discovery_signals
    unacceptable = m23.unacceptable_conditions(bundle)
    mods = run_modules(bundle, benchmarks=benchmarks, account=account, wallet_txs=wallet_txs, social_obs=social_obs)
    if forensics_out:
        from . import forensics
        dev_set = {x for x in ((bundle.get("identity") or {}).get("creator"), (bundle.get("identity") or {}).get("dev")) if x}
        mods["forensics"] = {**forensics.summarize_profiles(forensics_out, mods.get("holders"), dev_set), "heuristics": ["address is not person; shared funding is economic linkage only"], "unknowns": []}
    ident = mods["identity"]
    prev = None
    if persist:
        with db.connect() as con:
            prev = db.previous_thesis(con, mint)
    prev_snap = json.loads(prev["snapshot_json"]) if prev and prev["snapshot_json"] else None
    prev_inv = None
    if prev:
        with db.connect() as con:
            row = con.execute("SELECT invalidation_level FROM entries WHERE thesis_id=? ORDER BY id LIMIT 1", (prev["id"],)).fetchone()
            prev_inv = row["invalidation_level"] if row else None
    ri = ranker_inputs(mods)
    if ident.get("status") == "IDENTITY NOT VERIFIED":
        score_result = {"total": 0, "breakdown": {}, "fatal_flags": [{"flag": "IDENTITY_NOT_VERIFIED", "evidence": "; ".join(ident.get("unknowns", [])), "severity": "FATAL", "category": "identity"}], "untradeable": True, "unknown_buckets": list(m24.HELPERS), "unknown_count": 8}
        status = {"status": "REJECTED", "reasoning": "IDENTITY NOT VERIFIED"}
    else:
        comps, rats = m24.derive_components(**ri)
        score_result = m24.score({k: (comps[k], rats[k]) for k in comps}, **ri)
        cur_tmp = m25.compact_snapshot(bundle, mods, score_result, None)
        mdiff = m25.diff(prev_snap, cur_tmp, prev_invalidation_level=prev_inv, prev_interpretation=prev["thesis_text"] if prev else None)
        status = m24.assign_status(score_result, breakout=ri["breakout"], entries=ri["entries"], lifecycle=mods["lifecycle"], early=mods["early"], monitor_diff=mdiff if not mdiff.get("first_snapshot") else None)
        mods["monitor"] = mdiff
    thesis = m23.assemble(bundle, mods)
    snapshot = m25.compact_snapshot(bundle, mods, score_result, status["status"])
    result = {"mint": mint, "bundle": bundle, "modules": mods, "ranker_inputs": ri, "score": score_result, "status": status, "thesis": thesis,
              "unacceptable": unacceptable, "snapshot": snapshot, "previous_snapshot": prev_snap}
    from .report import render_token_report
    report_md = render_token_report(result)
    result["report_md"] = report_md
    if persist:
        path = persist_result(result, report_dir)
        result["report_path"] = str(path)
    return result


def persist_result(r: dict[str, Any], report_dir: Path | None = None) -> Path:
    b, mods = r["bundle"], r["modules"]
    mint = r["mint"]; t = b["observed_at"]
    ident, mk = b.get("identity") or {}, b.get("market") or {}
    report_dir = report_dir or (db.DATA_DIR / "reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    sym = (ident.get("symbol") or "UNKNOWN").replace("/", "_")[:12]
    path = report_dir / f"{time.strftime('%Y%m%d_%H%M', time.gmtime(t))}_{sym}_{mint[:6]}.md"
    path.write_text(r["report_md"])
    with db.connect() as con:
        db.upsert_token(con, mint, name=ident.get("name"), symbol=ident.get("symbol"), decimals=ident.get("decimals"), token_program=ident.get("token_program"),
                        creator=ident.get("creator"), dev_wallet=ident.get("dev"), launchpad=ident.get("launchpad"), graduated_pool=ident.get("graduated_pool"),
                        graduated_at=ident.get("graduated_at"), first_pool_at=ident.get("first_pool_at"), website=(b.get("social") or {}).get("website"),
                        twitter=(b.get("social") or {}).get("twitter"), identity_confidence=mods["identity"].get("confidence"))
        vol, nb, tx = mk.get("vol") or {}, mk.get("net_buyers") or {}, mk.get("txns") or {}
        db.insert(con, "market_snapshots", {"mint": mint, "observed_at": t, "source": "merged", "price_usd": mk.get("price_usd"), "price_sol": mk.get("price_sol"),
                  "circ_supply": mk.get("circ_supply"), "total_supply": mk.get("total_supply"), "market_cap": mk.get("market_cap"), "fdv": mk.get("fdv"),
                  "liquidity_usd": mk.get("liquidity_usd_total"), "vol_5m": vol.get("5m"), "vol_1h": vol.get("1h"), "vol_6h": vol.get("6h"), "vol_24h": vol.get("24h"),
                  "buys_1h": (tx.get("1h") or [None])[0], "sells_1h": (tx.get("1h") or [None, None])[1], "buys_24h": (tx.get("24h") or [None])[0], "sells_24h": (tx.get("24h") or [None, None])[1],
                  "buy_vol_24h": mk.get("buy_vol_24h"), "sell_vol_24h": mk.get("sell_vol_24h"), "organic_buy_vol_24h": mk.get("organic_buy_vol_24h"), "organic_sell_vol_24h": mk.get("organic_sell_vol_24h"),
                  "net_buyers_1h": nb.get("1h"), "net_buyers_24h": nb.get("24h"), "holder_count": mk.get("holder_count"),
                  "chg_5m": (mk.get("chg") or {}).get("5m"), "chg_1h": (mk.get("chg") or {}).get("1h"), "chg_6h": (mk.get("chg") or {}).get("6h"), "chg_24h": (mk.get("chg") or {}).get("24h"),
                  "raw_json": json.dumps({"sources": b.get("sources"), "discrepancies": b.get("discrepancies")})})
        for p in b.get("pools") or []:
            if not p.get("pool"):
                continue
            con.execute("INSERT OR IGNORE INTO pools (pool_address, mint, dex, quote_mint, pool_created_at, first_seen_at) VALUES (?,?,?,?,?,?)",
                        (p["pool"], mint, p.get("dex") or p.get("market_type"), p.get("quote"), p.get("created"), t))
            db.insert(con, "pool_snapshots", {"pool_address": p["pool"], "observed_at": t, "source": p.get("source"), "reserve_usd": p.get("reserve_usd"), "base_reserve": p.get("base_reserve"),
                      "quote_reserve": p.get("quote_reserve"), "vol_24h": p.get("vol_24h"), "price_usd": p.get("price"), "raw_json": json.dumps(p.get("lp"))})
        for side, qs in (b.get("quotes") or {}).items():
            for usd, q in qs.items():
                db.insert(con, "liquidity_quotes", {"mint": mint, "observed_at": t, "side": side, "usd_size": float(usd), "in_amount": q.get("in"), "out_amount": q.get("out"),
                          "price_impact_pct": (q.get("impact") or 0) * 100 if q.get("status") == "OK" else None, "route_json": json.dumps(q.get("route")), "n_pools": len(q.get("route") or []),
                          "status": q.get("status"), "error": str(q.get("error"))[:200] if q.get("error") else None})
        a = b.get("authorities") or {}
        mech = mods.get("mechanics") or {}
        db.insert(con, "token_authorities", {"mint": mint, "observed_at": t, "source": "merged", "mint_authority": mech.get("mint_authority"), "freeze_authority": mech.get("freeze_authority"),
                  "token_program": mech.get("token_program"), "extensions_json": json.dumps(mech.get("extensions")), "transfer_fee_bps": mech.get("transfer_fee_bps"),
                  "permanent_delegate": mech.get("permanent_delegate"), "metadata_mutable": a.get("metadata_mutable"), "update_authority": a.get("update_authority"),
                  "supply_raw": str(a.get("supply_raw")) if a.get("supply_raw") is not None else None, "decimals": a.get("decimals")})
        for c in (mods.get("holders") or {}).get("classified") or []:
            db.insert(con, "holders", {"mint": mint, "observed_at": t, "source": "rugcheck", "rank": c.get("rank"), "token_account": c.get("account"), "owner": c.get("owner"),
                      "amount": c.get("amount"), "pct": c.get("pct"), "classification": c.get("classification"), "classification_basis": c.get("basis"), "insider_flag": 1 if c.get("classification") == "INSIDER" else 0})
        for c in (mods.get("clusters") or {}).get("clusters") or []:
            db.insert(con, "wallet_clusters", {"mint": mint, "observed_at": t, "cluster_key": c["key"], "members_json": json.dumps(c["members"]), "combined_pct": c.get("pct"),
                      "evidence_json": json.dumps(c.get("evidence")), "confidence": c.get("confidence")})
        for tr in b.get("trades") or []:
            db.insert(con, "wallet_transactions", {"mint": mint, "tx_hash": tr[6] if len(tr) > 6 else None, "block_time": tr[0], "wallet": tr[1], "kind": tr[2], "base_amount": tr[3], "usd": tr[4], "price_usd": tr[5], "source": "geckoterminal"})
        for z in (mods.get("structure") or {}).get("zones") or []:
            db.insert(con, "price_levels", {"mint": mint, "observed_at": t, "timeframe": z.get("tf"), "kind": z.get("kind"), "low": z.get("low"), "high": z.get("high"), "strength": z.get("strength"), "why": z.get("why")})
        att = mods.get("attention") or {}
        for w, v in (att.get("holder_change") or {}).items():
            if v is not None:
                db.insert(con, "social_snapshots", {"mint": mint, "observed_at": t, "source": "jupiter", "metric": f"holder_change_{w}", "value": v})
        tid = db.insert(con, "theses", {"mint": mint, "created_at": t, "lifecycle": (mods.get("lifecycle") or {}).get("stage"), "structure": (mods.get("structure") or {}).get("structure"),
                        "thesis_text": (r["thesis"]["questions"].get("IS SUPPLY BEING ACCUMULATED OR DISTRIBUTED?") or "") + " | " + (r["status"].get("reasoning") or ""),
                        "invalidation_text": r["thesis"]["questions"].get("WHAT INVALIDATES THE THESIS?"), "score": r["score"].get("total"), "score_breakdown_json": json.dumps(r["score"].get("breakdown")),
                        "fatal_flags_json": json.dumps(r["score"].get("fatal_flags")), "status": r["status"]["status"], "confidence": _confidence(r), "report_path": str(path), "snapshot_json": json.dumps(r["snapshot"])})
        for e in (mods.get("entries") or {}).get("entries") or []:
            pe = next((p for p in (mods.get("rr") or {}).get("per_entry") or [] if p.get("style") == e.get("style")), None)
            db.insert(con, "entries", {"thesis_id": tid, "mint": mint, "style": e.get("style"), "condition": e.get("condition"), "zone_low": e.get("zone_low"), "zone_high": e.get("zone_high"),
                      "invalidation_level": e.get("invalidation_level"), "invalidation_text": e.get("invalidation_text"), "expected_execution": e.get("expected_execution"), "rr_json": json.dumps(pe)})
        st = r["status"]["status"]
        if st == "REJECTED":
            db.insert(con, "rejections", {"mint": mint, "symbol": ident.get("symbol"), "rejected_at": t, "stage": "deep", "why_surfaced": r["thesis"]["questions"].get("WHY IS IT RECEIVING ATTENTION?"),
                      "why_failed": r["status"].get("reasoning"), "evidence": "; ".join(f"{f['flag']}: {f['evidence']}" for f in r["score"].get("fatal_flags") or []),
                      "reconsider_if": _reconsider(r)})
            con.execute("DELETE FROM watchlist WHERE mint=?", (mint,))
        else:
            con.execute("INSERT INTO watchlist (mint, added_at, status, last_status_change) VALUES (?,?,?,?) ON CONFLICT(mint) DO UPDATE SET status=excluded.status, last_status_change=excluded.last_status_change",
                        (mint, t, st, t))
    return path


def _confidence(r: dict) -> str:
    unk = r["score"].get("unknown_count") or 0
    idc = r["modules"]["identity"].get("confidence")
    if idc in ("LOW", "NOT VERIFIED") or unk >= 4:
        return "LOW"
    if unk >= 2:
        return "MODERATE"
    return "HIGH"


def _reconsider(r: dict) -> str:
    flags = [f["flag"] for f in r["score"].get("fatal_flags") or []]
    out = []
    for f in flags:
        if "MINT" in f or "FREEZE" in f or "DELEGATE" in f:
            out.append("authority revoked on-chain")
        elif "LP" in f:
            out.append("LP locked/burned or migrated to protocol-custodied pool")
        elif "EXIT" in f or "ROUTE" in f or "DEPTH" in f:
            out.append("executable sell depth at 5% impact exceeds $5k")
        elif "HOLDER" in f or "CLUSTER" in f or "CONCENTRATION" in f:
            out.append("largest unexplained holder / cluster falls below threshold through absorbed distribution")
        elif "MANIP" in f or "WASH" in f:
            out.append("organic volume share and turnover normalize for several days")
        elif "DISTRIBUT" in f:
            out.append("insider inventory stabilizes and price reclaims structure with volume")
        elif "IDENTITY" in f:
            out.append("mint resolved consistently across sources")
    return "; ".join(dict.fromkeys(out)) or "no specific condition identified"
