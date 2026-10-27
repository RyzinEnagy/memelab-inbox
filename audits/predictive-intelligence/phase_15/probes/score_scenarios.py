"""Phase 15 scoring step (protocol 6 to 11), run only after the blind coding outputs are committed: E1 (A_WARN on the development
walk-forward out-of-sample rows against B0 and B2, with B2, R2 and S2 restated), E2 (rule warnings on every development label,
descriptive), the controls, E3 (POST_OPENING description on the opened holdout's public file), the frozen examples, the
decision, the cumulative search ledger and its totals.

Reads: the coding files only through `scenario_eval.verify_file` with the hashes of the committed CODING_LOG.json (read from git at
CODING_COMMIT); labels only through `labels.training_labels` on the development store (read-only); the committed Phase 10
out-of-sample predictions; the committed public Phase 12 holdout file (POST_OPENING). Never opens `phase_06/sealed/`; no socket.
Deterministic: two runs give identical files except `evidence/score_run_log.json` (times).

    python -B score_scenarios.py OUT_DIR [--dev-store PATH] [--reps 2000]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from memelab.predictive import baselines as B  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import evaluation as E  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import scenario_eval as S  # noqa: E402
from memelab.predictive import stats as K  # noqa: E402

CODING_COMMIT = "7b787bf"
P15 = "audits/predictive-intelligence/phase_15"
DEV_STORE = "/home/claude/pi_research/p06/dev_store.sqlite"
OOS = REPO / "audits/predictive-intelligence/phase_10/experiments/OOS_PREDICTIONS.csv"
SOCIAL_METRICS = REPO / "audits/predictive-intelligence/phase_10/experiments/SOCIAL_METRICS.csv"
HOLDOUT = REPO / "audits/predictive-intelligence/phase_12/validation/HOLDOUT_SCORED.csv"
PRIOR_LEDGER = REPO / "audits/predictive-intelligence/phase_13/experiments/SEARCH_LEDGER.csv"
SHORT = {L.T1: "T1_24h", L.T1B: "T1b_6h", L.T2: "T2_24h"}
LONG = {v: k for k, v in SHORT.items()}
SEED = 20261025
N_SEARCH_BEFORE = 118
CODING_DEBUG = ("P15:DEBUG:CODING:0", "coding step dbg1 2026-10-27T00:56:59Z to 00:57:41Z at uncommitted code; no label, outcome or "
                "prediction file opened"), ("P15:DEBUG:CODING:1", "coding step twin dbg2 at 00:58Z; byte-equal")
DEBUG_RUNS = (("P15:DEBUG:SCORING:0", "scoring step sdbg1 2026-10-27T01:03:08Z to 01:03:15Z at uncommitted code into the scratchpad, after "
                "the coding outputs were committed (7b787bf): every output written; the restated-number check compared Phase 10's "
                "6-decimal CSV values with a 5e-7 tolerance and reported 3 false differences (rounding); tolerance set to 1e-6; no rule, "
                "threshold, gate or output definition changed"),
              ("P15:DEBUG:SCORING:1", "scoring step sdbg2 at 01:03:53Z after that fix: one difference left, T2 B2 skill -0.196928 against "
               "Phase 10's -0.196927 (1.1e-6), because the restated numbers are recomputed from predictions written to 6 decimals; "
               "tolerance set to 1e-5 with that reason; same verdicts, no other change"),
              ("P15:DEBUG:SCORING:2", "scoring step sdbg3 after the second tolerance fix; restated numbers equal"))
SOCKETS: list[str] = []
SEALED: list[str] = []
COMPARATORS = {"A": S.RAN, "B": "BLOCKED_NO_APPROVED_LLM_SPEND", "C": "NO_CALIBRATED_CLASSIFIER_UNCALIBRATED_STAND_INS_ONLY",
               "D": "BLOCKED_NO_APPROVED_LLM_OR_ZEP_SPEND"}
OTHER_MODELS = ("B2", "R2_SC_RULE", "S2_SC_LOGIT_B2")
TOL = 1e-5     # Phase 10's metrics are written to 6 decimals and recomputed here from predictions also written to 6 decimals


def _hook(event, args):
    if event == "open" and args and "phase_06/sealed" in str(args[0]):
        SEALED.append(str(args[0]))
        raise RuntimeError("the sealed folder is never opened in Phase 15")
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKETS.append(event)
        raise RuntimeError("the scoring step makes no network call")


sys.addaudithook(_hook)


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *a], check=True, capture_output=True, text=True).stdout


def iso(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def r6(x):
    if x is None:
        return ""
    if isinstance(x, (float, np.floating)):
        return "" if not math.isfinite(float(x)) else f"{float(x):.6f}"
    return x


def csv_text(rows: list[dict]) -> str:
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r6(r.get(k)) for k in cols})
    return buf.getvalue()


def jdump(o) -> str:
    def d(x):
        if isinstance(x, np.integer):
            return int(x)
        if isinstance(x, np.floating):
            return float(x)
        if isinstance(x, np.ndarray):
            return x.tolist()
        if isinstance(x, SimpleNamespace):
            return vars(x)
        raise TypeError(type(x))
    return json.dumps(o, indent=1, sort_keys=True, default=d, allow_nan=True) + "\n"


def num(s: str) -> float:
    return float(s) if s not in ("", None) else float("nan")


def clean(res: dict) -> dict:
    """An evaluate() result without bootstrap arrays."""
    out = {k: v for k, v in res.items() if k not in ("intervals",)}
    out["intervals"] = {u: {kk: vv for kk, vv in iv.items()} for u, iv in (res.get("intervals") or {}).items()}
    return out


# ---------------------------------------------------------------- inputs
def load_coding():
    log = json.loads(git("show", f"{CODING_COMMIT}:{P15}/behavioral/CODING_LOG.json"))
    sha = log["outputs_sha256"]
    files = {}
    for k in ("behavioral/SCENARIO_CODING.csv", "behavioral/CONTROL_CODING.csv"):
        files[k] = list(csv.DictReader(io.StringIO(S.verify_file(REPO / P15 / k, sha[k]).decode())))
    if log["label_calls"] or log["forbidden_opens"] or log["socket_events"]:
        raise SystemExit("the coding run was not blind")
    coding = {(r["set"], r["decision_key"], r["target"]): r for r in files["behavioral/SCENARIO_CODING.csv"]}
    ctrl = {(r["control"], r["decision_key"], r["target"]): r for r in files["behavioral/CONTROL_CODING.csv"]}
    return log, coding, ctrl


def label_rows(dev, as_of, target):
    return L.training_labels(dev, as_of, target, mode="provider")


def warned_rows(labels, coding, set_name, target, *, label_filter=None, override=None):
    rows, missing = [], 0
    for r in labels:
        c = coding.get((set_name, r["decision_key"], target))
        if c is None:
            missing += 1
            continue
        w = c["warning"]
        if override is not None:
            w = override.get(r["decision_key"], w)
        if label_filter is not None and w == S.WARN_EVENT and label_filter not in c["labels"].split("|"):
            w = S.WARN_NONE
        lead = (float(r["first_touch_start"]) - float(r["decision_time"])) if (r["label"] == 1 and r["first_touch_start"] is not None) else None
        rows.append({"decision_key": r["decision_key"], "mint": r["mint"], "decision_time": float(r["decision_time"]),
                     "label_matures_at": float(r["label_matures_at"]), "day": iso(float(r["decision_time"]))[:10],
                     "y": int(r["label"]), "warning": w, "lead_s": lead})
    return rows, missing


def day_shuffled_warnings(coding, set_name, target) -> dict[str, str]:
    """NCS: warnings permuted among the decisions of the same day (one permutation, seed 20261025)."""
    by_day: dict[str, list[tuple[str, str]]] = {}
    for (s, k, t), r in sorted(coding.items()):
        if s == set_name and t == target:
            by_day.setdefault(r["day"], []).append((k, r["warning"]))
    rng = np.random.default_rng(SEED)
    out = {}
    for d in sorted(by_day):
        keys = [k for k, _ in by_day[d]]
        ws = [w for _, w in by_day[d]]
        perm = rng.permutation(len(ws))
        out.update({k: ws[i] for k, i in zip(keys, perm)})
    return out


# ---------------------------------------------------------------- E1
def e1(dev, coding, lab_h, reps, n_search):
    oos = [r for r in csv.DictReader(open(OOS))]
    out, row_out, cards = {}, [], []
    for target in S.PRIMARY:
        ts = SHORT[target]
        rows = [r for r in oos if r["target_short"] == ts]
        lab = {r["decision_key"]: r for r in lab_h[target]}
        mism = [r["decision_key"] for r in rows if r["decision_key"] not in lab or int(lab[r["decision_key"]]["label"]) != int(r["y"])]
        if mism:
            raise SystemExit(f"{ts}: {len(mism)} out-of-sample rows disagree with training_labels")
        shuffled = day_shuffled_warnings(coding, "DEVELOPMENT", target)
        ev = []
        for cut_s in sorted({r["cutoff_utc"] for r in rows}):
            cut = C.parse_utc(cut_s)
            tr_labels = label_rows(dev, cut, target)
            for tag, over in (("A_WARN", None), ("NCS", shuffled)):
                train, miss = warned_rows(tr_labels, coding, "DEVELOPMENT", target, override=over)
                card = S.fit_warn(target, train, cut)
                cards.append({"target": ts, "variant": tag, "cutoff_utc": cut_s, "missing_seed_training_rows": miss,
                              **{k: card[k] for k in ("n", "k", "excluded", "card_sha256", "training_keys_sha256")},
                              "abstain": card.get("abstain"), "b0": card.get("b0"), "cells": card.get("cells")})
                test_rows = [r for r in rows if r["cutoff_utc"] == cut_s]
                tw = []
                for r in test_rows:
                    c = coding.get(("DEVELOPMENT", r["decision_key"], target))
                    w = (over or {}).get(r["decision_key"], c["warning"]) if c else S.WARN_NOT_CODABLE
                    tw.append({"decision_key": r["decision_key"], "decision_time": C.parse_utc(r["decision_time_utc"]), "warning": w})
                p, why = S.predict_warn(card, tw)
                for r, pp, wy, t_ in zip(test_rows, p, why, tw):
                    key = (r["decision_key"], cut_s)
                    e = next((x for x in ev if x["key"] == key), None)
                    if e is None:
                        e = {"key": key, "fold": int(r["fold"]), "y": int(r["y"]),
                             "example": SimpleNamespace(day=r["day"], mint=r["mint"], decision_key=r["decision_key"]),
                             "B0": num(r["B0"]), "B2": num(r["B2"]), "R2_SC_RULE": num(r["R2_SC_RULE"]),
                             "S2_SC_LOGIT_B2": num(r["S2_SC_LOGIT_B2"]), "B2_why": r["B2_why"] or None,
                             "R2_SC_RULE_why": r["R2_SC_RULE_why"] or None, "S2_SC_LOGIT_B2_why": r["S2_SC_LOGIT_B2_why"] or None}
                        ev.append(e)
                    e[tag] = float(pp)
                    e[tag + "_why"] = wy
                    if tag == "A_WARN":
                        e["warning"] = t_["warning"]
        res = {"A_WARN_vs_B0": clean(B.evaluate(ev, "A_WARN", reference="B0", reps=reps, seed=SEED)),
               "A_WARN_vs_B2": clean(B.evaluate(ev, "A_WARN", reference="B2", reps=reps, seed=SEED)),
               "NCS_vs_B0": clean(B.evaluate(ev, "NCS", reference="B0", reps=reps, seed=SEED))}
        for m in OTHER_MODELS:
            res[f"{m}_vs_B0"] = clean(B.evaluate(ev, m, reference="B0", reps=reps, seed=SEED))
        res["rows"] = len(ev)
        res["statements_in_oos_rows"] = sum(1 for e in ev if e.get("warning") == S.WARN_EVENT)
        res["no_rule_statements"] = not any(r["warning"] == S.WARN_EVENT for (s, k, t), r in coding.items() if s == "DEVELOPMENT" and t == target)
        res["split_fingerprint"] = hashlib.sha256(json.dumps(sorted([list(e["key"]) for e in ev])).encode()).hexdigest()
        out[target] = res
        for e in ev:
            row_out.append({"target_short": ts, "fold": e["fold"], "cutoff_utc": e["key"][1], "decision_key": e["example"].decision_key,
                            "mint": e["example"].mint, "day": e["example"].day, "y": e["y"], "warning": e.get("warning"),
                            "A_WARN": e["A_WARN"], "A_WARN_why": e["A_WARN_why"], "NCS": e["NCS"], "B0": e["B0"], "B2": e["B2"],
                            "R2_SC_RULE": e["R2_SC_RULE"], "S2_SC_LOGIT_B2": e["S2_SC_LOGIT_B2"]})
    pv = [out[t]["A_WARN_vs_B0"].get("p_one_sided") for t in S.PRIMARY]
    holm = K.holm(pv)
    for t, h in zip(S.PRIMARY, holm):
        r = out[t]["A_WARN_vs_B0"]
        hp = h if math.isfinite(h) else None
        bonf = E.bonferroni(r.get("p_one_sided"), n_search)
        r["p_holm"], r["p_bonferroni_n_search"], r["n_search"] = hp, bonf, n_search
        r["verdict_with_holm"] = B.verdict(r, hp) if r.get("n_with_number") else r["verdict"]
        r["selection_status"] = S.selection_status_dev(r["verdict_with_holm"], hp, bonf, None)
        if out[t]["no_rule_statements"]:
            r["note"] = "NO_RULE_STATEMENTS: A_WARN equals B0 by construction on this target"
    return out, row_out, cards


def restated_match(e1_out) -> dict:
    sm = {(r["target_short"], r["model"]): r for r in csv.DictReader(open(SOCIAL_METRICS)) if r["view"] == "ALL" and r["reference"] == "B0"}
    out = {}
    for t in S.PRIMARY:
        for m in OTHER_MODELS:
            ours = e1_out[t][f"{m}_vs_B0"]
            ref = sm[(SHORT[t], m)]
            ok = int(ref["n_with_number"]) == ours["n_with_number"]
            if ours.get("brier") is not None and ref["brier"]:
                ok = ok and abs(float(ref["brier"]) - ours["brier"]) <= TOL and abs(float(ref["bss_vs_ref"]) - ours["bss"]) <= TOL
            ok = ok and ref["verdict"] == ours["verdict"]
            out[f"{SHORT[t]}:{m}"] = {"equal": bool(ok), "phase10_brier": ref["brier"], "ours": ours.get("brier"),
                                      "phase10_verdict": ref["verdict"], "our_verdict": ours["verdict"]}
    return out


# ---------------------------------------------------------------- E2 and controls
def e2(coding, ctrl, lab_h, reps):
    out, rows_out, per_label = {}, [], {}
    for target in S.PRIMARY:
        rows, miss = warned_rows(lab_h[target], coding, "DEVELOPMENT", target)
        res = S.warning_metrics(rows, reps=reps, seed=SEED)
        res["labelled_rows"] = len(lab_h[target])
        res["missing_seed"] = miss
        out[target] = res
        for r in rows:
            rows_out.append({"target_short": SHORT[target], "decision_key": r["decision_key"], "day": r["day"], "y": r["y"],
                             "warning": r["warning"], "lead_s": r["lead_s"]})
    hb = S.holm_by_target(out)
    for t in out:
        out[t].update(hb[t])
    for lab, t in (("ATTENTION_EXHAUSTION", L.T2), ("MANUFACTURED_ATTENTION_DUMP", L.T2), ("ORGANIC_ATTENTION_CONTINUATION", L.T1B)):
        rows, _ = warned_rows(lab_h[t], coding, "DEVELOPMENT", t, label_filter=lab)
        r = S.warning_metrics(rows, reps=reps, seed=SEED)
        r["verdict"] = r["gate"] or "SECONDARY_DESCRIPTION_NO_VERDICT"
        per_label[f"{SHORT[t]}:{lab}"] = r
    # NCB on T1
    ncb_rows = []
    for r in lab_h[L.T1]:
        c = ctrl.get(("NCB_VERIFIED", r["decision_key"], L.T1))
        if c is None:
            continue
        ncb_rows.append({"y": int(r["label"]), "day": iso(float(r["decision_time"]))[:10], "warning": c["warning"], "lead_s": None})
    ncb = S.warning_metrics(ncb_rows, reps=reps, seed=SEED)
    nh = S.holm_by_target({L.T1: ncb})[L.T1]
    ncb.update(nh)
    ncb["ncb_failed"] = nh["verdict"] in (S.LIFT_SUGGESTED, S.WORSE)
    unv = Counter((c["planted"], c["warning"]) for (ctl, k, t), c in ctrl.items() if ctl == "NCB_UNVERIFIED" and t == L.T1)
    return out, rows_out, per_label, {"NCB_VERIFIED_T1": ncb,
                                     "NCB_UNVERIFIED_T1_warnings": {f"planted={a}:{b}": v for (a, b), v in sorted(unv.items())}}


# ---------------------------------------------------------------- E3 (POST_OPENING)
def e3(dev, coding, lab_h, reps):
    H = L.holdout_start()
    hs = list(csv.DictReader(open(HOLDOUT)))
    out = {}
    log = {"label": "POST_OPENING", "source": "audits/predictive-intelligence/phase_12/validation/HOLDOUT_SCORED.csv",
           "source_sha256": hashlib.sha256(HOLDOUT.read_bytes()).hexdigest(), "rule": "PI-D-066: description only, more conservative only",
           "sealed_folder_opened": False}
    for target in S.PRIMARY:
        rows = [r for r in hs if r["target_short"] == SHORT[target]]
        wrows, miss = [], 0
        for r in rows:
            c = coding.get(("HOLDOUT_WINDOW", r["decision_key"], target))
            if c is None:
                miss += 1
                continue
            wrows.append({"decision_key": r["decision_key"], "decision_time": C.parse_utc(r["decision_time_utc"]), "y": int(r["y"]),
                          "day": r["day"], "warning": c["warning"], "mint": r["mint"], "B0": num(r["P07_B0"]), "B2": num(r["P07_B2"]),
                          "lead_s": None})
        wm = S.warning_metrics(wrows, reps=reps, seed=SEED)
        train, tmiss = warned_rows(lab_h[target], coding, "DEVELOPMENT", target)
        card = S.fit_warn(target, train, H)
        p, why = S.predict_warn(card, wrows)
        ev = [{"fold": 0, "y": w["y"], "example": SimpleNamespace(day=w["day"], mint=w["mint"]), "A_WARN": float(pp), "A_WARN_why": wy,
               "B0": w["B0"], "B2": w["B2"]} for w, pp, wy in zip(wrows, p, why)]
        vb0 = clean(B.evaluate(ev, "A_WARN", reference="B0", reps=reps, seed=SEED))
        vb2 = clean(B.evaluate(ev, "A_WARN", reference="B2", reps=reps, seed=SEED))
        post = E.FAILS if vb0.get("verdict") == "WORSE_THAN_BASE_RATE" else E.NO_UNCORRECTED_SKILL
        out[target] = {"rows": len(rows), "missing_seed": miss, "warning_metrics": wm, "a_warn_card_sha256": card["card_sha256"],
                       "a_warn_card_abstain": card.get("abstain"), "training_missing_seed": tmiss,
                       "A_WARN_H_vs_B0": vb0, "A_WARN_H_vs_B2": vb2, "post_opening_status": post}
    hb = S.holm_by_target({t: out[t]["warning_metrics"] for t in out})
    for t in out:
        out[t]["warning_metrics"].update(hb[t])
    return out, log


# ---------------------------------------------------------------- protocol 9 examples
def examples(e2_rows, coding):
    order = {L.T1: 0, L.T1B: 1, L.T2: 2}
    dt = {k: r["decision_time_utc"] for (s, k, t), r in coding.items() if s == "DEVELOPMENT"}
    rows = sorted(e2_rows, key=lambda r: (dt[r["decision_key"]], r["decision_key"], order[LONG[r["target_short"]]]))
    hit = next((r for r in rows if r["warning"] == S.WARN_EVENT and r["y"] == 1), None)
    miss = next((r for r in rows if r["warning"] == S.WARN_EVENT and r["y"] == 0), None)
    labelled = {r["decision_key"] for r in e2_rows}
    unscor = None
    for k in sorted(labelled, key=lambda k: (dt[k], k)):
        if all(coding[("DEVELOPMENT", k, t)]["warning"] in (S.WARN_NONE, S.WARN_NOT_CODABLE) for t in S.PRIMARY):
            unscor = k
            break

    def ex(r):
        if r is None:
            return None
        c = coding[("DEVELOPMENT", r["decision_key"], LONG[r["target_short"]])]
        return {"decision_key": r["decision_key"], "mint": c["mint"], "decision_time_utc": c["decision_time_utc"], "target": r["target_short"],
                "labels": c["labels"], "warning": r["warning"], "y": r["y"], "lead_h": (r["lead_s"] / 3600.0) if r["lead_s"] else None,
                "doc_sha256": c["doc_sha256"]}
    u = None
    if unscor:
        c = coding[("DEVELOPMENT", unscor, L.T1)]
        u = {"decision_key": unscor, "mint": c["mint"], "decision_time_utc": c["decision_time_utc"], "doc_sha256": c["doc_sha256"],
             "why": "NO_GROUNDED_SCENARIO: no statement on any primary target", "no_statement_doc": c["no_statement_doc"]}
    return {"A_correct": ex(hit), "A_fails": ex(miss), "A_cannot_be_scored": u,
            "D_MiroFish": {"correct": "NOT_AVAILABLE", "fails": "NOT_AVAILABLE",
                           "cannot_be_scored": "phase_14/behavioral/MIROFISH_PROBE.json run meter_cap_high: SIMULATION_RAN, NOT_CODABLE free text "
                                               "(fictional seed, canned mock LLM)"}}


# ---------------------------------------------------------------- ledger (P22)
def ledger_rows(e1_out, e2_out, per_label, ctrl, e3_out, coding_log) -> list[dict]:
    rows = []

    def add(eid, target, cand, kind, view="ALL", seed="", folds="", n_rows="", n_num="", verdict="", fp="", sel="", claim=""):
        rows.append({"phase": "15", "experiment_id": eid, "target": target, "candidate": cand, "kind": kind, "view": view, "seed": seed,
                     "folds": folds, "n_rows": n_rows, "n_with_number": n_num, "verdict": verdict, "split_fingerprint": fp,
                     "selection_status": sel, "claim": claim})
    for t in S.PRIMARY:
        r = e1_out[t]
        a = r["A_WARN_vs_B0"]
        add(f"P15:E1:{t}:A_WARN_vs_B0", t, "P15_A_WARN", "SIMPLE_ATTENTION_RULE", seed=SEED, folds=a.get("folds", ""), n_rows=a["n_rows"],
            n_num=a["n_with_number"], verdict=a["verdict_with_holm"], fp=r["split_fingerprint"], sel=a["selection_status"],
            claim="NOT_A_CLAIM")
        b = r["A_WARN_vs_B2"]
        add(f"P15:E1:{t}:A_WARN_vs_B2", t, "P15_A_WARN", "SIMPLE_ATTENTION_RULE", view="REFERENCE_B2", seed=SEED, folds=b.get("folds", ""),
            n_rows=b["n_rows"], n_num=b["n_with_number"], verdict=b["verdict"], fp=r["split_fingerprint"], sel=E.NO_UNCORRECTED_SKILL,
            claim="NOT_A_CLAIM")
        n = r["NCS_vs_B0"]
        add(f"P15:E1:{t}:NCS_A_WARN_SHUFFLED", t, "P15_A_WARN_NCS", "NEGATIVE_CONTROL", seed=SEED, folds=n.get("folds", ""),
            n_rows=n["n_rows"], n_num=n["n_with_number"], verdict=n["verdict"], fp=r["split_fingerprint"], claim="CONTROL")
        w = e2_out[t]
        add(f"P15:E2:{t}:A_WARNINGS", t, "P15_RULES_1_WARNINGS", "DESCRIPTION_ONLY", view="DEVELOPMENT_ALL_LABELS", seed=SEED,
            n_rows=w["n_rows"], n_num=w["n_scored"], verdict=w["verdict"], claim="NOT_A_CLAIM_RULES_AUTHORED_AFTER_DATA_PUBLIC")
        x = e3_out[t]
        add(f"P15:E3:{t}:A_POST_OPENING", t, "P15_RULES_1_WARNINGS", "POST_OPENING_CHECK", view="RETROSPECTIVE_HOLDOUT_SPENT", seed=SEED,
            n_rows=x["rows"], n_num=x["warning_metrics"]["n_scored"], verdict=x["warning_metrics"]["verdict"],
            sel=x["post_opening_status"], claim="POST_OPENING_NOT_A_CLAIM")
        add(f"P15:E3:{t}:A_WARN_H_POST_OPENING", t, "P15_A_WARN_H", "POST_OPENING_CHECK", view="RETROSPECTIVE_HOLDOUT_SPENT", seed=SEED,
            n_rows=x["A_WARN_H_vs_B0"]["n_rows"], n_num=x["A_WARN_H_vs_B0"]["n_with_number"], verdict=x["A_WARN_H_vs_B0"]["verdict"],
            sel=x["post_opening_status"], claim="POST_OPENING_NOT_A_CLAIM")
    for key, r in per_label.items():
        ts, lab = key.split(":")
        add(f"P15:E2:{LONG[ts]}:LABEL_{lab}", LONG[ts], f"P15_RULES_1_LABEL_{lab}", "DESCRIPTION_ONLY", view="DEVELOPMENT_ALL_LABELS",
            seed=SEED, n_rows=r["n_rows"], n_num=r["n_scored"], verdict=r["verdict"], claim="SECONDARY_DESCRIPTION")
    nc = ctrl["NCB_VERIFIED_T1"]
    add(f"P15:NCB:{L.T1}:BOGUS_VERIFIED", L.T1, "P15_NCB_BOGUS_VERIFIED", "NEGATIVE_CONTROL", view="DEVELOPMENT_ALL_LABELS", seed=SEED,
        n_rows=nc["n_rows"], n_num=nc["n_scored"], verdict=nc["verdict"], claim="CONTROL_FAILED" if nc["ncb_failed"] else "CONTROL")
    cs = coding_log["controls"]
    add("P15:NCB:UNVERIFIED", "", "P15_NCB_UNVERIFIED", "TRAP_OR_CHECK", n_rows=cs["NCB_UNVERIFIED"]["planted"],
        verdict=f"{cs['NCB_UNVERIFIED']['planted_unscorable_rumor_fade']} of {cs['NCB_UNVERIFIED']['planted']} UNSCORABLE_NO_OUTCOME_SOURCE",
        claim="CHECK")
    for nm in ("P28_AFTER_DECISION_OBSERVATION", "P28_POST_DECISION_DATE_TEXT"):
        add(f"P15:{nm.replace('P28_', 'P28:')}", "", "P15_P28_TRAP", "TRAP_OR_CHECK", n_rows=cs[nm]["seeds"],
            verdict=f"{cs[nm]['refused']} of {cs[nm]['seeds']} refused, {cs[nm]['statements']} statements", claim="CHECK")
    for eid, note in CODING_DEBUG + DEBUG_RUNS:
        add(eid, "", "", "DEBUG_RUN_REAL_DATA", verdict=note)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--dev-store", default=DEV_STORE)
    ap.add_argument("--reps", type=int, default=2000)
    a = ap.parse_args()
    out = Path(a.out)
    for d in ("behavioral", "experiments", "evidence"):
        (out / d).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    coding_log, coding, ctrl = load_coding()
    dev_sha = hashlib.sha256(Path(a.dev_store).read_bytes()).hexdigest()
    dev = sqlite3.connect(f"file:{a.dev_store}?mode=ro", uri=True)
    dev.row_factory = sqlite3.Row
    H = L.holdout_start()
    lab_h = {t: label_rows(dev, H, t) for t in S.PRIMARY}
    prior = list(csv.DictReader(open(PRIOR_LEDGER)))
    before = E.ledger_totals(prior)
    if before["n_search"] != N_SEARCH_BEFORE:
        raise SystemExit(f"prior N_search {before['n_search']} is not {N_SEARCH_BEFORE}")
    n_search = N_SEARCH_BEFORE + len(S.PRIMARY)          # A_WARN on three targets (protocol 11)
    e1_out, e1_rows, e1_cards = e1(dev, coding, lab_h, a.reps, n_search)
    restated = restated_match(e1_out)
    e2_out, e2_rows, per_label, ctrl_out = e2(coding, ctrl, lab_h, a.reps)
    e3_out, po_log = e3(dev, coding, lab_h, a.reps)
    ex = examples(e2_rows, coding)
    a_warn = {SHORT[t]: {"verdict": e1_out[t]["A_WARN_vs_B0"]["verdict_with_holm"],
                         "selection_status": e1_out[t]["A_WARN_vs_B0"]["selection_status"],
                         "brier": e1_out[t]["A_WARN_vs_B0"].get("brier"), "brier_b2": e1_out[t]["A_WARN_vs_B2"].get("brier_ref")}
              for t in S.PRIMARY}
    decision = S.decide(eligible_events=int(coding_log["event_count"]["eligible_catalyst_events"]), comparators=COMPARATORS, a_warn=a_warn)
    combined = {SHORT[t]: E.conservative_status(e1_out[t]["A_WARN_vs_B0"]["selection_status"], e3_out[t]["post_opening_status"])
                for t in S.PRIMARY}
    po_log["combined_status"] = combined
    po_log["computed"] = ["rule warnings on the holdout-window documents", "A_WARN fitted at the holdout start on development labels"]
    led = ledger_rows(e1_out, e2_out, per_label, ctrl_out, e3_out, coding_log)
    full = prior + led
    after = E.ledger_totals(full)
    results = {"phase": "15", "scenario_eval_version": S.SCENARIO_EVAL_VERSION, "coding_commit": CODING_COMMIT,
               "coding_outputs_sha256": coding_log["outputs_sha256"], "event_count": coding_log["event_count"],
               "labelled_counts_dev": {SHORT[t]: {"n": len(lab_h[t]), "positives": int(sum(r["label"] for r in lab_h[t]))} for t in S.PRIMARY},
               "E1": {SHORT[t]: e1_out[t] for t in S.PRIMARY}, "E1_restated_equal_to_phase10": restated, "E1_cards": e1_cards,
               "E2": {SHORT[t]: e2_out[t] for t in S.PRIMARY}, "E2_per_label": per_label, "controls": ctrl_out,
               "controls_coding": coding_log["controls"], "E3_POST_OPENING": {SHORT[t]: e3_out[t] for t in S.PRIMARY},
               "examples": ex, "decision": decision, "comparators": COMPARATORS,
               "not_compared": {"B": "evidence-only LLM: no approved LLM spend (PI-D-005, PI-D-078); P26 would make a retrospective run EXPLORATORY_NOT_AS_OF",
                                "D": "MiroFish: no approved LLM or Zep spend, no key; MIROFISH_GATE BLOCKED (PI-D-077); non-reproducible for a fixed seed and NOT_CODABLE free text on its script path (Phase 14); P26",
                                "C": "no calibrated classifier exists (PI-D-069); B2, R2_SC_RULE and S2_SC_LOGIT_B2 are uncalibrated stand-ins"},
               "net_decision_utility": "NOT_COMPUTABLE: NO_HISTORICAL_EXECUTABLE_DEPTH, EXECUTION_DATA_MISSING, BACKTEST_NOT_AVAILABLE",
               "cost_usd": 0.0, "llm_calls": 0,
               "ledger": {"before": before, "after": after, "phase15_rows": len(led), "rule_configurations_after": E.rule_configurations(full)}}
    files = {"behavioral/INCREMENTAL_VALUE_RESULTS.json": jdump(results), "behavioral/E1_OOS_ROWS.csv": csv_text(e1_rows),
             "behavioral/E2_SCORED_ROWS.csv": csv_text(e2_rows), "behavioral/POST_OPENING_LOG.json": jdump(po_log),
             "experiments/SEARCH_LEDGER.csv": csv_text(full), "experiments/LEDGER_TOTALS.json": jdump(results["ledger"])}
    for k, v in files.items():
        (out / k).write_text(v)
    log = {"script": f"{P15}/probes/score_scenarios.py", "start_utc": iso(t0), "end_utc": iso(time.time()), "head": git("rev-parse", "HEAD").strip(),
           "dev_store_sha256": dev_sha, "reps": a.reps, "sockets": SOCKETS, "sealed_opens": SEALED, "debug_runs": [list(x) for x in DEBUG_RUNS],
           "outputs_sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in files.items()}}
    (out / "evidence/score_run_log.json").write_text(jdump(log))
    print(json.dumps({"decision": decision, "E1": {SHORT[t]: e1_out[t]["A_WARN_vs_B0"]["verdict_with_holm"] for t in S.PRIMARY},
                      "E2": {SHORT[t]: e2_out[t]["verdict"] for t in S.PRIMARY}, "NCB": ctrl_out["NCB_VERIFIED_T1"]["verdict"],
                      "restated_equal": all(v["equal"] for v in restated.values()), "n_search": after["n_search"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
