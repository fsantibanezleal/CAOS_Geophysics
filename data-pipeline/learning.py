"""GPU-trained observation-to-column-density CNN and observation autoencoder.

The inverse target is depth-integrated density, not an identifiable 3D reconstruction.
Geometry realizations are grouped by seed; no realization crosses splits.
"""
from pathlib import Path
import json
import hashlib
import numpy as np
import torch
from torch import nn
from scipy.interpolate import griddata
from geology import VOLUME_SHAPE, VOLUME_SPACING
from potential import invert
from evaluation import model_metrics


class InverseCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Conv2d(1,16,3,padding=1),nn.GELU(),nn.Conv2d(16,24,3,padding=1),nn.GELU(),nn.AdaptiveAvgPool2d((4,4)),nn.Flatten(),nn.Linear(384,96),nn.GELU(),nn.Linear(96,VOLUME_SHAPE[1]*VOLUME_SHAPE[2]))
    def forward(self,x):
        return self.net(x).reshape(-1,*VOLUME_SHAPE[1:])


class ObservationAE(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Flatten(),nn.Linear(256,64),nn.GELU(),nn.Linear(64,12),nn.GELU(),nn.Linear(12,64),nn.GELU(),nn.Linear(64,256))
    def forward(self,x):
        return self.net(x).reshape(-1,1,16,16)


def generate(centers,count,seed):
    rng=np.random.default_rng(seed)
    x,y,u=centers.T; z=-u
    models=[]
    for i in range(count):
        cx,cy=rng.uniform(-650,650),rng.uniform(-450,450)
        cz=rng.uniform(280,850)
        a,b,c=rng.uniform(210,520,3)
        contrast=rng.uniform(.2,.65)*(-1 if i%5==0 else 1)
        family=i%4
        if family==0:
            mask=((x-cx)/a)**2+((y-cy)/b)**2+((z-cz)/c)**2<1
        elif family==1:
            mask=(abs(x-cx-.25*z)<a*.4)&(abs(y-cy)<b)&(z>180)&(z<cz+200)
        elif family==2:
            depth=cz*np.clip(1-((x-cx)/(a*2))**2,0,1)*np.clip(1-((y-cy)/(b*2))**2,0,1)
            mask=(z<depth)&(z>100)
        else:
            top=cz+.22*x+np.where(y>cy,150,0)
            mask=(z>top)&(z<top+220)
        models.append(mask.astype(float)*contrast)
    return np.asarray(models)


def generate_ood(centers,count=80,seed=59001):
    """Held-out geometric families; never used to fit weights or thresholds."""
    rng=np.random.default_rng(seed)
    x,y,u=centers.T;z=-u;models=[]
    for i in range(count):
        cx,cy=rng.uniform(-250,250,2);depth=rng.uniform(250,650)
        radius=rng.uniform(280,550);width=rng.uniform(70,180)
        angle=rng.uniform(-np.pi,np.pi)
        xx=(x-cx)*np.cos(angle)+(y-cy)*np.sin(angle)
        yy=-(x-cx)*np.sin(angle)+(y-cy)*np.cos(angle)
        if i%2==0:
            distance=np.sqrt((xx/1.25)**2+yy**2)
            mask=(distance>radius)&(distance<radius+width)&(z>depth-150)&(z<depth+250)
        else:
            mask=((abs(xx)<width)&(abs(yy)<650)&(z>depth-150)&(z<depth+250))|((abs(yy)<width)&(abs(xx)<650)&(z>depth)&(z<depth+350))
        models.append(mask.astype(float)*rng.uniform(.25,.65))
    return np.asarray(models)


def checkpoint(model,path):
    state={name:dict(shape=list(value.shape),values=value.detach().cpu().numpy().ravel().tolist()) for name,value in model.state_dict().items()}
    path.write_text(json.dumps(state,separators=(",",":")))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_checkpoint(model,path):
    state=json.loads(Path(path).read_text())
    model.load_state_dict({k:torch.tensor(v["values"],dtype=torch.float32).reshape(v["shape"]) for k,v in state.items()})
    model.eval()
    return model


