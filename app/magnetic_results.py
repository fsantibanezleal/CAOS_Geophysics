"""Owned replay result seam; explicitly not installed in the service dispatcher.

Reuse existing authenticated owner/job/dataset records and checked result bytes.
The caller resolves its durable native receipt separately from the response.
No database migration, method allow-list, hosted worker or auth is added here.
"""

from app.errors import ApiError

LOCAL_MAGNETIC_METHOD_ID = 'magnetic.survey-l2-irls-local/v1'


def validate_owned_magnetic_result(payload, *, user, job, dataset, expected_binding):
    """Validate a previously byte/hash-verified private projection before return."""
    if (str(job.owner_id) != str(user.id) or str(dataset.owner_id) != str(user.id)
            or job.project_id != dataset.project_id or job.dataset_id != dataset.id):
        raise ApiError(404, 'not_found', 'Resource not found')
    if job.state != 'succeeded' or job.method_id != LOCAL_MAGNETIC_METHOD_ID:
        raise ApiError(409, 'magnetic_result_unavailable', 'A complete local magnetic replay is required')
    if (type(expected_binding) is not dict or set(expected_binding) != {
            'job_id', 'dataset_id', 'source_id', 'generation_sha256', 'configuration_sha256', 'original_sha256'}
            or expected_binding['job_id'] != job.id or expected_binding['dataset_id'] != dataset.id
            or expected_binding['original_sha256'] != dataset.raw_sha256
            or job.dataset_sha256 != dataset.sha256):
        raise ApiError(409, 'derived_integrity_failed', 'Durable magnetic receipt or dataset identity differs')
    if (type(payload) is not dict or payload.get('schema') != 'magnetic-owner-result-view-1'
            or payload.get('binding') != expected_binding or payload.get('lane') != 'local_replay'
            or payload.get('online_admitted') is not False or type(payload.get('claims')) is not dict
            or set(payload['claims']) != {'full_method_accepted', 'field_source_verified', 'geology_truth_known', 'online_admitted'}
            or any(value is not False for value in payload['claims'].values())):
        raise ApiError(409, 'derived_integrity_failed', 'Magnetic result binding or execution claim differs')
    return payload
