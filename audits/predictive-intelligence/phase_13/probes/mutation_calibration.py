"""Phase 13 mutation probe: each mutation of memelab/predictive/calibration.py or abstention.py must make
tests/test_predictive_calibration.py or tests/test_predictive_abstention.py fail.

Works on a temporary copy of the tracked memelab and tests files plus the files the tests read (the checkout is never edited),
so it runs at HEAD. Writes a JSON report.

    python -B mutation_calibration.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
CP = "memelab/predictive/calibration.py"
AP = "memelab/predictive/abstention.py"
TESTS = ["tests/test_predictive_calibration.py", "tests/test_predictive_abstention.py"]
EXTRA = [CP, AP, *TESTS, "audits/predictive-intelligence/phase_13/ACCEPTANCE_CHECKLIST.md",
         "audits/predictive-intelligence/phase_13/models/FORECAST_RESULT_SCHEMA.json", "docs/predictive-intelligence/DECISIONS.md",
         "audits/predictive-intelligence/phase_06/PHASE_06_RESULTS.json"]

MUTATIONS = [
    # calibration set (rule 1)
    (CP, "C1 split not checked", '        if r["split"] not in SPLITS_ALLOWED:', "        if False:"),
    (CP, "C2 relabelled holdout accepted", '        if not (float(r["decision_time"]) < HOLDOUT_START and float(r["label_matures_at"]) <= HOLDOUT_START):', "        if False:"),
    (CP, "C3 row at the cutoff accepted", '        if not float(r["decision_time"]) < cutoff:', '        if not float(r["decision_time"]) <= cutoff:'),
    (CP, "C4 immature label accepted", '        if not float(r["label_matures_at"]) <= cutoff:\n            raise CalibrationError(f"calibration row', '        if False:\n            raise CalibrationError(f"calibration row'),
    (CP, "C5 in-sample score accepted", '        if not float(r["scored_by_cutoff"]) <= float(r["decision_time"]):\n            raise CalibrationError(f"calibration row', '        if False:\n            raise CalibrationError(f"calibration row'),
    (CP, "C6 duplicate accepted", '        if k in seen:\n            raise CalibrationError(f"calibration row', '        if False:\n            raise CalibrationError(f"calibration row'),
    (CP, "C7 non-finite score accepted", '        if not _fin01(r["score"]):\n            raise CalibrationError(f"calibration row', '        if False:\n            raise CalibrationError(f"calibration row'),
    (CP, "C8 rows_at filters future rows silently into the check", "    use = [r for r in rows if float(r[\"decision_time\"]) < cutoff and float(r[\"label_matures_at\"]) <= cutoff]",
     "    use = list(rows)"),
    # gates and method
    (CP, "G1 event gate off by one", '    if n < FIT_GATE["min_events"]:', '    if n < FIT_GATE["min_events"] - 1:'),
    (CP, "G2 per-class gate checks positives only", '    if k < FIT_GATE["min_per_class"] or n - k < FIT_GATE["min_per_class"]:', '    if k < FIT_GATE["min_per_class"]:'),
    (CP, "G3 day gate dropped", '    if days < FIT_GATE["min_days"]:', "    if False:"),
    (CP, "G4 Venn-Abers from fewer events", '    if n >= VENN_ABERS_GATE["min_events"] and min(k, n - k) >= VENN_ABERS_GATE["min_per_class"]:',
     '    if n >= 150 and min(k, n - k) >= VENN_ABERS_GATE["min_per_class"]:'),
    (CP, "G5 evidence gate per class dropped", '    if k < EVIDENCE_GATE["min_per_class"] or n - k < EVIDENCE_GATE["min_per_class"]:', "    if False:"),
    (CP, "G6 fit gate constant loosened", '"min_events": _A["min_train_events"]', '"min_events": 50'),
    # evidence and status
    (CP, "E1 holdout evidence admitted", '        if r["split"] not in EVIDENCE_SPLITS:', "        if False:"),
    (CP, "E2 pre-cutoff evidence admitted", '        if float(r["decision_time"]) < max(fit_cutoff, PROSPECTIVE_START):', "        if False:"),
    (CP, "E3 evidence overlapping fit admitted", "    if any(r[\"decision_key\"] in fit_keys for r in rows):", "    if False:"),
    (CP, "E4 evidence maturity ignored", '        if not float(r["label_matures_at"]) <= as_of:', "        if False:"),
    (CP, "E5 calibrated without a passed check", '    status = CALIBRATED if (cal is not None and champion is not None and ev["status"] == "ADMISSIBLE" and ev["passed"]',
     '    status = CALIBRATED if (cal is not None and champion is not None and ev["status"] == "ADMISSIBLE"'),
    (CP, "E6 flat predictions calibrated", '    elif deg and deg["flat"]:', "    elif False:"),
    (CP, "E7 simulation source accepted", '    if source not in SOURCES:\n        raise CalibrationError(f"calibration source', '    if False:\n        raise CalibrationError(f"calibration source'),
    (CP, "E8 card sha not verified", '    if card.get("card_sha") != want:', "    if False:"),
    (CP, "E9 publishable ignores level", '            "publishable": status == CALIBRATED and level in PUBLISHABLE_LEVELS,', '            "publishable": status == CALIBRATED,'),
    (CP, "E10 calibrated card without calibrator accepted", '    if card.get("status") == CALIBRATED and (card.get("calibrator") is None or not card["evidence"].get("passed")):', "    if False:"),
    # numbers
    (CP, "N1 interval ignores support", "    return [float(min(low, wl)), float(max(high, wh))]", "    return [float(low), float(high)]"),
    (CP, "N2 flat threshold loosened", "FLAT_PTP = 1e-9", "FLAT_PTP = -1.0"),
    (CP, "N3 conflict flag never set", "    if (b - br) * (ll - llr) < 0:", "    if False:"),
    (CP, "N4 AUC below 10 per class", "    if min(k, n - k) >= AUC_MIN_PER_CLASS:", "    if True:"),
    (CP, "N5 narrower bootstrap governs", '    out["bss_governing"] = max(w, key=lambda nm: (w[nm], nm))', '    out["bss_governing"] = min(w, key=lambda nm: (w[nm], nm))'),
    (CP, "N6 calibrator output not range checked", "        if not np.all(np.isfinite(a)) or np.any(a < 0) or np.any(a > 1):", "        if False:"),
    (CP, "N7 calibrator input NaN accepted", '    if s.size == 0 or not np.all(np.isfinite(s)):\n        raise CalibrationError("calibrator input', '    if False:\n        raise CalibrationError("calibrator input'),
    (CP, "N8 support extrapolates", "    if score < lo or score > hi:\n        return None", "    if False:\n        return None"),
    (CP, "N9 heterogeneity p without +1", "    p = (1 + hits) / (perms + 1)", "    p = hits / perms"),
    (CP, "N10 drift two sided", 'DRIFT = {"delta": 0.005, "threshold": 2.0, "min_obs": 30, "two_sided": False}', 'DRIFT = {"delta": 0.005, "threshold": 20.0, "min_obs": 30, "two_sided": False}'),
    (CP, "N11 base rate governing narrower", '    out["governing"] = "day_block" if wd >= wm else "mint_block"', '    out["governing"] = "day_block" if wd < wm else "mint_block"'),
    # abstention conditions
    (AP, "A1 flag ignored", '    if req.get("flag_on") is not True:', "    if False:"),
    (AP, "A2 chain ignored", "    if req.get(\"chain\") != reg.get(\"scope_chain\", \"solana\"):", "    if False:"),
    (AP, "A3 mint not verified", '    if not mint_verified(req.get("chain"), req.get("mint")):', "    if False:"),
    (AP, "A4 pool not checked", '    if req.get("pool_point_in_time") is not True:', "    if False:"),
    (AP, "A5 gap treated as eligible", '    elif el != "ELIGIBLE":', "    elif False:"),
    (AP, "A6 size ignored", '    if req.get("position_usd") is not None:', "    if False:"),
    (AP, "A7 backtest requirement ignored", '    if req.get("backtest_required") and bt != "VERIFIED":', "    if False:"),
    (AP, "A8 missing input ignored", '        if miss or raw_why == "OOD":', "        if False:"),
    (AP, "A9 out of range ignored", "        if c in req_cols and math.isfinite(vals[int(j)]) and abs(float(z[i])) > CAL.OOD_Z:", "        if False:"),
    (AP, "A10 extrapolated score accepted", '        if support is None:\n            conds.append(_cond("SCORE_OUTSIDE_CALIBRATION_RANGE"', '        if False:\n            conds.append(_cond("SCORE_OUTSIDE_CALIBRATION_RANGE"'),
    (AP, "A11 level ignored", "    if level not in CAL.PUBLISHABLE_LEVELS:", "    if False:"),
    (AP, "A12 future-trained card accepted", "        if cut > T:", "        if False:"),
    (AP, "A13 stale card accepted", '        elif T - cut > C.ACCEPTANCE["max_model_age_s"]:', "        elif False:"),
    (AP, "A14 feature set not compared", '        if req.get("feature_set_sha") != card.get("feature_set_sha"):', "        if False:"),
    (AP, "A15 invalid raw accepted", "    if raw is not None and not (_fin(raw) and 0.0 <= float(raw) <= 1.0):", "    if False:"),
    (AP, "A16 calibration card of another model accepted", '              and cal_card.get("champion_model_sha") == card.get("model_sha") and cal_card.get("target") == tgt)',
     "              )"),
    (AP, "A17 display range ignored", "        if point is not None and not (CAL.DISPLAY_RANGE[0] <= point <= CAL.DISPLAY_RANGE[1]):", "        if False:"),
    (AP, "A18 low support ignored", '    if support is None or int(support["n"]) < CAL.SUPPORT_MIN:', "    if False:"),
    (AP, "A19 drift ignored", "    if drift_at(drift_alarms, T):", "    if False:"),
    (AP, "A20 pending evidence not named", '    if ev.get("status") == "NOT_YET_MATURED":', '    if ev.get("status") == "PENDING":'),
    (AP, "A21 token history ignored", "    if card is not None and card.get(\"needs_token_history\") is True and int(req.get(\"token_history_rows\") or 0) < TOKEN_HISTORY_MIN_ROWS:", "    if False:"),
    (AP, "A22 disallowed path not refused", "            L.refuse_sealed(p)\n", ""),
    (AP, "A23 late availability accepted", '    late = sorted(c for c, v in xs.items() if _fin(v) and (not _fin(av.get(c)) or float(av[c]) > T))', "    late = []"),
    (AP, "A24 behavioral input accepted", '    if req.get("behavioral_inputs"):', "    if False:"),
    # publication validator
    (AP, "V1 scenario numbers accepted", '        if not isinstance(s, dict) or any(PROB_LIKE.search(str(k)) for k in s) or not all(_plain(v) for v in s.values()):', "        if False:"),
    (AP, "V2 cohort fractions accepted", '        if not isinstance(coh, dict) or any(PROB_LIKE.search(str(k)) for k in coh) or any(isinstance(v, float) for v in coh.values()):', "        if False:"),
    (AP, "V3 simulation source accepted", '    if st == "FORECAST" and any(m in mid for m in SIMULATION_MARKERS):', "    if False:"),
    (AP, "V4 reference allowlist off", "            if extra:\n                errs.append(f\"calibration_reference has keys", "            if False:\n                errs.append(f\"calibration_reference has keys"),
    (AP, "V5 reference numbers not compared", "        if ref.get(k) != want.get(k):", "        if False:"),
    (AP, "V6 support interval not required", "        if not (isinstance(iv, list) and len(iv) == 2 and all(_fin(v) for v in iv) and iv[0] <= wl + 1e-12 and iv[1] >= wh - 1e-12):", "        if False:"),
    (AP, "V7 shadow caveat not required", '    if cal["level"] == "SHADOW" and SHADOW_CAVEAT not in cav:', "    if False:"),
    (AP, "V8 new mint caveat not required", '    if (doc.get("cohort") or {}).get("new_mint") and NEW_MINT_CAVEAT not in cav:', "    if False:"),
    (AP, "V9 level not checked", '    if cal["level"] not in CAL.PUBLISHABLE_LEVELS:', "    if False:"),
    (AP, "V10 record reasons not compared", '        if sorted(set(record.get("reasons") or [])) != sorted(set(doc.get("abstain_reasons") or [])) or \\',
     '        if False and \\'),
    (AP, "V11 record id not checked", '        if record.get("record_id") != sha({k: v for k, v in record.items() if k != "record_id"}):\n            errs.append("abstention record content', '        if False:\n            errs.append("abstention record content'),
    (AP, "V12 interval caveat not required", "    if INTERVAL_CAVEAT not in cav:", "    if False:"),
    (AP, "V13 calibration card not verified", "        CAL.verify_card(cal)\n    except Exception as e:", "        pass\n    except Exception as e:"),
    (AP, "S1 tampered calibration card used", "            CAL.verify_card(cal_card)\n        except Exception as e:", "            pass\n        except Exception as e:"),
    (AP, "S2 level mismatch ignored", '    elif cal_card is not None and cal_card.get("level") != level:', "    elif False:"),
    (AP, "S3 forged support accepted", '    elif not any(int(b["n"]) == sn and int(b["k"]) == sk for b in cal.get("support_bins") or []):', "    elif False:"),
    (AP, "S4 base rate not compared", '        if not (_fin(doc.get("base_rate")) and abs(float(doc["base_rate"]) - want_base) <= 1e-12):', "        if False:"),
    (AP, "P1 append-only check off", "    if now != expect_sha:", "    if False:"),
    (AP, "P2 trading words allowed", '    if any(re.search(r"\\b" + re.escape(w) + r"\\b", low) for w in TRADING_WORDS):', "    if False:"),
    (AP, "P3 forecast with conditions", "    if conds:\n        doc = {", "    if False:\n        doc = {"),
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
        orig = {p: (root / p).read_text() for p in (CP, AP)}
        cmd = [sys.executable, "-B", "-m", "pytest", *TESTS, "-q", "-x", "-p", "no:cacheprovider"]
        base = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("tests fail on the unmutated copy:\n" + base.stdout[-3000:])
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
