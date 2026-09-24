"""Validated observation ingestion. Raw external observations remain local and ignored."""
from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
import tarfile
import urllib.request
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def validate_table(table):
    table=np.asarray(table,dtype=float)
    if table.ndim!=2 or table.shape[1]!=5 or len(table)<4:raise ValueError('Require >=4 rows: east_m,north_m,up_m,value,sigma')
    if not np.isfinite(table).all():raise ValueError('Non-finite observation rejected')
    if np.any(table[:,4]<=0):raise ValueError('Nonpositive uncertainty rejected')
    if len(np.unique(table[:,:3],axis=0))!=len(table):raise ValueError('Duplicate station coordinates rejected')
    # Stable station order is independent of source line order.
    return table[np.lexsort((table[:,0],table[:,1]))]


def read_csv(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as stream:
        reader=csv.DictReader(stream)
        expected=['east_m','north_m','up_m','value','sigma']
        if reader.fieldnames!=expected:raise ValueError('CSV headers must be '+','.join(expected))
        return validate_table([[float(row[k]) for k in expected] for row in reader])


def external():
    ledger=json.loads((ROOT/'data/source-ledger.json').read_text())
    reports=[]
    for source in ledger['sources']:
        if not source.get('raw_path'):continue
        path=ROOT/source['raw_path'];path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():urllib.request.urlretrieve(source['url'],path)
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        if sha!=source['sha256']:raise ValueError('Upstream checksum changed: '+source['name'])
        with tarfile.open(path,'r:gz') as archive:
            member=next(m for m in archive.getmembers() if m.name.endswith('_data.obs'))
            if member.size>10_000_000:raise ValueError('Observation member too large')
            observations=np.loadtxt(io.BytesIO(archive.extractfile(member).read()))
        # Tutorial archives contain XYZ and value, not measured uncertainty.
        sigma=max(np.std(observations[:,3])*.03,1e-12)
        table=validate_table(np.c_[observations,np.full(len(observations),sigma)])
        out=ROOT/'data/raw'/path.name.replace('.tar.gz','.npz');out.parent.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(out,locations=table[:,:3],observed=table[:,3],sigma=table[:,4])
        reports.append(dict(source=source['url'],archive_sha256=sha,member=member.name,rows=len(table),columns=['east_m','north_m','up_m','value','sigma'],units='mGal' if 'gravity' in path.name else 'nT',synthetic_tutorial=True,preprocessed_path=out.relative_to(ROOT).as_posix(),preprocessed_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),uncertainty_policy='3% observation SD assigned for local experimentation, not instrument uncertainty',redistribution='raw and preprocessed values remain ignored; upstream license not assumed'))
    report=ROOT/'data/external-preprocessing.json'
    report.write_text(json.dumps(reports,indent=2))
    print(json.dumps(reports,indent=2))


def invert_csv(path,family,out):
    from discretize import TensorMesh
    from simpeg import maps
    from simpeg.potential_fields import gravity,magnetics
    from potential import invert
    a=read_csv(path);xy=a[:,:2]
    width=np.maximum(np.ptp(xy,axis=0)*1.25,100)
    spacing=[width[0]/14,width[1]/12,min(width)/10]
    top=float(np.min(a[:,2])-spacing[2]/2)
    origin=[xy[:,0].mean()-width[0]/2,xy[:,1].mean()-width[1]/2,top-8*spacing[2]]
    mesh=TensorMesh([np.full(14,spacing[0]),np.full(12,spacing[1]),np.full(8,spacing[2])],origin=origin)
    if family=='gravity':
        survey=gravity.Survey(gravity.sources.SourceField([gravity.receivers.Point(a[:,:3],components='gz')]))
        G=gravity.simulation.Simulation3DIntegral(mesh,survey=survey,rhoMap=maps.IdentityMap(nP=mesh.nC),engine='geoana').G
    else:
        survey=magnetics.Survey(magnetics.sources.UniformBackgroundField([magnetics.receivers.Point(a[:,:3],components='tmi')],amplitude=50000,inclination=60,declination=12))
        G=magnetics.simulation.Simulation3DIntegral(mesh,survey=survey,chiMap=maps.IdentityMap(nP=mesh.nC),engine='geoana').G
    weighted=G/a[:,4,None];d=a[:,3]/a[:,4]
    results={}
    for name,sparse in [('l2',False),('irls',True)]:
        result=invert(weighted,d,1,.018,sparse)
        result['predicted']=(G@result['model']).tolist()
        result['residual']=(a[:,3]-result['predicted']).tolist()
        results[name]=result
    record=dict(schema='inverse-earth.user-survey/v2',family=family,input_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),coordinate_convention='ENU; gravity gz positive upward; magnetics fixed 50000 nT / 60 deg inclination / 12 deg declination',mesh=dict(shape=[8,12,14],spacing=spacing,origin=origin),results=results,limitations='No terrain mask, regional removal or automatic field-direction estimation. User must preprocess these explicitly. No known truth or model accuracy claim.')
    Path(out).write_text(json.dumps(record,separators=(',',':')))
    print('Validated and inverted',len(a),'stations ->',out)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--external',action='store_true');parser.add_argument('--csv',type=Path);parser.add_argument('--family',choices=['gravity','magnetics'],default='gravity');parser.add_argument('--output',default='data/raw/user-inversion.json');args=parser.parse_args()
    if args.external:external()
    if args.csv:
        Path(args.output).parent.mkdir(parents=True,exist_ok=True)
        invert_csv(args.csv,args.family,args.output)
