"""Owned additive protected waveform dataset and result service."""

from __future__ import annotations
import asyncio
import os
import uuid

from sqlalchemy import select

from app.errors import ApiError
from app.models import AccountUsage, ObservationDataset, WaveformDatasetSource, utcnow
from app.processing_contract import canonical_bytes, checked_derived_path, dataset_key, sha256
from app.processing_storage import account_derived_usage
from app.waveform_contract import index_pair, request_identity, parser_version, MODALITY


async def create_waveform_dataset(settings, session, user, project_id, asset, source, request):
    from app.projects import _owned_asset, _verified_file

    if request is None:
        raise ApiError(
            422,
            "waveform_request_required",
            "Waveform indexing requires an explicit scientific request",
            ["waveform_request"],
        )
    value, digest = request_identity(request)
    companion = asset.physical_metadata.get("geometry", {}).get("stationxml_asset_id")
    xml, xml_source = await _owned_asset(session, project_id, companion, user)
    if xml.detected_format != "stationxml":
        raise ApiError(422, "stationxml_missing", "Waveform companion must be the exact owned StationXML asset")
    existing = (
        await session.execute(
            select(ObservationDataset).where(
                ObservationDataset.raw_asset_id == asset.id, ObservationDataset.parser_version == parser_version(digest)
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ApiError(409, "dataset_exists", "This raw pair and scientific request already have an immutable index")
    from app.waveform_contract import source_identity

    source_identity(asset, source)
    source_identity(xml, xml_source)
    if not 1 <= asset.byte_count <= 16777216 or not 1 <= xml.byte_count <= 2097152:
        raise ApiError(413, "waveform_input_limit", "Waveform source exceeds the fixed byte envelope")
    paths = [await asyncio.to_thread(_verified_file, settings, a) for a in (asset, xml)]
    raw, raw_xml = await asyncio.to_thread(read_original_pair, paths, (asset, xml))
    dataset_id = str(uuid.uuid4())
    payload = index_pair(
        raw,
        raw_xml,
        value,
        dataset_id=dataset_id,
        owner_id=str(user.id),
        project_id=project_id,
        raw_pair={"miniseed": (asset, source), "stationxml": (xml, xml_source)},
    )
    encoded = canonical_bytes(payload)
    if len(encoded) > 2097152:
        raise ApiError(413, "waveform_index_limit", "Waveform structural index exceeds the metadata cap")
    raw_usage = (
        await session.execute(select(AccountUsage.raw_bytes).where(AccountUsage.user_id == user.id))
    ).scalar_one_or_none() or 0
    if raw_usage + await account_derived_usage(session, user.id) + len(encoded) > settings.account_quota_bytes:
        raise ApiError(507, "account_quota_exceeded", "Account private-byte quota exceeded")
    key = dataset_key(str(user.id), project_id, dataset_id)
    target = checked_derived_path(settings, key)
    target.parent.mkdir(parents=True, exist_ok=True)
    commit_attempted = False
    created = False
    try:
        with target.open("xb") as handle:
            created = True
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        row = ObservationDataset(
            id=dataset_id,
            project_id=project_id,
            owner_id=user.id,
            raw_asset_id=asset.id,
            version=1,
            parser_version=payload["parser_version"],
            modality=MODALITY,
            row_count=payload["dimensions"]["sample"],
            raw_sha256=asset.sha256,
            sha256=sha256(encoded),
            byte_count=len(encoded),
            storage_key=key,
            created_at=utcnow(),
        )
        session.add(row)
        await session.flush()
        for role, binding in payload["sources"].items():
            session.add(
                WaveformDatasetSource(
                    dataset_id=dataset_id,
                    role=role,
                    **{
                        key: binding[key]
                        for key in ("asset_id", "source_id", "source_version", "raw_sha256", "raw_bytes")
                    },
                )
            )
        commit_attempted = True
        await session.commit()
        return row
    except Exception:
        await session.rollback()
        if created and not commit_attempted:
            target.unlink()
        raise


async def validate_source_rows(session, settings, dataset, payload):
    """Revalidate both durable dependencies and actual originals before execution."""
    from app.models import RawAsset, SourceRecord
    from app.projects import _verified_file
    from app.waveform_contract import source_identity

    rows = (
        (await session.execute(select(WaveformDatasetSource).where(WaveformDatasetSource.dataset_id == dataset.id)))
        .scalars()
        .all()
    )
    if len(rows) != 2 or {row.role for row in rows} != {"miniseed", "stationxml"}:
        raise ApiError(409, "waveform_source_changed", "Waveform source dependencies are incomplete")
    paths = {}
    for row in rows:
        pair = (
            await session.execute(
                select(RawAsset, SourceRecord)
                .join(SourceRecord, RawAsset.source_id == SourceRecord.id)
                .where(
                    RawAsset.id == row.asset_id,
                    RawAsset.owner_id == dataset.owner_id,
                    RawAsset.project_id == dataset.project_id,
                )
            )
        ).one_or_none()
        if pair is None:
            raise ApiError(409, "waveform_source_changed", "Waveform original dependency is absent")
        asset, source = pair
        binding = payload["sources"][row.role]
        if (
            source_identity(asset, source) != binding
            or any(
                getattr(row, k) != binding[k]
                for k in ("asset_id", "source_id", "source_version", "raw_sha256", "raw_bytes")
            )
            or asset.detected_format != ("miniseed" if row.role == "miniseed" else "stationxml")
        ):
            raise ApiError(409, "waveform_source_changed", "Waveform original dependency changed")
        if (
            row.role == "miniseed"
            and asset.physical_metadata.get("geometry", {}).get("stationxml_asset_id")
            != payload["sources"]["stationxml"]["asset_id"]
        ):
            raise ApiError(409, "waveform_source_changed", "Waveform companion relation changed")
        paths[row.role] = await asyncio.to_thread(_verified_file, settings, asset)
    return paths


def read_original_pair(paths, assets):
    """Hash the bounded bytes actually indexed while original handles are held."""
    from contextlib import ExitStack
    import app.waveform_result  # noqa: F401 -- registers the fixed ordinary helper path.
    from waveform_m08_files import open_input
    from waveform_input import WaveformInputError

    try:
        with ExitStack() as held:
            handles = [held.enter_context(open_input(path, cap))
                       for path, cap in zip(paths, (16777216, 2097152), strict=True)]
            values = [handle.read_bytes() for handle in handles]
            if any(len(raw) != asset.byte_count or sha256(raw) != asset.sha256
                   for raw, asset in zip(values, assets, strict=True)):
                raise ValueError("original changed")
            return values
    except (OSError, ValueError, WaveformInputError):
        raise ApiError(409, "raw_integrity_failed", "Waveform original differs from its receipt") from None
