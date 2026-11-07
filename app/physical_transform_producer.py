"""Exact saved terminal-transform bindings. Pure stdlib, never numerical replay.

The caller must independently audit the supplied complete correction ancestry.
This reader proves structure/digest/SQL consistency, not scientific accuracy or
runtime admission. In particular non-pass height precision remains non-pass.
"""

import re

from app.physical_contract import TRANSFORM, J, M, byte_sha, canonical, digest, fields, integer, require, sha, text, uuid
from app.physical_producer import PARENT_KEYS, REQUEST_KEYS, RESULT_KEYS, PRODUCTION_KEYS, PINS, _child, _decode, _same
from app.physical_wire import DATASET_KEYS, number, scientific_digest, source_structure

PINS_TRANSFORM = {**PINS, 'verde':'1.9.0', 'scikit-learn':'1.9.1', 'matplotlib':'3.10.8'}
NULL_ADAPTER = ('adapter_result_sha256','adapter_receipt_sha256','core_result_sha256',
                'submitted_config_sha256','normalized_config_sha256','adapter_receipt_bytes')
OUTPUT_KEYS = 'schema_version original_correction_result geometry config model selection split stations evaluation axes grids condition nonuniqueness uncertainty resolution provenance'


def _vector(value, count, *, low=float('-inf'), nullable=False, flags=False):
    require(type(value) is list and len(value)==count, 'transform_vector_shape')
    for item in value:
        if flags:
            require(type(item) is bool, 'transform_boolean')
        elif item is None:
            require(nullable, 'transform_unexpected_null')
        else:
            number(item, low)


def _indices(value, count):
    require(type(value) is list and len(value)<=count, 'transform_index_shape')
    for item in value:
        integer(item, 0, count-1)
    require(len(set(value))==len(value), 'transform_duplicate_index')
    return set(value)


def _metrics(value, count):
    fields(value, 'covered_count unsupported_count rmse_mgal normalized_rmse signed_mean_mgal')
    integer(value['covered_count'], 0, count)
    integer(value['unsupported_count'], 0, count)
    require(value['covered_count']+value['unsupported_count']==count, 'transform_metric_count')
    for key in ('rmse_mgal','normalized_rmse','signed_mean_mgal'):
        item=value[key]
        require((item is None)==(value['covered_count']==0), 'transform_metric_null')
        if item is not None:
            number(item, float('-inf') if key=='signed_mean_mgal' else 0)


