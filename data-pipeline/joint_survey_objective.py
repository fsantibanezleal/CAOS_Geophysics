"""Actual supplied development-data weighted objective; NOT an inverse solve.

No user kernels/callbacks, private M02 imports, I/O, model selection or sealed
observations. Exact objective protocol: own feature/objective-unit.md.
"""

import math

import numpy as np
import scipy.linalg as la

import gravity_forward
import magnetic_forward
import joint_survey_plan as planner
import joint_survey_structure as structure


BETAS=(.0001,.001,.01,.1,1.,10.,100.,1000.)
LAMBDAS=(0.,.001,.01,.1,1.,10.)


def _sha(value,field):
    planner._text(value,field)
    if len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError(field+': exact lowercase SHA256 required')


def _metadata(request):
    planner._keys(request,('schema','survey_request','development','models','direction_physical','weights'),'objective')
    planner._enum(request['schema'],('joint-survey-objective-request-1',),'objective.schema')
    req=request['survey_request']; planner._contract(req)
    n=len(req['prior']['density']['lower'])
    models=request['models']; planner._keys(models,('density_kg_m3','susceptibility_si'),'models')
    for key in models: planner._array(models[key],(n,),'models.'+key)
    planner._array(request['direction_physical'],(2*n,),'direction_physical')
    weights=request['weights']; planner._keys(weights,('beta_gravity','beta_magnetic','coupling'),'weights')
    for key in weights:
        planner._float(weights[key],0.,1000.,'weights.'+key)
        if weights[key] not in (LAMBDAS if key=='coupling' else BETAS):
            raise ValueError('weights: frozen candidate required')
    development=request['development'];planner._keys(development,('plan_sha256','gravity','magnetic'),'development')
    _sha(development['plan_sha256'],'development.plan_sha256')
    for modality in ('gravity','magnetic'):
        d=development[modality]
        planner._keys(d,('rows','observed','noise_values','observations_sha256','noise_sha256'),'development.'+modality)
        rows=d['rows']
        if type(rows) is not np.ndarray or rows.dtype!=np.dtype('int64'):
            raise TypeError('development.rows: native int64 ndarray required')
        if rows.ndim!=1 or not 2<=len(rows)<=min(2048,len(req[modality]['receivers_m'])):
            raise ValueError('development.rows: declared row length limit')
        m=len(rows); planner._array(d['observed'],(m,),'development.observed')
        shape=(m,m) if req[modality]['noise']['kind']=='full_covariance' else (m,)
        planner._array(d['noise_values'],shape,'development.noise_values')
        for key in ('observations_sha256','noise_sha256'): _sha(d[key],'development.'+key)
    planner._metadata_budget(request)


def _weights(survey,data,n_train):
    values=data['noise_values']
    if survey['noise']['kind']=='diagonal_sd':
        if np.any(values<=0): raise ValueError('noise: positive SD required, no floor')
        return ('diagonal',values[:n_train])
    if not np.array_equal(values,values.T): raise ValueError('noise: exact covariance symmetry required')
    # Whole declared development SPD, then only the marginal training block.
    # No validation observation can condition a training residual.
    la.cholesky(values,lower=True,check_finite=False)
    if (survey['noise']['cross_partition']=='declared_absent'
            and np.any(values[:n_train,n_train:]!=0)):
        raise ValueError('noise: declared absent cross-partition covariance is nonzero')
    return ('cholesky',la.cholesky(values[:n_train,:n_train],lower=True,check_finite=False))


def _whiten(weights,value):
    kind,w=weights
    if kind=='diagonal': return value/w[:,None] if value.ndim==2 else value/w
    return la.solve_triangular(w,value,lower=True,check_finite=False)


