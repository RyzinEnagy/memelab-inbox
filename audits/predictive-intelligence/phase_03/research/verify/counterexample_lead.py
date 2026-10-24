"""Phase 03 lead's own wrong-but-plausible counterexample (not independent; PI-D-013 skeptic still owed).

A consistent author awards MAPIE the recalibration item C2 (3 points) with a real, resolvable evidence line ("Venn-Abers
fit on the later calibration window"), rebuilds the scorecard and ranks so that every sum and sort is right. The claim
is false: the lead's check MA-1/MA-2 shows MAPIE's Venn-Abers port fails the definition above the calibration range.
Before the verified-finding veto (check_scorecard.VETO) the checker accepted this; after it, the checker refuses it.
Usage: python3 -B counterexample_lead.py   (prints the checker's result on the mutated copy)
"""
import csv, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import check_scorecard as CS  # noqa: E402
d = tempfile.mkdtemp(prefix="p03cx_")
for f in ("RUBRIC_ITEMS.csv", "SCORE_ITEMS.csv", "SCORECARD.csv"):
    shutil.copy(os.path.join(RES, f), d)
for f in ("REVIEWS", "SMOKES", "verify"):
    os.symlink(os.path.join(RES, f), os.path.join(d, f))
with open(os.path.join(d, "SCORE_ITEMS.csv")) as fh:
    rows = list(csv.DictReader(fh))
for r in rows:
    if r["repo"] == "scikit-learn-contrib/MAPIE" and r["item_id"] == "C2":
        r["points"] = "3"; r["evidence"] = "SMOKES/scikit-learn-contrib__MAPIE/raw_smoke_mapie.txt Venn-Abers fit on the later calibration window (prefit)"
with open(os.path.join(d, "SCORE_ITEMS.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(rows)
with open(os.path.join(d, "SCORECARD.csv")) as fh:
    card = list(csv.DictReader(fh))
for r in card:
    if r["repo"] == "scikit-learn-contrib/MAPIE":
        r["lead_calibration_uncertainty"] = str(int(r["lead_calibration_uncertainty"]) + 3); r["lead_total"] = str(int(r["lead_total"]) + 3)
elig = [r for r in card if r["eligible_for_top10"] == "YES"]
elig.sort(key=lambda r: tuple([-int(r["lead_total"])] + [-int(r["lead_" + c]) for c in CS.TIE_ORDER] + [r["repo"].lower()]))
for i, r in enumerate(elig, 1):
    r["eligible_rank"] = str(i)
with open(os.path.join(d, "SCORECARD.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(card[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(card)
e = CS.check(d)
print("MAPIE C2 awarded against MA-1/MA-2, ranks rebuilt (MAPIE now rank %s): problems %d" % (next(r["eligible_rank"] for r in card if r["repo"] == "scikit-learn-contrib/MAPIE"), len(e)))
for x in e:
    print("  ", x)
shutil.rmtree(d)
sys.exit(0 if e else 1)
