"""Phase 09 mutation probe: each mutation of memelab/predictive/onchain.py or depth_adapter.py must make
tests/test_predictive_onchain.py fail.

Works on a temporary copy of the repository's tracked files plus the Phase 09 files (the checkout is never edited). Writes a
JSON report.

    python -B mutation_onchain.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
ON = "memelab/predictive/onchain.py"
DA = "memelab/predictive/depth_adapter.py"
TEST = "tests/test_predictive_onchain.py"
EXTRA = [ON, DA, TEST, "tests/fixtures/predictive/bt_depth_schema_v2.sql"]

MUTATIONS = [
    # onchain-1 features
    (ON, "oldest visible decision used instead of the newest", "    elif decs:\n        dec = decs[-1]", "    elif decs:\n        dec = decs[0]"),
    (ON, "P36 snapshot time check removed", 'if aux["t"] is not None and aux["t"] > Td:', "if False:"),
    (ON, "previous decision may share the decision time", 'prior = [d for d in decs if float(d["decision_time"]) < Td]',
     'prior = [d for d in decs if float(d["decision_time"]) <= Td and d["decision_key"] != dec["decision_key"]][:1]'),
    (ON, "previous decision is the first, not the latest", "pd = prior[-1]", "pd = prior[0]"),
    (ON, "LP risk order changed", 'LP_RISK = {"LOW": 0.0, "MODERATE": 1.0, "HIGH": 2.0, "CRITICAL": 3.0}',
     'LP_RISK = {"LOW": 0.0, "MODERATE": 2.0, "HIGH": 1.0, "CRITICAL": 3.0}'),
    (ON, "CANNOT_EXIT_5K not structural", '"LP_RISK_CRITICAL", "NO_SELL_ROUTE", "CANNOT_EXIT_5K"})', '"LP_RISK_CRITICAL", "NO_SELL_ROUTE"})'),
    (ON, "INSIDER_DISTRIBUTION not a distribution flag", '"CLUSTER_OWNERSHIP_GT_25PCT",\n                                "INSIDER_DISTRIBUTION"})',
     '"CLUSTER_OWNERSHIP_GT_25PCT"})'),
    (ON, "unknown line format guessed as not observed", '        return None, "UNPARSEABLE"\n\n    for key in LINES:',
     '        return None, "NOT_OBSERVED_BY_LAB"\n\n    for key in LINES:'),
    (ON, "authority read without observed mechanics", '        if mi is None:\n            v[name] = (None, v["oc_mechanics_issues"][1])',
     '        if mi is None and False:\n            v[name] = (None, v["oc_mechanics_issues"][1])'),
    (ON, "contradiction accepted", 'v[name] = (None, "INCONSISTENT_RECORD") if (on and mi == 0) else (float(on), None)', "v[name] = (float(on), None)"),
    (ON, "exit share uses market cap", 'cap, liq = snap.get("exit_cap_3pct"), snap.get("liquidity")', 'cap, liq = snap.get("exit_cap_3pct"), snap.get("mcap")'),
    (ON, "zero liquidity accepted", 'elif float(liq) <= 0 or float(cap) < 0:', "elif float(cap) < 0:"),
    (ON, "NO_SELL_ROUTE flag ignored", 'if nr is not None or (names is not None and "NO_SELL_ROUTE" in names):', "if nr is not None:"),
    (ON, "change of liquidity reversed", 'diff("oc_d_log1p_liquidity", aux["liquidity"], pa["liquidity"], True)',
     'diff("oc_d_log1p_liquidity", pa["liquidity"], aux["liquidity"], True)'),
    (ON, "authority switch ignores freeze", 'for n in ("oc_mint_authority_active", "oc_freeze_authority_active")]',
     'for n in ("oc_mint_authority_active", "oc_mint_authority_active")]'),
    (ON, "value available at the next export", 'vals[n] = _value(v, why, Td, ins)', "vals[n] = _value(v, why, Td + 1.0, ins)"),
    (ON, "non-finite value accepted", '    if v is not None and not math.isfinite(v):\n        raise OnchainError', '    if False:\n        raise OnchainError'),
    (ON, "v2 tolerance loosened", "abs(a - b) > 1e-9 * max(1.0, abs(a))", "abs(a - b) > 1e-3 * max(1.0, abs(a))"),
    (ON, "attach ignores the decision time", ' or float(s["decision_time"]) != e.decision_time:\n            raise B.IdentityJoinError("onchain-1',
     ':\n            raise B.IdentityJoinError("onchain-1'),
    (ON, "missing value becomes zero", 'x[c] = v["value"] if v["value"] is not None else float("nan")', 'x[c] = v["value"] if v["value"] is not None else 0.0'),
    (ON, "allowlist removed", "    bad = [c for c in columns if c not in ALLOWED]\n    if bad:\n        raise F.AsOfError(f\"columns {bad} are not in the Phase 09 allowlist (NC2-OC",
     "    bad = []\n    if bad:\n        raise F.AsOfError(f\"columns {bad} are not in the Phase 09 allowlist (NC2-OC"),
    # models and cards
    (ON, "count gate on all training rows", "    g = B.gate(len(use), int(y.sum()))\n    if g:\n        return _card(kind, target, train, cutoff, {\"abstain\": g, \"spec\": spec}, n_used=len(use)",
     "    g = B.gate(len(train), int(y_all.sum()))\n    if g:\n        return _card(kind, target, train, cutoff, {\"abstain\": g, \"spec\": spec}, n_used=len(use)"),
    (ON, "rule shrinkage removed", '"p": (sum(v) + M_SHRINK * b0) / (len(v) + M_SHRINK)}', '"p": sum(v) / len(v)}'),
    (ON, "rule missing cell scored as no-flag cell", '        return "MISSING"\n    return f"S{int(a)}D{int(b)}"', '        return "S0D0"\n    return f"S{int(a)}D{int(b)}"'),
    (ON, "required rows not enforced", 'ok = [i for i, e in enumerate(examples) if complete(e, spec["rows"])]', "ok = list(range(n))"),
    (ON, "P13 guard removed", 'early = [e for e in examples if e.decision_time < float(card["training_cutoff"])]', "early = []"),
    (ON, "card version check removed", 'if card.get("feature_set_sha") != feature_set_sha() or card.get("onchain_version") != ONCHAIN_VERSION:', "if False:"),
    (ON, "CX-S08 scored rows standardised with their own statistics",
     'prep, lr = K.Prep.from_dict(body["prep"]), K.Logistic.from_dict(body["logistic"])', 'prep, lr = K.Prep().fit(X), K.Logistic.from_dict(body["logistic"])'),
    (ON, "walk-forward index check removed", "        if want != got:\n            raise B.WalkForwardMismatch", "        if False:\n            raise B.WalkForwardMismatch"),
    (ON, "degenerate test inverted", "return bool(q.size > 1 and np.ptp(q) == 0)", "return bool(q.size > 1 and np.ptp(q) > 0)"),
    # early warning, veto, cap, wallets
    (ON, "alarm at or above the prevalence", 'a = r[model] > r["B0"]', 'a = r[model] >= r["B0"]'),
    (ON, "negative lead time accepted", "                if lead < 0:\n                    raise OnchainError", "                if False:\n                    raise OnchainError"),
    (ON, "a missing flag list is a pass", '        return {"veto": None, "state": "VETO_UNKNOWN", "flags": [], "structural": []}',
     '        return {"veto": False, "state": "NO_FATAL_FLAG", "flags": [], "structural": []}'),
    (ON, "forecast clears the veto", '"veto_overrides_forecast": v["veto"] is not False,',
     '"veto_overrides_forecast": v["veto"] is not False and not (forecast_doc.get("probability") or 1) < 0.01,'),
    (ON, "size cap ignores the loss limit", 'good = [q["size_usd"] for q in ok if q["proceeds_ratio"] >= 1 - max_loss]', 'good = [q["size_usd"] for q in ok]'),
    (ON, "exchange checked after the developer label", '    if address in set(custody) or address in cex_labels:', '    if False:'),
    (ON, "mint-like developer address trusted", "        if address.endswith(MINT_SUFFIXES) or address in set(known_mints):", "        if False:"),
    (ON, "a transfer counts as a sale", 'is_sale = kind == "SWAP" and direction == "SELL" and bool(movement.get("counterparty_is_pool"))',
     'is_sale = direction in ("SELL", "OUT")'),
    (ON, "inferred cluster counted as insider", 'bool(is_sale and role.get("role") == "DEV" and role.get("basis") == "OBSERVED")',
     'bool(is_sale and role.get("role") in ("DEV", "CLUSTER_MEMBER_INFERRED"))'),
    # collector adapter
    (DA, "CX-09 post-decision rows visible", 'return [o for o in obs if o["available_at"] is not None and o["available_at"] <= float(T)]',
     'return [o for o in obs if o["available_at"] is not None and o["available_at"] <= float(T) + 3600.0]'),
    (DA, "CX-09 assert_visible removed", '        if o.get("available_at") is None or o["available_at"] > float(T):\n            raise DepthLeakageError',
     '        if False:\n            raise DepthLeakageError'),
    (DA, "read-only open removed", 'con = sqlite3.connect(f"file:{p.resolve()}?mode=ro", uri=True)', "con = sqlite3.connect(str(p))"),
    (DA, "tracked lab database accepted", "    if rp in S._forbidden_paths():\n        raise AdapterError", "    if False:\n        raise AdapterError"),
    (DA, "migration version not checked", "        if v is None or int(v) < MIN_MIGRATION:", "        if False:"),
    (DA, "column check removed", "        if miss:\n            out.append(f\"{t}: columns {miss} missing\")", "        if False:\n            out.append(f\"{t}: columns {miss} missing\")"),
    (DA, "Solana compared without case", 'return a == b if chain == "solana" else a.lower() == b.lower()', "return a.lower() == b.lower()"),
    (DA, "export time not checked", "    if abs(float(r[\"export_time\"]) - float(decision_time)) > 1e-6:", "    if False:"),
    (DA, "proceeds from reported reserve", '            o["proceeds_ratio"] = float(r["out_usd"]) / float(r["size_usd"])',
     '            o["proceeds_ratio"] = float(r["reserve_usd"] or r["out_usd"]) / float(r["size_usd"])'),
    (DA, "PRICE_DISAGREES gets a number", 'if r["kind"] == "QUOTE" and r["state"] == "OK" and r["out_usd"] is not None and r["size_usd"]:',
     'if r["kind"] == "QUOTE" and r["state"] in ("OK", "PRICE_DISAGREES") and r["out_usd"] is not None and r["size_usd"]:'),
    (DA, "P37 lost route is not an event", '        return dict(base, state="ROUTE_LOST", label=1, baseline_id=b0["id"], horizon_id=h0["id"],',
     '        return dict(base, state="ROUTE_LOST", label=0, baseline_id=b0["id"], horizon_id=h0["id"],'),
    (DA, "P05 maturity check removed", '    if float(as_of) < T + horizon_s + horizon_tol_s:\n        return dict(base, state="NOT_YET_MATURED", label=None)',
     '    if False:\n        return dict(base, state="NOT_YET_MATURED", label=None)'),
    (DA, "unanswered read used as baseline", 'b = [o for o in qs if o["captured_at"] <= T + baseline_max_lag_s and o["state"] in ANSWERED]',
     'b = [o for o in qs if o["captured_at"] <= T + baseline_max_lag_s]'),
    (DA, "drop threshold direction", 'ev = h0["proceeds_ratio"] <= b0["proceeds_ratio"] * (1.0 - drop)', 'ev = h0["proceeds_ratio"] >= b0["proceeds_ratio"] * (1.0 - drop)'),
    (DA, "label is not size specific", 'and o["size_usd"] == size_usd\n          and o["captured_at"] is not None', '\n          and o["captured_at"] is not None'),
    (DA, "pools merged", '        g.setdefault(o["pool_address"], []).append(o)', '        g.setdefault("ALL", []).append(o)'),
]


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
        (root / "data").mkdir(exist_ok=True)
        if (REPO / "data/memelab.sqlite").is_file():
            shutil.copy2(REPO / "data/memelab.sqlite", root / "data/memelab.sqlite")
        orig = {p: (root / p).read_text() for p in (ON, DA)}
        cmd = [sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"]
        base = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("tests fail on the unmutated copy:\n" + base.stdout[-2000:])
        for path, name, old, new in MUTATIONS:
            src = orig[path]
            if src.count(old) != 1:
                results.append({"file": path, "mutation": name, "applied": False, "caught": None, "note": f"pattern found {src.count(old)} times"})
                continue
            (root / path).write_text(src.replace(old, new))
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
            first = next((ln for ln in r.stdout.splitlines() if ln.startswith("FAILED") or ln.startswith("ERROR")), "")
            results.append({"file": path, "mutation": name, "applied": True, "caught": r.returncode != 0, "first_failure": first[:200]})
            (root / path).write_text(src)
    applied = [r for r in results if r["applied"]]
    rep = {"mutations": len(MUTATIONS), "applied": len(applied), "caught": sum(1 for r in applied if r["caught"]),
           "survived": [r["mutation"] for r in applied if not r["caught"]],
           "not_applied": [r["mutation"] for r in results if not r["applied"]], "results": results}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("mutations", "applied", "caught", "survived", "not_applied")}))
    return 0 if rep["caught"] == rep["mutations"] else 1


if __name__ == "__main__":
    sys.exit(main())
