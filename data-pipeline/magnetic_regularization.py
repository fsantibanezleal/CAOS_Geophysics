"""M04 volume-normalized first-order susceptibility regularization.

The SimPEG objective is checked against an explicit active-face graph. Faces
touching inactive cells and exterior faces are excluded by the independent
graph, and the reference model participates in the smoothness residual.
"""

import numpy as np
from discretize import TensorMesh
from simpeg import maps
from simpeg.regularization import WeightedLeastSquares


MAX_FULL_CELLS = 4096
MAX_ACTIVE_CELLS = 2048
MAX_LENGTH_M = 1e5
ENGINE_EPOCH = "simpeg-0.25.2-discretize-0.12.0-magnetic-volume-faces-1"


class MagneticRegularizer:
    """Actual SimPEG WLS objective plus an independent active-face oracle."""

    def __init__(self, mesh, active_cells, reference_q, lengths_m):
        if type(mesh) is not TensorMesh or mesh.dim != 3:
            raise TypeError("mesh: expected a 3D discretize.TensorMesh")
        full = mesh.nC
        if type(full) is not int or not 1 <= full <= MAX_FULL_CELLS:
            raise ValueError("mesh: full-cell count outside 1..4096")
        if (type(active_cells) is not np.ndarray or active_cells.dtype != np.bool_
                or active_cells.ndim != 1 or active_cells.shape != (full,)):
            raise TypeError("active_cells: expected native bool full-mesh mask")
        active_count = int(np.count_nonzero(active_cells))
        if not 1 <= active_count <= min(full, MAX_ACTIVE_CELLS):
            raise ValueError("active_cells: active count outside 1..2048")
        if (type(reference_q) is not np.ndarray or reference_q.dtype != np.float64
                or reference_q.ndim != 1 or reference_q.shape != (active_count,)):
            raise TypeError("reference_q: expected native float64 active-cell vector")
        if (type(lengths_m) is not np.ndarray or lengths_m.dtype != np.float64
                or lengths_m.shape != (3,)):
            raise TypeError("lengths_m: expected native float64 ENU length vector")
        # All dimensions and products are admitted before numerical scans/copies.
        if (not np.isfinite(reference_q).all() or np.any((reference_q < 0.) | (reference_q > 10.))
                or not np.isfinite(lengths_m).all()
                or np.any(lengths_m <= 0.) or np.any(lengths_m > MAX_LENGTH_M)):
            raise ValueError("reference/lengths: finite bounded physical values required")
        self.mesh = mesh
        self.active_cells = active_cells.copy()
        self.active_indices = np.flatnonzero(self.active_cells).astype(np.int64)
        self.volumes = np.array(mesh.cell_volumes[self.active_cells], dtype=np.float64, copy=True)
        self.total_volume = float(np.sum(self.volumes, dtype=np.float64))
        if (not np.isfinite(self.volumes).all() or np.any(self.volumes <= 0.)
                or not np.isfinite(self.total_volume) or self.total_volume <= 0.):
            raise ValueError("mesh: active cell volumes must be finite and positive")
        self.reference_q = reference_q.copy()
        self.lengths_m = lengths_m.copy()
        self.reference_q.flags.writeable = False
        self.lengths_m.flags.writeable = False
        self.active_cells.flags.writeable = False
        self.active_indices.flags.writeable = False
        self.volumes.flags.writeable = False
        self._face_pairs = self._build_active_faces()
        self._quadratic = self._independent_quadratic()

        if (WeightedLeastSquares.__module__.split(".")[0] != "simpeg"
                or __import__("simpeg").__version__ != "0.25.2"
                or __import__("discretize").__version__ != "0.12.0"):
            raise RuntimeError("runtime: unreviewed SimPEG/discretize version")
        # SimPEG weights enter as a diagonal W. Supplying v_i/V gives the exact
        # target cell and face-volume quadrature after W.T @ W.
        self.simpeg = WeightedLeastSquares(
            mesh, active_cells=self.active_cells,
            alpha_s=1., alpha_x=float(lengths_m[0]**2),
            alpha_y=float(lengths_m[1]**2), alpha_z=float(lengths_m[2]**2),
            alpha_xx=0., alpha_yy=0., alpha_zz=0.,
            mapping=maps.IdentityMap(nP=active_count),
            reference_model=self.reference_q, reference_model_in_smooth=True,
            weights={"volume": self.volumes / self.total_volume},
        )

    @property
    def parameter_count(self):
        return len(self.active_indices)

    def _build_active_faces(self):
        shape = tuple(int(v) for v in self.mesh.shape_cells)
        full_to_active = np.full(self.mesh.nC, -1, dtype=np.int64)
        full_to_active[self.active_indices] = np.arange(self.parameter_count, dtype=np.int64)
        centres = np.asarray(self.mesh.cell_centers, dtype=np.float64)
        volumes = np.asarray(self.mesh.cell_volumes, dtype=np.float64)
        result = []
        strides = (1, shape[0], shape[0] * shape[1])
        for axis, stride in enumerate(strides):
            for left in range(self.mesh.nC):
                ijk = list(np.unravel_index(left, shape, order="F"))
                if ijk[axis] + 1 >= shape[axis]:
                    continue
                right = left + stride
                if not self.active_cells[left] or not self.active_cells[right]:
                    continue
                distance = float(centres[right, axis] - centres[left, axis])
                average_volume = float((volumes[left] + volumes[right]) / 2.)
                if not np.isfinite(distance) or distance <= 0. or not np.isfinite(average_volume):
                    raise ValueError("mesh: invalid active-face geometry")
                result.append((axis, int(full_to_active[left]), int(full_to_active[right]),
                               distance, average_volume / self.total_volume))
        return tuple(result)

    def _independent_quadratic(self):
        matrix = np.diag(self.volumes / self.total_volume)
        for axis, left, right, distance, weight in self._face_pairs:
            scale = self.lengths_m[axis] ** 2 * weight / distance**2
            matrix[left, left] += scale
            matrix[right, right] += scale
            matrix[left, right] -= scale
            matrix[right, left] -= scale
        return matrix

    def evaluate(self, q):
        if type(q) is not np.ndarray or q.dtype != np.float64 or q.shape != (self.parameter_count,):
            raise TypeError("q: expected native float64 active-cell vector")
        if not np.isfinite(q).all() or np.any((q < 0.) | (q > 10.)):
            raise ValueError("q: finite normalized susceptibility values in [0,10] required")
        delta = q - self.reference_q
        phi_independent = float(delta @ self._quadratic @ delta)
        gradient_independent = 2. * (self._quadratic @ delta)
        action = 2. * self._quadratic
        phi_simpeg = float(self.simpeg(q))
        gradient_simpeg = np.asarray(self.simpeg.deriv(q), dtype=np.float64)
        hessian_simpeg = self.simpeg.deriv2(q)
        if hasattr(hessian_simpeg, "toarray"):
            hessian_simpeg = hessian_simpeg.toarray()
        hessian_simpeg = np.asarray(hessian_simpeg, dtype=np.float64)
        if (not np.isfinite([phi_independent, phi_simpeg]).all()
                or not np.isfinite(gradient_simpeg).all()
                or not np.isfinite(hessian_simpeg).all()):
            raise FloatingPointError("regularization produced nonfinite values")
        hessian_simpeg = hessian_simpeg.copy(order="C")
        hessian_simpeg.flags.writeable = False

        def hessian_action(direction):
            if (type(direction) is not np.ndarray or direction.dtype != np.float64
                    or direction.shape != (self.parameter_count,)):
                raise TypeError("direction_q: expected native float64 active-cell vector")
            if not np.isfinite(direction).all():
                raise ValueError("direction_q: values must be finite")
            result = hessian_simpeg @ direction
            if not np.isfinite(result).all():
                raise FloatingPointError("regularization Hessian action is nonfinite")
            result.flags.writeable = False
            return result
        return {
            "phi": phi_simpeg,
            "gradient_q": gradient_simpeg,
            "hessian_action": hessian_action,
            "independent_phi": phi_independent,
            "independent_gradient_q": gradient_independent,
            "independent_hessian": action,
            "active_face_count_by_axis": tuple(
                sum(face[0] == axis for face in self._face_pairs) for axis in range(3)
            ),
            "unit": "dimensionless",
            "parameter_unit": "q=chi_si/0.01",
            "engine_epoch": ENGINE_EPOCH,
        }
