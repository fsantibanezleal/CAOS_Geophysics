"""Narrow participant in the existing owned DELETE, never another delete route."""

import asyncio
from pathlib import Path

from sqlalchemy import func, select

from app.errors import ApiError
from app.models import DeletionReceipt, ObservationDataset, ProcessingJob, RawAsset, SourceRecord
from app.physical_contract import canonical, require
from app.profile_archive_custody import METHODS, deletion_entries, retained_inventory


async def archive_relations(session):
    """Complete profile job relations in the caller's current SQL snapshot."""
    jobs=(await session.execute(select(ProcessingJob.id,ProcessingJob.owner_id,ProcessingJob.project_id,
        ProcessingJob.dataset_id,ProcessingJob.dataset_sha256,ProcessingJob.request_sha256,ProcessingJob.method_id,
        ProcessingJob.state).where(ProcessingJob.method_id.in_(METHODS)).limit(100001))).all()
    require(len(jobs)<=100000,'profile_archive_relation_cap')
    result=[]
    # Batched complete relation sets, not an N+1 request loop or filtered joins
    # that could hide an orphan/foreign processing job.
    datasets={row.id:row for row in (await session.execute(select(ObservationDataset.id,ObservationDataset.owner_id,
        ObservationDataset.project_id,ObservationDataset.raw_asset_id,ObservationDataset.raw_sha256,
        ObservationDataset.sha256,ObservationDataset.parser_version,ObservationDataset.modality).limit(100001))).all()}
    raws={row.id:row for row in (await session.execute(select(RawAsset.id,RawAsset.owner_id,RawAsset.project_id,
        RawAsset.source_id,RawAsset.sha256,RawAsset.detected_format).limit(100001))).all()}
    sources={row.id:row for row in (await session.execute(select(SourceRecord.id,SourceRecord.owner_id,
        SourceRecord.project_id,SourceRecord.sha256).limit(100001))).all()}
    require(len(datasets)+len(raws)+len(sources)+len(jobs)<=100000,'profile_archive_relation_cap')
    for job in jobs:
        dataset=datasets.get(job.dataset_id)
        require(dataset is not None,'profile_archive_dataset_missing')
        raw=raws.get(dataset.raw_asset_id)
        require(raw is not None,'profile_archive_raw_missing')
        source=sources.get(raw.source_id)
        require(source is not None,'profile_archive_source_missing')
        require(all((str(row.owner_id),row.project_id)==(str(job.owner_id),job.project_id) for row in (dataset,raw,source)) and
                job.dataset_sha256==dataset.sha256 and dataset.raw_sha256==raw.sha256==source.sha256,
                'profile_archive_live_relations')
        require(dataset.parser_version=='supplied-profile-original/v1' and
                dataset.modality==('ert_profile' if job.method_id=='ert.topographic-profile/v1' else 'traveltime_profile') and
                raw.detected_format==('ert_ohm' if job.method_id=='ert.topographic-profile/v1' else 'traveltime_sgt'),
                'profile_archive_original_dictionary')
        result.append(dict(id=job.id,owner_id=str(job.owner_id),project_id=job.project_id,dataset_id=dataset.id,
            dataset_sha256=dataset.sha256,raw_asset_id=raw.id,source_id=source.id,raw_sha256=raw.sha256,
            request_sha256=job.request_sha256,method_id=job.method_id,state=job.state))
    receipt_bytes=(await session.execute(select(func.coalesce(func.sum(func.length(DeletionReceipt.derived_manifest)),0)))).scalar_one()
    require(receipt_bytes<=16*1048576,'profile_archive_receipt_bytes')
    receipts=(await session.execute(select(DeletionReceipt.id,DeletionReceipt.owner_id,
        DeletionReceipt.project_id,DeletionReceipt.derived_manifest).limit(100001))).all()
    require(len(result)+len(receipts)<=100000,'profile_archive_relation_cap')
    return result,[dict(id=r.id,owner_id=str(r.owner_id),project_id=r.project_id,derived_manifest=r.derived_manifest) for r in receipts]


class ProfileArchiveDeletion:
    """Fixed operator-installed authority and actual all-participant lease.

    It requires the request middleware to acquire exclusive BEFORE auth/session
    creation. It neither upgrades a lease nor obtains one inside the SQL TX.
    Runtime assembly must register all API/worker/recovery writers separately.
    """
    def __init__(self, leases, *, approved_installations):
        from app.physical_leases import WriterLeases
        require(isinstance(leases,WriterLeases),'profile_archive_native_lease')
        self.leases=leases
        # Source/runtime/configuration binding comes from the fixed trusted
        # operator installer, never the archived manifest or an HTTP field.
        self.approval_bytes=canonical(approved_installations)
        require(len(self.approval_bytes)<=4*1048576,'profile_archive_registry_cap')

    def check_exclusion(self):
        self.leases.require_held(exclusive=True)

    async def prepare(self, settings, session, owner_id, project_id, jobs):
        import json
        self.check_exclusion()
        require(session.in_transaction(),'profile_archive_delete_snapshot')
        require(Path(settings.data_dir)==Path(self.leases.files.root_path),'profile_archive_root_binding')
        require(not any(job.state in ('queued','running') for job in jobs),'profile_archive_active_project')
        relations,receipts=await archive_relations(session)
        approved=json.loads(self.approval_bytes)
        files=self.leases.files
        records=await asyncio.to_thread(retained_inventory,files,relations,receipts,approved_installations=approved)
        try:
            stages=await asyncio.to_thread(files.names,'.job-staging',limit=100000)
        except FileNotFoundError:
            stages=[]
        require(not set(stages)&{job.id for job in jobs},'profile_archive_active_or_unrecovered_stage')
        self.check_exclusion()
        return deletion_entries(records,owner_id=owner_id,project_id=project_id)


async def prepare_archive_deletion(app, settings, session, owner_id, project_id, jobs):
    """Called before the original route moves anything, under its transaction."""
    participant=getattr(app.state,'profile_archive_deletion',None)
    path=Path(settings.data_dir)/'.profile-retained'
    if participant is None:
        # A nonparticipating legacy binary cannot erase the identity needed to
        # recover a global retained archive, even if the UUID looks unrelated.
        if path.exists() or path.is_symlink():
            raise ApiError(409,'profile_archive_custody_unresolved','Retained profile custody requires the installed deletion participant')
        return []
    if not isinstance(participant,ProfileArchiveDeletion):
        raise ApiError(409,'profile_archive_custody_unresolved','Retained profile deletion participant is not recognized')
    try:
        return await participant.prepare(settings,session,owner_id,project_id,jobs)
    except (ValueError,OSError):
        raise ApiError(409,'profile_archive_custody_unresolved','Retained profile custody is unresolved; original bytes and rows are preserved') from None
