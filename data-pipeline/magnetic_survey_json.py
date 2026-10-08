"""Stdlib-only closed M04 byte protocol. No IO, numerical arrays or engine import.

Likelihood tokens are scanned/typed/hashed but never decoded into a value list.
Only admitted geometry/prior metadata is materialized for a planner snapshot.
See docs/design/features/m04-survey-inversion/contracts.md for exact limits.
"""

import copy
import datetime
import hashlib
import json
import math
import re
import struct
from dataclasses import dataclass
from types import MappingProxyType
from urllib.parse import urlsplit

MAX_BYTES = 8388608
MAX_TOKENS = 500000
MAX_DEPTH = 12
QUANTITIES = ("secondary_enu_nT", "linear_tmi_nT", "exact_total_anomaly_nT")
RELATIONS = ("secondary_field_declared", "projection_of_secondary_declared",
             "total_norm_minus_declared_uniform_F")
BETAS = [.0001, .001, .01, .1, 1., 10., 100., 1000.]
QC = ("accepted", "missing_physical_metadata", "invalid_measurement",
      "provider_qc_excluded", "geometry_ineligible")
RIGHTS = ("private_user_supplied", "provider_link_only", "redistribution_permitted", "unresolved")
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_ID = re.compile(r"[A-Za-z0-9_.-]{1,96}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z", re.ASCII)
_FACTORY = object()


class InputError(ValueError):
    """Closed safe error: messages contain no raw user values or traceback."""

    def __init__(self, code, path, message):
        safe_path = path if path.isascii() and len(path) <= 2048 and all(ord(c) >= 32 for c in path) else "$/document"
        self.code, self.path, self.message = code, safe_path, message
        super().__init__(f"{code}: {path}: {message}")

    def envelope(self):
        return dict(schema="magnetic-input-error-1", code=self.code,
                    path=self.path, message=self.message)


