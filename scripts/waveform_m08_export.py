"""Bounded ordinary waveform export/reopen; not runtime/resource authority."""

from dataclasses import dataclass
import hashlib
import json
import math
import re
import struct

from waveform_input import bounded_json, exact_bytes, native_precount, fail, keys, sha
from waveform_evaluation import ARRAY_NAMES, SealedWaveform, seal_result, _sealed_metadata, evaluate_waveform_candidates

TOTAL_CAP = 33554432
JSON_CAP = 2097152
CHUNK = 65536
SCHEMA = "caos.local-waveform-export.v1"
_ARRAY_PATTERN = re.compile(r"c0[0-2]-(?:" + "|".join(map(re.escape, sorted(ARRAY_NAMES))) + r")\.bin\Z")


def _name(value):
    if type(value) is not str or not (
        value in ("calculation.json", "evaluation.json", "receipt.json", "manifest.json", "manifest.pending")
        or _ARRAY_PATTERN.fullmatch(value)
    ):
        fail("waveform_contract")
    return value


def _canonical(value, cap):
    native_precount(value, cap, max_nodes=2097152, max_depth=16)
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode(
        "ascii"
    )
    if len(encoded) > cap:
        fail("waveform_limit")
    return encoded


@dataclass(frozen=True)
class Member:
    name: str
    bytes: int
    sha256: str
    data: bytes | memoryview


@dataclass(frozen=True)
class ExportPlan:
    members: tuple
    manifest: bytes
    total_bytes: int
    calculation_sha256: str

    @property
    def names(self):
        return tuple(member.name for member in self.members)


