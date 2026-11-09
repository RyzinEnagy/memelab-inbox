"""Phase 20 skeptic: own recompute of Phase 19 labels and P07_B2 reference numbers (no lab module, no Phase 20 probe imported).

    python3 -I -B p20_own_recompute.py CLONE OUT.json

Labels: 14 Phase 19 LABELED outcomes (current entry per decision and target), chosen by sha256 of decision_key+target (a
different sample rule from Phase 20's "all"), recomputed from the archived GeckoTerminal body with numpy-free code written from
the target registry text in contract.TARGETS (barriers 1.25 / 0.85, drawdown 0.5, halt span t_entry+18h..+48h, 300 s entry lag,
reference candle end+lag <= T within 3600 s). B2: 12 decisions picked by sha256 order (not Phase 20's first-30 rule), export row
from `git show`, inputs and the logistic from the frozen card, compared with PROSPECTIVE_PREDICTIONS.csv.
"""
import csv
import gzip
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

CL = Path(sys.argv[1])
A = CL / "audits/predictive-intelligence"
GITREPO = sys.argv[3] if len(sys.argv) > 3 else str(CL)   # read-only git log/show for origin/main exports
H = {"price_path_target_before_invalidation_24h": 86400, "price_path_target_before_invalidation_6h": 21600,
     "price_path_severe_drawdown_or_halt_24h": 86400}


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def label(target, T, rows, boundary):
    # rows: [start, o, h, l, c, v]; keep candles fully closed by the vendor boundary
    cs = sorted({int(float(r[0])): [float(x) for x in r[:6]] for r in rows if float(r[0]) + 300 <= boundary}.values())
    refs = [c for c in cs if T - 3600 <= c[0] + 300 and c[0] + 600 <= T]
    if not refs:
        return ("NO_REFERENCE", None)
    p0 = refs[-1][4]
    te = T + 300
    hor = H[target]
    path = [c for c in cs if c[0] >= te and c[0] + 300 <= te + hor]
    complete = boundary >= math.ceil((te + hor) / 300) * 300 and cs[0][0] < te
    if target != "price_path_severe_drawdown_or_halt_24h":
        for c in path:
            hi, lo = c[2] >= 1.25 * p0, c[3] <= 0.85 * p0
            if hi and lo:
                return ("AMBIGUOUS_BAR", 0)
            if hi:
                return ("TARGET_FIRST", 1)
            if lo:
                return ("INVALIDATION_FIRST", 0)
        if not complete:
            return ("UNVERIFIABLE", None)
        return ("NEITHER", 0) if path else ("NO_TRADES_AFTER_ENTRY", 0)
    if any(c[3] <= 0.5 * p0 for c in path):
        return ("DRAWDOWN_50", 1)
    if not complete:
        return ("UNVERIFIABLE", None)
    if any(c[0] < te + 172800 and c[0] + 300 > te + 64800 for c in cs):
        return ("NO_SEVERE_EVENT", 0)
    return ("HALT_NEEDS_OTHER_POOLS", None)


def labels(n=14):
    cur = {}
    for line in (A / "phase_19/monitoring/OUTCOME_LEDGER.jsonl").read_text().splitlines():
        p = json.loads(line)["payload"]
        if p.get("kind") == "OUTCOME":
            cur[(p["decision_key"], p["target"])] = p
    lab = sorted(((k, o) for k, o in cur.items() if o["state"] == "LABELED"), key=lambda x: h(x[0][0] + x[0][1]))
    # stratify: take the first n by hash but make sure every target appears
    pick, seen = [], set()
    for k, o in lab:
        if len(pick) < n - 3 or o["target"] not in seen:
            pick.append((k, o))
            seen.add(o["target"])
        if len(pick) >= n:
            break
    man = {r["response_key"]: r for r in csv.DictReader(open(A / "phase_19/raw/MANIFEST.csv"))}
    out = []
    for (dk, t), o in pick:
        m = man[o["response_key"]]
        body = gzip.decompress((A / "phase_19/raw" / m["file"]).read_bytes())
        ok_sha = hashlib.sha256(body).hexdigest() == m["body_sha256"]
        d = json.loads(body)
        tok = parse_qs(urlsplit(m["request_url"]).query)["token"][0]
        base = d["meta"]["base"]["address"]
        rows = d["data"]["attributes"]["ohlcv_list"]
        got = label(t, float(o["decision_time"]), rows, ts(m["boundary_at"]))
        out.append({"decision_key": dk[:16], "target": t, "ledger": [o["label_class"], o["label"]], "mine": list(got),
                    "identity_ok": tok == o["mint"] == base, "body_sha_ok": ok_sha,
                    "equal": list(got) == [o["label_class"], o["label"]]})
    return out


