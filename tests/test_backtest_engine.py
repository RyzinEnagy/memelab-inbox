"""Phase 10: deterministic event and portfolio core (G24, G25, G28, G29, G35 plus order lifecycle). Synthetic data."""
import json
from pathlib import Path

import pytest

from memelab.backtest import execution as X
from memelab.backtest.engine import Engine, EngineConfig, TokenData
from memelab.backtest.strategies import registry
from memelab.backtest.strategies.base import Exits, Signal, Strategy
from memelab.backtest.strategies.features import B

ROOT = Path(__file__).resolve().parent.parent
T = 1_800_000_000.0
H = 3600


def mk(rows, t0=T, lag=0.0):
    return [B(t0 + i * H, t0 + (i + 1) * H, o, h, l, c, v, t0 + (i + 1) * H + lag) for i, (o, h, l, c, v) in enumerate(rows)]


class SignalAt(Strategy):
    """test strategy: signal when the closed bar index equals `at`, with an absolute stop and optional R target"""
    id, version = "TEST_AT", "1"
    default_params = {"at": 20, "stop": None, "stop_frac": None, "tp_r": None, "hold": None}

    def evaluate(self, chain, mint, bars, d, ctx=None):
        if len(bars) - 1 != self.params["at"]:
            return None
        last = bars[-1]
        stop = self.params["stop"] if self.params["stop"] is not None else (last.c * (1 - self.params["stop_frac"]) if self.params["stop_frac"] else None)
        return Signal(self.id, self.version, chain, mint, last.end, d, "BUY", Exits(stop, take_profit_r=self.params["tp_r"],
                      max_hold_s=self.params["hold"] * H if self.params["hold"] else None), {}, self.phash, "test", latest_input_available_at=last.avail)


def bakeoff_tokens():
    d = json.loads((ROOT / "audits" / "backtesting" / "bakeoff" / "dataset.json").read_text()) if (ROOT / "audits/backtesting/bakeoff/dataset.json").exists() else None
    return d


# G29: the engine reproduces the independent bake-off oracle on the canonical dataset (flat paper model)
def test_g29_engine_matches_bakeoff_oracle():
    d = bakeoff_tokens()
    if d is None:
        pytest.skip("bake-off dataset not present")
    oracle = json.loads((ROOT / "audits/backtesting/bakeoff/oracle_expected.json").read_text())
    rows = [(b["o"], b["h"], b["l"], b["c"], b["v"]) for b in d["bars"]]
    td = TokenData("solana", d["mint"], mk(rows, t0=d["bars"][0]["t"]))
    cfg = EngineConfig(account_usd=100_000, size_usd=1000.0, latency_s=0.0, fill_model="FLAT", fees=X.Fees(0.0025, 0, None, 0.0), max_exposure_frac=1.0,
                       entry_impact_cap=1.0, sol_usd_default=150.0)
    # stop 10% below the planned entry 1.11 = 0.999 (as in the bake-off)
    r = Engine(cfg).run(SignalAt(at=20, stop=0.999), [td])
    tr = r["trades"][0]
    assert tr["entry_mid"] == 1.11 and tr["exit_ref_price"] == 0.95 and tr["exit_reason"] == "STOP_GAP_FILL_AT_OPEN"
    assert tr["proceeds_usd"] == pytest.approx(oracle["A_noimpact_1000"]["proceeds"], rel=1e-9)


# G25: stop gaps through, realized loss exceeds the intended stop risk
def test_g25_gap_through_stop():
    rows = [(1.0, 1.01, 0.99, 1.0, 100)] * 21 + [(1.0, 1.01, 0.99, 1.0, 100), (0.6, 0.62, 0.55, 0.58, 100)] + [(0.58, 0.6, 0.57, 0.58, 100)] * 5
    td = TokenData("solana", "GAP", mk(rows))
    cfg = EngineConfig(fill_model="FLAT", fees=X.Fees(0.0, 0, None, 0.0), sol_usd_default=150, latency_s=0)
    r = Engine(cfg).run(SignalAt(at=20, stop_frac=0.10), [td])
    tr = r["trades"][0]
    assert tr["exit_reason"] == "STOP_GAP_FILL_AT_OPEN" and tr["exit_ref_price"] == 0.6
    assert tr["ret"] == pytest.approx(-0.40, abs=1e-9) and tr["ret"] < -0.10


