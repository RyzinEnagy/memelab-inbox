"""Phase 12 mutation probe: each mutation of memelab/predictive/evaluation.py must make tests/test_predictive_evaluation.py fail.

Works on a temporary copy of the repository's tracked files plus the files the tests read (the checkout is never edited), so it
runs at HEAD. Never touches the sealed folder (the tests use a stand-in). Writes a JSON report.

    python -B mutation_evaluation.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
EP = "memelab/predictive/evaluation.py"
TEST = "tests/test_predictive_evaluation.py"
EXTRA = [EP, TEST, "docs/predictive-intelligence/DECISIONS.md",
         "audits/predictive-intelligence/phase_06/PHASE_06_RESULTS.json",
         "audits/predictive-intelligence/phase_11/experiments/SEARCH_LEDGER.csv"]

MUTATIONS = [
    # the seal and the single opening
    (EP, "seal check exit ignored", "    if exit_code != 0:\n        raise SealError", "    if False:\n        raise SealError"),
    (EP, "seal problems ignored", '    if not isinstance(report, dict) or report.get("problems") != []:', "    if not isinstance(report, dict):"),
    (EP, "pinned hash not compared", "        if report.get(key) != SEAL_PINS[key]:", "        if False:"),
    (EP, "pin not required in DECISIONS", "        if SEAL_PINS[key] not in decisions_text:", "        if False:"),
    (EP, "any folder accepted", "    if not d.as_posix().endswith(L.SEALED_DIR):", "    if False:"),
    (EP, "second first opening accepted", '    if mode == "FIRST_OPENING" and log_path.exists():', "    if False:"),
    (EP, "reproduction without a log accepted", "        if not log_path.exists():\n            raise EvaluationError(\"a REPRODUCTION", "        if False:\n            raise EvaluationError(\"a REPRODUCTION"),
    (EP, "bytes read not hashed against the pin", '    if got != SEAL_PINS["holdout_labels_sha256"]:', "    if False:"),
    (EP, "log written after decompressing", '    if mode == "FIRST_OPENING":\n        log_path.parent.mkdir(parents=True, exist_ok=True)\n        log_path.write_text(json.dumps({"entries": [entry]}, sort_keys=True, indent=1) + "\\n")\n    rows = [json.loads(line) for line in gzip.decompress(raw).decode().splitlines() if line.strip()]',
     '    rows = [json.loads(line) for line in gzip.decompress(raw).decode().splitlines() if line.strip()]\n    if mode == "FIRST_OPENING":\n        log_path.parent.mkdir(parents=True, exist_ok=True)\n        log_path.write_text(json.dumps({"entries": [entry]}, sort_keys=True, indent=1) + "\\n")'),
    (EP, "record fields not required", "        if not record.get(k):\n            raise EvaluationError", "        if False:\n            raise EvaluationError"),
    # the holdout rows
    (EP, "stored split trusted", '        if r.get("split") != "HOLDOUT" or L.split_of(target, dt) != "HOLDOUT":', '        if r.get("split") != "HOLDOUT":'),
    (EP, "maturity not recomputed", '        if abs(float(r["label_matures_at"]) - C.label_matures_at(target, dt)) > 1e-6:', "        if False:"),
    (EP, "version not checked", '        if r.get("target_version") != C.TARGETS[target]["version"] or r.get("labels_version") != L.LABELS_VERSION:', "        if False:"),
    (EP, "registry not checked", '        if r.get("registry_sha") != C.registry_sha256():', "        if False:"),
    (EP, "contacted flag not cross-checked", '        if bool(r.get("holdout_contacted")) != listed:', "        if False:"),
    (EP, "contacted kept", "            if exclude_contacted:", "            if False:"),
    (EP, "censored scored", '        if st != "LABELED" or r.get("censored") or r.get("label") not in (0, 1):', '        if st != "LABELED" or r.get("label") not in (0, 1):'),
    (EP, "pending scored", '        if st != "LABELED" or r.get("censored") or r.get("label") not in (0, 1):', '        if r.get("censored") or r.get("label") not in (0, 1):'),
    (EP, "observed before maturity accepted", '        if obs is None or float(obs) < float(r["label_matures_at"]):', "        if obs is None:"),
    (EP, "assert_scorable skipped", '        C.assert_scorable({"label": r["label"], "target": target, "decision_time": dt, "label_status": st,', '        (lambda *a: None)({"label": r["label"], "target": target, "decision_time": dt, "label_status": st,'),
    (EP, "key conflict view ignored", '        if not include_key_conflict and "KEY_CONFLICT" in flags:', "        if False:"),
    (EP, "duplicates accepted", "        if k in seen:", "        if False:"),
    (EP, "identity by time not checked", '    if float(label_row["decision_time"]) != float(pred_row["decision_time"]):', "    if False:"),
    (EP, "identity by mint not checked", '    for a in ("decision_key", "chain", "mint"):', '    for a in ("decision_key", "chain"):'),
    # model time
    (EP, "future-trained card accepted", "    early = [t for t in decision_times if float(t) < cut]", "    early = []"),
    (EP, "training decision at cutoff accepted", '    if mt is not None and float(mt) >= cut:', '    if mt is not None and float(mt) > cut:'),
    (EP, "training maturity after cutoff accepted", '    if mm is not None and float(mm) > cut:', "    if False:"),
    (EP, "stale decisions scored", "    return [STALE if float(t) - cut > age else None for t in decision_times]", "    return [None for t in decision_times]"),
    (EP, "row count not checked", "    if len(p) != len(examples):", "    if False:"),
    (EP, "probabilities not checked", "    if fin.size:\n        K.check_probs(fin)\n    return p, why", "    return p, why"),
    # champion
    (EP, "champion from any view", '        if r.get("target") != target or r.get("view") != "ALL" or r.get("reference") != "B2" or r.get("verdict") != DEV_SKILL:',
     '        if r.get("target") != target or r.get("reference") != "B2" or r.get("verdict") != DEV_SKILL:'),
    (EP, "champion against any reference", '        if r.get("target") != target or r.get("view") != "ALL" or r.get("reference") != "B2" or r.get("verdict") != DEV_SKILL:',
     '        if r.get("target") != target or r.get("view") != "ALL" or r.get("verdict") != DEV_SKILL:'),
    (EP, "abstaining champion accepted", "        if fitted.get(cid):\n            won.append", "        if True:\n            won.append"),
    (EP, "highest brier champion", "        won.sort()", "        won.sort(reverse=True)"),
    (EP, "champion when B2 abstains", '    if fitted.get("P07_B2"):', "    if True:"),
    (EP, "skill verdict not renamed", "    return HOLDOUT_SKILL if v == DEV_SKILL else v", "    return v"),
    # selection correction and the ledger
    (EP, "max-T not centred", "            s = 1.0 - float(np.sum((pp[key][i] - yy[t][i]) ** 2)) / den - obs[key]", "            s = 1.0 - float(np.sum((pp[key][i] - yy[t][i]) ** 2)) / den"),
    (EP, "max-T compares own statistic only", "            mx = max(mx, s)", "            mx = s if key == defined[0] else mx"),
    (EP, "Bonferroni not multiplied", "    return min(1.0, p * n)", "    return min(1.0, p)"),
    (EP, "unknown ledger kind dropped", '            raise EvaluationError(f"ledger kind {k!r} is not classified', '            other += 1 or EvaluationError(f"ledger kind {k!r} is not classified'),
    (EP, "controls counted by row", '            ctrl.add((r["phase"], r["target"], r["candidate"], r["seed"]))', '            ctrl.add((r["phase"], r["target"], r["candidate"]))'),
    (EP, "bake-off left out of N_search", '"n_search": len(cand) + bake}', '"n_search": len(cand)}'),
    (EP, "shadow ignores calibration", '    cal_ok = bool(cal.get("in_the_large_ok")) and cal.get("every_bin_ok") in (True, None)', "    cal_ok = True"),
    (EP, "shadow ignores per-class minimum", '    counts = n >= a["min_holdout_events"] and k >= a["min_holdout_per_class"] and n - k >= a["min_holdout_per_class"]',
     '    counts = n >= a["min_holdout_events"]'),
    # repair pass 2: the skeptic's 12 mutations (5 survived the first-pass tests), then the new correction states
    (EP, "S1 max-T strict exceedance", "            if mx == -math.inf or mx >= obs[key]:", "            if mx == -math.inf or mx > obs[key]:"),
    (EP, "S2 max-T undefined replicate not an exceedance", "            if mx == -math.inf or mx >= obs[key]:", "            if mx != -math.inf and mx >= obs[key]:"),
    (EP, "S3 max-T only over the candidate's own target", "        for key in defined:\n            t = key[0]\n            i = rows[t][masks[key][rows[t]]]",
     "        for key in [k for k in defined if k[0] == defined[0][0]]:\n            t = key[0]\n            i = rows[t][masks[key][rows[t]]]"),
    (EP, "S4 max-T p without the +1", "    return {key: {\"bss\": obs[key], \"p_max_t\": ((1 + exceed[key]) / (reps + 1))", "    return {key: {\"bss\": obs[key], \"p_max_t\": ((exceed[key]) / (reps + 1))"),
    (EP, "S5 candidates keyed by name only (target dropped)", '            cand.add((r["target"], r["candidate"]))', '            cand.add(r["candidate"])'),
    (EP, "S6 holdout rows counted as candidates", "        if k in HOLDOUT_KINDS:\n            holdout += 1\n        elif k in CANDIDATE_KINDS:", "        if k in HOLDOUT_KINDS or k in CANDIDATE_KINDS:"),
    (EP, "S7 stale age doubled", "    return [STALE if float(t) - cut > age else None for t in decision_times]", "    return [STALE if float(t) - cut > 2 * age else None for t in decision_times]"),
    (EP, "S8 champion accepts any non-insufficient verdict", '        if r.get("target") != target or r.get("view") != "ALL" or r.get("reference") != "B2" or r.get("verdict") != DEV_SKILL:',
     '        if r.get("target") != target or r.get("view") != "ALL" or r.get("reference") != "B2" or str(r.get("verdict")).startswith("INSUFFICIENT"):'),
    (EP, "S9 shadow bss point allows -0.05", '    bss_ok = bss is not None and math.isfinite(bss) and bss >= a["promotion"]["SHADOW"]["bss_point_min"]', '    bss_ok = bss is not None and math.isfinite(bss) and bss >= a["promotion"]["SHADOW"]["bss_point_min"] - 0.05'),
    (EP, "S10 card cutoff check uses <=", "    early = [t for t in decision_times if float(t) < cut]", "    early = [t for t in decision_times if float(t) < cut - 3600]"),
    (EP, "S11 Bonferroni with n-1", "    return min(1.0, p * n)", "    return min(1.0, p * max(1, n - 1))"),
    (EP, "S12 debug runs counted as candidates", "        elif k in DEBUG_KINDS:\n            debug += 1", "        elif k in DEBUG_KINDS:\n            cand.add((r['phase'], r['experiment_id']))"),
    (EP, "R1 missing correction read as a fail", "    if len(known) < len(ps):\n        return NOT_COMPUTED", "    if len(known) < len(ps):\n        return FAILS"),
    (EP, "R2 missing correction read as a pass", "    if len(known) < len(ps):\n        return NOT_COMPUTED", "    if False:\n        return NOT_COMPUTED"),
    (EP, "R3 alpha itself passes", "    if any(p >= alpha for p in known):", "    if any(p > alpha for p in known):"),
    (EP, "R4 skill needed before correction dropped", "    if own_verdict != HOLDOUT_SKILL:\n        return NO_UNCORRECTED_SKILL", "    if False:\n        return NO_UNCORRECTED_SKILL"),
    (EP, "R5 post-opening pass creates a claim", "    if post_opening == SURVIVES:\n        return POST_OPENING_NOT_A_CLAIM", "    if post_opening == SURVIVES:\n        return SURVIVES"),
    (EP, "R6 post-opening fail ignored", "    if FAILS in (recorded, post_opening):", "    if recorded == FAILS:"),
    (EP, "R7 rules counted by name only", '    return len({(r["target"], r["candidate"]) for r in rows if r["kind"] in OTHER_KINDS})', '    return len({r["candidate"] for r in rows if r["kind"] in OTHER_KINDS})'),
]
EQUIVALENT: list[tuple] = []


def main() -> int:
    out = Path(sys.argv[1])
    files = subprocess.run(["git", "ls-files", "memelab", "tests"], cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    files += EXTRA
    results = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo"
        for f in sorted(set(files)):
            src = REPO / f
            if src.is_file():
                (root / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, root / f)
        orig = {p: (root / p).read_text() for p in (EP,)}
        cmd = [sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"]
        base = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("tests fail on the unmutated copy:\n" + base.stdout[-2000:])
        for path, name, old, new in MUTATIONS + EQUIVALENT:
            src = orig[path]
            if src.count(old) != 1:
                results.append({"file": path, "mutation": name, "applied": False, "caught": None, "note": f"pattern found {src.count(old)} times"})
                continue
            (root / path).write_text(src.replace(old, new))
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
            first = next((ln for ln in r.stdout.splitlines() if ln.startswith("FAILED") or ln.startswith("ERROR")), "")
            results.append({"file": path, "mutation": name, "applied": True, "caught": r.returncode != 0, "first_failure": first[:200]})
            (root / path).write_text(src)
    eq_names = {n for _, n, _, _ in EQUIVALENT}
    applied = [r for r in results if r["applied"] and r["mutation"] not in eq_names]
    rep = {"mutations": len(MUTATIONS), "applied": len(applied), "caught": sum(1 for r in applied if r["caught"]),
           "survived": [r["mutation"] for r in applied if not r["caught"]],
           "equivalent": [{"mutation": r["mutation"], "caught": r["caught"]} for r in results if r["mutation"] in eq_names],
           "not_applied": [r["mutation"] for r in results if not r["applied"]], "results": results}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("mutations", "applied", "caught", "survived", "not_applied")}))
    return 0 if rep["caught"] == rep["mutations"] else 1


if __name__ == "__main__":
    sys.exit(main())
