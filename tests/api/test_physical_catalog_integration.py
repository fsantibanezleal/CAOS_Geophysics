"""Real root files/SQLite against the merged catalog; no science/host claim."""

from contextlib import closing
import json
import sqlite3
from uuid import uuid4

import pytest

from app.physical_catalog import catalog_response, lineage_transaction, list_datasets_transaction
from app.physical_contract import byte_sha
from app.physical_read import dataset_bytes_response, read_dataset_bytes_transaction, read_dataset_transaction
from app.physical_roots import prepare_root, publish_root
from tests.api.test_physical_forest import connect
from tests.api.test_physical_roots import install_fixture, publish_values, root_case as root_case
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


@pytest.fixture
def published_root(root_case):
    path, files, values, body, original = root_case
    with closing(connect(path)) as connection:
        prepare_root(connection, files, **values)
        install_fixture(files, values, body)
        publish_root(connection, files, **publish_values(values))
    return path, files, values, body, original


def caller(connection):
    assert connection.execute('PRAGMA journal_mode=WAL').fetchone() == ('wal',)
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA synchronous=FULL')
    connection.execute('PRAGMA trusted_schema=OFF')
    connection.execute('BEGIN IMMEDIATE')
    connection.execute("UPDATE projects SET name='Pending caller metadata'")


def context(values):
    return dict(owner_id=values['owner_id'], project_id=values['project_id'], approved_manifests={})


def test_original_dataset_body_and_raw_numeric_spelling_are_not_reserialized(published_root):
    path, files, values, body, original = published_root
    with closing(sqlite3.connect(path)) as connection:
        caller(connection)
        arguments = dict(context(values), dataset_id=values['root_dataset_id'])
        saved = read_dataset_bytes_transaction(connection, files, **arguments)
        assert type(saved) is bytes and saved == body
        assert dataset_bytes_response(saved).body == body
        assert read_dataset_transaction(connection, files, **arguments) == json.loads(body)
        assert connection.in_transaction
        assert connection.execute('SELECT name FROM projects').fetchone() == ('Pending caller metadata',)
        connection.rollback()
    # A response projection alone is not scientific validation; preserve the
    # authored JSON dialect rather than reconstructing it through JSON numbers.
    authored = b' { "number": 1.00, "zero": -0.0, "label": "\\u0061" }\n'
    response = dataset_bytes_response(authored)
    assert response.body == authored and response.headers['cache-control'] == 'no-store'
    assert byte_sha(response.body) == byte_sha(authored)
    assert original.startswith(b' \n')


def test_current_root_catalog_and_lineage_have_no_fabricated_producer(published_root):
    path, files, values, body, _ = published_root
    with closing(sqlite3.connect(path)) as connection:
        caller(connection)
        listed = list_datasets_transaction(connection, files, **context(values), secret=b'authored-test-key'*3)
        assert listed['schema'] == 'geophysics.physical-dataset-list/v2'
        assert listed['next_cursor'] is None and len(listed['items']) == 1
        item = listed['items'][0]
        assert item['dataset_id'] == values['root_dataset_id']
        assert item['dataset_sha256'] == byte_sha(body) and item['bytes'] == len(body)
        assert item['production'] is None and item['parent_dataset_id'] is None
        assert item['created_at'].endswith('Z') and 'storage_key' not in item
        selected = lineage_transaction(connection, files, **context(values), dataset_id=values['root_dataset_id'])
        assert len(selected['nodes']) == 1 and selected['edges'] == selected['productions'] == []
        assert selected['nodes'][0]['sha256'] == byte_sha(body)
        assert selected['selected_dataset_id'] == selected['root_dataset_id'] == values['root_dataset_id']
        for value in (listed, selected):
            response = catalog_response(value)
            assert json.loads(response.body) == value
            assert len(response.body) <= 256*1024 and response.headers['cache-control'] == 'no-store'
        assert connection.in_transaction
        assert connection.execute('SELECT name FROM projects').fetchone() == ('Pending caller metadata',)
        connection.rollback()


@pytest.mark.parametrize('operation', ['list', 'lineage', 'bytes'])
def test_foreign_catalog_context_retains_original_caller_transaction(published_root, operation):
    path, files, values, _, _ = published_root
    with closing(sqlite3.connect(path)) as connection:
        caller(connection)
        arguments = context(values)
        arguments['owner_id'] = str(uuid4())
        before = connection.total_changes
        with pytest.raises(ValueError):
            if operation == 'list':
                list_datasets_transaction(connection, files, **arguments, secret=b'authored-test-key'*3)
            elif operation == 'lineage':
                lineage_transaction(connection, files, **arguments, dataset_id=values['root_dataset_id'])
            else:
                read_dataset_bytes_transaction(connection, files, **arguments, dataset_id=values['root_dataset_id'])
        assert connection.total_changes == before and connection.in_transaction
        assert connection.execute('SELECT name FROM projects').fetchone() == ('Pending caller metadata',)
        connection.rollback()