def _same_native(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_same_native(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same_native(a, b) for a, b in zip(left, right))
    return left == right


def _evaluation(raw, calculation_sha256, metadata):
    value = bounded_json(raw, JSON_CAP, max_nodes=2097152, max_depth=16)
    if (
        type(value) is not dict
        or value.get("schema") != "caos.local-waveform-evaluation.v1"
        or value.get("sealed_calculation_sha256") != calculation_sha256
        or value.get("status") not in ("evaluated", "not_evaluable")
    ):
        fail("waveform_contract")
    keys(
        value,
        "schema status sealed_calculation_sha256 reference_json_raw_bytes reference_json_raw_sha256 "
        "original_reference_parent_sha256 event_id matching_policy tolerance_s references reference_count "
        "reference_status_counts matched_reference_fraction median_absolute_residual_s unmatched_candidate_count "
        "reference_rights_declaration field_truth method_accepted provider_verified",
    )
    if (
        type(value["references"]) is not list
        or len(value["references"]) > 128
        or type(value["reference_json_raw_bytes"]) is not int
        or not 0 < value["reference_json_raw_bytes"] <= 1048576
        or type(value["reference_json_raw_sha256"]) is not str
        or not re.fullmatch("[a-f0-9]{64}", value["reference_json_raw_sha256"])
    ):
        fail("waveform_contract")
    refs = []
    for row in value["references"]:
        keys(row, "reference status candidate_index signed_residual_s")
        refs.append(row["reference"])
    reference = {
        "schema": "caos.waveform-analyst-references.v1",
        "event_id": value["event_id"],
        "source": {
            "raw_sha256": value["original_reference_parent_sha256"],
            "citation": "Bounded exported reference rows, not authenticated original source",
            "rights": value["reference_rights_declaration"],
        },
        "selection_sealed_before_scoring": True,
        "references": refs,
    }
    # Recompute matching, not scientific prediction or provenance authentication.
    replay = evaluate_waveform_candidates(
        SealedWaveform(_canonical(metadata, JSON_CAP), calculation_sha256), _canonical(reference, 1048576)
    )
    for key in value:
        if key not in ("reference_json_raw_bytes", "reference_json_raw_sha256") and not _same_native(
            value[key], replay[key]
        ):
            fail("waveform_contract")
    return value


def plan_export(result, sealed, *, evaluation=None):
    if type(sealed) is not SealedWaveform:
        fail("waveform_type")
    actual = seal_result(result)
    if actual != sealed:
        fail("waveform_contract")
    members = [
        Member("calculation.json", len(actual.metadata_bytes), sha(actual.metadata_bytes), actual.metadata_bytes)
    ]
    for descriptor in result.metadata["array_descriptors"]:
        name = _name(f"c{descriptor['channel_index']:02d}-{descriptor['name']}.bin")
        data = memoryview(result.arrays[(descriptor["channel_index"], descriptor["name"])]).cast("B")
        members.append(Member(name, descriptor["bytes"], descriptor["sha256"], data))
    if evaluation is not None:
        exact_bytes(evaluation, JSON_CAP)
        _evaluation(evaluation, sealed.calculation_sha256, result.metadata)
        members.append(Member("evaluation.json", len(evaluation), sha(evaluation), evaluation))
    receipt = _canonical(
        {
            "schema": "caos.local-waveform-export-receipt.v1",
            "status": result.metadata["status"],
            "calculation_sha256": sealed.calculation_sha256,
            "source_byte_identities": result.metadata["sources"],
            "runtime_authorized": False,
            "resources": "unavailable",
        },
        65536,
    )
    members.append(Member("receipt.json", len(receipt), sha(receipt), receipt))
    members.sort(key=lambda member: member.name)
    if len(members) > 54 or len({m.name for m in members}) != len(members):
        fail("waveform_contract")
    manifest = _canonical(
        {
            "schema": SCHEMA,
            "status": result.metadata["status"],
            "calculation_sha256": sealed.calculation_sha256,
            "files": [{"name": m.name, "bytes": m.bytes, "sha256": m.sha256} for m in members],
        },
        JSON_CAP,
    )
    total = sum(m.bytes for m in members) + len(manifest)
    if total > TOTAL_CAP:
        fail("waveform_limit")
    return ExportPlan(tuple(members), manifest, total, sealed.calculation_sha256)


def member_chunks(member):
    if (
        type(member) is not Member
        or type(member.bytes) is not int
        or not 0 < member.bytes <= TOTAL_CAP
        or type(member.data) not in (bytes, memoryview)
        or len(member.data) != member.bytes
        or type(member.sha256) is not str
        or not re.fullmatch("[a-f0-9]{64}", member.sha256)
        or type(member.data) is memoryview
        and (not member.data.readonly or member.data.format != "B")
    ):
        fail("waveform_contract")
    _name(member.name)
    digest = hashlib.sha256()
    for offset in range(0, member.bytes, CHUNK):
        chunk = member.data[offset : offset + CHUNK]
        digest.update(chunk)
        yield chunk
    if digest.hexdigest() != member.sha256:
        fail("waveform_contract")


def _directory(directory):
    from waveform_m08_files import OwnedDirectory

    if type(directory) is not OwnedDirectory:
        fail("waveform_type")
    directory.check_identity()


def _read(directory, name, cap):
    _name(name)
    with directory.open_regular(name) as handle:
        size = directory.file_size(handle)
        if not 0 < size <= cap:
            fail("waveform_limit")
        raw = handle.read(cap + 1)
        if len(raw) != size:
            fail("waveform_contract")
        return raw


def _manifest(raw):
    value = bounded_json(raw, JSON_CAP, max_nodes=4096, max_depth=8)
    keys(value, "schema status calculation_sha256 files")
    if (
        value["schema"] != SCHEMA
        or value["status"] not in ("computed", "qc_only")
        or type(value["calculation_sha256"]) is not str
        or not re.fullmatch("[a-f0-9]{64}", value["calculation_sha256"])
        or type(value["files"]) is not list
        or not 2 <= len(value["files"]) <= 54
    ):
        fail("waveform_contract")
    total, names = len(raw), []
    for item in value["files"]:
        keys(item, "name bytes sha256")
        name = _name(item["name"])
        if (
            name in ("manifest.json", "manifest.pending")
            or type(item["bytes"]) is not int
            or not 0 < item["bytes"] <= TOTAL_CAP
            or type(item["sha256"]) is not str
            or not re.fullmatch("[a-f0-9]{64}", item["sha256"])
        ):
            fail("waveform_contract")
        total += item["bytes"]
        if total > TOTAL_CAP:
            fail("waveform_limit")
        names.append(name)
    if names != sorted(set(names)) or "calculation.json" not in names or "receipt.json" not in names:
        fail("waveform_contract")
    return value


def _verify(directory, raw, marker):
    manifest = _manifest(raw)
    names = {item["name"] for item in manifest["files"]}
    if set(directory.names(55)) != names | {marker}:
        fail("waveform_contract")
    calculation = _read(directory, "calculation.json", JSON_CAP)
    if sha(calculation) != manifest["calculation_sha256"]:
        fail("waveform_contract")
    metadata = bounded_json(calculation, JSON_CAP, max_nodes=2097152, max_depth=16)
    _sealed_metadata(metadata)
    if _canonical(metadata, JSON_CAP) != calculation or metadata["status"] != manifest["status"]:
        fail("waveform_contract")
    descriptors = {f"c{d['channel_index']:02d}-{d['name']}.bin": d for d in metadata["array_descriptors"]}
    allowed = set(descriptors) | {"calculation.json", "receipt.json"}
    if "evaluation.json" in names:
        allowed.add("evaluation.json")
    if names != allowed:
        fail("waveform_contract")
    for item in manifest["files"]:
        descriptor = descriptors.get(item["name"])
        if descriptor is not None and (descriptor["bytes"] != item["bytes"] or descriptor["sha256"] != item["sha256"]):
            fail("waveform_contract")
        count, digest = 0, hashlib.sha256()
        with directory.open_regular(item["name"]) as handle:
            if directory.file_size(handle) != item["bytes"]:
                fail("waveform_contract")
            while count < item["bytes"]:
                chunk = handle.read(min(CHUNK, item["bytes"] - count))
                if not chunk:
                    fail("waveform_contract")
                count += len(chunk)
                digest.update(chunk)
                if descriptor is not None:
                    dtype = descriptor["dtype"]
                    if dtype == "<f8" and (
                        len(chunk) % 8 or any(not math.isfinite(v[0]) for v in struct.iter_unpack("<d", chunk))
                    ):
                        fail("waveform_contract")
                    if dtype == "|b1" and any(v not in (0, 1) for v in chunk):
                        fail("waveform_contract")
            if handle.read(1) or digest.hexdigest() != item["sha256"]:
                fail("waveform_contract")
    receipt = bounded_json(_read(directory, "receipt.json", 65536), 65536, max_nodes=4096, max_depth=16)
    keys(receipt, "schema status calculation_sha256 source_byte_identities runtime_authorized resources")
    if (
        receipt["schema"] != "caos.local-waveform-export-receipt.v1"
        or receipt["status"] != metadata["status"]
        or receipt["calculation_sha256"] != manifest["calculation_sha256"]
        or receipt["source_byte_identities"] != metadata["sources"]
        or receipt["runtime_authorized"] is not False
        or receipt["resources"] != "unavailable"
    ):
        fail("waveform_contract")
    if "evaluation.json" in names:
        _evaluation(_read(directory, "evaluation.json", JSON_CAP), manifest["calculation_sha256"], metadata)
    return SealedWaveform(calculation, manifest["calculation_sha256"])


def verify_export(directory):
    _directory(directory)
    return _verify(directory, _read(directory, "manifest.json", JSON_CAP), "manifest.json")


def write_export(plan, directory):
    _directory(directory)
    if (
        directory.readonly
        or type(plan) is not ExportPlan
        or type(plan.members) is not tuple
        or not 2 <= len(plan.members) <= 54
        or any(type(member) is not Member or type(member.bytes) is not int for member in plan.members)
        or directory.names(55)
    ):
        fail("waveform_contract")
    manifest = _manifest(plan.manifest)
    if (
        type(plan.total_bytes) is not int
        or not 0 < plan.total_bytes <= TOTAL_CAP
        or plan.total_bytes != sum(m.bytes for m in plan.members) + len(plan.manifest)
        or plan.calculation_sha256 != manifest["calculation_sha256"]
        or [{"name": m.name, "bytes": m.bytes, "sha256": m.sha256} for m in plan.members] != manifest["files"]
    ):
        fail("waveform_contract")
    for member in plan.members:
        with directory.create_regular(member.name) as handle:
            for chunk in member_chunks(member):
                if handle.write(chunk) != len(chunk):
                    fail("waveform_contract")
            directory.flush_file(handle)
    with directory.create_regular("manifest.pending") as handle:
        if handle.write(plan.manifest) != len(plan.manifest):
            fail("waveform_contract")
        directory.flush_file(handle)
    _verify(directory, _read(directory, "manifest.pending", JSON_CAP), "manifest.pending")
    directory.publish_pending()
    verified = verify_export(directory)
    return {
        "manifest_sha256": sha(plan.manifest),
        "calculation_sha256": verified.calculation_sha256,
        "bytes": plan.total_bytes,
        "runtime_authorized": False,
    }
