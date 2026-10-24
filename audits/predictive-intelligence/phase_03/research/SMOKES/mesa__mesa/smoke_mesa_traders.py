"""Mesa smoke at the pinned SHA (Phase 03, reviewer R5): an LLM-free, seeded trader-reaction ABM.

Synthetic, format and behaviour only. For each challenge decision row a tiny market of
heterogeneous trader agents (momentum, contrarian, noise, take-profit exiters) reacts to a
signal for T steps; price moves with net demand scaled by liquidity. A run "hits" if the
synthetic price touches +25% before -15%. The share of R seeded runs that hit is the
simulator frequency. It is a frequency over simulator randomness, never a calibrated
probability of a real event (P27); scoring it against labels only shows what happens if
someone treats it as one.

S1: signal = ret_1h (legitimate, available at decision) vs leak_future_ret (TRAP, available
    6 h later). Mesa has no availability-time or split mechanism, so nothing stops the trap.
S2: frequencies in [0,1], Brier and log loss on holdout (censored rows excluded) vs the
    train-prevalence baseline.
S3: liq_usd NaN: run once without imputation to show what Mesa does, then impute train median.
S4: Mesa has no calibration; reliability in 3 quantile bins is reported as description.
S5: determinism: rerun with the same seeds gives a byte-identical frequency vector;
    persistence is "save params + seeds", no model artifact.
S6: cost: wall time, per-run latency, peak RSS, no network (run inside unshare -n).

Usage: PYTHONPATH=<mesa clone> python smoke_mesa_traders.py CHALLENGE_CSV
"""
import csv
import hashlib
import json
import math
import resource
import sys
import time

import numpy as np

import mesa

T_STEPS = 12
N_AGENTS = 20
R_SEEDS = 5


class Trader(mesa.Agent):
    def __init__(self, model, kind, thresh, size):
        super().__init__(model)
        self.kind = kind
        self.thresh = thresh
        self.size = size

    def step(self):
        m = self.model
        x = m.signal + m.last_ret
        if self.kind == "momentum":
            d = 1 if x > self.thresh else (-1 if x < -self.thresh else 0)
        elif self.kind == "contrarian":
            d = -1 if m.last_ret > self.thresh else (1 if m.last_ret < -self.thresh else 0)
        elif self.kind == "exiter":
            d = -1 if m.price > 1.0 + self.thresh else 0
        else:
            d = int(m.rng.integers(-1, 2))
        m.demand += d * self.size


class Market(mesa.Model):
    def __init__(self, signal, liq, rng):
        super().__init__(rng=rng)
        self.signal = float(signal)
        self.liq_scale = math.log10(liq)  # NaN liq propagates
        self.price = 1.0
        self.last_ret = 0.0
        self.demand = 0.0
        kinds = ["momentum"] * 8 + ["contrarian"] * 5 + ["noise"] * 4 + ["exiter"] * 3
        for k in kinds[:N_AGENTS]:
            Trader(self, k, float(self.rng.uniform(0.0, 0.12)), float(self.rng.uniform(0.5, 1.5)))
        self.hit = None

    def step(self):
        self.demand = 0.0
        self.agents.shuffle_do("step")
        ret = 0.02 * self.demand / self.liq_scale + float(self.rng.normal(0, 0.03))
        self.price *= math.exp(ret)
        self.last_ret = ret
        self.signal *= 0.7
        if self.hit is None:
            if self.price >= 1.25:
                self.hit = 1
            elif self.price <= 0.85:
                self.hit = 0


def sim_freq(signal, liq, seed_base):
    hits = 0
    for r in range(R_SEEDS):
        m = Market(signal, liq, rng=seed_base * 1000 + r)
        for _ in range(T_STEPS):
            m.step()
            if m.hit is not None:
                break
        hits += 1 if m.hit == 1 else 0
    return hits / R_SEEDS


def load(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def num(x):
    return float("nan") if x == "" else float(x)


def scores(p, y, base):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, float)
    brier = float(np.mean((p - y) ** 2))
    ll = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    pb = np.clip(np.full_like(y, base), 1e-6, 1 - 1e-6)
    return {"brier": round(brier, 5), "logloss": round(ll, 5),
            "brier_base": round(float(np.mean((pb - y) ** 2)), 5),
            "logloss_base": round(float(-np.mean(y * np.log(pb) + (1 - y) * np.log(1 - pb))), 5),
            "auc": round(auc(p, y), 4)}


