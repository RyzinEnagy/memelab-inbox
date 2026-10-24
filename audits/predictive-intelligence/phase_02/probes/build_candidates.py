"""Build research/CANDIDATES.csv and research/SHORTLIST.csv from the recorded evidence.

Usage:
  python build_candidates.py PHASE02_DIR CLONE_ROOT PACKAGE_DIR

Inputs (all under PHASE02_DIR/research unless noted):
  CANDIDATE_ANNOTATIONS.csv  hand-written family, role, need ids, screen note
  SHORTLIST_ANNOTATIONS.csv  hand-written code evidence (path::symbol), reasons
  SPECIAL_FLAGS.json         flags read by hand from pinned files, with sources
  NEEDS.csv                  frozen needs and their GAP_MATRIX cells
  VERIFY_RESULTS.jsonl       probes/verify_repos.py output
  ROOT_COMMITS.jsonl         probes/root_commits.py output
  PYPI_LOOKUPS.jsonl         probes/pypi_lookup.py output
  QUERY_RESULTS.jsonl        every discovery call (search, keyword index, docs, papers, WebSearch)
  PACKAGE_DIR/references/CANDIDATE_SEEDS.md
Code evidence for the shortlist is checked in the blob-less clones under
CLONE_ROOT at the pinned SHA (path exists in the tree, symbol defined in the
file); blob id and line are written to SHORTLIST.csv.
"""
import csv
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime

INACTIVE_BEFORE = "2025-04-24"  # 18 months before the phase date 2026-10-24
GH = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
LICENSE_FLAG = {"AGPL-3.0": "COPYLEFT_AGPL", "GPL-3.0": "COPYLEFT_GPL", "GPL-2.0": "COPYLEFT_GPL",
                "GPL": "COPYLEFT_GPL", "LGPL": "COPYLEFT_LGPL", "BUSL-1.1": "SOURCE_AVAILABLE_BUSL",
                "COMMONS-CLAUSE": "COMMONS_CLAUSE", "NON-COMMERCIAL-TERMS": "NONCOMMERCIAL_TERMS",
                "ELASTIC": "SOURCE_AVAILABLE_ELASTIC", "POLYFORM": "SOURCE_AVAILABLE_POLYFORM",
                "OTHER_REVIEW": "LICENSE_REVIEW"}


