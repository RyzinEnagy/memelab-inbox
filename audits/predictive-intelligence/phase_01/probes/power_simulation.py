"""Phase 01 design arithmetic (synthetic, not a result): how large a Brier skill score (BSS) over the prevalence baseline can a
holdout of n independent events distinguish from zero?

Assumptions, stated so they can be attacked: base rate 0.30; the model is perfectly calibrated and its probabilities follow a
Beta distribution whose variance gives the true BSS (BSS = var(p) / (base * (1 - base))); the baseline predicts the true base rate;
events are independent (real events cluster by day and mint, so real detectability is lower); detection = lower end of a normal 95%
interval on the mean per-event Brier difference above zero. Seeded; no data are read.

    python audits/predictive-intelligence/phase_01/probes/power_simulation.py
"""
import numpy as np

rng = np.random.default_rng(20261024)
base = 0.30
print("true_BSS    n  sd(BSS_hat)  P(detect)")
for bss in (0.02, 0.05, 0.10, 0.20):
    k = base * (1 - base) / (bss * base * (1 - base)) - 1
    a, b = base * k, (1 - base) * k
    for n in (50, 100, 150, 250):
        est, det = [], 0
        for _ in range(4000):
            p = rng.beta(a, b, n)
            y = rng.random(n) < p
            d = (base - y) ** 2 - (p - y) ** 2
            bb = np.mean((base - y) ** 2)
            est.append(1 - np.mean((p - y) ** 2) / bb if bb > 0 else 0.0)
            if d.mean() - 1.96 * d.std(ddof=1) / np.sqrt(n) > 0:
                det += 1
        print(f"{bss:8.2f} {n:4d} {np.std(est):12.3f} {det / 4000:10.2f}")