def test_stop_before_target_in_same_bar_and_target_alone():
    rows = [(1.0, 1.01, 0.99, 1.0, 100)] * 22 + [(1.0, 1.5, 0.8, 1.0, 100)] + [(1.0, 1.01, 0.99, 1.0, 100)] * 3
    td = TokenData("solana", "BOTH", mk(rows))
    cfg = EngineConfig(fill_model="FLAT", fees=X.Fees(0.0, 0, None, 0.0), sol_usd_default=150, latency_s=0)
    tr = Engine(cfg).run(SignalAt(at=20, stop_frac=0.1, tp_r=2.0), [td])["trades"][0]
    assert tr["exit_reason"].startswith("STOP_INTRABAR_BOTH_IN_BAR") and tr["exit_ref_price"] == pytest.approx(0.9)
    rows2 = [(1.0, 1.01, 0.99, 1.0, 100)] * 22 + [(1.0, 1.5, 0.95, 1.2, 100)] + [(1.0, 1.01, 0.99, 1.0, 100)] * 3
    tr2 = Engine(cfg).run(SignalAt(at=20, stop_frac=0.1, tp_r=2.0), [TokenData("solana", "TP", mk(rows2))])["trades"][0]
    assert tr2["exit_reason"] == "TAKE_PROFIT_INTRABAR" and tr2["exit_ref_price"] == pytest.approx(1.2)


# G24: 50 simultaneous signals compete for capital and limits; cash and limits are conserved
def test_g24_competing_signals_conserve_cash_and_limits():
    rows = [(1.0, 1.01, 0.99, 1.0, 100)] * 21 + [(1.0, 1.02, 0.98, 1.01, 100)] * 30
    toks = [TokenData("solana", f"M{i:02d}", mk(rows), liquidity=[(T, 1_000_000.0)]) for i in range(50)]
    cfg = EngineConfig(account_usd=5_000, size_usd=500, max_positions=5, max_exposure_frac=0.6, sol_usd_default=150, latency_s=0)
    r = Engine(cfg).run(SignalAt(at=20, stop_frac=0.5, hold=5), toks)
    assert r["counts"]["signals"] == 50 and r["counts"]["filled"] == 5          # max positions binds
    assert r["counts"]["rejected_limits"] == 45
    assert sorted(t["mint"] for t in r["trades"]) == [f"M{i:02d}" for i in range(5)]   # deterministic tie-break by mint
    assert r["final_cash"] > 0
    # exposure binds: 0.5 x equity, where equity already reflects fees paid on earlier entries (4 fit, not 5)
    r2 = Engine(EngineConfig(account_usd=5_000, size_usd=500, max_positions=50, max_exposure_frac=0.5, sol_usd_default=150, latency_s=0)).run(SignalAt(at=20, stop_frac=0.5, hold=5), toks)
    assert r2["counts"]["filled"] == 4
    spent = sum(f["requested"] for f in r2["fills"] if f["action"] == "BUY" and f["status"] == "FILLED")
    assert spent <= 0.5 * 5_000


# G28: baselines under the same universe and execution
def test_g28_baselines_same_conditions():
    rows = [(1.0 + 0.001 * i, 1.01 + 0.001 * i, 0.99 + 0.001 * i, 1.0 + 0.001 * i, 100) for i in range(80)]
    toks = [TokenData("solana", f"B{i}", mk(rows), liquidity=[(T, 200_000.0)], universe_from=T + 10 * H) for i in range(4)]
    cfg = EngineConfig(sol_usd_default=150, latency_s=0)
    nt = Engine(cfg).run(registry.make("NO_TRADE"), toks)
    assert nt["n_trades"] == 0 and nt["pnl_usd"] == 0
    disc = Engine(cfg).run(registry.make("ENTER_AT_DISCOVERY", hold_bars=12), toks)
    assert disc["n_trades"] == 4 and all(t["entry_time"] >= T + 10 * H for t in disc["trades"])   # nothing before discovery
    rnd1 = Engine(cfg).run(registry.make("RANDOM_ENTRY", p=0.1, seed=5), toks)
    rnd2 = Engine(cfg).run(registry.make("RANDOM_ENTRY", p=0.1, seed=5), toks)
    assert rnd1["ledger_hash"] == rnd2["ledger_hash"]


