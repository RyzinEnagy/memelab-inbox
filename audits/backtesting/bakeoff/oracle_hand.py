"""Independent hand-calculation oracle for the bake-off. Shares no code with any engine.

Every expected value below is derived by explicit arithmetic on numbers read off the dataset
definition (dataset.py), written out step by step so a reviewer can redo it on paper.
"""
import json

d = json.load(open("dataset.json"))
B = {i: b for i, b in enumerate(d["bars"])}
fee = 0.0025
Q = 60_000.0
net_fee = 0.01

out = {}

# ---- Strategy A: breakout. Prior 20-bar high before bar 20 = max over bars 0..19 of high.
# Highs for i<20: odd bars high = o + 0.005 = 1.00 + 0.002i + 0.01 + 0.005; even bars high = c + 0.005 = 1.00 + 0.002i + 0.005 + 0.005
prior_high = max(1.015 + 0.002 * i if i % 2 else 1.010 + 0.002 * i for i in range(20))   # = 1.015 + 0.038 = 1.053 (bar 19)
assert abs(prior_high - 1.053) < 1e-12
assert B[20]["c"] == 1.10 and B[20]["c"] > prior_high          # signal on bar 20 close
entry_bar, entry_px = 21, 1.11                                    # next bar open
stop = round(entry_px * 0.90, 10)                                 # 0.999
exit_bar, exit_px = 35, 0.95                                      # bar 35 opens at 0.95 < stop: gap fill at the open
assert B[35]["o"] == 0.95 and all(B[i]["l"] > stop for i in range(21, 35))
out["A_entry"] = {"bar": entry_bar, "t": d["bars"][21]["t"], "price": entry_px}
out["A_exit"] = {"bar": exit_bar, "t": d["bars"][35]["t"], "price": exit_px, "reason": "STOP_GAP_FILL_AT_OPEN"}

# zero-impact, 0.25% fee each side, notional 1000
units = 1000 * (1 - fee) / 1.11                 # 997.5 / 1.11 = 898.648648648...
proceeds = units * 0.95 * (1 - fee)             # 851.581925675...
out["A_noimpact_1000"] = {"units": units, "proceeds": proceeds, "pnl": proceeds - 1000, "ret": proceeds / 1000 - 1}

# CPMM: quote reserve 60,000 at the bar open, base reserve = 60,000 / open
for size in (1000.0, 50000.0):
    b_in = Q / 1.11
    tok = b_in * (size * (1 - fee)) / (Q + size * (1 - fee))
    b_out = Q / 0.95
    q_out = Q * (tok * (1 - fee)) / (b_out + tok * (1 - fee))
    proceeds = q_out - net_fee
    cost = size + net_fee
    out[f"A_cpmm_{int(size)}"] = {"tokens": tok, "avg_entry_px": size / tok, "proceeds": proceeds, "pnl": proceeds - cost, "ret": proceeds / cost - 1}

# ---- Strategy B: event. first_seen_at = T0 + 7h + 600s -> decision then; earliest execution = next bar open = bar 8.
T0 = d["bars"][0]["t"]
assert d["event"]["first_seen_at"] == T0 + 7 * 3600 + 600
out["B_entry"] = {"bar": 8, "t": T0 + 8 * 3600, "price": 1.00 + 0.016 - 0.01}       # 1.006
out["B_exit"] = {"bar": 14, "t": T0 + 14 * 3600, "price": 1.00 + 0.028 - 0.01}      # 1.018
out["B_naive_published_entry"] = {"bar": 6, "price": 1.00 + 0.012 - 0.01}          # what a published-time join would do (wrong)
u = 1000 * (1 - fee) / 1.006
p = u * 1.018 * (1 - fee)
out["B_noimpact_1000"] = {"units": u, "proceeds": p, "pnl": p - 1000, "ret": p / 1000 - 1}

json.dump(out, open("oracle_expected.json", "w"), indent=1, sort_keys=True)
for k, v in out.items():
    print(k, {kk: (round(vv, 6) if isinstance(vv, float) else vv) for kk, vv in v.items()})
