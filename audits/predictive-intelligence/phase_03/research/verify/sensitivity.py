"""Phase 03 lead: how the eligible top ten moves under alternative readings of contested rubric items, under the
reviewers' totals and (repair pass) under the blind rescorer's scores for the seven repositories it scored.
Usage: python3 sensitivity.py OUT_JSON. Reads SCORE_ITEMS.csv and SCORECARD.csv; no network.
"""
import csv, json, os, sys
RES = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIE = ["temporal_integrity", "transferable_outcomes", "calibration_uncertainty", "features", "decision_execution",
       "code_quality", "integration_fit", "reproducibility", "license_security", "cost_latency"]
si = list(csv.DictReader(open(os.path.join(RES, "SCORE_ITEMS.csv"))))
card = {r["repo"]: r for r in csv.DictReader(open(os.path.join(RES, "SCORECARD.csv")))}
elig = [r for r in card if card[r]["eligible_for_top10"] == "YES"]
LEAD_R1 = {"statsmodels/statsmodels", "online-ml/river", "sktime/sktime", "IFCA-Advanced-Computing/frouros", "unionai-oss/pandera",
           "scikit-learn-contrib/MAPIE", "baobach/mlfinpy", "deepcharles/ruptures", "probabl-ai/skore", "feast-dev/feast"}
DROPS = {
    "A_calibrator_output_not_O1": {("ip200/venn-abers", "O1")},   # MAPIE O1 is already 0 (veto MA-1, MA-4)
    "B_caller_rules_not_library_mechanism": {("unionai-oss/pandera", "T3"), ("unionai-oss/pandera", "T4a")},
    "C_only_reviewer_repeat_runs_for_R1": {(r, "R1") for r in LEAD_R1},
}
DROPS["E_all_of_A_B_C"] = set().union(*DROPS.values())
# repair pass (prose spot audit): Q2 read strictly, every component of the reviewed role covered by the tests that ran
DROPS["H_strict_Q2_every_role_component_tested"] = {(r, "Q2") for r in (
    "scikit-learn/scikit-learn", "interpretml/interpret", "statsmodels/statsmodels", "scikit-learn-contrib/MAPIE",
    "blue-yonder/tsfresh", "deepcharles/ruptures", "CamDavidsonPilon/lifelines", "soda-inria/hazardous", "mlflow/mlflow")}
# repair pass: readings that ADD points the lead refused, and the blind rescorer's totals
ADDS = {"G_wrapper_probabilities_count": {("sktime/sktime", "O1"): ("transferable_outcomes", 5)}}
BLIND = os.path.join(RES, "BLIND_RESCORE", "PHASE_03_BLIND_RESCORE.csv")
def rank(drop, add=None, override=None):
    sc = {}
    for repo in elig:
        crit = {c: 0 for c in TIE}
        for x in si:
            if x["repo"] == repo and (repo, x["item_id"]) not in drop:
                crit[x["criterion"]] += int(x["points"])
        for (r2, _iid), (c, p) in (add or {}).items():
            if r2 == repo:
                crit[c] += p
        if override and repo in override:
            crit = {c: int(override[repo][c]) for c in TIE}
        sc[repo] = crit
    order = sorted(elig, key=lambda r: tuple([-sum(sc[r].values())] + [-sc[r][c] for c in TIE] + [r.lower()]))
    return [(r, sum(sc[r].values())) for r in order]
out = {"lead": rank(set())[:12]}
for k, v in DROPS.items():
    out[k] = rank(v)[:12]
for k, v in ADDS.items():
    out[k] = rank(set(), v)[:12]
if os.path.exists(BLIND):
    b = {r["repo"]: r for r in csv.DictReader(open(BLIND))}
    out["F_blind_scores_for_the_seven"] = rank(set(), None, b)[:12]
rv = sorted(elig, key=lambda r: (-int(card[r]["reviewer_total"]), r.lower()))
out["D_reviewers_proposed_totals"] = [(r, int(card[r]["reviewer_total"])) for r in rv[:12]]
lead10 = {r for r, _ in out["lead"][:10]}
summary = {}
for k, v in out.items():
    top = [r for r, _ in v[:10]]
    summary[k] = {"top10": top, "enters": sorted(set(top) - lead10), "leaves": sorted(lead10 - set(top)), "rank11_12": v[10:12]}
    print(k, "| enters", summary[k]["enters"], "| leaves", summary[k]["leaves"])
json.dump({"rankings": out, "summary": summary}, open(sys.argv[1], "w"), indent=1)
