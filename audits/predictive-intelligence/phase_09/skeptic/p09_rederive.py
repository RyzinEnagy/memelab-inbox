"""Skeptic 09: re-derive onchain-1 features for 10 labelled development decisions from the git exports themselves (not from
the store and not with onchain.py), and prove the row each value comes from is first held by the export at the decision time.
Usage: python -I p09_rederive.py CLONE P05_STORE_COPY FEATURES_CSV"""
import csv, hashlib, json, math, sqlite3, subprocess, sys
clone, store, fcsv = sys.argv[1:4]
git = lambda *a: subprocess.run(["git", "-C", clone, *a], capture_output=True, text=True, check=True).stdout
P = "data/state/latest.json"
fp = [ln.split() for ln in git("rev-list", "--reverse", "--first-parent", "--timestamp", "refs/remotes/origin/main", "--", P).splitlines()]
order = {c: i for i, (t, c) in enumerate(fp)}
ctime = {c: float(t) for t, c in fp}
cache = {}
def export(c):
    if c not in cache:
        d = json.loads(git("show", f"{c}:{P}"))
        t = d.get("_tables", d)
        cache[c] = t
    return cache[c]
def rsha(row):  # my own canonical form, written from the spec (row without id, sorted keys, compact)
    return hashlib.sha256(json.dumps({k: v for k, v in row.items() if k != "id"}, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
def first_holder(mint, sha):
    for t, c in fp:
        if any(r["mint"] == mint and rsha(r) == sha for r in export(c).get("theses") or []):
            return c
    return None
STRUCT = {"MINT_AUTHORITY_ACTIVE", "FREEZE_AUTHORITY_ACTIVE", "PERMANENT_DELEGATE", "TRANSFER_FEE_GT_5PCT", "TRANSFER_HOOK_UNKNOWN",
          "NON_TRANSFERABLE", "HONEYPOT", "CANNOT_BUY", "HIDDEN_OWNER", "EXTREME_TAX", "SIMULATION_FAILED", "AIRDROP_SCAM", "SELFDESTRUCT",
          "CREATOR_PRIOR_HONEYPOT", "PROXY_WITH_LIVE_OWNER", "TAX_MODIFIABLE_BY_OWNER", "LP_RISK_CRITICAL", "NO_SELL_ROUTE", "CANNOT_EXIT_5K"}
def mine(row, tok):
    bd = json.loads(row["score_breakdown_json"])
    lines = [s for b in bd.values() if isinstance(b, dict) for s in (b.get("rationale") or [])]
    def after(prefix):
        hits = [s[len(prefix):] for s in lines if s.startswith(prefix)]
        return hits[0] if hits else None
    flags = [f["flag"] for f in json.loads(row["fatal_flags_json"] or "[]")]
    snap = json.loads(row["snapshot_json"])
    lr = after("LP risk ")
    lk = after("LP locked/burned ")
    lg = after("largest unexplained holder ")
    out = {"oc_structural_fatal": float(any(f in STRUCT for f in flags)),
           "oc_lp_risk_ord": {"LOW": 0.0, "MODERATE": 1.0, "HIGH": 2.0, "CRITICAL": 3.0}.get(lr),
           "oc_lp_locked_pct": float(lk.rstrip("%")) if lk else None,
           "oc_largest_unexplained_pct": float(lg.rstrip("%")) if lg else None,
           "oc_exit_cap_share": (snap["exit_cap_3pct"] / snap["liquidity"]) if snap.get("liquidity") and snap.get("exit_cap_3pct") is not None else None,
           "oc_token2022": {"TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb": 1.0, "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": 0.0}.get((tok or {}).get("token_program")),
           "_t": snap.get("t")}
    return out
con = sqlite3.connect(store); con.row_factory = sqlite3.Row
rows = list(csv.DictReader(open(fcsv)))
pick = sorted(rows, key=lambda r: r["decision_key"])
with_prior = [r for r in pick if r["oc_prior_gap_h"] not in ("NO_PRIOR_DECISION", "")]
sel = with_prior[::max(1, len(with_prior) // 6)][:6] + [r for r in pick if r not in with_prior][::20][:4]
report, diffs = [], 0
for r in sel:
    d = dict(con.execute("SELECT * FROM predictive_decisions WHERE decision_key=?", (r["decision_key"],)).fetchone())
    c = d["export_commit"]
    first = first_holder(r["mint"], r["row_sha256"])
    ex = export(c)
    grow = next(x for x in ex["theses"] if x["mint"] == r["mint"] and rsha(x) == r["row_sha256"])
    tok = next((k for k in ex.get("tokens") or [] if k["mint"] == r["mint"]), None)
    m = mine(grow, tok)
    T = ctime[c]
    checks = {"first_holder_is_export_commit": first == c, "commit_time_is_decision_time": abs(T - d["decision_time"]) < 1e-6,
              "store_row_equals_git_row": json.loads(d["row_json"]) == {k: v for k, v in grow.items() if k != "id"},
              "snapshot_t_before_T": m["_t"] is not None and m["_t"] <= T}
    vals = {}
    for k in ("oc_structural_fatal", "oc_lp_risk_ord", "oc_lp_locked_pct", "oc_largest_unexplained_pct", "oc_exit_cap_share", "oc_token2022"):
        theirs = r[k]
        th = float(theirs) if theirs not in ("", None) and not theirs.isalpha() and "_" not in theirs else theirs
        ok = (m[k] is None and isinstance(th, str)) or (isinstance(th, float) and m[k] is not None and abs(th - m[k]) <= 1e-6 * max(1, abs(m[k])))
        vals[k] = [m[k], th, ok]
        diffs += not ok
    cap = T - m["_t"]
    vals["oc_capture_delay_s"] = [cap, r["oc_capture_delay_s"], abs(cap - float(r["oc_capture_delay_s"])) < 1e-3 * max(1, cap)]
    diffs += not vals["oc_capture_delay_s"][2]
    if r["oc_prior_gap_h"] not in ("NO_PRIOR_DECISION",):
        prev = [dict(x) for x in con.execute("SELECT * FROM predictive_decisions WHERE chain=? AND mint=? AND decision_time<? ORDER BY decision_time",
                                              (d["chain"], d["mint"], d["decision_time"]))][-1]
        pex = export(prev["export_commit"])
        prow = next(x for x in pex["theses"] if x["mint"] == r["mint"] and rsha(x) == prev["row_sha256"])
        pm = mine(prow, None)
        pfirst = first_holder(r["mint"], prev["row_sha256"])
        dl = (m["oc_lp_locked_pct"] - pm["oc_lp_locked_pct"]) if m["oc_lp_locked_pct"] is not None and pm["oc_lp_locked_pct"] is not None else None
        gap = (T - ctime[prev["export_commit"]]) / 3600
        vals["oc_d_lp_locked_pp"] = [dl, r["oc_d_lp_locked_pp"], dl is not None and abs(dl - float(r["oc_d_lp_locked_pp"])) < 1e-6]
        vals["oc_prior_gap_h"] = [gap, r["oc_prior_gap_h"], abs(gap - float(r["oc_prior_gap_h"])) < 1e-6 * max(1, gap)]
        checks["prior_first_holder_before_T"] = pfirst == prev["export_commit"] and order[pfirst] < order[c]
        diffs += (not vals["oc_d_lp_locked_pp"][2]) + (not vals["oc_prior_gap_h"][2])
    report.append({"decision_key": r["decision_key"][:12], "mint": r["mint"][:8], "T": r["decision_time_utc"], "checks": checks, "values": vals})
bad_checks = sum(1 for x in report for v in x["checks"].values() if not v)
print(json.dumps({"decisions": len(report), "value_differences": diffs, "failed_availability_checks": bad_checks, "detail": report}, indent=1, default=str))
