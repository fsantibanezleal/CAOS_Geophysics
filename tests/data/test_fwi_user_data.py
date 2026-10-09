"""Separate strict byte/serialization controls from opt-in real CUDA physics."""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import sys

import numpy as np
import pytest

import fwi_user_data as fwi


def fixture(root, *, samples=512, receivers=20):
    root.mkdir()
    initial = np.full((96, 128), 2050, dtype="<f4")
    observed = np.linspace(.001, .005, 3*receivers*samples, dtype="<f4").reshape(3,receivers,samples)
    arrays = {"initial":initial,"observed":observed}
    descriptors = {}
    for name, value in arrays.items():
        raw = value.tobytes()
        (root/(name+".f32")).write_bytes(raw)
        descriptors[name] = {"shape":list(value.shape),"dtype":"float32-le",
                            "units":"m/s" if name == "initial" else "point-source-amplitude",
                            "sha256":fwi.digest(raw),"bytes":len(raw)}
    request = {"schema":fwi.SCHEMA,"id":"original-acoustic-control",
               "source":{"citation":"Original numerical integration control; no measured field geology",
                         "rights":"owner-permitted","scope":"synthetic-control"},
               "acquisition":{"frame":"local-x-z-down","spacing_m":12.5,"dt_s":.0005,
                   "sources_m":fwi.SOURCES,"receivers_m":fwi.receiver_coordinates(receivers),
                   "wavelet":"Ricker-peak-at-1.5-over-f","amplitude_convention":"Deepwave-scalar-point-source"},
               "initial":descriptors["initial"],"observed":descriptors["observed"],
               "parameters":{"frequency_hz":8,"beta":.001,"iterations_per_stage":1}}
    (root/"request.json").write_bytes(fwi.canonical(request))
    return request, arrays


@pytest.mark.parametrize("change", ["units","geometry","bool_shape","duplicate","excessive_depth","wrong_hash","nonfinite","repo","unknown","zero_energy","bounds"])
def test_admission_before_engine(tmp_path, change):
    root = tmp_path/"input"
    request, _ = fixture(root)
    if change == "units":
        request["observed"]["units"] = "Pa"
    elif change == "geometry":
        request["acquisition"]["sources_m"] = [[400,75],[800,75],[1275,75]]
    elif change == "bool_shape":
        request["initial"]["shape"] = [96.0,128]
    elif change == "wrong_hash":
        request["observed"]["sha256"] = "0"*64
    elif change == "unknown":
        request["download_url"] = "https://example.invalid/never-read"
    elif change == "repo":
        (tmp_path/".git").write_text("gitdir: never-read")
    elif change in ("nonfinite","zero_energy","bounds"):
        name = "initial" if change == "bounds" else "observed"
        raw = (root/(name+".f32")).read_bytes()
        if change == "zero_energy":
            raw = b"\x00"*len(raw)
        else:
            raw = struct.pack("<f", float("nan") if change == "nonfinite" else 1400)+raw[4:]
        (root/(name+".f32")).write_bytes(raw)
        request[name]["sha256"] = fwi.digest(raw)
    encoded = fwi.canonical(request)
    if change == "duplicate":
        encoded = encoded[:-1]+b',"id":"duplicate"}'
    elif change == "excessive_depth":
        encoded = b'['*20+b'0'+b']'*20
    (root/"request.json").write_bytes(encoded)
    with pytest.raises(fwi.FwiInputError):
        fwi.admit(root)


def test_lineage_and_no_truth(tmp_path):
    root = tmp_path/"input"
    request, _ = fixture(root)
    before = {path.name:fwi.digest(path.read_bytes()) for path in root.iterdir()}
    admitted, raw = fwi.admit(root)
    assert admitted == request
    assert fwi.digest(raw["request.json"]) == before["request.json"]
    assert {path.name:fwi.digest(path.read_bytes()) for path in root.iterdir()} == before
    changed = deepcopy(request)
    changed["truth"] = [[2200]]
    with pytest.raises(fwi.FwiInputError):
        fwi.validate_request(fwi.canonical(changed))


def bookkeeping(request, arrays, root):
    # Algebraic arrays validate storage and binding only, NOT acoustic physics.
    output = {**arrays}
    methods = {}
    for method in fwi.METHODS:
        output[method+"-model"] = arrays["initial"].copy()
        output[method+"-background"] = arrays["initial"].copy()
        output[method+"-predicted"] = arrays["observed"]*.9
        output[method+"-residual"] = arrays["observed"]-output[method+"-predicted"]
        output[method+"-frames"] = np.stack([arrays["initial"],arrays["initial"]])
        methods[method] = {"truth":None,"model_recovery_evaluated":False,"numerical_verdict":"finite-budget",
                          "history_records":[{"update":0},{"update":1}],"frame_history_indices":[0,1],"frame_indices":[0,1],
                          "state_identity":{"final_frame_index":1,"selected_iteration":1}}
    manifest = {"schema":fwi.RESULT_SCHEMA,"id":request["id"],"request":request,
                "request_utf8":(root/"request.json").read_text(encoding="utf-8"),
                "originals":{path.name:{"sha256":fwi.digest(path.read_bytes()),"bytes":path.stat().st_size} for path in root.iterdir()},
                "execution_lane":"local-cpu","truth":None,"methods":methods,"active_receivers":[i%5 != 2 for i in range(20)],
                "source_hashes":fwi._code_hashes(),"environment":{"torch":"storage-control","deepwave":"not-executed","numpy":np.__version__,"device":"CPU"},
                "resources":{"wall_seconds":0.,"peak_sampled_rss_bytes":1,"rss_sampling_seconds":.02,"peak_cuda_allocated_bytes":0},"arrays":{},"complete":False}
    return manifest, output


