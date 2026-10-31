"""RESEARCH ONLY: exact tiny quadratic certificates; never imported by product.

Uses frozen unsealed six-cell development control. No solver/threshold mutation,
output-file writes, accepted-state insertion, holdout access, or production fallback.
Prints actual measurements for a separately reviewed documentation amendment.
"""
import hashlib
import json
import math
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING
from fractions import Fraction as F
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'data-pipeline'))
t = runpy.run_path(str(ROOT / 'tests/numerics/test_gravity_l2.py'))
np, l2 = t['np'], t['l2']


def ff(x):
    return F.from_float(float(x))


def fm(a):
    return [[ff(x) for x in row] for row in a]


def mv(a, x):
    return [sum((v*y for v, y in zip(row, x)), F(0)) for row in a]


def mm(a, b):
    return [[sum((v*b[k][j] for k, v in enumerate(row)), F(0))
             for j in range(len(b[0]))] for row in a]


def norm(x):
    return max(map(abs, x))


def exact_system(blocks):
    n = len(blocks[0][1][0])
    h = [[F(0) for _ in range(n)] for _ in range(n)]
    c = [F(0) for _ in range(n)]
    for weight, a, b in blocks:
        for row, target in zip(a, b):
            for i in range(n):
                c[i] += 2*weight*row[i]*target
                for j in range(n):
                    h[i][j] += 2*weight*row[i]*row[j]
    return h, c


def solve(a, b):
    """Exact rational Gaussian elimination, positive pivots certify SPD here."""
    n = len(b)
    v = [row[:] + [target] for row, target in zip(a, b)]
    pivots = []
    for k in range(n):
        pivot = v[k][k]
        assert pivot > 0  # symmetric SPD Schur complements, no pivot heuristic
        pivots.append(pivot)
        for i in range(k+1, n):
            ratio = v[i][k]/pivot
            for j in range(k, n+1):
                v[i][j] -= ratio*v[k][j]
    x = [F(0)]*n
    for k in reversed(range(n)):
        x[k] = (v[k][-1]-sum((v[k][j]*x[j] for j in range(k+1, n)), F(0)))/v[k][k]
    assert mv(a, x) == b
    return x, pivots


def evaluate(blocks, x):
    phi = F(0)
    g = [F(0)]*len(x)
    for weight, a, b in blocks:
        r = [v-y for v, y in zip(mv(a, x), b)]
        phi += weight*sum((v*v for v in r), F(0))
        for j in range(len(x)):
            g[j] += 2*weight*sum((row[j]*v for row, v in zip(a, r)), F(0))
    return phi, g


def native(q, problem):
    pd = problem['misfit'](q)
    pm = problem['regularization'](q)
    g = problem['misfit'].deriv(q)+problem['beta_engine']*problem['regularization'].deriv(q)
    return float(pd+problem['beta_engine']*pm), float(np.linalg.norm(g, ord=np.inf))


def fsum_evaluate(blocks, q):
    """Flattened correctly rounded coefficients; products still rounded first."""
    phis, gs = [], [[] for _ in q]
    for weight, a, b in blocks:
        a = [[float(x) for x in row] for row in a]
        r = [math.fsum([*(v*float(x) for v, x in zip(row, q)), -float(y)])
             for row, y in zip(a, b)]
        phis.append(float(weight)*math.fsum(x*x for x in r))
        for j in range(len(q)):
            gs[j].extend(2*float(weight)*row[j]*v for row, v in zip(a, r))
    return math.fsum(phis), max(abs(math.fsum(v)) for v in gs)


def delta(blocks, x, y):
    """Exact residual identity, not subtraction of rounded absolute objectives."""
    change = [b-a for a, b in zip(x, y)]
    terms = []
    for weight, a, b in blocks:
        residual = [v-z for v, z in zip(mv(a, x), b)]
        dy = mv(a, change)
        terms.append(weight*sum((2*r*v+v*v for r, v in zip(residual, dy)), F(0)))
    answer = sum(terms, F(0))
    assert answer == evaluate(blocks, y)[0]-evaluate(blocks, x)[0]
    return answer


