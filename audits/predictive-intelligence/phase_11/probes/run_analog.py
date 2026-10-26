"""Phase 11 analog cohort and regime runner: the as-of regime label of every Solana development export instant (with the CX-11
full-sample comparison and the truncation check at every instant), analog-1 inputs for every Solana development decision, the
frozen walk-forward of AC1, AC2, AC3 (primary), AC3_LOCO and NC1-AC beside Phase 07's B0 and B2 on the same folds, the
comparisons (B0, B2, regime handling, the frozen primaries of Phases 08 to 10), the regime breakdown (P21), coverage and missing
data, the divergence flags (phase prompt step 5), the train-only cards at the holdout start, the traps (NC2-AC, P43-AC, P13-AC,
P36-AC, P14-AC, CX-11, future-issued tokens, survivorship), the forecast trace, the oracle arrays and the cumulative search ledger.

Reads only: the Phase 06 development store (labels through `labels.training_labels`; a SELECT without the label column for the
censoring counts), the Phase 05 store (version 2 snapshots through `features.training_view`, decision rows, onchain-1 through
`onchain.onchain_as_of`), git objects of `MAIN_REF` (the newest export, for the survivorship count only, never a cohort input)
and the committed Phase 07 to 10 out-of-sample files. Never opens the sealed holdout folder. No network: an audit hook refuses
any socket call. Deterministic: two runs into two folders give identical files except `evidence/run_log.json` (times).

    python -B run_analog.py OUTDIR [--reps 2000] [--dev-store PATH] [--feature-store PATH] [--npz PATH]
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import resource
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from memelab.predictive import analog as A  # noqa: E402
from memelab.predictive import baselines as B  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import onchain as O  # noqa: E402
from memelab.predictive import runtime as R  # noqa: E402
from memelab.predictive import stats as K  # noqa: E402

SOCKET_EVENTS: list[str] = []


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKET_EVENTS.append(event)
        raise RuntimeError(f"Phase 11 runner makes no network call ({event})")


sys.addaudithook(_hook)

_spec = importlib.util.spec_from_file_location("p07_run_baselines", REPO / "audits/predictive-intelligence/phase_07/probes/run_baselines.py")
P7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P7)

SHORT, H = P7.SHORT, P7.H
CODE = ["memelab/predictive/analog.py", "memelab/predictive/baselines.py", "memelab/predictive/stats.py",
        "memelab/predictive/features.py", "memelab/predictive/labels.py", "memelab/predictive/contract.py",
        "memelab/predictive/onchain.py", "memelab/social/replay_core.py",
        "audits/predictive-intelligence/phase_07/probes/run_baselines.py", "audits/predictive-intelligence/phase_11/probes/run_analog.py"]
P07 = REPO / "audits/predictive-intelligence/phase_07"
P10 = REPO / "audits/predictive-intelligence/phase_10"
P07_SPLITS = {"T1_24h": "0ab64525e04b8664a1cab51c9e24f5fa4f750681d32a5d97bfc520710e3845a4",
              "T1b_6h": "aa16e7adeae7d5bc8567de9ab85ed1f28843afe51bc0de9b52e24d587beb8a31",
              "T2_24h": "82a1c33b12cef45995eb15edd07b8e27ddcd76eafbdb8c503f5feb9501be86cd"}
TARGET_ORDER = (L.T1, L.T2, L.T1B)
MAIN_REF = "e245d91cc5f56060ba8e1aa7182c846c77d1526c"   # the origin/main commit Phase 10 pinned; survivorship count only
EXPORT_PATH = "data/state/latest.json"
VIEWS = ("ALL", "NEW_MINTS", "NO_PRIOR_DECISION", "NO_KEY_CONFLICT")
MODELS = A.MODEL_IDS + (A.LOCO,)
CROSS = {"P08_M2_T_LOGIT_B2": ("phase_08", "M2_T_LOGIT_B2"), "P09_M2_OC_LOGIT_B2": ("phase_09", "M2_OC_LOGIT_B2"),
         "P10_S2_SC_LOGIT_B2": ("phase_10", "S2_SC_LOGIT_B2")}
COMPARISONS = ([(m, "B0") for m in ("B2",) + A.MODEL_IDS]
               + [(m, "B2") for m in ("AC2_KNN", "AC3_KNN_REGIME")]
               + [("AC3_KNN_REGIME", "AC2_KNN")]
               + [("AC3_KNN_REGIME", c) for c in CROSS])
KIND = {"B2": "REFERENCE_PHASE07", "AC1_STRATA": "ANALOG_COHORT", "AC2_KNN": "ANALOG_COHORT",
        "AC3_KNN_REGIME": "ANALOG_COHORT_PRIMARY", A.LOCO: "SENSITIVITY_LEAVE_ONE_CAMPAIGN_OUT"}
# real-data runs before the recorded run (P22): appended before the recorded run, never removed
DEBUG_RUNS: list[str] = [
    "unlabelled looks before the pre-registration (2026-10-26 15:00Z to 15:03Z, ad hoc scripts in the session scratchpad, not kept): "
    "decision counts, median 24 h volume and constructive share per export instant over the 830 Solana development decisions, "
    "regime labels past-only and full-sample (count-based 20 flips, volume-based 32), launchpads, token programs and creators; "
    "no label read; the volume-based activity was chosen after seeing them (repair pass 2, skeptic m6)",
    "features-only probe after the pre-registration commit 46afc85 (15:14:33Z to 15:14:37Z on 2026-10-26): regime series, CX-11 "
    "flip count (32) and analog-1 inputs (launchpad class, token program, regime per decision) over the 830 Solana development "
    "decisions of the Phase 05 store; no label read, no cohort, no metric",
    "recorded run 1 at 0482a60 (15:20:26Z to 15:21:09Z) and its determinism twin (15:21:30Z to 15:22:15Z): every output equal to "
    "the run at the ledger-repair commit except SEARCH_LEDGER.csv, which lacked the B0 and AC3_LOCO rows (found by the committed-"
    "outputs test); superseded by the run at the ledger-repair commit",
    "recorded run at ff98b8d (15:26:22Z to 15:27:03Z) and its twin: the first-pass outputs committed in 208cdc1, superseded by the "
    "run at the repair-pass-2 commit (CX-S11 groups, ICC N, new_mint, claim column; PI-D-063)",
]
STATUS = A.STATUS


def write_csv(path: Path, rows: list[dict]) -> None:
    P7.write_csv(path, rows)


def write_json(path: Path, obj) -> None:
    P7.write_json(path, obj)


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *a], check=True, capture_output=True, text=True).stdout


def fnum(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else float("nan")


# ---------------------------------------------------------------- inputs
def decision_rows(fs) -> dict[str, dict]:
    out = {}
    for r in fs.execute("SELECT decision_key, chain, mint, decision_time, status, token_json, token_first_seen_at, pool_address "
                        "FROM predictive_decisions WHERE chain='solana' AND decision_key IS NOT NULL AND decision_time < ? "
                        "ORDER BY decision_time, id", (H,)):
        d = dict(r)
        d["token"] = json.loads(r["token_json"]) if r["token_json"] else {}
        out[r["decision_key"]] = d
    return out


def regime_rows(decs: dict, frows: dict) -> list[A.RegimeRow]:
    rows = []
    for k, d in decs.items():
        f = frows.get(k)
        if f is None:
            raise SystemExit(f"no version 2 snapshot for decision {k[:12]}")
        lv = fnum(f.get("thesis_log1p_vol_24h_usd"))
        av = f.get("thesis_log1p_vol_24h_usd__available_at")
        rows.append(A.RegimeRow(decision_time=float(d["decision_time"]), status=d["status"], log_vol=lv,
                                available_at=float(av) if av is not None else None))
    return rows


def extras_of(fs, decs: dict, frows: dict, series: dict) -> dict[str, dict]:
    out = {}
    for k, d in decs.items():
        T = float(d["decision_time"])
        oc = O.onchain_as_of(fs, d["chain"], d["mint"], T, decision_key=k)["values"]
        t22 = oc["oc_token2022"]
        fee = oc["oc_transfer_fee_pct"]["value"]
        out[k] = {"chain": d["chain"], "mint": d["mint"], "decision_time": T,
                  "launchpad_class": A.launchpad_class(d["token"]), "token2022": t22["value"],
                  "token2022_available_at": t22["available_at"], "regime": series[T]["label"],
                  "first_seen_at": d["token_first_seen_at"], "hist_prior": fnum(frows[k].get("hist_prior_decisions")),
                  "pool_address": d["pool_address"],
                  "oc": {"oc_mint_authority_active": oc["oc_mint_authority_active"]["value"],
                         "oc_freeze_authority_active": oc["oc_freeze_authority_active"]["value"],
                         "oc_transfer_fee_present": (None if fee is None else float(fee > 0)),
                         "oc_token2022": t22["value"], "oc_exit_cap_share": oc["oc_exit_cap_share"]["value"],
                         "oc_round_trip_friction_pct": oc["oc_round_trip_friction_pct"]["value"]}}
        for kk, v in list(out[k]["oc"].items()):
            out[k]["oc"][kk] = float("nan") if v is None else float(v)
    return out


def aex_at(dev, target, as_of, frows, snaps, info, extras, *, include_kc=True):
    ex, rows = P7.examples_at(dev, target, as_of, frows, snaps, info, include_kc=include_kc)
    return A.attach(ex, extras), rows


def censored_counts(dev, target, as_of) -> dict:
    """Missing data of a pool: development decisions of the target matured by as_of that are censored or not labelled. Reads
    the state and censoring columns only, never the label column."""
    c = Counter()
    for r in dev.execute("SELECT decision_key, state, censored, decision_time, label_matures_at, split FROM predictive_labels "
                         "WHERE target=? AND split='DEVELOPMENT' AND label_matures_at <= ? AND revision_of IS NULL", (target, as_of)):
        c["censored" if r["censored"] else str(r["state"])] += 1
    return dict(sorted(c.items()))


# ---------------------------------------------------------------- views, metrics
def view_rows(oos, view):
    if view in ("ALL", "NO_KEY_CONFLICT"):
        return list(oos)
    if view == "NEW_MINTS":
        return [r for r in oos if r["new_mint"]]
    if view == "NO_PRIOR_DECISION":
        return [r for r in oos if r["no_prior_decision"]]
    raise ValueError(view)


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
            "cal_mean_pred": cal.get("mean_pred"), "cal_observed": cal.get("observed"), "ece": cal.get("ece"),
            "degenerate": extra.get("degenerate"), "verdict": ev.get("verdict"),
            "claim": ("none: below the frozen minimums; the skill and interval columns are descriptive only"
                      if (ev.get("verdict") or "").startswith("INSUFFICIENT") else "see verdict"),
            "promotion": "MODEL_NOT_PROMOTED",
            "status": STATUS, "revision_check_claimed": True,
            **{k: v for k, v in extra.items() if k not in ("p_holm", "degenerate")}}


def cross_columns(oos_by_target: dict) -> dict:
    """The frozen primaries of Phases 08 to 10 on the same out-of-sample rows (committed files, 6 decimals); y and B0 must agree."""
    out = {"rows_joined": 0, "y_disagree": 0, "b0_disagree": 0, "missing": 0}
    for name, (ph, col) in CROSS.items():
        rows = list(csv.DictReader(open(REPO / "audits/predictive-intelligence" / ph / "experiments/OOS_PREDICTIONS.csv")))
        idx = {(r["target_short"], r["decision_key"]): r for r in rows}
        for s, oos in oos_by_target.items():
            for r in oos:
                c = idx.get((s, r["example"].decision_key))
                if c is None:
                    out["missing"] += 1
                    r[name], r[name + "_why"] = float("nan"), "NOT_IN_PHASE_FILE"
                    continue
                out["rows_joined"] += 1
                if int(c["y"]) != r["y"]:
                    out["y_disagree"] += 1
                if abs(float(c["B0"]) - float(f"{r['B0']:.6f}")) > 1e-9:
                    out["b0_disagree"] += 1
                v = c[col]
                r[name] = float(v) if v not in ("", None) else float("nan")
                r[name + "_why"] = c.get(col + "_why") or None
    return out


# ---------------------------------------------------------------- traps on the real history
def traps(dev, frows, snaps, info, extras, decs, series, rrows, res_by_target, cards_h) -> dict:
    out = {}
    # NC2-AC: rows decided before a fold cutoff whose labels mature after it; P43-AC: rows decided after it
    nc2, p43, ft = Counter(), Counter(), Counter()
    for target in L.TARGETS:
        res = res_by_target[target]
        if not res["folds"]:
            continue
        cut = res["folds"][0]["cutoff"]
        pool = aex_at(dev, target, cut, frows, snaps, info, extras)[0]
        later = aex_at(dev, target, H, frows, snaps, info, extras)[0]
        for e in later:
            if e.decision_time < cut and e.label_matures_at > cut:
                try:
                    A.check_pool(pool + [e], cut)
                    nc2["accepted"] += 1
                except A.FutureUniverseError:
                    nc2["refused"] += 1
            elif e.decision_time >= cut:
                try:
                    A.check_pool(pool + [e], cut)
                    p43["accepted"] += 1
                except A.FutureUniverseError:
                    p43["refused"] += 1
        # future-issued tokens: mints whose first development decision is after the cutoff never enter the pool
        first = {}
        for d in decs.values():
            first[d["mint"]] = min(first.get(d["mint"], math.inf), float(d["decision_time"]))
        pool_mints = {e.mint for e in pool}
        for m, t in first.items():
            if t >= cut:
                ft["in_pool" if m in pool_mints else "excluded"] += 1
        fs_max = max((e.first_seen_at or 0.0) for e in pool) if pool else None
        ft[f"{SHORT[target]}_max_first_seen_le_cutoff"] = int(fs_max is None or fs_max <= cut)
    out["NC2_AC"] = {"description": "real rows decided before the first fold cutoff with labels maturing after it, added to the pool",
                     **dict(nc2), "pass": nc2["accepted"] == 0 and nc2["refused"] > 0}
    out["P43_AC"] = {"description": "real rows decided at or after the first fold cutoff, added to the pool", **dict(p43),
                     "pass": p43["accepted"] == 0 and p43["refused"] > 0}
    out["FUTURE_ISSUED_TOKENS"] = {"description": "development mints first decided at or after each target's first cutoff",
                                   **dict(ft), "pass": ft["in_pool"] == 0}
    # P13-AC: a holdout-start card on development decisions
    p13 = Counter()
    for target in L.TARGETS:
        dev_ex = aex_at(dev, target, H, frows, snaps, info, extras)[0]
        for m in A.MODEL_IDS:
            try:
                A.predict(cards_h[target][m], dev_ex[:5])
                p13["accepted"] += 1
            except A.ModelTrainedAfterDecision:
                p13["refused"] += 1
    out["P13_AC"] = {**dict(p13), "pass": p13["accepted"] == 0}
    # P36-AC: a target input available after its decision
    p36 = Counter()
    for target in L.TARGETS:
        res = res_by_target[target]
        for r in res["oos"][:10]:
            e = r["example"]
            bad = A.AExample(**{**e.__dict__, "avail": {**e.avail, B.LIQ: e.decision_time + 300.0}})
            try:
                A.check_target(bad, r["cutoff"])
                p36["accepted"] += 1
            except F.AsOfError:
                p36["refused"] += 1
    out["P36_AC"] = {**dict(p36), "pass": p36["accepted"] == 0 and p36["refused"] > 0}
    # P14-AC: same-creator rows excluded from real cohorts (counts from the answers)
    p14 = Counter()
    for target in L.TARGETS:
        for r in res_by_target[target]["oos"]:
            for m in ("AC2_KNN", "AC3_KNN_REGIME"):
                ex = r["answers"][m].get("excluded") or {}
                p14[f"{m}_same_creator_rows"] += ex.get("same_creator", 0)
                p14[f"{m}_answers_with_same_creator_rows"] += int(ex.get("same_creator", 0) > 0)
                ms = [a["mint"] for a in r["answers"][m]["analogs"]]
                p14["answers_with_a_mint_twice"] += int(len(ms) != len(set(ms)))
                if r["example"].creator and r["example"].creator in {decs[a["decision_key"]]["token"].get("creator") for a in r["answers"][m]["analogs"]}:
                    p14["same_creator_analog_selected"] += 1
    cr: dict = {}
    for d in decs.values():
        cr.setdefault(d["mint"], set()).add(d["token"].get("creator") or None)
    p14["development_mints_with_several_creator_values"] = sum(1 for v in cr.values() if len(v) > 1)
    out["P14_AC"] = {**dict(p14), "pass": p14["same_creator_analog_selected"] == 0 and p14["answers_with_a_mint_twice"] == 0}
    # CX-11: full-sample regime medians against the as-of labels, and truncation invariance at every instant
    inst = sorted(series)
    flips = [T for T in inst if series[T]["label"] not in (A.WARMUP, A.UNKNOWN) and A.regime_full_sample(rrows, T)["label"] != series[T]["label"]]
    non_inv = [T for T in inst if A.regime_as_of(A.visible_at(rrows, T), T) != series[T]]
    trap_leaks = [T for T in inst if not A.truncation_invariant(A.regime_full_sample, rrows, T)]
    out["CX11"] = {"instants": len(inst), "non_warmup_instants": sum(1 for T in inst if series[T]["label"] not in (A.WARMUP, A.UNKNOWN)),
                   "full_sample_label_differs": len(flips), "as_of_series_not_equal_to_truncated_recomputation": len(non_inv),
                   "full_sample_variant_not_truncation_invariant_at": len(trap_leaks),
                   "pass": len(non_inv) == 0 and len(flips) > 0 and len(trap_leaks) > 0}
    return out


def survivorship(res_by_target) -> dict:
    """P09 on the real history: analog mints absent from the newest export at MAIN_REF (dead, delisted or dropped) are still in
    the cohorts, because nothing reads a current list. The export is read here for this count only."""
    raw = subprocess.run(["git", "-C", str(REPO), "show", f"{MAIN_REF}:{EXPORT_PATH}"], check=True, capture_output=True).stdout
    d = json.loads(raw)
    t = d.get("_tables") or {k: v for k, v in d.items() if not k.startswith("_") and isinstance(v, list)}
    newest = {r.get("mint") for r in (t.get("tokens") or [])}
    c = Counter()
    for target, res in res_by_target.items():
        for r in res["oos"]:
            for a in r["answers"]["AC2_KNN"]["analogs"]:
                c["analog_rows"] += 1
                c["analog_rows_mint_absent_from_newest_export"] += int(a["mint"] not in newest)
    return {"main_ref": MAIN_REF, "newest_export_tokens": len(newest), **dict(c)}


# ---------------------------------------------------------------- oracle arrays
def oracle_arrays(npz: dict, tag: str, e: A.AExample, pool: list, ans: dict, model: str) -> None:
    if ans.get("reasons") and not ans.get("analogs"):
        return
    ref = [r for r in pool if A.complete(r)]
    if model == "AC3_KNN_REGIME":
        ref = [r for r in ref if r.regime == e.regime]
    if not ref or not ans.get("analogs"):
        return
    keep, _ = A._excluded(e, pool, loco=False)
    keep = {r.decision_key for r in keep}
    npz[tag + "_Xn"] = np.array([[r.x[c] for c in A.NUMERIC] for r in ref], float)
    npz[tag + "_Xc"] = np.array([[r.x[c] for c in A.CATEGORICAL] for r in ref], float)
    npz[tag + "_qn"] = np.array([e.x[c] for c in A.NUMERIC], float)
    npz[tag + "_qc"] = np.array([e.x[c] for c in A.CATEGORICAL], float)
    names = sorted({r.cluster for r in ref})
    npz[tag + "_cid"] = np.array([names.index(r.cluster) for r in ref], int)
    npz[tag + "_keyrank"] = np.argsort(np.argsort(np.array([r.decision_key for r in ref])))
    npz[tag + "_allowed"] = np.array([r.decision_key in keep for r in ref], bool)
    pos = {r.decision_key: i for i, r in enumerate(ref)}
    npz[tag + "_sel"] = np.array([pos[a["decision_key"]] for a in ans["analogs"]], int)
    npz[tag + "_seld"] = np.array([a["distance"] for a in ans["analogs"]], float)
    npz[tag + "_thr"] = np.array([ans["ood_threshold"]], float)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--reps", type=int, default=C.ACCEPTANCE["bootstrap"]["min_replicates"])
    ap.add_argument("--dev-store", default=P7.DEV_STORE)
    ap.add_argument("--feature-store", default=P7.FEATURE_STORE)
    ap.add_argument("--npz", default=None, help="write the neighbour designs for the scikit-learn NearestNeighbors oracle")
    a = ap.parse_args()
    out = Path(a.out)
    t0, c0 = time.time(), time.process_time()
    start_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
    for p in (a.dev_store, a.feature_store):
        L.refuse_sealed(p)
        R.refuse_bakeoff_labels(path=p)
    lab_db = REPO / "data" / "memelab.sqlite"
    stores = [a.dev_store, a.feature_store, str(lab_db)]
    sha_before = {p: P7.fsha(p) for p in stores}
    dev, fs = P7.ro(a.dev_store), P7.ro(a.feature_store)
    frows, snaps, info = P7.load_inputs(dev, fs)
    decs = decision_rows(fs)
    rrows = regime_rows(decs, frows)
    series = A.regime_series(rrows)
    extras = extras_of(fs, decs, frows, series)

    exp, ev_dir, art = out / "experiments", out / "evidence", out / "artifacts"
    res_by_target, runs_by_target, folds_ev, label_set = {}, {}, {}, {}
    p07 = {(r["target_short"], r["decision_key"]): r for r in csv.DictReader(open(P07 / "experiments/OOS_PREDICTIONS.csv"))}
    phase07_eq = {"rows": 0, "b0_diff": 0, "b2_diff": 0, "split_equal": {}}
    for target in TARGET_ORDER:
        s = SHORT[target]
        runs = {}
        for kc in (True, False):
            dev_ex, dev_rows = aex_at(dev, target, H, frows, snaps, info, extras, include_kc=kc)
            res = A.walk_forward(target, dev_ex, lambda c, kc=kc: aex_at(dev, target, c, frows, snaps, info, extras, include_kc=kc)[0])
            runs[kc] = (dev_ex, res)
            if kc:
                label_set[s] = {"n": len(dev_rows), "positives": int(sum(r["label"] for r in dev_rows)),
                                "label_set_sha": B.sha(sorted([r["label_key"], r["label"]] for r in dev_rows))}
        runs_by_target[target] = runs
        dev_ex, res = runs[True]
        res_by_target[target] = res
        phase07_eq["split_equal"][s] = res.get("split_fingerprint") == P07_SPLITS[s]
        for r in res["oos"]:
            q = p07.get((s, r["example"].decision_key))
            phase07_eq["rows"] += 1
            if q is None or f"{r['B0']:.6f}" != q["B0"]:
                phase07_eq["b0_diff"] += 1
            if q is None or (f"{r['B2']:.6f}" if math.isfinite(r["B2"]) else "") != q["B2"]:
                phase07_eq["b2_diff"] += 1
        folds_ev[s] = {"status": res["status"], "split_fingerprint": res.get("split_fingerprint"), "audit": res["audit"],
                       "folds": [{k: v for k, v in f.items() if k != "cards"} for f in res["folds"]],
                       "no_key_conflict_folds": [{k: v for k, v in f.items() if k != "cards"} for f in runs[False][1]["folds"]],
                       "development_days": sorted({e.day for e in dev_ex}), "development_n": len(dev_ex),
                       "development_positives": int(sum(e.y for e in dev_ex)),
                       "pool_missing_data": [{"cutoff_utc": f["cutoff_utc"], **censored_counts(dev, target, f["cutoff"])} for f in res["folds"]]}
        # fold cards: one pool per fold, card headers per model (model_sha verifiable by re-inserting the pool)
        fold_doc = {"target": target, "status": STATUS, "folds": []}
        for f in res["folds"]:
            pool_rows = f["cards"]["AC2_KNN"]["body"]["pool"]
            heads = {}
            for m in ("B0", "B2") + A.MODEL_IDS:
                c = f["cards"][m]
                if m in A.MODEL_IDS:
                    assert c["body"]["pool"] == pool_rows
                    heads[m] = {**{k: v for k, v in c.items() if k != "body"},
                                "body": {k: v for k, v in c["body"].items() if k != "pool"}, "pool_sha": B.sha(pool_rows)}
                else:
                    heads[m] = c
            fold_doc["folds"].append({"fold": f["fold"], "cutoff_utc": f["cutoff_utc"], "cutoff": f["cutoff"], "pool": pool_rows,
                                      "cards": heads})
        p = art / "folds" / f"{s}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(fold_doc, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")

    cross = cross_columns({SHORT[t]: res_by_target[t]["oos"] for t in TARGET_ORDER})
    for t in TARGET_ORDER:
        cross_columns({SHORT[t]: runs_by_target[t][False][1]["oos"]})

    # ------------------------------------------------------------ metrics
    metrics, holm_in, nc1_rows, ledger, regime_rows_out, loco_rows, cov_rows, div_rows, oos_out = [], {}, [], [], [], [], [], [], []
    for target in TARGET_ORDER:
        s = SHORT[target]
        runs = runs_by_target[target]
        res = runs[True][1]
        for view in VIEWS:
            rows = view_rows(runs[view != "NO_KEY_CONFLICT"][1]["oos"], view)
            for m, ref in COMPARISONS:
                if not rows:
                    ev = {"baseline": m, "n_rows": 0, "n_with_number": 0, "verdict": "INSUFFICIENT_HISTORY"}
                else:
                    ev = B.evaluate(rows, m, reference=ref, reps=a.reps)
                deg = A.degenerate([r[m] for r in rows]) if rows else False
                metrics.append((target, view, m, ref, ev, deg))
                if view == "ALL":
                    holm_in.setdefault((m, ref), {})[target] = ev.get("p_one_sided")
                ledger.append({"phase": "11", "experiment_id": f"P11:{target}:{m}", "target": target, "candidate": m,
                               "kind": KIND.get(m, "ANALOG_COHORT"), "view": f"{view} vs {ref}", "seed": 20261025,
                               "folds": len(res["folds"]), "n_rows": ev["n_rows"], "n_with_number": ev["n_with_number"],
                               "verdict": ev.get("verdict"), "split_fingerprint": runs[view != "NO_KEY_CONFLICT"][1].get("split_fingerprint")})
            # the reference B0 and the leave-one-campaign-out sensitivity are configurations too (ledger only, no claim)
            for m, kind, verdict in (("B0", "REFERENCE_PHASE07", "REFERENCE"), (A.LOCO, KIND[A.LOCO], "SENSITIVITY_NO_CLAIM")):
                ledger.append({"phase": "11", "experiment_id": f"P11:{target}:{m}", "target": target, "candidate": m, "kind": kind,
                               "view": view, "seed": 20261025, "folds": len(res["folds"]), "n_rows": len(rows),
                               "n_with_number": sum(1 for r in rows if math.isfinite(r[m])), "verdict": verdict,
                               "split_fingerprint": runs[view != "NO_KEY_CONFLICT"][1].get("split_fingerprint")})
            # NC1-AC
            seeds = res.get("nc1_seeds", [])
            nrows = [r for r in rows if any(math.isfinite(r[f"NC1AC_{q}"]) for q in seeds)]
            nk, nd = int(sum(r["y"] for r in nrows)), len({r["example"].day for r in nrows})
            for q in seeds:
                key = f"NC1AC_{q}"
                use = [r for r in rows if math.isfinite(r[key])]
                if use:
                    e2 = B.evaluate(rows, key, reps=a.reps, seed=20261025 + q, boot=False)
                    nc1_rows.append({"target_short": s, "view": view, "seed": q, "n": e2["n_with_number"], "brier": e2.get("brier"),
                                     "brier_ref": e2.get("brier_ref"), "bss": e2.get("bss"), "positives": nk, "days": nd})
                else:
                    nc1_rows.append({"target_short": s, "view": view, "seed": q, "n": 0, "positives": nk, "days": nd})
                ledger.append({"phase": "11", "experiment_id": f"P11:{target}:NC1AC_seed{q:02d}", "target": target, "candidate": "NC1AC",
                               "kind": "NEGATIVE_CONTROL", "view": view, "seed": q, "folds": len(res["folds"]), "n_rows": len(rows),
                               "n_with_number": len(use), "verdict": "", "split_fingerprint": res.get("split_fingerprint")})
        # regime breakdown (P21)
        for reg in sorted({r["regime"] or "NONE" for r in res["oos"]}):
            rows = [r for r in res["oos"] if (r["regime"] or "NONE") == reg]
            for m in ("B2", "AC2_KNN", "AC3_KNN_REGIME"):
                ev = B.evaluate(rows, m, reference="B0", reps=a.reps)
                regime_rows_out.append({"target_short": s, "regime": reg, "model": m, "reference": "B0", "n_rows": len(rows),
                                        "n_with_number": ev["n_with_number"], "positives": ev.get("positives"),
                                        "decision_days": ev.get("days"), "brier": ev.get("brier"), "brier_ref": ev.get("brier_ref"),
                                        "bss_vs_ref": ev.get("bss"), "verdict": ev.get("verdict"),
                                        "claim": "none (P21: below the frozen minimums)" if (ev.get("verdict") or "").startswith("INSUFFICIENT") else "see verdict",
                                        "status": STATUS})
        # leave one campaign out (descriptive)
        both = [r for r in res["oos"] if math.isfinite(r["AC3_KNN_REGIME"]) and math.isfinite(r[A.LOCO])]
        changed = sum(1 for r in res["oos"] if (math.isfinite(r["AC3_KNN_REGIME"]), round(r["AC3_KNN_REGIME"], 9) if math.isfinite(r["AC3_KNN_REGIME"]) else None)
                      != (math.isfinite(r[A.LOCO]), round(r[A.LOCO], 9) if math.isfinite(r[A.LOCO]) else None))
        loco_rows.append({"target_short": s, "oos_rows": len(res["oos"]), "answers_changed": changed, "common_rows": len(both),
                          "brier_ac3": K.brier([r["y"] for r in both], [r["AC3_KNN_REGIME"] for r in both]) if both else None,
                          "brier_ac3_loco": K.brier([r["y"] for r in both], [r[A.LOCO] for r in both]) if both else None,
                          "same_campaign_rows_excluded": sum(r["answers"][A.LOCO].get("excluded", {}).get("same_campaign", 0) for r in res["oos"]),
                          "oos_rows_with_narrative_tag": sum(1 for r in res["oos"] if r["example"].narrative),
                          "claim": "descriptive sensitivity only", "status": STATUS})
        # coverage and missing data
        for m in MODELS:
            ans = [r["answers"][m] for r in res["oos"]]
            nums = [x for x in ans if x.get("number") is not None]
            reasons = Counter(rr for x in ans for rr in (x.get("reasons") or []))
            Gs = [x.get("G") for x in ans if x.get("G")]
            cov_rows.append({"target_short": s, "model": m, "oos_rows": len(ans), "with_number": len(nums),
                             "abstain": len(ans) - len(nums),
                             "states": ";".join(f"{k}={v}" for k, v in sorted(Counter(A.state_of(x.get("reasons") or []) or "NUMBER" for x in ans).items())),
                             "reasons": ";".join(f"{k}={v}" for k, v in sorted(reasons.items())),
                             "median_G": float(np.median(Gs)) if Gs else None, "min_G": min(Gs) if Gs else None,
                             "median_analog_days": float(np.median([x["analog_days"] for x in ans if x.get("G")])) if Gs else None,
                             "median_day_kish_ess": float(np.median([x["day_kish_ess"] for x in ans if x.get("G")])) if Gs else None,
                             "median_n_eff_icc_numbers": float(np.median([x["n_eff_icc"] for x in nums])) if nums else None,
                             "min_n_eff_icc_numbers": min((x["n_eff_icc"] for x in nums), default=None),
                             "numbers_with_n_eff_icc_below_20": sum(1 for x in nums if x["n_eff_icc"] < A.MIN_G),
                             "answers_with_a_mint_twice": sum(1 for x in ans if x.get("G") and x["G"] != x["analog_mints"]),
                             "pool_n": ";".join(sorted({str(x.get("pool_n")) for x in ans})),
                             "new_mint_rows": sum(1 for r in res["oos"] if r["new_mint"]),
                             "no_prior_decision_rows": sum(1 for r in res["oos"] if r["no_prior_decision"]),
                             "time_unstable": sum(1 for x in nums if "TIME_UNSTABLE" in x.get("flags", [])), "status": STATUS})
        # divergence flags and out-of-sample predictions
        for r in res["oos"]:
            e = r["example"]
            cut = r["cutoff"]
            pool = None
            row = {"target_short": s, "fold": r["fold"], "cutoff_utc": B._iso(cut), "decision_key": e.decision_key, "mint": e.mint,
                   "decision_time_utc": B._iso(e.decision_time), "day": e.day, "y": e.y, "route": e.route, "regime": r["regime"],
                   "launchpad": e.launchpad, "new_mint": r["new_mint"], "no_prior_decision": r["no_prior_decision"],
                   "key_conflict": e.key_conflict, "B0": r["B0"], "B2": r["B2"]}
            for m in MODELS:
                x = r["answers"][m]
                row[m] = r[m]
                row[m + "_why"] = ";".join(x.get("reasons") or [])
                row[m + "_G"] = x.get("G")
                row[m + "_analog_mints"] = x.get("analog_mints")
                row[m + "_pool_day_icc"] = x.get("pool_day_icc")
                row[m + "_n_eff_icc"] = x.get("n_eff_icc")
                wi = x.get("wilson_icc") or [None, None]
                row[m + "_wilson_icc_lo"], row[m + "_wilson_icc_hi"] = wi[0], wi[1]
                row[m + "_days"] = x.get("analog_days")
                row[m + "_raw_rate"] = x.get("raw_rate")
                w = x.get("wilson") or [None, None]
                row[m + "_wilson_lo"], row[m + "_wilson_hi"] = w[0], w[1]
            for name in CROSS:
                row[name] = r.get(name)
            row["NC1AC_mean"] = float(np.nanmean([r[f"NC1AC_{q}"] for q in res["nc1_seeds"]])) if any(
                math.isfinite(r[f"NC1AC_{q}"]) for q in res["nc1_seeds"]) else float("nan")
            row["status"] = STATUS
            oos_out.append(row)
            for m in ("AC2_KNN", "AC3_KNN_REGIME"):
                x = r["answers"][m]
                if not x.get("analogs"):
                    continue
                if pool is None:
                    pool = {p.decision_key: p for p in aex_at(dev, target, cut, frows, snaps, info, extras)[0]}
                fl = A.divergence_flags(e, [pool[q["decision_key"]] for q in x["analogs"]])
                div_rows.append({"target_short": s, "decision_key": e.decision_key, "mint": e.mint, "model": m,
                                 "has_number": x.get("number") is not None, "G": x["G"], "flags": ";".join(fl),
                                 "n_flags": len(fl), "status": STATUS})
    holm_adj = {}
    for (m, ref), per_t in holm_in.items():
        ts = list(L.TARGETS)
        adj = K.holm([per_t.get(t) if per_t.get(t) is not None else float("nan") for t in ts])
        for t, v in zip(ts, adj):
            holm_adj[(t, m, ref)] = v
    mrows = []
    for target, view, m, ref, ev, deg in metrics:
        ph = holm_adj.get((target, m, ref)) if view == "ALL" else None
        if ev.get("n_with_number"):
            ev["verdict"] = B.verdict(ev, ph if ph is not None and math.isfinite(ph) else None)
        mrows.append(metric_row(target, view, ev, model=m, reference=ref, kind=KIND.get(m, "CROSS_PHASE"), extra={
            "p_holm": ph, "degenerate": deg, "split_fingerprint": res_by_target[target].get("split_fingerprint"),
            "label_set_sha": label_set[SHORT[target]]["label_set_sha"]}))
    for s in SHORT.values():
        for view in VIEWS:
            v = [r for r in nc1_rows if r["target_short"] == s and r["view"] == view and r.get("n")]
            bss = [r["bss"] for r in v if r.get("bss") is not None and math.isfinite(r["bss"])]
            mean_bss = float(np.mean(bss)) if bss else None
            mrows.append({"target": [t for t, x in SHORT.items() if x == s][0], "target_short": s, "view": view, "model": "NC1AC",
                          "reference": "B0", "kind": "NEGATIVE_CONTROL", "n_with_number": v[0]["n"] if v else 0,
                          "positives": v[0]["positives"] if v else None, "decision_days": v[0]["days"] if v else None,
                          "nc1_seeds": len(v), "nc1_mean_bss": mean_bss,
                          "verdict": B.nc1_verdict(v[0]["n"] if v else 0, v[0]["positives"] if v else 0, v[0]["days"] if v else 0, mean_bss),
                          "promotion": "MODEL_NOT_PROMOTED", "status": STATUS, "revision_check_claimed": True})

    # ------------------------------------------------------------ holdout-start cards, contract
    cards_h, smoke = {}, {}
    for target in TARGET_ORDER:
        s = SHORT[target]
        pool = aex_at(dev, target, H, frows, snaps, info, extras)[0]
        cards_h[target], smoke[s] = {}, {}
        for m in A.MODEL_IDS:
            card = A.fit(m, target, pool, H)
            p = art / s / f"{m}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(A.dumps(card))
            back = A.loads(p.read_text())
            tampered = json.loads(p.read_text())
            tampered["body"]["pool"][0]["y"] = 1 - tampered["body"]["pool"][0]["y"]
            try:
                A.verify_card(tampered)
                refused = False
            except B.ModelHashMismatch:
                refused = True
            fsh = P7.fsha(p)
            R.verify_artifact(p, [fsh])
            cards_h[target][m] = back
            smoke[s][m] = {"file_sha256": fsh, "model_sha": card["model_sha"], "n_train": card["n_train"], "k_train": card["k_train"],
                           "abstain": card["body"].get("abstain"), "roundtrip_identical": back == card, "tamper_refused": refused,
                           "pickle_used": False, "max_train_label_matures_at": card["max_train_label_matures_at"]}
        # contract: an ABSTAIN document from the AC3 card passes; a FORECAST with a cohort number is refused
        card = cards_h[target][A.PRIMARY]
        e0 = pool[-1]
        tgt = A.AExample(**{**e0.__dict__, "decision_time": H, "label_matures_at": H + B.maturity_lag(target),
                             "avail": {k: min(v, H) for k, v in e0.avail.items()}})
        ans = A.select(A.PRIMARY, tgt, pool, as_of=H)
        doc = A.abstain_document(target, ans, snapshot_hash=info[e0.decision_key]["row_sha256"], generated_at_utc=B._iso(H),
                                 base_rate=ans["b0"], card=card)
        errs = C.validate(doc, backtest=C.BACKTEST_NOT_AVAILABLE)
        fc = dict(doc, prediction_status="FORECAST", abstain_reasons=[], probability=0.3, uncertainty_interval=[0.2, 0.4],
                  training_cutoff_utc=card["training_cutoff_utc"])
        mc = {"model_sha": card["model_sha"], "feature_set_sha": card["feature_set_sha"], "targets": card["targets"],
              "target_version": card["target_version"], "training_cutoff_utc": card["training_cutoff_utc"]}
        errs_fc = C.validate(fc, model_card=mc, backtest=C.BACKTEST_NOT_AVAILABLE)
        smoke[s]["contract"] = {"abstain_errors": errs, "abstain_valid": not errs, "forecast_refused": bool(errs_fc),
                                "cohort_field": doc["cohort"]}

    # ------------------------------------------------------------ traps, survivorship, trace, oracle arrays
    trap_out = traps(dev, frows, snaps, info, extras, decs, series, rrows, res_by_target, cards_h)
    trap_out["P09_SURVIVORSHIP"] = survivorship(res_by_target)
    trap_out["PHASE07_EQUALITY"] = {**phase07_eq, "pass": phase07_eq["b0_diff"] == 0 and phase07_eq["b2_diff"] == 0
                                    and all(phase07_eq["split_equal"].values())}
    trap_out["CROSS_PHASE_JOIN"] = {**cross, "pass": cross["y_disagree"] == 0 and cross["b0_disagree"] == 0 and cross["missing"] == 0}
    npz: dict[str, np.ndarray] = {}
    for target in TARGET_ORDER:
        s = SHORT[target]
        for r in res_by_target[target]["oos"]:
            pool = None
            for m in ("AC2_KNN", "AC3_KNN_REGIME"):
                x = r["answers"][m]
                if x.get("analogs"):
                    if pool is None:
                        pool = A.regroup(aex_at(dev, target, r["cutoff"], frows, snaps, info, extras)[0])
                    oracle_arrays(npz, f"{s}_{r['example'].decision_key[:12]}_{m}", r["example"], pool, x, m)
    trace = []
    for target in TARGET_ORDER:
        oos = sorted(res_by_target[target]["oos"], key=lambda r: (r["example"].decision_time, r["example"].mint))
        pick = next((r for r in oos if r["answers"][A.PRIMARY].get("number") is not None), None) or \
            next((r for r in oos if any(r["answers"][m].get("number") is not None for m in A.MODEL_IDS)), None) or (oos[0] if oos else None)
        if pick is None:
            continue
        e = pick["example"]
        trace.append({"target": target, "target_short": SHORT[target], "decision_key": e.decision_key, "mint": e.mint,
                      "decision_time": e.decision_time, "cutoff": pick["cutoff"], "regime_record": series[e.decision_time],
                      "inputs": {c: e.x.get(c) for c in A.DIST_COLUMNS}, "creator": e.creator, "cell": list(A.cell_of(e)),
                      "answers": {m: pick["answers"][m] for m in MODELS}, "y": e.y,
                      "pool_keys": sorted(p.decision_key for p in aex_at(dev, target, pick["cutoff"], frows, snaps, info, extras)[0])})

    # ------------------------------------------------------------ outputs
    write_csv(exp / "ANALOG_METRICS.csv", mrows)
    write_csv(exp / "OOS_PREDICTIONS.csv", oos_out)
    write_csv(exp / "COHORT_COVERAGE.csv", cov_rows)
    write_csv(exp / "REGIME_BREAKDOWN.csv", regime_rows_out)
    write_csv(exp / "REGIME_SERIES.csv", [{**{k: v for k, v in rec.items() if k != "T"}, "T_utc": B._iso(T),
                                           "full_sample_label_trap": A.regime_full_sample(rrows, T)["label"]}
                                          for T, rec in sorted(series.items())])
    write_csv(exp / "LOCO_SENSITIVITY.csv", loco_rows)
    write_csv(exp / "DIVERGENCE_FLAGS.csv", div_rows)
    write_csv(exp / "NC1AC_SEEDS.csv", nc1_rows)
    write_csv(exp / "CROSS_PHASE_COMPARISON.csv", [r for r in mrows if r.get("reference") in CROSS or r.get("model") in CROSS])
    prior = list(csv.DictReader(open(P10 / "experiments/SEARCH_LEDGER.csv")))
    for i, when in enumerate(DEBUG_RUNS, 1):
        ledger.append({"phase": "11", "experiment_id": f"P11:debug_run_{i}", "target": "all three", "candidate": "analog-1",
                       "kind": "DEBUG_RUN_REAL_DATA", "view": "", "seed": "", "folds": "", "n_rows": "", "n_with_number": "",
                       "verdict": when, "split_fingerprint": ""})
    write_csv(exp / "SEARCH_LEDGER.csv", prior + ledger)
    write_json(ev_dir / "folds.json", folds_ev)
    write_json(ev_dir / "serialization_smoke.json", smoke)
    write_json(ev_dir / "traps.json", trap_out)
    write_json(ev_dir / "label_sets.json", label_set)
    write_json(ev_dir / "trace" / "trace.json", trace)
    write_json(ev_dir / "regime_counts.json", {"labels": dict(Counter(rec["label"] for rec in series.values())),
                                               "by_day": {d: dict(Counter(rec["label"] for T, rec in series.items() if B._iso(T)[:10] == d))
                                                          for d in sorted({B._iso(T)[:10] for T in series})}})
    if a.npz:
        np.savez(a.npz, **npz)
    sha_after = {p: P7.fsha(p) for p in stores}
    outputs = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file() and p.name != "run_log.json")
    write_json(ev_dir / "run_log.json", {
        "start_utc": start_utc, "end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "head": git("rev-parse", "HEAD").strip(),
        "wall_s": round(time.time() - t0, 2), "cpu_s": round(time.process_time() - c0, 2),
        "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "socket_events": SOCKET_EVENTS, "vendor_calls": 0, "firecrawl_credits": 0, "bootstrap_reps": a.reps,
        "code_sha256": {c: P7.fsha(REPO / c) for c in CODE}, "stores": {"before": sha_before, "after": sha_after,
                                                                       "unchanged": sha_before == sha_after},
        "registry_sha": C.registry_sha256(), "feature_set_sha": F.feature_set_sha(), "analog_feature_set_sha": A.feature_set_sha(),
        "labels_version": L.LABELS_VERSION, "as_of_utc": B._iso(H), "status": STATUS, "revision_check_claimed": True,
        "outputs_sha256": {o: P7.fsha(out / o) for o in outputs}})
    failed = [k for k, v in trap_out.items() if isinstance(v, dict) and v.get("pass") is False]
    print(json.dumps({"targets": {s: folds_ev[s]["status"] for s in folds_ev}, "outputs": len(outputs), "failed_traps": failed,
                      "socket_events": len(SOCKET_EVENTS), "stores_unchanged": sha_before == sha_after}))
    return 1 if failed or SOCKET_EVENTS or sha_before != sha_after else 0


if __name__ == "__main__":
    sys.exit(main())
