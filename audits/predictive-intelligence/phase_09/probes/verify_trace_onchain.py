"""Phase 09 independent check of the forecast trace. Uses neither memelab.predictive.onchain nor features: it reads the Phase 05
store's decision rows and stored version 2 values with plain SQL, re-derives the onchain-1 values with its own parser from the
decision row, its token row and the previous decision of the mint, and recomputes every model number in the trace from the
card's JSON numbers with plain Python. Writes a JSON report and FORECAST_TRACE.md beside the trace.

    python -B verify_trace_onchain.py TRACE.json [--feature-store PATH]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

FEATURE_STORE = "/home/claude/pi_research/p05/predictive_store.sqlite"
STRUCT = {"MINT_AUTHORITY_ACTIVE", "FREEZE_AUTHORITY_ACTIVE", "PERMANENT_DELEGATE", "TRANSFER_FEE_GT_5PCT", "TRANSFER_HOOK_UNKNOWN",
          "NON_TRANSFERABLE", "HONEYPOT", "CANNOT_BUY", "HIDDEN_OWNER", "EXTREME_TAX", "SIMULATION_FAILED", "AIRDROP_SCAM", "SELFDESTRUCT",
          "CREATOR_PRIOR_HONEYPOT", "PROXY_WITH_LIVE_OWNER", "TAX_MODIFIABLE_BY_OWNER", "LP_RISK_CRITICAL", "NO_SELL_ROUTE", "CANNOT_EXIT_5K"}
DISTR = {"LARGEST_HOLDER_GT_15PCT", "TOP10_GT_50PCT", "DEV_WALLET_FARM", "CLUSTER_OWNERSHIP_GT_25PCT", "INSIDER_DISTRIBUTION"}


def iso(t):
    return datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def first(lines, rx):
    for s in lines:
        m = re.fullmatch(rx, s)
        if m:
            return m
    return None


def num(s):
    return float(s.replace(",", ""))


def readings(row_json, token_json):
    r = json.loads(row_json)
    flags = [f["flag"] for f in json.loads(r.get("fatal_flags_json") or "[]")]
    sn = json.loads(r.get("snapshot_json") or "{}")
    bd = json.loads(r.get("score_breakdown_json") or "{}")
    lp = (bd.get("token_lp_safety") or {}).get("rationale") or []
    me = (bd.get("market_execution") or {}).get("rationale") or []
    so = (bd.get("supply_ownership") or {}).get("rationale") or []
    de = (bd.get("demand_order_flow") or {}).get("rationale") or []
    o = {"structural": float(any(f in STRUCT for f in flags)), "distribution": float(any(f in DISTR for f in flags))}
    mech_clean = any(s.startswith("token mechanics clean") for s in lp)
    mi = first(lp, r"token mechanics ([0-9]+) critical issue\(s\)")
    o["mech"] = 0.0 if mech_clean else (float(mi.group(1)) if mi else None)
    o["mint"] = None if o["mech"] is None else float("MINT_AUTHORITY_ACTIVE" in flags)
    o["freeze"] = None if o["mech"] is None else float("FREEZE_AUTHORITY_ACTIVE" in flags)
    m = first(lp, r"transfer fee ([0-9.,-]+)%")
    o["fee"] = num(m.group(1)) if m else None
    m = first(lp, r"LP risk ([A-Z_]+)")
    o["lp"] = {"LOW": 0.0, "MODERATE": 1.0, "HIGH": 2.0, "CRITICAL": 3.0}.get(m.group(1)) if m else None
    m = first(lp, r"LP locked/burned ([0-9.,-]+)%")
    o["locked"] = num(m.group(1)) if m else None
    liq, cap = sn.get("liquidity"), sn.get("exit_cap_3pct")
    o["share"] = cap / liq if (isinstance(liq, (int, float)) and isinstance(cap, (int, float)) and liq > 0 and cap >= 0) else None
    noroute = first(me, r"no sell route \((.*)\)") or ("NO_SELL_ROUTE" in flags)
    ok = first(me, r"route OK, ([0-9]+) hop\(s\)")
    o["noroute"] = 1.0 if noroute else (0.0 if ok else None)
    o["hops"] = float(ok.group(1)) if ok else None
    m = first(me, r"round-trip friction ([0-9.,-]+)%")
    o["friction"] = num(m.group(1)) if m else None
    m = first(so, r"largest unexplained holder ([0-9.,-]+)%")
    o["largest"] = num(m.group(1)) if m else None
    m = first(so, r"cluster-adjusted ownership [0-9.,-]+% \(confidence ([A-Za-z/_]+)\)")
    o["cluster"] = {"LOW": 0.0, "MODERATE": 1.0, "HIGH": 2.0}.get(m.group(1).upper()) if m else None
    m = first(so, r"early wallets ([A-Za-z_/]+)")
    o["early"] = {"ACCUMULATING": 0.0, "HOLDING": 1.0, "SCALING_OUT": 2.0, "DISTRIBUTING": 3.0, "EXITING": 4.0}.get(m.group(1).upper()) if m else None
    m = first(de, r"manipulation screen (.+) / wash ([A-Za-z/_]+)")
    o["wash"] = {"LOW": 0.0, "MODERATE": 1.0, "MEDIUM": 1.0, "HIGH": 2.0}.get(m.group(2).upper()) if m else None
    tp = json.loads(token_json or "{}").get("token_program")
    o["t2022"] = 1.0 if tp == "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb" else 0.0 if tp == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA" else None
    o["liq"], o["cap"], o["top10"], o["t"] = liq, cap, sn.get("adj_top10"), sn.get("t")
    return o


def onchain(con, mint, T, key):
    cur = con.execute("SELECT row_json, token_json, decision_time FROM predictive_decisions WHERE decision_key=?", (key,)).fetchone()
    a = readings(cur[0], cur[1])
    pr = con.execute("SELECT row_json, token_json, decision_time FROM predictive_decisions WHERE chain='solana' AND mint=? AND decision_time < ? "
                     "ORDER BY decision_time DESC, id DESC LIMIT 1", (mint, T)).fetchone()
    v = {"oc_structural_fatal": a["structural"], "oc_distribution_fatal": a["distribution"], "oc_mechanics_issues": a["mech"],
         "oc_mint_authority_active": a["mint"], "oc_freeze_authority_active": a["freeze"], "oc_transfer_fee_pct": a["fee"],
         "oc_token2022": a["t2022"], "oc_lp_risk_ord": a["lp"], "oc_lp_locked_pct": a["locked"], "oc_exit_cap_share": a["share"],
         "oc_no_sell_route": a["noroute"], "oc_route_hops": a["hops"], "oc_round_trip_friction_pct": a["friction"],
         "oc_largest_unexplained_pct": a["largest"], "oc_cluster_confidence_ord": a["cluster"], "oc_early_wallet_dir_ord": a["early"],
         "oc_wash_ord": a["wash"], "oc_capture_delay_s": (T - a["t"]) if a["t"] is not None else None}
    if pr is None:
        for k in ("oc_d_log1p_liquidity", "oc_d_log1p_exit_cap", "oc_d_adj_top10_pp", "oc_d_lp_locked_pp", "oc_authority_switch",
                  "oc_fee_change_pp", "oc_prior_gap_h"):
            v[k] = None
    else:
        b = readings(pr[0], pr[1])
        d = lambda x, y, lg=False: None if x is None or y is None else ((math.log1p(x) - math.log1p(y)) if lg else x - y)
        v["oc_d_log1p_liquidity"] = d(a["liq"], b["liq"], True)
        v["oc_d_log1p_exit_cap"] = d(a["cap"], b["cap"], True)
        v["oc_d_adj_top10_pp"] = d(a["top10"], b["top10"])
        v["oc_d_lp_locked_pp"] = d(a["locked"], b["locked"])
        st = [(a["mint"], b["mint"]), (a["freeze"], b["freeze"])]
        v["oc_authority_switch"] = None if any(x is None or y is None for x, y in st) else float(any(x != y for x, y in st))
        v["oc_fee_change_pp"] = d(a["fee"], b["fee"])
        v["oc_prior_gap_h"] = (T - float(pr[2])) / 3600.0
    return v


def sig(x):
    return None if x is None else float(f"{x:.10g}")


def v2_value(con, key, name):
    r = con.execute("SELECT v.value FROM predictive_snapshots s JOIN predictive_feature_values v USING(snapshot_key) WHERE s.decision_key=? "
                    "AND s.availability_mode='provider' AND v.feature_name=?", (key, name)).fetchone()
    return r[0] if r else None


def logit_number(body, x):
    cols, prep, lg = body.get("columns") or body["spec"]["columns"], body["prep"], body["logistic"]
    X = [x.get(c) for c in cols]
    kept = [X[j] for j in prep["keep"]]
    filled = [prep["med"][i] if (v is None or not math.isfinite(v)) else v for i, v in enumerate(kept)]
    ind = [1.0 if (kept[j] is None or not math.isfinite(kept[j])) else 0.0 for j in prep["ind"]]
    z = [(v - m) / s for v, m, s in zip(filled + ind, prep["mu"], prep["sd"])]
    t = lg["intercept"] + sum(c * v for c, v in zip(lg["coef"], z))
    return 1.0 / (1.0 + math.exp(-t))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("--feature-store", default=FEATURE_STORE)
    a = ap.parse_args()
    tr = json.loads(Path(a.trace).read_text())
    con = sqlite3.connect(f"file:{a.feature_store}?mode=ro", uri=True)
    T, key, mint = float(tr["decision_time"]), tr["decision_key"], tr["mint"]
    mine = onchain(con, mint, T, key)
    diffs = []
    for k, v in mine.items():
        w = tr["oc_values"].get(k)
        s = sig(v)
        if (s is None) != (w is None) or (s is not None and abs(s - w) > 1e-9 * max(1.0, abs(s))):
            diffs.append(f"{k}: recomputed {s!r} vs trace {w!r}")
    late = [k for k, av in tr["oc_available_at"].items() if av is not None and av > T]
    x = {}
    for c in ("thesis_log1p_liquidity_usd", "thesis_log1p_mcap_usd", "thesis_log1p_vol_24h_usd", "thesis_fatal_present", "thesis_adj_top10_pct"):
        x[c] = v2_value(con, key, c)
    age = v2_value(con, key, "token_age_s")
    x["log1p_token_age_days"] = math.log1p(age / 86400.0) if age is not None and age >= 0 else None
    x.update({k: (sig(v) if v is not None else None) for k, v in mine.items()})
    for c, w in tr["model_inputs"].items():
        if (x.get(c) is None) != (w is None) or (w is not None and abs(x[c] - w) > 1e-9 * max(1.0, abs(w))):
            diffs.append(f"input {c}: recomputed {x.get(c)!r} vs trace {w!r}")
    nums = {}
    for m, d in tr["models"].items():
        body = d["card"]["body"]
        if "abstain" in body:
            got = None
        elif m == "B0":
            got = body["p"]
        elif "cells" in body:
            a_, b_ = x.get("oc_structural_fatal"), x.get("oc_distribution_fatal")
            cell = "MISSING" if a_ is None or b_ is None else f"S{int(a_)}D{int(b_)}"
            got = body["cells"][cell]["p"] if cell in body["cells"] else body["b0"]
        else:
            req = body.get("required") or body["spec"]["rows"]
            got = None if any(x.get(c) is None for c in req) else logit_number(body, x)
        nums[m] = got
        w = d["number"]
        if (got is None) != (w is None) or (got is not None and abs(got - w) > 1e-12):
            diffs.append(f"model {m}: recomputed {got!r} vs trace {w!r}")
        if d["card"]["training_cutoff"] > T:
            diffs.append(f"model {m}: card trained after the decision")
    rep = {"decision_key": key, "decision_time_utc": iso(T), "values_compared": len(mine), "inputs_compared": len(tr["model_inputs"]),
           "models_compared": len(nums), "differences": diffs, "values_available_after_T": late,
           "invalid_inputs_all_rejected": tr.get("invalid_inputs_all_rejected"), "pass": not diffs and not late and tr.get("invalid_inputs_all_rejected") is True}
    out = Path(a.trace).with_name("verify_trace.json")
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    md = [f"# Phase 09 forecast trace", "",
          f"Decision `{key}` of mint `{mint}` at {iso(T)} (EXPORT_COMMIT), target `{tr['target']}`, fold {tr['fold']} (cutoff {tr['fold_cutoff_utc']}), label {tr['label_y']}.",
          f"Row sha256 `{tr['row_sha256']}`; onchain-1 snapshot sha `{tr['oc_snapshot_sha']}`. Status PROVISIONAL_PENDING_REVISION_REREAD.", "",
          "## Lab readings behind the values", "", f"- Fatal flags: {', '.join(tr['fatal_flags']) or 'none'}",
          f"- Token program: `{tr['token_program']}`", f"- Snapshot fields: {json.dumps(tr['snapshot_fields'], sort_keys=True)}"]
    for b, lines in tr["rationale"].items():
        md.append(f"- {b}: " + "; ".join(lines or []))
    if tr.get("prior_decision"):
        md.append(f"- Previous decision `{tr['prior_decision']['decision_key']}` at {iso(tr['prior_decision']['decision_time'])}: "
                  f"{json.dumps(tr['prior_decision']['snapshot_fields'], sort_keys=True)}")
    md += ["", "## onchain-1 values", "", "| Feature | Value | Missing reason |", "|---|---|---|"]
    for k, v in tr["oc_values"].items():
        md.append(f"| `{k}` | {v if v is not None else ''} | {tr['oc_reasons'].get(k, '')} |")
    md += ["", "## Models (fold cards)", "", "| Model | Card sha | Cutoff | Number | Abstain |", "|---|---|---|---|---|"]
    for m, d in tr["models"].items():
        md.append(f"| {m} | `{d['card_model_sha'][:16]}` | {d['training_cutoff_utc']} | {'' if d['number'] is None else round(d['number'], 6)} | {d['abstain'] or ''} |")
    md += ["", "## Invalid inputs", ""] + [f"- {k}: {v}" for k, v in tr["invalid_inputs"].items()]
    md += ["", "## Independent recomputation", "", f"`verify_trace_onchain.py` (no onchain.py, no features.py): {len(mine)} values, "
           f"{len(tr['model_inputs'])} model inputs and {len(nums)} model numbers recomputed; differences: {len(diffs)}; values available "
           f"after the decision: {len(late)}; pass: {rep['pass']}.", ""]
    Path(a.trace).with_name("FORECAST_TRACE.md").write_text("\n".join(md))
    print(json.dumps({k: rep[k] for k in ("values_compared", "inputs_compared", "models_compared", "pass")} | {"differences": len(diffs)}))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
