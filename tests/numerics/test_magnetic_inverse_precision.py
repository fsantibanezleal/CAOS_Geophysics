"""Independent Decimal160 full native-operand objective, not quadratic relabelling."""

from decimal import Decimal, localcontext, getcontext
from time import monotonic

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from magnetic_inverse import MagneticQuantity
from magnetic_inverse_precision import MagneticCertificate


def operands(quantity='exact_total_anomaly_nT', covariance=False):
    g = np.array([[13., -7.], [3., 8.], [-9., 2.],
                  [4., 11.], [-3., 5.], [7., -6.]])
    b0 = np.array([-38186.94682695953, 11674.921276231968, -30090.75115760241])
    op = MagneticQuantity(g, b0, b0/50000., 50000., quantity)
    c = 3 if quantity == 'secondary_enu_nT' else 1
    d = np.full((2, c), .02)
    noise = {'kind': 'diagonal_sd', 'values': np.full((2, c), .5)}
    if covariance:
        n = d.size
        noise = {'kind': 'full_covariance', 'values': .25*.2**np.abs(np.arange(n)[:, None]-np.arange(n))}
    terms = ({'alpha': 1., 'weights': np.array([.4, .7]),
              'derivative': csr_matrix(np.array([[1., 0.], [-.3, .5]]))},)
    cert = MagneticCertificate(op, d, noise, np.array([.1, .2]), np.zeros(2),
                               np.full(2, 10.), .3, terms)
    return op, cert, d, noise, terms


def objective(op, q, d, noise, terms):
    """Direct norm, no candidate rational expression or interval arithmetic."""
    with localcontext() as ctx:
        ctx.prec = 160
        dec = lambda x: Decimal.from_float(float(x))
        ab, b0, direction, f, quantity = op.operand_snapshot()
        b = [[sum(dec(a)*dec(x) for a, x in zip(row, q)) for row in ab[3*i:3*i+3]]
             for i in range(2)]
        if quantity == 'exact_total_anomaly_nT':
            h = [sum((dec(a)+v)**2 for a, v in zip(b0, row)).sqrt()-dec(f) for row in b]
        elif quantity == 'linear_tmi_nT':
            h = [sum(dec(a)*v for a, v in zip(direction, row)) for row in b]
        else:
            h = [v for row in b for v in row]
        r = [v-dec(x) for v, x in zip(h, d.ravel())]
        if noise['kind'] == 'diagonal_sd':
            wr = [v/dec(s) for v, s in zip(r, noise['values'].ravel())]
        else:
            # Bind the actual retained native Cholesky, as required, but solve
            # independently using Decimal160 rather than production triangular code.
            lower = np.linalg.cholesky(noise['values'])
            wr = []
            for i, v in enumerate(r):
                wr.append((v-sum(dec(lower[i,j])*wr[j] for j in range(i)))/dec(lower[i,i]))
        phi = sum(v*v for v in wr)
        delta = [dec(x)-dec(y) for x,y in zip(q, [.1,.2])]
        for term in terms:
            deriv = term['derivative'].toarray()
            phi += dec(.3)*dec(term['alpha'])*sum(
                (dec(w)*sum(dec(a)*v for a,v in zip(row,delta)))**2
                for w,row in zip(term['weights'],deriv))
        return +phi


@pytest.mark.parametrize('quantity', ['secondary_enu_nT','linear_tmi_nT','exact_total_anomaly_nT'])
@pytest.mark.parametrize('covariance', [False, True])
def test_full_objective_encloses_independent_actual_chord(quantity, covariance):
    op, cert, d, noise, terms = operands(quantity, covariance)
    q, qt = np.array([1., .8]), np.array([.3, .25])
    g = np.array([1., 1.])
    record = cert.certify(q,qt,g,1.,.2,0,0,monotonic()+120.)
    delta = objective(op,qt,d,noise,terms)-objective(op,q,d,noise,terms)
    with localcontext() as ctx:
        ctx.prec = 160
        slope = sum(Decimal.from_float(float(a))*(Decimal.from_float(float(y))-Decimal.from_float(float(x)))
                    for a,x,y in zip(g,q,qt))
        margin = delta-Decimal.from_float(1e-4)*slope
    for key, value in [('delta_interval',delta),('slope_interval',slope),('armijo_margin_interval',margin)]:
        lo,hi = map(Decimal, record[key])
        assert lo <= value <= hi
    assert record['decision'] == 'certified_accept'
    assert record['arithmetic_domain'] == ('fixed_native_operand_magnetic_norm' if
        quantity == 'exact_total_anomaly_nT' else 'fixed_native_operand_quadratic')


def test_reject_zero_chord_non_descent_deadline_and_caller_context():
    _, cert, _, _, _ = operands()
    q, qt = np.array([1.,1.]), np.array([.5,.5])
    before = getcontext().copy()
    record = cert.certify(q,qt,np.array([-1.,-1.]),1.,.2,0,0,monotonic()+120.)
    assert record['decision'] == 'certified_reject' and record['cause'] == 'non_descent'
    assert cert.certify(q,q,np.ones(2),1.,1.,0,0,monotonic()+120.)['cause'] == 'zero_displacement'
    late = cert.certify(q,qt,np.ones(2),1.,.2,0,0,monotonic()-1.)
    assert late['cause'] == 'wall_cap' and late['passes'] == 0
    assert late['precision_digits'] is None and late['delta_interval'] is None
    assert getcontext().prec == before.prec and getcontext().rounding == before.rounding
    assert getcontext().flags == before.flags


def test_total_norm_domain_crossing_has_no_partial_certificate():
    op = MagneticQuantity(np.array([[0.],[0.],[-5000000.]]),np.array([0.,0.,50000.]),
                          np.array([0.,0.,1.]),50000.,'exact_total_anomaly_nT')
    cert = MagneticCertificate(op,np.zeros((1,1)),{'kind':'diagonal_sd','values':np.ones((1,1))},
                               np.zeros(1),np.zeros(1),np.full(1,10.),1.,())
    record = cert.certify(np.zeros(1),np.ones(1),-np.ones(1),1.,0.,0,0,monotonic()+120.)
    assert record['decision'] == 'not_run' and record['cause'] == 'range_unsupported'
    assert record['passes'] == 0 and record['slope_interval'] is None


@pytest.mark.parametrize('fault', ['extra','sd','asymmetric','indefinite','csr','alpha','bounds'])
def test_closed_certificate_construction(fault):
    op, _, d, noise, terms = operands()
    reference, lower, upper = np.zeros(2), np.zeros(2), np.full(2,10.)
    if fault == 'extra': noise['extra'] = 1
    if fault == 'sd': noise['values'][0,0] = 0.
    if fault == 'asymmetric': noise = {'kind':'full_covariance','values':np.array([[1.,.1],[0.,1.]])}
    if fault == 'indefinite': noise = {'kind':'full_covariance','values':np.array([[1.,2.],[2.,1.]])}
    if fault == 'csr': terms[0]['derivative'] = terms[0]['derivative'].toarray()
    if fault == 'alpha': terms[0]['alpha'] = True
    if fault == 'bounds': upper[0] = 0.
    with pytest.raises((TypeError,ValueError)):
        MagneticCertificate(op,d,noise,reference,lower,upper,.3,terms)
