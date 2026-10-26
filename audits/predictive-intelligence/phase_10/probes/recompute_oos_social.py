"""Phase 10 independent recomputation of every out-of-sample number of the social models. Uses neither socialcat.py nor
features.py nor stats.py: the inputs come from the committed SOCIAL_FEATURES_DEVELOPMENT.csv (socialcat-1 values) and plain SQL
over the Phase 05 store (version 2 values), the cards from the committed artifacts/folds/<target>.json, and each number is
recomputed with plain Python (median fill, missing indicators, standardisation, logistic or boosted stumps, rule cells). Compared
with OOS_PREDICTIONS.csv at its 6 decimals.

    python -B recompute_oos_social.py [--feature-store PATH]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
import sys
from pathlib import Path

P10 = Path(__file__).resolve().parents[1]
FEATURE_STORE = "/home/claude/pi_research/p05/predictive_store.sqlite"
MODELS = ("R2_SC_RULE", "S1_SC_LOGIT", "S2_SC_LOGIT_B2", "S3_SC_LOGIT_TREND", "G1_SC_STUMPS_B2", "A2_SC_B2_TC")
V2 = ("thesis_log1p_liquidity_usd", "thesis_log1p_mcap_usd", "thesis_log1p_vol_24h_usd", "thesis_fatal_present")


def fnum(s):
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def design(body, x):
    cols, prep = body["spec"]["columns"], body["prep"]
    X = [x.get(c) for c in cols]
    kept = [X[j] for j in prep["keep"]]
    filled = [prep["med"][i] if v is None else v for i, v in enumerate(kept)]
    ind = [1.0 if kept[j] is None else 0.0 for j in prep["ind"]]
    return [(v - m) / s for v, m, s in zip(filled + ind, prep["mu"], prep["sd"])]


def number(body, x):
    if "abstain" in body:
        return None
    spec = body["spec"]
    if spec["kind"] == "rule":
        a, b = x.get(spec["columns"][0]), x.get(spec["columns"][1])
        cell = "MISSING" if a is None or b is None else f"T{int(a)}S{int(b)}"
        return body["cells"][cell]["p"] if cell in body["cells"] else body["b0"]
    if any(x.get(c) is None for c in spec["rows"]):
        return None
    z = design(body, x)
    if "logistic" in body:
        lg = body["logistic"]
        t = lg["intercept"] + sum(c * v for c, v in zip(lg["coef"], z))
    else:
        st = body["stumps"]
        t = st["init"]
        for j, thr, vl, vr in st["trees"]:
            t += st["lr"] * (vl if z[int(j)] <= thr else vr)
    return 1.0 / (1.0 + math.exp(-t))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feature-store", default=FEATURE_STORE)
    a = ap.parse_args()
    con = sqlite3.connect(f"file:{a.feature_store}?mode=ro", uri=True)
    feats = {r["decision_key"]: r for r in csv.DictReader(open(P10 / "experiments/SOCIAL_FEATURES_DEVELOPMENT.csv"))}
    oos = list(csv.DictReader(open(P10 / "experiments/OOS_PREDICTIONS.csv")))
    cards = {s: json.loads((P10 / "artifacts/folds" / f"{s}.json").read_text()) for s in sorted({r["target_short"] for r in oos})}
    diffs, compared, numbers = [], 0, 0
    for r in oos:
        k = r["decision_key"]
        x = {c: fnum(v) for c, v in feats[k].items() if c.startswith("sc_")}
        for c in V2:
            row = con.execute("SELECT v.value FROM predictive_snapshots s JOIN predictive_feature_values v USING(snapshot_key) WHERE "
                              "s.decision_key=? AND s.availability_mode='provider' AND v.feature_name=?", (k, c)).fetchone()
            x[c] = None if row is None or row[0] is None else float(row[0])
        age = con.execute("SELECT v.value FROM predictive_snapshots s JOIN predictive_feature_values v USING(snapshot_key) WHERE "
                          "s.decision_key=? AND s.availability_mode='provider' AND v.feature_name='token_age_s'", (k,)).fetchone()
        x["log1p_token_age_days"] = math.log1p(age[0] / 86400.0) if age and age[0] is not None and age[0] >= 0 else None
        fold = next(f for f in cards[r["target_short"]]["folds"] if f["fold"] == int(r["fold"]))
        for m in MODELS:
            got = number(fold["cards"][m]["body"], x)
            want = r[m]
            compared += 1
            mine = "" if got is None else f"{got:.6f}"
            numbers += got is not None
            if mine != want:
                diffs.append(f"{r['target_short']} {k[:12]} {m}: recomputed {mine!r} vs stored {want!r}")
    rep = {"rows": len(oos), "model_values_compared": compared, "numbers_recomputed": numbers, "differences": diffs, "pass": not diffs}
    (P10 / "evidence/recompute_oos.json").write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("rows", "model_values_compared", "numbers_recomputed", "pass")} | {"differences": len(diffs)}))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
