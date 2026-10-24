"""Check the Phase 02 research deliverables against the gate.

Usage:
  python check_candidates.py PHASE02_DIR GAP_MATRIX_CSV [--live N] [--seed S]

Offline checks (exit 1 with one line per problem):
  needs      NEEDS.csv sha256 equals the value frozen before the first query;
             every need cell exists in GAP_MATRIX.csv with status MISSING,
             PARTIAL or CONFLICT
  corpus     at least 12 distinct successful queries, 6 families, 4 mechanisms
  candidates at least 45 unique canonical repositories; 40-hex pins; clone
             HEAD equal to the pin; verified tree; not a fork; no shared root
             commit unless flagged SHARED_HISTORY_HARD_FORK and counted once;
             source present; license recorded from a file; need ids known;
             every discovery qid traceable to QUERY_RESULTS.jsonl,
             PYPI_LOOKUPS.jsonl, MIRROR_CHECKS.jsonl or the seed list; no crawler
             tooling; nothing that EXCLUSIONS.md excludes
  shortlist  at least 20 rows, a subset of the candidates with the same pins;
             at least 3 per high-priority family; MiroFish and OASIS present;
             no score or rank column; every code evidence item names a source
             file (not README, docs or notebooks), a blob and a line (P42)
  coverage   every verified input is a candidate, a same-HEAD path of one, or
             listed in EXCLUSIONS.md; every candidate not shortlisted has a
             reason in EXCLUSIONS.md section G
  audit      PROVENANCE_AUDIT.json has 5 rows, each reappeared
Live checks (--live N): for N candidates drawn with the seed, `git ls-remote`
(a moved HEAD is reported, not failed) and a fetch of the pinned commit into an
empty repository (must succeed); for every shortlisted repository, the code
evidence is re-read from a fresh blob-less fetch at the pin.
"""
import csv
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import tempfile

NEEDS_SHA256 = "90c9391aa6674abbf138b59e610ce0b72ab7eeb6a15763458e341d6fd6560f5e"
HIGH_PRIORITY = ["TABULAR_PROBABILITY", "TIME_SERIES", "CALIBRATION_UNCERTAINTY", "ONLINE_DRIFT_MONITORING",
                 "BEHAVIORAL_MULTI_AGENT", "EXPERIMENT_AUDIT_EVALUATION", "EVENT_TIME_LABELS"]  # event time added in repair pass 2 (skeptic m4)
NOT_PERMISSIVE = ("COPYLEFT_", "SOURCE_AVAILABLE_", "COMMONS_CLAUSE", "NONCOMMERCIAL_TERMS", "NO_LICENSE_FILE_AT_ROOT")
ISOLATED_FAMILIES = {"BEHAVIORAL_MULTI_AGENT"}  # run behind the PLANNED_SEAMS adapter, never imported in-process
TOOLING = {"firecrawl/firecrawl", "mendableai/firecrawl", "unclecode/crawl4ai", "getmaxun/maxun"}
GAP_OK = {"MISSING", "PARTIAL", "CONFLICT"}
NOT_CODE = re.compile(r"(^|/)(README[^/]*|docs?/.*|.*\.(md|rst|txt|ipynb|html|pdf))$", re.I)


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def table_repos(md, heading_prefix=None):
    prefixes = (heading_prefix,) if isinstance(heading_prefix, str) else heading_prefix
    out, on = set(), heading_prefix is None
    for line in md.splitlines():
        if line.startswith("## "):
            on = heading_prefix is None or any(line.startswith("## " + p) for p in prefixes)
        m = re.match(r"^\| `([^`]+)` \|", line)
        if on and m:
            out.add(m.group(1).lower())
    return out


