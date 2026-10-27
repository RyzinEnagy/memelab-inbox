"""Repair pass 2: compare the repeated recorded run (OUT_DIR) with the first-pass outputs committed at 872578d, file by file, and
for the rule documents also after removing the fields the repair added or that depend on the run time.

    python -B rerun_diff.py OUT_DIR RESULT.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
FIRST = "872578d"
P = "audits/predictive-intelligence/phase_14/"


def old(rel: str) -> bytes | None:
    p = subprocess.run(["git", "-C", str(REPO), "show", f"{FIRST}:{P}{rel}"], capture_output=True)
    return p.stdout if p.returncode == 0 else None


def strip(d: dict) -> dict:
    d = json.loads(json.dumps(d))
    d.pop("doc_sha256", None)
    d["provenance"].pop("created_at_utc", None)
    d["cost"].pop("llm_actions_observed", None)
    return d


def main(out: str, res_path: str) -> int:
    o = Path(out)
    files = sorted(x.relative_to(o).as_posix() for x in o.rglob("*") if x.is_file())
    res = {"first_pass": FIRST, "files": {}}
    for f in files:
        a, b = old(f), (o / f).read_bytes()
        res["files"][f] = "NEW" if a is None else ("BYTE_EQUAL" if a == b else "DIFFERS")
    old_docs = [json.loads(x)["document"] for x in old("behavioral/RULE_SCENARIOS_DEV.jsonl").decode().splitlines()]
    new_docs = [json.loads(x)["document"] for x in (o / "behavioral/RULE_SCENARIOS_DEV.jsonl").read_text().splitlines()]
    res["rule_documents"] = {"count_old": len(old_docs), "count_new": len(new_docs),
                             "equal_after_removing_doc_sha_created_at_and_llm_actions_observed": sum(strip(a) == strip(b) for a, b in zip(old_docs, new_docs)),
                             "hypotheses_equal": sum(a["hypotheses"] == b["hypotheses"] for a, b in zip(old_docs, new_docs))}
    oc, nc = json.loads(old("behavioral/RULE_COUNTS.json")), json.loads((o / "behavioral/RULE_COUNTS.json").read_text())
    res["rule_counts_equal_except_time_and_sha"] = {k: oc[k] == nc[k] for k in oc if k not in ("created_at_utc", "rule_scenarios_sha256")}
    res["seeds_byte_equal"] = old("behavioral/SEEDS_DEV.jsonl") == (o / "behavioral/SEEDS_DEV.jsonl").read_bytes()
    Path(res_path).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
