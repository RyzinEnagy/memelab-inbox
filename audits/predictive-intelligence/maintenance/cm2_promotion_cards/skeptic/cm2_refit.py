"""CM-2 skeptic: refit R-CM2-1 v1 from as-of data in a scratch clone and compare to the committed cards; B0 also by hand."""
import importlib.util, json, sys, gzip, hashlib
from pathlib import Path
repo = Path(sys.argv[1]); state = Path(sys.argv[2])
sys.path.insert(0, str(repo))
spec = importlib.util.spec_from_file_location("pd", repo / "audits/predictive-intelligence/daily/predictive_daily.py")
D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)
from memelab.predictive import baselines as B, labels as L
reg = D.registry()
now = max(reg["registered_at"].values())
state.mkdir(parents=True, exist_ok=True)
fs = D.build_store(state, "71fc50e1eb86d916034bb0285a466cf2ec1cc4d0")
hold = D.holdout_rows(); lab = D.label_store(state)
fit = D.fit_version(lab, hold, fs, rec=D.recipe(), version=1, now=now)
out = {}
for (kind, t), card in sorted(fit["cards"].items()):
    p = repo / f"audits/predictive-intelligence/daily/cards/R-CM2-1_v1_{kind}_{D.SHORT[t]}.json"
    out[f"{kind}_{D.SHORT[t]}"] = {"refit_equal_bytes": B.dumps(card) == p.read_text(), "model_sha": card["model_sha"][:12]}
# B0 by hand: labeled uncensored rows, newest version per (decision,target), matured by cutoff, split in WIDE
cut = fit["cutoff"]
rows = [json.loads(x)["row"] for x in gzip.open(repo / "audits/predictive-intelligence/daily/BASE_LABELS.jsonl.gz", "rt")]
rows = [r for r in rows if "label_key" in r] + [dict(r) for r in hold]
for t in D.TARGETS:
    best = {}
    for r in rows:
        if r.get("target") != t: continue
        if L.C.label_matures_at(t, r["decision_time"]) > cut: continue
        k = r["decision_key"]; best.setdefault(k, []).append(r)
    n = k1 = 0
    for k, rs in best.items():
        r = rs[-1]
        if r["state"] == "LABELED" and not int(r.get("censored") or 0) and r.get("label") in (0, 1):
            n += 1; k1 += int(r["label"])
    card = json.loads((repo / f"audits/predictive-intelligence/daily/cards/R-CM2-1_v1_B0_{D.SHORT[t]}.json").read_text())
    out[f"hand_B0_{D.SHORT[t]}"] = {"n": n, "k": k1, "p": k1 / n if n else None, "card_p": card["body"]["p"], "card_n": card["n_train"], "card_k": card["k_train"]}
out["cutoff_utc"] = D.iso(cut); out["now_used"] = D.iso(now)
print(json.dumps(out, indent=1))
