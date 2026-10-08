"""Source contract parity, without persisting scientific data in the product."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_contract as base
import magnetic_line_survey_contract as v1
import magnetic_line_survey_contract_v2 as v2
import magnetic_lines as bounded


def test_client_closed_schema_exactly_matches_all_pinned_server_descriptors():
    expected=dict(v1=v1.SCHEMAS,v2=v2.SCHEMAS,
        environment={name:bounded.RESULT_TABLES[name] for name in ('Environment','EnginePin','FilePin')},
        parameters=base.PARAMETERS,reasons=bounded.CROSSOVER_REASONS)
    source=Path(__file__).parents[2]/'frontend/src/features/magneticLineSurvey/schema.json'
    assert json.loads(source.read_text(encoding='utf-8'))==json.loads(json.dumps(expected))
