"""Negative tests for check_candidates.py: every mutation must be refused.

Usage: python check_candidates_negative.py PHASE02_DIR GAP_MATRIX_CSV

Copies research/ to a temporary folder, applies one mutation at a time,
runs the checker offline and requires exit 1 with the expected message.
Also runs the unmutated copy, which must pass. Prints one line per case.
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def rd(p):
    with open(p) as f:
        r = list(csv.DictReader(f))
    return r


def wr(p, rows, fields=None):
    fields = fields or list(rows[0].keys())
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def C(d):
    return os.path.join(d, "research", "CANDIDATES.csv")


def S(d):
    return os.path.join(d, "research", "SHORTLIST.csv")


def edit(path, fn):
    rows = rd(path)
    rows, fields = fn(rows)
    wr(path, rows, fields)


def m_dup(d, g):
    edit(C(d), lambda r: (r + [dict(r[5])], None))


def m_fork(d, g):
    edit(C(d), lambda r: ([dict(x, ecosystems_fork="true") if i == 3 else x for i, x in enumerate(r)], None))


def m_badsha(d, g):
    edit(C(d), lambda r: ([dict(x, pinned_sha="abc123") if i == 7 else x for i, x in enumerate(r)], None))


def m_unknown_need(d, g):
    edit(C(d), lambda r: ([dict(x, need_ids="N99") if i == 9 else x for i, x in enumerate(r)], None))


def m_need_present(d, g):
    rows = rd(g)
    for x in rows:
        if x["facility"] == "HIST_MARKET" and x["need"] == "CALIBRATION_SCORING":
            x["status"] = "VERIFIED_PRESENT"
    wr(g, rows)


def m_needs_edit(d, g):
    p = os.path.join(d, "research", "NEEDS.csv")
    open(p, "a").write("N15,a need added after the queries ran,TIME_SERIES,08,HIST_MARKET:MODEL_TRAINING,none\n")


def m_readme_evidence(d, g):
    edit(S(d), lambda r: ([dict(x, code_evidence_verified="README.md::Predictor@0123456789ab:1") if i == 0 else x for i, x in enumerate(r)], None))


def m_unverified_evidence(d, g):
    edit(S(d), lambda r: ([dict(x, code_evidence_verified="src/model.py::Predictor@MISSING:NOTFOUND") if i == 1 else x for i, x in enumerate(r)], None))


def m_no_evidence(d, g):
    edit(S(d), lambda r: ([dict(x, code_evidence_verified="") if i == 2 else x for i, x in enumerate(r)], None))


def m_crawler(d, g):
    def f(r):
        x = dict(r[0], canonical_repo="unclecode/crawl4ai", root_commits="f" * 40, shortlisted="no")
        return r + [x], None
    edit(C(d), f)


def m_vanished(d, g):
    edit(C(d), lambda r: ([dict(x, clone_head_matches_pin="", evidence_basis="UNVERIFIED", pinned_sha="") if i == 11 else x for i, x in enumerate(r)], None))


def m_short_not_cand(d, g):
    edit(S(d), lambda r: (r + [dict(r[0], canonical_repo="someone/not-a-candidate")], None))


def m_no_prov(d, g):
    edit(C(d), lambda r: ([dict(x, discovery_qids="") if i == 13 else x for i, x in enumerate(r)], None))


def m_fake_qid(d, g):
    edit(C(d), lambda r: ([dict(x, discovery_qids="Q99") if i == 14 else x for i, x in enumerate(r)], None))


def m_fake_chain(d, g):
    edit(C(d), lambda r: ([dict(x, discovery_qids="W01>someone/fork") if i == 15 else x for i, x in enumerate(r)], None))


def m_mirror(d, g):
    def f(r):
        roots = r[0]["root_commits"]
        return [dict(x, root_commits=roots) if i == 20 else x for i, x in enumerate(r)], None
    edit(C(d), f)


def m_fewer(d, g):
    def f(r):
        keep = r[:44]
        names = {x["canonical_repo"] for x in keep}
        return keep, None
    edit(C(d), f)


def m_score(d, g):
    def f(r):
        fields = list(r[0].keys()) + ["score"]
        return [dict(x, score="100") for x in r], fields
    edit(S(d), f)


def m_family(d, g):
    def f(r):
        out, n = [], 0
        for x in r:
            if x["family"] == "BEHAVIORAL_MULTI_AGENT" and x["canonical_repo"] not in ("666ghj/MiroFish", "camel-ai/oasis"):
                continue
            out.append(x)
        return out, None
    edit(S(d), f)
    edit(C(d), lambda r: ([dict(x, shortlisted="no") if x["canonical_repo"] in ("mesa/mesa", "bancaditalia/black-it") else x for x in r], None))


def m_mirofish(d, g):
    edit(S(d), lambda r: ([x for x in r if x["canonical_repo"] != "666ghj/MiroFish"], None))


def m_excluded_cand(d, g):
    edit(C(d), lambda r: (r + [dict(r[0], canonical_repo="TheSenseAI/SenseAI", root_commits="e" * 40, shortlisted="no")], None))


def m_license(d, g):
    edit(C(d), lambda r: ([dict(x, license_source="README says MIT") if i == 17 else x for i, x in enumerate(r)], None))


def m_audit(d, g):
    p = os.path.join(d, "research", "PROVENANCE_AUDIT.json")
    a = json.load(open(p))
    a["rows"][0]["reappeared"] = False
    json.dump(a, open(p, "w"))


def m_coverage(d, g):
    p = os.path.join(d, "research", "EXCLUSIONS.md")
    t = open(p).read().splitlines()
    open(p, "w").write("\n".join(l for l in t if not l.startswith("| `uber/causalml`")) + "\n")


def m_no_reason(d, g):
    p = os.path.join(d, "research", "EXCLUSIONS.md")
    t = open(p).read().splitlines()
    open(p, "w").write("\n".join(l for l in t if not l.startswith("| `dmlc/xgboost`")) + "\n")


CASES = [
    ("duplicate candidate", m_dup, "duplicate canonical"),
    ("fork counted (suspicious fork)", m_fork, "is a fork"),
    ("pin not a SHA", m_badsha, "not a 40-hex"),
    ("unknown need", m_unknown_need, "unknown need"),
    ("need cites a VERIFIED_PRESENT cell", m_need_present, "with status VERIFIED_PRESENT"),
    ("needs edited after the queries", m_needs_edit, "changed after it was frozen"),
    ("README as code evidence (P42)", m_readme_evidence, "documentation, not code"),
    ("code evidence not found at the pin", m_unverified_evidence, "code evidence not verified"),
    ("shortlisted with no code evidence (P42)", m_no_evidence, "no code evidence"),
    ("crawler as candidate", m_crawler, "crawler tooling"),
    ("vanished repository counted", m_vanished, "not verified at its pin"),
    ("shortlist row not a candidate", m_short_not_cand, "not in candidates"),
    ("no provenance", m_no_prov, "no discovery provenance"),
    ("invented query id", m_fake_qid, "unknown query"),
    ("invented fork chain", m_fake_chain, "not traceable"),
    ("mirror with shared history", m_mirror, "shares history"),
    ("fewer than 45", m_fewer, "fewer than 45"),
    ("score column in shortlist", m_score, "score or rank column"),
    ("behavioral family below 3", m_family, "BEHAVIORAL_MULTI_AGENT has 2"),
    ("MiroFish missing", m_mirofish, "666ghj/mirofish missing"),
    ("README-only repository as candidate (P42)", m_excluded_cand, "listed as excluded"),
    ("license from README", m_license, "license not read from a file"),
    ("provenance audit failed", m_audit, "audit"),
    ("screened repository dropped from exclusions", m_coverage, "uber/causalml is neither"),
    ("not shortlisted without a reason", m_no_reason, "dmlc/xgboost not shortlisted"),
]


def run(d, g):
    p = subprocess.run([sys.executable, os.path.join(HERE, "check_candidates.py"), d, g], capture_output=True, text=True)
    return p.returncode, p.stdout


def main(argv):
    base, gap = argv[1], argv[2]
    failures = 0
    with tempfile.TemporaryDirectory() as t:
        d0 = os.path.join(t, "clean")
        shutil.copytree(os.path.join(base, "research"), os.path.join(d0, "research"))
        g0 = os.path.join(t, "gap_clean.csv")
        shutil.copy(gap, g0)
        code, out = run(d0, g0)
        print("unmutated copy: exit %d (%s)" % (code, "pass" if code == 0 else "FAIL"))
        failures += code != 0
        for i, (name, fn, expect) in enumerate(CASES):
            d = os.path.join(t, "case%02d" % i)
            shutil.copytree(os.path.join(base, "research"), os.path.join(d, "research"))
            g = os.path.join(t, "gap%02d.csv" % i)
            shutil.copy(gap, g)
            fn(d, g)
            code, out = run(d, g)
            caught = code == 1 and expect in out
            failures += not caught
            print("%-45s exit %d %s" % (name, code, "caught" if caught else "NOT CAUGHT: " + out[-300:]))
    print("cases", len(CASES), "not caught", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
