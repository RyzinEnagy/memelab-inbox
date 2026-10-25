"""Phase 05: the point-in-time evidence store (research only, flag OFF, imported by no existing module).

A private SQLite file holds `predictive_*` tables, applied as numbered migrations with a checksum ledger, the pattern of
memelab/social/schema.py. It never goes into the tracked lab database (`connect` refuses it) and `db.init_db` does not know it.
Default path data/private/predictive_store.sqlite (gitignored), override MEMELAB_PREDICTIVE_STORE.

What is stored (contract: audits/predictive-intelligence/phase_05/data/FEATURE_STORE_CONTRACT.md):
  predictive_raw_responses   every external read: request, retrieval time, HTTP status, sha256 of the body, the body (gzip)
                             for vendor reads; a state-export version is a read of a git blob (body stays in git)
  predictive_candles         one row per distinct candle version; an identical re-read is a row in predictive_candle_reads,
                             a changed, newly appearing or vanished candle is a new version available from the read that
                             showed it (a revision never rewrites history, P07)
  predictive_source_status   what a fetch series covered and how it ended (OK, NO_DATA, READ_FAILED, CIRCUIT_OPEN, ...):
                             dead or unquoted pools stay visible (P09), outages are visible (P47)
  predictive_decisions       decision events of memelab/predictive/decisions.py (identity (mint, created_at, row_sha256),
                             time = first export commit holding the exact row, PI-D-015, PI-D-021), with the export commit,
                             blob, the token row's write-time trace and the store's own write time (PI-D-011 rule 3)
  predictive_feature_sets, predictive_snapshots, predictive_feature_values
                             immutable feature snapshots written by memelab/predictive/features.py

Every data table is append-only: triggers refuse UPDATE and DELETE. Ingestion is idempotent through deterministic keys with
UNIQUE constraints. Identity is chain plus the exact address (TEXT compared byte for byte); a Solana mint or pool must be
base58 that decodes to 32 bytes (PI-D-022); no symbol or name column exists, so none can take part in a join (P01).
Two clocks are kept apart (DATA_TIME_CONTRACT): `retrieved_at` is when the lab received bytes; `available_at` is the
conservative moment inference may use a row, with its basis. A backfill read is never a claim of historical availability:
a vendor candle's first version is available at its end plus the provider lag (replay_sources.PROVIDER_LAG, a labelled
HEURISTIC reconstruction), or at the read if that is earlier (CAPTURE); a later revision only from the read that showed it.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable

from . import contract as C
from . import decisions as D

SCHEMA_VERSION = "memelab.predictive.store/1"
INGEST_GT = "geckoterminal-ohlcv/1"
INGEST_EXPORT = "state-export/1"
SOURCE_GT = "geckoterminal-ohlcv"
SOURCE_EXPORT = "state-export"
AVAILABLE_BASES = ("PROVIDER_LAG_RECONSTRUCTION", "CAPTURE", "REVISION_FIRST_READ")
SERIES_STATUSES = ("OK", "NO_DATA", "READ_FAILED", "CIRCUIT_OPEN", "CALL_CAP_REACHED", "BAD_BODY", "IDENTITY_MISMATCH")
IDENTITY_CHECKS = ("OK_BASE", "OK_TOKEN_PARAM", "MINT_IS_QUOTE", "MINT_NOT_IN_POOL", "OTHER_TOKEN_PARAM", "NO_META",
                   "TOKEN_PARAM_NOT_BASE")
GT_PERIOD = {("minute", 1): 60, ("minute", 5): 300, ("minute", 15): 900, ("hour", 1): 3600, ("hour", 4): 14400,
             ("hour", 12): 43200, ("day", 1): 86400}


KNOWN_CHAINS = ("solana",) + tuple(C.EVM_CHAINS)


class StoreError(ValueError):
    pass


def _provider_lag() -> float:
    from ..social.replay_sources import PROVIDER_LAG
    return float(PROVIDER_LAG["geckoterminal-ohlcv"])


# ---------------------------------------------------------------- identity (P01, PI-D-022)
_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_INDEX = {ch: i for i, ch in enumerate(_B58_ALPHABET)}
_EVM = re.compile(r"0x[0-9a-fA-F]{40}")
_EVM_POOL_ID = re.compile(r"0x[0-9a-fA-F]{64}")        # a Uniswap v4 pool is a bytes32 id, not a contract address


def b58decode(s: str) -> bytes:
    if not isinstance(s, str) or not s:
        raise StoreError("not a base58 string")
    n = 0
    for ch in s:
        if ch not in _B58_INDEX:
            raise StoreError(f"{s!r} is not base58")
        n = n * 58 + _B58_INDEX[ch]
    body = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = len(s) - len(s.lstrip("1"))
    return b"\x00" * pad + body


def check_address(chain: Any, addr: Any, what: str = "mint") -> str:
    """The exact address or StoreError. Solana: base58 decoding to 32 bytes. EVM: 0x plus 40 hex. Nothing is normalized:
    two strings that differ in one character or in letter case are two identities."""
    if not isinstance(addr, str) or addr != addr.strip() or not addr:
        raise StoreError(f"{what} {addr!r} is not an exact address")
    if chain == "solana":
        if len(b58decode(addr)) != 32:
            raise StoreError(f"{what} {addr!r} does not decode to 32 bytes: not a Solana address (PI-D-022)")
        return addr
    if chain in C.EVM_CHAINS:
        if not (_EVM.fullmatch(addr) or (what == "pool" and _EVM_POOL_ID.fullmatch(addr))):
            raise StoreError(f"{what} {addr!r} is not an EVM address" + (" or pool id" if what == "pool" else ""))
        return addr
    raise StoreError(f"unknown chain {chain!r}: identity is chain plus exact address")


# ---------------------------------------------------------------- schema
LEDGER = """
CREATE TABLE IF NOT EXISTS predictive_schema_migrations (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  checksum TEXT NOT NULL,                 -- sha256 of the up script; a changed script on an applied version is refused
  applied_at REAL NOT NULL
);
"""

DATA_TABLES = ("predictive_raw_responses", "predictive_candles", "predictive_candle_reads", "predictive_source_status",
               "predictive_decisions", "predictive_feature_sets", "predictive_snapshots", "predictive_feature_values")


def _append_only(table: str) -> str:
    return (f"CREATE TRIGGER {table}_no_update BEFORE UPDATE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{table} is append-only: rows are never updated'); END;\n"
            f"CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{table} is append-only: rows are never deleted'); END;\n")


V1_UP = """
CREATE TABLE predictive_raw_responses (     -- one row per external read; the same read ingested twice is one row
  id INTEGER PRIMARY KEY,
  response_key TEXT NOT NULL UNIQUE,        -- sha256 of (source_id, request_url, retrieved_at, body_sha256)
  source_id TEXT NOT NULL,                  -- geckoterminal-ohlcv | state-export
  request_url TEXT NOT NULL,                -- vendor URL, or git:<path>@<commit> for an export version
  request_json TEXT NOT NULL,               -- parameters (pool, timeframe, before_timestamp, page; or ref, commit, blob)
  chain TEXT COLLATE BINARY, mint TEXT COLLATE BINARY, pool_address TEXT COLLATE BINARY,
  boundary_at REAL,                         -- request boundary (before_timestamp); candles ending after it are dropped
  retrieved_at REAL NOT NULL,               -- when the lab received the bytes (never a historical availability claim)
  http_status INTEGER NOT NULL,
  body_sha256 TEXT NOT NULL,
  body_bytes INTEGER NOT NULL,
  body_gzip BLOB,                           -- vendor body, gzip with mtime 0; NULL for a git blob (it stays in git)
  cover_from REAL,                          -- earliest candle start in the body (NULL: no candle)
  cover_complete INTEGER,                   -- always 0 for vendor reads: a short or empty page is NOT proof of no earlier trade
  candles_in_body INTEGER, candles_dropped_after_boundary INTEGER, candles_refused INTEGER,
  identity_check TEXT,                      -- OK_BASE | OK_TOKEN_PARAM | MINT_IS_QUOTE | MINT_NOT_IN_POOL | OTHER_TOKEN_PARAM | NO_META
  collector TEXT NOT NULL, ingest_version TEXT NOT NULL, schema_version TEXT NOT NULL,
  recorded_at REAL NOT NULL
);
CREATE INDEX ix_prr_pool ON predictive_raw_responses(chain, pool_address, retrieved_at);

