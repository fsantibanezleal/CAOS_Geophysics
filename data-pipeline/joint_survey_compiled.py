"""Admitted reusable actual physical joint objective, no I/O or solver injection."""
import math

import discretize
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import LinearOperator
from simpeg import maps
from simpeg.regularization import CrossGradient

import gravity_forward
import magnetic_forward
import joint_survey_objective as objective
import joint_survey_plan as planner


def _regularizer(mesh,geometry,lengths):
    volumes=geometry['active_cell_volumes_m3'];total=float(np.sum(volumes))
    full=np.flatnonzero(mesh['active']);lookup={int(f):i for i,f in enumerate(full)}
    n=len(full);nx=len(mesh['hx_m']);ny=len(mesh['hy_m']);nz=len(mesh['hz_m'])
    bounds=geometry['active_cell_bounds_m'];centres=geometry['active_cell_centres_m']
    row=list(range(n));col=list(range(n));values=list(np.sqrt(volumes/total));nextrow=n
    for index,f in enumerate(full):
        cell=(int(f)%nx,(int(f)//nx)%ny,int(f)//(nx*ny))
        for axis,stride in enumerate((1,nx,nx*ny)):
            if cell[axis]+1>=(nx,ny,nz)[axis] or int(f)+stride not in lookup: continue
            other=lookup[int(f)+stride];distance=float(centres[other,axis]-centres[index,axis])
            extents=bounds[index,1::2]-bounds[index,::2]
            area=math.prod(float(extents[a]) for a in range(3) if a!=axis)
            w=math.sqrt(area*lengths[axis]**2/(distance*total))
            row.extend((nextrow,nextrow));col.extend((index,other));values.extend((-w,w));nextrow+=1
    return sparse.csr_matrix((values,(row,col)),shape=(nextrow,n))


class JointDevelopmentProblem:
    """Trusted native model, not an upload hook or a fit/certificate."""
    def __init__(self,admitted,plan,whitening):
        self.plan=plan;self.development=admitted['development'];self.survey_request=admitted['survey_request']
        self.n=len(plan['prior']['density']['start'])
        self.scales=np.r_[np.full(self.n,plan['prior']['density']['scale']),
                          np.full(self.n,plan['prior']['susceptibility']['scale'])]
        self.lower=np.r_[plan['prior']['density']['lower'],plan['prior']['susceptibility']['lower']]/self.scales
        self.upper=np.r_[plan['prior']['density']['upper'],plan['prior']['susceptibility']['upper']]/self.scales
        self.start=np.r_[plan['prior']['density']['start'],plan['prior']['susceptibility']['start']]/self.scales
        self.reference=np.r_[plan['prior']['density']['reference'],plan['prior']['susceptibility']['reference']]/self.scales
        frame={k:plan['frame'][k] for k in ('kind','axes','length_unit','vertical_positive')}
        gravity=gravity_forward.forward_gravity({'schema':'gravity-prism-forward-request-1','frame':frame,
            'mesh':plan['mesh'],'receivers_m':plan['gravity']['receivers_m'],
            'density_kg_m3':plan['prior']['density']['start'],'engine':gravity_forward.ENGINE})
        magnetic=magnetic_forward.forward_magnetic({'schema':'magnetic-prism-forward-request-1','frame':frame,
            'mesh':plan['mesh'],'receivers_m':plan['magnetic']['receivers_m'],
            'susceptibility_si':plan['prior']['susceptibility']['start'],
            'inducing_field':plan['magnetic']['inducing_field'],'engine':magnetic_forward.ENGINE})
        self.geometry=gravity['geometry']
        self.J={'gravity':gravity['jacobian_mgal_per_kg_m3'],'magnetic':magnetic['linear_jacobian_nt_per_si']}
        self.A={};self.d={}
        for m,sl in (('gravity',slice(0,self.n)),('magnetic',slice(self.n,2*self.n))):
            count=len(plan[m]['training_rows']);data=self.development[m]
            self.A[m]=objective._whiten(whitening[m],self.J[m][data['rows'][:count]]*self.scales[sl])
            self.d[m]=objective._whiten(whitening[m],data['observed'][:count])
        self.R=_regularizer(plan['mesh'],self.geometry,plan['prior']['lengths_m'])
        mesh=discretize.TensorMesh([plan['mesh'][k] for k in ('hx_m','hy_m','hz_m')],origin=plan['mesh']['origin_m'])
        wires=maps.Wires(('density',self.n),('susceptibility',self.n))
        self.cross_exact=CrossGradient(mesh,wires,active_cells=plan['mesh']['active'],approx_hessian=False)
        self.cross_approximate=CrossGradient(mesh,wires,active_cells=plan['mesh']['active'],approx_hessian=True)
        self.factor=plan['prior']['coupling_length_m']**4/float(np.sum(mesh.cell_volumes[plan['mesh']['active']]))
        self.development_sha256=planner._digest({'survey_request':self.survey_request,'development':self.development})
        for value in (self.scales,self.lower,self.upper,self.start,self.reference,*self.A.values(),*self.d.values()):
            value.flags.writeable=False

    def _admit_state(self,q,weights):
        planner._array(q,(2*self.n,),'compiled.q');planner._finite(q)
        if np.any((q<self.lower)|(q>self.upper)): raise ValueError('compiled: model outside exact normalized bounds')
        planner._keys(weights,('beta_gravity','beta_magnetic','coupling'),'compiled.weights')
        for key,value in weights.items():
            planner._float(value,0.,1000.,key)
            if value not in (objective.LAMBDAS if key=='coupling' else objective.BETAS):
                raise ValueError('compiled: frozen weight required')

    def state(self,q,weights):
        self._admit_state(q,weights)
        terms={};gradient=np.zeros(2*self.n)
        with np.errstate(over='raise',invalid='raise',divide='raise'):
            for m,sl in (('gravity',slice(0,self.n)),('magnetic',slice(self.n,2*self.n))):
                residual=self.A[m]@q[sl]-self.d[m];delta=self.R@(q[sl]-self.reference[sl])
                terms['data_'+m]=.5*float(residual@residual)
                terms['regularization_'+m]=.5*float(delta@delta)
                gradient[sl]=self.A[m].T@residual+weights['beta_'+m]*(self.R.T@delta)
            terms['coupling']=float(self.factor*self.cross_exact(q))
            gradient+=weights['coupling']*self.factor*self.cross_exact.deriv(q)
            total=float(terms['data_gravity']+terms['data_magnetic']
                +weights['beta_gravity']*terms['regularization_gravity']
                +weights['beta_magnetic']*terms['regularization_magnetic']+weights['coupling']*terms['coupling'])
        if not math.isfinite(total) or not np.isfinite(gradient).all() or any(not math.isfinite(x) for x in terms.values()):
            raise RuntimeError('compiled: nonfinite actual objective')
        return {'objective':total,'terms':terms,'gradient_normalized':planner._snapshot(gradient),
                'search_hessian':self.hessian(q,weights)}

    def hessian(self,q,weights,*,exact=False):
        self._admit_state(q,weights);point=planner._snapshot(q);frozen=dict(weights)
        cross=self.cross_exact if exact else self.cross_approximate
        def action(v):
            planner._array(v,(2*self.n,),'compiled.direction');planner._finite(v)
            result=np.zeros(2*self.n)
            for m,sl in (('gravity',slice(0,self.n)),('magnetic',slice(self.n,2*self.n))):
                result[sl]=self.A[m].T@(self.A[m]@v[sl])+frozen['beta_'+m]*(self.R.T@(self.R@v[sl]))
            result+=frozen['coupling']*self.factor*cross.deriv2(point,v)
            if not np.isfinite(result).all(): raise RuntimeError('compiled: nonfinite actual Hv')
            return result
        return LinearOperator((2*self.n,2*self.n),matvec=action,rmatvec=action,dtype=np.float64)

    def predict(self,q):
        planner._array(q,(2*self.n,),'compiled.q');planner._finite(q)
        if np.any((q<self.lower)|(q>self.upper)): raise ValueError('compiled: model outside bounds')
        return {m:planner._snapshot(self.J[m]@(q[sl]*self.scales[sl]))
            for m,sl in (('gravity',slice(0,self.n)),('magnetic',slice(self.n,2*self.n)))}


def compile_joint_development(request: dict) -> JointDevelopmentProblem:
    planner._keys(request,('schema','survey_request','development'),'compile')
    planner._enum(request['schema'],('joint-survey-compile-request-1',),'compile.schema')
    planner._contract(request['survey_request']);planner._metadata_budget(request)
    prior=request['survey_request']['prior'];n=len(prior['density']['start'])
    value={'schema':'joint-survey-objective-request-1','survey_request':request['survey_request'],
        'development':request['development'],'models':{'density_kg_m3':prior['density']['start'],
            'susceptibility_si':prior['susceptibility']['start']},'direction_physical':np.zeros(2*n),
        'weights':{'beta_gravity':.0001,'beta_magnetic':.0001,'coupling':0.}}
    admitted,plan,whitening=objective._admit(value)
    return JointDevelopmentProblem(admitted,plan,whitening)
