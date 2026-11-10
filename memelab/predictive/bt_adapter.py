"""Phase 17: bt-adapter-1, a read-only interface to the backtesting module's per-opportunity assessment (research only, flag OFF,
standard library only; imported only by `memelab/predictive/integration.py`). Maintenance CM-1 (PI-D-120): bt-adapter-2.

The backtesting and stress-testing module came from `origin/feature/backtesting` (pull request #4, tip `69bc5c3`) and was merged
into this line on 2026-11-09 (PI-D-120; it was not here before, PI-D-043, PI-D-047). Its FAST assessment is the record
`memelab/backtest/assess.attach` returns and stores in the table `bt_assessments` (schema migration 1 of `memelab/backtest/schema.py`;
the scout attaches it to each analysis result as `backtest_assessment` when the backtesting policy is on). This module reads those
two shapes and nothing else:
  - from the installed package it uses only `memelab.backtest.store` (the store path: `MEMELAB_BT_DB` or `data/backtest/bt.sqlite`)
    and `memelab.backtest.schema` (the `bt_assessments` DDL text), both imported lazily; it never calls `store.connect`,
    `schema.migrate` or anything that writes, never fetches, and opens a store `mode=ro` with `query_only`;
  - the expected columns are pinned here from the schema text of `69bc5c3` and are also compared with the installed DDL, so a
    changed schema on either side is a refusal (SCHEMA_MISMATCH), not a silent read;
  - identity is chain plus exact mint, byte for byte (P01); an assessment of another identity is refused;
  - an assessment is usable for a decision only when its own `as_of` is at or before the decision time (an assessment made
    later is not evidence the decision could have had);
  - its output goes only into the integration's request record. It is never a forecast input and never a document field: the
    forecast contract refuses an assessment reference while backtesting is not VERIFIED (`contract.backtest_status`, P34; with
    the package installed the status is UNVERIFIED);
  - a fatal-flaw or structurally-untradeable assessment is an extra veto beside the lab's fatal flags; nothing here can clear a
    veto, and a missing assessment is UNTESTED, never read as favourable.
Results: BACKTEST_NOT_AVAILABLE (package not installed), BACKTEST_STORE_MISSING (installed, no store file; the real store lives
only on Elving's computer), UNTESTED (store read, no assessment of this mint at or before the decision), ASSESSMENT_REFUSED,
ASSESSMENT_UNVERIFIED (a usable assessment, shown as context while the engine is not VERIFIED).
"""
from __future__ import annotations

import importlib
import json
import math
import os
import sqlite3
from pathlib import Path
from typing import Any

ADAPTER_VERSION = "bt-adapter-2"                       # PI-D-120: reads the installed package read-only
SCHEMA_SOURCE = "memelab/backtest/schema.py migration 1 (bt_assessments) and memelab/backtest/assess.py attach at 69bc5c3"
EXPECTED_COLUMNS = ("id", "request_key", "chain", "mint", "snapshot_hash", "engine_version", "as_of", "stage", "tier", "state",
                    "result_json", "result_hash", "created_at")
STAGES = ("FAST", "DEEP")
TIERS = ("HISTORICAL_COHORT", "SCENARIO_ONLY", "UNAVAILABLE", "TOKEN_SPECIFIC")
STATES = ("COMPLETE", "PARTIAL_WITH_LIMITATIONS", "INSUFFICIENT_HISTORY", "INSUFFICIENT_EXECUTION_DATA", "UNSUPPORTED_POOL",
          "RISK_FATAL_FLAW", "STALE_DATA", "ERROR", "INVALID_TOKEN_ID", "SOURCE_BLOCKED")
STRESS_DECISIONS = ("RESEARCHABLE", "INCONCLUSIVE", "NO_TRADE", "STRUCTURALLY_UNTRADEABLE", "RISK_FATAL_FLAW",
                    "INSUFFICIENT_EXECUTION_DATA")
VETO_STATES = ("RISK_FATAL_FLAW",)
VETO_DECISIONS = ("RISK_FATAL_FLAW", "STRUCTURALLY_UNTRADEABLE", "NO_TRADE")
VETO_FLAGS = ("BT_STRUCTURALLY_UNTRADEABLE",)
NOT_AVAILABLE = "BACKTEST_NOT_AVAILABLE"
STORE_MISSING = "BACKTEST_STORE_MISSING"
RESULTS = (NOT_AVAILABLE, STORE_MISSING, "UNTESTED", "ASSESSMENT_REFUSED", "ASSESSMENT_UNVERIFIED")
PACKAGE = "memelab.backtest"                                # used read-only: .store (path) and .schema (DDL text)


class BacktestAdapterError(ValueError):
    pass


