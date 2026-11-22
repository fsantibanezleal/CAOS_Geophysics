"""Geometry export, bounded NPY members and result-bundle container.

Exclusive new-generation writes and readback, no replacement of original or
prior successful generations. Container integrity and pointer publication are
implemented; full result/request semantics and filesystem crash durability
remain unimplemented and unaccepted.
"""

import hashlib
import io
import math
import os
import re
import stat
import uuid
from pathlib import Path
from magnetic_survey_json import (
    InputError, SurveyHandle, _Lexer, _Schema, canonical, digest, fail, keys, parse_request,
)
from magnetic_survey import plan_geometry

MAX_EXPORT_BYTES = 16777216
MAX_ARRAY_MEMBER_BYTES = 128 * 1024 * 1024
MAX_ARRAY_HEADER_BYTES = 65536
MAX_ARRAY_ELEMENTS = MAX_ARRAY_MEMBER_BYTES // 8
MAX_BUNDLE_BYTES = 128 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_BUNDLE_MEMBERS = 64
_MEMBER_NAME = re.compile(r"[A-Za-z0-9_.-]{1,96}\.npy\Z", re.ASCII)
_ID = re.compile(r"[A-Za-z0-9_.-]{1,96}\Z", re.ASCII)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_ARRAY_UNITS = {"nT", "nT^2", "SI", "m", "1", "index", "bool"}
_HISTORY_PHASES = ("l2", "irls_surrogate", "irls_fixed")
_HISTORY_STATUSES = ("iterating", "converged", "failed")
_HISTORY_BETAS = (0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)
_HISTORY_INDEX_MEMBER = "history-index.npy"
_HISTORY_NUMERIC_MEMBER = "history-numeric.npy"
_HISTORY_HASH_MEMBER = "history-model-hash-words.npy"


def _array_member_metadata(member, *, history_empty=False):
    """Validate the bounded public member descriptor without NumPy imports."""
    keys(member, "name dtype shape unit bytes sha256", "$/member")
    name = member["name"]
    if (type(name) is not str or not _MEMBER_NAME.fullmatch(name)
            or ".." in name or "/" in name or "\\" in name):
        fail("type", "$/member/name", "Flat bounded NPY member name required")
    dtype = member["dtype"]
    if type(dtype) is not str or dtype not in {"float64", "int64", "bool"}:
        fail("type", "$/member/dtype", "Unsupported NPY member dtype")
    shape = member["shape"]
    if type(shape) is not list or not 1 <= len(shape) <= 3:
        fail("count", "$/member/shape", "One to three dimensions required")
    elements = 1
    for dimension in shape:
        minimum = 0 if history_empty else 1
        if type(dimension) is not int or dimension < minimum or dimension > MAX_ARRAY_ELEMENTS:
            fail("count", "$/member/shape", "Array dimension outside member capacity")
        if dimension == 0:
            elements = 0
            continue
        if elements == 0:
            continue
        if elements > MAX_ARRAY_ELEMENTS // dimension:
            fail("resource", "$/member/shape", "Array element product exceeds member capacity")
        elements *= dimension
    unit = member["unit"]
    if type(unit) is not str or unit not in _ARRAY_UNITS:
        fail("enum", "$/member/unit", "Unsupported typed NPY unit")
    expected_dtype = "bool" if unit == "bool" else "int64" if unit == "index" else "float64"
    if dtype != expected_dtype:
        fail("type", "$/member/dtype", "Member dtype conflicts with its declared unit")
    size = member["bytes"]
    if type(size) is not int or not 1 <= size <= MAX_ARRAY_MEMBER_BYTES:
        fail("resource", "$/member/bytes", "NPY member byte count exceeds capacity")
    digest = member["sha256"]
    if type(digest) is not str or not _SHA256.fullmatch(digest):
        fail("hash", "$/member/sha256", "Lowercase SHA-256 required")
    return dtype, tuple(shape), elements, size, digest