CREATE TABLE predictive_candles (           -- one row per distinct version of one candle position
  id INTEGER PRIMARY KEY,
  obs_key TEXT NOT NULL UNIQUE,             -- sha256 of (series_key, values, vanished, revision_of): identical re-reads collapse
  series_key TEXT NOT NULL,                 -- sha256 of (source_id, chain, pool, period, start): one candle position
  source_id TEXT NOT NULL,
  source_record_id TEXT NOT NULL,           -- <pool>:<period_s>:<start>
  chain TEXT NOT NULL COLLATE BINARY, mint TEXT NOT NULL COLLATE BINARY, pool_address TEXT NOT NULL COLLATE BINARY,
  period_s INTEGER NOT NULL, start_at REAL NOT NULL, end_at REAL NOT NULL,
  o REAL, h REAL, l REAL, c REAL, v REAL,
  vanished INTEGER NOT NULL DEFAULT 0,      -- 1: a later read covering this position no longer served it
  event_time REAL NOT NULL,                 -- provider candle start
  published_at REAL,                        -- provider publication time: UNKNOWN for GeckoTerminal (NULL)
  retrieved_at REAL NOT NULL,               -- first read that returned this exact version
  available_at REAL NOT NULL,
  available_basis TEXT NOT NULL CHECK (available_basis IN ('PROVIDER_LAG_RECONSTRUCTION','CAPTURE','REVISION_FIRST_READ')),
  revision_of TEXT,                         -- obs_key of the version this one follows (NULL for the first version)
  revision_kind TEXT CHECK (revision_kind IS NULL OR revision_kind IN ('OPEN_WINDOW','VALUES','APPEARED','VANISHED')),
  response_key TEXT NOT NULL REFERENCES predictive_raw_responses(response_key),
  raw_sha256 TEXT NOT NULL,
  ingest_version TEXT NOT NULL, schema_version TEXT NOT NULL, recorded_at REAL NOT NULL,
  CHECK (end_at = start_at + period_s),
  CHECK (available_at >= end_at OR available_basis = 'CAPTURE'),
  CHECK (available_basis <> 'REVISION_FIRST_READ' OR revision_of IS NOT NULL OR available_at = retrieved_at)
);
CREATE INDEX ix_pc_pool_av ON predictive_candles(chain, pool_address, available_at);
CREATE INDEX ix_pc_series ON predictive_candles(series_key, id);

CREATE TABLE predictive_candle_reads (      -- every read that returned an existing candle version unchanged
  id INTEGER PRIMARY KEY,
  read_key TEXT NOT NULL UNIQUE,            -- sha256 of (obs_key, response_key)
  obs_key TEXT NOT NULL REFERENCES predictive_candles(obs_key),
  response_key TEXT NOT NULL REFERENCES predictive_raw_responses(response_key),
  retrieved_at REAL NOT NULL,
  recorded_at REAL NOT NULL
);

