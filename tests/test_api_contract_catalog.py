from pathlib import Path
import subprocess
import sys


def test_runtime_api_payload_schemas_and_openapi_match_route_source():
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, str(root / "scripts/check_api_contracts.py")], cwd=root, check=True)
