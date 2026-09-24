"""Reproduce prior selection and test conditional intervals on independent models."""
import argparse
from pathlib import Path
import numpy as np
import spatial_inverse as inverse
from potential import operators
from learning import generate
from geology import VOLUME_SHAPE, VOLUME_SPACING
from rebuild import save


def main(output):
    mesh,_,G,_=operators()
    models=generate(mesh.cell_centers,12,67081)
    data=models@G.T
    sigma=.025*np.std(data)
    observed=data+np.random.default_rng(67082).normal(0,sigma,data.shape)
    selection=[]
    for power in (0.,.375,.75):
        inverse.DEPTH_POWER=power;inverse.geometry.cache_clear();inverse._systems.clear()
        ratios=[]
        for truth,d in zip(models,observed):
            m,_=inverse.solve(G,d,sigma,VOLUME_SHAPE,VOLUME_SPACING)
            ratios.append(float(np.linalg.norm(m-truth)/np.linalg.norm(truth)))
        selection.append(dict(depth_power=power,baseline_ratios=ratios,mean_ratio=float(np.mean(ratios))))
        print('PRIOR',power,selection[-1]['mean_ratio'],flush=True)
    selected=min(selection,key=lambda row:row['mean_ratio'])['depth_power']
    if selected!=.375:raise ValueError('Calibration changed; review evidence before changing the frozen prior')
    inverse.DEPTH_POWER=selected;inverse.geometry.cache_clear();inverse._systems.clear()
    test=generate(mesh.cell_centers,16,67091)
    dtest=test@G.T
    noise=np.random.default_rng(67092).normal(0,sigma,dtest.shape)
    rows=[]
    for i,(truth,d) in enumerate(zip(test,dtest+noise)):
        m,states=inverse.solve(G,d,sigma,VOLUME_SHAPE,VOLUME_SPACING)
        ensemble=inverse.conditional_ensemble(G,d,sigma,VOLUME_SHAPE,VOLUME_SPACING,states['solver']['beta'],67100+i)
        cover=(truth>=ensemble['lower'])&(truth<=ensemble['upper'])
        support=abs(truth)>.05*max(float(np.max(abs(truth))),1e-30)
        rows.append(dict(realization=i,baseline_ratio=float(np.linalg.norm(m-truth)/np.linalg.norm(truth)),
                         coverage=float(cover.mean()),support_coverage=float(cover[support].mean()) if support.any() else 0.,
                         background_coverage=float(cover[~support].mean()) if (~support).any() else 0.))
    report=dict(schema='inverse-earth.prior-calibration/v1',calibration_seed=67081,calibration_noise_seed=67082,
                selection_rule='minimum mean zero-model RMSE ratio on calibration-only geometries',candidates=selection,selected_depth_power=selected,
                test_seed=67091,test_noise_seed=67092,test_count=16,bootstrap_members=32,test_realizations=rows,
                mean_test_baseline_ratio=float(np.mean([r['baseline_ratio'] for r in rows])),
                mean_pointwise_coverage=float(np.mean([r['coverage'] for r in rows])),
                mean_support_coverage=float(np.mean([r['support_coverage'] for r in rows])),
                claim='Conditional estimator repeatability only; coverage explicitly tests omitted regularization bias, not a posterior calibration claim')
    save(output,report)
    print('TEST',report['mean_test_baseline_ratio'],'COVERAGE',report['mean_pointwise_coverage'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output)