CREATE TABLE predictive_source_status (     -- how one fetch series of one pool ended; retrieval metadata, never a feature
  id INTEGER PRIMARY KEY,
  status_key TEXT NOT NULL UNIQUE,
  source_id TEXT NOT NULL,
  chain TEXT NOT NULL COLLATE BINARY, mint TEXT NOT NULL COLLATE BINARY, pool_address TEXT NOT NULL COLLATE BINARY,
  series_id TEXT NOT NULL,                  -- the planned series (pool, boundary)
  boundary_at REAL NOT NULL, need_from REAL NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('OK','NO_DATA','READ_FAILED','CIRCUIT_OPEN','CALL_CAP_REACHED','BAD_BODY',
                                         'IDENTITY_MISMATCH')),
  period_s INTEGER NOT NULL,                -- candle period of the series (features read 300 s series only)
  detail TEXT,
  cover_from REAL,                          -- earliest candle start read in the series (NULL: none)
  cover_complete INTEGER NOT NULL,          -- always 0 (repair m2): coverage starts at cover_from, nothing is assumed before it
  last_end_at REAL,                         -- end of the newest candle kept
  calls INTEGER NOT NULL, candles_kept INTEGER NOT NULL,
  response_keys_json TEXT NOT NULL,
  checked_at REAL NOT NULL,                 -- retrieval time of the last call in the series
  recorded_at REAL NOT NULL
);
CREATE INDEX ix_pss_pool ON predictive_source_status(chain, pool_address, checked_at);

CREATE TABLE predictive_decisions (         -- decision events of decisions.py (PI-D-015, PI-D-021)
  id INTEGER PRIMARY KEY,
  decision_key TEXT NOT NULL UNIQUE,        -- sha256 of (chain, mint, created_at, row_sha256, decision_time)
  chain TEXT COLLATE BINARY,                -- NULL when the export has no token row (never a default)
  mint TEXT NOT NULL COLLATE BINARY,
  pool_address TEXT COLLATE BINARY,         -- point-in-time pool: primary_pool or graduated_pool of that export's token row
  row_sha256 TEXT NOT NULL,
  created_at REAL NOT NULL,                 -- data only: the collector-run start, never a time for availability (PI-D-011)
  decision_time REAL NOT NULL,
  decision_time_basis TEXT NOT NULL CHECK (decision_time_basis IN ('EXPORT_COMMIT','CAPTURE_TIME')),
  export_commit TEXT, export_blob TEXT,
  row_first_visible REAL NOT NULL,
  token_first_seen_at REAL,                 -- write-time trace of the token row in that export (db.now() at first persist)
  status TEXT, flags_json TEXT NOT NULL, rows_sharing_key INTEGER NOT NULL,
  row_json TEXT NOT NULL,                   -- the exact decision row without id
  token_json TEXT,                          -- the token row of that export
  response_key TEXT NOT NULL REFERENCES predictive_raw_responses(response_key),
  ingest_version TEXT NOT NULL, schema_version TEXT NOT NULL,
  recorded_at REAL NOT NULL,                -- when this store wrote the record
  CHECK (decision_time >= row_first_visible),
  CHECK (decision_time >= created_at)
);
CREATE INDEX ix_pd_mint ON predictive_decisions(chain, mint, decision_time);
CREATE INDEX ix_pd_time ON predictive_decisions(decision_time);

CREATE TABLE predictive_feature_sets (
  feature_set_sha TEXT PRIMARY KEY,
  feature_version TEXT NOT NULL,
  definitions_json TEXT NOT NULL,
  recorded_at REAL NOT NULL
);

CREATE TABLE predictive_snapshots (         -- one immutable feature snapshot per (decision or query time, version, mode)
  id INTEGER PRIMARY KEY,
  snapshot_key TEXT NOT NULL UNIQUE,
  decision_key TEXT,                        -- the decision record the snapshot reads (NULL: none visible at the cutoff)
  chain TEXT NOT NULL COLLATE BINARY, mint TEXT NOT NULL COLLATE BINARY, pool_address TEXT COLLATE BINARY,
  decision_time REAL NOT NULL, cutoff_at REAL NOT NULL,
  feature_version TEXT NOT NULL, feature_set_sha TEXT NOT NULL REFERENCES predictive_feature_sets(feature_set_sha),
  availability_mode TEXT NOT NULL CHECK (availability_mode IN ('provider','capture')),
  data_version TEXT NOT NULL,               -- sha256 of every input row key the snapshot read
  source_status_json TEXT NOT NULL,
  max_input_available_at REAL,
  snapshot_sha256 TEXT NOT NULL,
  recorded_at REAL NOT NULL,
  CHECK (cutoff_at = decision_time),
  CHECK (max_input_available_at IS NULL OR max_input_available_at <= cutoff_at)
);

