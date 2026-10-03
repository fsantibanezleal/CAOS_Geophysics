"""Local source-valid MT candidate replay; no bake or invocation in hosted CI."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'data-pipeline'))
sys.path.insert(0, str(ROOT / 'scripts'))
from electromagnetics import (  # noqa: E402
    MT_BOUNDS, METHODS, bootstrap_mt, curves, identifiability, impedance,
    invert_mt, objective_residual,
)
from geology import VARIANTS, mt_model, registry  # noqa: E402
from provenance import generator_fingerprint  # noqa: E402
from rebuild import REUSABLE_VERSIONS, jsonable  # noqa: E402


PREDICTION_RTOL = 3e-5
PREDICTION_ATOL = 1e-10
METRIC_RTOL = 2e-4
METRIC_ATOL = 2e-5
SOURCE_FILES = (
    'data-pipeline/electromagnetics.py', 'data-pipeline/edi.py',
    'data-pipeline/geology.py', 'data-pipeline/provenance.py',
    'data-pipeline/rebuild.py', 'data-pipeline/seismic.py',
    'scripts/build_field_screen.py', 'scripts/validate_mt_replays.py',
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> str:
    value = hashlib.sha256()
    for path in sorted(p for p in root.rglob('*') if p.is_file()):
        value.update(path.relative_to(root).as_posix().encode() + b'\0')
        value.update(bytes.fromhex(digest(path)))
    return value.hexdigest()


def check_close(actual, expected, *, prediction=False, atol=None):
    np.testing.assert_allclose(
        actual, expected, rtol=PREDICTION_RTOL if prediction else METRIC_RTOL,
        atol=atol if atol is not None else PREDICTION_ATOL if prediction else METRIC_ATOL,
    )


def check_finite(value):
    if isinstance(value, dict):
        for child in value.values():
            check_finite(child)
    elif isinstance(value, list):
        for child in value:
            check_finite(child)
    elif isinstance(value, float):
        assert np.isfinite(value), 'Nonfinite artifact value'


def original_input(case: dict, variant: str):
    rho, h = mt_model(case['geometry'], 1.5 if variant == 'contrast' else 1)
    f = np.geomspace(.001 if variant == 'acquisition' else .01, 100, 36)
    active = np.arange(len(f)) % 2 == 0 if variant == 'coverage' else np.ones(len(f), bool)
    clean = impedance(rho, h, f)
    relative = .10 if variant == 'noise' else .025
    sig = relative * abs(clean)
    rng = np.random.default_rng(case['seed'])
    obs = clean + sig * (rng.normal(size=len(f)) + 1j * rng.normal(size=len(f)))
    initial = np.full(len(rho), 100.)
    beta = .3 if variant == 'regularization' else .001
    return rho, h, f, active, clean, sig, obs, initial, beta


def validate_condition(run: dict, case: dict, variant: str, reference: dict, *, replay_bootstrap=True):
    check_finite(run)
    assert (run['id'], run['family'], run['geometry'], run['seed'], run['variant']) == (
        case['id'], 'mt', case['geometry'], case['seed'], variant)
    version = run['provenance']['version']
    assert version in REUSABLE_VERSIONS
    assert run['provenance']['generator_fingerprint'] == generator_fingerprint('mt', version=version)
    assert run['provenance']['synthetic'] is True and run['provenance']['seed'] == case['seed']
    assert run['export_precision_significant_digits'] == 7
    assert run['schema'] == 'inverse-earth/v2' and run['units'] == 'ohm m' and run['data_units'] == 'ohm'
    assert set(run['methods']) == set(METHODS)
    rho, h, f, mask, clean, sig, obs, initial, beta = original_input(case, variant)
    exact = dict(truth=rho, thickness=h, frequencies=f, active=mask.tolist(),
                 clean=curves(clean, f), observed=curves(obs, f), sigma=sig, initial=initial)
    for name, expected in exact.items():
        assert run[name] == jsonable(expected), f'Seeded source mismatch: {name}'
        assert run[name] == reference[name], f'Published input changed: {name}'
    assert run['parameters'] == reference['parameters']
    assert run['parameters']['regularization'] == beta
    rows = []
    for key, method in run['methods'].items():
        solver = method['solver']
        for name in ('device', 'dtype', 'bounds_ohm_m', 'beta', 'initial_model', 'fixed_thickness_m',
                     'objective', 'residual_normalization', 'sigma_definition', 'regularization_normalization'):
            assert solver[name] == reference['methods'][key]['solver'][name], f'Changed solver setting: {name}'
        if key == 'mt-lm':
            assert solver['max_nfev'] == 400
            assert solver['tolerance'] == dict(ftol=1e-10, xtol=1e-10, gtol=1e-10)
        else:
            assert solver['max_steps'] == (1200 if key == 'mt-adam' else 1800)
            assert solver['learning_rate'] == (.06 if key == 'mt-adam' else .015)
            assert solver['seed'] == case['seed']
            for name in ('max_steps', 'learning_rate_schedule', 'parameterization'):
                assert solver[name] == reference['methods'][key]['solver'][name]
        assert solver['device'] == method['device'] == 'cpu'
        model = np.asarray(method['model'])
        assert model.shape == rho.shape and np.all((model >= MT_BOUNDS[0]) & (model <= MT_BOUNDS[1]))
        frames, states, history = method['frames'], method['states'], method['history']
        assert len(frames) == len(states) == len(history) and len(frames) > 1
        assert frames[-1] == method['model'] and frames[0] == initial.tolist()
        assert method['state']['selected_frame'] == method['state_identity']['final_frame_index'] == len(frames) - 1
        assert states[-1]['kind'] == 'selected_final' and method['state_identity']['predictions'] == 'final-model'
        for index, (frame, state, loss) in enumerate(zip(frames, states, history, strict=True)):
            assert state['frame_index'] == index
            residual = objective_residual(np.log(frame), h, f, obs, sig, beta, mask)
            data = float(np.sum(residual[:2 * int(mask.sum())] ** 2))
            prior = float(np.sum(residual[2 * int(mask.sum()):] ** 2))
            check_close(loss, data + prior)
            for name, value in dict(total=data + prior, data=data, regularization=prior).items():
                check_close(state['objective'][name], value)
        pred = impedance(model, h, f)
        predicted = curves(pred, f)
        for name in ('real', 'imag', 'apparent', 'phase'):
            check_close(method['predicted'][name], predicted[name], prediction=True)
        # The existing release gate allows cancellation error proportional to
        # seven-digit observation amplitude, not to a near-zero residual.
        rounding = 2e-6 * max(float(np.max(abs(obs))), float(np.max(abs(pred))), 1e-8)
        check_close(method['residual']['real'], (obs - pred).real, atol=rounding)
        check_close(method['residual']['imag'], (obs - pred).imag, atol=rounding)
        weighted = (pred - obs) / sig
        start_weighted = (impedance(initial, h, f) - obs) / sig
        objective = objective_residual(np.log(model), h, f, obs, sig, beta, mask)
        data = float(np.sum(objective[:2 * int(mask.sum())] ** 2))
        prior = float(np.sum(objective[2 * int(mask.sum()):] ** 2))
        log_rmse = float(np.sqrt(np.mean(np.log(model / rho) ** 2)))
        initial_rmse = float(np.sqrt(np.mean(np.log(initial / rho) ** 2)))
        metrics = dict(wrms=float(np.sqrt(np.mean(abs(weighted) ** 2))),
                       active_component_wrms=float(np.sqrt(np.mean(abs(weighted[mask]) ** 2) / 2)),
                       initial_component_wrms=float(np.sqrt(np.mean(abs(start_weighted[mask]) ** 2) / 2)),
                       objective=data + prior, data_objective=data, regularization_objective=prior,
                       log_model_rmse=log_rmse, initial_log_model_rmse=initial_rmse,
                       model_error_ratio=log_rmse / initial_rmse)
        for name, value in metrics.items():
            check_close(method['metrics'][name], value)
        if (~mask).any():
            check_close(method['metrics']['withheld_component_wrms'],
                        float(np.sqrt(np.mean(abs(weighted[~mask]) ** 2) / 2)))
        else:
            assert method['metrics']['withheld_component_wrms'] is None
        for name, value in dict(total=data + prior, data=data, regularization=prior).items():
            check_close(method['objective'][name], value)
        diag = identifiability(model, h, f, sig, mask)
        assert method['identifiability']['status'] == diag['status']
        assert method['identifiability']['unresolved_layers'] == diag['unresolved_layers']
        status = 'failed' if not solver['success'] or metrics['active_component_wrms'] > 1.5 else 'unresolved'
        if log_rmse >= initial_rmse:
            status = 'failed'
        elif diag['status'] == 'locally_resolved' and status != 'failed':
            status = 'recovered'
        assert method['evaluation']['status'] == status, 'Verdict differs from re-evaluated criteria'
        rows.append(dict(case=case['id'], variant=variant, method=key, status=status,
                         states_replayed=len(frames), source_and_settings_match=True,
                         reference_status=reference['methods'][key]['evaluation']['status'],
                         max_reference_model_difference=float(np.max(abs(model - reference['methods'][key]['model'])))))
    u = run['methods']['mt-lm']['uncertainty']
    samples = np.asarray(u['samples'])
    assert u['requested'] == u['completed'] == u['members'] == 128 and not u['failures']
    assert samples.shape == (128, len(rho)) and u['status'] == 'computed'
    assert u['kind'] == 'conditional-parametric-bootstrap' and u['seed'] == case['seed'] + 100000
    assert u['successful_seeds'] == u['sample_seeds'] == [
        int(child.generate_state(1)[0]) for child in np.random.SeedSequence(u['seed']).spawn(128)]
    assert u['active'] == mask.tolist() and u['fixed_thickness_m'] == h.tolist()
    assert u['beta'] == beta and u['initial_model'] == initial.tolist() and u['bounds_ohm_m'] == list(MT_BOUNDS)
    check_close(u['sigma_per_real_component'], sig)
    assert np.all((samples >= MT_BOUNDS[0]) & (samples <= MT_BOUNDS[1]))
    check_close(u['conditioning_model'], run['methods']['mt-lm']['model'])
    assert u['confidence'] == .95
    check_close(u['quantiles'], [.025, .975])
    lower, upper = np.quantile(samples, u['quantiles'], axis=0)
    for name, value in dict(lower=lower, upper=upper, mean=samples.mean(axis=0),
                            std=samples.std(axis=0, ddof=1), interval_ohm_m=[lower, upper]).items():
        check_close(u[name], value)
    if replay_bootstrap:
        # Reconstruct the pre-export conditioning fit rather than starting from
        # a rounded, potentially weakly identified exported model.
        fitted = invert_mt(h, f, obs, sig, active=mask, initial=initial, beta=beta,
                           methods=('mt-lm',), seed=case['seed'])['mt-lm']['model']
        check_close(run['methods']['mt-lm']['model'], fitted)
        ensemble = bootstrap_mt(fitted, h, f, sig, active=mask, initial=initial,
                                beta=beta, samples=128, seed=case['seed'] + 100000)
        assert ensemble['status'] == 'computed'
        check_close(u['samples'], ensemble['samples'])
    return rows


def validate_field(data: Path, source: Path) -> dict:
    from edi import screen_edi
    from build_field_screen import SOURCE_SHA256, STATION
    assert source.name == STATION and digest(source) == SOURCE_SHA256, 'Pinned cl061 original required'
    manifest = json.loads((data / 'edi/manifest.json').read_text(encoding='utf-8'))
    assert len(manifest['field_screens']) == 1
    entry = manifest['field_screens'][0]
    assert entry['artifact'] == 'clear-lake-cl061-screen.json'
    artifact = data / 'edi' / entry['artifact']
    assert digest(artifact) == entry['artifact_sha256'] and artifact.stat().st_size == entry['artifact_bytes']
    assert entry['parser_source_sha256'] == digest(ROOT / 'data-pipeline/edi.py')
    assert entry['source_sha256'] == SOURCE_SHA256 and entry['source_bytes'] == source.stat().st_size == 16411
    run = json.loads(artifact.read_text(encoding='utf-8'))
    fresh = screen_edi(source, units='mt', variance_convention='complex', rotation='preserve')
    for name, value in fresh.items():
        assert run[name] == value, f'Fresh cl061 screen differs: {name}'
    assert run['id'] == 'cl061' and len(run['frequencies_hz']) == 42
    assert run['truth'] is None and run['methods'] == {} and run['inversion_performed'] is False
    assert run['one_d_inversion_eligible'] is entry['one_d_inversion_eligible'] is False
    assert run['compatibility']['passes_screen'] is False
    return dict(artifact='edi/' + entry['artifact'], sha256=digest(artifact), bytes=artifact.stat().st_size,
                source_sha256=SOURCE_SHA256, source_bytes=source.stat().st_size,
                parser_source_sha256=entry['parser_source_sha256'], one_d_inversion_eligible=False,
                compatibility=run['compatibility'])


def validate_matrix(catalog: dict):
    cases = [case for case in registry() if case['family'] == 'mt']
    expected = {(case['id'], v) for case in cases for v, _, _ in VARIANTS}
    declared = [(case['id'], v['id']) for case in catalog['cases'] for v in case['variants']]
    assert len(declared) == 24 and set(declared) == expected, 'Complete 24-condition MT matrix required'
    assert catalog['complete'] is False and len(catalog['cases']) == 4, 'Partial candidate, not full release'
    return cases, expected


def validate(data: Path, reference: Path, source: Path, *, expected_canonical_sha256: str):
    assert data.resolve().is_relative_to((ROOT / 'data/experiments').resolve()), 'Ignored candidate only'
    assert data.resolve() != reference.resolve(), 'Never mutate canonical artifacts'
    assert tree_digest(reference) == expected_canonical_sha256, 'Canonical tree changed'
    catalog = json.loads((data / 'catalog.json').read_text(encoding='utf-8'))
    cases, expected = validate_matrix(catalog)
    actual = {(p.parent.name, p.stem) for case in cases for p in (data / case['id']).glob('*.json')}
    assert actual == expected, 'Missing or unexpected MT condition files'
    release = json.loads((data / 'release.json').read_text(encoding='utf-8'))
    assert release['complete'] is False and (release['cases'], release['runs'], release['methods']) == (4, 24, 72)
    entries = {(c['id'], v['id']): v for c in catalog['cases'] for v in c['variants']}
    records, inventory = [], []
    for case in cases:
        for variant, _, _ in VARIANTS:
            entry = entries[case['id'], variant]
            rel = f"{case['id']}/{variant}.json"
            assert entry['path'] == rel
            path = data / rel
            assert digest(path) == entry['sha256'] and path.stat().st_size == entry['bytes']
            run = json.loads(path.read_text(encoding='utf-8'))
            prior_path = reference / rel
            prior = json.loads(prior_path.read_text(encoding='utf-8'))
            for key in METHODS:
                assert run['methods'][key]['metrics'] == entry['methods'][key]['metrics']
                assert run['methods'][key]['evaluation'] == entry['methods'][key]['evaluation']
            records.extend(validate_condition(run, case, variant, prior))
            inventory.append(dict(path=rel, sha256=digest(path), bytes=path.stat().st_size,
                                  reference_sha256=digest(prior_path), source_valid=True,
                                  generator_fingerprint=run['provenance']['generator_fingerprint'],
                                  version=run['provenance']['version'], seed=case['seed']))
            print(f"REPLAY {case['id']}/{variant}: 3 methods, 128 actual bootstrap refits", flush=True)
    field = validate_field(data, source)
    assert tree_digest(reference) == expected_canonical_sha256, 'Canonical changed during replay'
    return dict(
        schema='inverse-earth/mt-source-reconciliation/v1', status='PASS',
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        source_sha256={name: digest(ROOT / name) for name in SOURCE_FILES},
        python=platform.python_version(), platform=platform.platform(),
        dependencies={name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'torch', 'mt-metadata', 'pandas')},
        conditions=24, method_results=len(records), bootstrap_refits=24 * 128,
        states_replayed=sum(row['states_replayed'] for row in records),
        verdicts=dict(Counter(row['status'] for row in records)),
        tolerances=dict(prediction_rtol=PREDICTION_RTOL, prediction_atol=PREDICTION_ATOL,
                        metric_rtol=METRIC_RTOL, metric_atol=METRIC_ATOL,
                        residual_atol='2e-6 * max(abs(observed),abs(prediction),1e-8), existing seven-digit cancellation allowance'),
        catalog_sha256=digest(data / 'catalog.json'), release_sha256=digest(data / 'release.json'),
        canonical_tree_sha256=expected_canonical_sha256, canonical_unchanged=True,
        field_screen=field, edi_manifest_sha256=digest(data / 'edi/manifest.json'),
        artifacts=inventory, records=records,
        inherited_edi='Three synthetic EDI fixtures and two calibration receipts copied unchanged from canonical; not newly executed here',
        claim='Actual current-source MT solve and numerical replay only; retained failed/unresolved methods are not recovery successes. No full-release or live-host acceptance.',
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--reference', type=Path, default=ROOT / 'data/derived/v2')
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--expected-canonical-sha256', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    assert args.report.resolve().is_relative_to(args.data.resolve()), 'Receipt stays in ignored candidate'
    assert not args.report.exists(), 'Preserve previous replay receipt'
    result = validate(args.data, args.reference, args.source,
                      expected_canonical_sha256=args.expected_canonical_sha256)
    result['command'] = [sys.executable, *sys.argv]
    args.report.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')
    print('PASS 24 conditions / 72 methods / 3072 bootstrap refits; cl061 QC-only', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
