"""Prepare public execution logs: replace machine paths, preserve raw local copies.

Usage: python prepare_public_evidence.py RESULTS_DIR RAW_ARCHIVE_DIR
No assertion, result, exit status, or source excerpt is redacted. The raw archive
must be outside the Git checkout; filenames/digests are recorded for comparison.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys


def main():
    results, archive = map(Path, sys.argv[1:])
    archive.mkdir(parents=True, exist_ok=True)
    assert not any(archive.iterdir()), "never overwrite an existing raw archive"
    root = Path(__file__).resolve().parents[4]
    decoder = json.JSONDecoder()
    observations = {}
    for kind in ["baseline", "recovery"]:
        log = (results / (kind + "-independent-acceptance.log")).read_text()
        parsed = []
        for match in re.finditer(r'^[F.]*({.*)$', log, re.MULTILINE):
            try:
                obj, _ = decoder.raw_decode(match.group(1))
                if "case" in obj:
                    parsed.append(obj)
            except ValueError:
                pass
        assert len(parsed) == 10, (kind, len(parsed))
        observations[kind] = parsed
    assert observations["baseline"] == observations["recovery"]
    (results / "probe-observations.json").write_text(json.dumps(observations, indent=2) + "\n")
    records = []
    for path in sorted(results.iterdir()):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        shutil.copy2(path, archive / path.name)
        text = raw.decode()
        text = text.replace(str(root), "<REVIEW_ROOT>")
        text = text.replace("/private/tmp/m00-clean-baseline", "<CLEAN_BASELINE>").replace("/private/tmp/m00-clean-recovery", "<CLEAN_RECOVERY>")
        text = re.sub(r"/(?:private/)?var/folders/[^\s\"'<>]+", "<TEMP_PATH>", text)
        text = re.sub(r"/Users/[^/\s\"']+/.cache/codex-runtimes/[^\s\"'<>]+", "<PYTHON_RUNTIME_PATH>", text)
        public = text.encode()
        path.write_bytes(public)
        records.append({"file": path.name, "raw_sha256": hashlib.sha256(raw).hexdigest(),
                        "published_sha256": hashlib.sha256(public).hexdigest(), "machine_paths_replaced": public != raw})
    (results / "publication-redactions.json").write_text(json.dumps({"policy": "Machine-specific absolute paths only; raw local copies retained outside repository",
             "files": records}, indent=2) + "\n")
    print(f"Prepared {len(records)} files; 10 identical probe observations per checkout; raw logs retained locally")


if __name__ == "__main__":
    main()
