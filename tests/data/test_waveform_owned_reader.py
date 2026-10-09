"""Owned pair barrier controls; authored records are not native science proof."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sys
from uuid import UUID, uuid4

import pytest

from tests.api.test_waveform_linux_installation import configuration

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"tests/fixtures/waveform_m08"))
from full_workflow import make_case


def module():
    spec = importlib.util.spec_from_file_location("_m08_owned_reader_test",ROOT/"scripts/waveform_m08_owned_reader.py")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def records(value):
    from waveform_m08_installation import SOURCE_FILES
    config = configuration(type("Authority",(),{"SOURCE_FILES":SOURCE_FILES}))
    owner,project,dataset_id,job_id = [str(uuid4()) for _ in range(4)]
    fixture = make_case("nominal1")
    request = json.loads(fixture["request"])
    request["source"]["citation"] += " café"
    science_sha = value.structural_input().scientific_identity(request)
    sources,assets,bindings,dependencies = {},{},{},[]
    for role in value.ROLE_CAPS:
        body = fixture["mseed" if role == "miniseed" else "stationxml"]
        source_id,asset_id = str(uuid4()),str(uuid4())
        sources[role] = dict(id=source_id,owner_id=owner,project_id=project,version=1,sha256=value.sha(body),
                             rights_decision="mirror",private_storage_permission="attested")
        assets[role] = dict(id=asset_id,owner_id=owner,project_id=project,source_id=source_id,sha256=value.sha(body),
                            byte_count=len(body),detected_format=role,storage_key=f"projects/{owner}/{project}/{asset_id}",
                            physical_metadata={"geometry":{}})
        bindings[role] = dict(asset_id=asset_id,source_id=source_id,source_version=1,raw_sha256=value.sha(body),
                              raw_bytes=len(body),rights_decision="mirror",private_storage_permission="attested")
        dependencies.append(dict(dataset_id=dataset_id,role=role,**{key:bindings[role][key] for key in
                              ("asset_id","source_id","source_version","raw_sha256","raw_bytes")}))
    assets["miniseed"]["physical_metadata"]["geometry"]["stationxml_asset_id"] = assets["stationxml"]["id"]
    payload = dict(schema="geophysics.waveform-dataset/v1",dataset_id=dataset_id,version=1,owner_id=owner,
        project_id=project,raw_asset_id=assets["miniseed"]["id"],parent_raw_sha256=assets["miniseed"]["sha256"],
        parser_version="m08/v1/"+science_sha,modality="waveform_counts_response",
        dimensions=dict(channel=1,sample=18000,record=18),sources=bindings,request=request,
        scientific_request_sha256=science_sha,qc_verdict="structural_index_not_physical_qc")
    data = value.product_bytes(payload)
    dataset = dict(id=dataset_id,owner_id=owner,project_id=project,raw_asset_id=assets["miniseed"]["id"],
        version=1,parser_version=payload["parser_version"],modality=payload["modality"],row_count=18000,
        raw_sha256=assets["miniseed"]["sha256"],sha256=value.sha(data),byte_count=len(data),
        storage_key=f"derived/{owner}/{project}/datasets/{dataset_id}.json")
    immutable = dict(schema="geophysics.processing-request/v1",job_id=job_id,project_id=project,
        dataset_id=dataset_id,dataset_sha256=dataset["sha256"],method_id=value.METHOD,
        parameters=dict(scientific_request_sha256=science_sha),waveform_sources=bindings,
        scientific_request=request,scientific_request_sha256=science_sha,
        implementation_sha256=value.sha(value.canonical(config["source_hashes"])))
    job = dict(id=job_id,owner_id=owner,project_id=project,dataset_id=dataset_id,dataset_sha256=dataset["sha256"],
        method_id=value.METHOD,request_json=immutable,request_sha256=value.sha(value.product_bytes(immutable)),
        preflight=dict(estimated_memory_bytes=1,estimated_scratch_bytes=1,memory_limit_bytes=1073741824,
            scratch_limit_bytes=52690944,wall_limit_seconds=120,memory_kind="platform_committed_or_cgroup_charge_not_rss",
            cpu_budget_ns=60000000000,cpu_stop_ns=57000000000),state="running",cancel_requested=False)
    return config,dict(job=job,project=dict(id=project,owner_id=owner),dataset=dataset,
                       dependencies=dependencies,assets=assets,sources=sources),payload


def test_closed_real_definition_pair_keeps_existing_canonical_domains():
    value = module()
    config,record,payload = records(value)
    keys = value.checked_relations(config,record["job"]["id"],record,payload)
    assert keys == {role:item["storage_key"] for role,item in record["assets"].items()}
    assert value.product_bytes(record["job"]["request_json"]) != value.canonical(record["job"]["request_json"])
    assert record["job"]["request_sha256"] == value.sha(value.product_bytes(record["job"]["request_json"]))


@pytest.mark.parametrize("change",[
    lambda r:r["job"].update(state="queued"),lambda r:r["job"].update(cancel_requested=True),
    lambda r:r["job"].update(cancel_requested=0),lambda r:r["job"].update(method_id="mt.edi-qc/v1"),
    lambda r:r["project"].update(owner_id=str(uuid4())),lambda r:r["dataset"].update(owner_id=str(uuid4())),
    lambda r:r["dataset"].update(storage_key="../../api.sqlite3"),lambda r:r["dataset"].update(raw_sha256="a"*64),
    lambda r:r["dataset"].update(parser_version="old"),lambda r:r["dataset"].update(sha256="a"*64),
    lambda r:r["dependencies"].pop(),lambda r:r["dependencies"][0].update(role="stationxml"),
    lambda r:r["dependencies"][0].update(source_version=2),lambda r:r["dependencies"][0].update(raw_bytes=1),
    lambda r:r["sources"]["stationxml"].update(owner_id=str(uuid4())),
    lambda r:r["sources"]["stationxml"].update(private_storage_permission="unknown"),
    lambda r:r["sources"]["stationxml"].update(rights_decision="forbidden"),
    lambda r:r["sources"]["stationxml"].update(sha256="a"*64),
    lambda r:r["assets"]["stationxml"].update(storage_key="/etc/shadow"),
    lambda r:r["assets"]["stationxml"].update(detected_format="miniseed"),
    lambda r:r["assets"]["miniseed"].update(physical_metadata={"geometry":{}}),
    lambda r:r["job"]["preflight"].update(cpu_budget_ns=60000000001),
    lambda r:r["job"]["preflight"].update(cpu_stop_ns=57000000001),
    lambda r:r["job"]["preflight"].update(memory_limit_bytes=1073741825),
    lambda r:r["job"]["preflight"].update(scratch_limit_bytes=52690945),
    lambda r:r["job"]["preflight"].update(wall_limit_seconds=121),
    lambda r:r["job"]["preflight"].update(estimated_scratch_bytes=True),
    lambda r:r["job"].update(extra=True),
])
def test_foreign_mutated_or_relaxed_relations_refuse(change):
    value = module()
    config,record,payload = records(value)
    changed = deepcopy(record)
    change(changed)
    with pytest.raises(ValueError):
        value.checked_relations(config,record["job"]["id"],changed,payload)


@pytest.mark.parametrize("change",[
    lambda q:q.update(implementation_sha256="a"*64),lambda q:q.update(command="/bin/sh"),
    lambda q:q.update(dataset_id=str(uuid4())),lambda q:q.update(scientific_request_sha256="a"*64),
    lambda q:q["parameters"].update(extra=1),lambda q:q["scientific_request"]["source"].update(rights="unknown"),
    lambda q:q["waveform_sources"]["miniseed"].update(source_version=2),
])
def test_consistently_rehashed_but_changed_request_cannot_adopt_original_index(change):
    value = module()
    config,record,payload = records(value)
    record = deepcopy(record)
    change(record["job"]["request_json"])
    record["job"]["request_sha256"] = value.sha(value.product_bytes(record["job"]["request_json"]))
    with pytest.raises(ValueError):
        value.checked_relations(config,record["job"]["id"],record,payload)


def ordinary_database(tmp_path):
    import sqlite3
    value = module()
    config,record,payload = records(value)
    config.update(uid=65534,gid=65534,science_uid=61901,science_gid=61901,data_root=str(tmp_path/"private"))
    assert os.geteuid() == 0
    assert tmp_path.is_absolute() and not tmp_path.is_relative_to(ROOT)
    # These are authored relation controls, never an original scientific fixture mirror.
    private = Path(config["data_root"])
    private.mkdir()
    fixture = make_case("nominal1")
    for role,asset in record["assets"].items():
        path = private/asset["storage_key"]
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(fixture["mseed" if role == "miniseed" else "stationxml"])
    index = private/record["dataset"]["storage_key"]
    index.parent.mkdir(parents=True,exist_ok=True)
    index.write_bytes(value.product_bytes(payload))
    database = private/"api.sqlite3"
    with sqlite3.connect(database) as db:
        rows = {"processing_jobs":[record["job"]],"projects":[record["project"]],
                "observation_datasets":[record["dataset"]],"waveform_dataset_sources":record["dependencies"],
                "raw_assets":list(record["assets"].values()),"source_records":list(record["sources"].values())}
        for table,items in rows.items():
            keys = sorted(items[0])
            db.execute("CREATE TABLE "+table+" ("+",".join(keys)+")")
            for item in items:
                sql = {key:(json.dumps(v) if type(v) is dict else UUID(v).hex if key == "owner_id" else v)
                       for key,v in item.items()}
                db.execute("INSERT INTO "+table+" ("+",".join(keys)+") VALUES ("+",".join("?" for _ in keys)+")",
                           tuple(sql[key] for key in keys))
    # Only the fresh pytest leaf/basetemp, never its existing external ancestors.
    for path in (tmp_path,tmp_path.parent):
        path.chmod(0o755)
    for path in (private,*private.rglob("*")):
        path.chmod(0o755 if path.is_dir() else 0o644)
    return value,config,record,database


@pytest.mark.skipif(sys.platform != "linux" or os.environ.get("M08_RUN_LINUX_NATIVE") != "1",
                    reason="explicit Linux root fork/UID qualification only; not production or science proof")
def test_actual_reader_opens_sqlite_and_both_originals_only_after_irrevocable_drop(tmp_path,monkeypatch):
    import sqlite3
    import stat
    value,config,record,database = ordinary_database(tmp_path)
    config['source_root'] = str(ROOT)
    secret = tmp_path/"root-only-sentinel"
    secret.write_bytes(b"root-reader-descriptor-must-not-survive")
    secret.chmod(0o600)
    sentinel = os.open(secret,os.O_RDONLY)
    original = value.os.execve
    def inspected(path,argv,environment):
        assert os.getuid() == os.geteuid() == 65534
        assert os.getgid() == os.getegid() == 65534 and os.getgroups() == []
        with pytest.raises(OSError):
            os.fstat(sentinel)
        with pytest.raises(PermissionError):
            os.open(secret,os.O_RDONLY)
        with pytest.raises(PermissionError):
            os.setuid(0)
        assert path == '/usr/bin/python3' and environment == {} and os.getcwd() == '/'
        assert argv == value.reader_argv(config,record['job']['id'])
        return original(path,argv,environment)
    monkeypatch.setattr(value.os,"execve",inspected)
    try:
        packet = value.nonroot_query(config,record["job"]["id"])
        assert packet["record"] == record
        assert packet["reader"] == dict(uid=65534,gid=65534,groups=[])
        # The API's ordinary files are neither adopted nor chmod'd by root reader.
        assert stat.S_IMODE(database.stat().st_mode) == 0o644
        with sqlite3.connect(database) as db:
            db.execute("UPDATE source_records SET private_storage_permission='unknown' WHERE id=?",
                       (record["sources"]["stationxml"]["id"],))
        with pytest.raises(ValueError,match="waveform_owned_reader_refused"):
            value.nonroot_query(config,record["job"]["id"])
    finally:
        os.close(sentinel)


def live_wal(database):
    """Separate ordinary writer: observer must not inherit an already-mapped WAL."""
    from contextlib import contextmanager
    import select
    import sqlite3
    @contextmanager
    def held():
        os.chown(database,65534,65534)
        os.chown(database.parent,65534,65534)
        ready_read,ready_write = os.pipe()
        stop_read,stop_write = os.pipe()
        pid = os.fork()
        if pid == 0:
            try:
                os.close(ready_read)
                os.close(stop_write)
                os.setgroups([])
                os.setgid(65534)
                os.setuid(65534)
                with sqlite3.connect(database) as connection:
                    assert connection.execute('PRAGMA journal_mode=WAL').fetchone() == ('wal',)
                    connection.execute('CREATE TABLE reader_mechanism (value)')
                    connection.execute('INSERT INTO reader_mechanism VALUES (1)')
                    connection.commit()
                    os.write(ready_write,b'R')
                    assert os.read(stop_read,1) == b'S'
                os._exit(0)
            except BaseException:
                os._exit(2)
        os.close(ready_write)
        os.close(stop_read)
        try:
            assert select.select([ready_read],[],[],5)[0]
            assert os.read(ready_read,1) == b'R'
            assert Path(str(database)+'-wal').is_file()
            assert Path(str(database)+'-shm').is_file()
            yield
        finally:
            try:
                os.write(stop_write,b'S')
            except BrokenPipeError:
                pass
            os.close(stop_write)
            os.close(ready_read)
            assert os.waitstatus_to_exitcode(os.waitpid(pid,0)[1]) == 0
    return held()


@pytest.mark.skipif(sys.platform != "linux" or os.environ.get("M08_RUN_LINUX_NATIVE") != "1",
                    reason="actual live-WAL mechanics under original limits, not science proof")
def test_actual_legacy_inherited_wal_mapping_refuses_under_original_limit(tmp_path):
    import mmap
    import resource
    import select
    import sqlite3
    _,_,_,database = ordinary_database(tmp_path)
    with live_wal(database),mmap.mmap(-1,320*1024**2) as reservation:
        assert len(reservation) == 320*1024**2  # Virtual reservation, never written.
        read,write = os.pipe()
        pid = os.fork()
        if pid == 0:
            try:
                os.close(read)
                os.setgroups([])
                os.setgid(65534)
                os.setuid(65534)
                resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
                resource.setrlimit(resource.RLIMIT_CPU,(5,5))
                try:
                    with sqlite3.connect('file:'+str(database)+'?mode=ro',uri=True) as db:
                        db.execute('SELECT value FROM reader_mechanism').fetchone()
                except sqlite3.OperationalError as error:
                    os.write(write,str(error.sqlite_errorcode).encode('ascii'))
                    os._exit(0)
                os._exit(3)
            except BaseException:
                os._exit(2)
        os.close(write)
        try:
            assert select.select([read],[],[],8)[0]
            assert os.read(read,64) == b'5386'
        finally:
            os.close(read)
            assert os.waitstatus_to_exitcode(os.waitpid(pid,0)[1]) == 0


@pytest.mark.skipif(sys.platform != "linux" or os.environ.get("M08_RUN_LINUX_NATIVE") != "1",
                    reason="actual live-WAL fresh image under original limits, not science proof")
def test_actual_fresh_reader_reopens_live_wal_under_original_limit(tmp_path):
    import mmap
    value,config,record,database = ordinary_database(tmp_path)
    config['source_root'] = str(ROOT)
    with live_wal(database),mmap.mmap(-1,320*1024**2) as reservation:
        assert len(reservation) == 320*1024**2
        packet = value.nonroot_query(config,record['job']['id'])
        assert packet['record'] == record
        assert packet['reader'] == dict(uid=65534,gid=65534,groups=[])