# G35: a paper-profitable strategy turns negative after realistic exit costs
def test_g35_paper_profit_vs_realizable():
    rows = [(1.0, 1.01, 0.99, 1.0, 100)] * 21 + [(1.0 + 0.02 * k, 1.02 + 0.02 * k, 0.99 + 0.02 * k, 1.01 + 0.02 * k, 100) for k in range(12)]
    thin = TokenData("solana", "THIN", mk(rows), liquidity=[(T, 4_000.0)])
    paper = Engine(EngineConfig(fill_model="FLAT", sol_usd_default=150, latency_s=0, entry_impact_cap=1.0, size_usd=1000)).run(SignalAt(at=20, stop_frac=0.5, hold=10), [thin])
    real = Engine(EngineConfig(sol_usd_default=150, latency_s=0, entry_impact_cap=1.0, size_usd=1000)).run(SignalAt(at=20, stop_frac=0.5, hold=10), [thin])
    assert paper["trades"][0]["ret"] > 0.1
    assert real["trades"][0]["ret"] < 0
    assert real["trades"][0]["paper_ret_mid"] == pytest.approx(paper["trades"][0]["paper_ret_mid"])


def test_order_lifecycle_expired_canceled_nonexecutable():
    rows = [(1.0, 1.01, 0.99, 1.0, 100)] * 21
    cfg = EngineConfig(sol_usd_default=150, latency_s=0)
    end = Engine(cfg).run(SignalAt(at=20, stop_frac=0.1), [TokenData("solana", "END", mk(rows), liquidity=[(T, 1e6)])])
    assert end["counts"]["expired"] == 1 and end["n_trades"] == 0               # signal on the last bar: no fill
    rows2 = rows + [(1.0, 1.01, 0.99, 1.0, 100)] * 5
    noliq = Engine(cfg).run(SignalAt(at=20, stop_frac=0.1), [TokenData("solana", "NOLIQ", mk(rows2))])
    assert noliq["counts"]["canceled"] == 1 and noliq["fills"][0]["reason"].startswith("INSUFFICIENT_EXECUTION_DATA")
    clmm = Engine(cfg).run(SignalAt(at=20, stop_frac=0.1), [TokenData("solana", "CL", mk(rows2), liquidity=[(T, 1e6)], pool_type="CLMM")])
    assert clmm["fills"][0]["reason"] == "UNSUPPORTED_POOL"
    big = Engine(EngineConfig(sol_usd_default=150, latency_s=0, size_usd=900)).run(SignalAt(at=20, stop_frac=0.1), [TokenData("solana", "TINY", mk(rows2), liquidity=[(T, 10_000.0)])])
    assert big["counts"]["canceled"] == 1 and "entry impact" in big["fills"][0]["reason"]
    # liquidity disappears after entry (snapshot too old at exit): exit is NON_EXECUTABLE, realizable value 0
    long_rows = rows + [(1.0, 1.01, 0.99, 1.0, 100)] * 100
    gone = Engine(EngineConfig(sol_usd_default=150, latency_s=0, liquidity_max_age_s=24 * H)).run(SignalAt(at=20, stop_frac=0.5, hold=60), [TokenData("solana", "GONE", mk(long_rows), liquidity=[(T + 20 * H, 1e6)])])
    tr = gone["trades"][0]
    assert "NON_EXECUTABLE" in tr["exit_reason"] and tr["proceeds_usd"] == 0 and tr["ret"] == -1.0


