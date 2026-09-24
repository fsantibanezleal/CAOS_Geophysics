"""SimPEG 3D integral operators and explicit weighted inverse objectives."""
from __future__ import annotations

import numpy as np
from scipy.linalg import solve
from simpeg import maps
from simpeg.potential_fields import gravity, magnetics

from geology import properties, volume_grid


def operators(height=60.0, inclination=60.0):
    mesh=volume_grid()
    xx,yy=np.meshgrid(np.linspace(-1050,1050,16),np.linspace(-900,900,16))
    receivers=np.c_[xx.ravel(),yy.ravel(),np.full(xx.size,height)]
    gs=gravity.Survey(gravity.sources.SourceField([gravity.receivers.Point(receivers,components="gz")]))
    gsim=gravity.simulation.Simulation3DIntegral(mesh,survey=gs,rhoMap=maps.IdentityMap(nP=mesh.nC),engine="geoana")
    ms=magnetics.Survey(magnetics.sources.UniformBackgroundField([magnetics.receivers.Point(receivers,components="tmi")],amplitude=50000,inclination=inclination,declination=12))
    msim=magnetics.simulation.Simulation3DIntegral(mesh,survey=ms,chiMap=maps.IdentityMap(nP=mesh.nC),engine="geoana")
    return mesh,receivers,np.asarray(gsim.G,dtype=float),np.asarray(msim.G,dtype=float)


def invert(G,d,sigma,beta=.04,sparse=False):
    # Sensitivity scaling gives a reproducible depth-aware parameterization m=Wq.
    sensitivity=np.sqrt(np.sum(G**2,axis=0))
    W=1/np.maximum(sensitivity, np.max(sensitivity)*.06)
    A=G*W
    scale=np.linalg.norm(A,ord="fro")/np.sqrt(len(d))
    A=A/scale
    b=d/scale
    weight=np.ones(G.shape[1])
    history=[]
    frames=[]
    for _ in range(8 if sparse else 1):
        covariance=1/weight
        gram=(A*covariance)@A.T+beta*np.eye(len(d))
        q=covariance*(A.T@solve(gram,b,assume_a="pos"))
        m=W*q
        residual=G@m-d
        history.append(float(np.mean((residual/sigma)**2)))
        frames.append(m.tolist())
        if sparse:
            epsilon=max(np.max(np.abs(q))*.12,1e-10)
            weight=1/np.sqrt(q*q+epsilon**2)
            weight/=np.median(weight)
    return dict(model=m.tolist(),predicted=(G@m).tolist(),residual=(d-G@m).tolist(),history=history,frames=frames,
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
    beta=.25 if variant=="regularization" else .018
    methods={}
    for name,sparse in [("l2",False),("irls",True)]:
        out=invert(G[mask],observed[mask],sigma,beta,sparse)
        m=np.asarray(out["model"])
        out["predicted"]=(G@m).tolist()
        out["residual"]=(observed-G@m).tolist()
        out["metrics"]["model_rmse"]=float(np.sqrt(np.mean((m-truth)**2)))
        out["name"]="Sparse IRLS" if sparse else "Sensitivity-weighted L2"
        out["name_es"]="IRLS dispersa" if sparse else "L2 ponderada por sensibilidad"
        methods[name]=out
    if ismag:
        vkey=f"vector-{height}"
        if vkey not in cache:
            cache[vkey]=vector_matrix(mesh,receivers)
        V=cache[vkey]
        out=invert(V[mask],observed[mask],sigma,beta)
        vector=np.asarray(out["model"]).reshape(3,-1)
        out.update(model=np.linalg.norm(vector,axis=0).tolist(),vectors=vector.T.tolist(),frames=[],predicted=(V@vector.ravel()).tolist(),residual=(observed-V@vector.ravel()).tolist(),name="Vector magnetization",name_es="Magnetización vectorial")
        methods["vector"]=out
    return dict(schema="inverse-earth/v2",**case,variant=variant,engine="SimPEG 0.25.2 3D integral / SciPy",lane="computed replay",
                grid=dict(shape=[8,12,14],origin=[-1120,-960,-1120],spacing=[160,160,140],centers=mesh.cell_centers.tolist()),
                truth=truth.tolist(),secondary_truth=chi.tolist(),units=unit,data_units=data_unit,
                survey=dict(shape=[16,16],locations=receivers.tolist(),observed=observed.tolist(),clean=clean.tolist(),sigma=sigma,active=mask.tolist(),height=height,inclination=60,declination=12),methods=methods,
                parameters=dict(contrast=contrast,noise_sigma=sigma,height_m=height,regularization=beta,receivers=int(mask.sum())))
