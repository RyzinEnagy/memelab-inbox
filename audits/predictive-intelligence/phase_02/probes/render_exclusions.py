"""Write research/EXCLUSIONS.md from recorded evidence and the reasons below.

Usage: python render_exclusions.py PHASE02_DIR

Every repository that was verified or read but is not a candidate appears in
section A to F with its reason and evidence; every candidate that is not
shortlisted appears in section G with a reason class. The checker parses the
backticked `owner/name` in the first column of every table row.
"""
import csv
import json
import os
import re
import sys

TERMS = "surv|calib|conformal|drift|regime|hmm|markov|feature|barrier|label|bootstrap|changepoint|change-point|forecast|anomal|outlier|backtest|sentiment|agent|simulat"

SCREENED = [
    # (repo, class, reason, evidence)
    ("microsoft/LightGBM", "SAME_HEAD_PATH", "package seed path; serves the same HEAD as lightgbm-org/LightGBM, which PyPI lightgbm names as its source; counted once there", "VERIFY_RESULTS.jsonl (pin 064a6db1 at both paths; ecosyste.ms 404 for the old path)"),
    ("microsoft/interpret", "SAME_HEAD_PATH", "package seed path; same HEAD as interpretml/interpret (PyPI interpret source)", "VERIFY_RESULTS.jsonl (pin d82ea62a at both paths)"),
    ("automl/TabPFN", "SAME_HEAD_PATH", "code link in the TabPFN paper (A05); same HEAD as PriorLabs/TabPFN (PyPI tabpfn source)", "VERIFY_RESULTS.jsonl (pin 9d9d8725 at both paths)"),
    ("JoaquinAmatRodrigo/skforecast", "SAME_HEAD_PATH", "linked from the scikit-learn Related Projects page (D01); same HEAD as skforecast/skforecast", "VERIFY_RESULTS.jsonl (pin 3ecc0dc3 at both paths)"),
    ("TDAmeritrade/stumpy", "SAME_HEAD_PATH", "old path; same HEAD as stumpy-dev/stumpy (PyPI stumpy source)", "VERIFY_RESULTS.jsonl (pin 248e3440 at both paths)"),
    ("projectmesa/mesa", "SAME_HEAD_PATH", "package seed path; same HEAD as mesa/mesa (PyPI mesa source)", "VERIFY_RESULTS.jsonl (pin 949dc8c5 at both paths)"),
    ("iterative/dvc", "SAME_HEAD_PATH", "old path; same HEAD as treeverse/dvc (PyPI dvc source)", "VERIFY_RESULTS.jsonl (pin 56e59829 at both paths)"),
    ("pandera-dev/pandera", "SAME_HEAD_PATH", "named by the 2026 PyPI pandera release; same HEAD as unionai-oss/pandera, the path ecosyste.ms records and the README at the pin links; recorded as the candidate path until repair pass 2, now the canonical rule PI-D-025 takes unionai-oss/pandera", "EXTRA_PINS.jsonl and SUCCESSOR_SEARCH.jsonl (edb0d8b2 at both paths)"),
    ("TheClimateCorporation/properscoring", "SAME_HEAD_PATH", "pre-transfer path still named by PyPI properscoring (2015); same HEAD as properscoring/properscoring, which ecosyste.ms records as archived; the candidate row sat on this path until repair pass 2 (skeptic m1)", "SUCCESSOR_SEARCH.jsonl (a465b557 at both paths)"),
    ("JoelForamitti/agentpy", "SAME_HEAD_PATH", "pre-rename path still named by PyPI agentpy (2021); same HEAD as jofmi/agentpy, which ecosyste.ms records; the candidate row sat on this path until repair pass 2 (skeptic m1)", "SUCCESSOR_SEARCH.jsonl (42f5d498 at both paths)"),
    ("slundberg/shap", "SAME_HEAD_PATH", "rename test; same HEAD as shap/shap (PyPI shap source). shap/shap itself is screened below", "EXTRA_PINS.jsonl (c058cae5 at both paths)"),
    ("rhiever/tpot", "SAME_HEAD_PATH", "linked from D01; same HEAD as EpistasisLab/tpot. EpistasisLab/tpot is screened below", "EXTRA_PINS.jsonl (1bca6c6a at both paths)"),
    ("mendableai/firecrawl", "SAME_HEAD_PATH", "old path of the Firecrawl crawler; same HEAD as firecrawl/firecrawl (tooling, section D)", "EXTRA_PINS.jsonl (e1dc7a43 at both paths)"),
    ("AgentPy/agentpy", "VANISHED", "package seed URL; `git ls-remote` asks for credentials (repository missing or private). Successor traced through PyPI agentpy project URLs to JoelForamitti/agentpy, which now serves as jofmi/agentpy (candidate). Not treated as identical: no pinned commit can be compared", "VERIFY_RESULTS.jsonl status VANISHED_OR_PRIVATE; PYPI_LOOKUPS.jsonl agentpy"),
    ("Yosri-Ben-Halima/cpcv", "VANISHED", "linked from the PyPI cpcv project (found by W03); the repository does not answer `git ls-remote` without credentials; the package source cannot be inspected", "VERIFY_RESULTS.jsonl status VANISHED_OR_PRIVATE; PYPI_LOOKUPS.jsonl cpcv"),
    ("jtaylor205/temporian", "VANISHED", "returned by W30; `git ls-remote` asks for credentials (missing or private); google/temporian is the candidate", "VERIFY_RESULTS.jsonl status VANISHED_OR_PRIVATE"),
    ("predicatai/predicat-feature-store", "VANISHED", "one of about 70 predicat-* packages of one vendor returned by K15; its linked repository does not answer `git ls-remote` without credentials; the rest of that vendor family was not screened", "VERIFY_RESULTS.jsonl status VANISHED_OR_PRIVATE"),
    ("TheSenseAI/SenseAI", "README_ONLY_CLAIM", "P42 on a real repository (found by W09): the README claims machine-learning models that predict token price movements with very high accuracy; the pinned tree has 9 files (JavaScript, PHP, HTML, a whitepaper), no Python, no training or evaluation code, no tests and no license file; scoreCalculator.js is a fixed weighted sum. No credit", "VERIFY_RESULTS.jsonl (pin f89e1360, py_files 0, license_files empty)"),
    ("Cooktrenches/Scan-Scam-AI-v1", "README_ONLY_CLAIM", "P42 on a real repository (found by W09): ml_module/ARCHITECTURE.md:474 to :477 tabulates rug-detection accuracy, precision, recall and F1 of 82% to 92%; the pinned tree has only `*_EXAMPLE.json` datasets, a shuffled random split (ml_module/model_trainer.py:121 train_test_split, random_state 42: no time order, P36 and P43), pickled models (ml_module/models/*.pkl, unsafe to load, P32), test_*.py files that call live APIs, and no license file (all rights reserved). No credit", "VERIFY_RESULTS.jsonl (pin cd9f2627, license_files empty)"),
    ("uber/causalml", "NON_MATCHING_NEED", "package seed; uplift and treatment-effect estimation; no frozen need asks for causal effects, and START_HERE forbids causal claims from correlational features", "VERIFY_RESULTS.jsonl (pin d59bb520, Apache-2.0)"),
    ("py-why/dowhy", "NON_MATCHING_NEED", "package seed; causal inference and refutation; same reason as causalml. Its refuters resemble negative controls (NC1), which the existing replay code already plans", "VERIFY_RESULTS.jsonl (pin 9a0ec4a9, MIT)"),
    ("py-why/EconML", "NON_MATCHING_NEED", "heterogeneous treatment effects; same reason as causalml", "VERIFY_RESULTS.jsonl (pin 9f61a337, MIT and BSD-3-Clause)"),
    ("shap/shap", "NON_MATCHING_NEED", "feature attribution; explanations are not a frozen need, and attributions are not calibration evidence", "EXTRA_PINS.jsonl (c058cae5)"),
    ("EpistasisLab/tpot", "NON_MATCHING_NEED", "genetic-programming AutoML (LGPL at the old path's pin); open-ended pipeline search conflicts with the selection discipline (P22) and duplicates autogluon and h2o-3", "EXTRA_PINS.jsonl (1bca6c6a); VERIFY_RESULTS.jsonl rhiever/tpot license LGPL"),
    ("aangelopoulos/conformal-prediction", "SAMPLE_ONLY", "tutorial notebooks for a conformal prediction introduction (D02); no package, no tests", "VERIFY_RESULTS.jsonl (pin 0426de35, test_files 0)"),
    ("scikit-multiflow/scikit-multiflow", "SUPERSEDED_INACTIVE", "merged into river (river README, D06); last commit 2020-11-19", "VERIFY_RESULTS.jsonl (pin d073a706)"),
    ("JackBenny39/pyziabm", "INACTIVE_NO_TESTS", "zero-intelligence order book model found by W07; last commit 2018-02-05, no tests", "VERIFY_RESULTS.jsonl (pin b4e62aa0)"),
    ("TUM-DAML/seml", "NON_MATCHING_NEED", "experiment manager for Slurm clusters with a MongoDB backend; the lab has neither", "VERIFY_RESULTS.jsonl (pin 48175e86)"),
    ("kukapay/crypto-sentiment-mcp", "PAID_API_WRAPPER", "one Python file that forwards requests to the Santiment GraphQL API and stops without SANTIMENT_API_KEY (main.py:10 to :14); no model; paid API not approved (PI-D-005)", "VERIFY_RESULTS.jsonl (pin a002ecef, py_files 1)"),
    ("G-Research/fasttrackml", "ARCHIVED", "MLflow-compatible tracking server; archived (ecosyste.ms archived=true), last commit 2025-01-31", "VERIFY_RESULTS.jsonl (pin 4d6f286e)"),
    ("Sakeeb91/market-regime-detection", "NO_CODE_NO_LICENSE", "returned by W32; the pinned tree has no Python source and no license file; ecosyste.ms has no record", "VERIFY_RESULTS.jsonl (pin 52b2aab9, py_files 0)"),
    ("jmschrei/torchegranate", "SUPERSEDED", "the old development repository of pomegranate 1.0, still linked by PyPI pomegranate; different history from jmschrei/pomegranate (candidate), last commit 2023-04-15", "VERIFY_RESULTS.jsonl (pin d1c81423)"),
    ("Liuyi-Hu/regime_switch_model", "INACTIVE_NO_TESTS", "PyPI regime-switch-model (found by W31); last commit 2017-11-08, five Python files, no tests", "VERIFY_RESULTS.jsonl (pin 1da6ab9c)"),
    ("poypoyan/edhsmm", "ARCHIVED", "explicit-duration hidden semi-Markov models (K16); archived, no tests", "VERIFY_RESULTS.jsonl (pin 03e99991)"),
    ("microsoft/autogen", "ARCHIVED_BY_README", "package seed; README.md at the pin states the project is archived and no longer maintained (successor microsoft/agent-framework, not evaluated); general LLM agent orchestration is not a forecasting or simulation need; ecosyste.ms still shows archived=false (its sync lags)", "VERIFY_RESULTS.jsonl (pin 004749e6; LICENSE is CC-BY-4.0 text, LICENSE-CODE MIT)"),
]
TOOLING = [
    ("firecrawl/firecrawl", "TOOLING_NOT_CANDIDATE", "web crawler (Elving's research tool, MCP); data-collection tooling, not a predictive component (GRADING_RUBRIC); AGPL-3.0 at the pin", "EXTRA_PINS.jsonl and VERIFY_RESULTS.jsonl mendableai/firecrawl (e1dc7a43, AGPL-3.0)"),
    ("unclecode/crawl4ai", "TOOLING_NOT_CANDIDATE", "web crawler; tooling, not a candidate; Apache-2.0 at the pin", "VERIFY_RESULTS.jsonl (pin 30165f1e)"),
    ("getmaxun/maxun", "TOOLING_NOT_CANDIDATE", "web automation robots; tooling, not a candidate (RESEARCH_TOOLING); AGPL-3.0 at the pin", "VERIFY_RESULTS.jsonl (pin 8f2ab6bd)"),
]
REPAIR_SCREEN = [
    ("alteryx/featuretools", "D01 rank 7 (skeptic)"), ("hmmlearn/hmmlearn", "D01 rank 22 (skeptic)"),
    ("Novartis/torchsurv", "K10 (skeptic)"), ("autonlab/auton-survival", "K10_p2 rank 55 (skeptic)"),
    ("loft-br/xgboost-survival-embeddings", "K10_p1 rank 22 (skeptic)"), ("TA-Lib/ta-lib-python", "D05 rank 95 (skeptic)"),
    ("feast-dev/feast", "K15, W29, W33"), ("google/temporian", "W30"), ("jtaylor205/temporian", "W30"),
    ("airbnb/chronon", "W33"), ("quintoandar/butterfree", "K15"), ("4paradigm/OpenMLDB", "K15"),
    ("featureform/featureform", "K15"), ("feathr-ai/feathr", "K15, W29"), ("alibaba/feathub", "K15"),
    ("logicalclocks/feature-store-api", "K15"), ("MatsMoll/aligned", "K15"), ("chinmay1182/ftlite", "K15, W29"),
    ("pydoni/feature-forge", "W29"), ("predicatai/predicat-feature-store", "K15"),
    ("jmschrei/pomegranate", "D01 rank 23"), ("jmschrei/torchegranate", "PyPI pomegranate link"),
    ("Yizhan-Oliver-Shu/jump-models", "K17, W32"), ("deeptime-ml/deeptime", "K16"), ("Mogeng/IOHMM", "K16"),
    ("maximtrp/mchmm", "K16"), ("jamesross2/Bayesian-HMM", "K16"), ("poypoyan/edhsmm", "K16"),
    ("AlgorithmicMind/regimelab", "W32"), ("Liuyi-Hu/regime_switch_model", "W31"),
    ("Sakeeb91/market-regime-detection", "W32"),
    ("statsmodels/statsmodels", "already a candidate; MarkovRegression added as N07 code evidence"),
]
NOT_SHORTLISTED = {
    "dmlc/xgboost": ("DUPLICATE_ROLE", "boosting comparator covered by LightGBM; Phase 03 may swap"),
    "catboost/catboost": ("DUPLICATE_ROLE", "boosting comparator covered by LightGBM"),
    "h2oai/h2o-3": ("JVM_REQUIRED", "Java server; AutoML search adds selection risk (P22)"),
    "autogluon/autogluon": ("HEAVY_SEARCH", "large dependency tree; AutoML ensembles add selection risk (P22)"),
    "stanfordmlgroup/ngboost": ("DUPLICATE_ROLE", "distributional outputs not needed for binary targets"),
    "scikit-learn-contrib/imbalanced-learn": ("PROBABILITY_DISTORTION", "resampling distorts probabilities; class weights in the base learner do the job"),
    "ZhiningLiu1998/imbalanced-ensemble": ("PROBABILITY_DISTORTION", "same as imbalanced-learn"),
    "soda-inria/tabicl": ("DUPLICATE_ROLE", "small-data in-context role covered by TabPFN; checkpoint license not stated in the repository"),
    "perpetual-ml/perpetual": ("DUPLICATE_ROLE", "low-tuning booster; LightGBM holds the boosting slot"),
    "deel-ai/puncc": ("DUPLICATE_ROLE", "conformal role covered by MAPIE and crepes"),
    "EFS-OpenSource/calibration-framework": ("GPU_BASE_DEPENDENCY", "torch is a base requirement on PyPI"),
    "frazane/scoringrules": ("DUPLICATE_ROLE", "mostly continuous scores; Brier and log loss covered by scikit-learn and model-diagnostics"),
    "properscoring/properscoring": ("ARCHIVED", "archived; last commit 2022-10-12"),
    "astrogilda/tsbootstrap": ("DUPLICATE_ROLE", "block bootstrap covered by arch"),
    "Moffran/calibrated_explanations": ("DUPLICATE_ROLE", "wraps crepes"),
    "egonmedhatten/online-cp": ("DEFERRED", "online conformal belongs to Phase 19 monitoring; young"),
    "KhiopsLab/khalib": ("YOUNG_SMALL", "five Python files; calibration role covered"),
    "ml-stat-Sustech/TorchCP": ("LICENSE_AND_GPU", "LGPL-3.0 and torch"),
    "donlnz/nonconformist": ("INACTIVE", "last commit 2021-03-20"),
    "OliverHennhoefer/nonconform": ("NOT_CLASSIFICATION", "anomaly detection with false discovery control"),
    "facebookincubator/MCGrad": ("GPU_BASE_DEPENDENCY", "torch base requirement; multicalibration needs larger groups than 17 days give"),
    "unit8co/darts": ("VALUE_FORECASTER", "forecasts values, not barrier events"),
    "Nixtla/statsforecast": ("VALUE_FORECASTER", "forecasts values, not barrier events"),
    "Nixtla/mlforecast": ("VALUE_FORECASTER", "forecasts values, not barrier events"),
    "Nixtla/neuralforecast": ("GPU_BASE_DEPENDENCY", "torch; data hungry"),
    "aeon-toolkit/aeon": ("SHARED_HISTORY", "hard fork of sktime (shared root commit); sktime holds the slot"),
    "amazon-science/chronos-forecasting": ("GPU_LLM_STACK", "torch and transformers base requirements; zero-shot path sampling stays a Phase 08 research option"),
    "google-research/timesfm": ("WEIGHTS_TERMS", "3.0 weights non-commercial; torch"),
    "facebook/prophet": ("WRONG_TIMESCALE", "daily and weekly seasonality model for 5-minute memecoin paths"),
    "awslabs/gluonts": ("GPU_BASE_DEPENDENCY", "torch for most models; value forecaster"),
    "skforecast/skforecast": ("VALUE_FORECASTER", "forecasts values, not barrier events"),
    "bukosabino/ta": ("DUPLICATE_ROLE", "indicator features covered by tsfresh; no test files"),
    "tslearn-team/tslearn": ("DUPLICATE_ROLE", "analog search covered by stumpy"),
    "microsoft/qlib": ("DOMAIN_MISMATCH", "equity daily-bar platform; no Python 3.13 declared on PyPI"),
    "SeldonIO/alibi-detect": ("LICENSE_BUSL", "Business Source License 1.1, non-production use only"),
    "mitre/menelaus": ("INACTIVE", "last commit 2023-08-23"),
    "adaptive-machine-learning/CapyMOA": ("JVM_REQUIRED", "MOA jar through jpype"),
    "VowpalWabbit/vowpal_wabbit": ("DUPLICATE_ROLE", "online learning covered by river"),
    "whylabs/whylogs": ("INACTIVE", "last commit 2025-01-10"),
    "deepchecks/deepchecks": ("LICENSE_AGPL", "AGPL-3.0 at the pin"),
    "selimfirat/pysad": ("NOT_CLASSIFICATION", "streaming anomaly scores"),
    "simon-hirsch/ondil": ("LICENSE_GPL", "GPL-3.0 at the pin; online role covered by river"),
    "camel-ai/camel": ("FRAMEWORK_LAYER", "evaluated through OASIS, which pins it"),
    "getzep/graphiti": ("SERVICE_STACK", "LLM plus graph database; evaluated through MiroFish's Zep dependency"),
    "jofmi/agentpy": ("INACTIVE", "last commit 2025-02-06; role covered by mesa"),
    "tsinghua-fib-lab/AgentSociety": ("DUPLICATE_ROLE", "LLM society simulation role covered by OASIS and MiroFish"),
    "rgCASS/casevo": ("YOUNG_SMALL", "15 Python files, no tests"),
    "AgentTorch/AgentTorch": ("GPU_LLM_AND_DUPLICATE_ROLE", "torch and LLM; LLM population simulation covered by OASIS and MiroFish; AGPL-3.0 (allowed only behind the isolated adapter)"),
    "jpmorganchase/abides-jpmc-public": ("ARCHIVED", "order-book market simulator, archived; memecoins trade on AMM pools"),
    "abides-sim/abides": ("INACTIVE", "last commit 2020-11-19, no tests"),
    "cadCAD-org/cadCAD": ("INACTIVE", "last commit 2024-04-19"),
    "stelios12312312/TokenLab": ("DOMAIN_MISMATCH", "token supply and demand economics, not trader behavior around a listing"),
    "sebp/scikit-survival": ("LICENSE_GPL", "GPL-3.0 at the pin; survival role covered by lifelines and hazardous"),
    "havakv/pycox": ("GPU_AND_INACTIVE", "torch; last commit 2024-09-04"),
    "shi-ang/SurvivalEVAL": ("LICENSE_GPL", "GPL-3.0 at the pin"),
    "sktime/skpro": ("INTERFACE_LAYER", "wraps other survival and probabilistic libraries"),
    "mchiuminatto/triple_barrier": ("DUPLICATE_ROLE", "barrier labels covered by mlfinpy; LLM and server packages in its dependency files"),
    "quantscious/finmlkit": ("DUPLICATE_ROLE", "barrier labels covered by mlfinpy"),
    "treeverse/dvc": ("NOT_A_GAP", "git already versions the exports; data versioning is not a gap cell"),
    "aimhubio/aim": ("SERVER_STACK", "tracking server; no Python 3.13 declared on PyPI"),
    "IDSIA/sacred": ("DUPLICATE_ROLE", "ledger role covered by mlflow and skore; Phase 03 may compare it as a lighter ledger"),
    "fivetran/great_expectations": ("HEAVY_DUPLICATE", "data validation role covered by pandera"),
    "skfolio/skfolio": ("DUPLICATE_ROLE", "purged CV covered by purged-cross-validation; portfolio optimization otherwise"),
    "sam31415/timeseriescv": ("INACTIVE", "last commit 2022-02-15"),
    "autogluon/fev": ("VALUE_FORECASTER", "benchmark harness for value forecasts"),
    "optuna/optuna": ("SEARCH_RISK", "hyperparameter search raises selection risk; its trial ledger is noted for Phase 12"),
    "yzhao062/pyod": ("NEED_BLOCKED_NO_DATA", "holder and wallet history are not exported (distribution target BLOCKED_NO_DATA)"),
    "pygod-team/pygod": ("NEED_BLOCKED_NO_DATA", "wallet graph data not exported; torch geometric"),
    "safe-graph/UGFraud": ("NEED_BLOCKED_NO_DATA", "wallet graph data not exported; last commit 2022-04-17"),
    "networkx/networkx": ("NEED_BLOCKED_NO_DATA", "general graph library; no wallet graph data yet"),
    "freqtrade/freqtrade": ("LICENSE_GPL_AND_EXECUTION", "GPL-3.0; includes live order execution"),
    "polakowo/vectorbt": ("COMMONS_CLAUSE", "Apache-2.0 with Commons Clause; backtest scope is BACKTEST_NOT_AVAILABLE (PI-D-006)"),
    "mementum/backtrader": ("LICENSE_GPL_AND_INACTIVE", "GPL-3.0; last commit 2023-04-19"),
    "AI4Finance-Foundation/FinRL": ("TRADING_AGENT", "reinforcement-learning trading agents"),
    "Logarithm-Labs/fractal-defi": ("DEFERRED", "DeFi strategy simulation; N14 waits for execution data (PI-D-020)"),
    "cjhutto/vaderSentiment": ("NEED_BLOCKED_NO_DATA", "catalyst and social text history not exported"),
    "MaartenGr/BERTopic": ("NEED_BLOCKED_NO_DATA", "catalyst and social text history not exported; embedding models"),
    "AI4Finance-Foundation/FinGPT": ("GPU_LLM_AND_CONTAMINATION", "GPU and LLM; pretraining contamination (P26)"),
    "alteryx/featuretools": ("INACTIVE", "last commit 2024-11-13; the closest conceptual match (cutoff times), so Phase 03 may pull it with a recorded reason"),
    "google/temporian": ("INACTIVE", "last commit 2024-07-25; PyPI requires Python <3.12"),
    "airbnb/chronon": ("JVM_REQUIRED", "Scala and Spark"),
    "quintoandar/butterfree": ("JVM_REQUIRED", "pyspark"),
    "4paradigm/OpenMLDB": ("SERVER_STACK_DUPLICATE", "database server; point-in-time role covered by feast"),
    "featureform/featureform": ("LICENSE_MPL", "MPL-2.0 file-level copyleft in-process; server stack"),
    "feathr-ai/feathr": ("INACTIVE", "last commit 2024-03-26"),
    "alibaba/feathub": ("INACTIVE", "last commit 2023-09-21"),
    "logicalclocks/feature-store-api": ("INACTIVE", "last commit 2024-07-12; needs a Hopsworks server"),
    "MatsMoll/aligned": ("LICENSE_FSL", "Functional Source License 1.1, source-available"),
    "chinmay1182/ftlite": ("YOUNG_SMALL", "13 commits, one test file"),
    "pydoni/feature-forge": ("YOUNG_SMALL", "12 commits"),
    "hmmlearn/hmmlearn": ("INACTIVE", "last commit 2024-10-31; regime states covered by statsmodels MarkovRegression"),
    "jmschrei/pomegranate": ("INACTIVE", "last commit 2025-02-07; torch base requirement"),
    "Yizhan-Oliver-Shu/jump-models": ("INACTIVE", "last commit 2025-01-12; 13 commits, no test files"),
    "deeptime-ml/deeptime": ("LICENSE_LGPL", "LGPL in-process; regime states covered by statsmodels"),
    "Mogeng/IOHMM": ("INACTIVE", "last commit 2023-04-30"),
    "maximtrp/mchmm": ("LICENSE_GPL", "GPL-3.0 at the pin"),
    "jamesross2/Bayesian-HMM": ("INACTIVE", "last commit 2019-09-14"),
    "AlgorithmicMind/regimelab": ("YOUNG_SMALL", "15 commits; equity and VIX inputs"),
    "Novartis/torchsurv": ("GPU_BASE_DEPENDENCY", "torch base requirement; time-to-event role covered by lifelines and hazardous on CPU"),
    "autonlab/auton-survival": ("INACTIVE", "last commit 2023-10-16; torch"),
    "loft-br/xgboost-survival-embeddings": ("ARCHIVED", "archived (ecosyste.ms)"),
    "TA-Lib/ta-lib-python": ("DUPLICATE_ROLE", "indicator features covered by tsfresh; needs the TA-Lib C library"),
}


