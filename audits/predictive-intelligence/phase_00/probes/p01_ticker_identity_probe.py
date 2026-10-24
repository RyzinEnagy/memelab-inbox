"""Phase 00 probe for P01 (same symbol, different mints). Read-only against the repo; writes only to a temp folder.

Part A (real data): imports the state export of a ref (default origin/main) into a temp database and checks that
tokens sharing a symbol stay separate rows keyed by mint and that every thesis joins to its token by mint.
It also shows how many thesis rows a symbol join would wrongly merge.

Part B (code path): feeds the catalyst matcher an invented event whose ticker search returns ONE candidate that is an
impostor (the real token is absent from the provider answer). Records the link the existing code stores.

Usage (from the repo root): python audits/predictive-intelligence/phase_00/probes/p01_ticker_identity_probe.py [ref]
No network. Exit 0 always; the printed JSON is the result.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

REF = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True).stdout.strip()
TMP = tempfile.mkdtemp(prefix="pi_p01_")
os.environ["MEMELAB_DB"] = os.path.join(TMP, "p01.sqlite")
sys.path.insert(0, ROOT)

from memelab import db  # noqa: E402

assert str(db.DB_PATH).startswith(TMP), "refusing to run against a tracked database"
db.init_db()
out: dict = {"ref": REF, "ref_sha": subprocess.run(["git", "rev-parse", REF], check=True, capture_output=True, text=True).stdout.strip(), "temp_db": db.DB_PATH.name}

# Part A: real state export
raw = subprocess.run(["git", "show", f"{REF}:data/state/latest.json"], check=True, capture_output=True).stdout
p = os.path.join(TMP, "state.json")
with open(p, "wb") as f:
    f.write(raw)
from memelab import state  # noqa: E402

out["import_counts"] = state.import_(p)
with db.connect() as con:
    out["tokens"] = con.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
    out["distinct_mints"] = con.execute("SELECT COUNT(DISTINCT mint) FROM tokens").fetchone()[0]
    coll = con.execute("SELECT UPPER(symbol) s, COUNT(DISTINCT mint) n FROM tokens WHERE symbol IS NOT NULL GROUP BY UPPER(symbol) HAVING n > 1").fetchall()
    out["symbols_with_2plus_mints"] = len(coll)
    out["mints_in_collision_groups"] = sum(r["n"] for r in coll)
    out["theses"] = con.execute("SELECT COUNT(*) FROM theses").fetchone()[0]
    out["theses_without_token_row"] = con.execute("SELECT COUNT(*) FROM theses t LEFT JOIN tokens k ON k.mint=t.mint WHERE k.mint IS NULL").fetchone()[0]
    out["theses_join_rows_by_mint"] = con.execute("SELECT COUNT(*) FROM theses t JOIN tokens k ON k.mint=t.mint").fetchone()[0]
    out["theses_join_rows_by_symbol"] = con.execute(
        "SELECT COUNT(*) FROM theses t JOIN tokens a ON a.mint=t.mint JOIN tokens b ON UPPER(b.symbol)=UPPER(a.symbol)").fetchone()[0]
    out["note_A"] = "a symbol join multiplies thesis rows by the number of mints sharing the symbol; the stored keys are mints, so the existing tables do not do this"

# Part B: catalyst matcher, ticker-only search, impostor is the only candidate
from memelab.catalyst import ingest as I, match as M  # noqa: E402

t0 = time.time()
I.ingest_bodies({"cat:news:cointelegraph": {"_cat": "news:cointelegraph", "s": 200, "body": [
    {"title": "Coinbase adds support for Probe Inu (PRBI)", "link": "https://cointelegraph.com/probe-inu", "pub": "Wed, 07 Oct 2026 01:00:00 +0000"}]}},
    retrieved_at=t0)
per_event, _ = M.terms_for_events()
IMPOSTOR = "Imp0ster1111111111111111111111111111111111"
bodies = {"jup_tok:PRBI": [{"id": IMPOSTOR, "symbol": "PRBI", "name": "Probe Inu", "liquidity": 80_000, "mcap": 400_000}],
          "jup_tok:Probe Inu": [{"id": IMPOSTOR, "symbol": "PRBI", "name": "Probe Inu", "liquidity": 80_000}]}
out["terms"] = list(per_event.values())[0]
out["link_stats"] = M.link_events(bodies, per_event)
with db.connect() as con:
    rows = [dict(r) for r in con.execute("SELECT mint, link_type, link_strength, competing_json FROM catalyst_token_links")]
out["links"] = rows
out["note_B"] = ("the catalyst matcher stores a mint link from a ticker or name search; with a single visible candidate it is graded "
                 "MODERATE, not AMBIGUOUS. catalyst_outcomes (monitor.record_outcomes) are then keyed by that mint.")
print(json.dumps(out, indent=1, default=str))
