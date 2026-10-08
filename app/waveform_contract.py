"""Strict structural waveform indexing; no scientific engine or native calls."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.errors import ApiError

# Path-owned stdlib scanner, not a package or a configurable provider.
_spec = importlib.util.spec_from_file_location(
    "_m08_structural_input", Path(__file__).resolve().parents[1] / "data-pipeline" / "waveform_input.py"
)
INPUT = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(INPUT)

METHOD_ID = "seismic.waveform-qc-classical/v1"
MODALITY = "waveform_counts_response"
PARSER = "m08-counts-response/v1"
SCRATCH = 52690944
MEMORY = 1073741824  # Experimental committed-memory/charge limit, NOT RSS admission.
WALL = 120
IMPLEMENTATION_FILES = (
    "scripts/waveform_m08_windows.py", "scripts/waveform_m08_files.py", "scripts/waveform_m08_export.py",
    "scripts/waveform_m08_child.py", "scripts/process_waveform_m08.py", "data-pipeline/waveform_input.py",
    "data-pipeline/waveform_processing.py", "data-pipeline/waveform_evaluation.py", "app/waveform_contract.py",
    "app/waveform_processing.py", "app/waveform_worker.py", "app/waveform_result.py",
)


def implementation_sha256():
    root = Path(__file__).resolve().parents[1]
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in IMPLEMENTATION_FILES}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
ARRAY_NAMES = (
    "counts",
    "physical_native",
    "filtered_native",
    "edge_valid",
    "time_taper",
    "response_frequency_hz",
    "response_real",
    "response_imag",
    "inverse_real",
    "inverse_imag",
    "prefilter_weight",
    "characteristic",
    "psd_frequency_hz",
    "counts_psd",
    "physical_psd",
    "filtered_psd",
    "filter_sos",
)
MEMBER = re.compile(
    r"(?:calculation|evaluation|receipt|manifest)\.json\Z|c0[0-2]-(?:" + "|".join(ARRAY_NAMES) + r")\.bin\Z"
)


class WaveformParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    scientific_request_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


def request_identity(request):
    try:
        value = INPUT.validate_request(request)
        if value["source"]["rights"] not in ("private-use-attested", "reviewed-public-scsn"):
            raise ValueError()
        raw = INPUT.scientific_identity(value)
        # The ordinary helper returns a SHA; retain exact native request separately.
        return value, raw
    except (INPUT.WaveformInputError, ValueError, TypeError):
        raise ApiError(
            422, "waveform_request_invalid", "Waveform scientific request is invalid", ["waveform_request"]
        ) from None


def parser_version(request_sha):
    return "m08/v1/" + request_sha


def source_identity(asset, source):
    if (
        source.private_storage_permission != "attested"
        or source.rights_decision == "forbidden"
        or source.sha256 != asset.sha256
        or source.id != asset.source_id
        or source.owner_id != asset.owner_id
        or source.project_id != asset.project_id
    ):
        raise ApiError(422, "waveform_source_ineligible", "Waveform source attestation or identity is invalid")
    return {
        "asset_id": asset.id,
        "source_id": source.id,
        "source_version": source.version,
        "raw_sha256": asset.sha256,
        "raw_bytes": asset.byte_count,
        "rights_decision": source.rights_decision,
        "private_storage_permission": "attested",
    }


def index_pair(mseed, xml, request, *, dataset_id, owner_id, project_id, raw_pair):
    value, digest = request_identity(request)
    try:
        rows = INPUT.scan_miniseed(mseed, value)
        INPUT.scan_stationxml(xml)
        sources = {role: source_identity(*pair) for role, pair in raw_pair.items()}
        for role, body in (("miniseed", mseed), ("stationxml", xml)):
            if (
                len(body) != sources[role]["raw_bytes"]
                or hashlib.sha256(body).hexdigest() != sources[role]["raw_sha256"]
            ):
                raise ValueError()
        if value["source"]["declared_sha256"] not in (None, sources["miniseed"]["raw_sha256"]):
            raise ValueError()
        return {
            "schema": "geophysics.waveform-dataset/v1",
            "dataset_id": dataset_id,
            "version": 1,
            "owner_id": owner_id,
            "project_id": project_id,
            "raw_asset_id": sources["miniseed"]["asset_id"],
            "parent_raw_sha256": sources["miniseed"]["raw_sha256"],
            "parser_version": parser_version(digest),
            "modality": MODALITY,
            "dimensions": {
                "channel": len(value["channels"]),
                "sample": sum(r["npts"] for r in rows),
                "record": len(rows),
            },
            "sources": sources,
            "request": value,
            "scientific_request_sha256": digest,
            "qc_verdict": "structural_index_not_physical_qc",
        }
    except (INPUT.WaveformInputError, ValueError, TypeError):
        raise ApiError(
            422, "waveform_input_invalid", "Waveform input is malformed or outside the fixed envelope"
        ) from None


def validate_dataset(payload, dataset):
    expected = set(
        "schema dataset_id version owner_id project_id raw_asset_id parent_raw_sha256 parser_version modality dimensions sources request scientific_request_sha256 qc_verdict".split()
    )
    try:
        if type(payload) is not dict or set(payload) != expected:
            raise ValueError()
        value, digest = request_identity(payload["request"])
        sources = payload["sources"]
        if (
            set(sources) != {"miniseed", "stationxml"}
            or payload["schema"] != "geophysics.waveform-dataset/v1"
            or payload["dataset_id"] != dataset.id
            or payload["version"] != dataset.version
            or payload["owner_id"] != str(dataset.owner_id)
            or payload["project_id"] != dataset.project_id
            or payload["raw_asset_id"] != dataset.raw_asset_id
            or payload["parent_raw_sha256"] != dataset.raw_sha256
            or payload["modality"] != MODALITY
            or dataset.modality != MODALITY
            or payload["parser_version"] != parser_version(digest)
            or dataset.parser_version != payload["parser_version"]
            or payload["scientific_request_sha256"] != digest
            or payload["qc_verdict"] != "structural_index_not_physical_qc"
        ):
            raise ValueError()
        dims = payload["dimensions"]
        if (
            set(dims) != {"channel", "sample", "record"}
            or any(type(n) is not int for n in dims.values())
            or dims["channel"] != len(value["channels"])
            or dims["sample"] != dataset.row_count
            or not 1 <= dims["sample"] <= 180000
            or not 1 <= dims["record"] <= 4096
        ):
            raise ValueError()
        for role, row in sources.items():
            if set(row) != {
                "asset_id",
                "source_id",
                "source_version",
                "raw_sha256",
                "raw_bytes",
                "rights_decision",
                "private_storage_permission",
            }:
                raise ValueError()
            UUID(row["asset_id"])
            UUID(row["source_id"])
            if (
                type(row["source_version"]) is not int
                or row["source_version"] < 1
                or type(row["raw_bytes"]) is not int
                or not 1 <= row["raw_bytes"] <= (16777216 if role == "miniseed" else 2097152)
                or not re.fullmatch("[a-f0-9]{64}", row["raw_sha256"])
                or row["rights_decision"] not in ("mirror", "provider-link-only", "derivative-only")
                or row["private_storage_permission"] != "attested"
            ):
                raise ValueError()
        if (
            sources["miniseed"]["asset_id"] != dataset.raw_asset_id
            or sources["miniseed"]["raw_sha256"] != dataset.raw_sha256
        ):
            raise ValueError()
    except (KeyError, ValueError, TypeError, ApiError):
        raise ApiError(409, "derived_integrity_failed", "Waveform dataset identity or contract changed") from None


def artifact_key(owner, project, job, name):
    for item in (owner, project, job):
        if str(UUID(item)) != item:
            raise ApiError(409, "derived_integrity_failed", "Waveform artifact identity is invalid")
    if type(name) is not str or MEMBER.fullmatch(name) is None:
        raise ApiError(409, "derived_integrity_failed", "Waveform artifact name is invalid")
    return f"derived/{owner}/{project}/waveforms/{job}/{name}"


def artifact_path(settings, key):
    parts = key.split("/")
    if (
        len(parts) != 6
        or parts[0] != "derived"
        or parts[3] != "waveforms"
        or artifact_key(parts[1], parts[2], parts[4], parts[5]) != key
    ):
        raise ApiError(409, "derived_integrity_failed", "Waveform artifact key is invalid")
    path = settings.data_dir.joinpath(*parts)
    for p in (path, *path.parents):
        if p == settings.data_dir:
            break
        if p.is_symlink() or (p.exists() and getattr(p.lstat(), "st_file_attributes", 0) & 0x400):
            raise ApiError(409, "derived_integrity_failed", "Waveform artifact path is unsafe")
    return path


def context_path(settings):
    # Server/operator supplied, never a request path or an environment provider hook.
    return settings.data_dir / ".waveform-context" / "context.json"


def context_available(settings):
    path = context_path(settings)
    if not path.is_file() or path.is_symlink() or path.parent.is_symlink() or not 0 < path.stat().st_size <= 65536:
        return False
    try:
        context = INPUT.bounded_json(path.read_bytes(), 65536)
        return (
            set(context) == {"schema", "platform", "python", "python_sha256", "admission_path", "admission_sha256"}
            and context["schema"] == "geophysics.waveform-worker-context/v1"
            and os.name == "nt" and context["platform"] == "windows"
            and all(
                type(context[k]) is str and re.fullmatch("[a-f0-9]{64}", context[k])
                for k in ("python_sha256", "admission_sha256")
            )
        )
    except (INPUT.WaveformInputError, TypeError, ValueError, OSError):
        return False
