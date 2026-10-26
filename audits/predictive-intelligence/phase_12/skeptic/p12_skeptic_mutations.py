"""Phase 12 skeptic mutations of memelab/predictive/evaluation.py, run through the phase's own probe machinery.
Usage: python -B p12_skeptic_mutations.py <clone> OUT.json"""
import importlib.util, sys, json
clone, out = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("mp", f"{clone}/audits/predictive-intelligence/phase_12/probes/mutation_evaluation.py")
mp = importlib.util.module_from_spec(spec); spec.loader.exec_module(mp)
EP = mp.EP
mp.MUTATIONS = [
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
]
sys.argv = ["x", out]
mp.REPO = mp.Path(clone)
rc = mp.main()
print("probe exit", rc)
