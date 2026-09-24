"""Layered-earth impedance, bounded least squares, autodiff and neural inversion."""
from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares
import torch

from geology import mt_model

MU=4e-7*np.pi


def impedance(rho,thickness,frequencies):
    omega=2*np.pi*np.asarray(frequencies)
    Z=np.sqrt(1j*omega*MU*rho[-1])
    for j in range(len(rho)-2,-1,-1):
        k=np.sqrt(1j*omega*MU/rho[j])
        w=np.sqrt(1j*omega*MU*rho[j])
        t=np.tanh(k*thickness[j])
        Z=w*(Z+w*t)/(w+Z*t)
    return Z


def torch_impedance(logrho,thickness,frequencies):
    rho=logrho.exp()
    omega=2*np.pi*frequencies
    Z=torch.sqrt(1j*omega*MU*rho[-1])
    for j in range(len(rho)-2,-1,-1):
        k=torch.sqrt(1j*omega*MU/rho[j])
        w=torch.sqrt(1j*omega*MU*rho[j])
        t=torch.tanh(k*thickness[j])
        Z=w*(Z+w*t)/(w+Z*t)
    return Z


def curves(z,f):
    return dict(real=z.real.tolist(),imag=z.imag.tolist(),apparent=(abs(z)**2/(MU*2*np.pi*f)).tolist(),phase=np.angle(z,deg=True).tolist())


def solve_case(case,variant):
    torch.manual_seed(case["seed"])
    rho,h=mt_model(case["geometry"],1.5 if variant=="contrast" else 1)
    f=np.geomspace(.001 if variant=="acquisition" else .01,100,36)
    active=np.arange(len(f))%2==0 if variant=="coverage" else np.ones(len(f),bool)
    z=impedance(rho,h,f)
    relative=.10 if variant=="noise" else .025
    sigma=relative*abs(z)
    rng=np.random.default_rng(case["seed"])
    observed=z+sigma*(rng.normal(size=len(f))+1j*rng.normal(size=len(f)))
    initial=np.full(len(rho),100.0)
    beta=.3 if variant=="regularization" else .001
    methods={}
    ls_frames=[]
    ls_history=[]
    def residual(logrho):
        r=(impedance(np.exp(logrho),h,f)[active]-observed[active])/sigma[active]
        result=np.r_[r.real,r.imag,np.sqrt(beta)*np.diff(logrho)]
        if not ls_frames or np.linalg.norm(np.log(np.asarray(ls_frames[-1]))-logrho)>1e-4:
            ls_frames.append(np.exp(logrho).tolist())
            ls_history.append(float(np.mean(result**2)))
        return result
    fit=least_squares(residual,np.log(initial),bounds=(np.log(1),np.log(6000)),max_nfev=160)
    def pack(name,name_es,model,history,frames):
        pred=impedance(model,h,f)
        return dict(name=name,name_es=name_es,model=model.tolist(),predicted=curves(pred,f),residual=curves(observed-pred,f),history=history,frames=frames,
                    metrics=dict(wrms=float(np.sqrt(np.mean(abs((pred-observed)/sigma)**2))),log_model_rmse=float(np.sqrt(np.mean((np.log(model/rho))**2)))))
    methods["mt-lm"]=pack("Bounded complex least squares","Mínimos cuadrados complejos acotados",np.exp(fit.x),ls_history,ls_frames)
    device="cuda" if torch.cuda.is_available() else "cpu"
    tf=torch.tensor(f,dtype=torch.float64,device=device)
    th=torch.tensor(h,dtype=torch.float64,device=device)
    obs=torch.tensor(observed,device=device)
    sig=torch.tensor(sigma,device=device)
    mask=torch.tensor(active,device=device)
    for neural in (False,True):
        if neural:
            net=torch.nn.Sequential(torch.nn.Linear(1,24),torch.nn.Tanh(),torch.nn.Linear(24,24),torch.nn.Tanh(),torch.nn.Linear(24,1)).double().to(device)
            nodes=torch.linspace(0,1,len(rho),dtype=torch.float64,device=device)[:,None]
            parameters=net.parameters()
        else:
            param=torch.nn.Parameter(torch.log(torch.tensor(initial,dtype=torch.float64,device=device)))
            parameters=[param]
        optim=torch.optim.Adam(parameters,lr=.025 if neural else .06)
        history=[]; frames=[]
        best=float("inf"); best_model=initial.copy()
        for step in range(420 if neural else 250):
            optim.zero_grad()
            log=1+7*torch.sigmoid(net(nodes).squeeze(-1)) if neural else param
            pred=torch_impedance(log,th,tf)
            loss=torch.mean(abs((pred[mask]-obs[mask])/sig[mask])**2)+beta*torch.mean(torch.diff(log)**2)
            loss.backward(); optim.step()
            val=float(loss.detach())
            if val<best:
                best=val; best_model=log.detach().exp().cpu().numpy().copy()
            if step%10==0:
                history.append(val); frames.append(log.detach().exp().cpu().tolist())
        key="mt-neural" if neural else "mt-adam"
        methods[key]=pack("Physics-guided neural inversion" if neural else "Differentiable impedance inversion","Inversión neuronal guiada por física" if neural else "Inversión diferenciable de impedancia",best_model,history,frames)
        methods[key]["device"]=device
    return dict(schema="inverse-earth/v2",**case,variant=variant,engine="Complex layered-earth recursion / SciPy / PyTorch",lane="computed replay",units="ohm m",data_units="ohm",
                truth=rho.tolist(),thickness=h.tolist(),frequencies=f.tolist(),observed=curves(observed,f),clean=curves(z,f),sigma=sigma.tolist(),active=active.tolist(),methods=methods,
                parameters=dict(noise_fraction=relative,regularization=beta,frequencies=int(active.sum()),minimum_frequency_hz=float(f.min())))
