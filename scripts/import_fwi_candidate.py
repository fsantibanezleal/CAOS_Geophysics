"""Plan/stage a byte-preserving 0.04.002 container; import requires separate operator approval."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'data-pipeline'))
from artifact_versions import CONTAINER_VERSION, REPLAY_SOURCE_FILES, SCIENTIFIC_FILES, digest, header_bytes  # noqa: E402

CANONICAL = REPO/'data/derived/v2'
EXPERIMENTS = REPO/'data/experiments'
BACKUPS = REPO/'data/raw/canonical-backups'
TOOLS = ('scripts/import_fwi_candidate.py', 'scripts/check_artifacts.py', 'data-pipeline/artifact_versions.py')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False)+'\n').encode()


def write_new(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def safe_path(path):
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError('Symlink/junction path forbidden: '+str(part))
    return path.resolve()


def safe_tree(root):
    safe_path(root)
    for path in root.rglob('*'):
        safe_path(path)


def ignored_child(path, parent):
    resolved = safe_path(path)
    if resolved == parent.resolve() or not resolved.is_relative_to(parent.resolve()):
        raise ValueError('Expected distinct child of '+str(parent))
    if subprocess.run(['git', 'check-ignore', '--quiet', str(resolved)], cwd=REPO).returncode:
        raise ValueError('Private/staging output must be ignored')
    return resolved


def exact_target(target):
    if safe_path(target) != CANONICAL.resolve():
        raise ValueError('Only this checkout exact data/derived/v2 target is permitted')


def snapshot(root):
    safe_tree(root)
    return [dict(path=p.relative_to(root).as_posix(), sha256=digest(p), bytes=p.stat().st_size)
            for p in sorted(root.rglob('*')) if p.is_file()]


def tree_sha(entries):
    value = hashlib.sha256()
    for entry in sorted(entries, key=lambda e: Path(e['path'])):
        value.update(entry['path'].encode()+b'\0')
        value.update(bytes.fromhex(entry['sha256']))
    return value.hexdigest()


def clean_canonical(expected_digest):
    exact_target(CANONICAL)
    relative = CANONICAL.relative_to(REPO).as_posix()
    dirty = subprocess.check_output(['git', 'status', '--porcelain=v1', '--untracked-files=all', '--', relative],
                                    cwd=REPO, text=True)
    if dirty.strip():
        raise ValueError('Dirty canonical data; preserve and review before import')
    entries = snapshot(CANONICAL)
    tracked = subprocess.check_output(['git', 'ls-files', '--', relative], cwd=REPO, text=True).splitlines()
    expected_names = {p[len(relative)+1:] for p in tracked}
    if len(entries) != 137 or {e['path'] for e in entries} != expected_names or tree_sha(entries) != expected_digest:
        raise ValueError('Changed canonical inventory/digest; expected frozen 137-file baseline')
    return entries


def artifact_gate(data):
    spec = importlib.util.spec_from_file_location('import_artifact_guard', REPO/'scripts/check_artifacts.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    gate.ROOT = data
    result = gate.validate()
    if result != dict(cases=20, runs=120, method_results=348):
        raise ValueError('Full 120/348 artifact gate required')
    return result


def independent_acceptance(candidate, fwi_path, mt_path, fwi_pin, mt_pin):
    for path, pin in ((fwi_path, fwi_pin), (mt_path, mt_pin)):
        safe_path(path)
        if not pin or digest(path) != pin:
            raise ValueError('Independent receipt hash mismatch')
    catalog, release, mt, fwi = read(candidate/'catalog.json'), read(candidate/'release.json'), read(mt_path), read(fwi_path)
    if mt['schema'] != 'inverse-earth/combined-candidate-mt-replay/v1' or fwi['schema'] != 'inverse-earth/fwi-replay/v1':
        raise ValueError('Expected independent scientific replay receipt schemas')
    if catalog['version'] != '0.04.001' or release['version'] != '0.04.001':
        raise ValueError('Original accepted 0.04.001 compatibility container required')
    if (mt['status'], mt['conditions'], mt['method_results'], mt['states_replayed'], mt['bootstrap_refits'],
        mt['canonical_unchanged']) != ('PASS', 120, 348, 4038, 3072, True):
        raise ValueError('Independent full MT acceptance required')
    if mt['artifact_gate'] != dict(cases=20, runs=120, method_results=348):
        raise ValueError('Independent full artifact matrix required')
    if (mt['catalog_sha256'], mt['release_sha256']) != (digest(candidate/'catalog.json'), digest(candidate/'release.json')):
        raise ValueError('Independent acceptance refers to another candidate')
    if set(mt['source_sha256']) != REPLAY_SOURCE_FILES:
        raise ValueError('Missing/unexpected independent replay source bindings')
    epochs = {}
    for name, recorded in mt['source_sha256'].items():
        path = safe_path(REPO/name)
        if not path.is_relative_to(REPO.resolve()):
            raise ValueError('Unsafe independent source path')
        current = digest(path)
        if current == recorded:
            continue
        if name != 'scripts/check_artifacts.py':
            raise ValueError('Source changed since independent review: '+name)
        original = subprocess.check_output(['git', 'show', mt['source_revision']+':'+name], cwd=REPO)
        if hashlib.sha256(original).hexdigest() != recorded:
            raise ValueError('Historical guard epoch is not bound to its actual executed revision')
        epochs[name] = dict(independent_review_sha256=recorded, migration_guard_sha256=current,
                           reason='Explicit reviewed 0.04.002 container reuse/migration contract; '
                                  'original physics/fingerprint checks remain mandatory. No old tool hash substitution.')
    for name in ('data-pipeline/seismic.py', 'data-pipeline/electromagnetics.py',
                 'data-pipeline/edi.py', 'data-pipeline/geology.py', 'data-pipeline/provenance.py'):
        if name not in mt['source_sha256']:
            raise ValueError('Missing independent scientific source binding')
    variants = {v['path']: v for c in catalog['cases'] for v in c['variants']}
    inventory = mt['artifacts']
    if len(inventory) != 120 or len({e['path'] for e in inventory}) != 120 or {e['path'] for e in inventory} != set(variants):
        raise ValueError('Independent complete unique candidate inventory required')
    for entry in inventory:
        declared = variants[entry['path']]
        path = candidate/entry['path']
        if (digest(path), path.stat().st_size) != (entry['sha256'], entry['bytes']) or (
                entry['sha256'], entry['bytes']) != (declared['sha256'], declared['bytes']):
            raise ValueError('Accepted candidate byte drift')
    seismic = {c['id']: c for c in catalog['cases'] if c['family'] == 'seismic'}
    expected = {(c['id'], v['id'], method) for c in seismic.values() for v in c['variants'] for method in v['methods']}
    records = fwi['records']
    keys = [(r['case'], r['variant'], r['method']) for r in records]
    if (fwi['conditions'], fwi['method_results'], len(keys), len(set(keys))) != (24, 48, 48, 48) or set(keys) != expected:
        raise ValueError('Independent complete unique FWI coverage required')
    for record in records:
        variant = next(v for v in seismic[record['case']]['variants'] if v['id'] == record['variant'])
        if record['status'] != variant['methods'][record['method']]['evaluation']['status']:
            raise ValueError('Independent FWI negative verdict drift')
    return dict(source_revision=mt['source_revision'], fwi_sha256=fwi_pin, mt_sha256=mt_pin,
                catalog_sha256=mt['catalog_sha256'], release_sha256=mt['release_sha256'],
                recorded_source_sha256=mt['source_sha256'], guard_epoch_differences=epochs,
                introduced_policy_sha256=digest(REPO/'data-pipeline/artifact_versions.py'))


def make_plan(candidate, fwi, mt, fwi_pin, mt_pin, canonical_digest, target, stage, backup, receipts):
    exact_target(target)
    candidate = ignored_child(candidate, EXPERIMENTS)
    stage, receipts = (ignored_child(p, EXPERIMENTS) for p in (stage, receipts))
    backup = ignored_child(backup, BACKUPS)
    paths = (candidate, stage, backup, receipts)
    if any(a.is_relative_to(b) or b.is_relative_to(a) for i, a in enumerate(paths) for b in paths[i+1:]):
        raise ValueError('Candidate, stage, backup and receipts must not overlap')
    if backup.exists():
        raise ValueError('Preserve existing private backup; use a fresh plan')
    for path in (fwi, mt):
        ignored_child(path, EXPERIMENTS)
        if path.resolve().is_relative_to(stage) or path.resolve().is_relative_to(backup):
            raise ValueError('Replay input overlaps publication output')
    canonical = clean_canonical(canonical_digest)
    safe_tree(candidate)
    acceptance = independent_acceptance(candidate, fwi, mt, fwi_pin, mt_pin)
    artifact_gate(candidate)
    catalog = read(candidate/'catalog.json')
    names = {v['path'] for c in catalog['cases'] for v in c['variants']}
    names |= {p.relative_to(candidate).as_posix() for folder in ('models', 'edi')
              for p in (candidate/folder).rglob('*') if p.is_file()}
    if len(names) != 133:
        raise ValueError('Exactly 120 conditions and 13 auxiliary files required')
    preserved = [dict(path=name, sha256=digest(candidate/name), bytes=(candidate/name).stat().st_size)
                 for name in sorted(names)]
    return dict(schema='inverse-earth/canonical-container-import-plan/v1', target=str(CANONICAL.resolve()),
                stage=str(stage), backup=str(backup), receipts=str(receipts), canonical=canonical,
                canonical_tree_sha256=canonical_digest, acceptance=acceptance, preserved_files=preserved,
                version_semantics=dict(container=CONTAINER_VERSION, reused_producer_versions=['0.04.000', '0.04.001'],
                                       producer_and_fixture_bytes_unchanged=True, live_deployment=False),
                scientific_source_sha256={name: digest(REPO/name) for name in SCIENTIFIC_FILES},
                tools={name: digest(REPO/name) for name in TOOLS},
                inputs=dict(candidate=str(candidate), fwi=str(fwi.resolve()), mt=str(mt.resolve()),
                            fwi_pin=fwi_pin, mt_pin=mt_pin))


def verify_plan(plan_path):
    plan = read(plan_path)
    if plan_path.resolve() != (Path(plan['receipts'])/'plan.json').resolve():
        raise ValueError('Frozen plan location mismatch')
    args = plan['inputs']
    current = make_plan(Path(args['candidate']), Path(args['fwi']), Path(args['mt']), args['fwi_pin'], args['mt_pin'],
                        plan['canonical_tree_sha256'], Path(plan['target']), Path(plan['stage']),
                        Path(plan['backup']), Path(plan['receipts']))
    if current != plan:
        raise ValueError('Frozen plan/input/tool drift; no canonical writes')
    return plan


def stage_container(plan_path):
    plan = verify_plan(plan_path)
    stage, candidate = Path(plan['stage']), Path(plan['inputs']['candidate'])
    if stage.exists():
        raise ValueError('Preserve existing staging directory')
    stage.mkdir(parents=True)
    for entry in plan['preserved_files']:
        target = stage/entry['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(candidate/entry['path'], target)
    for name, source in (('fwi-replay.json', plan['inputs']['fwi']), ('mt-replay.json', plan['inputs']['mt'])):
        shutil.copyfile(source, stage/name)
    raw = header_bytes((candidate/'catalog.json').read_bytes(), '0.04.001', CONTAINER_VERSION)
    write_new(stage/'catalog.json', raw)
    migration = dict(schema='inverse-earth/byte-preserving-container-migration/v1', from_version='0.04.001',
                     to_version=CONTAINER_VERSION, reused_producer_versions=['0.04.000', '0.04.001'],
                     plan_sha256=digest(plan_path), source_catalog_sha256=plan['acceptance']['catalog_sha256'],
                     source_release_sha256=plan['acceptance']['release_sha256'],
                     catalog_sha256=hashlib.sha256(raw).hexdigest(), preserved_files=plan['preserved_files'],
                     scientific_source_sha256=plan['scientific_source_sha256'],
                     independent_review_source_sha256=plan['acceptance']['recorded_source_sha256'],
                     guard_epoch_differences=plan['acceptance']['guard_epoch_differences'],
                     gate_sha256={name: plan['tools'][name] for name in TOOLS if name != 'scripts/import_fwi_candidate.py'},
                     independent_receipts={'fwi-replay.json': plan['inputs']['fwi_pin'], 'mt-replay.json': plan['inputs']['mt_pin']})
    write_new(stage/'migration.json', encoded(migration))
    validation = dict(schema='inverse-earth/container-validation/v1', container_version=CONTAINER_VERSION,
                      plan_sha256=digest(plan_path), scientific_review_revision=plan['acceptance']['source_revision'],
                      source_artifact_matrix=dict(cases=20, runs=120, method_results=348),
                      independent_receipts=migration['independent_receipts'],
                      scope='Original independent numerical acceptance of preserved scientific bytes; '
                            'container acceptance requires the current guard and frozen stage receipt. '
                            'No rebake, new empirical truth, host admission or product-convergence claim.')
    write_new(stage/'validation.json', encoded(validation))
    release = read(candidate/'release.json')
    release['version'] = CONTAINER_VERSION
    release['container_migration_sha256'] = digest(stage/'migration.json')
    release['container_validation_sha256'] = digest(stage/'validation.json')
    write_new(stage/'release.json', encoded(release))
    result = artifact_gate(stage)
    verify_plan(plan_path)
    receipt = dict(schema='inverse-earth/staged-container/v1', stage=str(stage), artifact_gate=result,
                   plan_sha256=digest(plan_path), inventory=snapshot(stage), producer_and_fixture_bytes_unchanged=True,
                   canonical_import_executed=False)
    if len(receipt['inventory']) != 139:
        raise ValueError('Unexpected staged container file count')
    write_new(Path(plan['receipts'])/'stage.json', encoded(receipt))
    return receipt


def publish(stage, target, backup, expected_original, expected_published, failed_path, gate):
    """Exact directory renames; originals retained, no recursive deletion or overwrite."""
    if backup.exists() or failed_path.exists():
        raise ValueError('Fresh private backup/recovery paths required')
    if snapshot(target) != expected_original or snapshot(stage) != expected_published:
        raise ValueError('Publication input drift')
    backup.parent.mkdir(parents=True, exist_ok=True)
    published = False
    os.replace(target, backup)
    try:
        if snapshot(backup) != expected_original:
            raise ValueError('Backup differs from frozen original')
        os.replace(stage, target)
        published = True
        if snapshot(target) != expected_published:
            raise ValueError('Published data differ from validated stage')
        gate(target)
    except BaseException:
        if published:
            os.replace(target, failed_path)
        if not target.exists():
            shutil.copytree(backup, target)
        # If an external writer created a target in the rename gap, do not overwrite it.
        raise
    return dict(backup_tree_sha256=tree_sha(snapshot(backup)), published_tree_sha256=tree_sha(snapshot(target)),
                original_backup_retained=True)


def import_container(plan_path, approval):
    if approval != 'IMPORT-'+digest(plan_path):
        raise ValueError('Separate exact operator approval token required')
    plan = verify_plan(plan_path)
    stage = Path(plan['stage'])
    receipt = read(Path(plan['receipts'])/'stage.json')
    if receipt['plan_sha256'] != digest(plan_path) or receipt['inventory'] != snapshot(stage):
        raise ValueError('Staged receipt/input drift')
    artifact_gate(stage)
    verify_plan(plan_path)
    write_new(Path(plan['receipts'])/'import-started.json', encoded(dict(plan_sha256=digest(plan_path))))
    try:
        result = publish(stage, Path(plan['target']), Path(plan['backup']), plan['canonical'], receipt['inventory'],
                         Path(plan['receipts'])/'failed-publish', artifact_gate)
    except BaseException as error:
        recovery = dict(error_type=type(error).__name__, error=str(error), plan_sha256=digest(plan_path),
                        backup_exists=Path(plan['backup']).exists(), canonical_exists=Path(plan['target']).exists())
        for label, path in (('backup', plan['backup']), ('canonical', plan['target'])):
            try:
                recovery[label+'_matches_original'] = snapshot(Path(path)) == plan['canonical']
            except (OSError, ValueError):
                recovery[label+'_matches_original'] = False
        write_new(Path(plan['receipts'])/'import-error.json', encoded(recovery))
        raise
    write_new(Path(plan['receipts'])/'import.json', encoded(dict(plan_sha256=digest(plan_path), **result)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['plan', 'stage', 'import'])
    parser.add_argument('--receipts', type=Path, required=True)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--independent-fwi', type=Path)
    parser.add_argument('--independent-mt', type=Path)
    parser.add_argument('--fwi-sha256')
    parser.add_argument('--mt-sha256')
    parser.add_argument('--expected-canonical-sha256')
    parser.add_argument('--target', type=Path, default=CANONICAL)
    parser.add_argument('--stage', type=Path)
    parser.add_argument('--backup', type=Path)
    parser.add_argument('--approval', help='Only after separate owner review: IMPORT-<frozen plan SHA256>')
    args = parser.parse_args()
    plan_path = args.receipts.resolve()/'plan.json'
    if args.mode == 'plan':
        if any(getattr(args, name) is None for name in ('candidate', 'independent_fwi', 'independent_mt', 'fwi_sha256',
                'mt_sha256', 'expected_canonical_sha256', 'stage', 'backup')):
            parser.error('Plan requires candidate, independent receipts/pins, canonical digest, fresh stage and backup')
        if plan_path.exists() or args.stage.exists():
            parser.error('Preserve existing frozen plan/stage; choose fresh paths')
        plan = make_plan(args.candidate, args.independent_fwi, args.independent_mt, args.fwi_sha256, args.mt_sha256,
                         args.expected_canonical_sha256, args.target, args.stage, args.backup, args.receipts)
        write_new(plan_path, encoded(plan))
        result = dict(plan_sha256=digest(plan_path), canonical_import_executed=False)
    elif args.mode == 'stage':
        result = stage_container(plan_path)
        result = {key: result[key] for key in ('artifact_gate', 'producer_and_fixture_bytes_unchanged', 'canonical_import_executed')}
    else:
        result = import_container(plan_path, args.approval)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
