"""Disk hull and geometry support masks, prior to measurement access."""
from __future__ import annotations

from hashlib import sha256
import math
from fractions import Fraction
from pathlib import Path

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_geometry as geometry
import magnetic_line_survey_io as io
from magnetic_lines import _utc_ns

OUTSIDE_HULL = 1 << 10
BEYOND_RADIUS = 1 << 11
SAMPLING_UNRESOLVED = 1 << 12


def _sampling(db, request, lines, sensors):
    """Original-line spacing qualification, bounded summaries in producer SQL.

    No CV omissions become acquisition holes. Sampling is informational in
    the ordinary mask contract, not permission to fill geometric holes.
    """
    selected = [s['sensor_id'] for s in sensors].index(request['sensor_id'])
    db.execute('CREATE TABLE sampling (line INTEGER PRIMARY KEY,azimuth REAL,e REAL,n REAL,spacing REAL)')
    for (line,) in db.execute('SELECT DISTINCT line FROM rows WHERE sensor=? ORDER BY line',(selected,)):
        if lines[line]['kind'] == 'tie':
            continue
        count = db.execute('SELECT count(*) FROM rows WHERE line=? AND sensor=?',(line,selected)).fetchone()[0]
        center = tuple(math.fsum(v/count for v, in db.execute('SELECT '+axis+' FROM rows WHERE line=? AND sensor=? ORDER BY pos',
                                                           (line,selected))) for axis in ('e','n'))
        first = db.execute('SELECT e,n FROM rows WHERE line=? AND sensor=? ORDER BY ordinal LIMIT 1',(line,selected)).fetchone()
        last = db.execute('SELECT e,n FROM rows WHERE line=? AND sensor=? ORDER BY ordinal DESC LIMIT 1',(line,selected)).fetchone()
        de,dn = last[0]-first[0],last[1]-first[1]
        if math.hypot(de,dn) == 0:
            continue
        spacing = None
        prior = None
        for row in db.execute('SELECT pos,ordinal,e,n FROM rows WHERE line=? AND sensor=? ORDER BY ordinal',(line,selected)):
            if prior is not None and not db.execute('SELECT 1 FROM gaps WHERE id=?',(prior[0],)).fetchone():
                distance = math.hypot(row[2]-prior[2],row[3]-prior[3])
                spacing = distance if spacing is None else max(spacing,distance)
            prior = row
        db.execute('INSERT INTO sampling VALUES (?,?,?,?,?)',(line,math.degrees(math.atan2(de,dn))%360,*center,spacing))
    resolved = request['geometry_policy']['minimum_resolved_wavelength_m'] is not None
    if db.execute('SELECT count(*) FROM sampling').fetchone()[0] < 2:
        resolved = False
    wavelength = request['geometry_policy']['minimum_resolved_wavelength_m']
    for line,angle,e,n,spacing in db.execute('SELECT * FROM sampling ORDER BY line'):
        nearest = None
        radians = math.radians(angle)
        for other,azimuth,x,y,_ in db.execute('SELECT * FROM sampling WHERE line!=? ORDER BY line',(line,)):
            if abs((azimuth-angle+90)%180-90) > 5:
                resolved = False
                continue
            distance = abs((x-e)*math.cos(radians)-(y-n)*math.sin(radians))
            if not math.isfinite(distance):
                raise core.SurveyError('metadata_ineligible','seal')
            if distance > 0:
                nearest = distance if nearest is None else min(nearest,distance)
        if nearest is None or spacing is None or wavelength is None or wavelength < 2*max(nearest,spacing):
            resolved = False
    return resolved


def _gaps(db,request,sensors):
    """Original acquisition adjacencies, not deliberately omitted CV rows."""
    sensor = [s['sensor_id'] for s in sensors].index(request['sensor_id'])
    policy = request['geometry_policy']
    db.execute('CREATE TABLE gaps (id INTEGER PRIMARY KEY,e0 REAL,n0 REAL,e1 REAL,n1 REAL,mask INTEGER)')
    db.execute('CREATE VIRTUAL TABLE gap_boxes USING rtree(id,e0,e1,n0,n1)')
    radius = request['grid']['support_radius_m']
    prior = None
    for row in db.execute('SELECT pos,line,ordinal,utc,e,n,z,mask FROM rows WHERE sensor=? ORDER BY line,sensor,ordinal',(sensor,)):
        if prior is not None and prior[1] == row[1]:
            length = math.hypot(row[4]-prior[4],row[5]-prior[5])
            mask = 0
            if not math.isfinite(length):
                raise core.SurveyError('metadata_ineligible','seal')
            if length == 0:
                mask |= 1 << 2
            if length > policy['max_segment_gap_m'] or row[2] != prior[2]+1:
                mask |= 1 << 4
            if (row[7] | prior[7]) & 2:
                mask |= 1 << 6
            if policy['max_time_gap_s'] is not None:
                if (row[7] | prior[7]) & 1:
                    mask |= 1 << 5
                elif not 0 < _utc_ns(row[3])-_utc_ns(prior[3]) <= Fraction.from_float(policy['max_time_gap_s'])*1000000000:
                    mask |= 1 << 4
            if mask:
                db.execute('INSERT INTO gaps VALUES (?,?,?,?,?,?)',(prior[0],prior[4],prior[5],row[4],row[5],mask))
                db.execute('INSERT INTO gap_boxes VALUES (?,?,?,?,?)',(prior[0],min(prior[4],row[4])-radius,
                    max(prior[4],row[4])+radius,min(prior[5],row[5])-radius,max(prior[5],row[5])+radius))
        prior = row
    db.commit()


