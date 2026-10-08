"""Literal pinned migration capsule in an exclusive external copied fixture.

No default mount, schema aliases/stamps, file deletion or numerical execution.
"""
import hashlib
import difflib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[2]
M01 = 'd22238737aab4645ba75d18a74251c3bb840fd64'
M11 = 'b9cd9a196f912a2134805b89db1e94d5bbda5546'
M03 = '6909634906584f8512a3acf73b385d1bdd63cbc0'
PINS = {
    (M01,'app/migrations/versions/0001_api_foundation.py'):'f595ce71642f8555c9a7e3e615aeccf1f642eaf2a1be09f8864b25a8797e52ae',
    (M01,'app/migrations/versions/0002_private_storage_permission.py'):'572a55739d70b0fc54f6bfdc3fa19ed3ab514fac2136feb817a3c8c89f2551ca',
    (M01,'app/migrations/versions/0003_processing_jobs.py'):'06a9437a41e6665e1689cb85af0789c741e420dc380888139ed138c2abe4939f',
    (M01,'app/migrations/candidates/0004_waveform_artifacts.py'):'82c827b94940d803fae42eb7137fda63f2b4d816e11dddd481f79c5b3cb41ac3',
    (M01,'app/migrations/candidates/0005_physical_forest.py'):'77610d1f49dc1ffe2b4cd8bbb5c8f3afa39c63266c1a89850c2f17afa7803a8f',
    (M01,'app/migrations/physical_successor/env.py'):'50e71e32a227481f92e420cb7d54e5e9d2c0c15762f7a6f0ed1643ed334aeb2b',
    (M01,'app/physical_persistence.py'):'37281cd0af47128b72f9783834e2aafb00a826a97e9d716dfc5727bd0637ce2a',
    (M01,'app/physical_successor.py'):'0ec64cc98ce35cea03ede8eb97a3b0641ae5cc37b18befde7f1e76b222f9f97d',
    (M11,'app/migrations/candidates/0006_joint_artifacts.py'):'1543352aa96da92c56741f246ee12e484f0c27ea15a9c373b43d28362736274c',
    (M11,'app/joint_models.py'):'345a1e4d2fe767b196482a8ef4acdba66d6ba1a436e24646062dbe751055db3f',
    (M11,'app/joint_successor.py'):'a2b410c4e0f60b5e66e6935f49af3172a51711b7b7db1b734be8842a64c7fa1f',
    (M03,'app/magnetic_line_survey_migrations/0007_magnetic_line_artifacts.py'):'c598c9e67406ea7259068d5a02b7d6eef6ee5747b0be311ed664a249f5fb934a',
}


def mount_packet(output):
    """Emit additive literal source patch, not an automatic default mount."""
    assert output.is_absolute() and not output.exists()
    assert all(not (p/'.git').exists() for p in (output,*output.parents))
    selected=[(c,n,h) for (c,n),h in PINS.items() if n.endswith((
        '/0005_physical_forest.py','/0006_joint_artifacts.py','/0007_magnetic_line_artifacts.py',
        '/joint_models.py','/joint_successor.py'))]
    patches=[];records=[]
    for commit,name,digest in selected:
        body=subprocess.check_output(['git','-C',str(ROOT),'show',commit+':'+name])
        assert hashlib.sha256(body).hexdigest()==digest
        target='app/migrations/versions/'+Path(name).name if '/candidates/' in name or '/magnetic_line_survey_migrations/' in name else name
        patches.extend(difflib.unified_diff([],body.decode('utf-8').splitlines(keepends=True),
            fromfile='/dev/null',tofile='b/'+target))
        records.append(dict(commit=commit,source=name,target=target,sha256=digest,bytes=len(body)))
    patch=''.join(patches).encode('utf-8')
    document=dict(schema='geophysics.union-migration-mount-packet/v1',records=records,
        patch_sha256=hashlib.sha256(patch).hexdigest(),default_mounted=False,
        m01_downgrade='0005-to-0004 always refused by literal source',
        m03_composite_sql_ownership='not established: separate FKs accept cross-owner intake')
    output.mkdir(parents=True,exist_ok=False)
    with (output/'migration-mount.patch').open('xb') as f: f.write(patch)
    with (output/'manifest.json').open('x',encoding='utf-8',newline='\n') as f:
        json.dump(document,f,indent=2,sort_keys=True)
        f.write('\n')
    print(json.dumps(document,sort_keys=True))


def capsule(output):
    assert output.is_absolute() and not output.exists()
    assert all(not (p/'.git').exists() for p in (output,*output.parents))
    bodies = {}
    # Close all source bytes before creating or opening any SQL target.
    for (commit,name),digest in PINS.items():
        body = subprocess.check_output(['git','-C',str(ROOT),'show',commit+':'+name])
        assert hashlib.sha256(body).hexdigest() == digest, name
        bodies[name] = body
    for name in ('app/physical_persistence.py','app/physical_successor.py'):
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == hashlib.sha256(bodies[name]).hexdigest()
    output.mkdir()
    versions=output/'versions';versions.mkdir()
    # Preserve env.py's original product-relative parent depth; target database
    # stays a sibling of copied source, never inside its declared product root.
    environment=output/'source/app/migrations/physical_successor';environment.mkdir(parents=True)
    modules=output/'modules';modules.mkdir()
    for name,body in bodies.items():
        if '/candidates/' in name or '/versions/' in name or '/magnetic_line_survey_migrations/' in name:
            target=versions/Path(name).name
        elif name.endswith('/env.py'): target=environment/'env.py'
        else: target=modules/Path(name).name
        with target.open('xb') as f: f.write(body)
    for leaf in ('joint_models','joint_successor'):
        name='app.'+leaf
        if name in sys.modules:
            assert getattr(sys.modules[name],'__union_source_sha256__',None)==hashlib.sha256(bodies['app/'+leaf+'.py']).hexdigest()
        else:
            spec=importlib.util.spec_from_file_location(name,modules/(leaf+'.py'))
            module=importlib.util.module_from_spec(spec)
            sys.modules[name]=module
            spec.loader.exec_module(module)
            module.__union_source_sha256__=hashlib.sha256(bodies['app/'+leaf+'.py']).hexdigest()
    config=Config(str(ROOT/'app/alembic.ini'))
    config.set_main_option('script_location',str(environment))
    config.set_main_option('version_locations',str(versions))
    config.attributes['m01_successor_candidate_only']=True
    script=ScriptDirectory.from_config(config)
    assert script.get_heads()==['0007_magnetic_line_artifacts']
    assert [(r.revision,r.down_revision) for r in script.walk_revisions()]==[
        ('0007_magnetic_line_artifacts','0006_joint_artifacts'),('0006_joint_artifacts','0005_physical_forest'),
        ('0005_physical_forest','0004_waveform_artifacts'),('0004_waveform_artifacts','0003_processing_jobs'),
        ('0003_processing_jobs','0002_private_storage_permission'),('0002_private_storage_permission','0001_api_foundation'),
        ('0001_api_foundation',None)]
    source_manifest=[dict(commit=c,path=n,sha256=h,bytes=len(bodies[n])) for (c,n),h in PINS.items()]
    with (output/'source-manifest.json').open('x',encoding='utf-8') as f:
        json.dump(source_manifest,f,indent=2,sort_keys=True)
    return config, output/'union.sqlite3'


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--mount-packet',type=Path,required=True)
    mount_packet(parser.parse_args().mount_packet)
