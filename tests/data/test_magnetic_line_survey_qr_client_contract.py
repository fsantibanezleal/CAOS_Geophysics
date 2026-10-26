"""Additive QR descriptor parity; original frozen qualification files untouched."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_survey_contract_qr as qr


def test_qr_client_exact_closed_schema_descriptors():
    path=Path(__file__).parents[2]/'frontend/src/features/magneticLineSurvey/schema_qr.json'
    assert json.loads(path.read_text(encoding='utf-8'))==json.loads(json.dumps(qr.SCHEMAS))
