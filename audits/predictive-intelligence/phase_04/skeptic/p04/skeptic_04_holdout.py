"""Skeptic 04: holdout integrity and independent label re-derivation from the raw GeckoTerminal bodies.
Own reference/path/barrier code (does not call contract.reference_candle, path_candles or build_dev_sample.barrier_class).
Uses memelab.predictive.decisions (Phase 01, already skeptic-reviewed) only to enumerate decision events.
    python -I -B skeptic_04_holdout.py REPO RAW_DIR OUT_JSON
"""
import csv, hashlib, json, sys, subprocess, collections, urllib.parse as up
from pathlib import Path
from datetime import datetime, timezone

repo, raw, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(repo))
from memelab.predictive import decisions as D  # noqa
from memelab.predictive import contract as C  # noqa (constants only)

A = repo / "audits/predictive-intelligence/phase_04/adoption/data"
H0 = datetime(2026, 10, 17, tzinfo=timezone.utc).timestamp()
H1 = datetime(2026, 10, 24, tzinfo=timezone.utc).timestamp()
REF = "98338a8ba3c5e65c5850933a35c06885b6ef991a"
iso = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
res = {}

calls = json.loads((A / "dev_sample_calls.json").read_text())
plan = json.loads((A / "dev_sample_plan.json").read_text())
bad_sha, before_gt_h0, beyond_before, late = [], [], [], []
inclusive_eq, inclusive_n = 0, 0
cand = collections.defaultdict(dict)
for c in calls:
    if c["http"] != 200:
        continue
    b = (raw / c["file"]).read_bytes()
    if hashlib.sha256(b).hexdigest() != c["sha256"]:
        bad_sha.append(c["file"])
    q = up.parse_qs(up.urlparse(c["url"]).query)
    bt = int(q["before_timestamp"][0])
    if bt > H0:
        before_gt_h0.append(c["tag"])
    lst = json.loads(b)["data"]["attributes"]["ohlcv_list"]
    pool = up.urlparse(c["url"]).path.split("/pools/")[1].split("/")[0]
    assert pool == plan["pools"][int(c["tag"][1:4])]["pool"]
    if lst:
        mx = max(int(r[0]) for r in lst)
        inclusive_n += 1
        if mx == bt:
            inclusive_eq += 1
        if mx > bt:
            beyond_before.append((c["tag"], mx - bt))
    for r in lst:
        if int(r[0]) >= H0:
            late.append((c["tag"], int(r[0]) - H0))
            continue
        cand[pool][int(r[0])] = [float(x) for x in r]
res["raw"] = {"bodies_200": sum(1 for c in calls if c["http"] == 200), "sha_mismatch": bad_sha,
              "before_timestamp_gt_h0": before_gt_h0, "max_before_minus_h0": max(int(up.parse_qs(up.urlparse(c["url"]).query)["before_timestamp"][0]) for c in calls) - H0,
              "candles_beyond_before_timestamp": beyond_before,
              "bodies_whose_newest_candle_equals_before_timestamp": [inclusive_eq, inclusive_n],
              "candles_at_or_after_h0": late}
# pace
ts = sorted(c["retrieved_t"] for c in calls)
mx60 = max(sum(1 for u in ts if t <= u < t + 60) for t in ts)
res["pace"] = {"calls": len(ts), "max_calls_in_any_60s": mx60, "min_gap_s": round(min(b - a for a, b in zip(ts, ts[1:])), 2),
               "http": dict(collections.Counter(c["http"] for c in calls))}

# decisions
git = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True).stdout
revs = [l.split() for l in git("rev-list", "--reverse", "--first-parent", "--timestamp", REF, "--", "data/state/latest.json").decode().splitlines() if l.strip()]
ex = [D.export_from_doc(s, int(t), json.loads(git("show", f"{s}:data/state/latest.json"))) for t, s in revs]
evs = D.decisions(D.candidates(ex))
fetched = set(cand)
hold = [e for e in evs if e["chain"] == "solana" and H0 <= e["decision_time"] < H1]
hold_on_fetched = [e for e in hold if e["pool_pit"] in fetched]
def ref_ok(pool, d):
    return [s for s in cand[pool] if s + 600 <= d and s + 300 >= d - 3600]
