"""R3 shared helpers for Phase 03 smokes (synthetic challenge only; format and behaviour, never evidence of edge)."""
import csv, hashlib, math, os, sys, json, time, platform

CHALLENGE = "/home/claude/pi_research/challenge/challenge.csv"
CHALLENGE_SHA256 = "18fda40cc7a2a6f5aa607a32f1a096976317f901f5b75d1ae23b4bcaddd5f23d"
FEATURES = ["liq_usd", "vol_24h", "age_h", "score100", "fatal_flag", "ret_1h"]
TRAP = "leak_future_ret"


def load():
    import numpy as np
    raw = open(CHALLENGE, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    assert got == CHALLENGE_SHA256, ("challenge sha256 mismatch", got)
    rows = list(csv.DictReader(open(CHALLENGE)))
    out = {}
    for k in rows[0].keys():
        vals = [r[k] for r in rows]
        if k in ("decision_id", "mint", "symbol", "split"):
            out[k] = np.array(vals, dtype=object)
        else:
            out[k] = np.array([float(v) if v != "" else float("nan") for v in vals], dtype=float)
    return out


def design(d, idx, with_trap=False, log_money=True):
    """Feature matrix with NaN kept. liq and vol logged (NaN stays NaN)."""
    import numpy as np
    cols = list(FEATURES) + ([TRAP] if with_trap else [])
    X = []
    for c in cols:
        v = d[c][idx].astype(float)
        if log_money and c in ("liq_usd", "vol_24h"):
            v = np.log(v)
        X.append(v)
    return np.column_stack(X), cols


def masks(d):
    import numpy as np
    s = d["split"]
    lab = ~np.isnan(d["label"])
    return {
        "train": (s == "train") & lab,
        "val": (s == "val") & lab,
        "holdout": (s == "holdout") & lab,
        "holdout_all": (s == "holdout"),
        "embargo": (s == "embargo"),
        "censored": d["censored"] == 1,
    }


def brier(y, p):
    import numpy as np
    return float(np.mean((p - y) ** 2))


def logloss(y, p, clip=1e-6):
    import numpy as np
    q = np.clip(p, clip, 1 - clip)
    return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))


def prob_report(y, p, base_rate):
    """Shape and proper scores vs train-prevalence baseline. y must exclude censored rows."""
    import numpy as np
    p = np.asarray(p, dtype=float)
    rep = {
        "n": int(len(y)), "positives": int(np.sum(y)),
        "shape": list(p.shape), "finite": bool(np.all(np.isfinite(p))),
        "in_0_1": bool(np.all((p >= 0) & (p <= 1))) if np.all(np.isfinite(p)) else False,
        "min": float(np.nanmin(p)), "max": float(np.nanmax(p)), "mean": float(np.nanmean(p)),
        "brier": brier(y, p), "logloss": logloss(y, p),
        "base_rate_train": float(base_rate),
        "brier_base": brier(y, np.full(len(y), base_rate)),
        "logloss_base": logloss(y, np.full(len(y), base_rate)),
    }
    rep["bss_vs_base"] = 1 - rep["brier"] / rep["brier_base"]
    try:
        from sklearn.metrics import roc_auc_score
        rep["auc"] = float(roc_auc_score(y, p))
    except Exception as e:  # sklearn may be absent in a venv
        rep["auc"] = None
    return rep


def ipcw_brier_at(t, time_obs, event, surv_prob_at_t, train_time, train_event):
    """Graf et al. IPCW Brier at time t for survival probability S(t|x). Censoring KM fitted on training only.
    Written by R3 (numpy), not taken from any reviewed library."""
    import numpy as np
    G = km_censoring(train_time, train_event)
    def Gf(s):
        idx = np.searchsorted(G[0], s, side="right") - 1
        return np.where(idx >= 0, G[1][np.clip(idx, 0, None)], 1.0)
    time_obs = np.asarray(time_obs, float); event = np.asarray(event, int)
    S = np.asarray(surv_prob_at_t, float)
    died = (time_obs <= t) & (event == 1)
    alive = time_obs > t
    w_d = np.where(died, 1.0 / np.maximum(Gf(time_obs - 1e-9), 1e-12), 0.0)
    w_a = np.where(alive, 1.0 / max(float(Gf(np.array([t]))[0]), 1e-12), 0.0)
    return float(np.mean(w_d * (0 - S) ** 2 + w_a * (1 - S) ** 2))