CREATE TABLE predictive_feature_values (
  id INTEGER PRIMARY KEY,
  value_key TEXT NOT NULL UNIQUE,           -- sha256 of (snapshot_key, feature_name)
  snapshot_key TEXT NOT NULL REFERENCES predictive_snapshots(snapshot_key),
  chain TEXT NOT NULL COLLATE BINARY, mint TEXT NOT NULL COLLATE BINARY, pool_address TEXT COLLATE BINARY,
  decision_time REAL NOT NULL, cutoff_at REAL NOT NULL,
  feature_name TEXT NOT NULL, feature_version TEXT NOT NULL,
  value REAL,
  missing_reason TEXT,
  missing_basis TEXT CHECK (missing_basis IS NULL OR missing_basis IN ('AS_OF','HEURISTIC','RETRIEVAL')),
  feature_available_at REAL,                -- latest availability among the inputs actually used
  available_basis TEXT,
  evidence TEXT NOT NULL CHECK (evidence IN ('FACT','HEURISTIC','INFERENCE','UNKNOWN')),
  source_ids_json TEXT NOT NULL, raw_hashes_json TEXT NOT NULL, source_record_count INTEGER NOT NULL,
  retrieved_at REAL,                        -- latest retrieval among the inputs
  source_fingerprint TEXT NOT NULL,         -- sha256 of the input row keys
  recorded_at REAL NOT NULL,
  CHECK ((value IS NULL) <> (missing_reason IS NULL)),
  CHECK ((missing_reason IS NULL) = (missing_basis IS NULL)),
  CHECK (feature_available_at IS NULL OR feature_available_at <= cutoff_at),
  UNIQUE (snapshot_key, feature_name)
);
""" + "".join(_append_only(t) for t in DATA_TABLES)

V1_DOWN = "".join(f"DROP TABLE IF EXISTS {t};\n" for t in reversed(DATA_TABLES))

MIGRATIONS = [(1, "point-in-time evidence and feature store", V1_UP, V1_DOWN)]


def _checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode()).hexdigest()


def _run(con: sqlite3.Connection, script: str) -> None:
    try:
        con.executescript("BEGIN;\n" + script + "\nCOMMIT;")
    except Exception:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise


def current_version(con: sqlite3.Connection) -> int:
    con.executescript(LEDGER)
    row = con.execute("SELECT MAX(version) FROM predictive_schema_migrations").fetchone()
    return int(row[0] or 0)


def migrate(con: sqlite3.Connection, target: int | None = None, migrations=None) -> list[int]:
    """Apply pending migrations up to target (default latest), one transaction each. Additive: creates predictive_* tables only."""
    migrations = migrations if migrations is not None else MIGRATIONS
    con.executescript(LEDGER)
    applied = {r[0]: r[1] for r in con.execute("SELECT version, checksum FROM predictive_schema_migrations")}
    for v, _n, up, _d in migrations:
        if v in applied and applied[v] != _checksum(up):
            raise StoreError(f"predictive migration {v} changed after it was applied; add a new migration instead")
    done = []
    for v, name, up, _d in sorted(migrations):
        if v in applied or (target is not None and v > target):
            continue
        ledger = (f"INSERT INTO predictive_schema_migrations(version,name,checksum,applied_at) "
                  f"VALUES ({int(v)}, '{name.replace(chr(39), '')}', '{_checksum(up)}', {time.time()!r});")
        _run(con, up + "\n" + ledger)
        done.append(v)
    return done


def rollback(con: sqlite3.Connection, target: int = 0, migrations=None) -> list[int]:
    """Undo applied migrations above target, newest first. Drops predictive_* tables only (their rows go with them: take
    a backup first with memelab.social.schema.backup_db). Legacy, social, catalyst, chains and launch tables are untouched."""
    migrations = migrations if migrations is not None else MIGRATIONS
    con.executescript(LEDGER)
    applied = sorted((r[0] for r in con.execute("SELECT version FROM predictive_schema_migrations")), reverse=True)
    by_v = {m[0]: m for m in migrations}
    undone = []
    for v in applied:
        if v <= target:
            break
        if v not in by_v:
            raise StoreError(f"no down script for applied predictive migration {v}")
        _run(con, by_v[v][3] + f"\nDELETE FROM predictive_schema_migrations WHERE version={int(v)};")
        undone.append(v)
    if target == 0:                      # back to the exact schema the database had before migrate
        con.execute("DROP TABLE IF EXISTS predictive_schema_migrations")
    return undone


def default_path() -> Path:
    env = os.environ.get("MEMELAB_PREDICTIVE_STORE")
    if env:
        return Path(env)
    from .. import db
    return Path(db.DATA_DIR) / "private" / "predictive_store.sqlite"


def _forbidden_paths() -> set[Path]:
    from .. import db
    return {Path(db.DB_PATH).resolve(), (Path(db.DATA_DIR) / "memelab.sqlite").resolve()}


def connect(path: str | Path | None = None, *, migrate_schema: bool = True) -> sqlite3.Connection:
    """Open the private store. Refuses the tracked lab database (and MEMELAB_DB): the store never goes there."""
    p = Path(path) if path else default_path()
    if p.resolve() in _forbidden_paths():
        raise StoreError("the predictive store never goes into the lab database (data/memelab.sqlite or MEMELAB_DB)")
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    if migrate_schema:
        migrate(con)
    return con


# ---------------------------------------------------------------- helpers
def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def sha(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def _num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


EPOCH_S_RANGE = (1.0e9, 1.0e10)          # 2001 to 2286 in seconds; a millisecond or microsecond stamp falls outside


def epoch_seconds(x: Any, what: str) -> float:
    """Every *_at in the store is UTC epoch seconds. A value in milliseconds, a string or a non-finite number is refused."""
    if not _num(x) or not (EPOCH_S_RANGE[0] <= float(x) < EPOCH_S_RANGE[1]):
        raise StoreError(f"{what} {x!r} is not UTC epoch seconds (unit check: milliseconds and strings are refused)")
    return float(x)


def _insert(con: sqlite3.Connection, table: str, row: dict) -> bool:
    """INSERT OR IGNORE on the table's unique key; True when a row was added."""
    cols = list(row)
    cur = con.execute(f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                      [row[c] for c in cols])
    return cur.rowcount == 1


def gz(b: bytes) -> bytes:
    return gzip.compress(b, compresslevel=9, mtime=0)


