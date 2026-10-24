"""Phase 03 lead: negative tests for check_scorecard.py (19 first-pass mutations, 12 added in the repair pass). Each mutation is applied to a fresh copy of the research
files in a temporary directory and must be refused by the rule it targets (EXPECT names the expected message). Usage: python3 check_scorecard_negative.py
"""
import csv, io, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import check_scorecard as CS  # noqa: E402

FILES = ["RUBRIC_ITEMS.csv", "SCORE_ITEMS.csv", "SCORECARD.csv", "RANKED_TOP10.md"]

def load(d, name):
    return list(csv.DictReader(open(os.path.join(d, name))))

def save(d, name, rows):
    with open(os.path.join(d, name), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def copy():
    d = tempfile.mkdtemp(prefix="p03neg_")
    for f in FILES:
        shutil.copy(os.path.join(RES, f), d)
    os.symlink(os.path.join(RES, "REVIEWS"), os.path.join(d, "REVIEWS"))
    os.symlink(os.path.join(RES, "SMOKES"), os.path.join(d, "SMOKES"))
    os.symlink(os.path.join(RES, "verify"), os.path.join(d, "verify"))
    return d

def item(d, repo, iid, **kw):
    rows = load(d, "SCORE_ITEMS.csv")
    for r in rows:
        if r["repo"] == repo and r["item_id"] == iid:
            r.update({k: str(v) for k, v in kw.items()})
    save(d, "SCORE_ITEMS.csv", rows)

def card(d, repo, **kw):
    rows = load(d, "SCORECARD.csv")
    for r in rows:
        if r["repo"] == repo:
            r.update({k: str(v) for k, v in kw.items()})
    save(d, "SCORECARD.csv", rows)

def bump(d, repo, crit, delta):
    rows = load(d, "SCORECARD.csv")
    for r in rows:
        if r["repo"] == repo:
            r["lead_" + crit] = str(int(r["lead_" + crit]) + delta)
            r["lead_total"] = str(int(r["lead_total"]) + delta)
    save(d, "SCORECARD.csv", rows)

def award(d, repo, iid, pts, evidence, crit):
    item(d, repo, iid, points=pts, evidence=evidence)
    bump(d, repo, crit, pts)

def m_wrong_criterion_sum(d):
    rows = load(d, "SCORECARD.csv"); rows[0]["lead_features"] = str(int(rows[0]["lead_features"]) + 1); save(d, "SCORECARD.csv", rows)
def m_wrong_total(d):
    rows = load(d, "SCORECARD.csv"); rows[1]["lead_total"] = str(int(rows[1]["lead_total"]) + 3); save(d, "SCORECARD.csv", rows)
def m_over_max(d):
    bump(d, "scikit-learn/scikit-learn", "license_security", 1)
def m_point_without_evidence(d):
    item(d, "scikit-learn/scikit-learn", "Q1", evidence="")
def m_partial_item(d):
    item(d, "scikit-learn/scikit-learn", "T1", points=1)
    bump(d, "scikit-learn/scikit-learn", "temporal_integrity", -2)
def m_swapped_ranks(d):
    rows = load(d, "SCORECARD.csv"); a, b = rows[0]["eligible_rank"], rows[1]["eligible_rank"]
    rows[0]["eligible_rank"], rows[1]["eligible_rank"] = b, a; save(d, "SCORECARD.csv", rows)
def m_reject_ranked(d):
    card(d, "baobach/mlfinpy", eligible_for_top10="YES", eligible_rank="31")
def m_readme_only_point(d):  # P42
    award(d, "mesa/mesa", "T1", 3, "REVIEWS/mesa__mesa.md README: agents are time-aware", "temporal_integrity")
def m_readme_hundred(d):  # P42: a candidate scoring 100 from its README
    rows = load(d, "SCORE_ITEMS.csv")
    for r in rows:
        if r["repo"] == "666ghj/MiroFish":
            r["points"] = r["item_points"]; r["evidence"] = "REVIEWS/666ghj__MiroFish.md README: Predicting Anything, precise future trajectories"
    save(d, "SCORE_ITEMS.csv", rows)
    card(d, "666ghj/MiroFish", **{"lead_" + c: w for c, w in CS.locked_weights().items()}, lead_total=100)
def m_agpl_install(d):  # P31
    card(d, "666ghj/MiroFish", integration_decision="INSTALL")
def m_agpl_l1(d):  # P31
    award(d, "bancaditalia/black-it", "L1", 3, "REVIEWS/bancaditalia__black-it.md s2 license", "license_security")
def m_swarm_probability(d):  # P27
    award(d, "mesa/mesa", "O1", 5, "SMOKES/mesa__mesa/smoke_mesa_traders_output.json share of runs that hit", "transferable_outcomes")
def m_llm_temporal(d):  # P26
    award(d, "camel-ai/oasis", "T6", 2, "SMOKES/camel-ai__oasis/smoke_run1.json post_created_at", "temporal_integrity")
def m_chrono_from_prose(d):  # P13 guard
    award(d, "lightgbm-org/LightGBM", "T6", 2, "REVIEWS/lightgbm-org__LightGBM.md s3 text model embeds parameters", "temporal_integrity")
def m_missing_row(d):
    rows = [r for r in load(d, "SCORE_ITEMS.csv") if not (r["repo"] == "ip200/venn-abers" and r["item_id"] == "K4")]
    save(d, "SCORE_ITEMS.csv", rows)
def m_bad_path(d):
    item(d, "online-ml/river", "Q1", evidence="SMOKES/online-ml__river/does_not_exist.txt 161 passed")
def m_top10_table(d):
    t = open(os.path.join(d, "RANKED_TOP10.md")).read()
    lines = t.splitlines()
    idx = [i for i, l in enumerate(lines) if l.startswith("| 1 |") or l.startswith("| 2 |")]
    if len(idx) == 2:
        lines[idx[0]], lines[idx[1]] = lines[idx[1]], lines[idx[0]]
    open(os.path.join(d, "RANKED_TOP10.md"), "w").write("\n".join(lines) + "\n")
def m_award_against_finding(d):  # the lead's counterexample: a resolvable but false award
    award(d, "scikit-learn-contrib/MAPIE", "C2", 3, "SMOKES/scikit-learn-contrib__MAPIE/raw_smoke_mapie.txt Venn-Abers fit on the later window", "calibration_uncertainty")
def m_weight_changed(d):
    rows = load(d, "RUBRIC_ITEMS.csv")
    for r in rows:
        if r["item_id"] == "T1":
            r["points"] = "4"
    save(d, "RUBRIC_ITEMS.csv", rows)

# ---- repair pass: the skeptic's accepted mutations (skeptic/p03/skeptic_mutations.py) and the new rules ----
def m_readme_at_pin(d):  # skeptic check 6: README at the pin
    award(d, "mesa/mesa", "D2", 3, "pin:mesa__mesa/README.md:1 README says thresholds are tuned", "decision_execution")
def m_docs_at_pin(d):  # skeptic check 6: docs page at the pin, no README keyword
    award(d, "blue-yonder/tsfresh", "T2", 4, "pin:blue-yonder__tsfresh/docs/text/faq.rst:1 docs say windows are rolled forward; SMOKES/blue-yonder__tsfresh/ raw", "temporal_integrity")
def m_t1_from_prose(d):  # skeptic check 6: T1 from review prose
    award(d, "mesa/mesa", "T1", 3, "REVIEWS/mesa__mesa.md s4 walk-forward", "temporal_integrity")
def m_t3_from_prose(d):  # skeptic check 6: T3 from review prose
    award(d, "deepcharles/ruptures", "T3", 2, "REVIEWS/deepcharles__ruptures.md s4 handles pending labels", "temporal_integrity")
def m_fabricated_existing_file(d):  # skeptic check 6: existing raw file that says nothing about the item
    first = sorted(os.listdir(os.path.join(RES, "SMOKES", "probabl-ai__skore")))[0]
    award(d, "probabl-ai/skore", "C4", 2, "SMOKES/probabl-ai__skore/%s coverage 0.90 measured" % first, "calibration_uncertainty")
def m_prose_only_smoke_item(d):  # m1: review prose alone on an item that needs raw output
    item(d, "scikit-learn/scikit-learn", "K1", evidence="REVIEWS/scikit-learn__scikit-learn.md s4 offline")
def m_group_split_empty(d):  # the skeptic's counterexample: group split certified by overlap counts alone
    award(d, "eslazarev/purged-cross-validation", "O5", 2, "verify/rerun_purgedcv.out.txt PurgedGroupKFold_shared_mints [0, 0, 0, 0, 0]", "transferable_outcomes")
def m_group_split_with_audit(d):  # same, citing the fold audit: two empty training folds
    award(d, "eslazarev/purged-cross-validation", "O5", 2, "verify/rerun_purgedcv.out.txt PurgedGroupKFold_shared_mints [0, 0, 0, 0, 0]; fold_audit:purgedcv.PurgedGroupKFold", "transferable_outcomes")
def m_future_trained_t2(d):  # purge credited to a splitter that trains on later rows
    item(d, "eslazarev/purged-cross-validation", "T2", evidence="verify/rerun_purgedcv.out.txt PurgedKFold_leaks [0, 0, 0, 0, 0]; fold_audit:purgedcv.PurgedKFold")
def m_mapie_o1(d):  # M2: probability point resting on the defective Venn-Abers port
    award(d, "scikit-learn-contrib/MAPIE", "O1", 5, "SMOKES/scikit-learn-contrib__MAPIE/raw_smoke_mapie.txt Venn-Abers calibrator output p0p1 (527,2), merged probability", "transferable_outcomes")
def m_wrapper_probability(d):  # m5: probabilities of a wrapped third-party estimator
    award(d, "sktime/sktime", "O1", 5, "SMOKES/sktime__sktime/smoke_sktime.result.json SklearnClassifierPipeline proba_shape [87,2] finite", "transferable_outcomes")
def m_hazardous_recalibration(d):  # m4: recalibration with a confirmed definition error
    award(d, "soda-inria/hazardous", "C2", 3, "SMOKES/soda-inria__hazardous/smoke_hazardous.result.json recalibrate_survival_function_val_to_holdout outside_0_1 0", "calibration_uncertainty")

EXPECT = {"m_over_max": "outside 0..", "m_readme_only_point": "P42", "m_readme_hundred": "P42", "m_agpl_install": "P31", "m_agpl_l1": "P31",
          "m_swarm_probability": "P27", "m_llm_temporal": "P26", "m_chrono_from_prose": "P13", "m_reject_ranked": "REJECT",
          "m_partial_item": "partial", "m_point_without_evidence": "without evidence", "m_missing_row": "missing SCORE_ITEMS",
          "m_bad_path": "does not resolve", "m_top10_table": "RANKED_TOP10", "m_swapped_ranks": "rank of", "m_weight_changed": "do not sum",
          "m_wrong_total": "total of", "m_wrong_criterion_sum": "items sum to", "m_award_against_finding": "verified finding",
          "m_readme_at_pin": "P42 at the pin", "m_docs_at_pin": "P42 at the pin", "m_t1_from_prose": "P13", "m_t3_from_prose": "P13",
          "m_fabricated_existing_file": "ANCHOR", "m_prose_only_smoke_item": "evidence rule", "m_group_split_empty": "FOLD: splitter evidence without",
          "m_group_split_with_audit": "a training fold has 0 rows", "m_future_trained_t2": "rows decided after the test start",
          "m_mapie_o1": "verified finding MA-1", "m_wrapper_probability": "verified finding ST-4", "m_hazardous_recalibration": "verified finding HZ-3"}

MUTATIONS = [m_wrong_criterion_sum, m_wrong_total, m_over_max, m_point_without_evidence, m_partial_item, m_swapped_ranks,
             m_reject_ranked, m_readme_only_point, m_readme_hundred, m_agpl_install, m_agpl_l1, m_swarm_probability,
             m_llm_temporal, m_chrono_from_prose, m_missing_row, m_bad_path, m_top10_table, m_weight_changed, m_award_against_finding,
             m_readme_at_pin, m_docs_at_pin, m_t1_from_prose, m_t3_from_prose, m_fabricated_existing_file, m_prose_only_smoke_item,
             m_group_split_empty, m_group_split_with_audit, m_future_trained_t2, m_mapie_o1, m_wrapper_probability,
             m_hazardous_recalibration]

def main():
    base = copy()
    assert not CS.check(base), "unmutated copy must pass"
    shutil.rmtree(base)
    refused = 0
    for m in MUTATIONS:
        d = copy()
        m(d)
        e = CS.check(d)
        hit = [x for x in e if EXPECT[m.__name__] in x]
        ok = bool(hit)
        refused += ok
        print("%-28s %s  %s" % (m.__name__, "REFUSED" if ok else "NOT REFUSED BY THE EXPECTED RULE", (hit or e or [""])[0][:100]))
        shutil.rmtree(d)
    print("%d of %d mutations refused" % (refused, len(MUTATIONS)))
    return 0 if refused == len(MUTATIONS) else 1

if __name__ == "__main__":
    sys.exit(main())
