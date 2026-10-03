"""Local-only test-first JSON controls; authored data, never field admission.

Running this file directly with a named profile emits a cold stdlib-only resource
receipt. The pytest tests below separately exercise all fourteen approved gates.
"""

from copy import deepcopy
from hashlib import sha256
import importlib
import importlib.metadata
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import time
import tracemalloc


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "data-pipeline/gravity_station_json.py"
CORE_SHA = "7863699269b491c2895bcf030d3fb65cf27ac32a652fce91112bc2c7c9c73321"
SOURCE_PINS = {
    "gravity_processing.py": CORE_SHA,
    "gravity_station_adapter.py": "b770b16ef87e83dd92f65a90472145ef93a525a9cedf7f55ee3e6f20f8a10cf8",
    "gravity_transforms.py": "d11d0f207c89c308c9f8711da2a31b84b8adaeb0c12597a5ecc89ce527fdecf0",
    "edi.py": "1a6226f34cd36e3e30f6406a296c6f4e3bc38aa93ca5bda1d4f4428d3852b543",
}
RAW_CAP = 16 * 1024 * 1024
CANON_CAP = 8 * 1024 * 1024
PRIVATE = "PRIVATE_INPUT_MARKER_D:/not-a-real-source.json"


def survey(count=1):
    return {
        "schema_version": "gravity-stations-1", "state": "observed_absolute", "history": [],
        "metadata": {
            "source_kind": "synthetic_control", "source_sha256": "a" * 64,
            "source_citation": "Authored JSON structural controls, not field observations",
            "rights": "Authored test controls", "crs": "EPSG:4326", "reference_ellipsoid": "WGS84",
            "height_datum": "ellipsoidal", "height_unit": "m", "height_sign": "upward",
            "gravity_unit": "mGal", "gravity_sign": "downward", "gravity_quantity": "absolute_gravity",
            "gravity_datum": "Declared analytical control", "tide_system": "tide_free",
            "instrument_processing": {
                k: {"status": "applied" if k == "calibration" else "not_applicable",
                    "citation": "Authored calibrated control without drift or tide"}
                for k in ("calibration", "drift", "tide")
            },
        },
        "stations": [{
            "station_id": f"control-{i}", "latitude_deg": 45.0, "longitude_deg": i / 100,
            "receiver_height_m": 0, "surface_height_m": 0, "original_value": 980000,
            "value_mgal": 980000, "gravity_sigma": 0, "receiver_sigma_m": 0,
            "surface_sigma_m": 0, "latitude_sigma_deg": 0,
        } for i in range(count)],
    }


def encoded(value, *, ascii=True, sort=True):
    # Fixture/oracle construction may encode a whole copy; the helper may not.
    return json.dumps(value, ensure_ascii=ascii, sort_keys=sort, separators=(",", ":"), allow_nan=False).encode()


def history_root(count=2, state="terrain_adjusted_disturbance"):
    obj = survey(count)
    ids = [s["station_id"] for s in obj["stations"]]
    ref = {"ellipsoid": "WGS84", "height_reference": "WGS84_ellipsoid", "boule": "0.5.0"}
    params = [ref, {**ref, "height_term": "gamma(phi,0)-gamma(phi,h)"}, {
        "harmonica": "0.7.0", "density_kg_m3": 2670, "density_sigma_kg_m3": 0,
        "geometry": "land_infinite_plate", "height_reference": "WGS84_ellipsoid",
    }, {
        "kind": "additive_residual_to_plate", "unit": "mGal", "height_reference": "WGS84_ellipsoid",
        "density_kg_m3": 2600, "source_sha256": "b" * 64, "method": "Authored structural history",
        "station_ids": ids, "additions_mgal": [10] * count, "sigma_mgal": [0] * count,
    }]
    names = ("normal_reference", "elevation_reference", "bouguer_plate", "terrain_residual")
    lengths = {"observed_absolute": 0, "gravity_disturbance": 2,
               "bouguer_disturbance": 3, "terrain_adjusted_disturbance": 4}
    obj["state"] = state
    obj["history"] = [{"name": names[i], "parameters": deepcopy(params[i]), "additions_mgal": [0] * count,
                       "input_values_sha256": "c" * 64, "output_values_sha256": "d" * 64}
                      for i in range(lengths[state])]
    return obj