# ---------------------------------------------------------------- state exports and decision records
def ingest_exports(con: sqlite3.Connection, exports: list[dict], *, now: float, ref: str | None = None,
                   collector: str = "git first-parent reader") -> dict:
    """Store one raw read per export version and every decision event of decisions.py. Idempotent.

    exports: the complete history, oldest first, each {"commit", "commit_time", "theses", "tokens"} plus optional "blob",
    "body_sha256", "body_bytes", "path" (memelab.predictive.sources.export_versions gives them). Decision events depend on every
    earlier version (decisions.py), so a call must include every version already stored: a partial history would turn a
    re-exported old row into a new decision. Adding later versions only adds later decisions (rows never leave the visible set)."""
    known = {json.loads(r["request_json"])["commit"] for r in
             con.execute("SELECT request_json FROM predictive_raw_responses WHERE source_id=?", (SOURCE_EXPORT,))}
    missing = known - {ex["commit"] for ex in exports}
    if missing:
        raise StoreError(f"{len(missing)} stored export versions are not in this call: give the full history, oldest first")
    rk_of: dict[str, str] = {}
    added_resp = 0
    for ex in exports:
        path = ex.get("path", "data/state/latest.json")
        url = f"git:{path}@{ex['commit']}"
        bsha = ex.get("body_sha256") or sha({"theses": ex["theses"], "tokens": ex["tokens"]})
        rk = sha([SOURCE_EXPORT, url, ex["commit"], bsha])     # retrieval of a commit is the commit itself: re-reads collapse
        rk_of[ex["commit"]] = rk
        added_resp += _insert(con, "predictive_raw_responses", {
            "response_key": rk, "source_id": SOURCE_EXPORT, "request_url": url,
            "request_json": canon({"ref": ref, "commit": ex["commit"], "blob": ex.get("blob"), "path": path,
                                   "commit_time": ex["commit_time"]}),
            "chain": None, "mint": None, "pool_address": None, "boundary_at": None, "retrieved_at": float(now),
            "http_status": 200, "body_sha256": bsha, "body_bytes": int(ex.get("body_bytes") or 0), "body_gzip": None,
            "cover_from": None, "cover_complete": None, "candles_in_body": None, "candles_dropped_after_boundary": None,
            "candles_refused": None, "identity_check": None, "collector": collector, "ingest_version": INGEST_EXPORT,
            "schema_version": SCHEMA_VERSION, "recorded_at": float(now)})
    tok_at = {(ex["commit"], k["mint"]): k for ex in exports for k in ex.get("tokens") or []}
    blob_of = {ex["commit"]: ex.get("blob") for ex in exports}
    cands = D.candidates(exports)
    row_of = {(c["mint"], c["created_at"], c["row_sha256"]): c["row"] for c in cands}
    evs = D.decisions(cands)
    added, refused = 0, []
    for e in evs:
        epoch_seconds(e["decision_time"], "decision_time")
        epoch_seconds(e["created_at"], "created_at")
        if e["decision_time_basis"] not in C.DECISION_TIME_BASES:
            raise StoreError(f"decision time basis {e['decision_time_basis']!r} is not allowed (PI-D-011)")
        if e["decision_time"] < e["created_at"]:
            raise StoreError("decision time before the row's created_at: the row cannot have existed (PI-D-011)")
        tk = tok_at.get((e["commit"], e["mint"]))
        if e["chain"] in KNOWN_CHAINS:
            try:
                check_address(e["chain"], e["mint"])
                if e["pool_pit"]:
                    check_address(e["chain"], e["pool_pit"], "pool")
            except StoreError as err:            # a malformed identity never enters the store; it is counted
                refused.append({"mint": e["mint"], "decision_time": e["decision_time"], "reason": str(err)})
                continue
        row = row_of[(e["mint"], e["created_at"], e["row_sha256"])]
        body = {k: v for k, v in row.items() if k not in D.ROW_EXCLUDE}
        fs = tk.get("first_seen_at") if tk else None
        added += _insert(con, "predictive_decisions", {
            "decision_key": decision_key(e), "chain": e["chain"], "mint": e["mint"], "pool_address": e["pool_pit"],
            "row_sha256": e["row_sha256"], "created_at": float(e["created_at"]), "decision_time": float(e["decision_time"]),
            "decision_time_basis": e["decision_time_basis"], "export_commit": e["commit"], "export_blob": blob_of.get(e["commit"]),
            "row_first_visible": float(e["row_first_visible"]), "token_first_seen_at": float(fs) if _num(fs) else None,
            "status": e["status"], "flags_json": canon(e["flags"]), "rows_sharing_key": int(e["rows_sharing_key"]),
            "row_json": canon(body), "token_json": canon(tk) if tk else None, "response_key": rk_of[e["commit"]],
            "ingest_version": INGEST_EXPORT, "schema_version": SCHEMA_VERSION, "recorded_at": float(now)})
    return {"exports": len(exports), "responses_added": added_resp, "decision_events": len(evs), "decisions_added": added,
            "refused": refused}


def decision_key(e: dict) -> str:
    return sha([e["chain"], e["mint"], float(e["created_at"]), e["row_sha256"], float(e["decision_time"])])


def snapshot_ref_ok(con: sqlite3.Connection, chain: str, mint: str, snapshot_hash: str) -> bool:
    """PI-D-022: a forecast's snapshot_hash must be the row_sha256 of a decision record of that exact (chain, mint)."""
    h = snapshot_hash[7:] if isinstance(snapshot_hash, str) and snapshot_hash.startswith("sha256:") else snapshot_hash
    return con.execute("SELECT 1 FROM predictive_decisions WHERE chain=? AND mint=? AND row_sha256=? LIMIT 1",
                       (chain, mint, h)).fetchone() is not None


