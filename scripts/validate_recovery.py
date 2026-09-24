"""Local numerical release gates; never train or execute this in hosted CI."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'data-pipeline'))
from evaluation import model_metrics


def validate(data,report):
    catalog=json.loads((data/'catalog.json').read_text(encoding='utf-8'))
    rows=[];failures=[];nominal={};cache={}
    for case in catalog['cases']:
        for entry in case['variants']:
            path=data/entry['path'];raw=path.read_bytes()
            assert hashlib.sha256(raw).hexdigest()==entry['sha256']
            run=json.loads(raw)
            for key,method in run['methods'].items():
                label=f"{case['id']}/{entry['id']}/{key}"
                try:
                    model=np.asarray(method['model'])
                    assert np.isfinite(model).all(), 'nonfinite-model'
                    verdict=method['evaluation']
                    assert verdict['status'] in ('recovered','unresolved','failed','negative-control')
                    assert isinstance(verdict['reason_codes'],list)
                    if method.get('frames'):
                        np.testing.assert_allclose(method['frames'][-1],model,rtol=2e-6,atol=1e-8,err_msg='last-frame-not-final-model')
                    if case['family'] in ('gravity','magnetics','joint','learned') and key not in ('cnn','autoencoder'):
                        from potential import operators, vector_matrix
                        height=run['parameters']['height_m']
                        if height not in cache:cache[height]=operators(height)
                        mesh,rx,Gg,Gm=cache[height]
                        if key=='vector':
                            vkey=f'vector-{height}'
                            if vkey not in cache:cache[vkey]=vector_matrix(mesh,rx)
                            prediction=cache[vkey]@np.asarray(method['vectors']).T.ravel()
                        else:prediction=(Gm if case['family']=='magnetics' else Gg)@model
                        np.testing.assert_allclose(prediction,method['predicted'],rtol=2e-5,atol=1e-5)
                        observed=np.asarray(run['survey']['observed']);sigma=run['survey']['sigma']
                        active=np.asarray(run['survey']['active'],bool)
                        # Seven-significant-digit JSON introduces cancellation
                        # error proportional to the data amplitude, not residual.
                        rounding=2e-6*max(float(np.max(abs(observed))),float(np.max(abs(prediction))),1e-8)
                        np.testing.assert_allclose(observed-prediction,method['residual'],rtol=2e-4,atol=rounding)
                        if (~active).any():
                            expected=np.sqrt(np.mean(((prediction-observed)[~active]/sigma)**2))
                            np.testing.assert_allclose(expected,method['metrics']['heldout_wrms'],rtol=2e-4,atol=2e-5)
                        if 'magnetic_model' in method:
                            np.testing.assert_allclose(Gm@method['magnetic_model'],method['magnetic_predicted'],rtol=2e-5,atol=1e-5)
                    if case['family']=='mt':
                        from electromagnetics import impedance
                        prediction=impedance(model,run['thickness'],np.asarray(run['frequencies']))
                        np.testing.assert_allclose(prediction.real,method['predicted']['real'],rtol=3e-5,atol=1e-10)
                        np.testing.assert_allclose(prediction.imag,method['predicted']['imag'],rtol=3e-5,atol=1e-10)
                    if case['family']=='seismic':
                        truth=np.asarray(run['truth']);initial=np.asarray(run['initial'])
                        ratio=model_metrics(model,truth,initial)['baseline_ratio']
                        if entry['id']=='reference' and case['geometry'] in ('layers','normal_fault','channel'):
                            nominal.setdefault(case['id'],[]).append(ratio)
                    if key=='pgi':
                        np.testing.assert_allclose(np.sum(method['prior_membership'],axis=1),1.,atol=2e-6)
                        assert method['petrophysical_prior']['sample_sha256']
                    if method.get('uncertainty'):
                        u=method['uncertainty'];assert u['members']>=16
                        assert np.asarray(u['lower']).shape==model.shape
                        assert np.all(np.asarray(u['lower'])<=u['upper'])
                        assert 'posterior' in u['conditioning'].lower()
                    rows.append(dict(case=case['id'],variant=entry['id'],method=key,status=verdict['status'],reason_codes=verdict['reason_codes'],metrics=method['metrics']))
                except (AssertionError,KeyError,ValueError) as exc:
                    failures.append(dict(result=label,error=str(exc)))
            print('CHECK',case['id'],entry['id'],flush=True)
    for case,ratios in nominal.items():
        if min(ratios)>=1:failures.append(dict(result=case,error='No nominal reference inverse improves the independent starting-model RMSE'))
    if len(catalog['cases'])==20 and len(nominal)!=3:
        failures.append(dict(result='FWI',error='Three nominal reference recovery cases required'))
    receipt=dict(schema='inverse-earth.recovery-validation/v1',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 catalog_sha256=hashlib.sha256((data/'catalog.json').read_bytes()).hexdigest(),results=len(rows),failures=failures,
                 nominal_fwi_ratios=nominal,status='PASS' if not failures else 'FAIL',verdicts=rows,
                 claim='Contract and declared numerical gates only; retained unresolved and negative-control results are not recovery successes')
    report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(receipt['status'],len(rows),'results;',len(failures),'failed gates',flush=True)
    return not failures


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,default=ROOT/'data/derived/v2')
    parser.add_argument('--report',type=Path,default=ROOT/'docs/validation/recovery.json')
    args=parser.parse_args();raise SystemExit(0 if validate(args.data,args.report) else 1)
