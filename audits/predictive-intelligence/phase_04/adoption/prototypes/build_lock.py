"""Phase 04: trim a universal hash lock to the wheels the lab can use and check every hash against PyPI.

Input: a lock written by `uv pip compile --universal --generate-hashes --only-binary :all:` (all wheels of every pinned version).
For each `name==version` it reads PyPI's JSON for that exact version (free, unauthenticated) and keeps only the sha256 of
wheels for CPython 3.13 on Linux x86_64 (manylinux), Windows x86_64 and macOS arm64, plus pure-Python wheels. Every kept
hash must also be in the input lock, and every pin must keep at least one wheel per platform, or the script fails.

    python build_lock.py IN.lock OUT.lock BOM.json PYPI_CACHE_DIR
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))
from memelab.predictive import runtime as R  # noqa: E402

PLAT = {
    "linux_x86_64": re.compile(r"-(cp313-cp313|cp3\d+-abi3|py3-none|py2\.py3-none)-[^-]*manylinux[^-]*x86_64\.whl$|-(py3|py2\.py3)-none-any\.whl$"),
    "win_amd64": re.compile(r"-(cp313-cp313|cp3\d+-abi3|py3-none|py2\.py3-none)-win_amd64\.whl$|-(py3|py2\.py3)-none-any\.whl$"),
    "macos_arm64": re.compile(r"-(cp313-cp313|cp3\d+-abi3|py3-none|py2\.py3-none)-macosx_[0-9_]+_(arm64|universal2)\.whl$|-(py3|py2\.py3)-none-any\.whl$"),
}


def abi3_ok(fn: str) -> bool:
    m = re.search(r"-cp3(\d+)-abi3-", fn)
    return m is None or int(m.group(1)) <= 13


def entries(text: str) -> list[tuple[str, str, str, set[str]]]:
    out, cur = [], []
    for ln in text.splitlines():
        if ln.lstrip().startswith("#") or not ln.strip():
            continue
        cur.append(ln.rstrip("\\").strip())
        if not ln.endswith("\\"):
            joined = " ".join(cur)
            cur = []
            spec = re.sub(r"--hash=sha256:[0-9a-f]{64}", "", joined).strip()
            m = re.match(r"^([A-Za-z0-9._-]+)==([^\s;]+)\s*(;.*)?$", spec)
            out.append((m.group(1), m.group(2), (m.group(3) or "").strip(), set(re.findall(r"sha256:([0-9a-f]{64})", joined))))
    return out


def pypi(name: str, ver: str, cache: Path) -> dict:
    f = cache / f"{name}-{ver}.json"
    if not f.exists():
        time.sleep(1.0)
        body = subprocess.run(["curl", "-sS", "-m", "60", f"https://pypi.org/pypi/{name}/{ver}/json"], capture_output=True, check=True).stdout
        f.write_bytes(body)
    return json.loads(f.read_text())


def main(inp: str, out: str, bom: str, cache: str) -> None:
    cache_dir = Path(cache)
    cache_dir.mkdir(parents=True, exist_ok=True)
    lines, rows, problems = [], [], []
    for name, ver, marker, hashes in entries(Path(inp).read_text()):
        d = pypi(name, ver, cache_dir)
        files = [u for u in d["urls"] if u["packagetype"] == "bdist_wheel" and abi3_ok(u["filename"])]
        keep = {}
        for u in files:
            plats = [p for p, rx in PLAT.items() if rx.search(u["filename"])]
            if plats:
                keep[u["digests"]["sha256"]] = (u["filename"], plats, u["size"])
        for h in keep:
            if h not in hashes:
                problems.append(f"{name}=={ver}: PyPI digest {h[:12]} for {keep[h][0]} not in the input lock")
        covered = {p for _, ps, _ in keep.values() for p in ps}
        needed = set(PLAT)
        if "win32" in marker:
            needed = {"win_amd64"}
        elif "darwin" in marker:
            needed = {"macos_arm64"}
        if not needed <= covered:
            problems.append(f"{name}=={ver}: no wheel for {sorted(needed - covered)}")
        lic = d["info"].get("license_expression") or (d["info"].get("license") or "").splitlines()[0][:40] if (d["info"].get("license_expression") or d["info"].get("license")) else ""
        rows.append({"name": name, "version": ver, "marker": marker, "requires_python": d["info"].get("requires_python"),
                     "license_declared": lic, "upload_time": min(u["upload_time_iso_8601"] for u in d["urls"])[:10],
                     "wheels": [{"file": f, "sha256": h, "platforms": ps, "bytes": sz} for h, (f, ps, sz) in sorted(keep.items(), key=lambda x: x[1][0])]})
        spec = f"{name}=={ver}" + (f" {marker}" if marker else "")
        lines.append(spec + " \\\n" + " \\\n".join(f"    --hash=sha256:{h}" for h in sorted(keep)))
    if Path(out).name.startswith("core"):
        header = ("# memelab predictive core: the numpy the lab already runs (README `pip install pytest numpy`), pinned with wheel hashes\n"
                  "# for CPython 3.13 on Linux x86_64, Windows x86_64 and macOS arm64. The essential engine needs nothing else.\n"
                  "# Check with memelab.predictive.runtime.check_lock; install with runtime.install_argv (PI-D-032).\n")
    else:
        header = ("# memelab predictive research dependencies: CPython 3.13, Linux x86_64, Windows x86_64, macOS arm64 wheels only.\n"
                  "# Build the install command only with memelab.predictive.runtime.install_argv (check_lock first, then\n"
                  "# pip install --require-hashes --only-binary=:all: --no-deps), into a dedicated venv, never the interpreter that\n"
                  "# runs the scheduled lab (docs/predictive-intelligence/DECISIONS.md PI-D-032, PI-D-035).\n")
    text = header + "\n".join(lines) + "\n"
    Path(out).write_text(text)
    guard = R.check_lock(text, {w["sha256"] for r in rows for w in r["wheels"]})
    Path(bom).write_text(json.dumps({"input_lock": Path(inp).name, "packages": rows, "problems": problems, "check_lock": guard},
                                    indent=1) + "\n")
    print(json.dumps({"packages": len(rows), "hashes": sum(len(r["wheels"]) for r in rows), "problems": problems, "check_lock": guard}))
    if problems or guard:
        raise SystemExit(1)


if __name__ == "__main__":
    main(*sys.argv[1:5])
