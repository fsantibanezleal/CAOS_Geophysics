"""Strict private workflow I/O; solve has no sealed read before durable freeze."""
import json

import joint_survey_compiled as compiled
import joint_survey_evaluation as evaluation
import joint_survey_files as files
import joint_survey_intake as intake
import joint_survey_plan as planner
import joint_survey_resources as resources
from joint_survey_model_export import write_physical_model,validate_physical_model
from joint_survey_serialization import _external,local_joint_data_root


def _under(root,path,*,existing):
    value=_external(path,existing=existing)
    if value==root or not value.is_relative_to(root): raise ValueError('workflow: path must be beneath configured external data root')
    return value


def _write_json(path,value):
    files.metadata_budget(value)
    content=files._content(value)
    with path.open('xb') as stream: stream.write(content)


def _admit_paths(data_root,development,sealed,output,scratch,*,frozen=None,existing_output=False):
    root=local_joint_data_root(data_root)
    values={'development':_under(root,development,existing=True),'sealed':_under(root,sealed,existing=True),
        'output':_under(root,output,existing=existing_output),'scratch':_external(scratch,existing=True)}
    if frozen is not None: values['frozen']=_under(root,frozen,existing=True)
    for key,left in values.items():
        for other,right in values.items():
            if key>=other: continue
            if left==right or left.is_relative_to(right) or right.is_relative_to(left):
                raise ValueError('workflow: disjoint input/output/scratch directories required')
    if not existing_output and values['output'].exists(): raise FileExistsError('workflow: exclusive output required')
    intake._ordinary(values['output'].parent,directory=True)
    return values


def _compile(directory):
    admitted=intake.load_joint_development(str(directory))
    problem=compiled.compile_joint_development({'schema':'joint-survey-compile-request-1',
        'survey_request':admitted['survey_request'],'development':admitted['development']})
    return admitted,problem


def _finish(root,budget,mode,admitted,frozen,*,inverse_completed,calibration_sha256=None):
    size=resources.scratch_bytes(root)
    if size>planner.MAX_EXPORT_BYTES: raise RuntimeError('workflow_export_cap')
    receipt=budget.receipt(workflow_completed=True)
    status={'schema':'joint-survey-workflow-receipt-1','mode':mode,'status':'completed',
        'plan_sha256':admitted['plan']['plan_sha256'],'frozen_sha256':frozen['frozen_sha256'],
        'calibration_sha256':calibration_sha256,'input_bindings':admitted['bindings'],
        'source_diagnostics':admitted['diagnostics'],'inverse_completed':inverse_completed,
        'sealed_evaluation_completed':True,'field_eligible':False,'public_activation':False,
        'private_export_bytes_before_receipt':size,'resources':receipt}
    _write_json(root/'workflow.json',status)
    if resources.scratch_bytes(root)>planner.MAX_EXPORT_BYTES: raise RuntimeError('workflow_export_cap')
    budget.checkpoint()
    return status


def _resource_receipt(value):
    planner._keys(value,('schema','elapsed_seconds','peak_sampled_rss_bytes','peak_sampled_scratch_bytes','samples',
        'sampling_seconds','deadline_seconds','rss_limit_bytes','scratch_limit_bytes','workflow_completed',
        'complete_workflow_resource_pass','os_reservation','hard_realtime_interruption'),'resource receipt')
    planner._enum(value['schema'],('joint-survey-resource-receipt-1',),'resource.schema')
    planner._float(value['elapsed_seconds'],0.,resources.MAX_SECONDS,'resource elapsed')
    if any(type(value[k]) is not int or not lower<=value[k]<=upper for k,lower,upper in (
            ('peak_sampled_rss_bytes',1,resources.MAX_RSS),('peak_sampled_scratch_bytes',0,resources.MAX_SCRATCH),('samples',2,2**63-1))):
        raise ValueError('workflow: measured resource counters/caps drift')
    for key,expected in (('sampling_seconds',.05),('deadline_seconds',resources.MAX_SECONDS),
            ('rss_limit_bytes',resources.MAX_RSS),('scratch_limit_bytes',resources.MAX_SCRATCH),
            ('workflow_completed',True),('complete_workflow_resource_pass',True),('os_reservation',False),('hard_realtime_interruption',False)):
        if type(value[key]) is not type(expected) or value[key]!=expected: raise ValueError('workflow: resource contract drift')


