"""Compare every engine's result to the hand oracle. Exit 0 only if every expectation below holds."""
import json, sys
o = json.load(open("oracle_expected.json")); p = json.load(open("result_proto.json"))
b = json.load(open("result_backtestingpy.json")); v = json.load(open("result_vectorbt.json"))
checks = []
def ck(name, cond, info=""):
    checks.append((name, bool(cond))); print(("PASS " if cond else "FAIL ") + name + (f"  [{info}]" if info else ""))
close = lambda a, c, tol=1e-9: abs(a - c) <= tol * max(1, abs(c))
# proto vs oracle, every case
for k in ("A_noimpact_1000", "A_cpmm_1000", "A_cpmm_50000", "B_noimpact_1000"):
    t = p[k][0]; e = o[k]
    ck(f"proto {k} proceeds == oracle", close(t["proceeds"], e["proceeds"]), f"{t['proceeds']:.6f} vs {e['proceeds']:.6f}")
ck("proto A entry bar/price == oracle", p["A_noimpact_1000"][0]["entry_bar"] == o["A_entry"]["bar"] and p["A_noimpact_1000"][0]["entry_px"] == o["A_entry"]["price"])
ck("proto A exit is gap fill at open", p["A_noimpact_1000"][0]["exit_bar"] == 35 and p["A_noimpact_1000"][0]["exit_px"] == 0.95 and p["A_noimpact_1000"][0]["reason"] == "STOP_GAP_FILL_AT_OPEN")
ck("proto B enters at first bar after first_seen_at (bar 8)", p["B_noimpact_1000"][0]["entry_bar"] == 8)
ck("published-time join would enter 2 bars early (leak detected)", p["B_naive_published_1000"][0]["entry_bar"] == 6)
r1, r50 = p["A_cpmm_1000"][0]["ret"], p["A_cpmm_50000"][0]["ret"]
ck("G10: size makes fills non-linearly worse (50k ret << 1k ret)", r50 < r1 - 0.3, f"{r1:.4f} vs {r50:.4f}")
ck("CPMM avg entry above mid for both sizes", o["A_cpmm_1000"]["avg_entry_px"] > 1.11 and o["A_cpmm_50000"]["avg_entry_px"] > 1.11)
# backtesting.py: same bars and prices (units are integers by default, so P&L reconciles by formula, checked below)
bt = b["A_noimpact_1000"][0]
ck("backtesting.py A entry/exit bars and prices == oracle", (bt["entry_bar"], bt["entry_px"], bt["exit_bar"], bt["exit_px"]) == (21, 1.11, 35, 0.95))
units = bt["size"]; recon = units * 0.95 * (1 - 0.0025) - units * 1.11 * (1 + 0.0025)
ck("backtesting.py A P&L reconciles: integer units, fee on notional both sides", close(bt["pnl"], recon, 1e-9), f"{bt['pnl']:.6f} vs {recon:.6f}")
bb = b["B_noimpact_1000"][0]
ck("backtesting.py B entry bar 8 / exit bar 14", (bb["entry_bar"], bb["exit_bar"]) == (8, 14))
# vectorbt
vd, va = v["default_close_fill"][0], v["adjusted_next_open"][0]
ck("vectorbt DEFAULT fills on the signal bar close (optimistic, differs from oracle)", vd["entry_bar"] == 20 and vd["entry_px"] == 1.10)
ck("vectorbt ADJUSTED (shift + price=open) matches oracle bars/prices", (va["entry_bar"], va["entry_px"], va["exit_bar"], va["exit_px"]) == (21, 1.11, 35, 0.95))
size = 1000 / (1.11 * (1 + 0.0025)); recon_v = size * 0.95 * (1 - 0.0025) - 1000
ck("vectorbt adjusted P&L reconciles: fee added to entry price", close(va["pnl"], recon_v, 1e-9), f"{va['pnl']:.6f} vs {recon_v:.6f}")
n_fail = sum(1 for _, c in checks if not c)
print(f"\n{len(checks) - n_fail}/{len(checks)} checks pass")
sys.exit(1 if n_fail else 0)
