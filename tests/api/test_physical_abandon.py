"""Root abandonment cuts preserve literal liability; no native/scientific claim."""

from uuid import uuid4

import pytest

from app.physical_abandon import abandon_root
from app.physical_roots import prepare_root
from tests.api.test_physical_forest import connect
from tests.api.test_physical_roots import root_case as root_case, install_fixture
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


def arguments(values):
    return dict(owner_id=values['owner_id'],project_id=values['project_id'],intent_id=values['intent_id'],
                abandon_batch_id=str(uuid4()),abandoned_us=3)


@pytest.mark.parametrize('installed',[False,True])
def test_abandon_root_never_adopts_copy_and_transfers_each_literal_charge(root_case,installed):
    path,files,values,body,original=root_case
    with connect(path) as db:
        prepare_root(db,files,**values)
        if installed:
            install_fixture(files,values,body)
        result=abandon_root(db,files,**arguments(values))
        assert result['installed_targets']==int(installed)
        assert not db.execute('SELECT 1 FROM observation_datasets').fetchone()
        assert not db.execute('SELECT 1 FROM physical_publication_intents').fetchone()
        assert not db.execute('SELECT 1 FROM physical_dataset_families').fetchone()
        assert not db.execute('SELECT 1 FROM physical_publication_targets').fetchone()
        assert db.execute('SELECT sum(charged_bytes) FROM physical_custody_batches').fetchone()==(
            len(original)+len(body)*(1+int(installed)),)
        assert db.execute("SELECT count(*) FROM physical_custody_batches WHERE state='cleanup_pending'").fetchone()==(1+int(installed),)
        assert (files.root/f".job-staging/{values['root_dataset_id']}/dataset.json").read_bytes()==body
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]


@pytest.mark.parametrize('cut',['debt','retired'])
def test_uncertain_abandonment_retains_sql_reservations_and_all_files(root_case,cut):
    path,files,values,body,_=root_case
    with connect(path) as db:
        prepare_root(db,files,**values)
        install_fixture(files,values,body)
        def fail(point):
            if point==cut:
                raise RuntimeError('injected_root_abandon_cut')
        with pytest.raises(RuntimeError):
            abandon_root(db,files,**arguments(values),failure_cut=fail)
        assert db.execute('SELECT count(*) FROM physical_publication_intents').fetchone()==(1,)
        assert db.execute('SELECT state,reserved_count FROM physical_dataset_families').fetchone()==('pending',1)
        assert db.execute('SELECT state FROM physical_custody_batches').fetchone()==('sealed',)


@pytest.mark.parametrize('change',['foreign_owner','foreign_project','corrupt_target','unknown_stage','mismatched_target','wrong_family'])
def test_unknown_or_foreign_state_is_preserved_not_conveniently_abandoned(root_case,change):
    path,files,values,body,_=root_case
    with connect(path) as db:
        prepare_root(db,files,**values)
        install_fixture(files,values,body)
        request=arguments(values)
        if change=='foreign_owner':
            request['owner_id']=str(uuid4())
        elif change=='foreign_project':
            request['project_id']=str(uuid4())
        elif change=='corrupt_target':
            target=db.execute('SELECT storage_key FROM physical_publication_targets').fetchone()[0]
            (files.root/target).write_bytes(b'unknown bytes')
        elif change=='unknown_stage':
            (files.root/f".job-staging/{values['root_dataset_id']}/unknown").write_bytes(b'unknown')
        elif change=='mismatched_target':
            db.execute("UPDATE physical_publication_targets SET sha256=?",('a'*64,))
        else:
            db.execute("UPDATE physical_dataset_families SET state='published',published_count=1,reserved_count=0")
        with pytest.raises((ValueError,OSError)):
            abandon_root(db,files,**request)
        assert db.execute('SELECT count(*) FROM physical_publication_intents').fetchone()==(1,)
        assert not db.execute('SELECT 1 FROM observation_datasets').fetchone()


def test_abandonment_never_commits_an_outer_transaction(root_case):
    path,files,values,_,_=root_case
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        with pytest.raises(ValueError,match='outside_transaction'):
            abandon_root(db,files,**arguments(values))
        assert db.in_transaction
        db.rollback()
