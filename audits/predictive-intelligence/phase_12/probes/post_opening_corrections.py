"""Phase 12 repair pass 2, POST_OPENING (PI-D-066): the selection-correction gaps the independent skeptic found, computed after
the holdout was opened, logged, and allowed only to make results more conservative. It never changes the champion, never adds
a candidate and never creates a skill claim (`evaluation.conservative_status`).

  1. CX-S12, m5: the recorded run computed max-T only against B0; every secondary row against B2 had no max-T, so "0 of 129
     survive" could not have reported a card beating B2. Here the max-T against B2 is computed over every fitted card other than
     B0 and B2 (same day-block rule, 20,000 replicates, seed 20261025).
  2. m3: the full-search Bonferroni with N_search + the 9 non-probability rule configurations (127).
  3. m1: a corrected copy of the full experiment ledger with `selection_status` and `claim` beside every verdict, so no
     Holm-only verdict reads as a claim. The recorded `FULL_EXPERIMENT_LEDGER.csv` stays byte-equal (its hash is in the opening
     log); later phases add to `FULL_EXPERIMENT_LEDGER_CORRECTED.csv`.

Reads only committed Phase 12 outputs (`HOLDOUT_SCORED.csv` holds the scored holdout labels); never the sealed folder; no
network. Deterministic apart from `POST_OPENING_LOG.json` times.

    python -B post_opening_corrections.py OUTDIR
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from memelab.predictive import evaluation as E  # noqa: E402

VAL = REPO / "audits/predictive-intelligence/phase_12/validation"
SHORT = ("T1_24h", "T1b_6h", "T2_24h")
LONG = {"T1_24h": "price_path_target_before_invalidation_24h", "T1b_6h": "price_path_target_before_invalidation_6h",
        "T2_24h": "price_path_severe_drawdown_or_halt_24h"}
RECORDED = ("HOLDOUT_SCORED.csv", "HOLDOUT_METRICS.csv", "FULL_EXPERIMENT_LEDGER.csv", "CANDIDATES.json", "OPENING_LOG.json")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def f(x):
    return float(x) if x not in ("", None) else None


def num(x):
    if x is None:
        return ""
    if isinstance(x, bool):
        return "1" if x else "0"
    if isinstance(x, int):
        return str(x)
    return "" if not math.isfinite(x) else f"{x:.17g}"


def write_csv(path: Path, rows: list[dict]) -> None:
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (num(v) if isinstance(v, (float, int, bool)) else ("" if v is None else v)) for k, v in r.items()})


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    before = {n: sha(VAL / n) for n in RECORDED}
    log = json.loads((VAL / "OPENING_LOG.json").read_text())
    if [e["mode"] for e in log["entries"]] != ["FIRST_OPENING"]:
        raise SystemExit("expected exactly the first opening in the log")
    for n, h in log["entries"][0]["outputs_sha256"].items():
        if (VAL / n).exists() and sha(VAL / n) != h:
            raise SystemExit(f"{n} differs from the hash in the opening log")
    with open(VAL / "HOLDOUT_SCORED.csv") as fh:
        scored = list(csv.DictReader(fh))
    with open(VAL / "HOLDOUT_METRICS.csv") as fh:
        metrics = list(csv.DictReader(fh))
    cands = json.loads((VAL / "CANDIDATES.json").read_text())
    fitted = {(c["target_short"], c["candidate"]) for c in cands["candidates"] if c["fitted"]}
    with open(VAL / "FULL_EXPERIMENT_LEDGER.csv") as fh:
        ledger = list(csv.DictReader(fh))
    n_search = E.ledger_totals([r for r in ledger if r["phase"] != "12"])["n_search"]
    n_rules = E.rule_configurations([r for r in ledger if r["phase"] != "12"])
    n_post = n_search + n_rules
    # 1. max-T against B2 over every fitted card other than B0 and B2 (the same family shape as the recorded one against B0)
    days, ys, refs, preds = {}, {}, {}, {}
    for s in SHORT:
        rr = [r for r in scored if r["target_short"] == s]
        days[s] = [r["day"] for r in rr]
        ys[s] = np.array([float(r["y"]) for r in rr])
        refs[s] = np.array([f(r["P07_B2"]) if f(r["P07_B2"]) is not None else float("nan") for r in rr])
        for (ss, cid) in sorted(fitted):
            if ss == s and cid not in ("P07_B0", "P07_B2"):
                p = np.array([f(r[cid]) if f(r[cid]) is not None else float("nan") for r in rr])
                if np.isfinite(p).any():
                    preds[(s, cid)] = p
    mt_b2 = E.max_t(days, ys, refs, preds, reps=E.REPS, seed=E.SEED)
    # 2 and 3. per secondary row: recorded state, post-opening state, the conservative combination
    rows, by_id = [], {}
    for m in metrics:
        if m["kind"] != "SECONDARY_HOLDOUT":
            continue
        s, cid, ref = m["target_short"], m["model"], m["reference"]
        own = m["uncorrected_verdict"]
        p_raw, p_h, p_mt = f(m["p_one_sided"]), f(m["p_holm"]), f(m["p_max_t"])
        rec = E.selection_status(own, p_h, p_mt, f(m["p_bonferroni_full_search"]))
        if (rec == E.SURVIVES) != (m["skill_after_selection_correction"] == "1"):
            raise SystemExit(f"recorded state disagrees with the recorded column on {s} {cid} vs {ref}")
        p_mt_post = p_mt if ref == "P07_B0" else (mt_b2.get((s, cid)) or {}).get("p_max_t")
        bon_post = E.bonferroni(p_raw, n_post)
        post = E.selection_status(own, p_h, p_mt_post, bon_post)
        final = E.conservative_status(rec, post)
        row = {"target_short": s, "model": cid, "reference": ref, "n_with_number": m["n_with_number"], "bss": f(m["bss"]),
               "uncorrected_verdict": own, "recorded_verdict_column_holm_only": m["verdict"], "p_one_sided": p_raw, "p_holm": p_h,
               "p_max_t_recorded": p_mt, "p_bonferroni_118": f(m["p_bonferroni_full_search"]),
               "p_max_t_vs_b2_post_opening": p_mt_post if ref == "P07_B2" else None, "p_bonferroni_127_post_opening": bon_post,
               "selection_status_recorded": rec, "selection_status_post_opening": post, "selection_status_final": final,
               "label": "POST_OPENING"}
        rows.append(row)
        by_id[f"P12:{LONG[s]}:{cid}_vs_{ref[4:]}"] = row
    write_csv(out / "POST_OPENING_CORRECTIONS.csv", rows)
    # corrected ledger: every recorded row plus selection_status and claim; then the post-opening checks
    corrected = []
    for r in ledger:
        c = dict(r)
        st, claim = "", ""
        if r["phase"] == "12" and r["kind"] == "SECONDARY_HOLDOUT":
            st = by_id[r["experiment_id"]]["selection_status_final"]
            claim = "CLAIM_SKILL_AFTER_SELECTION_CORRECTION" if st == E.SURVIVES else (
                "NOT_A_CLAIM_VERDICT_IS_HOLM_ONLY" if r["verdict"] == E.HOLDOUT_SKILL else "NO_CLAIM")
        elif r["phase"] == "12" and r["kind"] == "PRIMARY_HOLDOUT":
            claim = "NO_CLAIM" if r["verdict"] != E.HOLDOUT_SKILL else "SEE_PRIMARY_RESULTS"
        c["selection_status"], c["claim"] = st, claim
        corrected.append(c)
    for name, view, verdict in (
            ("MAX_T_AGAINST_B2", f"{len(preds)} fitted cards other than B0 and B2, day block, 20000 replicates",
             f"{sum(1 for v in mt_b2.values() if v['p_max_t'] is not None and v['p_max_t'] < E.ALPHA)} below 0.05"),
            ("BONFERRONI_N_SEARCH_PLUS_RULES", f"N = {n_search} + {n_rules} = {n_post}",
             f"{sum(1 for r in rows if r['p_bonferroni_127_post_opening'] is not None and r['p_bonferroni_127_post_opening'] < E.ALPHA)} below 0.05"),
            ("SELECTION_STATUS_FINAL", "every secondary row",
             json.dumps(dict(sorted({k: sum(1 for r in rows if r['selection_status_final'] == k) for k in {r['selection_status_final'] for r in rows}}.items()))))):
        corrected.append({"phase": "12", "experiment_id": f"P12:all:POST_OPENING_{name}", "target": "all three", "candidate": name,
                          "kind": "POST_OPENING_CHECK", "view": view, "seed": E.SEED, "folds": "HOLDOUT", "n_rows": "",
                          "n_with_number": "", "verdict": verdict, "split_fingerprint": "", "selection_status": "",
                          "claim": "POST_OPENING_MORE_CONSERVATIVE_ONLY"})
    write_csv(out / "FULL_EXPERIMENT_LEDGER_CORRECTED.csv", corrected)
    after = {n: sha(VAL / n) for n in RECORDED}
    if before != after:
        raise SystemExit("a recorded output changed")
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    summary = {"label": "POST_OPENING", "decision": "PI-D-066", "time_utc": datetime.fromtimestamp(t0, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "head": head, "inputs_sha256": before, "recorded_outputs_unchanged": True, "sealed_folder_read": False,
               "n_search": n_search, "rule_configurations": n_rules, "n_search_post_opening": n_post,
               "max_t_vs_b2_family": len(preds), "max_t_vs_b2_below_alpha": sum(1 for v in mt_b2.values() if v["p_max_t"] is not None and v["p_max_t"] < E.ALPHA),
               "min_p_max_t_vs_b2": min((v["p_max_t"] for v in mt_b2.values() if v["p_max_t"] is not None), default=None),
               "status_counts": {k: sum(1 for r in rows if r["selection_status_final"] == k) for k in sorted({r["selection_status_final"] for r in rows})},
               "rule": "may only make results more conservative; never changes the champion, adds a candidate or creates a claim",
               "outputs_sha256": {n: sha(out / n) for n in ("POST_OPENING_CORRECTIONS.csv", "FULL_EXPERIMENT_LEDGER_CORRECTED.csv")}}
    (out / "POST_OPENING_LOG.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: summary[k] for k in ("n_search_post_opening", "max_t_vs_b2_family", "max_t_vs_b2_below_alpha",
                                              "min_p_max_t_vs_b2", "status_counts")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
