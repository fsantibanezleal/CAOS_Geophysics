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
import os
import stat
import struct
import sqlite3
import json
import re
from decimal import Decimal
import tempfile
from contextlib import contextmanager


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
    def __init__(self, xyz, sources, sigma_nT=None, *, chunk_rows=4096, chunk_sources=128, job_handle=None):
        _count(chunk_rows, 1, 4096)
        _count(chunk_sources, 1, 128)
        if job_handle is not None:
            from magnetic_line_survey_runtime import require_job
            require_job(job_handle)
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
        if (n > 128 or m > 32) and job_handle is None:
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


def global_operator(xyz, sources, sigma_nT=None, *, chunk_rows=4096, chunk_sources=128, job_handle=None):
    return GlobalOperator(xyz, sources, sigma_nT, chunk_rows=chunk_rows,
                          chunk_sources=chunk_sources, job_handle=job_handle)


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
            # Keep the unchanged 14-key algebra return; the owner adapter can
            # obtain real recurrence estimates, not invent zero receipt fields.
            model.solver_estimates = dict(zip(('normr_estimate', 'normar_estimate',
                'norma_estimate', 'conda_estimate', 'normx_estimate'), map(float, output[3:])))
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


# No numerical imports in this custody/intake section. Fixed ordinary contract
# reads are trusted repository source, not source bytes supplied by the caller.
def _contract():
    try:
        fixed = Path(__file__).resolve().with_name('magnetic_line_contract.py')
        if sha256(fixed.read_bytes()).hexdigest() != '33720f8510a273292c45b7554010b90886b707a086168ff5c001ec6ca2e78645':
            raise SurveyError('custody_mismatch', 'ingest')
        loaded = import_module('magnetic_line_contract')
        if Path(loaded.__file__).resolve(strict=True) != fixed:
            raise SurveyError('custody_mismatch', 'ingest')
        return loaded
    except (OSError, ImportError, AttributeError, TypeError, ValueError):
        raise SurveyError('custody_mismatch', 'ingest') from None


def _closed(value, keys, stage='ingest'):
    if type(value) is not dict or set(value) != set(keys.split()):
        raise SurveyError('invalid_contract', stage)
    return value


def _plain_path(value, *, directory=False):
    # Caller paths are local entry arguments only, never manifest names.
    if type(value) not in (str, type(Path())):
        raise SurveyError('invalid_contract', 'ingest')
    path = Path(os.path.abspath(value))
    for candidate in (path, *path.parents):
        s = candidate.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 1024:
            raise SurveyError('custody_mismatch', 'ingest')
    s = path.stat()
    if directory:
        if not stat.S_ISDIR(s.st_mode):
            raise SurveyError('custody_mismatch', 'ingest')
    elif not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
        raise SurveyError('custody_mismatch', 'ingest')
    return path


def _file_key(s):
    # Windows path.stat and handle fstat expose different historical ctime
    # semantics. File ID/volume/length/last-write/link-count agree across APIs;
    # ctime is additionally compared within the same handle API below.
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_nlink


def _write_member(root, name, data):
    if type(name) is not str or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', name):
        raise SurveyError('invalid_contract', 'export')
    with (root / name).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return dict(name=name, bytes=len(data), sha256=sha256(data).hexdigest())


_GEOMETRY_TYPES = {
    'row_id': ('ascii64', 'identity', 64), 'line_index': ('uint32', 'identity', 4),
    'sensor_index': ('uint8', 'identity', 1), 'ordinal': ('uint64', 'identity', 8),
    'utc': ('ascii30', 'UTC', 30), 'easting': ('float64', 'm', 8),
    'northing': ('float64', 'm', 8), 'upward': ('float64', 'm', 8),
    'terrain_upward': ('float64', 'm', 8), 'clearance': ('float64', 'm', 8),
    'heading': ('float64', 'degree', 8), 'missing_mask': ('uint32', 'identity', 4)}
_FORMATS = {'float64': '<d', 'uint64': '<Q', 'uint32': '<I', 'uint8': '<B'}
_MISSING_BITS = {'utc': 0, 'upward': 1, 'terrain_upward': 2, 'clearance': 3, 'heading': 6}


