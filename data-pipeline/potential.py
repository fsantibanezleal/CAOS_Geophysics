"""SimPEG 3D integral operators and explicit weighted inverse objectives."""
from __future__ import annotations

import numpy as np
from simpeg import maps
from simpeg.potential_fields import gravity, magnetics

from geology import properties, volume_grid, VOLUME_SHAPE, VOLUME_SPACING
from spatial_inverse import solve, conditional_ensemble
from evaluation import evaluate


def operators(height=60.0, inclination=60.0):
    mesh=volume_grid()
    xx,yy=np.meshgrid(np.linspace(-1050,1050,16),np.linspace(-900,900,16))
    receivers=np.c_[xx.ravel(),yy.ravel(),np.full(xx.size,height)]
    gs=gravity.Survey(gravity.sources.SourceField([gravity.receivers.Point(receivers,components="gz")]))
    gsim=gravity.simulation.Simulation3DIntegral(mesh,survey=gs,rhoMap=maps.IdentityMap(nP=mesh.nC),engine="geoana")
    ms=magnetics.Survey(magnetics.sources.UniformBackgroundField([magnetics.receivers.Point(receivers,components="tmi")],amplitude=50000,inclination=inclination,declination=12))
    msim=magnetics.simulation.Simulation3DIntegral(mesh,survey=ms,chiMap=maps.IdentityMap(nP=mesh.nC),engine="geoana")
    return mesh,receivers,np.asarray(gsim.G,dtype=float),np.asarray(msim.G,dtype=float)


def invert(G,d,sigma,beta=.018,sparse=False,shape=VOLUME_SHAPE,spacing=VOLUME_SPACING):
    m, states = solve(G, d, sigma, shape, spacing, strength=beta/.018, sparse_model=sparse)
    return dict(model=m.tolist(),predicted=(G@m).tolist(),residual=(d-G@m).tolist(),**states,
                state_identity=dict(final_frame_index=len(states['frames'])-1, selected_iteration=len(states['frames'])-1,
                                    frame_quantity='physical model', predictions='final-model'),
                metrics=dict(wrms=float(np.sqrt(np.mean(((G@m-d)/sigma)**2))),rmse=float(np.sqrt(np.mean((G@m-d)**2))),model_norm=float(np.linalg.norm(m))))


def vector_matrix(mesh,receivers,inclination=60):
    survey=magnetics.Survey(magnetics.sources.UniformBackgroundField([magnetics.receivers.Point(receivers,components="tmi")],amplitude=50000,inclination=inclination,declination=12))
    simulation=magnetics.simulation.Simulation3DIntegral(mesh,survey=survey,chiMap=maps.IdentityMap(nP=3*mesh.nC),model_type="vector",engine="geoana")
    return np.asarray(simulation.G,dtype=float)


