"""Exhaustive geometry-only crossover inventory using an external R-tree.

Index pruning is conservative; exact float64 bounds determine the candidate
set. Gapped/height/time/degenerate pairs remain records, not invisible deletions.
Measurement, partition and graph-calibration eligibility are subsequent gates.
"""
from __future__ import annotations

from fractions import Fraction
import math

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_geometry as planner
import magnetic_line_survey_io as io
from magnetic_lines import intersect_segments, _utc_ns, CROSSOVER_REASONS


def geometry_crossovers(root, inspection, geometry_policy, output, *, temp_root, candidate_limit=8000000, alignment=None):
    policy = base.validate_named('GeometryPolicy', geometry_policy)
    if type(candidate_limit) is not int or not 1 <= candidate_limit <= 8000000:
        raise core.SurveyError('invalid_contract', 'seal')
    physical = policy['crossover']
    output = io.external_path(output)
    if output.exists():
        raise core.SurveyError('custody_mismatch', 'seal')
    output.mkdir()
    with planner.geometry_index(root, inspection, temp_root=temp_root, alignment=alignment) as (db, _, lines, sensors):
        bounds = db.execute('SELECT min(e),max(e),min(n),max(n) FROM rows').fetchone()
        span = max(bounds[1]-bounds[0], bounds[3]-bounds[2])
        tau = 64*core.EPSILON*max(1., span, *(abs(v) for v in bounds))
        if not math.isfinite(tau) or tau <= 0:
            raise core.SurveyError('metadata_ineligible', 'crossover')
        db.execute('CREATE TABLE segments (id INTEGER PRIMARY KEY, name TEXT UNIQUE, p INTEGER, q INTEGER, '
                   'line INTEGER,sensor INTEGER,tie INTEGER,e0 REAL,e1 REAL,n0 REAL,n1 REAL)')
        db.execute('CREATE VIRTUAL TABLE boxes USING rtree(id,e0,e1,n0,n1)')
        prior = None
        for pos,line,sensor,e,n in db.execute('SELECT pos,line,sensor,e,n FROM rows ORDER BY line,sensor,ordinal'):
            if prior is not None and prior[1:3] == (line,sensor):
                old,e_old,n_old = prior[0], prior[3], prior[4]
                bbox = (min(e_old,e),max(e_old,e),min(n_old,n),max(n_old,n))
                db.execute('INSERT INTO segments VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    (old,f'S{old:06d}',old,pos,line,sensor,int(lines[line]['kind']=='tie'),*bbox))
                if lines[line]['kind']=='tie':
                    db.execute('INSERT INTO boxes VALUES (?,?,?,?,?)', (old,*bbox))
            prior = (pos,line,sensor,e,n)
        db.execute('CREATE TABLE pairs (sequence INTEGER PRIMARY KEY,flight INTEGER,tie INTEGER)')
        count = 0
        for fid,e0,e1,n0,n1 in db.execute('SELECT id,e0,e1,n0,n1 FROM segments WHERE tie=0 ORDER BY name'):
            query = ('SELECT s.id,s.e0,s.e1,s.n0,s.n1 FROM boxes b JOIN segments s ON b.id=s.id '
                     'WHERE b.e0<=? AND b.e1>=? AND b.n0<=? AND b.n1>=? ORDER BY s.name')
            for tid,t0,t1,u0,u1 in db.execute(query, (e1+tau,e0-tau,n1+tau,n0-tau)):
                if e0 > t1+tau or t0 > e1+tau or n0 > u1+tau or u0 > n1+tau:
                    continue
                count += 1
                if count > candidate_limit:
                    raise core.SurveyError('resource_refused', 'seal')
                db.execute('INSERT INTO pairs VALUES (?,?,?)', (count-1,fid,tid))
        db.commit()
        segments = db.execute('SELECT count(*) FROM segments').fetchone()[0]
        db.execute('CREATE TABLE representatives (id TEXT PRIMARY KEY,line_a INTEGER,line_b INTEGER,sensor INTEGER,e REAL,n REAL)')
        db.execute('CREATE INDEX physical_group ON representatives(line_a,line_b,sensor)')

        def endpoint(pos):
            row = db.execute('SELECT pos,line,sensor,utc,e,n,z,mask FROM rows WHERE pos=?', (pos,)).fetchone()
            return dict(pos=row[0], line=row[1], sensor=row[2], utc=None if row[7]&1 else row[3],
                        e=row[4], n=row[5], z=None if row[7]&2 else row[6])

        def records():
            for sequence,fid,tid in db.execute('SELECT sequence,flight,tie FROM pairs ORDER BY sequence'):
                segments_ = []
                for sid in (fid,tid):
                    name,p,q = db.execute('SELECT name,p,q FROM segments WHERE id=?',(sid,)).fetchone()
                    segments_.append((name,endpoint(p),endpoint(q)))
                flight,tie = segments_
                points = [p for segment in segments_ for p in segment[1:]]
                record = dict(crossover_id=f'X{sequence:06d}',flight_segment_id=flight[0],tie_segment_id=tie[0],
                    a=None,b=None,easting_m=None,northing_m=None,height_difference_m=None,time_separation_s=None,
                    disposition='rejected',reasons=[],shared_endpoint_group_id=None,constraint_representative=None,
                    tolerance=dict(coordinate_m=tau,determinant_m2=None,sine_dimensionless=None,
                                   parameter_dimensionless=None,matrix_residual_m=None))
                reasons = set()
                for _,p,q in segments_:
                    length = math.hypot(q['e']-p['e'],q['n']-p['n'])
                    if not math.isfinite(length) or length > policy['max_segment_gap_m']:
                        reasons.add('gap')
                    if policy['max_time_gap_s'] is not None:
                        if p['utc'] is None or q['utc'] is None:
                            reasons.add('unsupported_time')
                        elif not 0 < _utc_ns(q['utc'])-_utc_ns(p['utc']) <= Fraction.from_float(policy['max_time_gap_s'])*1000000000:
                            reasons.add('gap')
                if any(p['sensor']!=points[0]['sensor'] for p in points):
                    reasons.add('sensor_mismatch')
                if any(p['z'] is None for p in points):
                    reasons.add('missing_height')
                xy = [(p['e'],p['n']) for p in points]
                v = (xy[1][0]-xy[0][0],xy[1][1]-xy[0][1])
                w = (xy[3][0]-xy[2][0],xy[3][1]-xy[2][1])
                lp,lq = math.hypot(*v),math.hypot(*w)
                if lp > tau and lq > tau and math.isfinite(lp*lq):
                    determinant = abs(v[0]*w[1]-v[1]*w[0])
                    threshold = 64*core.EPSILON*lp*lq+4*tau*(lp+lq)+4*tau*tau
                    record['tolerance']['determinant_m2'] = threshold
                    record['tolerance']['sine_dimensionless'] = max(physical['min_crossing_sine'],threshold/(lp*lq))
                    if determinant > 0:
                        record['tolerance']['parameter_dimensionless'] = 64*core.EPSILON+8*tau*(lp+lq)/determinant
                try:
                    found = intersect_segments(*xy,tau,physical['min_crossing_sine'])
                    record.update(found)
                except base.MagneticContractError as error:
                    reason = {'intersection.degenerate':'degenerate_segment','intersection.parallel':'parallel_or_collinear',
                              'intersection.ill_conditioned':'ill_conditioned','intersection.matrix':'ill_conditioned',
                              'intersection.parameters':'parameter_outside_segment'}.get(error.error['field'],'ill_conditioned')
                    reasons.add(reason)
                a,b = record['a'],record['b']
                if a is not None and b is not None and 'missing_height' not in reasons:
                    def height(p,q,alpha):
                        return p['z'] if p['z']==q['z'] else math.fsum(((1-alpha)*p['z'],alpha*q['z']))
                    delta = height(flight[1],flight[2],a)-height(tie[1],tie[2],b)
                    if not math.isfinite(delta):
                        raise core.SurveyError('metadata_ineligible','crossover')
                    record['height_difference_m'] = delta
                    if abs(delta) > physical['max_height_separation_m']:
                        reasons.add('height_mismatch')
                    if all(p['utc'] is not None for p in points):
                        origin = min(_utc_ns(p['utc']) for p in points)
                        times = [_utc_ns(p['utc'])-origin for p in points]
                        elapsed = abs(math.fsum(((1-a)*times[0],a*times[1],-(1-b)*times[2],-b*times[3])))*1e-9
                        record['time_separation_s'] = elapsed
                        if physical['max_time_separation_s'] is not None and elapsed > physical['max_time_separation_s']:
                            reasons.add('unsupported_time')
                    elif physical['max_time_separation_s'] is not None:
                        reasons.add('unsupported_time')
                    if not reasons:
                        record['disposition'] = 'admitted'
                        role = (flight[1]['line'],tie[1]['line'],flight[1]['sensor'])
                        prior_group = next((rid for rid,e,n in db.execute(
                            'SELECT id,e,n FROM representatives WHERE line_a=? AND line_b=? AND sensor=? ORDER BY rowid', role)
                            if math.hypot(record['easting_m']-e,record['northing_m']-n) <= tau),None)
                        if prior_group is None:
                            prior_group = record['crossover_id']
                            db.execute('INSERT INTO representatives VALUES (?,?,?,?,?,?)',
                                (prior_group,*role,record['easting_m'],record['northing_m']))
                        else:
                            reasons.add('duplicate_physical_constraint')
                        record['shared_endpoint_group_id'] = record['constraint_representative'] = prior_group
                record['reasons'] = [reason for reason in CROSSOVER_REASONS if reason in reasons]
                yield record

        table = io.write_table(output, 'crossovers', 'crossover_geometry', records()) if count else None
        result = dict(schema='m03-crossover-geometry-plan/1', geometry_sha256=inspection['geometry_sha256'],
            geometry_policy_sha256=base.digest(policy), segments=segments,candidates=count,table=table,
            value_access='not_opened',measurement_and_partition_admission='not_opened')
        if alignment is not None:
            result['navigation_sha256'] = base.digest(alignment[1])
        core._write_member(output,'crossover-plan.json',base.canonical_bytes(result))
        return result
