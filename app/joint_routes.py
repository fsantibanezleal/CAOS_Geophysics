"""Authenticated M11 native-member intake and structural dataset indexing.

This is a transport/custody API. It never decodes numerical arrays or asserts
scientific acceptance. Routes are mounted only by the operator-bound physical
assembly; every mutation is reclassified with the complete current custody
census and quota inside the same SQLite write transaction before commit.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import stat
import tempfile
import time
from datetime import timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app import physical_joint_dataset_contract as dataset_contract
from app import physical_joint_native_contract as native
from app.errors import ApiError
from app.models import AccountUsage, RateWindow, ObservationDataset, RawAsset, SourceRecord, User, utcnow
from app.physical_async_sql import run_native_transaction
from app.physical_contract import byte_sha, canonical
from app.projects import _owned_asset, _owned_project
from app.schemas import SourceInput
from app.views import RawAssetView, asset_view

DATASET_SCHEMA = dataset_contract.SCHEMA
REQUEST_CAP = 65536
MAX_MEMBERS = 40
INDEX_CAP = native.MAX_JSON


def member_request(raw: bytes) -> dict:
    """Closed asset map, validated before any private source read."""
    if type(raw) is not bytes or len(raw) > REQUEST_CAP:
        raise ValueError("joint_dataset_request_cap")
    value = native.bounded_json(raw)
    native._keys(value, ("development", "sealed"))
    seen: set[str] = set()
    for role, members in value.items():
        if role not in ("development", "sealed") or type(members) is not dict or not members:
            raise ValueError("joint_dataset_members")
        allowed = {name + ".npy" for name in (native.DEVELOPMENT if role == "development" else native.SEALED)}
        allowed |= ({"request.json", "gravity.raw", "magnetic.raw", "gravity.corrections.json",
                     "magnetic.corrections.json"} if role == "development" else {"sealed.json"})
        for name, identity in members.items():
            if name not in allowed or type(identity) is not str:
                raise ValueError("joint_dataset_name")
            try:
                parsed = UUID(identity)
            except (ValueError, AttributeError) as error:
                raise ValueError("joint_dataset_asset_id") from error
            if str(parsed) != identity or identity in seen:
                raise ValueError("joint_dataset_asset_id")
            seen.add(identity)
    if len(seen) > MAX_MEMBERS or "request.json" not in value["development"] or "sealed.json" not in value["sealed"]:
        raise ValueError("joint_dataset_exact_inventory")
    return value


def _physical(request: Request, session: AsyncSession):
    from app.physical_assembly import PhysicalAssembly
    physical = getattr(request.app.state, "physical_assembly", None)
    if (not isinstance(physical, PhysicalAssembly) or session.info.get("physical_assembly") is not physical):
        raise ApiError(409, "physical_admission_closed", "The operator-bound physical runtime is unavailable")
    try:
        physical.leases.require_held()
    except (ValueError, OSError) as error:
        raise ApiError(409, "physical_writer_busy", "Private writer exclusion is unavailable") from error
    return physical


async def _registered_0006(session: AsyncSession) -> None:
    """Require canonical schema identity, not a revision stamp or table alias."""
    try:
        heads = (await session.execute(text("SELECT version_num FROM alembic_version"))).scalars().all()
        if heads != ["0006_joint_artifacts"]:
            raise ValueError("joint_schema_revision")
        from app.physical_schema import BASE_TABLES, DDL, EXTENSIONS
        ddl_rows = (await session.execute(text(
            "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name"))).all()
        digest = hashlib.sha256(json.dumps([tuple(row) for row in ddl_rows], separators=(",", ":"),
            ensure_ascii=False).encode()).hexdigest()
        tables = set((await session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))).scalars().all())
        if digest != DDL[heads[0]] or tables != BASE_TABLES | EXTENSIONS[heads[0]]:
            raise ValueError("joint_schema_identity")
    except Exception as error:
        raise ApiError(409, "joint_schema_unavailable", "Canonical M11 schema admission is required") from error


async def _classify(session: AsyncSession, physical):
    """Full source/filesystem/quota proof on the caller's current SQL snapshot."""
    try:
        result = await run_native_transaction(session, "classify_snapshot", files=physical.leases.files,
                                             **physical.participant.arguments())
    except (ValueError, OSError) as error:
        raise ApiError(409, "joint_custody_unresolved", "M11 custody cannot be proven from the current snapshot") from error
    if result.classification != "coherent_committed":
        raise ApiError(409, "joint_custody_unresolved", "M11 custody cannot be proven from the current snapshot")
    return result


