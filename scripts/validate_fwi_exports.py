"""CUDA replay of every published seismic observation, model and prediction."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'data-pipeline'))
from geology import VARIANTS, registry, seismic_model
from seismic import RECORD_SAMPLES, _relative_mse, independent_start, recovery_evaluation, recovery_metrics, simulate


def validate(data, case_ids=None, variant_ids=None):
    assert torch.cuda.is_available(), 'Full FWI export replay requires CUDA'
    torch.set_num_threads(4)
    records = []
    selected_cases=[case for case in registry() if case['family']=='seismic' and (not case_ids or case['id'] in case_ids)]
    selected_variants=[variant for variant,_,_ in VARIANTS if not variant_ids or variant in variant_ids]
    assert selected_cases and selected_variants
    if case_ids:assert {case['id'] for case in selected_cases}==set(case_ids)
    if variant_ids:assert set(selected_variants)==set(variant_ids)
    with torch.no_grad():
        for case in selected_cases:
            for variant in selected_variants:
                path = data / case['id'] / f'{variant}.json'
                run = json.loads(path.read_text(encoding='utf-8'))
                assert run['export_precision_significant_digits'] == 10
                assert run['id'] == case['id'] and run['variant'] == variant
                torch.manual_seed(case['seed'])
                truth = seismic_model(case['geometry'], 1.15 if variant == 'contrast' else 1)
                initial = independent_start()
                receivers = run['parameters']['receivers']
                clean = simulate(torch.tensor(truth, device='cuda'), run['frequency'], receivers, RECORD_SAMPLES)
                sigma = float(clean.std()) * run['parameters']['noise_fraction']
                observed = clean + torch.randn_like(clean) * sigma
                np.testing.assert_allclose(observed.cpu().numpy()[:, :, ::8], run['observed'], rtol=2e-5, atol=2e-5)
                initial_prediction = simulate(torch.tensor(initial, device='cuda'), run['frequency'], receivers, RECORD_SAMPLES)
                active = torch.tensor(run['active_receivers'], device='cuda')
                for method_id, method in run['methods'].items():
                    model = np.asarray(method['model'], dtype=np.float32).T
                    prediction = simulate(torch.tensor(model, device='cuda'), run['frequency'], receivers, RECORD_SAMPLES)
                    np.testing.assert_allclose(prediction.cpu().numpy()[:, :, ::8], method['predicted'], rtol=2e-5, atol=2e-5,
                                               err_msg=f'{case["id"]}/{variant}/{method_id}: model -> prediction')
                    np.testing.assert_allclose((observed - prediction).cpu().numpy()[:, :, ::8], method['residual'],
                                               rtol=2e-4, atol=2e-5,
                                               err_msg=f'{case["id"]}/{variant}/{method_id}: observation - prediction')
                    metrics = recovery_metrics(model, truth, initial, prediction, observed, initial_prediction, active, sigma)
                    for name, value in metrics.items():
                        np.testing.assert_allclose(value, method['metrics'][name], rtol=2e-5, atol=2e-5,
                                                   err_msg=f'{case["id"]}/{variant}/{method_id}/{name}')
                    assert method['evaluation'] == recovery_evaluation(metrics, case['geometry'] == 'salt')
                    np.testing.assert_allclose(float(_relative_mse(prediction, observed)), method['history'][-1],
                                               rtol=2e-5, atol=2e-5)
                    records.append(dict(case=case['id'], variant=variant, method=method_id,
                                        velocity_rmse=metrics['velocity_rmse'], active_wrms=metrics['active_wrms'],
                                        withheld_wrms=metrics['withheld_wrms'], status=method['evaluation']['status']))
                print(f'REPLAY {case["id"]}/{variant}: {len(run["methods"])} final models', flush=True)
    assert len(records) == 2*len(selected_cases)*len(selected_variants)
    return dict(schema='inverse-earth/fwi-replay/v1', cuda=torch.cuda.get_device_name(0),
                conditions=len(selected_cases)*len(selected_variants), method_results=len(records), records=records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--cases', nargs='+')
    parser.add_argument('--variants', nargs='+')
    args = parser.parse_args()
    result = validate(args.data, args.cases, args.variants)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(f'PASS {result["conditions"]} FWI conditions / {result["method_results"]} CUDA model replays')
