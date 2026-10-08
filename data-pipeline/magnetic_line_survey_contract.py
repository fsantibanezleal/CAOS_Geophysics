"""Closed M03 streamed schemas, independent of the unchanged bounded contract."""
from __future__ import annotations

from copy import deepcopy
import math
import re

import magnetic_line_contract as base
from magnetic_line_survey import SurveyError


E, L, I, literal = base.E, base.L, base.I, base.literal
P = E(*base.PERMISSIONS)
V = E('pass', 'fail', 'unresolved', 'ineligible', 'nonconverged', 'cancelled', 'resource_refused')
DTYPES = ('float64', 'uint8', 'uint32', 'uint64', 'int64', 'ascii64', 'ascii30')
UNITS = ('m', 'nT', 'nT^2', 'nT*m', 'nT^-2', '1_per_m', 's', 'degree',
         'decimal_year', 'dimensionless', 'identity', 'UTC', 'cycles_per_m', 'rad_per_m')
ROLES = ('row_id', 'line_index', 'sensor_index', 'ordinal', 'utc', 'easting', 'northing',
         'upward', 'terrain_upward', 'clearance', 'magnetic', 'uncertainty', 'heading',
         'missing_mask', 'qc_mask', 'partition_index', 'source_position', 'source_block_member',
         'source_scale', 'coefficient', 'predicted', 'residual', 'reference_east',
         'reference_north', 'reference_up', 'reference_F', 'reference_date', 'navigation',
         'base', 'crossover', 'offset', 'grid_coordinate', 'grid_value', 'grid_mask',
         'spectrum_axis', 'spectrum_power', 'microlevel_removed', 'microlevel_retained')
TABLE_NAMES = ('line_definition', 'sensor_definition', 'aux_identity', 'operation_state',
               'offset_value', 'spatial_block', 'crossover_geometry', 'crossover_value',
               'source_block', 'candidate_fit', 'line_evaluation', 'level_component', 'sector_power')
TABLE_TYPES = dict(zip(TABLE_NAMES, ('LineDefinition', 'SensorDefinition', 'AuxIdentity',
    'SurveyState', 'OffsetValue', 'SpatialBlock', 'CrossoverGeometry', 'CrossoverValue',
    'SourceBlock', 'CandidateFit', 'LineEvaluation', 'LevelComponent', 'SectorPower')))
