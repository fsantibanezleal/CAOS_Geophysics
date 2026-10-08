"""Actual supplied-generation parity and negative receipt binding, no fit."""

import argparse
import copy
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]/'data-pipeline'))
from magnetic_result_bundle import read_bundle
from magnetic_result_view import project_result
from magnetic_local_paths import external_path
from magnetic_survey_json import canonical, InputError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    imported = read_bundle(external_path(args.bundle))
    result, request = imported['result'], imported['request']
    receipt = dict(job_id='ac0f3d62-a176-4019-92e0-06b14a3be476',
        dataset_id='84d72b03-8f93-49cd-bd26-dee9800a03ae', source_id=request['source']['id'],
        generation_sha256=imported['generation_sha256'], configuration_sha256=result['identity']['configuration_sha256'],
        original_sha256=request['source']['original_sha256'])
    view = project_result(args.bundle, receipt)
    assert len(view['rows']) == len(result['inventory']['row_ids'])
    for j, i in enumerate(result['prediction']['rows']['data']):
        c = len(view['components'])
        row = view['rows'][i]
        assert row['row_id'] == result['inventory']['row_ids'][i]
        assert row['predicted_nT'] == result['prediction']['values_nT']['data'][c*j:c*j+c]
        assert row['residual_nT'] == result['prediction']['residual_nT']['data'][c*j:c*j+c]
        assert row['residual_nT'] == [o-p for o, p in zip(row['observed_nT'], row['predicted_nT'])]
    assert view['model'] == result['model'] and view['history'] == result['history']
    assert not view['online_admitted'] and not any(view['claims'].values())
    rejected = []
    for key in ('source_id', 'generation_sha256', 'configuration_sha256', 'original_sha256'):
        tampered = copy.deepcopy(receipt)
        tampered[key] = '0'*64
        try:
            project_result(args.bundle, tampered)
        except InputError:
            rejected.append(key)
        else:
            raise AssertionError('Unbound '+key+' was accepted')
    proof = dict(schema='magnetic-result-parity-1', receipt=receipt, actual_original_rows=len(view['rows']),
        actual_fitted_rows=len(result['prediction']['rows']['data']), native_numeric_exact_equality=True,
        rejected_binding_changes=rejected, api_owner_mounted=False, browser_verified=False, field_verified=False)
    output = external_path(args.output)
    with output.open('xb') as stream:
        stream.write(canonical(proof))
        stream.flush()
        os.fsync(stream.fileno())
    with output.with_suffix('.view.json').open('xb') as stream:
        stream.write(canonical(view))
        stream.flush()
        os.fsync(stream.fileno())
    print(imported['generation_sha256'])


if __name__ == '__main__':
    main()
