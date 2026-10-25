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
import geology
from geology import VOLUME_SHAPE, VOLUME_SPACING
from potential import invert
from evaluation import model_metrics


_LEGACY_SURVEY_SHAPE = (16, 16)
_CHECKPOINT_SCHEMA = "inverse-earth.learned-potential-checkpoint/v1"


def survey_shape():
    """Return the canonical (northing, easting) observation-grid dimensions.

    The fallback preserves the original committed 16x16 release. Once geology
    defines SURVEY_SHAPE, all newly trained models and artifacts bind to it.
    """
    shape = tuple(getattr(geology, "SURVEY_SHAPE", _LEGACY_SURVEY_SHAPE))
    if len(shape) != 2 or any(not isinstance(size, (int, np.integer)) or size < 1 for size in shape):
        raise ValueError(f"geology.SURVEY_SHAPE must contain two positive integers; got {shape!r}")
    return tuple(int(size) for size in shape)


def _observation_tensor(values, shape, scale, device):
    values = np.asarray(values)
    expected = int(np.prod(shape))
    if values.ndim != 2 or values.shape[1] != expected:
        raise ValueError(
            f"Expected observations shaped (samples, {expected}) for survey grid {tuple(shape)}, "
            f"got {values.shape}"
        )
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError(f"Observation normalization scale must be finite and positive; got {scale!r}")
    return torch.as_tensor(values / scale, dtype=torch.float32, device=device).reshape(-1, 1, *shape)


class InverseCNN(nn.Module):
    architecture = "observation-cnn-to-column-density/v1"

    def __init__(self, input_shape=None):
        super().__init__()
        self.input_shape = tuple(input_shape or survey_shape())
        self.net=nn.Sequential(nn.Conv2d(1,16,3,padding=1),nn.GELU(),nn.Conv2d(16,24,3,padding=1),nn.GELU(),nn.AdaptiveAvgPool2d((4,4)),nn.Flatten(),nn.Linear(384,96),nn.GELU(),nn.Linear(96,VOLUME_SHAPE[1]*VOLUME_SHAPE[2]))
    def forward(self,x):
        if x.ndim != 4 or tuple(x.shape[1:2]) != (1,) or tuple(x.shape[-2:]) != self.input_shape:
            raise ValueError(f"CNN expects (batch, 1, {self.input_shape[0]}, {self.input_shape[1]}), got {tuple(x.shape)}")
        return self.net(x).reshape(-1,*VOLUME_SHAPE[1:])


class ObservationAE(nn.Module):
    architecture = "observation-autoencoder/v1"

    def __init__(self, input_shape=None):
        super().__init__()
        self.input_shape = tuple(input_shape or survey_shape())
        n_observations = int(np.prod(self.input_shape))
        self.net=nn.Sequential(nn.Flatten(),nn.Linear(n_observations,64),nn.GELU(),nn.Linear(64,12),nn.GELU(),nn.Linear(12,64),nn.GELU(),nn.Linear(64,n_observations))
    def forward(self,x):
        if x.ndim != 4 or tuple(x.shape[1:2]) != (1,) or tuple(x.shape[-2:]) != self.input_shape:
            raise ValueError(f"Autoencoder expects (batch, 1, {self.input_shape[0]}, {self.input_shape[1]}), got {tuple(x.shape)}")
        return self.net(x).reshape(-1,1,*self.input_shape)


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
    payload=dict(schema=_CHECKPOINT_SCHEMA,architecture=model.architecture,
                 survey_shape=list(model.input_shape),state=state)
    path.write_text(json.dumps(payload,separators=(",",":")))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_checkpoint(model,path):
    payload=json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") == _CHECKPOINT_SCHEMA:
        stored_shape=tuple(payload.get("survey_shape",()))
        if stored_shape != model.input_shape:
            raise ValueError(f"Checkpoint survey shape {stored_shape} does not match model survey shape {model.input_shape}")
        if payload.get("architecture") != model.architecture:
            raise ValueError(f"Checkpoint architecture {payload.get('architecture')!r} does not match {model.architecture!r}")
        state=payload.get("state")
    else:
        # The unversioned checkpoints in v2 predate shape metadata. They are
        # safe to interpret only at the original fixed 16x16 input geometry.
        if model.input_shape != _LEGACY_SURVEY_SHAPE:
            raise ValueError("Unversioned legacy checkpoint is fixed to 16x16; retrain for the current survey shape")
        state=payload
    if not isinstance(state, dict):
        raise ValueError("Checkpoint state dictionary is missing or invalid")
    tensors={}
    for name,value in state.items():
        if not isinstance(value,dict) or "shape" not in value or "values" not in value:
            raise ValueError(f"Invalid checkpoint tensor entry: {name}")
        tensors[name]=torch.as_tensor(value["values"],dtype=torch.float32).reshape(value["shape"])
    model.load_state_dict(tensors)
    model.eval()
    return model


