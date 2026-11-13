"""Actual source-bound navigation tokens, never scientific admission tokens."""

import base64
import hashlib
import hmac
from uuid import uuid4

import pytest

from app.physical_catalog import _cursor, _open_cursor, _secret, _bounded, _order_time

SECRET = b'controlled-navigation-test-secret-only' * 2
OWNER, PROJECT, ANCHOR, LAST = (str(uuid4()) for _ in range(4))
AFTER = ('2026-10-08 12:34:56.123456', LAST)


def token():
    return _cursor(SECRET, OWNER, PROJECT, 123, ANCHOR, AFTER)


def test_exact_closed_navigation_roundtrip_is_bounded_and_context_bound():
    value = token()
    assert len(value) <= 256 and '=' not in value
    assert _open_cursor(value, SECRET, OWNER, PROJECT) == (123, ANCHOR, AFTER)


@pytest.mark.parametrize('damage', ['owner','project','secret','signature','source','padding','overlength','trailing','version','length','stamp'])
def test_no_cross_context_unknown_or_rehashed_cursor_is_adopted(damage):
    value, secret, owner, project = token(), SECRET, OWNER, PROJECT
    if damage == 'owner': owner = str(uuid4())
    elif damage == 'project': project = str(uuid4())
    elif damage == 'secret': secret = b'x' * 64
    elif damage == 'source': value = '!'
    elif damage == 'padding': value += '='
    elif damage == 'overlength': value = 'A' * 257
    else:
        packet = base64.urlsafe_b64decode(value + '='*((-len(value)) % 4))
        body = bytearray(packet[:-32])
        if damage == 'signature':
            value = base64.urlsafe_b64encode(packet[:-1] + bytes([packet[-1] ^ 1])).decode().rstrip('=')
        else:
            if damage == 'trailing': body += b'\0'
            elif damage == 'version': body[:4] = b'PCD2'
            elif damage == 'length': body[60] = 27
            elif damage == 'stamp': body[61] = 255
            value = base64.urlsafe_b64encode(body + hmac.digest(_secret(SECRET), body, hashlib.sha256)).decode().rstrip('=')
    with pytest.raises(ValueError):
        _open_cursor(value, secret, owner, project)


@pytest.mark.parametrize('value', [True, '', '2026-10-08T00:00:00Z', '2026-02-30 00:00:00', '2026-10-08 12:34:56.1234567',
    '2026-10-08 12:34:56+01:00', '2026-10-08 12:34:56-00:00', '2026-10-08 12:34:56.1234567+00:00'])
def test_no_coerced_or_invalid_database_order_timestamp(value):
    with pytest.raises(ValueError): _order_time(value)


@pytest.mark.parametrize('stamp', ['2026-10-08 12:34:56+00:00', '2026-10-08 12:34:56.123456+00:00'])
def test_native_utc_database_key_roundtrips_without_timestamp_normalization(stamp):
    after = (stamp, LAST)
    value = _cursor(SECRET, OWNER, PROJECT, 123, ANCHOR, after)
    assert len(value) <= 256
    assert _open_cursor(value, SECRET, OWNER, PROJECT) == (123, ANCHOR, after)


def test_receipt_total_and_ordinary_string_caps_never_emit_partial_projection():
    with pytest.raises(ValueError): _bounded({'items': ['x' * 8193]})
    with pytest.raises(ValueError): _bounded({'items': ['x' * 8000] * 40})


def test_native_operations_are_closed_source_owned_catalog_functions():
    from app.physical_async_sql import _operation
    from app.physical_catalog import list_datasets_transaction, lineage_transaction
    assert _operation('list_datasets_transaction') is list_datasets_transaction
    assert _operation('lineage_transaction') is lineage_transaction
    with pytest.raises(ValueError): _operation('list_any_dataset')
