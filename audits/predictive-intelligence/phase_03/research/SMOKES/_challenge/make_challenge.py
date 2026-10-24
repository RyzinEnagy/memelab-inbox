"""Shared synthetic challenge data for Phase 03/04 smoke tests (format and behaviour only, never evidence of memecoin edge).

Writes challenge.csv with seeded synthetic decision snapshots:
  decision_id, mint, symbol, decision_time (epoch s), split (train/val/holdout/embargo),
  liq_usd, vol_24h, age_h, score100, fatal_flag, ret_1h        -> legitimate as-of features (NaN allowed)
  leak_future_ret, leak_available_at                           -> TRAP: only available 6h AFTER decision_time; must be excluded
  label (0/1, NaN when censored), label_matures_at, censored   -> binary target, ~8% prevalence, 24h horizon
  time_to_event_h, event_observed                              -> survival framing of the same target (censor at 24h)
Holdout rows carry a covariate shift in liq_usd and ret_1h (for drift detectors).
Same symbol is reused by several mints (identity trap): never group by symbol.
Usage: python -I make_challenge.py OUT_DIR
"""
import csv, math, os, sys
import numpy as np

SEED = 20261024
N = 3000
N_MINTS = 300
T0 = 1790000000  # fixed epoch, no wall clock
DAYS = 30

def main(out_dir):
    rng = np.random.default_rng(SEED)
    os.makedirs(out_dir, exist_ok=True)
    mints = [f"MINT{idx:04d}" + "x" * 28 for idx in range(N_MINTS)]
    symbols = [f"SYM{idx % 120:03d}" for idx in range(N_MINTS)]  # 120 symbols over 300 mints
    t = np.sort(rng.uniform(0, DAYS * 86400, N)).astype(int) + T0
    m = rng.integers(0, N_MINTS, N)
    frac = (t - T0) / (DAYS * 86400)
    split = np.where(frac < 0.6, "train", np.where(frac < 0.78, "val", np.where(frac < 0.80, "embargo", "holdout")))
    shift = (split == "holdout").astype(float)
    liq = np.exp(rng.normal(10 + 0.8 * shift, 1.2, N))
    vol = np.exp(rng.normal(11, 1.5, N))
    age = rng.gamma(2.0, 30.0, N)
    score = np.clip(rng.normal(55, 15, N), 0, 100).round()
    fatal = rng.random(N) < 0.15
    ret1 = rng.normal(0.01 + 0.03 * shift, 0.08, N)
    z = -3.2 + 0.35 * (np.log(vol) - 11) - 0.25 * (np.log(liq) - 10) + 0.02 * (score - 55) + 4.0 * ret1 - 0.8 * fatal - 0.004 * age
    p = 1 / (1 + np.exp(-z))
    y = (rng.random(N) < p).astype(float)
    tte = np.where(y == 1, rng.uniform(0.2, 24, N), 24.0)
    leak = y * rng.normal(0.30, 0.05, N) + (1 - y) * rng.normal(-0.05, 0.10, N)
    matures = t + 86400
    cutoff = T0 + DAYS * 86400
    cens = matures > cutoff
    y_out = np.where(cens, np.nan, y)
    ev = np.where(cens, 0, y).astype(int)
    tte = np.where(cens, np.minimum(tte, (cutoff - t) / 3600.0), tte)
    liq[rng.random(N) < 0.05] = np.nan
    vol[rng.random(N) < 0.10] = np.nan
    path = os.path.join(out_dir, "challenge.csv")
    cols = ["decision_id", "mint", "symbol", "decision_time", "split", "liq_usd", "vol_24h", "age_h", "score100",
            "fatal_flag", "ret_1h", "leak_future_ret", "leak_available_at", "label", "label_matures_at", "censored",
            "time_to_event_h", "event_observed"]
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for i in range(N):
            mi = int(m[i])
            w.writerow([f"d{i:05d}", mints[mi], symbols[mi], int(t[i]), split[i],
                        "" if math.isnan(liq[i]) else round(float(liq[i]), 2),
                        "" if math.isnan(vol[i]) else round(float(vol[i]), 2),
                        round(float(age[i]), 3), int(score[i]), int(fatal[i]), round(float(ret1[i]), 5),
                        round(float(leak[i]), 5), int(t[i]) + 6 * 3600,
                        "" if math.isnan(y_out[i]) else int(y_out[i]), int(matures[i]), int(cens[i]),
                        round(float(tte[i]), 4), int(ev[i])])
    print(path, N, "rows; prevalence (uncensored)", round(float(np.nanmean(y_out)), 4), "censored", int(cens.sum()))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