def _geometry_config(science, parent):
    geometry,config=science['geometry'],science['config']
    fields(geometry, 'station_ids easting_m northing_m upward_m coordinate_unit axis_order vertical_reference metric_crs mapping_citation component data_unit source_free_citation geometry_error_model geometry_error_citation mask mask_reasons')
    ids=[s['station_id'] for s in parent['payload']['correction_result']['dataset']['stations']]
    count=len(ids)
    require(20<=count<=400 and geometry['station_ids']==ids, 'transform_station_order')
    for key, literal in (('coordinate_unit','m'),('axis_order','easting,northing,upward'),
        ('vertical_reference','WGS84_ellipsoid'),('component','g_z_downward'),('data_unit','mGal'),
        ('geometry_error_model','fixed_geometry_conditional')):
        require(geometry[key]==literal, 'transform_geometry_literal')
    for key in ('metric_crs','mapping_citation','source_free_citation','geometry_error_citation'):
        text(geometry[key]); require(bool(geometry[key].strip()), 'transform_geometry_text')
    require(geometry['metric_crs'] not in ('EPSG:4326','EPSG:4267','EPSG:4979'), 'transform_metric_crs')
    for key in ('easting_m','northing_m','upward_m'):
        _vector(geometry[key],count)
    _same(geometry['upward_m'],parent['payload']['correction_result']['qc']['receiver_ellipsoidal_m'])
    _vector(geometry['mask'],count,flags=True)
    require(type(geometry['mask_reasons']) is list and len(geometry['mask_reasons'])==count, 'transform_mask_shape')
    for masked,reason in zip(geometry['mask'],geometry['mask_reasons']):
        if masked:
            text(reason); require(bool(reason.strip()), 'transform_mask_reason')
        else:
            require(reason is None, 'transform_mask_reason')
    required=set('depths_m dampings heights_m region_m grid_spacing_m coverage_radius_m block_shape holdout_fraction seed inner_folds min_validation_coverage max_input_sigma_mgal max_transfer_sigma_mgal max_condition error_model'.split())
    require(type(config) is dict and set(config)==required | (
        {'covariance_mgal2','covariance_citation'} if config.get('error_model')=='supplied_covariance' else set()), 'transform_config_keys')
    require(config['error_model'] in ('independent_stations','supplied_covariance'), 'transform_error_kind')
    for key,low,high in (('depths_m',10,10000),('dampings',1e-8,1e8),
                         ('heights_m',max(geometry['upward_m']),max(geometry['upward_m'])+10000)):
        require(type(config[key]) is list and 1<=len(config[key])<=8, 'transform_candidates')
        for item in config[key]:
            number(item,low,high)
        require(len(set(config[key]))==len(config[key]), 'transform_candidates')
    require(len(config['depths_m'])*len(config['dampings'])<=12, 'transform_candidates')
    _vector(config['region_m'],4)
    w,e,s,n=config['region_m']
    require(w<e and s<n and max(e-w,n-s)<=20000, 'transform_region')
    for key,low,high in (('grid_spacing_m',1,20000),('coverage_radius_m',1,20000),('holdout_fraction',0.1,0.4),
        ('min_validation_coverage',0.1,1),('max_input_sigma_mgal',1e-9,100),('max_transfer_sigma_mgal',1e-9,100),('max_condition',1,1e12)):
        number(config[key],low,high)
    integer(config['seed'],0,2**31-1); integer(config['inner_folds'],2,5)
    require(type(config['block_shape']) is list and len(config['block_shape'])==2, 'transform_block_shape')
    for item in config['block_shape']:
        integer(item,2,20)
    if config['error_model']=='supplied_covariance':
        text(config['covariance_citation']); require(bool(config['covariance_citation'].strip()), 'transform_covariance_citation')
        require(type(config['covariance_mgal2']) is list and len(config['covariance_mgal2'])==count, 'transform_covariance_shape')
        for row in config['covariance_mgal2']:
            _vector(row,count)
    return ids


