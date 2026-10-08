"""Actual POSIX closed namespace controls, no adoption or live mutation."""

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch

from app.physical_contract import ContractError
from app.physical_posix import PrivateFiles


BODY = b'original retained station bytes\n'


def declaration():
    return {'source/raw': dict(cap=4096, bytes=len(BODY), sha256=hashlib.sha256(BODY).hexdigest(), required=True),
            'stage/optional': dict(cap=4096, bytes=None, sha256=None, required=False)}


def make(root, name):
    path = root/name
    path.mkdir(mode=0o700)
    (path/'source').mkdir(mode=0o700)
    (path/'source/raw').write_bytes(BODY)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    root = Path(parser.parse_args().root)
    assert root.is_absolute() and os.name == 'posix' and os.geteuid() != 0
    cases = []
    positive = make(root, 'complete')
    (positive/'stage').mkdir(mode=0o700)
    (positive/'stage/optional').write_bytes(b'known partial')
    (positive/'cache').mkdir(mode=0o700)
    with PrivateFiles(positive) as files:
        actual = files.census(declaration(), empty_directories=('cache',))
    assert set(actual) == {'source/raw', 'stage/optional'}
    assert actual['source/raw']['bytes'] == len(BODY)
    assert actual['source/raw']['sha256'] == hashlib.sha256(BODY).hexdigest()
    assert actual['stage/optional']['sha256'] == hashlib.sha256(b'known partial').hexdigest()
    cases.append('exact_complete_and_known_partial')
    with PrivateFiles(make(root, 'absent_optional')) as files:
        assert set(files.census(declaration())) == {'source/raw'}
    cases.append('optional_absence_no_adoption')

    controls = ('unknown_file', 'unknown_directory', 'symlink', 'hardlink', 'fifo',
                'oversize', 'missing_required', 'wrong_hash', 'wrong_bytes',
                'namespace_overlap', 'bad_cap', 'bool_bytes', 'bad_required',
                'unknown_record_key', 'bad_empty_declaration', 'parent_escape')
    for name in controls:
        path = make(root, name)
        expected, empty = deepcopy(declaration()), ()
        if name == 'unknown_file':
            (path/'unexpected').write_bytes(b'never adopt')
        elif name == 'unknown_directory':
            (path/'unexpected').mkdir(mode=0o700)
        elif name == 'symlink':
            (path/'alias').symlink_to('source/raw')
            expected['alias'] = deepcopy(expected['source/raw'])
        elif name == 'hardlink':
            os.link(path/'source/raw', path/'alias')
            expected['alias'] = deepcopy(expected['source/raw'])
        elif name == 'fifo':
            os.mkfifo(path/'fifo', 0o600)
            expected['fifo'] = dict(cap=4096,bytes=None,sha256=None,required=True)
        elif name == 'oversize':
            expected['source/raw']['cap'] = 1
            expected['source/raw']['bytes'] = None
        elif name == 'missing_required':
            expected['absent'] = deepcopy(expected['source/raw'])
        elif name == 'wrong_hash':
            expected['source/raw']['sha256'] = '0'*64
        elif name == 'wrong_bytes':
            expected['source/raw']['bytes'] += 1
        elif name == 'namespace_overlap':
            expected['source'] = deepcopy(expected['source/raw'])
        elif name == 'bad_cap':
            expected['source/raw']['cap'] = True
        elif name == 'bool_bytes':
            expected['source/raw']['bytes'] = True
        elif name == 'bad_required':
            expected['source/raw']['required'] = 1
        elif name == 'unknown_record_key':
            expected['source/raw']['adopt'] = True
        elif name == 'bad_empty_declaration':
            empty = 'cache'
        elif name == 'parent_escape':
            expected['../raw'] = expected.pop('source/raw')
        with PrivateFiles(path) as files:
            try:
                files.census(expected, empty_directories=empty)
            except ContractError:
                pass
            else:
                raise AssertionError('negative admitted: '+name)
        assert (path/'source/raw').read_bytes() == BODY
        cases.append(name)

    path = make(root, 'unknown_body_not_read')
    (path/'source/raw').rename(path/'source/unregistered')
    with PrivateFiles(path) as files, patch('app.physical_posix.os.read', side_effect=AssertionError('unknown body read')):
        try:
            files.census(declaration())
        except ContractError:
            pass
        else:
            raise AssertionError('unknown admitted')
    assert (path/'source/unregistered').read_bytes() == BODY
    cases.append('unknown_body_not_read')

    path = make(root, 'read_mutation')
    original_read = os.read
    changed = False
    def mutate(descriptor, length):
        nonlocal changed
        value = original_read(descriptor, length)
        if not changed:
            changed = True
            with (path/'source/raw').open('ab') as stream:
                stream.write(b'retained mutation')
        return value
    with PrivateFiles(path) as files, patch('app.physical_posix.os.read', side_effect=mutate):
        try:
            files.census(declaration())
        except ContractError:
            pass
        else:
            raise AssertionError('mutation admitted')
    assert (path/'source/raw').read_bytes() == BODY+b'retained mutation'
    cases.append('actual_read_mutation_refused')
    print(json.dumps(dict(schema='geophysics.physical-census-drill/v1', uid=os.geteuid(), cases=cases,
                          case_count=len(cases), preserved_originals=True, production_activated=False),sort_keys=True))


if __name__ == '__main__':
    main()
