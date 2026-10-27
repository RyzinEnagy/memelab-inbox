"""Phase 20 (G7): compare the runs of flag_off_identity.sh. Hashes, counts and booleans only.

    python -B flag_off_summary.py OUTDIR OUTJSON
"""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path


def tables(path: Path) -> dict:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    out = {}
    for t in ("tokens", "theses", "entries", "watchlist", "rejections"):
        rows = [{k: r[k] for k in r.keys() if not (t == "tokens" and k in ("first_seen_at", "last_seen_at"))}
                for r in con.execute(f"SELECT * FROM {t} ORDER BY rowid")]
        out[t] = hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()
    con.close()
    return out


def reports(d: Path) -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.glob("*.md"))}


def main(out: Path, outjson: Path) -> int:
    runs = {}
    for ln in (out / "logs" / "runs.txt").read_text().splitlines():
        f = ln.split()
        runs[f[0]] = {"export": f[2], "exit": int(f[4]), "commit": f[6], "private_dir": f[8]}
    res = {"runs": runs, "exports_sha256": (out / "logs" / "exports.sha256").read_text().split()[0::2], "comparisons": {}}
    ok = True
    for name, r in runs.items():
        r["reports"] = reports(out / "runs" / name)
        r["tables"] = tables(out / "runs" / name / "lab.sqlite")
        r["predictive_modules_imported"] = json.loads((out / "logs" / f"{name}.imports.json").read_text())
        r["sandbox_tracked_changes"] = [x for x in (out / "logs" / f"{name}.git_status").read_text().splitlines() if x.strip()]
        r["stdout_sha256"] = hashlib.sha256((out / "logs" / f"{name}.stdout").read_bytes()).hexdigest()
    for name, r in runs.items():
        if name.startswith("base_"):
            continue
        b = runs["base_" + name[len("frozen_"):]]
        cmp = {"reports_byte_equal": r["reports"] == b["reports"], "reports": len(r["reports"]),
               "stdout_byte_equal": r["stdout_sha256"] == b["stdout_sha256"],
               "lab_tables_equal": r["tables"] == b["tables"], "exit_equal": r["exit"] == b["exit"], "exit": r["exit"],
               "no_private_dir": r["private_dir"] == "no", "no_predictive_import": r["predictive_modules_imported"] == [],
               "no_tracked_change": r["sandbox_tracked_changes"] == []}
        res["comparisons"][name] = cmp
        ok = ok and all(cmp[k] for k in cmp if k not in ("reports", "exit"))
    res["checkout_status"] = (out / "logs" / "checkout_git_status.txt").read_text().splitlines()
    res["all_identical"] = ok and res["checkout_status"] == []
    outjson.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"all_identical": res["all_identical"], "runs": len(runs),
                      "failing": {k: [x for x, v in c.items() if v is False] for k, c in res["comparisons"].items() if not all(
                          v for x, v in c.items() if x not in ("reports", "exit"))},
                      "frozen_exits": {k: c["exit"] for k, c in res["comparisons"].items()}}))
    return 0 if res["all_identical"] else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
