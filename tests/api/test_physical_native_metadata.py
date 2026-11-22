"""Operator DB filename binding and exact empty legacy namespace controls."""

from contextlib import closing
from dataclasses import replace
import json
import sqlite3

import pytest

from app.database import make_engine
from app.physical_classifier import classify_snapshot
from tests.api.test_physical_assembly import bound_fixture
from tests.api.test_physical_classifier import CensusFiles
from tests.api.test_physical_deleted_inventory import case
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


@pytest.mark.parametrize('name', ['api.sqlite3', 'geophysics.sqlite3'])
def test_engine_selected_database_must_match_exact_operator_metadata(root_case, monkeypatch, name):
    settings, physical = bound_fixture(root_case, monkeypatch)
    selected = replace(settings, db_path=settings.data_dir/name)
    registry = json.loads(physical.participant.registration)
    rule = dict(cap=512*1048576, bytes=None, sha256=None, required=True)
    registry['native_metadata'] = {name: rule, name+'-wal': dict(rule, required=False),
                                   name+'-shm': dict(rule, required=False)}
    physical.participant.registration = json.dumps(registry).encode()
    physical.bind_engine(selected, make_engine(selected))
    assert not selected.database_path.exists()
    other = 'api.sqlite3' if name == 'geophysics.sqlite3' else 'geophysics.sqlite3'
    registry['native_metadata'][other] = rule
    physical.participant.registration = json.dumps(registry).encode()
    with pytest.raises(ValueError, match='physical_assembly_database_metadata_binding'):
        physical.bind_engine(selected, make_engine(selected))
    assert not selected.database_path.exists()


@pytest.mark.parametrize('damage', ['missing', 'unregistered', 'nested', 'outside'])
def test_native_metadata_does_not_whitelist_arbitrary_or_foreign_database(root_case, monkeypatch, damage):
    settings, physical = bound_fixture(root_case, monkeypatch)
    path = settings.data_dir/'api.sqlite3'
    registry = json.loads(physical.participant.registration)
    if damage == 'unregistered': path = settings.data_dir/'arbitrary.db'
    if damage == 'nested': path = settings.data_dir/'nested/api.sqlite3'
    if damage == 'outside': path = settings.database_path
    if damage != 'missing':
        registry['native_metadata'] = {'api.sqlite3': dict(cap=1048576, bytes=None, sha256=None, required=True)}
    physical.participant.registration = json.dumps(registry).encode()
    selected = replace(settings, db_path=path)
    with pytest.raises(ValueError, match='physical_assembly_database_metadata_binding'):
        physical.bind_engine(selected, make_engine(selected))


@pytest.mark.parametrize('namespace', ['.staging', '.exports'])
def test_only_empty_known_original_namespace_is_recognized_not_its_unknown_members(root_case, namespace):
    case(root_case)
    path, files, *_ = root_case
    directory = files.root/namespace
    directory.mkdir()
    with closing(sqlite3.connect(path)) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('BEGIN')
        result = classify_snapshot(connection, CensusFiles(files), approved_manifests={},
            approved_installations={}, native_metadata={})
        assert result.classification == 'coherent_committed', result.reason
        sentinel = directory/'must-stay-unknown'
        sentinel.write_bytes(b'authentic unknown retained')
        result = classify_snapshot(connection, CensusFiles(files), approved_manifests={},
            approved_installations={}, native_metadata={})
        assert result.classification == 'inconsistent' and not result.inventory_sha256
        assert sentinel.read_bytes() == b'authentic unknown retained'
        connection.rollback()