def lookback_ok(pool, d):
    return [s for s in cand[pool] if s + 600 <= d and s + 300 >= d - 86400]
res["holdout"] = {"holdout_decisions_solana": len(hold), "on_fetched_pools": len(hold_on_fetched),
                  "with_a_fetched_pre_h0_candle_usable_as_reference": sorted((e["mint"][:6], iso(e["decision_time"])) for e in hold_on_fetched if ref_ok(e["pool_pit"], e["decision_time"])),
                  "with_a_fetched_pre_h0_candle_in_24h_lookback": len([e for e in hold_on_fetched if lookback_ok(e["pool_pit"], e["decision_time"])]),
                  "contacted_on_fetched_pools": [m[:6] for m, t in C.ACCEPTANCE["holdout_contacted"]["decisions"] if any(e["mint"] == m for e in hold_on_fetched)]}

# independent labels
def ref(pool, d):
    ok = ref_ok(pool, d)
    return max(ok) if ok else None
def label(pool, d, H):
    s0 = ref(pool, d); p0 = cand[pool][s0][4]
    te = d + 300
    path = sorted(s for s in cand[pool] if s >= te and s + 300 <= te + H)
    if not path:
        return s0, "NO_TRADES_AFTER_ENTRY"
    for s in path:
        hi, lo = cand[pool][s][2], cand[pool][s][3]
        if hi >= 1.25 * p0 and lo <= 0.85 * p0: return s0, "AMBIGUOUS_BAR"
        if hi >= 1.25 * p0: return s0, "TARGET_FIRST"
        if lo <= 0.85 * p0: return s0, "INVALIDATION_FIRST"
    return s0, "NEITHER"
def mature(d, H): return d + 300 + H + 900
dev = [e for e in evs if e["chain"] == "solana" and e["snapshot"].get("price") and e["pool_pit"] and e["decision_time"] < H0 and mature(e["decision_time"], 21600) <= H0]
for H, fname in ((86400, "dev_t1_24h.csv"), (21600, "dev_t1b_6h.csv")):
    rows = list(csv.DictReader(open(A / fname)))
    devH = [e for e in dev if mature(e["decision_time"], H) <= H0]
    # own eligibility: ELIGIBLE iff a reference candle exists and the pool read was ok
    elig = [e for e in devH if e["pool_pit"] in cand and ref(e["pool_pit"], e["decision_time"]) is not None]
    kept, last = [], {}
    for e in sorted(elig, key=lambda e: (e["mint"], e["decision_time"])):
        if e["mint"] not in last or e["decision_time"] >= last[e["mint"]] + H:
            kept.append(e); last[e["mint"]] = e["decision_time"]
    mine = {}
    for e in kept:
        s0, k = label(e["pool_pit"], e["decision_time"], H)
        mine[(e["mint"], e["decision_time"])] = (s0, k)
    theirs = {(r["mint"], float(r["decision_time"])): (int(r["p0_candle_start"]), r["label_class"]) for r in rows}
    diff = [(k[0][:6], iso(k[1]), mine.get(k), theirs.get(k)) for k in set(mine) | set(theirs) if mine.get(k) != theirs.get(k)]
    res[fname] = {"rows": len(rows), "mine": len(mine), "differences": diff[:20], "n_diff": len(diff),
                  "classes_mine": dict(collections.Counter(v[1] for v in mine.values())),
                  "max_decision": iso(max(float(r["decision_time"]) for r in rows)),
                  "max_label_matures": iso(max(float(r["label_matures_at"]) for r in rows)),
                  "rows_at_or_after_h0": sum(float(r["decision_time"]) >= H0 for r in rows),
                  "contacted_mints_in_rows": [r["mint"][:6] for r in rows if r["mint"] in {m for m, _ in C.ACCEPTANCE["holdout_contacted"]["decisions"]}],
                  "max_path_candle_end_used": iso(max(float(r["decision_time"]) + 300 + H for r in rows))}
out.write_text(json.dumps(res, indent=1, default=str) + "\n")
print(json.dumps(res, indent=1, default=str))
