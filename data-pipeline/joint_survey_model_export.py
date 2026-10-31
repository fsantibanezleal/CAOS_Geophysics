"""Physical-unit model/geometry export, independently replayed from frozen q."""
import numpy as np

import joint_survey_evaluation as evaluation
import joint_survey_files as files
import joint_survey_plan as planner


def physical_model_record(problem,frozen):
    evaluation.verify_frozen_model(frozen,problem)
    model=frozen['q']*problem.scales;n=problem.n;p=problem.plan
    arrays={'density_kg_m3':model[:n],'susceptibility_si':model[n:],
        'active_cell_centres_m':problem.geometry['active_cell_centres_m'],
        'active_cell_bounds_m':problem.geometry['active_cell_bounds_m'],
        'active_cell_volumes_m3':problem.geometry['active_cell_volumes_m3'],
        'active_full_indices':np.flatnonzero(p['mesh']['active']).astype(np.int64),
        'mesh_origin_m':p['mesh']['origin_m'],'mesh_hx_m':p['mesh']['hx_m'],
        'mesh_hy_m':p['mesh']['hy_m'],'mesh_hz_m':p['mesh']['hz_m']}
    payload={'schema':'joint-survey-physical-model-1','plan_sha256':p['plan_sha256'],
        'development_sha256':problem.development_sha256,'frozen_sha256':frozen['frozen_sha256'],
        'origin':frozen['origin'],'selection_sha256':frozen['selection_sha256'],
        'frame':p['frame'],'cell_order':'x-fast','density_unit':'kg_m3','susceptibility_unit':'si',
        'length_unit':'m','volume_unit':'m3','density_scale':p['prior']['density']['scale'],
        'susceptibility_scale':p['prior']['susceptibility']['scale'],
        'inducing_field':p['magnetic']['inducing_field'],'physical_epochs':dict(evaluation.EPOCHS),
        'field_eligible':False,'recovery_verified':False,'global_optimum_verified':False,
        'rights_verified':False,'public_redistribution':False,'inverse_execution_asserted_by_this_model':False}
    return {'payload':payload,'arrays':planner._snapshot(arrays)}


def write_physical_model(directory,problem,frozen):
    record=physical_model_record(problem,frozen)
    return files.write_arrays(directory,'model.json','joint-survey-physical-model-file-1',record['payload'],record['arrays'])


def validate_physical_model(directory,problem,frozen):
    expected=physical_model_record(problem,frozen)
    specs={k:(v.dtype.str,v.shape) for k,v in expected['arrays'].items()}
    def validate(value):
        # JSON axes are lists; canonical digest preserves the identical order.
        if planner._digest(value)!=planner._digest(expected['payload']): raise ValueError('physical model: metadata drift')
    payload,arrays,bindings=files.read_arrays(directory,'model.json','joint-survey-physical-model-file-1',specs,validate)
    if planner._digest({'payload':payload,'arrays':arrays})!=planner._digest(expected):
        raise ValueError('physical model: actual units/models/geometry drift')
    return {'physical_model_verified':True,'model_manifest_sha256':bindings['manifest_sha256'],'field_eligible':False}
