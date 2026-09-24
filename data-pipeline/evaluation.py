"""Independent physical-unit recovery diagnostics; no solver tuning here."""
import numpy as np


def model_metrics(model, truth, initial=None, centers=None):
    m, t = np.asarray(model, float).ravel(), np.asarray(truth, float).ravel()
    start = np.zeros_like(t) if initial is None else np.asarray(initial, float).ravel()
    error = float(np.sqrt(np.mean((m - t) ** 2)))
    baseline = float(np.sqrt(np.mean((start - t) ** 2)))
    support = abs(t) > .05 * max(float(np.max(abs(t))), 1e-30)
    result = dict(model_rmse=error, initial_model_rmse=baseline, baseline_ratio=error / max(baseline, 1e-30),
                  correlation=float(np.corrcoef(m, t)[0, 1]) if np.std(m) > 1e-15 and np.std(t) > 1e-15 else 0.,
                  support_rmse=float(np.sqrt(np.mean((m[support] - t[support]) ** 2))) if support.any() else 0.,
                  background_rmse=float(np.sqrt(np.mean((m[~support] - t[~support]) ** 2))) if (~support).any() else 0.)
    if centers is not None:
        centers = np.asarray(centers)
        cm = np.average(centers, weights=np.maximum(abs(m), 1e-30), axis=0)
        ct = np.average(centers, weights=np.maximum(abs(t), 1e-30), axis=0)
        result['centroid_error_m'] = float(np.linalg.norm(cm - ct))
        result['recovered_centroid_depth_m'] = float(-cm[2])
        result['true_centroid_depth_m'] = float(-ct[2])
    return result


def evaluate(model, truth, predicted, observed, sigma, active, initial=None, centers=None, negative_control=False):
    metrics = model_metrics(model, truth, initial, centers)
    active = np.asarray(active, bool)
    residual = (np.asarray(predicted) - observed) / sigma
    metrics['wrms'] = float(np.sqrt(np.mean(residual[active] ** 2)))
    metrics['rmse'] = float(np.sqrt(np.mean((np.asarray(predicted)[active] - np.asarray(observed)[active]) ** 2)))
    reasons = []
    if (~active).any():
        metrics['heldout_wrms'] = float(np.sqrt(np.mean(residual[~active] ** 2)))
        if metrics['heldout_wrms'] > 2:
            reasons.append('withheld-data-not-predicted')
    if metrics['baseline_ratio'] >= 1:
        reasons.append('no-improvement-over-initial-model')
    if metrics['correlation'] < .5:
        reasons.append('low-model-correlation')
    if metrics['wrms'] > 2:
        reasons.append('active-data-misfit-above-noise')
    if negative_control:
        reasons.append('deliberately-misspecified-physical-model')
    status = 'negative-control' if negative_control else ('failed' if metrics['baseline_ratio'] >= 1 else ('unresolved' if reasons else 'recovered'))
    return metrics, dict(status=status, reason_codes=reasons)
