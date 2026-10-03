"""Explicit release-container reuse, never a producer-provenance rewrite. Stdlib only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[1]
CONTAINER_VERSION = '0.04.002'
RUN_VERSIONS = {
    '0.04.000': frozenset({'0.04.000'}),
    '0.04.001': frozenset({'0.04.000', '0.04.001'}),
    CONTAINER_VERSION: frozenset({'0.04.000', '0.04.001', CONTAINER_VERSION}),
}
SCIENTIFIC_FILES = tuple('data-pipeline/'+n for n in (
    'geology.py', 'potential.py', 'spatial_inverse.py', 'evaluation.py', 'joint.py',
    'petrophysics.py', 'learning.py', 'electromagnetics.py', 'edi.py', 'seismic.py',
    'seismic_batch.py', 'provenance.py'))
REPLAY_SOURCE_FILES = frozenset((
    'data-pipeline/electromagnetics.py', 'data-pipeline/edi.py', 'data-pipeline/geology.py',
    'data-pipeline/provenance.py', 'data-pipeline/rebuild.py', 'data-pipeline/seismic.py',
    'scripts/build_field_screen.py', 'scripts/validate_mt_replays.py', 'data-pipeline/seismic_batch.py',
    'data-pipeline/assemble_fwi_candidate.py', 'data-pipeline/catalog.py', 'scripts/check_artifacts.py',
    'scripts/validate_fwi_exports.py', 'scripts/validate_fwi_mt_candidate.py'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def allowed_run_version(container, version):
    assert container in RUN_VERSIONS, 'Unsupported container version'
    assert version in RUN_VERSIONS[container], 'Unexpected run version'


def header_bytes(raw, previous, following):
    """Preserve every catalog byte except its unique version string."""
    before = json.loads(raw)
    assert before['version'] == previous
    matches = list(re.finditer(rb'("version"\s*:\s*")([^"\r\n]+)(")', raw))
    assert len(matches) == 1, 'Ambiguous container version fields'
    match = matches[0]
    result = raw[:match.start(2)] + following.encode('ascii') + raw[match.end(2):]
    after = json.loads(result)
    before['version'] = following
    assert after == before, 'Container migration changed scientific catalog fields'
    return result


def validate_migration(root, catalog, release):
    if catalog['version'] != CONTAINER_VERSION:
        return
    path = root/'migration.json'
    assert digest(path) == release['container_migration_sha256'], 'Migration manifest hash mismatch'
    migration = json.loads(path.read_text(encoding='utf-8'))
    assert migration['schema'] == 'inverse-earth/byte-preserving-container-migration/v1'
    assert (migration['from_version'], migration['to_version']) == ('0.04.001', CONTAINER_VERSION)
    assert migration['reused_producer_versions'] == ['0.04.000', '0.04.001']
    raw = (root/'catalog.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == migration['catalog_sha256']
    assert hashlib.sha256(header_bytes(raw, CONTAINER_VERSION, '0.04.001')).hexdigest() == migration['source_catalog_sha256']
    entries = migration['preserved_files']
    actual = {v['path'] for c in catalog['cases'] for v in c['variants']}
    actual |= {p.relative_to(root).as_posix() for folder in ('models', 'edi')
               for p in (root/folder).rglob('*') if p.is_file()}
    assert len(entries) == 133 and len({e['path'] for e in entries}) == 133
    assert {e['path'] for e in entries} == actual, 'Preserved artifact inventory mismatch'
    for entry in entries:
        target = (root/entry['path']).resolve()
        assert target.is_relative_to(root.resolve()), 'Unsafe migration artifact path'
        assert target.stat().st_size == entry['bytes'] and digest(target) == entry['sha256'], 'Producer/fixture byte drift'
    for name, sha256 in migration['scientific_source_sha256'].items():
        assert name in SCIENTIFIC_FILES and digest(REPO/name) == sha256, 'Stale migration scientific source'
    assert set(migration['scientific_source_sha256']) == set(SCIENTIFIC_FILES)
    for name in ('scripts/check_artifacts.py', 'data-pipeline/artifact_versions.py'):
        assert digest(REPO/name) == migration['gate_sha256'][name], 'Migration gate bytes changed'
    for name, pin in migration['independent_receipts'].items():
        assert name in ('fwi-replay.json', 'mt-replay.json') and digest(root/name) == pin
    assert set(migration['independent_receipts']) == {'fwi-replay.json', 'mt-replay.json'}
    mt = json.loads((root/'mt-replay.json').read_text(encoding='utf-8'))
    recorded = mt['source_sha256']
    assert set(recorded) == REPLAY_SOURCE_FILES, 'Missing/unexpected independent source bindings'
    assert migration['independent_review_source_sha256'] == recorded, 'Historical source hashes were relabeled'
    differences = {}
    for name, historical in recorded.items():
        current = digest(REPO/name)
        if current != historical:
            assert name == 'scripts/check_artifacts.py', 'Unreviewed replay/producer source change'
            differences[name] = (historical, current)
    epochs = migration['guard_epoch_differences']
    assert set(epochs) == set(differences), 'Guard epoch differences missing or forged'
    for name, (historical, current) in differences.items():
        assert (epochs[name]['independent_review_sha256'], epochs[name]['migration_guard_sha256']) == (historical, current)
    assert mt['status'] == 'PASS' and mt['catalog_sha256'] == migration['source_catalog_sha256']
    assert mt['release_sha256'] == migration['source_release_sha256']
    assert (mt['conditions'], mt['method_results'], mt['states_replayed'], mt['bootstrap_refits']) == (120, 348, 4038, 3072)
    fwi = json.loads((root/'fwi-replay.json').read_text(encoding='utf-8'))
    assert (fwi['conditions'], fwi['method_results'], len(fwi['records'])) == (24, 48, 48)
    assert digest(root/'validation.json') == release['container_validation_sha256'], 'Validation descriptor hash mismatch'
    validation = json.loads((root/'validation.json').read_text(encoding='utf-8'))
    assert validation['schema'] == 'inverse-earth/container-validation/v1'
    assert validation['container_version'] == CONTAINER_VERSION and validation['plan_sha256'] == migration['plan_sha256']
    assert validation['source_artifact_matrix'] == mt['artifact_gate'] == dict(cases=20, runs=120, method_results=348)
    assert validation['independent_receipts'] == migration['independent_receipts']