def evaluate_joint_workflow(*,data_root,development,sealed,frozen,output,scratch):
    paths=_admit_paths(data_root,development,sealed,output,scratch,frozen=frozen)
    with resources.JointResourceBudget(str(paths['scratch'])) as budget:
        admitted,problem=_compile(paths['development']);budget.checkpoint()
        model=evaluation.load_frozen_model(str(paths['frozen']),problem)
        # An externally labelled optimized model is not proof of execution.
        # Evaluation mode always has inverse_completed=false.
        paths['output'].mkdir(mode=0o700)
        evaluation.write_frozen_model(str(paths['output']/'frozen'),model,problem)
        values=evaluation.load_joint_sealed(str(paths['sealed']),problem,model,admitted['sealed_manifest'])
        result=evaluation.evaluate_frozen_joint(problem,model,values);budget.checkpoint()
        evaluation.write_joint_result(str(paths['output']/'result'),result)
        evaluation.validate_joint_result(str(paths['output']/'result'),problem,model,values)
        write_physical_model(str(paths['output']/'models'),problem,model)
        validate_physical_model(str(paths['output']/'models'),problem,model)
        return _finish(paths['output'],budget,'evaluate',admitted,model,inverse_completed=False)


def solve_joint_workflow(*,data_root,development,sealed,output,scratch):
    # This command uses only the reviewed product optimizer, never an input
    # factory/selector/import path or test oracle.
    from joint_survey_optimizer import calibrate_joint_development,JointCalibrationFailure
    from joint_survey_calibration_io import write_joint_calibration
    paths=_admit_paths(data_root,development,sealed,output,scratch)
    with resources.JointResourceBudget(str(paths['scratch'])) as budget:
        admitted,problem=_compile(paths['development']);budget.checkpoint()
        try: ledger=calibrate_joint_development(problem,budget)
        except JointCalibrationFailure as failure:
            return _failed_solve(paths,budget,problem,failure,False)
        paths['output'].mkdir(mode=0o700)
        progress={'sealed_read_started':False}
        try:
            write_joint_calibration(str(paths['output']/'calibration'),ledger,problem,budget)
            if ledger['status']!='selected':
                status={'schema':'joint-survey-workflow-receipt-1','mode':'solve','status':'failed',
                    'reason':ledger['reason'],'calibration_sha256':ledger['calibration_sha256'],
                    'inverse_completed':False,'sealed_evaluation_completed':False,'public_activation':False,
                    'resources':budget.receipt(workflow_completed=False)}
                _write_json(paths['output']/'workflow.json',status)
                return status
            return _complete_solve(paths,budget,admitted,problem,ledger,ledger['selection'],progress)
        except RuntimeError:
            # A later replay/resource failure retains the genuine driver ledger,
            # including all accepted states, without claiming completed export.
            failure=JointCalibrationFailure(budget.failure or 'workflow_scientific_replay_failure',None)
            failure.verified_candidates=ledger['candidates'];failure.source_inventory=ledger['source_inventory']
            failure.optimizer_binding=ledger['optimizer_binding']
            return _failed_solve(paths,budget,problem,failure,progress['sealed_read_started'])


def _failed_solve(paths,budget,problem,failure,sealed_read_started):
    from joint_survey_calibration_io import write_aborted_calibration
    if not paths['output'].exists(): paths['output'].mkdir(mode=0o700)
    write_aborted_calibration(str(paths['output']/'aborted'),failure,problem,
        frozen_selection_created=(paths['output']/'frozen'/'frozen.json').is_file(),
        sealed_values_read_started=sealed_read_started)
    status={'schema':'joint-survey-workflow-failure-1','mode':'solve','status':'failed','reason':failure.reason,
        'inverse_completed':False,'sealed_evaluation_completed':False,'public_activation':False,
        'accepted_attempts_retained':True,'resources':budget.failure_receipt()}
    _write_json(paths['output']/'failure.json',status)
    return status


def _complete_solve(paths,budget,admitted,problem,ledger,selected,progress):
        from joint_survey_calibration_io import verify_joint_calibration
        model=evaluation.freeze_joint_model(problem,selected['q'],selected['weights'],origin='optimized_selection',
            selection_sha256=ledger['calibration_sha256'])
        evaluation.write_frozen_model(str(paths['output']/'frozen'),model,problem)
        verify_joint_calibration(ledger,problem,budget,frozen=model)
        # NO sealed data byte has been opened until the durable freeze above.
        progress['sealed_read_started']=True
        values=evaluation.load_joint_sealed(str(paths['sealed']),problem,model,admitted['sealed_manifest'])
        result=evaluation.evaluate_frozen_joint(problem,model,values);budget.checkpoint()
        evaluation.write_joint_result(str(paths['output']/'result'),result)
        evaluation.validate_joint_result(str(paths['output']/'result'),problem,model,values)
        write_physical_model(str(paths['output']/'models'),problem,model)
        validate_physical_model(str(paths['output']/'models'),problem,model)
        return _finish(paths['output'],budget,'solve',admitted,model,inverse_completed=True,
            calibration_sha256=ledger['calibration_sha256'])


