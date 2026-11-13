"""Original shot gathers -> actual acoustic FWI -> exact portable arrays.

No scientific import at module load or during byte/physical admission. The
canonical seismic producer is reused, not modified or supplied a truth model.
"""
from __future__ import annotations

import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import re
import struct
import threading
import time

SCHEMA = "geophysics.fwi-user-data/v1"
RESULT_SCHEMA = "geophysics.fwi-local-result/v1"
MAX_REQUEST = 16384
MAX_MANIFEST = 2*1024*1024
MAX_ARRAY = 16*1024*1024
MAX_GENERATION = 64*1024*1024
METHODS = ("fwi-l2", "fwi-multiscale")
SHAPE = [96, 128]
SOURCES = [[300, 75], [800, 75], [1275, 75]]
ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")


class FwiInputError(ValueError):
    """Fixed public input/export rejection."""


def fail():
    raise FwiInputError("Invalid or unsupported acoustic input or generation")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()


def keys(value, expected):
    if type(value) is not dict or set(value) != set(expected.split()):
        fail()


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            fail()
        result[key] = value
    return result


def decode(raw, cap):
    if type(raw) is not bytes or not 0 < len(raw) <= cap:
        fail()
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=pairs,
                           parse_constant=lambda _: fail())
        def walk(item, depth=0):
            if depth > 12:
                fail()
            if type(item) is dict:
                for child in item.values():
                    walk(child, depth+1)
            elif type(item) is list:
                for child in item:
                    walk(child, depth+1)
        walk(value)
        return value
    except (UnicodeError, RecursionError, OverflowError, json.JSONDecodeError):
        fail()


def number(value, lower, upper):
    if type(value) not in (float, int) or not math.isfinite(value) or not lower <= value <= upper:
        fail()


def integer(value, lower, upper):
    if type(value) is not int or not lower <= value <= upper:
        fail()


def external(path):
    """Reject repo and redirected custody before reading or making a directory."""
    path = Path(path)
    if not path.is_absolute():
        fail()
    for parent in (path, *path.parents):
        if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
            fail()
        if (parent/".git").exists():
            fail()
    return path


def read_regular(path, cap):
    path = external(path)
    if not path.is_file() or not 0 < path.stat().st_size <= cap:
        fail()
    with path.open("rb") as stream:
        raw = stream.read(cap+1)
    if not 0 < len(raw) <= cap:
        fail()
    return raw


def receiver_coordinates(count):
    return [[float(int(6+114*i/(count-1)))*12.5, 75] for i in range(count)]


def array_descriptor(value, shape, units):
    keys(value, "shape dtype units bytes sha256")
    if value["shape"] != shape or value["dtype"] != "float32-le" or value["units"] != units:
        fail()
    if type(value["shape"]) is not list or any(type(size) is not int or size < 1 for size in value["shape"]):
        fail()
    size = 4*math.prod(shape)
    if type(value["bytes"]) is not int or value["bytes"] != size or size > MAX_ARRAY:
        fail()
    if type(value["sha256"]) is not str or not SHA.fullmatch(value["sha256"]):
        fail()


def validate_request(request_raw):
    request = decode(request_raw, MAX_REQUEST)
    keys(request, "schema id source acquisition observed initial parameters")
    if request["schema"] != SCHEMA or type(request["id"]) is not str or not ID.fullmatch(request["id"]):
        fail()
    source = request["source"]
    keys(source, "citation rights scope")
    if (type(source["citation"]) is not str or not source["citation"].strip()
            or len(source["citation"]) > 2048 or source["rights"] not in ("owner-permitted", "CC0", "CC-BY")
            or source["scope"] not in ("owner-provided", "synthetic-control")):
        fail()
    acquisition = request["acquisition"]
    keys(acquisition, "frame spacing_m dt_s sources_m receivers_m wavelet amplitude_convention")
    if (acquisition["frame"] != "local-x-z-down" or acquisition["spacing_m"] != 12.5
            or acquisition["dt_s"] != .0005 or acquisition["sources_m"] != SOURCES
            or acquisition["wavelet"] != "Ricker-peak-at-1.5-over-f"
            or acquisition["amplitude_convention"] != "Deepwave-scalar-point-source"):
        fail()
    observed = request["observed"]
    keys(observed, "shape dtype units bytes sha256")
    shape = observed["shape"]
    if type(shape) is not list or len(shape) != 3 or any(type(v) is not int for v in shape):
        fail()
    if shape[0] != 3 or shape[1] not in (20, 40):
        fail()
    integer(shape[2], 512, 3200)
    if acquisition["receivers_m"] != receiver_coordinates(shape[1]):
        fail()
    array_descriptor(observed, shape, "point-source-amplitude")
    array_descriptor(request["initial"], SHAPE, "m/s")
    parameters = request["parameters"]
    keys(parameters, "frequency_hz beta iterations_per_stage")
    number(parameters["frequency_hz"], 4, 12)
    number(parameters["beta"], .0001, .1)
    integer(parameters["iterations_per_stage"], 1, 100)
    return request


