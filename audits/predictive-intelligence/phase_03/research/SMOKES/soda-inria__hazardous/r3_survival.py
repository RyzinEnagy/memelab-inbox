"""R3 competing-risk variant of the shared challenge (synthetic; seed 20261025; not produced by make_challenge.py).
event 1 = target first (the challenge's positives, same time), event 2 = invalidation first (assigned by a seeded rule
to a share of the challenge's negatives, time uniform 0.2..24 h), event 0 = censored (neither by 24 h, or the
challenge's own censored rows at their censoring time)."""
import numpy as np

SEED = 20261025


def competing_variant(d):
    rng = np.random.default_rng(SEED)
    n = len(d["label"])
    lab = d["label"]
    ev = np.zeros(n, dtype=int)
    dur = d["time_to_event_h"].astype(float).copy()
    pos = lab == 1
    neg = lab == 0
    ev[pos] = 1
    z = -0.4 - 6.0 * d["ret_1h"] + 0.8 * d["fatal_flag"]
    q = 1 / (1 + np.exp(-z))
    inv = neg & (rng.random(n) < q)
    ev[inv] = 2
    dur[inv] = rng.uniform(0.2, 24.0, n)[inv]
    # censored rows (label NaN) keep event 0 at their censoring time
    return ev, dur
