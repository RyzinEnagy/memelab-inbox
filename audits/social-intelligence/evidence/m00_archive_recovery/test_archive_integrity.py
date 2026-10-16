"""Negative checks prove that archive integrity failures cannot look like acceptance."""
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
AUDIT = ROOT / 'audits/social-intelligence'
spec = importlib.util.spec_from_file_location('verify_m00_archives', HERE / 'verify_archives.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


@pytest.fixture
def copy(tmp_path):
    dst = tmp_path / 'audit'
    shutil.copytree(AUDIT, dst)
    return dst


def test_tampered_archive_is_rejected(copy):
    path = next((copy / 'originals/phase04').glob('*.zip'))
    path.write_bytes(path.read_bytes() + b'x')
    with pytest.raises(AssertionError):
        v.verify(copy, ROOT)


def test_tampered_extracted_source_is_rejected(copy):
    path = copy / 'originals/phase00/evidence/original-staged-prompts.md'
    path.write_bytes(path.read_bytes() + b'x')
    with pytest.raises(AssertionError):
        v.verify(copy, ROOT)


def test_secondary_ops_severity_cannot_replace_primary_grade(copy):
    path = copy / 'M00_INDEPENDENT_CROSSWALK.json'
    data = json.loads(path.read_text())
    next(r for r in data['rows'] if r['id'] == 'OPS-008')['original_severity'] = 'Medium'
    path.write_text(json.dumps(data))
    with pytest.raises(AssertionError):
        v.verify(copy, ROOT)
