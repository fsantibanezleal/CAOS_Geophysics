"""All24 actual immutable workflow supplements. No refit or precision upgrade."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'data-pipeline'))

import joint_survey_instrument as instrument
import joint_survey_intake as intake
import joint_survey_files as files
from joint_survey_serialization import _external,local_joint_data_root


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--data-root');parser.add_argument('--matrix-root',required=True)
    parser.add_argument('--output-root',required=True);parser.add_argument('--scratch-root',required=True)
    args=parser.parse_args();root=local_joint_data_root(args.data_root)
    matrix=_external(args.matrix_root,existing=True);output=_external(args.output_root)
    scratch=_external(args.scratch_root,existing=True)
    for path in (matrix,output):
        if path==root or not path.is_relative_to(root): raise ValueError('matrix: configured external data root required')
    if output.exists(): raise FileExistsError('matrix: exclusive supplemental output')
    if any(a==b or a.is_relative_to(b) or b.is_relative_to(a) for a,b in ((matrix,output),(matrix,scratch),(output,scratch))):
        raise ValueError('matrix: disjoint external paths')
    matrix_sha=intake._file_sha(matrix/'matrix.json');sources=instrument.source_inventory()
    output.mkdir(mode=0o700);records=[]
    for index in range(24):
        name=f'joint-control-{index:02d}';case=matrix/name;destination=output/name
        arguments={'data_root':str(root),'development':str(case/'development'),'sealed':str(case/'sealed'),
            'original':str(case/'output'),'output':str(destination),'scratch':str(scratch)}
        try:
            exported=instrument.state_instrument_workflow(**arguments)
            verified=instrument.state_instrument_workflow(**arguments,validate=True)
            record={'case_id':name,'completed':True,'export':exported,'validation':verified}
        except (ValueError,TypeError,RuntimeError,OSError) as exc:
            record={'case_id':name,'completed':False,'error_type':type(exc).__name__}
        files.metadata_budget(record)
        with (output/(name+'.json')).open('xb') as stream: stream.write(files._content(record))
        records.append({'case_id':name,'completed':record['completed'],
            'record_sha256':intake._file_sha(output/(name+'.json'))})
        print(json.dumps(records[-1],sort_keys=True),flush=True)
    stable=matrix_sha==intake._file_sha(matrix/'matrix.json') and sources==instrument.source_inventory()
    summary={'schema':'joint-state-instrument-matrix-1','original_matrix_sha256':matrix_sha,
        'exporter_source_inventory':sources,'sources_and_original_matrix_unchanged':stable,
        'cells_attempted':24,'completed_export_and_replay':sum(r['completed'] for r in records),
        'records':records,'refit':False,'original_precision_failures_retained':True,
        'scientific_acceptance_verified':False,'field_eligible':False,'public_activation':False}
    files.metadata_budget(summary)
    with (output/'instrument-matrix.json').open('xb') as stream: stream.write(files._content(summary))
    print(json.dumps(summary,sort_keys=True),flush=True)
    return 0 if stable and all(r['completed'] for r in records) else 1


if __name__=='__main__': raise SystemExit(main())