def solve_case(case,variant,cache):
    contrast=1.5 if variant=="contrast" else 1
    height=180 if variant=="acquisition" else 60
    key=height
    if key not in cache:
        cache[key]=operators(height)
    mesh,receivers,Gg,Gm=cache[key]
    rho,chi=properties(case["geometry"],mesh.cell_centers,contrast)
    ismag=case["family"]=="magnetics"
    G=Gm if ismag else Gg
    truth=chi if ismag else rho
    unit="SI" if ismag else "g/cm³"
    data_unit="nT" if ismag else "mGal"
    clean=G@truth
    if case["geometry"]=="remanent":
        if f"vector-{height}" not in cache:
            cache[f"vector-{height}"]=vector_matrix(mesh,receivers)
        V=cache[f"vector-{height}"]
        direction=np.array([.80,-.55,.23]); direction/=np.linalg.norm(direction)
        clean=V@np.concatenate([chi*v for v in direction])
    rng=np.random.default_rng(case["seed"])
    sigma=max(float(np.std(clean))*(.14 if variant=="noise" else .025), .2 if ismag else .006)
    observed=clean+rng.normal(0,sigma,len(clean))
    mask=np.arange(len(observed))%2==0 if variant=="coverage" else np.ones(len(observed),bool)
    beta=.25 if variant=="regularization" and case['family']!='joint' else .018
    methods={}
    for name,sparse in [("l2",False),("irls",True)]:
        out=invert(G[mask],observed[mask],sigma,beta,sparse)
        m=np.asarray(out["model"])
        out["predicted"]=(G@m).tolist()
        out["residual"]=(observed-G@m).tolist()
        metrics, verdict = evaluate(m, truth, G@m, observed, sigma, mask, centers=mesh.cell_centers,
                                    negative_control=case['geometry']=='remanent')
        out['metrics'].update(metrics)
        out['evaluation'] = verdict
        out['target'] = dict(quantity='susceptibility' if ismag else 'density contrast', units=unit,
                             dimensionality=3, provenance='Original seeded synthetic geological reference')
        out["name"]="Spatial L1/L2 IRLS" if sparse else "Spatially regularized L2"
        out["name_es"]="IRLS espacial L1/L2" if sparse else "L2 con regularización espacial"
        if not sparse:
            ensemble = conditional_ensemble(G[mask], observed[mask], sigma, VOLUME_SHAPE, VOLUME_SPACING,
                                            out['solver']['beta'], case['seed']+90000)
            lo, hi = np.asarray(ensemble['lower']), np.asarray(ensemble['upper'])
            covered = (truth >= lo) & (truth <= hi)
            support = abs(truth) > .05 * max(float(np.max(abs(truth))), 1e-30)
            ensemble['coverage'] = float(covered.mean())
            ensemble['support_coverage'] = float(covered[support].mean()) if support.any() else 0.
            ensemble['coverage_scope'] = 'Pointwise coverage of this known synthetic reference; not a calibrated probability'
            out['uncertainty'] = ensemble
        methods[name]=out
    if ismag:
        vkey=f"vector-{height}"
        if vkey not in cache:
            cache[vkey]=vector_matrix(mesh,receivers)
        V=cache[vkey]
        out=invert(V[mask],observed[mask],sigma,beta)
        vector=np.asarray(out["model"]).reshape(3,-1)
        out.update(model=np.linalg.norm(vector,axis=0).tolist(),vectors=vector.T.tolist(),frames=[],predicted=(V@vector.ravel()).tolist(),residual=(observed-V@vector.ravel()).tolist(),name="Vector magnetization",name_es="Magnetización vectorial")
        from simpeg.utils.mat_utils import dip_azimuth2cartesian
        true_direction = direction if case['geometry']=='remanent' else dip_azimuth2cartesian(np.array([60.]),np.array([12.]))[0]
        vector_truth = chi[:,None]*true_direction[None,:]
        metrics, verdict = evaluate(np.linalg.norm(vector,axis=0), abs(chi), V@vector.ravel(), observed, sigma, mask, centers=mesh.cell_centers)
        support = chi > .05*max(float(np.max(chi)),1e-30)
        cosine = np.sum(vector.T*vector_truth,axis=1)/(np.linalg.norm(vector,axis=0)*np.linalg.norm(vector_truth,axis=1)+1e-30)
        metrics['direction_error_deg'] = float(np.mean(np.degrees(np.arccos(np.clip(cosine[support],-1,1))))) if support.any() else 0.
        metrics['vector_rmse'] = float(np.sqrt(np.mean((vector.T-vector_truth)**2)))
        out.update(metrics=metrics,evaluation=verdict,vector_truth=vector_truth.tolist(),
                   target=dict(quantity='effective magnetization / inducing-field amplitude',units='SI',dimensionality=3,provenance='Three-component model; scalar amplitude is not induced susceptibility under remanence'),
                   state_identity=dict(final_frame_index=None,selected_iteration=0,frame_quantity='vector amplitude',predictions='final-model'))
        methods["vector"]=out
    return dict(schema="inverse-earth/v2",**case,variant=variant,engine="SimPEG 0.25.2 3D integral / SciPy",lane="computed replay",
                grid=dict(shape=list(VOLUME_SHAPE),origin=[-1120,-960,-1120],spacing=list(VOLUME_SPACING),centers=mesh.cell_centers.tolist()),
                truth=truth.tolist(),secondary_truth=chi.tolist(),units=unit,data_units=data_unit,
                survey=dict(shape=[16,16],locations=receivers.tolist(),observed=observed.tolist(),clean=clean.tolist(),sigma=sigma,active=mask.tolist(),height=height,inclination=60,declination=12),methods=methods,
                parameters=dict(contrast=contrast,noise_sigma=sigma,height_m=height,regularization=beta,receivers=int(mask.sum())))
