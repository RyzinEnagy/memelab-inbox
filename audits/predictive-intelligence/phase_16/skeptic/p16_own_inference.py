"""Phase 16 skeptic: own-code check that registry entries reproduce Phase 12 holdout predictions.
(1) for all 69 entries, recompute the identical-inference hash directly from HOLDOUT_PREDICTIONS.csv with own canonicalization;
(2) for B0, B1, B2 of every target (9 cards), recompute every number with own math from card body + Phase 12 inputs (inputs only).
Usage: python -B p16_own_inference.py <repo clone> <out.json>"""
import csv, hashlib, importlib.util, json, math, sys
from pathlib import Path
REPO = Path(sys.argv[1]); OUT = Path(sys.argv[2])
sys.path.insert(0, str(REPO))
AUD = REPO / "audits/predictive-intelligence"
def canon(o): return json.dumps(o, sort_keys=True, separators=(",", ":"), allow_nan=False)
rec = {}
for r in csv.DictReader(open(AUD / "phase_12/validation/HOLDOUT_PREDICTIONS.csv")):
    if r["candidate"].startswith("NC1_"): continue
    rec.setdefault((r["target_short"], r["candidate"]), []).append(r)
SHORT = {"price_path_target_before_invalidation_24h": "T1_24h", "price_path_target_before_invalidation_6h": "T1b_6h",
         "price_path_severe_drawdown_or_halt_24h": "T2_24h"}
res = {"hash_checks": {}, "own_number_checks": {}}
ents = {}
for p in sorted((AUD / "phase_16/registry/entries").glob("*.json")):
    e = json.loads(p.read_text())
    assert hashlib.sha256(canon({k: v for k, v in e.items() if k != "entry_id"}).encode()).hexdigest() == e["entry_id"] == p.stem
    s, cid = SHORT[e["target"]], e["family"]["candidate"]
    ents[(s, cid)] = e
    rows = sorted([[r["decision_key"], float(r["number"]) if r["number"] != "" else None, r["why"]] for r in rec[(s, cid)]], key=lambda x: x[0])
    h = hashlib.sha256(canon(rows).encode()).hexdigest()
    res["hash_checks"][f"{s}:{cid}"] = {"own_hash_equals_entry": h == e["inference"]["outputs_sha"], "rows": len(rows)}
res["hash_equal"] = sum(v["own_hash_equals_entry"] for v in res["hash_checks"].values()); res["entries"] = len(ents)
# own numbers for B0, B1, B2
spec = importlib.util.spec_from_file_location("rh", AUD / "phase_12/probes/run_holdout.py"); RH = importlib.util.module_from_spec(spec); spec.loader.exec_module(RH)
inp = RH.Inputs(RH.P7.DEV_STORE, RH.P7.FEATURE_STORE)
from memelab.predictive import labels as L
groups_of = None
for t in (L.T1, L.T1B, L.T2):
    s = SHORT[t]
    ex = inp.family("07", inp.examples(t))
    for cid in ("P07_B0", "P07_B1", "P07_B2"):
        card = json.loads((REPO / ents[(s, cid)]["card_path"]).read_text()); b = card["body"]
        recd = {r["decision_key"]: r for r in rec[(s, cid)]}
        maxd, exact, nnum, mism = 0.0, 0, 0, []
        for e in ex:
            if cid == "P07_B0": p, why = b["p"], ""
            elif cid == "P07_B1":
                g = b["status_groups"].get(e.status); p = b["groups"][g]["p"] if g in b["groups"] else b["b0"]; why = ""
            else:
                x = [e.x.get(c) for c in b["columns"]]; x = [float("nan") if v is None else float(v) for v in x]
                req = [b["columns"].index(c) for c in b["required"]]
                if not all(math.isfinite(x[i]) for i in req): p, why = None, "OOD"
                else:
                    pr = b["prep"]; xs = [x[i] for i in pr["keep"]]
                    f = [(pr["med"][j] if not math.isfinite(v) else v) for j, v in enumerate(xs)]
                    f += [1.0 if not math.isfinite(xs[i]) else 0.0 for i in pr["ind"]]
                    z = [(v - pr["mu"][j]) / pr["sd"][j] for j, v in enumerate(f)]
                    eta = b["logistic"]["intercept"] + sum(c * v for c, v in zip(b["logistic"]["coef"], z))
                    p, why = 1.0 / (1.0 + math.exp(-eta)), ""
            r = recd[e.decision_key]
            if p is None:
                if r["number"] != "" or r["why"] != why: mism.append(e.decision_key[:12])
                continue
            nnum += 1
            d = abs(p - float(r["number"])); maxd = max(maxd, d); exact += (repr(p) == repr(float(r["number"])))
            if d > 1e-12 or r["why"] != why: mism.append(e.decision_key[:12])
        res["own_number_checks"][f"{s}:{cid}"] = {"decisions": len(ex), "recorded_rows": len(recd), "numbers": nnum, "max_abs_diff": maxd,
                                                  "bit_exact": exact, "mismatches_over_1e-12": mism}
OUT.write_text(json.dumps(res, indent=1, sort_keys=True)); print(json.dumps({"hash_equal": res["hash_equal"], "entries": res["entries"],
      "own": {k: (v["numbers"], v["max_abs_diff"], len(v["mismatches_over_1e-12"])) for k, v in res["own_number_checks"].items()}}, indent=0))
