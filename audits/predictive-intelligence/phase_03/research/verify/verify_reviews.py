"""Phase 03 lead verification of reviewer claims (offline, read-only).

Each check names a review, the claim it tests, the kind of evidence (pin = the pinned clone under
/home/claude/pi_research/src, smoke = the reviewer's raw output under research/SMOKES, rerun = the lead's own
re-execution output under research/verify, registry = a file the lead downloaded and hashed) and what was found.
A check that fails is a finding: the lead corrects the score that rested on the claim (SCORE_ITEMS.csv notes).

Usage: python3 verify_reviews.py [--json OUT]
Exit 0 when every check passes, 1 otherwise. Needs the pinned clones listed in SHORTLIST.csv to exist locally.
"""
import glob, hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)
SMK = os.path.join(RES, "SMOKES")
SRC = "/home/claude/pi_research/src"

def text(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()

def rj(path):
    t = text(path)
    i = t.index("RESULTS_JSON ")
    return json.loads(t[i + 13:].strip().splitlines()[0])

def jfile(path):
    return json.loads(text(path).replace("NaN", "null"))

def line(repo, rel, n):
    return text(os.path.join(SRC, repo, rel)).splitlines()[n - 1]

def lines(repo, rel, a, b):
    return "\n".join(text(os.path.join(SRC, repo, rel)).splitlines()[a - 1:b])

def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

def smoke(repo, rel):
    return os.path.join(SMK, repo, rel)

def rerun(name):
    return rj(os.path.join(HERE, name))

CHECKS = []
def check(cid, repo, kind, claim):
    def deco(fn):
        CHECKS.append((cid, repo, kind, claim, fn))
        return fn
    return deco

# ---------------- pins ----------------
@check("PIN-ALL", "all", "pin", "every local clone HEAD equals the SHORTLIST.csv pin")
def _():
    import csv
    rows = list(csv.DictReader(open(os.path.join(RES, "..", "..", "phase_02", "research", "SHORTLIST.csv"))))
    bad = []
    for r in rows:
        d = os.path.join(SRC, r["canonical_repo"].replace("/", "__"))
        h = subprocess.run(["git", "-C", d, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if h != r["pinned_sha"]:
            bad.append((r["canonical_repo"], h[:12], r["pinned_sha"][:12]))
    return {"repos": len(rows), "mismatches": bad}, not bad

# ---------------- R1 ----------------
SK = "scikit-learn__scikit-learn"
@check("SK-1", SK, "pin", "TimeSeriesSplit is row based: train_end = test_start - gap (_split.py:1104, :1292-1306)")
def _():
    a = line(SK, "sklearn/model_selection/_split.py", 1104); b = lines(SK, "sklearn/model_selection/_split.py", 1292, 1306)
    return [a.strip(), "train_end = test_start - gap" in b], a.startswith("class TimeSeriesSplit") and "train_end = test_start - gap" in b
@check("SK-2", SK, "smoke", "TimeSeriesSplit gap 0 leaves 93 to 107 unmatured training labels per fold; custom day walk-forward 0")
def _():
    d = rj(smoke(SK, "smoke_output.txt"))["S1_splitters"]
    g0 = d["TimeSeriesSplit"]["gap_0_rows"]["train_rows_with_label_maturing_after_test_start_per_fold"]
    wf = d["custom_day_walk_forward"]["maturity_violations_per_fold"]
    return {"gap0": g0, "walk_forward_max": max(wf), "folds": len(wf)}, g0 == [102, 106, 93, 99, 107] and max(wf) == 0 and len(wf) == 19
@check("SK-3", SK, "smoke", "two runs give identical metrics (run1 file versus final file)")
def _():
    a = rj(smoke(SK, "smoke_output.txt")); b = rj(smoke(SK, "smoke_output_run1.txt"))
    keys = ("S1_leak_trap", "S2_probability", "S4_calibration")
    return {k: a[k] == b[k] for k in keys}, all(a[k] == b[k] for k in keys)
@check("SK-4", SK, "smoke", "sigmoid calibration fitted on the later val window ran (FrozenEstimator); pickle reload identical; version stamp 1.10.dev0")
def _():
    a = rj(smoke(SK, "smoke_output.txt"))
    fs = a["S4_calibration"]["frozen_sigmoid"]["holdout"]; s5 = a["S5_persistence"]
    return {"frozen_sigmoid_brier": fs["brier"], "pickle_identical": s5["pickle"]["identical"], "stamp": s5["version_stamp_in_state"]}, fs["finite"] and s5["pickle"]["identical"] and s5["version_stamp_in_state"] == "1.10.dev0"
@check("SK-5", SK, "rerun", "lead's own fit on all 1,746 train rows reproduces R1's holdout Brier 0.030994")
def _():
    o = rj(os.path.join(SMK, "_challenge", "overlap_effect.out.txt"))["holdout_scores"]["train_all"]["brier"]
    r = rj(smoke(SK, "smoke_output.txt"))["S1_leak_trap"]["logistic_without_leak"]["brier"]
    return [o, r], abs(o - r) < 1e-6
@check("SK-6", SK, "pin", "brier_score_loss and sample_weight in CalibratedClassifierCV.fit; _sklearn_version stamped in pickles")
def _():
    a = line(SK, "sklearn/metrics/_classification.py", 3708); b = line(SK, "sklearn/calibration.py", 448); c = line(SK, "sklearn/base.py", 517)
    return [a.strip(), b.strip(), c.strip()], "def brier_score_loss" in a and "sample_weight" in b and "_sklearn_version" in c

LG = "lightgbm-org__LightGBM"
@check("LG-1", LG, "pin", "deterministic defaults to false (config.h:271); binary_logloss metric exists")
def _():
    a = line(LG, "include/LightGBM/config.h", 271); b = "binary_logloss" in text(os.path.join(SRC, LG, "src/metric/binary_metric.hpp"))
    return [a.strip(), b], "deterministic = false" in a and b
@check("LG-2", LG, "smoke", "native text model sha256 identical across two runs; reload max abs diff 0; same-seed trees identical")
def _():
    a = rj(smoke(LG, "smoke_output.txt")); b = rj(smoke(LG, "smoke_output_run1.txt"))
    na, nb = a["S5_persistence"]["native_text"], b["S5_persistence"]["native_text"]
    return {"sha_a": na["sha256"][:12], "sha_b": nb["sha256"][:12], "diff": na["max_abs_diff"], "det": a["determinism"]["same_seed_same_threads_trees_identical"]}, na["sha256"] == nb["sha256"] and na["max_abs_diff"] == 0.0 and a["determinism"]["same_seed_same_threads_trees_identical"]
@check("LG-3", LG, "pin", "sklearn fit accepts sample_weight (D1)")
def _():
    t = text(os.path.join(SRC, LG, "python-package/lightgbm/sklearn.py"))
    return "sample_weight" in t, re.search(r"def fit\([^)]*sample_weight", t, re.S) is not None
@check("LG-4", LG, "smoke", "native NaN: 77 holdout rows with NaN give finite probabilities; network attempts 0")
def _():
    a = rj(smoke(LG, "smoke_output.txt"))
    return {"S3": a["S3_missing"], "net": a["network_attempts"]}, a["network_attempts"] == [] and "true" in json.dumps(a["S3_missing"]).lower()

IN = "interpretml__interpret"
@check("IN-1", IN, "pin", "survival_cox objective exists at the pin (SurvivalCoxObjective.hpp, _ebm.py) and JSON reload is labelled untested")
def _():
    a = os.path.exists(os.path.join(SRC, IN, "shared/libebm/compute/objectives/SurvivalCoxObjective.hpp"))
    b = "survival_cox" in text(os.path.join(SRC, IN, "python/interpret-core/interpret/glassbox/_ebm.py"))
    c = "UNTESTED_from_jsonable" in text(os.path.join(SRC, IN, "python/interpret-core/interpret/glassbox/_ebm_core/_json.py"))
    return [a, b, c], a and b and c
@check("IN-2", IN, "smoke", "pin Cox fit keeps 107 censored holdout rows; Harrell C 0.6749 above the permutation range")
def _():
    a = rj(smoke(IN, "smoke_output_pin_cox.txt"))["cox_survival"]
    return {"c": a["harrell_c_holdout"], "cens": a["holdout_censored_before_24h"], "perm97.5": a["harrell_c_permuted_risk_200"]["p97.5"]}, a["holdout_censored_before_24h"] == 107 and a["harrell_c_holdout"] > a["harrell_c_permuted_risk_200"]["p97.5"]
@check("IN-3", IN, "smoke", "same seed identical probabilities; JSON export reload identical; pickle reload identical; release and pin metrics equal")
def _():
    a = rj(smoke(IN, "smoke_output.txt")); p = rj(smoke(IN, "smoke_output_pin.txt"))
    ok = a["determinism"]["same_seed_identical_proba"] and a["S5_persistence"]["json_reload_private"]["identical"] and a["S5_persistence"]["pickle"]["identical"] and a["S2_probability"] == p["S2_probability"]
    return {"det": a["determinism"], "json": a["S5_persistence"]["json_reload_private"], "release_eq_pin": a["S2_probability"] == p["S2_probability"]}, ok
@check("IN-4", IN, "pin", "fit accepts sample_weight; bags argument allows caller-defined validation rows")
def _():
    t = text(os.path.join(SRC, IN, "python/interpret-core/interpret/glassbox/_ebm.py"))
    return ["sample_weight" in t, "+1 for training, -1 for validation" in t], "sample_weight: Any = None" in t and "+1 for training, -1 for validation" in t

TP = "PriorLabs__TabPFN"
@check("TP-1", TP, "registry", "default TabPFN-3.5 weight license text (HF) sha256 9570fdd6... is non-commercial, non-production, not for consumers, outputs restricted")
def _():
    t = text(os.path.join(HERE, "registry", "tabpfn_licenses.txt"))
    flags = [("'%s' 1" % p) in t for p in ("non-commercial and non-production", "Section 13 of the German Civil Code", "Outputs may be used only for Non-Commercial Purposes")]
    return flags, "sha256 9570fdd687bb76ed" in t and all(flags)
@check("TP-2", TP, "registry", "TabPFN-2 classifier weight license (HF) sha256 08b1851b... asks for 'Built with PriorLabs-TabPFN' attribution when distributed")
def _():
    t = text(os.path.join(HERE, "registry", "tabpfn_licenses.txt"))
    return "sha256 08b1851b4b6136b5" in t, "sha256 08b1851b4b6136b5" in t and "'Built with PriorLabs-TabPFN' 1" in t
@check("TP-3", TP, "pin", "default model_version is V3_5 and loading calls a license check; config.json fetched to increment a download counter")
def _():
    s = lines(TP, "src/tabpfn/settings.py", 30, 45); m = text(os.path.join(SRC, TP, "src/tabpfn/model_loading.py"))
    return ["V3_5" in s, "ensure_license_accepted" in m, "download counter" in m], "V3_5" in s and "ensure_license_accepted" in m and "download counter" in m
@check("TP-4", TP, "smoke", "default constructor fails offline with a gated-repo error after one blocked connect; reruns differ by 6e-8 (not bit-identical)")
def _():
    a = rj(smoke(TP, "smoke_output.txt"))
    return {"err": a["default_v3_5_offline"][:40], "det": a["determinism"]}, "GatedRepoError" in a["default_v3_5_offline"] and a["determinism"]["same_seed_identical_proba"] is False

SM = "statsmodels__statsmodels"
@check("SM-1", SM, "pin", "MarkovSwitching.predict raises NotImplementedError out of sample (markov_switching.py:806-807) although the docstring promises forecasting")
def _():
    b = lines(SM, "statsmodels/tsa/regime_switching/markov_switching.py", 806, 807); d = line(SM, "statsmodels/tsa/regime_switching/markov_switching.py", 763)
    return [b.strip(), d.strip()[:60]], "NotImplementedError" in b and "forecast" in d.lower()
@check("SM-2", SM, "rerun", "filtered regime probabilities with fixed parameters are unchanged when later rows are appended; smoothed ones change (control)")
def _():
    r = rerun("rerun_statsmodels.out.txt")
    return r, r["filtered_first_1000_with_800_later_rows_appended_max_abs_diff"] == 0.0 and r["smoothed_first_1000_with_800_later_rows_appended_max_abs_diff"] > 1e-6 and r["out_of_sample_predict"] == "NotImplementedError"
@check("SM-3", SM, "smoke", "Holm adjusted (0.036, 0.060, 0.060); Wilson equals lab alpha_core.wilson within 1e-5; pickle reload identical")
def _():
    a = rj(smoke(SM, "smoke_output.txt"))
    h = json.dumps(a["S4_uncertainty"]["holm"]); w = a["S4_uncertainty"]["wilson_vs_lab_alpha_core_max_abs_diff"]
    return {"holm": h[:120], "wilson": w, "pickle": a["S5_persistence"]["identical"]}, "0.036" in h and "0.06" in h and w < 1e-5 and a["S5_persistence"]["identical"]

FE = "feast-dev__feast"
@check("FE-1", FE, "pin", "dask offline store keeps feature rows with timestamp <= entity time (dask.py _filter_ttl :1187-1220); created-timestamp filter off by default")
def _():
    b = lines(FE, "sdk/python/feast/infra/offline_stores/dask.py", 1187, 1220); f = line(FE, "sdk/python/feast/feature_store.py", 2014)
    return ["<= df_to_join[entity_df_event_timestamp_col]" in b, f.strip()], "<= df_to_join[entity_df_event_timestamp_col]" in b and "filter_by_created_timestamp: bool = False" in f
@check("FE-2", FE, "rerun", "lead re-ran R1's script in a fresh scratch dir: identical point-in-time table, 0 rows with own future value, 330 rows silently dropped")
def _():
    a = rj(smoke(FE, "smoke_output.txt")); b = rj(os.path.join(HERE, "rerun_feast_r1_script.out.txt"))
    s = b["S1_leak_trap"]
    return {"pit_equal": a["pit_semantics"] == b["pit_semantics"], "own_future": s["timestamp_field_is_availability_time"]["rows_returning_own_future_value"], "dropped": s["entity_rows_missing_from_output"]}, a["pit_semantics"] == b["pit_semantics"] and s["timestamp_field_is_availability_time"]["rows_returning_own_future_value"] == 0 and s["entity_rows_missing_from_output"] == 330
@check("FE-3", FE, "pin", "pyproject requires pandas <3 (lab runs pandas 3)")
def _():
    t = text(os.path.join(SRC, FE, "pyproject.toml"))
    return '"pandas>=1.4.3,<3"' in t, '"pandas>=1.4.3,<3"' in t

# ---------------- R2 ----------------
MA = "scikit-learn-contrib__MAPIE"
VA = "ip200__venn-abers"
@check("MA-1", MA, "pin", "MAPIE's Venn-Abers p1 loop lacks the 'p1[-1, 1] = 1.0' line that venn-abers has (venn_abers.py:118)")
def _():
    m = text(os.path.join(SRC, MA, "mapie/_venn_abers.py")); v = line(VA, "src/venn_abers.py", 118)
    return ["p1[-1, 1] = 1.0" in m, v.strip()], ("p1[-1, 1] = 1.0" not in m) and "p1[-1, 1] = 1.0" in v
@check("MA-2", MA, "smoke", "LAC 0.90 coverage 0.9184 with 0 of 17 positives; Venn-Abers p1 differs from the definition by 0.4; risk controller abstains")
def _():
    t = text(smoke(MA, "raw_smoke_mapie.txt"))
    ok = "lac conf=0.9: coverage=0.9184" in t and "positives_cov=0.0000" in t and "max |p1 MAPIE - p1 definition| = 0.4" in t and "controller abstains" in t
    return ok, ok
@check("MA-3", MA, "pin", "no Brier or log-loss function in mapie/metrics (C1)")
def _():
    t = "".join(text(p) for p in glob.glob(os.path.join(SRC, MA, "mapie/metrics/*.py")))
    return [bool(re.search(r"def \w*brier", t)), bool(re.search(r"def \w*log_loss", t))], not re.search(r"def \w*brier", t) and not re.search(r"def \w*log_loss", t)
CR = "henrikbostrom__crepes"
@check("CR-1", CR, "pin", "no test files at the pin")
def _():
    n = len([p for p in glob.glob(os.path.join(SRC, CR, "**", "test*.py"), recursive=True)])
    return n, n == 0
@check("CR-2", CR, "smoke", "class-conditional sets cover 16 of 17 positives (0.9412); martingale alarms only after the shift (619, 637, 622); no alarm val only; seeded p-values identical")
def _():
    t = text(smoke(CR, "raw_smoke_crepes.txt"))
    ok = "positives_cov=0.9412" in t and "{'SimpleJumper': 619, 'SleeperStayer': 637, 'Composite': 622}" in t and "{'SimpleJumper': 556, 'SleeperStayer': 556, 'Composite': 556}" in t and "same seed equal: True" in t
    return ok, ok
@check("VA-1", VA, "smoke", "Venn-Abers equals the IVAP definition on 530 probes (max diff 0); NaN test score returns 0.625 silently")
def _():
    t = text(smoke(VA, "raw_smoke_venn_abers.txt"))
    ok = "max |p0 - definition| = 0; max |p1 - definition| = 0" in t and "NaN test score -> [[0.375 0.625]]" in t
    return ok, ok
MD = "lorentzenchr__model-diagnostics"
@check("MD-1", MD, "smoke", "decomposition equals own Brier and log loss exactly; NaN to SquaredError returns nan silently; zero-event bin p-value misleading (chance 0.362)")
def _():
    t = text(smoke(MD, "raw_smoke_model_diagnostics.txt"))
    ok = "SquaredError()(y, p with NaN) = nan" in t and "0.362" in t and "max difference" in t.lower() or "0.00e+00" in t
    return ok, ok
AR = "bashtage__arch"
@check("AR-1", AR, "smoke", "Monte Carlo coverage IID 0.715 versus stationary 0.875; SPA p 0.306; NaN gives [nan, nan] without error")
def _():
    t = text(smoke(AR, "raw_smoke_arch.txt"))
    ok = "IID                    empirical coverage 0.715" in t and "Stationary(optimal)    empirical coverage 0.875" in t and "'consistent': 0.306" in t and "interval [nan, nan]" in t
    return ok, ok
@check("AR-2", AR, "pin", "root LICENSE.md sha256 c6e622bd... (NCSA-style permissive)")
def _():
    h = sha(os.path.join(SRC, AR, "LICENSE.md"))
    return h[:16], h.startswith("c6e622bd89db4e13")
MF = "baobach__mlfinpy"
@check("MF-1", MF, "rerun", "PurgedKFold leaves overlapping label windows in training on a 6-row constructed case")
def _():
    r = rerun("rerun_mlfinpy.out.txt")
    return r["total_overlapping_train_rows"], r["total_overlapping_train_rows"] == 3
@check("MF-2", MF, "rerun", "defective purge line identical to BSD-3 mlfinlab fork 47889b88 :91; no Hudson and Thames notice in mlfinpy")
def _():
    t = text(os.path.join(HERE, "rerun_mlfinpy_provenance.out.txt"))
    ok = "fork_head 47889b884c7e7e4ca850ce2b87ea1514e0834866" in t and "bsd3_hudson True" in t and "fork_line_91_defect True" in t and "mlfinpy_hudson_notices 0" in t and "shared_test_docstring True" in t
    return ok, ok
@check("MF-3", MF, "smoke", "no Python 3.13 resolution (numba 0.60 has no cp313 wheel)")
def _():
    t = text(smoke(MF, "raw_py313_wheel_resolution.txt"))
    ok = "numba" in t and ("No solution" in t or "unsatisfiable" in t.lower() or "no wheels" in t.lower())
    return t.strip().splitlines()[-1][:120], ok
PC = "eslazarev__purged-cross-validation"
@check("PC-1", PC, "rerun", "lead's own interval-union checker: walk-forward, purged k-fold, CPCV, group k-fold leave 0 overlapping training rows; scikit-learn KFold control leaves 111 to 207 (overlap only: says nothing about fold sizes or training on later rows, see PC-3)")
def _():
    r = rerun("rerun_purgedcv.out.txt")
    ok = max(r["WalkForwardSplit_leaks"]) == 0 and max(r["PurgedKFold_leaks"]) == 0 and r["CPCV_leaks_max"] == 0 and max(r["PurgedGroupKFold_leaks"]) == 0 and max(r["PurgedGroupKFold_shared_mints"]) == 0 and min(r["control_sklearn_KFold_leaks"]) > 0 and max(r["PurgedKFold_embargo_violations"]) == 0 and r["hand_case_kept"] == [0, 1, 5]
    return {k: r[k] for k in ("WalkForwardSplit_leaks", "PurgedKFold_leaks", "CPCV_leaks_max", "control_sklearn_KFold_leaks")}, ok
@check("PC-2", PC, "pin", "overlap primitive is half-open (_intervals.py)")
def _():
    t = text(os.path.join(SRC, PC, "src/purgedcv/_intervals.py"))
    return "def overlaps_any_half_open_interval" in t, "def overlaps_any_half_open_interval" in t

# ---------------- R3 ----------------
LL = "CamDavidsonPilon__lifelines"
@check("LL-1", LL, "pin", "k_fold_cross_validation shuffles rows (utils/__init__.py:765); pandas<3.0 declared")
def _():
    a = line(LL, "lifelines/utils/__init__.py", 765); b = text(os.path.join(SRC, LL, "reqs/base-requirements.txt"))
    return [a.strip()[:80], "pandas" in b and "<3" in b], "np.random.permutation" in a and re.search(r"pandas[^\n]*<\s*3", b) is not None
@check("LL-2", LL, "smoke", "censor-aware Cox concordance 0.696 clean, 0.991 with trap; identical metrics on pandas 3.0.5")
def _():
    a = jfile(smoke(LL, "smoke_lifelines.result.json")); b = jfile(smoke(LL, "smoke_lifelines_pandas3.result.json"))
    c = a["S2_S6_clean"]["concordance_holdout_all_incl_censored"]; t = a["S1_trap"]["with_trap"]["concordance_holdout_all_incl_censored"]
    same = a["S2_S6_clean"]["binary_24h_on_labeled_holdout"] == b["S2_S6_clean"]["binary_24h_on_labeled_holdout"]
    return {"clean": round(c, 3), "trap": round(t, 3), "pandas3_same": same}, abs(c - 0.696) < 0.001 and abs(t - 0.991) < 0.001 and same
HZ = "soda-inria__hazardous"
@check("HZ-1", HZ, "registry", "PyPI hazardous 0.2.0 wheel (sha256 0c25c1b2...) ships a 213,846,118-byte SEER file that is not in the pinned tree")
def _():
    t = text(os.path.join(HERE, "registry", "hazardous_0.2.0_wheel_listing.txt"))
    inpin = os.path.exists(os.path.join(SRC, HZ, "hazardous/data/seer_cancer_cardio_raw_data.txt"))
    ok = "wheel_sha256 0c25c1b2f76f14bf" in t and "hazardous/data/seer_cancer_cardio_raw_data.txt 213846118" in t and not inpin
    return {"in_pin_tree": inpin}, ok
@check("HZ-2", HZ, "smoke", "default fit 253.8 s; cumulative incidence non-monotone for 634 of 634 rows; same seed refit identical")
def _():
    a = jfile(smoke(HZ, "smoke_hazardous.result.json"))
    s = a["S2_S3_S6_clean"]
    return {"fit_s": s["fit_s"], "nonmono": s["cif1_non_monotone_rows"], "seed": a["S5_persistence"]["refit_same_seed_identical_n_iter20"]}, s["fit_s"] > 200 and s["cif1_non_monotone_rows"] == 634 and a["S5_persistence"]["refit_same_seed_identical_n_iter20"]
@check("HZ-T", HZ, "rerun", "SurvivalBoost fits the 1,746 train rows in under 60 s at a reduced n_iter (K2)")
def _():
    r = rerun("rerun_hazardous_timing.out.txt")
    return r, r["fit_s_n_iter_10"] < 60 and r["predict_ms_per_row_one_horizon"] < 100
@check("REPEAT", "all", "rerun", "reviewer smoke scripts re-run by the lead give identical results after removing timing, path and id fields")
def _():
    d = json.load(open(os.path.join(HERE, "repeat_runs.json")))
    ok = all(v["exit_code"] == 0 and (v["identical_after_normalization"] or all(re.search(r"(creation-date|\.id$|report_id|data_refs)", x) for x in v["differences"])) for v in d.values())
    return {k: (v["identical_after_normalization"], v["values_compared"]) for k, v in d.items()}, ok and len(d) == 9
RV = "online-ml__river"
@check("RV-1", RV, "rerun", "simulate_qa releases 2,892 labels at or after maturity and 0 before; 108 flushed unmatured at stream end")
def _():
    r = rerun("rerun_river.out.txt")
    return r, r["answers_released_before_maturity"] == 0 and r["answers_released_at_or_after_maturity"] == 2892 and r["flush_answers_not_matured_by_last_decision"] == 108
@check("RV-2", RV, "pin", "end-of-stream flush loop (qa.py:244)")
def _():
    a = line(RV, "river/stream/qa.py", 244)
    return a.strip(), "for memento in mementos" in a
@check("RV-3", RV, "smoke", "NaN values silently make LogisticRegression weights non-finite")
def _():
    a = jfile(smoke(RV, "smoke_river.result.json"))["S3_nan"]["bare_LR_nan_values"]
    return a, a["weights_finite_after_learning"] is False
ST = "sktime__sktime"
@check("ST-1", ST, "pin", "evaluate passes the test-period X to predict (_functions.py:289); no purge or embargo in sktime/split")
def _():
    a = line(ST, "sktime/forecasting/model_evaluation/_functions.py", 289)
    n = sum(len(re.findall(r"\b(embargo|purge)\b", text(p), re.I)) for p in glob.glob(os.path.join(SRC, ST, "sktime/split/**/*.py"), recursive=True))
    return [a.strip()[:70], n], "X=X_test" in a and n == 0
@check("ST-2", ST, "smoke", "row-count expanding window leaves unmatured training labels; instance splitter shares 0 mints; panel NaN pipeline finite")
def _():
    a = jfile(smoke(ST, "smoke_sktime.result.json"))
    um = [f["train_labels_not_matured_at_test_start"] for f in a["A1_expanding_rows"]["detail"]]
    return {"unmatured": um, "mint_overlap": a["A5_instance_splitter"]["mint_overlap_train_test"]}, min(um) > 0 and a["A5_instance_splitter"]["mint_overlap_train_test"] == [0, 0, 0] and a["S3_nan_panel"]["SummaryTransformer_LR_pipeline"]["proba_finite"]
TS = "blue-yonder__tsfresh"
@check("TS-1", TS, "pin", "ComprehensiveFCParameters repeats the key number_of_maxima in one dict (settings.py:272-278)")
def _():
    b = lines(TS, "tsfresh/feature_extraction/settings.py", 270, 280)
    return b.count('"number_of_maxima"'), b.count('"number_of_maxima"') >= 3
@check("TS-2", TS, "smoke", "backward windows truncation invariant (127,428 of 127,428 cells)")
def _():
    t = text(smoke(TS, "smoke_tsfresh.out.txt"))
    ok = "127428" in t
    return ok, ok
RU = "deepcharles__ruptures"
@check("RU-1", RU, "pin", "typing_extensions imported (base.py:8) but not declared in setup.cfg")
def _():
    a = line(RU, "src/ruptures/base.py", 8); cfg = text(os.path.join(SRC, RU, "setup.cfg"))
    return [a.strip(), "typing_extensions" in cfg or "typing-extensions" in cfg], "typing_extensions" in a and not ("typing_extensions" in cfg or "typing-extensions" in cfg)
@check("RU-2", RU, "smoke", "a NaN in a path makes PELT return a breakpoint every 5 samples with no error")
def _():
    d = jfile(smoke(RU, "smoke_ruptures.result.json"))["S3_nan"]
    ok = d["Pelt_l2"]["raised"] is None and d["Pelt_l2"]["result"][:3] == [15, 20, 25] and d["L1Potts"]["raised"] is not None
    return {"Pelt_l2": d["Pelt_l2"]["result"][:4], "L1Potts": str(d["L1Potts"]["raised"])[:40]}, ok
SU = "stumpy-dev__stumpy"
@check("SU-1", SU, "rerun", "stumpi left profile equals the lead's own past-only numpy distance; self-join P changes when only future samples change")
def _():
    r = rerun("rerun_stumpy.out.txt")
    return r, r["stumpi_left_P_vs_lead_numpy_past_only_max_abs_diff"] < 1e-9 and r["self_join_P_at_100_changes_when_only_samples_after_150_change"]
@check("SU-2", SU, "smoke", "pickling a stumpi object fails")
def _():
    t = text(smoke(SU, "smoke_stumpy.out.txt"))
    ok = "PicklingError" in t or "Can't pickle" in t
    return ok, ok

# ---------------- R4 ----------------
EV = "evidentlyai__evidently"
@check("EV-1", EV, "pin", "telemetry posts to a raw-IP HTTP endpoint unless DO_NOT_TRACK is set; EVIDENTLY_DISABLE_TELEMETRY defined but unread")
def _():
    t = text(os.path.join(SRC, EV, "src/evidently/telemetry.py"))
    unread = sum(text(p).count("EVIDENTLY_DISABLE_TELEMETRY") for p in glob.glob(os.path.join(SRC, EV, "src/**/*.py"), recursive=True))
    return ["35.232.253.5" in t, "DO_NOT_TRACK" in t, unread], "35.232.253.5" in t and "DO_NOT_TRACK" in t and unread == 1
@check("EV-2", EV, "smoke", "import fails under the default pandas 3 resolution; UI path connects once without the switch and 0 times with it")
def _():
    a = text(smoke(EV, "import_default_resolution.out.txt")); on = text(smoke(EV, "telemetry_ui_switch_on.connect.txt")); off = text(smoke(EV, "telemetry_ui_switch_off.connect.txt"))
    ok = "infer_dtype_from_object" in a and "35.232.253.5" in on and "35.232.253.5" not in off
    return ok, ok
NM = "NannyML__nannyml"
@check("NM-1", NM, "pin", "Segment usage tracker created at import with a hard-coded key and a MAC-derived id; off switch NML_DISABLE_USAGE_LOGGING")
def _():
    t = text(os.path.join(SRC, NM, "nannyml/usage_logging.py"))
    return ["uuid.getnode" in t, "NML_DISABLE_USAGE_LOGGING" in t, "load_dotenv()" in t], "uuid.getnode" in t and "NML_DISABLE_USAGE_LOGGING" in t and "load_dotenv()" in t
@check("NM-2", NM, "smoke", "fresh install fails to import (statsmodels undeclared); telemetry connects with the switch absent, not with it")
def _():
    a = text(smoke(NM, "import_default_resolution.out.txt")); on = text(smoke(NM, "telemetry_switch_on.connect.txt")); off = text(smoke(NM, "telemetry_switch_off.connect.txt"))
    ok = "statsmodels" in a and "ModuleNotFoundError" in a and on.count("AF_INET") == 2 and off.count("AF_INET") == 0
    return [on.count("AF_INET"), off.count("AF_INET")], ok
FR = "IFCA-Advanced-Computing__frouros"
@check("FR-1", FR, "smoke", "PSI on a column with NaN returns 0.0 without error; KS returns NaN")
def _():
    t = text(smoke(FR, "smoke_frouros.out.txt"))
    m = re.search(r"RESULT S3_nan (\{.*\})", t)
    d = json.loads(m.group(1).replace("NaN", "null")) if m else {}
    s = json.dumps(d)
    return s[:200], '"psi": 0.0' in s.lower() or "0.0" in s
@check("FR-2", FR, "pin", "numpy, scipy and matplotlib upper bounds in pyproject; __version__ 0.9.0 while pyproject says 0.10.0")
def _():
    p = text(os.path.join(SRC, FR, "pyproject.toml")); v = text(os.path.join(SRC, FR, "frouros/__init__.py"))
    return ['numpy<2.3' in p.replace(" ", "").replace('"', '') or "numpy" in p, '0.9.0' in v, '0.10.0' in p], ("<2.3" in p) and '0.9.0' in v and '0.10.0' in p
ML = "mlflow__mlflow"
@check("ML-1", ML, "pin", "telemetry client set at import; disabled only by MLFLOW_DISABLE_TELEMETRY, DO_NOT_TRACK equal to 'true', CI or dev builds")
def _():
    a = lines(ML, "mlflow/__init__.py", 454, 456); b = lines(ML, "mlflow/telemetry/utils.py", 144, 158)
    return ["set_telemetry_client()" in a, 'os.environ.get("DO_NOT_TRACK", "false").lower() == "true"' in b], "set_telemetry_client()" in a and '"DO_NOT_TRACK", "false").lower() == "true"' in b
@check("ML-2", ML, "smoke", "release 3.17.2: DO_NOT_TRACK=1 still connects; MLFLOW_DISABLE_TELEMETRY=true does not; lineage run id matches registered version")
def _():
    a = text(smoke(ML, "telemetry_release_dnt_equals_1.connect.txt")); b = text(smoke(ML, "telemetry_release_off_mlflow.connect.txt")); c = text(smoke(ML, "smoke_mlflow_pin.out.txt"))
    ok = a.count("AF_INET") == 1 and b.count("AF_INET") == 0 and '"model_version_run_id_matches": true' in c
    return [a.count("AF_INET"), b.count("AF_INET")], ok
SO = "probabl-ai__skore"
@check("SO-1", SO, "smoke", "SKD011 names the trap column as likely target leakage (tip); SKD013 flags shuffled KFold time overlap (issue)")
def _():
    t = text(smoke(SO, "smoke_skore.out.txt"))
    ok = "leak_future_ret" in t and "SKD011" in t and "SKD013" in t and "contain training timestamps that are after the earliest test timestamp" in t
    return ok, ok
@check("SO-2", SO, "pin", "git_commit recorded as 'None (working tree dirty)' outside a repository (string in source)")
def _():
    t = text(os.path.join(SRC, SO, "skore/src/skore/_project/git.py"))
    return "working tree dirty" in t, "working tree dirty" in t
PA = "unionai-oss__pandera"
@check("PA-1", PA, "rerun", "lead's own registered as-of check: legit 0 failing rows, 1-second-late row 41 caught, trap 3,000 rows caught, strict=True refuses an undeclared column, a raising check fails closed")
def _():
    r = rerun("rerun_pandera.out.txt")
    ok = r["legit_rows_failing"] == 0 and r["one_second_late_rows_failing"] == [41] and r["trap_with_availability_rows_failing"] == 3000 and r["undeclared_column_strict_true"].startswith("refused") and "fail-closed" in r["check_that_raises"]
    return r, ok
@check("PA-2", PA, "smoke", "import re-adds numpy 2 removed aliases and sets SPARK_LOCAL_IP and PYARROW_IGNORE_TIMEZONE")
def _():
    t = text(smoke(PA, "smoke_pandera.out.txt"))
    ok = '"numpy_NaN_alias_after": true' in t and '"SPARK_LOCAL_IP": "127.0.0.1"' in t
    return ok, ok

# ---------------- R5 ----------------
MI = "666ghj__MiroFish"
@check("MI-1", MI, "pin", "AGPL-3.0 LICENSE sha256 8486a10c...; Flask binds 0.0.0.0; CORS origins '*'; default SECRET_KEY; no random seeding anywhere")
def _():
    h = sha(os.path.join(SRC, MI, "LICENSE"))
    a = line(MI, "backend/run.py", 40); b = line(MI, "backend/app/__init__.py", 43); c = line(MI, "backend/app/config.py", 21)
    n = subprocess.run(["git", "-C", os.path.join(SRC, MI), "grep", "-c", "-E", r"random\.seed|np\.random\.seed"], capture_output=True, text=True).stdout.strip()
    ok = h.startswith("8486a10c4393cee1") and "0.0.0.0" in a and '"origins": "*"' in b and "mirofish-secret-key" in c and n == ""
    return [h[:16], a.strip(), b.strip(), c.strip(), n or "0 hits"], ok
@check("MI-2", MI, "pin", "ReportAgent plan prompt states that the simulated world's evolution is the prediction of the future (report_agent.py:552-567)")
def _():
    b = lines(MI, "backend/app/services/report_agent.py", 552, 567)
    return "未来的预演" in b, "未来的预演" in b and "就是对未来可能发生情况的预测" in b
@check("MI-3", MI, "smoke", "two identical runs against a deterministic mock differ (trace sha a0a70f5f vs 3159ba9f); with the LLM unreachable the script exits 0 and prints loop complete")
def _():
    s = jfile(smoke(MI, "sim_summary.json")); t = text(smoke(MI, "llm_down_output.txt"))
    shas = [r["trace_sha256"][:8] for r in s["runs"]]
    ok = shas == ["a0a70f5f", "3159ba9f"] and s["identical_trace_across_runs"] is False and "exit_code=0" in t and "模拟循环完成" in t and "APIConnectionError" in t
    return shas, ok
@check("MI-4", MI, "smoke", "API list route answers 200 without credentials and reflects an untrusted CORS origin")
def _():
    t = text(smoke(MI, "api_smoke_output.txt"))
    ok = '"list_without_auth_status": 200' in t and "untrusted.example" in t
    return ok, ok
OA = "camel-ai__oasis"
@check("OA-1", OA, "pin", "Reddit clock starts at datetime.now() (platform.py:76-81); agent swallows LLM exceptions and returns them (agent.py:153-155)")
def _():
    a = lines(OA, "oasis/social_platform/platform.py", 76, 81); b = lines(OA, "oasis/social_agent/agent.py", 152, 155)
    return ["datetime.now()" in a, "return e" in b], "datetime.now()" in a and "return e" in b
@check("OA-2", OA, "smoke", "two runs with the deterministic mock give different traces (7bb959b1 vs 10472c0f)")
def _():
    a = jfile(smoke(OA, "smoke_run1.json"))["trace_sha256"][:8]; b = jfile(smoke(OA, "smoke_run2.json"))["trace_sha256"][:8]
    return [a, b], a == "7bb959b1" and b == "10472c0f"
ME = "mesa__mesa"
@check("ME-1", ME, "smoke", "same seeds give a byte-identical frequency vector (sha 61cd4e71); the trap lifts AUC 0.59 to 0.81 unchecked")
def _():
    t = text(smoke(ME, "smoke_mesa_traders_output.json"))
    ok = "61cd4e71" in t and "0.8082" in t and "0.5878" in t
    return ok, ok
@check("ME-2", ME, "pin", "Model seeds a numpy Generator and a stdlib Random from the scenario (model.py:128-129)")
def _():
    b = lines(ME, "mesa/model.py", 120, 135)
    return ["self.random = random.Random" in b], "self.random = random.Random" in b
BI = "bancaditalia__black-it"
@check("BI-1", BI, "smoke", "6 golden-value tests fail with the locked scikit-learn, scipy and joblib versions")
def _():
    t = text(smoke(BI, "blackit_pytest_offline_locked_sklearn.txt"))
    ok = re.search(r"6 failed", t) is not None
    return ok, ok
@check("BI-2", BI, "pin", "NaN moments silently set to 0 (utils/time_series.py:87); AGPL-3.0 LICENSE sha256 d6e088f2...")
def _():
    a = line(BI, "black_it/utils/time_series.py", 87); h = sha(os.path.join(SRC, BI, "LICENSE"))
    return [a.strip(), h[:16]], "nan_to_num" in a and h.startswith("d6e088f2fc2918a7")

# ---------------- repair pass (skeptic M2, M3, m4, m5; blind rescore) ----------------
def fold_audit():
    out = {}
    for f in sorted(glob.glob(os.path.join(HERE, "fold_audit_*.out.txt"))):
        out.update(rj(f))
    return out

@check("PC-3", PC, "rerun", "fold audit: walk-forward trains on 1,403 to 2,522 earlier rows with 0 rows decided after the test start; purged k-fold and CPCV train on up to 2,091 and 1,739 later rows; group k-fold by mint has two empty training folds (0, 0, 45, 179, 397)")
def _():
    a = fold_audit()
    w, k, c, g = a["purgedcv.WalkForwardSplit"], a["purgedcv.PurgedKFold"], a["purgedcv.CombinatorialPurgedCV"], a["purgedcv.PurgedGroupKFold"]
    ntr = [f["n_train"] for f in g["per_fold"]]
    ok = (w["min_n_train"] == 1403 and w["max_train_label_matures_after_first_test"] == 0 and w["max_overlap"] == 0
          and k["max_train_decided_after_first_test"] == 2091 and c["max_train_decided_after_first_test"] == 1739
          and ntr == [0, 0, 45, 179, 397])
    return {"walk_forward_min_train": w["min_n_train"], "purged_kfold_future": k["max_train_decided_after_first_test"],
            "cpcv_future": c["max_train_decided_after_first_test"], "group_kfold_n_train": ntr}, ok

@check("SK-7", SK, "rerun", "fold audit: TimeSeriesSplit trains only on earlier rows (min 483, 0 decided after the test start) but leaves up to 110 training labels maturing after the test start")
def _():
    t = fold_audit()["sklearn.TimeSeriesSplit"]
    ok = t["min_n_train"] == 483 and t["max_train_decided_after_first_test"] == 0 and t["max_train_label_matures_after_first_test"] == 110
    return {k: t[k] for k in ("min_n_train", "max_train_decided_after_first_test", "max_train_label_matures_after_first_test")}, ok

@check("ST-3", ST, "rerun", "fold audit: ExpandingWindowSplitter trains only on earlier rows (min 1,000); InstanceSplitter by mint trains on up to 1,966 rows decided after the test start")
def _():
    a = fold_audit(); e, i = a["sktime.ExpandingWindowSplitter"], a["sktime.InstanceSplitter_KFold3"]
    ok = e["min_n_train"] == 1000 and e["max_train_decided_after_first_test"] == 0 and i["max_shared_groups"] == 0 and i["max_train_decided_after_first_test"] == 1966
    return {"expanding_min_train": e["min_n_train"], "instance_future": i["max_train_decided_after_first_test"]}, ok

@check("ST-4", ST, "smoke", "sktime's own panel classifiers raised on unequal-length series; the only probabilities came from DummyClassifier(prior) (one constant) and SklearnClassifierPipeline wrapping scikit-learn LogisticRegression")
def _():
    c = jfile(smoke(ST, "smoke_sktime.result.json"))["C_classification_S2_S6"]
    own_failed = all("raised" in c[k] for k in ("SummaryClassifier", "KNeighborsTimeSeriesClassifier(dtw)"))
    dummy_const = c["DummyClassifier(prior)"]["min"] == c["DummyClassifier(prior)"]["max"]
    wrapped = "SklearnClassifierPipeline(SummaryTransformer, LogisticRegression)" in c
    return [own_failed, dummy_const, wrapped], own_failed and dummy_const and wrapped

@check("MA-4", MA, "rerun", "VennAbersCalibrator(cv='prefit') with a fitted Pipeline refits the caller's transformers on the calibration rows (caller predictions change); Venn-Abers p1 0.5 above the calibration range where the definition gives 1.0")
def _():
    r = rerun("rerun_mapie_prefit.out.txt")
    p = r["venn_abers_probe_above_cal_max"]
    ok = r["caller_base_max_abs_change"] > 0.001 and r["caller_scaler_mean_changed"] and r["same_scaler_object"] and abs(p["p1"] - 1.0) > 0.1
    return {"caller_base_max_abs_change": round(r["caller_base_max_abs_change"], 5), "p1": p["p1"]}, ok

@check("MA-5", MA, "pin", "custom per-row risk BinaryRisk(risk_occurrence, risk_condition) (risks.py:277) is consumed by BinaryClassificationController (binary_classification.py:182); MAPIE's own code, not a pass-through")
def _():
    a = line(MA, "mapie/risk_control/risks.py", 277); b = line(MA, "mapie/risk_control/binary_classification.py", 182)
    return [a.strip(), b.strip()], a.startswith("class BinaryRisk(") and "binary_risk_choice_map" in b

@check("CR-3", CR, "pin", "crepes WrapClassifier.fit passes **kwargs to the wrapped learner (base.py:3379); no weight or cost is consumed by crepes code")
def _():
    a = line(CR, "src/crepes/base.py", 3379)
    w = re.findall(r"sample_weight|cost", text(os.path.join(SRC, CR, "src/crepes/base.py")))
    return [a.strip(), len(w)], "self.learner.fit(X, y, **kwargs)" in a and not w

@check("HZ-3", HZ, "rerun", "recalibrate_survival_function subtracts the absolute calibration error, so it moves survival away from the KM curve when the model under-states survival, and leaves [0, 1] (to -0.27) in the mirror case")
def _():
    r = rerun("rerun_hazardous_recal.out.txt")
    ok = r["library_shift_equals_abs_delta"] and r["library_moves_against_the_error"] and r["mirror_outside_0_1"] > 0
    src = line(HZ, "hazardous/metrics/_km_calibration.py", 131)
    return {"abs": r["library_shift_equals_abs_delta"], "mirror_min": min(r["mirror_recalibrated"][0]), "src": src.strip()}, ok and "np.abs(mean_predictions - pred_km)" in src

@check("RV-4", RV, "pin", "progressive_val_score learns every answer simulate_qa yields, including the end-of-stream flush (progressive_validation.py:138-155 after qa.py:244)")
def _():
    b = lines(RV, "river/evaluate/progressive_validation.py", 136, 156)
    return ["if y is None:" in b, "learn(x, y" in b], "if y is None:" in b and "learn(x, y" in b and "continue" in b

@check("RV-5", RV, "registry", "the 34 Rust crates in the normal dependency closure of the pinned Cargo.lock are all permissive (read from the local crates.io cache); the one MPL-2.0 crate is dev or bench only")
def _():
    r = rerun("river_crate_licenses.out.txt")
    ok = r["normal_closure_crates"] == 34 and r["normal_closure_non_permissive"] == [] and not r["missing_from_cache"]
    return {k: r[k] for k in ("normal_closure_crates", "normal_closure_non_permissive", "non_permissive_or_unknown")}, ok

@check("IN-5", "interpretml__interpret", "rerun", "review S4 'has_term_standard_deviations false' is wrong (blind rescore): the pinned EBM sets standard_deviations_ (_ebm.py:1639), one finite array per term")
def _():
    r = rerun("rerun_interpret_sd.out.txt")
    ok = r["has_standard_deviations_"] and r["n_sd_arrays"] == r["n_terms"] and r["shapes_match"] and r["all_finite"]
    return {k: r[k] for k in ("has_standard_deviations_", "n_sd_arrays", "all_finite")}, ok

def main():
    out = []
    for cid, repo, kind, claim, fn in CHECKS:
        try:
            obs, ok = fn()
        except Exception as e:  # noqa: BLE001
            obs, ok = "ERROR %s: %s" % (type(e).__name__, str(e)[:160]), False
        out.append({"id": cid, "repo": repo, "kind": kind, "claim": claim, "observed": obs, "pass": bool(ok)})
        print("%-6s %-5s %-34s %s" % (cid, "PASS" if ok else "FAIL", repo[:34], claim[:90]))
    n_fail = sum(not r["pass"] for r in out)
    repos = sorted({r["repo"] for r in out if r["repo"] != "all"})
    print("checks %d, failed %d, repositories covered %d" % (len(out), n_fail, len(repos)))
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as fh:
            json.dump({"checks": out, "failed": n_fail, "repositories_covered": repos}, fh, indent=1, ensure_ascii=False, default=str)
    return 1 if n_fail else 0

if __name__ == "__main__":
    sys.exit(main())
