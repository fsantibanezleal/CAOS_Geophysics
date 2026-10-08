"""Separate QR Result/3: exhaustive source/candidate/receipt custody semantics.

Actual DGELS receipts are never cast into LSMR. The original opened acquisition
and adverse historical results are not promoted to untouched or field evidence.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import itertools
import math
from pathlib import Path
import sqlite3

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as v1
import magnetic_line_survey_contract_qr as schema
import magnetic_line_survey_hp as hp
import magnetic_line_survey_io as io
import magnetic_line_survey_representation_qr as representation
from magnetic_line_survey_fit import select_candidate
from magnetic_line_survey_support import grid_ids


def references(value):
    if type(value) is dict:
        if 'array_id' in value and 'manifest' in value or 'table_id' in value and 'manifest' in value:
            yield value
            return
        for child in value.values():
            yield from references(child)
    elif type(value) is list:
        for child in value:
            yield from references(child)


def _refs(value):
    result={}
    for ref in references(value):
        name=ref['manifest']['name']
        if name in result and result[name]!=ref:
            raise core.SurveyError('custody_mismatch','export')
        result[name]=ref
    return list(result.values())


def _check(predicate):
    if not predicate:
        # Safe source check ID only, never a traceback/path/value. This makes
        # retained scientific refusal diagnosable without leaking owner data.
        import inspect
        error=core.SurveyError('custody_mismatch','replay')
        error.error['field']='result_check.'+str(inspect.currentframe().f_back.f_lineno)
        raise error


def _role(ref,role,dtype,unit,shape,ordered=None):
    _check((ref['role'],ref['dtype'],ref['unit'],ref['shape'])==(role,dtype,unit,shape))
    if ordered is not None:
        _check(ref['ordered_ids_sha256']==ordered)


def _verify_channel_edges(reader,result,metadata,request,arrays):
    """Reconstruct every domain-separated edge in original source row order."""
    original={ref['role']:ref for ref in metadata['arrays']}
    missing=next(ref for ref in result['input']['arrays'] if ref['role']=='missing_mask')
    ids=original['row_id']
    n=ids['shape'][0]
    aligned=[ref for ref in result['geometry']['arrays'] if ref['role']=='navigation' and
             ref['shape']==[n,3] and ref['ordered_ids_sha256']==ids['ordered_ids_sha256']]
    parent=request['channel_sha256']
    expected_state=deepcopy(metadata['channel_state'])
    for index,channel in enumerate(result['channels']):
        mask=arrays[channel['data']['mask_array_id']]
        values=reader.cells(channel['data'])
        if not index:
            identity=sha256(b'[')
            for pos,(rid,value,flag) in enumerate(zip(reader.cells(ids),values,reader.cells(missing),strict=True)):
                if pos:
                    identity.update(b',')
                identity.update(base.canonical_bytes([rid,None if flag&16 else value]))
            identity.update(b']')
            _check(identity.hexdigest()==parent==request['split']['sealed_values_sha256'])
            _check(channel['state']==expected_state and channel['kind']==metadata['quantity']['kind'])
            continue
        operation=request['operations'][index-1]
        name=operation['operation']
        state=channel['state'][-1]
        _check(channel['state'][:-1]==expected_state and state['parent_channel_sha256']==parent and
               state['parameters']==operation['parameters'])
        lagged=any(op['operation']=='lag' for op in request['operations'][:index])
        if lagged:
            _check(len(aligned)==1)
            cells=reader.cells(aligned[0])
            coordinates=iter(lambda:tuple(itertools.islice(cells,3)),())
        else:
            coordinates=zip(*(reader.cells(original[role]) for role in ('easting','northing','upward')),strict=True)
        identity=sha256(b'm03-correction-row-edge/1\0'+base.canonical_bytes(dict(operation=name,kind=channel['kind'])))
        for rid,xyz,value,qc,raw_mask in zip(reader.cells(ids),coordinates,reader.cells(channel['data']),
                reader.cells(mask),reader.cells(missing),strict=True):
            _check(len(xyz)==3)
            nullable=None if raw_mask&16 or qc&(1|8|32) else value
            encoded=base.canonical_bytes([rid,*xyz,nullable,qc])
            identity.update(len(encoded).to_bytes(8,'little')+encoded)
        child=identity.hexdigest()
        _check(state['output_channel_sha256']==child and state['evidence_sha256']==base.digest(
            dict(operation=name,parent=parent,output=child,parameters=operation['parameters'])))
        if name=='main_field':
            _check(channel['reference_receipt_sha256']==operation['parameters']['evaluated_reference']['receipt_sha256'])
        expected_state.append(state)
        parent=child


def _aux_identities(value):
    result=[]
    def visit(item):
        if type(item) is dict:
            if set(item)==set(base.SCHEMAS['AuxIdentity']):
                if item not in result:
                    result.append(item)
            else:
                for child in item.values():
                    visit(child)
        elif type(item) is list:
            for child in item:
                visit(child)
    visit(value)
    return result


def _pack(root,refs,destination):
    reader=representation.Reader(root)
    for ref in refs:
        reader.verify(ref)
    for identity in reader.known.values():
        payload=core._verified_member(reader.root,identity,set(),8388608)
        path=destination/identity['name']
        if path.exists():
            _check(base.read_bounded(core._plain_path(path),8388608)==payload)
        else:
            core._write_member(destination,identity['name'],payload)


def assemble_fixed_result(workspace,sealed,measurements,corrected,fitted,grids,metadata,request,
                          request_root,navigation_root,auxiliary_roots,reference_definitions,*,
                          run_id,environment,temp_root,job_handle,execution,original_documents=None):
    """Assemble actual completed stages, not a cast of their diagnostic envelopes.

    Unsupported requested operations refuse before a Result. No successful
    scientific/field/admission gate is manufactured for a converged computation.
    Raw mirroring denial is retained; this bundle alone cannot replay without
    legitimately available original acquisition bytes.
    """
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    workspace=io.external_path(workspace)
    resolution=request.get('schema')=='magnetic-line-survey-request/2'
    if not resolution:raise core.SurveyError('invalid_contract','export')
    contract=schema if resolution else v1
    metadata=contract.validate('SurveyInput',metadata)
    request=contract.validate('SurveyRequest',request)
    _check(fitted['evaluation_count']==1 and fitted['fit']['fit_count']==(97 if resolution else 25) and
        grids['geometry_sha256']==base.digest(sealed['geometry']) and
        grids['fit_sha256']==base.digest(fitted) and grids['request_sha256']==base.digest(request))
    _check([edge['operation'] for edge in corrected['edges']]==[op['operation'] for op in request['operations']])
    if any(op['operation'] in ('leveling','microlevel') for op in request['operations']):
        raise core.SurveyError('unsupported_operation','export')
    output=workspace/'result'
    if output.exists():
        raise core.SurveyError('custody_mismatch','export')
    output.mkdir()
    original=metadata['original']
    n=sealed['geometry']['rows']
    identity=next(ref['ordered_ids_sha256'] for ref in metadata['arrays'] if ref['role']=='row_id')
    flag_ref=corrected['masks'][-1]
    flags=io.Reader(workspace/'corrected')
    dispositions=io.Writer(output,'inventory-disposition',role='qc_mask',shape=[n],dtype='uint32',unit='identity')
    counts=[0,0,0]
    for flag in flags.cells(flag_ref):
        disposition=2 if flag&1 else 3 if flag else 1
        counts[disposition-1]+=1
        dispositions.append(io.encoded_cell(disposition,'uint32'))
    inventory=dict(original_rows=n,retained=counts[0],invalid=counts[1],excluded=counts[2],
        disposition=dispositions.finish(identity),reasons=flag_ref,flags=flag_ref)
    parts=sealed['partitions']['partitions']
    if resolution:
        selected_geometry=fitted['fit']['selected_source_geometry_index']
        parts=[dict(part,source_members=sealed['geometry']['source_maps'][selected_geometry*4+fold]['source_members'])
            for fold,part in enumerate(parts)]
    partitions=dict(seal_sha256=base.digest(sealed['geometry']),final_training=parts[0]['training'],
        outer_validation=parts[0]['validation'],exclusions=parts[0]['exclusions'],
        inner=[dict(fold_id=part['fold_id'],**{key:part[key] for key in ('training','validation','exclusions','source_members')})
               for part in parts[1:]],evaluation_count=1)
    predictive=dict(overall='unresolved',gates=[dict(gate_id='predictive',verdict='unresolved',
        evidence_sha256=base.digest(fitted),reason='No applicable predictive acceptance established')],
        numerical_success=True,reasons=['Convergence is not predictive or field acceptance'])
    # The original S1 quality rule is unchanged and is not reused as a field
    # uncertainty or as a new acceptance target for other controls.
    if metadata['authored_control'] is not None and metadata['authored_control']['regime']=='S1':
        verdict='pass' if fitted['rmse_nT']<=max(1e-6,.05*fitted['signal_rms_nT']) else 'fail'
        predictive['overall']=predictive['gates'][0]['verdict']=verdict
        predictive['gates'][0]['reason']='Original S1 5-percent signal RMS criterion; opened diagnostic acquisition'
    if metadata['authored_control']['regime']!='S1':
        predictive['gates'][0]['reason']='Opened authored QR diagnostic; no independent prospective predictive acceptance'
    evaluation=dict(observed=fitted['outer_arrays'][0],predicted=fitted['outer_arrays'][1],residual=fitted['outer_arrays'][2],
        **{key:fitted[key] for key in ('scored','excluded','coverage','signal_rms_nT','rmse_nT','per_line')},
        comparison=None,verdict=predictive)
    aux=_aux_identities(request['operations'])
    document_bytes=dict(metadata=base.canonical_bytes(metadata),request=base.canonical_bytes(request))
    if original_documents is not None:
        core._closed(original_documents,'metadata request','export')
        for key,expected in (('metadata',metadata),('request',request)):
            if type(original_documents[key]) is not bytes or len(original_documents[key])>2097152 or \
               base.strict_json(original_documents[key])!=expected:
                raise core.SurveyError('custody_mismatch','export')
            document_bytes[key]=original_documents[key]
    metadata_file=core._write_member(output,'metadata.json',document_bytes['metadata'])
    request_file=core._write_member(output,'request.json',document_bytes['request'])
    # Geometric crossing pairs remain identified as geometry, without inventing
    # corrected differences or training offsets where none was requested.
    crossovers=sealed['crossovers']['table']
    execution_file=core._write_member(output,'qr-execution.json',base.canonical_bytes(execution))
    result=dict(schema='magnetic-line-survey-result/3',policy_epoch=schema.POLICY_EPOCH,execution=execution_file,run_id=run_id,
        lane='local_synthetic' if metadata['source_kind']=='original_synthetic_acquisition' else 'local_user',
        input=dict(dataset_sha256=request['dataset_version_sha256'],original=original,metadata=metadata_file,
            arrays=metadata['arrays']+measurements['arrays'],auxiliary_identities=aux),request=request_file,
        environment=environment,geometry=sealed['geometry'],inventory=inventory,channels=corrected['channels'],
        crossovers=crossovers,leveling=None,partitions=partitions,fit=fitted['fit'],grid=grids['grid'],spectrum=grids['spectrum'],
        evaluation=evaluation,rights=metadata['rights'],artifacts=[],verdict=dict(overall='fail' if predictive['overall']=='fail' else 'unresolved',
            numerical_success=True,gates=[dict(gate_id='numerics',verdict='pass',evidence_sha256=base.digest(fitted['fit']),reason=None),
                predictive['gates'][0],dict(gate_id='field_source',verdict='unresolved',evidence_sha256=None,
                    reason='No authenticated original field acquisition'),
                dict(gate_id='host_admission',verdict='unresolved',evidence_sha256=None,
                    reason='Whole-run host admission not established')],
            reasons=['Numerical success does not establish predictive, field or host acceptance']))
    all_refs=_refs([result,corrected['masks']])
    roots=[workspace/'sealed',workspace/'measurements',workspace/'corrected',workspace/'fit',workspace/'grids',
           io.external_path(request_root),output]+[io.external_path(root) for root in auxiliary_roots.values()]
    if navigation_root is not None:
        roots.append(io.external_path(navigation_root))
    for ref in all_refs:
        matches=[root for root in roots if (root/ref['manifest']['name']).is_file()]
        _check(bool(matches))
        for root in matches:
            _pack(root,[ref],output)
    # Retain reference definition originals as explicit actual source members.
    extra=[execution_file]
    scaled_file=fitted['fit']['scaled_coefficients']
    extra.append(core._write_member(output,scaled_file['name'],
        core._verified_member(workspace/'fit',scaled_file,set(),524288)))
    if resolution:
        proof=sealed['capacity_proof']
        payload=core._verified_member(workspace/'sealed',proof,set(),4194304)
        extra.append(core._write_member(output,proof['name'],payload))
    for operation,definition in reference_definitions.items():
        payload=core._verified_member(io.external_path(auxiliary_roots[operation]),definition,set(),4194304)
        name=operation+'-source.json'
        extra.append(core._write_member(output,name,payload))
    all_refs=_refs([result,request,corrected['masks']])
    for ref in all_refs:
        if not (output/ref['manifest']['name']).exists():
            matches=[root for root in roots if (root/ref['manifest']['name']).is_file()]
            _check(bool(matches))
            for root in matches:
                _pack(root,[ref],output)
    logical={ref['manifest']['name']:ref['manifest'] for ref in all_refs}
    logical.update({item['name']:item for item in [metadata_file,request_file]+extra})
    if len(logical)+1>192 or len([ref for ref in all_refs if 'array_id' in ref])>128:
        raise core.SurveyError('resource_refused','export')
    result['artifacts']=[dict(role='source' if item['name'] in {value['name'] for value in extra} else 'data',
        **item,permission='allowed',disposition='included',reason='Private processing closure; no public location/raw grant')
        for item in sorted(logical.values(),key=lambda value:value['name'])]
    result['artifacts'].append(dict(role='raw',name='original.csv',bytes=0,sha256=None,
        permission=metadata['rights']['raw_mirroring'],disposition='denied' if metadata['rights']['raw_mirroring']=='denied' else 'unresolved',
        reason='Original acquisition is not mirrored by the private result assembler'))
    result=schema.validate('SurveyResult',result)
    verify_result(output,result,temp_root=temp_root,allow_uncommitted=True,job_handle=job_handle)
    core._write_member(output,'result.json',base.canonical_bytes(result))
    return result


def verify_result(root,result=None,*,temp_root,allow_uncommitted=False,job_handle=None):
    """Strict closed result/custody and cross-object semantics, not a new fit.

    Native source/model recomputation is a separate contained gate, not silently
    claimed by this verifier. It does verify actual residuals, inventories,
    source-order partitions, candidate completeness/selection and grid domains.
    """
    root=io.external_path(root)
    stored=base.strict_json(base.read_bounded(core._plain_path(root/'result.json'),2097152)) if not allow_uncommitted else result
    if result is not None:
        _check(stored==result)
    result=schema.validate('SurveyResult',stored)
    resolution=result['policy_epoch']==schema.POLICY_EPOCH
    contract=schema if resolution else v1
    reader=representation.Reader(root)
    metadata=contract.validate('SurveyInput',base.strict_json(reader.member(result['input']['metadata'])))
    request=contract.validate('SurveyRequest',base.strict_json(reader.member(result['request'])))
    _check(result['input']['original']==metadata['original']==result['geometry']['original'])
    _check(result['input']['dataset_sha256']==request['dataset_version_sha256']==base.dataset_identity(
        metadata['original']['csv_sha256'],base.digest(metadata)))
    _check(result['rights']==metadata['rights'] and result['rights']['private_processing']=='allowed')
    _check(result['input']['auxiliary_identities']==_aux_identities(request['operations']))
    execution=base.strict_json(reader.member(result['execution']))
    from magnetic_line_survey_qr_execution import verify_execution
    verify_execution(execution,result['geometry'],metadata,request,root,source_environment=result['environment'],
        document_hashes=dict(metadata=result['input']['metadata']['sha256'],request=result['request']['sha256']))
    environment=deepcopy(result['environment'])
    env_sha=environment.pop('environment_receipt_sha256')
    _check(env_sha==base.digest(environment))
    refs=_refs([result,request])
    # The legacy ChannelReceipt links its QC target by ID rather than embedding
    # an ArrayRef. Resolve ONLY that explicitly declared target from the included
    # actual manifest, with channel-bound role/unit/shape/order. No filename-based
    # role discovery, alternate mask, unbound target or unknown artifact is allowed.
    for channel in result['channels']:
        mask_id=channel['data']['mask_array_id']
        if not any(ref.get('array_id')==mask_id for ref in refs):
            name='array-'+mask_id+'.json'
            targets=[item for item in result['artifacts'] if item['name']==name and item['disposition']=='included']
            _check(len(targets)==1)
            member={key:targets[0][key] for key in ('name','bytes','sha256')}
            body=base.strict_json(reader.member(member))
            epoch=v1 if body.get('schema')=='magnetic-line-array-manifest/1' else schema
            manifest=epoch.validate('ArrayManifest',body)
            _check(manifest['array_id']==mask_id and manifest['shape']==channel['data']['shape'] and
                manifest['dtype']=='uint32' and manifest['unit']=='identity')
            refs.append(epoch.validate('ArrayRef',dict(array_id=mask_id,role='qc_mask',shape=manifest['shape'],dtype='uint32',
                unit='identity',chunk_rows=4096,manifest=member,ordered_ids_sha256=channel['data']['ordered_ids_sha256'],mask_array_id=None)))
    for ref in refs:
        reader.verify(ref)
    arrays={ref['array_id']:ref for ref in refs if 'array_id' in ref}
    _check(len(arrays)==len([ref for ref in refs if 'array_id' in ref]))
    _check(len(arrays)<=128 and len(result['artifacts'])<=192)
    n=result['geometry']['rows']
    original_refs={ref['role']:ref for ref in metadata['arrays']}
    row_ids=original_refs['row_id']
    _role(row_ids,'row_id','ascii64','identity',[n])
    row_hash=row_ids['ordered_ids_sha256']
    _check(result['inventory']['original_rows']==n)
    for key in ('disposition','reasons','flags'):
        _role(result['inventory'][key],'qc_mask','uint32','identity',[n],row_hash)
    counts=[0,0,0]
    for disposition,reason,flag in zip(*(reader.cells(result['inventory'][key]) for key in ('disposition','reasons','flags')),strict=True):
        _check(disposition==(2 if flag&1 else 3 if flag else 1) and reason==flag)
        counts[disposition-1]+=1
    _check(counts==[result['inventory'][key] for key in ('retained','invalid','excluded')])
    channels=result['channels']
    _check(len(channels)==len(request['operations'])+1 and channels[0]['role']=='original' and channels[0]['parent_sha256'] is None)
    parent=request['channel_sha256']
    for index,channel in enumerate(channels):
        _role(channel['data'],'magnetic','float64','nT',[n],row_hash)
        mask=arrays.get(channel['data']['mask_array_id'])
        _check(mask is not None)
        _role(mask,'qc_mask','uint32','identity',[n],row_hash)
        if index:
            state=channel['state'][-1]
            operation=request['operations'][index-1]
            _check(channel['role']=='derived' and channel['parent_sha256']==parent and state['parent_channel_sha256']==parent and
                state['operation']==operation['operation'] and state['parameters']==operation['parameters'] and state['status']=='applied')
            parent=state['output_channel_sha256']
    _check(channels[-1]['kind']=='scalar_total_field_anomaly')
    _verify_channel_edges(reader,result,metadata,request,arrays)
    partitions=result['partitions']
    _check(partitions['seal_sha256']==base.digest(result['geometry']) and partitions['evaluation_count']==1)
    folds=[dict(training=partitions['final_training'],validation=partitions['outer_validation'],exclusions=partitions['exclusions'])]+partitions['inner']
    _check([fold['fold_id'] for fold in folds[1:]]==[fold['fold_id'] for fold in request['split']['inner_folds']])
    # Disk-backed identity/order/disjoint checks; no O(N) Python set or an
    # O(lines*N) scan. Every partition index remains in original source order.
    with io.scratch_directory(temp_root) as scratch:
        db=sqlite3.connect(Path(scratch)/'verify.sqlite')
        try:
            db.execute('PRAGMA cache_size=-131072')
            db.execute('PRAGMA temp_store=FILE')
            db.execute("PRAGMA temp_store_directory='"+str(scratch).replace("'","''")+"'")
            sensors=list(reader.table(metadata['acquisition']['sensor_dictionary']))
            selected=[index for index,sensor in enumerate(sensors) if sensor['sensor_id']==request['sensor_id']]
            _check(len(selected)==1)
            db.execute('CREATE TABLE ids(pos INTEGER PRIMARY KEY,id TEXT UNIQUE,sensor INTEGER)')
            db.executemany('INSERT INTO ids VALUES (?,?,?)',((pos,rid,sensor) for pos,(rid,sensor) in enumerate(
                zip(reader.cells(row_ids),reader.cells(original_refs['sensor_index']),strict=True))))
            _check(db.execute('SELECT count(*) FROM ids').fetchone()[0]==n)
            db.execute('CREATE TABLE partition(fold INTEGER,pos INTEGER,kind INTEGER,PRIMARY KEY(fold,pos))')
            for f,fold in enumerate(folds):
                for kind,key in enumerate(('training','validation','exclusions'),1):
                    ref=fold[key]
                    _role(ref,'partition_index','uint64','identity',ref['shape'])
                    _check(ref in result['geometry']['arrays'])
                    ordered=sha256()
                    previous=-1
                    for pos in reader.cells(ref):
                        _check(previous<pos<n)
                        previous=pos
                        rid=db.execute('SELECT id FROM ids WHERE pos=?',(pos,)).fetchone()[0]
                        ordered.update(rid.encode('ascii').ljust(64,b'\0'))
                        db.execute('INSERT INTO partition VALUES (?,?,?)',(f,pos,kind))
                    _check(ordered.hexdigest()==ref['ordered_ids_sha256'])
                # Nonselected sensors need not be in the split, but no selected
                # row may silently disappear from the partition inventory.
                _check(not db.execute('SELECT 1 FROM ids i LEFT JOIN partition p ON i.pos=p.pos AND p.fold=? '
                    'WHERE (i.sensor=? AND p.pos IS NULL) OR (i.sensor!=? AND p.pos IS NOT NULL) LIMIT 1',
                    (f,selected[0],selected[0])).fetchone())
            db.commit()
            if resolution:
                from magnetic_line_survey_resolution_geometry import verify_result_maps
                verify_result_maps(reader,result,metadata,request,db)
        except sqlite3.IntegrityError:
            raise core.SurveyError('custody_mismatch','replay') from None
        finally:
            db.close()
    fit=result['fit']
    _check(fit['solver']==schema.POLICY and fit['legacy_request_solver']==request['solver'] and fit['fit_count']==(97 if resolution else 25) and
        fit['candidates']['row_schema']==('candidate_fit_qr_v3'))
    candidates=list(reader.table(fit['candidates']))
    identities=list(reader.table(fit['solve_identities']))
    _check(len(identities)==97)
    for index,row in enumerate(candidates):
        _check(identities[index]==dict(sequence=index,**{key:row[key] for key in
            ('source_geometry_index','fold_id','depth_m','damping','solve')}))
    _check(identities[96]==dict(sequence=96,source_geometry_index=fit['selected_source_geometry_index'],fold_id='final',
        depth_m=fit['selected_depth_m'],damping=fit['selected_damping'],solve=fit['solve']))
    for index,identity in enumerate(identities):
        fold=0 if index==96 else index%3+1
        _check(identity['fold_id']==('final' if fold==0 else folds[fold]['fold_id']))
        _check(identity['solve']['rows']==folds[fold]['training']['shape'][0] and
            identity['solve']['sources']==result['geometry']['source_counts_by_geometry'][identity['source_geometry_index']][fold])
    expected=list(itertools.product(request['equivalent_sources']['depth_candidates_m'],
        request['equivalent_sources']['damping_candidates'],[fold['fold_id'] for fold in folds[1:]]))
    if resolution:
        expected=[(g,*identity) for g in range(4) for identity in expected]
    _check(len(candidates)==(96 if resolution else 24) and
        [(row['source_geometry_index'],row['depth_m'],row['damping'],row['fold_id']) if resolution else
         (row['depth_m'],row['damping'],row['fold_id']) for row in candidates]==expected)
    scores=[]
    for index in range(0,len(candidates),3):
        group=candidates[index:index+3]
        for row,fold in zip(group,folds[1:],strict=True):
            _check(row['scored']>0 and row['scored']+row['excluded']==fold['validation']['shape'][0] and
                row['rmse_nT'] is not None and row['solve']['numerical_verdict']=='component_pass' and row['verdict']['overall']=='pass')
            _check(row['verdict']['gates']==[dict(gate_id='solve',verdict='pass',evidence_sha256=base.digest(row['solve']),reason=None)])
        scores.append(dict(depth_m=group[0]['depth_m'],damping=group[0]['damping'],
                           mean_rmse_nT=math.fsum(row['rmse_nT'] for row in group)/3))
        if resolution:
            scores[-1]['source_geometry_index']=group[0]['source_geometry_index']
    if resolution:
        from magnetic_line_survey_physical_fit_qr import select_resolution_candidate
        selected=select_resolution_candidate(scores)
        _check(fit['selected_source_geometry_index']==selected['source_geometry_index'])
    else:
        selected=select_candidate(scores)
    _check((fit['selected_depth_m'],fit['selected_damping'])==(selected['depth_m'],selected['damping']))
    m=fit['sources']['shape'][0]
    expected_sources=result['geometry']['source_counts_by_geometry'][selected['source_geometry_index']][0] if resolution else result['geometry']['source_counts'][0]
    _check(m==expected_sources and fit['solve']['numerical_verdict']=='component_pass')
    _check(fit['scaled_coefficients']['name']=='qr-final-scaled.bin' and fit['scaled_coefficients']['bytes']==8*m and
        fit['scaled_coefficients']['sha256']==fit['solve']['scaled_coefficients_sha256'])
    reader.member(fit['scaled_coefficients'],524288)
    _role(fit['sources'],'source_position','float64','m',[m,3])
    for key,role,unit in (('column_scales','source_scale','1_per_m'),('coefficients','coefficient','nT*m')):
        _role(fit[key],role,'float64',unit,[m],fit['sources']['ordered_ids_sha256'])
    _check(all(value>0 for value in reader.cells(fit['column_scales'])))
    ev=result['evaluation']
    _check(ev['scored']>0 and ev['scored']+ev['excluded']==partitions['outer_validation']['shape'][0] and
        ev['coverage']==ev['scored']/partitions['outer_validation']['shape'][0])
    # Bounded compensated totals, never retain a whole outer residual vector.
    rs=ss=rc=sc=0.
    for observed,predicted,residual in zip(*(reader.cells(ev[key]) for key in ('observed','predicted','residual')),strict=True):
        _check(residual==observed-predicted)
        for value,is_signal in ((residual,False),(observed,True)):
            square=value*value
            _check(math.isfinite(square) and (value==0 or square>0))
            if is_signal:
                y=square-sc;t=ss+y;sc=(t-ss)-y;ss=t
            else:
                y=square-rc;t=rs+y;rc=(t-rs)-y;rs=t
    for key,role in (('observed','magnetic'),('predicted','predicted'),('residual','residual')):
        _role(ev[key],role,'float64','nT',[ev['scored']],ev['observed']['ordered_ids_sha256'])
    _check(abs(math.sqrt(rs/ev['scored'])-ev['rmse_nT'])<=1e-12*max(1.,ev['rmse_nT']) and
        abs(math.sqrt(ss/ev['scored'])-ev['signal_rms_nT'])<=1e-12*max(1.,ev['signal_rms_nT']))
    _check(metadata['source_kind']=='original_synthetic_acquisition' and result['lane']=='local_synthetic')
    gates={gate['gate_id']:gate for gate in result['verdict']['gates']}
    _check(set(gates)=={'numerics','predictive','field_source','host_admission'} and gates['numerics']['verdict']=='pass' and
        gates['field_source']['verdict']=='unresolved' and gates['host_admission']['verdict']=='unresolved' and
        result['verdict']['numerical_success'] is True)
    expected_predictive='unresolved'
    if metadata['authored_control']['regime']=='S1':
        expected_predictive='pass' if ev['rmse_nT']<=max(1e-6,.05*ev['signal_rms_nT']) else 'fail'
    _check(gates['predictive']['verdict']==ev['verdict']['overall']==expected_predictive and
        result['verdict']['overall']==('fail' if expected_predictive=='fail' else 'unresolved'))
    _check(ev['per_line']['row_schema']=='line_evaluation')
    lines=list(reader.table(ev['per_line']))
    _check(len({line['line_id'] for line in lines})==len(lines) and sum(line['scored'] for line in lines)==ev['scored'] and
           sum(line['excluded'] for line in lines)==ev['excluded'])
    grids=result['grid']
    _check(len(grids)==(2 if request['grid']['continuation_delta_m'] is not None else 1))
    cells=0
    for index,grid in enumerate(grids):
        config=request['grid'] if index==0 else dict(request['grid'],
            plane_upward_m=request['grid']['plane_upward_m']+request['grid']['continuation_delta_m'],continuation_delta_m=None)
        _check(grid['config']==config and grid['role']==('fitted_plane' if index==0 else 'continued_plane'))
        shape=[config['ny'],config['nx']]
        cells+=math.prod(shape)
        _role(grid['values'],'grid_value','float64','nT',shape,grid_ids(config))
        _role(grid['support_mask'],'grid_mask','uint32','identity',shape,grid_ids(config))
        _check(grid['support_mask'] in result['geometry']['arrays'] and grid['values']['mask_array_id']==grid['support_mask']['array_id'])
        for key,name,origin,step,count in (('easting_axis','easting',config['origin_e_m'],config['spacing_e_m'],config['nx']),
                ('northing_axis','northing',config['origin_n_m'],config['spacing_n_m'],config['ny'])):
            ref=grid[key]
            _role(ref,'grid_axis','float64','m',[count])
            ordered=sha256()
            previous=None
            for i,value in enumerate(reader.cells(ref)):
                _check(value==origin+i*step and (previous is None or value>previous and abs(value-previous-step)<=64*core.EPSILON*step))
                ordered.update(f'{name}.{i}'.encode('ascii').ljust(64,b'\0'))
                previous=value
            _check(ref['ordered_ids_sha256']==ordered.hexdigest())
        for value,mask in zip(reader.cells(grid['values']),reader.cells(grid['support_mask']),strict=True):
            _check(not mask&~4096 or value==0)
    _check((result['spectrum'] is None)==(request['spectrum'] is None))
    if result['spectrum'] is not None:
        spectrum=result['spectrum']
        _check(spectrum['config']==request['spectrum'])
        cells+=math.prod(spectrum['power']['shape'])
        _check(spectrum['power']['role']=='spectrum_power' and spectrum['power']['unit']=='nT^2')
        _check(abs(math.fsum(reader.cells(spectrum['power']))-spectrum['parseval_sum_nT2'])<=
            1e-10*max(spectrum['parseval_sum_nT2'],1e-12))
    _check(cells<=1048576 and cells==result['geometry']['capacity']['exported_cells'])
    included=[item for item in result['artifacts'] if item['disposition']=='included']
    _check(len({item['name'] for item in result['artifacts']})==len(result['artifacts']))
    for item in included:
        reader.member({key:item[key] for key in ('name','bytes','sha256')})
    expected={ref['manifest']['name'] for ref in refs}|{result['request']['name'],result['input']['metadata']['name']}
    _check(expected<={item['name'] for item in included})
    reader.reject_unknown(extra=() if allow_uncommitted else ('result.json',))
    native='not_executed'
    if job_handle is not None:
        verify_selected_model(reader,result,metadata,request,temp_root=temp_root,job_handle=job_handle)
        native='pass'
    return dict(schema='m03-result-custody-verification/1',result_sha256=base.digest(result),
        policy_epoch=result['policy_epoch'],rows=n,logical_members=len(result['artifacts']),physical_members=len(reader.known),
        physical_bytes=sum(item['bytes'] for item in reader.known.values()),
        custody_and_semantics='pass',selected_model_recomputation=native,
        replay_originals='not_available',field_acceptance='unresolved',host_admission='not_established')


def verify_selected_model(reader,result,metadata,request,*,temp_root,job_handle):
    """Contained all-source gradient, observed-row and complete-grid recomputation.

    Reverification of a retained single evaluation cannot select/tune a new fit
    and never creates a second untouched-validation label or new acceptance rule.
    """
    from functools import partial
    from magnetic_line_survey_runtime import require_job
    from magnetic_line_survey_fit import mapped_array,mapping_lifetime,predict_global,_readonly
    require_job(job_handle)
    np,_=core.engines()
    n=result['geometry']['rows']
    fit=result['fit']
    with io.scratch_directory(temp_root) as scratch,mapping_lifetime() as mappings:
        scratch=Path(scratch)
        mapper=partial(mapped_array,registry=mappings)
        original={ref['role']:ref for ref in metadata['arrays']}
        row_hash=original['row_id']['ordered_ids_sha256']
        aligned=[ref for ref in result['geometry']['arrays'] if ref['role']=='navigation' and ref['shape']==[n,3] and
                 ref['ordered_ids_sha256']==row_hash]
        if any(op['operation']=='lag' for op in request['operations']):
            _check(len(aligned)==1)
            xyz=mapper(reader,aligned[0],scratch/'xyz.bin',np)
        else:
            xyz=_readonly(np,np.column_stack([mapper(reader,original[role],scratch/(role+'.bin'),np)
                    for role in ('easting','northing','upward')]))
        train=mapper(reader,result['partitions']['final_training'],scratch/'train.bin',np)
        values=mapper(reader,result['channels'][-1]['data'],scratch/'values.bin',np)
        sources=mapper(reader,fit['sources'],scratch/'sources.bin',np)
        strengths=mapper(reader,fit['coefficients'],scratch/'strengths.bin',np)
        scales=mapper(reader,fit['column_scales'],scratch/'scales.bin',np)
        flags={ref['array_id']:ref for ref in _refs([result,request]) if 'array_id' in ref}
        qc=mapper(reader,flags[result['channels'][-1]['data']['mask_array_id']],scratch/'qc.bin',np)
        _check(not np.any(qc[train]))
        config=request['equivalent_sources']['source_geometries'][fit['selected_source_geometry_index']] if result['policy_epoch']==schema.POLICY_EPOCH else request['equivalent_sources']['source_geometry']
        # Training-only centroids, original signed floor/half-open convention
        # and sorted source IDs are reconstructed in disk storage independently.
        db=sqlite3.connect(scratch/'centroids.sqlite')
        try:
            db.execute('PRAGMA cache_size=-131072')
            db.execute('PRAGMA temp_store=FILE')
            db.execute("PRAGMA temp_store_directory='"+str(scratch).replace("'","''")+"'")
            db.execute('CREATE TABLE rows(pos INTEGER PRIMARY KEY,id TEXT,e REAL,n REAL,z REAL,be INTEGER,bn INTEGER)')
            ids=mapper(reader,original['row_id'],scratch/'ids.bin',np)
            for pos in train:
                pos=int(pos)
                e,north,z=map(float,xyz[pos])
                be=math.floor((e-config['origin_e_m'])/config['block_e_m'])
                bn=math.floor((north-config['origin_n_m'])/config['block_n_m'])
                db.execute('INSERT INTO rows VALUES (?,?,?,?,?,?,?)',(pos,bytes(ids[pos]).rstrip(b'\0').decode('ascii'),e,north,z,be,bn))
            db.execute('CREATE INDEX block_order ON rows(be,bn,id)')
            blocks=list(db.execute('SELECT DISTINCT be,bn FROM rows ORDER BY be,bn'))
            _check(len(blocks)==len(sources))
            minimum,maximum=db.execute('SELECT min(z),max(z) FROM rows').fetchone()
            for index,(be,bn) in enumerate(blocks):
                count=db.execute('SELECT count(*) FROM rows WHERE be=? AND bn=?',(be,bn)).fetchone()[0]
                expected=(math.fsum(e for e, in db.execute('SELECT e FROM rows WHERE be=? AND bn=? ORDER BY id',(be,bn)))/count,
                    math.fsum(north for north, in db.execute('SELECT n FROM rows WHERE be=? AND bn=? ORDER BY id',(be,bn)))/count,
                    minimum-fit['selected_depth_m'])
                _check(tuple(sources[index])==expected)
        finally:
            db.close()
        weighted=request['equivalent_sources']['weights_policy']=='admitted_inverse_variance'
        sigmas=[ref for ref in result['input']['arrays'] if ref['role']=='uncertainty']
        _check(len(sigmas)==1)
        sigma=mapper(reader,sigmas[0],scratch/'sigma.bin',np) if weighted else None
        operator=core.GlobalOperator(_readonly(np,xyz[train]),sources,_readonly(np,sigma[train]) if weighted else None,
            job_handle=job_handle)
        _check(np.allclose(operator.scales,scales,rtol=1e-12,atol=0))
        scaled_payload=reader.member(fit['scaled_coefficients'],524288)
        _check(fit['scaled_coefficients']['name']=='qr-final-scaled.bin' and len(scaled_payload)==8*len(sources))
        c=_readonly(np,np.frombuffer(scaled_payload,dtype='<f8'))
        p=hp.preconditioner(operator,fit['selected_damping'])
        _check(hp.content_sha256(operator.scales)==fit['solve']['column_scales_sha256'] and
            hp.content_sha256(p)==fit['solve']['preconditioner_sha256'] and
            hp.content_sha256(strengths)==fit['solve']['coefficients_sha256'] and
            hp.content_sha256(c)==fit['solve']['scaled_coefficients_sha256'] and
            np.array_equal(c/scales,strengths))
        diagnostics=hp.original_diagnostics(operator,_readonly(np,values[train]),fit['selected_damping'],c)
        _check(diagnostics['stationarity_relative']<=1e-9)
        for key in ('data_term','regularization_term','objective'):
            expected=fit['solve']['original_diagnostics'][key]
            _check(abs(diagnostics[key]-expected)<=1e-12*max(1.,abs(expected)))
        del operator,sigma
        outer=mapper(reader,result['partitions']['outer_validation'],scratch/'outer.bin',np)
        support=[ref for ref in result['geometry']['arrays'] if ref['role']=='qc_mask' and
            ref['shape']==[len(outer)] and ref['ordered_ids_sha256']==result['partitions']['outer_validation']['ordered_ids_sha256']]
        _check(len(support)==1)
        mask=mapper(reader,support[0],scratch/'support.bin',np)
        eligible=outer[mask==0]
        _check(len(eligible)==result['evaluation']['scored'] and not np.any(qc[eligible]))
        observed=mapper(reader,result['evaluation']['observed'],scratch/'observed.bin',np)
        predicted=mapper(reader,result['evaluation']['predicted'],scratch/'predicted.bin',np)
        ordered=sha256()
        for pos in eligible:
            ordered.update(bytes(ids[pos]).ljust(64,b'\0'))
        _check(ordered.hexdigest()==result['evaluation']['observed']['ordered_ids_sha256'] and np.array_equal(observed,values[eligible]))
        for interval in core._chunks(len(eligible),4096):
            recomputed=predict_global(_readonly(np,xyz[eligible[interval]]),sources,strengths,job_handle=job_handle)
            _check(np.allclose(recomputed,predicted[interval],rtol=1e-12,atol=1e-12))
        for number,grid in enumerate(result['grid']):
            config=grid['config']
            _check(config['plane_upward_m']>=maximum and np.all(sources[:,2]<config['plane_upward_m']))
            values_grid=mapper(reader,grid['values'],scratch/f'grid{number}.bin',np).reshape(-1)
            masks=mapper(reader,grid['support_mask'],scratch/f'mask{number}.bin',np).reshape(-1)
            for interval in core._chunks(len(values_grid),4096):
                indices=np.arange(interval.start,interval.stop)
                eligible_grid=(masks[interval]&np.uint32(0xffffffff^4096))==0
                positions=indices[eligible_grid]
                if len(positions):
                    query=_readonly(np,np.column_stack((config['origin_e_m']+(positions%config['nx'])*config['spacing_e_m'],
                        config['origin_n_m']+(positions//config['nx'])*config['spacing_n_m'],
                        np.full(len(positions),config['plane_upward_m']))))
                    recomputed=predict_global(query,sources,strengths,job_handle=job_handle)
                    _check(np.allclose(recomputed,values_grid[interval][eligible_grid],rtol=1e-12,atol=1e-12))