def auc(p, y):
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p))
    ps = np.asarray(p)[order]
    i = 0
    while i < len(ps):
        j = i
        while j + 1 < len(ps) and ps[j + 1] == ps[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    pos = y == 1
    n1, n0 = pos.sum(), (~pos).sum()
    return float((ranks[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")


def main(path):
    rows = load(path)
    train = [r for r in rows if r["split"] == "train" and r["label"] != ""]
    hold = [r for r in rows if r["split"] == "holdout"]
    hold_scored = [r for r in hold if r["label"] != ""]
    base = float(np.mean([float(r["label"]) for r in train]))
    liq_med = float(np.nanmedian([num(r["liq_usd"]) for r in train]))
    out = {"mesa_version": mesa.__version__, "n_train_labeled": len(train), "n_holdout": len(hold),
           "n_holdout_censored_excluded": len(hold) - len(hold_scored), "train_prevalence": round(base, 5),
           "T_steps": T_STEPS, "agents": N_AGENTS, "seeds_per_row": R_SEEDS}
    y = [float(r["label"]) for r in hold_scored]

    # S3 without imputation
    t0 = time.time()
    raw = [sim_freq(num(r["ret_1h"]), num(r["liq_usd"]), i) for i, r in enumerate(hold_scored)]
    out["S3_rows_with_nan_liq"] = sum(1 for r in hold_scored if r["liq_usd"] == "")
    out["S3_no_impute_freq_on_nan_rows"] = sorted({f for f, r in zip(raw, hold_scored) if r["liq_usd"] == ""})
    out["S3_note"] = "NaN liquidity gives a NaN price path; no barrier is ever touched, so the row silently scores 0"

    def liq(r):
        v = num(r["liq_usd"])
        return liq_med if math.isnan(v) else v

    legit = [sim_freq(num(r["ret_1h"]), liq(r), i) for i, r in enumerate(hold_scored)]
    t_legit = time.time() - t0
    trap = [sim_freq(num(r["leak_future_ret"]), liq(r), i) for i, r in enumerate(hold_scored)]
    again = [sim_freq(num(r["ret_1h"]), liq(r), i) for i, r in enumerate(hold_scored)]
    other_seed = [sim_freq(num(r["ret_1h"]), liq(r), i + 7919) for i, r in enumerate(hold_scored)]
    wall = time.time() - t0
    out["S1_legit"] = scores(legit, y, base)
    out["S1_trap_leak_future_ret"] = scores(trap, y, base)
    out["S1_library_guard"] = "none: Mesa accepts any number as agent input; availability time is the wrapper's job"
    out["S2_freq_min_max"] = [min(legit), max(legit)]
    out["S2_all_finite_in_0_1"] = all(0.0 <= f <= 1.0 and math.isfinite(f) for f in legit)
    out["S2_distinct_values"] = sorted(set(legit))
    out["S4_mean_freq_vs_prevalence"] = [round(float(np.mean(legit)), 4), round(float(np.mean(y)), 4)]
    q = np.quantile(legit, [1 / 3, 2 / 3])
    bins = []
    for lo, hi in [(-1, q[0]), (q[0], q[1]), (q[1], 2)]:
        idx = [k for k, f in enumerate(legit) if lo < f <= hi]
        if idx:
            bins.append({"n": len(idx), "mean_freq": round(float(np.mean([legit[k] for k in idx])), 4),
                         "observed": round(float(np.mean([y[k] for k in idx])), 4)})
    out["S4_reliability_3bins"] = bins
    h = lambda v: hashlib.sha256(json.dumps(v).encode()).hexdigest()
    out["S5_same_seed_identical"] = h(legit) == h(again)
    out["S5_other_seed_identical"] = h(legit) == h(other_seed)
    out["S5_freq_sha256"] = h(legit)
    n_runs = 5 * len(hold_scored) * R_SEEDS
    out["S6_wall_s_total"] = round(wall, 2)
    out["S6_ms_per_model_run_legit_pass"] = round(1000 * t_legit / (2 * len(hold_scored) * R_SEEDS), 3)
    out["S6_model_runs"] = n_runs
    out["S6_peak_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