def km_censoring(time_obs, event):
    """Kaplan-Meier of the censoring distribution (censoring = event 0). Returns (times, G(t))."""
    import numpy as np
    t = np.asarray(time_obs, float); c = (np.asarray(event, int) == 0).astype(int)
    order = np.argsort(t); t = t[order]; c = c[order]
    uniq = np.unique(t)
    n_at_risk = len(t); surv = 1.0; ts, gs = [], []
    for u in uniq:
        at = t == u
        d = int(c[at].sum())
        if n_at_risk > 0:
            surv *= 1 - d / n_at_risk
        ts.append(u); gs.append(surv)
        n_at_risk -= int(at.sum())
    return np.array(ts), np.array(gs)


def env_info():
    return {"python": sys.version.split()[0], "platform": platform.platform(), "executable": sys.executable}


def dump(obj, path=None):
    s = json.dumps(obj, indent=1, default=lambda o: float(o) if hasattr(o, "__float__") else str(o))
    print(s)
    if path:
        open(path, "w").write(s)


class Timer:
    def __init__(self): self.t = {}
    def __call__(self, name):
        tm = self
        class _C:
            def __enter__(s): s.t0 = time.perf_counter(); return s
            def __exit__(s, *a): tm.t[name] = round(time.perf_counter() - s.t0, 4)
        return _C()


def seeded_paths(n_paths=300, seed=20261026, min_len=24, max_len=288, gap_prob=0.15):
    """Synthetic OHLCV-like 5-minute paths, one per mint, short and irregular (omitted intervals = no trade).
    Each path gets 0..2 planted regime changes in drift/volatility. Returns list of dicts with
    t (epoch s, irregular), close, high, low, volume, cps (true change indices in the kept-candle index).
    Written by R3; synthetic, format and behaviour only."""
    import numpy as np
    rng = np.random.default_rng(seed)
    out = []
    T0 = 1790000000
    for i in range(n_paths):
        L = int(rng.integers(min_len, max_len + 1))
        k = int(rng.integers(0, 3))
        cps = sorted(rng.choice(np.arange(8, L - 8), size=k, replace=False).tolist()) if L > 20 and k else []
        bounds = [0] + cps + [L]
        r = np.empty(L)
        for a, b in zip(bounds[:-1], bounds[1:]):
            mu = rng.normal(0, 0.01); sd = rng.choice([0.005, 0.02, 0.05])
            r[a:b] = rng.normal(mu, sd, b - a)
        close = 1e-4 * np.exp(np.cumsum(r))
        high = close * np.exp(np.abs(rng.normal(0, 0.01, L)))
        low = close * np.exp(-np.abs(rng.normal(0, 0.01, L)))
        vol = np.exp(rng.normal(7, 1.5, L))
        start = T0 + int(rng.integers(0, 30 * 86400)) // 300 * 300
        t = start + 300 * np.arange(L)
        keep = rng.random(L) > gap_prob
        keep[0] = True
        # map true change indices into kept index space
        kept_idx = np.cumsum(keep) - 1
        cps_kept = sorted(set(int(kept_idx[c]) for c in cps))
        out.append({"mint": f"PMINT{i:04d}", "t": t[keep], "close": close[keep], "high": high[keep],
                    "low": low[keep], "volume": vol[keep], "cps": cps_kept, "n_dense": L})
    return out
