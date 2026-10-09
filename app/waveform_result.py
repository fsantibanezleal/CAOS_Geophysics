"""Bounded immutable scientific member publication, inventory and downloads."""

from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sys
import re

from sqlalchemy import select, text

from app.errors import ApiError
from app.models import ProcessingJob, WaveformResultArtifact, utcnow
from app.processing_contract import canonical_bytes, checked_derived_path, result_key, sha256
from app.waveform_contract import INPUT, METHOD_ID, SCRATCH, artifact_key, artifact_path

# The path-invoked ordinary scripts must share one class namespace with their CLI.
_ROOT = Path(__file__).resolve().parents[1]
for _ordinary_root in (_ROOT / "data-pipeline", _ROOT / "scripts"):
    if str(_ordinary_root) not in sys.path:
        sys.path.insert(0, str(_ordinary_root))


def local_export(path, *, held_fd=None):
    # Existing strict ordinary reopener. Imports do not invoke a decoder/engine.
    import waveform_m08_child  # noqa: F401
    from waveform_m08_files import open_output
    from waveform_m08_export import verify_export
    from waveform_m08_windows import ControlError

    try:
        if held_fd is not None:
            if sys.platform != "linux" or type(held_fd) is not int or held_fd < 0:
                raise ValueError()
            from waveform_m08_linux import LinuxHeldDirectory
            lease = LinuxHeldDirectory(held_fd)
        else:
            lease = open_output(path)
        with lease as directory:
            sealed = verify_export(directory)
            names = directory.names(55)
            members = []
            for name in sorted(names):
                with directory.open_regular(name) as stream:
                    size = directory.file_size(stream)
                    if not 0 < size <= 33554432:
                        raise ValueError()
                    digest = hashlib.sha256()
                    count = 0
                    while chunk := stream.read(65536):
                        count += len(chunk)
                        if count > size:
                            raise ValueError()
                        digest.update(chunk)
                    if count != size:
                        raise ValueError()
                    members.append({"name": name, "bytes": size, "sha256": digest.hexdigest()})
            if sum(row["bytes"] for row in members) > 33554432:
                raise ValueError()
            return sealed, members
    except (INPUT.WaveformInputError, ControlError, ValueError, OSError):
        raise ApiError(409, "waveform_export_invalid", "Waveform export failed independent validation") from None


def checked_resources(receipt, release):
    if type(receipt) is dict and receipt.get("schema") in {"caos.m08-linux-resources.v1", "caos.m08-linux-resources.v2"}:
        from app.waveform_linux_exec import checked_resources as checked_linux_resources
        return checked_linux_resources(receipt, release)
    try:
        INPUT.native_precount(receipt, 65536, max_nodes=4096, max_depth=8)
        INPUT.native_precount(release, 65536, max_nodes=4096, max_depth=8)
        if (
            receipt["schema"] != "caos.m08-local-resources.v1"
            or receipt["status"] != "measured"
            or receipt["runtime_authorized"] is not False
            or receipt["method_accepted"] is not False
            or receipt["host_admitted"] is not False
            or receipt["active_processes"] != 0
            or type(receipt["active_processes"]) is not int
            or release
            != {
                "schema": "caos.m08-local-release.v1",
                "run_id": receipt["run_id"],
                "receipt_sha256": hashlib.sha256(
                    json.dumps(
                        receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
                    ).encode()
                ).hexdigest(),
                "all_native_owned_handles_closed": True,
                "runtime_authorized": False,
            }
            or release["all_native_owned_handles_closed"] is not True
        ):
            raise ValueError()
        for key, maximum in (
            ("cpu_ns", 60000000000),
            ("max_sample_gap_ns", 100000000),
            ("peak_committed_bytes", 1073741824),
        ):
            if type(receipt[key]) is not int or not 0 <= receipt[key] <= maximum:
                raise ValueError()
        if (
            receipt["budget_ns"] != 60000000000
            or receipt["stop_ns"] != 57000000000
            or type(receipt["sample_count"]) is not int
            or receipt["sample_count"] < 2
            or type(receipt["drained_ns"]) is not int
            or type(receipt["stable_final_ns"]) is not int
            or receipt["stable_final_ns"] < receipt["drained_ns"] + 100000000
        ):
            raise ValueError()
        return {
            "schema": "geophysics.waveform-resources/v1",
            "cpu_ns": receipt["cpu_ns"],
            "max_sample_gap_ns": receipt["max_sample_gap_ns"],
            "peak_memory_bytes": receipt["peak_committed_bytes"],
            "memory_kind": "windows_job_committed",
            "native_receipt_sha256": release["receipt_sha256"],
            "release_sha256": sha256(canonical_bytes(release)),
            "runtime_authorized": False,
            "host_admitted": False,
        }
    except (KeyError, TypeError, ValueError, INPUT.WaveformInputError):
        raise ApiError(
            409, "waveform_resource_invalid", "Final waveform native accounting or release is invalid"
        ) from None