SCHEMAS = deepcopy(base.SCHEMAS)
SCHEMAS.update({
    'FileIdentity': dict(name='ID', bytes=I(1, 4194304), sha256='Hash'),
    'ArrayRef': dict(array_id='ID', role=E(*ROLES), shape=L(I(0, 16000000), 1, 2),
        dtype=E(*DTYPES), unit=E(*UNITS), chunk_rows=I(1, 4096), manifest='FileIdentity',
        ordered_ids_sha256='Hash', mask_array_id='?ID'),
    'TableRef': dict(table_id='ID', row_schema=E(*TABLE_NAMES), rows=I(1, 8000000), manifest='FileIdentity'),
    'PageIdentity': dict(sequence=I(0, 511), first_row=I(0, 15999999), rows=I(1, 16000000), file='FileIdentity'),
    'ChunkIdentity': dict(sequence=I(0, 32767), first_row=I(0, 15999999), rows=I(1, 4096),
        bytes=I(1, 8388608), sha256='Hash', name='ID'),
    'ManifestPage': dict(schema=literal('magnetic-line-manifest-page/1'), owner_id='ID',
        sequence=I(0, 511), entries=L('ChunkIdentity', 1, 2048)),
    'ArrayManifest': dict(schema=literal('magnetic-line-array-manifest/1'), array_id='ID',
        shape=L(I(0, 16000000), 1, 2), dtype=E(*DTYPES), unit=E(*UNITS),
        pages=L('PageIdentity', 0, 512), content_sha256='Hash'),
    'TableManifest': dict(schema=literal('magnetic-line-table-manifest/1'), table_id='ID',
        row_schema=E(*TABLE_NAMES), rows=I(1, 8000000), pages=L('PageIdentity', 1, 512), content_sha256='Hash'),
    'SurveyOriginal': dict(base.SCHEMAS['Original'], csv_bytes=I(1, 4294967296)),
    'SurveyInput': dict(base.SCHEMAS['Sidecar'], schema=literal('magnetic-line-survey-input/1'),
        original='SurveyOriginal', acquisition='SurveyAcquisition', channel_state=L('SurveyState', 0, 64),
        reference='?SurveyReference', subset='?SurveySubset', arrays=L('ArrayRef', 1, 128),
        auxiliaries=L('SurveyAux', 0, 16)),
    'SurveyAcquisition': dict(base.SCHEMAS['Acquisition'], line_dictionary='TableRef', sensor_dictionary='TableRef'),
    'SurveySubset': dict(base.SCHEMAS['Subset'], parent_row_count=I(1, 8000000), selected_ids='ArrayRef'),
    'SurveyState': dict(base.SCHEMAS['StateRecord']),
    'SurveyOperationRequest': dict(base.SCHEMAS['OperationRequest']),
    'SurveyAux': dict(aux_id='ID', kind=E('navigation', 'base', 'calibration', 'independent_offsets', 'reference'),
        identity='AuxIdentity', payload=('aux_payload',)),
    'SurveyNavigation': dict(schema=literal('magnetic-line-navigation-stream/1'), identity='AuxIdentity',
        clock='Clock', coordinates='Coordinates', row_ids='ArrayRef', utc='ArrayRef', line_index='ArrayRef', xyz='ArrayRef'),
    'SurveyBase': dict(schema=literal('magnetic-line-base-stream/1'), identity='AuxIdentity', clock='Clock',
        station_id='ID', quantity=literal('scalar_total_intensity'), unit=literal('nT'), utc='ArrayRef', intensity='ArrayRef'),
    'SurveyCalibration': dict(base.SCHEMAS['CalibrationIdentity'], calibration_row_ids='ArrayRef'),
    'SurveyOffsets': dict(base.SCHEMAS['IndependentOffsets'], calibration='SurveyCalibration', values='TableRef'),
    'SurveyReference': dict(base.SCHEMAS['Reference'], epoch='SurveyEpoch', vector_east_nT='ArrayRef',
        vector_north_nT='ArrayRef', vector_up_nT='ArrayRef', scalar_F_nT='ArrayRef'),
    'SurveyEpoch': dict(base.SCHEMAS['ReferenceEpoch'], row_date_decimal_year='?ArrayRef'),
    'LagParameters': dict(base.SCHEMAS['LagParameters'], navigation='SurveyNavigation'),
    'DiurnalParameters': dict(base.SCHEMAS['DiurnalParameters'], base='SurveyBase'),
    'HeadingParameters': dict(base.SCHEMAS['HeadingParameters'], calibration='SurveyCalibration'),
    'MainFieldParameters': dict(base.SCHEMAS['MainFieldParameters'], evaluated_reference='SurveyReference'),
    'RereferenceParameters': dict(base.SCHEMAS['RereferenceParameters'], old_reference='SurveyReference', new_reference='SurveyReference'),
    'LevelingParameters': dict(base.SCHEMAS['LevelingParameters'], heldout_calibration='?SurveyOffsets'),
    'MicrolevelParameters': dict(base.SCHEMAS['MicrolevelParameters'], spectrum_policy='SurveySpectrum'),
    'SurveyRequest': dict(base.SCHEMAS['Request'], schema=literal('magnetic-line-survey-request/1'),
        operations=L('SurveyOperationRequest', 0, 6), grid='SurveyGrid', equivalent_sources='SurveySources',
        split='SurveySplit', spectrum='?SurveySpectrum', profile=literal('m03-offline-stream/1'), solver='SolverPolicy'),
    'SurveySources': dict(base.SCHEMAS['EquivalentSourcesConfig'], source_geometry='SurveySourceGeometry', weight_multiplier=literal(1)),
    'SurveySourceGeometry': dict(base.SCHEMAS['SourceGeometry'],
        version=literal('half_open_training_blocks_stream/1'), max_sources=I(1, 65536)),
    'SurveySplit': dict(base.SCHEMAS['SplitConfig'], version=literal('full_lines_buffered_ties_stream/1'),
        outer_line_ids='ArrayRef', heldout_blocks='TableRef', anchor_line_ids='?ArrayRef', inner_folds=L('SurveyFold', 3, 3)),
    'SurveyFold': dict(base.SCHEMAS['InnerFold'], validation_line_ids='ArrayRef', validation_blocks='TableRef'),
    'SurveyGrid': dict(base.SCHEMAS['GridConfig'], nx=I(2, 1048576), ny=I(2, 1048576), boundary_policy='SurveyBoundary'),
    'SurveyBoundary': dict(base.SCHEMAS['BoundaryPolicy'], pad_e_cells=I(0, 1048576), pad_n_cells=I(0, 1048576)),
    'SurveySpectrum': dict(base.SCHEMAS['SpectrumConfig'], rectangle='SurveyRectangle'),
    'SurveyRectangle': dict(e_start=I(0, 1048575), n_start=I(0, 1048575), nx=I(2, 1048576), ny=I(2, 1048576)),
    'SolverPolicy': dict(schema=literal('m03-lsmr-policy/1'), atol=literal(1e-12), btol=literal(1e-12),
        conlim=literal(100000000), maxiter=literal(2000), stationarity_relative=literal(1e-9),
        chunk_rows=literal(4096), chunk_sources=literal(128), threads=literal(1), initial_guess=literal('zero'),
        damping_map=literal('sqrt_lambda'), stop_policy=literal('code_and_independent_gradient')),
    'CapacityRecord': dict(profile=literal('m03-offline-stream/1'), rows=I(1, 8000000), sources=I(1, 65536),
        auxiliary_rows=I(0, 16000000), crossover_candidates=I(0, 8000000), exported_cells=I(0, 1048576),
        fft_cells=I(0, 4194304), raw_bytes=I(1, 4294967296), auxiliary_bytes=I(0, 4294967296),
        fit_buffer_bytes=I(0, 4294967296), geometry_buffer_bytes=I(0, 4294967296), transform_buffer_bytes=I(0, 4294967296),
        scratch_bound_bytes=I(0, 34359738368), kernel_pair_bound=I(0, 10**15), resource_state=E('unmeasured', 'measured_pass', 'refused')),
    'GeometrySeal': dict(schema=literal('magnetic-line-survey-geometry/1'), original='SurveyOriginal',
        coordinates_sha256='Hash', acquisition_sha256='Hash', request_geometry_sha256='Hash', rows=I(1, 8000000),
        lines=I(1, 65536), sensors=I(1, 4), segments=I(0, 7999999), crossover_candidates=I(0, 8000000),
        source_counts=L(I(1, 65536), 4, 4), arrays=L('ArrayRef', 1, 128), dictionaries=L('TableRef', 1, 16),
        capacity='CapacityRecord', value_access=literal('not_opened')),
    'SourceBlock': dict(row_index=I(0, 7999999), block_e=I(-2147483648, 2147483647),
        block_n=I(-2147483648, 2147483647), source_index=I(0, 65535)),
    'CrossoverGeometry': dict(crossover_id='ID', flight_segment_id='ID', tie_segment_id='ID',
        a='?F64', b='?F64', easting_m='?F64', northing_m='?F64', height_difference_m='?F64',
        time_separation_s='?Nonneg', disposition=E('admitted', 'rejected'), reasons=L('CrossoverReason', 0, 16),
        shared_endpoint_group_id='?ID', constraint_representative='?ID', tolerance='IntersectionTolerance'),
    'IntersectionTolerance': dict(coordinate_m='Pos', determinant_m2='?Pos', sine_dimensionless='?Pos',
        parameter_dimensionless='?Pos', matrix_residual_m='?Nonneg'),
    'TimingRecord': dict(cpu_s='Nonneg', wall_s='Nonneg', peak_rss_bytes=I(0, 2**63-1),
        peak_committed_bytes=I(0, 2**63-1), scratch_bytes=I(0, 2**63-1), stop_cpu_s='?Nonneg', stop_wall_s='?Nonneg'),
    'SolverReceipt': dict(istop=I(0, 7), iterations=I(0, 2000), normr_estimate='Nonneg', normar_estimate='Nonneg',
        norma_estimate='Nonneg', conda_estimate='Nonneg', normx_estimate='Nonneg', data_term='Nonneg',
        regularization_term='Nonneg', objective='Nonneg', objective_unit=E('nT^2', 'dimensionless'),
        stationarity_inf='Nonneg', stationarity_relative='Nonneg', gradient_denominator='Nonneg',
        coefficient_error_bound_nT='Nonneg', operator_forward_calls=I(0, 10000), operator_adjoint_calls=I(0, 10000),
        timing='TimingRecord', verdict=E('pass', 'nonconverged', 'resource_refused', 'cancelled')),
    'SurveyGate': dict(gate_id='ID', verdict=V, evidence_sha256='?Hash', reason='?Text'),
    'SurveyVerdict': dict(overall=V, gates=L('SurveyGate', 1, 64), numerical_success='Bool', reasons=L('Text', 0, 64)),
    'CandidateFit': dict(fold_id='ID', depth_m='Pos', damping='Pos', solve='SolverReceipt', scored=I(0, 8000000),
        excluded=I(0, 8000000), rmse_nT='?Nonneg', verdict='SurveyVerdict'),
    'InputReceipt': dict(dataset_sha256='Hash', original='SurveyOriginal', metadata='FileIdentity',
        arrays=L('ArrayRef', 1, 128), auxiliary_identities=L('AuxIdentity', 0, 16)),
    'InventoryReceipt': dict(original_rows=I(1, 8000000), retained=I(0, 8000000), invalid=I(0, 8000000),
        excluded=I(0, 8000000), disposition='ArrayRef', reasons='ArrayRef', flags='ArrayRef'),
    'ChannelReceipt': dict(channel_id='ID', kind=E('scalar_total_intensity', 'scalar_total_field_anomaly'),
        role=E('original', 'derived', 'diagnostic_removed', 'diagnostic_retained'), data='ArrayRef',
        state=L('SurveyState', 0, 64), parent_sha256='?Hash', reference_receipt_sha256='?Hash'),
    'FoldReceipt': dict(fold_id='ID', training='ArrayRef', validation='ArrayRef', exclusions='ArrayRef', source_members='ArrayRef'),
    'PartitionReceipt': dict(seal_sha256='Hash', final_training='ArrayRef', outer_validation='ArrayRef',
        exclusions='ArrayRef', inner=L('FoldReceipt', 3, 3), evaluation_count=I(0, 1)),
    'FitReceipt': dict(solver='SolverPolicy', candidates='TableRef', selected_depth_m='Pos', selected_damping='Pos',
        sources='ArrayRef', column_scales='ArrayRef', coefficients='ArrayRef', solve='SolverReceipt', fit_count=I(1, 26)),
    'SurveyGridReceipt': dict(grid_id='ID', config='SurveyGrid', quantity=literal('scalar_total_field_anomaly'),
        easting_axis='ArrayRef', northing_axis='ArrayRef', values='ArrayRef', support_mask='ArrayRef',
        role=E('fitted_plane', 'continued_plane', 'microlevel_diagnostic')),
    'SurveySpectrumReceipt': dict(config='SurveySpectrum', power='ArrayRef', east_axis='ArrayRef', north_axis='ArrayRef',
        window_mean_square='Pos', mean_removed_nT='F64', parseval_sum_nT2='Nonneg', sectors='?TableRef', microlevel='?SurveyMicrolevelReceipt'),
    'SurveyMicrolevelReceipt': dict(parameters='MicrolevelParameters', transfer='ArrayRef', removed='ArrayRef', retained='ArrayRef',
        removed_power_nT2='Nonneg', retained_power_nT2='Nonneg', clipped_removed='?ArrayRef', geological_preservation_claim=literal(False)),
    'SurveyLevelingReceipt': dict(offsets='TableRef', components='TableRef', before_residuals='ArrayRef', after_residuals='ArrayRef',
        uncalibrated_line_ids='ArrayRef', scope=literal('training_only'), gauge_policy=literal('lexicographic_first_tie_per_component')),
    'LevelComponent': dict(component_id='ID', line_ids='ArrayRef', gauge_line_id='ID', rank=I(0, 65536),
        singular_values='?ArrayRef', condition='?Pos', absolute_datum=literal(False),
        rank_method=literal('incidence_connected_component'), rank_receipt_sha256='Hash'),
    'SectorPower': dict(sector_id='ID', bin_count=I(0, 4194304), power_nT2='Nonneg'),
    'EvaluationReceipt': dict(observed='ArrayRef', predicted='ArrayRef', residual='ArrayRef', scored=I(0, 8000000),
        excluded=I(0, 8000000), coverage='Nonneg', signal_rms_nT='?Nonneg', rmse_nT='?Nonneg',
        per_line='TableRef', comparison='?ComparisonReceipt', verdict='SurveyVerdict'),
    'LineEvaluation': dict(line_id='ID', scored=I(0, 8000000), excluded=I(0, 8000000), rmse_nT='?Nonneg', signal_rms_nT='?Nonneg'),
    'ComparisonReceipt': dict(provider_identity='AuxIdentity', quantity='Quantity', coordinates='Coordinates',
        values='ArrayRef', residual='ArrayRef', rmse_nT='?Nonneg', verdict='SurveyVerdict'),
    'SurveyMember': dict(role='ID', name='ID', bytes=I(0, 34359738368), sha256='?Hash', permission=P,
        disposition=E('included', 'denied', 'unresolved'), reason='Text'),
    'SurveyResult': dict(schema=literal('magnetic-line-survey-result/1'), run_id='ID',
        lane=E('local_synthetic', 'local_user', 'field_provider_product'), input='InputReceipt', request='FileIdentity',
        environment='Environment', geometry='GeometrySeal', inventory='InventoryReceipt', channels=L('ChannelReceipt', 1, 8),
        crossovers='?TableRef', leveling='?SurveyLevelingReceipt', partitions='PartitionReceipt', fit='FitReceipt',
        grid=L('SurveyGridReceipt', 1, 3), spectrum='?SurveySpectrumReceipt', evaluation='EvaluationReceipt',
        rights='Rights', artifacts=L('SurveyMember', 0, 192), verdict='SurveyVerdict'),
})
SCHEMAS['CrossoverValue'] = dict(SCHEMAS['CrossoverGeometry'], flight_minus_tie_nT='?F64', difference_variance_nT2='?Nonneg')


