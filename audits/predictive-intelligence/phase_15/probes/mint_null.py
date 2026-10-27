"""Phase 15 repair pass 2 (PI-D-082, skeptic CX-S15 and m2, m6, m7): a recorded addition beside the frozen Phase 15 outputs,
which it never rewrites. It can only make statements more conservative.

1. The mint-block nulls (`scenario_eval.clustered_metrics`) beside the recorded decision-level null, for E2 per target and per
   label, for E3 (POST_OPENING) per target and per label; Holm over three on the conservative p values; each verdict is
   `more_conservative` of the recorded one. The decision-level p must equal the recorded one (same seed), else the run stops.
2. The recorded bogus control judged as the single test it is (no family padding), and a bogus warning planted per mint on
   each target.
3. The calibration check of CX-S15: the share of salts in which an outcome-independent per-mint warning gives p < 0.05, for
   the decision null and for the conservative p.
4. N_search primary and sensitivity; ledger rows of this addition; the registry-to-ledger mapping in both directions.

Reads the coding files and labels exactly as `score_scenarios.py` does (git-pinned hashes, `labels.training_labels`, the public
holdout file); never opens `phase_06/sealed/`; no socket (the scorer's audit hook is installed on import).

    python -B mint_null.py OUT_DIR [--dev-store PATH] [--reps 2000] [--salts 400] [--salt-reps 500]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_scenarios as SC  # noqa: E402  (installs the sealed-folder and socket hook)

from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import evaluation as E  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import scenario_eval as S  # noqa: E402

REPO, P15 = SC.REPO, SC.REPO / SC.P15
SHORT, LONG, SEED = SC.SHORT, SC.LONG, SC.SEED
PER_LABEL = (("ATTENTION_EXHAUSTION", L.T2), ("MANUFACTURED_ATTENTION_DUMP", L.T2), ("ORGANIC_ATTENTION_CONTINUATION", L.T1B))
NON_CONFIG_KINDS = {"COUNT": "behavioral/EVENT_SET.csv and CODING_LOG.json event_count",
                    "BLIND_CODING": "behavioral/CODING_LOG.json and the coding files committed in 7b787bf",
                    "NOT_RUN": "INCREMENTAL_VALUE_RESULTS.json comparators and not_compared",
                    "DECISION": "INCREMENTAL_VALUE_RESULTS.json decision (scenario_eval.decide)"}
DEBUG_RUNS = (("P15:DEBUG:RP2:0", "mint-null probe rdbg1 2026-10-27T02:11:51Z to 02:13:27Z at uncommitted repair code into the scratchpad (PI-D-082): every output written; "
               "no rule, threshold, gate, null definition or output definition changed after it"),)


def even(s: str) -> bool:
    return int(hashlib.sha256(s.encode()).hexdigest()[0], 16) % 2 == 0


def same_perm(a: dict | None, b: dict | None) -> bool:
    return (a is None and b is None) or (a is not None and b is not None and all(a[k] == b[k] for k in ("observed_hits", "p_up", "p_down", "reps", "seed")))


def holdout_rows(coding, target, label=None):
    rows = []
    for r in (x for x in SC.csv.DictReader(open(SC.HOLDOUT)) if x["target_short"] == SHORT[target]):
        c = coding.get(("HOLDOUT_WINDOW", r["decision_key"], target))
        if c is None:
            continue
        w = c["warning"]
        if label is not None and w == S.WARN_EVENT and label not in c["labels"].split("|"):
            w = S.WARN_NONE
        rows.append({"y": int(r["y"]), "day": r["day"], "warning": w, "mint": r["mint"], "lead_s": None})
    return rows


def calibration(rows, salts, reps):
    mints = sorted({r["mint"] for r in rows})
    cnt = {"decision": [0, 0], "conservative": [0, 0]}
    for s in range(salts):
        planted = {m for m in mints if even(f"{m}:cx-s15:{s}")}
        c = S.clustered_metrics([{**r, "warning": S.WARN_EVENT if r["mint"] in planted else S.WARN_NONE} for r in rows], reps=reps, seed=SEED)
        if c["decision"] is None:
            continue
        cnt["decision"][0] += c["decision"]["p_up"] < S.ALPHA
        cnt["decision"][1] += c["decision"]["p_down"] < S.ALPHA
        cnt["conservative"][0] += c["p_up_conservative"] < S.ALPHA
        cnt["conservative"][1] += c["p_down_conservative"] < S.ALPHA
    bound = S.ALPHA + 2 * math.sqrt(S.ALPHA * (1 - S.ALPHA) / salts)
    out = {k: {"share_p_up_below_alpha": v[0] / salts, "share_p_down_below_alpha": v[1] / salts} for k, v in cnt.items()}
    worst = max(out["conservative"].values())
    return {"salts": salts, "reps_per_salt": reps, "alpha": S.ALPHA, "bound": bound, **out,
            "verdict": "CALIBRATION_HOLDS" if worst <= bound else "CALIBRATION_FAILED",
            "decision_null_above_bound": max(out["decision"].values()) > bound}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--dev-store", default=SC.DEV_STORE)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--salts", type=int, default=400)
    ap.add_argument("--salt-reps", type=int, default=500)
    a = ap.parse_args()
    out = Path(a.out)
    for d in ("behavioral", "experiments", "evidence"):
        (out / d).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rec = json.loads((P15 / "behavioral/INCREMENTAL_VALUE_RESULTS.json").read_text())
    coding_log, coding, ctrl = SC.load_coding()
    dev_sha = hashlib.sha256(Path(a.dev_store).read_bytes()).hexdigest()
    dev = sqlite3.connect(f"file:{a.dev_store}?mode=ro", uri=True)
    dev.row_factory = sqlite3.Row
    lab_h = {t: SC.label_rows(dev, L.holdout_start(), t) for t in S.PRIMARY}
    res: dict = {"phase": "15", "addition": "repair pass 2 (PI-D-082)", "version": S.MINT_NULL_VERSION, "seed": SEED, "reps": a.reps,
                 "recorded_results_sha256": hashlib.sha256((P15 / "behavioral/INCREMENTAL_VALUE_RESULTS.json").read_bytes()).hexdigest(),
                 "rule": "more conservative only: conservative p = largest of the decision, mint-within-day and whole-sample mint nulls"}
    bad = []
    # 1. E2 and E3
    e2c, dev_rows = {}, {}
    for t in S.PRIMARY:
        rows, _ = SC.warned_rows(lab_h[t], coding, "DEVELOPMENT", t)
        dev_rows[t] = rows
        e2c[t] = S.clustered_metrics(rows, reps=a.reps, seed=SEED)
        if not same_perm(e2c[t]["decision"], rec["E2"][SHORT[t]]["permutation"]):
            bad.append(f"E2 {t}")
    hb = S.conservative_holm_by_target({t: rec["E2"][SHORT[t]] for t in S.PRIMARY}, e2c)
    res["E2"] = {SHORT[t]: {**e2c[t], **hb[t], "verdict_recorded": rec["E2"][SHORT[t]]["verdict"]} for t in S.PRIMARY}
    res["E2_per_label"] = {}
    for lab, t in PER_LABEL:
        rows, _ = SC.warned_rows(lab_h[t], coding, "DEVELOPMENT", t, label_filter=lab)
        c = S.clustered_metrics(rows, reps=a.reps, seed=SEED)
        k = f"{SHORT[t]}:{lab}"
        if not same_perm(c["decision"], rec["E2_per_label"][k]["permutation"]):
            bad.append(f"E2 {k}")
        res["E2_per_label"][k] = {**c, "verdict": "SECONDARY_DESCRIPTION_NO_VERDICT"}
    e3c = {}
    for t in S.PRIMARY:
        e3c[t] = S.clustered_metrics(holdout_rows(coding, t), reps=a.reps, seed=SEED)
        if not same_perm(e3c[t]["decision"], rec["E3_POST_OPENING"][SHORT[t]]["warning_metrics"]["permutation"]):
            bad.append(f"E3 {t}")
    hb3 = S.conservative_holm_by_target({t: rec["E3_POST_OPENING"][SHORT[t]]["warning_metrics"] for t in S.PRIMARY}, e3c)
    res["E3_POST_OPENING"] = {SHORT[t]: {**e3c[t], **hb3[t], "verdict_recorded": rec["E3_POST_OPENING"][SHORT[t]]["warning_metrics"]["verdict"]}
                              for t in S.PRIMARY}
    res["E3_POST_OPENING_per_label"] = {}
    for lab, t in PER_LABEL:
        c = S.clustered_metrics(holdout_rows(coding, t, lab), reps=a.reps, seed=SEED)
        k = f"{SHORT[t]}:{lab}"
        if not same_perm(c["decision"], rec["E3_POST_OPENING_per_label"][k]["permutation"]):
            bad.append(f"E3 {k}")
        res["E3_POST_OPENING_per_label"][k] = {**c, "verdict": rec["E3_POST_OPENING_per_label"][k]["verdict"]}
    # 2. controls
    ncb_rows = []
    for r in lab_h[L.T1]:
        c = ctrl.get(("NCB_VERIFIED", r["decision_key"], L.T1))
        if c is not None:
            ncb_rows.append({"y": int(r["label"]), "day": SC.iso(float(r["decision_time"]))[:10], "warning": c["warning"], "mint": r["mint"],
                             "lead_s": None})
    nc = S.clustered_metrics(ncb_rows, reps=a.reps, seed=SEED)
    if not same_perm(nc["decision"], rec["controls"]["NCB_VERIFIED_T1"]["permutation"]):
        bad.append("NCB")
    res["NCB_VERIFIED_T1_own_level"] = {
        **nc, "recorded_verdict_through_padded_holm": rec["controls"]["NCB_VERIFIED_T1"]["verdict"],
        "decision_null_own_level": S.control_own_level(nc["lift"], nc["decision"]["p_up"], nc["decision"]["p_down"]),
        "conservative_own_level": S.control_own_level(nc["lift"], nc["p_up_conservative"], nc["p_down_conservative"])}
    res["NCB_MINT_PLANTED"] = {}
    for t in S.PRIMARY:
        rows = [{**r, "warning": S.WARN_EVENT if even(f"{r['mint']}:bogus-control-mint") else S.WARN_NONE} for r in dev_rows[t]]
        c = S.clustered_metrics(rows, reps=a.reps, seed=SEED)
        dl = S.control_own_level(c["lift"], c["decision"]["p_up"], c["decision"]["p_down"])
        cl = S.control_own_level(c["lift"], c["p_up_conservative"], c["p_down_conservative"])
        res["NCB_MINT_PLANTED"][SHORT[t]] = {**c, "planted_mints": len({r["mint"] for r in rows if r["warning"] == S.WARN_EVENT}),
                                             "decision_null_own_level": dl, "conservative_own_level": cl,
                                             "ncb_mint_failed": cl == "FLAGGED"}
    # 3. calibration (CX-S15)
    res["CALIBRATION_MINT_PLANTED"] = {SHORT[t]: calibration(dev_rows[t], a.salts, a.salt_reps) for t in S.PRIMARY}
    if bad:
        raise SystemExit(f"the decision-level null differs from the recorded one: {bad}")
    # 4. ledger addition, N_search, mapping
    prior = list(csv.DictReader(open(P15 / "experiments/SEARCH_LEDGER.csv")))
    add_rows = []

    def add(eid, target, cand, kind, view, n_rows="", n_num="", verdict="", claim=""):
        add_rows.append({"phase": "15", "experiment_id": eid, "target": target, "candidate": cand, "kind": kind, "view": view, "seed": SEED,
                         "folds": "", "n_rows": n_rows, "n_with_number": n_num, "verdict": verdict, "split_fingerprint": "",
                         "selection_status": "", "claim": claim})
    for t in S.PRIMARY:
        x = res["E2"][SHORT[t]]
        add(f"P15:RP2:E2:{t}:A_WARNINGS:MINT_NULL", t, "P15_RULES_1_WARNINGS", "DESCRIPTION_ONLY", "DEVELOPMENT_ALL_LABELS_MINT_NULL",
            x["n_scored"], x["n_scored"], x["verdict_conservative"], "NOT_A_CLAIM_MORE_CONSERVATIVE_ONLY")
    for lab, t in PER_LABEL:
        x = res["E2_per_label"][f"{SHORT[t]}:{lab}"]
        add(f"P15:RP2:E2:{t}:LABEL_{lab}:MINT_NULL", t, f"P15_RULES_1_LABEL_{lab}", "DESCRIPTION_ONLY", "DEVELOPMENT_ALL_LABELS_MINT_NULL",
            x["n_scored"], x["n_scored"], x["verdict"], "SECONDARY_DESCRIPTION")
    for t in S.PRIMARY:
        x = res["E3_POST_OPENING"][SHORT[t]]
        add(f"P15:RP2:E3:{t}:A_POST_OPENING:MINT_NULL", t, "P15_RULES_1_WARNINGS", "POST_OPENING_CHECK", "RETROSPECTIVE_HOLDOUT_SPENT_MINT_NULL",
            x["n_scored"], x["n_scored"], x["verdict_conservative"], "POST_OPENING_NOT_A_CLAIM")
    for lab, t in PER_LABEL:
        x = res["E3_POST_OPENING_per_label"][f"{SHORT[t]}:{lab}"]
        add(f"P15:RP2:E3:{t}:LABEL_{lab}_POST_OPENING:MINT_NULL", t, f"P15_RULES_1_LABEL_{lab}", "POST_OPENING_CHECK",
            "RETROSPECTIVE_HOLDOUT_SPENT_MINT_NULL", x["n_scored"], x["n_scored"], x["verdict"], "POST_OPENING_NOT_A_CLAIM")
    x = res["NCB_VERIFIED_T1_own_level"]
    add(f"P15:RP2:NCB:{L.T1}:BOGUS_VERIFIED:OWN_LEVEL", L.T1, "P15_NCB_BOGUS_VERIFIED", "NEGATIVE_CONTROL", "DEVELOPMENT_ALL_LABELS",
        x["n_scored"], x["n_scored"], f"decision {x['decision_null_own_level']}, conservative {x['conservative_own_level']}", "CONTROL")
    for t in S.PRIMARY:
        x = res["NCB_MINT_PLANTED"][SHORT[t]]
        add(f"P15:RP2:NCB:{t}:BOGUS_MINT_PLANTED", t, "P15_NCB_BOGUS_MINT_PLANTED", "NEGATIVE_CONTROL", "DEVELOPMENT_ALL_LABELS",
            x["n_scored"], x["n_scored"], f"decision {x['decision_null_own_level']}, conservative {x['conservative_own_level']}",
            "CONTROL_FAILED" if x["ncb_mint_failed"] else "CONTROL")
    for t in S.PRIMARY:
        x = res["CALIBRATION_MINT_PLANTED"][SHORT[t]]
        add(f"P15:RP2:CALIBRATION:{t}:MINT_PLANTED_NULL", t, "P15_MINT_NULL_CALIBRATION", "TRAP_OR_CHECK", "DEVELOPMENT_ALL_LABELS",
            len(dev_rows[t]), x["salts"], x["verdict"], "CHECK")
    for eid, note in DEBUG_RUNS:
        add(eid, "", "", "DEBUG_RUN_REAL_DATA", "", verdict=note)
    full = prior + add_rows
    tot = E.ledger_totals(full)
    rec_tot = json.loads((P15 / "experiments/LEDGER_TOTALS.json").read_text())
    rules = E.rule_configurations(full)
    if tot["n_search"] != rec_tot["after"]["n_search"] or rules != rec_tot["rule_configurations_after"]:
        raise SystemExit("the addition changed N_search or the rule configurations")
    res["n_search"] = {"primary": tot["n_search"], "rule_configurations": rules, "sensitivity": tot["n_search"] + rules,
                       "note": "primary = protocol 11 (118 + A_WARN on three targets); sensitivity = primary + non-probability rule and "
                               "description configurations, the like-for-like of Phase 12's post-opening 127 (PI-D-066 item 4)"}
    res["ledger_after_addition"] = tot
    reg = list(csv.DictReader(open(P15 / "experiments/EXPERIMENT_REGISTRY.csv"))) + \
        list(csv.DictReader(open(P15 / "experiments/EXPERIMENT_REGISTRY_RP2.csv")))
    led15 = [r for r in full if r["phase"] == "15"]
    led_ids = {r["experiment_id"] for r in led15}
    reg_ids = {r["experiment_id"] for r in reg}
    mp = []
    for r in reg:
        i = r["experiment_id"]
        if i in led_ids:
            mp.append({"direction": "REGISTRY_TO_LEDGER", "registry_id": i, "ledger_id": i, "basis": "SAME_ID"})
        elif r["kind"] in NON_CONFIG_KINDS:
            mp.append({"direction": "REGISTRY_TO_LEDGER", "registry_id": i, "ledger_id": "",
                       "basis": f"NO_LEDGER_ROW_NOT_A_SEARCH_CONFIGURATION ({r['kind']}); recorded in {NON_CONFIG_KINDS[r['kind']]}"})
        else:
            raise SystemExit(f"registry row {i} has no ledger row")
    for r in led15:
        i = r["experiment_id"]
        if i in reg_ids:
            basis = "SAME_ID"
        elif r["kind"] == "DEBUG_RUN_REAL_DATA":
            basis = "DEBUG_RUN_REAL_DATA: logged runs (protocol 11), never registered in advance"
        elif i.endswith(":A_WARN_H_POST_OPENING"):
            basis = "POST_OPENING_CHECK declared in protocol 6 (E3: A_WARN fitted at the holdout start), not given a registry row"
        elif i.endswith("_POST_OPENING") and ":LABEL_" in i:
            basis = "POST_OPENING_CHECK added by change control CP15-0 (PI-D-080), not given a registry row"
        else:
            raise SystemExit(f"ledger row {i} has no registry basis")
        mp.append({"direction": "LEDGER_TO_REGISTRY", "registry_id": i if i in reg_ids else "", "ledger_id": i, "basis": basis})
    files = {"behavioral/MINT_CLUSTERED_NULL.json": SC.jdump(res),
             "experiments/SEARCH_LEDGER_RP2_ADDITION.csv": SC.csv_text(add_rows),
             "experiments/REGISTRY_LEDGER_MAP.csv": SC.csv_text(mp)}
    for k, v in files.items():
        (out / k).write_text(v)
    log = {"script": f"{SC.P15}/probes/mint_null.py", "start_utc": SC.iso(t0), "end_utc": SC.iso(time.time()),
           "head": SC.git("rev-parse", "HEAD").strip(), "dev_store_sha256": dev_sha, "reps": a.reps, "salts": a.salts,
           "salt_reps": a.salt_reps, "sockets": SC.SOCKETS, "sealed_opens": SC.SEALED,
           "outputs_sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in files.items()}}
    (out / "evidence/mint_null_run_log.json").write_text(SC.jdump(log))
    print(json.dumps({"E2": {k: (v["p_up_conservative"], v["verdict_conservative"]) for k, v in res["E2"].items()},
                      "NCB_own": {k: res["NCB_VERIFIED_T1_own_level"][k] for k in ("decision_null_own_level", "conservative_own_level")},
                      "NCB_mint": {k: (v["decision_null_own_level"], v["conservative_own_level"]) for k, v in res["NCB_MINT_PLANTED"].items()},
                      "calibration": {k: (v["decision"], v["conservative"], v["verdict"]) for k, v in res["CALIBRATION_MINT_PLANTED"].items()},
                      "n_search": res["n_search"], "map_rows": len(mp)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