def directed_margin(blocks, x, y, digits, recorded_gradient=None):
    """Interval certificate for actual chord; precision ladder, no tolerance.

    Includes coefficient conversion, all residual products/sums, and slope.
    Verifies each returned enclosure against the rational reference afterwards.
    """
    def rounded(fn, direction):
        with localcontext() as context:
            context.prec, context.rounding = digits, direction
            return fn()
    def interval(v):
        return (rounded(lambda: Decimal(v.numerator)/Decimal(v.denominator), ROUND_FLOOR),
                rounded(lambda: Decimal(v.numerator)/Decimal(v.denominator), ROUND_CEILING))
    def add(a, b):
        return (rounded(lambda: a[0]+b[0], ROUND_FLOOR),
                rounded(lambda: a[1]+b[1], ROUND_CEILING))
    def multiply(a, b):
        return (min(rounded(lambda: p*q, ROUND_FLOOR) for p in a for q in b),
                max(rounded(lambda: p*q, ROUND_CEILING) for p in a for q in b))
    def isum(values):
        s = interval(F(0))
        for v in values:
            s = add(s, v)
        return s
    change = [b-a for a, b in zip(x, y)]
    phi_terms, slope_terms = [], []
    two = interval(F(2))
    for weight, a, b in blocks:
        ai = [[interval(v) for v in row] for row in a]
        r = [add(isum(multiply(v, interval(z)) for v, z in zip(row, x)), interval(-target))
             for row, target in zip(ai, b)]
        dy = [isum(multiply(v, interval(z)) for v, z in zip(row, change)) for row in ai]
        inner = isum(add(multiply(two, multiply(rr, d)), multiply(d, d)) for rr, d in zip(r, dy))
        slope = multiply(two, isum(multiply(rr, d) for rr, d in zip(r, dy)))
        phi_terms.append(multiply(interval(weight), inner))
        slope_terms.append(multiply(interval(weight), slope))
    decrease, slope = isum(phi_terms), isum(slope_terms)
    if recorded_gradient is not None:
        slope = isum(multiply(interval(v), interval(d)) for v, d in zip(recorded_gradient, change))
    margin = add(decrease, multiply(interval(-ff(1e-4)), slope))
    exact_decrease = delta(blocks, x, y)
    exact_slope = sum((v*(b-a) for v, a, b in zip(evaluate(blocks, x)[1], x, y)), F(0))
    if recorded_gradient is not None:
        exact_slope = sum((v*d for v, d in zip(recorded_gradient, change)), F(0))
    exact_margin = exact_decrease-ff(1e-4)*exact_slope
    assert F(margin[0]) <= exact_margin <= F(margin[1])
    assert F(slope[0]) <= exact_slope <= F(slope[1])
    return {'decimal_digits': digits, 'armijo_margin_interval': [str(v) for v in margin],
            'slope_domain': 'recorded_native_gradient' if recorded_gradient is not None else 'exact_quadratic_gradient',
            'slope_interval': [str(v) for v in slope],
            'exact_rational_inclusion_asserted': True,
            'certified_strict_descent_and_armijo': bool(margin[1] < 0 and slope[1] < 0)}


def bound_flat_gradient(blocks, x):
    """Conservative serial dot/AXPY graph bound on exact rational coefficients.

    Rounds each flattened coefficient and target to binary64 first; includes
    that representation error separately. Assumes nearest, no over/underflow.
    Gamma uses 2n (product + sum), padded 2ops for residual and scalar factors.
    Entire bound arithmetic is rational, not a falsely outward float estimate.
    """
    u = F(1, 2**53)
    def gamma(k):
        return k*u/(1-k*u)
    total = [F(0)]*len(x)
    magnitude = [F(0)]*len(x)
    for w, a, b in blocks:
        ar = [[ff(float(v)) for v in row] for row in a]
        br = [ff(float(v)) for v in b]
        wr = ff(float(w))
        r = [v-y for v, y in zip(mv(a, x), b)]
        errs = []
        for row, rounded, target, rt in zip(a, ar, b, br):
            coefficient_error = sum((abs(v-rv)*abs(y) for v, rv, y in zip(row, rounded, x)), F(0))+abs(target-rt)
            dot_size = sum((abs(v*y) for v, y in zip(rounded, x)), F(0))+abs(rt)
            errs.append(coefficient_error+gamma(2*len(x)+2)*dot_size)
        for j in range(len(x)):
            size = sum((abs(row[j]*v) for row, v in zip(ar, r)), F(0))
            representation = sum((abs(row[j]-rr[j])*abs(v) for row, rr, v in zip(a, ar, r)), F(0))
            propagation = sum((abs(row[j])*e for row, e in zip(ar, errs)), F(0))
            inner = representation+propagation+gamma(2*len(a)+2)*(size+propagation)
            total[j] += 2*abs(wr)*inner+2*abs(w-wr)*sum((abs(row[j]*v) for row, v in zip(a, r)), F(0))
            magnitude[j] += 2*abs(wr)*(size+inner)
    return [e+gamma(2*len(blocks)+2)*size for e, size in zip(total, magnitude)]


seen, directions = [], []
record = l2._RecordedProjectedGNCG._record
find_direction = l2._RecordedProjectedGNCG.findSearchDirection
def observe(opt):
    pair = record(opt)
    seen.append(opt.xc.copy())
    return pair
l2._RecordedProjectedGNCG._record = observe
def observe_direction(opt):
    d = find_direction(opt)
    directions.append((opt.xc.copy(), d.copy(), opt.g.copy()))
    return d
