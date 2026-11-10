"""Phase 17: offline historical import from the committed real GeckoTerminal responses (tests/fixtures/backtest/real/)
into a research database, plus a flat SOL/USD reference series and the lab's real universe record for that token.
Usage: python audits/backtesting/release/p17_fixture_import.py <bt.sqlite path>"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from memelab.backtest import store                     # noqa: E402
from memelab.backtest.sources import corpus, gecko     # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "backtest" / "real"
MAN = json.loads((FIX / "MANIFEST.json").read_text())
MINT, POOL = MAN["mint"], "7AvDaHLbHW6qaMGuHQGpebbbGaV7fRTdFq5T5Vd4vdoH"


def replay(url, timeout=30.0):
    for f, m in MAN["files"].items():
        if m["url"] == url:
            return 200, (FIX / f).read_bytes()
    return 404, b""


db = Path(sys.argv[1])
store.RAW_DIR = db.parent / "raw"
con = store.connect(db)
b = gecko.Budget(max_calls=10, min_spacing_s=0.0)
p = gecko.fetch_pools(con, MINT, b, replay, observed_at=MAN["files"]["gt_pools_3GVSN8.json"]["observed_at"])
o = gecko.fetch_ohlcv(con, MINT, POOL, b, replay, observed_at=MAN["files"]["gt_ohlcv_3GVSN8.json"]["observed_at"])
for r in con.execute("SELECT start FROM bt_market_bars WHERE mint=? ORDER BY start", (MINT,)).fetchall():
    store.record_bar(con, chain="solana", mint=corpus.SOL_MINT, pool_address=corpus.SOL_USDC_POOL, tf=3600, start=r["start"], o=150, h=150, l=150, c=150,
                     volume_usd=1e6, observed_at=MAN["files"]["gt_ohlcv_3GVSN8.json"]["observed_at"], provider="test")
t_lab = 1791547052.132     # the lab's real record time for this token (2026-10-09 11:57Z)
store.record_universe_member(con, universe_id="lab_state_history", chain="solana", mint=MINT, basis="THESIS", entered_at=t_lab,
                             status_at_entry="ENTRY CONDITIONS MET", score_at_entry=70, fatal_flags=[], snapshot={"liquidity": 150000.0, "price": 0.0114},
                             committed_by=t_lab + 900)
con.commit()
n = con.execute("SELECT COUNT(*) FROM bt_market_bars WHERE mint=?", (MINT,)).fetchone()[0]
print(json.dumps({"mint": MINT, "pools": len(p["pools"]), "bars": n, "raw_files": sorted(MAN["files"])}))
