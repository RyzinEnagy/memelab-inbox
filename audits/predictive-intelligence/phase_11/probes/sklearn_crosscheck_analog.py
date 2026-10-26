"""Phase 11 oracle cross-check (research venv only; the lab never imports scikit-learn, PI-D-031, PI-D-032).

For every real neighbour query `run_analog.py --npz` wrote (AC2 and AC3 at each out-of-sample decision with analogs), scikit-learn
`NearestNeighbors(algorithm="brute", metric="euclidean")` on [z-scores, one-hot categories / sqrt(2)] (a category mismatch then
adds exactly 1 to the squared distance) gives every reference row's distance to the target; one row per cluster (its nearest,
ties by decision key) and the 30 nearest clusters among the allowed rows must equal the module's analogs, with distances within
1e-9. The out-of-distribution threshold (95th percentile of each reference row's 30th nearest other-cluster distance) is
recomputed from `kneighbors` on the reference rows and compared within 1e-9. Seeded synthetic queries are added so the check
exists even if no real query had analogs.

    /home/claude/pi_research/venvs/p04_bundle/bin/python -B sklearn_crosscheck_analog.py ARRAYS.npz OUT.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
from sklearn.neighbors import NearestNeighbors

K, Q, TOL = 30, 0.95, 1e-9


def design(Xn, Xc, qn, qc):
    mu = Xn.mean(axis=0)
    sd = Xn.std(axis=0)
    sd = np.where(sd > 0, sd, 1.0)
    cats = [np.unique(np.r_[Xc[:, j], qc[j]]) for j in range(Xc.shape[1])]

    def enc(c):
        return np.concatenate([(c[..., j:j + 1] == cats[j]).astype(float) / np.sqrt(2.0) for j in range(len(cats))], axis=-1)
    return np.c_[(Xn - mu) / sd, enc(Xc)], np.r_[(qn - mu) / sd, enc(qc)]


def per_cluster(d, cid, keyrank, allowed):
    best = {}
    for i in np.argsort(d, kind="stable"):
        if not allowed[i]:
            continue
        c = int(cid[i])
        if c not in best or (d[i], keyrank[i]) < (d[best[c]], keyrank[best[c]]):
            best[c] = int(i)
    return sorted(best.values(), key=lambda i: (d[i], keyrank[i]))


def check(Xn, Xc, qn, qc, cid, keyrank, allowed, sel, seld, thr):
    Z, z = design(Xn, Xc, qn, qc)
    nn = NearestNeighbors(n_neighbors=len(Z), algorithm="brute", metric="euclidean").fit(Z)
    dist, idx = nn.kneighbors(z[None, :])
    d = np.empty(len(Z))
    d[idx[0]] = dist[0]
    mine = per_cluster(d, cid, keyrank, allowed)[:K]
    dd, ii = nn.kneighbors(Z)
    kth = []
    for r in range(len(Z)):
        cm = {}
        for dv, j in zip(dd[r], ii[r]):
            if cid[j] == cid[r]:
                continue
            cm.setdefault(int(cid[j]), dv)
        v = sorted(cm.values())
        kth.append(v[min(K, len(v)) - 1])
    t = float(np.quantile(np.array(kth), Q))
    return {"same_set": list(mine) == [int(x) for x in sel], "max_dist_diff": float(np.max(np.abs(d[mine] - seld))) if len(mine) == len(seld) else None,
            "thr_diff": abs(t - float(thr[0])), "n_ref": int(len(Z)), "k": len(mine)}


def main() -> int:
    arr = np.load(sys.argv[1])
    tags = sorted({k.rsplit("_", 1)[0] for k in arr.files if k.endswith("_Xn")})
    rows = []
    for t in tags:
        r = check(arr[t + "_Xn"], arr[t + "_Xc"], arr[t + "_qn"], arr[t + "_qc"], arr[t + "_cid"], arr[t + "_keyrank"],
                  arr[t + "_allowed"], arr[t + "_sel"], arr[t + "_seld"], arr[t + "_thr"])
        r["tag"] = t
        rows.append(r)
    # synthetic queries through the module itself
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[4]))
    from memelab.predictive import analog as A  # noqa: E402
    rng = np.random.default_rng(20261026)
    syn = []
    for s in range(5):
        n = 120
        Xn = rng.normal(size=(n, 4))
        Xc = np.c_[rng.integers(0, 3, n), rng.integers(0, 2, n)].astype(float)
        cid = rng.integers(0, 90, n)
        keys = [f"k{s}_{i:04d}" for i in range(n)]

        class E:
            pass
        rows_ = []
        for i in range(n):
            e = E()
            e.x = dict(zip(A.NUMERIC, Xn[i])) | dict(zip(A.CATEGORICAL, Xc[i]))
            e.cluster, e.decision_key = f"c{cid[i]}", keys[i]
            rows_.append(e)
        q = E()
        q.x = dict(zip(A.NUMERIC, rng.normal(size=4))) | dict(zip(A.CATEGORICAL, [1.0, 0.0]))
        idx = A.KnnIndex(rows_)
        d = idx.query(q)
        sel = idx.nearest_clusters(d)[:K]
        names = sorted({e.cluster for e in rows_})
        cc = np.array([names.index(e.cluster) for e in rows_])
        r = check(Xn, Xc, np.array([q.x[c] for c in A.NUMERIC]), np.array([q.x[c] for c in A.CATEGORICAL]), cc,
                  np.argsort(np.argsort(np.array(keys))), np.ones(n, bool), np.array(sel), d[sel], np.array([idx.threshold()]))
        r["tag"] = f"synthetic_{s}"
        syn.append(r)
    allr = rows + syn
    ok = all(r["same_set"] and r["max_dist_diff"] is not None and r["max_dist_diff"] <= TOL and r["thr_diff"] <= TOL for r in allr)
    res = {"real_queries": len(rows), "synthetic_queries": len(syn), "all_equal": ok,
           "max_dist_diff": max((r["max_dist_diff"] or 0.0) for r in allr), "max_thr_diff": max(r["thr_diff"] for r in allr),
           "tolerance": TOL, "oracle": "sklearn.neighbors.NearestNeighbors(algorithm='brute', metric='euclidean')", "rows": allr}
    import sklearn
    res["sklearn_version"] = sklearn.__version__
    open(sys.argv[2], "w").write(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