def upper_root(target=CANON_CAP):
    obj = survey(400)
    remaining = target - len(encoded(obj))
    assert remaining >= 0
    for station in obj["stations"]:
        count = min(8192 - len(station["station_id"].encode()), remaining // 6)
        station["station_id"] += "\x01" * count
        remaining -= 6 * count
    assert remaining < 6
    obj["metadata"]["source_citation"] += "x" * remaining
    assert len(encoded(obj)) == target
    return obj


def profile_raw(profile):
    if profile == "nominal":
        return encoded(survey())
    if profile == "upper400":
        return encoded(history_root(400))
    if profile in ("canonical-upper", "canonical-over"):
        return encoded(upper_root(CANON_CAP + (profile == "canonical-over")))
    if profile in ("raw-upper", "raw-over"):
        raw = encoded(survey())
        return raw + b" " * (RAW_CAP + (profile == "raw-over") - len(raw))
    if profile == "malformed":
        tail = b'{"x":0,"\\u0078":1}'
        return b" " * (RAW_CAP - 1 - len(tail)) + tail
    if profile == "overflow":
        return encoded(survey()).replace(b'"gravity_sigma":0', b'"gravity_sigma":1e400')
    if profile == "nodes-over":
        return b"[" + b"0," * 199999 + b"0]"
    if profile == "depth-over":
        return b"[" * 17 + b"0" + b"]" * 17
    raise ValueError("Unknown authored benchmark profile")


def peak_process_bytes():
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
                    "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel, psapi = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise OSError("Resource telemetry unavailable")
        return counters.PeakWorkingSetSize, "Windows GetProcessMemoryInfo PeakWorkingSetSize bytes"
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak * (1 if sys.platform == "darwin" else 1024)), "getrusage ru_maxrss, platform-scaled bytes"


def cold_record(profile):
    process_start, cpu_start = time.perf_counter(), time.process_time()
    tracemalloc.start()
    raw = profile_raw(profile)
    raw_hash = sha256(raw).hexdigest()
    sys.path.insert(0, str(ROOT / "data-pipeline"))
    cold_start = time.perf_counter()
    boundary = importlib.import_module("gravity_station_json")
    calls = 0
    native = boundary._materialize

    def observed(data):
        nonlocal calls
        calls += 1
        return native(data)

    boundary._materialize = observed  # Test-only observation, no caller hook exposed by the helper.
    status, error = "accepted", None
    try:
        result = boundary.load_gravity_stations_json(raw)
    except boundary.GravityStationsJsonError as exc:
        status, error = "rejected", exc.code
        result = None
    cold_wall = (time.perf_counter() - cold_start) * 1000
    current, peak_alloc = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_rss, rss_method = peak_process_bytes()
    return {
        "schema": "geophysics.local-json-benchmark/v1", "profile": profile, "status": status, "error_code": error,
        "python": sys.version, "implementation": sys.implementation.name, "platform": sys.platform,
        "module_sha256": sha256(MODULE.read_bytes()).hexdigest(),
        "test_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "raw_bytes": len(raw), "raw_sha256": raw_hash,
        "canonical_bytes": sum(len(p.encode()) for p in json.JSONEncoder(
            sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).iterencode(result))
        if result is not None else None,
        "cold_helper_wall_ms": cold_wall, "process_wall_ms": (time.perf_counter() - process_start) * 1000,
        "process_cpu_ms": (time.process_time() - cpu_start) * 1000,
        "peak_tracemalloc_bytes": peak_alloc, "current_tracemalloc_bytes": current,
        "peak_process_bytes": peak_rss, "peak_process_method": rss_method, "materializer_calls": calls,
        "helper_scratch_bytes": 0, "scratch_basis": "no helper I/O, independently instrumented by separate gate",
        "trace_overhead_included": True, "synthetic_control": True, "host_admission": False,
    }