def encode_array_member(array, *, name, unit, _history_empty=False):
    """Encode one bounded float64/int64/bool array as an uncompressed NPY member.

    This primitive does not validate or publish a magnetic Result bundle.
    """
    import numpy as np

    if type(array) is not np.ndarray:
        fail("type", "$/array", "Built-in NumPy array required")
    shape = array.shape
    minimum = 0 if _history_empty else 1
    if (array.ndim < 1 or array.ndim > 3
            or any(type(d) is not int or d < minimum for d in shape)):
        fail("count", "$/array/shape", "One to three dimensions required")
    elements = 1
    for dimension in shape:
        if dimension == 0:
            elements = 0
            continue
        if elements == 0:
            continue
        if elements > MAX_ARRAY_ELEMENTS // dimension:
            fail("resource", "$/array/shape", "Array element product exceeds member capacity")
        elements *= dimension
    dtype = array.dtype
    if dtype == np.dtype(np.float64):
        dtype_name = "float64"
        if not np.isfinite(array).all():
            fail("type", "$/array", "Nonfinite numeric member is forbidden")
    elif dtype == np.dtype(np.int64):
        dtype_name = "int64"
    elif dtype == np.dtype(np.bool_):
        dtype_name = "bool"
    else:
        fail("type", "$/array/dtype", "Only float64, int64, and bool members are supported")
    # Reuse metadata validation for name, unit and dtype binding before copying.
    descriptor = {"name": name, "dtype": dtype_name, "shape": list(shape), "unit": unit,
                  "bytes": 1, "sha256": "0"*64}
    _array_member_metadata(descriptor, history_empty=_history_empty)
    if elements * dtype.itemsize > MAX_ARRAY_MEMBER_BYTES:
        fail("resource", "$/array", "Array payload exceeds 128 MiB")
    contiguous = np.ascontiguousarray(array)
    stream = io.BytesIO()
    np.lib.format.write_array(stream, contiguous, version=(2, 0), allow_pickle=False)
    raw = stream.getvalue()
    if len(raw) > MAX_ARRAY_MEMBER_BYTES:
        fail("resource", "$/array", "NPY header and payload exceed 128 MiB")
    descriptor["bytes"] = len(raw)
    descriptor["sha256"] = hashlib.sha256(raw).hexdigest()
    return descriptor, raw


def decode_array_member(member, raw, *, _history_empty=False):
    """Validate an exact NPY file and return an owned array without pickle."""
    dtype_name, shape, elements, expected_bytes, expected_hash = _array_member_metadata(
        member, history_empty=_history_empty)
    if type(raw) is not bytes:
        fail("type", "$/member/data", "Immutable byte string required")
    if len(raw) != expected_bytes:
        fail("count", "$/member/data", "NPY member byte count mismatch")
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        fail("hash", "$/member/data", "NPY member hash mismatch")

    import numpy as np
    stream = io.BytesIO(raw)
    try:
        version = np.lib.format.read_magic(stream)
        if version not in {(1, 0), (2, 0), (3, 0)}:
            fail("encoding", "$/member/data", "Unsupported NPY format version")
        header_shape, fortran_order, disk_dtype = np.lib.format._read_array_header(
            stream, version, max_header_size=MAX_ARRAY_HEADER_BYTES)
    except InputError:
        raise
    except (EOFError, OSError, ValueError, TypeError, OverflowError):
        fail("encoding", "$/member/data", "Malformed or oversized NPY header")
    if fortran_order or tuple(header_shape) != shape:
        fail("count", "$/member/data", "NPY order or shape differs from descriptor")
    expected_kind_size = {"float64": ("f", 8), "int64": ("i", 8), "bool": ("b", 1)}[dtype_name]
    if disk_dtype.hasobject or (disk_dtype.kind, disk_dtype.itemsize) != expected_kind_size:
        fail("type", "$/member/data", "NPY header dtype differs from descriptor")
    data_offset = stream.tell()
    if data_offset + elements*disk_dtype.itemsize != len(raw):
        fail("count", "$/member/data", "NPY payload has a wrong length or trailing bytes")
    try:
        result = np.frombuffer(raw, dtype=disk_dtype, count=elements, offset=data_offset).reshape(shape).astype(
            np.dtype(dtype_name), copy=True, order="C")
    except (ValueError, TypeError, OverflowError):
        fail("encoding", "$/member/data", "NPY numeric payload cannot be decoded")
    if dtype_name == "float64" and not np.isfinite(result).all():
        fail("type", "$/member/data", "Nonfinite numeric member is forbidden")
    return result