class _ChunkWriter:
    def __init__(self, root, identifier, *, role=None, row_schema=None):
        self.root, self.identifier, self.role, self.row_schema = root, identifier, role, row_schema
        self.prefix = 'array' if role else 'table'
        self.entries, self.pages, self.buffer = [], [], bytearray()
        self.rows = self.chunk_first = self.page_first = 0
        self.chunk_sequence = 0
        self.content = sha256()

    def append(self, payload, identity_payload=None):
        self.buffer.extend(payload)
        self.content.update(payload if identity_payload is None else identity_payload)
        self.rows += 1
        if self.rows - self.chunk_first == 4096:
            self.flush()

    def flush(self):
        if not self.buffer:
            return
        name = f'{self.prefix}-{self.identifier}-{self.chunk_sequence:08d}.' + ('bin' if self.role else 'jsonl')
        if len(self.buffer) > 8388608:
            raise SurveyError('resource_refused', 'ingest')
        member = _write_member(self.root, name, self.buffer)
        self.entries.append(dict(sequence=self.chunk_sequence, first_row=self.chunk_first,
                                 rows=self.rows-self.chunk_first, **member))
        self.chunk_sequence += 1
        self.chunk_first = self.rows
        self.buffer.clear()
        if len(self.entries) == 2048:
            self._page()

    def _page(self):
        if not self.entries:
            return
        sequence = len(self.pages)
        value = dict(schema='magnetic-line-manifest-page/1', owner_id=self.identifier,
                     sequence=sequence, entries=self.entries)
        encoded = _contract().canonical_bytes(value)
        if len(encoded) > 4194304 or sequence >= 512:
            raise SurveyError('resource_refused', 'ingest')
        member = _write_member(self.root, f'{self.prefix}-{self.identifier}-page-{sequence:06d}.json', encoded)
        self.pages.append(dict(sequence=sequence, first_row=self.page_first,
                               rows=self.rows-self.page_first, file=member))
        self.page_first = self.rows
        self.entries = []

    def finish(self, ordered_ids_sha256=None):
        self.flush()
        self._page()
        if self.role:
            dtype, unit, _ = _GEOMETRY_TYPES[self.role]
            value = dict(schema='magnetic-line-array-manifest/1', array_id=self.identifier,
                         shape=[self.rows], dtype=dtype, unit=unit, pages=self.pages,
                         content_sha256=self.content.hexdigest())
        else:
            value = dict(schema='magnetic-line-table-manifest/1', table_id=self.identifier,
                         row_schema=self.row_schema, rows=self.rows, pages=self.pages,
                         content_sha256=self.content.hexdigest())
        member = _write_member(self.root, f'{self.prefix}-{self.identifier}.json', _contract().canonical_bytes(value))
        if self.role:
            return dict(array_id=self.identifier, role=self.role, shape=[self.rows],
                        dtype=dtype, unit=unit, chunk_rows=4096, manifest=member,
                        ordered_ids_sha256=ordered_ids_sha256,
                        mask_array_id='missing_mask' if self.role in _MISSING_BITS else None)
        return dict(table_id=self.identifier, row_schema=self.row_schema,
                    rows=self.rows, manifest=member)


def _binary(role, value):
    dtype, _, width = _GEOMETRY_TYPES[role]
    if dtype.startswith('ascii'):
        encoded = (value or '').encode('ascii')
        if len(encoded) > width or b'\0' in encoded:
            raise SurveyError('invalid_contract', 'ingest')
        return encoded.ljust(width, b'\0')
    return struct.pack(_FORMATS[dtype], 0 if value is None else value)


def _geometry_record(tokens, contract):
    if len(tokens) != 14 or any('"' in s or '\x00' in s for s in tokens):
        raise SurveyError('invalid_contract', 'ingest')
    for i in (0, 1, 3):
        if not contract.ID_PATTERN.fullmatch(tokens[i]):
            raise SurveyError('invalid_contract', 'ingest')
    if tokens[2] not in ('flight', 'tie', 'reflight') or \
       not re.fullmatch(r'[0-9]{1,19}', tokens[4]) or int(tokens[4]) > 2**63-1:
        raise SurveyError('invalid_contract', 'ingest')
    if len(tokens[5]) > 30:
        raise SurveyError('invalid_contract', 'ingest')
    if tokens[5]:
        contract.utc_key(tokens[5])
    for s in tokens[6:]:
        if len(s) > 128 or not s.isascii() or any(c.isspace() for c in s):
            raise SurveyError('resource_refused', 'ingest')
    record = dict(row_id=tokens[0], line_id=tokens[1], line_kind=tokens[2],
                  sensor_id=tokens[3], ordinal=int(tokens[4]), utc=tokens[5] or None)
    for key, i in [('easting', 6), ('northing', 7), ('upward', 8),
                   ('terrain_upward', 9), ('clearance', 10), ('heading', 13)]:
        token = tokens[i]
        if not token:
            if key in ('easting', 'northing'):
                raise SurveyError('invalid_contract', 'ingest')
            record[key] = None
        else:
            if not contract.CSV_NUMBER.fullmatch(token):
                raise SurveyError('invalid_contract', 'ingest')
            value = float(token)
            if not math.isfinite(value) or (value == 0 and Decimal(token) != 0):
                raise SurveyError('invalid_contract', 'ingest')
            record[key] = 0.0 if value == 0 else value
    # Deliberately do NOT decode tokens11/12, including their missingness.
    record['missing_mask'] = sum(1 << bit for key, bit in _MISSING_BITS.items() if record[key] is None)
    return record


