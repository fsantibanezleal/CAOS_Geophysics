"""Read complete case receipts after fitting; retain all pending/failure cells."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]/'data-pipeline'))
from magnetic_local_paths import external_path
from magnetic_result_bundle import read_bundle
from magnetic_survey_json import canonical, digest
from magnetic_s2_evaluation import evaluate_model, adverse_verdict


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--roots', nargs='+', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    roots = [external_path(p) for p in args.roots]
    generator_path = Path(__file__).parents[1]/'tests'/'fixtures'/'magnetic_survey'/'generate.py'
    spec = importlib.util.spec_from_file_location('post_freeze_original_s2', generator_path)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    lanes = ('secondary_enu_nT', 'linear_tmi_nT', 'exact_total_anomaly_nT')
    cells = []
    for regime in 'ABCDEF':
        for quantity in lanes:
            name = regime+'-'+quantity
            paths = [root/name/'scientific-verdict.json' for root in roots if (root/name/'scientific-verdict.json').exists()]
            if len(paths) > 1:
                raise ValueError('Ambiguous repeated case cannot select an attractive result')
            cell = dict(regime=regime, quantity=quantity, status='pending_no_terminal_receipt', outer_rms_nT=None,
                        model_evaluation=None, alternate_start_sensitivity='not_evaluated', mesh_sensitivity='not_evaluated')
            if paths:
                path = paths[0]
                raw = path.read_bytes()
                verdict = json.loads(raw)
                cell.update(status=verdict['scientific_verdict'], actual=verdict,
                            receipt_sha256=hashlib.sha256(raw).hexdigest())
                if verdict['result_status'] == 'complete' and (path.parent/'generation'/'manifest.json').exists():
                    imported = read_bundle(path.parent/'generation')
                    result, request = imported['result'], imported['request']
                    evaluator = json.loads((path.parent/'evaluator.json').read_bytes())
                    expected = generator.generate_control(regime, quantity)
                    if (evaluator['regime'] != regime or evaluator['quantity'] != quantity
                            or evaluator['modelling_request_sha256'] != digest(request)
                            or evaluator['bodies'] != expected['bodies'] or evaluator['truth_field'] != expected['truth_field']
                            or evaluator['provenance'] != expected['provenance']
                            or hashlib.sha256(expected['original_bytes']).hexdigest() != request['source']['original_sha256']):
                        raise ValueError('Independent unchanged evaluator/original/request identity differs; no alternate truth')
                    cell.update(generation_sha256=imported['generation_sha256'], outer_rms_nT=result['metrics']['outer']['rms_nT'],
                        model_evaluation=evaluate_model(request['geometry']['mesh'], evaluator['bodies'], result['model']['chi_si']['data']),
                        candidate_comparison=result['candidates'], selected=result['selected'],
                        local_resolution_kind=result['diagnostics']['resolution_kind'], field_truth=False)
            cells.append(cell)
    for cell in cells:
        if cell['regime'] in 'DE':
            paired = next(c for c in cells if c['regime'] == 'A' and c['quantity'] == cell['quantity'])
            cell['adverse_evaluation'] = adverse_verdict(cell['outer_rms_nT'], paired['outer_rms_nT'])
    proof = dict(schema='magnetic-complete-s2-evaluation-1', frozen_case_count=18, cases=cells,
        all_terminal=all(c['status'] != 'pending_no_terminal_receipt' for c in cells),
        full_method_accepted=False, field_verified=False, online_admitted=False, thresholds_weakened=False,
        fitted_and_failed_are_not_averaged=True)
    with external_path(args.output).open('xb') as stream:
        stream.write(canonical(proof))
        stream.flush()
        os.fsync(stream.fileno())
    print('Actual terminal cases: '+str(sum(c['status'] != 'pending_no_terminal_receipt' for c in cells))+'/18')


if __name__ == '__main__':
    main()
