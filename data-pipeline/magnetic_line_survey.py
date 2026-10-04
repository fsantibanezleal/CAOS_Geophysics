"""M03 global streamed-operator algebra and provisional allocation planning.

Not an intake, field-eligibility decision, scientific Result or host admission.
Only small independent algebra controls execute without a native containment
controller. The old magnetic_lines implementation and limits are unchanged.
"""
from __future__ import annotations

from hashlib import sha256
from importlib import import_module
from importlib.metadata import distribution, PackageNotFoundError, version
import math
from pathlib import Path
import platform


ROW_LIMIT = 8000000
SOURCE_LIMIT = 65536
RSS_LIMIT = 4294967296
SCRATCH_LIMIT = 34359738368
EPSILON = 2.220446049250313e-16
ENGINE_PINS = {"numpy": "2.2.6", "scipy": "1.15.2", "harmonica": "0.7.0",
               "verde": "1.9.0", "scikit-learn": "1.9.1",
               "threadpoolctl": "3.7.0", "xarray": "2026.9.0"}
SOURCE_PINS = {
    "harmonica._equivalent_sources.cartesian": (
        "harmonica", "harmonica/_equivalent_sources/cartesian.py",
        "f62f2b5ad5a0ece1b66482a98d700f5093f8f5e18fd05062ca24e72437bea44f"),
    "verde.base.least_squares": (
        "verde", "verde/base/least_squares.py",
        "a4eb01f891016a50be2451432842e0449ac924ec2fdfef8ecb182cc1f36ec090"),
    "scipy.sparse.linalg._isolve.lsmr": (
        "scipy", "scipy/sparse/linalg/_isolve/lsmr.py",
        "f1e60be3f5216f602bf33535acc72474aa80fbe0149d5929145d0432bc29e0ce"),
}


class SurveyError(ValueError):
    """Closed safe error: arbitrary native messages never enter this object."""
    def __init__(self, code, stage):
        if type(code) is not str or code not in {"invalid_contract", "custody_mismatch", "metadata_ineligible",
                        "unsupported_operation", "nonconverged", "cancelled",
                        "resource_refused", "io_failed"}:
            code = "invalid_contract"
        if type(stage) is not str or stage not in {"ingest", "seal", "correction", "crossover", "fit",
                         "predict", "transform", "evaluate", "export", "replay"}:
            stage = "fit"
        message = code + ":" + stage
        self.error = dict(schema="magnetic-line-survey-error/1", code=code,
                          stage=stage, field=None, message=message,
                          partial_manifest_sha256=None)
        super().__init__(message)


