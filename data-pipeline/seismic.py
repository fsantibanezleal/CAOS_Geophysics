"""Actual Deepwave forward/adjoint FWI on distinct geological sections."""
from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F
import deepwave

from geology import seismic_model, SEISMIC_SPACING


def simulate(v,frequency=8.0,receivers=40,nt=2200,callback=None):
    device=v.device
    source_locations=torch.tensor([[[24,6]],[[64,6]],[[102,6]]],device=device)
    rx=torch.linspace(6,120,receivers,device=device).long()
    receiver_locations=torch.stack((rx,torch.full_like(rx,6)),dim=-1)[None].repeat(3,1,1)
    t=torch.arange(nt,device=device,dtype=v.dtype)*.0005
    a=np.pi*frequency*(t-1.5/frequency)
    wavelet=(1-2*a*a)*torch.exp(-a*a)
    sources=wavelet[None,None].repeat(3,1,1)
    return deepwave.scalar(v,SEISMIC_SPACING,.0005,source_amplitudes=sources,source_locations=source_locations,
        receiver_locations=receiver_locations,pml_width=24,pml_freq=frequency,accuracy=4,
        max_vel=4600,forward_callback=callback,callback_frequency=48)[-1]


def lowpass(x,width):
    if width<=1:
        return x
    flat=x.reshape(-1,1,x.shape[-1])
    return F.avg_pool1d(F.pad(flat,(width//2,width//2),mode="replicate"),width,stride=1).reshape(x.shape)


def solve_case(case,variant,iterations=28):
    torch.manual_seed(case["seed"])
    device="cuda" if torch.cuda.is_available() else "cpu"
    truth=seismic_model(case["geometry"],1.15 if variant=="contrast" else 1)
    vtrue=torch.tensor(truth,device=device)
    freq=5.0 if variant=="acquisition" else (9.0 if case["geometry"]=="salt" else 8.0)
    receivers=20 if variant=="coverage" else 40
    # Initial model depends only on a declared depth trend, never smoothed truth.
    start=np.broadcast_to(1800+np.arange(truth.shape[1])*11.0,truth.shape).copy().astype(np.float32)
    snapshots=[]
    def callback(state):
        field=state.get_wavefield("wavefield_0")[1]
        snapshots.append(field.detach().cpu().numpy().T.tolist())
    with torch.no_grad():
        clean=simulate(vtrue,freq,receivers,callback=callback)
        noise=.08 if variant=="noise" else .01
        sigma=float(clean.std())*noise
        observed=clean+torch.randn_like(clean)*sigma
    scale=float(observed.square().mean())
    beta=.06 if variant=="regularization" else .002
    methods={}
    for multiscale in (False,True):
        param=torch.nn.Parameter(torch.logit(torch.tensor((start-1400)/3000,device=device)))
        optimizer=torch.optim.Adam([param],lr=.045)
        history=[]; frames=[]; best=float("inf"); best_model=start.copy()
        with torch.no_grad():
            initial_pred=simulate(torch.tensor(start,device=device),freq,receivers)
            initial_loss=float((initial_pred-observed).square().mean()/scale)
        for it in range(iterations):
            optimizer.zero_grad()
            v=1400+3000*torch.sigmoid(param)
            pred=simulate(v,freq,receivers)
            window=(41 if it<iterations//3 else 17 if it<2*iterations//3 else 1) if multiscale else 1
            data_loss=(lowpass(pred,window)-lowpass(observed,window)).square().mean()/scale
            reg=4*((v[:,1:]-v[:,:-1]).square().mean()+(v[1:]-v[:-1]).square().mean())/1e6
            loss=data_loss+beta*reg
            loss.backward()
            torch.nn.utils.clip_grad_norm_([param],10)
            optimizer.step()
            with torch.no_grad():
                raw=float((pred-observed).square().mean()/scale)
                history.append(raw)
                if raw<best:
                    best=raw; best_model=v.detach().cpu().numpy().copy()
                if it%2==0:
                    frames.append(v.detach().cpu().numpy().T.tolist())
        with torch.no_grad():
            final=simulate(torch.tensor(best_model,device=device),freq,receivers)
        key="fwi-multiscale" if multiscale else "fwi-l2"
        methods[key]=dict(name="Multiscale acoustic FWI" if multiscale else "Acoustic waveform L2 FWI",name_es="FWI acústica multiescala" if multiscale else "FWI acústica L2",
            model=best_model.T.tolist(),predicted=final.detach().cpu().numpy()[:,:,::8].tolist(),residual=(observed-final).detach().cpu().numpy()[:,:,::8].tolist(),history=history,frames=frames,
            metrics=dict(initial_relative_mse=initial_loss,relative_mse=float((final-observed).square().mean()/scale),velocity_rmse=float(np.sqrt(np.mean((best_model-truth)**2)))),device=device)
    return dict(schema="inverse-earth/v2",**case,variant=variant,engine="Deepwave 0.0.27 / PyTorch automatic differentiation",lane="computed replay",units="m/s",data_units="amplitude",
        truth=truth.T.tolist(),initial=start.T.tolist(),observed=observed.detach().cpu().numpy()[:,:,::8].tolist(),wavefields=snapshots,
        grid=dict(shape=[96,128],spacing=[12.5,12.5]),dt=.004,wavefield_dt=.024,frequency=freq,
        sources=[[300,75],[800,75],[1275,75]],receivers=(torch.linspace(6,120,receivers).long()*12.5).tolist(),methods=methods,
        parameters=dict(frequency_hz=freq,noise_fraction=noise,receivers=receivers,regularization=beta,iterations=iterations))