def fail(code, path, message):
    raise InputError(code, path, message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def keys(value, names, path):
    if type(value) is not dict or set(value) != set(names.split()):
        fail("type", path, "Exact built-in object keys required")


def enum(value, choices, path):
    if type(value) is not str or value not in choices:
        fail("enum", path, "Unsupported literal enum")


def integer(value, lower, upper, path):
    if type(value) is not int or not lower <= value <= upper:
        fail("type", path, "Exact bounded integral token required")
    return value


def real(value, lower, upper, path, strict_lower=False, strict_upper=False):
    if type(value) not in (int, float):
        fail("type", path, "Finite real number required")
    out = float(value)
    if (not math.isfinite(out) or out < lower or out > upper
            or (strict_lower and out == lower) or (strict_upper and out == upper)):
        fail("type", path, "Real outside declared range")
    return out


def text(value, path):
    if (type(value) is not str or not 1 <= len(value.encode("utf-8")) <= 2048
            or any((ord(c) < 32 and c != "\n") or ord(c) == 127 for c in value)):
        fail("type", path, "Nonempty bounded text without controls required")


def identifier(value, path):
    if type(value) is not str or not _ID.fullmatch(value):
        fail("type", path, "Bounded ASCII identifier required")


def hash_value(value, path):
    if type(value) is not str or not _HASH.fullmatch(value):
        fail("hash", path, "Lowercase SHA256 required")


def sequence(value, count, path):
    if type(value) is not list or len(value) != count:
        fail("count", path, "Exact original-order list count required")


@dataclass(frozen=True, repr=False)
class _Span:
    start: int
    end: int
    count: int
    float_hash: str | None
    int_hash: str | None
    bool_hash: str | None
    negative_zero: bool


class _Lexer:
    """Bound complete lexical document while deferring all descriptor data lists."""

    def __init__(self, raw, max_bytes=MAX_BYTES, max_string=2048, max_strings=262144,
                 max_tokens=MAX_TOKENS, defer=True):
        if type(raw) is not bytes:
            fail("type", "$", "Exact bytes required; no native callbacks")
        if len(raw) > max_bytes:
            fail("bytes", "$", "Input byte limit exceeded")
        if raw.startswith(b"\xef\xbb\xbf"):
            fail("encoding", "$", "UTF8 BOM forbidden")
        try:
            self.raw = raw.decode("utf-8", errors="strict")
        except UnicodeError:
            fail("encoding", "$", "Invalid UTF8")
        self.i = self.tokens = self.string_bytes = 0
        self.max_string, self.max_strings = max_string, max_strings
        self.max_tokens, self.defer = max_tokens, defer

    def token(self):
        self.tokens += 1
        if self.tokens > self.max_tokens:
            fail("tokens", "$", "Token limit exceeded")

    def whitespace(self):
        while self.i < len(self.raw) and self.raw[self.i] in " \t\r\n":
            self.i += 1

    def punctuation(self, char):
        self.whitespace()
        if self.i >= len(self.raw) or self.raw[self.i] != char:
            fail("type", "$", "Invalid JSON structure")
        self.i += 1
        self.token()

    def string(self):
        self.token()
        start = self.i
        self.i += 1
        escaped = False
        # Every decoded code point costs at least one byte and at most12 lexical
        # characters (surrogate escape pair). Bound the slice before json.loads.
        while self.i < len(self.raw):
            if self.i-start > 12*self.max_string+2:
                fail("bytes", "$", "Decoded string byte limit exceeded")
            c = self.raw[self.i]
            self.i += 1
            if c == '"' and not escaped:
                try:
                    value = json.loads(self.raw[start:self.i])
                    size = len(value.encode("utf-8", errors="strict"))
                except (ValueError, UnicodeError):
                    fail("encoding", "$", "Invalid JSON string or surrogate")
                self.string_bytes += size
                if size > self.max_string or self.string_bytes > self.max_strings:
                    fail("bytes", "$", "Decoded string byte limit exceeded")
                return value
            if ord(c) < 32:
                fail("encoding", "$", "Unescaped control in string")
            escaped = not escaped if c == "\\" else False
        fail("type", "$", "Unterminated string")

    def scalar(self):
        self.whitespace()
        self.negative_zero_token = False
        if self.i >= len(self.raw):
            fail("type", "$", "Missing JSON value")
        c = self.raw[self.i]
        if c == '"':
            return self.string()
        for literal, value in (("true", True), ("false", False), ("null", None)):
            if self.raw.startswith(literal, self.i):
                self.i += len(literal)
                self.token()
                return value
        if c in "-0123456789":
            start = self.i
            # Bound numeric lexeme before regex/conversion, including exponent.
            while self.i < len(self.raw) and self.raw[self.i] in "-+0123456789.eE":
                self.i += 1
                if self.i-start > 64:
                    fail("tokens", "$", "Numeric lexeme limit exceeded")
            token = self.raw[start:self.i]
            if not _NUMBER.fullmatch(token):
                fail("type", "$", "Invalid number token")
            self.token()
            value = float(token) if any(c in token for c in ".eE") else int(token)
            converted = float(value)
            self.negative_zero_token = converted == 0 and token.startswith("-")
            mantissa = token.lower().split("e")[0]
            nonzero = any(c in "123456789" for c in mantissa)
            if not math.isfinite(converted) or (converted == 0 and nonzero):
                fail("type", "$", "Number not representable as finite binary64")
            return value
        fail("type", "$", "Invalid scalar token")

    def data_span(self, depth):
        if depth > MAX_DEPTH:
            fail("depth", "$", "Container depth limit exceeded")
        start = self.i
        self.punctuation("[")
        count = 0
        float_ok = int_ok = bool_ok = True
        float_hash, int_hash, bool_hash = (hashlib.sha256() for _ in range(3))
        negative_zero = False
        self.whitespace()
        if self.i < len(self.raw) and self.raw[self.i] != "]":
            while True:
                value = self.scalar()
                count += 1
                if type(value) in (int, float):
                    f = -0.0 if self.negative_zero_token else float(value)
                    float_hash.update(struct.pack("<d", f))
                    negative_zero |= f == 0 and math.copysign(1., f) < 0
                    bool_ok = False
                    if type(value) is int and -(2**63) <= value < 2**63:
                        int_hash.update(struct.pack("<q", value))
                    else:
                        int_ok = False
                elif type(value) is bool:
                    bool_hash.update(bytes((int(value),)))
                    float_ok = int_ok = False
                else:
                    fail("type", "$", "Descriptor data must be flat numeric or boolean tokens")
                self.whitespace()
                if self.i < len(self.raw) and self.raw[self.i] == ",":
                    self.punctuation(",")
                else:
                    break
        self.punctuation("]")
        return _Span(start, self.i, count,
                     float_hash.hexdigest() if float_ok else None,
                     int_hash.hexdigest() if int_ok else None,
                     bool_hash.hexdigest() if bool_ok else None, negative_zero)

    def value(self, depth=0, path="$", data=False):
        self.whitespace()
        if self.i >= len(self.raw):
            fail("type", path, "Missing JSON value")
        c = self.raw[self.i]
        if c in "[{" and depth+1 > MAX_DEPTH:
            fail("depth", path, "Container depth limit exceeded")
        if c == "[" and data and self.defer:
            return self.data_span(depth+1)
        if c == "{":
            self.punctuation("{")
            out = {}
            self.whitespace()
            if self.i < len(self.raw) and self.raw[self.i] != "}":
                while True:
                    self.whitespace()
                    if self.i >= len(self.raw) or self.raw[self.i] != '"':
                        fail("type", path, "String object key required")
                    key = self.string()
                    if key in out:
                        fail("duplicate_key", path, "Duplicate decoded object key")
                    self.punctuation(":")
                    out[key] = self.value(depth+1, path+"/"+key, key == "data")
                    self.whitespace()
                    if self.i < len(self.raw) and self.raw[self.i] == ",":
                        self.punctuation(",")
                    else:
                        break
            self.punctuation("}")
            return out
        if c == "[":
            self.punctuation("[")
            out = []
            self.whitespace()
            if self.i < len(self.raw) and self.raw[self.i] != "]":
                while True:
                    out.append(self.value(depth+1, path))
                    self.whitespace()
                    if self.i < len(self.raw) and self.raw[self.i] == ",":
                        self.punctuation(",")
                    else:
                        break
            self.punctuation("]")
            return out
        return self.scalar()

    def document(self):
        out = self.value()
        self.whitespace()
        if self.i != len(self.raw):
            fail("type", "$", "Trailing JSON tokens")
        return out


class _Schema:
    def __init__(self, lexer):
        self.lexer = lexer
        self.elements = self.bytes = 0
        self.descriptors = []

    def descriptor(self, value, dtype, shape, path, geometry=False):
        keys(value, "dtype shape data sha256", path)
        enum(value["dtype"], [dtype], path+"/dtype")
        sequence(value["shape"], len(shape), path+"/shape")
        count = 1
        for actual, expected in zip(value["shape"], shape):
            integer(actual, 1, 500000, path+"/shape")
            if actual != expected:
                fail("count", path, "Descriptor shape mismatch")
            count *= actual
            if count > 500000:
                fail("resource", path, "Descriptor scalar count exceeded")
        data = value["data"]
        if type(data) is not _Span or data.count != count:
            fail("count", path, "Descriptor flat payload count mismatch")
        actual_hash = {"float64": data.float_hash, "int64": data.int_hash, "bool": data.bool_hash}[dtype]
        if actual_hash is None:
            fail("type", path, "Descriptor primitive type mismatch")
        hash_value(value["sha256"], path+"/sha256")
        if value["sha256"] != actual_hash:
            fail("hash", path, "Descriptor payload hash mismatch")
        if geometry and data.negative_zero:
            fail("geometry", path, "Negative zero geometry forbidden")
        self.elements += count
        self.bytes += count*(1 if dtype == "bool" else 8)
        if self.elements > 500000 or self.bytes > 96*1024**2:
            fail("resource", path, "Combined descriptor capacity exceeded")
        self.descriptors.append((value, path))

    def vector(self, value, minimum, maximum, path, geometry=False):
        keys(value, "dtype shape data sha256", path)
        sequence(value["shape"], 1, path+"/shape")
        n = integer(value["shape"][0], minimum, maximum, path+"/shape")
        self.descriptor(value, "float64", [n], path, geometry)
        return n

    def values(self, descriptor):
        span = descriptor["data"]
        # Only geometry/prior values call this, after complete schema preflight.
        data = json.loads(self.lexer.raw[span.start:span.end])
        return [float(x) for x in data] if descriptor["dtype"] == "float64" else data

    def frame(self, v, path):
        keys(v, "axes coordinate_unit vertical_positive crs vertical_datum origin transform_sha256", path)
        for key, literal in (("axes", "ENU"), ("coordinate_unit", "m"), ("vertical_positive", "up")):
            enum(v[key], [literal], path+"/"+key)
        for key in ("crs", "vertical_datum"):
            text(v[key], path+"/"+key)
        self.descriptor(v["origin"], "float64", [3], path+"/origin", True)
        hash_value(v["transform_sha256"], path+"/transform_sha256")

    def field(self, v, path):
        keys(v, "kind F_nT I_deg D_deg reference_epoch provenance source_sha256 spatial_policy", path)
        enum(v["kind"], ["uniform_inducing_field"], path)
        enum(v["spatial_policy"], ["explicit_uniform_approximation"], path)
        for key, bounds in (("F_nT", (1, 1e6)), ("I_deg", (-90, 90)), ("D_deg", (-180, 180))):
            v[key] = real(v[key], *bounds, path+"/"+key, strict_upper=key == "D_deg")
        text(v["reference_epoch"], path)
        text(v["provenance"], path)
        hash_value(v["source_sha256"], path)

    def parameters(self, node, path):
        op, p = node["operation"], node["parameters"]
        variants = {
            "original": ("kind", "identity"),
            "frame_conversion": ("kind from_frame to_frame transform_sha256", "external_frame_conversion"),
            "background_subtraction": ("kind field", "subtract_uniform_F"),
            "linear_projection": ("kind field component_order", "projection_of_secondary"),
            "total_norm_difference": ("kind field", "norm_total_minus_F"),
            "declared_external_correction": ("kind record_sha256 bundle_sha256", "external_preprocessed"),
            "m03_processed_eligible": ("kind bundle_sha256 descriptor_sha256 quantity approved_epoch", "m03_approved_output")}
        enum(op, variants, path)
        expected, tag = variants[op]
        keys(p, expected, path+"/parameters")
        enum(p["kind"], [tag], path+"/parameters/kind")
        for key in p:
            if key.endswith("sha256"):
                hash_value(p[key], path+"/parameters/"+key)
        if "field" in p:
            self.field(p["field"], path+"/parameters/field")
        if op == "frame_conversion":
            self.frame(p["from_frame"], path+"/parameters/from_frame")
            self.frame(p["to_frame"], path+"/parameters/to_frame")
        if op == "linear_projection" and p["component_order"] != ["E", "N", "U"]:
            fail("enum", path, "Exact ENU component order required")
        if op == "m03_processed_eligible":
            enum(p["quantity"], QUANTITIES, path)
            text(p["approved_epoch"], path)

    def validate(self, doc):
        keys(doc, "schema source frame inducing_field acquisition processing geometry observations noise prior policy intent", "$")
        enum(doc["schema"], ["magnetic-survey-inversion-1"], "$/schema")
        enum(doc["intent"], ["local_calibrate", "local_evaluate", "replay_only"], "$/intent")
        if doc["intent"] == "replay_only":
            fail("endpoint", "$/intent", "Replay requires a validated result bundle")
        source = doc["source"]
        keys(source, "id kind original_sha256 original_bytes provider_url rights scope citation", "$/source")
        identifier(source["id"], "$/source/id")
        enum(source["kind"], ["field", "authored_synthetic"], "$/source/kind")
        hash_value(source["original_sha256"], "$/source/original_sha256")
        integer(source["original_bytes"], 1, 2**63-1, "$/source/original_bytes")
        if source["provider_url"] is not None:
            text(source["provider_url"], "$/source/provider_url")
            try:
                parsed = urlsplit(source["provider_url"])
            except ValueError:
                fail("physical_metadata", "$/source/provider_url", "Invalid citation URL")
            if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
                fail("physical_metadata", "$/source/provider_url", "HTTP citation URL required")
        enum(source["rights"], RIGHTS, "$/source/rights")
        enum(source["scope"], ["complete_acquisition", "declared_subset"], "$/source/scope")
        text(source["citation"], "$/source/citation")
        self.frame(doc["frame"], "$/frame")
        self.field(doc["inducing_field"], "$/inducing_field")
        a = doc["acquisition"]
        keys(a, "row_ids group_ids timestamp_policy timestamps geometry_basis", "$/acquisition")
        if type(a["row_ids"]) is not list:
            fail("type", "$/acquisition/row_ids", "Original row identifiers required")
        n = integer(len(a["row_ids"]), 1, 2048, "$/acquisition/row_ids")
        sequence(a["group_ids"], n, "$/acquisition/group_ids")
        for key in ("row_ids", "group_ids"):
            for v in a[key]:
                identifier(v, "$/acquisition/"+key)
        if len(set(a["row_ids"])) != n:
            fail("geometry", "$/acquisition/row_ids", "Duplicate original identity")
        enum(a["timestamp_policy"], ["recorded_utc", "unavailable_declared"], "$/acquisition/timestamp_policy")
        if a["timestamp_policy"] == "unavailable_declared":
            if a["timestamps"] is not None:
                fail("type", "$/acquisition/timestamps", "Explicit null required")
        else:
            sequence(a["timestamps"], n, "$/acquisition/timestamps")
            for v in a["timestamps"]:
                if type(v) is not str or not _UTC.fullmatch(v):
                    fail("physical_metadata", "$/acquisition/timestamps", "Strict recorded UTC required")
                try:
                    datetime.datetime.fromisoformat(v[:-1])
                except ValueError:
                    fail("physical_metadata", "$/acquisition/timestamps", "Invalid Gregorian UTC")
        text(a["geometry_basis"], "$/acquisition/geometry_basis")
        p = doc["processing"]
        keys(p, "nodes final_node quantity background_relation eligibility", "$/processing")
        enum(p["quantity"], QUANTITIES, "$/processing/quantity")
        enum(p["background_relation"], [RELATIONS[QUANTITIES.index(p["quantity"])]], "$/processing/background_relation")
        enum(p["eligibility"], ["explicit_induced_assumption"], "$/processing/eligibility")
        identifier(p["final_node"], "$/processing/final_node")
        if type(p["nodes"]) is not list or not 1 <= len(p["nodes"]) <= 64:
            fail("count", "$/processing/nodes", "Bounded processing DAG required")
        nodes = {}
        roots = 0
        for i, node in enumerate(p["nodes"]):
            path = f"$/processing/nodes/{i}"
            keys(node, "id parents operation input_sha256 output_sha256 parameters_sha256 parameters citation", path)
            identifier(node["id"], path)
            if node["id"] in nodes:
                fail("lineage", path, "Duplicate processing node")
            parents = node["parents"]
            if type(parents) is not list or len(parents) > 8:
                fail("count", path, "Bounded parent list required")
            for parent in parents:
                identifier(parent, path)
            if len(set(parents)) != len(parents) or any(parent not in nodes for parent in parents):
                fail("lineage", path, "Unique earlier parents required")
            for key in ("input_sha256", "output_sha256", "parameters_sha256"):
                hash_value(node[key], path+"/"+key)
            text(node["citation"], path)
            self.parameters(node, path)
            if node["operation"] == "original":
                roots += 1
                if parents or node["input_sha256"] != source["original_sha256"]:
                    fail("lineage", path, "Original source root mismatch")
            else:
                if not parents:
                    fail("lineage", path, "Non-original node requires parents")
                hashes = [nodes[x]["output_sha256"] for x in parents]
                expected = hashes[0] if len(hashes) == 1 else hashlib.sha256("\n".join(hashes).encode("ascii")).hexdigest()
                if expected != node["input_sha256"]:
                    fail("lineage", path, "Parent input identity mismatch")
            nodes[node["id"]] = node
        if roots != 1 or p["final_node"] not in nodes:
            fail("lineage", "$/processing", "One original root and known final node required")
        reachable, stack = set(), [p["final_node"]]
        while stack:
            key = stack.pop()
            if key not in reachable:
                reachable.add(key)
                stack.extend(nodes[key]["parents"])
        if reachable != set(nodes):
            fail("lineage", "$/processing", "Disconnected processing nodes forbidden")
        c = 3 if p["quantity"] == QUANTITIES[0] else 1
        d = n*c
        g = doc["geometry"]
        keys(g, "receivers_m usable qc_reason mesh partition", "$/geometry")
        self.descriptor(g["receivers_m"], "float64", [n, 3], "$/geometry/receivers_m", True)
        self.descriptor(g["usable"], "bool", [n], "$/geometry/usable")
        sequence(g["qc_reason"], n, "$/geometry/qc_reason")
        for v in g["qc_reason"]:
            enum(v, QC, "$/geometry/qc_reason")
        mesh = g["mesh"]
        keys(mesh, "origin_m widths_x_m widths_y_m widths_z_m active", "$/geometry/mesh")
        self.descriptor(mesh["origin_m"], "float64", [3], "$/geometry/mesh/origin_m", True)
        dims = [self.vector(mesh[key], 1, 64, "$/geometry/mesh/"+key, True)
                for key in ("widths_x_m", "widths_y_m", "widths_z_m")]
        full = math.prod(dims)
        if full > 4096:
            fail("resource", "$/geometry/mesh", "Full-cell capacity exceeded")
        self.descriptor(mesh["active"], "bool", [full], "$/geometry/mesh/active")
        # Count active mask directly from bounded lexeme span, no numeric buffer.
        active_span = mesh["active"]["data"]
        active = self.lexer.raw[active_span.start:active_span.end].count("true")
        integer(active, 1, 2048, "$/geometry/mesh/active")
        part = g["partition"]
        keys(part, "name block_width_m buffer_m seed", "$/geometry/partition")
        enum(part["name"], ["magnetic-geometry-seal-1"], "$/geometry/partition/name")
        self.descriptor(part["block_width_m"], "float64", [2], "$/geometry/partition/block_width_m", True)
        part["buffer_m"] = real(part["buffer_m"], 0, 1e5, "$/geometry/partition/buffer_m")
        if part["buffer_m"] == 0 and math.copysign(1., part["buffer_m"]) < 0:
            fail("geometry", "$/geometry/partition/buffer_m", "Negative zero geometry forbidden")
        integer(part["seed"], 104729, 104729, "$/geometry/partition/seed")
        obs = doc["observations"]
        keys(obs, "quantity unit values values_sha256", "$/observations")
        enum(obs["quantity"], [p["quantity"]], "$/observations/quantity")
        enum(obs["unit"], ["nT"], "$/observations/unit")
        self.descriptor(obs["values"], "float64", [n, c], "$/observations/values")
        hash_value(obs["values_sha256"], "$/observations/values_sha256")
        if obs["values_sha256"] != obs["values"]["sha256"] or nodes[p["final_node"]]["output_sha256"] != obs["values_sha256"]:
            fail("hash", "$/observations", "Final observation identity mismatch")
        noise = doc["noise"]
        keys(noise, "kind unit values basis citation cross_partition_dependence", "$/noise")
        enum(noise["kind"], ["diagonal_sd", "full_covariance"], "$/noise/kind")
        covariance = noise["kind"] == "full_covariance"
        enum(noise["unit"], ["nT^2" if covariance else "nT"], "$/noise/unit")
        enum(noise["basis"], ["measured_gaussian", "propagated_gaussian", "explicit_conditional_gaussian"], "$/noise/basis")
        enum(noise["cross_partition_dependence"], ["declared_absent", "possible_not_removed"], "$/noise/cross_partition_dependence")
        text(noise["citation"], "$/noise/citation")
        if covariance and d > 512:
            fail("resource", "$/noise", "Full covariance component cap exceeded")
        self.descriptor(noise["values"], "float64", [d, d] if covariance else [n, c], "$/noise/values")
        prior = doc["prior"]
        keys(prior, "lower_si upper_si start_si reference_si chi_scale_si lengths_m reference_in_smooth spatial_weights basis", "$/prior")
        for key in ("lower_si", "upper_si", "start_si", "reference_si"):
            self.descriptor(prior[key], "float64", [active], "$/prior/"+key)
        prior["chi_scale_si"] = real(prior["chi_scale_si"], .01, .01, "$/prior/chi_scale_si")
        self.descriptor(prior["lengths_m"], "float64", [3], "$/prior/lengths_m")
        if prior["reference_in_smooth"] is not True:
            fail("enum", "$/prior/reference_in_smooth", "Explicit true required")
        enum(prior["spatial_weights"], ["none"], "$/prior/spatial_weights")
        text(prior["basis"], "$/prior/basis")
        policy = doc["policy"]
        keys(policy, "name betas penalties optimizer_binding resource_profile", "$/policy")
        enum(policy["name"], ["magnetic-nested-l2-irls-1"], "$/policy/name")
        sequence(policy["betas"], 8, "$/policy/betas")
        policy["betas"] = [real(x, b, b, "$/policy/betas") for x, b in zip(policy["betas"], BETAS)]
        if policy["penalties"] != ["l2", "sparse_smallness"]:
            fail("enum", "$/policy/penalties", "Frozen penalty order required")
        enum(policy["resource_profile"], ["local_bounded", "online_proposed"], "$/policy/resource_profile")
        binding = policy["optimizer_binding"]
        keys(binding, "accepted_source accepted_export epoch", "$/policy/optimizer_binding")
        for key, value in binding.items():
            if value is not None:
                (hash_value if key == "accepted_source" else text)(value, "$/policy/optimizer_binding/"+key)
        if any(x is None for x in binding.values()) and not all(x is None for x in binding.values()):
            fail("dependency", "$/policy/optimizer_binding", "Binding must be all-null or all-explicit")
        b = 8*(18*d*active+6*d*d+8*active*active+64*(d+active)+8*full)
        if 3*n*active > 12582912 or b > 805306368:
            fail("resource", "$/geometry", "Conservative working capacity exceeded")
        if policy["resource_profile"] == "online_proposed" and (n > 512 or active > 256 or d > 1536):
            fail("resource", "$/policy", "Online proposed count cap exceeded")
        self.preflight = dict(rows=n, components=c, active_cells=active, full_cells=full,
                              descriptor_bytes=self.bytes, scalar_elements=self.elements,
                              conservative_bytes=b)

    def materialize(self, doc):
        def visit(v, likelihood=False):
            if type(v) is dict:
                out = {}
                for key, value in v.items():
                    if type(value) is _Span:
                        if not likelihood:
                            out[key] = self.values(v)
                    else:
                        out[key] = visit(value, likelihood)
                return out
            if type(v) is list:
                return [visit(x, likelihood) for x in v]
            return v
        # Metadata cap excludes numeric buffers but includes every shape/hash/key.
        metadata = visit(doc, True)
        if len(canonical(metadata)) > 262144:
            fail("resource", "$", "Metadata byte limit exceeded")
        result = {key: visit(v, key in ("observations", "noise")) for key, v in doc.items()}
        for node in result["processing"]["nodes"]:
            if digest(node["parameters"]) != node["parameters_sha256"]:
                fail("hash", "$/processing", "Typed parameters canonical hash mismatch")
        g, prior = result["geometry"], result["prior"]
        if any(flag != (reason == "accepted") for flag, reason in zip(g["usable"]["data"], g["qc_reason"])):
            fail("geometry", "$/geometry", "QC reason and usability disagree")
        for key in ("receivers_m",):
            if any(abs(x) > 1e7 for x in g[key]["data"]):
                fail("geometry", "$/geometry", "Coordinate bound exceeded")
        for origin in (result["frame"]["origin"]["data"], g["mesh"]["origin_m"]["data"]):
            if any(abs(x) > 1e7 for x in origin):
                fail("geometry", "$/geometry", "Origin bound exceeded")
        for key in ("widths_x_m", "widths_y_m", "widths_z_m"):
            widths = g["mesh"][key]["data"]
            if any(not .001 <= x <= 1e5 for x in widths) or sum(widths) > 1e5:
                fail("geometry", "$/geometry/mesh", "Declared width/span bound exceeded")
        for x in g["partition"]["block_width_m"]["data"]:
            real(x, 0, 1e5, "$/geometry/partition", strict_lower=True)
        for x in prior["lengths_m"]["data"]:
            real(x, 0, 1e5, "$/prior/lengths_m", strict_lower=True)
        for lo, hi, start, ref in zip(*(prior[k]["data"] for k in ("lower_si", "upper_si", "start_si", "reference_si"))):
            if not 0 <= lo < hi <= .1 or not lo <= start <= hi or not lo <= ref <= hi:
                fail("physical_metadata", "$/prior", "Physical SI bounds/start/reference mismatch")
        return result


class SurveyHandle:
    """Private byte owner, not a solver object or a tamperproof security boundary."""

    __slots__ = ("__raw", "__metadata", "__preflight")

    def __init__(self, raw, metadata, preflight, *, _factory=None):
        if _factory is not _FACTORY:
            fail("type", "$", "Handles originate only from closed byte parsing")
        self.__raw, self.__metadata, self.__preflight = raw, metadata, preflight

    def metadata(self):
        return copy.deepcopy(self.__metadata)

    @property
    def preflight(self):
        return MappingProxyType(self.__preflight.copy())

    def _export_bytes(self):
        return self.__raw


def parse_request(raw):
    """Validate bounded bytes and return metadata-only original-order snapshots."""
    lexer = _Lexer(raw)
    doc = lexer.document()
    schema = _Schema(lexer)
    schema.validate(doc)
    return SurveyHandle(raw, schema.materialize(doc), schema.preflight, _factory=_FACTORY)
