"""Skeptic P03: extra mutations against the lead's check_scorecard.check(), on copies of research/.
Usage: python3 -B skeptic_mutations.py <research_dir>
Each mutation reports REFUSED (checker found a problem) or ACCEPTED (checker passed the mutated copy)."""
import csv, os, shutil, sys, tempfile, importlib.util

RES = os.path.abspath(sys.argv[1])
spec = importlib.util.spec_from_file_location("cs", os.path.join(RES, "verify", "check_scorecard.py"))
cs = importlib.util.module_from_spec(spec); spec.loader.exec_module(cs)

def load(p):
    with open(p, newline="") as f:
        r = csv.DictReader(f); return r.fieldnames, list(r)

def save(p, fn, rows):
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn); w.writeheader(); w.writerows(rows)

def award(d, repo, item, evidence):
    fn, si = load(os.path.join(d, "SCORE_ITEMS.csv"))
    pts = crit = None
    for r in si:
        if r["repo"] == repo and r["item_id"] == item:
            r["points"] = r["item_points"]; r["evidence"] = evidence; pts = int(r["item_points"]); crit = r["criterion"]
    save(os.path.join(d, "SCORE_ITEMS.csv"), fn, si)
    fn, sc = load(os.path.join(d, "SCORECARD.csv"))
    for r in sc:
        if r["repo"] == repo:
            r["lead_" + crit] = str(int(r["lead_" + crit]) + pts); r["lead_total"] = str(int(r["lead_total"]) + pts)
    rerank(sc)
    save(os.path.join(d, "SCORECARD.csv"), fn, sc)

def rerank(sc):
    # a consistent forger also re-sorts the ranks with the lead's own rule
    el = [r for r in sc if r["eligible_for_top10"] == "YES"]
    key = lambda r: tuple([-int(r["lead_total"])] + [-int(r["lead_" + c]) for c in cs.TIE_ORDER] + [r["repo"].lower()])
    for i, r in enumerate(sorted(el, key=key), 1):
        r["eligible_rank"] = str(i)

def remove(d, repo, item):
    fn, si = load(os.path.join(d, "SCORE_ITEMS.csv"))
    for r in si:
        if r["repo"] == repo and r["item_id"] == item:
            pts = int(r["points"]); crit = r["criterion"]; r["points"] = "0"; r["evidence"] = "no qualifying evidence (unanswered = 0)"
    save(os.path.join(d, "SCORE_ITEMS.csv"), fn, si)
    fn, sc = load(os.path.join(d, "SCORECARD.csv"))
    for r in sc:
        if r["repo"] == repo:
            r["lead_" + crit] = str(int(r["lead_" + crit]) - pts); r["lead_total"] = str(int(r["lead_total"]) - pts)
    save(os.path.join(d, "SCORECARD.csv"), fn, sc)

def edit_total(d, repo, delta):
    fn, sc = load(os.path.join(d, "SCORECARD.csv"))
    for r in sc:
        if r["repo"] == repo: r["lead_total"] = str(int(r["lead_total"]) + delta)
    save(os.path.join(d, "SCORECARD.csv"), fn, sc)

MUT = {
 # a lone score edit in the scorecard: must be refused
 "s_total_plus_one_sklearn": lambda d: edit_total(d, "scikit-learn/scikit-learn", 1),
 # fabricated point, evidence is an existing raw file that says nothing about the item (content not checked)
 "s_fabricated_point_existing_file": lambda d: award(d, "probabl-ai/skore", "C4",
      "SMOKES/probabl-ai__skore/" + sorted(os.listdir(os.path.join(d, "SMOKES", "probabl-ai__skore")))[0] + " coverage 0.90 measured"),
 # P42 hole: a point resting only on a README at the pin
 "s_readme_at_pin": lambda d: award(d, "mesa/mesa", "D2", "pin:mesa__mesa/README.md:1 README says thresholds are tuned"),
 # P42 hole: docs page at the pin, no README keyword
 "s_docs_at_pin": lambda d: award(d, "blue-yonder/tsfresh", "T2", "pin:blue-yonder__tsfresh/docs/text/faq.rst:1 docs say windows are rolled forward; SMOKES/blue-yonder__tsfresh/ raw"),
 # chronology item T1 or T3 from review prose (P13 guard covers only T2, T4a, T5, T6)
 "s_T3_from_review_prose": lambda d: award(d, "deepcharles/ruptures", "T3", "REVIEWS/deepcharles__ruptures.md s4 handles pending labels"),
 "s_T1_from_review_prose": lambda d: award(d, "mesa/mesa", "T1", "REVIEWS/mesa__mesa.md s4 walk-forward"),
}
for name, fn in MUT.items():
    tmp = tempfile.mkdtemp(prefix="skp03_")
    d = os.path.join(tmp, "research"); shutil.copytree(RES, d)
    try:
        fn(d)
        e = cs.check(d)
        print("%-34s %s  %s" % (name, "REFUSED " if e else "ACCEPTED", (e[0][:110] if e else "")))
    finally:
        shutil.rmtree(tmp)

# MAPIE O1 under the lead's own veto principle: remove O1 and see the cut
tmp = tempfile.mkdtemp(prefix="skp03_"); d = os.path.join(tmp, "research"); shutil.copytree(RES, d)
remove(d, "scikit-learn-contrib/MAPIE", "O1")
_, sc = load(os.path.join(d, "SCORECARD.csv"))
el = [r for r in sc if r["eligible_for_top10"] == "YES"]
key = lambda r: tuple([-int(r["lead_total"])] + [-int(r["lead_" + c]) for c in cs.TIE_ORDER] + [r["repo"].lower()])
print("top ten without MAPIE O1:", [(r["repo"], r["lead_total"]) for r in sorted(el, key=key)[:12]])
shutil.rmtree(tmp)
