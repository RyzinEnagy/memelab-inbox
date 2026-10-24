"""Phase 17 reviewer check: machine-checks the factual claims of the release documents against the code, the evidence
files and a COPY of the research database. Read-only on the repository; writes only to the database copy.
Checks:
1. every `python -m memelab backtest ...` command in the runbook: the subcommand exists and every --flag is accepted;
2. the runbook's policy table against assess.DEFAULT_POLICY;
3. repository paths named in the three documents exist;
4. the release report's final-hash table against p10_runs.json, p11_results.json, the Phase 16 sealed rerun log, the
   committed clean-install log (made at HEAD, or only prose changed since) and the database file, plus a replay of the Phase 15 daily report on the copy;
5. corpus counts quoted in the release report and runbook against the copy.
Usage: python3 audits/backtesting/testing/p17_doc_claims_check.py <copy of bt.sqlite> [--runbook P] [--report P] [--licenses P]
Exit 0 when every check passes."""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

ap = argparse.ArgumentParser()
ap.add_argument("db")
ap.add_argument("--runbook", default=str(ROOT / "docs/backtesting/RUNBOOK.md"))
ap.add_argument("--report", default=str(ROOT / "docs/backtesting/RELEASE_REPORT.md"))
ap.add_argument("--licenses", default=str(ROOT / "docs/backtesting/LICENSE_ATTRIBUTIONS.md"))
args = ap.parse_args()
assert Path(args.db).resolve() != (ROOT / "data/backtest/bt.sqlite").resolve(), "use a copy"
runbook, report, lic = (Path(p).read_text() for p in (args.runbook, args.report, args.licenses))
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


# 1. runbook commands and flags
helps = {}


def flags_of(sub):
    if sub not in helps:
        r = subprocess.run([sys.executable, "-m", "memelab", "backtest", *sub.split(), "--help"], cwd=ROOT, capture_output=True, text=True)
        helps[sub] = (r.returncode, set(re.findall(r"--[a-z][a-z0-9-]*", r.stdout)))
    return helps[sub]


cmds = re.findall(r"`((?:python -m memelab )?backtest [^`]+|outcomes [^`]+)`", runbook)
for c in cmds:
    words = c.replace("python -m memelab ", "").split()
    words = words[1:] if words[0] == "backtest" else words
    sub = " ".join(words[:2]) if words[0] == "outcomes" and len(words) > 1 and not words[1].startswith("-") else words[0]
    code, known = flags_of(sub)
    used = set(re.findall(r"--[a-z][a-z0-9-]*", c))
    check(f"runbook command `{c[:60]}`", code == 0 and used <= known, f"unknown flags {sorted(used - known)}" if used - known else ("" if code == 0 else "no such subcommand"))

# 2. policy defaults
from memelab.backtest import assess  # noqa: E402
rows = dict(re.findall(r"^\| ([a-z_]+) \| ([^|]+) \|", runbook, re.M))
for k, v in assess.DEFAULT_POLICY.items():
    if k not in rows:
        check(f"policy default {k}", False, "missing from the runbook table")
        continue
    doc = rows[k].strip().strip('"')
    want = (f"{len(v)} TA strategies" if k == "ta_strategies" else
            str([int(x) if float(x).is_integer() else x for x in v]).replace("'", "") if isinstance(v, list) else
            str(v).lower() if isinstance(v, bool) else (str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)))
    check(f"policy default {k} = {doc}", doc == want, f"code has {want}")

# 3. paths named in the documents
for label, text in (("runbook", runbook), ("report", report), ("licenses", lic)):
    for p in sorted(set(re.findall(r"\b((?:audits|docs|memelab|tools|tests)/[A-Za-z0-9_./-]+[A-Za-z0-9_])", text))):
        if any(ch in p for ch in "<>*"):
            continue
        check(f"{label} names {p}", (ROOT / p).exists())

