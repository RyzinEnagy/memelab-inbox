"""Phase 18 mutation probe: each mutation of memelab/predictive/reports.py must make tests/test_predictive_reports.py fail.
Works on a temporary copy of the tracked memelab and tests trees plus the committed artifacts the tests read (the checkout is
never edited), so it runs at HEAD. Each original fragment must occur exactly once. Writes a JSON report.

    python -B mutation_reports.py OUT.json [--only NAME_PREFIX ...]

Mutations left out as equivalent (a later check catches the same input, recorded here so a reader can test them): the range
check of a FORECAST probability and the number check of an abstention (both repeated by `integration.check_document`), the
record-conditions check of a FORECAST (repeated by `abstention.validate_publication`), the status-versus-request check (a
FORECAST without the request's raw number is refused anyway), the exact-mint text of an attempted request (attempted requests
always carry an exact address). Three checks are layered on purpose and each alone is masked by another (first probe run,
2026-10-27): the ownership check (R2) by the state-check refusal and the request refusal, the state-check refusal (R3) by the
pairing, ownership and abstention checks, the abstention `check_document` (R9) by the state check (which runs the same
validator); they are probed as the combinations that remove every layer (R2+R3+Q, R3+R9).
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
RPT = "memelab/predictive/reports.py"
TEST = "tests/test_predictive_reports.py"
A = "audits/predictive-intelligence"
EXTRA_DIRS = [f"{A}/phase_16/registry", f"{A}/phase_13/artifacts", f"{A}/phase_07/artifacts"]

MUTATIONS = [
    # rule 1: reading and refusing
    ("R1 pair errors ignored", '        fail += I.pair_errors(doc, rec)\n', '        pass\n'),
    ("R2+R3+Q ownership, state-check and request refusals all removed",
     [('        if (dline.get("pass_id"), dline.get("request_seq")) != (req.get("pass_id"), req.get("seq")):', '        if False:'),
      ('    if trec.get("forecast_id") in refused_ids:', '    if False:'),
      ('    if req_refused:\n        fail.append("its request failed the state check")', '    if False:\n        fail.append("its request failed the state check")')]),
    ("R3+R9 state-check refusal and the abstention check both removed",
     [('    if trec.get("forecast_id") in refused_ids:', '    if False:'),
      ('        fail += I.check_document(doc, rec, config_path=config_path)\n        if fail:', '        if fail:')]),
    ("R10 a state problem naming no document ignored", '            seqs.add(-1)', '            pass'),
    ("R4 stored point not compared (CX-18)", '    if not _same(trec.get("calibrated_point"), p):', '    if False:'),
    ("R5 stored interval not compared", '    if not (isinstance(iv, list) and isinstance(siv, list) and len(iv) == len(siv) == 2 and all(_same(a, b) for a, b in zip(iv, siv))):', '    if False:'),
    ("R6 cards not resolved or checked", '    if not fail:\n        card, cal, why = _resolve_cards(', '    if False:\n        card, cal, why = _resolve_cards('),
    ("R7 a tampered state shown", '        view.update(state="STATE_TAMPERED", detail=I._ident(type(e).__name__, 40))', '        view.update(state="OK", detail=I._ident(type(e).__name__, 40))'),
    ("R8 state-check failure hidden", '        view["state"] = "STATE_CHECK_FAILED" if chk.get("problems") else "OK"', '        view["state"] = "OK"'),
    # rule 2: lab snapshot
    ("L1 any row of the mint used", '        match = [r for r in rows if snapshot_hash and I.snapshot_sha(r) == snapshot_hash]', '        match = rows'),
    # rule 4: no unsupported number
    ("N1 a number for an abstention", '        tv["number"] = None\n        return tv\n    # FORECAST',
     '        tv["number"] = {"probability": 0.5, "interval": [0.4, 0.6], "base_rate": 0.3, "level": None, "method": None, "support_n": 0, '
     '"support_k": 0, "holdout_n": 0, "calibration_card_sha": None, "cohort": None}\n        return tv\n    # FORECAST'),
    ("N2 abstention row without its label", '    if t["status"] == "ABSTAIN":\n        return "ABSTAIN (no number)"', '    if False:\n        return "ABSTAIN (no number)"'),
    # rule 6: sections
    ("S1 simulation state removed from the opportunity", '    d = {"facts": [f"behavioral simulation {SIMULATION_STATE}: {SIMULATION_WHY}"], "inferences": [],', '    d = {"facts": [], "inferences": [],'),
    ("S3 not-attempted events dropped", '            if r.get("event") in I.ATTEMPTED or (mint is not None and r.get("mint") != mint):', '            if True:'),
    ("S4 unblock lines dropped", "        L += [f\"  - {r}: {UNBLOCK.get(r, 'a recorded decision')}.\" for r in reasons]", '        pass'),
    ("S5 index pin mismatch unchecked", '            if tf.get("event_id") != t["registry"].get("pin_event_id"):', '            if False:'),
    ("S6 index of another log used", '    if idx.get("log_sha256") != reg.get("log_sha256"):', '    if False:'),
    # rule 7: sanitization
    ("Z1 trading-word check off", '    if not _plain(t):\n        raise ReportError("the text would carry a trading word")', '    if False:\n        raise ReportError("the text would carry a trading word")'),
    ("Z2 local-path check off", '    if LOCAL_PATH.search(t):\n        raise ReportError', '    if False:\n        raise ReportError'),
    ("Z3 lab status with trade wording shown", '        if _plain(status):\n            return status, "FACT"', '        if True:\n            return status, "FACT"'),
    ("Z6 inexact mint text printed", '"mint": I._mint_text(r.get("chain"), r.get("mint")),', '"mint": str(r.get("mint")),'),
    # CP18-0 (PI-D-099)
    ("C1 fatal-flag codes withheld again", '                       "fatal_flags": [_code(f) for f in sv.get("flags") or []],',
     '                       "fatal_flags": [I._ident(f, 40) for f in sv.get("flags") or []],'),
    ("C2 own detail text stripped", "SNAPSHOT_NOT_VERIFIED ({sn.get('lab_detail') or 'no detail'})", "SNAPSHOT_NOT_VERIFIED ({I._ident(sn.get('lab_detail') or 'no detail', 60)})"),
    # CP18-1 (PI-D-100)
    ("C3 measured changes unlabelled", '''                   + (f" ({MEASURED_LABEL}: {'; '.join(o['changes'])})" if measured else''',
     '''                   + (f" ({'; '.join(o['changes'])})" if measured else'''),
    # rule 8: watermark
    ("W1 watermark flag never set", '    view["format_only"] = any(t.get("is_fixture") for t in docs)', '    view["format_only"] = False'),
    ("W2 render guard removed", '    if fixture and not view.get("format_only"):', '    if False:'),
    ("W4 fixture in a live alert run allowed", '        if fixture and not fixture_run:', '        if False:'),
    # rules 9 to 11: alerts
    ("A1 send allowed", '    if send:\n        raise AlertRefused(', '    if False:\n        raise AlertRefused('),
    ("A2 dedupe removed", "        if con.execute(\"SELECT 1 FROM alert_events WHERE mode='dry_run' AND dedupe_key=?\", (c[\"dedupe_key\"],)).fetchone():", '        if False:'),
    ("A3 cooldown removed", '        if AE._in_cooldown(con, "dry_run", c["cooldown_key"], now, float(cfg["cooldown_hours"])):', '        if False:'),
    ("A5 notices first under the cap", '    cands.sort(key=lambda c: (-AC.SEVERITIES.index(c["severity"]),', '    cands.sort(key=lambda c: (AC.SEVERITIES.index(c["severity"]),'),
    ("A7 stale inputs alert", '        stale = o["snapshot"]["input_state"] == I.INPUT_STALE or cap is None or', '        stale = False and'),
    ("A13 outbox inside the repository allowed", '    _refuse_path(box, "alert outbox")', '    pass'),
    ("A14 tampered state gives no alert", '            if view.get("state") == "STATE_TAMPERED":\n                ev = _evaluate(', '            if False:\n                ev = _evaluate('),
    ("A15 disclaimer removed", '    L.append(AC.DISCLAIMER)', '    pass'),
    ("A16 alert text unchecked", '    check_text(text, [a.get("mint") or ""])', '    pass'),
    ("A17 flag off still writes the alert state", '    if not I.config(config_path)["enabled"]:\n        return None\n    pol = policy', '    pol = policy'),
    # CP18-2 (PI-D-102), repair pass 2, and the skeptic's extra mutations (adapted to the repaired code where the fragment moved)
    ("S2 risk-overridden number shown", '        if x["overridden"]:                               # CP18-2 item 1', '        if False:'),
    ("Z4 symbol unsanitized", '"symbol": _token_text(tok.get("symbol")) if', '"symbol": tok.get("symbol") if'),
    ("Z5 token report path printed", '"token_report": _token_text(Path(str((req.get("report_refs") or {}).get("token_report") or "")).name, 80)',
     '"token_report": str((req.get("report_refs") or {}).get("token_report"))'),
    ("W3 forecast row unwatermarked", '    fx = " FORMAT-ONLY FIXTURE" if t.get("is_fixture") else ""', '    fx = ""'),
    ("A4 daily caps removed", '        if (used_w if warn else used_n) >= cap_n:', '        if False:'),
    ("A6 risk does not suppress reevaluate (CX-18, M1)", '        for t in withheld:\n            sup(o, "reevaluate", "RISK_OVERRIDES_FORECAST"',
     '        for t in []:\n            sup(o, "reevaluate", "RISK_OVERRIDES_FORECAST"'),
    ("A8 liquidity bound strict", '    if fall is not None and fall <= -lim + 1e-12:', '    if fall is not None and fall < -lim:'),
    ("A9 withdrawn never detected", '            if prev and cur is not None and cur["status"] != "FORECAST" and not cur.get("overridden"):', '            if False:'),
    ("A10 every pass evaluated again", '                first = 0 if (changed or prev is None or prev["snapshot_run_id"] is None) else prev["snapshot_run_id"] + 1',
     '                first = 0'),
    ("A11 too_soon removed", '        elif prev is not None and 0 <= now - prev["started_at"] < float(pol["min_interval_minutes"]) * 60:', '        elif False:'),
    ("A12 no_new_upstream_data removed", '            if (not changed and prev is not None and prev["snapshot_run_id"] == seq', '            if (False and prev is not None and prev["snapshot_run_id"] == seq'),
    ("A18 the backtest veto is no risk", '    if ex["backtest_veto"] is True:\n        out.append({"code": "BACKTEST_VETO"', '    if False:\n        out.append({"code": "BACKTEST_VETO"'),
    ("M1 liquidity fall no risk", '    if fall is not None and fall <= -lim + 1e-12:\n        out.append({"code": LIQUIDITY_FALL', '    if False:\n        out.append({"code": LIQUIDITY_FALL'),
    ("M2 feed check removed", '            changed = _feed_check(state_dir, config_path, prev)', '            changed = None'),
    ("M3a newer snapshot not attached", 'view["opportunities"].append(_opportunity(rv, newer=_newer(st, key, lst[-1], lab)))', 'view["opportunities"].append(_opportunity(rv, newer=[]))'),
    ("M3b newer snapshot never alerted", '    for n in newer:                                        # CP18-2 item 3', '    for n in []:'),
    ("M3c any event counted as covered", '            cov = r.get("event") in ("UNCHANGED", "DUPLICATE") and', '            cov = True or r.get("event") in ("UNCHANGED", "DUPLICATE") and'),
    ("M4 run-together trade words allowed (CX-SK18)", '    if any(w in letters for w in TOKEN_WORDS) or _MULTIPLIER.search(raw.lower()):', '    if False:'),
    ("m7 only opportunity mints removed before the check", '    check_text(text, _mints(view))', '    check_text(text, [o["mint"] for o in view["opportunities"]])'),
    ("m8 clock behind is too_soon", 'elif prev is not None and 0 <= now - prev["started_at"] <', 'elif prev is not None and now - prev["started_at"] <'),
    ("m9 unknown liquidity no risk", '    if any(str(c) == "liquidity became unknown" for c in o.get("changes") or []):', '    if False:'),
    ("m10 alert database not restricted", '    _refuse_alert_db(dbp, lab_db)', '    pass'),
    ("m11a one cap for every severity", '        cap_n = int(policy["daily_cap_warning"] if warn else policy["daily_cap"])', '        cap_n = int(policy["daily_cap"])'),
    ("m11b notices use the warnings' room", '        if (used_w if warn else used_n) >= cap_n:', '        if (used_w + used_n) >= cap_n:'),
    ("X1 token row of another chain used", '        if tok is not None and tok.get("chain", chain) != chain:', '        if False:'),
    ("X2 request capture age ignored", ' or cap is None or now - cap > float(policy["source_max_age_hours"]) * 3600', ''),
    ("X3 unknown check not shown in the risk column", '"text": "fatal-flag check unknown", "short": ["unknown"]', '"text": "fatal-flag check unknown", "short": []'),
    ("X4 unknown lab status printed raw", '    return _token_text(status), "UNKNOWN"', '    return str(status), "UNKNOWN"'),
    ("X5 non-matching change strings printed raw", 'I._ident(c, 60) if not re.fullmatch(r"[A-Za-z0-9_ .:%+-]+", str(c)) else str(c)', 'str(c)'),
    ("X6 served MODEL_STALE/DRIFT pipeline alert removed", '                if b_ in ("MODEL_STALE", "DRIFT_ALERT", "REGISTRY_UNAVAILABLE"):', '                if False:'),
    ("X7 ERROR events give no pipeline alert", '    for e in errors:\n        b = {"policy": "pipeline_health"', '    for e in []:\n        b = {"policy": "pipeline_health"'),
    ("X8 reevaluate ignores the base rate", 'not (_fin(n.get("base_rate")) and n["interval"][0] > float(n["base_rate"]) + _TOL)', 'False'),
    ("X9 unknown check not a risk", '    if ex["veto_unknown"]:\n        out.append({"code": "FATAL_CHECK_UNKNOWN"', '    if False:\n        out.append({"code": "FATAL_CHECK_UNKNOWN"'),
    ("X10 backtest-veto reasons dropped from the execution section", """                   + (f"; backtest veto {', '.join(ex['backtest_veto_reasons'])}" if ex["backtest_veto"] else ""),""", """                   + "","""),
    ("X11 SIMULATION_NOT_AVAILABLE dropped from at a glance", """    L.append(f"- Backtesting: {sysv['backtest_status']}. Behavioral simulation: {SIMULATION_STATE}.")""", """    L.append(f"- Backtesting: {sysv['backtest_status']}.")"""),
    ("X12 target definitions horizon dropped", """{d['horizon_seconds'] / 3600:.0f} hours | \"""", """\" \""""),
]


