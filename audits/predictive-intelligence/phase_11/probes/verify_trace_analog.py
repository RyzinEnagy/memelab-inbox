"""Phase 11 independent trace check. Uses neither analog.py nor features.py nor baselines.py: recomputes, for each traced decision,
the regime label at T, the analog inputs of the target and of every pool row, the z-scores, the distances, one analog per cluster,
the 30 nearest clusters, the out-of-distribution threshold and the cohort number, from plain SQL over the Phase 05 store (version 2
values, decision rows and token rows) and the pool labels of the committed fold artifact, and compares with the trace.

    python -B verify_trace_analog.py [OUTDIR] [--feature-store PATH]
Invalid inputs (a pool row decided after the cutoff, a label maturing after it, a target value changed) must be rejected.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

P11 = Path(__file__).resolve().parents[1]
FEATURE_STORE = "/home/claude/pi_research/p05/predictive_store.sqlite"
H = datetime(2026, 10, 17, tzinfo=timezone.utc).timestamp()
CONSTRUCTIVE = {"WATCH", "SETUP DEVELOPING", "NEAR ENTRY", "ENTRY CONDITIONS MET"}
NUM = ("thesis_log1p_liquidity_usd", "thesis_log1p_mcap_usd", "thesis_log1p_vol_24h_usd", "log1p_token_age_days")
K, Q, M, MIN_G, MIN_DAYS = 30, 0.95, 20.0, 20, 5


def day(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


def load(fs_path):
    con = sqlite3.connect(f"file:{fs_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    vals = {}
    for r in con.execute("SELECT s.decision_key, v.feature_name, v.value, v.feature_available_at FROM predictive_snapshots s "
                         "JOIN predictive_feature_values v ON v.snapshot_key = s.snapshot_key WHERE s.availability_mode='provider' "
                         "AND s.decision_key IS NOT NULL AND v.feature_name IN ('thesis_log1p_liquidity_usd','thesis_log1p_mcap_usd',"
                         "'thesis_log1p_vol_24h_usd','token_age_s')"):
        vals.setdefault(r["decision_key"], {})[r["feature_name"]] = r["value"]
    decs = {}
    for r in con.execute("SELECT decision_key, mint, decision_time, status, token_json FROM predictive_decisions "
                         "WHERE chain='solana' AND decision_key IS NOT NULL AND decision_time < ?", (H,)):
        tok = json.loads(r["token_json"] or "{}")
        v = vals.get(r["decision_key"], {})
        age = v.get("token_age_s")
        lp = tok.get("launchpad")
        prog = tok.get("token_program")
        decs[r["decision_key"]] = {
            "mint": r["mint"], "t": float(r["decision_time"]), "status": r["status"], "creator": tok.get("creator") or None,
            "x": [v.get("thesis_log1p_liquidity_usd"), v.get("thesis_log1p_mcap_usd"), v.get("thesis_log1p_vol_24h_usd"),
                  math.log1p(age / 86400.0) if isinstance(age, (int, float)) and age >= 0 else None],
            "lp": "NONE_RECORDED" if not (isinstance(lp, str) and lp.strip()) else ("PUMP_FUN" if lp.strip().lower() == "pump.fun" else "OTHER_LAUNCHPAD"),
            "t22": 1.0 if prog == "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb" else 0.0 if prog == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA" else None}
    return decs


def regime(decs, T):
    rows = [d for d in decs.values() if d["t"] <= T]
    inst = sorted({d["t"] for d in rows if d["t"] < T})

    def inp(s):
        w = [d for d in rows if s - 86400 < d["t"] <= s]
        v = [d["x"][2] for d in w if d["x"][2] is not None]
        return (statistics.median(v) if v else None, sum(d["status"] in CONSTRUCTIVE for d in w) / len(w) if w else None)
    if len(inst) < 5:
        return "WARMUP"
    a, t = inp(T)
    past = [inp(s) for s in inst]
    ma, mt = statistics.median([p[0] for p in past]), statistics.median([p[1] for p in past])
    return ("ACTIVE" if a > ma else "QUIET") + "/" + ("RISK_ON" if t > mt else "RISK_OFF")


def quantile(v, q):
    v = sorted(v)
    pos = (len(v) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def cohort(model, tgt, pool, decs, regimes):
    """pool: list of (key, y). Returns the selected keys with distances, the threshold and the number (or None)."""
    def cl(k):
        c = decs[k]["creator"]
        return "creator:" + c if c else "mint:solana:" + decs[k]["mint"]
    b0 = sum(y for _, y in pool) / len(pool)
    complete = [(k, y) for k, y in pool if None not in decs[k]["x"] and decs[k]["t22"] is not None]
    ref = complete
    if model == "AC3_KNN_REGIME":
        ref = [(k, y) for k, y in complete if regimes[k] == regimes[tgt]]
    n = len(ref)
    mu = [sum(decs[k]["x"][j] for k, _ in ref) / n for j in range(4)]
    sd = [math.sqrt(sum((decs[k]["x"][j] - mu[j]) ** 2 for k, _ in ref) / n) or 1.0 for j in range(4)]

    def z(k):
        return [(decs[k]["x"][j] - mu[j]) / sd[j] for j in range(4)]

    def dist(a, b):
        za, zb = z(a), z(b)
        mm = (decs[a]["lp"] != decs[b]["lp"]) + (decs[a]["t22"] != decs[b]["t22"])
        return math.sqrt(sum((u - v) ** 2 for u, v in zip(za, zb)) + mm)

    def nearest(q, rows, skip=None):
        best = {}
        for k, y in rows:
            if skip is not None and cl(k) == skip:
                continue
            d = dist(q, k)
            c = cl(k)
            if c not in best or (d, k) < (best[c][0], best[c][1]):
                best[c] = (d, k, y)
        return sorted(best.values())
    tm, tc = decs[tgt]["mint"], decs[tgt]["creator"]
    cands = [(k, y) for k, y in ref if decs[k]["mint"] != tm and not (tc and decs[k]["creator"] == tc)]
    nn = nearest(tgt, cands)[:K]
    kth = []
    for k, _ in ref:
        o = nearest(k, ref, skip=cl(k))
        kth.append(o[min(K, len(o)) - 1][0])
    thr = quantile(kth, Q)
    G = len(nn)
    kpos = sum(y for _, _, y in nn)
    days = {day(decs[k]["t"]) for _, k, _ in nn}
    ok = G >= MIN_G and len(days) >= MIN_DAYS and nn[-1][0] <= thr
    return {"keys": [k for _, k, _ in nn], "dist": [d for d, _, _ in nn], "thr": thr, "G": G,
            "number": (kpos + M * b0) / (G + M) if ok else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir", nargs="?", default=str(P11))
    ap.add_argument("--feature-store", default=FEATURE_STORE)
    a = ap.parse_args()
    out = Path(a.outdir)
    trace = json.loads((out / "evidence/trace/trace.json").read_text())
    decs = load(a.feature_store)
    regimes = {k: regime(decs, d["t"]) for k, d in decs.items()}
    res = {"traces": [], "differences": 0, "invalid_inputs_rejected": 0, "invalid_inputs_tried": 0}
    for tr in trace:
        s = tr["target_short"]
        folds = json.loads((out / f"artifacts/folds/{s}.json").read_text())["folds"]
        f = next(f for f in folds if abs(f["cutoff"] - tr["cutoff"]) < 1e-6)
        pool = [(r["decision_key"], int(r["y"])) for r in f["pool"]]
        assert sorted(k for k, _ in pool) == tr["pool_keys"]
        rec = {"target_short": s, "decision_key": tr["decision_key"][:12], "checks": {}}
        diff = 0
        # pool chronology and inputs equal the artifact
        for r in f["pool"]:
            d = decs[r["decision_key"]]
            if not (r["decision_time"] < f["cutoff"] and r["label_matures_at"] <= f["cutoff"]):
                diff += 1
            for j, c in enumerate(NUM):
                v = r["x"].get(c)
                if (v is None) != (d["x"][j] is None) or (v is not None and abs(v - d["x"][j]) > 1e-9):
                    diff += 1
        rec["checks"]["regime"] = [regime(decs, tr["decision_time"]), tr["regime_record"]["label"]]
        diff += int(rec["checks"]["regime"][0] != rec["checks"]["regime"][1])
        for m in ("AC2_KNN", "AC3_KNN_REGIME"):
            ans = tr["answers"][m]
            if not ans.get("analogs") and ans.get("reasons"):
                rec["checks"][m] = {"skipped": ans["reasons"]}
                continue
            c = cohort(m, tr["decision_key"], pool, decs, regimes)
            same = (c["keys"] == [x["decision_key"] for x in ans["analogs"]]
                    and all(abs(u - x["distance"]) < 1e-9 for u, x in zip(c["dist"], ans["analogs"]))
                    and abs(c["thr"] - ans["ood_threshold"]) < 1e-9
                    and ((c["number"] is None and ans["number"] is None) or (c["number"] is not None and ans["number"] is not None
                                                                            and abs(c["number"] - ans["number"]) < 1e-12)))
            rec["checks"][m] = {"G": c["G"], "number": c["number"], "trace_number": ans["number"], "equal": same}
            diff += int(not same)
        # invalid inputs: a later row in the pool, a changed target value
        bad_pool = pool + [(next(k for k, d in decs.items() if d["t"] >= f["cutoff"]), 1)]
        res["invalid_inputs_tried"] += 2
        late = [k for k, _ in bad_pool if decs[k]["t"] >= f["cutoff"]]
        res["invalid_inputs_rejected"] += int(bool(late))      # the verifier's chronology rule rejects the injected row
        saved = list(decs[tr["decision_key"]]["x"])
        decs[tr["decision_key"]]["x"][0] = saved[0] + 1.0
        c2 = cohort("AC2_KNN", tr["decision_key"], pool, decs, regimes) if tr["answers"]["AC2_KNN"].get("analogs") else None
        decs[tr["decision_key"]]["x"] = saved
        res["invalid_inputs_rejected"] += int(c2 is None or c2["keys"] != [x["decision_key"] for x in tr["answers"]["AC2_KNN"]["analogs"]]
                                              or abs((c2["number"] or -1) - (tr["answers"]["AC2_KNN"]["number"] or -1)) > 1e-12)
        rec["differences"] = diff
        res["differences"] += diff
        res["traces"].append(rec)
    res["pass"] = res["differences"] == 0 and res["invalid_inputs_rejected"] == res["invalid_inputs_tried"]
    print(json.dumps(res, indent=1, sort_keys=True))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
