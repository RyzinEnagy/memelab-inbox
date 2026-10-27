"""Phase 17 mutation probe: each mutation of memelab/predictive/integration.py, memelab/predictive/bt_adapter.py or the hook in
memelab/cli.py must make tests/test_predictive_integration.py fail. Works on a temporary copy of the tracked memelab and tests
trees plus the committed artifacts the tests read (the checkout is never edited), so it runs at HEAD. Each original fragment
must occur exactly once. Writes a JSON report.

    python -B mutation_integration.py OUT.json [--only NAME_PREFIX ...]
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
INT = "memelab/predictive/integration.py"
BTA = "memelab/predictive/bt_adapter.py"
CLI = "memelab/cli.py"
TEST = "tests/test_predictive_integration.py"
A = "audits/predictive-intelligence"
EXTRA_DIRS = [f"{A}/phase_16/registry", f"{A}/phase_13/artifacts", f"{A}/phase_07/artifacts"]

MUTATIONS = [
    # rule 1: the flag and the hook
    ("F1 flag ignored by the pass", INT, '    if not cfg["enabled"]:\n        return None\n    t_start = clock()', '    if False:\n        return None\n    t_start = clock()'),
    ("H1 section replaces the body", CLI, '        md += "\\n" + pred', '        md = pred'),
    ("H2 analyze line not printed", CLI, '    if pline:\n        print(pline)', '    if False:\n        print(pline)'),
    # rule 2: the decision snapshot
    ("S1 snapshot hash of the row with its id", INT, '    tr["snapshot_hash"] = D.row_sha256(tr["row"]) if tr["row"] else None', '    tr["snapshot_hash"] = sha(tr["row"]) if tr["row"] else None'),
    ("S2 oldest row of a shared key", INT, 'created_at=? ORDER BY id DESC"', 'created_at=? ORDER BY id ASC"'),
    ("S3 capture before the row accepted", INT, '    if T < float(row["created_at"]):', '    if False:'),
    ("S4 row and result not compared", INT, '    if row.get("mint") != tr["mint"] or row.get("status") != tr["status"] or row.get("score") != tr["score"]:', '    if False:'),
    ("S5 identity check bypassed", INT, '        except Exception:  # noqa: BLE001\n            tr["identity_ok"] = False', '        except Exception:  # noqa: BLE001\n            tr["identity_ok"] = True'),
    ("S6 default chain", INT, '"chain": b.get("chain"), "mint"', '"chain": b.get("chain") or "solana", "mint"'),
    # rule 3: exactly once
    ("X1 duplicate check removed", INT, '    if all(have):', '    if False:'),
    ("X2 non-primary targets not listed", INT, 'for t in PRIMARY}) if not p["attempted"]]', 'for t in PRIMARY}) if p["attempted"]]'),
    # rule 4: the material gate
    ("G1 score threshold 6", INT, '"material": {"score_abs": 5,', '"material": {"score_abs": 6,'),
    ("G2 relative bound strict", INT, 'if abs(d) + 1e-12 >= lim else None', 'if abs(d) > lim else None'),
    ("G3 served pin not in the key (CX-17)", INT, '    for k in ("pool", "status", "fatal", "catalyst", "served"):', '    for k in ("pool", "status", "fatal", "catalyst"):'),
    ("G4 catalyst not in the key", INT, '    for k in ("pool", "status", "fatal", "catalyst", "served"):', '    for k in ("pool", "status", "fatal", "served"):'),
    ("G5 age trigger removed", INT, '    if capture - prev_capture >= m["max_age_s"]:', '    if False:'),
    ("G6 previous attempt not as of the capture", INT, 'if float(a["capture_time"]) <= float(base["capture_time"])]', 'if True]'),
    ("G7 became known or unknown ignored", INT, '    if (a is None) != (b is None):\n        return f"{name}', '    if False:\n        return f"{name}'),
    ("G8 price bound 0.2", INT, '"price_rel": 0.10,', '"price_rel": 0.20,'),
    # rule 5: bounded work
    ("Q1 queue cap removed", INT, '    if attempted >= FROZEN["queue_max"]:', '    if False:'),
    ("Q2 per-mint supersede removed", INT, '    if newest.get(key) != tr["position"]:', '    if False:'),
    ("Q3 oldest snapshot kept", INT, '>= (float(trigs[j]["row"]["created_at"]), trigs[j]["position"])', '<= (float(trigs[j]["row"]["created_at"]), trigs[j]["position"])'),
    ("Q4 pass budget removed", INT, '    if clock() - t_start > FROZEN["pass_budget_s"]:', '    if False:'),
    # rule 6: network and cost
    ("N1 cost cap lifted", INT, 'max_cost=FROZEN["cost_cap_usd"],', 'max_cost=1e9,'),
    ("N2 reader without a champion", INT, '    if not stale and any(served[t]["use_champion"] for t in PRIMARY):\n        elig, elig_detail = _eligibility(', '    if not stale:\n        elig, elig_detail = _eligibility('),
    ("N3 breaker lifted", INT, 'breaker=FROZEN["breaker_failures"],', 'breaker=1000,'),
    ("N4 reader timeout ignored", INT, '    if took > FROZEN["reader_timeout_s"]:', '    if False:'),
    # rule 7: serving
    ("R1 registry outage not visible", INT, '    if reg["state"] != "OK":\n        out["blocking"].append', '    if reg["state"] == "NEVER":\n        out["blocking"].append'),
    ("R2 fixture champion outside a fixture run", INT, 'drift_alarms=drift_alarms, inference=inference, root=root, allow_fixture=allow_fixture)', 'drift_alarms=drift_alarms, inference=inference, root=root, allow_fixture=True)'),
    ("R3 drift alarms dropped", INT, '        served[t] = _serve(t, T, reg=reg, rt=rt, root=root, allow_fixture=allow_fixture, drift_alarms=drift_alarms)', '        served[t] = _serve(t, T, reg=reg, rt=rt, root=root, allow_fixture=allow_fixture, drift_alarms=())'),
    # rule 8: staleness and features
    ("T1 stale bound inverted", INT, '(T - float(obs) > FROZEN["stale_input_s"])', '(T - float(obs) < FROZEN["stale_input_s"])'),
    ("T2 staleness also for export decisions", INT, '    stale = (base["decision_time_basis"] == "CAPTURE_TIME") and (', '    stale = True and ('),
    # rule 9: catalysts
    ("C1 any link type counts", INT, '    exact = [r for r in vis if r["link_type"] in rule["link_types"] and r["link_strength"] == rule["strength"]]', '    exact = list(vis)'),
    ("C2 later links visible", INT, 'and _fin(r["linked_at"]) and r["linked_at"] <= T\n', 'and _fin(r["linked_at"])\n'),
    ("C3 catalyst pass rate limit removed", INT, '        if lr is not None and now - lr < rule["refresh_min_interval_s"]:', '        if False:'),
    ("C4 catalyst pass dedup removed", INT, '        if (r["mint"], r["event_key"]) in seen_keys:', '        if False:'),
    ("C5 ticker links refresh", INT, '        if r["link_type"] not in rule["link_types"] or r["link_strength"] != rule["strength"]:', '        if False:'),
    # rule 10: decision support
    ("V1 backtest veto dropped", INT, '    veto = ds["veto_overrides_forecast"] or btc["veto"]["veto"] is True', '    veto = ds["veto_overrides_forecast"]'),
    ("V2 max loss changed", INT, '"decision_support": {"max_loss": 0.05,', '"decision_support": {"max_loss": 0.5,'),
    # rules 11 and 12: documents and points
    ("D1 document without record accepted", INT, '    if record is None:\n        return ["a document without its persisted abstention record is never shown (Phase 13 m4)"]', '    if record is None:\n        return []'),
    ("D2 reasons not compared", INT, '    if sorted(record.get("reasons") or []) != sorted(doc.get("abstain_reasons") or []):\n        errs.append("the document\'s reasons differ from its record")', '    if False:\n        errs.append("the document\'s reasons differ from its record")'),
    ("D3 point tolerance wide", INT, 'abs(float(doc["probability"]) - float(ev["point"])) <= 1e-12)', 'abs(float(doc["probability"]) - float(ev["point"])) <= 1.0)'),
    ("D4 interval not compared", INT, '        errs.append(f"interval {iv!r} is not the recomputed {list(ev[\'interval\'])!r}")', '        pass'),
    ("D5 raw number not required", INT, '    if not _fin(raw) or cal_card is None or card is None:', '    if cal_card is None or card is None:'),
    # rule 14: persistence
    ("P1 record id not checked", INT, '        if AB.canon(r) != line or r.get("record_id") != sha({k: v for k, v in r.items() if k != "record_id"}):', '        if AB.canon(r) != line:'),
    ("P2 file sha not checked", INT, '        if got != want:\n            raise StateTampered', '        if False:\n            raise StateTampered'),
    ("P3 pass chain not checked", INT, '        if p.get("seq") != i or p.get("prev") != prev:', '        if False:'),
    # rule 15: the section
    ("W1 trading words allowed", INT, '    if not _plain_ok(ident):', '    if False:'),
    ("W2 veto line hidden", INT, '                L_.append(f"- Fatal-flag veto: {\', \'.join(sv[\'flags\'])}; no forecast clears it")', '                pass'),
    # rule 16: metrics
    ("O1 duplicates miscounted", INT, '"unchanged_cache_hits": ev.count("UNCHANGED"), "duplicates": ev.count("DUPLICATE"),', '"unchanged_cache_hits": ev.count("UNCHANGED"), "duplicates": 0,'),
    # bt-adapter-1
    ("B1 identity unchecked", BTA, '    if rec.get("chain", "solana") != chain or rec.get("mint") != mint:', '    if False:'),
    ("B2 later assessment accepted", BTA, '    elif float(rec["as_of"]) > float(decision_time):', '    elif False:'),
    ("B3 no-trade not a veto", BTA, 'VETO_DECISIONS = ("RISK_FATAL_FLAW", "STRUCTURALLY_UNTRADEABLE", "NO_TRADE")', 'VETO_DECISIONS = ("RISK_FATAL_FLAW", "STRUCTURALLY_UNTRADEABLE")'),
    ("B4 table time filter removed", BTA, "stage='FAST' AND as_of <= ? \"", "stage='FAST' AND ? IS NOT NULL \""),
    ("B5 schema unchecked", BTA, '    if tuple(cols) != EXPECTED_COLUMNS:', '    if False:'),
    ("B6 unknown stress decision accepted", BTA, '    if dec is not None and dec not in STRESS_DECISIONS:', '    if False:'),
]


def main(out: str, only: list[str] | None = None) -> int:
    srcs = {f: (REPO / f).read_text() for f in (INT, BTA, CLI)}
    muts = [m for m in MUTATIONS if not only or any(m[0].startswith(o) for o in only)]
    for name, f, a, b in muts:
        if srcs[f].count(a) != 1:
            raise SystemExit(f"{name}: fragment occurs {srcs[f].count(a)} times in {f}")
    results = []
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="p17_mut_") as td:
        root = Path(td)
        for d in ("memelab", "tests"):
            shutil.copytree(REPO / d, root / d, ignore=shutil.ignore_patterns("__pycache__"))
        for d in EXTRA_DIRS:
            shutil.copytree(REPO / d, root / d)
        cmd = [sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"]
        base = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("baseline fails: " + base.stdout[-3000:])
        for name, f, a, b in muts:
            (root / f).write_text(srcs[f].replace(a, b))
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=900)
            failed = [ln.split(" ")[1] for ln in r.stdout.splitlines() if ln.startswith("FAILED")]
            results.append({"mutation": name, "file": f, "caught": r.returncode != 0,
                            "first_failure": failed[0] if failed else (r.stdout.strip().splitlines() or [""])[-1]})
            (root / f).write_text(srcs[f])
    rep = {"modules": [INT, BTA, CLI], "tests": TEST, "mutations": len(results), "caught": sum(r["caught"] for r in results),
           "survivors": [r["mutation"] for r in results if not r["caught"]], "results": results, "wall_s": round(time.time() - t0, 1)}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("mutations", "caught", "survivors", "wall_s")}))
    return 0 if not rep["survivors"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[3:] if len(sys.argv) > 2 and sys.argv[2] == "--only" else None))
