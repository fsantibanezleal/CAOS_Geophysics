"""Actual induced magnetic quantities on frozen native operands.

Geometry construction is metadata-only. This is not an optimizer, correction,
field-source verifier or online admission. Returned snapshots are owned and
write-protected, not tamperproof; no returned storage is retained as state.
"""

from decimal import Context, Decimal, localcontext
import hashlib
import math
from time import monotonic

import numpy as np


QUANTITIES = ('secondary_enu_nT', 'linear_tmi_nT', 'exact_total_anomaly_nT')


def native_array(value, shape, name):
    if type(value) is not np.ndarray or value.dtype != np.dtype('float64'):
        raise TypeError(f'{name}: exact native float64 ndarray required')
    if value.shape != shape:
        raise ValueError(f'{name}: exact shape required')


def owned(value):
    out = np.array(value, dtype=np.float64, order='C', copy=True)
    if not np.isfinite(out).all():
        raise ValueError('nonfinite native operand or derived result')
    out.flags.writeable = False
    return out


def finite_float(value, name, positive=False):
    if type(value) is not float or not math.isfinite(value):
        raise ValueError(f'{name}: finite native float required')
    if positive and value <= 0.:
        raise ValueError(f'{name}: positive native float required')


def _check_deadline(deadline):
    finite_float(deadline, 'deadline')
    if monotonic() > deadline:
        raise TimeoutError('magnetic operator: wall_cap')


class MagneticQuantity:
    """Retained rounded A_b=.01*Gchi with real norm-minus-retained-F semantics."""

    def __init__(self, Gchi, B0, direction, F, quantity):
        if type(Gchi) is not np.ndarray or Gchi.dtype != np.dtype('float64'):
            raise TypeError('Gchi: exact native float64 ndarray required')
        if (Gchi.ndim != 2 or Gchi.shape[0] % 3 or
                not 1 <= Gchi.shape[0]//3 <= 2048 or not 1 <= Gchi.shape[1] <= 2048 or
                Gchi.size > 12582912):
            raise ValueError('Gchi: count/shape outside closed bounds')
        native_array(B0, (3,), 'B0')
        native_array(direction, (3,), 'direction')
        finite_float(F, 'F')
        if not 1. <= F <= 1e6:
            raise ValueError('F: outside declared range')
        if type(quantity) is not str or quantity not in QUANTITIES:
            raise ValueError('quantity: unsupported physical quantity')
        # All metadata/counts above precede scans, multiplication and copies.
        if not np.isfinite(Gchi).all():
            raise ValueError('Gchi: nonfinite')
        with np.errstate(over='raise', invalid='raise'):
            self.__ab = owned(.01*Gchi)
        self.__b0, self.__direction = owned(B0), owned(direction)
        self.__f, self.__quantity = F, quantity
        self.rows, self.parameters = Gchi.shape[0]//3, Gchi.shape[1]
        self.components = 3 if quantity == QUANTITIES[0] else 1
        self.operand_sha256 = hashlib.sha256(
            self.__ab.astype('<f8', copy=False).tobytes(order='C')+
            self.__b0.astype('<f8', copy=False).tobytes()+
            self.__direction.astype('<f8', copy=False).tobytes()+
            np.array([F], dtype='<f8').tobytes()+quantity.encode('ascii')).hexdigest()

    def operand_snapshot(self):
        """Internal independent snapshots, never mutable trusted-state aliases."""
        return (owned(self.__ab), owned(self.__b0), owned(self.__direction),
                self.__f, self.__quantity)

    def evaluate(self, q):
        native_array(q, (self.parameters,), 'q')
        if not np.isfinite(q).all() or np.any(q < 0.) or np.any(q > 10.):
            raise ValueError('q: outside finite production box0..10')
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            b = (self.__ab @ q).reshape(self.rows, 3)
            total = self.__b0+b
            norms, exact = [], []
            with localcontext(Context(prec=80, Emin=-9999, Emax=9999)):
                background = [Decimal.from_float(float(v)) for v in self.__b0]
                f = Decimal.from_float(self.__f)
                delta0 = sum(v*v for v in background)-f*f
                for row in b:
                    secondary = [Decimal.from_float(float(v)) for v in row]
                    square = sum((a+v)**2 for a, v in zip(background, secondary))
                    if not square.is_finite() or square <= 0:
                        raise ValueError('total field domain: nonpositive norm')
                    norm = square.sqrt()
                    if norm/f <= Decimal.from_float(1e-8):
                        raise ValueError('total field domain: T/F<=1e-8')
                    numerator = delta0+2*sum(a*v for a, v in zip(background, secondary))+sum(v*v for v in secondary)
                    norms.append(float(norm))
                    exact.append(float(numerator/(norm+f)))
            norm_array = np.array(norms)
            if self.__quantity == QUANTITIES[0]:
                prediction, jac = b, self.__ab
            elif self.__quantity == QUANTITIES[1]:
                prediction = (b @ self.__direction)[:, None]
                jac = np.einsum('c,nca->na', self.__direction,
                                self.__ab.reshape(self.rows, 3, self.parameters))
            else:
                prediction = np.array(exact)[:, None]
                jac = np.einsum('nc,nca->na', total/norm_array[:, None],
                                self.__ab.reshape(self.rows, 3, self.parameters))
        return dict(prediction_nT=owned(prediction), jacobian_nT_per_q=owned(jac),
                    secondary_enu_nT=owned(b), total_norm_nT=owned(norm_array))


