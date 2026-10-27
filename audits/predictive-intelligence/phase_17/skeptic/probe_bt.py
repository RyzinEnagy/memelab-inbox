import sys, sqlite3, hashlib, tempfile, json, os
from pathlib import Path
REPO = Path(sys.argv[1]); sys.path.insert(0, str(REPO))
from memelab.predictive import bt_adapter as BT, contract as C
tmp = Path(tempfile.mkdtemp(prefix="sk17bt_")); p = tmp / "bt.sqlite"
con = sqlite3.connect(p)
con.execute("CREATE TABLE bt_assessments (id INTEGER PRIMARY KEY, request_key TEXT, chain TEXT, mint TEXT, snapshot_hash TEXT, engine_version TEXT, as_of REAL, stage TEXT, tier TEXT, state TEXT, result_json TEXT, result_hash TEXT, created_at REAL)")
M = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"
for i, (asof, state) in enumerate([(100.0, "RISK_FATAL_FLAW"), (300.0, "COMPLETE")]):
    rec = {"request_key": f"k{i}", "chain": "solana", "mint": M, "as_of": asof, "state": state, "tier": "SCENARIO_ONLY", "stress": {"decision": "RESEARCHABLE"}}
    con.execute("INSERT INTO bt_assessments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (None, f"k{i}", "solana", M, "s", "e", asof, "FAST", "SCENARIO_ONLY", state, json.dumps(rec), "h", asof))
con.commit(); con.close()
h0 = hashlib.sha256(p.read_bytes()).hexdigest(); ls0 = sorted(os.listdir(tmp))
r200 = BT.from_table(p, chain="solana", mint=M, decision_time=200.0, installed_status="BACKTEST_NOT_AVAILABLE")
r400 = BT.from_table(p, chain="solana", mint=M, decision_time=400.0, installed_status="BACKTEST_NOT_AVAILABLE")
rlow = BT.from_table(p, chain="solana", mint=M.lower(), decision_time=400.0, installed_status="BACKTEST_NOT_AVAILABLE")
nochain = BT.check_record({"mint": M, "state": "COMPLETE", "as_of": 1.0}, chain="bsc", mint=M, decision_time=2.0)
# write attempt through the adapter's own connection
c2 = BT.connect_ro(p)
try:
    c2.execute("DELETE FROM bt_assessments"); wrote = "WROTE"
except sqlite3.Error as e:
    wrote = f"refused: {type(e).__name__}: {e}"
c2.close()
h1 = hashlib.sha256(p.read_bytes()).hexdigest()
# derived status: fake an importable memelab.backtest
fake = tmp / "fakepkg"; (fake / "memelab" / "backtest").mkdir(parents=True)
st_before = C.backtest_status()
import importlib.util, memelab
memelab.__path__.append(str(fake / "memelab")); (fake / "memelab" / "backtest" / "__init__.py").write_text("")
importlib.invalidate_caches()
st_after = C.backtest_status()
print(json.dumps({"as_of_200_result": r200["result"], "as_of_200_veto": r200["veto"], "as_of_400_result": r400["result"], "as_of_400_state": (r400.get("assessment") or {}).get("state"),
  "lowercase_mint": rlow["result"], "missing_chain_record_on_bsc_refusals": nochain, "write_through_ro": wrote, "db_unchanged": h0 == h1,
  "files_unchanged": ls0 == sorted(x for x in os.listdir(tmp) if x != "fakepkg"), "status_before": st_before, "status_with_fake_memelab_backtest": st_after}, indent=1))
