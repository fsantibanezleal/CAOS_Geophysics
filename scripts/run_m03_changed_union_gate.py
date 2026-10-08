"""Run M01's UNCHANGED copied-chain assertions with one changed literal pin.

No peer source edits, skipped negatives, live SQL, mounted routes or aliases.
Existing M01/M11 predecessor pins/guards remain those of the original harness.
"""
import argparse
from hashlib import sha256
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--m01-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--commit',required=True)
    args=parser.parse_args()
    product=Path(__file__).resolve().parents[1]
    source='app/magnetic_line_survey_migrations/0007_magnetic_line_artifacts.py'
    if not args.output.is_absolute() or args.output.exists() or not args.m01_root.is_absolute():raise ValueError('exclusive_external_output_required')
    if any((p/'.git').exists() for p in (args.output,*args.output.parents)):raise ValueError('external_output_required')
    # Source closes before target opening; peer assertions remain literal.
    body=subprocess.check_output(['git','-C',str(product),'show',args.commit+':'+source])
    peer_body=subprocess.check_output(['git','-C',str(args.m01_root),'show',args.commit+':'+source])
    if body!=peer_body:raise ValueError('source_pin_mismatch')
    test=args.m01_root/'tests/api/test_physical_union_schema.py'
    before=sha256(test.read_bytes()).hexdigest()
    sys.path.insert(0,str(args.m01_root))
    from tests.ops import physical_union_fixture as fixture
    old=fixture.M03
    del fixture.PINS[(old,source)]
    fixture.M03=args.commit
    fixture.PINS[(args.commit,source)]=sha256(body).hexdigest()
    args.output.mkdir()
    import pytest
    code=pytest.main([str(test),'-q','-x','-s','-p','no:cacheprovider',
        '--basetemp='+str(args.output/'copied-fixtures'),'--junitxml='+str(args.output/'copied-chain.xml')])
    if sha256(test.read_bytes()).hexdigest()!=before:raise ValueError('peer_assertions_changed')
    print('UNCHANGED_M01_TEST_SHA256='+before)
    print('CHANGED_M03_COMMIT='+args.commit)
    print('CHANGED_M03_DDL_SOURCE_SHA256='+sha256(body).hexdigest())
    return code


if __name__=='__main__':raise SystemExit(main())