def _definitions(value, name, key, limit, contract):
    if type(value) is not list or not 1 <= len(value) <= limit:
        raise SurveyError('invalid_contract', 'ingest')
    decoded = [contract._type(x, name, name, 0) for x in value]
    ids = [x[key] for x in decoded]
    if ids != sorted(set(ids)):
        raise SurveyError('invalid_contract', 'ingest')
    return decoded


def _original_identity(value, contract):
    _closed(value, 'csv_sha256 csv_bytes source_url provider_identifier retrieval_utc')
    contract._type(value['csv_sha256'], 'Hash', 'original', 0)
    _count(value['csv_bytes'], 1, 4294967296)
    for key in ('source_url', 'provider_identifier'):
        contract._type(value[key], '?Text', 'original', 0)
    contract._type(value['retrieval_utc'], '?UTC', 'original', 0)


@contextmanager
def _identity_index(parent):
    # Verification scratch is a separately fresh owned directory. No caller
    # arrays, user databases or immutable artifact directory are modified.
    from magnetic_line_survey_io import external_path
    parent = external_path(parent)
    with tempfile.TemporaryDirectory(prefix='m03-verify-', dir=parent) as temporary:
        db = sqlite3.connect(Path(temporary) / 'identity.sqlite3')
        try:
            db.execute('PRAGMA cache_size=-8192')
            db.execute('PRAGMA temp_store=FILE')
            db.execute("PRAGMA temp_store_directory='"+temporary.replace("'", "''")+"'")
            db.execute('PRAGMA max_page_count=8388608')
            db.execute('CREATE TABLE identities (id TEXT PRIMARY KEY)')
            db.execute('CREATE TABLE ordinals (line INTEGER, sensor INTEGER, ordinal INTEGER, PRIMARY KEY(line,sensor))')
            yield db
        finally:
            db.close()


