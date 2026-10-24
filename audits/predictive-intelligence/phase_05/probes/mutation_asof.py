"""Phase 05 mutation check: every mutation of the new code must make the Phase 05 tests fail.

Each mutation is one exact text replacement in memelab/predictive/{store,features,sources}.py, applied to a copy of memelab/
and tests/ in a temporary folder; the Phase 05 tests run there (`pytest tests/test_predictive_asof_*.py -x -q`). A mutation
whose text is not found is an error (the check would be vacuous). Nothing in the repository is changed.

    python -B mutation_asof.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TESTS = ["tests/test_predictive_asof_store.py", "tests/test_predictive_asof_features.py", "tests/test_predictive_asof_fixture.py"]

# Two protections are layered on purpose, so mutating one layer alone cannot leak: the candle SQL filter and outcomes_core
# .visible (both cut at the cutoff), and in capture mode the candle column and the series gate (checked_at). Those layers are
# mutated together ("both layers"); each is also listed alone under REDUNDANT and reported, not counted.
MUTATIONS = [
    ("features", "view cutoff one second late", "        self.con, self.cutoff, self.mode = con, float(cutoff), mode",
     "        self.con, self.cutoff, self.mode = con, float(cutoff) + 1, mode"),
    ("features", "both layers admit one second later (the audit must still raise)",
     [('f"AND period_s = ? AND {col} <= ?", (chain, mint, pool, PERIOD_S, self.cutoff))',
       'f"AND period_s = ? AND {col} <= ? + 1", (chain, mint, pool, PERIOD_S, self.cutoff))'),
      ("        vis = OC.visible(obs, chain, mint, self.cutoff)", "        vis = OC.visible(obs, chain, mint, self.cutoff + 1)")]),
    ("features", "audit removed", "        return self.audit.check(kind, rows, self.cutoff)", "        return rows"),
    ("features", "revisions ignored: always the first version", "        vis = OC.visible(obs, chain, mint, self.cutoff)",
     "        vis = [min((o for o in obs if o['series_key'] == k), key=lambda o: o['seq']) for k in {o['series_key'] for o in obs}]"),
    ("features", "capture mode sees series read after the cutoff",
     '        if self.mode == "capture":\n            q += " AND checked_at <= ?"', '        if False:\n            q += " AND checked_at <= ?"'),
    ("features", "decision filter admits later decisions",
     '"SELECT * FROM predictive_decisions WHERE chain=? AND mint=? AND decision_time <= ? "',
     '"SELECT * FROM predictive_decisions WHERE chain=? AND mint=? AND decision_time <= ? + 86400 "'),
    ("features", "universe admits later decisions", '"AND decision_time > ? AND decision_time <= ?", (chain, since, self.cutoff))',
     '"AND decision_time > ? AND decision_time <= ? + 1", (chain, since, self.cutoff))'),
    ("features", "missing field becomes a zero", '        return None, "ABSENT_IN_SNAPSHOT"\n    v = snap[key]',
     '        return 0.0, None\n    v = snap[key]'),
    ("features", "feature version not checked",
     '    if feature_version != FEATURE_VERSION:\n        raise FeatureVersionError', '    if False:\n        raise FeatureVersionError'),
    ("features", "both layers: capture mode uses the reconstruction and sees later series",
     [('        col = "available_at" if self.mode == "provider" else "retrieved_at"', '        col = "available_at"'),
      ('        if self.mode == "capture":\n            q += " AND checked_at <= ?"', '        if False:\n            q += " AND checked_at <= ?"')]),
    ("features", "coverage not required up to the decision", "    need_to = T - lag                     #", "    need_to = -1e18                       #"),
    ("features", "drift not refused", "        if old[0] != snap[\"snapshot_sha256\"]:\n            raise SnapshotDriftError",
     "        if False:\n            raise SnapshotDriftError"),
    ("features", "truncated copy keeps every candle",
     'out.execute(f"INSERT INTO main.predictive_candles SELECT * FROM src.predictive_candles WHERE {col} <= ?", (T,))',
     'out.execute(f"INSERT INTO main.predictive_candles SELECT * FROM src.predictive_candles WHERE {col} <= ? + 1e12", (T,))'),
    ("features", "window coverage not checked", "        if cover_from > T - w - PERIOD_S:\n            return None, \"OUTSIDE_FETCHED_WINDOW\"",
     "        if False:\n            return None, \"OUTSIDE_FETCHED_WINDOW\""),
    ("features", "retrieval failures look like quiet markets", '"VENDOR_NO_DATA": RETRIEVAL', '"VENDOR_NO_DATA": AS_OF'),
    ("features", "training view takes later decisions", '        if r["availability_mode"] != mode or r["decision_time"] > as_of:',
     '        if r["availability_mode"] != mode:'),
    ("features", "row validator accepts a later availability", "            if v > d:\n                raise AsOfError",
     "            if v > d + 1:\n                raise AsOfError"),
    ("store", "no provider lag", "            av, basis, rev = end + lag, \"PROVIDER_LAG_RECONSTRUCTION\", None",
     "            av, basis, rev = end, \"PROVIDER_LAG_RECONSTRUCTION\", None"),
    ("store", "boundary candle kept", "        if boundary is not None and start + period > float(boundary):",
     "        if boundary is not None and start > float(boundary):"),
    ("store", "revision available at the first version's time", "            av, basis, rev = ra, \"REVISION_FIRST_READ\", prev[\"obs_key\"]",
     "            av, basis, rev = prev[\"available_at\"], \"REVISION_FIRST_READ\", prev[\"obs_key\"]"),
    ("store", "late appearance treated as old history",
     "        elif _covered_by_earlier_read(con, chain, pool, start, period, ra) is not None:",
     "        elif False:"),
    ("store", "vanished candles ignored", "    if status == 200 and bad_body is None and ident_ok and boundary is not None:",
     "    if False:"),
    ("store", "tracked database allowed", "    if p.resolve() in _forbidden_paths():", "    if False:"),
    ("store", "any base58 length accepted", "        if len(b58decode(addr)) != 32:", "        if len(b58decode(addr)) > 64:"),
    ("store", "vendor identity not checked", "        ident = gt_identity(body, mint, sent)",
     "        ident = \"OK_BASE\""),
    ("store", "partial export history accepted", "    if missing:\n        raise StoreError(f\"{len(missing)} stored export",
     "    if False:\n        raise StoreError(f\"{len(missing)} stored export"),
    ("store", "row existing after its decision accepted", '    if e["decision_time"] < e["created_at"]:\n            raise StoreError',
     '    if False:\n            raise StoreError'),
    ("store", "append-only triggers dropped", '"".join(_append_only(t) for t in DATA_TABLES)', '""'),
    ("store", "rollback keeps the ledger", '        con.execute("DROP TABLE IF EXISTS predictive_schema_migrations")', "        pass"),
    ("store", "millisecond stamps accepted", "EPOCH_S_RANGE = (1.0e9, 1.0e10)", "EPOCH_S_RANGE = (1.0e9, 1.0e16)"),
    ("store", "a pool may serve two mints", "    if any(r[0] != mint for r in owner):", "    if False:"),
    ("sources", "holdout pad removed", "        if boundary > h0 - HOLDOUT_CONTACT_PAD_S:", "        if boundary > h0:"),
    ("sources", "sealed decisions fetched", "    if not development_period(float(dec[\"decision_time\"])):\n        return \"NOT_FETCHED_SEALED\"",
     "    if False:\n        return \"NOT_FETCHED_SEALED\""),
    ("sources", "no token parameter", '            + (f"&token={token}" if token else ""))', "            + \"\")"),
    ("sources", "HTTP errors not counted by the breaker", '                if int(code) != 200:\n                    raise HTTPStatusError',
     '                if False:\n                    raise HTTPStatusError'),
    # repair pass: the independent skeptic's five surviving mutations and the m1 and m2 rules
    ("store", "any token parameter counts as the mint's price",
     '        return "OK_TOKEN_PARAM" if token_param == mint else "OTHER_TOKEN_PARAM"', '        return "OK_TOKEN_PARAM"'),
    ("store", "recorded token trusted over the URL sent",
     [("    if recorded != sent:\n        raise StoreError", "    if False:\n        raise StoreError"),
      ("        ident = gt_identity(body, mint, sent)", "        ident = gt_identity(body, mint, recorded)")]),
    ("store", "short page claims the vendor's whole history", "    cover_complete = 0", "    cover_complete = 1 if len(rows) < limit else 0"),
    ("features", "as-of view mixes candle periods", 'f"AND period_s = ? AND {col} <= ?", (chain, mint, pool, PERIOD_S, self.cutoff))',
     'f"AND ? > 0 AND {col} <= ?", (chain, mint, pool, PERIOD_S, self.cutoff))'),
    ("store", "token row taken from the newest export", '        tk = tok_at.get((e["commit"], e["mint"]))',
     '        tk = next((k for ex2 in reversed(exports) for k in ex2.get("tokens") or [] if k["mint"] == e["mint"]), None)'),
    ("store", "revision compared with the oldest version", "ORDER BY available_at DESC, id DESC LIMIT 1", "ORDER BY available_at ASC, id ASC LIMIT 1"),
    ("store", "a read of another candle period covers a position", "        if url_period(r[\"request_url\"]) in (None, period):",
     "        if True:"),
    ("sources", "check_plan allows a boundary after the pool's last development decision",
     'if p["boundary"] > h0 - HOLDOUT_CONTACT_PAD_S or p["boundary"] > p["last_decision"]:', 'if p["boundary"] > h0 - HOLDOUT_CONTACT_PAD_S:'),
]


REDUNDANT = [
    ("features", "candle SQL filter alone admits one second later",
     'f"AND period_s = ? AND {col} <= ?", (chain, mint, pool, PERIOD_S, self.cutoff))',
     'f"AND period_s = ? AND {col} <= ? + 1", (chain, mint, pool, PERIOD_S, self.cutoff))'),
    ("features", "visible alone ignores the cutoff", "        vis = OC.visible(obs, chain, mint, self.cutoff)",
     "        vis = OC.visible(obs, chain, mint, 1e18)"),
    ("features", "capture candle column alone uses the reconstruction",
     '        col = "available_at" if self.mode == "provider" else "retrieved_at"', '        col = "available_at"'),
]


def run(name: str, path: str, old, new, tmp: Path) -> dict:
    work = tmp / "w"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()
    shutil.copytree(REPO / "memelab", work / "memelab", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(REPO / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    for rel in ("audits/predictive-intelligence/phase_05/data",):
        shutil.copytree(REPO / rel, work / rel)
    (work / "data").mkdir()
    f = work / "memelab" / "predictive" / f"{path}.py"
    src = f.read_text()
    pairs = old if isinstance(old, list) else [(old, new)]
    for o, n in pairs:
        if src.count(o) != 1:
            return {"mutation": name, "file": path, "error": f"text found {src.count(o)} times"}
        src = src.replace(o, n)
    f.write_text(src)
    t0 = time.time()
    p = subprocess.run([sys.executable, "-B", "-m", "pytest", *TESTS, "-x", "-q", "-p", "no:cacheprovider"], cwd=work,
                       capture_output=True, text=True, timeout=900)
    tail = [ln for ln in p.stdout.splitlines() if ln.strip()][-1:] or [""]
    return {"mutation": name, "file": path, "caught": p.returncode != 0, "result": tail[0], "seconds": round(time.time() - t0, 1)}


def main(out: str) -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        base = run("none (control)", "store", "SCHEMA_VERSION = ", "SCHEMA_VERSION = ", tmp)
        res = [run(m[1], m[0], m[2], m[3] if len(m) > 3 else None, tmp) for m in MUTATIONS]
        red = [run(n, path, o, nw, tmp) for path, n, o, nw in REDUNDANT]
    caught = sum(1 for r in res if r.get("caught"))
    rep = {"control_passes": base.get("caught") is False, "control": base, "mutations": len(res), "caught": caught,
           "errors": [r for r in res if "error" in r], "survivors": [r for r in res if r.get("caught") is False], "results": res,
           "redundant_single_layer": red}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("control_passes", "mutations", "caught")} | {"survivors": [r["mutation"] for r in rep["survivors"]],
                                                                                      "errors": [r["mutation"] for r in rep["errors"]],
                                                                                      "redundant_caught": [r.get("caught") for r in red]}))


if __name__ == "__main__":
    main(sys.argv[1])