def typed(value, spec, parent=None):
    """No defaults, arbitrary mappings, boolean-as-number or floating underflow."""
    if type(spec) is str and spec.startswith('?'):
        return None if value is None else typed(value, spec[1:], parent)
    if type(spec) is tuple:
        tag = spec[0]
        if tag == 'parameters':
            if value is None and spec[1]:
                return None
            if type(parent) is not dict or parent.get('operation') not in base.PARAMETERS:
                raise SurveyError('invalid_contract', 'ingest')
            return validate(base.PARAMETERS[parent['operation']], value)
        if tag == 'aux_payload':
            names = dict(navigation='SurveyNavigation', base='SurveyBase', calibration='SurveyCalibration',
                         independent_offsets='SurveyOffsets', reference='SurveyReference')
            return validate(names[parent['kind']], value)
        if tag == 'list':
            if type(value) is not list or not spec[2] <= len(value) <= spec[3]:
                raise SurveyError('invalid_contract', 'ingest')
            return [typed(x, spec[1]) for x in value]
        if tag == 'nullable':
            return None if value is None else typed(value, spec[1])
        if tag == 'rows':
            raise SurveyError('invalid_contract', 'ingest')
    if spec == 'Bool':
        if type(value) is not bool:
            raise SurveyError('invalid_contract', 'ingest')
        return value
    if spec == 'CrossoverReason':
        from magnetic_lines import CROSSOVER_REASONS
        return base._type(value, E(*CROSSOVER_REASONS), 'survey', 0)
    if type(spec) is str and spec in SCHEMAS:
        return validate(spec, value)
    if spec == 'Environment':
        # The environment object is the original closed, measured engine receipt.
        from magnetic_lines import _result_type
        return _result_type(value, 'Environment', 'environment', 1)
    decoded = base._type(value, spec, 'survey', 0)
    if spec in ('F64', 'Pos', 'Nonneg') and decoded == 0 and value != 0:
        raise SurveyError('invalid_contract', 'ingest')
    return decoded


