"""Phase 04 behavioral comparator check: one LLM-free trader-reaction model written twice, with Mesa 3.5.1 agents and as a
plain numpy loop, run on the same synthetic scenario seeds. Both outputs are simulator frequencies over seeded randomness
(SIMULATOR_FREQUENCY_NOT_A_PROBABILITY, P27): they are compared for determinism, cost and agreement of their own distribution,
never scored as forecasts.

Model (written for the lab, after the Phase 03 reviewer's design in REVIEWS/mesa__mesa.md): 20 traders (8 momentum,
5 contrarian, 4 noise, 3 take-profit exiters) with seeded thresholds and sizes react to a decaying signal for 12 steps; the
price moves with net demand scaled by log liquidity plus seeded noise; a run hits when the price touches 1.25 before 0.85.

    python behavior_check.py numpy|mesa [N_SCENARIOS] [R_SEEDS]
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time

import numpy as np

T_STEPS, KINDS = 12, ["momentum"] * 8 + ["contrarian"] * 5 + ["noise"] * 4 + ["exiter"] * 3
SEED = 20261024


def scenarios(n: int) -> list[tuple[float, float]]:
    rng = np.random.default_rng(SEED)
    return [(float(rng.normal(0.01, 0.08)), float(math.exp(rng.normal(11, 1.2)))) for _ in range(n)]


def run_numpy(signal: float, liq: float, seed: int) -> int | None:
    rng = np.random.default_rng(seed)
    kinds = np.array(KINDS)
    thr = rng.uniform(0.0, 0.12, len(KINDS))
    size = rng.uniform(0.5, 1.5, len(KINDS))
    scale = math.log10(liq)
    price, last, sig = 1.0, 0.0, signal
    for _ in range(T_STEPS):
        order = rng.permutation(len(KINDS))
        demand = 0.0
        for i in order:
            k = kinds[i]
            if k == "momentum":
                x = sig + last
                d = 1 if x > thr[i] else (-1 if x < -thr[i] else 0)
            elif k == "contrarian":
                d = -1 if last > thr[i] else (1 if last < -thr[i] else 0)
            elif k == "exiter":
                d = -1 if price > 1.0 + thr[i] else 0
            else:
                d = int(rng.integers(-1, 2))
            demand += d * size[i]
        ret = 0.02 * demand / scale + float(rng.normal(0, 0.03))
        price *= math.exp(ret)
        last, sig = ret, sig * 0.7
        if price >= 1.25:
            return 1
        if price <= 0.85:
            return 0
    return None


_MESA = {}


def _mesa_classes():
    if _MESA:
        return _MESA["Market"]
    import mesa

    class Trader(mesa.Agent):
        def __init__(self, model, kind, thresh, size):
            super().__init__(model)
            self.kind, self.thresh, self.size = kind, thresh, size

        def step(self):
            m = self.model
            if self.kind == "momentum":
                x = m.signal + m.last
                d = 1 if x > self.thresh else (-1 if x < -self.thresh else 0)
            elif self.kind == "contrarian":
                d = -1 if m.last > self.thresh else (1 if m.last < -self.thresh else 0)
            elif self.kind == "exiter":
                d = -1 if m.price > 1.0 + self.thresh else 0
            else:
                d = int(m.rng.integers(-1, 2))
            m.demand += d * self.size

    class Market(mesa.Model):
        def __init__(self, signal, liq, seed):
            super().__init__(rng=seed)
            self.signal, self.scale, self.price, self.last, self.demand = signal, math.log10(liq), 1.0, 0.0, 0.0
            for k in KINDS:
                Trader(self, k, float(self.rng.uniform(0.0, 0.12)), float(self.rng.uniform(0.5, 1.5)))

        def step(self):
            self.demand = 0.0
            self.agents.shuffle_do("step")
            ret = 0.02 * self.demand / self.scale + float(self.rng.normal(0, 0.03))
            self.price *= math.exp(ret)
            self.last, self.signal = ret, self.signal * 0.7

    _MESA["Market"] = Market
    return Market


def run_mesa(signal: float, liq: float, seed: int) -> int | None:
    m = _mesa_classes()(signal, liq, seed)
    for _ in range(T_STEPS):
        m.step()
        if m.price >= 1.25:
            return 1
        if m.price <= 0.85:
            return 0
    return None


def main() -> None:
    impl = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    r = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    f = run_numpy if impl == "numpy" else run_mesa
    t0 = time.perf_counter()
    freqs = []
    for j, (sig, liq) in enumerate(scenarios(n)):
        hits = [f(sig, liq, SEED * 1000 + j * r + k) for k in range(r)]
        freqs.append(sum(1 for h in hits if h == 1) / r)
    wall = time.perf_counter() - t0
    out = {"impl": impl, "scenarios": n, "seeds_per_scenario": r, "kind": "SIMULATOR_FREQUENCY_NOT_A_PROBABILITY",
           "mean_hit_share": round(float(np.mean(freqs)), 4), "share_of_scenarios_with_any_hit": round(float(np.mean([x > 0 for x in freqs])), 4),
           "frequencies_sha256": hashlib.sha256(json.dumps(freqs).encode()).hexdigest()}
    print(json.dumps(out, sort_keys=True))
    print(json.dumps({"ms_per_model_run": round(1000 * wall / (n * r), 3)}), file=sys.stderr)


if __name__ == "__main__":
    main()
