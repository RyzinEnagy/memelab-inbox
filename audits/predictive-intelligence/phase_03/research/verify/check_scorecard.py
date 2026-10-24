"""Phase 03 lead: offline checker for the scoring deliverables. Positive test: python3 check_scorecard.py (exit 0).
check_scorecard_negative.py runs the same checks on mutated copies and expects each to be refused.

Checks: locked weights equal the package's GRADING_RUBRIC.md; RUBRIC_ITEMS sum to them; SCORE_ITEMS has every
repository x item, all-or-nothing points, evidence for every point and every evidence path resolvable; no point rests
on README text alone (P42); chronology items rest on raw output or re-execution, not review prose (P13 guard);
LLM agent simulators earn no temporal point (P26) and no behavioral simulator earns a probability or calibration
point (P27); strong-copyleft repositories earn no L1 point and are never INSTALL or ADAPTER in process (P31);
no point contradicts a confirmed lead finding (VETO);
repair pass (skeptic M3, m1, m2): a T1, T2, T3 or O5 point that rests on a splitter must cite a fold audit
(fold_audit:<suite>.<splitter>, from verify/fold_audit_*.out.txt) showing no small or empty training fold and no
training on later rows (FOLD); a pinned README or documentation file is never evidence (P42 at the pin); T1 and T3
join the chronology items; review prose alone is evidence only for the low-risk items in PROSE_OK; a point in the
temporal, outcome, calibration, feature or decision criteria needs a pinned path:line, a fold audit, or a raw or
re-execution file whose description quotes at least one token (an identifier with a digit, underscore or dot, a
number of three or more digits, a CamelCase word, or a `backtick quote` of six or more characters) found in that file
(ANCHOR);
SCORECARD criteria and totals recompute; the eligible ranking reproduces from the CSV with the written tie rule;
no REJECT row is ranked; RANKED_TOP10.md lists the first ten eligible rows in order with their totals.
Usage: python3 check_scorecard.py [RESEARCH_DIR]
"""
import csv, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = "/mnt/user-data/uploads/Memecoin_Predictive_Intelligence_Engine_Prompt_Package/references/GRADING_RUBRIC.md"
SRC = "/home/claude/pi_research/src"
CRITERIA = ["temporal_integrity", "transferable_outcomes", "calibration_uncertainty", "features", "decision_execution",
            "code_quality", "integration_fit", "reproducibility", "cost_latency", "license_security"]
RUBRIC_NAMES = ["Temporal integrity", "Transferable measurable", "Calibration, uncertainty", "Catalyst/social/on-chain",
                "Decision/execution", "Code quality", "Integration fit", "Experiment reproducibility", "Cost, latency", "Licensing, security"]
TIE_ORDER = ["temporal_integrity", "transferable_outcomes", "calibration_uncertainty", "features", "decision_execution",
             "code_quality", "integration_fit", "reproducibility", "license_security", "cost_latency"]
BEHAVIORAL = {"666ghj/MiroFish", "camel-ai/oasis", "mesa/mesa", "bancaditalia/black-it"}
LLM_AGENTS = {"666ghj/MiroFish", "camel-ai/oasis"}
COPYLEFT = {"666ghj/MiroFish", "bancaditalia/black-it"}
CHRONO_ITEMS = {"T1", "T2", "T3", "T4a", "T5", "T6"}
# Items whose evidence may be review prose alone (the reviewer read source, docs or a registry and recorded it); every
# other item needs raw output, a pinned path:line, a lead re-execution, a fold audit or a registry file (PI-D-029).
PROSE_OK = {"Q2", "Q4", "Q5", "I2", "I3", "I4", "K2", "K3", "L2", "L4", "L5"}
SUBSTANCE = {"temporal_integrity", "transferable_outcomes", "calibration_uncertainty", "features", "decision_execution"}
FOLD_ITEMS = {"T1", "T2", "T3", "O5"}
MIN_TRAIN_FRACTION = 0.10   # a fold must train on at least 10% of the labelled rows (289 of 2,893 on the challenge)
SPLITTER = re.compile(r"WalkForward|PurgedKFold|PurgedGroupKFold|CombinatorialPurged|CPCV|TimeSeriesSplit|GroupKFold|"
                      r"\bKFold|ExpandingWindowSplitter|ExpandingCutoffSplitter|SlidingWindowSplitter|InstanceSplitter|"
                      r"instance_splitter|expanding_rows|expanding_cutoff|walk.forward", re.I)