# 4. final hashes
table = dict(re.findall(r"^\| ([^|]+?) \| ([^|]+?) \|$", report.split("## Final hashes", 1)[1].split("##", 1)[0], re.M))
p10 = {r["strategy"]: r for r in json.loads((ROOT / "audits/backtesting/engine/p10_runs.json").read_text())}
p11 = json.loads((ROOT / "audits/backtesting/validation/p11_results.json").read_text())
sealed_log = (ROOT / "audits/backtesting/testing/logs/p16r4_sealed_rerun.log").read_text()
install_log = (ROOT / "audits/backtesting/release/logs/p17_clean_install.log").read_text()
db_hash = hashlib.sha256((ROOT / "data/backtest/bt.sqlite").read_bytes()).hexdigest()
head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
for item, val in table.items():
    v = val.strip()
    if item.startswith("research database file"):
        check("hash: research database file", db_hash.startswith(v), db_hash[:16])
    elif item.startswith("sealed-test cutoff"):
        check("hash: sealed-test cutoff dataset", str(p11["dataset_hash"]).startswith(v) and f'"dataset_hash_at_T1": "{p11["dataset_hash"]}' in sealed_log)
    elif item.startswith("whole-corpus dataset"):
        check("hash: whole-corpus dataset", all(r["dataset_hash"].startswith(v) for r in p10.values()) and re.search(r'"dataset_hash_no_cutoff": "' + v, sealed_log))
    elif item.startswith("Phase 11 pre-registration"):
        pre = hashlib.sha256((ROOT / "audits/backtesting/validation/P11_PREREG.md").read_bytes()).hexdigest()
        check("hash: Phase 11 pre-registration file", pre.startswith(v) and p11["prereg_sha256"].startswith(v), pre[:12])
    elif item.startswith("sealed-test ledgers"):
        for sid, hv in re.findall(r"([A-Z_]+) ([0-9a-f]{12})", v):
            check(f"hash: sealed-test ledger {sid}", p11["strategies"][sid]["test_ledger_hash"].startswith(hv) and f'"test_ledger_hash": "{p11["strategies"][sid]["test_ledger_hash"]}' in sealed_log)
    elif item.startswith("Phase 10 whole-universe runs"):
        for sid, rid, led in re.findall(r"([A-Z_]+) ([0-9a-f]{12}) / ([0-9a-f]{12})", v):
            check(f"hash: Phase 10 run {sid}", p10[sid]["run_id"].startswith(rid) and p10[sid]["ledger_hash"].startswith(led))
    elif item.startswith("Phase 15 replayed daily report"):
        from memelab.backtest import outcomes as O, store
        con = store.connect(args.db)
        asof = con.execute("SELECT MAX(available_at) FROM bt_market_bars").fetchone()[0]
        opps = O.opportunities(con)
        O.track(con, now=asof, observed_asof=asof, opps=opps)
        rep = O.daily_report(con, "2026-10-14", asof, opps=opps)
        now_h = store.sha256(rep)
        committed = store.sha256((ROOT / "audits/backtesting/outcomes/DAILY_SAMPLE.md").read_text())
        check("hash: Phase 15 daily report reproduces at HEAD", now_h.startswith(v), f"now {now_h[:12]}, committed DAILY_SAMPLE.md {committed[:12]}")
    elif item.startswith("Phase 17 clean-install run"):
        rid, led = re.findall(r"[0-9a-f]{12}", v)[:2]
        m = re.search(r"clone HEAD ([0-9a-f]{40})", install_log)
        check("hash: clean-install run id and ledger in the committed log", f"'run_id': '{rid}" in install_log and f"'ledger_hash': '{led}" in install_log)
        # The log is made from a commit and then committed, so HEAD is usually one step past it. The real claim is that
        # nothing the log tested has changed since: every later change must be prose (.md that no .py or .sh
        # file names) or the log itself.
        changed = []
        if m and m.group(1) != head:
            changed = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", m.group(1), head], capture_output=True, text=True).stdout.split()
        def read_by_code(f):  # R5: a .md file that a test, tool or script opens is evidence, not prose. This checker is
            name = Path(f).name  # left out: it checks the documents it reads at HEAD itself.
            r = subprocess.run(["git", "-C", str(ROOT), "grep", "-l", "-F", name, head, "--", "*.py", "*.sh",
                                ":(exclude)audits/backtesting/testing/p17_doc_claims_check.py"], capture_output=True, text=True)
            return bool(r.stdout.strip())
        code_changed = [f for f in changed if not ((f.endswith(".md") and not read_by_code(f)) or f == "audits/backtesting/release/logs/p17_clean_install.log")]
        check("clean-install log was made at HEAD or only prose changed since", m and not code_changed,
              f"log {m.group(1)[:7] if m else None}, HEAD {head[:7]}, non-prose changes since: {code_changed[:5]}")

# 5. corpus counts
import sqlite3  # noqa: E402
c = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
bars = c.execute("SELECT COUNT(*) FROM bt_market_bars").fetchone()[0]
mints = c.execute("SELECT COUNT(DISTINCT mint) FROM bt_market_bars").fetchone()[0]
uni = c.execute("SELECT COUNT(DISTINCT mint) FROM bt_universe_members").fetchone()[0]
nobars = c.execute("SELECT COUNT(*) FROM (SELECT DISTINCT mint FROM bt_universe_members WHERE mint NOT IN (SELECT DISTINCT mint FROM bt_market_bars))").fetchone()[0]
check("report: 139,168 hourly bars over 258 mints", f"{bars:,} hourly bars over {mints} mints" in report, f"{bars:,} over {mints}")
check("report: 429 of 686 universe mints have no stored bars", f"{nobars} of {uni} universe mints have no stored bars" in report, f"{nobars} of {uni}")
check("runbook: storage sentence", f"{bars:,} hourly bars over {mints} mints" in runbook)

bad = [r for r in results if not r[1]]
for name, ok, detail in results:
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))
print(f"{len(results) - len(bad)} of {len(results)} checks pass")
sys.exit(1 if bad else 0)
