"""Authored refined Choclo controls, NOT production inference or field data.

External sealed/truth channel is deliberately not a calibration request.
Frozen constants/source and nonclaims: feature/case-matrix.md.
"""
import hashlib
import math

import choclo
from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY as MU0
import numpy as np

import joint_survey_plan as planner


FAMILIES = ('co_structural','disjoint','flat_null','wrong_field')
REGIMES = ('dense','sparse_blocked','shifted_geometry')


def _direction(inclination,declination):
    i,d=map(math.radians,(inclination,declination))
    return np.array([math.cos(i)*math.sin(d),math.cos(i)*math.cos(d),-math.sin(i)])


def _source(widths,origin):
    refined=[np.repeat(w/2,2) for w in widths]
    edges=[o+np.r_[0.,np.cumsum(w)] for o,w in zip(origin,refined)]
    nx,ny,nz=map(len,refined)
    bounds=[];parents=[]
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                bounds.append([edges[0][i],edges[0][i+1],edges[1][j],edges[1][j+1],edges[2][k],edges[2][k+1]])
                parents.append(i//2+3*(j//2)+6*(k//2))
    return np.array(bounds),np.array(parents,dtype=np.int64)


def _blob(centres,centre,lengths):
    return np.exp(-.5*np.sum(((centres-np.array(centre))/np.array(lengths))**2,axis=1))


def _descriptor(value):
    if type(value) is dict: return {key:_descriptor(v) for key,v in value.items()}
    if type(value) is np.ndarray:
        return {'dtype':value.dtype.str,'shape':list(value.shape),'sha256':hashlib.sha256(value.tobytes(order='C')).hexdigest()}
    return value


def make_joint_control(index: int) -> dict:
    """Create one fixed synthetic control; never optimize, select or export."""
    if type(index) is not int: raise TypeError('control: exact builtin index required')
    if not 0<=index<24: raise ValueError('control: frozen index0..23')
    planner._runtime()
    if type(choclo.__version__) is not str or choclo.__version__!='v0.3.2':
        raise RuntimeError('control: unreviewed Choclo oracle version')
    family=FAMILIES[index//6];regime=REGIMES[(index//2)%3];covariance=bool(index%2)
    seed=1101+index;rng=np.random.default_rng(seed)
    widths=[np.array([40.,70.,90.]),np.array([30.,50.]),np.array([60.,110.])]
    origin=np.array([-140.,-180.,-260.]);bounds,parents=_source(widths,origin)
    centres=(bounds[:,::2]+bounds[:,1::2])/2
    a=_blob(centres,(-90.,-150.,-180.),(30.,22.,35.))
    b=_blob(centres,(15.,-125.,-125.),(24.,18.,24.))
    c=_blob(centres,(-20.,-160.,-215.),(20.,15.,20.))
    d=_blob(centres,(25.,-165.,-230.),(18.,13.,18.))
    rho=600*a-350*b;chi=.012*a+.008*b
    if family=='disjoint': rho+=400*c;chi=.015*d
    elif family=='flat_null': rho[:]=0.;chi[:]=.005
    declared_direction=_direction(60.,12.)
    source_direction=_direction(25.,-35.) if family=='wrong_field' else declared_direction.copy()
    source_magnetization=chi[:,None]*50000.*1e-9/MU0*source_direction
    sparse=regime=='sparse_blocked'
    lines=np.array([-150.,-60.,90.]) if sparse else np.array([-210.,-130.,-50.,30.,110.,190.])
    xs=np.linspace(-230.,230.,8)
    if sparse: xs=xs[[0,3,7]]
    rx=np.array([[x,y,120.+10.*math.sin(j)] for y in lines for j,x in enumerate(xs)])
    count=len(rx);groups=np.repeat(np.arange(len(lines),dtype=np.int64),len(xs));partition=groups%3
    measured={'gravity':rx.copy(),'magnetic':rx+np.array([5.,0.,0.])}
    values={};noises={};clean={}
    for modality,sigma in (('gravity',.005),('magnetic',1.)):
        prediction=[]
        for receiver in measured[modality]:
            if modality=='gravity':
                value=sum(choclo.prism.gravity_u(*receiver,*box,float(density)) for box,density in zip(bounds,rho))*1e5
            else:
                field=np.zeros(3)
                for box,magnetization in zip(bounds,source_magnetization):
                    field+=np.array(choclo.prism.magnetic_field(*receiver,*box,*magnetization))
                value=float(field@declared_direction)*1e9
            prediction.append(value)
        clean[modality]=np.array(prediction)
        noise=sigma**2*(.65*np.eye(count)+.35*np.ones((count,count))) if covariance else np.full(count,sigma)
        draw=rng.normal(size=count)
        error=np.linalg.cholesky(noise)@draw if covariance else noise*draw
        values[modality]=clean[modality]+error;noises[modality]=noise
    frame={'kind':'local_cartesian','axes':('east','north','up'),'length_unit':'m','vertical_positive':'up',
        'reference_id':'authored-joint-control-enu','horizontal_datum':'authored Cartesian origin, no acquired CRS',
        'vertical_datum':'authored local height, not a field datum'}
    survey={'schema':'joint-survey-plan-request-1','frame':frame,
        'mesh':{'origin_m':origin,'hx_m':widths[0],'hy_m':widths[1],'hz_m':widths[2],'active':np.ones(12,dtype=bool)},
        'prior':{'density':{'lower':np.full(12,-1500.),'upper':np.full(12,1500.),'start':np.zeros(12),
                           'reference':np.zeros(12),'scale':750.},
            'susceptibility':{'lower':np.zeros(12),'upper':np.full(12,.1),'start':np.full(12,.005),
                              'reference':np.full(12,.005),'scale':.03},
            'lengths_m':np.array([60.,110.,75.]),'coupling_length_m':100.,
            'basis':'fixed authored physical prior, no truth-trained scale'},'policy':dict(planner.POLICY)}
    source_descriptors={}
    for modality,unit,component in (('gravity','mGal','gz_up'),('magnetic','nT','linear_tmi')):
        original={'receivers_m':measured[modality],'observed':values[modality],
                  'noise_values':noises[modality],'unit':unit,'source_magnetization_direction_enu':source_direction}
        source_bytes=planner._json(_descriptor(original)).encode('utf-8')
        source_descriptors[modality]=source_bytes.decode('utf-8')
        correction=planner._json({'schema':'authored-joint-correction-1','synthetic':True,
                                 'field_corrections_applied':False}).encode('utf-8')
        declared=measured[modality]+np.array([20.,-15.,12.]) if regime=='shifted_geometry' else measured[modality].copy()
        survey[modality]={'source':{'source_id':f'authored-joint-{index:02d}-{modality}',
            'citation':'Authored refined Choclo source control, not field observations',
            'raw_sha256':hashlib.sha256(source_bytes).hexdigest(),'raw_bytes':len(source_bytes),
            'rights':'redistributable','correction_sha256':hashlib.sha256(correction).hexdigest()},
            'reference_id':frame['reference_id'],'component':component,'unit':unit,'receivers_m':declared,
            'mask':np.zeros(count,dtype=bool),'missing_reasons':('',)*count,'groups':groups.copy(),
            'partition':partition.copy(),'noise':{'kind':'full_covariance' if covariance else 'diagonal_sd',
                'unit':unit+'^2' if covariance else unit,'basis':'conditional_gaussian',
                'cross_partition':'possible_not_removed' if covariance else 'declared_absent',
                'citation':'fixed authored Gaussian draw, sigma and covariance before fitting'}}
        if modality=='magnetic':
            survey[modality]['inducing_field']={'amplitude_nt':50000.,'inclination_deg':60.,'declination_deg':12.}
    plan=planner.plan_joint_survey(survey)
    development={'plan_sha256':plan['plan_sha256']};sealed={}
    for modality in ('gravity','magnetic'):
        s=plan[modality];rows=np.r_[s['training_rows'],s['validation_rows']];held=s['sealed_rows']
        noise=noises[modality]
        marginal=noise[np.ix_(rows,rows)] if covariance else noise[rows]
        observed=values[modality][rows]
        development[modality]={'rows':rows,'observed':observed,'noise_values':marginal,
            'observations_sha256':planner._digest({'rows':rows,'observed':observed,'unit':s['unit'],
                                                   'plan_sha256':plan['plan_sha256']}),
            'noise_sha256':planner._digest({'rows':rows,'noise_values':marginal,'unit':s['noise']['unit'],
                                           'kind':s['noise']['kind'],'plan_sha256':plan['plan_sha256']})}
        sealed[modality]={'rows':held,'observed':values[modality][held],
            'noise_values':noise[np.ix_(held,held)] if covariance else noise[held],
            'unit':s['unit'],'noise_unit':s['noise']['unit']}
    volumes=np.prod(bounds[:,1::2]-bounds[:,::2],axis=1)
    coarse_rho=np.array([float(volumes[parents==i]@rho[parents==i])/float(np.sum(volumes[parents==i])) for i in range(12)])
    coarse_chi=np.array([float(volumes[parents==i]@chi[parents==i])/float(np.sum(volumes[parents==i])) for i in range(12)])
    result={'schema':'joint-survey-authored-control-1','case_id':f'joint-control-{index:02d}',
        'family':family,'regime':regime,'seed':seed,'survey_request':survey,'development':development,'sealed':sealed,
        'truth':{'source_bounds_m':bounds,'source_density_kg_m3':rho,'source_susceptibility_si':chi,
            'source_to_coarse_cell':parents,'coarse_density_kg_m3':coarse_rho,'coarse_susceptibility_si':coarse_chi,
            'source_magnetization_direction_enu':source_direction,'declared_field_direction_enu':declared_direction},
        'provenance':{'generator':'authored-refined-choclo-control-1','source_engine':'Choclo0.3.2',
            'source_representation':'native-array-descriptor-json, not provider measurement file',
            'original_source_descriptors':source_descriptors,
            'gravity_measured_receivers_m':measured['gravity'],'magnetic_measured_receivers_m':measured['magnetic'],
            'original_gravity_observed_mgal':values['gravity'],'original_magnetic_observed_nt':values['magnetic'],
            'gravity_clean_mgal':clean['gravity'],'magnetic_clean_nt':clean['magnetic']},
        'diagnostics':{'synthetic':True,'inverse_completed':False,'field_eligible':False}}
    planner._finite(result)
    return planner._snapshot(result)