def inspect_geometry(csv_path, output_root, original, rights, line_definitions, sensor_definitions):
    """All original rows, geometry only, immutable chunks, no field admission."""
    contract = _contract()
    try:
        _original_identity(original, contract)
        rights = contract._type(rights, 'Rights', 'rights', 0)
        if rights['decision'] != 'allowed' or rights['private_processing'] != 'allowed':
            raise SurveyError('metadata_ineligible', 'ingest')
        lines = _definitions(line_definitions, 'LineDefinition', 'line_id', 65536, contract)
        sensors = _definitions(sensor_definitions, 'SensorDefinition', 'sensor_id', 4, contract)
        line_map = {x['line_id']: (i, x['kind']) for i, x in enumerate(lines)}
        sensor_map = {x['sensor_id']: i for i, x in enumerate(sensors)}
        from magnetic_line_survey_io import external_path
        source = external_path(csv_path, directory=False)
        if type(output_root) not in (str, type(Path())):
            raise SurveyError('invalid_contract', 'ingest')
        root = external_path(output_root)
        root.mkdir()  # Fresh absent destination only, no overwrite/retry adoption.
        index = root / 'geometry-index.sqlite3'
        db = sqlite3.connect(index)
        try:
            db.execute('PRAGMA cache_size=-8192')
            db.execute('PRAGMA temp_store=FILE')
            db.execute("PRAGMA temp_store_directory='"+str(root).replace("'", "''")+"'")
            db.execute('PRAGMA max_page_count=8388608')
            db.execute('CREATE TABLE row_geometry (pos INTEGER PRIMARY KEY, id TEXT UNIQUE, line TEXT, sensor TEXT, ordinal INTEGER, data BLOB)')
            db.execute('CREATE INDEX line_ordinal ON row_geometry(line,sensor,ordinal)')
            digest, geometry_digest, ids_digest = sha256(), sha256(), sha256()
            count = total = 0
            with source.open('rb') as stream:
                before = os.fstat(stream.fileno())
                if _file_key(before) != _file_key(source.stat()) or before.st_nlink != 1:
                    raise SurveyError('custody_mismatch', 'ingest')
                while True:
                    raw = stream.readline(min(4097, 4294967296-total+1, original['csv_bytes']-total+1))
                    if not raw:
                        break
                    total += len(raw)
                    if total > 4294967296 or len(raw) > 4096:
                        raise SurveyError('resource_refused', 'ingest')
                    if total > original['csv_bytes']:
                        raise SurveyError('custody_mismatch', 'ingest')
                    digest.update(raw)
                    text = raw.decode('utf-8-sig' if count == 0 and total == len(raw) else 'utf-8')
                    text = text[:-2] if text.endswith('\r\n') else text[:-1] if text.endswith('\n') else text
                    if '\r' in text or '\n' in text:
                        raise SurveyError('invalid_contract', 'ingest')
                    if count == 0 and total == len(raw):
                        if text != ','.join(contract.CSV_COLUMNS):
                            raise SurveyError('invalid_contract', 'ingest')
                        continue
                    if count >= ROW_LIMIT:
                        raise SurveyError('resource_refused', 'ingest')
                    record = _geometry_record(text.split(','), contract)
                    if record['line_id'] not in line_map or record['sensor_id'] not in sensor_map or \
                       line_map[record['line_id']][1] != record['line_kind']:
                        raise SurveyError('invalid_contract', 'ingest')
                    last = db.execute('SELECT MAX(ordinal) FROM row_geometry WHERE line=? AND sensor=?',
                                      (record['line_id'], record['sensor_id'])).fetchone()[0]
                    if last is not None and record['ordinal'] <= last:
                        raise SurveyError('invalid_contract', 'ingest')
                    encoded = contract.canonical_bytes(record)
                    db.execute('INSERT INTO row_geometry VALUES (?,?,?,?,?,?)',
                               (count, record['row_id'], record['line_id'], record['sensor_id'], record['ordinal'], encoded))
                    geometry_digest.update(struct.pack('<Q', len(encoded)) + encoded)
                    ids_digest.update(_binary('row_id', record['row_id']))
                    count += 1
                    if count % 4096 == 0:
                        db.commit()
                        if sum(p.stat().st_size for p in root.iterdir()) > SCRATCH_LIMIT:
                            raise SurveyError('resource_refused', 'ingest')
                after = os.fstat(stream.fileno())
            if _file_key(before) != _file_key(after) or before.st_ctime_ns != after.st_ctime_ns or \
               _file_key(after) != _file_key(source.stat()) or \
               total != original['csv_bytes'] or digest.hexdigest() != original['csv_sha256']:
                raise SurveyError('custody_mismatch', 'ingest')
            if not count:
                raise SurveyError('invalid_contract', 'ingest')
            if [x[0] for x in db.execute('SELECT DISTINCT line FROM row_geometry ORDER BY line')] != list(line_map) or \
               [x[0] for x in db.execute('SELECT DISTINCT sensor FROM row_geometry ORDER BY sensor')] != list(sensor_map):
                raise SurveyError('invalid_contract', 'ingest')
            writers = {role: _ChunkWriter(root, role, role=role) for role in _GEOMETRY_TYPES}
            for (encoded,) in db.execute('SELECT data FROM row_geometry ORDER BY pos'):
                record = json.loads(encoded)
                record['line_index'] = line_map[record['line_id']][0]
                record['sensor_index'] = sensor_map[record['sensor_id']]
                for role, writer in writers.items():
                    writer.append(_binary(role, record[role]))
            arrays = [writer.finish(ids_digest.hexdigest()) for writer in writers.values()]
        finally:
            db.close()
        # Only this producer-created ephemeral geometry index is removed;
        # all successful immutable artifacts and originals remain untouched.
        index.unlink()
        tables = []
        for identifier, name, values in [('lines', 'line_definition', lines), ('sensors', 'sensor_definition', sensors)]:
            writer = _ChunkWriter(root, identifier, row_schema=name)
            for row in values:
                encoded = contract.canonical_bytes(row)
                writer.append(encoded+b'\n', struct.pack('<Q', len(encoded))+encoded)
            tables.append(writer.finish())
        result = dict(schema='m03-geometry-inspection/1', original=original,
                      rows=count, lines=len(lines), sensors=len(sensors), arrays=arrays,
                      dictionaries=tables, geometry_sha256=geometry_digest.hexdigest(),
                      value_access='not_opened')
        _write_member(root, 'inspection.json', contract.canonical_bytes(result))
        return verify_geometry_inspection(root, result)
    except SurveyError:
        raise
    except contract.MagneticContractError:
        raise SurveyError('invalid_contract', 'ingest') from None
    except sqlite3.IntegrityError:
        raise SurveyError('invalid_contract', 'ingest') from None
    except (OSError, sqlite3.Error):
        raise SurveyError('io_failed', 'ingest') from None
    except (ValueError, UnicodeError, OverflowError):
        raise SurveyError('invalid_contract', 'ingest') from None


