"""Fresh value-free resolution/2 geometry and all sixteen training source maps.

No numerical library or magnetic/sigma decoder is used. A geometry-only legacy
seed retains the established navigation/crossover/support conventions; its
25-fit preliminary capacity is never the published v2 admission proof. Exact
four-geometry counts and the 96+worst-final proof precede new source-map exports.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import math
from pathlib import Path

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as v1
import magnetic_line_survey_contract_v2 as v2
import magnetic_line_survey_io as io
import magnetic_line_survey_representation as representation
from magnetic_line_survey_capacity_v2 import plan_capacity
from magnetic_line_survey_geometry import geometry_index
from magnetic_line_survey_result import _pack


def _seed_request(request):
    """Internal geometry compatibility only; never rewrite stored v2 policy."""
    seed=deepcopy(request)
    seed.update(schema='magnetic-line-survey-request/1',profile='m03-offline-stream/1')
    seed['split']['tuning_candidate_order']='depth_then_damping_ascending'
    sources=seed['equivalent_sources']
    sources.update(source_geometry=sources.pop('source_geometries')[0],candidate_order='depth_then_damping_ascending',
                   tie_break='larger_damping_then_depth')
    return v1.validate('SurveyRequest',seed)


def _blocks(db,configuration):
    for pos,e,n in db.execute('SELECT pos,e,n FROM rows ORDER BY pos'):
        east=math.floor((e-configuration['origin_e_m'])/configuration['block_e_m'])
        north=math.floor((n-configuration['origin_n_m'])/configuration['block_n_m'])
        if not -2147483648<=east<=2147483647 or not -2147483648<=north<=2147483647:
            raise core.SurveyError('resource_refused','seal')
        db.execute('UPDATE rows SET block_e=?,block_n=? WHERE pos=?',(east,north,pos))


def seal_resolution_geometry(geometry_root,inspection,metadata,request,request_root,output,*,
                             temp_root,navigation_root=None):
    """Seal exactly 4x4 maps before new value access, under the approved limits.

    This is a real geometry producer, not execution of the 97 numerical fits.
    Whole-epoch native resource and single-unopened-outer gates remain separate.
    """
    request=v2.validate('SurveyRequest',request)
    metadata=v2.validate('SurveyInput',metadata)
    if request['dataset_version_sha256']!=base.dataset_identity(metadata['original']['csv_sha256'],base.digest(metadata)):
        raise core.SurveyError('custody_mismatch','seal')
    output=io.external_path(output)
    if output.exists():
        raise core.SurveyError('custody_mismatch','seal')
    seed_metadata=dict(metadata,schema='magnetic-line-survey-input/1')
    v1.validate('SurveyInput',seed_metadata)
    seed_request=_seed_request(request)
    # The subordinate geometry seed has its own accurately tagged v1 identity.
    # The retained v2 request/metadata are unchanged and separately verified
    # above; never copy their hash into a differently tagged byte domain.
    seed_request['dataset_version_sha256']=base.dataset_identity(metadata['original']['csv_sha256'],base.digest(seed_metadata))
    from magnetic_line_survey_seal import seal_geometry
    with io.scratch_directory(temp_root) as scratch:
        scratch=Path(scratch)
        seed=seal_geometry(geometry_root,inspection,seed_metadata,seed_request,request_root,scratch/'seed',
                           temp_root=scratch,navigation_root=navigation_root)
        geometry=seed['geometry']
        parts=seed['partitions']['partitions']
        reader=representation.Reader(scratch/'seed')
        for ref in geometry['arrays']+geometry['dictionaries']:
            reader.verify(ref)
        reader.reject_unknown(extra=('geometry-seal.json',))
        alignment=None
        if 'navigation' in seed:
            # The public seed contains finite coordinate members, not the
            # navigation producer envelope expected by the SQL view. Rebuild
            # that value-free stage honestly instead of forging its missing
            # receipt or disabling its strict custody check.
            from magnetic_line_survey_navigation import align_geometry
            lag=next(op for op in request['operations'] if op['operation']=='lag')
            aligned=align_geometry(geometry_root,inspection,seed_metadata,lag,navigation_root,scratch/'alignment',temp_root=scratch)
            if aligned!=seed['navigation']:
                raise core.SurveyError('custody_mismatch','seal')
            alignment=(scratch/'alignment',aligned)
        with geometry_index(geometry_root,inspection,temp_root=scratch,alignment=alignment) as (db,_reader,_lines,_sensors):
            db.execute('CREATE TABLE part (fold INTEGER,pos INTEGER,PRIMARY KEY(fold,pos))')
            for fold,part in enumerate(parts):
                db.executemany('INSERT INTO part VALUES (?,?)',((fold,pos) for pos in reader.cells(part['training'])))
            db.execute('CREATE INDEX part_pos ON part(pos,fold)')
            db.execute('CREATE INDEX block_order ON rows(block_e,block_n,id)')
            geometries=request['equivalent_sources']['source_geometries']
            counts=[]
            for configuration in geometries:
                _blocks(db,configuration)
                by_fold=[]
                for fold in range(4):
                    count=db.execute('SELECT count(*) FROM (SELECT DISTINCT r.block_e,r.block_n FROM rows r '
                        'JOIN part p ON r.pos=p.pos WHERE p.fold=?)',(fold,)).fetchone()[0]
                    core._count(count,1,configuration['max_sources'])
                    by_fold.append(count)
                counts.append(by_fold)
            training=[part['training']['shape'][0] for part in parts]
            validation=[part['validation']['shape'][0] for part in parts]
            shared_arrays=[ref for ref in geometry['arrays'] if ref['role'] not in ('source_position','source_block_member')]
            dictionaries=[ref for ref in geometry['dictionaries'] if ref['row_schema']!='source_block']
            # Count root manifests needed for a full physical Result plus
            # immutable request/metadata/reference/model/export members, not
            # merely sixteen maps or the old25-fit diagnostic envelope.
            future_arrays=len(shared_arrays)+32+2*(len(request['operations'])+1)+3+3+3+5*2+8
            future_dictionaries=len(dictionaries)+2
            future_members=future_arrays+future_dictionaries+16
            map_bytes=sum(16*training[f]+24*counts[g][f] for g in range(4) for f in range(4))
            retained=(sum(item['bytes'] for item in reader.known.values())+map_bytes+256*geometry['rows']+
                64*max(max(row) for row in counts)+64*geometry['capacity']['exported_cells']+
                future_arrays*2097152+96*65536)
            capacity,proof=plan_capacity(geometry['rows'],training,validation,counts,
                auxiliary_rows=geometry['capacity']['auxiliary_rows'],auxiliary_bytes=geometry['capacity']['auxiliary_bytes'],
                crossover_candidates=geometry['crossover_candidates'],exported_cells=geometry['capacity']['exported_cells'],
                fft_cells=geometry['capacity']['fft_cells'],raw_bytes=metadata['original']['csv_bytes'],
                retained_member_bytes=retained,retained_index_bytes=512*geometry['rows'],
                logical_members=future_members,arrays=future_arrays,dictionaries=future_dictionaries)
            # Before materializing any map sources/membership. This JSON binds
            # the exact actual geometry counts to the prospective proof.
            output.mkdir()
            proof_file=core._write_member(output,'resolution-capacity-proof.json',base.canonical_bytes(dict(
                schema='m03-resolution-capacity-proof/1',request_sha256=base.digest(request),
                original=inspection['original'],coordinates_sha256=geometry['coordinates_sha256'],
                source_counts_by_geometry=counts,capacity=capacity,proof=proof,value_access='not_opened')))
            _pack(scratch/'seed',shared_arrays+dictionaries,output)
            maps=[]
            for g,configuration in enumerate(geometries):
                _blocks(db,configuration)
                for fold,part in enumerate(parts):
                    blocks=list(db.execute('SELECT DISTINCT r.block_e,r.block_n FROM rows r JOIN part p ON r.pos=p.pos '
                        'WHERE p.fold=? ORDER BY r.block_e,r.block_n',(fold,)))
                    if len(blocks)!=counts[g][fold]:
                        raise core.SurveyError('custody_mismatch','seal')
                    db.execute('DROP TABLE IF EXISTS current_sources')
                    db.execute('CREATE TABLE current_sources(idx INTEGER PRIMARY KEY,be INTEGER,bn INTEGER,e REAL,n REAL,z REAL,UNIQUE(be,bn))')
                    minimum=db.execute('SELECT min(r.z) FROM rows r JOIN part p ON r.pos=p.pos WHERE p.fold=?',(fold,)).fetchone()[0]
                    height=minimum-request['equivalent_sources']['depth_candidates_m'][0]
                    if not math.isfinite(height) or height==minimum:
                        raise core.SurveyError('metadata_ineligible','seal')
                    identity=sha256()
                    for index,(east,north) in enumerate(blocks):
                        query=' FROM rows r JOIN part p ON r.pos=p.pos WHERE p.fold=? AND r.block_e=? AND r.block_n=?'
                        args=(fold,east,north)
                        count=db.execute('SELECT count(*)'+query,args).fetchone()[0]
                        e=math.fsum(value for value, in db.execute('SELECT r.e'+query+' ORDER BY r.id',args))/count
                        n=math.fsum(value for value, in db.execute('SELECT r.n'+query+' ORDER BY r.id',args))/count
                        db.execute('INSERT INTO current_sources VALUES (?,?,?,?,?,?)',(index,east,north,e,n,height))
                        identity.update(base.canonical_bytes([index,east,north,e,n,height]))
                    source=representation.write_array(output,f'g{g}-f{fold}-sources','source_position',
                        db.execute('SELECT e,n,z FROM current_sources ORDER BY idx'),[len(blocks),3],'float64','m',identity.hexdigest())
                    members=representation.write_array(output,f'g{g}-f{fold}-members','source_block_member',
                        db.execute('SELECT r.pos,s.idx FROM rows r JOIN part p ON r.pos=p.pos '
                            'JOIN current_sources s ON s.be=r.block_e AND s.bn=r.block_n WHERE p.fold=? ORDER BY r.pos',(fold,)),
                        [training[fold],2],'uint64','identity',part['training']['ordered_ids_sha256'])
                    maps.append(dict(source_geometry_index=g,fold_id='final' if fold==0 else part['fold_id'],
                        training=part['training'],sources=source,source_members=members))
            geometry_request=deepcopy(request)
            del geometry_request['channel_sha256'],geometry_request['dataset_version_sha256'],geometry_request['split']['sealed_values_sha256']
            seal=dict(geometry,schema='magnetic-line-survey-geometry/2',
                acquisition_sha256=base.digest(metadata['acquisition']),request_geometry_sha256=base.digest(geometry_request),
                arrays=shared_arrays+[ref for item in maps for ref in (item['sources'],item['source_members'])],
                dictionaries=dictionaries,source_counts_by_geometry=counts,source_maps=maps,capacity=capacity)
            del seal['source_counts']
            v2.validate('GeometrySeal',seal)
            core._write_member(output,'geometry-seal.json',base.canonical_bytes(seal))
            verify=representation.Reader(output)
            for ref in seal['arrays']+seal['dictionaries']:
                verify.verify(ref)
            verify.member(proof_file)
            verify.reject_unknown(extra=('geometry-seal.json',))
            partitions=dict(schema='m03-resolution-partitions/1',request_sha256=base.digest(request),
                partitions=[dict({key:part[key] for key in ('training','validation','exclusions')},
                    fold_id='final' if fold==0 else part['fold_id']) for fold,part in enumerate(parts)])
            return dict(geometry=seal,capacity_proof=proof_file,partitions=partitions,support=seed['support'],
                crossovers=seed['crossovers'],navigation=seed.get('navigation'),value_access='not_opened',
                actual_numerical_fit_count=0,native_admission='not_established')


def verify_resolution_geometry(geometry_root,inspection,metadata,request,request_root,sealed_root,sealed,*,
                               temp_root,navigation_root=None):
    """Independently reconstruct all sixteen maps and exact pre-value work bound.

    No source-table centroid, echoed capacity count, magnetic value or outer
    score is authority. This check is mandatory before a v2 native allocation.
    It does not turn arithmetic admission into measured host qualification.
    """
    from magnetic_line_survey_result import _check
    metadata=v2.validate('SurveyInput',metadata)
    request=v2.validate('SurveyRequest',request)
    geometry=v2.validate('GeometrySeal',sealed['geometry'])
    core._closed(sealed,'geometry capacity_proof partitions support crossovers navigation value_access '
        'actual_numerical_fit_count native_admission','seal')
    reader=representation.Reader(sealed_root)
    _check(base.strict_json(base.read_bounded(core._plain_path(reader.root/'geometry-seal.json'),2097152))==geometry)
    _check(request['dataset_version_sha256']==base.dataset_identity(metadata['original']['csv_sha256'],base.digest(metadata)))
    _check(geometry['original']==metadata['original']==inspection['original'] and geometry['value_access']=='not_opened'
        and sealed['value_access']=='not_opened' and sealed['actual_numerical_fit_count']==0
        and sealed['native_admission']=='not_established')
    geometry_request=deepcopy(request)
    del geometry_request['channel_sha256'],geometry_request['dataset_version_sha256'],geometry_request['split']['sealed_values_sha256']
    _check(geometry['request_geometry_sha256']==base.digest(geometry_request)
        and geometry['acquisition_sha256']==base.digest(metadata['acquisition']))
    for ref in geometry['arrays']+geometry['dictionaries']:
        reader.verify(ref)
    proof=base.strict_json(reader.member(sealed['capacity_proof']))
    core._closed(proof,'schema request_sha256 original coordinates_sha256 source_counts_by_geometry capacity proof value_access','seal')
    _check(proof['schema']=='m03-resolution-capacity-proof/1' and proof['request_sha256']==base.digest(request)
        and proof['original']==geometry['original'] and proof['coordinates_sha256']==geometry['coordinates_sha256']
        and proof['value_access']=='not_opened')
    reader.reject_unknown(extra=('geometry-seal.json',))
    core._closed(sealed['partitions'],'schema request_sha256 partitions','seal')
    _check(sealed['partitions']['schema']=='m03-resolution-partitions/1'
        and sealed['partitions']['request_sha256']==base.digest(request))
    parts=sealed['partitions']['partitions']
    _check(type(parts) is list and len(parts)==4 and [part['fold_id'] for part in parts]==['final','A','B','C'])
    for part in parts:
        core._closed(part,'fold_id training validation exclusions','seal')
        _check(all(part[key] in geometry['arrays'] for key in ('training','validation','exclusions')))
    maps=geometry['source_maps']
    _check([(item['source_geometry_index'],item['fold_id']) for item in maps]==
        [(g,fold) for g in range(4) for fold in ('final','A','B','C')])
    geometries=request['equivalent_sources']['source_geometries']
    seed_metadata=dict(metadata,schema='magnetic-line-survey-input/1')
    alignment=None
    with io.scratch_directory(temp_root) as scratch:
        scratch=Path(scratch)
        if sealed['navigation'] is not None:
            from magnetic_line_survey_navigation import align_geometry
            lag=next(op for op in request['operations'] if op['operation']=='lag')
            aligned=align_geometry(geometry_root,inspection,seed_metadata,lag,navigation_root,scratch/'alignment',temp_root=scratch)
            _check(aligned==sealed['navigation'])
            alignment=(scratch/'alignment',aligned)
        with geometry_index(geometry_root,inspection,temp_root=scratch,alignment=alignment) as (db,_reader,_lines,_sensors):
            db.execute('CREATE TABLE verified_training(fold INTEGER,pos INTEGER,PRIMARY KEY(fold,pos))')
            db.execute('CREATE INDEX verified_training_pos ON verified_training(pos,fold)')
            for fold,part in enumerate(parts):
                previous=-1
                for pos in reader.cells(part['training']):
                    _check(type(pos) is int and previous<pos<geometry['rows'])
                    db.execute('INSERT INTO verified_training VALUES (?,?)',(fold,pos))
                    previous=pos
            actual_counts=[]
            for g,configuration in enumerate(geometries):
                _blocks(db,configuration)
                fold_counts=[]
                for fold,part in enumerate(parts):
                    item=maps[g*4+fold]
                    _check(item['training']==part['training'] and item['sources'] in geometry['arrays']
                        and item['source_members'] in geometry['arrays'])
                    query=' FROM rows r JOIN verified_training p ON r.pos=p.pos WHERE p.fold=?'
                    blocks=list(db.execute('SELECT DISTINCT r.block_e,r.block_n'+query+' ORDER BY r.block_e,r.block_n',(fold,)))
                    count=len(blocks)
                    _check(1<=count<=configuration['max_sources'])
                    fold_counts.append(count)
                    _check(item['sources']['shape']==[count,3] and item['source_members']['shape']==[part['training']['shape'][0],2]
                        and item['source_members']['ordered_ids_sha256']==part['training']['ordered_ids_sha256'])
                    positions=iter(reader.cells(part['training']))
                    members=iter(reader.cells(item['source_members']))
                    indexes={block:index for index,block in enumerate(blocks)}
                    for pos,east,north in db.execute('SELECT r.pos,r.block_e,r.block_n'+query+' ORDER BY r.pos',(fold,)):
                        _check(next(positions,None)==pos and next(members,None)==pos and next(members,None)==indexes[(east,north)])
                    _check(next(positions,None) is None and next(members,None) is None)
                    minimum=db.execute('SELECT min(r.z)'+query,(fold,)).fetchone()[0]
                    height=minimum-request['equivalent_sources']['depth_candidates_m'][0]
                    sources=iter(reader.cells(item['sources']))
                    identity=sha256()
                    for index,(east,north) in enumerate(blocks):
                        block_query=query+' AND r.block_e=? AND r.block_n=?'
                        args=(fold,east,north)
                        number=db.execute('SELECT count(*)'+block_query,args).fetchone()[0]
                        e=math.fsum(value for value, in db.execute('SELECT r.e'+block_query+' ORDER BY r.id',args))/number
                        n=math.fsum(value for value, in db.execute('SELECT r.n'+block_query+' ORDER BY r.id',args))/number
                        _check(tuple(next(sources,None) for _ in range(3))==(e,n,height))
                        identity.update(base.canonical_bytes([index,east,north,e,n,height]))
                    _check(next(sources,None) is None and identity.hexdigest()==item['sources']['ordered_ids_sha256'])
                actual_counts.append(fold_counts)
            _check(actual_counts==geometry['source_counts_by_geometry']==proof['source_counts_by_geometry'])
    training=[part['training']['shape'][0] for part in parts]
    validation=[part['validation']['shape'][0] for part in parts]
    shared=[ref for ref in geometry['arrays'] if ref['role'] not in ('source_position','source_block_member')]
    arrays=len(shared)+32+2*(len(request['operations'])+1)+3+3+3+10+8
    dictionaries=len(geometry['dictionaries'])+2
    reservation=proof['proof']
    _check(type(reservation['retained_member_bytes']) is int)
    retained_actual=sum(item['bytes'] for name,item in reader.known.items() if name!=sealed['capacity_proof']['name'])
    minimum_retained=(retained_actual+256*geometry['rows']+64*max(max(row) for row in actual_counts)+
        64*geometry['capacity']['exported_cells']+arrays*2097152+96*65536)
    _check(reservation['retained_member_bytes']>=minimum_retained)
    capacity,expected=plan_capacity(geometry['rows'],training,validation,actual_counts,
        auxiliary_rows=geometry['capacity']['auxiliary_rows'],auxiliary_bytes=geometry['capacity']['auxiliary_bytes'],
        crossover_candidates=geometry['crossover_candidates'],exported_cells=geometry['capacity']['exported_cells'],
        fft_cells=geometry['capacity']['fft_cells'],raw_bytes=metadata['original']['csv_bytes'],
        retained_member_bytes=reservation['retained_member_bytes'],retained_index_bytes=512*geometry['rows'],
        logical_members=arrays+dictionaries+16,arrays=arrays,dictionaries=dictionaries)
    _check(capacity==geometry['capacity']==proof['capacity'] and expected==reservation)
    return dict(schema='m03-resolution-geometry-verification/1',source_maps=16,source_counts_by_geometry=actual_counts,
        mandatory_fit_count=97,inner_fit_count=96,capacity_and_maps='pass',value_access='not_opened',
        actual_numerical_fit_count=0,native_admission='not_established')


def verify_result_maps(reader,result,metadata,request,db):
    """Reconstruct every retained v2 map from original rows and split SQL index."""
    import itertools
    from magnetic_line_survey_result import _check
    n=result['geometry']['rows']
    refs={ref['role']:ref for ref in metadata['arrays']}
    aligned=[ref for ref in result['geometry']['arrays'] if ref['role']=='navigation' and
        ref['shape']==[n,3] and ref['ordered_ids_sha256']==refs['row_id']['ordered_ids_sha256']]
    if any(op['operation']=='lag' for op in request['operations']):
        _check(len(aligned)==1)
        cells=reader.cells(aligned[0])
        xyz=iter(lambda:tuple(itertools.islice(cells,3)),())
    else:
        xyz=zip(*(reader.cells(refs[role]) for role in ('easting','northing','upward')),strict=True)
    for column in ('e','n','z'):
        db.execute('ALTER TABLE ids ADD COLUMN '+column+' REAL')
    db.execute('ALTER TABLE ids ADD COLUMN be INTEGER')
    db.execute('ALTER TABLE ids ADD COLUMN bn INTEGER')
    count=0
    for count,triple in enumerate(xyz,1):
        _check(len(triple)==3 and all(math.isfinite(value) for value in triple))
        db.execute('UPDATE ids SET e=?,n=?,z=? WHERE pos=?',(*triple,count-1))
    _check(count==n)
    maps=result['geometry']['source_maps']
    _check([(item['source_geometry_index'],item['fold_id']) for item in maps]==
        [(g,fold) for g in range(4) for fold in ('final','A','B','C')])
    folds=[dict(training=result['partitions']['final_training'],validation=result['partitions']['outer_validation'])]+result['partitions']['inner']
    counts=[]
    db.execute('CREATE INDEX verified_block_ids ON ids(be,bn,id)')
    for g,configuration in enumerate(request['equivalent_sources']['source_geometries']):
        for pos,e,north in db.execute('SELECT pos,e,n FROM ids ORDER BY pos'):
            be=math.floor((e-configuration['origin_e_m'])/configuration['block_e_m'])
            bn=math.floor((north-configuration['origin_n_m'])/configuration['block_n_m'])
            _check(-2147483648<=be<=2147483647 and -2147483648<=bn<=2147483647)
            db.execute('UPDATE ids SET be=?,bn=? WHERE pos=?',(be,bn,pos))
        group=[]
        for fold,part in enumerate(folds):
            item=maps[g*4+fold]
            _check(item['training']==part['training'])
            query=' FROM ids r JOIN partition p ON r.pos=p.pos WHERE p.fold=? AND p.kind=1'
            blocks=list(db.execute('SELECT DISTINCT r.be,r.bn'+query+' ORDER BY r.be,r.bn',(fold,)))
            m=len(blocks)
            _check(1<=m<=configuration['max_sources'] and item['sources']['shape']==[m,3]
                and item['source_members']['shape']==[part['training']['shape'][0],2]
                and item['source_members']['ordered_ids_sha256']==part['training']['ordered_ids_sha256'])
            positions=reader.cells(part['training'])
            members=iter(reader.cells(item['source_members']))
            indices={block:index for index,block in enumerate(blocks)}
            for pos,be,bn in db.execute('SELECT r.pos,r.be,r.bn'+query+' ORDER BY r.pos',(fold,)):
                _check(next(positions,None)==pos and next(members,None)==pos and next(members,None)==indices[(be,bn)])
            _check(next(positions,None) is None and next(members,None) is None)
            minimum=db.execute('SELECT min(r.z)'+query,(fold,)).fetchone()[0]
            height=minimum-request['equivalent_sources']['depth_candidates_m'][0]
            sources=iter(reader.cells(item['sources']))
            identity=sha256()
            for index,(be,bn) in enumerate(blocks):
                block_query=query+' AND r.be=? AND r.bn=?'
                args=(fold,be,bn)
                number=db.execute('SELECT count(*)'+block_query,args).fetchone()[0]
                e=math.fsum(value for value, in db.execute('SELECT r.e'+block_query+' ORDER BY r.id',args))/number
                north=math.fsum(value for value, in db.execute('SELECT r.n'+block_query+' ORDER BY r.id',args))/number
                _check(tuple(next(sources,None) for _ in range(3))==(e,north,height))
                identity.update(base.canonical_bytes([index,be,bn,e,north,height]))
            _check(next(sources,None) is None and identity.hexdigest()==item['sources']['ordered_ids_sha256'])
            group.append(m)
            if fold and g==result['fit']['selected_source_geometry_index']:
                _check(part['source_members']==item['source_members'])
        counts.append(group)
    _check(counts==result['geometry']['source_counts_by_geometry'])
    proof_members=[item for item in result['artifacts'] if item['name']=='resolution-capacity-proof.json' and item['disposition']=='included']
    _check(len(proof_members)==1)
    proof=base.strict_json(reader.member({key:proof_members[0][key] for key in ('name','bytes','sha256')}))
    core._closed(proof,'schema request_sha256 original coordinates_sha256 source_counts_by_geometry capacity proof value_access','replay')
    _check(proof['schema']=='m03-resolution-capacity-proof/1' and proof['request_sha256']==base.digest(request)
        and proof['original']==metadata['original'] and proof['value_access']=='not_opened'
        and proof['coordinates_sha256']==result['geometry']['coordinates_sha256'] and proof['source_counts_by_geometry']==counts)
    arrays=len([ref for ref in result['geometry']['arrays'] if ref['role'] not in ('source_position','source_block_member')])+32+2*(len(request['operations'])+1)+3+3+3+10+8
    dictionaries=len(result['geometry']['dictionaries'])+2
    capacity,expected=plan_capacity(n,[part['training']['shape'][0] for part in folds],
        [part['validation']['shape'][0] for part in folds],counts,
        auxiliary_rows=result['geometry']['capacity']['auxiliary_rows'],auxiliary_bytes=result['geometry']['capacity']['auxiliary_bytes'],
        crossover_candidates=result['geometry']['crossover_candidates'],exported_cells=result['geometry']['capacity']['exported_cells'],
        fft_cells=result['geometry']['capacity']['fft_cells'],raw_bytes=metadata['original']['csv_bytes'],
        retained_member_bytes=proof['proof']['retained_member_bytes'],retained_index_bytes=512*n,
        logical_members=arrays+dictionaries+16,arrays=arrays,dictionaries=dictionaries)
    _check(capacity==result['geometry']['capacity']==proof['capacity'] and expected==proof['proof'])
