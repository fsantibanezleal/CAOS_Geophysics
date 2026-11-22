"""Actual archived original books; original logical/outer guards stay intact."""
import os
from pathlib import Path

import pytest

import gravity_irls_pool as pool
import gravity_l2 as l2
import gravity_workflow_io as transport


def test_original_nonzero_native_books_compact_before_partition_guard():
    # Read-only historical original48 scientific fixture, not an invented fit
    # or permission to replay its old science through a changed source epoch.
    archive = Path(os.environ['GEOPHYSICS_M02_ORIGINAL_NATIVE_ARCHIVE'])
    wrapper = transport.native_from_archive(archive.read_bytes())
    original = pool.decode(wrapper['partition'])
    books = (original['initialization_evidence'],)+original['native_evidence']
    assert len(books) == 22
    compact = tuple(pool.encode_compact(pool.decode(book)) for book in books)
    for before, after in zip(books, compact):
        assert before['raw_sha256'] == after['raw_sha256']
        assert after['schema'] == 'gravity-irls-typed-pool-2'
        assert pool.survey._digest(pool.decode(before)) == pool.survey._digest(pool.decode(after))
    # Logical occurrences, not identity deduplication. The deliberately larger
    # encoded wrapper hits its unchanged scalar cap with repeated strings.
    with pytest.raises(ValueError, match='storage/metadata/scalar cap'):
        l2._result_native_metadata({'native_evidence': books*7})
    l2._result_native_metadata({'native_evidence': compact*7})
    data = transport.archive_bytes({'native_evidence': compact*7})
    read = transport.native_from_archive(data)
    for index, encoded in enumerate(read['native_evidence']):
        assert pool.survey._digest(pool.decode(encoded)) == books[index % 22]['raw_sha256']
