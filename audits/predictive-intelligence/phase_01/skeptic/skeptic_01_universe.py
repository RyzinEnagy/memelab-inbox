"""Phase 01 skeptic: independent re-derivation of the decision universe, written without reusing the phase's probe code.

Run from a clone of the repo (read-only, no network):
    python /home/claude/pi_orchestration/skeptic/skeptic_01_universe.py origin/main OUT.json

Checks:
  A. counts: export versions, theses, mints by chain (chain from ANY export's token row, not defaulted), thinned and
     matured counts for 6 h / 24 h / 7 d, split counts against the frozen holdout window;
  B. thesis rows whose content changes between exports under the same (mint, created_at) key;
  C. duplicate theses: same mint and identical snapshot_json under different created_at keys (re-stamped copies);
  D. theses whose first export has no token row (chain silently defaulted to solana by the phase probe);
  E. theses that vanish from an export and reappear later; theses whose first export is one of the 7 unconfirmed commits;
  F. commit time ordering: first-parent linear, monotonic.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import subprocess
import sys

H = {"6h": 21600, "24h": 86400, "7d": 604800}
LAG, MARGIN = 300, 900
HOLD = ("2026-10-17T00:00:00Z", "2026-10-24T00:00:00Z")
UNCONFIRMED = ("996190ce", "2c6cbf54", "53a616e1", "fe8fc3bb", "6e09bfae", "1aa6fcd1", "98338a8b")


def git(*a):
    return subprocess.run(["git", *a], check=True, capture_output=True).stdout


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def h(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()[:16]


def main(ref, out):
    revs = [l.split() for l in git("rev-list", "--reverse", "--first-parent", "--timestamp", ref, "--", "data/state/latest.json").decode().split("\n") if l]
    revs = [(s, int(t)) for t, s in revs]
    res = {"export_versions": len(revs)}
    mono = all(revs[i][1] <= revs[i + 1][1] for i in range(len(revs) - 1))
    res["F_commit_times_monotonic_first_parent"] = mono
    first = {}           # key -> dict
    content = collections.defaultdict(set)
    present = collections.defaultdict(list)   # key -> list of export idx
    chain_any = {}
    no_token_row_first = 0
    for i, (sha, ct) in enumerate(revs):
        doc = json.loads(git("show", f"{sha}:data/state/latest.json"))
        tb = doc.get("_tables") or {k: v for k, v in doc.items() if isinstance(v, list)}
        toks = {t["mint"]: t for t in tb.get("tokens") or []}
        for m, t in toks.items():
            if t.get("chain"):
                chain_any.setdefault(m, t["chain"])
        for th in tb.get("theses") or []:
            key = (th["mint"], repr(float(th["created_at"])))
            row = {k: v for k, v in th.items() if k != "id"}
            content[key].add(h(row))
            present[key].append(i)
            if key not in first:
                tk = toks.get(th["mint"])
                if tk is None:
                    no_token_row_first += 1
                s = json.loads(th.get("snapshot_json") or "{}")
                first[key] = {"mint": th["mint"], "created_at": float(th["created_at"]), "sha": sha, "ct": ct,
                              "chain_first": (tk or {}).get("chain"), "price": s.get("price"), "snap_h": h(s),
                              "status": th.get("status")}
    data_end = revs[-1][1]
    res["theses"] = len(first)
    res["mints"] = len({r["mint"] for r in first.values()})
    for r in first.values():
        r["chain"] = r["chain_first"] or chain_any.get(r["mint"]) or "UNKNOWN"
    res["D_theses_without_token_row_in_first_export"] = no_token_row_first
    res["D_chain_disagreement_default_vs_any"] = sum(1 for r in first.values() if (r["chain_first"] or "solana") != r["chain"])
    mint_chain = {}
    for r in first.values():
        mint_chain[r["mint"]] = r["chain"]
    res["mints_by_chain"] = dict(collections.Counter(mint_chain.values()))
    # B: content changes
    changed = [k for k, v in content.items() if len(v) > 1]
    res["B_keys_with_changed_content_across_exports"] = len(changed)
    # C: duplicates by (mint, snapshot hash)
    by_snap = collections.defaultdict(list)
    for k, r in first.items():
        by_snap[(r["mint"], r["snap_h"])].append(r)
    dups = [v for v in by_snap.values() if len(v) > 1]
    res["C_same_mint_same_snapshot_multiple_created_at"] = {"groups": len(dups), "extra_rows": sum(len(v) - 1 for v in dups),
                                                            "examples": [[(x["created_at"], x["sha"][:8]) for x in v][:3] for v in dups[:3]]}
    # E: vanish and reappear
    gaps = 0
    for k, idx in present.items():
        if idx and (idx[-1] - idx[0] + 1) != len(idx):
            gaps += 1
    res["E_keys_that_vanish_and_reappear"] = gaps
    unc = collections.Counter(r["sha"][:8] for r in first.values() if r["sha"][:8] in UNCONFIRMED)
    res["E_theses_first_exported_in_unconfirmed_commits"] = dict(unc)
    # A: thinned and matured counts, Solana, priced
    sol = collections.defaultdict(list)
    for r in first.values():
        if r["chain"] == "solana" and r["price"]:
            sol[r["mint"]].append(r["ct"])
    h0, h1 = ts(HOLD[0]), ts(HOLD[1])
    res["solana_priced_mints"] = len(sol)
    split = {}
    for name, hz in H.items():
        kept = []
        for m, lst in sol.items():
            last = None
            for t in sorted(set(lst)):
                if last is None or t >= last + hz:
                    kept.append((m, t))
                    last = t
        conf = 86400 if name == "T2" else 0
        mat = [(m, t) for m, t in kept if t + LAG + hz <= data_end]
        c = collections.Counter()
        for m, t in kept:
            mt = t + LAG + hz + MARGIN
            if mt > data_end:
                c["not_matured"] += 1
            elif t >= h0:
                c["holdout"] += 1
            elif mt > h0:
                c["purged"] += 1
            else:
                c["development"] += 1
        # holdout decisions whose decision time rests on an unconfirmed commit
        unc_hold = sum(1 for m, t in kept if t >= h0 and t + LAG + hz + MARGIN <= data_end and any(
            r["ct"] == t and r["sha"][:8] in UNCONFIRMED for r in first.values() if r["mint"] == m))
        split[name] = {"thinned": len(kept), "matured_by_data_end_no_margin": len(mat), **c, "holdout_on_unconfirmed_commit": unc_hold}
    # T2: 24 h + 24 h confirmation
    kept = []
    for m, lst in sol.items():
        last = None
        for t in sorted(set(lst)):
            if last is None or t >= last + 86400:
                kept.append((m, t))
                last = t
    c = collections.Counter()
    for m, t in kept:
        mt = t + LAG + 86400 + 86400 + MARGIN
        c["not_matured" if mt > data_end else "holdout" if t >= h0 else "purged" if mt > h0 else "development"] += 1
    split["T2"] = dict(c)
    res["splits"] = split
    res["data_end"] = dt.datetime.fromtimestamp(data_end, dt.UTC).isoformat()
    json.dump(res, open(out, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
