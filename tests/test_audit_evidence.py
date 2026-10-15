"""M00 tests: a partial recovery must never be misrepresented as acceptance."""
import json
from pathlib import Path

from tools.check_audit_evidence import inspect

ROOT = Path(__file__).resolve().parents[1]


def test_current_m00_evidence_is_intact_but_gate_blocked():
    record = inspect(ROOT)
    assert record['integrity_errors'] == []
    assert record['recovered'] == 8
    assert record['required'] == 8
    assert record['missing'] == []
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
    (target / 'EVIDENCE_CROSSWALK.md').write_bytes((source / 'EVIDENCE_CROSSWALK.md').read_bytes())
    (target / 'FINDINGS.md').write_bytes((source / 'FINDINGS.md').read_bytes())
    victim = target / 'recovered' / '00_BASELINE.md'
    victim.write_bytes(victim.read_bytes() + b'UNAUTHORIZED CHANGE')
    assert any('checksum' in e for e in inspect(root)['integrity_errors'])


def test_original_empty_archive_does_not_pass(tmp_path):
    source = ROOT / 'audits' / 'social-intelligence'
    target = tmp_path / 'audits' / 'social-intelligence'
    target.mkdir(parents=True)
    (target / 'EVIDENCE_MANIFEST.json').write_bytes((source / 'EVIDENCE_MANIFEST.json').read_bytes())
    (target / 'EVIDENCE_CROSSWALK.md').write_bytes((source / 'EVIDENCE_CROSSWALK.md').read_bytes())
    (target / 'FINDINGS.md').write_bytes((source / 'FINDINGS.md').read_bytes())
    result = inspect(tmp_path)
    assert result['status'] == 'INVALID'
    assert len(result['integrity_errors']) >= 8


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
    (target / 'EVIDENCE_CROSSWALK.md').write_bytes((source / 'EVIDENCE_CROSSWALK.md').read_bytes())
    (target / 'FINDINGS.md').write_bytes((source / 'FINDINGS.md').read_bytes())
    result=inspect(tmp_path)
    assert result['status'] == 'INVALID'
    assert len(result['integrity_errors']) >= 8



def test_recovered_original_findings_and_id_inventory():
    import re
    from hashlib import sha256
    audit = ROOT / 'audits' / 'social-intelligence'
    manifest=json.loads((audit / 'EVIDENCE_MANIFEST.json').read_text())
    assert len(manifest['supporting_sources'])==2
    for entry in manifest['supporting_sources']:
        blob=(audit / entry['path']).read_bytes()
        assert sha256(blob).hexdigest()==entry['sha256']
        assert len(blob)==entry['bytes']
    crosswalk=(audit/'EVIDENCE_CROSSWALK.md').read_text()
    rows=re.findall(r'^\| ((?:AUD|ARCH|ADV|OPS)-\d{3}) \|',crosswalk,re.M)
    assert len(rows)==67 and len(set(rows))==67
    for prefix, count in [('AUD',33),('ARCH',15),('ADV',9),('OPS',10)]:
        assert {i for i in rows if i.startswith(prefix+'-')} == {f'{prefix}-{j:03d}' for j in range(1,count+1)}
    for n in range(18,34):
        assert f'| AUD-{n:03d} |' in crosswalk
        assert 'PENDING PRIMARY REPORT' not in crosswalk
    canonical=(audit/'FINDINGS.md').read_text()
    table=canonical.split('## AUD-001',1)[0]
    assert len(re.findall(r'^\| AUD-\d{3} \|',table,re.M))==33
    assert 'AUD-032' in canonical and 'AUD-002' in canonical


def test_tampering_original_snapshot_fails(tmp_path):
    src=ROOT/'audits'/'social-intelligence'
    dst=tmp_path/'audits'/'social-intelligence'
    dst.mkdir(parents=True)
    manifest=json.loads((src/'EVIDENCE_MANIFEST.json').read_text())
    for entry in manifest['required_sources'] + manifest['supporting_sources']:
        if entry['status']=='RECOVERED':
            p=src/entry['path'];q=dst/entry['path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
    for name in ['EVIDENCE_CROSSWALK.md','FINDINGS.md']:
        (dst/name).write_bytes((src/name).read_bytes())
    (dst/'EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest))
    assert inspect(tmp_path)['status']=='BLOCKED'  # reviewer still not accepted
    victim=dst/'recovered'/'phase03_FINDINGS.md';victim.write_bytes(victim.read_bytes()+b'x')
    record=inspect(tmp_path)
    assert record['status']=='INVALID'
    assert any('supporting-source integrity' in e for e in record['integrity_errors'])


def test_original_upload_hashes_pinned_independently_of_manifest():
    from hashlib import sha256
    source = ROOT / 'audits' / 'social-intelligence' / 'recovered'
    expected = {
        '02_ARCHITECTURE_AUDIT.md': '0584201710ce79b47e00c9e05547df2eefda4c9756e5211e92de4e4d2fbb24de',
        'phase02_FINDINGS.md': '694dd5e52acc6ac4074c010363acc9a283f9f2c06a5106247de89c149d78fc8d',
        '03_RESEARCH_VALIDITY.md': '06cd96136950a1bcebe03a6fcd8cf92ca68d1d82b6a72385b54d93112d203322',
        'phase03_FINDINGS.md': '4a4a18c1462c8047eb03f86f6a67a49984ebd6b9ef5c6963f3f47b1493192964',
    }
    for name, digest in expected.items():
        assert sha256((source / name).read_bytes()).hexdigest() == digest