def main(out: str, only: list[str] | None = None) -> int:
    src = (REPO / RPT).read_text()
    muts = [(m[0], m[1]) if isinstance(m[1], list) else (m[0], [(m[1], m[2])]) for m in MUTATIONS]
    muts = [m for m in muts if not only or any(m[0].startswith(o) for o in only)]
    for name, pairs in muts:
        for a, b in pairs:
            if src.count(a) != 1:
                raise SystemExit(f"{name}: fragment occurs {src.count(a)} times")
    results = []
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="p18_mut_") as td:
        root = Path(td)
        for d in ("memelab", "tests"):
            shutil.copytree(REPO / d, root / d, ignore=shutil.ignore_patterns("__pycache__"))
        for d in EXTRA_DIRS:
            shutil.copytree(REPO / d, root / d)
        cmd = [sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"]
        base = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("baseline fails: " + base.stdout[-3000:])
        for name, pairs in muts:
            mutated = src
            for a, b in pairs:
                mutated = mutated.replace(a, b)
            (root / RPT).write_text(mutated)
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=900)
            failed = [ln.split(" ")[1] for ln in r.stdout.splitlines() if ln.startswith("FAILED") or ln.startswith("ERROR")]
            results.append({"mutation": name, "caught": r.returncode != 0,
                            "first_failure": failed[0] if failed else (r.stdout.strip().splitlines() or [""])[-1]})
            (root / RPT).write_text(src)
    rep = {"module": RPT, "tests": TEST, "mutations": len(results), "caught": sum(r["caught"] for r in results),
           "survivors": [r["mutation"] for r in results if not r["caught"]], "results": results, "wall_s": round(time.time() - t0, 1)}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("mutations", "caught", "survivors", "wall_s")}))
    return 0 if not rep["survivors"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[3:] if len(sys.argv) > 2 and sys.argv[2] == "--only" else None))
