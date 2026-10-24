"""Phase 01 skeptic: is the thesis key (mint, created_at) a point-in-time identity?

For every key, collect each distinct row content (all fields except id) and the first export commit in which that content
appears. A "revision" is a content first seen in a later export than the key's first export. If a later phase attaches the
key's first-export commit time (PI-D-015) to a revised content, that is look-ahead.

    python /home/claude/pi_orchestration/skeptic/skeptic_01_revisions.py origin/main OUT.json
"""
import collections
import datetime as dt
import hashlib
import json
import subprocess
import sys

FIELDS = ("status", "fatal_flags_json", "score")
SNAP = ("price", "liquidity", "vol_24h", "mcap", "exit_cap_3pct")


def git(*a):
    return subprocess.run(["git", *a], check=True, capture_output=True).stdout


def hc(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()[:16]


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.UTC).strftime("%Y-%m-%dT%H:%MZ")


def main(ref, out):
    revs = [l.split() for l in git("rev-list", "--reverse", "--first-parent", "--timestamp", ref, "--", "data/state/latest.json").decode().split("\n") if l]
    revs = [(s, int(t)) for t, s in revs]
    key_first = {}                           # key -> (sha, ct)
    content_first = {}                       # (key, hash) -> (sha, ct, row)
    within_dupe_exports = collections.Counter()
    within_dupe_keys = set()
    chain = {}
    for sha, ct in revs:
        doc = json.loads(git("show", f"{sha}:data/state/latest.json"))
        tb = doc.get("_tables") or {k: v for k, v in doc.items() if isinstance(v, list)}
        for t in tb.get("tokens") or []:
            chain.setdefault(t["mint"], t.get("chain"))
        cnt = collections.Counter()
        for th in tb.get("theses") or []:
            key = (th["mint"], repr(float(th["created_at"])))
            row = {k: v for k, v in th.items() if k != "id"}
            cnt[key] += 1
            key_first.setdefault(key, (sha, ct))
            content_first.setdefault((key, hc(row)), (sha, ct, row))
        d = [k for k, n in cnt.items() if n > 1]
        if d:
            within_dupe_exports[sha[:8]] = len(d)
            within_dupe_keys.update(d)
    by_key = collections.defaultdict(list)
    for (key, h), v in content_first.items():
        by_key[key].append(v)
    revised = []
    for key, lst in by_key.items():
        f_sha, f_ct = key_first[key]
        first_contents = [r for s, c, r in lst if s == f_sha]
        for s, c, r in lst:
            if c > f_ct:
                diffs = sorted(k for k in FIELDS if all(r.get(k) != fr.get(k) for fr in first_contents))
                sj = json.loads(r.get("snapshot_json") or "{}")
                sdiffs = sorted(k for k in SNAP if all(sj.get(k) != json.loads(fr.get("snapshot_json") or "{}").get(k) for fr in first_contents))
                revised.append({"mint": key[0], "created_at": key[1], "chain": chain.get(key[0]), "first_export": f_sha[:8], "first_ct": iso(f_ct),
                                "revision_export": s[:8], "revision_ct": iso(c), "delay_h": round((c - f_ct) / 3600, 2),
                                "fields_differ": diffs, "snapshot_fields_differ": sdiffs,
                                "first_status": [fr.get("status") for fr in first_contents], "revised_status": r.get("status"),
                                "first_score": [fr.get("score") for fr in first_contents], "revised_score": r.get("score")})
    res = {"export_versions": len(revs), "keys": len(key_first),
           "exports_with_duplicate_keys_inside": dict(within_dupe_exports), "keys_duplicated_inside_an_export": len(within_dupe_keys),
           "keys_with_content_first_seen_after_key_first_export": len({(r["mint"], r["created_at"]) for r in revised}),
           "revision_rows": len(revised),
           "revisions_changing_status": sum(1 for r in revised if "status" in r["fields_differ"]),
           "revisions_changing_fatal_flags": sum(1 for r in revised if "fatal_flags_json" in r["fields_differ"]),
           "revisions_changing_score": sum(1 for r in revised if "score" in r["fields_differ"]),
           "revisions_changing_snapshot_price": sum(1 for r in revised if "price" in r["snapshot_fields_differ"]),
           "revisions_on_solana": sum(1 for r in revised if r["chain"] == "solana"),
           "delay_h_max": max((r["delay_h"] for r in revised), default=None),
           "examples": sorted(revised, key=lambda r: -r["delay_h"])[:8]}
    json.dump({**res, "all_revisions": revised}, open(out, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
