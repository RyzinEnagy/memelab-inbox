"""Skeptic 09: my own mutations of onchain.py and depth_adapter.py at HEAD (not the phase's list). Each runs
tests/test_predictive_onchain.py on a fresh `git archive HEAD` copy. Usage: python p09_own_mutations.py CLONE OUT.json"""
import json, os, subprocess, sys, tempfile, shutil
clone, outp = sys.argv[1], sys.argv[2]
ON, DA = "memelab/predictive/onchain.py", "memelab/predictive/depth_adapter.py"
M = [
 (DA, "CX-09 with a one-hour tolerance in visible_at", 'o["available_at"] <= float(T)]', 'o["available_at"] <= float(T) + 3600.0]'),
 (DA, "assert_visible one-hour tolerance", 'o["available_at"] > float(T):', 'o["available_at"] > float(T) + 3600.0:'),
 (DA, "link ignores the export time", 'if abs(float(r["export_time"]) - float(decision_time)) > 1e-6:', 'if abs(float(r["export_time"]) - float(decision_time)) > 1e12:'),
 (DA, "link tolerates an hour between the two walks", 'if abs(float(r["export_time"]) - float(decision_time)) > 1e-6:', 'if abs(float(r["export_time"]) - float(decision_time)) > 3600:'),
 (DA, "link takes the first of two collector rows", '        raise DepthIdentityError("two collector decisions share one exact row")', '        rows = rows[:1]'),
 (DA, "adapter may open the lab database", '    if rp in S._forbidden_paths():', '    if False:'),
 (DA, "schema migration floor removed", '        if v is None or int(v) < MIN_MIGRATION:', '        if False:'),
 (DA, "exit_context uses the oldest OK quote", '    q = ok[-1]', '    q = ok[0]'),
 (DA, "pre-decision quote accepted as label baseline", 'and o["captured_at"] is not None and T <= o["captured_at"] <= float(as_of)]', 'and o["captured_at"] is not None and T - 3600.0 <= o["captured_at"] <= float(as_of)]'),
 (ON, "dev-wallet mint suffix check removed", 'if address.endswith(MINT_SUFFIXES) or address in set(known_mints):', 'if address in set(known_mints):'),
 (ON, "CEX labels ignored (custody list only)", '    if address in set(custody) or address in cex_labels:', '    if address in set(custody):'),
 (ON, "deposit to an exchange counted as a sale", '    is_sale = kind == "SWAP" and direction == "SELL" and bool(movement.get("counterparty_is_pool"))',
  '    is_sale = (kind == "SWAP" and direction == "SELL" and bool(movement.get("counterparty_is_pool"))) or (kind == "TRANSFER" and movement.get("to_role") == "CUSTODY_OR_EXCHANGE")'),
 (ON, "inferred cluster sale counted as insider", '"counts_as_insider_distribution": bool(is_sale and role.get("role") == "DEV" and role.get("basis") == "OBSERVED"),',
  '"counts_as_insider_distribution": bool(is_sale and role.get("role") in ("DEV", "CLUSTER_MEMBER_INFERRED")),'),
 (ON, "AsOfView reads a day ahead", '    view = F.AsOfView(con, T, "provider")', '    view = F.AsOfView(con, T + 86400.0, "provider")'),
 (ON, "size cap ignores max_loss", '    good = [q["size_usd"] for q in ok if q["proceeds_ratio"] >= 1 - max_loss]', '    good = [q["size_usd"] for q in ok]'),
 (ON, "unknown veto treated as no veto", '"veto_overrides_forecast": v["veto"] is not False,', '"veto_overrides_forecast": v["veto"] is True,'),
 (ON, "missing flag list is a pass", '        return {"veto": None, "state": "VETO_UNKNOWN", "flags": [], "structural": []}', '        return {"veto": False, "state": "NO_FATAL_FLAG", "flags": [], "structural": []}'),
 (ON, "unknown token program read as SPL", '(None, wt or ("ABSENT_IN_SNAPSHOT" if tp is None else "UNPARSEABLE")))', '(0.0, None))'),
 (ON, "version 2 consistency tolerance 1e-2", 'abs(a - b) > 1e-9 * max(1.0, abs(a))', 'abs(a - b) > 1e-2 * max(1.0, abs(a))'),
 (ON, "early wallet UNKNOWN mapped to HOLDING", 'EARLY_DIR = {"ACCUMULATING": 0.0, "HOLDING": 1.0,', 'EARLY_DIR = {"UNKNOWN": 1.0, "ACCUMULATING": 0.0, "HOLDING": 1.0,'),
 (ON, "capture delay sign flipped", '_value(Td - aux["t"], None, Td, ins)', '_value(aux["t"] - Td, None, Td, ins)'),
 (ON, "rule shrinkage m=0", "M_SHRINK = 20.0", "M_SHRINK = 0.0001"),
 (ON, "early warning at equality", 'a = r[model] > r["B0"]', 'a = r[model] >= r["B0"]'),
 (ON, "negative lead time tolerated", '                if lead < 0:\n                    raise', '                if lead < -86400:\n                    raise'),
]
res = []
with tempfile.TemporaryDirectory() as td:
    root = os.path.join(td, "r")
    os.makedirs(root)
    subprocess.run(f"git -C {clone} archive HEAD | tar -x -C {root}", shell=True, check=True)
    env = dict(os.environ, MEMELAB_DB=os.path.join(td, "x.sqlite"))
    cmd = [sys.executable, "-B", "-m", "pytest", "tests/test_predictive_onchain.py", "-q", "-x", "-p", "no:cacheprovider"]
    base = subprocess.run(cmd, cwd=root, capture_output=True, text=True, env=env)
    assert base.returncode == 0, base.stdout[-1500:]
    for path, name, old, new in M:
        p = os.path.join(root, path); src = open(p).read()
        if src.count(old) != 1:
            res.append({"mutation": name, "applied": False, "count": src.count(old)}); continue
        open(p, "w").write(src.replace(old, new))
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, env=env)
        first = next((l for l in r.stdout.splitlines() if l.startswith(("FAILED", "ERROR"))), "")
        res.append({"mutation": name, "file": path, "applied": True, "caught": r.returncode != 0, "first_failure": first[:160]})
        open(p, "w").write(src)
rep = {"applied": sum(r["applied"] for r in res), "caught": sum(1 for r in res if r.get("caught")),
       "survived": [r["mutation"] for r in res if r["applied"] and not r["caught"]], "not_applied": [r["mutation"] for r in res if not r["applied"]], "results": res}
open(outp, "w").write(json.dumps(rep, indent=1))
print(json.dumps({k: rep[k] for k in ("applied", "caught", "survived", "not_applied")}, indent=1))
