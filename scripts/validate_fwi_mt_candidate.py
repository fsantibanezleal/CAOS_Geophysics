"""Independent full-candidate MT replay using unchanged numerical checks; no solves for FWI here."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_mt_replays as mt  # noqa: E402
from geology import registry, VARIANTS  # noqa: E402


def full_matrix(catalog):
    expected = {(c['id'], v) for c in registry() for v, _, _ in VARIANTS}
    declared = [(c['id'], v['id']) for c in catalog['cases'] for v in c['variants']]
    assert catalog['complete'] is True and len(catalog['cases']) == 20
    assert len(declared) == 120 and set(declared) == expected, 'Complete unique full matrix required'
    assert sum(len(v['methods']) for c in catalog['cases'] for v in c['variants']) == 348


def validate(data, reference, source, expected_canonical_sha256):
    assert data.resolve().is_relative_to((ROOT/'data/experiments').resolve()), 'Ignored candidate only'
    assert mt.tree_digest(reference) == expected_canonical_sha256, 'Canonical tree changed'
    catalog = json.loads((data/'catalog.json').read_text(encoding='utf-8'))
    full_matrix(catalog)
    spec = importlib.util.spec_from_file_location('full_candidate_gate', ROOT/'scripts/check_artifacts.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    gate.ROOT = data
    artifact_gate = gate.validate()
    records, inventory = [], []
    for case in catalog['cases']:
        for variant in case['variants']:
            relative = f'{case["id"]}/{variant["id"]}.json'
            assert variant['path'] == relative
            path = data/relative
            assert (mt.digest(path), path.stat().st_size) == (variant['sha256'], variant['bytes'])
            run = json.loads(path.read_text(encoding='utf-8'))
            inventory.append(dict(path=relative, sha256=mt.digest(path), bytes=path.stat().st_size,
                                  reference_sha256=mt.digest(reference/relative),
                                  version=run['provenance']['version'],
                                  generator_fingerprint=run['provenance']['generator_fingerprint']))
            if case['family'] == 'mt':
                original = json.loads((reference/relative).read_text(encoding='utf-8'))
                records.extend(mt.validate_condition(run, case, variant['id'], original))
                print(f'REPLAY {relative}: 3 methods, 128 actual bootstrap refits', flush=True)
    field = mt.validate_field(data, source)
    assert mt.tree_digest(reference) == expected_canonical_sha256, 'Canonical changed during replay'
    source_files = [*mt.SOURCE_FILES, 'data-pipeline/seismic_batch.py', 'data-pipeline/assemble_fwi_candidate.py',
                    'data-pipeline/catalog.py', 'scripts/check_artifacts.py',
                    'scripts/validate_fwi_exports.py', 'scripts/validate_fwi_mt_candidate.py']
    verdicts = Counter(m['evaluation']['status'] for c in catalog['cases'] for v in c['variants']
                       for m in v['methods'].values())
    return dict(schema='inverse-earth/combined-candidate-mt-replay/v1', status='PASS',
                recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                source_sha256={name: mt.digest(ROOT/name) for name in source_files},
                python=platform.python_version(), platform=platform.platform(),
                dependencies={name: importlib.metadata.version(name) for name in
                              ('numpy', 'scipy', 'torch', 'deepwave', 'mt-metadata', 'pandas')},
                artifact_gate=artifact_gate, conditions=120, method_results=348,
                mt_conditions=24, mt_method_results=len(records), bootstrap_refits=24*128,
                states_replayed=sum(r['states_replayed'] for r in records),
                mt_verdicts=dict(Counter(r['status'] for r in records)), verdicts=dict(verdicts),
                tolerances=dict(prediction_rtol=mt.PREDICTION_RTOL, prediction_atol=mt.PREDICTION_ATOL,
                                metric_rtol=mt.METRIC_RTOL, metric_atol=mt.METRIC_ATOL,
                                residual_atol='existing 2e-6 maximum data/prediction amplitude cancellation allowance'),
                catalog_sha256=mt.digest(data/'catalog.json'), release_sha256=mt.digest(data/'release.json'),
                canonical_tree_sha256=expected_canonical_sha256, canonical_unchanged=True,
                field_screen=field, edi_manifest_sha256=mt.digest(data/'edi/manifest.json'),
                artifacts=inventory, records=records,
                claim='Independent combined-source MT/field replay. FWI replay and tests are separately required. '
                      'Synthetic recovery is not geological truth; host/product acceptance is not asserted.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--reference', type=Path, default=ROOT/'data/derived/v2')
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--expected-canonical-sha256', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    assert args.report.resolve().is_relative_to((ROOT/'data/experiments').resolve()), 'Ignored receipt only'
    assert not args.report.exists(), 'Preserve previous receipt'
    result = validate(args.data, args.reference, args.source, args.expected_canonical_sha256)
    result['command'] = [sys.executable, *sys.argv]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    print('PASS full 120/348 artifact gate; MT 4038 states and 3072 refits; cl061 QC-only', flush=True)


if __name__ == '__main__':
    main()
