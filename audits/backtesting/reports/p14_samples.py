"""Phase 14 evidence: text snapshots of the backtest report, scout section, alert line and CLI help.

Inputs are real: the PAID analysis from the committed inbox captures and a temporary copy of the research corpus
(data/backtest/bt.sqlite, never written). Degraded variants (G31 new token, G34 blocked quotes, a high-status
mismatch) are the same real analysis with one input removed or changed, and are labeled as such.
Run: python audits/backtesting/reports/p14_samples.py"""
import copy, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from memelab import db, pipeline                        # noqa: E402
from memelab.backtest import assess, report as R, store  # noqa: E402
from memelab.bridge import ingest                       # noqa: E402

OUT = Path(__file__).parent / "samples"
OUT.mkdir(exist_ok=True)
PAID = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"
IDS = ["disc01", "s2_01", "deep01a"]
res = [ingest.load_result(ROOT / "data" / "inbox" / f"{i}.result.json") for i in IDS]
bodies = {k: v[0] for k, v in ingest.merged_bodies(res).items()}
t = max(r.observed_at for r in res)
base = pipeline.analyze_token(PAID, bodies, observed_at=t, sol_price=120.8, persist=False)
pol = dict(assess.DEFAULT_POLICY, enabled=True)
index = {}


def write(name, doc):
    assert R.validate(doc) == [], name
    (OUT / f"{name}.json").write_text(json.dumps(doc, indent=1, default=str) + "\n")
    (OUT / f"{name}.md").write_text(R.render_md(doc))
    index[name] = {"label": doc["headline"]["label"], "state": doc["trace"]["assessment_state"], "tier": doc["trace"]["assessment_tier"],
                   "request_key": doc["trace"]["request_key"], "mismatch": doc["headline"]["mismatch"]}


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    shutil.copy(ROOT / "data" / "backtest" / "bt.sqlite", td / "bt.sqlite")
    con = store.connect(td / "bt.sqlite")
    shared = R.shared_context(con)
    write("PAID_real", R.build(assess.attach(copy.deepcopy(base), pol, con=con, now=t + 60), con=con, shared=shared, lab_db=db.DB_PATH))
    write("PAID_judged_today_stale", R.build(assess.attach(copy.deepcopy(base), pol, con=con), con=con, shared=shared, lab_db=db.DB_PATH))
    g31 = copy.deepcopy(base); g31["bundle"]["ohlcv"]["hour1"] = g31["bundle"]["ohlcv"]["hour1"][-5:]
    write("G31_variant_new_token", R.build(assess.attach(g31, pol, con=con, now=t + 60), con=con, shared=shared, lab_db=db.DB_PATH))
    g34 = copy.deepcopy(base)
    for q in g34["bundle"]["quotes"]["SELL"].values():
        q["status"] = "HTTP_429"
    write("G34_variant_quotes_blocked", R.build(assess.attach(g34, pol, con=con, now=t + 60), con=con, shared=shared, lab_db=db.DB_PATH))
    g34b = copy.deepcopy(base); g34b["bundle"]["market"]["price_usd"] = None
    write("G34_variant_price_blocked", R.build(assess.attach(g34b, pol, con=con, now=t + 60), con=con, shared=shared, lab_db=db.DB_PATH))
    mm = copy.deepcopy(base); mm["status"]["status"] = "ENTRY CONDITIONS MET"; mm["modules"].setdefault("depth", {})["no_route"] = True
    write("variant_high_status_no_route", R.build(assess.attach(mm, pol, con=con, now=t + 60), con=con, shared=shared, lab_db=db.DB_PATH))
    (OUT / "coverage.json").write_text(json.dumps(R.coverage(con), indent=1) + "\n")
    con.close()

    # scout section and per-token files, with the lab database redirected to a temp copy (never the tracked one)
    from memelab import cli
    env = {**os.environ, "MEMELAB_BACKTEST": "1", "MEMELAB_BT_DB": str(td / "bt.sqlite")}
    lab_copy = td / "lab.sqlite"
    shutil.copy(db.DB_PATH, lab_copy)
    rd = td / "reports"
    rd.mkdir()
    code = ("import sys\nfrom pathlib import Path\nfrom memelab import db, cli\ndb.DB_PATH = Path(sys.argv[1]); db.DATA_DIR = Path(sys.argv[1]).parent\n"
            "class A: pass\n"
            "a = A(); a.mints = [sys.argv[2]]; a.results = sys.argv[3:6]; a.stage1 = None; a.min_score = 55; a.social = False; "
            "a.social_policy = None; a.social_include_fixtures = False; a.report_dir = sys.argv[6]; cli.cmd_scout(a)")
    p = subprocess.run([sys.executable, "-c", code, str(lab_copy), PAID, *IDS, str(rd)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-2000:]
    scout = next(rd.glob("*_SCOUT.md")).read_text()
    (OUT / "scout_section.md").write_text(scout[scout.index("## Backtest and stress"):])
    (OUT / "scout_section.json").write_text(next(rd.glob("*_SCOUT.backtest.json")).read_text())

    # alert line: a dry-run social alert for PAID with the backtesting policy on (fixture feed, nothing sent)
    from memelab.social import alerts_core as AC, alerts_engine as AE, alerts_transport as AT
    T0 = t + 3600
    it = {"item_id": "ca:solana:" + PAID, "kind": "CONTRACT", "label": f"PAID on solana ({PAID})", "symbol": "PAID", "chain": "solana", "contract": PAID,
          "times": {"last_observed_at": T0 - 3600}, "freshness": {"status": "FRESH", "confidence": "MODERATE"},
          "independence": {"independent_sources": 3, "status": "ok", "repeats": 0},
          "who": [{"display": f"{h} (x)", "source_id": f"x:id:{h}", "trader": tr, "role": "INDEPENDENT_ORIGINAL", "account_kind": "UNKNOWN",
                   "url": f"https://example.invalid/x/{h}"} for h, tr in (("a", "ta"), ("b", "tb"), ("c", None))],
          "links": [], "chronology": [], "liquidity": {"status": "REPORTED", "facts": []}, "digest": {"changes": []}, "activity": {"window_mentions": 4},
          "is_fixture": True, "provenance": {"narrative_run_id": 0, "cluster_key": "sample", "claims": [], "chronology_runs": [], "market_fact_ids": []}}
    fd = {"schema": "memelab.social.feed/1", "as_of": T0, "feed_sha256": "sample", "fixture": True, "availability": {"status": "AVAILABLE"},
          "data_freshness": {"status": "FRESH", "snapshot_run_id": 1, "snapshot_window": "sample"}, "items": [it]}
    os.environ["MEMELAB_BACKTEST"] = "1"
    store.BT_DB_PATH = td / "bt.sqlite"
    ac = AE.connect(td / "alerts.sqlite")
    AE.run(ac, feed=fd, policy=AC.make_policy({}), mode="dry_run", now=T0, transports=[AT.FileSink(td / "outbox")])
    (OUT / "alert_dry_run.txt").write_text("\n".join(f.read_text() for f in sorted((td / "outbox" / "preview").glob("*.txt"))))

help_ = subprocess.run([sys.executable, "-m", "memelab", "backtest", "--help"], cwd=ROOT, capture_output=True, text=True).stdout
help_ += "\n" + subprocess.run([sys.executable, "-m", "memelab", "backtest", "stress", "--help"], cwd=ROOT, capture_output=True, text=True).stdout
(OUT / "cli_help.txt").write_text(help_)
(OUT / "INDEX.json").write_text(json.dumps(index, indent=1) + "\n")
print(json.dumps(index, indent=1))