def build_operator(raw, rows, *, deadline):
    """Closed original-order metadata -> actual public SimPEG component kernel.

    No observation/noise spans are decoded. An outer coordinate may be predicted;
    that never opens its likelihood. The caller owns the per-process resource
    authority; a monotonic clock check is not native-call containment.
    """
    _check_deadline(deadline)
    if type(rows) is not tuple or not 1 <= len(rows) <= 2048:
        raise TypeError('rows: bounded native tuple required')
    if any(type(i) is not int or i < 0 for i in rows) or any(a >= b for a, b in zip(rows, rows[1:])):
        raise ValueError('rows: strictly increasing original native indices')
    from magnetic_survey_json import parse_request
    from magnetic_survey import plan_geometry
    handle = parse_request(raw)
    plan, meta = plan_geometry(handle), handle.metadata()
    if not plan['eligibility']['local_processing']:
        raise ValueError('rights: local magnetic processing unresolved')
    if any(node['operation'] != 'original' for node in meta['processing']['nodes']):
        raise ValueError('lineage: original identity only until provenance binding')
    flags = meta['geometry']['usable']['data']
    if any(i >= len(flags) or not flags[i] for i in rows):
        raise ValueError('rows: original usable indices required')
    _check_deadline(deadline)
    # Heavy engine imports occur only after the bounded schema and geometry seal.
    import magnetic_forward as forward
    from discretize import TensorMesh
    from simpeg import maps
    from simpeg.potential_fields import magnetics
    forward._runtime()
    spec = meta['geometry']['mesh']
    widths = [np.array(spec[k]['data'], dtype=np.float64)
              for k in ('widths_x_m', 'widths_y_m', 'widths_z_m')]
    origin = np.array(spec['origin_m']['data'], dtype=np.float64)
    active = np.array(spec['active']['data'], dtype=bool)
    edges = [o+np.r_[0., np.cumsum(w)] for o, w in zip(origin, widths)]
    ijk = np.unravel_index(np.arange(active.size), tuple(map(len, widths)), order='F')
    declared = np.column_stack([e[i+s] for e, i in zip(edges, ijk) for s in (0, 1)])
    tensor = TensorMesh(widths, origin=origin)
    forward._tensor_state(tensor, edges, widths, declared)
    xyz = np.array(meta['geometry']['receivers_m']['data'], dtype=np.float64).reshape(-1, 3)[list(rows)]
    field = meta['inducing_field']
    rx = magnetics.receivers.Point(xyz, components=['bx', 'by', 'bz'])
    source = magnetics.sources.UniformBackgroundField(receiver_list=[rx], amplitude=field['F_nT'],
        inclination=field['I_deg'], declination=field['D_deg'])
    n_active = int(active.sum())
    sim = magnetics.simulation.Simulation3DIntegral(tensor, survey=magnetics.Survey(source),
        active_cells=active, chiMap=maps.IdentityMap(nP=n_active), model_type='scalar',
        engine='geoana', store_sensitivities='ram', sensitivity_dtype=np.float64,
        n_processes=1, is_amplitude_data=False)
    kernel = sim.G
    native_array(kernel, (3*len(rows), n_active), 'engine.G')
    jac = sim.getJ(np.zeros(n_active))
    if not np.allclose(jac, kernel, rtol=1e-12, atol=1e-10):
        raise RuntimeError('engine: IdentityMap getJ/Gchi mismatch')
    _check_deadline(deadline)
    b0 = np.array(source.b0, dtype=np.float64)
    return MagneticQuantity(kernel, b0, b0/field['F_nT'], float(field['F_nT']),
                            meta['processing']['quantity'])
