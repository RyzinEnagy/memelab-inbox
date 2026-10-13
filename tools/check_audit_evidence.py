"""Read-only validator for M00 audit evidence, never a release/readiness gate.

A clean integrity check (exit 0) is deliberately not a M00 PASS. Use
--require-complete to enforce the eight-source availability gate; it exits 2
while any primary audit input is unavailable or review is pending.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED = (
    '00_BASELINE.md', 'REQUIREMENTS_MATRIX.md', '01_FUNCTIONAL_AUDIT.md',
    '02_ARCHITECTURE_AUDIT.md', '03_RESEARCH_VALIDITY.md',
    '04_ADVERSARIAL_AUDIT.md', '05_OPERATIONS_AND_UX.md',
    '06_STRATEGIC_IMPROVEMENTS.md',
)


def inspect(root: Path, manifest_path: Path | None = None) -> dict:
    audit = root / 'audits' / 'social-intelligence'
    manifest_file = manifest_path or audit / 'EVIDENCE_MANIFEST.json'
    manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
    errors: list[str] = []
    if manifest.get('schema_version') != 1 or manifest.get('remediation_phase') != 'M00':
        errors.append('wrong manifest contract')
    sources = manifest.get('required_sources')
    if not isinstance(sources, list):
        raise ValueError('required_sources must be a list')
    names = [entry.get('name') for entry in sources]
    if len(sources) != 8 or set(names) != set(EXPECTED) or len(names) != len(set(names)):
        errors.append('source inventory does not match the eight required inputs')
    missing: list[str] = []
    recovered: list[str] = []
    for entry in sources:
        name = entry.get('name', '<unknown>')
        rel = entry.get('path', '')
        path = audit / rel
        if not rel or path.resolve() == audit.resolve() or not path.resolve().is_relative_to(audit.resolve()):
            errors.append(f'{name}: invalid path outside audit directory')
            continue
        state = entry.get('status')
        if state == 'RECOVERED':
            recovered.append(name)
            if not path.is_file():
                errors.append(f'{name}: claimed recovered but file is unavailable')
            else:
                data = path.read_bytes()
                if entry.get('bytes') != len(data) or entry.get('sha256') != hashlib.sha256(data).hexdigest():
                    errors.append(f'{name}: checksum or byte count differs from manifest')
        elif state == 'MISSING':
            missing.append(name)
            if path.exists():
                errors.append(f'{name}: file now exists but is still marked missing; reconcile before PASS')
            if entry.get('sha256') is not None or entry.get('bytes') is not None:
                errors.append(f'{name}: missing row contains a purported checksum')
        else:
            errors.append(f'{name}: invalid status {state}')
    review = manifest.get('independent_review')
    if review not in ('PENDING', 'ACCEPTED', 'REJECTED'):
        errors.append('missing or invalid independent review status')
    crosswalk = audit / 'EVIDENCE_CROSSWALK.md'
    if not crosswalk.is_file():
        errors.append('crosswalk missing')
    elif '# M00 finding-to-evidence crosswalk' not in crosswalk.read_text(encoding='utf-8'):
        errors.append('crosswalk marker missing')
    status = 'INVALID' if errors else ('BLOCKED' if missing or review != 'ACCEPTED' else 'READY_FOR_REVIEW')
    return dict(status=status, recovered=len(recovered),required=len(EXPECTED),missing=missing,
                independent_review=review,integrity_errors=errors)


def main() -> int:
    parser = argparse.ArgumentParser(description='Check M00 evidence integrity and acceptance status')
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--require-complete',action='store_true',help='Fail unless eight inputs and independent review are complete')
    ns=parser.parse_args()
    result=inspect(ns.root)
    print(json.dumps(result,indent=2))
    if result['integrity_errors']:
        return 1
    if ns.require_complete and result['status'] != 'READY_FOR_REVIEW':
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
