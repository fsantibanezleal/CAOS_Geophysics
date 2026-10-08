"""Fold-local values on ALL original geometric pairs, without scope leakage."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import math
import re

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_io as io
from magnetic_line_survey_geometry import geometry_index
from magnetic_lines import CROSSOVER_REASONS


def crossover_values(root,inspection,policy,geometry_root,geometry,partition_root,training,
                     measurement_root,measurements,uncertainty,output,*,temp_root):
    """Rebuild representatives only AFTER this fold's bracket/value admission."""
    policy = base.validate_named('GeometryPolicy',policy)
    physical = policy['crossover']
    output = io.external_path(output)
    if output.exists():
        raise core.SurveyError('custody_mismatch','crossover')
    stored = base.strict_json(base.read_bounded(core._plain_path(io.external_path(geometry_root)/'crossover-plan.json'),2097152))
    measured = base.strict_json(base.read_bounded(core._plain_path(io.external_path(measurement_root)/'measurement-pass.json'),2097152))
    if stored!=geometry or geometry['geometry_sha256']!=inspection['geometry_sha256'] or \
       geometry['geometry_policy_sha256']!=base.digest(policy) or measured!=measurements or \
       measurements['geometry_sha256']!=inspection['geometry_sha256'] or measurements['original']!=inspection['original']:
        raise core.SurveyError('custody_mismatch','crossover')
    if physical['uncertainty_policy']=='documented_independent_rows' and (uncertainty is None or
        uncertainty['meaning']!='independent_one_sigma' or uncertainty['independence_assumption']!='row_independent'):
        raise core.SurveyError('metadata_ineligible','crossover')
    if uncertainty is not None:
        base.validate_named('Uncertainty',uncertainty)
    if training['role']!='partition_index' or training['dtype']!='uint64' or len(training['shape'])!=1:
        raise core.SurveyError('invalid_contract','crossover')
    if [r['role'] for r in measurements['arrays']]!=['magnetic','uncertainty','missing_mask'] or \
       any(r['shape']!=[inspection['rows']] for r in measurements['arrays']):
        raise core.SurveyError('custody_mismatch','crossover')
    output.mkdir()
    gr = io.Reader(geometry_root)
    mr = io.Reader(measurement_root)
    pr = io.Reader(partition_root)
    value_refs = {ref['role']:ref for ref in measurements['arrays']}
    admitted = 0
    with geometry_index(root,inspection,temp_root=temp_root) as (db,_,lines,_):
        db.execute('CREATE TABLE training (pos INTEGER PRIMARY KEY)')
        previous = -1
        training_hash = sha256()
        for pos in pr.cells(training):
            if pos<=previous or not 0<=pos<inspection['rows']:
                raise core.SurveyError('custody_mismatch','crossover')
            previous=pos
            rid=db.execute('SELECT id FROM rows WHERE pos=?',(pos,)).fetchone()[0]
            training_hash.update(rid.encode('ascii').ljust(64,b'\0'))
            db.execute('INSERT INTO training VALUES (?)',(pos,))
        if training_hash.hexdigest()!=training['ordered_ids_sha256']:
            raise core.SurveyError('custody_mismatch','crossover')
        db.execute('CREATE TABLE measured (pos INTEGER PRIMARY KEY,value REAL,sigma REAL,mask INTEGER)')
        for pos,(value,sigma,mask) in enumerate(zip(*(mr.cells(value_refs[k]) for k in ('magnetic','uncertainty','missing_mask')),strict=True)):
            if pos>=inspection['rows']:
                raise core.SurveyError('custody_mismatch','crossover')
            db.execute('INSERT INTO measured VALUES (?,?,?,?)',(pos,value,sigma,mask))
            if pos%4096==4095:
                db.commit()
        if db.execute('SELECT count(*) FROM measured').fetchone()[0]!=inspection['rows']:
            raise core.SurveyError('custody_mismatch','crossover')
        db.execute('CREATE TABLE representatives (id TEXT PRIMARY KEY,flight INTEGER,tie INTEGER,sensor INTEGER,e REAL,n REAL)')
        db.execute('CREATE INDEX representative_role ON representatives(flight,tie,sensor)')
        db.commit()

        def segment(identifier):
            if type(identifier) is not str or not re.fullmatch(r'S[0-9]{6,7}',identifier):
                raise core.SurveyError('custody_mismatch','crossover')
            pos=int(identifier[1:])
            row = db.execute('SELECT pos,line,sensor,ordinal FROM rows WHERE pos=?',(pos,)).fetchone()
            if row is None or identifier!=f'S{pos:06d}':
                raise core.SurveyError('custody_mismatch','crossover')
            other = db.execute('SELECT pos,line,sensor,ordinal FROM rows WHERE line=? AND sensor=? AND ordinal>? ORDER BY ordinal LIMIT 1',row[1:]).fetchone()
            if other is None:
                raise core.SurveyError('custody_mismatch','crossover')
            return row,other

        def records():
            nonlocal admitted
            for original in gr.table(geometry['table']):
                record = deepcopy(original)
                record.update(flight_minus_tie_nT=None,difference_variance_nT2=None,
                              disposition='rejected',shared_endpoint_group_id=None,constraint_representative=None)
                reasons=set(record['reasons'])-{'duplicate_physical_constraint'}
                flight,tie = segment(record['flight_segment_id']),segment(record['tie_segment_id'])
                if lines[flight[0][1]]['kind']=='tie' or lines[tie[0][1]]['kind']!='tie':
                    raise core.SurveyError('custody_mismatch','crossover')
                endpoints = [*flight,*tie]
                values = []
                for pos,line,sensor,_ in endpoints:
                    if not db.execute('SELECT 1 FROM training WHERE pos=?',(pos,)).fetchone():
                        reasons.add('spatial_buffer' if lines[line]['kind']=='tie' else 'outer_sealed')
                    value = db.execute('SELECT value,sigma,mask FROM measured WHERE pos=?',(pos,)).fetchone()
                    if value[2]&16:
                        reasons.add('missing_value')
                    values.append(value)
                if record['a'] is not None and record['b'] is not None and not reasons:
                    a,b = record['a'],record['b']
                    if not 0<=a<=1 or not 0<=b<=1:
                        raise core.SurveyError('custody_mismatch','crossover')
                    def interpolate(left,right,weight):
                        return left if left==right else math.fsum(((1-weight)*left,weight*right))
                    difference = interpolate(values[0][0],values[1][0],a)-interpolate(values[2][0],values[3][0],b)
                    if not math.isfinite(difference):
                        raise core.SurveyError('metadata_ineligible','crossover')
                    record['flight_minus_tie_nT']=difference
                    if physical['uncertainty_policy']=='documented_independent_rows':
                        if any(v[2]&32 or v[1]<=0 for v in values):
                            raise core.SurveyError('metadata_ineligible','crossover')
                        try:
                            variance = math.fsum((v[1]*w)**2 for v,w in zip(values,(1-a,a,1-b,b),strict=True))
                        except OverflowError:
                            raise core.SurveyError('metadata_ineligible','crossover') from None
                        if not math.isfinite(variance) or variance<=0:
                            raise core.SurveyError('metadata_ineligible','crossover')
                        record['difference_variance_nT2']=variance
                    record['disposition']='admitted'
                    role=(flight[0][1],tie[0][1],flight[0][2])
                    prior = next((rid for rid,e,n in db.execute('SELECT id,e,n FROM representatives WHERE flight=? AND tie=? AND sensor=? ORDER BY rowid',role)
                                  if math.hypot(record['easting_m']-e,record['northing_m']-n)<=record['tolerance']['coordinate_m']),None)
                    if prior is None:
                        prior=record['crossover_id']
                        admitted += 1
                        db.execute('INSERT INTO representatives VALUES (?,?,?,?,?,?)',(prior,*role,record['easting_m'],record['northing_m']))
                    else:
                        reasons.add('duplicate_physical_constraint')
                    record['constraint_representative']=record['shared_endpoint_group_id']=prior
                record['reasons']=[reason for reason in CROSSOVER_REASONS if reason in reasons]
                yield record

        table = None if geometry['table'] is None else io.write_table(output,'fold-crossovers','crossover_value',records())
        result = dict(schema='m03-fold-crossover-values/1',geometry_sha256=inspection['geometry_sha256'],
            geometry_policy_sha256=base.digest(policy),training=training,measurements_sha256=base.digest(measurements),
            table=table,admitted_constraints=admitted,field_acceptance='unresolved')
        core._write_member(output,'crossover-values.json',base.canonical_bytes(result))
        return result


