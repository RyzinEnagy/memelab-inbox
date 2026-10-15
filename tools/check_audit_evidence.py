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
    # Preserve original intermediate findings registers as immutable source bytes.
    supporting = manifest.get('supporting_sources', [])
    if not isinstance(supporting, list):
        errors.append('invalid supporting-source inventory')
        supporting = []
    support_names = [item.get('name') for item in supporting]
    if len(supporting) != 2 or set(support_names) != {'phase02_FINDINGS.md', 'phase03_FINDINGS.md'}:
        errors.append('missing or duplicated historical Phase 02/03 findings snapshots')
    for entry in supporting:
        rel = entry.get('path', '')
        path = audit / rel
        if not rel or not path.resolve().is_relative_to(audit.resolve()) or not path.is_file():
            errors.append(f'{entry.get("name")}: missing or unsafe supporting-source path')
        elif entry.get('status') != 'RECOVERED' or entry.get('bytes') != path.stat().st_size or entry.get('sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
            errors.append(f'{entry.get("name")}: supporting-source integrity mismatch')
    review = manifest.get('independent_review')
    if review not in ('PENDING', 'ACCEPTED', 'REJECTED'):
        errors.append('missing or invalid independent review status')
    crosswalk = audit / 'EVIDENCE_CROSSWALK.md'
    if not crosswalk.is_file():
        errors.append('crosswalk missing')
    elif '# M00 finding-to-evidence crosswalk' not in crosswalk.read_text(encoding='utf-8'):
        errors.append('crosswalk marker missing')
    else:
        rows = crosswalk.read_text(encoding='utf-8').splitlines()
        import re
        recorded = [re.match(r'^\| ((?:AUD|ARCH|ADV|OPS)-\d{3}) \|', line) for line in rows]
        recorded = [m.group(1) for m in recorded if m]
        expected = {*(f'AUD-{n:03d}' for n in range(1,34)), *(f'ARCH-{n:03d}' for n in range(1,16)), *(f'ADV-{n:03d}' for n in range(1,10)), *(f'OPS-{n:03d}' for n in range(1,11))}
        if set(recorded) != expected or len(recorded) != len(expected):
            errors.append('crosswalk IDs incomplete or duplicated')
        canonical = audit / 'FINDINGS.md'
        if canonical.is_file():
            tab = canonical.read_text(encoding='utf-8').split('## AUD-001',1)[0]
            got = re.findall(r'^\| (AUD-\d{3}) \|', tab, re.MULTILINE)
            expected_aud={f'AUD-{n:03d}' for n in range(1,34)}
            if set(got) != expected_aud or len(got)!=33:
                errors.append('canonical AUD register is not a unique full 33-ID inventory')
        else:
            errors.append('canonical FINDINGS.md missing')
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
