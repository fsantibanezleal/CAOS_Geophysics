"""Source-proved offline candidate assembly. No solves, training or canonical writes."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

from geology import registry, VARIANTS
from provenance import generator_fingerprint

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT/'data/experiments'
BASELINE = 'dce92a1d8693afd60a33ff429dfff59cad4de64d'
FAMILY_MODULES = {
    'gravity': ['geology.py', 'potential.py', 'spatial_inverse.py', 'evaluation.py'],
    'magnetics': ['geology.py', 'potential.py', 'spatial_inverse.py', 'evaluation.py'],
    'mt': ['geology.py', 'electromagnetics.py'],
    'seismic': ['geology.py', 'seismic.py'],
    'joint': ['geology.py', 'potential.py', 'spatial_inverse.py', 'evaluation.py', 'joint.py', 'petrophysics.py'],
    'learned': ['geology.py', 'potential.py', 'spatial_inverse.py', 'evaluation.py', 'learning.py'],
}
VERSION_SEMANTICS = dict(
    kind='isolated source-consistent compatibility candidate', published=False,
    canonical_import=False, release_version_assigned=False, next_release_required=True,
    compatibility_catalog_version='0.04.001', expected_next_patch='0.04.002',
    note='Run versions/fingerprints remain original. Actual release version/evidence require owner review; '
         'this is not the published 0.04.001 science and does not relabel old solver hashes.')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def output_paths(output, receipts, sources):
    output, receipts = output.resolve(), receipts.resolve()
    for path in (output, receipts):
        if path == EXPERIMENTS.resolve() or not path.is_relative_to(EXPERIMENTS.resolve()):
            raise ValueError('Outputs must be distinct children of this worktree data/experiments')
    for left, right in [(output, receipts), *[(output, s.resolve()) for s in sources],
                        *[(receipts, s.resolve()) for s in sources]]:
        if left.is_relative_to(right) or right.is_relative_to(left):
            raise ValueError('Output, receipts and input trees must not overlap')
    if output.exists():
        raise ValueError('Candidate destination must be fresh; existing data will not be overwritten')
    return output, receipts


def baseline_bytes(commit, relative):
    return subprocess.check_output(['git', 'show', f'{commit}:{relative}'], cwd=ROOT)


def family_proof(family, baseline, *, fresh_mt=False):
    modules = []
    for name in sorted(FAMILY_MODULES[family]):
        current = (ROOT/'data-pipeline'/name).read_bytes()
        previous = baseline_bytes(baseline, 'data-pipeline/'+name)
        modules.append(dict(module=name, current_sha256=sha(current), baseline_sha256=sha(previous),
                            unchanged=current == previous))
    if family != 'seismic' and not (family == 'mt' and fresh_mt) and not all(m['unchanged'] for m in modules):
        raise ValueError(f'Cannot reuse changed family: {family}')
    return dict(modules=modules, unchanged=all(m['unchanged'] for m in modules))


def mt_contribution(mt, expected_sha256, source):
    """Read-only, pinned fresh contribution; no canonical fallback or hash rewriting."""
    raw = (mt/'mt-replay.json').read_bytes()
    if not expected_sha256 or sha(raw) != expected_sha256:
        raise ValueError('MT producer receipt hash mismatch')
    receipt = json.loads(raw)
    if (receipt['schema'], receipt['status'], receipt['conditions'], receipt['method_results'],
        receipt['bootstrap_refits'], receipt['canonical_unchanged']) != (
            'inverse-earth/mt-source-reconciliation/v1', 'PASS', 24, 72, 3072, True):
        raise ValueError('Incomplete fresh MT producer receipt')
    names = ['data-pipeline/'+n for n in ('electromagnetics.py', 'edi.py', 'geology.py', 'provenance.py', 'rebuild.py')]
    names += ['scripts/build_field_screen.py', 'scripts/validate_mt_replays.py']
    for name in names:
        if receipt['source_sha256'].get(name) != sha((ROOT/name).read_bytes()):
            raise ValueError('Fresh MT source mismatch: '+name)
    expected = {f'{c["id"]}/{v}.json' for c in registry() if c['family'] == 'mt' for v, _, _ in VARIANTS}
    entries = {r['path']: dict(r) for r in receipt['artifacts']}
    if len(receipt['artifacts']) != 24 or set(entries) != expected:
        raise ValueError('Need all 24 unique fresh MT condition paths')
    for path, entry in entries.items():
        if entry['reference_sha256'] != sha((source/path).read_bytes()) or entry['source_valid'] is not True:
            raise ValueError('MT original reference mismatch: '+path)
    for name, key in [('catalog.json', 'catalog_sha256'), ('release.json', 'release_sha256'),
                      ('edi/manifest.json', 'edi_manifest_sha256')]:
        if sha((mt/name).read_bytes()) != receipt[key]:
            raise ValueError('MT contribution hash mismatch: '+name)
    catalog = read_json(mt/'catalog.json')
    declared = [v['path'] for c in catalog['cases'] for v in c['variants']]
    if catalog['complete'] is not False or len(catalog['cases']) != 4 or len(declared) != 24 or set(declared) != expected:
        raise ValueError('MT partial catalog matrix mismatch')
    release = read_json(mt/'release.json')
    if release['complete'] is not False or (release['cases'], release['runs'], release['methods']) != (4, 24, 72):
        raise ValueError('MT partial release matrix mismatch')
    for case in catalog['cases']:
        for variant in case['variants']:
            entry = entries[variant['path']]
            if (variant['sha256'], variant['bytes']) != (entry['sha256'], entry['bytes']):
                raise ValueError('MT partial catalog receipt mismatch')
            entry['methods'] = variant['methods']
    manifest = read_json(mt/'edi/manifest.json')
    original = read_json(source/'edi/manifest.json')
    if {k: v for k, v in manifest.items() if k != 'field_screens'} != {
            k: v for k, v in original.items() if k != 'field_screens'}:
        raise ValueError('MT handoff altered inherited EDI evidence')
    field = receipt['field_screen']
    if field['artifact'] != 'edi/clear-lake-cl061-screen.json' or len(manifest['field_screens']) != 1:
        raise ValueError('Unexpected MT field screen')
    screen_raw = (mt/field['artifact']).read_bytes()
    entry = manifest['field_screens'][0]
    if (sha(screen_raw), len(screen_raw)) != (field['sha256'], field['bytes']):
        raise ValueError('Fresh field artifact hash/size mismatch')
    for key, value in dict(artifact_sha256=field['sha256'], artifact_bytes=field['bytes'],
                           parser_source_sha256=sha((ROOT/'data-pipeline/edi.py').read_bytes()),
                           source_sha256=field['source_sha256'], source_bytes=field['source_bytes'],
                           one_d_inversion_eligible=False).items():
        if entry[key] != value:
            raise ValueError('Fresh field manifest mismatch: '+key)
    old_field = original['field_screens'][0]
    if (field['source_sha256'], field['source_bytes']) != (old_field['source_sha256'], old_field['source_bytes']):
        raise ValueError('Measured field source changed')
    screen = json.loads(screen_raw)
    if screen['truth'] is not None or screen['methods'] or screen['inversion_performed'] is not False or (
            screen['one_d_inversion_eligible'] is not False or screen['compatibility']['passes_screen'] is not False):
        raise ValueError('Field negative result changed')
    return dict(receipt_sha256=sha(raw), producer=receipt, entries=entries,
                relevant_source_files=names, unrelated_seismic_source=dict(
                    producer_sha256=receipt['source_sha256']['data-pipeline/seismic.py'],
                    combined_sha256=sha((ROOT/'data-pipeline/seismic.py').read_bytes())),
                inherited_edi_manifest_except_field_unchanged=True)


def validate_run(raw, case, variant, expected, *, seismic=False):
    if sha(raw) != expected['sha256'] or len(raw) != expected['bytes']:
        raise ValueError(f'Input hash/size mismatch: {case["id"]}/{variant}')
    run = json.loads(raw)
    if any(run.get(k) != case[k] for k in ('id', 'family', 'geometry', 'seed')) or run['variant'] != variant:
        raise ValueError('Input case identity mismatch')
    prior = run['provenance']
    version = prior['version']
    if version not in ('0.04.000', '0.04.001'):
        raise ValueError('Unexpected provenance version; no version migration is authorized')
    expected_fingerprint = generator_fingerprint(case['family'], version=version)
    if prior['generator_fingerprint'] != expected_fingerprint:
        raise ValueError('Stale scientific source/settings')
    if set(run['methods']) != set(expected['methods']):
        raise ValueError('Input method matrix mismatch')
    if seismic:
        execution = prior['candidate_execution']
        for key, name in [('solver_sha256', 'seismic.py'), ('geology_sha256', 'geology.py'),
                          ('batch_writer_sha256', 'seismic_batch.py')]:
            if execution[key] != sha((ROOT/'data-pipeline'/name).read_bytes()):
                raise ValueError('Stale seismic execution provenance: '+key)
        if run['export_precision_significant_digits'] != 10 or run['parameters']['iterations'] != 28:
            raise ValueError('Seismic precision or call budget mismatch')
        for method in run['methods'].values():
            if method['solver']['optimizer_calls'] != 112 or method['solver']['lbfgs_max_eval_per_call'] != 25:
                raise ValueError('Seismic optimizer settings mismatch')
    return dict(version=version, generator_fingerprint=expected_fingerprint,
                methods=sorted(run['methods']))


def build_plan(source, seismic, ledger, output, receipts, baseline, mt=None, mt_receipt_sha256=None):
    output, receipts = output_paths(output, receipts, [source, seismic, ledger.parent, *([mt] if mt else [])])
    for path in (source, seismic, ledger):
        if not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('Inputs must be in the specified worktree')
    baseline = subprocess.check_output(['git', 'rev-parse', baseline+'^{commit}'], cwd=ROOT, text=True).strip()
    catalog_raw = (source/'catalog.json').read_bytes()
    if catalog_raw != baseline_bytes(baseline, 'data/derived/v2/catalog.json'):
        raise ValueError('Reuse catalogue differs from the pinned baseline')
    catalog = json.loads(catalog_raw)
    cases = registry()
    by_id = {c['id']: c for c in catalog['cases']}
    if len(by_id) != 20 or len(catalog['cases']) != 20 or set(by_id) != {c['id'] for c in cases}:
        raise ValueError('Original catalogue must have all 20 unique cases')
    frozen = read_json(ledger)
    ledger_entries = {(r['case'], r['variant']): r for r in frozen['completed']}
    if frozen['status'] != 'complete' or len(frozen['completed']) != 24 or len(ledger_entries) != 24:
        raise ValueError('Need the complete unique 24-condition seismic ledger')
    fresh = mt_contribution(mt, mt_receipt_sha256, source) if mt else None
    proofs = {family: family_proof(family, baseline, fresh_mt=fresh is not None) for family in FAMILY_MODULES}
    runs = []
    for case in cases:
        variants = {v['id']: v for v in by_id[case['id']]['variants']}
        if len(by_id[case['id']]['variants']) != 6 or set(variants) != {v[0] for v in VARIANTS}:
            raise ValueError('Original catalogue variant matrix mismatch')
        for variant, _, _ in VARIANTS:
            relative = f'{case["id"]}/{variant}.json'
            original = variants[variant]
            if original['path'] != relative:
                raise ValueError('Unexpected original path')
            old_raw = (source/relative).read_bytes()
            if sha(old_raw) != original['sha256'] or len(old_raw) != original['bytes']:
                raise ValueError('Original input changed: '+relative)
            is_seismic = case['family'] == 'seismic'
            is_mt = case['family'] == 'mt' and fresh is not None
            chosen = seismic/relative if is_seismic else mt/relative if is_mt else source/relative
            raw = chosen.read_bytes() if is_seismic or is_mt else old_raw
            expected = (dict(ledger_entries[(case['id'], variant)], methods=['fwi-l2', 'fwi-multiscale']) if is_seismic
                        else fresh['entries'][relative] if is_mt else original)
            metadata = validate_run(raw, case, variant, expected, seismic=is_seismic)
            if is_mt:
                run = json.loads(raw)
                if metadata['generator_fingerprint'] != expected['generator_fingerprint'] or (
                        metadata['version'] != expected['version'] or run['seed'] != expected['seed']):
                    raise ValueError('Fresh MT producer identity mismatch')
            runs.append(dict(path=relative, source=str(chosen.resolve()), sha256=sha(raw), bytes=len(raw),
                             family=case['family'], selection=('fresh-precision10-seismic' if is_seismic else
                                 'fresh-source-mt' if is_mt else 'unchanged-family-reuse'),
                             original_source=str((source/relative).resolve()), original_sha256=sha(old_raw), **metadata))
    auxiliary = []
    for folder in ('models', 'edi'):
        for path in sorted((source/folder).rglob('*')):
            if path.is_file():
                raw = path.read_bytes()
                if raw != baseline_bytes(baseline, 'data/derived/v2/'+path.relative_to(source).as_posix()):
                    raise ValueError('Auxiliary input differs from pinned baseline: '+str(path))
                relative = path.relative_to(source).as_posix()
                refreshed = fresh is not None and relative in ('edi/manifest.json', 'edi/clear-lake-cl061-screen.json')
                chosen = mt/relative if refreshed else path
                selected = chosen.read_bytes() if refreshed else raw
                auxiliary.append(dict(path=relative, source=str(chosen.resolve()),
                                      sha256=sha(selected), bytes=len(selected),
                                      original_source=str(path.resolve()), original_sha256=sha(raw),
                                      selection='fresh-field-screen-evidence' if refreshed else 'baseline-byte-reuse'))
    if not {'models/training.json', 'models/cnn.json', 'models/autoencoder.json', 'edi/manifest.json'} <= {a['path'] for a in auxiliary}:
        raise ValueError('Missing learned/EDI auxiliary evidence')
    tools = ['data-pipeline/assemble_fwi_candidate.py', 'data-pipeline/catalog.py', 'data-pipeline/rebuild.py',
             'data-pipeline/provenance.py', 'scripts/check_artifacts.py', 'scripts/validate_fwi_exports.py',
             'scripts/validate_mt_replays.py', 'scripts/validate_fwi_mt_candidate.py']
    counts = dict(Counter(r['family'] for r in runs))
    if len(runs) != 120 or sum(len(r['methods']) for r in runs) != 348:
        raise ValueError('Candidate must contain 120 conditions / 348 methods')
    return dict(schema='inverse-earth/fwi-full-assembly-plan/v1', baseline_commit=baseline,
                source_catalog_sha256=sha(catalog_raw), seismic_ledger_sha256=sha(ledger.read_bytes()),
                output=str(output), receipts=str(receipts), family_proofs=proofs, family_conditions=counts,
                mt_contribution=fresh,
                version_semantics=VERSION_SEMANTICS, runs=runs, auxiliary=auxiliary,
                tools={p: sha((ROOT/p).read_bytes()) for p in tools},
                excluded_old_receipts=['validation.json', 'fwi-replay.json'],
                inputs=dict(source=str(source.resolve()), seismic=str(seismic.resolve()), ledger=str(ledger.resolve()),
                            mt=str(mt.resolve()) if mt else None, mt_receipt_sha256=mt_receipt_sha256))


def assemble(plan_path):
    plan = read_json(plan_path)
    if plan_path.resolve() != (Path(plan['receipts'])/'plan.json').resolve():
        raise ValueError('Plan path differs from frozen receipts location')
    inputs = plan['inputs']
    current = build_plan(*(Path(inputs[k]) for k in ('source', 'seismic', 'ledger')),
                         Path(plan['output']), Path(plan['receipts']), plan['baseline_commit'],
                         Path(inputs['mt']) if inputs.get('mt') else None, inputs.get('mt_receipt_sha256'))
    if current != plan:
        raise ValueError('Frozen assembly plan changed; no files copied')
    output = Path(plan['output'])
    output.mkdir()
    for item in plan['runs']+plan['auxiliary']:
        destination = output/item['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item['source'], destination)
        if sha(destination.read_bytes()) != item['sha256']:
            raise ValueError('Destination copy mismatch: '+item['path'])
    from catalog import assemble as assemble_catalog
    assemble_catalog(output)
    spec = importlib.util.spec_from_file_location('assembly_artifact_gate', ROOT/'scripts/check_artifacts.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    gate.ROOT = output
    result = gate.validate()
    for item in plan['runs']+plan['auxiliary']:
        if sha(Path(item['source']).read_bytes()) != item['sha256']:
            raise ValueError('Source changed during assembly: '+item['path'])
    for item in plan['runs']+plan['auxiliary']:
        if sha(Path(item['original_source']).read_bytes()) != item['original_sha256']:
            raise ValueError('Original canonical input changed during assembly: '+item['path'])
    if sha((Path(inputs['source'])/'catalog.json').read_bytes()) != plan['source_catalog_sha256']:
        raise ValueError('Original catalogue changed during assembly')
    if plan['mt_contribution'] and sha((Path(inputs['mt'])/'mt-replay.json').read_bytes()) != inputs['mt_receipt_sha256']:
        raise ValueError('MT producer receipt changed during assembly')
    catalog_raw = (output/'catalog.json').read_bytes()
    candidate = dict(schema='inverse-earth/fwi-full-candidate/v1', **VERSION_SEMANTICS,
                     assembly_plan_sha256=sha(plan_path.read_bytes()),
                     catalog_sha256=sha(catalog_raw), release_sha256=sha((output/'release.json').read_bytes()),
                     artifact_gate=result, acceptance='artifact gate passed; physical replay and test gates still required')
    write_json(output/'candidate.json', candidate)
    differences = [dict(path=r['path'], original_sha256=r['original_sha256'], candidate_sha256=r['sha256'],
                        changed=r['original_sha256'] != r['sha256'], selection=r['selection']) for r in plan['runs']]
    receipt = dict(schema='inverse-earth/fwi-full-assembly-receipt/v1', candidate=candidate,
                   source_inputs_unchanged=True, copied_conditions=120,
                   source_reused_conditions=72 if plan['mt_contribution'] else 96,
                   fresh_mt_conditions=24 if plan['mt_contribution'] else 0,
                   fresh_seismic_conditions=24, copied_auxiliary_files=len(plan['auxiliary']),
                   source_diff=differences, catalog_assembled_from_current_sources=True)
    write_json(Path(plan['receipts'])/'assembly.json', receipt)
    print(json.dumps(dict(artifact_gate=result, catalog_sha256=candidate['catalog_sha256'],
                          receipt=str(Path(plan['receipts'])/'assembly.json'))), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['plan', 'assemble'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--receipts', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=ROOT/'data/derived/v2')
    parser.add_argument('--seismic', type=Path, default=EXPERIMENTS/'fwi-candidate-precision10')
    parser.add_argument('--seismic-ledger', type=Path, default=EXPERIMENTS/'fwi-batch-receipts-precision10/ledger.json')
    parser.add_argument('--baseline-commit', default=BASELINE)
    parser.add_argument('--mt', type=Path, help='Explicit read-only fresh MT contribution, never canonical fallback')
    parser.add_argument('--mt-receipt-sha256', help='Independently supplied producer receipt pin')
    args = parser.parse_args()
    plan_path = args.receipts.resolve()/'plan.json'
    if args.mode == 'plan':
        if plan_path.exists():
            parser.error('Frozen plan already exists; use distinct receipts instead of overwriting')
        if bool(args.mt) != bool(args.mt_receipt_sha256):
            parser.error('Fresh MT directory and independent receipt pin must be supplied together')
        plan = build_plan(args.source, args.seismic, args.seismic_ledger, args.output, args.receipts,
                          args.baseline_commit, args.mt, args.mt_receipt_sha256)
        write_json(plan_path, plan)
        print(json.dumps(dict(conditions=120, methods=348, family_conditions=plan['family_conditions'], plan=str(plan_path))))
    else:
        plan = read_json(plan_path)
        if args.output.resolve() != Path(plan['output']):
            parser.error('Output differs from frozen plan')
        assemble(plan_path)


if __name__ == '__main__':
    main()
