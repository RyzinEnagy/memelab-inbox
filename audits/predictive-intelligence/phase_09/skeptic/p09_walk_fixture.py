"""Skeptic 09 fixture: a realistic git history on which the collector's walk (backtesting depth.export_decisions) and the
predictive walk (sources.export_versions + decisions.decisions) disagree, then what depth_adapter.link does.
Step 1 (run with the backtesting code on sys.path): python p09_walk_fixture.py collect BTCODE WORKDIR
Step 2 (run with the predictive clone on sys.path):  python p09_walk_fixture.py link CLONE WORKDIR
History (one Solana mint M, export file data/state/latest.json):
  A  t0        rows r1                      (baseline export)
  S  t0+600    side branch from A: rows r1, r2   (a branch export committed earlier than main's B)
  B  t0+1200   main: rows r1, r3
  Mg t0+1800   merge S into main, resolved to S's file (r1, r2): the merge is TREESAME to its second parent for the path
  C  t0+3600   main: rows r1, r2, r3 (r3 re-exported)
Predictive (first-parent A, B, Mg, C): r3 first visible at B, r2 at Mg. Collector (git log with history simplification, sorted
by time): A, S, Mg?, C ... r2 at S (earlier), r3 only at C (B is pruned)."""
import json, os, subprocess, sys, sqlite3
mode, code, work = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, code)
repo = os.path.join(work, "walkrepo")
MINT = "So1aMint1111111111111111111111111111111111pump"
POOL = "Poo1111111111111111111111111111111111111111"
t0 = 1793000000
def row(i, created):
    return {"id": i, "mint": MINT, "created_at": created, "status": "WATCH", "score": 50 + i, "fatal_flags_json": "[]",
            "snapshot_json": json.dumps({"price": 1.0 + i, "t": created})}
TOK = [{"mint": MINT, "chain": "solana", "primary_pool": POOL}]
r1, r2, r3 = row(1, t0 - 100), row(2, t0 + 500), row(3, t0 + 1100)
def git(*a, t=None):
    env = dict(os.environ)
    if t is not None:
        env.update(GIT_AUTHOR_DATE=f"@{t} +0000", GIT_COMMITTER_DATE=f"@{t} +0000")
    env.update(GIT_AUTHOR_NAME="s", GIT_AUTHOR_EMAIL="s@x", GIT_COMMITTER_NAME="s", GIT_COMMITTER_EMAIL="s@x")
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True, env=env).stdout
def write(rows):
    os.makedirs(os.path.join(repo, "data/state"), exist_ok=True)
    with open(os.path.join(repo, "data/state/latest.json"), "w") as f:
        json.dump({"_tables": {"theses": rows, "tokens": TOK}}, f)
if mode == "collect":
    subprocess.run(["rm", "-rf", repo]); os.makedirs(repo)
    git("init", "-q", "-b", "main")
    write([r1]); git("add", "-A"); git("commit", "-qm", "A", t=t0)
    git("checkout", "-qb", "side"); write([r1, r2]); git("commit", "-qam", "S", t=t0 + 600)
    git("checkout", "-q", "main"); write([r1, r3]); git("commit", "-qam", "B", t=t0 + 1200)
    subprocess.run(["git", "-C", repo, "merge", "-q", "--no-ff", "--no-commit", "side"], capture_output=True)
    write([r1, r2]); git("add", "-A"); git("commit", "-qm", "Mg", t=t0 + 1800)
    write([r1, r2, r3]); git("commit", "-qam", "C", t=t0 + 3600)
    from memelab.backtest import depth, store
    ex = depth.export_decisions(repo, ref="main", now=t0 + 3700)
    dbp = os.path.join(work, "bt_walk.sqlite")
    if os.path.exists(dbp): os.remove(dbp)
    con = store.connect(dbp)
    for d in ex["decisions"]:
        did, _ = depth.record_decision(con, d, recorded_at=t0 + 3700)
        dec = dict(d, id=did)
        depth._snapshot(con, run_id="r1", dec=dec, kind="POOL", provider="geckoterminal", url="u", resp={"t": d["export_time"] + 900, "status": 200, "sha": "x"},
                        state="OK", reserve_usd=1000.0, price_usd=1.0)
    con.commit(); con.execute("PRAGMA wal_checkpoint(TRUNCATE)"); con.execute("PRAGMA journal_mode=DELETE"); con.close()
    print(json.dumps({"collector_log": git("log", "--format=%s %ct", "main", "--", "data/state/latest.json").split("\n"),
                      "collector_decisions": [(d["created_at"], d["export_time"] - t0) for d in ex["decisions"]]}, indent=1))
else:
    from memelab.predictive import sources as SRC, decisions as D, depth_adapter as A
    exps = SRC.export_versions(repo, "main")
    evs = D.decisions(D.candidates(exps))
    con = A.connect_ro(os.path.join(work, "bt_walk.sqlite"))
    print("schema problems:", A.check_schema(con))
    out = []
    for e in evs:
        try:
            r = A.link(con, chain="solana", mint=e["mint"], row_sha256=e["row_sha256"], decision_time=e["decision_time"])
            res = "LINKED" if r else "NO_COLLECTOR_ROW"
        except A.DepthIdentityError as err:
            res = "REFUSED: " + str(err)
        obs = A.observations(con, chain="solana", mint=e["mint"])
        vis = A.visible_at(obs, e["decision_time"])
        out.append({"pred_decision_t_minus_t0": e["decision_time"] - t0, "created_at_minus_t0": e["created_at"] - t0, "link": res,
                    "visible_collector_rows": [(o["captured_at"] - t0) for o in vis]})
    print(json.dumps(out, indent=1))
