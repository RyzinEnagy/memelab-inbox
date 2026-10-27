"""Phase 15 mutation probe: each mutation of memelab/predictive/scenario_eval.py must make tests/test_predictive_scenario_eval.py
fail. Works on a temporary copy of the tracked memelab and tests trees plus the files the tests read (the checkout is never
edited), so it runs at HEAD. Each original fragment must occur exactly once. Writes a JSON report.

    python -B mutation_scenario_eval.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MP = "memelab/predictive/scenario_eval.py"
TEST = "tests/test_predictive_scenario_eval.py"
EXTRA = ["audits/predictive-intelligence/phase_14/behavioral/MIROFISH_PROBE.json"]

MUTATIONS = [
    # blindness
    ("B1 outcome key accepted", "            if isinstance(k, str) and OUTCOME_KEY.match(k):", "            if False:"),
    ("B2 nested keys not walked", "            check_blind(v, f\"{path}.{k}\" if path else str(k))", "            pass"),
    ("B3 lists not walked", "            check_blind(v, f\"{path}[{i}]\")", "            pass"),
    ("B4 file hash not checked", "    if got != expected_sha256:", "    if False:"),
    # coding rules
    ("K1 validation errors ignored", "    if validation_errors:\n        return _not_codable(doc, \"DOCUMENT_INVALID\")", "    if False:\n        return _not_codable(doc, \"DOCUMENT_INVALID\")"),
    ("K2 kind not checked", "    if doc.get(\"kind\") != DOC_KIND:", "    if False:"),
    ("K3 status not checked", "    if doc.get(\"status\") not in CODABLE_STATUSES:", "    if False:"),
    ("K4 empty hypotheses coded", "    if not isinstance(hyps, list) or not hyps:", "    if not isinstance(hyps, list):"),
    ("K5 secondary monitors scored", "        if metric not in PRIMARY:", "        if metric not in PRIMARY and False:"),
    ("K6 any expectation accepted", "        if expect not in EXPECTS:", "        if False:"),
    ("K7 window start unchecked", "        if ws != T or we != T + C.TARGETS[metric][\"horizon_s\"]:", "        if we != T + C.TARGETS[metric][\"horizon_s\"]:"),
    ("K8 window end unchecked", "        if ws != T or we != T + C.TARGETS[metric][\"horizon_s\"]:", "        if ws != T:"),
    ("K9 no-statement not counted", "            out[\"no_statement\"] += 1", "            pass"),
    # warnings
    ("W1 conflict read as event", "        if ex == {\"EVENT\", \"NO_EVENT\"}:\n            out[t] = WARN_CONFLICT", "        if ex == {\"EVENT\", \"NO_EVENT\"}:\n            out[t] = WARN_EVENT"),
    ("W2 not codable read as none", "        return {t: WARN_NOT_CODABLE for t in PRIMARY}", "        return {t: WARN_NONE for t in PRIMARY}"),
    ("W3 no-event read as none", "        elif ex == {\"NO_EVENT\"}:\n            out[t] = WARN_NO_EVENT", "        elif ex == {\"NO_EVENT\"}:\n            out[t] = WARN_NONE"),
    # metrics
    ("M1 excluded rows scored", "        if w in EXCLUDED:\n            excl[w] += 1\n        else:\n            use.append(r)",
     "        if w in EXCLUDED:\n            excl[w] += 1\n        use.append(r)"),
    ("M2 precision over all rows", "                           \"precision\": (hits / nw) if nw else None,", "                           \"precision\": (hits / n) if nw else None,"),
    ("M3 lift without prevalence", "    res[\"lift\"] = (res[\"precision\"] - res[\"prevalence\"]) if (nw and n) else None",
     "    res[\"lift\"] = res[\"precision\"] if (nw and n) else None"),
    ("M4 permutation across days", "            wp[g] = rng.permutation(w[g])", "            wp = rng.permutation(w)"),
    ("M5 p without +1", "    return {\"observed_hits\": obs, \"p_up\": (1 + int(np.sum(null >= obs))) / (reps + 1),",
     "    return {\"observed_hits\": obs, \"p_up\": int(np.sum(null >= obs)) / reps,"),
    ("M6 days gate off", "    if days < a[\"min_effective_days\"]:\n        return INSUFFICIENT_DAYS", "    if False:\n        return INSUFFICIENT_DAYS"),
    ("M7 per-class gate off", "    if n < a[\"min_holdout_events\"] or k < a[\"min_holdout_per_class\"] or n - k < a[\"min_holdout_per_class\"]:\n        return INSUFFICIENT_EVENTS",
     "    if n < a[\"min_holdout_events\"]:\n        return INSUFFICIENT_EVENTS"),
    ("M8 warned gate off", "    if warned < MIN_WARNED:", "    if warned < 1:"),
    ("M9 raw p instead of Holm", "    pu = K.holm([u[\"p_up\"] if u else None for u in up])", "    pu = [u[\"p_up\"] if u else float(\"nan\") for u in up]"),
    ("M10 lift sign ignored", "    if lift is not None and lift > 0 and p_up_holm is not None", "    if lift is not None and p_up_holm is not None"),
    ("M11 lead times of misses", "    leads = [float(r[\"lead_s\"]) / 3600.0 for r, ww, yy in zip(use, w, y) if ww and yy == 1 and r.get(\"lead_s\") is not None]",
     "    leads = [float(r[\"lead_s\"]) / 3600.0 for r, ww, yy in zip(use, w, y) if r.get(\"lead_s\") is not None]"),
    # A_WARN
    ("A1 unmatured training rows", "        if not (float(r[\"decision_time\"]) < cutoff and float(r[\"label_matures_at\"]) <= cutoff):",
     "        if not (float(r[\"decision_time\"]) < cutoff):"),
    ("A2 later decisions in training", "        if not (float(r[\"decision_time\"]) < cutoff and float(r[\"label_matures_at\"]) <= cutoff):",
     "        if not (float(r[\"label_matures_at\"]) <= cutoff):"),
    ("A3 training gate off", "    g = B.gate(n, k)\n    if g:\n        card[\"abstain\"] = g", "    g = None\n    if g:\n        card[\"abstain\"] = g"),
    ("A4 no shrinkage", "            c[\"p\"] = (c[\"k\"] + B.M_SHRINK * b0) / (c[\"n\"] + B.M_SHRINK)", "            c[\"p\"] = c[\"k\"] / c[\"n\"]"),
    ("A5 earlier decisions scored", "    if early:\n        raise ScenarioEvalError(f\"A_WARN trained to", "    if False:\n        raise ScenarioEvalError(f\"A_WARN trained to"),
    ("A6 card hash unchecked", "    if sha(body) != card.get(\"card_sha256\"):", "    if False:"),
    ("A7 ambiguous rows get a number", "        if w in EXCLUDED:\n            why[i] = \"AMBIGUOUS_OR_NOT_CODABLE\"\n            continue",
     "        if w in EXCLUDED:\n            why[i] = \"AMBIGUOUS_OR_NOT_CODABLE\""),
    ("A8 dev selection without max-T", "    if len(known) < len(ps):\n        return E.NOT_COMPUTED", "    if False:\n        return E.NOT_COMPUTED"),
    ("A9 dev selection ignores failures", "    if any(p >= ALPHA for p in known):\n        return E.FAILS", "    if False:\n        return E.FAILS"),
    # decision
    ("D1 event minimum off", "    if eligible_events < MIN_EVENTS:", "    if eligible_events < 1:"),
    ("D2 D not required", "    if comparators.get(\"D\") != RAN:", "    if False:"),
    ("D3 B not required", "    if comparators.get(\"B\") != RAN:", "    if False:"),
    ("D4 stability not required", "        if d.get(\"stability\") != \"STABLE\":", "        if False:"),
    ("D5 P26 not required", "        if d.get(\"cutoff_verified_before_events\") is not True:", "        if False:"),
    ("D6 budget not required", "        if d.get(\"within_approved_budget\") is not True:", "        if False:"),
    ("D7 GO on evaluable alone", "    mirofish = MIROFISH_GO_CANDIDATE if (validation == EVALUABLE and not mf) else MIROFISH_NO_GO",
     "    mirofish = MIROFISH_GO_CANDIDATE if validation == EVALUABLE else MIROFISH_NO_GO"),
    ("D8 rules promoted without B2", "                and math.isfinite(b) and math.isfinite(b2) and b <= b2):", "                ):"),
    ("D9 rules promoted without correction", "        if (a.get(\"verdict\") == DEV_SKILL and a.get(\"selection_status\") == E.SURVIVES and b is not None and b2 is not None",
     "        if (a.get(\"verdict\") == DEV_SKILL and b is not None and b2 is not None"),
]


def main(out: str) -> int:
    src = (REPO / MP).read_text()
    for name, a, b in MUTATIONS:
        if src.count(a) != 1:
            raise SystemExit(f"{name}: fragment occurs {src.count(a)} times")
    results = []
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="p15_mut_") as td:
        root = Path(td)
        for d in ("memelab", "tests"):
            shutil.copytree(REPO / d, root / d, ignore=shutil.ignore_patterns("__pycache__"))
        for f in EXTRA:
            (root / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / f, root / f)
        cmd = [sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"]
        base = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("baseline fails: " + base.stdout[-2000:])
        for name, a, b in MUTATIONS:
            (root / MP).write_text(src.replace(a, b))
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=900)
            failed = [ln.split(" ")[1] for ln in r.stdout.splitlines() if ln.startswith("FAILED")]
            results.append({"mutation": name, "caught": r.returncode != 0,
                            "first_failure": failed[0] if failed else (r.stdout.strip().splitlines() or [""])[-1]})
        (root / MP).write_text(src)
    rep = {"module": MP, "tests": TEST, "mutations": len(results), "caught": sum(r["caught"] for r in results),
           "survivors": [r["mutation"] for r in results if not r["caught"]], "results": results, "wall_s": round(time.time() - t0, 1)}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("mutations", "caught", "survivors", "wall_s")}))
    return 0 if not rep["survivors"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