def incidence_constraints(root,inspection,value_root,values,*,temp_root):
    """Stream actual fold representatives to the one global graph solver."""
    stored=base.strict_json(base.read_bounded(core._plain_path(io.external_path(value_root)/'crossover-values.json'),2097152))
    if stored!=values or values['geometry_sha256']!=inspection['geometry_sha256']:
        raise core.SurveyError('custody_mismatch','crossover')
    reader=io.Reader(value_root)
    count=0
    with geometry_index(root,inspection,temp_root=temp_root) as (db,_,lines,_):
        if values['table'] is not None:
            for row in reader.table(values['table']):
                if row['disposition']!='admitted' or row['constraint_representative']!=row['crossover_id']:
                    continue
                line_ids=[]
                for key in ('flight_segment_id','tie_segment_id'):
                    token=row[key]
                    if not re.fullmatch(r'S[0-9]{6,7}',token) or token!=f'S{int(token[1:]):06d}':
                        raise core.SurveyError('custody_mismatch','crossover')
                    line=db.execute('SELECT line FROM rows WHERE pos=?',(int(token[1:]),)).fetchone()
                    if line is None:
                        raise core.SurveyError('custody_mismatch','crossover')
                    line_ids.append(lines[line[0]])
                if line_ids[0]['kind']=='tie' or line_ids[1]['kind']!='tie' or row['flight_minus_tie_nT'] is None:
                    raise core.SurveyError('custody_mismatch','crossover')
                count+=1
                yield dict(flight=line_ids[0]['line_id'],tie=line_ids[1]['line_id'],
                           difference_nT=row['flight_minus_tie_nT'],variance_nT2=row['difference_variance_nT2'])
        if count!=values['admitted_constraints']:
            raise core.SurveyError('custody_mismatch','crossover')
        reader.reject_unknown(extra=('crossover-values.json',))
