"""Matched uncoupled, cross-gradient and explicit Gaussian-mixture inversions."""
import numpy as np
import torch
from potential import invert
from geology import VOLUME_SHAPE, VOLUME_SPACING
from spatial_inverse import geometry, precision
from evaluation import evaluate, model_metrics
from petrophysics import fit_prior


def cross_gradient(a,b,shape=VOLUME_SHAPE,spacing=VOLUME_SPACING):
    ga=torch.gradient(a.reshape(shape),spacing=tuple(spacing[::-1]))
    gb=torch.gradient(b.reshape(shape),spacing=tuple(spacing[::-1]))
    return torch.stack((ga[1]*gb[2]-ga[2]*gb[1],ga[2]*gb[0]-ga[0]*gb[2],ga[0]*gb[1]-ga[1]*gb[0]))


def mixture_nll(a,b,prior):
    x=torch.stack([a*.5,b*.03],dim=-1)
    means=torch.as_tensor(prior['means'],dtype=x.dtype,device=x.device)
    cov=torch.as_tensor(prior['covariances'],dtype=x.dtype,device=x.device)
    weights=torch.as_tensor(prior['weights'],dtype=x.dtype,device=x.device)
    delta=x[:,None,:]-means
    energy=.5*(2*np.log(2*np.pi)+torch.linalg.slogdet(cov)[1]+torch.einsum('nki,kij,nkj->nk',delta,torch.linalg.inv(cov),delta))
    logits=torch.log(weights)-energy
    return -torch.logsumexp(logits,dim=1).mean(),torch.softmax(logits,dim=1)


def spatial_energy(model,weight):
    x=model.reshape(VOLUME_SHAPE)
    value=(weight*x.square()).sum()
    for axis,(spacing,length) in enumerate(zip(VOLUME_SPACING[::-1],(140.,240.,240.))):
        left=[slice(None)]*3;right=left.copy()
        left[axis]=slice(None,-1);right[axis]=slice(1,None)
        left,right=tuple(left),tuple(right)
        value=value+(length/spacing)**2*((x[right]-x[left]).square()*(weight[left]+weight[right])*.5).sum()
    return value


