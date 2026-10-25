"""Skeptic 09 counterexample CX-S09: the depth-only size cap reads post-decision, stale and other-pool quotes.
onchain.decision_support(forecast, flags, quotes, max_loss) and size_cap_usd(quotes, max_loss) take no decision time and no pool:
they trust the caller to pass `depth_adapter.visible_at(...)` rows of the decision pool. The natural wrong call passes
`depth_adapter.observations(con, chain, mint)` (every row of the mint) straight in. Nothing refuses it.
Step 1 (backtesting code): python p09_cx_sizecap.py build BTCODE WORKDIR   (collector schema via the collector's own store)
Step 2 (predictive clone):  python p09_cx_sizecap.py run CLONE WORKDIR"""
import json, os, sys
mode, code, work = sys.argv[1:4]
sys.path.insert(0, code)
db = os.path.join(work, "bt_cx_sizecap.sqlite")
MINT = "CxMint11111111111111111111111111111111111pump"
A, Bp = "PoolA111111111111111111111111111111111111111", "PoolB111111111111111111111111111111111111111"
T = 1793100000.0                       # the predictive decision (export commit) time
if mode == "build":
    from memelab.backtest import store, depth
    if os.path.exists(db): os.remove(db)
    con = store.connect(db)
    # an earlier decision of the mint 20 h before T (its rows are legitimately visible at T) and the decision at T
    d0 = dict(chain="solana", mint=MINT, pool_address=A, pool_source="EXPORT_PRIMARY_POOL", export_commit="c0", export_time=T - 72000, export_path="data/state/latest.json", created_at=T - 72100, row_sha256="r0", status="WATCH")
    d1 = dict(d0, export_commit="c1", export_time=T, created_at=T - 100, row_sha256="r1")
    ids = [depth.record_decision(con, d, recorded_at=T + 4000)[0] for d in (d0, d1)]
    def q(did, dec, pool, t, size, ratio, state="OK"):
        depth._snapshot(con, run_id=f"r{int(t)}", dec=dict(dec, id=did, pool_address=pool), kind="QUOTE", provider="jupiter", url="u",
                        resp={"t": t, "status": 200, "sha": "s"}, state=state, size_usd=size, out_usd=size * ratio if state == "OK" else None, price_impact=0.01)
    q(ids[0], d0, Bp, T - 70000, 2000.0, 0.99)     # 19.4 h stale, another pool (P02)
    q(ids[0], d0, A, T - 3000, 2000.0, 0.60)       # the newest visible read of the decision pool at this size: 40% loss
    q(ids[0], d0, A, T - 3000, 100.0, 0.97)
    q(ids[1], d1, A, T + 1500, 2000.0, 0.98)       # the collector's first read for the decision itself, 25 min after T (CX-09)
    con.commit(); con.execute("PRAGMA wal_checkpoint(TRUNCATE)"); con.execute("PRAGMA journal_mode=DELETE"); con.close()
    print("built", db)
else:
    from memelab.predictive import depth_adapter as DA, onchain as O
    con = DA.connect_ro(db)
    obs = DA.observations(con, chain="solana", mint=MINT)
    doc = {"kind": "ABSTAIN", "probability": None}
    wrong = O.decision_support(doc, [], obs, max_loss=0.05)["size_cap"]
    right_rows = [o for o in DA.visible_at(obs, T) if o["pool_address"] == A]
    newest = {}
    for o in right_rows:
        if o["kind"] == "QUOTE" and o["state"] == "OK":
            newest[o["size_usd"]] = o
    as_of = O.size_cap_usd(list(newest.values()), max_loss=0.05)
    ctx = DA.exit_context(obs, T=T, pool_address=A, size_usd=2000.0)
    try:
        DA.assert_visible(obs, T); refused = False
    except DA.DepthLeakageError as e:
        refused = str(e)
    print(json.dumps({"size_cap_from_all_rows_of_the_mint (accepted, no error)": wrong,
                      "size_cap_from_newest_visible_reads_of_the_decision_pool": as_of,
                      "exit_context_2000_on_pool_A_at_T": ctx,
                      "assert_visible_on_the_same_rows": refused}, indent=1))
