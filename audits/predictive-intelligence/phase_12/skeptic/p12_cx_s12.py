"""CX-S12 (skeptic, SYNTHETIC data only; no holdout label is read).
A wrong-but-plausible reading of the Phase 12 output: "0 of 129 secondary comparisons survive the selection correction" is taken
to mean no frozen card beat B2 after correction. But run_holdout.py (lines 725-728) sets p_max_t = None for every row whose
reference is P07_B2 and requires p_max_t < 0.05 for skill_after_selection_correction, so a vs-B2 row can never survive,
whatever the data. This script builds a synthetic holdout where a candidate X is far better than B2 and shows the runner's own
rule reports X-vs-B2 as not surviving, while the same evidence against B0 survives.
    python -B p12_cx_s12.py <clone>"""
import sys, math, numpy as np
sys.path.insert(0, sys.argv[1])
from memelab.predictive import evaluation as E
rng = np.random.default_rng(1)
days = [f"2026-10-{17+d}" for d in range(7)]
T = {}
for t in ("T1_24h", "T1b_6h", "T2_24h"):
    n = 70; d = [days[i % 7] for i in range(n)]
    y = (rng.random(n) < 0.25).astype(float)
    b0 = np.full(n, 0.25)
    b2 = np.clip(0.25 + rng.normal(0, 0.15, n), 0.01, 0.99)       # a noisy simple model
    x = np.where(y == 1, 0.8, 0.08)                                 # a strong synthetic candidate
    T[t] = dict(d=d, y=y, b0=b0, b2=b2, x=x)
REPS = 20000
def boot_p(y, p, r, d):  # one-sided day-block bootstrap p of BSS<=0 (own code)
    u = sorted(set(d)); idx = {k: [i for i, z in enumerate(d) if z == k] for k in u}; c = 0
    for _ in range(REPS):
        s = sum((idx[u[j]] for j in rng.integers(0, len(u), len(u))), [])
        c += (1 - np.sum((p[s]-y[s])**2)/np.sum((r[s]-y[s])**2)) <= 0
    return (1 + c) / (REPS + 1)
rows = []
for t, v in T.items():
    for ref in ("B0", "B2"):
        rows.append((t, ref, boot_p(v["y"], v["x"], v[ref.lower()], v["d"])))
holm = E.holm([p for *_, p in rows])
mt = E.max_t({t: v["d"] for t, v in T.items()}, {t: v["y"] for t, v in T.items()}, {t: v["b0"] for t, v in T.items()},
             {(t, "X"): v["x"] for t, v in T.items()} | {(t, "B2"): v["b2"] for t, v in T.items()}, reps=REPS, seed=5)
mt_b2 = E.max_t({t: v["d"] for t, v in T.items()}, {t: v["y"] for t, v in T.items()}, {t: v["b2"] for t, v in T.items()},
                {(t, "X"): v["x"] for t, v in T.items()}, reps=REPS, seed=5)
for (t, ref, p), ph in zip(rows, holm):
    mtp = mt[(t, "X")]["p_max_t"] if ref == "B0" else None        # exactly the runner's rule (line 725)
    bon = E.bonferroni(p, 118)
    corrected = (ph < E.ALPHA and mtp is not None and mtp < E.ALPHA and bon is not None and bon < E.ALPHA)
    print(f"{t} X vs {ref}: p={p:.4f} holm={ph:.4f} bonf118={bon:.4f} p_max_t={mtp} -> skill_after_selection_correction={corrected}"
          + (f"   (a max-T against B2 would give {mt_b2[(t,'X')]['p_max_t']:.4f})" if ref == "B2" else ""))
