"""Only training/development label clocks may inform pre-test method design."""

import hashlib
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from profile_stead_train_dev import profile  # noqa: E402
from stead_phase import METADATA_SHA256, SteadMember  # noqa: E402


def test_pick_position_profile_does_not_compute_test_member_statistics(tmp_path: Path):
    train = [
        SteadMember("noise", "bucket1$0,:3,:6000", None, "NW.N", "train",
                    "noise", "BH", None, None),
        SteadMember("quake", "bucket1$1,:3,:6000", "evt", "NW.Q", "train",
                    "earthquake_local", "BH", 700, 1300),
    ]
    dev = [
        SteadMember("devquake", "bucket1$2,:3,:6000", "dev-evt", "NW.D", "dev",
                    "earthquake_local", "BH", 850, 1900),
    ]
    selected = {
        "train": {"ids_sha256": hashlib.sha256("noise\nquake".encode()).hexdigest()},
        "dev": {"ids_sha256": hashlib.sha256("devquake".encode()).hexdigest()},
    }
    manifest = tmp_path / "selection.json"
    manifest.write_text(json.dumps({
        "schema": "caos.stead-phase-members.v1",
        "report": {"metadata_sha256": METADATA_SHA256, "selected": selected},
        "members": {
            "train": [item.__dict__ for item in train],
            "dev": [item.__dict__ for item in dev],
            "test": [{"trace_id": "never-inspect-test", "p_index": 9999}],
        },
    }), encoding="utf-8")
    result = profile(manifest)
    assert set(result["partitions"]) == {"train", "dev"}
    assert result["partitions"]["train"]["P_sample_quantiles"] == [700.0] * 7
    assert result["partitions"]["dev"]["P_sample_quantiles"] == [850.0] * 7
    assert result["test_member_statistics_computed"] is False
    assert "9999" not in json.dumps(result)
