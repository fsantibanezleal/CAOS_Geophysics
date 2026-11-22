"""Exact copied successor recognition without granting unbound method custody."""

from contextlib import closing
import sqlite3

from alembic import command
import pytest

from app.physical_classifier import classify_snapshot
from app.physical_schema import DDL, EXTENSIONS, schema_tables
from tests.ops.physical_union_fixture import capsule


class EmptyFiles:
    """Positive empty namespace control only, no POSIX/runtime proof."""
    def census(self, expected, *, empty_directories=()):
        assert expected == {}
        return {}

    def names(self, key, *, limit):
        raise FileNotFoundError(key)


@pytest.fixture
def empty_union(tmp_path, monkeypatch):
    config, path = capsule(tmp_path/'union')
    monkeypatch.setenv('GEOPHYSICS_DB_PATH', str(path))
    monkeypatch.setenv('GEOPHYSICS_CANDIDATE_ROOT', str(path.parent))
    return config, path


@pytest.mark.parametrize('revision', tuple(DDL))
def test_exact_allocated_5_6_changed7_empty_full_snapshot_is_ready_and_read_only(empty_union, revision):
    config, path = empty_union
    command.upgrade(config, revision)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('BEGIN IMMEDIATE')
        before = connection.total_changes
        head, names = schema_tables(connection)
        assert head == revision and EXTENSIONS[head] <= names
        result = classify_snapshot(connection, EmptyFiles(), approved_manifests={},
            approved_installations={}, native_metadata={})
        assert result.classification == 'coherent_committed', result.reason
        assert result.inventory_sha256 and not result.runtime and not result.account_charges
        assert connection.in_transaction and connection.total_changes == before
        connection.rollback()


@pytest.mark.parametrize('damage', ['head', 'column', 'table', 'index', 'trigger'])
def test_union_unknown_shape_is_not_a_revision_only_alias(empty_union, damage):
    config, path = empty_union
    command.upgrade(config, '0007_magnetic_line_artifacts')
    with closing(sqlite3.connect(path)) as connection:
        if damage == 'head': connection.execute("UPDATE alembic_version SET version_num='0008_unreviewed'")
        if damage == 'column': connection.execute('ALTER TABLE user ADD COLUMN unreviewed TEXT')
        if damage == 'table': connection.execute('CREATE TABLE unreviewed(id INTEGER PRIMARY KEY)')
        if damage == 'index': connection.execute('CREATE INDEX unreviewed ON projects(name)')
        if damage == 'trigger': connection.execute('CREATE TRIGGER unreviewed AFTER UPDATE ON projects BEGIN SELECT 1; END')
        connection.commit()
        connection.execute('BEGIN')
        with pytest.raises(ValueError, match='physical_classifier_schema'):
            schema_tables(connection)
        result = classify_snapshot(connection, EmptyFiles(), approved_manifests={},
            approved_installations={}, native_metadata={})
        assert result.classification == 'inconsistent' and not result.inventory_sha256
        connection.rollback()
