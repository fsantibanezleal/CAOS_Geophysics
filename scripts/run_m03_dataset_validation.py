"""Fail-first genuine owner component tests under the shared dispatcher only."""
import argparse
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from run_m03_qr_reproduction import dispatcher_ancestry,native_startup_receipt,base,core,io,read,require

PRODUCT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    names=('scope','native-executable','api-packages','scientific-packages','output','dispatcher-lock',
        'retained-root','parent-executable','context-root')
    for name in names:
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--native-parent',action='store_true')
    args=parser.parse_args()
    require(args.scope in ('accounting','native'))
    lock=base.strict_json(read(args.dispatcher_lock,65536));require(set(lock)=={'pid','token'})
    occupancy=dispatcher_ancestry(lock['pid'])
    executable=Path(args.native_executable).resolve(strict=True)
    require(sha256(executable.read_bytes()).hexdigest()=='5365b422ee178f691988eb937b7abca5f48910b148f76fcce6dbaf5585c948d0')
    output=Path(args.output);require(not output.exists())
    io.external_path(output.parent)
    from run_m03_native_context import IMAGE_SHA,PARENT_SHA,image_identity
    parent=Path(args.parent_executable).resolve(strict=True)
    require(sha256(parent.read_bytes()).hexdigest()==PARENT_SHA)
    startup=native_startup_receipt(args.context_root)
    if not args.native_parent:
        require(sys.version_info[:2]==(3,13))
        bootstrap=output.with_name(output.name+'-parent-context')
        require(not bootstrap.exists());bootstrap.mkdir()
        command=[str(parent),'-B','-S',str(Path(__file__).resolve()),'--native-parent']
        for name in names:command.extend(['--'+name,getattr(args,name.replace('-','_'))])
        core._write_member(bootstrap,'seal.json',base.canonical_bytes(dict(schema='m03-dataset-native-parent-seal/1',
            argv=command,dispatcher_lock=lock,occupancy=occupancy,startup_receipt_sha256=base.digest(startup),
            source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),native_image_sha256=IMAGE_SHA,
            production_installation='not_established')))
        started=time.perf_counter()
        completed=subprocess.run(command,cwd=bootstrap,check=False,timeout=250 if args.scope=='accounting' else 550)
        core._write_member(bootstrap,'drain.json',base.canonical_bytes(dict(schema='m03-dataset-native-parent-drain/1',
            bootstrap_exit=completed.returncode,bootstrap_wall_s=time.perf_counter()-started,
            bootstrap_not_scientific_child=True,production_installation='not_established')))
        return completed.returncode
    require(sys.version_info[:3]==(3,12,10) and image_identity()['sha256']==IMAGE_SHA)
    output.mkdir();system=output/'system-temp';system.mkdir()
    api=Path(args.api_packages).resolve(strict=True);scientific=Path(args.scientific_packages).resolve(strict=True)
    require(api.is_dir() and scientific.is_dir())
    # The native scientific ABI is unchanged. The outer dispatcher is stdlib
    # only; it neither loads incompatible wheels nor uses an activation alias.
    # Store activation has already completed in the external output CWD.
    # The existing read-only Alembic fixture intentionally resolves its source
    # migration directory from the product root. Change CWD only AFTER native
    # process initialization; every test allocation still uses external roots.
    code="import sys,runpy,os;sys.path[:0]=[sys.argv.pop(1),sys.argv.pop(1)];root=sys.argv.pop(1);sys.path.insert(0,root);os.chdir(root);runpy.run_module('pytest',run_name='__main__')"
    tests=[PRODUCT/'tests/api/test_magnetic_line_survey_dataset.py']
    if args.scope=='accounting':
        tests.insert(0,PRODUCT/'tests/api/test_magnetic_line_survey_dataset_accounting.py')
        tests.append(PRODUCT/'tests/api/test_magnetic_line_survey_dataset_drain.py')
        tests.extend([PRODUCT/'tests/api/test_magnetic_line_survey_qr_publication_contract.py',
                      PRODUCT/'tests/data/test_magnetic_line_survey_qr_client_contract.py'])
    xml=output/'tests.xml'
    retained=io.external_path(args.retained_root)
    require(sha256(read(retained/'worker/result/result.json')).hexdigest()=='275ae3a46c287f4d44db95608bff0fb674e7f4bf752a47e75c56be768f0d4c76')
    environment=dict(os.environ,GEOPHYSICS_EXISTING_PACKAGE_ROOT=str(scientific),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
        PYTHONDONTWRITEBYTECODE='1',TEMP=str(system),TMP=str(system),TMPDIR=str(system),
        GEOPHYSICS_M03_QR_RETAINED_ROOT=str(retained))
    for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','NUMBA_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):environment[key]='1'
    command=[str(executable),'-B','-S','-c',code,str(scientific),str(api),str(PRODUCT),*[str(item) for item in tests],
        '-k','not real_intake_native_' if args.scope=='accounting' else 'real_intake_native_',
        '-x','-q','-p','no:cacheprovider',f'--junitxml={xml}',f'--basetemp={output}/tests-temp']
    core._write_member(output,'component-seal.json',base.canonical_bytes(dict(schema='m03-owner-dataset-controls-seal/1',
        scope=args.scope,dispatcher_lock=lock,occupancy=occupancy,argv=command,
        field8201='not_verified',production_installation='not_established')))
    completed=subprocess.run(command,cwd=output,env=environment,check=False)
    require(not (PRODUCT/'%SystemDrive%').exists())
    if completed.returncode:return completed.returncode
    suites=ET.parse(xml).getroot().findall('testsuite')
    expected=28 if args.scope=='accounting' else 2
    require(sum(int(item.get('tests','0')) for item in suites)==expected and
        not any(int(item.get(key,'0')) for item in suites for key in ('errors','failures','skipped')))
    core._write_member(output,'component-result.json',base.canonical_bytes(dict(schema='m03-owner-dataset-controls/1',
        scope=args.scope,tests=expected,verdict='component_pass',xml_sha256=sha256(xml.read_bytes()).hexdigest(),
        production_installation='not_established',field8201='not_verified')))
    return 0


if __name__=='__main__':raise SystemExit(main())
