from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_server_gravity_l2_runner_isolated_and_source_bound():
    script = (ROOT / "scripts/server_gravity_l2_admission.sh").read_text(encoding="utf-8")
    for term in (
        "set -Eeuo pipefail",
        "[[ $# != 1",
        "{7,63}",
        "/opt/fasl-admission/geophysics/$RUN_ID",
        "admission-source-revision.txt",
        "DynamicUser=yes",
        "StateDirectoryMode=0700",
        "ProtectSystem=strict",
        "ProtectHome=yes",
        "PrivateTmp=yes",
        "PrivateDevices=yes",
        "PrivateNetwork=yes",
        "NoNewPrivileges=yes",
        "CapabilityBoundingSet=",
        "MemoryMax=2G",
        "MemorySwapMax=0",
        "RuntimeMaxSec=1800",
        "GEOPHYSICS_TEST_GRAVITY_PYTHON",
        "test_uploaded_user_survey_runs_isolated_inverse_and_parameter_changes_predictions",
    ):
        assert term in script
    assert "PublicNetwork" not in script
    assert "nginx" not in script
    assert "activate" not in script.lower()
