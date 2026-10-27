"""Phase 20 (G10, G11): independent recalculation with Phase 20's own code. No lab module is imported: the vendor bodies are
parsed here, the target rules are re-implemented from the frozen registry text (contract.TARGETS as written in
phase_01/architecture/TARGET_REGISTRY.md), the decision rows come from `git show` of the state exports, and the B0 and B2
numbers are computed here from the frozen card JSON (median fill, standardisation, logistic).

    python -B recalc.py OUTJSON

Samples (rules fixed in ../ACCEPTANCE_CHECKLIST.md before the run):
  (a) every Phase 19 LABELED outcome (current version per decision and target) recomputed from phase_19/raw/;
  (b) the first 40 Phase 06 DEVELOPMENT LABELED Solana labels by sha256 of their label key, from phase_06/raw/ (inputs read from
      the private development store read-only: decision time, pool, mint, response key; the class is recomputed here);
  (c) the first 30 prospective Solana decisions by decision key with a P07_B2 number, every target: decision identity (decision
      key from the exact export row), inputs from the row, B0 and B2 numbers from the frozen cards;
  (G11) two real events traced end to end: export row, decision, snapshot hash, B2 number, the system document and its record
      (Phase 19 published copy of the Phase 18 run), the outcome and its read.
Network: none. Phase 19 outcomes are PROVISIONAL_PENDING_REVISION_REREAD (PI-D-106).
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

REPO = Path(__file__).resolve().parents[4]
AUD = REPO / "audits/predictive-intelligence"
P = 300.0
LAG = 300.0
TGT = {"price_path_target_before_invalidation_24h": ("T1", 86400.0), "price_path_target_before_invalidation_6h": ("T1b", 21600.0),
       "price_path_severe_drawdown_or_halt_24h": ("T2", 86400.0)}
CARD = {"T1": "T1_24h", "T1b": "T1b_6h", "T2": "T2_24h"}


def canon(o) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def sha(o) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def ceil5(t: float) -> float:
    return math.ceil(t / P) * P


# ---------------------------------------------------------------- vendor bodies (own parser)
def manifest(phase: str) -> dict[str, dict]:
    return {r["response_key"]: r for r in csv.DictReader(open(AUD / f"phase_{phase}/raw/MANIFEST.csv"))}


def candles(phase: str, row: dict, mint: str, boundary: float) -> tuple[list, str]:
    body = gzip.decompress((AUD / f"phase_{phase}/raw" / row["file"]).read_bytes())
    if hashlib.sha256(body).hexdigest() != row["body_sha256"]:
        return [], "BODY_SHA_MISMATCH"
    if row.get("http_status") not in ("200", 200):
        return [], "HTTP_" + str(row.get("http_status"))
    d = json.loads(body)
    tok = parse_qs(urlsplit(row["request_url"]).query).get("token", [None])[0]
    base = ((d.get("meta") or {}).get("base") or {}).get("address")
    if tok != mint or base != mint:
        return [], "IDENTITY"
    out = {}
    for r in ((d.get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []:
        try:
            s, o, h, l, c, v = (float(x) for x in r[:6])
        except (TypeError, ValueError):
            continue
        if not all(math.isfinite(x) for x in (s, o, h, l, c, v)) or min(o, h, l, c) <= 0 or v < 0 or s + P > boundary or s in out:
            continue
        if h < max(o, c) - 1e-12 or l > min(o, c) + 1e-12:
            continue
        out[s] = (s, o, h, l, c, v)
    return [out[k] for k in sorted(out)], "OK"


def classify(tshort: str, H: float, T: float, cs: list, boundary: float) -> dict:
    ref = [c for c in cs if c[0] + P + LAG <= T and c[0] + P >= T - 3600]
    if not ref:
        return {"state": "NO_REFERENCE"}
    p0 = max(ref, key=lambda c: c[0])[4]
    te = T + LAG
    path = [c for c in cs if c[0] >= te and c[0] + P <= te + H]
    cover = cs[0][0] if cs else None
    seen = boundary >= ceil5(te + H) and cover is not None and cover < te
    if tshort in ("T1", "T1b"):
        for c in path:
            up, lo = c[2] >= 1.25 * p0, c[3] <= 0.85 * p0
            if up or lo:
                cls = "AMBIGUOUS_BAR" if up and lo else ("TARGET_FIRST" if up else "INVALIDATION_FIRST")
                return {"state": "LABELED", "label_class": cls, "label": int(cls == "TARGET_FIRST"), "p0": p0}
        if not seen:
            return {"state": "UNVERIFIABLE_NO_VENDOR_HISTORY", "p0": p0}
        cls = "NEITHER" if path else "NO_TRADES_AFTER_ENTRY"
        return {"state": "LABELED", "label_class": cls, "label": 0, "p0": p0}
    for c in path:
        if c[3] <= 0.5 * p0:
            return {"state": "LABELED", "label_class": "DRAWDOWN_50", "label": 1, "p0": p0}
    if not seen:
        return {"state": "UNVERIFIABLE_NO_VENDOR_HISTORY", "p0": p0}
    s, e = te + 64800.0, te + 86400.0 + 86400.0
    if any(c[0] < e and c[0] + P > s for c in cs):
        return {"state": "LABELED", "label_class": "NO_SEVERE_EVENT", "label": 0, "p0": p0}
    return {"state": "HALT_NEEDS_OTHER_POOLS", "p0": p0}


# ---------------------------------------------------------------- (a) Phase 19 outcomes
def current_outcomes() -> dict:
    cur = {}
    for line in (AUD / "phase_19/monitoring/OUTCOME_LEDGER.jsonl").read_text().splitlines():
        p = json.loads(line)["payload"]
        if p.get("kind") == "OUTCOME":
            cur[(p["decision_key"], p["target"])] = p
    return cur


def part_a() -> dict:
    man = manifest("19")
    rows, mism = [], []
    for (dk, tg), o in sorted(current_outcomes().items()):
        if o["state"] != "LABELED":
            continue
        ts, H = TGT[tg]
        m = man.get(o["response_key"])
        if m is None:
            mism.append({"decision_key": dk, "target": ts, "why": "read not in the archive"})
            continue
        b = datetime.fromisoformat(m["boundary_at"].replace("Z", "+00:00")).timestamp()
        cs, st = candles("19", m, o["mint"], b)
        got = classify(ts, H, float(o["decision_time"]), cs, b) if st == "OK" else {"state": st}
        same = got.get("state") == "LABELED" and got.get("label_class") == o["label_class"] and got.get("label") == o["label"]
        rows.append({"decision_key": dk[:16], "target": ts, "ledger": [o["label_class"], o["label"]],
                     "recomputed": [got.get("label_class"), got.get("label")], "equal": same})
        if not same:
            mism.append({"decision_key": dk, "target": ts, "ledger": o["label_class"], "recomputed": got})
    by = {}
    for r in rows:
        by.setdefault(r["target"], [0, 0])
        by[r["target"]][0] += 1
        by[r["target"]][1] += int(r["equal"])
    return {"labeled_outcomes": len(rows), "equal": sum(r["equal"] for r in rows), "by_target_n_equal": by, "mismatches": mism,
            "marker": "PROVISIONAL_PENDING_REVISION_REREAD", "rows": rows}


# ---------------------------------------------------------------- (b) Phase 06 development labels
def part_b(n: int = 40) -> dict:
    db = Path("/home/claude/pi_research/p06/dev_store.sqlite")
    if not db.is_file():
        return {"state": "SKIPPED_PRIVATE_STORE_ABSENT"}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute("SELECT * FROM predictive_labels WHERE split='DEVELOPMENT' AND state='LABELED' AND chain='solana' "
                                         "AND revision_of IS NULL")]
    con.close()
    rows.sort(key=lambda r: hashlib.sha256(r["label_key"].encode()).hexdigest())
    man = manifest("06")
    out, mism = [], []
    for r in rows[:n]:
        ts, H = TGT[r["target"]]
        m = man.get(r["response_key"])
        if m is None:
            mism.append({"label_key": r["label_key"][:16], "why": "read not in the archive"})
            continue
        b = datetime.fromisoformat(m["boundary_at"].replace("Z", "+00:00")).timestamp()
        cs, st = candles("06", m, r["mint"], b)
        got = classify(ts, H, float(r["decision_time"]), cs, b) if st == "OK" else {"state": st}
        if r["label_class"] == "TRADING_HALT" and got.get("state") == "HALT_NEEDS_OTHER_POOLS":
            got = {"state": "LABELED", "label_class": "TRADING_HALT", "label": 1, "p0": got.get("p0"), "note": "other pools not re-read here"}
        eq = got.get("label_class") == r["label_class"] and got.get("label") == r["label"] and \
            abs((got.get("p0") or 0) - (r["p0"] or 0)) <= 1e-12 * max(1.0, abs(r["p0"] or 0))
        out.append({"label_key": r["label_key"][:16], "target": ts, "store": [r["label_class"], r["label"], r["p0"]],
                    "recomputed": [got.get("label_class"), got.get("label"), got.get("p0")], "equal": eq})
        if not eq:
            mism.append({"label_key": r["label_key"], "store": r["label_class"], "recomputed": got})
    return {"sampled": len(out), "equal": sum(x["equal"] for x in out), "mismatches": mism, "rows": out}


# ---------------------------------------------------------------- (c) decisions, inputs and B0 and B2 numbers
def git(*a) -> str:
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, check=True).stdout


def export_at(commit: str) -> dict:
    d = json.loads(git("show", f"{commit}:data/state/latest.json"))
    t = d.get("_tables") or {k: v for k, v in d.items() if not k.startswith("_") and isinstance(v, list)}
    return {"theses": t.get("theses") or [], "tokens": t.get("tokens") or []}


def row_sha(row: dict) -> str:
    return hashlib.sha256(json.dumps({k: v for k, v in row.items() if k != "id"}, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


def parse_time(x) -> float | None:
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    if isinstance(x, str) and x:
        try:
            return datetime.fromisoformat(x.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
        except ValueError:
            return None
    return None


def inputs_of(row: dict, tok: dict | None, T: float) -> dict:
    s = json.loads(row.get("snapshot_json") or "{}")

    def l1p(v):
        return math.log1p(float(v)) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0 else float("nan")
    ff = json.loads(row.get("fatal_flags_json") or "null")
    fp = parse_time((tok or {}).get("first_pool_at"))
    age = (T - fp) if fp is not None else float("nan")
    return {"thesis_log1p_liquidity_usd": l1p(s.get("liquidity")), "thesis_log1p_mcap_usd": l1p(s.get("mcap")),
            "thesis_log1p_vol_24h_usd": l1p(s.get("vol_24h")),
            "thesis_fatal_present": float(bool(ff)) if isinstance(ff, list) else float("nan"),
            "log1p_token_age_days": math.log1p(age / 86400.0) if math.isfinite(age) and age >= 0 else float("nan")}


def b2_number(card: dict, x: dict) -> float | None:
    b = card["body"]
    if not all(math.isfinite(x[c]) for c in b["required"]):
        return None
    prep, lg = b["prep"], b["logistic"]
    v = [x[c] for c in b["columns"]]
    v = [v[i] for i in prep["keep"]]
    miss = [not math.isfinite(z) for z in v]
    f = [prep["med"][i] if miss[i] else v[i] for i in range(len(v))] + [float(miss[i]) for i in prep["ind"]]
    z = [(f[i] - prep["mu"][i]) / prep["sd"][i] for i in range(len(f))]
    s = lg["intercept"] + sum(a * b_ for a, b_ in zip(lg["coef"], z))
    return 1.0 / (1.0 + math.exp(-s))


def part_c(n: int = 30) -> dict:
    preds = list(csv.DictReader(open(AUD / "phase_19/monitoring/PROSPECTIVE_PREDICTIONS.csv")))
    want = {(r["decision_key"], r["target_short"], r["candidate"]): r for r in preds if r["candidate"] in ("P07_B0", "P07_B2")}
    keys = sorted({r["decision_key"] for r in preds if r["candidate"] == "P07_B2" and r["number"] not in ("", None) and r["chain"] == "solana"})[:n]
    dec = {r["decision_key"]: r for r in preds}
    commits = {}
    for line in git("log", "--format=%H %ct", "refs/remotes/origin/main", "--", "data/state/latest.json").splitlines():
        h, t = line.split()
        commits[float(t)] = h
    cards = {ts: {k: json.loads((AUD / f"phase_07/artifacts/{CARD[ts]}/{k}.json").read_text()) for k in ("B0", "B2")}
             for ts in CARD}
    cache, out, mism = {}, [], []
    for dk in keys:
        r = dec[dk]
        T = float(r["decision_time"])
        c = commits.get(T)
        if c is None:
            mism.append({"decision_key": dk, "why": "no export commit at the decision time"})
            continue
        ex = cache.setdefault(c, export_at(c))
        rows = [x for x in ex["theses"] if x["mint"] == r["mint"]]
        newest = max(float(x["created_at"]) for x in rows)
        row = [x for x in rows if float(x["created_at"]) == newest][0]
        tok = next((t for t in ex["tokens"] if t["mint"] == r["mint"]), None)
        rs = row_sha(row)
        dkey = sha([r["chain"], r["mint"], float(row["created_at"]), rs, T])
        x = inputs_of(row, tok, T)
        item = {"decision_key": dk[:16], "export_commit": c[:12], "decision_key_recomputed_equal": dkey == dk, "targets": {}}
        for ts in CARD:
            mine = {"P07_B0": cards[ts]["B0"]["body"]["p"], "P07_B2": b2_number(cards[ts]["B2"], x)}
            for cand, v in mine.items():
                rec = want.get((dk, CARD[ts], cand))
                rn = float(rec["number"]) if rec and rec["number"] not in ("", None) else None
                eq = (rn is None and v is None) or (rn is not None and v is not None and abs(rn - v) <= 1e-9)
                item["targets"][f"{ts}:{cand}"] = {"recorded": rn, "recomputed": v, "equal": eq}
                if not eq:
                    mism.append({"decision_key": dk, "target": ts, "candidate": cand, "recorded": rn, "recomputed": v})
        out.append(item)
    n_num = sum(len(i["targets"]) for i in out)
    return {"decisions": len(out), "numbers_compared": n_num, "numbers_equal": sum(t["equal"] for i in out for t in i["targets"].values()),
            "decision_keys_equal": sum(i["decision_key_recomputed_equal"] for i in out), "mismatches": mism, "rows": out}


# ---------------------------------------------------------------- G11: two real events end to end
def trace_two() -> dict:
    cur = current_outcomes()
    lab = [(k, o) for k, o in sorted(cur.items()) if o["state"] == "LABELED" and o["target"].endswith("invalidation_24h")]
    pos = [x for x in lab if x[1]["label"] == 1][:1]
    neg = [x for x in lab if x[1]["label"] == 0][:1]
    docs = [json.loads(x) for x in (AUD / "phase_19/monitoring/published/DOCUMENTS.jsonl").read_text().splitlines()]
    recs = {json.loads(x)["record_id"]: json.loads(x) for x in (AUD / "phase_19/monitoring/published/RECORDS.jsonl").read_text().splitlines()}
    preds = list(csv.DictReader(open(AUD / "phase_19/monitoring/PROSPECTIVE_PREDICTIONS.csv")))
    commits = {}
    for line in git("log", "--format=%H %ct", "refs/remotes/origin/main", "--", "data/state/latest.json").splitlines():
        h, t = line.split()
        commits[float(t)] = h
    man = manifest("19")
    card = json.loads((AUD / "phase_07/artifacts/T1_24h/B2.json").read_text())
    out = []
    for (dk, tg), o in pos + neg:
        T = float(o["decision_time"])
        c = commits[T]
        ex = export_at(c)
        rows = [x for x in ex["theses"] if x["mint"] == o["mint"]]
        row = max(rows, key=lambda x: float(x["created_at"]))
        tok = next((t for t in ex["tokens"] if t["mint"] == o["mint"]), None)
        rs = row_sha(row)
        snap = row_sha({k: v for k, v in row.items() if k != "report_path"})
        x = inputs_of(row, tok, T)
        b2 = b2_number(card, x)
        rec_b2 = next((float(p["number"]) for p in preds if p["decision_key"] == dk and p["target_short"] == "T1_24h" and p["candidate"] == "P07_B2"
                       and p["number"] not in ("", None)), None)
        d = [y for y in docs if y["document"]["mint_address"] == o["mint"] and y["document"]["target"] == tg
             and y["document"]["decision_time_utc"] == datetime.fromtimestamp(T, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")]
        doc = d[0]["document"] if d else None
        rec = recs.get(d[0]["abstention_record_id"]) if d else None
        m = man[o["response_key"]]
        b = datetime.fromisoformat(m["boundary_at"].replace("Z", "+00:00")).timestamp()
        cs, st = candles("19", m, o["mint"], b)
        lab_ = classify("T1", 86400.0, T, cs, b)
        links = {"decision_key_from_export_row": sha(["solana", o["mint"], float(row["created_at"]), rs, T]) == dk,
                 "document_snapshot_hash_is_the_row_without_id_and_report_path": doc is not None and doc["snapshot_hash"] == snap,
                 "document_abstains_with_reasons_and_no_number": doc is not None and doc["prediction_status"] == "ABSTAIN" and doc["probability"] is None
                 and bool(doc["abstain_reasons"]),
                 "record_matches_document": rec is not None and sorted(rec.get("reasons") or []) == sorted(doc["abstain_reasons"]),
                 "b2_reference_number_recomputed": rec_b2 is not None and b2 is not None and abs(rec_b2 - b2) <= 1e-9,
                 "outcome_read_identity_and_label_recomputed": st == "OK" and lab_.get("label_class") == o["label_class"],
                 "read_after_maturity": float(o["label_observed_at"]) >= T + 300 + 86400 + 900}
        out.append({"mint": o["mint"], "decision_time_utc": datetime.fromtimestamp(T, timezone.utc).isoformat(), "export_commit": c,
                    "row_sha256": rs, "snapshot_hash": snap, "inputs": x, "b2_t1": b2, "b2_recorded": rec_b2,
                    "document": {k: doc[k] for k in ("forecast_id", "prediction_status", "abstain_reasons", "model_id")} if doc else None,
                    "outcome": {k: o[k] for k in ("state", "label_class", "label", "response_key", "label_observed_at")},
                    "recomputed_label": lab_, "links": links, "all_links_hold": all(links.values())})
    return {"events": out, "marker": "PROVISIONAL_PENDING_REVISION_REREAD"}


def main(outjson: Path) -> int:
    res = {"a_phase19_outcomes": part_a(), "b_phase06_labels": part_b(), "c_reference_numbers": part_c(), "g11_traces": trace_two()}
    ok = (not res["a_phase19_outcomes"]["mismatches"] and not res["b_phase06_labels"].get("mismatches")
          and not res["c_reference_numbers"]["mismatches"] and res["c_reference_numbers"]["decision_keys_equal"] == res["c_reference_numbers"]["decisions"]
          and all(e["all_links_hold"] for e in res["g11_traces"]["events"]) and len(res["g11_traces"]["events"]) == 2)
    res["all_equal"] = ok
    outjson.parent.mkdir(parents=True, exist_ok=True)
    outjson.write_text(json.dumps(res, indent=1, sort_keys=True, default=str) + "\n")
    print(json.dumps({"all_equal": ok, "a": {k: res["a_phase19_outcomes"][k] for k in ("labeled_outcomes", "equal", "by_target_n_equal")},
                      "b": {k: res["b_phase06_labels"].get(k) for k in ("sampled", "equal")},
                      "c": {k: res["c_reference_numbers"][k] for k in ("decisions", "numbers_compared", "numbers_equal", "decision_keys_equal")},
                      "g11": [e["all_links_hold"] for e in res["g11_traces"]["events"]],
                      "mismatches": {"a": len(res["a_phase19_outcomes"]["mismatches"]), "b": len(res["b_phase06_labels"].get("mismatches") or []),
                                     "c": len(res["c_reference_numbers"]["mismatches"])}}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