def _gap_mask(db,e,n,radius):
    mask = 0
    for e0,n0,e1,n1,reason in db.execute('SELECT g.e0,g.n0,g.e1,g.n1,g.mask FROM gap_boxes b JOIN gaps g ON b.id=g.id '
                                       'WHERE b.e0<=? AND b.e1>=? AND b.n0<=? AND b.n1>=?',(e,e,n,n)):
        delta = (e1-e0,n1-n0)
        length = math.hypot(*delta)
        direction = (0.,0.) if length == 0 else (delta[0]/length,delta[1]/length)
        fraction = 0. if length == 0 else math.fsum(((e-e0)*direction[0],(n-n0)*direction[1]))/length
        if not math.isfinite(fraction):
            raise core.SurveyError('metadata_ineligible','seal')
        weight = max(0.,min(1.,fraction))
        if math.hypot(e-e0-weight*delta[0],n-n0-weight*delta[1]) <= radius:
            mask |= reason
    return mask


def _cross(o,a,b):
    value = (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    if not math.isfinite(value):
        raise core.SurveyError('metadata_ineligible','seal')
    return value


def _hull(db):
    origin = db.execute('SELECT min(e),min(n) FROM training').fetchone()
    db.execute('CREATE TABLE hull_stack (side INTEGER,sequence INTEGER,e REAL,n REAL,PRIMARY KEY(side,sequence))')
    lengths = []
    for side,order in ((0,'ASC'),(1,'DESC')):
        length,prior = 0,None
        for e,n in db.execute(f'SELECT e,n FROM training ORDER BY e {order},n {order}'):
            point = (e-origin[0],n-origin[1])
            if point == prior:
                continue
            prior = point
            while length >= 2:
                last = list(db.execute('SELECT e,n FROM hull_stack WHERE side=? AND sequence>=? ORDER BY sequence', (side,length-2)))
                if _cross(last[0],last[1],point) > 0:
                    break
                db.execute('DELETE FROM hull_stack WHERE side=? AND sequence=?',(side,length-1))
                length -= 1
            db.execute('INSERT INTO hull_stack VALUES (?,?,?,?)',(side,length,*point))
            length += 1
        lengths.append(length)
    db.execute('CREATE TABLE hull (sequence INTEGER PRIMARY KEY,e REAL,n REAL)')
    position = 0
    for side,length in enumerate(lengths):
        for e,n in db.execute('SELECT e,n FROM hull_stack WHERE side=? AND sequence<? ORDER BY sequence',(side,length-1)):
            db.execute('INSERT INTO hull VALUES (?,?,?)',(position,e,n))
            position += 1
    if position < 3:
        raise core.SurveyError('metadata_ineligible','seal')
    return origin


def _support(db,e,n,origin,radius):
    point = (e-origin[0],n-origin[1])
    first = db.execute('SELECT e,n FROM hull ORDER BY sequence LIMIT 1').fetchone()
    previous = first
    inside = True
    for current in db.execute('SELECT e,n FROM hull WHERE sequence>0 ORDER BY sequence'):
        if _cross(previous,current,point) < 0:
            inside = False
            break
        previous = current
    if inside and _cross(previous,first,point) < 0:
        inside = False
    # Conservative R-tree float32 boxes, then exact float64 distances. Only
    # existence within the frozen radius is needed, not a fabricated distance
    # to an omitted nearest point beyond it.
    nearby = any(math.hypot(e-x,n-y) <= radius for x,y in db.execute(
        'SELECT t.e,t.n FROM training_boxes b JOIN training t ON b.id=t.pos '
        'WHERE b.e0<=? AND b.e1>=? AND b.n0<=? AND b.n1>=?', (e+radius,e-radius,n+radius,n-radius)))
    return (0 if inside else OUTSIDE_HULL) | (0 if nearby else BEYOND_RADIUS)


def grid_ids(config):
    identity = sha256()
    for j in range(config['ny']):
        for i in range(config['nx']):
            identity.update(f'g.{j}.{i}'.encode('ascii').ljust(64,b'\0'))
    return identity.hexdigest()


def plan_support(root,inspection,request,partition_root,planned,output,*,temp_root):
    request = schema.validate('SurveyRequest',request)
    output = io.external_path(output)
    if output.exists():
        raise core.SurveyError('custody_mismatch','seal')
    partition_root = io.external_path(partition_root)
    stored = base.strict_json(base.read_bounded(core._plain_path(partition_root/'partition-plan.json'),2097152))
    if stored != planned or planned['request_sha256'] != base.digest(request) or planned['geometry_sha256'] != inspection['geometry_sha256']:
        raise core.SurveyError('custody_mismatch','seal')
    output.mkdir()
    reader = io.Reader(partition_root)
    grid = request['grid']
    radius = grid['support_radius_m']
    results = []
    grid_mask = None
    spectrum_qualified = False
    with geometry.geometry_index(root,inspection,temp_root=temp_root) as (db,_,lines,sensors):
        _gaps(db,request,sensors)
        sampling_resolved = _sampling(db,request,lines,sensors)
        for number,part in enumerate(planned['partitions']):
            db.execute('CREATE TABLE training (pos INTEGER PRIMARY KEY,e REAL,n REAL)')
            db.execute('CREATE INDEX training_xy ON training(e,n)')
            db.execute('CREATE VIRTUAL TABLE training_boxes USING rtree(id,e0,e1,n0,n1)')
            for pos in reader.cells(part['training']):
                if type(pos) is not int or not 0 <= pos < inspection['rows']:
                    raise core.SurveyError('custody_mismatch','seal')
                e,n = db.execute('SELECT e,n FROM rows WHERE pos=?',(pos,)).fetchone()
                db.execute('INSERT INTO training VALUES (?,?,?)',(pos,e,n))
                db.execute('INSERT INTO training_boxes VALUES (?,?,?,?,?)',(pos,e,e,n,n))
            db.commit()
            origin = _hull(db)
            eligible = total = 0
            writer = io.Writer(output,f'f{number}-support',role='qc_mask',shape=part['validation']['shape'],dtype='uint32',unit='identity')
            for pos in reader.cells(part['validation']):
                e,n = db.execute('SELECT e,n FROM rows WHERE pos=?',(pos,)).fetchone()
                mask = _support(db,e,n,origin,radius)
                writer.append(io.encoded_cell(mask,'uint32'))
                eligible += int(mask==0)
                total += 1
            coverage = eligible/total
            if coverage < request['split']['minimum_supported_fraction']:
                raise core.SurveyError('metadata_ineligible','seal')
            support = writer.finish(part['validation']['ordered_ids_sha256'])
            results.append(dict(fold_id=part['fold_id'],validation_mask=support,scored=eligible,excluded=total-eligible,coverage=coverage))
            if number==0:
                writer = io.Writer(output,'grid-support',role='grid_mask',shape=[grid['ny'],grid['nx']],dtype='uint32',unit='identity')
                spectrum = request['spectrum']
                spectrum_qualified = spectrum is not None
                for j in range(grid['ny']):
                    n = grid['origin_n_m']+j*grid['spacing_n_m']
                    row_bytes = bytearray()
                    for i in range(grid['nx']):
                        e = grid['origin_e_m']+i*grid['spacing_e_m']
                        if not math.isfinite(e) or not math.isfinite(n):
                            raise core.SurveyError('metadata_ineligible','seal')
                        mask = _support(db,e,n,origin,radius) | _gap_mask(db,e,n,radius)
                        if not sampling_resolved:
                            mask |= SAMPLING_UNRESOLVED
                        row_bytes.extend(io.encoded_cell(mask,'uint32'))
                        if spectrum is not None:
                            rectangle = spectrum['rectangle']
                            if rectangle['e_start'] <= i < rectangle['e_start']+rectangle['nx'] and \
                               rectangle['n_start'] <= j < rectangle['n_start']+rectangle['ny'] and mask & ~SAMPLING_UNRESOLVED:
                                spectrum_qualified = False
                    writer.append(row_bytes)
                grid_mask = writer.finish(grid_ids(grid))
            for table in ('hull','hull_stack','training_boxes','training'):
                db.execute('DROP TABLE '+table)
            db.commit()
    result = dict(schema='m03-geometry-support-plan/1',geometry_sha256=inspection['geometry_sha256'],
        request_sha256=base.digest(request),partitions=results,grid_mask=grid_mask,
        spectrum_geometrically_qualified=spectrum_qualified,sampling_resolved=sampling_resolved,value_access='not_opened')
    core._write_member(output,'support-plan.json',base.canonical_bytes(result))
    return result