def load_bundle(source,device=None,grid_shape=None):
    """Reuse immutable, hash-checked training evidence for case-only rebuilds."""
    source=Path(source)
    meta=json.loads((source/'training.json').read_text(encoding='utf-8'))
    current_shape=tuple(grid_shape or survey_shape())
    schema=meta.get('schema')
    if schema=='inverse-earth.learning/v2':
        if current_shape != _LEGACY_SURVEY_SHAPE:
            raise ValueError(f"Legacy learning bundle is fixed to 16x16; current geology.SURVEY_SHAPE is {current_shape}. Retrain the learned models.")
    elif schema=='inverse-earth.learning/v3':
        if tuple(meta.get('survey_shape',())) != current_shape:
            raise ValueError(f"Training ledger survey shape {tuple(meta.get('survey_shape',()))} does not match geology.SURVEY_SHAPE {current_shape}")
    else:
        raise ValueError('Unsupported training ledger schema')
    models=[]
    for name,kind in [('cnn',InverseCNN),('autoencoder',ObservationAE)]:
        entry=meta['models'][name]
        path=source/Path(entry['checkpoint']).name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError(f'Checkpoint hash mismatch: {name}')
        models.append(load_checkpoint(kind(input_shape=current_shape),path).to(device or ('cuda' if torch.cuda.is_available() else 'cpu')))
    return *models,meta