def main(argv):
    base = argv[1]
    R = os.path.join(base, "research")
    cands = list(csv.DictReader(open(os.path.join(R, "CANDIDATES.csv"))))
    mirrors = [json.loads(l) for l in open(os.path.join(R, "MIRROR_CHECKS.jsonl"))]
    queries = [json.loads(l) for l in open(os.path.join(R, "QUERY_RESULTS.jsonl"))]
    gh_blocked = [q for q in queries if q["mechanism"] == "GITHUB_SEARCH_API"]
    returned = set()
    for q in queries:
        for it in q.get("items") or []:
            r = it.get("repo") or it.get("full_name")
            if r:
                returned.add(r.lower())
    named = {c["canonical_repo"].lower() for c in cands}
    named |= {r.lower() for r, *_ in SCREENED + TOOLING} | {m["repo"].lower() for m in mirrors}
    for c in cands:
        named |= {x.lower() for x in c["same_head_paths"].split(";") if x}
    term_re = re.compile(TERMS, re.I)
    residual = sum(1 for r in returned - named if term_re.search(r.split("/")[-1]))
    L = []
    L.append("# Phase 02 exclusions\n")
    L.append("Every repository that Phase 02 verified (`git ls-remote`, blob-less clone at the pin, ecosyste.ms lookup) or read, and that is not a candidate, is listed in sections A to F with its reason. Section G gives the reason each candidate is not on the shortlist. Reasons are screening facts at the pinned SHA, not scores; Phase 03 may revisit any of them. Generated by `probes/render_exclusions.py` from the recorded evidence.\n")
    L.append("Returned by a query but never selected for verification: %d distinct repository names across the query corpus (QUERY_RESULTS.jsonl). Correction in repair pass 2 (independent skeptic, finding M1): the first version said the selection rule was a match between a name, package summary or documentation and a frozen need. That was not applied mechanically. Selection was analyst judgment guided by the needs, and the skeptic found six need-matching names in recorded results that had been passed over (featuretools, hmmlearn, torchsurv, auton-survival, xgboost-survival-embeddings, ta-lib-python). They are screened now (section H), and two query families that had not been searched (point-in-time feature stores, regime and state models) were added. A name-term scan of the names still unscreened (terms: %s) matches %d of them; they remain unscreened and Phase 03 may pull any of them with a recorded reason. The GitHub search API returned HTTP 403 for all %d queries (session proxy policy), so no repository was found or excluded through it.\n" % (len(returned - named), TERMS, residual, len(gh_blocked)))
    sections = [
        ("A. Same HEAD at another path (renamed, transferred or same-HEAD copy; counted once under the canonical path)", [s for s in SCREENED if s[1] == "SAME_HEAD_PATH"]),
        ("B. Vanished or private", [s for s in SCREENED if s[1] == "VANISHED"]),
        ("C. Forks and mirrors", [("%s" % m["repo"], m["relation"], "of %s; found by %s" % (m["of"], m["found_by"]), "MIRROR_CHECKS.jsonl: " + m["evidence"]) for m in mirrors]),
        ("D. Crawler and robot tooling (not candidates by rule)", TOOLING),
        ("E. README-only or marketing claims (P42)", [s for s in SCREENED if s[1] == "README_ONLY_CLAIM"]),
        ("F. Screened and not matching a frozen need, archived, sample-only or unusable", [s for s in SCREENED if s[1] not in ("SAME_HEAD_PATH", "VANISHED", "README_ONLY_CLAIM")]),
    ]
    for title, rows in sections:
        L.append("\n## %s\n" % title)
        L.append("| Repository | Class | Reason | Evidence |")
        L.append("|---|---|---|---|")
        for r, cls, why, ev in rows:
            L.append("| `%s` | %s | %s | %s |" % (r, cls, why.replace("|", "/"), ev.replace("|", "/")))
    L.append("\n## Papers found without public code\n")
    L.append("| Paper | Found by | Finding |")
    L.append("|---|---|---|")
    L.append("| arXiv 2608.20271, early prediction of fraudulent Solana memecoins | W04, A08 | no code link on the abstract or HTML page (2026-10-24T03:05Z) |")
    L.append("| arXiv 2504.07132, SolRPDS rug pull dataset | W04, W17, A09 | dataset on Hugging Face (DeFiLab/SolRPDS), no GitHub code link; a dataset, not a tool |")
    L.append("| arXiv 2603.24625, rug pull scams on Solana | W04, A10 | no code link on the abstract page |")
    L.append("\nThe MiroFish README describes a prediction engine that predicts anything. That claim earns nothing: MiroFish stays a candidate and is shortlisted only as a behavioral scenario generator (CANDIDATES.csv special_flags NO_PROBABILITY_OUTPUT and README_PREDICTION_CLAIMS_NOT_CREDITED).\n")
    L.append("\n## G. Candidates not shortlisted\n")
    L.append("Shortlist rule, written down in repair pass 2 from the reasons the first version applied (the reasons themselves did not change; `probes/check_candidates.py` now enforces 2, 4 and 6): (1) the candidate fills a frozen need, and per need and role one or two rows are shortlisted, the most direct implementation first (DUPLICATE_ROLE otherwise); (2) a library that would run in-process must carry a permissive license (MIT, BSD, Apache, ISC, NCSA); copyleft, source-available or non-commercial code terms exclude it, while behavioral simulators, which run only behind the isolated PLANNED_SEAMS adapter, may be copyleft and are flagged; (3) a heavy dependency (JVM, torch as a base requirement, a server stack) excludes a row only when another shortlisted or eligible row covers the role without it; (4) last commit within 18 months and not archived; (5) the need must be live: needs whose targets are BLOCKED_NO_DATA or DEFERRED (N11, N12, N14) are not shortlisted, and model rows must output event probabilities, not value forecasts or anomaly scores; (6) at least 3 rows per high-priority family (tabular, time series, calibration, online and drift, behavioral, experiment audit, event-time labels), and MiroFish and OASIS always (package-mandated); (7) very young projects (about 15 commits or fewer, or 5 files or fewer) are not shortlisted when an established row covers the role (YOUNG_SMALL).\n")
    L.append("| Repository | Family | Reason class | Reason |")
    L.append("|---|---|---|---|")
    missing = []
    for c in cands:
        if c["shortlisted"] == "yes":
            continue
        if c["canonical_repo"] not in NOT_SHORTLISTED:
            missing.append(c["canonical_repo"])
            continue
        cls, why = NOT_SHORTLISTED[c["canonical_repo"]]
        L.append("| `%s` | %s | %s | %s |" % (c["canonical_repo"], c["family"], cls, why))
    if missing:
        print("NO REASON FOR", missing)
        return 1
    L.append("\n## H. Repair pass 2 screen (independent skeptic finding M1)\n")
    L.append("Every name listed here was screened under the same admission rule (PI-D-024, with the canonical-path amendment PI-D-025). Outcome: CANDIDATE (row in CANDIDATES.csv), SHORTLISTED, or the section above that excludes it.\n")
    L.append("| Repository | Found by | Outcome |")
    L.append("|---|---|---|")
    byname = {c["canonical_repo"]: c for c in cands}
    for repo, found in REPAIR_SCREEN:
        c = byname.get(repo)
        if c:
            out = "SHORTLISTED" if c["shortlisted"] == "yes" else "CANDIDATE (section G: %s)" % NOT_SHORTLISTED.get(repo, ("", ""))[0]
        else:
            cls = [x for x in SCREENED if x[0] == repo]
            out = "EXCLUDED (%s)" % cls[0][1] if cls else "NOT FOUND"
        L.append("| `%s` | %s | %s |" % (repo, found, out))
    open(os.path.join(R, "EXCLUSIONS.md"), "w").write("\n".join(L) + "\n")
    print("excluded screened", len(SCREENED) + len(TOOLING) + len(mirrors), "not shortlisted", sum(1 for c in cands if c["shortlisted"] != "yes"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
