"""CX-S12 check (repair pass 2; SYNTHETIC data only, no holdout label). The skeptic's scenario: a candidate X far better than
both references on three 70-row, 7-day targets. The first-pass runner rule (`p_max_t` None for every row against B2, and a pass
needs every p below 0.05) reports X against B2 as "not surviving"; `evaluation.selection_status` reports CORRECTION_NOT_COMPUTED,
and with a max-T against B2 computed it reports SURVIVES (on synthetic data). Writes a JSON report.

    python -B cx_s12_check.py OUT.json [--reps N]
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from memelab.predictive import evaluation as E  # noqa: E402
from memelab.predictive import stats as K  # noqa: E402

reps = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == "--reps" else 20000
rng = np.random.default_rng(1)
days = [f"2026-10-{17 + d}" for d in range(7)]
T = {}
for t in ("T1_24h", "T1b_6h", "T2_24h"):
    d = [days[i % 7] for i in range(70)]
    y = (rng.random(70) < 0.25).astype(float)
    T[t] = dict(d=d, y=y, b0=np.full(70, 0.25), b2=np.clip(0.25 + rng.normal(0, 0.15, 70), 0.01, 0.99), x=np.where(y == 1, 0.8, 0.08))
rows = []
for t, v in T.items():
    for ref in ("b0", "b2"):
        bs = K.group_bootstrap(v["d"], lambda i: K.brier_skill(v["y"][i], v["x"][i], v[ref][i]), reps=reps, seed=5)
        rows.append((t, ref, (1 + int(np.sum(~(bs["values"] > 0)))) / (reps + 1)))
holm = E.holm([p for *_, p in rows])
D, Y = {t: v["d"] for t, v in T.items()}, {t: v["y"] for t, v in T.items()}
mt0 = E.max_t(D, Y, {t: v["b0"] for t, v in T.items()}, {(t, "X"): v["x"] for t, v in T.items()} | {(t, "B2"): v["b2"] for t, v in T.items()}, reps=reps, seed=5)
mt2 = E.max_t(D, Y, {t: v["b2"] for t, v in T.items()}, {(t, "X"): v["x"] for t, v in T.items()}, reps=reps, seed=5)
out = []
for (t, ref, p), ph in zip(rows, holm):
    own = E.HOLDOUT_SKILL
    bon = E.bonferroni(p, 118)
    first_mt = mt0[(t, "X")]["p_max_t"] if ref == "b0" else None
    first_pass_rule = bool(ph < E.ALPHA and first_mt is not None and first_mt < E.ALPHA and bon is not None and bon < E.ALPHA)
    out.append({"target": t, "reference": ref.upper(), "p": p, "holm": ph, "bonferroni_118": bon,
                "first_pass_skill_after_correction": first_pass_rule,
                "repaired_status_as_recorded": E.selection_status(own, ph, first_mt, bon),
                "repaired_status_with_max_t_vs_b2": E.selection_status(own, ph, first_mt if ref == "b0" else mt2[(t, "X")]["p_max_t"], bon)})
caught = all(r["repaired_status_as_recorded"] == E.NOT_COMPUTED for r in out if r["reference"] == "B2") and \
    all(not r["first_pass_skill_after_correction"] for r in out if r["reference"] == "B2")
rep = {"data": "SYNTHETIC", "reps": reps, "rows": out, "first_pass_hides_b2_rows_as_not_surviving": caught}
Path(sys.argv[1]).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
print(json.dumps({"caught": caught, "statuses": [(r["target"], r["reference"], r["first_pass_skill_after_correction"], r["repaired_status_as_recorded"], r["repaired_status_with_max_t_vs_b2"]) for r in out]}))
raise SystemExit(0 if caught else 1)