def check(base, gap_csv, live=0, seed=20261024):
    R = os.path.join(base, "research")
    P = []
    gap = {(r["facility"], r["need"]): r["status"] for r in csv.DictReader(open(gap_csv))}
    needs_path = os.path.join(R, "NEEDS.csv")
    if hashlib.sha256(open(needs_path, "rb").read()).hexdigest() != NEEDS_SHA256:
        P.append("needs: NEEDS.csv changed after it was frozen")
    needs = {r["need_id"]: r for r in csv.DictReader(open(needs_path))}
    for n, r in needs.items():
        for cell in r["gap_cells"].split(";"):
            f, k = cell.split(":")
            if gap.get((f, k)) not in GAP_OK:
                P.append("needs: %s cites %s with status %s" % (n, cell, gap.get((f, k))))

    q = jl(os.path.join(R, "QUERY_RESULTS.jsonl"))
    ok = [r for r in q if r["mechanism"] != "GITHUB_SEARCH_API" and (r["mechanism"] == "WEBSEARCH" or r.get("http_status") == 200)]
    if len({(r["mechanism"], r.get("query") or r.get("url")) for r in ok}) < 12:
        P.append("corpus: fewer than 12 distinct successful queries")
    if len({r["family"] for r in ok}) < 6:
        P.append("corpus: fewer than 6 topic families")
    if len({r["mechanism"] for r in ok}) < 4:
        P.append("corpus: fewer than 4 mechanisms")
    qids = {r["qid"] for r in q}
    pypi = {r["package"]: r for r in jl(os.path.join(R, "PYPI_LOOKUPS.jsonl"))}
    mirrors = jl(os.path.join(R, "MIRROR_CHECKS.jsonl"))
    mirror_keys = {"%s>%s" % (m["found_by"], m["repo"]) for m in mirrors}

    cands = list(csv.DictReader(open(os.path.join(R, "CANDIDATES.csv"))))
    names = [c["canonical_repo"].lower() for c in cands]
    if len(set(names)) != len(names):
        P.append("candidates: duplicate canonical repository")
    seen_roots, hist = {}, 0
    for c in cands:
        n = c["canonical_repo"]
        if not re.fullmatch(r"[0-9a-f]{40}", c["pinned_sha"]):
            P.append("candidates: %s pin is not a 40-hex SHA" % n)
        if c["clone_head_matches_pin"] != "true" or c["evidence_basis"] != "PINNED_TREE":
            P.append("candidates: %s not verified at its pin" % n)
        if c["ecosystems_fork"] == "true":
            P.append("candidates: %s is a fork" % n)
        rs = [x for x in c["root_commits"].split(";") if x]
        if not rs:
            P.append("candidates: %s has no root commit recorded" % n)
        shared = [seen_roots[x] for x in rs if x in seen_roots]
        if shared and "SHARED_HISTORY_HARD_FORK" not in c["special_flags"]:
            P.append("candidates: %s shares history with %s" % (n, shared[0]))
        if not shared:
            hist += 1
        for x in rs:
            seen_roots.setdefault(x, n)
        if not (str(c["py_files"]).isdigit() and int(c["py_files"]) > 0) and not c["pypi_package"]:
            P.append("candidates: %s has no source in its tree and no package" % n)
        if not c["license_source"].startswith(("FILE:", "API_ONLY")):
            P.append("candidates: %s license not read from a file" % n)
        for nid in c["need_ids"].split(";"):
            if nid not in needs:
                P.append("candidates: %s unknown need %s" % (n, nid))
        dq = [x for x in c["discovery_qids"].split(";") if x]
        if not dq:
            P.append("candidates: %s has no discovery provenance" % n)
        for x in dq:
            if x == "SEED":
                if c["in_package_seeds"] != "yes":
                    P.append("candidates: %s credited to SEED but not in the seed list" % n)
            elif x.startswith("PYPI:"):
                if x[5:] not in pypi:
                    P.append("candidates: %s credited to unknown PyPI lookup %s" % (n, x))
            elif ">" in x:
                head, tail = x.split(">", 1)
                if head not in qids or not (tail.startswith(("PYPI:", "DOCS:")) or x in mirror_keys):
                    P.append("candidates: %s chained credit %s not traceable" % (n, x))
            elif x not in qids:
                P.append("candidates: %s credited to unknown query %s" % (n, x))
        if n.lower() in TOOLING:
            P.append("candidates: %s is crawler tooling" % n)
    if hist < 45:
        P.append("candidates: %d unique histories, fewer than 45" % hist)

    # canonical path (repair pass 2, skeptic m1 and counterexample): a row must sit on the path the
    # metadata mirror knows; a row without a mirror record needs a recorded successor search, and a
    # path that a search showed to be pre-transfer can never be a candidate
    verify = jl(os.path.join(R, "VERIFY_RESULTS.jsonl"))
    eco_name = {}
    for v in verify:
        if v.get("eco_status") == 200 and v.get("eco_full_name"):
            eco_name[v["input"].lower()] = v["eco_full_name"]
    succ_path = os.path.join(R, "SUCCESSOR_SEARCH.jsonl")
    succ = jl(succ_path) if os.path.exists(succ_path) else []
    by_canon = {e["canonical"].lower(): e for e in succ}
    old_paths = {e["recorded_path"].lower(): e["canonical"] for e in succ if e["recorded_path"].lower() != e["canonical"].lower()}
    for c in cands:
        n, k = c["canonical_repo"], c["canonical_repo"].lower()
        if k in old_paths:
            P.append("candidates: %s is recorded under a pre-transfer path (current path %s)" % (n, old_paths[k]))
        if str(c["ecosystems_status"]) == "200":
            if c["canonical_basis"] != "ECOSYSTEMS_RECORD":
                P.append("candidates: %s canonical basis %s with a mirror record" % (n, c["canonical_basis"]))
            if k in eco_name and eco_name[k].lower() != k:
                P.append("candidates: %s differs from its mirror name %s" % (n, eco_name[k]))
        else:
            e = by_canon.get(k)
            if not e or len(e.get("sources") or []) < 2:
                P.append("candidates: %s has no mirror record and no recorded successor search (possible pre-transfer path)" % n)
            else:
                for pth in e["paths"]:
                    if pth["path"].lower() != k and pth.get("repos_ecosystems") == 200 and pth.get("head") and c["pinned_sha"].startswith(pth["head"]):
                        P.append("candidates: %s is recorded under a pre-transfer path; %s serves the same HEAD and has a record" % (n, pth["path"]))
        e = by_canon.get(k)
        if e:
            for pth in e["paths"]:
                if pth["path"].lower() == k and (pth.get("archived") or (pth.get("package_record") or {}).get("archived")):
                    if "ARCHIVED" not in c["activity_flags"] or c["ecosystems_archived"] != "true":
                        P.append("candidates: %s lost its archived flag" % n)

    excl_md = open(os.path.join(R, "EXCLUSIONS.md")).read()
    excluded = table_repos(excl_md, ("A.", "B.", "C.", "D.", "E.", "F."))
    g_section = table_repos(excl_md, "G.")
    for c in cands:
        if c["canonical_repo"].lower() in excluded:
            P.append("candidates: %s is listed as excluded" % c["canonical_repo"])
    short = list(csv.DictReader(open(os.path.join(R, "SHORTLIST.csv"))))
    by = {c["canonical_repo"]: c for c in cands}
    hdr = [h.lower() for h in (short[0].keys() if short else [])]
    if any("score" in h or "rank" in h for h in hdr):
        P.append("shortlist: has a score or rank column")
    if len(short) < 20:
        P.append("shortlist: %d rows, fewer than 20" % len(short))
    fam = {}
    for s in short:
        n = s["canonical_repo"]
        if n not in by:
            P.append("shortlist: %s not in candidates" % n)
            continue
        if s["pinned_sha"] != by[n]["pinned_sha"]:
            P.append("shortlist: %s pin differs from candidates" % n)
        if by[n]["shortlisted"] != "yes":
            P.append("shortlist: %s not marked shortlisted in candidates" % n)
        if s["family"] != by[n]["family"]:
            P.append("shortlist: %s family %s differs from candidates family %s" % (n, s["family"], by[n]["family"]))
        fam[by[n]["family"]] = fam.get(by[n]["family"], 0) + 1
        # written shortlist rule (EXCLUSIONS.md section G): active, and permissive unless isolated
        if by[n]["activity_flags"]:
            P.append("shortlist: %s breaks the shortlist rule (activity %s)" % (n, by[n]["activity_flags"]))
        bad = [f for f in by[n]["license_flags"].split(";") if f.startswith(NOT_PERMISSIVE)]
        if bad and by[n]["family"] not in ISOLATED_FAMILIES:
            P.append("shortlist: %s breaks the shortlist rule (license %s in-process)" % (n, ";".join(bad)))
        items = [x for x in s["code_evidence_verified"].split("|") if x]
        if not items:
            P.append("shortlist: %s has no code evidence (P42)" % n)
        for it in items:
            m = re.fullmatch(r"(.+)::([A-Za-z_][A-Za-z0-9_]*)@([0-9a-f]{12}):(\d+)", it)
            if not m:
                P.append("shortlist: %s code evidence not verified: %s" % (n, it))
                continue
            if NOT_CODE.search(m.group(1)):
                P.append("shortlist: %s code evidence is documentation, not code: %s (P42)" % (n, m.group(1)))
    for f in HIGH_PRIORITY:
        if fam.get(f, 0) < 3:
            P.append("shortlist: family %s has %d rows, fewer than 3" % (f, fam.get(f, 0)))
    sn = {s["canonical_repo"].lower() for s in short}
    for must in ("666ghj/mirofish", "camel-ai/oasis"):
        if must not in sn:
            P.append("shortlist: %s missing" % must)
    for c in cands:
        if c["shortlisted"] == "yes" and c["canonical_repo"].lower() not in sn:
            P.append("shortlist: %s marked shortlisted but absent" % c["canonical_repo"])
        if c["shortlisted"] != "yes" and c["canonical_repo"].lower() not in g_section:
            P.append("coverage: %s not shortlisted and no reason in EXCLUSIONS.md section G" % c["canonical_repo"])

    covered = {c["canonical_repo"].lower() for c in cands} | excluded
    for c in cands:
        covered |= {x.lower() for x in c["same_head_paths"].split(";") if x}
    for v in jl(os.path.join(R, "VERIFY_RESULTS.jsonl")):
        if v["input"].lower() not in covered and (v.get("canonical") or "").lower() not in covered:
            P.append("coverage: verified input %s is neither a candidate nor excluded" % v["input"])

    audit = json.load(open(os.path.join(R, "PROVENANCE_AUDIT.json")))
    rows = audit.get("rows") or []
    if len(rows) < 5 or not all(r.get("reappeared") for r in rows):
        P.append("audit: fewer than 5 reproduced provenance rows")

    if live:
        rng = random.Random(seed)
        pick = rng.sample(cands, min(live, len(cands)))
        sbys = {s["canonical_repo"]: s for s in short}
        targets = {c["canonical_repo"]: c for c in pick}
        targets.update({n: by[n] for n in sbys if n in by})
        for n, c in sorted(targets.items()):
            url = "https://github.com/" + n
            lr = subprocess.run(["git", "ls-remote", url, "HEAD"], capture_output=True, text=True, timeout=120)
            now = lr.stdout.split()[0] if lr.returncode == 0 and lr.stdout.strip() else "FAILED"
            with tempfile.TemporaryDirectory() as d:
                subprocess.run(["git", "init", "-q", d], check=True)
                fx = subprocess.run(["git", "-C", d, "fetch", "-q", "--depth", "1", "--filter=blob:none", url, c["pinned_sha"]],
                                    capture_output=True, text=True, timeout=900)
                state = "pin fetched" if fx.returncode == 0 else "PIN NOT FETCHABLE"
                if fx.returncode != 0:
                    P.append("live: %s pinned commit not fetchable" % n)
                ev = []
                if n in sbys and fx.returncode == 0:
                    for it in sbys[n]["code_evidence_verified"].split("|"):
                        m = re.fullmatch(r"(.+)::([A-Za-z_][A-Za-z0-9_]*)@([0-9a-f]{12}):(\d+)", it)
                        if not m:
                            continue
                        path, sym, blob, line = m.groups()
                        ls = subprocess.run(["git", "-C", d, "ls-tree", c["pinned_sha"], "--", path], capture_output=True, text=True).stdout.split()
                        text = subprocess.run(["git", "-C", d, "show", "%s:%s" % (c["pinned_sha"], path)], capture_output=True, text=True).stdout
                        lines = text.splitlines()
                        good = len(ls) >= 3 and ls[2].startswith(blob) and int(line) <= len(lines) and re.search(
                            r"^\s*(class|def|async def)\s+%s\b|^%s\s*=" % (sym, sym), lines[int(line) - 1])
                        ev.append("%s %s" % (path, "ok" if good else "MISMATCH"))
                        if not good:
                            P.append("live: %s code evidence mismatch %s" % (n, it))
            print("live", n, "head now", now[:12], "moved" if now != c["pinned_sha"] else "same", state, "; ".join(ev))
    return P


def main(argv):
    live, seed = 0, 20261024
    if "--live" in argv:
        i = argv.index("--live")
        live = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    if "--seed" in argv:
        i = argv.index("--seed")
        seed = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    problems = check(argv[1], argv[2], live, seed)
    for p in problems:
        print("PROBLEM", p)
    print("problems", len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
