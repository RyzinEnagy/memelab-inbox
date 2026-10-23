"""Research runner: frozen universe + stored bars -> TokenData -> engine -> saved, reproducible run (Phase 10).

Point-in-time choices made here:
- a token becomes tradable at the later of its first lab record and the time its pool basis could be chosen
  (`gecko.pool_basis_at` needs bars already available); the choice is never made with later data;
- each bar is used in its FIRST stored version (a provider revision is never applied backwards);
- lab theses are known at their own record time (`thesis_known_at="created"`, the lab's clock) or, more
  conservatively, at the first git commit that contained them (`"committed"`);
- liquidity for fills comes only from the lab's own liquidity observations in thesis snapshots, valid for
  `liquidity_max_age_s`; pool type and fee come from the pool record (`execution.assumed_swap_fee`);
- SOL/USD for network fees comes from the stored SOL/USDC bars available at each time; missing means the fill is
  refused, never a default.
Results are saved under run_id = sha256(config, dataset hash, code); a second call with the same inputs returns the
stored result (restart recovery) instead of recomputing or duplicating rows.
"""
from __future__ import annotations

import bisect
import json
import time

from . import ENGINE_VERSION, execution as X, quality, store
from .engine import Engine, EngineConfig, TokenData
from .sources import corpus, gecko
from .strategies import registry
from .strategies.features import B

SOL = "So11111111111111111111111111111111111111112"
RUNS_DIR = store.ROOT / "data" / "backtest" / "runs"
BASIS_TRIES_H = (0, 6, 12, 24, 48)


def _first_versions(con, mint: str, pool: str, tf: int = 3600) -> list[B]:
    rows = con.execute("SELECT start, end, o, h, l, c, volume_usd, available_at FROM bt_market_bars WHERE mint=? AND pool_address=? AND timeframe_s=? "
                       "ORDER BY start, available_at, id", (mint, pool, tf)).fetchall()
    seen, out = set(), []
    for r in rows:
        if r["start"] in seen:
            continue
        seen.add(r["start"])
        out.append(B(r["start"], r["end"], r["o"], r["h"], r["l"], r["c"], r["volume_usd"] or 0.0, r["available_at"]))
    return out


def sol_usd_series(con, max_age_s: float = 6 * 3600):
    bars = _first_versions(con, SOL, corpus.SOL_USDC_POOL)
    av = [b.avail for b in bars]

    def f(t: float):
        i = bisect.bisect_right(av, t) - 1
        if i < 0 or t - bars[i].end > max_age_s:
            return None
        return bars[i].c
    return f


def build_tokens(con, universe_id: str = "lab_state_history", chain: str = "solana", thesis_known_at: str = "created",
                 mints: list[str] | None = None, catalysts: list[dict] | None = None) -> tuple[list[TokenData], list[dict]]:
    rows = [dict(r) for r in con.execute("SELECT * FROM bt_universe_members WHERE universe_id=? AND chain=? ORDER BY entered_at, id", (universe_id, chain))]
    by: dict[str, list[dict]] = {}
    for r in rows:
        if mints is None or r["mint"] in mints:
            by.setdefault(r["mint"], []).append(r)
    tokens, skipped = [], []
    for mint, rs in sorted(by.items()):
        cats = [c for c in (catalysts or []) if c.get("mint") == mint and c.get("chain", chain) == chain]
        # the lab knew a token from its first record of any kind: a scout thesis/rejection or a launch-monitor record
        t0 = min([r["entered_at"] for r in rs] + [c["available_at"] for c in cats])
        basis, bt = None, None
        for h in BASIS_TRIES_H:
            basis = gecko.pool_basis_at(con, chain, mint, t0 + h * 3600)
            if basis:
                bt = t0 + h * 3600
                break
        if not basis:
            skipped.append({"mint": mint, "reason": "INSUFFICIENT_HISTORY: no pool with bars within 48 h of discovery"})
            continue
        pv = con.execute("SELECT pool_type, dex FROM bt_pool_versions WHERE pool_address=? ORDER BY available_at LIMIT 1", (basis["pool_address"],)).fetchone()
        fee, fee_basis = X.assumed_swap_fee(pv["dex"] if pv else None)
        theses, liq = [], []
        for r in rs:
            if r["basis"] != "THESIS":
                continue
            snap = json.loads(r["snapshot_json"]) if r["snapshot_json"] else {}
            known = r["available_at"] if thesis_known_at == "created" else max(r["available_at"], r["committed_by"] or r["available_at"])
            theses.append({"available_at": known, "status": r["status_at_entry"], "score": r["score_at_entry"],
                           "fatal_flags": json.loads(r["fatal_flags_json"] or "[]"), "snapshot": snap})
            if snap.get("liquidity"):
                liq.append((known, float(snap["liquidity"])))
        bars = _first_versions(con, mint, basis["pool_address"])
        tokens.append(TokenData(chain, mint, bars, liquidity=liq, pool_type=(pv["pool_type"] if pv else "UNKNOWN"), theses=theses,
                                universe_from=max(t0, bt), swap_fee=fee, fee_basis=fee_basis, catalysts=cats))
    return tokens, skipped


def run(con, strategy_id: str, params: dict | None = None, cfg: EngineConfig | None = None, universe_id: str = "lab_state_history",
        until: float | None = None, decide_from: float | None = None, decide_until: float | None = None, thesis_known_at: str = "created",
        mints: list[str] | None = None, save: bool = True, label: str | None = None) -> dict:
    cfg = cfg or EngineConfig()
    strat = registry.make(strategy_id, **(params or {}))
    cats = None
    if strat.kind == "CATALYST":
        from .sources import lab_events
        cats = lab_events.launch_catalysts(store.ROOT)       # the lab's own contemporaneous launch records (Phase 09)
    tokens, skipped = build_tokens(con, universe_id, thesis_known_at=thesis_known_at, mints=mints, catalysts=cats)
    dhash = quality.dataset_hash(con, sorted(t.mint for t in tokens) + [SOL], cutoff=until)
    config = {"strategy_id": strat.id, "strategy_version": strat.version, "params": strat.params, "universe_definition": universe_id,
              "thesis_known_at": thesis_known_at, "until": until, "decide_from": decide_from, "decide_until": decide_until,
              "engine": {k: (v.__dict__ if hasattr(v, "__dict__") else v) for k, v in cfg.__dict__.items()}, "cost_model_version": X.COST_MODEL_VERSION,
              "mints": sorted(mints) if mints else None, "label": label}
    run_id = store.register_run(con, config, dataset_hash=dhash, seed=strat.params.get("seed")) if save else None
    if save:
        con.commit()                                      # never hold the write lock while the engine runs
    if save:
        prev = con.execute("SELECT result_json FROM bt_run_results WHERE run_id=? ORDER BY created_at LIMIT 1", (run_id,)).fetchone()
        if prev:
            out = json.loads(prev[0])
            out["cache"] = "HIT"
            return out
    t0 = time.time()
    res = Engine(cfg, sol_usd=sol_usd_series(con)).run(strat, tokens, until=until, decide_from=decide_from, decide_until=decide_until)
    res.update(run_id=run_id, dataset_hash=dhash, tokens=len(tokens), skipped=skipped, wall_s=round(time.time() - t0, 2),
               engine_version=ENGINE_VERSION, created_at=time.time())
    if save:
        store.record_result(con, run_id, "COMPLETE", res)
        con.commit()
        d = RUNS_DIR / run_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "result.json").write_text(json.dumps(res, indent=1, default=str))
        (d / "journal.json").write_text(json.dumps(res.get("journal", []), indent=1, default=str))
    res["cache"] = "MISS"
    return res