def attach(run,cache,iterations=80):
    mesh,_,Gg,Gm=cache[run['parameters']['height_m']]
    torch.set_num_threads(2)
    chi=np.asarray(run['secondary_truth']);rho=np.asarray(run['truth'])
    clean=Gm@chi
    sigma=max(float(np.std(clean))*(.14 if run['variant']=='noise' else .025),.2)
    dm=clean+np.random.default_rng(run['seed']+1).normal(0,sigma,len(clean))
    dg=np.asarray(run['survey']['observed']);sg=run['survey']['sigma']
    mask=np.asarray(run['survey']['active'],bool)
    magnetic=invert(Gm[mask],dm[mask],sigma)
    initial_a=np.asarray(run['methods']['l2']['model'])/.5
    initial_b=np.asarray(magnetic['model'])/.03
    ag=torch.tensor(Gg[mask]*.5/sg,dtype=torch.float64)
    am=torch.tensor(Gm[mask]*.03/sigma,dtype=torch.float64)
    tg=torch.tensor(dg[mask]/sg,dtype=torch.float64)
    tm=torch.tensor(dm[mask]/sigma,dtype=torch.float64)
    weights=torch.tensor(geometry(tuple(VOLUME_SHAPE),tuple(VOLUME_SPACING))[0]**2,dtype=torch.float64).reshape(VOLUME_SHAPE)
    bg=run['methods']['l2']['solver']['beta']/mask.sum()
    bm=magnetic['solver']['beta']/mask.sum()
    qdiag=torch.tensor(precision(VOLUME_SHAPE,VOLUME_SPACING).diagonal(),dtype=torch.float64)
    pa=(ag.square().mean(0)+bg*.5**2*qdiag).rsqrt()
    pb=(am.square().mean(0)+bm*.03**2*qdiag).rsqrt()
    prior=fit_prior()
    initial_cross=float(cross_gradient(torch.tensor(initial_a),torch.tensor(initial_b)).square().mean()*240.**4)
    cross_scale=max(initial_cross,1e-12)
    run['petrophysical_prior']=prior
    run['magnetic_survey']=dict(observed=dm.tolist(),clean=clean.tolist(),sigma=sigma)
    strength=4. if run['variant']=='regularization' else 1.
    for key,coupling,petro,name,name_es in [
        ('joint-uncoupled',0.,0.,'Matched uncoupled inversion','Inversión desacoplada comparable'),
        ('joint',strength,0.,'Physical cross-gradient inversion','Inversión por gradiente cruzado físico'),
        ('pgi',0.,strength,'Gaussian-mixture petrophysical inversion','Inversión petrofísica de mezcla gaussiana')]:
        qa=torch.nn.Parameter(torch.tensor(initial_a,dtype=torch.float64)/pa)
        qb=torch.nn.Parameter(torch.tensor(initial_b,dtype=torch.float64)/pb)
        optimizer=torch.optim.LBFGS([qa,qb],lr=1.,max_iter=1,history_size=15,line_search_fn='strong_wolfe',tolerance_grad=1e-10,tolerance_change=1e-12)
        def components():
            a,b=qa*pa,qb*pb
            data=(ag@a-tg).square().mean()+(am@b-tm).square().mean()
            regular=bg*spatial_energy(a*.5,weights)+bm*spatial_energy(b*.03,weights)
            cross=cross_gradient(a,b).square().mean()*240.**4/cross_scale
            nll,_=mixture_nll(a,b,prior)
            return data+regular+coupling*cross+petro*nll,data,regular,cross,nll
        def closure():
            optimizer.zero_grad();loss=components()[0];loss.backward();return loss
        history=[];frames=[];terms=[]
        for step in range(iterations):
            optimizer.step(closure)
            if step%8==0 or step==iterations-1:
                with torch.no_grad():values=[float(v) for v in components()]
                if not np.isfinite(values).all():raise ValueError('Non-finite joint objective')
                history.append(values[0]);terms.append(values[1:]);frames.append((qa.detach()*pa*.5).numpy().tolist())
        a,b=qa.detach()*pa,qb.detach()*pb
        density=(a*.5).numpy();susceptibility=(b*.03).numpy()
        cross=cross_gradient(a*.5,b*.03).square().sum(0).sqrt().numpy()
        metrics,verdict=evaluate(density,rho,Gg@density,dg,sg,mask,centers=mesh.cell_centers,
                                 negative_control=key=='pgi' and run['geometry']=='conflict')
        initial_error=model_metrics(initial_a*.5,rho)['model_rmse']
        metrics.update(magnetic_wrms=float(np.sqrt(np.mean(((Gm@susceptibility-dm)[mask]/sigma)**2))),
                       magnetic_model_rmse=model_metrics(susceptibility,chi)['model_rmse'],
                       independent_model_rmse=initial_error,independent_baseline_ratio=metrics['model_rmse']/max(initial_error,1e-30),
                       cross_gradient=float(cross.mean()))
        if (~mask).any():metrics['magnetic_heldout_wrms']=float(np.sqrt(np.mean(((Gm@susceptibility-dm)[~mask]/sigma)**2)))
        if key!='joint-uncoupled' and metrics['independent_baseline_ratio']>=1 and verdict['status']!='negative-control':
            verdict['status']='unresolved';verdict['reason_codes'].append('coupling-does-not-improve-independent-density-recovery')
        method=dict(name=name,name_es=name_es,model=density.tolist(),secondary_model=susceptibility.tolist(),magnetic_model=susceptibility.tolist(),
                    predicted=(Gg@density).tolist(),residual=(dg-Gg@density).tolist(),magnetic_predicted=(Gm@susceptibility).tolist(),
                    cross_gradient=cross.ravel().tolist(),history=history,frames=frames,objective_terms=terms,metrics=metrics,evaluation=verdict,device='cpu',
                    solver=dict(optimizer='Diagonal-Hessian preconditioned L-BFGS strong Wolfe',iterations=iterations,cross_gradient_weight=coupling,mixture_weight=petro,
                                gravity_beta=bg*mask.sum(),magnetic_beta=bm*mask.sum(),cross_gradient_spacing_m=list(VOLUME_SPACING),cross_gradient_initial_scale=cross_scale,
                                objective_terms=['whitened data means','physical spatial priors','cross gradient normalized by matched independent initial value','mean negative log mixture density']),
                    target=dict(quantity='density contrast with jointly estimated susceptibility',units='g/cm³',dimensionality=3,provenance='Independent original synthetic geological reference'),
                    state_identity=dict(final_frame_index=len(frames)-1,selected_iteration=iterations,frame_quantity='density contrast',predictions='final-model'))
        if key=='pgi':
            method['prior_membership']=mixture_nll(a.detach(),b.detach(),prior)[1].numpy().tolist()
            method['petrophysical_prior']=prior
        run['methods'][key]=method
    return run
