"""Native export parity on a synthetic contract fixture, not a field score."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import onnx
import pytest
import torch


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import export_stead_phase_onnx as exporter  # noqa: E402
from phase_model import PhaseUNet  # noqa: E402
from stead_phase import file_sha256  # noqa: E402


def test_frozen_checkpoint_exports_once_with_native_dev_parity(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(exporter, "ROOT", tmp_path)
    private = tmp_path / "data/raw/phase"
    extraction = private / "extracted"
    models = private / "models"
    extraction.mkdir(parents=True)
    models.mkdir()
    values = np.random.default_rng(22).normal(size=(2, 3, 6000)).astype(np.float32)
    array_path = extraction / "stead-dev-normalized.npy"
    np.save(array_path, values)
    source_hash = "a" * 64
    dev_hash = "b" * 64
    model_code_sha256 = hashlib.sha256(
        Path(sys.modules[PhaseUNet.__module__].__file__).read_bytes()).hexdigest()
    (extraction / "stead-dev-index.json").write_text(json.dumps({
        "schema": "caos.stead-phase-local-array.v1", "partition": "dev",
        "array_shape": [2, 3, 6000], "array_sha256": file_sha256(array_path),
        "selection_sha256": dev_hash, "waveform_source_sha256": source_hash,
        "members": [
            {"valid": True, "member": {"trace_id": "dev-a", "p_index": 1000, "s_index": 2000}},
            {"valid": True, "member": {"trace_id": "dev-b", "p_index": None, "s_index": None}},
        ],
    }), encoding="utf-8")
    checkpoint = models / "phase-model.pt"
    torch.save({
        "schema": "caos.phase-picking-checkpoint.v1",
        "model": PhaseUNet().state_dict(),
        "source_sha256": source_hash,
        "dev_selection_sha256": dev_hash,
        "chosen_epoch": 1,
        "model_code_sha256": model_code_sha256,
        "input": {"shape": [3, 6000]},
    }, checkpoint)
    freeze = models / "phase-freeze.json"
    freeze.write_text(json.dumps({
        "schema": "caos.phase-freeze.v1", "frozen_before_test": True,
        "checkpoint_filename": checkpoint.name,
        "checkpoint_sha256": file_sha256(checkpoint),
        "waveform_source_sha256": source_hash,
        "chosen_epoch": 1,
        "model_code_sha256": model_code_sha256,
        "p_threshold": 0.5, "s_threshold": 0.5,
    }), encoding="utf-8")
    result = exporter.export(
        extraction, freeze, models, sample_count=2,
        private_root=tmp_path / "data/raw",
    )
    assert result["status"] == "native-onnx-dev-parity-only"
    assert result["parity"]["dev_trace_count"] == 2
    assert result["parity"]["max_probability_absolute_error"] <= 0.001
    assert result["parity"]["max_peak_time_error_samples"] <= 1
    assert result["onnx_sha256"] == file_sha256(models / "phase-model.onnx")
    assert b"D:\\_Repos" not in (models / "phase-model.onnx").read_bytes()
    assert not result["heldout_test_opened"] and not result["browser_parity_claim"]
    with pytest.raises(FileExistsError, match="do not overwrite"):
        exporter.export(extraction, freeze, models, sample_count=2,
                        private_root=tmp_path / "data/raw")


def test_exporter_debug_paths_are_removed_from_nested_onnx_docs(tmp_path: Path):
    graph = onnx.helper.make_graph(
        [onnx.helper.make_node("Identity", ["x"], ["y"])], "identity",
        [onnx.helper.make_tensor_value_info("x", onnx.TensorProto.FLOAT, [1])],
        [onnx.helper.make_tensor_value_info("y", onnx.TensorProto.FLOAT, [1])],
    )
    model = onnx.helper.make_model(graph)
    model.graph.node[0].doc_string = "D:\\_Repos\\private\\path\\model.py"
    trace = model.graph.node[0].metadata_props.add()
    trace.key = "pkg.torch.onnx.stack_trace"
    trace.value = "D:\\_Repos\\private\\path\\model.py"
    retained = model.graph.node[0].metadata_props.add()
    retained.key = "scientific.parameter"
    retained.value = "fixed"
    model.doc_string = "D:\\_Repos\\private\\path\\export.py"
    path = tmp_path / "with-debug.onnx"
    onnx.save_model(model, path)
    exporter._sanitize_export(path)
    cleaned = onnx.load(str(path))
    assert cleaned.doc_string == ""
    assert cleaned.graph.node[0].doc_string == ""
    assert cleaned.graph.node[0].op_type == "Identity"
    assert [(pair.key, pair.value) for pair in cleaned.graph.node[0].metadata_props] == [("scientific.parameter", "fixed")]
    assert b"D:\\_Repos" not in path.read_bytes()