def validate(name, value):
    try:
        table = SCHEMAS[name]
        if type(value) is not dict or set(value) != set(table):
            raise SurveyError('invalid_contract', 'ingest')
        result = {k: typed(value[k], spec, value) for k, spec in table.items()}
        conditions(name, result)
        return result
    except SurveyError:
        raise
    except (base.MagneticContractError, KeyError, TypeError, ValueError, OverflowError):
        raise SurveyError('invalid_contract', 'ingest') from None


def _ref(value, role, dtype, unit, shape=None):
    if value['role'] != role or value['dtype'] != dtype or value['unit'] != unit or \
       (shape is not None and value['shape'] != shape):
        raise SurveyError('invalid_contract', 'ingest')


def conditions(name, v):
    if name in base.SCHEMAS and name not in ('LagParameters', 'HeadingParameters', 'MainFieldParameters',
                                            'RereferenceParameters', 'LevelingParameters'):
        base._conditional(name, v, 'survey')
    if name in ('ArrayRef', 'TableRef'):
        identifier = v['array_id' if name == 'ArrayRef' else 'table_id']
        if len(identifier) > 32 or v['manifest']['name'] != ('array-' if name == 'ArrayRef' else 'table-') + identifier + '.json':
            raise SurveyError('invalid_contract', 'ingest')
    if name == 'FileIdentity' and (v['name'] in ('.', '..') or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', v['name'])):
        raise SurveyError('invalid_contract', 'ingest')
    if name == 'ArrayRef':
        if math.prod(v['shape']) > 16000000 or (0 in v['shape'] and len(v['shape']) != 1) or v['role'] in ('crossover', 'offset'):
            raise SurveyError('invalid_contract', 'ingest')
        fixed = dict(row_id=('ascii64', 'identity'), line_index=('uint32', 'identity'),
                     sensor_index=('uint8', 'identity'), ordinal=('uint64', 'identity'), utc=('ascii30', 'UTC'),
                     missing_mask=('uint32', 'identity'), qc_mask=('uint32', 'identity'), grid_mask=('uint32', 'identity'),
                     partition_index=('uint64', 'identity'), source_block_member=('uint64', 'identity'),
                     source_scale=('float64', '1_per_m'), coefficient=('float64', 'nT*m'),
                     source_position=('float64', 'm'), reference_date=('float64', 'decimal_year'),
                     navigation=('float64', 'm'), grid_coordinate=('float64', 'm'),
                     heading=('float64', 'degree'), spectrum_power=('float64', 'nT^2'))
        fixed.update({r: ('float64', 'm') for r in
                      ('easting', 'northing', 'upward', 'terrain_upward', 'clearance')})
        fixed.update({r: ('float64', 'nT') for r in
                      ('magnetic', 'uncertainty', 'predicted', 'residual', 'reference_east',
                       'reference_north', 'reference_up', 'reference_F', 'base', 'grid_value',
                       'microlevel_removed', 'microlevel_retained')})
        if v['role'] in fixed and (v['dtype'], v['unit']) != fixed[v['role']]:
            raise SurveyError('invalid_contract', 'ingest')
        if v['role'] in ('source_position', 'navigation', 'grid_coordinate') and (len(v['shape']) != 2 or v['shape'][1] != 3):
            raise SurveyError('invalid_contract', 'ingest')
        if v['role'] == 'source_block_member' and (len(v['shape']) != 2 or v['shape'][1] != 2):
            raise SurveyError('invalid_contract', 'ingest')
        if v['role'] == 'spectrum_axis' and (v['dtype'] != 'float64' or
              v['unit'] not in ('cycles_per_m', 'rad_per_m')):
            raise SurveyError('invalid_contract', 'ingest')
        matrix_roles = ('source_position', 'source_block_member', 'navigation', 'grid_coordinate',
                        'grid_value', 'grid_mask', 'spectrum_power', 'microlevel_removed', 'microlevel_retained')
        if len(v['shape']) == 2 and v['role'] not in matrix_roles:
            raise SurveyError('invalid_contract', 'ingest')
        if not v['shape'][0] and v['role'] not in ('row_id', 'partition_index'):
            raise SurveyError('invalid_contract', 'ingest')
        if v['role'] in ('source_position', 'source_scale', 'coefficient') and v['shape'][0] > 65536:
            raise SurveyError('resource_refused', 'seal')
        if v['role'] == 'source_block_member' and v['shape'][0] > 8000000:
            raise SurveyError('resource_refused', 'seal')
        if v['role'] in ('grid_value', 'grid_mask') and (len(v['shape']) != 2 or math.prod(v['shape']) > 1048576):
            raise SurveyError('resource_refused', 'seal')
        if v['role'] == 'grid_coordinate' and v['shape'][0] > 1048576:
            raise SurveyError('resource_refused', 'seal')
    if name == 'TableRef':
        limit = {'sensor_definition': 4, 'aux_identity': 16, 'operation_state': 64, 'candidate_fit': 24, 'sector_power': 16}.get(v['row_schema'],
                  8000000 if v['row_schema'] in ('crossover_geometry', 'crossover_value', 'source_block') else 65536)
        if v['rows'] > limit:
            raise SurveyError('invalid_contract', 'ingest')
    if name == 'SurveyAcquisition':
        if v['line_dictionary']['row_schema'] != 'line_definition' or v['sensor_dictionary']['row_schema'] != 'sensor_definition':
            raise SurveyError('invalid_contract', 'ingest')
    if name == 'SurveySourceGeometry':
        base._conditional('SourceGeometry', v, 'survey')
    if name == 'SurveySources':
        base._conditional('EquivalentSourcesConfig', v, 'survey')
    if name == 'SurveyEpoch':
        base._conditional('ReferenceEpoch', v, 'survey')
        if v['row_date_decimal_year'] is not None:
            _ref(v['row_date_decimal_year'], 'reference_date', 'float64', 'decimal_year')
    if name == 'SurveyReference':
        igrf = v['kind'] == 'igrf_evaluated'
        if not 0 < v['direction_tolerance_deg'] <= .5 or \
           (igrf and (v['model_generation'] != 'IGRF14' or v['coefficients_sha256'] is None)) or \
           (not igrf and (v['model_generation'] != 'authored_constant' or v['coefficients_sha256'] is not None)):
            raise SurveyError('invalid_contract', 'ingest')
        shape = v['scalar_F_nT']['shape']
        for key, role in [('vector_east_nT', 'reference_east'), ('vector_north_nT', 'reference_north'),
                          ('vector_up_nT', 'reference_up'), ('scalar_F_nT', 'reference_F')]:
            _ref(v[key], role, 'float64', 'nT', shape)
    if name in ('SurveyState', 'SurveyOperationRequest'):
        if name == 'SurveyState':
            base._conditional('StateRecord', v, 'survey')
    if name == 'SurveyGrid':
        if v['nx'] * v['ny'] > 1048576:
            raise SurveyError('resource_refused', 'seal')
        b = v['boundary_policy']
        if b['pad_e_cells'] > 2*v['nx'] or b['pad_n_cells'] > 2*v['ny'] or \
           (v['nx']+2*b['pad_e_cells'])*(v['ny']+2*b['pad_n_cells']) > 4194304:
            raise SurveyError('resource_refused', 'seal')
    if name == 'SurveyRectangle' and v['nx']*v['ny'] > 1048576:
        raise SurveyError('resource_refused', 'seal')
    if name == 'SurveySplit':
        if v['minimum_supported_fraction'] > 1 or len({f['fold_id'] for f in v['inner_folds']}) != 3:
            raise SurveyError('invalid_contract', 'ingest')
        for key in ('outer_line_ids', 'anchor_line_ids'):
            if v[key] is not None:
                _ref(v[key], 'row_id', 'ascii64', 'identity')
        if v['heldout_blocks']['row_schema'] != 'spatial_block':
            raise SurveyError('invalid_contract', 'ingest')
    if name == 'SurveyFold':
        _ref(v['validation_line_ids'], 'row_id', 'ascii64', 'identity')
        if v['validation_blocks']['row_schema'] != 'spatial_block':
            raise SurveyError('invalid_contract', 'ingest')
    if name == 'SurveyRequest':
        operations = [o['operation'] for o in v['operations']]
        if operations != sorted(set(operations), key=base.OPERATIONS.index) or \
           ('main_field' in operations and 'rereference' in operations) or \
           v['split']['buffer_m'] < v['grid']['support_radius_m']:
            raise SurveyError('invalid_contract', 'ingest')
    if name == 'InventoryReceipt' and v['retained'] + v['invalid'] + v['excluded'] != v['original_rows']:
        raise SurveyError('invalid_contract', 'ingest')
    if name == 'SurveyVerdict':
        if len({g['gate_id'] for g in v['gates']}) != len(v['gates']) or \
           (v['overall'] == 'pass' and any(g['verdict'] != 'pass' for g in v['gates'])):
            raise SurveyError('invalid_contract', 'ingest')
    if name == 'SolverReceipt' and (v['objective'] != v['data_term'] + v['regularization_term'] or \
           (v['verdict'] == 'pass' and (v['istop'] not in (0, 1, 2, 4, 5) or v['conda_estimate'] >= 1e8 or v['stationarity_relative'] > 1e-9))):
        raise SurveyError('invalid_contract', 'ingest')
    if name == 'SurveyMember':
        included = v['disposition'] == 'included'
        if (included and (v['permission'] != 'allowed' or v['sha256'] is None)) or \
           (not included and (v['bytes'] != 0 or v['sha256'] is not None)):
            raise SurveyError('invalid_contract', 'ingest')


def read_document(path, name):
    try:
        raw = base.read_bounded(path, 2097152)
        return raw, validate(name, base.strict_json(raw))
    except base.MagneticContractError:
        raise SurveyError('invalid_contract', 'ingest') from None
