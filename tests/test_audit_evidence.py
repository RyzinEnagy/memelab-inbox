"""M00 tests: a partial recovery must never be misrepresented as acceptance."""
import json
from pathlib import Path

from tools.check_audit_evidence import inspect

ROOT = Path(__file__).resolve().parents[1]


def test_current_m00_evidence_is_intact_but_gate_blocked():
    record = inspect(ROOT)
    assert record['integrity_errors'] == []
    assert record['recovered'] == 6
    assert record['required'] == 8
    assert record['missing'] == ['02_ARCHITECTURE_AUDIT.md', '03_RESEARCH_VALIDITY.md']
    assert record['status'] == 'BLOCKED'


def test_tampered_recovered_document_fails_integrity(tmp_path):
    root = tmp_path
    source = ROOT / 'audits' / 'social-intelligence'
    target = root / 'audits' / 'social-intelligence'
    (target / 'recovered').mkdir(parents=True)
    manifest = json.loads((source / 'EVIDENCE_MANIFEST.json').read_text())
    # Copy only the necessary files and weaken no production or source assertions.
    for entry in manifest['required_sources']:
        if entry['status'] == 'RECOVERED':
            p = source / entry['path']
            q = target / entry['path']
            q.parent.mkdir(parents=True, exist_ok=True)
            q.write_bytes(p.read_bytes())
    (target / 'EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest))
    (target / 'EVIDENCE_CROSSWALK.md').write_text('# M00 finding-to-evidence crosswalk\n')
    victim = target / 'recovered' / '00_BASELINE.md'
    victim.write_bytes(victim.read_bytes() + b'UNAUTHORIZED CHANGE')
    assert any('checksum' in e for e in inspect(root)['integrity_errors'])


def test_original_empty_archive_does_not_pass(tmp_path):
    source = ROOT / 'audits' / 'social-intelligence'
    target = tmp_path / 'audits' / 'social-intelligence'
    target.mkdir(parents=True)
    (target / 'EVIDENCE_MANIFEST.json').write_bytes((source / 'EVIDENCE_MANIFEST.json').read_bytes())
    (target / 'EVIDENCE_CROSSWALK.md').write_text('# M00 finding-to-evidence crosswalk\n')
    result = inspect(tmp_path)
    assert result['status'] == 'INVALID'
    assert len(result['integrity_errors']) >= 6


def test_unreviewed_manifest_cannot_claim_m00_complete(tmp_path):
    source = ROOT / 'audits' / 'social-intelligence'
    target = tmp_path / 'audits' / 'social-intelligence'
    target.mkdir(parents=True)
    manifest=json.loads((source / 'EVIDENCE_MANIFEST.json').read_text())
    manifest['independent_review'] = 'PENDING'
    for entry in manifest['required_sources']:
        if entry['status'] == 'MISSING':
            # Even a forged status cannot produce an accepted manifest.
            entry['status']='RECOVERED'
    (target / 'EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest))
    (target / 'EVIDENCE_CROSSWALK.md').write_text('# M00 finding-to-evidence crosswalk\n')
    result=inspect(tmp_path)
    assert result['status'] == 'INVALID'
    assert len(result['integrity_errors']) >= 2