l2._RecordedProjectedGNCG.findSearchDirection = observe_direction
req, obs, noise, prior, jac, independent_a, independent_b = t['six_cell_control']('diagonal_sd', 1500., 'upper_lower')
problem = l2._build_problem(req, obs, noise, prior, np.arange(5, dtype=np.int64), .01)
result = l2._solve_partition(problem, prior)
l2._RecordedProjectedGNCG._record = record
l2._RecordedProjectedGNCG.findSearchDirection = find_direction
g = fm(problem['simulation'].G)
w = fm(problem['misfit'].W.toarray())
blocks = [(F(1), mm(w, g), mv(w, list(map(ff, problem['misfit'].data.dobs))))]
components = []
for alpha, f in zip(problem['regularization'].multipliers, problem['regularization'].objfcts):
    if float(alpha) == 0:
        continue
    wd = mm(fm(f.W.toarray()), fm(f.f_m_deriv(problem['reference_q']).toarray()))
    blocks.append((ff(problem['beta_engine'])*ff(alpha), wd, mv(wd, list(map(ff, problem['reference_q'])))))
    components.append({'class': type(f).__name__, 'rows': len(wd), 'alpha': float(alpha)})


def certificate(label, bb):
    h, c = exact_system(bb)
    assert h == list(map(list, zip(*h)))
    optimum, pivots = solve(h, c)
    lower, upper = map(ff, [-1.5, 1.5])
    assert all(lower < x < upper for x in optimum)
    exact_phi, exact_g = evaluate(bb, optimum)
    assert all(v == 0 for v in exact_g)
    nearest = np.array([float(x) for x in optimum])
    xp = list(map(ff, nearest))
    initial = list(map(ff, seen[0]))
    init_norm = max(F(1), norm(evaluate(bb, initial)[1]))
    final = list(map(ff, seen[-1]))
    inverse_columns = [solve(h, [F(int(i == j)) for i in range(6)])[0] for j in range(6)]
    inverse_norm = max(sum((abs(inverse_columns[j][i]) for j in range(6)), F(0)) for i in range(6))
    hnorm = max(sum(map(abs, row), F(0)) for row in h)
    # Round-nearest exact optimum certificate: backward residual and objective gap.
    phi_round, grad_round = evaluate(bb, xp)
    floor_bound = max(sum((abs(h[i][j])*ff(math.ulp(nearest[j]))/2 for j in range(6)), F(0)) for i in range(6))
    rows = []
    for index, q in enumerate(seen):
        x = list(map(ff, q))
        phi, grad = evaluate(bb, x)
        pn, gn = native(q, problem)
        pf, gf = fsum_evaluate(bb, q)
        rows.append({'index': index, 'q_hex': [float(v).hex() for v in q],
                     'phi_exact_rounded': float(phi), 'gradient_exact_inf': float(norm(grad)),
                     'gradient_exact_normalized_full': float(norm(grad)/init_norm),
                     'phi_native': pn, 'gradient_native_inf': gn,
                     'phi_fsum_flattened': pf, 'gradient_fsum_flattened_inf': gf,
                     'gradient_error_bound_flattened_inf': float(max(bound_flat_gradient(bb, x))),
                     'gap_to_exact_optimum': float(phi-exact_phi)})
    # Diagnostic refinement solves corrections, never registers accepted states.
    current = seen[-1].copy()
    refinement = []
    h64 = np.array([[float(v) for v in row] for row in h])
    for k in range(6):
        x = list(map(ff, current))
        grad = evaluate(bb, x)[1]
        correction = np.linalg.solve(h64, -np.array([float(v) for v in grad]))
        trial = current+correction
        y = list(map(ff, trial))
        improvement = delta(bb, x, y)
        pn, gn = native(trial, problem)
        slope = sum((v*(b-a) for v, a, b in zip(grad, x, y)), F(0))
        refinement.append({'index': k, 'distinct': bool(np.any(trial != current)),
                           'correction_inf': float(np.linalg.norm(correction, ord=np.inf)),
                           'actual_displacement_inf': float(np.linalg.norm(trial-current, ord=np.inf)),
                           'objective_delta_exact': float(improvement),
                           'armijo_inequality_only': bool(improvement <= ff(1e-4)*slope),
                           'admissible_strict_chord': bool(np.any(trial != current) and slope < 0 and improvement <= ff(1e-4)*slope),
                           'gradient_exact_inf': float(norm(evaluate(bb, y)[1])),
                           'gradient_native_inf': gn, 'phi_native': pn})
        if not np.any(trial != current) or improvement >= 0:
            break
        current = trial
    native_trials = []
    for index, (state, direction, recorded_gradient) in enumerate(directions):
        if index < 3:
            continue
        x = list(map(ff, state))
        grad = evaluate(bb, x)[1]
        for j in range(20):
            trial = np.clip(state+(2.**-j)*direction, -1.5, 1.5)
            y = list(map(ff, trial))
            slope = sum((v*(b-a) for v, a, b in zip(grad, x, y)), F(0))
            decrease = delta(bb, x, y)
            pn, gn = native(trial, problem)
            native_trials.append({'direction_index': index, 'trial': j,
                                  'distinct': bool(np.any(trial != state)),
                                  'actual_displacement_inf': float(np.linalg.norm(trial-state, ord=np.inf)),
                                  'objective_delta_exact': float(decrease), 'slope_exact': float(slope),
                                  'armijo_exact_margin': float(decrease-ff(1e-4)*slope),
                                  'armijo_exact_pass_strict_direction': bool(slope < 0 and decrease <= ff(1e-4)*slope),
                                  'gradient_exact_inf': float(norm(evaluate(bb, y)[1])),
                                  'gradient_native_inf': gn, 'phi_native': pn})
            if j == 0:
                native_trials[-1]['directed_precision_ladder'] = [directed_margin(bb, x, y, p, list(map(ff, recorded_gradient))) for p in (17, 25, 34, 50, 80)]
            if not np.any(trial != state):
                break
    serialized_blocks = [{'weight': str(weight), 'a': [[str(x) for x in row] for row in a],
                          'b': [str(x) for x in b]} for weight, a, b in bb]
    return {'domain': label, 'rows': sum(len(a) for _, a, _ in bb),
            'exact_coefficients_sha256': hashlib.sha256(json.dumps(serialized_blocks, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'exact_optimum_q_rationals': [str(x) for x in optimum],
            'exact_spd_positive_pivots': [float(p) for p in pivots],
            'exact_optimum_interior': True, 'exact_optimum_gradient_zero': True,
            'optimum_q_rounded': nearest.tolist(), 'nearest_q_hex': [x.hex() for x in nearest],
            'minimum_exact_bound_margin_q': float(min(min(x-lower, upper-x) for x in optimum)),
            'gradient_at_nearest_q_exact_inf': float(norm(grad_round)),
            'nearest_q_rounding_gradient_upper_bound': float(floor_bound),
            'nearest_objective_gap': float(phi_round-exact_phi),
            'native_at_nearest_q': dict(zip(('phi', 'gradient_inf'), native(nearest, problem))),
            'initial_exact_gradient_norm': float(init_norm), 'hessian_inf_norm': float(hnorm),
            'inverse_hessian_inf_norm': float(inverse_norm), 'condition_hessian_inf': float(hnorm*inverse_norm),
            'terminal_model_error_inf_q_exact': float(norm([x-y for x, y in zip(final, optimum)])),
            'terminal_error_bound_inf_q_from_kkt': float(inverse_norm*norm(evaluate(bb, final)[1])),
            'accepted_states': rows, 'refinement_DIAGNOSTIC_NOT_ACCEPTED': refinement,
            'native_direction_trials_DIAGNOSTIC_NOT_ACCEPTED': native_trials,
            'last_native_accepted_step_delta_exact': float(delta(bb, list(map(ff, seen[-2])), final))}


output = {'schema': 'm02-l2-precision-research-1', 'acceptance': False,
          'assertions_executed': ['exact_symmetric_H_and_SPD_pivots_positive', 'exact_H_optimum_equals_rhs',
                                  'exact_optimum_strictly_inside_declared_bounds', 'exact_optimum_gradient_zero',
                                  'residual_delta_equals_exact_objective_difference',
                                  'directed_decimal_margin_contains_rational_truth',
                                  'directed_decimal_slope_contains_rational_truth'],
          'specimen': 'six_cell/diagonal_sd/1500/upper_lower/unsealed_development',
          'frozen_result': {'status': result['status'], 'reason': result['reason'],
                            'iterations': result['iterations'], 'kkt_normalized': result['kkt_normalized'],
                            'relative_changes': result['trace']['relative_changes'].tolist()},
          'float64': {'bits': np.finfo(np.float64).nmant+1, 'unit_roundoff': 2.**-53},
          'longdouble': {'bits': np.finfo(np.longdouble).nmant+1, 'itemsize': np.dtype(np.longdouble).itemsize},
          'components': components, 'certificates': [certificate('fixed_native_operand_quadratic', blocks),
              certificate('independent_Choclo_pairwise_R_Cholesky_rounded_augmented',
                          [(F(1), fm(independent_a), list(map(ff, independent_b)))])],
          'sha256': {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in
                     ('data-pipeline/gravity_l2.py', 'tests/numerics/test_gravity_l2.py',
                      'docs/research/m02-l2-precision-diagnostic-2026-10-03.py')}}
print(json.dumps(output, indent=2, allow_nan=False))
