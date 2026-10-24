"""Phase 03 lead: uniform checks of the generic rubric items for all 30 repositories, against the pinned clones,
the reviewers' raw outputs and the PyPI listing, compared with what SCORE_ITEMS.csv awards.

Q3  commit date of the pinned HEAD (git log in the clone) on or after 2026-04-24, and a release (PyPI upload time
    from pypi_wheels.json, or a git tag for MiroFish) on or after 2025-04-24.
L1  root license file at the pin: sha256 and a text classification (MIT, BSD, Apache, NCSA-style permissive; AGPL or GPL).
L3  telemetry markers in the package source at the pin (tests and docs excluded), adjudicated in TELEMETRY_ADJUDICATION.
K4  PyPI wheel usable on Python 3.13 (pure or Windows) from pypi_wheels.json, with recorded overrides.
Q1  the reviewer's repo-test output contains "N passed".
Usage: python3 verify_generic.py [--json OUT]; exit 1 when an award disagrees with a check.
"""
import csv, glob, hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)
SRC = "/home/claude/pi_research/src"
PKGDIR = {"scikit-learn/scikit-learn": "sklearn", "lightgbm-org/LightGBM": "python-package/lightgbm",
          "interpretml/interpret": "python/interpret-core/interpret", "PriorLabs/TabPFN": "src/tabpfn",
          "statsmodels/statsmodels": "statsmodels", "feast-dev/feast": "sdk/python/feast", "scikit-learn-contrib/MAPIE": "mapie",
          "henrikbostrom/crepes": "src/crepes", "ip200/venn-abers": "src", "lorentzenchr/model-diagnostics": "src/model_diagnostics",
          "bashtage/arch": "arch", "baobach/mlfinpy": "mlfinpy", "eslazarev/purged-cross-validation": "src/purgedcv",
          "CamDavidsonPilon/lifelines": "lifelines", "soda-inria/hazardous": "hazardous", "online-ml/river": "river",
          "sktime/sktime": "sktime", "blue-yonder/tsfresh": "tsfresh", "deepcharles/ruptures": "src/ruptures", "stumpy-dev/stumpy": "stumpy",
          "evidentlyai/evidently": "src/evidently", "NannyML/nannyml": "nannyml", "IFCA-Advanced-Computing/frouros": "frouros",
          "mlflow/mlflow": "mlflow", "probabl-ai/skore": "skore/src/skore", "unionai-oss/pandera": "pandera", "mesa/mesa": "mesa",
          "bancaditalia/black-it": "black_it", "camel-ai/oasis": "oasis", "666ghj/MiroFish": "backend/app"}
TESTOUT = {"scikit-learn/scikit-learn": "repo_tests_subset.txt", "lightgbm-org/LightGBM": "repo_tests_subset.txt",
           "interpretml/interpret": "repo_tests_subset.txt", "PriorLabs/TabPFN": "repo_tests_subset.txt",
           "statsmodels/statsmodels": "repo_tests_subset.txt", "feast-dev/feast": "repo_tests_subset.txt",
           "scikit-learn-contrib/MAPIE": "raw_repo_tests_mapie.txt", "henrikbostrom/crepes": None, "ip200/venn-abers": "raw_repo_tests_venn_abers.txt",
           "lorentzenchr/model-diagnostics": "raw_repo_tests_model_diagnostics.txt", "bashtage/arch": "raw_repo_tests_arch.txt",
           "baobach/mlfinpy": "raw_repo_tests_mlfinpy.txt", "eslazarev/purged-cross-validation": "raw_repo_tests_purgedcv.txt",
           "CamDavidsonPilon/lifelines": "repo_tests.out.txt", "soda-inria/hazardous": "repo_tests.out.txt", "online-ml/river": "repo_tests.out.txt",
           "sktime/sktime": "repo_tests.out.txt", "blue-yonder/tsfresh": "repo_tests.out.txt", "deepcharles/ruptures": "repo_tests.out.txt",
           "stumpy-dev/stumpy": "repo_tests.out.txt", "evidentlyai/evidently": "repo_tests_subset.out.txt", "NannyML/nannyml": "repo_tests_subset.out.txt",
           "IFCA-Advanced-Computing/frouros": "repo_tests_subset.out.txt", "mlflow/mlflow": "repo_tests_subset.out.txt",
           "probabl-ai/skore": "repo_tests_subset.out.txt", "unionai-oss/pandera": "repo_tests_subset.out.txt", "mesa/mesa": "mesa_pytest_offline.txt",
           "bancaditalia/black-it": "blackit_pytest_offline_locked_sklearn.txt", "camel-ai/oasis": "oasis_pytest_offline.txt",
           "666ghj/MiroFish": "backend_pytest.txt"}
