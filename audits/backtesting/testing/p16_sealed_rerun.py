"""Phase 16: repeat the Phase 11 sealed benchmark on a COPY of the research corpus and check the data cutoff.
- recomputes the dataset hash at the pre-registered cutoff T1 and compares it with p11_results.json;
- recomputes the hash with no cutoff (shows whether data after T1 exists and is excluded);
- reruns validate() for BREAKOUT_CLOSE and LAB_STATUS with the pre-registered grids and compares the frozen choice,
  sealed-test metrics and the sealed-test ledger hash with the stored results;
- counts bars whose availability is after T1 and checks the sealed-test run never read one (until=T1).
Usage: python3 audits/backtesting/testing/p16_sealed_rerun.py <copy of bt.sqlite>"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from memelab.backtest import quality, runner, store, validation as V  # noqa: E402
from memelab.backtest.engine import EngineConfig  # noqa: E402

db = Path(sys.argv[1])
assert db.resolve() != (ROOT / "data" / "backtest" / "bt.sqlite").resolve(), "use a copy"
stored = json.loads((ROOT / "audits/backtesting/validation/p11_results.json").read_text())
T0, T1, EMB = 1791331200.0, 1792771200.0, 2 * 86400.0
con = store.connect(db)
tokens, _ = runner.build_tokens(con)
sol = runner.sol_usd_series(con)
mints = sorted(t.mint for t in tokens) + [runner.SOL]
out = {"stored_dataset_hash": stored["dataset_hash"], "dataset_hash_at_T1": quality.dataset_hash(con, mints, cutoff=T1),
       "dataset_hash_no_cutoff": quality.dataset_hash(con, mints), "tokens": len(tokens), "stored_tokens": stored["tokens"],
       "bars_available_after_T1": con.execute("SELECT COUNT(*) FROM bt_market_bars WHERE available_at>?", (T1,)).fetchone()[0],
       "max_bar_available_at": con.execute("SELECT MAX(available_at) FROM bt_market_bars").fetchone()[0]}
out["cutoff_hash_matches"] = out["dataset_hash_at_T1"] == out["stored_dataset_hash"]
plan = V.SplitPlan.make(T0, T1, (0.5, 0.25, 0.25), embargo_s=EMB)
grids = {"BREAKOUT_CLOSE": [{"lookback": lb, "vol_mult": vm} for lb in (12, 24) for vm in (1.0, 1.5)],
         "LAB_STATUS": [{"min_score": 55}, {"min_score": 65}, {"min_score": 55, "statuses": ["ENTRY CONDITIONS MET", "NEAR ENTRY"]}]}
out["strategies"] = {}
for sid, grid in grids.items():
    t0 = time.time()
    r = V.validate(sid, grid, tokens, EngineConfig(), plan, min_n_tune=8, min_n_test=30, sol_usd=sol)
    rt = V.run_window(V.registry.make(sid, **r.chosen), tokens, EngineConfig(), plan, "test", sol)
    s = stored["strategies"][sid]
    last_read = max([f["fill_time"] for f in rt["fills"] if f.get("fill_time")] + [0.0])
    out["strategies"][sid] = {"chosen": r.chosen, "stored_chosen": s["chosen"], "frozen_sha": r.frozen_sha, "stored_frozen_sha": s["frozen_sha"],
                              "verdict": r.verdict, "stored_verdict": s["verdict"], "test_n": (r.test or {}).get("n"), "stored_test_n": (s.get("test") or {}).get("n"),
                              "test_mean_ret": (r.test or {}).get("mean_ret"), "stored_test_mean_ret": (s.get("test") or {}).get("mean_ret"),
                              "test_ledger_hash": rt["ledger_hash"], "stored_test_ledger_hash": s.get("test_ledger_hash"),
                              "latest_fill_time": last_read, "latest_fill_le_T1": last_read <= T1, "wall_s": round(time.time() - t0, 1)}
    x = out["strategies"][sid]
    x["reproduced"] = (x["chosen"] == x["stored_chosen"] and x["frozen_sha"] == x["stored_frozen_sha"] and x["verdict"] == x["stored_verdict"]
                       and x["test_n"] == x["stored_test_n"] and x["test_ledger_hash"] == x["stored_test_ledger_hash"])
# the seal is an in-memory object per validate() call: a second validate() call reads the sealed window again without objection
seal_a, seal_b = V.TestSeal(), V.TestSeal()
seal_a.freeze({"s": 1}); seal_a.open({"s": 1})
seal_b.freeze({"s": 1}); seal_b.open({"s": 1})
out["seal_is_per_object_only"] = True
print(json.dumps(out, indent=1, default=str))
