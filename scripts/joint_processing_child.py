"""One fixed supplied-joint solve/replay/instrument child; no uploaded code."""
from pathlib import Path
import argparse
import hashlib
import os
import sys
import time

# Only stdlib bootstrap before closed source/runtime/input verification.
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import joint_execution as execution


def run(control_path, expected):
    execution.sha(expected)
    control,raw=execution.read_json(execution.ordinary(control_path,external=True))
    execution.require(execution.digest(raw)==expected,'joint_control_changed')
    context,context_raw=execution.read_json(control['context_path'])
    python,site=execution.validate_context(context)
    execution.require(sys.flags.no_site and sys.dont_write_bytecode,'joint_isolated_startup')
    execution.require(Path(sys.executable)==python and sys.version_info[:3]==(3,12,10) and sys.platform=='win32',
                      'joint_registered_runtime_epoch')
    data,stage,scratch=execution.validate_control(control,context)
    execution.require(not (stage/'receipt.json').exists(),'joint_exclusive_receipt')
    os.environ.update(TEMP=str(scratch),TMP=str(scratch),TMPDIR=str(scratch),
        NUMBA_CACHE_DIR=str(scratch/'numba'),MPLCONFIGDIR=str(scratch/'mpl'))
    for variable in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        execution.require(os.environ.get(variable)=='1','joint_registered_single_threads')
    sys.path.insert(0,str(site));sys.path.insert(0,str(ROOT/'data-pipeline'))
    # Torch's Windows native dependency initialization is required by the reviewed
    # installed SimPEG tree. It is never a trained model or uploaded dependency.
    import torch
    import joint_survey_workflow as workflow
    import joint_survey_instrument as instrument
    from joint_survey_optimizer import reviewed_source_inventory
    inventory=reviewed_source_inventory()
    loaded_before=execution.loaded_inventory(site)
    phases={};state='failed';reason='joint_child_failed'
    original=stage/'original';output=stage/'export'
    def checkpoint():
        execution.require(time.monotonic()<control['deadline'],'joint_same_job_deadline')
        execution.require(context['source_hashes']==execution.source_inventory(),'joint_product_source_changed')
        current,raw=execution.read_json(control['context_path'])
        execution.require(current==context and execution.digest(raw)==control['context_sha256'],'joint_selected_context_changed')
    args=dict(data_root=str(data),development=str(stage/'inputs'/'development'),
        sealed=str(stage/'inputs'/'sealed'),scratch=str(scratch))
    try:
        checkpoint()
        phases['solve']=workflow.solve_joint_workflow(**args,output=str(original))
        checkpoint()
        if phases['solve']['status']!='completed':
            reason=phases['solve'].get('reason','joint_native_failure')
        else:
            execution.require(phases['solve']['inverse_completed'] is True,'joint_actual_inverse_required')
            phases['original_replay']=workflow.validate_joint_workflow(**args,output=str(original))
            checkpoint()
            phases['instrument_export']=instrument.state_instrument_workflow(**args,original=str(original),output=str(output))
            checkpoint()
            phases['instrument_replay']=instrument.state_instrument_workflow(**args,original=str(original),output=str(output),validate=True)
            checkpoint()
            execution.require(phases['instrument_export']['instrument_manifest_sha256']==
                phases['instrument_replay']['instrument_manifest_sha256'],'joint_instrument_replay_changed')
            state='execution_completed';reason=None
    except (ValueError,RuntimeError,OSError,TypeError,ImportError) as error:
        reason='joint_'+type(error).__name__
    loaded_after=execution.loaded_inventory(site)
    execution.require(all(loaded_after.get(k)==v for k,v in loaded_before.items()),'joint_loaded_source_changed')
    checkpoint()
    receipt={'schema':'geophysics.joint-fixed-execution/v1','state':state,'reason':reason,
        'job_id':control['job_id'],'owner_id':control['owner_id'],'project_id':control['project_id'],
        'dataset_id':control['dataset_id'],'dataset_sha256':control['dataset_sha256'],
        'control_sha256':expected,'context_sha256':execution.digest(context_raw),
        'product_source_hashes':context['source_hashes'],'native_source_inventory':inventory,
        'loaded_module_hashes':loaded_after,'loaded_transitive_closure_verified':False,
        'phases':phases,'scientific_acceptance_verified':False,'host_admission':False,'public_activation':False}
    # Large loaded provenance is its own closed, exact-hash member. No truncation.
    closure=execution.canonical(receipt.pop('loaded_module_hashes'))
    execution.require(len(closure)<=256*1024,'joint_loaded_manifest_cap')
    with (stage/'loaded-modules.json').open('xb') as stream:
        stream.write(closure);stream.flush();os.fsync(stream.fileno())
    receipt['loaded_module_sha256']=execution.digest(closure)
    execution.write_json(stage/'receipt.json',receipt)
    return 0 if state=='execution_completed' else 1


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--control',required=True);parser.add_argument('--sha256',required=True)
    args=parser.parse_args()
    try: return run(args.control,args.sha256)
    except (ValueError,TypeError,RuntimeError,OSError,ImportError,KeyError):
        # Literal fixed failure, full native stderr/stage retained by supervisor.
        print('joint_fixed_child_refused',file=sys.stderr);return 1


if __name__=='__main__': raise SystemExit(main())