MARKERS = re.compile(r"posthog|segment\.io|api\.segment|mixpanel|sentry_sdk|scarf|telemetry|usage_logging|download counter|analytics", re.I)
# Lead adjudication of telemetry marker hits (read in the pinned source): True = default-on phone-home exists.
TELEMETRY_ADJUDICATION = {
    "evidentlyai/evidently": (True, "src/evidently/telemetry.py posts to 35.232.253.5 unless DO_NOT_TRACK; UI service sends events"),
    "NannyML/nannyml": (True, "nannyml/usage_logging.py Segment tracker, default on"),
    "mlflow/mlflow": (True, "mlflow/telemetry set at import, default on in releases"),
    "PriorLabs/TabPFN": (True, "model_loading.py downloads config.json only to increment a download counter"),
}
K4_OVERRIDE = {"baobach/mlfinpy": (False, "pure wheel, but its pinned numba 0.60 and numpy 1.26 have no cp313 wheels (raw_py313_wheel_resolution.txt)"),
               "soda-inria/hazardous": (False, "the only release (0.2.0) is the rejected artifact with unknown-rights data")}

def lic_class(t):
    if "GNU AFFERO" in t.upper():
        return "AGPL"
    if "GNU GENERAL PUBLIC LICENSE" in t.upper():
        return "GPL"
    if "Apache License" in t:
        return "Apache-2.0"
    if "Permission is hereby granted, free of charge" in t:
        return "MIT"
    if "Redistribution and use in source and binary forms" in t:
        return "BSD"
    if "to deal with the Software" in t:
        return "NCSA-style"
    return "UNKNOWN"

def main():
    awards = {}
    for r in csv.DictReader(open(os.path.join(RES, "SCORE_ITEMS.csv"))):
        awards[(r["repo"], r["item_id"])] = int(r["points"]) > 0
    pypi = json.load(open(os.path.join(HERE, "pypi_wheels.json")))
    short = list(csv.DictReader(open(os.path.join(RES, "..", "..", "phase_02", "research", "SHORTLIST.csv"))))
    out, bad = [], 0
    for row in short:
        repo = row["canonical_repo"]; d = os.path.join(SRC, repo.replace("/", "__"))
        res = {"repo": repo}
        cd = subprocess.run(["git", "-C", d, "log", "-1", "--format=%cI"], capture_output=True, text=True).stdout.strip()
        if repo == "666ghj/MiroFish":
            rel = subprocess.run(["git", "-C", d, "log", "-1", "--format=%cI", "v0.1.2"], capture_output=True, text=True).stdout.strip() or None
        else:
            rel = (pypi.get(repo) or {}).get("upload_time")
        q3 = bool(cd) and cd[:10] >= "2026-04-24" and bool(rel) and rel[:10] >= "2025-04-24"
        res.update({"pin_commit_date": cd, "latest_release": rel, "Q3_check": q3})
        lf = sorted(glob.glob(os.path.join(d, "LICENSE*")) + glob.glob(os.path.join(d, "COPYING*")))
        lf = [p for p in lf if os.path.isfile(p)][:1]
        txt = open(lf[0], encoding="utf-8", errors="replace").read() if lf else ""
        cls = lic_class(txt)
        res.update({"license_file": os.path.basename(lf[0]) if lf else None, "license_sha256": hashlib.sha256(open(lf[0], "rb").read()).hexdigest()[:16] if lf else None,
                    "license_class": cls, "L1_check": cls in ("MIT", "BSD", "Apache-2.0", "NCSA-style")})
        hits = []
        for p in glob.glob(os.path.join(d, PKGDIR[repo], "**", "*.py"), recursive=True):
            if re.search(r"(^|/)(tests?|docs?|examples?)(/|$)", os.path.relpath(p, d)):
                continue
            if MARKERS.search(open(p, encoding="utf-8", errors="replace").read()):
                hits.append(os.path.relpath(p, d))
        adj = TELEMETRY_ADJUDICATION.get(repo, (False, "marker hits read by the lead: no default-on phone-home" if hits else "no marker"))
        res.update({"telemetry_marker_files": len(hits), "telemetry_marker_examples": hits[:4], "telemetry_default_on": adj[0], "telemetry_note": adj[1],
                    "L3_check": not adj[0]})
        k4 = K4_OVERRIDE.get(repo, ((pypi.get(repo) or {}).get("k4_pass", False), "pypi_wheels.json"))
        res.update({"K4_check": k4[0], "K4_note": k4[1]})
        tf = TESTOUT[repo]
        tt = open(os.path.join(RES, "SMOKES", repo.replace("/", "__"), tf), encoding="utf-8", errors="replace").read() if tf else ""
        m = re.search(r"(\d+) passed", tt)
        res.update({"test_output": tf, "tests_passed": int(m.group(1)) if m else 0})
        mism = []
        for item, ok in (("Q3", q3), ("L1", res["L1_check"]), ("L3", res["L3_check"]), ("K4", k4[0])):
            if awards.get((repo, item)) != ok:
                mism.append(item)
        if awards.get((repo, "Q1")) and not res["tests_passed"]:
            mism.append("Q1")
        res["award_mismatches"] = mism
        bad += bool(mism)
        out.append(res)
        print("%-40s Q3 %-5s L1 %-10s L3 %-5s K4 %-5s passed %-5s %s" % (repo, q3, cls, res["L3_check"], k4[0], res["tests_passed"], ("MISMATCH " + ",".join(mism)) if mism else ""))
    print("repositories %d, award mismatches %d" % (len(out), bad))
    if "--json" in sys.argv:
        json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
