"""Owner original/aligned geometry seal: all original rows, no measurement decoding.

This seal records geometry eligibility, not predictive or measured host
acceptance. Lag requests must run the independent navigation stage first;
an original-coordinate seal is never relabelled as lag-corrected geometry.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_io as io
from magnetic_line_survey_geometry import geometry_index, plan_partitions
from magnetic_line_survey_crossovers import geometry_crossovers
from magnetic_line_survey_support import plan_support


def _metadata(root, inspection, metadata, request, *, allow_navigation=False):
    schema.validate('SurveyInput', metadata)
    schema.validate('SurveyRequest', request)
    if metadata['source_kind'] not in ('field_acquisition','original_synthetic_acquisition') or \
       (metadata['source_kind']=='original_synthetic_acquisition') != (metadata['authored_control'] is not None) or \
       metadata['rights']['private_processing'] != 'allowed':
        raise core.SurveyError('metadata_ineligible','seal')
    acq,policy = metadata['acquisition'],request['geometry_policy']
    datum = metadata['coordinates']['vertical_datum']
    if datum is None or request['grid']['datum'] != datum or \
       policy['max_segment_gap_m'] > acq['max_segment_gap_m'] or \
       (policy['max_time_gap_s'] is not None and (acq['max_time_gap_s'] is None or policy['max_time_gap_s'] > acq['max_time_gap_s'])):
        raise core.SurveyError('metadata_ineligible','seal')
    if metadata['original'] != inspection['original'] or metadata['arrays'] != inspection['arrays'] or \
       [acq['line_dictionary'],acq['sensor_dictionary']] != inspection['dictionaries'] or \
       request['dataset_version_sha256'] != base.dataset_identity(inspection['original']['csv_sha256'],base.digest(metadata)):
        raise core.SurveyError('custody_mismatch','seal')
    if any(op['operation']=='lag' for op in request['operations']) and not allow_navigation:
        raise core.SurveyError('unsupported_operation','seal')
    reader = io.Reader(root)
    refs = {ref['role']:ref for ref in inspection['arrays']}
    subset = metadata['subset']
    if subset is not None:
        if subset['parent_row_count'] < inspection['rows'] or subset['selected_ids']['shape'] != [inspection['rows']]:
            raise core.SurveyError('custody_mismatch','seal')
        if any(a!=b for a,b in zip(reader.cells(subset['selected_ids']),reader.cells(refs['row_id']),strict=True)):
            raise core.SurveyError('custody_mismatch','seal')
    tolerance = acq['height_consistency_tolerance_m']
    if tolerance is None:
        raise core.SurveyError('metadata_ineligible','seal')
    for z,terrain,clearance,mask in zip(*(reader.cells(refs[k]) for k in ('upward','terrain_upward','clearance','missing_mask')),strict=True):
        if mask & 2 or (not mask & (4|8) and abs(z-terrain-clearance)>tolerance):
            raise core.SurveyError('metadata_ineligible','seal')


def _coordinates(db, datum):
    identity = sha256()
    identity.update(b'{"datum":'+base.canonical_bytes(datum)+b',"rows":[')
    for pos,rid,e,n,z in db.execute('SELECT pos,id,e,n,z FROM rows ORDER BY pos'):
        if pos:
            identity.update(b',')
        identity.update(base.canonical_bytes([rid,e,n,z]))
    identity.update(b']}')
    return identity.hexdigest()


def _pack(root, references, destination):
    """Only verified members; never copy unrelated raw/value files."""
    # Owner plans cross the process boundary as JSON path strings. Apply the
    # same external-path validation as the in-process Path entry points.
    root, destination = io.external_path(root), io.external_path(destination)
    reader = io.Reader(root)
    for ref in references:
        reader.verify(ref)
    for name,identity in reader.known.items():
        payload = core._verified_member(root,identity,set(),8388608)
        if (destination/name).exists():
            # Two different identity descriptors may not overwrite a member.
            if base.read_bounded(core._plain_path(destination/name),8388608) != payload:
                raise core.SurveyError('custody_mismatch','seal')
        else:
            core._write_member(destination,name,payload)


def seal_geometry(root, inspection, metadata, request, request_root, output, *, temp_root, navigation_root=None):
    """Assemble original or independently aligned geometry; values unopened."""
    root,output = io.external_path(root),io.external_path(output)
    core.verify_geometry_inspection(root,inspection)
    _metadata(root,inspection,metadata,request,allow_navigation=navigation_root is not None)
    if output.exists():
        raise core.SurveyError('custody_mismatch','seal')
    with io.scratch_directory(temp_root) as scratch:
        scratch = Path(scratch)
        alignment = None
        navigation_refs = []
        lags = [op for op in request['operations'] if op['operation']=='lag']
        if navigation_root is not None:
            if len(lags)!=1:
                raise core.SurveyError('invalid_contract','seal')
            from magnetic_line_survey_navigation import align_geometry
            aligned = align_geometry(root,inspection,metadata,lags[0],navigation_root,scratch/'navigation',temp_root=temp_root)
            alignment = (scratch/'navigation',aligned)
            navigation_refs = [lags[0]['parameters']['navigation'][key] for key in ('row_ids','utc','line_index','xyz')]
        partitions = plan_partitions(root,inspection,request,request_root,scratch/'partitions',temp_root=temp_root,alignment=alignment)
        crossovers = geometry_crossovers(root,inspection,request['geometry_policy'],scratch/'crossovers',temp_root=temp_root,alignment=alignment)
        support = plan_support(root,inspection,request,scratch/'partitions',partitions,scratch/'support',temp_root=temp_root,alignment=alignment)
        arrays = list(inspection['arrays'])
        dictionaries = list(inspection['dictionaries'])
        part_arrays,part_tables = [],[]
        for part in partitions['partitions']:
            part_arrays.extend(part[key] for key in ('training','validation','exclusions','sources','source_members'))
            part_tables.append(part['source_blocks'])
        support_arrays = [p['validation_mask'] for p in support['partitions']]+[support['grid_mask']]
        arrays.extend(part_arrays+support_arrays)
        if alignment is not None:
            arrays.extend(navigation_refs+[aligned['coordinates'],aligned['mask']])
        dictionaries.extend(part_tables)
        cross_tables = [] if crossovers['table'] is None else [crossovers['table']]
        dictionaries.extend(cross_tables)
        with geometry_index(root,inspection,temp_root=temp_root,alignment=alignment) as (db,_,lines,sensors):
            coordinates = _coordinates(db,metadata['coordinates']['vertical_datum'])
        geometry_request = deepcopy(request)
        for key in ('channel_sha256','dataset_version_sha256'):
            del geometry_request[key]
        del geometry_request['split']['sealed_values_sha256']
        # Non-geometric operations are still part of the request identity, but
        # their measured/reference array bytes are never opened in this stage.
        capacity = core.plan_capacity(inspection['rows'],max(p['sources']['shape'][0] for p in partitions['partitions']),
            crossover_candidates=crossovers['candidates'],exported_cells=partitions['capacity']['exported_cells'],
            fft_cells=partitions['capacity']['fft_cells'],raw_bytes=inspection['original']['csv_bytes'])
        if alignment is not None:
            auxiliary_reader = io.Reader(navigation_root)
            for ref in navigation_refs:
                auxiliary_reader.verify(ref)
            auxiliary_reader.reject_unknown()
            capacity = core.plan_capacity(inspection['rows'],max(p['sources']['shape'][0] for p in partitions['partitions']),
                auxiliary_rows=navigation_refs[0]['shape'][0],auxiliary_bytes=sum(v['bytes'] for v in auxiliary_reader.known.values()),
                crossover_candidates=crossovers['candidates'],exported_cells=partitions['capacity']['exported_cells'],
                fft_cells=partitions['capacity']['fft_cells'],raw_bytes=inspection['original']['csv_bytes'])
        seal = schema.validate('GeometrySeal',dict(schema='magnetic-line-survey-geometry/1',original=inspection['original'],
            coordinates_sha256=coordinates,acquisition_sha256=base.digest(metadata['acquisition']),
            request_geometry_sha256=base.digest(geometry_request),rows=inspection['rows'],lines=len(lines),sensors=len(sensors),
            segments=crossovers['segments'],crossover_candidates=crossovers['candidates'],
            source_counts=[p['sources']['shape'][0] for p in partitions['partitions']],arrays=arrays,dictionaries=dictionaries,
            capacity=capacity,value_access='not_opened'))
        output.mkdir()
        _pack(root,inspection['arrays']+inspection['dictionaries'],output)
        _pack(scratch/'partitions',part_arrays+part_tables,output)
        _pack(scratch/'crossovers',cross_tables,output)
        _pack(scratch/'support',support_arrays,output)
        if alignment is not None:
            _pack(navigation_root,navigation_refs,output)
            _pack(scratch/'navigation',[aligned['coordinates'],aligned['mask']],output)
        core._write_member(output,'geometry-seal.json',base.canonical_bytes(seal))
        # The public seal is closed; additional stage mapping is an in-memory
        # owner return, not hidden extra keys in the published contract.
        result = dict(geometry=seal,partitions=partitions,crossovers=crossovers,support=support)
        if alignment is not None:
            result['navigation'] = aligned
        return result