def _require_quota(result, owner_id, limit):
    charge = result.account_charges.get(str(owner_id))
    if charge is None or charge["total"] > limit:
        raise ApiError(507, "account_quota_exceeded", "Account private-byte quota exceeded")


async def _member_rate(session: AsyncSession, owner_id) -> None:
    now = int(time.time())
    bucket = now - now % 3600
    key = str(owner_id)
    stmt = insert(RateWindow).values(scope="joint_native_member", client_key=key, window_start=bucket, count=1)
    await session.execute(stmt.on_conflict_do_update(
        index_elements=["scope", "client_key", "window_start"], set_={"count": RateWindow.count + 1}))
    count = (await session.execute(select(RateWindow.count).where(
        RateWindow.scope == "joint_native_member", RateWindow.client_key == key,
        RateWindow.window_start == bucket))).scalar_one()
    if count == 1:
        await session.execute(delete(RateWindow).where(
            RateWindow.scope == "joint_native_member", RateWindow.window_start < now - 86400))
    await session.commit()
    if count > 80:
        raise ApiError(429, "joint_member_rate_limited", "Native member rate window exceeded")


def _member_envelope(stream, meta: dict, count: int) -> None:
    stream.seek(0)
    head = stream.read(native.MAX_HEADER + 10)
    if head.startswith((b"PK\x03\x04", b"PK\x05\x06", b"\x1f\x8b", b"7z\xbc\xaf'\x1c", b"Rar!")) or head[257:262] == b"ustar":
        raise ApiError(415, "archive_forbidden", "Archives are not accepted as native members")
    descriptor = meta["descriptor"]
    if descriptor is not None:
        offset = native.native_header(head, descriptor, count)
        digest = hashlib.sha256()
        stream.seek(offset)
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
        if digest.hexdigest() != descriptor["data_sha256"]:
            raise ValueError("joint_member_data_digest")
    elif meta["name"] in ("request.json", "sealed.json"):
        stream.seek(0)
        raw = stream.read(native.MAX_JSON + 1)
        if len(raw) > native.MAX_JSON:
            raise ValueError("joint_member_json_cap")
        native.manifest(raw, meta["role"])
    elif meta["name"].endswith(".json"):
        stream.seek(0)
        raw = stream.read(native.MAX_JSON + 1)
        if len(raw) > native.MAX_JSON or type(native.bounded_json(raw)) is not dict:
            raise ValueError("joint_member_correction_object")


def _directory_state(files, key):
    parent, name = files._parent(key)
    try:
        try:
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return False
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("physical_private_directory")
        files.private_directory_identity(key)
        return True
    finally:
        os.close(parent)


def _ensure_parent_dirs(files, target: str) -> list[str]:
    parts = target.split("/")[:-1]
    created = []
    prefix = ""
    try:
        for part in parts:
            prefix = f"{prefix}/{part}".lstrip("/")
            # The first parent is the private root; each later parent is
            # created only after the preceding directory has been verified.
            if not _directory_state(files, prefix):
                created.append(prefix)
                files.create_directory(prefix)
        return created
    except BaseException:
        _remove_empty_dirs(files, created)
        raise


def _remove_empty_dirs(files, paths: list[str]) -> None:
    for key in reversed(paths):
        parent, name = files._parent(key)
        try:
            try:
                os.rmdir(name, dir_fd=parent)
                os.fsync(parent)
            except FileNotFoundError:
                pass
        finally:
            os.close(parent)


def _remove_new_file(files, key: str, cap: int) -> None:
    try:
        body = files.read(key, cap=cap)
    except FileNotFoundError:
        return
    files.remove(key, cap=cap, expected_bytes=len(body), expected_sha256=byte_sha(body))


def _dataset_receipt(dataset_id, project_id, raw_asset_id, row_count, digest):
    return {"dataset_id": dataset_id, "project_id": project_id, "raw_asset_id": raw_asset_id,
        "parser_version": native.PARSER, "modality": native.MODALITY, "row_count": row_count,
        "sha256": digest, "qc_verdict": "structural_native_members_only", "scientific_accepted": False,
        "receipt_url": f"/api/projects/{project_id}/joint-datasets/{dataset_id}"}