# ---------------------------------------------------------------- vendor candles
def parse_gt_ohlcv(body: bytes) -> list[list]:
    d = json.loads(body)
    lst = (((d or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list")
    if not isinstance(lst, list):
        raise StoreError("body has no data.attributes.ohlcv_list")
    return lst


def gt_identity(body: bytes, mint: str, token_param: str | None) -> str:
    """Whose price the candles are. GeckoTerminal prices the pool's base token unless `token=<address>` asks for another, so a
    read without that parameter is the mint's price only when the mint is the base token (Phase 05 finding: one pool of the
    real sample has the mint as quote, and its default candles price the other token)."""
    try:
        meta = (json.loads(body) or {}).get("meta") or {}
    except ValueError:
        return "NO_META"
    base, quote = (meta.get("base") or {}).get("address"), (meta.get("quote") or {}).get("address")
    if base is None and quote is None:
        return "NO_META"
    if mint not in (base, quote):
        return "MINT_NOT_IN_POOL"
    if token_param is not None:                       # only the exact mint address counts; "base", "quote" or another address do not
        if token_param != mint:
            return "OTHER_TOKEN_PARAM"
        # With token=<mint> GeckoTerminal re-orients the body: meta.base is the mint (all 216 real reads of Phases 05 and 06,
        # quote-side pools included). A body that still shows the other token as base may price the other token (a vendor
        # change or a proxy that drops the parameter): refused (Phase 06 skeptic counterexample CX-S06, PI-D-045).
        return "OK_TOKEN_PARAM" if base == mint else "TOKEN_PARAM_NOT_BASE"
    return "OK_BASE" if base == mint else "MINT_IS_QUOTE"


def url_token(url: str) -> str | None:
    """The `token` query parameter of the URL actually requested (None when absent)."""
    from urllib.parse import parse_qs, urlsplit
    vals = parse_qs(urlsplit(url).query).get("token")
    if vals and len(vals) > 1:
        raise StoreError("a request URL with two token parameters is ambiguous")
    return vals[0] if vals else None


def _series_key(source_id: str, chain: str, pool: str, period: int, start: float) -> str:
    return sha([source_id, chain, pool, int(period), float(start)])


def _latest_version(con: sqlite3.Connection, series_key: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM predictive_candles WHERE series_key=? ORDER BY available_at DESC, id DESC LIMIT 1",
                       (series_key,)).fetchone()


def url_period(url: str) -> int | None:
    """Candle period of a GeckoTerminal OHLCV request URL (`.../ohlcv/<timeframe>?aggregate=<n>`), None when not parseable."""
    from urllib.parse import parse_qs, urlsplit
    u = urlsplit(url)
    tf = u.path.rstrip("/").rsplit("/", 1)[-1] if "/ohlcv/" in u.path else None
    agg = (parse_qs(u.query).get("aggregate") or ["1"])[0]
    try:
        return GT_PERIOD.get((tf, int(agg)))
    except ValueError:
        return None


def _covered_by_earlier_read(con: sqlite3.Connection, chain: str, pool: str, start: float, period: int,
                             before_retrieved: float) -> sqlite3.Row | None:
    """An earlier read of the same pool and the same candle period whose window [cover_from, boundary] included this position.
    A read of another period never covers it; a read whose period cannot be parsed is treated as covering (conservative: a
    candle then counts only from its own read)."""
    for r in con.execute(
            "SELECT * FROM predictive_raw_responses WHERE source_id=? AND chain=? AND pool_address=? AND http_status=200 "
            "AND identity_check LIKE 'OK%' AND retrieved_at < ? AND boundary_at IS NOT NULL AND ? + ? <= boundary_at "
            "AND (cover_complete = 1 OR (cover_from IS NOT NULL AND cover_from <= ?)) ORDER BY retrieved_at",
            (SOURCE_GT, chain, pool, before_retrieved, start, period, start)):
        if url_period(r["request_url"]) in (None, period):
            return r
    return None


def ingest_gt_response(con: sqlite3.Connection, resp: dict, *, chain: str, mint: str, pool: str, now: float,
                       limit: int = 1000, provider_lag_s: float | None = None) -> dict:
    """Store one GeckoTerminal OHLCV read and its candles. resp: {"url", "params", "retrieved_at", "http_status", "body"
    (bytes), "boundary_at", "timeframe", "aggregate", "collector"}. Idempotent: the same read twice adds nothing.

    Rules: candles ending after the request boundary are dropped and counted (GeckoTerminal's before_timestamp is inclusive and
    returns the candle that contains an unaligned boundary, PI-D-034); each candle passes outcomes_core.normalize_observation
    (high and low contain open and close; a candle that closes after the read is refused); a position read for the first time
    is available at end + provider lag (HEURISTIC) or at the read if earlier (CAPTURE), unless an earlier read covered the
    position without it (then it appeared later: REVISION_FIRST_READ at this read); a changed version is available from this
    read (REVISION_FIRST_READ); an unchanged one adds a read record only. Reads of one pool are ingested in retrieval order."""
    from ..social import outcomes_core as OC
    check_address(chain, mint)
    check_address(chain, pool, "pool")
    owner = con.execute("SELECT DISTINCT mint FROM predictive_raw_responses WHERE source_id=? AND chain=? AND pool_address=?",
                        (SOURCE_GT, chain, pool)).fetchall()
    if any(r[0] != mint for r in owner):
        raise StoreError(f"pool {pool} already belongs to another mint: a pool has exactly one mint (P01, P02)")
    lag = _provider_lag() if provider_lag_s is None else float(provider_lag_s)
    tf, agg = resp.get("timeframe", "minute"), int(resp.get("aggregate", 5))
    period = GT_PERIOD.get((tf, agg))
    if period is None:
        raise StoreError(f"unknown timeframe {tf}/{agg}")
    ra = epoch_seconds(resp["retrieved_at"], "retrieved_at")
    last = con.execute("SELECT MAX(retrieved_at) FROM predictive_raw_responses WHERE source_id=? AND chain=? AND pool_address=?",
                       (SOURCE_GT, chain, pool)).fetchone()[0]
    body: bytes = resp.get("body") or b""
    bsha = hashlib.sha256(body).hexdigest()
    rk = sha([SOURCE_GT, resp["url"], ra, bsha])
    if con.execute("SELECT 1 FROM predictive_raw_responses WHERE response_key=?", (rk,)).fetchone():
        return {"response_key": rk, "duplicate_read": True, "added": 0, "revisions": 0, "reads": 0, "dropped": 0, "refused": 0}
    if last is not None and ra < last:
        raise StoreError("reads of one pool must be ingested in retrieval order (a revision is only known from its read)")
    boundary = resp.get("boundary_at")
    status = int(resp["http_status"])
    rows: list = []
    bad_body = None
    ident = None
    sent = url_token(resp["url"])                     # the token of the request actually sent (skeptic CX-05)
    recorded = (resp.get("params") or {}).get("token", sent)
    if recorded != sent:
        raise StoreError(f"recorded token parameter {recorded!r} disagrees with the URL sent ({sent!r}): read refused")
    if status == 200:
        try:
            rows = parse_gt_ohlcv(body)
        except (ValueError, StoreError) as e:
            bad_body = str(e)[:200]
        ident = gt_identity(body, mint, sent)
    kept, dropped, refused = [], 0, 0
    if ident is not None and not ident.startswith("OK"):
        refused, rows_checked = len(rows), []           # never the mint's price: every candle refused, the read kept
    else:
        rows_checked = rows
    for r in rows_checked:
        try:
            start = epoch_seconds(r[0], "candle start")
            vals = [float(x) if x is not None else None for x in r[1:6]]
        except (TypeError, ValueError, IndexError):        # StoreError is a ValueError: a millisecond start is refused here
            refused += 1
            continue
        if boundary is not None and start + period > float(boundary):
            dropped += 1
            continue
        o, h, l, c, v = vals
        try:
            OC.normalize_observation({"kind": "CANDLE", "chain": chain, "contract": mint, "t": start, "available_at": ra,
                                      "provider": SOURCE_GT, "pair": pool, "period_s": period, "o": o, "h": h, "l": l, "c": c},
                                     {"future_dated_tolerance_s": 0})
        except OC.OutcomeError:
            refused += 1
            continue
        if not all(_num(x) and x > 0 for x in (o, h, l, c)) or not (_num(v) and v >= 0):
            refused += 1
            continue
        kept.append((start, o, h, l, c, v))
    starts = [k[0] for k in kept]
    cover_from = min(starts) if starts else None
    ident_ok = ident is None or ident.startswith("OK")
    if not ident_ok:
        cover_from = None
    # Repair m2: the vendor bounds each request in time, so a page shorter than the limit (even an empty one) does not prove
    # that nothing traded earlier (live: an empty page at 2026-10-14 for a pool with a candle on 2026-09-28). Coverage starts at
    # the earliest candle read; nothing is assumed before it.
    cover_complete = 0
    _insert(con, "predictive_raw_responses", {
        "response_key": rk, "source_id": SOURCE_GT, "request_url": resp["url"], "request_json": canon(resp.get("params") or {}),
        "chain": chain, "mint": mint, "pool_address": pool, "boundary_at": float(boundary) if boundary is not None else None,
        "retrieved_at": ra, "http_status": status, "body_sha256": bsha, "body_bytes": len(body), "body_gzip": gz(body),
        "cover_from": cover_from, "cover_complete": cover_complete, "candles_in_body": len(rows),
        "candles_dropped_after_boundary": dropped, "candles_refused": refused, "identity_check": ident,
        "collector": resp.get("collector", "memelab.predictive.sources"), "ingest_version": INGEST_GT,
        "schema_version": SCHEMA_VERSION, "recorded_at": float(now)})
    added = revisions = reads = 0
    seen_series = set()
    for start, o, h, l, c, v in sorted(kept):
        sk = _series_key(SOURCE_GT, chain, pool, period, start)
        if sk in seen_series:          # the same position twice in one body: keep the first
            continue
        seen_series.add(sk)
        prev = _latest_version(con, sk)
        values = [o, h, l, c, v]
        if prev is not None and not prev["vanished"] and [prev["o"], prev["h"], prev["l"], prev["c"], prev["v"]] == values:
            reads += _insert(con, "predictive_candle_reads", {"read_key": sha([prev["obs_key"], rk]), "obs_key": prev["obs_key"],
                                                              "response_key": rk, "retrieved_at": ra, "recorded_at": float(now)})
            continue
        end = start + period
        kind = None
        if prev is not None:
            av, basis, rev = ra, "REVISION_FIRST_READ", prev["obs_key"]
            same_cv = not prev["vanished"] and [prev["c"], prev["v"]] == [c, v]
            kind = "OPEN_WINDOW" if same_cv else ("APPEARED" if prev["vanished"] else "VALUES")
            revisions += 1
        elif _covered_by_earlier_read(con, chain, pool, start, period, ra) is not None:
            av, basis, rev, kind = ra, "REVISION_FIRST_READ", None, "APPEARED"   # appeared after an earlier read covered it
            revisions += 1
        elif ra < end + lag:
            av, basis, rev = ra, "CAPTURE", None
        else:
            av, basis, rev = end + lag, "PROVIDER_LAG_RECONSTRUCTION", None
        ok = sha([sk, values, 0, rev])
        added += _insert(con, "predictive_candles", {
            "obs_key": ok, "series_key": sk, "source_id": SOURCE_GT, "source_record_id": f"{pool}:{period}:{int(start)}",
            "chain": chain, "mint": mint, "pool_address": pool, "period_s": period, "start_at": start, "end_at": end,
            "o": o, "h": h, "l": l, "c": c, "v": v, "vanished": 0, "event_time": start, "published_at": None,
            "retrieved_at": ra, "available_at": av, "available_basis": basis, "revision_of": rev, "revision_kind": kind,
            "response_key": rk, "raw_sha256": bsha, "ingest_version": INGEST_GT, "schema_version": SCHEMA_VERSION,
            "recorded_at": float(now)})
    vanished = 0
    if status == 200 and bad_body is None and ident_ok and boundary is not None:
        lo = cover_from if not cover_complete else float("-inf")
        if cover_from is not None or cover_complete:
            for prev in con.execute(
                    "SELECT * FROM predictive_candles p WHERE chain=? AND pool_address=? AND period_s=? AND start_at >= ? "
                    "AND end_at <= ? AND id = (SELECT MAX(id) FROM predictive_candles q WHERE q.series_key = p.series_key) "
                    "AND vanished = 0 AND retrieved_at < ?", (chain, pool, period, lo, float(boundary), ra)).fetchall():
                if prev["series_key"] in seen_series:
                    continue
                ok = sha([prev["series_key"], [None] * 5, 1, prev["obs_key"]])
                vanished += _insert(con, "predictive_candles", {
                    "obs_key": ok, "series_key": prev["series_key"], "source_id": SOURCE_GT,
                    "source_record_id": prev["source_record_id"], "chain": chain, "mint": mint, "pool_address": pool,
                    "period_s": period, "start_at": prev["start_at"], "end_at": prev["end_at"], "o": None, "h": None, "l": None,
                    "c": None, "v": None, "vanished": 1, "event_time": prev["start_at"], "published_at": None, "retrieved_at": ra,
                    "available_at": ra, "available_basis": "REVISION_FIRST_READ", "revision_of": prev["obs_key"],
                    "revision_kind": "VANISHED", "response_key": rk, "raw_sha256": bsha, "ingest_version": INGEST_GT,
                    "schema_version": SCHEMA_VERSION, "recorded_at": float(now)})
    return {"response_key": rk, "duplicate_read": False, "status": status, "bad_body": bad_body, "identity_check": ident,
            "candles": len(rows),
            "kept": len(kept), "added": added, "revisions": revisions, "vanished": vanished, "reads": reads,
            "dropped": dropped, "refused": refused, "cover_from": cover_from, "cover_complete": cover_complete}


def record_series_status(con: sqlite3.Connection, *, chain: str, mint: str, pool: str, series_id: str, boundary_at: float,
                         need_from: float, status: str, detail: str | None, response_keys: list[str], calls: int,
                         candles_kept: int, last_end_at: float | None, checked_at: float, now: float,
                         period_s: int = 300) -> bool:
    """How one planned fetch series ended. Retrieval metadata: it sets missing reasons, it is never a feature (P09, P47)."""
    if status not in SERIES_STATUSES:
        raise StoreError(f"series status {status!r} is not one of {SERIES_STATUSES}")
    check_address(chain, mint)
    check_address(chain, pool, "pool")
    rows = [con.execute("SELECT cover_from, cover_complete, http_status, identity_check FROM predictive_raw_responses "
                        "WHERE response_key=?",
                        (k,)).fetchone() for k in response_keys]
    oks = [r for r in rows if r is not None and r["http_status"] == 200 and (r["identity_check"] or "").startswith("OK")]
    covers = [r["cover_from"] for r in oks if r["cover_from"] is not None]
    complete = 1 if (status in ("OK", "NO_DATA") and any(r["cover_complete"] for r in oks)) else 0
    kept = (int(candles_kept), last_end_at)
    return _insert(con, "predictive_source_status", {
        "status_key": sha([SOURCE_GT, chain, pool, series_id, status, sorted(response_keys), checked_at]), "source_id": SOURCE_GT,
        "chain": chain, "mint": mint, "pool_address": pool, "series_id": series_id, "boundary_at": float(boundary_at),
        "need_from": float(need_from), "status": status, "period_s": int(period_s), "detail": detail,
        "cover_from": min(covers) if covers else None,
        "cover_complete": complete, "last_end_at": kept[1], "calls": int(calls), "candles_kept": kept[0],
        "response_keys_json": canon(list(response_keys)), "checked_at": float(checked_at), "recorded_at": float(now)})


# ---------------------------------------------------------------- integrity
def verify(con: sqlite3.Connection) -> list[str]:
    """Recompute what can be recomputed: body hashes of stored vendor bodies, candle-to-body hashes, the decision rows' own
    hashes, the invariants of every feature value, snapshot hashes from their values. Returns problems (empty: consistent)."""
    probs: list[str] = []
    for r in con.execute("SELECT response_key, body_sha256, body_gzip FROM predictive_raw_responses WHERE body_gzip IS NOT NULL"):
        if hashlib.sha256(gzip.decompress(r["body_gzip"])).hexdigest() != r["body_sha256"]:
            probs.append(f"raw body {r['response_key'][:12]} does not match its sha256")
    for r in con.execute("SELECT c.obs_key FROM predictive_candles c JOIN predictive_raw_responses r USING(response_key) "
                         "WHERE c.raw_sha256 <> r.body_sha256"):
        probs.append(f"candle {r['obs_key'][:12]} names a body hash that is not its response's")
    for r in con.execute("SELECT decision_key, row_sha256, row_json FROM predictive_decisions"):
        if D.row_sha256(json.loads(r["row_json"])) != r["row_sha256"]:
            probs.append(f"decision {r['decision_key'][:12]}: row_json does not hash to row_sha256")
    n = con.execute("SELECT COUNT(*) FROM predictive_feature_values WHERE feature_available_at > cutoff_at").fetchone()[0]
    if n:
        probs.append(f"{n} feature values available after their cutoff")
    from . import features as F
    for s in con.execute("SELECT snapshot_key, snapshot_sha256 FROM predictive_snapshots"):
        vals = F.stored_values(con, s["snapshot_key"])
        if F.values_sha(vals) != s["snapshot_sha256"]:
            probs.append(f"snapshot {s['snapshot_key'][:12]}: values do not hash to snapshot_sha256")
    return probs


def table_counts(con: sqlite3.Connection) -> dict[str, int]:
    return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in DATA_TABLES}


def stored_body(con: sqlite3.Connection, response_key: str) -> bytes | None:
    r = con.execute("SELECT body_gzip FROM predictive_raw_responses WHERE response_key=?", (response_key,)).fetchone()
    return gzip.decompress(r[0]) if r and r[0] is not None else None


def responses(con: sqlite3.Connection, source_id: str | None = None) -> list[dict]:
    q = "SELECT * FROM predictive_raw_responses" + (" WHERE source_id=?" if source_id else "") + " ORDER BY retrieved_at, id"
    return [dict(r) for r in con.execute(q, (source_id,) if source_id else ())]


def iter_rows(con: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> list[dict]:
    return [dict(r) for r in con.execute(sql, tuple(params))]