def _verified_member(root, identity, known, limit=4194304):
    _closed(identity, 'name bytes sha256', 'replay')
    name = identity['name']
    if type(name) is not str or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', name) or name in known or \
       type(identity['bytes']) is not int or not 0 < identity['bytes'] <= limit:
        raise SurveyError('custody_mismatch', 'replay')
    _contract()._type(identity['sha256'], 'Hash', 'member', 0)
    path = _plain_path(root / name)
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        data = stream.read(min(limit, identity['bytes'])+1)
        after = os.fstat(stream.fileno())
    if _file_key(before) != _file_key(after) or before.st_ctime_ns != after.st_ctime_ns or \
       _file_key(after) != _file_key(path.stat()) or \
       len(data) != identity['bytes'] or sha256(data).hexdigest() != identity['sha256']:
        raise SurveyError('custody_mismatch', 'replay')
    known.add(name)
    return data


def _manifest_chunks(root, ref, known, array):
    contract = _contract()
    prefix = 'array' if array else 'table'
    identifier = ref['array_id' if array else 'table_id']
    if type(identifier) is not str or not re.fullmatch(r'[A-Za-z0-9_.-]{1,32}', identifier):
        raise SurveyError('custody_mismatch', 'replay')
    if ref['manifest']['name'] != f'{prefix}-{identifier}.json':
        raise SurveyError('custody_mismatch', 'replay')
    data = _verified_member(root, ref['manifest'], known, 2097152)
    value = contract.strict_json(data)
    keys = 'schema array_id shape dtype unit pages content_sha256' if array else 'schema table_id row_schema rows pages content_sha256'
    _closed(value, keys, 'replay')
    rows = ref['shape'][0] if array else ref['rows']
    if array and (type(value['shape']) is not list or len(value['shape']) != 1 or type(value['shape'][0]) is not int):
        raise SurveyError('custody_mismatch', 'replay')
    if not array and type(value['rows']) is not int:
        raise SurveyError('custody_mismatch', 'replay')
    contract._type(value['content_sha256'], 'Hash', 'content', 0)
    if value['schema'] != f'magnetic-line-{prefix}-manifest/1' or \
       any(value[k] != ref[k] for k in (('array_id', 'shape', 'dtype', 'unit') if array else ('table_id', 'row_schema', 'rows'))) or \
       type(value['pages']) is not list or not 1 <= len(value['pages']) <= 512:
        raise SurveyError('custody_mismatch', 'replay')
    digest, position, sequence = sha256(), 0, 0
    for number, page in enumerate(value['pages']):
        _closed(page, 'sequence first_row rows file', 'replay')
        if type(page['sequence']) is not int or page['sequence'] != number or \
           type(page['first_row']) is not int or page['first_row'] != position or type(page['rows']) is not int or \
           page['file']['name'] != f'{prefix}-{identifier}-page-{number:06d}.json':
            raise SurveyError('custody_mismatch', 'replay')
        body = contract.strict_json(_verified_member(root, page['file'], known))
        _closed(body, 'schema owner_id sequence entries', 'replay')
        if body['schema'] != 'magnetic-line-manifest-page/1' or body['owner_id'] != identifier or \
           type(body['sequence']) is not int or body['sequence'] != number or \
           type(body['entries']) is not list or not 1 <= len(body['entries']) <= 2048:
            raise SurveyError('custody_mismatch', 'replay')
        start = position
        for entry in body['entries']:
            _closed(entry, 'sequence first_row rows bytes sha256 name', 'replay')
            count = entry['rows']
            if type(count) is not int or not 1 <= count <= 4096 or type(entry['sequence']) is not int or \
               entry['sequence'] != sequence or type(entry['first_row']) is not int or entry['first_row'] != position or \
               entry['name'] != f'{prefix}-{identifier}-{sequence:08d}.' + ('bin' if array else 'jsonl'):
                raise SurveyError('custody_mismatch', 'replay')
            payload = _verified_member(root, {k: entry[k] for k in ('name', 'bytes', 'sha256')}, known, 8388608)
            if array:
                if len(payload) != count * _GEOMETRY_TYPES[ref['role']][2]:
                    raise SurveyError('custody_mismatch', 'replay')
                digest.update(payload)
                yield payload
            else:
                lines = payload.splitlines()
                if len(lines) != count or not payload.endswith(b'\n'):
                    raise SurveyError('custody_mismatch', 'replay')
                decoded = []
                for encoded in lines:
                    row = contract.strict_json(encoded)
                    if contract.canonical_bytes(row) != encoded:
                        raise SurveyError('custody_mismatch', 'replay')
                    digest.update(struct.pack('<Q', len(encoded))+encoded)
                    decoded.append(row)
                yield decoded
            position += count
            sequence += 1
            if position > rows:
                raise SurveyError('custody_mismatch', 'replay')
        if page['rows'] != position-start:
            raise SurveyError('custody_mismatch', 'replay')
    if position != rows or digest.hexdigest() != value['content_sha256']:
        raise SurveyError('custody_mismatch', 'replay')


