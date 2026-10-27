"""Phase 19: prior contact with the prospective holdout, from metadata only (no candle body, no label is opened).

    python -B contact_scan.py OUT.json

Lists (1) every committed raw GeckoTerminal read of Phases 04 to 06 whose pool or mint is a prospective Solana decision's and
whose boundary is after that decision's entry (manifest columns only: pool, mint, boundary); (2) the measured market changes
between two attempts that the Phase 18 replay report printed for prospective mints (the line text is not copied, only the
count and the mints' first six characters). Decisions come from the state exports in git at REF through decisions.py.
"""
from __future__ import annotations

import csv
import glob
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import decisions as D  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import sources as SRC  # noqa: E402

REF = "71fc50e1eb86d916034bb0285a466cf2ec1cc4d0"


def main(out: Path) -> int:
    ex = SRC.export_versions(REPO, REF)
    evs = [e for e in D.decisions(D.candidates(ex)) if e["decision_time"] >= L.prospective_start()]
    sol = [e for e in evs if e["chain"] == "solana"]
    pool_of = {}
    for e in sol:
        pool_of.setdefault(e["mint"], set())
    reads = []
    for man in sorted(glob.glob(str(REPO / "audits/predictive-intelligence/phase_0[456]/**/MANIFEST.csv"), recursive=True)):
        for m in csv.DictReader(open(man)):
            b = m.get("boundary_at") or ""
            if not b:
                continue
            bt = C.parse_utc(b) if b.endswith("Z") else float(b)
            for e in sol:
                if m.get("mint") == e["mint"] and bt > L.t_entry(e["decision_time"]):
                    reads.append({"manifest": Path(man).relative_to(REPO).as_posix(), "mint6": e["mint"][:6],
                                  "decision_time_utc": L._iso(e["decision_time"]), "boundary_utc": b,
                                  "minutes_after_entry": round((bt - L.t_entry(e["decision_time"])) / 60, 1)})
    rep = (REPO / "audits/predictive-intelligence/phase_18/real/REAL_REPLAY_REPORT.md").read_text()
    lines = [x for x in rep.splitlines() if "measured market changes since the previous attempt" in x]
    mints = sorted({e["mint"] for e in sol})
    printed = sorted({m[:6] for m in mints for x in lines if m in x})
    res = {"ref": REF, "prospective_events": len(evs), "solana_events": len(sol), "solana_mints": len(mints),
           "raw_reads_after_a_prospective_entry": reads,
           "phase18_report_measured_change_lines": len(lines), "phase18_measured_change_mints6": printed,
           "note": "metadata only: no body was decompressed and no label or price was computed"}
    out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in res.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
