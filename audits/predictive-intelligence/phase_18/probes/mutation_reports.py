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
    ("S2 veto override line removed", '        if ex["veto"]:\n            L.append("  - Overridden:', '        if False:\n            L.append("  - Overridden:'),
    ("S3 not-attempted events dropped", '            if r.get("event") in I.ATTEMPTED or (mint is not None and r.get("mint") != mint):', '            if True:'),
    ("S4 unblock lines dropped", "        L += [f\"  - {r}: {UNBLOCK.get(r, 'a recorded decision')}.\" for r in reasons]", '        pass'),
    ("S5 index pin mismatch unchecked", '            if tf.get("event_id") != t["registry"].get("pin_event_id"):', '            if False:'),
    ("S6 index of another log used", '    if idx.get("log_sha256") != reg.get("log_sha256"):', '    if False:'),
    # rule 7: sanitization
    ("Z1 trading-word check off", '    if not _plain(t):\n        raise ReportError("the text would carry a trading word")', '    if False:\n        raise ReportError("the text would carry a trading word")'),
    ("Z2 local-path check off", '    if LOCAL_PATH.search(t):\n        raise ReportError', '    if False:\n        raise ReportError'),
    ("Z3 lab status with trade wording shown", '        if _plain(status):\n            return status, "FACT"', '        if True:\n            return status, "FACT"'),
    ("Z4 symbol unsanitized", '"symbol": I._ident(tok.get("symbol")) if', '"symbol": tok.get("symbol") if'),
    ("Z5 token report path printed", '"token_report": I._ident(Path(str((req.get("report_refs") or {}).get("token_report") or "")).name, 80)',
     '"token_report": str((req.get("report_refs") or {}).get("token_report"))'),
    ("Z6 inexact mint text printed", '"mint": I._mint_text(r.get("chain"), r.get("mint")),', '"mint": str(r.get("mint")),'),
    # rule 8: watermark
    ("W1 watermark flag never set", '    view["format_only"] = any(t.get("is_fixture") for t in docs)', '    view["format_only"] = False'),
    ("W2 render guard removed", '    if fixture and not view.get("format_only"):', '    if False:'),
    ("W3 forecast row unwatermarked", '        s += " FORMAT-ONLY FIXTURE"', '        pass'),
    ("W4 fixture in a live alert run allowed", '        if fixture and not fixture_run:', '        if False:'),
    # rules 9 to 11: alerts
    ("A1 send allowed", '    if send:\n        raise AlertRefused(', '    if False:\n        raise AlertRefused('),
    ("A2 dedupe removed", "        if con.execute(\"SELECT 1 FROM alert_events WHERE mode='dry_run' AND dedupe_key=?\", (c[\"dedupe_key\"],)).fetchone():", '        if False:'),
    ("A3 cooldown removed", '        if AE._in_cooldown(con, "dry_run", c["cooldown_key"], now, float(cfg["cooldown_hours"])):', '        if False:'),
    ("A4 daily cap removed", '        if used >= int(policy["daily_cap"]):', '        if False:'),
    ("A5 notices first under the cap", '    cands.sort(key=lambda c: (-AC.SEVERITIES.index(c["severity"]),', '    cands.sort(key=lambda c: (AC.SEVERITIES.index(c["severity"]),'),
    ("A6 veto does not override a forecast (CX-18)", '            if ex["veto"] or ex["backtest_veto"] is True:\n                sup(o, "reevaluate", "VETO_OVERRIDES_FORECAST"',
     '            if False:\n                sup(o, "reevaluate", "VETO_OVERRIDES_FORECAST"'),
    ("A7 stale inputs alert", '        stale = o["snapshot"]["input_state"] == I.INPUT_STALE or cap is None or', '        stale = False and'),
    ("A8 liquidity bound strict", 'risky = ex["structural_veto"] or ex["veto_unknown"] or ex["backtest_veto"] is True or (fall is not None and fall <= -lim + 1e-12)',
     'risky = ex["structural_veto"] or ex["veto_unknown"] or ex["backtest_veto"] is True or (fall is not None and fall < -lim)'),
    ("A9 withdrawn never detected", '            if prev and cur is not None and cur["status"] != "FORECAST":', '            if False:'),
    ("A10 every pass evaluated again", '            first = (prev["snapshot_run_id"] + 1) if prev is not None and prev["snapshot_run_id"] is not None else 0', '            first = 0'),
    ("A11 too_soon removed", '        elif prev is not None and now - prev["started_at"] < float(pol["min_interval_minutes"]) * 60:', '        elif False:'),
    ("A12 no_new_upstream_data removed", '        elif prev is not None and prev["snapshot_run_id"] == seq and bool(prev["fixture"]) == bool(fixture_run):', '        elif False:'),
    ("A13 outbox inside the repository allowed", '    _refuse_path(box, "alert outbox")', '    pass'),
    ("A14 tampered state gives no alert", '            if view.get("state") == "STATE_TAMPERED":\n                ev = _evaluate(', '            if False:\n                ev = _evaluate('),
    ("A15 disclaimer removed", '    L.append(AC.DISCLAIMER)', '    pass'),
    ("A16 alert text unchecked", '    check_text(text, [a.get("mint") or ""])', '    pass'),
    ("A17 flag off still writes the alert state", '    if not I.config(config_path)["enabled"]:\n        return None\n    pol = policy', '    pol = policy'),
    ("A18 risk alert ignores the backtest veto", 'or ex["backtest_veto"] is True or (fall is not None and fall <= -lim + 1e-12)', 'or (fall is not None and fall <= -lim + 1e-12)'),
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