def test_determinism_and_no_trading_before_discovery():
    rows = [(1.0 + 0.01 * (i % 5), 1.05 + 0.01 * (i % 5), 0.95, 1.0 + 0.01 * ((i + 1) % 5), 100 + i) for i in range(100)]
    toks = [TokenData("solana", f"D{i}", mk(rows), liquidity=[(T, 300_000.0)], universe_from=T + 50 * H) for i in range(3)]
    cfg = EngineConfig(sol_usd_default=150)
    a = Engine(cfg).run(registry.make("BREAKOUT_CLOSE", lookback=10, vol_mult=0.0), toks)
    b = Engine(cfg).run(registry.make("BREAKOUT_CLOSE", lookback=10, vol_mult=0.0), toks)
    assert a["ledger_hash"] == b["ledger_hash"]
    assert all(t["decision_time"] >= T + 50 * H for t in a["trades"])


def test_missing_sol_price_refuses_instead_of_guessing():
    rows = [(1.0, 1.01, 0.99, 1.0, 100)] * 26
    r = Engine(EngineConfig(sol_usd_default=None, latency_s=0)).run(SignalAt(at=20, stop_frac=0.1), [TokenData("solana", "NOSOL", mk(rows), liquidity=[(T, 1e6)])])
    assert r["counts"]["canceled"] == 1 and "SOL/USD" in r["fills"][0]["reason"]


def test_run_until_never_reads_past_cutoff():
    rows = [(1.0, 1.01, 0.99, 1.0, 100)] * 25 + [(5.0, 5.1, 4.9, 5.0, 100)] * 5   # a future spike after the cutoff
    td = TokenData("solana", "CUT", mk(rows), liquidity=[(T, 1e7)])
    cut = T + 25 * H
    r = Engine(EngineConfig(sol_usd_default=150, latency_s=0, fill_model="FLAT", fees=X.Fees(0, 0, None, 0.0))).run(SignalAt(at=20, stop_frac=0.5), [td], until=cut)
    tr = r["trades"][0]
    assert tr["exit_reason"].startswith("TRUNCATED_AT_CUTOFF") and tr["exit_ref_price"] == 1.0 and tr["exit_time"] <= cut


def test_bar_straddling_cutoff_is_not_applied():
    # bar 25 starts exactly at the cutoff and crashes intrabar; with the cutoff at its start it must not trigger the stop
    rows = [(1.0, 1.01, 0.99, 1.0, 100)] * 25 + [(1.0, 1.0, 0.1, 0.5, 100)] + [(0.5, 0.5, 0.5, 0.5, 100)] * 3
    td = TokenData("solana", "STRAD", mk(rows), liquidity=[(T, 1e7)])
    cut = T + 25 * H
    r = Engine(EngineConfig(sol_usd_default=150, latency_s=0, fill_model="FLAT", fees=X.Fees(0, 0, None, 0.0))).run(SignalAt(at=20, stop_frac=0.2), [td], until=cut)
    assert r["trades"][0]["exit_reason"].startswith("TRUNCATED_AT_CUTOFF")
    full = Engine(EngineConfig(sol_usd_default=150, latency_s=0, fill_model="FLAT", fees=X.Fees(0, 0, None, 0.0))).run(SignalAt(at=20, stop_frac=0.2), [td])
    assert full["trades"][0]["exit_reason"].startswith("STOP_INTRABAR")     # (a crash bar: filled at its close, Phase 10 rule)


# ---------------- portfolio limits added in Phase 10: correlated groups, account drawdown halt, order journal ----------------

def _flat_tokens(n, group=None, drop_at=None):
    toks = []
    for k in range(n):
        rows = [(1.0, 1.01, 0.99, 1.0, 100.0)] * 40
        if drop_at is not None:
            rows = rows[:drop_at] + [(0.5, 0.5, 0.45, 0.46, 100.0)] * (40 - drop_at)
        toks.append(TokenData("solana", f"G{k:02d}", mk(rows), liquidity=[(T, 5e6)], group=group))
    return toks


