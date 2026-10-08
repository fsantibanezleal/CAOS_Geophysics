"""Original-noise, source-owned IRLS partition with the approved corrector.

The public boundary accepts physical request DTOs only. Native construction,
fixed Sparse weights, original noise actions and lifetime are owned here.
This prospective cpu3 epoch does not upgrade historical plain/cpu2 results.
"""
import hashlib
from pathlib import Path
from time import monotonic

import numpy as np

import gravity_original_optimizer as original
import gravity_irls_corrected as corrected


RUNTIME_EPOCH = 'm02-survey-irls-cpu-3'
POLICY = 'safeguarded-irls-interior-threepair-original-noise-reduced-1'
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def source_inventory():
    sources = original.source_inventory()
    sources.update(corrected._SOURCES)
    sources[Path(__file__).name] = SOURCE_SHA256
    return sources


def allocation_plan(n, m, a, covariance):
    base = original.allocation_plan(n, m, a, covariance)
    extra = dict(retained_native_stages=21*sum(base['retained_audits'].values()),
        auxiliary_proposals=63*(20*(8*a+2048)+8*12*a+32768),
        sparse_stage_records=21*(8*8*a+32768))
    admitted = base['admitted_bytes']+sum(extra.values())
    if admitted > 2*1024**3:
        raise ValueError('original IRLS: simultaneous22 native ledgers exceed original2GiB')
    value = dict(base, admitted_bytes=admitted, irls_retained=extra,
        partition_epoch=RUNTIME_EPOCH, auxiliary_CG_calls=126, anchors=63)
    value.pop('allocation_plan_sha256')
    value['allocation_plan_sha256'] = original.physics.survey._digest(value)
    return value


class GravityIRLSPartition:
    """Closed original physical constructor; no caller native objects/actions."""
    def __init__(self, request, observations, noise, prior, rows, beta_candidate, *,
                 observation_rows=None, deadline):
        p = original.physics
        p.survey._native_metadata(dict(request=request, observations=observations,
            noise=noise, prior=prior, rows=rows, beta_candidate=beta_candidate,
            observation_rows=observation_rows))
        if type(deadline) is not float or not np.isfinite(deadline):
            raise ValueError('original IRLS: finite original absolute clock')
        self.started = monotonic()
        self.deadline = min(deadline, self.started+120.)
        p.metric._time(self.deadline)
        p.survey._keys(noise, ('kind', 'values'), 'original IRLS noise')
        p.survey._enum(noise['kind'], ('diagonal_sd', 'full_covariance'), 'noise.kind')
        self.allocation = allocation_plan(len(request['stations']['receivers_m']),
            len(rows), len(prior['start_kg_m3']), noise['kind'] == 'full_covariance')
        self.problem = p._build_problem(request, observations, noise, prior, rows,
            beta_candidate, observation_rows=observation_rows)
        self.prior = p.survey._snapshot(prior)
        self.noise = p.survey._snapshot(noise)
        self.positions = p.survey._readonly(rows if observation_rows is None else
            np.searchsorted(observation_rows, rows))
        self.inventory = source_inventory()
        self.base_hash = corrected._problem_hash(self.problem, self.prior, {})
        self.closed = False
        self.initial_evidence = None

    def check(self):
        if self.closed:
            raise ValueError('original IRLS: disposed partition')
        original.physics.metric._time(self.deadline)
        if (self.inventory != source_inventory() or self.base_hash !=
                corrected._problem_hash(self.problem, self.prior, {})):
            raise ValueError('original IRLS: source/physical base drift')

    def _adapter(self, problem, q, index, stage=None):
        self.check()
        prior = dict(self.prior, start_kg_m3=np.ascontiguousarray(q*1000.))
        adapter = original._Objective(problem, prior, self.noise, self.positions,
            self.inventory, self.allocation)
        if stage is not None:
            # Native Sparse is never granted the ordinary-L2 zero-row allowance.
            if adapter.zero_row_terms:
                raise ValueError('unsupported_sparse_empty_face')
            adapter.identity_value['stage_index'] = index
            adapter.identity_value['objective_sha256'] = original.owned.digest((
                adapter.identity_value['objective_sha256'], stage['epsilon'],
                stage['objective_sha256'], stage['policy_sha256']))
        # Rebind after the exact native stage identity is installed.
        adapter.source_digest = original.accuracy._source_digest(adapter.quadratic_operands(q))
        return adapter

    def initialize(self):
        self.check()
        q = self.prior['start_kg_m3']/1000.
        adapter = self._adapter(self.problem, q, 0)
        started = monotonic()
        raw, _, _ = original._solve_adapter(adapter, self.deadline, 200)
        self.initial_evidence = raw
        trace = dict(raw['trace'])
        trace.pop('models_q')
        trace['models_kg_m3'] = original.physics.survey._readonly(raw['trace']['models_q']*1000.)
        prediction = None if raw['q'] is None else self.problem['simulation'].dpred(raw['q'])+self.problem['background']
        result = {k:raw[k] for k in ('status', 'reason', 'phi_d', 'phi_m',
            'phi_engine', 'kkt_normalized', 'iterations')}
        result.update(model_kg_m3=None if raw['q'] is None else raw['q']*1000.,
            beta_candidate=self.problem['beta_candidate'], beta_engine=float(self.problem['beta_engine']),
            fit_rows=self.problem['rows'], predicted_mgal=prediction,
            residual_observed_minus_predicted_mgal=None if prediction is None else self.problem['observations']-prediction,
            wrms=None if raw['phi_d'] is None else float(np.sqrt(raw['phi_d']/len(self.problem['rows']))),
            trace=trace, wall_seconds=monotonic()-started,
            failed_trial=None if raw['status'] == 'converged' else
                dict(iteration=raw['iterations'], reason=raw['reason']))
        return result

    def solve_stage(self, q, policy, index, initial, remaining_steps):
        self.check()
        stage = corrected._stage(self.problem, q, policy, index, initial)
        adapter = self._adapter(stage['problem'], q, index, stage)
        result, _, _ = original._solve_adapter(adapter, self.deadline, remaining_steps)
        return result

    def close(self):
        self.closed = True
        self.initial_evidence = None


def solve_partition(request, observations, noise, prior, rows, beta_candidate, *,
                    policy, observation_rows=None, deadline):
    """One original partition, same200 accepted/201states/120s, no hooks."""
    owner = GravityIRLSPartition(request, observations, noise, prior, rows,
        beta_candidate, observation_rows=observation_rows, deadline=deadline)
    try:
        return corrected._solve_partition(owner.problem, owner.prior, policy,
            owner.deadline, original_owner=owner)
    finally:
        owner.close()
