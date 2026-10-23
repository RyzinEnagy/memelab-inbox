"""Phase 11: statistical validation and selection discipline (G06, G26, G27, G28). Synthetic, seeded data."""
import random

import pytest

from memelab.backtest import validation as V
from memelab.backtest.engine import EngineConfig, TokenData
from memelab.backtest.strategies.features import B
from memelab.backtest.timeguard import LeakageError

T = 1_800_000_000.0
H = 3600


def walk(seed, n=400, drift=0.0, vol=0.03):
    rng = random.Random(seed)
    p, out = 1.0, []
    for i in range(n):
        o = p
        c = max(1e-6, o * (1 + drift + rng.gauss(0, vol)))
        h = max(o, c) * (1 + abs(rng.gauss(0, 0.01)))
        l = min(o, c) * (1 - abs(rng.gauss(0, 0.01)))
        out.append(B(T + i * H, T + (i + 1) * H, o, h, l, c, 100 + rng.random() * 400, T + (i + 1) * H + 60))
        p = c
    return out


def universe(n_tok=30, n=400, seed=0, drift=0.0):
    snaps = [(T + d * 86400, 5_000_000.0) for d in range(n // 24 + 1)]          # a liquidity observation every day
    return [TokenData("solana", f"W{seed}_{k:02d}", walk(seed * 1000 + k, n, drift), liquidity=list(snaps)) for k in range(n_tok)]


CFG = EngineConfig(account_usd=1e7, size_usd=500, max_positions=1000, max_exposure_frac=1.0, sol_usd_default=150, latency_s=5, entry_impact_cap=0.05)
PLAN = V.SplitPlan.make(T, T + 400 * H, embargo_s=50 * H)


def test_seal_discipline():
    s = V.TestSeal()
    with pytest.raises(LeakageError):
        s.open({"a": 1})
    s.freeze({"a": 1})
    with pytest.raises(LeakageError):
        s.open({"a": 2})
    s.open({"a": 1})
    with pytest.raises(LeakageError):
        s.open({"a": 1})
    with pytest.raises(LeakageError):
        s.freeze({"a": 3})


def test_embargo_keeps_trades_inside_their_split():
    toks = universe(10)
    r = V.run_window(V.registry.make("BREAKOUT_CLOSE", lookback=12, vol_mult=0.0, max_hold_bars=40), toks, CFG, PLAN, "train")
    assert r["n_trades"] > 0
    assert all(t["exit_time"] <= PLAN.train_end for t in r["trades"])
    assert all(t["decision_time"] < PLAN.train_end - PLAN.embargo_s for t in r["trades"])


def test_g27_g28_noise_strategy_is_not_declared_profitable_and_winners_curse_reported():
    toks = universe(30, seed=3)
    grid = [{"p": 0.02, "seed": s} for s in range(12)]                  # 12 trials of pure noise
    rep = V.validate("RANDOM_ENTRY", grid, toks, CFG, PLAN, min_n_test=30)
    assert rep.trials == 12 and rep.frozen_sha
    assert rep.verdict in ("NO_EVIDENCE_OF_EDGE", "INSUFFICIENT_SAMPLE")
    assert set(rep.baselines) == {"NO_TRADE", "ENTER_AT_DISCOVERY", "RANDOM_ENTRY", "MA_CROSS"}
    assert rep.baselines["NO_TRADE"]["n"] == 0
    wc = rep.winners_curse
    assert wc["train_mean_ret"] is not None and wc["validation_mean_ret"] is not None
    best_train = max(t["train"].get("mean_ret", -9) for t in rep.tuning if t["train"].get("n", 0) >= 8)
    assert wc["train_mean_ret"] == best_train                            # the reported in-sample number is the selected maximum


def test_g26_tiny_sample_huge_win_rate_abstains():
    up = [TokenData("solana", "UP", walk(1, 400, drift=0.01, vol=0.001), liquidity=[(T + d * 86400, 5e6) for d in range(18)])]
    rep = V.validate("ENTER_AT_DISCOVERY", [{"hold_bars": 10}], up, CFG, PLAN, min_n_test=30)
    assert rep.verdict == "INSUFFICIENT_SAMPLE"
    assert rep.test["n"] <= 1


def test_g06_dead_token_counts_as_loss_not_dropped():
    live = walk(5, 400)
    dead_bars = walk(6, 260)                   # bars stop at hour 260: the token died
    toks = [TokenData("solana", "LIVE", live, liquidity=[(T, 5e6)]), TokenData("solana", "DEAD", dead_bars, liquidity=[(T, 5e6)])]
    cfg = EngineConfig(**{**CFG.__dict__, "liquidity_max_age_s": 24 * H})
    plan = V.SplitPlan.make(T, T + 400 * H, fractions=(0.5, 0.25, 0.25), embargo_s=10 * H)
    r = V.run_window(V.registry.make("ENTER_AT_DISCOVERY", hold_bars=500), toks, cfg, plan, "train")
    by = {t["mint"]: t for t in r["trades"]}
    assert "DEAD" in by and by["DEAD"]["ret"] == -1.0 and "NON_EXECUTABLE" in by["DEAD"]["exit_reason"]
    m = V.metrics(r["trades"])
    assert m["non_executable_exits"] >= 1 and m["worst_ret"] == -1.0


def test_statistics_helpers():
    assert V.wilson(10, 10)[1] == pytest.approx(1.0) and V.wilson(10, 10)[0] < 0.75   # 10/10 is not certainty
    assert V.holm({"a": 0.001, "b": 0.04, "c": 0.5}) == {"a": True, "b": False, "c": False}
    trades = [{"ret": 0.01, "exit_time": T + d * 86400 + k} for d in range(10) for k in range(3)]
    lo, hi = V.day_block_bootstrap(trades)
    assert lo == pytest.approx(0.01) and hi == pytest.approx(0.01)
    assert V.deflated_sharpe(0.5, 50, 0, 3, [0.1, 0.2]) is None           # too few observations: not computed
    assert 0 <= V.deflated_sharpe(0.3, 200, 0.0, 3.0, [0.0, 0.05, 0.1, 0.02]) <= 1


def test_validation_is_deterministic():
    toks = universe(8, seed=9)
    a = V.validate("BREAKOUT_CLOSE", [{"lookback": 12, "vol_mult": 0.0}, {"lookback": 24, "vol_mult": 0.0}], toks, CFG, PLAN, min_n_test=5)
    b = V.validate("BREAKOUT_CLOSE", [{"lookback": 12, "vol_mult": 0.0}, {"lookback": 24, "vol_mult": 0.0}], toks, CFG, PLAN, min_n_test=5)
    assert a.test == b.test and a.chosen == b.chosen and a.frozen_sha == b.frozen_sha


def test_walk_forward_never_tunes_on_its_out_of_sample_block():
    toks = universe(10, seed=21)
    wf = V.walk_forward("BREAKOUT_CLOSE", [{"lookback": 12, "vol_mult": 0.0}, {"lookback": 24, "vol_mult": 0.0}], toks, CFG, T, T + 400 * H, folds=3, embargo_s=50 * H)
    assert len(wf["folds"]) == 3
    for f in wf["folds"]:
        assert f["tune_until"] < f["oos_window"][0]                  # an embargo separates tuning from the block it is judged on
    assert wf["pooled_oos"]["n"] == sum(f["oos"].get("n", 0) for f in wf["folds"])


def test_overfit_control_best_of_many_noise_seeds_is_flagged():
    toks = universe(30, seed=5)
    grid = [{"p": 0.03, "seed": s} for s in range(24)]               # pick the luckiest of 24 random-entry seeds
    rep = V.validate("RANDOM_ENTRY", grid, toks, CFG, PLAN, min_n_test=30)
    assert rep.verdict != "CANDIDATE_EDGE_OUT_OF_SAMPLE"
    assert rep.winners_curse["selection_from_trials"] == 24
    assert rep.winners_curse["train_mean_ret"] >= max(t["train"].get("mean_ret", -9) for t in rep.tuning if t["train"].get("n", 0) >= 8)


def test_regime_breakdown_uses_only_prices_known_at_entry():
    trades = [{"ret": 0.1, "entry_time": T + 100 * H, "exit_time": T + 110 * H, "mint": "A"},
              {"ret": -0.1, "entry_time": T + 260 * H, "exit_time": T + 270 * H, "mint": "B"}]
    sol = lambda t: 100.0 if t < T + 250 * H else 80.0                  # SOL drops at hour 250
    rb = V.regime_breakdown(trades, sol)
    assert rb["SOL_UP_24H"]["n"] == 1 and rb["SOL_DOWN_24H"]["n"] == 1 and rb["SOL_DOWN_24H"]["mean_ret"] == -0.1
    late = lambda t: 100.0 if t < T + 261 * H else 80.0                 # a drop one hour AFTER entry must not relabel the trade
    assert V.regime_breakdown(trades, late)["SOL_DOWN_24H"]["n"] == 0


def test_g26_few_days_and_few_trades_never_produce_significance():
    """Found on real data: 6 sealed-test trades over 3 days gave a 'significant' Holm result before this rule."""
    trades = [{"ret": 0.03 + 0.001 * k, "exit_time": T + d * 86400 + k} for d in range(3) for k in range(2)]
    assert V.day_block_bootstrap(trades) is None and V.bootstrap_p_mean_le_zero(trades) is None
    rep = V.ValidationReport("TINY", {}, 1, test={"n": 6, "p_mean_le_0": 0.0005})
    big = V.ValidationReport("BIG", {}, 1, test={"n": 40, "p_mean_le_0": 0.01})
    cmp = V.compare_strategies([rep, big])
    assert "TINY" not in cmp["pvalues"] and cmp["not_tested_insufficient_sample"] == ["TINY"] and cmp["holm_reject_h0"] == {"BIG": True}


def test_overfit_flag_fires_when_training_gains_vanish_out_of_sample():
    def regime_walk(seed, n=400):
        rng = random.Random(seed)
        p, out = 1.0, []
        for i in range(n):
            drift = 0.006 if i < 200 else -0.006                       # what worked in training stops working
            o = p
            c = max(1e-6, o * (1 + drift + rng.gauss(0, 0.004)))
            out.append(B(T + i * H, T + (i + 1) * H, o, max(o, c) * 1.002, min(o, c) * 0.998, c, 300.0, T + (i + 1) * H + 60))
            p = c
        return out
    snaps = [(T + d * 86400, 5_000_000.0) for d in range(18)]
    toks = [TokenData("solana", f"R{k:02d}", regime_walk(k), liquidity=list(snaps)) for k in range(30)]
    grid = [{"p": 0.03, "seed": s, "stop_frac": 0.5, "tp_r": None, "max_hold_bars": 12} for s in range(12)]
    rep = V.validate("RANDOM_ENTRY", grid, toks, CFG, PLAN, min_n_test=30)
    assert rep.winners_curse["train_mean_ret"] > 0 and rep.winners_curse["overfit_flag"]
    assert rep.verdict != "CANDIDATE_EDGE_OUT_OF_SAMPLE" and any("OVERFIT_FLAG" in n for n in rep.notes)


def test_tuning_reads_only_the_training_window_and_the_test_once(monkeypatch):
    calls = []
    real = V.run_window

    def spy(strategy, tokens, cfg, plan, name, sol_usd=None):
        calls.append((strategy.id, name))
        return real(strategy, tokens, cfg, plan, name, sol_usd)
    monkeypatch.setattr(V, "run_window", spy)
    toks = universe(6, seed=31)
    V.validate("BREAKOUT_CLOSE", [{"lookback": 12, "vol_mult": 0.0}, {"lookback": 24, "vol_mult": 0.0}], toks, CFG, PLAN, min_n_test=5)
    own = [n for sid, n in calls if sid == "BREAKOUT_CLOSE"]
    assert own == ["train", "train", "validation", "test"]                  # grid on train only, then one look at each later window
    assert all(n == "test" for sid, n in calls if sid != "BREAKOUT_CLOSE")  # baselines only on the sealed test


def test_a_window_never_reads_past_its_end():
    """Phase 16 M16-13: a position open at the window end is truncated there, never carried on later bars."""
    from memelab.backtest.strategies.base import Exits, Signal, Strategy

    class HoldForever(Strategy):
        id, version = "HOLD_FOREVER", "1"
        default_params = {}

        def evaluate(self, chain, mint, bars, d, ctx=None):
            if len(bars) != 12:
                return None
            last = bars[-1]
            return Signal(self.id, self.version, chain, mint, last.end, d, "BUY", Exits(None, max_hold_s=10_000 * H), {}, self.phash, "test",
                          latest_input_available_at=last.avail)
    toks = universe(3, seed=77)
    for name in ("train", "validation", "test"):
        a, b = PLAN.window(name)
        r = V.run_window(HoldForever(), toks, CFG, PLAN, name)
        assert all(f["fill_time"] is None or f["fill_time"] <= b for f in r["fills"])
        assert all(t["exit_time"] <= b for t in r["trades"])
        assert all(j["t"] <= b for j in r["journal"])
    tr = V.run_window(HoldForever(), toks, CFG, PLAN, "train")["trades"]
    assert tr and all(t["exit_reason"].startswith("TRUNCATED_AT_CUTOFF") for t in tr)
