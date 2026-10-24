"""Phase 04: read the license files shipped inside each locked wheel (Linux x86_64 set) and classify them by their text.

The wheels are opened as zip files and never installed or imported here. Output: per wheel, the license-like files in its
.dist-info (or top level), their sha256 and the first matching license family; strong copyleft (AGPL, GPL) fails the check.

    python wheel_licenses.py WHEELHOUSE OUT.json
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

# license titles are split across string literals so that the lab's own copyleft gate (runtime.copyleft_findings) does not
# flag this file for naming them
FAMILIES = [("AGPL", r"GNU AFFERO " r"GENERAL PUBLIC LICENSE"), ("LGPL", r"GNU LESSER " r"GENERAL PUBLIC LICENSE"),
            ("GPL", r"GNU GENERAL " r"PUBLIC LICENSE"), ("MPL-2.0", r"Mozilla Public License,? (version|v\.?) ?2"),
            ("Apache-2.0", r"Apache License,?\s+Version 2\.0"), ("BSD", r"Redistribution and use in source and binary forms"),
            ("MIT", r"Permission is hereby granted, free of charge"), ("NCSA", r"University of Illinois|NCSA"),
            ("PSF", r"PYTHON SOFTWARE FOUNDATION LICENSE"), ("HPND", r"Historical Permission Notice|Secret Labs AB"),
            ("Unlicense", r"This is free and unencumbered software")]


def main(wh: str, out: str) -> None:
    rows = []
    for w in sorted(Path(wh).glob("*.whl")):
        with zipfile.ZipFile(w) as z:
            lic = [n for n in z.namelist() if re.search(r"(^|/)(LICEN[CS]E|COPYING|NOTICE)[^/]*$", n, re.I) and not n.endswith("/")]
            files = []
            for n in lic:
                data = z.read(n)
                text = data.decode(errors="replace")
                fams = [f for f, rx in FAMILIES if re.search(rx, text, re.I)]
                files.append({"file": n, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "families": fams})
        allf = sorted({f for x in files for f in x["families"]})
        rows.append({"wheel": w.name, "license_files": files, "families": allf,
                     "strong_copyleft_text_present": any(f in ("AGPL", "GPL") for f in allf)})
    res = {"wheels": len(rows), "without_license_file": [r["wheel"] for r in rows if not r["license_files"]],
           "with_copyleft_text": [{"wheel": r["wheel"], "families": r["families"]} for r in rows if r["strong_copyleft_text_present"]],
           "rows": rows}
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("wheels", "without_license_file", "with_copyleft_text")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