def admit(root):
    root = external(root)
    if not root.is_dir() or {p.name for p in root.iterdir()} != {"request.json", "observed.f32", "initial.f32"}:
        fail()
    request_raw = read_regular(root/"request.json", MAX_REQUEST)
    request = validate_request(request_raw)
    observed, shape = request["observed"], request["observed"]["shape"]
    raw = {"request.json":request_raw}
    for name, descriptor in (("observed.f32", observed), ("initial.f32", request["initial"])):
        member = read_regular(root/name, descriptor["bytes"])
        if len(member) != descriptor["bytes"] or digest(member) != descriptor["sha256"]:
            fail()
        energy = [0., 0.]
        for index, (value,) in enumerate(struct.iter_unpack("<f", member)):
            if not math.isfinite(value):
                fail()
            if name == "initial.f32":
                if not 1400 < value < 4400:
                    fail()
            else:
                if abs(value) > 1e12:
                    fail()
                energy[int((index//shape[2])%shape[1]%5 == 2)] += value*value
        if name == "observed.f32" and min(energy) <= 0:
            fail()
        raw[name] = member
    return request, raw


def _code_hashes():
    root = Path(__file__).resolve().parent
    return {name:digest((root/name).read_bytes()) for name in ("fwi_user_data.py", "seismic.py", "geology.py")}


def calculate(root, *, device):
    request, original = admit(root)
    source_hashes = _code_hashes()
    if device not in ("cpu", "cuda"):
        fail()
    import numpy as np
    import psutil
    import torch
    import seismic

    if device == "cuda" and not torch.cuda.is_available():
        raise FwiInputError("Requested CUDA device is unavailable")
    # Check the exact installed engine acquisition, including integer-cell
    # linspace rounding, before launching a single propagation.
    expected = (torch.linspace(6, 120, request["observed"]["shape"][1]).long()*12.5).tolist()
    if [point[0] for point in request["acquisition"]["receivers_m"]] != expected:
        raise FwiInputError("Declared acquisition differs from installed acoustic engine")
    observed = torch.tensor(np.frombuffer(original["observed.f32"], dtype="<f4").copy().reshape(request["observed"]["shape"]), device=device)
    initial = torch.tensor(np.frombuffer(original["initial.f32"], dtype="<f4").copy().reshape(SHAPE).T.copy(), device=device)
    prior = (torch.are_deterministic_algorithms_enabled(), torch.is_deterministic_algorithms_warn_only_enabled(),
             torch.backends.cudnn.deterministic, torch.backends.cudnn.benchmark)
    peak = [psutil.Process().memory_info().rss]
    stop = threading.Event()
    def monitor():
        process = psutil.Process()
        while not stop.wait(.02):
            peak[0] = max(peak[0], process.memory_info().rss)
    watcher = threading.Thread(target=monitor, daemon=True)
    started = time.perf_counter()
    watcher.start()
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    try:
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        outputs, active = seismic.invert_observations(observed, initial,
            frequency=request["parameters"]["frequency_hz"],
            iterations=request["parameters"]["iterations_per_stage"], beta=request["parameters"]["beta"])
        arrays = {"observed":observed.detach().cpu().numpy(), "initial":initial.detach().cpu().numpy().T}
        methods = {}
        for name in METHODS:
            output = outputs[name]
            predicted = output.pop("predicted_tensor").detach().cpu().numpy()
            first = output.pop("initial_prediction_tensor").detach().cpu().numpy()
            arrays[name+"-model"] = output.pop("model_tensor").detach().cpu().numpy().T
            arrays[name+"-background"] = output.pop("background_tensor").detach().cpu().numpy().T
            arrays[name+"-predicted"] = predicted
            arrays[name+"-residual"] = arrays["observed"]-predicted
            arrays[name+"-frames"] = np.asarray(output.pop("frames"), dtype=np.float32)
            mask = active.detach().cpu().numpy()
            metrics = {}
            for label, select in (("fitted", mask), ("withheld", ~mask)):
                target = arrays["observed"][:, select].astype(np.float64)
                denominator = float(np.mean(target*target))
                for stage, values in (("initial", first), ("final", predicted)):
                    metrics[label+"_"+stage+"_relative_mse"] = float(np.mean((target-values[:, select])**2)/denominator)
            methods[name] = {**output, "metrics":metrics, "numerical_verdict":"finite-budget",
                "truth":None, "model_recovery_evaluated":False}
        if device == "cuda":
            torch.cuda.synchronize()
        peak[0] = max(peak[0], psutil.Process().memory_info().rss)
        resources = {"wall_seconds":time.perf_counter()-started,"peak_sampled_rss_bytes":peak[0],
                     "rss_sampling_seconds":.02,
                     "peak_cuda_allocated_bytes":torch.cuda.max_memory_allocated() if device == "cuda" else 0}
    finally:
        stop.set()
        watcher.join(timeout=2)
        torch.use_deterministic_algorithms(prior[0], warn_only=prior[1])
        torch.backends.cudnn.deterministic, torch.backends.cudnn.benchmark = prior[2:]
    if _code_hashes() != source_hashes:
        raise FwiInputError("Acoustic source changed during execution")
    manifest = {"schema":RESULT_SCHEMA, "id":request["id"], "request":request,
                "request_utf8":original["request.json"].decode("utf-8"),
                "originals":{name:{"sha256":digest(raw),"bytes":len(raw)} for name,raw in original.items()},
                "execution_lane":"local-"+device,"truth":None,"methods":methods,
                "active_receivers":active.detach().cpu().tolist(),"source_hashes":source_hashes,
                "environment":{"torch":str(torch.__version__),"deepwave":version("deepwave"),"numpy":np.__version__,
                               "device":torch.cuda.get_device_name() if device == "cuda" else "CPU"},
                "resources":resources, "arrays":{}, "complete":False}
    return manifest, arrays


def _units(name):
    return "point-source-amplitude" if name == "observed" or name.endswith(("-predicted", "-residual")) else "m/s"


def exclusive(path, raw):
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def export_generation(manifest, arrays, output):
    import numpy as np
    output = external(output)
    if output.exists():
        raise FwiInputError("A fresh external output directory is required")
    output.mkdir(parents=False)
    members = {}
    total = 0
    for name, value in arrays.items():
        if name not in {"observed", "initial", *(method+"-"+kind for method in METHODS for kind in ("model", "background", "predicted", "residual", "frames"))}:
            fail()
        array = np.asarray(value, dtype="<f4", order="C")
        raw = array.tobytes(order="C")
        if not 0 < len(raw) <= MAX_ARRAY or not np.isfinite(array).all():
            fail()
        total += len(raw)
        if total > MAX_GENERATION:
            fail()
        exclusive(output/(name+".f32"), raw)
        members[name] = {"name":name+".f32", "dtype":"float32-le", "shape":list(array.shape),
                         "units":_units(name), "bytes":len(raw), "sha256":digest(raw)}
    # Verify the very bytes just written before creating the success manifest.
    prepared = {**manifest,"arrays":members,"complete":True}
    encoded = canonical(prepared)
    if len(encoded) > MAX_MANIFEST:
        fail()
    _reopen(output, prepared)
    exclusive(output/"manifest.json", encoded)
    return import_generation(output)


def _reopen(output, manifest):
    import numpy as np
    keys(manifest, "schema id request request_utf8 originals execution_lane truth methods active_receivers source_hashes environment resources arrays complete")
    expected = {"observed", "initial", *(method+"-"+kind for method in METHODS for kind in ("model", "background", "predicted", "residual", "frames"))}
    if (manifest.get("schema") != RESULT_SCHEMA or manifest.get("complete") is not True
            or manifest.get("truth") is not None or set(manifest.get("arrays", {})) != expected
            or set(manifest.get("methods", {})) != set(METHODS)):
        fail()
    request = validate_request(canonical(manifest["request"]))
    if type(manifest["request_utf8"]) is not str:
        fail()
    original_request = manifest["request_utf8"].encode("utf-8", errors="strict")
    if validate_request(original_request) != request:
        fail()
    if manifest["id"] != request["id"] or manifest["execution_lane"] not in ("local-cpu", "local-cuda"):
        fail()
    keys(manifest["originals"], "request.json observed.f32 initial.f32")
    for name, original in manifest["originals"].items():
        keys(original, "bytes sha256")
        integer(original["bytes"], 1, MAX_ARRAY)
        if type(original["sha256"]) is not str or not SHA.fullmatch(original["sha256"]):
            fail()
        if name != "request.json" and original != {key:request[name.split('.')[0]][key] for key in ("bytes", "sha256")}:
            fail()
    keys(manifest["source_hashes"], "fwi_user_data.py seismic.py geology.py")
    if any(type(value) is not str or not SHA.fullmatch(value) for value in manifest["source_hashes"].values()):
        fail()
    if manifest["originals"]["request.json"] != {"bytes":len(original_request),"sha256":digest(original_request)}:
        fail()
    keys(manifest["environment"], "torch deepwave numpy device")
    if any(type(value) is not str or not 0 < len(value) <= 256 for value in manifest["environment"].values()):
        fail()
    keys(manifest["resources"], "wall_seconds peak_sampled_rss_bytes rss_sampling_seconds peak_cuda_allocated_bytes")
    number(manifest["resources"]["wall_seconds"], 0, 1e9)
    integer(manifest["resources"]["peak_sampled_rss_bytes"], 1, 2**53-1)
    integer(manifest["resources"]["peak_cuda_allocated_bytes"], 0, 2**53-1)
    if manifest["resources"]["rss_sampling_seconds"] != .02:
        fail()
    shape = manifest["request"]["observed"]["shape"]
    if manifest["active_receivers"] != [index%5 != 2 for index in range(shape[1])]:
        fail()
    arrays = {}
    total = 0
    for name, descriptor in manifest["arrays"].items():
        keys(descriptor, "name dtype shape units bytes sha256")
        if descriptor["name"] != name+".f32":
            fail()
        declared = descriptor["shape"]
        if name == "observed" or name.endswith(("-predicted", "-residual")):
            if declared != shape:
                fail()
        elif name.endswith("-frames"):
            if type(declared) is not list or len(declared) != 3 or declared[1:] != SHAPE:
                fail()
            integer(declared[0], 1, 128)
        elif declared != SHAPE:
            fail()
        array_descriptor({k:v for k,v in descriptor.items() if k != "name"}, declared, _units(name))
        raw = read_regular(output/descriptor["name"], descriptor["bytes"])
        if len(raw) != descriptor["bytes"] or digest(raw) != descriptor["sha256"]:
            fail()
        total += len(raw)
        if total > MAX_GENERATION:
            fail()
        value = np.frombuffer(raw, dtype="<f4").reshape(declared)
        if not np.isfinite(value).all():
            fail()
        if _units(name) == "m/s" and (value.min() < 1400 or value.max() > 4400):
            fail()
        arrays[name] = value
    if digest(read_regular(output/"observed.f32", MAX_ARRAY)) != manifest["request"]["observed"]["sha256"] or digest(read_regular(output/"initial.f32", MAX_ARRAY)) != manifest["request"]["initial"]["sha256"]:
        fail()
    for method in METHODS:
        state = manifest["methods"][method]
        frames = arrays[method+"-frames"]
        indices = state["frame_history_indices"]
        if (type(indices) is not list or len(indices) != len(frames)
                or any(type(index) is not int or not 0 <= index < len(state["history_records"]) for index in indices)
                or any(right <= left for left, right in zip(indices, indices[1:]))
                or state["frame_indices"] != indices):
            fail()
        if (state.get("truth") is not None or state.get("model_recovery_evaluated") is not False
                or state.get("numerical_verdict") != "finite-budget"
                or state["state_identity"]["final_frame_index"] != len(frames)-1
                or state["frame_history_indices"][-1] != len(state["history_records"])-1
                or state["state_identity"]["selected_iteration"] != len(state["history_records"])-1
                or not np.array_equal(frames[-1], arrays[method+"-model"])
                or not np.array_equal(arrays[method+"-residual"], arrays["observed"]-arrays[method+"-predicted"])):
            fail()
    if arrays["initial"].min() <= 1400 or arrays["initial"].max() >= 4400:
        fail()
    return manifest, arrays


def import_generation(output):
    output = external(output)
    manifest = decode(read_regular(output/"manifest.json", MAX_MANIFEST), MAX_MANIFEST)
    if {path.name for path in output.iterdir()} != {"manifest.json", *(name+".f32" for name in manifest.get("arrays", {}))}:
        fail()
    return _reopen(output, manifest)
