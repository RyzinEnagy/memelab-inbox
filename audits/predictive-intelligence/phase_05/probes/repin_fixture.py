"""Re-pin the constants of tests/test_predictive_asof_fixture.py (definitions hash, schema checksum, snapshot hashes) from the
current code. Run only after a recorded version change (P46); the diff of the test file is the review.

    python -B repin_fixture.py
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

TEST = REPO / "tests" / "test_predictive_asof_fixture.py"


def main() -> None:
    src = TEST.read_text()
    ns = {"__file__": str(TEST), "__name__": "repin"}
    exec(compile(src, str(TEST), "exec"), ns)
    with tempfile.TemporaryDirectory() as d:
        fx, con, _ = ns["build"](Path(d) / "s.sqlite")
        got = {}
        for mode in F.MODES:
            F.build_snapshots(con, feature_version=F.FEATURE_VERSION, mode=mode, now=1792800001.0)
            for r in S.iter_rows(con, "SELECT decision_key, snapshot_sha256 FROM predictive_snapshots WHERE availability_mode=?", (mode,)):
                got[f"{r['decision_key']}:{mode}"] = r["snapshot_sha256"]
        con.close()
    exp = "EXPECTED = {\n" + "".join(f'    "{k}":\n        "{v}",\n' for k, v in sorted(got.items())) + "}"
    src = re.sub(r"EXPECTED = \{\n.*?\n\}", lambda m: exp, src, count=1, flags=re.S)
    src = re.sub(r'FEATURE_SET_SHA = "[0-9a-f]{64}"', f'FEATURE_SET_SHA = "{F.feature_set_sha()}"', src)
    src = re.sub(r'SCHEMA_V1_SHA = "[0-9a-f]{64}"', f'SCHEMA_V1_SHA = "{S._checksum(S.V1_UP)}"', src)
    TEST.write_text(src)
    print(len(got), F.feature_set_sha())


if __name__ == "__main__":
    main()
