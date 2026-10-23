"""Phase 11 real-data validation, exactly as pre-registered in P11_PREREG.md.
    python audits/backtesting/validation/p11_validate.py > audits/backtesting/validation/p11_results.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from memelab.backtest import quality, runner, store, validation as V  # noqa: E402
from memelab.backtest.engine import EngineConfig  # noqa: E402

T0, T1, EMB = 1791331200.0, 1792771200.0, 2 * 86400.0
GRIDS = {
    "LAB_STATUS": [{"min_score": 55}, {"min_score": 65}, {"min_score": 55, "statuses": ["ENTRY CONDITIONS MET", "NEAR ENTRY"]}],
    "BREAKOUT_CLOSE": [{"lookback": lb, "vol_mult": vm} for lb in (12, 24) for vm in (1.0, 1.5)],
    "MOMENTUM": [{"min_roc": r, "min_bar_volume_usd": v} for r in (0.05, 0.10) for v in (2000.0, 10000.0)],
    "BREAKOUT_RETEST": [{}], "RECLAIM": [{}], "TREND_HHHL": [{}], "ABSORPTION_BREAK": [{}],
    "RANDOM_ENTRY": [{"p": 0.02, "seed": s} for s in range(40)],
}


def main():
    con = store.connect()
    tokens, skipped = runner.build_tokens(con)
    tokens_c, _ = runner.build_tokens(con, thesis_known_at="committed")
    sol = runner.sol_usd_series(con)
    dh = quality.dataset_hash(con, sorted(t.mint for t in tokens) + [runner.SOL], cutoff=T1)
    cfg = EngineConfig()
    plan = V.SplitPlan.make(T0, T1, (0.5, 0.25, 0.25), embargo_s=EMB)
    import hashlib
    pre = Path(__file__).with_name("P11_PREREG.md")
    reps, out = [], {"prereg_sha256": hashlib.sha256(pre.read_bytes()).hexdigest(), "dataset_hash": dh, "tokens": len(tokens), "plan": plan.as_dict(), "started": time.time(), "strategies": {}}
    for sid, grid in GRIDS.items():
        r = V.validate(sid, grid, tokens, cfg, plan, min_n_tune=8, min_n_test=30, sol_usd=sol)
        reps.append(r)
        d = V.report_dict(r)
        # sealed-test trades again for the regime split (same frozen config, same window: deterministic, not a second look for tuning)
        rt = V.run_window(V.registry.make(sid, **r.chosen), tokens, cfg, plan, "test", sol)
        d["test_regimes"] = V.regime_breakdown(rt["trades"], sol)
        d["test_ledger_hash"] = rt["ledger_hash"]
        out["strategies"][sid] = d
    lab_c = V.validate("LAB_STATUS", GRIDS["LAB_STATUS"], tokens_c, cfg, plan, min_n_tune=8, min_n_test=30, sol_usd=sol)
    out["sensitivity_lab_status_committed"] = V.report_dict(lab_c)
    out["holm"] = V.compare_strategies(reps, min_n_test=30)
    out["total_trials"] = sum(len(g) for g in GRIDS.values())
    out["walk_forward_breakout_close"] = V.walk_forward("BREAKOUT_CLOSE", GRIDS["BREAKOUT_CLOSE"], tokens, cfg, T0, T1, folds=3, embargo_s=EMB, sol_usd=sol)
    out["finished"] = time.time()
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=1, default=str))
