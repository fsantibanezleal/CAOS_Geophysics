"""Actual magnetic physical DTO bridge to the public original-noise solver.

This additive bridge requires the actual native MagneticObjective, never a
private optimizer/certificate replacement. Acquisition, likelihood sealing,
source authority and the original allocation plan remain the workflow owner's.
"""
import hashlib
from pathlib import Path

import numpy as np
import scipy.sparse as sp

import physical_original_optimizer as optimizer
import physical_original_quadratic as original
import physical_owned_spd as owned


SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class _MagneticDTO:
    def __init__(self, objective, source_components):
        from magnetic_optimizer_adapter import MagneticObjective
        if type(objective) is not MagneticObjective:
            raise TypeError('original magnetic bridge: actual native objective only')
        if (objective.operator.quantity not in ('secondary_enu_nT', 'linear_tmi_nT')
            or type(source_components) is not int
            or not 3*objective.operator.rows <= source_components <= 2048):
            raise ValueError('original magnetic bridge: original linear source COMPONENTS')
        self.native, self.source_components = objective, source_components

    def __getattr__(self, name):
        return getattr(self.native, name)

    def identity(self):
        return dict(self.native.identity(), runtime_epoch=optimizer.LINEAR_EPOCH)

    def metric_operands(self, q):
        o = self.native
        return owned.MetricOperands(owned.binding_for(self.identity(), q),
            self.source_components, o.observed.size, len(q), o.factor is not None,
            (o.beta*o.regularizer.vendor.deriv2(q)).tocsr().sorted_indices(),
            np.ascontiguousarray(o._state(q)[-1]))

    def quadratic_operands(self, q):
        o = self.native
        g, _, direction, _, quantity = o.operator.operand_snapshot()
        projection = direction if quantity == 'linear_tmi_nT' else None
        whitening = (original.OriginalWhitening('stored_lower_cholesky', o.factor, o.noise['values'])
            if o.factor is not None else original.OriginalWhitening('diagonal_sd', o.noise['values'].ravel()))
        terms = tuple(owned.QuadraticTerm(t['alpha'], sp.diags(t['weights'], format='csr'),
            t['derivative']) for t in o.regularizer.terms())
        return original.OriginalQuadraticOperands(owned.binding_for(self.identity(), q),
            self.source_components, g, projection, whitening, o.observed.ravel(),
            o.regularizer.reference, o.lower, o.upper, 1., o.beta, terms, g, projection)

    def magnetic_domain(self, q):
        _, background, direction, field_norm, quantity = self.native.operator.operand_snapshot()
        return optimizer.OriginalMagneticDomain(owned.binding_for(self.identity(), q),
            background, field_norm, direction, quantity)


def solve_magnetic_original(objective, start_q, *, source_components, budget, binding, terminal):
    """No new clock or step allowance; same native original physical solve."""
    dto = _MagneticDTO(objective, source_components)
    return optimizer.solve_bounded_linear(dto, objective.lower, objective.upper, start_q,
        budget=budget, binding=binding, terminal=terminal)
