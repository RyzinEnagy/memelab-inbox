"""CM-2 daily cycle of the predictive engine (PI-D-122; rules: ../maintenance/cm2_promotion_cards/CHANGE_CONTROL.md Part C).

    python -B audits/predictive-intelligence/daily/predictive_daily.py run      # the whole cycle, for an unattended task
    python -B audits/predictive-intelligence/daily/predictive_daily.py status   # print the last summary and the windows
    python -B audits/predictive-intelligence/daily/predictive_daily.py verify   # check the ledger, the registry and the archive

Options of `run`: --state-dir (private, default data/private/predictive_daily, git-ignored), --no-fetch (use the local
origin/main), --export-ref (default origin/main; tests only), --no-commit (tests only: refuses any label read, because predictions must be committed first), --max-calls
(default 60), --max-minutes (default 40), --now (tests only).

Order of one run (each step refuses to start if the one before failed): lock and preflight; read the state exports on
origin/main and rebuild the private store; one PREDICTION per new Solana decision after the recipe freeze, target and kind;
commit the ledger; read matured labels (free GeckoTerminal, paced at 5.7 a minute, raw bodies archived with sha256); append
outcomes; evaluate windows with contract.PROMOTION_CM2; retrain on cadence; write ALERT_SUMMARY.txt; commit.

Writes only: the state directory, this folder (audits/predictive-intelligence/daily/), one line in
audits/predictive-intelligence/COST_LEDGER.md for a run that made calls, and git commits limited to those paths.
Exit 0 when the cycle completed; otherwise a nonzero code and a named reason on stderr and in ALERT_SUMMARY.txt.
Research only: no trade, no wallet, no key, no paid call; nothing is published or sent.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from memelab.predictive import baselines as B  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import evaluation as E  # noqa: E402
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import monitoring as M  # noqa: E402
from memelab.predictive import promotion as P  # noqa: E402
from memelab.predictive import runtime as R  # noqa: E402
from memelab.predictive import sources as SRC  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

REL = "audits/predictive-intelligence/daily"
DAILY = REPO / REL
RECIPE = DAILY / "RECIPE.json"
LEDGER = DAILY / "LEDGER.jsonl"
CARDS = DAILY / "cards"
REG = DAILY / "registry"
REG_LOG = REG / "REGISTRY_LOG.jsonl"
ENTRIES = REG / "entries"
BASE_LABELS = DAILY / "BASE_LABELS.jsonl.gz"
LABEL_ROWS = DAILY / "LABEL_ROWS.jsonl"
READS = DAILY / "READS.jsonl"
RAW = DAILY / "raw"
CALLS = DAILY / "CALLS.jsonl"
RUNS = DAILY / "RUNS.jsonl"
ALERT = DAILY / "ALERT_SUMMARY.txt"
STATUS = DAILY / "STATUS.json"
COST_REL = "audits/predictive-intelligence/COST_LEDGER.md"
SEALED = REPO / "audits/predictive-intelligence/phase_06/sealed/holdout_labels.jsonl.gz"
ALLOWED = (REL, COST_REL)

RECIPE_SHA256 = "93b6671433e9e94147d8728a1dcdd7b605fb37cbc82de5285a9a670fe2ddb50a"   # RECIPE.json as frozen in ed85b2c
GOVERNING_SHA = "b88f0058a3c86301d5c44ef1115a62ee1477971f733d7d3abbe25a3d7141e032"
TARGETS = (L.T1, L.T1B, L.T2)
SHORT = {L.T1: "T1_24h", L.T1B: "T1b_6h", L.T2: "T2_24h"}
KINDS = ("B0", "B2")
WIDE = ("DEVELOPMENT", "HOLDOUT", "PROSPECTIVE")
PER_MIN = 5.7
LIST_URL = "https://api.geckoterminal.com/api/v2/networks/solana/tokens/{mint}/pools?page=1"
EXPORT_REF = "origin/main"
MAX_AGE = float(C.ACCEPTANCE["max_model_age_s"])
DAY = 86400.0
CADENCE_S = 7 * DAY                      # RECIPE.json cadence: retrain when the newest version is 7 days old and a label matured

EXIT = {"OK": 0, "LOCKED": 2, "PREFLIGHT_FAILED": 3, "EXPORT_FETCH_FAILED": 4, "PREDICTION_COMMIT_FAILED": 5,
        "LABEL_FETCH_FAILED": 6, "LEDGER_REFUSED": 7, "TIME_BUDGET_EXCEEDED": 8, "RETRAIN_FAILED": 9, "COMMIT_FAILED": 10,
        "WRITE_OUTSIDE_ALLOWED_PATHS": 11}


class Fail(RuntimeError):
    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}")
        self.reason, self.detail = reason, detail


def iso(t: float) -> str:
    return datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fsha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def canon(o) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def jsave(p: Path, o) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, indent=1, sort_keys=True, default=str) + "\n")


def jl_read(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def jl_append(p: Path, rows: list[dict]) -> None:
    if not rows:
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        for r in rows:
            f.write(canon(r) + "\n")


def git(*a: str, check: bool = True, timeout: int = 180) -> str:
    r = subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise Fail("PREFLIGHT_FAILED", f"git {' '.join(a[:2])}: {r.stderr.strip()[:200]}")
    return r.stdout


# ---------------------------------------------------------------- recipe, freeze, holdout
def recipe() -> dict:
    if fsha(RECIPE) != RECIPE_SHA256:
        raise Fail("PREFLIGHT_FAILED", "RECIPE.json differs from its pinned sha256 (a recipe change is a new recipe)")
    if C.governing_sha256() != GOVERNING_SHA:
        raise Fail("PREFLIGHT_FAILED", "the governing fingerprint differs from the pin (contract or PROMOTION_CM2 changed)")
    return json.loads(RECIPE.read_text())


def freeze_time() -> float:
    out = git("log", "--diff-filter=A", "--format=%ct", "--", f"{REL}/RECIPE.json").split()
    if not out:
        raise Fail("PREFLIGHT_FAILED", "the commit that froze RECIPE.json is not in this clone (use a full clone)")
    return float(out[-1])


def holdout_rows() -> list[dict]:
    """The spent retrospective holdout (opened once in Phase 12), verified against the Phase 12 seal pins."""
    if fsha(SEALED) != E.SEAL_PINS["holdout_labels_sha256"]:
        raise Fail("PREFLIGHT_FAILED", "the sealed holdout file differs from the Phase 12 seal pin")
    with gzip.open(SEALED, "rt") as f:
        return [json.loads(x) for x in f if x.strip()]


# ---------------------------------------------------------------- private stores
def build_store(state: Path, ref: str) -> "object":
    """Exports and feature snapshots only (no candle), rebuilt when the export ref or the feature definitions change."""
    tip = git("rev-parse", ref).strip()
    mark = state / "store.json"
    path = state / "store.sqlite"
    want = {"ref": tip, "feature_set_sha": F.feature_set_sha(), "feature_version": F.FEATURE_VERSION, "schema": S.SCHEMA_VERSION}
    if not (path.exists() and mark.exists() and json.loads(mark.read_text()) == want):
        for p in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm"), mark):
            if p.exists():
                p.unlink()
        con = S.connect(path)
        ex = SRC.export_versions(REPO, tip)
        S.ingest_exports(con, ex, now=time.time(), ref=tip)
        F.build_snapshots(con, feature_version=F.FEATURE_VERSION, mode="provider", now=time.time())
        con.commit()
        con.close()
        jsave(mark, want)
    return S.connect(path)


def label_store(state: Path):
    """A private label table rebuilt from the committed base set and the daily label rows (both append-only)."""
    path = state / "labels.sqlite"
    for p in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        if p.exists():
            p.unlink()
    con = L.connect(path)
    rows = []
    if BASE_LABELS.exists():
        with gzip.open(BASE_LABELS, "rt") as f:
            rows += [json.loads(x) for x in f if x.strip()]
    rows += jl_read(LABEL_ROWS)
    for kind in ("predictive_label_runs", "predictive_labels"):
        for r in rows:
            if r["table"] == kind:
                S._insert(con, kind, {k: v for k, v in r["row"].items() if k != "id"})
    con.commit()
    return con


# ---------------------------------------------------------------- registry of the recipe
def registry() -> dict:
    ev = P.read_log(REG_LOG.read_text()) if REG_LOG.exists() else []
    st = P.state(ev)
    reg_at = {}
    for e in ev:
        if e["kind"] == "REGISTER":
            reg_at[e["entry"]["entry_id"]] = C.parse_utc(e["as_of_utc"])
    st["registered_at"] = reg_at
    st["events"] = ev
    return st


def versions(reg: dict, kind: str, target: str) -> list[dict]:
    out = [dict(e, registered_at=reg["registered_at"][i]) for i, e in reg["entries"].items()
           if e.get("recipe_id") and e["kind"] == kind and e["target"] == target and i not in reg["retired"]]
    return sorted(out, key=lambda e: (e["version"], e["registered_at"]))


def in_force(reg: dict, kind: str, target: str, t: float) -> tuple[dict | None, str | None]:
    """The newest version registered at or before t whose cutoff is before t; (entry, None) or (entry or None, reason)."""
    cand = [e for e in versions(reg, kind, target) if e["registered_at"] <= t and float(e["training_cutoff"]) < t]
    if not cand:
        return None, "MODEL_NOT_SELECTED"
    e = cand[-1]
    if t - float(e["training_cutoff"]) > MAX_AGE:
        return e, "MODEL_STALE"
    return e, None


def load_card(entry: dict) -> dict:
    p = REPO / entry["card_path"]
    if fsha(p) != entry["card_file_sha256"]:
        raise Fail("PREFLIGHT_FAILED", f"card {p.name} differs from its registry entry")
    return B.loads(p.read_text())


# ---------------------------------------------------------------- fitting one version of the recipe
def fit_version(lab_con, hold: list[dict], fs_con, *, rec: dict, version: int, now: float) -> dict:
    """B0 and B2 per target on every label training_labels returns with the recipe's splits; cutoff = the largest maturity."""
    rows_now = {t: L.training_labels(lab_con, now, t, splits=WIDE, spent_holdout_rows=hold) for t in TARGETS}
    mats = [float(r["label_matures_at"]) for t in TARGETS for r in rows_now[t]]
    if not mats:
        raise Fail("RETRAIN_FAILED", "no training label")
    cutoff = max(mats)
    fmap = {r["decision_key"]: r for r in F.training_view(fs_con, as_of=cutoff, feature_version=F.FEATURE_VERSION, mode="provider")}
    out = {"cutoff": cutoff, "cards": {}, "label_sets": {}}
    for t in TARGETS:
        rows = L.training_labels(lab_con, cutoff, t, splits=WIDE, spent_holdout_rows=hold)
        ex = B.join(rows, fmap)
        B.check_asof(ex, sorted(B.ALLOWED_COLUMNS), as_of=cutoff, with_labels=True)
        for e in ex:
            if not (e.decision_time < cutoff and e.label_matures_at <= cutoff):
                raise Fail("RETRAIN_FAILED", f"training row {e.decision_key[:12]} not decided before and matured by the cutoff")
        split_n = Counter(L.split_of(t, r["decision_time"]) for r in rows)
        meta = {"phase": "CM2", "recipe_id": rec["recipe_id"], "version": version, "training_splits": list(WIDE),
                "split_counts": dict(sorted(split_n.items())), "evidence_class": "CM2_ALL_MATURED_PROVIDER_MODE"}
        for kind in KINDS:
            card = B.fit_b0(t, ex, cutoff) if kind == "B0" else B.fit_b2(t, ex, cutoff)
            card.update(meta)
            card["model_sha"] = B.sha({k: v for k, v in card.items() if k != "model_sha"})
            B.verify_card(card)
            out["cards"][(kind, t)] = card
        out["label_sets"][t] = {"n": len(ex), "k": int(sum(e.y for e in ex)), "splits": dict(sorted(split_n.items())),
                                "days": len({e.day for e in ex}), "mints": len({e.mint for e in ex})}
    return out