def git(*a):
    return subprocess.run(["git", "-C", GITREPO, *a], capture_output=True, text=True, check=True).stdout


def b2(n=12):
    preds = list(csv.DictReader(open(A / "phase_19/monitoring/PROSPECTIVE_PREDICTIONS.csv")))
    rec = {(r["decision_key"], r["target_short"]): r for r in preds if r["candidate"] == "P07_B2"}
    keys = sorted({k for (k, _), r in rec.items() if r["number"] and r["chain"] == "solana"}, key=lambda k: h("sk20" + k))
    commits = {}
    for line in git("log", "--format=%H %ct", "refs/remotes/origin/main", "--", "data/state/latest.json").splitlines():
        c, t = line.split()
        commits[int(t)] = c
    out, used = [], 0
    for dk in keys:
        if used >= n:
            break
        any_r = next(r for (k, _), r in rec.items() if k == dk)
        T = float(any_r["decision_time"])
        c = commits.get(int(T))
        if c is None:
            continue
        used += 1
        ex = json.loads(git("show", f"{c}:data/state/latest.json"))
        tb = ex.get("_tables") or ex
        rows = [x for x in tb["theses"] if x["mint"] == any_r["mint"]]
        row = max(rows, key=lambda x: float(x["created_at"]))
        tok = next((x for x in tb["tokens"] if x["mint"] == any_r["mint"]), {}) or {}
        snap = json.loads(row.get("snapshot_json") or "{}")
        ff = json.loads(row.get("fatal_flags_json") or "null")

        def lg(v):
            return math.log1p(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0 else float("nan")
        fp = tok.get("first_pool_at")
        age = (T - ts(fp)) / 86400 if isinstance(fp, str) and fp else float("nan")
        x = [lg(snap.get("liquidity")), lg(snap.get("mcap")), lg(snap.get("vol_24h")),
             (1.0 if ff else 0.0) if isinstance(ff, list) else float("nan"), math.log1p(age) if age == age and age >= 0 else float("nan")]
        for tshort, folder in (("T1_24h", "T1_24h"), ("T1b_6h", "T1b_6h"), ("T2_24h", "T2_24h")):
            card = json.loads((A / f"phase_07/artifacts/{folder}/B2.json").read_text())["body"]
            pr, lo = card["prep"], card["logistic"]
            if any(not math.isfinite(x[i]) for i in range(4)):
                mine = None
            else:
                v = [x[i] for i in pr["keep"]]
                miss = [not math.isfinite(z) for z in v]
                v = [pr["med"][i] if miss[i] else z for i, z in enumerate(v)] + [1.0 if miss[i] else 0.0 for i in pr["ind"]]
                s = lo["intercept"] + sum(cf * (vv - mu) / sd for cf, vv, mu, sd in zip(lo["coef"], v, pr["mu"], pr["sd"]))
                mine = 1 / (1 + math.exp(-s))
            r = rec.get((dk, tshort))
            recd = float(r["number"]) if r and r["number"] else None
            out.append({"decision_key": dk[:16], "target": tshort, "recorded": recd, "mine": mine,
                        "abs_diff": None if (mine is None or recd is None) else abs(mine - recd),
                        "equal": (mine is None and recd is None) or (mine is not None and recd is not None and abs(mine - recd) <= 1e-8)})
    return out


L, Bn = labels(), b2()
res = {"labels": L, "labels_equal": sum(r["equal"] for r in L), "labels_n": len(L), "b2": Bn, "b2_equal": sum(r["equal"] for r in Bn),
       "b2_n": len(Bn), "b2_max_abs_diff": max((r["abs_diff"] or 0) for r in Bn)}
Path(sys.argv[2]).write_text(json.dumps(res, indent=1))
print({k: v for k, v in res.items() if not isinstance(v, list)})
for r in L:
    if not r["equal"]:
        print("LABEL DIFF", r)
for r in Bn:
    if not r["equal"]:
        print("B2 DIFF", r)