def test_correlated_group_cap():
    cfg = EngineConfig(account_usd=1e6, size_usd=100, max_positions=50, max_exposure_frac=1.0, sol_usd_default=150, max_positions_per_group=2)
    eng = Engine(cfg)
    res = eng.run(SignalAt(at=20, hold=5), _flat_tokens(5, group="creator:SAME"))
    assert res["counts"]["filled"] == 2
    assert sum(1 for j in res["journal"] if j["event"] == "REJECTED_LIMIT" and "correlated group" in j["reason"]) == 3
    res = Engine(cfg).run(SignalAt(at=20, hold=5), _flat_tokens(5, group=None))     # no group known: only the normal limits
    assert res["counts"]["filled"] == 5


def test_account_drawdown_halts_new_entries_but_keeps_managing_open_positions():
    early = [TokenData("solana", f"E{k}", mk([(1.0, 1.01, 0.99, 1.0, 100.0)] * 15 + [(0.3, 0.3, 0.29, 0.3, 100.0)] * 25), liquidity=[(T, 5e6)]) for k in range(3)]
    late = [TokenData("solana", "L0", mk([(1.0, 1.01, 0.99, 1.0, 100.0)] * 40), liquidity=[(T, 5e6)])]
    cfg = EngineConfig(account_usd=3000, size_usd=900, max_positions=10, max_exposure_frac=1.0, sol_usd_default=150, max_drawdown_frac=0.2)

    class Two(Strategy):
        id, version = "TEST_TWO", "1"
        default_params = {}

        def evaluate(self, chain, mint, bars, d, ctx=None):
            want = 10 if mint.startswith("E") else 30
            if len(bars) - 1 != want:
                return None
            last = bars[-1]
            return Signal(self.id, self.version, chain, mint, last.end, d, "BUY", Exits(None, max_hold_s=100 * H), {}, self.phash, "t", latest_input_available_at=last.avail)
    eng = Engine(cfg)
    res = eng.run(Two(), early + late)
    assert any(j["event"] == "HALT_NEW_ENTRIES" for j in res["journal"])
    assert not any(t["mint"] == "L0" for t in res["trades"])                     # the late entry was refused
    assert {t["mint"] for t in res["trades"]} == {"E0", "E1", "E2"}             # open positions were still managed and closed


def test_every_order_is_journaled_from_submission():
    eng = Engine(EngineConfig(sol_usd_default=150))
    res = eng.run(SignalAt(at=20, hold=3), _flat_tokens(2))
    subs = [j for j in res["journal"] if j["event"] == "SUBMITTED"]
    assert len(subs) == res["counts"]["submitted"] == 2
    for s in subs:
        later = [j for j in res["journal"] if j.get("order") == s["order"] and j["event"] != "SUBMITTED"]
        assert later and later[0]["event"] in ("FILLED_BUY", "CANCELED", "EXPIRED", "REJECTED_LIMIT")


def test_discovery_baseline_is_one_attempt_not_whenever_tradable():
    tok = TokenData("solana", "D0", mk([(1.0, 1.01, 0.99, 1.0, 100.0)] * 40), liquidity=[(T + 10 * H, 5e6)], universe_from=T)
    res = Engine(EngineConfig(sol_usd_default=150)).run(registry.make("ENTER_AT_DISCOVERY"), [tok])
    assert res["counts"]["submitted"] == 1 and res["n_trades"] == 0                # no liquidity at discovery: canceled, never retried


def test_backtest_package_has_no_trading_path():
    banned = ("sendTransaction", "sendRawTransaction", "signTransaction", "/swap/v1/swap", "Keypair", "private_key", "mnemonic", "seed phrase")
    for f in (ROOT / "memelab" / "backtest").rglob("*.py"):
        t = f.read_text()
        assert not any(b in t for b in banned), f