def train(mesh,G,outdir,epochs=180):
    device="cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(7721)
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    counts=[800,160,160];seeds=[18001,29001,39001]
    models=[generate(mesh.cell_centers,n,s) for n,s in zip(counts,seeds)]
    # Physical forward modelling precedes data-only normalization.
    observations=[m@G.T for m in models]
    scale=float(np.std(observations[0]))
    target_scale=400.0
    targets=[m.reshape(-1,*VOLUME_SHAPE).sum(1)*VOLUME_SPACING[2]/target_scale for m in models]
    rng=np.random.default_rng(5001)
    noisy=[d+rng.normal(0,.02*scale,d.shape) for d in observations]
    xx=[torch.tensor(d/scale,dtype=torch.float32,device=device).reshape(-1,1,16,16) for d in noisy]
    yy=[torch.tensor(v,dtype=torch.float32,device=device) for v in targets]
    cnn=InverseCNN().to(device); ae=ObservationAE().to(device)
    records={}
    for name,model in [("cnn",cnn),("autoencoder",ae)]:
        optimizer=torch.optim.Adam(model.parameters(),lr=.001)
        best=float("inf");best_state=None;history=[]
        for epoch in range(epochs):
            model.train()
            for indices in torch.randperm(counts[0],device=device).split(64):
                optimizer.zero_grad()
                target=yy[0][indices] if name=="cnn" else xx[0][indices]
                loss=(model(xx[0][indices])-target).square().mean()
                loss.backward();optimizer.step()
            model.eval()
            with torch.no_grad():
                validation=float((model(xx[1])-(yy[1] if name=="cnn" else xx[1])).square().mean())
            if validation<best:
                best=validation;best_state={k:v.detach().clone() for k,v in model.state_dict().items()}
            if epoch%5==0:
                history.append(dict(epoch=epoch,train=float(loss.detach()),validation=validation))
            if epoch%20==0:print(f'TRAIN {name} epoch {epoch}/{epochs}: validation={validation:.6g}',flush=True)
        model.load_state_dict(best_state)
        with torch.no_grad():
            pred=model(xx[2]);target=yy[2] if name=="cnn" else xx[2]
            errors=(pred-target).square().reshape(counts[2],-1).mean(1).cpu().numpy()
        sha=checkpoint(model,outdir/f"{name}.json")
        records[name]=dict(checkpoint=f"models/{name}.json",sha256=sha,validation_mse=best,test_mse=float(errors.mean()),test_errors=errors.tolist(),history=history)
    # The classical baseline solves the same observation-to-column target on the test cases.
    classical=np.array([invert(G,data,.02*scale)['model'] for data in noisy[2]])
    classic_projection=classical.reshape(-1,*VOLUME_SHAPE).sum(1)*VOLUME_SPACING[2]
    truth_projection=targets[2]*target_scale
    # Threshold calibration is disjoint from early-stopping validation and test.
    calibration=generate(mesh.cell_centers,160,49001)@G.T
    calibration+=np.random.default_rng(49002).normal(0,.02*scale,calibration.shape)
    ood=generate_ood(mesh.cell_centers)@G.T
    ood+=np.random.default_rng(59002).normal(0,.02*scale,ood.shape)
    with torch.no_grad():
        cal_x=torch.tensor(calibration/scale,dtype=torch.float32,device=device).reshape(-1,1,16,16)
        ood_x=torch.tensor(ood/scale,dtype=torch.float32,device=device).reshape(-1,1,16,16)
        calibration_error=(ae(cal_x)-cal_x).square().flatten(1).mean(1).cpu().numpy()
        ood_error=(ae(ood_x)-ood_x).square().flatten(1).mean(1).cpu().numpy()
    threshold=float(np.quantile(calibration_error,.99))
    id_error=np.asarray(records['autoencoder']['test_errors'])
    detection=dict(calibration_seed=49001,calibration_count=160,ood_seed=59001,ood_count=80,
                   threshold_policy='99th percentile of separate in-distribution calibration reconstruction errors',
                   calibration_errors=calibration_error.tolist(),id_test_errors=id_error.tolist(),ood_test_errors=ood_error.tolist(),
                   true_positive=int(np.sum(ood_error>threshold)),false_negative=int(np.sum(ood_error<=threshold)),
                   false_positive=int(np.sum(id_error>threshold)),true_negative=int(np.sum(id_error<=threshold)),
                   sensitivity=float(np.mean(ood_error>threshold)),specificity=float(np.mean(id_error<=threshold)),
                   roc_auc=float(np.mean(ood_error[:,None]>id_error[None,:])+.5*np.mean(ood_error[:,None]==id_error[None,:])),
                   limitation='Reconstruction error is not a universal out-of-distribution detector; missed withheld geometries are retained')
    metadata=dict(schema="inverse-earth.learning/v2",device=device,gpu=torch.cuda.get_device_name(0) if device=="cuda" else None,
        seeds=seeds,split_counts=counts,split_policy="Disjoint generator seeds; complete realization assigned to one split; oblique and ring geometries withheld from training",input_scale=scale,target_scale=target_scale,novelty_threshold=threshold,
        models=records,classical_test_mse=float(np.mean((classic_projection-truth_projection)**2)),cnn_test_mse=records["cnn"]["test_mse"]*target_scale**2,units="(g/cm³ m)²",
        classical_test_errors=np.mean((classic_projection-truth_projection)**2,axis=(1,2)).tolist(),
        comparison=dict(input='Exactly identical seeded noisy observations for classical and CNN inverses',noise_sigma=.02*scale,
                        noisy_test_sha256=hashlib.sha256(noisy[2].astype('<f8').tobytes()).hexdigest(),target='Depth-integrated density on the identical 24 by 28 grid',classical='Noise-aware spatial L2 with discrepancy-selected beta'),
        novelty_evaluation=detection)
    (outdir/"training.json").write_text(json.dumps(metadata,separators=(",",":")))
    return cnn,ae,metadata