DOC_AT_PIN = re.compile(r"(^|/)(README[^/]*|[^/]+\.(md|rst|ipynb|txt)|docs?/.*)$", re.I)
LICENSE_FILE = re.compile(r"(^|/)(LICEN[SC]E|COPYING|NOTICE|THIRD[_-]PARTY)[^/]*$", re.I)
# Verified-finding veto: when a lead check in verify/VERIFY_RESULTS.json passed (the defect is confirmed), the listed
# (repository, item) pairs must score 0. Added in repair of the lead's own counterexample (counterexample_lead.py).
VETO = {
    "MA-1": [("scikit-learn-contrib/MAPIE", "C2"), ("scikit-learn-contrib/MAPIE", "Q5"), ("scikit-learn-contrib/MAPIE", "O1")],
    "MA-4": [("scikit-learn-contrib/MAPIE", "O1"), ("scikit-learn-contrib/MAPIE", "Q5")],
    "MA-2": [("scikit-learn-contrib/MAPIE", "C2")],
    "VA-1": [("ip200/venn-abers", "Q5")],
    "MD-1": [("lorentzenchr/model-diagnostics", "Q5")],
    "AR-1": [("bashtage/arch", "Q5")],
    "MF-1": [("baobach/mlfinpy", "T2")],
    "MF-2": [("baobach/mlfinpy", "L2")],
    "MF-3": [("baobach/mlfinpy", "I1"), ("baobach/mlfinpy", "K4")],
    "CR-1": [("henrikbostrom/crepes", "Q1"), ("henrikbostrom/crepes", "Q2")],
    "LL-1": [("CamDavidsonPilon/lifelines", "I2")],
    "HZ-1": [("soda-inria/hazardous", "L2"), ("soda-inria/hazardous", "L4"), ("soda-inria/hazardous", "K4")],
    "HZ-2": [("soda-inria/hazardous", "Q5"), ("soda-inria/hazardous", "O3")],
    "HZ-3": [("soda-inria/hazardous", "C2")],
    "PC-3": [("eslazarev/purged-cross-validation", "O5")],
    "ST-4": [("sktime/sktime", "O1")],
    "RV-3": [("online-ml/river", "F1"), ("online-ml/river", "Q5")],
    "TS-1": [("blue-yonder/tsfresh", "Q5")],
    "RU-1": [("deepcharles/ruptures", "Q4")],
    "RU-2": [("deepcharles/ruptures", "Q5"), ("deepcharles/ruptures", "F1")],
    "SU-2": [("stumpy-dev/stumpy", "R2")],
    "EV-1": [("evidentlyai/evidently", "L3")],
    "EV-2": [("evidentlyai/evidently", "Q4"), ("evidentlyai/evidently", "I2")],
    "NM-1": [("NannyML/nannyml", "L3")],
    "NM-2": [("NannyML/nannyml", "Q4")],
    "FR-1": [("IFCA-Advanced-Computing/frouros", "Q5"), ("IFCA-Advanced-Computing/frouros", "F1")],
    "FR-2": [("IFCA-Advanced-Computing/frouros", "I2")],
    "ML-1": [("mlflow/mlflow", "L3")],
    "ML-2": [("mlflow/mlflow", "L3")],
    "SO-2": [("probabl-ai/skore", "Q5")],
    "MI-1": [("666ghj/MiroFish", "L1"), ("666ghj/MiroFish", "L5")],
    "MI-3": [("666ghj/MiroFish", "R1"), ("666ghj/MiroFish", "Q5"), ("666ghj/MiroFish", "K1")],
    "MI-4": [("666ghj/MiroFish", "L5")],
    "OA-1": [("camel-ai/oasis", "Q5")],
    "OA-2": [("camel-ai/oasis", "R1")],
    "BI-1": [("bancaditalia/black-it", "Q1")],
    "BI-2": [("bancaditalia/black-it", "Q5"), ("bancaditalia/black-it", "L1")],
    "TP-1": [("PriorLabs/TabPFN", "L2")],
    "TP-3": [("PriorLabs/TabPFN", "L3")],
    "TP-4": [("PriorLabs/TabPFN", "R1")],
    "FE-2": [("feast-dev/feast", "Q5"), ("feast-dev/feast", "F1")],
    "FE-3": [("feast-dev/feast", "I2")],
    "SK-2": [("scikit-learn/scikit-learn", "T2")],
    "ST-1": [("sktime/sktime", "T2")],
}

