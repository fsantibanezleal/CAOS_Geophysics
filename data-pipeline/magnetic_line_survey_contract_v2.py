"""Explicit new representation epoch and separately tagged resolution-v2 policy.

The original contract module, old ArrayRef roles, numerical policy and historical
receipts are unchanged. New readers may verify old members, never reinterpret
an old grid-coordinate descriptor as a metre axis or weaken a solver criterion.
"""
from __future__ import annotations

from copy import deepcopy
import math

import magnetic_line_contract as base
import magnetic_line_survey_contract as v1
from magnetic_line_survey import SurveyError

E, L, I, literal = base.E, base.L, base.I, base.literal
ROLES = (*v1.ROLES, 'grid_axis', 'microlevel_transfer')
TABLE_NAMES = (*v1.TABLE_NAMES, 'candidate_fit_v2')
SCHEMAS = deepcopy(v1.SCHEMAS)
SCHEMAS.update({
    'ArrayRef': dict(v1.SCHEMAS['ArrayRef'], role=E(*ROLES)),
    'ArrayManifest': dict(v1.SCHEMAS['ArrayManifest'], schema=literal('magnetic-line-array-manifest/2')),
    'TableRef': dict(v1.SCHEMAS['TableRef'], row_schema=E(*TABLE_NAMES)),
    'TableManifest': dict(v1.SCHEMAS['TableManifest'], schema=literal('magnetic-line-table-manifest/2'), row_schema=E(*TABLE_NAMES)),
    'CandidateFit': dict(v1.SCHEMAS['CandidateFit'], source_geometry_index=I(0,3)),
    'SurveySources': {key: spec for key,spec in v1.SCHEMAS['SurveySources'].items() if key!='source_geometry'},
    'SurveySplit': dict(v1.SCHEMAS['SurveySplit'], tuning_candidate_order=literal('width_descending_then_depth_then_damping_ascending')),
    'SurveyRequest': dict(v1.SCHEMAS['SurveyRequest'], schema=literal('magnetic-line-survey-request/2'), profile=literal('m03-offline-stream/2')),
    'SurveyInput': dict(v1.SCHEMAS['SurveyInput'], schema=literal('magnetic-line-survey-input/2')),
    'CapacityRecord': dict(v1.SCHEMAS['CapacityRecord'], profile=literal('m03-offline-stream/2')),
    'FoldSourceMap': dict(source_geometry_index=I(0,3), fold_id='ID', training='ArrayRef', sources='ArrayRef', source_members='ArrayRef'),
    'FitReceipt': dict(v1.SCHEMAS['FitReceipt'], fit_count=I(97,98), selected_source_geometry_index=I(0,3)),
    'SurveyResult': dict(v1.SCHEMAS['SurveyResult'], schema=literal('magnetic-line-survey-result/2'),
        policy_epoch=E('fixed_basis_v1','resolution_v2'), geometry=('policy_geometry',), fit=('policy_fit',)),
})
SCHEMAS['SurveySources'].update(source_geometries=L('SurveySourceGeometry',4,4),
    candidate_order=literal('width_descending_then_depth_then_damping_ascending'),
    tie_break=literal('larger_damping_then_depth_then_block_width'))
SCHEMAS['GeometrySeal'] = {key:spec for key,spec in v1.SCHEMAS['GeometrySeal'].items() if key!='source_counts'}
SCHEMAS['GeometrySeal'].update(schema=literal('magnetic-line-survey-geometry/2'),
    source_counts_by_geometry=L(L(I(1,65536),4,4),4,4),source_maps=L('FoldSourceMap',16,16))


def typed(value, spec, parent=None):
    if type(spec) is str and spec.startswith('?'):
        return None if value is None else typed(value,spec[1:],parent)
    if type(spec) is tuple:
        if spec[0] in ('policy_geometry','policy_fit'):
            if parent['policy_epoch']=='fixed_basis_v1':
                return v1.validate('GeometrySeal' if spec[0]=='policy_geometry' else 'FitReceipt',value)
            return validate('GeometrySeal' if spec[0]=='policy_geometry' else 'FitReceipt',value)
        if spec[0]=='parameters':
            if value is None and spec[1]:
                return None
            return validate(base.PARAMETERS[parent['operation']],value)
        if spec[0]=='aux_payload':
            return validate(dict(navigation='SurveyNavigation',base='SurveyBase',calibration='SurveyCalibration',
                independent_offsets='SurveyOffsets',reference='SurveyReference')[parent['kind']],value)
        if spec[0]=='list':
            if type(value) is not list or not spec[2] <= len(value) <= spec[3]:
                raise SurveyError('invalid_contract','ingest')
            return [typed(item,spec[1]) for item in value]
        if spec[0]=='nullable':
            return None if value is None else typed(value,spec[1])
    if type(spec) is str and spec in SCHEMAS:
        return validate(spec,value)
    return v1.typed(value,spec,parent)


def validate(name, value):
    try:
        table = SCHEMAS[name]
        if type(value) is not dict or set(value)!=set(table):
            raise SurveyError('invalid_contract','ingest')
        result = {key:typed(value[key],spec,value) for key,spec in table.items()}
        conditions(name,result)
        return result
    except SurveyError:
        raise
    except (base.MagneticContractError, KeyError, TypeError, ValueError, OverflowError):
        raise SurveyError('invalid_contract','ingest') from None


