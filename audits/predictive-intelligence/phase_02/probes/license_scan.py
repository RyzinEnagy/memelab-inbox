"""Per-file license scan of shortlisted repositories at their pins (Phase 03 license-gate input).

Usage: python license_scan.py PHASE02_DIR WORK_DIR

For every row of research/SHORTLIST.csv: a depth-1 fetch of the pinned
commit with all blobs into WORK_DIR, a checkout, then:
  - SPDX-License-Identifier lines anywhere in the first 40 lines of source files
  - license names in those header lines (Apache, MIT grant, BSD, GPL family,
    MPL, Business Source, non-commercial wording) that differ from the root label
  - license, notice and copying files below the root, classified from their text
  - .gitmodules entries (code pulled into builds, not into the tree)
  - third-party notice files
Writes research/LICENSE_SCAN.csv. The checkout is deleted after each row.
Nothing is installed or executed; file text is data.
"""
import csv
import os
import re
import shutil
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_repos import classify_license  # noqa: E402

SRC = re.compile(r"\.(py|pyx|pxd|pyi|c|cc|cpp|cxx|h|hpp|hh|cu|cuh|js|jsx|ts|tsx|r|java|scala|go|rs|sql|sh)$", re.I)
LIC = re.compile(r"(^|/)(LICEN[CS]E|COPYING|NOTICE|THIRD[-_ ]?PARTY|COPYRIGHT)[^/]*$", re.I)
SPDX = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+\-() ]+)")
HEADER_MARKS = [
    ("APACHE", re.compile(r"Apache License|Licensed under the Apache", re.I)),
    ("MIT_GRANT", re.compile(r"Permission is hereby granted, free of charge|MIT License", re.I)),
    ("BSD", re.compile(r"BSD[- ](2|3|two|three)[- ]Clause|Redistribution and use in source and binary forms", re.I)),
    ("GPL_FAMILY", re.compile(r"GNU (Affero |Lesser )?General Public License|\b[AL]?GPL-?[23]", re.I)),
    ("MPL", re.compile(r"Mozilla Public License|MPL-2\.0", re.I)),
    ("SOURCE_AVAILABLE", re.compile(r"Business Source License|Functional Source License|Elastic License|PolyForm|Commons Clause|Community License", re.I)),
    ("NONCOMMERCIAL", re.compile(r"\bnon-?commercial\b", re.I)),
]
ROOT_FAMILY = {"MIT": "MIT_GRANT", "Apache-2.0": "APACHE", "BSD-3-Clause": "BSD", "BSD-2-Clause": "BSD",
               "AGPL-3.0": "GPL_FAMILY", "GPL-3.0": "GPL_FAMILY", "LGPL": "GPL_FAMILY", "MPL-2.0": "MPL"}


def scan(d, root_label):
    spdx, marks, mark_paths, nested, notices = Counter(), Counter(), {}, [], []
    files = 0
    for dp, dn, fn in os.walk(d):
        if ".git" in dn:
            dn.remove(".git")
        for f in fn:
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, d)
            if os.path.islink(full) or os.path.getsize(full) > 2_000_000:
                continue
            if LIC.search(rel):
                if "/" in rel:
                    text = open(full, encoding="utf-8", errors="replace").read()
                    nested.append("%s:%s" % (rel, "+".join(classify_license(text))))
                if re.search(r"NOTICE|THIRD", rel, re.I):
                    notices.append(rel)
                continue
            if not SRC.search(rel):
                continue
            files += 1
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    head = "".join([next(fh, "") for _ in range(40)])
            except OSError:
                continue
            for m in SPDX.finditer(head):
                spdx[m.group(1).strip()] += 1
            for name, pat in HEADER_MARKS:
                if pat.search(head) and name != ROOT_FAMILY.get(root_label.split("+")[0], ""):
                    marks[name] += 1
                    mark_paths.setdefault(name, []).append(rel)
    gm = ""
    if os.path.exists(os.path.join(d, ".gitmodules")):
        gm = ";".join(sorted(set(re.findall(r"url\s*=\s*(\S+)", open(os.path.join(d, ".gitmodules")).read()))))
    return files, spdx, marks, mark_paths, nested, notices, gm


def main(argv):
    base, work = argv[1], argv[2]
    R = os.path.join(base, "research")
    short = list(csv.DictReader(open(os.path.join(R, "SHORTLIST.csv"))))
    out = []
    os.makedirs(work, exist_ok=True)
    for s in short:
        c, pin, root_label = s["canonical_repo"], s["pinned_sha"], s["license"]
        d = os.path.join(work, c.replace("/", "__"))
        shutil.rmtree(d, ignore_errors=True)
        subprocess.run(["git", "init", "-q", d], check=True)
        f = subprocess.run(["git", "-C", d, "fetch", "-q", "--depth", "1", "https://github.com/" + c, pin],
                           capture_output=True, text=True, timeout=1800)
        if f.returncode != 0:
            out.append({"canonical_repo": c, "pinned_sha": pin, "root_license": root_label, "source_files_scanned": 0,
                        "spdx_ids": "", "other_header_marks": "", "example_paths": "", "nested_license_files": "",
                        "notice_files": "", "submodules": "", "phase03_gate_input": "SCAN_FAILED: " + f.stderr.strip()[-100:]})
            continue
        subprocess.run(["git", "-C", d, "-c", "advice.detachedHead=false", "checkout", "-q", pin], check=True)
        files, spdx, marks, mark_paths, nested, notices, gm = scan(d, root_label)
        shutil.rmtree(d, ignore_errors=True)
        notes = []
        if marks.get("GPL_FAMILY"):
            notes.append("GPL-family text in %d file headers" % marks["GPL_FAMILY"])
        if marks.get("SOURCE_AVAILABLE"):
            notes.append("source-available license named in %d file headers" % marks["SOURCE_AVAILABLE"])
        if marks.get("NONCOMMERCIAL"):
            notes.append("non-commercial wording in %d file headers" % marks["NONCOMMERCIAL"])
        other = [k for k in ("APACHE", "MIT_GRANT", "BSD", "MPL") if marks.get(k)]
        if other:
            notes.append("other permissive or file-level licenses in headers: %s" % ", ".join("%s %d" % (k, marks[k]) for k in other))
        if nested:
            notes.append("%d nested license or notice files" % len(nested))
        if gm:
            notes.append("git submodules pulled into builds")
        if not notes:
            notes.append("no header, nested or submodule license different from the root found")
        out.append({
            "canonical_repo": c, "pinned_sha": pin, "root_license": root_label, "source_files_scanned": files,
            "spdx_ids": ";".join("%s:%d" % kv for kv in sorted(spdx.items())),
            "other_header_marks": ";".join("%s:%d" % kv for kv in sorted(marks.items())),
            "example_paths": " | ".join("%s: %s" % (k, ", ".join(v[:3])) for k, v in sorted(mark_paths.items())),
            "nested_license_files": " | ".join(nested[:12]) + (" | (%d more)" % (len(nested) - 12) if len(nested) > 12 else ""),
            "notice_files": ";".join(notices[:8]),
            "submodules": gm,
            "phase03_gate_input": "; ".join(notes) + "; header text is a lead, not a license determination",
        })
        print(c, files, dict(marks), len(nested), "submodules" if gm else "")
    with open(os.path.join(R, "LICENSE_SCAN.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