if __name__ == "__main__":
    print(json.dumps(cold_record(sys.argv[1]), sort_keys=True, allow_nan=False))
    raise SystemExit(0)


import pytest  # noqa: E402; direct cold mode above must work with CPython -S and stdlib only.


@pytest.fixture
def boundary():
    return importlib.import_module("gravity_station_json")


def rejected(boundary, raw, code=None):
    with pytest.raises(boundary.GravityStationsJsonError) as caught:
        boundary.load_gravity_stations_json(raw)
    error = caught.value
    if code is not None:
        assert error.code == code
    assert error.__context__ is None and error.__cause__ is None
    assert error.args == (error.message,) and str(error) == error.message
    assert set(vars(error)) == {"code", "field", "message"}
    return error


def test_exact_bytes_and_native_return(boundary, monkeypatch):
    class Hostile:
        def __len__(self):
            pytest.fail("Non-exact input method called")
        def read(self):
            pytest.fail("File-like method called")
    class Subbytes(bytes):
        def decode(self, *args, **kwargs):
            pytest.fail("Bytes subclass method called")
    raw = encoded(survey())
    for wrong in (raw.decode(), bytearray(raw), memoryview(raw), Subbytes(raw), survey(), Path("no-file"), Hostile()):
        rejected(boundary, wrong, "gravity_json_type")
    decoded = json.loads(raw)
    monkeypatch.setattr(boundary, "_materialize", lambda _: decoded)
    assert boundary.load_gravity_stations_json(raw) is decoded
    monkeypatch.undo()
    first, second = boundary.load_gravity_stations_json(raw), boundary.load_gravity_stations_json(raw)
    assert type(first) is dict and first == second == survey()
    first["stations"][0]["value_mgal"] = 123
    assert second["stations"][0]["value_mgal"] == 980000


def test_actual_raw_byte_boundary(boundary, monkeypatch):
    assert boundary.load_gravity_stations_json(profile_raw("raw-upper")) == survey()
    monkeypatch.setattr(boundary, "_scan", lambda _: pytest.fail("Raw excess reached scanner"))
    rejected(boundary, profile_raw("raw-over"), "gravity_json_limit")
    monkeypatch.undo()
    rejected(boundary, b"", "gravity_json_invalid")


def test_scanner_bounds_before_materialization(boundary, monkeypatch):
    monkeypatch.setattr(boundary, "_materialize", lambda _: pytest.fail("Hostile input reached final materializer"))
    positives = [b"[" * 16 + b"0" + b"]" * 16,
                 b"[" + b"0," * 199998 + b"0]", b'{"' + b"x" * 128 + b'":0}',
                 b'"' + b"x" * 8192 + b'"', b"0." + b"0" * 125 + b"1"]
    for raw in positives:
        assert boundary._scan(raw)[0] == len(encoded(json.loads(raw)))
    assert boundary._scan(positives[0])[2] == 16
    assert boundary._scan(positives[1])[1] == 200000
    for raw in (profile_raw("depth-over"), profile_raw("nodes-over"), b'{"' + b"x" * 129 + b'":0}',
                b'"' + b"x" * 8193 + b'"', b"0." + b"0" * 126 + b"1",
                b'"' + b"\\u00e1" * 4097 + b'"', b'{"' + b"\\u00e1" * 65 + b'":0}'):
        rejected(boundary, raw, "gravity_json_limit")


