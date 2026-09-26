"""Recompute the matched baseline from independent serialized test evidence."""
import json
import os
from pathlib import Path
import numpy as np
import pytest
from learning import attach,generate,load_bundle
from potential import operators,invert
from geology import VOLUME_SHAPE,VOLUME_SPACING

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('INVERSE_EARTH_DATA',ROOT/'data/derived/v2'))


def test_matched_noisy_classical_test_baseline():
    meta=json.loads((DATA/'models/training.json').read_text())
    mesh,_,G,_=operators()
    observations=[generate(mesh.cell_centers,n,s)@G.T for n,s in zip(meta['split_counts'],meta['seeds'])]
    scale=float(np.std(observations[0]));rng=np.random.default_rng(5001)
    noisy=[d+rng.normal(0,.02*scale,d.shape) for d in observations]
    truth=generate(mesh.cell_centers,160,39001).reshape(-1,*VOLUME_SHAPE).sum(1)*VOLUME_SPACING[2]
    for index in [0,7,42,159]:
        model=np.asarray(invert(G,noisy[2][index],.02*scale)['model'])
        column=model.reshape(VOLUME_SHAPE).sum(0)*VOLUME_SPACING[2]
        error=float(np.mean((column-truth[index])**2))
        assert error==pytest.approx(meta['classical_test_errors'][index],rel=1e-6)
    assert meta['classical_test_mse']==pytest.approx(np.mean(meta['classical_test_errors']))
    assert 'identical' in meta['comparison']['input']


def test_detector_calibration_and_failure_denominators():
    meta=json.loads((DATA/'models/training.json').read_text());d=meta['novelty_evaluation']
    assert d['calibration_seed'] not in meta['seeds'] and d['ood_seed'] not in meta['seeds']
    threshold=np.quantile(d['calibration_errors'],.99)
    assert threshold==pytest.approx(meta['novelty_threshold'])
    positive=np.asarray(d['ood_test_errors']);negative=np.asarray(d['id_test_errors'])
    assert d['false_negative']==int(np.sum(positive<=threshold))
    assert d['false_positive']==int(np.sum(negative>threshold))
    assert d['true_positive']+d['false_negative']==80
    assert d['true_negative']+d['false_positive']==160
    assert d['sensitivity']==pytest.approx(np.mean(positive>threshold))
    assert d['roc_auc']==pytest.approx(np.mean(positive[:,None]>negative[None,:])+.5*np.mean(positive[:,None]==negative[None,:]))


def test_frozen_regularization_is_marked_not_a_neural_intervention():
    for case in ('LEARNED_CNN','LEARNED_AUTOENCODER'):
        reference=json.loads((DATA/case/'reference.json').read_text(encoding='utf-8'))
        regular=json.loads((DATA/case/'regularization.json').read_text(encoding='utf-8'))
        for key in ('cnn','autoencoder'):
            assert regular['methods'][key]['applicability']['varied_parameter'] is False
            np.testing.assert_array_equal(reference['methods'][key]['model'],regular['methods'][key]['model'])
            assert regular['methods'][key]['target'] and regular['methods'][key]['evaluation']


@pytest.mark.parametrize('case',('LEARNED_CNN','LEARNED_AUTOENCODER'))
@pytest.mark.parametrize('variant',('reference','contrast','noise','acquisition','coverage','regularization'))
def test_case_score_is_input_consistent_and_not_a_geological_verdict(case,variant):
    run=json.loads((DATA/case/f'{variant}.json').read_text(encoding='utf-8'))
    attach(run,load_bundle(DATA/'models',device='cpu'))
    method=run['methods']['autoencoder']
    net=np.asarray(method['network_input']);pred=np.asarray(method['predicted'])
    residual=np.asarray(method['residual']);errors=np.asarray(method['model'])
    scale=json.loads((DATA/'models/training.json').read_text())['input_scale']
    np.testing.assert_allclose(residual,net-pred,atol=1e-5)
    np.testing.assert_allclose(errors.ravel(),(residual/scale)**2,atol=1e-6)
    assert method['metrics']['reconstruction_mse']==pytest.approx(float(errors.mean()))
    assert method['evaluation']==dict(status='unresolved',reason_codes=['case-score-not-calibrated-as-geology'])
    if variant=='coverage':
        assert not np.array_equal(net,np.asarray(run['survey']['observed']))
        assert method['metrics']['raw_observation_mse']!=pytest.approx(method['metrics']['reconstruction_mse'])
    else:
        np.testing.assert_array_equal(net,run['survey']['observed'])


def test_frozen_bundle_rejects_tampered_checkpoint(tmp_path):
    import shutil
    for name in ('training.json','cnn.json','autoencoder.json'):
        shutil.copyfile(DATA/'models'/name,tmp_path/name)
    with (tmp_path/'cnn.json').open('ab') as file:
        file.write(b' ')
    with pytest.raises(ValueError,match='Checkpoint hash mismatch: cnn'):
        load_bundle(tmp_path,device='cpu')