@pytest.mark.parametrize("change", ["bytes","units","shape","unknown_member","final_frame","mask","truth","request"])
def test_export_roundtrip_and_tampering(tmp_path, change):
    root = tmp_path/"input"
    request, arrays = fixture(root)
    manifest, values = bookkeeping(request, arrays, root)
    output = tmp_path/"generation"
    saved, loaded = fwi.export_generation(manifest, values, output)
    np.testing.assert_array_equal(loaded["observed"], arrays["observed"])
    assert saved["truth"] is None
    with pytest.raises(fwi.FwiInputError):
        fwi.export_generation(manifest, values, output)
    if change == "bytes":
        target = output/"fwi-l2-predicted.f32"
        target.write_bytes(target.read_bytes()[:-4]+struct.pack("<f",3.))
    elif change == "unknown_member":
        (output/"original-secret.dat").write_bytes(b"unknown")
    else:
        if change == "units":
            saved["arrays"]["fwi-l2-model"]["units"] = "km/s"
        elif change == "shape":
            saved["arrays"]["observed"]["shape"] = [20,3,512]
        elif change == "final_frame":
            saved["methods"]["fwi-l2"]["state_identity"]["final_frame_index"] = 0
        elif change == "mask":
            saved["active_receivers"][2] = True
        elif change == "truth":
            saved["truth"] = [[999]]
        elif change == "request":
            saved["request"]["acquisition"]["dt_s"] = .004
        (output/"manifest.json").write_bytes(fwi.canonical(saved))
    with pytest.raises(fwi.FwiInputError):
        fwi.import_generation(output)


def test_cli_and_no_overwrite(tmp_path):
    root = tmp_path/"input"
    fixture(root)
    output = tmp_path/"existing"
    output.mkdir()
    marker = output/"protected.txt"
    marker.write_bytes(b"keep")
    script = Path(__file__).resolve().parents[2]/"scripts/process_fwi.py"
    completed = subprocess.run([sys.executable,"-B",str(script),"--input",str(root),"--output",str(output),"--device","cuda"],capture_output=True,timeout=20)
    assert completed.returncode == 2 and b"failed" in completed.stderr
    assert completed.stdout == b"" and marker.read_bytes() == b"keep"
    assert not (output/"manifest.json").exists()


def test_prepare_original_cli_preserves_and_rejects_before_output(tmp_path):
    root = tmp_path/"input"
    fixture(root)
    original = {name:(root/name).read_bytes() for name in ("observed.f32","initial.f32")}
    script = Path(__file__).resolve().parents[2]/"scripts/prepare_fwi_input.py"
    def command(output):
        return [sys.executable,"-B",str(script),"--observed",str(root/"observed.f32"),"--initial",str(root/"initial.f32"),
                "--output",str(output),"--id","prepared-control","--citation","Independent original acquisition declaration",
                "--rights","owner-permitted","--scope","synthetic-control","--receivers","20","--samples","512",
                "--frequency-hz","8","--beta","0.001","--iterations-per-stage","28"]
    output = tmp_path/"prepared"
    completed = subprocess.run(command(output),capture_output=True,timeout=20)
    assert completed.returncode == 0, completed.stderr
    request, raw = fwi.admit(output)
    assert request["parameters"]["iterations_per_stage"] == 28
    assert raw["observed.f32"] == original["observed.f32"]
    assert {name:(root/name).read_bytes() for name in original} == original
    repeated = subprocess.run(command(output),capture_output=True,timeout=20)
    assert repeated.returncode == 2
    invalid = tmp_path/"invalid-preparation"
    (root/"initial.f32").write_bytes(struct.pack("<f",float("nan"))+original["initial.f32"][4:])
    rejected = subprocess.run(command(invalid),capture_output=True,timeout=20)
    assert rejected.returncode == 2 and not invalid.exists()