def verify_geometry_inspection(output_root, receipt):
    """Verify byte/semantic custody, never substitute for scientific replay."""
    contract = _contract()
    try:
        from magnetic_line_survey_io import external_path
        root = external_path(output_root)
        _closed(receipt, 'schema original rows lines sensors arrays dictionaries geometry_sha256 value_access', 'replay')
        if receipt['schema'] != 'm03-geometry-inspection/1' or receipt['value_access'] != 'not_opened':
            raise SurveyError('custody_mismatch', 'replay')
        n = _count(receipt['rows'], 1, ROW_LIMIT)
        _count(receipt['lines'], 1, 65536)
        _count(receipt['sensors'], 1, 4)
        _original_identity(receipt['original'], contract)
        contract._type(receipt['geometry_sha256'], 'Hash', 'geometry', 0)
        if type(receipt['arrays']) is not list or len(receipt['arrays']) != len(_GEOMETRY_TYPES) or \
           type(receipt['dictionaries']) is not list or len(receipt['dictionaries']) != 2:
            raise SurveyError('custody_mismatch', 'replay')
        known = {'inspection.json'}
        saved = _plain_path(root / 'inspection.json')
        data = contract.read_bounded(saved, 2097152)
        if contract.strict_json(data) != receipt:
            raise SurveyError('custody_mismatch', 'replay')
        definitions = []
        for ref, name, count_key, key, limit in zip(receipt['dictionaries'], ['LineDefinition', 'SensorDefinition'],
              ['lines', 'sensors'], ['line_id', 'sensor_id'], [65536, 4]):
            _closed(ref, 'table_id row_schema rows manifest', 'replay')
            if ref['row_schema'] != ('line_definition' if name == 'LineDefinition' else 'sensor_definition') or \
               type(ref['rows']) is not int or ref['rows'] != receipt[count_key] or not 1 <= ref['rows'] <= limit:
                raise SurveyError('custody_mismatch', 'replay')
            table = []
            for rows in _manifest_chunks(root, ref, known, False):
                table.extend(rows)
            definitions.append(_definitions(table, name, key, limit, contract))
        refs = {}
        for ref in receipt['arrays']:
            _closed(ref, 'array_id role shape dtype unit chunk_rows manifest ordered_ids_sha256 mask_array_id', 'replay')
            role = ref['role']
            if type(role) is not str or role not in _GEOMETRY_TYPES or role in refs or ref['array_id'] != role:
                raise SurveyError('custody_mismatch', 'replay')
            dtype, unit, _ = _GEOMETRY_TYPES[role]
            if type(ref['shape']) is not list or len(ref['shape']) != 1 or type(ref['shape'][0]) is not int or \
               ref['shape'] != [n] or ref['dtype'] != dtype or ref['unit'] != unit or \
               type(ref['chunk_rows']) is not int or ref['chunk_rows'] != 4096 or \
               ref['mask_array_id'] != ('missing_mask' if role in _MISSING_BITS else None):
                raise SurveyError('custody_mismatch', 'replay')
            contract._type(ref['ordered_ids_sha256'], 'Hash', 'array', 0)
            refs[role] = ref
        iterators = {role: _manifest_chunks(root, refs[role], known, True) for role in _GEOMETRY_TYPES}
        geometry_hash, ids_hash = sha256(), sha256()
        seen_lines, seen_sensors = set(), set()
        position = 0
        with _identity_index(root.parent) as identity_index:
            while position < n:
                payloads = {role: next(iterator) for role, iterator in iterators.items()}
                rows = min(4096, n-position)
                if any(len(payloads[k]) != rows*_GEOMETRY_TYPES[k][2] for k in payloads):
                    raise SurveyError('custody_mismatch', 'replay')
                ids_hash.update(payloads['row_id'])
                for i in range(rows):
                    decoded = {}
                    for role, payload in payloads.items():
                        dtype, _, width = _GEOMETRY_TYPES[role]
                        cell = payload[i*width:(i+1)*width]
                        if dtype.startswith('ascii'):
                            token = cell.rstrip(b'\0')
                            if b'\0' in token:
                                raise SurveyError('custody_mismatch', 'replay')
                            value = token.decode('ascii')
                        else:
                            value = struct.unpack(_FORMATS[dtype], cell)[0]
                            if dtype == 'float64' and not math.isfinite(value):
                                raise SurveyError('custody_mismatch', 'replay')
                        decoded[role] = value
                    mask = decoded['missing_mask']
                    if mask & ~79 or decoded['line_index'] >= len(definitions[0]) or decoded['sensor_index'] >= len(definitions[1]):
                        raise SurveyError('custody_mismatch', 'replay')
                    for role, bit in _MISSING_BITS.items():
                        if mask & (1 << bit):
                            if _binary(role, decoded[role]) != b'\0'*_GEOMETRY_TYPES[role][2]:
                                raise SurveyError('custody_mismatch', 'replay')
                            decoded[role] = None
                        elif role == 'utc':
                            contract.utc_key(decoded[role])
                    key = (decoded.pop('line_index'), decoded.pop('sensor_index'))
                    line = definitions[0][key[0]]
                    sensor = definitions[1][key[1]]
                    identity_index.execute('INSERT INTO identities VALUES (?)', (decoded['row_id'],))
                    prior = identity_index.execute('SELECT ordinal FROM ordinals WHERE line=? AND sensor=?', key).fetchone()
                    if prior is not None and decoded['ordinal'] <= prior[0]:
                        raise SurveyError('custody_mismatch', 'replay')
                    identity_index.execute('INSERT OR REPLACE INTO ordinals VALUES (?,?,?)', (*key, decoded['ordinal']))
                    seen_lines.add(line['line_id'])
                    seen_sensors.add(sensor['sensor_id'])
                    decoded.update(line_id=line['line_id'], line_kind=line['kind'], sensor_id=sensor['sensor_id'])
                    if not contract.ID_PATTERN.fullmatch(decoded['row_id']) or decoded['ordinal'] > 2**63-1:
                        raise SurveyError('custody_mismatch', 'replay')
                    encoded = contract.canonical_bytes(decoded)
                    geometry_hash.update(struct.pack('<Q', len(encoded))+encoded)
                position += rows
                identity_index.commit()
        for iterator in iterators.values():
            if next(iterator, None) is not None:
                raise SurveyError('custody_mismatch', 'replay')
        if geometry_hash.hexdigest() != receipt['geometry_sha256'] or \
           any(ref['ordered_ids_sha256'] != ids_hash.hexdigest() for ref in refs.values()) or \
           len(seen_lines) != receipt['lines'] or len(seen_sensors) != receipt['sensors'] or \
           {p.name for p in root.iterdir()} != known:
            raise SurveyError('custody_mismatch', 'replay')
        return receipt
    except SurveyError:
        raise
    except (contract.MagneticContractError, KeyError, TypeError, ValueError, UnicodeError,
            StopIteration, OSError, struct.error, sqlite3.Error):
        raise SurveyError('custody_mismatch', 'replay') from None