def test_strict_grammar_encoding_duplicates_and_nonfinite(boundary, monkeypatch):
    malformed = [b"{", b"[", b"[1,]", b'{"x":1,}', b"[1 2]", b'{"x" 1}', b'{"x":}',
                 b"truefalse", b"{} []", b"{}//comment", b"+1", b"01", b"-01", b"1.", b".1", b"1e+",
                 b"NaN", b"Infinity", b"-Infinity", b"1e400", b"-1e400", b"\xef\xbb\xbf{}",
                 b"\xff{}", b'"\xc0\x80"', b'"\xed\xa0\x80"', b'"\xf4\x90\x80\x80"',
                 b'"\xe2\x82"', b'"\x01"', b'"\\q"', b'"\\u000z"', b'"\\ud800"', b'"\\udfff"',
                 b'"\\ud800\\u0041"', b'"\\udfff\\ud800"', b'"\\ud800\\ud800"', b"{}\x0b",
                 b'{"x":0,"x":1}', b'{"x":0,"\\u0078":1}', b'{"a":{"b":0,"\\u0062":1}}',
                 b'{"\\ud834\\udd1e":0,"\xf0\x9d\x84\x9e":1}']
    malformed += ["{}".encode("utf-16"), "{}".encode("utf-32")]
    monkeypatch.setattr(boundary, "_materialize", lambda _: pytest.fail("Grammar error reached materializer"))
    for raw in malformed:
        rejected(boundary, raw, "gravity_json_invalid")
    for raw in (b'"\\ud834\\udd1e"', b'"\xf0\x9d\x84\x9e"', b'{"a": [true,false,null,{},[]]}'):
        assert boundary._scan(raw)[0] == len(encoded(json.loads(raw)))
    monkeypatch.undo()
    for raw in (b"[]", b"1", b"null", b"false", b'"text"'):
        rejected(boundary, raw, "gravity_json_contract")


def test_numeric_unicode_semantics_and_integer_bounds(boundary):
    for token in (b"1", b"1.0", b"1e0", b"-0", b"-0.0", b"0e-999", b"-1e-999", b"5e-324",
                  b"1.7976931348623157e308", b"9007199254740991", b"-9007199254740991", b"9007199254740992.0"):
        raw = encoded(survey()).replace(b'"value_mgal":980000', b'"value_mgal":' + token)
        native = json.loads(raw)["stations"][0]["value_mgal"]
        got = boundary.load_gravity_stations_json(raw)["stations"][0]["value_mgal"]
        assert type(got) is type(native) and got == native
        assert math.copysign(1, got) == math.copysign(1, native)
    for token in (b"9007199254740992", b"-9007199254740992"):
        rejected(boundary, encoded(survey()).replace(b'"value_mgal":980000', b'"value_mgal":' + token),
                 "gravity_json_limit")
    for key in set(survey()["stations"][0]) - {"station_id"}:
        for invalid in (True, False, None, "0"):
            obj = survey()
            obj["stations"][0][key] = invalid
            rejected(boundary, encoded(obj), "gravity_json_contract")
    obj = survey(2)
    obj["stations"][0]["station_id"] = "\u00e9"
    obj["stations"][1]["station_id"] = "e\u0301"
    obj["metadata"]["source_citation"] += " \U0001d11e \u00e1"
    assert boundary.load_gravity_stations_json(encoded(obj)) == boundary.load_gravity_stations_json(encoded(obj, ascii=False)) == obj


