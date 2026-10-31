"""Exact current lexical admission; generic and historical limits stay frozen."""

from copy import deepcopy

import pytest

from app.physical_contract import M, canonical, decode_source
from app.physical_tombstone_lexer import (
    INDEX_CAP, INVENTORY, JOINT, JOINT_INVENTORY, RECEIPT, ROOT,
    _CurrentReader, decode_current_tombstone,
)


def envelope(*, joint=False):
    # Lexer envelopes only, deliberately not a valid scientific/SQL tombstone.
    native = dict(schema=RECEIPT, id='x', owner_id='x', project_id='x', deleted_at='x',
                  backup_purge_status='not_attempted')
    for name in ('asset_hashes', 'asset_manifest', 'derived_manifest'):
        native[name] = dict(utf8='[]', bytes=2, sha256='0'*64)
    inventory = dict(schema=JOINT_INVENTORY if joint else INVENTORY, source_policy_sha256='0'*64)
    for name in ('raw_assets', 'datasets', 'edges', 'productions', 'jobs', 'custody',
                 'waveform_sources', 'waveform_artifacts', 'profile_archives'):
        inventory[name] = []
    if joint:
        inventory['joint'] = dict(schema=JOINT, originals=[], datasets=[], sources=[], jobs=[], artifacts=[])
    return dict(schema=ROOT, id='x', project_id='x', owner_id='x', deleted_at='x',
                origin_revision='0005_physical_forest', legacy_receipt=native, physical_inventory=inventory)


@pytest.mark.parametrize('name', ['asset_hashes', 'asset_manifest', 'derived_manifest'])
def test_native_sql_text_only_exact_path_and_original_generic_refusal(name):
    value = envelope()
    original = '["' + '\u03b1'*5000 + '"]'
    value['legacy_receipt'][name]['utf8'] = original
    body = canonical(value)
    assert decode_current_tombstone([body[:30], body[30:]])['legacy_receipt'][name]['utf8'] == original
    with pytest.raises(ValueError, match='^string(?:_limit)?$'):
        decode_source([body], max_bytes=16*M, depth=16, nodes=200000)


@pytest.mark.parametrize('slot', ['dataset', 'index', 'request'])
def test_only_closed_joint_lexical_paths(slot):
    value = envelope(joint=True)
    text = 'a'*9000
    record = dict(utf8=text, bytes=len(text), sha256='0'*64)
    if slot == 'dataset':
        value['physical_inventory']['joint']['datasets'] = [dict(body=record)]
    else:
        value['physical_inventory']['joint']['jobs'] = [dict(index=record if slot == 'index' else None,
                                                           request_utf8=text if slot == 'request' else '{}')]
    assert decode_current_tombstone([canonical(value)]) == value


@pytest.mark.parametrize('damage', ['root-schema', 'receipt-schema', 'inventory-schema', 'joint-schema',
    'extra-root', 'extra-record', 'ordinary-utf8', 'ordinary-base64', 'old-inventory-joint'])
def test_unknown_envelopes_never_reach_build_pass(monkeypatch, damage):
    value = envelope(joint=True)
    if damage == 'root-schema': value['schema'] = 'geophysics.physical-deletion/v1'
    elif damage == 'receipt-schema': value['legacy_receipt']['schema'] = 'unknown'
    elif damage == 'inventory-schema': value['physical_inventory']['schema'] = 'unknown'
    elif damage == 'joint-schema': value['physical_inventory']['joint']['schema'] = 'unknown'
    elif damage == 'extra-root': value['extra'] = True
    elif damage == 'extra-record': value['legacy_receipt']['asset_hashes']['extra'] = True
    elif damage.startswith('ordinary-'):
        value['physical_inventory']['raw_assets'] = [{damage[9:]: 'a'*8193}]
    else: value['physical_inventory']['schema'] = INVENTORY
    original = _CurrentReader.finish
    def tracked(self, *, build):
        assert not build, 'an unregistered envelope reached allocation pass'
        return original(self, build=build)
    monkeypatch.setattr(_CurrentReader, 'finish', tracked)
    with pytest.raises(ValueError): decode_current_tombstone([canonical(value)])


@pytest.mark.parametrize('slot,cap', [('receipt', 4*M), ('index', INDEX_CAP), ('request', INDEX_CAP)])
def test_original_lexical_utf8_caps_before_admission(slot, cap):
    value = envelope(joint=True)
    if slot == 'receipt':
        value['legacy_receipt']['derived_manifest']['utf8'] = 'a'*(cap+1)
    else:
        value['physical_inventory']['joint']['jobs'] = [dict(index=None, request_utf8='{}')]
        row = value['physical_inventory']['joint']['jobs'][0]
        if slot == 'index': row['index'] = dict(utf8='a'*(cap+1), bytes=cap+1, sha256='0'*64)
        else: row['request_utf8'] = 'a'*(cap+1)
    with pytest.raises(ValueError, match='^string(?:_limit)?$'): decode_current_tombstone([canonical(value)])


@pytest.mark.parametrize('damage', ['duplicate', 'nonfinite', 'trailing', 'partial', 'bom', 'utf8', 'chunks'])
def test_original_token_and_eof_refusals(damage):
    body = canonical(envelope())
    if damage == 'duplicate': body = body[:-1] + b',"schema":"' + ROOT.encode() + b'"}'
    elif damage == 'nonfinite': body = body.replace(b'"bytes":2', b'"bytes":NaN', 1)
    elif damage == 'trailing': body += b'{}'
    elif damage == 'partial': body = body[:-1]
    elif damage == 'bom': body = b'\xef\xbb\xbf' + body
    elif damage == 'utf8': body = b'\xff'
    with pytest.raises(ValueError): decode_current_tombstone([body, 'bad'] if damage == 'chunks' else [body])


def test_lexer_does_not_replace_full_identity_validation():
    from app.physical_deleted_inventory import validate_current_tombstone
    value = envelope()
    assert decode_current_tombstone([canonical(value)]) == value
    with pytest.raises(ValueError):
        validate_current_tombstone(decode_current_tombstone([canonical(value)]),
                                  expected_source_policy_sha256='0'*64, approved_installations={})
    copy = deepcopy(value)
    copy['legacy_receipt']['asset_hashes']['utf8'] = 'x'*9000
    with pytest.raises(ValueError):
        validate_current_tombstone(decode_current_tombstone([canonical(copy)]),
                                  expected_source_policy_sha256='0'*64, approved_installations={})