def register_version(fit: dict, *, rec: dict, version: int, as_of: float, retire: list[str] | None = None,
                     retire_source: str | None = None) -> list[dict]:
    """Card files, entries and the REGISTER (+ RETIRE) and PIN events of one version. Levels at registration: ABSTAIN for a
    reference (no window can have passed yet), recomputed later only from closed windows."""
    CARDS.mkdir(parents=True, exist_ok=True)
    ENTRIES.mkdir(parents=True, exist_ok=True)
    evs: list[dict] = []
    if retire:
        evs.append({"kind": "RETIRE", "as_of_utc": iso(as_of), "entry_ids": sorted(retire), "source_log_sha256": retire_source,
                    "reason": "MODEL_STALE since 2026-10-31; replaced by recipe R-CM2-1 (ED-10, PI-D-122); kept for history"})
    ids: dict = {}
    for (kind, t), card in sorted(fit["cards"].items()):
        rel = f"{REL}/cards/{rec['recipe_id']}_v{version}_{kind}_{SHORT[t]}.json"
        (REPO / rel).write_text(B.dumps(card))
        lv = P.level([], role="REFERENCE_BASELINE")
        e = P.make_entry(entry_kind="CM2_CARD", recipe_id=rec["recipe_id"], version=version, kind=kind, target=t,
                         role="REFERENCE_BASELINE", model_id=card["model_id"], model_sha=card["model_sha"], card_path=rel,
                         card_file_sha256=fsha(REPO / rel), training_cutoff=card["training_cutoff"],
                         training_cutoff_utc=card["training_cutoff_utc"], registry_sha=card["registry_sha"],
                         governing_sha=C.governing_sha256(), n_train=card["n_train"], k_train=card["k_train"],
                         n_used=card["n_used"], k_used=card["k_used"], label_set_sha=card["label_set_sha"],
                         data_snapshot_sha=card["data_snapshot_sha"], level=lv["level"], level_reasons=lv["reasons"],
                         tests={"leakage": True, "provenance": True, "contract": card["registry_sha"] == C.registry_sha256()},
                         is_fixture=False)
        jsave(ENTRIES / f"{e['entry_id']}.json", e)
        evs.append({"kind": "REGISTER", "as_of_utc": iso(as_of), "entry": e})
        ids[(kind, t)] = e["entry_id"]
    for t in TARGETS:
        evs.append({"kind": "PIN", "as_of_utc": iso(as_of), "target": t, "mode": "NO_VIABLE_CHAMPION", "champion": None,
                    "references": {"B0": ids[("B0", t)], "B2": ids[("B2", t)]},
                    "reasons": ["NO_PROSPECTIVE_WINDOW_PASSED", "REFERENCE_BASELINE_NEVER_PUBLISHED"]})
    cur = fsha(REG_LOG) if REG_LOG.exists() else None
    return P.append_events(REG_LOG, evs, expect_sha=cur)