def test_canonical_precount_and_scientific_vectors(boundary, monkeypatch):
    vectors = [(1, "2bfd14f43d17fc7cea24e0917a8879b4b2f880b8baeec1b9d90fbaad655e71bd"),
               (1.0, "3b6b06ecd1c968c8e738e0f11c4bb361fca80a9a694de22fe66a05286afbd081"),
               (-0.0, "a8a313cade05001e69f7ddb5db01e1e2d06fb8f6913ab492cc4506d4e65d465a"),
               (1e-7, "ff7a1315299260617fe404199e54e6d976a0b03e47da54fccec073c2fa48ff5c")]
    for number, digest in vectors:
        raw = encoded({"n": number})
        assert sha256(raw).hexdigest() == digest
        assert boundary._scan(raw)[0] == len(raw)
    assert sha256(encoded({"s": "\u00e1"})).hexdigest() == "e74e492be1c93dbcb256ec215ca9b13edd33816ed36b4132c2984b04f839afde"
    rng = random.Random(71931)
    chars = ['"', "\\", "\x00", "\b", "\t", "\n", "\f", "\r", "\x7f", "\u00e1", "\u2028", "\U0001d11e"]
    for _ in range(100):
        value = {"z": [rng.random(), rng.randrange(-100, 100), "".join(rng.choices(chars, k=40)), None],
                 "a": {"x": False, "y": []}}
        raw = json.dumps(value, ensure_ascii=rng.choice((True, False)), indent=2).encode()
        assert boundary._scan(raw)[0] == len(encoded(value))
    raw = encoded(upper_root())
    assert boundary.load_gravity_stations_json(raw) == json.loads(raw)
    monkeypatch.setattr(boundary, "_materialize", lambda _: pytest.fail("Canonical overflow materialized"))
    rejected(boundary, encoded(upper_root(CANON_CAP + 1)), "gravity_json_limit")
    monkeypatch.undo()
    # Cross-check disagreement must never be silently accepted.
    original = boundary._scan
    monkeypatch.setattr(boundary, "_scan", lambda raw: (original(raw)[0] + 1, *original(raw)[1:]))
    rejected(boundary, encoded(survey()), "gravity_json_invalid")


def test_exact_root_metadata_and_station_contract(boundary):
    for count in (1, 400):
        assert boundary.load_gravity_stations_json(encoded(survey(count))) == survey(count)
    for count in (0, 401):
        rejected(boundary, encoded(survey(count)), "gravity_json_contract")
    for unit in ("mGal", "m/s^2", "microGal"):
        for sign in ("upward", "downward"):
            obj = survey()
            obj["metadata"].update(gravity_unit=unit, gravity_sign=sign)
            assert boundary.load_gravity_stations_json(encoded(obj)) == obj
    obj = survey()
    obj["metadata"].update(height_datum="orthometric", geoid_model="Explicit supplied model")
    obj["stations"][0].update(geoid_m=20, geoid_sigma_m=0)
    assert boundary.load_gravity_stations_json(encoded(obj)) == obj
    objects = [(survey(), ()), (survey(), ("metadata",)), (survey(), ("metadata", "instrument_processing")),
               (survey(), ("metadata", "instrument_processing", "calibration")), (survey(), ("stations", 0))]
    for root, path in objects:
        nested = root
        for p in path:
            nested = nested[p]
        for key in tuple(nested):
            changed = deepcopy(root)
            node = changed
            for p in path:
                node = node[p]
            del node[key]
            rejected(boundary, encoded(changed), "gravity_json_contract")
        nested[PRIVATE] = 0
        rejected(boundary, encoded(root), "gravity_json_contract")
    for path, value in [(('metadata', 'crs'), 'EPSG:3857'), (('metadata', 'source_kind'), 'unknown'),
                        (('metadata', 'height_datum'), 'unknown'), (('metadata', 'gravity_sign'), 'unknown'),
                        (('metadata', 'gravity_unit'), 'unknown'), (('metadata', 'source_sha256'), 'A' * 64),
                        (('metadata', 'source_citation'), ' '), (('stations', 0, 'latitude_deg'), 91),
                        (('stations', 0, 'longitude_deg'), -181), (('stations', 0, 'gravity_sigma'), -1)]:
        obj = survey()
        node = obj
        for p in path[:-1]:
            node = node[p]
        node[path[-1]] = value
        rejected(boundary, encoded(obj), "gravity_json_contract")
    obj = survey(2)
    obj["stations"][1]["station_id"] = obj["stations"][0]["station_id"]
    rejected(boundary, encoded(obj), "gravity_json_contract")
    obj = survey()
    obj["metadata"]["instrument_processing"]["calibration"]["status"] = "not_applicable"
    rejected(boundary, encoded(obj), "gravity_json_contract")
    for key in ("geoid_m", "geoid_sigma_m"):
        obj = survey()
        obj["stations"][0][key] = 0
        rejected(boundary, encoded(obj), "gravity_json_contract")
    obj = survey()
    obj["metadata"]["geoid_model"] = "Not permitted"
    rejected(boundary, encoded(obj), "gravity_json_contract")


