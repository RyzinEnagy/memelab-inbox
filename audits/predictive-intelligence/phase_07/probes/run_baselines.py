"""Phase 07 baseline runner: the frozen walk-forward of B0 to B4 with negative controls on the development labels, the
train-only artifacts at the holdout start, the traps, the serialization smoke and every table of the phase.

Reads only: the Phase 06 development store (labels through `labels.training_labels`, decision rows) and the Phase 05 store
(stored provider-mode feature snapshots through `features.training_view`), both opened read-only. Never opens the sealed
holdout folder. No network: an audit hook refuses any socket connect. Deterministic: two runs into two folders give identical
files except `evidence/run_log.json` (times).

    python -B run_baselines.py OUTDIR [--reps 2000] [--dev-store PATH] [--feature-store PATH] [--npz PATH]

PROVISIONAL (PI-D-046): until Phase 06's 48 h revision re-read is folded in. If it changes a development label, rerun this
script at the Phase 07 commit; the new outputs supersede these.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import resource
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from memelab.predictive import baselines as B  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import runtime as R  # noqa: E402
from memelab.predictive import stats as K  # noqa: E402

SOCKET_EVENTS: list[str] = []


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKET_EVENTS.append(event)
        raise RuntimeError(f"Phase 07 runner makes no network call ({event})")


sys.addaudithook(_hook)

SHORT = {L.T1: "T1_24h", L.T1B: "T1b_6h", L.T2: "T2_24h"}
H = L.holdout_start()
DEV_STORE = "/home/claude/pi_research/p06/dev_store.sqlite"
FEATURE_STORE = "/home/claude/pi_research/p05/predictive_store.sqlite"
CODE = ["memelab/predictive/stats.py", "memelab/predictive/baselines.py", "memelab/predictive/labels.py",
        "memelab/predictive/features.py", "memelab/predictive/contract.py",
        "audits/predictive-intelligence/phase_07/probes/run_baselines.py"]
VIEWS = ("ALL", "NEW_MINTS", "NEW_CREATORS", "NEW_NARRATIVES", "PIT_ONLY", "NO_KEY_CONFLICT")


def fsha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ro(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def r6(x):
    if x is None:
        return ""
    if isinstance(x, float):
        return "" if not math.isfinite(x) else f"{x:.6f}"
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
            w.writerow({k: r6(r.get(k)) for k in cols})


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, sort_keys=True, indent=1, default=_default) + "\n")


def _default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, B.Example):
        return o.decision_key
    raise TypeError(type(o))


# ---------------------------------------------------------------- loading
def load_inputs(dev: sqlite3.Connection, fs: sqlite3.Connection):
    frows = {r["decision_key"]: r for r in F.training_view(fs, as_of=H, feature_version=F.FEATURE_VERSION, mode="provider")}
    snaps = {r["decision_key"]: r["snapshot_sha256"] for r in
             fs.execute("SELECT decision_key, snapshot_sha256 FROM predictive_snapshots WHERE availability_mode='provider' AND decision_key IS NOT NULL")}
    info = {}
    for r in dev.execute("SELECT decision_key, status, token_json, row_sha256, mint, chain, decision_time FROM predictive_decisions"):
        tok = json.loads(r["token_json"]) if r["token_json"] else {}
        nar = tok.get("narrative_id")
        info[r["decision_key"]] = {"status": r["status"], "narrative": str(nar) if nar not in (None, "") else None,
                                   "symbol": tok.get("symbol"), "row_sha256": r["row_sha256"], "mint": r["mint"],
                                   "chain": r["chain"], "decision_time": r["decision_time"]}
    return frows, snaps, info


def examples_at(dev, target, as_of, frows, snaps, info, *, include_kc=True):
    rows = L.training_labels(dev, as_of, target, mode="provider", include_key_conflict=include_kc)
    return B.join(rows, frows, decision_info=info, snapshots=snaps), rows


# ---------------------------------------------------------------- views and metrics
def view_rows(oos, view):
    if view in ("ALL", "NO_KEY_CONFLICT"):
        return list(oos)
    if view == "NEW_MINTS":
        return [r for r in oos if r["new_mint"]]
    if view == "NEW_CREATORS":
        return [r for r in oos if r["new_creator"] is not False]
    if view == "NEW_NARRATIVES":
        return [r for r in oos if r["new_narrative"] is not False]
    if view == "PIT_ONLY":
        return [r for r in oos if r["example"].route == "PIT_RECORDED"]
    raise ValueError(view)


def nc1_summary(rows, seeds, reps):
    out = []
    for s in seeds:
        key = f"NC1_{s}"
        if not rows or not any(math.isfinite(r[key]) for r in rows):
            out.append({"seed": s, "n": 0})
            continue
        ev = B.evaluate(rows, key, reps=reps, seed=20261025 + s, boot=False)
        out.append({"seed": s, "n": ev["n_with_number"], "brier": ev.get("brier"), "brier_ref": ev.get("brier_ref"),
                    "bss": ev.get("bss"), "log_loss": ev.get("log_loss")})
    return out


def metric_row(target, view, ev, *, kind, extra):
    iv = ev.get("intervals") or {}
    cal = ev.get("calibration") or {}
    return {"target": target, "target_short": SHORT[target], "view": view, "baseline": ev["baseline"], "kind": kind,
            "n_oos_rows": ev["n_rows"], "n_with_number": ev["n_with_number"], "coverage": ev.get("coverage"),
            "abstain_reasons": ";".join(f"{k}={v}" for k, v in sorted(ev.get("abstain_reasons", {}).items())),
            "positives": ev.get("positives"), "prevalence": ev.get("prevalence"), "decision_days": ev.get("days"),
            "mints": ev.get("mints"), "folds": ev.get("folds"), "brier": ev.get("brier"), "brier_b0": ev.get("brier_ref"),
            "bss_vs_b0": ev.get("bss"), "log_loss": ev.get("log_loss"), "log_loss_b0": ev.get("log_loss_ref"),
            "roc_auc": ev.get("auc"), "average_precision": ev.get("average_precision"),
            "bss_ci_day_lo": (iv.get("day", {}).get("ci") or [None, None])[0], "bss_ci_day_hi": (iv.get("day", {}).get("ci") or [None, None])[1],
            "bss_ci_mint_lo": (iv.get("mint", {}).get("ci") or [None, None])[0], "bss_ci_mint_hi": (iv.get("mint", {}).get("ci") or [None, None])[1],
            "governing": ev.get("governing") or ("UNDEFINED" if ev.get("n_with_number") else ""),
            "p_one_sided": ev.get("p_one_sided"), "p_holm": extra.get("p_holm"),
            "ess_day": ev.get("ess_day"), "ess_mint": ev.get("ess_mint"),
            "cal_mean_pred": cal.get("mean_pred"), "cal_observed": cal.get("observed"),
            "cal_wilson_lo": (cal.get("wilson") or [None, None])[0], "cal_wilson_hi": (cal.get("wilson") or [None, None])[1],
            "cal_in_the_large_ok": cal.get("in_the_large_ok"), "cal_bins": len(cal.get("bins") or []),
            "cal_every_bin_ok": cal.get("every_bin_ok"), "ece": cal.get("ece"),
            "verdict": ev.get("verdict"), "status": B.PROVISIONAL, "revision_check_claimed": False,
            **{k: v for k, v in extra.items() if k != "p_holm"}}


# ---------------------------------------------------------------- traps
def traps(dev, frows, info):
    out = {}
    # NC2: the label itself as a feature, declared with its true availability (the label's maturity), and the first-touch
    # candle after t_entry: refused by the allowlist and by validate_rows on every row.
    rows = L.training_labels(dev, H, L.T1, mode="provider")
    ex = B.join(rows, frows, decision_info=info)
    refused_allow = refused_asof = accepted = 0
    for e, r in zip(ex, rows):
        avail = float(r["first_touch_start"]) + 600 if r["first_touch_start"] is not None else float(r["label_matures_at"])
        e2 = B.Example(**{**e.__dict__, "x": {**e.x, "trap_future_label": float(r["label"])},
                          "avail": {**e.avail, "trap_future_label": avail}})
        try:
            B.check_asof([e2], ["trap_future_label"], as_of=None, with_labels=False)
            accepted += 1
        except F.AsOfError:
            refused_allow += 1
        row = {"decision_time": e.decision_time, "trap": float(r["label"]), "trap__available_at": avail}
        try:
            F.validate_rows([row], columns=list(row), availability=["trap__available_at"])
            accepted += 1
        except F.AsOfError:
            refused_asof += 1
    out["NC2"] = {"rows": len(ex), "refused_by_allowlist": refused_allow, "refused_by_validate_rows": refused_asof,
                  "accepted": accepted, "min_trap_delay_s": min((float(r["first_touch_start"]) + 600 - float(r["decision_time"])
                                                                if r["first_touch_start"] is not None else
                                                                float(r["label_matures_at"]) - float(r["decision_time"])) for r in rows),
                  "pass": accepted == 0 and refused_allow == refused_asof == len(ex)}
    # NC3: real same-symbol mint pairs among labelled development decisions, joined by symbol
    by_sym: dict[str, dict[str, dict]] = {}
    for t in L.TARGETS:
        for r in L.training_labels(dev, H, t, mode="provider"):
            sym = info[r["decision_key"]]["symbol"]
            if isinstance(sym, str) and sym:
                by_sym.setdefault(sym.upper(), {}).setdefault(r["mint"], r)
    pairs = refused = accepted3 = 0
    detail = []
    for sym, per_mint in sorted(by_sym.items()):
        if len(per_mint) < 2:
            continue
        mints = sorted(per_mint)
        for a in mints:
            for b in mints:
                if a == b:
                    continue
                pairs += 1
                lab = per_mint[a]
                fb = frows[per_mint[b]["decision_key"]]
                try:
                    B.join_by_symbol(lab, {sym: fb}, sym)
                    accepted3 += 1
                except B.IdentityJoinError:
                    refused += 1
        detail.append({"symbol_sha256": hashlib.sha256(sym.encode()).hexdigest()[:16], "mints": mints})
    out["NC3"] = {"symbol_groups": len(detail), "ordered_pairs": pairs, "refused": refused, "accepted": accepted3,
                  "groups": detail, "pass": pairs > 0 and accepted3 == 0}
    # CX-07: join by mint taking the mint's latest stored snapshot instead of the decision's own
    latest: dict[str, dict] = {}
    for k, f in frows.items():
        if f["mint"] not in latest or f["decision_time"] > latest[f["mint"]]["decision_time"]:
            latest[f["mint"]] = f
    n = later = refused7 = 0
    for t in L.TARGETS:
        for r in L.training_labels(dev, H, t, mode="provider"):
            n += 1
            f = latest[r["mint"]]
            if f["decision_time"] != r["decision_time"]:
                later += 1
                try:
                    B.check_identity(r, f)
                except B.IdentityJoinError:
                    refused7 += 1
    out["CX07"] = {"label_rows": n, "rows_whose_mint_has_a_later_snapshot": later, "refused": refused7,
                   "pass": refused7 == later}
    return out


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--reps", type=int, default=C.ACCEPTANCE["bootstrap"]["min_replicates"])
    ap.add_argument("--dev-store", default=DEV_STORE)
    ap.add_argument("--feature-store", default=FEATURE_STORE)
    ap.add_argument("--npz", default=None, help="write the B2 fold designs and OOS arrays for the scikit-learn cross-check")
    a = ap.parse_args()
    out = Path(a.out)
    t0, c0 = time.time(), time.process_time()
    start_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
    for p in (a.dev_store, a.feature_store):
        L.refuse_sealed(p)
        R.refuse_bakeoff_labels(path=p)
    store_sha_before = {p: fsha(p) for p in (a.dev_store, a.feature_store)}
    dev, fs = ro(a.dev_store), ro(a.feature_store)
    frows, snaps, info = load_inputs(dev, fs)

    metrics, calib, oos_out, cohorts, prev_rows, nc1_rows, ledger, folds_ev = [], [], [], [], [], [], [], {}
    holm_in: dict[tuple[str, str], dict[str, float]] = {}
    npz: dict[str, np.ndarray] = {}
    art_dir = out / "artifacts"
    card_files = []
    smoke = {}
    label_set = {}
    for target in L.TARGETS:
        s = SHORT[target]
        runs = {}
        for include_kc in (True, False):
            dev_ex, dev_rows = examples_at(dev, target, H, frows, snaps, info, include_kc=include_kc)
            res = B.walk_forward(target, dev_ex, lambda c: examples_at(dev, target, c, frows, snaps, info, include_kc=include_kc)[0])
            runs[include_kc] = (dev_ex, res)
            if include_kc:
                label_set[target] = {"n": len(dev_rows), "positives": int(sum(r["label"] for r in dev_rows)),
                                     "label_set_sha": B.sha(sorted([r["label_key"], r["label"]] for r in dev_rows))}
        dev_ex, res = runs[True]
        folds_ev[s] = {"status": res["status"], "split_fingerprint": res.get("split_fingerprint"), "audit": res["audit"],
                       "folds": [{k: v for k, v in f.items() if k != "cards"} for f in res["folds"]],
                       "no_key_conflict_folds": [{k: v for k, v in f.items() if k != "cards"} for f in runs[False][1]["folds"]],
                       "development_days": sorted({e.day for e in dev_ex}),
                       "development_n": len(dev_ex), "development_positives": int(sum(e.y for e in dev_ex))}
        write_json(art_dir / "folds" / f"{s}.json", {"target": target, "status": B.PROVISIONAL,
                                                     "folds": [{"fold": f["fold"], "cutoff_utc": f["cutoff_utc"], "cards": f["cards"]}
                                                               for f in res["folds"]]})
        # pooled out-of-sample evaluation, every view
        for view in VIEWS:
            rows = view_rows(runs[view != "NO_KEY_CONFLICT"][1]["oos"], view)
            for b in B.BASELINES + ("B4C",):
                ev = B.evaluate(rows, b, reps=a.reps)
                kind = "DESCRIPTION_ONLY" if b == "B4C" else "BASELINE"
                metrics.append((target, view, ev, kind))
                if view == "ALL" and b in B.GATED:
                    holm_in.setdefault((view, b), {})[target] = ev.get("p_one_sided")
                if view == "ALL" and b != "B4C" and ev.get("calibration"):
                    for i, bn in enumerate(ev["calibration"]["bins"] or [{"n": ev["calibration"]["n"], "positives": None,
                                                                          "mean_pred": ev["calibration"]["mean_pred"],
                                                                          "observed": ev["calibration"]["observed"],
                                                                          "wilson": ev["calibration"]["wilson"], "ok": ev["calibration"]["in_the_large_ok"],
                                                                          "p_min": None, "p_max": None}]):
                        calib.append({"target_short": s, "baseline": b, "bin": i if ev["calibration"]["bins"] else "in_the_large",
                                      "n": bn["n"], "positives": bn["positives"], "mean_pred": bn["mean_pred"], "observed": bn["observed"],
                                      "wilson_lo": bn["wilson"][0], "wilson_hi": bn["wilson"][1], "ok": bn["ok"],
                                      "p_min": bn["p_min"], "p_max": bn["p_max"], "status": B.PROVISIONAL})
                ledger.append({"phase": "07", "experiment_id": f"P07:{target}:{b}", "target": target, "candidate": b,
                               "kind": kind, "view": view, "seed": 20261025, "folds": len(res["folds"]),
                               "n_rows": ev["n_rows"], "n_with_number": ev["n_with_number"], "verdict": ev.get("verdict"),
                               "split_fingerprint": res.get("split_fingerprint") if view != "NO_KEY_CONFLICT" else runs[False][1].get("split_fingerprint")})
            for nc in nc1_summary(rows, res.get("nc1_seeds", []), a.reps):
                nc1_rows.append({"target_short": s, "view": view, **nc})
                ledger.append({"phase": "07", "experiment_id": f"P07:{target}:NC1_seed{nc['seed']:02d}", "target": target,
                               "candidate": "NC1", "kind": "NEGATIVE_CONTROL", "view": view, "seed": nc["seed"],
                               "folds": len(res["folds"]), "n_rows": len(rows), "n_with_number": nc["n"], "verdict": "",
                               "split_fingerprint": res.get("split_fingerprint")})
        # out-of-sample predictions and cohorts (ALL view)
        for r in res["oos"]:
            e = r["example"]
            oos_out.append({"target_short": s, "fold": r["fold"], "cutoff_utc": B._iso(r["cutoff"]), "decision_key": e.decision_key,
                            "mint": e.mint, "decision_time_utc": B._iso(e.decision_time), "day": e.day, "y": e.y,
                            "route": e.route, "status_group": B.status_group(e.status), "fatal": e.x.get(B.FATAL),
                            "new_mint": r["new_mint"], "new_creator": r["new_creator"], "new_narrative": r["new_narrative"],
                            "key_conflict": e.key_conflict,
                            **{b: r[b] for b in B.BASELINES}, **{b + "_why": r[b + "_why"] or "" for b in B.BASELINES},
                            "B4C_description_only": r["B4C"],
                            "NC1_mean": float(np.nanmean([r[f"NC1_{q}"] for q in res["nc1_seeds"]])) if any(
                                math.isfinite(r[f"NC1_{q}"]) for q in res["nc1_seeds"]) else float("nan"),
                            "status": B.PROVISIONAL})
        dims = {"route": lambda e: e.route, "status_group": lambda e: B.status_group(e.status),
                "liquidity_bucket": lambda e: e.cohort.get("liquidity_bucket"), "launch_age_bucket": lambda e: e.cohort.get("launch_age_bucket"),
                "week": lambda e: e.cohort.get("week_utc"), "day": lambda e: e.day}
        for dim, fn in dims.items():
            for row in B.cohort_table(res["oos"], fn):
                cohorts.append({"target_short": s, "dimension": dim, **row, "status": B.PROVISIONAL})
        # training prevalence description at the development end
        y = np.array([e.y for e in dev_ex], float)
        lo, hi = K.wilson(int(y.sum()), len(y))
        prev_rows.append({"target_short": s, "cohort_dimension": "ALL", "cohort": "ALL", "n": len(y), "positives": int(y.sum()),
                          "prevalence": float(y.mean()) if len(y) else None, "wilson_lo": lo, "wilson_hi": hi,
                          "days": len({e.day for e in dev_ex}), "mints": len({e.mint for e in dev_ex}),
                          "as_of_utc": B._iso(H), "status": B.PROVISIONAL})
        for dim, fn in dims.items():
            for v in sorted({fn(e) or "UNKNOWN" for e in dev_ex}):
                ee = [e for e in dev_ex if (fn(e) or "UNKNOWN") == v]
                yy = np.array([e.y for e in ee], float)
                big = len(ee) >= C.ACCEPTANCE["min_bin_events"]
                wl, wh = K.wilson(int(yy.sum()), len(yy)) if big else (None, None)
                prev_rows.append({"target_short": s, "cohort_dimension": dim, "cohort": v, "n": len(ee), "positives": int(yy.sum()),
                                  "prevalence": float(yy.mean()) if big else None, "wilson_lo": wl, "wilson_hi": wh,
                                  "days": len({e.day for e in ee}), "mints": len({e.mint for e in ee}), "as_of_utc": B._iso(H),
                                  "note": "" if big else "n < 20: counts only, no rate claimed", "status": B.PROVISIONAL})
        # train-only artifacts at the holdout start
        train = examples_at(dev, target, H, frows, snaps, info)[0]
        cards = B.fit_all(target, train, H)
        smoke[s] = {}
        for b, card in cards.items():
            p = art_dir / s / f"{b}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(B.dumps(card))
            card_files.append(p)
            back = B.loads(p.read_text())
            p1, w1 = B.predict(card, train)
            p2, w2 = B.predict(back, train)
            same = bool(np.array_equal(np.nan_to_num(p1, nan=-1.0), np.nan_to_num(p2, nan=-1.0)) and w1 == w2)
            tampered = json.loads(p.read_text())
            if "logistic" in tampered["body"]:
                tampered["body"]["logistic"]["coef"][0] += 1e-9
            elif "p" in tampered["body"]:
                tampered["body"]["p"] += 1e-9
            else:
                tampered["n_train"] += 1
            try:
                B.verify_card(tampered)
                tamper_refused = False
            except B.ModelHashMismatch:
                tamper_refused = True
            fsh = fsha(p)
            R.verify_artifact(p, [fsh])
            smoke[s][b] = {"file_sha256": fsh, "model_sha": card["model_sha"], "abstain": card["body"].get("abstain"),
                           "n_train": card["n_train"], "k_train": card["k_train"], "n_used": card["n_used"],
                           "roundtrip_identical": same, "tamper_refused": tamper_refused,
                           "numbers": int(np.sum(np.isfinite(p1))), "pickle_used": False}
        # contract: an ABSTAIN document per target passes; a FORECAST claiming a B2 number is refused
        ex0 = train[-1]
        dinfo = info[ex0.decision_key]
        card2 = cards["B2"]
        doc = B.abstain_document(target, mint=ex0.mint, snapshot_hash=dinfo["row_sha256"], decision_time_utc=B._iso(ex0.decision_time),
                                 generated_at_utc=B._iso(H), reasons=["INSUFFICIENT_HISTORY", "MODEL_NOT_SELECTED"],
                                 base_rate=cards["B0"]["body"]["p"], card=card2)
        errs_abstain = C.validate(doc, backtest=C.BACKTEST_NOT_AVAILABLE)
        fc = dict(doc, prediction_status="FORECAST", abstain_reasons=[], probability=0.3, uncertainty_interval=[0.2, 0.4],
                  training_cutoff_utc=B._iso(H))
        mc = {"model_sha": card2["model_sha"], "feature_set_sha": card2["feature_set_sha"], "targets": card2["targets"],
              "target_version": card2["target_version"], "training_cutoff_utc": card2["training_cutoff_utc"]}
        errs_fc = C.validate(fc, model_card=mc, backtest=C.BACKTEST_NOT_AVAILABLE)
        smoke[s]["contract"] = {"abstain_errors": errs_abstain, "forecast_errors": errs_fc,
                                "abstain_valid": not errs_abstain, "forecast_refused": bool(errs_fc)}
        if a.npz:
            for f in res["folds"]:
                c2 = f["cards"]["B2"]
                if "abstain" in c2["body"]:
                    continue
                tr = examples_at(dev, target, f["cutoff"], frows, snaps, info)[0]
                use = [e for e in tr if all(math.isfinite(e.x[c]) for c in B.B2_REQUIRED)]
                X = B.matrix(use, B.B2_COLUMNS)
                Z = K.Prep.from_dict(c2["body"]["prep"]).transform(X)
                npz[f"{s}_f{f['fold']}_Z"] = Z
                npz[f"{s}_f{f['fold']}_y"] = B.labels_of(use)
                npz[f"{s}_f{f['fold']}_coef"] = np.r_[c2["body"]["logistic"]["intercept"], c2["body"]["logistic"]["coef"]]
            for b in ("B2", "B3", "B4"):
                rr = [r for r in res["oos"] if math.isfinite(r[b])]
                if rr:
                    npz[f"{s}_oos_{b}_y"] = np.array([r["y"] for r in rr], float)
                    npz[f"{s}_oos_{b}_p"] = np.array([r[b] for r in rr], float)

    # Holm across the three targets, per gated baseline, on the ALL view; verdicts recomputed with it
    holm_adj = {}
    for (view, b), per_t in holm_in.items():
        ts = list(L.TARGETS)
        adj = K.holm([per_t.get(t) if per_t.get(t) is not None else float("nan") for t in ts])
        for t, v in zip(ts, adj):
            holm_adj[(t, view, b)] = v
    mrows = []
    for target, view, ev, kind in metrics:
        ph = holm_adj.get((target, view, ev["baseline"]))
        if kind == "BASELINE" and ev["baseline"] != "B0":
            ev["verdict"] = B.verdict(ev, ph if ph is not None and math.isfinite(ph) else None) if ev.get("n_with_number") else ev["verdict"]
        if ev["baseline"] == "B0":
            ev["verdict"] = "REFERENCE"
        if kind == "DESCRIPTION_ONLY":
            ev["verdict"] = "DESCRIPTION_ONLY_NOT_AS_OF"
        mrows.append(metric_row(target, view, ev, kind=kind, extra={"p_holm": ph,
                                "split_fingerprint": folds_ev[SHORT[target]]["split_fingerprint"],
                                "label_set_sha": label_set[target]["label_set_sha"]}))
    # NC1 aggregate rows into the metrics table
    for s in SHORT.values():
        for view in VIEWS:
            v = [r for r in nc1_rows if r["target_short"] == s and r["view"] == view and r.get("n")]
            bss = [r["bss"] for r in v if r.get("bss") is not None and math.isfinite(r["bss"])]
            mrows.append({"target": [t for t, x in SHORT.items() if x == s][0], "target_short": s, "view": view, "baseline": "NC1",
                          "kind": "NEGATIVE_CONTROL", "n_with_number": v[0]["n"] if v else 0, "nc1_seeds": len(v),
                          "nc1_mean_bss": float(np.mean(bss)) if bss else None,
                          "nc1_share_bss_gt_0": float(np.mean([x > 0 for x in bss])) if bss else None,
                          "nc1_mean_brier": float(np.mean([r["brier"] for r in v])) if v else None,
                          "verdict": ("NC1_DEGRADES_OR_EQUAL" if bss and np.mean(bss) <= 0 else
                                      "NC1_FINDING_MEAN_BSS_ABOVE_0" if bss else "INSUFFICIENT_HISTORY"),
                          "status": B.PROVISIONAL, "revision_check_claimed": False})
    exp = out / "experiments"
    write_csv(exp / "BASELINE_METRICS.csv", mrows)
    write_csv(exp / "CALIBRATION_BINS.csv", calib)
    write_csv(exp / "OOS_PREDICTIONS.csv", oos_out)
    write_csv(exp / "OOS_COHORTS.csv", cohorts)
    write_csv(exp / "TRAINING_PREVALENCE.csv", prev_rows)
    write_csv(exp / "NC1_SEEDS.csv", nc1_rows)
    # search ledger: Phase 07 runs plus the Phase 04 bake-off runs as tried configurations (PI-D-034)
    bake = json.loads((REPO / "audits/predictive-intelligence/phase_04/adoption/BAKEOFF_RESULTS.json").read_text())
    for ds in ("dev24", "dev6"):
        for name in sorted(bake["approaches"][ds]):
            ledger.append({"phase": "04", "experiment_id": f"P04:{ds}:{name}", "target": L.T1 if ds == "dev24" else L.T1B,
                           "candidate": name.split("__")[0], "kind": "BAKEOFF_ONLY", "view": name.split("__")[1], "seed": "",
                           "folds": "", "n_rows": "", "n_with_number": "",
                           "verdict": "tried configuration (PI-D-034); labels without token=<mint> for 8 of 102 and 9 of 159 events (PI-D-038)",
                           "split_fingerprint": ""})
    write_csv(exp / "SEARCH_LEDGER.csv", ledger)
    ev_dir = out / "evidence"
    write_json(ev_dir / "folds.json", folds_ev)
    write_json(ev_dir / "serialization_smoke.json", smoke)
    write_json(ev_dir / "traps.json", traps(dev, frows, info))
    write_json(ev_dir / "label_sets.json", label_set)
    if a.npz:
        np.savez(a.npz, **npz)
    store_sha_after = {p: fsha(p) for p in (a.dev_store, a.feature_store)}
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    outputs = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file() and p.name != "run_log.json")
    write_json(ev_dir / "run_log.json", {
        "start_utc": start_utc, "end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "head": head,
        "wall_s": round(time.time() - t0, 2), "cpu_s": round(time.process_time() - c0, 2),
        "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "socket_events": SOCKET_EVENTS, "vendor_calls": 0, "bootstrap_reps": a.reps,
        "code_sha256": {c: fsha(REPO / c) for c in CODE}, "stores": {"before": store_sha_before, "after": store_sha_after,
                                                                    "unchanged": store_sha_before == store_sha_after},
        "registry_sha": C.registry_sha256(), "feature_set_sha": F.feature_set_sha(), "labels_version": L.LABELS_VERSION,
        "as_of_utc": B._iso(H), "status": B.PROVISIONAL, "revision_check_claimed": False,
        "outputs_sha256": {o: fsha(out / o) for o in outputs}})
    print(json.dumps({"targets": {s: folds_ev[s]["status"] for s in folds_ev}, "outputs": len(outputs),
                      "socket_events": len(SOCKET_EVENTS), "stores_unchanged": store_sha_before == store_sha_after}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
