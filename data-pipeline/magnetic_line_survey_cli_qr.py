"""Actual external-storage run, contained verify, immutable export and replay.

Only the fixed sibling worker executes native code. CLI paths are trusted local
file choices, never HTTP fields, expressions, URLs, plugins or module callbacks.
"""
from __future__ import annotations

import argparse
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


def run_local(csv,metadata,request,auxiliary_root,output,*,data_root,temp_root,run_id,expected_environment=None,prerequisite,capacity_root):
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
    prerequisite=io.external_path(prerequisite,directory=False)
    capacity_root=io.external_path(capacity_root)
    plan=dict(schema='m03-local-qr-run-plan/1',csv_path=str(csv),metadata_path=str(metadata),
        request_path=str(request),auxiliary_root=str(auxiliary_root),run_id=run_id,expected_environment=expected_environment,
        prerequisite=str(prerequisite),capacity_root=str(capacity_root))
    path=output/'plan.json'
    core._write_member(output,'plan.json',base.canonical_bytes(plan))
    from magnetic_line_survey_runtime import run_worker
    executable,packages=_runtime()
    lifetime=run_worker(executable,packages,output,path)
    if lifetime['verdict']!='component_pass':
        raise core.SurveyError('cancelled' if lifetime['verdict']=='cancelled' else 'resource_refused','fit')
    result=base.strict_json(base.read_bounded(core._plain_path(output/'result/result.json'),2097152))
    return dict(schema='m03-local-qr-run/1',result_sha256=base.digest(result),policy_epoch=result['policy_epoch'],
        rows=result['inventory']['original_rows'],execution='completed',scientific_verdict=result['verdict']['overall'],
        lifetime=lifetime,host_admission='not_established')


def verify_local(result_root,output,*,temp_root):
    temporary=io.local_root(temp_root,temporary=True)
    result_root=io.external_path(result_root)
    output=_inside(temporary,output)
    if output.exists():
        raise core.SurveyError('custody_mismatch','export')
    output.mkdir()
    core._write_member(output,'plan.json',base.canonical_bytes(dict(schema='m03-qr-result-verification-plan/1',
        result_root=str(result_root))))
    from magnetic_line_survey_runtime import run_worker
    executable,packages=_runtime()
    receipt=run_worker(executable,packages,output,output/'plan.json')
    if receipt['verdict']!='component_pass':
        raise core.SurveyError('resource_refused','replay')
    return base.strict_json(base.read_bounded(core._plain_path(output/'verification.json'),2097152))


def replay_local(bundle,output,*,data_root,temp_root,prerequisite):
    """Actual new cold execution from permitted original bytes, never hash-only."""
    from magnetic_line_survey_export_qr import verify_export
    bundle=io.external_path(bundle)
    manifest=verify_export(bundle,temp_root=temp_root)
    if manifest['result'] is None or manifest['original'] is None or manifest['replay']!='available':
        raise core.SurveyError('metadata_ineligible','replay')
    original=base.strict_json(base.read_bounded(core._plain_path(bundle/'result/result.json'),2097152))
    temporary=io.local_root(temp_root,temporary=True)
    capacity_root=_inside(temporary,str(output)+'-capacity')
    if capacity_root.exists():raise core.SurveyError('custody_mismatch','replay')
    capacity_root.mkdir()
    core._write_member(capacity_root,'geometry-seal.json',base.canonical_bytes(original['geometry']))
    proof=base.read_bounded(core._plain_path(bundle/'result/resolution-capacity-proof.json'),4194304)
    core._write_member(capacity_root,'resolution-capacity-proof.json',proof)
    summary=run_local(bundle/'original.csv',bundle/'result/metadata.json',bundle/'result/request.json',bundle/'result',output,
        data_root=data_root,temp_root=temp_root,run_id=original['run_id'],expected_environment=original['environment'],prerequisite=prerequisite,capacity_root=capacity_root)
    replay=base.strict_json(base.read_bounded(core._plain_path(io.external_path(output)/'result/result.json'),2097152))
    # QR receipts have no fitted timing/status surrogate; one-thread immutable
    # scientific reproduction must reproduce the complete Result byte identity.
    if original!=replay:
        raise core.SurveyError('custody_mismatch','replay')
    return dict(schema='m03-local-qr-replay/1',original_result_sha256=base.digest(original),
        replay_result_sha256=summary['result_sha256'],scientific_members='pass',
        field_acceptance='unresolved',host_admission='not_established')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    run=commands.add_parser('run')
    for name in ('csv','metadata','request','auxiliary-root','data-root','temp-root','output-root','run-id','prerequisite','capacity-root'):
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
    replay.add_argument('--prerequisite',required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='run':
            result=run_local(args.csv,args.metadata,args.request,args.auxiliary_root,args.output_root,
                data_root=args.data_root,temp_root=args.temp_root,run_id=args.run_id,
                prerequisite=args.prerequisite,capacity_root=args.capacity_root)
        elif args.command=='verify':
            result=verify_local(args.result_root,args.output_root,temp_root=args.temp_root)
        elif args.command=='export':
            from magnetic_line_survey_export_qr import export_result
            result=export_result(args.result_root,args.destination,scope=args.scope,
                temp_root=io.local_root(args.temp_root,temporary=True),original_csv=args.original_csv)
        else:
            result=replay_local(args.bundle_root,args.output_root,data_root=args.data_root,
                temp_root=io.local_root(args.temp_root,temporary=True),prerequisite=args.prerequisite)
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
