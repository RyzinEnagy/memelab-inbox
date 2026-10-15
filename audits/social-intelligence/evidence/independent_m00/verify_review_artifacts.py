"""Verify review references independently of the earlier M00 inventory checker.

Run from the repository root. Required Git objects: application 698f73b,
publication b4c4216, recovery 3b434e1, optional comparison 3f27fc7.
This verifies bytes/references, never accepts a research or release gate.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path.cwd()
AUDIT = ROOT / "audits/social-intelligence"
OUT = AUDIT / "evidence/independent_m00/results"
PIN = "698f73b854567ce60b56ce275b5ab6822a9d5f60"
RECOVERY = "3b434e1dcc59290d993a638ca615f61b929189bc"
PUBLICATION = "b4c4216b9391227be5fdfe7cfe20b60e32d9e8f6"
ORIGINAL_UPLOADS = {
    "02_ARCHITECTURE_AUDIT.md": "0584201710ce79b47e00c9e05547df2eefda4c9756e5211e92de4e4d2fbb24de",
    "03_RESEARCH_VALIDITY.md": "06cd96136950a1bcebe03a6fcd8cf92ca68d1d82b6a72385b54d93112d203322",
    "phase02_FINDINGS.md": "694dd5e52acc6ac4074c010363acc9a283f9f2c06a5106247de89c149d78fc8d",
    "phase03_FINDINGS.md": "4a4a18c1462c8047eb03f86f6a67a49984ebd6b9ef5c6963f3f47b1493192964",
}


def git(*args):
    return subprocess.check_output(["git", *args])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = []
    manifest = json.loads((AUDIT / "EVIDENCE_MANIFEST.json").read_text())
    for entry in manifest["required_sources"] + manifest["supporting_sources"]:
        blob = (AUDIT / entry["path"]).read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        assert digest == entry["sha256"] and len(blob) == entry["bytes"], entry["path"]
        if entry["name"] in ORIGINAL_UPLOADS:
            assert digest == ORIGINAL_UPLOADS[entry["name"]]
        sources.append({"name": entry["name"], "bytes": len(blob), "sha256": digest,
                        "manifest_match": True, "independent_original_upload_digest": ORIGINAL_UPLOADS.get(entry["name"]),
                        "origin_note": entry["origin_note"]})
    cross = json.loads((AUDIT / "M00_INDEPENDENT_CROSSWALK.json").read_text())
    expected = {*(f"AUD-{i:03d}" for i in range(1, 34)), *(f"ARCH-{i:03d}" for i in range(1, 16)),
                *(f"ADV-{i:03d}" for i in range(1, 10)), *(f"OPS-{i:03d}" for i in range(1, 11))}
    assert len(cross["rows"]) == 67 and {r["id"] for r in cross["rows"]} == expected
    reqs = (AUDIT / "recovered/REQUIREMENTS_MATRIX.md").read_text()
    checked_code = set()
    for row in cross["rows"]:
        assert row["status"] == "OPEN" and row["sources"] and row["code"]
        for source in row["sources"]:
            lines = (AUDIT / source["path"]).read_text().splitlines()
            assert "\n".join(lines[source["start"] - 1:source["end"]]) == source["evidence_excerpt"]
        for c in row["code"]:
            lines = git("show", f"{c['ref']}:{c['path']}").decode().splitlines()
            snippet = "\n".join(lines[c["start"] - 1:c["end"]]) + "\n"
            assert hashlib.sha256(snippet.encode()).hexdigest() == c["snippet_sha256"]
            checked_code.add((c["ref"], c["path"], c["start"], c["end"]))
        for req in row["requirements"]:
            assert "**" + req + "**" in reqs
    req_ids = re.findall(r"\*\*(REQ-\d\d-\d\d)\*\*", reqs)
    assert len(req_ids) == len(set(req_ids)) == 105
    files = []
    for path in git("ls-tree", "-rz", "--name-only", PIN).decode().split("\0"):
        if path:
            blob = git("show", f"{PIN}:{path}")
            files.append({"path": path, "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()})
    archive = git("archive", "--format=tar", PIN)
    snapshot = {"commit": PIN, "git_tree": git("rev-parse", PIN + "^{tree}").decode().strip(),
                "git_archive_tar_sha256": hashlib.sha256(archive).hexdigest(), "git_archive_tar_bytes": len(archive),
                "files": files, "note": "Fresh deterministic snapshot digest; does not recover the original audit ZIP or raw test logs."}
    (OUT / "pinned-source-snapshot.json").write_text(json.dumps(snapshot, indent=2) + "\n")
    diff = git("diff", "--name-only", PUBLICATION, RECOVERY).decode().splitlines()
    forbidden = [p for p in diff if p.startswith(("memelab/", "bridge/", "data/", "state/", "inbox/"))]
    assert forbidden == []
    pin_diff = git("diff", "--name-only", PIN, RECOVERY, "--", "memelab", "bridge", "data", "state", "inbox").decode().splitlines()
    assert pin_diff == []
    old_tree = git("ls-tree", "-r", "--name-only", PUBLICATION, "audits/social-intelligence").decode().splitlines()
    absent = [e["name"] for e in manifest["required_sources"] if
              "audits/social-intelligence/" + e["name"] not in old_tree]
    assert len(absent) == 7 and "06_STRATEGIC_IMPROVEMENTS.md" not in absent
    record = {"source_documents": sources, "manifest_matches": len(sources), "original_upload_digests_matched": 4,
              "crosswalk_ids": 67, "checked_code_spans": len(checked_code), "requirements": len(req_ids),
              "m00_changed_files": diff, "forbidden_path_changes": forbidden, "pinned_application_path_changes": pin_diff,
              "original_publication_missing_inputs": absent, "decision": "BLOCKED",
              "limits": ["04/05 original bytes unavailable", "00/RM/01 independent original Library bytes unavailable",
                         "Original staged prompt, probe and raw-log archives absent; fresh probes are new evidence"]}
    (OUT / "independent-integrity.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: record[k] for k in ["manifest_matches", "original_upload_digests_matched", "crosswalk_ids",
                                           "checked_code_spans", "requirements", "decision"]}, indent=2))


if __name__ == "__main__":
    main()