def conditions(name, value):
    if name=='SurveyGrid':
        boundary=value['boundary_policy']
        pe,pn=boundary['pad_e_cells'],boundary['pad_n_cells']
        if value['nx']*value['ny']>1048576 or 2*pe>value['nx'] or 2*pn>value['ny'] or \
           (value['nx']+2*pe)*(value['ny']+2*pn)>4194304:
            raise SurveyError('resource_refused','seal')
        if boundary['mode']=='periodic' and (pe or pn or boundary['detrend']!='none' or boundary['taper']!='none'):
            raise SurveyError('invalid_contract','ingest')
        return
    if name=='ArrayRef':
        role, shape = value['role'], value['shape']
        if role in ('spectrum_power','microlevel_removed','microlevel_retained') and \
           (len(shape)!=2 or math.prod(shape)>4194304):
            raise SurveyError('resource_refused','seal')
        if role not in ('grid_axis','microlevel_transfer','navigation'):
            v1.conditions(name,value)
            return
        identifier = value['array_id']
        if len(identifier)>32 or value['manifest']['name']!='array-'+identifier+'.json' or \
           value['dtype']!='float64' or not all(shape):
            raise SurveyError('invalid_contract','ingest')
        if role=='grid_axis' and (len(shape)!=1 or shape[0]>1048576 or value['unit']!='m' or value['mask_array_id'] is not None):
            raise SurveyError('invalid_contract','ingest')
        if role=='microlevel_transfer' and (len(shape)!=2 or math.prod(shape)>4194304 or value['unit']!='dimensionless' or
                                           value['mask_array_id'] is not None):
            raise SurveyError('invalid_contract','ingest')
        if role=='navigation' and (len(shape)!=2 or shape[1]!=3 or shape[0]>16000000 or value['unit']!='m'):
            raise SurveyError('invalid_contract','ingest')
        return
    if name=='TableRef' and value['row_schema']=='candidate_fit_v2':
        if value['rows']!=96 or len(value['table_id'])>32 or value['manifest']['name']!='table-'+value['table_id']+'.json':
            raise SurveyError('invalid_contract','ingest')
        return
    if name=='SurveySources':
        geometries=value['source_geometries']
        if [(item['block_e_m'],item['block_n_m']) for item in geometries]!=[(width,width) for width in (400.,200.,100.,50.)] or \
           len({(item['origin_e_m'],item['origin_n_m']) for item in geometries})!=1 or \
           value['depth_candidates_m']!=[200.,500.] or value['damping_candidates']!=[.0001,.01,1.,100.]:
            raise SurveyError('invalid_contract','ingest')
        # The original weight/unit/depth/lambda checks, without substituting
        # the new order literal into a v1 parser or changing its source geometry.
        original=dict(value,source_geometry=geometries[0],candidate_order='depth_then_damping_ascending',
                      tie_break='larger_damping_then_depth')
        del original['source_geometries']
        v1.validate('SurveySources',original)
        return
    if name=='SurveySplit':
        original=dict(value,tuning_candidate_order='depth_then_damping_ascending')
        # This check only verifies inherited constraints; it does not rewrite
        # the externally stored request or its version/hash.
        v1.conditions(name,original)
        return
    if name=='SurveyRequest':
        operations=[operation['operation'] for operation in value['operations']]
        if operations!=sorted(set(operations),key=base.OPERATIONS.index) or \
           'main_field' in operations and 'rereference' in operations or value['split']['buffer_m']<value['grid']['support_radius_m']:
            raise SurveyError('invalid_contract','ingest')
        return
    if name=='GeometrySeal':
        maps=value['source_maps']
        if len({(item['source_geometry_index'],item['fold_id']) for item in maps})!=16:
            raise SurveyError('invalid_contract','ingest')
        folds={item['fold_id'] for item in maps}
        if len(folds)!=4:
            raise SurveyError('invalid_contract','ingest')
        for index in range(4):
            if {item['fold_id'] for item in maps if item['source_geometry_index']==index}!=folds:
                raise SurveyError('invalid_contract','ingest')
        for item in maps:
            if item['training']['role']!='partition_index' or item['sources']['role']!='source_position' or \
               item['source_members']['role']!='source_block_member' or \
               item['source_members']['shape']!=[item['training']['shape'][0],2] or \
               any(item[key] not in value['arrays'] for key in ('training','sources','source_members')):
                raise SurveyError('invalid_contract','ingest')
        if value['capacity']['rows']!=value['rows'] or value['capacity']['sources']!=max(
                count for counts in value['source_counts_by_geometry'] for count in counts) or \
           value['capacity']['crossover_candidates']!=value['crossover_candidates']:
            raise SurveyError('custody_mismatch','seal')
        return
    if name in ('CandidateFit','FitReceipt','CapacityRecord','SurveyResult','ArrayManifest','TableManifest','FoldSourceMap','SurveyInput'):
        # Closed fields and nested constraints above are necessary, not full
        # cross-object/scientific verification. The owner validator must prove
        # every map/count/candidate/permission before assembling a result.
        return
    v1.conditions(name,value)
