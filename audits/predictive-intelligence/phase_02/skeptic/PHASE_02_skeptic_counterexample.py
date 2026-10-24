"""Phase 02 skeptic counterexamples (independent reviewer, PI-D-013).

Usage:
  python3 -I PHASE_02_skeptic_counterexample.py PHASE02_DIR GAP_MATRIX_CSV ECO_JSON_DIR

Copies the Phase 02 research folder and probes to a temporary directory,
applies one mutation per case, and runs the phase's own
probes/check_candidates.py (offline) on each copy. A case is CAUGHT when the
checker exits non-zero. Nothing is written inside PHASE02_DIR.

Case A is real data, no mutation: TheClimateCorporation/properscoring is
recorded under its pre-transfer path; ecosyste.ms knows the repository as
properscoring/properscoring with archived = true (JSON in ECO_JSON_DIR).
Case B is the new counterexample: a SHORTLISTED repository recorded under a
pre-transfer path, with the mirror lookup 404 and the archived flag lost.
Case C removes the whole event-time (survival, barrier timing) family from the
shortlist. Case D meets a family minimum by relabelling a shortlist row with a
family that differs from its CANDIDATES.csv family.
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile


def read(p):
    with open(p, newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def write(p, fields, rows):
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def add_g_reasons(excl_path, repos):
    text = open(excl_path).read()
    head = "## G. Candidates not shortlisted"
    i = text.index(head)
    j = text.index("|---|---|---|---|", i) + len("|---|---|---|---|")
    extra = "".join("\n| `%s` | X | SKEPTIC_MUTATION | removed by the skeptic counterexample |" % r for r in repos)
    open(excl_path, "w").write(text[:j] + extra + text[j:])


def run_checker(base, gap):
    p = subprocess.run([sys.executable, "-I", os.path.join(base, "probes", "check_candidates.py"), base, gap],
                       capture_output=True, text=True)
    last = [l for l in p.stdout.splitlines() if l.strip()]
    return p.returncode, (last[-1] if last else p.stderr.strip()[-200:])


def fresh(src, tmp, name):
    d = os.path.join(tmp, name)
    shutil.copytree(os.path.join(src, "research"), os.path.join(d, "research"))
    shutil.copytree(os.path.join(src, "probes"), os.path.join(d, "probes"))
    return d


def case_b(d):
    R = os.path.join(d, "research")
    old, new = "projectmesa/mesa", "mesa/mesa"
    f, rows = read(os.path.join(R, "CANDIDATES.csv"))
    for r in rows:
        if r["canonical_repo"] == new:
            # as with properscoring: the successor path was never tried, so it
            # appears nowhere (no same-HEAD path, no section A line)
            r["canonical_repo"], r["url"] = old, "https://github.com/" + old
            r["same_head_paths"] = ""
            r["ecosystems_status"], r["ecosystems_fork"], r["ecosystems_archived"] = "404", "", ""
            r["ecosystems_last_synced_at"], r["activity_flags"] = "", ""
    write(os.path.join(R, "CANDIDATES.csv"), f, rows)
    excl = os.path.join(R, "EXCLUSIONS.md")
    lines = open(excl).read().split("\n")
    open(excl, "w").write("\n".join(l for l in lines if not l.startswith("| `%s` |" % old)))
    ver = os.path.join(R, "VERIFY_RESULTS.jsonl")
    keep = [l for l in open(ver) if l.strip() and json.loads(l).get("input", "").lower() != new]
    open(ver, "w").write("".join(keep))
    f, rows = read(os.path.join(R, "SHORTLIST.csv"))
    for r in rows:
        if r["canonical_repo"] == new:
            r["canonical_repo"] = old
    write(os.path.join(R, "SHORTLIST.csv"), f, rows)


def unshortlist(d, repos):
    R = os.path.join(d, "research")
    f, rows = read(os.path.join(R, "CANDIDATES.csv"))
    for r in rows:
        if r["canonical_repo"] in repos:
            r["shortlisted"] = "no"
    write(os.path.join(R, "CANDIDATES.csv"), f, rows)
    f, rows = read(os.path.join(R, "SHORTLIST.csv"))
    write(os.path.join(R, "SHORTLIST.csv"), f, [r for r in rows if r["canonical_repo"] not in repos])
    add_g_reasons(os.path.join(R, "EXCLUSIONS.md"), repos)


def case_c(d):
    unshortlist(d, ["CamDavidsonPilon/lifelines", "soda-inria/hazardous", "baobach/mlfinpy"])


def case_d(d):
    unshortlist(d, ["NannyML/nannyml", "IFCA-Advanced-Computing/frouros"])
    R = os.path.join(d, "research")
    f, rows = read(os.path.join(R, "SHORTLIST.csv"))
    for r in rows:
        if r["canonical_repo"] == "scikit-learn/scikit-learn":
            r["family"] = "ONLINE_DRIFT_MONITORING"
    write(os.path.join(R, "SHORTLIST.csv"), f, rows)


def main(argv):
    src, gap, eco_dir = argv[1], os.path.abspath(argv[2]), argv[3]
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        d = fresh(src, tmp, "A")
        code, last = run_checker(d, gap)
        eco = json.load(open(os.path.join(eco_dir, "eco_properscoring_properscoring.json")))
        f, rows = read(os.path.join(d, "research", "CANDIDATES.csv"))
        row = next(r for r in rows if r["canonical_repo"].endswith("/properscoring"))
        out.append(("A real row: stale pre-transfer path, archived lost", code,
                    "%s; recorded %s eco_status=%s archived='%s'; ecosyste.ms full_name=%s archived=%s"
                    % (last, row["canonical_repo"], row["ecosystems_status"], row["ecosystems_archived"],
                       eco.get("full_name"), eco.get("archived"))))
        for name, fn, label in (("B", case_b, "B shortlisted repo under pre-transfer path, archived unknown"),
                                ("C", case_c, "C whole event-time family dropped from shortlist"),
                                ("D", case_d, "D family minimum met by a relabelled shortlist row")):
            d = fresh(src, tmp, name)
            fn(d)
            code, last = run_checker(d, gap)
            out.append((label, code, last))
    for label, code, last in out:
        print("%-62s checker exit %d -> %s | %s" % (label, code, "CAUGHT" if code else "NOT CAUGHT", last))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