def _admit(request):
    _metadata(request)
    planner._finite(request)
    admitted=planner._snapshot(request)
    plan=planner.plan_joint_survey(admitted['survey_request'])
    dev=admitted['development']
    if dev['plan_sha256']!=plan['plan_sha256']: raise ValueError('development: stale bound plan')
    whitening={}
    for modality in ('gravity','magnetic'):
        s=plan[modality]; d=dev[modality]
        expected=np.r_[s['training_rows'],s['validation_rows']]
        if not np.array_equal(d['rows'],expected): raise ValueError('development: exact train then validation row IDs required')
        binding={'rows':d['rows'],'observed':d['observed'],'unit':s['unit'],'plan_sha256':plan['plan_sha256']}
        if planner._digest(binding)!=d['observations_sha256']: raise ValueError('development: observed identity drift')
        binding={'rows':d['rows'],'noise_values':d['noise_values'],'unit':s['noise']['unit'],
                 'kind':s['noise']['kind'],'plan_sha256':plan['plan_sha256']}
        if planner._digest(binding)!=d['noise_sha256']: raise ValueError('development: noise identity drift')
        whitening[modality]=_weights(s,d,len(s['training_rows']))
    for prop,key in (('density','density_kg_m3'),('susceptibility','susceptibility_si')):
        model=admitted['models'][key]; prior=plan['prior'][prop]
        if np.any((model<prior['lower'])|(model>prior['upper'])):
            raise ValueError('models: outside supplied physical bounds')
    return admitted,plan,whitening


