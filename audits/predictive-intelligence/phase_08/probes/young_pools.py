"""Phase 08 repair pass 2 (skeptic m1): which CENSORED_RETRIEVAL decisions are pools younger than the 24 h window at T (the
history did not exist) rather than retrieval gaps. Reads the Phase 05 store read-only; no label is read.

    python -B young_pools.py OUT.json [--feature-store PATH]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
FS = "/home/claude/pi_research/p05/predictive_store.sqlite"


def t(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    return datetime.fromisoformat(str(x).replace("Z", "+00:00")).timestamp()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--feature-store", default=FS)
    a = ap.parse_args()
    con = sqlite3.connect(f"file:{a.feature_store}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    import csv
    rows = [r for r in csv.DictReader(open(REPO / "audits/predictive-intelligence/phase_08/experiments/TECH_FEATURES_DEVELOPMENT.csv"))
            if r["tech_status"] == "CENSORED_RETRIEVAL"]
    out = []
    for r in rows:
        d = con.execute("SELECT decision_time, pool_address, token_json, mint FROM predictive_decisions WHERE decision_key=?",
                        (r["decision_key"],)).fetchone()
        T = float(d["decision_time"])
        tok = json.loads(d["token_json"]) if d["token_json"] else {}
        fp = t(tok.get("first_pool_at"))
        first = con.execute("SELECT MIN(start_at) FROM predictive_candles WHERE mint=? AND pool_address=? AND period_s=300",
                            (d["mint"], d["pool_address"])).fetchone()[0]
        st = con.execute("SELECT status, need_from, cover_from, calls FROM predictive_source_status WHERE mint=? AND pool_address=? "
                         "AND boundary_at >= ? ORDER BY checked_at", (d["mint"], d["pool_address"], T - 300)).fetchall()
        age_h = (T - fp) / 3600 if fp is not None else None
        young = age_h is not None and age_h < 24.0 + 600 / 3600          # the 24 h window plus one candle cannot exist
        out.append({"decision_key": r["decision_key"], "pool_age_h_at_T": round(age_h, 2) if age_h is not None else None,
                    "first_candle_minus_first_pool_at_h": round((first - fp) / 3600, 2) if (first is not None and fp is not None) else None,
                    "history_before_T_h": round((T - first) / 3600, 2) if first is not None else None,
                    "candles_begin_within_0_1_h_of_first_pool": (first is not None and fp is not None and abs(first - fp) <= 360),
                    "series": [dict(s) for s in st], "class": "POOL_YOUNGER_THAN_WINDOW" if young else "OLDER_POOL_SHORT_HISTORY"})
    rep = {"censored_retrieval_decisions": len(out),
           "pool_younger_than_window": sum(1 for o in out if o["class"] == "POOL_YOUNGER_THAN_WINDOW"),
           "older_pool_short_history": sum(1 for o in out if o["class"] == "OLDER_POOL_SHORT_HISTORY"), "rows": out,
           "reading": ("a pool younger than the 24 h window at T has no history to fetch; the frozen version 2 coverage rule still "
                       "labels it OUTSIDE_FETCHED_WINDOW (RETRIEVAL basis). No number moves: such rows are excluded either way. "
                       "Consequence: tech-1 models cannot score a pool younger than about 24 h 5 min at its decision.")}
    Path(a.out).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("censored_retrieval_decisions", "pool_younger_than_window", "older_pool_short_history")}))


if __name__ == "__main__":
    sys.exit(main())
