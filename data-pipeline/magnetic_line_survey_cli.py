"""Actual external-storage run, contained verify, immutable export and replay.

Only the fixed sibling worker executes native code. CLI paths are trusted local
file choices, never HTTP fields, expressions, URLs, plugins or module callbacks.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import os
from pathlib import Path
import sys

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_io as io


def _runtime():
    executable=Path(sys.base_prefix)/('python.exe' if sys.platform=='win32' else 'bin/python')
    packages=os.environ.get('GEOPHYSICS_EXISTING_PACKAGE_ROOT')
    if packages is None:
        raise core.SurveyError('custody_mismatch','ingest')
    return executable,Path(packages)


def _inside(root,path,*,directory=True):
    path=io.external_path(path,directory=directory)
    if path!=root and root not in path.parents:
        raise core.SurveyError('invalid_contract','ingest')
    return path


def run_local(csv,metadata,request,auxiliary_root,output,*,data_root,temp_root,run_id,expected_environment=None):
    """Fresh cold original-row intake through Result/fsync; no predecoded values."""
    data=io.local_root(data_root)
    temporary=io.local_root(temp_root,temporary=True)
    csv=_inside(data,csv,directory=False)
    metadata=_inside(data,metadata,directory=False)
    request=_inside(data,request,directory=False)
    auxiliary_root=_inside(data,auxiliary_root)
    output=io.external_path(output)
    # The current Windows controller measures its complete owned directory.
    # Do not spill uncounted temporary/native-cache files into the data root.
    _inside(temporary,output)
    if output.exists():
        raise core.SurveyError('custody_mismatch','export')
    base._type(run_id,'ID','run_id',0)
    output.mkdir()
    plan=dict(schema='m03-local-run-plan/2',csv_path=str(csv),metadata_path=str(metadata),
        request_path=str(request),auxiliary_root=str(auxiliary_root),run_id=run_id,expected_environment=expected_environment)
    path=output/'plan.json'
    core._write_member(output,'plan.json',base.canonical_bytes(plan))
    from magnetic_line_survey_runtime import run_worker
    executable,packages=_runtime()
    lifetime=run_worker(executable,packages,output,path)
    if lifetime['verdict']!='component_pass':
        raise core.SurveyError('cancelled' if lifetime['verdict']=='cancelled' else 'resource_refused','fit')
    result=base.strict_json(base.read_bounded(core._plain_path(output/'result/result.json'),2097152))
    return dict(schema='m03-local-run/1',result_sha256=base.digest(result),policy_epoch=result['policy_epoch'],
        rows=result['inventory']['original_rows'],execution='completed',scientific_verdict=result['verdict']['overall'],
        lifetime=lifetime,host_admission='not_established')


def verify_local(result_root,output,*,temp_root):
    temporary=io.local_root(temp_root,temporary=True)
    result_root=io.external_path(result_root)
    output=_inside(temporary,output)
    if output.exists():
        raise core.SurveyError('custody_mismatch','export')
    output.mkdir()
    core._write_member(output,'plan.json',base.canonical_bytes(dict(schema='m03-result-verification-plan/1',
        result_root=str(result_root))))
    from magnetic_line_survey_runtime import run_worker
    executable,packages=_runtime()
    receipt=run_worker(executable,packages,output,output/'plan.json')
    if receipt['verdict']!='component_pass':
        raise core.SurveyError('resource_refused','replay')
    return base.strict_json(base.read_bounded(core._plain_path(output/'verification.json'),2097152))


def replay_local(bundle,output,*,data_root,temp_root):
    """Actual new cold execution from permitted original bytes, never hash-only."""
    from magnetic_line_survey_export import verify_export
    bundle=io.external_path(bundle)
    manifest=verify_export(bundle,temp_root=temp_root)
    if manifest['result'] is None or manifest['original'] is None or manifest['replay']!='available':
        raise core.SurveyError('metadata_ineligible','replay')
    original=base.strict_json(base.read_bounded(core._plain_path(bundle/'result/result.json'),2097152))
    summary=run_local(bundle/'original.csv',bundle/'result/metadata.json',bundle/'result/request.json',bundle/'result',output,
        data_root=data_root,temp_root=temp_root,run_id=original['run_id'],expected_environment=original['environment'])
    replay=base.strict_json(base.read_bounded(core._plain_path(io.external_path(output)/'result/result.json'),2097152))
    # Wall/CPU/native-counter fields intentionally vary. Compare all scientific
    # values/masks/geometry and request identities, not a fabricated equal timing.
    from magnetic_line_survey_result import _refs
    old={ref['manifest']['name']:ref for ref in _refs(original)}
    new={ref['manifest']['name']:ref for ref in _refs(replay)}
    if set(old)!=set(new):
        raise core.SurveyError('custody_mismatch','replay')
    from magnetic_line_survey_representation import Reader
    first,second=Reader(bundle/'result'),Reader(io.external_path(output)/'result')
    for name,ref in old.items():
        other=new[name]
        if 'array_id' in ref:
            if ref!=other or any(a!=b for a,b in zip(first.cells(ref),second.cells(other),strict=True)):
                raise core.SurveyError('custody_mismatch','replay')
        elif ref['row_schema'] in ('candidate_fit','candidate_fit_v2'):
            for first_row,second_row in zip(first.table(ref),second.table(other),strict=True):
                # Only measured resource clocks/counters may differ. Every
                # candidate, score, numerical diagnostic and gate is replayed.
                for row in (first_row,second_row):
                    row['solve'].pop('timing')
                    row['verdict']['gates'][0]['evidence_sha256']=base.digest(row['solve'])
                if first_row!=second_row:
                    raise core.SurveyError('custody_mismatch','replay')
        elif ref!=other:
            raise core.SurveyError('custody_mismatch','replay')
    if original['geometry']!=replay['geometry'] or original['request']!=replay['request'] or \
       original['verdict']['overall']!=replay['verdict']['overall']:
        raise core.SurveyError('custody_mismatch','replay')
    fits=[deepcopy(value['fit']) for value in (original,replay)]
    for fit in fits:
        fit.pop('candidates')
        fit['solve'].pop('timing')
    if fits[0]!=fits[1] or original['inventory']!=replay['inventory'] or original['channels']!=replay['channels']:
        raise core.SurveyError('custody_mismatch','replay')
    return dict(schema='m03-local-replay/1',original_result_sha256=base.digest(original),
        replay_result_sha256=summary['result_sha256'],scientific_members='pass',
        field_acceptance='unresolved',host_admission='not_established')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    run=commands.add_parser('run')
    for name in ('csv','metadata','request','auxiliary-root','data-root','temp-root','output-root','run-id'):
        run.add_argument('--'+name,required=name not in ('data-root','temp-root'))
    verify=commands.add_parser('verify')
    verify.add_argument('--result-root',required=True)
    verify.add_argument('--output-root',required=True)
    verify.add_argument('--temp-root')
    export=commands.add_parser('export')
    export.add_argument('--result-root',required=True)
    export.add_argument('--destination',required=True)
    export.add_argument('--scope',choices=('private','public'),required=True)
    export.add_argument('--original-csv')
    export.add_argument('--temp-root')
    replay=commands.add_parser('replay')
    replay.add_argument('--bundle-root',required=True)
    replay.add_argument('--output-root',required=True)
    replay.add_argument('--data-root')
    replay.add_argument('--temp-root')
    args=parser.parse_args(argv)
    try:
        if args.command=='run':
            result=run_local(args.csv,args.metadata,args.request,args.auxiliary_root,args.output_root,
                data_root=args.data_root,temp_root=args.temp_root,run_id=args.run_id)
        elif args.command=='verify':
            result=verify_local(args.result_root,args.output_root,temp_root=args.temp_root)
        elif args.command=='export':
            from magnetic_line_survey_export import export_result
            result=export_result(args.result_root,args.destination,scope=args.scope,
                temp_root=io.local_root(args.temp_root,temporary=True),original_csv=args.original_csv)
        else:
            result=replay_local(args.bundle_root,args.output_root,data_root=args.data_root,
                temp_root=io.local_root(args.temp_root,temporary=True))
        print(base.canonical_bytes(result).decode('ascii'))
        return 0
    except core.SurveyError as error:
        print(base.canonical_bytes(error.error).decode('ascii'))
        return 2
    except (OSError,ValueError,TypeError,KeyError):
        print(base.canonical_bytes(core.SurveyError('io_failed','export').error).decode('ascii'))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
