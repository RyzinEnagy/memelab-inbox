"""Statistical validation and strategy-selection discipline.

- Chronological blocked splits (train / validation / sealed test) over decision time, with an embargo before each
  split end so no trade's holding period reads data from the next split.
- Tuning sees only the training window. The chosen configuration is frozen (sha256) before the sealed test can be
  evaluated, and the test can be evaluated once per frozen configuration (TestSeal).
- Every configuration tried is counted (trials). Baselines run under the same universe, engine, execution and costs.
- Uncertainty: block bootstrap by calendar day (trades on one day are dependent), Wilson interval for win rate,
  Holm correction across the strategies compared. Deflated Sharpe only when the sample supports it.
- Verdicts are conservative: INSUFFICIENT_SAMPLE, NO_EVIDENCE_OF_EDGE, CANDIDATE_EDGE_OUT_OF_SAMPLE. Nothing is ever
  "profitable" on an in-sample curve.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from dataclasses import dataclass, field
from statistics import NormalDist

from .engine import Engine, EngineConfig, TokenData
from .strategies import registry
from .timeguard import LeakageError

N = NormalDist()


@dataclass(frozen=True)
class SplitPlan:
    start: float
    train_end: float
    valid_end: float
    end: float
    embargo_s: float

    @staticmethod
    def make(t0: float, t1: float, fractions=(0.5, 0.25, 0.25), embargo_s: float = 2 * 86400) -> "SplitPlan":
        if t1 <= t0 or abs(sum(fractions) - 1) > 1e-9:
            raise ValueError("bad split range or fractions")
        span = t1 - t0
        return SplitPlan(t0, t0 + fractions[0] * span, t0 + (fractions[0] + fractions[1]) * span, t1, embargo_s)

    def window(self, name: str) -> tuple[float, float]:
        return {"train": (self.start, self.train_end), "validation": (self.train_end, self.valid_end), "test": (self.valid_end, self.end)}[name]

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def run_window(strategy, tokens: list[TokenData], cfg: EngineConfig, plan: SplitPlan, name: str, sol_usd=None) -> dict:
    a, b = plan.window(name)
    # decisions stop one embargo before the window end; nothing after the window end is read
    return Engine(cfg, sol_usd).run(strategy, tokens, until=b, decide_from=a, decide_until=max(a, b - plan.embargo_s))


def metrics(trades: list[dict]) -> dict:
    rets = [t["ret"] for t in trades if t.get("ret") is not None]
    n = len(rets)
    if n == 0:
        return {"n": 0}
    wins = sum(1 for r in rets if r > 0)
    gains, losses = sum(r for r in rets if r > 0), -sum(r for r in rets if r < 0)
    cum, peak, mdd = 0.0, 0.0, 0.0      # cumulative return in units of one fixed stake, in exit order
    for t in sorted(trades, key=lambda x: (x["exit_time"], x["mint"])):
        if t.get("ret") is None:
            continue
        cum += t["ret"]
        peak = max(peak, cum)
        mdd = max(mdd, peak - cum)
    srt = sorted(rets)
    sd = statistics.pstdev(rets) if n > 1 else 0.0
    return {"n": n, "mean_ret": sum(rets) / n, "median_ret": statistics.median(rets), "win_rate": wins / n, "win_rate_wilson95": wilson(wins, n),
            "profit_factor": (gains / losses) if losses > 0 else None, "p05_ret": srt[max(0, int(0.05 * n) - 1)] if n >= 20 else None,
            "worst_ret": srt[0], "best_ret": srt[-1], "max_drawdown_stakes": mdd, "sum_ret_stakes": cum, "sharpe_per_trade": (sum(rets) / n / sd) if sd > 0 else None,
            "non_executable_exits": sum(1 for t in trades if "NON_EXECUTABLE" in (t.get("exit_reason") or ""))}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


MIN_DAY_BLOCKS = 5     # fewer independent days than this cannot support an interval or a p-value (G26)


def day_block_bootstrap(trades: list[dict], n_boot: int = 2000, seed: int = 11, alpha: float = 0.05) -> tuple[float, float] | None:
    """Percentile CI of the mean trade return, resampling whole UTC days of exits (dependence-aware). None when there
    are fewer than MIN_DAY_BLOCKS days with exits: two or three days give falsely narrow intervals."""
    by_day: dict[int, list[float]] = {}
    for t in trades:
        if t.get("ret") is not None:
            by_day.setdefault(int(t["exit_time"] // 86400), []).append(t["ret"])
    days = sorted(by_day)
    if len(days) < MIN_DAY_BLOCKS:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        pick = [rng.choice(days) for _ in days]
        vals = [r for d in pick for r in by_day[d]]
        means.append(sum(vals) / len(vals))
    means.sort()
    return means[int(alpha / 2 * n_boot)], means[int((1 - alpha / 2) * n_boot) - 1]


def holm(pvals: dict[str, float], alpha: float = 0.05) -> dict[str, bool]:
    order = sorted(pvals, key=pvals.get)
    m, out, stop = len(order), {}, False
    for i, k in enumerate(order):
        if stop or pvals[k] > alpha / (m - i):
            stop = True
            out[k] = False
        else:
            out[k] = True
    return out


def bootstrap_p_mean_le_zero(trades: list[dict], n_boot: int = 2000, seed: int = 13) -> float | None:
    """One-sided bootstrap p-value for H0: mean trade return <= 0 (day blocks)."""
    by_day: dict[int, list[float]] = {}
    for t in trades:
        if t.get("ret") is not None:
            by_day.setdefault(int(t["exit_time"] // 86400), []).append(t["ret"])
    days = sorted(by_day)
    if len(days) < MIN_DAY_BLOCKS:
        return None
    allr = [r for d in days for r in by_day[d]]
    mu = sum(allr) / len(allr)
    rng = random.Random(seed)
    cnt = 0
    for _ in range(n_boot):
        vals = [r - mu for d in (rng.choice(days) for _ in days) for r in by_day[d]]   # centered under H0
        if sum(vals) / len(vals) >= mu:
            cnt += 1
    return (cnt + 1) / (n_boot + 1)


def deflated_sharpe(sr: float, n: int, skew: float, kurt: float, trial_srs: list[float]) -> float | None:
    """Bailey & Lopez de Prado deflated Sharpe ratio (probability the true SR exceeds the expected max of noise trials).
    Returned only when n >= 100 and at least 2 trials; otherwise None (no invented precision)."""
    if n < 100 or len(trial_srs) < 2:
        return None
    v = statistics.pvariance(trial_srs)
    k = len(trial_srs)
    g = 0.5772156649
    sr0 = math.sqrt(v) * ((1 - g) * N.inv_cdf(1 - 1 / k) + g * N.inv_cdf(1 - 1 / (k * math.e)))
    den = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr * sr))
    return N.cdf((sr - sr0) * math.sqrt(n - 1) / den)


class TestSeal:
    """The sealed test may be read once, only for the configuration frozen before it."""

    def __init__(self):
        self.frozen: str | None = None
        self.used = False

    @staticmethod
    def sha(cfg: dict) -> str:
        return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()

    def freeze(self, cfg: dict) -> str:
        if self.frozen:
            raise LeakageError("configuration already frozen; re-freezing after seeing results is not allowed")
        self.frozen = self.sha(cfg)
        return self.frozen

    def open(self, cfg: dict) -> None:
        if not self.frozen:
            raise LeakageError("sealed test requested before the configuration was frozen")
        if self.sha(cfg) != self.frozen:
            raise LeakageError("sealed test requested for a configuration other than the frozen one")
        if self.used:
            raise LeakageError("sealed test already used for this frozen configuration")
        self.used = True


@dataclass
class ValidationReport:
    strategy_id: str
    plan: dict
    trials: int
    tuning: list = field(default_factory=list)
    chosen: dict | None = None
    frozen_sha: str | None = None
    validation: dict | None = None
    test: dict | None = None
    baselines: dict = field(default_factory=dict)
    winners_curse: dict | None = None
    verdict: str = "NOT_RUN"
    notes: list = field(default_factory=list)


def validate(strategy_id: str, grid: list[dict], tokens: list[TokenData], cfg: EngineConfig, plan: SplitPlan,
             baselines=("NO_TRADE", "ENTER_AT_DISCOVERY", "RANDOM_ENTRY", "MA_CROSS"), min_n_tune: int = 8, min_n_test: int = 30,
             sol_usd=None, seal: TestSeal | None = None) -> ValidationReport:
    rep = ValidationReport(strategy_id, plan.as_dict(), trials=len(grid))
    seal = seal or TestSeal()
    # 1. tune on train only
    best, best_score = None, -math.inf
    for params in grid:
        r = run_window(registry.make(strategy_id, **params), tokens, cfg, plan, "train", sol_usd)
        m = metrics(r["trades"])
        rep.tuning.append({"params": params, "train": m})
        score = m.get("mean_ret") if m.get("n", 0) >= min_n_tune else -math.inf
        if score is not None and score > best_score:
            best, best_score = params, score
    if best is None:
        best = grid[0]
        rep.notes.append(f"no configuration reached {min_n_tune} training trades; first grid point frozen without tuning")
    rep.chosen = best
    rep.frozen_sha = seal.freeze({"strategy": strategy_id, "params": best})
    # 2. validation (selection already made: report only)
    rv = run_window(registry.make(strategy_id, **best), tokens, cfg, plan, "validation", sol_usd)
    rep.validation = metrics(rv["trades"])
    train_m = next(t["train"] for t in rep.tuning if t["params"] == best)
    rep.winners_curse = {"train_mean_ret": train_m.get("mean_ret"), "validation_mean_ret": rep.validation.get("mean_ret"),
                         "drop": (train_m.get("mean_ret") or 0) - (rep.validation.get("mean_ret") or 0) if rep.validation.get("n") else None,
                         "overfit_flag": bool(train_m.get("mean_ret") is not None and train_m["mean_ret"] > 0 and (
                             (rep.validation.get("n") and rep.validation.get("mean_ret") is not None and rep.validation["mean_ret"] < train_m["mean_ret"] / 2)
                             or (len(grid) >= 10 and not rep.validation.get("n")))),
                         "selection_from_trials": len(grid)}
    if rep.winners_curse["overfit_flag"]:
        rep.notes.append("OVERFIT_FLAG: the selected configuration lost more than half its training mean out of sample (or traded nothing there after a large search)")
    # 3. sealed test, once, frozen config; baselines (not tuned) on the same window
    seal.open({"strategy": strategy_id, "params": best})
    rt = run_window(registry.make(strategy_id, **best), tokens, cfg, plan, "test", sol_usd)
    tm = metrics(rt["trades"])
    tm["bootstrap95_mean_ret"] = day_block_bootstrap(rt["trades"])
    tm["p_mean_le_0"] = bootstrap_p_mean_le_zero(rt["trades"])
    rep.test = tm
    for b in baselines:
        rb = run_window(registry.make(b), tokens, cfg, plan, "test", sol_usd)
        bm = metrics(rb["trades"])
        bm["bootstrap95_mean_ret"] = day_block_bootstrap(rb["trades"])
        rep.baselines[b] = bm
    # 4. verdict
    if tm.get("n", 0) < min_n_test:
        rep.verdict = "INSUFFICIENT_SAMPLE"
        rep.notes.append(f"sealed test has {tm.get('n', 0)} trades < {min_n_test}; no performance claim")
        return rep
    ci = tm.get("bootstrap95_mean_ret")
    best_base = max((v.get("mean_ret") for v in rep.baselines.values() if v.get("n")), default=0.0)
    if ci and ci[0] > 0 and ci[0] > (best_base or 0.0) and not rep.winners_curse["overfit_flag"]:
        rep.verdict = "CANDIDATE_EDGE_OUT_OF_SAMPLE"
    else:
        rep.verdict = "NO_EVIDENCE_OF_EDGE"
    return rep


def compare_strategies(reports: list[ValidationReport], alpha: float = 0.05, min_n_test: int = 30) -> dict:
    """Holm correction across strategies on the sealed-test one-sided p-values. A strategy whose sealed test is below
    the minimum sample is listed as not tested; it never enters (or wins) the significance comparison (G26)."""
    eligible = [r for r in reports if r.test and (r.test.get("n") or 0) >= min_n_test and r.test.get("p_mean_le_0") is not None]
    p = {r.strategy_id: r.test["p_mean_le_0"] for r in eligible}
    return {"pvalues": p, "holm_reject_h0": holm(p, alpha) if p else {}, "alpha": alpha, "strategies_compared": len(reports),
            "not_tested_insufficient_sample": sorted(r.strategy_id for r in reports if r not in eligible)}


def report_dict(rep: ValidationReport) -> dict:
    return dict(rep.__dict__)


def regime_breakdown(trades: list[dict], sol_usd, lookback_s: float = 86400.0) -> dict:
    """Split trades by the SOL/USD move over the day before entry (as known then): UP, DOWN, UNKNOWN."""
    out: dict[str, list[dict]] = {"SOL_UP_24H": [], "SOL_DOWN_24H": [], "UNKNOWN": []}
    for t in trades:
        a, b = sol_usd(t["entry_time"] - lookback_s), sol_usd(t["entry_time"])
        k = "UNKNOWN" if not a or not b else ("SOL_UP_24H" if b >= a else "SOL_DOWN_24H")
        out[k].append(t)
    return {k: metrics(v) for k, v in out.items()}


def walk_forward(strategy_id: str, grid: list[dict], tokens: list[TokenData], cfg: EngineConfig, t0: float, t1: float, folds: int,
                 embargo_s: float, min_n_tune: int = 5, sol_usd=None) -> dict:
    """Expanding-window walk-forward: for fold k, tune on [t0, cut_k - embargo] and evaluate the frozen choice on
    [cut_k, cut_k + step). Every fold's out-of-sample block is new data; nothing tunes on it."""
    step = (t1 - t0) / (folds + 1)
    res = []
    for k in range(1, folds + 1):
        cut = t0 + k * step
        tune_until = cut - embargo_s                  # tuning decisions stop one embargo before the out-of-sample block
        best, best_score = grid[0], -math.inf
        for params in grid:
            r = Engine(cfg, sol_usd).run(registry.make(strategy_id, **params), tokens, until=cut, decide_from=t0, decide_until=tune_until)
            m = metrics(r["trades"])
            sc = m.get("mean_ret") if m.get("n", 0) >= min_n_tune else -math.inf
            if sc is not None and sc > best_score:
                best, best_score = params, sc
        o = Engine(cfg, sol_usd).run(registry.make(strategy_id, **best), tokens, until=min(t1, cut + step), decide_from=cut,
                                     decide_until=min(t1, cut + step) - embargo_s)
        res.append({"fold": k, "tune_until": tune_until, "oos_window": [cut, min(t1, cut + step)], "chosen": best,
                    "in_sample_mean_ret": None if best_score == -math.inf else best_score, "oos": metrics(o["trades"]), "oos_trades": o["trades"]})
    allo = [t for f in res for t in f["oos_trades"]]
    for f in res:
        f.pop("oos_trades")
    return {"strategy": strategy_id, "folds": res, "pooled_oos": metrics(allo), "pooled_oos_bootstrap95": day_block_bootstrap(allo), "trials_per_fold": len(grid)}