def attach(run,bundle):
    cnn,ae,meta=bundle
    device=next(cnn.parameters()).device
    observed_input=np.asarray(run["survey"]["observed"])
    mask=np.asarray(run["survey"]["active"],dtype=bool)
    if not mask.all():
        xy=np.asarray(run["survey"]["locations"])[:,:2]
        interpolated=griddata(xy[mask],observed_input[mask],xy,method="linear")
        nearest=griddata(xy[mask],observed_input[mask],xy,method="nearest")
        observed_input=np.where(np.isfinite(interpolated),interpolated,nearest)
    run["learning_preprocess"]="Training-scale normalization; linear interpolation of omitted stations with nearest edge fill; fixed-height trained network"
    x=torch.tensor(observed_input/meta["input_scale"],dtype=torch.float32,device=device).reshape(1,1,16,16)
    truth=np.asarray(run["truth"]).reshape(VOLUME_SHAPE).sum(0)*VOLUME_SPACING[2]
    with torch.no_grad():
        column=cnn(x)[0].cpu().numpy()*meta["target_scale"]
        reconstruction=ae(x)[0,0].cpu().numpy()*meta["input_scale"]
    observed=np.asarray(run["survey"]["observed"]).reshape(16,16)
    error=(reconstruction-observed)**2/meta["input_scale"]**2
    run["column_truth"]=truth.tolist()
    run["methods"]["cnn"]=dict(name="CNN column-density inversion",name_es="Inversión CNN de densidad integrada",model=column.tolist(),predicted=[],residual=(column-truth).tolist(),history=[v["validation"] for v in meta["models"]["cnn"]["history"]],frames=[],metrics=dict(column_rmse=float(np.sqrt(np.mean((column-truth)**2)))),checkpoint=meta["models"]["cnn"]["sha256"],units="g/cm³ m")
    run["methods"]["autoencoder"]=dict(name="Observation autoencoder",name_es="Autoencoder de observaciones",model=error.tolist(),predicted=reconstruction.ravel().tolist(),residual=(observed-reconstruction).ravel().tolist(),history=[v["validation"] for v in meta["models"]["autoencoder"]["history"]],frames=[],metrics=dict(reconstruction_mse=float(error.mean()),threshold=meta["novelty_threshold"],above_threshold=bool(error.mean()>meta["novelty_threshold"])),checkpoint=meta["models"]["autoencoder"]["sha256"],units="normalized squared error")
    for method_id in ('l2','irls'):
        projection=np.asarray(run['methods'][method_id]['model']).reshape(VOLUME_SHAPE).sum(0)*VOLUME_SPACING[2]
        run['methods'][method_id]['column_model']=projection.tolist()
        run['methods'][method_id]['metrics']['column_rmse']=float(np.sqrt(np.mean((projection-truth)**2)))
    cnn_method=run['methods']['cnn'];ae_method=run['methods']['autoencoder']
    cnn_method['metrics'].update(model_metrics(column,truth))
    cnn_method['metrics']['classical_column_rmse']=run['methods']['l2']['metrics']['column_rmse']
    cnn_method['metrics']['classical_baseline_ratio']=cnn_method['metrics']['column_rmse']/max(cnn_method['metrics']['classical_column_rmse'],1e-30)
    cnn_method['evaluation']=dict(status='unresolved' if cnn_method['metrics']['classical_baseline_ratio']>=1 else 'recovered',
                                  reason_codes=['held-out-geological-family','column-target-not-three-dimensional-recovery']+(['does-not-improve-classical-baseline'] if cnn_method['metrics']['classical_baseline_ratio']>=1 else []))
    if cnn_method['metrics']['baseline_ratio']>=1:cnn_method['evaluation']['status']='failed'
    cnn_method['target']=dict(quantity='depth-integrated density contrast',units='g/cm³ m',dimensionality=2,provenance='Depth integral of original synthetic volume; not a reconstructed depth profile')
    ae_method['evaluation']=dict(status='recovered' if ae_method['metrics']['above_threshold'] else 'failed',
                                 reason_codes=['withheld-geometric-family-detected' if ae_method['metrics']['above_threshold'] else 'withheld-geometric-family-missed'])
    ae_method['target']=dict(quantity='normalized observation reconstruction error',units='normalized squared error',dimensionality=2,provenance='Known withheld geometry; no subsurface recovery claim')
    ae_method['detection_validation']=meta['novelty_evaluation']
    for method in (cnn_method,ae_method):
        method['applicability']=dict(varied_parameter=run['variant']!='regularization',reason='Frozen checkpoint; regularization changes classical comparator only' if run['variant']=='regularization' else 'Fixed checkpoint evaluated on modified observations')
        method['state_identity']=dict(final_frame_index=None,selected_iteration=None,frame_quantity='checkpoint inference',predictions='final-model')
    return run
