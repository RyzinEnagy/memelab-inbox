"""Phase 07 skeptic counterexample CX-S07: the frozen verdict function awards SKILL_INDICATED_DEVELOPMENT_ONLY to a baseline
evaluated on 6 out-of-sample rows with ONE positive, as long as they fall on 5 decision days. No minimum event or per-class
count enters `baselines.verdict` or `baselines.evaluate` (the AUC rule needs 10 per class, the verdict needs nothing), and
the bootstrap cannot see the problem: every replicate without the positive still scores the model above B0 because it is
lower on the negatives, so the one-sided p is 1/2001 and Holm (x3) stays below 0.05.

This is a wrong-but-plausible outcome: on the real T1b data the out-of-sample set already has only 3 positives in 44 rows
over exactly 5 days. Run from the repository clone:

    python -B /home/claude/pi_orchestration/skeptic/p07_counterexample.py /home/claude/pi_orchestration/skeptic_07
"""
import datetime as dt
import sys

sys.path.insert(0, sys.argv[1])
from memelab.predictive import baselines as B  # noqa: E402
from memelab.predictive import stats as K  # noqa: E402

base = dt.datetime(2026, 10, 12, 12, tzinfo=dt.timezone.utc).timestamp()
spec = [  # (day offset, y, model p); B0 = training prevalence 0.20 for every row
    (0, 1, 0.45), (0, 0, 0.05), (1, 0, 0.06), (2, 0, 0.05), (3, 0, 0.07), (4, 0, 0.05)]
rows = []
for i, (d, y, p) in enumerate(spec):
    e = B.Example(decision_key=f"k{i}", chain="solana", mint=f"Mint{i}pump", decision_time=base + d * 86400.0,
                  label_matures_at=base + d * 86400.0 + 87600, y=y)
    rows.append({"fold": d, "example": e, "y": y, "B0": 0.20, "B2": p, "B2_why": None})

ev = B.evaluate(rows, "B2")
p_holm = K.holm([float("nan"), ev["p_one_sided"], float("nan")])[1]   # the other two targets undefined, counted as p = 1
v = B.verdict(ev, p_holm)
print({"n": ev["n_with_number"], "positives": ev["positives"], "days": ev["days"], "bss": round(ev["bss"], 3),
       "intervals": {u: [round(x, 3) for x in ev["intervals"][u]["ci"]] for u in ev["intervals"]},
       "governing": ev["governing"], "p_one_sided": round(ev["p_one_sided"], 5), "p_holm": round(p_holm, 5), "verdict": v})
sys.exit(0 if v == "SKILL_INDICATED_DEVELOPMENT_ONLY" else 1)
