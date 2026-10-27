"""Phase 19 skeptic: recompute every LABELED prospective outcome from the archived raw bodies without importing memelab.

Usage: python -I p19_independent_labels.py REPO_CLONE OUT.json
Rules implemented from phase_06/labels/TARGET_SCHEMA.md (labels-1) only:
  t_entry = D + 300; reference candle = newest candle with end + 300 <= D and end >= D - 3600, P0 = its close;
  path = candles with start >= t_entry and end <= t_entry + H; candles ending after the read boundary are dropped;
  T1/T1b: first path candle with high >= 1.25 P0 or low <= 0.85 P0 (both = AMBIGUOUS_BAR); none = NEITHER (or
  NO_TRADES_AFTER_ENTRY when the path is empty); T2: low <= 0.5 P0 in the 24 h path = DRAWDOWN_50, else NO_SEVERE_EVENT
  (halts are not re-derived: the phase reported 0 records needing other pools).
Also: body sha256 equals the manifest and the ledger; meta base address equals the mint; label read after maturity;
BSS of B2 vs B0 on the scored rows recomputed from PROSPECTIVE_PREDICTIONS.csv and these labels.
"""
import csv
import gzip
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

repo = Path(sys.argv[1])
PH = repo / "audits/predictive-intelligence/phase_19"
T1, T1B, T2 = ("price_path_target_before_invalidation_24h", "price_path_target_before_invalidation_6h",
               "price_path_severe_drawdown_or_halt_24h")
H = {T1: 86400, T1B: 6 * 3600, T2: 86400}
MAT = {T1: 300 + 86400 + 900, T1B: 300 + 6 * 3600 + 900, T2: 300 + 86400 + 86400 + 900}
SHORT = {T1: "T1_24h", T1B: "T1b_6h", T2: "T2_24h"}

man = {r["response_key"]: r for r in csv.DictReader(open(PH / "raw/MANIFEST.csv")) if r["response_key"]}
ledger = [json.loads(x) for x in open(PH / "monitoring/OUTCOME_LEDGER.jsonl")]
outs = {}
for e in ledger:
    p = e["payload"]
    if p["kind"] == "OUTCOME":
        outs[(p["decision_key"], p["target"])] = p      # last wins (no revisions exist)


def iso2t(s):
    from datetime import datetime, timezone
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def candles_of(rk, mint):
    m = man[rk]
    raw = gzip.open(PH / "raw" / m["file"]).read()
    assert hashlib.sha256(raw).hexdigest() == m["body_sha256"], "body sha mismatch"
    d = json.loads(raw)
    base = d["meta"]["base"]["address"]
    b = iso2t(m["boundary_at"])
    cs = {}
    for r in d["data"]["attributes"]["ohlcv_list"]:
        t, o, h, l, c, v = [float(x) for x in r]
        if t + 300 > b:
            continue
        if min(o, h, l, c) <= 0:
            continue
        cs[t] = (t, o, h, l, c, v)
    return sorted(cs.values()), base, m


def classify(target, D, cs):
    ref = None
    for c in cs:
        end = c[0] + 300
        if end + 300 <= D and end >= D - 3600 and (ref is None or c[0] > ref[0]):
            ref = c
    if ref is None:
        return None, None
    p0 = ref[4]
    te = D + 300
    path = [c for c in cs if c[0] >= te and c[0] + 300 <= te + H[target]]
    if target == T2:
        for c in path:
            if c[3] <= 0.5 * p0:
                return "DRAWDOWN_50", p0
        return "NO_SEVERE_EVENT", p0
    for c in path:
        up, lo = c[2] >= 1.25 * p0, c[3] <= 0.85 * p0
        if up or lo:
            return ("AMBIGUOUS_BAR" if up and lo else "TARGET_FIRST" if up else "INVALIDATION_FIRST"), p0
    return ("NEITHER" if path else "NO_TRADES_AFTER_ENTRY"), p0


