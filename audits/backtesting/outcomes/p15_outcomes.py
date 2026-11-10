"""Phase 15 evidence on real data: outcomes for every frozen lab opportunity in the research corpus, calibration by
segment at 1/6/24/72 h, exit-model reconciliation against the lab's own later snapshots, drift and collector health,
a replayed daily report checked byte for byte, and a shadow evaluation. Works on a temporary COPY of
data/backtest/bt.sqlite (never written). Writes p15_outcomes.json, CALIBRATION_24H.md and DAILY_SAMPLE.md here.
Run: python audits/backtesting/outcomes/p15_outcomes.py"""
import json, shutil, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from memelab.backtest import outcomes as O, store          # noqa: E402
from memelab.backtest.sources import lab_events              # noqa: E402

HERE = Path(__file__).parent
t_start = time.time()
cats = lab_events.launch_catalysts(ROOT)                     # the lab's contemporaneous launch records (git history, read only)
out = {"protocol": O.PROTOCOL, "launch_catalyst_records": len(cats)}
with tempfile.TemporaryDirectory() as td:
    db = Path(td) / "bt.sqlite"
    shutil.copy(ROOT / "data" / "backtest" / "bt.sqlite", db)
    con = store.connect(db)
    asof = con.execute("SELECT MAX(available_at) FROM bt_market_bars").fetchone()[0]
    out["asof"] = asof
    run_hashes = [tuple(r) for r in con.execute("SELECT run_id, result_hash FROM bt_run_results ORDER BY id")]
    opps = O.opportunities(con)
    out["opportunities"] = {"total": len(opps), "by_source": {s: sum(1 for o in opps if o["source"] == s) for s in sorted({o["source"] for o in opps})},
                            "mints": len({o["mint"] for o in opps})}
    t0 = time.time()
    out["track_1"] = O.track(con, now=asof, observed_asof=asof, opps=opps)
    out["track_1"]["wall_s"] = round(time.time() - t0, 1)
    out["track_rate_limited"] = O.track(con, now=asof + 60, observed_asof=asof, opps=opps)["status"]
    out["track_2_new_rows"] = O.track(con, now=asof + 3700, observed_asof=asof, opps=opps)["new_rows"]
    out["calibration"] = {}
    for h in O.HORIZONS_S:
        cal = O.calibrate(con, asof=asof, horizon_s=h, catalysts=cats, opps=opps)
        out["calibration"][f"{h // 3600}h"] = cal
        if h == 24 * 3600:
            (HERE / "CALIBRATION_24H.md").write_text(O.render_calibration(cal))
    rec = O.exit_reconciliation(con, opps=[o for o in opps if o["source"] != "ASSESSMENT"])
    rec.pop("rows")
    out["exit_reconciliation_24h"] = rec
    out["drift"] = O.drift(con, now=asof, opps=opps)
    out["deviations"] = O.deviations(out["drift"], rec)
    if out["deviations"]:
        out["reevaluation_proposal"] = O.propose_reevaluation(con, "LAB_STATUS", out["deviations"], now=asof)
    days = sorted(out["drift"]["coverage_by_decision_day"])
    day = days[len(days) // 2]
    rep1 = O.daily_report(con, day, asof, opps=opps)
    rep2 = O.daily_report(con, day, asof, opps=O.opportunities(con))   # replay from the frozen records again
    out["daily_replay"] = {"day": day, "byte_identical": rep1 == rep2, "lines": rep1.count("\n"), "sha256": store.sha256(rep1)}
    (HERE / "DAILY_SAMPLE.md").write_text(rep1)
    plan_end = json.loads((ROOT / "audits/backtesting/validation/p11_results.json").read_text())["plan"]["end"]
    out["shadow_after_sealed_test"] = O.shadow(con, "BREAKOUT_CLOSE", since=plan_end)
    out["prior_runs_unchanged"] = run_hashes == [tuple(r) for r in con.execute("SELECT run_id, result_hash FROM bt_run_results ORDER BY id")]
    con.close()
out["wall_s"] = round(time.time() - t_start, 1)
(HERE / "p15_outcomes.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
c24 = out["calibration"]["24h"]
print(json.dumps({"opportunities": out["opportunities"], "track_1": out["track_1"], "rate_limited": out["track_rate_limited"],
                  "rerun_new_rows": out["track_2_new_rows"], "overall_24h": c24["overall"], "selection_bias_risk": c24["selection_bias_risk"],
                  "reconciliation": {k: rec[k] for k in ("pairs", "not_observable", "liq_error_median", "verdict")},
                  "warnings": out["drift"]["warnings"], "daily_replay": out["daily_replay"], "shadow": out["shadow_after_sealed_test"],
                  "prior_runs_unchanged": out["prior_runs_unchanged"], "wall_s": out["wall_s"]}, indent=1, default=str))
