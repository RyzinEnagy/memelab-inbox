"""Phase 03 repair pass (lead): license terms of the Rust crates compiled into river (blind rescore: "Rust crates
not license-checked by anyone"; the review says "not verified file by file").

Reads the pinned Cargo.lock and computes the closure of the crate's normal [dependencies] in Cargo.toml (pyo3,
bincode, serde, serde_json, num, ordered-float, libm) through the lock's per-package dependency lists (a superset of
what is linked, since build dependencies are included); dev and bench dependencies of the root are reported apart.
For each crate it reads the `license` field of its Cargo.toml in the local crates.io cache that the reviewer's source
build filled (~/.cargo/registry/src/index.crates.io-*). An SPDX "A OR B" counts as permissive when one alternative is.
Offline; nothing is built or run.
Usage: python3 river_crate_licenses.py <river clone> <cargo registry src dir>
"""
import json, os, re, sys

clone, reg = sys.argv[1], sys.argv[2]
lock = open(os.path.join(clone, "Cargo.lock")).read()
blocks = lock.split("[[package]]")[1:]
pkgs = {}
for b in blocks:
    name = re.search(r'^name = "([^"]+)"', b, re.M).group(1)
    ver = re.search(r'^version = "([^"]+)"', b, re.M).group(1)
    src = re.search(r'^source = "([^"]+)"', b, re.M)
    deps = re.search(r'^dependencies = \[(.*?)\]', b, re.M | re.S)
    deps = [d.strip().strip('",').split(" ")[0] for d in deps.group(1).split("\n") if d.strip().strip('",')] if deps else []
    pkgs.setdefault(name, []).append((ver, bool(src), deps))
ctoml = open(os.path.join(clone, "Cargo.toml")).read()
normal = re.findall(r'^([A-Za-z0-9_-]+)\s*=', ctoml.split("[dependencies]")[1].split("\n[")[0], re.M)
seen, stack = set(), list(normal)
while stack:
    n = stack.pop()
    if n in seen or n not in pkgs:
        continue
    seen.add(n)
    for ver, _, deps in pkgs[n]:
        stack.extend(deps)
PERMISSIVE = re.compile(r"^(MIT|Apache-2\.0|BSD-[23]-Clause|ISC|Zlib|Unicode-3\.0|Unicode-DFS-2016|Unlicense|CC0-1\.0|BSL-1\.0|0BSD|Apache-2\.0 WITH LLVM-exception)$")

def permissive(lic):
    for conj in re.split(r"\s+AND\s+", lic):
        alts = [a.strip("() ") for a in re.split(r"\s+OR\s+|/", conj)]
        if not any(PERMISSIVE.match(a) for a in alts if a):
            return False
    return True

rows, missing, nonperm = [], [], []
for name, vers in sorted(pkgs.items()):
    for ver, registry, _ in vers:
        if not registry:
            continue
        toml = os.path.join(reg, "%s-%s" % (name, ver), "Cargo.toml")
        if not os.path.isfile(toml):
            missing.append("%s %s" % (name, ver))
            continue
        m = re.search(r'^license\s*=\s*"([^"]+)"', open(toml, encoding="utf-8", errors="replace").read(), re.M)
        lic = m.group(1) if m else "NONE (license-file only)"
        ok = bool(m) and permissive(lic)
        rows.append({"crate": name, "version": ver, "license": lic, "permissive": ok, "in_normal_closure": name in seen})
        if not ok:
            nonperm.append("%s %s: %s (%s)" % (name, ver, lic, "in the normal closure" if name in seen else "dev or bench only"))
print("RESULTS_JSON " + json.dumps({"locked_registry_crates": len(rows) + len(missing), "read": len(rows),
                                    "normal_closure_crates": len([r for r in rows if r["in_normal_closure"]]),
                                    "normal_closure_non_permissive": [r["crate"] for r in rows if r["in_normal_closure"] and not r["permissive"]],
                                    "missing_from_cache": missing, "non_permissive_or_unknown": nonperm,
                                    "licenses": sorted({r["license"] for r in rows})}, sort_keys=True))