# ---------------------------------------------------------------- label reads (free GeckoTerminal, paced)
class Reader:
    def __init__(self, *, max_calls: int, deadline: float, offline: bool = False):
        self.guard = R.CallGuard(max_per_min=PER_MIN, max_calls=max_calls)
        self.deadline, self.offline, self.calls, self.stopped = deadline, offline, [], None

    def get(self, url: str, *, kind: str) -> tuple[int, bytes, float, float] | None:
        if self.offline:
            raise Fail("LABEL_FETCH_FAILED", "a label read was attempted with reads disabled")
        if self.stopped:
            return None
        if time.time() + 20 > self.deadline:
            self.stopped = "TIME_BUDGET"
            return None
        last = {}

        def call(u):
            last["sent"] = time.time()
            c, b = SRC.curl_get(u, timeout_s=30)
            last["r"] = (c, b)
            if c != 200:
                raise SRC.HTTPStatusError(f"HTTP {c}")
            return c, b

        for attempt in range(2):
            st, val = self.guard.call("geckoterminal", call, url)
            got = time.time()
            if st["state"] in (R.CIRCUIT_OPEN, R.CALL_CAP_REACHED, R.COST_CAP_REACHED):
                self.stopped = st["state"]
                return None
            code, body = val if st["state"] == R.AVAILABLE else last.get("r", (0, b""))
            sent = last.get("sent", got)
            self.calls.append({"kind": kind, "url": url, "sent_t": sent, "sent_utc": iso(sent), "retrieved_t": got, "http": code,
                               "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "attempt": attempt})
            ts = sorted(c["sent_t"] for c in self.calls)
            if max(sum(1 for u in ts if t <= u < t + 60) for t in ts) > 6:
                raise Fail("LABEL_FETCH_FAILED", "rate check: more than 6 calls in 60 s")
            if code == 429 and attempt == 0 and time.time() + 80 < self.deadline:
                time.sleep(60)
                continue
            return code, body, sent, got
        return code, body, sent, got


def archive(body: bytes, url: str, got: float) -> tuple[str, str]:
    RAW.mkdir(parents=True, exist_ok=True)
    bsha = hashlib.sha256(body).hexdigest()
    name = f"gt_{hashlib.sha256((url + repr(got)).encode()).hexdigest()[:16]}_{bsha[:8]}.json.gz"
    blob = gzip.compress(body, compresslevel=9, mtime=0)
    (RAW / name).write_bytes(blob)
    return name, hashlib.sha256(blob).hexdigest()


def read_record(kind: str, *, decision_key: str | None, mint: str, pool: str | None, url: str, boundary: float | None,
                code: int, body: bytes, sent: float, got: float) -> dict:
    name, fs = archive(body, url, got)
    return {"kind": kind, "decision_key": decision_key, "mint": mint, "pool": pool, "url": url, "boundary": boundary, "http": code,
            "requested_at": sent, "retrieved_at": got, "retrieved_utc": iso(got), "file": name, "file_sha256": fs,
            "body_sha256": hashlib.sha256(body).hexdigest(), "response_key": hashlib.sha256(canon([url, got, fs]).encode()).hexdigest()}


def body_of(rec: dict) -> bytes:
    blob = (RAW / rec["file"]).read_bytes()
    if hashlib.sha256(blob).hexdigest() != rec["file_sha256"]:
        raise Fail("PREFLIGHT_FAILED", f"archived body {rec['file']} differs from its sha256")
    body = gzip.decompress(blob)
    if hashlib.sha256(body).hexdigest() != rec["body_sha256"]:
        raise Fail("PREFLIGHT_FAILED", f"archived body {rec['file']} does not decompress to its body sha256")
    return body


def to_read(rec: dict) -> L.Read:
    return L.read_from_body(body_of(rec), mint=rec["mint"], pool=rec["pool"], url=rec["url"], boundary=rec["boundary"],
                            retrieved_at=rec["retrieved_at"], http_status=rec["http"], response_key=rec["response_key"])


def pools_of_list(body: bytes):
    try:
        d = json.loads(body)
    except ValueError:
        return None
    out = []
    for it in d.get("data") or []:
        a = (it.get("attributes") or {}).get("address")
        if isinstance(a, str):
            try:
                out.append(S.check_address("solana", a, "pool"))
            except S.StoreError:
                continue
    return out


def reads_state(reads: list[dict]) -> tuple[dict, dict, dict]:
    """Latest OHLCV read per decision, the vendor list per mint and the other-pool reads per decision, from READS.jsonl."""
    ohlcv, lists, others = {}, {}, {}
    for r in reads:
        if r["kind"] == "ohlcv":
            ohlcv[r["decision_key"]] = r
        elif r["kind"] == "pool_list":
            lists[r["mint"]] = r
        elif r["kind"] in ("ohlcv_other_pool", "other_pools_list_failed"):
            others.setdefault(r["decision_key"], []).append(r)
    return ohlcv, lists, others


def decision_dicts(rows: list[dict], lists: dict) -> list[dict]:
    out = []
    for r in rows:
        vl = lists.get(r["mint"])
        vp = None
        if vl is not None:
            ps = pools_of_list(body_of(vl)) if vl["http"] == 200 else None
            vp = ps if ps is not None else L.LIST_FAILED
        out.append(L.decision_from_row(r, vendor_pools=vp))
    return out


def universe(rows: list[dict], reads: list[dict], now: float) -> L.Universe:
    ohlcv, lists, others = reads_state(reads)
    decs = decision_dicts(rows, lists)
    read_of = {k: to_read(r) for k, r in ohlcv.items()}
    oth = {}
    for k, rs in others.items():
        if any(r["kind"] == "other_pools_list_failed" for r in rs):
            oth[k] = L.LIST_FAILED
        else:
            oth[k] = [to_read(r) if r["http"] == 200 or r.get("file") else None for r in rs][:3]
    return L.Universe(decs, as_of=now, read_of=read_of, other_reads=oth)


def plan_reads(decs: list[dict], ohlcv: dict, now: float) -> list[dict]:
    """One read per decision with a snapshot price and a pool, boundary = the largest window end of its matured targets; a
    decision whose read stops before a newly matured target's window end is read again (OI21-1)."""
    plan = []
    for d in decs:
        if L.snapshot_price(d) is None or not d.get("pool"):
            continue
        bs = [L.needed_boundary(t, d["decision_time"]) for t in TARGETS if C.label_matures_at(t, d["decision_time"]) <= now - 120]
        if not bs:
            continue
        b = max(bs)
        have = ohlcv.get(d["decision_key"])
        if have is not None and have["http"] == 200 and float(have["boundary"]) >= b:
            continue
        plan.append({"decision": d, "boundary": b})
    return sorted(plan, key=lambda p: (p["decision"]["decision_time"], p["decision"]["decision_key"]))


def fetch_labels(rows: list[dict], reader: Reader, now: float) -> dict:
    reads = jl_read(READS)
    ohlcv, lists, _ = reads_state(reads)
    new: list[dict] = []
    # vendor lists for decisions without a point-in-time pool (CURRENT_VENDOR_LIST route), once per mint
    decs0 = decision_dicts(rows, lists)
    for d in decs0:
        if d.get("pool") or L.snapshot_price(d) is None or d["mint"] in lists:
            continue
        if not any(C.label_matures_at(t, d["decision_time"]) <= now - 120 for t in TARGETS):
            continue
        url = LIST_URL.format(mint=d["mint"])
        got = reader.get(url, kind="pool_list")
        if got is None:
            break
        rec = read_record("pool_list", decision_key=None, mint=d["mint"], pool=None, url=url, boundary=None, code=got[0],
                          body=got[1], sent=got[2], got=got[3])
        new.append(rec)
        lists[d["mint"]] = rec
        jl_append(READS, [rec])
    decs = decision_dicts(rows, lists)
    for p in plan_reads(decs, ohlcv, now):
        d, b = p["decision"], int(p["boundary"])
        url = SRC.gt_url(d["pool"], b, token=d["mint"])
        if "token=" + d["mint"] not in url:
            raise Fail("LABEL_FETCH_FAILED", "a label read without token=<mint>")
        got = reader.get(url, kind="ohlcv")
        if got is None:
            break
        rec = read_record("ohlcv", decision_key=d["decision_key"], mint=d["mint"], pool=d["pool"], url=url, boundary=b,
                          code=got[0], body=got[1], sent=got[2], got=got[3])
        new.append(rec)
        jl_append(READS, [rec])
    # other pools for T2 records with an evidenced reference halt (at most 3, vendor order)
    u = universe(rows, jl_read(READS), now)
    for r in M.prospective_records(u):
        if r["target"] != L.T2 or r["state"] != L.NEEDS_OTHER_POOLS:
            continue
        d = r["decision"]
        vl = lists.get(d["mint"])
        if vl is None:
            url = LIST_URL.format(mint=d["mint"])
            got = reader.get(url, kind="pool_list")
            if got is None:
                break
            vl = read_record("pool_list", decision_key=None, mint=d["mint"], pool=None, url=url, boundary=None, code=got[0],
                             body=got[1], sent=got[2], got=got[3])
            lists[d["mint"]] = vl
            new.append(vl)
            jl_append(READS, [vl])
        pools = pools_of_list(body_of(vl)) if vl["http"] == 200 else None
        if pools is None:
            rec = {"kind": "other_pools_list_failed", "decision_key": d["decision_key"], "mint": d["mint"], "pool": None,
                   "url": vl["url"], "boundary": None, "http": vl["http"], "retrieved_at": vl["retrieved_at"], "file": None}
            new.append(rec)
            jl_append(READS, [rec])
            continue
        b = int(L.needed_boundary(L.T2, d["decision_time"]))
        for pool in [x for x in pools if x != d["pool"]][:3]:
            url = SRC.gt_url(pool, b, token=d["mint"])
            got = reader.get(url, kind="ohlcv_other_pool")
            if got is None:
                break
            rec = read_record("ohlcv_other_pool", decision_key=d["decision_key"], mint=d["mint"], pool=pool, url=url, boundary=b,
                              code=got[0], body=got[1], sent=got[2], got=got[3])
            new.append(rec)
            jl_append(READS, [rec])
    jl_append(CALLS, reader.calls)
    return {"reads": len(new), "calls": len(reader.calls), "stopped": reader.stopped,
            "http": dict(Counter(str(c["http"]) for c in reader.calls))}


# ---------------------------------------------------------------- ledger steps
def new_decision_rows(fs_con, freeze: float, idx: M.Index) -> list[dict]:
    rows = S.iter_rows(fs_con, "SELECT * FROM predictive_decisions WHERE decision_key IS NOT NULL AND decision_time > ? "
                               "ORDER BY decision_time, mint, id", (freeze,))
    return [r for r in rows if r["chain"] == "solana" and r["decision_key"] not in idx.decisions]


def predicted_rows(fs_con, idx: M.Index) -> list[dict]:
    keys = set(idx.decisions)
    if not keys:
        return []
    rows = S.iter_rows(fs_con, "SELECT * FROM predictive_decisions WHERE decision_key IS NOT NULL ORDER BY decision_time, mint, id")
    return [r for r in rows if r["decision_key"] in keys]


def predict(fs_con, rows: list[dict], reg: dict, rec: dict, now: float) -> list[dict]:
    if not rows:
        return []
    fmap = {r["decision_key"]: r for r in F.training_view(fs_con, as_of=max(r["decision_time"] for r in rows),
                                                          feature_version=F.FEATURE_VERSION, mode="provider")}
    decs = [{"decision_key": r["decision_key"], "chain": r["chain"], "mint": r["mint"], "decision_time": float(r["decision_time"])}
            for r in rows]
    set_body = canon(decs).encode()
    set_id = "cm2set_" + hashlib.sha256(set_body).hexdigest()[:32]
    out = [{"kind": "PREDICTION_SET", "set_id": set_id, "decisions": decs, "sha256": hashlib.sha256(set_body).hexdigest(),
            "recipe_id": rec["recipe_id"], "recorded_at": now}]
    cards: dict[str, dict] = {}
    for r in rows:
        dt = float(r["decision_time"])
        f = fmap.get(r["decision_key"])
        for t in TARGETS:
            for kind in KINDS:
                e, why = in_force(reg, kind, t, dt)
                number = None
                if e is not None and why is None:
                    if f is None:
                        why = "MISSING_REQUIRED_INPUT"
                    else:
                        card = cards.setdefault(e["entry_id"], load_card(e))
                        x, av = B.model_inputs(f)
                        ex = B.Example(r["decision_key"], r["chain"], r["mint"], dt, dt, 0, x, av)
                        p, w = B.predict(card, [ex])
                        if math.isfinite(float(p[0])):
                            number = float(p[0])
                        else:
                            why = w[0] or "OOD"
                pl = {"kind": "PREDICTION", "set_id": set_id, "decision_key": r["decision_key"], "chain": r["chain"],
                      "mint": r["mint"], "decision_time": dt, "target": t, "candidate": f"{rec['recipe_id']}:{kind}", "number": number,
                      "why": why, "card_file_sha256": e["card_file_sha256"] if e else None, "model_sha": e["model_sha"] if e else None,
                      "training_cutoff_utc": e["training_cutoff_utc"] if e else None, "label_matures_at": C.label_matures_at(t, dt),
                      "published": False, "role": "REFERENCE_BASELINE", "version": e["version"] if e else None,
                      "entry_id": e["entry_id"] if e else None,
                      "version_registered_at": e["registered_at"] if e else None, "version_stale": (why == "MODEL_STALE") if e else None,
                      "recorded_at": now}
                pl["prediction_id"] = "cm2p_" + M.sha({k: v for k, v in pl.items() if k != "recorded_at"})[:40]
                out.append(pl)
    return out


def append_ledger(payloads: list[dict]) -> dict:
    if not payloads:
        return {"appended": 0}
    idx = M.load(LEDGER)
    try:
        return M.append(LEDGER, payloads, expect_sha=M.head_sha(idx.entries))
    except M.LedgerError as e:
        raise Fail("LEDGER_REFUSED", str(e))


def label_rows_for(recs: list[dict], now: float) -> list[dict]:
    have = set()
    for r in jl_read(LABEL_ROWS):
        if r["table"] == "predictive_labels":
            have.add(r["row"]["label_key"])
    run = {"run_key": L.sha(["cm2-daily", L.LABELS_VERSION, C.registry_sha256()]), "labels_version": L.LABELS_VERSION,
           "registry_sha": C.registry_sha256(), "export_ref": EXPORT_REF, "params_json": canon({"recipe": "R-CM2-1"}), "recorded_at": 0.0}
    out = []
    runs = {r["row"]["run_key"] for r in jl_read(LABEL_ROWS) if r["table"] == "predictive_label_runs"}
    if run["run_key"] not in runs:
        out.append({"table": "predictive_label_runs", "row": run})
    for rec in recs:
        if rec["state"] == L.NEEDS_OTHER_POOLS or rec["state"] not in ("LABELED", "MARKET_INACTIVE", "VENDOR_OR_ROUTE_GAP",
                                                                        "UNVERIFIABLE_NO_VENDOR_HISTORY", "THINNED"):
            continue
        row = L.record_row(rec, run_key=run["run_key"], registry_sha=C.registry_sha256(), now=now)
        if row["label_key"] not in have:
            have.add(row["label_key"])
            out.append({"table": "predictive_labels", "row": row})
    return out


# ---------------------------------------------------------------- windows
def commit_times() -> dict[int, float]:
    """For each ledger line number, the commit time of the first commit of the ledger that holds it."""
    out: dict[int, float] = {}
    log = git("log", "--reverse", "--format=%H %ct", "--", f"{REL}/LEDGER.jsonl").split("\n")
    seen = 0
    for line in log:
        if not line.strip():
            continue
        h, ct = line.split()
        n = len([x for x in git("show", f"{h}:{REL}/LEDGER.jsonl", check=False).splitlines() if x.strip()])
        for s in range(seen, n):
            out.setdefault(s, float(ct))
        seen = max(seen, n)
    return out


def window_rows(idx: M.Index, target: str, kind: str, rec: dict, commits: dict[int, float]) -> list[dict]:
    seq_of = {}
    for e in idx.entries:
        p = e["payload"]
        if p["kind"] == "PREDICTION":
            seq_of[("P", p["prediction_id"])] = e["seq"]
        elif p["kind"] == "OUTCOME":
            seq_of[("O", p["outcome_id"])] = e["seq"]
    preds = M.predictions(idx)
    cur = M.current_outcomes(idx)
    out = []
    cand = f"{rec['recipe_id']}:{kind}"
    for (k, t, c), p in preds.items():
        if t != target or c != cand:
            continue
        o = cur.get((k, t))
        final = o is not None and o["state"] not in M.NON_FINAL
        sc = final and o["state"] == "LABELED" and not int(o["censored"]) and o["label"] in (0, 1) and p["number"] is not None
        b0 = preds.get((k, t, f"{rec['recipe_id']}:B0"))
        b2 = preds.get((k, t, f"{rec['recipe_id']}:B2"))
        ps = seq_of[("P", p["prediction_id"])]
        out.append({"decision_key": k, "decision_time": p["decision_time"], "mint": p["mint"], "final": final, "scorable": sc,
                    "y": o["label"] if sc else None, "number": p["number"], "b0_number": b0["number"] if b0 else None,
                    "b2_number": b2["number"] if b2 else None, "prediction_seq": ps,
                    "outcome_seq": seq_of.get(("O", o["outcome_id"])) if o else None, "prediction_committed_at": commits.get(ps),
                    "label_observed_at": o["label_observed_at"] if o else None,
                    "version_registered_at": p.get("version_registered_at"), "version_stale": p.get("version_stale"),
                    "entry_id": p.get("entry_id")})
    return out


def window_results(idx: M.Index, target: str, kind: str) -> list[dict]:
    return [e["payload"]["result"] for e in idx.entries if e["payload"]["kind"] == "MONITOR"
            and e["payload"].get("monitor") == "WINDOW_RESULT" and e["payload"]["target"] == target and e["payload"]["kind_model"] == kind]


def evaluate(rec: dict, reg: dict, freeze: float, now: float) -> dict:
    idx = M.load(LEDGER)
    commits = commit_times()
    summary, new = {}, []
    for t in TARGETS:
        for kind in KINDS:
            res = window_results(idx, t, kind)
            rows = window_rows(idx, t, kind, rec, commits)
            while True:
                after = freeze
                from_day = C.parse_utc(res[-1]["next_from_day_utc"]) if res else None
                win = P.next_window(rows, after=after, from_day=from_day)
                if win["state"] != P.CLOSED:
                    break
                tests = {"leakage": True, "provenance": True, "contract": True}
                for r in win["scored"]:
                    e = reg["entries"].get(r["entry_id"])
                    if e is None:
                        tests = {"leakage": False, "provenance": False, "contract": False}
                    else:
                        tests = {k: tests[k] and e["tests"].get(k) is True for k in tests}
                out = P.evaluate_window(win, kind=kind, freeze=freeze, n_search=int(rec["n_search_cumulative"]), windows=len(res) + 1,
                                        tests=tests)
                out["next_from_day_utc"] = iso(win["next_from_day"])
                out["window"] = len(res) + 1
                new.append({"kind": "MONITOR", "monitor": "WINDOW_RESULT", "target": t, "kind_model": kind, "recipe_id": rec["recipe_id"],
                            "result": out, "recorded_at": now})
                res.append(out)
            lv = P.level(res, role="REFERENCE_BASELINE")
            summary[(t, kind)] = {"level": lv["level"], "windows": len(res), "open": {k: win.get(k) for k in
                                  ("scored_n", "scored_k", "scored_days", "complete_days")}}
    led = append_ledger(new)
    return {"summary": summary, "appended": led.get("appended", 0)}


# ---------------------------------------------------------------- commits and the summary
def porcelain() -> set[str]:
    return {ln[3:] for ln in git("status", "--porcelain", "--untracked-files=all").splitlines() if ln.strip()}


def outside(paths: set[str]) -> set[str]:
    return {p for p in paths if not any(p == a or p.startswith(a + "/") for a in ALLOWED)}


def commit(msg: str, *, reason: str) -> str | None:
    if not (porcelain() - outside(porcelain())):
        return None
    ident = []
    if not git("config", "user.email", check=False).strip():
        ident = ["-c", "user.name=memelab predictive daily", "-c", "user.email=predictive-daily@localhost"]
    r = subprocess.run(["git", "-C", str(REPO), *ident, "add", "--", *ALLOWED], capture_output=True, text=True)
    if r.returncode:
        raise Fail(reason, r.stderr.strip()[:200])
    r = subprocess.run(["git", "-C", str(REPO), *ident, "commit", "-q", "-m", msg, "--", *ALLOWED], capture_output=True, text=True)
    if r.returncode:
        raise Fail(reason, (r.stderr or r.stdout).strip()[:200])
    return git("rev-parse", "HEAD").strip()


def cost_line(day: str, calls: int, http: dict) -> None:
    p = REPO / COST_REL
    txt = p.read_text()
    line = (f"| {day} | CM-2 daily | none | no billable call; {calls} free GeckoTerminal calls by the daily cycle "
            f"(http {', '.join(f'{k}: {v}' for k, v in sorted(http.items()))}), paced at 5.7 a minute, logged in "
            f"`daily/CALLS.jsonl` | 0 | 0 |\n")
    marker = "\nRemaining Firecrawl allowance"
    i = txt.rfind(marker)
    txt = txt[:i].rstrip("\n") + "\n" + line + txt[i:] if i >= 0 else txt + line
    p.write_text(txt)


def write_alert(lines: list[str]) -> None:
    ALERT.write_text("\n".join(lines[:12]) + "\n")


def summary_lines(st: dict) -> list[str]:
    out = [f"memelab predictive daily {st['day']}: {st['result']}"]
    if st.get("reason"):
        out.append(f"failed: {st['reason']} ({st.get('detail', '')[:160]})")
    if "exports" in st:
        out.append(f"exports: newest {st['exports']['newest_utc']} ({st['exports']['tip'][:7]}); new decisions after the freeze: "
                   f"{st.get('new_decisions', 0)}")
    if "labels" in st:
        out.append(f"predictions appended: {st.get('predictions', 0)}; label calls: {st['labels']['calls']}; outcomes appended: "
                   f"{st.get('outcomes', 0)}")
    if "cards" in st:
        out.append(f"cards: {st['cards']}")
    if "windows" in st:
        out.append(f"windows: {st['windows']}")
    for n in st.get("notes", [])[:4]:
        out.append(f"note: {n}")
    out.append("nothing is published, traded or sent; levels are research states only")
    return out


# ---------------------------------------------------------------- the run
def run(args) -> int:
    t0 = time.time()
    now = float(args.now) if args.now is not None else t0
    deadline = t0 + 60 * float(args.max_minutes)
    state = Path(args.state_dir) if args.state_dir else REPO / "data/private/predictive_daily"
    st: dict = {"day": iso(now)[:10], "result": "RUNNING", "notes": []}
    state.mkdir(parents=True, exist_ok=True)
    lock = state / "lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if time.time() - lock.stat().st_mtime < 3 * 3600:
            print("FAILED LOCKED: another run holds the lock", file=sys.stderr)
            return EXIT["LOCKED"]
        lock.unlink()
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    before = outside(porcelain())
    try:
        rec = recipe()
        freeze = freeze_time()
        # recovery: a run that stopped after appending but before its commit left only allowed, append-only changes
        dirty = porcelain() - outside(porcelain())
        if dirty:
            if LEDGER.exists() and not M.verify(LEDGER)["ok"]:
                raise Fail("PREFLIGHT_FAILED", "the working ledger does not verify")
            old = git("show", f"HEAD:{REL}/LEDGER.jsonl", check=False)
            if LEDGER.exists() and not M.is_append_only(old, LEDGER.read_text()):
                raise Fail("PREFLIGHT_FAILED", "the working ledger is not an append of the committed one")
            if not args.no_commit:
                commit("predictive-intel daily: recover the changes of an interrupted run", reason="COMMIT_FAILED")
                st["notes"].append("RECOVERED_AN_INTERRUPTED_RUN")
        if LEDGER.exists():
            v = M.verify(LEDGER)
            if not v["ok"]:
                raise Fail("PREFLIGHT_FAILED", f"ledger: {v['problems'][:1]}")
        reg = registry()
        if not reg["entries"]:
            raise Fail("PREFLIGHT_FAILED", "no registered version of the recipe")
        # 1. exports
        if not args.no_fetch:
            r = subprocess.run(["git", "-C", str(REPO), "fetch", "-q", "origin", "main"], capture_output=True, text=True, timeout=180)
            if r.returncode:
                raise Fail("EXPORT_FETCH_FAILED", r.stderr.strip()[:200])
        fs = build_store(state, args.export_ref)
        tip = git("rev-parse", args.export_ref).strip()
        newest = float(git("log", "-1", "--format=%ct", tip, "--", SRC.EXPORT_PATH).strip() or 0)
        st["exports"] = {"tip": tip, "newest_utc": iso(newest)}
        if now - newest > 36 * 3600:
            st["notes"].append(f"NO_NEW_EXPORTS: the newest state export on origin/main is {iso(newest)[:10]}")
        # 2. predictions, committed before any read
        idx = M.load(LEDGER) if LEDGER.exists() else M.Index()
        rows = new_decision_rows(fs, freeze, idx)
        st["new_decisions"] = len(rows)
        pl = predict(fs, rows, reg, rec, now)
        st["predictions"] = append_ledger(pl).get("appended", 0) - (1 if pl else 0)
        if pl:
            if args.no_commit:
                raise Fail("PREDICTION_COMMIT_FAILED", "--no-commit: predictions cannot be committed, so no label is read")
            commit(f"predictive-intel daily: {len(rows)} decisions predicted ({st['day']})", reason="PREDICTION_COMMIT_FAILED")
        if LEDGER.exists() and git("show", f"HEAD:{REL}/LEDGER.jsonl", check=False) != LEDGER.read_text():
            if not args.no_commit:
                raise Fail("PREDICTION_COMMIT_FAILED", "HEAD does not hold every prediction before the label reads")
        # 3. labels (only for predicted decisions)
        idx = M.load(LEDGER) if LEDGER.exists() else M.Index()
        prow = predicted_rows(fs, idx)
        offline = bool(args.no_commit)
        reader = Reader(max_calls=int(args.max_calls), deadline=min(deadline, t0 + 25 * 60), offline=offline)
        if offline:
            plan_n = len(plan_reads(decision_dicts(prow, reads_state(jl_read(READS))[1]), reads_state(jl_read(READS))[0], now))
            if plan_n:
                raise Fail("LABEL_FETCH_FAILED", f"--no-commit: {plan_n} reads planned but reads are disabled")
            lab = {"reads": 0, "calls": 0, "stopped": None, "http": {}}
        else:
            lab = fetch_labels(prow, reader, now)
        st["labels"] = lab
        if lab["stopped"]:
            st["notes"].append(f"LABEL_READS_STOPPED_{lab['stopped']}: the rest is read next run")
        if lab["calls"]:
            cost_line(st["day"], lab["calls"], lab["http"])
        # 4. outcomes
        if prow:
            u = universe(prow, jl_read(READS), now)
            recs = M.prospective_records(u)
            idx = M.load(LEDGER)
            oc = M.next_outcomes(idx, recs, recorded_at=now)
            st["outcomes"] = append_ledger(oc).get("appended", 0)
            jl_append(LABEL_ROWS, label_rows_for(recs, now))
        # 5. windows
        ev = evaluate(rec, reg, freeze, now)
        st["windows"] = "; ".join(f"{SHORT[t]} {k} {v['level']} (windows {v['windows']}, open {v['open'].get('scored_n') or 0}/50 "
                                  f"events, {v['open'].get('scored_days') or 0}/5 days)" for (t, k), v in sorted(ev["summary"].items())
                                  if k == "B2") + "; B0 ABSTAIN (reference)"
        # 6. retrain on cadence
        newest_v = max(versions(reg, "B2", L.T1), key=lambda e: e["version"])
        age = now - float(newest_v["training_cutoff"])
        st["cards"] = (f"{rec['recipe_id']} v{newest_v['version']}, cutoff {newest_v['training_cutoff_utc']}, stale after "
                       f"{iso(float(newest_v['training_cutoff']) + MAX_AGE)}")
        if age >= CADENCE_S:
            lab_con = label_store(state)
            hold = holdout_rows()
            mats = [float(r["label_matures_at"]) for t in TARGETS
                    for r in L.training_labels(lab_con, now, t, splits=WIDE, spent_holdout_rows=hold)]
            if mats and max(mats) > float(newest_v["training_cutoff"]):
                try:
                    fit = fit_version(lab_con, hold, fs, rec=rec, version=newest_v["version"] + 1, now=now)
                    register_version(fit, rec=rec, version=newest_v["version"] + 1, as_of=now)
                except Fail:
                    raise
                except Exception as e:      # noqa: BLE001 (named reason, never a silent pass)
                    raise Fail("RETRAIN_FAILED", f"{type(e).__name__}: {e}")
                st["notes"].append(f"RETRAINED: version {newest_v['version'] + 1}, cutoff {iso(fit['cutoff'])}")
            else:
                st["notes"].append("NO_NEW_MATURED_LABELS: no retrain; the newest version goes MODEL_STALE at cutoff + 14 days")
        if now > float(newest_v["training_cutoff"]) + MAX_AGE:
            st["notes"].append("MODEL_STALE: every prediction abstains until a retrain")
        if time.time() > deadline:
            raise Fail("TIME_BUDGET_EXCEEDED", f"{round(time.time() - t0)} s")
        st["result"] = "OK"
        code = 0
    except Fail as e:
        st.update(result="FAILED", reason=e.reason, detail=e.detail)
        code = EXIT.get(e.reason, 1)
        print(f"FAILED {e.reason}: {e.detail}", file=sys.stderr)
    except Exception as e:                  # noqa: BLE001
        st.update(result="FAILED", reason="UNEXPECTED_ERROR", detail=f"{type(e).__name__}: {e}")
        code = 1
        print(f"FAILED UNEXPECTED_ERROR: {type(e).__name__}: {e}", file=sys.stderr)
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass
    st["wall_s"] = round(time.time() - t0, 1)
    write_alert(summary_lines(st))
    jl_append(RUNS, [{k: v for k, v in st.items() if k != "labels"} | {"label_calls": (st.get("labels") or {}).get("calls", 0),
                                                                        "exit": code, "run_utc": iso(t0)}])
    jsave(STATUS, {"day": st["day"], "result": st["result"], "exit": code, "alert": ALERT.read_text().splitlines()})
    after = outside(porcelain())
    if after - before:
        print(f"FAILED WRITE_OUTSIDE_ALLOWED_PATHS: {sorted(after - before)[:5]}", file=sys.stderr)
        return EXIT["WRITE_OUTSIDE_ALLOWED_PATHS"]
    if not args.no_commit:
        try:
            commit(f"predictive-intel daily: {st['day']} {st['result']}", reason="COMMIT_FAILED")
        except Fail as e:
            print(f"FAILED {e.reason}: {e.detail}", file=sys.stderr)
            return EXIT["COMMIT_FAILED"]
    return code


def cmd_verify(_args) -> int:
    probs = []
    if LEDGER.exists():
        v = M.verify(LEDGER)
        probs += v["problems"]
    try:
        reg = registry()
        for i, e in reg["entries"].items():
            if (ENTRIES / f"{i}.json").exists() and json.loads((ENTRIES / f"{i}.json").read_text()) != e:
                probs.append(f"entry {i[:12]} file differs from its REGISTER event")
            if e.get("card_path") and fsha(REPO / e["card_path"]) != e["card_file_sha256"]:
                probs.append(f"card {e['card_path']} differs from its entry")
    except (P.LogError, ValueError) as e:
        probs.append(f"registry: {e}")
    for r in jl_read(READS):
        if r.get("file"):
            try:
                body_of(r)
            except Fail as e:
                probs.append(e.detail)
    print(json.dumps({"ok": not probs, "problems": probs[:20]}))
    return 0 if not probs else 1


def cmd_status(_args) -> int:
    print(ALERT.read_text() if ALERT.exists() else "no run yet")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="predictive_daily")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--state-dir")
    r.add_argument("--no-fetch", action="store_true")
    r.add_argument("--no-commit", action="store_true")
    r.add_argument("--max-calls", type=int, default=60)
    r.add_argument("--max-minutes", type=float, default=40.0)
    r.add_argument("--now", type=float)
    r.add_argument("--export-ref", default=EXPORT_REF)
    sub.add_parser("verify")
    sub.add_parser("status")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        if a.max_calls < 0 or a.max_calls > 300 or a.max_minutes <= 0 or a.max_minutes > 120:
            print("FAILED PREFLIGHT_FAILED: --max-calls must be 0 to 300 and --max-minutes above 0 and at most 120", file=sys.stderr)
            return EXIT["PREFLIGHT_FAILED"]
        return run(a)
    return {"verify": cmd_verify, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