def _output(payload, science, parent, manifest):
    fields(payload,OUTPUT_KEYS)
    require(payload['schema_version']=='gravity-transform-result-1', 'transform_output_schema')
    for key,source in (('original_correction_result','correction_result'),('geometry','geometry'),('config','config')):
        _same(payload[key],science[source])
    ids=_geometry_config(science,parent); count=len(ids); cfg=science['config']
    split=payload['split']
    fields(split,'train_indices holdout_indices partition block_ids_active active_indices sha256')
    train=_indices(split['train_indices'],count); holdout=_indices(split['holdout_indices'],count)
    active=_indices(split['active_indices'],count)
    require(not train & holdout and train | holdout == active and len(train)>=12 and len(holdout)>=3 and
            active=={i for i,flag in enumerate(science['geometry']['mask']) if not flag}, 'transform_partition')
    require(type(split['partition']) is list and len(split['partition'])==count and
            split['partition']==['train' if i in train else 'holdout' if i in holdout else 'masked' for i in range(count)], 'transform_partition')
    require(type(split['block_ids_active']) is list and len(split['block_ids_active'])==len(active), 'transform_block_ids')
    for item in split['block_ids_active']:
        integer(item,0,399)
    sha(split['sha256'])
    stations=payload['stations']
    fields(stations,'station_ids observed_mgal fit_sigma_mgal predicted_mgal signed_predicted_minus_observed_mgal normalized_residual prediction_covered nearest_training_m')
    require(stations['station_ids']==ids, 'transform_station_order')
    _same(stations['observed_mgal'],[s['value_mgal'] for s in science['correction_result']['dataset']['stations']])
    _vector(stations['fit_sigma_mgal'],count,low=0)
    require(all(x>0 for x in stations['fit_sigma_mgal']), 'transform_positive_sigma')
    _vector(stations['prediction_covered'],count,flags=True)
    _vector(stations['nearest_training_m'],count,low=0)
    for key in ('predicted_mgal','signed_predicted_minus_observed_mgal','normalized_residual'):
        _vector(stations[key],count,nullable=True)
        require(all((value is not None)==flag for value,flag in zip(stations[key],stations['prediction_covered'])), 'transform_prediction_null')
    require(all(not stations['prediction_covered'][i] for i,flag in enumerate(science['geometry']['mask']) if flag), 'transform_mask_prediction')
    axes=payload['axes']; fields(axes,'easting_m northing_m grid_axis_order unit')
    require(axes['grid_axis_order']=='northing,easting' and axes['unit']=='mGal', 'transform_axis_units')
    for key in ('easting_m','northing_m'):
        require(type(axes[key]) is list and 3<=len(axes[key])<=12000, 'transform_axis_size')
        _vector(axes[key],len(axes[key]))
        require(all(a<b for a,b in zip(axes[key],axes[key][1:])), 'transform_axis_order')
    nodes=len(axes['northing_m'])*len(axes['easting_m'])
    require(nodes<=12000, 'transform_grid_size')
    grids=payload['grids']; require(type(grids) is list and len(grids)==len(cfg['heights_m']), 'transform_grid_count')
    precision=[]
    for grid,height in zip(grids,sorted(cfg['heights_m'])):
        fields(grid,'height_m shape predicted_mgal conditional_sigma_mgal covered outside_hull outside_radius nearest_training_m max_conditional_sigma_mgal adjacent_easting_difference_rms_mgal height_precision_passed')
        _same(grid['height_m'],height)
        require(type(grid['shape']) is list and len(grid['shape'])==2, 'transform_grid_shape')
        for item in grid['shape']:
            integer(item,3,12000)
        require(grid['shape']==[len(axes['northing_m']),len(axes['easting_m'])], 'transform_grid_shape')
        for key in ('covered','outside_hull','outside_radius'):
            _vector(grid[key],nodes,flags=True)
        require(grid['covered']==[not a and not b for a,b in zip(grid['outside_hull'],grid['outside_radius'])] and any(grid['covered']), 'transform_grid_coverage')
        _vector(grid['nearest_training_m'],nodes,low=0)
        for key in ('predicted_mgal','conditional_sigma_mgal'):
            _vector(grid[key],nodes,low=0 if key=='conditional_sigma_mgal' else float('-inf'),nullable=True)
            require(all((v is not None)==flag for v,flag in zip(grid[key],grid['covered'])), 'transform_grid_null')
        number(grid['max_conditional_sigma_mgal'],0)
        require(grid['max_conditional_sigma_mgal']==max(v for v in grid['conditional_sigma_mgal'] if v is not None), 'transform_grid_sigma_max')
        if grid['adjacent_easting_difference_rms_mgal'] is not None:
            number(grid['adjacent_easting_difference_rms_mgal'],0)
        require(type(grid['height_precision_passed']) is bool and
                grid['height_precision_passed']==(grid['max_conditional_sigma_mgal']<=cfg['max_transfer_sigma_mgal']), 'transform_height_precision')
        if grid['height_precision_passed']:
            precision.append(height)
    selection=payload['selection']; fields(selection,'depth_m damping height_m status candidates criterion')
    require(selection['status']==('passed' if precision else 'unmet_height_precision') and
            selection['height_m']==(precision[0] if precision else None), 'transform_precision_verdict')
    require(selection['criterion']=='Inner train-block normalized RMSE; height by train-only noise-transfer ceiling', 'transform_selection_criterion')
    candidates=selection['candidates']
    require(type(candidates) is list and len(candidates)==len(cfg['depths_m'])*len(cfg['dampings']), 'transform_candidate_count')
    combinations=[]
    for candidate in candidates:
        require(type(candidate) is dict and set(candidate)==set('depth_m damping status folds cv_normalized_rmse'.split()) |
                ({'reason'} if candidate.get('status')=='failed' else set()), 'transform_candidate_keys')
        require(candidate['status'] in ('passed','failed'), 'transform_candidate_status')
        number(candidate['depth_m']); number(candidate['damping'])
        combinations.append((candidate['depth_m'],candidate['damping']))
        if 'reason' in candidate:
            text(candidate['reason'])
        require(type(candidate['folds']) is list and len(candidate['folds'])<=cfg['inner_folds'], 'transform_fold_count')
        if candidate['status']=='passed':
            require(len(candidate['folds'])==cfg['inner_folds'], 'transform_fold_count')
            number(candidate['cv_normalized_rmse'],0)
        elif candidate['cv_normalized_rmse'] is not None:
            number(candidate['cv_normalized_rmse'],0)
        for fold in candidate['folds']:
            fields(fold,'train_indices validation_indices metrics condition')
            ft=_indices(fold['train_indices'],count); fv=_indices(fold['validation_indices'],count)
            require(not ft & fv and ft | fv == train and len(ft)>=8, 'transform_fold_partition')
            _metrics(fold['metrics'],len(fv)); number(fold['condition'],0,cfg['max_condition'])
    require(combinations==[(d,a) for d in cfg['depths_m'] for a in cfg['dampings']], 'transform_candidate_order')
    passed=[c for c in candidates if c['status']=='passed']
    require(bool(passed), 'transform_selected_candidate')
    chosen=min(passed,key=lambda c:(c['cv_normalized_rmse'],c['depth_m'],c['damping']))
    require((chosen['depth_m'],chosen['damping'])==(selection['depth_m'],selection['damping']), 'transform_selected_candidate')
    folds=[(f['train_indices'],f['validation_indices']) for f in chosen['folds']]
    require(split['sha256']==scientific_digest(dict(train=split['train_indices'],holdout=split['holdout_indices'],folds=folds)), 'transform_split_digest')
    for candidate in candidates:
        require([(f['train_indices'],f['validation_indices']) for f in candidate['folds']]==folds[:len(candidate['folds'])], 'transform_same_folds')
    model=payload['model']; fields(model,'points_m coefficients_mgal_m depth_m damping training_indices interpretation')
    require(model['training_indices']==split['train_indices'] and model['depth_m']==selection['depth_m'] and
            model['damping']==selection['damping'], 'transform_model_binding')
    require(type(model['points_m']) is list and len(model['points_m'])==3, 'transform_model_shape')
    for vector in (*model['points_m'],model['coefficients_mgal_m']):
        _vector(vector,len(train))
    require(model['interpretation']=='Nonunique harmonic coefficients, not density, mass, geology or physical source depth', 'transform_model_interpretation')
    fields(payload['evaluation'],'train holdout')
    _metrics(payload['evaluation']['train'],len(train)); _metrics(payload['evaluation']['holdout'],len(holdout))
    condition=payload['condition']; fields(condition,'damped_condition weighted_design_condition weighted_singular_values')
    number(condition['damped_condition'],0,cfg['max_condition'])
    if condition['weighted_design_condition'] is not None:
        number(condition['weighted_design_condition'],0)
    _vector(condition['weighted_singular_values'],len(train),low=0)
    alternatives=payload['nonuniqueness']; fields(alternatives,'training_only_alternatives interpretation')
    require(alternatives['interpretation']=='Comparable fits at different mathematical depths do not identify density or source geometry', 'transform_alternative_interpretation')
    require(type(alternatives['training_only_alternatives']) is list and 1<=len(alternatives['training_only_alternatives'])<=len(candidates), 'transform_alternatives')
    for row in alternatives['training_only_alternatives']:
        fields(row,'depth_m damping status '+('reason' if row.get('status')=='failed' else 'training_rmse_mgal coefficient_l2_mgal_m damped_condition'))
        require(row['status'] in ('passed','failed') and (row['depth_m'],row['damping']) in combinations, 'transform_alternative')
        if row['status']=='failed':
            text(row['reason'])
        else:
            for key in ('training_rmse_mgal','coefficient_l2_mgal_m','damped_condition'):
                number(row[key],0)
    uncertainty=payload['uncertainty']; fields(uncertainty,'kind error_model marginal_source fit_weights excludes')
    require(uncertainty==dict(kind='conditional_linear_noise_propagation',error_model=cfg['error_model'],
        marginal_source='Explicit cited covariance' if cfg['error_model']=='supplied_covariance' else 'Independent first-order correction propagation',
        fit_weights='Diagonal marginal inverse variances; not full-covariance GLS',
        excludes=['Geometry error','Parameter-selection uncertainty','Bias','Geological uncertainty']), 'transform_uncertainty_kind')
    resolution=payload['resolution']; fields(resolution,'median_training_nearest_neighbor_m grid_sampling_m coverage_radius_m coverage_is_resolution')
    number(resolution['median_training_nearest_neighbor_m'],0)
    require(resolution['grid_sampling_m']==cfg['grid_spacing_m'] and resolution['coverage_radius_m']==cfg['coverage_radius_m'] and
            resolution['coverage_is_resolution'] is False, 'transform_resolution')
    provenance=payload['provenance']; fields(provenance,'request_sha256 source_sha256 engines python module_sha256 corrections_reapplied correction_identity field_gate full_method_accepted')
    require(provenance['request_sha256']==scientific_digest(science) and provenance['source_sha256']==science['correction_result']['dataset']['metadata']['source_sha256']
        and provenance['engines']==manifest['runtime_manifest']['packages'] and provenance['python']==manifest['runtime_manifest']['python']
        and provenance['module_sha256']==manifest['transform_sha256'] and provenance['corrections_reapplied'] is False
        and provenance['field_gate']=='open' and provenance['full_method_accepted'] is False, 'transform_provenance')
    identity=provenance['correction_identity']; fields(identity,'input_state input_sha256 parent_policy deterministic_receipt_verified recorded_python runtime_python python_compatibility recorded_runtime_origin_verified recorded_runtime_implementation')
    require(identity['input_sha256']==science['correction_result']['processing']['input_sha256'] and
        identity['input_state'] in ('observed_absolute','gravity_disturbance','bouguer_disturbance') and
        identity['recorded_python']==science['correction_result']['processing']['python'] and
        identity['runtime_python']==manifest['runtime_manifest']['python'] and identity['deterministic_receipt_verified'] is True
        and identity['recorded_runtime_origin_verified'] is False and identity['recorded_runtime_implementation']=='Not specified by correction receipt'
        and identity['python_compatibility']=='Reviewed CPython 3.12.x lane'
        and identity['parent_policy']=='Canonical converted observations or verified known-stage history prefix only', 'transform_correction_identity')
    return 'passed' if precision else 'non_pass'


