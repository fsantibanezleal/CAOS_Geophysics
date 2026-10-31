"""Tiny upload custody controls, not fits, actual SQL or native OS proof."""

from copy import deepcopy
import io

import pytest

from app.physical_contract import byte_sha, canonical
from app.physical_joint_custody import original_inventory, scan_stream

OWNER = '10000000-0000-4000-8000-000000000001'
PROJECT = '20000000-0000-4000-8000-000000000002'
ASSET = '30000000-0000-4000-8000-000000000003'
SOURCE = '40000000-0000-4000-8000-000000000004'
BODY = b'Original raw instrument bytes; mechanism control, not scientific data.'
KEY = f'projects/{OWNER}/{PROJECT}/{ASSET}'


class Files:
    def scan_joint_member(self, key, **arguments):
        assert key == KEY
        return scan_stream(io.BytesIO(BODY), **arguments)


def rows():
    return dict(projects=[dict(id=PROJECT, owner_id=OWNER)],
        raw_assets=[dict(id=ASSET, owner_id=OWNER, project_id=PROJECT, source_id=SOURCE,
            sha256=byte_sha(BODY), byte_count=len(BODY), detected_format='joint_native',
            filename='gravity.raw', validation_status='raw_metadata_checked', storage_key=KEY,
            physical_metadata=canonical(dict(schema='joint-native-member-1',role='development',
                name='gravity.raw',descriptor=None,scientific_values_decoded=False,
                scientific_accepted=False)).decode())],
        source_records=[dict(id=SOURCE, owner_id=OWNER, project_id=PROJECT,
            declared_format='joint_native', sha256=byte_sha(BODY), expected_bytes=len(BODY),
            version=1, private_storage_permission='attested', rights_decision='mirror')])


def test_completed_original_before_dataset_is_not_zero_custody_or_science():
    original = rows()
    before = deepcopy(original)
    assert original_inventory(original, Files()) == dict(asset_ids=frozenset([ASSET]),
        source_ids=frozenset([SOURCE]), files={KEY:dict(cap=256*1024**2,bytes=len(BODY),sha256=byte_sha(BODY))})
    assert original == before


@pytest.mark.parametrize('damage', ['foreign_owner','source_owner','orphan_source','duplicate_asset',
    'duplicate_source','missing_source','length','rights','accepted','name','role','path','hash'])
def test_unbound_upload_never_gains_generic_format_whitelist(damage):
    value = rows()
    asset, source = value['raw_assets'][0], value['source_records'][0]
    if damage == 'foreign_owner': value['projects'][0]['owner_id'] = SOURCE
    if damage == 'source_owner': source['owner_id'] = SOURCE
    if damage == 'orphan_source': value['raw_assets'].clear()
    if damage == 'duplicate_asset': value['raw_assets'].append(dict(asset))
    if damage == 'duplicate_source': value['source_records'].append(dict(source))
    if damage == 'missing_source': value['source_records'].clear()
    if damage == 'length': source['expected_bytes'] += 1
    if damage == 'rights': source['rights_decision'] = 'forbidden'
    if damage == 'accepted': asset['physical_metadata'] = asset['physical_metadata'].replace('"scientific_accepted":false','"scientific_accepted":true')
    if damage == 'name': asset['filename'] = 'magnetic.raw'
    if damage == 'role': asset['physical_metadata'] = asset['physical_metadata'].replace('"development"','"unregistered"')
    if damage == 'path': asset['storage_key'] = '../original.raw'
    if damage == 'hash': asset['sha256'] = '0'*64
    with pytest.raises(ValueError):
        original_inventory(value, Files())


def test_joint_source_cannot_be_disguised_as_another_raw_format():
    value = rows()
    value['raw_assets'][0]['detected_format'] = 'gravity_stations_json'
    with pytest.raises(ValueError, match='physical_joint_original_source_inventory'):
        original_inventory(value, Files())