def locked_weights():
    t = open(PKG, encoding="utf-8").read()
    w = []
    for name in RUBRIC_NAMES:
        m = re.search(r"^\|\s*" + re.escape(name) + r"[^|]*\|\s*(\d+)\s*\|", t, re.M)
        w.append(int(m.group(1)))
    return dict(zip(CRITERIA, w))

def fold_audit(res):
    out = {}
    for f in sorted(os.listdir(os.path.join(res, "verify"))):
        if f.startswith("fold_audit_") and f.endswith(".out.txt"):
            t = open(os.path.join(res, "verify", f), encoding="utf-8").read()
            out.update(json.loads(t[t.index("RESULTS_JSON ") + 13:].strip().splitlines()[0]))
    return out

def fold_problem(entry, item):
    """None when the audited splitter can carry the item, else the reason."""
    rows = entry_rows = entry.get("_rows", 0)
    if entry["min_n_train"] < MIN_TRAIN_FRACTION * rows:
        return "a training fold has %d rows (minimum %d)" % (entry["min_n_train"], int(MIN_TRAIN_FRACTION * rows))
    if entry.get("max_train_decided_after_first_test", 0) > 0:
        return "trains on %d rows decided after the test start" % entry["max_train_decided_after_first_test"]
    if item in ("T2", "T3") and (entry.get("max_overlap", 0) > 0 or entry.get("max_train_label_matures_after_first_test", 0) > 0):
        return "training labels mature after the test start (%d)" % entry.get("max_train_label_matures_after_first_test", 0)
    if item == "O5" and entry.get("max_shared_groups", 1) != 0:
        return "groups shared between train and test"
    return None

def anchored(res, ref):
    """True when a raw or re-execution reference quotes a token that occurs in the cited file."""
    m = re.match(r"(SMOKES/\S+|verify/\S+)\s*(.*)", ref.strip())
    if not m:
        return False
    p = os.path.join(res, m.group(1).rstrip(":;,"))
    if not os.path.isfile(p):
        return False
    toks = re.findall(r"[A-Za-z_][A-Za-z0-9_.]*[0-9_][A-Za-z0-9_.]*|[0-9]+(?:[.,][0-9]+)+|[0-9]{3,}|[A-Z][a-z]+[A-Z][A-Za-z]+|[a-z]+_[a-z_]+", m.group(2))
    toks = [x.strip(".,") for x in toks if len(x.strip(".,")) >= 4] + re.findall(r"`([^`]{6,})`", m.group(2))
    txt = open(p, encoding="utf-8", errors="replace").read()
    return any(x in txt or x.replace(",", "") in txt for x in toks)

def resolve(res, ref, fa=None):
    ref = ref.strip()
    if ref.startswith("fold_audit:"):
        return fa is not None and ref.split()[0][len("fold_audit:"):] in fa
    if ref.startswith("pin:"):
        m = re.match(r"pin:([^/]+)/(.+?):(\d+)", ref)
        if not m:
            return False
        p = os.path.join(SRC, m.group(1), m.group(2))
        return os.path.isfile(p) and int(m.group(3)) <= len(open(p, encoding="utf-8", errors="replace").read().splitlines())
    m = re.match(r"(REVIEWS/\S+?\.md|SMOKES/\S+|verify/\S+)", ref)
    if not m:
        return None  # free text without a path: allowed only next to a resolvable path
    return os.path.exists(os.path.join(res, m.group(1).rstrip(":;,")))