def _history_validate(history, candidates):
    if type(history) is not list or len(history) > 4096:
        fail("count", "$/result/history", "History must contain zero to 4096 records")
    if type(candidates) is not list or len(candidates) != 16:
        fail("count", "$/result/candidates", "History requires the frozen 16-candidate order")
    candidate_ids = []
    for index, candidate in enumerate(candidates):
        if type(candidate) is not dict or type(candidate.get("id")) is not str or not _ID.fullmatch(candidate["id"]):
            fail("type", "$/result/candidates", "Candidate IDs are required for history references")
        keys(candidate, "id beta penalty folds status score", "$/result/candidates")
        beta = candidate["beta"]
        if (type(beta) not in (int, float) or beta != _HISTORY_BETAS[index//2]
                or candidate["penalty"] != ("l2" if index % 2 == 0 else "sparse_smallness")):
            fail("type", "$/result/candidates", "Candidate order must be frozen beta-major with L2 first")
        candidate_ids.append(candidate["id"])
    if len(set(candidate_ids)) != 16:
        fail("type", "$/result/candidates", "Candidate IDs must be unique")
    candidate_index = {value: index for index, value in enumerate(candidate_ids)}
    normalized = []
    for row_index, record in enumerate(history):
        path = f"$/result/history/{row_index}"
        keys(record, "candidate fold phase outer_iteration inner_iteration beta epsilon_q phi_d phi_regularizer objective kkt_inf model_sha256 status", path)
        candidate = record["candidate"]
        if type(candidate) is not str or candidate not in candidate_index:
            fail("type", path + "/candidate", "Unknown candidate ID")
        fold = record["fold"]
        if type(fold) is not int or fold not in (-1, 0, 1, 2):
            fail("count", path + "/fold", "Fold must be -1 or one of 0, 1, 2")
        phase = record["phase"]
        if type(phase) is not str or phase not in _HISTORY_PHASES:
            fail("enum", path + "/phase", "Unknown history phase")
        status = record["status"]
        if type(status) is not str or status not in _HISTORY_STATUSES:
            fail("enum", path + "/status", "Unknown history status")
        counters = (record["outer_iteration"], record["inner_iteration"])
        if any(type(value) is not int or value < 0 or value > 2**63-1 for value in counters):
            fail("count", path, "History iteration counters must be nonnegative int64")
        numeric = []
        for name in ("beta", "epsilon_q", "phi_d", "phi_regularizer", "objective", "kkt_inf"):
            value = record[name]
            try:
                finite = type(value) in (int, float) and math.isfinite(float(value))
            except (OverflowError, ValueError):
                finite = False
            if not finite or value < 0:
                fail("type", path + "/" + name, "History metric must be finite and nonnegative")
            numeric.append(float(value))
        if numeric[0] <= 0:
            fail("type", path + "/beta", "Beta must be positive")
        if numeric[0] != candidates[candidate_index[candidate]]["beta"]:
            fail("type", path + "/beta", "History beta differs from its frozen candidate")
        if (phase == "l2") != (numeric[1] == 0):
            fail("type", path + "/epsilon_q", "Only the L2 phase uses zero epsilon_q")
        model_hash = record["model_sha256"]
        if type(model_hash) is not str or not _SHA256.fullmatch(model_hash):
            fail("hash", path + "/model_sha256", "Lowercase model SHA-256 required")
        normalized.append((candidate_index[candidate], fold, _HISTORY_PHASES.index(phase),
                          counters[0], counters[1], _HISTORY_STATUSES.index(status),
                          numeric, model_hash))
    return normalized, candidate_ids


def encode_history_table(history, candidates):
    """Encode the contract's lossless three-array history representation."""
    import numpy as np

    normalized, _ = _history_validate(history, candidates)
    count = len(normalized)
    index = np.empty((count, 6), dtype=np.int64)
    numeric = np.empty((count, 6), dtype=np.float64)
    hash_words = np.empty((count, 4), dtype=np.int64)
    for row, values in enumerate(normalized):
        candidate, fold, phase, outer, inner, status, metrics, model_hash = values
        index[row] = (candidate, fold, phase, outer, inner, status)
        numeric[row] = metrics
        raw_hash = bytes.fromhex(model_hash)
        hash_words[row] = [int.from_bytes(raw_hash[offset:offset+8], "little", signed=True)
                           for offset in range(0, 32, 8)]
    members = []
    payloads = {}
    for array, name, unit in (
            (index, _HISTORY_INDEX_MEMBER, "index"),
            (numeric, _HISTORY_NUMERIC_MEMBER, "1"),
            (hash_words, _HISTORY_HASH_MEMBER, "index")):
        descriptor, payload = encode_array_member(array, name=name, unit=unit, _history_empty=True)
        members.append(descriptor)
        payloads[name] = payload
    return members, payloads


def decode_history_table(members, payloads, candidates):
    """Restore history records in the original order with exact ID/hash values."""
    import numpy as np

    if type(members) is not list or len(members) != 3 or type(payloads) is not dict:
        fail("count", "$/members", "History requires exactly three typed members")
    by_name = {}
    for member in members:
        if type(member) is not dict or member.get("name") in by_name:
            fail("type", "$/members", "Duplicate or malformed history member")
        by_name[member["name"]] = member
    expected = {
        _HISTORY_INDEX_MEMBER: ("int64", "index", (6,)),
        _HISTORY_NUMERIC_MEMBER: ("float64", "1", (6,)),
        _HISTORY_HASH_MEMBER: ("int64", "index", (4,)),
    }
    if set(by_name) != set(expected) or set(payloads) != set(expected):
        fail("type", "$/members", "History member inventory differs from contract")
    arrays = {}
    row_count = None
    for name, (dtype, unit, suffix) in expected.items():
        member = by_name[name]
        if (member.get("dtype"), member.get("unit"), type(member.get("shape")) is list,
                tuple(member.get("shape", ())[1:]) if type(member.get("shape")) is list else ()) != (
                dtype, unit, True, suffix):
            fail("type", "$/members", "History member dtype, unit, or shape differs")
        if row_count is None:
            row_count = member["shape"][0]
        elif member["shape"][0] != row_count:
            fail("count", "$/members", "History arrays have inconsistent row counts")
        arrays[name] = decode_array_member(member, payloads[name], _history_empty=True)
    if row_count is None or row_count > 4096:
        fail("count", "$/members", "History row count exceeds contract")
    if type(candidates) is not list or len(candidates) != 16:
        fail("count", "$/result/candidates", "History requires the frozen 16-candidate order")
    candidate_ids = []
    for index, candidate in enumerate(candidates):
        if type(candidate) is not dict or type(candidate.get("id")) is not str:
            fail("type", "$/result/candidates", "Candidate IDs are required for history references")
        keys(candidate, "id beta penalty folds status score", "$/result/candidates")
        if (type(candidate["beta"]) not in (int, float)
                or candidate["beta"] != _HISTORY_BETAS[index//2]
                or candidate["penalty"] != ("l2" if index % 2 == 0 else "sparse_smallness")
                or not _ID.fullmatch(candidate["id"])):
            fail("type", "$/result/candidates", "Candidate order must be frozen beta-major with L2 first")
        candidate_ids.append(candidate["id"])
    if len(set(candidate_ids)) != 16:
        fail("type", "$/result/candidates", "Candidate IDs must be unique")
    index = arrays[_HISTORY_INDEX_MEMBER]
    numeric = arrays[_HISTORY_NUMERIC_MEMBER]
    hash_words = arrays[_HISTORY_HASH_MEMBER]
    records = []
    for row in range(row_count):
        candidate, fold, phase, outer, inner, status = map(int, index[row])
        if not 0 <= candidate < 16 or fold not in (-1, 0, 1, 2):
            fail("count", "$/history", "History candidate or fold index outside contract")
        if not 0 <= phase < len(_HISTORY_PHASES) or not 0 <= status < len(_HISTORY_STATUSES):
            fail("enum", "$/history", "History phase or status index outside contract")
        if outer < 0 or inner < 0:
            fail("count", "$/history", "Negative history iteration count")
        metrics = list(map(float, numeric[row]))
        if any(not np.isfinite(value) or value < 0 for value in metrics) or metrics[0] <= 0:
            fail("type", "$/history", "History numeric array contains invalid values")
        if (_HISTORY_PHASES[phase] == "l2") != (metrics[1] == 0):
            fail("type", "$/history", "History epsilon does not match phase")
        hash_bytes = b"".join(int(word).to_bytes(8, "little", signed=True) for word in hash_words[row])
        records.append({
            "candidate": candidate_ids[candidate], "fold": fold,
            "phase": _HISTORY_PHASES[phase], "outer_iteration": outer,
            "inner_iteration": inner, "beta": metrics[0], "epsilon_q": metrics[1],
            "phi_d": metrics[2], "phi_regularizer": metrics[3],
            "objective": metrics[4], "kkt_inf": metrics[5],
            "model_sha256": hash_bytes.hex(), "status": _HISTORY_STATUSES[status],
        })
    _history_validate(records, candidates)
    return records


def _bundle_member_refs(value, found, path="$", *, inside_history=False):
    if type(value) is dict:
        if "member" in value:
            keys(value, "member", path)
            name = value["member"]
            if type(name) is not str or not _MEMBER_NAME.fullmatch(name) or ".." in name:
                fail("type", path, "Exact bounded member reference required")
            found.setdefault(name, []).append(path)
            return
        if "data" in value:
            fail("type", path, "Array payloads must be member references")
        for key, child in value.items():
            _bundle_member_refs(child, found, f"{path}/{key}", inside_history=inside_history)
    elif type(value) is list:
        for index, child in enumerate(value):
            _bundle_member_refs(child, found, f"{path}/{index}", inside_history=inside_history)


def _request_member_unit(path, request):
    if path.startswith("$/request_metadata/"):
        path = "$/" + path[len("$/request_metadata/"):]
    if path.endswith("/origin") or path.endswith("/origin_m") or path.endswith("/receivers_m"):
        return "m"
    if path.endswith("/widths_x_m") or path.endswith("/widths_y_m") or path.endswith("/widths_z_m"):
        return "m"
    if path.endswith("/block_width_m") or path.endswith("/lengths_m"):
        return "m"
    if path in {"$/geometry/usable", "$/geometry/mesh/active"}:
        return "bool"
    if path == "$/observations/values":
        return "nT"
    if path == "$/noise/values":
        noise_kind = request["noise"].get("kind") if type(request.get("noise")) is dict else None
        if noise_kind == "diagonal_sd":
            return "nT"
        if noise_kind == "full_covariance":
            return "nT^2"
        fail("type", path, "Noise kind must determine typed covariance units")
    if any(path == "$/prior/" + key for key in ("lower_si", "upper_si", "start_si", "reference_si")):
        return "SI"
    fail("type", path, "No scientific unit mapping exists for this request array")


def encode_request_metadata(request_bytes):
    """Validate source request bytes and externalize every typed input array."""
    import numpy as np

    if type(request_bytes) is not bytes:
        fail("type", "$/request", "Exact request bytes required")
    # parse_request performs the full bounded schema and semantic checks before
    # values are externalized. Its private byte owner is not modified.
    parse_request(request_bytes)
    lexer = _Lexer(request_bytes)
    document = lexer.document()
    schema = _Schema(lexer)
    schema.validate(document)
    references = {}
    members = []
    payloads = {}
    for index, (descriptor, path) in enumerate(schema.descriptors):
        unit = _request_member_unit(path, document)
        dtype = descriptor["dtype"]
        shape = descriptor["shape"]
        values = schema.values(descriptor)
        array = np.asarray(values, dtype={"float64": np.float64, "int64": np.int64,
                                         "bool": np.bool_}[dtype]).reshape(shape, order="C")
        name = f"request-{index:03d}.npy"
        member, raw = encode_array_member(array, name=name, unit=unit)
        members.append(member)
        payloads[name] = raw
        references[id(descriptor)] = {"member": name}

    def externalize(value):
        if type(value) is dict:
            reference = references.get(id(value))
            if reference is not None:
                return reference
            return {key: externalize(child) for key, child in value.items()}
        if type(value) is list:
            return [externalize(child) for child in value]
        return value

    metadata = externalize(document)
    if len(canonical(metadata)) > 262144:
        fail("resource", "$/request_metadata", "Bundle request metadata exceeds 256 KiB")
    return metadata, members, payloads


def _request_array_digest(array, dtype):
    import numpy as np

    if dtype == "float64":
        raw = np.asarray(array, dtype="<f8").tobytes(order="C")
    elif dtype == "int64":
        raw = np.asarray(array, dtype="<i8").tobytes(order="C")
    elif dtype == "bool":
        raw = np.asarray(array, dtype=np.bool_).tobytes(order="C")
    else:
        fail("type", "$/member/dtype", "Unsupported reconstructed request dtype")
    return hashlib.sha256(raw).hexdigest()


def _validate_request_metadata(request_metadata, member_by_name, payloads):
    def restore(value, path="$/request_metadata"):
        if type(value) is dict:
            if "member" in value:
                keys(value, "member", path)
                name = value["member"]
                if type(name) is not str or name not in member_by_name:
                    fail("count", path, "Request array member is absent")
                member = member_by_name[name]
                unit = _request_member_unit(path, request_metadata)
                if member["unit"] != unit:
                    fail("type", path, "Array unit disagrees with its scientific request field")
                array = decode_array_member(member, payloads[name])
                flat = array.reshape(-1, order="C")
                return {"dtype": member["dtype"], "shape": member["shape"],
                        "data": flat.tolist(), "sha256": _request_array_digest(array, member["dtype"])}
            if "data" in value:
                fail("type", path, "Request arrays must be member references")
            return {key: restore(child, path + "/" + key) for key, child in value.items()}
        if type(value) is list:
            return [restore(child, path + "/" + str(index)) for index, child in enumerate(value)]
        return value

    reconstructed = restore(request_metadata)
    request_raw = canonical(reconstructed)
    parse_request(request_raw)
    return request_raw


def validate_bundle_container(manifest, payloads):
    """Validate the bounded generation envelope and every referenced NPY file.

    This is container integrity validation; the complete scientific Result and
    request semantics still require their dedicated schema validators.
    """
    if type(manifest) is not dict:
        fail("type", "$", "Bundle manifest object required")
    keys(manifest, "schema result request_metadata original members generation_sha256", "$")
    if manifest["schema"] != "magnetic-survey-bundle-1":
        fail("enum", "$/schema", "Unsupported magnetic bundle schema")
    keys(manifest["result"], "schema status identity inventory partition candidates selected model prediction metrics history diagnostics claims", "$/result")
    keys(manifest["request_metadata"], "schema source frame inducing_field acquisition processing geometry observations noise prior policy intent", "$/request_metadata")
    keys(manifest["original"], "sha256 bytes scope rights included", "$/original")
    source = manifest["request_metadata"]["source"]
    keys(source, "id kind original_sha256 original_bytes provider_url rights scope citation", "$/request_metadata/source")
    original = manifest["original"]
    if (type(original["sha256"]) is not str or not _SHA256.fullmatch(original["sha256"])
            or type(original["bytes"]) is not int or original["bytes"] < 1
            or type(original["scope"]) is not str
            or original["scope"] not in {"complete_acquisition", "declared_subset"}
            or type(original["rights"]) is not str
            or original["rights"] not in {"private_user_supplied", "provider_link_only", "redistribution_permitted", "unresolved"}
            or original["included"] is not False):
        fail("type", "$/original", "Closed original-byte reference required; raw inclusion is forbidden")
    if (original["sha256"] != source["original_sha256"]
            or original["bytes"] != source["original_bytes"]
            or original["scope"] != source["scope"] or original["rights"] != source["rights"]):
        fail("hash", "$/original", "Original reference differs from validated request metadata")
    result = manifest["result"]
    if result["schema"] != "magnetic-survey-result-1":
        fail("enum", "$/result/schema", "Unsupported magnetic result schema")
    if type(result["status"]) is not str or result["status"] not in {"failed", "ineligible"}:
        fail("dependency", "$/result/status", "Successful result publication requires full scientific schema validation")
    claims = result["claims"]
    keys(claims, "full_method_accepted field_source_verified geology_truth_known online_admitted", "$/result/claims")
    if any(value is not False for value in claims.values()):
        fail("type", "$/result/claims", "Unaccepted result claims must all remain false")
    history = result["history"]
    keys(history, "codec index numeric model_hash_words", "$/result/history")
    if history["codec"] != "magnetic-history-table-1":
        fail("enum", "$/result/history/codec", "Unsupported lossless history codec")
    history_members = [history[key] for key in ("index", "numeric", "model_hash_words")]
    if any(type(reference) is not dict or set(reference) != {"member"} for reference in history_members):
        fail("type", "$/result/history", "History arrays must be exact member references")

    members = manifest["members"]
    if type(members) is not list or not 1 <= len(members) <= MAX_BUNDLE_MEMBERS:
        fail("count", "$/members", "Bundle requires one to 64 array members")
    if type(payloads) is not dict:
        fail("type", "$/members", "Member payload mapping required")
    member_by_name = {}
    for member in members:
        if type(member) is not dict:
            fail("type", "$/members", "Member descriptor object required")
        name = member.get("name")
        if name in member_by_name:
            fail("type", "$/members", "Duplicate member name")
        member_by_name[name] = member
    if set(payloads) != set(member_by_name):
        fail("count", "$/members", "Payload inventory differs from the manifest")

    references = {}
    _bundle_member_refs(result, references, "$/result")
    _bundle_member_refs(manifest["request_metadata"], references, "$/request_metadata")
    if set(references) != set(member_by_name) or any(len(paths) != 1 for paths in references.values()):
        fail("count", "$/members", "Each member must be referenced exactly once, with no unused members")
    if any(reference["member"] not in member_by_name for reference in history_members):
        fail("count", "$/result/history", "History reference is absent from member table")

    total_bytes = 0
    member_specs = []
    for name, member in member_by_name.items():
        empty_history = name in {_HISTORY_INDEX_MEMBER, _HISTORY_NUMERIC_MEMBER, _HISTORY_HASH_MEMBER}
        metadata = _array_member_metadata(member, history_empty=empty_history)
        raw = payloads[name]
        if type(raw) is not bytes or len(raw) != member["bytes"]:
            fail("count", "$/members/" + str(name), "Exact immutable member bytes required")
        total_bytes += len(raw)
        if total_bytes > MAX_BUNDLE_BYTES:
            fail("resource", "$/members", "Bundle member bytes exceed 128 MiB")
        member_specs.append((name, member, raw, empty_history, metadata))
    unsigned = dict(manifest)
    generation = unsigned.pop("generation_sha256")
    if type(generation) is not str or not _SHA256.fullmatch(generation) or generation != digest(unsigned):
        fail("hash", "$/generation_sha256", "Canonical bundle generation identity mismatch")
    encoded_manifest = canonical(manifest)
    if len(encoded_manifest) > MAX_MANIFEST_BYTES:
        fail("resource", "$", "Bundle manifest exceeds 1 MiB")
    if total_bytes + len(encoded_manifest) > MAX_BUNDLE_BYTES:
        fail("resource", "$", "Complete bundle exceeds 128 MiB")
    for _, member, raw, empty_history, _ in member_specs:
        decode_array_member(member, raw, _history_empty=empty_history)
    _validate_request_metadata(manifest["request_metadata"], member_by_name, payloads)
    history_payloads = {reference["member"]: payloads[reference["member"]]
                        for reference in history_members}
    decode_history_table([member_by_name[reference["member"]] for reference in history_members],
                         history_payloads, result["candidates"])
    return {"generation_sha256": generation, "manifest_bytes": len(encoded_manifest),
            "member_bytes": total_bytes, "members": len(members)}


def _bundle_regular_file(path, maximum):
    if path.is_symlink():
        fail("durability", "$", "Symlink bundle file forbidden")
    try:
        with path.open("rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
                fail("resource", "$", "Regular bounded bundle file required")
            raw = stream.read(maximum + 1)
    except OSError:
        fail("durability", "$", "Bundle file could not be read")
    if len(raw) != info.st_size:
        fail("durability", "$", "Bundle file changed during read")
    return raw


def _read_bundle_generation(root, generation):
    directory = root / "generations" / generation
    if directory.is_symlink() or not directory.is_dir():
        fail("durability", "$", "Local bundle generation directory required")
    manifest_raw = _bundle_regular_file(directory / "manifest.json", MAX_MANIFEST_BYTES)
    lexer = _Lexer(manifest_raw, max_bytes=MAX_MANIFEST_BYTES, max_string=MAX_MANIFEST_BYTES,
                   max_strings=MAX_MANIFEST_BYTES, max_tokens=500000, defer=False)
    manifest = lexer.document()
    if type(manifest) is not dict or type(manifest.get("members")) is not list:
        fail("type", "$", "Closed bundle manifest required")
    if len(manifest["members"]) > MAX_BUNDLE_MEMBERS:
        fail("count", "$/members", "Bundle member cap exceeded")
    payloads = {}
    for member in manifest["members"]:
        if type(member) is not dict or type(member.get("name")) is not str:
            fail("type", "$/members", "Member descriptor required")
        name = member["name"]
        if name in payloads:
            fail("type", "$/members", "Duplicate member name")
        _array_member_metadata(member, history_empty=name in {
            _HISTORY_INDEX_MEMBER, _HISTORY_NUMERIC_MEMBER, _HISTORY_HASH_MEMBER})
        payloads[name] = _bundle_regular_file(directory / name, MAX_ARRAY_MEMBER_BYTES)
    expected_files = {"manifest.json", *payloads}
    try:
        if {item.name for item in directory.iterdir()} != expected_files:
            fail("type", "$/members", "Generation directory contains unlisted files")
    except OSError:
        fail("durability", "$", "Bundle generation inventory could not be read")
    validate_bundle_container(manifest, payloads)
    return manifest, payloads


def read_bundle_generation(base_directory):
    """Read and validate the generation selected by the local atomic pointer."""
    root = Path(base_directory)
    if root.is_symlink() or not root.is_dir():
        fail("durability", "$", "Existing local bundle root directory required")
    pointer_raw = _bundle_regular_file(root / "CURRENT.json", 1024)
    lexer = _Lexer(pointer_raw, max_bytes=1024, max_string=256, max_strings=1024,
                   max_tokens=32, defer=False)
    pointer = lexer.document()
    keys(pointer, "schema generation generation_sha256", "$/pointer")
    if (pointer["schema"] != "magnetic-bundle-pointer-1"
            or type(pointer["generation"]) is not str
            or re.fullmatch(r"g-[0-9a-f]{32}", pointer["generation"], re.ASCII) is None
            or type(pointer["generation_sha256"]) is not str
            or not _SHA256.fullmatch(pointer["generation_sha256"])):
        fail("type", "$/pointer", "Closed local generation pointer required")
    manifest, payloads = _read_bundle_generation(root, pointer["generation"])
    if manifest["generation_sha256"] != pointer["generation_sha256"]:
        fail("hash", "$/pointer", "Pointer and generation identities differ")
    return manifest, payloads


def write_bundle_generation(base_directory, manifest, payloads):
    """Publish one verified local bundle by same-volume atomic pointer replace.

    Directory durability semantics are filesystem-specific and not inferred from
    successful file fsync or atomic replacement.
    """
    report = validate_bundle_container(manifest, payloads)
    root = Path(base_directory)
    if root.exists() and (root.is_symlink() or not root.is_dir()):
        fail("durability", "$", "Bundle root must be a real directory")
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        fail("durability", "$", "Symlink bundle root forbidden")
    generations = root / "generations"
    if generations.exists() and (generations.is_symlink() or not generations.is_dir()):
        fail("durability", "$", "Generation store must be a real directory")
    generations.mkdir(exist_ok=True)
    current = root / "CURRENT.json"
    if current.is_symlink() or (current.exists() and not current.is_file()):
        fail("durability", "$", "Current bundle pointer must be a regular file")
    generation = "g-" + uuid.uuid4().hex
    directory = generations / generation
    directory.mkdir(exist_ok=False)
    try:
        for member in manifest["members"]:
            name = member["name"]
            path = directory / name
            with path.open("xb") as stream:
                stream.write(payloads[name])
                stream.flush()
                os.fsync(stream.fileno())
        manifest_raw = canonical(manifest)
        with (directory / "manifest.json").open("xb") as stream:
            stream.write(manifest_raw)
            stream.flush()
            os.fsync(stream.fileno())
        stored, _ = _read_bundle_generation(root, generation)
        if stored["generation_sha256"] != report["generation_sha256"]:
            fail("durability", "$", "Generation readback identity differs")
        pointer = canonical({"schema": "magnetic-bundle-pointer-1", "generation": generation,
                             "generation_sha256": report["generation_sha256"]})
        temporary = root / ("CURRENT." + uuid.uuid4().hex + ".tmp")
        with temporary.open("xb") as stream:
            stream.write(pointer)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, current)
    except BaseException:
        # Do not modify the currently selected generation on any pre-swap error.
        # A crash may leave an unreferenced directory; readers never select it.
        raise
    return {**report, "generation": generation}


def export_geometry(handle):
    if type(handle) is not SurveyHandle:
        fail("type", "$", "Closed parsed byte handle required")
    raw = handle._export_bytes()
    doc = dict(schema="magnetic-geometry-export-1", request_sha256=hashlib.sha256(raw).hexdigest(),
               request_bytes=len(raw), request=raw.decode("utf-8"), plan=plan_geometry(handle))
    doc["generation_sha256"] = digest(doc)
    out = canonical(doc)
    if len(out) > MAX_EXPORT_BYTES:
        fail("resource", "$", "Geometry export byte capacity exceeded")
    return out


def import_geometry(raw):
    # A bounded outer document contains a single bounded request UTF8 string.
    # Root depth includes the plan, whose descriptor data remain bounded lists.
    lexer = _Lexer(raw, max_bytes=MAX_EXPORT_BYTES, max_string=8388608,
                   max_strings=MAX_EXPORT_BYTES, max_tokens=500000, defer=False)
    doc = lexer.document()
    keys(doc, "schema request_sha256 request_bytes request plan generation_sha256", "$")
    if doc["schema"] != "magnetic-geometry-export-1" or type(doc["request"]) is not str:
        fail("type", "$", "Closed geometry export required")
    generation = doc.pop("generation_sha256")
    if generation != digest(doc):
        fail("hash", "$", "Geometry generation identity mismatch")
    request = doc["request"].encode("utf-8")
    if type(doc["request_bytes"]) is not int or doc["request_bytes"] != len(request):
        fail("count", "$", "Request byte count mismatch")
    if doc["request_sha256"] != hashlib.sha256(request).hexdigest():
        fail("hash", "$", "Original request identity mismatch")
    expected = plan_geometry(parse_request(request))
    # Canonical comparison preserves numeric types/negative zero, unlike ==.
    if canonical(doc["plan"]) != canonical(expected):
        fail("hash", "$/plan", "Recomputed geometry plan mismatch")
    return expected


def write_geometry(path, handle):
    """Create only a new explicit local export; no provider reads or overwrite."""
    target = Path(path)
    raw = export_geometry(handle)
    created = False
    try:
        with target.open("xb") as stream:
            created = True
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        imported = read_geometry(target)
        if canonical(imported) != canonical(plan_geometry(handle)):
            fail("durability", "$", "Export readback differs")
    except BaseException:
        if created:
            # Only the exact newly created target, never a parent or prior file.
            target.unlink(missing_ok=True)
        raise


def read_geometry(path):
    target = Path(path)
    if target.is_symlink():
        fail("durability", "$", "Symlink export forbidden")
    with target.open("rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            fail("durability", "$", "Regular local export file required")
        if info.st_size > MAX_EXPORT_BYTES:
            fail("resource", "$", "Geometry export byte capacity exceeded")
        raw = stream.read(MAX_EXPORT_BYTES+1)
    return import_geometry(raw)