def _regularization(mesh,geometry,lengths,q,reference,v):
    """Physical volume smallness plus two-active-neighbor face differences.

    Sparse linear work; never form a full dense combined Hessian. Actual accepted
    tensor centres/bounds/volumes define physical area/distance, not fictitious
    centre +/- half-width prisms or zero models outside active cells.
    """
    volumes=geometry['active_cell_volumes_m3']; total=float(np.sum(volumes)); delta=q-reference
    weight=volumes/total
    energy=.5*float(delta@(weight*delta)); gradient=weight*delta; hv=weight*v
    full=np.flatnonzero(mesh['active']); lookup={int(f):i for i,f in enumerate(full)}
    nx=len(mesh['hx_m']);ny=len(mesh['hy_m']);nz=len(mesh['hz_m']);dims=(nx,ny,nz)
    bounds=geometry['active_cell_bounds_m']; centres=geometry['active_cell_centres_m']
    for index,f in enumerate(full):
        cell=(int(f)%nx,(int(f)//nx)%ny,int(f)//(nx*ny))
        for axis,stride in enumerate((1,nx,nx*ny)):
            if cell[axis]+1>=dims[axis] or int(f)+stride not in lookup: continue
            other=lookup[int(f)+stride]
            distance=float(centres[other,axis]-centres[index,axis])
            extents=bounds[index,1::2]-bounds[index,::2]
            area=math.prod(float(extents[a]) for a in range(3) if a!=axis)
            if not math.isfinite(distance) or distance<=0: raise RuntimeError('regularization: invalid neighbor distance')
            w=area*lengths[axis]**2/(distance*total)
            difference=delta[other]-delta[index]; direction=v[other]-v[index]
            energy+=.5*w*difference**2
            gradient[index]-=w*difference;gradient[other]+=w*difference
            hv[index]-=w*direction;hv[other]+=w*direction
    return float(energy),gradient,hv


def evaluate_joint_objective(request: dict) -> dict:
    """Evaluate train-only actual physical F/g/Hv; return development predictions."""
    admitted,plan,whitening=_admit(request)
    req=admitted['survey_request'];models=admitted['models'];prior=plan['prior']
    rho=models['density_kg_m3'];chi=models['susceptibility_si'];n=len(rho)
    frame={key:plan['frame'][key] for key in ('kind','axes','length_unit','vertical_positive')}
    gravity=gravity_forward.forward_gravity({'schema':'gravity-prism-forward-request-1','frame':frame,
        'mesh':plan['mesh'],'receivers_m':plan['gravity']['receivers_m'],'density_kg_m3':rho,
        'engine':gravity_forward.ENGINE})
    magnetic=magnetic_forward.forward_magnetic({'schema':'magnetic-prism-forward-request-1','frame':frame,
        'mesh':plan['mesh'],'receivers_m':plan['magnetic']['receivers_m'],'susceptibility_si':chi,
        'inducing_field':plan['magnetic']['inducing_field'],'engine':magnetic_forward.ENGINE})
    cross=structure.evaluate_joint_structure({'schema':'joint-survey-structure-request-1',
        'survey_request':req,'density_kg_m3':rho,'susceptibility_si':chi,
        'direction_physical':admitted['direction_physical']})
    scales=np.r_[np.full(n,prior['density']['scale']),np.full(n,prior['susceptibility']['scale'])]
    q=np.r_[rho,chi]/scales;v=admitted['direction_physical']/scales
    reference=np.r_[prior['density']['reference'],prior['susceptibility']['reference']]/scales
    terms={};predictions={};gradients=[];hvs=[]
    weights=admitted['weights']
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        for modality,J,predicted,sl,prop in (
                ('gravity',gravity['jacobian_mgal_per_kg_m3'],gravity['gz_up_mgal'],slice(0,n),'density'),
                ('magnetic',magnetic['linear_jacobian_nt_per_si'],magnetic['linear_tmi_nt'],slice(n,2*n),'susceptibility')):
            data=admitted['development'][modality];rows=data['rows'];s=plan[modality]
            ntrain=len(s['training_rows']);residual=predicted[rows]-data['observed']
            r=_whiten(whitening[modality],residual[:ntrain])
            A=_whiten(whitening[modality],J[rows[:ntrain]]*scales[sl])
            terms['data_'+modality]=.5*float(r@r)
            reg,reggrad,reghv=_regularization(plan['mesh'],gravity['geometry'],prior['lengths_m'],q[sl],reference[sl],v[sl])
            terms['regularization_'+modality]=reg
            beta=weights['beta_'+modality]
            gradients.append((A.T@r+beta*reggrad)/scales[sl])
            hvs.append((A.T@(A@v[sl])+beta*reghv)/scales[sl])
            predictions[modality]={'rows':planner._snapshot(rows),'observed':planner._snapshot(data['observed']),
                'predicted':planner._snapshot(predicted[rows]),'signed_residual':planner._snapshot(residual),'unit':s['unit']}
        terms['coupling']=cross['objective']
        total=float(terms['data_gravity']+terms['data_magnetic']
            +weights['beta_gravity']*terms['regularization_gravity']
            +weights['beta_magnetic']*terms['regularization_magnetic']+weights['coupling']*terms['coupling'])
        gradient=np.concatenate(gradients)+weights['coupling']*cross['gradient_physical']
        base_hv=np.concatenate(hvs)
        exact_hv=base_hv+weights['coupling']*cross['exact_hessian_vector_physical']
        approximate_hv=base_hv+weights['coupling']*cross['approx_hessian_vector_physical']
    if (any(not math.isfinite(x) for x in (*terms.values(),total))
            or any(not np.isfinite(a).all() for a in (gradient,exact_hv,approximate_hv))):
        raise RuntimeError('objective: nonfinite actual physical state')
    return {'schema':'joint-survey-objective-1','plan_sha256':plan['plan_sha256'],'objective':total,'terms':terms,
            'gradient_physical':planner._snapshot(gradient),
            'exact_hessian_vector_physical':planner._snapshot(exact_hv),
            'approx_hessian_vector_physical':planner._snapshot(approximate_hv),'predictions':predictions,
            'diagnostics':{'inverse_completed':False,'field_eligible':False,'sealed_consumed':False,
                'cross_partition_dependence':any(plan[k]['noise']['cross_partition']=='possible_not_removed' for k in ('gravity','magnetic')),
                'training_rows_gravity':len(plan['gravity']['training_rows']),
                'training_rows_magnetic':len(plan['magnetic']['training_rows'])}}
