"""Phase 13 runner: the calibration, uncertainty and abstention layer of PI-D-067 on the real data, in one deterministic pass.

    python -B run_calibration.py OUTDIR [--dev-store PATH] [--feature-store PATH]

Development part (real data, no holdout): the champion B2's walk-forward out-of-sample rows re-derived from the Phase 07 fold
cards through the training gate; the calibration card per target at the holdout start H (and at every fold cutoff); the
reliability of the raw out-of-sample numbers with counts, base rates and Wilson bands; the score report; descriptive
below-gate Venn-Abers and Platt fits (never publishable); event-rate uncertainty; exchangeability across days and routes; the
drift stream; the abstention layer replayed on every out-of-sample row; the answer for the newest prospective decisions as of
2026-10-26T20:00:00Z (no label of them is read).

Retrospective holdout part (POST_OPENING, PI-D-066): computed only from committed Phase 12 files (HOLDOUT_SCORED.csv,
HOLDOUT_DECISIONS.csv, CALIBRATION_BINS.csv) plus the decisions' stored features, never the sealed folder; logged; combined with
`evaluation.conservative_status`, so it can only make a statement more conservative. It never fits, selects or promotes.

Reads only, read-only: the Phase 06 development store (decisions; labels through `labels.training_labels`), the Phase 05 store
(stored feature snapshots through `features.training_view`), the committed Phase 07 cards and Phase 12 files. No network: an
audit hook refuses any socket call. Two runs give identical files except `evidence/run_log.json`.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import resource
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from memelab.predictive import abstention as AB  # noqa: E402
from memelab.predictive import baselines as B  # noqa: E402
from memelab.predictive import calibration as CAL  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import evaluation as E  # noqa: E402
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import runtime as R  # noqa: E402

SOCKET_EVENTS: list[str] = []


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKET_EVENTS.append(event)
        raise RuntimeError(f"Phase 13 runner makes no network call ({event})")


sys.addaudithook(_hook)


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P7 = _load("p07_run_baselines", "audits/predictive-intelligence/phase_07/probes/run_baselines.py")
AUD = REPO / "audits/predictive-intelligence"
P12V = AUD / "phase_12/validation"
SHORT = P7.SHORT
LONG = {v: k for k, v in SHORT.items()}
TARGETS = (L.T1, L.T1B, L.T2)
H, END = L.holdout_start(), L.prospective_start()
AS_OF_TODAY = "2026-10-26T20:00:00Z"
REGISTRY = AUD / "phase_13/experiments/EXPERIMENT_REGISTRY.csv"
REGISTRY_SHA = "d73e19cff2b91eb293b3f4c86b1752b4f805d162e97e27d279b72e8c210146fb"
PRIOR_LEDGER = P12V / "FULL_EXPERIMENT_LEDGER_CORRECTED.csv"
CODE = ["memelab/predictive/calibration.py", "memelab/predictive/abstention.py", "memelab/predictive/baselines.py",
        "memelab/predictive/stats.py", "memelab/predictive/labels.py", "memelab/predictive/features.py",
        "memelab/predictive/contract.py", "memelab/predictive/evaluation.py",
        "audits/predictive-intelligence/phase_07/probes/run_baselines.py",
        "audits/predictive-intelligence/phase_13/probes/run_calibration.py"]
POST_OPENING_INPUTS = ["HOLDOUT_SCORED.csv", "HOLDOUT_DECISIONS.csv", "CALIBRATION_BINS.csv", "OPENING_LOG.json"]
# runs on real data before the recorded run (P22); appended before the recorded run, never removed
DEBUG_RUNS: list[str] = [
    "run 2026-10-26T20:37:42Z to 20:37:52Z at uncommitted code into the session scratchpad (dbg1): every output computed; the "
    "holdout reliability comparison reported a false difference because Phase 12's CALIBRATION_BINS.csv lists the B2 rows once "
    "per comparison; the comparison was fixed; no rule, threshold or output definition changed",
    "run 20:38:30Z to 20:38:40Z (dbg2): 0 failures, same numbers",
    "run 20:39:50Z to 20:40:00Z (dbg3): adds the fold B0 column to CALIBRATION_SETS.csv for the oracle; 0 failures, same numbers; "
    "the oracle probe was written on these outputs: scikit-learn _sigmoid_calibration differs from the numpy Platt by up to 9.4e-6 "
    "on the T2 descriptive set (G7 as registered fails there), so the PI-D-053 newton-cholesky reference was added beside it "
    "after seeing that result",
]


# ---------------------------------------------------------------- io
def fsha(p) -> str:
    return P7.fsha(p)


def iso(t) -> str:
    return datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def r12(x):
    if x is None:
        return ""
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, float):
        return "" if not math.isfinite(x) else repr(round(x, 12))
    return x


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r12(r.get(k)) for k in cols})


def _default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    raise TypeError(type(o))


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, sort_keys=True, indent=1, default=_default, allow_nan=False) + "\n")


def jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n" for r in rows))


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def read_csv(p: Path) -> list[dict]:
    with open(p) as f:
        return list(csv.DictReader(f))


def fnum(s) -> float:
    try:
        v = float(s)
    except (TypeError, ValueError):
        return float("nan")
    return v


# ---------------------------------------------------------------- development: the walk-forward re-derived
def load_card(rel: str) -> dict:
    return B.loads((REPO / rel).read_text())


def dev_walk(dev, target, frows, snaps, info):
    """Phase 07's frozen walk-forward recomputed through the training gate (no NC1 seeds); fold cards must equal the committed
    fold artifacts byte for byte in model_sha, and the B2 and B0 numbers the committed OOS file within its 6 decimals."""
    s = SHORT[target]
    dev_ex, _ = P7.examples_at(dev, target, H, frows, snaps, info)
    res = B.walk_forward(target, dev_ex, lambda c: P7.examples_at(dev, target, c, frows, snaps, info)[0], nc1_seeds=())
    art = json.loads((AUD / f"phase_07/artifacts/folds/{s}.json").read_text())
    checks = {"folds": len(res["folds"]), "fold_card_sha_equal": True, "fold_cutoffs_equal": True}
    for f, a in zip(res["folds"], art["folds"]):
        if f["cutoff_utc"] != a["cutoff_utc"]:
            checks["fold_cutoffs_equal"] = False
        for b in ("B0", "B2"):
            B.verify_card(a["cards"][b])
            if f["cards"][b]["model_sha"] != a["cards"][b]["model_sha"]:
                checks["fold_card_sha_equal"] = False
    if len(art["folds"]) != len(res["folds"]):
        checks["fold_card_sha_equal"] = False
    committed = {r["decision_key"]: r for r in read_csv(AUD / "phase_07/experiments/OOS_PREDICTIONS.csv") if r["target_short"] == s}
    diff = 0.0
    for r in res["oos"]:
        c = committed.get(r["example"].decision_key)
        if c is None:
            checks.setdefault("missing_in_committed", 0)
            checks["missing_in_committed"] += 1
            continue
        for b in ("B0", "B2"):
            a, bb = r[b], fnum(c[b])
            if math.isfinite(a) != math.isfinite(bb):
                diff = math.inf
            elif math.isfinite(a):
                diff = max(diff, abs(a - bb))
    checks["oos_rows"] = len(res["oos"])
    checks["committed_rows"] = len(committed)
    checks["max_abs_diff_vs_committed_6_decimals"] = diff
    checks["equal_within_rounding"] = diff <= 5e-7 and len(committed) == len(res["oos"])
    return dev_ex, res, checks


def cal_rows_of(res) -> list[dict]:
    out = []
    for r in res["oos"]:
        e = r["example"]
        if not math.isfinite(r["B2"]):
            continue
        out.append({"decision_key": e.decision_key, "mint": e.mint, "decision_time": e.decision_time,
                    "label_matures_at": e.label_matures_at, "y": int(e.y), "score": float(r["B2"]),
                    "scored_by_cutoff": float(r["cutoff"]), "split": "DEVELOPMENT"})
    return out


def request_of(target: str, e: B.Example, info: dict, *, flag_on: bool, eligibility: str | None, new_mint: bool) -> dict:
    return {"chain": e.chain, "mint": e.mint, "target": target, "decision_time": e.decision_time, "decision_time_basis": "EXPORT_COMMIT",
            "snapshot_hash": info["row_sha256"], "flag_on": flag_on, "pool_point_in_time": e.route == "PIT_RECORDED",
            "route": e.route, "eligibility": eligibility, "position_usd": None, "backtest_required": False,
            "x": dict(e.x), "avail": dict(e.avail), "feature_set_sha": F.feature_set_sha(), "new_mint": bool(new_mint),
            "token_history_rows": 0}


def matrix_counts(records: list[dict]) -> Counter:
    c = Counter()
    for r in records:
        for cd in {x["code"] for x in r["conditions"]}:
            c[cd] += 1
    return c


# ---------------------------------------------------------------- the run
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--dev-store", default=P7.DEV_STORE)
    ap.add_argument("--feature-store", default=P7.FEATURE_STORE)
    a = ap.parse_args()
    out = Path(a.out)
    t0, c0 = time.time(), time.process_time()
    start_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
    if fsha(REGISTRY) != REGISTRY_SHA:
        raise SystemExit("the experiment registry differs from its pre-registered sha256")
    for p in (a.dev_store, a.feature_store):
        L.refuse_sealed(p)
        R.refuse_bakeoff_labels(path=p)
    stores_before = {p: fsha(p) for p in (a.dev_store, a.feature_store)}
    dev, fs = P7.ro(a.dev_store), P7.ro(a.feature_store)
    frows, snaps, info = P7.load_inputs(dev, fs)
    flag_on = C.enabled()
    bt = C.backtest_status()
    failures: list[str] = []

    cal_dir, art_dir = out / "calibration", out / "artifacts"
    rel_rows, base_rows, ledger13, cs_rows = [], [], [], []
    replay = {"flag_on": flag_on, "backtest_status": bt, "targets": {}}
    score_rep, below, exch, drift_out, fold_cards_out, cards_h = {}, {}, {}, {}, {}, {}
    dev_pairs, dev_records = [], []
    dev_counts: dict[str, Counter] = {}
    dev_cov: dict[str, dict] = {}
    for t in TARGETS:
        s = SHORT[t]
        dev_ex, res, checks = dev_walk(dev, t, frows, snaps, info)
        if not (checks["fold_card_sha_equal"] and checks["fold_cutoffs_equal"] and checks["equal_within_rounding"]):
            failures.append(f"{s}: walk-forward re-derivation differs from Phase 07 ({checks})")
        rows = cal_rows_of(res)
        champion = load_card(f"audits/predictive-intelligence/phase_07/artifacts/{s}/B2.json")
        # calibration card at H (evidence: the prospective holdout, not matured)
        card_h = CAL.build_card(t, champion, rows, H, level="ABSTAIN",
                                evidence={"status": "NOT_YET_MATURED", "source": "PROSPECTIVE_HOLDOUT"})
        cards_h[s] = card_h
        (art_dir / s).mkdir(parents=True, exist_ok=True)
        (art_dir / s / "CALIBRATION_CARD.json").write_text(CAL.dumps(card_h))
        cn = card_h["calibration_set"]
        b0_of = {rr["example"].decision_key: rr["B0"] for rr in res["oos"]}
        for r in CAL.rows_at(rows, H):
            cs_rows.append({"target_short": s, "decision_key": r["decision_key"], "mint": r["mint"],
                            "decision_time_utc": iso(r["decision_time"]), "label_matures_at_utc": iso(r["label_matures_at"]),
                            "scored_by_cutoff_utc": iso(r["scored_by_cutoff"]), "y": r["y"], "raw_b2": r["score"],
                            "b0_fold": b0_of[r["decision_key"]], "split": r["split"]})
        # fold-time calibration cards (what the layer knew at each fold cutoff)
        fold_cards = {}
        for f in res["folds"]:
            fold_cards[f["fold"]] = CAL.build_card(t, f["cards"]["B2"], rows, float(f["cutoff"]), level="ABSTAIN",
                                                   evidence={"status": "NOT_YET_MATURED", "source": "PROSPECTIVE_HOLDOUT"})
        fold_cards_out[s] = {str(k): {"cutoff_utc": v["cutoff_utc"], "calibration_set": v["calibration_set"], "status": v["status"],
                                      "details": v["details"], "card_sha": v["card_sha"]} for k, v in fold_cards.items()}
        # reliability of the raw out-of-sample numbers, base rates, Wilson bands
        y = np.array([r["y"] for r in rows], float)
        p = np.array([r["score"] for r in rows], float)
        b0 = np.array([rr["B0"] for rr in res["oos"] if math.isfinite(rr["B2"])], float)
        rel = CAL.reliability(y, p)
        rel_rows.append({"target_short": s, "view": "DEV_OOS_RAW_B2", "part": "IN_THE_LARGE", "n": rel["n"], "positives": int(y.sum()),
                         "mean_pred": rel["mean_pred"], "observed": rel["observed"], "wilson_lo": rel["wilson"][0],
                         "wilson_hi": rel["wilson"][1], "ok": rel["in_the_large_ok"], "base_rate_mean_fold_b0": float(b0.mean()),
                         "base_rate_at_H": float(champion["k_train"]) / float(champion["n_train"]),
                         "days": cn["days"], "note": rel.get("note", ""), "claim": "DESCRIPTIVE_UNCALIBRATED"})
        for i, bn in enumerate(rel["bins"]):
            rel_rows.append({"target_short": s, "view": "DEV_OOS_RAW_B2", "part": f"BIN_{i}", "n": bn["n"], "positives": bn["positives"],
                             "mean_pred": bn["mean_pred"], "observed": bn["observed"], "wilson_lo": bn["wilson"][0],
                             "wilson_hi": bn["wilson"][1], "ok": bn["ok"], "p_min": bn["p_min"], "p_max": bn["p_max"],
                             "claim": "DESCRIPTIVE_UNCALIBRATED"})
        for f in res["folds"]:
            fr = [rr for rr in res["oos"] if rr["fold"] == f["fold"] and math.isfinite(rr["B2"])]
            if not fr:
                continue
            fy = np.array([rr["y"] for rr in fr], float)
            lo, hi = CAL.K.wilson(int(fy.sum()), len(fy))
            rel_rows.append({"target_short": s, "view": "DEV_OOS_RAW_B2", "part": f"FOLD_{f['fold']}_{f['test_day']}", "n": len(fr),
                             "positives": int(fy.sum()), "mean_pred": float(np.mean([rr["B2"] for rr in fr])), "observed": float(fy.mean()),
                             "wilson_lo": lo, "wilson_hi": hi, "ok": lo <= float(np.mean([rr["B2"] for rr in fr])) <= hi,
                             "base_rate_mean_fold_b0": float(fr[0]["B0"]), "note": "fold of one decision day; n below 20 gives no rate claim" if len(fr) < 20 else "",
                             "claim": "DESCRIPTIVE_UNCALIBRATED"})
        # score report against the fold training prevalence
        sr = CAL.score_report(y, p, b0, days=[iso(r["decision_time"])[:10] for r in rows], mints=[r["mint"] for r in rows])
        score_rep[s] = sr
        # descriptive below-gate fits (never publishable)
        bel = {"publishable": False, "claim": "DESCRIPTIVE_BELOW_GATE_NOT_A_CALIBRATION", "n": int(y.size), "positives": int(y.sum())}
        if 0 < y.sum() < y.size:
            va = CAL.fit_calibrator(p, y, "VENN_ABERS")
            pl = CAL.fit_calibrator(p, y, "PLATT")
            grid = np.quantile(p, [0.1, 0.25, 0.5, 0.75, 0.9])
            gp, g0, g1 = CAL.apply_calibrator(va, grid)
            pp, _, _ = CAL.apply_calibrator(pl, grid)
            bins = CAL.support_bins(p, y)
            gridrows = []
            for i, sc in enumerate(grid):
                sup = CAL.support_of(bins, float(sc))
                iv = CAL.interval(float(g0[i]), float(g1[i]), sup["n"], sup["k"]) if sup else None
                gridrows.append({"raw_b2": float(sc), "va_p0": float(g0[i]), "va_p1": float(g1[i]), "va_merged": float(gp[i]),
                                 "va_width": float(g1[i] - g0[i]), "platt": float(pp[i]), "support_n": sup["n"] if sup else None,
                                 "support_k": sup["k"] if sup else None, "hull_interval": iv,
                                 "hull_width": (iv[1] - iv[0]) if iv else None})
            bel.update({"platt_params": pl["params"], "venn_abers_grid": gridrows, "support_bins": bins})
        else:
            bel["note"] = "one class in the out-of-sample rows: no descriptive fit"
        fwd = []
        for f in res["folds"]:
            fit = CAL.rows_at(rows, float(f["cutoff"]))
            test = [r for r in rows if r["scored_by_cutoff"] == float(f["cutoff"])]
            fy = [r["y"] for r in fit]
            row = {"fold": f["fold"], "cutoff_utc": f["cutoff_utc"], "fit_n": len(fit), "fit_positives": int(sum(fy)), "scored_n": len(test)}
            if fit and 0 < sum(fy) < len(fy) and test:
                va = CAL.fit_calibrator([r["score"] for r in fit], fy, "VENN_ABERS")
                tp, t0_, t1_ = CAL.apply_calibrator(va, [r["score"] for r in test])
                ty = np.array([r["y"] for r in test], float)
                lo, hi = CAL.K.wilson(int(ty.sum()), len(ty))
                m0, m1 = float(np.mean(t0_)), float(np.mean(t1_))
                row.update({"mean_p0": m0, "mean_p1": m1, "mean_merged": float(np.mean(tp)), "mean_width": float(np.mean(t1_ - t0_)),
                            "observed": float(ty.mean()), "wilson_lo": lo, "wilson_hi": hi, "observed_inside_mean_p0_p1": m0 <= float(ty.mean()) <= m1,
                            "wilson_overlaps_mean_p0_p1": not (hi < m0 or lo > m1)})
            else:
                row["note"] = "no fit: empty or one-class rows matured by the fold cutoff"
            fwd.append(row)
            rel_rows.append({"target_short": s, "view": "DEV_FORWARD_VA_BELOW_GATE", "part": f"FOLD_{f['fold']}",
                             "n": row["scored_n"], "positives": int(sum(r["y"] for r in test)), "mean_pred": row.get("mean_merged"),
                             "observed": row.get("observed"), "wilson_lo": row.get("wilson_lo"), "wilson_hi": row.get("wilson_hi"),
                             "va_mean_p0": row.get("mean_p0"), "va_mean_p1": row.get("mean_p1"),
                             "covered": row.get("observed_inside_mean_p0_p1"), "fit_n": row["fit_n"], "note": row.get("note", ""),
                             "claim": "DESCRIPTIVE_BELOW_GATE_NOT_A_CALIBRATION"})
        bel["forward_folds"] = fwd
        below[s] = bel
        # event-rate uncertainty and exchangeability on every development label at H
        yd = np.array([e.y for e in dev_ex], float)
        days = [e.day for e in dev_ex]
        mints = [e.mint for e in dev_ex]
        bru = CAL.base_rate_uncertainty(yd, days=days, mints=mints)
        base_rows.append({"target_short": s, "rows": "ALL_DEVELOPMENT_LABELS_AT_H", **{k: v for k, v in bru.items() if not isinstance(v, list)},
                          "wilson_lo": bru["wilson"][0], "wilson_hi": bru["wilson"][1], "day_block_lo": bru["day_block"][0],
                          "day_block_hi": bru["day_block"][1], "mint_block_lo": bru["mint_block"][0], "mint_block_hi": bru["mint_block"][1]})
        exch[s] = {"days": CAL.heterogeneity(days, yd), "route": CAL.heterogeneity([e.route or "UNKNOWN" for e in dev_ex], yd),
                   "rows": "ALL_DEVELOPMENT_LABELS_AT_H",
                   "regime": "one out-of-sample regime label in development (Phase 11): regime exchangeability cannot be tested",
                   "day_rates": {d: {"n": int(sum(1 for x in days if x == d)), "positives": int(sum(yd[i] for i, x in enumerate(days) if x == d))}
                                 for d in sorted(set(days))}}
        # repair pass 2 (PI-D-070, skeptic m2): route rates and the day test without the earliest decision day
        routes = [e.route or "UNKNOWN" for e in dev_ex]
        exch[s]["route_rates"] = {r_: {"n": int(sum(1 for x in routes if x == r_)), "positives": int(sum(yd[i] for i, x in enumerate(routes) if x == r_))}
                                  for r_ in sorted(set(routes))}
        first_day = min(days)
        keep = [i for i, d in enumerate(days) if d != first_day]
        exch[s]["days_without_first_day"] = {"dropped_day": first_day,
                                             **CAL.heterogeneity([days[i] for i in keep], yd[keep])}
        # drift stream: champion loss minus B0 loss at each label's maturity (out-of-sample rows only)
        stream = [(rr["example"].label_matures_at, (rr["B2"] - rr["y"]) ** 2 - (rr["B0"] - rr["y"]) ** 2) for rr in res["oos"]
                  if math.isfinite(rr["B2"])]
        alarms = CAL.drift_alarm_times(stream)
        drift_out[s] = {"observations": len(stream), "alarm_times_utc": [iso(x) for x in alarms], "settings": CAL.DRIFT,
                        "note": "fewer observations than min_obs cannot alarm" if len(stream) < CAL.DRIFT["min_obs"] else ""}
        # the abstention layer on every out-of-sample row
        recs, ck = [], {"card_time_cross_check_equal": True}
        for rr in res["oos"]:
            e = rr["example"]
            fold_card = res["folds"][rr["fold"]]["cards"]["B2"]
            try:
                st = E.check_card_time(fold_card, [e.decision_time])[0]
            except E.RetrospectiveModelNotAvailable:
                st = "AFTER"
            req = request_of(t, e, info[e.decision_key], flag_on=flag_on, eligibility="ELIGIBLE", new_mint=rr["new_mint"])
            doc, rec = AB.forecast_result(req, card=fold_card, level="ABSTAIN", cal_card=fold_cards[rr["fold"]],
                                          raw=rr["B2"] if math.isfinite(rr["B2"]) else None, raw_why=rr["B2_why"],
                                          drift_alarms=alarms, generated_at_utc=iso(e.decision_time), backtest_status=bt)
            codes = {c["code"] for c in rec["conditions"]}
            if ("MODEL_TOO_OLD" in codes) != (st == E.STALE) or ("MODEL_TRAINED_AFTER_DECISION" in codes) != (st == "AFTER"):
                ck["card_time_cross_check_equal"] = False
            errs = AB.validate_publication(doc, model_card=fold_card, calibration_card=fold_cards[rr["fold"]], record=rec, backtest=bt)
            if errs or doc["prediction_status"] != "ABSTAIN":
                failures.append(f"{s} {e.decision_key[:12]}: {doc['prediction_status']} {errs}")
            dev_pairs.append({"document": doc, "record": rec})
            recs.append(rec)
        dev_records += recs
        dev_counts[s] = matrix_counts(recs)
        dev_cov[s] = {"requests": len(recs), "forecast": sum(1 for r in recs if r["prediction_status"] == "FORECAST"),
                      "raw_number": sum(1 for rr in res["oos"] if math.isfinite(rr["B2"])), "calibrated_number": 0}
        replay["targets"][s] = {**checks, **ck, "calibration_rows": len(rows), "card_at_H": card_h["card_sha"]}
        # ledger rows (phase 13)
        sf = {"T1_24h": "0ab64525e04b8664a1cab51c9e24f5fa4f750681d32a5d97bfc520710e3845a4",
              "T1b_6h": "aa16e7adeae7d5bc8567de9ab85ed1f28843afe51bc0de9b52e24d587beb8a31",
              "T2_24h": "82a1c33b12cef45995eb15edd07b8e27ddcd76eafbdb8c503f5feb9501be86cd"}[s]
        for eid, cand, kind, n_rows, n_num, verdict in [
            ("CAL_GATE_B2", "P07_B2", "DESCRIPTION_ONLY", cn["n"], 0, card_h["status"]),
            ("VA_BELOW_GATE_DESCRIPTIVE", "venn_abers(P07_B2 OOS)", "DESCRIPTION_ONLY", int(y.size), int(y.size) if "venn_abers_grid" in bel else 0, "DESCRIPTIVE_BELOW_GATE"),
            ("PLATT_BELOW_GATE_DESCRIPTIVE", "platt(P07_B2 OOS)", "DESCRIPTION_ONLY", int(y.size), int(y.size) if "platt_params" in bel else 0, "DESCRIPTIVE_BELOW_GATE"),
            ("VA_FORWARD_FOLDS_DESCRIPTIVE", "venn_abers expanding over folds", "DESCRIPTION_ONLY", int(y.size), sum(r["scored_n"] for r in fwd if "mean_p0" in r), "DESCRIPTIVE_BELOW_GATE"),
            ("RAW_B2_RELIABILITY_DEV", "P07_B2", "DESCRIPTION_ONLY", int(y.size), int(y.size), "CALIBRATION_OK_IN_THE_LARGE" if rel["in_the_large_ok"] else "CALIBRATION_FAILS_IN_THE_LARGE"),
            ("SCORE_REPORT_DEV", "P07_B2", "DESCRIPTION_ONLY", int(y.size), int(y.size), sr["conflict"] or "NO_CONFLICT"),
            ("BASE_RATE_UNCERTAINTY", "B0", "DESCRIPTION_ONLY", int(yd.size), int(yd.size), "DESCRIPTIVE"),
            ("EXCHANGEABILITY_DAYS", "labels", "DESCRIPTION_ONLY", int(yd.size), int(yd.size), exch[s]["days"]["status"]),
            ("EXCHANGEABILITY_ROUTE", "labels", "DESCRIPTION_ONLY", int(yd.size), int(yd.size), exch[s]["route"]["status"]),
            ("ABSTENTION_REPLAY_DEV", "abstention-1 on P07_B2 fold cards", "DESCRIPTION_ONLY", len(recs), 0, "ABSTAIN_ALL" if all(r["prediction_status"] == "ABSTAIN" for r in recs) else "SOME_FORECAST"),
        ]:
            ledger13.append({"phase": "13", "experiment_id": f"P13:{t}:{eid}", "target": t, "candidate": cand, "kind": kind,
                             "view": "DEVELOPMENT", "seed": CAL.SEED, "folds": len(res["folds"]), "n_rows": n_rows,
                             "n_with_number": n_num, "verdict": verdict, "split_fingerprint": sf, "selection_status": "",
                             "claim": "NOT_A_CLAIM_DESCRIPTIVE"})

    # Holm over the six exchangeability tests (repair pass 2, PI-D-070, skeptic m2)
    fam = [(s_, kind) for s_ in (SHORT[t] for t in TARGETS) for kind in ("days", "route")]
    ph = CAL.K.holm([exch[s_][kind]["p"] if exch[s_][kind]["p"] is not None else 1.0 for s_, kind in fam])
    for (s_, kind), q in zip(fam, ph):
        exch[s_][kind]["p_holm_six_tests"] = q
        exch[s_][kind]["status_after_holm"] = "EXCHANGEABILITY_REJECTED" if q < 0.05 else "NOT_REJECTED_AFTER_HOLM"
    for s_ in (SHORT[t] for t in TARGETS):
        ledger13.append({"phase": "13", "experiment_id": f"P13:{LONG[s_]}:EXCHANGEABILITY_HOLM_AND_FIRST_DAY_DROP", "target": LONG[s_],
                         "candidate": "labels", "kind": "DESCRIPTION_ONLY", "view": "DEVELOPMENT", "seed": CAL.SEED, "folds": "",
                         "n_rows": exch[s_]["days"]["n"], "n_with_number": exch[s_]["days"]["n"],
                         "verdict": f"holm days {exch[s_]['days']['p_holm_six_tests']:.3f} route {exch[s_]['route']['p_holm_six_tests']:.3f}",
                         "split_fingerprint": "", "selection_status": "", "claim": "NOT_A_CLAIM_DESCRIPTIVE_ADDED_IN_REPAIR_PASS_2"})

    # ---------------------------------------------------------------- today: the newest prospective decisions (no label read)
    today = C.parse_utc(AS_OF_TODAY)
    pro = [dict(r) for r in dev.execute("SELECT * FROM predictive_decisions WHERE chain='solana' AND decision_key IS NOT NULL "
                                        "AND decision_time >= ? AND decision_time <= ? ORDER BY decision_time, decision_key", (END, today))]
    today_pairs, today_out = [], {"as_of_utc": AS_OF_TODAY, "decisions": len(pro), "targets": {},
                                  "note": "prospective decisions of the development store; their features are not in the Phase 05 store "
                                          "(sealed by design) and no price was read, so inputs are missing and eligibility is unknown; "
                                          "no label of them is read"}
    for t in TARGETS:
        s = SHORT[t]
        champion = load_card(f"audits/predictive-intelligence/phase_07/artifacts/{s}/B2.json")
        recs = []
        for d in pro:
            dd = L.decision_from_row(d)
            req = {"chain": dd["chain"], "mint": dd["mint"], "target": t, "decision_time": float(dd["decision_time"]),
                   "decision_time_basis": "EXPORT_COMMIT", "snapshot_hash": d["row_sha256"], "flag_on": flag_on,
                   "pool_point_in_time": dd.get("route") == "PIT_RECORDED", "route": dd.get("route"), "eligibility": None,
                   "position_usd": None, "backtest_required": False, "x": {}, "avail": {}, "feature_set_sha": F.feature_set_sha(),
                   "new_mint": None, "token_history_rows": 0}
            doc, rec = AB.forecast_result(req, card=champion, level="ABSTAIN", cal_card=cards_h[s], raw=None, raw_why="OOD",
                                          drift_alarms=[], generated_at_utc=AS_OF_TODAY, backtest_status=bt)
            errs = AB.validate_publication(doc, model_card=champion, calibration_card=cards_h[s], record=rec, backtest=bt)
            if errs or doc["prediction_status"] != "ABSTAIN":
                failures.append(f"today {s}: {errs}")
            today_pairs.append({"document": doc, "record": rec})
            recs.append(rec)
        standing = AB.evaluate({"chain": "solana", "mint": pro[-1]["mint"] if pro else "", "target": t, "decision_time": today,
                                "decision_time_basis": "CAPTURE_TIME", "snapshot_hash": "0" * 64, "flag_on": flag_on,
                                "pool_point_in_time": True, "eligibility": "ELIGIBLE", "x": {}, "avail": {},
                                "feature_set_sha": F.feature_set_sha()},
                               card=champion, level="ABSTAIN", cal_card=cards_h[s], raw=None, backtest_status=bt)
        st_codes = [c for c in standing["conditions"] if c["code"] in ("FLAG_OFF", "MODEL_NOT_PROMOTED", "NO_CALIBRATOR",
                                                                         "CALIBRATION_SET_TOO_SMALL", "CALIBRATION_EVIDENCE_TOO_SMALL",
                                                                         "CALIBRATION_EVIDENCE_PENDING", "MODEL_TOO_OLD", "NO_CHAMPION",
                                                                         "DEGENERATE_FLAT_PREDICTIONS", "DRIFT")]
        today_out["targets"][s] = {"prediction_status": "ABSTAIN" if all(r["prediction_status"] == "ABSTAIN" for r in recs) else "MIXED",
                                   "standing_conditions": [{k: c[k] for k in ("code", "reason", "detail")} for c in st_codes],
                                   "standing_reasons": AB.reasons_of(st_codes),
                                   "champion": champion["model_id"], "champion_model_sha": champion["model_sha"],
                                   "champion_stale_after_utc": iso(float(champion["training_cutoff"]) + C.ACCEPTANCE["max_model_age_s"]),
                                   "calibration_card_sha": cards_h[s]["card_sha"], "calibration_status": cards_h[s]["status"],
                                   "decision_requests": len(recs), "reason_counts": dict(sorted(Counter(x for r in recs for x in r["reasons"]).items()))}
        ledger13.append({"phase": "13", "experiment_id": f"P13:{t}:TODAY_STATUS", "target": t, "candidate": "abstention-1",
                         "kind": "DESCRIPTION_ONLY", "view": "PROSPECTIVE_DECISIONS_NO_LABEL", "seed": "", "folds": "", "n_rows": len(recs),
                         "n_with_number": 0, "verdict": today_out["targets"][s]["prediction_status"], "split_fingerprint": "",
                         "selection_status": "", "claim": "NOT_A_CLAIM_DESCRIPTIVE"})

    # ---------------------------------------------------------------- retrospective holdout: POST_OPENING description only
    po_inputs = {f: fsha(P12V / f) for f in POST_OPENING_INPUTS}
    scored = read_csv(P12V / "HOLDOUT_SCORED.csv")
    hdec = {r["decision_key"]: r for r in read_csv(P12V / "HOLDOUT_DECISIONS.csv")}
    p12bins = read_csv(P12V / "CALIBRATION_BINS.csv")
    frows_end = {r["decision_key"]: r for r in F.training_view(fs, as_of=END, feature_version=F.FEATURE_VERSION, mode="provider")}
    hold_pairs, hold_records, hold_out = [], [], {}
    hold_counts: dict[str, Counter] = {}
    hold_cov: dict[str, dict] = {}
    for t in TARGETS:
        s = SHORT[t]
        champion = load_card(f"audits/predictive-intelligence/phase_07/artifacts/{s}/B2.json")
        sr_rows = [r for r in scored if r["target_short"] == s]
        exs = []
        for r in sr_rows:
            fr = frows_end[r["decision_key"]]
            x, av = B.model_inputs(fr)
            exs.append(B.Example(decision_key=r["decision_key"], chain=fr["chain"], mint=fr["mint"], decision_time=float(fr["decision_time"]),
                                 label_matures_at=C.label_matures_at(t, float(fr["decision_time"])), y=int(r["y"]), x=x, avail=av,
                                 route=hdec[r["decision_key"]]["route"], snapshot_sha256=None))
            if fr["mint"] != r["mint"]:
                failures.append(f"holdout identity {r['decision_key'][:12]}")
        p, why = B.predict(champion, exs)
        committed = np.array([fnum(r["P07_B2"]) for r in sr_rows])
        diff = float(np.nanmax(np.abs(p - committed))) if len(p) else 0.0
        if not (np.array_equal(np.isfinite(p), np.isfinite(committed)) and diff <= 1e-12):
            failures.append(f"holdout {s}: B2 recomputed differs from HOLDOUT_SCORED ({diff})")
        y = np.array([e.y for e in exs], float)
        ok = np.isfinite(p)
        recs = []
        for i, e in enumerate(exs):
            d = hdec[e.decision_key]
            req = request_of(t, e, {"row_sha256": info[e.decision_key]["row_sha256"]} if e.decision_key in info else {"row_sha256": "0" * 64},
                             flag_on=flag_on, eligibility="ELIGIBLE", new_mint=d.get(f"new_mint_{s}") in ("1", "True", "true"))
            doc, rec = AB.forecast_result(req, card=champion, level="ABSTAIN", cal_card=cards_h[s], raw=float(p[i]) if ok[i] else None,
                                          raw_why=why[i], drift_alarms=[], generated_at_utc=iso(e.decision_time), backtest_status=bt)
            if AB.validate_publication(doc, model_card=champion, calibration_card=cards_h[s], record=rec, backtest=bt) or doc["prediction_status"] != "ABSTAIN":
                failures.append(f"holdout {s} {e.decision_key[:12]}: not a valid ABSTAIN")
            hold_pairs.append({"document": doc, "record": rec})
            recs.append(rec)
        hold_records += recs
        hold_counts[s] = matrix_counts(recs)
        hold_cov[s] = {"requests": len(recs), "forecast": sum(1 for r in recs if r["prediction_status"] == "FORECAST"),
                       "raw_number": int(ok.sum()), "calibrated_number": 0}
        # raw B2 reliability on the holdout, recomputed and compared with Phase 12's file
        relh = CAL.reliability(y[ok], p[ok])
        p12, seen_bins = [], set()
        for r in p12bins:                      # the file lists the B2 rows once per comparison; the first block is the one
            if r["target_short"] == s and r["view"] == "PRIMARY" and r["model"] == "P07_B2" and r["bin"] not in seen_bins:
                seen_bins.add(r["bin"])
                p12.append(r)
        same = len(p12) == 1 + len(relh["bins"]) and abs(fnum(p12[0]["mean_pred"]) - relh["mean_pred"]) < 1e-12 and \
            all(int(p12[i + 1]["n"]) == b["n"] and int(p12[i + 1]["positives"]) == b["positives"] for i, b in enumerate(relh["bins"]))
        if not same:
            failures.append(f"holdout {s}: reliability differs from Phase 12's CALIBRATION_BINS.csv")
        rel_rows.append({"target_short": s, "view": "HOLDOUT_RAW_B2_POST_OPENING", "part": "IN_THE_LARGE", "n": relh["n"],
                         "positives": int(y[ok].sum()), "mean_pred": relh["mean_pred"], "observed": relh["observed"],
                         "wilson_lo": relh["wilson"][0], "wilson_hi": relh["wilson"][1], "ok": relh["in_the_large_ok"],
                         "base_rate_at_H": float(champion["k_train"]) / float(champion["n_train"]),
                         "note": "equal to phase_12 CALIBRATION_BINS.csv" if same else "DIFFERS", "claim": "POST_OPENING_DESCRIPTION"})
        for i, bn in enumerate(relh["bins"]):
            rel_rows.append({"target_short": s, "view": "HOLDOUT_RAW_B2_POST_OPENING", "part": f"BIN_{i}", "n": bn["n"],
                             "positives": bn["positives"], "mean_pred": bn["mean_pred"], "observed": bn["observed"],
                             "wilson_lo": bn["wilson"][0], "wilson_hi": bn["wilson"][1], "ok": bn["ok"], "p_min": bn["p_min"],
                             "p_max": bn["p_max"], "claim": "POST_OPENING_DESCRIPTION"})
        # the development below-gate Venn-Abers on the holdout scores: does its interval cover the observed rate?
        rows_dev = [r for r in cs_rows if r["target_short"] == s]
        dy = [int(r["y"]) for r in rows_dev]
        va_h = {"claim": "POST_OPENING_DESCRIPTION_NOT_A_CALIBRATION", "fit": "development out-of-sample rows only"}
        post_state = E.NO_UNCORRECTED_SKILL
        if rows_dev and 0 < sum(dy) < len(dy) and ok.any():
            va = CAL.fit_calibrator([float(r["raw_b2"]) for r in rows_dev], dy, "VENN_ABERS")
            hp, h0, h1 = CAL.apply_calibrator(va, p[ok])
            yo = y[ok]
            lo, hi = CAL.K.wilson(int(yo.sum()), len(yo))
            m0, m1 = float(np.mean(h0)), float(np.mean(h1))
            relv = CAL.reliability(yo, hp)
            va_h.update({"n": int(len(yo)), "positives": int(yo.sum()), "observed": float(yo.mean()), "wilson": [lo, hi],
                         "mean_p0": m0, "mean_p1": m1, "mean_merged": float(np.mean(hp)), "mean_width": float(np.mean(h1 - h0)),
                         "observed_inside_mean_p0_p1": m0 <= float(yo.mean()) <= m1,
                         "merged_check_in_the_large_ok": relv["in_the_large_ok"], "merged_check_every_bin_ok": relv["every_bin_ok"]})
            post_state = E.SURVIVES if CAL.check_passed(relv) else E.FAILS
            rel_rows.append({"target_short": s, "view": "HOLDOUT_DEV_VA_BELOW_GATE_POST_OPENING", "part": "IN_THE_LARGE", "n": int(len(yo)),
                             "positives": int(yo.sum()), "mean_pred": float(np.mean(hp)), "observed": float(yo.mean()), "wilson_lo": lo,
                             "wilson_hi": hi, "ok": relv["in_the_large_ok"], "va_mean_p0": m0, "va_mean_p1": m1,
                             "covered": m0 <= float(yo.mean()) <= m1, "fit_n": len(rows_dev),
                             "claim": "POST_OPENING_DESCRIPTION_NOT_A_CALIBRATION"})
        else:
            va_h["note"] = "no development fit (one class) or no holdout number"
        recorded = E.NO_UNCORRECTED_SKILL          # Phase 12's primary row: NOT_DISTINGUISHABLE or INSUFFICIENT_EVENTS, no skill claim
        combined = E.conservative_status(recorded, post_state)
        shift = CAL.prevalence_shift([e.y for e in P7.examples_at(dev, t, H, frows, snaps, info)[0]], y[ok])
        hold_out[s] = {"scored_rows": len(exs), "with_raw_number": int(ok.sum()), "venn_abers_dev_fit_on_holdout": va_h,
                       "post_opening_state": post_state, "recorded_state": recorded, "combined_state": combined,
                       "combined_is_a_claim": combined == E.SURVIVES, "publication": "ABSTAIN (unchanged by any post-opening result)",
                       "prevalence_shift_dev_vs_holdout": shift, "max_abs_b2_diff_vs_holdout_scored": diff}
        if combined == E.SURVIVES:
            failures.append(f"holdout {s}: a post-opening computation produced a claim")
        for eid, cand, n_rows, n_num, verdict in [
            ("ABSTENTION_REPLAY_HOLDOUT", "abstention-1 on the frozen P07_B2 card at H", len(recs), 0,
             "ABSTAIN_ALL" if all(r["prediction_status"] == "ABSTAIN" for r in recs) else "SOME_FORECAST"),
            ("VA_BELOW_GATE_ON_HOLDOUT", "venn_abers(P07_B2 OOS) applied to holdout", int(ok.sum()), int(ok.sum()), combined),
            ("SHIFT_DEV_VS_HOLDOUT", "labels", int(ok.sum()), int(ok.sum()), f"p={shift['p']:.4f}"),
        ]:
            ledger13.append({"phase": "13", "experiment_id": f"P13:{t}:{eid}", "target": t, "candidate": cand, "kind": "POST_OPENING_CHECK",
                             "view": "RETROSPECTIVE_HOLDOUT_POST_OPENING", "seed": CAL.SEED, "folds": "", "n_rows": n_rows,
                             "n_with_number": n_num, "verdict": verdict, "split_fingerprint": "", "selection_status": combined if eid.startswith("VA") else "",
                             "claim": "NOT_A_CLAIM_POST_OPENING"})
    po_log = {"label": "POST_OPENING", "decision": "PI-D-066 item 2, PI-D-067", "head_code": git("rev-parse", "HEAD"),
              "inputs_sha256": po_inputs, "sealed_folder_read": False,
              "computations": ["abstention-1 replay on the scored holdout rows", "raw B2 reliability (equal to Phase 12)",
                               "development below-gate Venn-Abers applied to holdout scores", "prevalence shift development vs holdout"],
              "rule": "may only make a statement more conservative (evaluation.conservative_status); never fits, selects or promotes",
              "time": "see evidence/run_log.json (kept out of this file so two runs are byte-equal)"}

    # ---------------------------------------------------------------- traps on real rows (CX-13 on the real holdout rows)
    traps = {}
    for t in TARGETS:
        s = SHORT[t]
        hrows = [{"decision_key": r["decision_key"], "mint": r["mint"], "decision_time": C.parse_utc(r["decision_time_utc"]),
                  "label_matures_at": C.label_matures_at(t, C.parse_utc(r["decision_time_utc"])), "y": int(r["y"]),
                  "score": fnum(r["P07_B2"]), "scored_by_cutoff": H, "split": "RETROSPECTIVE_HOLDOUT"}
                 for r in scored if r["target_short"] == s and math.isfinite(fnum(r["P07_B2"]))]
        res_t = {}
        for name, rows_, cut in (("holdout_rows_as_fit_set", hrows, C.parse_utc("2026-10-26T18:00:00Z")),
                                 ("holdout_rows_relabelled_development", [dict(r, split="DEVELOPMENT") for r in hrows], C.parse_utc("2026-10-26T18:00:00Z"))):
            try:
                CAL.build_card(t, load_card(f"audits/predictive-intelligence/phase_07/artifacts/{s}/B2.json"), rows_, cut, level="SHADOW")
                res_t[name] = "ACCEPTED"
                failures.append(f"trap {s} {name} accepted")
            except CAL.CalibrationError as ex:
                res_t[name] = f"REFUSED: {str(ex)[:120]}"
        traps[s] = res_t

    # ---------------------------------------------------------------- abstention matrix, records, ledger
    mrows = []
    for code, (reason, text) in AB.CONDITIONS.items():
        row = {"condition": code, "contract_reason": reason, "explanation": text}
        for s in (SHORT[t] for t in TARGETS):
            row[f"dev_{s}"] = dev_counts[s].get(code, 0)
        for s in (SHORT[t] for t in TARGETS):
            row[f"holdout_post_opening_{s}"] = hold_counts[s].get(code, 0)
        mrows.append(row)
    for label, cov in (("dev", dev_cov), ("holdout_post_opening", hold_cov)):
        for key in ("requests", "forecast", "raw_number", "calibrated_number"):
            row = {"condition": f"COVERAGE_{key.upper()}", "contract_reason": "", "explanation": f"{label}: {key}"}
            for s in (SHORT[t] for t in TARGETS):
                row[f"{label}_{s}"] = cov[s][key]
            mrows.append(row)
    write_csv(cal_dir / "ABSTENTION_MATRIX.csv", mrows)
    for name, pairs in (("FORECAST_RESULTS_DEV.jsonl", dev_pairs), ("FORECAST_RESULTS_TODAY.jsonl", today_pairs),
                        ("FORECAST_RESULTS_HOLDOUT_POST_OPENING.jsonl", hold_pairs)):
        jsonl(cal_dir / name, pairs)
    for name, recs in (("ABSTENTION_RECORDS_DEV.jsonl", dev_records), ("ABSTENTION_RECORDS_HOLDOUT_POST_OPENING.jsonl", hold_records)):
        p = cal_dir / name
        if p.exists():
            p.unlink()
        AB.append(p, recs, expect_sha=None)
    write_csv(cal_dir / "RELIABILITY_COVERAGE.csv", rel_rows)
    write_csv(cal_dir / "CALIBRATION_SETS.csv", cs_rows)
    write_csv(cal_dir / "BASE_RATE_UNCERTAINTY.csv", base_rows)
    write_json(cal_dir / "SCORE_REPORT_DEV.json", score_rep)
    write_json(cal_dir / "BELOW_GATE_DESCRIPTIVE.json", below)
    write_json(cal_dir / "EXCHANGEABILITY.json", exch)
    write_json(cal_dir / "DRIFT_DEV.json", drift_out)
    write_json(cal_dir / "FOLD_CALIBRATION_CARDS.json", fold_cards_out)
    write_json(cal_dir / "TODAY_STATUS.json", today_out)
    write_json(cal_dir / "HOLDOUT_POST_OPENING.json", hold_out)
    write_json(cal_dir / "POST_OPENING_LOG.json", po_log)
    write_json(cal_dir / "REPLAY_CHECKS.json", {**replay, "traps_cx13_on_real_holdout_rows": traps})
    prior = read_csv(PRIOR_LEDGER)
    debug = [{"phase": "13", "experiment_id": f"P13:DEBUG:{i}", "target": "", "candidate": "", "kind": "DEBUG_RUN_REAL_DATA",
              "view": "", "seed": "", "folds": "", "n_rows": "", "n_with_number": "", "verdict": d, "split_fingerprint": "",
              "selection_status": "", "claim": ""} for i, d in enumerate(DEBUG_RUNS)]
    fixtures = [{"phase": "13", "experiment_id": r["experiment_id"], "target": "", "candidate": "fixture", "kind": "TRAP_OR_CHECK",
                 "view": "FIXTURE", "seed": "", "folds": "", "n_rows": "", "n_with_number": "", "verdict": "TESTED_IN_SUITE",
                 "split_fingerprint": "", "selection_status": "", "claim": "NOT_A_CLAIM_FIXTURE"}
                for r in read_csv(REGISTRY) if r["kind"] == "TRAP_OR_CHECK"]
    ledger = prior + ledger13 + fixtures + debug
    write_csv(out / "experiments/SEARCH_LEDGER.csv", ledger)
    tot_before, tot_after = E.ledger_totals(prior), E.ledger_totals(ledger)
    if tot_after["candidate_configurations"] != tot_before["candidate_configurations"] or tot_after["n_search"] != tot_before["n_search"]:
        failures.append("Phase 13 changed the candidate count or N_search")
    write_json(out / "experiments/LEDGER_TOTALS.json", {"before_phase_13": tot_before, "after_phase_13": tot_after,
                                                         "rule_configurations_after": E.rule_configurations(ledger)})

    stores_after = {p: fsha(p) for p in (a.dev_store, a.feature_store)}
    if stores_after != stores_before:
        failures.append("a store changed")
    outputs = sorted(p for p in out.rglob("*") if p.is_file() and p.parent.name != "evidence" and "probes" not in p.parts
                     and p.suffix in (".csv", ".json", ".jsonl") and ("calibration" in p.parts or "artifacts" in p.parts or "experiments" in p.parts))
    log = {"start_utc": start_utc, "end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "head": git("rev-parse", "HEAD"),
           "dirty_code": git("status", "--porcelain", "--", *CODE), "code_sha256": {c: fsha(REPO / c) for c in CODE},
           "registry_sha256": fsha(REGISTRY), "stores": {p: {"before": stores_before[p], "after": stores_after[p]} for p in stores_before},
           "outputs_sha256": {p.relative_to(out).as_posix(): fsha(p) for p in outputs if p.name != "EXPERIMENT_REGISTRY.csv"},
           "post_opening_logged_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "post_opening_inputs_sha256": po_inputs,
           "socket_events": SOCKET_EVENTS, "vendor_calls": 0, "firecrawl_credits": 0, "llm_calls": 0,
           "wall_s": round(time.time() - t0, 2), "cpu_s": round(time.process_time() - c0, 2),
           "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "failures": failures,
           "registry_fingerprint": C.registry_sha256(), "flag_on": flag_on, "backtest_status": bt}
    write_json(out / "evidence/run_log.json", log)
    print(json.dumps({"failures": failures, "status": {SHORT[t]: cards_h[SHORT[t]]["status"] for t in TARGETS},
                      "dev_requests": {k: v["requests"] for k, v in dev_cov.items()}, "dev_forecasts": sum(v["forecast"] for v in dev_cov.values()),
                      "holdout_requests": {k: v["requests"] for k, v in hold_cov.items()}, "today_decisions": len(pro),
                      "wall_s": log["wall_s"]}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
