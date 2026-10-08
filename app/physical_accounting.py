"""Literal retained-byte accounting inside the caller's consistent transaction."""

from types import MappingProxyType

from app.physical_contract import integer, require, uuid
from app.physical_persistence import CORRECTION, TRANSFORM, M


# Positive existing method registry. No unknown method falls back to flag-QC.
# Flag/MT constants are the unchanged processing_contract/mt_contract values;
# profiles are pinned profile_contract64MiB, M08 waveform_contract52690944.
LEGACY_SCRATCH = MappingProxyType({
    "gravity.station-outlier-flags/v1": 8*M,
    "mt.edi-full-tensor-qc/v1": 8*M,
    "mt.edi-fixed-thickness-trf/v1": 32*M,
    "ert.topographic-profile/v1": 64*M,
    "traveltime.first-arrival-profile/v1": 64*M,
    "seismic.waveform-qc-classical/v1": 52690944,
})


def account_private_charge(connection, owner_id, *, profile_records=None, approved_installations=None):
    uuid(owner_id)
    require(connection.in_transaction, "physical_accounting_requires_consistent_transaction")
    require(connection.execute("SELECT 1 FROM user WHERE id=?", (owner_id,)).fetchone() is not None, "physical_account_owner")
    def total(sql):
        value = connection.execute(sql, (owner_id,)).fetchone()[0]
        return integer(0 if value is None else value)
    raw = total("SELECT SUM(byte_count) FROM raw_assets WHERE owner_id=?")
    usage = connection.execute("SELECT raw_bytes FROM account_usage WHERE user_id=?", (owner_id,)).fetchone()
    require((usage[0] if usage else 0) == raw, "physical_raw_accounting")
    datasets = total("SELECT SUM(byte_count) FROM observation_datasets WHERE owner_id=?")
    results = total("SELECT SUM(result_bytes) FROM processing_jobs WHERE owner_id=? AND state='succeeded'")
    # M08's immutable extra members are separate stored result files, not part
    # of the main job envelope's result_bytes. Count every copy, never hashes.
    results += total("SELECT SUM(a.byte_count) FROM waveform_result_artifacts a JOIN processing_jobs j ON j.id=a.job_id WHERE j.owner_id=?")
    controls = total("SELECT SUM(length(c.request_bytes)+length(c.module_manifest_bytes)+coalesce(length(c.parent_production_bytes),0)+length(CAST(j.request_json AS BLOB))+length(CAST(j.preflight AS BLOB))) FROM physical_job_controls c JOIN processing_jobs j ON j.id=c.job_id WHERE c.owner_id=?")
    controls += total("SELECT SUM(length(adapter_receipt_bytes)) FROM physical_dataset_productions WHERE owner_id=?")
    permanent = total("SELECT SUM(permanent_reservation_bytes) FROM physical_job_controls WHERE owner_id=?")
    permanent += total("SELECT SUM(permanent_reservation_bytes) FROM physical_publication_intents WHERE owner_id=?")
    custody = total("SELECT SUM(charged_bytes) FROM physical_custody_batches WHERE owner_id=?")
    active = 0
    for job_id, method in connection.execute("SELECT id,method_id FROM processing_jobs WHERE owner_id=? AND state IN ('queued','running')", (owner_id,)):
        if method in (CORRECTION, TRANSFORM):
            require(connection.execute("SELECT 1 FROM physical_job_controls WHERE job_id=? AND owner_id=?", (job_id, owner_id)).fetchone() is not None,
                    "physical_control_missing")
        else:
            require(method in LEGACY_SCRATCH, "physical_unknown_active_method")
            active += LEGACY_SCRATCH[method]
    result = dict(raw=raw, datasets=datasets, results=results, controls=controls,
                  permanent=permanent, custody=custody, legacy_active=active,
                  profile_retained=_profile_charge(connection,owner_id,profile_records,approved_installations))
    result["total"] = integer(sum(result.values()))
    return MappingProxyType(result)


