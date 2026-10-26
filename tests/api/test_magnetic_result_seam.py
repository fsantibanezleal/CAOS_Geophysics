"""Owner seam negatives, not a claim that routes/method admission are mounted."""

import copy
from types import SimpleNamespace

import pytest

from app.errors import ApiError
from app.magnetic_results import LOCAL_MAGNETIC_METHOD_ID, validate_owned_magnetic_result


def control():
    user = SimpleNamespace(id='owner-a')
    dataset = SimpleNamespace(id='dataset-a', owner_id='owner-a', project_id='project-a',
                              sha256='d'*64, raw_sha256='a'*64)
    job = SimpleNamespace(id='job-a', dataset_id='dataset-a', owner_id='owner-a', project_id='project-a',
                          state='succeeded', method_id=LOCAL_MAGNETIC_METHOD_ID, dataset_sha256='d'*64)
    binding = dict(job_id=job.id, dataset_id=dataset.id, source_id='source-a', generation_sha256='b'*64,
                   configuration_sha256='c'*64, original_sha256='a'*64)
    payload = dict(schema='magnetic-owner-result-view-1', binding=binding.copy(), lane='local_replay',
        online_admitted=False, claims=dict(full_method_accepted=False, field_source_verified=False,
                                          geology_truth_known=False, online_admitted=False))
    return payload, dict(user=user, job=job, dataset=dataset, expected_binding=binding)


def test_actual_seam_keeps_explicit_replay_only():
    payload, refs = control()
    assert validate_owned_magnetic_result(payload, **refs) is payload


@pytest.mark.parametrize('target,field,value', [
    ('job', 'owner_id', 'owner-b'), ('dataset', 'owner_id', 'owner-b'),
    ('job', 'project_id', 'other-project'), ('job', 'dataset_id', 'other-dataset'),
])
def test_cross_owner_project_dataset_non_disclosing(target, field, value):
    payload, refs = control()
    setattr(refs[target], field, value)
    with pytest.raises(ApiError) as error:
        validate_owned_magnetic_result(payload, **refs)
    assert error.value.status == 404


@pytest.mark.parametrize('state', ['queued', 'running', 'failed', 'cancelled', 'nonconverged', 'ineligible'])
def test_failed_or_pending_never_returns_projection(state):
    payload, refs = control()
    refs['job'].state = state
    with pytest.raises(ApiError) as error:
        validate_owned_magnetic_result(payload, **refs)
    assert error.value.status == 409


@pytest.mark.parametrize('field', ['job_id', 'dataset_id', 'source_id', 'generation_sha256', 'configuration_sha256', 'original_sha256'])
def test_changed_response_binding_is_not_selected_receipt(field):
    payload, refs = control()
    payload = copy.deepcopy(payload)
    payload['binding'][field] = 'changed'
    with pytest.raises(ApiError, match='binding'):
        validate_owned_magnetic_result(payload, **refs)


@pytest.mark.parametrize('claim', ['full_method_accepted', 'field_source_verified', 'geology_truth_known', 'online_admitted'])
def test_client_cannot_promote_a_scientific_claim(claim):
    payload, refs = control()
    payload['claims'][claim] = True
    with pytest.raises(ApiError, match='claim'):
        validate_owned_magnetic_result(payload, **refs)