res = {"compared": 0, "equal": 0, "diffs": [], "checks": defaultdict(int), "by_target": defaultdict(lambda: [0, 0])}
mine = {}
for (k, t), p in sorted(outs.items()):
    if p["state"] != "LABELED":
        continue
    cs, base, m = candles_of(p["response_key"], p["mint"])
    res["checks"]["body_sha_equal_ledger"] += int(m["body_sha256"] == p["body_sha256"])
    res["checks"]["meta_base_is_mint"] += int(base == p["mint"])
    res["checks"]["token_param_in_url"] += int(("token=" + p["mint"]) in m["request_url"])
    res["checks"]["read_after_maturity"] += int(float(m["retrieved_t"]) >= p["decision_time"] + MAT[t])
    res["checks"]["maturity_equal"] += int(abs(p["label_matures_at"] - (p["decision_time"] + MAT[t])) < 1e-6)
    cls, p0 = classify(t, p["decision_time"], cs)
    lab = 1 if cls in ("TARGET_FIRST", "DRAWDOWN_50", "TRADING_HALT") else 0
    mine[(k, t)] = lab
    res["compared"] += 1
    if cls == p["label_class"] and lab == p["label"]:
        res["equal"] += 1
    else:
        res["diffs"].append({"key": k[:12], "target": SHORT[t], "mine": cls, "ledger": p["label_class"]})
    res["by_target"][SHORT[t]][0] += 1
    res["by_target"][SHORT[t]][1] += lab

# non-LABELED states: never carry a label
res["non_labeled_with_label"] = sum(1 for p in outs.values() if p["state"] != "LABELED" and p["label"] is not None)
res["states"] = defaultdict(int)
for (k, t), p in outs.items():
    res["states"][SHORT[t] + ":" + p["state"]] += 1
pend = [p for p in outs.values() if p["state"] == "PENDING"]
res["pending"] = {"n": len(pend), "targets": sorted({SHORT[p["target"]] for p in pend}),
                  "matures_utc_min": min(p["label_matures_at"] for p in pend) if pend else None,
                  "any_pending_matured_before_reads": any(p["label_matures_at"] <= 1793109626 for p in pend)}

# scored rows: exactly my LABELED set?  BSS of B2 vs B0 on them
pred = defaultdict(dict)
for r in csv.DictReader(open(PH / "monitoring/PROSPECTIVE_PREDICTIONS.csv")):
    if r["candidate"] in ("P07_B0", "P07_B2") and r["number"] != "":
        pred[(r["target_short"], r["decision_key"])][r["candidate"]] = float(r["number"])
scored = defaultdict(set)
for r in csv.DictReader(open(PH / "monitoring/PROSPECTIVE_SCORED.csv")):
    scored[r["target_short"]].add((r["decision_key"], int(r["y"])))
res["bss"] = {}
for t in (T1, T1B, T2):
    s = SHORT[t]
    rows = [(k, y) for (k, tt), y in mine.items() if tt == t]
    res["checks"]["scored_set_equal_" + s] = int(set(rows) == scored[s])
    b0 = sum((pred[(s, k)]["P07_B0"] - y) ** 2 for k, y in rows) / len(rows)
    b2 = sum((pred[(s, k)]["P07_B2"] - y) ** 2 for k, y in rows) / len(rows)
    days = len({outs[(k, t)]["decision_time"] // 86400 for k, _ in rows})
    res["bss"][s] = {"n": len(rows), "pos": sum(y for _, y in rows), "days": days, "brier_b2": round(b2, 4),
                     "brier_b0": round(b0, 4), "bss": round(1 - b2 / b0, 3)}
res["checks"] = dict(res["checks"])
res["by_target"] = dict(res["by_target"])
res["states"] = dict(res["states"])
Path(sys.argv[2]).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
print(json.dumps({k: res[k] for k in ("compared", "equal", "diffs", "checks", "bss", "pending", "non_labeled_with_label")}, indent=0))
