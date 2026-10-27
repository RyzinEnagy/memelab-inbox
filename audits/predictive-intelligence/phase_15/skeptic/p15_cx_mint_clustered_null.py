"""Skeptic Phase 15 counterexample CX-S15: an outcome-independent bogus warning assigned per MINT (as real attention rules are,
because a mint's attention proxies persist across its repeated decisions), scored with the phase's own frozen
scenario_eval.warning_metrics (day-stratified permutation of decisions). If the decision-level permutation null were valid for
such warnings, p_up < 0.05 would occur in about 5% of salts. The phase's NCB control plants per DECISION (hash of the decision
key), so it cannot see this. Usage: python -I ... REPO DEV_STORE [n_salts] [reps]"""
import csv, hashlib, json, sqlite3, sys
repo, store = sys.argv[1], sys.argv[2]
n_salts = int(sys.argv[3]) if len(sys.argv) > 3 else 200
reps = int(sys.argv[4]) if len(sys.argv) > 4 else 500
sys.path.insert(0, repo)
from memelab.predictive import scenario_eval as S  # noqa: E402
P15 = f"{repo}/audits/predictive-intelligence/phase_15/behavioral"
LONG = {"T1_24h": "price_path_target_before_invalidation_24h", "T1b_6h": "price_path_target_before_invalidation_6h",
        "T2_24h": "price_path_severe_drawdown_or_halt_24h"}
con = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
day = {r["decision_key"]: r["day"] for r in csv.DictReader(open(f"{P15}/SCENARIO_CODING.csv")) if r["set"] == "DEVELOPMENT"}
def half(s): return int(hashlib.sha256(s.encode()).hexdigest()[0], 16) % 2 == 0
out = {}
for short, T in LONG.items():
    L = list(con.execute("SELECT decision_key, mint, label FROM predictive_labels WHERE target=? AND split='DEVELOPMENT' AND "
                         "state='LABELED' AND eligibility='ELIGIBLE' AND censored=0 AND thinned_by IS NULL", (T,)))
    res = {}
    for unit in ("DECISION", "MINT"):
        up = down = either = 0; ps = []
        for s in range(n_salts):
            rows = [{"y": int(y), "day": day[k], "lead_s": None,
                     "warning": "EVENT" if half((k if unit == "DECISION" else m) + f":cx-s15:{s}") else "NONE"} for k, m, y in L]
            perm = S.warning_metrics(rows, reps=reps, seed=20261025)["permutation"]
            a, b = perm["p_up"] < 0.05, perm["p_down"] < 0.05
            up += a; down += b; either += a or b
        res[unit] = {"salts": n_salts, "share_p_up_below_0.05": up / n_salts, "share_p_down_below_0.05": down / n_salts,
                     "share_either_below_0.05": either / n_salts}
    out[short] = res
print(json.dumps({"reps_per_salt": reps, "results": out, "nominal_one_sided": 0.05, "nominal_either": 0.10}, indent=1))