def _installed() -> tuple[Any, Any] | None:
    """(schema module, store module) of the installed backtesting package, or None. Importing them runs no migration and opens
    no file (both only define constants and functions at import)."""
    try:
        return importlib.import_module(PACKAGE + ".schema"), importlib.import_module(PACKAGE + ".store")
    except ImportError:
        return None


def default_store() -> Path | None:
    """The store the installed package would use (`MEMELAB_BT_DB`, else `memelab.backtest.store.BT_DB_PATH`); None when the package
    is not installed. Only the path: whether it exists is the caller's question."""
    mods = _installed()
    if mods is None:
        return None
    env = os.environ.get("MEMELAB_BT_DB")
    return Path(env) if env else Path(mods[1].BT_DB_PATH)


def installed_columns() -> tuple[str, ...] | None:
    """Columns of `bt_assessments` as the installed `memelab.backtest.schema` defines them, built in an in-memory database from its
    DDL text (nothing on disk is touched); None when the package is not installed, () when it defines no such table."""
    mods = _installed()
    if mods is None:
        return None
    ddl = (getattr(mods[0], "V1_TABLES", None) or {}).get("bt_assessments")
    if not isinstance(ddl, str):
        return ()
    mem = sqlite3.connect(":memory:")
    try:
        mem.executescript(ddl)
        return tuple(r[1] for r in mem.execute("PRAGMA table_info(bt_assessments)"))
    finally:
        mem.close()


def _absent(installed_status: str) -> str:
    return NOT_AVAILABLE if installed_status == NOT_AVAILABLE else STORE_MISSING


def store_state(path: str | Path | None, *, installed_status: str) -> dict:
    """What a pass can say about the store before reading any row: BACKTEST_NOT_AVAILABLE, BACKTEST_STORE_MISSING, SCHEMA_MISMATCH
    or OK. Never raises for a missing or unreadable file; only the file name is reported, never a full path."""
    if installed_status == NOT_AVAILABLE:
        return {"state": NOT_AVAILABLE, "store": None}
    if path is None or not Path(path).exists():
        return {"state": STORE_MISSING, "store": Path(path).name if path is not None else None}
    try:
        con = connect_ro(path)
        try:
            bad = check_schema(con)
        finally:
            con.close()
    except (sqlite3.Error, BacktestAdapterError) as e:
        return {"state": "STORE_UNREADABLE", "store": Path(path).name, "detail": type(e).__name__}
    return {"state": "SCHEMA_MISMATCH" if bad else "OK", "store": Path(path).name}


