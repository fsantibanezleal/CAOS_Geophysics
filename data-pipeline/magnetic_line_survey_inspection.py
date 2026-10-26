"""Two forward phases, with external atomic reservation BETWEEN them."""
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_bundle as bundle
import magnetic_line_survey_preparation_capacity as capacity


def _inspect(plan):
    core._closed(plan,'schema original metadata request bundles','ingest')
    bundle._check(plan['schema']=='m03-owner-inspection-plan/1','invalid_contract')
    bundle._check(type(plan['bundles']) is list and 1<=len(plan['bundles'])<=16,'invalid_contract')
    proof=capacity.inspection_capacity(plan['original']['bytes'],
        [plan[key]['bytes'] for key in ('metadata','request')],[item['bytes'] for item in plan['bundles']])
    metadata,request=bundle.decode_documents(bundle._verified_document(plan['metadata']),bundle._verified_document(plan['request']))
    bundle._check(metadata['original']['csv_sha256']==plan['original']['sha256'] and metadata['original']['csv_bytes']==plan['original']['bytes'])
    bundle._check(request['dataset_version_sha256']==base.dataset_identity(metadata['original']['csv_sha256'],base.digest(metadata)))
    bundle._check(metadata['rights']['decision']==metadata['rights']['private_processing']=='allowed','metadata_ineligible')
    bundle._check(1<=len(bundle._refs(dict(metadata=metadata,request=request)))<=192,'resource_refused')
    rows=bundle._geometry_preflight(plan['original'])
    counts=[bundle._index_bundle(None,item,number)[1] for number,item in enumerate(plan['bundles'])]
    bundle._check(sum(counts)<=proof['physical_member_cap'],'resource_refused')
    next_phase=capacity.preparation_capacity(rows,proof['auxiliary_bytes'],sum(counts))
    return dict(schema='m03-owner-inspection-receipt/1',original=metadata['original'],rows=rows,
        metadata_sha256=plan['metadata']['sha256'],request_sha256=plan['request']['sha256'],
        bundle_sha256=[item['sha256'] for item in plan['bundles']],bundle_members=counts,
        auxiliary_bytes=proof['auxiliary_bytes'],next_phase=next_phase,value_access='not_opened')


def run_inspection_plan(plan,workspace,job_handle):
    from magnetic_line_survey_runtime import require_job,owned_bytes
    require_job(job_handle)
    receipt=_inspect(plan)
    core._write_member(workspace,'inspection.json',base.canonical_bytes(receipt))
    bundle._check(owned_bytes(workspace)<=capacity.INSPECTION_BYTES,'resource_refused')
    return 0


def run_staged_preparation_plan(plan,workspace,job_handle):
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    core._closed(plan,'schema original metadata request bundles inspection','ingest')
    bundle._check(plan['schema']=='m03-owner-preparation-plan/2','invalid_contract')
    previous=base.strict_json(bundle._verified_document(plan['inspection']))
    inspection_plan={key:value for key,value in plan.items() if key!='inspection'}
    inspection_plan['schema']='m03-owner-inspection-plan/1'
    rebuilt=_inspect(inspection_plan)
    bundle._check(previous==rebuilt)
    preparation_plan={key:value for key,value in plan.items() if key!='inspection'}
    preparation_plan['schema']='m03-owner-preparation-plan/1'
    bundle._prepare(preparation_plan,workspace,capacity_override=rebuilt['next_phase'])
    return 0