def test_exact_history_shapes_without_numerical_replay(boundary):
    for state in ("observed_absolute", "gravity_disturbance", "bouguer_disturbance", "terrain_adjusted_disturbance"):
        obj = history_root(state=state)
        assert boundary.load_gravity_stations_json(encoded(obj)) == obj
    base = history_root()
    for path in [("history",), ("history", 0, "parameters"), ("history", 3, "parameters")]:
        obj = deepcopy(base)
        node = obj
        for p in path[:-1]:
            node = node[p]
        node[path[-1]] = [] if path == ("history",) else {"wrong": True}
        rejected(boundary, encoded(obj), "gravity_json_contract")
    for index in range(4):
        for key in tuple(base["history"][index]):
            obj = deepcopy(base)
            del obj["history"][index][key]
            rejected(boundary, encoded(obj), "gravity_json_contract")
        for key in tuple(base["history"][index]["parameters"]):
            obj = deepcopy(base)
            del obj["history"][index]["parameters"][key]
            rejected(boundary, encoded(obj), "gravity_json_contract")
        for key, value in (("name", "unknown"), ("input_values_sha256", "bad"), ("additions_mgal", [0])):
            obj = deepcopy(base)
            obj["history"][index][key] = value
            rejected(boundary, encoded(obj), "gravity_json_contract")
    obj = deepcopy(base)
    obj["history"][3]["parameters"]["station_ids"].reverse()
    rejected(boundary, encoded(obj), "gravity_json_contract")
    # Numerical mismatch is deliberately retained, never repaired by the loader.
    assert base["history"][3]["additions_mgal"] != base["history"][3]["parameters"]["additions_mgal"]
    assert boundary.load_gravity_stations_json(encoded(base)) == base


def test_safe_typed_errors_and_no_decoder_context(boundary, monkeypatch):
    for raw in (b'{"' + PRIVATE.encode() + b'":', b'{"x":0,"x":1}', encoded({PRIVATE: 0}), b"1e400"):
        error = rejected(boundary, raw)
        assert PRIVATE not in str(error) + repr(vars(error))
        assert len(error.field.encode("ascii")) <= 160 and not hasattr(error, "doc")
    with monkeypatch.context() as patch:
        def broken(*args, **kwargs):
            raise json.JSONDecodeError(PRIVATE, PRIVATE, 0)
        patch.setattr(boundary.json, "loads", broken)
        rejected(boundary, encoded(survey()), "gravity_json_invalid")
    with monkeypatch.context() as patch:
        def broken(*args, **kwargs):
            raise UnicodeDecodeError("utf8", PRIVATE.encode(), 0, 1, PRIVATE)
        patch.setattr(boundary.json.JSONEncoder, "iterencode", broken)
        rejected(boundary, encoded(survey()), "gravity_json_invalid")