@pytest.mark.skipif(os.environ.get("GEOPHYSICS_FWI_GPU_TEST") != "1", reason="explicit serialized CUDA gate required")
@pytest.mark.parametrize("receivers", [20, 40])
def test_actual_gpu_input_and_parameter_effect(tmp_path, receivers):
    import torch
    import seismic
    assert torch.cuda.is_available(), "explicit GPU gate must not silently skip unavailable hardware"
    torch.set_num_threads(2)
    root = tmp_path/"actual-original"
    request, _ = fixture(root, samples=768, receivers=receivers)
    with torch.no_grad():
        original = seismic.simulate(torch.full((128,96),2200.,device="cuda"),frequency=8.,receivers=receivers,nt=768).cpu().numpy().astype("<f4")
    raw = original.tobytes()
    (root/"observed.f32").write_bytes(raw)
    request["observed"]["sha256"] = hashlib.sha256(raw).hexdigest()
    (root/"request.json").write_bytes(fwi.canonical(request))
    original_hash = fwi.digest(raw)
    manifest, arrays = fwi.calculate(root,device="cuda")
    saved, loaded = fwi.export_generation(manifest,arrays,tmp_path/"actual-result")
    assert saved["execution_lane"] == "local-cuda"
    assert saved["resources"]["peak_cuda_allocated_bytes"] > 0
    assert loaded["observed"].shape == (3,receivers,768)
    assert saved["active_receivers"] == [index % 5 != 2 for index in range(receivers)]
    assert fwi.digest((root/"observed.f32").read_bytes()) == original_hash
    for method in fwi.METHODS:
        assert saved["methods"][method]["solver"]["truth_used_by_inverse"] is False
        np.testing.assert_array_equal(loaded[method+"-frames"][-1],loaded[method+"-model"])
        np.testing.assert_array_equal(loaded[method+"-residual"], original-loaded[method+"-predicted"])
        assert saved["methods"][method]["solver"]["optimizer_calls"] == 4
    request["parameters"]["beta"] = .05
    (root/"request.json").write_bytes(fwi.canonical(request))
    changed, second = fwi.calculate(root,device="cuda")
    assert changed["request"]["parameters"]["beta"] == .05
    assert not np.array_equal(arrays["fwi-multiscale-model"],second["fwi-multiscale-model"])


@pytest.mark.skipif(os.environ.get("GEOPHYSICS_FWI_FULL_GPU_TEST") != "1", reason="explicit full-budget serialized CUDA gate required")
def test_full_budget_supplied_gpu_replay(tmp_path):
    import torch
    import seismic
    assert torch.cuda.is_available()
    torch.set_num_threads(2)
    root = tmp_path/"full-original"
    request, _ = fixture(root, samples=3200)
    # Original controlled heterogeneous source, no smoothed-truth initial.
    x = torch.arange(128, device="cuda")[:, None]
    z = torch.arange(96, device="cuda")[None, :]
    truth = (2000.+z*8.+((x > 55)&(z > 35))*240.).expand(128,96).contiguous()
    with torch.no_grad():
        observed = seismic.simulate(truth,frequency=8.,receivers=20,nt=3200).cpu().numpy().astype("<f4")
    original = observed.tobytes()
    (root/"observed.f32").write_bytes(original)
    request["observed"]["sha256"] = fwi.digest(original)
    request["parameters"]["iterations_per_stage"] = 28
    (root/"request.json").write_bytes(fwi.canonical(request))
    before = {path.name:fwi.digest(path.read_bytes()) for path in root.iterdir()}
    script = Path(__file__).resolve().parents[2]/"scripts/process_fwi.py"
    output = tmp_path/"full-result"
    completed = subprocess.run([sys.executable,"-B",str(script),"--input",str(root),"--output",str(output),"--device","cuda"],capture_output=True,timeout=1800,
                               env={**os.environ,"OMP_NUM_THREADS":"2","MKL_NUM_THREADS":"2"})
    assert completed.returncode == 0, completed.stderr[-2000:]
    manifest, arrays = fwi.import_generation(output)
    assert {path.name:fwi.digest(path.read_bytes()) for path in root.iterdir()} == before
    evaluations = {}
    for method in fwi.METHODS:
        assert manifest["methods"][method]["solver"]["optimizer_calls"] == 112
        velocity = torch.tensor(arrays[method+"-model"].T.copy(), device="cuda")
        with torch.no_grad():
            predicted = seismic.simulate(velocity,frequency=8.,receivers=20,nt=3200).cpu().numpy()
        np.testing.assert_allclose(arrays[method+"-predicted"],predicted,rtol=2e-5,atol=2e-5)
        np.testing.assert_allclose(arrays[method+"-residual"],observed-predicted,rtol=2e-4,atol=2e-5)
        evaluations[method] = {"model_rmse_m_s":float(np.sqrt(np.mean((arrays[method+"-model"]-truth.cpu().numpy().T)**2))),
                               "initial_model_rmse_m_s":float(np.sqrt(np.mean((arrays["initial"]-truth.cpu().numpy().T)**2))),
                               "metrics":manifest["methods"][method]["metrics"],
                               "solver_stop":"finite_budget"}
    # Truth is evaluated externally only after both inverses/export are fixed.
    (tmp_path/"independent-replay.json").write_bytes(fwi.canonical({"schema":"geophysics.fwi-user-workflow-review/v1",
        "array_forward_replay_passed":True,"iterations_per_stage":28,"truth_used_by_inverse":False,
        "model_recovery_is_acceptance":False,"evaluation":evaluations,"resources":manifest["resources"],
        "manifest_sha256":fwi.digest((output/"manifest.json").read_bytes())}))