def _fin(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def check_record(rec: Any, *, chain: str, mint: str, decision_time: float) -> list[str]:
    """Reasons an assessment record cannot be used for this decision (empty: usable as context)."""
    if not isinstance(rec, dict):
        return ["not an assessment record"]
    out = []
    if rec.get("chain") != chain or rec.get("mint") != mint:               # no default chain (PI-D-021, CP17-1)
        out.append("IDENTITY_MISMATCH: the assessment is about another chain or mint (P01)")
    if rec.get("state") not in STATES:
        out.append(f"UNKNOWN_STATE {rec.get('state')!r}")
    if rec.get("tier") is not None and rec.get("tier") not in TIERS:
        out.append(f"UNKNOWN_TIER {rec.get('tier')!r}")
    dec = (rec.get("stress") or {}).get("decision") if isinstance(rec.get("stress"), dict) else None
    if dec is not None and dec not in STRESS_DECISIONS:
        out.append(f"UNKNOWN_STRESS_DECISION {dec!r}")
    if not _fin(rec.get("as_of")):
        out.append("NO_AS_OF: the assessment has no time")
    elif float(rec["as_of"]) > float(decision_time):
        out.append("AFTER_DECISION: the assessment was made after the decision")
    return out


def veto_of(rec: dict | None) -> dict:
    """Extra veto from an assessment: fatal flaw, structurally untradeable or no tradeable size. Never a clearance."""
    if not isinstance(rec, dict):
        return {"veto": None, "reasons": ["UNTESTED"]}
    why = []
    if rec.get("state") in VETO_STATES:
        why.append(f"state {rec['state']}")
    dec = (rec.get("stress") or {}).get("decision") if isinstance(rec.get("stress"), dict) else None
    if dec in VETO_DECISIONS:
        why.append(f"stress {dec}")
    why += [f"flag {f}" for f in rec.get("flags") or [] if f in VETO_FLAGS]
    return {"veto": True if why else None, "reasons": why or ["NO_BACKTEST_VETO"]}


def summarize(rec: dict, *, source: str) -> dict:
    st = rec.get("stress") if isinstance(rec.get("stress"), dict) else {}
    ms = (st.get("max_size") or {}) if isinstance(st.get("max_size"), dict) else {}
    return {"source": source, "request_key": rec.get("request_key"), "state": rec.get("state"), "tier": rec.get("tier"),
            "as_of": rec.get("as_of"), "engine_version": rec.get("engine_version"), "stress_decision": st.get("decision"),
            "max_size_usd_under_caps": ms.get("max_size_usd"), "flags": list(rec.get("flags") or [])}


def from_result(r: dict, *, chain: str, mint: str, decision_time: float, installed_status: str) -> dict:
    """The assessment attached to a scout result by the backtesting branch's hook (`backtest_assessment`), as context."""
    rec = r.get("backtest_assessment") if isinstance(r, dict) else None
    return _context(rec, chain=chain, mint=mint, decision_time=decision_time, installed_status=installed_status, source="RESULT")


def _context(rec: Any, *, chain: str, mint: str, decision_time: float, installed_status: str, source: str) -> dict:
    base = {"adapter_version": ADAPTER_VERSION, "installed_status": installed_status, "verified": installed_status == "VERIFIED"}
    if rec is None:
        res = NOT_AVAILABLE if installed_status == NOT_AVAILABLE else "UNTESTED"
        return base | {"result": res, "assessment": None, "veto": veto_of(None), "refusals": []}
    bad = check_record(rec, chain=chain, mint=mint, decision_time=decision_time)
    if bad:
        return base | {"result": "ASSESSMENT_REFUSED", "assessment": None, "veto": veto_of(None), "refusals": bad}
    return base | {"result": "ASSESSMENT_UNVERIFIED" if installed_status != "VERIFIED" else "ASSESSMENT", "refusals": [],
                   "assessment": summarize(rec, source=source), "veto": veto_of(rec)}


def connect_ro(path: str | Path) -> sqlite3.Connection:
    p = Path(path)
    if not p.exists():
        raise BacktestAdapterError(f"{p.name}: no backtest database")
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    return con


def check_schema(con: sqlite3.Connection) -> list[str]:
    cols = [r[1] for r in con.execute("PRAGMA table_info(bt_assessments)")]
    if not cols:
        return ["bt_assessments: table missing"]
    if tuple(cols) != EXPECTED_COLUMNS:
        return [f"bt_assessments: columns {cols} differ from {list(EXPECTED_COLUMNS)} ({SCHEMA_SOURCE})"]
    inst = installed_columns()
    if inst is not None and inst != EXPECTED_COLUMNS:            # the installed package moved away from the pin (PI-D-120 item 3)
        return [f"bt_assessments: the installed {PACKAGE}.schema defines {list(inst)}, the pin is {list(EXPECTED_COLUMNS)}"]
    return []


def from_table(path: str | Path | None, *, chain: str, mint: str, decision_time: float, installed_status: str) -> dict:
    """Newest FAST assessment of exactly this chain and mint made at or before the decision, from `bt_assessments` (read-only)."""
    base = {"adapter_version": ADAPTER_VERSION, "installed_status": installed_status, "verified": installed_status == "VERIFIED"}
    if path is None or not Path(path).exists():                   # PI-D-120: installed but no store is BACKTEST_STORE_MISSING
        return base | {"result": _absent(installed_status), "assessment": None, "veto": veto_of(None),
                       "refusals": [] if path is None else ["no backtest database"]}
    con = connect_ro(path)
    try:
        bad = check_schema(con)
        if bad:
            return base | {"result": "ASSESSMENT_REFUSED", "assessment": None, "veto": veto_of(None), "refusals": ["SCHEMA_MISMATCH"] + bad}
        rows = con.execute("SELECT * FROM bt_assessments WHERE chain=? AND mint=? AND stage='FAST' AND as_of <= ? "
                           "ORDER BY as_of DESC, id DESC LIMIT 1", (chain, mint, float(decision_time))).fetchall()
    finally:
        con.close()
    if not rows:
        return base | {"result": "UNTESTED", "assessment": None, "veto": veto_of(None), "refusals": []}
    row = dict(rows[0])
    if row["chain"] != chain or row["mint"] != mint:              # SQLite compares TEXT byte for byte; kept as a second check
        raise BacktestAdapterError("a row of another identity came back")
    try:
        rec = json.loads(row["result_json"])
    except (TypeError, ValueError):
        return base | {"result": "ASSESSMENT_REFUSED", "assessment": None, "veto": veto_of(None), "refusals": ["result_json is not JSON"]}
    if rec.get("state") != row["state"] or rec.get("request_key") != row["request_key"]:
        return base | {"result": "ASSESSMENT_REFUSED", "assessment": None, "veto": veto_of(None),
                       "refusals": ["result_json disagrees with its row (state or request key)"]}
    return _context(rec, chain=chain, mint=mint, decision_time=decision_time, installed_status=installed_status, source="TABLE")
