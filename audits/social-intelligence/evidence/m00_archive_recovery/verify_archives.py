"""Validate supplied original archives and current M00 links without executing them.

Run from the repository root. Zero means integrity PASS, never M00 acceptance.
Original historical reports/results and prior independent results are not edited.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import zipfile


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def verify(audit, root):
    records = json.loads((audit / 'originals/ARCHIVES.json').read_text())
    members = json.loads((audit / 'originals/ARCHIVE_FILES.json').read_text())
    assert len(records['archives']) == 4 and len(members) == 50
    verified_members = 0
    internal_hashes = 0
    credential_hits, placeholders = [], []
    spec = importlib.util.spec_from_file_location('m00_release_scan', root / 'tools/release_audit.py')
    scanner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)
    for archive in records['archives']:
        path = audit / archive['path']
        blob = path.read_bytes()
        assert len(blob) == archive['bytes'] and digest(blob) == archive['sha256'], archive['path']
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            rows = [m for m in members if m['phase'] == archive['phase']]
            assert len(z.infolist()) == len(rows)
            indexed = {m['archive_member']: m for m in rows}
            assert len(indexed) == len(rows)
            for info in z.infolist():
                p = PurePosixPath(info.filename)
                assert not p.is_absolute() and '..' not in p.parts and '\\' not in info.filename
                assert not stat.S_ISLNK(info.external_attr >> 16) and not info.is_dir()
                row = indexed[info.filename]
                data = z.read(info)
                assert data == (audit / row['path']).read_bytes(), row['path']
                assert len(data) == row['bytes'] and digest(data) == row['sha256'], row['path']
                scanner.scan_bytes(row['path'], data, credential_hits, placeholders)
                verified_members += 1
        phase = audit / 'originals' / archive['phase']
        checksums = phase / ('evidence/phase05_manifest.json' if archive['phase'] == 'phase05' else 'evidence/SHA256SUMS.json')
        if checksums.exists():
            for name, expected in json.loads(checksums.read_text()).items():
                data = (phase / name).read_bytes()
                sha = expected if isinstance(expected, str) else expected['sha256']
                assert digest(data) == sha, str(phase / name)
                if isinstance(expected, dict):
                    assert len(data) == expected['bytes']
                internal_hashes += 1
    assert internal_hashes == 43 and not credential_hits
    for entry in records['loose_uploads']:
        data = (audit / entry['preserved_path']).read_bytes()
        assert len(data) == entry['bytes'] and digest(data) == entry['sha256']
    manifest = json.loads((audit / 'EVIDENCE_MANIFEST.json').read_text())
    for entry in manifest['required_sources'] + manifest['supporting_sources']:
        data = (audit / entry['path']).read_bytes()
        assert len(data) == entry['bytes'] and digest(data) == entry['sha256'], entry['path']
    for phase, name in [('phase00', '00_BASELINE.md'), ('phase00', 'REQUIREMENTS_MATRIX.md'), ('phase01', '01_FUNCTIONAL_AUDIT.md')]:
        assert (audit / 'originals' / phase / name).read_bytes() == (audit / 'recovered' / name).read_bytes()
    for phase, name in [('phase04', '04_ADVERSARIAL_AUDIT.md'), ('phase05', '05_OPERATIONS_AND_UX.md')]:
        assert (audit / 'originals' / phase / name).read_bytes() == (audit / 'recovered' / name).read_bytes() + b'\n'
    prompt_lines = (audit / 'originals/phase00/evidence/original-staged-prompts.md').read_text().splitlines()
    matrix = (audit / 'recovered/REQUIREMENTS_MATRIX.md').read_text()
    reqs = []
    for line in matrix.splitlines():
        m = re.match(r'\| \*\*(REQ-\d\d-\d\d)\*\* — (.*?) \|', line)
        if m:
            found = [i + 1 for i, s in enumerate(prompt_lines) if m[2] in s]
            assert found, m[1]
            reqs.append({'id': m[1], 'source_lines': found, 'exact_text_found': True})
    assert len(reqs) == len({r['id'] for r in reqs}) == 105
    cross = json.loads((audit / 'M00_INDEPENDENT_CROSSWALK.json').read_text())
    expected = {*(f'AUD-{i:03d}' for i in range(1,34)), *(f'ARCH-{i:03d}' for i in range(1,16)), *(f'ADV-{i:03d}' for i in range(1,10)), *(f'OPS-{i:03d}' for i in range(1,11))}
    assert len(cross['rows']) == 67 and {r['id'] for r in cross['rows']} == expected
    code = set()
    for row in cross['rows']:
        assert row['status'] == 'OPEN'
        for s in row['sources']:
            lines = (audit / s['path']).read_text().splitlines()
            assert '\n'.join(lines[s['start']-1:s['end']]) == s['evidence_excerpt'], row['id']
        for c in row['code']:
            lines = subprocess.check_output(['git','show',f"{c['ref']}:{c['path']}"], cwd=root).decode().splitlines()
            assert digest(('\n'.join(lines[c['start']-1:c['end']])+'\n').encode()) == c['snippet_sha256']
            code.add((c['ref'],c['path'],c['start'],c['end']))
        assert all(r in {a['id'] for a in reqs} for r in row['requirements'])
        if row['id'].startswith('OPS-'):
            s = row['sources'][0]
            assert s['path'] == 'originals/phase05/FINDINGS.md'
            cells = [s.strip() for s in s['evidence_excerpt'].strip('|').split('|')]
            assert cells[0] == row['id'] and cells[2] == row['original_severity']
            assert row['original_evidence_grade'] == cells[3] + '; ' + cells[4]
    assert len(code) == 83
    application_changes = subprocess.check_output(['git','diff','--name-only','698f73b854567ce60b56ce275b5ab6822a9d5f60','--','memelab','bridge','data','state','inbox'], cwd=root, text=True).splitlines()
    assert not application_changes
    return {'integrity':'PASS','m00_acceptance':'BLOCKED','original_archives':4,'extracted_members':verified_members,
            'embedded_hashes_matched':internal_hashes,'primary_inputs':8,'supporting_snapshots':2,
            'requirements_exact_text_matched':len(reqs),'crosswalk_ids':67,'pinned_code_spans':len(code),
            'primary_ops_rows':10,'credential_findings':credential_hits,'credential_placeholders':placeholders,
            'application_path_changes':application_changes,'remaining':'Original Phase 03 A–E scripts/inputs/raw logs absent; Phase 04 terminated-suite log not supplied.'}, reqs


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--audit', type=Path, default=Path('audits/social-intelligence'))
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    record, reqs = verify(a.audit.resolve(), Path.cwd())
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'archive-integrity.json').write_text(json.dumps(record, indent=2)+'\n')
    (a.out / 'requirement-source-links.json').write_text(json.dumps(reqs, indent=2)+'\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
