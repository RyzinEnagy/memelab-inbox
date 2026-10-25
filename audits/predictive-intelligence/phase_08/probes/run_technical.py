"""Phase 08 technical runner: tech-1 for every labelled development decision (with the version 2 consistency check), the frozen
walk-forward of M1 to M3, ablations A1 to A5 and NC1-T beside Phase 07's B0 and B2 on the same folds, the train-only cards at the
holdout start, the traps, the forecast trace, coverage, hit and miss tables and the cumulative search ledger.

Reads only: the Phase 06 development store (labels through `labels.training_labels`, decision rows) and the Phase 05 store
(stored provider-mode version 2 snapshots through `features.training_view`, candles through `features.AsOfView`), both opened
read-only. Never opens the sealed holdout folder. No network: an audit hook refuses any socket connect. Deterministic: two
runs into two folders give identical files except `evidence/run_log.json` (times).

    python -B run_technical.py OUTDIR [--reps 2000] [--dev-store PATH] [--feature-store PATH] [--npz PATH]

PROVISIONAL (PI-D-046): until Phase 06's 48 h revision re-read is folded in. If it changes a development label, rerun this
script at the Phase 08 code commit; the new outputs supersede these.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import resource
import statistics
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
from memelab.predictive import technical as T  # noqa: E402

SOCKET_EVENTS: list[str] = []


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKET_EVENTS.append(event)
        raise RuntimeError(f"Phase 08 runner makes no network call ({event})")


sys.addaudithook(_hook)

_spec = importlib.util.spec_from_file_location("p07_run_baselines", REPO / "audits/predictive-intelligence/phase_07/probes/run_baselines.py")
P7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P7)

SHORT, H = P7.SHORT, P7.H
CODE = ["memelab/predictive/technical.py", "memelab/predictive/baselines.py", "memelab/predictive/stats.py",
        "memelab/predictive/features.py", "memelab/predictive/labels.py", "memelab/predictive/contract.py",
        "audits/predictive-intelligence/phase_07/probes/run_baselines.py",
        "audits/predictive-intelligence/phase_08/probes/run_technical.py"]
VIEWS = P7.VIEWS
P07 = REPO / "audits/predictive-intelligence/phase_07"
P07_SPLITS = {"T1_24h": "0ab64525e04b8664a1cab51c9e24f5fa4f750681d32a5d97bfc520710e3845a4",
              "T1b_6h": "aa16e7adeae7d5bc8567de9ab85ed1f28843afe51bc0de9b52e24d587beb8a31",
              "T2_24h": "82a1c33b12cef45995eb15edd07b8e27ddcd76eafbdb8c503f5feb9501be86cd"}
# real-data runs before the recorded run (P22): appended here before the recorded run, never removed
DEBUG_RUNS: list[str] = [
    "features-only probe before the code commit (about 21:40Z): tech-1 and the version 2 consistency on the 240 labelled development decisions; label rows read for their decision keys only, no label value used, no fit, no metric",
]
COMPARISONS = [(m, "B0") for m in ("B2",) + T.ALL_IDS] + [(m, "B2") for m in T.MODEL_IDS + ("A5_T_B2_TC",)]


def write_csv(path: Path, rows: list[dict]) -> None:
    P7.write_csv(path, rows)


def write_json(path: Path, obj) -> None:
    P7.write_json(path, obj)


# ---------------------------------------------------------------- tech-1 for every labelled development decision
def tech_snapshots(dev, fs, frows):
    keys = {}
    for t in L.TARGETS:
        for kc in (True, False):
            for r in L.training_labels(dev, H, t, mode="provider", include_key_conflict=kc):
                keys[r["decision_key"]] = r
    reasons: dict[str, dict] = {}
    for r in fs.execute("SELECT s.decision_key, v.feature_name, v.missing_reason FROM predictive_snapshots s JOIN predictive_feature_values v "
                        "USING(snapshot_key) WHERE s.availability_mode='provider' AND s.decision_key IS NOT NULL AND v.feature_name LIKE 'cdl_%'"):
        reasons.setdefault(r["decision_key"], {})[r["feature_name"]] = r["missing_reason"]
    snaps, incons, unavailable = {}, {}, []
    lag = 300.0
    for k in sorted(keys):
        r = keys[k]
        s = T.technical_as_of(fs, r["chain"], r["mint"], float(r["decision_time"]), mode="provider", decision_key=k)
        v2 = dict(frows[k])
        v2["__reasons"] = reasons.get(k, {})
        d = T.v2_consistency(s, v2)
        if d:
            incons[k] = d
        snaps[k] = s
        pool = s["pool_address"]
        Tt = float(r["decision_time"])
        if pool:
            q = fs.execute("SELECT COUNT(*) n, SUM(CASE WHEN end_at > ? THEN 1 ELSE 0 END) holding, MIN(available_at) first_av "
                           "FROM predictive_candles WHERE chain='solana' AND mint=? AND pool_address=? AND period_s=300 "
                           "AND vanished=0 AND start_at < ? AND available_at > ?", (Tt, r["mint"], pool, Tt, Tt)).fetchone()
            used_late = sum(1 for v in s["values"].values() if v["available_at"] is not None and v["available_at"] > Tt)
            unavailable.append({"decision_key": k, "pool_set": True, "candles_started_before_T_not_available": q["n"] or 0,
                                "of_which_holding_or_ending_after_T": q["holding"] or 0,
                                "of_which_closed_but_inside_provider_lag": (q["n"] or 0) - (q["holding"] or 0),
                                "inputs_used_after_T": used_late})
        else:
            unavailable.append({"decision_key": k, "pool_set": False, "candles_started_before_T_not_available": 0,
                                "of_which_holding_or_ending_after_T": 0, "of_which_closed_but_inside_provider_lag": 0,
                                "inputs_used_after_T": 0})
    return snaps, incons, unavailable, lag


def tex_at(dev, target, as_of, frows, snaps, info, tsnaps, *, include_kc=True):
    ex, rows = P7.examples_at(dev, target, as_of, frows, snaps, info, include_kc=include_kc)
    return T.attach(ex, tsnaps), rows


# ---------------------------------------------------------------- metrics
def metric_row(target, view, ev, *, model, reference, kind, extra):
    iv = ev.get("intervals") or {}
    cal = ev.get("calibration") or {}
    return {"target": target, "target_short": SHORT[target], "view": view, "model": model, "reference": reference, "kind": kind,
            "n_oos_rows": ev["n_rows"], "n_with_number": ev["n_with_number"], "coverage": ev.get("coverage"),
            "abstain_reasons": ";".join(f"{k}={v}" for k, v in sorted(ev.get("abstain_reasons", {}).items())),
            "positives": ev.get("positives"), "prevalence": ev.get("prevalence"), "decision_days": ev.get("days"),
            "mints": ev.get("mints"), "folds_with_number": ev.get("folds"), "brier": ev.get("brier"), "brier_ref": ev.get("brier_ref"),
            "bss_vs_ref": ev.get("bss"), "log_loss": ev.get("log_loss"), "log_loss_ref": ev.get("log_loss_ref"),
            "roc_auc": ev.get("auc"), "average_precision": ev.get("average_precision"),
            "bss_ci_day_lo": (iv.get("day", {}).get("ci") or [None, None])[0], "bss_ci_day_hi": (iv.get("day", {}).get("ci") or [None, None])[1],
            "bss_ci_mint_lo": (iv.get("mint", {}).get("ci") or [None, None])[0], "bss_ci_mint_hi": (iv.get("mint", {}).get("ci") or [None, None])[1],
            "governing": ev.get("governing") or ("UNDEFINED" if ev.get("n_with_number") else ""),
            "p_one_sided": ev.get("p_one_sided"), "p_holm": extra.get("p_holm"), "ess_day": ev.get("ess_day"), "ess_mint": ev.get("ess_mint"),
            "cal_mean_pred": cal.get("mean_pred"), "cal_observed": cal.get("observed"), "cal_in_the_large_ok": cal.get("in_the_large_ok"),
            "cal_bins": len(cal.get("bins") or []), "cal_every_bin_ok": cal.get("every_bin_ok"), "ece": cal.get("ece"),
            "degenerate": extra.get("degenerate"), "verdict": ev.get("verdict"), "promotion": "MODEL_NOT_PROMOTED" if model != "B2" else "",
            "status": T.PROVISIONAL, "revision_check_claimed": False,
            **{k: v for k, v in extra.items() if k not in ("p_holm", "degenerate")}}


def nc1t_summary(rows, seeds, reps):
    out = []
    for s in seeds:
        key = f"NC1T_{s}"
        if not rows or not any(math.isfinite(r[key]) for r in rows):
            out.append({"seed": s, "n": 0})
            continue
        ev = B.evaluate(rows, key, reps=reps, seed=20261025 + s, boot=False)
        out.append({"seed": s, "n": ev["n_with_number"], "brier": ev.get("brier"), "brier_ref": ev.get("brier_ref"), "bss": ev.get("bss"),
                    "positives": ev.get("positives"), "days": ev.get("days")})
    return out


# ---------------------------------------------------------------- traps and the forecast trace
def traps(fs, dev_ex_by_target, tsnaps, cards_h):
    out = {}
    # NC2-T: the next-hour return after the decision (tech_log_ret_1h at T + 1 h), declared at its true availability
    n = val = refused_allow = refused_asof = accepted = 0
    min_delay = None
    seen = set()
    for target, exs in dev_ex_by_target.items():
        for e in exs:
            if e.decision_key in seen or e.tech_status is not None:
                continue
            seen.add(e.decision_key)
            n += 1
            fut = T.technical_as_of(fs, e.chain, e.mint, e.decision_time + 3600, mode="provider")["values"]["tech_log_ret_1h"]
            if fut["value"] is None:
                continue
            val += 1
            av = float(fut["available_at"])
            min_delay = av - e.decision_time if min_delay is None else min(min_delay, av - e.decision_time)
            e2 = T.TExample(**{**e.__dict__, "x": {**e.x, "trap_next_hour_return": fut["value"]},
                               "avail": {**e.avail, "trap_next_hour_return": av}})
            try:
                T.check_asof([e2], ["trap_next_hour_return"], as_of=None, with_labels=False)
                accepted += 1
            except F.AsOfError:
                refused_allow += 1
            e3 = T.TExample(**{**e.__dict__, "x": {**e.x, "tech_log_ret_1h": fut["value"]}, "avail": {**e.avail, "tech_log_ret_1h": av}})
            try:
                T.check_asof([e3], ["tech_log_ret_1h"], as_of=None, with_labels=False)
                accepted += 1
            except F.AsOfError:
                refused_asof += 1
    out["NC2T"] = {"decisions_with_every_tech_feature": n, "with_a_future_value": val, "refused_by_allowlist": refused_allow,
                   "refused_by_validate_rows": refused_asof, "accepted": accepted, "min_trap_delay_s": min_delay,
                   "pass": accepted == 0 and refused_allow == refused_asof == val and val > 0}
    # P06-T: cutoff moved to T + 600 s (the candle holding T and the one closing at T become visible)
    changed = refused6 = accepted6 = 0
    nn = 0
    for k, s in sorted(tsnaps.items()):
        if T.row_status(s) is not None:
            continue
        nn += 1
        later = T.technical_as_of(fs, s["chain"], s["mint"], s["decision_time"] + 600, mode="provider")["values"]
        diff = [c for c in T.TECH if later[c]["value"] != s["values"][c]["value"]]
        if not diff:
            continue
        changed += 1
        c = diff[0]
        row = {"decision_time": s["decision_time"], c: later[c]["value"], c + "__available_at": later[c]["available_at"]}
        try:
            F.validate_rows([row], columns=list(row), availability=[c + "__available_at"])
            accepted6 += 1
        except F.AsOfError:
            refused6 += 1
    out["P06T"] = {"decisions_with_every_tech_feature": nn, "values_changed_by_moving_the_cutoff_600s": changed,
                   "refused": refused6, "accepted": accepted6, "pass": accepted6 == 0 and refused6 == changed}
    # P13-T: a holdout-start card applied to the earliest development decision
    res = {}
    for target, exs in dev_ex_by_target.items():
        e = min(exs, key=lambda x: (x.decision_time, x.mint))
        for m, card in cards_h[target].items():
            try:
                T.predict(card, [e])
                res[f"{SHORT[target]}:{m}"] = "ACCEPTED"
            except T.ModelTrainedAfterDecision:
                res[f"{SHORT[target]}:{m}"] = "REFUSED"
    out["P13T"] = {"results": res, "pass": all(v == "REFUSED" for v in res.values())}
    # CX-08 on real data: revisions that changed only opens, highs or lows, visible at labelled decisions on their pools
    n_ow = 0
    pools = {(s["mint"], s["pool_address"]) for s in tsnaps.values() if s["pool_address"]}
    for mint, pool in sorted(pools):
        n_ow += fs.execute("SELECT COUNT(*) FROM predictive_candles WHERE mint=? AND pool_address=? AND revision_kind='OPEN_WINDOW'",
                           (mint, pool)).fetchone()[0]
    out["CX08_real"] = {"pools": len(pools), "open_window_revisions_on_these_pools": n_ow,
                        "note": "tech-1 reads closes and volumes only (test_tech_reads_closes_and_volumes_only, test_cx08_*); "
                                "these revisions cannot move a tech-1 value"}
    return out


def trace(fs, res_by_target, tsnaps, cards_h, info):
    pick = None
    for target in (L.T1B, L.T1, L.T2):
        rows = sorted([r for r in res_by_target[target]["oos"] if r["example"].tech_status is None],
                      key=lambda r: (r["example"].decision_time, r["example"].mint))
        if rows:
            pick = (target, rows[0])
            break
    if pick is None:
        return {"status": "NO_OOS_ROW_WITH_EVERY_TECH_FEATURE"}
    target, row = pick
    e = row["example"]
    s = tsnaps[e.decision_key]
    Tt = e.decision_time
    view = F.AsOfView(fs, Tt, "provider")
    cs = [c for c in view.candles("solana", e.mint, s["pool_address"]) if c["end_at"] <= Tt and c["end_at"] > Tt - 86400 - 3600]
    excl = fs.execute("SELECT start_at, end_at, available_at, retrieved_at, available_basis FROM predictive_candles WHERE mint=? AND "
                      "pool_address=? AND period_s=300 AND vanished=0 AND start_at < ? AND available_at > ? ORDER BY start_at",
                      (e.mint, s["pool_address"], Tt + 600, Tt)).fetchall()
    fold = res_by_target[target]["folds"][row["fold"]]
    out = {"target": target, "decision_key": e.decision_key, "chain": e.chain, "mint": e.mint, "pool_address": s["pool_address"],
           "decision_time": Tt, "decision_time_utc": B._iso(Tt), "decision_time_basis": "EXPORT_COMMIT",
           "row_sha256": info[e.decision_key]["row_sha256"], "label_y": e.y, "fold": row["fold"], "fold_cutoff_utc": fold["cutoff_utc"],
           "selection_rule": "earliest out-of-sample row of T1b (then T1, T2) by decision time then mint with every tech-1 feature",
           "candles_read": [{"start_at": c["start_at"], "end_at": c["end_at"], "available_at": c["available_at"],
                             "retrieved_at": c["retrieved_at"], "available_basis": c["available_basis"], "close": c["c"], "volume_usd": c["v"],
                             "obs_key": c["obs_key"]} for c in cs],
           "candles_not_yet_available_at_T": [dict(r) for r in excl][:6],
           "tech_values": {k: v["value"] for k, v in s["values"].items()},
           "tech_available_at": {k: v["available_at"] for k, v in s["values"].items()},
           "b2_inputs": {c: e.x[c] for c in B.B2_COLUMNS}, "tech_snapshot_sha": s["tech_snapshot_sha"],
           "models": {}}
    for m in ("B0", "B2") + T.MODEL_IDS:
        card = fold["cards"][m]
        out["models"][m] = {"card_model_sha": card["model_sha"], "training_cutoff_utc": card["training_cutoff_utc"],
                            "number": None if not math.isfinite(row[m]) else row[m], "abstain": row.get(m + "_why"),
                            "card": card}
    # invalid inputs that must be rejected
    rej = {}
    e_late = T.TExample(**{**e.__dict__, "avail": {**e.avail, "tech_log_ret_1h": Tt + 300}})
    try:
        T.check_asof([e_late], ["tech_log_ret_1h"], as_of=None, with_labels=False)
        rej["candle_closing_at_T_used"] = "ACCEPTED"
    except F.AsOfError as ex:
        rej["candle_closing_at_T_used"] = f"REFUSED: {ex}"
    try:
        F.AsOfView(fs, Tt).audit.check("candle", [{"_avail": Tt + 1}], Tt)
        rej["view_row_available_after_T"] = "ACCEPTED"
    except F.LeakageError as ex:
        rej["view_row_available_after_T"] = f"REFUSED: {str(ex)[:160]}"
    e_nan = T.TExample(**{**e.__dict__, "x": {**e.x, "tech_rv_1h": float("nan")}})
    p, why = T.predict_numbers(fold["cards"]["M1_T_LOGIT"], [e_nan])
    rej["non_finite_feature"] = f"no number, reason {why[0]}" if not math.isfinite(p[0]) else "ACCEPTED"
    try:
        T.Stumps(rounds=1).fit(np.array([[0.0], [float("nan")]] * 20), np.array([0.0, 1.0] * 20))
        rej["non_finite_feature_in_a_fit"] = "ACCEPTED"
    except ValueError as ex:
        rej["non_finite_feature_in_a_fit"] = f"REFUSED: {ex}"
    try:
        T.predict(cards_h[target]["M2_T_LOGIT_B2"], [e])
        rej["holdout_start_card_on_this_development_decision"] = "ACCEPTED"
    except T.ModelTrainedAfterDecision as ex:
        rej["holdout_start_card_on_this_development_decision"] = f"REFUSED: {ex}"
    out["invalid_inputs"] = rej
    out["invalid_inputs_all_rejected"] = all(not v.startswith("ACCEPTED") for v in rej.values())
    # latency of one forecast from the store (tech-1 at T plus every fold card)
    lat = []
    for _ in range(20):
        t0 = time.perf_counter()
        s2 = T.technical_as_of(fs, e.chain, e.mint, Tt, mode="provider", decision_key=e.decision_key)
        ex2 = T.attach([B.Example(**{k: v for k, v in e.__dict__.items() if k in B.Example.__dataclass_fields__})], {e.decision_key: s2})
        for m in T.MODEL_IDS:
            T.predict(fold["cards"][m], ex2)
        lat.append(time.perf_counter() - t0)
    out["latency_s_median_of_20"] = round(statistics.median(lat), 4)
    return out


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--reps", type=int, default=C.ACCEPTANCE["bootstrap"]["min_replicates"])
    ap.add_argument("--dev-store", default=P7.DEV_STORE)
    ap.add_argument("--feature-store", default=P7.FEATURE_STORE)
    ap.add_argument("--npz", default=None)
    a = ap.parse_args()
    out = Path(a.out)
    t0, c0 = time.time(), time.process_time()
    start_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
    for p in (a.dev_store, a.feature_store):
        L.refuse_sealed(p)
        R.refuse_bakeoff_labels(path=p)
    store_sha_before = {p: P7.fsha(p) for p in (a.dev_store, a.feature_store)}
    dev, fs = P7.ro(a.dev_store), P7.ro(a.feature_store)
    frows, snaps, info = P7.load_inputs(dev, fs)
    tsnaps, incons, unavailable, _ = tech_snapshots(dev, fs, frows)
    if incons:
        write_json(out / "evidence" / "v2_consistency.json", {"inconsistent": incons})
        raise SystemExit(f"tech-1 and version 2 disagree on {len(incons)} decisions: stop (PI-D-050 item 2)")
    p07_oos = {}
    with open(P07 / "experiments/OOS_PREDICTIONS.csv") as f:
        for r in csv.DictReader(f):
            p07_oos[(r["target_short"], r["decision_key"])] = r

    mrows, abl, hm, oos_out, cov, nc1_rows, ledger, folds_ev = [], [], [], [], [], [], [], {}
    holm_in: dict[tuple, dict] = {}
    metrics = []
    res_by_target, dev_ex_by_target, cards_h, smoke = {}, {}, {}, {}
    p07_equal = {}
    npz: dict[str, np.ndarray] = {}
    art = out / "artifacts"
    for target in L.TARGETS:
        s = SHORT[target]
        runs = {}
        for kc in (True, False):
            dev_ex, _ = tex_at(dev, target, H, frows, snaps, info, tsnaps, include_kc=kc)
            res = T.walk_forward(target, dev_ex, lambda c: tex_at(dev, target, c, frows, snaps, info, tsnaps, include_kc=kc)[0])
            runs[kc] = (dev_ex, res)
        dev_ex, res = runs[True]
        res_by_target[target], dev_ex_by_target[target] = res, dev_ex
        if res.get("split_fingerprint") != P07_SPLITS[s]:
            raise SystemExit(f"{s}: split fingerprint differs from Phase 07's")
        diffs = 0
        for r in res["oos"]:
            q = p07_oos[(s, r["example"].decision_key)]
            for b in ("B0", "B2"):
                mine = "" if not math.isfinite(r[b]) else f"{r[b]:.6f}"
                diffs += mine != q[b]
        p07_equal[s] = {"oos_rows": len(res["oos"]), "b0_b2_differences_at_6_decimals": diffs, "split_fingerprint_equal": True}
        if diffs:
            raise SystemExit(f"{s}: B0 or B2 out-of-sample numbers differ from Phase 07's ({diffs})")
        folds_ev[s] = {"status": res["status"], "split_fingerprint": res.get("split_fingerprint"), "audit": res["audit"],
                       "folds": [{k: v for k, v in f.items() if k != "cards"} for f in res["folds"]],
                       "no_key_conflict_folds": [{k: v for k, v in f.items() if k != "cards"} for f in runs[False][1]["folds"]]}
        write_json(art / "folds" / f"{s}.json", {"target": target, "status": T.PROVISIONAL,
                                                 "folds": [{"fold": f["fold"], "cutoff_utc": f["cutoff_utc"],
                                                            "cards": {m: f["cards"][m] for m in T.ALL_IDS}} for f in res["folds"]]})
        for view in VIEWS:
            rows = P7.view_rows(runs[view != "NO_KEY_CONFLICT"][1]["oos"], view)
            for m, ref in COMPARISONS:
                ev = B.evaluate(rows, m, reference=ref, reps=a.reps)
                kind = ("REFERENCE_PHASE07" if m == "B2" else "ABLATION" if m.startswith("A") else
                        "TECHNICAL_MODEL_PRIMARY" if m == T.PRIMARY else "TECHNICAL_MODEL")
                deg = T.degenerate([r[m] for r in rows])
                metrics.append((target, view, ev, m, ref, kind, deg))
                if view == "ALL":
                    holm_in.setdefault((m, ref), {})[target] = ev.get("p_one_sided")
                ledger.append({"phase": "08", "experiment_id": f"P08:{target}:{m}", "target": target, "candidate": m, "kind": kind,
                               "view": f"{view} vs {ref}", "seed": 20261025, "folds": len(res["folds"]), "n_rows": ev["n_rows"],
                               "n_with_number": ev["n_with_number"], "verdict": ev.get("verdict"),
                               "split_fingerprint": res.get("split_fingerprint") if view != "NO_KEY_CONFLICT" else runs[False][1].get("split_fingerprint")})
            ledger.append({"phase": "08", "experiment_id": f"P08:{target}:B0", "target": target, "candidate": "B0",
                           "kind": "REFERENCE_PHASE07", "view": view, "seed": "", "folds": len(res["folds"]), "n_rows": len(rows),
                           "n_with_number": sum(1 for r in rows if math.isfinite(r["B0"])), "verdict": "REFERENCE",
                           "split_fingerprint": res.get("split_fingerprint")})
            nrows = [r for r in rows if any(math.isfinite(r[f"NC1T_{q}"]) for q in res.get("nc1_seeds", []))]
            for nc in nc1t_summary(rows, res.get("nc1_seeds", []), a.reps):
                nc1_rows.append({"target_short": s, "view": view, **nc})
                ledger.append({"phase": "08", "experiment_id": f"P08:{target}:NC1T_seed{nc['seed']:02d}", "target": target,
                               "candidate": "NC1T", "kind": "NEGATIVE_CONTROL", "view": view, "seed": nc["seed"], "folds": len(res["folds"]),
                               "n_rows": len(rows), "n_with_number": nc["n"], "verdict": "", "split_fingerprint": res.get("split_fingerprint")})
            del nrows
        for r in res["oos"]:
            e = r["example"]
            oos_out.append({"target_short": s, "fold": r["fold"], "cutoff_utc": B._iso(r["cutoff"]), "decision_key": e.decision_key,
                            "mint": e.mint, "decision_time_utc": B._iso(e.decision_time), "day": e.day, "y": e.y, "route": e.route,
                            "tech_status": e.tech_status or "COMPLETE", "tech_missing_reasons": ";".join(sorted(set(e.tech_reasons.values()))),
                            "new_mint": r["new_mint"], "key_conflict": e.key_conflict,
                            **{m: r[m] for m in ("B0", "B2") + T.ALL_IDS}, **{m + "_why": r[m + "_why"] or "" for m in ("B0", "B2") + T.ALL_IDS},
                            "NC1T_mean": float(np.nanmean([r[f"NC1T_{q}"] for q in res["nc1_seeds"]])) if any(
                                math.isfinite(r[f"NC1T_{q}"]) for q in res["nc1_seeds"]) else float("nan"),
                            "status": T.PROVISIONAL})
        dims = {"route": lambda e: e.route, "liquidity_bucket": lambda e: e.cohort.get("liquidity_bucket"),
                "launch_age_bucket": lambda e: e.cohort.get("launch_age_bucket"), "week": lambda e: e.cohort.get("week_utc"),
                "day": lambda e: e.day}
        for dim, fn in dims.items():
            for m in ("B2",) + T.MODEL_IDS:
                for row in T.hit_miss(res["oos"], m, fn):
                    hm.append({"target_short": s, "dimension": dim, "model": m, "threshold": "fold B0 (training prevalence)", **row,
                               "status": T.PROVISIONAL})
        for which, exs in (("DEVELOPMENT_AT_HOLDOUT_START", dev_ex), ("OUT_OF_SAMPLE", [r["example"] for r in res["oos"]])):
            for dim, fn in [("ALL", lambda e: "ALL")] + list(dims.items()):
                for v in sorted({str(fn(e) or "UNKNOWN") for e in exs}):
                    ee = [e for e in exs if str(fn(e) or "UNKNOWN") == v]
                    rs: dict[str, int] = {}
                    for e in ee:
                        for reason in sorted(set(e.tech_reasons.values())):
                            rs[reason] = rs.get(reason, 0) + 1
                    cov.append({"target_short": s, "set": which, "dimension": dim, "value": v, "n": len(ee),
                                "positives": int(sum(e.y for e in ee)) if which == "OUT_OF_SAMPLE" else "",
                                "tech_complete": sum(1 for e in ee if e.tech_status is None),
                                "ood": sum(1 for e in ee if e.tech_status == "OOD"),
                                "censored_retrieval": sum(1 for e in ee if e.tech_status == "CENSORED_RETRIEVAL"),
                                "rows_with_reason": ";".join(f"{k}={v2}" for k, v2 in sorted(rs.items()))})
        # train-only cards at the holdout start
        train = tex_at(dev, target, H, frows, snaps, info, tsnaps)[0]
        cards_h[target] = {m: T.fit(m, target, train, H) for m in T.MODEL_IDS}
        smoke[s] = {}
        for m, card in cards_h[target].items():
            p = art / s / f"{m}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(T.dumps(card))
            back = T.loads(p.read_text())
            p1, w1 = T.predict_numbers(card, train)
            p2, w2 = T.predict_numbers(back, train)
            same = bool(np.array_equal(np.nan_to_num(p1, nan=-1.0), np.nan_to_num(p2, nan=-1.0)) and w1 == w2)
            tam = json.loads(p.read_text())
            if "logistic" in tam["body"]:
                tam["body"]["logistic"]["coef"][0] += 1e-9
            elif "stumps" in tam["body"]:
                tam["body"]["stumps"]["init"] += 1e-9
            else:
                tam["n_train"] += 1
            try:
                T.verify_card(tam)
                refused = False
            except B.ModelHashMismatch:
                refused = True
            fsh = P7.fsha(p)
            R.verify_artifact(p, [fsh])
            smoke[s][m] = {"file_sha256": fsh, "model_sha": card["model_sha"], "abstain": card["body"].get("abstain"),
                           "n_train": card["n_train"], "k_train": card["k_train"], "n_used": card["n_used"], "k_used": card["k_used"],
                           "roundtrip_identical": same, "tamper_refused": refused, "numbers": int(np.sum(np.isfinite(p1))),
                           "pickle_used": False}
        ex0 = train[-1]
        c2 = cards_h[target][T.PRIMARY]
        doc = B.abstain_document(target, mint=ex0.mint, snapshot_hash=info[ex0.decision_key]["row_sha256"],
                                 decision_time_utc=B._iso(ex0.decision_time), generated_at_utc=B._iso(H),
                                 reasons=["INSUFFICIENT_HISTORY", "MODEL_NOT_SELECTED"], base_rate=float(np.mean([e.y for e in train])), card=c2)
        ea = C.validate(doc, backtest=C.BACKTEST_NOT_AVAILABLE)
        fc = dict(doc, prediction_status="FORECAST", abstain_reasons=[], probability=0.3, uncertainty_interval=[0.2, 0.4])
        mc = {k: c2[k] for k in ("model_sha", "feature_set_sha", "targets", "target_version", "training_cutoff_utc")}
        ef = C.validate(fc, model_card=mc, backtest=C.BACKTEST_NOT_AVAILABLE)
        smoke[s]["contract"] = {"abstain_errors": ea, "forecast_errors": ef, "abstain_valid": not ea, "forecast_refused": bool(ef)}
        if a.npz:
            for f in res["folds"]:
                tr = tex_at(dev, target, f["cutoff"], frows, snaps, info, tsnaps)[0]
                for m in ("M1_T_LOGIT", "M2_T_LOGIT_B2", "M3_T_STUMPS"):
                    c = f["cards"][m]
                    if "abstain" in c["body"]:
                        continue
                    use = [e for e in tr if T.complete(e, c["body"]["spec"]["rows"])]
                    X = T.matrix(use, c["body"]["spec"]["columns"])
                    tag = f"{s}_f{f['fold']}_{m}"
                    npz[tag + "_X"] = X
                    npz[tag + "_y"] = B.labels_of(use)
                    if "logistic" in c["body"]:
                        npz[tag + "_Z"] = K.Prep.from_dict(c["body"]["prep"]).transform(X)
                        npz[tag + "_coef"] = np.r_[c["body"]["logistic"]["intercept"], c["body"]["logistic"]["coef"]]
                    else:
                        npz[tag + "_p"] = T.Stumps.from_dict(c["body"]["stumps"]).predict_proba1(X)
    # Holm across the three targets per (model, reference) on the ALL view
    holm_adj = {}
    for key, per_t in holm_in.items():
        ts = list(L.TARGETS)
        adj = K.holm([per_t.get(t) if per_t.get(t) is not None else float("nan") for t in ts])
        for t, v in zip(ts, adj):
            holm_adj[(t,) + key] = v
    for target, view, ev, m, ref, kind, deg in metrics:
        ph = holm_adj.get((target, m, ref)) if view == "ALL" else None
        if ev.get("n_with_number"):
            ev["verdict"] = B.verdict(ev, ph if ph is not None and math.isfinite(ph) else None)
        mrows.append(metric_row(target, view, ev, model=m, reference=ref, kind=kind,
                                extra={"p_holm": ph, "degenerate": deg, "split_fingerprint": folds_ev[SHORT[target]]["split_fingerprint"]}))
        if view == "ALL" and m.startswith("A") and ref == "B0":
            abl.append({"target_short": SHORT[target], "ablation": m, "n_with_number": ev["n_with_number"], "positives": ev.get("positives"),
                        "brier": ev.get("brier"), "brier_b0": ev.get("brier_ref"), "bss_vs_b0": ev.get("bss"), "verdict": ev.get("verdict"),
                        "abstain_reasons": ";".join(f"{k}={v}" for k, v in sorted(ev.get("abstain_reasons", {}).items())),
                        "status": T.PROVISIONAL})
    for s in SHORT.values():
        for view in VIEWS:
            v = [r for r in nc1_rows if r["target_short"] == s and r["view"] == view and r.get("n")]
            bss = [r["bss"] for r in v if r.get("bss") is not None and math.isfinite(r["bss"])]
            mean_bss = float(np.mean(bss)) if bss else None
            tgt = [t for t, x in SHORT.items() if x == s][0]
            mrows.append({"target": tgt, "target_short": s, "view": view, "model": "NC1T", "reference": "B0", "kind": "NEGATIVE_CONTROL",
                          "n_with_number": v[0]["n"] if v else 0, "positives": v[0]["positives"] if v else None,
                          "decision_days": v[0]["days"] if v else None, "nc1_seeds": len(v), "nc1_mean_bss": mean_bss,
                          "verdict": B.nc1_verdict(v[0]["n"] if v else 0, v[0]["positives"] if v else 0, v[0]["days"] if v else 0, mean_bss),
                          "status": T.PROVISIONAL, "revision_check_claimed": False})
    exp = out / "experiments"
    write_csv(exp / "TECHNICAL_METRICS.csv", mrows)
    write_csv(exp / "ABLATIONS.csv", abl)
    write_csv(exp / "HIT_MISS_COHORTS.csv", hm)
    write_csv(exp / "OOS_PREDICTIONS.csv", oos_out)
    write_csv(exp / "TECH_COVERAGE.csv", cov)
    write_csv(exp / "NC1T_SEEDS.csv", nc1_rows)
    feats = []
    for k, sn in sorted(tsnaps.items()):
        feats.append({"decision_key": k, "mint": sn["mint"], "decision_time_utc": B._iso(sn["decision_time"]),
                      "tech_status": T.row_status(sn) or "COMPLETE", "tech_snapshot_sha": sn["tech_snapshot_sha"],
                      **{c: sn["values"][c]["value"] if sn["values"][c]["value"] is not None else sn["values"][c]["missing_reason"]
                         for c in T.TECH}})
    write_csv(exp / "TECH_FEATURES_DEVELOPMENT.csv", feats)
    # cumulative search ledger: Phase 07's rows, then Phase 08's
    with open(P07 / "experiments/SEARCH_LEDGER.csv") as f:
        prior = list(csv.DictReader(f))
    for i, when in enumerate(DEBUG_RUNS, 1):
        ledger.append({"phase": "08", "experiment_id": f"P08:debug_run_{i}", "target": "all three", "candidate": "as recorded run",
                       "kind": "DEBUG_RUN_REAL_DATA", "view": "", "seed": "", "folds": "", "n_rows": "", "n_with_number": "",
                       "verdict": when, "split_fingerprint": ""})
    write_csv(exp / "SEARCH_LEDGER.csv", prior + ledger)
    reg = [r["experiment_id"] for r in csv.DictReader(open(REPO / "audits/predictive-intelligence/phase_08/experiments/EXPERIMENT_REGISTRY.csv"))]
    led = {r["experiment_id"] for r in ledger}
    reg_trap = {x for x in reg if x.split(":")[-1] in ("NC2T", "P06T", "P13T")}
    missing = sorted(set(reg) - led - reg_trap)
    ev_dir = out / "evidence"
    tr = traps(fs, dev_ex_by_target, tsnaps, cards_h)
    tr["registry_rows_missing_from_ledger"] = missing
    write_json(ev_dir / "traps.json", tr)
    write_json(ev_dir / "folds.json", folds_ev)
    write_json(ev_dir / "serialization_smoke.json", smoke)
    write_json(ev_dir / "phase07_equality.json", p07_equal)
    write_json(ev_dir / "v2_consistency.json", {"decisions_checked": len(tsnaps), "inconsistent": incons,
                                               "restated": sorted(T.V2_SAME), "derived": ["tech_log1p_candles_24h",
                                               "tech_log1p_last_close_age_min", "tech_log_rel_vol_1h"]})
    ua = {"decisions": len(unavailable), "with_point_in_time_pool": sum(1 for u in unavailable if u["pool_set"]),
          "candles_started_before_T_not_available_total": sum(u["candles_started_before_T_not_available"] for u in unavailable),
          "of_which_holding_or_ending_after_T": sum(u["of_which_holding_or_ending_after_T"] for u in unavailable),
          "of_which_closed_but_inside_provider_lag": sum(u["of_which_closed_but_inside_provider_lag"] for u in unavailable),
          "inputs_used_after_T": sum(u["inputs_used_after_T"] for u in unavailable),
          "store_candles_with_end_after_availability": fs.execute("SELECT COUNT(*) FROM predictive_candles WHERE vanished=0 AND end_at > available_at").fetchone()[0],
          "per_decision": unavailable}
    write_json(ev_dir / "unavailable_candles.json", ua)
    tdir = ev_dir / "trace"
    tj = trace(fs, res_by_target, tsnaps, cards_h, info)
    write_json(tdir / "FORECAST_TRACE.json", tj)
    if a.npz:
        np.savez(a.npz, **npz)
    store_sha_after = {p: P7.fsha(p) for p in (a.dev_store, a.feature_store)}
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    outputs = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file() and p.name != "run_log.json")
    write_json(ev_dir / "run_log.json", {
        "start_utc": start_utc, "end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "head": head,
        "wall_s": round(time.time() - t0, 2), "cpu_s": round(time.process_time() - c0, 2),
        "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "socket_events": SOCKET_EVENTS, "vendor_calls": 0, "bootstrap_reps": a.reps,
        "code_sha256": {c: P7.fsha(REPO / c) for c in CODE},
        "stores": {"before": store_sha_before, "after": store_sha_after, "unchanged": store_sha_before == store_sha_after},
        "registry_sha": C.registry_sha256(), "tech_feature_set_sha": T.feature_set_sha(), "base_feature_set_sha": F.feature_set_sha(),
        "labels_version": L.LABELS_VERSION, "as_of_utc": B._iso(H), "status": T.PROVISIONAL, "revision_check_claimed": False,
        "debug_runs_logged": len(DEBUG_RUNS), "outputs_sha256": {o: P7.fsha(out / o) for o in outputs}})
    print(json.dumps({"targets": {s: folds_ev[s]["status"] for s in folds_ev}, "outputs": len(outputs), "socket_events": len(SOCKET_EVENTS),
                      "stores_unchanged": store_sha_before == store_sha_after, "ledger_missing": len(missing)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
