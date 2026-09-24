"""Gravity/magnetic joint objective with a differentiable structural constraint."""
import numpy as np
import torch
from potential import invert
from geology import VOLUME_SHAPE


def cross_gradient(a,b,shape=VOLUME_SHAPE):
    ga=torch.gradient(a.reshape(shape))
    gb=torch.gradient(b.reshape(shape))
    return torch.stack((ga[1]*gb[2]-ga[2]*gb[1],ga[2]*gb[0]-ga[0]*gb[2],ga[0]*gb[1]-ga[1]*gb[0]))


def attach(run,cache):
    _,_,Gg,Gm=cache[run["parameters"]["height_m"]]
    device="cuda" if torch.cuda.is_available() else "cpu"
    chi=np.asarray(run["secondary_truth"])
    clean=Gm@chi
    rng=np.random.default_rng(run["seed"]+1)
    sigma=max(np.std(clean)*(.14 if run["variant"]=="noise" else .025),.2)
    dm=clean+rng.normal(0,sigma,len(clean))
    dg=np.asarray(run["survey"]["observed"])
    sg=run["survey"]["sigma"]
    mask=np.asarray(run["survey"]["active"],dtype=bool)
    initial_m=invert(Gm[mask],dm[mask],sigma)["model"]
    ag=torch.tensor(Gg[mask]*.5,dtype=torch.float32,device=device)
    am=torch.tensor(Gm[mask]*.03,dtype=torch.float32,device=device)
    tg=torch.tensor(dg[mask],dtype=torch.float32,device=device)
    tm=torch.tensor(dm[mask],dtype=torch.float32,device=device)
    a=torch.nn.Parameter(torch.tensor(np.asarray(run["methods"]["l2"]["model"])/.5,dtype=torch.float32,device=device))
    b=torch.nn.Parameter(torch.tensor(np.asarray(initial_m)/.03,dtype=torch.float32,device=device))
    optimizer=torch.optim.Adam([a,b],lr=.008)
    history=[]; frames=[]
    coupling=25.0 if run["variant"]=="regularization" else 4.0
    for step in range(180):
        optimizer.zero_grad()
        data=((ag@a-tg)/sg).square().mean()+((am@b-tm)/sigma).square().mean()
        cross=cross_gradient(a,b).square().mean()
        loss=data+coupling*cross+.015*(a.square().mean()+b.square().mean())
        loss.backward(); optimizer.step()
        if step%6==0:
            history.append(float(loss.detach()))
            frames.append((a.detach()*.5).cpu().tolist())
    density=(a.detach()*.5).cpu().numpy()
    susceptibility=(b.detach()*.03).cpu().numpy()
    cross=cross_gradient(a.detach(),b.detach()).square().sum(0).sqrt().cpu().numpy()
    run["magnetic_survey"]=dict(observed=dm.tolist(),clean=clean.tolist(),sigma=float(sigma))
    run["methods"]["joint"]=dict(name="Cross-gradient joint inversion",name_es="Inversión conjunta por gradiente cruzado",model=density.tolist(),secondary_model=susceptibility.tolist(),cross_gradient=cross.ravel().tolist(),predicted=(Gg@density).tolist(),residual=(dg-Gg@density).tolist(),magnetic_predicted=(Gm@susceptibility).tolist(),history=history,frames=frames,
        metrics=dict(wrms=float(np.sqrt(np.mean(((Gg@density-dg)/sg)**2))),magnetic_wrms=float(np.sqrt(np.mean(((Gm@susceptibility-dm)/sigma)**2))),cross_gradient=float(cross.mean()),model_rmse=float(np.sqrt(np.mean((density-np.asarray(run["truth"]))**2)))) ,device=device)
    return run
