"""Actual pinned SimPEG structural objective/derivatives; not optimization.

No private M02 imports, supplied kernels, I/O, fitting or field eligibility.
Physical models/direction use density kg/m3 then SI susceptibility. The plotted
cell-centre cross-gradient is a DIFFERENT quantity from the optimized scalar.
"""

import discretize
import numpy as np
from simpeg import maps
from simpeg.regularization import CrossGradient

import joint_survey_plan as planner


def evaluate_joint_structure(request: dict) -> dict:
    """Return dimensionless actual coupling and physical gradient/Hv snapshots."""
    planner._keys(request,('schema','survey_request','density_kg_m3','susceptibility_si',
                          'direction_physical'),'structure')
    planner._enum(request['schema'],('joint-survey-structure-request-1',),'structure.schema')
    survey=request['survey_request']
    # Own planner metadata only, before ANY planner scans/copies/hash/mesh calls.
    planner._contract(survey)
    n=len(survey['prior']['density']['lower'])
    for key in ('density_kg_m3','susceptibility_si'): planner._array(request[key],(n,),'structure.'+key)
    planner._array(request['direction_physical'],(2*n,),'structure.direction_physical')
    planner._metadata_budget(request)
    planner._finite(request)
    plan=planner.plan_joint_survey(survey)
    rho=planner._snapshot(request['density_kg_m3']); chi=planner._snapshot(request['susceptibility_si'])
    direction=planner._snapshot(request['direction_physical'])
    for key,model in (('density',rho),('susceptibility',chi)):
        p=plan['prior'][key]
        if np.any((model<p['lower'])|(model>p['upper'])):
            raise ValueError('structure: physical model outside declared prior bounds')
    mesh=plan['mesh']
    tensor=discretize.TensorMesh([mesh[k] for k in ('hx_m','hy_m','hz_m')],origin=mesh['origin_m'])
    wires=maps.Wires(('density',n),('susceptibility',n))
    exact=CrossGradient(tensor,wires,active_cells=mesh['active'],approx_hessian=False)
    approximate=CrossGradient(tensor,wires,active_cells=mesh['active'],approx_hessian=True)
    scales=np.r_[np.full(n,plan['prior']['density']['scale']),
                 np.full(n,plan['prior']['susceptibility']['scale'])]
    q=np.r_[rho,chi]/scales; v=direction/scales
    volumes=tensor.cell_volumes[mesh['active']]
    factor=plan['prior']['coupling_length_m']**4/float(np.sum(volumes))
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        value=float(factor*exact(q))
        gradient=np.asarray(factor*exact.deriv(q)/scales)
        exact_hv=np.asarray(factor*exact.deriv2(q,v)/scales)
        approximate_hv=np.asarray(factor*approximate.deriv2(q,v)/scales)
        diagnostic=np.asarray(exact.calculate_cross_gradient(q,normalized=False))
    if (not np.isfinite(value) or any(a.dtype!=np.float64 or a.shape!=(2*n,)
            or not np.isfinite(a).all() for a in (gradient,exact_hv,approximate_hv))
            or diagnostic.dtype!=np.float64 or diagnostic.shape!=(n,)
            or not np.isfinite(diagnostic).all()):
        raise RuntimeError('structure: nonfinite or malformed actual engine output')
    return {'schema':'joint-survey-structure-1','plan_sha256':plan['plan_sha256'],'objective':value,
            'gradient_physical':planner._snapshot(gradient),
            'exact_hessian_vector_physical':planner._snapshot(exact_hv),
            'approx_hessian_vector_physical':planner._snapshot(approximate_hv),
            'cell_centre_cross_gradient':planner._snapshot(diagnostic),'optimizer_completed':False}