def _profile_charge(connection, owner_id, records, approved):
    """Fresh closed archive census supplied by the participating runtime.

    No filesystem discovery or archive authority is inferred from SQL. Missing
    saved custody is a refusal, not zero charge. The runtime must also census
    the live archive namespace in this transaction, before invoking admission.
    """
    import json
    from app.physical_contract import canonical
    from app.profile_archive_custody import ARCHIVE_SCHEMAS, archive_limits, validate_saved_entry, validate_original_receipt_entry, _json
    saved={}
    cursor=connection.execute('SELECT owner_id,project_id,derived_manifest FROM deletion_receipts')
    count=0; byte_count=0
    for owner,project,body in cursor:
        count+=1; require(count<=100000,'physical_profile_receipt_cap')
        if body is None: continue
        require(type(body) is str,'physical_profile_receipt_type')
        encoded=body.encode('utf-8'); byte_count+=len(encoded)
        require(byte_count<=16*M,'physical_profile_receipt_cap')
        entries=_json(encoded,4*M)
        require(type(entries) is list and len(entries)<=4096,'physical_profile_receipt_cap')
        for entry in entries:
            require(type(entry) is dict,'physical_profile_receipt_type')
            if entry.get('schema') in ARCHIVE_SCHEMAS:
                identifier=entry.get('job_id')
                require(identifier not in saved,'physical_profile_duplicate_charge')
                saved[identifier]=(owner,project,entry)
            else:
                validate_original_receipt_entry(entry)
    if records is None:
        require(not saved,'physical_profile_census_required')
        return 0
    require(type(records) is list and len(records)<=128 and type(approved) is dict,'physical_profile_charge_census')
    archive_limits(records)
    seen=set(); total_charge=0
    for record in records:
        require(type(record) is dict,'physical_profile_charge_record')
        relation=validate_saved_entry(record,owner_id=record.get('owner_id'),project_id=record.get('project_id'),
            approved_installations=approved)
        identifier=relation['id']
        require(identifier not in seen,'physical_profile_duplicate_charge'); seen.add(identifier)
        if identifier in saved:
            owner,project,entry=saved[identifier]
            require((owner,project)==(relation['owner_id'],relation['project_id']) and
                    canonical(entry)==canonical(record),'physical_profile_saved_charge_binding')
            require(connection.execute('SELECT 1 FROM processing_jobs WHERE id=?',(identifier,)).fetchone() is None,
                    'physical_profile_duplicate_charge')
        else:
            row=connection.execute('''SELECT j.owner_id,j.project_id,j.dataset_id,j.dataset_sha256,j.request_sha256,
                j.method_id,j.state,j.request_json,d.raw_asset_id,d.sha256,d.raw_sha256,r.source_id,r.sha256,s.sha256,
                d.owner_id,d.project_id,r.owner_id,r.project_id,s.owner_id,s.project_id
                FROM processing_jobs j LEFT JOIN observation_datasets d ON d.id=j.dataset_id
                LEFT JOIN raw_assets r ON r.id=d.raw_asset_id LEFT JOIN source_records s ON s.id=r.source_id
                WHERE j.id=?''',(identifier,)).fetchone()
            require(row is not None,'physical_profile_live_charge_binding')
            owner,project,dataset,dataset_sha,request_sha,method,state,request,raw,actual_dataset_sha,dataset_raw_sha,source,raw_sha,source_sha,*joins=row
            require((owner,project,dataset,dataset_sha,request_sha,method,state,raw,source,raw_sha)==
                tuple(relation[k] for k in ('owner_id','project_id','dataset_id','dataset_sha256','request_sha256',
                    'method_id','state','raw_asset_id','source_id','raw_sha256')) and
                dataset_sha==actual_dataset_sha and dataset_raw_sha==raw_sha==source_sha and
                joins==[owner,project,owner,project,owner,project], 'physical_profile_live_charge_binding')
            request=json.loads(request)
            require(type(request) is dict and request.get('raw_asset_id')==raw and request.get('raw_sha256')==raw_sha,
                    'physical_profile_live_charge_binding')
        if relation['owner_id']==owner_id:
            total_charge+=integer(record['charged_bytes'])
    require(set(saved)<=seen,'physical_profile_missing_custody_charge')
    return integer(total_charge)
