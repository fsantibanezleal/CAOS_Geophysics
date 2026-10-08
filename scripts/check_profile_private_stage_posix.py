"""Actual ordinary POSIX producer -> unchanged recovery mode/member regression.

Execute selected production AST bytes, without importing scientific dependencies.
No sudo/systemd/SQLite/root custody or complete privileged-crash claim is made.
Use a fresh explicit external POSIX data root; never the retained q12 directory.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from types import SimpleNamespace
import uuid


def selected(path, names, namespace):
    tree = ast.parse(path.read_bytes(), filename=str(path))
    nodes = [n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    args = parser.parse_args()
    assert os.name == 'posix' and os.geteuid() != 0
    root = Path(args.root)
    assert root.is_absolute() and not root.exists()
    assert not any((p/'.git').exists() for p in root.parents)
    root.mkdir(mode=0o700)
    source = Path(__file__).resolve().parents[1]
    namespace = dict(os=os,stat=stat,Path=Path)
    selected(source/'app/errors.py',('ApiError',),namespace)
    selected(source/'app/profile_linux_worker.py',
        ('require','identity','directory_fd','private_stage_parent','regular_at'),namespace)
    namespace['sha256'] = lambda body:hashlib.sha256(body).hexdigest()
    # Load the real recovery constants and exact private predicates/inventory.
    recovery = source/'app/profile_incomplete_recovery.py'
    tree = ast.parse(recovery.read_bytes())
    constants = [n for n in tree.body if isinstance(n,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id == 'MEMBER_CAPS' for t in n.targets)]
    exec(compile(ast.Module(body=constants,type_ignores=[]),str(recovery),'exec'),namespace)
    namespace['STAGE_CAP'] = 64*1024**2
    selected(recovery,('private_directory','private_member','inventory'),namespace)
    writer = dict(os=os,re=re)
    selected(source/'scripts/profile_linux_supervisor.py',('require','exclusive'),writer)
    count = 0
    original_umask = os.umask(0)
    try:
        # Execute the ACTUAL producer segment, not a fixture mkdir substitute.
        worker_tree = ast.parse((source/'app/profile_linux_worker.py').read_bytes())
        execute = next(n for n in worker_tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name == 'execute')
        statements = next(n for n in execute.body if isinstance(n,ast.Try)).body
        begin = next(i for i,n in enumerate(statements) if isinstance(n,ast.Assign) and
            any(isinstance(t,ast.Name) and t.id == 'stage_parent_fd' for t in n.targets))
        end = next(i for i,n in enumerate(statements) if isinstance(n,ast.Assign) and
            any(isinstance(t,ast.Name) and t.id == 'process' for t in n.targets))
        producer = compile(ast.Module(body=statements[begin:end],type_ignores=[]),str(source/'app/profile_linux_worker.py'),'exec')
        for case in ('empty','partial','all-retained-members'):
            data = root/case
            data.mkdir(mode=0o700)
            identifier = str(uuid.uuid4())
            stage = data/'.job-staging'/identifier
            namespace.update(settings=SimpleNamespace(data_dir=data),job=SimpleNamespace(id=identifier),stage=stage)
            exec(producer,namespace)
            parent_fd,stage_fd = namespace['stage_parent_fd'],namespace['stage_fd']
            try:
                assert stat.S_IMODE(os.fstat(parent_fd).st_mode) == 0o700
                assert stat.S_IMODE(os.fstat(stage_fd).st_mode) == 0o700
                namespace['private_directory'](parent_fd)
                held = namespace['private_directory'](stage_fd)
                assert held == dict(device=stage.stat().st_dev,inode=stage.stat().st_ino)
                assert namespace['inventory'](stage_fd) == {}
                if case != 'empty':
                    for name,body in (('result.json',b'partial unadmitted bytes'),('linux-stderr.txt',b'')):
                        writer['exclusive'](stage_fd,name,body,os.geteuid(),os.getegid())
                        actual,record = namespace['private_member'](stage_fd,name,1024)
                        assert actual == body and record['sha256'] == hashlib.sha256(body).hexdigest()
                        assert stat.S_IMODE(os.stat(name,dir_fd=stage_fd).st_mode) == 0o600
                    assert set(namespace['inventory'](stage_fd)) == {'result.json','linux-stderr.txt'}
                if case == 'all-retained-members':
                    writer['exclusive'](stage_fd,'linux-execution.json',b'operational only',os.geteuid(),os.getegid())
                    namespace['private_member'](stage_fd,'linux-execution.json',1024)
                    assert stat.S_IMODE(os.stat('linux-execution.json',dir_fd=stage_fd).st_mode) == 0o600
                    try:
                        namespace['inventory'](stage_fd)
                    except namespace['ApiError']:
                        pass
                    else:
                        raise AssertionError('execution receipt cannot be incomplete evidence')
                count += 1
            finally:
                os.close(stage_fd)
                os.close(parent_fd)
        # Each unsafe existing producer parent remains byte/identity/mode exact.
        for mode in (0o755,0o750,0o710,0o701,0o770,0o777):
            data = root/('unsafe-'+oct(mode))
            data.mkdir(mode=0o700)
            parent = data/'.job-staging'
            parent.mkdir(mode=mode)
            marker = parent/'unknown.bin'
            marker.write_bytes(b'preserve unknown debt')
            before = parent.lstat()
            try:
                namespace['private_stage_parent'](data)
            except namespace['ApiError']:
                pass
            else:
                raise AssertionError('unsafe existing parent adopted')
            after = parent.lstat()
            assert (before.st_dev,before.st_ino,before.st_mode,before.st_ctime_ns) == (
                after.st_dev,after.st_ino,after.st_mode,after.st_ctime_ns)
            assert marker.read_bytes() == b'preserve unknown debt'
            count += 1
        data = root/'linked-parent'
        data.mkdir(mode=0o700)
        (data/'.job-staging').symlink_to(root/'empty'/'.job-staging',target_is_directory=True)
        try:
            namespace['private_stage_parent'](data)
        except OSError:
            count += 1
        else:
            raise AssertionError('linked parent adopted')
        # Recovery still refuses accessible retained members after real chmod of
        # this gate's OWN fixture, not any pre-existing debt or original input.
        path = root/'partial'/'.job-staging'
        parent_fd = namespace['directory_fd'](path)
        stage_fd = os.open(os.listdir(parent_fd)[0],os.O_RDONLY|os.O_DIRECTORY,dir_fd=parent_fd)
        try:
            os.chmod('result.json',0o644,dir_fd=stage_fd)
            try:
                namespace['inventory'](stage_fd)
            except namespace['ApiError']:
                count += 1
            else:
                raise AssertionError('unsafe member adopted')
        finally:
            os.close(stage_fd)
            os.close(parent_fd)
    finally:
        os.umask(original_umask)
    result = dict(schema='profile-private-stage-posix-regression-1',tests=count,failures=0,
        uid=os.geteuid(),gid=os.getegid(),permissive_umask=0,actual_filesystem=True,
        source_hashes={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in (
            'app/profile_linux_worker.py','app/profile_incomplete_recovery.py','scripts/profile_linux_supervisor.py')},
        privileged_crash_qualified=False)
    with (root/'receipt.json').open('xb') as stream:
        stream.write(json.dumps(result,sort_keys=True).encode()+b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(result,sort_keys=True))


if __name__ == '__main__':
    main()
