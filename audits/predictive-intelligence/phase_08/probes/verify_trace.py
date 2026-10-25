"""Phase 08 independent check of the forecast trace. Uses neither memelab.predictive.technical nor features: it reads the Phase 05
store's tables with plain SQL, rebuilds the visible candles at the decision time by its own rule (newest version of each candle
position whose available_at is at or before T, vanished positions removed, end at or before T), recomputes the 15 tech-1
values and the B2 inputs from the decision row, and recomputes every number in the trace from the card's JSON numbers.
Writes a JSON report and FORECAST_TRACE.md beside the trace.

    python -B verify_trace.py TRACE.json [--feature-store PATH]
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

FEATURE_STORE = "/home/claude/pi_research/p05/predictive_store.sqlite"


def iso(t):
    return datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def visible(con, mint, pool, T):
    rows = con.execute("SELECT id, series_key, start_at, end_at, c, v, available_at, retrieved_at, vanished, obs_key "
                       "FROM predictive_candles WHERE mint=? AND pool_address=? AND period_s=300 AND available_at <= ? ORDER BY id",
                       (mint, pool, T)).fetchall()
    newest = {}
    for r in rows:
        k = r[1]
        if k not in newest or r[0] > newest[k][0]:
            newest[k] = r
    out = [r for r in newest.values() if not r[8] and r[3] <= T]
    out.sort(key=lambda r: r[3])
    return [{"start": r[2], "end": r[3], "c": r[4], "v": r[5], "av": r[6], "ra": r[7], "obs_key": r[9]} for r in out]


def tech(cs, T):
    last = cs[-1]

    def px(x):
        return [c for c in cs if c["end"] <= x][-1]

    def win(a, b=None):
        b = T if b is None else b
        return [c for c in cs if a < c["end"] <= b]
    L = math.log
    o = {}
    for n, w in (("tech_log_ret_1h", 3600), ("tech_log_ret_6h", 21600), ("tech_log_ret_24h", 86400)):
        o[n] = L(last["c"] / px(T - w)["c"])
    for n, w in (("tech_rv_1h", 3600), ("tech_rv_6h", 21600)):
        seq = [px(T - w)] + win(T - w)
        o[n] = math.sqrt(sum(L(b["c"] / a["c"]) ** 2 for a, b in zip(seq, seq[1:])))
    for n, w in (("tech_log_range_6h", 21600), ("tech_log_range_24h", 86400)):
        cl = [px(T - w)["c"]] + [c["c"] for c in win(T - w)]
        o[n] = L(max(cl) / min(cl))
    v1 = sum(c["v"] for c in win(T - 3600))
    v24 = sum(c["v"] for c in win(T - 86400))
    o["tech_log_rel_vol_1h"] = L((v1 + 1) / (v24 / 24 + 1))
    o["tech_log1p_candles_24h"] = math.log1p(len(win(T - 86400)))
    o["tech_log1p_last_close_age_min"] = math.log1p((T - last["end"]) / 60)
    ph = max([px(T - 86400)["c"]] + [c["c"] for c in win(T - 86400, T - 3600)])
    rh = max([px(T - 3600)["c"]] + [c["c"] for c in win(T - 3600)])
    o["tech_log_breakout_1h"] = L(rh / ph)
    o["tech_failed_breakout_1h"] = 1.0 if (rh > ph and last["c"] < ph) else 0.0
    ph6 = max([px(T - 86400)["c"]] + [c["c"] for c in win(T - 86400, T - 21600)])
    broke = any(c["c"] > ph6 for c in win(T - 21600))
    o["tech_retest_6h"] = 1.0 if (broke and abs(L(last["c"] / ph6)) <= L(1.03)) else 0.0
    o["tech_log_dist_24h_high"] = L(last["c"] / max([px(T - 86400)["c"]] + [c["c"] for c in win(T - 86400)]))
    o["tech_log_pullback_6h"] = L(last["c"] / max([px(T - 21600)["c"]] + [c["c"] for c in win(T - 21600)]))
    return o


def b2_inputs(con, key, T):
    row = con.execute("SELECT row_json, token_json FROM predictive_decisions WHERE decision_key=?", (key,)).fetchone()
    r = json.loads(row[0])
    snap = json.loads(r["snapshot_json"])
    tok = json.loads(row[1]) if row[1] else {}
    fp = tok.get("first_pool_at")
    age = None
    if fp:
        t0 = float(fp) if isinstance(fp, (int, float)) else datetime.fromisoformat(fp.replace("Z", "+00:00")).timestamp()
        age = (T - t0) if T >= t0 else None
    ff = json.loads(r.get("fatal_flags_json") or "null")
    return {"thesis_log1p_liquidity_usd": math.log1p(snap["liquidity"]), "thesis_log1p_mcap_usd": math.log1p(snap["mcap"]),
            "thesis_log1p_vol_24h_usd": math.log1p(snap["vol_24h"]), "thesis_fatal_present": float(bool(ff)),
            "log1p_token_age_days": math.log1p(age / 86400) if age is not None else float("nan")}


def logistic_number(body, x):
    cols = body.get("spec", {}).get("columns") or body["columns"]
    prep, lr = body["prep"], body["logistic"]
    raw = [x[c] for c in cols]
    kept = [raw[j] for j in prep["keep"]]
    miss = [not math.isfinite(v) for v in kept]
    filled = [prep["med"][i] if miss[i] else kept[i] for i in range(len(kept))]
    z = filled + [1.0 if miss[i] else 0.0 for i in prep["ind"]]
    zs = [(z[i] - prep["mu"][i]) / prep["sd"][i] for i in range(len(z))]
    s = lr["intercept"] + sum(a * b for a, b in zip(lr["coef"], zs))
    return 1 / (1 + math.exp(-s))


def stumps_number(body, x):
    cols, st = body["spec"]["columns"], body["stumps"]
    s = st["init"]
    for j, thr, vl, vr in st["trees"]:
        s += st["lr"] * (vl if x[cols[int(j)]] <= thr else vr)
    return 1 / (1 + math.exp(-s))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("--feature-store", default=FEATURE_STORE)
    a = ap.parse_args()
    tr = json.loads(Path(a.trace).read_text())
    con = sqlite3.connect(f"file:{a.feature_store}?mode=ro", uri=True)
    T = float(tr["decision_time"])
    cs = visible(con, tr["mint"], tr["pool_address"], T)
    mine = tech(cs, T)
    rep = {"decision_key": tr["decision_key"], "decision_time_utc": tr["decision_time_utc"], "differences": []}
    for k, v in mine.items():
        t = tr["tech_values"][k]
        if t is None or abs(v - t) > 1e-9 * max(1.0, abs(v)):
            rep["differences"].append(f"{k}: independent {v!r} vs trace {t!r}")
    for k, v in tr["tech_available_at"].items():
        if v is not None and v > T:
            rep["differences"].append(f"{k}: available at {v} after T")
    used = {c["obs_key"] for c in tr["candles_read"]}
    want = {c["obs_key"] for c in cs if c["end"] > T - 86400 - 3600}
    if used != want:
        rep["differences"].append(f"candle set differs: {len(used ^ want)} candles")
    b2 = b2_inputs(con, tr["decision_key"], T)
    for k, v in b2.items():
        t = tr["b2_inputs"][k]
        if (math.isfinite(v) or (t is not None and math.isfinite(t))) and (t is None or abs(v - t) > 1e-9 * max(1.0, abs(v))):
            rep["differences"].append(f"{k}: independent {v!r} vs trace {t!r}")
    x = {**mine, **b2}
    nums = {}
    for m, d in tr["models"].items():
        body = d["card"]["body"]
        if "abstain" in body:
            want_n = None
        elif m == "B0":
            want_n = body["p"]
        elif "stumps" in body:
            want_n = stumps_number(body, x)
        else:
            want_n = logistic_number(body, x)
        nums[m] = want_n
        got = d["number"]
        if (want_n is None) != (got is None) or (want_n is not None and abs(want_n - got) > 1e-9):
            rep["differences"].append(f"{m}: independent {want_n!r} vs trace {got!r}")
        if float(d["card"]["training_cutoff"]) > T:
            rep["differences"].append(f"{m}: card trained after the decision")
    rep["independent_numbers"] = nums
    rep["candles_visible_in_last_25h"] = len(want)
    rep["invalid_inputs_all_rejected"] = tr["invalid_inputs_all_rejected"]
    rep["pass"] = not rep["differences"] and tr["invalid_inputs_all_rejected"]
    out = Path(a.trace).with_name("verify_trace.json")
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    # the human-readable trace
    lines = [f"# Forecast trace (Phase 08, {tr['target']})", "",
             "PROVISIONAL_PENDING_REVISION_REREAD (PI-D-046). Research only; no number here is a published probability.", "",
             f"Selection rule (fixed before the run): {tr['selection_rule']}.", "",
             "| Item | Value |", "|---|---|",
             f"| Decision key | `{tr['decision_key']}` |", f"| Mint (exact) | `{tr['mint']}` |",
             f"| Point-in-time pool | `{tr['pool_address']}` |",
             f"| Decision time (export commit) | {tr['decision_time_utc']} |", f"| Decision row sha256 | `{tr['row_sha256']}` |",
             f"| Fold and cutoff | {tr['fold']}, trained to {tr['fold_cutoff_utc']} |", f"| tech-1 snapshot sha | `{tr['tech_snapshot_sha']}` |",
             f"| Outcome (known only after maturity, not an input) | {tr['label_y']} |", "",
             "## Candles of the last hour, in time order", "",
             "Every candle read is visible at T: its end plus the 300 s provider lag, or the lab's read, is at or before T. "
             "Only closes and volumes are read.", "",
             "| Start (UTC) | End (UTC) | Available at (UTC) | Basis | Close (USD) | Volume (USD) |", "|---|---|---|---|---|---|"]
    for c in tr["candles_read"]:
        if c["end_at"] > T - 3600 - 300:
            lines.append(f"| {iso(c['start_at'])} | {iso(c['end_at'])} | {iso(c['available_at'])} | {c['available_basis']} | "
                         f"{c['close']:.10g} | {c['volume_usd']:.6g} |")
    lines += ["", "## Candles that existed for this pool but were not available at T (never read)", "",
              "| Start (UTC) | End (UTC) | Available at (UTC) | Basis |", "|---|---|---|---|"]
    for c in tr["candles_not_yet_available_at_T"]:
        lines.append(f"| {iso(c['start_at'])} | {iso(c['end_at'])} | {iso(c['available_at'])} | {c['available_basis']} |")
    lines += ["", "## tech-1 values at T", "", "| Feature | Value | Available at (UTC) | Independent recomputation |", "|---|---|---|---|"]
    for k, v in tr["tech_values"].items():
        av = tr["tech_available_at"][k]
        lines.append(f"| `{k}` | {v:.10g} | {iso(av) if av is not None else 'no input row'} | {mine[k]:.10g} |")
    lines += ["", "## Numbers from the fold's cards", "", "| Model | Card model sha (first 12) | Trained to | Number | Abstain reason | Independent |",
              "|---|---|---|---|---|---|"]
    for m, d in tr["models"].items():
        n = d["number"]
        ind = nums[m]
        lines.append(f"| {m} | `{d['card_model_sha'][:12]}` | {d['training_cutoff_utc']} | {'' if n is None else f'{n:.6f}'} | "
                     f"{d['abstain'] or ''} | {'' if ind is None else f'{ind:.6f}'} |")
    lines += ["", "## Invalid inputs, each rejected", "", "| Input | Result |", "|---|---|"]
    for k, v in tr["invalid_inputs"].items():
        lines.append(f"| {k} | {v.replace('|', '/')[:220]} |")
    lines += ["", f"Independent check (`probes/verify_trace.py`): {'no difference' if not rep['differences'] else rep['differences']}; "
              f"latency of one forecast from the store, median of 20: {tr['latency_s_median_of_20']} s.", ""]
    Path(a.trace).with_name("FORECAST_TRACE.md").write_text("\n".join(lines))
    print(json.dumps({"pass": rep["pass"], "differences": rep["differences"][:5]}))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
