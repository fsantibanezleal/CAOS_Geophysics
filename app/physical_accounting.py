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


def account_private_charge(connection, owner_id):
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
                  permanent=permanent, custody=custody, legacy_active=active)
    result["total"] = integer(sum(result.values()))
    return MappingProxyType(result)
