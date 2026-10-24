"""Phase 03 lead: build SCORE_ITEMS.csv, SCORECARD.csv and the eligible ranking from RUBRIC_ITEMS.csv and
score_inputs.py. Deterministic; no network. Usage: python3 build_scorecard.py
Ranking rule (written before the first build): eligible rows only (no hard-veto REJECT for the recommended route),
sorted by total descending; ties broken by the criteria in descending locked weight (temporal 18, outcomes 14,
calibration 12, features 10, decision 10, code 8, integration 8, reproducibility 8, license 7, cost 5), then by
canonical repository name ascending.
"""
import csv, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import score_inputs as SI  # noqa: E402

CRITERIA = ["temporal_integrity", "transferable_outcomes", "calibration_uncertainty", "features", "decision_execution",
            "code_quality", "integration_fit", "reproducibility", "cost_latency", "license_security"]
SHORT = {"temporal_integrity": "T", "transferable_outcomes": "O", "calibration_uncertainty": "C", "features": "F",
         "decision_execution": "D", "code_quality": "Q", "integration_fit": "I", "reproducibility": "R",
         "cost_latency": "K", "license_security": "L"}
TIE_ORDER = ["temporal_integrity", "transferable_outcomes", "calibration_uncertainty", "features", "decision_execution",
             "code_quality", "integration_fit", "reproducibility", "license_security", "cost_latency"]
CATEGORY = {  # Phase 03 category for CATEGORY_WINNERS.md (from the Phase 02 family and the reviewed role)
    "scikit-learn/scikit-learn": "supervised_tabular", "lightgbm-org/LightGBM": "supervised_tabular",
    "interpretml/interpret": "supervised_tabular", "PriorLabs/TabPFN": "supervised_tabular",
    "statsmodels/statsmodels": "supervised_tabular",
    "sktime/sktime": "time_series", "blue-yonder/tsfresh": "time_series", "deepcharles/ruptures": "time_series",
    "stumpy-dev/stumpy": "time_series",
    "online-ml/river": "online_incremental",
    "scikit-learn-contrib/MAPIE": "calibration_uncertainty", "henrikbostrom/crepes": "calibration_uncertainty",
    "ip200/venn-abers": "calibration_uncertainty", "lorentzenchr/model-diagnostics": "calibration_uncertainty",
    "bashtage/arch": "calibration_uncertainty",
    "CamDavidsonPilon/lifelines": "onchain_anomaly_event_time", "soda-inria/hazardous": "onchain_anomaly_event_time",
    "baobach/mlfinpy": "onchain_anomaly_event_time", "feast-dev/feast": "onchain_anomaly_event_time",
    "666ghj/MiroFish": "behavioral_multi_agent", "camel-ai/oasis": "behavioral_multi_agent", "mesa/mesa": "behavioral_multi_agent",
    "bancaditalia/black-it": "behavioral_multi_agent",
    "evidentlyai/evidently": "evaluation_monitoring", "NannyML/nannyml": "evaluation_monitoring",
    "IFCA-Advanced-Computing/frouros": "evaluation_monitoring", "mlflow/mlflow": "evaluation_monitoring",
    "probabl-ai/skore": "evaluation_monitoring", "unionai-oss/pandera": "evaluation_monitoring",
    "eslazarev/purged-cross-validation": "evaluation_monitoring",
}

def reviewer_scores(path):
    t = open(path, encoding="utf-8").read()
    s = t[t.index("## 6"):]
    s = s[:s.index("## 7")]
    vals, total = [], None
    for ln in s.splitlines():
        if not ln.startswith("|") or set(ln.replace("|", "").strip()) <= set("-: ") or re.search(r"Criterion", ln):
            continue
        cells = [c.strip().strip("*") for c in ln.strip("|").split("|")]
        nums = [c for c in cells[1:] if re.fullmatch(r"\d+", c)]
        if cells[0].lower().startswith("total"):
            total = int(nums[-1])
        else:
            vals.append(int(nums[-1]))
    assert len(vals) == 10 and sum(vals) == total, (path, vals, total)
    return vals, total

GENERIC = {"Q3": "Q3_check", "L1": "L1_check", "L3": "L3_check", "K4": "K4_check"}

def generic_refs():
    """Repair pass (skeptic m1): items the lead's generic verifier re-derived for all 30 repositories cite its output."""
    p = os.path.join(HERE, "VERIFY_GENERIC.json")
    out = {}
    if os.path.exists(p):
        import json
        for r in json.load(open(p)):
            for iid, key in GENERIC.items():
                if r.get(key) is True and not r.get("award_mismatches"):
                    out[(r["repo"], iid)] = "verify/VERIFY_GENERIC.json %s %s true" % (r["repo"], key)
    return out