def check(res):
    errs = []
    lw = locked_weights()
    if sum(lw.values()) != 100:
        errs.append("locked weights do not sum to 100")
    items = list(csv.DictReader(open(os.path.join(res, "RUBRIC_ITEMS.csv"))))
    ipts = {}
    for it in items:
        ipts[it["item_id"]] = (it["criterion"], int(it["points"]))
        if int(it["locked_weight"]) != lw[it["criterion"]]:
            errs.append("RUBRIC_ITEMS weight differs from GRADING_RUBRIC.md for %s" % it["item_id"])
    for c in CRITERIA:
        if sum(p for (cc, p) in ipts.values() if cc == c) != lw[c]:
            errs.append("RUBRIC_ITEMS for %s do not sum to %d" % (c, lw[c]))
    fa = fold_audit(res)
    for k, v in fa.items():
        if isinstance(v, dict):
            v["_rows"] = fa.get("rows", 0)
    si = list(csv.DictReader(open(os.path.join(res, "SCORE_ITEMS.csv"))))
    card = list(csv.DictReader(open(os.path.join(res, "SCORECARD.csv"))))
    repos = [r["repo"] for r in card]
    if len(repos) != 30 or len(set(repos)) != 30:
        errs.append("SCORECARD does not have 30 distinct repositories")
    seen = {}
    for r in si:
        key = (r["repo"], r["item_id"])
        if key in seen:
            errs.append("duplicate SCORE_ITEMS row %s" % (key,))
        seen[key] = r
        c, p = ipts.get(r["item_id"], (None, None))
        pts = int(r["points"])
        if c is None or c != r["criterion"] or int(r["item_points"]) != p:
            errs.append("unknown or mislabelled item %s" % (key,))
            continue
        if pts not in (0, p):
            errs.append("partial item value %s" % (key,))
        if pts:
            ev = r["evidence"]
            if not ev.strip() or ev.startswith("no qualifying evidence"):
                errs.append("point without evidence %s" % (key,))
            refs = [x for x in ev.split(";") if x.strip()]
            res_flags = [resolve(res, x, fa) for x in refs]
            if any(f is False for f in res_flags) or not any(f is True for f in res_flags):
                errs.append("evidence does not resolve %s: %s" % (key, ev[:80]))
            if re.search(r"README", ev) and not re.search(r"SMOKES/|verify/|pin:|REVIEWS/\S+ s[1-8]", ev):
                errs.append("P42: README-only evidence %s" % (key,))
            if r["item_id"] in CHRONO_ITEMS and not re.search(r"SMOKES/|verify/|fold_audit:", ev):
                errs.append("P13 guard: chronology item without raw output or re-execution %s" % (key,))
            for x in refs:
                m = re.match(r"\s*pin:[^/]+/(.+?):\d+", x)
                if m and DOC_AT_PIN.search(m.group(1)) and not (r["criterion"] == "license_security" and LICENSE_FILE.search(m.group(1))):
                    errs.append("P42 at the pin: documentation file cited as evidence %s: %s" % (key, m.group(1)))
            if not re.search(r"SMOKES/|verify/|pin:|fold_audit:", ev) and r["item_id"] not in PROSE_OK:
                errs.append("evidence rule: review prose alone for %s %s" % key)
            if r["criterion"] in SUBSTANCE and not (any(x.strip().startswith(("pin:", "fold_audit:")) for x in refs) or any(anchored(res, x) for x in refs)):
                errs.append("ANCHOR: no pinned line, fold audit or quoted token found in a cited raw file %s" % (key,))
            if r["item_id"] in FOLD_ITEMS and (SPLITTER.search(ev) or r["repo"] == "eslazarev/purged-cross-validation"):
                cites = [x.strip().split()[0][len("fold_audit:"):] for x in refs if x.strip().startswith("fold_audit:")]
                if not cites:
                    errs.append("FOLD: splitter evidence without a fold audit %s" % (key,))
                for c in cites:
                    if c in fa and isinstance(fa[c], dict):
                        why = fold_problem(fa[c], r["item_id"])
                        if why:
                            errs.append("FOLD: %s for %s %s: %s" % (c, r["repo"], r["item_id"], why))
            if r["repo"] in LLM_AGENTS and r["criterion"] == "temporal_integrity":
                errs.append("P26: LLM agent simulator earned a temporal point %s" % (key,))
            if r["repo"] in BEHAVIORAL and (r["item_id"] == "O1" or r["criterion"] == "calibration_uncertainty"):
                errs.append("P27: behavioral simulator earned a probability or calibration point %s" % (key,))
            if r["repo"] in COPYLEFT and r["item_id"] == "L1":
                errs.append("P31: strong copyleft earned L1 %s" % (key,))
    vr = os.path.join(res, "verify", "VERIFY_RESULTS.json")
    passed = {c["id"] for c in json.load(open(vr))["checks"] if c["pass"]} if os.path.exists(vr) else set()
    for cid, pairs in VETO.items():
        if cid not in passed:
            errs.append("verified-finding check %s missing or failing; its veto cannot be applied" % cid)
            continue
        for repo, iid in pairs:
            r = seen.get((repo, iid))
            if r is not None and int(r["points"]):
                errs.append("verified finding %s vetoes %s %s, but it scores %s" % (cid, repo, iid, r["points"]))
    for repo in repos:
        for iid in ipts:
            if (repo, iid) not in seen:
                errs.append("missing SCORE_ITEMS row %s %s (unanswered must be an explicit 0)" % (repo, iid))
    for r in card:
        tot = 0
        for c in CRITERIA:
            s = sum(int(x["points"]) for x in si if x["repo"] == r["repo"] and x["criterion"] == c)
            v = int(r["lead_" + c])
            if v != s:
                errs.append("criterion %s of %s is %d, items sum to %d" % (c, r["repo"], v, s))
            if not 0 <= v <= lw[c]:
                errs.append("criterion %s of %s outside 0..%d" % (c, r["repo"], lw[c]))
            tot += v
        if int(r["lead_total"]) != tot:
            errs.append("total of %s is %s, criteria sum to %d" % (r["repo"], r["lead_total"], tot))
        if int(r["reviewer_total"]) != sum(int(r["reviewer_" + c]) for c in CRITERIA):
            errs.append("reviewer total of %s does not recompute" % r["repo"])
        if r["repo"] in COPYLEFT and re.match(r"(INSTALL|ADAPTER)", r["integration_decision"]):
            errs.append("P31: strong copyleft %s has in-process decision %s" % (r["repo"], r["integration_decision"]))
        if r["eligible_for_top10"] == "NO" and r["eligible_rank"]:
            errs.append("ineligible %s carries a rank" % r["repo"])
        if r["flags"].startswith("REJECT (") and r["integration_decision"] == "REJECT" and r["eligible_for_top10"] != "NO":
            errs.append("REJECT %s marked eligible" % r["repo"])
    elig = [r for r in card if r["eligible_for_top10"] == "YES"]
    exp = sorted(elig, key=lambda r: tuple([-int(r["lead_total"])] + [-int(r["lead_" + c]) for c in TIE_ORDER] + [r["repo"].lower()]))
    for i, r in enumerate(exp, 1):
        if str(r["eligible_rank"]) != str(i):
            errs.append("rank of %s is %s, the sort gives %d" % (r["repo"], r["eligible_rank"], i))
    top = os.path.join(res, "RANKED_TOP10.md")
    if os.path.exists(top):
        t = open(top, encoding="utf-8").read()
        rows = re.findall(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|", t, re.M)
        want = [(str(i), r["repo"], str(r["lead_total"])) for i, r in enumerate(exp[:10], 1)]
        got = [(a, b.strip("` "), c) for a, b, c in rows[:10]]
        if got != want:
            errs.append("RANKED_TOP10.md table differs from the CSV sort: %s" % got[:3])
        if len(exp) < 10 and "BLOCKED" not in t:
            errs.append("fewer than ten eligible but RANKED_TOP10.md does not BLOCK")
    return errs

if __name__ == "__main__":
    res = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
    e = check(res)
    for x in e:
        print("FAIL", x)
    print("checks done, problems %d" % len(e))
    sys.exit(1 if e else 0)
