"""Phase 09 repair pass 2: the skeptic's counterexample CX-S09 against the first-pass size cap (onchain.py at 796e844) and the
repaired one. Builds the skeptic's fixture (a 19.4 h old quote on another pool, the decision pool 50 min before the decision, the
collector's own first read 25 min after it) in a temp collector database from the documented schema and writes a JSON report.

    python -B cx_s09_check.py OUT.json
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from memelab.predictive import depth_adapter as DA  # noqa: E402
from memelab.predictive import onchain as O  # noqa: E402

MINT, A, B = "CxMint11111111111111111111111111111111111pump", "PoolA", "PoolB"
T = 1793100000.0


def old_onchain():
    src = subprocess.run(["git", "show", "796e844:memelab/predictive/onchain.py"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    spec = importlib.util.spec_from_loader("memelab.predictive.onchain_first_pass", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "memelab.predictive"
    sys.modules[spec.name] = mod
    exec(compile(src, "onchain_first_pass.py", "exec"), mod.__dict__)
    return mod


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bt.sqlite"
        con = sqlite3.connect(p)
        con.executescript((REPO / "tests/fixtures/predictive/bt_depth_schema_v2.sql").read_text())
        con.execute("INSERT INTO bt_schema_migrations VALUES (2,'forward depth collector','y',0)")
        dec = ("INSERT INTO bt_depth_decisions (chain,mint,pool_address,pool_source,export_commit,export_time,created_at,row_sha256,status,"
               "recorded_at,content_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?)")
        con.execute(dec, ("solana", MINT, A, "EXPORT_PRIMARY_POOL", "c0", T - 72000, T - 72100, "r0", "WATCH", T, "d0"))
        con.execute(dec, ("solana", MINT, A, "EXPORT_PRIMARY_POOL", "c1", T, T - 100, "r1", "WATCH", T, "d1"))
        snap = ("INSERT INTO bt_depth_snapshots (run_id,decision_id,chain,mint,pool_address,kind,provider,size_usd,captured_at,http_status,state,"
                "out_usd,price_impact,recorded_at,content_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
        for i, (did, pool, t, size, ratio) in enumerate(((1, B, T - 70000, 2000.0, 0.99), (1, A, T - 3000, 2000.0, 0.60),
                                                         (1, A, T - 3000, 100.0, 0.97), (2, A, T + 1500, 2000.0, 0.98))):
            con.execute(snap, ("r", did, "solana", MINT, pool, "QUOTE", "jupiter", size, t, 200, "OK", size * ratio, 0.01, T, f"s{i}"))
        con.commit()
        con.close()
        obs = DA.observations(DA.connect_ro(p), chain="solana", mint=MINT)
    first = old_onchain().decision_support({"probability": None}, [], obs, max_loss=0.05)["size_cap"]
    repaired = O.decision_support({"probability": None}, [], obs, decision_time=T, pool_address=A, max_loss=0.05, max_age_s=6 * 3600.0)["size_cap"]
    rep = {"rows": len(obs), "first_pass_size_cap": first, "repaired_size_cap": repaired,
           "first_pass_wrong": first.get("size_cap_usd") == 2000.0, "repaired_as_of": repaired.get("size_cap_usd") == 100.0}
    rep["pass"] = rep["first_pass_wrong"] and rep["repaired_as_of"]
    Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
    Path(sys.argv[1]).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("first_pass_wrong", "repaired_as_of", "pass")}))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
