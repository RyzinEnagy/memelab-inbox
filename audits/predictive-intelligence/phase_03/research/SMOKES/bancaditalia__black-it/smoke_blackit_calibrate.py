"""black-it smoke at the pinned SHA (Phase 03, reviewer R5): calibrate an LLM-free trader-reaction ABM.

Synthetic, format and behaviour only. A vectorised trader model (momentum share m, price impact a)
reacts to one fictional catalyst shock; it returns a (N, 1) series of synthetic log returns.
A target series is generated from known parameters (a=0.02, m=0.6, seed 123). black-it must
recover them from the series alone (falsifiability: a behavioural model whose parameters are
fitted to observed paths, then judged out of sample by the wrapper).

Checks: parameter recovery, determinism (same random_state twice), sensitivity to random_state,
the S1 analog (black-it fits whatever real_data it is given; a series that runs past the decision
cut-off is accepted without complaint), checkpoint format (pickle files), cost, offline.

Usage: PYTHONPATH=<black-it clone> python smoke_blackit_calibrate.py WORKDIR
"""
import hashlib
import json
import os
import resource
import sys
import time

import numpy as np

from black_it.calibrator import Calibrator
from black_it.loss_functions.msm import MethodOfMomentsLoss
from black_it.samplers.best_batch import BestBatchSampler
from black_it.samplers.halton import HaltonSampler

K = 50
SHOCK_T = 20


def trader_model(theta, N, seed):
    a, m = float(theta[0]), float(theta[1])
    rng = np.random.default_rng(seed)
    n_mom = int(round(m * K))
    thr = rng.uniform(0.0, 0.05, K)
    out = np.zeros(N)
    last = 0.0
    for t in range(N):
        shock = 0.15 * (0.8 ** (t - SHOCK_T)) if t >= SHOCK_T else 0.0
        x = shock + last
        mom = np.where(x > thr[:n_mom], 1, np.where(x < -thr[:n_mom], -1, 0)).sum()
        con = np.where(last > thr[n_mom:], -1, np.where(last < -thr[n_mom:], 1, 0)).sum()
        ret = a * (mom + con) / 10.0 + rng.normal(0, 0.01)
        out[t] = ret
        last = ret
    return out.reshape(N, 1)


def run(real, seed, work, tag, n_batches=6):
    cal = Calibrator(
        samplers=[HaltonSampler(batch_size=8), BestBatchSampler(batch_size=8)],
        real_data=real, model=trader_model,
        parameters_bounds=[[0.005, 0.0], [0.05, 1.0]], parameters_precision=[0.001, 0.01],
        ensemble_size=3, loss_function=MethodOfMomentsLoss(), random_state=seed, n_jobs=1,
        saving_folder=os.path.join(work, tag), verbose=False)
    t0 = time.time()
    params, losses = cal.calibrate(n_batches)
    wall = time.time() - t0
    return params, losses, wall


def main(work):
    os.makedirs(work, exist_ok=True)
    N = 120
    real = trader_model([0.02, 0.6], N, 123)
    out = {"true_params": [0.02, 0.6], "series_len": N, "model_evals_per_calibration": 6 * 8 * 3}
    p1, l1, w1 = run(real, 1, work, "cal_seed1")
    p1b, l1b, _ = run(real, 1, work, "cal_seed1_again")
    p2, l2, w2 = run(real, 2, work, "cal_seed2")
    h = lambda a: hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
    out["best_params_seed1"] = p1[0].tolist()
    out["best_loss_seed1"] = float(l1[0])
    out["top5_params_seed1"] = p1[:5].tolist()
    out["best_params_seed2"] = p2[0].tolist()
    out["best_loss_seed2"] = float(l2[0])
    out["same_random_state_identical"] = h(p1) == h(p1b) and h(l1) == h(l1b)
    out["different_random_state_identical"] = h(p1) == h(p2)
    out["wall_s_per_calibration"] = [round(w1, 2), round(w2, 2)]
    # S1 analog: a "real" series that includes 60 steps after a decision cut-off at t=60 is accepted as is
    leaky = real.copy()
    p3, l3, _ = run(leaky, 1, work, "cal_full_series_no_cutoff", n_batches=2)
    out["S1_series_past_cutoff_accepted"] = True
    out["S1_note"] = "Calibrator takes real_data as given; no timestamp, cut-off or availability check exists"
    files = sorted(os.listdir(os.path.join(work, "cal_seed1")))
    out["checkpoint_files"] = files
    out["checkpoint_uses_pickle"] = any(f.endswith(".pickle") for f in files)
    out["peak_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