def train(mesh,G,outdir,epochs=180):
    device="cuda" if torch.cuda.is_available() else "cpu"
    input_shape=survey_shape()
    observation_count=int(np.prod(input_shape))
    if np.asarray(G).ndim != 2 or np.asarray(G).shape[0] != observation_count:
        raise ValueError(f"Forward operator must contain {observation_count} survey rows for {input_shape}; got {np.asarray(G).shape}")
    torch.manual_seed(7721)
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    counts=[800,160,160];seeds=[18001,29001,39001]
    models=[generate(mesh.cell_centers,n,s) for n,s in zip(counts,seeds)]
    # Physical forward modelling precedes data-only normalization.
    observations=[m@G.T for m in models]
    if any(data.shape != (count, observation_count) for data,count in zip(observations,counts)):
        raise ValueError(f"Forward observations do not match the survey geometry {input_shape}")
    scale=float(np.std(observations[0]))
    target_scale=400.0
    targets=[m.reshape(-1,*VOLUME_SHAPE).sum(1)*VOLUME_SPACING[2]/target_scale for m in models]
    rng=np.random.default_rng(5001)
    noisy=[d+rng.normal(0,.02*scale,d.shape) for d in observations]
    xx=[_observation_tensor(d,input_shape,scale,device) for d in noisy]
    yy=[torch.tensor(v,dtype=torch.float32,device=device) for v in targets]
    cnn=InverseCNN(input_shape=input_shape).to(device); ae=ObservationAE(input_shape=input_shape).to(device)
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
        cal_x=_observation_tensor(calibration,input_shape,scale,device)
        ood_x=_observation_tensor(ood,input_shape,scale,device)
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
    metadata=dict(schema="inverse-earth.learning/v3",survey_shape=list(input_shape),device=device,gpu=torch.cuda.get_device_name(0) if device=="cuda" else None,
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
    input_shape=tuple(run.get("survey",{}).get("shape",()))
    if input_shape != tuple(meta.get('survey_shape',_LEGACY_SURVEY_SHAPE)):
        raise ValueError(f"Training bundle survey shape {tuple(meta.get('survey_shape',_LEGACY_SURVEY_SHAPE))} does not match run survey shape {input_shape}")
    observed_input=np.asarray(run["survey"]["observed"])
    mask=np.asarray(run["survey"]["active"],dtype=bool)
    if observed_input.ndim != 1 or observed_input.size != int(np.prod(input_shape)) or mask.shape != observed_input.shape:
        raise ValueError(f"Survey observations and active mask must each contain {int(np.prod(input_shape))} values for {input_shape}")
    if not mask.all():
        xy=np.asarray(run["survey"]["locations"])[:,:2]
        if xy.shape != (observed_input.size,2):
            raise ValueError(f"Survey locations must have shape ({observed_input.size}, 2); got {xy.shape}")
        if not mask.any():
            raise ValueError("Cannot interpolate a survey with no active observations")
        interpolated=griddata(xy[mask],observed_input[mask],xy,method="linear")
        nearest=griddata(xy[mask],observed_input[mask],xy,method="nearest")
        observed_input=np.where(np.isfinite(interpolated),interpolated,nearest)
    run["learning_preprocess"]="Training-scale normalization; linear interpolation of omitted stations with nearest edge fill; fixed-height trained network"
    x=_observation_tensor(observed_input.reshape(1,-1),input_shape,meta["input_scale"],device)
    truth=np.asarray(run["truth"]).reshape(VOLUME_SHAPE).sum(0)*VOLUME_SPACING[2]
    with torch.no_grad():
        column=cnn(x)[0].cpu().numpy()*meta["target_scale"]
        reconstruction=ae(x)[0,0].cpu().numpy()*meta["input_scale"]
    observed=np.asarray(run["survey"]["observed"]).reshape(input_shape)
    network_input=observed_input.reshape(input_shape)
    # The detector was calibrated against the tensor supplied to the network.
    # In a coverage experiment this is an interpolated map, not the full survey.
    error=(reconstruction-network_input)**2/meta["input_scale"]**2
    run["column_truth"]=truth.tolist()
    run["methods"]["cnn"]=dict(name="CNN column-density inversion",name_es="Inversión CNN de densidad integrada",model=column.tolist(),predicted=[],residual=(column-truth).tolist(),history=[v["validation"] for v in meta["models"]["cnn"]["history"]],frames=[],metrics=dict(column_rmse=float(np.sqrt(np.mean((column-truth)**2)))),checkpoint=meta["models"]["cnn"]["sha256"],units="g/cm³ m")
    run["methods"]["autoencoder"]=dict(name="Observation autoencoder",name_es="Autoencoder de observaciones",model=error.tolist(),predicted=reconstruction.ravel().tolist(),residual=(network_input-reconstruction).ravel().tolist(),network_input=network_input.ravel().tolist(),history=[v["validation"] for v in meta["models"]["autoencoder"]["history"]],frames=[],metrics=dict(reconstruction_mse=float(error.mean()),threshold=meta["novelty_threshold"],above_threshold=bool(error.mean()>meta["novelty_threshold"]),raw_observation_mse=float(np.mean((reconstruction-observed)**2)/meta["input_scale"]**2)),checkpoint=meta["models"]["autoencoder"]["sha256"],units="normalized squared error")
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
    # The single-case threshold flag is a score comparison, not a validated
    # geological-family classification: the display cases have different
    # amplitude/noise/acquisition laws from the separate detector test cohort.
    ae_method['evaluation']=dict(status='unresolved',reason_codes=['case-score-not-calibrated-as-geology'])
    ae_method['target']=dict(quantity='normalized network-input reconstruction error',units='normalized squared error',dimensionality=2,provenance='Autoencoder input after any coverage interpolation; no subsurface recovery claim')
    ae_method['detection_validation']=meta['novelty_evaluation']
    for method in (cnn_method,ae_method):
        method['applicability']=dict(varied_parameter=run['variant']!='regularization',reason='Frozen checkpoint; regularization changes classical comparator only' if run['variant']=='regularization' else 'Fixed checkpoint evaluated on modified observations')
        method['state_identity']=dict(final_frame_index=None,selected_iteration=None,frame_quantity='checkpoint inference',predictions='final-model')
    return run
