"""Independent original laboratory-like samples and a fitted two-property GMM.

These are synthetic prior observations, never labels from a display-case volume.
"""
import hashlib
import numpy as np
from scipy.special import logsumexp


def fit_prior(seed=68121, count=640):
    rng = np.random.default_rng(seed)
    labels = rng.choice(2, count, p=[.65, .35])
    means = np.array([[0., 0.], [.42, .028]])
    covariance = np.array([[[.045**2, 0.], [0., .003**2]],
                           [[.08**2, .35*.08*.006], [.35*.08*.006, .006**2]]])
    samples = np.array([rng.multivariate_normal(means[k], covariance[k]) for k in labels])
    scale = np.array([.5, .03])
    x = samples / scale
    mu = np.array([[0., 0.], [.8, .9]])
    cov = np.repeat(np.eye(2)[None]*.1, 2, axis=0)
    weights = np.ones(2)/2
    history = []
    for _ in range(80):
        delta = x[:, None] - mu
        logits = np.log(weights)[None] - .5*(2*np.log(2*np.pi) + np.linalg.slogdet(cov)[1][None]
                  + np.einsum('nki,kij,nkj->nk', delta, np.linalg.inv(cov), delta))
        normalizer = logsumexp(logits, axis=1)
        responsibilities = np.exp(logits - normalizer[:, None])
        mass = responsibilities.sum(0)
        weights = mass/len(x)
        mu = responsibilities.T@x/mass[:, None]
        delta = x[:, None]-mu
        cov = np.einsum('nk,nki,nkj->kij', responsibilities, delta, delta)/mass[:, None, None]+1e-6*np.eye(2)
        history.append(float(-normalizer.mean()))
    order = np.argsort(mu[:, 0])
    return dict(kind='independently-fitted-Gaussian-mixture', seed=seed, count=count,
                source='Original synthetic petrophysical samples; not measured cores or voxel labels',
                units=['g/cm³', 'SI'], samples=samples.tolist(),
                sample_sha256=hashlib.sha256(samples.astype('<f8').tobytes()).hexdigest(),
                weights=weights[order].tolist(), means=(mu[order]*scale).tolist(),
                covariances=(cov[order]*scale[None, :, None]*scale[None, None, :]).tolist(),
                em_negative_log_likelihood=history)
