"""Phase 10 independent check of the forecast trace. Uses neither memelab.predictive.socialcat nor features: it reads the Phase 05
store's decision rows and stored version 2 values with plain SQL, re-derives the socialcat-1 model inputs with its own parser from
the decision row, its stored token row and the previous decision of the mint, checks the stored token row against the token row
of the decision's own export read from git, and recomputes every model number in the trace from the card's JSON numbers with
plain Python (logistic and stumps). Writes a JSON report and FORECAST_TRACE.md beside the trace.

    python -B verify_trace_social.py TRACE.json [--feature-store PATH]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
FEATURE_STORE = "/home/claude/pi_research/p05/predictive_store.sqlite"
TREND = {"EXHAUSTION": 0.0, "STABILITY": 1.0, "ACCELERATION": 2.0}
MANIP = {"MOSTLY ORGANIC": 0.0, "MIXED / UNCERTAIN": 1.0, "LIKELY MANUFACTURED": 2.0, "SEVERELY MANIPULATED": 3.0}


def iso(t):
    return datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def first(lines, rx):
    for s in lines:
        m = re.fullmatch(rx, s)
        if m:
            return m
    return None


def readings(row_json):
    r = json.loads(row_json)
    sn = json.loads(r.get("snapshot_json") or "{}")
    bd = json.loads(r.get("score_breakdown_json") or "{}")
    at = (bd.get("attention_narrative") or {}).get("rationale") or []
    de = (bd.get("demand_order_flow") or {}).get("rationale") or []
    o = {}
    m = first(at, r"attention trend ([A-Z_]+)")
    o["trend"] = TREND.get(m.group(1)) if m else None
    m = first(at, r"narrative strength ([0-9.,-]+)")
    o["strength"] = float(m.group(1)) if m else None
    o["paid"] = 1.0 if "attention paid/boosted" in at else 0.0 if "attention organic" in at else None
    m = first(de, r"manipulation screen (.+) / wash ([A-Za-z/_]+)")
    o["manip"] = MANIP.get(m.group(1).strip().upper()) if m else None
    if o["paid"] == 1.0 or (o["manip"] is not None and o["manip"] >= 2):
        o["suspect"] = 1.0
    elif o["paid"] == 0.0 and o["manip"] is not None:
        o["suspect"] = 0.0
    else:
        o["suspect"] = None
    st = sn.get("lifecycle")
    o["late"] = 1.0 if st in ("DISTRIBUTION", "BREAKDOWN", "POST_BREAKDOWN") else 0.0 if st in (
        "LAUNCH", "DISCOVERY", "EARLY_EXPANSION", "BROAD_ATTENTION", "MANIA") else None
    return o


def channels(token):
    n = 0
    for k in ("website", "twitter", "telegram"):
        v = token.get(k)
        if not isinstance(v, str) or v.strip() in ("", "None", "null", "NULL"):
            continue
        if re.search(r"/search\b|search\?|[?&]q=", v, re.I):
            continue
        if v.strip().lower().startswith(("http://", "https://")):
            n += 1
    return float(n)


def social(con, mint, T, key):
    cur = con.execute("SELECT row_json, token_json FROM predictive_decisions WHERE decision_key=?", (key,)).fetchone()
    a = readings(cur[0])
    v = {"sc_attention_trend_ord": a["trend"], "sc_narrative_strength": a["strength"], "sc_manipulation_ord": a["manip"],
         "sc_attention_suspect": a["suspect"], "sc_lifecycle_late": a["late"], "sc_channels_n": channels(json.loads(cur[1] or "{}"))}
    pr = con.execute("SELECT row_json FROM predictive_decisions WHERE chain='solana' AND mint=? AND decision_time < ? "
                     "ORDER BY decision_time DESC, id DESC LIMIT 1", (mint, T)).fetchone()
    if pr is None:
        v["sc_d_attention_trend"] = v["sc_attention_reversal"] = None
    else:
        b = readings(pr[0])
        if a["trend"] is None or b["trend"] is None:
            v["sc_d_attention_trend"] = v["sc_attention_reversal"] = None
        else:
            v["sc_d_attention_trend"] = a["trend"] - b["trend"]
            v["sc_attention_reversal"] = float(b["trend"] >= 1 and a["trend"] == 0)
    return v, json.loads(cur[1] or "null")


def sig(x):
    return None if x is None else float(f"{x:.10g}")


def v2_value(con, key, name):
    r = con.execute("SELECT v.value FROM predictive_snapshots s JOIN predictive_feature_values v USING(snapshot_key) WHERE s.decision_key=? "
                    "AND s.availability_mode='provider' AND v.feature_name=?", (key, name)).fetchone()
    return r[0] if r else None


def design(body, x):
    cols, prep = body.get("columns") or body["spec"]["columns"], body["prep"]
    X = [x.get(c) for c in cols]
    kept = [X[j] for j in prep["keep"]]
    filled = [prep["med"][i] if (v is None or not math.isfinite(v)) else v for i, v in enumerate(kept)]
    ind = [1.0 if (kept[j] is None or not math.isfinite(kept[j])) else 0.0 for j in prep["ind"]]
    return [(v - m) / s for v, m, s in zip(filled + ind, prep["mu"], prep["sd"])]


def logit_number(body, x):
    lg = body["logistic"]
    z = design(body, x)
    t = lg["intercept"] + sum(c * v for c, v in zip(lg["coef"], z))
    return 1.0 / (1.0 + math.exp(-t))


def stumps_number(body, x):
    st = body["stumps"]
    z = design(body, x)
    raw = st["init"]
    for j, thr, vl, vr in st["trees"]:
        raw += st["lr"] * (vl if z[int(j)] <= thr else vr)
    return 1.0 / (1.0 + math.exp(-raw))


def own_export_token(commit, mint):
    raw = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:data/state/latest.json"], check=True, capture_output=True).stdout
    d = json.loads(raw)
    t = d.get("_tables") or d
    return next((k for k in t.get("tokens") or [] if k.get("mint") == mint), None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("--feature-store", default=FEATURE_STORE)
    a = ap.parse_args()
    tr = json.loads(Path(a.trace).read_text())
    con = sqlite3.connect(f"file:{a.feature_store}?mode=ro", uri=True)
    T, key, mint = float(tr["decision_time"]), tr["decision_key"], tr["mint"]
    mine, stored_tok = social(con, mint, T, key)
    diffs = []
    for k, v in mine.items():
        w = tr["sc_values"].get(k)
        s = sig(v)
        if (s is None) != (w is None) or (s is not None and abs(s - w) > 1e-9 * max(1.0, abs(s))):
            diffs.append(f"{k}: recomputed {s!r} vs trace {w!r}")
    own = own_export_token(tr["export_commit"], mint)
    if json.dumps(own, sort_keys=True) != json.dumps(stored_tok, sort_keys=True):
        diffs.append("stored token row differs from the token row of the decision's own export (CX-10)")
    late = [k for k, av in tr["sc_available_at"].items() if av is not None and av > T]
    x = {}
    for c in ("thesis_log1p_liquidity_usd", "thesis_log1p_mcap_usd", "thesis_log1p_vol_24h_usd", "thesis_fatal_present"):
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
            a_, b_ = x.get("sc_attention_trend_ord"), x.get("sc_attention_suspect")
            cell = "MISSING" if a_ is None or b_ is None else f"T{int(a_)}S{int(b_)}"
            got = body["cells"][cell]["p"] if cell in body["cells"] else body["b0"]
        else:
            req = body.get("required") or body["spec"]["rows"]
            if any(x.get(c) is None for c in req):
                got = None
            elif "stumps" in body:
                got = stumps_number(body, x)
            else:
                got = logit_number(body, x)
        nums[m] = got
        w = d["number"]
        if (got is None) != (w is None) or (got is not None and abs(got - w) > 1e-12):
            diffs.append(f"model {m}: recomputed {got!r} vs trace {w!r}")
        if d["card"]["training_cutoff"] > T:
            diffs.append(f"model {m}: card trained after the decision")
    ev = tr.get("event_without_post_event_text") or {}
    rep = {"decision_key": key, "decision_time_utc": iso(T), "values_compared": len(mine), "inputs_compared": len(tr["model_inputs"]),
           "models_compared": len(nums), "differences": diffs, "values_available_after_T": late,
           "token_row_equals_own_export": own == stored_tok, "event_without_post_event_text": ev.get("pass"),
           "invalid_inputs_all_rejected": tr.get("invalid_inputs_all_rejected"),
           "pass": not diffs and not late and tr.get("invalid_inputs_all_rejected") is True and ev.get("pass") is True}
    out = Path(a.trace).with_name("verify_trace.json")
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    md = ["# Phase 10 forecast trace", "",
          f"Decision `{key}` of mint `{mint}` at {iso(T)} (EXPORT_COMMIT `{tr['export_commit'][:10]}`), target `{tr['target']}`, fold "
          f"{tr['fold']} (cutoff {tr['fold_cutoff_utc']}), label {tr['label_y']}.",
          f"Row sha256 `{tr['row_sha256']}`; socialcat-1 snapshot sha `{tr['sc_snapshot_sha']}`. Status PROVISIONAL_PENDING_REVISION_REREAD.",
          f"Catalyst state {tr['catalyst_state']}; social state {tr['social_state']}; lab event classes: {', '.join(tr['lab_event_classes']) or 'none'}.", "",
          "## Lab readings behind the values", "", f"- Snapshot fields: {json.dumps(tr['snapshot_fields'], sort_keys=True)}",
          f"- Token row of the decision's export: {json.dumps(tr['token_row'], sort_keys=True)}"]
    for b, lines in tr["rationale"].items():
        md.append(f"- {b}: " + "; ".join(lines or []))
    if tr.get("prior_decision"):
        md.append(f"- Previous decision `{tr['prior_decision']['decision_key']}` at {iso(tr['prior_decision']['decision_time'])}: "
                  f"{json.dumps(tr['prior_decision']['snapshot_fields'], sort_keys=True)}; " + "; ".join(tr["prior_decision"]["attention_narrative"] or []))
    md += ["", "## socialcat-1 values", "", "| Feature | Value | Missing reason |", "|---|---|---|"]
    for k, v in tr["sc_values"].items():
        md.append(f"| `{k}` | {v if v is not None else ''} | {tr['sc_reasons'].get(k, '')} |")
    md += ["", "## Models (fold cards)", "", "| Model | Card sha | Cutoff | Number | Abstain |", "|---|---|---|---|---|"]
    for m, d in tr["models"].items():
        md.append(f"| {m} | `{d['card_model_sha'][:16]}` | {d['training_cutoff_utc']} | {'' if d['number'] is None else round(d['number'], 6)} | {d['abstain'] or ''} |")
    md += ["", "## Event without post-event text", "", f"- {json.dumps(ev, sort_keys=True)}"]
    md += ["", "## Invalid inputs", ""] + [f"- {k}: {v}" for k, v in tr["invalid_inputs"].items()]
    md += ["", "## Independent recomputation", "", f"`verify_trace_social.py` (no socialcat.py, no features.py): {len(mine)} values, "
           f"{len(tr['model_inputs'])} model inputs and {len(nums)} model numbers recomputed; token row equal to the decision's own "
           f"export: {own == stored_tok}; differences: {len(diffs)}; values available after the decision: {len(late)}; pass: {rep['pass']}.", ""]
    Path(a.trace).with_name("FORECAST_TRACE.md").write_text("\n".join(md))
    print(json.dumps({k: rep[k] for k in ("values_compared", "inputs_compared", "models_compared", "pass")} | {"differences": len(diffs)}))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
