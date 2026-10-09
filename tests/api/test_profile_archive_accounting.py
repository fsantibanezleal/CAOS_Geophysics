"""Literal profile archive charge survives deletion, no physical erasure claim."""

from copy import deepcopy
import json
from uuid import uuid4

import pytest

from app.physical_accounting import account_private_charge
from app.physical_contract import canonical
from app.profile_archive_custody import retained_inventory
from tests.api.test_physical_forest import connect, forest as forest, successor as successor
from tests.api.test_profile_archive_custody import archive_fixture


def saved_fixture(path, values, tmp_path):
    files,relation,_,installation,_=archive_fixture(tmp_path/'profile')
    relation['owner_id']=values['owner_id']
    # Build one complete native-domain metadata fixture under this real SQL
    # account, then transfer its exact descriptor to a surviving receipt.
    files,relation,_,installation,_=archive_fixture(tmp_path/'owned',declared_relation=relation,
        declared_installation=installation)
    records=retained_inventory(files,[relation],[],approved_installations={relation['id']:installation})
    with connect(path) as db:
        db.execute('''INSERT INTO deletion_receipts(id,project_id,owner_id,deleted_at,asset_hashes,asset_manifest,
            derived_manifest,backup_purge_status) VALUES(?,?,?,?,?,?,?,?)''',
            (str(uuid4()),relation['project_id'],relation['owner_id'],'2026-10-08 12:00:00','[]','[]',
             canonical(records).decode(),'not_attempted'))
    return records,{relation['id']:installation}


def test_deleted_archive_all_literal_copies_remain_charged(forest,tmp_path):
    path,values=forest
    records,approved=saved_fixture(path,values,tmp_path)
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        charge=account_private_charge(db,values['owner_id'],profile_records=records,approved_installations=approved)
        assert charge['profile_retained']==records[0]['charged_bytes']
        assert charge['raw']==7  # Only unrelated live originals remain raw quota.
        assert charge['total']==sum(v for k,v in charge.items() if k!='total')
        db.rollback()


@pytest.mark.parametrize('damage',['no-census','missing','duplicate','charge','authority','owner','saved-drift'])
def test_missing_or_rehashed_archive_never_releases_saved_charge(damage,forest,tmp_path):
    path,values=forest
    records,approved=saved_fixture(path,values,tmp_path)
    before=deepcopy(records)
    if damage=='no-census': records=None
    elif damage=='missing': records=[]
    elif damage=='duplicate': records=records+deepcopy(records)
    elif damage=='charge': records[0]['charged_bytes']-=1
    elif damage=='authority': approved[records[0]['job_id']]['configuration_sha256']='b'*64
    elif damage=='owner': records[0]['owner_id']=str(uuid4())
    with connect(path) as db:
        if damage=='saved-drift':
            changed=deepcopy(before); changed[0]['charged_bytes']-=1
            db.execute('UPDATE deletion_receipts SET derived_manifest=?',(json.dumps(changed),))
        native_before=db.execute('SELECT derived_manifest FROM deletion_receipts').fetchone()
        db.execute('BEGIN IMMEDIATE')
        with pytest.raises(ValueError):
            account_private_charge(db,values['owner_id'],profile_records=records,approved_installations=approved)
        assert db.execute('SELECT derived_manifest FROM deletion_receipts').fetchone()==native_before
        db.rollback()