def test_stdlib_only_no_io_hooks_or_global_changes(boundary):
    import ast
    tree = ast.parse(MODULE.read_text())
    imports = {node.module.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports |= {alias.name.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert imports <= {"__future__", "json", "math"}
    source = MODULE.read_text()
    for forbidden in ("object_hook", "object_pairs_hook", "parse_float=", "parse_int=", "parse_constant=",
                      "setrecursionlimit", "set_int_max_str_digits", "deepcopy", "getenv", "environ", "open("):
        assert forbidden not in source
    program = r'''
import builtins,copy,json,math,os,socket,subprocess,sys,types
code=compile(builtins.open(sys.argv[1],encoding="utf8").read(),sys.argv[1],"exec")
raw=sys.stdin.buffer.read()
before=(sys.getrecursionlimit(),sys.get_int_max_str_digits(),json.loads,json.dumps,json.JSONEncoder)
original_import=builtins.__import__
def guarded(name,*args,**kwargs):
    if name.split(".")[0] not in ("__future__","json","math"):
        raise AssertionError("Forbidden helper import: "+name)
    return original_import(name,*args,**kwargs)
def forbidden(*args,**kwargs):
    raise AssertionError("Forbidden helper side effect")
builtins.__import__=guarded
builtins.open=forbidden
socket.socket=forbidden
subprocess.Popen=forbidden
copy.copy=copy.deepcopy=forbidden
os.getenv=forbidden
module=types.ModuleType("isolated_json_boundary")
exec(code,module.__dict__)
assert module.load_gravity_stations_json(raw)["schema_version"]=="gravity-stations-1"
for bad in (b'{"a":0,"a":1}',b'1e400'):
    try: module.load_gravity_stations_json(bad)
    except module.GravityStationsJsonError as exc: assert exc.__context__ is None
    else: raise AssertionError("Malformed input accepted")
assert before==(sys.getrecursionlimit(),sys.get_int_max_str_digits(),json.loads,json.dumps,json.JSONEncoder)
assert not any(n in sys.modules for n in ("numpy","scipy","boule","harmonica","gravity_processing"))
'''
    child = subprocess.run([sys.executable, "-B", "-S", "-c", program, str(MODULE)], input=encoded(survey()),
                           capture_output=True, timeout=30, cwd=ROOT)
    assert child.returncode == 0, child.stderr.decode()
    assert child.stdout == child.stderr == b""


def test_structural_acceptance_is_not_scientific_admission(boundary):
    for name, pin in SOURCE_PINS.items():
        assert sha256((ROOT / "data-pipeline" / name).read_bytes()).hexdigest() == pin
    pins = {"boule": "0.5.0", "harmonica": "0.7.0", "numpy": "2.2.6", "scipy": "1.15.2"}
    for name, pin in pins.items():
        try:
            found = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pytest.skip(f"Real core gate UNRESOLVED: existing runtime lacks {name}; no installation authorized")
        assert found == pin, f"Existing runtime incompatible with pinned {name}"
    import gravity_processing as core
    import gravity_station_adapter as adapter
    assert Path(core.__file__).resolve() == (ROOT / "data-pipeline/gravity_processing.py").resolve()
    assert Path(adapter.__file__).resolve() == (ROOT / "data-pipeline/gravity_station_adapter.py").resolve()
    cfg = {"target": "bouguer_disturbance", "uncertainty_model": "conservative_marginals",
           "density_kg_m3": 2670, "density_sigma_kg_m3": 0}
    for orthometric in (False, True):
        root = survey(2)
        if orthometric:
            root["metadata"].update(height_datum="orthometric", geoid_model="Authored fixed geoid declaration")
            for row in root["stations"]:
                row.update(geoid_m=20, geoid_sigma_m=0)
        native = boundary.load_gravity_stations_json(encoded(root))
        corrected = core.process_survey(native, cfg)
        assert corrected == core.process_survey(root, cfg)
        assert boundary.load_gravity_stations_json(encoded(corrected["dataset"])) == corrected["dataset"]
        request = {"schema_version": "gravity-station-adapter-request-1", "method": "gravity.station-corrections/v1",
                   "dataset": native, "config": cfg, "input_dataset_sha256": core.digest(native),
                   "submitted_config_sha256": core.digest(cfg)}
        assert adapter.run_station_corrections(request)["correction_result"] == corrected
    bads = []
    root = survey(2)
    root["stations"][0]["longitude_deg"], root["stations"][1]["longitude_deg"] = -180, 180
    bads.append(root)
    for changes in ({"receiver_height_m": -1}, {"value_mgal": 980001}, {"surface_height_m": -1}):
        root = survey()
        root["stations"][0].update(changes)
        bads.append(root)
    damaged = core.process_survey(survey(), {"target": "gravity_disturbance", "uncertainty_model": "independent_first_order"})["dataset"]
    damaged["history"][0]["input_values_sha256"] = "0" * 64
    bads.append(damaged)
    for root in bads:
        native = boundary.load_gravity_stations_json(encoded(root))
        assert native == root
        with pytest.raises(core.GravityContractError):
            core.process_survey(native, cfg)


def test_raw_and_supplied_source_hash_domains(boundary):
    obj = survey()
    obj["metadata"]["source_citation"] += "\u00e1"
    raws = [encoded(obj), encoded(obj, ascii=False, sort=False), json.dumps(obj, indent=2).encode()]
    assert len({sha256(raw).hexdigest() for raw in raws}) == 3
    digests = set()
    for raw in raws:
        before = sha256(raw).hexdigest()
        native = boundary.load_gravity_stations_json(raw)
        assert native == obj and native["metadata"]["source_sha256"] == "a" * 64
        assert sha256(raw).hexdigest() == before != native["metadata"]["source_sha256"]
        digests.add(sha256(encoded(native)).hexdigest())
    assert len(digests) == 1
    obj["stations"][0]["value_mgal"] = 1
    a = encoded(boundary.load_gravity_stations_json(encoded(obj)))
    obj["stations"][0]["value_mgal"] = 1.0
    b = encoded(boundary.load_gravity_stations_json(encoded(obj)))
    assert sha256(a).digest() != sha256(b).digest()


def test_local_resource_and_legacy_regression_evidence(boundary, tmp_path):
    profiles = ("nominal", "upper400", "canonical-upper", "raw-upper", "malformed", "overflow", "raw-over",
                "canonical-over", "depth-over", "nodes-over")
    for profile in profiles:
        child = subprocess.run([sys.executable, "-B", "-S", str(Path(__file__).resolve()), profile],
                               capture_output=True, cwd=tmp_path, timeout=180)
        assert child.returncode == 0 and child.stderr == b"", child.stderr.decode()
        receipt = json.loads(child.stdout)
        assert receipt["module_sha256"] == sha256(MODULE.read_bytes()).hexdigest()
        assert receipt["test_sha256"] == sha256(Path(__file__).read_bytes()).hexdigest()
        assert receipt["peak_process_bytes"] > 0 and receipt["peak_tracemalloc_bytes"] > 0
        assert receipt["helper_scratch_bytes"] == 0 and receipt["host_admission"] is False
        accepted = profile in profiles[:4]
        assert receipt["status"] == ("accepted" if accepted else "rejected")
        assert receipt["materializer_calls"] == int(accepted)
        # Explicit test artifacts only, not source/field data. tmp_path is fresh per execution.
        (tmp_path / f"{profile}.json").write_bytes(child.stdout)
        (tmp_path / f"{profile}.stderr.log").write_bytes(child.stderr)
    for name, pin in SOURCE_PINS.items():
        assert sha256((ROOT / "data-pipeline" / name).read_bytes()).hexdigest() == pin


def test_local_only_scope_and_nonclaims(boundary):
    assert set(boundary.load_gravity_stations_json(encoded(survey()))) == set(survey())
    import ast
    tree = ast.parse(MODULE.read_text())
    public = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_")]
    assert public == ["GravityStationsJsonError", "load_gravity_stations_json"]
    assert boundary.MAX_RAW_BYTES == RAW_CAP and boundary.MAX_CANONICAL_BYTES == CANON_CAP
    assert (boundary.MAX_DEPTH, boundary.MAX_NODES, boundary.MAX_KEY_BYTES, boundary.MAX_STRING_BYTES,
            boundary.MAX_NUMERIC_LEXEME, boundary.MAX_INTEGER) == (16, 200000, 128, 8192, 128, 9007199254740991)
    for name, pin in SOURCE_PINS.items():
        assert sha256((ROOT / "data-pipeline" / name).read_bytes()).hexdigest() == pin