def _count(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise SurveyError("resource_refused", "seal")
    return value


def allocation_bounds(rows, sources, exported_cells=0, fft_cells=0):
    """Pure integer rejection arithmetic, never a measured resource verdict."""
    n = _count(rows, 1, ROW_LIMIT)
    m = _count(sources, 1, SOURCE_LIMIT)
    p = _count(exported_cells, 0, 1048576)
    q = _count(fft_cells, 0, 4194304)
    r, c = 4096, 128
    cache, reserve = 134217728, 1073741824
    return dict(
        fit_buffer_bytes=8 * (32*n + 64*m + 8*r*c + 48*r + 24*c) + cache + reserve,
        geometry_buffer_bytes=cache + 33554432 + 8*(32*r + 16*c) + reserve,
        transform_buffer_bytes=max(
            16*16*q + 8*16*p + cache + reserve,
            8*(16*r + 64*m + 8*r*c + 24*c) + cache + reserve))


def plan_capacity(rows, sources, *, auxiliary_rows=0, crossover_candidates=0,
                  exported_cells=0, fft_cells=0, raw_bytes=1, auxiliary_bytes=0):
    """Conservative25-fit bound using max fold N/M, no hidden coarsening.

    A subsequent geometry planner may sum the25 exact fold shapes instead;
    this independent entry only refuses conservatively, never admits a host.
    """
    bounds = allocation_bounds(rows, sources, exported_cells, fft_cells)
    _count(auxiliary_rows, 0, 16000000)
    _count(crossover_candidates, 0, 8000000)
    _count(raw_bytes, 1, 4294967296)
    _count(auxiliary_bytes, 0, 4294967296)
    scratch = (2*(raw_bytes + auxiliary_bytes) + 512*rows + 256*sources +
               256*crossover_candidates + 256*exported_cells + 128*fft_cells + 268435456)
    pairs = 25*4004*rows*sources + exported_cells*sources
    if max(bounds.values()) > RSS_LIMIT or scratch > SCRATCH_LIMIT or pairs > 10**15:
        raise SurveyError("resource_refused", "seal")
    return dict(profile="m03-offline-stream/1", rows=rows, sources=sources,
                auxiliary_rows=auxiliary_rows, crossover_candidates=crossover_candidates,
                exported_cells=exported_cells, fft_cells=fft_cells,
                raw_bytes=raw_bytes, auxiliary_bytes=auxiliary_bytes, **bounds,
                scratch_bound_bytes=scratch, kernel_pair_bound=pairs,
                resource_state="unmeasured")


def engines():
    """Fixed installed-file reads, actual versions and loaded-origin checks."""
    if platform.python_implementation() != "CPython" or platform.python_version_tuple()[:2] != ("3", "12"):
        raise SurveyError("custody_mismatch", "fit")
    try:
        if any(version(name) != expected for name, expected in ENGINE_PINS.items()):
            raise SurveyError("custody_mismatch", "fit")
        for name, (package, relative, digest) in SOURCE_PINS.items():
            fixed = Path(distribution(package).locate_file(relative)).resolve(strict=True)
            if sha256(fixed.read_bytes()).hexdigest() != digest:
                raise SurveyError("custody_mismatch", "fit")
            loaded = import_module(name)
            if Path(loaded.__file__).resolve(strict=True) != fixed:
                raise SurveyError("custody_mismatch", "fit")
    except (PackageNotFoundError, OSError, AttributeError, TypeError, ImportError):
        raise SurveyError("custody_mismatch", "fit") from None
    return import_module("numpy"), import_module("harmonica")


def _array(np, value, shape):
    if type(value) not in (np.ndarray, np.memmap) or value.shape != shape or \
       value.dtype != np.dtype("<f8") or not value.flags.c_contiguous or value.flags.writeable:
        raise SurveyError("invalid_contract", "fit")
    return value


def _finite(np, value):
    if not np.isfinite(value).all():
        raise SurveyError("metadata_ineligible", "fit")


def _chunks(size, step):
    for start in range(0, size, step):
        yield slice(start, min(size, start + step))


def _sum_into(total, compensation, increment):
    adjusted = increment - compensation
    updated = total + adjusted
    compensation[:] = (updated - total) - adjusted
    total[:] = updated


class GlobalOperator:
    """One global model; row/source chunks change storage/actions, not physics.

    Internal algebra entry consumes read-only admitted arrays. Metadata/custody
    are upstream responsibilities, not claimed to be checked by this class.
    Full-shape execution remains refused until native lifetime control exists.
    """
    def __init__(self, xyz, sources, sigma_nT=None, *, chunk_rows=4096, chunk_sources=128):
        _count(chunk_rows, 1, 4096)
        _count(chunk_sources, 1, 128)
        # Type discovery is an import, not an unbounded scientific allocation.
        np, hm = engines()
        if type(xyz) not in (np.ndarray, np.memmap) or xyz.ndim != 2 or xyz.shape[1] != 3 or \
           type(sources) not in (np.ndarray, np.memmap) or sources.ndim != 2 or sources.shape[1] != 3:
            raise SurveyError("invalid_contract", "fit")
        n, m = len(xyz), len(sources)
        plan_capacity(n, m)
        if n < 2:
            raise SurveyError("invalid_contract", "fit")
        # No caller boolean or provisional envelope grants large-run execution.
        if n > 128 or m > 32:
            raise SurveyError("resource_refused", "fit")
        self.xyz = _array(np, xyz, (n, 3))
        self.sources = _array(np, sources, (m, 3))
        self.n, self.m = n, m
        self.r, self.c = chunk_rows, chunk_sources
        self.np = np
        _finite(np, self.xyz)
        _finite(np, self.sources)
        if not np.all(sources[:, 2] == sources[0, 2]) or not np.all(xyz[:, 2] > sources[0, 2]):
            raise SurveyError("metadata_ineligible", "fit")
        self.root_weights = np.ones(n, dtype=np.float64)
        if sigma_nT is not None:
            sigma = _array(np, sigma_nT, (n,))
            _finite(np, sigma)
            if np.any(sigma <= 0):
                raise SurveyError("metadata_ineligible", "fit")
            with np.errstate(over="ignore", under="ignore", divide="ignore", invalid="ignore"):
                self.root_weights = 1 / sigma
                weights = self.root_weights**2
            if not np.isfinite(weights).all() or np.any(weights <= 0):
                raise SurveyError("metadata_ineligible", "fit")
        self.weighted = sigma_nT is not None
        self.root_weights.flags.writeable = False
        self.model = hm.EquivalentSources(dtype="float64", parallel=False)
        self.forward_calls = self.adjoint_calls = 0
        self.scales = self._scales()
        self.scales.flags.writeable = False
        from scipy.sparse.linalg import LinearOperator
        self.operator = LinearOperator((n, m), matvec=self._forward,
                                       rmatvec=self._adjoint, dtype=np.dtype("float64"))

    def _direct(self, row, col):
        np = self.np
        x, s = self.xyz[row], self.sources[col]
        # Native Harmonica uses squared distance; detect overflow BEFORE it.
        with np.errstate(over="ignore", under="ignore", invalid="ignore", divide="ignore"):
            d2 = np.zeros((len(x), len(s)), dtype=np.float64)
            for axis in range(3):
                delta = x[:, axis, None] - s[None, :, axis]
                d2 += delta**2
            j = 1 / np.sqrt(d2)
        if not np.isfinite(d2).all() or np.any(d2 <= 0) or not np.isfinite(j).all() or np.any(j <= 0):
            raise SurveyError("metadata_ineligible", "fit")
        return j

    def _kernel(self, row, col):
        # Check distances before the real engine allocates/computes its block.
        self._direct(row, col)
        x, s = self.xyz[row], self.sources[col]
        j = self.model.jacobian(tuple(x[:, axis] for axis in range(3)),
                                tuple(s[:, axis] for axis in range(3)))
        if type(j) is not self.np.ndarray or j.shape != (len(x), len(s)) or j.dtype != self.np.float64:
            raise SurveyError("custody_mismatch", "fit")
        _finite(self.np, j)
        if self.np.any(j <= 0):
            raise SurveyError("metadata_ineligible", "fit")
        return j

    def _scales(self):
        np = self.np
        scales = np.empty(self.m, dtype=np.float64)
        for col in _chunks(self.m, self.c):
            width = col.stop - col.start
            summed, comp, maximum = (np.zeros(width) for _ in range(3))
            for row in _chunks(self.n, self.r):
                j = self._kernel(row, col)
                _sum_into(summed, comp, np.array([math.fsum(j[:, k]) for k in range(width)]))
                maximum = np.maximum(maximum, j.max(axis=0))
            mean = summed / self.n
            summed[:] = comp[:] = 0
            for row in _chunks(self.n, self.r):
                deviations = (self._kernel(row, col) - mean)**2
                _sum_into(summed, comp, np.array([math.fsum(deviations[:, k]) for k in range(width)]))
            std = np.sqrt(summed / self.n)
            if not np.isfinite(std).all() or np.any(std <= 1024 * EPSILON * maximum):
                raise SurveyError("metadata_ineligible", "fit")
            scales[col] = std
        return scales

    def _forward(self, value):
        np = self.np
        if type(value) is not np.ndarray:
            raise SurveyError("invalid_contract", "fit")
        if value.shape not in ((self.m,), (self.m, 1)) or value.dtype != np.float64:
            raise SurveyError("invalid_contract", "fit")
        value = value.reshape(self.m)
        _finite(np, value)
        result = np.empty(self.n, dtype=np.float64)
        for row in _chunks(self.n, self.r):
            total, comp = (np.zeros(row.stop-row.start) for _ in range(2))
            for col in _chunks(self.m, self.c):
                _sum_into(total, comp, self._kernel(row, col) @ (value[col] / self.scales[col]))
            result[row] = total * self.root_weights[row]
        _finite(np, result)
        self.forward_calls += 1
        return result

    def _adjoint(self, value):
        np = self.np
        if type(value) is not np.ndarray:
            raise SurveyError("invalid_contract", "fit")
        if value.shape not in ((self.n,), (self.n, 1)) or value.dtype != np.float64:
            raise SurveyError("invalid_contract", "fit")
        value = value.reshape(self.n)
        _finite(np, value)
        result, comp = np.zeros(self.m), np.zeros(self.m)
        for row in _chunks(self.n, self.r):
            weighted = value[row] * self.root_weights[row]
            for col in _chunks(self.m, self.c):
                _sum_into(result[col], comp[col],
                          self._kernel(row, col).T @ weighted / self.scales[col])
        _finite(np, result)
        self.adjoint_calls += 1
        return result


def global_operator(xyz, sources, sigma_nT=None, *, chunk_rows=4096, chunk_sources=128):
    return GlobalOperator(xyz, sources, sigma_nT, chunk_rows=chunk_rows,
                          chunk_sources=chunk_sources)


def _damping(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 1e6:
        raise SurveyError("invalid_contract", "fit")
    return float(value)


def _squared_norm(value):
    """Scaled norm avoids silently losing a nonzero objective to dot underflow."""
    norm = math.hypot(*(float(x) for x in value))
    square = norm * norm
    if not math.isfinite(square) or (norm > 0 and square == 0):
        raise SurveyError("nonconverged", "fit")
    # Use compensated component squares for representable results so exact
    # integer controls stay exact; the scaled norm above detects lost totals.
    return math.fsum(float(x) * float(x) for x in value)


def check_stationarity(model, values, damping, c, istop, conda):
    if type(model) is not GlobalOperator:
        raise SurveyError("invalid_contract", "fit")
    try:
        with model.np.errstate(over="raise", invalid="raise", divide="raise"):
            return _stationarity(model, values, damping, c, istop, conda)
    except (FloatingPointError, OverflowError, model.np.linalg.LinAlgError):
        raise SurveyError("nonconverged", "fit") from None


def _stationarity(model, values, damping, c, istop, conda):
    """Independent direct-kernel gradient, not the solver recurrence/adjoint."""
    np = model.np
    damping = _damping(damping)
    y = _array(np, values, (model.n,))
    c = _array(np, c, (model.m,))
    _finite(np, y)
    _finite(np, c)
    if type(istop) is not int or istop not in (0, 1, 2, 4, 5) or \
       type(conda) not in (int, float) or not math.isfinite(conda) or not 0 <= conda < 1e8:
        raise SurveyError("nonconverged", "fit")
    atb, atprediction, gradient = (np.zeros(model.m) for _ in range(3))
    cb, cp, cg = (np.zeros(model.m) for _ in range(3))
    data_terms = []
    for row in _chunks(model.n, model.r):
        prediction, comp = (np.zeros(row.stop-row.start) for _ in range(2))
        for col in _chunks(model.m, model.c):
            a = model._direct(row, col) * model.root_weights[row, None] / model.scales[col]
            _sum_into(prediction, comp, a @ c[col])
        b = model.root_weights[row] * y[row]
        residual = prediction - b
        data_terms.append(_squared_norm(residual))
        for col in _chunks(model.m, model.c):
            a = model._direct(row, col) * model.root_weights[row, None] / model.scales[col]
            _sum_into(atb[col], cb[col], a.T @ b)
            _sum_into(atprediction[col], cp[col], a.T @ prediction)
            _sum_into(gradient[col], cg[col], a.T @ residual)
    gradient += damping * c
    data_term = math.fsum(data_terms)
    penalty_square = _squared_norm(c)
    penalty = damping * penalty_square
    if penalty_square > 0 and penalty == 0:
        raise SurveyError("nonconverged", "fit")
    denominator = max(float(np.max(np.abs(atb))), float(np.max(np.abs(atprediction))),
                      damping * float(np.max(np.abs(c))))
    absolute = float(np.max(np.abs(gradient)))
    relative = absolute / denominator if denominator > 0 else (0. if absolute == 0 else math.inf)
    error_bound = math.hypot(*(float(x) for x in gradient)) / damping
    if not all(math.isfinite(t) for t in (data_term, penalty, data_term+penalty,
                                        denominator, absolute, relative, error_bound)) or relative > 1e-9:
        raise SurveyError("nonconverged", "fit")
    return dict(data_term=data_term, regularization_term=penalty,
                objective=data_term+penalty, gradient_denominator=denominator,
                stationarity_inf=absolute, stationarity_relative=relative,
                coefficient_error_bound_nT=error_bound)


def solve_global(model, values, damping):
    """Internal algebra solve, deliberately not a fabricated SurveyResult."""
    if type(model) is not GlobalOperator:
        raise SurveyError("invalid_contract", "fit")
    np = model.np
    damping = _damping(damping)
    y = _array(np, values, (model.n,))
    _finite(np, y)
    from scipy.sparse.linalg import lsmr
    from threadpoolctl import threadpool_limits
    try:
        with threadpool_limits(limits=1), np.errstate(over="raise", invalid="raise", divide="raise"):
            output = lsmr(model.operator, model.root_weights * y, damp=math.sqrt(damping),
                          atol=1e-12, btol=1e-12, conlim=1e8, maxiter=2000,
                          show=False, x0=None)
            c = np.asarray(output[0], dtype=np.float64)
            c.flags.writeable = False
            if not all(math.isfinite(float(t)) and t >= 0 for t in output[3:]):
                raise SurveyError("nonconverged", "fit")
            diagnostics = check_stationarity(model, y, damping, c, int(output[1]), float(output[6]))
    except (FloatingPointError, OverflowError, np.linalg.LinAlgError):
        raise SurveyError("nonconverged", "fit") from None
    coefficients = c / model.scales
    _finite(np, coefficients)
    coefficients.flags.writeable = False
    return dict(coefficients=coefficients, scaled_coefficients=c, **diagnostics,
                istop=int(output[1]), iterations=int(output[2]),
                objective_unit="dimensionless" if model.weighted else "nT^2",
                operator_forward_calls=model.forward_calls,
                operator_adjoint_calls=model.adjoint_calls)
