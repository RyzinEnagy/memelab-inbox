"""Phase 06: pick real development traces of the four hand-check shapes and dump the candles a hand check needs.

Rule (fixed before looking): among LABELED development records, the earliest decision of each shape:
  false_breakout        T1 INVALIDATION_FIRST with a path high of at least 1.10 x P0 before the touching candle
  delayed_confirmation  T1b NEITHER and T1 TARGET_FIRST of the same decision (first touch after the 6 h horizon)
  rug_halt              T2 DRAWDOWN_50 with HALT_ON_REFERENCE_POOL, else T2 TRADING_HALT
  ambiguous_bar         T1 or T1b AMBIGUOUS_BAR
Development only; the holdout is never opened. Output: evidence/real_traces.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_labels as B  # noqa: E402
import make_labels as M  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402


def main():
    u, cd, _ = M.universe()
    recs, _ = L.build(u)
    dev = [r for r in recs if r["split"] == "DEVELOPMENT" and r["state"] == "LABELED"]
    by = {(r["decision_key"], r["target"]): r for r in dev}
    dev.sort(key=lambda r: (r["decision"]["decision_time"], r["decision_key"], r["target"]))
    pick = {}
    for r in dev:
        k, t = r["decision_key"], r["target"]
        d, rd = r["decision"], r["read"]
        path = C.path_candles(list(rd.candles), d["decision_time"], C.TARGETS[t]["horizon_s"])
        if "false_breakout" not in pick and t == L.T1 and r["label_class"] == "INVALIDATION_FIRST":
            before = [c for c in path if c[0] < r["first_touch_start"]]
            if any(c[2] >= 1.10 * r["p0"] for c in before):
                pick["false_breakout"] = (k, [L.T1, L.T1B, L.T2])
        if "delayed_confirmation" not in pick and t == L.T1 and r["label_class"] == "TARGET_FIRST":
            r6 = by.get((k, L.T1B))
            if r6 is not None and r6["label_class"] == "NEITHER":
                pick["delayed_confirmation"] = (k, [L.T1, L.T1B, L.T2])
        if "rug_halt" not in pick and t == L.T2 and (r["label_class"] == "TRADING_HALT" or
                                                     (r["label_class"] == "DRAWDOWN_50" and "HALT_ON_REFERENCE_POOL" in r["flags"])):
            pick["rug_halt"] = (k, [L.T1, L.T1B, L.T2])
        if "ambiguous_bar" not in pick and t in (L.T1, L.T1B) and r["label_class"] == "AMBIGUOUS_BAR":
            pick["ambiguous_bar"] = (k, [L.T1, L.T1B, L.T2])
    out = {}
    for shape, (k, ts) in pick.items():
        r0 = next(r for r in recs if r["decision_key"] == k)
        d, rd = r0["decision"], r0["read"]
        te = L.t_entry(d["decision_time"])
        ref = C.reference_candle(list(rd.candles), d["decision_time"])
        s, e = L.halt_span(d["decision_time"])
        win = [list(c) for c in rd.candles if ref[0] - 900 <= c[0] < te + 86400]
        labels = {}
        for t in ts:
            x = next(r for r in recs if r["decision_key"] == k and r["target"] == t)
            labels[t] = {"split": x["split"], "state": x["state"], "class": x["label_class"], "label": x["label"],
                         "first_touch_start": B.iso(x.get("first_touch_start")), "flags": x.get("flags"), "detail": x.get("detail")}
        out[shape] = {"mint": d["mint"], "pool": rd.pool, "route": d["route"], "decision_time": B.iso(d["decision_time"]),
                      "t_entry": B.iso(te), "read_url": rd.url, "read_retrieved_at": B.iso(rd.retrieved_at), "read_boundary": B.iso(rd.boundary),
                      "read_cover_from": B.iso(rd.cover_from), "body_sha256": rd.body_sha256,
                      "reference_candle": [B.iso(ref[0])] + list(ref[1:]), "p0": ref[4],
                      "barriers": {"upper_1.25": ref[4] * 1.25, "lower_0.85": ref[4] * 0.85, "drawdown_0.5": ref[4] * 0.5},
                      "halt_span": [B.iso(s), B.iso(e)],
                      "candles_in_halt_span": sum(1 for c in rd.candles if L.in_span(c, s, e)),
                      "candles_ref_minus_15min_to_entry_plus_24h": [[B.iso(c[0])] + c[1:] for c in win], "labels": labels}
    B.jsave(B.EVID / "real_traces.json", out)
    print(json.dumps({k: [v["mint"][:8], v["decision_time"], {t[-3:]: v["labels"][t]["class"] for t in v["labels"]}] for k, v in out.items()}))


if __name__ == "__main__":
    main()
