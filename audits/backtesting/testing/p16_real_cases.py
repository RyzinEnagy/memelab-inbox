"""Phase 16 real historical cases, on a COPY of the research corpus (never the original).
Usage: python3 audits/backtesting/testing/p16_real_cases.py <copy of bt.sqlite> > audits/backtesting/testing/p16_real_cases.json
Cases (all real, dated, with provenance from the lab's own committed records):
  RUG       3GVSN8...pump ("D O T"): pump.fun graduation seen by the lab's launch monitor, lab REJECTED it (DEV_WALLET_FARM), collapsed
  FAILED    FgnSJw...pump ("puter"): graduation seen 12 min after its first trade, ran up, then -99% within 24 h
  POSITIVE  7K52aY...EcxLh ("PQC"): graduation, +190% over the next 24 h (then -18% at 72 h)
  FRESH     G9wFzt...pump ("QTC"): lab thesis RESEARCH REQUIRED when its pool was 2.4 h old (3 closed hourly bars)
For each: the lab's records at the time (with git commit), the package's outcome windows, what the strategies did in a
replay, the FAST-stage stress for the lab's own snapshot at the decision time, and the report for the mint.
Also: the same ticker "D O T" on two mints (G01, real)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from memelab.backtest import assess, outcomes as O, quality, report, runner, store, stress as S  # noqa: E402
from memelab.backtest.engine import Engine, EngineConfig  # noqa: E402
from memelab.backtest.sources import lab_events  # noqa: E402
from memelab.backtest.strategies import registry  # noqa: E402

CASES = {"RUG": "3GVSN8DLVvrxEafP7JQj6CwBFRxCq8vuUVmsRbCEpump", "FAILED_CATALYST": "FgnSJwFoote99diZUhtRV9Ajcfwzjj6hDx82TDhVpump",
         "POSITIVE_CATALYST": "7K52aYQW9rWGjwZmQ7o2d1P6E7bji6hSMsqaLy5EcxLh", "FRESH": "G9wFzt1XqToHN64yrVae5JxFfY9v4K9w7quJ6zXpump"}
DOT_TWIN = "46hMQPKT2sPw"


def iso(t):
    return None if t is None else time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(t))


def main(db: Path):
    assert db.resolve() != (ROOT / "data" / "backtest" / "bt.sqlite").resolve(), "use a copy"
    con = store.connect(db)
    asof = con.execute("SELECT MAX(available_at) FROM bt_market_bars").fetchone()[0]
    launches = lab_events.launch_catalysts(ROOT)
    out = {"corpus_asof": iso(asof), "cases": {}}
    sol = runner.sol_usd_series(con)
    # replay runs (not saved): the lab-status strategy and the catalyst strategy with the lab's launch records
    runs = {}
    for sid, params in (("LAB_STATUS", {}), ("CATALYST_VERIFIED", {"min_origins": 1})):
        r = runner.run(con, sid, params=params, save=False)
        runs[sid] = r
    for name, mint in CASES.items():
        c = {"mint": mint}
        la = [x for x in launches if x["mint"] == mint]
        c["launch_records"] = [{k: x[k] for k in ("claim_type", "origin_group", "mint_verified", "source_commit", "lab_status")} |
                               {"first_seen_utc": iso(x["first_seen_at"]), "claimed_event_utc": iso(x["published_at"]), "committed_utc": iso(x["committed_by"])} for x in la]
        uni = [dict(r) for r in con.execute("SELECT basis, symbol, status_at_entry, score_at_entry, entered_at, committed_by, source_commit, snapshot_json, fatal_flags_json "
                                            "FROM bt_universe_members WHERE mint=? ORDER BY entered_at, id", (mint,))]
        c["lab_records"] = [{"basis": u["basis"], "symbol": u["symbol"], "status": u["status_at_entry"], "score": u["score_at_entry"], "entered_utc": iso(u["entered_at"]),
                             "committed_utc": iso(u["committed_by"]), "commit": (u["source_commit"] or "")[:12], "fatal_flags": json.loads(u["fatal_flags_json"] or "[]"),
                             "price": (json.loads(u["snapshot_json"] or "{}") or {}).get("price"), "liquidity": (json.loads(u["snapshot_json"] or "{}") or {}).get("liquidity")}
                            for u in uni]
        pools = [dict(p) for p in con.execute("SELECT pool_address, dex, pool_type, pool_created_at, observed_at FROM bt_pool_versions WHERE mint=?", (mint,))]
        c["pools"] = [{"pool": p["pool_address"], "dex": p["dex"], "type": p["pool_type"], "created_utc": iso(p["pool_created_at"]), "observed_utc": iso(p["observed_at"])} for p in pools]
        b = con.execute("SELECT COUNT(*), MIN(start), MAX(end), MIN(l), MAX(h) FROM bt_market_bars WHERE mint=? AND timeframe_s=3600", (mint,)).fetchone()
        c["bars"] = {"n": b[0], "from": iso(b[1]), "to": iso(b[2]), "min_low": b[3], "max_high": b[4]}
        # decision points: the first lab thesis and (if any) the graduation record
        th = next((u for u in uni if u["basis"] == "THESIS"), None)
        decisions = []
        if la:
            decisions.append(("launch_record", la[0]["available_at"]))
        if th:
            decisions.append(("lab_thesis", th["entered_at"]))
        c["outcomes"] = {}
        for label, t in decisions:
            opp = {"chain": "solana", "mint": mint, "decision_time": t, "opportunity_id": f"p16:{label}"}
            c["outcomes"][label] = {"decision_utc": iso(t)}
            for h in (3600, 6 * 3600, 24 * 3600, 72 * 3600):
                o = O.outcome_for(con, opp, h, asof)
                rz = o.get("realized") or {}
                c["outcomes"][label][f"{h // 3600}h"] = {"state": o["state"], "ret_close": rz.get("ret_close"), "max_drawdown": rz.get("max_drawdown"),
                                                          "max_runup": rz.get("max_runup"), "reason": o.get("missing_reason")}
        # lab's contemporaneous price vs the bar that contains that moment (independent provider pulls vs GeckoTerminal bars)
        if th:
            snap = json.loads(th["snapshot_json"] or "{}")
            bar = con.execute("SELECT start, l, h, c FROM bt_market_bars WHERE mint=? AND timeframe_s=3600 AND start<=? AND end>? ORDER BY volume_usd DESC LIMIT 1",
                              (mint, th["entered_at"], th["entered_at"])).fetchone()
            c["lab_price_vs_bar"] = {"lab_price": snap.get("price"), "bar_low": bar["l"] if bar else None, "bar_high": bar["h"] if bar else None,
                                     "inside_bar_range": bool(bar and bar["l"] * 0.999 <= (snap.get("price") or 0) <= bar["h"] * 1.001)}
            # FAST-stage stress from the lab's own snapshot at the thesis time (no router quotes were stored with theses)
            pv = con.execute("SELECT pool_type, dex FROM bt_pool_versions WHERE mint=? ORDER BY pool_created_at LIMIT 1", (mint,)).fetchone()
            fee, fee_basis = assess.X.assumed_swap_fee(pv["dex"] if pv else None)
            sp = S.Snapshot(chain="solana", mint=mint, as_of=th["entered_at"], price_usd=snap.get("price") or 0.0, liquidity_usd=snap.get("liquidity"),
                            pool_type=pv["pool_type"] if pv else "UNKNOWN", sol_usd=sol(th["entered_at"]), fatal_flags=json.loads(th["fatal_flags_json"] or "[]"),
                            status=th["status_at_entry"], score=th["score_at_entry"], swap_fee=fee, fee_basis=fee_basis)
            st = S.stress(sp, [250.0, 1000.0, 5000.0], max_loss_usd=250.0, max_exit_impact=0.05)
            c["stress_at_thesis"] = {"decision": st["decision"], "reasons": st["decision_reasons"], "max_size_usd": (st["max_size"] or {}).get("max_size_usd"),
                                     "base": [(x["size_usd"], x.get("status"), x.get("ret")) for x in st["scenarios"] if x["scenario"] == "BASE"],
                                     "sol_usd_asof": sp.sol_usd}
            # cohort evidence as the package computes it (no as-of: see defect D1) vs a point-in-time count
            coh = S.empirical_cohort(con, th["status_at_entry"])
            known = con.execute("SELECT COUNT(DISTINCT mint) FROM bt_universe_members WHERE universe_id='lab_state_history' AND basis='THESIS' AND status_at_entry IS ? AND available_at<=?",
                                (th["status_at_entry"], th["entered_at"])).fetchone()[0]
            c["cohort_evidence"] = {"package_n": coh.get("n"), "package_tier": coh.get("tier"), "cohort_tokens_known_at_decision": known}
            # token signal states and DEEP-stage replay on bars available at the thesis time
            vis = [x for x in runner._first_versions(con, mint, pools[0]["pool_address"]) if x.avail <= th["entered_at"]] if pools else []
            c["token_signals_at_thesis"] = {"closed_bars": len(vis), "signals": {sid: type(registry.make(sid).evaluate("solana", mint, vis, th["entered_at"])).__name__
                                                                                 for sid in assess.DEFAULT_POLICY["ta_strategies"]}}
            toks, skipped = runner.build_tokens(con, mints=[mint])
            deep = {}
            for sid in assess.DEFAULT_POLICY["ta_strategies"]:
                rr = Engine(EngineConfig(), sol).run(registry.make(sid), toks, until=th["entered_at"]) if toks else {"n_trades": 0}
                deep[sid] = rr["n_trades"]
            c["deep_stage_replay_trades"] = {"per_strategy": deep, "skipped": skipped, "state": "COMPLETE" if sum(deep.values()) else "INSUFFICIENT_HISTORY"}
        # what the replay strategies did with this mint
        c["replay"] = {}
        for sid, r in runs.items():
            c["replay"][sid] = {"trades": [{k: t[k] for k in ("entry_time", "exit_time", "exit_reason", "ret", "paper_ret_mid", "status")} for t in r["trades"] if t["mint"] == mint],
                                "journal": [{k: j.get(k) for k in ("t", "event", "reason")} for j in r["journal"] if j.get("mint") == mint][:8]}
        # the report a user gets for this mint today (no stored assessment exists for it)
        doc = report.build(None, con=con, lab={"chain": "solana", "mint": mint}, include_strategies=False)
        c["report_today"] = {"label": doc["headline"]["label"], "why": doc["headline"]["why"], "assessment_state": doc["trace"]["assessment_state"], "errors": report.validate(doc)}
        out["cases"][name] = c
    # G01 on real data: the ticker "D O T" on two different mints
    dot = [dict(r) for r in con.execute("SELECT DISTINCT mint, symbol FROM bt_universe_members WHERE symbol LIKE 'D%O%T%' AND length(symbol) <= 8")]
    out["same_ticker_two_mints"] = {"rows": dot, "bars_per_mint": {d["mint"]: con.execute("SELECT COUNT(*), COUNT(DISTINCT pool_address) FROM bt_market_bars WHERE mint=?", (d["mint"],)).fetchone()[:]
                                                                     for d in dot},
                                    "launch_records": [{"mint": x["mint"], "symbol": x["symbol"], "first_seen": iso(x["first_seen_at"])} for x in launches if x["symbol"] and x["symbol"].replace(" ", "").replace(" ", "") == "DOT"]}
    out["reconcile_lab_vs_bars"] = {k: v for k, v in quality.reconcile_lab_vs_bars(con).items() if k != "worst"}
    con.close()
    return out


if __name__ == "__main__":
    print(json.dumps(main(Path(sys.argv[1])), indent=1, default=str))