def jl(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def sym_line(text, sym):
    pat = re.compile(r"^\s*(class|def|async def)\s+%s\b|^%s\s*=" % (re.escape(sym), re.escape(sym)))
    for i, line in enumerate(text.splitlines(), 1):
        if pat.search(line):
            return i
    return None


def git(clone, *args):
    return subprocess.run(["git", "-C", clone] + list(args), capture_output=True, text=True)


def main(argv):
    base, clone_root, pkg = argv[1], argv[2], argv[3]
    R = os.path.join(base, "research")
    ann = list(csv.DictReader(open(os.path.join(R, "CANDIDATE_ANNOTATIONS.csv"))))
    short = {r["canonical"]: r for r in csv.DictReader(open(os.path.join(R, "SHORTLIST_ANNOTATIONS.csv")))}
    needs = {r["need_id"]: r for r in csv.DictReader(open(os.path.join(R, "NEEDS.csv")))}
    special = json.load(open(os.path.join(R, "SPECIAL_FLAGS.json")))["flags"]
    verify = jl(os.path.join(R, "VERIFY_RESULTS.jsonl"))
    roots = {r["repo"].lower(): r for r in jl(os.path.join(R, "ROOT_COMMITS.jsonl"))}
    pypi = jl(os.path.join(R, "PYPI_LOOKUPS.jsonl"))
    queries = jl(os.path.join(R, "QUERY_RESULTS.jsonl"))
    seeds_text = open(os.path.join(pkg, "references", "CANDIDATE_SEEDS.md")).read()
    seeds = {(m.group(1) + "/" + m.group(2)).lower() for m in GH.finditer(seeds_text)}

    canon = {a["canonical"].lower(): a["canonical"] for a in ann}
    # verification record per canonical name (exact-name record preferred)
    vrec = {}
    for v in verify:
        name = (v.get("canonical") or v["input"])
        if name.lower() in canon and (name.lower() not in vrec or v["input"].lower() == name.lower()):
            vrec[name.lower()] = v
    # aliases: another verified input with the same pinned SHA (served at an old path)
    alias = defaultdict(list)
    sha_to_canon = {vrec[c]["pinned_sha"]: c for c in vrec if vrec[c].get("pinned_sha")}
    for v in verify:
        c = sha_to_canon.get(v.get("pinned_sha"))
        if c and v["input"].lower() != c and v.get("eco_status") == 404:
            alias[c].append(v["input"])
    for e in jl(os.path.join(R, "EXTRA_PINS.jsonl")):
        for c, v in vrec.items():
            if v.get("pinned_sha", "").startswith(e["ls_remote_head_prefix"]) and e["repo"].lower() != c \
                    and e["repo"] not in alias[c]:
                alias[c].append(e["repo"])
    alias_to_canon = {a.lower(): c for c, al in alias.items() for a in al}
    pypi_names = {p["package"].lower(): p for p in pypi}
    PYPI_URL = re.compile(r"(?:pypi\.org/project/|pypi\.python\.org/pypi/|libraries\.io/pypi/|registries/pypi\.org/packages/)([A-Za-z0-9_.-]+)")
    DOCSEARCH = re.compile(r"docsearch\.algolia\.com/mcp/docs/repo/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")

    # provenance
    prov = defaultdict(set)
    mech = defaultdict(set)

    def hit(repo, qid, m):
        if not repo:
            return
        k = repo.lower()
        k = alias_to_canon.get(k, k)
        if k in canon:
            prov[k].add(qid)
            mech[k].add(m)
    for q in queries:
        for it in q.get("items") or []:
            hit(it.get("repo") or it.get("full_name"), q["qid"], q["mechanism"])
        for u in q.get("result_urls") or []:
            m = PYPI_URL.search(u)
            if m and m.group(1).lower() in pypi_names:
                for r in pypi_names[m.group(1).lower()].get("github_repos") or []:
                    hit(r, "%s>PYPI:%s" % (q["qid"], m.group(1).lower()), q["mechanism"])
            m = re.search(r"https?://([a-z0-9-]+)\.readthedocs\.io", u)
            if m and m.group(1).lower() in pypi_names:
                for r in pypi_names[m.group(1).lower()].get("github_repos") or []:
                    hit(r, "%s>DOCS:%s" % (q["qid"], m.group(1).lower()), q["mechanism"])
            m = DOCSEARCH.search(u)
            if m:
                hit(m.group(1) + "/" + m.group(2), q["qid"], q["mechanism"])
    qmech = {q["qid"]: q["mechanism"] for q in queries}
    for mrow in jl(os.path.join(R, "MIRROR_CHECKS.jsonl")):
        hit(mrow["of"], "%s>%s" % (mrow["found_by"], mrow["repo"]), qmech.get(mrow["found_by"], ""))
    for p in pypi:
        for r in p.get("github_repos") or []:
            hit(r, "PYPI:" + p["package"], "PYPI_JSON")
    for s in seeds:
        hit(s, "SEED", "PACKAGE_SEED_LIST")
    pypi_by = {p["package"]: p for p in pypi}

    # shared roots among candidates
    root_owner = defaultdict(list)
    for c in canon:
        for rt in (roots.get(c) or {}).get("roots") or []:
            root_owner[rt].append(canon[c])

    out_rows, short_rows = [], []
    for a in ann:
        c = a["canonical"]
        k = c.lower()
        v = vrec.get(k, {})
        p = pypi_by.get(a["pypi"]) if a["pypi"] else None
        lic_files = v.get("license_files") or []
        if not lic_files and v.get("pinned_sha"):
            # REUSE layout: license texts under LICENSES/ instead of the root
            clone = os.path.join(clone_root, c.replace("/", "__"))
            names = git(clone, "ls-tree", "-r", "--name-only", v["pinned_sha"], "--", "LICENSES").stdout.split()
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from verify_repos import classify_license
            import hashlib
            for n in names:
                text = git(clone, "show", "%s:%s" % (v["pinned_sha"], n)).stdout
                lic_files.append({"path": n, "sha256": hashlib.sha256(text.encode()).hexdigest(),
                                  "classification": classify_license(text)})
        labels = sorted({l for f in lic_files for l in f["classification"]})
        lflags = sorted({LICENSE_FLAG[l] for l in labels if l in LICENSE_FLAG})
        if not lic_files:
            lflags.append("NO_LICENSE_FILE_AT_ROOT")
        sflags = [f for f, _ in special.get(c, [])]
        sflag_src = ["%s: %s" % (f, s) for f, s in special.get(c, [])]
        shared = sorted({o for rt in (roots.get(k) or {}).get("roots") or [] for o in root_owner[rt] if o != c})
        commit_date = v.get("commit_date", "")
        activity = []
        if commit_date and commit_date[:10] < INACTIVE_BEFORE:
            activity.append("INACTIVE_18M")
        if v.get("eco_archived"):
            activity.append("ARCHIVED")
        gap = sorted({g for n in a["need_ids"].split(";") for g in needs[n]["gap_cells"].split(";")})
        row = {
            "canonical_repo": c, "url": "https://github.com/" + c, "family": a["family"], "role": a["role"],
            "need_ids": a["need_ids"], "gap_cells": ";".join(gap),
            "same_head_paths": ";".join(sorted(alias.get(k, []))),
            "discovery_qids": ";".join(sorted(prov[k])), "discovery_mechanisms": ";".join(sorted(mech[k])),
            "in_package_seeds": "yes" if (k in seeds or any(x.lower() in seeds for x in alias.get(k, []))) else "no",
            "pinned_sha": v.get("pinned_sha", ""), "pin_observed_at": v.get("ls_remote_at", ""),
            "clone_head_matches_pin": str(v.get("head_matches_pin", "")).lower(),
            "commit_date": commit_date,
            "ecosystems_status": v.get("eco_status", ""),
            "ecosystems_fork": "" if v.get("eco_fork") is None else str(v.get("eco_fork")).lower(),
            "ecosystems_archived": "" if v.get("eco_archived") is None else str(v.get("eco_archived")).lower(),
            "ecosystems_last_synced_at": v.get("eco_last_synced_at") or "",
            "root_commits": ";".join((roots.get(k) or {}).get("roots") or []),
            "shared_history_with": ";".join(shared),
            "license": "+".join(labels) if labels else "NONE_FOUND",
            "license_source": ";".join("FILE:%s sha256:%s" % (f["path"], f["sha256"][:16]) for f in lic_files) or "NONE",
            "license_flags": ";".join(lflags),
            "dep_flags_pinned_files": ";".join(v.get("dep_flags") or []),
            "dep_files_scanned": ";".join(v.get("dep_files") or []),
            "pypi_package": a["pypi"], "pypi_version": (p or {}).get("version", ""),
            "pypi_latest_upload": ((p or {}).get("latest_upload") or "")[:10],
            "pypi_dep_flags_base": ";".join((p or {}).get("dep_flags") or []),
            "py313_declared_on_pypi": "" if not p else str(p.get("py313_supported")).lower(),
            "py_files": v.get("py_files", ""), "test_files": v.get("test_files", ""),
            "activity_flags": ";".join(activity), "special_flags": ";".join(sflags),
            "special_flag_sources": " | ".join(sflag_src),
            "evidence_basis": "PINNED_TREE" if v.get("status") == "VERIFIED" else "UNVERIFIED",
            "screen_note": a["screen_note"], "shortlisted": "yes" if c in short else "no",
        }
        out_rows.append(row)
        if c in short:
            s = short[c]
            clone = os.path.join(clone_root, c.replace("/", "__"))
            checked = []
            for ev in s["code_evidence"].split("|"):
                path, sym = ev.split("::")
                ls = git(clone, "ls-tree", v.get("pinned_sha", "HEAD"), "--", path).stdout.split()
                blob = ls[2] if len(ls) >= 3 else ""
                text = git(clone, "show", "%s:%s" % (v.get("pinned_sha", "HEAD"), path)).stdout if blob else ""
                line = sym_line(text, sym) if text else None
                checked.append("%s::%s@%s:%s" % (path, sym, blob[:12] or "MISSING", line or "NOTFOUND"))
            short_rows.append({
                "canonical_repo": c, "family": a["family"], "need_ids": a["need_ids"], "gap_cells": row["gap_cells"],
                "pinned_sha": row["pinned_sha"], "license": row["license"], "license_flags": row["license_flags"],
                "special_flags": row["special_flags"], "code_evidence": s["code_evidence"],
                "code_evidence_verified": "|".join(checked),
                "inclusion_reason": s["inclusion_reason"], "uncertainty_for_phase03": s["uncertainty_for_phase03"],
            })
    with open(os.path.join(R, "CANDIDATES.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    with open(os.path.join(R, "SHORTLIST.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(short_rows[0].keys()))
        w.writeheader()
        w.writerows(short_rows)
    print("candidates", len(out_rows), "shortlist", len(short_rows))
    for r in short_rows:
        if "MISSING" in r["code_evidence_verified"] or "NOTFOUND" in r["code_evidence_verified"]:
            print("EVIDENCE PROBLEM", r["canonical_repo"], r["code_evidence_verified"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
