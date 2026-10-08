"""M04 discriminator in existing magnetic preparation attempts, not a new ledger.

The integration owner binds complete accounting and task-checked physical
guards. No HTTP callback, missing native counter or generic JSON fallback can
grant custody. Local read-only CPU work does not claim OS/native admission.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import hashlib
import re
import shutil
from uuid import uuid4

from sqlalchemy import select, text

from app.errors import ApiError
from app.magnetic_line_survey_models import SurveyDatasetAttempt
from app.processing_contract import canonical_bytes

SCHEMA = "magnetic-owned-custody-attempt-1"
LIFETIME = "magnetic-owned-custody-drain-1"
MAX_ZIP = 128 * 1024**2
OPERATIONS = {"import": 4*MAX_ZIP, "read": 2*MAX_ZIP, "export": 2*MAX_ZIP}
SOURCE_KEYS = frozenset("dataset_id dataset_sha256 raw_asset_id raw_sha256 raw_bytes source_record_id rights_decision private_storage_permission".split())


def refuse():
    raise ApiError(409, "magnetic_custody_debt", "Exact magnetic custody requires owner reconciliation")


async def drain(pending):
    """Repeated cancellation cannot leave an owned writer running after return."""
    while not pending.done():
        try:
            await asyncio.shield(pending)
        except asyncio.CancelledError:
            continue
        except BaseException:
            break
    return pending.result()


async def bounded_work(function, *args, timeout):
    """Bound the response wait, but never misreport cancelled to_thread as drain.

    A timed-out/cancelled worker MUST actually complete before the caller can
    release guards. This is not a hard native CPU/memory containment receipt.
    """
    pending = asyncio.create_task(asyncio.to_thread(function, *args))
    try:
        return await asyncio.wait_for(asyncio.shield(pending), timeout)
    except BaseException:
        try:
            await drain(pending)
        except BaseException:
            pass  # Preserve original timeout/cancellation; work is now done.
        raise


class MagneticCustodyOwner:
    def __init__(self, physical, *, base_charge, device_charge):
        from app.physical_assembly import PhysicalAssembly
        if type(physical) is not PhysicalAssembly or not callable(base_charge) or not callable(device_charge):
            refuse()
        self.physical, self.base_charge, self.device_charge = physical, base_charge, device_charge

    def require(self, session, settings, *, excluded=False):
        if (session.info.get("magnetic_custody_owner") is not self
                or session.info.get("physical_assembly") is not self.physical
                or settings.data_dir != self.physical.leases.files.root_path):
            refuse()
        self.physical.leases.require_held(exclusive=excluded)
        if excluded:
            self.physical.worker.require_held()
        else:
            self.physical.worker.require_processing_held()

    @asynccontextmanager
    async def lifetime(self, session, settings):
        # This operation acquires guards in its OWN task. An inherited ContextVar
        # from an ASGI request is not all-writer or processing lease authority.
        async with self.physical.leases.acquire():
            async with self.physical.worker.acquire_processing():
                self.require(session, settings)
                yield
                self.require(session, settings)

    async def reserve(self, session, settings, user, dataset, *, operation, sources, job_id=None):
        self.require(session, settings)
        if operation not in OPERATIONS or session.in_transaction():
            refuse()
        identifier = str(uuid4())
        request = dict(schema=SCHEMA, operation=operation, stage_key=f".magnetic-custody/{identifier}",
                       dataset_id=dataset.id, dataset_sha256=dataset.sha256, job_id=job_id)
        validate_sources(sources, request)
        await session.execute(text("BEGIN IMMEDIATE"))
        try:
            previous = (await session.execute(select(SurveyDatasetAttempt).where(
                SurveyDatasetAttempt.owner_id == user.id))).scalars().all()
            # Failed/uncertain attempts are never silently adopted or zero charged.
            if any(row.input_json.get("schema") == SCHEMA and row.state != "published" for row in previous):
                refuse()
            charge = await self.base_charge(session, user.id)
            device = await self.device_charge(session)
            if type(charge) is not int or charge < 0 or type(device) is not int or device < 0:
                refuse()
            reservation = OPERATIONS[operation]
            debt = await attempt_charge(session, user.id)
            if charge + debt + reservation > settings.account_quota_bytes:
                raise ApiError(413, "quota_exceeded", "Replay scratch and permanent copies exceed account quota")
            if device + reservation > settings.worker_scratch_bytes or shutil.disk_usage(settings.data_dir).free < device + reservation + 64*1024**2:
                raise ApiError(507, "magnetic_scratch_reservation_refused", "External scratch capacity refused")
            row = SurveyDatasetAttempt(id=identifier, owner_id=user.id, project_id=dataset.project_id,
                input_json=request, source_receipts=sources,
                authority_sha256=hashlib.sha256(canonical_bytes(request)).hexdigest(),
                reservation_bytes=reservation, state="reserved", retained_bytes=0, inventory=[], dataset_id=dataset.id)
            session.add(row)
            await session.commit()  # BEFORE the first directory/archive/extraction.
            return row
        except BaseException:
            await session.rollback()
            raise


def owner_for(session):
    owner = session.info.get("magnetic_custody_owner")
    if type(owner) is not MagneticCustodyOwner:
        refuse()
    return owner


def validate_sources(sources, request):
    from app.magnetic_contract import _uuid
    if (type(sources) is not dict or set(sources) != SOURCE_KEYS
            or sources["dataset_id"] != request["dataset_id"]
            or sources["dataset_sha256"] != request["dataset_sha256"]
            or type(sources["raw_bytes"]) is not int or not 0 < sources["raw_bytes"] <= MAX_ZIP
            or sources["rights_decision"] not in ("mirror", "link")
            or sources["private_storage_permission"] != "attested"):
        refuse()
    for key in ("dataset_id", "raw_asset_id", "source_record_id"):
        _uuid(sources[key])
    for key in ("dataset_sha256", "raw_sha256"):
        if type(sources[key]) is not str or not re.fullmatch("[0-9a-f]{64}", sources[key]):
            refuse()


def validate_attempt(row):
    request = row.input_json
    if (type(request) is not dict or set(request) != {"schema", "operation", "stage_key", "dataset_id", "dataset_sha256", "job_id"}
            or request["schema"] != SCHEMA or request["operation"] not in OPERATIONS
            or request["stage_key"] != f".magnetic-custody/{row.id}"
            or request["dataset_id"] != row.dataset_id
            or hashlib.sha256(canonical_bytes(request)).hexdigest() != row.authority_sha256
            or row.reservation_bytes != OPERATIONS[request["operation"]]
            or type(row.retained_bytes) is not int or not 0 <= row.retained_bytes <= row.reservation_bytes):
        refuse()
    from app.magnetic_contract import _uuid
    _uuid(row.id)
    _uuid(request["job_id"])
    validate_sources(row.source_receipts, request)
    if row.state == "published":
        if row.lifetime != dict(schema=LIFETIME, work_completed=True, scratch_removed=True, native_admission=False):
            refuse()
        if row.inventory or row.retained_bytes:
            refuse()
    elif row.state not in ("reserved", "running", "drained", "failed", "publication_uncertain"):
        refuse()
    return request


async def attempt_charge(session, owner_id):
    rows = (await session.execute(select(SurveyDatasetAttempt).where(
        SurveyDatasetAttempt.owner_id == owner_id))).scalars().all()
    charge = 0
    for row in rows:
        if type(row.input_json) is not dict:
            refuse()
        if row.input_json.get("schema") != SCHEMA:
            # Parent separately dispatches M03; this is explicitly M04 subtotal.
            if row.input_json.get("schema") != "m03-owner-dataset-request/1":
                refuse()
            continue
        validate_attempt(row)
        charge += row.retained_bytes if row.state == "published" else max(row.reservation_bytes, row.retained_bytes)
    return charge


async def reconcile_attempts(session, owner, settings):
    """Exact additive startup/delete reader; debt/unknown dirs stay refused."""
    owner.require(session, settings, excluded=True)
    rows = (await session.execute(select(SurveyDatasetAttempt))).scalars().all()
    selected = [row for row in rows if type(row.input_json) is dict and row.input_json.get("schema") == SCHEMA]
    for row in selected:
        validate_attempt(row)
        if row.state != "published":
            refuse()
        from app.magnetic_custody import _owned, _sources, exact_zip_inventory
        from app.models import ProcessingJob
        from types import SimpleNamespace
        dataset, asset, source = await _owned(session, SimpleNamespace(id=row.owner_id), row.dataset_id, row.project_id)
        if _sources(dataset, asset, source) != row.source_receipts:
            refuse()
        job = await session.get(ProcessingJob, row.input_json["job_id"])
        if (job is None or (job.owner_id, job.project_id, job.dataset_id, job.dataset_sha256) !=
                (row.owner_id, row.project_id, row.dataset_id, row.input_json["dataset_sha256"])):
            refuse()
        await bounded_work(exact_zip_inventory, settings, job, timeout=min(120, settings.worker_wall_seconds))
    files = owner.physical.leases.files
    try:
        names = files.names(".magnetic-custody", limit=100000)
    except FileNotFoundError:
        names = []
    # Normal success removes the exact owned stage. Any surviving/unknown name
    # requires excluded recovery, not an inferred zero-byte empty namespace.
    if names:
        refuse()
    return dict(schema="magnetic-owned-custody-reconciliation-1", attempts=len(selected), retained_bytes=0)