def verify_transform_producer(*, parent_snapshot, input_bytes, child_bytes, request_bytes,
                              result_bytes, approved_manifest, job, production):
    """Four-body/SQL barrier using independently audited prior correction receipt."""
    parent=_child(input_bytes)
    child=_decode(child_bytes,64*M); fields(child,DATASET_KEYS)
    require((child['schema'],child['kind'],child['parser_version'],child['modality'],child['payload_schema'],child['structural_verdict'])==
        ('geophysics.physical-dataset/v2','derived','gravity-stations-json/v1','gravity_equivalent_source_transform','gravity-transform-result-1','child_verified'), 'transform_child_schema')
    for key in ('dataset_id','owner_id','project_id','raw_asset_id','root_dataset_id','parent_dataset_id'):
        uuid(child[key])
    integer(child['version'],2,J); integer(child['raw_bytes'],1,16*M)
    require(child['version']>parent['version'] and child['dataset_id'] not in (parent['dataset_id'],parent['root_dataset_id']) and
            child['parent_dataset_id']==parent['dataset_id'] and child['parent_dataset_sha256']==byte_sha(input_bytes), 'transform_edge')
    for key in ('owner_id','project_id','root_dataset_id','raw_asset_id','raw_sha256','raw_bytes'):
        require(child[key]==parent[key], 'transform_family')
    source_structure(child['source']); _same(child['source'],parent['source'])
    fields(child['production'],PRODUCTION_KEYS)
    req=_decode(request_bytes,34*M,24,500000); result=_decode(result_bytes,64*M)
    fields(req,REQUEST_KEYS); fields(result,RESULT_KEYS); fields(parent_snapshot,PARENT_KEYS)
    require(req['schema']=='geophysics.physical-request/v2' and result['schema']=='geophysics.physical-result/v2'
            and req['method_id']==result['method_id']==TRANSFORM, 'transform_wrapped_schema')
    _same(req['parent_production'],parent_snapshot)
    require(parent_snapshot['schema']=='geophysics.physical-parent-production/v1' and
        parent_snapshot['method_id']=='gravity.station-corrections/v1' and parent_snapshot['state']=='succeeded'
        and parent_snapshot['scientific_verdict']=='passed', 'transform_parent_snapshot')
    for key in ('owner_id','project_id','root_dataset_id','raw_asset_id','raw_sha256','raw_bytes'):
        require(req[key]==parent[key]==parent_snapshot[key], 'transform_request_parent')
    require((parent_snapshot['output_dataset_id'],parent_snapshot['output_dataset_sha256'],parent_snapshot['output_dataset_bytes'],parent_snapshot['output_dataset_version'])==
        (parent['dataset_id'],byte_sha(input_bytes),len(input_bytes),parent['version']), 'transform_parent_bytes')
    require(parent_snapshot['adapter_result_sha256']==scientific_digest(parent['payload'])==parent['scientific_payload_sha256'], 'transform_parent_payload')
    _same(parent_snapshot['adapter_receipt'],parent['payload']['receipt'])
    require(parent_snapshot['adapter_receipt_sha256']==scientific_digest(parent_snapshot['adapter_receipt']) and
        parent_snapshot['core_result_sha256']==scientific_digest(parent['payload']['correction_result']), 'transform_parent_receipt')
    for key in PRODUCTION_KEYS.split():
        require(parent['production'][key]==parent_snapshot['adapter_result_sha256' if key=='scientific_result_sha256' else key], 'transform_parent_production')
    manifest=req['module_manifest']; fields(manifest,'schema parser_sha256 wrapper_sha256 adapter_sha256 core_sha256 transform_sha256 runtime_manifest')
    require(manifest['schema']=='geophysics.physical-modules/v1' and manifest['adapter_sha256'] is None, 'transform_manifest')
    for key in ('parser_sha256','wrapper_sha256','core_sha256','transform_sha256'):
        sha(manifest[key])
    runtime=manifest['runtime_manifest']; fields(runtime,'python python_implementation packages')
    require(type(runtime['python']) is str and re.fullmatch(r'3\.12\.\d+',runtime['python']) and
        runtime['python_implementation']=='CPython' and runtime['packages']==PINS_TRANSFORM and type(approved_manifest) is dict, 'transform_runtime')
    _same(manifest,approved_manifest); _same(result['module_manifest'],manifest)
    require(digest(manifest)==req['module_manifest_sha256']==result['module_manifest_sha256'], 'transform_manifest_hash')
    science=req['scientific_request']; fields(science,'schema_version correction_result geometry config'); fields(req['parameters'],'geometry config')
    require(science['schema_version']=='gravity-transform-request-1', 'transform_request_schema')
    _same(science['correction_result'],parent['payload']['correction_result'])
    for key in ('geometry','config'):
        _same(science[key],req['parameters'][key])
    require(scientific_digest(science)==req['scientific_request_sha256'] and digest(req['parameters'])==req['submitted_parameters_sha256'], 'transform_request_digest')
    for key in ('job_id','owner_id','project_id','dataset_id','dataset_sha256','raw_asset_id','raw_sha256','raw_bytes',
                'method_id','submitted_parameters_sha256','scientific_request_sha256'):
        require(result[key]==req[key], 'transform_result_identity')
    uuid(req['job_id']); require(req['dataset_id']==parent['dataset_id'] and req['dataset_sha256']==byte_sha(input_bytes), 'transform_selected_input')
    require(result['request_sha256']==digest(req) and (result['output_dataset_id'],result['output_dataset_sha256'])==
        (child['dataset_id'],byte_sha(child_bytes)), 'transform_result_output')
    _same(result['scientific_result'],child['payload'])
    # Inner output ceilings remain stricter than its complete application wrapper.
    _decode(canonical(child['payload'],scientific=True),64*M,24,2000000)
    _decode(canonical(science,scientific=True),16*M,16,200000)
    _decode(canonical(parent_snapshot),M,16,10000)
    require(len(canonical(manifest))<=65536, 'transform_manifest_limit')
    require(scientific_digest(child['payload'])==child['scientific_payload_sha256']==result['scientific_result_sha256'], 'transform_payload_hash')
    verdict=_output(child['payload'],science,parent,manifest)
    require(result['scientific_verdict']==child['production']['scientific_verdict']==verdict and child['production']['adapter_result_sha256'] is None, 'transform_verdict')
    for key in ('job_id','method_id','request_sha256','scientific_result_sha256','module_manifest_sha256'):
        require(child['production'][key]==result[key], 'transform_child_production')
    limits=req['limits']; ceilings=dict(cpu_ms=240000,wall_seconds=300,rss_bytes=1536*M,scratch_bytes=512*M,
        scientific_input_bytes=16*M,child_output_bytes=64*M,stdout_bytes=65536,stderr_bytes=65536)
    fields(limits,' '.join(ceilings))
    for key,cap in ceilings.items():
        integer(limits[key],1,cap)
        if key in ('scientific_input_bytes','child_output_bytes','stdout_bytes','stderr_bytes'):
            require(limits[key]==cap, 'transform_fixed_limit')
    require(len(canonical(science,scientific=True))<=limits['scientific_input_bytes'] and len(canonical(req['parameters']))<=16*M, 'transform_input_limit')
    measured=result['receipt']; fields(measured,'wall_ms cpu_ms peak_rss_bytes scratch_peak_bytes child_output_bytes environment environment_sha256 admission_receipt_sha256')
    for key,cap in (('wall_ms',limits['wall_seconds']*1000),('cpu_ms',limits['cpu_ms']),('peak_rss_bytes',limits['rss_bytes']),
                    ('scratch_peak_bytes',limits['scratch_bytes']),('child_output_bytes',limits['child_output_bytes'])):
        integer(measured[key],0 if key in ('wall_ms','cpu_ms','scratch_peak_bytes') else 1,cap)
    _same(measured['environment'],runtime)
    require(measured['environment_sha256']==digest(runtime) and measured['child_output_bytes']==len(canonical(child['payload'],scientific=True))
        and measured['admission_receipt_sha256']==sha(req['admission_receipt_sha256']), 'transform_resource_binding')
    for key,value in dict(id=req['job_id'],owner_id=req['owner_id'],project_id=req['project_id'],dataset_id=parent['dataset_id'],
        dataset_sha256=byte_sha(input_bytes),method_id=TRANSFORM,state='succeeded',request_sha256=digest(req),result_sha256=byte_sha(result_bytes),
        result_bytes=len(result_bytes),result_key=f"derived/{req['owner_id']}/{req['project_id']}/results/{req['job_id']}.json",
        wall_ms=measured['wall_ms'],physical_cpu_ms=measured['cpu_ms'],peak_rss_bytes=measured['peak_rss_bytes'],scratch_bytes=measured['scratch_peak_bytes'],
        error_code=None,error_message=None).items():
        require(job[key]==value, 'transform_saved_job')
    require(job['finished_at'] is not None, 'transform_terminal')
    for key in NULL_ADAPTER:
        require(production[key] is None, 'transform_no_adapter')
    expected=dict(child_dataset_id=child['dataset_id'],job_id=req['job_id'],owner_id=req['owner_id'],project_id=req['project_id'],
        root_dataset_id=req['root_dataset_id'],raw_asset_id=req['raw_asset_id'],parent_dataset_id=req['dataset_id'],parent_dataset_sha256=req['dataset_sha256'],
        method_id=TRANSFORM,request_sha256=digest(req),submitted_parameters_sha256=req['submitted_parameters_sha256'],scientific_request_sha256=req['scientific_request_sha256'],
        scientific_result_sha256=scientific_digest(child['payload']),module_manifest_sha256=digest(manifest),result_sha256=byte_sha(result_bytes),
        result_bytes=len(result_bytes),scientific_verdict=verdict)
    for key,value in expected.items():
        require(production[key]==value, 'transform_saved_relation')
    return child