def validate_result(payload, job):
    try:
        expected = set(
            "schema job_id project_id dataset_id dataset_sha256 method_id request_sha256 scientific_request_sha256 sources scientific_status calculation_sha256 calculation members resources".split()
        )
        native_keys = {"linux_execution","linux_installation"}
        if type(payload) is not dict:
            raise ValueError()
        if native_keys & set(payload):
            if not native_keys <= set(payload):
                raise ValueError()
            from app.waveform_linux_execution import validate_terminal
            from waveform_m08_installation import validate_installation_binding
            validate_terminal(payload["linux_execution"],job,payload=payload)
            validate_installation_binding(payload["linux_installation"],checked=payload["linux_execution"]["installation"])
            if payload["resources"]["memory_kind"] != "linux_cgroup_charge":
                raise ValueError()
            expected |= native_keys
        # The separately bounded private native graph has uint64 monotonic clocks.
        # Scientific/public metadata keeps its unchanged JS-safe integer dialect.
        INPUT.native_precount({key:value for key,value in payload.items() if key not in native_keys},
                              4194304,max_nodes=2097152,max_depth=24)
        if (
            type(payload) is not dict
            or set(payload) != expected
            or payload["schema"] != "geophysics.waveform-result/v1"
            or payload["job_id"] != job.id
            or payload["project_id"] != job.project_id
            or payload["dataset_id"] != job.dataset_id
            or payload["dataset_sha256"] != job.dataset_sha256
            or payload["method_id"] != METHOD_ID
            or job.method_id != METHOD_ID
            or payload["request_sha256"] != job.request_sha256
            or payload["scientific_request_sha256"] != job.request_json["scientific_request_sha256"]
            or payload["sources"] != job.request_json["waveform_sources"]
            or payload["scientific_status"] not in ("computed", "qc_only")
        ):
            raise ValueError()
        metadata = payload["calculation"]
        import waveform_m08_child  # noqa: F401
        from waveform_evaluation import _sealed_metadata

        _sealed_metadata(metadata)
        scientific_bytes = json.dumps(
            metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode()
        if (
            len(scientific_bytes) > 2097152
            or sha256(scientific_bytes) != payload["calculation_sha256"]
            or metadata["status"] != payload["scientific_status"]
            or metadata["request"]["submitted"] != job.request_json["scientific_request"]
            or metadata["request"]["scientific_sha256"] != payload["scientific_request_sha256"]
        ):
            raise ValueError()
        for role, label in (("miniseed", "miniseed"), ("stationxml", "stationxml")):
            if (
                metadata["sources"][label]["raw_sha256"] != payload["sources"][role]["raw_sha256"]
                or metadata["sources"][label]["raw_bytes"] != payload["sources"][role]["raw_bytes"]
            ):
                raise ValueError()
        members = payload["members"]
        if type(members) is not list or not 3 <= len(members) <= 55:
            raise ValueError()
        names = []
        total = 0
        for row in members:
            if type(row) is not dict or set(row) != {"name", "bytes", "sha256"}:
                raise ValueError()
            artifact_key(str(job.owner_id), job.project_id, job.id, row["name"])
            if type(row["bytes"]) is not int or not 0 < row["bytes"] <= 33554432:
                raise ValueError()
            if type(row["sha256"]) is not str or not re.fullmatch("[a-f0-9]{64}", row["sha256"]):
                raise ValueError()
            names.append(row["name"])
            total += row["bytes"]
        if (
            names != sorted(set(names))
            or total > 33554432
            or not {"calculation.json", "manifest.json", "receipt.json"} <= set(names)
        ):
            raise ValueError()
        resources = payload["resources"]
        if (
            set(resources)
            != set(
                "schema cpu_ns max_sample_gap_ns peak_memory_bytes memory_kind native_receipt_sha256 release_sha256 runtime_authorized host_admitted".split()
            )
            or resources["schema"] != "geophysics.waveform-resources/v1"
            or resources["runtime_authorized"] is not False
            or resources["host_admitted"] is not False
            or resources["memory_kind"] not in ("windows_job_committed", "linux_cgroup_charge")
        ):
            raise ValueError()
        for key, maximum in (
            ("cpu_ns", 60000000000),
            ("max_sample_gap_ns", 100000000),
            ("peak_memory_bytes", 1073741824),
        ):
            if type(resources[key]) is not int or not 0 <= resources[key] <= maximum:
                raise ValueError()
    except (ValueError, TypeError, KeyError, INPUT.WaveformInputError, ApiError):
        raise ApiError(
            409, "derived_integrity_failed", "Waveform result identity or scientific contract changed"
        ) from None


def verified_artifacts(settings, job, payload, rows):
    validate_result(payload, job)
    expected = {row["name"]: row for row in payload["members"]}
    if len(rows) != len(expected) or {row.name for row in rows} != set(expected):
        raise ApiError(409, "derived_integrity_failed", "Waveform artifact rows differ from the result")
    for row in rows:
        item = expected[row.name]
        if (
            row.storage_key != artifact_key(str(job.owner_id), job.project_id, job.id, row.name)
            or row.byte_count != item["bytes"]
            or row.sha256 != item["sha256"]
        ):
            raise ApiError(409, "derived_integrity_failed", "Waveform artifact identity changed")
    directory = artifact_path(settings, rows[0].storage_key).parent
    sealed, members = local_export(directory)
    if members != payload["members"] or sealed.calculation_sha256 != payload["calculation_sha256"]:
        raise ApiError(409, "derived_integrity_failed", "Waveform artifact content changed")
    return directory


def preflight_publication_paths(target, directory, members, *, platform):
    """Pure destination check; never create, normalize or bypass a path limit."""
    try:
        if platform not in ("nt", "posix"):
            raise ValueError()
        if platform != "nt":
            return
        # The selected Windows API interpreter has the observed MAX_PATH limit.
        # Count UTF-16 code units, not Python characters or UTF-8 bytes. Include
        # the exact metadata target and every independently generated member.
        paths = [target, directory, *(directory / row["name"] for row in members)]
        for path in paths:
            value = str(path)
            if (not value or "\0" in value or value.startswith(("\\\\?\\", "\\\\.\\"))
                    or len(value.encode("utf-16-le", errors="strict")) // 2 >= 260):
                raise ValueError()
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise ApiError(503, "waveform_storage_unavailable",
                       "Waveform publication destinations exceed supported storage paths") from None


def preflight_lifecycle_paths(data_root,owner,project,target,directory,members,*,platform):
    """Exact generated live/delete and fixed-length ZIP targets, before install."""
    preflight_publication_paths(target,directory,members,platform=platform)
    if platform != "nt":
        return
    try:
        from uuid import UUID
        if any(type(value) is not str or str(UUID(value)) != value for value in (owner,project)):
            raise ValueError()
        live = data_root/"derived"/owner/project
        deleting = data_root/".deleting"/f"{owner}--{project}--derived"
        deletion_target = deleting/target.relative_to(live)
        deletion_directory = deleting/directory.relative_to(live)
        preflight_publication_paths(deletion_target,deletion_directory,members,platform=platform)
        # ZIP uses only a newly generated canonical UUID plus '.zip'. All UUID
        # values have exactly this length; no original/user name becomes a path.
        exports = data_root/".exports"
        preflight_publication_paths(exports/"00000000-0000-4000-8000-000000000000.zip",exports,[],platform=platform)
    except (ValueError,TypeError,AttributeError):
        raise ApiError(503,"waveform_storage_unavailable",
                       "Waveform lifecycle destinations exceed supported storage paths") from None


async def publish_result(settings, sessions, job, export_path, receipt, release, *, linux_execution=None,
                         linux_installation=None, linux_stage_fd=None):
    """The installed lane adopts its held export; never makes a third copy."""
    if linux_execution is None and linux_installation is None and linux_stage_fd is None:
        return await _publish_result(settings,sessions,job,export_path,receipt,release)
    from app.waveform_linux_execution import identity, validate_terminal
    from waveform_m08_installation import canonical, regular_at, validate_installation_binding
    export_fd = None
    try:
        if (sys.platform != "linux" or type(linux_stage_fd) is not int or linux_stage_fd < 0
                or linux_execution is None or linux_installation is None
                or Path(export_path) != settings.data_dir/".job-staging"/job.id/"export"):
            raise ValueError()
        held = identity(linux_stage_fd)
        validate_terminal(linux_execution,job,held,linux_installation)
        validate_installation_binding(linux_installation,checked=linux_execution["installation"])
        if (set(os.listdir(linux_stage_fd)) != {"export","root_receipt.json"}
                or regular_at(linux_stage_fd,"root_receipt.json",65536) != canonical(linux_execution)):
            raise ValueError()
        info = Path(export_path).parent.stat(follow_symlinks=False)
        if dict(device=info.st_dev,inode=info.st_ino) != held:
            raise ValueError()
        export_fd = os.open("export",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=linux_stage_fd)
        return await _publish_result(settings,sessions,job,export_path,receipt,release,
            linux_execution=linux_execution,linux_installation=linux_installation,
            linux_stage_fd=linux_stage_fd,export_fd=export_fd)
    except (OSError,ValueError,TypeError,KeyError):
        raise ApiError(409,"waveform_stage_changed","Waveform held publication stage changed; bytes retained") from None
    finally:
        if export_fd is not None:
            os.close(export_fd)


async def _publish_result(settings, sessions, job, export_path, receipt, release, *, linux_execution=None,
                          linux_installation=None, linux_stage_fd=None, export_fd=None):
    """Only called after the actual supervisor finishes and acknowledges release."""
    from app.waveform_processing import validate_source_rows
    from app.processing_contract import verified_json, dataset_key
    from app.models import ObservationDataset, AccountUsage
    from app.processing_storage import account_derived_usage

    sealed, members = local_export(export_path,held_fd=export_fd)
    resources = checked_resources(receipt, release)
    payload = {
        "schema": "geophysics.waveform-result/v1",
        "job_id": job.id,
        "project_id": job.project_id,
        "dataset_id": job.dataset_id,
        "dataset_sha256": job.dataset_sha256,
        "method_id": METHOD_ID,
        "request_sha256": job.request_sha256,
        "scientific_request_sha256": job.request_json["scientific_request_sha256"],
        "sources": job.request_json["waveform_sources"],
        "scientific_status": json.loads(sealed.metadata_bytes)["status"],
        "calculation_sha256": sealed.calculation_sha256,
        "calculation": json.loads(sealed.metadata_bytes),
        "members": members,
        "resources": resources,
    }
    if linux_execution is not None or linux_installation is not None:
        if (linux_execution is None or linux_installation is None
                or linux_execution.get("native") != {"eligibility":receipt,"release":release}):
            raise ApiError(409,"waveform_resource_invalid","Linux waveform terminal differs from retained native bytes")
        payload.update(linux_execution=linux_execution,linux_installation=linux_installation)
    validate_result(payload, job)
    encoded = canonical_bytes(payload)
    if len(encoded) > 4194304:
        raise ApiError(413, "waveform_result_limit", "Waveform result metadata exceeds its bound")
    key = result_key(str(job.owner_id), job.project_id, job.id)
    target = checked_derived_path(settings, key)
    directory = artifact_path(settings, artifact_key(str(job.owner_id), job.project_id, job.id, "manifest.json")).parent
    preflight_lifecycle_paths(settings.data_dir,str(job.owner_id),job.project_id,target,directory,members,platform=os.name)
    async with sessions() as session:
        await session.execute(text("BEGIN IMMEDIATE"))
        current = (await session.execute(select(ProcessingJob).where(ProcessingJob.id == job.id))).scalar_one()
        if current.cancel_requested or current.state != "running":
            raise ApiError(409, "user_cancelled", "Waveform publication cancelled before installation")
        dataset = (
            await session.execute(select(ObservationDataset).where(ObservationDataset.id == job.dataset_id))
        ).scalar_one()
        indexed = verified_json(
            settings, dataset_key(str(job.owner_id), job.project_id, job.dataset_id), dataset.sha256, dataset.byte_count
        )
        await validate_source_rows(session, settings, dataset, indexed)
        raw_usage = (
            await session.execute(select(AccountUsage.raw_bytes).where(AccountUsage.user_id == job.owner_id))
        ).scalar_one_or_none() or 0
        total = len(encoded) + sum(row["bytes"] for row in members)
        # Existing active reservation already charges the full scratch bound.
        if total > SCRATCH or (
            hasattr(settings, "account_quota_bytes")
            and raw_usage + await account_derived_usage(session, job.owner_id) - SCRATCH + total
            > settings.account_quota_bytes
        ):
            raise ApiError(507, "account_quota_exceeded", "Waveform publication exceeds reserved private bytes")
        directory.parent.mkdir(parents=True, exist_ok=True)
        if export_fd is None:
            directory.mkdir(mode=0o700)  # Exclusive; no overwrite or rollback erasure.
        else:
            from app.waveform_publication import adopt_export
            from waveform_m08_installation import directory_fd
            parent_fd = directory_fd(directory.parent)
            try:
                adopt_export(linux_stage_fd,export_fd,parent_fd,job.id,linux_execution["stage"])
            finally:
                os.close(parent_fd)
        for row in members:
            source = Path(export_path) / row["name"]
            destination = directory / row["name"]
            if export_fd is None:
                _copy_member(source,destination,row)
            session.add(
                WaveformResultArtifact(
                    job_id=job.id,
                    name=row["name"],
                    storage_key=artifact_key(str(job.owner_id), job.project_id, job.id, row["name"]),
                    byte_count=row["bytes"],
                    sha256=row["sha256"],
                )
            )
        if local_export(directory,held_fd=export_fd) != (sealed, members):
            raise ApiError(409, "waveform_export_invalid", "Installed waveform export differs from its seal")
        if export_fd is not None:
            from app.waveform_publication import verify_adopted_path
            verify_adopted_path(directory,export_fd)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        if export_fd is not None:
            verify_adopted_path(directory,export_fd)
            if verified_json(settings,key,sha256(encoded),len(encoded)) != payload:
                raise ApiError(409,"waveform_stage_changed","Waveform installed metadata changed; bytes retained")
        current.state = "succeeded"
        current.result_key = key
        current.result_sha256 = sha256(encoded)
        current.result_bytes = len(encoded)
        current.scratch_bytes = total
        current.peak_rss_bytes = None  # Job committed-memory is not RSS.
        current.finished_at = utcnow()
        await session.commit()  # Any exception retains bytes; no uncertain-commit deletion.
    return payload


def _copy_member(source,destination,row):
    """Unchanged ordinary/Windows exclusive member-copy path."""
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        count = 0
        digest = hashlib.sha256()
        while chunk := incoming.read(65536):
            count += len(chunk)
            if count > row["bytes"]:
                raise ApiError(409, "waveform_export_invalid", "Waveform member changed during publication")
            digest.update(chunk)
            outgoing.write(chunk)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    if count != row["bytes"] or digest.hexdigest() != row["sha256"]:
        raise ApiError(409, "waveform_export_invalid", "Waveform member changed during publication")


async def result_directory(session, settings, job, payload):
    rows = (
        (await session.execute(select(WaveformResultArtifact).where(WaveformResultArtifact.job_id == job.id)))
        .scalars()
        .all()
    )
    return verified_artifacts(settings, job, payload, rows)


def member_response(directory, name, item):
    from fastapi.responses import StreamingResponse
    from waveform_m08_files import open_output

    # Keep both ancestor and regular-file leases until the stream closes.
    lease = open_output(directory)
    handle = lease.open_regular(name)

    def chunks():
        try:
            count = 0
            digest = hashlib.sha256()
            while body := handle.read(65536):
                count += len(body)
                if count > item["bytes"]:
                    raise RuntimeError("waveform_download_integrity_failed")
                digest.update(body)
                yield body
            if count != item["bytes"] or digest.hexdigest() != item["sha256"]:
                raise RuntimeError("waveform_download_integrity_failed")
        finally:
            handle.close()
            lease.__exit__(None, None, None)

    return StreamingResponse(
        chunks(),
        media_type="application/octet-stream",
        headers={
            "Content-Length": str(item["bytes"]),
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{name}"',
            "X-Content-SHA256": item["sha256"],
        },
    )


def zip_response(settings, directory, payload):
    import uuid
    import zipfile
    from fastapi.responses import StreamingResponse
    from waveform_m08_files import open_output

    exports = settings.data_dir / ".exports"
    if exports.is_symlink():
        raise ApiError(409, "derived_integrity_failed", "Export staging is unsafe")
    exports.mkdir(exist_ok=True)
    target = exports / f"{uuid.uuid4()}.zip"
    try:
        with (
            target.open("xb") as output,
            zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive,
            open_output(directory) as lease,
        ):
            for row in payload["members"]:
                with lease.open_regular(row["name"]) as incoming, archive.open(row["name"], "w") as outgoing:
                    digest = hashlib.sha256()
                    count = 0
                    while chunk := incoming.read(65536):
                        count += len(chunk)
                        if count > row["bytes"]:
                            raise ValueError()
                        digest.update(chunk)
                        outgoing.write(chunk)
                    if count != row["bytes"] or digest.hexdigest() != row["sha256"]:
                        raise ValueError()
        if target.stat().st_size > 33554432 + 65536:
            raise ValueError()
    except Exception:
        target.unlink(missing_ok=True)  # Only this newly created export, never originals.
        raise ApiError(409, "waveform_export_invalid", "Waveform ZIP could not be verified") from None

    def chunks():
        try:
            with target.open("rb") as stream:
                while chunk := stream.read(65536):
                    yield chunk
        finally:
            target.unlink(missing_ok=True)

    return StreamingResponse(
        chunks(),
        media_type="application/zip",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="waveform-{payload["job_id"]}.zip"',
        },
    )
