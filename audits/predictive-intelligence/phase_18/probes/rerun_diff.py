"""Phase 18: what changed between the recorded real outputs at one commit (read from git) and the outputs in the working tree.

    python -B rerun_diff.py OLD_COMMIT OUT.json

Counts, statuses, reasons and alert decisions are compared field by field. Report and alert texts are compared line by line
after masking what a new run always changes (hex ids and hashes, ISO times, local times, run ages); the lines that still
differ are listed verbatim (they hold no local path).
"""
from __future__ import annotations

import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
REAL = "audits/predictive-intelligence/phase_18/real"
TEXTS = ["REAL_SCOUT_REPORT.md", "REAL_REPLAY_REPORT.md", "REAL_ALERTS_SCOUT_DRY_RUN.txt", "REAL_ALERTS_REPLAY_DRY_RUN.txt"]
MASKS = [(re.compile(r"\b[0-9a-f]{12,64}\b"), "<hex>"), (re.compile(r"fc_[0-9a-f]{32}"), "<fc>"),
         (re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ"), "<utc>"), (re.compile(r"\d{4}-\d\d-\d\d \d\d:\d\d (EDT|EST|UTC)"), "<local>"),
         (re.compile(r"age at capture [0-9.]+ (minutes|hours|days)"), "age at capture <age>")]


def _mask(s: str) -> str:
    for rx, rep in MASKS:
        s = rx.sub(rep, s)
    return s


def _old(commit: str, name: str) -> str:
    return subprocess.run(["git", "show", f"{commit}:{REAL}/{name}"], cwd=REPO, capture_output=True, text=True, check=True).stdout


def main(commit: str, out: str) -> int:
    o = json.loads(_old(commit, "REAL_RUN_CHECKS.json"))
    n = json.loads((REPO / REAL / "REAL_RUN_CHECKS.json").read_text())
    fields = {}
    for part in ("scout_report", "replay_report"):
        for k in ("state", "counts", "statuses", "reason_counts", "input_states", "lab_states", "vetoes", "veto_opportunities",
                  "backtest_results", "not_attempted_events", "percent_or_fraction_outside_definitions", "local_path", "trading_word"):
            fields[f"{part}.{k}"] = {"equal": o[part][k] == n[part][k]} | ({} if o[part][k] == n[part][k] else {"old": o[part][k], "new": n[part][k]})
    for part in ("scout_alerts", "replay_alerts"):
        for k in ("outcome", "candidates", "new", "deduped", "alert_policies", "suppressed", "ledger", "remote_deliveries_succeeded",
                  "sent_folder_exists", "previews"):
            fields[f"{part}.{k}"] = {"equal": o[part][k] == n[part][k]} | ({} if o[part][k] == n[part][k] else {"old": o[part][k], "new": n[part][k]})
    texts = {}
    for name in TEXTS:
        a, b = _old(commit, name).splitlines(), (REPO / REAL / name).read_text().splitlines()
        changed = [l for l in difflib.unified_diff(a, b, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        am, bm = [_mask(x) for x in a], [_mask(x) for x in b]
        rest = [l for l in difflib.unified_diff(am, bm, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        texts[name] = {"lines_old": len(a), "lines_new": len(b), "changed_lines": len(changed), "changed_after_masking_ids_and_times": len(rest),
                       "remaining_differences": sorted(set(rest))[:40]}
    rep = {"old_commit": commit, "fields": fields, "fields_not_equal": sorted(k for k, v in fields.items() if not v["equal"]), "texts": texts}
    Path(out).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"fields_not_equal": rep["fields_not_equal"],
                      "texts": {k: (v["changed_lines"], v["changed_after_masking_ids_and_times"]) for k, v in texts.items()}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