def validate_joint_workflow(*,data_root,development,sealed,output,scratch):
    paths=_admit_paths(data_root,development,sealed,output,scratch,existing_output=True)
    with resources.JointResourceBudget(str(paths['scratch'])) as budget:
        admitted,problem=_compile(paths['development'])
        status=intake._parse_json(intake._read_bounded(paths['output']/'workflow.json',planner.MAX_METADATA_BYTES))
        planner._keys(status,('schema','mode','status','plan_sha256','frozen_sha256','calibration_sha256','input_bindings',
            'source_diagnostics','inverse_completed','sealed_evaluation_completed','field_eligible','public_activation',
            'private_export_bytes_before_receipt','resources'),'workflow receipt')
        planner._enum(status['schema'],('joint-survey-workflow-receipt-1',),'workflow.schema')
        planner._enum(status['mode'],('solve','evaluate'),'workflow.mode');planner._enum(status['status'],('completed',),'workflow.status')
        _resource_receipt(status['resources'])
        expected={'workflow.json','frozen','result','models'}|({'calibration'} if status['mode']=='solve' else set())
        if set(p.name for p in paths['output'].iterdir())!=expected: raise ValueError('workflow: exact artifact inventory')
        if status['input_bindings']!=admitted['bindings'] or status['source_diagnostics']!=admitted['diagnostics']:
            raise ValueError('workflow: original development receipts drift')
        model=evaluation.load_frozen_model(str(paths['output']/'frozen'),problem)
        if status['plan_sha256']!=problem.plan['plan_sha256'] or status['frozen_sha256']!=model['frozen_sha256']:
            raise ValueError('workflow: frozen identity drift')
        if any(type(status[key]) is not bool or status[key] is not expected for key,expected in (
                ('inverse_completed',status['mode']=='solve'),('sealed_evaluation_completed',True),('field_eligible',False),('public_activation',False))):
            raise ValueError('workflow: claim flags drift')
        if status['mode']=='solve':
            from joint_survey_calibration_io import load_joint_calibration,verify_joint_calibration
            ledger=load_joint_calibration(str(paths['output']/'calibration'),problem,budget)
            verify_joint_calibration(ledger,problem,budget,frozen=model)
            if status['calibration_sha256']!=ledger['calibration_sha256']: raise ValueError('workflow: calibration identity drift')
        elif status['calibration_sha256'] is not None: raise ValueError('workflow: evaluate cannot claim actual calibration')
        values=evaluation.load_joint_sealed(str(paths['sealed']),problem,model,admitted['sealed_manifest'])
        verified=evaluation.validate_joint_result(str(paths['output']/'result'),problem,model,values)
        physical=validate_physical_model(str(paths['output']/'models'),problem,model)
        size=resources.scratch_bytes(paths['output'])
        receipt_size=intake._ordinary(paths['output']/'workflow.json').st_size
        if type(status['private_export_bytes_before_receipt']) is not int or status['private_export_bytes_before_receipt']!=size-receipt_size:
            raise ValueError('workflow: actual export byte receipt drift')
        if size>planner.MAX_EXPORT_BYTES: raise ValueError('workflow: actual export cap')
        return {'schema':'joint-survey-validation-receipt-1','validated':True,'mode':status['mode'],
            'inverse_completed':status['mode']=='solve','field_eligible':False,'result':verified,
            'physical_models':physical,
            'verification_resources':budget.receipt(workflow_completed=True)}


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description='Private supplied gravity/magnetic physical processing',allow_abbrev=False)
    commands=parser.add_subparsers(dest='command',required=True)
    for command in ('solve','evaluate','validate'):
        sub=commands.add_parser(command,allow_abbrev=False)
        sub.add_argument('--data-root');sub.add_argument('--development',required=True)
        sub.add_argument('--sealed',required=True);sub.add_argument('--output',required=True)
        sub.add_argument('--scratch-root',required=True)
        if command=='evaluate': sub.add_argument('--frozen',required=True)
    args=vars(parser.parse_args(argv));command=args.pop('command');args['scratch']=args.pop('scratch_root')
    try:
        method={'solve':solve_joint_workflow,'evaluate':evaluate_joint_workflow,'validate':validate_joint_workflow}[command]
        status=method(**args)
        print(json.dumps(status,sort_keys=True,allow_nan=False))
        return 0 if status.get('status','completed')=='completed' else 1
    except (ValueError,TypeError,RuntimeError,OSError,ImportError) as exc:
        # Local operator stderr is not a web response or exported device path.
        print(json.dumps({'schema':'joint-survey-cli-error-1','status':'failed','error_type':type(exc).__name__,
            'inverse_completed':False,'public_activation':False},sort_keys=True))
        return 1


if __name__=='__main__': raise SystemExit(main())