def _root_time_micros(value):
    stamp = value.astimezone(timezone.utc)
    epoch = stamp.replace(year=1970, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    delta = stamp - epoch
    micros = delta.days * 86400000000 + delta.seconds * 1000000 + delta.microseconds
    if not 0 <= micros <= 9007199254740991:
        raise ValueError("joint_root_timestamp")
    return micros, stamp.replace(tzinfo=None).isoformat(sep=" ")


async def _insert_dataset_root(session, dataset, payload):
    """M11's exact allocated root tuple, using current branch SQL contracts."""
    if (await session.execute(text("PRAGMA foreign_keys"))).scalar_one() != 1:
        raise ValueError("joint_root_foreign_keys_required")
    revision = (await session.execute(text("SELECT version_num FROM alembic_version"))).scalars().all()
    if revision != ["0006_joint_artifacts"]:
        raise ValueError("joint_root_exact_allocated_head_required")
    ddl = (await session.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='observation_datasets'"))).scalar_one()
    if ddl.count("(kind='root' AND parser_version='m11-native-members/v1'") != 1:
        raise ValueError("joint_root_exact_dictionary_required")
    namespace = SimpleNamespace(**dataset)
    dataset_contract.validate_dataset(payload, namespace)
    micros, created = _root_time_micros(dataset["created_at"])
    await session.execute(text(
        "INSERT INTO physical_dataset_families (root_dataset_id,raw_asset_id,project_id,owner_id,parser_version,state,next_ordinal,published_count,reserved_count,created_us) "
        "VALUES (:id,:raw_asset_id,:project_id,:owner_id,:parser_version,'published',2,1,0,:micros)"),
        {"id": dataset["id"], "raw_asset_id": dataset["raw_asset_id"], "project_id": dataset["project_id"],
         "owner_id": dataset["owner_id"], "parser_version": native.PARSER, "micros": micros})
    await session.execute(text(
        "INSERT INTO observation_datasets (id,project_id,owner_id,raw_asset_id,version,parser_version,modality,row_count,raw_sha256,sha256,byte_count,storage_key,created_at,kind,root_dataset_id,parent_dataset_id,payload_schema) "
        "VALUES (:id,:project_id,:owner_id,:raw_asset_id,1,:parser,:modality,:rows,:raw_sha,:sha,:bytes,:key,:created,'root',:id,NULL,:schema)"),
        {"id": dataset["id"], "project_id": dataset["project_id"], "owner_id": dataset["owner_id"],
         "raw_asset_id": dataset["raw_asset_id"], "parser": native.PARSER, "modality": native.MODALITY,
         "rows": dataset["row_count"], "raw_sha": dataset["raw_sha256"], "sha": dataset["sha256"],
         "bytes": dataset["byte_count"], "key": dataset["storage_key"], "created": created,
         "schema": DATASET_SCHEMA})


def install_joint_routes(app, settings, current_user, get_session):
    router = APIRouter(prefix="/api/projects", tags=["joint-native"])

    @router.post("/{project_id}/joint-members", status_code=201, response_model=RawAssetView)
    async def upload_member(project_id: str, request: Request, user: User = Depends(current_user),
                            session: AsyncSession = Depends(get_session)):
        physical = _physical(request, session)
        owner_id = user.id
        await _owned_project(session, project_id, user)
        await session.rollback()
        await session.execute(text("BEGIN"))
        await _registered_0006(session)
        await session.rollback()
        try:
            raw_meta = request.headers.get("x-joint-member-metadata", "").encode("utf-8")
            meta = native.member_metadata(raw_meta)
            source_input = SourceInput.model_validate(meta["source"])
        except (ValueError, UnicodeError, ValidationError) as error:
            raise ApiError(422, "joint_member_metadata_invalid", "Native member metadata is invalid") from error
        if source_input.rights_decision == "forbidden":
            raise ApiError(422, "rights_forbidden", "Forbidden sources cannot be stored")
        if (not source_input.provider.strip() or len(source_input.rights_statement.strip()) < 10
                or not source_input.attribution.strip()):
            raise ApiError(422, "joint_member_rights_invalid", "Provider, rights basis, and attribution must be explicit")
        if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/octet-stream":
            raise ApiError(415, "mime_format_mismatch", "Native members require binary transport")
        limit = min(settings.max_upload_bytes, native.MAX_BYTES, source_input.expected_bytes or 0)
        length = request.headers.get("content-length")
        if (source_input.expected_bytes is None or source_input.expected_sha256 is None or limit < 1
                or source_input.expected_bytes > limit or (length and
                (not length.isdigit() or int(length) != source_input.expected_bytes or int(length) > limit))):
            raise ApiError(413, "upload_too_large", "Native member exceeds its declared byte bound")
        await session.rollback()
        async with request.app.state.sessions() as rate_session:
            await _member_rate(rate_session, owner_id)
        staged = None
        try:
            with tempfile.TemporaryFile(mode="w+b") as stage:
                stage_info = os.fstat(stage.fileno())
                if (not stat.S_ISREG(stage_info.st_mode) or stage_info.st_nlink not in (0, 1)
                        or (os.name == "posix" and stat.S_IMODE(stage_info.st_mode) & 0o077)):
                    raise ApiError(409, "joint_member_stage_unsafe", "Private upload staging is unavailable")
                digest = hashlib.sha256()
                count = 0
                async for chunk in request.stream():
                    count += len(chunk)
                    if count > limit:
                        raise ApiError(413, "upload_too_large", "Native member exceeds its declared byte bound")
                    digest.update(chunk)
                    await asyncio.to_thread(stage.write, chunk)
                await asyncio.to_thread(stage.flush)
                await asyncio.to_thread(os.fsync, stage.fileno())
                if count != source_input.expected_bytes or digest.hexdigest() != source_input.expected_sha256.lower():
                    raise ApiError(422, "joint_member_digest_mismatch", "Native member differs from its original receipt")
                try:
                    await asyncio.to_thread(_member_envelope, stage, meta, count)
                except (ValueError, TypeError, KeyError, UnicodeError) as error:
                    raise ApiError(422, "joint_member_native_invalid", "Native member metadata or data digest is invalid") from error
                stage.seek(0)
                staged = os.fdopen(os.dup(stage.fileno()), "rb", closefd=True)

            await session.rollback()
            await session.execute(text("BEGIN IMMEDIATE"))
            await session.refresh(user)
            await _registered_0006(session)
            physical.leases.require_held()
            await _owned_project(session, project_id, user)
            version = (await session.execute(select(func.max(SourceRecord.version)).where(
                SourceRecord.owner_id == owner_id, SourceRecord.project_id == project_id,
                SourceRecord.original_filename == meta["name"]))).scalar_one() or 0
            now = utcnow()
            asset_id, source_id = str(uuid4()), str(uuid4())
            storage_key = f"projects/{owner_id}/{project_id}/{asset_id}"
            source = SourceRecord(id=source_id, project_id=project_id, owner_id=owner_id,
                original_filename=meta["name"], version=version + 1, provider=source_input.provider,
                exact_url=None, doi=source_input.doi, citation=source_input.citation, retrieved_at=now,
                rights_statement=source_input.rights_statement, rights_decision=source_input.rights_decision,
                private_storage_permission="attested", declared_format="joint_native", expected_bytes=count,
                sha256=digest.hexdigest(), attribution=source_input.attribution)
            asset = RawAsset(id=asset_id, project_id=project_id, owner_id=owner_id, source_id=source_id,
                filename=meta["name"], client_mime="application/octet-stream", detected_format="joint_native",
                byte_count=count, sha256=digest.hexdigest(), storage_key=storage_key,
                physical_metadata={"schema": "joint-native-member-1", "role": meta["role"],
                    "name": meta["name"], "descriptor": meta["descriptor"],
                    "scientific_values_decoded": False, "scientific_accepted": False},
                validation_status="raw_metadata_checked", created_at=now)
            usage = (await session.execute(select(AccountUsage).where(AccountUsage.user_id == owner_id))).scalar_one_or_none()
            if usage is None:
                usage = AccountUsage(user_id=owner_id, raw_bytes=0)
                session.add(usage)
            usage.raw_bytes += count
            session.add(source)
            await session.flush([source])
            session.add(asset)
            await session.flush()
            created_dirs = _ensure_parent_dirs(physical.leases.files, storage_key)
            file_attempted = False
            commit_attempted = committed = False
            try:
                file_attempted = True
                try:
                    physical.leases.files.write_new_stream(storage_key, staged, cap=limit,
                        expected_bytes=count, expected_sha256=digest.hexdigest())
                except FileExistsError:
                    file_attempted = False
                    raise
                proof = await _classify(session, physical)
                _require_quota(proof, owner_id, settings.account_quota_bytes)
                physical.leases.require_held()
                commit_attempted = True
                await session.commit()
                committed = True
                return asset_view(asset, source)
            finally:
                if not committed:
                    await session.rollback()
                    if not commit_attempted:
                        if file_attempted:
                            _remove_new_file(physical.leases.files, storage_key, limit)
                        _remove_empty_dirs(physical.leases.files, created_dirs)
        except ApiError:
            raise
        except (ValueError, OSError, TypeError, KeyError) as error:
            raise ApiError(409, "joint_member_custody_unresolved", "M11 member custody could not be published safely") from error
        finally:
            if staged is not None:
                staged.close()

    @router.post("/{project_id}/joint-datasets", status_code=201)
    async def create_dataset(project_id: str, request: Request, user: User = Depends(current_user),
                             session: AsyncSession = Depends(get_session)):
        physical = _physical(request, session)
        owner_id = user.id
        await _owned_project(session, project_id, user)
        await session.rollback()
        await session.execute(text("BEGIN"))
        await _registered_0006(session)
        await session.rollback()
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > REQUEST_CAP:
                raise ApiError(413, "joint_dataset_request_cap", "Native dataset source map exceeds its byte bound")
            raw.extend(chunk)
        try:
            members = member_request(bytes(raw))
        except (ValueError, TypeError, KeyError, UnicodeError) as error:
            raise ApiError(422, "joint_dataset_members_invalid", "Native dataset source map is invalid") from error
        await session.rollback()
        await session.execute(text("BEGIN IMMEDIATE"))
        await session.refresh(user)
        await _registered_0006(session)
        await _owned_project(session, project_id, user)
        files = physical.leases.files
        bindings, manifests = {}, {}
        primary = None
        total = 0
        try:
            for role, names in members.items():
                for name, asset_id in names.items():
                    asset, source = await _owned_asset(session, project_id, asset_id, user)
                    binding = native.source_identity(asset, source, owner_id=owner_id, project_id=project_id)
                    meta = asset.physical_metadata
                    if (asset.storage_key != f"projects/{owner_id}/{project_id}/{asset.id}"
                            or asset.detected_format != "joint_native" or asset.filename != name or type(meta) is not dict
                            or set(meta) != {"schema", "role", "name", "descriptor", "scientific_values_decoded", "scientific_accepted"}
                            or meta != {"schema": "joint-native-member-1", "role": role, "name": name,
                                "descriptor": meta.get("descriptor"), "scientific_values_decoded": False,
                                "scientific_accepted": False}):
                        raise ValueError("joint_source_member_binding")
                    descriptor = meta["descriptor"]
                    native.member_metadata(canonical({"role": role, "name": name, "descriptor": descriptor,
                        "source": {"expected_bytes": asset.byte_count, "expected_sha256": asset.sha256}}))
                    if total + asset.byte_count > native.MAX_BYTES:
                        raise ValueError("joint_dataset_total_bytes")
                    total += asset.byte_count
                    files.scan_joint_member(asset.storage_key, byte_count=asset.byte_count,
                                            sha256=asset.sha256, descriptor=descriptor)
                    binding["descriptor"] = descriptor
                    bindings.setdefault(role, {})[name] = binding
                    if name in ("request.json", "sealed.json"):
                        raw_manifest = files.read(asset.storage_key, cap=INDEX_CAP, expected_bytes=asset.byte_count,
                                                  expected_sha256=asset.sha256)
                        manifests[role] = native.bounded_json(raw_manifest)
                    if role == "development" and name == "request.json":
                        primary = asset
            if set(manifests) != {"development", "sealed"} or primary is None:
                raise ValueError("joint_dataset_manifest_required")
            identity = str(uuid4())
            payload = {"schema": DATASET_SCHEMA, "dataset_id": identity, "version": 1,
                "owner_id": str(owner_id), "project_id": project_id, "raw_asset_id": primary.id,
                "parent_raw_sha256": primary.sha256, "parser_version": native.PARSER,
                "modality": native.MODALITY, "dimensions": {}, "manifests": manifests, "members": bindings,
                "qc_verdict": "structural_native_members_only", "scientific_values_decoded": False,
                "scientific_accepted": False}
            row_count = dataset_contract.close_manifests(payload)
            payload["dimensions"] = {"source_observations": row_count}
            encoded = canonical(payload)
            if len(encoded) > INDEX_CAP:
                raise ApiError(413, "joint_dataset_index_cap", "Native dataset index exceeds its byte bound")
            existing = (await session.execute(select(ObservationDataset.id).where(
                ObservationDataset.raw_asset_id == primary.id, ObservationDataset.parser_version == native.PARSER))).scalar_one_or_none()
            if existing is not None:
                raise ApiError(409, "dataset_exists", "This native request already has an immutable dataset")
            now = utcnow()
            storage_key = f"derived/{owner_id}/{project_id}/datasets/{identity}.json"
            dataset_row = {"id": identity, "owner_id": str(owner_id), "project_id": project_id,
                "raw_asset_id": primary.id, "version": 1, "parser_version": native.PARSER,
                "modality": native.MODALITY, "row_count": row_count, "raw_sha256": primary.sha256,
                "sha256": byte_sha(encoded), "byte_count": len(encoded), "storage_key": storage_key,
                "created_at": now}
            created_dirs = _ensure_parent_dirs(files, storage_key)
            file_attempted = commit_attempted = committed = False
            try:
                file_attempted = True
                try:
                    files.write_new(storage_key, encoded, cap=INDEX_CAP)
                except FileExistsError:
                    file_attempted = False
                    raise
                await _insert_dataset_root(session, dataset_row, payload)
                for role, role_members in bindings.items():
                    for name, binding in role_members.items():
                        await session.execute(text(
                            "INSERT INTO joint_dataset_sources (dataset_id,role,name,asset_id,source_id,raw_sha256,raw_bytes,source_version) "
                            "VALUES (:dataset,:role,:name,:asset,:source,:sha,:bytes,:version)"),
                            {"dataset": identity, "role": role, "name": name, "asset": binding["asset_id"],
                             "source": binding["source_id"], "sha": binding["raw_sha256"],
                             "bytes": binding["raw_bytes"], "version": binding["source_version"]})
                await session.flush()
                proof = await _classify(session, physical)
                _require_quota(proof, owner_id, settings.account_quota_bytes)
                physical.leases.require_held()
                commit_attempted = True
                await session.commit()
                committed = True
                return _dataset_receipt(identity, project_id, primary.id, row_count, dataset_row["sha256"])
            finally:
                if not committed:
                    await session.rollback()
                    if not commit_attempted:
                        if file_attempted:
                            _remove_new_file(files, storage_key, INDEX_CAP)
                        _remove_empty_dirs(files, created_dirs)
        except ApiError:
            raise
        except (ValueError, OSError, TypeError, KeyError) as error:
            raise ApiError(422, "joint_dataset_original_invalid", "Native originals or their custody bindings are invalid") from error

    @router.get("/{project_id}/joint-datasets/{dataset_id}")
    async def get_dataset(project_id: str, dataset_id: str, request: Request,
                          user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
        physical = _physical(request, session)
        owner_id = user.id
        await _owned_project(session, project_id, user)
        await session.rollback()
        await session.execute(text("BEGIN"))
        await _registered_0006(session)
        dataset = (await session.execute(text(
            "SELECT id,owner_id,project_id,raw_asset_id,row_count,sha256,byte_count,storage_key,parser_version,modality "
            "FROM observation_datasets WHERE id=:id AND owner_id=:owner AND project_id=:project AND parser_version=:parser AND modality=:modality"),
            {"id": dataset_id, "owner": str(owner_id), "project": project_id,
             "parser": native.PARSER, "modality": native.MODALITY})).mappings().one_or_none()
        if dataset is None:
            raise ApiError(404, "not_found", "Native dataset not found")
        proof = await _classify(session, physical)
        if str(owner_id) not in proof.account_charges:
            raise ApiError(409, "joint_custody_unresolved", "M11 custody cannot be proven from the current snapshot")
        return JSONResponse(_dataset_receipt(dataset["id"], dataset["project_id"], dataset["raw_asset_id"],
                                dataset["row_count"], dataset["sha256"]), headers={"Cache-Control": "no-store"})

    app.include_router(router)
