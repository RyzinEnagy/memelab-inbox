"""Phase 04 bake-off dataset: a real, timestamped development sample (BAKEOFF_ONLY, never a Phase 06 label set).

Decisions come from the state exports on main at REF through memelab/predictive/decisions.py (CC-02, PI-D-021). Features are
taken from the decision row and its token row in the export where the row first appears, so every feature is available at the
decision (available_at = decision_time = export commit time, PI-D-015). Labels follow the frozen registry: reference candle
(contract.reference_candle), eligibility class (contract.eligibility), path (contract.path_candles), barriers of T1 (24 h) and
T1b (6 h). Only development decisions are kept: decision before the holdout start and label maturity at or before it.

Holdout protection (Phase 01 seal, ACCEPTANCE holdout_seal and holdout_contacted):
  - every GeckoTerminal request ends at or before the holdout start (before_timestamp <= H0);
  - every returned candle that starts at or after H0 is dropped and counted;
  - no decision at or after H0 is labeled; the check at the end refuses the output otherwise.

Network: GeckoTerminal public OHLCV only, PIT_RECORDED pools only (no vendor pool lists), at most 6 calls a minute (PACE_S),
at most MAX_CALLS, HTTP 429 backoff, circuit breaker after 5 consecutive failures (ACCEPTANCE api_limits). Raw bodies go to
RAW_DIR outside the repository with their sha256; the call log (URL, retrieval time, HTTP status, bytes, sha256) is committed.

    python build_dev_sample.py plan  OUT_DIR
    python build_dev_sample.py fetch OUT_DIR RAW_DIR
    python build_dev_sample.py label OUT_DIR RAW_DIR
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import decisions as D  # noqa: E402

REF = "98338a8ba3c5e65c5850933a35c06885b6ef991a"     # origin/main as read by Phase 01 (split_counts.json "ref")
BASE = "https://api.geckoterminal.com/api/v2/networks/solana"
PACE_S = 10.5                                         # 5.7 calls a minute, under the frozen 6 (api_limits)
MAX_CALLS = C.ACCEPTANCE["api_limits"]["calls_per_run"]
BREAKER = C.ACCEPTANCE["api_limits"]["breaker_consecutive_failures"]
LIMIT = 1000
PERIOD = 300
H0 = C.parse_utc(C.ACCEPTANCE["holdout_window_utc"][0])
T24 = "price_path_target_before_invalidation_24h"
T6 = "price_path_target_before_invalidation_6h"
LOOKBACK = C.ACCEPTANCE["eligibility"]["quiet_route_lookback_s"]


def iso(t: float) -> str:
    return dt.datetime.fromtimestamp(float(t), dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*a: str) -> bytes:
    return subprocess.run(["git", *a], check=True, capture_output=True, cwd=REPO).stdout


def development_events() -> list[dict]:
    revs = [ln.split() for ln in git("rev-list", "--reverse", "--first-parent", "--timestamp", REF, "--",
                                     "data/state/latest.json").decode().splitlines() if ln.strip()]
    exports = [D.export_from_doc(s, int(t), json.loads(git("show", f"{s}:data/state/latest.json"))) for t, s in revs]
    tok_at = {}
    for ex in exports:
        for k in ex["tokens"]:
            tok_at[(ex["commit"], k["mint"])] = k
    evs = D.decisions(D.candidates(exports))
    out = []
    for e in evs:
        if e["chain"] != "solana" or not e["snapshot"].get("price") or not e["pool_pit"]:
            continue
        if e["decision_time"] >= H0 or C.label_matures_at(T6, e["decision_time"]) > H0:
            continue
        e = dict(e)
        tk = tok_at.get((e["commit"], e["mint"])) or {}
        e["first_pool_at"] = tk.get("first_pool_at")
        out.append(e)
    return out


def plan(out_dir: Path) -> dict:
    evs = development_events()
    by_pool = collections.defaultdict(list)
    for e in evs:
        by_pool[e["pool_pit"]].append(e["decision_time"])
    pools = []
    for p, ts in sorted(by_pool.items()):
        need_from = min(ts) - LOOKBACK - PERIOD
        need_to = min(max(ts) + 300 + 86400 + PERIOD, H0)
        pools.append({"pool": p, "events": len(ts), "need_from": need_from, "need_to": need_to})
    pl = {"ref": REF, "h0": iso(H0), "events": len(evs), "pools": pools}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "dev_sample_plan.json").write_text(json.dumps(pl, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"events": len(evs), "pools": len(pools)}))
    return pl


class Fetcher:
    def __init__(self, raw_dir: Path, log_path: Path):
        self.raw, self.log_path = raw_dir, log_path
        self.raw.mkdir(parents=True, exist_ok=True)
        self.calls = json.loads(log_path.read_text()) if log_path.exists() else []
        self.last = 0.0
        self.consecutive_failures = 0

    def get(self, url: str, tag: str) -> tuple[int, dict | None]:
        if len(self.calls) >= MAX_CALLS:
            raise SystemExit("call budget reached")
        if self.consecutive_failures >= BREAKER:
            raise SystemExit("circuit breaker open: 5 consecutive failures")
        wait = self.last + PACE_S - time.time()
        if wait > 0:
            time.sleep(wait)
        started = time.time()
        p = subprocess.run(["curl", "-sS", "-m", "60", "-o", "-", "-w", "\n%{http_code}", "-H",
                            "Accept: application/json;version=20230302", url], capture_output=True, timeout=90)
        self.last = time.time()
        body, _, code = p.stdout.rpartition(b"\n")
        try:
            code = int(code or 0)
        except ValueError:
            code = 0
        h = hashlib.sha256(body).hexdigest()
        n = len(self.calls)
        (self.raw / f"{n:04d}_{tag}.json").write_bytes(body)
        self.calls.append({"n": n, "tag": tag, "url": url, "retrieved_at": iso(started), "retrieved_t": started, "http": code,
                           "bytes": len(body), "sha256": h, "file": f"{n:04d}_{tag}.json"})
        self.log_path.write_text(json.dumps(self.calls, indent=1) + "\n")
        self.consecutive_failures = 0 if code == 200 else self.consecutive_failures + 1
        try:
            return code, json.loads(body) if code == 200 else None
        except ValueError:
            return code, None


def fetch(out_dir: Path, raw_dir: Path) -> None:
    pl = json.loads((out_dir / "dev_sample_plan.json").read_text())
    f = Fetcher(raw_dir, out_dir / "dev_sample_calls.json")
    done = {c["tag"] for c in f.calls if c["http"] == 200}
    for i, p in enumerate(pl["pools"]):
        before = int(p["need_to"])
        assert before <= H0, "request window past the holdout start"
        page = 0
        while True:
            tag = f"p{i:03d}_{page}"
            if tag in done:
                c = next(c for c in f.calls if c["tag"] == tag and c["http"] == 200)
                d = json.loads((raw_dir / c["file"]).read_bytes())
            else:
                url = f"{BASE}/pools/{p['pool']}/ohlcv/minute?aggregate=5&limit={LIMIT}&before_timestamp={before}&currency=usd"
                code, d, tries = None, None, 0
                while tries < 3:
                    code, d = f.get(url, tag)
                    tries += 1
                    if code == 429:
                        time.sleep(60)
                        continue
                    break
                if code != 200:
                    break
            lst = (((d or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
            if len(lst) < LIMIT or not lst:
                break
            earliest = min(int(c[0]) for c in lst)
            if earliest <= p["need_from"]:
                break
            before = earliest
            page += 1
    print(json.dumps({"calls": len(f.calls), "http": dict(collections.Counter(c["http"] for c in f.calls))}))


def barrier_class(target: str, candles: list, decision_time: float, p0: float) -> tuple[str, float]:
    """Class and the time (s after t_entry) at which it is known: the end of the first touching candle, else the horizon."""
    t = C.TARGETS[target]
    up, dn = t["upper"] * p0, t["lower"] * p0
    t_entry = decision_time + 300
    path = C.path_candles(candles, decision_time, t["horizon_s"])
    if not path:
        return "NO_TRADES_AFTER_ENTRY", float(t["horizon_s"])
    for c in path:
        hi, lo = float(c[2]), float(c[3])
        end = float(c[0]) + PERIOD - t_entry
        if hi >= up and lo <= dn:
            return "AMBIGUOUS_BAR", end
        if hi >= up:
            return "TARGET_FIRST", end
        if lo <= dn:
            return "INVALIDATION_FIRST", end
    return "NEITHER", float(t["horizon_s"])


def _f(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def _log(x):
    x = _f(x)
    return math.log10(x) if x is not None and x > 0 else None


def features(e: dict) -> dict:
    s = e["snapshot"]
    fp = e.get("first_pool_at")          # ISO 8601 text in the token row (normalize.py:81), sometimes absent
    try:
        fp = (dt.datetime.fromisoformat(fp.replace("Z", "+00:00")).timestamp() if isinstance(fp, str) and fp
              else float(fp) if isinstance(fp, (int, float)) else None)
    except (TypeError, ValueError):
        fp = None
    age_h = (e["decision_time"] - fp) / 3600 if fp is not None and fp <= e["decision_time"] else None
    status = e.get("status") or ""
    return {"log_liquidity": _log(s.get("liquidity")), "log_mcap": _log(s.get("mcap")), "log_vol_24h": _log(s.get("vol_24h")),
            "log_age_h": math.log10(age_h + 1) if age_h is not None else None,
            "fatal_flag": 1 if (s.get("fatal") or (e.get("fatal_flags_json") not in (None, "", "[]"))) else 0,
            "status_rejected": 1 if status == "REJECTED" else 0, "score": _f(e.get("score")),
            "adj_top10": _f(s.get("adj_top10")), "net_buyers_24h": _f(s.get("net_buyers_24h"))}


def label(out_dir: Path, raw_dir: Path) -> None:
    pl = json.loads((out_dir / "dev_sample_plan.json").read_text())
    calls = json.loads((out_dir / "dev_sample_calls.json").read_text())
    by_tag = {}
    for c in calls:
        if c["http"] == 200:
            by_tag[c["tag"]] = c
    candles_by_pool, read_ok, retrieved, dropped_after_h0 = {}, {}, {}, 0
    for i, p in enumerate(pl["pools"]):
        rows, page, ok = {}, 0, False
        while f"p{i:03d}_{page}" in by_tag:
            c = by_tag[f"p{i:03d}_{page}"]
            d = json.loads((raw_dir / c["file"]).read_bytes())
            if hashlib.sha256((raw_dir / c["file"]).read_bytes()).hexdigest() != c["sha256"]:
                raise SystemExit(f"raw body {c['file']} changed since retrieval")
            for r in d["data"]["attributes"]["ohlcv_list"]:
                if int(r[0]) >= H0:
                    dropped_after_h0 += 1
                    continue
                rows[int(r[0])] = r
            retrieved[p["pool"]] = max(retrieved.get(p["pool"], 0), c["retrieved_t"])
            ok = True
            page += 1
        candles_by_pool[p["pool"]] = sorted(rows.values(), key=lambda r: r[0])
        read_ok[p["pool"]] = ok
    evs = development_events()
    assert len(evs) == pl["events"], "decision universe changed since the plan"
    elig_counts = collections.Counter()
    base = []
    for e in evs:
        cs = candles_by_pool.get(e["pool_pit"])
        ok = read_ok.get(e["pool_pit"], False)
        cls = C.eligibility(cs if ok else None, e["decision_time"], read_ok=ok, pool=e["pool_pit"], route="PIT_RECORDED",
                            snapshot_vol_24h=e["snapshot"].get("vol_24h"))
        elig_counts[cls] += 1
        e = dict(e, eligibility=cls)
        base.append(e)
    summary = {"ref": REF, "h0": iso(H0), "events_development_pit": len(evs), "eligibility_unthinned": dict(elig_counts),
               "candles_dropped_at_or_after_h0": dropped_after_h0, "calls": len(calls),
               "calls_http": dict(collections.Counter(c["http"] for c in calls)), "targets": {}}
    for target, fname in ((T24, "dev_t1_24h.csv"), (T6, "dev_t1b_6h.csv")):
        dev = [e for e in base if C.label_matures_at(target, e["decision_time"]) <= H0]
        elig = [e for e in dev if e["eligibility"] == "ELIGIBLE"]
        kept = D.thin(elig, C.TARGETS[target]["horizon_s"])
        rows = []
        for e in kept:
            cs = candles_by_pool[e["pool_pit"]]
            ref = C.reference_candle(cs, e["decision_time"], max_age_s=C.ACCEPTANCE["eligibility"]["reference_max_age_s"])
            p0 = float(ref[4])
            klass, t_known = barrier_class(target, cs, e["decision_time"], p0)
            mat = C.label_matures_at(target, e["decision_time"])
            obs = retrieved[e["pool_pit"]]
            assert e["decision_time"] < H0 and mat <= H0 and obs >= mat
            row = {"event_id": hashlib.sha256(f"{e['mint']}|{e['created_at']}|{e['row_sha256']}".encode()).hexdigest()[:16],
                   "mint": e["mint"], "pool": e["pool_pit"], "commit": e["commit"][:12], "decision_time": e["decision_time"],
                   "decision_time_utc": iso(e["decision_time"]), "feature_available_at": e["decision_time"],
                   "label_matures_at": mat, "label_observed_at": round(obs, 3), "p0_candle_start": int(ref[0]),
                   "key_conflict": 1 if "KEY_CONFLICT" in e["flags"] else 0, **features(e),
                   "label_class": klass, "y": 1 if klass in C.TARGETS[target]["positive"] else 0, "event_time_s": t_known,
                   "use": "BAKEOFF_ONLY"}
            rows.append(row)
        rows.sort(key=lambda r: (r["decision_time"], r["mint"]))
        with open(out_dir / fname, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        summary["targets"][target] = {"file": fname, "development_unthinned": len(dev), "eligible_unthinned": len(elig),
                                      "thinned_events": len(rows), "positives": sum(r["y"] for r in rows),
                                      "classes": dict(collections.Counter(r["label_class"] for r in rows)),
                                      "decision_days": len({r["decision_time_utc"][:10] for r in rows}),
                                      "mints": len({r["mint"] for r in rows}),
                                      "first_decision_utc": rows[0]["decision_time_utc"], "last_decision_utc": rows[-1]["decision_time_utc"],
                                      "max_label_matures_at_utc": iso(max(r["label_matures_at"] for r in rows))}
    # holdout seal check
    contacted = {m for m, _ in C.ACCEPTANCE["holdout_contacted"]["decisions"]}
    for target in (T24, T6):
        with open(out_dir / summary["targets"][target]["file"]) as fh:
            for r in csv.DictReader(fh):
                assert float(r["decision_time"]) < H0, "holdout decision in the bake-off set"
                assert float(r["label_matures_at"]) <= H0, "label matures inside the holdout window"
    summary["holdout_check"] = {"decisions_at_or_after_h0": 0, "labels_maturing_after_h0": 0,
                                "contacted_mints_with_development_rows": sorted(m[:6] for m in contacted
                                                                                if any(e["mint"] == m for e in evs))}
    (out_dir / "dev_sample_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=1, sort_keys=True))


if __name__ == "__main__":
    cmd, out = sys.argv[1], Path(sys.argv[2])
    if cmd == "plan":
        plan(out)
    elif cmd == "fetch":
        fetch(out, Path(sys.argv[3]))
    elif cmd == "label":
        label(out, Path(sys.argv[3]))
    else:
        raise SystemExit(__doc__)