def test_crash_through_stop_inside_one_bar_fills_at_the_close_not_the_stop():
    rows = [(1.0, 1.01, 0.99, 1.0, 100.0)] * 22 + [(1.0, 1.0, 0.0002, 0.0003, 100.0)] + [(0.0003, 0.0003, 0.0003, 0.0003, 1.0)] * 10
    tok = TokenData("solana", "RUG", mk(rows), liquidity=[(T, 5e6)])
    res = Engine(EngineConfig(sol_usd_default=150)).run(SignalAt(at=20, stop_frac=0.2, hold=10), [tok])
    t = res["trades"][0]
    assert t["exit_reason"] == "STOP_INTRABAR_CRASH_FILL_AT_CLOSE" and t["ret"] < -0.99
    rows2 = [(1.0, 1.01, 0.99, 1.0, 100.0)] * 22 + [(1.0, 1.0, 0.75, 0.9, 100.0)] + [(0.9, 0.9, 0.9, 0.9, 1.0)] * 10
    t2 = Engine(EngineConfig(sol_usd_default=150)).run(SignalAt(at=20, stop_frac=0.2, hold=10), [TokenData("solana", "DIP", mk(rows2), liquidity=[(T, 5e6)])])["trades"][0]
    assert t2["exit_reason"] == "STOP_INTRABAR" and -0.25 < t2["ret"] < -0.19     # an ordinary stop still fills near the stop


def test_canceled_entry_after_submission_still_pays_the_network_fee():
    tok = TokenData("solana", "THIN", mk([(1.0, 1.01, 0.99, 1.0, 100.0)] * 30), liquidity=[(T, 2_000.0)])     # far too thin for 500 USD
    cfg = EngineConfig(sol_usd_default=150, size_usd=500)
    res = Engine(cfg).run(SignalAt(at=20), [tok])
    assert res["counts"]["canceled"] == 1 and res["n_trades"] == 0
    assert res["final_cash"] == pytest.approx(cfg.account_usd - cfg.fees.network_fee_sol * 150)


# G06: a delisted token is never filled after its delisting, and a held position is exited at the delisting (Phase 16 M16-9)
def test_delisted_token_is_never_filled_and_a_held_position_is_exited():
    rows = [(1.0, 1.01, 0.99, 1.0, 100)] * 30
    cfg = EngineConfig(fill_model="FLAT", fees=X.Fees(0.0, 0, None, 0.0), sol_usd_default=150, latency_s=0)
    gone = Engine(cfg).run(SignalAt(at=20), [TokenData("solana", "GONE", mk(rows), delisted_at=T + 21 * H)])
    assert gone["n_trades"] == 0 and gone["counts"]["filled"] == 0
    assert any(j["event"] == "EXPIRED" and j.get("reason") == "delisted" for j in gone["journal"])
    later = Engine(cfg).run(SignalAt(at=20), [TokenData("solana", "LATER", mk(rows), delisted_at=T + 25 * H)])
    tr = later["trades"][0]
    assert tr["exit_reason"] == "DELISTED" and tr["exit_time"] == T + 25 * H


# G17: partial exits keep the original cost; a remainder that cannot be sold by the end is reported, not dropped (Phase 16 D3/D4)
def test_partial_exits_report_original_cost_and_unsold_remainder():
    rows = [(1.0, 1.01, 0.99, 1.0, 100)] * 22 + [(2.0, 2.02, 1.98, 2.0, 100)] * 4
    td = TokenData("solana", "PART", mk(rows), liquidity=[(T, 20_000.0)])
    cfg = EngineConfig(account_usd=10_000, size_usd=1_000, latency_s=0, sol_usd_default=150, entry_impact_cap=1.0, exit_impact_cap=0.05,
                       max_exposure_frac=1.0, liquidity_max_age_s=1e9)
    r = Engine(cfg).run(SignalAt(at=20, hold=2), [td])
    assert r["counts"]["filled"] == 1 and r["n_trades"] == 1
    tr = r["trades"][0]
    buy = next(f for f in r["fills"] if f["action"] == "BUY" and f["status"] == "FILLED")
    assert tr["cost_usd"] == pytest.approx(buy["requested"] + buy["fees"]["network_usd"])
    assert tr["status"] == "PARTIAL_UNSOLD_AT_END" and tr["unsold_tokens"] > 0
    assert tr["ret"] == pytest.approx(tr["proceeds_usd"] / tr["cost_usd"] - 1)
    assert r["final_cash"] == pytest.approx(10_000 - tr["cost_usd"] + tr["proceeds_usd"])