def main():
    gref = generic_refs()
    items = list(csv.DictReader(open(os.path.join(RES, "RUBRIC_ITEMS.csv"))))
    short = list(csv.DictReader(open(os.path.join(RES, "..", "..", "phase_02", "research", "SHORTLIST.csv"))))
    repos = [r["canonical_repo"] for r in short]
    assert set(r.replace("/", "__") for r in repos) == set(SI.AW), "score_inputs does not cover the shortlist exactly"
    item_ids = {it["item_id"] for it in items}
    rows_items, card = [], []
    for repo in repos:
        key = repo.replace("/", "__")
        aw = SI.AW[key]
        unknown = set(aw) - item_ids
        assert not unknown, (key, unknown)
        rv, rtot = reviewer_scores(os.path.join(RES, "REVIEWS", key + ".md"))
        crit = {c: 0 for c in CRITERIA}
        awarded = []
        for it in items:
            iid, c, pts = it["item_id"], it["criterion"], int(it["points"])
            if iid in aw:
                evid, chk = aw[iid]
                assert evid.strip(), (key, iid)
                if (repo, iid) in gref:
                    evid = evid + "; " + gref[(repo, iid)]
                p = pts
                awarded.append(iid)
            else:
                evid, chk, p = "", "", 0
            crit[c] += p
            notes = SI.ZERO_NOTES.get(key, {})
            note = "" if p else (notes.get(SHORT[c], "") or notes.get("all", ""))
            rows_items.append({"repo": repo, "item_id": iid, "criterion": c, "item_points": pts, "points": p,
                               "evidence": evid if p else "no qualifying evidence (unanswered = 0)", "verify_checks": chk, "note": note})
        total = sum(crit.values())
        flags = SI.FLAGS[key]
        ineligible = flags.startswith("REJECT (") and SI.DECISION[key] == "REJECT"
        row = {"repo": repo, "category": CATEGORY[repo], "phase02_family": next(r["family"] for r in short if r["canonical_repo"] == repo),
               "pinned_sha": next(r["pinned_sha"] for r in short if r["canonical_repo"] == repo),
               "license_at_pin": next(r["license"] for r in short if r["canonical_repo"] == repo)}
        for c, v in zip(CRITERIA, rv):
            row["lead_" + c] = crit[c]
            row["reviewer_" + c] = v
        row.update({"lead_total": total, "reviewer_total": rtot, "lead_minus_reviewer": total - rtot,
                    "items_awarded": " ".join(awarded), "flags": flags,
                    "eligible_for_top10": "NO" if ineligible else "YES",
                    "recommended_route": SI.ROUTE[key], "integration_decision": SI.DECISION[key]})
        card.append(row)
    elig = [r for r in card if r["eligible_for_top10"] == "YES"]
    elig.sort(key=lambda r: tuple([-r["lead_total"]] + [-r["lead_" + c] for c in TIE_ORDER] + [r["repo"].lower()]))
    for i, r in enumerate(elig, 1):
        r["eligible_rank"] = i
    for r in card:
        r.setdefault("eligible_rank", "")
    card.sort(key=lambda r: (r["eligible_rank"] == "", r["eligible_rank"] if r["eligible_rank"] != "" else 0, r["repo"].lower()))
    cols = ["eligible_rank", "repo", "category", "phase02_family", "pinned_sha", "license_at_pin"]
    for c in CRITERIA:
        cols += ["lead_" + c, "reviewer_" + c]
    cols += ["lead_total", "reviewer_total", "lead_minus_reviewer", "eligible_for_top10", "flags", "integration_decision", "recommended_route", "items_awarded"]
    with open(os.path.join(RES, "SCORECARD.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in card:
            w.writerow(r)
    with open(os.path.join(RES, "SCORE_ITEMS.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["repo", "item_id", "criterion", "item_points", "points", "evidence", "verify_checks", "note"], lineterminator="\n")
        w.writeheader()
        for r in rows_items:
            w.writerow(r)
    for r in card:
        print("%-3s %-40s %3d (reviewer %3d, %+d) %s" % (r["eligible_rank"], r["repo"], r["lead_total"], r["reviewer_total"], r["lead_minus_reviewer"], r["eligible_for_top10"]))

if __name__ == "__main__":
    main()
