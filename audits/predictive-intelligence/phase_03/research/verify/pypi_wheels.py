"""Phase 03 lead: rubric item K4 from the PyPI JSON API (free, public). For each package's latest release, is there
a wheel usable on Python 3.13 that is pure Python or built for Windows, and what does requires_python say?
Usage: python3 pypi_wheels.py OUT_JSON
"""
import json, re, sys, urllib.request
PKG = {"scikit-learn/scikit-learn": "scikit-learn", "lightgbm-org/LightGBM": "lightgbm", "interpretml/interpret": "interpret-core",
       "PriorLabs/TabPFN": "tabpfn", "statsmodels/statsmodels": "statsmodels", "feast-dev/feast": "feast",
       "scikit-learn-contrib/MAPIE": "mapie", "henrikbostrom/crepes": "crepes", "ip200/venn-abers": "venn-abers",
       "lorentzenchr/model-diagnostics": "model-diagnostics", "bashtage/arch": "arch", "baobach/mlfinpy": "mlfinpy",
       "eslazarev/purged-cross-validation": "purgedcv", "CamDavidsonPilon/lifelines": "lifelines", "soda-inria/hazardous": "hazardous",
       "online-ml/river": "river", "sktime/sktime": "sktime", "blue-yonder/tsfresh": "tsfresh", "deepcharles/ruptures": "ruptures",
       "stumpy-dev/stumpy": "stumpy", "evidentlyai/evidently": "evidently", "NannyML/nannyml": "nannyml",
       "IFCA-Advanced-Computing/frouros": "frouros", "mlflow/mlflow": "mlflow", "probabl-ai/skore": "skore",
       "unionai-oss/pandera": "pandera", "mesa/mesa": "mesa", "bancaditalia/black-it": "black-it", "camel-ai/oasis": "camel-oasis",
       "666ghj/MiroFish": "mirofish"}
def rp_ok(spec):
    if not spec:
        return True
    for part in spec.split(","):
        m = re.match(r"\s*(<=|<|>=|>|==|!=|~=)\s*(\d+)\.(\d+)", part)
        if not m:
            continue
        op, v = m.group(1), (int(m.group(2)), int(m.group(3)))
        if op == "<" and not (3, 13) < v: return False
        if op == "<=" and not (3, 13) <= v: return False
        if op in (">=", "~=") and not (3, 13) >= v: return False
        if op == ">" and not (3, 13) > v: return False
    return True
out = {}
for repo, name in PKG.items():
    try:
        d = json.load(urllib.request.urlopen("https://pypi.org/pypi/%s/json" % name, timeout=30))
    except Exception as e:  # noqa: BLE001
        out[repo] = {"package": name, "error": "%s" % e}; continue
    info, files = d["info"], d["urls"]
    whl = [f["filename"] for f in files if f["filename"].endswith(".whl")]
    pure = [w for w in whl if w.endswith("-none-any.whl")]
    win313 = [w for w in whl if ("cp313" in w or "py3-none" in w or "abi3" in w) and "win" in w]
    ok = rp_ok(info.get("requires_python")) and bool(pure or win313)
    out[repo] = {"package": name, "version": info["version"], "requires_python": info.get("requires_python"),
                 "upload_time": files[0]["upload_time_iso_8601"] if files else None, "pure_wheels": pure[:2], "windows_313_wheels": win313[:2],
                 "sdist_only": not whl, "k4_pass": ok}
    print(repo, name, info["version"], info.get("requires_python"), "K4" if ok else "no")
json.dump(out, open(sys.argv[1], "w"), indent=1, sort_keys=True)
