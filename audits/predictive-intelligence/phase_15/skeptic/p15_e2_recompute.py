"""Skeptic Phase 15: E2 and NCB counts and day-stratified permutation recomputed from the raw label table and the committed
coding files with my own numpy permutation (different RNG stream from the phase's). Usage: python -I ... REPO DEV_STORE"""
import csv, sqlite3, sys, json
import numpy as np
repo, store = sys.argv[1], sys.argv[2]
P15 = f"{repo}/audits/predictive-intelligence/phase_15/behavioral"
LONG = {"T1_24h": "price_path_target_before_invalidation_24h", "T1b_6h": "price_path_target_before_invalidation_6h",
        "T2_24h": "price_path_severe_drawdown_or_halt_24h"}
con = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
cod = {(r["decision_key"], r["target"]): r for r in csv.DictReader(open(f"{P15}/SCENARIO_CODING.csv")) if r["set"] == "DEVELOPMENT"}
ctl = {(r["decision_key"], r["target"]): r for r in csv.DictReader(open(f"{P15}/CONTROL_CODING.csv")) if r["control"] == "NCB_VERIFIED"}
oos = {(r["decision_key"], LONG[r["target_short"]]): int(r["y"]) for r in csv.DictReader(open(f"{P15}/E1_OOS_ROWS.csv"))}
def labs(target):
    return [dict(zip(("k", "y", "mint", "ft", "t"), row)) for row in con.execute(
        "SELECT decision_key, label, mint, first_touch_start, decision_time FROM predictive_labels WHERE target=? AND split='DEVELOPMENT' "
        "AND state='LABELED' AND eligibility='ELIGIBLE' AND censored=0 AND thinned_by IS NULL", (target,))]
def perm(w, y, days, reps=20000, seed=7):
    rng = np.random.default_rng(seed); w = np.asarray(w, bool); y = np.asarray(y, int)
    obs = int((w & (y == 1)).sum()); groups = {}
    for i, d in enumerate(days): groups.setdefault(d, []).append(i)
    idx = [np.array(v) for v in groups.values()]; null = np.empty(reps, int)
    for r in range(reps):
        wp = w.copy()
        for g in idx: wp[g] = rng.permutation(w[g])
        null[r] = int((wp & (y == 1)).sum())
    return (1 + int((null >= obs).sum())) / (reps + 1)
def desc(rows, wfun):
    y = [int(l["y"]) for l in rows]; w = [wfun(l) for l in rows]; days = [cod[(l["k"], T)]["day"] for l in rows]
    n, k, nw = len(y), sum(y), sum(w); h = sum(1 for a, b in zip(w, y) if a and b)
    return {"n": n, "pos": k, "days": len(set(days)), "warned": nw, "hits": h, "precision": h / nw if nw else None,
            "prevalence": k / n, "p_up_my_perm": perm(w, y, days) if 0 < nw < n else None}
out = {}
ymis = 0
for short, T in LONG.items():
    L = labs(T)
    for l in L:
        if (l["k"], T) in oos and oos[(l["k"], T)] != int(l["y"]): ymis += 1
    out[short] = desc(L, lambda l: cod[(l["k"], T)]["warning"] == "EVENT")
    for lab in ("ATTENTION_EXHAUSTION", "MANUFACTURED_ATTENTION_DUMP", "ORGANIC_ATTENTION_CONTINUATION"):
        if any(lab in cod[(l["k"], T)]["labels"].split("|") for l in L):
            out[f"{short}:{lab}"] = desc(L, lambda l: cod[(l["k"], T)]["warning"] == "EVENT" and lab in cod[(l["k"], T)]["labels"].split("|"))
    if short == "T1_24h":
        out["NCB_VERIFIED_T1"] = desc(L, lambda l: ctl[(l["k"], T)]["warning"] == "EVENT")
out["E1_y_mismatches_vs_label_table"] = ymis
print(json.dumps(out, indent=1))
