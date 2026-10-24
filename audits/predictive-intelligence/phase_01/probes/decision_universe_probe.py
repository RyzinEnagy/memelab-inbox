"""Phase 01 probe: how many eligible, time-correct decision events the lab's real history can supply.

Read-only. No network. Walks every version of data/state/latest.json on a ref OLDEST FIRST (so the first export that
contains a thesis is known), and reports:
  - the gap between theses.created_at and the commit time of the first export holding the thesis (the provable
    public availability time, PI-D-008), next to the write-lag lower bound from tokens.first_seen_at (PI-D-011);
  - optional cross-check of export commit times against GitHub push events (server clock), from a JSON file;
  - per chain, how many thesis mints carry a point-in-time pool address (tokens.graduated_pool / primary_pool as of
    the first export holding the thesis);
  - decision events after thinning to non-overlapping label windows per mint for 6 h, 24 h and 7 d, by UTC day and by
    status, and how many have matured by the data end;
  - how many 24 h decisions have a follow-up thesis snapshot 20 to 28 h later with exit capacity (the only historical
    executable-depth measure), i.e. whether a liquidity-degradation label is measurable from what exists;
  - launch cohort size, platforms, first_seen window and outcome fill (newest row per mint).

Usage (repo root):
    python audits/predictive-intelligence/phase_01/probes/decision_universe_probe.py origin/main OUT.json [PUSH_EVENTS.json]

Writes only OUT.json (keep it outside the repo or under the phase folder). This is a planning probe, NOT a label builder:
it computes no outcome and reads no price after a decision.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import statistics
import subprocess
import sys

DELAY_S = 7200          # PI-D-011 rule 1 alternative: at least the observed max write lag (116.5 min), rounded up to 2 h (reported only)
EXEC_LAG_S = 300        # outcomes_core DEFAULT_POLICY execution_lag_s
HORIZONS = {"6h": 21600, "24h": 86400, "7d": 604800}


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def iso(t):
    return None if t is None else dt.datetime.fromtimestamp(float(t), dt.UTC).strftime("%Y-%m-%dT%H:%MZ")


def pct(xs, qs=(0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)):
    xs = sorted(xs)
    if not xs:
        return None
    out = {}
    for q in qs:
        i = min(len(xs) - 1, max(0, round(q * (len(xs) - 1))))
        out[f"p{int(q * 100)}"] = round(xs[i], 2)
    out["n"] = len(xs)
    return out


def thin(times: list[float], h: float) -> list[float]:
    """Keep a decision only when it is at least h after the previous kept one (non-overlapping label windows)."""
    kept, last = [], None
    for t in sorted(times):
        if last is None or t >= last + h:
            kept.append(t)
            last = t
    return kept


def main(ref: str, out: str, push_path: str | None = None) -> None:
    log = [ln.split() for ln in git("log", "--reverse", "--format=%H %ct", ref, "--", "data/state/latest.json").decode().splitlines() if ln.strip()]
    theses: dict[tuple[str, float], dict] = {}
    tok_first: dict[str, dict] = {}       # token row as of the first export that holds the mint
    tok_first_seen: dict[str, float] = {}
    cohort: dict[str, dict] = {}
    cohort_first_commit: dict[str, int] = {}
    exported_at: dict[str, float] = {}
    for sha, ct in log:
        ct = int(ct)
        doc = json.loads(git("show", f"{sha}:data/state/latest.json"))
        tables = doc.get("_tables") or {k: v for k, v in doc.items() if isinstance(v, list)}
        if doc.get("_exported_at"):
            exported_at[sha] = float(doc["_exported_at"])
        toks = {t["mint"]: t for t in tables.get("tokens") or []}
        for m, t in toks.items():
            tok_first.setdefault(m, dict(t, _commit=sha, _commit_t=ct))
            if t.get("first_seen_at") is not None:
                tok_first_seen[m] = min(tok_first_seen.get(m, float("inf")), float(t["first_seen_at"]))
        for th in tables.get("theses") or []:
            key = (th["mint"], float(th["created_at"]))
            if key in theses:
                continue
            try:
                s = json.loads(th.get("snapshot_json") or "{}")
            except Exception:
                s = {}
            tk = toks.get(th["mint"]) or {}
            theses[key] = {"mint": th["mint"], "created_at": float(th["created_at"]), "commit": sha, "commit_t": ct,
                           "exported_at": doc.get("_exported_at"), "status": th.get("status"), "score": th.get("score"),
                           "chain": tk.get("chain") or "solana", "pool_pit": tk.get("primary_pool") or tk.get("graduated_pool"),
                           "price": s.get("price"), "liquidity": s.get("liquidity"), "exit_cap_3pct": s.get("exit_cap_3pct")}
        for c in tables.get("launch_cohort") or []:
            cohort[c["mint"]] = c                    # newest row wins (oldest-first walk), skeptic F2 of Phase 00
            cohort_first_commit.setdefault(c["mint"], ct)
    res: dict = {"ref": ref, "ref_sha": git("rev-parse", ref).decode().strip(), "export_versions": len(log),
                 "rules": {"decision_delay_s": DELAY_S, "execution_lag_s": EXEC_LAG_S, "horizons_s": HORIZONS,
                           "decision_time": "commit time of the first export holding the thesis (provable: the row is inside the commit)",
                           "alternative_reported": "created_at + delay"}}
    data_end = max(int(ct) for _s, ct in log)
    res["data_end"] = iso(data_end)
    rows = sorted(theses.values(), key=lambda r: (r["mint"], r["created_at"]))
    # clocks
    lag_commit = [(r["commit_t"] - r["created_at"]) / 60 for r in rows]
    neg = sum(1 for x in lag_commit if x < 0)
    first_by_mint = {}
    for r in rows:
        first_by_mint.setdefault(r["mint"], r)
    write_lag = [(tok_first_seen[m] - r["created_at"]) / 60 for m, r in first_by_mint.items() if m in tok_first_seen and tok_first_seen[m] > r["created_at"]]
    res["clocks"] = {"theses": len(rows), "mints": len(first_by_mint),
                     "commit_minus_created_min": pct(lag_commit), "commit_before_created": neg,
                     "first_thesis_write_lag_min_lower_bound": pct(write_lag),
                     "commit_minus_created_under_delay": sum(1 for x in lag_commit if x * 60 < DELAY_S),
                     "commit_minus_first_seen_min_for_first_thesis": pct([(r["commit_t"] - tok_first_seen[m]) / 60 for m, r in first_by_mint.items() if m in tok_first_seen])}
    if push_path:
        push = json.load(open(push_path))
        by_head = {}
        for p in push:
            if p.get("ref") == "refs/heads/main" and p.get("head"):
                t = dt.datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")).timestamp()
                by_head[p["head"]] = min(by_head.get(p["head"], float("inf")), t)
        diffs = [by_head[s] - int(ct) for s, ct in log if s in by_head]
        res["clocks"]["push_minus_commit_s"] = pct(diffs) if diffs else None
        res["clocks"]["export_commits_with_push_event"] = len(diffs)
    # universe by chain and pool address
    chain_mints = collections.Counter(r["chain"] for r in first_by_mint.values())
    pool_pit = collections.Counter((r["chain"], bool(r["pool_pit"])) for r in first_by_mint.values())
    priced = collections.Counter(r["chain"] for r in first_by_mint.values()
                                 if any(x["price"] for x in rows if x["mint"] == r["mint"]))
    res["universe"] = {"mints_by_chain": dict(chain_mints), "mints_with_pit_pool_by_chain": {f"{c}:{'pool' if b else 'no_pool'}": n for (c, b), n in pool_pit.items()},
                       "mints_with_a_priced_thesis_by_chain": dict(priced),
                       "thesis_status_all": dict(collections.Counter(r["status"] for r in rows))}
    # decision events
    for r in rows:
        r["decision_t"] = r["commit_t"]
    by_mint = collections.defaultdict(list)
    for r in rows:
        if r["chain"] == "solana" and r["price"]:
            by_mint[r["mint"]].append(r)
    events = {}
    for name, h in HORIZONS.items():
        kept = []
        for m, lst in by_mint.items():
            ts = thin([x["decision_t"] for x in lst], h)
            idx = {x["decision_t"]: x for x in lst}
            kept += [idx[t] for t in ts]
        matured = [x for x in kept if x["decision_t"] + EXEC_LAG_S + h <= data_end]
        days = collections.Counter(iso(x["decision_t"])[:10] for x in matured)
        if name == "24h":
            res["_events_24h_list"] = [{"mint": x["mint"], "created_at": x["created_at"], "decision_t": x["decision_t"], "commit": x["commit"],
                                        "pool_pit": x["pool_pit"], "status": x["status"]} for x in sorted(matured, key=lambda x: (x["decision_t"], x["mint"]))]
        events[name] = {"decisions_after_thinning": len(kept), "matured_by_data_end": len(matured),
                        "mints": len({x["mint"] for x in matured}), "with_pit_pool": sum(1 for x in matured if x["pool_pit"]),
                        "status": dict(collections.Counter(x["status"] for x in matured)),
                        "by_day": dict(sorted(days.items())),
                        "first_decision_per_mint_only": len({x["mint"] for x in matured})}
    res["events_solana_priced"] = events
    # liquidity-degradation measurability from snapshots
    h24 = HORIZONS["24h"]
    kept24 = []
    for m, lst in by_mint.items():
        ts = set(thin([x["decision_t"] for x in lst], h24))
        kept24 += [x for x in lst if x["decision_t"] in ts]
    follow = 0
    for x in kept24:
        later = [y for y in by_mint[x["mint"]] if x["created_at"] + 20 * 3600 <= y["created_at"] <= x["created_at"] + 28 * 3600 and y.get("exit_cap_3pct") is not None]
        if later and x.get("exit_cap_3pct") is not None:
            follow += 1
    res["liquidity_label_from_snapshots"] = {"decisions_24h": len(kept24), "with_exit_cap_at_decision_and_followup_20_28h": follow,
                                             "note": "follow-up snapshots exist only for tokens the scheduled runs kept analysing (watchlist), a selected subset"}
    # launch cohort
    fs = [c.get("first_seen_at") for c in cohort.values() if c.get("first_seen_at")]
    res["launch_cohort"] = {"mints": len(cohort), "by_chain": dict(collections.Counter(c.get("chain") for c in cohort.values())),
                            "platform_top": collections.Counter(c.get("platform") for c in cohort.values()).most_common(6),
                            "sample_basis": dict(collections.Counter(c.get("sample_basis") for c in cohort.values())),
                            "first_seen_range": [iso(min(fs)), iso(max(fs))] if fs else None,
                            "first_seen_by_day": dict(sorted(collections.Counter(iso(x)[:10] for x in fs).items())),
                            "mcap_24h_known": sum(1 for c in cohort.values() if c.get("mcap_24h") is not None),
                            "mcap_7d_known": sum(1 for c in cohort.values() if c.get("mcap_7d") is not None),
                            "rug_flag_non_null": sum(1 for c in cohort.values() if c.get("rug_flag") is not None)}
    with open(out, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True, default=str)
    print(json.dumps({k: res[k] for k in ("export_versions", "data_end", "clocks", "universe")}, indent=1, default=str))
    # _events_24h_list: decision keys only (mint, times, pool, status); no price after a decision is read anywhere in this probe


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
