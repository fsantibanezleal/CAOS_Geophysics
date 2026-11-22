"""Product-specific checks for the template-derived local workflow contract."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def workflow_module():
    spec = importlib.util.spec_from_file_location("geophysics_local_workflow", ROOT / "scripts/local/workflow.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_workflow_declares_real_scientific_pipeline_and_outputs():
    config = json.loads((ROOT / "scripts/local/workflow.json").read_text(encoding="utf-8"))
    assert config["readiness_provider"] == "scripts/local/geophysics_readiness.py"
    assert config["readiness_check"] == "scripts/check_readiness.py"
    assert config["stage_inputs"] == []
    assert config["required"] == [
        "data/derived/v2/catalog.json",
        "data/derived/v2/release.json",
        "data/derived/readiness.json",
        "data/derived/v2/models/training.json",
        "data/derived/v2/models/cnn.json",
        "data/derived/v2/models/autoencoder.json",
    ]
    assert config["promote"] == ["data/derived/v2", "data/derived/readiness.json"]
    assert not any("params.csv" in str(row) or "surrogate.json" in str(row)
                   for row in config["generation"] + config["validators"])
    for row in config["generation"] + config["validators"]:
        assert (ROOT / row["script"]).is_file(), row["script"]
    assert "data-pipeline/rebuild.py" in [row["script"] for row in config["generation"]]
    assert "scripts/check_artifacts.py" in [row["script"] for row in config["validators"]]


def test_readiness_provider_admits_current_release_and_rejects_incomplete_stage(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "geophysics_readiness_provider", ROOT / "scripts/local/geophysics_readiness.py"
    )
    provider = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(provider)

    assert provider.validate(ROOT)
    empty = tmp_path / "incomplete"
    (empty / "data/derived/v2").mkdir(parents=True)
    (empty / "VERSION").write_text((ROOT / "VERSION").read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises((FileNotFoundError, ValueError, json.JSONDecodeError)):
        provider.validate(empty)


def test_promoted_file_and_directory_are_hash_bound(tmp_path):
    workflow = workflow_module()
    stage = tmp_path / "stage"
    (stage / "data/derived/v2").mkdir(parents=True)
    (stage / "data/derived/v2/catalog.json").write_bytes(b'{"complete":true}\n')
    (stage / "data/derived/readiness.json").write_bytes(b'{"state":"available"}\n')
    config = {"promote": ["data/derived/v2", "data/derived/readiness.json"]}

    hashes = workflow.payload_hashes(stage, config)

    assert hashes == {
        "data/derived/v2/catalog.json": hashlib.sha256(b'{"complete":true}\n').hexdigest(),
        "data/derived/readiness.json": hashlib.sha256(b'{"state":"available"}\n').hexdigest(),
    }
