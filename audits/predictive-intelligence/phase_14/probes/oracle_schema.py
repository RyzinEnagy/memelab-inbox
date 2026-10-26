"""Phase 14 schema oracle: every committed rule-based scenario document against SCENARIO_SCHEMA.json with jsonschema (an oracle
only; the lab's own `behavioral.validate_scenario` is the rule), plus the lab validator on the same documents.

    python -B oracle_schema.py OUT.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
import jsonschema  # noqa: E402

from memelab.predictive import behavioral as BH  # noqa: E402

P14 = REPO / "audits/predictive-intelligence/phase_14"


def main(out: str) -> int:
    schema = json.loads((P14 / "behavioral/SCENARIO_SCHEMA.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    v = jsonschema.Draft202012Validator(schema)
    docs = [json.loads(x)["document"] for x in (P14 / "behavioral/RULE_SCENARIOS_DEV.jsonl").read_text().splitlines()]
    schema_errors = sum(1 for d in docs if list(v.iter_errors(d)))
    lab_errors = sum(1 for d in docs if BH.validate_scenario(d))
    bad = dict(docs[0], fictional=False)
    rep = {"documents": len(docs), "jsonschema_version": __import__("importlib.metadata").metadata.version("jsonschema"),
           "schema_errors": schema_errors, "lab_validator_errors": lab_errors,
           "negative_control_fictional_false": {"jsonschema_errors": len(list(v.iter_errors(bad))), "lab_errors": len(BH.validate_scenario(bad))}}
    Path(out).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps(rep))
    return 0 if schema_errors == 0 and lab_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
